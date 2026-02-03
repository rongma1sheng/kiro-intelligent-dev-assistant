#!/usr/bin/env python3
"""检查测试覆盖率"""
import json
import os
from datetime import datetime

if os.path.exists('coverage.json'):
    with open('coverage.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    totals = data['totals']
    percent = totals['percent_covered']
    covered = totals['covered_lines']
    total = totals['num_statements']
    missing = totals['missing_lines']
    
    print('✅ coverage.json 已更新')
    print(f'覆盖率: {percent:.2f}%')
    print(f'已覆盖: {covered} / {total} 行')
    print(f'未覆盖: {missing} 行')
    print(f'文件数量: {len(data["files"])}')
    
    mtime = os.path.getmtime('coverage.json')
    print(f'最后更新: {datetime.fromtimestamp(mtime)}')
    
    # 显示覆盖率最低的10个文件
    print('\n📊 覆盖率最低的10个文件:')
    files_coverage = []
    for filepath, filedata in data['files'].items():
        file_percent = filedata['summary']['percent_covered']
        files_coverage.append((filepath, file_percent))
    
    files_coverage.sort(key=lambda x: x[1])
    for i, (filepath, file_percent) in enumerate(files_coverage[:10], 1):
        print(f'{i}. {filepath}: {file_percent:.2f}%')
    
    # 显示覆盖率最高的10个文件
    print('\n🏆 覆盖率最高的10个文件:')
    files_coverage.sort(key=lambda x: x[1], reverse=True)
    for i, (filepath, file_percent) in enumerate(files_coverage[:10], 1):
        print(f'{i}. {filepath}: {file_percent:.2f}%')
else:
    print('❌ coverage.json 未找到')
