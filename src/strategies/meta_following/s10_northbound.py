"""S10 Northbound (北向) - 北向资金跟随策略

白皮书依据: 第六章 5.2 模块化军火库 - Meta-Following系

策略特点：
- 实时监控北向资金流向
- 跟随外资重仓股
- 中长期持有
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from loguru import logger

from src.strategies.base_strategy import Strategy
from src.strategies.data_models import Position, Signal, StrategyConfig


class S10NorthboundStrategy(Strategy):
    """S10 Northbound (北向) 策略

    白皮书依据: 第六章 5.2 模块化军火库 - Meta-Following系

    策略逻辑：
    1. 实时监控北向资金流向
    2. 识别外资持续加仓标的
    3. 分析持仓变化和流入强度
    4. 跟随建仓

    适用场景：
    - 外资主导的价值投资行情
    - 核心资产配置
    - 中长期投资
    """

    def __init__(self, config: StrategyConfig):
        """初始化S10北向策略

        Args:
            config: 策略配置（Arena进化出的参数）
        """
        super().__init__(name="S10_Northbound", config=config)

        # 策略特有参数
        self.min_holding_ratio: float = 0.01  # 最低持股比例（1%）
        self.min_inflow_days: int = 3  # 最少连续流入天数
        self.min_daily_inflow: float = 50_000_000  # 最低日流入金额（5000万）
        self.holding_change_threshold: float = 0.001  # 持仓变化阈值（0.1%）

        logger.info(
            f"S10_Northbound策略初始化 - "
            f"最低持股比例: {self.min_holding_ratio*100:.1f}%, "
            f"连续流入天数: {self.min_inflow_days}"
        )

    async def generate_signals(self, market_data: Dict[str, Any]) -> List[Signal]:
        """生成交易信号

        白皮书依据: Requirement 5.2

        信号生成逻辑：
        1. 获取北向资金持仓数据
        2. 筛选持续加仓标的
        3. 分析流入强度
        4. 生成跟随信号

        Args:
            market_data: 市场数据
                {
                    'northbound_data': Dict[str, Dict],  # 北向资金数据
                    'prices': Dict[str, Dict],  # 价格数据
                    'fundamentals': Dict[str, Dict]  # 基本面数据
                }

        Returns:
            交易信号列表
        """
        signals: List[Signal] = []

        northbound_data = market_data.get("northbound_data", {})
        prices = market_data.get("prices", {})
        fundamentals = market_data.get("fundamentals", {})

        for symbol, nb_data in northbound_data.items():
            try:
                signal = await self._analyze_northbound(
                    symbol, nb_data, prices.get(symbol, {}), fundamentals.get(symbol, {})
                )
                if signal:
                    signals.append(signal)
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.warning(f"分析{symbol}北向资金时出错: {e}")
                continue

        # 按置信度排序
        signals = sorted(signals, key=lambda x: x.confidence, reverse=True)[:10]

        logger.info(f"S10_Northbound生成{len(signals)}个北向信号")
        return signals

    async def _analyze_northbound(
        self, symbol: str, nb_data: Dict[str, Any], _price_data: Dict[str, Any], fundamental_data: Dict[str, Any]
    ) -> Optional[Signal]:
        """分析北向资金数据

        Args:
            symbol: 标的代码
            nb_data: 北向资金数据
            price_data: 价格数据
            fundamental_data: 基本面数据

        Returns:
            交易信号或None
        """
        # 获取北向资金数据
        holding_ratio = nb_data.get("holding_ratio", 0)  # 持股比例
        holding_change = nb_data.get("holding_change_5d", 0)  # 5日持仓变化
        consecutive_inflow_days = nb_data.get("consecutive_inflow_days", 0)  # 连续流入天数
        daily_inflow = nb_data.get("daily_inflow", 0)  # 日流入金额
        _ = nb_data.get("total_holding_value", 0)  # 总持仓市值（用于后续扩展）

        # 条件1: 持股比例达标
        if holding_ratio < self.min_holding_ratio:
            return None

        # 条件2: 连续流入天数达标
        if consecutive_inflow_days < self.min_inflow_days:
            return None

        # 条件3: 日流入金额达标
        if daily_inflow < self.min_daily_inflow:
            return None

        # 条件4: 持仓变化为正
        if holding_change < self.holding_change_threshold:
            return None

        # 计算置信度
        confidence = self._calculate_northbound_confidence(
            holding_ratio, holding_change, consecutive_inflow_days, daily_inflow, fundamental_data
        )

        reason = (
            f"北向持股{holding_ratio*100:.2f}%, "
            f"5日增持{holding_change*100:.3f}%, "
            f"连续流入{consecutive_inflow_days}天, "
            f"日流入{daily_inflow/1e6:.1f}M"
        )

        logger.info(f"S10_Northbound北向信号 - {symbol}: {reason}")

        return Signal(
            symbol=symbol, action="buy", confidence=confidence, timestamp=datetime.now().isoformat(), reason=reason
        )

    def _calculate_northbound_confidence(  # pylint: disable=too-many-positional-arguments
        self,
        holding_ratio: float,
        holding_change: float,
        consecutive_inflow_days: int,
        daily_inflow: float,
        fundamental_data: Dict[str, Any],
    ) -> float:
        """计算北向信号置信度

        Args:
            holding_ratio: 持股比例
            holding_change: 持仓变化
            consecutive_inflow_days: 连续流入天数
            daily_inflow: 日流入金额
            fundamental_data: 基本面数据

        Returns:
            置信度 (0.0-1.0)
        """
        # 持股比例得分 (0-0.25)
        ratio_score = min(0.25, holding_ratio * 2.5)

        # 持仓变化得分 (0-0.20)
        change_score = min(0.20, holding_change * 20)

        # 连续流入得分 (0-0.20)
        inflow_days_score = min(0.20, consecutive_inflow_days * 0.04)

        # 日流入金额得分 (0-0.20)
        inflow_score = min(0.20, (daily_inflow - 50_000_000) / 500_000_000)

        # 基本面得分 (0-0.15)
        roe = fundamental_data.get("roe", 0)
        pe = fundamental_data.get("pe_ratio", 50)
        fundamental_score = 0.0
        if roe > 0.15 and 0 < pe < 30:
            fundamental_score = 0.15
        elif roe > 0.10 and 0 < pe < 50:
            fundamental_score = 0.10

        confidence = ratio_score + change_score + inflow_days_score + inflow_score + fundamental_score
        confidence = max(0.5, min(0.90, confidence + 0.4))

        return confidence

    async def calculate_position_sizes(self, signals: List[Signal]) -> List[Position]:
        """计算仓位大小

        白皮书依据: Requirement 5.3

        北向策略特点：
        - 中长期持有
        - 仓位较大
        - 分散投资

        Args:
            signals: 交易信号列表

        Returns:
            仓位列表
        """
        positions: List[Position] = []

        sorted_signals = sorted(signals, key=lambda x: x.confidence, reverse=True)

        total_allocated = 0.0

        for signal in sorted_signals:
            if signal.action != "buy":
                continue

            # 北向策略仓位较大
            base_size = self.max_single_stock * signal.confidence

            if total_allocated + base_size > self.max_position:
                base_size = self.max_position - total_allocated

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
            f"S10_Northbound仓位计算完成 - " f"标的数: {len(positions)}, " f"总仓位: {total_allocated*100:.2f}%"
        )

        return positions
