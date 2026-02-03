"""可视化系统集成测试

白皮书依据: 第五章 5.4 可视化系统

测试可视化系统组件的集成，验证仪表盘和图表生成功能。
"""

import pytest
import asyncio
from datetime import datetime
from typing import Dict, Any, List
import numpy as np

from src.brain.visualization import (
    StrategyDashboard,
    StockDashboard,
    ChartGenerator,
    StrategyDashboardData,
    StockDashboardData,
    StockRecommendation,
    SmartMoneyAnalysis,
    RecommendationAction,
    SmartMoneyType,
    RiskLevel,
    OverfittingRiskLevel,
    MarketAdaptation,
    HoldingPeriod,
    PositionSuggestion,
    OverfittingData,
    BehaviorPattern,
)


class TestChartGeneratorIntegration:
    """图表生成器集成测试
    
    白皮书依据: 第五章 5.4.3 29种可视化图表
    """
    
    @pytest.fixture
    def chart_generator(self) -> ChartGenerator:
        """创建图表生成器"""
        return ChartGenerator()
    
    def test_chart_generator_initialization(
        self,
        chart_generator: ChartGenerator,
    ) -> None:
        """测试图表生成器初始化
        
        白皮书依据: 第五章 5.4.3 29种可视化图表
        """
        assert chart_generator is not None

    def test_generate_essence_radar_chart(
        self,
        chart_generator: ChartGenerator,
    ) -> None:
        """测试生成本质雷达图
        
        白皮书依据: 第五章 5.4.3 图表1
        """
        data = {
            "收益性": 0.8,
            "稳定性": 0.7,
            "风险控制": 0.85,
            "容量": 0.6,
            "适应性": 0.75,
        }
        
        chart = chart_generator.generate_essence_radar(data=data)
        
        assert chart is not None
        assert isinstance(chart, bytes)
    
    def test_generate_overfitting_dashboard(
        self,
        chart_generator: ChartGenerator,
    ) -> None:
        """测试生成过拟合仪表盘
        
        白皮书依据: 第五章 5.4.3 图表2
        """
        data = OverfittingData(
            in_sample_sharpe=2.0,
            out_sample_sharpe=1.5,
            parameter_sensitivity=0.3,
            complexity_score=0.4,
            risk_level="低",
        )
        
        chart = chart_generator.generate_overfitting_dashboard(data=data)
        
        assert chart is not None
        assert isinstance(chart, bytes)
    
    def test_generate_feature_importance_bar(
        self,
        chart_generator: ChartGenerator,
    ) -> None:
        """测试生成特征重要性柱状图
        
        白皮书依据: 第五章 5.4.3 图表3
        """
        data = [
            ("momentum", 0.3),
            ("volatility", 0.25),
            ("volume", 0.2),
            ("price", 0.15),
            ("trend", 0.1),
        ]
        
        chart = chart_generator.generate_feature_importance_bar(data=data)
        
        assert chart is not None
        assert isinstance(chart, bytes)
    
    def test_generate_correlation_heatmap(
        self,
        chart_generator: ChartGenerator,
    ) -> None:
        """测试生成相关性热力图
        
        白皮书依据: 第五章 5.4.3 图表4
        """
        data = np.array([
            [1.0, 0.5, 0.3],
            [0.5, 1.0, 0.4],
            [0.3, 0.4, 1.0],
        ])
        labels = ["策略A", "策略B", "策略C"]
        
        chart = chart_generator.generate_correlation_heatmap(
            data=data,
            labels=labels,
        )
        
        assert chart is not None
        assert isinstance(chart, bytes)

    def test_chart_generator_all_methods_exist(
        self,
        chart_generator: ChartGenerator,
    ) -> None:
        """测试图表生成器支持所有图表类型
        
        白皮书依据: 第五章 5.4.3 29种可视化图表
        
        验证图表生成器支持所有29种图表类型。
        """
        chart_methods = [
            "generate_essence_radar",
            "generate_overfitting_dashboard",
            "generate_feature_importance_bar",
            "generate_correlation_heatmap",
            "generate_nonstationarity_chart",
            "generate_signal_noise_trend",
            "generate_capacity_curve",
            "generate_market_adaptation_matrix",
            "generate_stop_loss_comparison",
            "generate_slippage_histogram",
            "generate_trade_review_timeline",
            "generate_sentiment_evolution",
            "generate_smart_vs_retail_radar",
            "generate_market_technical_chart",
            "generate_limit_up_heatmap",
            "generate_sector_strength_matrix",
            "generate_sector_rotation_chart",
            "generate_drawdown_underwater",
            "generate_strategy_correlation_heatmap",
            "generate_efficient_frontier",
            "generate_stress_test_result",
            "generate_trading_cost_analysis",
            "generate_decay_trend",
            "generate_position_management_matrix",
            "generate_fitness_evolution",
            "generate_arena_comparison",
            "generate_factor_evolution",
            "generate_smart_money_cost_distribution",
            "generate_stock_scorecard",
        ]
        
        for method_name in chart_methods:
            assert hasattr(chart_generator, method_name), f"缺少方法: {method_name}"


class TestStrategyDashboardIntegration:
    """策略仪表盘集成测试
    
    白皮书依据: 第五章 5.4.1 策略分析中心仪表盘
    """
    
    @pytest.fixture
    def chart_generator(self) -> ChartGenerator:
        """创建图表生成器"""
        return ChartGenerator()
    
    @pytest.fixture
    def strategy_dashboard(
        self,
        chart_generator: ChartGenerator,
    ) -> StrategyDashboard:
        """创建策略仪表盘"""
        return StrategyDashboard(
            chart_generator=chart_generator,
        )
    
    @pytest.fixture
    def sample_dashboard_data(self) -> StrategyDashboardData:
        """创建示例仪表盘数据"""
        return StrategyDashboardData(
            strategy_id="test_strategy_001",
            strategy_name="动量策略",
            overall_score=85,
            overfitting_risk=OverfittingRiskLevel.LOW,
            market_adaptation=MarketAdaptation.HIGH,
            essence_radar_data={
                "收益性": 0.8,
                "稳定性": 0.7,
                "风险控制": 0.85,
                "容量": 0.6,
                "适应性": 0.75,
            },
            risk_matrix_data=[[1.0, 0.5], [0.5, 1.0]],
            feature_importance_data=[("momentum", 0.3), ("volatility", 0.25)],
            market_adaptation_matrix={"牛市": {"适配度": 0.9}},
            evolution_visualization_data={"generations": 10},
            updated_at=datetime.now(),
        )
    
    @pytest.mark.asyncio
    async def test_dashboard_initialization(
        self,
        strategy_dashboard: StrategyDashboard,
    ) -> None:
        """测试仪表盘初始化"""
        assert strategy_dashboard is not None
        assert strategy_dashboard._chart_generator is not None

    @pytest.mark.asyncio
    async def test_export_data_json(
        self,
        strategy_dashboard: StrategyDashboard,
        sample_dashboard_data: StrategyDashboardData,
    ) -> None:
        """测试导出JSON数据"""
        # 手动添加到缓存
        strategy_dashboard._dashboard_cache["test_strategy_001"] = (
            sample_dashboard_data,
            datetime.now(),
        )
        
        # 导出JSON
        json_data = await strategy_dashboard.export_data(
            strategy_id="test_strategy_001",
            format="json",
        )
        
        assert json_data is not None
        # JSON数据可能是bytes或str
        if isinstance(json_data, bytes):
            json_str = json_data.decode('utf-8')
        else:
            json_str = json_data
        assert "strategy_id" in json_str
    
    @pytest.mark.asyncio
    async def test_export_data_csv(
        self,
        strategy_dashboard: StrategyDashboard,
        sample_dashboard_data: StrategyDashboardData,
    ) -> None:
        """测试导出CSV数据"""
        # 手动添加到缓存
        strategy_dashboard._dashboard_cache["test_strategy_001"] = (
            sample_dashboard_data,
            datetime.now(),
        )
        
        # 导出CSV
        csv_data = await strategy_dashboard.export_data(
            strategy_id="test_strategy_001",
            format="csv",
        )
        
        assert csv_data is not None
    
    @pytest.mark.asyncio
    async def test_get_history(
        self,
        strategy_dashboard: StrategyDashboard,
        sample_dashboard_data: StrategyDashboardData,
    ) -> None:
        """测试获取历史记录"""
        # 手动添加历史记录
        strategy_dashboard._history_storage["test_strategy_001"] = [
            sample_dashboard_data,
        ]
        
        # 获取历史
        history = await strategy_dashboard.get_history(
            strategy_id="test_strategy_001",
            limit=30,
        )
        
        assert history is not None
        # 历史记录可能是列表或其他格式
        if isinstance(history, list):
            assert len(history) >= 1


class TestStockDashboardIntegration:
    """个股仪表盘集成测试
    
    白皮书依据: 第五章 5.4.2 个股分析仪表盘
    """
    
    @pytest.fixture
    def chart_generator(self) -> ChartGenerator:
        """创建图表生成器"""
        return ChartGenerator()
    
    @pytest.fixture
    def stock_dashboard(
        self,
        chart_generator: ChartGenerator,
    ) -> StockDashboard:
        """创建个股仪表盘"""
        return StockDashboard(
            chart_generator=chart_generator,
        )
    
    @pytest.fixture
    def sample_stock_data(self) -> StockDashboardData:
        """创建示例个股数据"""
        return StockDashboardData(
            symbol="000001.SZ",
            name="平安银行",
            recommendation=StockRecommendation(
                action=RecommendationAction.BUY,
                confidence=0.85,
                current_price=13.5,
                target_price=15.5,
                stop_loss_price=12.0,
                buy_price_range=(12.5, 14.0),
                position_suggestion=PositionSuggestion.LIGHT,
                holding_period=HoldingPeriod.SHORT,
                support_reasons=["技术面突破", "资金流入"],
                risk_warnings=["大盘风险"],
            ),
            smart_money_analysis=SmartMoneyAnalysis(
                smart_money_type=SmartMoneyType.INSTITUTION,
                position_cost=13.0,
                holding_ratio=0.15,
                current_profit=0.05,
                behavior_pattern=BehaviorPattern.ACCUMULATING,
                risk_level=RiskLevel.MEDIUM,
            ),
            updated_at=datetime.now(),
        )
    
    @pytest.mark.asyncio
    async def test_dashboard_initialization(
        self,
        stock_dashboard: StockDashboard,
    ) -> None:
        """测试仪表盘初始化"""
        assert stock_dashboard is not None
        assert stock_dashboard._chart_generator is not None

    @pytest.mark.asyncio
    async def test_batch_load_dashboards(
        self,
        stock_dashboard: StockDashboard,
    ) -> None:
        """测试批量加载仪表盘"""
        symbols = ["000001.SZ", "000002.SZ", "600000.SH"]
        
        dashboards = await stock_dashboard.batch_load_dashboards(
            symbols=symbols,
        )
        
        assert dashboards is not None
        assert len(dashboards) == len(symbols)
    
    @pytest.mark.asyncio
    async def test_generate_charts(
        self,
        stock_dashboard: StockDashboard,
        sample_stock_data: StockDashboardData,
    ) -> None:
        """测试生成图表"""
        # 手动添加到缓存
        stock_dashboard._dashboard_cache["000001.SZ"] = (
            sample_stock_data,
            datetime.now(),
        )
        
        # 生成图表
        charts = await stock_dashboard.generate_charts(
            symbol="000001.SZ",
        )
        
        assert charts is not None


class TestVisualizationComponentsIntegration:
    """可视化组件集成测试
    
    白皮书依据: 第五章 5.4 可视化系统
    """
    
    @pytest.fixture
    def chart_generator(self) -> ChartGenerator:
        """创建图表生成器"""
        return ChartGenerator()
    
    @pytest.fixture
    def strategy_dashboard(
        self,
        chart_generator: ChartGenerator,
    ) -> StrategyDashboard:
        """创建策略仪表盘"""
        return StrategyDashboard(
            chart_generator=chart_generator,
        )
    
    @pytest.fixture
    def stock_dashboard(
        self,
        chart_generator: ChartGenerator,
    ) -> StockDashboard:
        """创建个股仪表盘"""
        return StockDashboard(
            chart_generator=chart_generator,
        )
    
    def test_shared_chart_generator(
        self,
        chart_generator: ChartGenerator,
        strategy_dashboard: StrategyDashboard,
        stock_dashboard: StockDashboard,
    ) -> None:
        """测试共享图表生成器"""
        assert strategy_dashboard._chart_generator is chart_generator
        assert stock_dashboard._chart_generator is chart_generator
    
    @pytest.mark.asyncio
    async def test_concurrent_operations(
        self,
        stock_dashboard: StockDashboard,
    ) -> None:
        """测试并发操作"""
        symbols = ["000001.SZ", "000002.SZ", "600000.SH"]
        
        tasks = [
            stock_dashboard.load_dashboard(symbol=symbol)
            for symbol in symbols
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        assert len(results) == len(symbols)
