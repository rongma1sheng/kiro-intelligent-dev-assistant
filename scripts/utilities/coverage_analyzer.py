#!/usr/bin/env python3
"""
测试覆盖率分析器

功能:
1. 分析测试覆盖率报告
2. 识别未覆盖的代码
3. 生成覆盖率改进建议
4. 追踪覆盖率趋势
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any


class CoverageAnalyzer:
    """覆盖率分析器"""
    
    def __init__(self):
        """初始化分析器"""
        self.project_root = Path.cwd()
        self.coverage_file = self.project_root / "coverage.json"
        self.reports_dir = self.project_root / "reports"
        self.reports_dir.mkdir(exist_ok=True)
        
    def analyze(self) -> Dict[str, Any]:
        """分析覆盖率
        
        Returns:
            Dict[str, Any]: 分析结果
        """
        if not self.coverage_file.exists():
            print("❌ 未找到覆盖率报告文件: coverage.json")
            print("请先运行: pytest --cov=src --cov-report=json")
            return {}
        
        with open(self.coverage_file, 'r', encoding='utf-8') as f:
            coverage_data = json.load(f)
        
        # 提取总体覆盖率
        totals = coverage_data.get('totals', {})
        total_coverage = totals.get('percent_covered', 0)
        
        print("=" * 60)
        print("📊 测试覆盖率分析报告")
        print("=" * 60)
        print(f"总覆盖率: {total_coverage:.2f}%")
        print(f"总行数: {totals.get('num_statements', 0)}")
        print(f"已覆盖: {totals.get('covered_lines', 0)}")
        print(f"未覆盖: {totals.get('missing_lines', 0)}")
        print(f"分支覆盖率: {totals.get('percent_covered_display', 'N/A')}")
        print("=" * 60)
        
        # 分析各文件覆盖率
        files_data = coverage_data.get('files', {})
        
        # 找出覆盖率低的文件
        low_coverage_files = []
        for file_path, file_data in files_data.items():
            file_coverage = file_data['summary'].get('percent_covered', 0)
            if file_coverage < 100:
                low_coverage_files.append({
                    'path': file_path,
                    'coverage': file_coverage,
                    'missing_lines': file_data['summary'].get('missing_lines', 0)
                })
        
        # 按覆盖率排序
        low_coverage_files.sort(key=lambda x: x['coverage'])
        
        if low_coverage_files:
            print("\n⚠️  覆盖率不足100%的文件:")
            print("-" * 60)
            for i, file_info in enumerate(low_coverage_files[:10], 1):
                print(f"{i}. {file_info['path']}")
                print(f"   覆盖率: {file_info['coverage']:.2f}%")
                print(f"   未覆盖行数: {file_info['missing_lines']}")
        else:
            print("\n✅ 所有文件覆盖率达到100%")
        
        # 生成改进建议
        suggestions = self._generate_suggestions(low_coverage_files)
        
        if suggestions:
            print("\n💡 改进建议:")
            print("-" * 60)
            for i, suggestion in enumerate(suggestions, 1):
                print(f"{i}. {suggestion}")
        
        # 保存详细报告
        report_file = self.reports_dir / f"coverage_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        report_data = {
            'timestamp': datetime.now().isoformat(),
            'total_coverage': total_coverage,
            'totals': totals,
            'low_coverage_files': low_coverage_files,
            'suggestions': suggestions
        }
        
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)
        
        print(f"\n📄 详细报告已保存: {report_file}")
        
        return report_data
    
    def _generate_suggestions(self, low_coverage_files: List[Dict]) -> List[str]:
        """生成改进建议
        
        Args:
            low_coverage_files: 低覆盖率文件列表
            
        Returns:
            List[str]: 建议列表
        """
        suggestions = []
        
        if not low_coverage_files:
            return suggestions
        
        # 按覆盖率分类
        critical_files = [f for f in low_coverage_files if f['coverage'] < 50]
        medium_files = [f for f in low_coverage_files if 50 <= f['coverage'] < 80]
        low_files = [f for f in low_coverage_files if 80 <= f['coverage'] < 100]
        
        if critical_files:
            suggestions.append(
                f"优先处理 {len(critical_files)} 个覆盖率<50%的文件，这些文件测试严重不足"
            )
        
        if medium_files:
            suggestions.append(
                f"补充 {len(medium_files)} 个覆盖率50-80%的文件的测试用例"
            )
        
        if low_files:
            suggestions.append(
                f"完善 {len(low_files)} 个覆盖率80-100%的文件，达到100%覆盖率"
            )
        
        # 具体文件建议
        if low_coverage_files:
            worst_file = low_coverage_files[0]
            suggestions.append(
                f"从覆盖率最低的文件开始: {worst_file['path']} ({worst_file['coverage']:.2f}%)"
            )
        
        return suggestions
    
    def compare_with_baseline(self, baseline_file: str) -> Dict[str, Any]:
        """与基线对比
        
        Args:
            baseline_file: 基线覆盖率文件路径
            
        Returns:
            Dict[str, Any]: 对比结果
        """
        baseline_path = Path(baseline_file)
        if not baseline_path.exists():
            print(f"❌ 基线文件不存在: {baseline_file}")
            return {}
        
        with open(baseline_path, 'r', encoding='utf-8') as f:
            baseline_data = json.load(f)
        
        with open(self.coverage_file, 'r', encoding='utf-8') as f:
            current_data = json.load(f)
        
        baseline_coverage = baseline_data.get('totals', {}).get('percent_covered', 0)
        current_coverage = current_data.get('totals', {}).get('percent_covered', 0)
        
        diff = current_coverage - baseline_coverage
        
        print("=" * 60)
        print("📈 覆盖率趋势对比")
        print("=" * 60)
        print(f"基线覆盖率: {baseline_coverage:.2f}%")
        print(f"当前覆盖率: {current_coverage:.2f}%")
        print(f"变化: {diff:+.2f}%")
        
        if diff > 0:
            print("✅ 覆盖率提升")
        elif diff < 0:
            print("❌ 覆盖率下降")
        else:
            print("➡️  覆盖率持平")
        
        print("=" * 60)
        
        return {
            'baseline': baseline_coverage,
            'current': current_coverage,
            'diff': diff
        }


def main():
    """主函数"""
    analyzer = CoverageAnalyzer()
    
    if len(sys.argv) > 1 and sys.argv[1] == 'compare':
        if len(sys.argv) < 3:
            print("用法: python scripts/coverage_analyzer.py compare <baseline_file>")
            sys.exit(1)
        analyzer.compare_with_baseline(sys.argv[2])
    else:
        result = analyzer.analyze()
        
        # 如果覆盖率不足100%，返回非0退出码
        total_coverage = result.get('total_coverage', 0)
        if total_coverage < 100:
            sys.exit(1)


if __name__ == "__main__":
    main()
