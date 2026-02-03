"""
元学习协调器

协调整个团队技能元学习系统的运行，管理学习策略和知识迁移。
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import logging

from .models import (
    RoleSkillProfile, LearningEvent, LearningOutcome, 
    TeamSkillsSnapshot, Skill
)


class MetaLearningCoordinator:
    """元学习协调器"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # 学习策略配置
        self.learning_strategies = {
            "collaborative": {
                "description": "协作学习策略",
                "min_participants": 2,
                "effectiveness": 0.8
            },
            "mentoring": {
                "description": "导师制学习策略", 
                "min_participants": 2,
                "effectiveness": 0.9
            },
            "self_directed": {
                "description": "自主学习策略",
                "min_participants": 1,
                "effectiveness": 0.6
            },
            "project_based": {
                "description": "项目驱动学习策略",
                "min_participants": 1,
                "effectiveness": 0.7
            }
        }
        
        # 知识迁移规则
        self.transfer_rules = {
            "similar_roles": 0.8,      # 相似角色间的知识迁移效率
            "complementary_roles": 0.6, # 互补角色间的知识迁移效率
            "cross_domain": 0.4        # 跨领域知识迁移效率
        }
    
    def coordinate_skill_learning(self, 
                                role_profiles: Dict[str, RoleSkillProfile],
                                learning_goals: Dict[str, List[str]]) -> Dict[str, Any]:
        """协调技能学习"""
        coordination_plan = {
            "learning_groups": [],
            "mentoring_pairs": [],
            "individual_plans": [],
            "resource_allocation": {},
            "timeline": {}
        }
        
        try:
            # 1. 分析学习需求
            learning_needs = self._analyze_learning_needs(role_profiles, learning_goals)
            
            # 2. 形成学习小组
            learning_groups = self._form_learning_groups(role_profiles, learning_needs)
            coordination_plan["learning_groups"] = learning_groups
            
            # 3. 建立导师关系
            mentoring_pairs = self._establish_mentoring_pairs(role_profiles, learning_needs)
            coordination_plan["mentoring_pairs"] = mentoring_pairs
            
            # 4. 制定个人学习计划
            individual_plans = self._create_individual_plans(role_profiles, learning_needs)
            coordination_plan["individual_plans"] = individual_plans
            
            # 5. 分配学习资源
            resource_allocation = self._allocate_learning_resources(learning_groups, mentoring_pairs, individual_plans)
            coordination_plan["resource_allocation"] = resource_allocation
            
            # 6. 制定时间线
            timeline = self._create_learning_timeline(coordination_plan)
            coordination_plan["timeline"] = timeline
            
            self.logger.info("Successfully coordinated skill learning for team")
            
        except Exception as e:
            self.logger.error(f"Failed to coordinate skill learning: {e}")
        
        return coordination_plan
    
    def manage_knowledge_transfer(self, 
                                source_role: str,
                                target_role: str,
                                skill_name: str,
                                transfer_context: Dict[str, Any]) -> Dict[str, Any]:
        """管理知识迁移"""
        transfer_plan = {
            "transfer_efficiency": 0.0,
            "transfer_method": "",
            "estimated_time": 0,
            "success_probability": 0.0,
            "prerequisites": [],
            "milestones": []
        }
        
        try:
            # 1. 评估迁移可行性
            feasibility = self._assess_transfer_feasibility(source_role, target_role, skill_name)
            
            if feasibility["is_feasible"]:
                # 2. 确定迁移效率
                transfer_plan["transfer_efficiency"] = self._calculate_transfer_efficiency(
                    source_role, target_role, skill_name, transfer_context
                )
                
                # 3. 选择迁移方法
                transfer_plan["transfer_method"] = self._select_transfer_method(
                    source_role, target_role, transfer_plan["transfer_efficiency"]
                )
                
                # 4. 估算时间和成功概率
                transfer_plan["estimated_time"] = self._estimate_transfer_time(
                    skill_name, transfer_plan["transfer_efficiency"]
                )
                transfer_plan["success_probability"] = self._calculate_success_probability(
                    transfer_plan["transfer_efficiency"], transfer_context
                )
                
                # 5. 定义前置条件和里程碑
                transfer_plan["prerequisites"] = self._define_transfer_prerequisites(
                    source_role, target_role, skill_name
                )
                transfer_plan["milestones"] = self._create_transfer_milestones(
                    skill_name, transfer_plan["estimated_time"]
                )
            
            self.logger.info(f"Created knowledge transfer plan from {source_role} to {target_role} for {skill_name}")
            
        except Exception as e:
            self.logger.error(f"Failed to manage knowledge transfer: {e}")
        
        return transfer_plan
    
    def track_learning_progress(self, 
                              role_profiles: Dict[str, RoleSkillProfile],
                              learning_events: List[LearningEvent],
                              time_window: int = 30) -> Dict[str, Any]:
        """跟踪学习进度"""
        progress_report = {
            "overall_progress": {},
            "role_progress": {},
            "skill_progress": {},
            "learning_velocity": {},
            "bottlenecks": [],
            "recommendations": []
        }
        
        try:
            # 1. 计算整体进度
            progress_report["overall_progress"] = self._calculate_overall_progress(
                role_profiles, learning_events, time_window
            )
            
            # 2. 分析各角色进度
            for role_name, profile in role_profiles.items():
                role_events = [e for e in learning_events if e.role_name == role_name]
                progress_report["role_progress"][role_name] = self._analyze_role_progress(
                    profile, role_events, time_window
                )
            
            # 3. 分析技能进度
            progress_report["skill_progress"] = self._analyze_skill_progress(
                learning_events, time_window
            )
            
            # 4. 计算学习速度
            progress_report["learning_velocity"] = self._calculate_learning_velocity(
                learning_events, time_window
            )
            
            # 5. 识别瓶颈
            progress_report["bottlenecks"] = self._identify_learning_bottlenecks(
                role_profiles, learning_events
            )
            
            # 6. 生成改进建议
            progress_report["recommendations"] = self._generate_progress_recommendations(
                progress_report
            )
            
            self.logger.info("Successfully tracked learning progress")
            
        except Exception as e:
            self.logger.error(f"Failed to track learning progress: {e}")
        
        return progress_report
    
    def adapt_learning_strategies(self, 
                                progress_data: Dict[str, Any],
                                performance_metrics: Dict[str, float]) -> Dict[str, Any]:
        """适应学习策略"""
        adaptation_plan = {
            "strategy_adjustments": {},
            "resource_reallocation": {},
            "timeline_changes": {},
            "new_initiatives": [],
            "discontinued_approaches": []
        }
        
        try:
            # 1. 分析当前策略效果
            strategy_effectiveness = self._analyze_strategy_effectiveness(
                progress_data, performance_metrics
            )
            
            # 2. 识别需要调整的策略
            for strategy, effectiveness in strategy_effectiveness.items():
                if effectiveness < 0.6:  # 效果不佳的策略
                    adaptation_plan["strategy_adjustments"][strategy] = {
                        "current_effectiveness": effectiveness,
                        "proposed_changes": self._propose_strategy_improvements(strategy),
                        "expected_improvement": 0.2
                    }
            
            # 3. 重新分配资源
            adaptation_plan["resource_reallocation"] = self._optimize_resource_allocation(
                progress_data, strategy_effectiveness
            )
            
            # 4. 调整时间线
            adaptation_plan["timeline_changes"] = self._adjust_learning_timeline(
                progress_data, performance_metrics
            )
            
            # 5. 提出新举措
            adaptation_plan["new_initiatives"] = self._propose_new_initiatives(
                progress_data, performance_metrics
            )
            
            # 6. 识别需要停止的方法
            adaptation_plan["discontinued_approaches"] = self._identify_ineffective_approaches(
                strategy_effectiveness
            )
            
            self.logger.info("Successfully adapted learning strategies")
            
        except Exception as e:
            self.logger.error(f"Failed to adapt learning strategies: {e}")
        
        return adaptation_plan
    
    def _analyze_learning_needs(self, 
                              role_profiles: Dict[str, RoleSkillProfile],
                              learning_goals: Dict[str, List[str]]) -> Dict[str, Any]:
        """分析学习需求"""
        needs = {
            "skill_gaps": {},
            "priority_skills": [],
            "shared_learning_opportunities": [],
            "individual_needs": {}
        }
        
        # 收集所有技能缺口
        all_gaps = {}
        for role_name, profile in role_profiles.items():
            role_gaps = profile.skill_gaps
            all_gaps[role_name] = role_gaps
            
            # 提取优先技能
            for gap in role_gaps:
                if gap.priority > 0.7:
                    needs["priority_skills"].append({
                        "role": role_name,
                        "skill": gap.skill_name,
                        "priority": gap.priority
                    })
        
        needs["skill_gaps"] = all_gaps
        
        # 识别共同学习机会
        skill_demand = {}
        for role_name, gaps in all_gaps.items():
            for gap in gaps:
                if gap.skill_name not in skill_demand:
                    skill_demand[gap.skill_name] = []
                skill_demand[gap.skill_name].append(role_name)
        
        for skill, roles in skill_demand.items():
            if len(roles) >= 2:  # 2个或更多角色需要此技能
                needs["shared_learning_opportunities"].append({
                    "skill": skill,
                    "roles": roles,
                    "potential_group_size": len(roles)
                })
        
        return needs
    
    def _form_learning_groups(self, 
                            role_profiles: Dict[str, RoleSkillProfile],
                            learning_needs: Dict[str, Any]) -> List[Dict[str, Any]]:
        """形成学习小组"""
        groups = []
        
        for opportunity in learning_needs["shared_learning_opportunities"]:
            if opportunity["potential_group_size"] >= 2:
                group = {
                    "skill": opportunity["skill"],
                    "members": opportunity["roles"],
                    "group_size": len(opportunity["roles"]),
                    "learning_strategy": "collaborative",
                    "estimated_duration": "4-6周",
                    "meeting_frequency": "每周1次",
                    "success_metrics": [
                        "所有成员达到基础熟练度",
                        "能够相互指导和支持",
                        "在实际项目中应用技能"
                    ]
                }
                groups.append(group)
        
        return groups
    
    def _establish_mentoring_pairs(self, 
                                 role_profiles: Dict[str, RoleSkillProfile],
                                 learning_needs: Dict[str, Any]) -> List[Dict[str, Any]]:
        """建立导师关系"""
        pairs = []
        
        # 为每个优先技能寻找潜在导师
        for priority_skill in learning_needs["priority_skills"]:
            skill_name = priority_skill["skill"]
            learner_role = priority_skill["role"]
            
            # 寻找拥有此技能的其他角色
            potential_mentors = []
            for role_name, profile in role_profiles.items():
                if role_name != learner_role:
                    skill = profile.get_skill_by_name(skill_name)
                    if skill and skill.proficiency > 0.7:
                        potential_mentors.append({
                            "role": role_name,
                            "proficiency": skill.proficiency,
                            "experience": skill.usage_frequency
                        })
            
            # 选择最佳导师
            if potential_mentors:
                best_mentor = max(potential_mentors, key=lambda x: x["proficiency"] + x["experience"] * 0.1)
                pair = {
                    "skill": skill_name,
                    "mentor": best_mentor["role"],
                    "learner": learner_role,
                    "mentor_proficiency": best_mentor["proficiency"],
                    "learning_strategy": "mentoring",
                    "estimated_duration": "6-8周",
                    "meeting_frequency": "每周2次",
                    "success_metrics": [
                        "学习者技能熟练度提升50%",
                        "能够独立完成相关任务",
                        "导师教学能力提升"
                    ]
                }
                pairs.append(pair)
        
        return pairs
    
    def _create_individual_plans(self, 
                               role_profiles: Dict[str, RoleSkillProfile],
                               learning_needs: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """制定个人学习计划"""
        individual_plans = {}
        
        for role_name, profile in role_profiles.items():
            plan = {
                "role": role_name,
                "learning_objectives": [],
                "self_directed_skills": [],
                "project_based_skills": [],
                "timeline": "3个月",
                "weekly_commitment": "5-8小时"
            }
            
            # 识别适合自主学习的技能
            for gap in profile.skill_gaps:
                if gap.priority < 0.7:  # 非高优先级技能适合自主学习
                    plan["self_directed_skills"].append({
                        "skill": gap.skill_name,
                        "current_level": gap.current_level.value,
                        "target_level": gap.required_level.value,
                        "learning_path": gap.learning_path,
                        "estimated_time": gap.estimated_time
                    })
            
            # 设定学习目标
            plan["learning_objectives"] = [
                f"提升{len(plan['self_directed_skills'])}项技能",
                "参与至少1个技能学习小组",
                "完成2个实践项目",
                "分享学习经验给团队"
            ]
            
            individual_plans[role_name] = plan
        
        return individual_plans
    
    def _allocate_learning_resources(self, 
                                   learning_groups: List[Dict[str, Any]],
                                   mentoring_pairs: List[Dict[str, Any]],
                                   individual_plans: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """分配学习资源"""
        allocation = {
            "time_allocation": {},
            "budget_allocation": {},
            "tool_requirements": [],
            "space_requirements": [],
            "external_resources": []
        }
        
        # 时间分配
        total_group_time = len(learning_groups) * 2  # 每组每周2小时
        total_mentoring_time = len(mentoring_pairs) * 3  # 每对每周3小时
        total_individual_time = len(individual_plans) * 6  # 每人每周6小时
        
        allocation["time_allocation"] = {
            "group_learning": f"{total_group_time}小时/周",
            "mentoring": f"{total_mentoring_time}小时/周", 
            "individual_learning": f"{total_individual_time}小时/周",
            "total_weekly_commitment": f"{total_group_time + total_mentoring_time + total_individual_time}小时/周"
        }
        
        # 工具需求
        required_tools = set()
        for group in learning_groups:
            if "programming" in group["skill"]:
                required_tools.add("开发环境")
                required_tools.add("代码协作工具")
        
        allocation["tool_requirements"] = list(required_tools)
        
        return allocation
    
    def _create_learning_timeline(self, coordination_plan: Dict[str, Any]) -> Dict[str, Any]:
        """创建学习时间线"""
        timeline = {
            "phase_1": {
                "duration": "第1-2周",
                "activities": [
                    "组建学习小组",
                    "建立导师关系",
                    "制定个人学习计划"
                ]
            },
            "phase_2": {
                "duration": "第3-8周", 
                "activities": [
                    "执行小组学习",
                    "进行导师指导",
                    "开展自主学习"
                ]
            },
            "phase_3": {
                "duration": "第9-12周",
                "activities": [
                    "项目实践应用",
                    "技能评估验证",
                    "经验分享总结"
                ]
            }
        }
        
        return timeline
    
    def _calculate_overall_progress(self, 
                                  role_profiles: Dict[str, RoleSkillProfile],
                                  learning_events: List[LearningEvent],
                                  time_window: int) -> Dict[str, float]:
        """计算整体进度"""
        cutoff_date = datetime.now() - timedelta(days=time_window)
        recent_events = [e for e in learning_events if e.timestamp >= cutoff_date]
        
        if not recent_events:
            return {"progress_rate": 0.0, "success_rate": 0.0, "activity_level": 0.0}
        
        success_events = [e for e in recent_events if e.outcome == LearningOutcome.SUCCESS]
        success_rate = len(success_events) / len(recent_events)
        
        # 计算活跃度
        active_roles = len(set(e.role_name for e in recent_events))
        activity_level = active_roles / len(role_profiles) if role_profiles else 0
        
        # 计算进度率（基于技能提升）
        skill_improvements = 0
        for event in success_events:
            if event.event_type.value in ["skill_learning", "improvement"]:
                skill_improvements += 1
        
        progress_rate = skill_improvements / len(role_profiles) if role_profiles else 0
        
        return {
            "progress_rate": progress_rate,
            "success_rate": success_rate,
            "activity_level": activity_level
        }
    
    def _analyze_role_progress(self, 
                             profile: RoleSkillProfile,
                             role_events: List[LearningEvent],
                             time_window: int) -> Dict[str, Any]:
        """分析角色进度"""
        if not role_events:
            return {"status": "inactive", "progress": 0.0}
        
        success_events = [e for e in role_events if e.outcome == LearningOutcome.SUCCESS]
        success_rate = len(success_events) / len(role_events)
        
        # 分析技能发展
        skills_worked_on = set(e.skill_id for e in role_events)
        skill_progress = len(skills_worked_on) / max(1, len(profile.get_all_skills()))
        
        status = "excellent" if success_rate > 0.8 else "good" if success_rate > 0.6 else "needs_improvement"
        
        return {
            "status": status,
            "success_rate": success_rate,
            "skill_progress": skill_progress,
            "active_skills": len(skills_worked_on),
            "total_events": len(role_events)
        }
    
    def _analyze_skill_progress(self, learning_events: List[LearningEvent], time_window: int) -> Dict[str, Any]:
        """分析技能进度"""
        cutoff_date = datetime.now() - timedelta(days=time_window)
        recent_events = [e for e in learning_events if e.timestamp >= cutoff_date]
        
        skill_stats = {}
        for event in recent_events:
            skill_id = event.skill_id
            if skill_id not in skill_stats:
                skill_stats[skill_id] = {"total": 0, "success": 0}
            
            skill_stats[skill_id]["total"] += 1
            if event.outcome == LearningOutcome.SUCCESS:
                skill_stats[skill_id]["success"] += 1
        
        # 计算每个技能的成功率
        skill_progress = {}
        for skill_id, stats in skill_stats.items():
            success_rate = stats["success"] / stats["total"] if stats["total"] > 0 else 0
            skill_progress[skill_id] = {
                "success_rate": success_rate,
                "activity_level": stats["total"],
                "status": "progressing" if success_rate > 0.6 else "struggling"
            }
        
        return skill_progress
    
    def _calculate_learning_velocity(self, learning_events: List[LearningEvent], time_window: int) -> Dict[str, float]:
        """计算学习速度"""
        cutoff_date = datetime.now() - timedelta(days=time_window)
        recent_events = [e for e in learning_events if e.timestamp >= cutoff_date]
        
        if not recent_events:
            return {"events_per_day": 0.0, "skills_per_week": 0.0}
        
        events_per_day = len(recent_events) / time_window
        unique_skills = len(set(e.skill_id for e in recent_events))
        skills_per_week = unique_skills / (time_window / 7)
        
        return {
            "events_per_day": events_per_day,
            "skills_per_week": skills_per_week
        }
    
    def _identify_learning_bottlenecks(self, 
                                     role_profiles: Dict[str, RoleSkillProfile],
                                     learning_events: List[LearningEvent]) -> List[Dict[str, Any]]:
        """识别学习瓶颈"""
        bottlenecks = []
        
        # 识别长期无进展的技能
        skill_last_success = {}
        for event in learning_events:
            if event.outcome == LearningOutcome.SUCCESS:
                skill_last_success[event.skill_id] = event.timestamp
        
        for role_name, profile in role_profiles.items():
            for skill in profile.get_all_skills():
                last_success = skill_last_success.get(skill.name)
                if not last_success or (datetime.now() - last_success).days > 30:
                    bottlenecks.append({
                        "type": "stagnant_skill",
                        "role": role_name,
                        "skill": skill.name,
                        "issue": "技能长期无进展",
                        "days_since_success": (datetime.now() - last_success).days if last_success else 999
                    })
        
        return bottlenecks
    
    def _generate_progress_recommendations(self, progress_report: Dict[str, Any]) -> List[str]:
        """生成进度改进建议"""
        recommendations = []
        
        overall_progress = progress_report.get("overall_progress", {})
        success_rate = overall_progress.get("success_rate", 0)
        activity_level = overall_progress.get("activity_level", 0)
        
        if success_rate < 0.6:
            recommendations.append("整体学习成功率偏低，建议调整学习方法和难度")
        
        if activity_level < 0.5:
            recommendations.append("团队学习活跃度不足，建议增加激励措施")
        
        bottlenecks = progress_report.get("bottlenecks", [])
        if len(bottlenecks) > 3:
            recommendations.append("存在多个学习瓶颈，建议重点解决阻塞问题")
        
        return recommendations
    
    def _analyze_strategy_effectiveness(self, 
                                      progress_data: Dict[str, Any],
                                      performance_metrics: Dict[str, float]) -> Dict[str, float]:
        """分析策略效果"""
        # 简化实现：基于整体指标评估策略效果
        overall_success = progress_data.get("overall_progress", {}).get("success_rate", 0.5)
        
        return {
            "collaborative": overall_success * 0.9,  # 协作学习通常效果较好
            "mentoring": overall_success * 1.1,     # 导师制效果最好
            "self_directed": overall_success * 0.7,  # 自主学习效果一般
            "project_based": overall_success * 0.8   # 项目驱动效果较好
        }
    
    def _propose_strategy_improvements(self, strategy: str) -> List[str]:
        """提出策略改进建议"""
        improvements = {
            "collaborative": [
                "增加小组讨论频率",
                "引入同伴评估机制",
                "设置小组竞赛活动"
            ],
            "mentoring": [
                "提供导师培训",
                "建立导师激励机制",
                "定期评估导师效果"
            ],
            "self_directed": [
                "提供更多学习资源",
                "增加进度检查点",
                "建立学习伙伴制度"
            ],
            "project_based": [
                "选择更贴近实际的项目",
                "增加项目指导支持",
                "建立项目成果展示机制"
            ]
        }
        
        return improvements.get(strategy, ["优化学习内容和方法"])
    
    def _optimize_resource_allocation(self, 
                                    progress_data: Dict[str, Any],
                                    strategy_effectiveness: Dict[str, float]) -> Dict[str, Any]:
        """优化资源分配"""
        # 将更多资源分配给效果好的策略
        total_effectiveness = sum(strategy_effectiveness.values())
        
        allocation = {}
        for strategy, effectiveness in strategy_effectiveness.items():
            allocation[strategy] = {
                "resource_percentage": (effectiveness / total_effectiveness) * 100,
                "recommended_adjustment": "increase" if effectiveness > 0.7 else "maintain" if effectiveness > 0.5 else "decrease"
            }
        
        return allocation
    
    def _adjust_learning_timeline(self, 
                                progress_data: Dict[str, Any],
                                performance_metrics: Dict[str, float]) -> Dict[str, Any]:
        """调整学习时间线"""
        current_progress = progress_data.get("overall_progress", {}).get("progress_rate", 0.5)
        
        if current_progress > 0.8:
            return {"adjustment": "accelerate", "factor": 0.8, "reason": "进度超前"}
        elif current_progress < 0.3:
            return {"adjustment": "extend", "factor": 1.3, "reason": "进度滞后"}
        else:
            return {"adjustment": "maintain", "factor": 1.0, "reason": "进度正常"}
    
    def _propose_new_initiatives(self, 
                               progress_data: Dict[str, Any],
                               performance_metrics: Dict[str, float]) -> List[Dict[str, Any]]:
        """提出新举措"""
        initiatives = []
        
        activity_level = progress_data.get("overall_progress", {}).get("activity_level", 0.5)
        
        if activity_level < 0.5:
            initiatives.append({
                "name": "学习激励计划",
                "description": "建立学习积分和奖励机制",
                "expected_impact": "提高学习积极性"
            })
        
        success_rate = progress_data.get("overall_progress", {}).get("success_rate", 0.5)
        
        if success_rate < 0.6:
            initiatives.append({
                "name": "学习支持小组",
                "description": "为学习困难的成员提供额外支持",
                "expected_impact": "提高学习成功率"
            })
        
        return initiatives
    
    def _identify_ineffective_approaches(self, strategy_effectiveness: Dict[str, float]) -> List[str]:
        """识别无效方法"""
        ineffective = []
        
        for strategy, effectiveness in strategy_effectiveness.items():
            if effectiveness < 0.4:
                ineffective.append(f"{strategy}策略效果不佳，建议暂停或重新设计")
        
        return ineffective