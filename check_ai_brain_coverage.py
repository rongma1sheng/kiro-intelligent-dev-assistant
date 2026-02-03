#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
检查AI大脑协调器的覆盖率
"""

import json

def check_ai_brain_coverage():
    """检查AI大脑协调器的覆盖率"""
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
        
        print(f"🎯 AI大脑协调器覆盖率报告")
        print(f"文件: {ai_brain_file}")
        print(f"总行数: {summary['num_statements']}")
        print(f"覆盖行数: {summary['covered_lines']}")
        print(f"覆盖率: {summary['percent_covered']:.2f}%")
        print(f"缺失行数: {summary['missing_lines']}")
        
        if 'missing_lines' in file_data:
            missing_lines = file_data['missing_lines']
            print(f"缺失行号: {missing_lines}")
            print(f"缺失行数量: {len(missing_lines)}")
            
            # 检查是否达到100%覆盖率
            if summary['percent_covered'] >= 100.0:
                print("✅ 已达到100%覆盖率！")
            else:
                print(f"❌ 未达到100%覆盖率，还需覆盖 {len(missing_lines)} 行")
                
                # 显示前10个缺失行号
                if missing_lines:
                    print(f"前10个缺失行号: {missing_lines[:10]}")
        
    except Exception as e:
        print(f"❌ 检查覆盖率时出错: {e}")

if __name__ == "__main__":
    check_ai_brain_coverage()