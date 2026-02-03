"""ESG智能因子挖掘器

白皮书依据: 第四章 4.1.10 ESG智能因子挖掘器

本模块实现基于ESG（环境、社会、治理）的因子挖掘，捕捉可持续发展趋势和ESG风险。

Author: MIA Team
Date: 2026-01-25
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import pandas as pd
from loguru import logger

from src.evolution.esg_intelligence.esg_intelligence_operators import ESGIntelligenceOperatorRegistry
from src.evolution.genetic_miner import GeneticMiner, Individual


@dataclass
class ESGIntelligenceConfig:
    """ESG智能配置

    白皮书依据: 第四章 4.1.10 ESG智能因子挖掘器

    Attributes:
        esg_threshold: ESG评分阈值 [0, 1]
        controversy_threshold: 争议冲击阈值
        carbon_reduction_target: 碳减排目标（年度百分比）
        sustainability_window: 可持续性评估窗口（天）
    """

    esg_threshold: float = 0.6
    controversy_threshold: float = 0.5
    carbon_reduction_target: float = 0.05
    sustainability_window: int = 252


class ESGIntelligenceFactorMiner(GeneticMiner):
    """ESG智能因子挖掘器

    白皮书依据: 第四章 4.1.10 ESG智能因子挖掘器

    使用遗传算法挖掘基于ESG的有效因子。支持8种核心ESG智能算子：
    1. esg_controversy_shock - ESG争议冲击
    2. carbon_emission_trend - 碳排放趋势
    3. employee_satisfaction - 员工满意度
    4. board_diversity_score - 董事会多样性
    5. green_investment_ratio - 绿色投资比例
    6. esg_momentum - ESG改善动量
    7. sustainability_score - 可持续性评分
    8. esg_risk_premium - ESG风险溢价

    应用场景：
    - ESG投资策略
    - 可持续发展评估
    - ESG风险管理

    Attributes:
        esg_config: ESG智能配置
        operator_registry: ESG智能算子注册表
        esg_analysis: ESG分析结果记录
    """

    def __init__(self, config: Optional[ESGIntelligenceConfig] = None, evolution_config: Optional[Any] = None):
        """初始化ESG智能因子挖掘器

        Args:
            config: ESG智能配置
            evolution_config: 遗传算法配置（EvolutionConfig对象）

        Raises:
            ValueError: 当配置参数不合法时
        """
        # 初始化基类
        super().__init__(config=evolution_config)

        # 初始化ESG智能配置（存储为esg_config，不覆盖self.config）
        if config is None:
            config = ESGIntelligenceConfig()

        self.esg_config = config

        # 验证配置
        self._validate_config()

        # 初始化算子注册表
        self.operator_registry = ESGIntelligenceOperatorRegistry()

        # 扩展算子白名单（添加ESG智能算子）
        self._extend_operator_whitelist()

        # 初始化ESG分析结果记录
        self.esg_analysis: Dict[str, List[Dict[str, Any]]] = {}

        logger.info(
            f"初始化ESGIntelligenceFactorMiner: "
            f"esg_threshold={self.esg_config.esg_threshold}, "
            f"controversy_threshold={self.esg_config.controversy_threshold}"
        )

    def _validate_config(self) -> None:
        """验证配置参数

        Raises:
            ValueError: 当配置参数不合法时
        """
        if not 0 <= self.esg_config.esg_threshold <= 1:
            raise ValueError(f"esg_threshold必须在[0, 1]范围内，" f"当前: {self.esg_config.esg_threshold}")

        if not 0 <= self.esg_config.controversy_threshold <= 1:
            raise ValueError(
                f"controversy_threshold必须在[0, 1]范围内，" f"当前: {self.esg_config.controversy_threshold}"
            )

        if not 0 <= self.esg_config.carbon_reduction_target <= 1:
            raise ValueError(
                f"carbon_reduction_target必须在[0, 1]范围内，" f"当前: {self.esg_config.carbon_reduction_target}"
            )

        if self.esg_config.sustainability_window <= 0:
            raise ValueError(f"sustainability_window必须 > 0，" f"当前: {self.esg_config.sustainability_window}")

    def _extend_operator_whitelist(self) -> None:
        """扩展算子白名单

        将ESG智能专用算子添加到遗传算法的算子白名单中
        """
        esg_intelligence_operators = [
            "esg_controversy_shock",
            "carbon_emission_trend",
            "employee_satisfaction",
            "board_diversity_score",
            "green_investment_ratio",
            "esg_momentum",
            "sustainability_score",
            "esg_risk_premium",
        ]

        # 添加到基类的算子白名单
        if not hasattr(self, "operator_whitelist"):
            self.operator_whitelist = []

        self.operator_whitelist.extend(esg_intelligence_operators)

        logger.debug(f"扩展算子白名单，新增{len(esg_intelligence_operators)}个ESG智能算子")

    def detect_esg_risks(self, data: pd.DataFrame) -> pd.Series:
        """检测ESG风险

        白皮书依据: 第四章 4.1.10 ESG风险检测

        ESG风险包括：
        1. 争议冲击
        2. 碳排放超标
        3. 治理问题

        Args:
            data: 市场数据

        Returns:
            ESG风险信号 (1=高风险, 0=低风险)
        """
        if data.empty:
            return pd.Series(0, index=data.index)

        # 1. 争议冲击风险
        controversy_shock = self.operator_registry.esg_controversy_shock(data, window=60)

        # 2. 碳排放风险
        carbon_trend = self.operator_registry.carbon_emission_trend(data, window=self.esg_config.sustainability_window)

        # 3. 治理风险（董事会多样性低）
        board_diversity = self.operator_registry.board_diversity_score(
            data, window=self.esg_config.sustainability_window
        )

        # 综合ESG风险信号
        esg_risk = (
            (controversy_shock > self.esg_config.controversy_threshold)
            | (carbon_trend > self.esg_config.carbon_reduction_target)
            | (board_diversity < -0.5)
        ).astype(int)

        risk_count = esg_risk.sum()
        if risk_count > 0:
            logger.info(f"检测到{risk_count}个ESG风险信号 " f"({risk_count / len(esg_risk) * 100:.1f}%)")

        return esg_risk

    def detect_esg_opportunities(self, data: pd.DataFrame) -> pd.Series:
        """检测ESG投资机会

        白皮书依据: 第四章 4.1.10 ESG投资机会检测

        ESG投资机会包括：
        1. ESG改善动量强
        2. 可持续性评分高
        3. 绿色投资比例增加

        Args:
            data: 市场数据

        Returns:
            ESG投资机会信号 (1=机会, 0=无机会)
        """
        if data.empty:
            return pd.Series(0, index=data.index)

        # 1. ESG改善动量
        esg_momentum = self.operator_registry.esg_momentum(data, window=self.esg_config.sustainability_window)

        # 2. 可持续性评分
        sustainability = self.operator_registry.sustainability_score(data, window=self.esg_config.sustainability_window)

        # 3. 绿色投资比例
        green_investment = self.operator_registry.green_investment_ratio(
            data, window=self.esg_config.sustainability_window
        )

        # 综合ESG投资机会信号
        esg_opportunity = (
            (esg_momentum > 0.3) | (sustainability > self.esg_config.esg_threshold) | (green_investment > 0.5)
        ).astype(int)

        opportunity_count = esg_opportunity.sum()
        if opportunity_count > 0:
            logger.info(
                f"检测到{opportunity_count}个ESG投资机会 " f"({opportunity_count / len(esg_opportunity) * 100:.1f}%)"
            )

        return esg_opportunity

    def analyze_esg_impact(self, data: pd.DataFrame) -> Dict[str, pd.Series]:
        """综合分析ESG影响

        白皮书依据: 第四章 4.1.10 ESG影响分析

        综合分析所有ESG维度的影响：
        1. 环境（E）- 碳排放、绿色投资
        2. 社会（S）- 员工满意度
        3. 治理（G）- 董事会多样性
        4. 综合 - ESG动量、可持续性、风险溢价

        Args:
            data: 市场数据

        Returns:
            ESG影响指标字典
        """
        if data.empty:
            return {}

        esg_impacts = {}

        # 环境维度（E）
        carbon_trend = self.operator_registry.carbon_emission_trend(data, window=self.esg_config.sustainability_window)
        esg_impacts["carbon_trend"] = carbon_trend

        green_investment = self.operator_registry.green_investment_ratio(
            data, window=self.esg_config.sustainability_window
        )
        esg_impacts["green_investment"] = green_investment

        # 社会维度（S）
        employee_satisfaction = self.operator_registry.employee_satisfaction(data, window=60)
        esg_impacts["employee_satisfaction"] = employee_satisfaction

        # 治理维度（G）
        board_diversity = self.operator_registry.board_diversity_score(
            data, window=self.esg_config.sustainability_window
        )
        esg_impacts["board_diversity"] = board_diversity

        # 综合维度
        esg_momentum = self.operator_registry.esg_momentum(data, window=self.esg_config.sustainability_window)
        esg_impacts["esg_momentum"] = esg_momentum

        sustainability = self.operator_registry.sustainability_score(data, window=self.esg_config.sustainability_window)
        esg_impacts["sustainability"] = sustainability

        esg_premium = self.operator_registry.esg_risk_premium(data, window=self.esg_config.sustainability_window)
        esg_impacts["esg_premium"] = esg_premium

        controversy_shock = self.operator_registry.esg_controversy_shock(data, window=60)
        esg_impacts["controversy_shock"] = controversy_shock

        logger.debug(
            f"ESG影响分析完成: "
            f"sustainability_mean={sustainability.mean():.4f}, "
            f"esg_momentum_mean={esg_momentum.mean():.4f}"
        )

        return esg_impacts

    def calculate_esg_composite_score(self, data: pd.DataFrame) -> pd.Series:
        """计算ESG综合评分

        白皮书依据: 第四章 4.1.10 ESG综合评分

        综合多个ESG指标计算总体ESG评分：
        - 正值：ESG表现优秀
        - 负值：ESG表现不佳

        Args:
            data: 市场数据

        Returns:
            ESG综合评分 (-1到1)
        """
        if data.empty:
            return pd.Series(0, index=data.index)

        # 获取所有ESG影响
        esg_impacts = self.analyze_esg_impact(data)

        if not esg_impacts:
            return pd.Series(0, index=data.index)

        # 加权平均计算综合评分
        weights = {
            "carbon_trend": -0.15,  # 负面指标（碳排放增加是负面）
            "green_investment": 0.15,
            "employee_satisfaction": 0.15,
            "board_diversity": 0.15,
            "esg_momentum": 0.15,
            "sustainability": 0.20,
            "esg_premium": 0.10,
            "controversy_shock": -0.05,  # 负面指标
        }

        composite_score = pd.Series(0.0, index=data.index)
        total_weight = 0.0

        for indicator_name, weight in weights.items():
            if indicator_name in esg_impacts:
                indicator = esg_impacts[indicator_name]
                # 归一化到[-1, 1]
                indicator_norm = (indicator - indicator.mean()) / (indicator.std() + 1e-8)
                indicator_norm = indicator_norm.clip(-3, 3) / 3
                composite_score += indicator_norm * weight
                total_weight += abs(weight)

        if total_weight > 0:
            composite_score /= total_weight

        logger.debug(f"ESG综合评分: mean={composite_score.mean():.4f}, " f"std={composite_score.std():.4f}")

        return composite_score

    def identify_esg_leaders(self, data: pd.DataFrame, threshold: float = 0.6) -> List[Dict[str, Any]]:
        """识别ESG领先企业

        白皮书依据: 第四章 4.1.10 ESG领先企业识别

        ESG领先企业特征：
        1. ESG综合评分高
        2. 可持续性评分高
        3. ESG改善动量强

        Args:
            data: 市场数据
            threshold: ESG领先阈值

        Returns:
            ESG领先企业列表
        """
        if data.empty:
            return []

        leaders = []

        # 获取ESG综合评分
        composite_score = self.calculate_esg_composite_score(data)

        # 识别领先企业
        is_leader = composite_score > threshold

        for date, leader_flag in is_leader.items():
            if leader_flag:
                leader = {
                    "date": date,
                    "score": composite_score[date],
                    "rank": "leader",
                    "magnitude": composite_score[date],
                }
                leaders.append(leader)

        logger.info(f"识别到{len(leaders)}个ESG领先企业")

        return leaders

    async def mine_factors(self, data: pd.DataFrame, returns: pd.Series, generations: int = 10) -> List[Individual]:
        """挖掘ESG智能因子

        白皮书依据: 第四章 4.1.10 ESG智能因子挖掘

        完整流程：
        1. 数据验证
        2. 初始化种群
        3. 适应度评估
        4. 遗传进化
        5. 返回最优因子

        Args:
            data: 市场数据
            returns: 收益率数据
            generations: 进化代数

        Returns:
            最优因子列表

        Raises:
            ValueError: 当数据格式不正确时
        """
        logger.info(f"开始挖掘ESG智能因子: " f"进化代数={generations}")

        # 1. 数据验证
        if data.empty:
            raise ValueError("输入数据为空")

        # 2. 初始化种群
        await self.initialize_population(data_columns=data.columns.tolist())

        # 3. 适应度评估
        await self.evaluate_fitness(data, returns)

        # 4. 遗传进化
        best_individual = await self.evolve(data=data, returns=returns, generations=generations)

        # 5. 返回最优因子
        logger.info(f"ESG智能因子挖掘完成，" f"最优因子适应度: {best_individual.fitness:.4f}")

        return self.population[:10]  # 返回前10个最优因子

    def get_esg_report(self) -> Dict[str, Any]:
        """获取ESG分析报告

        Returns:
            ESG分析报告字典
        """
        total_analysis = sum(len(analysis) for analysis in self.esg_analysis.values())

        return {
            "total_esg_analysis": total_analysis,
            "analysis_by_type": {analysis_type: len(analysis) for analysis_type, analysis in self.esg_analysis.items()},
            "esg_threshold": self.esg_config.esg_threshold,
            "controversy_threshold": self.esg_config.controversy_threshold,
            "carbon_reduction_target": self.esg_config.carbon_reduction_target,
            "sustainability_window": self.esg_config.sustainability_window,
        }
