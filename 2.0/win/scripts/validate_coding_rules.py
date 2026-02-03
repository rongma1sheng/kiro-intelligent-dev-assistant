#!/usr/bin/env python
"""
验证MIA编码规则文件的完整性和一致性

检查项:
1. 编码规则是否覆盖所有核心铁律
2. 示例代码是否符合白皮书定义
3. 性能指标是否与白皮书一致
4. 测试要求是否与白皮书一致
5. 编码流程是否完整
"""

import re
from pathlib import Path
from typing import List, Dict, Tuple


class CodingRulesValidator:
    """编码规则验证器"""
    
    def __init__(self, rules_file: str, whitepaper_file: str):
        self.rules_file = Path(rules_file)
        self.whitepaper_file = Path(whitepaper_file)
        self.rules_content = self.rules_file.read_text(encoding='utf-8')
        self.whitepaper_content = self.whitepaper_file.read_text(encoding='utf-8')
        self.issues: List[str] = []
        self.warnings: List[str] = []
        self.successes: List[str] = []
    
    def validate_all(self) -> Tuple[int, int, int]:
        """执行所有验证检查
        
        Returns:
            (成功数, 警告数, 错误数)
        """
        print("=" * 80)
        print("MIA编码规则验证报告")
        print("=" * 80)
        print()
        
        # 1. 检查核心铁律
        self._check_core_rules()
        
        # 2. 检查性能指标
        self._check_performance_metrics()
        
        # 3. 检查测试要求
        self._check_test_requirements()
        
        # 4. 检查编码流程
        self._check_coding_workflow()
        
        # 5. 检查示例代码
        self._check_example_code()
        
        # 6. 检查禁止行为
        self._check_forbidden_behaviors()
        
        # 输出结果
        self._print_results()
        
        return len(self.successes), len(self.warnings), len(self.issues)
    
    def _check_core_rules(self):
        """检查核心铁律是否完整"""
        print("📋 检查1: 核心铁律完整性")
        print("-" * 80)
        
        required_rules = [
            "铁律1: 白皮书至上",
            "铁律2: 禁止简化和占位符",
            "铁律3: 完整的错误处理",
            "铁律4: 完整的类型注解",
            "铁律5: 完整的文档字符串",
            "铁律6: 性能要求必须满足",
            "铁律7: 测试覆盖率要求"
        ]
        
        for rule in required_rules:
            if rule in self.rules_content:
                self.successes.append(f"✅ 找到: {rule}")
            else:
                self.issues.append(f"❌ 缺失: {rule}")
        
        print()
    
    def _check_performance_metrics(self):
        """检查性能指标是否与白皮书一致"""
        print("⚡ 检查2: 性能指标一致性")
        print("-" * 80)
        
        # 白皮书中的性能指标（使用更灵活的匹配模式）
        whitepaper_metrics = {
            "本地推理延迟": [r"< 20ms", r"延迟\s*<\s*20\s*ms", r"20ms", r"20\s*ms"],
            "热备切换延迟": [r"< 200ms", r"超时\s*>\s*200\s*ms", r"200ms", r"切换.*200"],
            "SPSC延迟": [r"< 100[μu]s", r"100[μu]s", r"SPSC.*延迟"]
        }
        
        for metric_name, patterns in whitepaper_metrics.items():
            # 在白皮书中查找（任意一个模式匹配即可）
            found_in_whitepaper = any(re.search(pattern, self.whitepaper_content, re.IGNORECASE) 
                                     for pattern in patterns)
            # 在编码规则中查找
            found_in_rules = any(re.search(pattern, self.rules_content, re.IGNORECASE) 
                                for pattern in patterns)
            
            if found_in_whitepaper and found_in_rules:
                self.successes.append(f"✅ 性能指标一致: {metric_name}")
            elif found_in_rules and not found_in_whitepaper:
                self.warnings.append(f"⚠️  性能指标仅在编码规则中: {metric_name}")
            elif found_in_whitepaper and not found_in_rules:
                self.issues.append(f"❌ 性能指标缺失: {metric_name}")
            else:
                self.warnings.append(f"⚠️  性能指标未找到: {metric_name}")
        
        print()
    
    def _check_test_requirements(self):
        """检查测试要求是否与白皮书一致"""
        print("🧪 检查3: 测试要求一致性")
        print("-" * 80)
        
        # 测试覆盖率要求
        if "≥ 85%" in self.rules_content or ">= 85%" in self.rules_content:
            self.successes.append("✅ 测试覆盖率要求: ≥ 85%")
        else:
            self.issues.append("❌ 测试覆盖率要求缺失")
        
        # 测试类型
        test_types = ["单元测试", "集成测试", "E2E测试", "性能测试"]
        for test_type in test_types:
            if test_type in self.rules_content:
                self.successes.append(f"✅ 测试类型: {test_type}")
            else:
                self.warnings.append(f"⚠️  测试类型未明确提及: {test_type}")
        
        print()
    
    def _check_coding_workflow(self):
        """检查编码流程是否完整"""
        print("🔄 检查4: 编码流程完整性")
        print("-" * 80)
        
        required_steps = [
            "步骤1: 阅读白皮书",
            "步骤2: 检查实现清单",
            "步骤3: 编写测试用例",
            "步骤4: 实现功能",
            "步骤5: 运行测试",
            "步骤6: 代码质量检查",
            "步骤7: 更新检查清单"
        ]
        
        for step in required_steps:
            if step in self.rules_content:
                self.successes.append(f"✅ 编码流程: {step}")
            else:
                self.issues.append(f"❌ 编码流程缺失: {step}")
        
        print()
    
    def _check_example_code(self):
        """检查示例代码是否符合白皮书定义"""
        print("💻 检查5: 示例代码验证")
        print("-" * 80)
        
        # 检查示例代码中的类名是否在白皮书中定义
        whitepaper_classes = [
            "GeneticMiner",
            "Soldier",
            "Commander",
            "Devil",
            "Scholar",
            "Arena",
            "MetaEvolution"
        ]
        
        # Individual 是合理的内部数据结构，不算幻觉
        internal_data_structures = ["Individual"]
        
        for class_name in whitepaper_classes:
            # 在编码规则的示例代码中查找
            if f"class {class_name}" in self.rules_content:
                # 验证是否在白皮书中定义
                if class_name in self.whitepaper_content:
                    self.successes.append(f"✅ 示例类名正确: {class_name}")
                else:
                    self.issues.append(f"❌ 示例类名幻觉: {class_name} (白皮书中未定义)")
        
        # 检查内部数据结构（使用@dataclass的不算幻觉）
        for class_name in internal_data_structures:
            if f"class {class_name}" in self.rules_content:
                # 检查是否使用了@dataclass
                if "@dataclass" in self.rules_content:
                    self.successes.append(f"✅ 内部数据结构合理: {class_name} (使用@dataclass)")
                else:
                    self.warnings.append(f"⚠️  内部数据结构: {class_name} (建议使用@dataclass)")
        
        # 检查是否有幻觉类名（排除错误示例中的）
        hallucination_patterns = [
            (r"class\s+Advanced\w+", "Advanced"),
            (r"class\s+Super\w+", "Super"),
            (r"class\s+Ultra\w+", "Ultra"),
            (r"class\s+Enhanced\w+", "Enhanced")
        ]
        
        for pattern, prefix in hallucination_patterns:
            matches = re.findall(pattern, self.rules_content)
            if matches:
                for match in matches:
                    # 检查是否在"违规示例"或"错误示例"部分
                    # 查找match前后的文本
                    match_pos = self.rules_content.find(match)
                    context_before = self.rules_content[max(0, match_pos-200):match_pos]
                    
                    if "违规示例" in context_before or "错误" in context_before or "❌" in context_before:
                        self.successes.append(f"✅ 错误示例正确使用: {match}")
                    else:
                        self.warnings.append(f"⚠️  可能的幻觉类名: {match}")
        
        print()
    
    def _check_forbidden_behaviors(self):
        """检查禁止行为是否明确列出"""
        print("🚫 检查6: 禁止行为清单")
        print("-" * 80)
        
        forbidden_items = [
            "pass",
            "TODO",
            "NotImplemented",
            "...",
            "# 实现细节省略",
            "# 待实现"
        ]
        
        for item in forbidden_items:
            if item in self.rules_content:
                self.successes.append(f"✅ 禁止项已列出: {item}")
            else:
                self.warnings.append(f"⚠️  禁止项未明确: {item}")
        
        print()
    
    def _print_results(self):
        """打印验证结果"""
        print("=" * 80)
        print("验证结果汇总")
        print("=" * 80)
        print()
        
        # 成功项
        if self.successes:
            print(f"✅ 成功 ({len(self.successes)}项):")
            for success in self.successes:
                print(f"  {success}")
            print()
        
        # 警告项
        if self.warnings:
            print(f"⚠️  警告 ({len(self.warnings)}项):")
            for warning in self.warnings:
                print(f"  {warning}")
            print()
        
        # 错误项
        if self.issues:
            print(f"❌ 错误 ({len(self.issues)}项):")
            for issue in self.issues:
                print(f"  {issue}")
            print()
        
        # 总体评分
        total = len(self.successes) + len(self.warnings) + len(self.issues)
        score = (len(self.successes) * 1.0 + len(self.warnings) * 0.5) / total * 100 if total > 0 else 0
        
        print("=" * 80)
        print(f"总体评分: {score:.1f}/100")
        print(f"  成功: {len(self.successes)}项")
        print(f"  警告: {len(self.warnings)}项")
        print(f"  错误: {len(self.issues)}项")
        print("=" * 80)
        
        if score >= 90:
            print("🎉 优秀！编码规则文件质量很高！")
        elif score >= 75:
            print("👍 良好！编码规则文件基本符合要求。")
        elif score >= 60:
            print("⚠️  及格！编码规则文件需要改进。")
        else:
            print("❌ 不及格！编码规则文件存在严重问题。")


def main():
    """主函数"""
    rules_file = ".kiro/steering/mia_coding_rules.md"
    whitepaper_file = "00_核心文档/mia.md"
    
    validator = CodingRulesValidator(rules_file, whitepaper_file)
    successes, warnings, issues = validator.validate_all()
    
    # 返回退出码
    if issues > 0:
        exit(1)
    elif warnings > 0:
        exit(0)
    else:
        exit(0)


if __name__ == "__main__":
    main()
