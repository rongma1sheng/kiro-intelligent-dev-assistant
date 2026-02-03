# Performance Tests

This directory contains comprehensive performance benchmarking tests for the MIA system.

## Overview

Performance tests establish baselines, identify bottlenecks, and ensure the system meets the performance requirements defined in the whitepaper.

## Test Modules

### 1. Scheduler Performance (`test_scheduler_performance.py`)

Tests the Chronos scheduler's performance characteristics.

**Requirements**:
- Scheduling latency < 1ms (P99)
- Throughput > 1000 tasks/second

**Test Classes**:
- `TestSchedulerLatency`: Latency measurements
- `TestSchedulerThroughput`: Throughput measurements
- `TestSchedulerScalability`: Scalability tests

### 2. Pipeline Performance (`test_pipeline_performance.py`)

Tests the data pipeline's processing performance.

**Requirements**:
- Processing latency < 10ms (P99)
- Throughput > 1M records/second

**Test Classes**:
- `TestPipelineLatency`: Latency measurements
- `TestPipelineThroughput`: Throughput measurements
- `TestPipelineScalability`: Scalability tests

### 3. SPSC Queue Performance (`test_spsc_performance.py`)

Tests the lock-free SPSC queue's performance.

**Requirements**:
- Read/Write latency < 100μs (P99)
- Throughput > 10M operations/second

**Test Classes**:
- `TestSPSCLatency`: Latency measurements
- `TestSPSCThroughput`: Throughput measurements
- `TestSPSCScalability`: Scalability tests

### 4. Sanitizer Performance (`test_sanitizer_performance.py`)

Tests the data sanitizer's cleaning performance.

**Requirements**:
- Cleaning latency < 50ms (P99) for 1000 records
- Throughput > 20K records/second

**Test Classes**:
- `TestSanitizerLatency`: Latency measurements
- `TestSanitizerThroughput`: Throughput measurements
- `TestSanitizerScalability`: Scalability tests
- `TestSanitizerLayerPerformance`: Per-layer performance

## Running Tests

### Run All Performance Tests
```bash
pytest tests/performance/ -v
```

### Run Specific Module
```bash
pytest tests/performance/test_scheduler_performance.py -v
```

### Run Specific Test Class
```bash
pytest tests/performance/test_scheduler_performance.py::TestSchedulerLatency -v
```

### Run Specific Test
```bash
pytest tests/performance/test_scheduler_performance.py::TestSchedulerLatency::test_single_task_latency -v
```

## Performance Reports

After running tests, individual performance reports are generated:

- `performance_report_scheduler.txt`
- `performance_report_pipeline.txt`
- `performance_report_spsc.txt`
- `performance_report_sanitizer.txt`

### Generate Comprehensive Report

Use the performance report generator script:

```bash
python scripts/generate_performance_report.py
```

This generates a comprehensive markdown report in `performance_reports/`.

## Metrics Collected

### Latency Metrics
- P50 (median)
- P95 (95th percentile)
- P99 (99th percentile)
- Mean
- Standard deviation
- Min/Max

### Throughput Metrics
- Mean throughput
- Standard deviation
- Min/Max throughput

### Memory Metrics
- Mean usage
- Peak usage
- Standard deviation

## Performance Requirements

All requirements are defined in the whitepaper (白皮书):

| Component | Metric | Requirement | Whitepaper Reference |
|-----------|--------|-------------|---------------------|
| Chronos Scheduler | Latency (P99) | < 1ms | 第一章 1.1 |
| Chronos Scheduler | Throughput | > 1000 tasks/s | 第一章 1.1 |
| Data Pipeline | Latency (P99) | < 10ms | 第三章 3.1 |
| Data Pipeline | Throughput | > 1M records/s | 第三章 3.1 |
| SPSC Queue | Latency (P99) | < 100μs | 第三章 3.2 |
| SPSC Queue | Throughput | > 10M ops/s | 第三章 3.2 |
| Data Sanitizer | Latency (P99) | < 50ms (1K records) | 第三章 3.3 |
| Data Sanitizer | Throughput | > 20K records/s | 第三章 3.3 |

## Interpreting Results

### Latency

- **P99 < Requirement**: ✅ Pass
- **P99 >= Requirement**: ❌ Fail - Optimization needed

### Throughput

- **Mean > Requirement**: ✅ Pass
- **Mean < Requirement**: ❌ Fail - Optimization needed

### Stability

- **Std < 10% of Mean**: ✅ Stable
- **Std >= 10% of Mean**: ⚠️ Unstable - Investigate variance

## Troubleshooting

### High Latency

**Possible Causes**:
- Lock contention
- Excessive memory allocation
- System load
- I/O operations in hot path

**Solutions**:
- Use lock-free data structures
- Pre-allocate memory
- Run tests on idle system
- Optimize I/O operations

### Low Throughput

**Possible Causes**:
- Small batch sizes
- Sequential processing
- Memory copying
- Inefficient algorithms

**Solutions**:
- Increase batch sizes
- Use parallel processing
- Implement zero-copy techniques
- Optimize algorithms

### High Variance

**Possible Causes**:
- GC pauses
- OS scheduling
- Cache misses
- Resource contention

**Solutions**:
- Tune GC settings
- Use real-time scheduling
- Improve cache locality
- Reduce resource sharing

## Best Practices

1. **Run on Idle System**: Minimize background processes
2. **Multiple Runs**: Run tests multiple times for statistical significance
3. **Warm-up**: Include warm-up iterations to stabilize caches
4. **Consistent Environment**: Use same hardware/OS for comparisons
5. **Monitor System**: Check CPU, memory, I/O during tests

## Contributing

When adding new performance tests:

1. Follow existing test structure
2. Use `PerformanceMetrics` class for consistency
3. Include whitepaper references
4. Document requirements clearly
5. Add to comprehensive report generator

## References

- Whitepaper: `00_核心文档/mia.md`
- Performance Baseline Report: `docs/performance_baseline_report.md`
- Task Checklist: `.kiro/specs/mia-system/tasks.md`
