"""性能回归测试自动化脚本

白皮书依据: 第一章 1.T.3 性能测试要求

功能:
- 自动运行性能回归测试
- 生成回归报告
- 发送性能告警
- 更新性能基线

使用方法:
    # 建立基线
    python scripts/run_regression_tests.py --establish-baseline
    
    # 运行回归测试
    python scripts/run_regression_tests.py --test
    
    # 更新基线
    python scripts/run_regression_tests.py --update-baseline
    
    # 生成报告
    python scripts/run_regression_tests.py --report
"""

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from loguru import logger


class RegressionTestAutomation:
    """回归测试自动化工具
    
    白皮书依据: 第一章 1.T.3 性能测试要求
    """
    
    def __init__(self):
        """初始化自动化工具"""
        self.baseline_file = Path("tests/performance/performance_baseline.json")
        self.report_dir = Path("performance_reports")
        self.report_dir.mkdir(parents=True, exist_ok=True)
        
        # 配置日志
        logger.add(
            "logs/regression_tests.log",
            rotation="1 day",
            retention="30 days",
            level="INFO"
        )
    
    def establish_baseline(self) -> bool:
        """建立性能基线
        
        Returns:
            是否成功
        """
        logger.info("Establishing performance baseline...")
        
        try:
            # 运行基线测试
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "pytest",
                    "tests/performance/test_regression.py::TestPerformanceRegression::test_establish_baseline",
                    "-v",
                    "-s"
                ],
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if result.returncode == 0:
                logger.info("✅ Baseline established successfully")
                self._save_baseline_metadata()
                return True
            else:
                logger.error(f"❌ Failed to establish baseline:\n{result.stderr}")
                return False
        
        except subprocess.TimeoutExpired:
            logger.error("❌ Baseline establishment timed out")
            return False
        except Exception as e:
            logger.error(f"❌ Error establishing baseline: {e}")
            return False
    
    def run_regression_tests(self) -> bool:
        """运行回归测试
        
        Returns:
            是否通过
        """
        logger.info("Running performance regression tests...")
        
        # 检查基线是否存在
        if not self.baseline_file.exists():
            logger.warning("No baseline found, establishing baseline first...")
            if not self.establish_baseline():
                return False
        
        try:
            # 运行回归测试
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "pytest",
                    "tests/performance/test_regression.py::TestPerformanceRegression::test_regression_detection",
                    "-v",
                    "-s"
                ],
                capture_output=True,
                text=True,
                timeout=300
            )
            
            # 保存测试输出
            self._save_test_output(result.stdout, result.stderr)
            
            if result.returncode == 0:
                logger.info("✅ All regression tests passed")
                return True
            else:
                logger.warning("⚠️ Some regression tests failed")
                logger.warning(f"Output:\n{result.stdout}")
                logger.error(f"Errors:\n{result.stderr}")
                
                # 发送告警
                self._send_alert(result.stdout)
                
                return False
        
        except subprocess.TimeoutExpired:
            logger.error("❌ Regression tests timed out")
            return False
        except Exception as e:
            logger.error(f"❌ Error running regression tests: {e}")
            return False
    
    def run_component_tests(self, component: str) -> bool:
        """运行特定组件的回归测试
        
        Args:
            component: 组件名称 (scheduler, pipeline, spsc, sanitizer)
            
        Returns:
            是否通过
        """
        logger.info(f"Running {component} regression tests...")
        
        test_map = {
            "scheduler": "test_scheduler_regression",
            "pipeline": "test_pipeline_regression",
            "spsc": "test_spsc_regression",
            "sanitizer": "test_sanitizer_regression"
        }
        
        if component not in test_map:
            logger.error(f"Unknown component: {component}")
            return False
        
        try:
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "pytest",
                    f"tests/performance/test_regression.py::TestPerformanceRegression::{test_map[component]}",
                    "-v",
                    "-s"
                ],
                capture_output=True,
                text=True,
                timeout=120
            )
            
            if result.returncode == 0:
                logger.info(f"✅ {component} regression tests passed")
                return True
            else:
                logger.warning(f"⚠️ {component} regression tests failed")
                logger.warning(f"Output:\n{result.stdout}")
                return False
        
        except Exception as e:
            logger.error(f"❌ Error running {component} tests: {e}")
            return False
    
    def update_baseline(self) -> bool:
        """更新性能基线
        
        Returns:
            是否成功
        """
        logger.info("Updating performance baseline...")
        
        # 备份旧基线
        if self.baseline_file.exists():
            backup_file = self.baseline_file.with_suffix(
                f".backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            )
            self.baseline_file.rename(backup_file)
            logger.info(f"Old baseline backed up to {backup_file}")
        
        # 建立新基线
        return self.establish_baseline()
    
    def generate_report(self) -> Optional[str]:
        """生成回归测试报告
        
        Returns:
            报告文件路径，失败返回None
        """
        logger.info("Generating regression test report...")
        
        if not self.baseline_file.exists():
            logger.error("No baseline found, cannot generate report")
            return None
        
        try:
            # 加载基线数据
            with open(self.baseline_file, 'r', encoding='utf-8') as f:
                baseline = json.load(f)
            
            # 生成报告
            report_file = self.report_dir / f"regression_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
            
            with open(report_file, 'w', encoding='utf-8') as f:
                f.write(self._format_report(baseline))
            
            logger.info(f"✅ Report generated: {report_file}")
            return str(report_file)
        
        except Exception as e:
            logger.error(f"❌ Error generating report: {e}")
            return None
    
    def _save_baseline_metadata(self) -> None:
        """保存基线元数据"""
        metadata = {
            "established_at": datetime.now().isoformat(),
            "python_version": sys.version,
            "platform": sys.platform
        }
        
        metadata_file = self.baseline_file.with_suffix(".metadata.json")
        
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
    
    def _save_test_output(self, stdout: str, stderr: str) -> None:
        """保存测试输出
        
        Args:
            stdout: 标准输出
            stderr: 标准错误
        """
        output_file = self.report_dir / f"test_output_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("=== STDOUT ===\n")
            f.write(stdout)
            f.write("\n\n=== STDERR ===\n")
            f.write(stderr)
    
    def _send_alert(self, message: str) -> None:
        """发送性能告警
        
        Args:
            message: 告警消息
        """
        logger.warning("=" * 70)
        logger.warning("PERFORMANCE REGRESSION ALERT")
        logger.warning("=" * 70)
        logger.warning(message)
        logger.warning("=" * 70)
        
        # TODO: 集成告警系统 (邮件、钉钉、企业微信等)
        # 这里可以添加实际的告警发送逻辑
    
    def _format_report(self, baseline: Dict) -> str:
        """格式化报告
        
        Args:
            baseline: 基线数据
            
        Returns:
            格式化的Markdown报告
        """
        report = []
        report.append("# Performance Regression Test Report")
        report.append("")
        report.append(f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"**Baseline Established**: {baseline.get('timestamp', 'Unknown')}")
        report.append("")
        
        report.append("## Performance Baseline")
        report.append("")
        
        metrics = baseline.get("metrics", {})
        
        for component, data in metrics.items():
            report.append(f"### {component.upper()}")
            report.append("")
            
            if "latency" in data:
                lat = data["latency"]
                report.append("**Latency Statistics:**")
                report.append("")
                report.append("| Metric | Value |")
                report.append("|--------|-------|")
                report.append(f"| P50 | {lat['p50']:.4f} |")
                report.append(f"| P95 | {lat['p95']:.4f} |")
                report.append(f"| P99 | {lat['p99']:.4f} |")
                report.append(f"| Mean | {lat['mean']:.4f} |")
                report.append(f"| Std | {lat['std']:.4f} |")
                report.append("")
            
            if "throughput" in data:
                thr = data["throughput"]
                report.append("**Throughput Statistics:**")
                report.append("")
                report.append("| Metric | Value |")
                report.append("|--------|-------|")
                report.append(f"| Mean | {thr['mean']:.2f} |")
                report.append(f"| Std | {thr['std']:.2f} |")
                report.append(f"| Min | {thr['min']:.2f} |")
                report.append(f"| Max | {thr['max']:.2f} |")
                report.append("")
        
        report.append("## Regression Detection Rules")
        report.append("")
        report.append("- ⚠️ Warning: Performance degradation > 10%")
        report.append("- ❌ Failure: Performance degradation > 20%")
        report.append("")
        
        report.append("## How to Run")
        report.append("")
        report.append("```bash")
        report.append("# Run all regression tests")
        report.append("python scripts/run_regression_tests.py --test")
        report.append("")
        report.append("# Run specific component test")
        report.append("python scripts/run_regression_tests.py --test --component scheduler")
        report.append("")
        report.append("# Update baseline")
        report.append("python scripts/run_regression_tests.py --update-baseline")
        report.append("```")
        report.append("")
        
        return "\n".join(report)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="Performance Regression Test Automation"
    )
    
    parser.add_argument(
        "--establish-baseline",
        action="store_true",
        help="Establish performance baseline"
    )
    
    parser.add_argument(
        "--test",
        action="store_true",
        help="Run regression tests"
    )
    
    parser.add_argument(
        "--component",
        type=str,
        choices=["scheduler", "pipeline", "spsc", "sanitizer"],
        help="Test specific component"
    )
    
    parser.add_argument(
        "--update-baseline",
        action="store_true",
        help="Update performance baseline"
    )
    
    parser.add_argument(
        "--report",
        action="store_true",
        help="Generate regression test report"
    )
    
    args = parser.parse_args()
    
    automation = RegressionTestAutomation()
    
    success = True
    
    if args.establish_baseline:
        success = automation.establish_baseline()
    
    elif args.test:
        if args.component:
            success = automation.run_component_tests(args.component)
        else:
            success = automation.run_regression_tests()
    
    elif args.update_baseline:
        success = automation.update_baseline()
    
    elif args.report:
        report_file = automation.generate_report()
        success = report_file is not None
    
    else:
        parser.print_help()
        sys.exit(1)
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
