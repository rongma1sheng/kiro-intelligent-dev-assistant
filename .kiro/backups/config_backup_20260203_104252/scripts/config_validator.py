#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
.kiro配置验证脚本 v4.0

验证.kiro目录下所有配置文件的一致性和完整性
- Hook配置验证
- Settings配置验证  
- Specs文档验证
- Steering配置验证
- 版本一致性检查
"""

import json
import os
import re
from pathlib import Path
from typing import Dict, List, Any, Tuple


class KiroConfigValidator:
    """Kiro配置验证器"""
    
    def __init__(self, kiro_path: str = ".kiro"):
        self.kiro_path = Path(kiro_path)
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.target_version = "4.0.0"
        
    def validate_all(self) -> Tuple[bool, List[str], List[str]]:
        """验证所有配置"""
        print("🔍 开始.kiro配置验证...")
        
        # 验证目录结构
        self._validate_directory_structure()
        
        # 验证Hook配置
        self._validate_hooks()
        
        # 验证Settings配置
        self._validate_settings()
        
        # 验证Specs文档
        self._validate_specs()
        
        # 验证Steering配置
        self._validate_steering()
        
        # 验证版本一致性
        self._validate_version_consistency()
        
        # 输出结果
        self._print_results()
        
        return len(self.errors) == 0, self.errors, self.warnings
    
    def _validate_directory_structure(self):
        """验证目录结构"""
        required_dirs = ["hooks", "settings", "specs", "steering"]
        
        for dir_name in required_dirs:
            dir_path = self.kiro_path / dir_name
            if not dir_path.exists():
                self.errors.append(f"缺少必需目录: {dir_path}")
            elif not dir_path.is_dir():
                self.errors.append(f"路径不是目录: {dir_path}")
    
    def _validate_hooks(self):
        """验证Hook配置"""
        hooks_dir = self.kiro_path / "hooks"
        if not hooks_dir.exists():
            return
            
        hook_files = list(hooks_dir.glob("*.hook"))
        
        if len(hook_files) == 0:
            self.warnings.append("hooks目录中没有找到.hook文件")
            return
        
        print(f"📋 验证 {len(hook_files)} 个Hook文件...")
        
        for hook_file in hook_files:
            try:
                with open(hook_file, 'r', encoding='utf-8') as f:
                    hook_config = json.load(f)
                
                # 验证必需字段
                required_fields = ["name", "version", "when", "then"]
                for field in required_fields:
                    if field not in hook_config:
                        self.errors.append(f"Hook {hook_file.name} 缺少必需字段: {field}")
                
                # 验证版本
                if "version" in hook_config:
                    if hook_config["version"] != self.target_version:
                        self.warnings.append(f"Hook {hook_file.name} 版本不一致: {hook_config['version']} != {self.target_version}")
                
                # 验证触发条件
                if "when" in hook_config:
                    when_config = hook_config["when"]
                    if "type" not in when_config:
                        self.errors.append(f"Hook {hook_file.name} 缺少触发类型")
                    elif when_config["type"] not in ["fileEdited", "userTriggered", "promptSubmit"]:
                        self.warnings.append(f"Hook {hook_file.name} 使用了非标准触发类型: {when_config['type']}")
                
            except json.JSONDecodeError as e:
                self.errors.append(f"Hook {hook_file.name} JSON格式错误: {e}")
            except Exception as e:
                self.errors.append(f"Hook {hook_file.name} 验证失败: {e}")
    
    def _validate_settings(self):
        """验证Settings配置"""
        settings_dir = self.kiro_path / "settings"
        if not settings_dir.exists():
            return
        
        # 验证LLM行为约束配置
        llm_config_file = settings_dir / "llm-behavior-constraints.json"
        if llm_config_file.exists():
            try:
                with open(llm_config_file, 'r', encoding='utf-8') as f:
                    llm_config = json.load(f)
                
                # 验证版本
                if llm_config.get("version") != self.target_version:
                    self.warnings.append(f"LLM配置版本不一致: {llm_config.get('version')} != {self.target_version}")
                
                # 验证必需配置段
                required_sections = ["instruction_constraints", "context_protection", "quality_thresholds"]
                for section in required_sections:
                    if section not in llm_config:
                        self.errors.append(f"LLM配置缺少必需段: {section}")
                        
            except Exception as e:
                self.errors.append(f"LLM配置验证失败: {e}")
        
        # 验证MCP配置
        mcp_files = ["mcp.json", "mcp_mac.json"]
        for mcp_file in mcp_files:
            mcp_path = settings_dir / mcp_file
            if mcp_path.exists():
                try:
                    with open(mcp_path, 'r', encoding='utf-8') as f:
                        mcp_config = json.load(f)
                    
                    if "mcpServers" not in mcp_config:
                        self.errors.append(f"MCP配置 {mcp_file} 缺少mcpServers段")
                        
                except Exception as e:
                    self.errors.append(f"MCP配置 {mcp_file} 验证失败: {e}")
    
    def _validate_specs(self):
        """验证Specs文档"""
        specs_dir = self.kiro_path / "specs"
        if not specs_dir.exists():
            self.warnings.append("缺少specs目录")
            return
        
        # 检查是否有规格文档
        spec_dirs = [d for d in specs_dir.iterdir() if d.is_dir()]
        if len(spec_dirs) == 0:
            self.warnings.append("specs目录中没有找到规格文档")
        
        for spec_dir in spec_dirs:
            required_files = ["requirements.md", "design.md"]
            for req_file in required_files:
                file_path = spec_dir / req_file
                if not file_path.exists():
                    self.warnings.append(f"规格 {spec_dir.name} 缺少文件: {req_file}")
    
    def _validate_steering(self):
        """验证Steering配置"""
        steering_dir = self.kiro_path / "steering"
        if not steering_dir.exists():
            self.errors.append("缺少steering目录")
            return
        
        # 检查核心配置文件
        core_files = [
            "silicon-valley-team-config-optimized.md",
            "task-hierarchy-management.md",
            "role-permission-matrix.md"
        ]
        
        for core_file in core_files:
            file_path = steering_dir / core_file
            if not file_path.exists():
                self.warnings.append(f"缺少核心steering文件: {core_file}")
    
    def _validate_version_consistency(self):
        """验证版本一致性"""
        print("🔍 检查版本一致性...")
        
        versions_found = set()
        
        # 检查Hook版本
        hooks_dir = self.kiro_path / "hooks"
        if hooks_dir.exists():
            for hook_file in hooks_dir.glob("*.hook"):
                try:
                    with open(hook_file, 'r', encoding='utf-8') as f:
                        hook_config = json.load(f)
                    if "version" in hook_config:
                        versions_found.add(hook_config["version"])
                except:
                    pass
        
        # 检查Settings版本
        settings_dir = self.kiro_path / "settings"
        llm_config_file = settings_dir / "llm-behavior-constraints.json"
        if llm_config_file.exists():
            try:
                with open(llm_config_file, 'r', encoding='utf-8') as f:
                    llm_config = json.load(f)
                if "version" in llm_config:
                    versions_found.add(llm_config["version"])
            except:
                pass
        
        if len(versions_found) > 1:
            self.warnings.append(f"发现多个版本: {versions_found}")
        elif len(versions_found) == 1 and list(versions_found)[0] != self.target_version:
            self.warnings.append(f"版本不是目标版本 {self.target_version}: {versions_found}")
    
    def _print_results(self):
        """输出验证结果"""
        print("\n" + "="*60)
        print("📊 .kiro配置验证结果")
        print("="*60)
        
        if len(self.errors) == 0 and len(self.warnings) == 0:
            print("✅ 所有配置验证通过！")
        else:
            if self.errors:
                print(f"❌ 发现 {len(self.errors)} 个错误:")
                for i, error in enumerate(self.errors, 1):
                    print(f"  {i}. {error}")
            
            if self.warnings:
                print(f"⚠️ 发现 {len(self.warnings)} 个警告:")
                for i, warning in enumerate(self.warnings, 1):
                    print(f"  {i}. {warning}")
        
        print("="*60)


def main():
    """主函数"""
    validator = KiroConfigValidator()
    success, errors, warnings = validator.validate_all()
    
    if success:
        print("🎉 配置验证成功！")
        return 0
    else:
        print("💥 配置验证失败！")
        return 1


if __name__ == "__main__":
    exit(main())