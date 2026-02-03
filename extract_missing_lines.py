#!/usr/bin/env python3
import json

# 读取覆盖率数据
with open('coverage.json', 'r') as f:
    data = json.load(f)

# 检查AI大脑协调器的覆盖率
coord_file = 'src\\brain\\ai_brain_coordinator.py'
if coord_file in data['files']:
    coord_data = data['files'][coord_file]
    print(f"AI Brain Coordinator Coverage:")
    print(f"Lines covered: {coord_data['summary']['covered_lines']}/{coord_data['summary']['num_statements']}")
    print(f"Percentage: {coord_data['summary']['percent_covered']}%")
    
    # 显示缺失的行
    missing_lines = coord_data.get('missing_lines', [])
    print(f"Missing lines ({len(missing_lines)} total):")
    print(missing_lines)
    
    # 按范围分组显示
    if missing_lines:
        ranges = []
        start = missing_lines[0]
        end = missing_lines[0]
        
        for line in missing_lines[1:]:
            if line == end + 1:
                end = line
            else:
                if start == end:
                    ranges.append(str(start))
                else:
                    ranges.append(f"{start}-{end}")
                start = line
                end = line
        
        # 添加最后一个范围
        if start == end:
            ranges.append(str(start))
        else:
            ranges.append(f"{start}-{end}")
        
        print(f"Missing line ranges: {', '.join(ranges)}")
else:
    print("AI Brain Coordinator file not found in coverage data")