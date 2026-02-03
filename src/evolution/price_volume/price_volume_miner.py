"""量价关系因子挖掘器

白皮书依据: 第四章 4.1.11 量价关系因子挖掘器

本模块实现基于价格和成交量关系的因子挖掘，深度挖掘价格和成交量之间的关系，
识别资金流向和市场力量。

Author: MIA Team
Date: 2026-01-25
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import pandas as pd
from loguru import logger

from src.evolution.genetic_miner import GeneticMiner, Individual
from src.evolution.price_volume.price_volume_operators import PriceVolumeOperatorRegistry


@dataclass
class PriceVolumeConfig:
    """量价关系配置

    白皮书依据: 第四章 4.1.11 量价关系因子挖掘器

    Attributes:
        divergence_threshold: 背离阈值 [0, 1]
        volume_surge_multiplier: 成交量激增倍数
        vwap_deviation_threshold: VWAP偏离阈值
        correlation_window: 相关性计算窗口
    """

    divergence_threshold: float = 0.3
    volume_surge_multiplier: float = 2.0
    vwap_deviation_threshold: float = 0.02
    correlation_window: int = 20


class PriceVolumeRelationshipFactorMiner(GeneticMiner):
    """量价关系因子挖掘器

    白皮书依据: 第四章 4.1.11 量价关系因子挖掘器

    使用遗传算法挖掘基于量价关系的有效因子。支持12种核心量价算子：
    1. volume_price_correlation - 量价相关性
    2. obv_divergence - OBV背离
    3. vwap_deviation - VWAP偏离度
    4. volume_weighted_momentum - 成交量加权动量
    5. price_volume_trend - 价量趋势
    6. accumulation_distribution - 累积派发
    7. money_flow_index - 资金流量指数
    8. volume_surge_pattern - 成交量激增模式
    9. price_volume_breakout - 价量突破
    10. volume_profile_support - 成交量剖面支撑
    11. tick_volume_analysis - Tick成交量分析
    12. volume_weighted_rsi - 成交量加权RSI

    应用场景：
    - 趋势确认和反转识别
    - 支撑阻力判断
    - 资金流向分析

    Attributes:
        config: 量价关系配置
        operator_registry: 量价算子注册表
        divergence_signals: 背离信号记录
    """

    def __init__(self, config: Optional[PriceVolumeConfig] = None, evolution_config: Optional[Any] = None):
        """初始化量价关系因子挖掘器

        Args:
            config: 量价关系配置
            evolution_config: 遗传算法配置（EvolutionConfig对象）

        Raises:
            ValueError: 当配置参数不合法时
        """
        # 初始化基类
        super().__init__(config=evolution_config)

        # 初始化量价配置
        if config is None:
            config = PriceVolumeConfig()

        self.config = config

        # 验证配置
        self._validate_config()

        # 初始化算子注册表
        self.operator_registry = PriceVolumeOperatorRegistry()

        # 扩展算子白名单（添加量价算子）
        self._extend_operator_whitelist()

        # 初始化背离信号记录
        self.divergence_signals: Dict[str, List[Dict[str, Any]]] = {}

        logger.info(
            f"初始化PriceVolumeRelationshipFactorMiner: "
            f"divergence_threshold={self.config.divergence_threshold}, "
            f"volume_surge_multiplier={self.config.volume_surge_multiplier}"
        )

    def _validate_config(self) -> None:
        """验证配置参数

        Raises:
            ValueError: 当配置参数不合法时
        """
        if not 0 <= self.config.divergence_threshold <= 1:
            raise ValueError(f"divergence_threshold必须在[0, 1]范围内，" f"当前: {self.config.divergence_threshold}")

        if self.config.volume_surge_multiplier <= 1.0:
            raise ValueError(f"volume_surge_multiplier必须 > 1.0，" f"当前: {self.config.volume_surge_multiplier}")

        if not 0 <= self.config.vwap_deviation_threshold <= 1:
            raise ValueError(
                f"vwap_deviation_threshold必须在[0, 1]范围内，" f"当前: {self.config.vwap_deviation_threshold}"
            )

        if self.config.correlation_window <= 0:
            raise ValueError(f"correlation_window必须 > 0，" f"当前: {self.config.correlation_window}")

    def _extend_operator_whitelist(self) -> None:
        """扩展算子白名单

        将量价关系专用算子添加到遗传算法的算子白名单中
        """
        price_volume_operators = [
            "volume_price_correlation",
            "obv_divergence",
            "vwap_deviation",
            "volume_weighted_momentum",
            "price_volume_trend",
            "accumulation_distribution",
            "money_flow_index",
            "volume_surge_pattern",
            "price_volume_breakout",
            "volume_profile_support",
            "tick_volume_analysis",
            "volume_weighted_rsi",
        ]

        # 添加到基类的算子白名单
        if not hasattr(self, "operator_whitelist"):
            self.operator_whitelist = []

        self.operator_whitelist.extend(price_volume_operators)

        logger.debug(f"扩展算子白名单，新增{len(price_volume_operators)}个量价算子")

    def detect_divergence(self, price: pd.Series, indicator: pd.Series, window: int = 20) -> pd.Series:
        """检测价格与指标的背离

        白皮书依据: 第四章 4.1.11 背离检测

        背离类型：
        1. 顶背离：价格创新高，指标未创新高（看跌信号）
        2. 底背离：价格创新低，指标未创新低（看涨信号）

        Args:
            price: 价格序列
            indicator: 指标序列（如OBV、RSI等）
            window: 检测窗口

        Returns:
            背离信号序列 (1=顶背离, -1=底背离, 0=无背离)
        """
        if price.empty or indicator.empty:
            logger.warning("价格或指标序列为空")
            return pd.Series(0, index=price.index)

        divergence = pd.Series(0, index=price.index)

        # 计算滚动最高价和最低价
        price_high = price.rolling(window=window).max()
        price_low = price.rolling(window=window).min()

        # 计算指标滚动最高和最低
        indicator_high = indicator.rolling(window=window).max()
        indicator_low = indicator.rolling(window=window).min()

        # 检测顶背离：价格创新高，指标未创新高
        price_new_high = price >= price_high
        indicator_not_high = indicator < indicator_high * (1 - self.config.divergence_threshold)
        divergence[price_new_high & indicator_not_high] = 1

        # 检测底背离：价格创新低，指标未创新低
        price_new_low = price <= price_low
        indicator_not_low = indicator > indicator_low * (1 + self.config.divergence_threshold)
        divergence[price_new_low & indicator_not_low] = -1

        # 记录背离信号
        divergence_count = (divergence != 0).sum()
        if divergence_count > 0:
            logger.debug(
                f"检测到{divergence_count}个背离信号 "
                f"(顶背离:{(divergence == 1).sum()}, "
                f"底背离:{(divergence == -1).sum()})"
            )

        return divergence

    def analyze_volume_surge(self, volume: pd.Series, price_change: pd.Series, window: int = 20) -> pd.Series:
        """分析成交量激增模式

        白皮书依据: 第四章 4.1.11 成交量激增模式

        成交量激增 + 价格上涨 = 强势信号
        成交量激增 + 价格下跌 = 恐慌信号

        Args:
            volume: 成交量序列
            price_change: 价格变化序列
            window: 计算窗口

        Returns:
            成交量激增信号 (正值=强势, 负值=恐慌)
        """
        if volume.empty or price_change.empty:
            return pd.Series(0, index=volume.index)

        # 计算成交量均值
        volume_ma = volume.rolling(window=window).mean()

        # 检测成交量激增
        volume_surge = volume > (volume_ma * self.config.volume_surge_multiplier)

        # 结合价格变化
        surge_signal = pd.Series(0.0, index=volume.index)
        surge_signal[volume_surge & (price_change > 0)] = 1.0  # 强势
        surge_signal[volume_surge & (price_change < 0)] = -1.0  # 恐慌

        logger.debug(
            f"成交量激增分析: " f"强势信号={( surge_signal > 0).sum()}, " f"恐慌信号={(surge_signal < 0).sum()}"
        )

        return surge_signal

    def calculate_capital_flow_strength(self, data: pd.DataFrame) -> pd.Series:
        """计算资金流向强度

        白皮书依据: 第四章 4.1.11 资金流向分析

        综合多个量价指标评估资金流向：
        1. OBV趋势
        2. 累积派发线
        3. 资金流量指数

        Args:
            data: 包含价格和成交量的数据框

        Returns:
            资金流向强度 (正值=流入, 负值=流出)
        """
        if data.empty:
            return pd.Series(0, index=data.index)

        # 计算OBV
        obv = self.operator_registry.on_balance_volume(data, "close", "volume")
        obv_trend = obv.diff()

        # 计算累积派发
        ad = self.operator_registry.accumulation_distribution(data, "high", "low", "close", "volume")
        ad_trend = ad.diff()

        # 计算资金流量指数
        mfi = self.operator_registry.money_flow_index(data, "high", "low", "close", "volume")

        # 综合评分（归一化）
        obv_score = (obv_trend - obv_trend.mean()) / (obv_trend.std() + 1e-8)
        ad_score = (ad_trend - ad_trend.mean()) / (ad_trend.std() + 1e-8)
        mfi_score = (mfi - 50) / 50  # MFI范围[0, 100]，中性值50

        # 加权平均
        capital_flow = obv_score * 0.4 + ad_score * 0.3 + mfi_score * 0.3

        logger.debug(f"资金流向强度: mean={capital_flow.mean():.4f}, " f"std={capital_flow.std():.4f}")

        return capital_flow

    def mine_factors(self, data: pd.DataFrame, returns: pd.Series, generations: int = 10) -> List[Individual]:
        """挖掘量价关系因子

        白皮书依据: 第四章 4.1.11 量价关系因子挖掘

        完整流程：
        1. 数据验证
        2. 初始化种群
        3. 适应度评估
        4. 遗传进化
        5. 返回最优因子

        Args:
            data: 市场数据（必须包含price和volume列）
            returns: 收益率数据
            generations: 进化代数

        Returns:
            最优因子列表

        Raises:
            ValueError: 当数据缺少必要列时
        """
        logger.info(f"开始挖掘量价关系因子: " f"进化代数={generations}")

        # 1. 数据验证
        required_columns = ["close", "volume"]
        missing_columns = set(required_columns) - set(data.columns)
        if missing_columns:
            raise ValueError(f"数据缺少必要列: {missing_columns}")

        # 2. 初始化种群
        self.initialize_population()  # pylint: disable=e1120

        # 3. 适应度评估
        self.evaluate_fitness(data, returns)

        # 4. 遗传进化
        best_individual = self.evolve(generations=generations)  # pylint: disable=e1120

        # 5. 返回最优因子
        logger.info(f"量价关系因子挖掘完成，" f"最优因子适应度: {best_individual.fitness:.4f}")

        return self.population[:10]  # 返回前10个最优因子

    def get_divergence_report(self) -> Dict[str, Any]:
        """获取背离信号报告

        Returns:
            背离信号报告字典
        """
        total_signals = sum(len(signals) for signals in self.divergence_signals.values())

        return {
            "total_divergence_signals": total_signals,
            "divergence_by_type": {
                signal_type: len(signals) for signal_type, signals in self.divergence_signals.items()
            },
            "divergence_threshold": self.config.divergence_threshold,
            "volume_surge_multiplier": self.config.volume_surge_multiplier,
        }
