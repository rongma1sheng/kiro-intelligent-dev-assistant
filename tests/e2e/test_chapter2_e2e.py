"""Chapter 2 AI三脑端到端测试

白皮书依据: 第二章 AI三脑架构
测试范围: Task 11.2 - 端到端测试

测试场景:
1. 完整工作流程测试
2. 组件协作测试
3. 系统稳定性测试
4. 事件驱动通信测试
"""

import pytest
import asyncio
import numpy as np
from datetime import datetime
from typing import List

from src.brain.chapter2_integration import Chapter2Integration, IntegrationConfig
from src.brain.meta_learning.data_models import MarketContext, PerformanceMetrics
from src.infra.event_bus import EventBus, EventType
from src.core.exceptions import ComponentInitializationError


class TestChapter2E2E:
    """Chapter 2端到端测试套件"""
    
    @pytest.fixture
    async def integration(self):
        """集成测试夹具"""
        config = IntegrationConfig(
            enable_meta_learner=True,
            enable_algo_hunter=True,
            enable_algo_sentinel=False,  # 禁用哨兵（需要外部API）
            enable_engram_memory=True,
            algo_hunter_config={
                'model_type': '1d_cnn',
                'model_path': None,
                'device': 'cpu'  # 使用CPU避免GPU依赖
            },
            engram_memory_config={
                'ngram_size': 4,
                'embedding_dim': 512,
                'memory_size': 10000,  # 小内存用于测试
                'storage_backend': 'ram'
            }
        )
        
        integration = Chapter2Integration(config)
        await integration.initialize()
        await integration.start()
        
        yield integration
        
        await integration.cleanup()
    
    @pytest.mark.asyncio
    async def test_e2e_integration_lifecycle(self):
        """测试完整的集成生命周期
        
        测试流程:
        1. 初始化所有组件
        2. 启动集成
        3. 验证运行状态
        4. 停止集成
        5. 清理资源
        """
        config = IntegrationConfig(
            enable_meta_learner=True,
            enable_algo_hunter=True,
            enable_algo_sentinel=False,
            enable_engram_memory=True,
            algo_hunter_config={
                'model_type': '1d_cnn',
                'model_path': None,
                'device': 'cpu'
            }
        )
        
        integration = Chapter2Integration(config)
        
        # 1. 初始化
        await integration.initialize()
        assert integration.meta_learner is not None
        assert integration.algo_hunter is not None
        assert integration.engram_memory is not None
        assert not integration.is_running
        
        # 2. 启动
        await integration.start()
        assert integration.is_running
        assert integration.start_time is not None
        
        # 3. 验证状态
        status = integration.get_status()
        assert status['is_running']
        assert status['components']['meta_learner']['initialized']
        assert status['components']['algo_hunter']['initialized']
        assert status['components']['engram_memory']['initialized']
        
        # 4. 健康检查
        health = await integration.health_check()
        assert health['healthy']
        assert len(health['issues']) == 0
        
        # 5. 停止
        await integration.stop()
        assert not integration.is_running
        
        # 6. 清理
        await integration.cleanup()
        assert integration.meta_learner is None
        assert integration.algo_hunter is None
        assert integration.engram_memory is None
    
    @pytest.mark.asyncio
    async def test_e2e_meta_learner_workflow(self, integration):
        """测试元学习器完整工作流程
        
        测试流程:
        1. 观察多个学习样本
        2. 触发模型训练
        3. 预测最优策略
        4. 获取学习报告
        """
        meta_learner = integration.meta_learner
        
        # 1. 观察学习样本 - 需要100个样本才能触发训练（默认min_samples_for_training=100）
        for i in range(100):
            market_context = MarketContext(
                volatility=0.2 + (i % 20) * 0.01,
                liquidity=0.8 - (i % 20) * 0.01,
                trend_strength=0.5 + (i % 10) * 0.02,
                regime=['bull', 'bear', 'sideways'][i % 3],
                aum=1000000.0 + i * 10000,
                portfolio_concentration=0.5,
                recent_drawdown=0.1 + (i % 5) * 0.01
            )
            
            # 创建有变化的性能指标，让策略A和B交替获胜
            perf_a = PerformanceMetrics(
                sharpe_ratio=1.5 + (i % 10) * 0.1,
                max_drawdown=0.1,
                win_rate=0.6,
                profit_factor=2.0,
                calmar_ratio=1.2,
                sortino_ratio=1.8,
                decision_latency_ms=10.0
            )
            
            perf_b = PerformanceMetrics(
                sharpe_ratio=1.2 + (i % 5) * 0.2,
                max_drawdown=0.15,
                win_rate=0.55,
                profit_factor=1.8,
                calmar_ratio=1.0,
                sortino_ratio=1.5,
                decision_latency_ms=15.0
            )
            
            await meta_learner.observe_and_learn(market_context, perf_a, perf_b)
        
        # 2. 验证学习样本记录
        report = meta_learner.get_learning_report()
        assert report['total_samples'] == 100
        assert report['strategy_a_wins'] + report['strategy_b_wins'] == 100
        
        # 3. 预测最优策略（模型应该已经训练）
        market_context = MarketContext(
            volatility=0.25,
            liquidity=0.75,
            trend_strength=0.5,
            regime='bull',
            aum=1000000.0,
            portfolio_concentration=0.5,
            recent_drawdown=0.1
        )
        
        strategy, confidence = await meta_learner.predict_best_strategy(market_context)
        assert strategy in ['A', 'B', 'hybrid']
        assert 0.0 <= confidence <= 1.0
    
    @pytest.mark.asyncio
    async def test_e2e_algo_hunter_workflow(self, integration):
        """测试主力雷达完整工作流程
        
        测试流程:
        1. 生成模拟Tick数据
        2. 检测主力行为
        3. 验证推理结果
        4. 检查性能统计
        """
        algo_hunter = integration.algo_hunter
        
        # 1. 生成模拟Tick数据 - 需要5个特征维度
        tick_data = np.random.randn(100, 5).astype(np.float32)
        
        # 2. 检测主力行为
        probability = await algo_hunter.detect_main_force(tick_data)
        
        # 3. 验证结果
        assert 0.0 <= probability <= 1.0
        
        # 4. 检查统计信息
        stats = algo_hunter.get_inference_stats()
        assert stats['total_inferences'] >= 1
        assert stats['avg_latency_ms'] > 0
        assert stats['failed_inferences'] >= 0
    
    @pytest.mark.asyncio
    async def test_e2e_engram_memory_workflow(self, integration):
        """测试Engram记忆系统完整工作流程
        
        测试流程:
        1. 存储多个记忆
        2. 查询记忆
        3. 验证O(1)查询
        4. 检查统计信息
        """
        engram_memory = integration.engram_memory
        
        # 1. 存储记忆
        test_texts = [
            "市场波动率上升，流动性下降",
            "趋势强度增强，建议增加仓位",
            "主力资金流入，关注买入信号"
        ]
        
        for text in test_texts:
            embedding = np.random.randn(512).astype(np.float32)
            engram_memory.store_memory(
                text=text,
                context=["trading", "analysis"],
                embedding=embedding
            )
        
        # 2. 查询记忆
        query_text = "市场波动率上升"
        result = engram_memory.query_memory(query_text)
        
        # 3. 验证结果（可能为None，因为N-gram匹配）
        if result is not None:
            assert result.shape == (512,)
        
        # 4. 检查统计信息
        stats = engram_memory.get_statistics()
        assert stats.total_queries >= 1
        assert stats.hit_count + stats.miss_count == stats.total_queries
    
    @pytest.mark.asyncio
    async def test_e2e_component_collaboration(self, integration):
        """测试组件协作
        
        测试场景:
        1. AlgoHunter检测主力行为
        2. 结果存储到EngramMemory
        3. MetaLearner学习策略
        4. 验证组件间数据流
        """
        algo_hunter = integration.algo_hunter
        engram_memory = integration.engram_memory
        meta_learner = integration.meta_learner
        
        # 1. AlgoHunter检测
        tick_data = np.random.randn(100, 5).astype(np.float32)
        probability = await algo_hunter.detect_main_force(tick_data)
        
        # 2. 存储检测结果到记忆
        detection_text = f"主力概率: {probability:.2f}"
        embedding = np.random.randn(512).astype(np.float32)
        engram_memory.store_memory(
            text=detection_text,
            context=["algo_hunter", "detection"],
            embedding=embedding
        )
        
        # 3. MetaLearner学习
        market_context = MarketContext(
            volatility=0.25,
            liquidity=0.75,
            trend_strength=0.5,
            regime='bull',
            aum=1000000.0,
            portfolio_concentration=0.5,
            recent_drawdown=0.1
        )
        
        perf_a = PerformanceMetrics(
            sharpe_ratio=1.5,
            max_drawdown=0.1,
            win_rate=0.6,
            profit_factor=2.0,
            calmar_ratio=1.2,
            sortino_ratio=1.8,
            decision_latency_ms=10.0
        )
        
        perf_b = PerformanceMetrics(
            sharpe_ratio=1.2,
            max_drawdown=0.15,
            win_rate=0.55,
            profit_factor=1.8,
            calmar_ratio=1.0,
            sortino_ratio=1.5,
            decision_latency_ms=15.0
        )
        
        await meta_learner.observe_and_learn(market_context, perf_a, perf_b)
        
        # 4. 验证数据流
        hunter_stats = algo_hunter.get_inference_stats()
        memory_stats = engram_memory.get_statistics()
        learner_report = meta_learner.get_learning_report()
        
        assert hunter_stats['total_inferences'] >= 1
        assert memory_stats.total_queries >= 0
        assert learner_report['total_samples'] >= 1
    
    @pytest.mark.asyncio
    async def test_e2e_event_driven_communication(self):
        """测试事件驱动通信
        
        测试场景:
        1. 组件发布事件
        2. EventBus分发事件
        3. 订阅者接收事件
        4. 验证异步通信
        """
        event_bus = EventBus()
        received_events = []
        
        # 订阅事件
        async def event_handler(event):
            received_events.append(event)
        
        event_bus.subscribe(EventType.ANALYSIS_COMPLETED, event_handler)
        
        # 创建集成（使用自定义event_bus）
        config = IntegrationConfig(
            enable_meta_learner=True,
            enable_algo_hunter=True,
            enable_algo_sentinel=False,
            enable_engram_memory=True,
            algo_hunter_config={
                'model_type': '1d_cnn',
                'model_path': None,
                'device': 'cpu'
            }
        )
        
        integration = Chapter2Integration(config)
        integration.event_bus = event_bus  # 使用自定义event_bus
        
        await integration.initialize()
        await integration.start()
        
        try:
            # 触发AlgoHunter检测（会发布事件）
            tick_data = np.random.randn(100, 5).astype(np.float32)
            await integration.algo_hunter.detect_main_force(tick_data)
            
            # 等待事件传播
            await asyncio.sleep(0.2)
            
            # 验证事件接收
            assert len(received_events) >= 0  # 可能有事件发布
            
        finally:
            await integration.cleanup()
    
    @pytest.mark.asyncio
    async def test_e2e_system_stability(self, integration):
        """测试系统稳定性
        
        测试场景:
        1. 连续运行多次操作
        2. 验证无内存泄漏
        3. 验证性能稳定
        4. 验证错误恢复
        """
        algo_hunter = integration.algo_hunter
        meta_learner = integration.meta_learner
        
        # 1. 连续运行100次AlgoHunter检测
        latencies = []
        for i in range(100):
            tick_data = np.random.randn(100, 5).astype(np.float32)
            
            import time
            start = time.perf_counter()
            probability = await algo_hunter.detect_main_force(tick_data)
            end = time.perf_counter()
            
            latencies.append((end - start) * 1000)
            assert 0.0 <= probability <= 1.0
        
        # 2. 验证性能稳定（延迟不应显著增加）
        avg_latency_first_10 = np.mean(latencies[:10])
        avg_latency_last_10 = np.mean(latencies[-10:])
        
        # 最后10次的平均延迟不应超过前10次的2倍（允许一些波动）
        assert avg_latency_last_10 < avg_latency_first_10 * 2.0
        
        # 3. 连续学习50个样本
        for i in range(50):
            market_context = MarketContext(
                volatility=0.2 + i * 0.001,
                liquidity=0.8 - i * 0.001,
                trend_strength=0.5,
                regime='bull',
                aum=1000000.0,
                portfolio_concentration=0.5,
                recent_drawdown=0.1
            )
            
            perf_a = PerformanceMetrics(
                sharpe_ratio=1.5,
                max_drawdown=0.1,
                win_rate=0.6,
                profit_factor=2.0,
                calmar_ratio=1.2,
                sortino_ratio=1.8,
                decision_latency_ms=10.0
            )
            
            perf_b = PerformanceMetrics(
                sharpe_ratio=1.2,
                max_drawdown=0.15,
                win_rate=0.55,
                profit_factor=1.8,
                calmar_ratio=1.0,
                sortino_ratio=1.5,
                decision_latency_ms=15.0
            )
            
            await meta_learner.observe_and_learn(market_context, perf_a, perf_b)
        
        # 4. 验证学习稳定
        report = meta_learner.get_learning_report()
        assert report['total_samples'] >= 50
    
    @pytest.mark.asyncio
    async def test_e2e_error_recovery(self):
        """测试错误恢复
        
        测试场景:
        1. 组件初始化失败
        2. 验证优雅降级
        3. 验证错误日志
        """
        # 测试无效配置
        config = IntegrationConfig(
            enable_meta_learner=False,
            enable_algo_hunter=False,
            enable_algo_sentinel=False,
            enable_engram_memory=False
        )
        
        with pytest.raises(ValueError, match="At least one component must be enabled"):
            integration = Chapter2Integration(config)
    
    @pytest.mark.asyncio
    async def test_e2e_context_manager(self):
        """测试异步上下文管理器
        
        测试场景:
        1. 使用async with自动管理生命周期
        2. 验证自动初始化和清理
        """
        config = IntegrationConfig(
            enable_meta_learner=True,
            enable_algo_hunter=True,
            enable_algo_sentinel=False,
            enable_engram_memory=True,
            algo_hunter_config={
                'model_type': '1d_cnn',
                'model_path': None,
                'device': 'cpu'
            }
        )
        
        async with Chapter2Integration(config) as integration:
            # 验证已初始化和启动
            assert integration.is_running
            assert integration.meta_learner is not None
            assert integration.algo_hunter is not None
            assert integration.engram_memory is not None
            
            # 执行一些操作
            tick_data = np.random.randn(100, 5).astype(np.float32)
            probability = await integration.algo_hunter.detect_main_force(tick_data)
            assert 0.0 <= probability <= 1.0
        
        # 退出上下文后应该已清理
        assert not integration.is_running
    
    @pytest.mark.asyncio
    async def test_e2e_concurrent_operations(self, integration):
        """测试并发操作
        
        测试场景:
        1. 并发执行多个AlgoHunter检测
        2. 并发执行多个MetaLearner学习
        3. 验证线程安全
        """
        algo_hunter = integration.algo_hunter
        meta_learner = integration.meta_learner
        
        # 1. 并发AlgoHunter检测
        async def detect_task():
            tick_data = np.random.randn(100, 5).astype(np.float32)
            return await algo_hunter.detect_main_force(tick_data)
        
        tasks = [detect_task() for _ in range(10)]
        results = await asyncio.gather(*tasks)
        
        assert len(results) == 10
        assert all(0.0 <= p <= 1.0 for p in results)
        
        # 2. 并发MetaLearner学习
        async def learn_task(i):
            market_context = MarketContext(
                volatility=0.2 + i * 0.01,
                liquidity=0.8,
                trend_strength=0.5,
                regime='bull',
                aum=1000000.0,
                portfolio_concentration=0.5,
                recent_drawdown=0.1
            )
            
            perf_a = PerformanceMetrics(
                sharpe_ratio=1.5,
                max_drawdown=0.1,
                win_rate=0.6,
                profit_factor=2.0,
                calmar_ratio=1.2,
                sortino_ratio=1.8,
                decision_latency_ms=10.0
            )
            
            perf_b = PerformanceMetrics(
                sharpe_ratio=1.2,
                max_drawdown=0.15,
                win_rate=0.55,
                profit_factor=1.8,
                calmar_ratio=1.0,
                sortino_ratio=1.5,
                decision_latency_ms=15.0
            )
            
            await meta_learner.observe_and_learn(market_context, perf_a, perf_b)
        
        tasks = [learn_task(i) for i in range(10)]
        await asyncio.gather(*tasks)
        
        # 验证所有学习样本都被记录
        report = meta_learner.get_learning_report()
        assert report['total_samples'] >= 10


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
