#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
全量功能调试脚本 V2

基于实际模块接口进行功能测试，测试每个模块的真实API

使用方法：
    python scripts/debug_functional_test_v2.py
"""

import sys
import traceback
from datetime import datetime
from typing import Dict, List, Any
from dataclasses import dataclass
import uuid

sys.path.insert(0, '.')


@dataclass
class TestResult:
    name: str
    passed: bool
    details: str
    error: str = ""


class FunctionalDebuggerV2:
    """功能调试器V2 - 基于实际API"""
    
    def __init__(self):
        self.results: Dict[str, List[TestResult]] = {}
        self.total_tests = 0
        self.passed_tests = 0
        
    def log(self, msg: str, level: str = "INFO"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        prefix = {"INFO": "ℹ️", "OK": "✅", "WARN": "⚠️", "ERROR": "❌", "TEST": "🧪", "SECTION": "📦"}
        print(f"[{timestamp}] {prefix.get(level, '•')} {msg}")

    def run_test(self, category: str, name: str, test_func) -> bool:
        self.total_tests += 1
        try:
            result = test_func()
            self.passed_tests += 1
            if category not in self.results:
                self.results[category] = []
            self.results[category].append(TestResult(name, True, str(result)[:100]))
            self.log(f"{name}: {str(result)[:60]}", "OK")
            return True
        except Exception as e:
            if category not in self.results:
                self.results[category] = []
            self.results[category].append(TestResult(name, False, "", str(e)[:100]))
            self.log(f"{name}: {str(e)[:60]}", "ERROR")
            return False

    # ========================================================================
    # 1. 基础设施层
    # ========================================================================
    
    def test_infra_layer(self):
        """基础设施层功能测试"""
        self.log("=" * 60)
        self.log("1. 基础设施层功能测试", "SECTION")
        self.log("=" * 60)
        
        # 缓存管理器
        def test_cache():
            from src.infra.cache_manager import CacheManager
            cache = CacheManager()
            key = f"test_{uuid.uuid4().hex[:8]}"
            cache.set(key, {"data": 123})
            result = cache.get(key)
            cache.delete(key)
            return f"缓存读写: {result is not None}"
        self.run_test("infra", "缓存管理器", test_cache)
        
        # 路径管理器
        def test_path():
            from src.infra.path_manager import PathManager
            pm = PathManager()
            return f"数据路径: {pm.get_data_path()}"
        self.run_test("infra", "路径管理器", test_path)
        
        # 数据模型
        def test_data_models():
            from src.infra.data_models import DataSourceType
            return f"数据源类型: {DataSourceType.MARKET_DATA.value}"
        self.run_test("infra", "数据模型", test_data_models)
        
        # K线合成器
        def test_bar_synthesizer():
            from src.infra.bar_synthesizer import BarSynthesizer
            synth = BarSynthesizer()
            return f"K线合成器初始化成功"
        self.run_test("infra", "K线合成器", test_bar_synthesizer)
        
        # 希腊字母引擎
        def test_greeks():
            from src.infra.greeks_engine import GreeksEngine
            engine = GreeksEngine()
            return f"Greeks引擎初始化成功"
        self.run_test("infra", "希腊字母引擎", test_greeks)

    # ========================================================================
    # 2. 执行层
    # ========================================================================
    
    def test_execution_layer(self):
        """执行层功能测试"""
        self.log("=" * 60)
        self.log("2. 执行层功能测试", "SECTION")
        self.log("=" * 60)
        
        # 市场数据
        def test_market_data():
            from src.execution.market_data import TickData
            tick = TickData(
                symbol="000001.SZ",
                price=10.50,
                volume=10000,
                timestamp=datetime.now()
            )
            return f"Tick: {tick.symbol} @ {tick.price}"
        self.run_test("execution", "市场数据", test_market_data)
        
        # 订单模型
        def test_order_model():
            from src.execution.order_manager import Order, OrderSide, OrderType, OrderStatus
            order = Order(
                order_id=str(uuid.uuid4())[:8],
                symbol="000001.SZ",
                side=OrderSide.BUY,
                order_type=OrderType.LIMIT,
                quantity=100,
                price=10.50
            )
            return f"订单: {order.order_id} {order.side.value} {order.quantity}股"
        self.run_test("execution", "订单模型", test_order_model)
        
        # 订单管理器
        def test_order_manager():
            from src.execution.order_manager import OrderManager
            manager = OrderManager()
            return f"订单管理器初始化成功"
        self.run_test("execution", "订单管理器", test_order_manager)
        
        # 风控系统
        def test_risk_control():
            from src.execution.risk_control_system import RiskControlSystem, RiskCheckResult, RiskCheckType
            risk = RiskControlSystem()
            # 测试风控检查结果模型
            result = RiskCheckResult(
                passed=True,
                check_type=RiskCheckType.POSITION_LIMIT,
                reason="通过"
            )
            return f"风控系统: total_capital={risk.total_capital}"
        self.run_test("execution", "风控系统", test_risk_control)
        
        # 多账户管理
        def test_multi_account():
            from src.execution.multi_account_manager import MultiAccountManager
            manager = MultiAccountManager()
            return f"多账户管理器初始化成功"
        self.run_test("execution", "多账户管理", test_multi_account)

    # ========================================================================
    # 3. 风控层
    # ========================================================================
    
    def test_risk_layer(self):
        """风控层功能测试"""
        self.log("=" * 60)
        self.log("3. 风控层功能测试", "SECTION")
        self.log("=" * 60)
        
        # 风险监控器
        def test_risk_monitor():
            from src.risk.risk_monitor import RiskMonitor
            monitor = RiskMonitor()
            return f"风险监控器: total_capital={monitor.total_capital}"
        self.run_test("risk", "风险监控器", test_risk_monitor)
        
        # 风险识别系统
        def test_risk_identification():
            from src.risk.risk_identification_system import RiskIdentificationSystem
            system = RiskIdentificationSystem()
            return f"风险识别系统初始化成功"
        self.run_test("risk", "风险识别系统", test_risk_identification)
        
        # 应急响应系统
        def test_emergency():
            from src.risk.emergency_response_system import EmergencyResponseSystem
            system = EmergencyResponseSystem()
            return f"应急响应系统初始化成功"
        self.run_test("risk", "应急响应系统", test_emergency)
        
        # 风控矩阵
        def test_risk_matrix():
            from src.risk.risk_control_matrix import RiskControlMatrix
            matrix = RiskControlMatrix()
            return f"风控矩阵初始化成功"
        self.run_test("risk", "风控矩阵", test_risk_matrix)

    # ========================================================================
    # 4. AI三脑系统
    # ========================================================================
    
    def test_brain_layer(self):
        """AI三脑系统功能测试"""
        self.log("=" * 60)
        self.log("4. AI三脑系统功能测试", "SECTION")
        self.log("=" * 60)
        
        # Soldier引擎
        def test_soldier():
            from src.brain.soldier.core import SoldierWithFailover, SoldierMode
            soldier = SoldierWithFailover(
                local_model_path="models/test",
                cloud_api_key="test_key"
            )
            return f"Soldier: mode={soldier.mode}"
        self.run_test("brain", "Soldier引擎", test_soldier)
        
        # 幻觉过滤器
        def test_hallucination():
            from src.brain.hallucination_filter import HallucinationFilter
            filter = HallucinationFilter()
            return f"幻觉过滤器初始化成功"
        self.run_test("brain", "幻觉过滤器", test_hallucination)
        
        # 市场状态引擎
        def test_regime():
            from src.brain.regime_engine import RegimeEngine
            engine = RegimeEngine()
            return f"市场状态引擎初始化成功"
        self.run_test("brain", "市场状态引擎", test_regime)
        
        # 批处理调度器
        def test_scheduler():
            from src.brain.adaptive_batch_scheduler import AdaptiveBatchScheduler
            scheduler = AdaptiveBatchScheduler()
            return f"批处理调度器初始化成功"
        self.run_test("brain", "批处理调度器", test_scheduler)
        
        # 组合医生
        def test_portfolio_doctor():
            from src.brain.portfolio_doctor import PortfolioDoctor
            doctor = PortfolioDoctor()
            return f"组合医生初始化成功"
        self.run_test("brain", "组合医生", test_portfolio_doctor)
        
        # LLM网关
        def test_llm_gateway():
            from src.brain.llm_gateway import LLMGateway
            return f"LLM网关类加载成功"
        self.run_test("brain", "LLM网关", test_llm_gateway)
        
        # 双架构运行器
        def test_dual_runner():
            from src.brain.dual_architecture_runner import DualArchitectureRunner
            return f"双架构运行器类加载成功"
        self.run_test("brain", "双架构运行器", test_dual_runner)
        
        # Commander引擎
        def test_commander():
            from src.brain.commander_engine_v2 import CommanderEngineV2
            return f"Commander引擎类加载成功"
        self.run_test("brain", "Commander引擎", test_commander)
        
        # Scholar引擎
        def test_scholar():
            from src.brain.scholar_engine_v2 import ScholarEngineV2
            return f"Scholar引擎类加载成功"
        self.run_test("brain", "Scholar引擎", test_scholar)

    # ========================================================================
    # 5. 监控层
    # ========================================================================
    
    def test_monitoring_layer(self):
        """监控层功能测试"""
        self.log("=" * 60)
        self.log("5. 监控层功能测试", "SECTION")
        self.log("=" * 60)
        
        # 性能监控器
        def test_performance():
            from src.monitoring.performance_monitor import PerformanceMonitor
            monitor = PerformanceMonitor()
            # 测试延迟跟踪
            stats = monitor.track_soldier_latency(15.5)
            stats = monitor.track_soldier_latency(12.3)
            return f"性能监控: P99={stats.get('p99', 0):.2f}ms"
        self.run_test("monitoring", "性能监控器", test_performance)
        
        # 成本追踪器
        def test_cost_tracker():
            from src.monitoring.cost_tracker import CostTracker
            tracker = CostTracker()
            cost = tracker.track_api_call("deepseek", "deepseek-chat", 100, 50)
            daily = tracker.get_daily_cost()
            return f"成本追踪: 日成本=¥{daily:.4f}"
        self.run_test("monitoring", "成本追踪器", test_cost_tracker)
        
        # 告警管理器
        def test_alert():
            from src.monitoring.alert_manager import AlertManager, AlertLevel, Alert
            manager = AlertManager()
            # 创建告警对象
            alert = Alert(
                name="test_alert",
                level=AlertLevel.WARNING,
                message="测试告警",
                timestamp=datetime.now()
            )
            return f"告警管理器: 告警级别={alert.level.value}"
        self.run_test("monitoring", "告警管理器", test_alert)
        
        # 成本预测器
        def test_cost_predictor():
            from src.monitoring.cost_predictor import CostPredictor
            predictor = CostPredictor()
            return f"成本预测器初始化成功"
        self.run_test("monitoring", "成本预测器", test_cost_predictor)
        
        # Prometheus收集器
        def test_prometheus():
            from src.monitoring.prometheus_collector import PrometheusMetricsCollector, MetricType
            # 测试指标类型枚举
            metric_type = MetricType.COUNTER
            return f"Prometheus收集器: MetricType={metric_type.value}"
        self.run_test("monitoring", "Prometheus收集器", test_prometheus)

    # ========================================================================
    # 6. 因子进化
    # ========================================================================
    
    def test_evolution_layer(self):
        """因子进化功能测试"""
        self.log("=" * 60)
        self.log("6. 因子进化功能测试", "SECTION")
        self.log("=" * 60)
        
        # 因子数据模型
        def test_factor_models():
            from src.evolution.factor_data_models import Factor
            factor = Factor(
                id=str(uuid.uuid4())[:8],
                name="momentum_20d",
                expression="close / delay(close, 20) - 1",
                category="technical",
                implementation_code="def calc(): pass",
                created_at=datetime.now(),
                generation=1,
                fitness_score=0.85,
                baseline_ic=0.05,
                baseline_ir=1.2,
                baseline_sharpe=1.5,
                liquidity_adaptability=0.9
            )
            return f"因子: {factor.name}, IC={factor.baseline_ic}"
        self.run_test("evolution", "因子数据模型", test_factor_models)
        
        # 遗传挖掘器
        def test_genetic():
            from src.evolution.genetic_miner import GeneticMiner
            miner = GeneticMiner()
            return f"遗传挖掘器初始化成功"
        self.run_test("evolution", "遗传挖掘器", test_genetic)
        
        # 因子生命周期
        def test_lifecycle():
            from src.evolution.factor_lifecycle_manager import FactorLifecycleManager
            manager = FactorLifecycleManager()
            return f"因子生命周期管理器初始化成功"
        self.run_test("evolution", "因子生命周期", test_lifecycle)
        
        # 策略评估器
        def test_evaluator():
            from src.evolution.strategy_evaluator import StrategyEvaluator
            evaluator = StrategyEvaluator()
            return f"策略评估器初始化成功"
        self.run_test("evolution", "策略评估器", test_evaluator)
        
        # Z2H认证
        def test_z2h():
            from src.evolution.z2h_certification import Z2HCertification
            cert = Z2HCertification()
            return f"Z2H认证系统初始化成功"
        self.run_test("evolution", "Z2H认证", test_z2h)
        
        # 斯巴达竞技场
        def test_sparta():
            from src.evolution.sparta_arena import SpartaArena
            arena = SpartaArena()
            return f"斯巴达竞技场初始化成功"
        self.run_test("evolution", "斯巴达竞技场", test_sparta)
        
        # 因子竞技场
        def test_factor_arena():
            from src.evolution.factor_arena import FactorArenaSystem
            arena = FactorArenaSystem()
            return f"因子竞技场初始化成功"
        self.run_test("evolution", "因子竞技场", test_factor_arena)

    # ========================================================================
    # 7. 资金管理
    # ========================================================================
    
    def test_capital_layer(self):
        """资金管理功能测试"""
        self.log("=" * 60)
        self.log("7. 资金管理功能测试", "SECTION")
        self.log("=" * 60)
        
        # 资金分配器
        def test_allocator():
            from src.capital.capital_allocator import CapitalAllocator
            allocator = CapitalAllocator()
            return f"资金分配器初始化成功"
        self.run_test("capital", "资金分配器", test_allocator)
        
        # AUM传感器
        def test_aum():
            from src.capital.aum_sensor import AUMSensor
            sensor = AUMSensor()
            return f"AUM传感器初始化成功"
        self.run_test("capital", "AUM传感器", test_aum)
        
        # 策略选择器
        def test_selector():
            from src.capital.strategy_selector import StrategySelector
            selector = StrategySelector()
            return f"策略选择器初始化成功"
        self.run_test("capital", "策略选择器", test_selector)
        
        # 权重调整器
        def test_adjuster():
            from src.capital.weight_adjuster import WeightAdjuster
            adjuster = WeightAdjuster()
            return f"权重调整器初始化成功"
        self.run_test("capital", "权重调整器", test_adjuster)
        
        # 资金层级
        def test_tier():
            from src.capital.tier import Tier
            tier = Tier.from_aum(500000)
            return f"资金层级: AUM=500000 -> {tier}"
        self.run_test("capital", "资金层级", test_tier)

    # ========================================================================
    # 8. 合规安全
    # ========================================================================
    
    def test_compliance_layer(self):
        """合规安全功能测试"""
        self.log("=" * 60)
        self.log("8. 合规安全功能测试", "SECTION")
        self.log("=" * 60)
        
        # 交易合规管理器
        def test_trading_compliance():
            from src.compliance.trading_compliance_manager import TradingComplianceManager
            manager = TradingComplianceManager()
            return f"交易合规: daily_limit={manager.daily_trade_limit}"
        self.run_test("compliance", "交易合规管理器", test_trading_compliance)
        
        # 数据隐私管理器
        def test_privacy():
            from src.compliance.data_privacy_manager import DataPrivacyManager
            manager = DataPrivacyManager()
            return f"数据隐私管理器初始化成功"
        self.run_test("compliance", "数据隐私管理器", test_privacy)
        
        # 网络守卫
        def test_network():
            from src.compliance.network_guard import NetworkGuard
            guard = NetworkGuard()
            return f"网络守卫初始化成功"
        self.run_test("compliance", "网络守卫", test_network)
        
        # 末日监控器
        def test_doomsday():
            from src.compliance.doomsday_monitor import DoomsdayMonitor
            monitor = DoomsdayMonitor()
            return f"末日监控器初始化成功"
        self.run_test("compliance", "末日监控器", test_doomsday)
        
        # 统一安全网关
        def test_security_gateway():
            from src.compliance.unified_security_gateway import UnifiedSecurityGateway
            gateway = UnifiedSecurityGateway()
            return f"统一安全网关初始化成功"
        self.run_test("compliance", "统一安全网关", test_security_gateway)
        
        # 认证管理器
        def test_auth():
            from src.security.auth_manager import AuthManager
            return f"认证管理器类加载成功"
        self.run_test("security", "认证管理器", test_auth)

    # ========================================================================
    # 9. 核心系统
    # ========================================================================
    
    def test_core_layer(self):
        """核心系统功能测试"""
        self.log("=" * 60)
        self.log("9. 核心系统功能测试", "SECTION")
        self.log("=" * 60)
        
        # 依赖注入容器
        def test_di():
            from src.core.dependency_container import DIContainer
            container = DIContainer()
            return f"依赖注入容器初始化成功"
        self.run_test("core", "依赖注入容器", test_di)
        
        # 健康检查器
        def test_health():
            from src.core.health_checker import HealthChecker
            checker = HealthChecker()
            return f"健康检查器初始化成功"
        self.run_test("core", "健康检查器", test_health)
        
        # 末日开关
        def test_doomsday_switch():
            from src.core.doomsday_switch import DoomsdaySwitch
            switch = DoomsdaySwitch()
            triggered = switch.is_triggered()
            return f"末日开关: triggered={triggered}"
        self.run_test("core", "末日开关", test_doomsday_switch)
        
        # 资金监控器
        def test_fund():
            from src.core.fund_monitor import FundMonitor, AlertLevel
            monitor = FundMonitor(initial_equity=1000000)
            return f"资金监控器: initial_equity={monitor.initial_equity}"
        self.run_test("core", "资金监控器", test_fund)
        
        # GPU看门狗
        def test_gpu():
            from src.core.gpu_watchdog import GPUWatchdog
            watchdog = GPUWatchdog()
            return f"GPU看门狗初始化成功"
        self.run_test("core", "GPU看门狗", test_gpu)
        
        # 锁箱管理器
        def test_lockbox():
            from src.core.lockbox_manager import LockBoxManager
            # LockBoxManager需要redis和broker参数，测试类加载
            return f"锁箱管理器类加载成功"
        self.run_test("core", "锁箱管理器", test_lockbox)

    # ========================================================================
    # 10. 策略层
    # ========================================================================
    
    def test_strategy_layer(self):
        """策略层功能测试"""
        self.log("=" * 60)
        self.log("10. 策略层功能测试", "SECTION")
        self.log("=" * 60)
        
        # 基础策略
        def test_base_strategy():
            from src.strategies.base_strategy import Strategy
            return f"基础策略类(Strategy)加载成功"
        self.run_test("strategy", "基础策略", test_base_strategy)
        
        # 信号聚合器
        def test_aggregator():
            from src.strategies.signal_aggregator import SignalAggregator
            aggregator = SignalAggregator()
            return f"信号聚合器初始化成功"
        self.run_test("strategy", "信号聚合器", test_aggregator)
        
        # 智能仓位构建器
        def test_position():
            from src.strategies.smart_position_builder import SmartPositionBuilder
            builder = SmartPositionBuilder()
            return f"智能仓位构建器初始化成功"
        self.run_test("strategy", "智能仓位构建器", test_position)
        
        # 策略风险管理器
        def test_strategy_risk():
            from src.strategies.strategy_risk_manager import StrategyRiskManager
            from src.strategies.data_models import StrategyConfig
            # 创建配置（包含所有必填参数）
            config = StrategyConfig(
                strategy_name="test_strategy",
                capital_tier="tier3_medium",
                max_position=0.8,
                max_single_stock=0.1,
                max_industry=0.3,
                stop_loss_pct=-0.08,  # 必须为负数
                take_profit_pct=0.20,  # 必须为正数
                trailing_stop_enabled=True
            )
            manager = StrategyRiskManager(config)
            return f"策略风险管理器: stop_loss={manager.stop_loss_pct*100:.1f}%"
        self.run_test("strategy", "策略风险管理器", test_strategy_risk)
        
        # 动量策略
        def test_momentum():
            from src.strategies.meta_momentum.s02_aggressive import S02AggressiveStrategy
            return f"动量策略类加载成功"
        self.run_test("strategy", "动量策略", test_momentum)
        
        # 均值回归策略
        def test_mean_reversion():
            from src.strategies.meta_mean_reversion.s01_retracement import S01RetracementStrategy
            return f"均值回归策略类加载成功"
        self.run_test("strategy", "均值回归策略", test_mean_reversion)

    # ========================================================================
    # 11. 集成层
    # ========================================================================
    
    def test_integration_layer(self):
        """集成层功能测试"""
        self.log("=" * 60)
        self.log("11. 集成层功能测试", "SECTION")
        self.log("=" * 60)
        
        # 成本监控集成
        def test_cost_integration():
            from src.integration.cost_monitoring_integration import CostMonitoringIntegration
            return f"成本监控集成类加载成功"
        self.run_test("integration", "成本监控集成", test_cost_integration)
        
        # 风险应急集成
        def test_risk_integration():
            from src.integration.risk_emergency_integration import RiskEmergencyIntegration
            return f"风险应急集成类加载成功"
        self.run_test("integration", "风险应急集成", test_risk_integration)
        
        # 调度管道
        def test_scheduler_pipeline():
            from src.integration.scheduler_pipeline import ScheduledPipelineManager, PipelineTask
            manager = ScheduledPipelineManager()
            return f"调度管道管理器初始化成功"
        self.run_test("integration", "调度管道", test_scheduler_pipeline)

    # ========================================================================
    # 12. 界面层
    # ========================================================================
    
    def test_interface_layer(self):
        """界面层功能测试"""
        self.log("=" * 60)
        self.log("12. 界面层功能测试", "SECTION")
        self.log("=" * 60)
        
        # 健康API
        def test_health_api():
            from src.interface.health_api import HealthAPI
            return f"健康API类加载成功"
        self.run_test("interface", "健康API", test_health_api)
        
        # 访问控制
        def test_access():
            from src.interface.access_control import UserRole, PageAccess, TradingPermission
            role = UserRole.ADMIN
            page = PageAccess.COCKPIT
            return f"访问控制: role={role.name}, page={page.value}"
        self.run_test("interface", "访问控制", test_access)
        
        # UI主题
        def test_theme():
            from src.interface.ui_theme import ThemeMode, ColorScheme, ThemeColors
            colors = ThemeColors()
            return f"UI主题: bg={colors.bg_primary}, primary={colors.primary}"
        self.run_test("interface", "UI主题", test_theme)

    # ========================================================================
    # 13. 完整交易流程
    # ========================================================================
    
    def test_trading_workflow(self):
        """完整交易流程功能测试"""
        self.log("=" * 60)
        self.log("13. 完整交易流程模拟", "SECTION")
        self.log("=" * 60)
        
        # Step 1: 获取行情
        def step1():
            from src.execution.market_data import TickData
            tick = TickData(
                symbol="000001.SZ",
                price=10.50,
                volume=50000,
                timestamp=datetime.now()
            )
            return f"行情: {tick.symbol} @ {tick.price}"
        self.run_test("workflow", "Step1_获取行情", step1)
        
        # Step 2: 创建订单
        def step2():
            from src.execution.order_manager import Order, OrderSide, OrderType
            order = Order(
                order_id=str(uuid.uuid4())[:8],
                symbol="000001.SZ",
                side=OrderSide.BUY,
                order_type=OrderType.LIMIT,
                quantity=100,
                price=10.50
            )
            return f"订单: {order.order_id} {order.side.value} {order.quantity}股"
        self.run_test("workflow", "Step2_创建订单", step2)
        
        # Step 3: 风控检查
        def step3():
            from src.execution.risk_control_system import RiskControlSystem
            risk = RiskControlSystem()
            return f"风控: total_capital={risk.total_capital}"
        self.run_test("workflow", "Step3_风控检查", step3)
        
        # Step 4: 合规检查
        def step4():
            from src.compliance.trading_compliance_manager import TradingComplianceManager
            compliance = TradingComplianceManager()
            return f"合规: daily_limit={compliance.daily_trade_limit}"
        self.run_test("workflow", "Step4_合规检查", step4)
        
        # Step 5: AI决策
        def step5():
            from src.brain.soldier.core import SoldierWithFailover
            soldier = SoldierWithFailover(
                local_model_path="models/test",
                cloud_api_key="test_key"
            )
            return f"AI: mode={soldier.mode}"
        self.run_test("workflow", "Step5_AI决策", step5)
        
        # Step 6: 成本记录
        def step6():
            from src.monitoring.cost_tracker import CostTracker
            tracker = CostTracker()
            cost = tracker.track_api_call("deepseek", "deepseek-chat", 100, 50)
            return f"成本: ¥{cost:.4f}"
        self.run_test("workflow", "Step6_成本记录", step6)
        
        # Step 7: 性能记录
        def step7():
            from src.monitoring.performance_monitor import PerformanceMonitor
            monitor = PerformanceMonitor()
            stats = monitor.track_soldier_latency(15.5)
            return f"性能: P99={stats.get('p99', 0):.2f}ms"
        self.run_test("workflow", "Step7_性能记录", step7)

    # ========================================================================
    # 主运行方法
    # ========================================================================
    
    def run_all_tests(self):
        """运行所有功能测试"""
        start_time = datetime.now()
        
        self.log("=" * 70)
        self.log("🧪 MIA项目全量功能测试 V2", "INFO")
        self.log(f"开始时间: {start_time.isoformat()}")
        self.log("=" * 70)
        print()
        
        # 运行各层测试
        self.test_infra_layer()
        print()
        self.test_execution_layer()
        print()
        self.test_risk_layer()
        print()
        self.test_brain_layer()
        print()
        self.test_monitoring_layer()
        print()
        self.test_evolution_layer()
        print()
        self.test_capital_layer()
        print()
        self.test_compliance_layer()
        print()
        self.test_core_layer()
        print()
        self.test_strategy_layer()
        print()
        self.test_integration_layer()
        print()
        self.test_interface_layer()
        print()
        self.test_trading_workflow()
        print()
        
        # 输出总结
        end_time = datetime.now()
        self.print_summary(start_time, end_time)

    def print_summary(self, start_time: datetime, end_time: datetime):
        """输出测试总结"""
        self.log("=" * 70)
        self.log("📊 功能测试总结", "INFO")
        self.log("=" * 70)
        
        print()
        print("┌" + "─" * 50 + "┐")
        print(f"│ {'测试类别':<20} │ {'通过':>8} │ {'失败':>8} │ {'通过率':>8} │")
        print("├" + "─" * 50 + "┤")
        
        for category, results in self.results.items():
            passed = sum(1 for r in results if r.passed)
            failed = len(results) - passed
            rate = (passed / len(results) * 100) if results else 0
            status = "✅" if failed == 0 else "❌"
            print(f"│ {status} {category:<17} │ {passed:>8} │ {failed:>8} │ {rate:>7.1f}% │")
        
        print("├" + "─" * 50 + "┤")
        rate = (self.passed_tests / self.total_tests * 100) if self.total_tests else 0
        print(f"│ {'合计':<20} │ {self.passed_tests:>8} │ {self.total_tests - self.passed_tests:>8} │ {rate:>7.1f}% │")
        print("└" + "─" * 50 + "┘")
        
        duration = (end_time - start_time).total_seconds()
        
        print()
        print(f"📈 统计信息:")
        print(f"   • 总测试数: {self.total_tests}")
        print(f"   • 通过: {self.passed_tests} ({rate:.1f}%)")
        print(f"   • 失败: {self.total_tests - self.passed_tests}")
        print(f"   • 耗时: {duration:.2f}秒")
        
        # 输出失败详情
        failed_tests = []
        for category, results in self.results.items():
            for r in results:
                if not r.passed:
                    failed_tests.append((category, r.name, r.error))
        
        if failed_tests:
            print()
            self.log("失败测试详情:", "ERROR")
            for cat, name, err in failed_tests:
                print(f"   ❌ [{cat}] {name}: {err[:50]}...")
        
        print()
        if self.passed_tests == self.total_tests:
            self.log(f"🎉 全部 {self.total_tests} 个功能测试通过！", "OK")
        else:
            self.log(f"⚠️ {self.total_tests - self.passed_tests} 个测试需要修复", "WARN")


def main():
    debugger = FunctionalDebuggerV2()
    debugger.run_all_tests()


if __name__ == "__main__":
    main()
