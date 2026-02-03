#!/usr/bin/env python3
"""
分析Commander Engine V2的最终覆盖率报告
"""

import json
import sys

def analyze_commander_coverage():
    """分析Commander Engine V2的覆盖率"""
    try:
        # 读取覆盖率报告
        with open('commander_engine_v2_final_100_percent_coverage.json', 'r', encoding='utf-8') as f:
            coverage_data = json.load(f)
        
        # 查找Commander Engine V2的覆盖率数据
        commander_file = None
        for file_path, file_data in coverage_data.get('files', {}).items():
            if 'commander_engine_v2.py' in file_path:
                commander_file = file_data
                print(f"找到Commander Engine V2文件: {file_path}")
                break
        
        if not commander_file:
            print("❌ 未找到Commander Engine V2的覆盖率数据")
            return
        
        # 分析覆盖率数据
        summary = commander_file.get('summary', {})
        
        print("\n📊 Commander Engine V2 覆盖率分析:")
        print("=" * 60)
        
        # 语句覆盖率
        total_statements = summary.get('num_statements', 0)
        covered_statements = summary.get('covered_lines', 0)
        missing_statements = summary.get('missing_lines', 0)
        statement_coverage = summary.get('percent_covered', 0)
        
        print(f"📈 语句覆盖率: {statement_coverage:.2f}%")
        print(f"   - 总语句数: {total_statements}")
        print(f"   - 已覆盖: {covered_statements}")
        print(f"   - 未覆盖: {missing_statements}")
        
        # 分支覆盖率
        total_branches = summary.get('num_branches', 0)
        covered_branches = summary.get('covered_branches', 0)
        missing_branches_count = summary.get('missing_branches', 0)
        branch_coverage = summary.get('percent_branches_covered', 0)
        
        print(f"\n🌿 分支覆盖率: {branch_coverage:.2f}%")
        print(f"   - 总分支数: {total_branches}")
        print(f"   - 已覆盖: {covered_branches}")
        print(f"   - 未覆盖: {missing_branches_count}")
        
        # 分析缺失的行
        missing_lines = commander_file.get('missing_lines', [])
        if missing_lines:
            print(f"\n❌ 未覆盖的行 ({len(missing_lines)}行):")
            # 将连续的行号分组显示
            ranges = []
            start = missing_lines[0]
            end = start
            
            for line in missing_lines[1:]:
                if line == end + 1:
                    end = line
                else:
                    if start == end:
                        ranges.append(str(start))
                    else:
                        ranges.append(f"{start}-{end}")
                    start = end = line
            
            # 添加最后一个范围
            if start == end:
                ranges.append(str(start))
            else:
                ranges.append(f"{start}-{end}")
            
            # 每行显示10个范围
            for i in range(0, len(ranges), 10):
                print(f"   {', '.join(ranges[i:i+10])}")
        
        # 分析缺失的分支
        missing_branches = commander_file.get('missing_branches', [])
        if missing_branches:
            print(f"\n🌿 未覆盖的分支 ({len(missing_branches)}个):")
            for i, branch in enumerate(missing_branches):
                if i < 20:  # 只显示前20个
                    print(f"   [{branch[0]}, {branch[1]}]")
                elif i == 20:
                    print(f"   ... 还有 {len(missing_branches) - 20} 个分支")
                    break
        
        # 分析已执行的行
        executed_lines = commander_file.get('executed_lines', [])
        print(f"\n✅ 已覆盖的行: {len(executed_lines)}行")
        
        # 分析已执行的分支
        executed_branches = commander_file.get('executed_branches', [])
        print(f"✅ 已覆盖的分支: {len(executed_branches)}个")
        
        # 总结
        print("\n" + "=" * 60)
        if statement_coverage >= 100 and branch_coverage >= 100:
            print("🎉 恭喜！Commander Engine V2已达到100%覆盖率！")
        elif statement_coverage >= 95 and branch_coverage >= 90:
            print("🎯 Commander Engine V2覆盖率良好，接近目标！")
        else:
            print("⚠️  Commander Engine V2覆盖率需要进一步提升")
        
        print(f"📊 综合评分: {(statement_coverage + branch_coverage) / 2:.2f}%")
        
        return {
            'statement_coverage': statement_coverage,
            'branch_coverage': branch_coverage,
            'total_statements': total_statements,
            'total_branches': total_branches,
            'missing_lines_count': len(missing_lines),
            'missing_branches_count': len(missing_branches)
        }
        
    except FileNotFoundError:
        print("❌ 覆盖率报告文件不存在")
        return None
    except json.JSONDecodeError as e:
        print(f"❌ JSON解析错误: {e}")
        return None
    except Exception as e:
        print(f"❌ 分析过程中出现错误: {e}")
        return None

if __name__ == "__main__":
    result = analyze_commander_coverage()
    if result:
        # 返回适当的退出码
        if result['statement_coverage'] >= 100 and result['branch_coverage'] >= 100:
            sys.exit(0)  # 成功
        else:
            sys.exit(1)  # 需要改进
    else:
        sys.exit(2)  # 错误