# MIA系统项目目录结构规划

**版本**: v1.6.0  
**日期**: 2026-01-18  
**目的**: 定义完整的项目目录结构

---

## 📁 完整目录结构

```
MIA_System/
│
├─ 00_核心文档/                          # 核心开发文档
│  ├─ README.md                         # 文档总览
│  ├─ mia.md                            # 系统架构白皮书 ⭐⭐⭐⭐⭐
│  ├─ DEVELOPMENT_GUIDE.md              # 开发指南
│  ├─ ARCHITECTURE_DECISIONS.md         # 架构决策记录
│  ├─ IMPLEMENTATION_CHECKLIST.md       # 实现检查清单
│  ├─ ANTI_HALLUCINATION_GUIDE.md       # 防幻觉指南
│  ├─ TESTING_STRATEGY.md               # 测试策略
│  ├─ API_REFERENCE_TEMPLATE.md         # API文档模板
│  ├─ QUICK_REFERENCE.md                # 快速参考
│  ├─ DOCUMENTATION_SUMMARY.md          # 文档体系总结
│  └─ PROJECT_STRUCTURE.md              # 本文档
│
├─ 01_开发过程文档/                      # 开发过程记录（可选）
│  ├─ CLEANUP_PLAN_REPORT.md
│  ├─ FINAL_CLEANUP_SUMMARY.md
│  ├─ README_CLEANUP.md
│  └─ READY_TO_CLEAN.md
│
├─ src/                                  # 源代码目录
│  │
│  ├─ scheduler/                         # 第一章: 柯罗诺斯生物钟
│  │  ├─ __init__.py
│  │  ├─ main_orchestrator.py           # 主调度器
│  │  ├─ state_machine.py               # 五态状态机
│  │  ├─ gpu_watchdog.py                # GPU看门狗
│  │  └─ calendar.py                    # 日历感知
│  │
│  ├─ brain/                             # 第二章: AI三脑
│  │  ├─ __init__.py
│  │  ├─ soldier.py                     # Soldier (快系统)
│  │  ├─ commander.py                   # Commander (慢系统)
│  │  ├─ devil.py                       # Devil (魔鬼审计)
│  │  ├─ scholar.py                     # Scholar (学者引擎)
│  │  ├─ algo_hunter.py                 # Algo Hunter (主力雷达)
│  │  ├─ algo_evolution_sentinel.py     # 🧬 AlgoEvolution Sentinel (算法进化哨兵) - 新增
│  │  ├─ failover.py                    # 热备切换
│  │  ├─ model_loader.py                # 模型加载器
│  │  ├─ algo_evolution/                # 算法进化监控模块 - 新增
│  │  │  ├─ __init__.py
│  │  │  ├─ paper_monitor.py            # 论文监控器
│  │  │  ├─ algo_translator.py          # 算法翻译器
│  │  │  ├─ sandbox_validator.py        # 沙盒验证器
│  │  │  ├─ evolution_integrator.py     # 进化集成器
│  │  │  ├─ dashboard.py                # 监控仪表板
│  │  │  └─ models/                     # 数据模型
│  │  │     ├─ __init__.py
│  │  │     ├─ paper.py                 # 论文数据模型
│  │  │     ├─ algorithm.py             # 算法数据模型
│  │  │     └─ validation_result.py     # 验证结果模型
│  │  ├─ memory/                        # 🧠 统一记忆系统 - 新增
│  │  │  ├─ __init__.py
│  │  │  ├─ unified_memory_system.py    # 统一记忆系统
│  │  │  ├─ working_memory.py           # 工作记忆
│  │  │  ├─ enhanced_short_term_memory.py # 增强短期记忆
│  │  │  ├─ long_term_memory.py         # 长期记忆
│  │  │  ├─ episodic_memory.py          # 情景记忆
│  │  │  ├─ semantic_memory.py          # 语义记忆
│  │  │  ├─ memory_manager.py           # 记忆管理器
│  │  │  ├─ context_compressor.py       # 上下文压缩器
│  │  │  ├─ knowledge_extractor.py      # 知识提取器
│  │  │  ├─ memory_sync_scheduler.py    # 记忆同步调度器
│  │  │  └─ engram/                     # 🚀 Engram记忆模块 - 革命性新增
│  │  │     ├─ __init__.py
│  │  │     ├─ engram_memory.py         # Engram核心记忆系统
│  │  │     ├─ deterministic_hash_router.py # 确定性哈希路由
│  │  │     ├─ memory_table.py          # 记忆表 (RAM/SSD)
│  │  │     ├─ ngram_extractor.py       # N-gram特征提取器
│  │  │     ├─ gating_mechanism.py      # 门控融合机制
│  │  │     ├─ performance_optimizer.py # 性能优化器
│  │  │     ├─ engram_cluster.py        # 分布式Engram集群
│  │  │     └─ memory_embeddings.py     # 记忆向量管理
│  │  └─ analyzers/                     # 第五章: 16个分析器
│  │     ├─ __init__.py
│  │     ├─ strategy_analyzer.py        # 策略分析器（总控）
│  │     ├─ essence_analyzer.py         # 策略本质分析
│  │     ├─ risk_analyzer.py            # 风险识别与评估
│  │     ├─ overfitting_detector.py     # 过度拟合检测
│  │     ├─ feature_analyzer.py         # 特征工程分析
│  │     ├─ macro_analyzer.py           # 大盘判断与宏观分析
│  │     ├─ microstructure_analyzer.py  # 市场微观结构分析
│  │     ├─ sector_analyzer.py          # 行业与板块分析
│  │     ├─ smart_money_analyzer.py     # 主力资金深度分析
│  │     ├─ recommendation_engine.py    # 个股结论性建议
│  │     ├─ trading_cost_analyzer.py    # 交易成本分析
│  │     ├─ decay_analyzer.py           # 策略衰减分析
│  │     ├─ stop_loss_analyzer.py       # 止损逻辑优化
│  │     ├─ slippage_analyzer.py        # 滑点分析
│  │     ├─ nonstationarity_analyzer.py # 非平稳性处理
│  │     ├─ signal_noise_analyzer.py    # 信噪比分析
│  │     ├─ capacity_analyzer.py        # 资金容量评估
│  │     ├─ stress_test_analyzer.py     # 压力测试
│  │     ├─ trade_review_analyzer.py    # 交易复盘
│  │     ├─ sentiment_analyzer.py       # 市场情绪
│  │     ├─ retail_sentiment_analyzer.py # 散户情绪
│  │     ├─ correlation_analyzer.py     # 相关性分析
│  │     └─ position_sizing_analyzer.py # 仓位管理
│  │
│  ├─ infra/                             # 第三章: 基础设施
│  │  ├─ __init__.py
│  │  ├─ spsc_queue.py                  # SPSC无锁环形队列
│  │  ├─ data_probe.py                  # 数据探针（自适应）
│  │  ├─ sanitizer.py                   # 数据清洗器（8层）
│  │  ├─ bridge.py                      # 历史数据注入桥接器
│  │  ├─ ipc_protocol.py                # IPC标准化协议
│  │  ├─ redis_pool.py                  # Redis连接池
│  │  ├─ websocket_server.py            # WebSocket服务器
│  │  └─ bar_synthesizer.py             # Bar合成器
│  │
│  ├─ evolution/                         # 第四章: 斯巴达进化
│  │  ├─ __init__.py
│  │  ├─ genetic_miner.py               # 遗传算法因子挖掘
│  │  ├─ arena.py                       # 斯巴达竞技场（双轨测试）
│  │  ├─ meta_evolution.py              # 超参数元进化
│  │  ├─ prompt_evolution.py            # 提示词进化引擎
│  │  ├─ z2h_capsule.py                 # Z2H基因胶囊
│  │  ├─ darwin_system.py               # 达尔文进化体系集成
│  │  ├─ operator_whitelist.py          # 算子白名单
│  │  └─ security/                      # 🔒 统一安全网关 (第七章)
│  │     ├─ __init__.py
│  │     ├─ unified_security_gateway.py # 统一安全网关
│  │     ├─ ast_whitelist_validator.py  # AST白名单验证器
│  │     ├─ docker_sandbox.py           # Docker沙箱
│  │     ├─ network_guard.py            # 网络防护
│  │     ├─ audit_logger.py             # 审计日志
│  │     ├─ container_pool.py           # 容器池
│  │     ├─ security_context.py         # 安全上下文
│  │     ├─ validation_result.py        # 验证结果
│  │     └─ security_errors.py          # 安全错误定义
│  │
│  ├─ execution/                         # 第六章: 执行与风控
│  │  ├─ __init__.py
│  │  ├─ executor.py                    # 游击队战术执行
│  │  ├─ risk_gate.py                   # 风险门闸
│  │  ├─ lockbox.py                     # 诺亚方舟（LockBox）
│  │  └─ margin_watchdog.py             # 保证金看门狗
│  │
│  ├─ strategies/                        # 第六章: 15个策略
│  │  ├─ __init__.py
│  │  ├─ meta_momentum/                 # Meta-Momentum (动量系)
│  │  │  ├─ __init__.py
│  │  │  ├─ S02_aggressive.py           # S02: Aggressive (激进)
│  │  │  ├─ S07_morning_sniper.py       # S07: Morning Sniper (首板)
│  │  │  └─ S13_limit_down_reversal.py  # S13: Limit Down Reversal (地天板)
│  │  ├─ meta_mean_reversion/           # Meta-MeanReversion (回归系)
│  │  │  ├─ __init__.py
│  │  │  ├─ S01_retracement.py          # S01: Retracement (回马枪)
│  │  │  ├─ S05_dynamic_grid.py         # S05: Dynamic Grid (网格)
│  │  │  └─ S11_fallen_angel.py         # S11: Fallen Angel (堕落天使)
│  │  ├─ meta_following/                # Meta-Following (跟随系)
│  │  │  ├─ __init__.py
│  │  │  ├─ S06_dragon_tiger.py         # S06: Dragon Tiger (龙虎榜)
│  │  │  ├─ S10_northbound.py           # S10: Northbound (北向)
│  │  │  └─ S15_algo_hunter.py          # S15: Algo Hunter (主力雷达)
│  │  ├─ meta_arbitrage/                # Meta-Arbitrage (套利系)
│  │  │  ├─ __init__.py
│  │  │  ├─ S09_cb_scalper.py           # S09: CB Scalper (可转债)
│  │  │  ├─ S14_cross_domain_arb.py     # S14: Cross-Domain Arb (跨域)
│  │  │  ├─ S17_derivatives_linkage.py  # S17: Derivatives Linkage (期现联动)
│  │  │  ├─ S18_future_trend.py         # S18: Future Trend (期指趋势) [Shadow Mode]
│  │  │  └─ S19_option_sniper.py        # S19: Option Sniper (期权狙击) [Shadow Mode]
│  │  └─ meta_event/                    # Meta-Event (事件系)
│  │     ├─ __init__.py
│  │     └─ S16_theme_hunter.py         # S16: Theme Hunter (题材猎手)
│  │
│  ├─ config/                            # 配置管理
│  │  ├─ __init__.py
│  │  ├─ secure_config.py               # 安全配置（加密存储）
│  │  └─ settings.py                    # 系统设置
│  │
│  ├─ core/                              # 核心组件
│  │  ├─ __init__.py
│  │  ├─ auditor.py                     # 独立审计进程
│  │  ├─ regime_engine.py               # 市场态识别
│  │  ├─ capital_genome.py              # 资本基因树
│  │  └─ portfolio_doctor.py            # 持仓诊断
│  │
│  ├─ monitoring/                        # 监控与日志
│  │  ├─ __init__.py
│  │  ├─ audit_logger.py                # 审计日志系统
│  │  ├─ metrics.py                     # 性能指标
│  │  └─ alerts.py                      # 告警系统
│  │
│  ├─ interface/                         # 用户界面
│  │  ├─ __init__.py
│  │  ├─ dashboard.py                   # Streamlit Dashboard
│  │  ├─ auth.py                        # JWT认证
│  │  ├─ api.py                         # FastAPI接口
│  │  └─ websocket_handler.py           # WebSocket处理
│  │
│  └─ utils/                             # 工具函数
│     ├─ __init__.py
│     ├─ logger.py                      # 日志工具
│     ├─ decorators.py                  # 装饰器
│     └─ helpers.py                     # 辅助函数
│
├─ tests/                                # 测试目录
│  ├─ __init__.py
│  ├─ conftest.py                       # pytest配置
│  │
│  ├─ unit/                              # 单元测试
│  │  ├─ __init__.py
│  │  ├─ chapter_1/                     # 第一章测试
│  │  │  ├─ __init__.py
│  │  │  ├─ test_main_orchestrator.py
│  │  │  ├─ test_state_machine.py
│  │  │  └─ test_gpu_watchdog.py
│  │  ├─ chapter_2/                     # 第二章测试
│  │  │  ├─ __init__.py
│  │  │  ├─ test_soldier.py
│  │  │  ├─ test_commander.py
│  │  │  ├─ test_devil.py
│  │  │  └─ test_failover.py
│  │  ├─ chapter_3/                     # 第三章测试
│  │  │  ├─ __init__.py
│  │  │  ├─ test_spsc_queue.py
│  │  │  ├─ test_data_probe.py
│  │  │  └─ test_sanitizer.py
│  │  ├─ chapter_4/                     # 第四章测试
│  │  │  ├─ __init__.py
│  │  │  ├─ test_genetic_miner.py
│  │  │  ├─ test_arena.py
│  │  │  └─ test_meta_evolution.py
│  │  ├─ chapter_5/                     # 第五章测试
│  │  │  ├─ __init__.py
│  │  │  ├─ test_strategy_analyzer.py
│  │  │  └─ test_analyzers.py
│  │  ├─ chapter_6/                     # 第六章测试
│  │  │  ├─ __init__.py
│  │  │  ├─ test_executor.py
│  │  │  └─ test_strategies.py
│  │  └─ chapter_7/                     # 第七章测试 (统一安全网关)
│  │     ├─ __init__.py
│  │     ├─ test_unified_security_gateway.py  # 统一安全网关测试
│  │     ├─ test_ast_whitelist_validator.py   # AST白名单验证器测试
│  │     ├─ test_docker_sandbox.py            # Docker沙箱测试
│  │     ├─ test_network_guard.py             # 网络防护测试
│  │     ├─ test_audit_logger.py              # 审计日志测试
│  │     ├─ test_container_pool.py            # 容器池测试
│  │     ├─ test_security_context.py          # 安全上下文测试
│  │     ├─ test_secure_config.py             # 安全配置测试
│  │     └─ test_auditor.py                   # 审计器测试
│  │
│  ├─ integration/                       # 集成测试
│  │  ├─ __init__.py
│  │  ├─ chapter_1/
│  │  ├─ chapter_2/
│  │  ├─ chapter_3/
│  │  ├─ chapter_4/
│  │  ├─ chapter_5/
│  │  ├─ chapter_6/
│  │  └─ chapter_7/
│  │
│  ├─ e2e/                               # E2E测试
│  │  ├─ __init__.py
│  │  ├─ test_full_workflow.py          # 完整交易日流程
│  │  ├─ test_hot_failover.py           # 热备切换场景
│  │  └─ test_evolution_pipeline.py     # 进化流程
│  │
│  ├─ properties/                        # 属性测试 (Property-Based Testing)
│  │  ├─ __init__.py
│  │  ├─ evolution/
│  │  │  └─ security/
│  │  │     ├─ __init__.py
│  │  │     ├─ test_security_properties.py  # 安全属性测试
│  │  │     └─ generators.py                # 测试数据生成器
│  │  └─ conftest.py                    # pytest配置
│  │
│  └─ performance/                       # 性能测试
│     ├─ __init__.py
│     ├─ test_latency.py                # 延迟测试
│     ├─ test_throughput.py             # 吞吐量测试
│     └─ test_memory.py                 # 内存测试
│
├─ scripts/                              # 工具脚本
│  ├─ check_hallucination.py            # 幻觉检查
│  ├─ pre_commit_check.py               # 提交前检查
│  ├─ run_tests.sh                      # 测试运行
│  ├─ encrypt_api_key.py                # API密钥加密
│  ├─ setup_environment.py              # 环境配置
│  └─ generate_docs.py                  # 文档生成
│
├─ data/                                 # 数据目录（D盘）
│  ├─ .gitkeep
│  ├─ historical/                       # 历史数据
│  ├─ tick/                             # Tick数据
│  ├─ bar/                              # Bar数据
│  ├─ radar_archive/                    # 雷达信号归档
│  ├─ exported_factors/                 # 导出的因子
│  ├─ z2h_capsules/                     # Z2H基因胶囊
│  └─ backups/                          # 备份
│
├─ models/                               # 模型目录
│  ├─ .gitkeep
│  ├─ qwen-30b/                         # Qwen-30B模型
│  ├─ algo_hunter/                      # 主力雷达模型
│  └─ checkpoints/                      # 模型检查点
│
├─ logs/                                 # 日志目录（D盘）
│  ├─ .gitkeep
│  ├─ audit/                            # 审计日志
│  ├─ trading/                          # 交易日志
│  ├─ evolution/                        # 进化日志
│  └─ system/                           # 系统日志
│
├─ docs/                                 # 生成的文档
│  ├─ _build/                           # Sphinx构建输出
│  ├─ api/                              # API文档
│  └─ guides/                           # 使用指南
│
├─ docker/                               # Docker配置
│  ├─ Dockerfile
│  ├─ docker-compose.yml
│  └─ .dockerignore
│
├─ .github/                              # GitHub配置（如果使用）
│  └─ workflows/
│     ├─ ci.yml                         # CI流程
│     └─ test.yml                       # 测试流程
│
├─ .vscode/                              # VSCode配置
│  └─ settings.json
│
├─ requirements.txt                      # 核心依赖
├─ requirements-dev.txt                  # 开发依赖
├─ pytest.ini                           # pytest配置
├─ pyproject.toml                       # 项目配置
├─ .env.example                         # 环境变量模板
├─ .env                                 # 环境变量（不提交）
├─ .gitignore                           # Git忽略规则
├─ README.md                            # 项目说明
├─ START_HERE.md                        # 开始指南
└─ WORK_COMPLETED.md                    # 完成报告
```

---

## 📊 目录说明

### 核心源码 (src/)

#### scheduler/ - 第一章
- **main_orchestrator.py**: 主调度器，管理五态切换
- **state_machine.py**: 五态状态机实现
- **gpu_watchdog.py**: GPU看门狗，监控AMD显存
- **calendar.py**: 日历感知，识别交易日

#### brain/ - 第二章
- **soldier.py**: 快系统，毫秒级决策
- **commander.py**: 慢系统，战略级分析
- **devil.py**: 魔鬼审计，代码审计
- **scholar.py**: 学者引擎，研报学习
- **algo_hunter.py**: 主力雷达，识别主力行为
- **analyzers/**: 16个专业分析器

#### infra/ - 第三章
- **spsc_queue.py**: SPSC无锁环形队列
- **data_probe.py**: 数据探针，自适应数据源
- **sanitizer.py**: 数据清洗器，8层清洗
- **bridge.py**: 历史数据注入桥接器

#### evolution/ - 第四章
- **genetic_miner.py**: 遗传算法因子挖掘
- **arena.py**: 斯巴达竞技场，双轨测试
- **meta_evolution.py**: 超参数元进化
- **z2h_capsule.py**: Z2H基因胶囊

#### execution/ - 第六章
- **executor.py**: 游击队战术执行
- **risk_gate.py**: 风险门闸
- **lockbox.py**: 诺亚方舟，利润隔离

#### strategies/ - 第六章（15个策略）
- **meta_momentum/**: 动量系策略（3个：S02, S07, S13）
- **meta_mean_reversion/**: 回归系策略（3个：S01, S05, S11）
- **meta_following/**: 跟随系策略（3个：S06, S10, S15）
- **meta_arbitrage/**: 套利系策略（5个：S09, S14, S17, S18, S19）
- **meta_event/**: 事件系策略（1个：S16）

**注意**: 白皮书声称19个策略，实际只定义了15个（缺失S03, S04, S08, S12）

---

## 🎯 创建目录结构

### 自动创建脚本

创建 `scripts/setup_project_structure.py`:

```python
#!/usr/bin/env python3
"""
创建MIA系统项目目录结构
"""

import os
from pathlib import Path

def create_directory_structure():
    """创建完整的目录结构"""
    
    # 定义目录结构
    directories = [
        # 源代码
        "src/scheduler",
        "src/brain/analyzers",
        "src/infra",
        "src/evolution",
        "src/execution",
        "src/strategies/meta_momentum",
        "src/strategies/meta_mean_reversion",
        "src/strategies/meta_following",
        "src/strategies/meta_arbitrage",
        "src/strategies/meta_event",
        "src/config",
        "src/core",
        "src/monitoring",
        "src/interface",
        "src/utils",
        
        # 测试
        "tests/unit/chapter_1",
        "tests/unit/chapter_2",
        "tests/unit/chapter_3",
        "tests/unit/chapter_4",
        "tests/unit/chapter_5",
        "tests/unit/chapter_6",
        "tests/unit/chapter_7",
        "tests/integration/chapter_1",
        "tests/integration/chapter_2",
        "tests/integration/chapter_3",
        "tests/integration/chapter_4",
        "tests/integration/chapter_5",
        "tests/integration/chapter_6",
        "tests/integration/chapter_7",
        "tests/e2e",
        "tests/performance",
        
        # 数据
        "data/historical",
        "data/tick",
        "data/bar",
        "data/radar_archive",
        "data/exported_factors",
        "data/z2h_capsules",
        "data/backups",
        
        # 模型
        "models/qwen-30b",
        "models/algo_hunter",
        "models/checkpoints",
        
        # 日志
        "logs/audit",
        "logs/trading",
        "logs/evolution",
        "logs/system",
        
        # 文档
        "docs/_build",
        "docs/api",
        "docs/guides",
        
        # Docker
        "docker",
    ]
    
    # 创建目录
    for directory in directories:
        path = Path(directory)
        path.mkdir(parents=True, exist_ok=True)
        
        # 创建 __init__.py
        if directory.startswith("src/") or directory.startswith("tests/"):
            init_file = path / "__init__.py"
            if not init_file.exists():
                init_file.touch()
        
        # 创建 .gitkeep
        if directory.startswith("data/") or directory.startswith("models/") or directory.startswith("logs/"):
            gitkeep = path / ".gitkeep"
            if not gitkeep.exists():
                gitkeep.touch()
        
        print(f"✅ 创建目录: {directory}")
    
    print("\n🎉 目录结构创建完成！")

if __name__ == "__main__":
    create_directory_structure()
```

### 使用方法

```bash
# 运行脚本创建目录结构
python scripts/setup_project_structure.py
```

---

## 📝 文件命名规范

### Python文件

- **模块**: `snake_case.py`
- **类**: `PascalCase`
- **函数**: `snake_case()`
- **常量**: `UPPER_SNAKE_CASE`

### 测试文件

- **单元测试**: `test_<module_name>.py`
- **集成测试**: `test_<feature>_integration.py`
- **E2E测试**: `test_<scenario>_e2e.py`

### 文档文件

- **Markdown**: `UPPER_SNAKE_CASE.md`
- **配置**: `lowercase.ini`, `lowercase.toml`

---

## 🔍 目录职责

### src/ - 源代码
- 所有业务逻辑代码
- 按章节组织
- 每个模块独立

### tests/ - 测试
- 单元测试（75%）
- 集成测试（20%）
- E2E测试（5%）

### data/ - 数据
- 存储在D盘
- 不提交到Git
- 定期备份

### models/ - 模型
- 存储训练好的模型
- 不提交到Git（太大）
- 使用Git LFS（可选）

### logs/ - 日志
- 存储在D盘
- 审计日志永久保留
- 其他日志定期清理

### docs/ - 文档
- Sphinx生成的文档
- API参考
- 使用指南

---

## ✅ 检查清单

创建目录结构后，确认：

- [ ] 所有src/目录有__init__.py
- [ ] 所有tests/目录有__init__.py
- [ ] 所有data/目录有.gitkeep
- [ ] 所有models/目录有.gitkeep
- [ ] 所有logs/目录有.gitkeep
- [ ] .gitignore正确配置
- [ ] 目录权限正确

---

**记住**: 保持目录结构清晰，便于维护和扩展！

---

## 📊 第8-19章目录扩展

### 第八章: 混合模型成本控制

```
src/cost/                                # 成本控制模块
├─ __init__.py
├─ cost_tracker.py                      # 成本追踪器
├─ budget_manager.py                    # 预算管理器
├─ cost_optimizer.py                    # 成本优化器
└─ cost_reporter.py                     # 成本报表生成

tests/unit/chapter_8/                   # 第八章测试
├─ __init__.py
├─ test_cost_tracker.py
├─ test_budget_manager.py
└─ test_cost_optimizer.py
```

### 第九章: 工程铁律

```
scripts/                                 # 工具脚本（扩展）
├─ check_hallucination.py              # 幻觉检查
├─ pre_commit_check.py                  # 提交前检查
├─ run_tests.sh                         # 测试运行
├─ check_consistency.py                 # 一致性检查
├─ full_comparison.py                   # 全量对比
├─ analyze_whitepaper_completeness.py   # 白皮书完整度分析
├─ code_quality_check.py                # 代码质量检查（新增）
├─ security_scan.py                     # 安全扫描（新增）
└─ performance_benchmark.py             # 性能基准测试（新增）

.github/workflows/                       # CI/CD配置
├─ ci.yml                               # 持续集成
├─ test.yml                             # 测试流程
├─ security.yml                         # 安全扫描（新增）
└─ deploy.yml                           # 部署流程（新增）
```

### 第十章: 无人值守系统

```
src/core/                                # 核心组件（扩展）
├─ __init__.py
├─ auditor.py                           # 独立审计进程
├─ regime_engine.py                     # 市场态识别
├─ capital_genome.py                    # 资本基因树
├─ portfolio_doctor.py                  # 持仓诊断
├─ health_checker.py                    # 健康检查器（新增）
├─ fund_monitor.py                      # 资金监控器（新增）
├─ daemon.py                            # 守护进程（新增）
└─ notification_manager.py              # 通知管理器（新增）

tests/unit/chapter_10/                  # 第十章测试
├─ __init__.py
├─ test_health_checker.py
├─ test_fund_monitor.py
├─ test_daemon.py
└─ test_notification_manager.py
```

### 第十一章: AI安全与质量保障

```
src/brain/                               # AI三脑（扩展）
├─ __init__.py
├─ soldier.py                           # Soldier (快系统)
├─ commander.py                         # Commander (慢系统)
├─ devil.py                             # Devil (魔鬼审计)
├─ scholar.py                           # Scholar (学者引擎)
├─ algo_hunter.py                       # Algo Hunter (主力雷达)
├─ failover.py                          # 热备切换
├─ model_loader.py                      # 模型加载器
├─ hallucination_filter.py              # 防幻觉系统（新增）
└─ analyzers/                           # 16个分析器
    ├─ __init__.py
    ├─ strategy_analyzer.py
    ├─ essence_analyzer.py
    ├─ risk_analyzer.py
    ├─ overfitting_detector.py
    ├─ feature_analyzer.py
    ├─ macro_analyzer.py
    ├─ microstructure_analyzer.py
    ├─ sector_analyzer.py
    ├─ smart_money_analyzer.py
    ├─ recommendation_engine.py
    ├─ trading_cost_analyzer.py
    ├─ decay_analyzer.py
    ├─ stop_loss_analyzer.py
    ├─ slippage_analyzer.py
    ├─ nonstationarity_analyzer.py
    ├─ signal_noise_analyzer.py
    ├─ capacity_analyzer.py
    ├─ stress_test_analyzer.py
    ├─ trade_review_analyzer.py
    ├─ sentiment_analyzer.py
    ├─ retail_sentiment_analyzer.py
    ├─ correlation_analyzer.py
    └─ position_sizing_analyzer.py

src/evolution/                           # 斯巴达进化（扩展）
├─ __init__.py
├─ genetic_miner.py                     # 遗传算法因子挖掘
├─ arena.py                             # 斯巴达竞技场（双轨测试）
├─ meta_evolution.py                    # 超参数元进化
├─ prompt_evolution.py                  # 提示词进化引擎
├─ z2h_capsule.py                       # Z2H基因胶囊
├─ darwin_system.py                     # 达尔文进化体系集成
├─ operator_whitelist.py                # 算子白名单
├─ algorithm_validator.py               # 算法验证器（新增）
├─ algorithm_evolution_optimizer.py     # 算法进化优化器（新增）
└─ rlvr_engine.py                       # RLVR惩罚引擎（新增）

tests/unit/chapter_11/                  # 第十一章测试
├─ __init__.py
├─ test_hallucination_filter.py
├─ test_algorithm_validator.py
├─ test_algorithm_evolution_optimizer.py
└─ test_rlvr_engine.py
```

### 第十二章: 系统可靠性与运维

```
src/infra/                               # 基础设施（扩展）
├─ __init__.py
├─ spsc_queue.py                        # SPSC无锁环形队列
├─ data_probe.py                        # 数据探针（自适应）
├─ sanitizer.py                         # 数据清洗器（8层）
├─ bridge.py                            # 历史数据注入桥接器
├─ ipc_protocol.py                      # IPC标准化协议
├─ redis_pool.py                        # Redis连接池
├─ websocket_server.py                  # WebSocket服务器
├─ bar_synthesizer.py                   # Bar合成器
├─ redis_decorator.py                   # Redis重试装饰器（新增）
├─ network_resilience.py                # 网络容错系统（新增）
└─ shm_manager.py                       # SharedMemory管理器（新增）

src/core/                                # 核心组件（扩展）
├─ gpu_watchdog.py                      # GPU看门狗（新增）
└─ soldier_failover.py                  # Soldier热备切换（新增）

scripts/                                 # 工具脚本（扩展）
├─ deploy.sh                            # 部署脚本（新增）
├─ backup.sh                            # 备份脚本（新增）
├─ restore.sh                           # 恢复脚本（新增）
└─ health_check.sh                      # 健康检查脚本（新增）

tests/unit/chapter_12/                  # 第十二章测试
├─ __init__.py
├─ test_redis_pool.py
├─ test_gpu_watchdog.py
├─ test_soldier_failover.py
├─ test_shm_manager.py
└─ test_network_resilience.py
```

### 第十三章: 监控与可观测性

```
src/monitoring/                          # 监控与日志（扩展）
├─ __init__.py
├─ audit_logger.py                      # 审计日志系统
├─ metrics.py                           # 性能指标
├─ alerts.py                            # 告警系统
├─ metrics_collector.py                 # 指标采集器（新增）
├─ log_analyzer.py                      # 日志分析器（新增）
├─ trace_manager.py                     # 链路追踪管理器（新增）
└─ dashboard_metrics.py                 # Dashboard指标（新增）

tests/unit/chapter_13/                  # 第十三章测试
├─ __init__.py
├─ test_metrics_collector.py
├─ test_log_analyzer.py
└─ test_trace_manager.py
```

### 第十四章: 测试、质量与成熟度

```
tests/                                   # 测试目录（扩展）
├─ __init__.py
├─ conftest.py                          # pytest配置
│
├─ unit/                                # 单元测试
│  ├─ __init__.py
│  ├─ chapter_1/                        # 第一章测试
│  ├─ chapter_2/                        # 第二章测试
│  ├─ chapter_3/                        # 第三章测试
│  ├─ chapter_4/                        # 第四章测试
│  ├─ chapter_5/                        # 第五章测试
│  ├─ chapter_6/                        # 第六章测试
│  ├─ chapter_7/                        # 第七章测试
│  ├─ chapter_8/                        # 第八章测试（新增）
│  ├─ chapter_9/                        # 第九章测试（新增）
│  ├─ chapter_10/                       # 第十章测试（新增）
│  ├─ chapter_11/                       # 第十一章测试（新增）
│  ├─ chapter_12/                       # 第十二章测试（新增）
│  ├─ chapter_13/                       # 第十三章测试（新增）
│  ├─ chapter_14/                       # 第十四章测试（新增）
│  ├─ chapter_15/                       # 第十五章测试（新增）
│  ├─ chapter_16/                       # 第十六章测试（新增）
│  ├─ chapter_17/                       # 第十七章测试（新增）
│  ├─ chapter_18/                       # 第十八章测试（新增）
│  └─ chapter_19/                       # 第十九章测试（新增）
│
├─ integration/                          # 集成测试（扩展）
│  ├─ __init__.py
│  ├─ chapter_1/
│  ├─ chapter_2/
│  ├─ chapter_3/
│  ├─ chapter_4/
│  ├─ chapter_5/
│  ├─ chapter_6/
│  ├─ chapter_7/
│  ├─ chapter_8/                        # 新增
│  ├─ chapter_9/                        # 新增
│  ├─ chapter_10/                       # 新增
│  ├─ chapter_11/                       # 新增
│  ├─ chapter_12/                       # 新增
│  ├─ chapter_13/                       # 新增
│  ├─ chapter_14/                       # 新增
│  ├─ chapter_15/                       # 新增
│  ├─ chapter_16/                       # 新增
│  ├─ chapter_17/                       # 新增
│  ├─ chapter_18/                       # 新增
│  └─ chapter_19/                       # 新增
│
├─ e2e/                                  # E2E测试（扩展）
│  ├─ __init__.py
│  ├─ test_full_workflow.py             # 完整交易日流程
│  ├─ test_hot_failover.py              # 热备切换场景
│  ├─ test_evolution_pipeline.py        # 进化流程
│  ├─ test_cost_control.py              # 成本控制流程（新增）
│  ├─ test_emergency_response.py        # 应急响应流程（新增）
│  └─ test_disaster_recovery.py         # 灾难恢复流程（新增）
│
├─ performance/                          # 性能测试（扩展）
│  ├─ __init__.py
│  ├─ test_latency.py                   # 延迟测试
│  ├─ test_throughput.py                # 吞吐量测试
│  ├─ test_memory.py                    # 内存测试
│  ├─ test_concurrency.py               # 并发测试（新增）
│  └─ test_stress.py                    # 压力测试（新增）
│
└─ security/                             # 安全测试（新增）
   ├─ __init__.py
   ├─ test_encryption.py                # 加密测试
   ├─ test_authentication.py            # 认证测试
   ├─ test_authorization.py             # 授权测试
   └─ test_vulnerability.py             # 漏洞扫描测试

scripts/                                 # 工具脚本（扩展）
├─ code_quality_check.py                # 代码质量检查
├─ security_scan.py                     # 安全扫描
├─ performance_benchmark.py             # 性能基准测试
└─ maturity_assessment.py               # 成熟度评估（新增）
```

### 第十五章: 功能完善路线图

```
docs/                                    # 生成的文档（扩展）
├─ _build/                              # Sphinx构建输出
├─ api/                                 # API文档
├─ guides/                              # 使用指南
├─ roadmap/                             # 路线图文档（新增）
│  ├─ phase1_mvp.md                     # Phase 1: MVP
│  ├─ phase2_core.md                    # Phase 2: 核心功能
│  └─ phase3_advanced.md                # Phase 3: 高级功能
└─ changelog/                           # 变更日志（新增）
   ├─ v1.0.md
   ├─ v1.1.md
   └─ v2.0.md
```

### 第十六章: 性能优化指南

```
src/optimization/                        # 性能优化模块（新增）
├─ __init__.py
├─ latency_optimizer.py                 # 延迟优化器
├─ throughput_optimizer.py              # 吞吐量优化器
├─ resource_optimizer.py                # 资源优化器
├─ network_optimizer.py                 # 网络优化器
└─ cache_manager.py                     # 缓存管理器

tests/unit/chapter_16/                  # 第十六章测试
├─ __init__.py
├─ test_latency_optimizer.py
├─ test_throughput_optimizer.py
├─ test_resource_optimizer.py
└─ test_network_optimizer.py
```

### 第十七章: 架构演进规划

```
docker/                                  # Docker配置（扩展）
├─ Dockerfile                           # 主Dockerfile
├─ docker-compose.yml                   # Docker Compose配置
├─ .dockerignore                        # Docker忽略规则
├─ Dockerfile.trading                   # 交易服务（新增）
├─ Dockerfile.data                      # 数据服务（新增）
├─ Dockerfile.analysis                  # 分析服务（新增）
└─ Dockerfile.monitoring                # 监控服务（新增）

k8s/                                     # Kubernetes配置（新增）
├─ deployment.yaml                      # 部署配置
├─ service.yaml                         # 服务配置
├─ ingress.yaml                         # 入口配置
├─ configmap.yaml                       # 配置映射
├─ secret.yaml                          # 密钥配置
└─ hpa.yaml                             # 自动扩缩容配置

src/gateway/                             # API网关（新增）
├─ __init__.py
├─ gateway.py                           # 网关主程序
├─ auth_middleware.py                   # 认证中间件
├─ rate_limiter.py                      # 限流器
└─ circuit_breaker.py                   # 熔断器

tests/unit/chapter_17/                  # 第十七章测试
├─ __init__.py
├─ test_gateway.py
├─ test_auth_middleware.py
└─ test_rate_limiter.py
```

### 第十八章: 成本控制与优化

```
src/cost/                                # 成本控制模块（扩展）
├─ __init__.py
├─ cost_tracker.py                      # 成本追踪器
├─ budget_manager.py                    # 预算管理器
├─ cost_optimizer.py                    # 成本优化器
├─ cost_reporter.py                     # 成本报表生成
├─ resource_analyzer.py                 # 资源分析器（新增）
└─ cost_forecaster.py                   # 成本预测器（新增）

tests/unit/chapter_18/                  # 第十八章测试
├─ __init__.py
├─ test_resource_analyzer.py
└─ test_cost_forecaster.py
```

### 第十九章: 风险管理与应急响应

```
src/risk/                                # 风险管理模块（新增）
├─ __init__.py
├─ risk_identifier.py                   # 风险识别器
├─ risk_assessor.py                     # 风险评估器
├─ risk_responder.py                    # 风险应对器
├─ emergency_manager.py                 # 应急管理器
└─ incident_tracker.py                  # 事件追踪器

docs/emergency/                          # 应急文档（新增）
├─ system_failure.md                    # 系统故障预案
├─ data_loss.md                         # 数据丢失预案
├─ security_incident.md                 # 安全事件预案
├─ fund_anomaly.md                      # 资金异常预案
└─ disaster_recovery.md                 # 灾难恢复预案

tests/unit/chapter_19/                  # 第十九章测试
├─ __init__.py
├─ test_risk_identifier.py
├─ test_risk_assessor.py
├─ test_risk_responder.py
└─ test_emergency_manager.py
```

---

## 📈 完整目录统计

### 源代码目录

```
src/
├─ scheduler/          (第一章: 柯罗诺斯生物钟)
├─ brain/              (第二章: AI三脑 + 第十一章: AI安全)
├─ infra/              (第三章: 基础设施 + 第十二章: 可靠性)
├─ evolution/          (第四章: 斯巴达进化 + 第十一章: 算法验证)
├─ execution/          (第六章: 执行与风控)
├─ strategies/         (第六章: 15个策略)
├─ config/             (配置管理)
├─ core/               (核心组件 + 第十章: 无人值守)
├─ monitoring/         (第十三章: 监控与可观测性)
├─ interface/          (用户界面)
├─ utils/              (工具函数)
├─ cost/               (第八章: 成本控制 + 第十八章: 成本优化)
├─ optimization/       (第十六章: 性能优化)
├─ gateway/            (第十七章: API网关)
└─ risk/               (第十九章: 风险管理)

总计: 14个主要模块
```

### 测试目录

```
tests/
├─ unit/               (19个章节 × 单元测试)
├─ integration/        (19个章节 × 集成测试)
├─ e2e/                (端到端测试)
├─ performance/        (性能测试)
└─ security/           (安全测试)

总计: 5个测试类型
```

### 文档目录

```
docs/
├─ _build/             (Sphinx构建输出)
├─ api/                (API文档)
├─ guides/             (使用指南)
├─ roadmap/            (路线图文档)
├─ changelog/          (变更日志)
└─ emergency/          (应急文档)

总计: 6个文档类别
```

### 配置目录

```
docker/                (Docker配置)
k8s/                   (Kubernetes配置)
.github/workflows/     (CI/CD配置)
scripts/               (工具脚本)

总计: 4个配置类别
```

---

## 🎯 目录创建脚本更新

更新 `scripts/setup_project_structure.py` 以包含所有新增目录：

```python
#!/usr/bin/env python3
"""
创建MIA系统完整项目目录结构（第1-19章）
"""

import os
from pathlib import Path

def create_directory_structure():
    """创建完整的目录结构"""
    
    # 定义目录结构
    directories = [
        # 源代码（第1-7章）
        "src/scheduler",
        "src/brain/analyzers",
        "src/infra",
        "src/evolution",
        "src/execution",
        "src/strategies/meta_momentum",
        "src/strategies/meta_mean_reversion",
        "src/strategies/meta_following",
        "src/strategies/meta_arbitrage",
        "src/strategies/meta_event",
        "src/config",
        "src/core",
        "src/monitoring",
        "src/interface",
        "src/utils",
        
        # 源代码（第8-19章）
        "src/cost",                     # 第八章
        "src/optimization",             # 第十六章
        "src/gateway",                  # 第十七章
        "src/risk",                     # 第十九章
        
        # 测试（第1-19章）
        "tests/unit/chapter_1",
        "tests/unit/chapter_2",
        "tests/unit/chapter_3",
        "tests/unit/chapter_4",
        "tests/unit/chapter_5",
        "tests/unit/chapter_6",
        "tests/unit/chapter_7",
        "tests/unit/chapter_8",         # 新增
        "tests/unit/chapter_9",         # 新增
        "tests/unit/chapter_10",        # 新增
        "tests/unit/chapter_11",        # 新增
        "tests/unit/chapter_12",        # 新增
        "tests/unit/chapter_13",        # 新增
        "tests/unit/chapter_14",        # 新增
        "tests/unit/chapter_15",        # 新增
        "tests/unit/chapter_16",        # 新增
        "tests/unit/chapter_17",        # 新增
        "tests/unit/chapter_18",        # 新增
        "tests/unit/chapter_19",        # 新增
        
        "tests/integration/chapter_1",
        "tests/integration/chapter_2",
        "tests/integration/chapter_3",
        "tests/integration/chapter_4",
        "tests/integration/chapter_5",
        "tests/integration/chapter_6",
        "tests/integration/chapter_7",
        "tests/integration/chapter_8",  # 新增
        "tests/integration/chapter_9",  # 新增
        "tests/integration/chapter_10", # 新增
        "tests/integration/chapter_11", # 新增
        "tests/integration/chapter_12", # 新增
        "tests/integration/chapter_13", # 新增
        "tests/integration/chapter_14", # 新增
        "tests/integration/chapter_15", # 新增
        "tests/integration/chapter_16", # 新增
        "tests/integration/chapter_17", # 新增
        "tests/integration/chapter_18", # 新增
        "tests/integration/chapter_19", # 新增
        
        "tests/e2e",
        "tests/performance",
        "tests/security",               # 新增
        
        # 数据
        "data/historical",
        "data/tick",
        "data/bar",
        "data/radar_archive",
        "data/exported_factors",
        "data/z2h_capsules",
        "data/z2h_meta_capsules",       # 新增
        "data/backups",
        
        # 模型
        "models/qwen-30b",
        "models/algo_hunter",
        "models/checkpoints",
        
        # 日志
        "logs/audit",
        "logs/trading",
        "logs/evolution",
        "logs/system",
        "logs/emergency",               # 新增
        
        # 文档
        "docs/_build",
        "docs/api",
        "docs/guides",
        "docs/roadmap",                 # 新增
        "docs/changelog",               # 新增
        "docs/emergency",               # 新增
        
        # Docker & K8s
        "docker",
        "k8s",                          # 新增
    ]
    
    # 创建目录
    for directory in directories:
        path = Path(directory)
        path.mkdir(parents=True, exist_ok=True)
        
        # 创建 __init__.py
        if directory.startswith("src/") or directory.startswith("tests/"):
            init_file = path / "__init__.py"
            if not init_file.exists():
                init_file.touch()
        
        # 创建 .gitkeep
        if directory.startswith("data/") or directory.startswith("models/") or directory.startswith("logs/"):
            gitkeep = path / ".gitkeep"
            if not gitkeep.exists():
                gitkeep.touch()
        
        print(f"✅ 创建目录: {directory}")
    
    print(f"\n🎉 目录结构创建完成！")
    print(f"   总计: {len(directories)} 个目录")
    print(f"   覆盖: 第1-19章完整内容")

if __name__ == "__main__":
    create_directory_structure()
```

---

## ✅ 目录结构检查清单

创建目录结构后，确认：

- [ ] 所有src/目录有__init__.py（14个主要模块）
- [ ] 所有tests/目录有__init__.py（19章 × 2类型 + 3额外类型）
- [ ] 所有data/目录有.gitkeep
- [ ] 所有models/目录有.gitkeep
- [ ] 所有logs/目录有.gitkeep
- [ ] .gitignore正确配置
- [ ] 目录权限正确
- [ ] Docker配置完整
- [ ] K8s配置完整（如果使用）
- [ ] 文档目录完整

---

**版本**: v2.0 (完整版)  
**更新日期**: 2026-01-16  
**覆盖章节**: 第1-19章（完整）  
**新增目录**: 第8-19章相关目录结构
