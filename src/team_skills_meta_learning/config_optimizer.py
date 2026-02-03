"""
技能配置优化器

优化团队技能配置，识别技能缺口并提供发展建议。
"""

from typing import List, Dict, Any, Optional
from collections import defaultdict

from .models import (
    Skill, SkillCategory, SkillLevel, RoleSkillProfile, 
    SkillGap, PREDEFINED_SKILLS
)


class SkillConfigurationOptimizer:
    """技能配置优化器"""
    
    def __init__(self):
        # 角色技能要求定义
        self.role_skill_requirements = {
            "Product Manager": {
                "required_skills": ["technical_writing", "system_architecture"],
                "preferred_skills": ["project_management", "user_research"],
                "min_proficiency": 0.7
            },
            "Software Architect": {
                "required_skills": ["system_architecture", "python_programming", "technical_writing"],
                "preferred_skills": ["design_patterns", "scalability_design"],
                "min_proficiency": 0.8
            },
            "Full-Stack Engineer": {
                "required_skills": ["python_programming", "javascript_programming", "git_version_control"],
                "preferred_skills": ["database_design", "api_development"],
                "min_proficiency": 0.7
            },
            "Security Engineer": {
                "required_skills": ["python_programming", "security_analysis"],
                "preferred_skills": ["penetration_testing", "compliance_audit"],
                "min_proficiency": 0.8
            },
            "DevOps Engineer": {
                "required_skills": ["docker_containerization", "git_version_control", "python_programming"],
                "preferred_skills": ["kubernetes", "ci_cd_pipeline"],
                "min_proficiency": 0.7
            },
            "Test Engineer": {
                "required_skills": ["python_programming", "test_automation"],
                "preferred_skills": ["performance_testing", "security_testing"],
                "min_proficiency": 0.7
            },
            "Code Review Specialist": {
                "required_skills": ["code_review", "python_programming", "technical_writing"],
                "preferred_skills": ["static_analysis", "code_quality_metrics"],
                "min_proficiency": 0.8
            }
        }
    
    def identify_skill_gaps(self, profile: RoleSkillProfile, target_project: Dict[str, Any] = None) -> List[SkillGap]:
        """识别技能缺口"""
        gaps = []
        
        # 获取角色要求
        role_requirements = self.role_skill_requirements.get(profile.role_name, {})
        required_skills = role_requirements.get("required_skills", [])
        preferred_skills = role_requirements.get("preferred_skills", [])
        min_proficiency = role_requirements.get("min_proficiency", 0.6)
        
        # 检查必需技能
        for required_skill in required_skills:
            current_skill = profile.get_skill_by_name(required_skill)
            
            if not current_skill:
                # 完全缺失的技能
                gap = SkillGap(
                    skill_name=required_skill,
                    required_level=SkillLevel.INTERMEDIATE,
                    current_level=SkillLevel.NOVICE,
                    priority=1.0,
                    impact="缺失必需技能，严重影响工作效率",
                    learning_path=self._generate_learning_path(required_skill),
                    estimated_time=40  # 40小时学习时间
                )
                gaps.append(gap)
            elif current_skill.proficiency < min_proficiency:
                # 熟练度不足的技能
                gap = SkillGap(
                    skill_name=required_skill,
                    required_level=SkillLevel.INTERMEDIATE,
                    current_level=current_skill.level,
                    priority=0.8,
                    impact=f"技能熟练度不足({current_skill.proficiency:.1%})，需要提升",
                    learning_path=self._generate_improvement_path(current_skill),
                    estimated_time=20  # 20小时改进时间
                )
                gaps.append(gap)
        
        # 检查偏好技能
        for preferred_skill in preferred_skills:
            current_skill = profile.get_skill_by_name(preferred_skill)
            
            if not current_skill:
                gap = SkillGap(
                    skill_name=preferred_skill,
                    required_level=SkillLevel.BEGINNER,
                    current_level=SkillLevel.NOVICE,
                    priority=0.5,
                    impact="缺失偏好技能，可能影响职业发展",
                    learning_path=self._generate_learning_path(preferred_skill),
                    estimated_time=20
                )
                gaps.append(gap)
        
        # 基于项目需求识别额外技能缺口
        if target_project:
            project_gaps = self._identify_project_skill_gaps(profile, target_project)
            gaps.extend(project_gaps)
        
        # 按优先级排序
        gaps.sort(key=lambda x: x.priority, reverse=True)
        
        return gaps
    
    def recommend_skill_development(self, 
                                  profile: RoleSkillProfile, 
                                  skill_gaps: List[SkillGap], 
                                  max_recommendations: int = 5) -> List[Dict[str, Any]]:
        """推荐技能发展"""
        recommendations = []
        
        # 基于技能缺口生成推荐
        for gap in skill_gaps[:max_recommendations]:
            recommendation = {
                "skill_name": gap.skill_name,
                "priority": gap.priority,
                "current_level": gap.current_level.value,
                "target_level": gap.required_level.value,
                "learning_path": gap.learning_path,
                "estimated_time": gap.estimated_time,
                "impact": gap.impact,
                "learning_resources": self._get_learning_resources(gap.skill_name),
                "success_metrics": self._define_success_metrics(gap.skill_name),
                "timeline": self._create_learning_timeline(gap.estimated_time)
            }
            recommendations.append(recommendation)
        
        # 基于角色发展趋势生成推荐
        trend_recommendations = self._generate_trend_based_recommendations(profile)
        recommendations.extend(trend_recommendations[:max_recommendations - len(recommendations)])
        
        return recommendations
    
    def optimize_team_balance(self, role_profiles: Dict[str, RoleSkillProfile]) -> Dict[str, Any]:
        """优化团队技能平衡"""
        optimization_result = {
            "team_strengths": [],
            "team_weaknesses": [],
            "skill_distribution": {},
            "collaboration_opportunities": [],
            "rebalancing_suggestions": []
        }
        
        # 分析团队技能分布
        skill_counts = defaultdict(int)
        skill_proficiencies = defaultdict(list)
        
        for profile in role_profiles.values():
            for skill in profile.get_all_skills():
                skill_counts[skill.name] += 1
                skill_proficiencies[skill.name].append(skill.proficiency)
        
        # 识别团队优势
        for skill_name, count in skill_counts.items():
            if count >= 3:  # 3个或更多角色拥有此技能
                avg_proficiency = sum(skill_proficiencies[skill_name]) / len(skill_proficiencies[skill_name])
                if avg_proficiency > 0.7:
                    optimization_result["team_strengths"].append({
                        "skill": skill_name,
                        "coverage": count,
                        "average_proficiency": avg_proficiency
                    })
        
        # 识别团队弱点
        critical_skills = ["python_programming", "system_architecture", "technical_writing", "code_review"]
        for skill in critical_skills:
            if skill not in skill_counts or skill_counts[skill] < 2:
                optimization_result["team_weaknesses"].append({
                    "skill": skill,
                    "coverage": skill_counts.get(skill, 0),
                    "risk": "关键技能覆盖不足"
                })
        
        # 技能分布统计
        optimization_result["skill_distribution"] = dict(skill_counts)
        
        # 识别协作机会
        for skill_name, count in skill_counts.items():
            if 2 <= count <= 4:  # 适合协作的技能覆盖度
                roles_with_skill = [
                    role for role, profile in role_profiles.items()
                    if profile.get_skill_by_name(skill_name)
                ]
                optimization_result["collaboration_opportunities"].append({
                    "skill": skill_name,
                    "roles": roles_with_skill,
                    "opportunity": "可以组成技能小组进行知识分享"
                })
        
        # 生成重平衡建议
        optimization_result["rebalancing_suggestions"] = self._generate_rebalancing_suggestions(
            role_profiles, skill_counts, skill_proficiencies
        )
        
        return optimization_result
    
    def _generate_learning_path(self, skill_name: str) -> List[str]:
        """生成学习路径"""
        learning_paths = {
            "python_programming": [
                "学习Python基础语法",
                "掌握面向对象编程",
                "学习常用库和框架",
                "实践项目开发",
                "代码优化和最佳实践"
            ],
            "javascript_programming": [
                "学习JavaScript基础",
                "掌握ES6+新特性",
                "学习前端框架",
                "异步编程和Promise",
                "性能优化技巧"
            ],
            "system_architecture": [
                "学习架构设计原则",
                "掌握设计模式",
                "分布式系统设计",
                "性能和可扩展性",
                "架构评估和优化"
            ],
            "technical_writing": [
                "技术文档写作基础",
                "API文档编写",
                "架构文档设计",
                "用户手册编写",
                "文档维护和版本控制"
            ],
            "code_review": [
                "代码审查基础知识",
                "审查工具使用",
                "质量标准制定",
                "反馈技巧",
                "团队协作改进"
            ]
        }
        
        return learning_paths.get(skill_name, [
            f"学习{skill_name}基础知识",
            f"实践{skill_name}应用",
            f"深入{skill_name}高级特性",
            f"优化{skill_name}使用效果"
        ])
    
    def _generate_improvement_path(self, skill: Skill) -> List[str]:
        """生成技能改进路径"""
        base_path = self._generate_learning_path(skill.name)
        
        # 根据当前熟练度调整路径
        if skill.proficiency < 0.3:
            return base_path[:2]  # 专注基础
        elif skill.proficiency < 0.6:
            return base_path[1:4]  # 中级提升
        else:
            return base_path[3:]   # 高级优化
    
    def _identify_project_skill_gaps(self, profile: RoleSkillProfile, project: Dict[str, Any]) -> List[SkillGap]:
        """基于项目需求识别技能缺口"""
        gaps = []
        
        # 从项目需求中提取技能要求
        required_technologies = project.get("technologies", [])
        project_complexity = project.get("complexity", "medium")
        
        for tech in required_technologies:
            current_skill = profile.get_skill_by_name(tech)
            
            if not current_skill:
                priority = 0.9 if project_complexity == "high" else 0.6
                gap = SkillGap(
                    skill_name=tech,
                    required_level=SkillLevel.INTERMEDIATE,
                    current_level=SkillLevel.NOVICE,
                    priority=priority,
                    impact=f"项目需要{tech}技能",
                    learning_path=self._generate_learning_path(tech),
                    estimated_time=30
                )
                gaps.append(gap)
        
        return gaps
    
    def _get_learning_resources(self, skill_name: str) -> List[Dict[str, str]]:
        """获取学习资源"""
        resources = {
            "python_programming": [
                {"type": "documentation", "name": "Python官方文档", "url": "https://docs.python.org/"},
                {"type": "tutorial", "name": "Python教程", "url": "https://www.python.org/about/gettingstarted/"},
                {"type": "practice", "name": "LeetCode Python", "url": "https://leetcode.com/"}
            ],
            "javascript_programming": [
                {"type": "documentation", "name": "MDN JavaScript", "url": "https://developer.mozilla.org/en-US/docs/Web/JavaScript"},
                {"type": "tutorial", "name": "JavaScript.info", "url": "https://javascript.info/"},
                {"type": "practice", "name": "CodePen", "url": "https://codepen.io/"}
            ]
        }
        
        return resources.get(skill_name, [
            {"type": "search", "name": f"搜索{skill_name}相关资源", "url": f"https://www.google.com/search?q={skill_name}+tutorial"}
        ])
    
    def _define_success_metrics(self, skill_name: str) -> List[str]:
        """定义成功指标"""
        return [
            f"能够独立完成{skill_name}相关任务",
            f"在{skill_name}方面的代码质量达标",
            f"能够指导他人学习{skill_name}",
            f"在{skill_name}项目中承担关键角色"
        ]
    
    def _create_learning_timeline(self, estimated_hours: int) -> Dict[str, str]:
        """创建学习时间线"""
        weeks = max(1, estimated_hours // 10)  # 假设每周10小时学习时间
        
        return {
            "total_hours": estimated_hours,
            "estimated_weeks": weeks,
            "weekly_commitment": "10小时/周",
            "milestone_frequency": "每2周评估进度"
        }
    
    def _generate_trend_based_recommendations(self, profile: RoleSkillProfile) -> List[Dict[str, Any]]:
        """基于趋势生成推荐"""
        recommendations = []
        
        # 基于角色发展趋势的通用推荐
        role_trends = {
            "Full-Stack Engineer": ["containerization", "microservices", "cloud_platforms"],
            "DevOps Engineer": ["kubernetes", "terraform", "monitoring"],
            "Security Engineer": ["zero_trust", "cloud_security", "devsecops"],
            "Data Engineer": ["stream_processing", "data_lakes", "mlops"]
        }
        
        trending_skills = role_trends.get(profile.role_name, [])
        
        for skill in trending_skills[:2]:  # 最多推荐2个趋势技能
            if not profile.get_skill_by_name(skill):
                recommendation = {
                    "skill_name": skill,
                    "priority": 0.4,
                    "current_level": "novice",
                    "target_level": "beginner",
                    "learning_path": self._generate_learning_path(skill),
                    "estimated_time": 25,
                    "impact": "跟上行业发展趋势",
                    "learning_resources": self._get_learning_resources(skill),
                    "success_metrics": self._define_success_metrics(skill),
                    "timeline": self._create_learning_timeline(25)
                }
                recommendations.append(recommendation)
        
        return recommendations
    
    def _generate_rebalancing_suggestions(self, 
                                        role_profiles: Dict[str, RoleSkillProfile],
                                        skill_counts: Dict[str, int],
                                        skill_proficiencies: Dict[str, List[float]]) -> List[Dict[str, Any]]:
        """生成重平衡建议"""
        suggestions = []
        
        # 识别技能过度集中的情况
        for skill_name, count in skill_counts.items():
            if count > 6:  # 超过一半的角色都有此技能
                suggestions.append({
                    "type": "diversification",
                    "skill": skill_name,
                    "issue": "技能过度集中",
                    "suggestion": f"考虑让部分角色发展其他互补技能，避免{skill_name}技能过度集中"
                })
        
        # 识别关键技能缺失
        critical_skills = ["system_architecture", "code_review", "technical_writing"]
        for skill in critical_skills:
            if skill_counts.get(skill, 0) < 2:
                suggestions.append({
                    "type": "critical_skill_development",
                    "skill": skill,
                    "issue": "关键技能覆盖不足",
                    "suggestion": f"优先培养更多角色的{skill}技能，确保团队关键能力"
                })
        
        # 识别技能质量问题
        for skill_name, proficiencies in skill_proficiencies.items():
            avg_proficiency = sum(proficiencies) / len(proficiencies)
            if avg_proficiency < 0.5 and len(proficiencies) > 2:
                suggestions.append({
                    "type": "quality_improvement",
                    "skill": skill_name,
                    "issue": f"技能质量偏低(平均{avg_proficiency:.1%})",
                    "suggestion": f"组织{skill_name}技能提升培训，提高整体熟练度"
                })
        
        return suggestions