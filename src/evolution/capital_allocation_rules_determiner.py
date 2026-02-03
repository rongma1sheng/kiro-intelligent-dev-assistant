"""资金配置规则确定器

白皮书依据: 第四章 4.3.2 资金配置规则确定

本模块实现资金配置规则确定器，根据认证等级和Arena测试结果自动确定策略的资金配置规则。
"""

from dataclasses import dataclass
from typing import Any, Dict, Optional

from loguru import logger

from .z2h_data_models import CapitalAllocationRules, CapitalTier, CertificationLevel


@dataclass
class LiquidityAnalysis:
    """流动性分析结果

    Attributes:
        avg_daily_volume: 平均日成交量
        liquidity_score: 流动性评分（0-1）
        max_position_size: 最大持仓规模
        recommended_max_capital: 推荐最大资金
    """

    avg_daily_volume: float
    liquidity_score: float
    max_position_size: float
    recommended_max_capital: float


@dataclass
class MarketImpactAnalysis:
    """市场冲击分析结果

    Attributes:
        estimated_impact: 预估市场冲击（百分比）
        optimal_order_size: 最优订单规模
        max_order_size: 最大订单规模
        recommended_split_count: 推荐拆单数量
    """

    estimated_impact: float
    optimal_order_size: float
    max_order_size: float
    recommended_split_count: int


class CapitalAllocationRulesDeterminer:
    """资金配置规则确定器

    白皮书依据: 第四章 4.3.2 资金配置规则确定

    根据认证等级和Arena测试结果自动确定策略的资金配置规则。

    资金配置比例标准：
    - PLATINUM（白金级）: 最大20%
    - GOLD（黄金级）: 最大15%
    - SILVER（白银级）: 最大10%

    Attributes:
        platinum_ratio: 白金级最大配置比例，默认0.20
        gold_ratio: 黄金级最大配置比例，默认0.15
        silver_ratio: 白银级最大配置比例，默认0.10
        tier_capital_ranges: 各档位资金范围
    """

    # 各档位资金范围（元）
    TIER_CAPITAL_RANGES = {
        CapitalTier.TIER_1: (1000, 10000),  # 微型：1千-1万
        CapitalTier.TIER_2: (10000, 50000),  # 小型：1万-5万
        CapitalTier.TIER_3: (50000, 500000),  # 中型：5万-50万
        CapitalTier.TIER_4: (500000, 5000000),  # 大型：50万-500万
    }

    def __init__(self, platinum_ratio: float = 0.20, gold_ratio: float = 0.15, silver_ratio: float = 0.10):
        """初始化资金配置规则确定器

        Args:
            platinum_ratio: 白金级最大配置比例，范围[0, 1]
            gold_ratio: 黄金级最大配置比例，范围[0, 1]
            silver_ratio: 白银级最大配置比例，范围[0, 1]

        Raises:
            ValueError: 当配置比例不在有效范围或顺序不正确时
        """
        # 验证配置比例范围
        if not 0.0 <= platinum_ratio <= 1.0:
            raise ValueError(f"白金级配置比例必须在[0, 1]范围内: {platinum_ratio}")

        if not 0.0 <= gold_ratio <= 1.0:
            raise ValueError(f"黄金级配置比例必须在[0, 1]范围内: {gold_ratio}")

        if not 0.0 <= silver_ratio <= 1.0:
            raise ValueError(f"白银级配置比例必须在[0, 1]范围内: {silver_ratio}")

        # 验证配置比例顺序
        if not (platinum_ratio >= gold_ratio >= silver_ratio):  # pylint: disable=superfluous-parens
            raise ValueError(
                f"配置比例顺序必须满足: platinum >= gold >= silver, "
                f"当前: {platinum_ratio} >= {gold_ratio} >= {silver_ratio}"
            )

        self.platinum_ratio = platinum_ratio
        self.gold_ratio = gold_ratio
        self.silver_ratio = silver_ratio

        logger.info(
            f"初始化CapitalAllocationRulesDeterminer: "
            f"PLATINUM={platinum_ratio*100}%, GOLD={gold_ratio*100}%, SILVER={silver_ratio*100}%"
        )

    def determine_rules(
        self,
        certification_level: CertificationLevel,
        best_tier: CapitalTier,
        simulation_metrics: Dict[str, float],
        strategy_characteristics: Optional[Dict[str, Any]] = None,
    ) -> CapitalAllocationRules:
        """确定资金配置规则

        白皮书依据: Requirement 5.1-5.8

        根据认证等级、最佳档位和模拟盘指标确定完整的资金配置规则。

        Args:
            certification_level: 认证等级
            best_tier: 最佳资金档位
            simulation_metrics: 模拟盘综合指标
            strategy_characteristics: 策略特征（可选）

        Returns:
            CapitalAllocationRules: 资金配置规则

        Raises:
            ValueError: 当输入参数无效时
        """
        # 验证输入
        if certification_level == CertificationLevel.NONE:
            raise ValueError("未认证策略不能确定资金配置规则")

        if not simulation_metrics:
            raise ValueError("模拟盘指标不能为空")

        logger.info(f"开始确定资金配置规则 - 认证等级: {certification_level.value}, " f"最佳档位: {best_tier.value}")

        # 1. 根据认证等级确定基础配置比例
        max_allocation_ratio = self._get_max_allocation_ratio(certification_level)

        # 2. 确定最优资金规模
        optimal_capital = self._determine_optimal_capital_scale(best_tier, simulation_metrics)

        # 3. 分析流动性需求
        liquidity_analysis = self._analyze_liquidity_requirements(simulation_metrics, strategy_characteristics)

        # 4. 分析市场冲击
        market_impact_analysis = self._analyze_market_impact(  # pylint: disable=unused-variable
            simulation_metrics, strategy_characteristics
        )  # pylint: disable=unused-variable

        # 5. 确定资金范围
        min_capital, max_capital = self.TIER_CAPITAL_RANGES[best_tier]

        # 根据流动性分析调整最大资金
        max_capital = min(max_capital, liquidity_analysis.recommended_max_capital)

        # 6. 确定仓位限制
        position_limit_per_stock = self._calculate_position_limit(certification_level, simulation_metrics)

        # 7. 确定行业敞口限制
        sector_exposure_limit = self._calculate_sector_exposure_limit(certification_level)

        # 8. 确定最大杠杆
        max_leverage = self._calculate_max_leverage(certification_level)

        # 9. 确定流动性缓冲
        liquidity_buffer = self._calculate_liquidity_buffer(certification_level, liquidity_analysis)

        rules = CapitalAllocationRules(
            max_allocation_ratio=max_allocation_ratio,
            min_capital=min_capital,
            max_capital=max_capital,
            optimal_capital=optimal_capital,
            recommended_tier=best_tier,
            position_limit_per_stock=position_limit_per_stock,
            sector_exposure_limit=sector_exposure_limit,
            max_leverage=max_leverage,
            liquidity_buffer=liquidity_buffer,
        )

        logger.info(
            f"资金配置规则确定完成 - "
            f"最大配置比例: {max_allocation_ratio*100}%, "
            f"最优资金: {optimal_capital:.0f}, "
            f"资金范围: [{min_capital:.0f}, {max_capital:.0f}]"
        )

        return rules

    def _get_max_allocation_ratio(self, certification_level: CertificationLevel) -> float:
        """获取最大配置比例

        白皮书依据: Requirement 5.1-5.4

        根据认证等级返回对应的最大资金配置比例。

        Args:
            certification_level: 认证等级

        Returns:
            float: 最大配置比例
        """
        if certification_level == CertificationLevel.PLATINUM:  # pylint: disable=no-else-return
            return self.platinum_ratio
        elif certification_level == CertificationLevel.GOLD:
            return self.gold_ratio
        elif certification_level == CertificationLevel.SILVER:
            return self.silver_ratio
        else:
            return 0.0

    def _determine_optimal_capital_scale(self, best_tier: CapitalTier, simulation_metrics: Dict[str, float]) -> float:
        """确定最优资金规模

        白皮书依据: Requirement 5.5

        根据最佳档位和模拟盘表现确定最优资金规模。

        Args:
            best_tier: 最佳资金档位
            simulation_metrics: 模拟盘综合指标

        Returns:
            float: 最优资金规模
        """
        # 获取档位资金范围
        min_capital, max_capital = self.TIER_CAPITAL_RANGES[best_tier]

        # 提取关键指标
        sharpe_ratio = simulation_metrics.get("sharpe_ratio", 1.0)
        max_drawdown = simulation_metrics.get("max_drawdown", 0.2)
        win_rate = simulation_metrics.get("win_rate", 0.5)

        # 计算性能评分（0-1）
        performance_score = self._calculate_performance_score(sharpe_ratio, max_drawdown, win_rate)

        # 根据性能评分在档位范围内插值
        # 性能越好，推荐资金越接近上限
        optimal_capital = min_capital + (max_capital - min_capital) * performance_score

        return optimal_capital

    def _analyze_liquidity_requirements(
        self,
        simulation_metrics: Dict[str, float],  # pylint: disable=unused-argument
        strategy_characteristics: Optional[Dict[str, Any]],  # pylint: disable=unused-argument
    ) -> LiquidityAnalysis:
        """分析流动性需求

        白皮书依据: Requirement 5.6

        分析策略的流动性需求，确定最大资金规模。

        Args:
            simulation_metrics: 模拟盘综合指标
            strategy_characteristics: 策略特征

        Returns:
            LiquidityAnalysis: 流动性分析结果
        """
        # 提取策略特征
        if strategy_characteristics:
            avg_position_count = strategy_characteristics.get("avg_position_count", 10)
            avg_holding_period = strategy_characteristics.get("avg_holding_period_days", 5)
            turnover_rate = strategy_characteristics.get("turnover_rate", 2.0)
        else:
            avg_position_count = 10
            avg_holding_period = 5
            turnover_rate = 2.0

        # 估算平均日成交量需求（简化模型）
        # 假设每个持仓需要日均成交量的1%
        avg_daily_volume = avg_position_count * 1000000  # 简化：每个持仓100万日均成交量

        # 计算流动性评分
        # 持仓期越长、换手率越低，流动性要求越低，评分越高
        liquidity_score = min(1.0, (avg_holding_period / 10) * (2.0 / max(turnover_rate, 0.1)))

        # 计算最大持仓规模
        # 一般不超过日均成交量的5%
        max_position_size = avg_daily_volume * 0.05

        # 计算推荐最大资金
        # 基于持仓数量和单个持仓规模
        recommended_max_capital = max_position_size * avg_position_count

        return LiquidityAnalysis(
            avg_daily_volume=avg_daily_volume,
            liquidity_score=liquidity_score,
            max_position_size=max_position_size,
            recommended_max_capital=recommended_max_capital,
        )

    def _analyze_market_impact(
        self,
        simulation_metrics: Dict[str, float],  # pylint: disable=unused-argument
        strategy_characteristics: Optional[Dict[str, Any]],  # pylint: disable=unused-argument
    ) -> MarketImpactAnalysis:
        """分析市场冲击

        白皮书依据: Requirement 5.7

        分析策略交易对市场的冲击，确定最优交易规模。

        Args:
            simulation_metrics: 模拟盘综合指标
            strategy_characteristics: 策略特征

        Returns:
            MarketImpactAnalysis: 市场冲击分析结果
        """
        # 提取策略特征
        if strategy_characteristics:
            avg_position_count = strategy_characteristics.get("avg_position_count", 10)
            turnover_rate = strategy_characteristics.get("turnover_rate", 2.0)
        else:
            avg_position_count = 10
            turnover_rate = 2.0

        # 估算市场冲击（简化模型）
        # 换手率越高，市场冲击越大
        estimated_impact = min(0.01, turnover_rate * 0.001)  # 最大1%

        # 计算最优订单规模
        # 一般为持仓规模的10-20%
        optimal_order_size = 100000  # 简化：10万元

        # 计算最大订单规模
        # 一般为持仓规模的50%
        max_order_size = 500000  # 简化：50万元

        # 计算推荐拆单数量
        # 根据换手率和持仓数量
        recommended_split_count = max(1, int(turnover_rate * avg_position_count / 5))

        return MarketImpactAnalysis(
            estimated_impact=estimated_impact,
            optimal_order_size=optimal_order_size,
            max_order_size=max_order_size,
            recommended_split_count=recommended_split_count,
        )

    def _calculate_performance_score(self, sharpe_ratio: float, max_drawdown: float, win_rate: float) -> float:
        """计算性能评分

        综合夏普比率、最大回撤和胜率计算性能评分。

        Args:
            sharpe_ratio: 夏普比率
            max_drawdown: 最大回撤
            win_rate: 胜率

        Returns:
            float: 性能评分（0-1）
        """
        # 夏普比率评分（0-1）
        # 夏普比率>2.0为优秀
        sharpe_score = min(1.0, max(0.0, sharpe_ratio / 2.0))

        # 回撤评分（0-1）
        # 回撤<10%为优秀
        drawdown_score = max(0.0, 1.0 - max_drawdown / 0.1)

        # 胜率评分（0-1）
        # 胜率>60%为优秀
        win_rate_score = min(1.0, max(0.0, (win_rate - 0.4) / 0.2))

        # 综合评分（加权平均）
        performance_score = sharpe_score * 0.4 + drawdown_score * 0.4 + win_rate_score * 0.2

        return performance_score

    def _calculate_position_limit(
        self, certification_level: CertificationLevel, simulation_metrics: Dict[str, float]
    ) -> float:
        """计算单股仓位限制

        根据认证等级和风险指标确定单股仓位限制。

        Args:
            certification_level: 认证等级
            simulation_metrics: 模拟盘综合指标

        Returns:
            float: 单股仓位限制（比例）
        """
        # 基础仓位限制
        if certification_level == CertificationLevel.PLATINUM:
            base_limit = 0.10  # 10%
        elif certification_level == CertificationLevel.GOLD:
            base_limit = 0.08  # 8%
        else:  # SILVER
            base_limit = 0.05  # 5%

        # 根据波动率调整
        volatility = simulation_metrics.get("volatility", 0.2)
        if volatility > 0.3:
            base_limit *= 0.8  # 高波动降低仓位

        return base_limit

    def _calculate_sector_exposure_limit(self, certification_level: CertificationLevel) -> float:
        """计算行业敞口限制

        根据认证等级确定行业敞口限制。

        Args:
            certification_level: 认证等级

        Returns:
            float: 行业敞口限制（比例）
        """
        if certification_level == CertificationLevel.PLATINUM:  # pylint: disable=no-else-return
            return 0.30  # 30%
        elif certification_level == CertificationLevel.GOLD:
            return 0.25  # 25%
        else:  # SILVER
            return 0.20  # 20%

    def _calculate_max_leverage(self, certification_level: CertificationLevel) -> float:
        """计算最大杠杆倍数

        根据认证等级确定最大杠杆倍数。

        Args:
            certification_level: 认证等级

        Returns:
            float: 最大杠杆倍数
        """
        if certification_level == CertificationLevel.PLATINUM:  # pylint: disable=no-else-return
            return 2.0  # 2倍
        elif certification_level == CertificationLevel.GOLD:
            return 1.5  # 1.5倍
        else:  # SILVER
            return 1.0  # 不允许杠杆

    def _calculate_liquidity_buffer(
        self, certification_level: CertificationLevel, liquidity_analysis: LiquidityAnalysis
    ) -> float:
        """计算流动性缓冲

        根据认证等级和流动性分析确定流动性缓冲。

        Args:
            certification_level: 认证等级
            liquidity_analysis: 流动性分析结果

        Returns:
            float: 流动性缓冲（比例）
        """
        # 基础缓冲
        if certification_level == CertificationLevel.PLATINUM:
            base_buffer = 0.10  # 10%
        elif certification_level == CertificationLevel.GOLD:
            base_buffer = 0.15  # 15%
        else:  # SILVER
            base_buffer = 0.20  # 20%

        # 根据流动性评分调整
        # 流动性越好，缓冲可以越小
        adjusted_buffer = base_buffer * (1.0 - liquidity_analysis.liquidity_score * 0.3)

        return adjusted_buffer
