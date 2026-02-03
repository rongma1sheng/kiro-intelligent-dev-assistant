"""S07 Morning Sniper (首板) - 集合竞价抢筹策略

白皮书依据: 第六章 5.2 模块化军火库 - Meta-Momentum系

策略特点：
- 集合竞价期间利用量比和舆情热度
- 抢筹潜在首板强势股
- 高风险高收益
"""

from datetime import datetime, time
from typing import Any, Dict, List, Optional

from loguru import logger

from src.strategies.base_strategy import Strategy
from src.strategies.data_models import Position, Signal, StrategyConfig


class S07MorningSniperStrategy(Strategy):
    """S07 Morning Sniper (首板) 策略

    白皮书依据: 第六章 5.2 模块化军火库 - Meta-Momentum系

    策略逻辑：
    1. 集合竞价期间（09:15-09:25）监控量比异动
    2. 结合舆情热度筛选潜在首板标的
    3. 09:25前下单抢筹
    4. 快进快出，当日止盈止损

    适用场景：
    - 题材热点爆发
    - 政策利好刺激
    - 板块龙头效应
    """

    def __init__(self, config: StrategyConfig):
        """初始化S07首板策略

        Args:
            config: 策略配置（Arena进化出的参数）
        """
        super().__init__(name="S07_Morning_Sniper", config=config)

        # 策略特有参数
        self.volume_ratio_threshold: float = 3.0  # 量比阈值
        self.sentiment_threshold: float = 0.7  # 舆情热度阈值
        self.bid_price_threshold: float = 0.05  # 竞价涨幅阈值（5%）
        self.max_bid_price: float = 0.095  # 最大竞价涨幅（9.5%，接近涨停）

        # 时间窗口
        self.auction_start = time(9, 15)
        self.auction_end = time(9, 25)
        self.order_deadline = time(9, 24, 30)  # 下单截止时间

        logger.info(
            f"S07_Morning_Sniper策略初始化 - "
            f"量比阈值: {self.volume_ratio_threshold}x, "
            f"舆情阈值: {self.sentiment_threshold}"
        )

    async def generate_signals(self, market_data: Dict[str, Any]) -> List[Signal]:
        """生成交易信号

        白皮书依据: Requirement 5.2

        信号生成逻辑：
        1. 检查是否在集合竞价时间窗口
        2. 筛选量比异动标的
        3. 结合舆情热度评分
        4. 生成抢筹信号

        Args:
            market_data: 市场数据
                {
                    'current_time': datetime,
                    'auction_data': Dict[str, Dict],  # 竞价数据
                    'sentiment_scores': Dict[str, float],  # 舆情评分
                    'hot_themes': List[str]  # 热点题材
                }

        Returns:
            交易信号列表
        """
        signals: List[Signal] = []

        current_time = market_data.get("current_time", datetime.now())

        # 检查是否在集合竞价时间窗口
        if not self._is_auction_time(current_time):
            logger.debug("非集合竞价时间，跳过信号生成")
            return signals

        # 检查是否超过下单截止时间
        if current_time.time() > self.order_deadline:
            logger.debug("已过下单截止时间，跳过信号生成")
            return signals

        auction_data = market_data.get("auction_data", {})
        sentiment_scores = market_data.get("sentiment_scores", {})
        hot_themes = market_data.get("hot_themes", [])

        for symbol, data in auction_data.items():
            try:
                signal = await self._analyze_auction(symbol, data, sentiment_scores.get(symbol, 0.5), hot_themes)
                if signal:
                    signals.append(signal)
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.warning(f"分析{symbol}竞价数据时出错: {e}")
                continue

        # 按置信度排序，只取前N个
        signals = sorted(signals, key=lambda x: x.confidence, reverse=True)[:5]

        logger.info(f"S07_Morning_Sniper生成{len(signals)}个首板信号")
        return signals

    def _is_auction_time(self, current_time: datetime) -> bool:
        """检查是否在集合竞价时间窗口

        Args:
            current_time: 当前时间

        Returns:
            是否在竞价时间
        """
        current = current_time.time()
        return self.auction_start <= current <= self.auction_end

    async def _analyze_auction(
        self, symbol: str, auction_data: Dict[str, Any], sentiment_score: float, hot_themes: List[str]
    ) -> Optional[Signal]:
        """分析竞价数据

        Args:
            symbol: 标的代码
            auction_data: 竞价数据
            sentiment_score: 舆情评分
            hot_themes: 热点题材

        Returns:
            交易信号或None
        """
        # 获取竞价数据
        volume_ratio = auction_data.get("volume_ratio", 0)
        bid_price_change = auction_data.get("bid_price_change", 0)
        auction_data.get("bid_volume", 0)
        prev_close = auction_data.get("prev_close", 0)
        themes = auction_data.get("themes", [])

        if prev_close <= 0:
            return None

        # 条件1: 量比异动
        volume_condition = volume_ratio >= self.volume_ratio_threshold

        # 条件2: 竞价涨幅在合理范围
        price_condition = self.bid_price_threshold <= bid_price_change <= self.max_bid_price

        # 条件3: 舆情热度
        sentiment_condition = sentiment_score >= self.sentiment_threshold

        # 条件4: 题材匹配热点
        theme_match = any(theme in hot_themes for theme in themes)

        # 综合判断（至少满足3个条件）
        conditions_met = sum([volume_condition, price_condition, sentiment_condition, theme_match])

        if conditions_met >= 3:
            confidence = self._calculate_auction_confidence(
                volume_ratio, bid_price_change, sentiment_score, theme_match
            )

            reason = (
                f"竞价量比{volume_ratio:.1f}x, "
                f"涨幅{bid_price_change*100:.2f}%, "
                f"舆情{sentiment_score:.2f}, "
                f"题材{'匹配' if theme_match else '未匹配'}"
            )

            logger.info(f"S07_Morning_Sniper首板信号 - {symbol}: {reason}")

            return Signal(
                symbol=symbol, action="buy", confidence=confidence, timestamp=datetime.now().isoformat(), reason=reason
            )

        return None

    def _calculate_auction_confidence(
        self, volume_ratio: float, bid_price_change: float, sentiment_score: float, theme_match: bool
    ) -> float:
        """计算竞价信号置信度

        Args:
            volume_ratio: 量比
            bid_price_change: 竞价涨幅
            sentiment_score: 舆情评分
            theme_match: 题材是否匹配

        Returns:
            置信度 (0.0-1.0)
        """
        # 量比得分 (0-0.3)
        volume_score = min(0.3, (volume_ratio - 3) * 0.05)

        # 涨幅得分 (0-0.25) - 涨幅适中最佳
        if 0.05 <= bid_price_change <= 0.07:
            price_score = 0.25
        elif 0.07 < bid_price_change <= 0.09:
            price_score = 0.20
        else:
            price_score = 0.15

        # 舆情得分 (0-0.25)
        sentiment_score_val = min(0.25, (sentiment_score - 0.5) * 0.5)

        # 题材得分 (0-0.2)
        theme_score = 0.2 if theme_match else 0.0

        confidence = volume_score + price_score + sentiment_score_val + theme_score
        confidence = max(0.5, min(0.95, confidence + 0.5))

        return confidence

    async def calculate_position_sizes(self, signals: List[Signal]) -> List[Position]:
        """计算仓位大小

        白皮书依据: Requirement 5.3

        首板策略特点：
        - 单股仓位较小（高风险）
        - 分散投资多个标的
        - 快进快出

        Args:
            signals: 交易信号列表

        Returns:
            仓位列表
        """
        positions: List[Position] = []

        # 首板策略单股仓位上限较低
        max_single = min(self.max_single_stock, 0.05)  # 最多5%

        # 按置信度排序
        sorted_signals = sorted(signals, key=lambda x: x.confidence, reverse=True)

        total_allocated = 0.0
        max_total = min(self.max_position, 0.20)  # 首板策略总仓位上限20%

        for signal in sorted_signals:
            if signal.action != "buy":
                continue

            # 根据置信度计算仓位
            base_size = max_single * signal.confidence

            # 检查总仓位限制
            if total_allocated + base_size > max_total:
                base_size = max_total - total_allocated

            if base_size <= 0.01:  # 最小仓位1%
                break

            position = Position(
                symbol=signal.symbol,
                size=base_size,
                entry_price=100.0,  # 占位价格
                current_price=100.0,  # 占位价格
                pnl_pct=0.0,
                holding_days=0,
                industry="unknown",
            )

            positions.append(position)
            total_allocated += base_size

            logger.debug(f"S07_Morning_Sniper仓位分配 - {signal.symbol}: " f"{base_size*100:.2f}%")

        logger.info(
            f"S07_Morning_Sniper仓位计算完成 - " f"标的数: {len(positions)}, " f"总仓位: {total_allocated*100:.2f}%"
        )

        return positions
