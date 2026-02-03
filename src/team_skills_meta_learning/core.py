"""
团队技能元学习系统核心模块

统一的技能元学习系统接口，整合技能识别、模式分析和配置优化功能。
"""

import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import logging

from .models import (
    Skill, SkillCategory, SkillLevel, RoleSkillProfile, 
    LearningEvent, LearningEventType, LearningOutcome,
    TeamSkillsSnapshot, SkillGap, PREDEFINED_SKILLS
)
from .skill_recognition import SkillRecognitionEngine
from .pattern_analyzer import LearningPatternAnalyzer
from .config_optimizer import SkillConfigurationOptimizer
from .meta_coordinator import MetaLearningCoordinator


class TeamSkillsMetaLearningSystem:
    """团队技能元学习系统主类"""
    
    def __init__(self, storage_path: str = ".kiro/team_skills", enable_learning: bool = True):
        """
        初始化团队技能元学习系统
        
        Args:
            storage_path: 存储路径
            enable_learning: 是否启用学习功能
        """
        self.storage_path = storage_path
        self.enable_learning = enable_learning
        
        # 初始化核心引擎
        self.skill_recognition = SkillRecognitionEngine()
        self.pattern_analyzer = LearningPatternAnalyzer()
        self.config_optimizer = SkillConfigurationOptimizer()
        self.meta_coordinator = MetaLearningCoordinator()
        
        # 团队角色配置
        self.team_roles = [
            "Product Manager", "Software Architect", "Algorithm Engineer",
            "Database Engineer", "UI/UX Engineer", "Full-Stack Engineer",
            "Security Engineer", "DevOps Engineer", "Data Engineer",
            "Test Engineer", "Scrum Master/Tech Lead", "Code Review Specialist"
        ]
        
        # 角色技能画像
        self.role_profiles: Dict[str, RoleSkillProfile] = {}
        
        # 学习事件历史
        self.learning_events: List[LearningEvent] = []
        
        # 设置日志
        self.logger = logging.getLogger(__name__)
        self.logger.info("Team Skills Meta-Learning System initialized")
        
        # 初始化角色技能画像
        self._initialize_role_profiles()
    
    def _initialize_role_profiles(self):
        """初始化角色技能画像"""
        for role in self.team_roles:
            self.role_profiles[role] = RoleSkillProfile(role_name=role)
            
            # 为每个角色分配基础技能
            base_skills = self._get_base_skills_for_role(role)
            for skill in base_skills:
                self.role_profiles[role].add_skill(skill, "primary")
    
    def _get_base_skills_for_role(self, role: str) -> List[Skill]:
        """获取角色的基础技能"""
        role_skill_mapping = {
            "Product Manager": ["technical_writing", "system_architecture"],
            "Software Architect": ["system_architecture", "python_programming", "technical_writing"],
            "Algorithm Engineer": ["python_programming", "system_architecture"],
            "Database Engineer": ["python_programming", "system_architecture"],
            "UI/UX Engineer": ["javascript_programming", "technical_writing"],
            "Full-Stack Engineer": ["python_programming", "javascript_programming", "git_version_control"],
            "Security Engineer": ["python_programming", "system_architecture"],
            "DevOps Engineer": ["docker_containerization", "git_version_control", "python_programming"],
            "Data Engineer": ["python_programming", "system_architecture"],
            "Test Engineer": ["python_programming", "technical_writing"],
            "Scrum Master/Tech Lead": ["technical_writing", "code_review"],
            "Code Review Specialist": ["code_review", "python_programming", "technical_writing"]
        }
        
        skill_ids = role_skill_mapping.get(role, [])
        skills = []
        
        for skill_id in skill_ids:
            if skill_id in PREDEFINED_SKILLS:
                # 创建技能副本，避免共享引用
                base_skill = PREDEFINED_SKILLS[skill_id]
                skill = Skill(
                    id=f"{role}_{skill_id}",
                    name=base_skill.name,
                    category=base_skill.category,
                    level=base_skill.level,
                    proficiency=base_skill.proficiency * 0.8,  # 初始熟练度稍低
                    tags=base_skill.tags + [role.lower().replace(" ", "_")]
                )
                skills.append(skill)
        
        return skills
    
    # ==================== 技能识别功能 ====================
    
    def analyze_code_skills(self, role: str, code_content: str, file_path: str) -> List[Skill]:
        """分析代码中体现的技能"""
        try:
            identified_skills = self.skill_recognition.extract_skills_from_code(
                code_content, file_path
            )
            
            # 更新角色技能画像
            if role in self.role_profiles:
                for skill in identified_skills:
                    existing_skill = self.role_profiles[role].get_skill_by_name(skill.name)
                    if existing_skill:
                        # 更新现有技能
                        existing_skill.usage_frequency += 1
                        existing_skill.last_used = datetime.now()
                    else:
                        # 添加新技能
                        self.role_profiles[role].add_skill(skill, "secondary")
            
            return identified_skills
            
        except Exception as e:
            self.logger.error(f"Failed to analyze code skills for {role}: {e}")
            return []
    
    def analyze_document_skills(self, role: str, document_content: str, doc_type: str) -> List[Skill]:
        """分析文档中体现的技能"""
        try:
            identified_skills = self.skill_recognition.extract_skills_from_docs(
                document_content, doc_type
            )
            
            # 更新角色技能画像
            if role in self.role_profiles:
                for skill in identified_skills:
                    existing_skill = self.role_profiles[role].get_skill_by_name(skill.name)
                    if existing_skill:
                        existing_skill.usage_frequency += 1
                        existing_skill.last_used = datetime.now()
                    else:
                        self.role_profiles[role].add_skill(skill, "secondary")
            
            return identified_skills
            
        except Exception as e:
            self.logger.error(f"Failed to analyze document skills for {role}: {e}")
            return []
    
    def analyze_review_skills(self, role: str, review_content: str, review_context: Dict[str, Any]) -> List[Skill]:
        """分析代码审查中体现的技能"""
        try:
            identified_skills = self.skill_recognition.extract_skills_from_reviews(
                review_content, review_context
            )
            
            # 更新角色技能画像
            if role in self.role_profiles:
                for skill in identified_skills:
                    existing_skill = self.role_profiles[role].get_skill_by_name(skill.name)
                    if existing_skill:
                        existing_skill.usage_frequency += 1
                        existing_skill.success_rate = min(1.0, existing_skill.success_rate + 0.1)
                    else:
                        self.role_profiles[role].add_skill(skill, "secondary")
            
            return identified_skills
            
        except Exception as e:
            self.logger.error(f"Failed to analyze review skills for {role}: {e}")
            return []
    
    # ==================== 学习模式分析 ====================
    
    def identify_success_patterns(self, role: str, time_window: int = 30) -> Dict[str, Any]:
        """识别成功模式"""
        try:
            # 获取指定时间窗口内的学习事件
            cutoff_date = datetime.now() - timedelta(days=time_window)
            recent_events = [
                event for event in self.learning_events
                if event.role_name == role and event.timestamp >= cutoff_date
                and event.outcome == LearningOutcome.SUCCESS
            ]
            
            return self.pattern_analyzer.identify_success_patterns(recent_events)
            
        except Exception as e:
            self.logger.error(f"Failed to identify success patterns for {role}: {e}")
            return {}
    
    def analyze_failure_patterns(self, role: str, time_window: int = 30) -> Dict[str, Any]:
        """分析失败模式"""
        try:
            cutoff_date = datetime.now() - timedelta(days=time_window)
            recent_events = [
                event for event in self.learning_events
                if event.role_name == role and event.timestamp >= cutoff_date
                and event.outcome == LearningOutcome.FAILURE
            ]
            
            return self.pattern_analyzer.analyze_failure_patterns(recent_events)
            
        except Exception as e:
            self.logger.error(f"Failed to analyze failure patterns for {role}: {e}")
            return {}
    
    def discover_skill_correlations(self, role: str) -> Dict[str, List[str]]:
        """发现技能关联"""
        try:
            if role not in self.role_profiles:
                return {}
            
            profile = self.role_profiles[role]
            return self.pattern_analyzer.discover_skill_correlations(profile.get_all_skills())
            
        except Exception as e:
            self.logger.error(f"Failed to discover skill correlations for {role}: {e}")
            return {}
    
    # ==================== 技能配置优化 ====================
    
    def identify_skill_gaps(self, role: str, target_project: Dict[str, Any] = None) -> List[SkillGap]:
        """识别技能缺口"""
        try:
            if role not in self.role_profiles:
                return []
            
            profile = self.role_profiles[role]
            return self.config_optimizer.identify_skill_gaps(profile, target_project)
            
        except Exception as e:
            self.logger.error(f"Failed to identify skill gaps for {role}: {e}")
            return []
    
    def recommend_skill_development(self, role: str, max_recommendations: int = 5) -> List[Dict[str, Any]]:
        """推荐技能发展"""
        try:
            if role not in self.role_profiles:
                return []
            
            profile = self.role_profiles[role]
            skill_gaps = self.identify_skill_gaps(role)
            
            return self.config_optimizer.recommend_skill_development(
                profile, skill_gaps, max_recommendations
            )
            
        except Exception as e:
            self.logger.error(f"Failed to recommend skill development for {role}: {e}")
            return []
    
    def optimize_team_balance(self) -> Dict[str, Any]:
        """优化团队技能平衡"""
        try:
            return self.config_optimizer.optimize_team_balance(self.role_profiles)
            
        except Exception as e:
            self.logger.error(f"Failed to optimize team balance: {e}")
            return {}
    
    # ==================== 学习事件记录 ====================
    
    def record_learning_event(self, 
                            role: str,
                            skill_id: str,
                            event_type: LearningEventType,
                            outcome: LearningOutcome,
                            context: Dict[str, Any] = None,
                            evidence: List[str] = None) -> str:
        """记录学习事件"""
        try:
            event_id = str(uuid.uuid4())
            
            event = LearningEvent(
                event_id=event_id,
                role_name=role,
                skill_id=skill_id,
                event_type=event_type,
                outcome=outcome,
                context=context or {},
                evidence=evidence or []
            )
            
            self.learning_events.append(event)
            
            # 更新技能统计
            if role in self.role_profiles:
                skill = self.role_profiles[role].get_skill_by_name(skill_id)
                if skill:
                    skill.usage_frequency += 1
                    if outcome == LearningOutcome.SUCCESS:
                        skill.success_rate = min(1.0, skill.success_rate + 0.05)
                    elif outcome == LearningOutcome.FAILURE:
                        skill.success_rate = max(0.0, skill.success_rate - 0.02)
            
            self.logger.info(f"Recorded learning event {event_id} for {role}")
            return event_id
            
        except Exception as e:
            self.logger.error(f"Failed to record learning event: {e}")
            return ""
    
    # ==================== 系统管理功能 ====================
    
    def get_role_profile(self, role: str) -> Optional[RoleSkillProfile]:
        """获取角色技能画像"""
        return self.role_profiles.get(role)
    
    def get_team_snapshot(self) -> TeamSkillsSnapshot:
        """获取团队技能快照"""
        try:
            snapshot_id = str(uuid.uuid4())
            
            # 计算团队指标
            team_metrics = self._calculate_team_metrics()
            
            # 统计技能分布
            skill_distribution = self._calculate_skill_distribution()
            
            # 计算协作矩阵
            collaboration_matrix = self._calculate_collaboration_matrix()
            
            # 分析学习趋势
            learning_trends = self._analyze_learning_trends()
            
            snapshot = TeamSkillsSnapshot(
                snapshot_id=snapshot_id,
                timestamp=datetime.now(),
                role_profiles=self.role_profiles.copy(),
                team_metrics=team_metrics,
                skill_distribution=skill_distribution,
                collaboration_matrix=collaboration_matrix,
                learning_trends=learning_trends
            )
            
            return snapshot
            
        except Exception as e:
            self.logger.error(f"Failed to get team snapshot: {e}")
            return TeamSkillsSnapshot(
                snapshot_id="error",
                timestamp=datetime.now(),
                role_profiles={},
                team_metrics={},
                skill_distribution={},
                collaboration_matrix={},
                learning_trends={}
            )
    
    def _calculate_team_metrics(self) -> Dict[str, float]:
        """计算团队整体指标 - 修复数据一致性"""
        if not self.role_profiles:
            return {}
        
        # 修复：安全计算平均熟练度
        total_proficiency = 0.0
        valid_profiles = 0
        
        for profile in self.role_profiles.values():
            try:
                proficiency = profile.calculate_overall_proficiency()
                if isinstance(proficiency, (int, float)) and not (proficiency != proficiency):  # 检查NaN
                    total_proficiency += proficiency
                    valid_profiles += 1
            except Exception as e:
                self.logger.warning(f"Failed to calculate proficiency for profile: {e}")
                continue
        
        avg_proficiency = total_proficiency / valid_profiles if valid_profiles > 0 else 0.0
        
        # 修复：准确计算技能覆盖率
        all_skills = set()
        total_skill_count = 0
        
        for profile in self.role_profiles.values():
            try:
                profile_skills = profile.get_all_skills()
                if profile_skills:
                    for skill in profile_skills:
                        if skill and hasattr(skill, 'name') and skill.name:
                            all_skills.add(skill.name)
                            total_skill_count += 1
            except Exception as e:
                self.logger.warning(f"Failed to get skills for profile: {e}")
                continue
        
        unique_skill_coverage = len(all_skills)
        
        # 修复：安全计算学习活跃度
        try:
            recent_events = [
                event for event in self.learning_events
                if hasattr(event, 'timestamp') and event.timestamp >= datetime.now() - timedelta(days=7)
            ]
            learning_activity = len(recent_events)
        except Exception as e:
            self.logger.warning(f"Failed to calculate learning activity: {e}")
            learning_activity = 0
        
        return {
            "average_proficiency": round(avg_proficiency, 3),
            "unique_skill_coverage": unique_skill_coverage,
            "total_skill_instances": total_skill_count,
            "learning_activity": learning_activity,
            "team_size": len(self.role_profiles),
            "valid_profiles": valid_profiles
        }
    
    def _calculate_skill_distribution(self) -> Dict[str, int]:
        """计算技能分布统计 - 修复数据一致性"""
        skill_counts = {}
        category_counts = {}
        
        for role_name, profile in self.role_profiles.items():
            try:
                skills = profile.get_all_skills()
                if not skills:
                    continue
                    
                for skill in skills:
                    if not skill or not hasattr(skill, 'name') or not skill.name:
                        continue
                        
                    # 统计具体技能
                    skill_name = skill.name
                    skill_counts[skill_name] = skill_counts.get(skill_name, 0) + 1
                    
                    # 统计技能类别
                    if hasattr(skill, 'category') and skill.category:
                        category = skill.category.value if hasattr(skill.category, 'value') else str(skill.category)
                        category_counts[category] = category_counts.get(category, 0) + 1
                        
            except Exception as e:
                self.logger.warning(f"Failed to calculate skill distribution for {role_name}: {e}")
                continue
        
        # 返回详细的分布信息
        return {
            "by_skill": skill_counts,
            "by_category": category_counts,
            "total_unique_skills": len(skill_counts),
            "total_skill_instances": sum(skill_counts.values()),
            "total_categories": len(category_counts)
        }
    
    def _calculate_collaboration_matrix(self) -> Dict[str, Dict[str, float]]:
        """计算协作矩阵"""
        # 简化实现：基于技能重叠度计算协作潜力
        matrix = {}
        
        roles = list(self.role_profiles.keys())
        for role1 in roles:
            matrix[role1] = {}
            for role2 in roles:
                if role1 == role2:
                    matrix[role1][role2] = 1.0
                else:
                    # 计算技能重叠度
                    skills1 = set(s.name for s in self.role_profiles[role1].get_all_skills())
                    skills2 = set(s.name for s in self.role_profiles[role2].get_all_skills())
                    
                    if skills1 or skills2:
                        overlap = len(skills1 & skills2) / len(skills1 | skills2)
                        matrix[role1][role2] = overlap
                    else:
                        matrix[role1][role2] = 0.0
        
        return matrix
    
    def _analyze_learning_trends(self) -> Dict[str, List[float]]:
        """分析学习趋势"""
        trends = {}
        
        # 按周统计学习事件
        for i in range(4):  # 最近4周
            week_start = datetime.now() - timedelta(weeks=i+1)
            week_end = datetime.now() - timedelta(weeks=i)
            
            week_events = [
                event for event in self.learning_events
                if week_start <= event.timestamp < week_end
            ]
            
            for role in self.team_roles:
                if role not in trends:
                    trends[role] = []
                
                role_events = [e for e in week_events if e.role_name == role]
                trends[role].insert(0, len(role_events))  # 插入到开头，保持时间顺序
        
        return trends
    
    def get_system_stats(self) -> Dict[str, Any]:
        """获取系统统计信息 - 修复数据一致性"""
        try:
            # 安全计算总技能数
            total_skills = 0
            unique_skills = set()
            valid_profiles = 0
            total_proficiency = 0.0
            
            for role_name, profile in self.role_profiles.items():
                try:
                    skills = profile.get_all_skills()
                    if skills:
                        valid_profiles += 1
                        for skill in skills:
                            if skill and hasattr(skill, 'name') and skill.name:
                                total_skills += 1
                                unique_skills.add(skill.name)
                        
                        # 安全计算熟练度
                        proficiency = profile.calculate_overall_proficiency()
                        if isinstance(proficiency, (int, float)) and not (proficiency != proficiency):
                            total_proficiency += proficiency
                            
                except Exception as e:
                    self.logger.warning(f"Failed to process profile {role_name}: {e}")
                    continue
            
            # 安全计算平均熟练度
            avg_proficiency = total_proficiency / valid_profiles if valid_profiles > 0 else 0.0
            
            # 安全计算技能类别
            skill_categories = set()
            for profile in self.role_profiles.values():
                try:
                    for skill in profile.get_all_skills():
                        if skill and hasattr(skill, 'category') and skill.category:
                            category = skill.category.value if hasattr(skill.category, 'value') else str(skill.category)
                            skill_categories.add(category)
                except Exception as e:
                    continue
            
            # 安全计算最近活动
            recent_activity = 0
            try:
                cutoff_date = datetime.now() - timedelta(days=7)
                recent_activity = len([
                    e for e in self.learning_events 
                    if hasattr(e, 'timestamp') and e.timestamp >= cutoff_date
                ])
            except Exception as e:
                self.logger.warning(f"Failed to calculate recent activity: {e}")
            
            stats = {
                "total_roles": len(self.role_profiles),
                "active_roles": valid_profiles,
                "total_skill_instances": total_skills,
                "unique_skills": len(unique_skills),
                "total_learning_events": len(self.learning_events),
                "average_proficiency": round(avg_proficiency, 3),
                "skill_categories": len(skill_categories),
                "recent_activity": recent_activity,
                "data_consistency": {
                    "profiles_with_skills": valid_profiles,
                    "empty_profiles": len(self.role_profiles) - valid_profiles,
                    "skill_distribution_ratio": round(total_skills / len(unique_skills), 2) if unique_skills else 0
                }
            }
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Failed to get system stats: {e}")
            return {
                "error": str(e),
                "total_roles": len(self.role_profiles) if self.role_profiles else 0,
                "status": "error"
            }