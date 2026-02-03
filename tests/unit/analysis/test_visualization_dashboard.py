"""VisualizationDashboard单元测试

白皮书依据: 第五章 5.4 可视化系统

测试策略分析可视化仪表盘的核心功能。

Author: MIA Team
Date: 2026-01-27
Version: v1.0
"""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
import json

from src.analysis.visualization_dashboard import (
    VisualizationDashboard,
    ChartConfig
)


@pytest.fixture
async def dashboard():
    """创建VisualizationDashboard实例"""
    dashboard = VisualizationDashboard(redis_url="redis://localhost:6379/0")
    yield dashboard
    await dashboard.disconnect()


@pytest.fixture
def mock_redis():
    """创建Mock Redis客户端"""
    mock = AsyncMock()
    return mock


@pytest.fixture
def sample_analysis_data():
    """示例分析数据"""
    return {
        'essence': {
            'overall_score': 85,
            'profitability': 90,
            'stability': 80,
            'risk_control': 85,
            'market_adaptability': 88,
            'execution_efficiency': 82
        },
        'risk': {
            'risk_level': 'medium',
            'market_adaptability': 'high'
        },
        'overfitting': {
            'risk_score': 35,
            'risk_level': 'low'
        }
    }


@pytest.fixture
def sample_stock_data():
    """示例个股数据"""
    return {
        'smart_money': {
            'smart_money_type': '机构',
            'cost_basis': 10.20,
            'holding_percentage': 15.0,
            'current_profit': 2.94,
            'behavior_pattern': '建仓中',
            'risk_level': '低'
        },
        'recommendation': {
            'action': '买入',
            'confidence': 0.85,
            'current_price': 10.50,
            'suggested_buy_price_range': [10.30, 10.50],
            'target_price': 12.00,
            'stop_loss_price': 9.80,
            'position_suggestion': '标准仓位（5-8%）',
            'holding_period': '中期（30-60天）',
            'support_reasons': ['主力持续建仓', '技术面突破', '板块轮动'],
            'risk_warnings': ['短期涨幅较大', '大盘转弱需止损']
        }
    }


class TestVisualizationDashboard:
    """VisualizationDashboard测试类"""
    
    def test_init(self):
        """测试初始化"""
        dashboard = VisualizationDashboard()
        
        assert dashboard.redis_client is None
        assert dashboard.redis_url == "redis://localhost:6379/0"
        assert len(dashboard.chart_generators) == 29
        assert len(dashboard.chart_configs) > 0
    
    def test_init_with_custom_redis_url(self):
        """测试自定义Redis URL初始化"""
        custom_url = "redis://custom:6380/1"
        dashboard = VisualizationDashboard(redis_url=custom_url)
        
        assert dashboard.redis_url == custom_url
    
    @pytest.mark.asyncio
    async def test_connect(self, dashboard, mock_redis):
        """测试Redis连接"""
        # 修复：正确Mock异步from_url方法
        async def mock_from_url(*args, **kwargs):
            return mock_redis
        
        with patch('redis.asyncio.from_url', side_effect=mock_from_url):
            await dashboard.connect()
            
            assert dashboard.redis_client is not None
    
    @pytest.mark.asyncio
    async def test_disconnect(self, dashboard, mock_redis):
        """测试Redis断开连接"""
        dashboard.redis_client = mock_redis
        
        await dashboard.disconnect()
        
        mock_redis.close.assert_called_once()
        assert dashboard.redis_client is None
    
    def test_init_chart_generators(self, dashboard):
        """测试图表生成器初始化"""
        generators = dashboard.chart_generators
        
        # 验证29个图表生成器都存在
        expected_generators = [
            'strategy_essence_radar',
            'overfitting_risk_gauge',
            'feature_importance_bar',
            'correlation_heatmap',
            'non_stationarity_analysis',
            'signal_noise_ratio_trend',
            'capital_capacity_curve',
            'market_adaptability_matrix',
            'stop_loss_effectiveness',
            'slippage_distribution',
            'trading_replay_timeline',
            'market_sentiment_evolution',
            'smart_vs_retail_sentiment',
            'market_technical_analysis',
            'limit_up_distribution',
            'sector_strength_matrix',
            'sector_rotation_chart',
            'drawdown_underwater_curve',
            'strategy_correlation_heatmap',
            'efficient_frontier_curve',
            'stress_test_results',
            'transaction_cost_analysis',
            'strategy_decay_trend',
            'position_management_matrix',
            'fitness_evolution_chart',
            'arena_performance_comparison',
            'factor_evolution_chart',
            'smart_money_cost_distribution',
            'stock_comprehensive_scorecard'
        ]
        
        assert len(generators) == 29
        for generator_name in expected_generators:
            assert generator_name in generators
            assert callable(generators[generator_name])
    
    def test_init_chart_configs(self, dashboard):
        """测试图表配置初始化"""
        configs = dashboard.chart_configs
        
        assert len(configs) > 0
        
        # 验证策略本质雷达图配置
        assert 'strategy_essence_radar' in configs
        radar_config = configs['strategy_essence_radar']
        assert isinstance(radar_config, ChartConfig)
        assert radar_config.chart_id == 'strategy_essence_radar'
        assert radar_config.chart_type == 'radar'
        assert radar_config.title == '策略本质雷达图'
        
        # 验证过拟合风险仪表盘配置
        assert 'overfitting_risk_gauge' in configs
        gauge_config = configs['overfitting_risk_gauge']
        assert isinstance(gauge_config, ChartConfig)
        assert gauge_config.chart_id == 'overfitting_risk_gauge'
        assert gauge_config.chart_type == 'gauge'
        assert gauge_config.title == '过拟合风险仪表盘'
    
    @pytest.mark.asyncio
    async def test_generate_strategy_dashboard_empty_strategy_id(self, dashboard):
        """测试空策略ID"""
        with pytest.raises(ValueError, match="strategy_id不能为空"):
            await dashboard.generate_strategy_dashboard("")
    
    @pytest.mark.asyncio
    async def test_generate_strategy_dashboard_success(
        self,
        dashboard,
        mock_redis,
        sample_analysis_data
    ):
        """测试成功生成策略仪表盘"""
        strategy_id = "S01"
        
        # Mock Redis客户端
        mock_redis.get = AsyncMock(side_effect=lambda key: json.dumps(
            sample_analysis_data.get(key.split(':')[-2], {})
        ))
        dashboard.redis_client = mock_redis
        
        # 生成仪表盘
        result = await dashboard.generate_strategy_dashboard(strategy_id)
        
        # 验证结果
        assert result['strategy_id'] == strategy_id
        assert 'timestamp' in result
        assert 'charts' in result
        assert 'summary' in result
        assert 'metadata' in result
        
        # 验证图表数量
        assert result['metadata']['total_charts'] == 29
        
        # 验证摘要
        summary = result['summary']
        assert summary['overall_score'] == 85
        assert summary['overfitting_risk'] == 'low'
        assert summary['market_adaptability'] == 'high'
    
    @pytest.mark.asyncio
    async def test_generate_stock_dashboard_empty_symbol(self, dashboard):
        """测试空股票代码"""
        with pytest.raises(ValueError, match="symbol不能为空"):
            await dashboard.generate_stock_dashboard("")
    
    @pytest.mark.asyncio
    async def test_generate_stock_dashboard_success(
        self,
        dashboard,
        mock_redis,
        sample_stock_data
    ):
        """测试成功生成个股仪表盘"""
        symbol = "000001.SZ"
        
        # Mock Redis客户端 - 修复：返回正确的数据结构
        def mock_get_side_effect(key):
            if 'smart_money' in key:
                return json.dumps(sample_stock_data['smart_money'])
            elif 'recommendation' in key:
                return json.dumps(sample_stock_data['recommendation'])
            return None
        
        mock_redis.get = AsyncMock(side_effect=mock_get_side_effect)
        dashboard.redis_client = mock_redis
        
        # 生成仪表盘
        result = await dashboard.generate_stock_dashboard(symbol)
        
        # 验证结果
        assert result['symbol'] == symbol
        assert 'timestamp' in result
        assert 'recommendation' in result
        assert 'smart_money_analysis' in result
        assert 'charts' in result
        
        # 验证结论性建议
        recommendation = result['recommendation']
        assert recommendation['action'] == '买入'
        assert recommendation['confidence'] == 0.85
        assert recommendation['current_price'] == 10.50
        
        # 验证主力资金分析
        smart_money = result['smart_money_analysis']
        assert smart_money['smart_money_type'] == '机构'
        assert smart_money['cost_basis'] == 10.20
        assert smart_money['holding_percentage'] == 15.0
    
    @pytest.mark.asyncio
    async def test_fetch_analysis_data(self, dashboard, mock_redis, sample_analysis_data):
        """测试获取分析数据"""
        strategy_id = "S01"
        
        # Mock Redis客户端
        mock_redis.get = AsyncMock(side_effect=lambda key: json.dumps(
            sample_analysis_data.get(key.split(':')[-2], {})
        ))
        dashboard.redis_client = mock_redis
        
        # 获取数据
        result = await dashboard._fetch_analysis_data(strategy_id)
        
        # 验证结果
        assert 'essence' in result
        assert 'risk' in result
        assert 'overfitting' in result
        assert result['essence']['overall_score'] == 85
    
    @pytest.mark.asyncio
    async def test_fetch_stock_data(self, dashboard, mock_redis, sample_stock_data):
        """测试获取个股数据"""
        symbol = "000001.SZ"
        
        # Mock Redis客户端 - 修复：返回正确的数据结构
        def mock_get_side_effect(key):
            if 'smart_money' in key:
                return json.dumps(sample_stock_data['smart_money'])
            elif 'recommendation' in key:
                return json.dumps(sample_stock_data['recommendation'])
            return None
        
        mock_redis.get = AsyncMock(side_effect=mock_get_side_effect)
        dashboard.redis_client = mock_redis
        
        # 获取数据
        result = await dashboard._fetch_stock_data(symbol)
        
        # 验证结果
        assert 'smart_money' in result
        assert 'recommendation' in result
        assert result['smart_money']['smart_money_type'] == '机构'
    
    def test_generate_summary(self, dashboard, sample_analysis_data):
        """测试生成摘要"""
        summary = dashboard._generate_summary(sample_analysis_data)
        
        assert summary['overall_score'] == 85
        assert summary['overfitting_risk'] == 'low'
        assert summary['market_adaptability'] == 'high'
        assert isinstance(summary['key_insights'], list)
    
    def test_generate_summary_empty_data(self, dashboard):
        """测试空数据生成摘要"""
        summary = dashboard._generate_summary({})
        
        assert summary['overall_score'] == 0
        assert summary['overfitting_risk'] == 'unknown'
        assert summary['market_adaptability'] == 'unknown'
    
    @pytest.mark.asyncio
    async def test_generate_recommendation_with_data(
        self,
        dashboard,
        sample_stock_data
    ):
        """测试生成结论性建议（有数据）"""
        symbol = "000001.SZ"
        
        result = await dashboard._generate_recommendation(symbol, sample_stock_data)
        
        assert result['action'] == '买入'
        assert result['confidence'] == 0.85
        assert result['current_price'] == 10.50
    
    @pytest.mark.asyncio
    async def test_generate_recommendation_without_data(self, dashboard):
        """测试生成结论性建议（无数据）"""
        symbol = "000001.SZ"
        
        result = await dashboard._generate_recommendation(symbol, {})
        
        assert result['action'] == '观望'
        assert result['confidence'] == 0.5
        assert result['current_price'] == 0.0
    
    @pytest.mark.asyncio
    async def test_generate_smart_money_analysis_with_data(
        self,
        dashboard,
        sample_stock_data
    ):
        """测试生成主力资金分析（有数据）"""
        symbol = "000001.SZ"
        
        result = await dashboard._generate_smart_money_analysis(symbol, sample_stock_data)
        
        assert result['smart_money_type'] == '机构'
        assert result['cost_basis'] == 10.20
        assert result['holding_percentage'] == 15.0
    
    @pytest.mark.asyncio
    async def test_generate_smart_money_analysis_without_data(self, dashboard):
        """测试生成主力资金分析（无数据）"""
        symbol = "000001.SZ"
        
        result = await dashboard._generate_smart_money_analysis(symbol, {})
        
        assert result['smart_money_type'] == '未知'
        assert result['cost_basis'] == 0.0
        assert result['holding_percentage'] == 0.0
    
    @pytest.mark.asyncio
    async def test_generate_strategy_essence_radar(
        self,
        dashboard,
        sample_analysis_data
    ):
        """测试生成策略本质雷达图"""
        strategy_id = "S01"
        
        result = await dashboard._generate_strategy_essence_radar(
            strategy_id,
            sample_analysis_data
        )
        
        assert result is not None
        assert isinstance(result, str)  # Plotly JSON
        
        # 验证JSON可解析
        import json
        chart_data = json.loads(result)
        assert 'data' in chart_data
        assert 'layout' in chart_data
    
    @pytest.mark.asyncio
    async def test_generate_strategy_essence_radar_no_data(self, dashboard):
        """测试生成策略本质雷达图（无数据）"""
        strategy_id = "S01"
        
        result = await dashboard._generate_strategy_essence_radar(strategy_id, {})
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_generate_overfitting_risk_gauge(
        self,
        dashboard,
        sample_analysis_data
    ):
        """测试生成过拟合风险仪表盘"""
        strategy_id = "S01"
        
        result = await dashboard._generate_overfitting_risk_gauge(
            strategy_id,
            sample_analysis_data
        )
        
        assert result is not None
        assert isinstance(result, str)  # Plotly JSON
        
        # 验证JSON可解析
        import json
        chart_data = json.loads(result)
        assert 'data' in chart_data
        assert 'layout' in chart_data
    
    @pytest.mark.asyncio
    async def test_generate_overfitting_risk_gauge_no_data(self, dashboard):
        """测试生成过拟合风险仪表盘（无数据）"""
        strategy_id = "S01"
        
        result = await dashboard._generate_overfitting_risk_gauge(strategy_id, {})
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_generate_feature_importance_bar(
        self,
        dashboard,
        sample_analysis_data
    ):
        """测试生成特征重要性柱状图"""
        strategy_id = "S01"
        
        result = await dashboard._generate_feature_importance_bar(
            strategy_id,
            sample_analysis_data
        )
        
        assert result is not None
        assert isinstance(result, str)  # Plotly JSON
        
        # 验证JSON可解析
        import json
        chart_data = json.loads(result)
        assert 'data' in chart_data
        assert 'layout' in chart_data


class TestChartConfig:
    """ChartConfig测试类"""
    
    def test_chart_config_creation(self):
        """测试ChartConfig创建"""
        config = ChartConfig(
            chart_id='test_chart',
            chart_type='radar',
            title='测试图表',
            description='这是一个测试图表',
            data_source='mia:test:data'
        )
        
        assert config.chart_id == 'test_chart'
        assert config.chart_type == 'radar'
        assert config.title == '测试图表'
        assert config.description == '这是一个测试图表'
        assert config.data_source == 'mia:test:data'


class TestPerformance:
    """性能测试类"""
    
    @pytest.mark.asyncio
    async def test_generate_strategy_dashboard_performance(
        self,
        dashboard,
        mock_redis,
        sample_analysis_data
    ):
        """测试策略仪表盘生成性能
        
        白皮书依据: 第五章 5.6 性能指标
        - 综合分析(29维度): <30秒
        """
        import time
        
        strategy_id = "S01"
        
        # Mock Redis客户端
        mock_redis.get = AsyncMock(side_effect=lambda key: json.dumps(
            sample_analysis_data.get(key.split(':')[-2], {})
        ))
        dashboard.redis_client = mock_redis
        
        # 测试性能
        start_time = time.time()
        await dashboard.generate_strategy_dashboard(strategy_id)
        elapsed_time = time.time() - start_time
        
        # 验证性能（应该 < 30秒）
        assert elapsed_time < 30.0, f"性能不达标: {elapsed_time:.2f}秒 > 30秒"
    
    @pytest.mark.asyncio
    async def test_generate_stock_dashboard_performance(
        self,
        dashboard,
        mock_redis,
        sample_stock_data
    ):
        """测试个股仪表盘生成性能
        
        白皮书依据: 第五章 5.6 性能指标
        - 个股结论性建议: <3秒
        """
        import time
        
        symbol = "000001.SZ"
        
        # Mock Redis客户端
        mock_redis.get = AsyncMock(side_effect=lambda key: json.dumps(
            sample_stock_data.get(key.split(':')[-2], {})
        ))
        dashboard.redis_client = mock_redis
        
        # 测试性能
        start_time = time.time()
        await dashboard.generate_stock_dashboard(symbol)
        elapsed_time = time.time() - start_time
        
        # 验证性能（应该 < 3秒）
        assert elapsed_time < 3.0, f"性能不达标: {elapsed_time:.2f}秒 > 3秒"
