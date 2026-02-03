"""事件驱动因子算子库

白皮书依据: 第四章 4.1.16 事件驱动因子挖掘器

本模块实现15种核心事件驱动算子，用于识别和量化各类公司事件对股价的影响。

Author: MIA Team
Date: 2026-01-25
"""

import numpy as np
import pandas as pd
from loguru import logger


class EventDrivenOperatorRegistry:
    """事件驱动算子注册表

    白皮书依据: 第四章 4.1.16 事件驱动因子挖掘器

    提供15种核心事件驱动算子：
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
    """

    def __init__(self):
        """初始化事件驱动算子注册表"""
        logger.debug("初始化EventDrivenOperatorRegistry")

    def earnings_surprise(
        self,
        data: pd.DataFrame,
        earnings_col: str = "earnings_actual",
        estimate_col: str = "earnings_estimate",
        window: int = 20,
    ) -> pd.Series:
        """计算盈利意外

        白皮书依据: 第四章 4.1.16 盈利意外

        盈利意外 = (实际盈利 - 预期盈利) / 预期盈利
        正值表示超预期，负值表示低于预期

        Args:
            data: 市场数据
            earnings_col: 实际盈利列名
            estimate_col: 预期盈利列名
            window: 计算窗口

        Returns:
            盈利意外指数
        """
        if data.empty:
            return pd.Series(0, index=data.index)

        # 如果有实际盈利数据
        if earnings_col in data.columns and estimate_col in data.columns:
            actual = data[earnings_col]
            estimate = data[estimate_col]
            surprise = (actual - estimate) / (estimate.abs() + 1e-8)
            return surprise

        # 如果没有盈利数据，使用价格跳空作为代理
        if "close" in data.columns:
            price = data["close"]
            # 计算隔夜跳空（假设盈利公布在盘后）
            overnight_gap = (price - price.shift(1)) / price.shift(1)
            # 识别异常跳空（可能是盈利意外）
            gap_threshold = overnight_gap.rolling(window=window).std() * 2
            surprise_proxy = overnight_gap / (gap_threshold + 1e-8)
            return surprise_proxy.clip(-5, 5)

        return pd.Series(0, index=data.index)

    def merger_arbitrage_spread(
        self,
        data: pd.DataFrame,
        target_price_col: str = "merger_target_price",
        price_col: str = "close",
        window: int = 20,
    ) -> pd.Series:
        """计算并购套利价差

        白皮书依据: 第四章 4.1.16 并购套利价差

        并购套利价差 = (目标价格 - 当前价格) / 当前价格
        正值表示套利空间，负值表示交易可能失败

        Args:
            data: 市场数据
            target_price_col: 并购目标价格列名
            price_col: 当前价格列名
            window: 计算窗口

        Returns:
            并购套利价差
        """
        if data.empty or price_col not in data.columns:
            return pd.Series(0, index=data.index)

        price = data[price_col]

        # 如果有并购目标价格数据
        if target_price_col in data.columns:
            target_price = data[target_price_col]
            spread = (target_price - price) / price
            return spread

        # 如果没有并购数据，使用价格偏离历史高点作为代理
        # （并购通常发生在股价低迷时）
        rolling_high = price.rolling(window=window * 5).max()
        spread_proxy = (rolling_high - price) / price
        return spread_proxy.clip(0, 1)

    def ipo_lockup_expiry(
        self,
        data: pd.DataFrame,
        lockup_expiry_col: str = "lockup_expiry_date",
        days_before: int = 30,
        days_after: int = 10,
    ) -> pd.Series:
        """计算IPO锁定期到期影响

        白皮书依据: 第四章 4.1.16 IPO锁定期到期

        锁定期到期前后，股价通常会受到抛压影响。

        Args:
            data: 市场数据
            lockup_expiry_col: 锁定期到期日列名
            days_before: 到期前天数
            days_after: 到期后天数

        Returns:
            锁定期到期影响指数 (负值表示抛压)
        """
        if data.empty:
            return pd.Series(0, index=data.index)

        # 如果有锁定期数据
        if lockup_expiry_col in data.columns:
            # 计算距离锁定期到期的天数
            expiry_dates = pd.to_datetime(data[lockup_expiry_col], errors="coerce")
            days_to_expiry = (expiry_dates - data.index).dt.days

            # 到期前后的影响（负值表示抛压）
            impact = pd.Series(0.0, index=data.index)
            impact[days_to_expiry.between(-days_after, days_before)] = -1.0

            # 到期前影响逐渐增强
            mask_before = days_to_expiry.between(0, days_before)
            impact[mask_before] = -days_to_expiry[mask_before] / days_before

            return impact

        # 如果没有锁定期数据，使用上市后时间作为代理
        # 假设上市6个月后锁定期到期
        if "close" in data.columns and "volume" in data.columns:
            # 使用成交量异常作为代理（锁定期到期时成交量放大）
            volume = data["volume"]
            volume_ma = volume.rolling(window=20).mean()
            volume_surge = (volume - volume_ma) / (volume_ma + 1e-8)

            # 成交量激增 + 价格下跌 = 可能是锁定期到期抛压
            price = data["close"]
            price_change = price.pct_change()
            lockup_proxy = volume_surge * (-price_change)

            return lockup_proxy.clip(-1, 1)

        return pd.Series(0, index=data.index)

    def dividend_announcement(
        self,
        data: pd.DataFrame,
        dividend_col: str = "dividend_yield",
        announcement_col: str = "dividend_announcement",  # pylint: disable=unused-argument
        window: int = 20,
    ) -> pd.Series:
        """计算股息公告影响

        白皮书依据: 第四章 4.1.16 股息公告

        股息公告通常是正面信号，尤其是股息增加时。

        Args:
            data: 市场数据
            dividend_col: 股息率列名
            announcement_col: 股息公告列名
            window: 计算窗口

        Returns:
            股息公告影响指数 (正值表示利好)
        """
        if data.empty:
            return pd.Series(0, index=data.index)

        # 如果有股息数据
        if dividend_col in data.columns:
            dividend = data[dividend_col]
            # 计算股息变化
            dividend_change = dividend.diff()
            dividend_momentum = dividend_change.rolling(window=window).mean()
            return dividend_momentum

        # 如果没有股息数据，使用价格稳定性作为代理
        # （高股息股票通常价格稳定）
        if "close" in data.columns:
            price = data["close"]
            returns = price.pct_change()
            volatility = returns.rolling(window=window).std()

            # 低波动 + 正收益 = 可能是高股息股票
            avg_return = returns.rolling(window=window).mean()
            dividend_proxy = avg_return / (volatility + 1e-8)

            return dividend_proxy.clip(-5, 5)

        return pd.Series(0, index=data.index)

    def share_buyback_signal(  # pylint: disable=too-many-positional-arguments
        self,
        data: pd.DataFrame,
        buyback_col: str = "share_buyback",
        price_col: str = "close",
        volume_col: str = "volume",
        window: int = 20,
    ) -> pd.Series:
        """计算股票回购信号

        白皮书依据: 第四章 4.1.16 股票回购信号

        股票回购通常是管理层对公司价值的信心表现。

        Args:
            data: 市场数据
            buyback_col: 回购金额列名
            price_col: 价格列名
            volume_col: 成交量列名
            window: 计算窗口

        Returns:
            股票回购信号 (正值表示回购活跃)
        """
        if data.empty or price_col not in data.columns or volume_col not in data.columns:
            return pd.Series(0, index=data.index)

        # 如果有回购数据
        if buyback_col in data.columns:
            buyback = data[buyback_col]
            buyback_momentum = buyback.rolling(window=window).sum()
            return buyback_momentum

        # 如果没有回购数据，使用价格支撑 + 成交量作为代理
        price = data[price_col]
        volume = data[volume_col]

        # 回购特征：价格下跌时成交量放大（公司在买入）
        price_change = price.pct_change()
        volume_ma = volume.rolling(window=window).mean()
        volume_ratio = volume / (volume_ma + 1e-8)

        # 价格下跌 + 成交量放大 = 可能是回购
        buyback_proxy = (-price_change) * volume_ratio
        buyback_signal = buyback_proxy.rolling(window=window).mean()

        return buyback_signal.clip(0, 5)

    def management_change(
        self,
        data: pd.DataFrame,
        management_change_col: str = "management_change",
        price_col: str = "close",
        window: int = 60,
    ) -> pd.Series:
        """计算管理层变动影响

        白皮书依据: 第四章 4.1.16 管理层变动

        管理层变动（尤其是CEO更换）对股价有显著影响。

        Args:
            data: 市场数据
            management_change_col: 管理层变动列名
            price_col: 价格列名
            window: 计算窗口

        Returns:
            管理层变动影响指数
        """
        if data.empty or price_col not in data.columns:
            return pd.Series(0, index=data.index)

        # 如果有管理层变动数据
        if management_change_col in data.columns:
            change_events = data[management_change_col]
            # 计算变动后的累积影响
            impact = change_events.rolling(window=window).sum()
            return impact

        # 如果没有管理层数据，使用价格趋势反转作为代理
        # （管理层变动通常发生在业绩不佳后，可能带来反转）
        price = data[price_col]

        # 计算长期和短期趋势
        long_trend = price.pct_change(window)
        short_trend = price.pct_change(window // 3)

        # 趋势反转信号
        trend_reversal = (long_trend < 0) & (short_trend > 0)
        reversal_signal = trend_reversal.astype(float)

        return reversal_signal.rolling(window=window).sum()

    def regulatory_approval(
        self, data: pd.DataFrame, approval_col: str = "regulatory_approval", price_col: str = "close", window: int = 20
    ) -> pd.Series:
        """计算监管批准影响

        白皮书依据: 第四章 4.1.16 监管批准

        监管批准（如药品批准、并购批准）是重大利好。

        Args:
            data: 市场数据
            approval_col: 监管批准列名
            price_col: 价格列名
            window: 计算窗口

        Returns:
            监管批准影响指数 (正值表示利好)
        """
        if data.empty or price_col not in data.columns:
            return pd.Series(0, index=data.index)

        # 如果有监管批准数据
        if approval_col in data.columns:
            approval = data[approval_col]
            approval_impact = approval.rolling(window=window).sum()
            return approval_impact

        # 如果没有监管数据，使用价格跳空作为代理
        # （监管批准通常导致价格跳空）
        price = data[price_col]

        # 计算隔夜跳空
        overnight_gap = (price - price.shift(1)) / price.shift(1)

        # 识别显著正向跳空（可能是监管批准）
        gap_threshold = overnight_gap.rolling(window=window).std() * 2
        significant_gap = (overnight_gap > gap_threshold).astype(float)

        approval_proxy = significant_gap.rolling(window=window).sum()

        return approval_proxy

    def product_launch(  # pylint: disable=too-many-positional-arguments
        self,
        data: pd.DataFrame,
        launch_col: str = "product_launch",
        price_col: str = "close",
        volume_col: str = "volume",
        window: int = 20,
    ) -> pd.Series:
        """计算产品发布影响

        白皮书依据: 第四章 4.1.16 产品发布

        新产品发布是重要的催化剂事件。

        Args:
            data: 市场数据
            launch_col: 产品发布列名
            price_col: 价格列名
            volume_col: 成交量列名
            window: 计算窗口

        Returns:
            产品发布影响指数
        """
        if data.empty or price_col not in data.columns or volume_col not in data.columns:
            return pd.Series(0, index=data.index)

        # 如果有产品发布数据
        if launch_col in data.columns:
            launch = data[launch_col]
            launch_impact = launch.rolling(window=window).sum()
            return launch_impact

        # 如果没有产品发布数据，使用价格上涨 + 成交量放大作为代理
        price = data[price_col]
        volume = data[volume_col]

        price_change = price.pct_change()
        volume_ma = volume.rolling(window=window).mean()
        volume_surge = volume / (volume_ma + 1e-8)

        # 价格上涨 + 成交量放大 = 可能是产品发布
        launch_proxy = (price_change > 0).astype(float) * volume_surge
        launch_signal = launch_proxy.rolling(window=window).mean()

        return launch_signal.clip(0, 5)

    def earnings_guidance_revision(
        self, data: pd.DataFrame, guidance_col: str = "earnings_guidance", price_col: str = "close", window: int = 20
    ) -> pd.Series:
        """计算业绩指引修正影响

        白皮书依据: 第四章 4.1.16 业绩指引修正

        业绩指引上调/下调对股价有直接影响。

        Args:
            data: 市场数据
            guidance_col: 业绩指引列名
            price_col: 价格列名
            window: 计算窗口

        Returns:
            业绩指引修正影响 (正值=上调，负值=下调)
        """
        if data.empty or price_col not in data.columns:
            return pd.Series(0, index=data.index)

        # 如果有业绩指引数据
        if guidance_col in data.columns:
            guidance = data[guidance_col]
            guidance_change = guidance.diff()
            revision_momentum = guidance_change.rolling(window=window).mean()
            return revision_momentum

        # 如果没有指引数据，使用价格动量作为代理
        price = data[price_col]

        # 计算价格动量的加速度（指引修正通常导致趋势加速）
        momentum = price.pct_change(window)
        momentum_change = momentum.diff()

        revision_proxy = momentum_change.rolling(window=window).mean()

        return revision_proxy.clip(-0.1, 0.1)

    def analyst_upgrade_downgrade(
        self, data: pd.DataFrame, rating_col: str = "analyst_rating", price_col: str = "close", window: int = 20
    ) -> pd.Series:
        """计算分析师评级变动影响

        白皮书依据: 第四章 4.1.16 分析师评级变动

        分析师上调/下调评级对股价有短期影响。

        Args:
            data: 市场数据
            rating_col: 分析师评级列名
            price_col: 价格列名
            window: 计算窗口

        Returns:
            分析师评级变动影响 (正值=上调，负值=下调)
        """
        if data.empty or price_col not in data.columns:
            return pd.Series(0, index=data.index)

        # 如果有分析师评级数据
        if rating_col in data.columns:
            rating = data[rating_col]
            rating_change = rating.diff()
            upgrade_momentum = rating_change.rolling(window=window).mean()
            return upgrade_momentum

        # 如果没有评级数据，使用价格跳空 + 成交量作为代理
        price = data[price_col]

        # 分析师评级变动通常在盘前公布，导致开盘跳空
        overnight_gap = (price - price.shift(1)) / price.shift(1)

        # 计算跳空的方向和强度
        gap_strength = overnight_gap.rolling(window=window).mean()

        return gap_strength.clip(-0.1, 0.1)

    def index_rebalancing(  # pylint: disable=too-many-positional-arguments
        self,
        data: pd.DataFrame,
        index_weight_col: str = "index_weight",
        price_col: str = "close",
        volume_col: str = "volume",
        window: int = 20,
    ) -> pd.Series:
        """计算指数再平衡影响

        白皮书依据: 第四章 4.1.16 指数再平衡

        指数再平衡时，被动资金流入/流出对股价有显著影响。

        Args:
            data: 市场数据
            index_weight_col: 指数权重列名
            price_col: 价格列名
            volume_col: 成交量列名
            window: 计算窗口

        Returns:
            指数再平衡影响 (正值=流入，负值=流出)
        """
        if data.empty or price_col not in data.columns or volume_col not in data.columns:
            return pd.Series(0, index=data.index)

        # 如果有指数权重数据
        if index_weight_col in data.columns:
            weight = data[index_weight_col]
            weight_change = weight.diff()
            rebalancing_impact = weight_change.rolling(window=window).sum()
            return rebalancing_impact

        # 如果没有指数数据，使用成交量异常作为代理
        # （指数再平衡日成交量通常异常放大）
        volume = data[volume_col]
        volume_ma = volume.rolling(window=window).mean()
        volume_surge = (volume - volume_ma) / (volume_ma + 1e-8)

        # 识别异常成交量日（可能是再平衡日）
        rebalancing_proxy = (volume_surge > 2).astype(float)

        # 结合价格变化判断流入/流出
        price = data[price_col]
        price_change = price.pct_change()

        rebalancing_signal = rebalancing_proxy * np.sign(price_change)

        return rebalancing_signal.rolling(window=window).sum()

    def corporate_action(
        self, data: pd.DataFrame, action_col: str = "corporate_action", price_col: str = "close", window: int = 20
    ) -> pd.Series:
        """计算公司行动影响

        白皮书依据: 第四章 4.1.16 公司行动

        公司行动包括：拆股、合股、分拆、资产剥离等。

        Args:
            data: 市场数据
            action_col: 公司行动列名
            price_col: 价格列名
            window: 计算窗口

        Returns:
            公司行动影响指数
        """
        if data.empty or price_col not in data.columns:
            return pd.Series(0, index=data.index)

        # 如果有公司行动数据
        if action_col in data.columns:
            action = data[action_col]
            action_impact = action.rolling(window=window).sum()
            return action_impact

        # 如果没有公司行动数据，使用价格异常变化作为代理
        price = data[price_col]

        # 计算价格变化的异常值
        price_change = price.pct_change()
        price_change_ma = price_change.rolling(window=window).mean()
        price_change_std = price_change.rolling(window=window).std()

        # 识别异常价格变化（可能是公司行动）
        z_score = (price_change - price_change_ma) / (price_change_std + 1e-8)
        abnormal_change = (z_score.abs() > 3).astype(float)

        action_proxy = abnormal_change.rolling(window=window).sum()

        return action_proxy

    def litigation_risk(  # pylint: disable=too-many-positional-arguments
        self,
        data: pd.DataFrame,
        litigation_col: str = "litigation_events",
        price_col: str = "close",
        volume_col: str = "volume",
        window: int = 60,
    ) -> pd.Series:
        """计算诉讼风险

        白皮书依据: 第四章 4.1.16 诉讼风险

        诉讼事件通常是负面信号，增加不确定性。

        Args:
            data: 市场数据
            litigation_col: 诉讼事件列名
            price_col: 价格列名
            volume_col: 成交量列名
            window: 计算窗口

        Returns:
            诉讼风险指数 (正值表示风险增加)
        """
        if data.empty or price_col not in data.columns or volume_col not in data.columns:
            return pd.Series(0, index=data.index)

        # 如果有诉讼数据
        if litigation_col in data.columns:
            litigation = data[litigation_col]
            risk_accumulation = litigation.rolling(window=window).sum()
            return risk_accumulation

        # 如果没有诉讼数据，使用价格下跌 + 波动率上升作为代理
        price = data[price_col]

        # 计算价格下跌
        price_change = price.pct_change()
        price_decline = (-price_change).clip(0, 1)

        # 计算波动率上升
        volatility = price_change.rolling(window=window).std()
        vol_ma = volatility.rolling(window=window * 2).mean()
        vol_increase = ((volatility - vol_ma) / (vol_ma + 1e-8)).clip(0, 5)

        # 诉讼风险 = 价格下跌 + 波动率上升
        risk_proxy = price_decline * 0.6 + vol_increase * 0.4
        risk_signal = risk_proxy.rolling(window=window).mean()

        return risk_signal

    def credit_rating_change(
        self, data: pd.DataFrame, rating_col: str = "credit_rating", price_col: str = "close", window: int = 20
    ) -> pd.Series:
        """计算信用评级变动影响

        白皮书依据: 第四章 4.1.16 信用评级变动

        信用评级上调/下调对股价和债券价格有显著影响。

        Args:
            data: 市场数据
            rating_col: 信用评级列名
            price_col: 价格列名
            window: 计算窗口

        Returns:
            信用评级变动影响 (正值=上调，负值=下调)
        """
        if data.empty or price_col not in data.columns:
            return pd.Series(0, index=data.index)

        # 如果有信用评级数据
        if rating_col in data.columns:
            rating = data[rating_col]
            rating_change = rating.diff()
            rating_momentum = rating_change.rolling(window=window).mean()
            return rating_momentum

        # 如果没有评级数据，使用价格趋势 + 财务健康度代理
        price = data[price_col]

        # 计算价格趋势（评级上调通常伴随价格上涨）
        price_trend = price.pct_change(window)

        # 计算价格稳定性（评级上调的公司通常价格稳定）
        returns = price.pct_change()
        volatility = returns.rolling(window=window).std()
        stability = 1 / (volatility + 1e-8)
        stability_norm = (stability - stability.rolling(window=window * 2).mean()) / (
            stability.rolling(window=window * 2).std() + 1e-8
        )

        # 综合信号
        rating_proxy = price_trend * 0.6 + stability_norm * 0.4

        return rating_proxy.clip(-1, 1)

    def activist_investor_entry(  # pylint: disable=too-many-positional-arguments
        self,
        data: pd.DataFrame,
        activist_col: str = "activist_entry",
        price_col: str = "close",
        volume_col: str = "volume",
        window: int = 60,
    ) -> pd.Series:
        """计算激进投资者进入影响

        白皮书依据: 第四章 4.1.16 激进投资者进入

        激进投资者进入通常推动公司变革，对股价有显著影响。

        Args:
            data: 市场数据
            activist_col: 激进投资者进入列名
            price_col: 价格列名
            volume_col: 成交量列名
            window: 计算窗口

        Returns:
            激进投资者进入影响指数
        """
        if data.empty or price_col not in data.columns or volume_col not in data.columns:
            return pd.Series(0, index=data.index)

        # 如果有激进投资者数据
        if activist_col in data.columns:
            activist = data[activist_col]
            activist_impact = activist.rolling(window=window).sum()
            return activist_impact

        # 如果没有激进投资者数据，使用大额持仓变化作为代理
        price = data[price_col]
        volume = data[volume_col]

        # 激进投资者进入特征：
        # 1. 成交量持续放大
        volume_ma = volume.rolling(window=window).mean()
        volume_surge = (volume / (volume_ma + 1e-8)).rolling(window=10).mean()

        # 2. 价格从低位反弹
        price_low = price.rolling(window=window).min()
        price_recovery = (price - price_low) / (price_low + 1e-8)

        # 3. 波动率上升（激进投资者推动变革）
        returns = price.pct_change()
        volatility = returns.rolling(window=window).std()
        vol_ma = volatility.rolling(window=window * 2).mean()
        vol_increase = (volatility - vol_ma) / (vol_ma + 1e-8)

        # 综合信号
        activist_proxy = volume_surge * 0.4 + price_recovery * 0.3 + vol_increase * 0.3

        activist_signal = activist_proxy.rolling(window=window).mean()

        # 填充NaN值
        activist_signal = activist_signal.fillna(0)

        return activist_signal.clip(0, 5)
