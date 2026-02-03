#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
分析AI大脑协调器覆盖率缺失情况
"""

import subprocess
import json
import sys

def run_coverage_analysis():
    """运行覆盖率分析"""
    print("🔍 运行AI大脑协调器覆盖率分析...")
    
    # 设置环境变量并运行测试
    cmd = [
        "python", "-m", "pytest", 
        "tests/unit/brain/test_ai_brain_coordinator_final_100_percent.py",
        "--cov=src.brain.ai_brain_coordinator",
        "--cov-report=json:ai_brain_coordinator_coverage.json",
        "--cov-report=term-missing",
        "-v"
    ]
    
    # 设置环境变量
    import os
    env = os.environ.copy()
    env["PYTHONPATH"] = "C:\\mia"
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, env=env)
        print("STDOUT:", result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        
        # 读取JSON覆盖率报告
        try:
            with open("ai_brain_coordinator_coverage.json", "r", encoding="utf-8") as f:
                coverage_data = json.load(f)
            
            # 分析AI大脑协调器的覆盖率
            ai_brain_file = None
            for file_path, file_data in coverage_data["files"].items():
                if "ai_brain_coordinator.py" in file_path:
                    ai_brain_file = file_path
                    break
            
            if ai_brain_file:
                file_data = coverage_data["files"][ai_brain_file]
                print(f"\n📊 AI大脑协调器覆盖率分析:")
                print(f"文件: {ai_brain_file}")
                print(f"总语句数: {file_data['summary']['num_statements']}")
                print(f"已覆盖: {file_data['summary']['covered_lines']}")
                print(f"缺失: {file_data['summary']['missing_lines']}")
                print(f"覆盖率: {file_data['summary']['percent_covered']:.2f}%")
                
                # 分析缺失的行
                missing_lines = file_data["missing_lines"]
                print(f"\n❌ 缺失的行数 ({len(missing_lines)} 行):")
                
                # 按范围分组显示
                ranges = []
                start = missing_lines[0] if missing_lines else 0
                end = start
                
                for line in missing_lines[1:]:
                    if line == end + 1:
                        end = line
                    else:
                        if start == end:
                            ranges.append(f"{start}")
                        else:
                            ranges.append(f"{start}-{end}")
                        start = line
                        end = line
                
                # 添加最后一个范围
                if missing_lines:
                    if start == end:
                        ranges.append(f"{start}")
                    else:
                        ranges.append(f"{start}-{end}")
                
                print(", ".join(ranges))
                
                # 分析已覆盖的行
                executed_lines = file_data["executed_lines"]
                print(f"\n✅ 已覆盖的行数 ({len(executed_lines)} 行):")
                print(f"覆盖行范围: {min(executed_lines)}-{max(executed_lines)}")
                
                return {
                    "total_statements": file_data['summary']['num_statements'],
                    "covered_lines": len(executed_lines),
                    "missing_lines": missing_lines,
                    "coverage_percent": file_data['summary']['percent_covered']
                }
            else:
                print("❌ 未找到AI大脑协调器文件的覆盖率数据")
                return None
                
        except FileNotFoundError:
            print("❌ 覆盖率JSON文件未找到")
            return None
        except json.JSONDecodeError as e:
            print(f"❌ JSON解析错误: {e}")
            return None
            
    except Exception as e:
        print(f"❌ 运行覆盖率分析失败: {e}")
        return None

if __name__ == "__main__":
    result = run_coverage_analysis()
    if result:
        print(f"\n🎯 总结:")
        print(f"需要补充测试的行数: {len(result['missing_lines'])}")
        print(f"当前覆盖率: {result['coverage_percent']:.2f}%")
        print(f"目标: 100%")
    else:
        print("❌ 分析失败")
        sys.exit(1)