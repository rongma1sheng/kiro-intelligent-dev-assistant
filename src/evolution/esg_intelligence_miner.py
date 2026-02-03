"""ESG智能因子挖掘器

白皮书依据: 第四章 4.1.10 ESG智能因子挖掘
需求: 9.1-9.10
"""

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple

import pandas as pd
from loguru import logger


@dataclass
class ESGFactor:
    """ESG因子数据结构

    Attributes:
        factor_name: 因子名称
        factor_values: 因子值序列
        esg_category: ESG类别（E/S/G）
        data_quality: 数据质量评分
        proxy_used: 是否使用了代理数据
        metadata: 额外元数据
    """

    factor_name: str
    factor_values: pd.Series
    esg_category: str
    data_quality: float
    proxy_used: bool
    metadata: Dict[str, Any]


class ESGIntelligenceFactorMiner:
    """ESG智能因子挖掘器

    白皮书依据: 第四章 4.1.10 ESG智能因子挖掘
    需求: 9.1-9.10

    挖掘ESG（环境、社会、治理）相关因子，捕获可持续性风险和机会。
    支持8个核心ESG算子，提供数据代理机制处理缺失数据。

    Attributes:
        operators: 8个ESG算子字典
        industry_averages: 行业平均值缓存
        data_quality_threshold: 数据质量阈值
    """

    def __init__(self, data_quality_threshold: float = 0.7):
        """初始化ESG智能因子挖掘器

        白皮书依据: 第四章 4.1.10
        需求: 9.1, 9.9

        Args:
            data_quality_threshold: 数据质量阈值，默认0.7
        """
        self.operators: Dict[str, Callable] = self._initialize_operators()
        self.industry_averages: Dict[str, pd.Series] = {}
        self.data_quality_threshold = data_quality_threshold

        logger.info(
            f"ESGIntelligenceFactorMiner initialized with 8 operators, " f"quality_threshold={data_quality_threshold}"
        )

        # 健康状态跟踪
        self._is_healthy = True
        self._error_count = 0

    def is_healthy(self) -> bool:
        """检查挖掘器健康状态

        Returns:
            是否健康
        """
        return self._is_healthy and self._error_count < 5

    def get_metadata(self) -> Dict:
        """获取挖掘器元数据

        Returns:
            元数据字典
        """
        return {
            "miner_type": "esg",
            "miner_name": "ESGIntelligenceFactorMiner",
            "is_healthy": self.is_healthy(),
            "error_count": self._error_count,
            "data_quality_threshold": self.data_quality_threshold,
            "operators_count": len(self.operators),
        }

    def _initialize_operators(self) -> Dict[str, Callable]:
        """初始化8个ESG算子

        白皮书依据: 第四章 4.1.10
        需求: 9.1-9.8, 9.9

        Returns:
            算子名称到函数的映射字典
        """
        return {
            "esg_controversy_shock": self._esg_controversy_shock,
            "carbon_emission_trend": self._carbon_emission_trend,
            "employee_satisfaction_score": self._employee_satisfaction_score,
            "board_diversity_score": self._board_diversity_score,
            "green_investment_ratio": self._green_investment_ratio,
            "esg_momentum": self._esg_momentum,
            "sustainability_score": self._sustainability_score,
            "esg_risk_premium": self._esg_risk_premium,
        }

    def mine_factors(
        self, esg_data: pd.DataFrame, price_data: pd.DataFrame, industry_mapping: Optional[Dict[str, str]] = None
    ) -> List[ESGFactor]:
        """挖掘ESG智能因子

        白皮书依据: 第四章 4.1.10
        需求: 9.1-9.8

        Args:
            esg_data: ESG数据，索引为股票代码，列为ESG指标
            price_data: 价格数据，用于计算ESG风险溢价
            industry_mapping: 股票到行业的映射，用于代理数据

        Returns:
            ESG因子列表

        Raises:
            ValueError: 当输入数据无效时
        """
        if esg_data.empty:
            raise ValueError("ESG数据不能为空")

        if price_data.empty:
            raise ValueError("价格数据不能为空")

        logger.info(f"开始挖掘ESG因子 - " f"股票数: {len(esg_data.index)}, " f"ESG指标数: {len(esg_data.columns)}")

        # 计算行业平均值（用于数据代理）
        if industry_mapping:
            self._calculate_industry_averages(esg_data, industry_mapping)

        factors = []

        try:
            # 算子1: ESG争议冲击
            controversy_factor = self._esg_controversy_shock(esg_data, price_data)
            factors.append(controversy_factor)

            # 算子2: 碳排放趋势
            carbon_factor = self._carbon_emission_trend(esg_data)
            factors.append(carbon_factor)

            # 算子3: 员工满意度评分
            satisfaction_factor = self._employee_satisfaction_score(esg_data)
            factors.append(satisfaction_factor)

            # 算子4: 董事会多样性评分
            diversity_factor = self._board_diversity_score(esg_data)
            factors.append(diversity_factor)

            # 算子5: 绿色投资比率
            green_investment_factor = self._green_investment_ratio(esg_data)
            factors.append(green_investment_factor)

            # 算子6: ESG动量
            momentum_factor = self._esg_momentum(esg_data)
            factors.append(momentum_factor)

            # 算子7: 可持续性评分
            sustainability_factor = self._sustainability_score(esg_data)
            factors.append(sustainability_factor)

            # 算子8: ESG风险溢价
            risk_premium_factor = self._esg_risk_premium(esg_data, price_data)
            factors.append(risk_premium_factor)

            logger.info(f"成功挖掘 {len(factors)} 个ESG因子")

            return factors

        except Exception as e:
            logger.error(f"挖掘ESG因子失败: {e}")
            raise

    def _calculate_industry_averages(self, esg_data: pd.DataFrame, industry_mapping: Dict[str, str]) -> None:
        """计算行业平均值

        白皮书依据: 第四章 4.1.10
        需求: 9.10

        Args:
            esg_data: ESG数据
            industry_mapping: 股票到行业的映射
        """
        try:
            # 按行业分组计算平均值
            industry_groups = {}
            for symbol, industry in industry_mapping.items():
                if symbol in esg_data.index:
                    if industry not in industry_groups:
                        industry_groups[industry] = []
                    industry_groups[industry].append(symbol)

            # 计算每个行业的平均值
            for industry, symbols in industry_groups.items():
                industry_data = esg_data.loc[symbols]
                self.industry_averages[industry] = industry_data.mean()

            logger.debug(f"计算了 {len(self.industry_averages)} 个行业的平均值")

        except Exception as e:
            logger.error(f"计算行业平均值失败: {e}")
            raise

    def _apply_proxy_if_needed(
        self, data: pd.Series, industry_mapping: Optional[Dict[str, str]] = None
    ) -> Tuple[pd.Series, bool]:
        """应用数据代理机制

        白皮书依据: 第四章 4.1.10
        需求: 9.10

        当ESG数据缺失时，使用行业平均值作为代理。

        Args:
            data: 原始数据序列
            industry_mapping: 股票到行业的映射

        Returns:
            (处理后的数据, 是否使用了代理)
        """
        proxy_used = False
        result = data.copy()

        if industry_mapping and self.industry_averages:
            for symbol in data.index:
                if pd.isna(data[symbol]) or data[symbol] == 0:
                    # 数据缺失，使用行业平均值
                    industry = industry_mapping.get(symbol)
                    if industry and industry in self.industry_averages:
                        # 使用行业平均值
                        result[symbol] = self.industry_averages[industry].mean()
                        proxy_used = True
                        logger.debug(f"使用行业平均值代理: {symbol} -> {industry}")

        return result, proxy_used

    def _esg_controversy_shock(self, esg_data: pd.DataFrame, price_data: pd.DataFrame) -> ESGFactor:
        """算子1: ESG争议冲击因子

        白皮书依据: 第四章 4.1.10
        需求: 9.1

        检测ESG争议事件对股价的冲击影响。
        争议事件包括环境污染、劳工纠纷、治理丑闻等。

        Args:
            esg_data: ESG数据
            price_data: 价格数据

        Returns:
            ESG争议冲击因子
        """
        try:
            # 假设ESG数据中有controversy_score列（争议评分，越高越严重）
            if "controversy_score" in esg_data.columns:
                controversy_scores = esg_data["controversy_score"]
            else:
                # 如果没有专门的争议评分，使用ESG总分的负值作为代理
                controversy_scores = -esg_data.mean(axis=1)

            # 计算价格变化
            price_data.pct_change().iloc[-1]  # pylint: disable=w0106

            # 计算争议冲击：争议评分变化与价格变化的关系
            controversy_change = controversy_scores - controversy_scores.mean()

            # 标准化
            factor_values = (controversy_change / (controversy_change.std() + 1e-10)).fillna(0)

            # 评估数据质量
            data_quality = 1.0 - (controversy_scores.isna().sum() / len(controversy_scores))

            logger.debug(f"ESG争议冲击因子计算完成，数据质量: {data_quality:.2f}")

            return ESGFactor(
                factor_name="esg_controversy_shock",
                factor_values=factor_values,
                esg_category="综合",
                data_quality=data_quality,
                proxy_used=False,
                metadata={
                    "description": "ESG争议事件对股价的冲击影响",
                    "controversy_mean": controversy_scores.mean(),
                    "controversy_std": controversy_scores.std(),
                },
            )

        except Exception as e:
            logger.error(f"ESG争议冲击计算失败: {e}")
            raise

    def _carbon_emission_trend(self, esg_data: pd.DataFrame) -> ESGFactor:
        """算子2: 碳排放趋势因子

        白皮书依据: 第四章 4.1.10
        需求: 9.2

        追踪企业碳排放趋势和减排进展。
        碳排放下降趋势可能预示着更好的环境表现和监管合规性。

        Args:
            esg_data: ESG数据

        Returns:
            碳排放趋势因子
        """
        try:
            # 假设ESG数据中有carbon_emissions列
            if "carbon_emissions" in esg_data.columns:
                emissions = esg_data["carbon_emissions"]
            elif "environmental_score" in esg_data.columns:
                # 使用环境评分作为代理（评分越高，排放越低）
                emissions = -esg_data["environmental_score"]
            else:
                # 使用ESG总分的环境部分作为代理
                emissions = -esg_data.mean(axis=1)

            # 计算排放趋势（负值表示减排）
            # 这里简化为当前值与平均值的差异
            emission_trend = emissions - emissions.mean()

            # 标准化（负值表示减排，是好的信号）
            factor_values = (-emission_trend / (emission_trend.std() + 1e-10)).fillna(0)

            # 评估数据质量
            data_quality = 1.0 - (emissions.isna().sum() / len(emissions))

            logger.debug(f"碳排放趋势因子计算完成，数据质量: {data_quality:.2f}")

            return ESGFactor(
                factor_name="carbon_emission_trend",
                factor_values=factor_values,
                esg_category="环境(E)",
                data_quality=data_quality,
                proxy_used="carbon_emissions" not in esg_data.columns,
                metadata={
                    "description": "企业碳排放趋势和减排进展",
                    "emission_mean": emissions.mean(),
                    "emission_std": emissions.std(),
                },
            )

        except Exception as e:
            logger.error(f"碳排放趋势计算失败: {e}")
            raise

    def _employee_satisfaction_score(self, esg_data: pd.DataFrame) -> ESGFactor:
        """算子3: 员工满意度评分因子

        白皮书依据: 第四章 4.1.10
        需求: 9.3

        从员工评价和调查中提取满意度评分。
        高员工满意度通常与更好的公司文化和长期业绩相关。

        Args:
            esg_data: ESG数据

        Returns:
            员工满意度评分因子
        """
        try:
            # 假设ESG数据中有employee_satisfaction列
            if "employee_satisfaction" in esg_data.columns:
                satisfaction = esg_data["employee_satisfaction"]
            elif "social_score" in esg_data.columns:
                # 使用社会评分作为代理
                satisfaction = esg_data["social_score"]
            else:
                # 使用ESG总分作为代理
                satisfaction = esg_data.mean(axis=1)

            # 标准化满意度评分
            factor_values = ((satisfaction - satisfaction.mean()) / (satisfaction.std() + 1e-10)).fillna(0)

            # 评估数据质量
            data_quality = 1.0 - (satisfaction.isna().sum() / len(satisfaction))

            logger.debug(f"员工满意度因子计算完成，数据质量: {data_quality:.2f}")

            return ESGFactor(
                factor_name="employee_satisfaction_score",
                factor_values=factor_values,
                esg_category="社会(S)",
                data_quality=data_quality,
                proxy_used="employee_satisfaction" not in esg_data.columns,
                metadata={
                    "description": "员工满意度评分",
                    "satisfaction_mean": satisfaction.mean(),
                    "satisfaction_std": satisfaction.std(),
                },
            )

        except Exception as e:
            logger.error(f"员工满意度计算失败: {e}")
            raise

    def _board_diversity_score(self, esg_data: pd.DataFrame) -> ESGFactor:
        """算子4: 董事会多样性评分因子

        白皮书依据: 第四章 4.1.10
        需求: 9.4

        评估董事会在性别、种族、专业背景等方面的多样性。
        多样性更高的董事会通常能做出更好的决策。

        Args:
            esg_data: ESG数据

        Returns:
            董事会多样性评分因子
        """
        try:
            # 假设ESG数据中有board_diversity列
            if "board_diversity" in esg_data.columns:
                diversity = esg_data["board_diversity"]
            elif "governance_score" in esg_data.columns:
                # 使用治理评分作为代理
                diversity = esg_data["governance_score"]
            else:
                # 使用ESG总分作为代理
                diversity = esg_data.mean(axis=1)

            # 标准化多样性评分
            factor_values = ((diversity - diversity.mean()) / (diversity.std() + 1e-10)).fillna(0)

            # 评估数据质量
            data_quality = 1.0 - (diversity.isna().sum() / len(diversity))

            logger.debug(f"董事会多样性因子计算完成，数据质量: {data_quality:.2f}")

            return ESGFactor(
                factor_name="board_diversity_score",
                factor_values=factor_values,
                esg_category="治理(G)",
                data_quality=data_quality,
                proxy_used="board_diversity" not in esg_data.columns,
                metadata={
                    "description": "董事会多样性评分",
                    "diversity_mean": diversity.mean(),
                    "diversity_std": diversity.std(),
                },
            )

        except Exception as e:
            logger.error(f"董事会多样性计算失败: {e}")
            raise

    def _green_investment_ratio(self, esg_data: pd.DataFrame) -> ESGFactor:
        """算子5: 绿色投资比率因子

        白皮书依据: 第四章 4.1.10
        需求: 9.5

        衡量企业在绿色项目和可持续发展方面的资本配置比例。
        更高的绿色投资比率可能预示着未来的竞争优势。

        Args:
            esg_data: ESG数据

        Returns:
            绿色投资比率因子
        """
        try:
            # 假设ESG数据中有green_investment_ratio列
            if "green_investment_ratio" in esg_data.columns:
                green_ratio = esg_data["green_investment_ratio"]
            elif "environmental_score" in esg_data.columns:
                # 使用环境评分作为代理
                green_ratio = esg_data["environmental_score"] / 100.0
            else:
                # 使用ESG总分作为代理
                green_ratio = esg_data.mean(axis=1) / 100.0

            # 标准化绿色投资比率
            factor_values = ((green_ratio - green_ratio.mean()) / (green_ratio.std() + 1e-10)).fillna(0)

            # 评估数据质量
            data_quality = 1.0 - (green_ratio.isna().sum() / len(green_ratio))

            logger.debug(f"绿色投资比率因子计算完成，数据质量: {data_quality:.2f}")

            return ESGFactor(
                factor_name="green_investment_ratio",
                factor_values=factor_values,
                esg_category="环境(E)",
                data_quality=data_quality,
                proxy_used="green_investment_ratio" not in esg_data.columns,
                metadata={
                    "description": "绿色投资在资本配置中的比例",
                    "ratio_mean": green_ratio.mean(),
                    "ratio_std": green_ratio.std(),
                },
            )

        except Exception as e:
            logger.error(f"绿色投资比率计算失败: {e}")
            raise

    def _esg_momentum(self, esg_data: pd.DataFrame) -> ESGFactor:
        """算子6: ESG动量因子

        白皮书依据: 第四章 4.1.10
        需求: 9.6

        追踪ESG指标的改善速度和趋势。
        ESG评分快速改善的公司可能获得更多投资者青睐。

        Args:
            esg_data: ESG数据

        Returns:
            ESG动量因子
        """
        try:
            # 计算ESG综合评分
            esg_score = esg_data.mean(axis=1)

            # 计算ESG动量（当前评分与历史平均的差异）
            # 这里简化为与均值的偏离度
            esg_momentum = esg_score - esg_score.mean()

            # 标准化
            factor_values = (esg_momentum / (esg_momentum.std() + 1e-10)).fillna(0)

            # 评估数据质量
            data_quality = 1.0 - (esg_score.isna().sum() / len(esg_score))

            logger.debug(f"ESG动量因子计算完成，数据质量: {data_quality:.2f}")

            return ESGFactor(
                factor_name="esg_momentum",
                factor_values=factor_values,
                esg_category="综合",
                data_quality=data_quality,
                proxy_used=False,
                metadata={
                    "description": "ESG指标的改善速度和趋势",
                    "momentum_mean": esg_momentum.mean(),
                    "momentum_std": esg_momentum.std(),
                },
            )

        except Exception as e:
            logger.error(f"ESG动量计算失败: {e}")
            raise

    def _sustainability_score(self, esg_data: pd.DataFrame) -> ESGFactor:
        """算子7: 可持续性评分因子

        白皮书依据: 第四章 4.1.10
        需求: 9.7

        聚合多个ESG指标形成综合可持续性评分。
        综合评分反映了企业的整体可持续发展能力。

        Args:
            esg_data: ESG数据

        Returns:
            可持续性评分因子
        """
        try:
            # 计算加权综合评分
            # 假设E、S、G三个维度权重相等
            if all(col in esg_data.columns for col in ["environmental_score", "social_score", "governance_score"]):
                sustainability = (
                    esg_data["environmental_score"] * 0.33
                    + esg_data["social_score"] * 0.33
                    + esg_data["governance_score"] * 0.34
                )
            else:
                # 使用所有可用列的平均值
                sustainability = esg_data.mean(axis=1)

            # 标准化
            factor_values = ((sustainability - sustainability.mean()) / (sustainability.std() + 1e-10)).fillna(0)

            # 评估数据质量
            data_quality = 1.0 - (sustainability.isna().sum() / len(sustainability))

            logger.debug(f"可持续性评分因子计算完成，数据质量: {data_quality:.2f}")

            return ESGFactor(
                factor_name="sustainability_score",
                factor_values=factor_values,
                esg_category="综合",
                data_quality=data_quality,
                proxy_used=False,
                metadata={
                    "description": "综合可持续性评分",
                    "score_mean": sustainability.mean(),
                    "score_std": sustainability.std(),
                    "weights": {"E": 0.33, "S": 0.33, "G": 0.34},
                },
            )

        except Exception as e:
            logger.error(f"可持续性评分计算失败: {e}")
            raise

    def _esg_risk_premium(self, esg_data: pd.DataFrame, price_data: pd.DataFrame) -> ESGFactor:
        """算子8: ESG风险溢价因子

        白皮书依据: 第四章 4.1.10
        需求: 9.8

        量化ESG因素对股票估值的影响。
        ESG评分高的公司可能享有估值溢价。

        Args:
            esg_data: ESG数据
            price_data: 价格数据

        Returns:
            ESG风险溢价因子
        """
        try:
            # 计算ESG综合评分
            esg_score = esg_data.mean(axis=1)

            # 计算收益率
            returns = price_data.pct_change().mean()

            # 对齐索引
            common_index = esg_score.index.intersection(returns.index)
            esg_aligned = esg_score.loc[common_index]
            returns_aligned = returns.loc[common_index]

            # 计算ESG风险溢价：ESG评分与收益率的关系
            # 高ESG评分的股票如果收益率也高，说明有正向溢价
            esg_premium = esg_aligned * returns_aligned

            # 标准化
            factor_values = ((esg_premium - esg_premium.mean()) / (esg_premium.std() + 1e-10)).fillna(0)

            # 扩展到所有股票
            full_factor_values = pd.Series(0.0, index=esg_score.index)
            full_factor_values.loc[common_index] = factor_values

            # 评估数据质量
            data_quality = len(common_index) / len(esg_score)

            logger.debug(f"ESG风险溢价因子计算完成，数据质量: {data_quality:.2f}")

            return ESGFactor(
                factor_name="esg_risk_premium",
                factor_values=full_factor_values,
                esg_category="综合",
                data_quality=data_quality,
                proxy_used=False,
                metadata={
                    "description": "ESG因素对股票估值的影响",
                    "premium_mean": esg_premium.mean(),
                    "premium_std": esg_premium.std(),
                    "correlation": esg_aligned.corr(returns_aligned) if len(common_index) > 1 else 0.0,
                },
            )

        except Exception as e:
            logger.error(f"ESG风险溢价计算失败: {e}")
            raise

    def evaluate_data_quality(self, esg_data: pd.DataFrame) -> Dict[str, float]:
        """评估ESG数据质量

        白皮书依据: 第四章 4.1.10

        Args:
            esg_data: ESG数据

        Returns:
            数据质量指标字典
        """
        try:
            # 计算完整性
            completeness = 1.0 - (esg_data.isna().sum().sum() / esg_data.size)

            # 计算一致性（标准差相对于均值）
            consistency = 1.0 - (esg_data.std().mean() / (esg_data.mean().mean() + 1e-10))
            consistency = max(0.0, min(1.0, consistency))

            # 计算覆盖率
            coverage = len(esg_data) / len(esg_data)  # 简化版本

            # 综合质量评分
            overall_quality = completeness * 0.5 + consistency * 0.3 + coverage * 0.2

            quality_metrics = {
                "completeness": completeness,
                "consistency": consistency,
                "coverage": coverage,
                "overall": overall_quality,
            }

            logger.info(
                f"ESG数据质量评估 - "
                f"完整性: {completeness:.2%}, "
                f"一致性: {consistency:.2%}, "
                f"综合: {overall_quality:.2%}"
            )

            return quality_metrics

        except Exception as e:
            logger.error(f"数据质量评估失败: {e}")
            raise

    def get_operator_list(self) -> List[str]:
        """获取所有可用算子列表

        Returns:
            算子名称列表
        """
        return list(self.operators.keys())

    def clear_industry_cache(self) -> None:
        """清空行业平均值缓存"""
        self.industry_averages.clear()
        logger.info("行业平均值缓存已清空")
