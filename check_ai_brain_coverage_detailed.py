#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
详细检查AI大脑协调器的覆盖率
"""

import json

def check_ai_brain_coverage_detailed():
    """详细检查AI大脑协调器的覆盖率"""
    try:
        with open('ai_brain_coordinator_final_test_coverage.json', 'r', encoding='utf-8') as f:
            coverage_data = json.load(f)
        
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
        
        print(f"🎯 AI大脑协调器详细覆盖率报告")
        print(f"文件: {ai_brain_file}")
        print(f"=" * 60)
        
        # 语句覆盖率
        print(f"📊 语句覆盖率:")
        print(f"  总语句数: {summary['num_statements']}")
        print(f"  覆盖语句数: {summary['covered_lines']}")
        print(f"  语句覆盖率: {summary['percent_covered']:.2f}%")
        print(f"  缺失语句数: {summary['missing_lines']}")
        
        # 分支覆盖率
        print(f"📊 分支覆盖率:")
        print(f"  总分支数: {summary['num_branches']}")
        print(f"  覆盖分支数: {summary['covered_branches']}")
        print(f"  分支覆盖率: {summary['percent_branches_covered']:.2f}%")
        print(f"  缺失分支数: {summary['missing_branches']}")
        
        # 整体覆盖率
        if summary.get('percent_statements_covered'):
            print(f"📊 整体覆盖率:")
            print(f"  语句覆盖率: {summary['percent_statements_covered']:.2f}%")
            print(f"  分支覆盖率: {summary['percent_branches_covered']:.2f}%")
        
        # 缺失行详情
        if 'missing_lines' in file_data and file_data['missing_lines']:
            missing_lines = file_data['missing_lines']
            print(f"❌ 缺失行号: {missing_lines}")
            print(f"❌ 缺失行数量: {len(missing_lines)}")
        else:
            print("✅ 所有语句行都已覆盖")
        
        # 缺失分支详情
        if 'missing_branches' in file_data and file_data['missing_branches']:
            missing_branches = file_data['missing_branches']
            print(f"❌ 缺失分支: {missing_branches}")
            print(f"❌ 缺失分支数量: {len(missing_branches)}")
        else:
            print("✅ 所有分支都已覆盖")
        
        # 最终判断
        statement_coverage = summary['percent_covered']
        branch_coverage = summary['percent_branches_covered']
        
        print(f"=" * 60)
        if statement_coverage >= 100.0 and branch_coverage >= 100.0:
            print("🎉 恭喜！已达到100%完整覆盖率（语句+分支）！")
        elif statement_coverage >= 100.0:
            print(f"✅ 语句覆盖率已达到100%")
            print(f"❌ 分支覆盖率为{branch_coverage:.2f}%，还需提升")
        else:
            print(f"❌ 语句覆盖率为{statement_coverage:.2f}%，分支覆盖率为{branch_coverage:.2f}%")
            print("需要继续完善测试覆盖")
        
    except Exception as e:
        print(f"❌ 检查覆盖率时出错: {e}")

if __name__ == "__main__":
    check_ai_brain_coverage_detailed()