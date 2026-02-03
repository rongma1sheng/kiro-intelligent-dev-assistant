"""压力测试分析器

白皮书依据: 第五章 5.2.17 压力测试
引擎: Commander (战略级分析)
"""

from typing import Any, Dict, List

import numpy as np
from loguru import logger

from .data_models import StressTestAnalysis, StressTestGrade


class StressTestAnalyzer:
    """压力测试分析器

    白皮书依据: 第五章 5.2.17 压力测试

    分析内容:
    - 历史事件测试: 策略在历史极端事件中的表现
    - 情景测试: 假设情景下的表现
    - 生存概率: 策略在极端情况下的生存能力
    - 脆弱性识别: 策略的薄弱环节
    - 应急预案: 极端情况下的应对措施
    """

    # 历史极端事件
    HISTORICAL_EVENTS = [
        {"name": "2008金融危机", "drawdown": -0.50, "duration": 365},
        {"name": "2015股灾", "drawdown": -0.45, "duration": 60},
        {"name": "2018贸易战", "drawdown": -0.30, "duration": 180},
        {"name": "2020疫情冲击", "drawdown": -0.35, "duration": 30},
        {"name": "2022俄乌冲突", "drawdown": -0.20, "duration": 90},
    ]

    # 压力测试情景
    STRESS_SCENARIOS = [
        {"name": "市场暴跌20%", "market_shock": -0.20},
        {"name": "市场暴跌30%", "market_shock": -0.30},
        {"name": "波动率翻倍", "vol_multiplier": 2.0},
        {"name": "流动性枯竭", "liquidity_shock": 0.5},
        {"name": "黑天鹅事件", "market_shock": -0.40, "vol_multiplier": 3.0},
    ]

    def __init__(self):
        """初始化压力测试分析器"""
        logger.info("StressTestAnalyzer初始化完成")

    async def analyze(self, strategy_id: str, strategy_data: Dict[str, Any]) -> StressTestAnalysis:
        """执行压力测试

        Args:
            strategy_id: 策略ID
            strategy_data: 策略数据

        Returns:
            StressTestAnalysis: 压力测试报告
        """
        logger.info(f"开始压力测试: {strategy_id}")

        try:
            returns = strategy_data.get("returns", [])
            beta = strategy_data.get("beta", 1.0)
            strategy_data.get("max_drawdown", 0)
            risk_tolerance = strategy_data.get("risk_tolerance", 0.2)

            # 1. 历史事件测试
            historical_events = self._test_historical_events(returns, beta)

            # 2. 找出最差历史事件
            worst_event, worst_event_loss = self._find_worst_event(historical_events)

            # 3. 情景测试
            scenario_tests = self._test_scenarios(returns, beta)

            # 4. 找出最差情景
            worst_scenario, worst_scenario_loss = self._find_worst_scenario(scenario_tests)

            # 5. 计算生存概率
            survival_probability = self._calculate_survival_probability(
                worst_event_loss, worst_scenario_loss, risk_tolerance
            )

            # 6. 计算最大可容忍损失
            max_tolerable_loss = self._calculate_max_tolerable_loss(risk_tolerance, returns)

            # 7. 确定压力测试评级
            stress_test_grade = self._determine_grade(survival_probability, worst_scenario_loss, max_tolerable_loss)

            # 8. 识别脆弱性
            vulnerabilities, critical_vulnerabilities = self._identify_vulnerabilities(
                historical_events, scenario_tests, returns
            )

            # 9. 生成应急预案
            contingency_plans = self._generate_contingency_plans(vulnerabilities, worst_scenario)

            # 10. 生成建议
            recommended_actions = self._generate_recommendations(
                stress_test_grade, vulnerabilities, survival_probability
            )

            report = StressTestAnalysis(
                strategy_id=strategy_id,
                historical_events=historical_events,
                worst_event=worst_event,
                worst_event_loss=round(worst_event_loss, 4),
                scenario_tests=scenario_tests,
                worst_scenario=worst_scenario,
                worst_scenario_loss=round(worst_scenario_loss, 4),
                risk_tolerance=risk_tolerance,
                survival_probability=round(survival_probability, 2),
                max_tolerable_loss=round(max_tolerable_loss, 4),
                stress_test_grade=stress_test_grade,
                vulnerabilities=vulnerabilities,
                critical_vulnerabilities=critical_vulnerabilities,
                contingency_plans=contingency_plans,
                recommended_actions=recommended_actions,
            )

            logger.info(
                f"压力测试完成: {strategy_id}, " f"评级={stress_test_grade.value}, 生存概率={survival_probability:.1%}"
            )
            return report

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"压力测试失败: {strategy_id}, 错误: {e}")
            return StressTestAnalysis(
                strategy_id=strategy_id,
                historical_events=[],
                worst_event="分析失败",
                worst_event_loss=0.0,
                scenario_tests=[],
                worst_scenario="分析失败",
                worst_scenario_loss=0.0,
                risk_tolerance=0.2,
                survival_probability=0.5,
                max_tolerable_loss=0.2,
                stress_test_grade=StressTestGrade.C,
                vulnerabilities=["分析失败"],
                critical_vulnerabilities=[],
                contingency_plans=["建议人工审核"],
                recommended_actions=["建议人工审核"],
            )

    def _test_historical_events(self, returns: List[float], beta: float) -> List[Dict[str, Any]]:
        """测试历史事件

        Args:
            returns: 收益率序列
            beta: 策略Beta

        Returns:
            List[Dict[str, Any]]: 历史事件测试结果
        """
        results = []

        for event in self.HISTORICAL_EVENTS:
            # 估算策略在该事件中的损失
            market_loss = event["drawdown"]
            strategy_loss = market_loss * beta

            # 考虑策略特性调整
            if returns:
                strategy_vol = np.std(returns) * np.sqrt(252)
                market_vol = 0.20  # 假设市场年化波动率20%
                vol_ratio = strategy_vol / market_vol
                strategy_loss = strategy_loss * vol_ratio

            results.append(
                {
                    "event_name": event["name"],
                    "market_drawdown": event["drawdown"],
                    "strategy_loss": round(strategy_loss, 4),
                    "duration_days": event["duration"],
                    "recovery_estimate": event["duration"] * 1.5,  # 估计恢复时间
                }
            )

        return results

    def _find_worst_event(self, historical_events: List[Dict[str, Any]]) -> tuple:
        """找出最差历史事件

        Args:
            historical_events: 历史事件测试结果

        Returns:
            tuple: (最差事件名, 最大损失)
        """
        if not historical_events:
            return "无数据", 0.0

        worst = min(historical_events, key=lambda x: x["strategy_loss"])
        return worst["event_name"], worst["strategy_loss"]

    def _test_scenarios(
        self, returns: List[float], beta: float  # pylint: disable=unused-argument
    ) -> List[Dict[str, Any]]:  # pylint: disable=unused-argument
        """测试压力情景

        Args:
            returns: 收益率序列
            beta: 策略Beta

        Returns:
            List[Dict[str, Any]]: 情景测试结果
        """
        results = []

        for scenario in self.STRESS_SCENARIOS:
            # 基础损失
            market_shock = scenario.get("market_shock", 0)
            strategy_loss = market_shock * beta

            # 波动率冲击
            vol_multiplier = scenario.get("vol_multiplier", 1.0)
            if vol_multiplier > 1:
                strategy_loss *= vol_multiplier**0.5

            # 流动性冲击
            liquidity_shock = scenario.get("liquidity_shock", 0)
            if liquidity_shock > 0:
                strategy_loss *= 1 + liquidity_shock

            results.append(
                {
                    "scenario_name": scenario["name"],
                    "market_shock": market_shock,
                    "strategy_loss": round(strategy_loss, 4),
                    "vol_multiplier": vol_multiplier,
                    "liquidity_shock": liquidity_shock,
                }
            )

        return results

    def _find_worst_scenario(self, scenario_tests: List[Dict[str, Any]]) -> tuple:
        """找出最差情景

        Args:
            scenario_tests: 情景测试结果

        Returns:
            tuple: (最差情景名, 最大损失)
        """
        if not scenario_tests:
            return "无数据", 0.0

        worst = min(scenario_tests, key=lambda x: x["strategy_loss"])
        return worst["scenario_name"], worst["strategy_loss"]

    def _calculate_survival_probability(
        self, worst_event_loss: float, worst_scenario_loss: float, risk_tolerance: float
    ) -> float:
        """计算生存概率

        Args:
            worst_event_loss: 最差历史事件损失
            worst_scenario_loss: 最差情景损失
            risk_tolerance: 风险容忍度

        Returns:
            float: 生存概率 0-1
        """
        # 取最大损失
        max_loss = min(worst_event_loss, worst_scenario_loss)

        # 如果最大损失在容忍范围内，生存概率高
        if abs(max_loss) <= risk_tolerance:  # pylint: disable=no-else-return
            return 0.95
        elif abs(max_loss) <= risk_tolerance * 1.5:
            return 0.8
        elif abs(max_loss) <= risk_tolerance * 2:
            return 0.6
        elif abs(max_loss) <= risk_tolerance * 3:
            return 0.4
        else:
            return 0.2

    def _calculate_max_tolerable_loss(self, risk_tolerance: float, returns: List[float]) -> float:
        """计算最大可容忍损失

        Args:
            risk_tolerance: 风险容忍度
            returns: 收益率序列

        Returns:
            float: 最大可容忍损失
        """
        # 基于风险容忍度
        base_tolerance = risk_tolerance

        # 根据历史波动率调整
        if returns:
            vol = np.std(returns) * np.sqrt(252)
            # 高波动策略可以容忍更大损失
            vol_adjustment = min(0.1, vol * 0.2)
            base_tolerance += vol_adjustment

        return min(0.5, base_tolerance)  # 最大50%

    def _determine_grade(self, survival_probability: float, worst_loss: float, max_tolerable: float) -> StressTestGrade:
        """确定压力测试评级

        Args:
            survival_probability: 生存概率
            worst_loss: 最差损失
            max_tolerable: 最大可容忍损失

        Returns:
            StressTestGrade: 评级
        """
        # 综合评分
        score = 0

        # 生存概率评分
        if survival_probability >= 0.9:
            score += 40
        elif survival_probability >= 0.7:
            score += 30
        elif survival_probability >= 0.5:
            score += 20
        else:
            score += 10

        # 损失评分
        loss_ratio = abs(worst_loss) / max_tolerable if max_tolerable > 0 else 2
        if loss_ratio <= 0.5:
            score += 40
        elif loss_ratio <= 1.0:
            score += 30
        elif loss_ratio <= 1.5:
            score += 20
        else:
            score += 10

        # 确定评级
        if score >= 70:  # pylint: disable=no-else-return
            return StressTestGrade.A
        elif score >= 55:
            return StressTestGrade.B
        elif score >= 40:
            return StressTestGrade.C
        elif score >= 25:
            return StressTestGrade.D
        else:
            return StressTestGrade.F

    def _identify_vulnerabilities(
        self, historical_events: List[Dict[str, Any]], scenario_tests: List[Dict[str, Any]], returns: List[float]
    ) -> tuple:
        """识别脆弱性

        Args:
            historical_events: 历史事件测试
            scenario_tests: 情景测试
            returns: 收益率序列

        Returns:
            tuple: (脆弱性列表, 关键脆弱性列表)
        """
        vulnerabilities = []
        critical = []

        # 检查历史事件脆弱性
        for event in historical_events:
            if event["strategy_loss"] < -0.3:
                vuln = f"在{event['event_name']}中损失{abs(event['strategy_loss']):.1%}"
                vulnerabilities.append(vuln)
                if event["strategy_loss"] < -0.4:
                    critical.append(vuln)

        # 检查情景脆弱性
        for scenario in scenario_tests:
            if scenario["strategy_loss"] < -0.25:
                vuln = f"在{scenario['scenario_name']}情景下损失{abs(scenario['strategy_loss']):.1%}"
                vulnerabilities.append(vuln)
                if scenario["strategy_loss"] < -0.35:
                    critical.append(vuln)

        # 检查波动率脆弱性
        if returns:
            vol = np.std(returns) * np.sqrt(252)
            if vol > 0.4:
                vulnerabilities.append(f"策略波动率过高({vol:.1%})")

        # 检查尾部风险
        if returns and len(returns) > 100:
            var_99 = np.percentile(returns, 1)
            if var_99 < -0.05:
                vulnerabilities.append(f"尾部风险较大(VaR99={var_99:.2%})")

        if not vulnerabilities:
            vulnerabilities.append("未发现明显脆弱性")

        return vulnerabilities, critical

    def _generate_contingency_plans(self, vulnerabilities: List[str], worst_scenario: str) -> List[str]:
        """生成应急预案

        Args:
            vulnerabilities: 脆弱性列表
            worst_scenario: 最差情景

        Returns:
            List[str]: 应急预案
        """
        plans = []

        # 通用应急预案
        plans.append("设置最大回撤止损线，触发后自动减仓")
        plans.append("准备现金储备，应对极端情况下的追加保证金")

        # 针对最差情景的预案
        if "暴跌" in worst_scenario:
            plans.append("市场暴跌时：立即减仓至50%以下，等待企稳")

        if "波动率" in worst_scenario:
            plans.append("波动率飙升时：暂停新开仓，收紧止损")

        if "流动性" in worst_scenario:
            plans.append("流动性枯竭时：避免大单交易，分批减仓")

        if "黑天鹅" in worst_scenario:
            plans.append("黑天鹅事件：启动紧急风控，全面评估后再行动")

        # 针对脆弱性的预案
        for vuln in vulnerabilities[:3]:
            if "波动率过高" in vuln:
                plans.append("高波动期：降低仓位，增加对冲")
            if "尾部风险" in vuln:
                plans.append("购买尾部风险保护（如看跌期权）")

        return plans

    def _generate_recommendations(
        self, grade: StressTestGrade, vulnerabilities: List[str], survival_probability: float
    ) -> List[str]:
        """生成建议

        Args:
            grade: 压力测试评级
            vulnerabilities: 脆弱性列表
            survival_probability: 生存概率

        Returns:
            List[str]: 建议列表
        """
        recommendations = []

        if grade in [StressTestGrade.D, StressTestGrade.F]:
            recommendations.append("【紧急】策略抗风险能力不足，建议立即优化")
            recommendations.append("考虑降低策略杠杆或仓位")
        elif grade == StressTestGrade.C:
            recommendations.append("策略抗风险能力一般，建议加强风控")

        if survival_probability < 0.5:
            recommendations.append("生存概率较低，建议增加风险缓冲")

        if len(vulnerabilities) > 3:
            recommendations.append("脆弱性较多，建议全面审查策略逻辑")

        recommendations.append("定期进行压力测试，监控风险变化")
        recommendations.append("建立完善的应急响应机制")

        return recommendations
