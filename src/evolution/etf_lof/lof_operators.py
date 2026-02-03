# pylint: disable=too-many-lines
"""LOF (Listed Open-Ended Fund) Operators

白皮书依据: 第四章 4.1.18 - LOF基金因子挖掘器
版本: v1.6.1

LOF算子库提供20个专用算子，用于挖掘LOF特有的量化因子。
LOF具有场内外双重交易机制，可以进行转托管套利、基金经理选择等策略。

核心算子分类:
1. 场内外价差算子（1-5）: 价差、套利、折溢价、流动性
2. 基金分析算子（6-10）: 流动性分层、投资者结构、基金经理Alpha、风格、持仓集中度
3. 性能算子（11-20）: 行业配置、换手率、业绩持续性、费率影响、分红收益率、
                      净值动量、赎回压力、基准跟踪、市场冲击、横截面动量
"""

from typing import Dict, List

import numpy as np
import pandas as pd
from loguru import logger

from src.evolution.etf_lof.exceptions import DataQualityError, OperatorError


class LOFOperators:
    """LOF算子类

    白皮书依据: 第四章 4.1.18 - LOF基金因子挖掘器

    提供20个LOF专用算子，用于挖掘LOF特有的量化因子。

    算子分类:
    - 场内外价差算子（1-5）
    - 基金分析算子（6-10）
    - 性能算子（11-20）

    Attributes:
        operator_registry: 算子注册表，映射算子名称到算子函数
        data_quality_threshold: 数据质量阈值，默认0.8（80%非NaN）
    """

    def __init__(self, data_quality_threshold: float = 0.8):
        """初始化LOF算子类

        Args:
            data_quality_threshold: 数据质量阈值，范围[0, 1]，默认0.8

        Raises:
            ValueError: 当data_quality_threshold不在[0, 1]范围时
        """
        if not 0 <= data_quality_threshold <= 1:
            raise ValueError(f"data_quality_threshold must be in [0, 1], got {data_quality_threshold}")

        self.data_quality_threshold = data_quality_threshold

        # 算子注册表
        self.operator_registry: Dict[str, callable] = {
            # 场内外价差算子（1-5）
            "lof_onoff_price_spread": self.lof_onoff_price_spread,
            "lof_transfer_arbitrage_opportunity": self.lof_transfer_arbitrage_opportunity,
            "lof_premium_discount_rate": self.lof_premium_discount_rate,
            "lof_onmarket_liquidity": self.lof_onmarket_liquidity,
            "lof_offmarket_liquidity": self.lof_offmarket_liquidity,
            # 基金分析算子（6-10）
            "lof_liquidity_stratification": self.lof_liquidity_stratification,
            "lof_investor_structure": self.lof_investor_structure,
            "lof_fund_manager_alpha": self.lof_fund_manager_alpha,
            "lof_fund_manager_style": self.lof_fund_manager_style,
            "lof_holding_concentration": self.lof_holding_concentration,
            # 性能算子（11-20）
            "lof_sector_allocation_shift": self.lof_sector_allocation_shift,
            "lof_turnover_rate": self.lof_turnover_rate,
            "lof_performance_persistence": self.lof_performance_persistence,
            "lof_expense_ratio_impact": self.lof_expense_ratio_impact,
            "lof_dividend_yield_signal": self.lof_dividend_yield_signal,
            "lof_nav_momentum": self.lof_nav_momentum,
            "lof_redemption_pressure": self.lof_redemption_pressure,
            "lof_benchmark_tracking_quality": self.lof_benchmark_tracking_quality,
            "lof_market_impact_cost": self.lof_market_impact_cost,
            "lof_cross_sectional_momentum": self.lof_cross_sectional_momentum,
        }

        logger.info(f"LOFOperators initialized with {len(self.operator_registry)} operators")

    def get_operator(self, operator_name: str) -> callable:
        """获取算子函数

        Args:
            operator_name: 算子名称

        Returns:
            算子函数

        Raises:
            OperatorError: 当算子不存在时
        """
        if operator_name not in self.operator_registry:
            raise OperatorError(
                f"Operator '{operator_name}' not found. " f"Available operators: {list(self.operator_registry.keys())}"
            )
        return self.operator_registry[operator_name]

    def _validate_data(self, data: pd.DataFrame, required_columns: List[str]) -> None:
        """验证数据完整性

        Args:
            data: 输入数据框
            required_columns: 必需的列名列表

        Raises:
            OperatorError: 当数据为空时
            OperatorError: 当缺失必需列时
            DataQualityError: 当数据质量不达标时
        """
        # 检查数据是否为空
        if data.empty:
            raise OperatorError("Input data is empty")

        # 检查必需列是否存在
        missing_cols = [col for col in required_columns if col not in data.columns]
        if missing_cols:
            raise OperatorError(
                f"Missing required columns: {missing_cols}. " f"Available columns: {list(data.columns)}"
            )

        # 检查数据质量
        for col in required_columns:
            non_nan_ratio = data[col].notna().sum() / len(data)
            if non_nan_ratio < self.data_quality_threshold:
                raise DataQualityError(
                    f"Column '{col}' has too many NaN values. "
                    f"Non-NaN ratio: {non_nan_ratio:.2%}, "
                    f"threshold: {self.data_quality_threshold:.2%}"
                )

    def list_operators(self) -> List[str]:
        """列出所有可用的算子

        Returns:
            算子名称列表
        """
        return list(self.operator_registry.keys())

    # ========================================================================
    # 场内外价差算子（1-5）
    # ========================================================================

    def lof_onoff_price_spread(
        self, data: pd.DataFrame, onmarket_price_col: str = "onmarket_price", offmarket_nav_col: str = "offmarket_nav"
    ) -> pd.Series:
        """LOF场内外价差

        白皮书依据: 第四章 4.1.18 - lof_onoff_price_spread
        公式: (onmarket_price - offmarket_nav) / offmarket_nav

        计算LOF场内价格与场外净值的差异，识别转托管套利机会。
        正值表示场内溢价，负值表示场内折价。

        Args:
            data: 输入数据框
            onmarket_price_col: 场内价格列名，默认'onmarket_price'
            offmarket_nav_col: 场外净值列名，默认'offmarket_nav'

        Returns:
            场内外价差序列

        Raises:
            OperatorError: 当缺失必需列或计算失败时

        Example:
            >>> data = pd.DataFrame({
            ...     'onmarket_price': [10.5, 10.8, 10.6],
            ...     'offmarket_nav': [10.0, 10.5, 10.5]
            ... })
            >>> operators = LOFOperators()
            >>> spread = operators.lof_onoff_price_spread(data)
            >>> print(spread)
            0    0.050000
            1    0.028571
            2    0.009524
        """
        try:
            # 验证数据
            self._validate_data(data, [onmarket_price_col, offmarket_nav_col])

            # 计算场内外价差
            onmarket_price = data[onmarket_price_col]
            offmarket_nav = data[offmarket_nav_col]

            # 公式: (onmarket_price - offmarket_nav) / offmarket_nav
            spread = (onmarket_price - offmarket_nav) / offmarket_nav

            return spread

        except (DataQualityError, OperatorError):
            raise
        except Exception as e:
            logger.error(f"lof_onoff_price_spread failed: {e}")
            raise OperatorError(f"lof_onoff_price_spread failed: {e}") from e

    def lof_transfer_arbitrage_opportunity(self, data: pd.DataFrame, transaction_cost: float = 0.002) -> pd.Series:
        """LOF转托管套利机会

        白皮书依据: 第四章 4.1.18 - lof_transfer_arbitrage_opportunity

        评估场内外转托管的套利空间，计算套利成本和收益。
        当场内外价差超过交易成本时，存在套利机会。

        Args:
            data: 输入数据框，必须包含'onmarket_price'和'offmarket_nav'列
            transaction_cost: 交易成本（包括转托管费用），默认0.2%

        Returns:
            套利机会序列（1表示有套利机会，0表示无）

        Raises:
            OperatorError: 当缺失必需列或计算失败时

        Example:
            >>> data = pd.DataFrame({
            ...     'onmarket_price': [10.5, 10.1, 10.6],
            ...     'offmarket_nav': [10.0, 10.0, 10.5]
            ... })
            >>> operators = LOFOperators()
            >>> opportunity = operators.lof_transfer_arbitrage_opportunity(data, transaction_cost=0.01)
            >>> print(opportunity)
            0    1.0
            1    0.0
            2    0.0
        """
        try:
            # 验证数据
            self._validate_data(data, ["onmarket_price", "offmarket_nav"])

            # 计算场内外价差
            spread = self.lof_onoff_price_spread(data)

            # 判断是否存在套利机会
            # 场内溢价 > 交易成本：买场外卖场内
            # 场内折价 < -交易成本：买场内卖场外
            arbitrage_opportunity = (np.abs(spread) > transaction_cost).astype(float)

            return arbitrage_opportunity

        except (DataQualityError, OperatorError):
            raise
        except Exception as e:
            logger.error(f"lof_transfer_arbitrage_opportunity failed: {e}")
            raise OperatorError(f"lof_transfer_arbitrage_opportunity failed: {e}") from e

    def lof_premium_discount_rate(self, data: pd.DataFrame, window: int = 20) -> pd.Series:
        """LOF折溢价率

        白皮书依据: 第四章 4.1.18 - lof_premium_discount_rate

        分析LOF折溢价率的时间序列特征，预测折溢价率回归。
        计算折溢价率的滚动均值，识别折溢价率的趋势。

        Args:
            data: 输入数据框，必须包含'onmarket_price'和'offmarket_nav'列
            window: 滚动窗口大小，默认20

        Returns:
            折溢价率滚动均值序列

        Raises:
            OperatorError: 当缺失必需列或计算失败时
            ValueError: 当window <= 0时

        Example:
            >>> data = pd.DataFrame({
            ...     'onmarket_price': [10.5, 10.8, 10.6, 10.4, 10.7] * 5,
            ...     'offmarket_nav': [10.0, 10.5, 10.5, 10.3, 10.6] * 5
            ... })
            >>> operators = LOFOperators()
            >>> rate = operators.lof_premium_discount_rate(data, window=5)
        """
        try:
            # 验证参数
            if window <= 0:
                raise ValueError(f"window must be > 0, got {window}")

            # 验证数据
            self._validate_data(data, ["onmarket_price", "offmarket_nav"])

            # 计算场内外价差
            spread = self.lof_onoff_price_spread(data)

            # 计算折溢价率的滚动均值
            premium_discount_rate = spread.rolling(window=window).mean()

            return premium_discount_rate

        except (DataQualityError, OperatorError, ValueError):
            raise
        except Exception as e:
            logger.error(f"lof_premium_discount_rate failed: {e}")
            raise OperatorError(f"lof_premium_discount_rate failed: {e}") from e

    def lof_onmarket_liquidity(
        self, data: pd.DataFrame, volume_col: str = "onmarket_volume", window: int = 20
    ) -> pd.Series:
        """LOF场内流动性

        白皮书依据: 第四章 4.1.18 - lof_onmarket_liquidity

        评估LOF场内交易的流动性，识别流动性风险。
        使用滚动平均成交量作为流动性指标。

        Args:
            data: 输入数据框
            volume_col: 场内成交量列名，默认'onmarket_volume'
            window: 滚动窗口大小，默认20

        Returns:
            场内流动性序列（滚动平均成交量）

        Raises:
            OperatorError: 当缺失必需列或计算失败时
            ValueError: 当window <= 0时

        Example:
            >>> data = pd.DataFrame({
            ...     'onmarket_volume': [100000, 120000, 110000, 130000, 115000] * 5
            ... })
            >>> operators = LOFOperators()
            >>> liquidity = operators.lof_onmarket_liquidity(data, window=5)
        """
        try:
            # 验证参数
            if window <= 0:
                raise ValueError(f"window must be > 0, got {window}")

            # 验证数据
            self._validate_data(data, [volume_col])

            # 计算滚动平均成交量
            volume = data[volume_col]
            onmarket_liquidity = volume.rolling(window=window).mean()

            return onmarket_liquidity

        except (DataQualityError, OperatorError, ValueError):
            raise
        except Exception as e:
            logger.error(f"lof_onmarket_liquidity failed: {e}")
            raise OperatorError(f"lof_onmarket_liquidity failed: {e}") from e

    def lof_offmarket_liquidity(
        self, data: pd.DataFrame, redemption_col: str = "redemption_amount", window: int = 20
    ) -> pd.Series:
        """LOF场外流动性

        白皮书依据: 第四章 4.1.18 - lof_offmarket_liquidity

        评估LOF场外申购赎回的流动性，预测大额赎回风险。
        使用滚动平均赎回金额作为流动性指标，值越大表示赎回压力越大。

        Args:
            data: 输入数据框
            redemption_col: 赎回金额列名，默认'redemption_amount'
            window: 滚动窗口大小，默认20

        Returns:
            场外流动性序列（滚动平均赎回金额）

        Raises:
            OperatorError: 当缺失必需列或计算失败时
            ValueError: 当window <= 0时

        Example:
            >>> data = pd.DataFrame({
            ...     'redemption_amount': [50000, 60000, 55000, 70000, 58000] * 5
            ... })
            >>> operators = LOFOperators()
            >>> liquidity = operators.lof_offmarket_liquidity(data, window=5)
        """
        try:
            # 验证参数
            if window <= 0:
                raise ValueError(f"window must be > 0, got {window}")

            # 验证数据
            self._validate_data(data, [redemption_col])

            # 计算滚动平均赎回金额
            redemption = data[redemption_col]
            offmarket_liquidity = redemption.rolling(window=window).mean()

            return offmarket_liquidity

        except (DataQualityError, OperatorError, ValueError):
            raise
        except Exception as e:
            logger.error(f"lof_offmarket_liquidity failed: {e}")
            raise OperatorError(f"lof_offmarket_liquidity failed: {e}") from e

    # ========================================================================
    # 基金分析算子（6-10）
    # ========================================================================

    def lof_liquidity_stratification(self, data: pd.DataFrame, window: int = 20) -> pd.Series:
        """LOF流动性分层

        白皮书依据: 第四章 4.1.18 - lof_liquidity_stratification

        分析场内外流动性的差异，识别流动性套利机会。
        计算场内外流动性比率，比率越大表示场内流动性相对越好。

        Args:
            data: 输入数据框，必须包含'onmarket_volume'和'redemption_amount'列
            window: 滚动窗口大小，默认20

        Returns:
            流动性分层指标序列（场内流动性/场外流动性）

        Raises:
            OperatorError: 当缺失必需列或计算失败时
            ValueError: 当window <= 0时

        Example:
            >>> data = pd.DataFrame({
            ...     'onmarket_volume': [100000, 120000, 110000] * 10,
            ...     'redemption_amount': [50000, 60000, 55000] * 10
            ... })
            >>> operators = LOFOperators()
            >>> stratification = operators.lof_liquidity_stratification(data, window=10)
        """
        try:
            # 验证参数
            if window <= 0:
                raise ValueError(f"window must be > 0, got {window}")

            # 验证数据
            self._validate_data(data, ["onmarket_volume", "redemption_amount"])

            # 计算场内流动性
            onmarket_liquidity = self.lof_onmarket_liquidity(data, window=window)

            # 计算场外流动性
            offmarket_liquidity = self.lof_offmarket_liquidity(data, window=window)

            # 计算流动性分层指标（场内/场外，加小量避免除零）
            stratification = onmarket_liquidity / (offmarket_liquidity + 1e-8)

            return stratification

        except (DataQualityError, OperatorError, ValueError):
            raise
        except Exception as e:
            logger.error(f"lof_liquidity_stratification failed: {e}")
            raise OperatorError(f"lof_liquidity_stratification failed: {e}") from e

    def lof_investor_structure(
        self, data: pd.DataFrame, institutional_col: str = "institutional_holding", retail_col: str = "retail_holding"
    ) -> pd.Series:
        """LOF投资者结构

        白皮书依据: 第四章 4.1.18 - lof_investor_structure

        追踪机构/散户持仓比例变化，预测资金流向。
        计算机构持仓占比，比例越高表示机构投资者越多。

        Args:
            data: 输入数据框
            institutional_col: 机构持仓列名，默认'institutional_holding'
            retail_col: 散户持仓列名，默认'retail_holding'

        Returns:
            投资者结构指标序列（机构持仓占比）

        Raises:
            OperatorError: 当缺失必需列或计算失败时

        Example:
            >>> data = pd.DataFrame({
            ...     'institutional_holding': [60, 65, 70],
            ...     'retail_holding': [40, 35, 30]
            ... })
            >>> operators = LOFOperators()
            >>> structure = operators.lof_investor_structure(data)
            >>> print(structure)
            0    0.60
            1    0.65
            2    0.70
        """
        try:
            # 验证数据
            self._validate_data(data, [institutional_col, retail_col])

            # 计算总持仓
            institutional = data[institutional_col]
            retail = data[retail_col]
            total_holding = institutional + retail

            # 计算机构持仓占比（加小量避免除零）
            institutional_ratio = institutional / (total_holding + 1e-8)

            return institutional_ratio

        except (DataQualityError, OperatorError):
            raise
        except Exception as e:
            logger.error(f"lof_investor_structure failed: {e}")
            raise OperatorError(f"lof_investor_structure failed: {e}") from e

    def lof_fund_manager_alpha(
        self,
        data: pd.DataFrame,
        returns_col: str = "returns",
        benchmark_col: str = "benchmark_returns",
        window: int = 252,
    ) -> pd.Series:
        """LOF基金经理Alpha

        白皮书依据: 第四章 4.1.18 - lof_fund_manager_alpha

        评估基金经理历史业绩，识别优秀基金经理。
        计算超额收益（Alpha）= 基金收益 - 基准收益的滚动均值。

        Args:
            data: 输入数据框
            returns_col: 收益率列名，默认'returns'
            benchmark_col: 基准收益率列名，默认'benchmark_returns'
            window: 滚动窗口大小，默认252（一年）

        Returns:
            基金经理Alpha序列

        Raises:
            OperatorError: 当缺失必需列或计算失败时
            ValueError: 当window <= 0时

        Example:
            >>> data = pd.DataFrame({
            ...     'returns': [0.01, 0.02, 0.015, 0.018] * 100,
            ...     'benchmark_returns': [0.008, 0.015, 0.012, 0.014] * 100
            ... })
            >>> operators = LOFOperators()
            >>> alpha = operators.lof_fund_manager_alpha(data, window=60)
        """
        try:
            # 验证参数
            if window <= 0:
                raise ValueError(f"window must be > 0, got {window}")

            # 验证数据
            self._validate_data(data, [returns_col, benchmark_col])

            # 计算超额收益
            returns = data[returns_col]
            benchmark = data[benchmark_col]
            excess_returns = returns - benchmark

            # 计算Alpha（超额收益的滚动均值）
            alpha = excess_returns.rolling(window=window).mean()

            return alpha

        except (DataQualityError, OperatorError, ValueError):
            raise
        except Exception as e:
            logger.error(f"lof_fund_manager_alpha failed: {e}")
            raise OperatorError(f"lof_fund_manager_alpha failed: {e}") from e

    def lof_fund_manager_style(self, data: pd.DataFrame, holdings_col: str = "holdings", window: int = 60) -> pd.Series:
        """LOF基金经理风格

        白皮书依据: 第四章 4.1.18 - lof_fund_manager_style

        分析基金经理投资风格，预测风格漂移。
        计算持仓集中度的变化率，作为风格稳定性指标。

        Args:
            data: 输入数据框
            holdings_col: 持仓数据列名，默认'holdings'（字典类型）
            window: 滚动窗口大小，默认60

        Returns:
            基金经理风格指标序列（持仓集中度变化率）

        Raises:
            OperatorError: 当缺失必需列或计算失败时
            ValueError: 当window <= 0时

        Example:
            >>> data = pd.DataFrame({
            ...     'holdings': [
            ...         {'stock1': 0.3, 'stock2': 0.2, 'stock3': 0.5},
            ...         {'stock1': 0.35, 'stock2': 0.25, 'stock3': 0.4}
            ...     ] * 40
            ... })
            >>> operators = LOFOperators()
            >>> style = operators.lof_fund_manager_style(data, window=20)
        """
        try:
            # 验证参数
            if window <= 0:
                raise ValueError(f"window must be > 0, got {window}")

            # 验证数据
            self._validate_data(data, [holdings_col])

            # 计算持仓集中度（使用HHI指数）
            concentration = self.lof_holding_concentration(data, holdings_col=holdings_col)

            # 计算集中度的变化率（作为风格稳定性指标）
            style_change = concentration.pct_change(periods=window)

            return style_change

        except (DataQualityError, OperatorError, ValueError):
            raise
        except Exception as e:
            logger.error(f"lof_fund_manager_style failed: {e}")
            raise OperatorError(f"lof_fund_manager_style failed: {e}") from e

    def lof_holding_concentration(self, data: pd.DataFrame, holdings_col: str = "holdings") -> pd.Series:
        """LOF持仓集中度

        白皮书依据: 第四章 4.1.18 - lof_holding_concentration

        计算LOF持仓的集中度变化，识别集中度风险。
        使用HHI（Herfindahl-Hirschman Index）指数衡量集中度。

        Args:
            data: 输入数据框
            holdings_col: 持仓数据列名，默认'holdings'（字典类型，键为股票代码，值为权重）

        Returns:
            持仓集中度序列（HHI指数，范围0-1）

        Raises:
            OperatorError: 当缺失必需列或计算失败时

        Example:
            >>> data = pd.DataFrame({
            ...     'holdings': [
            ...         {'stock1': 0.5, 'stock2': 0.3, 'stock3': 0.2},
            ...         {'stock1': 0.4, 'stock2': 0.4, 'stock3': 0.2}
            ...     ]
            ... })
            >>> operators = LOFOperators()
            >>> concentration = operators.lof_holding_concentration(data)
            >>> print(concentration)
            0    0.38
            1    0.36
        """
        try:
            # 验证数据
            self._validate_data(data, [holdings_col])

            # 计算HHI指数
            def calculate_hhi(holdings_dict):
                """计算HHI指数"""
                if not isinstance(holdings_dict, dict) or len(holdings_dict) == 0:
                    return np.nan

                # HHI = sum(weight^2)
                hhi = sum(weight**2 for weight in holdings_dict.values())
                return hhi

            # 对每行计算HHI
            concentration = data[holdings_col].apply(calculate_hhi)

            return concentration

        except (DataQualityError, OperatorError):
            raise
        except Exception as e:
            logger.error(f"lof_holding_concentration failed: {e}")
            raise OperatorError(f"lof_holding_concentration failed: {e}") from e

    # ========================================================================
    # 性能算子（11-20）
    # ========================================================================

    def lof_sector_allocation_shift(
        self, data: pd.DataFrame, sector_weights_col: str = "sector_weights", window: int = 60
    ) -> pd.Series:
        """LOF行业配置变化

        白皮书依据: 第四章 4.1.18 - lof_sector_allocation_shift

        追踪LOF行业配置调整，预测配置趋势。
        计算行业权重集中度的变化率，识别配置调整。

        Args:
            data: 输入数据框
            sector_weights_col: 行业权重列名，默认'sector_weights'（字典类型）
            window: 滚动窗口大小，默认60

        Returns:
            行业配置变化序列

        Raises:
            OperatorError: 当缺失必需列或计算失败时
            ValueError: 当window <= 0时

        Example:
            >>> data = pd.DataFrame({
            ...     'sector_weights': [
            ...         {'tech': 0.4, 'finance': 0.3, 'consumer': 0.3},
            ...         {'tech': 0.5, 'finance': 0.25, 'consumer': 0.25}
            ...     ] * 40
            ... })
            >>> operators = LOFOperators()
            >>> shift = operators.lof_sector_allocation_shift(data, window=20)
        """
        try:
            # 验证参数
            if window <= 0:
                raise ValueError(f"window must be > 0, got {window}")

            # 验证数据
            self._validate_data(data, [sector_weights_col])

            # 计算行业权重集中度（使用HHI）
            def calculate_sector_hhi(sector_dict):
                """计算行业权重HHI"""
                if not isinstance(sector_dict, dict) or len(sector_dict) == 0:
                    return np.nan
                hhi = sum(weight**2 for weight in sector_dict.values())
                return hhi

            sector_concentration = data[sector_weights_col].apply(calculate_sector_hhi)

            # 计算集中度的变化率
            allocation_shift = sector_concentration.pct_change(periods=window)

            return allocation_shift

        except (DataQualityError, OperatorError, ValueError):
            raise
        except Exception as e:
            logger.error(f"lof_sector_allocation_shift failed: {e}")
            raise OperatorError(f"lof_sector_allocation_shift failed: {e}") from e

    def lof_turnover_rate(self, data: pd.DataFrame, turnover_col: str = "turnover", window: int = 60) -> pd.Series:
        """LOF换手率

        白皮书依据: 第四章 4.1.18 - lof_turnover_rate

        分析LOF持仓换手率，评估基金经理交易频率。
        使用滚动平均换手率识别交易风格。

        Args:
            data: 输入数据框
            turnover_col: 换手率列名，默认'turnover'
            window: 滚动窗口大小，默认60

        Returns:
            换手率序列（滚动平均）

        Raises:
            OperatorError: 当缺失必需列或计算失败时
            ValueError: 当window <= 0时

        Example:
            >>> data = pd.DataFrame({
            ...     'turnover': [0.1, 0.15, 0.12, 0.18, 0.14] * 20
            ... })
            >>> operators = LOFOperators()
            >>> rate = operators.lof_turnover_rate(data, window=20)
        """
        try:
            # 验证参数
            if window <= 0:
                raise ValueError(f"window must be > 0, got {window}")

            # 验证数据
            self._validate_data(data, [turnover_col])

            # 计算滚动平均换手率
            turnover = data[turnover_col]
            avg_turnover = turnover.rolling(window=window).mean()

            return avg_turnover

        except (DataQualityError, OperatorError, ValueError):
            raise
        except Exception as e:
            logger.error(f"lof_turnover_rate failed: {e}")
            raise OperatorError(f"lof_turnover_rate failed: {e}") from e

    def lof_performance_persistence(
        self, data: pd.DataFrame, returns_col: str = "returns", window: int = 252
    ) -> pd.Series:
        """LOF业绩持续性

        白皮书依据: 第四章 4.1.18 - lof_performance_persistence

        评估LOF历史业绩的持续性，预测未来表现。
        计算收益率的自相关性，衡量业绩持续性。

        Args:
            data: 输入数据框
            returns_col: 收益率列名，默认'returns'
            window: 滚动窗口大小，默认252（一年）

        Returns:
            业绩持续性序列（收益率自相关系数）

        Raises:
            OperatorError: 当缺失必需列或计算失败时
            ValueError: 当window <= 1时

        Example:
            >>> data = pd.DataFrame({
            ...     'returns': [0.01, 0.02, 0.015, 0.018] * 100
            ... })
            >>> operators = LOFOperators()
            >>> persistence = operators.lof_performance_persistence(data, window=60)
        """
        try:
            # 验证参数
            if window <= 1:
                raise ValueError(f"window must be > 1, got {window}")

            # 验证数据
            self._validate_data(data, [returns_col])

            # 计算收益率的滚动自相关
            returns = data[returns_col]

            def rolling_autocorr(series):
                """计算滚动自相关"""
                if len(series) < 2:
                    return np.nan
                # 计算lag-1自相关
                return series.autocorr(lag=1)

            persistence = returns.rolling(window=window).apply(rolling_autocorr, raw=False)

            return persistence

        except (DataQualityError, OperatorError, ValueError):
            raise
        except Exception as e:
            logger.error(f"lof_performance_persistence failed: {e}")
            raise OperatorError(f"lof_performance_persistence failed: {e}") from e

    def lof_expense_ratio_impact(
        self, data: pd.DataFrame, expense_ratio_col: str = "expense_ratio", returns_col: str = "returns"
    ) -> pd.Series:
        """LOF费率影响

        白皮书依据: 第四章 4.1.18 - lof_expense_ratio_impact

        分析管理费、托管费对收益的影响，识别高性价比LOF。
        计算费率调整后的净收益。

        Args:
            data: 输入数据框
            expense_ratio_col: 费率列名，默认'expense_ratio'（年化费率）
            returns_col: 收益率列名，默认'returns'

        Returns:
            费率影响序列（费率调整后的收益）

        Raises:
            OperatorError: 当缺失必需列或计算失败时

        Example:
            >>> data = pd.DataFrame({
            ...     'returns': [0.01, 0.02, 0.015],
            ...     'expense_ratio': [0.015, 0.015, 0.015]  # 1.5% annual
            ... })
            >>> operators = LOFOperators()
            >>> impact = operators.lof_expense_ratio_impact(data)
        """
        try:
            # 验证数据
            self._validate_data(data, [expense_ratio_col, returns_col])

            # 计算费率调整后的收益
            # 假设费率是年化的，转换为日费率（除以252）
            returns = data[returns_col]
            expense_ratio = data[expense_ratio_col]
            daily_expense = expense_ratio / 252

            # 净收益 = 总收益 - 费率
            net_returns = returns - daily_expense

            return net_returns

        except (DataQualityError, OperatorError):
            raise
        except Exception as e:
            logger.error(f"lof_expense_ratio_impact failed: {e}")
            raise OperatorError(f"lof_expense_ratio_impact failed: {e}") from e

    def lof_dividend_yield_signal(
        self, data: pd.DataFrame, dividend_col: str = "dividend", nav_col: str = "nav"
    ) -> pd.Series:
        """LOF分红收益率信号

        白皮书依据: 第四章 4.1.18 - lof_dividend_yield_signal

        追踪LOF分红历史和预期，识别高分红LOF。
        计算分红收益率 = 分红 / 净值。

        Args:
            data: 输入数据框
            dividend_col: 分红列名，默认'dividend'
            nav_col: 净值列名，默认'nav'

        Returns:
            分红收益率信号序列

        Raises:
            OperatorError: 当缺失必需列或计算失败时

        Example:
            >>> data = pd.DataFrame({
            ...     'dividend': [0.1, 0.0, 0.15],
            ...     'nav': [10.0, 10.5, 11.0]
            ... })
            >>> operators = LOFOperators()
            >>> yield_signal = operators.lof_dividend_yield_signal(data)
            >>> print(yield_signal)
            0    0.010000
            1    0.000000
            2    0.013636
        """
        try:
            # 验证数据
            self._validate_data(data, [dividend_col, nav_col])

            # 计算分红收益率
            dividend = data[dividend_col]
            nav = data[nav_col]

            # 分红收益率 = 分红 / 净值（加小量避免除零）
            dividend_yield = dividend / (nav + 1e-8)

            return dividend_yield

        except (DataQualityError, OperatorError):
            raise
        except Exception as e:
            logger.error(f"lof_dividend_yield_signal failed: {e}")
            raise OperatorError(f"lof_dividend_yield_signal failed: {e}") from e

    def lof_nav_momentum(self, data: pd.DataFrame, nav_col: str = "nav", window: int = 20) -> pd.Series:
        """LOF净值动量

        白皮书依据: 第四章 4.1.18 - lof_nav_momentum (NEW)

        分析LOF净值的动量特征，识别净值趋势延续性。
        计算净值的滚动收益率作为动量指标。

        Args:
            data: 输入数据框
            nav_col: 净值列名，默认'nav'
            window: 滚动窗口大小，默认20

        Returns:
            净值动量序列（window期收益率）

        Raises:
            OperatorError: 当缺失必需列或计算失败时
            ValueError: 当window <= 0时

        Example:
            >>> data = pd.DataFrame({
            ...     'nav': [10.0, 10.1, 10.2, 10.15, 10.3] * 10
            ... })
            >>> operators = LOFOperators()
            >>> momentum = operators.lof_nav_momentum(data, window=5)
        """
        try:
            # 验证参数
            if window <= 0:
                raise ValueError(f"window must be > 0, got {window}")

            # 验证数据
            self._validate_data(data, [nav_col])

            # 计算净值动量（window期收益率）
            nav = data[nav_col]
            momentum = nav.pct_change(periods=window)

            return momentum

        except (DataQualityError, OperatorError, ValueError):
            raise
        except Exception as e:
            logger.error(f"lof_nav_momentum failed: {e}")
            raise OperatorError(f"lof_nav_momentum failed: {e}") from e

    def lof_redemption_pressure(
        self, data: pd.DataFrame, redemption_col: str = "redemption_amount", aum_col: str = "aum", window: int = 20
    ) -> pd.Series:
        """LOF赎回压力

        白皮书依据: 第四章 4.1.18 - lof_redemption_pressure (NEW)

        评估LOF面临的赎回压力，预测流动性危机。
        计算赎回金额占资产规模的比例。

        Args:
            data: 输入数据框
            redemption_col: 赎回金额列名，默认'redemption_amount'
            aum_col: 资产规模列名，默认'aum'
            window: 滚动窗口大小，默认20

        Returns:
            赎回压力序列（赎回金额/资产规模的滚动均值）

        Raises:
            OperatorError: 当缺失必需列或计算失败时
            ValueError: 当window <= 0时

        Example:
            >>> data = pd.DataFrame({
            ...     'redemption_amount': [50000, 60000, 55000] * 10,
            ...     'aum': [1000000, 980000, 970000] * 10
            ... })
            >>> operators = LOFOperators()
            >>> pressure = operators.lof_redemption_pressure(data, window=10)
        """
        try:
            # 验证参数
            if window <= 0:
                raise ValueError(f"window must be > 0, got {window}")

            # 验证数据
            self._validate_data(data, [redemption_col, aum_col])

            # 计算赎回压力比率
            redemption = data[redemption_col]
            aum = data[aum_col]

            # 赎回压力 = 赎回金额 / 资产规模（加小量避免除零）
            pressure_ratio = redemption / (aum + 1e-8)

            # 计算滚动平均
            redemption_pressure = pressure_ratio.rolling(window=window).mean()

            return redemption_pressure

        except (DataQualityError, OperatorError, ValueError):
            raise
        except Exception as e:
            logger.error(f"lof_redemption_pressure failed: {e}")
            raise OperatorError(f"lof_redemption_pressure failed: {e}") from e

    def lof_benchmark_tracking_quality(
        self,
        data: pd.DataFrame,
        returns_col: str = "returns",
        benchmark_col: str = "benchmark_returns",
        window: int = 60,
    ) -> pd.Series:
        """LOF基准跟踪质量

        白皮书依据: 第四章 4.1.18 - lof_benchmark_tracking_quality (NEW)

        评估LOF跟踪基准的质量，识别跟踪误差异常。
        计算跟踪误差（tracking error）= 超额收益的标准差。

        Args:
            data: 输入数据框
            returns_col: 收益率列名，默认'returns'
            benchmark_col: 基准收益率列名，默认'benchmark_returns'
            window: 滚动窗口大小，默认60

        Returns:
            基准跟踪质量序列（跟踪误差，值越小质量越好）

        Raises:
            OperatorError: 当缺失必需列或计算失败时
            ValueError: 当window <= 1时

        Example:
            >>> data = pd.DataFrame({
            ...     'returns': [0.01, 0.02, 0.015, 0.018] * 20,
            ...     'benchmark_returns': [0.008, 0.015, 0.012, 0.014] * 20
            ... })
            >>> operators = LOFOperators()
            >>> quality = operators.lof_benchmark_tracking_quality(data, window=20)
        """
        try:
            # 验证参数
            if window <= 1:
                raise ValueError(f"window must be > 1, got {window}")

            # 验证数据
            self._validate_data(data, [returns_col, benchmark_col])

            # 计算超额收益
            returns = data[returns_col]
            benchmark = data[benchmark_col]
            excess_returns = returns - benchmark

            # 计算跟踪误差（超额收益的滚动标准差）
            tracking_error = excess_returns.rolling(window=window).std()

            return tracking_error

        except (DataQualityError, OperatorError, ValueError):
            raise
        except Exception as e:
            logger.error(f"lof_benchmark_tracking_quality failed: {e}")
            raise OperatorError(f"lof_benchmark_tracking_quality failed: {e}") from e

    def lof_market_impact_cost(
        self, data: pd.DataFrame, volume_col: str = "volume", trade_size_col: str = "trade_size", window: int = 20
    ) -> pd.Series:
        """LOF市场冲击成本

        白皮书依据: 第四章 4.1.18 - lof_market_impact_cost (NEW)

        估算大额交易的市场冲击，优化交易执行策略。
        计算交易规模占成交量的比例作为冲击成本指标。

        Args:
            data: 输入数据框
            volume_col: 成交量列名，默认'volume'
            trade_size_col: 交易规模列名，默认'trade_size'
            window: 滚动窗口大小，默认20

        Returns:
            市场冲击成本序列（交易规模/成交量的滚动均值）

        Raises:
            OperatorError: 当缺失必需列或计算失败时
            ValueError: 当window <= 0时

        Example:
            >>> data = pd.DataFrame({
            ...     'volume': [100000, 120000, 110000] * 10,
            ...     'trade_size': [5000, 6000, 5500] * 10
            ... })
            >>> operators = LOFOperators()
            >>> impact = operators.lof_market_impact_cost(data, window=10)
        """
        try:
            # 验证参数
            if window <= 0:
                raise ValueError(f"window must be > 0, got {window}")

            # 验证数据
            self._validate_data(data, [volume_col, trade_size_col])

            # 计算市场冲击比率
            volume = data[volume_col]
            trade_size = data[trade_size_col]

            # 市场冲击 = 交易规模 / 成交量（加小量避免除零）
            impact_ratio = trade_size / (volume + 1e-8)

            # 计算滚动平均
            market_impact = impact_ratio.rolling(window=window).mean()

            return market_impact

        except (DataQualityError, OperatorError, ValueError):
            raise
        except Exception as e:
            logger.error(f"lof_market_impact_cost failed: {e}")
            raise OperatorError(f"lof_market_impact_cost failed: {e}") from e

    def lof_cross_sectional_momentum(
        self, data: pd.DataFrame, returns_col: str = "returns", peer_returns_col: str = "peer_returns", window: int = 20
    ) -> pd.Series:
        """LOF横截面动量

        白皮书依据: 第四章 4.1.18 - lof_cross_sectional_momentum (NEW)

        分析LOF在同类基金中的相对表现，识别相对强势LOF。
        计算LOF收益率相对于同类基金平均收益率的超额表现。
        正值表示相对强势，负值表示相对弱势。

        Args:
            data: 输入数据框
            returns_col: 收益率列名，默认'returns'
            peer_returns_col: 同类基金平均收益率列名，默认'peer_returns'
            window: 滚动窗口大小，默认20

        Returns:
            横截面动量序列（相对收益的滚动均值）

        Raises:
            OperatorError: 当缺失必需列或计算失败时
            ValueError: 当window <= 0时

        Example:
            >>> data = pd.DataFrame({
            ...     'returns': [0.01, 0.02, 0.015, 0.018] * 10,
            ...     'peer_returns': [0.008, 0.015, 0.012, 0.014] * 10
            ... })
            >>> operators = LOFOperators()
            >>> momentum = operators.lof_cross_sectional_momentum(data, window=10)
        """
        try:
            # 验证参数
            if window <= 0:
                raise ValueError(f"window must be > 0, got {window}")

            # 验证数据
            self._validate_data(data, [returns_col, peer_returns_col])

            # 计算相对收益
            returns = data[returns_col]
            peer_returns = data[peer_returns_col]
            relative_returns = returns - peer_returns

            # 计算横截面动量（相对收益的滚动均值）
            cross_sectional_momentum = relative_returns.rolling(window=window).mean()

            return cross_sectional_momentum

        except (DataQualityError, OperatorError, ValueError):
            raise
        except Exception as e:
            logger.error(f"lof_cross_sectional_momentum failed: {e}")
            raise OperatorError(f"lof_cross_sectional_momentum failed: {e}") from e
