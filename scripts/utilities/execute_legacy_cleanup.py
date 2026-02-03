#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
执行旧版本知识积累脚本清理
基于智能分析结果进行自动化清理
"""

import json
from pathlib import Path
from datetime import datetime

def execute_cleanup():
    """执行清理操作"""
    
    # 读取清理报告
    report_path = Path(".kiro/reports/legacy_knowledge_cleanup_report.json")
    if not report_path.exists():
        print("清理报告不存在，请先运行分析")
        return
    
    with open(report_path, 'r', encoding='utf-8') as f:
        report = json.load(f)
    
    recommendations = report["recommendations"]
    scripts_dir = Path("scripts/utilities")
    
    # 创建归档目录
    archive_dir = Path("archive/legacy_knowledge_scripts")
    archive_dir.mkdir(parents=True, exist_ok=True)
    
    cleanup_results = {
        "execution_date": datetime.now().isoformat(),
        "actions_taken": [],
        "space_saved_kb": 0,
        "files_processed": 0
    }
    
    # 执行立即清理
    print("执行立即清理...")
    for item in recommendations["immediate_cleanup"]:
        script_path = scripts_dir / item["script"]
        if script_path.exists():
            size_kb = script_path.stat().st_size / 1024
            script_path.unlink()
            
            cleanup_results["actions_taken"].append({
                "action": "删除",
                "file": item["script"],
                "reason": item["reason"],
                "size_kb": size_kb
            })
            cleanup_results["space_saved_kb"] += size_kb
            cleanup_results["files_processed"] += 1
            print(f"  删除: {item['script']}")
    
    # 执行归档
    print("执行归档...")
    for item in recommendations["archive_candidates"]:
        script_path = scripts_dir / item["script"]
        if script_path.exists():
            archive_path = archive_dir / item["script"]
            size_kb = script_path.stat().st_size / 1024
            script_path.rename(archive_path)
            
            cleanup_results["actions_taken"].append({
                "action": "归档",
                "file": item["script"],
                "reason": item["reason"],
                "archive_location": str(archive_path),
                "size_kb": size_kb
            })
            cleanup_results["files_processed"] += 1
            print(f"  归档: {item['script']} -> {archive_path}")
    
    # 保存清理结果
    result_path = Path(".kiro/reports/cleanup_execution_result.json")
    with open(result_path, 'w', encoding='utf-8') as f:
        json.dump(cleanup_results, f, ensure_ascii=False, indent=2)
    
    print(f"\n清理完成!")
    print(f"处理文件: {cleanup_results['files_processed']}个")
    print(f"节省空间: {cleanup_results['space_saved_kb']:.1f}KB")
    print(f"详细结果: {result_path}")
    
    return cleanup_results

if __name__ == "__main__":
    execute_cleanup()