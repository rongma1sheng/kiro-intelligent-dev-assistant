"""策略本质分析器

白皮书依据: 第五章 5.2.1 策略本质分析
引擎: Commander (战略级分析)
"""

from typing import Any, Dict, List

from loguru import logger

from .data_models import MarketScenario, ProfitSource, StrategyEssenceReport


class EssenceAnalyzer:
    """策略本质分析器

    白皮书依据: 第五章 5.2.1 策略本质分析

    分析内容:
    - 盈利来源识别: 趋势/均值回归/套利/波动率
    - 市场假设提取: 策略依赖的市场规律
    - 适用场景评估: 牛市/熊市/震荡市表现
    - 可持续性评分: 策略长期有效性预测
    """

    def __init__(self):
        """初始化策略本质分析器"""
        # 策略类型关键词映射
        self._profit_source_keywords = {
            ProfitSource.TREND: ["trend", "momentum", "breakout", "ma", "ema", "macd", "趋势", "动量", "突破"],
            ProfitSource.MEAN_REVERSION: [
                "reversion",
                "mean",
                "rsi",
                "bollinger",
                "oversold",
                "overbought",
                "均值回归",
                "超买",
                "超卖",
            ],
            ProfitSource.ARBITRAGE: ["arbitrage", "spread", "pair", "hedge", "套利", "价差", "对冲"],
            ProfitSource.VOLATILITY: ["volatility", "vix", "straddle", "strangle", "波动率", "期权"],
            ProfitSource.MOMENTUM: ["momentum", "relative_strength", "rs", "动量", "相对强度"],
            ProfitSource.VALUE: ["value", "pe", "pb", "dividend", "fundamental", "价值", "估值", "基本面"],
        }

        logger.info("EssenceAnalyzer初始化完成")

    async def analyze(self, strategy_id: str, strategy_data: Dict[str, Any]) -> StrategyEssenceReport:
        """分析策略本质

        Args:
            strategy_id: 策略ID
            strategy_data: 策略数据

        Returns:
            StrategyEssenceReport: 策略本质分析报告
        """
        logger.info(f"开始分析策略本质: {strategy_id}")

        try:
            # 提取策略代码和参数
            strategy_code = strategy_data.get("code", "")
            strategy_params = strategy_data.get("parameters", {})
            strategy_data.get("name", strategy_id)
            historical_returns = strategy_data.get("returns", [])

            # 1. 识别盈利来源
            profit_source = self._identify_profit_source(strategy_code, strategy_params)

            # 2. 提取市场假设
            market_assumptions = self._extract_market_assumptions(profit_source, strategy_code, strategy_params)

            # 3. 评估适用场景
            applicable_scenarios = self._evaluate_applicable_scenarios(profit_source, historical_returns)

            # 4. 计算可持续性评分
            sustainability_score = self._calculate_sustainability_score(
                profit_source, market_assumptions, historical_returns
            )

            # 5. 提取核心逻辑
            core_logic = self._extract_core_logic(strategy_code, profit_source)

            # 6. 分析优势和局限
            advantages, limitations = self._analyze_strengths_weaknesses(profit_source, applicable_scenarios)

            report = StrategyEssenceReport(
                strategy_id=strategy_id,
                profit_source=profit_source,
                market_assumptions=market_assumptions,
                applicable_scenarios=applicable_scenarios,
                sustainability_score=sustainability_score,
                core_logic=core_logic,
                advantages=advantages,
                limitations=limitations,
            )

            logger.info(f"策略本质分析完成: {strategy_id}, 盈利来源: {profit_source.value}")
            return report

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"策略本质分析失败: {strategy_id}, 错误: {e}")
            # 返回默认报告
            return StrategyEssenceReport(
                strategy_id=strategy_id,
                profit_source=ProfitSource.MIXED,
                market_assumptions=["无法提取市场假设"],
                applicable_scenarios=[MarketScenario.SIDEWAYS],
                sustainability_score=0.5,
                core_logic="无法提取核心逻辑",
                advantages=["未知"],
                limitations=["分析失败"],
            )

    def _identify_profit_source(self, strategy_code: str, strategy_params: Dict[str, Any]) -> ProfitSource:
        """识别盈利来源

        Args:
            strategy_code: 策略代码
            strategy_params: 策略参数

        Returns:
            ProfitSource: 盈利来源类型
        """
        code_lower = strategy_code.lower()
        params_str = str(strategy_params).lower()
        combined_text = code_lower + " " + params_str

        # 统计各类型关键词出现次数
        scores = {}
        for source, keywords in self._profit_source_keywords.items():
            score = sum(1 for kw in keywords if kw in combined_text)
            scores[source] = score

        # 选择得分最高的类型
        if not scores or max(scores.values()) == 0:
            return ProfitSource.MIXED

        best_source = max(scores, key=scores.get)
        return best_source

    def _extract_market_assumptions(
        self,
        profit_source: ProfitSource,
        strategy_code: str,  # pylint: disable=unused-argument
        strategy_params: Dict[str, Any],  # pylint: disable=unused-argument
    ) -> List[str]:
        """提取市场假设

        Args:
            profit_source: 盈利来源
            strategy_code: 策略代码
            strategy_params: 策略参数

        Returns:
            List[str]: 市场假设列表
        """
        assumptions = []

        # 根据盈利来源添加基本假设
        source_assumptions = {
            ProfitSource.TREND: ["市场存在持续性趋势", "趋势一旦形成会延续一段时间", "价格突破后会继续运动"],
            ProfitSource.MEAN_REVERSION: ["价格会围绕均值波动", "极端偏离后会回归", "市场存在均值回归特性"],
            ProfitSource.ARBITRAGE: ["市场存在定价偏差", "价差会收敛", "套利机会可被捕捉"],
            ProfitSource.VOLATILITY: ["波动率可预测", "波动率存在均值回归", "隐含波动率与实际波动率存在差异"],
            ProfitSource.MOMENTUM: ["强者恒强", "动量效应存在", "相对强度可预测未来表现"],
            ProfitSource.VALUE: ["价值终将回归", "低估值股票长期表现更好", "基本面决定长期价格"],
            ProfitSource.MIXED: ["多种市场规律共存", "不同市场环境适用不同策略"],
        }

        assumptions.extend(source_assumptions.get(profit_source, []))

        # 从参数中提取额外假设
        if "lookback" in strategy_params or "window" in strategy_params:
            window = strategy_params.get("lookback", strategy_params.get("window", 20))
            assumptions.append(f"历史{window}期数据具有预测价值")

        if "threshold" in strategy_params:
            assumptions.append("存在有效的信号阈值")

        return assumptions[:5]  # 最多返回5个假设

    def _evaluate_applicable_scenarios(
        self, profit_source: ProfitSource, historical_returns: List[float]
    ) -> List[MarketScenario]:
        """评估适用场景

        Args:
            profit_source: 盈利来源
            historical_returns: 历史收益

        Returns:
            List[MarketScenario]: 适用场景列表
        """
        # 根据盈利来源确定适用场景
        source_scenarios = {
            ProfitSource.TREND: [MarketScenario.BULL, MarketScenario.BEAR],
            ProfitSource.MEAN_REVERSION: [MarketScenario.SIDEWAYS, MarketScenario.LOW_VOLATILITY],
            ProfitSource.ARBITRAGE: [MarketScenario.SIDEWAYS, MarketScenario.LOW_VOLATILITY],
            ProfitSource.VOLATILITY: [MarketScenario.HIGH_VOLATILITY],
            ProfitSource.MOMENTUM: [MarketScenario.BULL, MarketScenario.HIGH_VOLATILITY],
            ProfitSource.VALUE: [MarketScenario.BEAR, MarketScenario.SIDEWAYS],
            ProfitSource.MIXED: [MarketScenario.SIDEWAYS],
        }

        scenarios = source_scenarios.get(profit_source, [MarketScenario.SIDEWAYS])

        # 如果有历史收益数据，进一步分析
        if historical_returns and len(historical_returns) > 20:
            import numpy as np  # pylint: disable=import-outside-toplevel

            returns_array = np.array(historical_returns)
            volatility = np.std(returns_array)
            mean_return = np.mean(returns_array)

            # 高波动环境表现好
            if volatility > 0.02 and mean_return > 0:
                if MarketScenario.HIGH_VOLATILITY not in scenarios:
                    scenarios.append(MarketScenario.HIGH_VOLATILITY)

            # 低波动环境表现好
            if volatility < 0.01 and mean_return > 0:
                if MarketScenario.LOW_VOLATILITY not in scenarios:
                    scenarios.append(MarketScenario.LOW_VOLATILITY)

        return scenarios

    def _calculate_sustainability_score(
        self, profit_source: ProfitSource, market_assumptions: List[str], historical_returns: List[float]
    ) -> float:
        """计算可持续性评分

        Args:
            profit_source: 盈利来源
            market_assumptions: 市场假设
            historical_returns: 历史收益

        Returns:
            float: 可持续性评分 0-1
        """
        score = 0.5  # 基础分

        # 根据盈利来源调整
        source_sustainability = {
            ProfitSource.TREND: 0.6,
            ProfitSource.MEAN_REVERSION: 0.7,
            ProfitSource.ARBITRAGE: 0.5,  # 套利机会容易消失
            ProfitSource.VOLATILITY: 0.6,
            ProfitSource.MOMENTUM: 0.55,
            ProfitSource.VALUE: 0.75,  # 价值投资长期有效
            ProfitSource.MIXED: 0.6,
        }

        score = source_sustainability.get(profit_source, 0.5)

        # 根据假设数量调整（假设越少越简单越可持续）
        if len(market_assumptions) <= 2:
            score += 0.1
        elif len(market_assumptions) >= 5:
            score -= 0.1

        # 根据历史收益稳定性调整
        if historical_returns and len(historical_returns) > 50:
            import numpy as np  # pylint: disable=import-outside-toplevel

            returns_array = np.array(historical_returns)

            # 计算收益稳定性
            rolling_sharpe = []
            window = 20
            for i in range(window, len(returns_array)):
                window_returns = returns_array[i - window : i]
                if np.std(window_returns) > 0:
                    sharpe = np.mean(window_returns) / np.std(window_returns)
                    rolling_sharpe.append(sharpe)

            if rolling_sharpe:
                sharpe_stability = 1 - np.std(rolling_sharpe) / (np.mean(np.abs(rolling_sharpe)) + 0.01)
                score = score * 0.7 + sharpe_stability * 0.3

        return max(0, min(1, score))

    def _extract_core_logic(self, strategy_code: str, profit_source: ProfitSource) -> str:
        """提取核心逻辑

        Args:
            strategy_code: 策略代码
            profit_source: 盈利来源

        Returns:
            str: 核心逻辑描述
        """
        # 根据盈利来源生成核心逻辑描述
        logic_templates = {
            ProfitSource.TREND: "基于趋势跟踪，在价格突破或趋势确认时入场，顺势而为",
            ProfitSource.MEAN_REVERSION: "基于均值回归，在价格偏离均值时反向操作，等待回归",
            ProfitSource.ARBITRAGE: "基于套利机会，捕捉价差并在收敛时获利",
            ProfitSource.VOLATILITY: "基于波动率交易，在波动率变化时获利",
            ProfitSource.MOMENTUM: "基于动量效应，买入强势标的，卖出弱势标的",
            ProfitSource.VALUE: "基于价值投资，买入低估值标的，长期持有",
            ProfitSource.MIXED: "综合多种策略逻辑，根据市场环境动态调整",
        }

        base_logic = logic_templates.get(profit_source, "策略逻辑未知")

        # 尝试从代码中提取更多信息
        if strategy_code:
            # 检测是否有止损逻辑
            if "stop_loss" in strategy_code.lower() or "stoploss" in strategy_code.lower():
                base_logic += "，包含止损机制"

            # 检测是否有仓位管理
            if "position" in strategy_code.lower() or "size" in strategy_code.lower():
                base_logic += "，包含仓位管理"

        return base_logic

    def _analyze_strengths_weaknesses(
        self, profit_source: ProfitSource, applicable_scenarios: List[MarketScenario]
    ) -> tuple:
        """分析优势和局限

        Args:
            profit_source: 盈利来源
            applicable_scenarios: 适用场景

        Returns:
            tuple: (优势列表, 局限列表)
        """
        advantages = []
        limitations = []

        # 根据盈利来源分析
        source_analysis = {
            ProfitSource.TREND: {
                "advantages": ["趋势行情中收益可观", "逻辑简单易理解", "可捕捉大行情"],
                "limitations": ["震荡市容易亏损", "入场时机难把握", "可能错过趋势初期"],
            },
            ProfitSource.MEAN_REVERSION: {
                "advantages": ["震荡市表现稳定", "胜率较高", "风险可控"],
                "limitations": ["趋势市容易亏损", "收益空间有限", "需要准确判断均值"],
            },
            ProfitSource.ARBITRAGE: {
                "advantages": ["风险较低", "收益稳定", "与市场方向无关"],
                "limitations": ["收益空间有限", "机会稀缺", "需要快速执行"],
            },
            ProfitSource.VOLATILITY: {
                "advantages": ["高波动时收益好", "可双向获利", "策略灵活"],
                "limitations": ["低波动时亏损", "需要准确预测波动率", "成本较高"],
            },
            ProfitSource.MOMENTUM: {
                "advantages": ["牛市表现优异", "逻辑清晰", "可量化"],
                "limitations": ["熊市亏损严重", "动量反转风险", "换手率高"],
            },
            ProfitSource.VALUE: {
                "advantages": ["长期有效", "风险较低", "理论基础扎实"],
                "limitations": ["短期可能跑输", "需要耐心", "价值陷阱风险"],
            },
            ProfitSource.MIXED: {
                "advantages": ["适应性强", "风险分散", "灵活调整"],
                "limitations": ["复杂度高", "难以优化", "可能两头不讨好"],
            },
        }

        analysis = source_analysis.get(profit_source, {"advantages": ["未知"], "limitations": ["未知"]})

        advantages = analysis["advantages"]
        limitations = analysis["limitations"]

        # 根据适用场景补充
        if len(applicable_scenarios) >= 3:
            advantages.append("适用场景广泛")
        elif len(applicable_scenarios) == 1:
            limitations.append("适用场景单一")

        return advantages, limitations
