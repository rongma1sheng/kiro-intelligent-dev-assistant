"""散户情绪分析器

白皮书依据: 第五章 5.2.20 散户情绪
引擎: Soldier (战术级分析)
"""

from datetime import datetime
from typing import Any, Dict, List

import numpy as np
from loguru import logger

from .data_models import RetailSentimentAnalysis, SentimentCategory


class RetailSentimentAnalyzer:
    """散户情绪分析器

    白皮书依据: 第五章 5.2.20 散户情绪

    分析内容:
    - 散户持仓比例: 散户资金占比
    - 散户活跃度: 散户交易活跃程度
    - 散户情绪: 散户整体情绪
    - 行为特征: 追涨杀跌等行为
    - 反向信号: 基于散户行为的反向指标
    """

    def __init__(self):
        """初始化散户情绪分析器"""
        logger.info("RetailSentimentAnalyzer初始化完成")

    async def analyze(self, market_data: Dict[str, Any], analysis_date: str = None) -> RetailSentimentAnalysis:
        """分析散户情绪

        Args:
            market_data: 市场数据
            analysis_date: 分析日期

        Returns:
            RetailSentimentAnalysis: 散户情绪分析报告
        """
        if analysis_date is None:
            analysis_date = datetime.now().strftime("%Y-%m-%d")

        logger.info(f"开始散户情绪分析: {analysis_date}")

        try:
            retail_data = market_data.get("retail_data", {})
            prices = market_data.get("prices", [])
            volumes = market_data.get("volumes", [])
            new_accounts = market_data.get("new_accounts", 0)
            search_trends = market_data.get("search_trends", {})

            # 1. 计算散户持仓比例
            retail_position_ratio = self._calculate_retail_position_ratio(retail_data)

            # 2. 计算散户活跃度
            retail_activity = self._calculate_retail_activity(retail_data, new_accounts, volumes)

            # 3. 计算散户情绪
            retail_sentiment = self._calculate_retail_sentiment(retail_data, prices, search_trends)

            # 4. 确定情绪分类
            sentiment_category = self._determine_sentiment_category(retail_sentiment)

            # 5. 分析行为特征
            behavior_characteristics = self._analyze_behavior_characteristics(retail_data, prices)

            # 6. 计算追涨杀跌指数
            chase_kill_index = self._calculate_chase_kill_index(retail_data, prices)

            # 7. 计算羊群效应指数
            herd_behavior_index = self._calculate_herd_behavior_index(retail_data, volumes)

            # 8. 生成反向信号
            contrarian_signal, contrarian_strength = self._generate_contrarian_signal(
                retail_sentiment, chase_kill_index, herd_behavior_index
            )

            # 9. 识别常见错误
            common_mistakes = self._identify_common_mistakes(behavior_characteristics, chase_kill_index)

            # 10. 生成专业建议
            professional_advice = self._generate_professional_advice(
                sentiment_category, contrarian_signal, common_mistakes
            )

            # 11. 生成风险警告
            risk_warnings = self._generate_risk_warnings(retail_sentiment, chase_kill_index, herd_behavior_index)

            report = RetailSentimentAnalysis(
                analysis_date=analysis_date,
                retail_position_ratio=round(retail_position_ratio, 2),
                retail_activity=round(retail_activity, 2),
                retail_sentiment=round(retail_sentiment, 2),
                sentiment_category=sentiment_category,
                behavior_characteristics=behavior_characteristics,
                chase_kill_index=round(chase_kill_index, 2),
                herd_behavior_index=round(herd_behavior_index, 2),
                contrarian_signal=contrarian_signal,
                contrarian_strength=round(contrarian_strength, 2),
                common_mistakes=common_mistakes,
                professional_advice=professional_advice,
                risk_warnings=risk_warnings,
            )

            logger.info(
                f"散户情绪分析完成: {analysis_date}, " f"情绪={sentiment_category.value}, 反向信号={contrarian_signal}"
            )
            return report

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"散户情绪分析失败: {e}")
            return RetailSentimentAnalysis(
                analysis_date=analysis_date,
                retail_position_ratio=0.5,
                retail_activity=0.5,
                retail_sentiment=0.5,
                sentiment_category=SentimentCategory.NEUTRAL,
                behavior_characteristics=[],
                chase_kill_index=0.5,
                herd_behavior_index=0.5,
                contrarian_signal="neutral",
                contrarian_strength=0.0,
                common_mistakes=[],
                professional_advice=["分析失败"],
                risk_warnings=["数据不足"],
            )

    def _calculate_retail_position_ratio(self, retail_data: Dict[str, Any]) -> float:
        """计算散户持仓比例

        Args:
            retail_data: 散户数据

        Returns:
            float: 持仓比例 0-1
        """
        if not retail_data:
            return 0.5

        retail_holdings = retail_data.get("holdings", 0)
        total_holdings = retail_data.get("total_holdings", 0)

        if total_holdings > 0:
            return retail_holdings / total_holdings

        # 使用默认估算
        return retail_data.get("position_ratio", 0.5)

    def _calculate_retail_activity(self, retail_data: Dict[str, Any], new_accounts: int, volumes: List[float]) -> float:
        """计算散户活跃度

        Args:
            retail_data: 散户数据
            new_accounts: 新开户数
            volumes: 成交量

        Returns:
            float: 活跃度 0-1
        """
        activity = 0.5  # 基础活跃度

        # 新开户数影响
        if new_accounts > 0:
            # 假设正常水平是10万户/周
            account_ratio = new_accounts / 100000
            activity += min(0.2, account_ratio * 0.1)

        # 成交量影响
        if volumes and len(volumes) >= 20:
            volumes_array = np.array(volumes)
            vol_ratio = volumes_array[-5:].mean() / volumes_array[-20:].mean()
            if vol_ratio > 1.5:
                activity += 0.2
            elif vol_ratio > 1.2:
                activity += 0.1

        # 散户交易占比
        retail_trading_ratio = retail_data.get("trading_ratio", 0.5)
        activity = activity * 0.5 + retail_trading_ratio * 0.5

        return min(1, activity)

    def _calculate_retail_sentiment(
        self, retail_data: Dict[str, Any], prices: List[float], search_trends: Dict[str, Any]
    ) -> float:
        """计算散户情绪

        Args:
            retail_data: 散户数据
            prices: 价格序列
            search_trends: 搜索趋势

        Returns:
            float: 情绪 0-1
        """
        sentiment = 0.5

        # 价格趋势影响散户情绪
        if prices and len(prices) >= 20:
            prices_array = np.array(prices)
            recent_return = prices_array[-1] / prices_array[-20] - 1
            sentiment += recent_return * 2  # 散户情绪与价格高度相关

        # 搜索趋势影响
        if search_trends:
            stock_search = search_trends.get("stock_search_index", 50)
            # 搜索量高表示散户关注度高
            sentiment += (stock_search - 50) / 100

        # 散户净买入影响
        net_buy = retail_data.get("net_buy", 0)
        if net_buy != 0:
            sentiment += np.sign(net_buy) * 0.1

        return max(0, min(1, sentiment))

    def _determine_sentiment_category(self, sentiment: float) -> SentimentCategory:
        """确定情绪分类

        Args:
            sentiment: 情绪值

        Returns:
            SentimentCategory: 情绪分类
        """
        if sentiment <= 0.2:  # pylint: disable=no-else-return
            return SentimentCategory.EXTREME_FEAR
        elif sentiment <= 0.4:
            return SentimentCategory.FEAR
        elif sentiment <= 0.6:
            return SentimentCategory.NEUTRAL
        elif sentiment <= 0.8:
            return SentimentCategory.GREED
        else:
            return SentimentCategory.EXTREME_GREED

    def _analyze_behavior_characteristics(self, retail_data: Dict[str, Any], prices: List[float]) -> List[str]:
        """分析行为特征

        Args:
            retail_data: 散户数据
            prices: 价格序列

        Returns:
            List[str]: 行为特征列表
        """
        characteristics = []

        # 追涨行为
        if prices and len(prices) >= 10:
            prices_array = np.array(prices)
            recent_return = prices_array[-1] / prices_array[-5] - 1
            net_buy = retail_data.get("net_buy", 0)

            if recent_return > 0.03 and net_buy > 0:
                characteristics.append("追涨行为明显")
            elif recent_return < -0.03 and net_buy < 0:
                characteristics.append("杀跌行为明显")

        # 频繁交易
        turnover = retail_data.get("turnover_rate", 0)
        if turnover > 0.1:
            characteristics.append("交易频繁")

        # 集中持仓
        concentration = retail_data.get("concentration", 0)
        if concentration > 0.3:
            characteristics.append("持仓集中")

        # 短线操作
        avg_holding = retail_data.get("avg_holding_days", 0)
        if avg_holding < 5:
            characteristics.append("短线操作为主")

        if not characteristics:
            characteristics.append("行为特征不明显")

        return characteristics

    def _calculate_chase_kill_index(self, retail_data: Dict[str, Any], prices: List[float]) -> float:
        """计算追涨杀跌指数

        Args:
            retail_data: 散户数据
            prices: 价格序列

        Returns:
            float: 追涨杀跌指数 0-1
        """
        if not prices or len(prices) < 10:
            return 0.5

        prices_array = np.array(prices)

        # 计算价格变化与散户行为的相关性
        # 高相关性表示追涨杀跌严重

        net_buys = retail_data.get("net_buy_history", [])
        if not net_buys or len(net_buys) < 5:
            # 使用价格动量作为代理
            momentum = prices_array[-1] / prices_array[-5] - 1
            return 0.5 + momentum * 2

        # 计算相关性
        min_len = min(len(prices_array), len(net_buys))
        price_changes = np.diff(prices_array[-min_len:])
        net_buy_array = np.array(net_buys[-min_len + 1 :])

        if len(price_changes) > 0 and len(net_buy_array) > 0:
            corr = np.corrcoef(price_changes, net_buy_array[: len(price_changes)])[0, 1]
            if not np.isnan(corr):
                return (corr + 1) / 2  # 转换到0-1

        return 0.5

    def _calculate_herd_behavior_index(self, retail_data: Dict[str, Any], volumes: List[float]) -> float:
        """计算羊群效应指数

        Args:
            retail_data: 散户数据
            volumes: 成交量

        Returns:
            float: 羊群效应指数 0-1
        """
        index = 0.5

        # 成交量集中度
        if volumes and len(volumes) >= 20:
            volumes_array = np.array(volumes)
            vol_cv = np.std(volumes_array[-20:]) / np.mean(volumes_array[-20:])
            # 高变异系数表示羊群效应
            index += min(0.3, vol_cv * 0.3)

        # 散户行为一致性
        consistency = retail_data.get("behavior_consistency", 0.5)
        index = index * 0.5 + consistency * 0.5

        return min(1, index)

    def _generate_contrarian_signal(
        self, sentiment: float, chase_kill: float, herd_behavior: float  # pylint: disable=unused-argument
    ) -> tuple:  # pylint: disable=unused-argument
        """生成反向信号

        Args:
            sentiment: 散户情绪
            chase_kill: 追涨杀跌指数
            herd_behavior: 羊群效应指数

        Returns:
            tuple: (反向信号, 信号强度)
        """
        # 散户极度乐观时看空，极度悲观时看多
        if sentiment > 0.8 and chase_kill > 0.7:  # pylint: disable=no-else-return
            return "bearish", (sentiment - 0.5) * 2
        elif sentiment < 0.2 and chase_kill < 0.3:
            return "bullish", (0.5 - sentiment) * 2
        elif sentiment > 0.7:
            return "slightly_bearish", (sentiment - 0.5)
        elif sentiment < 0.3:
            return "slightly_bullish", (0.5 - sentiment)
        else:
            return "neutral", 0.0

    def _identify_common_mistakes(self, characteristics: List[str], chase_kill: float) -> List[str]:
        """识别常见错误

        Args:
            characteristics: 行为特征
            chase_kill: 追涨杀跌指数

        Returns:
            List[str]: 常见错误列表
        """
        mistakes = []

        if "追涨行为明显" in characteristics:
            mistakes.append("高位追涨，容易被套")

        if "杀跌行为明显" in characteristics:
            mistakes.append("恐慌杀跌，错失反弹")

        if "交易频繁" in characteristics:
            mistakes.append("频繁交易，成本侵蚀收益")

        if "持仓集中" in characteristics:
            mistakes.append("持仓过于集中，风险较大")

        if "短线操作为主" in characteristics:
            mistakes.append("过度短线，难以把握趋势")

        if chase_kill > 0.7:
            mistakes.append("追涨杀跌严重，需要逆向思维")

        if not mistakes:
            mistakes.append("暂无明显错误")

        return mistakes

    def _generate_professional_advice(
        self,
        category: SentimentCategory,  # pylint: disable=unused-argument
        contrarian_signal: str,
        mistakes: List[str],  # pylint: disable=unused-argument
    ) -> List[str]:
        """生成专业建议

        Args:
            category: 情绪分类
            contrarian_signal: 反向信号
            mistakes: 常见错误

        Returns:
            List[str]: 专业建议
        """
        advice = []

        # 基于反向信号的建议
        if contrarian_signal == "bearish":
            advice.append("散户过度乐观，专业投资者应保持谨慎")
            advice.append("考虑逐步减仓，锁定利润")
        elif contrarian_signal == "bullish":
            advice.append("散户过度悲观，可能是布局机会")
            advice.append("考虑逆向布局优质资产")

        # 基于错误的建议
        if "追涨杀跌严重" in mistakes:
            advice.append("建立交易纪律，避免情绪化操作")

        if "频繁交易" in mistakes:
            advice.append("降低交易频率，关注中长期机会")

        # 通用建议
        advice.append("保持独立思考，不盲目跟风")
        advice.append("制定投资计划，严格执行")

        return advice

    def _generate_risk_warnings(self, sentiment: float, chase_kill: float, herd_behavior: float) -> List[str]:
        """生成风险警告

        Args:
            sentiment: 散户情绪
            chase_kill: 追涨杀跌指数
            herd_behavior: 羊群效应指数

        Returns:
            List[str]: 风险警告
        """
        warnings = []

        if sentiment > 0.8:
            warnings.append("【警告】散户情绪过热，市场可能见顶")
        elif sentiment < 0.2:
            warnings.append("【警告】散户情绪极度悲观，注意恐慌性抛售")

        if chase_kill > 0.8:
            warnings.append("追涨杀跌行为极端，市场波动可能加剧")

        if herd_behavior > 0.8:
            warnings.append("羊群效应明显，注意踩踏风险")

        if not warnings:
            warnings.append("当前无重大风险警告")

        return warnings
