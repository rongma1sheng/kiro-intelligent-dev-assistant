"""
期货合约拼接器 - Contract Stitcher

白皮书依据: 第三章 3.3 衍生品管道 - Contract Stitcher
版本: v1.0.0
作者: MIA Team
日期: 2026-01-22

功能:
1. 主力合约识别（基于成交量和持仓量）
2. 价差平移算法（生成连续合约）
3. 合约切换点检测
4. 多品种期货支持（股指、商品、国债）

算法:
- 价差平移法: 在主力合约切换时，将历史价格平移，消除跳空
- 主力识别: 成交量和持仓量加权评分
- 切换检测: 连续N天成交量/持仓量超过阈值

性能目标:
- 拼接速度: > 1000条/秒
- 内存占用: < 500MB（单品种）
- 延迟: < 100ms（单次拼接）
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from loguru import logger


@dataclass
class ContractData:
    """期货合约数据结构

    Attributes:
        symbol: 合约代码（如IF2401）
        date: 交易日期
        open: 开盘价
        high: 最高价
        low: 最低价
        close: 收盘价
        volume: 成交量
        open_interest: 持仓量
        settlement: 结算价（可选）
    """

    symbol: str
    date: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    open_interest: float
    settlement: Optional[float] = None


@dataclass
class StitchedContract:
    """拼接后的连续合约数据

    Attributes:
        date: 交易日期
        open: 开盘价（调整后）
        high: 最高价（调整后）
        low: 最低价（调整后）
        close: 收盘价（调整后）
        volume: 成交量
        open_interest: 持仓量
        main_contract: 当前主力合约代码
        adjustment: 价差调整量
    """

    date: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    open_interest: float
    main_contract: str
    adjustment: float = 0.0


@dataclass
class SwitchPoint:
    """合约切换点

    Attributes:
        date: 切换日期
        old_contract: 旧主力合约
        new_contract: 新主力合约
        price_diff: 价差
        volume_ratio: 成交量比例
        oi_ratio: 持仓量比例
    """

    date: datetime
    old_contract: str
    new_contract: str
    price_diff: float
    volume_ratio: float
    oi_ratio: float


class ContractStitcher:
    """期货合约拼接器

    白皮书依据: 第三章 3.3 衍生品管道 - Contract Stitcher

    使用价差平移法拼接期货主力连续合约，消除合约切换时的跳空。

    Attributes:
        volume_weight: 成交量权重，默认0.6
        oi_weight: 持仓量权重，默认0.4
        switch_threshold: 切换阈值，默认1.2（新合约指标需超过旧合约20%）
        switch_days: 连续天数，默认3（连续3天满足条件才切换）
        contracts_buffer: 合约数据缓冲区
        switch_points: 切换点记录
        stats: 拼接统计
    """

    def __init__(
        self, volume_weight: float = 0.6, oi_weight: float = 0.4, switch_threshold: float = 1.2, switch_days: int = 3
    ):
        """初始化合约拼接器

        Args:
            volume_weight: 成交量权重，范围[0, 1]
            oi_weight: 持仓量权重，范围[0, 1]
            switch_threshold: 切换阈值，> 1.0
            switch_days: 连续天数，>= 1

        Raises:
            ValueError: 当参数不在有效范围时
        """
        # 参数验证
        if not 0 <= volume_weight <= 1:
            raise ValueError(f"成交量权重必须在[0, 1]，当前: {volume_weight}")

        if not 0 <= oi_weight <= 1:
            raise ValueError(f"持仓量权重必须在[0, 1]，当前: {oi_weight}")

        if abs(volume_weight + oi_weight - 1.0) > 1e-6:
            raise ValueError(f"权重之和必须为1，当前: {volume_weight + oi_weight}")

        if switch_threshold <= 1.0:
            raise ValueError(f"切换阈值必须 > 1.0，当前: {switch_threshold}")

        if switch_days < 1:
            raise ValueError(f"连续天数必须 >= 1，当前: {switch_days}")

        # 初始化属性
        self.volume_weight = volume_weight
        self.oi_weight = oi_weight
        self.switch_threshold = switch_threshold
        self.switch_days = switch_days

        # 数据缓冲区
        self.contracts_buffer: Dict[str, List[ContractData]] = {}
        self.switch_points: List[SwitchPoint] = []

        # 统计信息
        self.stats = {"total_contracts": 0, "total_switches": 0, "total_stitched": 0, "processing_time_ms": 0.0}

        logger.info(
            f"ContractStitcher初始化完成 - "
            f"volume_weight={volume_weight}, "
            f"oi_weight={oi_weight}, "
            f"switch_threshold={switch_threshold}, "
            f"switch_days={switch_days}"
        )

    def add_contract_data(self, symbol: str, data: List[ContractData]) -> None:
        """添加合约数据到缓冲区

        Args:
            symbol: 合约代码
            data: 合约数据列表

        Raises:
            ValueError: 当数据为空时
        """
        if not data:
            raise ValueError(f"合约数据不能为空: {symbol}")

        # 按日期排序
        sorted_data = sorted(data, key=lambda x: x.date)

        self.contracts_buffer[symbol] = sorted_data
        self.stats["total_contracts"] += 1

        logger.debug(f"添加合约数据: {symbol}, 数据量: {len(sorted_data)}")

    def identify_main_contract(self, date: datetime, contracts: List[str]) -> Optional[str]:
        """识别指定日期的主力合约

        白皮书依据: 第三章 3.3 衍生品管道 - 主力合约识别

        基于成交量和持仓量的加权评分识别主力合约。
        评分 = volume_weight * 成交量 + oi_weight * 持仓量

        Args:
            date: 交易日期
            contracts: 候选合约列表

        Returns:
            主力合约代码，如果无法识别则返回None
        """
        if not contracts:
            return None

        scores = {}

        for contract in contracts:
            if contract not in self.contracts_buffer:
                continue

            # 查找指定日期的数据
            contract_data = self.contracts_buffer[contract]
            day_data = None

            for data in contract_data:
                if data.date == date:
                    day_data = data
                    break

            if day_data is None:
                continue

            # 计算加权评分
            score = self.volume_weight * day_data.volume + self.oi_weight * day_data.open_interest
            scores[contract] = score

        if not scores:
            return None

        # 返回评分最高的合约
        main_contract = max(scores, key=scores.get)

        logger.debug(f"识别主力合约: {date.date()}, " f"主力={main_contract}, " f"评分={scores[main_contract]:.0f}")

        return main_contract

    def detect_switch_points(self, contracts: List[str], start_date: datetime, end_date: datetime) -> List[SwitchPoint]:
        """检测合约切换点

        白皮书依据: 第三章 3.3 衍生品管道 - 切换点检测

        检测主力合约切换点，要求新合约连续N天的评分超过旧合约。

        Args:
            contracts: 合约列表
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            切换点列表
        """
        switch_points = []
        current_main = None
        consecutive_days = 0
        candidate_main = None

        # 遍历每个交易日
        current_date = start_date
        while current_date <= end_date:
            # 识别当日主力合约
            main_contract = self.identify_main_contract(current_date, contracts)

            if main_contract is None:
                current_date += timedelta(days=1)
                continue

            # 初始化主力合约
            if current_main is None:
                current_main = main_contract
                current_date += timedelta(days=1)
                continue

            # 检查是否有新的候选主力
            if main_contract != current_main:
                # 计算评分比例
                current_score = self._get_contract_score(current_date, current_main)
                new_score = self._get_contract_score(current_date, main_contract)

                if current_score > 0:
                    score_ratio = new_score / current_score
                else:
                    score_ratio = float("inf")

                # 检查是否满足切换阈值
                if score_ratio >= self.switch_threshold:
                    if candidate_main == main_contract:
                        consecutive_days += 1
                    else:
                        candidate_main = main_contract
                        consecutive_days = 1

                    # 连续N天满足条件，确认切换
                    if consecutive_days >= self.switch_days:
                        # 获取价差
                        old_price = self._get_contract_price(current_date, current_main)
                        new_price = self._get_contract_price(current_date, main_contract)
                        price_diff = new_price - old_price if old_price and new_price else 0.0

                        # 记录切换点
                        switch_point = SwitchPoint(
                            date=current_date,
                            old_contract=current_main,
                            new_contract=main_contract,
                            price_diff=price_diff,
                            volume_ratio=score_ratio,
                            oi_ratio=score_ratio,
                        )
                        switch_points.append(switch_point)

                        logger.info(
                            f"检测到合约切换: {current_date.date()}, "
                            f"{current_main} → {main_contract}, "
                            f"价差={price_diff:.2f}"
                        )

                        # 更新主力合约
                        current_main = main_contract
                        consecutive_days = 0
                        candidate_main = None
                else:
                    # 不满足阈值，重置计数
                    consecutive_days = 0
                    candidate_main = None
            else:
                # 仍是当前主力，重置计数
                consecutive_days = 0
                candidate_main = None

            current_date += timedelta(days=1)

        self.switch_points = switch_points
        self.stats["total_switches"] = len(switch_points)

        logger.info(f"检测到 {len(switch_points)} 个切换点")

        return switch_points

    def stitch_contracts(
        self, contracts: List[str], start_date: datetime, end_date: datetime
    ) -> List[StitchedContract]:
        """拼接合约生成连续序列

        白皮书依据: 第三章 3.3 衍生品管道 - 价差平移算法

        使用价差平移法拼接合约，在切换点调整历史价格，消除跳空。

        Args:
            contracts: 合约列表
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            拼接后的连续合约数据

        Raises:
            ValueError: 当合约列表为空时
        """
        if not contracts:
            raise ValueError("合约列表不能为空")

        import time  # pylint: disable=import-outside-toplevel

        start_time = time.perf_counter()

        # 检测切换点
        switch_points = self.detect_switch_points(contracts, start_date, end_date)

        # 构建切换点字典（日期 -> 切换点）
        switch_dict = {sp.date: sp for sp in switch_points}

        # 拼接数据
        stitched_data = []
        cumulative_adjustment = 0.0
        current_main = None

        current_date = start_date
        while current_date <= end_date:
            # 检查是否有切换点
            if current_date in switch_dict:
                switch_point = switch_dict[current_date]
                # 累加价差调整
                cumulative_adjustment += switch_point.price_diff
                current_main = switch_point.new_contract

                logger.debug(
                    f"应用价差调整: {current_date.date()}, "
                    f"调整量={switch_point.price_diff:.2f}, "
                    f"累计={cumulative_adjustment:.2f}"
                )

            # 如果还没有主力合约，识别一个
            if current_main is None:
                current_main = self.identify_main_contract(current_date, contracts)

            if current_main is None:
                current_date += timedelta(days=1)
                continue

            # 获取当日数据
            day_data = self._get_contract_data(current_date, current_main)

            if day_data is None:
                current_date += timedelta(days=1)
                continue

            # 应用价差调整
            stitched = StitchedContract(
                date=day_data.date,
                open=day_data.open - cumulative_adjustment,
                high=day_data.high - cumulative_adjustment,
                low=day_data.low - cumulative_adjustment,
                close=day_data.close - cumulative_adjustment,
                volume=day_data.volume,
                open_interest=day_data.open_interest,
                main_contract=current_main,
                adjustment=cumulative_adjustment,
            )

            stitched_data.append(stitched)

            current_date += timedelta(days=1)

        elapsed = (time.perf_counter() - start_time) * 1000
        self.stats["processing_time_ms"] = elapsed
        self.stats["total_stitched"] = len(stitched_data)

        logger.info(
            f"合约拼接完成 - " f"数据量={len(stitched_data)}, " f"切换点={len(switch_points)}, " f"耗时={elapsed:.2f}ms"
        )

        return stitched_data

    def _get_contract_score(self, date: datetime, contract: str) -> float:
        """获取合约评分（内部方法）

        Args:
            date: 交易日期
            contract: 合约代码

        Returns:
            评分，如果无数据则返回0
        """
        if contract not in self.contracts_buffer:
            return 0.0

        contract_data = self.contracts_buffer[contract]

        for data in contract_data:
            if data.date == date:
                return self.volume_weight * data.volume + self.oi_weight * data.open_interest

        return 0.0

    def _get_contract_price(self, date: datetime, contract: str) -> Optional[float]:
        """获取合约价格（内部方法）

        Args:
            date: 交易日期
            contract: 合约代码

        Returns:
            收盘价，如果无数据则返回None
        """
        if contract not in self.contracts_buffer:
            return None

        contract_data = self.contracts_buffer[contract]

        for data in contract_data:
            if data.date == date:
                return data.close

        return None

    def _get_contract_data(self, date: datetime, contract: str) -> Optional[ContractData]:
        """获取合约数据（内部方法）

        Args:
            date: 交易日期
            contract: 合约代码

        Returns:
            合约数据，如果无数据则返回None
        """
        if contract not in self.contracts_buffer:
            return None

        contract_data = self.contracts_buffer[contract]

        for data in contract_data:
            if data.date == date:
                return data

        return None

    def get_stats(self) -> Dict[str, any]:
        """获取拼接统计

        Returns:
            统计信息字典
        """
        return {
            "total_contracts": self.stats["total_contracts"],
            "total_switches": self.stats["total_switches"],
            "total_stitched": self.stats["total_stitched"],
            "processing_time_ms": self.stats["processing_time_ms"],
            "avg_time_per_record_ms": (
                self.stats["processing_time_ms"] / self.stats["total_stitched"]
                if self.stats["total_stitched"] > 0
                else 0.0
            ),
        }

    def reset_stats(self) -> None:
        """重置统计"""
        self.stats = {"total_contracts": 0, "total_switches": 0, "total_stitched": 0, "processing_time_ms": 0.0}
        logger.info("拼接统计已重置")

    def clear_buffer(self) -> None:
        """清空缓冲区"""
        self.contracts_buffer.clear()
        self.switch_points.clear()
        logger.info("缓冲区已清空")
