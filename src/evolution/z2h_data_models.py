"""Z2H认证系统数据模型

白皮书依据: 第四章 4.3.2 Z2H基因胶囊认证系统

本模块定义了Z2H认证系统v2.0的核心数据模型，包括：
- Z2HGeneCapsule v2.0: 完整的策略元数据和认证信息
- CertificationLevel: 认证等级枚举
- CertificationStatus: 认证状态枚举
- CapitalTier: 资金档位枚举
- CertificationEligibility: 认证资格评估结果
- CapitalAllocationRules: 资金配置规则
- SimulationResult: 模拟盘验证结果
- TierSimulationResult: 单档位模拟结果
- CertificationResult: 认证结果
- CertifiedStrategy: 已认证策略
"""

import json
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class CertificationLevel(Enum):
    """认证等级

    白皮书依据: 第四章 4.3.2 认证等级评定标准

    三级认证体系：
    - PLATINUM（白金级）: Arena≥0.90, 所有层级优秀
    - GOLD（黄金级）: Arena≥0.80, 所有层级良好
    - SILVER（白银级）: Arena≥0.75, 所有层级合格
    """

    PLATINUM = "platinum"  # 白金级
    GOLD = "gold"  # 黄金级
    SILVER = "silver"  # 白银级
    NONE = "none"  # 未认证


class CertificationStatus(Enum):
    """认证状态

    白皮书依据: 第四章 4.3.2 认证状态管理

    认证状态流转：
    NOT_CERTIFIED → IN_PROGRESS → CERTIFIED
                                 ↓
                          DOWNGRADED / REVOKED
    """

    NOT_CERTIFIED = "not_certified"  # 未认证
    IN_PROGRESS = "in_progress"  # 认证中
    CERTIFIED = "certified"  # 已认证
    REVOKED = "revoked"  # 已撤销
    DOWNGRADED = "downgraded"  # 已降级


class CapitalTier(Enum):
    """资金档位

    白皮书依据: 第四章 4.3.1 四档资金分层测试

    四个资金档位：
    - TIER_1: 微型（1千-1万）
    - TIER_2: 小型（1万-5万）
    - TIER_3: 中型（5万-50万）
    - TIER_4: 大型（50万-500万）
    """

    TIER_1 = "tier_1"  # 微型（1千-1万）
    TIER_2 = "tier_2"  # 小型（1万-5万）
    TIER_3 = "tier_3"  # 中型（5万-50万）
    TIER_4 = "tier_4"  # 大型（50万-500万）


@dataclass
class Z2HGeneCapsule:  # pylint: disable=too-many-instance-attributes
    """Z2H基因胶囊 v2.0

    白皮书依据: 第四章 4.3.2 Z2H基因胶囊

    包含策略的完整元数据和认证信息，是策略的"身份证"和"履历表"。

    Attributes:
        strategy_id: 策略唯一标识
        strategy_name: 策略名称
        strategy_type: 策略类型（如momentum, mean_reversion等）
        source_factors: 源因子列表
        creation_date: 策略创建日期
        certification_date: 认证颁发日期
        certification_level: 认证等级
        arena_overall_score: Arena综合评分
        arena_layer_results: Arena四层验证详细结果
        arena_passed_layers: Arena通过的层数
        arena_failed_layers: Arena失败的层级列表
        simulation_duration_days: 模拟盘验证天数
        simulation_tier_results: 模拟盘各档位结果
        simulation_best_tier: 模拟盘最佳档位
        simulation_metrics: 模拟盘综合指标
        max_allocation_ratio: 最大资金配置比例
        recommended_capital_scale: 推荐资金规模
        optimal_trade_size: 最优交易规模
        liquidity_requirements: 流动性需求
        market_impact_analysis: 市场冲击分析
        avg_holding_period_days: 平均持仓天数
        turnover_rate: 换手率
        avg_position_count: 平均持仓数量
        sector_distribution: 行业分布
        market_cap_preference: 市值偏好
        var_95: 95% VaR
        expected_shortfall: 预期损失
        max_drawdown: 最大回撤
        drawdown_duration_days: 回撤持续天数
        volatility: 波动率
        beta: Beta系数
        market_correlation: 市场相关性
        bull_market_performance: 牛市表现
        bear_market_performance: 熊市表现
        sideways_market_performance: 震荡市表现
        high_volatility_performance: 高波动市场表现
        low_volatility_performance: 低波动市场表现
        market_adaptability_score: 市场适应性评分
        optimal_deployment_timing: 最优部署时机
        risk_management_rules: 风险管理规则
        monitoring_indicators: 监控指标
        exit_conditions: 退出条件
        portfolio_strategy_suggestions: 组合策略建议
        version: 版本号
        created_by: 创建者
    """

    # 基本信息
    strategy_id: str
    strategy_name: str
    strategy_type: str
    source_factors: List[str]
    creation_date: datetime
    certification_date: datetime
    certification_level: CertificationLevel

    # Arena验证结果
    arena_overall_score: float
    arena_layer_results: Dict[str, Dict[str, Any]]
    arena_passed_layers: int
    arena_failed_layers: List[str]

    # 模拟盘验证结果
    simulation_duration_days: int
    simulation_tier_results: Dict[str, Dict[str, Any]]
    simulation_best_tier: CapitalTier
    simulation_metrics: Dict[str, float]

    # 资金配置规则
    max_allocation_ratio: float
    recommended_capital_scale: Dict[str, float]
    optimal_trade_size: float
    liquidity_requirements: Dict[str, Any]
    market_impact_analysis: Dict[str, Any]

    # 交易特征
    avg_holding_period_days: float
    turnover_rate: float
    avg_position_count: int
    sector_distribution: Dict[str, float]
    market_cap_preference: str

    # 风险分析
    var_95: float
    expected_shortfall: float
    max_drawdown: float
    drawdown_duration_days: int
    volatility: float
    beta: float
    market_correlation: float

    # 市场环境表现
    bull_market_performance: Dict[str, float]
    bear_market_performance: Dict[str, float]
    sideways_market_performance: Dict[str, float]
    high_volatility_performance: Dict[str, float]
    low_volatility_performance: Dict[str, float]
    market_adaptability_score: float

    # 使用建议
    optimal_deployment_timing: List[str]
    risk_management_rules: Dict[str, Any]
    monitoring_indicators: List[str]
    exit_conditions: List[str]
    portfolio_strategy_suggestions: List[str]

    # 元数据
    version: str = "2.0"
    created_by: str = "Z2HCertificationV2"

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典

        白皮书依据: Requirement 16.1

        将Z2H基因胶囊序列化为字典，支持JSON序列化。
        处理特殊类型：datetime, Enum等。

        Returns:
            Dict[str, Any]: 字典表示
        """
        return {
            # 基本信息
            "strategy_id": self.strategy_id,
            "strategy_name": self.strategy_name,
            "strategy_type": self.strategy_type,
            "source_factors": self.source_factors,
            "creation_date": self.creation_date.isoformat(),
            "certification_date": self.certification_date.isoformat(),
            "certification_level": self.certification_level.value,
            # Arena验证结果
            "arena_overall_score": self.arena_overall_score,
            "arena_layer_results": self.arena_layer_results,
            "arena_passed_layers": self.arena_passed_layers,
            "arena_failed_layers": self.arena_failed_layers,
            # 模拟盘验证结果
            "simulation_duration_days": self.simulation_duration_days,
            "simulation_tier_results": self.simulation_tier_results,
            "simulation_best_tier": self.simulation_best_tier.value,
            "simulation_metrics": self.simulation_metrics,
            # 资金配置规则
            "max_allocation_ratio": self.max_allocation_ratio,
            "recommended_capital_scale": self.recommended_capital_scale,
            "optimal_trade_size": self.optimal_trade_size,
            "liquidity_requirements": self.liquidity_requirements,
            "market_impact_analysis": self.market_impact_analysis,
            # 交易特征
            "avg_holding_period_days": self.avg_holding_period_days,
            "turnover_rate": self.turnover_rate,
            "avg_position_count": self.avg_position_count,
            "sector_distribution": self.sector_distribution,
            "market_cap_preference": self.market_cap_preference,
            # 风险分析
            "var_95": self.var_95,
            "expected_shortfall": self.expected_shortfall,
            "max_drawdown": self.max_drawdown,
            "drawdown_duration_days": self.drawdown_duration_days,
            "volatility": self.volatility,
            "beta": self.beta,
            "market_correlation": self.market_correlation,
            # 市场环境表现
            "bull_market_performance": self.bull_market_performance,
            "bear_market_performance": self.bear_market_performance,
            "sideways_market_performance": self.sideways_market_performance,
            "high_volatility_performance": self.high_volatility_performance,
            "low_volatility_performance": self.low_volatility_performance,
            "market_adaptability_score": self.market_adaptability_score,
            # 使用建议
            "optimal_deployment_timing": self.optimal_deployment_timing,
            "risk_management_rules": self.risk_management_rules,
            "monitoring_indicators": self.monitoring_indicators,
            "exit_conditions": self.exit_conditions,
            "portfolio_strategy_suggestions": self.portfolio_strategy_suggestions,
            # 元数据
            "version": self.version,
            "created_by": self.created_by,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Z2HGeneCapsule":
        """从字典创建

        白皮书依据: Requirement 16.2

        从字典反序列化创建Z2H基因胶囊对象。
        处理特殊类型：datetime, Enum等。

        Args:
            data: 字典数据

        Returns:
            Z2HGeneCapsule: 基因胶囊对象

        Raises:
            ValueError: 当数据格式不正确时
        """
        try:
            return cls(
                # 基本信息
                strategy_id=data["strategy_id"],
                strategy_name=data["strategy_name"],
                strategy_type=data["strategy_type"],
                source_factors=data["source_factors"],
                creation_date=datetime.fromisoformat(data["creation_date"]),
                certification_date=datetime.fromisoformat(data["certification_date"]),
                certification_level=CertificationLevel(data["certification_level"]),
                # Arena验证结果
                arena_overall_score=data["arena_overall_score"],
                arena_layer_results=data["arena_layer_results"],
                arena_passed_layers=data["arena_passed_layers"],
                arena_failed_layers=data["arena_failed_layers"],
                # 模拟盘验证结果
                simulation_duration_days=data["simulation_duration_days"],
                simulation_tier_results=data["simulation_tier_results"],
                simulation_best_tier=CapitalTier(data["simulation_best_tier"]),
                simulation_metrics=data["simulation_metrics"],
                # 资金配置规则
                max_allocation_ratio=data["max_allocation_ratio"],
                recommended_capital_scale=data["recommended_capital_scale"],
                optimal_trade_size=data["optimal_trade_size"],
                liquidity_requirements=data["liquidity_requirements"],
                market_impact_analysis=data["market_impact_analysis"],
                # 交易特征
                avg_holding_period_days=data["avg_holding_period_days"],
                turnover_rate=data["turnover_rate"],
                avg_position_count=data["avg_position_count"],
                sector_distribution=data["sector_distribution"],
                market_cap_preference=data["market_cap_preference"],
                # 风险分析
                var_95=data["var_95"],
                expected_shortfall=data["expected_shortfall"],
                max_drawdown=data["max_drawdown"],
                drawdown_duration_days=data["drawdown_duration_days"],
                volatility=data["volatility"],
                beta=data["beta"],
                market_correlation=data["market_correlation"],
                # 市场环境表现
                bull_market_performance=data["bull_market_performance"],
                bear_market_performance=data["bear_market_performance"],
                sideways_market_performance=data["sideways_market_performance"],
                high_volatility_performance=data["high_volatility_performance"],
                low_volatility_performance=data["low_volatility_performance"],
                market_adaptability_score=data["market_adaptability_score"],
                # 使用建议
                optimal_deployment_timing=data["optimal_deployment_timing"],
                risk_management_rules=data["risk_management_rules"],
                monitoring_indicators=data["monitoring_indicators"],
                exit_conditions=data["exit_conditions"],
                portfolio_strategy_suggestions=data["portfolio_strategy_suggestions"],
                # 元数据
                version=data.get("version", "2.0"),
                created_by=data.get("created_by", "Z2HCertificationV2"),
            )
        except KeyError as e:
            raise ValueError(f"缺少必需字段: {e}") from e
        except (ValueError, TypeError) as e:
            raise ValueError(f"数据格式不正确: {e}") from e

    def to_json(self) -> str:
        """转换为JSON字符串

        白皮书依据: Requirement 16.1

        将Z2H基因胶囊序列化为JSON字符串。

        Returns:
            str: JSON字符串

        Raises:
            ValueError: 当序列化失败时
        """
        try:
            data = self.to_dict()
            return json.dumps(data, ensure_ascii=False, indent=2)
        except (TypeError, ValueError) as e:
            raise ValueError(f"JSON序列化失败: {e}") from e

    @classmethod
    def from_json(cls, json_str: str) -> "Z2HGeneCapsule":
        """从JSON字符串创建

        白皮书依据: Requirement 16.2

        从JSON字符串反序列化创建Z2H基因胶囊对象。

        Args:
            json_str: JSON字符串

        Returns:
            Z2HGeneCapsule: 基因胶囊对象

        Raises:
            ValueError: 当反序列化失败时
        """
        try:
            data = json.loads(json_str)
            return cls.from_dict(data)
        except json.JSONDecodeError as e:
            raise ValueError(f"JSON解析失败: {e}") from e
        except ValueError as e:
            raise ValueError(f"JSON反序列化失败: {e}") from e

    def validate(self) -> bool:  # pylint: disable=too-many-branches
        """验证基因胶囊数据的有效性

        白皮书依据: Requirement 16.3

        验证基因胶囊的所有字段是否符合要求。

        Returns:
            bool: 是否有效

        Raises:
            ValueError: 当数据无效时，包含详细的错误信息
        """
        errors = []

        # 验证基本信息
        if not self.strategy_id or not isinstance(self.strategy_id, str):
            errors.append("strategy_id必须是非空字符串")

        if not self.strategy_name or not isinstance(self.strategy_name, str):
            errors.append("strategy_name必须是非空字符串")

        if not self.strategy_type or not isinstance(self.strategy_type, str):
            errors.append("strategy_type必须是非空字符串")

        if not self.source_factors or not isinstance(self.source_factors, list):
            errors.append("source_factors必须是非空列表")

        # 验证日期
        if not isinstance(self.creation_date, datetime):
            errors.append("creation_date必须是datetime对象")

        if not isinstance(self.certification_date, datetime):
            errors.append("certification_date必须是datetime对象")

        # 只有当两个日期都是datetime时才比较
        if isinstance(self.creation_date, datetime) and isinstance(self.certification_date, datetime):
            if self.certification_date < self.creation_date:
                errors.append("certification_date不能早于creation_date")

        # 验证认证等级
        if not isinstance(self.certification_level, CertificationLevel):
            errors.append("certification_level必须是CertificationLevel枚举")

        # 验证Arena评分
        if not 0.0 <= self.arena_overall_score <= 1.0:
            errors.append("arena_overall_score必须在[0.0, 1.0]范围内")

        if not 0 <= self.arena_passed_layers <= 4:
            errors.append("arena_passed_layers必须在[0, 4]范围内")

        # 验证模拟盘结果
        if self.simulation_duration_days <= 0:
            errors.append("simulation_duration_days必须大于0")

        if not isinstance(self.simulation_best_tier, CapitalTier):
            errors.append("simulation_best_tier必须是CapitalTier枚举")

        # 验证资金配置规则
        if not 0.0 <= self.max_allocation_ratio <= 1.0:
            errors.append("max_allocation_ratio必须在[0.0, 1.0]范围内")

        if self.optimal_trade_size <= 0:
            errors.append("optimal_trade_size必须大于0")

        # 验证交易特征
        if self.avg_holding_period_days <= 0:
            errors.append("avg_holding_period_days必须大于0")

        if self.turnover_rate < 0:
            errors.append("turnover_rate不能为负数")

        if self.avg_position_count <= 0:
            errors.append("avg_position_count必须大于0")

        # 验证风险指标
        if not 0.0 <= self.var_95 <= 1.0:
            errors.append("var_95必须在[0.0, 1.0]范围内")

        if not 0.0 <= self.expected_shortfall <= 1.0:
            errors.append("expected_shortfall必须在[0.0, 1.0]范围内")

        if not 0.0 <= self.max_drawdown <= 1.0:
            errors.append("max_drawdown必须在[0.0, 1.0]范围内")

        if self.drawdown_duration_days < 0:
            errors.append("drawdown_duration_days不能为负数")

        if self.volatility < 0:
            errors.append("volatility不能为负数")

        # 验证市场适应性评分
        if not 0.0 <= self.market_adaptability_score <= 1.0:
            errors.append("market_adaptability_score必须在[0.0, 1.0]范围内")

        # 如果有错误，抛出异常
        if errors:
            raise ValueError(
                f"基因胶囊验证失败:\n" + "\n".join(f"- {error}" for error in errors)  # pylint: disable=w1309
            )  # pylint: disable=w1309

        return True


@dataclass
class CertificationEligibility:
    """认证资格评估结果

    白皮书依据: Requirement 1.1

    评估策略是否符合认证条件，包括Arena验证和模拟盘验证的综合评估。

    Attributes:
        eligible: 是否符合认证条件
        certification_level: 认证等级
        arena_score: Arena综合评分
        simulation_score: 模拟盘综合评分
        passed_criteria: 通过的标准列表
        failed_criteria: 未通过的标准列表
        failure_reasons: 失败原因列表
    """

    eligible: bool
    certification_level: CertificationLevel
    arena_score: float
    simulation_score: float
    passed_criteria: List[str]
    failed_criteria: List[str]
    failure_reasons: List[str]


@dataclass
class CapitalAllocationRules:
    """资金配置规则

    白皮书依据: Requirement 5.1-5.8

    根据认证等级和验证结果确定的资金配置规则。

    Attributes:
        max_allocation_ratio: 最大资金配置比例
        min_capital: 最小资金规模
        max_capital: 最大资金规模
        optimal_capital: 最优资金规模
        recommended_tier: 推荐资金档位
        position_limit_per_stock: 单股仓位限制
        sector_exposure_limit: 行业敞口限制
        max_leverage: 最大杠杆倍数
        liquidity_buffer: 流动性缓冲
    """

    max_allocation_ratio: float
    min_capital: float
    max_capital: float
    optimal_capital: float
    recommended_tier: CapitalTier
    position_limit_per_stock: float
    sector_exposure_limit: float
    max_leverage: float
    liquidity_buffer: float


@dataclass
class TierSimulationResult:
    """单档位模拟结果

    白皮书依据: Requirement 6.2

    单个资金档位的模拟盘验证结果。

    Attributes:
        tier: 资金档位
        initial_capital: 初始资金
        final_capital: 最终资金
        total_return: 总收益率
        sharpe_ratio: 夏普比率
        max_drawdown: 最大回撤
        win_rate: 胜率
        profit_factor: 盈利因子
        var_95: 95% VaR
        calmar_ratio: 卡玛比率
        information_ratio: 信息比率
        daily_pnl: 每日盈亏列表
        trades: 交易记录列表
    """

    tier: CapitalTier
    initial_capital: float
    final_capital: float
    total_return: float
    sharpe_ratio: float
    max_drawdown: float
    win_rate: float
    profit_factor: float
    var_95: float
    calmar_ratio: float
    information_ratio: float
    daily_pnl: List[float]
    trades: List[Dict[str, Any]]


@dataclass
class SimulationResult:
    """模拟盘验证结果

    白皮书依据: Requirement 6.1-6.8

    完整的模拟盘验证结果，包括四个档位的测试结果。

    Attributes:
        passed: 是否通过验证
        duration_days: 验证天数
        tier_results: 各档位结果
        best_tier: 最佳档位
        overall_metrics: 综合指标
        risk_metrics: 风险指标
        market_environment_performance: 市场环境表现
        passed_criteria_count: 通过的标准数量
        failed_criteria: 未通过的标准列表
    """

    passed: bool
    duration_days: int
    tier_results: Dict[str, TierSimulationResult]
    best_tier: CapitalTier
    overall_metrics: Dict[str, float]
    risk_metrics: Dict[str, float]
    market_environment_performance: Dict[str, Dict[str, float]]
    passed_criteria_count: int
    failed_criteria: List[str]


@dataclass
class CertificationResult:
    """认证结果

    白皮书依据: Requirement 2.7-2.8

    完整认证流程的最终结果。

    Attributes:
        passed: 是否通过认证
        strategy_id: 策略ID
        certification_level: 认证等级
        gene_capsule: Z2H基因胶囊
        failed_stage: 失败的阶段
        failure_reason: 失败原因
        certification_date: 认证日期
    """

    passed: bool
    strategy_id: str
    certification_level: Optional[CertificationLevel]
    gene_capsule: Optional[Z2HGeneCapsule]
    failed_stage: Optional[str]
    failure_reason: Optional[str]
    certification_date: Optional[datetime]


@dataclass
class CertifiedStrategy:
    """已认证策略

    白皮书依据: Requirement 7.1-7.7

    已获得Z2H认证的策略信息。

    Attributes:
        strategy_id: 策略ID
        strategy_name: 策略名称
        certification_level: 认证等级
        gene_capsule: Z2H基因胶囊
        certification_date: 认证日期
        status: 认证状态
        last_review_date: 最后复核日期
        next_review_date: 下次复核日期
    """

    strategy_id: str
    strategy_name: str
    certification_level: CertificationLevel
    gene_capsule: Z2HGeneCapsule
    certification_date: datetime
    status: CertificationStatus
    last_review_date: Optional[datetime] = None
    next_review_date: Optional[datetime] = None


# ============================================================================
# Arena验证结果序列化支持
# ============================================================================


def serialize_arena_result(arena_result: Any) -> Dict[str, Any]:
    """序列化Arena验证结果

    白皮书依据: Requirement 17.1

    将ArenaTestResult对象序列化为字典，支持嵌套对象。

    Args:
        arena_result: Arena测试结果对象

    Returns:
        Dict[str, Any]: 序列化后的字典

    Raises:
        ValueError: 当序列化失败时
    """
    try:
        # 检查是否有to_dict方法
        if hasattr(arena_result, "to_dict"):
            return arena_result.to_dict()

        # 如果是dataclass，使用asdict
        from dataclasses import asdict, is_dataclass  # pylint: disable=import-outside-toplevel

        if is_dataclass(arena_result):
            data = asdict(arena_result)

            # 处理特殊类型
            return _process_arena_dict(data)

        # 如果是字典，直接返回
        if isinstance(arena_result, dict):
            return _process_arena_dict(arena_result)

        raise ValueError(f"不支持的Arena结果类型: {type(arena_result)}")

    except Exception as e:
        raise ValueError(f"Arena结果序列化失败: {e}") from e


def deserialize_arena_result(data: Dict[str, Any], result_class: type = None) -> Any:
    """反序列化Arena验证结果

    白皮书依据: Requirement 17.2

    从字典反序列化创建ArenaTestResult对象。

    Args:
        data: 字典数据
        result_class: 结果类（可选）

    Returns:
        Arena测试结果对象

    Raises:
        ValueError: 当反序列化失败时
    """
    try:
        # 处理特殊类型
        processed_data = _restore_arena_dict(data)

        # 如果提供了类，使用from_dict或直接构造
        if result_class is not None:
            if hasattr(result_class, "from_dict"):  # pylint: disable=no-else-return
                return result_class.from_dict(processed_data)
            else:
                return result_class(**processed_data)

        # 否则返回字典
        return processed_data

    except Exception as e:
        raise ValueError(f"Arena结果反序列化失败: {e}") from e


def _process_arena_dict(data: Dict[str, Any]) -> Dict[str, Any]:
    """处理Arena字典中的特殊类型

    将datetime、Enum等特殊类型转换为可序列化的格式。

    Args:
        data: 原始字典

    Returns:
        处理后的字典
    """
    result = {}

    for key, value in data.items():
        if isinstance(value, datetime):
            result[key] = value.isoformat()
        elif isinstance(value, Enum):
            result[key] = value.value
        elif isinstance(value, dict):
            result[key] = _process_arena_dict(value)
        elif isinstance(value, list):
            result[key] = [_process_arena_dict(item) if isinstance(item, dict) else item for item in value]
        elif hasattr(value, "__dict__"):
            # 处理嵌套对象
            from dataclasses import asdict, is_dataclass  # pylint: disable=import-outside-toplevel

            if is_dataclass(value):
                result[key] = _process_arena_dict(asdict(value))
            else:
                result[key] = _process_arena_dict(vars(value))
        else:
            result[key] = value

    return result


def _restore_arena_dict(data: Dict[str, Any]) -> Dict[str, Any]:
    """恢复Arena字典中的特殊类型

    将序列化的格式转换回原始类型（尽可能）。

    Args:
        data: 序列化的字典

    Returns:
        恢复后的字典
    """
    result = {}

    for key, value in data.items():
        if isinstance(value, str):
            # 尝试解析为datetime
            if "T" in value and len(value) >= 19:  # ISO格式
                try:
                    result[key] = datetime.fromisoformat(value)
                    continue
                except (ValueError, AttributeError):
                    pass
            result[key] = value
        elif isinstance(value, dict):
            result[key] = _restore_arena_dict(value)
        elif isinstance(value, list):
            result[key] = [_restore_arena_dict(item) if isinstance(item, dict) else item for item in value]
        else:
            result[key] = value

    return result


def arena_result_to_json(arena_result: Any) -> str:
    """将Arena结果转换为JSON字符串

    白皮书依据: Requirement 17.1

    Args:
        arena_result: Arena测试结果对象

    Returns:
        str: JSON字符串

    Raises:
        ValueError: 当转换失败时
    """
    try:
        data = serialize_arena_result(arena_result)
        return json.dumps(data, ensure_ascii=False, indent=2)
    except Exception as e:
        raise ValueError(f"Arena结果JSON序列化失败: {e}") from e


def arena_result_from_json(json_str: str, result_class: type = None) -> Any:
    """从JSON字符串创建Arena结果

    白皮书依据: Requirement 17.2

    Args:
        json_str: JSON字符串
        result_class: 结果类（可选）

    Returns:
        Arena测试结果对象

    Raises:
        ValueError: 当转换失败时
    """
    try:
        data = json.loads(json_str)
        return deserialize_arena_result(data, result_class)
    except json.JSONDecodeError as e:
        raise ValueError(f"JSON解析失败: {e}") from e
    except Exception as e:
        raise ValueError(f"Arena结果JSON反序列化失败: {e}") from e
