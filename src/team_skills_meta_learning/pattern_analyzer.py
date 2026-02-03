"""
学习模式分析器

分析团队成员的学习模式，识别成功和失败的模式。
"""

from typing import List, Dict, Any
from collections import defaultdict, Counter
from datetime import datetime, timedelta

from .models import Skill, LearningEvent, LearningOutcome


class LearningPatternAnalyzer:
    """学习模式分析器"""
    
    def __init__(self):
        pass
    
    def identify_success_patterns(self, success_events: List[LearningEvent]) -> Dict[str, Any]:
        """识别成功模式"""
        if not success_events:
            return {"patterns": [], "insights": []}
        
        patterns = {}
        
        # 1. 分析成功的技能类型
        skill_success_count = Counter(event.skill_id for event in success_events)
        patterns["successful_skills"] = dict(skill_success_count.most_common(5))
        
        # 2. 分析成功的事件类型
        event_type_count = Counter(event.event_type.value for event in success_events)
        patterns["successful_event_types"] = dict(event_type_count.most_common())
        
        # 3. 分析成功的时间模式
        hour_success = defaultdict(int)
        day_success = defaultdict(int)
        
        for event in success_events:
            hour_success[event.timestamp.hour] += 1
            day_success[event.timestamp.strftime("%A")] += 1
        
        patterns["successful_hours"] = dict(sorted(hour_success.items(), key=lambda x: x[1], reverse=True)[:3])
        patterns["successful_days"] = dict(sorted(day_success.items(), key=lambda x: x[1], reverse=True)[:3])
        
        # 4. 分析成功的上下文模式
        context_patterns = defaultdict(int)
        for event in success_events:
            for key, value in event.context.items():
                if isinstance(value, str):
                    context_patterns[f"{key}:{value}"] += 1
        
        patterns["successful_contexts"] = dict(sorted(context_patterns.items(), key=lambda x: x[1], reverse=True)[:5])
        
        # 5. 生成洞察
        insights = self._generate_success_insights(patterns, len(success_events))
        
        return {
            "patterns": patterns,
            "insights": insights,
            "total_success_events": len(success_events),
            "analysis_timestamp": datetime.now().isoformat()
        }
    
    def analyze_failure_patterns(self, failure_events: List[LearningEvent]) -> Dict[str, Any]:
        """分析失败模式"""
        if not failure_events:
            return {"patterns": [], "insights": []}
        
        patterns = {}
        
        # 1. 分析失败的技能类型
        skill_failure_count = Counter(event.skill_id for event in failure_events)
        patterns["problematic_skills"] = dict(skill_failure_count.most_common(5))
        
        # 2. 分析失败的事件类型
        event_type_count = Counter(event.event_type.value for event in failure_events)
        patterns["problematic_event_types"] = dict(event_type_count.most_common())
        
        # 3. 分析失败的时间模式
        hour_failure = defaultdict(int)
        day_failure = defaultdict(int)
        
        for event in failure_events:
            hour_failure[event.timestamp.hour] += 1
            day_failure[event.timestamp.strftime("%A")] += 1
        
        patterns["problematic_hours"] = dict(sorted(hour_failure.items(), key=lambda x: x[1], reverse=True)[:3])
        patterns["problematic_days"] = dict(sorted(day_failure.items(), key=lambda x: x[1], reverse=True)[:3])
        
        # 4. 分析失败的上下文模式
        context_patterns = defaultdict(int)
        for event in failure_events:
            for key, value in event.context.items():
                if isinstance(value, str):
                    context_patterns[f"{key}:{value}"] += 1
        
        patterns["problematic_contexts"] = dict(sorted(context_patterns.items(), key=lambda x: x[1], reverse=True)[:5])
        
        # 5. 生成改进建议
        improvements = self._generate_improvement_suggestions(patterns, len(failure_events))
        
        return {
            "patterns": patterns,
            "improvements": improvements,
            "total_failure_events": len(failure_events),
            "analysis_timestamp": datetime.now().isoformat()
        }
    
    def discover_skill_correlations(self, skills: List[Skill]) -> Dict[str, List[str]]:
        """发现技能关联"""
        correlations = {}
        
        if len(skills) < 2:
            return correlations
        
        # 修复：确保技能数据一致性
        valid_skills = [skill for skill in skills if skill and hasattr(skill, 'name') and skill.name]
        
        if len(valid_skills) < 2:
            return correlations
        
        # 基于技能标签发现关联
        skill_tags = {}
        for skill in valid_skills:
            # 修复：安全处理标签数据
            tags = getattr(skill, 'tags', []) or []
            skill_tags[skill.name] = set(tags) if isinstance(tags, (list, tuple)) else set()
        
        # 计算技能间的标签重叠度
        for i, skill1 in enumerate(valid_skills):
            related_skills = []
            
            for j, skill2 in enumerate(valid_skills):
                if i != j:
                    tags1 = skill_tags.get(skill1.name, set())
                    tags2 = skill_tags.get(skill2.name, set())
                    
                    if tags1 and tags2:
                        # 修复：防止除零错误
                        union_size = len(tags1 | tags2)
                        if union_size > 0:
                            overlap = len(tags1 & tags2) / union_size
                            if overlap > 0.3:  # 30%以上重叠认为相关
                                related_skills.append(skill2.name)
            
            if related_skills:
                correlations[skill1.name] = related_skills
        
        # 基于使用频率发现关联 - 修复数据一致性
        high_usage_skills = []
        for skill in valid_skills:
            usage_freq = getattr(skill, 'usage_frequency', 0) or 0
            if usage_freq > 5:
                high_usage_skills.append(skill.name)
        
        if len(high_usage_skills) > 1:
            correlations["high_usage_cluster"] = high_usage_skills
        
        # 基于成功率发现关联 - 修复数据一致性
        high_success_skills = []
        for skill in valid_skills:
            success_rate = getattr(skill, 'success_rate', 0.0) or 0.0
            if success_rate > 0.8:
                high_success_skills.append(skill.name)
        
        if len(high_success_skills) > 1:
            correlations["high_success_cluster"] = high_success_skills
        
        return correlations
    
    def generate_learning_insights(self, all_events: List[LearningEvent]) -> List[str]:
        """生成学习洞察"""
        insights = []
        
        if not all_events:
            return ["暂无足够的学习数据生成洞察"]
        
        # 按结果分类事件
        success_events = [e for e in all_events if e.outcome == LearningOutcome.SUCCESS]
        failure_events = [e for e in all_events if e.outcome == LearningOutcome.FAILURE]
        
        success_rate = len(success_events) / len(all_events) if all_events else 0
        
        # 整体成功率洞察
        if success_rate > 0.8:
            insights.append(f"学习表现优秀，成功率达到{success_rate:.1%}")
        elif success_rate > 0.6:
            insights.append(f"学习表现良好，成功率为{success_rate:.1%}")
        else:
            insights.append(f"学习成功率较低({success_rate:.1%})，需要改进学习策略")
        
        # 技能分布洞察
        skill_distribution = Counter(event.skill_id for event in all_events)
        most_practiced = skill_distribution.most_common(1)
        if most_practiced:
            insights.append(f"最常练习的技能是'{most_practiced[0][0]}'，共{most_practiced[0][1]}次")
        
        # 时间模式洞察
        recent_events = [e for e in all_events if e.timestamp >= datetime.now() - timedelta(days=7)]
        if len(recent_events) > len(all_events) * 0.5:
            insights.append("最近一周学习活跃度很高")
        elif len(recent_events) < len(all_events) * 0.1:
            insights.append("最近学习活跃度较低，建议增加学习频率")
        
        # 学习类型洞察
        event_types = Counter(event.event_type.value for event in all_events)
        dominant_type = event_types.most_common(1)
        if dominant_type:
            insights.append(f"主要的学习方式是'{dominant_type[0][0]}'")
        
        return insights
    
    def _generate_success_insights(self, patterns: Dict[str, Any], total_events: int) -> List[str]:
        """生成成功模式洞察"""
        insights = []
        
        # 技能洞察
        if "successful_skills" in patterns and patterns["successful_skills"]:
            top_skill = list(patterns["successful_skills"].keys())[0]
            insights.append(f"在'{top_skill}'技能上表现最佳")
        
        # 时间洞察
        if "successful_hours" in patterns and patterns["successful_hours"]:
            best_hour = list(patterns["successful_hours"].keys())[0]
            insights.append(f"在{best_hour}点时学习效果最好")
        
        if "successful_days" in patterns and patterns["successful_days"]:
            best_day = list(patterns["successful_days"].keys())[0]
            insights.append(f"在{best_day}的学习成功率最高")
        
        # 上下文洞察
        if "successful_contexts" in patterns and patterns["successful_contexts"]:
            top_context = list(patterns["successful_contexts"].keys())[0]
            insights.append(f"在'{top_context}'环境下表现最佳")
        
        return insights
    
    def _generate_improvement_suggestions(self, patterns: Dict[str, Any], total_events: int) -> List[str]:
        """生成改进建议"""
        suggestions = []
        
        # 技能改进建议
        if "problematic_skills" in patterns and patterns["problematic_skills"]:
            problem_skill = list(patterns["problematic_skills"].keys())[0]
            suggestions.append(f"需要重点改进'{problem_skill}'技能的学习方法")
        
        # 时间改进建议
        if "problematic_hours" in patterns and patterns["problematic_hours"]:
            problem_hour = list(patterns["problematic_hours"].keys())[0]
            suggestions.append(f"避免在{problem_hour}点进行复杂的学习任务")
        
        if "problematic_days" in patterns and patterns["problematic_days"]:
            problem_day = list(patterns["problematic_days"].keys())[0]
            suggestions.append(f"在{problem_day}需要调整学习策略")
        
        # 上下文改进建议
        if "problematic_contexts" in patterns and patterns["problematic_contexts"]:
            problem_context = list(patterns["problematic_contexts"].keys())[0]
            suggestions.append(f"在'{problem_context}'环境下需要额外支持")
        
        return suggestions