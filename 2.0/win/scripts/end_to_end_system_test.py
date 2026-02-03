#!/usr/bin/env python
"""
端到端系统功能测试 - 硅谷项目开发经理设计
验证LLM反漂移协同系统的完整功能链路
"""

import json
import time
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any
import subprocess
import sys

class EndToEndSystemTest:
    """端到端系统测试器"""
    
    def __init__(self):
        self.logger = self._setup_logger()
        self.test_results = {}
        self.start_time = datetime.now()
        
    def _setup_logger(self) -> logging.Logger:
        """设置日志记录器"""
        logger = logging.getLogger('end_to_end_system_test')
        logger.setLevel(logging.INFO)
        
        # 确保日志目录存在
        log_dir = Path('logs')
        log_dir.mkdir(exist_ok=True)
        
        handler = logging.FileHandler('logs/end_to_end_test.log', encoding='utf-8')
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
        return logger
    
    def run_complete_test_suite(self) -> Dict[str, Any]:
        """运行完整的测试套件"""
        self.logger.info("开始端到端系统功能测试")
        
        test_suite = {
            "timestamp": datetime.now().isoformat(),
            "test_name": "LLM反漂移系统端到端功能测试",
            "version": "1.0.0",
            "tests": {},
            "summary": {"passed": 0, "failed": 0, "total": 0},
            "overall_status": "unknown",
            "execution_time": 0
        }
        
        # 定义测试用例
        test_cases = [
            ("hook_system_validation", "Hook系统验证", self._test_hook_system),
            ("config_management_test", "配置管理测试", self._test_config_management),
            ("monitoring_system_test", "监控系统测试", self._test_monitoring_system),
            ("permission_matrix_test", "权限矩阵测试", self._test_permission_matrix),
            ("behavior_constraints_test", "行为约束测试", self._test_behavior_constraints),
            ("integration_test", "系统集成测试", self._test_system_integration)
        ]
        
        # 执行测试用例
        for test_id, test_name, test_function in test_cases:
            self.logger.info(f"执行测试: {test_name}")
            try:
                test_result = test_function()
                test_suite["tests"][test_id] = {
                    "name": test_name,
                    "status": test_result["status"],
                    "details": test_result,
                    "execution_time": test_result.get("execution_time", 0)
                }
                
                if test_result["status"] == "passed":
                    test_suite["summary"]["passed"] += 1
                else:
                    test_suite["summary"]["failed"] += 1
                    
            except Exception as e:
                self.logger.error(f"测试执行失败 {test_name}: {e}")
                test_suite["tests"][test_id] = {
                    "name": test_name,
                    "status": "failed",
                    "error": str(e),
                    "execution_time": 0
                }
                test_suite["summary"]["failed"] += 1
        
        test_suite["summary"]["total"] = len(test_cases)
        
        # 确定总体状态
        if test_suite["summary"]["failed"] == 0:
            test_suite["overall_status"] = "all_passed"
        elif test_suite["summary"]["passed"] > test_suite["summary"]["failed"]:
            test_suite["overall_status"] = "mostly_passed"
        else:
            test_suite["overall_status"] = "mostly_failed"
        
        # 计算总执行时间
        test_suite["execution_time"] = (datetime.now() - self.start_time).total_seconds()
        
        return test_suite
    
    def _test_hook_system(self) -> Dict[str, Any]:
        """测试Hook系统"""
        start_time = time.time()
        result = {
            "status": "unknown",
            "checks": [],
            "issues": [],
            "execution_time": 0
        }
        
        try:
            # 运行Hook验证器
            cmd_result = subprocess.run([
                sys.executable, "scripts/hook_system_validator.py", "--validate"
            ], capture_output=True, text=True, timeout=30)
            
            if cmd_result.returncode == 0:
                validation_data = json.loads(cmd_result.stdout)
                
                # 检查验证结果
                if validation_data["summary"]["failed"] == 0:
                    result["status"] = "passed"
                    result["checks"].append(f"所有{validation_data['total_hooks']}个Hook验证通过")
                else:
                    result["status"] = "failed"
                    result["issues"].append(f"有{validation_data['summary']['failed']}个Hook验证失败")
            else:
                result["status"] = "failed"
                result["issues"].append(f"Hook验证器执行失败: {cmd_result.stderr}")
                
        except subprocess.TimeoutExpired:
            result["status"] = "failed"
            result["issues"].append("Hook验证器执行超时")
        except Exception as e:
            result["status"] = "failed"
            result["issues"].append(f"Hook系统测试异常: {e}")
        
        result["execution_time"] = time.time() - start_time
        return result
    
    def _test_config_management(self) -> Dict[str, Any]:
        """测试配置管理"""
        start_time = time.time()
        result = {
            "status": "unknown",
            "checks": [],
            "issues": [],
            "execution_time": 0
        }
        
        try:
            # 运行配置管理器
            cmd_result = subprocess.run([
                sys.executable, "scripts/unified_config_manager.py", "--validate", "--report"
            ], capture_output=True, text=True, timeout=60)
            
            if cmd_result.returncode == 0:
                # 解析输出
                lines = cmd_result.stdout.strip().split('\n')
                inconsistencies_line = [line for line in lines if "个不一致问题" in line]
                
                if inconsistencies_line and "发现 0 个不一致问题" in inconsistencies_line[0]:
                    result["status"] = "passed"
                    result["checks"].append("配置一致性检查通过")
                else:
                    result["status"] = "failed"
                    result["issues"].append("发现配置不一致问题")
            else:
                result["status"] = "failed"
                result["issues"].append(f"配置管理器执行失败: {cmd_result.stderr}")
                
        except subprocess.TimeoutExpired:
            result["status"] = "failed"
            result["issues"].append("配置管理器执行超时")
        except Exception as e:
            result["status"] = "failed"
            result["issues"].append(f"配置管理测试异常: {e}")
        
        result["execution_time"] = time.time() - start_time
        return result
    
    def _test_monitoring_system(self) -> Dict[str, Any]:
        """测试监控系统"""
        start_time = time.time()
        result = {
            "status": "unknown",
            "checks": [],
            "issues": [],
            "execution_time": 0
        }
        
        try:
            # 运行LLM执行监控器
            cmd_result = subprocess.run([
                sys.executable, "scripts/llm_execution_monitor.py"
            ], capture_output=True, text=True, timeout=30)
            
            if cmd_result.returncode == 0:
                # 检查输出是否包含监控报告
                if "监控报告" in cmd_result.stdout and "system_status" in cmd_result.stdout:
                    result["status"] = "passed"
                    result["checks"].append("LLM执行监控器正常运行")
                else:
                    result["status"] = "failed"
                    result["issues"].append("监控器输出格式异常")
            else:
                result["status"] = "failed"
                result["issues"].append(f"监控器执行失败: {cmd_result.stderr}")
                
        except subprocess.TimeoutExpired:
            result["status"] = "failed"
            result["issues"].append("监控器执行超时")
        except Exception as e:
            result["status"] = "failed"
            result["issues"].append(f"监控系统测试异常: {e}")
        
        result["execution_time"] = time.time() - start_time
        return result
    
    def _test_permission_matrix(self) -> Dict[str, Any]:
        """测试权限矩阵"""
        start_time = time.time()
        result = {
            "status": "unknown",
            "checks": [],
            "issues": [],
            "execution_time": 0
        }
        
        try:
            # 检查权限矩阵文件
            matrix_file = Path(".kiro/steering/role-permission-matrix.md")
            if matrix_file.exists():
                content = matrix_file.read_text(encoding='utf-8')
                
                # 检查关键角色是否存在
                key_roles = [
                    "Code Review Specialist",
                    "Full-Stack Engineer",
                    "Software Architect",
                    "Security Engineer",
                    "Test Engineer"
                ]
                
                missing_roles = []
                for role in key_roles:
                    if role not in content:
                        missing_roles.append(role)
                
                if not missing_roles:
                    result["status"] = "passed"
                    result["checks"].append(f"权限矩阵包含所有{len(key_roles)}个关键角色")
                else:
                    result["status"] = "failed"
                    result["issues"].append(f"权限矩阵缺少角色: {missing_roles}")
            else:
                result["status"] = "failed"
                result["issues"].append("权限矩阵文件不存在")
                
        except Exception as e:
            result["status"] = "failed"
            result["issues"].append(f"权限矩阵测试异常: {e}")
        
        result["execution_time"] = time.time() - start_time
        return result
    
    def _test_behavior_constraints(self) -> Dict[str, Any]:
        """测试行为约束"""
        start_time = time.time()
        result = {
            "status": "unknown",
            "checks": [],
            "issues": [],
            "execution_time": 0
        }
        
        try:
            # 检查行为约束配置文件
            constraints_file = Path(".kiro/settings/llm-behavior-constraints.json")
            if constraints_file.exists():
                with open(constraints_file, 'r', encoding='utf-8') as f:
                    constraints_config = json.load(f)
                
                # 检查必需的配置节
                required_sections = [
                    "instruction_constraints",
                    "context_protection",
                    "quality_thresholds",
                    "violation_handling"
                ]
                
                missing_sections = []
                for section in required_sections:
                    if section not in constraints_config:
                        missing_sections.append(section)
                
                if not missing_sections:
                    result["status"] = "passed"
                    result["checks"].append(f"行为约束配置包含所有{len(required_sections)}个必需节")
                else:
                    result["status"] = "failed"
                    result["issues"].append(f"行为约束配置缺少节: {missing_sections}")
            else:
                result["status"] = "failed"
                result["issues"].append("行为约束配置文件不存在")
                
        except json.JSONDecodeError:
            result["status"] = "failed"
            result["issues"].append("行为约束配置JSON格式错误")
        except Exception as e:
            result["status"] = "failed"
            result["issues"].append(f"行为约束测试异常: {e}")
        
        result["execution_time"] = time.time() - start_time
        return result
    
    def _test_system_integration(self) -> Dict[str, Any]:
        """测试系统集成"""
        start_time = time.time()
        result = {
            "status": "unknown",
            "checks": [],
            "issues": [],
            "execution_time": 0
        }
        
        try:
            # 运行系统部署检查器
            cmd_result = subprocess.run([
                sys.executable, "scripts/system_deployment_checker.py", "--check"
            ], capture_output=True, text=True, timeout=60)
            
            if cmd_result.returncode == 0:
                deployment_data = json.loads(cmd_result.stdout)
                
                if deployment_data["deployment_progress"] == 100.0:
                    result["status"] = "passed"
                    result["checks"].append("系统集成完整性100%")
                else:
                    result["status"] = "failed"
                    result["issues"].append(f"系统集成完整性仅{deployment_data['deployment_progress']}%")
            else:
                result["status"] = "failed"
                result["issues"].append(f"系统部署检查器执行失败: {cmd_result.stderr}")
                
        except subprocess.TimeoutExpired:
            result["status"] = "failed"
            result["issues"].append("系统部署检查器执行超时")
        except Exception as e:
            result["status"] = "failed"
            result["issues"].append(f"系统集成测试异常: {e}")
        
        result["execution_time"] = time.time() - start_time
        return result
    
    def generate_test_report(self) -> str:
        """生成测试报告"""
        test_data = self.run_complete_test_suite()
        
        report = []
        report.append("# LLM反漂移系统 - 端到端功能测试报告")
        report.append(f"**测试时间**: {test_data['timestamp']}")
        report.append(f"**测试版本**: {test_data['version']}")
        report.append(f"**总体状态**: {test_data['overall_status']}")
        report.append(f"**执行时间**: {test_data['execution_time']:.2f}秒")
        report.append("")
        
        # 测试摘要
        summary = test_data["summary"]
        report.append("## 测试摘要")
        report.append(f"- ✅ 通过: {summary['passed']}")
        report.append(f"- ❌ 失败: {summary['failed']}")
        report.append(f"- 📊 总计: {summary['total']}")
        report.append(f"- 📈 通过率: {(summary['passed']/summary['total']*100):.1f}%")
        report.append("")
        
        # 详细测试结果
        report.append("## 详细测试结果")
        for test_id, test_info in test_data["tests"].items():
            status_icon = "✅" if test_info["status"] == "passed" else "❌"
            report.append(f"### {status_icon} {test_info['name']}")
            report.append(f"**状态**: {test_info['status']}")
            report.append(f"**执行时间**: {test_info.get('execution_time', 0):.2f}秒")
            
            details = test_info["details"]
            if details.get("checks"):
                report.append("**检查项**:")
                for check in details["checks"]:
                    report.append(f"- ✅ {check}")
            
            if details.get("issues"):
                report.append("**问题**:")
                for issue in details["issues"]:
                    report.append(f"- ❌ {issue}")
            
            if test_info.get("error"):
                report.append(f"**错误**: {test_info['error']}")
            
            report.append("")
        
        # 结论和建议
        report.append("## 结论和建议")
        if test_data["overall_status"] == "all_passed":
            report.append("🎉 **所有测试通过！系统功能正常，可以投入使用。**")
            report.append("")
            report.append("### 建议的下一步:")
            report.append("- 开始性能监控和数据收集")
            report.append("- 进行用户培训和文档完善")
            report.append("- 开始生产环境部署准备")
        else:
            report.append("⚠️ **发现问题，需要修复后再投入使用。**")
            report.append("")
            report.append("### 建议的修复行动:")
            report.append("- 优先修复失败的测试项")
            report.append("- 重新运行测试验证修复效果")
            report.append("- 完善系统监控和告警机制")
        
        return "\n".join(report)

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='端到端系统功能测试')
    parser.add_argument('--test', action='store_true', help='运行功能测试')
    parser.add_argument('--report', action='store_true', help='生成测试报告')
    parser.add_argument('--output', type=str, help='报告输出文件')
    
    args = parser.parse_args()
    
    tester = EndToEndSystemTest()
    
    if args.test or args.report:
        if args.report:
            report = tester.generate_test_report()
            if args.output:
                with open(args.output, 'w', encoding='utf-8') as f:
                    f.write(report)
                print(f"测试报告已保存到: {args.output}")
            else:
                print(report)
        else:
            results = tester.run_complete_test_suite()
            print(json.dumps(results, indent=2, ensure_ascii=False))
    else:
        print("请使用 --test 或 --report 参数")

if __name__ == "__main__":
    main()