#!/usr/bin/env python3
"""
Hook系统验证器 - 硅谷项目开发经理设计
验证所有Hook配置的正确性和有效性
"""

import json
import os
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Any
from datetime import datetime

class HookSystemValidator:
    """Hook系统验证器"""
    
    def __init__(self, hooks_dir: str = ".kiro/hooks"):
        self.hooks_dir = Path(hooks_dir)
        self.logger = self._setup_logger()
        self.validation_results = {}
        
    def _setup_logger(self) -> logging.Logger:
        """设置日志记录器"""
        logger = logging.getLogger('hook_system_validator')
        logger.setLevel(logging.INFO)
        
        # 确保日志目录存在
        log_dir = Path('logs')
        log_dir.mkdir(exist_ok=True)
        
        handler = logging.FileHandler('logs/hook_validation.log', encoding='utf-8')
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
        return logger
    
    def validate_all_hooks(self) -> Dict[str, Any]:
        """验证所有Hook配置"""
        if not self.hooks_dir.exists():
            return {"error": f"Hook目录不存在: {self.hooks_dir}"}
        
        hook_files = list(self.hooks_dir.glob("*.kiro.hook"))
        if not hook_files:
            return {"error": "未找到任何Hook文件"}
        
        results = {
            "timestamp": datetime.now().isoformat(),
            "total_hooks": len(hook_files),
            "validation_results": {},
            "summary": {"passed": 0, "failed": 0, "warnings": 0}
        }
        
        for hook_file in hook_files:
            hook_name = hook_file.name
            self.logger.info(f"验证Hook: {hook_name}")
            
            validation_result = self._validate_single_hook(hook_file)
            results["validation_results"][hook_name] = validation_result
            
            # 更新摘要
            if validation_result["status"] == "passed":
                results["summary"]["passed"] += 1
            elif validation_result["status"] == "failed":
                results["summary"]["failed"] += 1
            else:
                results["summary"]["warnings"] += 1
        
        return results
    
    def _validate_single_hook(self, hook_file: Path) -> Dict[str, Any]:
        """验证单个Hook文件"""
        result = {
            "status": "unknown",
            "checks": {},
            "errors": [],
            "warnings": [],
            "metadata": {}
        }
        
        try:
            # 1. JSON格式验证
            with open(hook_file, 'r', encoding='utf-8') as f:
                hook_config = json.load(f)
            result["checks"]["json_format"] = "passed"
            
            # 2. 必需字段验证
            required_fields = ["name", "version", "description", "when", "then"]
            missing_fields = []
            for field in required_fields:
                if field not in hook_config:
                    missing_fields.append(field)
            
            if missing_fields:
                result["checks"]["required_fields"] = "failed"
                result["errors"].append(f"缺少必需字段: {missing_fields}")
            else:
                result["checks"]["required_fields"] = "passed"
            
            # 3. 字段类型验证
            type_checks = self._validate_field_types(hook_config)
            result["checks"]["field_types"] = type_checks["status"]
            if type_checks["errors"]:
                result["errors"].extend(type_checks["errors"])
            
            # 4. 触发器验证
            trigger_checks = self._validate_trigger_config(hook_config.get("when", {}))
            result["checks"]["trigger_config"] = trigger_checks["status"]
            if trigger_checks["errors"]:
                result["errors"].extend(trigger_checks["errors"])
            if trigger_checks["warnings"]:
                result["warnings"].extend(trigger_checks["warnings"])
            
            # 5. 动作验证
            action_checks = self._validate_action_config(hook_config.get("then", {}))
            result["checks"]["action_config"] = action_checks["status"]
            if action_checks["errors"]:
                result["errors"].extend(action_checks["errors"])
            if action_checks["warnings"]:
                result["warnings"].extend(action_checks["warnings"])
            
            # 6. 提取元数据
            result["metadata"] = {
                "name": hook_config.get("name", ""),
                "version": hook_config.get("version", ""),
                "description": hook_config.get("description", ""),
                "trigger_type": hook_config.get("when", {}).get("type", ""),
                "action_type": hook_config.get("then", {}).get("type", "")
            }
            
            # 确定总体状态
            if result["errors"]:
                result["status"] = "failed"
            elif result["warnings"]:
                result["status"] = "warning"
            else:
                result["status"] = "passed"
                
        except json.JSONDecodeError as e:
            result["status"] = "failed"
            result["checks"]["json_format"] = "failed"
            result["errors"].append(f"JSON格式错误: {e}")
        except Exception as e:
            result["status"] = "failed"
            result["errors"].append(f"验证过程出错: {e}")
        
        return result
    
    def _validate_field_types(self, hook_config: Dict) -> Dict[str, Any]:
        """验证字段类型"""
        result = {"status": "passed", "errors": []}
        
        # 验证字符串字段
        string_fields = ["name", "version", "description"]
        for field in string_fields:
            if field in hook_config and not isinstance(hook_config[field], str):
                result["errors"].append(f"字段 {field} 应该是字符串类型")
        
        # 验证对象字段
        object_fields = ["when", "then"]
        for field in object_fields:
            if field in hook_config and not isinstance(hook_config[field], dict):
                result["errors"].append(f"字段 {field} 应该是对象类型")
        
        if result["errors"]:
            result["status"] = "failed"
        
        return result
    
    def _validate_trigger_config(self, when_config: Dict) -> Dict[str, Any]:
        """验证触发器配置"""
        result = {"status": "passed", "errors": [], "warnings": []}
        
        if not when_config:
            result["errors"].append("触发器配置为空")
            result["status"] = "failed"
            return result
        
        # 验证触发器类型
        trigger_type = when_config.get("type")
        valid_triggers = [
            "agentStart", "agentStop", "promptSubmit", 
            "fileEdited", "fileCreated", "fileDeleted", "userTriggered"
        ]
        
        if not trigger_type:
            result["errors"].append("缺少触发器类型")
        elif trigger_type not in valid_triggers:
            result["errors"].append(f"无效的触发器类型: {trigger_type}")
        
        # 验证文件模式（对于文件相关触发器）
        file_triggers = ["fileEdited", "fileCreated", "fileDeleted"]
        if trigger_type in file_triggers:
            patterns = when_config.get("patterns")
            if not patterns:
                result["warnings"].append("文件触发器缺少patterns配置")
            elif not isinstance(patterns, list):
                result["errors"].append("patterns应该是数组类型")
        
        if result["errors"]:
            result["status"] = "failed"
        elif result["warnings"]:
            result["status"] = "warning"
        
        return result
    
    def _validate_action_config(self, then_config: Dict) -> Dict[str, Any]:
        """验证动作配置"""
        result = {"status": "passed", "errors": [], "warnings": []}
        
        if not then_config:
            result["errors"].append("动作配置为空")
            result["status"] = "failed"
            return result
        
        # 验证动作类型
        action_type = then_config.get("type")
        valid_actions = ["askAgent", "runCommand"]
        
        if not action_type:
            result["errors"].append("缺少动作类型")
        elif action_type not in valid_actions:
            result["errors"].append(f"无效的动作类型: {action_type}")
        
        # 验证动作参数
        if action_type == "askAgent":
            prompt = then_config.get("prompt")
            if not prompt:
                result["errors"].append("askAgent动作缺少prompt参数")
            elif not isinstance(prompt, str):
                result["errors"].append("prompt应该是字符串类型")
            elif len(prompt.strip()) == 0:
                result["warnings"].append("prompt内容为空")
        
        elif action_type == "runCommand":
            command = then_config.get("command")
            if not command:
                result["errors"].append("runCommand动作缺少command参数")
            elif not isinstance(command, str):
                result["errors"].append("command应该是字符串类型")
        
        if result["errors"]:
            result["status"] = "failed"
        elif result["warnings"]:
            result["status"] = "warning"
        
        return result
    
    def generate_validation_report(self) -> str:
        """生成验证报告"""
        results = self.validate_all_hooks()
        
        report = []
        report.append("# Hook系统验证报告")
        report.append(f"**生成时间**: {results['timestamp']}")
        report.append(f"**总Hook数量**: {results['total_hooks']}")
        report.append("")
        
        # 摘要
        summary = results["summary"]
        report.append("## 验证摘要")
        report.append(f"- ✅ 通过: {summary['passed']}")
        report.append(f"- ❌ 失败: {summary['failed']}")
        report.append(f"- ⚠️ 警告: {summary['warnings']}")
        report.append("")
        
        # 详细结果
        report.append("## 详细验证结果")
        for hook_name, hook_result in results["validation_results"].items():
            status_icon = "✅" if hook_result["status"] == "passed" else "❌" if hook_result["status"] == "failed" else "⚠️"
            report.append(f"### {status_icon} {hook_name}")
            
            # 元数据
            metadata = hook_result["metadata"]
            report.append(f"- **名称**: {metadata.get('name', 'N/A')}")
            report.append(f"- **版本**: {metadata.get('version', 'N/A')}")
            report.append(f"- **触发器**: {metadata.get('trigger_type', 'N/A')}")
            report.append(f"- **动作**: {metadata.get('action_type', 'N/A')}")
            
            # 检查结果
            checks = hook_result["checks"]
            report.append("- **检查结果**:")
            for check_name, check_status in checks.items():
                check_icon = "✅" if check_status == "passed" else "❌" if check_status == "failed" else "⚠️"
                report.append(f"  - {check_icon} {check_name}: {check_status}")
            
            # 错误和警告
            if hook_result["errors"]:
                report.append("- **错误**:")
                for error in hook_result["errors"]:
                    report.append(f"  - ❌ {error}")
            
            if hook_result["warnings"]:
                report.append("- **警告**:")
                for warning in hook_result["warnings"]:
                    report.append(f"  - ⚠️ {warning}")
            
            report.append("")
        
        return "\n".join(report)
    
    def fix_common_issues(self) -> Dict[str, Any]:
        """修复常见问题"""
        fix_results = {}
        
        # 这里可以实现自动修复逻辑
        # 例如：格式化JSON、修复常见的配置错误等
        
        return fix_results

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Hook系统验证器')
    parser.add_argument('--validate', action='store_true', help='验证所有Hook')
    parser.add_argument('--report', action='store_true', help='生成验证报告')
    parser.add_argument('--output', type=str, help='报告输出文件')
    
    args = parser.parse_args()
    
    validator = HookSystemValidator()
    
    if args.validate or args.report:
        if args.report:
            report = validator.generate_validation_report()
            if args.output:
                with open(args.output, 'w', encoding='utf-8') as f:
                    f.write(report)
                print(f"验证报告已保存到: {args.output}")
            else:
                print(report)
        else:
            results = validator.validate_all_hooks()
            print(json.dumps(results, indent=2, ensure_ascii=False))
    else:
        print("请使用 --validate 或 --report 参数")

if __name__ == "__main__":
    main()