#!/usr/bin/env python3
"""
Hook系统分析器

作为🔍 Code Review Specialist，我负责分析Hook系统的逻辑闭环、
缺陷、重叠和冗余问题，确保系统架构的合理性和效率。
"""

import json
import os
from pathlib import Path
from datetime import datetime
from collections import defaultdict

class HookSystemAnalyzer:
    """Hook系统分析器"""
    
    def __init__(self):
        self.hooks_dir = Path(".kiro/hooks")
        self.hooks = {}
        self.analysis_report = {
            "logical_closure": {},
            "defects": [],
            "overlaps": [],
            "redundancies": [],
            "optimization_suggestions": []
        }
        
    def load_all_hooks(self):
        """加载所有Hook文件"""
        print("📂 加载Hook文件...")
        
        hook_files = list(self.hooks_dir.glob("*.kiro.hook"))
        
        for hook_file in hook_files:
            try:
                with open(hook_file, 'r', encoding='utf-8') as f:
                    hook_data = json.load(f)
                    self.hooks[hook_file.stem] = {
                        'file': hook_file.name,
                        'data': hook_data
                    }
                    print(f"   ✅ 加载: {hook_file.name}")
            except Exception as e:
                print(f"   ❌ 加载失败: {hook_file.name} - {e}")
                self.analysis_report["defects"].append({
                    "type": "加载错误",
                    "file": hook_file.name,
                    "error": str(e),
                    "severity": "高"
                })
        
        print(f"📊 总计加载Hook: {len(self.hooks)} 个")
        
    def analyze_logical_closure(self):
        """分析逻辑闭环"""
        print("🔄 分析逻辑闭环...")
        
        # 分析触发类型覆盖
        trigger_types = defaultdict(list)
        file_patterns = defaultdict(list)
        
        for hook_name, hook_info in self.hooks.items():
            hook_data = hook_info['data']
            when_config = hook_data.get('when', {})
            trigger_type = when_config.get('type')
            
            if trigger_type:
                trigger_types[trigger_type].append(hook_name)
                
                # 分析文件模式
                patterns = when_config.get('patterns', [])
                for pattern in patterns:
                    file_patterns[pattern].append(hook_name)
        
        # 检查触发类型覆盖完整性
        expected_triggers = ['fileEdited', 'fileCreated', 'fileDeleted', 'userTriggered', 'promptSubmit', 'agentStop']
        missing_triggers = []
        
        for trigger in expected_triggers:
            if trigger not in trigger_types:
                missing_triggers.append(trigger)
        
        self.analysis_report["logical_closure"] = {
            "trigger_coverage": {
                "covered": list(trigger_types.keys()),
                "missing": missing_triggers,
                "coverage_percentage": (len(trigger_types) / len(expected_triggers)) * 100
            },
            "trigger_distribution": dict(trigger_types),
            "file_pattern_coverage": dict(file_patterns)
        }
        
        print(f"   📊 触发类型覆盖: {len(trigger_types)}/{len(expected_triggers)} ({self.analysis_report['logical_closure']['trigger_coverage']['coverage_percentage']:.1f}%)")
        
        if missing_triggers:
            print(f"   ⚠️ 缺失触发类型: {', '.join(missing_triggers)}")
        
    def detect_overlaps(self):
        """检测重叠问题"""
        print("🔍 检测重叠问题...")
        
        overlaps = []
        
        # 检查相同触发条件的Hook
        trigger_groups = defaultdict(list)
        
        for hook_name, hook_info in self.hooks.items():
            hook_data = hook_info['data']
            when_config = hook_data.get('when', {})
            
            trigger_key = (
                when_config.get('type'),
                tuple(sorted(when_config.get('patterns', [])))
            )
            
            trigger_groups[trigger_key].append(hook_name)
        
        # 找出重叠的触发条件
        for trigger_key, hooks in trigger_groups.items():
            if len(hooks) > 1:
                trigger_type, patterns = trigger_key
                
                # 分析功能重叠程度
                overlap_analysis = self._analyze_functional_overlap(hooks)
                
                overlaps.append({
                    "trigger_type": trigger_type,
                    "patterns": list(patterns),
                    "hooks": hooks,
                    "overlap_level": overlap_analysis["level"],
                    "description": overlap_analysis["description"],
                    "recommendation": overlap_analysis["recommendation"]
                })
        
        # 检查功能性重叠
        functional_overlaps = self._detect_functional_overlaps()
        overlaps.extend(functional_overlaps)
        
        self.analysis_report["overlaps"] = overlaps
        
        print(f"   🔍 发现重叠问题: {len(overlaps)} 个")
        
        for overlap in overlaps:
            print(f"      ⚠️ {overlap['overlap_level']}: {', '.join(overlap['hooks'])}")
    
    def _analyze_functional_overlap(self, hooks):
        """分析功能重叠程度"""
        # 简化的功能重叠分析
        hook_descriptions = []
        
        for hook_name in hooks:
            hook_data = self.hooks[hook_name]['data']
            description = hook_data.get('description', '')
            prompt = hook_data.get('then', {}).get('prompt', '')
            hook_descriptions.append((hook_name, description, prompt))
        
        # 基于关键词分析重叠程度
        quality_keywords = ['质量', '检测', '测试', 'quality', 'test', 'check']
        debug_keywords = ['调试', '错误', 'debug', 'error', 'bug']
        task_keywords = ['任务', '管理', 'task', 'management']
        
        quality_count = sum(1 for _, desc, prompt in hook_descriptions 
                          if any(kw in desc.lower() + prompt.lower() for kw in quality_keywords))
        debug_count = sum(1 for _, desc, prompt in hook_descriptions 
                        if any(kw in desc.lower() + prompt.lower() for kw in debug_keywords))
        task_count = sum(1 for _, desc, prompt in hook_descriptions 
                       if any(kw in desc.lower() + prompt.lower() for kw in task_keywords))
        
        if quality_count > 1:
            return {
                "level": "高度重叠",
                "description": f"{quality_count}个Hook都涉及质量检测功能",
                "recommendation": "考虑合并或明确分工"
            }
        elif debug_count > 1:
            return {
                "level": "中度重叠", 
                "description": f"{debug_count}个Hook都涉及调试功能",
                "recommendation": "明确各自的调试范围"
            }
        elif task_count > 1:
            return {
                "level": "中度重叠",
                "description": f"{task_count}个Hook都涉及任务管理",
                "recommendation": "区分任务管理的不同阶段"
            }
        else:
            return {
                "level": "轻微重叠",
                "description": "触发条件相同但功能不同",
                "recommendation": "可以保持现状，注意执行顺序"
            }
    
    def _detect_functional_overlaps(self):
        """检测功能性重叠"""
        functional_overlaps = []
        
        # 质量检测功能重叠分析
        quality_hooks = []
        for hook_name, hook_info in self.hooks.items():
            hook_data = hook_info['data']
            description = hook_data.get('description', '').lower()
            prompt = hook_data.get('then', {}).get('prompt', '').lower()
            
            if any(kw in description + prompt for kw in ['质量', '检测', 'quality', 'check']):
                quality_hooks.append(hook_name)
        
        if len(quality_hooks) > 2:
            functional_overlaps.append({
                "trigger_type": "功能重叠",
                "patterns": ["质量检测"],
                "hooks": quality_hooks,
                "overlap_level": "功能重叠",
                "description": f"{len(quality_hooks)}个Hook都涉及质量检测功能",
                "recommendation": "建立质量检测的分层架构，避免重复检测"
            })
        
        return functional_overlaps
    
    def detect_redundancies(self):
        """检测冗余代码和功能"""
        print("🔄 检测冗余问题...")
        
        redundancies = []
        
        # 检测相似的prompt内容
        prompt_similarities = self._analyze_prompt_similarities()
        redundancies.extend(prompt_similarities)
        
        # 检测版本不一致
        version_issues = self._check_version_consistency()
        redundancies.extend(version_issues)
        
        # 检测无效或过时的Hook
        obsolete_hooks = self._detect_obsolete_hooks()
        redundancies.extend(obsolete_hooks)
        
        self.analysis_report["redundancies"] = redundancies
        
        print(f"   🔄 发现冗余问题: {len(redundancies)} 个")
        
        for redundancy in redundancies:
            print(f"      ⚠️ {redundancy['type']}: {redundancy['description']}")
    
    def _analyze_prompt_similarities(self):
        """分析prompt相似性"""
        similarities = []
        
        prompts = {}
        for hook_name, hook_info in self.hooks.items():
            hook_data = hook_info['data']
            prompt = hook_data.get('then', {}).get('prompt', '')
            if prompt:
                prompts[hook_name] = prompt
        
        # 简化的相似性检测（基于关键短语）
        common_phrases = [
            "Mac环境自动适配",
            "使用python3命令",
            "使用zsh作为默认shell",
            "支持Apple Silicon和Intel芯片"
        ]
        
        for phrase in common_phrases:
            matching_hooks = [hook for hook, prompt in prompts.items() if phrase in prompt]
            if len(matching_hooks) > 3:  # 超过3个Hook包含相同短语
                similarities.append({
                    "type": "重复内容",
                    "description": f"'{phrase}' 在 {len(matching_hooks)} 个Hook中重复",
                    "hooks": matching_hooks,
                    "recommendation": "考虑提取为公共模板或配置"
                })
        
        return similarities
    
    def _check_version_consistency(self):
        """检查版本一致性"""
        version_issues = []
        
        versions = defaultdict(list)
        for hook_name, hook_info in self.hooks.items():
            hook_data = hook_info['data']
            version = hook_data.get('version', 'unknown')
            versions[version].append(hook_name)
        
        if len(versions) > 2:  # 版本过于分散
            version_issues.append({
                "type": "版本不一致",
                "description": f"发现 {len(versions)} 个不同版本: {list(versions.keys())}",
                "hooks": list(self.hooks.keys()),
                "recommendation": "统一Hook版本管理，建议使用语义化版本"
            })
        
        return version_issues
    
    def _detect_obsolete_hooks(self):
        """检测过时的Hook"""
        obsolete = []
        
        # 检测可能过时的Hook（基于描述和功能）
        for hook_name, hook_info in self.hooks.items():
            hook_data = hook_info['data']
            description = hook_data.get('description', '').lower()
            
            # 检测Windows特定的Hook（在非Windows环境中可能过时）
            if 'windows' in description and 'windows' in hook_name:
                obsolete.append({
                    "type": "平台特定",
                    "description": f"Windows特定Hook: {hook_name}",
                    "hooks": [hook_name],
                    "recommendation": "根据实际运行平台决定是否保留"
                })
        
        return obsolete
    
    def detect_defects(self):
        """检测缺陷"""
        print("🐛 检测系统缺陷...")
        
        defects = []
        
        for hook_name, hook_info in self.hooks.items():
            hook_data = hook_info['data']
            
            # 检查必需字段
            required_fields = ['name', 'version', 'description', 'when', 'then']
            for field in required_fields:
                if field not in hook_data:
                    defects.append({
                        "type": "缺失字段",
                        "file": hook_info['file'],
                        "field": field,
                        "severity": "中",
                        "description": f"Hook {hook_name} 缺失必需字段: {field}"
                    })
            
            # 检查when配置
            when_config = hook_data.get('when', {})
            if 'type' not in when_config:
                defects.append({
                    "type": "配置错误",
                    "file": hook_info['file'],
                    "field": "when.type",
                    "severity": "高",
                    "description": f"Hook {hook_name} 缺失触发类型配置"
                })
            
            # 检查then配置
            then_config = hook_data.get('then', {})
            if 'type' not in then_config:
                defects.append({
                    "type": "配置错误",
                    "file": hook_info['file'],
                    "field": "then.type",
                    "severity": "高",
                    "description": f"Hook {hook_name} 缺失执行类型配置"
                })
            
            # 检查prompt内容
            if then_config.get('type') == 'askAgent' and not then_config.get('prompt'):
                defects.append({
                    "type": "配置错误",
                    "file": hook_info['file'],
                    "field": "then.prompt",
                    "severity": "高",
                    "description": f"Hook {hook_name} askAgent类型缺失prompt内容"
                })
        
        self.analysis_report["defects"].extend(defects)
        
        print(f"   🐛 发现缺陷: {len(defects)} 个")
        
        for defect in defects:
            print(f"      ❌ {defect['severity']}: {defect['description']}")
    
    def generate_optimization_suggestions(self):
        """生成优化建议"""
        print("💡 生成优化建议...")
        
        suggestions = []
        
        # 基于分析结果生成建议
        closure_analysis = self.analysis_report["logical_closure"]
        
        # 触发覆盖建议
        if closure_analysis["trigger_coverage"]["coverage_percentage"] < 100:
            missing = closure_analysis["trigger_coverage"]["missing"]
            suggestions.append({
                "category": "功能完整性",
                "priority": "中",
                "suggestion": f"考虑添加缺失的触发类型: {', '.join(missing)}",
                "impact": "提升Hook系统的事件覆盖完整性",
                "implementation": "根据实际需求添加相应的Hook"
            })
        
        # 重叠问题建议
        if self.analysis_report["overlaps"]:
            high_overlap_count = len([o for o in self.analysis_report["overlaps"] if o["overlap_level"] == "高度重叠"])
            if high_overlap_count > 0:
                suggestions.append({
                    "category": "架构优化",
                    "priority": "高",
                    "suggestion": f"解决 {high_overlap_count} 个高度重叠问题",
                    "impact": "减少资源浪费，提升执行效率",
                    "implementation": "合并功能相似的Hook或明确分工边界"
                })
        
        # 冗余问题建议
        if self.analysis_report["redundancies"]:
            redundancy_count = len(self.analysis_report["redundancies"])
            suggestions.append({
                "category": "代码优化",
                "priority": "中",
                "suggestion": f"清理 {redundancy_count} 个冗余问题",
                "impact": "简化维护，提升可读性",
                "implementation": "提取公共模板，统一版本管理"
            })
        
        # 缺陷修复建议
        high_severity_defects = len([d for d in self.analysis_report["defects"] if d.get("severity") == "高"])
        if high_severity_defects > 0:
            suggestions.append({
                "category": "缺陷修复",
                "priority": "高",
                "suggestion": f"修复 {high_severity_defects} 个高严重性缺陷",
                "impact": "确保Hook系统正常运行",
                "implementation": "补充缺失配置，修正错误设置"
            })
        
        # 性能优化建议
        total_hooks = len(self.hooks)
        if total_hooks > 15:
            suggestions.append({
                "category": "性能优化",
                "priority": "中",
                "suggestion": f"当前Hook数量 ({total_hooks}) 较多，考虑优化",
                "impact": "减少系统开销，提升响应速度",
                "implementation": "合并相似功能，建立Hook优先级系统"
            })
        
        self.analysis_report["optimization_suggestions"] = suggestions
        
        print(f"   💡 生成优化建议: {len(suggestions)} 条")
        
        for suggestion in suggestions:
            print(f"      {suggestion['priority']}: {suggestion['suggestion']}")
    
    def generate_analysis_report(self):
        """生成分析报告"""
        print("📊 生成Hook系统分析报告...")
        
        report = {
            "metadata": {
                "analysis_date": datetime.now().isoformat(),
                "analyzer": "🔍 Code Review Specialist",
                "total_hooks": len(self.hooks),
                "analysis_scope": "逻辑闭环、缺陷、重叠、冗余分析"
            },
            "executive_summary": {
                "overall_health": self._calculate_overall_health(),
                "critical_issues": len([d for d in self.analysis_report["defects"] if d.get("severity") == "高"]),
                "optimization_opportunities": len(self.analysis_report["optimization_suggestions"]),
                "architecture_score": self._calculate_architecture_score()
            },
            "detailed_analysis": self.analysis_report,
            "hook_inventory": {
                hook_name: {
                    "file": hook_info["file"],
                    "version": hook_info["data"].get("version", "unknown"),
                    "trigger_type": hook_info["data"].get("when", {}).get("type", "unknown"),
                    "description": hook_info["data"].get("description", "")
                }
                for hook_name, hook_info in self.hooks.items()
            },
            "recommendations": {
                "immediate_actions": [s for s in self.analysis_report["optimization_suggestions"] if s["priority"] == "高"],
                "medium_term_improvements": [s for s in self.analysis_report["optimization_suggestions"] if s["priority"] == "中"],
                "long_term_optimizations": [s for s in self.analysis_report["optimization_suggestions"] if s["priority"] == "低"]
            }
        }
        
        # 保存报告
        report_path = Path(".kiro/reports/hook_system_analysis_report.json")
        report_path.parent.mkdir(exist_ok=True)
        
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Hook系统分析报告已保存到: {report_path}")
        
        return report
    
    def _calculate_overall_health(self):
        """计算系统整体健康度"""
        health_score = 100
        
        # 扣分项
        critical_defects = len([d for d in self.analysis_report["defects"] if d.get("severity") == "高"])
        high_overlaps = len([o for o in self.analysis_report["overlaps"] if o["overlap_level"] == "高度重叠"])
        redundancies = len(self.analysis_report["redundancies"])
        
        health_score -= critical_defects * 20  # 每个严重缺陷扣20分
        health_score -= high_overlaps * 15     # 每个高度重叠扣15分
        health_score -= redundancies * 5      # 每个冗余问题扣5分
        
        health_score = max(0, health_score)
        
        if health_score >= 90:
            return "优秀"
        elif health_score >= 75:
            return "良好"
        elif health_score >= 60:
            return "一般"
        else:
            return "需要改进"
    
    def _calculate_architecture_score(self):
        """计算架构评分"""
        score = 100
        
        # 触发覆盖完整性
        coverage = self.analysis_report["logical_closure"]["trigger_coverage"]["coverage_percentage"]
        score = score * (coverage / 100)
        
        # 重叠惩罚
        overlaps = len(self.analysis_report["overlaps"])
        score -= overlaps * 5
        
        # 冗余惩罚
        redundancies = len(self.analysis_report["redundancies"])
        score -= redundancies * 3
        
        return max(0, min(100, score))
    
    def execute_full_analysis(self):
        """执行完整分析"""
        print("🔍 开始Hook系统全面分析...")
        print("=" * 60)
        
        try:
            # 1. 加载所有Hook
            self.load_all_hooks()
            
            # 2. 分析逻辑闭环
            self.analyze_logical_closure()
            
            # 3. 检测重叠问题
            self.detect_overlaps()
            
            # 4. 检测冗余问题
            self.detect_redundancies()
            
            # 5. 检测缺陷
            self.detect_defects()
            
            # 6. 生成优化建议
            self.generate_optimization_suggestions()
            
            # 7. 生成分析报告
            report = self.generate_analysis_report()
            
            print("=" * 60)
            print("🎉 Hook系统分析完成!")
            print(f"📊 系统健康度: {report['executive_summary']['overall_health']}")
            print(f"🏗️ 架构评分: {report['executive_summary']['architecture_score']:.1f}/100")
            print(f"🚨 严重问题: {report['executive_summary']['critical_issues']} 个")
            print(f"💡 优化机会: {report['executive_summary']['optimization_opportunities']} 个")
            
            return True
            
        except Exception as e:
            print(f"❌ Hook系统分析过程中出现错误: {str(e)}")
            return False

def main():
    """主函数"""
    print("🔍 Hook系统分析器")
    print("作为Code Review Specialist，我将分析Hook系统的完整性和优化机会")
    print()
    
    analyzer = HookSystemAnalyzer()
    success = analyzer.execute_full_analysis()
    
    if success:
        print("\n🎯 Hook系统分析完成!")
        print("📋 请查看生成的报告了解详细分析结果和优化建议")
    else:
        print("\n⚠️ Hook系统分析过程中遇到问题")

if __name__ == "__main__":
    main()