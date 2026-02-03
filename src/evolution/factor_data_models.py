"""因子系统核心数据模型

白皮书依据: 第四章 4.1-4.3 斯巴达进化与生态

本模块定义了因子发现、验证、策略生成和认证流程中使用的核心数据模型，包括：
- Factor: 遗传算法发现的量化因子
- ValidatedFactor: 通过Arena三轨测试的验证因子
- CandidateStrategy: 从验证因子生成的候选策略
- ArenaTestResult: Arena测试结果
- FactorExpression: 因子数学表达式
- RiskFactor: 失败因子转换的风险信号
- RiskLimits: 动态风险控制参数
- PerformanceMetrics: 实时性能指标
- SimulationResult: 模拟盘验证结果
- SimulationMetrics: 模拟盘综合指标
- DailyResult: 每日模拟结果
- TradeableStrategy: 可交易策略配置
- Z2HCertifiedStrategy: Z2H认证策略

铁律1: 白皮书至上 - 所有数据模型严格遵循白皮书第四章定义
铁律2: 禁止简化和占位符 - 所有字段必须完整定义
铁律4: 完整的类型注解 - 所有字段都有明确的类型注解
铁律5: 完整的文档字符串 - 所有类都有完整的docstring
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

import pandas as pd

# ============================================================================
# 核心因子数据模型
# ============================================================================


@dataclass
class Factor:
    """遗传算法发现的量化因子

    白皮书依据: 第四章 4.1 暗物质挖掘工厂

    通过遗传算法自动发现的量化因子，包含完整的元数据和性能指标。

    Attributes:
        id: 因子唯一标识
        name: 因子名称
        expression: 数学表达式字符串
        category: 因子类别（technical, volume_price, statistical等）
        implementation_code: Python实现代码
        created_at: 创建时间
        generation: 发现时的遗传算法代数
        fitness_score: 遗传算法适应度评分
        baseline_ic: 初始信息系数
        baseline_ir: 初始信息比率
        baseline_sharpe: 初始夏普比率
        liquidity_adaptability: 流动性适应性评分
    """

    id: str
    name: str
    expression: str
    category: str
    implementation_code: str
    created_at: datetime
    generation: int
    fitness_score: float
    baseline_ic: float
    baseline_ir: float
    baseline_sharpe: float
    liquidity_adaptability: float


@dataclass
class ValidatedFactor:
    """通过Arena三轨测试的验证因子

    白皮书依据: 第四章 4.2.1 因子Arena三轨测试系统

    通过Reality Track、Hell Track和Cross-Market Track三轨测试的因子，
    具备进入策略生成阶段的资格。

    Attributes:
        factor: 原始因子对象
        arena_score: Arena综合评分（0.0-1.0）
        reality_score: Reality Track IC评分
        hell_score: Hell Track生存率评分
        cross_market_score: Cross-Market适应性评分
        markets_passed: 通过测试的市场数量
        z2h_eligible: 是否符合Z2H认证路径资格
        validation_date: 验证日期
        reality_result: Reality Track详细结果
        hell_result: Hell Track详细结果
        cross_market_result: Cross-Market Track详细结果
    """

    factor: Factor
    arena_score: float
    reality_score: float
    hell_score: float
    cross_market_score: float
    markets_passed: int
    z2h_eligible: bool
    validation_date: datetime
    reality_result: Dict[str, Any]
    hell_result: Dict[str, Any]
    cross_market_result: Dict[str, Any]


@dataclass
class CandidateStrategy:
    """从验证因子生成的候选策略

    白皮书依据: 第四章 4.2.2 因子组合策略生成与斯巴达考核

    从Arena验证因子生成的候选交易策略，等待斯巴达Arena考核。

    Attributes:
        id: 策略唯一标识
        name: 策略名称
        strategy_type: 策略类型（pure_factor, factor_combo, market_neutral等）
        source_factors: 源因子列表
        code: 生成的策略代码
        expected_sharpe: 预期夏普比率
        max_drawdown_limit: 最大允许回撤
        capital_allocation: 推荐资金配置
        rebalance_frequency: 再平衡频率（天数）
        status: 状态（candidate, arena_testing, simulation, certified, rejected）
        arena_scheduled: 是否已安排Arena测试
        simulation_required: 是否需要模拟盘验证
        z2h_eligible: 是否符合Z2H认证资格
        created_at: 创建时间
    """

    id: str
    name: str
    strategy_type: str
    source_factors: List[Factor]
    code: str
    expected_sharpe: float
    max_drawdown_limit: float
    capital_allocation: float
    rebalance_frequency: int
    status: str
    arena_scheduled: bool
    simulation_required: bool
    z2h_eligible: bool
    created_at: datetime


@dataclass
class ArenaTestResult:
    """Arena测试结果（因子或策略）

    白皮书依据: 第四章 4.2.1-4.2.2 Arena测试系统

    因子Arena或斯巴达Arena的测试结果，包含完整的评分和详细指标。

    Attributes:
        test_type: 测试类型（'factor'或'strategy'）
        subject_id: 测试对象ID（因子ID或策略ID）
        arena_score: Arena综合评分（0.0-1.0）
        reality_result: Reality Track结果
        hell_result: Hell Track结果
        cross_market_result: Cross-Market Track结果（仅因子）
        passed: 是否通过测试
        next_stage: 下一阶段名称
        test_timestamp: 测试时间戳
        detailed_metrics: 所有详细指标
    """

    test_type: str
    subject_id: str
    arena_score: float
    reality_result: Dict[str, Any]
    hell_result: Dict[str, Any]
    cross_market_result: Optional[Dict[str, Any]]
    passed: bool
    next_stage: str
    test_timestamp: datetime
    detailed_metrics: Dict[str, Any]


# ============================================================================
# 因子表达式和风险模型
# ============================================================================


@dataclass
class FactorExpression:
    """因子数学表达式

    白皮书依据: 第四章 4.1 因子表达式系统

    表示因子的数学表达式，包含验证和评估功能。

    Attributes:
        expression_string: 表达式字符串（如"rank(close/shift(close,20))"）
        operators_used: 使用的算子列表
        complexity: 表达式复杂度评分
        depth: 嵌套深度
        parameters: 可配置参数
    """

    expression_string: str
    operators_used: List[str]
    complexity: int
    depth: int
    parameters: Dict[str, Any]

    def evaluate(self, market_data: pd.DataFrame) -> pd.Series:
        """在市场数据上评估表达式

        白皮书依据: 第四章 4.1 因子计算

        Args:
            market_data: 市场数据DataFrame

        Returns:
            因子值序列

        Raises:
            ValueError: 当表达式无效或数据不足时
        """
        raise NotImplementedError("FactorExpression.evaluate需要在子类中实现")

    def simplify(self) -> "FactorExpression":
        """简化表达式

        白皮书依据: 第四章 4.1 表达式优化

        Returns:
            简化后的表达式
        """
        raise NotImplementedError("FactorExpression.simplify需要在子类中实现")

    def validate(self) -> bool:
        """验证表达式语法和算子

        白皮书依据: 第四章 4.1 表达式验证

        Returns:
            是否有效

        Raises:
            ValueError: 当表达式无效时，包含详细错误信息
        """
        raise NotImplementedError("FactorExpression.validate需要在子类中实现")


@dataclass
class RiskFactor:
    """失败因子转换的风险信号

    白皮书依据: 第四章 4.1 因子生命周期管理

    当因子性能退化时，转换为风险信号用于风险控制。

    Attributes:
        original_factor_id: 原始因子ID
        original_expression: 原始表达式
        risk_signal_expression: 风险信号表达式（反转或修改）
        risk_type: 风险类型（correlation_flip, factor_decay, performance_mutation等）
        sensitivity: 风险信号敏感度（0.0-1.0）
        created_at: 创建时间
        conversion_reason: 转换原因
        baseline_metrics: 失败前的原始因子指标
    """

    original_factor_id: str
    original_expression: str
    risk_signal_expression: str
    risk_type: str
    sensitivity: float
    created_at: datetime
    conversion_reason: str
    baseline_metrics: Dict[str, Any]


@dataclass
class RiskLimits:
    """动态风险控制参数

    白皮书依据: 第四章 4.3.2 风险控制参数

    根据Arena测试和模拟盘结果生成的动态风险限制。

    Attributes:
        max_position_size: 最大单仓位规模
        max_portfolio_concentration: 最大组合集中度
        max_drawdown_threshold: 最大回撤阈值（超过则停止交易）
        max_daily_loss: 最大日损失限制
        min_liquidity_rank: 最小流动性要求
        max_leverage: 最大杠杆倍数
        rebalance_frequency: 再平衡频率（天数）
        stop_loss_percentage: 单仓位止损百分比
    """

    max_position_size: float
    max_portfolio_concentration: float
    max_drawdown_threshold: float
    max_daily_loss: float
    min_liquidity_rank: float
    max_leverage: float
    rebalance_frequency: int
    stop_loss_percentage: float


# ============================================================================
# 性能监控数据模型
# ============================================================================


@dataclass
class PerformanceMetrics:
    """实时性能指标

    白皮书依据: 第四章 4.1 因子性能监控

    因子或策略的实时性能指标，用于监控和健康评估。

    Attributes:
        timestamp: 时间戳
        ic_1d: 1日IC
        ic_5d: 5日IC
        ic_10d: 10日IC
        ic_20d: 20日IC
        ir: 信息比率
        sharpe_ratio: 夏普比率
        turnover_rate: 换手率
        health_score: 健康评分（综合指标）
        correlation_with_market: 与市场相关性
        liquidity_score: 流动性评分
    """

    timestamp: datetime
    ic_1d: float
    ic_5d: float
    ic_10d: float
    ic_20d: float
    ir: float
    sharpe_ratio: float
    turnover_rate: float
    health_score: float
    correlation_with_market: float
    liquidity_score: float


# ============================================================================
# 模拟盘验证数据模型
# ============================================================================


@dataclass
class DailyResult:
    """每日模拟结果

    白皮书依据: 第四章 4.2.2 模拟盘验证

    模拟盘每日交易结果和性能指标。

    Attributes:
        date: 日期
        capital: 当日资金
        pnl: 当日盈亏
        return_rate: 当日收益率
        drawdown: 当日回撤
        positions: 持仓列表
        trades: 交易记录
    """

    date: datetime
    capital: float
    pnl: float
    return_rate: float
    drawdown: float
    positions: List[Dict[str, Any]]
    trades: List[Dict[str, Any]]


@dataclass
class SimulationMetrics:
    """模拟盘综合指标

    白皮书依据: 第四章 4.2.2 模拟盘验证标准

    30天模拟盘的最终综合指标。

    Attributes:
        total_return: 总收益率
        sharpe_ratio: 夏普比率
        max_drawdown: 最大回撤
        win_rate: 胜率
        profit_factor: 盈利因子
        average_win: 平均盈利
        average_loss: 平均亏损
        total_trades: 总交易次数
        winning_trades: 盈利交易次数
        losing_trades: 亏损交易次数
    """

    total_return: float
    sharpe_ratio: float
    max_drawdown: float
    win_rate: float
    profit_factor: float
    average_win: float
    average_loss: float
    total_trades: int
    winning_trades: int
    losing_trades: int


@dataclass
class SimulationResult:
    """模拟盘验证结果

    白皮书依据: 第四章 4.2.2 模拟盘验证运行

    30天实盘模拟的完整结果，包含每日数据和最终指标。

    Attributes:
        strategy: 候选策略
        passed: 是否通过验证
        failure_reason: 失败原因（如果未通过）
        daily_results: 每日结果列表
        final_metrics: 最终综合指标
        z2h_eligible: 是否符合Z2H认证资格
        simulation_start: 模拟开始时间
        simulation_end: 模拟结束时间
    """

    strategy: CandidateStrategy
    passed: bool
    failure_reason: Optional[str]
    daily_results: List[DailyResult]
    final_metrics: SimulationMetrics
    z2h_eligible: bool
    simulation_start: datetime
    simulation_end: datetime


# ============================================================================
# 可交易策略数据模型
# ============================================================================


@dataclass
class TradeableStrategy:
    """可交易策略配置

    白皮书依据: 第四章 4.3.2 实盘交易部署

    通过Z2H认证的策略的实盘交易配置。

    Attributes:
        base_strategy: 基础候选策略
        z2h_capsule: Z2H基因胶囊（从z2h_data_models导入）
        status: 状态
        max_capital_allocation: 最大资金配置
        risk_limits: 风险限制
        live_trading_enabled: 是否启用实盘交易
        deployment_config: 部署配置
    """

    base_strategy: CandidateStrategy
    z2h_capsule: Any  # Z2HGeneCapsule from z2h_data_models
    status: str
    max_capital_allocation: float
    risk_limits: RiskLimits
    live_trading_enabled: bool
    deployment_config: Dict[str, Any]


@dataclass
class Z2HCertifiedStrategy:
    """Z2H认证策略

    白皮书依据: 第四章 4.3.2 Z2H基因胶囊认证

    完全通过Z2H认证的策略，可用于实盘交易。

    Attributes:
        tradeable_strategy: 可交易策略配置
        z2h_capsule: Z2H基因胶囊
        certification_path: 完整认证路径描述
        live_trading_enabled: 是否启用实盘交易
        deployment_date: 部署日期
        live_performance: 实盘表现（如果已部署）
        status: 状态（certified, deployed, active, retired, archived）
    """

    tradeable_strategy: TradeableStrategy
    z2h_capsule: Any  # Z2HGeneCapsule from z2h_data_models
    certification_path: str
    live_trading_enabled: bool
    deployment_date: Optional[datetime]
    live_performance: Optional[Dict[str, Any]]
    status: str
