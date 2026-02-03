#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
全量模块调试脚本

覆盖项目所有23个主要模块的完整调试：
1. analysis - 分析模块
2. audit - 审计模块
3. base - 基础模块
4. brain - AI三脑系统
5. capital - 资金管理
6. chronos - 时序调度
7. compliance - 合规模块
8. config - 配置模块
9. core - 核心模块
10. evolution - 因子进化
11. execution - 执行模块
12. infra - 基础设施
13. integration - 集成模块
14. interface - 界面模块
15. monitoring - 监控模块
16. optimization - 优化模块
17. planning - 规划模块
18. quality - 质量模块
19. risk - 风控模块
20. scheduler - 调度模块
21. security - 安全模块
22. strategies - 策略模块
23. utils - 工具模块

使用方法：
    python scripts/debug_all_modules.py
"""

import sys
import os
import importlib
import traceback
from datetime import datetime
from typing import Dict, List, Tuple, Any
from dataclasses import dataclass
from enum import Enum

# 添加项目路径
sys.path.insert(0, '.')


class ModuleStatus(Enum):
    OK = "✅"
    WARN = "⚠️"
    ERROR = "❌"
    SKIP = "⏭️"


@dataclass
class ModuleResult:
    name: str
    status: ModuleStatus
    classes_loaded: int
    functions_loaded: int
    error: str = ""
    details: List[str] = None


class FullModuleDebugger:
    """全量模块调试器"""
    
    def __init__(self):
        self.results: Dict[str, List[ModuleResult]] = {}
        self.total_modules = 0
        self.total_classes = 0
        self.total_functions = 0
        self.errors: List[str] = []
        
    def log(self, msg: str, level: str = "INFO"):
        """日志输出"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        prefix = {
            "INFO": "ℹ️", "OK": "✅", "WARN": "⚠️", 
            "ERROR": "❌", "DEBUG": "🔍", "SECTION": "📦"
        }
        print(f"[{timestamp}] {prefix.get(level, '•')} {msg}")

    def try_import_module(self, module_path: str) -> Tuple[bool, Any, str]:
        """尝试导入模块"""
        try:
            module = importlib.import_module(module_path)
            return True, module, ""
        except Exception as e:
            return False, None, str(e)

    def analyze_module(self, module) -> Tuple[int, int, List[str]]:
        """分析模块内容"""
        classes = []
        functions = []
        details = []
        
        for name in dir(module):
            if name.startswith('_'):
                continue
            obj = getattr(module, name)
            if isinstance(obj, type):
                classes.append(name)
                details.append(f"  class {name}")
            elif callable(obj):
                functions.append(name)
        
        return len(classes), len(functions), details

    def debug_module_file(self, base_path: str, file_name: str) -> ModuleResult:
        """调试单个模块文件"""
        module_name = file_name.replace('.py', '')
        module_path = f"{base_path}.{module_name}"
        
        success, module, error = self.try_import_module(module_path)
        
        if not success:
            return ModuleResult(
                name=module_name,
                status=ModuleStatus.ERROR,
                classes_loaded=0,
                functions_loaded=0,
                error=error
            )
        
        classes, functions, details = self.analyze_module(module)
        
        return ModuleResult(
            name=module_name,
            status=ModuleStatus.OK,
            classes_loaded=classes,
            functions_loaded=functions,
            details=details
        )

    # ========================================================================
    # 各模块调试方法
    # ========================================================================

    def debug_analysis(self):
        """1. 分析模块"""
        self.log("=" * 60)
        self.log("1. 分析模块 (src/analysis)", "SECTION")
        self.log("=" * 60)
        
        modules = [
            ("darwin_integration", "Darwin进化集成"),
            ("knowledge_base", "知识库"),
            ("visualization_dashboard", "可视化仪表板"),
        ]
        
        results = []
        for mod_name, desc in modules:
            result = self.debug_module_file("src.analysis", f"{mod_name}.py")
            self.log(f"{result.status.value} {mod_name}: {desc} (类:{result.classes_loaded}, 函数:{result.functions_loaded})")
            if result.error:
                self.log(f"   错误: {result.error[:80]}", "ERROR")
            results.append(result)
        
        self.results["analysis"] = results

    def debug_audit(self):
        """2. 审计模块"""
        self.log("=" * 60)
        self.log("2. 审计模块 (src/audit)", "SECTION")
        self.log("=" * 60)
        
        modules = [
            ("auditor", "审计器"),
            ("audit_logger", "审计日志"),
            ("data_models", "数据模型"),
        ]
        
        results = []
        for mod_name, desc in modules:
            result = self.debug_module_file("src.audit", f"{mod_name}.py")
            self.log(f"{result.status.value} {mod_name}: {desc} (类:{result.classes_loaded}, 函数:{result.functions_loaded})")
            if result.error:
                self.log(f"   错误: {result.error[:80]}", "ERROR")
            results.append(result)
        
        self.results["audit"] = results

    def debug_base(self):
        """3. 基础模块"""
        self.log("=" * 60)
        self.log("3. 基础模块 (src/base)", "SECTION")
        self.log("=" * 60)
        
        modules = [
            ("exceptions", "异常定义"),
            ("models", "基础模型"),
        ]
        
        results = []
        for mod_name, desc in modules:
            result = self.debug_module_file("src.base", f"{mod_name}.py")
            self.log(f"{result.status.value} {mod_name}: {desc} (类:{result.classes_loaded}, 函数:{result.functions_loaded})")
            if result.error:
                self.log(f"   错误: {result.error[:80]}", "ERROR")
            results.append(result)
        
        self.results["base"] = results

    def debug_brain(self):
        """4. AI三脑系统"""
        self.log("=" * 60)
        self.log("4. AI三脑系统 (src/brain)", "SECTION")
        self.log("=" * 60)
        
        modules = [
            ("adaptive_batch_scheduler", "自适应批处理调度器"),
            ("ai_brain_coordinator", "AI脑协调器"),
            ("anti_pattern_library", "反模式库"),
            ("cache_manager", "缓存管理器"),
            ("chapter2_integration", "第二章集成"),
            ("commander_capital_integration", "Commander资金集成"),
            ("commander_engine_v2", "Commander引擎V2"),
            ("darwin_data_models", "Darwin数据模型"),
            ("darwin_system", "Darwin系统"),
            ("deepseek_client", "DeepSeek客户端"),
            ("devil_auditor", "魔鬼审计器"),
            ("dual_architecture_runner", "双架构运行器"),
            ("evolution_tree", "进化树"),
            ("gene_capsule_manager", "基因胶囊管理器"),
            ("hallucination_filter", "幻觉过滤器"),
            ("hybrid_risk_control", "混合风控"),
            ("intelligent_risk_control_router", "智能风控路由"),
            ("interfaces", "接口定义"),
            ("learning_data_store", "学习数据存储"),
            ("llm_gateway", "LLM网关"),
            ("llm_local_inference", "本地LLM推理"),
            ("portfolio_doctor", "组合医生"),
            ("prompt_engineer", "提示工程师"),
            ("prompt_engineering", "提示工程"),
            ("prompt_evolution", "提示进化"),
            ("redis_storage", "Redis存储"),
            ("regime_engine", "市场状态引擎"),
            ("risk_control_meta_learner", "风控元学习器"),
            ("scholar_engine_v2", "Scholar引擎V2"),
            ("sentiment_sentinel", "情绪哨兵"),
            ("soldier_engine_v2", "Soldier引擎V2"),
            ("soldier_failover", "Soldier故障转移"),
            ("vllm_inference_engine", "vLLM推理引擎"),
            ("vllm_memory_coordinator", "vLLM内存协调器"),
        ]
        
        results = []
        for mod_name, desc in modules:
            result = self.debug_module_file("src.brain", f"{mod_name}.py")
            self.log(f"{result.status.value} {mod_name}: {desc} (类:{result.classes_loaded}, 函数:{result.functions_loaded})")
            if result.error:
                self.log(f"   错误: {result.error[:80]}", "ERROR")
            results.append(result)
        
        self.results["brain"] = results

    def debug_capital(self):
        """5. 资金管理模块"""
        self.log("=" * 60)
        self.log("5. 资金管理模块 (src/capital)", "SECTION")
        self.log("=" * 60)
        
        modules = [
            ("aum_sensor", "AUM传感器"),
            ("capital_allocator", "资金分配器"),
            ("strategy_selector", "策略选择器"),
            ("tier", "资金层级"),
            ("weight_adjuster", "权重调整器"),
        ]
        
        results = []
        for mod_name, desc in modules:
            result = self.debug_module_file("src.capital", f"{mod_name}.py")
            self.log(f"{result.status.value} {mod_name}: {desc} (类:{result.classes_loaded}, 函数:{result.functions_loaded})")
            if result.error:
                self.log(f"   错误: {result.error[:80]}", "ERROR")
            results.append(result)
        
        self.results["capital"] = results

    def debug_chronos(self):
        """6. 时序调度模块"""
        self.log("=" * 60)
        self.log("6. 时序调度模块 (src/chronos)", "SECTION")
        self.log("=" * 60)
        
        modules = [
            ("clock_sync", "时钟同步"),
            ("gpu_watchdog", "GPU看门狗"),
            ("orchestrator", "编排器"),
            ("scheduler", "调度器"),
            ("services", "服务"),
            ("websocket_server", "WebSocket服务器"),
        ]
        
        results = []
        for mod_name, desc in modules:
            result = self.debug_module_file("src.chronos", f"{mod_name}.py")
            self.log(f"{result.status.value} {mod_name}: {desc} (类:{result.classes_loaded}, 函数:{result.functions_loaded})")
            if result.error:
                self.log(f"   错误: {result.error[:80]}", "ERROR")
            results.append(result)
        
        self.results["chronos"] = results

    def debug_compliance(self):
        """7. 合规模块"""
        self.log("=" * 60)
        self.log("7. 合规模块 (src/compliance)", "SECTION")
        self.log("=" * 60)
        
        modules = [
            ("ast_validator", "AST验证器"),
            ("data_models", "数据模型"),
            ("data_privacy_manager", "数据隐私管理器"),
            ("docker_sandbox", "Docker沙箱"),
            ("documentation_sync_checker", "文档同步检查器"),
            ("doomsday_monitor", "末日监控器"),
            ("engineering_law_validator", "工程法则验证器"),
            ("network_guard", "网络守卫"),
            ("trading_compliance_manager", "交易合规管理器"),
            ("unified_security_gateway", "统一安全网关"),
        ]
        
        results = []
        for mod_name, desc in modules:
            result = self.debug_module_file("src.compliance", f"{mod_name}.py")
            self.log(f"{result.status.value} {mod_name}: {desc} (类:{result.classes_loaded}, 函数:{result.functions_loaded})")
            if result.error:
                self.log(f"   错误: {result.error[:80]}", "ERROR")
            results.append(result)
        
        self.results["compliance"] = results

    def debug_core(self):
        """9. 核心模块"""
        self.log("=" * 60)
        self.log("9. 核心模块 (src/core)", "SECTION")
        self.log("=" * 60)
        
        modules = [
            ("daemon_manager", "守护进程管理器"),
            ("dependency_container", "依赖注入容器"),
            ("doomsday_switch", "末日开关"),
            ("exceptions", "异常定义"),
            ("fund_monitor", "资金监控器"),
            ("gpu_watchdog", "GPU看门狗"),
            ("health_checker", "健康检查器"),
            ("lockbox_manager", "锁箱管理器"),
        ]
        
        results = []
        for mod_name, desc in modules:
            result = self.debug_module_file("src.core", f"{mod_name}.py")
            self.log(f"{result.status.value} {mod_name}: {desc} (类:{result.classes_loaded}, 函数:{result.functions_loaded})")
            if result.error:
                self.log(f"   错误: {result.error[:80]}", "ERROR")
            results.append(result)
        
        self.results["core"] = results

    def debug_evolution(self):
        """10. 因子进化模块"""
        self.log("=" * 60)
        self.log("10. 因子进化模块 (src/evolution)", "SECTION")
        self.log("=" * 60)
        
        modules = [
            ("ai_enhanced_miner", "AI增强挖掘器"),
            ("algorithm_evolution_sentinel", "算法进化哨兵"),
            ("alternative_data_miner", "另类数据挖掘器"),
            ("arena_test_manager", "竞技场测试管理器"),
            ("capital_allocation_rules_determiner", "资金分配规则决定器"),
            ("certification_api_gateway", "认证API网关"),
            ("certification_config_manager", "认证配置管理器"),
            ("certification_failure_analyzer", "认证失败分析器"),
            ("certification_level_evaluator", "认证级别评估器"),
            ("certification_notification_service", "认证通知服务"),
            ("certification_performance_monitor", "认证性能监控"),
            ("certification_persistence_service", "认证持久化服务"),
            ("certification_state_manager", "认证状态管理器"),
            ("certification_traceability", "认证可追溯性"),
            ("commander_factor_decision", "Commander因子决策"),
            ("enhanced_illiquidity_miner", "增强流动性挖掘器"),
            ("error_handling", "错误处理"),
            ("esg_intelligence_miner", "ESG智能挖掘器"),
            ("event_driven_miner", "事件驱动挖掘器"),
            ("expression_ast", "表达式AST"),
            ("expression_types", "表达式类型"),
            ("factor_arena", "因子竞技场"),
            ("factor_combination_interaction_miner", "因子组合交互挖掘器"),
            ("factor_data_models", "因子数据模型"),
            ("factor_lifecycle_manager", "因子生命周期管理器"),
            ("factor_mining_intelligence_sentinel", "因子挖掘智能哨兵"),
            ("factor_to_strategy_converter", "因子转策略转换器"),
            ("four_tier_z2h_certification", "四层Z2H认证"),
            ("genetic_miner", "遗传挖掘器"),
            ("high_frequency_microstructure_miner", "高频微结构挖掘器"),
            ("live_strategy_loader", "实盘策略加载器"),
            ("macro_cross_asset_miner", "宏观跨资产挖掘器"),
            ("meta_miner", "元挖掘器"),
            ("ml_feature_engineering_miner", "ML特征工程挖掘器"),
            ("multi_market_adaptation", "多市场适应"),
            ("multi_objective", "多目标优化"),
            ("multi_tier_simulation_manager", "多层模拟管理器"),
            ("network_relationship_miner", "网络关系挖掘器"),
            ("price_volume_relationship_miner", "量价关系挖掘器"),
            ("qmt_broker_api", "QMT券商API"),
            ("relative_performance_evaluator", "相对绩效评估器"),
            ("reverse_evolution", "逆向进化"),
            ("rolling_backtest", "滚动回测"),
            ("sentiment_behavior_miner", "情绪行为挖掘器"),
            ("simulation_manager", "模拟管理器"),
            ("sparta_arena", "斯巴达竞技场"),
            ("sparta_arena_evaluator", "斯巴达竞技场评估器"),
            ("sparta_arena_standards", "斯巴达竞技场标准"),
            ("strategy_evaluator", "策略评估器"),
            ("strategy_library_manager", "策略库管理器"),
            ("stress_test_analyzer", "压力测试分析器"),
            ("style_rotation_miner", "风格轮动挖掘器"),
            ("time_series_dl_miner", "时序深度学习挖掘器"),
            ("unified_factor_mining_system", "统一因子挖掘系统"),
            ("walk_forward_analysis", "前向分析"),
            ("z2h_certification", "Z2H认证"),
            ("z2h_certification_pipeline", "Z2H认证管道"),
            ("z2h_certification_v2", "Z2H认证V2"),
            ("z2h_data_models", "Z2H数据模型"),
        ]
        
        results = []
        for mod_name, desc in modules:
            result = self.debug_module_file("src.evolution", f"{mod_name}.py")
            self.log(f"{result.status.value} {mod_name}: {desc} (类:{result.classes_loaded}, 函数:{result.functions_loaded})")
            if result.error:
                self.log(f"   错误: {result.error[:80]}", "ERROR")
            results.append(result)
        
        self.results["evolution"] = results

    def debug_execution(self):
        """11. 执行模块"""
        self.log("=" * 60)
        self.log("11. 执行模块 (src/execution)", "SECTION")
        self.log("=" * 60)
        
        modules = [
            ("lockbox", "锁箱"),
            ("margin_watchdog", "保证金看门狗"),
            ("market_data", "市场数据"),
            ("multi_account_data_models", "多账户数据模型"),
            ("multi_account_manager", "多账户管理器"),
            ("order_manager", "订单管理器"),
            ("order_risk_integration", "订单风控集成"),
            ("risk_control_system", "风控系统"),
        ]
        
        results = []
        for mod_name, desc in modules:
            result = self.debug_module_file("src.execution", f"{mod_name}.py")
            self.log(f"{result.status.value} {mod_name}: {desc} (类:{result.classes_loaded}, 函数:{result.functions_loaded})")
            if result.error:
                self.log(f"   错误: {result.error[:80]}", "ERROR")
            results.append(result)
        
        self.results["execution"] = results

    def debug_infra(self):
        """12. 基础设施模块"""
        self.log("=" * 60)
        self.log("12. 基础设施模块 (src/infra)", "SECTION")
        self.log("=" * 60)
        
        modules = [
            ("bar_synthesizer", "K线合成器"),
            ("bridge", "桥接器"),
            ("cache_manager", "缓存管理器"),
            ("contract_stitcher", "合约拼接器"),
            ("cross_chapter_event_bus", "跨章节事件总线"),
            ("data_archiver", "数据归档器"),
            ("data_completeness_checker", "数据完整性检查器"),
            ("data_downloader", "数据下载器"),
            ("data_exceptions", "数据异常"),
            ("data_models", "数据模型"),
            ("data_preheater", "数据预热器"),
            ("data_probe", "数据探针"),
            ("data_sanitizer", "数据清洗器"),
            ("derivatives_validator", "衍生品验证器"),
            ("event_bus", "事件总线"),
            ("future_config", "期货配置"),
            ("greeks_engine", "希腊字母引擎"),
            ("ipc_protocol", "IPC协议"),
            ("path_manager", "路径管理器"),
            ("pipeline", "数据管道"),
            ("radar_archiver", "雷达归档器"),
            ("redis_pubsub", "Redis发布订阅"),
            ("resilient_redis_pool", "弹性Redis池"),
            ("sanitizer", "清洗器"),
            ("service_discovery", "服务发现"),
            ("shared_memory", "共享内存"),
            ("spsc_buffer", "SPSC缓冲区"),
            ("spsc_manager", "SPSC管理器"),
            ("spsc_queue", "SPSC队列"),
            ("websocket_bridge_server", "WebSocket桥接服务器"),
        ]
        
        results = []
        for mod_name, desc in modules:
            result = self.debug_module_file("src.infra", f"{mod_name}.py")
            self.log(f"{result.status.value} {mod_name}: {desc} (类:{result.classes_loaded}, 函数:{result.functions_loaded})")
            if result.error:
                self.log(f"   错误: {result.error[:80]}", "ERROR")
            results.append(result)
        
        self.results["infra"] = results

    def debug_integration(self):
        """13. 集成模块"""
        self.log("=" * 60)
        self.log("13. 集成模块 (src/integration)", "SECTION")
        self.log("=" * 60)
        
        modules = [
            ("cost_monitoring_integration", "成本监控集成"),
            ("monitoring_reliability_integration", "监控可靠性集成"),
            ("risk_emergency_integration", "风险应急集成"),
            ("scheduler_pipeline", "调度管道"),
            ("testing_cicd_integration", "测试CI/CD集成"),
        ]
        
        results = []
        for mod_name, desc in modules:
            result = self.debug_module_file("src.integration", f"{mod_name}.py")
            self.log(f"{result.status.value} {mod_name}: {desc} (类:{result.classes_loaded}, 函数:{result.functions_loaded})")
            if result.error:
                self.log(f"   错误: {result.error[:80]}", "ERROR")
            results.append(result)
        
        self.results["integration"] = results

    def debug_interface(self):
        """14. 界面模块"""
        self.log("=" * 60)
        self.log("14. 界面模块 (src/interface)", "SECTION")
        self.log("=" * 60)
        
        modules = [
            ("access_control", "访问控制"),
            ("auditor_dashboard", "审计仪表板"),
            ("cockpit_dashboard", "驾驶舱仪表板"),
            ("derivatives_lab_dashboard", "衍生品实验室仪表板"),
            ("evolution_dashboard", "进化仪表板"),
            ("health_api", "健康API"),
            ("library_dashboard", "库仪表板"),
            ("multi_account_dashboard", "多账户仪表板"),
            ("portfolio_dashboard", "组合仪表板"),
            ("radar_dashboard", "雷达仪表板"),
            ("scanner_dashboard", "扫描仪表板"),
            ("system_dashboard", "系统仪表板"),
            ("tactical_dashboard", "战术仪表板"),
            ("ui_pro_max", "UI Pro Max"),
            ("ui_theme", "UI主题"),
            ("watchlist_dashboard", "自选股仪表板"),
        ]
        
        results = []
        for mod_name, desc in modules:
            result = self.debug_module_file("src.interface", f"{mod_name}.py")
            self.log(f"{result.status.value} {mod_name}: {desc} (类:{result.classes_loaded}, 函数:{result.functions_loaded})")
            if result.error:
                self.log(f"   错误: {result.error[:80]}", "ERROR")
            results.append(result)
        
        self.results["interface"] = results

    def debug_monitoring(self):
        """15. 监控模块"""
        self.log("=" * 60)
        self.log("15. 监控模块 (src/monitoring)", "SECTION")
        self.log("=" * 60)
        
        modules = [
            ("alert_manager", "告警管理器"),
            ("circuit_breaker", "熔断器"),
            ("circuit_breaker_costs", "熔断器成本"),
            ("cost_predictor", "成本预测器"),
            ("cost_reporter", "成本报告器"),
            ("cost_tracker", "成本追踪器"),
            ("performance_monitor", "性能监控器"),
            ("prometheus_collector", "Prometheus收集器"),
        ]
        
        results = []
        for mod_name, desc in modules:
            result = self.debug_module_file("src.monitoring", f"{mod_name}.py")
            self.log(f"{result.status.value} {mod_name}: {desc} (类:{result.classes_loaded}, 函数:{result.functions_loaded})")
            if result.error:
                self.log(f"   错误: {result.error[:80]}", "ERROR")
            results.append(result)
        
        self.results["monitoring"] = results

    def debug_optimization(self):
        """16. 优化模块"""
        self.log("=" * 60)
        self.log("16. 优化模块 (src/optimization)", "SECTION")
        self.log("=" * 60)
        
        modules = [
            ("cost_optimizer", "成本优化器"),
            ("performance_optimizer", "性能优化器"),
        ]
        
        results = []
        for mod_name, desc in modules:
            result = self.debug_module_file("src.optimization", f"{mod_name}.py")
            self.log(f"{result.status.value} {mod_name}: {desc} (类:{result.classes_loaded}, 函数:{result.functions_loaded})")
            if result.error:
                self.log(f"   错误: {result.error[:80]}", "ERROR")
            results.append(result)
        
        self.results["optimization"] = results

    def debug_planning(self):
        """17. 规划模块"""
        self.log("=" * 60)
        self.log("17. 规划模块 (src/planning)", "SECTION")
        self.log("=" * 60)
        
        modules = [
            ("architecture_evolution_planner", "架构进化规划器"),
            ("feature_prioritizer", "功能优先级排序器"),
        ]
        
        results = []
        for mod_name, desc in modules:
            result = self.debug_module_file("src.planning", f"{mod_name}.py")
            self.log(f"{result.status.value} {mod_name}: {desc} (类:{result.classes_loaded}, 函数:{result.functions_loaded})")
            if result.error:
                self.log(f"   错误: {result.error[:80]}", "ERROR")
            results.append(result)
        
        self.results["planning"] = results

    def debug_quality(self):
        """18. 质量模块"""
        self.log("=" * 60)
        self.log("18. 质量模块 (src/quality)", "SECTION")
        self.log("=" * 60)
        
        modules = [
            ("cmm_maturity_assessor", "CMM成熟度评估器"),
            ("code_quality_checker", "代码质量检查器"),
            ("test_coverage_analyzer", "测试覆盖率分析器"),
        ]
        
        results = []
        for mod_name, desc in modules:
            result = self.debug_module_file("src.quality", f"{mod_name}.py")
            self.log(f"{result.status.value} {mod_name}: {desc} (类:{result.classes_loaded}, 函数:{result.functions_loaded})")
            if result.error:
                self.log(f"   错误: {result.error[:80]}", "ERROR")
            results.append(result)
        
        self.results["quality"] = results

    def debug_risk(self):
        """19. 风控模块"""
        self.log("=" * 60)
        self.log("19. 风控模块 (src/risk)", "SECTION")
        self.log("=" * 60)
        
        modules = [
            ("emergency_response_system", "应急响应系统"),
            ("risk_control_matrix", "风控矩阵"),
            ("risk_identification_system", "风险识别系统"),
            ("risk_monitor", "风险监控器"),
        ]
        
        results = []
        for mod_name, desc in modules:
            result = self.debug_module_file("src.risk", f"{mod_name}.py")
            self.log(f"{result.status.value} {mod_name}: {desc} (类:{result.classes_loaded}, 函数:{result.functions_loaded})")
            if result.error:
                self.log(f"   错误: {result.error[:80]}", "ERROR")
            results.append(result)
        
        self.results["risk"] = results

    def debug_security(self):
        """21. 安全模块"""
        self.log("=" * 60)
        self.log("21. 安全模块 (src/security)", "SECTION")
        self.log("=" * 60)
        
        modules = [
            ("auth_manager", "认证管理器"),
            ("data_models", "数据模型"),
            ("secure_config", "安全配置"),
        ]
        
        results = []
        for mod_name, desc in modules:
            result = self.debug_module_file("src.security", f"{mod_name}.py")
            self.log(f"{result.status.value} {mod_name}: {desc} (类:{result.classes_loaded}, 函数:{result.functions_loaded})")
            if result.error:
                self.log(f"   错误: {result.error[:80]}", "ERROR")
            results.append(result)
        
        self.results["security"] = results

    def debug_strategies(self):
        """22. 策略模块"""
        self.log("=" * 60)
        self.log("22. 策略模块 (src/strategies)", "SECTION")
        self.log("=" * 60)
        
        modules = [
            ("base_strategy", "基础策略"),
            ("data_models", "数据模型"),
            ("signal_aggregator", "信号聚合器"),
            ("smart_position_builder", "智能仓位构建器"),
            ("strategy_risk_manager", "策略风险管理器"),
        ]
        
        results = []
        for mod_name, desc in modules:
            result = self.debug_module_file("src.strategies", f"{mod_name}.py")
            self.log(f"{result.status.value} {mod_name}: {desc} (类:{result.classes_loaded}, 函数:{result.functions_loaded})")
            if result.error:
                self.log(f"   错误: {result.error[:80]}", "ERROR")
            results.append(result)
        
        self.results["strategies"] = results

    def debug_utils(self):
        """23. 工具模块"""
        self.log("=" * 60)
        self.log("23. 工具模块 (src/utils)", "SECTION")
        self.log("=" * 60)
        
        modules = [
            ("logger", "日志工具"),
        ]
        
        results = []
        for mod_name, desc in modules:
            result = self.debug_module_file("src.utils", f"{mod_name}.py")
            self.log(f"{result.status.value} {mod_name}: {desc} (类:{result.classes_loaded}, 函数:{result.functions_loaded})")
            if result.error:
                self.log(f"   错误: {result.error[:80]}", "ERROR")
            results.append(result)
        
        self.results["utils"] = results

    # ========================================================================
    # 主调试流程
    # ========================================================================
    
    def run_full_debug(self):
        """运行全量调试"""
        start_time = datetime.now()
        
        self.log("=" * 70)
        self.log("🚀 MIA项目全量模块调试", "INFO")
        self.log(f"开始时间: {start_time.isoformat()}")
        self.log("=" * 70)
        print()
        
        # 依次调试所有模块
        self.debug_analysis()      # 1
        print()
        self.debug_audit()         # 2
        print()
        self.debug_base()          # 3
        print()
        self.debug_brain()         # 4
        print()
        self.debug_capital()       # 5
        print()
        self.debug_chronos()       # 6
        print()
        self.debug_compliance()    # 7
        print()
        self.debug_core()          # 9
        print()
        self.debug_evolution()     # 10
        print()
        self.debug_execution()     # 11
        print()
        self.debug_infra()         # 12
        print()
        self.debug_integration()   # 13
        print()
        self.debug_interface()     # 14
        print()
        self.debug_monitoring()    # 15
        print()
        self.debug_optimization()  # 16
        print()
        self.debug_planning()      # 17
        print()
        self.debug_quality()       # 18
        print()
        self.debug_risk()          # 19
        print()
        self.debug_security()      # 21
        print()
        self.debug_strategies()    # 22
        print()
        self.debug_utils()         # 23
        print()
        
        # 输出总结
        end_time = datetime.now()
        self.print_summary(start_time, end_time)

    def print_summary(self, start_time: datetime, end_time: datetime):
        """输出调试总结"""
        self.log("=" * 70)
        self.log("📊 全量调试总结", "INFO")
        self.log("=" * 70)
        
        total_modules = 0
        total_ok = 0
        total_error = 0
        total_classes = 0
        total_functions = 0
        
        print()
        print("┌" + "─" * 68 + "┐")
        print(f"│ {'模块包':<20} │ {'总数':>6} │ {'通过':>6} │ {'失败':>6} │ {'类':>6} │ {'函数':>6} │")
        print("├" + "─" * 68 + "┤")
        
        for pkg_name, results in self.results.items():
            pkg_total = len(results)
            pkg_ok = sum(1 for r in results if r.status == ModuleStatus.OK)
            pkg_error = pkg_total - pkg_ok
            pkg_classes = sum(r.classes_loaded for r in results)
            pkg_functions = sum(r.functions_loaded for r in results)
            
            total_modules += pkg_total
            total_ok += pkg_ok
            total_error += pkg_error
            total_classes += pkg_classes
            total_functions += pkg_functions
            
            status = "✅" if pkg_error == 0 else "❌"
            print(f"│ {status} {pkg_name:<17} │ {pkg_total:>6} │ {pkg_ok:>6} │ {pkg_error:>6} │ {pkg_classes:>6} │ {pkg_functions:>6} │")
        
        print("├" + "─" * 68 + "┤")
        print(f"│ {'合计':<20} │ {total_modules:>6} │ {total_ok:>6} │ {total_error:>6} │ {total_classes:>6} │ {total_functions:>6} │")
        print("└" + "─" * 68 + "┘")
        
        print()
        duration = (end_time - start_time).total_seconds()
        success_rate = (total_ok / total_modules * 100) if total_modules > 0 else 0
        
        print(f"📈 统计信息:")
        print(f"   • 总模块数: {total_modules}")
        print(f"   • 成功加载: {total_ok} ({success_rate:.1f}%)")
        print(f"   • 加载失败: {total_error}")
        print(f"   • 总类数量: {total_classes}")
        print(f"   • 总函数数: {total_functions}")
        print(f"   • 耗时: {duration:.2f}秒")
        
        # 输出失败模块详情
        if total_error > 0:
            print()
            self.log("失败模块详情:", "ERROR")
            for pkg_name, results in self.results.items():
                for r in results:
                    if r.status == ModuleStatus.ERROR:
                        print(f"   ❌ {pkg_name}.{r.name}: {r.error[:60]}...")
        
        print()
        if total_error == 0:
            self.log(f"🎉 全部 {total_modules} 个模块调试通过！", "OK")
        else:
            self.log(f"⚠️ {total_error} 个模块需要修复", "WARN")


def main():
    debugger = FullModuleDebugger()
    debugger.run_full_debug()


if __name__ == "__main__":
    main()
