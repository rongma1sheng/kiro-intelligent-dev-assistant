# MIA系统开发指南 (Development Guide)

**版本**: v1.0  
**日期**: 2026-01-16  
**状态**: 工业级开发标准  
**目标**: 确保LLM编码过程可控，防止偏离白皮书要求

---

## 📋 目录

1. [开发原则](#开发原则)
2. [架构约束](#架构约束)
3. [编码规范](#编码规范)
4. [测试要求](#测试要求)
5. [质量门禁](#质量门禁)
6. [开发流程](#开发流程)
7. [常见陷阱](#常见陷阱)

---

## 🎯 开发原则

### 核心原则 (CRITICAL)

1. **白皮书至上**: 所有实现必须严格遵循 `mia.md` 白皮书规范
2. **工业级标准**: 代码质量达到生产环境要求
3. **测试驱动**: 测试覆盖率 ≥ 85%
4. **性能优先**: 关键路径延迟 < 20ms
5. **安全第一**: 零信任架构，加密存储敏感信息

### 禁止事项 (FORBIDDEN)

❌ **严禁偏离白皮书架构**  
❌ **严禁硬编码敏感信息**  
❌ **严禁跳过测试**  
❌ **严禁使用未经审计的第三方库**  
❌ **严禁在C盘写入数据**

---

## 🏗️ 架构约束

### 1. 三位一体架构 (The Trinity)

```
The Body (AMD AI Max)  ← 全能计算节点
The Eye (Client)       ← 纯可视化终端
The Brain (Cloud API)  ← 逻辑外脑
```

**约束**:
- Client端禁止执行计算任务
- 所有AI推理在AMD或Cloud执行
- 热备切换延迟 < 200ms

### 2. 五态生物钟 (Chronos Scheduler)

```
State 0: 维护态 (Manual)
State 1: 战备态 (08:30-09:15)
State 2: 战争态 (09:15-15:00)
State 3: 诊疗态 (15:00-20:00)
State 4: 进化态 (20:00-08:30)
```

**约束**:
- 严格按时间切换状态
- 战争态禁止重型I/O
- 进化态独占GPU资源

### 3. 双盘物理隔离

```
C盘: 只读系统盘 (PYTHONDONTWRITEBYTECODE=1)
D盘: 读写数据盘 (日志/DB/Docker)
```

**约束**:
- 所有数据写入D盘
- C盘仅维护态可写
- 违反触发告警

---

## 💻 编码规范

### 1. 代码质量标准

```python
# ✅ 正确示例
def calculate_sharpe_ratio(returns: pd.Series, risk_free_rate: float = 0.03) -> float:
    """
    计算夏普比率
    
    Args:
        returns: 收益率序列
        risk_free_rate: 无风险利率，默认3%
        
    Returns:
        夏普比率
        
    Raises:
        ValueError: 收益率序列为空
    """
    if returns.empty:
        raise ValueError("收益率序列不能为空")
    
    excess_returns = returns - risk_free_rate / 252
    return excess_returns.mean() / excess_returns.std() * np.sqrt(252)
```

**质量指标**:
- ✅ 圈复杂度 ≤ 10
- ✅ 函数长度 ≤ 50行
- ✅ 类长度 ≤ 300行
- ✅ 代码重复率 < 5%
- ✅ 完整的Docstring
- ✅ 类型注解

### 2. 命名规范

```python
# 模块命名: snake_case
genetic_miner.py
strategy_analyzer.py

# 类命名: PascalCase
class GeneticMiner:
class StrategyAnalyzer:

# 函数/变量: snake_case
def evolve_population():
sharpe_ratio = 1.8

# 常量: UPPER_SNAKE_CASE
MAX_POPULATION_SIZE = 200
DEFAULT_MUTATION_RATE = 0.2

# 私有成员: _leading_underscore
def _internal_method():
self._private_var = 0
```

### 3. 错误处理

```python
# ✅ 正确: 具体异常 + 日志
try:
    data = download_data(symbol)
except ConnectionError as e:
    logger.error(f"下载失败: {symbol}, 错误: {e}")
    raise DataDownloadError(f"无法下载{symbol}数据") from e

# ❌ 错误: 捕获所有异常
try:
    data = download_data(symbol)
except:  # 太宽泛
    pass  # 吞掉异常
```

### 4. 性能优化

```python
# ✅ 正确: 使用NumPy向量化
returns = (prices / prices.shift(1) - 1).values

# ❌ 错误: 使用循环
returns = []
for i in range(1, len(prices)):
    returns.append(prices[i] / prices[i-1] - 1)
```

---

## 🧪 测试要求

### 1. 测试覆盖率目标

```
单元测试: ≥ 85%
集成测试: ≥ 75%
E2E测试: 关键流程100%
```

### 2. 测试结构

```
tests/
├── unit/
│   ├── chapter_1/  # 柯罗诺斯生物钟
│   ├── chapter_2/  # AI三脑
│   ├── chapter_3/  # 基础设施
│   ├── chapter_4/  # 斯巴达进化
│   └── chapter_5/  # LLM策略分析
├── integration/
│   ├── chapter_1/
│   └── ...
└── e2e/
    └── full_workflow_test.py
```

### 3. 测试示例

```python
# tests/unit/chapter_4/test_genetic_miner.py
import pytest
from evolution.genetic_miner import GeneticMiner

class TestGeneticMiner:
    @pytest.fixture
    def miner(self):
        return GeneticMiner(population_size=10)
    
    def test_initialize_population(self, miner):
        """测试种群初始化"""
        miner.initialize_population()
        assert len(miner.population) == 10
        assert all(hasattr(ind, 'fitness') for ind in miner.population)
    
    def test_evolve_convergence(self, miner):
        """测试进化收敛"""
        miner.initialize_population()
        initial_fitness = miner.population[0].fitness
        
        miner.evolve(generations=5)
        
        final_fitness = miner.population[0].fitness
        assert final_fitness >= initial_fitness  # 适应度应提升
    
    def test_empty_population_error(self, miner):
        """测试空种群异常"""
        with pytest.raises(ValueError, match="种群未初始化"):
            miner.evolve(generations=1)
```

### 4. Mock外部依赖

```python
# 测试LLM调用
@patch('brain.soldier.call_deepseek_api')
def test_soldier_decision(mock_api):
    mock_api.return_value = {"action": "BUY", "confidence": 0.85}
    
    soldier = Soldier()
    decision = soldier.make_decision(context)
    
    assert decision['action'] == 'BUY'
    assert decision['confidence'] == 0.85
    mock_api.assert_called_once()
```

---

## 🚦 质量门禁

### 1. 代码提交前检查

```bash
# 运行所有检查
python scripts/pre_commit_check.py

# 包含:
# 1. 代码格式化 (black)
# 2. 类型检查 (mypy)
# 3. 代码质量 (pylint)
# 4. 测试覆盖率 (pytest-cov)
# 5. 安全扫描 (bandit)
```

### 2. CI/CD流程

```yaml
# .github/workflows/ci.yml
name: MIA CI/CD

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: 运行单元测试
        run: pytest tests/unit --cov=. --cov-report=xml
      - name: 检查覆盖率
        run: |
          coverage report --fail-under=85
      - name: 代码质量检查
        run: pylint --fail-under=8.0 src/
```

### 3. 质量门禁标准

```
✅ 测试覆盖率 ≥ 85%
✅ Pylint评分 ≥ 8.0/10
✅ 无高危安全漏洞
✅ 圈复杂度 ≤ 10
✅ 所有测试通过
```

---

## 🔄 开发流程

### 1. 功能开发流程

```
1. 阅读白皮书相关章节
   ↓
2. 创建功能分支 (feature/xxx)
   ↓
3. 编写测试用例 (TDD)
   ↓
4. 实现功能代码
   ↓
5. 运行测试 (pytest)
   ↓
6. 代码审查 (Code Review)
   ↓
7. 合并到主分支
```

### 2. 分支策略

```
main          ← 生产环境
  ↑
develop       ← 开发主分支
  ↑
feature/xxx   ← 功能分支
hotfix/xxx    ← 紧急修复
```

### 3. Commit规范

```bash
# 格式: <type>(<scope>): <subject>

# 示例:
feat(chapter4): 实现遗传算法种群初始化
fix(chapter2): 修复Soldier热备切换延迟
test(chapter5): 添加策略分析器单元测试
docs(guide): 更新开发指南
refactor(infra): 重构数据清洗模块
```

---

## ⚠️ 常见陷阱

### 1. 架构偏离

```python
# ❌ 错误: Client端执行计算
# client/dashboard.py
def calculate_indicators(data):
    # 违反架构: Client应该是纯展示
    return compute_heavy_task(data)

# ✅ 正确: 调用AMD服务端
def get_indicators(symbol):
    response = requests.get(f"http://amd-server:8501/api/indicators/{symbol}")
    return response.json()
```

### 2. 状态混乱

```python
# ❌ 错误: 战争态执行重型I/O
if current_state == State.WAR_TIME:
    # 违反约束: 战争态禁止重型I/O
    df.to_parquet("large_file.parquet")

# ✅ 正确: 延迟到诊疗态
if current_state == State.WAR_TIME:
    # 仅写入内存
    pending_writes.append(df)
elif current_state == State.TACTICAL_TIME:
    # 诊疗态批量写入
    for df in pending_writes:
        df.to_parquet(f"data/{timestamp}.parquet")
```

### 3. 硬编码敏感信息

```python
# ❌ 错误: 硬编码API密钥
DEEPSEEK_API_KEY = "sk-1234567890abcdef"

# ✅ 正确: 加密存储
from config.secure_config import SecureConfig
api_key = SecureConfig().get_api_key("DEEPSEEK_API_KEY")
```

### 4. 测试不足

```python
# ❌ 错误: 仅测试正常路径
def test_download_data():
    data = download_data("000001.SZ")
    assert len(data) > 0

# ✅ 正确: 测试边界和异常
def test_download_data_normal():
    data = download_data("000001.SZ")
    assert len(data) > 0

def test_download_data_invalid_symbol():
    with pytest.raises(ValueError):
        download_data("INVALID")

def test_download_data_network_error():
    with patch('requests.get', side_effect=ConnectionError):
        with pytest.raises(DataDownloadError):
            download_data("000001.SZ")
```

### 5. 性能陷阱

```python
# ❌ 错误: 循环中重复计算
for symbol in symbols:
    market_data = get_market_data()  # 每次都获取
    process(symbol, market_data)

# ✅ 正确: 提前计算
market_data = get_market_data()  # 只获取一次
for symbol in symbols:
    process(symbol, market_data)
```

---

## 📚 参考资源

### 核心文档
- `mia.md` - 系统架构白皮书
- `ARCHITECTURE.md` - 架构决策记录
- `API_REFERENCE.md` - API接口文档

### 开发工具
- Black - 代码格式化
- Pylint - 代码质量检查
- MyPy - 类型检查
- Pytest - 测试框架
- Coverage.py - 覆盖率统计

### 学习资源
- [Python最佳实践](https://docs.python-guide.org/)
- [测试驱动开发](https://testdriven.io/)
- [Clean Code原则](https://github.com/zedr/clean-code-python)

---

## ✅ 检查清单

开发完成前，确认以下事项：

- [ ] 代码符合白皮书架构要求
- [ ] 测试覆盖率 ≥ 85%
- [ ] 所有测试通过
- [ ] Pylint评分 ≥ 8.0
- [ ] 无安全漏洞
- [ ] 完整的Docstring
- [ ] 类型注解完整
- [ ] 错误处理完善
- [ ] 性能满足要求
- [ ] 代码审查通过

---

**记住**: 质量是设计出来的，不是测试出来的。从一开始就按照工业级标准编写代码！
