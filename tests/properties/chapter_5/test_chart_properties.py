"""图表生成器属性测试

白皮书依据: 第五章 5.4.3 29种可视化图表

本模块实现了图表生成器的属性测试，验证：
- Property 18: 图表生成有效性
- Property 19: 图表渲染性能

**Validates: Requirements 7.1-7.30**
"""

import time
from datetime import datetime, timedelta
from typing import Dict, List

import numpy as np
import pytest
from hypothesis import given, settings, strategies as st

from src.brain.visualization.charts import (
    ChartGenerator,
    ChartGenerationError,
    OverfittingData,
    NonstationarityData,
    SignalNoiseData,
    CapacityData,
    StopLossData,
    TradeRecord,
    SentimentData,
    SmartRetailData,
    MarketTechnicalData,
    LimitUpData,
    SectorStrengthData,
    SectorRotationData,
    DrawdownData,
    EfficientFrontierData,
    StressTestData,
    TradingCostData,
    DecayData,
    PositionData,
    FitnessEvolutionData,
    ArenaComparisonData,
    FactorEvolutionData,
    SmartMoneyCostData,
    StockScorecardData,
)


# ============================================================================
# 测试夹具
# ============================================================================

@pytest.fixture
def chart_generator():
    """创建图表生成器实例"""
    return ChartGenerator()


@pytest.fixture
def sample_radar_data():
    """创建示例雷达图数据"""
    return {
        "动量": 0.8,
        "价值": 0.6,
        "质量": 0.7,
        "波动": 0.5,
        "流动性": 0.9,
    }


@pytest.fixture
def sample_overfitting_data():
    """创建示例过拟合数据"""
    return OverfittingData(
        in_sample_sharpe=2.5,
        out_sample_sharpe=1.2,
        parameter_sensitivity=0.3,
        complexity_score=0.6,
        risk_level="中",
    )


@pytest.fixture
def sample_feature_importance():
    """创建示例特征重要性数据"""
    return [
        ("动量因子", 0.25),
        ("价值因子", 0.20),
        ("质量因子", 0.18),
        ("波动率因子", 0.15),
        ("流动性因子", 0.12),
        ("规模因子", 0.10),
    ]


@pytest.fixture
def sample_correlation_matrix():
    """创建示例相关性矩阵"""
    return np.array([
        [1.0, 0.3, -0.2, 0.5],
        [0.3, 1.0, 0.1, -0.3],
        [-0.2, 0.1, 1.0, 0.4],
        [0.5, -0.3, 0.4, 1.0],
    ])


# ============================================================================
# Hypothesis策略
# ============================================================================

@st.composite
def radar_data_strategy(draw):
    """生成雷达图数据的策略"""
    num_dimensions = draw(st.integers(min_value=3, max_value=8))
    dimensions = [f"维度{i}" for i in range(num_dimensions)]
    values = [draw(st.floats(min_value=0, max_value=1)) for _ in range(num_dimensions)]
    return dict(zip(dimensions, values))


@st.composite
def feature_importance_strategy(draw):
    """生成特征重要性数据的策略"""
    num_features = draw(st.integers(min_value=3, max_value=10))
    features = [f"特征{i}" for i in range(num_features)]
    importances = [draw(st.floats(min_value=0, max_value=1)) for _ in range(num_features)]
    return list(zip(features, importances))


@st.composite
def slippage_data_strategy(draw):
    """生成滑点数据的策略"""
    num_points = draw(st.integers(min_value=10, max_value=100))
    return [draw(st.floats(min_value=-0.01, max_value=0.01)) for _ in range(num_points)]


# ============================================================================
# Property 18: 图表生成有效性
# ============================================================================

class TestChartGenerationValidity:
    """测试图表生成有效性
    
    **Feature: chapter-5-darwin-visualization-redis, Property 18: Chart generation validity**
    
    **Validates: Requirements 7.1-7.29**
    """
    
    def test_essence_radar_generates_valid_output(
        self,
        chart_generator,
        sample_radar_data,
    ):
        """测试策略本质雷达图生成有效输出
        
        **Validates: Requirements 7.1**
        """
        result = chart_generator.generate_essence_radar(sample_radar_data)
        
        assert result is not None
        assert len(result) > 0
        assert isinstance(result, bytes)
    
    def test_overfitting_dashboard_generates_valid_output(
        self,
        chart_generator,
        sample_overfitting_data,
    ):
        """测试过拟合风险仪表盘生成有效输出
        
        **Validates: Requirements 7.2**
        """
        result = chart_generator.generate_overfitting_dashboard(sample_overfitting_data)
        
        assert result is not None
        assert len(result) > 0
        assert isinstance(result, bytes)
    
    def test_feature_importance_bar_generates_valid_output(
        self,
        chart_generator,
        sample_feature_importance,
    ):
        """测试特征重要性柱状图生成有效输出
        
        **Validates: Requirements 7.3**
        """
        result = chart_generator.generate_feature_importance_bar(sample_feature_importance)
        
        assert result is not None
        assert len(result) > 0
        assert isinstance(result, bytes)
    
    def test_correlation_heatmap_generates_valid_output(
        self,
        chart_generator,
        sample_correlation_matrix,
    ):
        """测试相关性热力图生成有效输出
        
        **Validates: Requirements 7.4**
        """
        result = chart_generator.generate_correlation_heatmap(sample_correlation_matrix)
        
        assert result is not None
        assert len(result) > 0
        assert isinstance(result, bytes)
    
    def test_slippage_histogram_generates_valid_output(self, chart_generator):
        """测试滑点分布直方图生成有效输出
        
        **Validates: Requirements 7.10**
        """
        data = [0.001, -0.002, 0.003, -0.001, 0.002] * 20
        result = chart_generator.generate_slippage_histogram(data)
        
        assert result is not None
        assert len(result) > 0
        assert isinstance(result, bytes)
    
    @given(data=radar_data_strategy())
    @settings(max_examples=10, deadline=10000)
    def test_essence_radar_with_random_data(self, data):
        """测试雷达图处理随机数据
        
        **Validates: Requirements 7.1**
        """
        generator = ChartGenerator()
        result = generator.generate_essence_radar(data)
        
        assert result is not None
        assert len(result) > 0
    
    @given(data=feature_importance_strategy())
    @settings(max_examples=10, deadline=10000)
    def test_feature_importance_with_random_data(self, data):
        """测试特征重要性图处理随机数据
        
        **Validates: Requirements 7.3**
        """
        generator = ChartGenerator()
        result = generator.generate_feature_importance_bar(data)
        
        assert result is not None
        assert len(result) > 0
    
    @given(data=slippage_data_strategy())
    @settings(max_examples=10, deadline=10000)
    def test_slippage_histogram_with_random_data(self, data):
        """测试滑点直方图处理随机数据
        
        **Validates: Requirements 7.10**
        """
        generator = ChartGenerator()
        result = generator.generate_slippage_histogram(data)
        
        assert result is not None
        assert len(result) > 0


# ============================================================================
# Property 19: 图表渲染性能
# ============================================================================

class TestChartRenderingPerformance:
    """测试图表渲染性能
    
    **Feature: chapter-5-darwin-visualization-redis, Property 19: Chart rendering performance**
    
    **Validates: Requirements 7.30**
    """
    
    def test_essence_radar_renders_within_2_seconds(
        self,
        chart_generator,
        sample_radar_data,
    ):
        """测试雷达图渲染时间 < 2秒
        
        **Validates: Requirements 7.30**
        """
        start_time = time.time()
        chart_generator.generate_essence_radar(sample_radar_data)
        elapsed = time.time() - start_time
        
        assert elapsed < 2.0, f"渲染时间 {elapsed:.2f}s 超过2秒限制"
    
    def test_overfitting_dashboard_renders_within_2_seconds(
        self,
        chart_generator,
        sample_overfitting_data,
    ):
        """测试过拟合仪表盘渲染时间 < 2秒
        
        **Validates: Requirements 7.30**
        """
        start_time = time.time()
        chart_generator.generate_overfitting_dashboard(sample_overfitting_data)
        elapsed = time.time() - start_time
        
        assert elapsed < 2.0, f"渲染时间 {elapsed:.2f}s 超过2秒限制"
    
    def test_correlation_heatmap_renders_within_2_seconds(
        self,
        chart_generator,
        sample_correlation_matrix,
    ):
        """测试相关性热力图渲染时间 < 2秒
        
        **Validates: Requirements 7.30**
        """
        start_time = time.time()
        chart_generator.generate_correlation_heatmap(sample_correlation_matrix)
        elapsed = time.time() - start_time
        
        assert elapsed < 2.0, f"渲染时间 {elapsed:.2f}s 超过2秒限制"
    
    def test_large_feature_importance_renders_within_2_seconds(self, chart_generator):
        """测试大量特征的重要性图渲染时间 < 2秒
        
        **Validates: Requirements 7.30**
        """
        # 创建50个特征
        data = [(f"特征{i}", np.random.random()) for i in range(50)]
        
        start_time = time.time()
        chart_generator.generate_feature_importance_bar(data)
        elapsed = time.time() - start_time
        
        assert elapsed < 2.0, f"渲染时间 {elapsed:.2f}s 超过2秒限制"
    
    def test_large_slippage_histogram_renders_within_2_seconds(self, chart_generator):
        """测试大量滑点数据的直方图渲染时间 < 2秒
        
        **Validates: Requirements 7.30**
        """
        # 创建10000个滑点数据点
        data = list(np.random.normal(0, 0.005, 10000))
        
        start_time = time.time()
        chart_generator.generate_slippage_histogram(data)
        elapsed = time.time() - start_time
        
        assert elapsed < 2.0, f"渲染时间 {elapsed:.2f}s 超过2秒限制"


# ============================================================================
# 边界情况测试
# ============================================================================

class TestChartEdgeCases:
    """测试图表边界情况"""
    
    def test_empty_radar_data_raises_error(self, chart_generator):
        """测试空雷达数据抛出错误"""
        with pytest.raises(ChartGenerationError):
            chart_generator.generate_essence_radar({})
    
    def test_empty_feature_importance_raises_error(self, chart_generator):
        """测试空特征重要性数据抛出错误"""
        with pytest.raises(ChartGenerationError):
            chart_generator.generate_feature_importance_bar([])
    
    def test_empty_slippage_data_raises_error(self, chart_generator):
        """测试空滑点数据抛出错误"""
        with pytest.raises(ChartGenerationError):
            chart_generator.generate_slippage_histogram([])
    
    def test_empty_correlation_matrix_raises_error(self, chart_generator):
        """测试空相关性矩阵抛出错误"""
        with pytest.raises(ChartGenerationError):
            chart_generator.generate_correlation_heatmap(np.array([]))
    
    def test_single_dimension_radar(self, chart_generator):
        """测试单维度雷达图"""
        data = {"维度1": 0.5}
        # 单维度应该能生成，但可能不是有效的雷达图
        result = chart_generator.generate_essence_radar(data)
        assert result is not None


# ============================================================================
# 图表类型完整性测试
# ============================================================================

class TestAllChartTypes:
    """测试所有29种图表类型"""
    
    def test_get_available_charts_returns_29_types(self, chart_generator):
        """测试获取可用图表类型返回29种"""
        charts = chart_generator.get_available_charts()
        assert len(charts) == 29
    
    def test_nonstationarity_chart(self, chart_generator):
        """测试非平稳性分析图"""
        data = NonstationarityData(
            adf_statistic=-2.5,
            p_value=0.05,
            rolling_mean=[1.0, 1.1, 1.2, 1.1, 1.0],
            rolling_std=[0.1, 0.12, 0.11, 0.13, 0.1],
            timestamps=[datetime.now() - timedelta(days=i) for i in range(5)],
        )
        result = chart_generator.generate_nonstationarity_chart(data)
        assert result is not None
        assert len(result) > 0
    
    def test_signal_noise_trend(self, chart_generator):
        """测试信噪比趋势图"""
        data = SignalNoiseData(
            snr_values=[1.5, 1.6, 1.4, 1.7, 1.5],
            timestamps=[datetime.now() - timedelta(days=i) for i in range(5)],
            trend="上升",
        )
        result = chart_generator.generate_signal_noise_trend(data)
        assert result is not None
        assert len(result) > 0
    
    def test_capacity_curve(self, chart_generator):
        """测试资金容量曲线"""
        data = CapacityData(
            capacity_levels=[1e6, 5e6, 1e7, 5e7, 1e8],
            impact_costs=[0.01, 0.02, 0.05, 0.1, 0.2],
            optimal_capacity=1e7,
        )
        result = chart_generator.generate_capacity_curve(data)
        assert result is not None
        assert len(result) > 0
    
    def test_market_adaptation_matrix(self, chart_generator):
        """测试市场适配性矩阵"""
        data = {
            "牛市": {"收益": 0.8, "风险": 0.3, "稳定性": 0.7},
            "熊市": {"收益": 0.4, "风险": 0.6, "稳定性": 0.5},
            "震荡": {"收益": 0.6, "风险": 0.4, "稳定性": 0.8},
        }
        result = chart_generator.generate_market_adaptation_matrix(data)
        assert result is not None
        assert len(result) > 0
    
    def test_stop_loss_comparison(self, chart_generator):
        """测试止损效果对比图"""
        data = StopLossData(
            strategies=["固定止损", "追踪止损", "波动止损"],
            effectiveness=[0.7, 0.8, 0.75],
            avg_loss_reduction=[0.3, 0.4, 0.35],
        )
        result = chart_generator.generate_stop_loss_comparison(data)
        assert result is not None
        assert len(result) > 0
    
    def test_drawdown_underwater(self, chart_generator):
        """测试回撤水下曲线"""
        dates = [datetime.now() - timedelta(days=i) for i in range(30)]
        data = DrawdownData(
            dates=dates,
            drawdown_values=[-0.05, -0.08, -0.12, -0.10, -0.15] * 6,
            max_drawdown=-0.15,
            max_drawdown_date=dates[4],
        )
        result = chart_generator.generate_drawdown_underwater(data)
        assert result is not None
        assert len(result) > 0
    
    def test_efficient_frontier(self, chart_generator):
        """测试有效前沿曲线"""
        data = EfficientFrontierData(
            returns=[0.05, 0.08, 0.10, 0.12, 0.15],
            volatilities=[0.10, 0.12, 0.15, 0.18, 0.22],
            sharpe_ratios=[0.5, 0.67, 0.67, 0.67, 0.68],
            optimal_portfolio=(0.15, 0.10),
        )
        result = chart_generator.generate_efficient_frontier(data)
        assert result is not None
        assert len(result) > 0
    
    def test_fitness_evolution(self, chart_generator):
        """测试适应度演化图"""
        data = FitnessEvolutionData(
            generations=list(range(20)),
            fitness_values=[0.5 + i * 0.02 for i in range(20)],
            best_fitness=0.88,
        )
        result = chart_generator.generate_fitness_evolution(data)
        assert result is not None
        assert len(result) > 0
    
    def test_arena_comparison(self, chart_generator):
        """测试Arena表现对比图"""
        data = ArenaComparisonData(
            strategies=["策略A", "策略B", "策略C"],
            reality_scores=[0.8, 0.7, 0.75],
            hell_scores=[0.6, 0.65, 0.55],
            cross_market_scores=[0.7, 0.72, 0.68],
        )
        result = chart_generator.generate_arena_comparison(data)
        assert result is not None
        assert len(result) > 0
    
    def test_stock_scorecard(self, chart_generator):
        """测试个股综合评分卡"""
        data = StockScorecardData(
            symbol="000001",
            name="平安银行",
            dimensions=["基本面", "技术面", "资金面", "情绪面", "估值"],
            scores=[75, 68, 82, 70, 65],
            overall_score=72,
        )
        result = chart_generator.generate_stock_scorecard(data)
        assert result is not None
        assert len(result) > 0


# ============================================================================
# 运行测试
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
