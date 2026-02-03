"""事件驱动因子挖掘器

白皮书依据: 第四章 4.1.16 事件驱动因子挖掘器

本模块实现基于公司事件的因子挖掘，识别和量化各类公司事件对股价的影响。

Author: MIA Team
Date: 2026-01-25
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import pandas as pd
from loguru import logger

from src.evolution.event_driven.event_driven_operators import EventDrivenOperatorRegistry
from src.evolution.genetic_miner import GeneticMiner, Individual


@dataclass
class EventDrivenConfig:
    """事件驱动配置

    白皮书依据: 第四章 4.1.16 事件驱动因子挖掘器

    Attributes:
        event_window: 事件影响窗口（天）
        earnings_threshold: 盈利意外阈值
        merger_spread_threshold: 并购套利价差阈值
        min_event_impact: 最小事件影响阈值
    """

    event_window: int = 20
    earnings_threshold: float = 0.05
    merger_spread_threshold: float = 0.1
    min_event_impact: float = 0.01


class EventDrivenFactorMiner(GeneticMiner):
    """事件驱动因子挖掘器

    白皮书依据: 第四章 4.1.16 事件驱动因子挖掘器

    使用遗传算法挖掘基于公司事件的有效因子。支持15种核心事件驱动算子：
    1. earnings_surprise - 盈利意外
    2. merger_arbitrage_spread - 并购套利价差
    3. ipo_lockup_expiry - IPO锁定期到期
    4. dividend_announcement - 股息公告
    5. share_buyback_signal - 股票回购信号
    6. management_change - 管理层变动
    7. regulatory_approval - 监管批准
    8. product_launch - 产品发布
    9. earnings_guidance_revision - 业绩指引修正
    10. analyst_upgrade_downgrade - 分析师评级变动
    11. index_rebalancing - 指数再平衡
    12. corporate_action - 公司行动
    13. litigation_risk - 诉讼风险
    14. credit_rating_change - 信用评级变动
    15. activist_investor_entry - 激进投资者进入

    应用场景：
    - 事件套利策略
    - 特殊情况投资
    - 催化剂交易

    Attributes:
        event_config: 事件驱动配置
        operator_registry: 事件驱动算子注册表
        event_history: 事件历史记录
    """

    def __init__(self, config: Optional[EventDrivenConfig] = None, evolution_config: Optional[Any] = None):
        """初始化事件驱动因子挖掘器

        Args:
            config: 事件驱动配置
            evolution_config: 遗传算法配置（EvolutionConfig对象）

        Raises:
            ValueError: 当配置参数不合法时
        """
        # 初始化基类
        super().__init__(config=evolution_config)

        # 初始化事件驱动配置（存储为event_config，不覆盖self.config）
        if config is None:
            config = EventDrivenConfig()

        self.event_config = config

        # 验证配置
        self._validate_config()

        # 初始化算子注册表
        self.operator_registry = EventDrivenOperatorRegistry()

        # 扩展算子白名单（添加事件驱动算子）
        self._extend_operator_whitelist()

        # 初始化事件历史记录
        self.event_history: Dict[str, List[Dict[str, Any]]] = {}

        logger.info(
            f"初始化EventDrivenFactorMiner: "
            f"event_window={self.event_config.event_window}, "
            f"earnings_threshold={self.event_config.earnings_threshold}"
        )

    def _validate_config(self) -> None:
        """验证配置参数

        Raises:
            ValueError: 当配置参数不合法时
        """
        if self.event_config.event_window <= 0:
            raise ValueError(f"event_window必须 > 0，" f"当前: {self.event_config.event_window}")

        if not 0 <= self.event_config.earnings_threshold <= 1:
            raise ValueError(f"earnings_threshold必须在[0, 1]范围内，" f"当前: {self.event_config.earnings_threshold}")

        if not 0 <= self.event_config.merger_spread_threshold <= 1:
            raise ValueError(
                f"merger_spread_threshold必须在[0, 1]范围内，" f"当前: {self.event_config.merger_spread_threshold}"
            )

        if not 0 <= self.event_config.min_event_impact <= 1:
            raise ValueError(f"min_event_impact必须在[0, 1]范围内，" f"当前: {self.event_config.min_event_impact}")

    def _extend_operator_whitelist(self) -> None:
        """扩展算子白名单

        将事件驱动专用算子添加到遗传算法的算子白名单中
        """
        event_driven_operators = [
            "earnings_surprise",
            "merger_arbitrage_spread",
            "ipo_lockup_expiry",
            "dividend_announcement",
            "share_buyback_signal",
            "management_change",
            "regulatory_approval",
            "product_launch",
            "earnings_guidance_revision",
            "analyst_upgrade_downgrade",
            "index_rebalancing",
            "corporate_action",
            "litigation_risk",
            "credit_rating_change",
            "activist_investor_entry",
        ]

        # 添加到基类的算子白名单
        if not hasattr(self, "operator_whitelist"):
            self.operator_whitelist = []

        self.operator_whitelist.extend(event_driven_operators)

        logger.debug(f"扩展算子白名单，新增{len(event_driven_operators)}个事件驱动算子")

    def detect_earnings_events(self, data: pd.DataFrame) -> pd.Series:
        """检测盈利事件

        白皮书依据: 第四章 4.1.16 盈利事件检测

        盈利事件包括：
        1. 盈利意外
        2. 业绩指引修正

        Args:
            data: 市场数据

        Returns:
            盈利事件信号 (1=显著事件, 0=无事件)
        """
        if data.empty:
            return pd.Series(0, index=data.index)

        # 1. 盈利意外
        earnings_surprise = self.operator_registry.earnings_surprise(data, window=self.event_config.event_window)

        # 2. 业绩指引修正
        guidance_revision = self.operator_registry.earnings_guidance_revision(
            data, window=self.event_config.event_window
        )

        # 综合盈利事件信号
        earnings_event = (
            (earnings_surprise.abs() > self.event_config.earnings_threshold)
            | (guidance_revision.abs() > self.event_config.min_event_impact)
        ).astype(int)

        event_count = earnings_event.sum()
        if event_count > 0:
            logger.info(f"检测到{event_count}个盈利事件 " f"({event_count / len(earnings_event) * 100:.1f}%)")

        return earnings_event

    def detect_ma_events(self, data: pd.DataFrame) -> pd.Series:
        """检测并购事件

        白皮书依据: 第四章 4.1.16 并购事件检测

        并购事件包括：
        1. 并购套利机会
        2. 监管批准

        Args:
            data: 市场数据

        Returns:
            并购事件信号 (1=显著事件, 0=无事件)
        """
        if data.empty:
            return pd.Series(0, index=data.index)

        # 1. 并购套利价差
        merger_spread = self.operator_registry.merger_arbitrage_spread(data, window=self.event_config.event_window)

        # 2. 监管批准
        regulatory_approval = self.operator_registry.regulatory_approval(data, window=self.event_config.event_window)

        # 综合并购事件信号
        ma_event = ((merger_spread > self.event_config.merger_spread_threshold) | (regulatory_approval > 0)).astype(int)

        event_count = ma_event.sum()
        if event_count > 0:
            logger.info(f"检测到{event_count}个并购事件 " f"({event_count / len(ma_event) * 100:.1f}%)")

        return ma_event

    def detect_corporate_events(self, data: pd.DataFrame) -> pd.Series:
        """检测公司事件

        白皮书依据: 第四章 4.1.16 公司事件检测

        公司事件包括：
        1. 股息公告
        2. 股票回购
        3. 管理层变动
        4. 公司行动

        Args:
            data: 市场数据

        Returns:
            公司事件信号 (1=显著事件, 0=无事件)
        """
        if data.empty:
            return pd.Series(0, index=data.index)

        # 1. 股息公告
        dividend = self.operator_registry.dividend_announcement(data, window=self.event_config.event_window)

        # 2. 股票回购
        buyback = self.operator_registry.share_buyback_signal(data, window=self.event_config.event_window)

        # 3. 管理层变动
        management = self.operator_registry.management_change(data, window=self.event_config.event_window * 3)

        # 4. 公司行动
        corporate_action = self.operator_registry.corporate_action(data, window=self.event_config.event_window)

        # 综合公司事件信号
        corporate_event = (
            (dividend.abs() > self.event_config.min_event_impact)
            | (buyback > self.event_config.min_event_impact)
            | (management > 0)
            | (corporate_action > 0)
        ).astype(int)

        event_count = corporate_event.sum()
        if event_count > 0:
            logger.info(f"检测到{event_count}个公司事件 " f"({event_count / len(corporate_event) * 100:.1f}%)")

        return corporate_event

    def analyze_event_impact(self, data: pd.DataFrame) -> Dict[str, pd.Series]:
        """综合分析事件影响

        白皮书依据: 第四章 4.1.16 事件影响分析

        综合分析所有事件类型的影响：
        1. 盈利事件
        2. 并购事件
        3. 公司事件
        4. 市场事件
        5. 风险事件

        Args:
            data: 市场数据

        Returns:
            事件影响指标字典
        """
        if data.empty:
            return {}

        event_impacts = {}

        # 1. 盈利事件
        earnings_surprise = self.operator_registry.earnings_surprise(data, window=self.event_config.event_window)
        event_impacts["earnings_surprise"] = earnings_surprise

        # 2. 并购事件
        merger_spread = self.operator_registry.merger_arbitrage_spread(data, window=self.event_config.event_window)
        event_impacts["merger_spread"] = merger_spread

        # 3. 公司事件
        dividend = self.operator_registry.dividend_announcement(data, window=self.event_config.event_window)
        event_impacts["dividend"] = dividend

        buyback = self.operator_registry.share_buyback_signal(data, window=self.event_config.event_window)
        event_impacts["buyback"] = buyback

        # 4. 市场事件
        analyst_rating = self.operator_registry.analyst_upgrade_downgrade(data, window=self.event_config.event_window)
        event_impacts["analyst_rating"] = analyst_rating

        index_rebalancing = self.operator_registry.index_rebalancing(data, window=self.event_config.event_window)
        event_impacts["index_rebalancing"] = index_rebalancing

        # 5. 风险事件
        litigation = self.operator_registry.litigation_risk(data, window=self.event_config.event_window * 3)
        event_impacts["litigation"] = litigation

        credit_rating = self.operator_registry.credit_rating_change(data, window=self.event_config.event_window)
        event_impacts["credit_rating"] = credit_rating

        logger.debug(
            f"事件影响分析完成: "
            f"earnings_surprise_mean={earnings_surprise.mean():.4f}, "
            f"merger_spread_mean={merger_spread.mean():.4f}"
        )

        return event_impacts

    def calculate_event_composite_score(self, data: pd.DataFrame) -> pd.Series:
        """计算事件综合评分

        白皮书依据: 第四章 4.1.16 事件综合评分

        综合多个事件指标计算总体事件评分：
        - 正值：正面事件
        - 负值：负面事件

        Args:
            data: 市场数据

        Returns:
            事件综合评分
        """
        if data.empty:
            return pd.Series(0, index=data.index)

        # 获取所有事件影响
        event_impacts = self.analyze_event_impact(data)

        if not event_impacts:
            return pd.Series(0, index=data.index)

        # 加权平均计算综合评分
        weights = {
            "earnings_surprise": 0.25,
            "merger_spread": 0.15,
            "dividend": 0.10,
            "buyback": 0.10,
            "analyst_rating": 0.10,
            "index_rebalancing": 0.10,
            "litigation": -0.10,  # 负面事件
            "credit_rating": 0.10,
        }

        composite_score = pd.Series(0.0, index=data.index)
        total_weight = 0.0

        for event_name, weight in weights.items():
            if event_name in event_impacts:
                impact = event_impacts[event_name]
                # 归一化
                impact_norm = (impact - impact.mean()) / (impact.std() + 1e-8)
                impact_norm = impact_norm.clip(-3, 3) / 3
                composite_score += impact_norm * weight
                total_weight += abs(weight)

        if total_weight > 0:
            composite_score /= total_weight

        logger.debug(f"事件综合评分: mean={composite_score.mean():.4f}, " f"std={composite_score.std():.4f}")

        return composite_score

    def identify_catalyst_events(self, data: pd.DataFrame, threshold: float = 0.5) -> List[Dict[str, Any]]:
        """识别催化剂事件

        白皮书依据: 第四章 4.1.16 催化剂事件识别

        催化剂事件是可能导致股价显著变动的重要事件。

        Args:
            data: 市场数据
            threshold: 催化剂阈值

        Returns:
            催化剂事件列表
        """
        if data.empty:
            return []

        catalysts = []

        # 获取事件综合评分
        composite_score = self.calculate_event_composite_score(data)

        # 识别显著事件
        significant_events = composite_score.abs() > threshold

        for date, is_significant in significant_events.items():
            if is_significant:
                catalyst = {
                    "date": date,
                    "score": composite_score[date],
                    "type": "positive" if composite_score[date] > 0 else "negative",
                    "magnitude": abs(composite_score[date]),
                }
                catalysts.append(catalyst)

        logger.info(f"识别到{len(catalysts)}个催化剂事件")

        return catalysts

    async def mine_factors(self, data: pd.DataFrame, returns: pd.Series, generations: int = 10) -> List[Individual]:
        """挖掘事件驱动因子

        白皮书依据: 第四章 4.1.16 事件驱动因子挖掘

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
        logger.info(f"开始挖掘事件驱动因子: " f"进化代数={generations}")

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
        logger.info(f"事件驱动因子挖掘完成，" f"最优因子适应度: {best_individual.fitness:.4f}")

        return self.population[:10]  # 返回前10个最优因子

    def get_event_report(self) -> Dict[str, Any]:
        """获取事件报告

        Returns:
            事件报告字典
        """
        total_events = sum(len(events) for events in self.event_history.values())

        return {
            "total_events": total_events,
            "events_by_type": {event_type: len(events) for event_type, events in self.event_history.items()},
            "event_window": self.event_config.event_window,
            "earnings_threshold": self.event_config.earnings_threshold,
            "merger_spread_threshold": self.event_config.merger_spread_threshold,
            "min_event_impact": self.event_config.min_event_impact,
        }
