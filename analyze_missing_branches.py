#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
分析AI大脑协调器缺失分支的具体原因
"""

import json
import ast
import sys

def analyze_missing_branches():
    """分析缺失分支的具体原因"""
    
    # 读取覆盖率报告
    try:
        with open('ai_brain_coordinator_final_test_coverage.json', 'r', encoding='utf-8') as f:
            coverage_data = json.load(f)
    except FileNotFoundError:
        print("❌ 覆盖率报告文件不存在")
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
    missing_branches = file_data.get('missing_branches', [])
    
    print("🔍 缺失分支详细分析")
    print("=" * 60)
    
    # 读取源代码
    try:
        with open('src/brain/ai_brain_coordinator.py', 'r', encoding='utf-8') as f:
            source_lines = f.readlines()
    except FileNotFoundError:
        print("❌ 源文件不存在")
        return
    
    for branch in missing_branches:
        line_num, branch_num = branch
        print(f"\n🎯 分支 [{line_num}, {branch_num}]:")
        print(f"   行号: {line_num}")
        print(f"   分支编号: {branch_num}")
        
        # 显示相关代码行
        if 1 <= line_num <= len(source_lines):
            start_line = max(1, line_num - 3)
            end_line = min(len(source_lines), line_num + 3)
            
            print(f"   相关代码 (行 {start_line}-{end_line}):")
            for i in range(start_line - 1, end_line):
                marker = ">>> " if i + 1 == line_num else "    "
                print(f"   {marker}{i + 1:3d}: {source_lines[i].rstrip()}")
        
        # 分析分支类型
        if branch_num == -388:
            print(f"   🔍 分析: 这是一个 else 分支 (负数表示 else 或 except 分支)")
            print(f"   📝 说明: 当条件为 False 时执行的分支")
        elif branch_num == 815:
            print(f"   🔍 分析: 这是一个正向分支")
            print(f"   📝 说明: 当条件为 True 时执行的分支")
        
        # 分析具体原因
        if line_num == 430:
            print(f"   💡 具体分析: 第430行是 'if not future.done():' 的 else 分支")
            print(f"   🎯 触发条件: future.done() 返回 True 时")
            print(f"   ⚠️  问题: 在异常处理中，如果 future 已经完成，则不设置异常")
            print(f"   🔧 解决方案: 需要在异常发生前预先完成 future")
        elif line_num == 792:
            print(f"   💡 具体分析: 第792行可能是 resolve_conflicts 方法中的分支")
            print(f"   🎯 触发条件: 特定的决策冲突解决逻辑")
            print(f"   ⚠️  问题: 可能是边界条件或特殊情况的分支")
            print(f"   🔧 解决方案: 需要构造特定的测试场景")

def analyze_branch_coverage_details():
    """分析分支覆盖率的详细信息"""
    
    print("\n" + "=" * 60)
    print("📊 分支覆盖率详细分析")
    print("=" * 60)
    
    try:
        with open('ai_brain_coordinator_final_test_coverage.json', 'r', encoding='utf-8') as f:
            coverage_data = json.load(f)
    except FileNotFoundError:
        print("❌ 覆盖率报告文件不存在")
        return
    
    # 查找AI大脑协调器文件
    ai_brain_file = None
    for file_path in coverage_data['files']:
        if 'ai_brain_coordinator.py' in file_path:
            ai_brain_file = file_path
            break
    
    if not ai_brain_file:
        return
    
    file_data = coverage_data['files'][ai_brain_file]
    
    print(f"总分支数: {file_data['summary']['num_branches']}")
    print(f"覆盖分支数: {file_data['summary']['covered_branches']}")
    print(f"缺失分支数: {file_data['summary']['missing_branches']}")
    print(f"分支覆盖率: {file_data['summary']['percent_branches_covered']:.2f}%")
    
    # 显示所有分支信息
    if 'branches' in file_data:
        print(f"\n🌳 所有分支信息:")
        branches = file_data['branches']
        for line_num, branch_data in branches.items():
            print(f"   行 {line_num}: {branch_data}")

if __name__ == "__main__":
    analyze_missing_branches()
    analyze_branch_coverage_details()