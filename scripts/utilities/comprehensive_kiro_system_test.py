#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Kiro系统全面测试 v3.0
测试所有Hook、MCP设置、系统联动和整体健康状况
"""

import os
import sys
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
import subprocess

# 设置UTF-8编码（Windows兼容）
if sys.platform.startswith('win'):
    os.environ['PYTHONIOENCODING'] = 'utf-8'

class KiroSystemTester:
    def __init__(self):
        self.timestamp = datetime.now()
        self.test_results = {
            'timestamp': self.timestamp.isoformat(),
            'version': '3.0',
            'overall_health': 0,
            'tests': {}
        }
        
        # 测试配置
        self.kiro_path = Path('.kiro')
        self.hooks_path = self.kiro_path / 'hooks'
        self.settings_path = self.kiro_path / 'settings'
        
        # 预期的Hook文件
        self.expected_hooks = [
            'core-quality-guardian.kiro.hook',
            'intelligent-development-assistant.kiro.hook',
            'real-time-code-guardian.kiro.hook',
            'documentation-sync-manager.kiro.hook',
            'automated-deployment-orchestrator.kiro.hook',
            'background-knowledge-accumulator.kiro.hook'
        ]
    
    def test_directory_structure(self) -> Dict[str, Any]:
        """测试目录结构"""
        test_name = "目录结构测试"
        result = {
            'name': test_name,
            'status': 'pass',
            'score': 0,
            'max_score': 20,
            'details': [],
            'issues': []
        }
        
        try:
            # 检查.kiro目录
            if self.kiro_path.exists():
                result['details'].append("✅ .kiro目录存在")
                result['score'] += 5
            else:
                result['issues'].append("❌ .kiro目录不存在")
                result['status'] = 'fail'
            
            # 检查hooks目录
            if self.hooks_path.exists():
                result['details'].append("✅ hooks目录存在")
                result['score'] += 5
            else:
                result['issues'].append("❌ hooks目录不存在")
                result['status'] = 'fail'
            
            # 检查settings目录
            if self.settings_path.exists():
                result['details'].append("✅ settings目录存在")
                result['score'] += 5
            else:
                result['issues'].append("❌ settings目录不存在")
                result['status'] = 'fail'
            
            # 检查scripts目录
            scripts_path = Path('scripts/utilities')
            if scripts_path.exists():
                result['details'].append("✅ scripts/utilities目录存在")
                result['score'] += 5
            else:
                result['issues'].append("❌ scripts/utilities目录不存在")
                result['status'] = 'fail'
            
        except Exception as e:
            result['status'] = 'error'
            result['issues'].append(f"目录结构测试失败: {str(e)}")
        
        return result
    
    def test_hook_files(self) -> Dict[str, Any]:
        """测试Hook文件"""
        test_name = "Hook文件测试"
        result = {
            'name': test_name,
            'status': 'pass',
            'score': 0,
            'max_score': 30,
            'details': [],
            'issues': [],
            'hook_status': {}
        }
        
        try:
            if not self.hooks_path.exists():
                result['status'] = 'fail'
                result['issues'].append("❌ hooks目录不存在")
                return result
            
            # 检查每个预期的Hook文件
            for hook_file in self.expected_hooks:
                hook_path = self.hooks_path / hook_file
                
                if hook_path.exists():
                    # 验证Hook文件格式
                    try:
                        with open(hook_path, 'r', encoding='utf-8') as f:
                            hook_content = json.load(f)
                        
                        # 检查必需字段
                        required_fields = ['name', 'version', 'when', 'then']
                        missing_fields = [field for field in required_fields if field not in hook_content]
                        
                        if not missing_fields:
                            result['details'].append(f"✅ {hook_file} 格式正确")
                            result['hook_status'][hook_file] = 'valid'
                            result['score'] += 5
                        else:
                            result['issues'].append(f"⚠️ {hook_file} 缺少字段: {missing_fields}")
                            result['hook_status'][hook_file] = 'invalid'
                            result['score'] += 2
                    
                    except json.JSONDecodeError as e:
                        result['issues'].append(f"❌ {hook_file} JSON格式错误: {str(e)}")
                        result['hook_status'][hook_file] = 'json_error'
                    except Exception as e:
                        result['issues'].append(f"❌ {hook_file} 读取失败: {str(e)}")
                        result['hook_status'][hook_file] = 'read_error'
                else:
                    result['issues'].append(f"❌ {hook_file} 不存在")
                    result['hook_status'][hook_file] = 'missing'
                    result['status'] = 'fail'
        
        except Exception as e:
            result['status'] = 'error'
            result['issues'].append(f"Hook文件测试失败: {str(e)}")
        
        return result
    
    def test_intelligent_support(self) -> Dict[str, Any]:
        """测试智能开发支持系统"""
        test_name = "智能开发支持测试"
        result = {
            'name': test_name,
            'status': 'pass',
            'score': 0,
            'max_score': 30,
            'details': [],
            'issues': []
        }
        
        try:
            script_path = Path('scripts/utilities/intelligent_development_support_integrated.py')
            
            if not script_path.exists():
                result['status'] = 'fail'
                result['issues'].append("❌ 智能开发支持脚本不存在")
                return result
            
            # 尝试导入和测试
            try:
                sys.path.append('scripts/utilities')
                from intelligent_development_support_integrated import IntelligentDevelopmentSupport
                
                support = IntelligentDevelopmentSupport()
                
                # 测试错误诊断
                diagnosis = support.diagnose_error("UnicodeEncodeError: test")
                if diagnosis and 'category' in diagnosis:
                    result['details'].append("✅ 错误诊断功能正常")
                    result['score'] += 10
                else:
                    result['issues'].append("⚠️ 错误诊断功能异常")
                
                # 测试任务分配
                assignment = support.assign_task_to_role("修复数据库问题")
                if assignment and 'assigned_role' in assignment:
                    result['details'].append("✅ 任务分配功能正常")
                    result['score'] += 10
                else:
                    result['issues'].append("⚠️ 任务分配功能异常")
                
                # 测试生命周期管理
                lifecycle = support.manage_task_lifecycle("test", "in_progress")
                if lifecycle and 'current_state' in lifecycle:
                    result['details'].append("✅ 生命周期管理功能正常")
                    result['score'] += 10
                else:
                    result['issues'].append("⚠️ 生命周期管理功能异常")
            
            except ImportError as e:
                result['issues'].append(f"❌ 无法导入智能开发支持模块: {str(e)}")
                result['status'] = 'fail'
            except Exception as e:
                result['issues'].append(f"⚠️ 智能开发支持测试异常: {str(e)}")
        
        except Exception as e:
            result['status'] = 'error'
            result['issues'].append(f"智能开发支持测试失败: {str(e)}")
        
        return result
    
    def calculate_overall_health(self) -> int:
        """计算整体健康分数"""
        total_score = 0
        max_total_score = 0
        
        for test_result in self.test_results['tests'].values():
            total_score += test_result.get('score', 0)
            max_total_score += test_result.get('max_score', 0)
        
        if max_total_score > 0:
            health_score = int((total_score / max_total_score) * 100)
        else:
            health_score = 0
        
        return health_score
    
    def run_all_tests(self) -> Dict[str, Any]:
        """运行所有测试"""
        print("开始Kiro系统全面测试...")
        print("=" * 60)
        
        # 运行各项测试
        tests = [
            ('directory_structure', self.test_directory_structure),
            ('hook_files', self.test_hook_files),
            ('intelligent_support', self.test_intelligent_support)
        ]
        
        for test_key, test_func in tests:
            print(f"\n运行 {test_func.__doc__.replace('测试', '')}...")
            
            try:
                test_result = test_func()
                self.test_results['tests'][test_key] = test_result
                
                # 显示测试结果
                status_icon = "✅" if test_result['status'] == 'pass' else "❌" if test_result['status'] == 'fail' else "⚠️"
                print(f"{status_icon} {test_result['name']}: {test_result['score']}/{test_result['max_score']}")
                
                # 显示详细信息
                for detail in test_result.get('details', []):
                    print(f"  {detail}")
                
                # 显示问题
                for issue in test_result.get('issues', []):
                    print(f"  {issue}")
            
            except Exception as e:
                print(f"❌ 测试 {test_key} 执行失败: {str(e)}")
                self.test_results['tests'][test_key] = {
                    'name': f'{test_key} 测试',
                    'status': 'error',
                    'score': 0,
                    'max_score': 10,
                    'issues': [f'测试执行失败: {str(e)}']
                }
        
        # 计算整体健康分数
        self.test_results['overall_health'] = self.calculate_overall_health()
        
        # 显示总结
        print("\n" + "=" * 60)
        print("测试总结")
        print("=" * 60)
        print(f"整体健康分数: {self.test_results['overall_health']}/100")
        
        # 显示各项测试分数
        for test_key, test_result in self.test_results['tests'].items():
            status_icon = "✅" if test_result['status'] == 'pass' else "❌" if test_result['status'] == 'fail' else "⚠️"
            print(f"{status_icon} {test_result['name']}: {test_result['score']}/{test_result['max_score']}")
        
        # 健康状态评估
        health_score = self.test_results['overall_health']
        if health_score >= 90:
            print("\n系统健康状况: 优秀")
        elif health_score >= 80:
            print("\n系统健康状况: 良好")
        elif health_score >= 70:
            print("\n系统健康状况: 一般")
        else:
            print("\n系统健康状况: 需要改进")
        
        return self.test_results

def main():
    """主函数"""
    tester = KiroSystemTester()
    
    # 运行所有测试
    results = tester.run_all_tests()
    
    print("\n测试完成")
    
    return results

if __name__ == "__main__":
    main()