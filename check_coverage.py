#!/usr/bin/env python3
import json

# 读取覆盖率数据
with open('coverage.json', 'r') as f:
    data = json.load(f)

# 检查AI大脑协调器的覆盖率
coord_file = 'src\\brain\\ai_brain_coordinator.py'
if coord_file in data['files']:
    coord_data = data['files'][coord_file]['summary']
    print(f"AI Brain Coordinator Coverage:")
    print(f"Lines covered: {coord_data['covered_lines']}/{coord_data['num_statements']}")
    print(f"Percentage: {coord_data['percent_covered']}%")
    print(f"Missing lines count: {coord_data.get('missing_lines', 0)}")
    
    # 显示缺失的行
    missing_lines = data['files'][coord_file].get('missing_lines', [])
    if missing_lines:
        print(f"First 20 missing lines: {missing_lines[:20]}")  # 只显示前20个
else:
    print("AI Brain Coordinator file not found in coverage data")