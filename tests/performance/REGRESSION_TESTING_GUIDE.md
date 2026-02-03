# Performance Regression Testing Guide

**Version**: 1.0  
**Date**: 2026-01-17  
**Task**: 2.9.3 性能回归测试  
**白皮书依据**: 第一章 1.T.3 性能测试要求

---

## Overview

The performance regression testing framework provides automated detection of performance degradation across all MIA system components. It establishes performance baselines, monitors metrics over time, and alerts when performance degrades beyond acceptable thresholds.

### Key Features

- ✅ **Automated Baseline Management**: Establish and update performance baselines
- ✅ **Regression Detection**: Automatically detect performance degradation
- ✅ **Component-Specific Testing**: Test individual components or entire system
- ✅ **Alert System**: Warn when performance degrades > 10%, fail when > 20%
- ✅ **Historical Tracking**: Track performance metrics over time
- ✅ **Detailed Reporting**: Generate comprehensive regression reports

---

## Quick Start

### 1. Establish Baseline (First Time)

Before running regression tests, you must establish a performance baseline:

```bash
# Establish baseline for all components
python scripts/run_regression_tests.py --establish-baseline
```

This will:
- Run all performance tests
- Collect metrics (latency, throughput)
- Save baseline to `tests/performance/performance_baseline.json`
- Generate baseline metadata

### 2. Run Regression Tests

After establishing the baseline, run regression tests:

```bash
# Run all regression tests
python scripts/run_regression_tests.py --test

# Run specific component test
python scripts/run_regression_tests.py --test --component scheduler
python scripts/run_regression_tests.py --test --component pipeline
python scripts/run_regression_tests.py --test --component spsc
python scripts/run_regression_tests.py --test --component sanitizer
```

### 3. Generate Report

Generate a detailed regression test report:

```bash
python scripts/run_regression_tests.py --report
```

Report will be saved to `performance_reports/regression_report_YYYYMMDD_HHMMSS.md`

### 4. Update Baseline

When you make performance improvements or want to reset the baseline:

```bash
# Update baseline (backs up old baseline)
python scripts/run_regression_tests.py --update-baseline
```

---

## Regression Detection Rules

### Warning Threshold (10%)

Performance degradation between 10-20% triggers a **warning**:

- ⚠️ Latency increased by 10-20%
- ⚠️ Throughput decreased by 10-20%

**Action**: Investigate the cause, but test still passes

### Failure Threshold (20%)

Performance degradation > 20% triggers a **failure**:

- ❌ Latency increased by > 20%
- ❌ Throughput decreased by > 20%

**Action**: Test fails, must fix before merging

### Example Output

```
✅ scheduler latency OK (P99: 0.8523 vs 0.8234)
⚠️ pipeline latency degraded by 12.3% (P99: 8.9234 vs 7.9456)
❌ spsc_queue throughput dropped by 25.4% (Mean: 7456.23 vs 10000.00)
```

---

## Components Tested

### 1. Chronos Scheduler

**Metrics**:
- Scheduling latency (P50, P95, P99)
- Task throughput (tasks/second)

**Requirements** (from whitepaper):
- Latency < 1ms (P99)
- Throughput > 1000 tasks/s

**Test File**: `tests/performance/test_scheduler_performance.py`

### 2. Data Pipeline

**Metrics**:
- Processing latency (P50, P95, P99)
- Data throughput (records/second)

**Requirements** (from whitepaper):
- Latency < 10ms (P99)
- Throughput > 1M records/s

**Test File**: `tests/performance/test_pipeline_performance.py`

### 3. SPSC Queue

**Metrics**:
- Read/write latency (P50, P95, P99)
- Operation throughput (ops/second)

**Requirements** (from whitepaper):
- Latency < 100μs (P99)
- Throughput > 10M ops/s

**Test File**: `tests/performance/test_spsc_performance.py`

### 4. Data Sanitizer

**Metrics**:
- Cleaning latency (P50, P95, P99)
- Cleaning throughput (records/second)

**Requirements** (from whitepaper):
- Latency < 50ms (P99) for 1K records
- Throughput > 20K records/s

**Test File**: `tests/performance/test_sanitizer_performance.py`

---

## Baseline Management

### Baseline File Structure

The baseline is stored in `tests/performance/performance_baseline.json`:

```json
{
  "timestamp": "2026-01-17T10:30:00",
  "version": "1.0",
  "metrics": {
    "scheduler": {
      "latency": {
        "p50": 0.5234,
        "p95": 0.7456,
        "p99": 0.8523,
        "mean": 0.5678,
        "std": 0.1234
      },
      "throughput": {
        "mean": 1234.56,
        "std": 45.67,
        "min": 1100.00,
        "max": 1300.00
      }
    },
    "pipeline": { ... },
    "spsc_queue": { ... },
    "sanitizer": { ... }
  }
}
```

### Baseline Metadata

Metadata is stored in `tests/performance/performance_baseline.metadata.json`:

```json
{
  "established_at": "2026-01-17T10:30:00",
  "python_version": "3.11.5",
  "platform": "win32"
}
```

### Baseline Backup

When updating the baseline, the old baseline is automatically backed up:

```
tests/performance/
├── performance_baseline.json                    # Current baseline
├── performance_baseline.backup_20260117_103000.json  # Backup
└── performance_baseline.metadata.json           # Metadata
```

---

## Integration with CI/CD

### GitHub Actions Example

```yaml
name: Performance Regression Tests

on:
  pull_request:
    branches: [ main ]
  schedule:
    - cron: '0 2 * * *'  # Daily at 2 AM

jobs:
  regression-tests:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install -r requirements-dev.txt
    
    - name: Run regression tests
      run: |
        python scripts/run_regression_tests.py --test
    
    - name: Generate report
      if: always()
      run: |
        python scripts/run_regression_tests.py --report
    
    - name: Upload report
      if: always()
      uses: actions/upload-artifact@v3
      with:
        name: regression-report
        path: performance_reports/
```

### Pre-commit Hook

Add to `.git/hooks/pre-commit`:

```bash
#!/bin/bash

echo "Running performance regression tests..."
python scripts/run_regression_tests.py --test

if [ $? -ne 0 ]; then
    echo "❌ Performance regression detected!"
    echo "Run 'python scripts/run_regression_tests.py --report' for details"
    exit 1
fi

echo "✅ Performance regression tests passed"
```

---

## Troubleshooting

### Issue: No baseline found

**Error**:
```
No baseline found, run test_establish_baseline first
```

**Solution**:
```bash
python scripts/run_regression_tests.py --establish-baseline
```

### Issue: Tests timing out

**Error**:
```
Regression tests timed out
```

**Solution**:
- Check system resources (CPU, memory)
- Increase timeout in `scripts/run_regression_tests.py`
- Run component tests individually

### Issue: High variance in results

**Problem**: Test results vary significantly between runs

**Solution**:
- Ensure system is idle during tests
- Close background applications
- Run tests multiple times and average results
- Increase number of test iterations

### Issue: Platform-specific differences

**Problem**: Baseline from one platform doesn't match another

**Solution**:
- Maintain separate baselines per platform
- Use platform-specific baseline files:
  - `performance_baseline_windows.json`
  - `performance_baseline_linux.json`
  - `performance_baseline_macos.json`

---

## Best Practices

### 1. Establish Baseline on Clean System

- Close all unnecessary applications
- Ensure system is idle
- Run multiple times to verify consistency

### 2. Regular Baseline Updates

- Update baseline after major optimizations
- Update baseline when upgrading dependencies
- Keep backup of old baselines for comparison

### 3. Monitor Trends

- Track performance metrics over time
- Look for gradual degradation
- Investigate sudden changes

### 4. Component-Specific Testing

- Test individual components during development
- Run full suite before merging
- Use component tests for faster feedback

### 5. Alert Configuration

- Configure alerts for your team's communication tool
- Set up email notifications for failures
- Create dashboards for performance tracking

---

## Advanced Usage

### Custom Tolerance

Modify tolerance in test code:

```python
# Default: 10% tolerance
passed, warnings = baseline_manager.compare_metrics(
    current_metrics,
    baseline,
    tolerance=0.10
)

# Stricter: 5% tolerance
passed, warnings = baseline_manager.compare_metrics(
    current_metrics,
    baseline,
    tolerance=0.05
)
```

### Multiple Baselines

Maintain baselines for different scenarios:

```python
# Development baseline (relaxed)
baseline_dev = PerformanceBaseline("performance_baseline_dev.json")

# Production baseline (strict)
baseline_prod = PerformanceBaseline("performance_baseline_prod.json")

# CI baseline (moderate)
baseline_ci = PerformanceBaseline("performance_baseline_ci.json")
```

### Historical Tracking

Track performance over time:

```python
# Save metrics with timestamp
metrics_history = []
metrics_history.append({
    "timestamp": datetime.now().isoformat(),
    "metrics": current_metrics
})

# Analyze trends
def analyze_trend(history):
    # Calculate moving average
    # Detect gradual degradation
    # Generate trend report
    pass
```

---

## Performance Monitoring Dashboard

### Metrics to Track

1. **Latency Trends**
   - P99 latency over time
   - Latency distribution changes
   - Outlier detection

2. **Throughput Trends**
   - Average throughput over time
   - Peak throughput changes
   - Throughput variance

3. **Resource Usage**
   - CPU usage during tests
   - Memory usage during tests
   - Disk I/O during tests

4. **Test Execution Time**
   - Total test duration
   - Per-component test duration
   - Test timeout frequency

### Visualization Tools

- **Grafana**: Real-time performance dashboards
- **Prometheus**: Metrics collection and alerting
- **Jupyter Notebooks**: Ad-hoc analysis and visualization

---

## FAQ

### Q: How often should I run regression tests?

**A**: 
- **During development**: Before each commit
- **In CI/CD**: On every pull request
- **Scheduled**: Daily or weekly
- **After changes**: After performance-related changes

### Q: What if my changes intentionally change performance?

**A**: Update the baseline after verifying the changes are correct:

```bash
python scripts/run_regression_tests.py --update-baseline
```

### Q: Can I run regression tests in parallel?

**A**: No, performance tests should run sequentially to avoid interference. Parallel execution can skew results.

### Q: How do I compare performance across different machines?

**A**: Maintain separate baselines per machine or normalize metrics based on machine capabilities.

### Q: What if a test is flaky?

**A**: 
- Increase number of test iterations
- Add warmup runs before measurement
- Check for external interference (background processes)
- Consider using median instead of mean

---

## References

- **Whitepaper**: `00_核心文档/mia.md` - Chapter 1, Section 1.T.3
- **Performance Baseline Report**: `docs/performance_baseline_report.md`
- **Scheduler Optimization Report**: `docs/scheduler_optimization_report.md`
- **Task Checklist**: `.kiro/specs/mia-system/tasks.md` - Task 2.9.3

---

## Support

For issues or questions:
1. Check this guide first
2. Review test logs in `logs/regression_tests.log`
3. Check test output in `performance_reports/`
4. Consult the whitepaper for requirements

---

**Document Version**: 1.0  
**Last Updated**: 2026-01-17  
**Author**: MIA Development Team
