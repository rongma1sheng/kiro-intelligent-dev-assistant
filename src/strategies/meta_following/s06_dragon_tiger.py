"""S06 Dragon Tiger (龙虎榜) - 游资跟随策略

白皮书依据: 第六章 5.2 模块化军火库 - Meta-Following系

策略特点：
- 解析每日龙虎榜数据
- 跟随知名游资席位
- 短线操作
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Set

from loguru import logger

from src.strategies.base_strategy import Strategy
from src.strategies.data_models import Position, Signal, StrategyConfig


class S06DragonTigerStrategy(Strategy):
    """S06 Dragon Tiger (龙虎榜) 策略

    白皮书依据: 第六章 5.2 模块化军火库 - Meta-Following系

    策略逻辑：
    1. 解析每日龙虎榜数据
    2. 识别知名游资席位买入
    3. 分析买入金额和净买入
    4. 跟随建仓

    适用场景：
    - 游资主导的短线行情
    - 题材炒作初期
    - 龙头股接力
    """

    # 知名游资席位（示例）
    FAMOUS_SEATS: Set[str] = {
        "华泰证券深圳益田路",
        "东方财富拉萨团结路",
        "东方财富拉萨东环路",
        "国泰君安上海江苏路",
        "中信证券上海溧阳路",
        "华鑫证券上海宛平南路",
        "财通证券杭州上塘路",
        "国盛证券宁波桑田路",
    }

    def __init__(self, config: StrategyConfig):
        """初始化S06龙虎榜策略

        Args:
            config: 策略配置（Arena进化出的参数）
        """
        super().__init__(name="S06_Dragon_Tiger", config=config)

        # 策略特有参数
        self.min_buy_amount: float = 10_000_000  # 最低买入金额（1000万）
        self.min_net_buy_ratio: float = 0.3  # 最低净买入比例（30%）
        self.famous_seat_weight: float = 1.5  # 知名席位权重
        self.max_holding_days: int = 3  # 最大持仓天数

        logger.info(
            f"S06_Dragon_Tiger策略初始化 - "
            f"最低买入: {self.min_buy_amount/1e6:.0f}M, "
            f"净买入比例: {self.min_net_buy_ratio*100:.0f}%"
        )

    async def generate_signals(self, market_data: Dict[str, Any]) -> List[Signal]:
        """生成交易信号

        白皮书依据: Requirement 5.2

        信号生成逻辑：
        1. 解析龙虎榜数据
        2. 筛选知名席位买入
        3. 分析买入强度
        4. 生成跟随信号

        Args:
            market_data: 市场数据
                {
                    'dragon_tiger_data': Dict[str, Dict],  # 龙虎榜数据
                    'prices': Dict[str, Dict],  # 价格数据
                }

        Returns:
            交易信号列表
        """
        signals: List[Signal] = []

        dragon_tiger_data = market_data.get("dragon_tiger_data", {})
        prices = market_data.get("prices", {})

        for symbol, dt_data in dragon_tiger_data.items():
            try:
                signal = await self._analyze_dragon_tiger(symbol, dt_data, prices.get(symbol, {}))
                if signal:
                    signals.append(signal)
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.warning(f"分析{symbol}龙虎榜时出错: {e}")
                continue

        # 按置信度排序
        signals = sorted(signals, key=lambda x: x.confidence, reverse=True)[:5]

        logger.info(f"S06_Dragon_Tiger生成{len(signals)}个龙虎榜信号")
        return signals

    async def _analyze_dragon_tiger(
        self, symbol: str, dt_data: Dict[str, Any], price_data: Dict[str, Any]  # pylint: disable=unused-argument
    ) -> Optional[Signal]:
        """分析龙虎榜数据

        Args:
            symbol: 标的代码
            dt_data: 龙虎榜数据
            price_data: 价格数据

        Returns:
            交易信号或None
        """
        # 获取龙虎榜数据
        buy_seats = dt_data.get("buy_seats", [])  # 买入席位列表
        _ = dt_data.get("sell_seats", [])  # 卖出席位列表（用于计算净买入）
        total_buy = dt_data.get("total_buy", 0)  # 总买入金额
        total_sell = dt_data.get("total_sell", 0)  # 总卖出金额
        reason = dt_data.get("reason", "")  # 上榜原因

        if not buy_seats:
            return None

        # 分析买入席位
        famous_buy_amount = 0.0
        total_buy_amount = 0.0
        famous_seats_involved = []

        for seat in buy_seats:
            seat_name = seat.get("name", "")
            buy_amount = seat.get("buy_amount", 0)
            total_buy_amount += buy_amount

            if self._is_famous_seat(seat_name):
                famous_buy_amount += buy_amount
                famous_seats_involved.append(seat_name)

        # 条件1: 买入金额达标
        if total_buy_amount < self.min_buy_amount:
            return None

        # 条件2: 净买入为正
        net_buy = total_buy - total_sell
        if net_buy <= 0:
            return None

        # 条件3: 净买入比例达标
        net_buy_ratio = net_buy / total_buy if total_buy > 0 else 0
        if net_buy_ratio < self.min_net_buy_ratio:
            return None

        # 计算置信度
        confidence = self._calculate_dragon_tiger_confidence(
            total_buy_amount, net_buy_ratio, famous_buy_amount, len(famous_seats_involved)
        )

        seats_str = ", ".join(famous_seats_involved[:2]) if famous_seats_involved else "普通席位"
        reason_str = (
            f"龙虎榜买入{total_buy_amount/1e6:.1f}M, "
            f"净买入{net_buy_ratio*100:.0f}%, "
            f"席位: {seats_str}, "
            f"原因: {reason}"
        )

        logger.info(f"S06_Dragon_Tiger龙虎榜信号 - {symbol}: {reason_str}")

        return Signal(
            symbol=symbol, action="buy", confidence=confidence, timestamp=datetime.now().isoformat(), reason=reason_str
        )

    def _is_famous_seat(self, seat_name: str) -> bool:
        """判断是否为知名席位

        Args:
            seat_name: 席位名称

        Returns:
            是否为知名席位
        """
        for famous in self.FAMOUS_SEATS:
            if famous in seat_name:
                return True
        return False

    def _calculate_dragon_tiger_confidence(
        self, total_buy_amount: float, net_buy_ratio: float, famous_buy_amount: float, famous_seat_count: int
    ) -> float:
        """计算龙虎榜信号置信度

        Args:
            total_buy_amount: 总买入金额
            net_buy_ratio: 净买入比例
            famous_buy_amount: 知名席位买入金额
            famous_seat_count: 知名席位数量

        Returns:
            置信度 (0.0-1.0)
        """
        # 买入金额得分 (0-0.25)
        amount_score = min(0.25, (total_buy_amount - 10_000_000) / 100_000_000)

        # 净买入比例得分 (0-0.25)
        net_buy_score = min(0.25, (net_buy_ratio - 0.3) * 0.5)

        # 知名席位得分 (0-0.30)
        famous_ratio = famous_buy_amount / total_buy_amount if total_buy_amount > 0 else 0
        famous_score = min(0.30, famous_ratio * 0.4 + famous_seat_count * 0.05)

        # 席位数量得分 (0-0.10)
        seat_score = min(0.10, famous_seat_count * 0.03)

        confidence = amount_score + net_buy_score + famous_score + seat_score
        confidence = max(0.5, min(0.90, confidence + 0.45))

        return confidence

    async def calculate_position_sizes(self, signals: List[Signal]) -> List[Position]:
        """计算仓位大小

        白皮书依据: Requirement 5.3

        龙虎榜策略特点：
        - 短线操作
        - 快进快出
        - 仓位适中

        Args:
            signals: 交易信号列表

        Returns:
            仓位列表
        """
        positions: List[Position] = []

        sorted_signals = sorted(signals, key=lambda x: x.confidence, reverse=True)

        total_allocated = 0.0
        max_total = min(self.max_position, 0.30)  # 龙虎榜策略总仓位上限30%

        for signal in sorted_signals:
            if signal.action != "buy":
                continue

            base_size = self.max_single_stock * signal.confidence

            if total_allocated + base_size > max_total:
                base_size = max_total - total_allocated

            if base_size <= 0.01:
                break

            position = Position(
                symbol=signal.symbol,
                size=base_size,
                entry_price=100.0,  # 占位价格，实际交易时会被替换
                current_price=100.0,  # 占位价格，实际交易时会被替换
                pnl_pct=0.0,
                holding_days=0,
                industry="unknown",
            )

            positions.append(position)
            total_allocated += base_size

        logger.info(
            f"S06_Dragon_Tiger仓位计算完成 - " f"标的数: {len(positions)}, " f"总仓位: {total_allocated*100:.2f}%"
        )

        return positions
