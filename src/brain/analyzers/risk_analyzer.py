"""风险评估分析器

白皮书依据: 第五章 5.2.2 风险识别与评估
引擎: Commander (战略级分析)
"""

from typing import Any, Dict, List

import numpy as np
from loguru import logger

from .data_models import RiskAssessmentReport, RiskLevel


class RiskAnalyzer:
    """风险评估分析器

    白皮书依据: 第五章 5.2.2 风险识别与评估

    分析内容:
    - 系统性风险识别: 市场风险、流动性风险、政策风险
    - 特异性风险识别: 策略特有风险、参数风险
    - 风险矩阵构建: 风险名称 -> 严重程度映射
    - 缓解方案制定: 针对各类风险的应对措施
    """

    # 系统性风险类型
    SYSTEMATIC_RISK_TYPES = [
        "market_risk",  # 市场风险
        "liquidity_risk",  # 流动性风险
        "policy_risk",  # 政策风险
        "interest_rate_risk",  # 利率风险
        "exchange_rate_risk",  # 汇率风险
        "systemic_risk",  # 系统性风险
    ]

    # 特异性风险类型
    SPECIFIC_RISK_TYPES = [
        "model_risk",  # 模型风险
        "parameter_risk",  # 参数风险
        "execution_risk",  # 执行风险
        "concentration_risk",  # 集中度风险
        "overfitting_risk",  # 过拟合风险
        "data_risk",  # 数据风险
    ]

    def __init__(self):
        """初始化风险评估分析器"""
        self._risk_thresholds = {
            "max_drawdown": {"low": 0.05, "medium": 0.10, "high": 0.20, "critical": 0.30},
            "volatility": {"low": 0.10, "medium": 0.20, "high": 0.30, "critical": 0.50},
            "var_95": {"low": 0.02, "medium": 0.05, "high": 0.10, "critical": 0.15},
            "sharpe_ratio": {"critical": 0.5, "high": 1.0, "medium": 1.5, "low": 2.0},
        }
        logger.info("RiskAnalyzer初始化完成")

    async def analyze(self, strategy_id: str, strategy_data: Dict[str, Any]) -> RiskAssessmentReport:
        """分析策略风险

        Args:
            strategy_id: 策略ID
            strategy_data: 策略数据，包含returns, positions, trades等

        Returns:
            RiskAssessmentReport: 风险评估报告
        """
        logger.info(f"开始风险评估分析: {strategy_id}")

        try:
            returns = strategy_data.get("returns", [])
            positions = strategy_data.get("positions", [])
            trades = strategy_data.get("trades", [])
            parameters = strategy_data.get("parameters", {})

            # 1. 识别系统性风险
            systematic_risks = self._identify_systematic_risks(returns, positions)

            # 2. 识别特异性风险
            specific_risks = self._identify_specific_risks(returns, trades, parameters)

            # 3. 构建风险矩阵
            risk_matrix = self._build_risk_matrix(systematic_risks, specific_risks, returns)

            # 4. 制定缓解方案
            mitigation_plan = self._create_mitigation_plan(risk_matrix)

            # 5. 计算整体风险等级和评分
            overall_risk_level, risk_score = self._calculate_overall_risk(risk_matrix, returns)

            report = RiskAssessmentReport(
                strategy_id=strategy_id,
                systematic_risks=systematic_risks,
                specific_risks=specific_risks,
                risk_matrix=risk_matrix,
                mitigation_plan=mitigation_plan,
                overall_risk_level=overall_risk_level,
                risk_score=risk_score,
            )

            logger.info(f"风险评估完成: {strategy_id}, 整体风险等级: {overall_risk_level.value}")
            return report

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"风险评估分析失败: {strategy_id}, 错误: {e}")
            return RiskAssessmentReport(
                strategy_id=strategy_id,
                systematic_risks=[],
                specific_risks=[],
                risk_matrix={},
                mitigation_plan=["分析失败，建议人工审核"],
                overall_risk_level=RiskLevel.HIGH,
                risk_score=75.0,
            )

    def _identify_systematic_risks(self, returns: List[float], positions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """识别系统性风险

        Args:
            returns: 收益率序列
            positions: 持仓数据

        Returns:
            List[Dict[str, Any]]: 系统性风险列表
        """
        risks = []

        if not returns:
            risks.append(
                {
                    "type": "data_risk",
                    "name": "数据不足风险",
                    "description": "历史数据不足，无法准确评估风险",
                    "severity": RiskLevel.HIGH.value,
                    "probability": 0.8,
                }
            )
            return risks

        returns_array = np.array(returns)

        # 市场风险评估
        beta = self._estimate_beta(returns_array)
        if abs(beta) > 1.5:
            risks.append(
                {
                    "type": "market_risk",
                    "name": "高市场敏感性风险",
                    "description": f"策略Beta={beta:.2f}，对市场波动敏感",
                    "severity": RiskLevel.HIGH.value if abs(beta) > 2 else RiskLevel.MEDIUM.value,
                    "probability": 0.7,
                    "beta": beta,
                }
            )

        # 流动性风险评估
        if positions:
            concentration = self._calculate_concentration(positions)
            if concentration > 0.3:
                risks.append(
                    {
                        "type": "liquidity_risk",
                        "name": "流动性集中风险",
                        "description": f"持仓集中度={concentration:.1%}，可能面临流动性问题",
                        "severity": RiskLevel.HIGH.value if concentration > 0.5 else RiskLevel.MEDIUM.value,
                        "probability": 0.6,
                        "concentration": concentration,
                    }
                )

        # 尾部风险评估
        var_95 = np.percentile(returns_array, 5)
        cvar_95 = (
            returns_array[returns_array <= var_95].mean() if len(returns_array[returns_array <= var_95]) > 0 else var_95
        )

        if var_95 < -0.05:
            risks.append(
                {
                    "type": "tail_risk",
                    "name": "尾部风险",
                    "description": f"VaR(95%)={var_95:.2%}，CVaR(95%)={cvar_95:.2%}",
                    "severity": RiskLevel.HIGH.value if var_95 < -0.10 else RiskLevel.MEDIUM.value,
                    "probability": 0.05,
                    "var_95": var_95,
                    "cvar_95": cvar_95,
                }
            )

        # 波动率风险
        volatility = np.std(returns_array) * np.sqrt(252)
        if volatility > 0.25:
            risks.append(
                {
                    "type": "volatility_risk",
                    "name": "高波动风险",
                    "description": f"年化波动率={volatility:.1%}，波动较大",
                    "severity": RiskLevel.HIGH.value if volatility > 0.40 else RiskLevel.MEDIUM.value,
                    "probability": 0.8,
                    "volatility": volatility,
                }
            )

        return risks

    def _identify_specific_risks(
        self, returns: List[float], trades: List[Dict[str, Any]], parameters: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """识别特异性风险

        Args:
            returns: 收益率序列
            trades: 交易记录
            parameters: 策略参数

        Returns:
            List[Dict[str, Any]]: 特异性风险列表
        """
        risks = []

        # 参数风险
        param_count = len(parameters)
        if param_count > 10:
            risks.append(
                {
                    "type": "parameter_risk",
                    "name": "参数过多风险",
                    "description": f"策略有{param_count}个参数，可能存在过拟合",
                    "severity": RiskLevel.MEDIUM.value,
                    "probability": 0.6,
                    "param_count": param_count,
                }
            )

        # 执行风险
        if trades:
            avg_trade_size = np.mean([t.get("size", 0) for t in trades if "size" in t])
            if avg_trade_size > 100000:
                risks.append(
                    {
                        "type": "execution_risk",
                        "name": "大单执行风险",
                        "description": f"平均交易规模={avg_trade_size:.0f}，可能面临执行困难",
                        "severity": RiskLevel.MEDIUM.value,
                        "probability": 0.5,
                        "avg_trade_size": avg_trade_size,
                    }
                )

        # 模型风险
        if returns and len(returns) > 100:
            returns_array = np.array(returns)
            # 检查收益分布是否正态
            from scipy import stats  # pylint: disable=import-outside-toplevel

            _, p_value = stats.normaltest(returns_array)
            if p_value < 0.05:
                risks.append(
                    {
                        "type": "model_risk",
                        "name": "收益分布非正态风险",
                        "description": "收益分布显著偏离正态，传统风险模型可能失效",
                        "severity": RiskLevel.MEDIUM.value,
                        "probability": 0.7,
                        "normality_p_value": p_value,
                    }
                )

        # 过拟合风险（简单检测）
        if parameters:
            lookback = parameters.get("lookback", parameters.get("window", 0))
            if lookback and returns and len(returns) < lookback * 10:
                risks.append(
                    {
                        "type": "overfitting_risk",
                        "name": "样本不足风险",
                        "description": f"回看期={lookback}，但样本量仅{len(returns)}，可能过拟合",
                        "severity": RiskLevel.HIGH.value,
                        "probability": 0.7,
                    }
                )

        return risks

    def _build_risk_matrix(
        self, systematic_risks: List[Dict[str, Any]], specific_risks: List[Dict[str, Any]], returns: List[float]
    ) -> Dict[str, RiskLevel]:
        """构建风险矩阵

        Args:
            systematic_risks: 系统性风险列表
            specific_risks: 特异性风险列表
            returns: 收益率序列

        Returns:
            Dict[str, RiskLevel]: 风险名称到等级的映射
        """
        risk_matrix = {}

        # 添加系统性风险
        for risk in systematic_risks:
            risk_matrix[risk["name"]] = RiskLevel(risk["severity"])

        # 添加特异性风险
        for risk in specific_risks:
            risk_matrix[risk["name"]] = RiskLevel(risk["severity"])

        # 添加基础风险评估
        if returns:
            returns_array = np.array(returns)

            # 最大回撤风险
            max_dd = self._calculate_max_drawdown(returns_array)
            dd_level = self._get_risk_level("max_drawdown", abs(max_dd))
            risk_matrix["最大回撤风险"] = dd_level

            # 波动率风险
            vol = np.std(returns_array) * np.sqrt(252)
            vol_level = self._get_risk_level("volatility", vol)
            risk_matrix["波动率风险"] = vol_level

            # VaR风险
            var_95 = abs(np.percentile(returns_array, 5))
            var_level = self._get_risk_level("var_95", var_95)
            risk_matrix["VaR风险"] = var_level

        return risk_matrix

    def _create_mitigation_plan(self, risk_matrix: Dict[str, RiskLevel]) -> List[str]:
        """制定风险缓解方案

        Args:
            risk_matrix: 风险矩阵

        Returns:
            List[str]: 缓解方案列表
        """
        plans = []

        for risk_name, risk_level in risk_matrix.items():
            if risk_level == RiskLevel.CRITICAL:
                plans.append(f"【紧急】{risk_name}: 立即停止策略运行，进行全面审查")
            elif risk_level == RiskLevel.HIGH:
                if "回撤" in risk_name:
                    plans.append(f"【高优先级】{risk_name}: 设置更严格的止损，降低仓位")
                elif "波动" in risk_name:
                    plans.append(f"【高优先级】{risk_name}: 增加波动率过滤，减少高波动期交易")
                elif "流动性" in risk_name:
                    plans.append(f"【高优先级】{risk_name}: 分散持仓，避免集中度过高")
                else:
                    plans.append(f"【高优先级】{risk_name}: 需要重点关注和改进")
            elif risk_level == RiskLevel.MEDIUM:
                plans.append(f"【中优先级】{risk_name}: 持续监控，适时调整")

        if not plans:
            plans.append("当前风险水平可控，建议保持监控")

        return plans

    def _calculate_overall_risk(
        self, risk_matrix: Dict[str, RiskLevel], returns: List[float]  # pylint: disable=unused-argument
    ) -> tuple:  # pylint: disable=unused-argument
        """计算整体风险等级和评分

        Args:
            risk_matrix: 风险矩阵
            returns: 收益率序列

        Returns:
            tuple: (整体风险等级, 风险评分)
        """
        if not risk_matrix:
            return RiskLevel.MEDIUM, 50.0

        # 风险等级权重
        level_scores = {RiskLevel.LOW: 25, RiskLevel.MEDIUM: 50, RiskLevel.HIGH: 75, RiskLevel.CRITICAL: 100}

        # 计算加权平均风险评分
        total_score = sum(level_scores[level] for level in risk_matrix.values())
        avg_score = total_score / len(risk_matrix)

        # 确定整体风险等级
        if avg_score >= 85:
            overall_level = RiskLevel.CRITICAL
        elif avg_score >= 65:
            overall_level = RiskLevel.HIGH
        elif avg_score >= 40:
            overall_level = RiskLevel.MEDIUM
        else:
            overall_level = RiskLevel.LOW

        return overall_level, avg_score

    def _estimate_beta(self, returns: np.ndarray) -> float:
        """估算Beta值（简化版，假设市场收益为0）"""
        if len(returns) < 20:
            return 1.0
        # 简化：使用收益率标准差作为Beta的代理
        return np.std(returns) * np.sqrt(252) / 0.20  # 假设市场年化波动率20%

    def _calculate_concentration(self, positions: List[Dict[str, Any]]) -> float:
        """计算持仓集中度"""
        if not positions:
            return 0.0
        weights = [p.get("weight", 0) for p in positions]
        if not weights or sum(weights) == 0:
            return 0.0
        # 计算HHI指数
        weights = np.array(weights) / sum(weights)
        hhi = np.sum(weights**2)
        return hhi

    def _calculate_max_drawdown(self, returns: np.ndarray) -> float:
        """计算最大回撤"""
        cumulative = np.cumprod(1 + returns)
        running_max = np.maximum.accumulate(cumulative)
        drawdowns = (cumulative - running_max) / running_max
        return np.min(drawdowns)

    def _get_risk_level(self, metric: str, value: float) -> RiskLevel:  # pylint: disable=r0911
        """根据指标值获取风险等级"""
        thresholds = self._risk_thresholds.get(metric, {})
        if not thresholds:
            return RiskLevel.MEDIUM

        if metric == "sharpe_ratio":
            # 夏普比率越高风险越低
            if value >= thresholds["low"]:  # pylint: disable=no-else-return
                return RiskLevel.LOW
            elif value >= thresholds["medium"]:
                return RiskLevel.MEDIUM
            elif value >= thresholds["high"]:
                return RiskLevel.HIGH
            else:
                return RiskLevel.CRITICAL
        else:
            # 其他指标越高风险越高
            if value <= thresholds["low"]:  # pylint: disable=no-else-return
                return RiskLevel.LOW
            elif value <= thresholds["medium"]:
                return RiskLevel.MEDIUM
            elif value <= thresholds["high"]:
                return RiskLevel.HIGH
            else:
                return RiskLevel.CRITICAL
