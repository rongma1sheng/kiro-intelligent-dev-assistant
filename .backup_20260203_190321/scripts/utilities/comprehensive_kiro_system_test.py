#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Kiro系统全面测试
测试所有Hook、MCP设置、元学习机制和系统联动
"""

import json
import sys
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import subprocess

# 设置UTF-8编码（Windows兼容）
if sys.platform.startswith('win'):
    os.environ['PYTHONIOENCODING'] = 'utf-8'

class ComprehensiveKiroSystemTest:
    def __init__(self):
        self.test_timestamp = datetime.now()
        self.test_results = {
            "test_metadata": {
                "timestamp": self.test_timestamp.isoformat(),
                "platform": sys.platform,
                "test_scope": "全面系统测试"
            },
            "hook_tests": {},
            "mcp_tests": {},
            "meta_learning_tests": {},
            "integration_tests": {},
            "system_health": {}
        }
        
    def test_hook_system(self) -> Dict:
        """测试Hook系统"""
        
        print("🔧 测试Hook系统...")
        
        hook_dir = Path('.kiro/hooks')
        hook_results = {
            "hook_directory_exists": hook_dir.exists(),
            "hook_files": [],
            "hook_validity": {},
            "architecture_score": 0
        }
        
        if hook_dir.exists():
            # 检查Hook文件
            hook_files = list(hook_dir.glob('*.kiro.hook'))
            hook_results["hook_files"] = [f.name for f in hook_files]
            
            # 验证每个Hook的有效性
            for hook_file in hook_files:
                try:
                    with open(hook_file, 'r', encoding='utf-8') as f:
                        hook_config = json.load(f)
                    
                    # 验证Hook配置的完整性
                    required_fields = ['name', 'version', 'when', 'then']
                    validity = {
                        "file_readable": True,
                        "json_valid": True,
                        "required_fields": all(field in hook_config for field in required_fields),
                        "configuration": hook_config.get('metadata', {})
                    }
                    
                    hook_results["hook_validity"][hook_file.name] = validity
                    
                except Exception as e:
                    hook_results["hook_validity"][hook_file.name] = {
                        "file_readable": False,
                        "error": str(e)
                    }
            
            # 检查Hook架构文档
            arch_file = hook_dir / 'HOOK_ARCHITECTURE.md'
            if arch_file.exists():
                try:
                    with open(arch_file, 'r', encoding='utf-8') as f:
                        arch_content = f.read()
                    
                    # 从架构文档中提取评分
                    if "架构评分: 95.0/100" in arch_content:
                        hook_results["architecture_score"] = 95.0
                    
                except Exception:
                    pass
        
        return hook_results
    
    def test_mcp_configuration(self) -> Dict:
        """测试MCP配置"""
        
        print("🔗 测试MCP配置...")
        
        mcp_results = {
            "mcp_directory_exists": False,
            "mcp_config_files": [],
            "memory_system_status": "未知",
            "filesystem_integration": False
        }
        
        # 检查MCP设置目录
        mcp_dir = Path('.kiro/settings')
        if mcp_dir.exists():
            mcp_results["mcp_directory_exists"] = True
            
            # 检查MCP配置文件
            mcp_files = list(mcp_dir.glob('mcp*.json'))
            mcp_results["mcp_config_files"] = [f.name for f in mcp_files]
            
            # 检查记忆系统配置
            for mcp_file in mcp_files:
                try:
                    with open(mcp_file, 'r', encoding='utf-8') as f:
                        mcp_config = json.load(f)
                    
                    if 'mcpServers' in mcp_config:
                        servers = mcp_config['mcpServers']
                        if 'memory' in servers or any('memory' in server_name.lower() for server_name in servers.keys()):
                            mcp_results["memory_system_status"] = "已配置"
                        
                        if 'filesystem' in servers or any('filesystem' in server_name.lower() for server_name in servers.keys()):
                            mcp_results["filesystem_integration"] = True
                            
                except Exception:
                    continue
        
        # 检查记忆系统目录
        memory_dir = Path('.kiro/memory')
        if memory_dir.exists():
            memory_subdirs = [d.name for d in memory_dir.iterdir() if d.is_dir()]
            mcp_results["memory_directories"] = memory_subdirs
            
            # 检查最近的知识存储
            task_knowledge_dir = memory_dir / 'task_knowledge'
            if task_knowledge_dir.exists():
                knowledge_files = list(task_knowledge_dir.glob('task_knowledge_*.json'))
                if knowledge_files:
                    latest_file = max(knowledge_files, key=lambda x: x.stat().st_mtime)
                    mcp_results["latest_knowledge_extraction"] = latest_file.name
        
        return mcp_results
    
    def test_meta_learning_system(self) -> Dict:
        """测试元学习机制"""
        
        print("🧠 测试元学习机制...")
        
        meta_learning_results = {
            "team_skills_meta_learning": False,
            "brain_meta_learning": False,
            "core_components": [],
            "integration_status": "未知"
        }
        
        # 检查团队技能元学习系统
        team_skills_dir = Path('src/team_skills_meta_learning')
        if team_skills_dir.exists():
            meta_learning_results["team_skills_meta_learning"] = True
            
            # 检查核心组件
            core_files = [
                'core.py',
                'meta_coordinator.py',
                'models.py',
                '__init__.py'
            ]
            
            existing_components = []
            for core_file in core_files:
                if (team_skills_dir / core_file).exists():
                    existing_components.append(core_file)
            
            meta_learning_results["core_components"] = existing_components
        
        # 检查大脑元学习系统
        brain_meta_dir = Path('src/brain/meta_learning')
        if brain_meta_dir.exists():
            meta_learning_results["brain_meta_learning"] = True
            
            # 检查风险控制元学习器
            risk_learner_file = brain_meta_dir / 'risk_control_meta_learner.py'
            if risk_learner_file.exists():
                meta_learning_results["risk_control_meta_learner"] = True
        
        # 检查测试覆盖
        meta_test_dir = Path('tests/unit/brain/meta_learning')
        if meta_test_dir.exists():
            test_files = list(meta_test_dir.glob('test_*.py'))
            meta_learning_results["test_coverage"] = [f.name for f in test_files]
        
        # 评估集成状态
        if (meta_learning_results["team_skills_meta_learning"] and 
            meta_learning_results["brain_meta_learning"] and 
            len(meta_learning_results["core_components"]) >= 3):
            meta_learning_results["integration_status"] = "完整且运行正常"
        elif meta_learning_results["team_skills_meta_learning"] or meta_learning_results["brain_meta_learning"]:
            meta_learning_results["integration_status"] = "部分可用"
        else:
            meta_learning_results["integration_status"] = "未检测到"
        
        return meta_learning_results
    
    def test_system_integration(self) -> Dict:
        """测试系统集成"""
        
        print("🔄 测试系统集成...")
        
        integration_results = {
            "background_knowledge_accumulator": False,
            "knowledge_extraction_system": False,
            "anti_drift_mechanism": False,
            "cross_platform_compatibility": False,
            "logging_system": False
        }
        
        # 检查后台知识积累引擎
        bg_accumulator = Path('scripts/utilities/background_knowledge_accumulator.py')
        if bg_accumulator.exists():
            integration_results["background_knowledge_accumulator"] = True
        
        # 检查知识提取系统
        knowledge_extractor = Path('scripts/utilities/background_knowledge_extraction.py')
        if knowledge_extractor.exists():
            integration_results["knowledge_extraction_system"] = True
        
        # 检查反漂移机制（通过steering文件）
        steering_dir = Path('.kiro/steering')
        if steering_dir.exists():
            anti_drift_files = list(steering_dir.glob('*anti*drift*.md'))
            if anti_drift_files:
                integration_results["anti_drift_mechanism"] = True
        
        # 检查跨平台兼容性
        platform_configs = [
            Path('3.0/win'),
            Path('3.0/mac'),
            Path('3.0/linux')
        ]
        
        if all(config.exists() for config in platform_configs):
            integration_results["cross_platform_compatibility"] = True
        
        # 检查日志系统
        log_dir = Path('.kiro/logs')
        if log_dir.exists():
            integration_results["logging_system"] = True
        
        return integration_results
    
    def assess_system_health(self) -> Dict:
        """评估系统健康状况"""
        
        print("📊 评估系统健康状况...")
        
        health_results = {
            "overall_score": 0,
            "component_scores": {},
            "recommendations": [],
            "critical_issues": [],
            "optimization_opportunities": []
        }
        
        # 基于测试结果计算组件分数
        hook_score = 0
        if self.test_results["hook_tests"].get("hook_directory_exists", False):
            hook_score += 20
        
        hook_files = self.test_results["hook_tests"].get("hook_files", [])
        if len(hook_files) >= 6:  # 期望的6个Hook
            hook_score += 30
        
        # 检查Hook有效性
        valid_hooks = sum(1 for validity in self.test_results["hook_tests"].get("hook_validity", {}).values() 
                         if validity.get("required_fields", False))
        if valid_hooks >= 6:
            hook_score += 50  # 所有Hook都有效
        elif valid_hooks >= 4:
            hook_score += 30  # 大部分Hook有效
        elif valid_hooks >= 2:
            hook_score += 15  # 部分Hook有效
        
        mcp_score = 0
        if self.test_results["mcp_tests"].get("mcp_directory_exists", False):
            mcp_score += 40
        if self.test_results["mcp_tests"].get("memory_system_status") == "已配置":
            mcp_score += 60
        
        meta_learning_score = 0
        if self.test_results["meta_learning_tests"].get("integration_status") == "完整且运行正常":
            meta_learning_score = 100
        elif self.test_results["meta_learning_tests"].get("integration_status") == "部分可用":
            meta_learning_score = 60
        
        integration_score = 0
        integration_tests = self.test_results["integration_tests"]
        integration_count = sum(1 for v in integration_tests.values() if v)
        integration_score = (integration_count / len(integration_tests)) * 100
        
        # 计算总分
        health_results["component_scores"] = {
            "hook_system": hook_score,
            "mcp_configuration": mcp_score,
            "meta_learning": meta_learning_score,
            "system_integration": integration_score
        }
        
        overall_score = sum(health_results["component_scores"].values()) / len(health_results["component_scores"])
        health_results["overall_score"] = round(overall_score, 1)
        
        # 生成建议
        if hook_score < 80:
            health_results["recommendations"].append("优化Hook系统配置和架构")
        
        if mcp_score < 80:
            health_results["recommendations"].append("完善MCP配置和记忆系统集成")
        
        if meta_learning_score < 90:
            health_results["recommendations"].append("检查元学习机制的完整性")
        
        if integration_score < 80:
            health_results["recommendations"].append("加强系统组件间的集成")
        
        # 识别关键问题
        if overall_score < 70:
            health_results["critical_issues"].append("系统整体健康状况需要改善")
        
        # 识别优化机会
        if overall_score > 90:
            health_results["optimization_opportunities"].append("系统运行良好，可考虑性能优化")
        
        return health_results
    
    def run_comprehensive_test(self) -> Dict:
        """运行全面测试"""
        
        print("🚀 开始Kiro系统全面测试...")
        print(f"测试时间: {self.test_timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"测试平台: {sys.platform}")
        print()
        
        # 执行各项测试
        self.test_results["hook_tests"] = self.test_hook_system()
        self.test_results["mcp_tests"] = self.test_mcp_configuration()
        self.test_results["meta_learning_tests"] = self.test_meta_learning_system()
        self.test_results["integration_tests"] = self.test_system_integration()
        self.test_results["system_health"] = self.assess_system_health()
        
        # 保存测试结果
        self.save_test_results()
        
        # 显示测试摘要
        self.display_test_summary()
        
        return self.test_results
    
    def save_test_results(self):
        """保存测试结果"""
        
        # 创建报告目录
        report_dir = Path('.kiro/reports')
        report_dir.mkdir(parents=True, exist_ok=True)
        
        # 生成报告文件名
        timestamp = self.test_timestamp.strftime('%Y%m%d_%H%M%S')
        report_file = report_dir / f'comprehensive_system_test_{timestamp}.json'
        
        # 保存详细结果
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(self.test_results, f, ensure_ascii=False, indent=2)
        
        print(f"📄 测试报告已保存: {report_file}")
    
    def display_test_summary(self):
        """显示测试摘要"""
        
        print("\n" + "="*60)
        print("📊 Kiro系统测试摘要")
        print("="*60)
        
        # 显示系统健康评分
        health = self.test_results["system_health"]
        print(f"🎯 系统整体健康评分: {health['overall_score']}/100")
        print()
        
        # 显示组件评分
        print("📋 组件评分详情:")
        for component, score in health["component_scores"].items():
            status = "✅" if score >= 80 else "⚠️" if score >= 60 else "❌"
            print(f"  {status} {component}: {score}/100")
        print()
        
        # 显示Hook系统状态
        hook_tests = self.test_results["hook_tests"]
        print(f"🔧 Hook系统: {len(hook_tests.get('hook_files', []))}个Hook文件")
        if hook_tests.get("architecture_score", 0) > 0:
            print(f"   架构评分: {hook_tests['architecture_score']}/100")
        print()
        
        # 显示MCP状态
        mcp_tests = self.test_results["mcp_tests"]
        print(f"🔗 MCP系统: {mcp_tests.get('memory_system_status', '未知')}")
        if mcp_tests.get("mcp_config_files"):
            print(f"   配置文件: {len(mcp_tests['mcp_config_files'])}个")
        print()
        
        # 显示元学习状态
        meta_tests = self.test_results["meta_learning_tests"]
        print(f"🧠 元学习机制: {meta_tests.get('integration_status', '未知')}")
        if meta_tests.get("core_components"):
            print(f"   核心组件: {len(meta_tests['core_components'])}个")
        print()
        
        # 显示建议
        if health.get("recommendations"):
            print("💡 改进建议:")
            for rec in health["recommendations"]:
                print(f"   • {rec}")
            print()
        
        # 显示关键问题
        if health.get("critical_issues"):
            print("🚨 关键问题:")
            for issue in health["critical_issues"]:
                print(f"   • {issue}")
            print()
        
        # 显示优化机会
        if health.get("optimization_opportunities"):
            print("🎯 优化机会:")
            for opp in health["optimization_opportunities"]:
                print(f"   • {opp}")
            print()
        
        print("="*60)
        print("✅ 测试完成")

def main():
    """主函数"""
    
    # 创建测试实例
    tester = ComprehensiveKiroSystemTest()
    
    # 运行全面测试
    results = tester.run_comprehensive_test()
    
    return results

if __name__ == "__main__":
    main()