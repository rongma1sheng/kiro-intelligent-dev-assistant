"""S11 Fallen Angel (堕落天使) - 超跌反弹策略

白皮书依据: 第六章 5.2 模块化军火库 - Meta-MeanReversion系

策略特点：
- 捕捉基本面良好但因情绪错杀导致的超跌反弹
- 价值投资与技术分析结合
- 中长期持有
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from loguru import logger

from src.strategies.base_strategy import Strategy
from src.strategies.data_models import Position, Signal, StrategyConfig


class S11FallenAngelStrategy(Strategy):
    """S11 Fallen Angel (堕落天使) 策略

    白皮书依据: 第六章 5.2 模块化军火库 - Meta-MeanReversion系

    策略逻辑：
    1. 筛选基本面良好的标的（ROE>15%, PE<30）
    2. 识别因情绪错杀导致的超跌（跌幅>30%）
    3. 等待企稳信号
    4. 分批建仓，中长期持有

    适用场景：
    - 市场恐慌性下跌
    - 行业利空导致的错杀
    - 白马股的价值回归
    """

    def __init__(self, config: StrategyConfig):
        """初始化S11堕落天使策略

        Args:
            config: 策略配置（Arena进化出的参数）
        """
        super().__init__(name="S11_Fallen_Angel", config=config)

        # 基本面筛选参数
        self.min_roe: float = 0.15  # 最低ROE（15%）
        self.max_pe: float = 30.0  # 最高PE
        self.max_pb: float = 5.0  # 最高PB
        self.min_revenue_growth: float = 0.10  # 最低营收增长（10%）

        # 超跌判断参数
        self.oversold_threshold: float = -0.30  # 超跌阈值（-30%）
        self.lookback_period: int = 60  # 回看周期（60日）

        # 企稳信号参数
        self.stabilization_days: int = 3  # 企稳天数
        self.volume_recovery_threshold: float = 0.8  # 成交量恢复阈值

        logger.info(
            f"S11_Fallen_Angel策略初始化 - "
            f"ROE>{self.min_roe*100:.0f}%, "
            f"PE<{self.max_pe}, "
            f"超跌阈值: {self.oversold_threshold*100:.0f}%"
        )

    async def generate_signals(self, market_data: Dict[str, Any]) -> List[Signal]:
        """生成交易信号

        白皮书依据: Requirement 5.2

        信号生成逻辑：
        1. 基本面筛选
        2. 超跌判断
        3. 企稳确认
        4. 生成买入信号

        Args:
            market_data: 市场数据

        Returns:
            交易信号列表
        """
        signals: List[Signal] = []

        symbols = market_data.get("symbols", [])
        prices = market_data.get("prices", {})
        fundamentals = market_data.get("fundamentals", {})
        indicators = market_data.get("indicators", {})

        for symbol in symbols:
            try:
                signal = await self._analyze_fallen_angel(
                    symbol, prices.get(symbol, {}), fundamentals.get(symbol, {}), indicators.get(symbol, {})
                )
                if signal:
                    signals.append(signal)
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.warning(f"分析{symbol}堕落天使机会时出错: {e}")
                continue

        logger.info(f"S11_Fallen_Angel生成{len(signals)}个堕落天使信号")
        return signals

    async def _analyze_fallen_angel(
        self, symbol: str, price_data: Dict[str, Any], fundamental_data: Dict[str, Any], indicator_data: Dict[str, Any]
    ) -> Optional[Signal]:
        """分析堕落天使机会

        Args:
            symbol: 标的代码
            price_data: 价格数据
            fundamental_data: 基本面数据
            indicator_data: 技术指标数据

        Returns:
            交易信号或None
        """
        # 步骤1: 基本面筛选
        if not self._check_fundamentals(fundamental_data):
            return None

        # 步骤2: 超跌判断
        current_price = price_data.get("close", 0)
        high_60d = price_data.get("high_60d", 0)

        if current_price <= 0 or high_60d <= 0:
            return None

        drawdown = (current_price - high_60d) / high_60d

        if drawdown > self.oversold_threshold:
            return None  # 跌幅不够

        # 步骤3: 企稳确认
        if not self._check_stabilization(price_data, indicator_data):
            return None

        # 计算置信度
        confidence = self._calculate_fallen_angel_confidence(fundamental_data, drawdown, indicator_data)

        roe = fundamental_data.get("roe", 0)
        pe = fundamental_data.get("pe_ratio", 0)

        reason = f"基本面良好(ROE={roe*100:.1f}%, PE={pe:.1f}), " f"超跌{drawdown*100:.1f}%, " f"已企稳"

        logger.info(f"S11_Fallen_Angel堕落天使信号 - {symbol}: {reason}")

        return Signal(
            symbol=symbol, action="buy", confidence=confidence, timestamp=datetime.now().isoformat(), reason=reason
        )

    def _check_fundamentals(self, fundamental_data: Dict[str, Any]) -> bool:
        """检查基本面

        Args:
            fundamental_data: 基本面数据

        Returns:
            是否通过基本面筛选
        """
        roe = fundamental_data.get("roe", 0)
        pe = fundamental_data.get("pe_ratio", 100)
        pb = fundamental_data.get("pb_ratio", 10)
        revenue_growth = fundamental_data.get("revenue_growth", 0)

        # 排除ST和退市风险
        is_st = fundamental_data.get("is_st", False)
        delisting_risk = fundamental_data.get("delisting_risk", False)

        if is_st or delisting_risk:
            return False

        # 基本面条件
        roe_ok = roe >= self.min_roe
        pe_ok = 0 < pe <= self.max_pe
        pb_ok = 0 < pb <= self.max_pb
        growth_ok = revenue_growth >= self.min_revenue_growth

        # 至少满足3个条件
        conditions_met = sum([roe_ok, pe_ok, pb_ok, growth_ok])

        return conditions_met >= 3

    def _check_stabilization(self, price_data: Dict[str, Any], indicator_data: Dict[str, Any]) -> bool:
        """检查是否企稳

        Args:
            price_data: 价格数据
            indicator_data: 技术指标数据

        Returns:
            是否企稳
        """
        # 条件1: 连续N日未创新低
        low_3d = price_data.get("low_3d", 0)
        low_5d = price_data.get("low_5d", 0)
        no_new_low = low_3d >= low_5d * 0.99  # 允许1%误差

        # 条件2: RSI从超卖区回升
        rsi = indicator_data.get("rsi_14", 50)
        rsi_recovering = 30 < rsi < 50

        # 条件3: MACD底背离或金叉
        macd_hist = indicator_data.get("macd_hist", 0)
        macd_signal = indicator_data.get("macd_signal", 0)
        macd_bullish = macd_hist > macd_signal or macd_hist > 0

        # 条件4: 成交量恢复
        volume_ratio = indicator_data.get("volume_ratio_5d", 0)
        volume_recovering = volume_ratio >= self.volume_recovery_threshold

        # 至少满足2个条件
        conditions_met = sum([no_new_low, rsi_recovering, macd_bullish, volume_recovering])

        return conditions_met >= 2

    def _calculate_fallen_angel_confidence(
        self, fundamental_data: Dict[str, Any], drawdown: float, indicator_data: Dict[str, Any]
    ) -> float:
        """计算堕落天使信号置信度

        Args:
            fundamental_data: 基本面数据
            drawdown: 回撤幅度
            indicator_data: 技术指标数据

        Returns:
            置信度 (0.0-1.0)
        """
        # 基本面得分 (0-0.35)
        roe = fundamental_data.get("roe", 0)
        pe = fundamental_data.get("pe_ratio", 50)

        roe_score = min(0.15, (roe - 0.15) * 0.75)
        pe_score = min(0.20, (30 - pe) / 100) if pe > 0 else 0
        fundamental_score = roe_score + pe_score

        # 超跌程度得分 (0-0.30) - 跌得越多，反弹空间越大
        oversold_score = min(0.30, abs(drawdown + 0.30) * 0.75)

        # 技术面得分 (0-0.25)
        rsi = indicator_data.get("rsi_14", 50)
        rsi_score = min(0.15, (50 - rsi) / 200) if rsi < 50 else 0

        macd_hist = indicator_data.get("macd_hist", 0)
        macd_score = 0.10 if macd_hist > 0 else 0.05

        technical_score = rsi_score + macd_score

        confidence = fundamental_score + oversold_score + technical_score
        confidence = max(0.5, min(0.90, confidence + 0.4))

        return confidence

    async def calculate_position_sizes(self, signals: List[Signal]) -> List[Position]:
        """计算仓位大小

        白皮书依据: Requirement 5.3

        堕落天使策略特点：
        - 分批建仓
        - 中等仓位
        - 长期持有

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

            # 堕落天使策略仓位适中
            base_size = self.max_single_stock * signal.confidence * 0.8

            if total_allocated + base_size > self.max_position:
                base_size = self.max_position - total_allocated

            if base_size <= 0.01:
                break

            position = Position(
                symbol=signal.symbol,
                size=base_size,
                entry_price=0.0,
                current_price=0.0,
                pnl_pct=0.0,
                holding_days=0,
                industry="unknown",
            )

            positions.append(position)
            total_allocated += base_size

        logger.info(
            f"S11_Fallen_Angel仓位计算完成 - " f"标的数: {len(positions)}, " f"总仓位: {total_allocated*100:.2f}%"
        )

        return positions
