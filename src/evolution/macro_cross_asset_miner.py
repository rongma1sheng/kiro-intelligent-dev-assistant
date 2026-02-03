"""宏观与跨资产因子挖掘器

白皮书依据: 第四章 4.1.11 宏观与跨资产因子挖掘
需求: 11.1-11.12

实现10个宏观跨资产算子，处理宏观经济数据和跨资产相关性分析。
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from loguru import logger
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler


@dataclass
class MacroIndicator:
    """宏观指标数据结构

    Attributes:
        name: 指标名称
        value: 指标值
        timestamp: 数据时间戳
        source: 数据来源
        delay_hours: 数据延迟（小时）
        is_nowcast: 是否为nowcast预测值
    """

    name: str
    value: float
    timestamp: datetime
    source: str
    delay_hours: float
    is_nowcast: bool = False


@dataclass
class CrossAssetCorrelation:
    """跨资产相关性数据结构

    Attributes:
        asset1: 资产1
        asset2: 资产2
        correlation: 相关系数
        window: 计算窗口（天）
        timestamp: 计算时间戳
    """

    asset1: str
    asset2: str
    correlation: float
    window: int
    timestamp: datetime


class MacroCrossAssetFactorMiner:
    """宏观与跨资产因子挖掘器

    白皮书依据: 第四章 4.1.11 宏观与跨资产因子挖掘
    需求: 11.1-11.12

    实现10个宏观跨资产算子：
    1. yield_curve_slope: 收益率曲线斜率
    2. credit_spread_widening: 信用利差扩大
    3. currency_carry_trade: 货币套利交易
    4. commodity_momentum: 商品动量
    5. vix_term_structure: VIX期限结构
    6. cross_asset_correlation: 跨资产相关性
    7. macro_surprise: 宏观数据意外
    8. central_bank_policy_shift: 央行政策转向
    9. global_liquidity_flow: 全球流动性流动
    10. geopolitical_risk: 地缘政治风险

    Attributes:
        operators: 算子字典
        macro_data_cache: 宏观数据缓存
        nowcast_models: Nowcast模型字典
        data_delay_threshold: 数据延迟阈值（小时）
    """

    def __init__(self, data_delay_threshold: float = 24.0):
        """初始化宏观跨资产因子挖掘器

        Args:
            data_delay_threshold: 数据延迟阈值（小时），默认24小时

        Raises:
            ValueError: 当data_delay_threshold <= 0时
        """
        if data_delay_threshold <= 0:
            raise ValueError(f"数据延迟阈值必须 > 0，当前: {data_delay_threshold}")

        self.data_delay_threshold: float = data_delay_threshold
        self.operators: Dict[str, Callable] = self._initialize_operators()
        self.macro_data_cache: Dict[str, MacroIndicator] = {}
        self.nowcast_models: Dict[str, Any] = {}

        logger.info(f"初始化MacroCrossAssetFactorMiner: " f"data_delay_threshold={data_delay_threshold}小时")

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
            "miner_type": "macro",
            "miner_name": "MacroCrossAssetFactorMiner",
            "is_healthy": self.is_healthy(),
            "error_count": self._error_count,
            "data_delay_threshold": self.data_delay_threshold,
            "operators_count": len(self.operators),
        }

    def _initialize_operators(self) -> Dict[str, Callable]:
        """初始化10个宏观跨资产算子

        白皮书依据: 第四章 4.1.11
        需求: 11.1-11.11

        Returns:
            算子字典
        """
        return {
            "yield_curve_slope": self._yield_curve_slope,
            "credit_spread_widening": self._credit_spread_widening,
            "currency_carry_trade": self._currency_carry_trade,
            "commodity_momentum": self._commodity_momentum,
            "vix_term_structure": self._vix_term_structure,
            "cross_asset_correlation": self._cross_asset_correlation,
            "macro_surprise": self._macro_surprise,
            "central_bank_policy_shift": self._central_bank_policy_shift,
            "global_liquidity_flow": self._global_liquidity_flow,
            "geopolitical_risk": self._geopolitical_risk,
        }

    def _yield_curve_slope(
        self, short_term_yield: pd.Series, long_term_yield: pd.Series, window: int = 20
    ) -> pd.Series:
        """计算收益率曲线斜率

        白皮书依据: 第四章 4.1.11
        需求: 11.1

        收益率曲线斜率 = 长期利率 - 短期利率
        正斜率表示经济扩张预期，负斜率（倒挂）表示衰退预期

        Args:
            short_term_yield: 短期利率序列（如2年期国债）
            long_term_yield: 长期利率序列（如10年期国债）
            window: 平滑窗口

        Returns:
            收益率曲线斜率序列

        Raises:
            ValueError: 当输入序列长度不一致时
        """
        if len(short_term_yield) != len(long_term_yield):
            raise ValueError(f"短期和长期利率序列长度不一致: " f"{len(short_term_yield)} vs {len(long_term_yield)}")

        # 计算斜率
        slope = long_term_yield - short_term_yield

        # 平滑处理
        slope_smoothed = slope.rolling(window=window, min_periods=1).mean()

        # 计算斜率变化率
        slope_smoothed.diff()

        logger.debug(
            f"收益率曲线斜率计算完成 - "
            f"平均斜率: {slope_smoothed.mean():.4f}, "
            f"当前斜率: {slope_smoothed.iloc[-1]:.4f}"
        )

        return slope_smoothed

    def _credit_spread_widening(
        self, corporate_yield: pd.Series, treasury_yield: pd.Series, window: int = 60
    ) -> pd.Series:
        """计算信用利差扩大指标

        白皮书依据: 第四章 4.1.11
        需求: 11.2

        信用利差 = 公司债收益率 - 国债收益率
        利差扩大表示信用风险上升，市场避险情绪增强

        Args:
            corporate_yield: 公司债收益率序列
            treasury_yield: 国债收益率序列
            window: 计算窗口

        Returns:
            信用利差扩大指标序列

        Raises:
            ValueError: 当输入序列长度不一致时
        """
        if len(corporate_yield) != len(treasury_yield):
            raise ValueError(f"公司债和国债收益率序列长度不一致: " f"{len(corporate_yield)} vs {len(treasury_yield)}")

        # 计算信用利差
        credit_spread = corporate_yield - treasury_yield

        # 计算利差变化
        spread_change = credit_spread.diff()

        # 计算利差扩大速度（标准化）
        spread_velocity = spread_change.rolling(window=window, min_periods=1).mean()
        spread_std = credit_spread.rolling(window=window, min_periods=1).std()

        # 标准化利差扩大指标
        spread_widening = spread_velocity / (spread_std + 1e-8)

        logger.debug(
            f"信用利差扩大计算完成 - "
            f"当前利差: {credit_spread.iloc[-1]:.4f}, "
            f"扩大速度: {spread_widening.iloc[-1]:.4f}"
        )

        return spread_widening

    def _currency_carry_trade(
        self, high_yield_currency: pd.Series, low_yield_currency: pd.Series, exchange_rate: pd.Series, window: int = 20
    ) -> pd.Series:
        """计算货币套利交易收益

        白皮书依据: 第四章 4.1.11
        需求: 11.3

        套利收益 = 利率差 + 汇率变化

        Args:
            high_yield_currency: 高收益货币利率
            low_yield_currency: 低收益货币利率
            exchange_rate: 汇率（高收益货币/低收益货币）
            window: 计算窗口

        Returns:
            套利交易收益序列

        Raises:
            ValueError: 当输入序列长度不一致时
        """
        if not (
            len(high_yield_currency) == len(low_yield_currency) == len(exchange_rate)
        ):  # pylint: disable=superfluous-parens
            raise ValueError(
                f"输入序列长度不一致: " f"{len(high_yield_currency)}, {len(low_yield_currency)}, {len(exchange_rate)}"
            )

        # 计算利率差
        interest_rate_diff = high_yield_currency - low_yield_currency

        # 计算汇率变化率
        fx_return = exchange_rate.pct_change()

        # 计算套利收益（年化）
        carry_return = interest_rate_diff / 252 + fx_return

        # 计算滚动夏普比率
        carry_mean = carry_return.rolling(window=window, min_periods=1).mean()
        carry_std = carry_return.rolling(window=window, min_periods=1).std()
        carry_sharpe = carry_mean / (carry_std + 1e-8) * np.sqrt(252)

        logger.debug(
            f"货币套利交易计算完成 - "
            f"利率差: {interest_rate_diff.iloc[-1]:.4f}, "
            f"套利夏普: {carry_sharpe.iloc[-1]:.4f}"
        )

        return carry_sharpe

    def _commodity_momentum(self, commodity_prices: pd.DataFrame, window: int = 60) -> pd.Series:
        """计算商品动量指标

        白皮书依据: 第四章 4.1.11
        需求: 11.4

        计算多个商品的综合动量指标

        Args:
            commodity_prices: 商品价格数据框（列为不同商品）
            window: 动量计算窗口

        Returns:
            商品动量指标序列

        Raises:
            ValueError: 当输入数据为空时
        """
        if commodity_prices.empty:
            raise ValueError("商品价格数据不能为空")

        # 计算每个商品的动量
        momentum_by_commodity = {}
        for commodity in commodity_prices.columns:
            prices = commodity_prices[commodity]

            # 计算收益率
            returns = prices.pct_change()

            # 计算动量（过去window天的累计收益）
            momentum = returns.rolling(window=window, min_periods=1).sum()

            momentum_by_commodity[commodity] = momentum

        # 转换为数据框
        momentum_df = pd.DataFrame(momentum_by_commodity)

        # 计算综合动量（等权平均）
        composite_momentum = momentum_df.mean(axis=1)

        # 标准化
        momentum_mean = composite_momentum.rolling(window=window, min_periods=1).mean()
        momentum_std = composite_momentum.rolling(window=window, min_periods=1).std()
        normalized_momentum = (composite_momentum - momentum_mean) / (momentum_std + 1e-8)

        logger.debug(
            f"商品动量计算完成 - "
            f"商品数量: {len(commodity_prices.columns)}, "
            f"当前动量: {normalized_momentum.iloc[-1]:.4f}"
        )

        return normalized_momentum

    def _vix_term_structure(self, vix_spot: pd.Series, vix_futures: pd.DataFrame, window: int = 20) -> pd.Series:
        """计算VIX期限结构指标

        白皮书依据: 第四章 4.1.11
        需求: 11.5

        Contango（正向市场）: 远期VIX > 近期VIX，表示市场预期波动率下降
        Backwardation（反向市场）: 远期VIX < 近期VIX，表示市场预期波动率上升

        Args:
            vix_spot: VIX现货指数
            vix_futures: VIX期货价格（列为不同到期月份）
            window: 计算窗口

        Returns:
            VIX期限结构指标序列（正值=Contango，负值=Backwardation）

        Raises:
            ValueError: 当输入数据长度不一致时
        """
        if len(vix_spot) != len(vix_futures):
            raise ValueError(f"VIX现货和期货数据长度不一致: " f"{len(vix_spot)} vs {len(vix_futures)}")

        # 计算期限结构斜率（第一个月期货 - 现货）
        if vix_futures.shape[1] > 0:
            first_month_future = vix_futures.iloc[:, 0]
            term_structure_slope = (first_month_future - vix_spot) / vix_spot
        else:
            raise ValueError("VIX期货数据至少需要一个到期月份")

        # 计算期限结构曲率（如果有多个到期月份）
        if vix_futures.shape[1] >= 2:
            second_month_future = vix_futures.iloc[:, 1]
            curvature = (second_month_future - 2 * first_month_future + vix_spot) / vix_spot
        else:
            curvature = pd.Series(0, index=vix_spot.index)

        # 综合指标：斜率 + 曲率
        term_structure_indicator = term_structure_slope + 0.5 * curvature

        # 平滑处理
        smoothed_indicator = term_structure_indicator.rolling(window=window, min_periods=1).mean()

        logger.debug(
            f"VIX期限结构计算完成 - "
            f"当前斜率: {term_structure_slope.iloc[-1]:.4f}, "
            f"综合指标: {smoothed_indicator.iloc[-1]:.4f}"
        )

        return smoothed_indicator

    def _cross_asset_correlation(self, asset_returns: pd.DataFrame, window: int = 60) -> pd.Series:
        """计算跨资产相关性指标

        白皮书依据: 第四章 4.1.11
        需求: 11.6

        计算不同资产类别之间的平均相关性
        相关性上升表示风险分散效果下降

        Args:
            asset_returns: 资产收益率数据框（列为不同资产）
            window: 相关性计算窗口

        Returns:
            平均跨资产相关性序列

        Raises:
            ValueError: 当输入数据少于2个资产时
        """
        if asset_returns.shape[1] < 2:
            raise ValueError(f"至少需要2个资产计算相关性，当前: {asset_returns.shape[1]}")

        # 计算滚动相关性矩阵
        correlations = []

        for i in range(len(asset_returns)):
            if i < window - 1:
                # 数据不足，使用可用数据
                window_data = asset_returns.iloc[: i + 1]
            else:
                window_data = asset_returns.iloc[i - window + 1 : i + 1]

            # 计算相关性矩阵
            corr_matrix = window_data.corr()

            # 提取上三角（不包括对角线）
            upper_triangle = corr_matrix.where(np.triu(np.ones(corr_matrix.shape), k=1).astype(bool))

            # 计算平均相关性
            avg_corr = upper_triangle.stack().mean()
            correlations.append(avg_corr)

        # 转换为序列
        correlation_series = pd.Series(correlations, index=asset_returns.index)

        logger.debug(
            f"跨资产相关性计算完成 - "
            f"资产数量: {asset_returns.shape[1]}, "
            f"当前平均相关性: {correlation_series.iloc[-1]:.4f}"
        )

        return correlation_series

    def _macro_surprise(self, actual_values: pd.Series, consensus_forecasts: pd.Series, window: int = 12) -> pd.Series:
        """计算宏观数据意外指标

        白皮书依据: 第四章 4.1.11
        需求: 11.7

        意外 = (实际值 - 预期值) / 历史标准差

        Args:
            actual_values: 实际公布值
            consensus_forecasts: 市场一致预期
            window: 标准化窗口

        Returns:
            标准化宏观意外指标

        Raises:
            ValueError: 当输入序列长度不一致时
        """
        if len(actual_values) != len(consensus_forecasts):
            raise ValueError(f"实际值和预期值序列长度不一致: " f"{len(actual_values)} vs {len(consensus_forecasts)}")

        # 计算原始意外
        raw_surprise = actual_values - consensus_forecasts

        # 标准化意外
        surprise_mean = raw_surprise.rolling(window=window, min_periods=1).mean()
        surprise_std = raw_surprise.rolling(window=window, min_periods=1).std()

        standardized_surprise = (raw_surprise - surprise_mean) / (surprise_std + 1e-8)

        # 计算累计意外（动量）
        surprise_momentum = standardized_surprise.rolling(window=3, min_periods=1).sum()

        logger.debug(
            f"宏观意外计算完成 - "
            f"当前意外: {standardized_surprise.iloc[-1]:.4f}, "
            f"意外动量: {surprise_momentum.iloc[-1]:.4f}"
        )

        return standardized_surprise

    def _central_bank_policy_shift(
        self, policy_rate: pd.Series, forward_guidance: pd.Series, window: int = 12
    ) -> pd.Series:
        """检测央行政策转向信号

        白皮书依据: 第四章 4.1.11
        需求: 11.8

        综合政策利率变化和前瞻指引变化检测政策转向

        Args:
            policy_rate: 政策利率序列
            forward_guidance: 前瞻指引指数（量化）
            window: 检测窗口

        Returns:
            政策转向信号序列（正值=鹰派转向，负值=鸽派转向）

        Raises:
            ValueError: 当输入序列长度不一致时
        """
        if len(policy_rate) != len(forward_guidance):
            raise ValueError(f"政策利率和前瞻指引序列长度不一致: " f"{len(policy_rate)} vs {len(forward_guidance)}")

        # 计算政策利率变化
        rate_change = policy_rate.diff()

        # 计算前瞻指引变化
        guidance_change = forward_guidance.diff()

        # 标准化
        rate_change_std = rate_change.rolling(window=window, min_periods=1).std()
        guidance_change_std = guidance_change.rolling(window=window, min_periods=1).std()

        rate_signal = rate_change / (rate_change_std + 1e-8)
        guidance_signal = guidance_change / (guidance_change_std + 1e-8)

        # 综合信号（加权平均）
        policy_shift_signal = 0.6 * rate_signal + 0.4 * guidance_signal

        # 检测转向点（信号方向改变）
        signal_direction = np.sign(policy_shift_signal)
        direction_change = signal_direction.diff().abs()

        # 转向强度
        shift_strength = policy_shift_signal * direction_change

        logger.debug(
            f"央行政策转向检测完成 - "
            f"当前信号: {policy_shift_signal.iloc[-1]:.4f}, "
            f"转向强度: {shift_strength.iloc[-1]:.4f}"
        )

        return policy_shift_signal

    def _global_liquidity_flow(
        self, central_bank_balance_sheets: pd.DataFrame, cross_border_flows: pd.DataFrame, window: int = 12
    ) -> pd.Series:
        """计算全球流动性流动指标

        白皮书依据: 第四章 4.1.11
        需求: 11.9

        综合央行资产负债表和跨境资金流动衡量全球流动性

        Args:
            central_bank_balance_sheets: 主要央行资产负债表规模
            cross_border_flows: 跨境资金流动数据
            window: 计算窗口

        Returns:
            全球流动性流动指标

        Raises:
            ValueError: 当输入数据为空时
        """
        if central_bank_balance_sheets.empty or cross_border_flows.empty:
            raise ValueError("央行资产负债表和跨境流动数据不能为空")

        # 计算央行资产负债表总规模变化率
        total_balance_sheet = central_bank_balance_sheets.sum(axis=1)
        balance_sheet_growth = total_balance_sheet.pct_change()

        # 计算跨境资金净流入
        net_cross_border_flow = cross_border_flows.sum(axis=1)
        flow_growth = net_cross_border_flow.pct_change()

        # 标准化
        bs_growth_mean = balance_sheet_growth.rolling(window=window, min_periods=1).mean()
        bs_growth_std = balance_sheet_growth.rolling(window=window, min_periods=1).std()
        bs_signal = (balance_sheet_growth - bs_growth_mean) / (bs_growth_std + 1e-8)

        flow_mean = flow_growth.rolling(window=window, min_periods=1).mean()
        flow_std = flow_growth.rolling(window=window, min_periods=1).std()
        flow_signal = (flow_growth - flow_mean) / (flow_std + 1e-8)

        # 综合流动性指标
        liquidity_indicator = 0.7 * bs_signal + 0.3 * flow_signal

        logger.debug(
            f"全球流动性流动计算完成 - "
            f"资产负债表信号: {bs_signal.iloc[-1]:.4f}, "
            f"综合指标: {liquidity_indicator.iloc[-1]:.4f}"
        )

        return liquidity_indicator

    def _geopolitical_risk(
        self, news_sentiment: pd.Series, safe_haven_flows: pd.Series, volatility_index: pd.Series, window: int = 20
    ) -> pd.Series:
        """计算地缘政治风险指标

        白皮书依据: 第四章 4.1.11
        需求: 11.10

        综合新闻情绪、避险资金流动和波动率指数衡量地缘政治风险

        Args:
            news_sentiment: 地缘政治新闻情绪指数
            safe_haven_flows: 避险资产资金流入
            volatility_index: 波动率指数
            window: 计算窗口

        Returns:
            地缘政治风险指标

        Raises:
            ValueError: 当输入序列长度不一致时
        """
        if not (
            len(news_sentiment) == len(safe_haven_flows) == len(volatility_index)
        ):  # pylint: disable=superfluous-parens
            raise ValueError(
                f"输入序列长度不一致: " f"{len(news_sentiment)}, {len(safe_haven_flows)}, {len(volatility_index)}"
            )

        # 标准化各个组件
        sentiment_mean = news_sentiment.rolling(window=window, min_periods=1).mean()
        sentiment_std = news_sentiment.rolling(window=window, min_periods=1).std()
        sentiment_signal = (news_sentiment - sentiment_mean) / (sentiment_std + 1e-8)

        flow_mean = safe_haven_flows.rolling(window=window, min_periods=1).mean()
        flow_std = safe_haven_flows.rolling(window=window, min_periods=1).std()
        flow_signal = (safe_haven_flows - flow_mean) / (flow_std + 1e-8)

        vol_mean = volatility_index.rolling(window=window, min_periods=1).mean()
        vol_std = volatility_index.rolling(window=window, min_periods=1).std()
        vol_signal = (volatility_index - vol_mean) / (vol_std + 1e-8)

        # 综合风险指标（加权平均）
        # 负面情绪、避险流入、波动率上升都表示风险上升
        risk_indicator = (
            0.4 * (-sentiment_signal) + 0.3 * flow_signal + 0.3 * vol_signal  # 负面情绪  # 避险流入  # 波动率上升
        )

        # 平滑处理
        smoothed_risk = risk_indicator.rolling(window=5, min_periods=1).mean()

        logger.debug(
            f"地缘政治风险计算完成 - "
            f"情绪信号: {sentiment_signal.iloc[-1]:.4f}, "
            f"综合风险: {smoothed_risk.iloc[-1]:.4f}"
        )

        return smoothed_risk

    def check_data_delay(self, data_timestamp: datetime, current_time: Optional[datetime] = None) -> Tuple[float, bool]:
        """检查数据延迟

        白皮书依据: 第四章 4.1.11
        需求: 11.12

        Args:
            data_timestamp: 数据时间戳
            current_time: 当前时间，None表示使用系统时间

        Returns:
            (延迟小时数, 是否需要nowcast)
        """
        if current_time is None:
            current_time = datetime.now()

        delay_hours = (current_time - data_timestamp).total_seconds() / 3600
        needs_nowcast = delay_hours > self.data_delay_threshold

        if needs_nowcast:
            logger.warning(
                f"数据延迟超过阈值: {delay_hours:.2f}小时 > {self.data_delay_threshold}小时，" f"需要使用nowcast模型"
            )

        return delay_hours, needs_nowcast

    def nowcast_macro_indicator(
        self, indicator_name: str, historical_data: pd.Series, auxiliary_data: Optional[pd.DataFrame] = None
    ) -> float:
        """使用nowcast模型预测宏观指标

        白皮书依据: 第四章 4.1.11
        需求: 11.12

        当宏观数据延迟超过24小时时，使用nowcast模型预测当前值

        Args:
            indicator_name: 指标名称
            historical_data: 历史数据
            auxiliary_data: 辅助高频数据（可选）

        Returns:
            Nowcast预测值

        Raises:
            ValueError: 当历史数据不足时
        """
        if len(historical_data) < 10:
            raise ValueError(f"历史数据不足，无法进行nowcast: {len(historical_data)} < 10")

        # 如果模型不存在，训练新模型
        if indicator_name not in self.nowcast_models:
            self._train_nowcast_model(indicator_name, historical_data, auxiliary_data)

        # 使用模型预测
        model = self.nowcast_models[indicator_name]

        if auxiliary_data is not None and not auxiliary_data.empty:
            # 使用辅助数据进行预测
            X = auxiliary_data.iloc[-1:].values.reshape(1, -1)
            nowcast_value = model.predict(X)[0]
        else:
            # 使用简单的时间序列外推
            recent_values = historical_data.iloc[-5:].values
            trend = np.polyfit(range(len(recent_values)), recent_values, deg=1)
            nowcast_value = np.polyval(trend, len(recent_values))

        logger.info(f"Nowcast预测完成 - " f"指标: {indicator_name}, " f"预测值: {nowcast_value:.4f}")

        return float(nowcast_value)

    def _train_nowcast_model(
        self, indicator_name: str, historical_data: pd.Series, auxiliary_data: Optional[pd.DataFrame] = None
    ):
        """训练nowcast模型

        Args:
            indicator_name: 指标名称
            historical_data: 历史数据
            auxiliary_data: 辅助高频数据（可选）
        """
        if auxiliary_data is not None and not auxiliary_data.empty:
            # 使用线性回归模型
            # 对齐数据
            aligned_data = pd.concat([historical_data, auxiliary_data], axis=1).dropna()

            if len(aligned_data) < 10:
                logger.warning(f"对齐后数据不足，使用简单模型: {len(aligned_data)} < 10")
                self.nowcast_models[indicator_name] = None
                return

            y = aligned_data.iloc[:, 0].values
            X = aligned_data.iloc[:, 1:].values

            # 标准化
            scaler = StandardScaler()
            X_scaled = scaler.fit_transform(X)

            # 训练模型
            model = LinearRegression()
            model.fit(X_scaled, y)

            # 保存模型和scaler
            self.nowcast_models[indicator_name] = {"model": model, "scaler": scaler}

            logger.info(f"Nowcast模型训练完成 - " f"指标: {indicator_name}, " f"R²: {model.score(X_scaled, y):.4f}")
        else:
            # 没有辅助数据，使用简单模型
            self.nowcast_models[indicator_name] = None
            logger.info(f"使用简单时间序列外推模型: {indicator_name}")

    def mine_factors(
        self,
        data: Dict[str, pd.DataFrame],
        symbols: List[str],  # pylint: disable=unused-argument
        start_date: datetime,
        end_date: datetime,  # pylint: disable=unused-argument
    ) -> List[pd.Series]:
        """挖掘宏观跨资产因子

        白皮书依据: 第四章 4.1.11
        需求: 11.1-11.12

        Args:
            data: 数据字典，包含各类宏观和资产数据
            symbols: 股票代码列表
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            因子列表

        Raises:
            ValueError: 当必需数据缺失时
        """
        factors = []

        try:
            # 1. 收益率曲线斜率
            if "short_term_yield" in data and "long_term_yield" in data:
                yield_slope = self._yield_curve_slope(data["short_term_yield"], data["long_term_yield"])
                factors.append(yield_slope)

            # 2. 信用利差扩大
            if "corporate_yield" in data and "treasury_yield" in data:
                credit_spread = self._credit_spread_widening(data["corporate_yield"], data["treasury_yield"])
                factors.append(credit_spread)

            # 3. 货币套利交易
            if all(k in data for k in ["high_yield_currency", "low_yield_currency", "exchange_rate"]):
                carry_trade = self._currency_carry_trade(
                    data["high_yield_currency"], data["low_yield_currency"], data["exchange_rate"]
                )
                factors.append(carry_trade)

            # 4. 商品动量
            if "commodity_prices" in data:
                commodity_mom = self._commodity_momentum(data["commodity_prices"])
                factors.append(commodity_mom)

            # 5. VIX期限结构
            if "vix_spot" in data and "vix_futures" in data:
                vix_term = self._vix_term_structure(data["vix_spot"], data["vix_futures"])
                factors.append(vix_term)

            # 6. 跨资产相关性
            if "asset_returns" in data:
                cross_corr = self._cross_asset_correlation(data["asset_returns"])
                factors.append(cross_corr)

            # 7. 宏观意外
            if "actual_values" in data and "consensus_forecasts" in data:
                macro_surp = self._macro_surprise(data["actual_values"], data["consensus_forecasts"])
                factors.append(macro_surp)

            # 8. 央行政策转向
            if "policy_rate" in data and "forward_guidance" in data:
                policy_shift = self._central_bank_policy_shift(data["policy_rate"], data["forward_guidance"])
                factors.append(policy_shift)

            # 9. 全球流动性流动
            if "central_bank_balance_sheets" in data and "cross_border_flows" in data:
                liquidity = self._global_liquidity_flow(data["central_bank_balance_sheets"], data["cross_border_flows"])
                factors.append(liquidity)

            # 10. 地缘政治风险
            if all(k in data for k in ["news_sentiment", "safe_haven_flows", "volatility_index"]):
                geo_risk = self._geopolitical_risk(
                    data["news_sentiment"], data["safe_haven_flows"], data["volatility_index"]
                )
                factors.append(geo_risk)

            logger.info(
                f"宏观跨资产因子挖掘完成 - " f"生成因子数量: {len(factors)}, " f"时间范围: {start_date} 到 {end_date}"
            )

        except Exception as e:
            logger.error(f"因子挖掘失败: {e}")
            raise

        return factors
