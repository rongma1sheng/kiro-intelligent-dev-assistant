"""宏观与跨资产算子注册表

白皮书依据: 第四章 4.1.15 - 宏观与跨资产因子挖掘器
版本: v1.0.0

本模块实现10个宏观跨资产专用算子:
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
"""

from typing import Any, Callable, Dict, Optional

import numpy as np
import pandas as pd
from loguru import logger


class OperatorError(Exception):
    """算子计算错误"""


class DataQualityError(Exception):
    """数据质量错误"""


class MacroCrossAssetOperatorRegistry:
    """宏观与跨资产算子注册表

    白皮书依据: 第四章 4.1.15 - 宏观与跨资产因子挖掘器

    提供:
    1. 10个宏观跨资产算子的注册机制
    2. 算子验证和错误处理
    3. 数据质量检查
    4. 算子计算与日志记录

    Attributes:
        operators: 算子名称到计算函数的映射
        operator_metadata: 算子名称到元数据的映射
    """

    def __init__(self):
        """初始化宏观与跨资产算子注册表

        白皮书依据: 第四章 4.1.15 - 宏观与跨资产因子挖掘器
        """
        self.operators: Dict[str, Callable] = {}
        self.operator_metadata: Dict[str, Dict[str, Any]] = {}

        # 注册所有算子
        self._register_all_operators()

        logger.info(f"MacroCrossAssetOperatorRegistry初始化完成，共{len(self.operators)}个算子")

    def _register_all_operators(self) -> None:
        """注册所有10个宏观跨资产算子

        白皮书依据: 第四章 4.1.15 - 宏观与跨资产因子挖掘器
        """
        # 1. 收益率曲线斜率
        self._register_operator(
            name="yield_curve_slope",
            func=self.yield_curve_slope,
            category="interest_rate",
            description="收益率曲线斜率",
            formula="long_rate - short_rate",
        )

        # 2. 信用利差扩大
        self._register_operator(
            name="credit_spread_widening",
            func=self.credit_spread_widening,
            category="credit",
            description="信用利差扩大检测",
            formula="credit_spread - credit_spread_ma",
        )

        # 3. 货币套利交易
        self._register_operator(
            name="currency_carry_trade",
            func=self.currency_carry_trade,
            category="currency",
            description="货币套利交易信号",
            formula="interest_rate_diff * exchange_rate_momentum",
        )

        # 4. 商品动量
        self._register_operator(
            name="commodity_momentum",
            func=self.commodity_momentum,
            category="commodity",
            description="商品价格动量",
            formula="commodity_price_change(window)",
        )

        # 5. VIX期限结构
        self._register_operator(
            name="vix_term_structure",
            func=self.vix_term_structure,
            category="volatility",
            description="VIX期限结构",
            formula="vix_short / vix_long",
        )

        # 6. 跨资产相关性
        self._register_operator(
            name="cross_asset_correlation",
            func=self.cross_asset_correlation,
            category="correlation",
            description="跨资产相关性",
            formula="rolling_corr(asset1, asset2, window)",
        )

        # 7. 宏观意外指数
        self._register_operator(
            name="macro_surprise_index",
            func=self.macro_surprise_index,
            category="macro",
            description="宏观数据意外指数",
            formula="(actual - forecast) / std(actual - forecast)",
        )

        # 8. 央行政策转向
        self._register_operator(
            name="central_bank_policy_shift",
            func=self.central_bank_policy_shift,
            category="policy",
            description="央行政策转向检测",
            formula="detect_policy_change(interest_rate)",
        )

        # 9. 全球流动性流动
        self._register_operator(
            name="global_liquidity_flow",
            func=self.global_liquidity_flow,
            category="liquidity",
            description="全球流动性流动",
            formula="sum(central_bank_balance_sheets)",
        )

        # 10. 地缘政治风险指数
        self._register_operator(
            name="geopolitical_risk_index",
            func=self.geopolitical_risk_index,
            category="risk",
            description="地缘政治风险指数",
            formula="weighted_sum(geopolitical_events)",
        )

    def _register_operator(  # pylint: disable=too-many-positional-arguments
        self, name: str, func: Callable, category: str, description: str, formula: str
    ) -> None:  # pylint: disable=too-many-positional-arguments
        """注册算子及其元数据

        Args:
            name: 算子名称
            func: 算子计算函数
            category: 算子类别
            description: 算子描述
            formula: 数学公式
        """
        self.operators[name] = func
        self.operator_metadata[name] = {"category": category, "description": description, "formula": formula}

        logger.debug(f"注册算子: {name} ({category})")

    def get_operator(self, name: str) -> Optional[Callable]:
        """根据名称获取算子函数

        Args:
            name: 算子名称

        Returns:
            算子函数，如果不存在则返回None
        """
        return self.operators.get(name)

    def get_operator_names(self) -> list[str]:
        """获取所有算子名称列表

        Returns:
            算子名称列表
        """
        return list(self.operators.keys())

    def get_operators_by_category(self, category: str) -> Dict[str, Callable]:
        """获取指定类别的所有算子

        Args:
            category: 类别名称

        Returns:
            算子名称到函数的映射
        """
        return {
            name: func for name, func in self.operators.items() if self.operator_metadata[name]["category"] == category
        }

    def validate_operator_input(self, data: pd.DataFrame, required_columns: list[str]) -> None:
        """验证算子输入数据

        白皮书依据: 第四章 4.1 - 数据质量要求

        Args:
            data: 输入数据
            required_columns: 必需的列名

        Raises:
            OperatorError: 验证失败时
        """
        if data.empty:
            raise OperatorError("输入数据为空")

        missing_columns = set(required_columns) - set(data.columns)
        if missing_columns:
            raise OperatorError(f"缺少必需列: {missing_columns}")

        # 检查过多的NaN值 (>50%阈值)
        for col in required_columns:
            nan_ratio = data[col].isna().sum() / len(data)
            if nan_ratio > 0.5:
                raise DataQualityError(f"列 {col} 有 {nan_ratio:.1%} NaN值 (阈值: 50%)")

    # ========================================================================
    # 算子实现 (10个)
    # ========================================================================

    def yield_curve_slope(
        self, data: pd.DataFrame, short_rate_col: str = "short_rate", long_rate_col: str = "long_rate"
    ) -> pd.Series:
        """计算收益率曲线斜率

        白皮书依据: 第四章 4.1.15 - yield_curve_slope
        公式: long_rate - short_rate

        收益率曲线斜率反映经济预期：
        - 正斜率（正常）：经济扩张预期
        - 负斜率（倒挂）：经济衰退预警
        - 平坦：经济转折点

        Args:
            data: 包含利率数据的数据框
            short_rate_col: 短期利率列名
            long_rate_col: 长期利率列名

        Returns:
            收益率曲线斜率序列

        Raises:
            OperatorError: 计算失败时
        """
        try:
            self.validate_operator_input(data, [short_rate_col, long_rate_col])

            short_rate = data[short_rate_col]
            long_rate = data[long_rate_col]

            # 计算斜率
            slope = long_rate - short_rate

            # 统计倒挂情况
            inversion_ratio = (slope < 0).sum() / len(slope)
            if inversion_ratio > 0.1:
                logger.warning(f"收益率曲线倒挂比例: {inversion_ratio:.1%} " f"(阈值: 10%)")

            logger.debug(f"计算yield_curve_slope: mean={slope.mean():.4f}")

            return slope

        except Exception as e:
            logger.error(f"yield_curve_slope计算失败: {e}")
            raise OperatorError(f"yield_curve_slope失败: {e}") from e

    def credit_spread_widening(
        self, data: pd.DataFrame, credit_spread_col: str = "credit_spread", window: int = 20, threshold: float = 0.5
    ) -> pd.Series:
        """检测信用利差扩大

        白皮书依据: 第四章 4.1.15 - credit_spread_widening
        公式: credit_spread - credit_spread_ma

        信用利差扩大预示：
        - 信用风险上升
        - 流动性紧张
        - 经济衰退风险

        Args:
            data: 包含信用利差数据的数据框
            credit_spread_col: 信用利差列名
            window: 移动平均窗口
            threshold: 扩大阈值（标准差倍数）

        Returns:
            信用利差扩大信号（1=扩大，0=正常）

        Raises:
            OperatorError: 计算失败时
        """
        try:
            self.validate_operator_input(data, [credit_spread_col])

            credit_spread = data[credit_spread_col]

            # 计算移动平均
            spread_ma = credit_spread.rolling(window=window).mean()
            spread_std = credit_spread.rolling(window=window).std()

            # 检测扩大
            spread_deviation = (credit_spread - spread_ma) / (spread_std + 1e-8)
            widening_signal = (spread_deviation > threshold).astype(int)

            widening_count = widening_signal.sum()
            logger.debug(
                f"计算credit_spread_widening: "
                f"扩大信号={widening_count} "
                f"({widening_count / len(widening_signal) * 100:.1f}%)"
            )

            return widening_signal

        except Exception as e:
            logger.error(f"credit_spread_widening计算失败: {e}")
            raise OperatorError(f"credit_spread_widening失败: {e}") from e

    def currency_carry_trade(
        self,
        data: pd.DataFrame,
        interest_rate_diff_col: str = "interest_rate_diff",
        exchange_rate_col: str = "exchange_rate",
        window: int = 20,
    ) -> pd.Series:
        """计算货币套利交易信号

        白皮书依据: 第四章 4.1.15 - currency_carry_trade
        公式: interest_rate_diff * exchange_rate_momentum

        货币套利交易策略：
        - 借入低利率货币
        - 投资高利率货币
        - 赚取利差收益

        Args:
            data: 包含利率差和汇率数据的数据框
            interest_rate_diff_col: 利率差列名
            exchange_rate_col: 汇率列名
            window: 动量计算窗口

        Returns:
            货币套利交易信号

        Raises:
            OperatorError: 计算失败时
        """
        try:
            self.validate_operator_input(data, [interest_rate_diff_col, exchange_rate_col])

            interest_rate_diff = data[interest_rate_diff_col]
            exchange_rate = data[exchange_rate_col]

            # 计算汇率动量
            exchange_rate_momentum = exchange_rate.pct_change(window)

            # 套利信号 = 利率差 * 汇率动量
            carry_signal = interest_rate_diff * exchange_rate_momentum

            logger.debug(f"计算currency_carry_trade: mean={carry_signal.mean():.4f}")

            return carry_signal

        except Exception as e:
            logger.error(f"currency_carry_trade计算失败: {e}")
            raise OperatorError(f"currency_carry_trade失败: {e}") from e

    def commodity_momentum(
        self, data: pd.DataFrame, commodity_price_col: str = "commodity_price", window: int = 20
    ) -> pd.Series:
        """计算商品价格动量

        白皮书依据: 第四章 4.1.15 - commodity_momentum
        公式: commodity_price_change(window)

        商品动量反映：
        - 通胀预期
        - 经济活动强度
        - 供需关系

        Args:
            data: 包含商品价格数据的数据框
            commodity_price_col: 商品价格列名
            window: 动量计算窗口

        Returns:
            商品价格动量序列

        Raises:
            OperatorError: 计算失败时
        """
        try:
            self.validate_operator_input(data, [commodity_price_col])

            commodity_price = data[commodity_price_col]

            # 计算价格动量
            momentum = commodity_price.pct_change(window)

            logger.debug(f"计算commodity_momentum: mean={momentum.mean():.4f}")

            return momentum

        except Exception as e:
            logger.error(f"commodity_momentum计算失败: {e}")
            raise OperatorError(f"commodity_momentum失败: {e}") from e

    def vix_term_structure(
        self, data: pd.DataFrame, vix_short_col: str = "vix_short", vix_long_col: str = "vix_long"
    ) -> pd.Series:
        """计算VIX期限结构

        白皮书依据: 第四章 4.1.15 - vix_term_structure
        公式: vix_short / vix_long

        VIX期限结构形态：
        - Contango（正向）：短期VIX < 长期VIX（市场平静）
        - Backwardation（反向）：短期VIX > 长期VIX（市场恐慌）

        Args:
            data: 包含VIX数据的数据框
            vix_short_col: 短期VIX列名
            vix_long_col: 长期VIX列名

        Returns:
            VIX期限结构比率（>1=反向，<1=正向）

        Raises:
            OperatorError: 计算失败时
        """
        try:
            self.validate_operator_input(data, [vix_short_col, vix_long_col])

            vix_short = data[vix_short_col]
            vix_long = data[vix_long_col]

            # 计算期限结构比率
            term_structure = vix_short / (vix_long + 1e-8)

            # 统计反向市场
            backwardation_ratio = (term_structure > 1).sum() / len(term_structure)
            if backwardation_ratio > 0.2:
                logger.warning(f"VIX反向市场比例: {backwardation_ratio:.1%} " f"(阈值: 20%)")

            logger.debug(f"计算vix_term_structure: mean={term_structure.mean():.4f}")

            return term_structure

        except Exception as e:
            logger.error(f"vix_term_structure计算失败: {e}")
            raise OperatorError(f"vix_term_structure失败: {e}") from e

    def cross_asset_correlation(
        self, data: pd.DataFrame, asset1_col: str = "asset1", asset2_col: str = "asset2", window: int = 60
    ) -> pd.Series:
        """计算跨资产相关性

        白皮书依据: 第四章 4.1.15 - cross_asset_correlation
        公式: rolling_corr(asset1, asset2, window)

        跨资产相关性变化反映：
        - 风险传染
        - 避险情绪
        - 资产配置机会

        Args:
            data: 包含资产数据的数据框
            asset1_col: 资产1列名
            asset2_col: 资产2列名
            window: 滚动窗口

        Returns:
            跨资产相关系数序列 [-1, 1]

        Raises:
            OperatorError: 计算失败时
        """
        try:
            self.validate_operator_input(data, [asset1_col, asset2_col])

            asset1 = data[asset1_col]
            asset2 = data[asset2_col]

            # 计算滚动相关系数
            correlation = asset1.rolling(window=window).corr(asset2)

            # 检测相关性突变
            corr_change = correlation.diff().abs()
            significant_changes = (corr_change > 0.3).sum()

            if significant_changes > 0:
                logger.info(f"检测到{significant_changes}个跨资产相关性突变 " f"(变化 > 0.3)")

            logger.debug(f"计算cross_asset_correlation: mean={correlation.mean():.4f}")

            return correlation

        except Exception as e:
            logger.error(f"cross_asset_correlation计算失败: {e}")
            raise OperatorError(f"cross_asset_correlation失败: {e}") from e

    def macro_surprise_index(
        self, data: pd.DataFrame, actual_col: str = "actual", forecast_col: str = "forecast", window: int = 12
    ) -> pd.Series:
        """计算宏观数据意外指数

        白皮书依据: 第四章 4.1.15 - macro_surprise_index
        公式: (actual - forecast) / std(actual - forecast)

        宏观意外指数衡量：
        - 经济数据超预期程度
        - 市场预期偏差
        - 政策调整可能性

        Args:
            data: 包含实际值和预测值的数据框
            actual_col: 实际值列名
            forecast_col: 预测值列名
            window: 标准化窗口

        Returns:
            宏观意外指数（标准化）

        Raises:
            OperatorError: 计算失败时
        """
        try:
            self.validate_operator_input(data, [actual_col, forecast_col])

            actual = data[actual_col]
            forecast = data[forecast_col]

            # 计算意外
            surprise = actual - forecast

            # 标准化
            surprise_mean = surprise.rolling(window=window).mean()
            surprise_std = surprise.rolling(window=window).std()

            surprise_index = (surprise - surprise_mean) / (surprise_std + 1e-8)

            # 统计显著意外
            significant_surprises = (surprise_index.abs() > 2).sum()
            logger.debug(
                f"计算macro_surprise_index: "
                f"显著意外={significant_surprises} "
                f"({significant_surprises / len(surprise_index) * 100:.1f}%)"
            )

            return surprise_index

        except Exception as e:
            logger.error(f"macro_surprise_index计算失败: {e}")
            raise OperatorError(f"macro_surprise_index失败: {e}") from e

    def central_bank_policy_shift(
        self, data: pd.DataFrame, policy_rate_col: str = "policy_rate", window: int = 3
    ) -> pd.Series:
        """检测央行政策转向

        白皮书依据: 第四章 4.1.15 - central_bank_policy_shift
        公式: detect_policy_change(interest_rate)

        政策转向类型：
        - 加息周期开始
        - 降息周期开始
        - 政策暂停

        Args:
            data: 包含政策利率数据的数据框
            policy_rate_col: 政策利率列名
            window: 检测窗口

        Returns:
            政策转向信号（1=加息，-1=降息，0=不变）

        Raises:
            OperatorError: 计算失败时
        """
        try:
            self.validate_operator_input(data, [policy_rate_col])

            policy_rate = data[policy_rate_col]

            # 计算利率变化
            rate_change = policy_rate.diff()

            # 检测持续变化（政策转向）
            rate_change_sign = np.sign(rate_change)
            policy_shift = rate_change_sign.rolling(window=window).mean()

            # 转换为信号
            shift_signal = pd.Series(0, index=data.index)
            shift_signal[policy_shift > 0.5] = 1  # 加息周期
            shift_signal[policy_shift < -0.5] = -1  # 降息周期

            # 统计政策转向
            hike_count = (shift_signal == 1).sum()
            cut_count = (shift_signal == -1).sum()

            logger.debug(f"计算central_bank_policy_shift: " f"加息={hike_count}, 降息={cut_count}")

            return shift_signal

        except Exception as e:
            logger.error(f"central_bank_policy_shift计算失败: {e}")
            raise OperatorError(f"central_bank_policy_shift失败: {e}") from e

    def global_liquidity_flow(
        self, data: pd.DataFrame, balance_sheet_cols: list[str] = None, window: int = 12
    ) -> pd.Series:
        """计算全球流动性流动

        白皮书依据: 第四章 4.1.15 - global_liquidity_flow
        公式: sum(central_bank_balance_sheets)

        全球流动性反映：
        - 货币政策宽松程度
        - 市场资金供给
        - 资产价格支撑

        Args:
            data: 包含央行资产负债表数据的数据框
            balance_sheet_cols: 资产负债表列名列表
            window: 变化率计算窗口

        Returns:
            全球流动性变化率

        Raises:
            OperatorError: 计算失败时
        """
        try:
            if balance_sheet_cols is None:
                # 默认查找所有包含'balance_sheet'的列
                balance_sheet_cols = [col for col in data.columns if "balance_sheet" in col.lower()]

            if not balance_sheet_cols:
                raise OperatorError("未找到资产负债表数据列")

            self.validate_operator_input(data, balance_sheet_cols)

            # 计算总流动性
            total_liquidity = data[balance_sheet_cols].sum(axis=1)

            # 计算变化率
            liquidity_change = total_liquidity.pct_change(window)

            logger.debug(f"计算global_liquidity_flow: mean={liquidity_change.mean():.4f}")

            return liquidity_change

        except Exception as e:
            logger.error(f"global_liquidity_flow计算失败: {e}")
            raise OperatorError(f"global_liquidity_flow失败: {e}") from e

    def geopolitical_risk_index(
        self, data: pd.DataFrame, event_cols: list[str] = None, weights: Optional[Dict[str, float]] = None
    ) -> pd.Series:
        """计算地缘政治风险指数

        白皮书依据: 第四章 4.1.15 - geopolitical_risk_index
        公式: weighted_sum(geopolitical_events)

        地缘政治风险包括：
        - 军事冲突
        - 贸易摩擦
        - 政治动荡
        - 恐怖袭击

        Args:
            data: 包含地缘政治事件数据的数据框
            event_cols: 事件列名列表
            weights: 事件权重字典

        Returns:
            地缘政治风险指数

        Raises:
            OperatorError: 计算失败时
        """
        try:
            if event_cols is None:
                # 默认查找所有包含'risk'或'event'的列
                event_cols = [col for col in data.columns if "risk" in col.lower() or "event" in col.lower()]

            if not event_cols:
                raise OperatorError("未找到地缘政治事件数据列")

            self.validate_operator_input(data, event_cols)

            # 默认权重（均等）
            if weights is None:
                weights = {col: 1.0 / len(event_cols) for col in event_cols}

            # 计算加权风险指数
            risk_index = pd.Series(0.0, index=data.index)
            for col in event_cols:
                weight = weights.get(col, 1.0 / len(event_cols))
                risk_index += data[col] * weight

            # 归一化到[0, 1]
            risk_index = (risk_index - risk_index.min()) / (risk_index.max() - risk_index.min() + 1e-8)

            # 统计高风险期
            high_risk_periods = (risk_index > 0.7).sum()
            logger.debug(
                f"计算geopolitical_risk_index: "
                f"高风险期={high_risk_periods} "
                f"({high_risk_periods / len(risk_index) * 100:.1f}%)"
            )

            return risk_index

        except Exception as e:
            logger.error(f"geopolitical_risk_index计算失败: {e}")
            raise OperatorError(f"geopolitical_risk_index失败: {e}") from e
