"""S16 Theme Hunter (题材猎手) - 热点题材挖掘策略

白皮书依据: 第六章 5.2 模块化军火库 - Meta-Event系

策略特点：
- 基于Scholar引擎爬取的研报与舆情
- 驱动热点题材挖掘
- 捕捉市场热点轮动
"""

from datetime import datetime
from typing import Any, Dict, List, Set

from loguru import logger

from src.strategies.base_strategy import Strategy
from src.strategies.data_models import Position, Signal, StrategyConfig


class S16ThemeHunterStrategy(Strategy):
    """S16 Theme Hunter (题材猎手) 策略

    白皮书依据: 第六章 5.2 模块化军火库 - Meta-Event系

    策略逻辑：
    1. 监控Scholar引擎爬取的研报和舆情
    2. 识别热点题材和概念
    3. 筛选题材内的龙头股
    4. 跟踪题材轮动节奏

    适用场景：
    - 政策利好发布
    - 行业重大事件
    - 市场热点轮动
    - 概念炒作初期
    """

    def __init__(self, config: StrategyConfig):
        """初始化S16题材猎手策略

        Args:
            config: 策略配置（Arena进化出的参数）
        """
        super().__init__(name="S16_Theme_Hunter", config=config)

        # 策略特有参数
        self.theme_heat_threshold: float = 0.6  # 题材热度阈值
        self.news_count_threshold: int = 10  # 新闻数量阈值
        self.report_count_threshold: int = 3  # 研报数量阈值
        self.leader_rank_threshold: int = 5  # 龙头股排名阈值

        # 题材持续性参数
        self.theme_duration_days: int = 5  # 题材持续天数
        self.cooldown_days: int = 3  # 题材冷却天数

        # 已追踪的题材
        self.tracked_themes: Dict[str, Dict[str, Any]] = {}

        # 题材黑名单（已过热或已衰退）
        self.theme_blacklist: Set[str] = set()

        logger.info(
            f"S16_Theme_Hunter策略初始化 - "
            f"热度阈值: {self.theme_heat_threshold}, "
            f"新闻阈值: {self.news_count_threshold}"
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

        # 获取Scholar引擎数据
        scholar_data = market_data.get("scholar", {})
        research_reports = scholar_data.get("research_reports", [])
        news_data = scholar_data.get("news", [])
        sentiment_data = market_data.get("sentiment", {})

        # 识别热点题材
        hot_themes = await self._identify_hot_themes(research_reports, news_data, sentiment_data)

        # 更新题材追踪
        await self._update_theme_tracking(hot_themes)

        # 为每个热点题材生成信号
        for theme in hot_themes:
            try:
                theme_signals = await self._generate_theme_signals(theme, market_data)
                signals.extend(theme_signals)
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.warning(f"生成题材{theme.get('name', '')}信号时出错: {e}")
                continue

        signals = sorted(signals, key=lambda x: x.confidence, reverse=True)[:5]
        logger.info(f"S16_Theme_Hunter生成{len(signals)}个题材信号")
        return signals

    async def _identify_hot_themes(
        self,
        research_reports: List[Dict[str, Any]],
        news_data: List[Dict[str, Any]],
        sentiment_data: Dict[str, Any],  # pylint: disable=unused-argument
    ) -> List[Dict[str, Any]]:
        """识别热点题材

        Args:
            research_reports: 研报数据
            news_data: 新闻数据
            sentiment_data: 舆情数据

        Returns:
            热点题材列表
        """
        theme_scores: Dict[str, Dict[str, Any]] = {}

        # 从研报中提取题材
        for report in research_reports:
            themes = report.get("themes", [])
            for theme in themes:
                if theme not in theme_scores:
                    theme_scores[theme] = {
                        "name": theme,
                        "report_count": 0,
                        "news_count": 0,
                        "sentiment_score": 0,
                        "related_stocks": set(),
                        "first_seen": datetime.now().isoformat(),
                    }
                theme_scores[theme]["report_count"] += 1

                # 添加相关股票
                related = report.get("related_stocks", [])
                theme_scores[theme]["related_stocks"].update(related)

        # 从新闻中提取题材
        for news in news_data:
            themes = news.get("themes", [])
            for theme in themes:
                if theme not in theme_scores:
                    theme_scores[theme] = {
                        "name": theme,
                        "report_count": 0,
                        "news_count": 0,
                        "sentiment_score": 0,
                        "related_stocks": set(),
                        "first_seen": datetime.now().isoformat(),
                    }
                theme_scores[theme]["news_count"] += 1

                # 添加相关股票
                related = news.get("related_stocks", [])
                theme_scores[theme]["related_stocks"].update(related)

        # 计算题材热度
        hot_themes: List[Dict[str, Any]] = []

        for theme_name, theme_info in theme_scores.items():
            # 跳过黑名单题材
            if theme_name in self.theme_blacklist:
                continue

            # 计算热度得分
            heat_score = self._calculate_theme_heat(theme_info)

            if heat_score >= self.theme_heat_threshold:
                theme_info["heat_score"] = heat_score
                theme_info["related_stocks"] = list(theme_info["related_stocks"])
                hot_themes.append(theme_info)

        # 按热度排序
        hot_themes = sorted(hot_themes, key=lambda x: x["heat_score"], reverse=True)

        return hot_themes[:10]  # 最多返回10个热点题材

    def _calculate_theme_heat(self, theme_info: Dict[str, Any]) -> float:
        """计算题材热度

        Args:
            theme_info: 题材信息

        Returns:
            热度得分 (0.0-1.0)
        """
        report_count = theme_info.get("report_count", 0)
        news_count = theme_info.get("news_count", 0)
        stock_count = len(theme_info.get("related_stocks", []))

        # 研报得分
        report_score = min(0.35, report_count / self.report_count_threshold * 0.35)

        # 新闻得分
        news_score = min(0.35, news_count / self.news_count_threshold * 0.35)

        # 股票覆盖得分
        stock_score = min(0.30, stock_count / 20 * 0.30)

        heat_score = report_score + news_score + stock_score
        return min(1.0, heat_score)

    async def _update_theme_tracking(self, hot_themes: List[Dict[str, Any]]) -> None:
        """更新题材追踪

        Args:
            hot_themes: 热点题材列表
        """
        current_time = datetime.now()

        # 更新已追踪题材
        for theme_name in list(self.tracked_themes.keys()):
            theme_info = self.tracked_themes[theme_name]
            first_seen = datetime.fromisoformat(theme_info["first_seen"])
            days_tracked = (current_time - first_seen).days

            # 检查是否超过持续天数
            if days_tracked > self.theme_duration_days:
                # 移入黑名单
                self.theme_blacklist.add(theme_name)
                del self.tracked_themes[theme_name]
                logger.info(f"题材{theme_name}已过期，移入黑名单")

        # 添加新的热点题材
        for theme in hot_themes:
            theme_name = theme["name"]
            if theme_name not in self.tracked_themes:
                self.tracked_themes[theme_name] = theme
                logger.info(f"新增追踪题材: {theme_name}, 热度: {theme['heat_score']:.2f}")

        # 清理过期的黑名单
        # 这里简化处理，实际应该记录加入黑名单的时间

    async def _generate_theme_signals(self, theme: Dict[str, Any], market_data: Dict[str, Any]) -> List[Signal]:
        """为题材生成交易信号

        Args:
            theme: 题材信息
            market_data: 市场数据

        Returns:
            交易信号列表
        """
        signals: List[Signal] = []

        theme_name = theme.get("name", "")
        related_stocks = theme.get("related_stocks", [])
        heat_score = theme.get("heat_score", 0)

        if not related_stocks:
            return signals

        stocks_data = market_data.get("stocks", {})

        # 筛选龙头股
        leader_candidates: List[Dict[str, Any]] = []

        for symbol in related_stocks:
            stock_info = stocks_data.get(symbol, {})
            if not stock_info:
                continue

            # 计算龙头得分
            leader_score = self._calculate_leader_score(symbol, stock_info, theme)

            leader_candidates.append(
                {
                    "symbol": symbol,
                    "leader_score": leader_score,
                    "price": stock_info.get("price", 0),
                    "change_pct": stock_info.get("change_pct", 0),
                    "volume_ratio": stock_info.get("volume_ratio", 1.0),
                    "market_cap": stock_info.get("market_cap", 0),
                }
            )

        # 按龙头得分排序
        leader_candidates = sorted(leader_candidates, key=lambda x: x["leader_score"], reverse=True)

        # 选择前N个龙头股
        for i, candidate in enumerate(leader_candidates[: self.leader_rank_threshold]):
            symbol = candidate["symbol"]
            leader_score = candidate["leader_score"]
            change_pct = candidate["change_pct"]

            # 判断交易方向
            action = "hold"
            if leader_score > 0.6 and change_pct > 0:
                # 龙头股上涨，买入
                action = "buy"
            elif leader_score > 0.5 and change_pct < -0.03:
                # 龙头股回调，可能是买入机会
                action = "buy"

            if action == "hold":
                continue

            confidence = self._calculate_signal_confidence(heat_score, leader_score, candidate)

            reason = (
                f"题材[{theme_name}]热度{heat_score:.2f}, "
                f"龙头排名#{i+1}, "
                f"涨跌{change_pct*100:.2f}%, "
                f"量比{candidate['volume_ratio']:.2f}"
            )

            logger.info(f"S16_Theme_Hunter信号 - {symbol}: {reason}")

            signals.append(
                Signal(
                    symbol=symbol,
                    action=action,
                    confidence=confidence,
                    timestamp=datetime.now().isoformat(),
                    reason=reason,
                )
            )

        return signals

    def _calculate_leader_score(
        self, symbol: str, stock_info: Dict[str, Any], theme: Dict[str, Any]  # pylint: disable=unused-argument
    ) -> float:  # pylint: disable=unused-argument
        """计算龙头得分

        Args:
            symbol: 股票代码
            stock_info: 股票信息
            theme: 题材信息

        Returns:
            龙头得分 (0.0-1.0)
        """
        # 涨幅得分
        change_pct = stock_info.get("change_pct", 0)
        change_score = min(0.25, max(0, change_pct) * 2.5)

        # 量比得分
        volume_ratio = stock_info.get("volume_ratio", 1.0)
        volume_score = min(0.25, (volume_ratio - 1) * 0.1)

        # 市值得分（中等市值更容易成为龙头）
        market_cap = stock_info.get("market_cap", 0)
        if 5e9 <= market_cap <= 50e9:  # 50亿-500亿
            cap_score = 0.25
        elif 1e9 <= market_cap < 5e9:  # 10亿-50亿
            cap_score = 0.20
        elif 50e9 < market_cap <= 100e9:  # 500亿-1000亿
            cap_score = 0.15
        else:
            cap_score = 0.10

        # 题材相关度得分
        theme_relevance = stock_info.get("theme_relevance", 0.5)
        relevance_score = min(0.25, theme_relevance * 0.25)

        leader_score = change_score + volume_score + cap_score + relevance_score
        return min(1.0, leader_score)

    def _calculate_signal_confidence(self, heat_score: float, leader_score: float, candidate: Dict[str, Any]) -> float:
        """计算信号置信度"""
        heat_conf = min(0.30, heat_score * 0.30)
        leader_conf = min(0.30, leader_score * 0.30)

        # 量比加成
        volume_ratio = candidate.get("volume_ratio", 1.0)
        volume_conf = min(0.20, (volume_ratio - 1) * 0.1)

        confidence = heat_conf + leader_conf + volume_conf
        confidence = max(0.5, min(0.85, confidence + 0.3))
        return confidence

    async def calculate_position_sizes(self, signals: List[Signal]) -> List[Position]:
        """计算仓位大小"""
        positions: List[Position] = []
        total_allocated = 0.0
        max_total = min(self.max_position, 0.25)  # 题材策略总仓位上限25%

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
                    industry="theme_event",
                )
            )
            total_allocated += base_size

        logger.info(f"S16_Theme_Hunter仓位计算完成 - 标的数: {len(positions)}, 总仓位: {total_allocated*100:.2f}%")
        return positions

    def get_tracked_themes(self) -> Dict[str, Dict[str, Any]]:
        """获取当前追踪的题材

        Returns:
            追踪题材字典
        """
        return self.tracked_themes.copy()

    def clear_theme_blacklist(self) -> None:
        """清空题材黑名单"""
        self.theme_blacklist.clear()
        logger.info("题材黑名单已清空")
