"""性能报告生成器

白皮书依据: 第一章、第三章 性能要求

生成综合性能报告，包括：
- 性能基准测试结果
- 性能瓶颈识别
- 性能优化建议
- 性能趋势分析
"""

import os
import sys
import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any
from loguru import logger


class PerformanceReportGenerator:
    """性能报告生成器"""
    
    def __init__(self, output_dir: str = "performance_reports"):
        """初始化报告生成器
        
        Args:
            output_dir: 报告输出目录
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.report_file = self.output_dir / f"performance_report_{self.timestamp}.md"
        
        logger.info(f"Performance report will be saved to: {self.report_file}")
    
    def run_performance_tests(self) -> Dict[str, Any]:
        """运行所有性能测试
        
        Returns:
            测试结果字典
        """
        logger.info("Running performance tests...")
        
        results = {}
        
        # 运行调度器性能测试
        logger.info("Testing Chronos Scheduler performance...")
        scheduler_result = self._run_pytest("tests/performance/test_scheduler_performance.py")
        results['scheduler'] = scheduler_result
        
        # 运行数据管道性能测试
        logger.info("Testing Data Pipeline performance...")
        pipeline_result = self._run_pytest("tests/performance/test_pipeline_performance.py")
        results['pipeline'] = pipeline_result
        
        # 运行SPSC队列性能测试
        logger.info("Testing SPSC Queue performance...")
        spsc_result = self._run_pytest("tests/performance/test_spsc_performance.py")
        results['spsc'] = spsc_result
        
        # 运行数据清洗器性能测试
        logger.info("Testing Data Sanitizer performance...")
        sanitizer_result = self._run_pytest("tests/performance/test_sanitizer_performance.py")
        results['sanitizer'] = sanitizer_result
        
        return results
    
    def _run_pytest(self, test_file: str) -> Dict[str, Any]:
        """运行pytest测试
        
        Args:
            test_file: 测试文件路径
            
        Returns:
            测试结果
        """
        try:
            result = subprocess.run(
                ["pytest", test_file, "-v", "--tb=short"],
                capture_output=True,
                text=True,
                timeout=300
            )
            
            return {
                "success": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode
            }
        except subprocess.TimeoutExpired:
            logger.error(f"Test timeout: {test_file}")
            return {
                "success": False,
                "error": "Test timeout"
            }
        except Exception as e:
            logger.error(f"Test failed: {test_file}, error: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def collect_performance_metrics(self) -> Dict[str, Any]:
        """收集性能指标
        
        Returns:
            性能指标字典
        """
        metrics = {}
        
        # 读取各个模块的性能报告
        report_files = [
            "performance_report_scheduler.txt",
            "performance_report_pipeline.txt",
            "performance_report_spsc.txt",
            "performance_report_sanitizer.txt"
        ]
        
        for report_file in report_files:
            if os.path.exists(report_file):
                with open(report_file, 'r') as f:
                    content = f.read()
                    module_name = report_file.replace("performance_report_", "").replace(".txt", "")
                    metrics[module_name] = self._parse_report(content)
        
        return metrics
    
    def _parse_report(self, content: str) -> Dict[str, Any]:
        """解析性能报告
        
        Args:
            content: 报告内容
            
        Returns:
            解析后的指标
        """
        metrics = {}
        
        lines = content.split('\n')
        current_section = None
        
        for line in lines:
            line = line.strip()
            
            if "Latency Statistics" in line:
                current_section = "latency"
                metrics[current_section] = {}
            elif "Throughput Statistics" in line:
                current_section = "throughput"
                metrics[current_section] = {}
            elif "Memory Usage Statistics" in line:
                current_section = "memory"
                metrics[current_section] = {}
            elif current_section and ":" in line:
                # 解析指标行
                parts = line.split(":")
                if len(parts) == 2:
                    key = parts[0].strip()
                    value_str = parts[1].strip()
                    
                    # 提取数值
                    try:
                        value = float(value_str.split()[0])
                        metrics[current_section][key] = value
                    except (ValueError, IndexError):
                        pass
        
        return metrics
    
    def identify_bottlenecks(self, metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
        """识别性能瓶颈
        
        Args:
            metrics: 性能指标
            
        Returns:
            瓶颈列表
        """
        bottlenecks = []
        
        # 定义性能要求
        requirements = {
            "scheduler": {
                "latency_p99": 1.0,  # 1ms
                "throughput_mean": 1000  # 1000 tasks/s
            },
            "pipeline": {
                "latency_p99": 10.0,  # 10ms
                "throughput_mean": 1000000  # 1M records/s
            },
            "spsc": {
                "latency_p99": 100.0,  # 100μs
                "throughput_mean": 10000000  # 10M ops/s
            },
            "sanitizer": {
                "latency_p99": 50.0,  # 50ms for 1000 records
                "throughput_mean": 20000  # 20K records/s
            }
        }
        
        # 检查每个模块
        for module, module_metrics in metrics.items():
            if module not in requirements:
                continue
            
            req = requirements[module]
            
            # 检查延迟
            if "latency" in module_metrics and "P99" in module_metrics["latency"]:
                p99 = module_metrics["latency"]["P99"]
                if p99 > req["latency_p99"]:
                    bottlenecks.append({
                        "module": module,
                        "metric": "latency_p99",
                        "actual": p99,
                        "required": req["latency_p99"],
                        "severity": "high" if p99 > req["latency_p99"] * 2 else "medium"
                    })
            
            # 检查吞吐量
            if "throughput" in module_metrics and "Mean" in module_metrics["throughput"]:
                throughput = module_metrics["throughput"]["Mean"]
                if throughput < req["throughput_mean"]:
                    bottlenecks.append({
                        "module": module,
                        "metric": "throughput_mean",
                        "actual": throughput,
                        "required": req["throughput_mean"],
                        "severity": "high" if throughput < req["throughput_mean"] * 0.5 else "medium"
                    })
        
        return bottlenecks
    
    def generate_optimization_suggestions(self, bottlenecks: List[Dict[str, Any]]) -> List[str]:
        """生成优化建议
        
        Args:
            bottlenecks: 瓶颈列表
            
        Returns:
            优化建议列表
        """
        suggestions = []
        
        for bottleneck in bottlenecks:
            module = bottleneck["module"]
            metric = bottleneck["metric"]
            
            if module == "scheduler":
                if "latency" in metric:
                    suggestions.append(
                        f"- Scheduler latency optimization:\n"
                        f"  * Reduce lock contention in task queue\n"
                        f"  * Use lock-free data structures\n"
                        f"  * Optimize task sorting algorithm"
                    )
                elif "throughput" in metric:
                    suggestions.append(
                        f"- Scheduler throughput optimization:\n"
                        f"  * Batch task execution\n"
                        f"  * Reduce context switching\n"
                        f"  * Use thread pool for task execution"
                    )
            
            elif module == "pipeline":
                if "latency" in metric:
                    suggestions.append(
                        f"- Pipeline latency optimization:\n"
                        f"  * Reduce data copying\n"
                        f"  * Use zero-copy techniques\n"
                        f"  * Optimize processor chain"
                    )
                elif "throughput" in metric:
                    suggestions.append(
                        f"- Pipeline throughput optimization:\n"
                        f"  * Increase batch size\n"
                        f"  * Use parallel processing\n"
                        f"  * Optimize memory allocation"
                    )
            
            elif module == "spsc":
                if "latency" in metric:
                    suggestions.append(
                        f"- SPSC queue latency optimization:\n"
                        f"  * Use memory barriers correctly\n"
                        f"  * Optimize cache line alignment\n"
                        f"  * Reduce system call overhead"
                    )
                elif "throughput" in metric:
                    suggestions.append(
                        f"- SPSC queue throughput optimization:\n"
                        f"  * Increase queue capacity\n"
                        f"  * Batch read/write operations\n"
                        f"  * Use huge pages for shared memory"
                    )
            
            elif module == "sanitizer":
                if "latency" in metric:
                    suggestions.append(
                        f"- Sanitizer latency optimization:\n"
                        f"  * Vectorize operations with NumPy\n"
                        f"  * Use Pandas optimizations\n"
                        f"  * Cache intermediate results"
                    )
                elif "throughput" in metric:
                    suggestions.append(
                        f"- Sanitizer throughput optimization:\n"
                        f"  * Process data in chunks\n"
                        f"  * Use parallel processing\n"
                        f"  * Optimize layer execution order"
                    )
        
        return suggestions
    
    def generate_report(self) -> None:
        """生成综合性能报告"""
        logger.info("Generating comprehensive performance report...")
        
        # 运行性能测试
        test_results = self.run_performance_tests()
        
        # 收集性能指标
        metrics = self.collect_performance_metrics()
        
        # 识别瓶颈
        bottlenecks = self.identify_bottlenecks(metrics)
        
        # 生成优化建议
        suggestions = self.generate_optimization_suggestions(bottlenecks)
        
        # 生成报告
        report_lines = []
        report_lines.append("# MIA System Performance Report")
        report_lines.append("")
        report_lines.append(f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append(f"**Version**: v1.0")
        report_lines.append("")
        report_lines.append("---")
        report_lines.append("")
        
        # 执行摘要
        report_lines.append("## Executive Summary")
        report_lines.append("")
        
        total_tests = len(test_results)
        passed_tests = sum(1 for r in test_results.values() if r.get("success", False))
        
        report_lines.append(f"- Total test modules: {total_tests}")
        report_lines.append(f"- Passed modules: {passed_tests}")
        report_lines.append(f"- Failed modules: {total_tests - passed_tests}")
        report_lines.append(f"- Identified bottlenecks: {len(bottlenecks)}")
        report_lines.append("")
        
        # 性能指标
        report_lines.append("## Performance Metrics")
        report_lines.append("")
        
        for module, module_metrics in metrics.items():
            report_lines.append(f"### {module.capitalize()}")
            report_lines.append("")
            
            if "latency" in module_metrics:
                report_lines.append("**Latency:**")
                for key, value in module_metrics["latency"].items():
                    report_lines.append(f"- {key}: {value:.4f}")
                report_lines.append("")
            
            if "throughput" in module_metrics:
                report_lines.append("**Throughput:**")
                for key, value in module_metrics["throughput"].items():
                    report_lines.append(f"- {key}: {value:.2f}")
                report_lines.append("")
            
            if "memory" in module_metrics:
                report_lines.append("**Memory Usage:**")
                for key, value in module_metrics["memory"].items():
                    report_lines.append(f"- {key}: {value:.2f} MB")
                report_lines.append("")
        
        # 性能瓶颈
        report_lines.append("## Performance Bottlenecks")
        report_lines.append("")
        
        if bottlenecks:
            for bottleneck in bottlenecks:
                severity_emoji = "🔴" if bottleneck["severity"] == "high" else "🟡"
                report_lines.append(
                    f"{severity_emoji} **{bottleneck['module'].capitalize()}** - {bottleneck['metric']}"
                )
                report_lines.append(f"  - Actual: {bottleneck['actual']:.2f}")
                report_lines.append(f"  - Required: {bottleneck['required']:.2f}")
                report_lines.append(f"  - Severity: {bottleneck['severity']}")
                report_lines.append("")
        else:
            report_lines.append("✅ No performance bottlenecks detected. All metrics meet requirements.")
            report_lines.append("")
        
        # 优化建议
        report_lines.append("## Optimization Suggestions")
        report_lines.append("")
        
        if suggestions:
            for suggestion in suggestions:
                report_lines.append(suggestion)
                report_lines.append("")
        else:
            report_lines.append("✅ No optimization needed. System performance is optimal.")
            report_lines.append("")
        
        # 测试详情
        report_lines.append("## Test Details")
        report_lines.append("")
        
        for module, result in test_results.items():
            status = "✅ PASSED" if result.get("success", False) else "❌ FAILED"
            report_lines.append(f"### {module.capitalize()} - {status}")
            report_lines.append("")
            
            if not result.get("success", False):
                if "error" in result:
                    report_lines.append(f"**Error**: {result['error']}")
                    report_lines.append("")
        
        # 写入报告
        with open(self.report_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(report_lines))
        
        logger.info(f"Performance report generated: {self.report_file}")
        
        # 打印摘要
        print("\n" + "=" * 60)
        print("Performance Report Summary")
        print("=" * 60)
        print(f"Total test modules: {total_tests}")
        print(f"Passed modules: {passed_tests}")
        print(f"Failed modules: {total_tests - passed_tests}")
        print(f"Identified bottlenecks: {len(bottlenecks)}")
        print(f"\nFull report: {self.report_file}")
        print("=" * 60 + "\n")


def main():
    """主函数"""
    logger.info("Starting performance report generation...")
    
    generator = PerformanceReportGenerator()
    generator.generate_report()
    
    logger.info("Performance report generation completed")


if __name__ == "__main__":
    main()
