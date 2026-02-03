"""仓位管理分析器

白皮书依据: 第五章 5.2.22 仓位管理
引擎: Commander (战略级分析)
"""

from typing import Any, Dict, List, Optional

import numpy as np
from loguru import logger

from .data_models import PositionSizingAnalysis


class PositionSizingAnalyzer:
    """仓位管理分析器

    白皮书依据: 第五章 5.2.22 仓位管理

    分析内容:
    - Kelly公式计算最优仓位
    - 固定比例仓位计算
    - 波动率调整仓位
    - 风险预算仓位
    - 动态调整规则
    - 策略比较分析
    """

    # 默认参数
    DEFAULT_RISK_FREE_RATE: float = 0.03  # 无风险利率
    MAX_KELLY_FRACTION: float = 0.5  # Kelly上限
    MIN_POSITION: float = 0.05  # 最小仓位
    MAX_POSITION: float = 0.95  # 最大仓位

    def __init__(self, risk_free_rate: float = DEFAULT_RISK_FREE_RATE, max_kelly: float = MAX_KELLY_FRACTION):
        """初始化仓位管理分析器

        Args:
            risk_free_rate: 无风险利率
            max_kelly: Kelly公式上限
        """
        self.risk_free_rate = risk_free_rate
        self.max_kelly = max_kelly

        logger.info(f"PositionSizingAnalyzer初始化完成 - " f"无风险利率: {risk_free_rate}, Kelly上限: {max_kelly}")

    async def analyze(  # pylint: disable=too-many-positional-arguments
        self,
        strategy_id: str,
        returns: List[float],
        win_rate: Optional[float] = None,
        avg_win: Optional[float] = None,
        avg_loss: Optional[float] = None,
        current_volatility: Optional[float] = None,
        risk_budget: Optional[float] = None,
    ) -> PositionSizingAnalysis:
        """分析仓位管理

        Args:
            strategy_id: 策略ID
            returns: 历史收益率序列
            win_rate: 胜率（可选，如果不提供则从returns计算）
            avg_win: 平均盈利（可选）
            avg_loss: 平均亏损（可选）
            current_volatility: 当前波动率（可选）
            risk_budget: 风险预算（可选，默认2%）

        Returns:
            PositionSizingAnalysis: 仓位管理分析报告

        Raises:
            ValueError: 当收益数据不足时
        """
        if len(returns) < 20:
            raise ValueError("仓位分析至少需要20个收益数据点")

        logger.info(f"开始仓位管理分析: {strategy_id}")

        try:
            returns_array = np.array(returns)

            # 计算基础统计量
            if win_rate is None or avg_win is None or avg_loss is None:
                win_rate, avg_win, avg_loss = self._calculate_win_loss_stats(returns_array)

            if current_volatility is None:
                current_volatility = np.std(returns_array) * np.sqrt(252)

            if risk_budget is None:
                risk_budget = 0.02  # 默认2%风险预算

            # 1. 计算Kelly公式仓位
            kelly_fraction = self._calculate_kelly_fraction(win_rate, avg_win, avg_loss)

            # 2. 计算调整后的Kelly（半Kelly）
            adjusted_kelly = self._calculate_adjusted_kelly(kelly_fraction)

            # 3. 计算固定比例仓位
            fixed_fraction = self._calculate_fixed_fraction(returns_array, risk_budget)

            # 4. 计算波动率调整仓位
            volatility_adjusted = self._calculate_volatility_adjusted_position(returns_array, current_volatility)

            # 5. 计算风险预算仓位
            risk_budget_position = self._calculate_risk_budget_position(returns_array, risk_budget)

            # 6. 确定推荐仓位
            recommended_position = self._determine_recommended_position(
                kelly_fraction, adjusted_kelly, fixed_fraction, volatility_adjusted, risk_budget_position
            )

            # 7. 计算最大和最小仓位
            max_position = self._calculate_max_position(returns_array, current_volatility)
            min_position = self._calculate_min_position(returns_array)

            # 8. 生成动态调整规则
            dynamic_adjustment_rules = self._generate_dynamic_rules(returns_array, current_volatility, win_rate)

            # 9. 策略比较
            strategy_comparison = self._compare_strategies(
                kelly_fraction, adjusted_kelly, fixed_fraction, volatility_adjusted, risk_budget_position
            )

            # 10. 风险评估
            risk_assessment = self._assess_risk(returns_array, recommended_position, current_volatility)

            report = PositionSizingAnalysis(
                strategy_id=strategy_id,
                kelly_fraction=round(kelly_fraction, 4),
                adjusted_kelly=round(adjusted_kelly, 4),
                fixed_fraction=round(fixed_fraction, 4),
                volatility_adjusted=round(volatility_adjusted, 4),
                risk_budget_position=round(risk_budget_position, 4),
                recommended_position=round(recommended_position, 4),
                max_position=round(max_position, 4),
                min_position=round(min_position, 4),
                dynamic_adjustment_rules=dynamic_adjustment_rules,
                strategy_comparison=strategy_comparison,
                risk_assessment=risk_assessment,
            )

            logger.info(f"仓位管理分析完成: {strategy_id} - " f"推荐仓位: {recommended_position:.2%}")
            return report

        except Exception as e:
            logger.error(f"仓位管理分析失败: {strategy_id}, 错误: {e}")
            raise

    def _calculate_win_loss_stats(self, returns: np.ndarray) -> tuple:
        """计算胜率和盈亏统计

        Args:
            returns: 收益率数组

        Returns:
            tuple: (胜率, 平均盈利, 平均亏损)
        """
        wins = returns[returns > 0]
        losses = returns[returns < 0]

        win_rate = len(wins) / len(returns) if len(returns) > 0 else 0.5
        avg_win = np.mean(wins) if len(wins) > 0 else 0.01
        avg_loss = abs(np.mean(losses)) if len(losses) > 0 else 0.01

        return win_rate, avg_win, avg_loss

    def _calculate_kelly_fraction(self, win_rate: float, avg_win: float, avg_loss: float) -> float:
        """计算Kelly公式最优仓位

        Kelly公式: f* = (p * b - q) / b
        其中: p = 胜率, q = 1-p, b = 盈亏比

        Args:
            win_rate: 胜率
            avg_win: 平均盈利
            avg_loss: 平均亏损

        Returns:
            float: Kelly最优仓位 0-1
        """
        if avg_loss <= 0:
            return 0.0

        # 盈亏比
        b = avg_win / avg_loss

        # Kelly公式
        p = win_rate
        q = 1 - p

        kelly = (p * b - q) / b if b > 0 else 0

        # 限制在合理范围内
        kelly = max(0, min(self.max_kelly, kelly))

        return kelly

    def _calculate_adjusted_kelly(self, kelly_fraction: float) -> float:
        """计算调整后的Kelly（半Kelly）

        半Kelly可以降低波动，同时保留大部分收益

        Args:
            kelly_fraction: 原始Kelly仓位

        Returns:
            float: 调整后的Kelly仓位
        """
        # 使用半Kelly
        adjusted = kelly_fraction * 0.5

        # 确保在合理范围内
        return max(self.MIN_POSITION, min(self.MAX_POSITION, adjusted))

    def _calculate_fixed_fraction(self, returns: np.ndarray, risk_budget: float) -> float:
        """计算固定比例仓位

        基于最大回撤的固定比例方法

        Args:
            returns: 收益率数组
            risk_budget: 风险预算

        Returns:
            float: 固定比例仓位
        """
        # 计算最大回撤
        cumulative = np.cumprod(1 + returns)
        running_max = np.maximum.accumulate(cumulative)
        drawdowns = (running_max - cumulative) / running_max
        max_drawdown = np.max(drawdowns) if len(drawdowns) > 0 else 0.1

        if max_drawdown <= 0:
            max_drawdown = 0.1  # 默认10%

        # 固定比例 = 风险预算 / 最大回撤
        fixed_fraction = risk_budget / max_drawdown

        return max(self.MIN_POSITION, min(self.MAX_POSITION, fixed_fraction))

    def _calculate_volatility_adjusted_position(
        self, returns: np.ndarray, current_volatility: float  # pylint: disable=unused-argument
    ) -> float:  # pylint: disable=unused-argument
        """计算波动率调整仓位

        波动率越高，仓位越低

        Args:
            returns: 收益率数组
            current_volatility: 当前波动率

        Returns:
            float: 波动率调整仓位
        """
        # 目标波动率（年化15%）
        target_volatility = 0.15

        if current_volatility <= 0:
            current_volatility = 0.2  # 默认20%

        # 波动率调整因子
        vol_adjustment = target_volatility / current_volatility

        # 基础仓位50%
        base_position = 0.5

        adjusted_position = base_position * vol_adjustment

        return max(self.MIN_POSITION, min(self.MAX_POSITION, adjusted_position))

    def _calculate_risk_budget_position(self, returns: np.ndarray, risk_budget: float) -> float:
        """计算风险预算仓位

        基于VaR的风险预算方法

        Args:
            returns: 收益率数组
            risk_budget: 风险预算

        Returns:
            float: 风险预算仓位
        """
        # 计算95% VaR
        var_95 = np.percentile(returns, 5)

        if var_95 >= 0:
            # 如果VaR为正，说明策略很稳定
            return self.MAX_POSITION

        # 风险预算仓位 = 风险预算 / |VaR|
        risk_budget_position = risk_budget / abs(var_95)

        return max(self.MIN_POSITION, min(self.MAX_POSITION, risk_budget_position))

    def _determine_recommended_position(  # pylint: disable=too-many-positional-arguments
        self,
        kelly: float,  # pylint: disable=unused-argument
        adjusted_kelly: float,
        fixed_fraction: float,
        volatility_adjusted: float,
        risk_budget: float,  # pylint: disable=unused-argument
    ) -> float:
        """确定推荐仓位

        综合多种方法，取保守值

        Args:
            kelly: Kelly仓位
            adjusted_kelly: 调整后Kelly
            fixed_fraction: 固定比例
            volatility_adjusted: 波动率调整
            risk_budget: 风险预算

        Returns:
            float: 推荐仓位
        """
        # 收集所有有效仓位
        positions = [adjusted_kelly, fixed_fraction, volatility_adjusted, risk_budget]  # 优先使用半Kelly

        # 过滤掉异常值
        valid_positions = [p for p in positions if self.MIN_POSITION <= p <= self.MAX_POSITION]

        if not valid_positions:
            return 0.3  # 默认30%

        # 取中位数作为推荐值（更稳健）
        recommended = np.median(valid_positions)

        return max(self.MIN_POSITION, min(self.MAX_POSITION, recommended))

    def _calculate_max_position(self, returns: np.ndarray, current_volatility: float) -> float:
        """计算最大允许仓位

        Args:
            returns: 收益率数组
            current_volatility: 当前波动率

        Returns:
            float: 最大仓位
        """
        # 基于波动率的最大仓位
        # 波动率越高，最大仓位越低
        if current_volatility <= 0.1:
            max_pos = 0.95
        elif current_volatility <= 0.2:
            max_pos = 0.8
        elif current_volatility <= 0.3:
            max_pos = 0.6
        else:
            max_pos = 0.4

        # 考虑历史最大回撤
        cumulative = np.cumprod(1 + returns)
        running_max = np.maximum.accumulate(cumulative)
        drawdowns = (running_max - cumulative) / running_max
        max_drawdown = np.max(drawdowns) if len(drawdowns) > 0 else 0.1

        # 如果历史回撤很大，进一步降低最大仓位
        if max_drawdown > 0.3:
            max_pos *= 0.8
        elif max_drawdown > 0.2:
            max_pos *= 0.9

        return max(self.MIN_POSITION, min(self.MAX_POSITION, max_pos))

    def _calculate_min_position(self, returns: np.ndarray) -> float:
        """计算最小仓位

        Args:
            returns: 收益率数组

        Returns:
            float: 最小仓位
        """
        # 计算夏普比率
        mean_return = np.mean(returns)
        std_return = np.std(returns)

        if std_return > 0:
            sharpe = (mean_return - self.risk_free_rate / 252) / std_return * np.sqrt(252)
        else:
            sharpe = 0

        # 夏普比率越高，最小仓位可以越高
        if sharpe >= 2:
            min_pos = 0.2
        elif sharpe >= 1:
            min_pos = 0.1
        else:
            min_pos = 0.05

        return min_pos

    def _generate_dynamic_rules(
        self, returns: np.ndarray, current_volatility: float, win_rate: float  # pylint: disable=unused-argument
    ) -> List[str]:  # pylint: disable=unused-argument
        """生成动态调整规则

        Args:
            returns: 收益率数组
            current_volatility: 当前波动率
            win_rate: 胜率

        Returns:
            List[str]: 动态调整规则列表
        """
        rules = []

        # 波动率规则
        rules.append(f"当波动率超过{current_volatility * 1.5:.1%}时，仓位降低30%")
        rules.append(f"当波动率低于{current_volatility * 0.5:.1%}时，仓位可增加20%")

        # 连续亏损规则
        rules.append("连续亏损3次后，仓位降低50%")
        rules.append("连续盈利5次后，仓位可增加20%（但不超过最大仓位）")

        # 回撤规则
        rules.append("当回撤超过10%时，仓位降低至最小仓位")
        rules.append("当回撤恢复后，逐步恢复仓位")

        # 胜率规则
        if win_rate < 0.4:
            rules.append("当前胜率较低，建议保持较低仓位直到胜率恢复")
        elif win_rate > 0.6:
            rules.append("当前胜率较高，可适当增加仓位")

        # 市场环境规则
        rules.append("在市场极端波动期间（如VIX>30），仓位不超过30%")
        rules.append("在市场平稳期间，可按推荐仓位操作")

        return rules

    def _compare_strategies(  # pylint: disable=too-many-positional-arguments
        self, kelly: float, adjusted_kelly: float, fixed_fraction: float, volatility_adjusted: float, risk_budget: float
    ) -> Dict[str, Dict[str, float]]:
        """比较不同仓位策略

        Args:
            kelly: Kelly仓位
            adjusted_kelly: 调整后Kelly
            fixed_fraction: 固定比例
            volatility_adjusted: 波动率调整
            risk_budget: 风险预算

        Returns:
            Dict: 策略比较结果
        """
        return {
            "kelly": {
                "position": round(kelly, 4),
                "risk_level": "high",
                "expected_return": "highest",
                "volatility": "highest",
            },
            "half_kelly": {
                "position": round(adjusted_kelly, 4),
                "risk_level": "medium",
                "expected_return": "high",
                "volatility": "medium",
            },
            "fixed_fraction": {
                "position": round(fixed_fraction, 4),
                "risk_level": "medium",
                "expected_return": "medium",
                "volatility": "medium",
            },
            "volatility_adjusted": {
                "position": round(volatility_adjusted, 4),
                "risk_level": "low",
                "expected_return": "medium",
                "volatility": "low",
            },
            "risk_budget": {
                "position": round(risk_budget, 4),
                "risk_level": "low",
                "expected_return": "low",
                "volatility": "lowest",
            },
        }

    def _assess_risk(
        self, returns: np.ndarray, recommended_position: float, current_volatility: float
    ) -> Dict[str, Any]:
        """评估风险

        Args:
            returns: 收益率数组
            recommended_position: 推荐仓位
            current_volatility: 当前波动率

        Returns:
            Dict: 风险评估结果
        """
        # 计算预期最大回撤
        cumulative = np.cumprod(1 + returns)
        running_max = np.maximum.accumulate(cumulative)
        drawdowns = (running_max - cumulative) / running_max
        historical_max_dd = np.max(drawdowns) if len(drawdowns) > 0 else 0.1

        expected_max_dd = historical_max_dd * recommended_position

        # 计算预期波动率
        expected_volatility = current_volatility * recommended_position

        # 计算VaR
        var_95 = np.percentile(returns, 5) * recommended_position
        var_99 = np.percentile(returns, 1) * recommended_position

        # 风险等级评估
        if expected_max_dd > 0.2:
            risk_level = "high"
        elif expected_max_dd > 0.1:
            risk_level = "medium"
        else:
            risk_level = "low"

        return {
            "expected_max_drawdown": round(expected_max_dd, 4),
            "expected_volatility": round(expected_volatility, 4),
            "var_95": round(var_95, 4),
            "var_99": round(var_99, 4),
            "risk_level": risk_level,
            "warnings": self._generate_risk_warnings(expected_max_dd, expected_volatility, risk_level),
        }

    def _generate_risk_warnings(self, expected_max_dd: float, expected_volatility: float, risk_level: str) -> List[str]:
        """生成风险警告

        Args:
            expected_max_dd: 预期最大回撤
            expected_volatility: 预期波动率
            risk_level: 风险等级

        Returns:
            List[str]: 风险警告列表
        """
        warnings = []

        if expected_max_dd > 0.2:
            warnings.append(f"预期最大回撤{expected_max_dd:.1%}较高，建议降低仓位")

        if expected_volatility > 0.3:
            warnings.append(f"预期波动率{expected_volatility:.1%}较高，注意风险控制")

        if risk_level == "high":
            warnings.append("整体风险等级较高，建议谨慎操作")

        if not warnings:
            warnings.append("风险在可控范围内")

        return warnings
