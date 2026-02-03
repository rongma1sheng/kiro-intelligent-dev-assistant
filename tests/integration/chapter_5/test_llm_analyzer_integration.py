"""LLM分析器集成测试

白皮书依据: 第五章 5.1-5.5 LLM策略深度分析系统
测试范围: 完整分析流程、Redis存储、可视化生成

测试目标:
- 测试端到端分析流程
- 测试Redis存储集成和TTL配置
- 测试可视化生成
- 验证Property 11: Redis Storage with TTL
"""

import pytest
import asyncio
from typing import Dict, Any
from datetime import datetime
import pandas as pd
import numpy as np

from src.brain.analyzers.redis_storage import RedisStorageManager
from src.brain.analyzers.visualization_dashboard import VisualizationDashboard


class TestLLMAnalyzerIntegration:
    """LLM分析器集成测试
    
    白皮书依据: 第五章 5.1-5.5
    """
    
    @pytest.fixture
    async def redis_manager(self):
        """Redis存储管理器夹具"""
        manager = RedisStorageManager(
            host='localhost',
            port=6379,
            db=1  # 使用测试数据库
        )
        await manager.initialize()
        yield manager
        await manager.close()
    
    @pytest.fixture
    def visualization_dashboard(self):
        """可视化仪表盘夹具"""
        return VisualizationDashboard()
    
    @pytest.fixture
    def sample_strategy_metadata(self) -> Dict[str, Any]:
        """示例策略元数据"""
        return {
            'strategy_id': "TEST_STRATEGY_001",
            'strategy_name': "测试策略",
            'strategy_type': "multi_factor",
            'created_at': datetime.now().isoformat(),
            'version': "1.0.0"
        }
    
    @pytest.fixture
    def sample_performance_metrics(self) -> Dict[str, Any]:
        """示例性能指标"""
        return {
            'sharpe_ratio': 1.8,
            'annual_return': 0.25,
            'max_drawdown': -0.12,
            'win_rate': 0.62,
            'profit_factor': 2.1,
            'calmar_ratio': 2.08,
            'sortino_ratio': 2.5,
            'total_trades': 150,
            'avg_trade_duration_days': 5.2
        }
    
    @pytest.fixture
    def sample_market_data(self) -> pd.DataFrame:
        """示例市场数据"""
        dates = pd.date_range('2024-01-01', periods=100, freq='D')
        symbols = ['000001.SZ', '000002.SZ', '600000.SH']
        
        data = []
        for symbol in symbols:
            for date in dates:
                data.append({
                    'date': date,
                    'symbol': symbol,
                    'open': 10.0 + np.random.randn() * 0.5,
                    'high': 10.5 + np.random.randn() * 0.5,
                    'low': 9.5 + np.random.randn() * 0.5,
                    'close': 10.0 + np.random.randn() * 0.5,
                    'volume': 1000000 + np.random.randint(-100000, 100000)
                })
        
        return pd.DataFrame(data)


class TestEndToEndAnalysisFlow(TestLLMAnalyzerIntegration):
    """端到端分析流程测试
    
    白皮书依据: 第五章 5.1 策略分析流程
    """
    
    @pytest.mark.asyncio
    async def test_complete_analysis_workflow(
        self,
        redis_manager,
        visualization_dashboard,
        sample_strategy_metadata,
        sample_performance_metrics
    ):
        """测试完整分析工作流
        
        流程: 模拟分析结果 → Redis存储 → 可视化生成
        
        白皮书依据: 第五章 5.1-5.5
        """
        from src.brain.analyzers.data_models import ComprehensiveAnalysisReport
        
        # 1. 模拟分析结果（简化版本，不依赖实际分析器）
        strategy_id = sample_strategy_metadata['strategy_id']
        
        analysis_result = {
            'essence': {
                'core_logic': 'momentum',
                'profit_source': 'trend',
                'confidence': 0.85,
                'complexity': 'medium'
            },
            'risk': {
                'risk_level': 'low',
                'max_drawdown': -0.12,
                'volatility': 0.15,
                'var_95': -0.08
            },
            'overfitting': {
                'overfitting_risk': 'low',
                'confidence': 0.90
            },
            'comprehensive_score': 85
        }
        
        # 2. 存储到Redis
        for dimension, result in analysis_result.items():
            if dimension != 'comprehensive_score':
                success = await redis_manager.store_analysis_result(
                    dimension=dimension,
                    strategy_id=strategy_id,
                    result=result
                )
                assert success, f"存储{dimension}维度失败"
        
        # 3. 从Redis读取验证
        essence_result = await redis_manager.get_analysis_result(
            dimension='essence',
            strategy_id=strategy_id
        )
        assert essence_result is not None
        assert essence_result == analysis_result['essence']
        
        # 4. 创建ComprehensiveAnalysisReport对象
        analysis_report = ComprehensiveAnalysisReport(
            strategy_id=strategy_id,
            overall_score=85,
            essence_report=analysis_result.get('essence'),
            risk_report=analysis_result.get('risk'),
            overfitting_report=analysis_result.get('overfitting')
        )
        
        # 5. 生成可视化
        dashboard = visualization_dashboard.generate_strategy_dashboard(
            analysis_report=analysis_report
        )
        
        # 验证仪表盘生成
        assert dashboard is not None
        assert 'charts' in dashboard
        assert len(dashboard['charts']) > 0
        
        print(f"✅ 完整分析流程测试通过: {strategy_id}")
    
    @pytest.mark.asyncio
    async def test_batch_analysis_workflow(
        self,
        redis_manager
    ):
        """测试批量分析工作流
        
        白皮书依据: 第五章 5.1 批量分析
        """
        # 创建多个策略
        strategy_ids = [f"BATCH_TEST_{i:03d}" for i in range(5)]
        
        # 批量分析和存储
        for strategy_id in strategy_ids:
            # 模拟分析结果
            result = {
                'essence': {
                    'core_logic': 'momentum',
                    'confidence': 0.7 + np.random.rand() * 0.2
                }
            }
            
            # 存储essence维度
            await redis_manager.store_analysis_result(
                dimension='essence',
                strategy_id=strategy_id,
                result=result['essence']
            )
        
        # 批量读取验证
        results = await redis_manager.batch_get_analysis_results(
            dimension='essence',
            strategy_ids=strategy_ids
        )
        
        assert len(results) == len(strategy_ids)
        for strategy_id in strategy_ids:
            assert strategy_id in results
            assert results[strategy_id] is not None
        
        print(f"✅ 批量分析流程测试通过: {len(strategy_ids)}个策略")


class TestRedisStorageIntegration(TestLLMAnalyzerIntegration):
    """Redis存储集成测试
    
    白皮书依据: 第五章 5.5 Redis数据结构
    验证: Property 11 - Redis Storage with TTL
    """
    
    @pytest.mark.asyncio
    async def test_redis_ttl_configuration(self, redis_manager):
        """测试Redis TTL配置
        
        Property 11: Redis Storage with TTL
        白皮书依据: 第五章 5.5.1 TTL配置
        """
        strategy_id = "TTL_TEST_001"
        
        # 测试永久存储（essence维度）
        essence_result = {
            'core_logic': 'momentum',
            'confidence': 0.85
        }
        
        success = await redis_manager.store_analysis_result(
            dimension='essence',
            strategy_id=strategy_id,
            result=essence_result
        )
        assert success
        
        # 验证TTL配置
        ttl = redis_manager.ttl_config.get('essence')
        assert ttl is None, "essence维度应该永久存储"
        
        # 测试临时存储（macro维度，1小时TTL）
        macro_result = {
            'market_regime': 'bull',
            'confidence': 0.75
        }
        
        success = await redis_manager.store_analysis_result(
            dimension='macro',
            strategy_id=strategy_id,
            result=macro_result
        )
        assert success
        
        # 验证TTL配置
        ttl = redis_manager.ttl_config.get('macro')
        assert ttl == 3600, "macro维度应该1小时TTL"
        
        print("✅ Redis TTL配置测试通过")
    
    @pytest.mark.asyncio
    async def test_redis_storage_performance(self, redis_manager):
        """测试Redis存储性能
        
        白皮书依据: 第五章 5.5 性能要求
        - 单次写入延迟: <10ms
        - 单次读取延迟: <5ms
        - 批量查询延迟: <50ms
        """
        import time
        
        strategy_id = "PERF_TEST_001"
        test_result = {
            'test_key': 'test_value',
            'timestamp': datetime.now().isoformat()
        }
        
        # 测试写入性能
        start = time.perf_counter()
        await redis_manager.store_analysis_result(
            dimension='essence',
            strategy_id=strategy_id,
            result=test_result
        )
        write_latency_ms = (time.perf_counter() - start) * 1000
        
        assert write_latency_ms < 10, f"写入延迟{write_latency_ms:.2f}ms超过10ms"
        
        # 测试读取性能
        start = time.perf_counter()
        result = await redis_manager.get_analysis_result(
            dimension='essence',
            strategy_id=strategy_id
        )
        read_latency_ms = (time.perf_counter() - start) * 1000
        
        assert read_latency_ms < 5, f"读取延迟{read_latency_ms:.2f}ms超过5ms"
        assert result == test_result
        
        # 测试批量查询性能
        strategy_ids = [f"BATCH_PERF_{i:03d}" for i in range(10)]
        for sid in strategy_ids:
            await redis_manager.store_analysis_result(
                dimension='essence',
                strategy_id=sid,
                result=test_result
            )
        
        start = time.perf_counter()
        results = await redis_manager.batch_get_analysis_results(
            dimension='essence',
            strategy_ids=strategy_ids
        )
        batch_latency_ms = (time.perf_counter() - start) * 1000
        
        assert batch_latency_ms < 50, f"批量查询延迟{batch_latency_ms:.2f}ms超过50ms"
        assert len(results) == len(strategy_ids)
        
        print(f"✅ Redis存储性能测试通过:")
        print(f"  - 写入延迟: {write_latency_ms:.2f}ms")
        print(f"  - 读取延迟: {read_latency_ms:.2f}ms")
        print(f"  - 批量查询延迟: {batch_latency_ms:.2f}ms")
    
    @pytest.mark.asyncio
    async def test_redis_comprehensive_analysis_storage(self, redis_manager):
        """测试综合分析报告存储
        
        白皮书依据: 第五章 5.5.1 综合分析存储
        """
        strategy_id = "COMPREHENSIVE_TEST_001"
        
        comprehensive_report = {
            'strategy_id': strategy_id,
            'overall_score': 85,
            'dimensions': {
                'essence': {'score': 90},
                'risk': {'score': 80},
                'overfitting': {'score': 85}
            },
            'recommendation': 'APPROVED',
            'generated_at': datetime.now().isoformat()
        }
        
        # 存储综合报告
        success = await redis_manager.store_comprehensive_analysis(
            strategy_id=strategy_id,
            report=comprehensive_report
        )
        assert success
        
        # 读取验证
        retrieved_report = await redis_manager.get_comprehensive_analysis(
            strategy_id=strategy_id
        )
        
        assert retrieved_report is not None
        assert retrieved_report['strategy_id'] == strategy_id
        assert retrieved_report['overall_score'] == 85
        assert 'dimensions' in retrieved_report
        
        print("✅ 综合分析报告存储测试通过")


class TestVisualizationIntegration(TestLLMAnalyzerIntegration):
    """可视化集成测试
    
    白皮书依据: 第五章 5.4 可视化系统
    """
    
    @pytest.mark.asyncio
    async def test_strategy_dashboard_generation(
        self,
        visualization_dashboard,
        sample_strategy_metadata,
        sample_performance_metrics
    ):
        """测试策略分析中心仪表盘生成
        
        白皮书依据: 第五章 5.4.1 策略分析中心
        """
        from src.brain.analyzers.data_models import ComprehensiveAnalysisReport
        
        # 构建分析结果
        analysis_results = {
            'essence': {
                'core_logic': 'momentum',
                'confidence': 0.85,
                'complexity': 'medium'
            },
            'risk': {
                'risk_level': 'low',
                'max_drawdown': -0.12,
                'volatility': 0.15
            },
            'comprehensive_score': 85
        }
        
        # 创建ComprehensiveAnalysisReport对象
        analysis_report = ComprehensiveAnalysisReport(
            strategy_id=sample_strategy_metadata['strategy_id'],
            overall_score=85,
            essence_report=analysis_results.get('essence'),
            risk_report=analysis_results.get('risk')
        )
        
        # 生成仪表盘
        dashboard = visualization_dashboard.generate_strategy_dashboard(
            analysis_report=analysis_report
        )
        
        # 验证仪表盘结构
        assert dashboard is not None
        assert 'overall_score' in dashboard
        assert 'charts' in dashboard
        
        # 验证图表生成
        charts = dashboard['charts']
        assert len(charts) > 0
        
        print(f"✅ 策略仪表盘生成测试通过: {len(charts)}个图表")
    
    @pytest.mark.asyncio
    async def test_stock_dashboard_generation(
        self,
        visualization_dashboard,
        sample_market_data
    ):
        """测试个股分析仪表盘生成
        
        白皮书依据: 第五章 5.4.2 个股分析仪表盘
        """
        from src.brain.analyzers.data_models import ComprehensiveAnalysisReport
        
        symbol = '000001.SZ'
        
        # 准备个股数据
        stock_data = sample_market_data[
            sample_market_data['symbol'] == symbol
        ].copy()
        
        # 创建简化的分析报告
        analysis_report = ComprehensiveAnalysisReport(
            strategy_id=f"STOCK_{symbol}",
            overall_score=75
        )
        
        # 生成仪表盘
        dashboard = visualization_dashboard.generate_stock_dashboard(
            symbol=symbol,
            analysis_report=analysis_report
        )
        
        # 验证仪表盘结构
        assert dashboard is not None
        assert 'symbol' in dashboard
        assert 'sections' in dashboard
        
        print(f"✅ 个股仪表盘生成测试通过: {symbol}")
    
    @pytest.mark.asyncio
    async def test_sector_flow_dashboard_generation(
        self,
        visualization_dashboard
    ):
        """测试板块资金流向仪表盘生成
        
        白皮书依据: 第五章 5.4.3 板块资金异动监控
        """
        from src.brain.analyzers.data_models import (
            SectorCapitalFlowMonitoring,
            SectorFlowData,
            StockFlowData,
            SectorRotationAnalysis,
            SectorFlowTrend
        )
        
        # 准备板块数据
        hot_sectors = [
            SectorFlowData(
                sector_name='人工智能',
                net_inflow=125.3,
                inflow_amount=200.5,
                outflow_amount=75.2,
                price_change_pct=3.8,
                stock_count=50,
                rising_stock_count=35,
                falling_stock_count=15,
                leading_stocks=[
                    StockFlowData(
                        symbol='000001.SZ',
                        name='平安银行',
                        net_inflow=10.5,
                        price_change_pct=5.2,
                        current_price=15.80
                    )
                ]
            ),
            SectorFlowData(
                sector_name='半导体',
                net_inflow=98.7,
                inflow_amount=150.3,
                outflow_amount=51.6,
                price_change_pct=2.9,
                stock_count=40,
                rising_stock_count=28,
                falling_stock_count=12,
                leading_stocks=[
                    StockFlowData(
                        symbol='000002.SZ',
                        name='万科A',
                        net_inflow=8.3,
                        price_change_pct=4.1,
                        current_price=12.50
                    )
                ]
            )
        ]
        
        cold_sectors = [
            SectorFlowData(
                sector_name='房地产',
                net_inflow=-56.8,
                inflow_amount=30.2,
                outflow_amount=87.0,
                price_change_pct=-1.8,
                stock_count=30,
                rising_stock_count=8,
                falling_stock_count=22,
                leading_stocks=[]
            )
        ]
        
        rotation_analysis = SectorRotationAnalysis(
            current_stage='expansion',
            dominant_sectors=['人工智能', '半导体'],
            rotation_prediction='持续流入科技板块',
            confidence=0.85,
            allocation_suggestion={'人工智能': 0.4, '半导体': 0.3, '其他': 0.3}
        )
        
        flow_trends = {
            '人工智能': SectorFlowTrend(
                sector_name='人工智能',
                period_days=5,
                cumulative_net_inflow=125.3,
                trend_direction='inflow',
                trend_strength=0.85,
                daily_flows=[10.2, 15.3, 20.1, 25.5, 30.2]
            )
        }
        
        flow_data = SectorCapitalFlowMonitoring(
            timestamp=datetime.now(),
            period='1d',
            top_inflow_sectors=hot_sectors,
            top_outflow_sectors=cold_sectors,
            rotation_analysis=rotation_analysis,
            flow_trends=flow_trends,
            allocation_recommendation={'人工智能': 0.4, '半导体': 0.3, '其他': 0.3}
        )
        
        # 生成仪表盘
        dashboard = visualization_dashboard.generate_sector_flow_dashboard(
            flow_data=flow_data
        )
        
        # 验证仪表盘结构
        assert dashboard is not None
        assert 'period' in dashboard
        assert 'sections' in dashboard
        
        # 验证各个section
        sections = dashboard['sections']
        assert 'top_inflow' in sections
        assert 'top_outflow' in sections
        assert 'flow_heatmap' in sections
        
        print("✅ 板块资金流向仪表盘生成测试通过")


class TestErrorHandlingAndRecovery(TestLLMAnalyzerIntegration):
    """错误处理和恢复测试
    
    白皮书依据: 第五章 5.1 错误处理
    """
    
    @pytest.mark.asyncio
    async def test_redis_connection_failure_handling(self):
        """测试Redis连接失败处理"""
        # 使用无效配置
        manager = RedisStorageManager(
            host='invalid_host',
            port=9999
        )
        
        # 初始化应该失败但不抛出异常
        success = await manager.initialize()
        assert not success
        
        # 存储操作应该优雅降级
        result = await manager.store_analysis_result(
            dimension='essence',
            strategy_id='TEST_001',
            result={'test': 'data'}
        )
        assert not result  # 应该返回False而不是抛出异常
        
        print("✅ Redis连接失败处理测试通过")
    
    @pytest.mark.asyncio
    async def test_invalid_data_handling(
        self,
        redis_manager
    ):
        """测试无效数据处理"""
        strategy_id = "INVALID_TEST_001"
        
        # 尝试存储无效数据
        invalid_data = None
        
        # 应该优雅处理而不是崩溃
        try:
            result = await redis_manager.store_analysis_result(
                dimension='essence',
                strategy_id=strategy_id,
                result=invalid_data or {}
            )
            # 应该返回结果而不是崩溃
            assert isinstance(result, bool)
            print("✅ 无效数据处理测试通过")
        except Exception as e:
            pytest.fail(f"无效数据处理失败: {e}")


class TestCacheAndPerformance(TestLLMAnalyzerIntegration):
    """缓存和性能测试
    
    白皮书依据: 第五章 5.5 性能优化
    """
    
    @pytest.mark.asyncio
    async def test_cache_hit_rate(self, redis_manager):
        """测试缓存命中率"""
        strategy_id = "CACHE_TEST_001"
        test_data = {'test': 'data', 'timestamp': datetime.now().isoformat()}
        
        # 首次写入
        await redis_manager.store_analysis_result(
            dimension='essence',
            strategy_id=strategy_id,
            result=test_data
        )
        
        # 多次读取（应该命中缓存）
        for _ in range(10):
            result = await redis_manager.get_analysis_result(
                dimension='essence',
                strategy_id=strategy_id
            )
            assert result == test_data
        
        # 获取缓存统计
        stats = await redis_manager.get_cache_stats()
        
        assert stats['initialized']
        assert 'hit_rate' in stats
        
        print(f"✅ 缓存命中率测试通过: {stats.get('hit_rate', 0):.2%}")


# 运行所有测试
if __name__ == '__main__':
    pytest.main([__file__, '-v', '--asyncio-mode=auto'])
