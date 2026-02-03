"""S13 Limit Down Reversal (地天板) - 跌停板翘板策略

白皮书依据: 第六章 5.2 模块化军火库 - Meta-Momentum系

策略特点：
- 极端行情下博弈跌停板翘板
- 高风险高收益
- 需要严格的风控
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from loguru import logger

from src.strategies.base_strategy import Strategy
from src.strategies.data_models import Position, Signal, StrategyConfig


class S13LimitDownReversalStrategy(Strategy):
    """S13 Limit Down Reversal (地天板) 策略

    白皮书依据: 第六章 5.2 模块化军火库 - Meta-Momentum系

    策略逻辑：
    1. 识别跌停板打开的标的
    2. 分析跌停原因（利空出尽 vs 持续利空）
    3. 监控资金流入和封单变化
    4. 博弈翘板反弹

    适用场景：
    - 利空出尽后的超跌反弹
    - 错杀股的价值回归
    - 情绪极端后的修复

    风险提示：
    - 极高风险策略
    - 需要严格止损
    - 仓位必须控制
    """

    def __init__(self, config: StrategyConfig):
        """初始化S13地天板策略

        Args:
            config: 策略配置（Arena进化出的参数）
        """
        super().__init__(name="S13_Limit_Down_Reversal", config=config)

        # 策略特有参数
        self.limit_down_threshold: float = -0.095  # 跌停阈值（-9.5%）
        self.open_threshold: float = -0.08  # 跌停打开阈值（-8%）
        self.volume_surge_threshold: float = 2.0  # 成交量放大阈值
        self.bid_volume_ratio: float = 1.5  # 买盘/卖盘比例阈值

        # 风控参数（更严格）
        self.max_single_position: float = min(config.max_single_stock, 0.03)  # 最多3%
        self.max_total_position: float = min(config.max_position, 0.10)  # 最多10%
        self.strict_stop_loss: float = -0.05  # 严格止损5%

        logger.info(
            f"S13_Limit_Down_Reversal策略初始化 - "
            f"跌停阈值: {self.limit_down_threshold*100:.1f}%, "
            f"单股上限: {self.max_single_position*100:.1f}%"
        )

    async def generate_signals(self, market_data: Dict[str, Any]) -> List[Signal]:
        """生成交易信号

        白皮书依据: Requirement 5.2

        信号生成逻辑：
        1. 筛选曾经跌停但已打开的标的
        2. 分析跌停原因和基本面
        3. 监控资金流入情况
        4. 生成翘板信号

        Args:
            market_data: 市场数据
                {
                    'limit_down_stocks': Dict[str, Dict],  # 跌停相关数据
                    'fundamentals': Dict[str, Dict],  # 基本面数据
                    'news_sentiment': Dict[str, Dict]  # 新闻情绪
                }

        Returns:
            交易信号列表
        """
        signals: List[Signal] = []

        limit_down_stocks = market_data.get("limit_down_stocks", {})
        fundamentals = market_data.get("fundamentals", {})
        news_sentiment = market_data.get("news_sentiment", {})

        for symbol, data in limit_down_stocks.items():
            try:
                signal = await self._analyze_limit_down(
                    symbol, data, fundamentals.get(symbol, {}), news_sentiment.get(symbol, {})
                )
                if signal:
                    signals.append(signal)
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.warning(f"分析{symbol}跌停数据时出错: {e}")
                continue

        # 严格限制信号数量
        signals = sorted(signals, key=lambda x: x.confidence, reverse=True)[:3]

        logger.info(f"S13_Limit_Down_Reversal生成{len(signals)}个翘板信号")
        return signals

    async def _analyze_limit_down(
        self, symbol: str, limit_data: Dict[str, Any], fundamental_data: Dict[str, Any], sentiment_data: Dict[str, Any]
    ) -> Optional[Signal]:
        """分析跌停标的

        Args:
            symbol: 标的代码
            limit_data: 跌停相关数据
            fundamental_data: 基本面数据
            sentiment_data: 情绪数据

        Returns:
            交易信号或None
        """
        # 获取跌停数据
        current_change = limit_data.get("price_change", 0)
        was_limit_down = limit_data.get("was_limit_down", False)
        is_open = limit_data.get("is_open", False)
        open_time = limit_data.get("open_time", "")
        volume_ratio = limit_data.get("volume_ratio", 0)
        bid_ask_ratio = limit_data.get("bid_ask_ratio", 0)
        limit_down_reason = limit_data.get("reason", "unknown")

        # 条件1: 曾经跌停但已打开
        if not (was_limit_down and is_open):
            return None

        # 条件2: 当前跌幅在合理范围（已从跌停回升）
        if current_change < self.open_threshold:
            return None

        # 条件3: 成交量放大（有资金介入）
        if volume_ratio < self.volume_surge_threshold:
            return None

        # 条件4: 买盘强于卖盘
        if bid_ask_ratio < self.bid_volume_ratio:
            return None

        # 条件5: 排除持续利空（基本面检查）
        if self._is_continuous_negative(fundamental_data, sentiment_data):
            logger.debug(f"{symbol} 存在持续利空，跳过")
            return None

        # 计算置信度
        confidence = self._calculate_reversal_confidence(
            current_change, volume_ratio, bid_ask_ratio, fundamental_data, sentiment_data
        )

        reason = (
            f"跌停打开于{open_time}, "
            f"当前跌幅{current_change*100:.2f}%, "
            f"量比{volume_ratio:.1f}x, "
            f"买卖比{bid_ask_ratio:.2f}, "
            f"原因: {limit_down_reason}"
        )

        logger.info(f"S13_Limit_Down_Reversal翘板信号 - {symbol}: {reason}")

        return Signal(
            symbol=symbol, action="buy", confidence=confidence, timestamp=datetime.now().isoformat(), reason=reason
        )

    def _is_continuous_negative(self, fundamental_data: Dict[str, Any], sentiment_data: Dict[str, Any]) -> bool:
        """判断是否存在持续利空

        Args:
            fundamental_data: 基本面数据
            sentiment_data: 情绪数据

        Returns:
            是否存在持续利空
        """
        # 检查基本面风险
        is_st = fundamental_data.get("is_st", False)
        is_delisting_risk = fundamental_data.get("delisting_risk", False)
        consecutive_loss = fundamental_data.get("consecutive_loss_quarters", 0) >= 2

        # 检查情绪风险
        negative_news_count = sentiment_data.get("negative_news_count", 0)
        sentiment_score = sentiment_data.get("sentiment_score", 0.5)

        # 任一条件满足则认为存在持续利空
        if is_st or is_delisting_risk or consecutive_loss:
            return True

        if negative_news_count >= 3 and sentiment_score < 0.3:
            return True

        return False

    def _calculate_reversal_confidence(  # pylint: disable=too-many-positional-arguments
        self,
        current_change: float,
        volume_ratio: float,
        bid_ask_ratio: float,
        fundamental_data: Dict[str, Any],
        sentiment_data: Dict[str, Any],
    ) -> float:
        """计算翘板信号置信度

        Args:
            current_change: 当前涨跌幅
            volume_ratio: 量比
            bid_ask_ratio: 买卖比
            fundamental_data: 基本面数据
            sentiment_data: 情绪数据

        Returns:
            置信度 (0.0-1.0)
        """
        # 回升幅度得分 (0-0.25)
        recovery = current_change - self.limit_down_threshold
        recovery_score = min(0.25, recovery * 2.5)

        # 成交量得分 (0-0.25)
        volume_score = min(0.25, (volume_ratio - 2) * 0.125)

        # 买卖比得分 (0-0.25)
        bid_ask_score = min(0.25, (bid_ask_ratio - 1) * 0.25)

        # 基本面得分 (0-0.15)
        pe_ratio = fundamental_data.get("pe_ratio", 50)
        pb_ratio = fundamental_data.get("pb_ratio", 5)
        fundamental_score = 0.0
        if 0 < pe_ratio < 30 and 0 < pb_ratio < 3:
            fundamental_score = 0.15
        elif 0 < pe_ratio < 50 and 0 < pb_ratio < 5:
            fundamental_score = 0.10

        # 情绪得分 (0-0.10)
        sentiment_score = sentiment_data.get("sentiment_score", 0.5)
        sentiment_val = min(0.10, (sentiment_score - 0.3) * 0.25)

        confidence = recovery_score + volume_score + bid_ask_score + fundamental_score + sentiment_val

        # 地天板策略置信度上限较低（高风险）
        confidence = max(0.4, min(0.75, confidence + 0.3))

        return confidence

    async def calculate_position_sizes(self, signals: List[Signal]) -> List[Position]:
        """计算仓位大小

        白皮书依据: Requirement 5.3

        地天板策略特点：
        - 极小仓位（高风险）
        - 严格分散
        - 快进快出

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

            # 根据置信度计算仓位（极小）
            base_size = self.max_single_position * signal.confidence

            # 检查总仓位限制
            if total_allocated + base_size > self.max_total_position:
                base_size = self.max_total_position - total_allocated

            if base_size <= 0.005:  # 最小仓位0.5%
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

            logger.debug(f"S13_Limit_Down_Reversal仓位分配 - {signal.symbol}: " f"{base_size*100:.2f}%")

        logger.info(
            f"S13_Limit_Down_Reversal仓位计算完成 - "
            f"标的数: {len(positions)}, "
            f"总仓位: {total_allocated*100:.2f}%"
        )

        return positions

    async def apply_risk_controls(self, positions: List[Position]) -> List[Position]:
        """应用风险控制（覆盖基类方法，使用更严格的止损）

        Args:
            positions: 原始仓位列表

        Returns:
            过滤后的仓位列表
        """
        # 先调用基类的风险控制
        filtered = await super().apply_risk_controls(positions)

        # 地天板策略使用更严格的止损
        if filtered and hasattr(self, "risk_manager"):
            # 强制使用严格止损
            self.risk_manager.stop_loss_pct = self.strict_stop_loss

        logger.info(f"S13_Limit_Down_Reversal风险控制 - " f"使用严格止损: {self.strict_stop_loss*100:.1f}%")

        return filtered
