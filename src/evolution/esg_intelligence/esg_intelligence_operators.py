"""ESG智能因子算子库

白皮书依据: 第四章 4.1.10 ESG智能因子挖掘器

本模块实现8种核心ESG智能算子，用于挖掘ESG（环境、社会、治理）相关因子。

Author: MIA Team
Date: 2026-01-25
"""

import numpy as np
import pandas as pd
from loguru import logger


class ESGIntelligenceOperatorRegistry:
    """ESG智能算子注册表

    白皮书依据: 第四章 4.1.10 ESG智能因子挖掘器

    提供8种核心ESG智能算子：
    1. esg_controversy_shock - ESG争议冲击
    2. carbon_emission_trend - 碳排放趋势
    3. employee_satisfaction - 员工满意度
    4. board_diversity_score - 董事会多样性
    5. green_investment_ratio - 绿色投资比例
    6. esg_momentum - ESG改善动量
    7. sustainability_score - 可持续性评分
    8. esg_risk_premium - ESG风险溢价
    """

    def __init__(self):
        """初始化ESG智能算子注册表"""
        logger.debug("初始化ESGIntelligenceOperatorRegistry")

    def esg_controversy_shock(
        self, data: pd.DataFrame, controversy_col: str = "esg_controversy", price_col: str = "close", window: int = 60
    ) -> pd.Series:
        """计算ESG争议冲击

        白皮书依据: 第四章 4.1.10 ESG争议冲击

        ESG争议事件（环境污染、劳工纠纷、治理丑闻）对股价的负面冲击。

        Args:
            data: 市场数据
            controversy_col: ESG争议列名
            price_col: 价格列名
            window: 计算窗口

        Returns:
            ESG争议冲击指数 (正值表示负面冲击)
        """
        if data.empty or price_col not in data.columns:
            return pd.Series(0, index=data.index)

        # 如果有ESG争议数据
        if controversy_col in data.columns:
            controversy = data[controversy_col]
            # 计算争议事件的累积影响
            shock_impact = controversy.rolling(window=window).sum()
            return shock_impact

        # 如果没有ESG数据，使用负面新闻 + 价格下跌作为代理
        price = data[price_col]

        # 1. 价格异常下跌（可能是ESG争议）
        price_change = price.pct_change()
        price_drop = (-price_change).clip(0, 0.2)

        # 2. 波动率上升（争议导致不确定性）
        volatility = price_change.rolling(window=window).std()
        vol_ma = volatility.rolling(window=window * 2).mean()
        vol_increase = ((volatility - vol_ma) / (vol_ma + 1e-8)).clip(0, 5)

        # 3. 成交量放大（争议引发关注）
        if "volume" in data.columns:
            volume = data["volume"]
            volume_ma = volume.rolling(window=window).mean()
            volume_surge = ((volume - volume_ma) / (volume_ma + 1e-8)).clip(0, 3)
        else:
            volume_surge = pd.Series(0, index=data.index)

        # 综合争议冲击
        controversy_proxy = price_drop * 0.4 + vol_increase * 0.3 + volume_surge * 0.3

        shock_signal = controversy_proxy.rolling(window=window).mean()

        return shock_signal.fillna(0)

    def carbon_emission_trend(
        self, data: pd.DataFrame, emission_col: str = "carbon_emission", price_col: str = "close", window: int = 252
    ) -> pd.Series:
        """计算碳排放趋势

        白皮书依据: 第四章 4.1.10 碳排放趋势

        碳排放趋势反映公司的环境责任，低碳转型是长期趋势。

        Args:
            data: 市场数据
            emission_col: 碳排放列名
            price_col: 价格列名
            window: 计算窗口（年度数据，252交易日）

        Returns:
            碳排放趋势 (负值=减排，正值=增排)
        """
        if data.empty or price_col not in data.columns:
            return pd.Series(0, index=data.index)

        # 如果有碳排放数据
        if emission_col in data.columns:
            emission = data[emission_col]
            # 计算碳排放变化趋势
            emission_trend = emission.diff().rolling(window=window).mean()
            # 归一化
            emission_norm = emission_trend / (emission.rolling(window=window).mean() + 1e-8)
            return emission_norm

        # 如果没有碳排放数据，使用行业特征作为代理
        # 高碳行业（能源、材料）vs 低碳行业（科技、服务）
        price = data[price_col]

        # 使用价格长期趋势作为代理
        # 低碳转型的公司长期表现更好
        long_term_return = price.pct_change(window)

        # 使用波动率作为风险代理
        # 高碳企业面临更大的转型风险
        returns = price.pct_change()
        volatility = returns.rolling(window=window).std()

        # 低波动 + 正收益 = 可能是低碳企业
        carbon_proxy = -(long_term_return / (volatility + 1e-8))

        return carbon_proxy.fillna(0).clip(-5, 5)

    def employee_satisfaction(
        self,
        data: pd.DataFrame,
        satisfaction_col: str = "employee_satisfaction",
        price_col: str = "close",
        window: int = 60,
    ) -> pd.Series:
        """计算员工满意度

        白皮书依据: 第四章 4.1.10 员工满意度

        员工满意度高的公司通常有更好的生产力和创新能力。

        Args:
            data: 市场数据
            satisfaction_col: 员工满意度列名
            price_col: 价格列名
            window: 计算窗口

        Returns:
            员工满意度指数
        """
        if data.empty or price_col not in data.columns:
            return pd.Series(0, index=data.index)

        # 如果有员工满意度数据
        if satisfaction_col in data.columns:
            satisfaction = data[satisfaction_col]
            satisfaction_trend = satisfaction.rolling(window=window).mean()
            return satisfaction_trend

        # 如果没有满意度数据，使用公司稳定性作为代理
        price = data[price_col]

        # 1. 价格稳定性（满意度高的公司通常更稳定）
        returns = price.pct_change()
        volatility = returns.rolling(window=window).std()
        stability = 1 / (volatility + 1e-8)
        stability_norm = (stability - stability.rolling(window=window * 2).mean()) / (
            stability.rolling(window=window * 2).std() + 1e-8
        )

        # 2. 长期增长（满意度高的公司长期表现好）
        long_term_growth = price.pct_change(window)

        # 综合满意度代理
        satisfaction_proxy = stability_norm * 0.5 + long_term_growth * 0.5

        return satisfaction_proxy.fillna(0).clip(-3, 3)

    def board_diversity_score(
        self, data: pd.DataFrame, diversity_col: str = "board_diversity", price_col: str = "close", window: int = 252
    ) -> pd.Series:
        """计算董事会多样性

        白皮书依据: 第四章 4.1.10 董事会多样性

        董事会多样性（性别、种族、背景）与公司治理质量正相关。

        Args:
            data: 市场数据
            diversity_col: 董事会多样性列名
            price_col: 价格列名
            window: 计算窗口

        Returns:
            董事会多样性评分
        """
        if data.empty or price_col not in data.columns:
            return pd.Series(0, index=data.index)

        # 如果有董事会多样性数据
        if diversity_col in data.columns:
            diversity = data[diversity_col]
            diversity_score = diversity.rolling(window=window).mean()
            return diversity_score

        # 如果没有多样性数据，使用治理质量代理
        price = data[price_col]

        # 治理质量好的公司特征：
        # 1. 长期稳定增长
        long_term_return = price.pct_change(window)

        # 2. 低波动率
        returns = price.pct_change()
        volatility = returns.rolling(window=window).std()
        low_vol_score = -volatility / (volatility.rolling(window=window * 2).mean() + 1e-8)

        # 3. 正向动量
        momentum = price.pct_change(window // 4)

        # 综合治理质量代理
        governance_proxy = long_term_return * 0.4 + low_vol_score * 0.3 + momentum * 0.3

        return governance_proxy.fillna(0).clip(-3, 3)

    def green_investment_ratio(
        self,
        data: pd.DataFrame,
        green_investment_col: str = "green_investment",
        price_col: str = "close",
        window: int = 252,
    ) -> pd.Series:
        """计算绿色投资比例

        白皮书依据: 第四章 4.1.10 绿色投资比例

        绿色投资比例反映公司对可持续发展的承诺。

        Args:
            data: 市场数据
            green_investment_col: 绿色投资列名
            price_col: 价格列名
            window: 计算窗口

        Returns:
            绿色投资比例
        """
        if data.empty or price_col not in data.columns:
            return pd.Series(0, index=data.index)

        # 如果有绿色投资数据
        if green_investment_col in data.columns:
            green_investment = data[green_investment_col]
            investment_ratio = green_investment.rolling(window=window).mean()
            return investment_ratio

        # 如果没有绿色投资数据，使用研发投入作为代理
        # 创新型公司通常更注重可持续发展
        price = data[price_col]

        # 使用价格增长 + 低波动作为创新代理
        returns = price.pct_change()
        avg_return = returns.rolling(window=window).mean()
        volatility = returns.rolling(window=window).std()

        # 高收益低波动 = 可能是创新型/绿色企业
        innovation_proxy = avg_return / (volatility + 1e-8)

        return innovation_proxy.fillna(0).clip(-5, 5)

    def esg_momentum(
        self, data: pd.DataFrame, esg_score_col: str = "esg_score", price_col: str = "close", window: int = 252
    ) -> pd.Series:
        """计算ESG改善动量

        白皮书依据: 第四章 4.1.10 ESG改善动量

        ESG改善动量衡量公司ESG评分的改善速度，持续改善的公司更有投资价值。

        Args:
            data: 市场数据
            esg_score_col: ESG评分列名
            price_col: 价格列名
            window: 计算窗口

        Returns:
            ESG改善动量 (正值=改善，负值=恶化)
        """
        if data.empty or price_col not in data.columns:
            return pd.Series(0, index=data.index)

        # 如果有ESG评分数据
        if esg_score_col in data.columns:
            esg_score = data[esg_score_col]
            # 计算ESG评分变化率
            esg_change = esg_score.diff()
            # 计算改善动量（加速度）
            esg_momentum = esg_change.diff()
            # 平滑处理
            esg_momentum_smooth = esg_momentum.rolling(window=window).mean()
            return esg_momentum_smooth

        # 如果没有ESG数据，使用价格动量 + 稳定性作为代理
        # ESG改善的公司通常有稳定的正向动量
        price = data[price_col]

        # 1. 价格动量
        momentum = price.pct_change(window // 4)

        # 2. 动量加速度（改善速度）
        momentum_acceleration = momentum.diff()

        # 3. 稳定性（ESG好的公司更稳定）
        returns = price.pct_change()
        volatility = returns.rolling(window=window).std()
        stability = 1 / (volatility + 1e-8)

        # 综合ESG改善动量代理
        esg_momentum_proxy = (
            momentum_acceleration * 0.5 + (stability - stability.rolling(window=window * 2).mean()) * 0.5
        )

        return esg_momentum_proxy.fillna(0).clip(-3, 3)

    def sustainability_score(
        self,
        data: pd.DataFrame,
        sustainability_col: str = "sustainability_score",
        price_col: str = "close",
        window: int = 252,
    ) -> pd.Series:
        """计算可持续性评分

        白皮书依据: 第四章 4.1.10 可持续性评分

        可持续性评分综合评估公司的长期可持续发展能力。

        Args:
            data: 市场数据
            sustainability_col: 可持续性评分列名
            price_col: 价格列名
            window: 计算窗口

        Returns:
            可持续性评分
        """
        if data.empty or price_col not in data.columns:
            return pd.Series(0, index=data.index)

        # 如果有可持续性评分数据
        if sustainability_col in data.columns:
            sustainability = data[sustainability_col]
            sustainability_avg = sustainability.rolling(window=window).mean()
            return sustainability_avg

        # 如果没有可持续性数据，使用多维度代理
        price = data[price_col]
        returns = price.pct_change()

        # 1. 长期稳定增长（可持续性核心）
        long_term_return = price.pct_change(window)

        # 2. 低波动率（稳定性）
        volatility = returns.rolling(window=window).std()
        low_vol_score = -volatility / (volatility.rolling(window=window * 2).mean() + 1e-8)

        # 3. 正向趋势（持续性）
        trend = price.rolling(window=window).apply(
            lambda x: np.polyfit(range(len(x)), x, 1)[0] if len(x) > 1 else 0, raw=True
        )
        trend_norm = trend / (price.rolling(window=window).mean() + 1e-8)

        # 4. 回撤控制（风险管理）
        cumulative_return = (1 + returns).cumprod()
        running_max = cumulative_return.rolling(window=window, min_periods=1).max()
        drawdown = (cumulative_return - running_max) / (running_max + 1e-8)
        max_drawdown = drawdown.rolling(window=window).min()
        drawdown_control = -max_drawdown  # 转换为正向指标

        # 综合可持续性评分
        sustainability_proxy = (
            long_term_return * 0.3 + low_vol_score * 0.25 + trend_norm * 0.25 + drawdown_control * 0.2
        )

        return sustainability_proxy.fillna(0).clip(-3, 3)

    def esg_risk_premium(
        self, data: pd.DataFrame, esg_score_col: str = "esg_score", price_col: str = "close", window: int = 252
    ) -> pd.Series:
        """计算ESG风险溢价

        白皮书依据: 第四章 4.1.10 ESG风险溢价

        ESG风险溢价衡量ESG评分对预期收益的影响，高ESG评分可能带来溢价或折价。

        Args:
            data: 市场数据
            esg_score_col: ESG评分列名
            price_col: 价格列名
            window: 计算窗口

        Returns:
            ESG风险溢价
        """
        if data.empty or price_col not in data.columns:
            return pd.Series(0, index=data.index)

        # 如果有ESG评分数据
        if esg_score_col in data.columns:
            esg_score = data[esg_score_col]
            price = data[price_col]
            returns = price.pct_change()

            # 计算ESG评分与收益的关系
            # 使用滚动窗口计算相关性
            def rolling_corr(x, y, window):
                """计算滚动相关性"""
                result = pd.Series(index=x.index, dtype=float)
                for i in range(window, len(x)):
                    x_window = x.iloc[i - window : i]
                    y_window = y.iloc[i - window : i]
                    if len(x_window) > 1 and x_window.std() > 0 and y_window.std() > 0:
                        result.iloc[i] = x_window.corr(y_window)
                return result

            esg_return_corr = rolling_corr(returns, esg_score, window)

            # 计算超额收益（相对于市场）
            market_return = returns.rolling(window=window).mean()
            excess_return = returns - market_return

            # ESG风险溢价 = ESG相关性 * 超额收益
            esg_premium = esg_return_corr * excess_return

            return esg_premium.rolling(window=window).mean().fillna(0)

        # 如果没有ESG数据，使用质量因子作为代理
        # 高质量公司通常有更好的ESG表现
        price = data[price_col]
        returns = price.pct_change()

        # 1. 收益质量（稳定性）
        return_quality = returns.rolling(window=window).mean() / (returns.rolling(window=window).std() + 1e-8)

        # 2. 下行风险保护
        downside_returns = returns.clip(upper=0)
        downside_risk = downside_returns.rolling(window=window).std()
        downside_protection = -downside_risk / (returns.rolling(window=window).std() + 1e-8)

        # 3. 尾部风险
        returns_sorted = returns.rolling(window=window).apply(
            lambda x: np.percentile(x, 5) if len(x) > 0 else 0, raw=True
        )
        tail_risk = -returns_sorted

        # 综合ESG风险溢价代理
        esg_premium_proxy = return_quality * 0.4 + downside_protection * 0.3 + tail_risk * 0.3

        return esg_premium_proxy.fillna(0).clip(-3, 3)
