#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
团队技能元学习系统测试脚本

测试Skills元学习系统的各项功能。
"""

import sys
import os
from pathlib import Path
from datetime import datetime

# 添加src目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from team_skills_meta_learning import (
    TeamSkillsMetaLearningSystem, LearningEventType, LearningOutcome
)


class SkillsMetaLearningTester:
    """技能元学习系统测试器"""
    
    def __init__(self):
        self.system = None
        self.test_results = []
    
    def run_all_tests(self):
        """运行所有测试"""
        print("🧠 开始团队技能元学习系统测试...")
        print("="*60)
        
        try:
            # 1. 系统初始化测试
            self._test_system_initialization()
            
            # 2. 技能识别测试
            self._test_skill_recognition()
            
            # 3. 学习模式分析测试
            self._test_pattern_analysis()
            
            # 4. 技能配置优化测试
            self._test_config_optimization()
            
            # 5. 元学习协调测试
            self._test_meta_coordination()
            
            # 6. 团队快照测试
            self._test_team_snapshot()
            
            # 7. 输出结果
            self._print_results()
            
        except Exception as e:
            print(f"❌ 测试过程中发生错误: {e}")
            return False
        
        return all(result['passed'] for result in self.test_results)
    
    def _test_system_initialization(self):
        """测试系统初始化"""
        print("\n🔧 测试1: 系统初始化")
        
        try:
            self.system = TeamSkillsMetaLearningSystem(
                storage_path=".kiro/team_skills",
                enable_learning=True
            )
            
            # 验证组件初始化
            assert self.system.skill_recognition is not None
            assert self.system.pattern_analyzer is not None
            assert self.system.config_optimizer is not None
            assert self.system.meta_coordinator is not None
            
            # 验证团队角色初始化
            assert len(self.system.team_roles) == 12
            assert len(self.system.role_profiles) == 12
            
            # 验证角色技能画像
            for role in self.system.team_roles:
                profile = self.system.role_profiles[role]
                assert profile.role_name == role
                print(f"  ✅ {role}: {len(profile.get_all_skills())} 项基础技能")
            
            print("✅ 系统初始化成功")
            self._record_test_result("initialization", True, "系统初始化成功")
            
        except Exception as e:
            print(f"❌ 初始化失败: {e}")
            self._record_test_result("initialization", False, str(e))
            raise
    
    def _test_skill_recognition(self):
        """测试技能识别"""
        print("\n🔍 测试2: 技能识别")
        
        try:
            # 测试代码技能识别
            python_code = '''
def calculate_fibonacci(n):
    """计算斐波那契数列"""
    if n <= 1:
        return n
    return calculate_fibonacci(n-1) + calculate_fibonacci(n-2)

class DataProcessor:
    def __init__(self):
        self.data = []
    
    async def process_data(self):
        await self.fetch_data()
        return self.analyze()
'''
            
            code_skills = self.system.analyze_code_skills(
                "Full-Stack Engineer", python_code, "fibonacci.py"
            )
            
            print(f"  🔍 从Python代码中识别出 {len(code_skills)} 项技能:")
            for skill in code_skills:
                print(f"    - {skill.name} (熟练度: {skill.proficiency:.2f})")
            
            # 测试文档技能识别
            markdown_doc = '''
# API文档

## 概述
这是一个RESTful API的文档。

## 端点

### GET /users
获取用户列表

**参数:**
- `page`: 页码
- `limit`: 每页数量

**返回:**
```json
{
  "users": [...],
  "total": 100
}
```

### POST /users
创建新用户
'''
            
            doc_skills = self.system.analyze_document_skills(
                "Product Manager", markdown_doc, "api_doc"
            )
            
            print(f"  📝 从API文档中识别出 {len(doc_skills)} 项技能:")
            for skill in doc_skills:
                print(f"    - {skill.name} (熟练度: {skill.proficiency:.2f})")
            
            # 测试代码审查技能识别
            review_content = '''
LGTM! 这个实现看起来不错。

几个建议:
1. 考虑添加错误处理
2. 可以优化算法复杂度
3. 建议添加单元测试
4. 文档可以更详细一些

总体来说代码质量很好，approve!
'''
            
            review_skills = self.system.analyze_review_skills(
                "Code Review Specialist", review_content, {"file_path": "fibonacci.py"}
            )
            
            print(f"  👀 从代码审查中识别出 {len(review_skills)} 项技能:")
            for skill in review_skills:
                print(f"    - {skill.name} (熟练度: {skill.proficiency:.2f})")
            
            assert len(code_skills) > 0
            assert len(doc_skills) > 0
            assert len(review_skills) > 0
            
            print("✅ 技能识别功能正常")
            self._record_test_result("skill_recognition", True, "技能识别功能正常")
            
        except Exception as e:
            print(f"❌ 技能识别测试失败: {e}")
            self._record_test_result("skill_recognition", False, str(e))
    
    def _test_pattern_analysis(self):
        """测试学习模式分析"""
        print("\n📊 测试3: 学习模式分析")
        
        try:
            # 记录一些学习事件
            events = []
            
            # 成功事件
            for i in range(5):
                event_id = self.system.record_learning_event(
                    role="Full-Stack Engineer",
                    skill_id="python_programming",
                    event_type=LearningEventType.SKILL_USAGE,
                    outcome=LearningOutcome.SUCCESS,
                    context={"task": "coding", "complexity": "medium"}
                )
                events.append(event_id)
            
            # 失败事件
            for i in range(2):
                event_id = self.system.record_learning_event(
                    role="Full-Stack Engineer",
                    skill_id="javascript_programming",
                    event_type=LearningEventType.SKILL_LEARNING,
                    outcome=LearningOutcome.FAILURE,
                    context={"task": "learning", "complexity": "high"}
                )
                events.append(event_id)
            
            print(f"  📝 记录了 {len(events)} 个学习事件")
            
            # 分析成功模式
            success_patterns = self.system.identify_success_patterns("Full-Stack Engineer")
            print(f"  ✅ 识别成功模式: {len(success_patterns.get('patterns', {}))} 种")
            
            # 分析失败模式
            failure_patterns = self.system.analyze_failure_patterns("Full-Stack Engineer")
            print(f"  ❌ 识别失败模式: {len(failure_patterns.get('patterns', {}))} 种")
            
            # 发现技能关联
            correlations = self.system.discover_skill_correlations("Full-Stack Engineer")
            print(f"  🔗 发现技能关联: {len(correlations)} 组")
            
            print("✅ 学习模式分析功能正常")
            self._record_test_result("pattern_analysis", True, "学习模式分析功能正常")
            
        except Exception as e:
            print(f"❌ 学习模式分析测试失败: {e}")
            self._record_test_result("pattern_analysis", False, str(e))
    
    def _test_config_optimization(self):
        """测试技能配置优化"""
        print("\n⚙️ 测试4: 技能配置优化")
        
        try:
            # 识别技能缺口
            skill_gaps = self.system.identify_skill_gaps("Full-Stack Engineer")
            print(f"  🔍 识别技能缺口: {len(skill_gaps)} 个")
            
            for gap in skill_gaps[:3]:  # 显示前3个
                print(f"    - {gap.skill_name} (优先级: {gap.priority:.2f})")
            
            # 推荐技能发展
            recommendations = self.system.recommend_skill_development("Full-Stack Engineer")
            print(f"  💡 技能发展推荐: {len(recommendations)} 项")
            
            for rec in recommendations[:2]:  # 显示前2个
                print(f"    - {rec['skill_name']} (优先级: {rec['priority']:.2f})")
            
            # 优化团队平衡
            team_balance = self.system.optimize_team_balance()
            print(f"  ⚖️ 团队平衡分析:")
            print(f"    - 团队优势: {len(team_balance.get('team_strengths', []))} 项")
            print(f"    - 团队弱点: {len(team_balance.get('team_weaknesses', []))} 项")
            print(f"    - 协作机会: {len(team_balance.get('collaboration_opportunities', []))} 个")
            
            print("✅ 技能配置优化功能正常")
            self._record_test_result("config_optimization", True, "技能配置优化功能正常")
            
        except Exception as e:
            print(f"❌ 技能配置优化测试失败: {e}")
            self._record_test_result("config_optimization", False, str(e))
    
    def _test_meta_coordination(self):
        """测试元学习协调"""
        print("\n🎯 测试5: 元学习协调")
        
        try:
            # 协调技能学习
            learning_goals = {
                "Full-Stack Engineer": ["docker_containerization", "kubernetes"],
                "DevOps Engineer": ["python_programming", "monitoring"],
                "Security Engineer": ["penetration_testing", "compliance"]
            }
            
            coordination_plan = self.system.meta_coordinator.coordinate_skill_learning(
                self.system.role_profiles, learning_goals
            )
            
            print(f"  📋 学习协调计划:")
            print(f"    - 学习小组: {len(coordination_plan.get('learning_groups', []))} 个")
            print(f"    - 导师配对: {len(coordination_plan.get('mentoring_pairs', []))} 对")
            print(f"    - 个人计划: {len(coordination_plan.get('individual_plans', {}))} 个")
            
            # 跟踪学习进度
            progress_report = self.system.meta_coordinator.track_learning_progress(
                self.system.role_profiles, self.system.learning_events
            )
            
            overall_progress = progress_report.get("overall_progress", {})
            print(f"  📈 学习进度跟踪:")
            print(f"    - 整体成功率: {overall_progress.get('success_rate', 0):.2%}")
            print(f"    - 活跃度: {overall_progress.get('activity_level', 0):.2%}")
            print(f"    - 瓶颈数量: {len(progress_report.get('bottlenecks', []))}")
            
            print("✅ 元学习协调功能正常")
            self._record_test_result("meta_coordination", True, "元学习协调功能正常")
            
        except Exception as e:
            print(f"❌ 元学习协调测试失败: {e}")
            self._record_test_result("meta_coordination", False, str(e))
    
    def _test_team_snapshot(self):
        """测试团队快照"""
        print("\n📸 测试6: 团队快照")
        
        try:
            # 获取团队快照
            snapshot = self.system.get_team_snapshot()
            
            print(f"  📊 团队快照信息:")
            print(f"    - 快照ID: {snapshot.snapshot_id}")
            print(f"    - 角色数量: {len(snapshot.role_profiles)}")
            print(f"    - 团队指标: {len(snapshot.team_metrics)} 项")
            print(f"    - 技能分布: {len(snapshot.skill_distribution)} 类")
            
            # 显示团队指标
            for metric, value in snapshot.team_metrics.items():
                print(f"      - {metric}: {value}")
            
            # 获取系统统计
            stats = self.system.get_system_stats()
            print(f"  📈 系统统计:")
            print(f"    - 总角色数: {stats.get('total_roles', 0)}")
            print(f"    - 总技能数: {stats.get('total_skills', 0)}")
            print(f"    - 学习事件数: {stats.get('total_learning_events', 0)}")
            print(f"    - 平均熟练度: {stats.get('average_proficiency', 0):.2%}")
            
            assert snapshot.snapshot_id != "error"
            assert len(snapshot.role_profiles) > 0
            
            print("✅ 团队快照功能正常")
            self._record_test_result("team_snapshot", True, "团队快照功能正常")
            
        except Exception as e:
            print(f"❌ 团队快照测试失败: {e}")
            self._record_test_result("team_snapshot", False, str(e))
    
    def _record_test_result(self, test_name: str, passed: bool, message: str):
        """记录测试结果"""
        self.test_results.append({
            "test_name": test_name,
            "passed": passed,
            "message": message,
            "timestamp": datetime.now().isoformat()
        })
    
    def _print_results(self):
        """输出测试结果"""
        print("\n" + "="*60)
        print("📊 团队技能元学习系统测试结果")
        print("="*60)
        
        passed_tests = sum(1 for result in self.test_results if result['passed'])
        total_tests = len(self.test_results)
        
        print(f"总测试数: {total_tests}")
        print(f"通过: {passed_tests}")
        print(f"失败: {total_tests - passed_tests}")
        print(f"通过率: {(passed_tests/total_tests*100):.1f}%")
        
        print("\n📋 详细结果:")
        for result in self.test_results:
            status = "✅" if result['passed'] else "❌"
            print(f"  {status} {result['test_name']}: {result['message']}")
        
        print("\n" + "="*60)
        
        if passed_tests == total_tests:
            print("🎉 所有测试通过！团队技能元学习系统运行正常！")
        else:
            print("💥 部分测试失败，请检查错误信息")


def main():
    """主函数"""
    tester = SkillsMetaLearningTester()
    success = tester.run_all_tests()
    
    return 0 if success else 1


if __name__ == "__main__":
    exit(main())