# pylint: disable=too-many-lines
"""达尔文进化体系数据模型

白皮书依据: 第五章 5.3 达尔文进化体系集成

本模块定义了达尔文进化体系所需的所有数据模型，包括：
- Factor: 因子数据模型
- GeneCapsule: 基因胶囊数据模型
- EvolutionNode/EvolutionEdge: 演化树节点和边
- AntiPattern/FailureCase: 反向模式和失败案例
- 各种分析结果数据模型
"""

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class Z2HStampStatus(Enum):
    """Z2H钢印状态枚举

    白皮书依据: 第四章 4.3.2 Z2H基因胶囊认证系统
    """

    PENDING = "pending"  # 待认证
    PLATINUM = "platinum"  # 铂金级
    GOLD = "gold"  # 黄金级
    SILVER = "silver"  # 白银级
    REJECTED = "rejected"  # 认证失败
    EXPIRED = "expired"  # 认证过期


class MutationType(Enum):
    """变异类型枚举

    白皮书依据: 第五章 5.3.3 演化树
    """

    PARAMETER_MUTATION = "parameter_mutation"  # 参数变异
    STRUCTURE_MUTATION = "structure_mutation"  # 结构变异
    CROSSOVER = "crossover"  # 交叉
    OPTIMIZATION = "optimization"  # 优化
    INITIAL = "initial"  # 初始创建


class FailureStep(Enum):
    """失败步骤枚举

    白皮书依据: 第五章 5.3.1 进化协同流程
    """

    FACTOR_ANALYSIS = "factor_analysis"
    ACADEMIC_SEARCH = "academic_search"
    FUTURE_FUNCTION_DETECTION = "future_function_detection"
    ARENA_TEST = "arena_test"
    PERFORMANCE_ANALYSIS = "performance_analysis"
    WEAKNESS_IDENTIFICATION = "weakness_identification"
    OPTIMIZATION_SUGGESTION = "optimization_suggestion"
    PERFORMANCE_PREDICTION = "performance_prediction"
    Z2H_CERTIFICATION = "z2h_certification"
    REPORT_GENERATION = "report_generation"


@dataclass
class Factor:
    """因子数据模型

    白皮书依据: 第五章 5.3.1 进化协同流程

    Attributes:
        factor_id: 因子唯一标识
        expression: 因子表达式
        name: 因子名称
        description: 因子描述
        parameters: 因子参数配置
        created_at: 创建时间
    """

    factor_id: str
    expression: str
    name: str
    description: str
    parameters: Dict[str, Any]
    created_at: datetime

    def __post_init__(self) -> None:
        """验证因子数据完整性"""
        if not self.factor_id:
            raise ValueError("因子ID不能为空")
        if not self.expression:
            raise ValueError("因子表达式不能为空")
        if not self.name:
            raise ValueError("因子名称不能为空")

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "factor_id": self.factor_id,
            "expression": self.expression,
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Factor":
        """从字典创建因子对象"""
        return cls(
            factor_id=data["factor_id"],
            expression=data["expression"],
            name=data["name"],
            description=data["description"],
            parameters=data.get("parameters", {}),
            created_at=datetime.fromisoformat(data["created_at"]),
        )


@dataclass
class ArenaPerformance:
    """Arena表现数据模型

    白皮书依据: 第四章 4.2 Arena双轨测试

    Attributes:
        reality_track_score: 现实轨道得分
        hell_track_score: 地狱轨道得分
        cross_market_score: 跨市场得分
        sharpe_ratio: 夏普比率
        max_drawdown: 最大回撤
        win_rate: 胜率
        profit_factor: 盈利因子
        test_date: 测试日期
    """

    reality_track_score: float
    hell_track_score: float
    cross_market_score: float
    sharpe_ratio: float
    max_drawdown: float
    win_rate: float
    profit_factor: float
    test_date: datetime

    def __post_init__(self) -> None:
        """验证Arena表现数据"""
        if not 0 <= self.win_rate <= 1:
            raise ValueError(f"胜率必须在[0, 1]范围内，当前: {self.win_rate}")
        if self.max_drawdown < 0:
            raise ValueError(f"最大回撤不能为负数，当前: {self.max_drawdown}")

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "reality_track_score": self.reality_track_score,
            "hell_track_score": self.hell_track_score,
            "cross_market_score": self.cross_market_score,
            "sharpe_ratio": self.sharpe_ratio,
            "max_drawdown": self.max_drawdown,
            "win_rate": self.win_rate,
            "profit_factor": self.profit_factor,
            "test_date": self.test_date.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ArenaPerformance":
        """从字典创建Arena表现对象"""
        return cls(
            reality_track_score=data["reality_track_score"],
            hell_track_score=data["hell_track_score"],
            cross_market_score=data["cross_market_score"],
            sharpe_ratio=data["sharpe_ratio"],
            max_drawdown=data["max_drawdown"],
            win_rate=data["win_rate"],
            profit_factor=data["profit_factor"],
            test_date=datetime.fromisoformat(data["test_date"]),
        )


@dataclass
class AuditResult:
    """魔鬼审计结果数据模型

    白皮书依据: 第二章 2.5 Devil魔鬼审计

    Attributes:
        passed: 是否通过审计
        future_function_detected: 是否检测到未来函数
        issues: 发现的问题列表
        suggestions: 改进建议列表
        audit_date: 审计日期
        confidence: 审计置信度
    """

    passed: bool
    future_function_detected: bool
    issues: List[str]
    suggestions: List[str]
    audit_date: datetime
    confidence: float

    def __post_init__(self) -> None:
        """验证审计结果数据"""
        if not 0 <= self.confidence <= 1:
            raise ValueError(f"置信度必须在[0, 1]范围内，当前: {self.confidence}")

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "passed": self.passed,
            "future_function_detected": self.future_function_detected,
            "issues": self.issues,
            "suggestions": self.suggestions,
            "audit_date": self.audit_date.isoformat(),
            "confidence": self.confidence,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AuditResult":
        """从字典创建审计结果对象"""
        return cls(
            passed=data["passed"],
            future_function_detected=data["future_function_detected"],
            issues=data.get("issues", []),
            suggestions=data.get("suggestions", []),
            audit_date=datetime.fromisoformat(data["audit_date"]),
            confidence=data["confidence"],
        )


@dataclass
class EvolutionRecord:
    """进化记录数据模型

    白皮书依据: 第五章 5.3.2 基因胶囊

    Attributes:
        record_id: 记录ID
        parent_capsule_id: 父代胶囊ID
        mutation_type: 变异类型
        mutation_description: 变异描述
        fitness_before: 变异前适应度
        fitness_after: 变异后适应度
        timestamp: 时间戳
    """

    record_id: str
    parent_capsule_id: Optional[str]
    mutation_type: MutationType
    mutation_description: str
    fitness_before: float
    fitness_after: float
    timestamp: datetime

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "record_id": self.record_id,
            "parent_capsule_id": self.parent_capsule_id,
            "mutation_type": self.mutation_type.value,
            "mutation_description": self.mutation_description,
            "fitness_before": self.fitness_before,
            "fitness_after": self.fitness_after,
            "timestamp": self.timestamp.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EvolutionRecord":
        """从字典创建进化记录对象"""
        return cls(
            record_id=data["record_id"],
            parent_capsule_id=data.get("parent_capsule_id"),
            mutation_type=MutationType(data["mutation_type"]),
            mutation_description=data["mutation_description"],
            fitness_before=data["fitness_before"],
            fitness_after=data["fitness_after"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
        )


@dataclass
class GeneCapsule:
    """基因胶囊数据模型

    白皮书依据: 第五章 5.3.2 基因胶囊

    定义: 策略的完整元数据封装
    内容:
    - 策略代码
    - 参数配置
    - 29维度分析报告
    - Arena表现
    - 魔鬼审计结果
    - 进化历史
    - Z2H钢印状态

    存储: Redis + 知识库
    Key: mia:knowledge:gene_capsule:{capsule_id}
    TTL: 永久

    Attributes:
        capsule_id: 胶囊唯一标识
        strategy_code: 策略代码
        parameter_config: 参数配置
        analysis_report_29d: 29维度分析报告
        arena_performance: Arena表现
        devil_audit_result: 魔鬼审计结果
        evolution_history: 进化历史
        z2h_stamp_status: Z2H钢印状态
        family_id: 策略家族ID
        created_at: 创建时间
        updated_at: 更新时间
        version: 版本号
    """

    capsule_id: str
    strategy_code: str
    parameter_config: Dict[str, Any]
    analysis_report_29d: Dict[str, Any]
    arena_performance: ArenaPerformance
    devil_audit_result: AuditResult
    evolution_history: List[EvolutionRecord]
    z2h_stamp_status: Z2HStampStatus
    family_id: str
    created_at: datetime
    updated_at: datetime
    version: int = 1

    def __post_init__(self) -> None:
        """验证基因胶囊数据完整性"""
        if not self.capsule_id:
            raise ValueError("胶囊ID不能为空")
        if not self.strategy_code:
            raise ValueError("策略代码不能为空")
        if self.version < 1:
            raise ValueError(f"版本号必须 >= 1，当前: {self.version}")

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "capsule_id": self.capsule_id,
            "strategy_code": self.strategy_code,
            "parameter_config": self.parameter_config,
            "analysis_report_29d": self.analysis_report_29d,
            "arena_performance": self.arena_performance.to_dict(),
            "devil_audit_result": self.devil_audit_result.to_dict(),
            "evolution_history": [r.to_dict() for r in self.evolution_history],
            "z2h_stamp_status": self.z2h_stamp_status.value,
            "family_id": self.family_id,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "version": self.version,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GeneCapsule":
        """从字典创建基因胶囊对象"""
        return cls(
            capsule_id=data["capsule_id"],
            strategy_code=data["strategy_code"],
            parameter_config=data["parameter_config"],
            analysis_report_29d=data["analysis_report_29d"],
            arena_performance=ArenaPerformance.from_dict(data["arena_performance"]),
            devil_audit_result=AuditResult.from_dict(data["devil_audit_result"]),
            evolution_history=[EvolutionRecord.from_dict(r) for r in data["evolution_history"]],
            z2h_stamp_status=Z2HStampStatus(data["z2h_stamp_status"]),
            family_id=data["family_id"],
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            version=data.get("version", 1),
        )

    def serialize(self) -> str:
        """序列化为JSON字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False)

    @classmethod
    def deserialize(cls, json_str: str) -> "GeneCapsule":
        """从JSON字符串反序列化"""
        data = json.loads(json_str)
        return cls.from_dict(data)


@dataclass
class EvolutionNode:
    """演化树节点数据模型

    白皮书依据: 第五章 5.3.3 演化树

    Attributes:
        node_id: 节点ID
        capsule_id: 关联的基因胶囊ID
        strategy_name: 策略名称
        fitness: 适应度
        generation: 代数
        created_at: 创建时间
    """

    node_id: str
    capsule_id: str
    strategy_name: str
    fitness: float
    generation: int
    created_at: datetime

    def __post_init__(self) -> None:
        """验证节点数据"""
        if not self.node_id:
            raise ValueError("节点ID不能为空")
        if not self.capsule_id:
            raise ValueError("胶囊ID不能为空")
        if self.generation < 0:
            raise ValueError(f"代数不能为负数，当前: {self.generation}")

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "node_id": self.node_id,
            "capsule_id": self.capsule_id,
            "strategy_name": self.strategy_name,
            "fitness": self.fitness,
            "generation": self.generation,
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EvolutionNode":
        """从字典创建节点对象"""
        return cls(
            node_id=data["node_id"],
            capsule_id=data["capsule_id"],
            strategy_name=data["strategy_name"],
            fitness=data["fitness"],
            generation=data["generation"],
            created_at=datetime.fromisoformat(data["created_at"]),
        )


@dataclass
class EvolutionEdge:
    """演化树边数据模型

    白皮书依据: 第五章 5.3.3 演化树

    Attributes:
        edge_id: 边ID
        parent_node_id: 父节点ID
        child_node_id: 子节点ID
        mutation_type: 变异类型
        mutation_description: 变异描述
        fitness_change: 适应度变化
        created_at: 创建时间
    """

    edge_id: str
    parent_node_id: str
    child_node_id: str
    mutation_type: MutationType
    mutation_description: str
    fitness_change: float
    created_at: datetime

    def __post_init__(self) -> None:
        """验证边数据"""
        if not self.edge_id:
            raise ValueError("边ID不能为空")
        if not self.parent_node_id:
            raise ValueError("父节点ID不能为空")
        if not self.child_node_id:
            raise ValueError("子节点ID不能为空")

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "edge_id": self.edge_id,
            "parent_node_id": self.parent_node_id,
            "child_node_id": self.child_node_id,
            "mutation_type": self.mutation_type.value,
            "mutation_description": self.mutation_description,
            "fitness_change": self.fitness_change,
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EvolutionEdge":
        """从字典创建边对象"""
        return cls(
            edge_id=data["edge_id"],
            parent_node_id=data["parent_node_id"],
            child_node_id=data["child_node_id"],
            mutation_type=MutationType(data["mutation_type"]),
            mutation_description=data["mutation_description"],
            fitness_change=data["fitness_change"],
            created_at=datetime.fromisoformat(data["created_at"]),
        )


@dataclass
class FailureCase:
    """失败案例数据模型

    白皮书依据: 第五章 5.3.4 反向黑名单

    Attributes:
        case_id: 案例ID
        factor_expression: 因子表达式
        failure_reason: 失败原因
        failure_step: 失败步骤
        timestamp: 时间戳
    """

    case_id: str
    factor_expression: str
    failure_reason: str
    failure_step: FailureStep
    timestamp: datetime

    def __post_init__(self) -> None:
        """验证失败案例数据"""
        if not self.case_id:
            raise ValueError("案例ID不能为空")
        if not self.factor_expression:
            raise ValueError("因子表达式不能为空")
        if not self.failure_reason:
            raise ValueError("失败原因不能为空")

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "case_id": self.case_id,
            "factor_expression": self.factor_expression,
            "failure_reason": self.failure_reason,
            "failure_step": self.failure_step.value,
            "timestamp": self.timestamp.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FailureCase":
        """从字典创建失败案例对象"""
        return cls(
            case_id=data["case_id"],
            factor_expression=data["factor_expression"],
            failure_reason=data["failure_reason"],
            failure_step=FailureStep(data["failure_step"]),
            timestamp=datetime.fromisoformat(data["timestamp"]),
        )


@dataclass
class AntiPattern:
    """反向模式数据模型

    白皮书依据: 第五章 5.3.4 反向黑名单

    定义: 失败模式库
    内容:
    - 失败模式描述
    - 失败次数统计
    - 失败案例列表
    - 避免建议

    作用:
    - 避免重复错误
    - 指导因子挖掘
    - 提高进化效率

    Attributes:
        pattern_id: 模式ID
        description: 失败模式描述
        failure_count: 失败次数
        failure_cases: 失败案例列表
        avoidance_suggestions: 避免建议
        pattern_signature: 模式签名（用于匹配）
        created_at: 创建时间
        updated_at: 更新时间
    """

    pattern_id: str
    description: str
    failure_count: int
    failure_cases: List[FailureCase]
    avoidance_suggestions: List[str]
    pattern_signature: str
    created_at: datetime
    updated_at: datetime

    def __post_init__(self) -> None:
        """验证反向模式数据"""
        if not self.pattern_id:
            raise ValueError("模式ID不能为空")
        if not self.description:
            raise ValueError("模式描述不能为空")
        if self.failure_count < 0:
            raise ValueError(f"失败次数不能为负数，当前: {self.failure_count}")

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "pattern_id": self.pattern_id,
            "description": self.description,
            "failure_count": self.failure_count,
            "failure_cases": [c.to_dict() for c in self.failure_cases],
            "avoidance_suggestions": self.avoidance_suggestions,
            "pattern_signature": self.pattern_signature,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AntiPattern":
        """从字典创建反向模式对象"""
        return cls(
            pattern_id=data["pattern_id"],
            description=data["description"],
            failure_count=data["failure_count"],
            failure_cases=[FailureCase.from_dict(c) for c in data["failure_cases"]],
            avoidance_suggestions=data.get("avoidance_suggestions", []),
            pattern_signature=data["pattern_signature"],
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
        )

    def serialize(self) -> str:
        """序列化为JSON字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False)

    @classmethod
    def deserialize(cls, json_str: str) -> "AntiPattern":
        """从JSON字符串反序列化"""
        data = json.loads(json_str)
        return cls.from_dict(data)


@dataclass
class FactorMeaningAnalysis:
    """因子意义分析数据模型

    白皮书依据: 第五章 5.3.1 进化协同流程

    Attributes:
        factor_type: 因子类型
        economic_meaning: 经济学含义
        expected_behavior: 预期行为
        risk_factors: 风险因素列表
        confidence: 置信度
    """

    factor_type: str
    economic_meaning: str
    expected_behavior: str
    risk_factors: List[str]
    confidence: float

    def __post_init__(self) -> None:
        """验证因子意义分析数据"""
        if not 0 <= self.confidence <= 1:
            raise ValueError(f"置信度必须在[0, 1]范围内，当前: {self.confidence}")

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "factor_type": self.factor_type,
            "economic_meaning": self.economic_meaning,
            "expected_behavior": self.expected_behavior,
            "risk_factors": self.risk_factors,
            "confidence": self.confidence,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FactorMeaningAnalysis":
        """从字典创建因子意义分析对象"""
        return cls(
            factor_type=data["factor_type"],
            economic_meaning=data["economic_meaning"],
            expected_behavior=data["expected_behavior"],
            risk_factors=data.get("risk_factors", []),
            confidence=data["confidence"],
        )


@dataclass
class AcademicFactorMatch:
    """学术因子匹配数据模型

    白皮书依据: 第五章 5.3.1 进化协同流程

    Attributes:
        paper_title: 论文标题
        paper_authors: 论文作者列表
        factor_name: 因子名称
        similarity_score: 相似度得分
        paper_url: 论文URL
    """

    paper_title: str
    paper_authors: List[str]
    factor_name: str
    similarity_score: float
    paper_url: str

    def __post_init__(self) -> None:
        """验证学术因子匹配数据"""
        if not 0 <= self.similarity_score <= 1:
            raise ValueError(f"相似度得分必须在[0, 1]范围内，当前: {self.similarity_score}")

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "paper_title": self.paper_title,
            "paper_authors": self.paper_authors,
            "factor_name": self.factor_name,
            "similarity_score": self.similarity_score,
            "paper_url": self.paper_url,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AcademicFactorMatch":
        """从字典创建学术因子匹配对象"""
        return cls(
            paper_title=data["paper_title"],
            paper_authors=data.get("paper_authors", []),
            factor_name=data["factor_name"],
            similarity_score=data["similarity_score"],
            paper_url=data.get("paper_url", ""),
        )


@dataclass
class ArenaTestResult:
    """Arena测试结果数据模型

    白皮书依据: 第四章 4.2 Arena双轨测试

    Attributes:
        test_id: 测试ID
        factor_id: 因子ID
        performance: Arena表现
        passed: 是否通过测试
        test_duration_seconds: 测试耗时（秒）
        test_date: 测试日期
    """

    test_id: str
    factor_id: str
    performance: ArenaPerformance
    passed: bool
    test_duration_seconds: float
    test_date: datetime

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "test_id": self.test_id,
            "factor_id": self.factor_id,
            "performance": self.performance.to_dict(),
            "passed": self.passed,
            "test_duration_seconds": self.test_duration_seconds,
            "test_date": self.test_date.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ArenaTestResult":
        """从字典创建Arena测试结果对象"""
        return cls(
            test_id=data["test_id"],
            factor_id=data["factor_id"],
            performance=ArenaPerformance.from_dict(data["performance"]),
            passed=data["passed"],
            test_duration_seconds=data["test_duration_seconds"],
            test_date=datetime.fromisoformat(data["test_date"]),
        )


@dataclass
class PerformanceDiffAnalysis:
    """表现差异分析数据模型

    白皮书依据: 第五章 5.3.1 进化协同流程

    Attributes:
        reality_track_score: 现实轨道得分
        hell_track_score: 地狱轨道得分
        cross_market_score: 跨市场得分
        diff_summary: 差异总结
        key_differences: 关键差异列表
    """

    reality_track_score: float
    hell_track_score: float
    cross_market_score: float
    diff_summary: str
    key_differences: List[str]

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "reality_track_score": self.reality_track_score,
            "hell_track_score": self.hell_track_score,
            "cross_market_score": self.cross_market_score,
            "diff_summary": self.diff_summary,
            "key_differences": self.key_differences,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PerformanceDiffAnalysis":
        """从字典创建表现差异分析对象"""
        return cls(
            reality_track_score=data["reality_track_score"],
            hell_track_score=data["hell_track_score"],
            cross_market_score=data["cross_market_score"],
            diff_summary=data["diff_summary"],
            key_differences=data.get("key_differences", []),
        )


@dataclass
class WeaknessReport:
    """弱点报告数据模型

    白皮书依据: 第五章 5.3.1 进化协同流程

    Attributes:
        weaknesses: 弱点列表
        improvement_directions: 改进方向列表
        priority_ranking: 优先级排名列表 [(弱点, 优先级)]
    """

    weaknesses: List[str]
    improvement_directions: List[str]
    priority_ranking: List[Tuple[str, int]]

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "weaknesses": self.weaknesses,
            "improvement_directions": self.improvement_directions,
            "priority_ranking": self.priority_ranking,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WeaknessReport":
        """从字典创建弱点报告对象"""
        return cls(
            weaknesses=data.get("weaknesses", []),
            improvement_directions=data.get("improvement_directions", []),
            priority_ranking=[tuple(p) for p in data.get("priority_ranking", [])],
        )


@dataclass
class OptimizationSuggestions:
    """优化建议数据模型

    白皮书依据: 第五章 5.3.1 进化协同流程

    Attributes:
        hyperparameter_changes: 超参数变更建议
        structural_changes: 结构变更建议列表
        expected_improvement: 预期改进幅度
    """

    hyperparameter_changes: Dict[str, Any]
    structural_changes: List[str]
    expected_improvement: float

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "hyperparameter_changes": self.hyperparameter_changes,
            "structural_changes": self.structural_changes,
            "expected_improvement": self.expected_improvement,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "OptimizationSuggestions":
        """从字典创建优化建议对象"""
        return cls(
            hyperparameter_changes=data.get("hyperparameter_changes", {}),
            structural_changes=data.get("structural_changes", []),
            expected_improvement=data.get("expected_improvement", 0.0),
        )


@dataclass
class PerformancePrediction:
    """性能预测数据模型

    白皮书依据: 第五章 5.3.1 进化协同流程

    Attributes:
        predicted_sharpe: 预测夏普比率
        predicted_max_drawdown: 预测最大回撤
        predicted_win_rate: 预测胜率
        confidence_interval: 置信区间 (下限, 上限)
    """

    predicted_sharpe: float
    predicted_max_drawdown: float
    predicted_win_rate: float
    confidence_interval: Tuple[float, float]

    def __post_init__(self) -> None:
        """验证性能预测数据"""
        if not 0 <= self.predicted_win_rate <= 1:
            raise ValueError(f"预测胜率必须在[0, 1]范围内，当前: {self.predicted_win_rate}")
        if self.confidence_interval[0] > self.confidence_interval[1]:
            raise ValueError("置信区间下限不能大于上限")

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "predicted_sharpe": self.predicted_sharpe,
            "predicted_max_drawdown": self.predicted_max_drawdown,
            "predicted_win_rate": self.predicted_win_rate,
            "confidence_interval": list(self.confidence_interval),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PerformancePrediction":
        """从字典创建性能预测对象"""
        return cls(
            predicted_sharpe=data["predicted_sharpe"],
            predicted_max_drawdown=data["predicted_max_drawdown"],
            predicted_win_rate=data["predicted_win_rate"],
            confidence_interval=tuple(data["confidence_interval"]),
        )


@dataclass
class Z2HCertificationResult:
    """Z2H认证结果数据模型

    白皮书依据: 第四章 4.3.2 Z2H基因胶囊认证系统

    Attributes:
        certification_id: 认证ID
        factor_id: 因子ID
        status: 认证状态
        certification_level: 认证等级
        certification_date: 认证日期
        expiry_date: 过期日期
        remarks: 备注
    """

    certification_id: str
    factor_id: str
    status: Z2HStampStatus
    certification_level: Optional[str]
    certification_date: datetime
    expiry_date: Optional[datetime]
    remarks: str

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "certification_id": self.certification_id,
            "factor_id": self.factor_id,
            "status": self.status.value,
            "certification_level": self.certification_level,
            "certification_date": self.certification_date.isoformat(),
            "expiry_date": self.expiry_date.isoformat() if self.expiry_date else None,
            "remarks": self.remarks,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Z2HCertificationResult":
        """从字典创建Z2H认证结果对象"""
        return cls(
            certification_id=data["certification_id"],
            factor_id=data["factor_id"],
            status=Z2HStampStatus(data["status"]),
            certification_level=data.get("certification_level"),
            certification_date=datetime.fromisoformat(data["certification_date"]),
            expiry_date=datetime.fromisoformat(data["expiry_date"]) if data.get("expiry_date") else None,
            remarks=data.get("remarks", ""),
        )


@dataclass
class EvolutionContext:
    """进化上下文数据模型

    白皮书依据: 第五章 5.3.1 进化协同流程

    Attributes:
        factor: 因子
        parent_capsule_id: 父代胶囊ID
        meaning_analysis: 因子意义分析
        academic_matches: 学术因子匹配列表
        audit_result: 审计结果
        arena_result: Arena测试结果
        performance_diff: 表现差异分析
        weakness_report: 弱点报告
        optimization_suggestions: 优化建议
        performance_prediction: 性能预测
        z2h_result: Z2H认证结果
    """

    factor: Factor
    parent_capsule_id: Optional[str]
    meaning_analysis: Optional[FactorMeaningAnalysis] = None
    academic_matches: List[AcademicFactorMatch] = field(default_factory=list)
    audit_result: Optional[AuditResult] = None
    arena_result: Optional[ArenaTestResult] = None
    performance_diff: Optional[PerformanceDiffAnalysis] = None
    weakness_report: Optional[WeaknessReport] = None
    optimization_suggestions: Optional[OptimizationSuggestions] = None
    performance_prediction: Optional[PerformancePrediction] = None
    z2h_result: Optional[Z2HCertificationResult] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "factor": self.factor.to_dict(),
            "parent_capsule_id": self.parent_capsule_id,
            "meaning_analysis": self.meaning_analysis.to_dict() if self.meaning_analysis else None,
            "academic_matches": [m.to_dict() for m in self.academic_matches],
            "audit_result": self.audit_result.to_dict() if self.audit_result else None,
            "arena_result": self.arena_result.to_dict() if self.arena_result else None,
            "performance_diff": self.performance_diff.to_dict() if self.performance_diff else None,
            "weakness_report": self.weakness_report.to_dict() if self.weakness_report else None,
            "optimization_suggestions": (
                self.optimization_suggestions.to_dict() if self.optimization_suggestions else None
            ),
            "performance_prediction": self.performance_prediction.to_dict() if self.performance_prediction else None,
            "z2h_result": self.z2h_result.to_dict() if self.z2h_result else None,
        }


@dataclass
class EvolutionReport:
    """进化报告数据模型

    白皮书依据: 第五章 5.3.1 进化协同流程

    Attributes:
        report_id: 报告ID
        factor_id: 因子ID
        capsule_id: 胶囊ID
        meaning_analysis: 因子意义分析
        academic_matches: 学术因子匹配列表
        audit_result: 审计结果
        arena_result: Arena测试结果
        performance_diff: 表现差异分析
        weakness_report: 弱点报告
        optimization_suggestions: 优化建议
        performance_prediction: 性能预测
        z2h_result: Z2H认证结果
        created_at: 创建时间
    """

    report_id: str
    factor_id: str
    capsule_id: str
    meaning_analysis: FactorMeaningAnalysis
    academic_matches: List[AcademicFactorMatch]
    audit_result: AuditResult
    arena_result: ArenaTestResult
    performance_diff: PerformanceDiffAnalysis
    weakness_report: WeaknessReport
    optimization_suggestions: OptimizationSuggestions
    performance_prediction: PerformancePrediction
    z2h_result: Z2HCertificationResult
    created_at: datetime

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "report_id": self.report_id,
            "factor_id": self.factor_id,
            "capsule_id": self.capsule_id,
            "meaning_analysis": self.meaning_analysis.to_dict(),
            "academic_matches": [m.to_dict() for m in self.academic_matches],
            "audit_result": self.audit_result.to_dict(),
            "arena_result": self.arena_result.to_dict(),
            "performance_diff": self.performance_diff.to_dict(),
            "weakness_report": self.weakness_report.to_dict(),
            "optimization_suggestions": self.optimization_suggestions.to_dict(),
            "performance_prediction": self.performance_prediction.to_dict(),
            "z2h_result": self.z2h_result.to_dict(),
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EvolutionReport":
        """从字典创建进化报告对象"""
        return cls(
            report_id=data["report_id"],
            factor_id=data["factor_id"],
            capsule_id=data["capsule_id"],
            meaning_analysis=FactorMeaningAnalysis.from_dict(data["meaning_analysis"]),
            academic_matches=[AcademicFactorMatch.from_dict(m) for m in data["academic_matches"]],
            audit_result=AuditResult.from_dict(data["audit_result"]),
            arena_result=ArenaTestResult.from_dict(data["arena_result"]),
            performance_diff=PerformanceDiffAnalysis.from_dict(data["performance_diff"]),
            weakness_report=WeaknessReport.from_dict(data["weakness_report"]),
            optimization_suggestions=OptimizationSuggestions.from_dict(data["optimization_suggestions"]),
            performance_prediction=PerformancePrediction.from_dict(data["performance_prediction"]),
            z2h_result=Z2HCertificationResult.from_dict(data["z2h_result"]),
            created_at=datetime.fromisoformat(data["created_at"]),
        )


@dataclass
class EvolutionResult:
    """进化结果数据模型

    白皮书依据: 第五章 5.3.1 进化协同流程

    Attributes:
        success: 是否成功
        gene_capsule: 基因胶囊（成功时）
        evolution_report: 进化报告（成功时）
        failure_reason: 失败原因（失败时）
        failure_step: 失败步骤（失败时）
    """

    success: bool
    gene_capsule: Optional[GeneCapsule] = None
    evolution_report: Optional[EvolutionReport] = None
    failure_reason: Optional[str] = None
    failure_step: Optional[FailureStep] = None

    def __post_init__(self) -> None:
        """验证进化结果数据"""
        if self.success:
            if self.gene_capsule is None:
                raise ValueError("成功的进化结果必须包含基因胶囊")
            if self.evolution_report is None:
                raise ValueError("成功的进化结果必须包含进化报告")
        else:
            if self.failure_reason is None:
                raise ValueError("失败的进化结果必须包含失败原因")
            if self.failure_step is None:
                raise ValueError("失败的进化结果必须包含失败步骤")

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "success": self.success,
            "gene_capsule": self.gene_capsule.to_dict() if self.gene_capsule else None,
            "evolution_report": self.evolution_report.to_dict() if self.evolution_report else None,
            "failure_reason": self.failure_reason,
            "failure_step": self.failure_step.value if self.failure_step else None,
        }


@dataclass
class FamilyComparisonResult:
    """家族对比结果数据模型

    白皮书依据: 第五章 5.3.3 演化树

    Attributes:
        family_id: 家族ID
        members: 成员列表
        best_performer: 最佳表现者
        worst_performer: 最差表现者
        common_traits: 共同特征列表
        divergent_traits: 差异特征列表
        fitness_distribution: 适应度分布
    """

    family_id: str
    members: List[str]
    best_performer: str
    worst_performer: str
    common_traits: List[str]
    divergent_traits: List[str]
    fitness_distribution: Dict[str, float]

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "family_id": self.family_id,
            "members": self.members,
            "best_performer": self.best_performer,
            "worst_performer": self.worst_performer,
            "common_traits": self.common_traits,
            "divergent_traits": self.divergent_traits,
            "fitness_distribution": self.fitness_distribution,
        }


@dataclass
class FailureLearningResult:
    """失败学习结果数据模型

    白皮书依据: 第五章 5.3.3 演化树

    Attributes:
        family_id: 家族ID
        failed_branches: 失败分支列表
        failure_patterns: 失败模式列表
        lessons_learned: 学到的教训列表
        avoidance_recommendations: 避免建议列表
    """

    family_id: str
    failed_branches: List[str]
    failure_patterns: List[str]
    lessons_learned: List[str]
    avoidance_recommendations: List[str]

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "family_id": self.family_id,
            "failed_branches": self.failed_branches,
            "failure_patterns": self.failure_patterns,
            "lessons_learned": self.lessons_learned,
            "avoidance_recommendations": self.avoidance_recommendations,
        }


# 工厂函数
def create_factor(
    expression: str,
    name: str,
    description: str = "",
    parameters: Optional[Dict[str, Any]] = None,
) -> Factor:
    """创建因子对象的工厂函数

    Args:
        expression: 因子表达式
        name: 因子名称
        description: 因子描述
        parameters: 因子参数配置

    Returns:
        Factor: 创建的因子对象
    """
    return Factor(
        factor_id=str(uuid.uuid4()),
        expression=expression,
        name=name,
        description=description,
        parameters=parameters or {},
        created_at=datetime.now(),
    )


def create_evolution_record(
    parent_capsule_id: Optional[str],
    mutation_type: MutationType,
    mutation_description: str,
    fitness_before: float,
    fitness_after: float,
) -> EvolutionRecord:
    """创建进化记录对象的工厂函数

    Args:
        parent_capsule_id: 父代胶囊ID
        mutation_type: 变异类型
        mutation_description: 变异描述
        fitness_before: 变异前适应度
        fitness_after: 变异后适应度

    Returns:
        EvolutionRecord: 创建的进化记录对象
    """
    return EvolutionRecord(
        record_id=str(uuid.uuid4()),
        parent_capsule_id=parent_capsule_id,
        mutation_type=mutation_type,
        mutation_description=mutation_description,
        fitness_before=fitness_before,
        fitness_after=fitness_after,
        timestamp=datetime.now(),
    )
