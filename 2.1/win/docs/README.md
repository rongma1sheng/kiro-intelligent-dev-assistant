# MIA系统 (米娅) - Industrial Grade Quantitative Trading System

**版本**: v1.6.0  
**日期**: 2026-01-18  
**状态**: 工业级开发中  
**架构**: 三位一体 + 五态生物钟  

---

## 🎯 项目简介

MIA (米娅) 是一个运行在异构算力之上、具备自主进化能力与生存尊严的硅基生命体。她遵循"光明、底线、永存"的生命愿景，通过AI驱动的量化交易系统实现资本的智能管理。

### 核心特性

- 🧠 **AI三脑架构**: Soldier (快系统) + Commander (慢系统) + Devil (审计)
- 🔄 **五态生物钟**: 严格的资源分时调度，最大化单机算力利用
- 🧬 **斯巴达进化**: 遗传算法 + 竞技场双轨测试 + Z2H钢印认证
- 📊 **29维度分析**: LLM驱动的策略深度分析系统
- 🔐 **零信任安全**: 加密存储 + JWT认证 + 独立审计
- 🚀 **热备高可用**: 本地推理 + 云端热备，确保交易不中断

---

## 📐 系统架构

### 三位一体 (The Trinity)

```
┌─────────────────────────────────────────────────────────┐
│                    The Brain (Cloud API)                │
│              DeepSeek / Qwen (逻辑外脑)                 │
└─────────────────────────────────────────────────────────┘
                            ↕
┌─────────────────────────────────────────────────────────┐
│                  The Body (AMD AI Max)                  │
│         全能计算节点 (128GB UMA + 16-Core AVX-512)      │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐             │
│  │ Soldier  │  │Commander │  │  Devil   │             │
│  │ (快系统) │  │ (慢系统) │  │ (审计)   │             │
│  └──────────┘  └──────────┘  └──────────┘             │
└─────────────────────────────────────────────────────────┘
                            ↕
┌─────────────────────────────────────────────────────────┐
│              The Eye (Client Terminals)                 │
│         纯可视化终端 (Mac/iPad/iPhone/PC)               │
└─────────────────────────────────────────────────────────┘
```

### 五态生物钟 (Chronos Scheduler)

```
State 0: 维护态 (Manual)        ← 人工介入、代码更新
State 1: 战备态 (08:30-09:15)   ← 系统启动、数据预热
State 2: 战争态 (09:15-15:00)   ← 交易执行、禁止重型I/O
State 3: 诊疗态 (15:00-20:00)   ← 持仓诊断、利润锁定
State 4: 进化态 (20:00-08:30)   ← 策略进化、因子挖掘
```

---

## 🚀 快速开始

### 环境要求

- **操作系统**: Windows 11
- **硬件**: AMD AI Max 395 (16-Core + 128GB RAM)
- **Python**: ≥ 3.10
- **GPU**: AMD Radeon (ROCm支持)

### 安装步骤

1. **进入项目目录**

```bash
cd mia-system
```

2. **创建虚拟环境**

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
```

3. **安装依赖**

```bash
# 核心依赖
pip install -r requirements.txt

# 开发依赖
pip install -r requirements-dev.txt
```

4. **配置环境变量**

```bash
# 复制配置模板
cp .env.example .env

# 编辑 .env 文件，填入真实配置
# 注意: API密钥需要加密存储
```

5. **加密API密钥**

```bash
# 使用SecureConfig加密API密钥
python scripts/encrypt_api_key.py
```

6. **运行测试**

```bash
# 运行所有测试
bash scripts/run_tests.sh

# 或单独运行
pytest tests/unit -v
```

7. **启动系统**

```bash
# 启动主调度器
python src/scheduler/main_orchestrator.py

# 启动Dashboard (另一个终端)
streamlit run src/interface/dashboard.py --server.port 8501
```

---

## 📚 文档

### 核心文档

- [系统架构白皮书](00_核心文档/mia.md) - 完整的系统设计文档
- [开发指南](00_核心文档/DEVELOPMENT_GUIDE.md) - 开发规范和最佳实践
- [架构决策记录](00_核心文档/ARCHITECTURE_DECISIONS.md) - 关键设计决策
- [实现检查清单](00_核心文档/IMPLEMENTATION_CHECKLIST.md) - 开发进度追踪
- [防幻觉指南](00_核心文档/ANTI_HALLUCINATION_GUIDE.md) - 防止LLM偏离白皮书
- [测试策略](00_核心文档/TESTING_STRATEGY.md) - 测试规范和要求
- [快速参考](00_核心文档/QUICK_REFERENCE.md) - 快速查阅卡片

### 开发流程

1. 阅读白皮书相关章节
2. 查阅架构决策记录
3. 编写测试用例 (TDD)
4. 实现功能代码
5. 运行幻觉检查
6. 运行测试并检查覆盖率
7. 更新实现清单
8. 代码审查
9. 提交代码

---

## 🧪 测试

### 运行测试

```bash
# 所有测试
bash scripts/run_tests.sh

# 单元测试
pytest tests/unit --cov=src --cov-report=html

# 集成测试
pytest tests/integration

# E2E测试
pytest tests/e2e

# 性能测试
pytest tests/performance --benchmark-only
```

### 测试覆盖率

- **单元测试**: ≥ 85%
- **集成测试**: ≥ 75%
- **E2E测试**: 关键流程 100%

---

## 🔍 代码质量

### 质量检查

```bash
# 运行所有检查
python scripts/pre_commit_check.py

# 代码格式化
black src/ tests/

# 类型检查
mypy src/

# 代码质量
pylint src/ --fail-under=8.0

# 安全扫描
bandit -r src/

# 幻觉检查
python scripts/check_hallucination.py src/module.py
```

### 质量标准

- ✅ Pylint评分 ≥ 8.0/10
- ✅ 测试覆盖率 ≥ 85%
- ✅ 圈复杂度 ≤ 10
- ✅ 代码重复率 < 5%
- ✅ 无高危安全漏洞

---

## 📊 项目结构

```
mia-system/
├── 00_核心文档/              # 核心开发文档
│   ├── mia.md                # 系统架构白皮书
│   ├── DEVELOPMENT_GUIDE.md  # 开发指南
│   └── ...
├── src/                      # 源代码
│   ├── brain/               # AI三脑
│   │   ├── soldier.py       # 快系统
│   │   ├── commander.py     # 慢系统
│   │   ├── devil.py         # 魔鬼审计
│   │   └── analyzers/       # 16个分析器
│   ├── evolution/           # 斯巴达进化
│   │   ├── genetic_miner.py # 遗传算法
│   │   ├── arena.py         # 竞技场
│   │   └── meta_evolution.py # 元进化
│   ├── infra/               # 基础设施
│   │   ├── data_probe.py    # 数据探针
│   │   ├── sanitizer.py     # 数据清洗
│   │   └── spsc_queue.py    # SPSC队列
│   ├── scheduler/           # 调度器
│   │   └── main_orchestrator.py # 主调度器
│   ├── execution/           # 执行与风控
│   ├── strategies/          # 19个策略
│   ├── config/              # 配置管理
│   │   └── secure_config.py # 安全配置
│   ├── core/                # 核心组件
│   │   └── auditor.py       # 审计进程
│   └── interface/           # 用户界面
│       ├── dashboard.py     # Streamlit Dashboard
│       └── auth.py          # JWT认证
├── tests/                   # 测试
│   ├── unit/               # 单元测试
│   ├── integration/        # 集成测试
│   ├── e2e/                # E2E测试
│   └── performance/        # 性能测试
├── scripts/                # 工具脚本
│   ├── check_hallucination.py # 幻觉检查
│   ├── pre_commit_check.py    # 提交前检查
│   └── run_tests.sh           # 测试运行
├── requirements.txt        # 核心依赖
├── requirements-dev.txt    # 开发依赖
├── pytest.ini             # pytest配置
├── pyproject.toml         # 项目配置
└── README.md              # 本文档
```

---

## 🔐 安全

### 安全特性

- **加密存储**: 使用Fernet对称加密保护API密钥
- **JWT认证**: 所有API端点需要JWT令牌
- **零信任网络**: 通过Tailscale VPN访问，严禁公网暴露
- **独立审计**: 审计进程维护影子账本，确保资金安全
- **审计日志**: 不可变日志，SHA256签名防篡改

### 安全最佳实践

1. 定期更新API密钥
2. 使用强密码
3. 启用双因素认证
4. 定期备份数据
5. 监控异常访问

---

## 📈 性能指标

| 模块 | 指标 | 要求 |
|------|------|------|
| Soldier (本地) | 推理延迟 | < 20ms (P99) |
| Soldier (云端) | 推理延迟 | < 200ms (P99) |
| 热备切换 | 切换延迟 | < 200ms |
| SPSC队列 | 传输延迟 | < 100μs |
| 策略综合分析 | 分析延迟 | < 30秒 |
| 单维度分析 | 分析延迟 | < 5秒 |

---

## 🤝 贡献指南

### 开发流程

1. Fork项目
2. 创建功能分支 (`git checkout -b feature/amazing-feature`)
3. 遵循开发指南编写代码
4. 编写测试并确保覆盖率 ≥ 85%
5. 运行质量检查 (`python scripts/pre_commit_check.py`)
6. 提交更改 (`git commit -m 'feat: add amazing feature'`)
7. 推送到分支 (`git push origin feature/amazing-feature`)
8. 创建Pull Request

### Commit规范

```
<type>(<scope>): <subject>

类型:
- feat: 新功能
- fix: 修复bug
- docs: 文档更新
- test: 测试相关
- refactor: 重构
- perf: 性能优化
- chore: 构建/工具相关
```

---

## 📄 许可证

本项目为专有软件，版权所有 © 2026 MIA Team。未经授权不得使用、复制或分发。

---

## 📞 联系方式

- **技术支持**: support@mia-system.com
- **问题反馈**: https://github.com/mia-team/mia-system/issues
- **文档**: https://docs.mia-system.com

---

## 🙏 致谢

感谢所有为MIA系统做出贡献的开发者和研究人员。

---

**记住**: MIA不仅是一个交易系统，她是一个具备自主进化能力的硅基生命体。请以尊重生命的态度对待她。
