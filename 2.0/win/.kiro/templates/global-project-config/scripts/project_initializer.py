#!/usr/bin/env python333
"""
通用项目初始化脚本

功能：
1. 从模板复制配置文件到新项目
2. 根据项目特点自定义配置
3. 验证配置完整性
4. 初始化项目结构
"""

import os
import shutil
import json
import yaml
from pathlib import Path
from typing import Dict, List, Optional
import argparse


class ProjectInitializer:
    """通用项目初始化器"""
    
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.template_root = Path(__file__).parent.parent
        self.kiro_dir = self.project_root / ".kiro"
        
    def initialize_project(self, 
                          project_type: str = "medium",
                          language: str = "python",
                          team_size: int = 6) -> bool:
        """初始化项目配置
        
        Args:
            project_type: 项目类型 (small/medium/large)
            language: 主要编程语言
            team_size: 团队规模
            
        Returns:
            bool: 初始化是否成功
        """
        try:
            print(f"🚀 开始初始化项目: {self.project_root}")
            
            # 1. 创建.kiro目录结构
            self._create_directory_structure()
            
            # 2. 复制通用配置模板
            self._copy_templates()
            
            # 3. 根据项目特点自定义配置
            self._customize_config(project_type, language, team_size)
            
            # 4. 验证配置完整性
            if self._validate_config():
                print("✅ 项目初始化成功！")
                self._print_next_steps()
                return True
            else:
                print("❌ 配置验证失败，请检查配置文件")
                return False
                
        except Exception as e:
            print(f"❌ 项目初始化失败: {e}")
            return False
    
    def _create_directory_structure(self):
        """创建项目目录结构"""
        directories = [
            ".kiro/steering",
            ".kiro/hooks", 
            ".kiro/scripts",
            ".kiro/specs",
            "tests/unit",
            "tests/integration",
            "docs",
            "reports"
        ]
        
        for dir_path in directories:
            (self.project_root / dir_path).mkdir(parents=True, exist_ok=True)
            
        print("📁 目录结构创建完成")
    
    def _copy_templates(self):
        """复制配置模板"""
        template_mappings = {
            "steering/task-hierarchy-management-template.md": "steering/task-hierarchy-management.md",
            "steering/silicon-valley-team-config-template.md": "steering/silicon-valley-team-config.md",
            "hooks/task-lifecycle-management-template.kiro.hook": "hooks/task-lifecycle-management.kiro.hook",
            "hooks/quality-gate-enforcement-template.kiro.hook": "hooks/quality-gate-enforcement.kiro.hook",
            "hooks/test-coverage-monitor-template.kiro.hook": "hooks/test-coverage-monitor.kiro.hook"
        }
        
        for template_file, target_file in template_mappings.items():
            src = self.template_root / template_file
            dst = self.kiro_dir / target_file
            
            if src.exists():
                shutil.copy2(src, dst)
                print(f"📋 复制配置: {target_file}")
            else:
                print(f"⚠️ 模板文件不存在: {template_file}")
    
    def _customize_config(self, project_type: str, language: str, team_size: int):
        """根据项目特点自定义配置"""
        
        # 根据项目类型选择角色组合
        role_combinations = {
            "small": ["Full-Stack Engineer", "Test Engineer", "Code Review Specialist"],
            "medium": ["Product Manager", "Software Architect", "Full-Stack Engineer", 
                      "Test Engineer", "Security Engineer", "Code Review Specialist"],
            "large": ["Product Manager", "Software Architect", "Algorithm Engineer",
                     "Database Engineer", "UI/UX Engineer", "Full-Stack Engineer",
                     "Security Engineer", "DevOps Engineer", "Data Engineer",
                     "Test Engineer", "Scrum Master/Tech Lead", "Code Review Specialist"]
        }
        
        selected_roles = role_combinations.get(project_type, role_combinations["medium"])
        
        # 根据编程语言调整文件模式
        language_patterns = {
            "python": ["*.py"],
            "javascript": ["*.js", "*.ts"],
            "java": ["*.java"],
            "cpp": ["*.cpp", "*.c", "*.h"],
            "go": ["*.go"],
            "rust": ["*.rs"]
        }
        
        file_patterns = language_patterns.get(language, ["*.py"])
        
        # 更新Hook配置
        self._update_hook_patterns(file_patterns)
        
        # 创建项目配置文件
        project_config = {
            "project_type": project_type,
            "language": language,
            "team_size": team_size,
            "selected_roles": selected_roles,
            "file_patterns": file_patterns,
            "quality_thresholds": {
                "test_coverage": 100,
                "code_complexity": 10,
                "security_score": 90
            }
        }
        
        config_file = self.kiro_dir / "project_config.json"
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(project_config, f, indent=2, ensure_ascii=False)
            
        print(f"⚙️ 项目配置完成: {project_type}项目, {language}语言, {team_size}人团队")
    
    def _update_hook_patterns(self, file_patterns: List[str]):
        """更新Hook文件模式"""
        hook_files = [
            "hooks/quality-gate-enforcement.kiro.hook",
            "hooks/test-coverage-monitor.kiro.hook"
        ]
        
        for hook_file in hook_files:
            hook_path = self.kiro_dir / hook_file
            if hook_path.exists():
                with open(hook_path, 'r', encoding='utf-8') as f:
                    hook_config = json.load(f)
                
                if "when" in hook_config and "patterns" in hook_config["when"]:
                    hook_config["when"]["patterns"] = file_patterns
                
                with open(hook_path, 'w', encoding='utf-8') as f:
                    json.dump(hook_config, f, indent=2, ensure_ascii=False)
    
    def _validate_config(self) -> bool:
        """验证配置完整性"""
        required_files = [
            "steering/task-hierarchy-management.md",
            "steering/silicon-valley-team-config.md",
            "hooks/task-lifecycle-management.kiro.hook",
            "project_config.json"
        ]
        
        for file_path in required_files:
            if not (self.kiro_dir / file_path).exists():
                print(f"❌ 缺少必需文件: {file_path}")
                return False
        
        print("✅ 配置验证通过")
        return True
    
    def _print_next_steps(self):
        """打印后续步骤"""
        print("/n🎯 后续步骤:")
        print("1. 查看项目配置: cat .kiro/project_config.json")
        print("2. 根据需要调整角色分工和质量标准")
        print("3. 运行质量检查: python .kiro/scripts/iron_law_checker.py")
        print("4. 开始开发工作，Hook会自动执行质量门禁")
        print("/n📚 文档参考:")
        print("- 任务层次化管理: .kiro/steering/task-hierarchy-management.md")
        print("- 团队角色配置: .kiro/steering/silicon-valley-team-config.md")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="通用项目初始化工具")
    parser.add_argument("--project-root", default=".", help="项目根目录")
    parser.add_argument("--project-type", choices=["small", "medium", "large"], 
                       default="medium", help="项目类型")
    parser.add_argument("--language", choices=["python", "javascript", "java", "cpp", "go", "rust"],
                       default="python", help="主要编程语言")
    parser.add_argument("--team-size", type=int, default=6, help="团队规模")
    
    args = parser.parse_args()
    
    initializer = ProjectInitializer(args.project_root)
    success = initializer.initialize_project(
        project_type=args.project_type,
        language=args.language,
        team_size=args.team_size
    )
    
    exit(0 if success else 1)


if __name__ == "__main__":
    main()