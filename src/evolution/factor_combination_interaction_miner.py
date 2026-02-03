"""因子组合与交互挖掘器

白皮书依据: 第四章 4.1.15 因子组合与交互挖掘
需求: 14.1-14.8
设计文档: design.md - Factor Combination and Interaction Mining

实现6个因子组合算子，发现协同因子效应。
"""

from dataclasses import dataclass
from datetime import datetime
from itertools import combinations
from typing import Callable, Dict, List, Tuple

import numpy as np
import pandas as pd
from loguru import logger
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

from .unified_factor_mining_system import BaseMiner, FactorMetadata, MinerStatus, MinerType


@dataclass
class FactorInteraction:
    """因子交互

    Attributes:
        factor1: 第一个因子
        factor2: 第二个因子
        interaction_type: 交互类型
        interaction_strength: 交互强度
        synergy_score: 协同得分
    """

    factor1: str
    factor2: str
    interaction_type: str
    interaction_strength: float
    synergy_score: float


class FactorCombinationInteractionMiner(BaseMiner):
    """因子组合与交互挖掘器

    白皮书依据: 第四章 4.1.15 因子组合与交互挖掘
    需求: 14.1-14.8

    实现6个因子组合算子：
    1. factor_interaction_terms: 因子交互项
    2. nonlinear_combination: 非线性组合
    3. conditional_factor_exposure: 条件因子暴露
    4. factor_timing_signal: 因子时机信号
    5. multi_factor_synergy: 多因子协同
    6. factor_neutralization: 因子中性化

    Attributes:
        operators: 6个因子组合算子
        multicollinearity_threshold: 多重共线性阈值（默认0.9）
        min_factors: 最小因子数（默认2）
        max_factors: 最大因子数（默认5）
    """

    def __init__(self, multicollinearity_threshold: float = 0.9, min_factors: int = 2, max_factors: int = 5):
        """初始化因子组合与交互挖掘器

        白皮书依据: 第四章 4.1.15
        需求: 14.7, 14.8

        Args:
            multicollinearity_threshold: 多重共线性阈值，默认0.9
            min_factors: 最小因子数，默认2
            max_factors: 最大因子数，默认5

        Raises:
            ValueError: 当参数不在有效范围时
        """
        super().__init__(MinerType.FACTOR_COMBINATION, "FactorCombinationInteractionMiner")

        if not 0 < multicollinearity_threshold <= 1:
            raise ValueError(f"multicollinearity_threshold必须在 (0, 1]，" f"当前: {multicollinearity_threshold}")

        if min_factors < 2:
            raise ValueError(f"min_factors必须 >= 2，当前: {min_factors}")

        if max_factors < min_factors:
            raise ValueError(
                f"max_factors必须 >= min_factors，" f"当前: max_factors={max_factors}, min_factors={min_factors}"
            )

        self.multicollinearity_threshold = multicollinearity_threshold
        self.min_factors = min_factors
        self.max_factors = max_factors
        self.operators = self._initialize_operators()

        logger.info(
            f"初始化因子组合与交互挖掘器 - "
            f"multicollinearity_threshold={multicollinearity_threshold}, "
            f"min_factors={min_factors}, "
            f"max_factors={max_factors}, "
            f"operators={len(self.operators)}"
        )

    def _initialize_operators(self) -> Dict[str, Callable]:
        """初始化6个因子组合算子

        白皮书依据: 第四章 4.1.15
        需求: 14.1-14.6

        Returns:
            算子字典
        """
        return {
            "factor_interaction_terms": self._factor_interaction_terms,
            "nonlinear_combination": self._nonlinear_combination,
            "conditional_factor_exposure": self._conditional_factor_exposure,
            "factor_timing_signal": self._factor_timing_signal,
            "multi_factor_synergy": self._multi_factor_synergy,
            "factor_neutralization": self._factor_neutralization,
        }

    def _detect_multicollinearity(self, factors: pd.DataFrame) -> List[Tuple[str, str, float]]:
        """检测多重共线性

        白皮书依据: 第四章 4.1.15 多重共线性检测
        需求: 14.8

        当因子间相关性 > 0.9 时标记为冗余

        Args:
            factors: 因子DataFrame

        Returns:
            高相关因子对列表 [(factor1, factor2, correlation)]
        """
        try:
            # 计算相关矩阵
            corr_matrix = factors.corr()

            # 找出高相关因子对
            high_corr_pairs = []
            for i in range(len(corr_matrix.columns)):  # pylint: disable=consider-using-enumerate
                for j in range(i + 1, len(corr_matrix.columns)):
                    corr = abs(corr_matrix.iloc[i, j])
                    if corr > self.multicollinearity_threshold:
                        factor1 = corr_matrix.columns[i]
                        factor2 = corr_matrix.columns[j]
                        high_corr_pairs.append((factor1, factor2, corr))

                        logger.warning(
                            f"检测到多重共线性: {factor1} <-> {factor2}, "
                            f"相关性={corr:.4f} > 阈值={self.multicollinearity_threshold}"
                        )

            return high_corr_pairs

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"多重共线性检测失败: {e}")
            return []

    def _factor_interaction_terms(self, data: pd.DataFrame) -> pd.Series:
        """计算因子交互项

        白皮书依据: 第四章 4.1.15 因子交互
        需求: 14.1

        交互项 = factor1 * factor2
        捕捉因子间的非线性协同效应

        Args:
            data: 市场数据，包含多个因子列

        Returns:
            因子交互项序列

        Raises:
            ValueError: 当因子数量不足时
        """
        # 识别因子列（假设以factor_开头）
        factor_cols = [col for col in data.columns if col.startswith("factor_")]

        if len(factor_cols) < self.min_factors:
            raise ValueError(f"因子数量不足，需要至少{self.min_factors}个，" f"当前: {len(factor_cols)}")

        try:
            # 检测多重共线性
            factors_df = data[factor_cols]
            high_corr_pairs = self._detect_multicollinearity(factors_df)

            # 移除高相关因子对
            factors_to_remove = set()
            for factor1, factor2, _ in high_corr_pairs:
                # 保留第一个因子，移除第二个
                factors_to_remove.add(factor2)

            valid_factors = [f for f in factor_cols if f not in factors_to_remove]

            if len(valid_factors) < self.min_factors:
                logger.warning(f"移除高相关因子后，剩余因子数量不足: {len(valid_factors)}")
                valid_factors = factor_cols[: self.min_factors]

            # 计算所有因子对的交互项
            interaction_terms = []
            for factor1, factor2 in combinations(valid_factors, 2):
                interaction = data[factor1] * data[factor2]
                interaction_terms.append(interaction)

            # 综合交互项（取平均）
            if interaction_terms:
                combined_interaction = pd.concat(interaction_terms, axis=1).mean(axis=1)
            else:
                combined_interaction = pd.Series(0.0, index=data.index)

            logger.debug(
                f"因子交互项计算完成 - " f"有效因子数={len(valid_factors)}, " f"交互项数={len(interaction_terms)}"
            )

            return combined_interaction

        except Exception as e:
            logger.error(f"因子交互项计算失败: {e}")
            raise

    def _nonlinear_combination(self, data: pd.DataFrame) -> pd.Series:
        """创建非线性组合

        白皮书依据: 第四章 4.1.15 非线性组合
        需求: 14.2

        使用多种非线性变换：
        1. 平方项
        2. 对数项
        3. 指数项
        4. 交叉项

        Args:
            data: 市场数据，包含多个因子列

        Returns:
            非线性组合序列

        Raises:
            ValueError: 当因子数量不足时
        """
        factor_cols = [col for col in data.columns if col.startswith("factor_")]

        if len(factor_cols) < self.min_factors:
            raise ValueError(f"因子数量不足，需要至少{self.min_factors}个，" f"当前: {len(factor_cols)}")

        try:
            # 标准化因子
            scaler = StandardScaler()
            factors_scaled = pd.DataFrame(
                scaler.fit_transform(data[factor_cols]), columns=factor_cols, index=data.index
            )

            nonlinear_terms = []

            # 1. 平方项
            for factor in factor_cols:
                squared = factors_scaled[factor] ** 2
                nonlinear_terms.append(squared)

            # 2. 对数项（处理负值）
            for factor in factor_cols:
                # 将数据平移到正值域
                shifted = factors_scaled[factor] - factors_scaled[factor].min() + 1
                log_term = np.log(shifted)
                nonlinear_terms.append(log_term)

            # 3. 指数项（限制范围避免溢出）
            for factor in factor_cols:
                # 限制指数范围
                clipped = factors_scaled[factor].clip(-3, 3)
                exp_term = np.exp(clipped)
                nonlinear_terms.append(exp_term)

            # 4. 交叉项（选择前3个因子）
            top_factors = factor_cols[: min(3, len(factor_cols))]
            for factor1, factor2 in combinations(top_factors, 2):
                cross_term = factors_scaled[factor1] * factors_scaled[factor2]
                nonlinear_terms.append(cross_term)

            # 使用PCA降维
            if len(nonlinear_terms) > 0:
                nonlinear_matrix = pd.concat(nonlinear_terms, axis=1)

                # PCA降维到1维
                pca = PCA(n_components=1)
                combined = pca.fit_transform(nonlinear_matrix)
                combined_series = pd.Series(combined.flatten(), index=data.index)
            else:
                combined_series = pd.Series(0.0, index=data.index)

            logger.debug(f"非线性组合计算完成 - " f"非线性项数={len(nonlinear_terms)}")

            return combined_series

        except Exception as e:
            logger.error(f"非线性组合计算失败: {e}")
            raise

    def _conditional_factor_exposure(self, data: pd.DataFrame) -> pd.Series:
        """计算条件因子暴露

        白皮书依据: 第四章 4.1.15 条件暴露
        需求: 14.3

        根据市场状态调整因子暴露：
        - 牛市：增加动量因子暴露
        - 熊市：增加价值因子暴露
        - 震荡市：平衡暴露

        Args:
            data: 市场数据，包含因子和市场状态列

        Returns:
            条件因子暴露序列

        Raises:
            ValueError: 当必需列缺失时
        """
        required_cols = ["returns", "market_state"]
        missing_cols = [col for col in required_cols if col not in data.columns]
        if missing_cols:
            # 如果缺少market_state，根据收益率推断
            if "market_state" not in data.columns:
                # 使用移动平均判断市场状态
                ma_short = data["returns"].rolling(window=20).mean()
                ma_long = data["returns"].rolling(window=60).mean()

                data = data.copy()
                data["market_state"] = "neutral"
                data.loc[ma_short > ma_long, "market_state"] = "bull"
                data.loc[ma_short < ma_long, "market_state"] = "bear"

        try:
            factor_cols = [col for col in data.columns if col.startswith("factor_")]

            if len(factor_cols) < self.min_factors:
                raise ValueError(f"因子数量不足，需要至少{self.min_factors}个，" f"当前: {len(factor_cols)}")

            # 假设第一个因子是动量因子，第二个是价值因子
            momentum_factor = data[factor_cols[0]] if len(factor_cols) > 0 else pd.Series(0.0, index=data.index)
            value_factor = data[factor_cols[1]] if len(factor_cols) > 1 else pd.Series(0.0, index=data.index)

            # 根据市场状态调整权重
            conditional_exposure = pd.Series(0.0, index=data.index)

            # 牛市：70%动量 + 30%价值
            bull_mask = data["market_state"] == "bull"
            conditional_exposure[bull_mask] = 0.7 * momentum_factor[bull_mask] + 0.3 * value_factor[bull_mask]

            # 熊市：30%动量 + 70%价值
            bear_mask = data["market_state"] == "bear"
            conditional_exposure[bear_mask] = 0.3 * momentum_factor[bear_mask] + 0.7 * value_factor[bear_mask]

            # 震荡市：50%动量 + 50%价值
            neutral_mask = data["market_state"] == "neutral"
            conditional_exposure[neutral_mask] = 0.5 * momentum_factor[neutral_mask] + 0.5 * value_factor[neutral_mask]

            logger.debug(
                f"条件因子暴露计算完成 - "
                f"牛市比例={bull_mask.sum() / len(data):.2%}, "
                f"熊市比例={bear_mask.sum() / len(data):.2%}, "
                f"震荡市比例={neutral_mask.sum() / len(data):.2%}"
            )

            return conditional_exposure

        except Exception as e:
            logger.error(f"条件因子暴露计算失败: {e}")
            raise

    def _factor_timing_signal(self, data: pd.DataFrame) -> pd.Series:
        """生成因子时机信号

        白皮书依据: 第四章 4.1.15 因子时机
        需求: 14.4

        基于因子历史表现预测最佳使用时机：
        1. 因子动量：近期表现好的因子继续表现好
        2. 因子反转：长期表现差的因子可能反转
        3. 因子波动：低波动期增加暴露

        Args:
            data: 市场数据，包含因子和收益率列

        Returns:
            因子时机信号序列

        Raises:
            ValueError: 当必需列缺失时
        """
        if "returns" not in data.columns:
            raise ValueError("缺少必需列: returns")

        try:
            factor_cols = [col for col in data.columns if col.startswith("factor_")]

            if len(factor_cols) == 0:
                raise ValueError("未找到因子列")

            timing_signals = []

            for factor_col in factor_cols:
                # 1. 计算因子收益（因子值 * 未来收益）
                factor_returns = data[factor_col] * data["returns"].shift(-1)

                # 2. 因子动量（短期表现）
                factor_momentum = factor_returns.rolling(window=20).mean()

                # 3. 因子反转（长期表现）
                factor_long_term = factor_returns.rolling(window=60).mean()
                factor_reversal = -factor_long_term  # 反转信号

                # 4. 因子波动（低波动期增加权重）
                factor_volatility = factor_returns.rolling(window=20).std()
                volatility_signal = 1.0 / (1.0 + factor_volatility)

                # 综合时机信号
                timing = 0.4 * factor_momentum + 0.3 * factor_reversal + 0.3 * volatility_signal

                timing_signals.append(timing)

            # 综合所有因子的时机信号
            if timing_signals:
                combined_timing = pd.concat(timing_signals, axis=1).mean(axis=1)
            else:
                combined_timing = pd.Series(0.0, index=data.index)

            # 标准化
            combined_timing = ((combined_timing - combined_timing.mean()) / combined_timing.std()).fillna(0.0)

            logger.debug(f"因子时机信号计算完成 - " f"因子数={len(factor_cols)}")

            return combined_timing

        except Exception as e:
            logger.error(f"因子时机信号计算失败: {e}")
            raise

    def _multi_factor_synergy(self, data: pd.DataFrame) -> pd.Series:
        """测量多因子协同效应

        白皮书依据: 第四章 4.1.15 多因子协同
        需求: 14.5

        协同效应：多个因子组合的效果 > 单个因子效果之和

        测量方法：
        1. 计算单因子IC
        2. 计算组合因子IC
        3. 协同得分 = 组合IC - 单因子IC之和

        Args:
            data: 市场数据，包含因子和收益率列

        Returns:
            多因子协同信号序列

        Raises:
            ValueError: 当必需列缺失时
        """
        if "returns" not in data.columns:
            raise ValueError("缺少必需列: returns")

        try:
            factor_cols = [col for col in data.columns if col.startswith("factor_")]

            if len(factor_cols) < self.min_factors:
                raise ValueError(f"因子数量不足，需要至少{self.min_factors}个，" f"当前: {len(factor_cols)}")

            # 限制因子数量
            selected_factors = factor_cols[: min(self.max_factors, len(factor_cols))]

            # 1. 计算单因子IC
            single_ics = []
            for factor_col in selected_factors:
                ic = data[factor_col].corr(data["returns"], method="spearman")
                single_ics.append(abs(ic) if not np.isnan(ic) else 0.0)

            # 2. 计算组合因子（等权重）
            combined_factor = data[selected_factors].mean(axis=1)
            combined_ic = combined_factor.corr(data["returns"], method="spearman")
            combined_ic = abs(combined_ic) if not np.isnan(combined_ic) else 0.0

            # 3. 计算协同得分
            sum_single_ics = sum(single_ics)
            synergy_score = combined_ic - sum_single_ics

            # 创建协同信号（使用组合因子，权重由协同得分调整）
            synergy_weight = max(0.0, synergy_score)  # 只保留正协同
            synergy_signal = combined_factor * (1.0 + synergy_weight)

            logger.debug(
                f"多因子协同计算完成 - "
                f"因子数={len(selected_factors)}, "
                f"单因子IC之和={sum_single_ics:.4f}, "
                f"组合IC={combined_ic:.4f}, "
                f"协同得分={synergy_score:.4f}"
            )

            return synergy_signal

        except Exception as e:
            logger.error(f"多因子协同计算失败: {e}")
            raise

    def _factor_neutralization(self, data: pd.DataFrame) -> pd.Series:
        """执行因子中性化

        白皮书依据: 第四章 4.1.15 因子中性化
        需求: 14.6

        中性化：移除不想要的因子暴露
        例如：市场中性、行业中性、规模中性

        方法：正交化处理

        Args:
            data: 市场数据，包含因子和中性化目标列

        Returns:
            中性化后的因子序列

        Raises:
            ValueError: 当必需列缺失时
        """
        factor_cols = [col for col in data.columns if col.startswith("factor_")]

        if len(factor_cols) == 0:
            raise ValueError("未找到因子列")

        try:
            # 识别中性化目标（市场、行业、规模）
            neutralize_targets = []

            if "market_return" in data.columns:
                neutralize_targets.append("market_return")

            if "industry" in data.columns:
                # 行业哑变量
                industry_dummies = pd.get_dummies(data["industry"], prefix="industry")
                for col in industry_dummies.columns:
                    neutralize_targets.append(col)
                data = pd.concat([data, industry_dummies], axis=1)

            if "market_cap" in data.columns:
                neutralize_targets.append("market_cap")

            if not neutralize_targets:
                logger.warning("未找到中性化目标，返回原始因子")
                return data[factor_cols[0]]

            # 对每个因子执行正交化
            neutralized_factors = []

            for factor_col in factor_cols:
                # 构建回归矩阵
                X = data[neutralize_targets].fillna(0)
                y = data[factor_col].fillna(0)

                # 标准化
                X_scaled = (X - X.mean()) / X.std()
                y_scaled = (y - y.mean()) / y.std()

                # 正交化：residual = y - X * (X'X)^-1 * X'y
                try:
                    # 使用最小二乘法
                    from numpy.linalg import lstsq  # pylint: disable=import-outside-toplevel

                    beta = lstsq(X_scaled.values, y_scaled.values, rcond=None)[0]
                    y_pred = X_scaled.values @ beta
                    residual = y_scaled.values - y_pred

                    neutralized = pd.Series(residual, index=data.index)
                    neutralized_factors.append(neutralized)

                except Exception as e:  # pylint: disable=broad-exception-caught
                    logger.warning(f"因子 {factor_col} 正交化失败: {e}，使用原始值")
                    neutralized_factors.append(y_scaled)

            # 综合中性化因子
            if neutralized_factors:
                combined_neutralized = pd.concat(neutralized_factors, axis=1).mean(axis=1)
            else:
                combined_neutralized = pd.Series(0.0, index=data.index)

            logger.debug(f"因子中性化完成 - " f"因子数={len(factor_cols)}, " f"中性化目标数={len(neutralize_targets)}")

            return combined_neutralized

        except Exception as e:
            logger.error(f"因子中性化失败: {e}")
            raise

    def mine_factors(self, data: pd.DataFrame, returns: pd.Series, **kwargs) -> List[FactorMetadata]:
        """挖掘因子组合与交互因子

        白皮书依据: 第四章 4.1.15
        需求: 14.1-14.8

        Args:
            data: 市场数据DataFrame
            returns: 收益率序列
            **kwargs: 额外参数

        Returns:
            发现的因子列表

        Raises:
            ValueError: 当输入数据无效时
        """
        if data.empty:
            raise ValueError("输入数据不能为空")

        if len(returns) == 0:
            raise ValueError("收益率数据不能为空")

        try:
            self.metadata.status = MinerStatus.RUNNING
            logger.info("开始挖掘因子组合与交互因子...")

            # 确保数据包含returns列
            if "returns" not in data.columns:
                data = data.copy()
                data["returns"] = returns

            factors = []

            # 执行所有6个算子
            for operator_name, operator_func in self.operators.items():
                try:
                    logger.info(f"执行算子: {operator_name}")

                    # 执行算子
                    factor_values = operator_func(data)

                    # 计算因子指标
                    ic = self._calculate_ic(factor_values, returns)
                    ir = self._calculate_ir(factor_values, returns)
                    sharpe = self._calculate_sharpe(factor_values, returns)

                    # 计算综合适应度
                    fitness = abs(ic) * 0.4 + abs(ir) * 0.3 + abs(sharpe) * 0.3

                    # 创建因子元数据
                    factor = FactorMetadata(
                        factor_id=f"factor_combination_{operator_name}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                        factor_name=f"FactorCombination_{operator_name}",
                        factor_type=MinerType.FACTOR_COMBINATION,
                        data_source="market_data",
                        discovery_date=datetime.now(),
                        discoverer=self.miner_name,
                        expression=operator_name,
                        fitness=fitness,
                        ic=ic,
                        ir=ir,
                        sharpe=sharpe,
                    )

                    factors.append(factor)

                    logger.info(
                        f"算子 {operator_name} 完成 - "
                        f"IC={ic:.4f}, IR={ir:.4f}, Sharpe={sharpe:.4f}, "
                        f"Fitness={fitness:.4f}"
                    )

                except Exception as e:  # pylint: disable=broad-exception-caught
                    logger.error(f"算子 {operator_name} 执行失败: {e}")
                    continue

            # 更新元数据
            self.metadata.status = MinerStatus.COMPLETED
            self.metadata.total_factors_discovered += len(factors)
            self.metadata.last_run_time = datetime.now()

            if factors:
                avg_fitness = sum(f.fitness for f in factors) / len(factors)
                self.metadata.average_fitness = (
                    self.metadata.average_fitness * (self.metadata.total_factors_discovered - len(factors))
                    + avg_fitness * len(factors)
                ) / self.metadata.total_factors_discovered

            logger.info(
                f"因子组合与交互因子挖掘完成 - "
                f"发现因子数={len(factors)}, "
                f"平均适应度={self.metadata.average_fitness:.4f}"
            )

            return factors

        except Exception as e:
            self.metadata.status = MinerStatus.FAILED
            self.metadata.error_count += 1
            self.metadata.last_error = str(e)
            self.metadata.is_healthy = self.metadata.error_count < 5
            logger.error(f"因子组合与交互因子挖掘失败: {e}")
            raise

    def _calculate_ic(self, factor: pd.Series, returns: pd.Series) -> float:
        """计算信息系数（IC）"""
        try:
            common_index = factor.index.intersection(returns.index)
            if len(common_index) == 0:
                return 0.0

            factor_aligned = factor.loc[common_index]
            returns_aligned = returns.loc[common_index]

            ic = factor_aligned.corr(returns_aligned, method="spearman")
            return ic if not np.isnan(ic) else 0.0

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"IC计算失败: {e}")
            return 0.0

    def _calculate_ir(self, factor: pd.Series, returns: pd.Series) -> float:
        """计算信息比率（IR）"""
        try:
            window = min(60, len(factor))
            rolling_ic = []

            for i in range(window, len(factor)):
                ic = factor.iloc[i - window : i].corr(returns.iloc[i - window : i], method="spearman")
                if not np.isnan(ic):
                    rolling_ic.append(ic)

            if len(rolling_ic) == 0:
                return 0.0

            ic_mean = np.mean(rolling_ic)
            ic_std = np.std(rolling_ic)

            ir = ic_mean / ic_std if ic_std > 0 else 0.0
            return ir if not np.isnan(ir) else 0.0

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"IR计算失败: {e}")
            return 0.0

    def _calculate_sharpe(self, factor: pd.Series, returns: pd.Series) -> float:
        """计算夏普比率"""
        try:
            common_index = factor.index.intersection(returns.index)
            if len(common_index) == 0:
                return 0.0

            factor_aligned = factor.loc[common_index]
            returns_aligned = returns.loc[common_index]

            factor_returns = factor_aligned * returns_aligned

            mean_return = factor_returns.mean()
            std_return = factor_returns.std()

            sharpe = mean_return / std_return if std_return > 0 else 0.0
            sharpe_annualized = sharpe * np.sqrt(252)

            return sharpe_annualized if not np.isnan(sharpe_annualized) else 0.0

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"Sharpe计算失败: {e}")
            return 0.0
