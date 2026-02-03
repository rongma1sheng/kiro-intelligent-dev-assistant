"""
策略Arena数据模型 (Strategy Arena Data Models)

白皮书依据: 第四章 4.2.2 策略Arena双轨测试系统
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class StrategyType(Enum):
    """策略类型"""

    PURE_FACTOR = "pure_factor"  # 纯因子策略
    FACTOR_COMBO = "factor_combo"  # 因子组合策略
    MOMENTUM = "momentum"  # 动量策略
    MEAN_REVERSION = "mean_reversion"  # 均值回归策略
    ARBITRAGE = "arbitrage"  # 套利策略
    MARKET_MAKING = "market_making"  # 做市策略


class StrategyStatus(Enum):
    """策略状态"""

    CANDIDATE = "candidate"  # 候选策略
    ARENA_TESTING = "arena_testing"  # Arena测试中
    SIMULATION = "simulation"  # 模拟盘验证中
    CERTIFIED = "certified"  # Z2H认证
    ACTIVE = "active"  # 活跃交易
    MONITORING = "monitoring"  # 监控中
    DEPRECATED = "deprecated"  # 已弃用
    RETIRED = "retired"  # 已退役


class ExtremeScenarioType(Enum):
    """极端场景类型"""

    FLASH_CRASH = "flash_crash"  # 闪崩场景
    CIRCUIT_BREAKER = "circuit_breaker"  # 熔断场景
    LIQUIDITY_DROUGHT = "liquidity_drought"  # 流动性枯竭
    VOLATILITY_EXPLOSION = "volatility_explosion"  # 波动率爆炸
    BLACK_SWAN = "black_swan"  # 黑天鹅事件


@dataclass
class Strategy:
    """策略数据模型

    白皮书依据: 第四章 4.2.2 策略Arena双轨测试系统

    Attributes:
        id: 策略唯一标识
        name: 策略名称
        type: 策略类型
        source_factors: 源因子ID列表
        code: 策略实现代码
        description: 策略描述
        created_at: 创建时间
        status: 策略状态
        arena_tested: 是否已通过Arena测试
        arena_score: Arena综合评分 [0, 1]
        metadata: 策略元数据
    """

    id: str
    name: str
    type: StrategyType
    source_factors: List[str]
    code: str
    description: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    status: StrategyStatus = StrategyStatus.CANDIDATE
    arena_tested: bool = False
    arena_score: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """验证数据有效性

        白皮书依据: MIA编码铁律4 - 完整的类型注解和验证
        """
        if not self.id:
            raise ValueError("策略ID不能为空")
        if not self.name:
            raise ValueError("策略名称不能为空")
        if not self.code:
            raise ValueError("策略代码不能为空")
        if not self.source_factors:
            raise ValueError("源因子列表不能为空")
        if not isinstance(self.type, StrategyType):
            raise TypeError(f"策略类型必须是StrategyType枚举，当前类型: {type(self.type)}")
        if not isinstance(self.status, StrategyStatus):
            raise TypeError(f"策略状态必须是StrategyStatus枚举，当前类型: {type(self.status)}")
        if self.arena_score is not None:
            if not 0 <= self.arena_score <= 1:
                raise ValueError(f"Arena评分必须在[0, 1]范围内，当前值: {self.arena_score}")


@dataclass
class StrategyRealityTrackResult:
    """策略Reality Track测试结果

    白皮书依据: 第四章 4.2.2 策略Arena - Reality Track (3年历史回测)

    Attributes:
        sharpe_ratio: 夏普比率
        max_drawdown: 最大回撤
        annual_return: 年化收益率
        win_rate: 胜率
        profit_factor: 盈亏比
        calmar_ratio: 卡玛比率 (年化收益/最大回撤)
        sortino_ratio: 索提诺比率
        total_trades: 总交易次数
        avg_holding_period: 平均持仓周期(天)
        reality_score: Reality Track综合评分 [0, 1]
        test_period_days: 测试周期天数 (约1095天 = 3年)
    """

    sharpe_ratio: float
    max_drawdown: float
    annual_return: float
    win_rate: float
    profit_factor: float
    calmar_ratio: float
    sortino_ratio: float
    total_trades: int
    avg_holding_period: float
    reality_score: float
    test_period_days: int

    def __post_init__(self):
        """验证数据有效性"""
        if not 0 <= self.win_rate <= 1:
            raise ValueError(f"胜率必须在[0, 1]范围内，当前值: {self.win_rate}")
        if not 0 <= self.reality_score <= 1:
            raise ValueError(f"Reality评分必须在[0, 1]范围内，当前值: {self.reality_score}")
        if self.test_period_days <= 0:
            raise ValueError(f"测试周期必须大于0，当前值: {self.test_period_days}")
        if self.total_trades < 0:
            raise ValueError(f"总交易次数不能为负数，当前值: {self.total_trades}")
        if self.avg_holding_period < 0:
            raise ValueError(f"平均持仓周期不能为负数，当前值: {self.avg_holding_period}")
        if self.profit_factor < 0:
            raise ValueError(f"盈亏比不能为负数，当前值: {self.profit_factor}")


@dataclass
class StrategyHellTrackResult:
    """策略Hell Track测试结果

    白皮书依据: 第四章 4.2.2 策略Arena - Hell Track (极端场景压力测试)

    Attributes:
        survival_rate: 存活率 [0, 1]
        flash_crash_performance: 闪崩场景表现 [-1, 1]
        circuit_breaker_performance: 熔断场景表现 [-1, 1]
        liquidity_drought_performance: 流动性枯竭表现 [-1, 1]
        volatility_explosion_performance: 波动率爆炸表现 [-1, 1]
        black_swan_performance: 黑天鹅事件表现 [-1, 1]
        recovery_speed: 恢复速度 (天数)
        max_stress_drawdown: 压力测试最大回撤
        hell_score: Hell Track综合评分 [0, 1]
        scenarios_tested: 测试的场景数量
    """

    survival_rate: float
    flash_crash_performance: float
    circuit_breaker_performance: float
    liquidity_drought_performance: float
    volatility_explosion_performance: float
    black_swan_performance: float
    recovery_speed: float
    max_stress_drawdown: float
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
        if self.recovery_speed < 0:
            raise ValueError(f"恢复速度不能为负数，当前值: {self.recovery_speed}")

        # 验证各场景表现在合理范围内
        performances = [
            self.flash_crash_performance,
            self.circuit_breaker_performance,
            self.liquidity_drought_performance,
            self.volatility_explosion_performance,
            self.black_swan_performance,
        ]
        for perf in performances:
            if not -1 <= perf <= 1:
                raise ValueError(f"场景表现必须在[-1, 1]范围内，当前值: {perf}")


@dataclass
class StrategyTestResult:
    """策略测试结果

    白皮书依据: 第四章 4.2.2 策略Arena双轨测试系统

    Attributes:
        strategy_id: 策略ID
        reality_result: Reality Track测试结果
        hell_result: Hell Track测试结果
        overall_score: 综合评分 [0, 1]
        passed: 是否通过Arena测试
        pass_criteria_met: 通过标准是否满足
        test_timestamp: 测试时间戳
        test_duration_seconds: 测试耗时(秒)
        detailed_metrics: 详细指标
    """

    strategy_id: str
    reality_result: StrategyRealityTrackResult
    hell_result: StrategyHellTrackResult
    overall_score: float
    passed: bool
    pass_criteria_met: Dict[str, bool]
    test_timestamp: datetime = field(default_factory=datetime.now)
    test_duration_seconds: float = 0.0
    detailed_metrics: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """验证数据有效性"""
        if not self.strategy_id:
            raise ValueError("策略ID不能为空")
        if not 0 <= self.overall_score <= 1:
            raise ValueError(f"综合评分必须在[0, 1]范围内，当前值: {self.overall_score}")
        if self.test_duration_seconds < 0:
            raise ValueError(f"测试耗时不能为负数，当前值: {self.test_duration_seconds}")

        # 验证子结果对象
        if not isinstance(self.reality_result, StrategyRealityTrackResult):
            raise TypeError("reality_result必须是StrategyRealityTrackResult类型")
        if not isinstance(self.hell_result, StrategyHellTrackResult):
            raise TypeError("hell_result必须是StrategyHellTrackResult类型")

        # 验证通过标准字典
        required_criteria = ["arena_score", "sharpe_ratio", "max_drawdown"]
        for criterion in required_criteria:
            if criterion not in self.pass_criteria_met:
                raise ValueError(f"通过标准缺少必需项: {criterion}")


@dataclass
class PerformanceMetrics:
    """性能指标

    白皮书依据: 第四章 4.2.2 策略性能评估指标

    Attributes:
        sharpe_ratio: 夏普比率
        sortino_ratio: 索提诺比率
        calmar_ratio: 卡玛比率
        max_drawdown: 最大回撤
        annual_return: 年化收益率
        annual_volatility: 年化波动率
        win_rate: 胜率
        profit_factor: 盈亏比
        total_trades: 总交易次数
        avg_trade_return: 平均交易收益
    """

    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: float
    max_drawdown: float
    annual_return: float
    annual_volatility: float
    win_rate: float
    profit_factor: float
    total_trades: int
    avg_trade_return: float

    def __post_init__(self):
        """验证数据有效性"""
        if not 0 <= self.win_rate <= 1:
            raise ValueError(f"胜率必须在[0, 1]范围内，当前值: {self.win_rate}")
        if self.total_trades < 0:
            raise ValueError(f"总交易次数不能为负数，当前值: {self.total_trades}")
        if self.profit_factor < 0:
            raise ValueError(f"盈亏比不能为负数，当前值: {self.profit_factor}")
        if self.annual_volatility < 0:
            raise ValueError(f"年化波动率不能为负数，当前值: {self.annual_volatility}")
