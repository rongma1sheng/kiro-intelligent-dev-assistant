#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Git库合规性检查
验证是否符合智能开发支持要求，包括错误诊断、任务分配、生命周期管理功能
"""

import json
import sys
import os
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# 设置UTF-8编码（Windows兼容）
if sys.platform.startswith('win'):
    os.environ['PYTHONIOENCODING'] = 'utf-8'

class GitRepositoryComplianceChecker:
    def __init__(self):
        self.timestamp = datetime.now()
        self.compliance_results = {
            "check_metadata": {
                "timestamp": self.timestamp.isoformat(),
                "checker_version": "1.0.0",
                "platform": sys.platform
            },
            "git_status": {},
            "intelligent_support_compliance": {},
            "file_structure_compliance": {},
            "functionality_compliance": {},
            "overall_compliance": {}
        }
        
        # 智能开发支持要求
        self.required_features = {
            "error_diagnosis": {
                "description": "错误诊断和解决方案推荐",
                "required_files": [
                    "scripts/utilities/intelligent_development_support_integrated.py"
                ],
                "required_functions": [
                    "diagnose_error",
                    "_generate_solutions", 
                    "_generate_prevention_measures"
                ]
            },
            "task_assignment": {
                "description": "任务智能分配",
                "required_files": [
                    "scripts/utilities/intelligent_development_support_integrated.py"
                ],
                "required_functions": [
                    "assign_task_intelligently",
                    "_estimate_task_attributes"
                ]
            },
            "lifecycle_management": {
                "description": "生命周期自动管理",
                "required_files": [
                    "scripts/utilities/intelligent_development_support_integrated.py"
                ],
                "required_functions": [
                    "manage_task_lifecycle",
                    "_execute_state_transition",
                    "_generate_lifecycle_recommendations"
                ]
            },
            "integrated_support": {
                "description": "集成的智能开发支持",
                "required_files": [
                    "scripts/utilities/intelligent_development_support_integrated.py"
                ],
                "required_functions": [
                    "provide_integrated_support",
                    "_generate_integrated_recommendations",
                    "_generate_next_actions"
                ]
            }
        }
        
        # 预期的文件结构
        self.expected_structure = {
            "hook_system": [
                ".kiro/hooks/core-quality-guardian.kiro.hook",
                ".kiro/hooks/intelligent-development-assistant.kiro.hook",
                ".kiro/hooks/real-time-code-guardian.kiro.hook",
                ".kiro/hooks/documentation-sync-manager.kiro.hook",
                ".kiro/hooks/automated-deployment-orchestrator.kiro.hook",
                ".kiro/hooks/background-knowledge-accumulator.kiro.hook",
                ".kiro/hooks/HOOK_ARCHITECTURE.md"
            ],
            "knowledge_system": [
                "scripts/utilities/background_knowledge_accumulator.py",
                "scripts/utilities/background_knowledge_extraction.py",
                ".kiro/memory/",
                ".kiro/reports/"
            ],
            "testing_system": [
                "scripts/utilities/comprehensive_kiro_system_test.py",
                "scripts/utilities/kiro_comprehensive_test.py"
            ],
            "documentation": [
                "docs/README_CN.md",
                "docs/README_EN.md"
            ],
            "intelligent_support": [
                "scripts/utilities/intelligent_development_support_integrated.py",
                "scripts/utilities/integrated_development_support.py"
            ]
        }
    
    def check_git_status(self) -> Dict:
        """检查Git状态"""
        
        print("📊 检查Git状态...")
        
        git_status = {
            "repository_exists": False,
            "clean_working_tree": False,
            "latest_commit": None,
            "branch": None,
            "remote_configured": False,
            "total_commits": 0
        }
        
        try:
            # 检查是否是Git仓库
            result = subprocess.run(['git', 'rev-parse', '--git-dir'], 
                                  capture_output=True, text=True, encoding='utf-8')
            
            if result.returncode == 0:
                git_status["repository_exists"] = True
                
                # 检查工作树状态
                status_result = subprocess.run(['git', 'status', '--porcelain'], 
                                             capture_output=True, text=True, encoding='utf-8')
                git_status["clean_working_tree"] = len(status_result.stdout.strip()) == 0
                
                # 获取最新提交
                commit_result = subprocess.run(['git', 'log', '-1', '--oneline'], 
                                             capture_output=True, text=True, encoding='utf-8')
                if commit_result.returncode == 0:
                    git_status["latest_commit"] = commit_result.stdout.strip()
                
                # 获取当前分支
                branch_result = subprocess.run(['git', 'branch', '--show-current'], 
                                             capture_output=True, text=True, encoding='utf-8')
                if branch_result.returncode == 0:
                    git_status["branch"] = branch_result.stdout.strip()
                
                # 检查远程配置
                remote_result = subprocess.run(['git', 'remote', '-v'], 
                                             capture_output=True, text=True, encoding='utf-8')
                git_status["remote_configured"] = len(remote_result.stdout.strip()) > 0
                
                # 获取提交总数
                count_result = subprocess.run(['git', 'rev-list', '--count', 'HEAD'], 
                                            capture_output=True, text=True, encoding='utf-8')
                if count_result.returncode == 0:
                    git_status["total_commits"] = int(count_result.stdout.strip())
                    
        except Exception as e:
            print(f"⚠️ Git状态检查异常: {e}")
        
        return git_status
    
    def check_intelligent_support_compliance(self) -> Dict:
        """检查智能开发支持合规性"""
        
        print("🤖 检查智能开发支持合规性...")
        
        compliance = {
            "overall_score": 0,
            "feature_compliance": {},
            "missing_features": [],
            "implementation_quality": {}
        }
        
        total_features = len(self.required_features)
        compliant_features = 0
        
        for feature_name, feature_config in self.required_features.items():
            feature_compliance = {
                "description": feature_config["description"],
                "files_exist": True,
                "functions_exist": True,
                "missing_files": [],
                "missing_functions": [],
                "implementation_found": False
            }
            
            # 检查必需文件
            for required_file in feature_config["required_files"]:
                file_path = Path(required_file)
                if not file_path.exists():
                    feature_compliance["files_exist"] = False
                    feature_compliance["missing_files"].append(required_file)
            
            # 检查必需函数
            if feature_compliance["files_exist"]:
                for required_file in feature_config["required_files"]:
                    try:
                        with open(required_file, 'r', encoding='utf-8') as f:
                            file_content = f.read()
                        
                        for required_function in feature_config["required_functions"]:
                            if f"def {required_function}" not in file_content:
                                feature_compliance["functions_exist"] = False
                                feature_compliance["missing_functions"].append(required_function)
                        
                        if feature_compliance["functions_exist"]:
                            feature_compliance["implementation_found"] = True
                            
                    except Exception as e:
                        print(f"⚠️ 文件读取失败 {required_file}: {e}")
            
            # 评估功能合规性
            if (feature_compliance["files_exist"] and 
                feature_compliance["functions_exist"] and 
                feature_compliance["implementation_found"]):
                compliant_features += 1
            else:
                compliance["missing_features"].append(feature_name)
            
            compliance["feature_compliance"][feature_name] = feature_compliance
        
        # 计算总体评分
        compliance["overall_score"] = (compliant_features / total_features) * 100
        
        return compliance
    
    def check_file_structure_compliance(self) -> Dict:
        """检查文件结构合规性"""
        
        print("📁 检查文件结构合规性...")
        
        structure_compliance = {
            "overall_score": 0,
            "category_compliance": {},
            "missing_files": [],
            "extra_files": []
        }
        
        total_categories = len(self.expected_structure)
        compliant_categories = 0
        
        for category, expected_files in self.expected_structure.items():
            category_compliance = {
                "expected_count": len(expected_files),
                "found_count": 0,
                "missing_files": [],
                "compliance_percentage": 0
            }
            
            for expected_file in expected_files:
                file_path = Path(expected_file)
                
                # 对于目录，检查是否存在
                if expected_file.endswith('/'):
                    if file_path.exists() and file_path.is_dir():
                        category_compliance["found_count"] += 1
                    else:
                        category_compliance["missing_files"].append(expected_file)
                        structure_compliance["missing_files"].append(expected_file)
                else:
                    # 对于文件，检查是否存在
                    if file_path.exists() and file_path.is_file():
                        category_compliance["found_count"] += 1
                    else:
                        category_compliance["missing_files"].append(expected_file)
                        structure_compliance["missing_files"].append(expected_file)
            
            # 计算类别合规性
            category_compliance["compliance_percentage"] = (
                category_compliance["found_count"] / category_compliance["expected_count"]
            ) * 100
            
            if category_compliance["compliance_percentage"] >= 80:
                compliant_categories += 1
            
            structure_compliance["category_compliance"][category] = category_compliance
        
        # 计算总体评分
        structure_compliance["overall_score"] = (compliant_categories / total_categories) * 100
        
        return structure_compliance
    
    def check_functionality_compliance(self) -> Dict:
        """检查功能合规性"""
        
        print("⚙️ 检查功能合规性...")
        
        functionality = {
            "hook_system_v5": False,
            "background_knowledge_accumulator": False,
            "meta_learning_system": False,
            "anti_drift_mechanism": False,
            "cross_platform_compatibility": False,
            "intelligent_support_integration": False,
            "compliance_score": 0
        }
        
        # 检查Hook系统v5.0
        hook_arch_file = Path('.kiro/hooks/HOOK_ARCHITECTURE.md')
        if hook_arch_file.exists():
            try:
                with open(hook_arch_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                if "v5.0" in content and "重构版" in content:
                    functionality["hook_system_v5"] = True
            except Exception:
                pass
        
        # 检查后台知识积累引擎
        bg_accumulator = Path('scripts/utilities/background_knowledge_accumulator.py')
        if bg_accumulator.exists():
            try:
                with open(bg_accumulator, 'r', encoding='utf-8') as f:
                    content = f.read()
                if "BackgroundKnowledgeAccumulator" in content and "silent_mode" in content:
                    functionality["background_knowledge_accumulator"] = True
            except Exception:
                pass
        
        # 检查元学习系统
        meta_learning_dir = Path('src/team_skills_meta_learning')
        if meta_learning_dir.exists():
            core_files = ['core.py', 'meta_coordinator.py', 'models.py']
            if all((meta_learning_dir / f).exists() for f in core_files):
                functionality["meta_learning_system"] = True
        
        # 检查反漂移机制
        steering_dir = Path('.kiro/steering')
        if steering_dir.exists():
            anti_drift_files = list(steering_dir.glob('*anti*drift*.md'))
            if anti_drift_files:
                functionality["anti_drift_mechanism"] = True
        
        # 检查跨平台兼容性
        platform_dirs = [Path('3.0/win'), Path('3.0/mac'), Path('3.0/linux')]
        if all(d.exists() for d in platform_dirs):
            functionality["cross_platform_compatibility"] = True
        
        # 检查智能支持集成
        integrated_support = Path('scripts/utilities/intelligent_development_support_integrated.py')
        if integrated_support.exists():
            try:
                with open(integrated_support, 'r', encoding='utf-8') as f:
                    content = f.read()
                required_classes = ["IntelligentDevelopmentSupport"]
                required_methods = ["diagnose_error", "assign_task_intelligently", "manage_task_lifecycle"]
                
                if (all(cls in content for cls in required_classes) and 
                    all(method in content for method in required_methods)):
                    functionality["intelligent_support_integration"] = True
            except Exception:
                pass
        
        # 计算合规性评分
        total_checks = len([k for k in functionality.keys() if k != "compliance_score"])
        passed_checks = sum(1 for k, v in functionality.items() if k != "compliance_score" and v)
        functionality["compliance_score"] = (passed_checks / total_checks) * 100
        
        return functionality
    
    def generate_overall_compliance(self) -> Dict:
        """生成总体合规性评估"""
        
        print("📊 生成总体合规性评估...")
        
        # 获取各项评分
        git_score = 100 if self.compliance_results["git_status"].get("repository_exists", False) else 0
        intelligent_score = self.compliance_results["intelligent_support_compliance"].get("overall_score", 0)
        structure_score = self.compliance_results["file_structure_compliance"].get("overall_score", 0)
        functionality_score = self.compliance_results["functionality_compliance"].get("compliance_score", 0)
        
        # 计算加权总分
        weights = {
            "git_status": 0.1,
            "intelligent_support": 0.4,  # 最重要
            "file_structure": 0.2,
            "functionality": 0.3
        }
        
        overall_score = (
            git_score * weights["git_status"] +
            intelligent_score * weights["intelligent_support"] +
            structure_score * weights["file_structure"] +
            functionality_score * weights["functionality"]
        )
        
        # 确定合规等级
        if overall_score >= 90:
            compliance_level = "优秀"
            status = "完全符合要求"
        elif overall_score >= 80:
            compliance_level = "良好"
            status = "基本符合要求"
        elif overall_score >= 70:
            compliance_level = "及格"
            status = "部分符合要求"
        else:
            compliance_level = "不合格"
            status = "不符合要求"
        
        overall_compliance = {
            "overall_score": round(overall_score, 1),
            "compliance_level": compliance_level,
            "status": status,
            "component_scores": {
                "git_status": git_score,
                "intelligent_support": intelligent_score,
                "file_structure": structure_score,
                "functionality": functionality_score
            },
            "weights": weights,
            "recommendations": self._generate_recommendations()
        }
        
        return overall_compliance
    
    def _generate_recommendations(self) -> List[str]:
        """生成改进建议"""
        
        recommendations = []
        
        # 基于智能支持合规性的建议
        intelligent_compliance = self.compliance_results["intelligent_support_compliance"]
        if intelligent_compliance.get("overall_score", 0) < 100:
            missing_features = intelligent_compliance.get("missing_features", [])
            if missing_features:
                recommendations.append(f"完善缺失的智能支持功能: {', '.join(missing_features)}")
        
        # 基于文件结构的建议
        structure_compliance = self.compliance_results["file_structure_compliance"]
        if structure_compliance.get("overall_score", 0) < 100:
            missing_files = structure_compliance.get("missing_files", [])
            if missing_files:
                recommendations.append(f"添加缺失的文件: {len(missing_files)}个文件")
        
        # 基于功能合规性的建议
        functionality = self.compliance_results["functionality_compliance"]
        if functionality.get("compliance_score", 0) < 100:
            failed_checks = [k for k, v in functionality.items() 
                           if k != "compliance_score" and not v]
            if failed_checks:
                recommendations.append(f"完善功能实现: {', '.join(failed_checks)}")
        
        if not recommendations:
            recommendations.append("系统已完全符合要求，建议继续保持和优化")
        
        return recommendations
    
    def run_comprehensive_check(self) -> Dict:
        """运行全面合规性检查"""
        
        print("🔍 开始Git库合规性检查...")
        print("=" * 60)
        
        # 执行各项检查
        self.compliance_results["git_status"] = self.check_git_status()
        self.compliance_results["intelligent_support_compliance"] = self.check_intelligent_support_compliance()
        self.compliance_results["file_structure_compliance"] = self.check_file_structure_compliance()
        self.compliance_results["functionality_compliance"] = self.check_functionality_compliance()
        self.compliance_results["overall_compliance"] = self.generate_overall_compliance()
        
        # 保存检查结果
        self.save_compliance_report()
        
        # 显示检查摘要
        self.display_compliance_summary()
        
        return self.compliance_results
    
    def save_compliance_report(self):
        """保存合规性报告"""
        
        # 创建报告目录
        report_dir = Path('.kiro/reports')
        report_dir.mkdir(parents=True, exist_ok=True)
        
        # 生成报告文件名
        timestamp = self.timestamp.strftime('%Y%m%d_%H%M%S')
        report_file = report_dir / f'git_compliance_check_{timestamp}.json'
        
        # 保存报告
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(self.compliance_results, f, ensure_ascii=False, indent=2)
        
        print(f"📄 合规性报告已保存: {report_file}")
    
    def display_compliance_summary(self):
        """显示合规性摘要"""
        
        print("\n" + "="*60)
        print("📊 Git库合规性检查摘要")
        print("="*60)
        
        overall = self.compliance_results["overall_compliance"]
        
        # 总体评分
        print(f"🎯 总体合规性评分: {overall['overall_score']}/100")
        print(f"📈 合规等级: {overall['compliance_level']}")
        print(f"✅ 状态: {overall['status']}")
        print()
        
        # 各组件评分
        print("📋 组件评分详情:")
        component_scores = overall["component_scores"]
        for component, score in component_scores.items():
            status_icon = "✅" if score >= 80 else "⚠️" if score >= 60 else "❌"
            component_name = {
                "git_status": "Git状态",
                "intelligent_support": "智能开发支持",
                "file_structure": "文件结构",
                "functionality": "功能实现"
            }.get(component, component)
            print(f"  {status_icon} {component_name}: {score}/100")
        print()
        
        # 智能支持详情
        intelligent = self.compliance_results["intelligent_support_compliance"]
        print("🤖 智能开发支持详情:")
        for feature, compliance in intelligent["feature_compliance"].items():
            status = "✅" if compliance["implementation_found"] else "❌"
            feature_name = {
                "error_diagnosis": "错误诊断",
                "task_assignment": "任务分配", 
                "lifecycle_management": "生命周期管理",
                "integrated_support": "集成支持"
            }.get(feature, feature)
            print(f"  {status} {feature_name}: {compliance['description']}")
        print()
        
        # 改进建议
        if overall["recommendations"]:
            print("💡 改进建议:")
            for rec in overall["recommendations"]:
                print(f"   • {rec}")
            print()
        
        print("="*60)
        
        if overall["overall_score"] >= 90:
            print("🎉 恭喜！Git库完全符合智能开发支持要求")
        elif overall["overall_score"] >= 80:
            print("👍 Git库基本符合要求，建议进行小幅优化")
        else:
            print("⚠️ Git库需要进一步完善以满足要求")

def main():
    """主函数"""
    
    # 创建合规性检查器
    checker = GitRepositoryComplianceChecker()
    
    # 运行全面检查
    results = checker.run_comprehensive_check()
    
    return results

if __name__ == "__main__":
    main()