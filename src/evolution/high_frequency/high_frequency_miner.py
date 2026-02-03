"""高频微观结构因子挖掘器

白皮书依据: 第四章 4.1.6 高频微观结构因子挖掘器
"""

from typing import List, Optional

import pandas as pd
from loguru import logger

from ..genetic_miner import EvolutionConfig, GeneticMiner, Individual
from .high_frequency_operators import (
    HighFrequencyConfig,
    adverse_selection_cost,
    bid_ask_bounce,
    effective_spread_decomposition,
    hidden_liquidity_probe,
    market_maker_inventory,
    order_flow_imbalance,
    price_impact_curve,
    quote_stuffing_detection,
    tick_direction_momentum,
    trade_size_clustering,
)


class HighFrequencyMicrostructureFactorMiner(GeneticMiner):
    """高频微观结构因子挖掘器

    白皮书依据: 第四章 4.1.6 高频微观结构因子挖掘器

    专注于高频交易和市场微观结构分析，挖掘订单流、价格冲击、
    流动性等微观层面的因子。

    核心算子 (10个):
    1. order_flow_imbalance - 订单流不平衡
    2. price_impact_curve - 价格冲击曲线
    3. tick_direction_momentum - Tick方向动量
    4. bid_ask_bounce - 买卖价反弹
    5. trade_size_clustering - 交易规模聚类
    6. quote_stuffing_detection - 报价填充检测
    7. hidden_liquidity_probe - 隐藏流动性探测
    8. market_maker_inventory - 做市商库存
    9. adverse_selection_cost - 逆向选择成本
    10. effective_spread_decomposition - 有效价差分解

    应用场景:
    - 高频交易策略
    - 市场微观结构分析
    - 流动性评估
    - 交易成本分析
    """

    def __init__(self, config: Optional[EvolutionConfig] = None, hf_config: Optional[HighFrequencyConfig] = None):
        """初始化高频微观结构因子挖掘器

        Args:
            config: 进化配置
            hf_config: 高频配置
        """
        if config is None:
            config = EvolutionConfig()

        super().__init__(config=config)

        self.hf_config = hf_config or HighFrequencyConfig()

        # 注册高频算子
        self._register_hf_operators()

        logger.info(
            f"HighFrequencyMicrostructureFactorMiner初始化完成: "
            f"tick_window={self.hf_config.tick_window}, "
            f"imbalance_threshold={self.hf_config.imbalance_threshold}"
        )

    def _register_hf_operators(self):
        """注册高频算子到算子白名单"""
        self.hf_operators = {
            "order_flow_imbalance": order_flow_imbalance,
            "price_impact_curve": price_impact_curve,
            "tick_direction_momentum": tick_direction_momentum,
            "bid_ask_bounce": bid_ask_bounce,
            "trade_size_clustering": trade_size_clustering,
            "quote_stuffing_detection": quote_stuffing_detection,
            "hidden_liquidity_probe": hidden_liquidity_probe,
            "market_maker_inventory": market_maker_inventory,
            "adverse_selection_cost": adverse_selection_cost,
            "effective_spread_decomposition": effective_spread_decomposition,
        }

        # 确保operator_whitelist存在
        if not hasattr(self, "operator_whitelist"):
            self.operator_whitelist = []

        # 添加到白名单
        for op_name in self.hf_operators.keys():  # pylint: disable=consider-iterating-dictionary
            if op_name not in self.operator_whitelist:
                self.operator_whitelist.append(op_name)

        logger.info(f"注册了 {len(self.hf_operators)} 个高频微观结构算子")

    async def mine_factors(
        self, data: pd.DataFrame, returns: pd.Series, generations: int = 10, volume: Optional[pd.DataFrame] = None
    ) -> List[Individual]:
        """挖掘高频微观结构因子

        Args:
            data: 价格数据
            returns: 收益率数据
            generations: 进化代数
            volume: 成交量数据（可选，但强烈推荐）

        Returns:
            List[Individual]: 挖掘出的因子列表
        """
        try:
            logger.info("开始挖掘高频微观结构因子")

            # 初始化种群
            if not self.population:
                await self.initialize_population(data.columns.tolist())

            # 存储成交量数据供算子使用
            self.volume_data = volume  # pylint: disable=w0201

            # 进化种群
            best_individual = await self.evolve(data, returns, generations)

            # 收集所有有效因子
            valid_factors = [
                ind for ind in self.population if ind.fitness > 0.1 and abs(ind.ic) > self.config.min_ic_threshold
            ]

            logger.info(
                f"高频微观结构因子挖掘完成: "
                f"发现 {len(valid_factors)} 个有效因子, "
                f"最佳IC={best_individual.ic:.4f}"
            )

            return valid_factors

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"高频微观结构因子挖掘失败: {e}")
            return []

    def calculate_hf_factor(self, operator_name: str, data: pd.DataFrame, **kwargs) -> pd.Series:
        """计算单个高频因子

        Args:
            operator_name: 算子名称
            data: 价格数据
            **kwargs: 额外参数

        Returns:
            pd.Series: 因子值
        """
        try:
            if operator_name not in self.hf_operators:
                logger.error(f"未知的高频算子: {operator_name}")
                return pd.Series(0.0, index=data.index)

            operator_func = self.hf_operators[operator_name]

            # 准备参数
            params = {"data": data}

            # 添加算子特定参数
            if operator_name in [
                "order_flow_imbalance",
                "price_impact_curve",
                "trade_size_clustering",
                "hidden_liquidity_probe",
                "market_maker_inventory",
            ]:
                params["volume"] = kwargs.get("volume", self.volume_data)

            if operator_name == "order_flow_imbalance":
                params["window"] = self.hf_config.tick_window

            elif operator_name == "price_impact_curve":
                params["quantiles"] = self.hf_config.impact_quantiles

            elif operator_name == "tick_direction_momentum":
                params["window"] = self.hf_config.tick_window

            elif operator_name == "bid_ask_bounce":
                params["window"] = self.hf_config.cluster_window

            elif operator_name == "trade_size_clustering":
                params["window"] = self.hf_config.cluster_window

            elif operator_name == "quote_stuffing_detection":
                params["window"] = self.hf_config.spread_window
                params["threshold"] = self.hf_config.stuffing_threshold

            elif operator_name in ["hidden_liquidity_probe", "market_maker_inventory", "adverse_selection_cost"]:
                params["window"] = self.hf_config.cluster_window

            elif operator_name == "effective_spread_decomposition":
                params["window"] = self.hf_config.spread_window

            # 计算因子
            factor_values = operator_func(**params)

            return factor_values

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"计算高频因子失败 ({operator_name}): {e}")
            return pd.Series(0.0, index=data.index)

    def calculate_all_hf_metrics(self, data: pd.DataFrame, volume: Optional[pd.DataFrame] = None) -> pd.DataFrame:
        """计算所有高频指标

        Args:
            data: 价格数据
            volume: 成交量数据

        Returns:
            pd.DataFrame: 高频指标矩阵
        """
        try:
            metrics = pd.DataFrame(index=data.index)

            logger.info("计算订单流不平衡...")
            metrics["order_flow_imbalance"] = self.calculate_hf_factor("order_flow_imbalance", data, volume=volume)

            logger.info("计算价格冲击曲线...")
            metrics["price_impact"] = self.calculate_hf_factor("price_impact_curve", data, volume=volume)

            logger.info("计算Tick方向动量...")
            metrics["tick_momentum"] = self.calculate_hf_factor("tick_direction_momentum", data)

            logger.info("计算买卖价反弹...")
            metrics["bid_ask_bounce"] = self.calculate_hf_factor("bid_ask_bounce", data)

            logger.info("计算交易规模聚类...")
            metrics["trade_clustering"] = self.calculate_hf_factor("trade_size_clustering", data, volume=volume)

            logger.info("计算报价填充检测...")
            metrics["quote_stuffing"] = self.calculate_hf_factor("quote_stuffing_detection", data)

            logger.info("计算隐藏流动性...")
            metrics["hidden_liquidity"] = self.calculate_hf_factor("hidden_liquidity_probe", data, volume=volume)

            logger.info("计算做市商库存...")
            metrics["mm_inventory"] = self.calculate_hf_factor("market_maker_inventory", data, volume=volume)

            logger.info("计算逆向选择成本...")
            metrics["adverse_selection"] = self.calculate_hf_factor("adverse_selection_cost", data, volume=volume)

            logger.info("计算有效价差分解...")
            metrics["spread_decomposition"] = self.calculate_hf_factor("effective_spread_decomposition", data)

            logger.info(f"高频指标计算完成，共 {len(metrics.columns)} 个指标")

            return metrics

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"高频指标计算失败: {e}")
            return pd.DataFrame()
