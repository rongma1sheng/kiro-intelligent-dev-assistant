#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
完整业务流程调试脚本

用于调试整个项目的核心业务流程：
1. 数据层 - 数据获取、缓存、存储
2. 策略层 - 策略加载、信号生成
3. 风控层 - 风险评估、合规检查
4. 执行层 - 订单管理、交易执行
5. AI层 - 三脑系统、智能决策
6. 监控层 - 性能监控、告警系统

使用方法：
    python scripts/debug_full_workflow.py [module]
    
    module可选：
        all      - 调试所有模块（默认）
        data     - 数据层
        strategy - 策略层
        risk     - 风控层
        execution- 执行层
        brain    - AI层
        monitor  - 监控层
"""

import sys
import traceback
from datetime import datetime
from typing import Any, Dict, List, Optional

# 添加项目路径
sys.path.insert(0, '.')


class WorkflowDebugger:
    """业务流程调试器"""
    
    def __init__(self):
        self.results: Dict[str, Dict] = {}
        self.errors: List[str] = []
        
    def log(self, msg: str, level: str = "INFO"):
        """日志输出"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        prefix = {"INFO": "ℹ️", "OK": "✅", "WARN": "⚠️", "ERROR": "❌", "DEBUG": "🔍"}
        print(f"[{timestamp}] {prefix.get(level, '•')} {msg}")
    
    def test_module(self, name: str, test_func):
        """测试单个模块"""
        self.log(f"Testing {name}...", "DEBUG")
        try:
            result = test_func()
            self.results[name] = {"status": "OK", "result": result}
            self.log(f"{name}: OK", "OK")
            return True
        except Exception as e:
            self.results[name] = {"status": "ERROR", "error": str(e)}
            self.errors.append(f"{name}: {e}")
            self.log(f"{name}: {e}", "ERROR")
            traceback.print_exc()
            return False

    # ========================================================================
    # 1. 数据层调试
    # ========================================================================
    
    def debug_data_layer(self):
        """调试数据层"""
        self.log("=" * 50)
        self.log("数据层调试", "INFO")
        self.log("=" * 50)
        
        # 测试数据模型
        def test_data_models():
            from src.infra.data_models import DataSourceType
            # 简单测试枚举类型
            market_type = DataSourceType.MARKET_DATA
            return f"DataSourceType loaded: {market_type.value}"
        
        self.test_module("DataModels", test_data_models)
        
        # 测试缓存管理
        def test_cache_manager():
            from src.infra.cache_manager import CacheManager
            cache = CacheManager()
            return f"CacheManager initialized"
        
        self.test_module("CacheManager", test_cache_manager)
        
        # 测试事件总线
        def test_event_bus():
            from src.infra.event_bus import EventBus
            bus = EventBus()
            return f"EventBus initialized"
        
        self.test_module("EventBus", test_event_bus)

    # ========================================================================
    # 2. 策略层调试
    # ========================================================================
    
    def debug_strategy_layer(self):
        """调试策略层"""
        self.log("=" * 50)
        self.log("策略层调试", "INFO")
        self.log("=" * 50)
        
        # 测试基础策略
        def test_base_strategy():
            from src.strategies.meta_momentum.s02_aggressive import S02AggressiveStrategy
            return f"S02AggressiveStrategy class loaded"
        
        self.test_module("S02AggressiveStrategy", test_base_strategy)
        
        # 测试信号聚合器
        def test_signal_aggregator():
            from src.strategies.meta_mean_reversion.s01_retracement import S01RetracementStrategy
            return f"S01RetracementStrategy class loaded"
        
        self.test_module("S01RetracementStrategy", test_signal_aggregator)
        
        # 测试策略库
        def test_strategy_library():
            from src.core.dependency_container import DIContainer
            container = DIContainer()
            return f"DIContainer initialized"
        
        self.test_module("DIContainer", test_strategy_library)

    # ========================================================================
    # 3. 风控层调试
    # ========================================================================
    
    def debug_risk_layer(self):
        """调试风控层"""
        self.log("=" * 50)
        self.log("风控层调试", "INFO")
        self.log("=" * 50)
        
        # 测试风控系统
        def test_risk_control():
            from src.execution.risk_control_system import RiskControlSystem
            risk = RiskControlSystem()
            return f"RiskControlSystem initialized"
        
        self.test_module("RiskControlSystem", test_risk_control)
        
        # 测试风险监控
        def test_risk_monitor():
            from src.risk.risk_monitor import RiskMonitor
            monitor = RiskMonitor()
            return f"RiskMonitor initialized"
        
        self.test_module("RiskMonitor", test_risk_monitor)
        
        # 测试合规管理
        def test_compliance():
            from src.compliance.trading_compliance_manager import TradingComplianceManager
            compliance = TradingComplianceManager()
            return f"TradingComplianceManager initialized"
        
        self.test_module("TradingComplianceManager", test_compliance)

    # ========================================================================
    # 4. 执行层调试
    # ========================================================================
    
    def debug_execution_layer(self):
        """调试执行层"""
        self.log("=" * 50)
        self.log("执行层调试", "INFO")
        self.log("=" * 50)
        
        # 测试订单管理
        def test_order_manager():
            from src.execution.order_manager import OrderManager
            manager = OrderManager()
            return f"OrderManager initialized"
        
        self.test_module("OrderManager", test_order_manager)
        
        # 测试市场数据
        def test_market_data():
            from src.execution.market_data import TickData, DataSource
            tick = TickData(
                symbol="000001.SZ",
                price=10.5,
                volume=1000,
                timestamp=datetime.now()
            )
            return f"TickData created: {tick.symbol}"
        
        self.test_module("MarketData", test_market_data)

    # ========================================================================
    # 5. AI层调试（三脑系统）
    # ========================================================================
    
    def debug_brain_layer(self):
        """调试AI层"""
        self.log("=" * 50)
        self.log("AI层调试（三脑系统）", "INFO")
        self.log("=" * 50)
        
        # 测试Soldier引擎
        def test_soldier():
            from src.brain.soldier.core import SoldierWithFailover, SoldierMode
            soldier = SoldierWithFailover(
                local_model_path="models/test",
                cloud_api_key="test_key"
            )
            return f"SoldierWithFailover initialized, mode={soldier.mode}"
        
        self.test_module("SoldierWithFailover", test_soldier)
        
        # 测试推理引擎
        def test_inference():
            from src.brain.soldier.inference_engine import LocalInferenceEngine
            return f"LocalInferenceEngine class loaded"
        
        self.test_module("InferenceEngine", test_inference)
        
        # 测试LLM网关
        def test_llm_gateway():
            from src.brain.llm_gateway import LLMGateway
            return f"LLMGateway class loaded"
        
        self.test_module("LLMGateway", test_llm_gateway)
        
        # 测试双架构运行器
        def test_dual_runner():
            from src.brain.dual_architecture_runner import DualArchitectureRunner
            return f"DualArchitectureRunner class loaded"
        
        self.test_module("DualArchitectureRunner", test_dual_runner)

    # ========================================================================
    # 6. 监控层调试
    # ========================================================================
    
    def debug_monitor_layer(self):
        """调试监控层"""
        self.log("=" * 50)
        self.log("监控层调试", "INFO")
        self.log("=" * 50)
        
        # 测试性能监控
        def test_performance_monitor():
            from src.monitoring.performance_monitor import PerformanceMonitor
            monitor = PerformanceMonitor()
            return f"PerformanceMonitor initialized"
        
        self.test_module("PerformanceMonitor", test_performance_monitor)
        
        # 测试告警管理
        def test_alert_manager():
            from src.monitoring.alert_manager import AlertManager
            alert = AlertManager()
            return f"AlertManager initialized"
        
        self.test_module("AlertManager", test_alert_manager)
        
        # 测试成本追踪
        def test_cost_tracker():
            from src.monitoring.cost_tracker import CostTracker
            tracker = CostTracker()
            return f"CostTracker initialized"
        
        self.test_module("CostTracker", test_cost_tracker)

    # ========================================================================
    # 完整流程调试
    # ========================================================================
    
    def debug_full_workflow(self):
        """调试完整业务流程"""
        self.log("=" * 60)
        self.log("完整业务流程调试", "INFO")
        self.log(f"时间: {datetime.now().isoformat()}")
        self.log("=" * 60)
        print()
        
        # 依次调试各层
        self.debug_data_layer()
        print()
        
        self.debug_strategy_layer()
        print()
        
        self.debug_risk_layer()
        print()
        
        self.debug_execution_layer()
        print()
        
        self.debug_brain_layer()
        print()
        
        self.debug_monitor_layer()
        print()
        
        # 完整交易流程模拟
        self.debug_trading_workflow()
        print()
        
        # 输出总结
        self.print_summary()
    
    # ========================================================================
    # 7. 完整交易流程模拟
    # ========================================================================
    
    def debug_trading_workflow(self):
        """调试完整交易流程"""
        self.log("=" * 50)
        self.log("完整交易流程模拟", "INFO")
        self.log("=" * 50)
        
        # Step 1: 获取市场数据
        def test_get_market_data():
            from src.execution.market_data import TickData
            tick = TickData(
                symbol="000001.SZ",
                price=10.50,
                volume=10000,
                timestamp=datetime.now()
            )
            self.log(f"  股票: {tick.symbol}, 价格: {tick.price}", "DEBUG")
            return tick
        
        self.test_module("Step1_获取行情", test_get_market_data)
        
        # Step 2: 策略信号生成
        def test_generate_signal():
            # 模拟策略信号
            signal = {
                "symbol": "000001.SZ",
                "action": "BUY",
                "price": 10.50,
                "quantity": 100,
                "confidence": 0.85,
                "strategy": "S02_Aggressive"
            }
            self.log(f"  信号: {signal['action']} {signal['symbol']} x{signal['quantity']}", "DEBUG")
            return signal
        
        self.test_module("Step2_策略信号", test_generate_signal)
        
        # Step 3: 风控检查
        def test_risk_check():
            from src.execution.risk_control_system import RiskControlSystem
            risk = RiskControlSystem()
            
            # 检查风控系统状态
            self.log(f"  风控系统: 总资本={risk.total_capital}", "DEBUG")
            return {"risk_system": "initialized", "total_capital": risk.total_capital}
        
        self.test_module("Step3_风控检查", test_risk_check)
        
        # Step 4: 合规检查
        def test_compliance_check():
            from src.compliance.trading_compliance_manager import TradingComplianceManager
            compliance = TradingComplianceManager()
            
            # 检查合规系统状态
            self.log(f"  合规系统: 日限额={compliance.daily_trade_limit}", "DEBUG")
            return {"compliance": "initialized"}
        
        self.test_module("Step4_合规检查", test_compliance_check)
        
        # Step 5: 订单创建
        def test_create_order():
            from src.execution.order_manager import OrderManager, Order, OrderSide, OrderType
            import uuid
            manager = OrderManager()
            
            # 创建订单对象
            order = Order(
                order_id=str(uuid.uuid4())[:8],
                symbol="000001.SZ",
                side=OrderSide.BUY,
                quantity=100,
                price=10.50,
                order_type=OrderType.LIMIT
            )
            self.log(f"  订单: {order.symbol} {order.side.value} x{order.quantity} @{order.price}", "DEBUG")
            return {"order_created": True, "symbol": order.symbol}
        
        self.test_module("Step5_创建订单", test_create_order)
        
        # Step 6: AI决策验证
        def test_ai_decision():
            from src.brain.soldier.core import SoldierWithFailover
            soldier = SoldierWithFailover(
                local_model_path="models/test",
                cloud_api_key="test_key"
            )
            
            # 模拟AI决策请求
            decision_request = {
                "symbol": "000001.SZ",
                "action": "BUY",
                "context": {"price": 10.50, "volume": 10000}
            }
            self.log(f"  AI模式: {soldier.mode}", "DEBUG")
            return {"mode": str(soldier.mode), "ready": True}
        
        self.test_module("Step6_AI决策", test_ai_decision)
        
        # Step 7: 监控记录
        def test_monitoring():
            from src.monitoring.cost_tracker import CostTracker
            from src.monitoring.performance_monitor import PerformanceMonitor
            
            tracker = CostTracker()
            monitor = PerformanceMonitor()
            
            # 记录API调用成本
            cost = tracker.track_api_call(
                service="deepseek",
                model="deepseek-chat",
                input_tokens=100,
                output_tokens=50
            )
            
            self.log(f"  API成本: ¥{cost:.4f}", "DEBUG")
            return {"cost_tracked": True, "cost": cost}
        
        self.test_module("Step7_监控记录", test_monitoring)

    def print_summary(self):
        """输出调试总结"""
        self.log("=" * 60)
        self.log("调试总结", "INFO")
        self.log("=" * 60)
        
        total = len(self.results)
        passed = sum(1 for r in self.results.values() if r["status"] == "OK")
        failed = total - passed
        
        print(f"\n总计: {total} 个模块")
        print(f"✅ 通过: {passed}")
        print(f"❌ 失败: {failed}")
        
        if self.errors:
            print(f"\n失败详情:")
            for err in self.errors:
                print(f"  - {err}")
        
        print()
        if failed == 0:
            self.log("所有模块调试通过！", "OK")
        else:
            self.log(f"{failed} 个模块需要修复", "WARN")


def main():
    module = sys.argv[1] if len(sys.argv) > 1 else "all"
    
    debugger = WorkflowDebugger()
    
    if module == "all":
        debugger.debug_full_workflow()
    elif module == "data":
        debugger.debug_data_layer()
        debugger.print_summary()
    elif module == "strategy":
        debugger.debug_strategy_layer()
        debugger.print_summary()
    elif module == "risk":
        debugger.debug_risk_layer()
        debugger.print_summary()
    elif module == "execution":
        debugger.debug_execution_layer()
        debugger.print_summary()
    elif module == "brain":
        debugger.debug_brain_layer()
        debugger.print_summary()
    elif module == "monitor":
        debugger.debug_monitor_layer()
        debugger.print_summary()
    else:
        print(f"未知模块: {module}")
        print("可选: all, data, strategy, risk, execution, brain, monitor")
        sys.exit(1)


if __name__ == "__main__":
    main()
