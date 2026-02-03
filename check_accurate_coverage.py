#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
检查AI大脑协调器准确覆盖率
"""

import json

def check_accurate_coverage():
    """检查准确覆盖率"""
    
    try:
        with open('ai_brain_coordinator_accurate_coverage.json', 'r', encoding='utf-8') as f:
            coverage_data = json.load(f)
    except FileNotFoundError:
        print("❌ 准确覆盖率报告文件不存在")
        return
    
    # 查找AI大脑协调器文件
    ai_brain_file = None
    for file_path in coverage_data['files']:
        if 'ai_brain_coordinator.py' in file_path:
            ai_brain_file = file_path
            break
    
    if not ai_brain_file:
        print("❌ 未找到AI大脑协调器文件")
        return
    
    file_data = coverage_data['files'][ai_brain_file]
    summary = file_data['summary']
    
    print("🎯 AI大脑协调器准确覆盖率报告")
    print("=" * 60)
    print(f"📊 语句覆盖率: {summary['percent_covered']:.2f}% ({summary['covered_lines']}/{summary['num_statements']})")
    print(f"🌳 分支覆盖率: {summary['percent_branches_covered']:.2f}% ({summary['covered_branches']}/{summary['num_branches']})")
    
    missing_branches = file_data.get('missing_branches', [])
    if missing_branches:
        print(f"\n❌ 缺失分支数量: {len(missing_branches)}")
        print("缺失分支详情:")
        for branch in missing_branches:
            print(f"   - 分支 {branch}")
    else:
        print("\n✅ 所有分支都已覆盖！")
    
    # 检查是否达到100%分支覆盖率
    if summary['percent_branches_covered'] >= 100.0:
        print("\n🎉 恭喜！已达到100%分支覆盖率！")
        return True
    else:
        print(f"\n⚠️  还需要覆盖 {summary['num_branches'] - summary['covered_branches']} 个分支")
        return False

if __name__ == "__main__":
    check_accurate_coverage()