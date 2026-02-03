"""因子组合与交互因子挖掘器

白皮书依据: 第四章 4.1.15 因子组合与交互因子挖掘器
"""

from typing import Dict, List, Optional

import pandas as pd
from loguru import logger

from ..genetic_miner import EvolutionConfig, GeneticMiner, Individual
from .factor_combination_operators import (
    FactorCombinationConfig,
    conditional_factor_exposure,
    factor_interaction_term,
    factor_neutralization,
    factor_timing_signal,
    multi_factor_synergy,
    nonlinear_factor_combination,
)


class FactorCombinationInteractionMiner(GeneticMiner):
    """因子组合与交互因子挖掘器

    白皮书依据: 第四章 4.1.15 因子组合与交互因子挖掘器

    通过组合和交互现有因子,发现新的有效因子。

    核心算子 (6个):
    1. factor_interaction_term - 因子交互项
    2. nonlinear_factor_combination - 非线性因子组合
    3. conditional_factor_exposure - 条件因子暴露
    4. factor_timing_signal - 因子择时信号
    5. multi_factor_synergy - 多因子协同
    6. factor_neutralization - 因子中性化

    应用场景:
    - 因子增强和组合
    - 多因子策略构建
    - 因子择时
    """

    def __init__(
        self, config: Optional[EvolutionConfig] = None, combination_config: Optional[FactorCombinationConfig] = None
    ):
        """初始化因子组合与交互因子挖掘器

        Args:
            config: 进化配置
            combination_config: 因子组合配置
        """
        if config is None:
            config = EvolutionConfig()

        super().__init__(config=config)

        self.combination_config = combination_config or FactorCombinationConfig()

        # 存储已有因子
        self.existing_factors: Dict[str, pd.Series] = {}

        # 注册因子组合算子
        self._register_combination_operators()

        logger.info(
            f"FactorCombinationInteractionMiner初始化完成: "
            f"interaction_window={self.combination_config.interaction_window}, "
            f"max_factors={self.combination_config.max_factors}"
        )

    def _register_combination_operators(self):
        """注册因子组合算子到算子白名单"""
        self.combination_operators = {
            "factor_interaction_term": factor_interaction_term,
            "nonlinear_factor_combination": nonlinear_factor_combination,
            "conditional_factor_exposure": conditional_factor_exposure,
            "factor_timing_signal": factor_timing_signal,
            "multi_factor_synergy": multi_factor_synergy,
            "factor_neutralization": factor_neutralization,
        }

        # 确保operator_whitelist存在
        if not hasattr(self, "operator_whitelist"):
            self.operator_whitelist = []

        # 添加到白名单
        for op_name in self.combination_operators.keys():  # pylint: disable=consider-iterating-dictionary
            if op_name not in self.operator_whitelist:
                self.operator_whitelist.append(op_name)

        logger.info(f"注册了 {len(self.combination_operators)} 个因子组合算子")

    async def mine_factors(
        self, data: pd.DataFrame, returns: pd.Series, existing_factors: Dict[str, pd.Series], generations: int = 10
    ) -> List[Individual]:
        """挖掘因子组合与交互因子

        Args:
            data: 价格数据,列为股票代码
            returns: 收益率数据
            existing_factors: 已有因子字典 {name: series}
            generations: 进化代数

        Returns:
            List[Individual]: 挖掘出的因子列表
        """
        try:
            logger.info(f"开始挖掘因子组合与交互因子,已有因子数: {len(existing_factors)}")

            # 存储已有因子
            self.existing_factors = existing_factors

            # 初始化种群
            if not self.population:
                await self.initialize_population(data.columns.tolist())

            # 进化种群
            best_individual = await self.evolve(data, returns, generations)

            # 收集所有有效因子
            valid_factors = [
                ind for ind in self.population if ind.fitness > 0.1 and abs(ind.ic) > self.config.min_ic_threshold
            ]

            logger.info(
                f"因子组合与交互因子挖掘完成: "
                f"发现 {len(valid_factors)} 个有效因子, "
                f"最佳IC={best_individual.ic:.4f}"
            )

            return valid_factors

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"因子组合与交互因子挖掘失败: {e}")
            return []

    def calculate_combination_factor(  # pylint: disable=r0911
        self, operator_name: str, factors: Dict[str, pd.Series], **kwargs
    ) -> pd.Series:  # pylint: disable=r0911
        """计算单个组合因子

        Args:
            operator_name: 算子名称
            factors: 因子字典
            **kwargs: 额外参数

        Returns:
            pd.Series: 因子值
        """
        try:
            if operator_name not in self.combination_operators:
                logger.error(f"未知的因子组合算子: {operator_name}")
                return pd.Series(dtype="float64")

            operator_func = self.combination_operators[operator_name]

            # 准备参数
            if operator_name == "factor_interaction_term":  # pylint: disable=no-else-return
                # 需要两个因子
                if len(factors) < 2:
                    logger.warning("factor_interaction_term需要至少2个因子")
                    return pd.Series(dtype="float64")

                factor_list = list(factors.values())
                method = kwargs.get("method", "multiply")
                return operator_func(factor_list[0], factor_list[1], method=method)

            elif operator_name == "nonlinear_factor_combination":
                method = kwargs.get("method", "polynomial")
                degree = kwargs.get("degree", 2)
                return operator_func(factors, method=method, degree=degree)

            elif operator_name == "conditional_factor_exposure":
                # 需要两个因子:主因子和条件因子
                if len(factors) < 2:
                    logger.warning("conditional_factor_exposure需要至少2个因子")
                    return pd.Series(dtype="float64")

                factor_list = list(factors.values())
                threshold = kwargs.get("threshold", 0.0)
                return operator_func(factor_list[0], factor_list[1], threshold=threshold)

            elif operator_name == "factor_timing_signal":
                # 需要一个因子和收益率
                if len(factors) < 1:
                    logger.warning("factor_timing_signal需要至少1个因子")
                    return pd.Series(dtype="float64")

                factor = list(factors.values())[0]
                returns = kwargs.get("returns")
                if returns is None:
                    logger.warning("factor_timing_signal需要returns参数")
                    return pd.Series(dtype="float64")

                window = self.combination_config.timing_window
                return operator_func(factor, returns, window=window)

            elif operator_name == "multi_factor_synergy":
                window = self.combination_config.synergy_window
                return operator_func(factors, window=window)

            elif operator_name == "factor_neutralization":
                # 需要至少2个因子:待中性化因子和中性化因子
                if len(factors) < 2:
                    logger.warning("factor_neutralization需要至少2个因子")
                    return pd.Series(dtype="float64")

                factor_list = list(factors.items())
                main_factor = factor_list[0][1]
                neutralize_factors = {name: series for name, series in factor_list[1:]}  # pylint: disable=r1721
                method = self.combination_config.neutralization_method
                return operator_func(main_factor, neutralize_factors, method=method)

            else:
                logger.warning(f"未实现的算子: {operator_name}")
                return pd.Series(dtype="float64")

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"计算组合因子失败 ({operator_name}): {e}")
            return pd.Series(dtype="float64")

    def generate_interaction_factors(
        self, factors: Dict[str, pd.Series], max_combinations: int = 10
    ) -> Dict[str, pd.Series]:
        """生成交互因子

        Args:
            factors: 输入因子字典
            max_combinations: 最大组合数量

        Returns:
            Dict[str, pd.Series]: 交互因子字典
        """
        try:
            logger.info(f"开始生成交互因子,输入因子数: {len(factors)}")

            interaction_factors = {}
            count = 0

            # 生成两两交互
            factor_names = list(factors.keys())
            for i in range(len(factor_names)):  # pylint: disable=consider-using-enumerate
                for j in range(i + 1, len(factor_names)):
                    if count >= max_combinations:
                        break

                    name1 = factor_names[i]
                    name2 = factor_names[j]

                    # 乘法交互
                    interaction_name = f"{name1}_x_{name2}"
                    interaction_factor = self.calculate_combination_factor(
                        "factor_interaction_term", {name1: factors[name1], name2: factors[name2]}, method="multiply"
                    )

                    if not interaction_factor.empty:
                        interaction_factors[interaction_name] = interaction_factor
                        count += 1

                if count >= max_combinations:
                    break

            logger.info(f"生成了 {len(interaction_factors)} 个交互因子")

            return interaction_factors

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"生成交互因子失败: {e}")
            return {}

    def generate_nonlinear_combinations(
        self, factors: Dict[str, pd.Series], methods: List[str] = None, max_combinations: int = 5
    ) -> Dict[str, pd.Series]:
        """生成非线性组合因子

        Args:
            factors: 输入因子字典
            methods: 组合方法列表
            max_combinations: 最大组合数量

        Returns:
            Dict[str, pd.Series]: 非线性组合因子字典
        """
        try:
            if methods is None:
                methods = ["polynomial", "exponential", "logarithmic"]

            logger.info(f"开始生成非线性组合因子,方法: {methods}")

            nonlinear_factors = {}
            count = 0

            for method in methods:
                if count >= max_combinations:
                    break

                combination_name = f"nonlinear_{method}"
                combination_factor = self.calculate_combination_factor(
                    "nonlinear_factor_combination", factors, method=method, degree=2
                )

                if not combination_factor.empty:
                    nonlinear_factors[combination_name] = combination_factor
                    count += 1

            logger.info(f"生成了 {len(nonlinear_factors)} 个非线性组合因子")

            return nonlinear_factors

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"生成非线性组合因子失败: {e}")
            return {}

    def generate_conditional_factors(
        self, factors: Dict[str, pd.Series], max_combinations: int = 5
    ) -> Dict[str, pd.Series]:
        """生成条件因子

        Args:
            factors: 输入因子字典
            max_combinations: 最大组合数量

        Returns:
            Dict[str, pd.Series]: 条件因子字典
        """
        try:
            logger.info("开始生成条件因子")

            conditional_factors = {}
            count = 0

            factor_names = list(factors.keys())
            for i in range(len(factor_names)):  # pylint: disable=consider-using-enumerate
                for j in range(len(factor_names)):  # pylint: disable=consider-using-enumerate
                    if i == j or count >= max_combinations:
                        continue

                    name1 = factor_names[i]
                    name2 = factor_names[j]

                    conditional_name = f"{name1}_cond_{name2}"
                    conditional_factor = self.calculate_combination_factor(
                        "conditional_factor_exposure", {name1: factors[name1], name2: factors[name2]}, threshold=0.0
                    )

                    if not conditional_factor.empty:
                        conditional_factors[conditional_name] = conditional_factor
                        count += 1

            logger.info(f"生成了 {len(conditional_factors)} 个条件因子")

            return conditional_factors

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"生成条件因子失败: {e}")
            return {}

    def generate_timing_signals(self, factors: Dict[str, pd.Series], returns: pd.Series) -> Dict[str, pd.Series]:
        """生成择时信号

        Args:
            factors: 输入因子字典
            returns: 收益率数据

        Returns:
            Dict[str, pd.Series]: 择时信号字典
        """
        try:
            logger.info("开始生成择时信号")

            timing_signals = {}

            for name, factor in factors.items():
                signal_name = f"{name}_timing"
                timing_signal = self.calculate_combination_factor(
                    "factor_timing_signal", {name: factor}, returns=returns
                )

                if not timing_signal.empty:
                    timing_signals[signal_name] = timing_signal

            logger.info(f"生成了 {len(timing_signals)} 个择时信号")

            return timing_signals

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"生成择时信号失败: {e}")
            return {}

    def generate_neutralized_factors(
        self, factors: Dict[str, pd.Series], neutralize_against: List[str] = None
    ) -> Dict[str, pd.Series]:
        """生成中性化因子

        Args:
            factors: 输入因子字典
            neutralize_against: 需要中性化的因子名称列表

        Returns:
            Dict[str, pd.Series]: 中性化因子字典
        """
        try:
            logger.info("开始生成中性化因子")

            neutralized_factors = {}

            if neutralize_against is None:
                # 默认对所有其他因子中性化
                neutralize_against = list(factors.keys())

            for name, factor in factors.items():
                # 选择中性化因子(排除自己)
                neutralize_factors = {n: f for n, f in factors.items() if n != name and n in neutralize_against}

                if not neutralize_factors:
                    continue

                neutralized_name = f"{name}_neutralized"
                neutralized_factor = self.calculate_combination_factor(
                    "factor_neutralization", {name: factor, **neutralize_factors}
                )

                if not neutralized_factor.empty:
                    neutralized_factors[neutralized_name] = neutralized_factor

            logger.info(f"生成了 {len(neutralized_factors)} 个中性化因子")

            return neutralized_factors

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"生成中性化因子失败: {e}")
            return {}

    def analyze_factor_synergy(self, factors: Dict[str, pd.Series]) -> pd.Series:
        """分析因子协同效应

        Args:
            factors: 输入因子字典

        Returns:
            pd.Series: 协同效应时间序列
        """
        try:
            logger.info("开始分析因子协同效应")

            synergy = self.calculate_combination_factor("multi_factor_synergy", factors)

            if not synergy.empty:
                logger.info(f"协同效应分析完成: " f"均值={synergy.mean():.4f}, " f"标准差={synergy.std():.4f}")

            return synergy

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"分析因子协同效应失败: {e}")
            return pd.Series(dtype="float64")

    def generate_all_combinations(
        self, factors: Dict[str, pd.Series], returns: pd.Series, max_per_type: int = 5
    ) -> Dict[str, pd.Series]:
        """生成所有类型的组合因子

        Args:
            factors: 输入因子字典
            returns: 收益率数据
            max_per_type: 每种类型的最大数量

        Returns:
            Dict[str, pd.Series]: 所有组合因子字典
        """
        try:
            logger.info("开始生成所有类型的组合因子")

            all_combinations = {}

            # 1. 交互因子
            logger.info("生成交互因子...")
            interaction_factors = self.generate_interaction_factors(factors, max_combinations=max_per_type)
            all_combinations.update(interaction_factors)

            # 2. 非线性组合
            logger.info("生成非线性组合因子...")
            nonlinear_factors = self.generate_nonlinear_combinations(factors, max_combinations=max_per_type)
            all_combinations.update(nonlinear_factors)

            # 3. 条件因子
            logger.info("生成条件因子...")
            conditional_factors = self.generate_conditional_factors(factors, max_combinations=max_per_type)
            all_combinations.update(conditional_factors)

            # 4. 择时信号
            logger.info("生成择时信号...")
            timing_signals = self.generate_timing_signals(factors, returns)
            all_combinations.update(timing_signals)

            # 5. 中性化因子
            logger.info("生成中性化因子...")
            neutralized_factors = self.generate_neutralized_factors(factors)
            all_combinations.update(neutralized_factors)

            logger.info(f"生成了 {len(all_combinations)} 个组合因子")

            return all_combinations

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"生成所有组合因子失败: {e}")
            return {}
