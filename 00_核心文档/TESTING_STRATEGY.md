# MIA系统测试策略 (Testing Strategy)

**版本**: v1.0  
**日期**: 2026-01-16  
**目的**: 定义全面的测试策略，确保系统质量

---

## 📋 目录

1. [测试金字塔](#测试金字塔)
2. [测试类型](#测试类型)
3. [测试覆盖率要求](#测试覆盖率要求)
4. [测试框架与工具](#测试框架与工具)
5. [测试最佳实践](#测试最佳实践)
6. [CI/CD集成](#cicd集成)

---

## 🔺 测试金字塔

```
        /\
       /  \  E2E测试 (5%)
      /    \  - 全流程测试
     /------\  - 用户场景测试
    /        \
   / 集成测试 \ (20%)
  /  - 模块间  \
 /   - API集成  \
/----------------\
/   单元测试 (75%) \
/  - 函数级        \
/ - 类级           \
/------------------\
```

### 测试分布

- **单元测试**: 75% - 快速、隔离、大量
- **集成测试**: 20% - 模块间交互
- **E2E测试**: 5% - 关键用户流程

---

## 🧪 测试类型

### 1. 单元测试 (Unit Tests)

**目的**: 测试单个函数或类的行为

**覆盖率目标**: ≥ 85%

**示例**:

```python
# tests/unit/evolution/test_genetic_miner.py
import pytest
from evolution.genetic_miner import GeneticMiner

class TestGeneticMiner:
    @pytest.fixture
    def miner(self):
        """测试夹具：创建GeneticMiner实例"""
        return GeneticMiner(population_size=10)
    
    def test_initialize_population(self, miner):
        """测试种群初始化"""
        miner.initialize_population()
        
        # 断言
        assert len(miner.population) == 10
        assert all(hasattr(ind, 'fitness') for ind in miner.population)
    
    def test_evolve_improves_fitness(self, miner):
        """测试进化提升适应度"""
        miner.initialize_population()
        initial_best = max(ind.fitness for ind in miner.population)
        
        miner.evolve(generations=5)
        
        final_best = max(ind.fitness for ind in miner.population)
        assert final_best >= initial_best
    
    def test_empty_population_raises_error(self, miner):
        """测试空种群抛出异常"""
        with pytest.raises(ValueError, match="种群未初始化"):
            miner.evolve(generations=1)
    
    @pytest.mark.parametrize("population_size", [10, 50, 100])
    def test_different_population_sizes(self, population_size):
        """测试不同种群大小"""
        miner = GeneticMiner(population_size=population_size)
        miner.initialize_population()
        assert len(miner.population) == population_size
```

**测试内容**:
- ✅ 正常路径（Happy Path）
- ✅ 边界条件（Boundary Conditions）
- ✅ 异常处理（Exception Handling）
- ✅ 参数化测试（Parametrized Tests）

### 2. 集成测试 (Integration Tests)

**目的**: 测试模块间交互

**覆盖率目标**: ≥ 75%

**示例**:

```python
# tests/integration/chapter_4/test_evolution_pipeline.py
import pytest
from evolution.genetic_miner import GeneticMiner
from evolution.arena import Arena
from brain.devil import Devil

class TestEvolutionPipeline:
    def test_full_evolution_pipeline(self):
        """测试完整进化流程"""
        # 1. 遗传算法生成因子
        miner = GeneticMiner(population_size=10)
        miner.initialize_population()
        miner.evolve(generations=3)
        best_individual = miner.population[0]
        
        # 2. Arena测试
        arena = Arena()
        reality_result = arena.reality_track(best_individual)
        hell_result = arena.hell_track(best_individual)
        
        # 3. Devil审计
        devil = Devil()
        audit_result = devil.audit_strategy(best_individual)
        
        # 断言
        assert reality_result['passed']
        assert hell_result['passed']
        assert audit_result['passed']
    
    def test_soldier_commander_integration(self):
        """测试Soldier和Commander集成"""
        from brain.soldier import Soldier
        from brain.commander import Commander
        
        soldier = Soldier()
        commander = Commander()
        
        # Soldier快速决策
        quick_decision = soldier.make_decision(context)
        
        # Commander战略分析
        strategy = commander.analyze_strategy(context)
        
        # 断言
        assert quick_decision['action'] in ['BUY', 'SELL', 'HOLD']
        assert strategy['recommendation'] is not None
```

**测试内容**:
- ✅ 模块间数据流
- ✅ API集成
- ✅ 数据库集成
- ✅ 外部服务集成（Mock）

### 3. E2E测试 (End-to-End Tests)

**目的**: 测试完整用户场景

**覆盖率目标**: 关键流程100%

**示例**:

```python
# tests/e2e/test_full_workflow.py
import pytest
from datetime import datetime

class TestFullWorkflow:
    def test_complete_trading_day(self):
        """测试完整交易日流程"""
        # 1. 战备态：系统启动
        orchestrator = MainOrchestrator()
        orchestrator.transition_to_state(State.PREP_TIME)
        assert orchestrator.current_state == State.PREP_TIME
        
        # 2. 战争态：交易执行
        orchestrator.transition_to_state(State.WAR_TIME)
        
        # 模拟交易信号
        signal = {
            'symbol': '000001.SZ',
            'action': 'BUY',
            'quantity': 100
        }
        
        # 执行交易
        execution_result = orchestrator.execute_trade(signal)
        assert execution_result['status'] == 'SUCCESS'
        
        # 3. 诊疗态：持仓诊断
        orchestrator.transition_to_state(State.TACTICAL_TIME)
        diagnosis = orchestrator.diagnose_portfolio()
        assert diagnosis is not None
        
        # 4. 进化态：策略进化
        orchestrator.transition_to_state(State.EVOLUTION_TIME)
        evolution_result = orchestrator.run_evolution()
        assert evolution_result['new_strategies'] > 0
    
    def test_hot_failover_scenario(self):
        """测试热备切换场景"""
        soldier = Soldier()
        
        # 正常模式：本地推理
        decision1 = soldier.make_decision(context)
        assert soldier.current_mode == 'LOCAL'
        
        # 模拟本地模型故障
        soldier.simulate_local_failure()
        
        # 自动切换到云端
        decision2 = soldier.make_decision(context)
        assert soldier.current_mode == 'CLOUD'
        
        # 本地恢复
        soldier.simulate_local_recovery()
        
        # 切换回本地
        decision3 = soldier.make_decision(context)
        assert soldier.current_mode == 'LOCAL'
```

**测试内容**:
- ✅ 完整交易日流程
- ✅ 热备切换场景
- ✅ 数据探针自适应
- ✅ 进化流程

### 4. 性能测试 (Performance Tests)

**目的**: 验证性能指标

**示例**:

```python
# tests/performance/test_latency.py
import pytest
import time
from brain.soldier import Soldier

class TestPerformance:
    def test_soldier_local_latency(self):
        """测试Soldier本地推理延迟"""
        soldier = Soldier(mode='LOCAL')
        context = create_test_context()
        
        latencies = []
        for _ in range(100):
            start = time.perf_counter()
            decision = soldier.make_decision(context)
            elapsed = time.perf_counter() - start
            latencies.append(elapsed)
        
        # 性能断言
        p50 = sorted(latencies)[50]
        p95 = sorted(latencies)[95]
        p99 = sorted(latencies)[99]
        
        assert p50 < 0.010  # P50 < 10ms
        assert p95 < 0.015  # P95 < 15ms
        assert p99 < 0.020  # P99 < 20ms
    
    def test_spsc_queue_latency(self):
        """测试SPSC队列延迟"""
        from infra.spsc_queue import SPSCQueue
        
        queue = SPSCQueue(size=1024)
        
        latencies = []
        for i in range(1000):
            data = {'tick': i, 'price': 10.0 + i * 0.01}
            
            start = time.perf_counter()
            queue.write(data)
            read_data = queue.read()
            elapsed = time.perf_counter() - start
            
            latencies.append(elapsed)
        
        # 性能断言
        avg_latency = sum(latencies) / len(latencies)
        assert avg_latency < 0.0001  # 平均延迟 < 100μs
```

**测试内容**:
- ✅ 延迟测试（P50, P95, P99）
- ✅ 吞吐量测试
- ✅ 资源使用测试
- ✅ 压力测试

### 5. 安全测试 (Security Tests)

**目的**: 验证安全机制

**示例**:

```python
# tests/security/test_encryption.py
import pytest
from config.secure_config import SecureConfig

class TestSecurity:
    def test_api_key_encryption(self):
        """测试API密钥加密"""
        config = SecureConfig()
        
        # 原始密钥
        original_key = "sk-1234567890abcdef"
        
        # 加密
        encrypted = config.encrypt_api_key(original_key)
        assert encrypted != original_key
        
        # 解密
        decrypted = config.decrypt_api_key(encrypted)
        assert decrypted == original_key
    
    def test_jwt_token_validation(self):
        """测试JWT令牌验证"""
        from interface.auth import AuthManager
        
        auth = AuthManager()
        
        # 创建令牌
        token = auth.create_access_token(user_id='test_user', role='admin')
        
        # 验证令牌
        payload = auth.verify_token(token)
        assert payload['user_id'] == 'test_user'
        assert payload['role'] == 'admin'
    
    def test_expired_token_rejection(self):
        """测试过期令牌拒绝"""
        from interface.auth import AuthManager
        import time
        
        auth = AuthManager()
        auth.access_token_expire_hours = 0.0001  # 极短过期时间
        
        token = auth.create_access_token(user_id='test_user')
        time.sleep(1)  # 等待过期
        
        with pytest.raises(HTTPException, match="Token expired"):
            auth.verify_token(token)
```

**测试内容**:
- ✅ 加密/解密正确性
- ✅ JWT令牌验证
- ✅ 权限控制
- ✅ 注入攻击防护

---

## 📊 测试覆盖率要求

### 总体目标

```
单元测试覆盖率: ≥ 85%
集成测试覆盖率: ≥ 75%
E2E测试覆盖率: 关键流程100%
```

### 分章节要求

| 章节 | 单元测试 | 集成测试 | E2E测试 |
|------|---------|---------|---------|
| 第一章 | ≥ 90% | ≥ 80% | 100% |
| 第二章 | ≥ 85% | ≥ 75% | 100% |
| 第三章 | ≥ 90% | ≥ 80% | 100% |
| 第四章 | ≥ 85% | ≥ 75% | 100% |
| 第五章 | ≥ 85% | ≥ 75% | - |
| 第六章 | ≥ 85% | ≥ 75% | 100% |
| 第七章 | ≥ 85% | ≥ 75% | 100% |

### 关键模块要求

```
GeneticMiner: 90%
Arena: 90%
Soldier/Commander/Devil: 85%
DataProbe: 90%
Auditor: 90%
SecureConfig: 90%
```

---

## 🛠️ 测试框架与工具

### 核心框架

```python
# pytest - 测试框架
pip install pytest pytest-cov pytest-mock pytest-asyncio

# coverage - 覆盖率统计
pip install coverage

# hypothesis - 属性测试
pip install hypothesis

# faker - 测试数据生成
pip install faker
```

### Mock工具

```python
# unittest.mock - 标准库Mock
from unittest.mock import Mock, patch, MagicMock

# pytest-mock - pytest集成
@pytest.fixture
def mock_api(mocker):
    return mocker.patch('brain.soldier.call_deepseek_api')
```

### 性能测试

```python
# pytest-benchmark - 性能基准测试
pip install pytest-benchmark

def test_performance(benchmark):
    result = benchmark(function_to_test, arg1, arg2)
    assert result is not None
```

---

## 💡 测试最佳实践

### 1. 测试命名规范

```python
# 格式: test_<功能>_<场景>_<预期结果>

def test_genetic_miner_evolve_improves_fitness():
    """测试遗传算法进化提升适应度"""
    pass

def test_soldier_local_failure_switches_to_cloud():
    """测试Soldier本地故障切换到云端"""
    pass

def test_data_probe_invalid_symbol_raises_error():
    """测试数据探针无效标的抛出异常"""
    pass
```

### 2. 使用测试夹具 (Fixtures)

```python
@pytest.fixture
def sample_data():
    """提供测试数据"""
    return pd.DataFrame({
        'date': pd.date_range('2024-01-01', periods=100),
        'close': np.random.rand(100) * 100
    })

@pytest.fixture
def mock_redis(mocker):
    """Mock Redis客户端"""
    return mocker.patch('redis.Redis')

def test_with_fixtures(sample_data, mock_redis):
    """使用夹具的测试"""
    assert len(sample_data) == 100
    mock_redis.return_value.get.return_value = b'test_value'
```

### 3. 参数化测试

```python
@pytest.mark.parametrize("input,expected", [
    (10, 20),
    (20, 40),
    (30, 60),
])
def test_double(input, expected):
    """参数化测试"""
    assert double(input) == expected
```

### 4. Mock外部依赖

```python
# Mock LLM API调用
@patch('brain.soldier.call_deepseek_api')
def test_soldier_decision(mock_api):
    mock_api.return_value = {
        'action': 'BUY',
        'confidence': 0.85
    }
    
    soldier = Soldier()
    decision = soldier.make_decision(context)
    
    assert decision['action'] == 'BUY'
    assert decision['confidence'] == 0.85
    mock_api.assert_called_once()

# Mock 数据库
@patch('redis.Redis')
def test_cache_read(mock_redis):
    mock_redis.return_value.get.return_value = b'cached_value'
    
    result = read_from_cache('key')
    
    assert result == 'cached_value'
```

### 5. 异步测试

```python
@pytest.mark.asyncio
async def test_async_function():
    """测试异步函数"""
    result = await async_function()
    assert result is not None
```

### 6. 测试隔离

```python
# 每个测试独立，不依赖其他测试
class TestGeneticMiner:
    def setup_method(self):
        """每个测试前执行"""
        self.miner = GeneticMiner(population_size=10)
    
    def teardown_method(self):
        """每个测试后执行"""
        self.miner = None
    
    def test_1(self):
        """测试1"""
        pass
    
    def test_2(self):
        """测试2"""
        pass
```

---

## 🚀 CI/CD集成

### GitHub Actions配置

```yaml
# .github/workflows/test.yml
name: MIA Test Suite

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main, develop ]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v2
      
      - name: 设置Python环境
        uses: actions/setup-python@v2
        with:
          python-version: '3.10'
      
      - name: 安装依赖
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-cov pytest-mock
      
      - name: 运行单元测试
        run: |
          pytest tests/unit --cov=src --cov-report=xml --cov-report=term
      
      - name: 检查覆盖率
        run: |
          coverage report --fail-under=85
      
      - name: 运行集成测试
        run: |
          pytest tests/integration --cov=src --cov-append
      
      - name: 运行E2E测试
        run: |
          pytest tests/e2e
      
      - name: 上传覆盖率报告
        uses: codecov/codecov-action@v2
        with:
          files: ./coverage.xml
          flags: unittests
          name: codecov-umbrella
```

### 本地测试脚本

```bash
#!/bin/bash
# scripts/run_tests.sh

echo "运行单元测试..."
pytest tests/unit --cov=src --cov-report=html --cov-report=term

echo "运行集成测试..."
pytest tests/integration --cov=src --cov-append

echo "运行E2E测试..."
pytest tests/e2e

echo "生成覆盖率报告..."
coverage report

echo "检查覆盖率..."
coverage report --fail-under=85

echo "测试完成！"
```

---

## 📈 测试报告

### 覆盖率报告

```bash
# 生成HTML报告
pytest --cov=src --cov-report=html

# 查看报告
open htmlcov/index.html
```

### 性能报告

```bash
# 生成性能基准报告
pytest tests/performance --benchmark-only --benchmark-save=baseline

# 对比性能
pytest tests/performance --benchmark-only --benchmark-compare=baseline
```

---

## ✅ 测试检查清单

### 代码提交前

- [ ] 所有单元测试通过
- [ ] 单元测试覆盖率 ≥ 85%
- [ ] 所有集成测试通过
- [ ] 集成测试覆盖率 ≥ 75%
- [ ] 关键E2E测试通过
- [ ] 性能测试通过
- [ ] 安全测试通过
- [ ] 无测试警告

### 代码审查时

- [ ] 测试用例完整
- [ ] 测试覆盖边界条件
- [ ] 测试覆盖异常处理
- [ ] Mock外部依赖
- [ ] 测试命名规范
- [ ] 测试隔离性

---

**记住**: 测试不是负担，而是质量的保证！
