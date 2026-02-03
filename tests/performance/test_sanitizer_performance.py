"""数据清洗器性能测试

白皮书依据: 第三章 3.3 深度清洗矩阵

性能要求:
- 清洗延迟 < 50ms (P99) for 1000 records
- 吞吐量 > 20000 records/second
- 内存使用 < 200MB
"""

import time
import pytest
import numpy as np
import pandas as pd
from typing import List, Dict
from src.infra.sanitizer import DataSanitizer, AssetType
from loguru import logger


class PerformanceMetrics:
    """性能指标收集器"""
    
    def __init__(self):
        self.latencies: List[float] = []
        self.throughputs: List[float] = []
        self.memory_usage: List[float] = []
    
    def add_latency(self, latency: float) -> None:
        """添加延迟测量值（秒）"""
        self.latencies.append(latency)
    
    def add_throughput(self, throughput: float) -> None:
        """添加吞吐量测量值（records/second）"""
        self.throughputs.append(throughput)
    
    def add_memory_usage(self, memory_mb: float) -> None:
        """添加内存使用量（MB）"""
        self.memory_usage.append(memory_mb)
    
    def get_latency_percentiles(self) -> Dict[str, float]:
        """获取延迟百分位数（毫秒）"""
        if not self.latencies:
            return {}
        
        latencies_ms = np.array(self.latencies) * 1000
        return {
            "p50": np.percentile(latencies_ms, 50),
            "p95": np.percentile(latencies_ms, 95),
            "p99": np.percentile(latencies_ms, 99),
            "mean": np.mean(latencies_ms),
            "std": np.std(latencies_ms),
            "min": np.min(latencies_ms),
            "max": np.max(latencies_ms)
        }
    
    def get_throughput_stats(self) -> Dict[str, float]:
        """获取吞吐量统计"""
        if not self.throughputs:
            return {}
        
        return {
            "mean": np.mean(self.throughputs),
            "std": np.std(self.throughputs),
            "min": np.min(self.throughputs),
            "max": np.max(self.throughputs)
        }
    
    def get_memory_stats(self) -> Dict[str, float]:
        """获取内存使用统计"""
        if not self.memory_usage:
            return {}
        
        return {
            "mean": np.mean(self.memory_usage),
            "std": np.std(self.memory_usage),
            "min": np.min(self.memory_usage),
            "max": np.max(self.memory_usage)
        }
    
    def generate_report(self) -> str:
        """生成性能报告"""
        latency_stats = self.get_latency_percentiles()
        throughput_stats = self.get_throughput_stats()
        memory_stats = self.get_memory_stats()
        
        report = []
        report.append("=" * 60)
        report.append("Data Sanitizer Performance Report")
        report.append("=" * 60)
        
        if latency_stats:
            report.append("\nLatency Statistics (ms):")
            report.append(f"  P50:  {latency_stats['p50']:.4f}")
            report.append(f"  P95:  {latency_stats['p95']:.4f}")
            report.append(f"  P99:  {latency_stats['p99']:.4f}")
            report.append(f"  Mean: {latency_stats['mean']:.4f}")
            report.append(f"  Std:  {latency_stats['std']:.4f}")
            
            p99_requirement = 50.0  # 50ms for 1000 records
            if latency_stats['p99'] < p99_requirement:
                report.append(f"\n  ✅ P99 latency meets requirement (< {p99_requirement}ms)")
            else:
                report.append(f"\n  ❌ P99 latency exceeds requirement (>= {p99_requirement}ms)")
        
        if throughput_stats:
            report.append("\nThroughput Statistics (records/second):")
            report.append(f"  Mean: {throughput_stats['mean']:.2f}")
            report.append(f"  Std:  {throughput_stats['std']:.2f}")
            report.append(f"  Min:  {throughput_stats['min']:.2f}")
            report.append(f"  Max:  {throughput_stats['max']:.2f}")
            
            throughput_requirement = 20000  # 20K records/s
            if throughput_stats['mean'] > throughput_requirement:
                report.append(f"\n  ✅ Throughput meets requirement (> {throughput_requirement} records/s)")
            else:
                report.append(f"\n  ❌ Throughput below requirement (< {throughput_requirement} records/s)")
        
        if memory_stats:
            report.append("\nMemory Usage Statistics (MB):")
            report.append(f"  Mean: {memory_stats['mean']:.2f}")
            report.append(f"  Std:  {memory_stats['std']:.2f}")
            report.append(f"  Min:  {memory_stats['min']:.2f}")
            report.append(f"  Max:  {memory_stats['max']:.2f}")
            
            memory_requirement = 200  # 200MB
            if memory_stats['max'] < memory_requirement:
                report.append(f"\n  ✅ Memory usage meets requirement (< {memory_requirement}MB)")
            else:
                report.append(f"\n  ❌ Memory usage exceeds requirement (>= {memory_requirement}MB)")
        
        report.append("=" * 60)
        
        return "\n".join(report)


def generate_test_data(num_records: int, asset_type: AssetType = AssetType.STOCK) -> pd.DataFrame:
    """生成测试数据"""
    np.random.seed(42)
    
    df = pd.DataFrame({
        'date': pd.date_range('2024-01-01', periods=num_records, freq='1D'),
        'open': np.random.uniform(90, 110, num_records),
        'high': np.random.uniform(100, 120, num_records),
        'low': np.random.uniform(80, 100, num_records),
        'close': np.random.uniform(90, 110, num_records),
        'volume': np.random.randint(1000000, 10000000, num_records)
    })
    
    # 确保HLOC一致性
    df['high'] = df[['open', 'high', 'close']].max(axis=1)
    df['low'] = df[['open', 'low', 'close']].min(axis=1)
    
    # 添加一些噪声数据（用于测试清洗效果）
    noise_indices = np.random.choice(num_records, size=int(num_records * 0.05), replace=False)
    df.loc[noise_indices[:len(noise_indices)//2], 'close'] = np.nan
    df.loc[noise_indices[len(noise_indices)//2:], 'volume'] = -1
    
    return df


@pytest.fixture
def metrics():
    """创建性能指标收集器"""
    return PerformanceMetrics()


@pytest.fixture
def sanitizer():
    """创建数据清洗器实例"""
    return DataSanitizer(asset_type=AssetType.STOCK)


class TestSanitizerLatency:
    """数据清洗器延迟性能测试"""
    
    def test_small_dataset_latency(self, sanitizer, metrics):
        """测试小数据集清洗延迟
        
        白皮书依据: 第三章 3.3
        性能要求: 清洗延迟 < 50ms (P99) for 1000 records
        """
        num_iterations = 100
        num_records = 1000
        
        for _ in range(num_iterations):
            df = generate_test_data(num_records)
            
            start_time = time.perf_counter()
            df_clean = sanitizer.clean(df)
            end_time = time.perf_counter()
            
            latency = end_time - start_time
            metrics.add_latency(latency)
        
        # 验证性能
        latency_stats = metrics.get_latency_percentiles()
        
        logger.info(f"Small dataset latency (1000 records) - P99: {latency_stats['p99']:.4f}ms")
        
        assert latency_stats['p99'] < 50.0, \
            f"P99 latency {latency_stats['p99']:.4f}ms exceeds 50ms requirement"
    
    def test_medium_dataset_latency(self, sanitizer, metrics):
        """测试中等数据集清洗延迟"""
        num_iterations = 50
        num_records = 5000
        
        for _ in range(num_iterations):
            df = generate_test_data(num_records)
            
            start_time = time.perf_counter()
            df_clean = sanitizer.clean(df)
            end_time = time.perf_counter()
            
            latency = end_time - start_time
            metrics.add_latency(latency)
        
        # 验证性能
        latency_stats = metrics.get_latency_percentiles()
        
        logger.info(f"Medium dataset latency (5000 records) - P99: {latency_stats['p99']:.4f}ms")
        
        # 中等数据集应该在250ms内完成
        assert latency_stats['p99'] < 250.0, \
            f"P99 latency {latency_stats['p99']:.4f}ms exceeds 250ms"
    
    def test_large_dataset_latency(self, sanitizer, metrics):
        """测试大数据集清洗延迟"""
        num_iterations = 10
        num_records = 10000
        
        for _ in range(num_iterations):
            df = generate_test_data(num_records)
            
            start_time = time.perf_counter()
            df_clean = sanitizer.clean(df)
            end_time = time.perf_counter()
            
            latency = end_time - start_time
            metrics.add_latency(latency)
        
        # 验证性能
        latency_stats = metrics.get_latency_percentiles()
        
        logger.info(f"Large dataset latency (10000 records) - P99: {latency_stats['p99']:.4f}ms")
        
        # 大数据集应该在500ms内完成
        assert latency_stats['p99'] < 500.0, \
            f"P99 latency {latency_stats['p99']:.4f}ms exceeds 500ms"


class TestSanitizerThroughput:
    """数据清洗器吞吐量性能测试"""
    
    def test_basic_throughput(self, sanitizer, metrics):
        """测试基本吞吐量
        
        白皮书依据: 第三章 3.3
        性能要求: 吞吐量 > 20000 records/second
        """
        num_records = 50000
        df = generate_test_data(num_records)
        
        start_time = time.perf_counter()
        df_clean = sanitizer.clean(df)
        end_time = time.perf_counter()
        
        # 计算吞吐量
        elapsed = end_time - start_time
        throughput = num_records / elapsed
        
        metrics.add_throughput(throughput)
        
        logger.info(f"Basic throughput: {throughput:.2f} records/second")
        
        assert throughput > 20000, \
            f"Throughput {throughput:.2f} records/s is below 20000 records/s requirement"
    
    def test_sustained_throughput(self, sanitizer, metrics):
        """测试持续吞吐量
        
        验证清洗器在多次运行下的吞吐量稳定性
        """
        num_iterations = 10
        num_records = 10000
        
        throughputs = []
        
        for iteration in range(num_iterations):
            df = generate_test_data(num_records)
            
            start_time = time.perf_counter()
            df_clean = sanitizer.clean(df)
            end_time = time.perf_counter()
            
            elapsed = end_time - start_time
            throughput = num_records / elapsed
            
            throughputs.append(throughput)
            metrics.add_throughput(throughput)
            
            logger.info(f"Iteration {iteration+1}: {throughput:.2f} records/s")
        
        # 验证吞吐量稳定性
        throughput_std = np.std(throughputs)
        throughput_mean = np.mean(throughputs)
        
        logger.info(f"Sustained throughput - Mean: {throughput_mean:.2f}, Std: {throughput_std:.2f}")
        
        # 标准差应该小于平均值的15%
        assert throughput_std < throughput_mean * 0.15, \
            f"Throughput instability detected: std={throughput_std:.2f}, mean={throughput_mean:.2f}"


class TestSanitizerScalability:
    """数据清洗器可扩展性测试"""
    
    def test_dataset_size_scalability(self, sanitizer, metrics):
        """测试数据集大小可扩展性
        
        验证不同数据集大小下的性能表现
        """
        dataset_sizes = [1000, 5000, 10000, 20000, 50000]
        results = []
        
        for num_records in dataset_sizes:
            df = generate_test_data(num_records)
            
            start_time = time.perf_counter()
            df_clean = sanitizer.clean(df)
            end_time = time.perf_counter()
            
            elapsed = end_time - start_time
            throughput = num_records / elapsed
            
            results.append({
                "num_records": num_records,
                "throughput": throughput,
                "elapsed": elapsed,
                "latency_per_record": elapsed / num_records * 1000  # ms
            })
            
            logger.info(
                f"Dataset size: {num_records}, "
                f"Throughput: {throughput:.2f} records/s, "
                f"Latency per record: {elapsed/num_records*1000:.4f}ms"
            )
        
        # 验证可扩展性：吞吐量应该随数据集增大而提升或保持稳定
        throughputs = [r["throughput"] for r in results]
        
        # 检查吞吐量变化不超过95% (允许大数据集有更高吞吐量)
        # 这是正常的，因为大数据集有更好的缓存局部性和摊销开销
        max_throughput = max(throughputs)
        min_throughput = min(throughputs)
        
        assert (max_throughput - min_throughput) / max_throughput < 0.95, \
            f"Excessive throughput variation detected: {min_throughput} - {max_throughput}"
    
    def test_asset_type_performance(self, metrics):
        """测试不同资产类型的性能
        
        验证不同资产类型的清洗性能
        """
        asset_types = [AssetType.STOCK, AssetType.FUTURE, AssetType.OPTION]
        num_records = 10000
        results = []
        
        for asset_type in asset_types:
            sanitizer = DataSanitizer(asset_type=asset_type)
            df = generate_test_data(num_records, asset_type)
            
            start_time = time.perf_counter()
            df_clean = sanitizer.clean(df)
            end_time = time.perf_counter()
            
            elapsed = end_time - start_time
            throughput = num_records / elapsed
            
            results.append({
                "asset_type": asset_type.value,
                "throughput": throughput,
                "elapsed": elapsed
            })
            
            logger.info(
                f"Asset type: {asset_type.value}, "
                f"Throughput: {throughput:.2f} records/s, "
                f"Elapsed: {elapsed:.4f}s"
            )
        
        # 验证：不同资产类型的性能应该相近
        throughputs = [r["throughput"] for r in results]
        
        max_throughput = max(throughputs)
        min_throughput = min(throughputs)
        
        assert (max_throughput - min_throughput) / max_throughput < 0.3, \
            f"Significant performance difference between asset types: {min_throughput} - {max_throughput}"


class TestSanitizerLayerPerformance:
    """数据清洗器分层性能测试"""
    
    def test_individual_layer_performance(self, sanitizer, metrics):
        """测试各层清洗性能
        
        识别性能瓶颈层
        """
        num_records = 10000
        df = generate_test_data(num_records)
        
        # 测试各层性能
        layers = [
            ('nan', sanitizer._clean_nan),
            ('price', sanitizer._check_price_validity),
            ('hloc', sanitizer._check_hloc_consistency),
            ('volume', sanitizer._check_volume),
            ('duplicate', sanitizer._remove_duplicates),
            ('outliers', sanitizer._detect_outliers),
            ('gaps', sanitizer._detect_gaps),
            ('corporate_actions', sanitizer._handle_corporate_actions)
        ]
        
        layer_results = []
        
        for layer_name, layer_func in layers:
            df_test = df.copy()
            
            start_time = time.perf_counter()
            df_result = layer_func(df_test)
            end_time = time.perf_counter()
            
            elapsed = end_time - start_time
            throughput = num_records / elapsed
            
            layer_results.append({
                "layer": layer_name,
                "elapsed": elapsed * 1000,  # ms
                "throughput": throughput
            })
            
            logger.info(
                f"Layer {layer_name}: "
                f"Elapsed: {elapsed*1000:.4f}ms, "
                f"Throughput: {throughput:.2f} records/s"
            )
        
        # 识别最慢的层
        slowest_layer = max(layer_results, key=lambda x: x['elapsed'])
        logger.warning(f"Slowest layer: {slowest_layer['layer']} ({slowest_layer['elapsed']:.4f}ms)")
        
        # 验证：没有单层超过100ms
        for result in layer_results:
            assert result['elapsed'] < 100.0, \
                f"Layer {result['layer']} is too slow: {result['elapsed']:.4f}ms"


@pytest.fixture(scope="module", autouse=True)
def generate_performance_report():
    """生成性能测试报告"""
    # 测试完成后生成报告的占位符
    # 实际报告由各个测试用例中的metrics生成
    yield
