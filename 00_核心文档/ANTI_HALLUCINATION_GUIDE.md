# MIA系统防幻觉指南 (Anti-Hallucination Guide)

**版本**: v1.0  
**日期**: 2026-01-16  
**目的**: 防止LLM在开发过程中产生幻觉，确保严格遵循白皮书要求

---

## 🚨 什么是LLM幻觉？

LLM幻觉是指AI在生成代码或文档时，**编造不存在的功能、API或架构设计**，而这些内容并未在白皮书中定义。

### 常见幻觉类型

1. **架构幻觉**: 发明不存在的模块或组件
2. **API幻觉**: 调用不存在的函数或方法
3. **参数幻觉**: 使用未定义的配置参数
4. **流程幻觉**: 创造不存在的工作流程
5. **性能幻觉**: 声称未经验证的性能指标

---

## ✅ 防幻觉原则

### 原则1: 白皮书至上 (Whitepaper First)

**规则**: 所有实现必须在白皮书中有明确定义

```python
# ❌ 错误: 发明不存在的模块
from brain.super_analyzer import SuperAnalyzer  # 白皮书中不存在

# ✅ 正确: 使用白皮书定义的模块
from brain.soldier import Soldier  # 白皮书第二章明确定义
```

**检查方法**:
1. 在实现前，先在`mia.md`中搜索相关章节
2. 确认模块名称、类名、函数名与白皮书一致
3. 如有疑问，查阅`ARCHITECTURE_DECISIONS.md`

### 原则2: 显式优于隐式 (Explicit over Implicit)

**规则**: 不要假设任何未明确说明的行为

```python
# ❌ 错误: 假设存在自动重试机制
data = download_data(symbol)  # 假设会自动重试

# ✅ 正确: 显式实现重试逻辑
for attempt in range(3):
    try:
        data = download_data(symbol)
        break
    except Exception as e:
        if attempt == 2:
            raise
        time.sleep(2 ** attempt)
```

### 原则3: 验证优于信任 (Verify over Trust)

**规则**: 所有假设必须通过测试验证

```python
# ❌ 错误: 假设函数存在
result = some_function()  # 未验证是否存在

# ✅ 正确: 先验证再使用
if hasattr(module, 'some_function'):
    result = module.some_function()
else:
    raise NotImplementedError("some_function not found")
```

### 原则4: 文档优于记忆 (Document over Memory)

**规则**: 不要依赖记忆，始终查阅文档

```python
# ❌ 错误: 凭记忆使用API
api_key = config.get_key("DEEPSEEK")  # 记忆中的API

# ✅ 正确: 查阅文档后使用
# 根据ARCHITECTURE_DECISIONS.md ADR-009
from config.secure_config import SecureConfig
api_key = SecureConfig().get_api_key("DEEPSEEK_API_KEY")
```

---

## 🔍 幻觉检测清单

### 在编写代码前

- [ ] 我是否在`mia.md`中找到了这个功能的定义？
- [ ] 模块名称、类名、函数名是否与白皮书一致？
- [ ] 参数名称和类型是否与白皮书一致？
- [ ] 工作流程是否与白皮书描述一致？
- [ ] 性能指标是否在白皮书中有明确要求？

### 在编写代码后

- [ ] 我是否发明了新的模块或组件？
- [ ] 我是否调用了未定义的函数？
- [ ] 我是否使用了未定义的配置参数？
- [ ] 我是否创造了新的工作流程？
- [ ] 我是否声称了未经验证的性能？

### 在提交代码前

- [ ] 所有导入的模块是否在白皮书中定义？
- [ ] 所有调用的函数是否已实现？
- [ ] 所有配置参数是否在白皮书中定义？
- [ ] 所有测试用例是否通过？
- [ ] 代码审查是否通过？

---

## 📚 白皮书索引

### 快速查找表

| 功能 | 白皮书章节 | 关键类/函数 |
|------|-----------|------------|
| 五态调度 | 第一章 1.0-1.4 | main_orchestrator.py |
| Soldier | 第二章 2.1 | Soldier, call_deepseek_api |
| Commander | 第二章 2.2 | Commander, Qwen3-Next-80B |
| Algo Hunter | 第二章 2.3 | AlgoHunter, 1D-CNN/TST |
| Devil | 第二章 2.4 | Devil, DeepSeek-R1 |
| Scholar | 第二章 2.7 | Scholar, Auto-Scraper |
| SPSC队列 | 第三章 3.2 | SPSC Ring Buffer |
| 数据清洗 | 第三章 3.3 | DataSanitizer, 8层清洗 |
| 数据探针 | 第三章 3.3.1 | DataProbe, 自适应工作流 |
| 遗传算法 | 第四章 4.1 | GeneticMiner, evolve |
| Arena | 第四章 4.2 | Arena, Reality/Hell Track |
| Z2H胶囊 | 第四章 4.3 | Z2H Gene Capsule |
| 元进化 | 第四章 4.5 | MetaEvolution |
| 提示词进化 | 第四章 4.6 | PromptEvolutionEngine |
| 策略分析 | 第五章 5.1-5.2 | StrategyAnalyzer, 16个分析器 |
| 主力资金 | 第五章 5.2.8 | SmartMoneyAnalyzer |
| 个股建议 | 第五章 5.2.9 | RecommendationEngine |
| 加密存储 | 第七章 6.1.1 | SecureConfig, Fernet |
| JWT认证 | 第七章 6.1.2 | AuthManager, JWT |
| 审计进程 | 第七章 6.2.1 | Auditor, Shadow Ledger |

### 搜索技巧

```bash
# 在mia.md中搜索关键词
grep -n "GeneticMiner" 00_核心文档/mia.md

# 搜索特定章节
grep -A 20 "第四章" 00_核心文档/mia.md

# 搜索类定义
grep -n "class.*:" 00_核心文档/mia.md
```

---

## 🛡️ 常见幻觉案例

### 案例1: 发明不存在的模块

```python
# ❌ 幻觉代码
from brain.advanced_predictor import AdvancedPredictor

predictor = AdvancedPredictor()
prediction = predictor.predict(data)
```

**问题**: `AdvancedPredictor`在白皮书中不存在

**修正**:
1. 查阅白皮书第二章，确认AI三脑的定义
2. 使用白皮书定义的`Soldier`或`Commander`

```python
# ✅ 正确代码
from brain.soldier import Soldier

soldier = Soldier()
decision = soldier.make_decision(context)
```

### 案例2: 调用不存在的API

```python
# ❌ 幻觉代码
data = api.get_realtime_data(symbol, interval='1s')
```

**问题**: 白皮书中未定义`get_realtime_data`函数

**修正**:
1. 查阅白皮书第三章数据接口定义
2. 使用白皮书定义的数据探针机制

```python
# ✅ 正确代码
from infra.data_probe import DataProbe

probe = DataProbe()
data = probe.download_data(symbol, source='guojin')
```

### 案例3: 使用未定义的配置

```python
# ❌ 幻觉代码
max_threads = config.get('MAX_THREADS', 16)
```

**问题**: 白皮书中未定义`MAX_THREADS`配置

**修正**:
1. 查阅白皮书第一章资源调度
2. 确认是否需要多线程，或使用白皮书定义的进程模型

```python
# ✅ 正确代码
# 白皮书使用多进程模型，不是多线程
from multiprocessing import Process

process = Process(target=worker_func)
process.start()
```

### 案例4: 创造不存在的流程

```python
# ❌ 幻觉代码
def auto_optimize_strategy():
    """自动优化策略（幻觉流程）"""
    analyze_performance()
    adjust_parameters()
    validate_results()
    deploy_to_production()
```

**问题**: 白皮书中未定义这个自动优化流程

**修正**:
1. 查阅白皮书第四章进化流程
2. 使用白皮书定义的元进化机制

```python
# ✅ 正确代码
from evolution.meta_evolution import MetaEvolution

meta_evolution = MetaEvolution()
meta_evolution.initialize_meta_population()
meta_evolution.evolve_meta_population(generations=10)
champion = meta_evolution.sparta_arena_tournament()
```

### 案例5: 声称未验证的性能

```python
# ❌ 幻觉代码
def ultra_fast_compute(data):
    """超快计算，延迟<1μs（未验证）"""
    return np.mean(data)
```

**问题**: 声称的性能指标未经验证

**修正**:
1. 查阅白皮书性能要求
2. 编写性能测试验证

```python
# ✅ 正确代码
def compute_mean(data):
    """
    计算均值
    
    性能: 根据白皮书第三章要求，延迟<100μs
    测试: tests/unit/test_compute_mean.py
    """
    return np.mean(data)

# 性能测试
def test_compute_mean_performance():
    data = np.random.rand(1000)
    start = time.perf_counter()
    result = compute_mean(data)
    elapsed = time.perf_counter() - start
    assert elapsed < 0.0001  # 100μs
```

---

## 🔧 防幻觉工具

### 1. 代码审查脚本

```python
# scripts/check_hallucination.py
import ast
import re

def check_imports(file_path):
    """检查导入的模块是否在白皮书中定义"""
    with open(file_path, 'r') as f:
        tree = ast.parse(f.read())
    
    whitelist = [
        'brain.soldier', 'brain.commander', 'brain.devil',
        'evolution.genetic_miner', 'evolution.meta_evolution',
        'infra.data_probe', 'infra.sanitizer',
        # ... 更多白皮书定义的模块
    ]
    
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name not in whitelist:
                    print(f"⚠️ 可能的幻觉导入: {alias.name}")
        elif isinstance(node, ast.ImportFrom):
            if node.module not in whitelist:
                print(f"⚠️ 可能的幻觉导入: {node.module}")

if __name__ == '__main__':
    import sys
    check_imports(sys.argv[1])
```

### 2. 白皮书验证器

```python
# scripts/validate_against_whitepaper.py
def validate_class_name(class_name):
    """验证类名是否在白皮书中定义"""
    whitepaper_classes = [
        'Soldier', 'Commander', 'Devil', 'Scholar',
        'GeneticMiner', 'MetaEvolution', 'Arena',
        'StrategyAnalyzer', 'DataProbe', 'Auditor',
        # ... 更多白皮书定义的类
    ]
    
    if class_name not in whitepaper_classes:
        print(f"⚠️ 类名 '{class_name}' 未在白皮书中定义")
        return False
    return True

def validate_function_name(function_name):
    """验证函数名是否在白皮书中定义"""
    # 实现类似逻辑
    pass
```

### 3. 自动化检查

```bash
# .github/workflows/anti_hallucination.yml
name: Anti-Hallucination Check

on: [push, pull_request]

jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: 检查幻觉导入
        run: |
          python scripts/check_hallucination.py src/**/*.py
      - name: 验证白皮书一致性
        run: |
          python scripts/validate_against_whitepaper.py
```

---

## 📖 最佳实践

### 1. 开发前阅读

```
1. 阅读白皮书相关章节
2. 查阅架构决策记录
3. 查看实现检查清单
4. 确认功能定义明确
```

### 2. 开发中验证

```
1. 每写一个类，检查白皮书定义
2. 每写一个函数，检查白皮书定义
3. 每使用一个配置，检查白皮书定义
4. 每声称一个性能，编写测试验证
```

### 3. 开发后审查

```
1. 运行幻觉检查脚本
2. 代码审查（人工或AI）
3. 测试覆盖率检查
4. 白皮书一致性验证
```

---

## 🎯 检查清单

### 代码提交前

- [ ] 所有导入的模块在白皮书中有定义
- [ ] 所有类名在白皮书中有定义
- [ ] 所有函数名在白皮书中有定义
- [ ] 所有配置参数在白皮书中有定义
- [ ] 所有性能声称有测试验证
- [ ] 运行了幻觉检查脚本
- [ ] 通过了代码审查

### 代码审查时

- [ ] 检查是否有发明的模块
- [ ] 检查是否有发明的API
- [ ] 检查是否有发明的配置
- [ ] 检查是否有发明的流程
- [ ] 检查是否有未验证的性能声称

---

## 🚀 总结

**记住三个关键问题**:

1. **这个功能在白皮书中有定义吗？**
2. **这个API在白皮书中有定义吗？**
3. **这个性能指标经过验证了吗？**

**如果答案是"不确定"，那就是幻觉的信号！**

---

**原则**: 宁可多查一次白皮书，也不要凭记忆编码！
