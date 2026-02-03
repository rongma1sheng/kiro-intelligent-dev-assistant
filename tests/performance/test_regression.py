"""性能回归测试框架

白皮书依据: 第一章 1.T.3 性能测试要求

性能回归测试目标:
- 建立性能监控
- 实现自动化回归检测
- 设置性能告警机制
- 防止性能退化

回归检测标准:
- 延迟退化 > 10% → 警告
- 延迟退化 > 20% → 失败
- 吞吐量下降 > 10% → 警告
- 吞吐量下降 > 20% → 失败
"""

import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import pytest
import numpy as np
from loguru import logger

# 不导入其他测试模块，避免循环依赖


class PerformanceBaseline:
    """性能基线管理器
    
    白皮书依据: 第一章 1.T.3 性能测试要求
    
    负责存储、加载和比较性能基线数据。
    """
    
    def __init__(self, baseline_file: str = "performance_baseline.json"):
        """初始化基线管理器
        
        Args:
            baseline_file: 基线数据文件路径
        """
        self.baseline_file = Path(baseline_file)
        self.baseline_data: Dict = {}
        
        # 创建基线目录
        self.baseline_file.parent.mkdir(parents=True, exist_ok=True)
        
        # 加载现有基线
        if self.baseline_file.exists():
            self._load_baseline()
    
    def _load_baseline(self) -> None:
        """加载基线数据"""
        try:
            with open(self.baseline_file, 'r', encoding='utf-8') as f:
                self.baseline_data = json.load(f)
            logger.info(f"Loaded baseline from {self.baseline_file}")
        except Exception as e:
            logger.error(f"Failed to load baseline: {e}")
            self.baseline_data = {}
    
    def save_baseline(self, metrics: Dict) -> None:
        """保存基线数据
        
        Args:
            metrics: 性能指标字典
        """
        self.baseline_data = {
            "timestamp": datetime.now().isoformat(),
            "metrics": metrics,
            "version": "1.0"
        }
        
        try:
            with open(self.baseline_file, 'w', encoding='utf-8') as f:
                json.dump(self.baseline_data, f, indent=2, ensure_ascii=False)
            logger.info(f"Saved baseline to {self.baseline_file}")
        except Exception as e:
            logger.error(f"Failed to save baseline: {e}")
    
    def get_baseline(self) -> Optional[Dict]:
        """获取基线数据
        
        Returns:
            基线指标字典，如果不存在返回None
        """
        if not self.baseline_data:
            return None
        return self.baseline_data.get("metrics")
    
    def compare_metrics(
        self,
        current: Dict,
        baseline: Dict,
        tolerance: float = 0.10
    ) -> Tuple[bool, List[str]]:
        """比较当前指标与基线
        
        Args:
            current: 当前性能指标
            baseline: 基线性能指标
            tolerance: 容忍度（默认10%）
            
        Returns:
            (是否通过, 警告列表)
        """
        passed = True
        warnings = []
        
        for component, metrics in current.items():
            if component not in baseline:
                warnings.append(f"⚠️ {component}: No baseline found (skipping)")
                continue
            
            baseline_metrics = baseline[component]
            
            # 比较延迟指标
            if "latency" in metrics and "latency" in baseline_metrics:
                current_p99 = metrics["latency"].get("p99", 0)
                baseline_p99 = baseline_metrics["latency"].get("p99", 0)
                
                if baseline_p99 > 0:
                    degradation = (current_p99 - baseline_p99) / baseline_p99
                    
                    if degradation > tolerance * 2:  # 20% 退化
                        passed = False
                        warnings.append(
                            f"❌ {component} latency degraded by {degradation*100:.1f}% "
                            f"(P99: {current_p99:.4f} vs {baseline_p99:.4f})"
                        )
                    elif degradation > tolerance:  # 10% 退化
                        warnings.append(
                            f"⚠️ {component} latency degraded by {degradation*100:.1f}% "
                            f"(P99: {current_p99:.4f} vs {baseline_p99:.4f})"
                        )
                    else:
                        logger.info(
                            f"✅ {component} latency OK "
                            f"(P99: {current_p99:.4f} vs {baseline_p99:.4f})"
                        )
            
            # 比较吞吐量指标
            if "throughput" in metrics and "throughput" in baseline_metrics:
                current_mean = metrics["throughput"].get("mean", 0)
                baseline_mean = baseline_metrics["throughput"].get("mean", 0)
                
                if baseline_mean > 0:
                    degradation = (baseline_mean - current_mean) / baseline_mean
                    
                    if degradation > tolerance * 2:  # 20% 下降
                        passed = False
                        warnings.append(
                            f"❌ {component} throughput dropped by {degradation*100:.1f}% "
                            f"(Mean: {current_mean:.2f} vs {baseline_mean:.2f})"
                        )
                    elif degradation > tolerance:  # 10% 下降
                        warnings.append(
                            f"⚠️ {component} throughput dropped by {degradation*100:.1f}% "
                            f"(Mean: {current_mean:.2f} vs {baseline_mean:.2f})"
                        )
                    else:
                        logger.info(
                            f"✅ {component} throughput OK "
                            f"(Mean: {current_mean:.2f} vs {baseline_mean:.2f})"
                        )
        
        return passed, warnings


class RegressionTestRunner:
    """回归测试运行器
    
    白皮书依据: 第一章 1.T.3 性能测试要求
    
    负责运行所有性能测试并收集指标。
    """
    
    def __init__(self):
        """初始化测试运行器"""
        self.metrics: Dict = {}
    
    def run_scheduler_tests(self) -> Dict:
        """运行调度器性能测试
        
        Returns:
            调度器性能指标
        """
        logger.info("Running scheduler performance tests...")
        
        from src.chronos.scheduler import ChronosScheduler, Priority
        
        scheduler = ChronosScheduler()
        latencies = []
        
        # 运行延迟测试
        execution_times = []
        
        def task_callback():
            execution_times.append(time.perf_counter())
        
        scheduler.add_task(
            name="regression_test",
            callback=task_callback,
            interval=0.01,
            priority=Priority.NORMAL
        )
        
        scheduler.start()
        start_time = time.perf_counter()
        time.sleep(1.0)
        scheduler.stop()
        
        # 计算延迟
        expected_times = []
        current_time = start_time
        while current_time < start_time + 1.0:
            current_time += 0.01
            expected_times.append(current_time)
        
        for i, actual_time in enumerate(execution_times):
            if i < len(expected_times):
                latency = abs(actual_time - expected_times[i]) * 1000  # 转换为毫秒
                latencies.append(latency)
        
        # 运行吞吐量测试
        execution_count = 0
        
        def throughput_callback():
            nonlocal execution_count
            execution_count += 1
        
        scheduler2 = ChronosScheduler()
        for i in range(10):
            scheduler2.add_task(
                name=f"throughput_task_{i}",
                callback=throughput_callback,
                interval=0.01,
                priority=Priority.NORMAL
            )
        
        scheduler2.start()
        start_time = time.perf_counter()
        time.sleep(1.0)
        end_time = time.perf_counter()
        scheduler2.stop()
        
        throughput = execution_count / (end_time - start_time)
        
        return {
            "latency": {
                "p50": np.percentile(latencies, 50) if latencies else 0,
                "p95": np.percentile(latencies, 95) if latencies else 0,
                "p99": np.percentile(latencies, 99) if latencies else 0,
                "mean": np.mean(latencies) if latencies else 0,
                "std": np.std(latencies) if latencies else 0
            },
            "throughput": {
                "mean": throughput,
                "std": 0.0,
                "min": throughput,
                "max": throughput
            }
        }
    
    def run_pipeline_tests(self) -> Dict:
        """运行数据管道性能测试
        
        Returns:
            数据管道性能指标
        """
        logger.info("Running pipeline performance tests...")
        
        from src.infra.pipeline import DataPipeline, DataSource, DataProcessor, DataSink
        import pandas as pd
        
        # 创建测试数据
        test_data = pd.DataFrame({
            'value': np.random.randn(1000)
        })
        
        class TestSource(DataSource):
            def __init__(self, data):
                self.data = data
                self.index = 0
            
            def read(self, batch_size: int = 100):
                if self.index >= len(self.data):
                    return None
                batch = self.data.iloc[self.index:self.index + batch_size]
                self.index += batch_size
                return batch
        
        class TestProcessor(DataProcessor):
            def process(self, data: pd.DataFrame) -> pd.DataFrame:
                return data * 2
        
        class TestSink(DataSink):
            def __init__(self):
                self.count = 0
            
            def write(self, data: pd.DataFrame) -> None:
                self.count += len(data)
        
        # 测试延迟
        latencies = []
        for _ in range(10):
            source = TestSource(test_data.copy())
            processor = TestProcessor()
            sink = TestSink()
            
            # DataPipeline expects processors as a list
            pipeline = DataPipeline(source, [processor], sink)
            
            start = time.perf_counter()
            pipeline.run()
            elapsed = time.perf_counter() - start
            
            latencies.append(elapsed * 1000)  # 转换为毫秒
        
        # 测试吞吐量
        source = TestSource(test_data.copy())
        processor = TestProcessor()
        sink = TestSink()
        # DataPipeline expects processors as a list
        pipeline = DataPipeline(source, [processor], sink)
        
        start = time.perf_counter()
        pipeline.run()
        elapsed = time.perf_counter() - start
        
        throughput = len(test_data) / elapsed if elapsed > 0 else 0
        
        return {
            "latency": {
                "p50": np.percentile(latencies, 50),
                "p95": np.percentile(latencies, 95),
                "p99": np.percentile(latencies, 99),
                "mean": np.mean(latencies),
                "std": np.std(latencies)
            },
            "throughput": {
                "mean": throughput,
                "std": 0.0,
                "min": throughput,
                "max": throughput
            }
        }
    
    def run_spsc_tests(self) -> Dict:
        """运行SPSC队列性能测试
        
        Returns:
            SPSC队列性能指标
        """
        logger.info("Running SPSC queue performance tests...")
        
        from src.infra.spsc_queue import SPSCQueue
        
        # 测试延迟 - capacity必须是2的幂: 1024 = 2^10
        # item_size=128 to account for pickle overhead (~15 bytes)
        queue = SPSCQueue(capacity=1024, item_size=128)
        
        write_latencies = []
        read_latencies = []
        
        test_data = b"x" * 64  # Actual data size
        
        for _ in range(100):
            # 写入延迟
            start = time.perf_counter()
            queue.enqueue(test_data)
            write_latency = (time.perf_counter() - start) * 1_000_000  # 微秒
            write_latencies.append(write_latency)
            
            # 读取延迟
            start = time.perf_counter()
            queue.dequeue()
            read_latency = (time.perf_counter() - start) * 1_000_000  # 微秒
            read_latencies.append(read_latency)
        
        # 测试吞吐量 - capacity必须是2的幂: 8192 = 2^13
        queue2 = SPSCQueue(capacity=8192, item_size=128)
        
        start = time.perf_counter()
        for _ in range(1000):
            queue2.enqueue(test_data)
        write_elapsed = time.perf_counter() - start
        
        write_throughput = 1000 / write_elapsed
        
        return {
            "latency": {
                "p50": np.percentile(write_latencies + read_latencies, 50),
                "p95": np.percentile(write_latencies + read_latencies, 95),
                "p99": np.percentile(write_latencies + read_latencies, 99),
                "mean": np.mean(write_latencies + read_latencies),
                "std": np.std(write_latencies + read_latencies)
            },
            "throughput": {
                "mean": write_throughput,
                "std": 0.0,
                "min": write_throughput,
                "max": write_throughput
            }
        }
    
    def run_sanitizer_tests(self) -> Dict:
        """运行数据清洗器性能测试
        
        Returns:
            数据清洗器性能指标
        """
        logger.info("Running sanitizer performance tests...")
        
        from src.infra.sanitizer import DataSanitizer, AssetType
        import pandas as pd
        
        # 创建测试数据
        dates = pd.date_range('2025-01-01', periods=1000, freq='D')
        test_data = pd.DataFrame({
            'date': dates,
            'open': np.random.uniform(10, 100, 1000),
            'high': np.random.uniform(10, 100, 1000),
            'low': np.random.uniform(10, 100, 1000),
            'close': np.random.uniform(10, 100, 1000),
            'volume': np.random.uniform(1000, 100000, 1000)
        })
        
        # 确保HLOC一致性
        test_data['high'] = test_data[['open', 'high', 'close']].max(axis=1)
        test_data['low'] = test_data[['open', 'low', 'close']].min(axis=1)
        
        sanitizer = DataSanitizer(asset_type=AssetType.STOCK)
        
        # 测试延迟
        latencies = []
        for _ in range(10):
            start = time.perf_counter()
            sanitizer.clean(test_data.copy())
            elapsed = (time.perf_counter() - start) * 1000  # 毫秒
            latencies.append(elapsed)
        
        # 测试吞吐量
        start = time.perf_counter()
        sanitizer.clean(test_data.copy())
        elapsed = time.perf_counter() - start
        
        throughput = len(test_data) / elapsed
        
        return {
            "latency": {
                "p50": np.percentile(latencies, 50),
                "p95": np.percentile(latencies, 95),
                "p99": np.percentile(latencies, 99),
                "mean": np.mean(latencies),
                "std": np.std(latencies)
            },
            "throughput": {
                "mean": throughput,
                "std": 0.0,
                "min": throughput,
                "max": throughput
            }
        }
    
    def run_all_tests(self) -> Dict:
        """运行所有性能测试
        
        Returns:
            所有组件的性能指标
        """
        self.metrics = {
            "scheduler": self.run_scheduler_tests(),
            "pipeline": self.run_pipeline_tests(),
            "spsc_queue": self.run_spsc_tests(),
            "sanitizer": self.run_sanitizer_tests()
        }
        
        return self.metrics


@pytest.fixture
def baseline_manager():
    """创建基线管理器"""
    return PerformanceBaseline("tests/performance/performance_baseline.json")


@pytest.fixture
def test_runner():
    """创建测试运行器"""
    return RegressionTestRunner()


class TestPerformanceRegression:
    """性能回归测试套件
    
    白皮书依据: 第一章 1.T.3 性能测试要求
    """
    
    def test_establish_baseline(self, baseline_manager, test_runner):
        """建立性能基线
        
        白皮书依据: 第一章 1.T.3 性能测试要求
        
        首次运行时建立性能基线，后续运行将与此基线比较。
        """
        logger.info("Establishing performance baseline...")
        
        # 运行所有性能测试
        metrics = test_runner.run_all_tests()
        
        # 保存基线
        baseline_manager.save_baseline(metrics)
        
        logger.info("Performance baseline established successfully")
        
        # 生成基线报告
        report = self._generate_baseline_report(metrics)
        logger.info(f"\n{report}")
    
    def test_regression_detection(self, baseline_manager, test_runner):
        """检测性能回归
        
        白皮书依据: 第一章 1.T.3 性能测试要求
        
        运行性能测试并与基线比较，检测性能退化。
        """
        logger.info("Running regression detection...")
        
        # 获取基线
        baseline = baseline_manager.get_baseline()
        
        if baseline is None:
            pytest.skip("No baseline found, run test_establish_baseline first")
        
        # 运行当前性能测试
        current_metrics = test_runner.run_all_tests()
        
        # 比较指标
        passed, warnings = baseline_manager.compare_metrics(
            current_metrics,
            baseline,
            tolerance=0.10  # 10% 容忍度
        )
        
        # 生成回归报告
        report = self._generate_regression_report(
            current_metrics,
            baseline,
            warnings
        )
        logger.info(f"\n{report}")
        
        # 如果有警告，输出到控制台
        if warnings:
            logger.warning("Performance regression detected:")
            for warning in warnings:
                logger.warning(f"  {warning}")
        
        # 断言测试通过
        assert passed, f"Performance regression detected:\n" + "\n".join(warnings)
    
    def test_scheduler_regression(self, baseline_manager, test_runner):
        """调度器性能回归测试
        
        白皮书依据: 第一章 1.1 多时间尺度统一调度
        性能要求: 调度延迟 < 1ms (P99), 吞吐量 > 1000 tasks/s
        """
        logger.info("Testing scheduler performance regression...")
        
        baseline = baseline_manager.get_baseline()
        if baseline is None:
            pytest.skip("No baseline found")
        
        current = test_runner.run_scheduler_tests()
        
        passed, warnings = baseline_manager.compare_metrics(
            {"scheduler": current},
            {"scheduler": baseline.get("scheduler", {})},
            tolerance=0.10
        )
        
        if warnings:
            for warning in warnings:
                logger.warning(warning)
        
        assert passed, "Scheduler performance regression detected"
    
    def test_pipeline_regression(self, baseline_manager, test_runner):
        """数据管道性能回归测试
        
        白皮书依据: 第三章 3.1 数据管道
        性能要求: 处理延迟 < 10ms (P99), 吞吐量 > 1M records/s
        """
        logger.info("Testing pipeline performance regression...")
        
        baseline = baseline_manager.get_baseline()
        if baseline is None:
            pytest.skip("No baseline found")
        
        current = test_runner.run_pipeline_tests()
        
        passed, warnings = baseline_manager.compare_metrics(
            {"pipeline": current},
            {"pipeline": baseline.get("pipeline", {})},
            tolerance=0.10
        )
        
        if warnings:
            for warning in warnings:
                logger.warning(warning)
        
        assert passed, "Pipeline performance regression detected"
    
    def test_spsc_regression(self, baseline_manager, test_runner):
        """SPSC队列性能回归测试
        
        白皮书依据: 第三章 3.2 SPSC无锁队列
        性能要求: 读写延迟 < 100μs (P99), 吞吐量 > 10M ops/s
        """
        logger.info("Testing SPSC queue performance regression...")
        
        baseline = baseline_manager.get_baseline()
        if baseline is None:
            pytest.skip("No baseline found")
        
        current = test_runner.run_spsc_tests()
        
        passed, warnings = baseline_manager.compare_metrics(
            {"spsc_queue": current},
            {"spsc_queue": baseline.get("spsc_queue", {})},
            tolerance=0.10
        )
        
        if warnings:
            for warning in warnings:
                logger.warning(warning)
        
        assert passed, "SPSC queue performance regression detected"
    
    def test_sanitizer_regression(self, baseline_manager, test_runner):
        """数据清洗器性能回归测试
        
        白皮书依据: 第三章 3.3 数据清洗器
        性能要求: 清洗延迟 < 50ms (P99) for 1K records, 吞吐量 > 20K records/s
        """
        logger.info("Testing sanitizer performance regression...")
        
        baseline = baseline_manager.get_baseline()
        if baseline is None:
            pytest.skip("No baseline found")
        
        current = test_runner.run_sanitizer_tests()
        
        passed, warnings = baseline_manager.compare_metrics(
            {"sanitizer": current},
            {"sanitizer": baseline.get("sanitizer", {})},
            tolerance=0.10
        )
        
        if warnings:
            for warning in warnings:
                logger.warning(warning)
        
        assert passed, "Sanitizer performance regression detected"
    
    def _generate_baseline_report(self, metrics: Dict) -> str:
        """生成基线报告
        
        Args:
            metrics: 性能指标
            
        Returns:
            格式化的报告字符串
        """
        report = []
        report.append("=" * 70)
        report.append("Performance Baseline Report")
        report.append("=" * 70)
        report.append(f"Timestamp: {datetime.now().isoformat()}")
        report.append("")
        
        for component, data in metrics.items():
            report.append(f"{component.upper()}:")
            
            if "latency" in data:
                lat = data["latency"]
                report.append(f"  Latency (ms/μs):")
                report.append(f"    P50:  {lat['p50']:.4f}")
                report.append(f"    P95:  {lat['p95']:.4f}")
                report.append(f"    P99:  {lat['p99']:.4f}")
                report.append(f"    Mean: {lat['mean']:.4f}")
            
            if "throughput" in data:
                thr = data["throughput"]
                report.append(f"  Throughput:")
                report.append(f"    Mean: {thr['mean']:.2f}")
            
            report.append("")
        
        report.append("=" * 70)
        
        return "\n".join(report)
    
    def _generate_regression_report(
        self,
        current: Dict,
        baseline: Dict,
        warnings: List[str]
    ) -> str:
        """生成回归报告
        
        Args:
            current: 当前指标
            baseline: 基线指标
            warnings: 警告列表
            
        Returns:
            格式化的报告字符串
        """
        report = []
        report.append("=" * 70)
        report.append("Performance Regression Report")
        report.append("=" * 70)
        report.append(f"Timestamp: {datetime.now().isoformat()}")
        report.append("")
        
        if not warnings:
            report.append("✅ No performance regression detected")
        else:
            report.append(f"⚠️ {len(warnings)} issue(s) detected:")
            for warning in warnings:
                report.append(f"  {warning}")
        
        report.append("")
        report.append("Detailed Comparison:")
        report.append("")
        
        for component in current.keys():
            if component not in baseline:
                continue
            
            report.append(f"{component.upper()}:")
            
            curr_data = current[component]
            base_data = baseline[component]
            
            if "latency" in curr_data and "latency" in base_data:
                curr_p99 = curr_data["latency"]["p99"]
                base_p99 = base_data["latency"]["p99"]
                diff = ((curr_p99 - base_p99) / base_p99 * 100) if base_p99 > 0 else 0
                
                report.append(f"  Latency P99: {curr_p99:.4f} vs {base_p99:.4f} ({diff:+.1f}%)")
            
            if "throughput" in curr_data and "throughput" in base_data:
                curr_mean = curr_data["throughput"]["mean"]
                base_mean = base_data["throughput"]["mean"]
                diff = ((curr_mean - base_mean) / base_mean * 100) if base_mean > 0 else 0
                
                report.append(f"  Throughput: {curr_mean:.2f} vs {base_mean:.2f} ({diff:+.1f}%)")
            
            report.append("")
        
        report.append("=" * 70)
        
        return "\n".join(report)


if __name__ == "__main__":
    # 运行回归测试
    pytest.main([__file__, "-v", "-s"])
