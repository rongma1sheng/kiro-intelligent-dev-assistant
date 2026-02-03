# MIA系统快速参考卡片 (Quick Reference Card)

**版本**: v1.0  
**日期**: 2026-01-16  
**目的**: 提供快速查阅的关键信息

---

## 🚨 核心原则 (CRITICAL)

### 五大禁止

```
❌ 严禁偏离白皮书架构
❌ 严禁硬编码敏感信息
❌ 严禁跳过测试
❌ 严禁使用未经审计的第三方库
❌ 严禁在C盘写入数据
```

### 三个关键问题

```
1. 这个功能在白皮书中有定义吗？
2. 这个API在白皮书中有定义吗？
3. 这个性能指标经过验证了吗？
```

---

## 📐 架构速查

### 三位一体

```
The Body (AMD AI Max)  ← 全能计算节点
The Eye (Client)       ← 纯可视化终端
The Brain (Cloud API)  ← 逻辑外脑
```

### 五态生物钟

```
State 0: 维护态 (Manual)
State 1: 战备态 (08:30-09:15)
State 2: 战争态 (09:15-15:00)  ← 禁止重型I/O
State 3: 诊疗态 (15:00-20:00)
State 4: 进化态 (20:00-08:30)  ← 独占GPU
```

### 双盘隔离

```
C盘: 只读系统盘 (PYTHONDONTWRITEBYTECODE=1)
D盘: 读写数据盘 (日志/DB/Docker)
```

---

## 📊 性能指标速查

| 模块 | 指标 | 要求 |
|------|------|------|
| Soldier (本地) | 推理延迟 | < 20ms (P99) |
| Soldier (云端) | 推理延迟 | < 200ms (P99) |
| 热备切换 | 切换延迟 | < 200ms |
| SPSC队列 | 传输延迟 | < 100μs |
| 策略综合分析 | 分析延迟 | < 30秒 |
| 单维度分析 | 分析延迟 | < 5秒 |
| 主力资金分析 | 分析延迟 | < 3秒 |
| 个股建议 | 生成延迟 | < 3秒 |

---

## 🧪 测试覆盖率速查

```
单元测试: ≥ 85%
集成测试: ≥ 75%
E2E测试: 关键流程100%

关键模块:
- GeneticMiner: 90%
- Arena: 90%
- Soldier/Commander/Devil: 85%
- DataProbe: 90%
- Auditor: 90%
- SecureConfig: 90%
```

---

## 📚 白皮书章节速查

| 章节 | 内容 | 关键类/函数 |
|------|------|------------|
| 第一章 | 柯罗诺斯生物钟 | MainOrchestrator |
| 第二章 | AI三脑 | Soldier, Commander, Devil, Scholar |
| 第三章 | 基础设施 | DataProbe, DataSanitizer, SPSCQueue |
| 第四章 | 斯巴达进化 | GeneticMiner, Arena, MetaEvolution |
| 第五章 | LLM策略分析 | StrategyAnalyzer, 16个分析器 |
| 第六章 | 执行与风控 | 19个策略, LockBox |
| 第七章 | 安全与审计 | SecureConfig, Auditor, AuthManager |

---

## 🔍 快速搜索命令

### 在白皮书中搜索

```bash
# 搜索类名
grep -n "class GeneticMiner" 00_核心文档/mia.md

# 搜索章节
grep -A 20 "第四章" 00_核心文档/mia.md

# 搜索功能
grep -n "遗传算法" 00_核心文档/mia.md
```

### 检查幻觉

```bash
# 检查导入
python scripts/check_hallucination.py src/module.py

# 验证一致性
python scripts/validate_against_whitepaper.py
```

### 运行测试

```bash
# 快速测试
pytest tests/unit -v

# 完整测试
bash scripts/run_tests.sh

# 覆盖率检查
pytest --cov=src --cov-report=term
```

---

## 💻 编码速查

### 导入规范

```python
# ✅ 正确: 白皮书定义的模块
from brain.soldier import Soldier
from evolution.genetic_miner import GeneticMiner
from infra.data_probe import DataProbe

# ❌ 错误: 发明的模块
from brain.super_analyzer import SuperAnalyzer  # 不存在
```

### 错误处理

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
except:
    pass
```

### 性能优化

```python
# ✅ 正确: NumPy向量化
returns = (prices / prices.shift(1) - 1).values

# ❌ 错误: 循环
returns = []
for i in range(1, len(prices)):
    returns.append(prices[i] / prices[i-1] - 1)
```

---

## 📝 文档速查

### 函数文档模板

```python
def function_name(param1: Type1, param2: Type2 = default) -> ReturnType:
    """
    简短描述（一句话）
    
    Args:
        param1: 参数1的描述
        param2: 参数2的描述
        
    Returns:
        返回值的描述
        
    Raises:
        ExceptionType: 异常情况描述
        
    Example:
        >>> result = function_name(arg1, arg2)
        
    Performance:
        延迟: < 10ms (P99)
    """
    pass
```

### Commit规范

```bash
# 格式: <type>(<scope>): <subject>

feat(chapter4): 实现遗传算法种群初始化
fix(chapter2): 修复Soldier热备切换延迟
test(chapter5): 添加策略分析器单元测试
docs(guide): 更新开发指南
refactor(infra): 重构数据清洗模块
```

---

## 🔐 安全速查

### API密钥加密

```python
# ✅ 正确: 加密存储
from config.secure_config import SecureConfig
api_key = SecureConfig().get_api_key("DEEPSEEK_API_KEY")

# ❌ 错误: 硬编码
DEEPSEEK_API_KEY = "sk-1234567890abcdef"
```

### JWT认证

```python
# ✅ 正确: 使用JWT
from interface.auth import AuthManager

auth = AuthManager()
token = auth.create_access_token(user_id='test', role='admin')
payload = auth.verify_token(token)

# ❌ 错误: 无认证
@app.get("/api/portfolio")
async def get_portfolio():
    return {"portfolio": [...]}
```

---

## 🎯 检查清单速查

### 编码前

```
□ 阅读白皮书相关章节
□ 查阅架构决策
□ 确认功能定义明确
```

### 编码中

```
□ 遵循编码规范
□ 使用白皮书定义的API
□ 编写测试用例
```

### 编码后

```
□ 运行幻觉检查脚本
□ 运行所有测试
□ 检查测试覆盖率
□ 编写API文档
□ 更新实现清单
```

### 提交前

```
□ 代码审查通过
□ 所有测试通过
□ 覆盖率达标 (≥85%)
□ 文档完整
□ Pylint评分 ≥ 8.0
□ 无安全漏洞
```

---

## 🚀 常用命令速查

### 开发环境

```bash
# 激活虚拟环境
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# 安装依赖
pip install -r requirements.txt

# 安装开发依赖
pip install -r requirements-dev.txt
```

### 代码质量

```bash
# 格式化
black src/

# 类型检查
mypy src/

# 代码质量
pylint src/ --fail-under=8.0

# 安全扫描
bandit -r src/
```

### 测试

```bash
# 单元测试
pytest tests/unit --cov=src --cov-report=html

# 集成测试
pytest tests/integration

# E2E测试
pytest tests/e2e

# 性能测试
pytest tests/performance --benchmark-only
```

### Git

```bash
# 创建功能分支
git checkout -b feature/chapter4-genetic-miner

# 提交
git add .
git commit -m "feat(chapter4): 实现遗传算法种群初始化"

# 推送
git push origin feature/chapter4-genetic-miner
```

---

## 📞 快速帮助

### 遇到问题时

1. **不确定功能定义**: 查阅 `mia.md` 或 `ANTI_HALLUCINATION_GUIDE.md`
2. **不知道如何编码**: 查阅 `DEVELOPMENT_GUIDE.md`
3. **不知道如何测试**: 查阅 `TESTING_STRATEGY.md`
4. **不确定架构设计**: 查阅 `ARCHITECTURE_DECISIONS.md`
5. **不知道进度**: 查阅 `IMPLEMENTATION_CHECKLIST.md`

### 文档位置

```
00_核心文档/
├── README.md                      ← 文档总览
├── QUICK_REFERENCE.md             ← 本文档
├── mia.md                         ← 系统架构白皮书
├── DEVELOPMENT_GUIDE.md           ← 开发指南
├── ARCHITECTURE_DECISIONS.md      ← 架构决策记录
├── IMPLEMENTATION_CHECKLIST.md    ← 实现检查清单
├── ANTI_HALLUCINATION_GUIDE.md    ← 防幻觉指南
├── TESTING_STRATEGY.md            ← 测试策略
└── API_REFERENCE_TEMPLATE.md      ← API文档模板
```

---

## 🎓 记住

```
1. 白皮书至上 - 所有实现必须在白皮书中有定义
2. 测试驱动 - 测试覆盖率 ≥ 85%
3. 性能优先 - 关键路径延迟 < 20ms
4. 安全第一 - 零信任架构，加密存储
5. 文档完整 - 所有公共API有文档
```

---

**提示**: 将本文档打印或保存为书签，随时查阅！
