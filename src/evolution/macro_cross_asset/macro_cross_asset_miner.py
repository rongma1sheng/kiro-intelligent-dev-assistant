"""宏观与跨资产因子挖掘器

白皮书依据: 第四章 4.1.15 宏观与跨资产因子挖掘器

本模块实现基于宏观经济和跨资产视角的因子挖掘，从宏观经济和跨资产视角挖掘因子，
捕捉系统性风险和资产配置机会。

Author: MIA Team
Date: 2026-01-25
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import pandas as pd
from loguru import logger

from src.evolution.genetic_miner import GeneticMiner, Individual
from src.evolution.macro_cross_asset.macro_cross_asset_operators import MacroCrossAssetOperatorRegistry


@dataclass
class MacroCrossAssetConfig:
    """宏观与跨资产配置

    白皮书依据: 第四章 4.1.15 宏观与跨资产因子挖掘器

    Attributes:
        correlation_threshold: 相关性阈值 [0, 1]
        spread_threshold: 利差阈值
        momentum_window: 动量计算窗口
        risk_lookback_period: 风险回溯期
    """

    correlation_threshold: float = 0.7
    spread_threshold: float = 0.02
    momentum_window: int = 20
    risk_lookback_period: int = 60


class MacroCrossAssetFactorMiner(GeneticMiner):
    """宏观与跨资产因子挖掘器

    白皮书依据: 第四章 4.1.15 宏观与跨资产因子挖掘器

    使用遗传算法挖掘基于宏观经济和跨资产视角的有效因子。支持10种核心宏观跨资产算子：
    1. yield_curve_slope - 收益率曲线斜率
    2. credit_spread_widening - 信用利差扩大
    3. currency_carry_trade - 货币套利交易
    4. commodity_momentum - 商品动量
    5. vix_term_structure - VIX期限结构
    6. cross_asset_correlation - 跨资产相关性
    7. macro_surprise_index - 宏观意外指数
    8. central_bank_policy_shift - 央行政策转向
    9. global_liquidity_flow - 全球流动性流动
    10. geopolitical_risk_index - 地缘政治风险指数

    应用场景：
    - 宏观对冲策略
    - 资产配置决策
    - 系统性风险管理

    Attributes:
        config: 宏观与跨资产配置
        operator_registry: 宏观跨资产算子注册表
        macro_signals: 宏观信号记录
    """

    def __init__(self, config: Optional[MacroCrossAssetConfig] = None, evolution_config: Optional[Any] = None):
        """初始化宏观与跨资产因子挖掘器

        Args:
            config: 宏观与跨资产配置
            evolution_config: 遗传算法配置（EvolutionConfig对象）

        Raises:
            ValueError: 当配置参数不合法时
        """
        # 初始化基类
        super().__init__(config=evolution_config)

        # 初始化宏观跨资产配置
        if config is None:
            config = MacroCrossAssetConfig()

        self.config = config

        # 验证配置
        self._validate_config()

        # 初始化算子注册表
        self.operator_registry = MacroCrossAssetOperatorRegistry()

        # 扩展算子白名单（添加宏观跨资产算子）
        self._extend_operator_whitelist()

        # 初始化宏观信号记录
        self.macro_signals: Dict[str, List[Dict[str, Any]]] = {}

        logger.info(
            f"初始化MacroCrossAssetFactorMiner: "
            f"correlation_threshold={self.config.correlation_threshold}, "
            f"spread_threshold={self.config.spread_threshold}"
        )

    def _validate_config(self) -> None:
        """验证配置参数

        Raises:
            ValueError: 当配置参数不合法时
        """
        if not 0 <= self.config.correlation_threshold <= 1:
            raise ValueError(f"correlation_threshold必须在[0, 1]范围内，" f"当前: {self.config.correlation_threshold}")

        if self.config.spread_threshold <= 0:
            raise ValueError(f"spread_threshold必须 > 0，" f"当前: {self.config.spread_threshold}")

        if self.config.momentum_window <= 0:
            raise ValueError(f"momentum_window必须 > 0，" f"当前: {self.config.momentum_window}")

        if self.config.risk_lookback_period <= 0:
            raise ValueError(f"risk_lookback_period必须 > 0，" f"当前: {self.config.risk_lookback_period}")

    def _extend_operator_whitelist(self) -> None:
        """扩展算子白名单

        将宏观跨资产专用算子添加到遗传算法的算子白名单中
        """
        macro_cross_asset_operators = [
            "yield_curve_slope",
            "credit_spread_widening",
            "currency_carry_trade",
            "commodity_momentum",
            "vix_term_structure",
            "cross_asset_correlation",
            "macro_surprise_index",
            "central_bank_policy_shift",
            "global_liquidity_flow",
            "geopolitical_risk_index",
        ]

        # 添加到基类的算子白名单
        if not hasattr(self, "operator_whitelist"):
            self.operator_whitelist = []

        self.operator_whitelist.extend(macro_cross_asset_operators)

        logger.debug(f"扩展算子白名单，新增{len(macro_cross_asset_operators)}个宏观跨资产算子")

    def analyze_yield_curve(self, short_rate: pd.Series, long_rate: pd.Series) -> pd.Series:
        """分析收益率曲线形态

        白皮书依据: 第四章 4.1.15 收益率曲线分析

        收益率曲线形态：
        1. 正常曲线：长期利率 > 短期利率（经济扩张）
        2. 倒挂曲线：长期利率 < 短期利率（经济衰退预警）
        3. 平坦曲线：长短期利率接近（经济转折点）

        Args:
            short_rate: 短期利率序列
            long_rate: 长期利率序列

        Returns:
            收益率曲线斜率（正值=正常，负值=倒挂）
        """
        if short_rate.empty or long_rate.empty:
            logger.warning("利率序列为空")
            return pd.Series(0, index=short_rate.index)

        # 计算收益率曲线斜率
        slope = long_rate - short_rate

        # 记录倒挂信号
        inversion_count = (slope < 0).sum()
        if inversion_count > 0:
            logger.warning(
                f"检测到{inversion_count}个收益率曲线倒挂信号 " f"({inversion_count / len(slope) * 100:.1f}%)"
            )

        return slope

    def detect_credit_stress(self, credit_spread: pd.Series, threshold: Optional[float] = None) -> pd.Series:
        """检测信用压力

        白皮书依据: 第四章 4.1.15 信用利差分析

        信用利差扩大通常预示：
        1. 信用风险上升
        2. 流动性紧张
        3. 经济衰退风险

        Args:
            credit_spread: 信用利差序列
            threshold: 压力阈值，None则使用配置值

        Returns:
            信用压力信号（1=压力，0=正常）
        """
        if credit_spread.empty:
            return pd.Series(0, index=credit_spread.index)

        if threshold is None:
            threshold = self.config.spread_threshold

        # 计算利差变化
        spread_change = credit_spread.diff()

        # 检测利差快速扩大
        stress_signal = (spread_change > threshold).astype(int)

        stress_count = stress_signal.sum()
        if stress_count > 0:
            logger.info(f"检测到{stress_count}个信用压力信号 " f"({stress_count / len(stress_signal) * 100:.1f}%)")

        return stress_signal

    def calculate_cross_asset_correlation(self, asset1: pd.Series, asset2: pd.Series, window: int = 60) -> pd.Series:
        """计算跨资产相关性

        白皮书依据: 第四章 4.1.15 跨资产相关性分析

        跨资产相关性变化反映：
        1. 风险传染
        2. 避险情绪
        3. 资产配置机会

        Args:
            asset1: 资产1收益率序列
            asset2: 资产2收益率序列
            window: 滚动窗口

        Returns:
            滚动相关系数序列
        """
        if asset1.empty or asset2.empty:
            return pd.Series(0, index=asset1.index)

        # 计算滚动相关系数
        correlation = asset1.rolling(window=window).corr(asset2)

        # 检测相关性突变
        corr_change = correlation.diff().abs()
        significant_changes = (corr_change > 0.3).sum()

        if significant_changes > 0:
            logger.info(f"检测到{significant_changes}个跨资产相关性突变 " f"(变化 > 0.3)")

        return correlation

    def assess_systemic_risk(self, data: pd.DataFrame) -> pd.Series:
        """评估系统性风险

        白皮书依据: 第四章 4.1.15 系统性风险评估

        综合多个宏观指标评估系统性风险：
        1. 收益率曲线形态
        2. 信用利差水平
        3. VIX期限结构
        4. 跨资产相关性

        Args:
            data: 包含宏观指标的数据框

        Returns:
            系统性风险指数（0-1，越高风险越大）
        """
        if data.empty:
            return pd.Series(0, index=data.index)

        risk_components = []

        # 1. 收益率曲线风险（倒挂=高风险）
        if "short_rate" in data.columns and "long_rate" in data.columns:
            slope = self.analyze_yield_curve(data["short_rate"], data["long_rate"])
            curve_risk = (slope < 0).astype(float)
            risk_components.append(curve_risk)

        # 2. 信用利差风险（扩大=高风险）
        if "credit_spread" in data.columns:
            spread = data["credit_spread"]
            spread_risk = (spread - spread.mean()) / (spread.std() + 1e-8)
            spread_risk = spread_risk.clip(0, 1)
            risk_components.append(spread_risk)

        # 3. 波动率风险（VIX高=高风险）
        if "vix" in data.columns:
            vix = data["vix"]
            vix_risk = (vix - vix.mean()) / (vix.std() + 1e-8)
            vix_risk = vix_risk.clip(0, 1)
            risk_components.append(vix_risk)

        # 综合风险评分
        if risk_components:
            systemic_risk = pd.concat(risk_components, axis=1).mean(axis=1)
        else:
            systemic_risk = pd.Series(0, index=data.index)

        logger.debug(f"系统性风险评估: mean={systemic_risk.mean():.4f}, " f"max={systemic_risk.max():.4f}")

        return systemic_risk

    def mine_factors(self, data: pd.DataFrame, returns: pd.Series, generations: int = 10) -> List[Individual]:
        """挖掘宏观与跨资产因子

        白皮书依据: 第四章 4.1.15 宏观与跨资产因子挖掘

        完整流程：
        1. 数据验证
        2. 初始化种群
        3. 适应度评估
        4. 遗传进化
        5. 返回最优因子

        Args:
            data: 宏观市场数据
            returns: 收益率数据
            generations: 进化代数

        Returns:
            最优因子列表

        Raises:
            ValueError: 当数据格式不正确时
        """
        logger.info(f"开始挖掘宏观与跨资产因子: " f"进化代数={generations}")

        # 1. 数据验证
        if data.empty:
            raise ValueError("输入数据为空")

        # 2. 初始化种群
        self.initialize_population()  # pylint: disable=e1120

        # 3. 适应度评估
        self.evaluate_fitness(data, returns)

        # 4. 遗传进化
        best_individual = self.evolve(generations=generations)  # pylint: disable=e1120

        # 5. 返回最优因子
        logger.info(f"宏观与跨资产因子挖掘完成，" f"最优因子适应度: {best_individual.fitness:.4f}")

        return self.population[:10]  # 返回前10个最优因子

    def get_macro_signal_report(self) -> Dict[str, Any]:
        """获取宏观信号报告

        Returns:
            宏观信号报告字典
        """
        total_signals = sum(len(signals) for signals in self.macro_signals.values())

        return {
            "total_macro_signals": total_signals,
            "signals_by_type": {signal_type: len(signals) for signal_type, signals in self.macro_signals.items()},
            "correlation_threshold": self.config.correlation_threshold,
            "spread_threshold": self.config.spread_threshold,
            "momentum_window": self.config.momentum_window,
            "risk_lookback_period": self.config.risk_lookback_period,
        }
