"""S02 Aggressive (激进) - 动量驱动的趋势跟踪策略

白皮书依据: 第六章 5.2 模块化军火库 - Meta-Momentum系

策略特点：
- 动量驱动的趋势跟踪
- 专注于突破关键阻力位
- 适合强势市场环境
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from loguru import logger

from src.strategies.base_strategy import Strategy
from src.strategies.data_models import Position, Signal, StrategyConfig


class S02AggressiveStrategy(Strategy):
    """S02 Aggressive (激进) 策略

    白皮书依据: 第六章 5.2 模块化军火库 - Meta-Momentum系

    策略逻辑：
    1. 识别价格突破关键阻力位（20日高点）
    2. 结合成交量放大确认突破有效性
    3. 动量指标（RSI、MACD）确认趋势强度
    4. 快速建仓，追踪趋势

    适用场景：
    - 牛市或强势反弹行情
    - 板块轮动初期
    - 个股突破整理平台
    """

    def __init__(self, config: StrategyConfig):
        """初始化S02激进策略

        Args:
            config: 策略配置（Arena进化出的参数）
        """
        super().__init__(name="S02_Aggressive", config=config)

        # 策略特有参数
        self.breakout_period: int = 20  # 突破周期（20日高点）
        self.volume_multiplier: float = 1.5  # 成交量放大倍数
        self.rsi_threshold: float = 50.0  # RSI阈值
        self.momentum_window: int = 10  # 动量计算窗口

        logger.info(
            f"S02_Aggressive策略初始化 - "
            f"突破周期: {self.breakout_period}日, "
            f"成交量倍数: {self.volume_multiplier}x"
        )

    async def generate_signals(self, market_data: Dict[str, Any]) -> List[Signal]:
        """生成交易信号

        白皮书依据: Requirement 5.2

        信号生成逻辑：
        1. 价格突破N日高点
        2. 成交量 > 均量 * volume_multiplier
        3. RSI > rsi_threshold
        4. MACD金叉或柱状图放大

        Args:
            market_data: 市场数据
                {
                    'symbols': List[str],  # 标的列表
                    'prices': Dict[str, Dict],  # 价格数据
                    'volumes': Dict[str, Dict],  # 成交量数据
                    'indicators': Dict[str, Dict]  # 技术指标
                }

        Returns:
            交易信号列表
        """
        signals: List[Signal] = []

        symbols = market_data.get("symbols", [])
        prices = market_data.get("prices", {})
        volumes = market_data.get("volumes", {})
        indicators = market_data.get("indicators", {})

        for symbol in symbols:
            try:
                signal = await self._analyze_symbol(
                    symbol, prices.get(symbol, {}), volumes.get(symbol, {}), indicators.get(symbol, {})
                )
                if signal:
                    signals.append(signal)
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.warning(f"分析{symbol}时出错: {e}")
                continue

        logger.info(f"S02_Aggressive生成{len(signals)}个信号")
        return signals

    async def _analyze_symbol(
        self, symbol: str, price_data: Dict[str, Any], volume_data: Dict[str, Any], indicator_data: Dict[str, Any]
    ) -> Optional[Signal]:
        """分析单个标的

        Args:
            symbol: 标的代码
            price_data: 价格数据
            volume_data: 成交量数据
            indicator_data: 技术指标数据

        Returns:
            交易信号或None
        """
        # 获取必要数据
        current_price = price_data.get("close", 0)
        high_20d = price_data.get("high_20d", 0)
        current_volume = volume_data.get("volume", 0)
        avg_volume = volume_data.get("avg_volume_20d", 1)
        rsi = indicator_data.get("rsi_14", 50)
        macd_hist = indicator_data.get("macd_hist", 0)

        if current_price <= 0 or high_20d <= 0:
            return None

        # 条件1: 价格突破20日高点
        breakout = current_price > high_20d

        # 条件2: 成交量放大
        volume_surge = current_volume > avg_volume * self.volume_multiplier

        # 条件3: RSI确认
        rsi_confirm = rsi > self.rsi_threshold

        # 条件4: MACD确认
        macd_confirm = macd_hist > 0

        # 综合判断
        if breakout and volume_surge and rsi_confirm and macd_confirm:
            # 计算置信度
            confidence = self._calculate_confidence(current_price, high_20d, current_volume, avg_volume, rsi, macd_hist)

            reason = (
                f"突破{self.breakout_period}日高点{high_20d:.2f}, "
                f"成交量{current_volume/avg_volume:.1f}倍, "
                f"RSI={rsi:.1f}, MACD柱={macd_hist:.4f}"
            )

            logger.info(f"S02_Aggressive买入信号 - {symbol}: {reason}")

            return Signal(
                symbol=symbol, action="buy", confidence=confidence, timestamp=datetime.now().isoformat(), reason=reason
            )

        return None

    def _calculate_confidence(  # pylint: disable=too-many-positional-arguments
        self,
        current_price: float,
        high_20d: float,
        current_volume: float,
        avg_volume: float,
        rsi: float,
        macd_hist: float,
    ) -> float:
        """计算信号置信度

        Args:
            current_price: 当前价格
            high_20d: 20日高点
            current_volume: 当前成交量
            avg_volume: 平均成交量
            rsi: RSI值
            macd_hist: MACD柱状图

        Returns:
            置信度 (0.0-1.0)
        """
        # 突破幅度得分 (0-0.3)
        breakout_pct = (current_price - high_20d) / high_20d
        breakout_score = min(0.3, breakout_pct * 3)

        # 成交量得分 (0-0.3)
        volume_ratio = current_volume / avg_volume
        volume_score = min(0.3, (volume_ratio - 1) * 0.15)

        # RSI得分 (0-0.2)
        rsi_score = min(0.2, (rsi - 50) / 250)

        # MACD得分 (0-0.2)
        macd_score = min(0.2, abs(macd_hist) * 10)

        confidence = breakout_score + volume_score + rsi_score + macd_score
        confidence = max(0.5, min(0.95, confidence + 0.5))  # 基础置信度0.5

        return confidence

    async def calculate_position_sizes(self, signals: List[Signal]) -> List[Position]:
        """计算仓位大小

        白皮书依据: Requirement 5.3

        激进策略特点：
        - 高置信度信号给予更大仓位
        - 单股仓位上限由config控制
        - 总仓位不超过max_position

        Args:
            signals: 交易信号列表

        Returns:
            仓位列表
        """
        positions: List[Position] = []

        # 按置信度排序
        sorted_signals = sorted(signals, key=lambda x: x.confidence, reverse=True)

        total_allocated = 0.0

        for signal in sorted_signals:
            if signal.action != "buy":
                continue

            # 根据置信度计算仓位
            base_size = self.max_single_stock * signal.confidence

            # 检查总仓位限制
            if total_allocated + base_size > self.max_position:
                base_size = self.max_position - total_allocated

            if base_size <= 0:
                break

            position = Position(
                symbol=signal.symbol,
                size=base_size,
                entry_price=100.0,  # 占位价格，实际交易时会被替换
                current_price=100.0,  # 占位价格，实际交易时会被替换
                pnl_pct=0.0,
                holding_days=0,
                industry="unknown",  # 实际执行时填充
            )

            positions.append(position)
            total_allocated += base_size

            logger.debug(
                f"S02_Aggressive仓位分配 - {signal.symbol}: " f"{base_size*100:.2f}%, 置信度={signal.confidence:.2f}"
            )

        logger.info(
            f"S02_Aggressive仓位计算完成 - " f"标的数: {len(positions)}, " f"总仓位: {total_allocated*100:.2f}%"
        )

        return positions
