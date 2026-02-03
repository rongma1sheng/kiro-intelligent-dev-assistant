"""增强非流动性因子挖掘器

白皮书依据: 第四章 4.1.2 增强非流动性因子挖掘器
需求: Requirements 5.1-5.8

专门用于发现和验证流动性相关因子的挖掘器。
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List

import numpy as np
import pandas as pd
from loguru import logger

from .factor_data_models import Factor, RiskFactor


@dataclass
class LiquidityMetrics:
    """流动性指标

    Attributes:
        amihud_ratio: Amihud非流动性比率
        bid_ask_spread: 买卖价差
        zero_return_ratio: 零收益率比例
        turnover_decay: 换手率衰减
        liquidity_premium: 流动性溢价
    """

    amihud_ratio: float
    bid_ask_spread: float
    zero_return_ratio: float
    turnover_decay: float
    liquidity_premium: float


@dataclass
class LiquidityStratification:
    """流动性分层结果

    Attributes:
        high_liquidity: 高流动性股票
        medium_liquidity: 中等流动性股票
        low_liquidity: 低流动性股票
        ic_by_stratum: 各层IC值
        ic_stability: IC稳定性
    """

    high_liquidity: List[str]
    medium_liquidity: List[str]
    low_liquidity: List[str]
    ic_by_stratum: Dict[str, float]
    ic_stability: float


@dataclass
class ExitLevels:
    """退出价格水平

    白皮书依据: 第四章 4.1.2 退出信号生成
    需求: Requirements 5.8

    Attributes:
        immediate_exit: 立即退出价格
        warning_level: 警告水平价格
        stop_loss_level: 止损价格
    """

    immediate_exit: float
    warning_level: float
    stop_loss_level: float

    def __post_init__(self):
        """验证价格水平的顺序

        退出价格水平应该从高到低：
        immediate_exit >= warning_level >= stop_loss_level
        """
        if not (
            self.immediate_exit >= self.warning_level >= self.stop_loss_level
        ):  # pylint: disable=superfluous-parens
            raise ValueError(
                f"价格水平顺序错误: immediate_exit({self.immediate_exit}) >= "
                f"warning_level({self.warning_level}) >= stop_loss_level({self.stop_loss_level})"
            )


class EnhancedIlliquidityMiner:
    """增强非流动性因子挖掘器

    白皮书依据: 第四章 4.1.2 增强非流动性因子挖掘器
    需求: Requirements 5.1-5.8

    专门用于发现在低流动性环境下表现良好的因子。

    核心功能:
    1. 流动性特定算子（Amihud比率、买卖价差、零收益率比例等）
    2. 流动性分层测试（高/中/低流动性三分位）
    3. 流动性适应性评分
    4. 失败因子转换为风险因子
    5. 退出信号生成

    通过标准:
    - 流动性适应性评分 > 0.6
    - IC标准差跨流动性层级 < 0.4
    """

    def __init__(self):
        """初始化增强非流动性挖掘器"""
        # 流动性特定算子
        self.illiquidity_operators = [
            "amihud_ratio",
            "bid_ask_spread",
            "zero_return_ratio",
            "turnover_decay",
            "liquidity_premium",
        ]

        # 流动性分层阈值
        self.liquidity_tercile_thresholds = [0.33, 0.67]

        # 适应性评分权重
        self.ic_stability_weight = 0.6
        self.low_liquidity_performance_weight = 0.4

        # IC稳定性阈值
        self.max_ic_std_across_strata = 0.4

        # 最小适应性评分
        self.min_adaptability_score = 0.6

        logger.info("[EnhancedIlliquidityMiner] Initialized with liquidity-specific operators")

    def calculate_amihud_ratio(
        self, returns: pd.Series, volume_dollar: pd.Series, clip_outliers: bool = True
    ) -> pd.Series:
        """计算Amihud非流动性比率

        白皮书依据: 第四章 4.1.2 Amihud比率
        需求: Requirements 5.3

        Amihud非流动性 = |return| / volume_dollar

        Args:
            returns: 收益率序列
            volume_dollar: 成交额序列（美元或人民币）
            clip_outliers: 是否截断异常值（使用99分位数），默认True

        Returns:
            pd.Series: Amihud非流动性比率

        Raises:
            ValueError: 当输入数据为空或长度不匹配时
        """
        if returns.empty or volume_dollar.empty:
            raise ValueError("收益率和成交额数据不能为空")

        if len(returns) != len(volume_dollar):
            raise ValueError(f"收益率和成交额长度不匹配: {len(returns)} vs {len(volume_dollar)}")

        # 检查成交额是否包含0或负数
        if (volume_dollar <= 0).any():
            raise ValueError("成交额不能包含0或负数")

        # 计算Amihud比率: |return| / volume_dollar
        amihud = abs(returns) / volume_dollar

        # 可选：处理异常值（使用99分位数截断）
        if clip_outliers and len(amihud) > 0:
            upper_bound = amihud.quantile(0.99)
            amihud = amihud.clip(upper=upper_bound)

        return amihud

    def estimate_bid_ask_spread(self, high: pd.Series, low: pd.Series, close: pd.Series) -> pd.Series:
        """估算买卖价差

        白皮书依据: 第四章 4.1.2 买卖价差估算
        需求: Requirements 5.1

        使用Roll模型估算: spread ≈ 2 * sqrt(-cov(Δp_t, Δp_{t-1}))
        简化版本: spread ≈ (high - low) / close

        Args:
            high: 最高价序列
            low: 最低价序列
            close: 收盘价序列

        Returns:
            pd.Series: 买卖价差估算值
        """
        if high.empty or low.empty or close.empty:
            raise ValueError("价格数据不能为空")

        # 简化的买卖价差估算
        spread = (high - low) / close

        # 处理异常值
        spread = spread.clip(lower=0, upper=0.1)  # 价差不应超过10%

        return spread.fillna(0)

    def calculate_zero_return_ratio(self, returns: pd.Series, window: int = 20) -> pd.Series:
        """计算零收益率比例

        白皮书依据: 第四章 4.1.2 零收益率比例
        需求: Requirements 5.1

        零收益率比例 = 滚动窗口内收益率为0的天数比例

        Args:
            returns: 收益率序列
            window: 滚动窗口大小

        Returns:
            pd.Series: 零收益率比例
        """
        if returns.empty:
            raise ValueError("收益率数据不能为空")

        if window <= 0:
            raise ValueError(f"窗口大小必须大于0: {window}")

        # 计算零收益率指示器
        zero_returns = (abs(returns) < 1e-6).astype(int)

        # 滚动计算零收益率比例
        zero_ratio = zero_returns.rolling(window=window).mean()

        return zero_ratio.fillna(0)

    def calculate_turnover_decay(self, turnover: pd.Series, window: int = 20) -> pd.Series:
        """计算换手率衰减

        白皮书依据: 第四章 4.1.2 换手率衰减
        需求: Requirements 5.1

        换手率衰减 = (当前换手率 - 历史平均换手率) / 历史平均换手率

        Args:
            turnover: 换手率序列
            window: 历史窗口大小

        Returns:
            pd.Series: 换手率衰减
        """
        if turnover.empty:
            raise ValueError("换手率数据不能为空")

        if window <= 0:
            raise ValueError(f"窗口大小必须大于0: {window}")

        # 计算历史平均换手率
        historical_avg = turnover.rolling(window=window).mean()

        # 计算衰减率
        decay = (turnover - historical_avg) / (historical_avg + 1e-6)

        return decay.fillna(0)

    def calculate_liquidity_premium(self, returns: pd.Series, amihud_ratio: pd.Series) -> pd.Series:
        """计算流动性溢价

        白皮书依据: 第四章 4.1.2 流动性溢价
        需求: Requirements 5.1

        流动性溢价 = 收益率 × Amihud比率
        （低流动性股票需要更高的收益率补偿）

        Args:
            returns: 收益率序列
            amihud_ratio: Amihud非流动性比率

        Returns:
            pd.Series: 流动性溢价
        """
        if returns.empty or amihud_ratio.empty:
            raise ValueError("收益率和Amihud比率数据不能为空")

        # 计算流动性溢价
        premium = returns * amihud_ratio

        return premium.fillna(0)

    def stratify_by_liquidity(
        self, market_data: pd.DataFrame, volume_column: str = "volume", price_column: str = "close"
    ) -> Dict[str, List[str]]:
        """按流动性分层

        白皮书依据: 第四章 4.1.2 流动性分层
        需求: Requirements 5.2, 5.4

        将股票分为高/中/低流动性三个层级（terciles）

        Args:
            market_data: 市场数据（MultiIndex: date, symbol）
            volume_column: 成交量列名
            price_column: 价格列名

        Returns:
            Dict: 三个流动性层级的股票列表
                - 'high': 高流动性股票代码列表
                - 'medium': 中等流动性股票代码列表
                - 'low': 低流动性股票代码列表

        Raises:
            ValueError: 当数据为空或缺少必需列时
        """
        if market_data.empty:
            raise ValueError("市场数据不能为空")

        if volume_column not in market_data.columns:
            raise ValueError(f"缺少成交量列: {volume_column}")

        if price_column not in market_data.columns:
            raise ValueError(f"缺少价格列: {price_column}")

        # 计算成交额（价格 × 成交量）
        volume_dollar = market_data[price_column] * market_data[volume_column]

        # 按股票分组，计算每只股票的平均成交额
        if isinstance(market_data.index, pd.MultiIndex):
            # MultiIndex: (date, symbol)
            avg_volume_by_symbol = volume_dollar.groupby(level="symbol").mean()
        else:
            # 单层索引，假设是symbol
            avg_volume_by_symbol = volume_dollar.groupby(market_data.index).mean()

        # 按流动性排序（百分位排名）
        liquidity_rank = avg_volume_by_symbol.rank(pct=True)

        # 分为三层（terciles）
        # 高流动性：前33%
        # 中等流动性：中间34%
        # 低流动性：后33%
        high_liquidity_symbols = liquidity_rank[liquidity_rank >= 0.67].index.tolist()
        low_liquidity_symbols = liquidity_rank[liquidity_rank < 0.33].index.tolist()
        medium_liquidity_symbols = liquidity_rank[(liquidity_rank >= 0.33) & (liquidity_rank < 0.67)].index.tolist()

        strata = {"high": high_liquidity_symbols, "medium": medium_liquidity_symbols, "low": low_liquidity_symbols}

        logger.info(
            f"[EnhancedIlliquidityMiner] Liquidity stratification: "
            f"high={len(strata['high'])}, "
            f"medium={len(strata['medium'])}, "
            f"low={len(strata['low'])}"
        )

        return strata

    def calculate_liquidity_adaptability(
        self, factor_values: pd.Series, returns: pd.Series, volume_data: pd.Series
    ) -> float:
        """计算因子的流动性适应性评分

        白皮书依据: 第四章 4.1.2 流动性适应性评分
        需求: Requirements 5.2, 5.5, 5.6

        评分 = IC稳定性 × 0.6 + 低流动性表现 × 0.4

        Args:
            factor_values: 因子值序列
            returns: 收益率序列
            volume_data: 成交量序列

        Returns:
            float: 流动性适应性评分 [0, 1]

        Raises:
            ValueError: 当数据为空或长度不匹配时
        """
        if factor_values.empty or returns.empty or volume_data.empty:
            raise ValueError("因子值、收益率和成交量数据不能为空")

        # 计算Amihud比率作为流动性指标
        price = 100.0  # 假设价格（简化）
        volume_dollar = volume_data * price
        amihud = self.calculate_amihud_ratio(returns, volume_dollar)

        # 按流动性分层
        liquidity_rank = amihud.rank(pct=True)

        high_liq_mask = liquidity_rank < self.liquidity_tercile_thresholds[0]
        low_liq_mask = liquidity_rank >= self.liquidity_tercile_thresholds[1]
        med_liq_mask = ~(high_liq_mask | low_liq_mask)

        # 计算各层IC
        ic_high = self._calculate_ic(factor_values[high_liq_mask], returns[high_liq_mask])
        ic_medium = self._calculate_ic(factor_values[med_liq_mask], returns[med_liq_mask])
        ic_low = self._calculate_ic(factor_values[low_liq_mask], returns[low_liq_mask])

        # 计算IC稳定性（标准差）
        ic_values = [ic_high, ic_medium, ic_low]
        ic_std = np.std(ic_values)
        ic_stability = max(0, 1 - ic_std / self.max_ic_std_across_strata)

        # 计算低流动性表现（归一化）
        low_liq_performance = min(1.0, abs(ic_low) / 0.1)  # IC > 0.1 为满分

        # 综合评分
        adaptability_score = (
            ic_stability * self.ic_stability_weight + low_liq_performance * self.low_liquidity_performance_weight
        )

        return adaptability_score

    def _calculate_ic(self, factor: pd.Series, returns: pd.Series) -> float:
        """计算信息系数（内部方法）"""
        if len(factor) < 10 or len(returns) < 10:
            return 0.0

        # 对齐索引
        common_index = factor.index.intersection(returns.index)
        if len(common_index) < 10:
            return 0.0

        factor_aligned = factor.loc[common_index]
        returns_aligned = returns.loc[common_index]

        # 去除NaN
        valid_mask = ~(factor_aligned.isna() | returns_aligned.isna())
        if valid_mask.sum() < 10:
            return 0.0

        factor_clean = factor_aligned[valid_mask]
        returns_clean = returns_aligned[valid_mask]

        # 计算Spearman相关系数
        ic = factor_clean.corr(returns_clean, method="spearman")

        return ic if not np.isnan(ic) else 0.0

    def convert_to_risk_factor(self, failed_factor: Factor, failure_reason: str) -> RiskFactor:
        """将失败的因子转换为风险因子

        白皮书依据: 第四章 4.1.2 失败因子转换
        需求: Requirements 1.8, 5.7

        失败的因子可以转换为风险信号，用于退出预测。

        Args:
            failed_factor: 失败的因子
            failure_reason: 失败原因

        Returns:
            RiskFactor: 风险因子
        """
        # 生成风险信号表达式（反转原因子）
        risk_signal_expression = f"-({failed_factor.expression})"

        # 确定风险类型
        if "correlation_flip" in failure_reason.lower():
            risk_type = "correlation_flip"
        elif "decay" in failure_reason.lower():
            risk_type = "factor_decay"
        elif "performance" in failure_reason.lower():
            risk_type = "performance_mutation"
        else:
            risk_type = "unknown"

        # 计算敏感度（基于原因子的IC）
        sensitivity = min(1.0, abs(failed_factor.baseline_ic) * 2)

        risk_factor = RiskFactor(
            original_factor_id=failed_factor.id,
            original_expression=failed_factor.expression,
            risk_signal_expression=risk_signal_expression,
            risk_type=risk_type,
            sensitivity=sensitivity,
            created_at=datetime.now(),
            conversion_reason=failure_reason,
            baseline_metrics={
                "ic": failed_factor.baseline_ic,
                "ir": failed_factor.baseline_ir,
                "sharpe": failed_factor.baseline_sharpe,
                "liquidity_adaptability": failed_factor.liquidity_adaptability,
            },
        )

        logger.info(
            f"[EnhancedIlliquidityMiner] Converted failed factor to risk factor: " f"{failed_factor.id} -> {risk_type}"
        )

        return risk_factor

    def generate_exit_levels(self, current_price: float, risk_factor_signal: float, volatility: float) -> ExitLevels:
        """生成退出价格水平

        白皮书依据: 第四章 4.1.2 退出信号生成
        需求: Requirements 5.8

        基于风险因子信号和波动率生成三个退出价格水平：
        - 立即退出：当前价格 - 1σ
        - 警告水平：当前价格 - 2σ
        - 止损水平：当前价格 - 3σ

        Args:
            current_price: 当前价格
            risk_factor_signal: 风险因子信号强度 [0, 1]
            volatility: 价格波动率

        Returns:
            ExitLevels: 三个退出价格水平

        Raises:
            ValueError: 当价格或波动率无效时
        """
        if current_price <= 0:
            raise ValueError(f"当前价格必须大于0: {current_price}")

        if volatility < 0:
            raise ValueError(f"波动率不能为负: {volatility}")

        if not 0 <= risk_factor_signal <= 1:
            raise ValueError(f"风险信号必须在[0, 1]范围内: {risk_factor_signal}")

        # 根据风险信号调整退出水平
        # 风险信号越强，退出水平越接近当前价格
        signal_multiplier = 1.0 + risk_factor_signal

        # 计算三个退出水平
        immediate_exit = current_price - signal_multiplier * 1.0 * volatility
        warning_level = current_price - signal_multiplier * 2.0 * volatility
        stop_loss_level = current_price - signal_multiplier * 3.0 * volatility

        # 确保价格 > 0（至少为当前价格的1%）
        min_price = current_price * 0.01
        immediate_exit = max(min_price, immediate_exit)
        warning_level = max(min_price, warning_level)
        stop_loss_level = max(min_price, stop_loss_level)

        return ExitLevels(immediate_exit=immediate_exit, warning_level=warning_level, stop_loss_level=stop_loss_level)
