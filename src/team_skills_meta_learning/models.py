"""
团队技能元学习系统数据模型

定义技能、角色、学习事件等核心数据结构。
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum
import json


class SkillCategory(Enum):
    """技能分类"""
    TECHNICAL = "technical"          # 技术技能
    SOFT_SKILL = "soft_skill"       # 软技能
    COMMUNICATION = "communication"  # 沟通技能
    DOMAIN_KNOWLEDGE = "domain"     # 领域知识
    TOOL_PROFICIENCY = "tool"       # 工具熟练度
    METHODOLOGY = "methodology"      # 方法论


class SkillLevel(Enum):
    """技能等级"""
    NOVICE = "novice"               # 新手
    BEGINNER = "beginner"           # 初学者
    INTERMEDIATE = "intermediate"    # 中级
    ADVANCED = "advanced"           # 高级
    EXPERT = "expert"               # 专家


class LearningEventType(Enum):
    """学习事件类型"""
    SKILL_USAGE = "skill_usage"         # 技能使用
    SKILL_LEARNING = "skill_learning"   # 技能学习
    SKILL_ACQUISITION = "skill_acquisition"  # 技能获得
    SKILL_IMPROVEMENT = "improvement"    # 技能提升
    KNOWLEDGE_SHARING = "sharing"        # 知识分享
    COLLABORATION = "collaboration"      # 协作学习
    PROBLEM_SOLVING = "problem_solving"  # 问题解决


class LearningOutcome(Enum):
    """学习结果"""
    SUCCESS = "success"             # 成功
    PARTIAL_SUCCESS = "partial"     # 部分成功
    FAILURE = "failure"             # 失败
    LEARNING = "learning"           # 学习中


@dataclass
class SkillEvidence:
    """技能证据"""
    evidence_id: str
    evidence_type: str              # code_commit, document, review, etc.
    source_path: str               # 证据来源路径
    description: str               # 证据描述
    quality_score: float           # 质量评分 0-1
    timestamp: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "evidence_id": self.evidence_id,
            "evidence_type": self.evidence_type,
            "source_path": self.source_path,
            "description": self.description,
            "quality_score": self.quality_score,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata
        }


@dataclass
class Skill:
    """技能模型"""
    id: str
    name: str
    category: SkillCategory
    level: SkillLevel
    proficiency: float              # 熟练度 0-1
    confidence: float = 1.0         # 评估置信度 0-1
    evidence: List[SkillEvidence] = field(default_factory=list)
    last_used: datetime = field(default_factory=datetime.now)
    improvement_rate: float = 0.0   # 提升速度
    usage_frequency: int = 0        # 使用频率
    success_rate: float = 0.0       # 成功率
    related_skills: List[str] = field(default_factory=list)  # 相关技能ID
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def add_evidence(self, evidence: SkillEvidence):
        """添加技能证据"""
        self.evidence.append(evidence)
        self.last_used = max(self.last_used, evidence.timestamp)
        
        # 更新熟练度（基于证据质量）
        if evidence.quality_score > 0.7:
            self.proficiency = min(1.0, self.proficiency + 0.05)
    
    def calculate_proficiency(self) -> float:
        """计算综合熟练度"""
        if not self.evidence:
            return self.proficiency
        
        # 基于证据质量和频率计算
        evidence_score = sum(e.quality_score for e in self.evidence) / len(self.evidence)
        frequency_score = min(1.0, self.usage_frequency / 100.0)
        success_score = self.success_rate
        
        # 加权平均
        calculated_proficiency = (
            evidence_score * 0.4 + 
            frequency_score * 0.3 + 
            success_score * 0.3
        )
        
        return min(1.0, calculated_proficiency)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category.value,
            "level": self.level.value,
            "proficiency": self.proficiency,
            "confidence": self.confidence,
            "evidence": [e.to_dict() for e in self.evidence],
            "last_used": self.last_used.isoformat(),
            "improvement_rate": self.improvement_rate,
            "usage_frequency": self.usage_frequency,
            "success_rate": self.success_rate,
            "related_skills": self.related_skills,
            "tags": self.tags,
            "metadata": self.metadata
        }


@dataclass
class SkillGap:
    """技能缺口"""
    skill_name: str
    required_level: SkillLevel
    current_level: SkillLevel
    priority: float                 # 优先级 0-1
    impact: str                     # 影响描述
    learning_path: List[str] = field(default_factory=list)  # 学习路径
    estimated_time: int = 0         # 预估学习时间（小时）
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "skill_name": self.skill_name,
            "required_level": self.required_level.value,
            "current_level": self.current_level.value,
            "priority": self.priority,
            "impact": self.impact,
            "learning_path": self.learning_path,
            "estimated_time": self.estimated_time
        }


@dataclass
class RoleSkillProfile:
    """角色技能画像"""
    role_name: str
    primary_skills: List[Skill] = field(default_factory=list)      # 核心技能
    secondary_skills: List[Skill] = field(default_factory=list)    # 辅助技能
    learning_skills: List[Skill] = field(default_factory=list)     # 学习中的技能
    skill_gaps: List[SkillGap] = field(default_factory=list)       # 技能缺口
    learning_preferences: Dict[str, Any] = field(default_factory=dict)  # 学习偏好
    collaboration_patterns: Dict[str, Any] = field(default_factory=dict)  # 协作模式
    performance_metrics: Dict[str, float] = field(default_factory=dict)   # 性能指标
    last_updated: datetime = field(default_factory=datetime.now)
    
    def get_all_skills(self) -> List[Skill]:
        """获取所有技能"""
        return self.primary_skills + self.secondary_skills + self.learning_skills
    
    def get_skill_by_name(self, skill_name: str) -> Optional[Skill]:
        """根据名称获取技能"""
        for skill in self.get_all_skills():
            if skill.name == skill_name:
                return skill
        return None
    
    def add_skill(self, skill: Skill, skill_type: str = "secondary"):
        """添加技能"""
        if skill_type == "primary":
            self.primary_skills.append(skill)
        elif skill_type == "learning":
            self.learning_skills.append(skill)
        else:
            self.secondary_skills.append(skill)
        
        self.last_updated = datetime.now()
    
    def calculate_overall_proficiency(self) -> float:
        """计算整体熟练度"""
        all_skills = self.get_all_skills()
        if not all_skills:
            return 0.0
        
        # 核心技能权重更高
        total_score = 0.0
        total_weight = 0.0
        
        for skill in self.primary_skills:
            weight = 2.0
            total_score += skill.calculate_proficiency() * weight
            total_weight += weight
        
        for skill in self.secondary_skills:
            weight = 1.0
            total_score += skill.calculate_proficiency() * weight
            total_weight += weight
        
        for skill in self.learning_skills:
            weight = 0.5
            total_score += skill.calculate_proficiency() * weight
            total_weight += weight
        
        return total_score / total_weight if total_weight > 0 else 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "role_name": self.role_name,
            "primary_skills": [s.to_dict() for s in self.primary_skills],
            "secondary_skills": [s.to_dict() for s in self.secondary_skills],
            "learning_skills": [s.to_dict() for s in self.learning_skills],
            "skill_gaps": [g.to_dict() for g in self.skill_gaps],
            "learning_preferences": self.learning_preferences,
            "collaboration_patterns": self.collaboration_patterns,
            "performance_metrics": self.performance_metrics,
            "last_updated": self.last_updated.isoformat()
        }


@dataclass
class LearningEvent:
    """学习事件"""
    event_id: str
    role_name: str
    skill_id: str
    event_type: LearningEventType
    context: Dict[str, Any]         # 事件上下文
    outcome: LearningOutcome        # 学习结果
    timestamp: datetime = field(default_factory=datetime.now)
    evidence: List[str] = field(default_factory=list)  # 证据链接
    impact_score: float = 0.0       # 影响评分
    learning_insights: List[str] = field(default_factory=list)  # 学习洞察
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "role_name": self.role_name,
            "skill_id": self.skill_id,
            "event_type": self.event_type.value,
            "context": self.context,
            "outcome": self.outcome.value,
            "timestamp": self.timestamp.isoformat(),
            "evidence": self.evidence,
            "impact_score": self.impact_score,
            "learning_insights": self.learning_insights
        }


@dataclass
class TeamSkillsSnapshot:
    """团队技能快照"""
    snapshot_id: str
    timestamp: datetime
    role_profiles: Dict[str, RoleSkillProfile]  # 角色名 -> 技能画像
    team_metrics: Dict[str, float]              # 团队整体指标
    skill_distribution: Dict[str, int]          # 技能分布统计
    collaboration_matrix: Dict[str, Dict[str, float]]  # 协作矩阵
    learning_trends: Dict[str, List[float]]     # 学习趋势
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "timestamp": self.timestamp.isoformat(),
            "role_profiles": {k: v.to_dict() for k, v in self.role_profiles.items()},
            "team_metrics": self.team_metrics,
            "skill_distribution": self.skill_distribution,
            "collaboration_matrix": self.collaboration_matrix,
            "learning_trends": self.learning_trends
        }


# 预定义的技能库
PREDEFINED_SKILLS = {
    # 技术技能
    "python_programming": Skill(
        id="python_programming",
        name="Python编程",
        category=SkillCategory.TECHNICAL,
        level=SkillLevel.INTERMEDIATE,
        proficiency=0.7,
        tags=["programming", "python", "backend"]
    ),
    "javascript_programming": Skill(
        id="javascript_programming", 
        name="JavaScript编程",
        category=SkillCategory.TECHNICAL,
        level=SkillLevel.INTERMEDIATE,
        proficiency=0.6,
        tags=["programming", "javascript", "frontend"]
    ),
    "system_architecture": Skill(
        id="system_architecture",
        name="系统架构设计",
        category=SkillCategory.TECHNICAL,
        level=SkillLevel.ADVANCED,
        proficiency=0.8,
        tags=["architecture", "design", "system"]
    ),
    
    # 软技能
    "code_review": Skill(
        id="code_review",
        name="代码审查",
        category=SkillCategory.SOFT_SKILL,
        level=SkillLevel.ADVANCED,
        proficiency=0.8,
        tags=["review", "quality", "collaboration"]
    ),
    "technical_writing": Skill(
        id="technical_writing",
        name="技术文档写作",
        category=SkillCategory.SOFT_SKILL,
        level=SkillLevel.INTERMEDIATE,
        proficiency=0.6,
        tags=["documentation", "writing", "communication"]
    ),
    
    # 工具熟练度
    "git_version_control": Skill(
        id="git_version_control",
        name="Git版本控制",
        category=SkillCategory.TOOL_PROFICIENCY,
        level=SkillLevel.ADVANCED,
        proficiency=0.9,
        tags=["git", "version_control", "collaboration"]
    ),
    "docker_containerization": Skill(
        id="docker_containerization",
        name="Docker容器化",
        category=SkillCategory.TOOL_PROFICIENCY,
        level=SkillLevel.INTERMEDIATE,
        proficiency=0.7,
        tags=["docker", "containerization", "devops"]
    )
}