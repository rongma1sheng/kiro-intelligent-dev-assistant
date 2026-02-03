#!/usr/bin/env python3
"""
通用配置验证脚本

功能：
1. 验证配置文件完整性
2. 检查Hook配置正确性
3. 验证角色权限矩阵
4. 检查质量标准设置
"""

import os
import json
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import argparse
from dataclasses import dataclass
from enum import Enum


class ValidationResult(Enum):
    """验证结果枚举"""
    PASS = "PASS"
    WARNING = "WARNING"
    ERROR = "ERROR"


@dataclass
class ValidationIssue:
    """验证问题"""
    level: ValidationResult
    category: str
    message: str
    file_path: Optional[str] = None
    suggestion: Optional[str] = None


class ConfigValidator:
    """配置验证器"""
    
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.kiro_dir = self.project_root / ".kiro"
        self.issues: List[ValidationIssue] = []
        
    def validate_all(self) -> List[ValidationIssue]:
        """执行完整的配置验证"""
        print("🔍 开始配置验证...")
        
        # 1. 验证目录结构
        self._validate_directory_structure()
        
        # 2. 验证配置文件
        self._validate_config_files()
        
        # 3. 验证Hook配置
        self._validate_hooks()
        
        # 4. 验证脚本文件
        self._validate_scripts()
        
        # 5. 验证质量标准
        self._validate_quality_standards()
        
        return self.issues
    
    def _validate_directory_structure(self):
        """验证目录结构"""
        required_dirs = [
            ".kiro",
            ".kiro/steering",
            ".kiro/hooks",
            ".kiro/scripts",
            "tests",
            "tests/unit"
        ]
        
        for dir_path in required_dirs:
            full_path = self.project_root / dir_path
            if not full_path.exists():
                self.issues.append(ValidationIssue(
                    level=ValidationResult.ERROR,
                    category="directory_structure",
                    message=f"缺少必需目录: {dir_path}",
                    suggestion=f"创建目录: mkdir -p {dir_path}"
                ))
            elif not full_path.is_dir():
                self.issues.append(ValidationIssue(
                    level=ValidationResult.ERROR,
                    category="directory_structure",
                    message=f"路径不是目录: {dir_path}",
                    suggestion=f"删除文件并创建目录: rm {dir_path} && mkdir -p {dir_path}"
                ))
    
    def _validate_config_files(self):
        """验证配置文件"""
        required_files = {
            ".kiro/steering/task-hierarchy-management.md": "任务层次化管理配置",
            ".kiro/steering/silicon-valley-team-config.md": "硅谷团队配置",
            ".kiro/README.md": "项目说明文档",
            ".kiro/USAGE_GUIDE.md": "使用指南"
        }
        
        for file_path, description in required_files.items():
            full_path = self.project_root / file_path
            if not full_path.exists():
                self.issues.append(ValidationIssue(
                    level=ValidationResult.ERROR,
                    category="config_files",
                    message=f"缺少{description}: {file_path}",
                    file_path=file_path,
                    suggestion="从模板复制相应文件"
                ))
            elif full_path.stat().st_size == 0:
                self.issues.append(ValidationIssue(
                    level=ValidationResult.WARNING,
                    category="config_files",
                    message=f"{description}文件为空: {file_path}",
                    file_path=file_path,
                    suggestion="检查文件内容是否正确"
                ))
        
        # 验证项目配置文件
        project_config_path = self.kiro_dir / "project_config.json"
        if project_config_path.exists():
            try:
                with open(project_config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    
                # 验证必需字段
                required_fields = ["project_type", "language", "team_size", "quality_thresholds"]
                for field in required_fields:
                    if field not in config:
                        self.issues.append(ValidationIssue(
                            level=ValidationResult.ERROR,
                            category="project_config",
                            message=f"项目配置缺少必需字段: {field}",
                            file_path="project_config.json",
                            suggestion=f"添加字段: {field}"
                        ))
                        
            except json.JSONDecodeError as e:
                self.issues.append(ValidationIssue(
                    level=ValidationResult.ERROR,
                    category="project_config",
                    message=f"项目配置JSON格式错误: {e}",
                    file_path="project_config.json",
                    suggestion="修复JSON格式错误"
                ))
    
    def _validate_hooks(self):
        """验证Hook配置"""
        hook_files = list((self.kiro_dir / "hooks").glob("*.kiro.hook"))
        
        if not hook_files:
            self.issues.append(ValidationIssue(
                level=ValidationResult.WARNING,
                category="hooks",
                message="未找到任何Hook配置文件",
                suggestion="从模板复制Hook配置文件"
            ))
            return
        
        for hook_file in hook_files:
            try:
                with open(hook_file, 'r', encoding='utf-8') as f:
                    hook_config = json.load(f)
                
                # 验证Hook配置结构
                required_fields = ["name", "version", "when", "then"]
                for field in required_fields:
                    if field not in hook_config:
                        self.issues.append(ValidationIssue(
                            level=ValidationResult.ERROR,
                            category="hooks",
                            message=f"Hook配置缺少必需字段: {field}",
                            file_path=str(hook_file.relative_to(self.project_root)),
                            suggestion=f"添加字段: {field}"
                        ))
                
                # 验证when配置
                if "when" in hook_config:
                    when_config = hook_config["when"]
                    if "type" not in when_config:
                        self.issues.append(ValidationIssue(
                            level=ValidationResult.ERROR,
                            category="hooks",
                            message="Hook when配置缺少type字段",
                            file_path=str(hook_file.relative_to(self.project_root)),
                            suggestion="添加when.type字段"
                        ))
                
                # 验证then配置
                if "then" in hook_config:
                    then_config = hook_config["then"]
                    if "type" not in then_config:
                        self.issues.append(ValidationIssue(
                            level=ValidationResult.ERROR,
                            category="hooks",
                            message="Hook then配置缺少type字段",
                            file_path=str(hook_file.relative_to(self.project_root)),
                            suggestion="添加then.type字段"
                        ))
                        
            except json.JSONDecodeError as e:
                self.issues.append(ValidationIssue(
                    level=ValidationResult.ERROR,
                    category="hooks",
                    message=f"Hook配置JSON格式错误: {e}",
                    file_path=str(hook_file.relative_to(self.project_root)),
                    suggestion="修复JSON格式错误"
                ))
    
    def _validate_scripts(self):
        """验证脚本文件"""
        required_scripts = [
            ".kiro/scripts/universal_quality_gate.py",
            ".kiro/scripts/project_initializer.py"
        ]
        
        for script_path in required_scripts:
            full_path = self.project_root / script_path
            if not full_path.exists():
                self.issues.append(ValidationIssue(
                    level=ValidationResult.ERROR,
                    category="scripts",
                    message=f"缺少必需脚本: {script_path}",
                    file_path=script_path,
                    suggestion="从模板复制脚本文件"
                ))
            elif not os.access(full_path, os.X_OK):
                self.issues.append(ValidationIssue(
                    level=ValidationResult.WARNING,
                    category="scripts",
                    message=f"脚本文件不可执行: {script_path}",
                    file_path=script_path,
                    suggestion=f"设置执行权限: chmod +x {script_path}"
                ))
    
    def _validate_quality_standards(self):
        """验证质量标准"""
        project_config_path = self.kiro_dir / "project_config.json"
        if not project_config_path.exists():
            return
        
        try:
            with open(project_config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            quality_thresholds = config.get("quality_thresholds", {})
            
            # 验证测试覆盖率标准（铁律）
            test_coverage = quality_thresholds.get("test_coverage", 0)
            if test_coverage < 100:
                self.issues.append(ValidationIssue(
                    level=ValidationResult.ERROR,
                    category="quality_standards",
                    message=f"测试覆盖率标准违反铁律: {test_coverage}% < 100%",
                    file_path="project_config.json",
                    suggestion="设置test_coverage为100"
                ))
            
            # 验证代码复杂度标准（铁律）
            code_complexity = quality_thresholds.get("code_complexity", 999)
            if code_complexity > 10:
                self.issues.append(ValidationIssue(
                    level=ValidationResult.ERROR,
                    category="quality_standards",
                    message=f"代码复杂度标准违反铁律: {code_complexity} > 10",
                    file_path="project_config.json",
                    suggestion="设置code_complexity为10或更低"
                ))
            
            # 验证其他质量标准
            security_score = quality_thresholds.get("security_score", 0)
            if security_score < 90:
                self.issues.append(ValidationIssue(
                    level=ValidationResult.WARNING,
                    category="quality_standards",
                    message=f"安全评分标准较低: {security_score} < 90",
                    file_path="project_config.json",
                    suggestion="建议设置security_score为90或更高"
                ))
                
        except (json.JSONDecodeError, KeyError):
            pass  # 已在其他地方处理
    
    def generate_report(self, output_file: Optional[str] = None) -> str:
        """生成验证报告"""
        # 统计问题
        error_count = len([i for i in self.issues if i.level == ValidationResult.ERROR])
        warning_count = len([i for i in self.issues if i.level == ValidationResult.WARNING])
        
        # 确定总体状态
        if error_count > 0:
            overall_status = "❌ 验证失败"
        elif warning_count > 0:
            overall_status = "⚠️ 有警告"
        else:
            overall_status = "✅ 验证通过"
        
        report_content = f"""# 配置验证报告

## 📊 总体状态: {overall_status}

### 📈 问题统计
- **错误**: {error_count}个
- **警告**: {warning_count}个
- **总计**: {len(self.issues)}个

### 📋 详细问题列表
"""
        
        if not self.issues:
            report_content += "✅ 未发现任何问题\n"
        else:
            # 按类别分组显示问题
            categories = {}
            for issue in self.issues:
                if issue.category not in categories:
                    categories[issue.category] = []
                categories[issue.category].append(issue)
            
            for category, issues in categories.items():
                report_content += f"\n#### {category.replace('_', ' ').title()}\n"
                for issue in issues:
                    icon = "❌" if issue.level == ValidationResult.ERROR else "⚠️"
                    report_content += f"- {icon} {issue.message}\n"
                    if issue.file_path:
                        report_content += f"  📁 文件: {issue.file_path}\n"
                    if issue.suggestion:
                        report_content += f"  💡 建议: {issue.suggestion}\n"
        
        report_content += f"""
### 🔧 修复建议

#### 高优先级（错误）
"""
        
        error_issues = [i for i in self.issues if i.level == ValidationResult.ERROR]
        if error_issues:
            for i, issue in enumerate(error_issues, 1):
                report_content += f"{i}. {issue.message}\n"
                if issue.suggestion:
                    report_content += f"   解决方案: {issue.suggestion}\n"
        else:
            report_content += "✅ 无高优先级问题\n"
        
        report_content += "\n#### 中优先级（警告）\n"
        warning_issues = [i for i in self.issues if i.level == ValidationResult.WARNING]
        if warning_issues:
            for i, issue in enumerate(warning_issues, 1):
                report_content += f"{i}. {issue.message}\n"
                if issue.suggestion:
                    report_content += f"   解决方案: {issue.suggestion}\n"
        else:
            report_content += "✅ 无中优先级问题\n"
        
        report_content += f"""
---
**验证时间**: {__import__('datetime').datetime.now().isoformat()}
**验证工具**: Config Validator v1.0
**项目路径**: {self.project_root.absolute()}
"""
        
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(report_content)
            print(f"📄 验证报告已保存到: {output_file}")
        
        return report_content


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="通用配置验证工具")
    parser.add_argument("--project-root", default=".", help="项目根目录")
    parser.add_argument("--output", help="报告输出文件")
    parser.add_argument("--fail-on-error", action="store_true", help="有错误时返回非零退出码")
    
    args = parser.parse_args()
    
    # 创建验证器
    validator = ConfigValidator(args.project_root)
    
    # 执行验证
    issues = validator.validate_all()
    
    # 生成报告
    report_content = validator.generate_report(args.output)
    print("\n" + "="*50)
    print(report_content)
    
    # 统计错误数量
    error_count = len([i for i in issues if i.level == ValidationResult.ERROR])
    warning_count = len([i for i in issues if i.level == ValidationResult.WARNING])
    
    # 输出结果
    if error_count > 0:
        print(f"\n❌ 配置验证失败: {error_count}个错误, {warning_count}个警告")
        if args.fail_on_error:
            exit(1)
    elif warning_count > 0:
        print(f"\n⚠️ 配置验证有警告: {warning_count}个警告")
    else:
        print("\n✅ 配置验证通过")
    
    exit(0)


if __name__ == "__main__":
    main()