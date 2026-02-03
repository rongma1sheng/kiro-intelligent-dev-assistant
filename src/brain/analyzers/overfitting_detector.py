"""过拟合检测器

白皮书依据: 第五章 5.2.3 过度拟合检测
引擎: Commander (战略级分析)
"""

import re
from typing import Any, Dict, List

import numpy as np
from loguru import logger

from .data_models import OverfittingReport


class OverfittingDetector:
    """过拟合检测器

    白皮书依据: 第五章 5.2.3 过度拟合检测

    检测内容:
    - 未来函数检测: 识别使用未来数据的代码
    - 参数比例分析: 参数数量/样本数量
    - 样本内外差异: IS vs OOS性能差距
    - 过拟合概率评估: 综合评估过拟合风险
    """

    # 未来函数关键词
    FUTURE_FUNCTION_PATTERNS = [
        r"shift\s*\(\s*-",  # 负向shift
        r"\.shift\s*\(\s*-\d+",  # pandas负向shift
        r"future",  # 包含future的变量
        r"next_",  # next_开头的变量
        r"tomorrow",  # tomorrow相关
        r"forward",  # forward相关
        r"\[i\s*\+\s*\d+\]",  # 正向索引
        r"\.iloc\s*\[\s*\d+\s*:\s*\]",  # 向后切片
    ]

    def __init__(self):
        """初始化过拟合检测器"""
        self._compiled_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.FUTURE_FUNCTION_PATTERNS]
        logger.info("OverfittingDetector初始化完成")

    async def analyze(self, strategy_id: str, strategy_data: Dict[str, Any]) -> OverfittingReport:
        """检测策略过拟合风险

        Args:
            strategy_id: 策略ID
            strategy_data: 策略数据

        Returns:
            OverfittingReport: 过拟合检测报告
        """
        logger.info(f"开始过拟合检测: {strategy_id}")

        try:
            strategy_code = strategy_data.get("code", "")
            parameters = strategy_data.get("parameters", {})
            is_returns = strategy_data.get("is_returns", [])  # 样本内收益
            oos_returns = strategy_data.get("oos_returns", [])  # 样本外收益
            sample_size = strategy_data.get("sample_size", len(is_returns))

            # 1. 检测未来函数
            future_functions = self._detect_future_functions(strategy_code)

            # 2. 计算参数比例
            parameter_ratio = self._calculate_parameter_ratio(parameters, sample_size)

            # 3. 计算样本内外差异
            is_oos_gap = self._calculate_is_oos_gap(is_returns, oos_returns)

            # 4. 收集过拟合证据
            evidence = self._collect_evidence(future_functions, parameter_ratio, is_oos_gap, is_returns, oos_returns)

            # 5. 计算过拟合概率
            overfitting_probability = self._calculate_overfitting_probability(
                future_functions, parameter_ratio, is_oos_gap
            )

            # 6. 生成修复建议
            suggestions = self._generate_suggestions(
                future_functions, parameter_ratio, is_oos_gap, overfitting_probability
            )

            # 7. 判断是否过拟合
            is_overfitted = overfitting_probability > 0.5 or len(future_functions) > 0

            report = OverfittingReport(
                strategy_id=strategy_id,
                future_functions=future_functions,
                parameter_ratio=parameter_ratio,
                is_oos_gap=is_oos_gap,
                overfitting_probability=overfitting_probability,
                evidence=evidence,
                suggestions=suggestions,
                is_overfitted=is_overfitted,
            )

            logger.info(
                f"过拟合检测完成: {strategy_id}, "
                f"过拟合概率: {overfitting_probability:.1%}, "
                f"是否过拟合: {is_overfitted}"
            )
            return report

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"过拟合检测失败: {strategy_id}, 错误: {e}")
            return OverfittingReport(
                strategy_id=strategy_id,
                future_functions=[],
                parameter_ratio=0.0,
                is_oos_gap=0.0,
                overfitting_probability=0.5,
                evidence=["检测失败"],
                suggestions=["建议人工审核策略代码"],
                is_overfitted=False,
            )

    def _detect_future_functions(self, strategy_code: str) -> List[str]:
        """检测未来函数

        Args:
            strategy_code: 策略代码

        Returns:
            List[str]: 检测到的未来函数列表
        """
        if not strategy_code:
            return []

        future_functions = []
        lines = strategy_code.split("\n")

        for i, line in enumerate(lines, 1):
            for pattern in self._compiled_patterns:
                matches = pattern.findall(line)
                if matches:
                    for match in matches:
                        future_functions.append(f"第{i}行: 检测到可能的未来函数 '{match}'")

        # 检查特定的危险模式
        dangerous_patterns = [
            ("close[i+1]", "使用了未来收盘价"),
            ("high[i+1]", "使用了未来最高价"),
            ("low[i+1]", "使用了未来最低价"),
            ("volume[i+1]", "使用了未来成交量"),
            (".shift(-", "使用了负向shift，可能引入未来数据"),
        ]

        for pattern, description in dangerous_patterns:
            if pattern in strategy_code.lower():
                future_functions.append(f"警告: {description}")

        return list(set(future_functions))  # 去重

    def _calculate_parameter_ratio(self, parameters: Dict[str, Any], sample_size: int) -> float:
        """计算参数比例

        Args:
            parameters: 策略参数
            sample_size: 样本数量

        Returns:
            float: 参数比例 (参数数量/样本数量)
        """
        if sample_size <= 0:
            return 0.0

        # 计算有效参数数量（排除固定参数）
        effective_params = 0
        for key, value in parameters.items():  # pylint: disable=unused-variable
            if isinstance(value, (int, float)):
                effective_params += 1
            elif isinstance(value, (list, tuple)):
                effective_params += len(value)
            elif isinstance(value, dict):
                effective_params += len(value)

        return effective_params / sample_size

    def _calculate_is_oos_gap(self, is_returns: List[float], oos_returns: List[float]) -> float:
        """计算样本内外差异

        Args:
            is_returns: 样本内收益
            oos_returns: 样本外收益

        Returns:
            float: 样本内外差异（夏普比率差）
        """
        if not is_returns or not oos_returns:
            return 0.0

        is_array = np.array(is_returns)
        oos_array = np.array(oos_returns)

        # 计算样本内夏普比率
        is_sharpe = 0.0
        if np.std(is_array) > 0:
            is_sharpe = np.mean(is_array) / np.std(is_array) * np.sqrt(252)

        # 计算样本外夏普比率
        oos_sharpe = 0.0
        if np.std(oos_array) > 0:
            oos_sharpe = np.mean(oos_array) / np.std(oos_array) * np.sqrt(252)

        # 计算差异
        gap = is_sharpe - oos_sharpe

        return gap

    def _collect_evidence(  # pylint: disable=too-many-positional-arguments
        self,
        future_functions: List[str],
        parameter_ratio: float,
        is_oos_gap: float,
        is_returns: List[float],
        oos_returns: List[float],
    ) -> List[str]:
        """收集过拟合证据

        Args:
            future_functions: 未来函数列表
            parameter_ratio: 参数比例
            is_oos_gap: 样本内外差异
            is_returns: 样本内收益
            oos_returns: 样本外收益

        Returns:
            List[str]: 证据列表
        """
        evidence = []

        # 未来函数证据
        if future_functions:
            evidence.append(f"检测到{len(future_functions)}个可能的未来函数")

        # 参数比例证据
        if parameter_ratio > 0.01:
            evidence.append(f"参数比例过高: {parameter_ratio:.4f} (建议<0.01)")
        elif parameter_ratio > 0.005:
            evidence.append(f"参数比例偏高: {parameter_ratio:.4f} (建议<0.005)")

        # 样本内外差异证据
        if is_oos_gap > 1.0:
            evidence.append(f"样本内外夏普比率差异过大: {is_oos_gap:.2f}")
        elif is_oos_gap > 0.5:
            evidence.append(f"样本内外夏普比率差异偏大: {is_oos_gap:.2f}")

        # 收益分布证据
        if is_returns and oos_returns:
            is_array = np.array(is_returns)
            oos_array = np.array(oos_returns)

            # 检查收益率差异
            is_mean = np.mean(is_array)
            oos_mean = np.mean(oos_array)
            if is_mean > 0 and oos_mean < 0:  # pylint: disable=r1716
                evidence.append("样本内盈利但样本外亏损，强烈过拟合信号")

            # 检查波动率差异
            is_vol = np.std(is_array)
            oos_vol = np.std(oos_array)
            if oos_vol > is_vol * 1.5:
                evidence.append("样本外波动率显著高于样本内")

            # 检查最大回撤差异
            is_dd = self._calculate_max_drawdown(is_array)
            oos_dd = self._calculate_max_drawdown(oos_array)
            if oos_dd < is_dd * 1.5:  # 回撤是负数
                evidence.append("样本外最大回撤显著大于样本内")

        if not evidence:
            evidence.append("未发现明显过拟合证据")

        return evidence

    def _calculate_overfitting_probability(
        self, future_functions: List[str], parameter_ratio: float, is_oos_gap: float
    ) -> float:
        """计算过拟合概率

        Args:
            future_functions: 未来函数列表
            parameter_ratio: 参数比例
            is_oos_gap: 样本内外差异

        Returns:
            float: 过拟合概率 0-1
        """
        probability = 0.0

        # 未来函数权重最高
        if future_functions:
            probability += min(0.4, len(future_functions) * 0.1)

        # 参数比例
        if parameter_ratio > 0.01:
            probability += 0.3
        elif parameter_ratio > 0.005:
            probability += 0.15
        elif parameter_ratio > 0.001:
            probability += 0.05

        # 样本内外差异
        if is_oos_gap > 1.5:
            probability += 0.3
        elif is_oos_gap > 1.0:
            probability += 0.2
        elif is_oos_gap > 0.5:
            probability += 0.1

        return min(1.0, probability)

    def _generate_suggestions(
        self, future_functions: List[str], parameter_ratio: float, is_oos_gap: float, overfitting_probability: float
    ) -> List[str]:
        """生成修复建议

        Args:
            future_functions: 未来函数列表
            parameter_ratio: 参数比例
            is_oos_gap: 样本内外差异
            overfitting_probability: 过拟合概率

        Returns:
            List[str]: 修复建议列表
        """
        suggestions = []

        # 未来函数建议
        if future_functions:
            suggestions.append("【紧急】移除所有未来函数，确保只使用历史数据")
            suggestions.append("检查所有shift操作，确保参数为正数")
            suggestions.append("审查数据对齐逻辑，避免前视偏差")

        # 参数比例建议
        if parameter_ratio > 0.01:
            suggestions.append("减少策略参数数量，简化模型")
            suggestions.append("使用正则化方法约束参数")
            suggestions.append("增加训练样本数量")
        elif parameter_ratio > 0.005:
            suggestions.append("考虑减少参数或增加样本")

        # 样本内外差异建议
        if is_oos_gap > 1.0:
            suggestions.append("使用滚动窗口验证替代固定划分")
            suggestions.append("增加样本外测试期长度")
            suggestions.append("考虑使用交叉验证")
        elif is_oos_gap > 0.5:
            suggestions.append("监控样本外表现，及时调整")

        # 通用建议
        if overfitting_probability > 0.5:
            suggestions.append("建议进行Walk-Forward分析")
            suggestions.append("使用Bootstrap方法评估稳定性")
            suggestions.append("考虑使用更简单的策略逻辑")

        if not suggestions:
            suggestions.append("策略过拟合风险较低，建议持续监控")

        return suggestions

    def _calculate_max_drawdown(self, returns: np.ndarray) -> float:
        """计算最大回撤"""
        if len(returns) == 0:
            return 0.0
        cumulative = np.cumprod(1 + returns)
        running_max = np.maximum.accumulate(cumulative)
        drawdowns = (cumulative - running_max) / running_max
        return np.min(drawdowns)
