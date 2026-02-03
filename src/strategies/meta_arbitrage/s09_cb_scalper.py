"""S09 CB Scalper (可转债) - 可转债T+0极速交易策略

白皮书依据: 第六章 5.2 模块化军火库 - Meta-Arbitrage系

策略特点：
- 基于正股联动的T+0极速交易
- 利用可转债与正股的价格偏离
- 高频交易
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from loguru import logger

from src.strategies.base_strategy import Strategy
from src.strategies.data_models import Position, Signal, StrategyConfig


class S09CBScalperStrategy(Strategy):
    """S09 CB Scalper (可转债) 策略

    白皮书依据: 第六章 5.2 模块化军火库 - Meta-Arbitrage系

    策略逻辑：
    1. 监控可转债与正股的价格联动
    2. 识别价格偏离机会
    3. T+0快速交易
    4. 利用转股溢价率变化获利

    适用场景：
    - 正股大幅波动
    - 转股溢价率异常
    - 可转债流动性充足
    """

    def __init__(self, config: StrategyConfig):
        """初始化S09可转债策略

        Args:
            config: 策略配置（Arena进化出的参数）
        """
        super().__init__(name="S09_CB_Scalper", config=config)

        # 策略特有参数
        self.premium_threshold: float = 0.05  # 溢价率偏离阈值（5%）
        self.min_stock_change: float = 0.03  # 正股最小涨跌幅（3%）
        self.max_premium: float = 0.30  # 最大转股溢价率（30%）
        self.min_volume: float = 10_000_000  # 最小成交额（1000万）

        logger.info(
            f"S09_CB_Scalper策略初始化 - "
            f"溢价率阈值: {self.premium_threshold*100:.0f}%, "
            f"正股涨跌幅: {self.min_stock_change*100:.0f}%"
        )

    async def generate_signals(self, market_data: Dict[str, Any]) -> List[Signal]:
        """生成交易信号

        白皮书依据: Requirement 5.2

        Args:
            market_data: 市场数据

        Returns:
            交易信号列表
        """
        signals: List[Signal] = []

        cb_data = market_data.get("convertible_bonds", {})
        stock_data = market_data.get("stocks", {})

        for cb_code, cb_info in cb_data.items():
            try:
                signal = await self._analyze_cb_opportunity(cb_code, cb_info, stock_data)
                if signal:
                    signals.append(signal)
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.warning(f"分析{cb_code}可转债时出错: {e}")
                continue

        signals = sorted(signals, key=lambda x: x.confidence, reverse=True)[:5]
        logger.info(f"S09_CB_Scalper生成{len(signals)}个可转债信号")
        return signals

    async def _analyze_cb_opportunity(
        self, cb_code: str, cb_info: Dict[str, Any], stock_data: Dict[str, Any]
    ) -> Optional[Signal]:
        """分析可转债套利机会

        Args:
            cb_code: 可转债代码
            cb_info: 可转债信息
            stock_data: 正股数据

        Returns:
            交易信号或None
        """
        # 获取可转债数据
        cb_price = cb_info.get("price", 0)
        conversion_price = cb_info.get("conversion_price", 0)
        stock_code = cb_info.get("stock_code", "")
        cb_volume = cb_info.get("volume", 0)
        premium_rate = cb_info.get("premium_rate", 0)

        if cb_price <= 0 or conversion_price <= 0:
            return None

        # 获取正股数据
        stock_info = stock_data.get(stock_code, {})
        stock_price = stock_info.get("price", 0)
        stock_change = stock_info.get("change_pct", 0)

        if stock_price <= 0:
            return None

        # 计算转股价值
        conversion_value = (100 / conversion_price) * stock_price

        # 计算实际溢价率
        actual_premium = (cb_price - conversion_value) / conversion_value

        # 条件1: 成交额达标
        if cb_volume < self.min_volume:
            return None

        # 条件2: 溢价率在合理范围
        if actual_premium > self.max_premium:
            return None

        # 条件3: 正股有明显波动
        if abs(stock_change) < self.min_stock_change:
            return None

        # 判断交易方向
        action = "hold"
        if stock_change > self.min_stock_change and actual_premium < premium_rate - self.premium_threshold:
            # 正股上涨，可转债溢价率下降，买入可转债
            action = "buy"
        elif stock_change < -self.min_stock_change and actual_premium > premium_rate + self.premium_threshold:
            # 正股下跌，可转债溢价率上升，卖出可转债
            action = "sell"

        if action == "hold":
            return None

        confidence = self._calculate_cb_confidence(actual_premium, premium_rate, stock_change, cb_volume)

        reason = (
            f"正股{stock_code}涨跌{stock_change*100:.2f}%, "
            f"溢价率{actual_premium*100:.2f}%→{premium_rate*100:.2f}%, "
            f"成交额{cb_volume/1e6:.1f}M"
        )

        logger.info(f"S09_CB_Scalper可转债信号 - {cb_code}: {reason}")

        return Signal(
            symbol=cb_code, action=action, confidence=confidence, timestamp=datetime.now().isoformat(), reason=reason
        )

    def _calculate_cb_confidence(
        self, actual_premium: float, expected_premium: float, stock_change: float, volume: float
    ) -> float:
        """计算可转债信号置信度"""
        premium_diff = abs(actual_premium - expected_premium)
        premium_score = min(0.30, premium_diff * 3)
        stock_score = min(0.25, abs(stock_change) * 2.5)
        volume_score = min(0.25, (volume - 10_000_000) / 100_000_000)

        confidence = premium_score + stock_score + volume_score
        confidence = max(0.5, min(0.85, confidence + 0.4))
        return confidence

    async def calculate_position_sizes(self, signals: List[Signal]) -> List[Position]:
        """计算仓位大小"""
        positions: List[Position] = []
        total_allocated = 0.0
        max_total = min(self.max_position, 0.20)  # 可转债策略总仓位上限20%

        for signal in sorted(signals, key=lambda x: x.confidence, reverse=True):
            if signal.action not in ["buy", "sell"]:
                continue

            base_size = min(self.max_single_stock, 0.05) * signal.confidence

            if total_allocated + base_size > max_total:
                base_size = max_total - total_allocated

            if base_size <= 0.005:
                break

            positions.append(
                Position(
                    symbol=signal.symbol,
                    size=base_size,
                    entry_price=1.0,  # 占位价格，实际执行时更新
                    current_price=1.0,  # 占位价格，实际执行时更新
                    pnl_pct=0.0,
                    holding_days=0,
                    industry="convertible_bond",
                )
            )
            total_allocated += base_size

        logger.info(f"S09_CB_Scalper仓位计算完成 - 标的数: {len(positions)}, 总仓位: {total_allocated*100:.2f}%")
        return positions
