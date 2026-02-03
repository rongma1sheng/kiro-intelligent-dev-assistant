#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Hook触发逻辑分析报告生成器 v4.0

生成详细的Hook触发逻辑分析报告，包括：
- 触发条件映射表
- 文件类型覆盖分析
- 触发频率预测
- 性能影响评估
- 优化建议
"""

import json
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime


class TriggerAnalysisReporter:
    """触发逻辑分析报告生成器"""
    
    def __init__(self, hooks_dir: str = ".kiro/hooks"):
        self.hooks_dir = Path(hooks_dir)
        self.hooks_data = []
        
    def generate_report(self) -> str:
        """生成完整的分析报告"""
        self._load_hooks_data()
        
        report = []
        report.append("# Hook触发逻辑分析报告 v4.0")
        report.append("")
        report.append(f"**生成时间**: {datetime.now().isoformat()}")
        report.append(f"**分析对象**: {len(self.hooks_data)} 个Hook配置")
        report.append("**分析负责人**: Test Engineer")
        report.append("")
        
        # 1. 触发类型分布
        report.extend(self._analyze_trigger_types())
        
        # 2. 文件模式覆盖分析
        report.extend(self._analyze_file_patterns())
        
        # 3. 触发条件映射表
        report.extend(self._create_trigger_mapping_table())
        
        # 4. 触发频率预测
        report.extend(self._predict_trigger_frequency())
        
        # 5. 性能影响评估
        report.extend(self._assess_performance_impact())
        
        # 6. 优化建议
        report.extend(self._generate_optimization_suggestions())
        
        return "\n".join(report)
    
    def _load_hooks_data(self):
        """加载Hook数据"""
        for hook_file in self.hooks_dir.glob("*.hook"):
            try:
                with open(hook_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    config['file_name'] = hook_file.name
                    self.hooks_data.append(config)
            except Exception as e:
                print(f"加载Hook失败 {hook_file}: {e}")
    
    def _analyze_trigger_types(self) -> List[str]:
        """分析触发类型分布"""
        lines = []
        lines.append("## 📊 触发类型分布分析")
        lines.append("")
        
        # 统计触发类型
        trigger_counts = {}
        for hook in self.hooks_data:
            trigger_type = hook.get("when", {}).get("type", "unknown")
            trigger_counts[trigger_type] = trigger_counts.get(trigger_type, 0) + 1
        
        lines.append("### 触发类型统计")
        lines.append("")
        lines.append("| 触发类型 | 数量 | 百分比 | 说明 |")
        lines.append("|---------|------|--------|------|")
        
        total = len(self.hooks_data)
        for trigger_type, count in sorted(trigger_counts.items()):
            percentage = (count / total) * 100
            description = {
                "fileEdited": "文件编辑时自动触发",
                "userTriggered": "用户手动触发",
                "promptSubmit": "提示提交时自动触发",
                "unknown": "未知或配置错误"
            }.get(trigger_type, "其他")
            
            lines.append(f"| {trigger_type} | {count} | {percentage:.1f}% | {description} |")
        
        lines.append("")
        
        # 分析触发类型合理性
        lines.append("### 触发类型合理性分析")
        lines.append("")
        
        if trigger_counts.get("fileEdited", 0) > 0:
            lines.append(f"✅ **文件编辑触发**: {trigger_counts.get('fileEdited', 0)} 个Hook")
            lines.append("   - 优点: 实时响应，开发体验好")
            lines.append("   - 注意: 需要避免触发冲突")
            lines.append("")
        
        if trigger_counts.get("userTriggered", 0) > 0:
            lines.append(f"✅ **用户触发**: {trigger_counts.get('userTriggered', 0)} 个Hook")
            lines.append("   - 优点: 用户可控，不会意外触发")
            lines.append("   - 适用: 重量级操作，如全量测试")
            lines.append("")
        
        if trigger_counts.get("promptSubmit", 0) > 0:
            lines.append(f"✅ **提示提交触发**: {trigger_counts.get('promptSubmit', 0)} 个Hook")
            lines.append("   - 优点: 智能响应用户意图")
            lines.append("   - 注意: 需要准确的意图识别")
            lines.append("")
        
        return lines
    
    def _analyze_file_patterns(self) -> List[str]:
        """分析文件模式覆盖"""
        lines = []
        lines.append("## 📁 文件模式覆盖分析")
        lines.append("")
        
        # 收集所有文件模式
        file_patterns = {}
        for hook in self.hooks_data:
            if hook.get("when", {}).get("type") == "fileEdited":
                patterns = hook.get("when", {}).get("patterns", [])
                if isinstance(patterns, str):
                    patterns = [patterns]
                
                for pattern in patterns:
                    if pattern not in file_patterns:
                        file_patterns[pattern] = []
                    file_patterns[pattern].append(hook.get("name", "unknown"))
        
        lines.append("### 文件模式映射表")
        lines.append("")
        lines.append("| 文件模式 | 触发Hook | 覆盖说明 |")
        lines.append("|---------|----------|----------|")
        
        for pattern, hooks in sorted(file_patterns.items()):
            hooks_str = ", ".join(hooks)
            coverage_desc = self._describe_pattern_coverage(pattern)
            lines.append(f"| `{pattern}` | {hooks_str} | {coverage_desc} |")
        
        lines.append("")
        
        # 分析覆盖重叠
        lines.append("### 覆盖重叠分析")
        lines.append("")
        
        overlaps = []
        patterns_list = list(file_patterns.keys())
        for i, pattern1 in enumerate(patterns_list):
            for pattern2 in patterns_list[i+1:]:
                if self._patterns_overlap(pattern1, pattern2):
                    overlaps.append((pattern1, pattern2, file_patterns[pattern1], file_patterns[pattern2]))
        
        if overlaps:
            lines.append("⚠️ **发现模式重叠**:")
            lines.append("")
            for p1, p2, hooks1, hooks2 in overlaps:
                lines.append(f"- `{p1}` vs `{p2}`")
                lines.append(f"  - Hook1: {', '.join(hooks1)}")
                lines.append(f"  - Hook2: {', '.join(hooks2)}")
                lines.append("")
        else:
            lines.append("✅ **无模式重叠**: 所有文件模式都有明确的边界")
            lines.append("")
        
        return lines
    
    def _create_trigger_mapping_table(self) -> List[str]:
        """创建触发条件映射表"""
        lines = []
        lines.append("## 🎯 触发条件映射表")
        lines.append("")
        
        lines.append("### 完整触发条件表")
        lines.append("")
        lines.append("| Hook名称 | 触发类型 | 触发条件 | 执行频率 | 性能影响 |")
        lines.append("|---------|----------|----------|----------|----------|")
        
        for hook in self.hooks_data:
            name = hook.get("name", "unknown")
            trigger_type = hook.get("when", {}).get("type", "unknown")
            
            # 构建触发条件描述
            if trigger_type == "fileEdited":
                patterns = hook.get("when", {}).get("patterns", [])
                if isinstance(patterns, str):
                    patterns = [patterns]
                condition = f"编辑文件: {', '.join(patterns)}"
                frequency = "高频"
                performance = "低"
            elif trigger_type == "userTriggered":
                condition = "用户手动触发"
                frequency = "低频"
                performance = "中等"
            elif trigger_type == "promptSubmit":
                condition = "提示提交时"
                frequency = "中频"
                performance = "低"
            else:
                condition = "未知"
                frequency = "未知"
                performance = "未知"
            
            lines.append(f"| {name} | {trigger_type} | {condition} | {frequency} | {performance} |")
        
        lines.append("")
        return lines
    
    def _predict_trigger_frequency(self) -> List[str]:
        """预测触发频率"""
        lines = []
        lines.append("## 📈 触发频率预测")
        lines.append("")
        
        # 基于文件类型预测触发频率
        file_edit_hooks = [h for h in self.hooks_data if h.get("when", {}).get("type") == "fileEdited"]
        
        lines.append("### 基于开发活动的触发频率预测")
        lines.append("")
        lines.append("| 开发活动 | 涉及文件类型 | 触发Hook | 预计频率/天 |")
        lines.append("|---------|-------------|----------|-------------|")
        
        activities = [
            ("编写源代码", "src/**/*.py", "源代码360度调试系统", "20-50次"),
            ("编写测试", "tests/**/*.py", "测试文件质量防护", "10-30次"),
            ("更新PRD", "PRD.md", "PRD文档同步检查", "1-5次"),
            ("手动测试", "用户触发", "自动化部署测试", "2-10次"),
            ("质量检查", "用户触发", "统一质量检查系统", "1-3次"),
        ]
        
        for activity, file_type, hook_name, frequency in activities:
            lines.append(f"| {activity} | {file_type} | {hook_name} | {frequency} |")
        
        lines.append("")
        
        # 触发负载分析
        lines.append("### 系统负载分析")
        lines.append("")
        
        total_file_hooks = len([h for h in self.hooks_data if h.get("when", {}).get("type") == "fileEdited"])
        total_user_hooks = len([h for h in self.hooks_data if h.get("when", {}).get("type") == "userTriggered"])
        
        lines.append(f"- **文件编辑触发Hook**: {total_file_hooks} 个")
        lines.append(f"  - 预计日触发次数: {total_file_hooks * 30} - {total_file_hooks * 80} 次")
        lines.append(f"  - 系统负载: {'高' if total_file_hooks > 5 else '中等' if total_file_hooks > 2 else '低'}")
        lines.append("")
        
        lines.append(f"- **用户触发Hook**: {total_user_hooks} 个")
        lines.append(f"  - 预计日触发次数: {total_user_hooks * 2} - {total_user_hooks * 10} 次")
        lines.append(f"  - 系统负载: 低")
        lines.append("")
        
        return lines
    
    def _assess_performance_impact(self) -> List[str]:
        """评估性能影响"""
        lines = []
        lines.append("## ⚡ 性能影响评估")
        lines.append("")
        
        lines.append("### Hook性能分类")
        lines.append("")
        lines.append("| Hook名称 | 预估执行时间 | 资源消耗 | 性能等级 | 优化建议 |")
        lines.append("|---------|-------------|----------|----------|----------|")
        
        for hook in self.hooks_data:
            name = hook.get("name", "unknown")
            
            # 基于Hook名称和功能预估性能
            if "360度调试" in name or "全量" in name:
                exec_time = "10-30秒"
                resource = "高"
                level = "重量级"
                suggestion = "考虑异步执行"
            elif "实时" in name or "防护" in name:
                exec_time = "1-5秒"
                resource = "低"
                level = "轻量级"
                suggestion = "保持当前设计"
            elif "部署测试" in name:
                exec_time = "30-120秒"
                resource = "高"
                level = "重量级"
                suggestion = "用户触发，可接受"
            else:
                exec_time = "5-15秒"
                resource = "中等"
                level = "中等"
                suggestion = "监控执行时间"
            
            lines.append(f"| {name} | {exec_time} | {resource} | {level} | {suggestion} |")
        
        lines.append("")
        
        # 性能优化建议
        lines.append("### 性能优化策略")
        lines.append("")
        
        heavy_hooks = [h for h in self.hooks_data if "360度" in h.get("name", "") or "全量" in h.get("name", "")]
        if heavy_hooks:
            lines.append("🔧 **重量级Hook优化**:")
            for hook in heavy_hooks:
                lines.append(f"- {hook.get('name', 'unknown')}: 考虑增加缓存机制，避免重复执行")
            lines.append("")
        
        realtime_hooks = [h for h in self.hooks_data if "实时" in h.get("name", "")]
        if realtime_hooks:
            lines.append("⚡ **实时Hook优化**:")
            for hook in realtime_hooks:
                lines.append(f"- {hook.get('name', 'unknown')}: 保持轻量级，专注核心检查")
            lines.append("")
        
        return lines
    
    def _generate_optimization_suggestions(self) -> List[str]:
        """生成优化建议"""
        lines = []
        lines.append("## 💡 优化建议")
        lines.append("")
        
        # 架构优化建议
        lines.append("### 🏗️ 架构优化建议")
        lines.append("")
        
        file_hooks_count = len([h for h in self.hooks_data if h.get("when", {}).get("type") == "fileEdited"])
        if file_hooks_count > 3:
            lines.append("1. **文件编辑触发优化**:")
            lines.append("   - 当前有过多的文件编辑触发Hook，考虑合并相似功能")
            lines.append("   - 建议实现Hook执行优先级机制")
            lines.append("   - 添加Hook执行缓存，避免短时间内重复触发")
            lines.append("")
        
        # 性能优化建议
        lines.append("### ⚡ 性能优化建议")
        lines.append("")
        lines.append("1. **异步执行机制**:")
        lines.append("   - 重量级Hook应该异步执行，不阻塞用户操作")
        lines.append("   - 实现Hook执行队列，避免并发冲突")
        lines.append("")
        
        lines.append("2. **智能缓存策略**:")
        lines.append("   - 为文件编辑触发Hook添加基于文件修改时间的缓存")
        lines.append("   - 缓存Hook执行结果，避免重复计算")
        lines.append("")
        
        # 用户体验优化
        lines.append("### 🎨 用户体验优化建议")
        lines.append("")
        lines.append("1. **执行反馈机制**:")
        lines.append("   - 为长时间执行的Hook添加进度指示")
        lines.append("   - 提供Hook执行历史和结果查看")
        lines.append("")
        
        lines.append("2. **配置灵活性**:")
        lines.append("   - 允许用户禁用特定Hook")
        lines.append("   - 提供Hook执行频率配置选项")
        lines.append("")
        
        # 监控和维护建议
        lines.append("### 📊 监控和维护建议")
        lines.append("")
        lines.append("1. **执行监控**:")
        lines.append("   - 记录Hook执行时间和成功率")
        lines.append("   - 监控Hook触发频率和系统负载")
        lines.append("")
        
        lines.append("2. **定期维护**:")
        lines.append("   - 月度审查Hook配置和性能")
        lines.append("   - 季度评估Hook架构合理性")
        lines.append("")
        
        return lines
    
    def _describe_pattern_coverage(self, pattern: str) -> str:
        """描述模式覆盖范围"""
        if pattern.startswith("src/"):
            return "源代码文件"
        elif pattern.startswith("tests/"):
            return "测试文件"
        elif "*.py" in pattern:
            return "Python文件"
        elif "*.md" in pattern:
            return "Markdown文档"
        elif "**/*" in pattern:
            return "递归匹配所有文件"
        else:
            return "特定文件类型"
    
    def _patterns_overlap(self, pattern1: str, pattern2: str) -> bool:
        """检查两个模式是否重叠"""
        # 简单的重叠检测逻辑
        if pattern1 == pattern2:
            return True
        
        # 检查包含关系
        if "**/*" in pattern1 and pattern2.startswith(pattern1.replace("**/*", "")):
            return True
        if "**/*" in pattern2 and pattern1.startswith(pattern2.replace("**/*", "")):
            return True
        
        return False


def main():
    """主函数"""
    reporter = TriggerAnalysisReporter()
    report_content = reporter.generate_report()
    
    # 保存报告
    report_file = Path(".kiro/reports/hook_trigger_analysis_report.md")
    report_file.parent.mkdir(exist_ok=True)
    
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report_content)
    
    print(f"📊 Hook触发逻辑分析报告已生成: {report_file}")
    print("🔍 报告包含详细的触发逻辑分析和优化建议")
    
    return 0


if __name__ == "__main__":
    exit(main())