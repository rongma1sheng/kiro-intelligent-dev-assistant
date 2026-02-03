# MIA编码规则使用指南

**版本**: v1.6.0  
**日期**: 2026-01-18  
**目标用户**: LLM开发助手、人类开发者

---

## 📖 概述

MIA系统的编码规则（`.kiro/steering/mia_coding_rules.md`）是一个专门为LLM设计的编码提示词系统，旨在：

1. **防止幻觉**: 确保所有实现严格遵循白皮书定义
2. **保证质量**: 强制执行工业级代码标准
3. **提高效率**: 提供清晰的编码流程和示例
4. **确保一致性**: 统一编码风格和最佳实践

---

## 🚀 快速开始

### 对于Kiro AI（自动加载）

编码规则文件位于 `.kiro/steering/mia_coding_rules.md`，配置为 `inclusion: always`，这意味着：

- ✅ **自动加载**: 每次对话时自动包含在上下文中
- ✅ **最高优先级**: `priority: 1`，优先于其他规则
- ✅ **全局生效**: 适用于所有MIA系统代码编写任务

**你不需要做任何事情，规则会自动生效！**

### 对于其他LLM

如果你使用其他LLM（如ChatGPT、Claude等），请在开始编码前：

1. 阅读白皮书: `00_核心文档/mia.md`
2. 阅读编码规则: `.kiro/steering/mia_coding_rules.md`
3. 在每次编码任务开始时，将编码规则作为系统提示词

---

## 📋 编码流程（7步法）

### 步骤1: 阅读白皮书 📚

**目的**: 确保理解功能定义

**操作**:
```bash
# 打开白皮书
code 00_核心文档/mia.md

# 搜索相关章节
grep -n "GeneticMiner" 00_核心文档/mia.md
```

**检查清单**:
- [ ] 找到相关章节（如第四章 4.1）
- [ ] 阅读功能定义、参数、返回值
- [ ] 记录所有类名、函数名、常量名
- [ ] 确认性能要求

### 步骤2: 检查实现清单 ✅

**目的**: 确认功能范围和验收标准

**操作**:
```bash
# 打开实现检查清单
code 00_核心文档/IMPLEMENTATION_CHECKLIST.md

# 搜索对应检查项
grep -n "GeneticMiner" 00_核心文档/IMPLEMENTATION_CHECKLIST.md
```

**检查清单**:
- [ ] 找到对应的检查项
- [ ] 确认功能范围
- [ ] 确认验收标准
- [ ] 标记为"进行中"

### 步骤3: 编写测试用例 🧪

**目的**: 先写测试，后写代码（TDD）

**操作**:
```bash
# 创建测试文件
mkdir -p tests/unit/chapter_4
touch tests/unit/chapter_4/test_genetic_miner.py
```

**测试模板**:
```python
import pytest
from evolution.genetic_miner import GeneticMiner

class TestGeneticMiner:
    @pytest.fixture
    def miner(self):
        """测试夹具"""
        return GeneticMiner(population_size=10)
    
    def test_initialize_population(self, miner):
        """测试初始化种群"""
        miner.initialize_population()
        assert len(miner.population) == 10
    
    def test_invalid_population_size(self):
        """测试无效种群大小"""
        with pytest.raises(ValueError, match="种群大小必须 > 0"):
            GeneticMiner(population_size=0)
```

**检查清单**:
- [ ] 测试正常情况
- [ ] 测试边界条件
- [ ] 测试异常情况
- [ ] 运行测试（应该失败）

### 步骤4: 实现功能 💻

**目的**: 编写完整的、无占位符的代码

**操作**:
```bash
# 创建源代码文件
mkdir -p src/evolution
touch src/evolution/genetic_miner.py
```

**编码标准**:
```python
"""遗传算法因子挖掘器

白皮书依据: 第四章 4.1 暗物质挖掘工厂
"""

import numpy as np
import pandas as pd
from typing import List, Optional
from loguru import logger


class GeneticMiner:
    """遗传算法因子挖掘器
    
    白皮书依据: 第四章 4.1 暗物质挖掘工厂
    
    Attributes:
        population_size: 种群大小
        mutation_rate: 变异概率
    """
    
    def __init__(self, population_size: int = 50):
        """初始化
        
        Args:
            population_size: 种群大小，必须 > 0
            
        Raises:
            ValueError: 当population_size <= 0时
        """
        if population_size <= 0:
            raise ValueError(f"种群大小必须 > 0，当前: {population_size}")
        
        self.population_size: int = population_size
        self.population: List = []
        
        logger.info(f"初始化GeneticMiner: population_size={population_size}")
```

**检查清单**:
- [ ] 添加完整的docstring（包含白皮书依据）
- [ ] 添加类型注解
- [ ] 实现完整逻辑（不允许占位符）
- [ ] 添加错误处理
- [ ] 添加日志记录

### 步骤5: 运行测试 🧪

**目的**: 验证实现正确性

**操作**:
```bash
# 运行单元测试
pytest tests/unit/chapter_4/test_genetic_miner.py -v

# 检查覆盖率
pytest tests/unit/chapter_4/ --cov=src/evolution --cov-report=term
```

**检查清单**:
- [ ] 所有测试通过
- [ ] 覆盖率 ≥ 85%
- [ ] 无性能回归

### 步骤6: 代码质量检查 🔍

**目的**: 确保代码质量和防止幻觉

**操作**:
```bash
# 运行幻觉检查
python scripts/check_hallucination.py src/evolution/genetic_miner.py

# 运行代码质量检查
python scripts/pre_commit_check.py

# 运行Pylint
pylint src/evolution/genetic_miner.py
```

**检查清单**:
- [ ] 无幻觉（所有类名、函数名在白皮书中有定义）
- [ ] Pylint评分 ≥ 8.0/10
- [ ] 圈复杂度 ≤ 10
- [ ] 无安全漏洞

### 步骤7: 更新检查清单 📝

**目的**: 记录进度

**操作**:
```bash
# 打开检查清单
code 00_核心文档/IMPLEMENTATION_CHECKLIST.md

# 标记完成
# 将 [ ] 改为 [x]
```

**检查清单**:
- [ ] 标记对应检查项为完成 [x]
- [ ] 更新总体进度
- [ ] 提交代码

---

## 🚨 核心铁律（必须遵守）

### 铁律1: 白皮书至上 📖

**规则**: 所有实现必须在白皮书中有明确定义

**检查方法**:
```bash
# 在白皮书中搜索类名
grep -n "GeneticMiner" 00_核心文档/mia.md

# 如果找不到，说明是幻觉！
```

**示例**:
```python
# ❌ 错误: 白皮书中没有定义 AdvancedOptimizer
class AdvancedOptimizer:
    pass

# ✅ 正确: 白皮书第四章明确定义了 GeneticMiner
class GeneticMiner:
    """遗传算法因子挖掘器
    
    白皮书依据: 第四章 4.1 暗物质挖掘工厂
    """
    pass
```

### 铁律2: 禁止简化和占位符 🚫

**规则**: 严禁使用 pass、TODO、NotImplemented、...等占位符

**示例**:
```python
# ❌ 错误
def calculate_sharpe_ratio(returns):
    # TODO: 实现夏普比率计算  # ❌ 错误示例：违反MIA编码铁律2
    pass

# ✅ 正确
def calculate_sharpe_ratio(returns: pd.Series, risk_free_rate: float = 0.03) -> float:
    """计算夏普比率
    
    白皮书依据: 第四章 4.1 因子评估标准
    """
    if returns.empty:
        raise ValueError("收益率序列不能为空")
    
    excess_returns = returns - risk_free_rate / 252
    sharpe = excess_returns.mean() / excess_returns.std() * np.sqrt(252)
    
    return sharpe
```

### 铁律3: 完整的错误处理 ⚠️

**规则**: 所有可能失败的操作必须有错误处理

**示例**:
```python
# ❌ 错误
try:
    data = download_data(symbol)
except:
    pass

# ✅ 正确
try:
    data = download_data(symbol)
except ConnectionError as e:
    logger.error(f"下载失败: {symbol}, 错误: {e}")
    raise DataDownloadError(f"无法下载{symbol}数据") from e
except Timeout as e:
    logger.warning(f"下载超时: {symbol}, 重试中...")
    raise DataDownloadError(f"{symbol}数据下载超时") from e
```

### 铁律4: 完整的类型注解 📝

**规则**: 所有函数参数和返回值必须有类型注解

**示例**:
```python
# ❌ 错误
def process_data(data):
    return data.mean()

# ✅ 正确
from typing import Optional, List, Dict
import pandas as pd

def process_data(
    data: pd.DataFrame,
    columns: Optional[List[str]] = None,
    aggregation: str = 'mean'
) -> Dict[str, float]:
    """处理数据并返回聚合结果"""
    # ... 实现
```

### 铁律5: 完整的文档字符串 📄

**规则**: 所有公共类、函数必须有完整的docstring

**示例**:
```python
# ❌ 错误
def calculate_ic(factor, returns):
    return factor.corr(returns)

# ✅ 正确
def calculate_ic(
    factor: pd.Series,
    returns: pd.Series,
    method: str = 'pearson'
) -> float:
    """计算因子的信息系数(IC)
    
    白皮书依据: 第四章 4.1 因子评估标准 - IC (信息系数)
    
    Args:
        factor: 因子值序列
        returns: 对应的未来收益率序列
        method: 相关系数计算方法
        
    Returns:
        信息系数，范围 [-1, 1]
        
    Raises:
        ValueError: 当factor和returns长度不一致时
    """
    # ... 实现
```

### 铁律6: 性能要求必须满足 ⚡

**规则**: 关键路径必须满足白皮书定义的性能指标

**性能指标**:
- 本地推理延迟 < 20ms (P99)
- 热备切换延迟 < 200ms
- SPSC延迟 < 100μs

**检查方法**:
```python
import time

# 性能测试
start = time.perf_counter()
result = function_to_test()
elapsed = time.perf_counter() - start

assert elapsed < 0.020, f"性能不达标: {elapsed*1000:.2f}ms > 20ms"
```

### 铁律7: 测试覆盖率要求 🧪

**规则**: 所有新增代码必须有对应的单元测试

**测试要求**:
- 单元测试覆盖率 ≥ 85%
- 集成测试覆盖率 ≥ 75%
- E2E测试覆盖关键流程 100%

**检查方法**:
```bash
# 运行测试并检查覆盖率
pytest --cov=src --cov-report=term --cov-report=html

# 查看覆盖率报告
open htmlcov/index.html
```

---

## 🛠️ 工具和脚本

### 1. 幻觉检查脚本

**用途**: 检查代码中是否有白皮书未定义的类名、函数名

**使用方法**:
```bash
python scripts/check_hallucination.py src/your_module.py
```

**输出示例**:
```
⚠️ 可能的幻觉导入: brain.advanced_predictor
⚠️ 可能的幻觉类名: AdvancedOptimizer
```

### 2. 编码规则验证脚本

**用途**: 验证编码规则文件的完整性和一致性

**使用方法**:
```bash
python scripts/validate_coding_rules.py
```

**输出示例**:
```
================================================================================
MIA编码规则验证报告
================================================================================
总体评分: 88.7/100
  成功: 25项
  警告: 5项
  错误: 1项
```

### 3. 全量对齐检查脚本

**用途**: 检查所有文件的版本号、章节覆盖、性能指标等是否一致

**使用方法**:
```bash
python scripts/full_alignment_check.py
```

### 4. 提交前检查脚本

**用途**: 在提交代码前运行所有质量检查

**使用方法**:
```bash
python scripts/pre_commit_check.py
```

---

## 📚 相关文档

### 核心文档

1. **白皮书**: `00_核心文档/mia.md`
   - 系统架构和功能定义的唯一权威来源
   - 所有实现必须以此为准

2. **编码规则**: `.kiro/steering/mia_coding_rules.md`
   - LLM编码提示词系统
   - 7大核心铁律
   - 完整的编码流程和示例

3. **实现检查清单**: `00_核心文档/IMPLEMENTATION_CHECKLIST.md`
   - 245项实现检查项
   - 覆盖第1-19章完整内容
   - 进度追踪

4. **防幻觉指南**: `00_核心文档/ANTI_HALLUCINATION_GUIDE.md`
   - 什么是LLM幻觉
   - 如何防止幻觉
   - 幻觉检测清单

5. **开发指南**: `00_核心文档/DEVELOPMENT_GUIDE.md`
   - 开发环境设置
   - 编码规范
   - 最佳实践

### 验证报告

1. **编码规则验证报告**: `00_核心文档/CODING_RULES_VALIDATION_REPORT.md`
   - 编码规则文件的验证结果
   - 问题分析和改进建议

2. **全量对齐报告**: `00_核心文档/FULL_ALIGNMENT_REPORT.md`
   - 所有文件的一致性检查结果
   - 对齐评分: 100/100

---

## ❓ 常见问题

### Q1: 如何确认一个类名是否在白皮书中定义？

**A**: 使用grep搜索：
```bash
grep -n "ClassName" 00_核心文档/mia.md
```

如果找不到，说明是幻觉！

### Q2: 如果白皮书中没有定义某个内部数据结构怎么办？

**A**: 合理的内部数据结构不算幻觉，但需要：
1. 在docstring中说明用途
2. 使用 `@dataclass` 或类似装饰器
3. 不要暴露为公共API

示例：
```python
from dataclasses import dataclass

@dataclass
class Individual:
    """个体（因子表达式）- GeneticMiner的内部数据结构
    
    Attributes:
        expression: 因子表达式字符串
        fitness: 适应度评分
    """
    expression: str
    fitness: float = 0.0
```

### Q3: 如何处理白皮书中未明确的实现细节？

**A**: 遵循以下原则：
1. 优先查阅架构决策记录（ADR）
2. 参考防幻觉指南
3. 使用工业界最佳实践
4. 在docstring中说明实现依据

### Q4: 测试覆盖率达不到85%怎么办？

**A**: 
1. 补充测试用例（正常、边界、异常）
2. 使用参数化测试减少重复代码
3. 使用pytest-cov查看未覆盖的代码
4. 如果确实无法测试，添加 `# pragma: no cover` 注释

### Q5: 性能测试失败怎么办？

**A**:
1. 使用性能分析工具（如cProfile）找到瓶颈
2. 优化算法和数据结构
3. 使用缓存减少重复计算
4. 如果确实无法达标，与团队讨论调整指标

---

## 🎯 总结

**记住三个关键问题**:

1. **这个功能在白皮书中有定义吗？**
2. **这个API在白皮书中有定义吗？**
3. **这个性能指标经过验证了吗？**

**如果答案是"不确定"，那就是幻觉的信号！**

---

**原则**: 宁可多查一次白皮书，也不要凭记忆编码！

**目标**: 编写工业级、无幻觉、高质量的代码！

---

**文档版本**: v1.6.0  
**最后更新**: 2026-01-18  
**维护者**: MIA Team
