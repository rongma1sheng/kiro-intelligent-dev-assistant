#!/usr/bin/env python3
"""
紧急恢复知识提取器

作为📚 Knowledge Accumulator，我负责从紧急恢复过程中
提取有价值的知识，包括错误处理、恢复策略和预防措施。
"""

import json
from datetime import datetime
from pathlib import Path

class EmergencyRecoveryKnowledgeExtractor:
    """紧急恢复知识提取器"""
    
    def __init__(self):
        self.knowledge_base = {
            "critical_errors": [],
            "recovery_patterns": [],
            "prevention_strategies": [],
            "technical_solutions": [],
            "user_experience_lessons": []
        }
        
    def extract_critical_errors(self):
        """提取关键错误模式"""
        errors = [
            {
                "error_type": "配置文件误删",
                "description": "重复文件清理时误删了用户正在使用的Kiro配置文件",
                "root_cause": "清理脚本未正确识别活跃配置文件",
                "impact": "用户本地Kiro环境无法正常工作",
                "severity": "高",
                "affected_components": [".kiro/settings/", ".kiro/hooks/"],
                "detection_method": "用户反馈",
                "occurrence_context": "批量重复文件清理过程中"
            },
            {
                "error_type": "权限访问错误",
                "description": "Windows系统下某些文件删除时出现权限拒绝",
                "root_cause": "文件被其他进程占用或权限不足",
                "impact": "部分重复文件无法删除",
                "severity": "中",
                "affected_files": ["steering文件", "specs文件", "backup文件"],
                "workaround": "跳过权限错误文件，继续处理其他文件"
            },
            {
                "error_type": "文件优先级判断错误",
                "description": "清理脚本错误地选择了要保留的文件",
                "root_cause": "优先级算法未充分考虑文件的实际使用状态",
                "impact": "保留了备份文件而删除了活跃文件",
                "severity": "高",
                "lesson": "需要更智能的文件状态检测机制"
            }
        ]
        
        self.knowledge_base["critical_errors"] = errors
        return errors
    
    def extract_recovery_patterns(self):
        """提取恢复模式"""
        patterns = [
            {
                "pattern_name": "紧急配置恢复模式",
                "description": "当关键配置文件丢失时的快速恢复策略",
                "steps": [
                    "立即停止可能造成进一步损害的操作",
                    "查找最新的配置备份",
                    "从备份中恢复关键配置文件",
                    "重新创建缺失的基础配置",
                    "验证恢复结果的完整性",
                    "生成恢复报告和后续建议"
                ],
                "key_principles": [
                    "速度优先 - 快速恢复用户环境",
                    "最小化影响 - 只恢复必要的文件",
                    "验证完整性 - 确保恢复的配置可用",
                    "文档记录 - 记录恢复过程供学习"
                ],
                "success_criteria": "用户环境恢复正常工作状态"
            },
            {
                "pattern_name": "备份查找和验证模式",
                "description": "在紧急情况下快速定位和验证可用备份",
                "implementation": "按时间戳排序备份目录，选择最新的完整备份",
                "validation_steps": [
                    "检查备份目录的存在性",
                    "验证备份文件的完整性",
                    "确认备份内容的可用性",
                    "测试关键配置的有效性"
                ]
            },
            {
                "pattern_name": "渐进式恢复模式",
                "description": "分阶段恢复系统功能，优先恢复核心功能",
                "phases": [
                    "阶段1: 恢复基础MCP配置",
                    "阶段2: 恢复Hook自动化功能",
                    "阶段3: 恢复性能优化配置",
                    "阶段4: 恢复高级功能配置"
                ],
                "benefits": ["降低恢复风险", "快速恢复核心功能", "便于问题定位"]
            }
        ]
        
        self.knowledge_base["recovery_patterns"] = patterns
        return patterns
    
    def extract_prevention_strategies(self):
        """提取预防策略"""
        strategies = [
            {
                "strategy_name": "智能文件保护机制",
                "description": "在执行批量操作前识别和保护关键文件",
                "implementation": [
                    "建立活跃配置文件检测机制",
                    "创建文件重要性评估算法",
                    "实施多层确认机制",
                    "提供操作预览和回滚功能"
                ],
                "technical_approach": "文件访问时间分析 + 进程占用检测 + 用户确认",
                "expected_outcome": "避免误删关键配置文件"
            },
            {
                "strategy_name": "增强备份策略",
                "description": "建立更完善的自动备份和恢复机制",
                "components": [
                    "实时配置文件监控",
                    "增量备份机制",
                    "多版本备份保留",
                    "快速恢复工具"
                ],
                "backup_triggers": [
                    "配置文件修改时",
                    "执行危险操作前",
                    "定期自动备份",
                    "用户手动触发"
                ]
            },
            {
                "strategy_name": "用户环境隔离",
                "description": "将用户活跃配置与项目文件分离管理",
                "approach": "区分.kiro/active/和.kiro/templates/目录",
                "benefits": [
                    "保护用户个性化配置",
                    "避免批量操作影响",
                    "简化恢复流程",
                    "提高系统稳定性"
                ]
            },
            {
                "strategy_name": "操作前影响评估",
                "description": "在执行批量操作前评估潜在影响",
                "evaluation_criteria": [
                    "文件使用频率分析",
                    "系统依赖关系检查",
                    "用户配置识别",
                    "风险等级评估"
                ],
                "decision_matrix": "高风险操作需要用户明确授权"
            }
        ]
        
        self.knowledge_base["prevention_strategies"] = strategies
        return strategies
    
    def extract_technical_solutions(self):
        """提取技术解决方案"""
        solutions = [
            {
                "problem": "Windows文件权限访问错误",
                "solution": "优雅的权限错误处理",
                "implementation": "使用try-catch捕获权限错误，记录但不中断流程",
                "code_pattern": """
try:
    file_path.unlink()
    deleted_count += 1
except PermissionError as e:
    print(f"❌ 删除失败 {file_path}: 权限不足")
    continue  # 继续处理其他文件
""",
                "benefits": ["提高脚本健壮性", "避免单点失败", "提供清晰的错误信息"]
            },
            {
                "problem": "配置文件快速重建",
                "solution": "模板化配置生成",
                "implementation": "预定义配置模板，根据平台和环境动态生成",
                "key_features": [
                    "平台特定优化",
                    "环境变量自动配置",
                    "版本兼容性处理",
                    "用户偏好保留"
                ]
            },
            {
                "problem": "备份文件快速定位",
                "solution": "时间戳排序和智能匹配",
                "algorithm": "按修改时间排序备份目录，选择最新的完整备份",
                "validation": "检查备份完整性和文件可用性"
            },
            {
                "problem": "批量操作进度反馈",
                "solution": "分阶段进度显示",
                "implementation": "每处理一定数量文件显示进度，提供用户反馈",
                "user_experience": "让用户了解操作进展，避免焦虑"
            }
        ]
        
        self.knowledge_base["technical_solutions"] = solutions
        return solutions
    
    def extract_user_experience_lessons(self):
        """提取用户体验教训"""
        lessons = [
            {
                "lesson": "操作透明度的重要性",
                "description": "用户需要清楚了解系统正在执行什么操作",
                "problem": "批量删除文件时用户不知道会影响其配置",
                "solution": "提供详细的操作预览和影响评估",
                "implementation": [
                    "显示将要删除的文件列表",
                    "标识关键配置文件",
                    "提供操作影响说明",
                    "允许用户选择性确认"
                ]
            },
            {
                "lesson": "错误恢复的及时性",
                "description": "当发生错误时，需要立即提供恢复方案",
                "response_time": "检测到问题后立即开始恢复流程",
                "communication": "向用户说明问题和恢复进展",
                "reassurance": "让用户知道问题可以解决"
            },
            {
                "lesson": "用户信任的重建",
                "description": "错误发生后需要重建用户对系统的信任",
                "strategies": [
                    "承认错误并道歉",
                    "快速有效地解决问题",
                    "解释错误原因和预防措施",
                    "提供额外的保障机制"
                ]
            },
            {
                "lesson": "操作可逆性的价值",
                "description": "所有批量操作都应该提供撤销机制",
                "requirements": [
                    "操作前自动备份",
                    "详细的操作日志",
                    "一键恢复功能",
                    "分步骤回滚能力"
                ]
            }
        ]
        
        self.knowledge_base["user_experience_lessons"] = lessons
        return lessons
    
    def store_knowledge_to_memory(self):
        """将知识存储到记忆系统"""
        print("💾 将紧急恢复知识存储到记忆系统...")
        
        try:
            # 创建知识实体
            entities = []
            
            # 关键错误实体
            for error in self.knowledge_base["critical_errors"]:
                entities.append({
                    "name": f"关键错误_{error['error_type']}",
                    "entityType": "错误模式",
                    "observations": [
                        f"描述: {error['description']}",
                        f"根本原因: {error['root_cause']}",
                        f"影响: {error['impact']}",
                        f"严重性: {error['severity']}"
                    ]
                })
            
            # 恢复模式实体
            for pattern in self.knowledge_base["recovery_patterns"]:
                entities.append({
                    "name": f"恢复模式_{pattern['pattern_name']}",
                    "entityType": "恢复模式",
                    "observations": [
                        f"描述: {pattern['description']}",
                        f"步骤: {', '.join(pattern.get('steps', []))}",
                        f"关键原则: {', '.join(pattern.get('key_principles', []))}"
                    ]
                })
            
            # 预防策略实体
            for strategy in self.knowledge_base["prevention_strategies"]:
                entities.append({
                    "name": f"预防策略_{strategy['strategy_name']}",
                    "entityType": "预防策略",
                    "observations": [
                        f"描述: {strategy['description']}",
                        f"实施方法: {', '.join(strategy.get('implementation', []))}",
                        f"预期结果: {strategy.get('expected_outcome', '')}"
                    ]
                })
            
            # 技术解决方案实体
            for solution in self.knowledge_base["technical_solutions"]:
                entities.append({
                    "name": f"技术解决方案_{solution['problem']}",
                    "entityType": "技术解决方案",
                    "observations": [
                        f"问题: {solution['problem']}",
                        f"解决方案: {solution['solution']}",
                        f"实现: {solution['implementation']}",
                        f"优势: {', '.join(solution.get('benefits', []))}"
                    ]
                })
            
            # 用户体验教训实体
            for lesson in self.knowledge_base["user_experience_lessons"]:
                entities.append({
                    "name": f"用户体验教训_{lesson['lesson']}",
                    "entityType": "用户体验教训",
                    "observations": [
                        f"教训: {lesson['lesson']}",
                        f"描述: {lesson['description']}",
                        f"问题: {lesson.get('problem', '')}",
                        f"解决方案: {lesson.get('solution', '')}"
                    ]
                })
            
            # 使用MCP记忆系统存储
            result = mcp_memory_create_entities({"entities": entities})
            print(f"✅ 成功存储 {len(entities)} 个知识实体")
            
            # 创建知识关系
            relations = [
                {
                    "from": "关键错误_配置文件误删",
                    "to": "恢复模式_紧急配置恢复模式",
                    "relationType": "触发了"
                },
                {
                    "from": "恢复模式_紧急配置恢复模式",
                    "to": "预防策略_智能文件保护机制",
                    "relationType": "启发了"
                },
                {
                    "from": "技术解决方案_Windows文件权限访问错误",
                    "to": "关键错误_权限访问错误",
                    "relationType": "解决了"
                },
                {
                    "from": "用户体验教训_操作透明度的重要性",
                    "to": "预防策略_操作前影响评估",
                    "relationType": "指导了"
                },
                {
                    "from": "预防策略_增强备份策略",
                    "to": "恢复模式_备份查找和验证模式",
                    "relationType": "支持了"
                }
            ]
            
            relation_result = mcp_memory_create_relations({"relations": relations})
            print(f"✅ 成功创建 {len(relations)} 个知识关系")
            
            return True
            
        except Exception as e:
            print(f"❌ 知识存储失败: {e}")
            # 即使MCP存储失败，也要保存到本地文件
            return self.save_knowledge_locally()
    
    def save_knowledge_locally(self):
        """本地保存知识"""
        try:
            report_path = Path(".kiro/reports/emergency_recovery_knowledge.json")
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
                "source_event": "紧急配置恢复事件",
                "knowledge_categories": len(self.knowledge_base)
            },
            "knowledge_summary": {
                "critical_errors": len(self.knowledge_base["critical_errors"]),
                "recovery_patterns": len(self.knowledge_base["recovery_patterns"]),
                "prevention_strategies": len(self.knowledge_base["prevention_strategies"]),
                "technical_solutions": len(self.knowledge_base["technical_solutions"]),
                "user_experience_lessons": len(self.knowledge_base["user_experience_lessons"])
            },
            "knowledge_details": self.knowledge_base,
            "key_insights": [
                "配置文件保护机制的重要性",
                "紧急恢复流程的标准化价值",
                "用户体验在错误处理中的关键作用",
                "预防性措施比事后修复更有效",
                "操作透明度对用户信任的影响"
            ],
            "actionable_improvements": [
                "实施智能文件保护机制",
                "建立标准化紧急恢复流程",
                "增强操作前影响评估",
                "改进用户沟通和反馈机制",
                "建立更完善的备份策略"
            ],
            "value_assessment": {
                "learning_value": "极高 - 包含关键错误处理经验",
                "reusability": "高 - 可应用于类似紧急情况",
                "prevention_value": "极高 - 可避免类似问题再次发生",
                "user_impact": "高 - 直接影响用户体验和信任"
            }
        }
        
        # 保存报告
        report_path = Path(".kiro/reports/emergency_recovery_knowledge_report.json")
        report_path.parent.mkdir(exist_ok=True)
        
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"✅ 知识提取报告已保存到: {report_path}")
        return report
    
    def execute_knowledge_extraction(self):
        """执行知识提取流程"""
        print("📚 开始提取紧急恢复知识...")
        print("=" * 60)
        
        try:
            # 1. 提取各类知识
            self.extract_critical_errors()
            print("✅ 关键错误模式提取完成")
            
            self.extract_recovery_patterns()
            print("✅ 恢复模式提取完成")
            
            self.extract_prevention_strategies()
            print("✅ 预防策略提取完成")
            
            self.extract_technical_solutions()
            print("✅ 技术解决方案提取完成")
            
            self.extract_user_experience_lessons()
            print("✅ 用户体验教训提取完成")
            
            # 2. 存储到记忆系统
            memory_success = self.store_knowledge_to_memory()
            
            # 3. 生成报告
            report = self.generate_knowledge_report()
            
            print("=" * 60)
            print("🎉 紧急恢复知识提取完成!")
            
            total_knowledge = sum([
                len(self.knowledge_base["critical_errors"]),
                len(self.knowledge_base["recovery_patterns"]),
                len(self.knowledge_base["prevention_strategies"]),
                len(self.knowledge_base["technical_solutions"]),
                len(self.knowledge_base["user_experience_lessons"])
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
    print("📚 紧急恢复知识提取器")
    print("作为Knowledge Accumulator，我将从紧急恢复事件中提取宝贵知识")
    print()
    
    extractor = EmergencyRecoveryKnowledgeExtractor()
    success = extractor.execute_knowledge_extraction()
    
    if success:
        print("\n🎯 知识提取成功完成!")
        print("💡 这些知识将帮助预防类似问题并改进应急响应")
    else:
        print("\n⚠️ 知识提取过程中遇到问题")

if __name__ == "__main__":
    main()