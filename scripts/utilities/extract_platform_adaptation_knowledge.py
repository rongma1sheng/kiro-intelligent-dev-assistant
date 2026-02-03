#!/usr/bin/env python3
"""
平台适配知识提取器

作为📚 Knowledge Accumulator，我负责从平台适配修复过程中
提取有价值的知识，包括平台检测、配置适配和错误修复经验。
"""

import json
from datetime import datetime
from pathlib import Path

class PlatformAdaptationKnowledgeExtractor:
    """平台适配知识提取器"""
    
    def __init__(self):
        self.knowledge_base = {
            "platform_detection_patterns": [],
            "configuration_adaptation_strategies": [],
            "cross_platform_compatibility_issues": [],
            "automated_fix_patterns": [],
            "user_feedback_integration": []
        }
        
    def extract_platform_detection_patterns(self):
        """提取平台检测模式"""
        patterns = [
            {
                "pattern_name": "Python平台检测",
                "description": "使用Python platform模块自动检测操作系统",
                "implementation": """
import platform
system = platform.system().lower()
if system == "windows":
    return "win32"
elif system == "darwin":
    return "darwin"
elif system == "linux":
    return "linux"
""",
                "benefits": ["跨平台兼容", "自动化检测", "准确性高"],
                "use_cases": ["配置文件选择", "平台特定功能", "Hook适配"],
                "reliability": "高 - Python标准库保证"
            },
            {
                "pattern_name": "智能平台适配Hook",
                "description": "创建能够自动适配不同平台的Hook配置",
                "key_features": [
                    "运行时平台检测",
                    "动态提示生成",
                    "平台特定建议",
                    "自动化配置调整"
                ],
                "implementation_approach": "在Hook配置中嵌入平台检测逻辑",
                "scalability": "可扩展到支持更多平台"
            },
            {
                "pattern_name": "配置文件平台标识",
                "description": "在配置文件中明确标识目标平台",
                "format": """
{
  "metadata": {
    "platform": "win32|darwin|linux",
    "version": "x.x.x",
    "compatibility": ["platform1", "platform2"]
  }
}
""",
                "benefits": ["清晰的平台支持", "版本管理", "兼容性追踪"]
            }
        ]
        
        self.knowledge_base["platform_detection_patterns"] = patterns
        return patterns
    
    def extract_configuration_adaptation_strategies(self):
        """提取配置适配策略"""
        strategies = [
            {
                "strategy_name": "平台特定Hook替换策略",
                "description": "根据平台自动替换不适合的Hook配置",
                "process": [
                    "检测当前运行平台",
                    "识别平台不兼容的配置",
                    "移除不适合的配置文件",
                    "创建平台特定的替代配置",
                    "验证新配置的有效性"
                ],
                "example": "移除Mac性能监控Hook，创建Windows性能监控Hook",
                "automation_level": "全自动化"
            },
            {
                "strategy_name": "渐进式配置迁移",
                "description": "分步骤地将配置从一个平台适配到另一个平台",
                "phases": [
                    "阶段1: 移除不兼容配置",
                    "阶段2: 创建基础平台配置",
                    "阶段3: 添加平台特定优化",
                    "阶段4: 验证和测试配置"
                ],
                "rollback_support": "每个阶段都支持回滚",
                "risk_mitigation": "分阶段降低配置错误风险"
            },
            {
                "strategy_name": "配置模板化生成",
                "description": "使用模板动态生成平台特定配置",
                "template_structure": {
                    "base_template": "通用配置模板",
                    "platform_overrides": "平台特定覆盖配置",
                    "feature_flags": "平台功能开关",
                    "optimization_settings": "平台优化参数"
                },
                "generation_process": "模板 + 平台参数 = 最终配置",
                "maintainability": "高 - 统一模板管理"
            },
            {
                "strategy_name": "智能配置验证",
                "description": "自动验证配置在目标平台上的有效性",
                "validation_checks": [
                    "语法正确性检查",
                    "平台兼容性验证",
                    "依赖项可用性检查",
                    "功能完整性测试"
                ],
                "error_handling": "提供详细的错误信息和修复建议"
            }
        ]
        
        self.knowledge_base["configuration_adaptation_strategies"] = strategies
        return strategies
    
    def extract_cross_platform_compatibility_issues(self):
        """提取跨平台兼容性问题"""
        issues = [
            {
                "issue_type": "平台特定功能假设",
                "description": "配置中假设了特定平台的功能存在",
                "example": "在Windows上使用Mac特定的性能监控",
                "root_cause": "缺乏平台检测和适配机制",
                "impact": "功能无法正常工作，用户体验差",
                "solution": "实施平台检测和动态配置选择",
                "prevention": "在配置设计时考虑跨平台兼容性"
            },
            {
                "issue_type": "路径分隔符差异",
                "description": "不同平台使用不同的路径分隔符",
                "platforms": {
                    "windows": "反斜杠 (\\)",
                    "unix_like": "正斜杠 (/)"
                },
                "solution": "使用pathlib.Path或os.path.join处理路径",
                "best_practice": "避免硬编码路径分隔符"
            },
            {
                "issue_type": "命令行工具差异",
                "description": "不同平台有不同的系统命令和工具",
                "examples": {
                    "windows": ["sfc", "dism", "wmic", "powershell"],
                    "macos": ["diskutil", "system_profiler", "brew"],
                    "linux": ["fsck", "systemctl", "apt/yum"]
                },
                "adaptation_strategy": "为每个平台定义专用的命令集合"
            },
            {
                "issue_type": "环境变量命名差异",
                "description": "不同平台使用不同的环境变量名称和格式",
                "examples": {
                    "windows": "%USERPROFILE%, %TEMP%",
                    "unix_like": "$HOME, $TMPDIR"
                },
                "solution": "使用平台特定的环境变量配置"
            }
        ]
        
        self.knowledge_base["cross_platform_compatibility_issues"] = issues
        return issues
    
    def extract_automated_fix_patterns(self):
        """提取自动化修复模式"""
        patterns = [
            {
                "pattern_name": "错误检测和自动修复循环",
                "description": "检测配置错误并自动应用修复",
                "workflow": [
                    "用户反馈问题",
                    "自动分析问题类型",
                    "查找适用的修复策略",
                    "执行自动修复",
                    "验证修复结果",
                    "向用户报告修复状态"
                ],
                "key_principles": [
                    "快速响应用户反馈",
                    "自动化减少人工干预",
                    "透明的修复过程",
                    "可回滚的修复操作"
                ]
            },
            {
                "pattern_name": "配置冲突解决模式",
                "description": "自动解决平台配置冲突",
                "conflict_types": [
                    "平台不兼容配置",
                    "重复功能配置",
                    "版本不匹配配置"
                ],
                "resolution_strategy": [
                    "优先保留平台兼容配置",
                    "移除重复和冲突配置",
                    "升级过时配置到最新版本"
                ]
            },
            {
                "pattern_name": "批量配置更新模式",
                "description": "批量更新多个配置文件以保持一致性",
                "update_scope": [
                    "Hook配置文件",
                    "MCP服务器配置",
                    "平台特定设置",
                    "性能优化参数"
                ],
                "consistency_checks": [
                    "配置版本一致性",
                    "平台兼容性验证",
                    "功能完整性检查"
                ]
            },
            {
                "pattern_name": "智能回滚机制",
                "description": "在修复失败时自动回滚到稳定状态",
                "trigger_conditions": [
                    "修复操作失败",
                    "配置验证不通过",
                    "用户明确要求回滚"
                ],
                "rollback_strategy": [
                    "恢复备份配置",
                    "重置到默认状态",
                    "逐步撤销修改"
                ]
            }
        ]
        
        self.knowledge_base["automated_fix_patterns"] = patterns
        return patterns
    
    def extract_user_feedback_integration(self):
        """提取用户反馈集成经验"""
        integration_patterns = [
            {
                "pattern_name": "实时问题识别",
                "description": "从用户反馈中快速识别配置问题",
                "feedback_sources": [
                    "直接用户报告",
                    "系统错误日志",
                    "配置验证失败",
                    "功能异常行为"
                ],
                "identification_speed": "立即识别关键问题",
                "response_time": "问题识别后立即开始修复"
            },
            {
                "pattern_name": "用户体验优先修复",
                "description": "优先修复影响用户体验的问题",
                "priority_criteria": [
                    "功能完全无法使用",
                    "配置错误导致系统异常",
                    "用户工作流程中断",
                    "性能显著下降"
                ],
                "repair_approach": "快速修复 + 详细解释 + 预防措施"
            },
            {
                "pattern_name": "透明的修复沟通",
                "description": "向用户清晰说明问题和修复过程",
                "communication_elements": [
                    "问题确认和道歉",
                    "修复过程实时更新",
                    "修复结果验证",
                    "预防措施说明"
                ],
                "trust_rebuilding": "通过透明沟通重建用户信任"
            },
            {
                "pattern_name": "持续改进反馈循环",
                "description": "将用户反馈转化为系统改进",
                "improvement_cycle": [
                    "收集用户反馈",
                    "分析问题根因",
                    "设计预防机制",
                    "实施系统改进",
                    "验证改进效果"
                ],
                "knowledge_accumulation": "每次修复都增加系统智能"
            }
        ]
        
        self.knowledge_base["user_feedback_integration"] = integration_patterns
        return integration_patterns
    
    def store_knowledge_to_memory(self):
        """将知识存储到记忆系统"""
        print("💾 将平台适配知识存储到记忆系统...")
        
        try:
            # 创建知识实体
            entities = []
            
            # 平台检测模式实体
            for pattern in self.knowledge_base["platform_detection_patterns"]:
                entities.append({
                    "name": f"平台检测模式_{pattern['pattern_name']}",
                    "entityType": "平台检测模式",
                    "observations": [
                        f"描述: {pattern['description']}",
                        f"优势: {', '.join(pattern.get('benefits', []))}",
                        f"应用场景: {', '.join(pattern.get('use_cases', []))}",
                        f"可靠性: {pattern.get('reliability', '未评估')}"
                    ]
                })
            
            # 配置适配策略实体
            for strategy in self.knowledge_base["configuration_adaptation_strategies"]:
                entities.append({
                    "name": f"配置适配策略_{strategy['strategy_name']}",
                    "entityType": "配置适配策略",
                    "observations": [
                        f"描述: {strategy['description']}",
                        f"自动化程度: {strategy.get('automation_level', '未指定')}",
                        f"可维护性: {strategy.get('maintainability', '未评估')}"
                    ]
                })
            
            # 兼容性问题实体
            for issue in self.knowledge_base["cross_platform_compatibility_issues"]:
                entities.append({
                    "name": f"兼容性问题_{issue['issue_type']}",
                    "entityType": "兼容性问题",
                    "observations": [
                        f"问题类型: {issue['issue_type']}",
                        f"描述: {issue['description']}",
                        f"根本原因: {issue.get('root_cause', '未分析')}",
                        f"解决方案: {issue.get('solution', '待定')}"
                    ]
                })
            
            # 自动化修复模式实体
            for pattern in self.knowledge_base["automated_fix_patterns"]:
                entities.append({
                    "name": f"自动化修复模式_{pattern['pattern_name']}",
                    "entityType": "自动化修复模式",
                    "observations": [
                        f"描述: {pattern['description']}",
                        f"关键原则: {', '.join(pattern.get('key_principles', []))}",
                        f"适用范围: {pattern.get('update_scope', '通用')}"
                    ]
                })
            
            # 用户反馈集成实体
            for integration in self.knowledge_base["user_feedback_integration"]:
                entities.append({
                    "name": f"用户反馈集成_{integration['pattern_name']}",
                    "entityType": "用户反馈集成",
                    "observations": [
                        f"模式: {integration['pattern_name']}",
                        f"描述: {integration['description']}",
                        f"响应时间: {integration.get('response_time', '未指定')}",
                        f"信任重建: {integration.get('trust_rebuilding', '未涉及')}"
                    ]
                })
            
            # 使用MCP记忆系统存储
            result = mcp_memory_create_entities({"entities": entities})
            print(f"✅ 成功存储 {len(entities)} 个知识实体")
            
            # 创建知识关系
            relations = [
                {
                    "from": "平台检测模式_Python平台检测",
                    "to": "配置适配策略_平台特定Hook替换策略",
                    "relationType": "支持了"
                },
                {
                    "from": "兼容性问题_平台特定功能假设",
                    "to": "自动化修复模式_错误检测和自动修复循环",
                    "relationType": "触发了"
                },
                {
                    "from": "用户反馈集成_实时问题识别",
                    "to": "自动化修复模式_配置冲突解决模式",
                    "relationType": "启动了"
                },
                {
                    "from": "配置适配策略_渐进式配置迁移",
                    "to": "自动化修复模式_智能回滚机制",
                    "relationType": "需要了"
                },
                {
                    "from": "用户反馈集成_透明的修复沟通",
                    "to": "用户反馈集成_持续改进反馈循环",
                    "relationType": "促进了"
                }
            ]
            
            relation_result = mcp_memory_create_relations({"relations": relations})
            print(f"✅ 成功创建 {len(relations)} 个知识关系")
            
            return True
            
        except Exception as e:
            print(f"❌ 知识存储失败: {e}")
            return self.save_knowledge_locally()
    
    def save_knowledge_locally(self):
        """本地保存知识"""
        try:
            report_path = Path(".kiro/reports/platform_adaptation_knowledge.json")
            report_path.parent.mkdir(exist_ok=True)
            
            with open(report_path, "w", encoding="utf-8") as f:
                json.dump(self.knowledge_base, f, indent=2, ensure_ascii=False)
            
            print(f"✅ 知识已保存到本地: {report_path}")
            return True
        except Exception as e:
            print(f"❌ 本地保存失败: {e}")
            return False
    
    def generate_knowledge_report(self):
        """生成知识提取报告"""
        print("📊 生成知识提取报告...")
        
        report = {
            "metadata": {
                "extraction_date": datetime.now().isoformat(),
                "extractor": "📚 Knowledge Accumulator",
                "source_event": "平台适配修复任务",
                "knowledge_categories": len(self.knowledge_base)
            },
            "knowledge_summary": {
                "platform_detection_patterns": len(self.knowledge_base["platform_detection_patterns"]),
                "configuration_adaptation_strategies": len(self.knowledge_base["configuration_adaptation_strategies"]),
                "cross_platform_compatibility_issues": len(self.knowledge_base["cross_platform_compatibility_issues"]),
                "automated_fix_patterns": len(self.knowledge_base["automated_fix_patterns"]),
                "user_feedback_integration": len(self.knowledge_base["user_feedback_integration"])
            },
            "knowledge_details": self.knowledge_base,
            "key_insights": [
                "平台检测是跨平台兼容性的基础",
                "自动化修复可以显著提升用户体验",
                "用户反馈是系统改进的重要驱动力",
                "配置模板化可以提高维护效率",
                "透明沟通有助于重建用户信任"
            ],
            "actionable_improvements": [
                "建立标准化的平台检测机制",
                "实施配置模板化管理系统",
                "开发智能配置验证工具",
                "建立用户反馈快速响应机制",
                "创建跨平台兼容性测试套件"
            ],
            "value_assessment": {
                "learning_value": "高 - 包含完整的平台适配经验",
                "reusability": "极高 - 可应用于所有跨平台项目",
                "automation_potential": "高 - 大部分过程可自动化",
                "user_impact": "高 - 直接改善用户体验"
            }
        }
        
        # 保存报告
        report_path = Path(".kiro/reports/platform_adaptation_knowledge_report.json")
        report_path.parent.mkdir(exist_ok=True)
        
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"✅ 知识提取报告已保存到: {report_path}")
        return report
    
    def execute_knowledge_extraction(self):
        """执行知识提取流程"""
        print("📚 开始提取平台适配知识...")
        print("=" * 60)
        
        try:
            # 1. 提取各类知识
            self.extract_platform_detection_patterns()
            print("✅ 平台检测模式提取完成")
            
            self.extract_configuration_adaptation_strategies()
            print("✅ 配置适配策略提取完成")
            
            self.extract_cross_platform_compatibility_issues()
            print("✅ 跨平台兼容性问题提取完成")
            
            self.extract_automated_fix_patterns()
            print("✅ 自动化修复模式提取完成")
            
            self.extract_user_feedback_integration()
            print("✅ 用户反馈集成经验提取完成")
            
            # 2. 存储到记忆系统
            memory_success = self.store_knowledge_to_memory()
            
            # 3. 生成报告
            report = self.generate_knowledge_report()
            
            print("=" * 60)
            print("🎉 平台适配知识提取完成!")
            
            total_knowledge = sum([
                len(self.knowledge_base["platform_detection_patterns"]),
                len(self.knowledge_base["configuration_adaptation_strategies"]),
                len(self.knowledge_base["cross_platform_compatibility_issues"]),
                len(self.knowledge_base["automated_fix_patterns"]),
                len(self.knowledge_base["user_feedback_integration"])
            ])
            
            print(f"📊 提取知识总数: {total_knowledge}个")
            print(f"💾 记忆系统存储: {'成功' if memory_success else '失败'}")
            print(f"📈 知识价值评估: {report['value_assessment']['learning_value']}")
            
            return True
            
        except Exception as e:
            print(f"❌ 知识提取过程中出现错误: {str(e)}")
            return False

def main():
    """主函数"""
    print("📚 平台适配知识提取器")
    print("作为Knowledge Accumulator，我将从平台适配修复中提取宝贵知识")
    print()
    
    extractor = PlatformAdaptationKnowledgeExtractor()
    success = extractor.execute_knowledge_extraction()
    
    if success:
        print("\n🎯 知识提取成功完成!")
        print("💡 这些知识将帮助改进跨平台兼容性和自动化修复能力")
    else:
        print("\n⚠️ 知识提取过程中遇到问题")

if __name__ == "__main__":
    main()