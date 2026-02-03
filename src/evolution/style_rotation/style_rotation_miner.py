"""风格轮动因子挖掘器

白皮书依据: 第四章 4.1.14 风格轮动因子挖掘器
"""

from typing import Dict, List, Optional

import pandas as pd
from loguru import logger

from ..genetic_miner import EvolutionConfig, GeneticMiner, Individual
from .style_rotation_operators import (
    StyleRotationConfig,
    dividend_yield_cycle,
    factor_crowding_index,
    low_volatility_anomaly,
    momentum_reversal_switch,
    quality_junk_rotation,
    sector_rotation_signal,
    size_premium_cycle,
    value_growth_spread,
)


class StyleRotationFactorMiner(GeneticMiner):
    """风格轮动因子挖掘器

    白皮书依据: 第四章 4.1.14 风格轮动因子挖掘器

    识别市场风格轮动规律,捕捉不同投资风格的周期性表现。

    核心算子 (8个):
    1. value_growth_spread - 价值成长价差
    2. size_premium_cycle - 规模溢价周期
    3. momentum_reversal_switch - 动量反转切换
    4. quality_junk_rotation - 质量垃圾轮动
    5. low_volatility_anomaly - 低波动异象
    6. dividend_yield_cycle - 股息率周期
    7. sector_rotation_signal - 行业轮动信号
    8. factor_crowding_index - 因子拥挤指数

    应用场景:
    - 风格配置和因子择时
    - 组合优化
    - 风险管理
    """

    def __init__(self, config: Optional[EvolutionConfig] = None, style_config: Optional[StyleRotationConfig] = None):
        """初始化风格轮动因子挖掘器

        Args:
            config: 进化配置
            style_config: 风格轮动配置
        """
        if config is None:
            config = EvolutionConfig()

        super().__init__(config=config)

        self.style_config = style_config or StyleRotationConfig()

        # 注册风格轮动算子
        self._register_style_operators()

        logger.info(
            f"StyleRotationFactorMiner初始化完成: "
            f"spread_window={self.style_config.spread_window}, "
            f"cycle_window={self.style_config.cycle_window}"
        )

    def _register_style_operators(self):
        """注册风格轮动算子到算子白名单"""
        self.style_operators = {
            "value_growth_spread": value_growth_spread,
            "size_premium_cycle": size_premium_cycle,
            "momentum_reversal_switch": momentum_reversal_switch,
            "quality_junk_rotation": quality_junk_rotation,
            "low_volatility_anomaly": low_volatility_anomaly,
            "dividend_yield_cycle": dividend_yield_cycle,
            "sector_rotation_signal": sector_rotation_signal,
            "factor_crowding_index": factor_crowding_index,
        }

        # 确保operator_whitelist存在
        if not hasattr(self, "operator_whitelist"):
            self.operator_whitelist = []

        # 添加到白名单
        for op_name in self.style_operators.keys():  # pylint: disable=consider-iterating-dictionary
            if op_name not in self.operator_whitelist:
                self.operator_whitelist.append(op_name)

        logger.info(f"注册了 {len(self.style_operators)} 个风格轮动算子")

    async def mine_factors(
        self, data: pd.DataFrame, returns: pd.Series, generations: int = 10, sector_map: Optional[Dict[str, str]] = None
    ) -> List[Individual]:
        """挖掘风格轮动因子

        Args:
            data: 价格数据,列为股票代码
            returns: 收益率数据
            generations: 进化代数
            sector_map: 股票到行业的映射(可选)

        Returns:
            List[Individual]: 挖掘出的因子列表
        """
        try:
            logger.info("开始挖掘风格轮动因子")

            # 初始化种群
            if not self.population:
                await self.initialize_population(data.columns.tolist())

            # 存储行业映射供算子使用
            self.sector_map = sector_map  # pylint: disable=w0201

            # 进化种群
            best_individual = await self.evolve(data, returns, generations)

            # 收集所有有效因子
            valid_factors = [
                ind for ind in self.population if ind.fitness > 0.1 and abs(ind.ic) > self.config.min_ic_threshold
            ]

            logger.info(
                f"风格轮动因子挖掘完成: " f"发现 {len(valid_factors)} 个有效因子, " f"最佳IC={best_individual.ic:.4f}"
            )

            return valid_factors

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"风格轮动因子挖掘失败: {e}")
            return []

    def calculate_style_factor(self, operator_name: str, data: pd.DataFrame, **kwargs) -> pd.Series:
        """计算单个风格轮动因子

        Args:
            operator_name: 算子名称
            data: 价格数据
            **kwargs: 额外参数

        Returns:
            pd.Series: 因子值
        """
        try:
            if operator_name not in self.style_operators:
                logger.error(f"未知的风格轮动算子: {operator_name}")
                return pd.Series(0.0, index=data.index)

            operator_func = self.style_operators[operator_name]

            # 准备参数
            params = {"data": data}

            # 添加算子特定参数
            if operator_name == "value_growth_spread":
                params["window"] = self.style_config.spread_window
                params["value_quantile"] = self.style_config.value_quantile
                params["growth_quantile"] = self.style_config.growth_quantile

            elif operator_name == "size_premium_cycle":
                params["window"] = self.style_config.cycle_window
                params["size_quantile"] = self.style_config.size_quantile

            elif operator_name == "momentum_reversal_switch":
                params["momentum_window"] = self.style_config.momentum_window
                params["reversal_window"] = self.style_config.spread_window

            elif operator_name == "quality_junk_rotation":
                params["window"] = self.style_config.spread_window
                params["quality_quantile"] = self.style_config.quality_quantile

            elif operator_name == "low_volatility_anomaly":
                params["window"] = self.style_config.volatility_window

            elif operator_name == "dividend_yield_cycle":
                params["window"] = self.style_config.cycle_window

            elif operator_name == "sector_rotation_signal":
                params["sector_map"] = kwargs.get("sector_map", self.sector_map)
                params["window"] = self.style_config.spread_window

            elif operator_name == "factor_crowding_index":
                params["window"] = self.style_config.spread_window
                params["threshold"] = self.style_config.crowding_threshold

            # 计算因子
            factor_values = operator_func(**params)

            return factor_values

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"计算风格轮动因子失败 ({operator_name}): {e}")
            return pd.Series(0.0, index=data.index)

    def analyze_style_rotation(
        self, data: pd.DataFrame, window: int = 60  # pylint: disable=unused-argument
    ) -> Dict[str, pd.Series]:  # pylint: disable=unused-argument
        """分析风格轮动状态

        Args:
            data: 价格数据
            window: 分析窗口

        Returns:
            Dict[str, pd.Series]: 各风格因子的时间序列
        """
        try:
            logger.info("开始分析风格轮动状态...")

            analysis = {}

            # 计算各个风格因子
            logger.info("计算价值成长价差...")
            analysis["value_growth"] = self.calculate_style_factor("value_growth_spread", data)

            logger.info("计算规模溢价周期...")
            analysis["size_premium"] = self.calculate_style_factor("size_premium_cycle", data)

            logger.info("计算动量反转切换...")
            analysis["momentum_reversal"] = self.calculate_style_factor("momentum_reversal_switch", data)

            logger.info("计算质量垃圾轮动...")
            analysis["quality_junk"] = self.calculate_style_factor("quality_junk_rotation", data)

            logger.info("计算低波动异象...")
            analysis["low_volatility"] = self.calculate_style_factor("low_volatility_anomaly", data)

            logger.info("计算股息率周期...")
            analysis["dividend_yield"] = self.calculate_style_factor("dividend_yield_cycle", data)

            logger.info("计算因子拥挤指数...")
            analysis["crowding"] = self.calculate_style_factor("factor_crowding_index", data)

            logger.info(f"风格轮动分析完成，共 {len(analysis)} 个风格因子")

            return analysis

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"风格轮动分析失败: {e}")
            return {}

    def identify_dominant_style(self, data: pd.DataFrame, window: int = 60) -> pd.Series:
        """识别主导风格

        Args:
            data: 价格数据
            window: 识别窗口

        Returns:
            pd.Series: 主导风格标签
        """
        try:
            # 计算所有风格因子
            style_analysis = self.analyze_style_rotation(data, window)

            if not style_analysis:
                return pd.Series("unknown", index=data.index)

            # 转换为DataFrame
            style_df = pd.DataFrame(style_analysis)

            # 识别每个时间点的主导风格
            dominant_styles = []

            for idx in style_df.index:
                row = style_df.loc[idx]

                # 找到最强的风格
                if row.abs().max() > 0.5:  # 阈值
                    dominant_style = row.abs().idxmax()
                else:
                    dominant_style = "neutral"

                dominant_styles.append(dominant_style)

            result = pd.Series(dominant_styles, index=data.index)

            logger.info(f"主导风格识别完成: " f"{result.value_counts().to_dict()}")

            return result

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"主导风格识别失败: {e}")
            return pd.Series("unknown", index=data.index)

    def calculate_style_timing_signal(self, data: pd.DataFrame, window: int = 60) -> pd.DataFrame:
        """计算风格择时信号

        Args:
            data: 价格数据
            window: 计算窗口

        Returns:
            pd.DataFrame: 风格择时信号矩阵
        """
        try:
            logger.info("计算风格择时信号...")

            # 获取风格分析
            style_analysis = self.analyze_style_rotation(data, window)

            if not style_analysis:
                return pd.DataFrame()

            # 转换为DataFrame
            signals = pd.DataFrame(style_analysis)

            # 计算择时信号(标准化后的Z-score)
            for col in signals.columns:
                signals[col] = (signals[col] - signals[col].rolling(window=window, min_periods=window // 2).mean()) / (
                    signals[col].rolling(window=window, min_periods=window // 2).std() + 1e-8
                )

            signals = signals.fillna(0.0)

            # 添加综合信号
            signals["composite"] = signals.mean(axis=1)

            logger.info(f"风格择时信号计算完成，共 {len(signals.columns)} 个信号")

            return signals

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"风格择时信号计算失败: {e}")
            return pd.DataFrame()

    def calculate_all_style_metrics(
        self, data: pd.DataFrame, sector_map: Optional[Dict[str, str]] = None
    ) -> pd.DataFrame:
        """计算所有风格指标

        Args:
            data: 价格数据
            sector_map: 行业映射

        Returns:
            pd.DataFrame: 风格指标矩阵
        """
        try:
            metrics = pd.DataFrame(index=data.index)

            logger.info("计算价值成长价差...")
            metrics["value_growth_spread"] = self.calculate_style_factor("value_growth_spread", data)

            logger.info("计算规模溢价周期...")
            metrics["size_premium_cycle"] = self.calculate_style_factor("size_premium_cycle", data)

            logger.info("计算动量反转切换...")
            metrics["momentum_reversal_switch"] = self.calculate_style_factor("momentum_reversal_switch", data)

            logger.info("计算质量垃圾轮动...")
            metrics["quality_junk_rotation"] = self.calculate_style_factor("quality_junk_rotation", data)

            logger.info("计算低波动异象...")
            metrics["low_volatility_anomaly"] = self.calculate_style_factor("low_volatility_anomaly", data)

            logger.info("计算股息率周期...")
            metrics["dividend_yield_cycle"] = self.calculate_style_factor("dividend_yield_cycle", data)

            logger.info("计算行业轮动信号...")
            metrics["sector_rotation_signal"] = self.calculate_style_factor(
                "sector_rotation_signal", data, sector_map=sector_map
            )

            logger.info("计算因子拥挤指数...")
            metrics["factor_crowding_index"] = self.calculate_style_factor("factor_crowding_index", data)

            logger.info(f"风格指标计算完成，共 {len(metrics.columns)} 个指标")

            return metrics

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"风格指标计算失败: {e}")
            return pd.DataFrame()
