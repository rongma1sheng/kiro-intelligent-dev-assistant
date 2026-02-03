#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试智能开发支持功能
验证错误诊断、任务分配、生命周期管理的具体功能
"""

import sys
import os
from datetime import datetime
from pathlib import Path

# 设置UTF-8编码（Windows兼容）
if sys.platform.startswith('win'):
    os.environ['PYTHONIOENCODING'] = 'utf-8'

# 导入智能开发支持系统
sys.path.append('scripts/utilities')
from intelligent_development_support_integrated import IntelligentDevelopmentSupport

class IntelligentSupportFeatureTester:
    def __init__(self):
        self.support_system = IntelligentDevelopmentSupport()
        self.test_results = {
            "timestamp": datetime.now().isoformat(),
            "error_diagnosis_tests": [],
            "task_assignment_tests": [],
            "lifecycle_management_tests": [],
            "integration_tests": [],
            "overall_success": False
        }
    
    def test_error_diagnosis(self):
        """测试错误诊断功能"""
        
        print("🔍 测试错误诊断功能...")
        
        test_cases = [
            {
                "name": "Unicode编码错误",
                "error_message": "UnicodeEncodeError: 'gbk' codec can't encode character '🤖'",
                "expected_category": "编码问题",
                "expected_role": "🚀 Full-Stack Engineer"
            },
            {
                "name": "语法错误",
                "error_message": "IndentationError: expected an indented block after 'if' statement",
                "expected_category": "语法错误",
                "expected_role": "🔍 Code Review Specialist"
            },
            {
                "name": "导入错误",
                "error_message": "ModuleNotFoundError: No module named 'numpy'",
                "expected_category": "导入错误",
                "expected_role": "🚀 Full-Stack Engineer"
            },
            {
                "name": "权限错误",
                "error_message": "PermissionError: Access denied to file",
                "expected_category": "权限问题",
                "expected_role": "🔒 Security Engineer"
            }
        ]
        
        for test_case in test_cases:
            try:
                diagnosis = self.support_system.diagnose_error(
                    test_case["error_message"],
                    {"test_case": test_case["name"]}
                )
                
                test_result = {
                    "test_name": test_case["name"],
                    "success": True,
                    "diagnosis": {
                        "category": diagnosis["category"],
                        "severity": diagnosis["severity"],
                        "assigned_role": diagnosis["assigned_role"],
                        "solutions_count": len(diagnosis["solutions"]),
                        "prevention_measures_count": len(diagnosis["prevention_measures"])
                    },
                    "expectations_met": {
                        "category_match": diagnosis["category"] == test_case["expected_category"],
                        "role_match": diagnosis["assigned_role"] == test_case["expected_role"],
                        "has_solutions": len(diagnosis["solutions"]) > 0,
                        "has_prevention": len(diagnosis["prevention_measures"]) > 0
                    }
                }
                
                # 验证期望结果
                all_expectations_met = all(test_result["expectations_met"].values())
                test_result["success"] = all_expectations_met
                
                print(f"  {'✅' if test_result['success'] else '❌'} {test_case['name']}: "
                      f"{diagnosis['category']} -> {diagnosis['assigned_role']}")
                
            except Exception as e:
                test_result = {
                    "test_name": test_case["name"],
                    "success": False,
                    "error": str(e)
                }
                print(f"  ❌ {test_case['name']}: 测试失败 - {e}")
            
            self.test_results["error_diagnosis_tests"].append(test_result)
    
    def test_task_assignment(self):
        """测试任务分配功能"""
        
        print("\n📋 测试任务分配功能...")
        
        test_cases = [
            {
                "name": "架构优化任务",
                "task_description": "重构Hook系统架构，提升性能和可维护性",
                "expected_primary": "🏗️ Software Architect",
                "expected_effort": "高"  # 包含"重构"和"架构"关键词
            },
            {
                "name": "性能优化任务", 
                "task_description": "优化算法性能，减少计算复杂度",
                "expected_primary": "🧮 Algorithm Engineer",
                "expected_effort": "高"  # 性能优化是高工作量
            },
            {
                "name": "UI界面改进",
                "task_description": "改进用户界面设计，提升用户体验",
                "expected_primary": "🎨 UI/UX Engineer",
                "expected_effort": "中等"  # 包含"改进"关键词
            },
            {
                "name": "安全漏洞修复",
                "task_description": "修复安全漏洞，加强权限控制",
                "expected_primary": "🔒 Security Engineer",
                "expected_effort": "高"  # 安全相关任务是高工作量
            }
        ]
        
        for test_case in test_cases:
            try:
                assignment = self.support_system.assign_task_intelligently(
                    test_case["task_description"],
                    {"test_case": test_case["name"]}
                )
                
                test_result = {
                    "test_name": test_case["name"],
                    "success": True,
                    "assignment": {
                        "primary_assignee": assignment["primary_assignee"],
                        "supporting_roles": assignment["supporting_roles"],
                        "estimated_effort": assignment["estimated_effort"],
                        "priority": assignment["priority"],
                        "skills_required": assignment["skills_required"]
                    },
                    "expectations_met": {
                        "primary_match": assignment["primary_assignee"] == test_case["expected_primary"],
                        "effort_match": assignment["estimated_effort"] == test_case["expected_effort"],
                        "has_supporting_roles": len(assignment["supporting_roles"]) > 0,
                        "has_skills": len(assignment["skills_required"]) > 0,
                        "has_priority": assignment["priority"] in ["高", "中", "低"]
                    }
                }
                
                # 验证期望结果
                all_expectations_met = all(test_result["expectations_met"].values())
                test_result["success"] = all_expectations_met
                
                print(f"  {'✅' if test_result['success'] else '❌'} {test_case['name']}: "
                      f"{assignment['primary_assignee']} ({assignment['estimated_effort']}) "
                      f"[期望: {test_case['expected_primary']} ({test_case['expected_effort']})]")
                
            except Exception as e:
                test_result = {
                    "test_name": test_case["name"],
                    "success": False,
                    "error": str(e)
                }
                print(f"  ❌ {test_case['name']}: 测试失败 - {e}")
            
            self.test_results["task_assignment_tests"].append(test_result)
    
    def test_lifecycle_management(self):
        """测试生命周期管理功能"""
        
        print("\n🔄 测试生命周期管理功能...")
        
        test_cases = [
            {
                "name": "任务开始执行",
                "task_id": "test_task_001",
                "current_state": "planned",
                "action": "开始执行",
                "expected_new_state": "in_progress"
            },
            {
                "name": "请求代码审查",
                "task_id": "test_task_002", 
                "current_state": "in_progress",
                "action": "请求审查",
                "expected_new_state": "review"
            },
            {
                "name": "审查通过完成",
                "task_id": "test_task_003",
                "current_state": "review",
                "action": "通过审查",
                "expected_new_state": "completed"
            },
            {
                "name": "质量验证",
                "task_id": "test_task_004",
                "current_state": "completed",
                "action": "质量验证",
                "expected_new_state": "verified"
            }
        ]
        
        for test_case in test_cases:
            try:
                lifecycle_result = self.support_system.manage_task_lifecycle(
                    test_case["task_id"],
                    test_case["current_state"],
                    test_case["action"]
                )
                
                test_result = {
                    "test_name": test_case["name"],
                    "success": True,
                    "lifecycle": {
                        "current_state": lifecycle_result["current_state"],
                        "new_state": lifecycle_result["new_state"],
                        "action_taken": lifecycle_result["action_taken"],
                        "available_actions": lifecycle_result["available_actions"],
                        "recommendations_count": len(lifecycle_result["recommendations"])
                    },
                    "expectations_met": {
                        "state_transition": lifecycle_result["new_state"] == test_case["expected_new_state"],
                        "has_actions": len(lifecycle_result["available_actions"]) > 0,
                        "has_recommendations": len(lifecycle_result["recommendations"]) > 0
                    }
                }
                
                # 验证期望结果
                all_expectations_met = all(test_result["expectations_met"].values())
                test_result["success"] = all_expectations_met
                
                print(f"  {'✅' if test_result['success'] else '❌'} {test_case['name']}: "
                      f"{test_case['current_state']} -> {lifecycle_result['new_state']}")
                
            except Exception as e:
                test_result = {
                    "test_name": test_case["name"],
                    "success": False,
                    "error": str(e)
                }
                print(f"  ❌ {test_case['name']}: 测试失败 - {e}")
            
            self.test_results["lifecycle_management_tests"].append(test_result)
    
    def test_integrated_support(self):
        """测试集成支持功能"""
        
        print("\n🎯 测试集成支持功能...")
        
        test_cases = [
            {
                "name": "综合支持请求",
                "request": {
                    "id": "integration_test_001",
                    "type": "comprehensive",
                    "error_message": "SyntaxError: invalid syntax in line 42",
                    "task_description": "修复语法错误并优化代码质量",
                    "task_id": "fix_syntax_001",
                    "current_state": "blocked",
                    "action": "解除阻塞",
                    "context": {"urgency": "高", "file": "test_module.py"}
                }
            },
            {
                "name": "错误诊断专项",
                "request": {
                    "id": "integration_test_002",
                    "type": "error_diagnosis",
                    "error_message": "ImportError: cannot import name 'missing_function'",
                    "context": {"module": "utils", "function": "missing_function"}
                }
            },
            {
                "name": "任务分配专项",
                "request": {
                    "id": "integration_test_003",
                    "type": "task_assignment",
                    "task_description": "实现数据库查询优化，提升查询性能",
                    "context": {"database": "postgresql", "performance_target": "50%"}
                }
            }
        ]
        
        for test_case in test_cases:
            try:
                integrated_result = self.support_system.provide_integrated_support(
                    test_case["request"]
                )
                
                test_result = {
                    "test_name": test_case["name"],
                    "success": True,
                    "integration": {
                        "request_id": integrated_result["request_id"],
                        "has_error_diagnosis": integrated_result["error_diagnosis"] is not None,
                        "has_task_assignment": integrated_result["task_assignment"] is not None,
                        "has_lifecycle_management": integrated_result["lifecycle_management"] is not None,
                        "recommendations_count": len(integrated_result["integrated_recommendations"]),
                        "next_actions_count": len(integrated_result["next_actions"])
                    },
                    "expectations_met": {
                        "has_recommendations": len(integrated_result["integrated_recommendations"]) > 0,
                        "has_next_actions": len(integrated_result["next_actions"]) > 0,
                        "request_processed": integrated_result["request_id"] == test_case["request"]["id"]
                    }
                }
                
                # 验证期望结果
                all_expectations_met = all(test_result["expectations_met"].values())
                test_result["success"] = all_expectations_met
                
                print(f"  {'✅' if test_result['success'] else '❌'} {test_case['name']}: "
                      f"{integrated_result['request_id']} - "
                      f"{len(integrated_result['integrated_recommendations'])}建议, "
                      f"{len(integrated_result['next_actions'])}行动")
                
            except Exception as e:
                test_result = {
                    "test_name": test_case["name"],
                    "success": False,
                    "error": str(e)
                }
                print(f"  ❌ {test_case['name']}: 测试失败 - {e}")
            
            self.test_results["integration_tests"].append(test_result)
    
    def calculate_overall_success(self):
        """计算总体成功率"""
        
        all_tests = (
            self.test_results["error_diagnosis_tests"] +
            self.test_results["task_assignment_tests"] +
            self.test_results["lifecycle_management_tests"] +
            self.test_results["integration_tests"]
        )
        
        if not all_tests:
            return False
        
        successful_tests = sum(1 for test in all_tests if test.get("success", False))
        success_rate = successful_tests / len(all_tests)
        
        self.test_results["overall_success"] = success_rate >= 0.9  # 90%成功率
        self.test_results["success_rate"] = success_rate
        self.test_results["total_tests"] = len(all_tests)
        self.test_results["successful_tests"] = successful_tests
        
        return self.test_results["overall_success"]
    
    def run_all_tests(self):
        """运行所有测试"""
        
        print("🧪 开始智能开发支持功能测试...")
        print("=" * 60)
        
        # 运行各项测试
        self.test_error_diagnosis()
        self.test_task_assignment()
        self.test_lifecycle_management()
        self.test_integrated_support()
        
        # 计算总体成功率
        overall_success = self.calculate_overall_success()
        
        # 显示测试摘要
        print("\n" + "=" * 60)
        print("📊 智能开发支持功能测试摘要")
        print("=" * 60)
        
        print(f"🎯 总体测试结果: {'✅ 通过' if overall_success else '❌ 失败'}")
        print(f"📈 成功率: {self.test_results['success_rate']:.1%}")
        print(f"📋 测试统计: {self.test_results['successful_tests']}/{self.test_results['total_tests']} 通过")
        print()
        
        # 各功能模块测试结果
        modules = [
            ("错误诊断", "error_diagnosis_tests"),
            ("任务分配", "task_assignment_tests"),
            ("生命周期管理", "lifecycle_management_tests"),
            ("集成支持", "integration_tests")
        ]
        
        print("📋 功能模块测试结果:")
        for module_name, module_key in modules:
            module_tests = self.test_results[module_key]
            if module_tests:
                successful = sum(1 for test in module_tests if test.get("success", False))
                total = len(module_tests)
                status = "✅" if successful == total else "⚠️" if successful > 0 else "❌"
                print(f"  {status} {module_name}: {successful}/{total} 通过")
        
        print("\n" + "=" * 60)
        
        if overall_success:
            print("🎉 所有智能开发支持功能测试通过！")
            print("💪 系统已准备好提供全面的智能开发支持")
        else:
            print("⚠️ 部分功能测试未通过，需要进一步检查和优化")
        
        return self.test_results

def main():
    """主函数"""
    
    # 创建功能测试器
    tester = IntelligentSupportFeatureTester()
    
    # 运行所有测试
    results = tester.run_all_tests()
    
    return results

if __name__ == "__main__":
    main()