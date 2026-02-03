"""S01 Retracement (回马枪) - 强势股回调潜伏策略

白皮书依据: 第六章 5.2 模块化军火库 - Meta-MeanReversion系

策略特点：
- 监控强势股缩量回调至关键均线
- 潜伏等待反弹
- 中等风险中等收益
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from loguru import logger

from src.strategies.base_strategy import Strategy
from src.strategies.data_models import Position, Signal, StrategyConfig


class S01RetracementStrategy(Strategy):
    """S01 Retracement (回马枪) 策略

    白皮书依据: 第六章 5.2 模块化军火库 - Meta-MeanReversion系

    策略逻辑：
    1. 筛选近期强势股（20日涨幅>20%）
    2. 监控缩量回调至MA10/MA20
    3. 等待企稳信号（K线形态）
    4. 潜伏建仓

    适用场景：
    - 强势股正常回调
    - 板块轮动中的龙头回踩
    - 趋势股的二次买点
    """

    def __init__(self, config: StrategyConfig):
        """初始化S01回马枪策略

        Args:
            config: 策略配置（Arena进化出的参数）
        """
        super().__init__(name="S01_Retracement", config=config)

        # 策略特有参数
        self.strong_stock_threshold: float = 0.20  # 强势股涨幅阈值（20%）
        self.lookback_period: int = 20  # 回看周期
        self.ma_periods: List[int] = [10, 20]  # 关键均线
        self.volume_shrink_threshold: float = 0.6  # 缩量阈值（60%）
        self.retracement_threshold: float = 0.10  # 回调幅度阈值（10%）

        logger.info(
            f"S01_Retracement策略初始化 - "
            f"强势股阈值: {self.strong_stock_threshold*100:.0f}%, "
            f"均线周期: {self.ma_periods}"
        )

    async def generate_signals(self, market_data: Dict[str, Any]) -> List[Signal]:
        """生成交易信号

        白皮书依据: Requirement 5.2

        信号生成逻辑：
        1. 筛选强势股
        2. 检测回调至均线
        3. 确认缩量
        4. 识别企稳形态

        Args:
            market_data: 市场数据

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
                signal = await self._analyze_retracement(
                    symbol, prices.get(symbol, {}), volumes.get(symbol, {}), indicators.get(symbol, {})
                )
                if signal:
                    signals.append(signal)
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.warning(f"分析{symbol}回调时出错: {e}")
                continue

        logger.info(f"S01_Retracement生成{len(signals)}个回马枪信号")
        return signals

    async def _analyze_retracement(
        self, symbol: str, price_data: Dict[str, Any], volume_data: Dict[str, Any], indicator_data: Dict[str, Any]
    ) -> Optional[Signal]:
        """分析回调机会

        Args:
            symbol: 标的代码
            price_data: 价格数据
            volume_data: 成交量数据
            indicator_data: 技术指标数据

        Returns:
            交易信号或None
        """
        # 获取数据
        current_price = price_data.get("close", 0)
        high_20d = price_data.get("high_20d", 0)
        low_20d = price_data.get("low_20d", 0)
        price_20d_ago = price_data.get("close_20d_ago", 0)
        ma10 = indicator_data.get("ma_10", 0)
        ma20 = indicator_data.get("ma_20", 0)
        current_volume = volume_data.get("volume", 0)
        avg_volume = volume_data.get("avg_volume_20d", 1)

        if current_price <= 0 or price_20d_ago <= 0:
            return None

        # 条件1: 近期强势（20日涨幅>20%）
        gain_20d = (high_20d - low_20d) / low_20d if low_20d > 0 else 0
        is_strong = gain_20d >= self.strong_stock_threshold

        if not is_strong:
            return None

        # 条件2: 回调至均线附近
        near_ma10 = abs(current_price - ma10) / ma10 < 0.02 if ma10 > 0 else False
        near_ma20 = abs(current_price - ma20) / ma20 < 0.02 if ma20 > 0 else False
        near_ma = near_ma10 or near_ma20

        if not near_ma:
            return None

        # 条件3: 缩量回调
        volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1
        is_shrinking = volume_ratio < self.volume_shrink_threshold

        if not is_shrinking:
            return None

        # 条件4: 回调幅度合理
        retracement = (high_20d - current_price) / high_20d if high_20d > 0 else 0
        reasonable_retracement = 0.05 <= retracement <= self.retracement_threshold

        if not reasonable_retracement:
            return None

        # 计算置信度
        confidence = self._calculate_retracement_confidence(gain_20d, retracement, volume_ratio, near_ma10, near_ma20)

        ma_type = "MA10" if near_ma10 else "MA20"
        reason = (
            f"强势股回调至{ma_type}, "
            f"20日涨幅{gain_20d*100:.1f}%, "
            f"回调{retracement*100:.1f}%, "
            f"量比{volume_ratio:.2f}"
        )

        logger.info(f"S01_Retracement回马枪信号 - {symbol}: {reason}")

        return Signal(
            symbol=symbol, action="buy", confidence=confidence, timestamp=datetime.now().isoformat(), reason=reason
        )

    def _calculate_retracement_confidence(  # pylint: disable=too-many-positional-arguments
        self,
        gain_20d: float,
        retracement: float,
        volume_ratio: float,
        near_ma10: bool,
        near_ma20: bool,  # pylint: disable=unused-argument
    ) -> float:
        """计算回马枪信号置信度

        Args:
            gain_20d: 20日涨幅
            retracement: 回调幅度
            volume_ratio: 量比
            near_ma10: 是否接近MA10
            near_ma20: 是否接近MA20

        Returns:
            置信度 (0.0-1.0)
        """
        # 强势程度得分 (0-0.3)
        strength_score = min(0.3, (gain_20d - 0.2) * 1.5)

        # 回调幅度得分 (0-0.25) - 回调5-8%最佳
        if 0.05 <= retracement <= 0.08:
            retracement_score = 0.25
        elif 0.08 < retracement <= 0.10:
            retracement_score = 0.20
        else:
            retracement_score = 0.15

        # 缩量程度得分 (0-0.25)
        shrink_score = min(0.25, (0.6 - volume_ratio) * 0.5)

        # 均线支撑得分 (0-0.2)
        ma_score = 0.2 if near_ma10 else 0.15  # MA10支撑更强

        confidence = strength_score + retracement_score + shrink_score + ma_score
        confidence = max(0.5, min(0.90, confidence + 0.4))

        return confidence

    async def calculate_position_sizes(self, signals: List[Signal]) -> List[Position]:
        """计算仓位大小

        白皮书依据: Requirement 5.3

        回马枪策略特点：
        - 中等仓位
        - 分批建仓
        - 耐心持有

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

            # 根据置信度计算仓位
            base_size = self.max_single_stock * signal.confidence

            if total_allocated + base_size > self.max_position:
                base_size = self.max_position - total_allocated

            if base_size <= 0.01:
                break

            position = Position(
                symbol=signal.symbol,
                size=base_size,
                entry_price=100.0,  # Placeholder price
                current_price=100.0,  # Placeholder price
                pnl_pct=0.0,
                holding_days=0,
                industry="unknown",
            )

            positions.append(position)
            total_allocated += base_size

        logger.info(
            f"S01_Retracement仓位计算完成 - " f"标的数: {len(positions)}, " f"总仓位: {total_allocated*100:.2f}%"
        )

        return positions
