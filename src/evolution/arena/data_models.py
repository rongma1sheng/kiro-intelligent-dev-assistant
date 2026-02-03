"""
因子Arena数据模型 (Factor Arena Data Models)

白皮书依据: 第四章 4.2.1 因子Arena三轨测试系统
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional


class MarketType(Enum):
    """市场类型"""

    A_STOCK = "a_stock"  # A股市场
    US_STOCK = "us_stock"  # 美股市场
    CRYPTO = "crypto"  # 加密货币市场
    HK_STOCK = "hk_stock"  # 港股市场


class ExtremeScenarioType(Enum):
    """极端场景类型"""

    CRASH = "crash"  # 崩盘场景
    FLASH_CRASH = "flash_crash"  # 闪崩场景
    LIQUIDITY_CRISIS = "liquidity_crisis"  # 流动性危机
    VOLATILITY_SPIKE = "volatility_spike"  # 波动率飙升
    CORRELATION_BREAKDOWN = "correlation_breakdown"  # 相关性崩溃


@dataclass
class Factor:
    """因子数据模型

    白皮书依据: 第四章 4.1 暗物质挖掘工厂

    Attributes:
        id: 因子唯一标识
        name: 因子名称
        description: 因子描述
        expression: 因子表达式
        category: 因子类别 (technical, fundamental, alternative_data, etc.)
        created_at: 创建时间
        arena_tested: 是否已通过Arena测试
        arena_score: Arena综合评分 [0, 1]
    """

    id: str
    name: str
    description: str
    expression: str
    category: str
    created_at: datetime = field(default_factory=datetime.now)
    arena_tested: bool = False
    arena_score: Optional[float] = None

    def __post_init__(self):
        """验证数据有效性

        白皮书依据: MIA编码铁律4 - 完整的类型注解和验证
        """
        if not self.id:
            raise ValueError("因子ID不能为空")
        if not self.name:
            raise ValueError("因子名称不能为空")
        if not self.expression:
            raise ValueError("因子表达式不能为空")
        if self.arena_score is not None:
            if not 0 <= self.arena_score <= 1:
                raise ValueError(f"Arena评分必须在[0, 1]范围内，当前值: {self.arena_score}")


@dataclass
class RealityTrackResult:
    """Reality Track测试结果

    白皮书依据: 第四章 4.2.1 因子Arena - Reality Track

    Attributes:
        ic: 信息系数 (Information Coefficient)
        ir: 信息比率 (Information Ratio)
        sharpe_ratio: 夏普比率
        annual_return: 年化收益率
        max_drawdown: 最大回撤
        win_rate: 胜率
        reality_score: Reality Track综合评分 [0, 1]
        test_period_days: 测试周期天数
        sample_count: 样本数量
    """

    ic: float
    ir: float
    sharpe_ratio: float
    annual_return: float
    max_drawdown: float
    win_rate: float
    reality_score: float
    test_period_days: int
    sample_count: int

    def __post_init__(self):
        """验证数据有效性"""
        if not 0 <= self.reality_score <= 1:
            raise ValueError(f"Reality评分必须在[0, 1]范围内，当前值: {self.reality_score}")
        if not 0 <= self.win_rate <= 1:
            raise ValueError(f"胜率必须在[0, 1]范围内，当前值: {self.win_rate}")
        if self.test_period_days <= 0:
            raise ValueError(f"测试周期必须大于0，当前值: {self.test_period_days}")
        if self.sample_count <= 0:
            raise ValueError(f"样本数量必须大于0，当前值: {self.sample_count}")


@dataclass
class HellTrackResult:
    """Hell Track测试结果

    白皮书依据: 第四章 4.2.1 因子Arena - Hell Track

    Attributes:
        survival_rate: 存活率 [0, 1]
        crash_performance: 崩盘场景表现
        flash_crash_performance: 闪崩场景表现
        liquidity_crisis_performance: 流动性危机表现
        volatility_spike_performance: 波动率飙升表现
        correlation_breakdown_performance: 相关性崩溃表现
        hell_score: Hell Track综合评分 [0, 1]
        scenarios_tested: 测试的场景数量
    """

    survival_rate: float
    crash_performance: float
    flash_crash_performance: float
    liquidity_crisis_performance: float
    volatility_spike_performance: float
    correlation_breakdown_performance: float
    hell_score: float
    scenarios_tested: int

    def __post_init__(self):
        """验证数据有效性"""
        if not 0 <= self.survival_rate <= 1:
            raise ValueError(f"存活率必须在[0, 1]范围内，当前值: {self.survival_rate}")
        if not 0 <= self.hell_score <= 1:
            raise ValueError(f"Hell评分必须在[0, 1]范围内，当前值: {self.hell_score}")
        if self.scenarios_tested <= 0:
            raise ValueError(f"测试场景数量必须大于0，当前值: {self.scenarios_tested}")


@dataclass
class CrossMarketResult:
    """Cross-Market Track测试结果

    白皮书依据: 第四章 4.2.1 因子Arena - Cross-Market Track

    Attributes:
        a_stock_score: A股市场评分
        us_stock_score: 美股市场评分
        crypto_score: 加密货币市场评分
        hk_stock_score: 港股市场评分
        adaptability_score: 跨市场适应性评分 [0, 1]
        cross_market_score: Cross-Market Track综合评分 [0, 1]
        markets_tested: 测试的市场数量
    """

    a_stock_score: float
    us_stock_score: float
    crypto_score: float
    hk_stock_score: float
    adaptability_score: float
    cross_market_score: float
    markets_tested: int

    def __post_init__(self):
        """验证数据有效性"""
        if not 0 <= self.adaptability_score <= 1:
            raise ValueError(f"适应性评分必须在[0, 1]范围内，当前值: {self.adaptability_score}")
        if not 0 <= self.cross_market_score <= 1:
            raise ValueError(f"Cross-Market评分必须在[0, 1]范围内，当前值: {self.cross_market_score}")
        if self.markets_tested <= 0:
            raise ValueError(f"测试市场数量必须大于0，当前值: {self.markets_tested}")


@dataclass
class FactorTestResult:
    """因子测试结果

    白皮书依据: 第四章 4.2.1 因子Arena三轨测试系统

    Attributes:
        factor_id: 因子ID
        reality_result: Reality Track测试结果
        hell_result: Hell Track测试结果
        cross_market_result: Cross-Market Track测试结果
        overall_score: 综合评分 [0, 1]
        passed: 是否通过Arena测试
        test_timestamp: 测试时间戳
        detailed_metrics: 详细指标
    """

    factor_id: str
    reality_result: RealityTrackResult
    hell_result: HellTrackResult
    cross_market_result: CrossMarketResult
    overall_score: float
    passed: bool
    test_timestamp: datetime = field(default_factory=datetime.now)
    detailed_metrics: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """验证数据有效性"""
        if not self.factor_id:
            raise ValueError("因子ID不能为空")
        if not 0 <= self.overall_score <= 1:
            raise ValueError(f"综合评分必须在[0, 1]范围内，当前值: {self.overall_score}")

        # 验证子结果对象
        if not isinstance(self.reality_result, RealityTrackResult):
            raise TypeError("reality_result必须是RealityTrackResult类型")
        if not isinstance(self.hell_result, HellTrackResult):
            raise TypeError("hell_result必须是HellTrackResult类型")
        if not isinstance(self.cross_market_result, CrossMarketResult):
            raise TypeError("cross_market_result必须是CrossMarketResult类型")
