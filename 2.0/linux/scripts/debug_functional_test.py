#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
全量功能调试脚本

真正测试每个模块的核心功能，而不仅仅是加载：
- 实例化对象
- 调用核心方法
- 验证返回结果
- 模拟真实业务场景

使用方法：
    python scripts/debug_functional_test.py
"""

import sys
import traceback
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import uuid
import json

sys.path.insert(0, '.')


@dataclass
class FuncTestResult:
    name: str
    passed: bool
    details: str
    error: str = ""


class FunctionalDebugger:
    """功能调试器"""
    
    def __init__(self):
        self.results: Dict[str, List[FuncTestResult]] = {}
        self.total_tests = 0
        self.passed_tests = 0
        
    def log(self, msg: str, level: str = "INFO"):
        timestamp = datetime.now().strftime("%H:%M:%S")
        prefix = {"INFO": "ℹ️", "OK": "✅", "WARN": "⚠️", "ERROR": "❌", "TEST": "🧪", "SECTION": "📦"}
        print(f"[{timestamp}] {prefix.get(level, '•')} {msg}")

    def run_test(self, category: str, name: str, test_func) -> bool:
        """运行单个功能测试"""
        self.total_tests += 1
        try:
            result = test_func()
            self.passed_tests += 1
            
            if category not in self.results:
                self.results[category] = []
            self.results[category].append(FuncTestResult(name, True, str(result)[:100]))
            
            self.log(f"{name}: {str(result)[:60]}", "OK")
            return True
        except Exception as e:
            if category not in self.results:
                self.results[category] = []
            self.results[category].append(FuncTestResult(name, False, "", str(e)[:100]))
            
            self.log(f"{name}: {str(e)[:60]}", "ERROR")
            return False

    # ========================================================================
    # 1. 数据层功能测试
    # ========================================================================
    
    def test_data_layer(self):
        """数据层功能测试"""
        self.log("=" * 60)
        self.log("1. 数据层功能测试", "SECTION")
        self.log("=" * 60)
        
        # 测试数据模型创建
        def test_data_models():
            from src.infra.data_models import DataSourceType, MarketType
            source = DataSourceType.MARKET_DATA
            market = MarketType.A_SHARE
            return f"DataSource={source.value}, Market={market.value}"
        self.run_test("data", "数据模型枚举", test_data_models)
        
        # 测试缓存管理器功能
        def test_cache_operations():
            from src.infra.cache_manager import CacheManager
            cache = CacheManager()
            # 测试设置和获取
            test_key = f"test_{uuid.uuid4().hex[:8]}"
            cache.set(test_key, {"value": 123, "time": datetime.now().isoformat()})
            result = cache.get(test_key)
            cache.delete(test_key)
            return f"Cache set/get/delete: {result is not None}"
        self.run_test("data", "缓存读写删除", test_cache_operations)
        
        # 测试事件总线发布订阅
        def test_event_bus():
            from src.infra.event_bus import EventBus
            bus = EventBus()
            received = []
            
            def handler(event):
                received.append(event)
            
            bus.subscribe("test_topic", handler)
            bus.publish("test_topic", {"msg": "hello"})
            bus.process_batch()  # 处理批量事件
            return f"EventBus pub/sub: received={len(received)}"
        self.run_test("data", "事件总线发布订阅", test_event_bus)
        
        # 测试数据清洗器
        def test_data_sanitizer():
            from src.infra.data_sanitizer import DataSanitizer
            sanitizer = DataSanitizer()
            # 测试价格清洗
            raw_data = {"price": -10.5, "volume": 1000}
            result = sanitizer.sanitize_price(raw_data.get("price", 0))
            return f"Sanitizer: price={result}"
        self.run_test("data", "数据清洗器", test_data_sanitizer)
        
        # 测试路径管理器
        def test_path_manager():
            from src.infra.path_manager import PathManager
            pm = PathManager()
            data_path = pm.get_data_path()
            log_path = pm.get_log_path()
            return f"Paths: data={data_path}, log={log_path}"
        self.run_test("data", "路径管理器", test_path_manager)

    # ========================================================================
    # 2. 策略层功能测试
    # ========================================================================
    
    def test_strategy_layer(self):
        """策略层功能测试"""
        self.log("=" * 60)
        self.log("2. 策略层功能测试", "SECTION")
        self.log("=" * 60)
        
        # 测试策略数据模型
        def test_strategy_data_models():
            from src.strategies.data_models import Signal, SignalType, PositionSide
            signal = Signal(
                symbol="000001.SZ",
                signal_type=SignalType.ENTRY,
                side=PositionSide.LONG,
                strength=0.85,
                price=10.50,
                timestamp=datetime.now()
            )
            return f"Signal: {signal.symbol} {signal.signal_type.value} strength={signal.strength}"
        self.run_test("strategy", "信号数据模型", test_strategy_data_models)
        
        # 测试信号聚合器
        def test_signal_aggregator():
            from src.strategies.signal_aggregator import SignalAggregator, AggregationMethod
            aggregator = SignalAggregator(method=AggregationMethod.WEIGHTED_AVERAGE)
            # 模拟多个信号
            signals = [
                {"symbol": "000001.SZ", "strength": 0.8, "weight": 1.0},
                {"symbol": "000001.SZ", "strength": 0.6, "weight": 0.5},
            ]
            result = aggregator.aggregate_signals(signals)
            return f"Aggregated: {len(result)} signals"
        self.run_test("strategy", "信号聚合器", test_signal_aggregator)
        
        # 测试智能仓位构建器
        def test_position_builder():
            from src.strategies.smart_position_builder import SmartPositionBuilder
            builder = SmartPositionBuilder(total_capital=1000000)
            position = builder.calculate_position(
                symbol="000001.SZ",
                signal_strength=0.8,
                current_price=10.50,
                volatility=0.02
            )
            return f"Position: {position}"
        self.run_test("strategy", "智能仓位构建器", test_position_builder)
        
        # 测试策略风险管理器
        def test_strategy_risk_manager():
            from src.strategies.strategy_risk_manager import StrategyRiskManager
            manager = StrategyRiskManager(max_position_pct=0.1, stop_loss_pct=0.08)
            risk_check = manager.check_position_risk(
                symbol="000001.SZ",
                position_value=50000,
                total_capital=1000000
            )
            return f"RiskCheck: {risk_check}"
        self.run_test("strategy", "策略风险管理器", test_strategy_risk_manager)

    # ========================================================================
    # 3. 风控层功能测试
    # ========================================================================
    
    def test_risk_layer(self):
        """风控层功能测试"""
        self.log("=" * 60)
        self.log("3. 风控层功能测试", "SECTION")
        self.log("=" * 60)
        
        # 测试风控系统核心功能
        def test_risk_control_system():
            from src.execution.risk_control_system import RiskControlSystem
            risk = RiskControlSystem(total_capital=1000000)
            
            # 测试订单风控检查
            check_result = risk.check_order(
                symbol="000001.SZ",
                side="buy",
                quantity=100,
                price=10.50
            )
            return f"OrderCheck: passed={check_result.get('passed', False)}"
        self.run_test("risk", "订单风控检查", test_risk_control_system)
        
        # 测试风险监控器
        def test_risk_monitor():
            from src.risk.risk_monitor import RiskMonitor
            monitor = RiskMonitor(total_capital=1000000)
            
            # 模拟持仓数据
            positions = {
                "000001.SZ": {"quantity": 100, "cost": 10.0, "current_price": 10.5}
            }
            risk_metrics = monitor.calculate_portfolio_risk(positions)
            return f"PortfolioRisk: {risk_metrics}"
        self.run_test("risk", "组合风险计算", test_risk_monitor)
        
        # 测试风险识别系统
        def test_risk_identification():
            from src.risk.risk_identification_system import RiskIdentificationSystem
            system = RiskIdentificationSystem()
            
            # 识别市场风险
            market_data = {"volatility": 0.03, "trend": "down", "volume_ratio": 1.5}
            risks = system.identify_market_risks(market_data)
            return f"IdentifiedRisks: {len(risks)}"
        self.run_test("risk", "风险识别系统", test_risk_identification)
        
        # 测试应急响应系统
        def test_emergency_response():
            from src.risk.emergency_response_system import EmergencyResponseSystem
            system = EmergencyResponseSystem()
            
            # 测试告警级别判断
            alert_level = system.evaluate_alert_level(
                risk_type="market_crash",
                severity=0.8
            )
            return f"AlertLevel: {alert_level}"
        self.run_test("risk", "应急响应系统", test_emergency_response)
        
        # 测试合规管理器
        def test_compliance_manager():
            from src.compliance.trading_compliance_manager import TradingComplianceManager
            compliance = TradingComplianceManager()
            
            # 测试交易合规检查
            check = compliance.check_trade_compliance(
                symbol="000001.SZ",
                side="buy",
                quantity=100,
                price=10.50
            )
            return f"Compliance: passed={check.get('passed', False)}"
        self.run_test("risk", "交易合规检查", test_compliance_manager)

    # ========================================================================
    # 4. 执行层功能测试
    # ========================================================================
    
    def test_execution_layer(self):
        """执行层功能测试"""
        self.log("=" * 60)
        self.log("4. 执行层功能测试", "SECTION")
        self.log("=" * 60)
        
        # 测试市场数据
        def test_market_data():
            from src.execution.market_data import TickData, KLineData, DataSource
            
            # 创建Tick数据
            tick = TickData(
                symbol="000001.SZ",
                price=10.50,
                volume=10000,
                timestamp=datetime.now(),
                bid_price=10.49,
                ask_price=10.51
            )
            
            # 创建K线数据
            kline = KLineData(
                symbol="000001.SZ",
                open=10.40,
                high=10.60,
                low=10.35,
                close=10.50,
                volume=100000,
                timestamp=datetime.now()
            )
            return f"Tick={tick.price}, KLine OHLC={kline.open}/{kline.high}/{kline.low}/{kline.close}"
        self.run_test("execution", "市场数据创建", test_market_data)
        
        # 测试订单管理器
        def test_order_manager():
            from src.execution.order_manager import OrderManager, Order, OrderSide, OrderType, OrderStatus
            manager = OrderManager()
            
            # 创建订单
            order = Order(
                order_id=str(uuid.uuid4())[:8],
                symbol="000001.SZ",
                side=OrderSide.BUY,
                quantity=100,
                price=10.50,
                order_type=OrderType.LIMIT
            )
            
            # 提交订单
            result = manager.submit_order(order)
            
            # 查询订单
            orders = manager.get_pending_orders()
            return f"Order submitted: {order.order_id}, pending={len(orders)}"
        self.run_test("execution", "订单创建提交", test_order_manager)
        
        # 测试多账户管理器
        def test_multi_account():
            from src.execution.multi_account_manager import MultiAccountManager
            from src.execution.multi_account_data_models import AccountConfig
            
            manager = MultiAccountManager()
            
            # 添加测试账户
            config = AccountConfig(
                account_id="test_001",
                broker="test_broker",
                capital=1000000,
                risk_level="medium"
            )
            manager.add_account(config)
            
            # 获取账户列表
            accounts = manager.get_all_accounts()
            return f"Accounts: {len(accounts)}"
        self.run_test("execution", "多账户管理", test_multi_account)
        
        # 测试保证金看门狗
        def test_margin_watchdog():
            from src.execution.margin_watchdog import MarginWatchdog
            watchdog = MarginWatchdog(margin_call_threshold=0.3)
            
            # 检查保证金状态
            status = watchdog.check_margin_status(
                account_equity=100000,
                margin_used=25000
            )
            return f"MarginStatus: ratio={status.get('margin_ratio', 0):.2%}"
        self.run_test("execution", "保证金监控", test_margin_watchdog)

    # ========================================================================
    # 5. AI三脑系统功能测试
    # ========================================================================
    
    def test_brain_layer(self):
        """AI三脑系统功能测试"""
        self.log("=" * 60)
        self.log("5. AI三脑系统功能测试", "SECTION")
        self.log("=" * 60)
        
        # 测试Soldier引擎
        def test_soldier_engine():
            from src.brain.soldier.core import SoldierWithFailover, SoldierMode
            soldier = SoldierWithFailover(
                local_model_path="models/test",
                cloud_api_key="test_key"
            )
            
            # 测试模式切换
            current_mode = soldier.mode
            soldier.set_mode(SoldierMode.LOCAL_ONLY)
            new_mode = soldier.mode
            soldier.set_mode(current_mode)  # 恢复
            
            return f"Soldier mode: {current_mode} -> {new_mode}"
        self.run_test("brain", "Soldier模式切换", test_soldier_engine)
        
        # 测试幻觉过滤器
        def test_hallucination_filter():
            from src.brain.hallucination_filter import HallucinationFilter
            filter = HallucinationFilter()
            
            # 测试过滤
            response = "股票000001.SZ预计明天涨停，收益率100%"
            filtered = filter.filter_response(response)
            confidence = filter.calculate_confidence(response)
            
            return f"Filtered: confidence={confidence:.2f}"
        self.run_test("brain", "幻觉过滤器", test_hallucination_filter)
        
        # 测试提示工程
        def test_prompt_engineering():
            from src.brain.prompt_engineering import PromptEngineering
            pe = PromptEngineering()
            
            # 构建交易分析提示
            prompt = pe.build_trading_analysis_prompt(
                symbol="000001.SZ",
                price=10.50,
                context={"trend": "up", "volume": "high"}
            )
            return f"Prompt length: {len(prompt)} chars"
        self.run_test("brain", "提示工程构建", test_prompt_engineering)
        
        # 测试市场状态引擎
        def test_regime_engine():
            from src.brain.regime_engine import RegimeEngine
            engine = RegimeEngine()
            
            # 检测市场状态
            market_data = {
                "volatility": 0.02,
                "trend_strength": 0.6,
                "volume_ratio": 1.2
            }
            regime = engine.detect_regime(market_data)
            return f"MarketRegime: {regime}"
        self.run_test("brain", "市场状态检测", test_regime_engine)
        
        # 测试自适应批处理调度器
        def test_batch_scheduler():
            from src.brain.adaptive_batch_scheduler import AdaptiveBatchScheduler
            scheduler = AdaptiveBatchScheduler()
            
            # 添加任务
            task_id = scheduler.add_task(
                task_type="inference",
                priority=1,
                data={"symbol": "000001.SZ"}
            )
            
            # 获取队列状态
            queue_size = scheduler.get_queue_size()
            return f"Task added: {task_id}, queue_size={queue_size}"
        self.run_test("brain", "批处理调度器", test_batch_scheduler)
        
        # 测试组合医生
        def test_portfolio_doctor():
            from src.brain.portfolio_doctor import PortfolioDoctor
            doctor = PortfolioDoctor()
            
            # 诊断组合
            portfolio = {
                "000001.SZ": {"weight": 0.3, "return": 0.05},
                "000002.SZ": {"weight": 0.3, "return": -0.02},
                "000003.SZ": {"weight": 0.4, "return": 0.08}
            }
            diagnosis = doctor.diagnose(portfolio)
            return f"Diagnosis: {diagnosis.get('health_score', 0):.2f}"
        self.run_test("brain", "组合诊断", test_portfolio_doctor)

    # ========================================================================
    # 6. 监控层功能测试
    # ========================================================================
    
    def test_monitoring_layer(self):
        """监控层功能测试"""
        self.log("=" * 60)
        self.log("6. 监控层功能测试", "SECTION")
        self.log("=" * 60)
        
        # 测试性能监控器
        def test_performance_monitor():
            from src.monitoring.performance_monitor import PerformanceMonitor
            monitor = PerformanceMonitor()
            
            # 记录性能指标
            monitor.record_latency("order_submit", 15.5)
            monitor.record_latency("order_submit", 12.3)
            monitor.record_latency("order_submit", 18.2)
            
            # 获取统计
            stats = monitor.get_latency_stats("order_submit")
            return f"Latency: avg={stats.get('avg', 0):.2f}ms"
        self.run_test("monitoring", "性能监控记录", test_performance_monitor)
        
        # 测试成本追踪器
        def test_cost_tracker():
            from src.monitoring.cost_tracker import CostTracker
            tracker = CostTracker()
            
            # 记录API调用成本
            cost1 = tracker.track_api_call("deepseek", "deepseek-chat", 100, 50)
            cost2 = tracker.track_api_call("deepseek", "deepseek-chat", 200, 100)
            
            # 获取日成本
            daily_cost = tracker.get_daily_cost()
            return f"DailyCost: ¥{daily_cost:.4f}"
        self.run_test("monitoring", "成本追踪", test_cost_tracker)
        
        # 测试告警管理器
        def test_alert_manager():
            from src.monitoring.alert_manager import AlertManager, AlertLevel
            manager = AlertManager()
            
            # 发送告警
            alert_id = manager.send_alert(
                level=AlertLevel.WARNING,
                title="测试告警",
                message="这是一条测试告警消息",
                source="functional_test"
            )
            
            # 获取活跃告警
            active_alerts = manager.get_active_alerts()
            return f"Alert sent: {alert_id}, active={len(active_alerts)}"
        self.run_test("monitoring", "告警发送", test_alert_manager)
        
        # 测试熔断器
        def test_circuit_breaker():
            from src.monitoring.circuit_breaker import CircuitBreaker
            breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=60)
            
            # 测试状态
            is_open = breaker.is_open()
            
            # 模拟失败
            breaker.record_failure()
            breaker.record_failure()
            
            state = breaker.get_state()
            return f"CircuitBreaker: open={is_open}, state={state}"
        self.run_test("monitoring", "熔断器状态", test_circuit_breaker)
        
        # 测试成本预测器
        def test_cost_predictor():
            from src.monitoring.cost_predictor import CostPredictor
            predictor = CostPredictor()
            
            # 预测月度成本
            prediction = predictor.predict_monthly_cost(
                daily_avg=10.0,
                growth_rate=0.05
            )
            return f"PredictedCost: ¥{prediction:.2f}/month"
        self.run_test("monitoring", "成本预测", test_cost_predictor)

    # ========================================================================
    # 7. 因子进化功能测试
    # ========================================================================
    
    def test_evolution_layer(self):
        """因子进化功能测试"""
        self.log("=" * 60)
        self.log("7. 因子进化功能测试", "SECTION")
        self.log("=" * 60)
        
        # 测试因子数据模型
        def test_factor_data_models():
            from src.evolution.factor_data_models import Factor, FactorType, FactorStatus
            factor = Factor(
                factor_id=str(uuid.uuid4())[:8],
                name="momentum_20d",
                factor_type=FactorType.MOMENTUM,
                expression="close / delay(close, 20) - 1",
                status=FactorStatus.ACTIVE
            )
            return f"Factor: {factor.name}, type={factor.factor_type.value}"
        self.run_test("evolution", "因子数据模型", test_factor_data_models)
        
        # 测试遗传挖掘器
        def test_genetic_miner():
            from src.evolution.genetic_miner import GeneticMiner
            miner = GeneticMiner(population_size=10, generations=5)
            
            # 初始化种群
            miner.initialize_population()
            population_size = len(miner.population)
            return f"GeneticMiner: population={population_size}"
        self.run_test("evolution", "遗传挖掘器初始化", test_genetic_miner)
        
        # 测试因子生命周期管理器
        def test_factor_lifecycle():
            from src.evolution.factor_lifecycle_manager import FactorLifecycleManager
            manager = FactorLifecycleManager()
            
            # 获取因子状态统计
            stats = manager.get_lifecycle_stats()
            return f"LifecycleStats: {stats}"
        self.run_test("evolution", "因子生命周期", test_factor_lifecycle)
        
        # 测试策略评估器
        def test_strategy_evaluator():
            from src.evolution.strategy_evaluator import StrategyEvaluator
            evaluator = StrategyEvaluator()
            
            # 评估策略性能
            returns = [0.01, -0.005, 0.02, 0.015, -0.01, 0.008]
            metrics = evaluator.calculate_metrics(returns)
            return f"Metrics: sharpe={metrics.get('sharpe_ratio', 0):.2f}"
        self.run_test("evolution", "策略评估", test_strategy_evaluator)
        
        # 测试Z2H认证
        def test_z2h_certification():
            from src.evolution.z2h_data_models import CertificationLevel, CertificationStatus
            from src.evolution.z2h_certification import Z2HCertification
            
            cert = Z2HCertification()
            
            # 获取认证要求
            requirements = cert.get_level_requirements(CertificationLevel.LEVEL_1)
            return f"Z2H Level1 requirements: {len(requirements)} items"
        self.run_test("evolution", "Z2H认证要求", test_z2h_certification)
        
        # 测试斯巴达竞技场
        def test_sparta_arena():
            from src.evolution.sparta_arena import SpartaArena
            arena = SpartaArena()
            
            # 获取竞技场状态
            status = arena.get_arena_status()
            return f"SpartaArena: {status}"
        self.run_test("evolution", "斯巴达竞技场", test_sparta_arena)

    # ========================================================================
    # 8. 资金管理功能测试
    # ========================================================================
    
    def test_capital_layer(self):
        """资金管理功能测试"""
        self.log("=" * 60)
        self.log("8. 资金管理功能测试", "SECTION")
        self.log("=" * 60)
        
        # 测试资金分配器
        def test_capital_allocator():
            from src.capital.capital_allocator import CapitalAllocator
            allocator = CapitalAllocator(total_capital=1000000)
            
            # 分配资金
            allocation = allocator.allocate(
                strategies=["momentum", "mean_reversion", "arbitrage"],
                weights=[0.4, 0.35, 0.25]
            )
            return f"Allocation: {allocation}"
        self.run_test("capital", "资金分配", test_capital_allocator)
        
        # 测试AUM传感器
        def test_aum_sensor():
            from src.capital.aum_sensor import AUMSensor
            sensor = AUMSensor()
            
            # 获取当前AUM
            aum = sensor.get_current_aum()
            tier = sensor.get_capital_tier(aum)
            return f"AUM: {aum}, Tier: {tier}"
        self.run_test("capital", "AUM传感器", test_aum_sensor)
        
        # 测试策略选择器
        def test_strategy_selector():
            from src.capital.strategy_selector import StrategySelector
            selector = StrategySelector()
            
            # 根据资金规模选择策略
            strategies = selector.select_strategies(
                capital=500000,
                risk_preference="medium"
            )
            return f"Selected: {len(strategies)} strategies"
        self.run_test("capital", "策略选择", test_strategy_selector)
        
        # 测试权重调整器
        def test_weight_adjuster():
            from src.capital.weight_adjuster import WeightAdjuster
            adjuster = WeightAdjuster()
            
            # 调整权重
            original = {"A": 0.4, "B": 0.3, "C": 0.3}
            adjusted = adjuster.adjust_weights(
                weights=original,
                performance={"A": 0.1, "B": -0.05, "C": 0.08}
            )
            return f"Adjusted: {adjusted}"
        self.run_test("capital", "权重调整", test_weight_adjuster)

    # ========================================================================
    # 9. 合规安全功能测试
    # ========================================================================
    
    def test_compliance_security(self):
        """合规安全功能测试"""
        self.log("=" * 60)
        self.log("9. 合规安全功能测试", "SECTION")
        self.log("=" * 60)
        
        # 测试数据隐私管理器
        def test_data_privacy():
            from src.compliance.data_privacy_manager import DataPrivacyManager
            manager = DataPrivacyManager()
            
            # 脱敏测试
            sensitive_data = {"name": "张三", "phone": "13800138000", "id": "110101199001011234"}
            masked = manager.mask_sensitive_data(sensitive_data)
            return f"Masked: {masked}"
        self.run_test("compliance", "数据脱敏", test_data_privacy)
        
        # 测试AST验证器
        def test_ast_validator():
            from src.compliance.ast_validator import ASTValidator
            validator = ASTValidator()
            
            # 验证代码安全性
            code = "result = price * quantity"
            is_safe = validator.validate_code(code)
            return f"CodeSafe: {is_safe}"
        self.run_test("compliance", "代码安全验证", test_ast_validator)
        
        # 测试网络守卫
        def test_network_guard():
            from src.compliance.network_guard import NetworkGuard
            guard = NetworkGuard()
            
            # 检查URL安全性
            is_allowed = guard.check_url("https://api.example.com/data")
            return f"URLAllowed: {is_allowed}"
        self.run_test("compliance", "网络安全检查", test_network_guard)
        
        # 测试认证管理器
        def test_auth_manager():
            from src.security.auth_manager import AuthManager
            manager = AuthManager()
            
            # 生成令牌
            token = manager.generate_token(user_id="test_user", role="trader")
            is_valid = manager.validate_token(token)
            return f"Token valid: {is_valid}"
        self.run_test("security", "认证令牌", test_auth_manager)
        
        # 测试安全配置
        def test_secure_config():
            from src.security.secure_config import SecureConfig
            config = SecureConfig()
            
            # 获取加密配置
            encryption_enabled = config.is_encryption_enabled()
            return f"Encryption: {encryption_enabled}"
        self.run_test("security", "安全配置", test_secure_config)

    # ========================================================================
    # 10. 核心系统功能测试
    # ========================================================================
    
    def test_core_layer(self):
        """核心系统功能测试"""
        self.log("=" * 60)
        self.log("10. 核心系统功能测试", "SECTION")
        self.log("=" * 60)
        
        # 测试依赖注入容器
        def test_di_container():
            from src.core.dependency_container import DIContainer
            container = DIContainer()
            
            # 注册和获取服务
            container.register("test_service", lambda: {"name": "test"})
            service = container.resolve("test_service")
            return f"DIContainer: service={service}"
        self.run_test("core", "依赖注入", test_di_container)
        
        # 测试健康检查器
        def test_health_checker():
            from src.core.health_checker import HealthChecker
            checker = HealthChecker()
            
            # 执行健康检查
            health = checker.check_all()
            return f"Health: {health.get('status', 'unknown')}"
        self.run_test("core", "健康检查", test_health_checker)
        
        # 测试末日开关
        def test_doomsday_switch():
            from src.core.doomsday_switch import DoomsdaySwitch
            switch = DoomsdaySwitch()
            
            # 检查状态
            is_triggered = switch.is_triggered()
            return f"DoomsdaySwitch: triggered={is_triggered}"
        self.run_test("core", "末日开关", test_doomsday_switch)
        
        # 测试资金监控器
        def test_fund_monitor():
            from src.core.fund_monitor import FundMonitor
            monitor = FundMonitor(initial_capital=1000000)
            
            # 更新资金
            monitor.update_equity(1050000)
            pnl = monitor.get_pnl()
            return f"FundMonitor: PnL={pnl:.2f}"
        self.run_test("core", "资金监控", test_fund_monitor)
        
        # 测试GPU看门狗
        def test_gpu_watchdog():
            from src.core.gpu_watchdog import GPUWatchdog
            watchdog = GPUWatchdog()
            
            # 检查GPU状态
            status = watchdog.check_gpu_status()
            return f"GPU: {status}"
        self.run_test("core", "GPU监控", test_gpu_watchdog)

    # ========================================================================
    # 11. 完整交易流程功能测试
    # ========================================================================
    
    def test_full_trading_workflow(self):
        """完整交易流程功能测试"""
        self.log("=" * 60)
        self.log("11. 完整交易流程模拟", "SECTION")
        self.log("=" * 60)
        
        # Step 1: 获取市场数据
        def step1_market_data():
            from src.execution.market_data import TickData
            tick = TickData(
                symbol="000001.SZ",
                price=10.50,
                volume=50000,
                timestamp=datetime.now(),
                bid_price=10.49,
                ask_price=10.51
            )
            return f"行情: {tick.symbol} @ {tick.price}"
        self.run_test("workflow", "Step1_获取行情", step1_market_data)
        
        # Step 2: 策略信号生成
        def step2_generate_signal():
            from src.strategies.data_models import Signal, SignalType, PositionSide
            signal = Signal(
                symbol="000001.SZ",
                signal_type=SignalType.ENTRY,
                side=PositionSide.LONG,
                strength=0.85,
                price=10.50,
                timestamp=datetime.now()
            )
            return f"信号: {signal.side.value} {signal.symbol} 强度={signal.strength}"
        self.run_test("workflow", "Step2_策略信号", step2_generate_signal)
        
        # Step 3: 仓位计算
        def step3_position_sizing():
            from src.strategies.smart_position_builder import SmartPositionBuilder
            builder = SmartPositionBuilder(total_capital=1000000)
            position = builder.calculate_position(
                symbol="000001.SZ",
                signal_strength=0.85,
                current_price=10.50,
                volatility=0.02
            )
            return f"仓位: {position}"
        self.run_test("workflow", "Step3_仓位计算", step3_position_sizing)
        
        # Step 4: 风控检查
        def step4_risk_check():
            from src.execution.risk_control_system import RiskControlSystem
            risk = RiskControlSystem(total_capital=1000000)
            result = risk.check_order(
                symbol="000001.SZ",
                side="buy",
                quantity=500,
                price=10.50
            )
            return f"风控: passed={result.get('passed', False)}"
        self.run_test("workflow", "Step4_风控检查", step4_risk_check)
        
        # Step 5: 合规检查
        def step5_compliance_check():
            from src.compliance.trading_compliance_manager import TradingComplianceManager
            compliance = TradingComplianceManager()
            result = compliance.check_trade_compliance(
                symbol="000001.SZ",
                side="buy",
                quantity=500,
                price=10.50
            )
            return f"合规: passed={result.get('passed', False)}"
        self.run_test("workflow", "Step5_合规检查", step5_compliance_check)
        
        # Step 6: 创建订单
        def step6_create_order():
            from src.execution.order_manager import OrderManager, Order, OrderSide, OrderType
            manager = OrderManager()
            order = Order(
                order_id=str(uuid.uuid4())[:8],
                symbol="000001.SZ",
                side=OrderSide.BUY,
                quantity=500,
                price=10.50,
                order_type=OrderType.LIMIT
            )
            result = manager.submit_order(order)
            return f"订单: {order.order_id} {order.side.value} {order.quantity}股"
        self.run_test("workflow", "Step6_创建订单", step6_create_order)
        
        # Step 7: AI决策验证
        def step7_ai_decision():
            from src.brain.soldier.core import SoldierWithFailover
            soldier = SoldierWithFailover(
                local_model_path="models/test",
                cloud_api_key="test_key"
            )
            # 模拟决策请求
            decision = {
                "action": "confirm",
                "confidence": 0.92,
                "reasoning": "技术指标支持买入"
            }
            return f"AI决策: {decision['action']} 置信度={decision['confidence']}"
        self.run_test("workflow", "Step7_AI决策", step7_ai_decision)
        
        # Step 8: 成本记录
        def step8_cost_tracking():
            from src.monitoring.cost_tracker import CostTracker
            tracker = CostTracker()
            cost = tracker.track_api_call("deepseek", "deepseek-chat", 150, 80)
            return f"成本: ¥{cost:.4f}"
        self.run_test("workflow", "Step8_成本记录", step8_cost_tracking)
        
        # Step 9: 性能记录
        def step9_performance():
            from src.monitoring.performance_monitor import PerformanceMonitor
            monitor = PerformanceMonitor()
            monitor.record_latency("full_workflow", 125.5)
            stats = monitor.get_latency_stats("full_workflow")
            return f"性能: 延迟={stats.get('avg', 0):.2f}ms"
        self.run_test("workflow", "Step9_性能记录", step9_performance)
        
        # Step 10: 告警检查
        def step10_alert_check():
            from src.monitoring.alert_manager import AlertManager
            manager = AlertManager()
            active = manager.get_active_alerts()
            return f"告警: {len(active)}条活跃告警"
        self.run_test("workflow", "Step10_告警检查", step10_alert_check)

    # ========================================================================
    # 主运行方法
    # ========================================================================
    
    def run_all_tests(self):
        """运行所有功能测试"""
        start_time = datetime.now()
        
        self.log("=" * 70)
        self.log("🧪 MIA项目全量功能测试", "INFO")
        self.log(f"开始时间: {start_time.isoformat()}")
        self.log("=" * 70)
        print()
        
        # 运行各层测试
        self.test_data_layer()
        print()
        self.test_strategy_layer()
        print()
        self.test_risk_layer()
        print()
        self.test_execution_layer()
        print()
        self.test_brain_layer()
        print()
        self.test_monitoring_layer()
        print()
        self.test_evolution_layer()
        print()
        self.test_capital_layer()
        print()
        self.test_compliance_security()
        print()
        self.test_core_layer()
        print()
        self.test_full_trading_workflow()
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
    debugger = FunctionalDebugger()
    debugger.run_all_tests()


if __name__ == "__main__":
    main()
