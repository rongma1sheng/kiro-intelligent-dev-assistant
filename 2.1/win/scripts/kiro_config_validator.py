#!/usr/bin/env python33
"""
Kiro配置系统验证器
验证所有配置文件的完整性和一致性
"""

import json
import os
import yaml
from pathlib import Path
from typing import Dict, List, Any


class KiroConfigValidator:
    """Kiro配置验证器"""
    
    def __init__(self):
        self.kiro_path = Path(".kiro")
        self.validation_results = {
            "hooks": {"valid": 0, "invalid": 0, "errors": []},
            "steering": {"valid": 0, "invalid": 0, "errors": []},
            "mcp": {"valid": 0, "invalid": 0, "errors": []},
            "templates": {"valid": 0, "invalid": 0, "errors": []},
            "specs": {"valid": 0, "invalid": 0, "errors": []}
        }
    
    def validate_hooks(self) -> bool:
        """验证Hook配置"""
        hooks_path = self.kiro_path / "hooks"
        if not hooks_path.exists():
            self.validation_results["hooks"]["errors"].append("hooks目录不存在")
            return False
        
        hook_files = list(hooks_path.glob("*.hook"))
        print(f"🔍 验证{len(hook_files)}个Hook文件...")
        
        for hook_file in hook_files:
            try:
                with open(hook_file, 'r', encoding='utf-8') as f:
                    hook_config = json.load(f)
                
                # 验证必需字段
                required_fields = ["name", "version", "when", "then"]
                for field in required_fields:
                    if field not in hook_config:
                        raise ValueError(f"缺少必需字段: {field}")
                
                # 验证when配置
                if "type" not in hook_config["when"]:
                    raise ValueError("when配置缺少type字段")
                
                # 验证then配置
                if "type" not in hook_config["then"]:
                    raise ValueError("then配置缺少type字段")
                
                self.validation_results["hooks"]["valid"] += 1
                print(f"  ✅ {hook_file.name}")
                
            except Exception as e:
                self.validation_results["hooks"]["invalid"] += 1
                error_msg = f"{hook_file.name}: {str(e)}"
                self.validation_results["hooks"]["errors"].append(error_msg)
                print(f"  ❌ {error_msg}")
        
        return self.validation_results["hooks"]["invalid"] == 0
    
    def validate_steering(self) -> bool:
        """验证Steering配置"""
        steering_path = self.kiro_path / "steering"
        if not steering_path.exists():
            self.validation_results["steering"]["errors"].append("steering目录不存在")
            return False
        
        steering_files = list(steering_path.glob("*.md"))
        print(f"🔍 验证{len(steering_files)}个Steering文件...")
        
        for steering_file in steering_files:
            try:
                with open(steering_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # 验证文件不为空
                if not content.strip():
                    raise ValueError("文件内容为空")
                
                # 验证包含inclusion配置（如果有front-matter）
                if content.startswith("---"):
                    # 有front-matter，验证格式
                    try:
                        parts = content.split("---", 2)
                        if len(parts) >= 2:
                            yaml.safe_load(parts[1])
                    except yaml.YAMLError as e:
                        raise ValueError(f"front-matter YAML格式错误: {e}")
                
                self.validation_results["steering"]["valid"] += 1
                print(f"  ✅ {steering_file.name}")
                
            except Exception as e:
                self.validation_results["steering"]["invalid"] += 1
                error_msg = f"{steering_file.name}: {str(e)}"
                self.validation_results["steering"]["errors"].append(error_msg)
                print(f"  ❌ {error_msg}")
        
        return self.validation_results["steering"]["invalid"] == 0
    
    def validate_mcp(self) -> bool:
        """验证MCP配置"""
        mcp_file = self.kiro_path / "settings" / "mcp.json"
        print("🔍 验证MCP配置...")
        
        try:
            if not mcp_file.exists():
                raise FileNotFoundError("MCP配置文件不存在")
            
            with open(mcp_file, 'r', encoding='utf-8') as f:
                mcp_config = json.load(f)
            
            # 验证基本结构
            if "mcpServers" not in mcp_config:
                raise ValueError("缺少mcpServers配置")
            
            # 验证每个服务器配置
            for server_name, server_config in mcp_config["mcpServers"].items():
                required_fields = ["command", "args"]
                for field in required_fields:
                    if field not in server_config:
                        raise ValueError(f"服务器{server_name}缺少{field}配置")
            
            self.validation_results["mcp"]["valid"] = 1
            print("  ✅ mcp.json")
            
        except Exception as e:
            self.validation_results["mcp"]["invalid"] = 1
            error_msg = f"mcp.json: {str(e)}"
            self.validation_results["mcp"]["errors"].append(error_msg)
            print(f"  ❌ {error_msg}")
        
        return self.validation_results["mcp"]["invalid"] == 0
    
    def validate_templates(self) -> bool:
        """验证模板配置"""
        templates_path = self.kiro_path / "templates"
        print("🔍 验证模板配置...")
        
        try:
            if not templates_path.exists():
                raise FileNotFoundError("templates目录不存在")
            
            # 检查全局项目配置模板
            global_config_path = templates_path / "global-project-config"
            if not global_config_path.exists():
                raise FileNotFoundError("global-project-config模板不存在")
            
            # 验证关键文件存在
            required_files = [
                "README.md",
                "USAGE_GUIDE.md",
                "scripts/project_initializer.py",
                "scripts/universal_quality_gate.py"
            ]
            
            for required_file in required_files:
                file_path = global_config_path / required_file
                if not file_path.exists():
                    raise FileNotFoundError(f"模板文件缺失: {required_file}")
            
            self.validation_results["templates"]["valid"] = 1
            print("  ✅ 模板配置完整")
            
        except Exception as e:
            self.validation_results["templates"]["invalid"] = 1
            error_msg = f"templates: {str(e)}"
            self.validation_results["templates"]["errors"].append(error_msg)
            print(f"  ❌ {error_msg}")
        
        return self.validation_results["templates"]["invalid"] == 0
    
    def validate_specs(self) -> bool:
        """验证Specs配置"""
        specs_path = self.kiro_path / "specs"
        print("🔍 验证Specs配置...")
        
        try:
            if not specs_path.exists():
                print("  ⚠️ specs目录不存在（可选）")
                return True
            
            spec_dirs = [d for d in specs_path.iterdir() if d.is_dir()]
            for spec_dir in spec_dirs:
                # 验证每个spec目录包含基本文件
                required_files = ["requirements.md", "design.md"]
                for required_file in required_files:
                    file_path = spec_dir / required_file
                    if not file_path.exists():
                        raise FileNotFoundError(f"Spec {spec_dir.name} 缺少 {required_file}")
            
            self.validation_results["specs"]["valid"] = len(spec_dirs)
            print(f"  ✅ {len(spec_dirs)}个Spec配置有效")
            
        except Exception as e:
            self.validation_results["specs"]["invalid"] = 1
            error_msg = f"specs: {str(e)}"
            self.validation_results["specs"]["errors"].append(error_msg)
            print(f"  ❌ {error_msg}")
        
        return self.validation_results["specs"]["invalid"] == 0
    
    def generate_report(self) -> Dict[str, Any]:
        """生成验证报告"""
        total_valid = sum(result["valid"] for result in self.validation_results.values())
        total_invalid = sum(result["invalid"] for result in self.validation_results.values())
        total_errors = sum(len(result["errors"]) for result in self.validation_results.values())
        
        success_rate = (total_valid / (total_valid + total_invalid)) * 100 if (total_valid + total_invalid) > 0 else 100
        
        report = {
            "timestamp": "2026-02-02T12:45:00",
            "validation_summary": {
                "total_valid": total_valid,
                "total_invalid": total_invalid,
                "total_errors": total_errors,
                "success_rate": f"{success_rate:.1f}%"
            },
            "detailed_results": self.validation_results,
            "overall_status": "PASS" if total_invalid == 0 else "FAIL"
        }
        
        return report
    
    def run_validation(self) -> bool:
        """运行完整验证"""
        print("🚀 开始Kiro配置系统验证...")
        print("=" * 50)
        
        results = []
        results.append(self.validate_hooks())
        results.append(self.validate_steering())
        results.append(self.validate_mcp())
        results.append(self.validate_templates())
        results.append(self.validate_specs())
        
        print("=" * 50)
        
        # 生成报告
        report = self.generate_report()
        
        # 输出结果
        print(f"📊 验证结果:")
        print(f"  ✅ 有效配置: {report['validation_summary']['total_valid']}")
        print(f"  ❌ 无效配置: {report['validation_summary']['total_invalid']}")
        print(f"  🔍 错误数量: {report['validation_summary']['total_errors']}")
        print(f"  📈 成功率: {report['validation_summary']['success_rate']}")
        print(f"  🎯 总体状态: {report['overall_status']}")
        
        # 输出错误详情
        if report['validation_summary']['total_errors'] > 0:
            print("/n❌ 错误详情:")
            for category, result in self.validation_results.items():
                if result["errors"]:
                    print(f"  {category}:")
                    for error in result["errors"]:
                        print(f"    - {error}")
        
        return all(results)


def main():
    """主函数"""
    validator = KiroConfigValidator()
    success = validator.run_validation()
    
    if success:
        print("/n🎉 Kiro配置系统验证通过！")
        return 0
    else:
        print("/n💥 Kiro配置系统验证失败！")
        return 1


if __name__ == "__main__":
    exit(main())