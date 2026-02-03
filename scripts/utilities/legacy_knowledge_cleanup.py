#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
旧版本知识积累引擎清理评估
智能分析和清理冗余的知识积累脚本
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set

class LegacyKnowledgeCleanup:
    def __init__(self):
        self.analysis_date = datetime.now()
        self.scripts_dir = Path("scripts/utilities")
        
    def analyze_legacy_scripts(self) -> Dict:
        """分析旧版本知识积累脚本"""
        
        # 识别知识积累相关脚本
        knowledge_scripts = []
        for script_file in self.scripts_dir.glob("*.py"):
            if self._is_knowledge_script(script_file):
                analysis = self._analyze_script(script_file)
                knowledge_scripts.append(analysis)
        
        # 分类脚本
        categorized_scripts = self._categorize_scripts(knowledge_scripts)
        
        # 生成清理建议
        cleanup_recommendations = self._generate_cleanup_recommendations(categorized_scripts)
        
        return {
            "analysis_metadata": {
                "analysis_date": self.analysis_date.isoformat(),
                "total_scripts_analyzed": len(knowledge_scripts),
                "scripts_directory": str(self.scripts_dir)
            },
            "script_categories": categorized_scripts,
            "cleanup_recommendations": cleanup_recommendations,
            "new_system_status": {
                "background_accumulator": "已创建 - 现代化后台引擎",
                "integrated_support": "已创建 - 完整集成系统",
                "quick_extract": "已创建 - 高效知识提取"
            }
        }
    
    def _is_knowledge_script(self, script_file: Path) -> bool:
        """判断是否为知识积累相关脚本"""
        knowledge_keywords = [
            "extract", "knowledge", "accumulation", "finalize",
            "bilingual", "task_execution", "comprehensive"
        ]
        
        filename = script_file.name.lower()
        return any(keyword in filename for keyword in knowledge_keywords)
    
    def _analyze_script(self, script_file: Path) -> Dict:
        """分析单个脚本"""
        try:
            content = script_file.read_text(encoding='utf-8')
            
            return {
                "filename": script_file.name,
                "path": str(script_file),
                "size_kb": script_file.stat().st_size / 1024,
                "line_count": len(content.splitlines()),
                "last_modified": datetime.fromtimestamp(script_file.stat().st_mtime).isoformat(),
                "has_main_function": "def main(" in content,
                "has_mcp_integration": "mcp_memory" in content,
                "complexity_score": self._calculate_complexity(content)
            }
        except Exception as e:
            return {
                "filename": script_file.name,
                "path": str(script_file),
                "error": str(e),
                "analysis_failed": True
            }
    
    def _calculate_complexity(self, content: str) -> int:
        """计算脚本复杂度"""
        complexity = 0
        complexity += content.count("def ") * 2  # 函数定义
        complexity += content.count("class ") * 5  # 类定义
        complexity += content.count("if ") * 1  # 条件语句
        complexity += content.count("for ") * 2  # 循环
        complexity += content.count("try:") * 3  # 异常处理
        return complexity
    
    def _categorize_scripts(self, scripts: List[Dict]) -> Dict:
        """分类脚本"""
        categories = {
            "legacy_extractors": [],  # 旧版本提取器
            "finalization_scripts": [],  # 最终化脚本
            "bilingual_processors": [],  # 双语处理脚本
            "task_specific_extractors": [],  # 特定任务提取器
            "utility_scripts": []  # 工具脚本
        }
        
        for script in scripts:
            filename = script["filename"].lower()
            
            if "finalize" in filename:
                categories["finalization_scripts"].append(script)
            elif "bilingual" in filename:
                categories["bilingual_processors"].append(script)
            elif "extract" in filename and any(word in filename for word in ["task", "comprehensive", "git", "cross"]):
                categories["task_specific_extractors"].append(script)
            elif "extract" in filename:
                categories["legacy_extractors"].append(script)
            else:
                categories["utility_scripts"].append(script)
        
        return categories
    
    def _generate_cleanup_recommendations(self, categorized_scripts: Dict) -> Dict:
        """生成清理建议"""
        
        recommendations = {
            "immediate_cleanup": [],  # 立即清理
            "conditional_cleanup": [],  # 条件清理
            "keep_for_reference": [],  # 保留参考
            "archive_candidates": []  # 归档候选
        }
        
        # 分析每个类别
        for category, scripts in categorized_scripts.items():
            if category == "finalization_scripts":
                # 最终化脚本通常可以清理
                for script in scripts:
                    recommendations["immediate_cleanup"].append({
                        "script": script["filename"],
                        "reason": "最终化脚本，功能已被新系统替代",
                        "action": "删除"
                    })
            
            elif category == "legacy_extractors":
                # 旧版本提取器需要评估
                for script in scripts:
                    if script.get("complexity_score", 0) > 50:
                        recommendations["archive_candidates"].append({
                            "script": script["filename"],
                            "reason": "复杂度较高，可能包含有价值逻辑",
                            "action": "归档到archive目录"
                        })
                    else:
                        recommendations["immediate_cleanup"].append({
                            "script": script["filename"],
                            "reason": "简单提取器，已被新系统替代",
                            "action": "删除"
                        })
            
            elif category == "task_specific_extractors":
                # 特定任务提取器条件清理
                for script in scripts:
                    recommendations["conditional_cleanup"].append({
                        "script": script["filename"],
                        "reason": "特定任务提取器，如果任务已完成可清理",
                        "action": "检查任务状态后决定"
                    })
            
            elif category == "bilingual_processors":
                # 双语处理脚本保留参考
                for script in scripts:
                    recommendations["keep_for_reference"].append({
                        "script": script["filename"],
                        "reason": "双语处理逻辑可能在未来有用",
                        "action": "保留但移至参考目录"
                    })
        
        return recommendations
    
    def execute_cleanup(self, recommendations: Dict, dry_run: bool = True) -> Dict:
        """执行清理操作"""
        
        cleanup_results = {
            "dry_run": dry_run,
            "execution_date": datetime.now().isoformat(),
            "actions_taken": [],
            "space_saved_kb": 0,
            "files_processed": 0
        }
        
        # 创建归档目录
        archive_dir = Path("archive/legacy_knowledge_scripts")
        if not dry_run:
            archive_dir.mkdir(parents=True, exist_ok=True)
        
        # 执行立即清理
        for item in recommendations["immediate_cleanup"]:
            script_path = self.scripts_dir / item["script"]
            if script_path.exists():
                size_kb = script_path.stat().st_size / 1024
                
                if not dry_run:
                    script_path.unlink()
                
                cleanup_results["actions_taken"].append({
                    "action": "删除",
                    "file": item["script"],
                    "reason": item["reason"],
                    "size_kb": size_kb
                })
                cleanup_results["space_saved_kb"] += size_kb
                cleanup_results["files_processed"] += 1
        
        # 执行归档
        for item in recommendations["archive_candidates"]:
            script_path = self.scripts_dir / item["script"]
            if script_path.exists():
                archive_path = archive_dir / item["script"]
                size_kb = script_path.stat().st_size / 1024
                
                if not dry_run:
                    script_path.rename(archive_path)
                
                cleanup_results["actions_taken"].append({
                    "action": "归档",
                    "file": item["script"],
                    "reason": item["reason"],
                    "archive_location": str(archive_path),
                    "size_kb": size_kb
                })
                cleanup_results["files_processed"] += 1
        
        return cleanup_results
    
    def generate_cleanup_report(self, analysis: Dict, cleanup_results: Dict = None) -> Dict:
        """生成清理报告"""
        
        report = {
            "report_metadata": {
                "report_type": "旧版本知识积累引擎清理报告",
                "generated_by": "🧠 Knowledge Engineer - 系统清理专家",
                "generation_date": self.analysis_date.isoformat(),
                "analysis_scope": "scripts/utilities目录下的知识积累相关脚本"
            },
            "analysis_summary": {
                "total_scripts_found": analysis["analysis_metadata"]["total_scripts_analyzed"],
                "categories_identified": len(analysis["script_categories"]),
                "cleanup_recommendations": len(analysis["cleanup_recommendations"]["immediate_cleanup"]),
                "archive_candidates": len(analysis["cleanup_recommendations"]["archive_candidates"])
            },
            "new_system_advantages": {
                "background_accumulator": "零干扰的后台知识积累",
                "integrated_support": "完整的开发支持生态系统",
                "quick_extract": "高效的快速知识提取",
                "system_integration": "与MCP记忆系统深度集成"
            },
            "cleanup_benefits": {
                "code_maintainability": "减少代码库复杂度",
                "performance_improvement": "降低系统资源占用",
                "developer_experience": "简化开发环境",
                "focus_enhancement": "专注于核心功能"
            },
            "recommendations": analysis["cleanup_recommendations"]
        }
        
        if cleanup_results:
            report["cleanup_execution"] = cleanup_results
        
        return report

def main():
    """主函数"""
    print("开始旧版本知识积累引擎清理评估...")
    
    cleanup_analyzer = LegacyKnowledgeCleanup()
    
    # 分析旧版本脚本
    analysis = cleanup_analyzer.analyze_legacy_scripts()
    
    # 执行清理（干运行）
    cleanup_results = cleanup_analyzer.execute_cleanup(
        analysis["cleanup_recommendations"], 
        dry_run=True
    )
    
    # 生成报告
    report = cleanup_analyzer.generate_cleanup_report(analysis, cleanup_results)
    
    # 保存报告
    report_path = Path(".kiro/reports/legacy_knowledge_cleanup_report.json")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    # 输出摘要
    print(f"分析完成！发现 {analysis['analysis_metadata']['total_scripts_analyzed']} 个知识积累相关脚本")
    print(f"建议立即清理: {len(analysis['cleanup_recommendations']['immediate_cleanup'])} 个")
    print(f"建议归档: {len(analysis['cleanup_recommendations']['archive_candidates'])} 个")
    print(f"预计节省空间: {cleanup_results['space_saved_kb']:.1f} KB")
    print(f"详细报告: {report_path}")
    
    return {
        "analysis": analysis,
        "cleanup_results": cleanup_results,
        "report": report,
        "report_path": str(report_path)
    }

if __name__ == "__main__":
    result = main()
    print("清理评估完成！")