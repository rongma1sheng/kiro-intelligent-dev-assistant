#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
AI大脑协调器最终覆盖率检查脚本
专门检查5个分支修复后的覆盖率状况
"""

import json
import os

def check_ai_brain_coordinator_coverage():
    """检查AI大脑协调器覆盖率"""
    
    # 尝试读取最新的覆盖率报告
    coverage_files = [
        'ai_brain_coordinator_final_coverage.json',
        'ai_brain_coordinator_accurate_coverage.json', 
        'coverage.json'
    ]
    
    coverage_data = None
    used_file = None
    
    for file_name in coverage_files:
        if os.path.exists(file_name):
            try:
                with open(file_name, 'r', encoding='utf-8') as f:
                    coverage_data = json.load(f)
                used_file = file_name
                break
            except Exception as e:
                print(f"⚠️  读取 {file_name} 失败: {e}")
                continue
    
    if not coverage_data:
        print("❌ 未找到任何覆盖率报告文件")
        return False
    
    print(f"📊 使用覆盖率报告: {used_file}")
    
    # 查找AI大脑协调器文件
    ai_brain_file = None
    for file_path in coverage_data['files']:
        if 'ai_brain_coordinator.py' in file_path:
            ai_brain_file = file_path
            break
    
    if not ai_brain_file:
        print("❌ 未找到AI大脑协调器文件")
        return False
    
    file_data = coverage_data['files'][ai_brain_file]
    summary = file_data['summary']
    
    print("\n🎯 AI大脑协调器覆盖率报告")
    print("=" * 60)
    print(f"📁 文件路径: {ai_brain_file}")
    print(f"📊 语句覆盖率: {summary['percent_covered']:.2f}% ({summary['covered_lines']}/{summary['num_statements']})")
    print(f"🌳 分支覆盖率: {summary['percent_branches_covered']:.2f}% ({summary['covered_branches']}/{summary['num_branches']})")
    
    # 检查缺失分支
    missing_branches = file_data.get('missing_branches', [])
    if missing_branches:
        print(f"\n❌ 缺失分支数量: {len(missing_branches)}")
        print("缺失分支详情:")
        
        # 重点检查我们修复的5个分支
        target_branches = [
            [276, 277],  # Commander异常处理分支
            [422, -388], # 批处理项目异常处理分支
            [539, 542],  # 脑决策处理异常分支
            [559, -547], # 分析完成处理异常分支
            [792, 815]   # 冲突解决单一决策分支
        ]
        
        still_missing = []
        for target_branch in target_branches:
            if target_branch in missing_branches:
                still_missing.append(target_branch)
        
        if still_missing:
            print(f"\n🚨 关键问题：我们修复的5个分支中仍有 {len(still_missing)} 个未覆盖:")
            for branch in still_missing:
                print(f"   - 分支 {branch}")
        else:
            print(f"\n✅ 好消息：我们修复的5个目标分支都已覆盖！")
        
        print(f"\n📋 所有缺失分支:")
        for i, branch in enumerate(missing_branches, 1):
            print(f"   {i:2d}. 分支 {branch}")
            
    else:
        print("\n🎉 恭喜！所有分支都已覆盖！")
    
    # 检查是否达到100%分支覆盖率
    if summary['percent_branches_covered'] >= 100.0:
        print("\n🎉 任务完成！已达到100%分支覆盖率！")
        return True
    else:
        remaining_branches = summary['num_branches'] - summary['covered_branches']
        print(f"\n⚠️  还需要覆盖 {remaining_branches} 个分支才能达到100%")
        return False

if __name__ == "__main__":
    success = check_ai_brain_coordinator_coverage()
    exit(0 if success else 1)