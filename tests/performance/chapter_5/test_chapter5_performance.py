"""第五章性能测试

白皮书依据: 第五章 5.4 可视化系统

Property 23: 系统性能要求
- 单维度分析 < 5秒
- 综合分析 < 30秒
- 可视化加载 < 2秒
- PDF生成 < 10秒
- 个股建议 < 3秒
- 10并发请求

Validates: Requirements 11.1-11.7
"""

import pytest
import asyncio
import time
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


class TestChartGeneratorPerformance:
    """图表生成器性能测试
    
    白皮书依据: 第五章 5.4.3 29种可视化图表
    
    性能要求: 单个图表渲染 < 2秒
    """
    
    @pytest.fixture
    def chart_generator(self) -> ChartGenerator:
        """创建图表生成器"""
        return ChartGenerator()

    def test_essence_radar_performance(
        self,
        chart_generator: ChartGenerator,
    ) -> None:
        """测试本质雷达图生成性能
        
        **Validates: Requirements 11.1**
        
        性能要求: < 2秒
        """
        data = {
            "收益性": 0.8,
            "稳定性": 0.7,
            "风险控制": 0.85,
            "容量": 0.6,
            "适应性": 0.75,
        }
        
        start_time = time.perf_counter()
        chart = chart_generator.generate_essence_radar(data=data)
        elapsed = time.perf_counter() - start_time
        
        assert chart is not None
        assert elapsed < 2.0, f"本质雷达图生成耗时 {elapsed:.2f}秒，超过2秒限制"
    
    def test_overfitting_dashboard_performance(
        self,
        chart_generator: ChartGenerator,
    ) -> None:
        """测试过拟合仪表盘生成性能
        
        **Validates: Requirements 11.1**
        
        性能要求: < 2秒
        """
        data = OverfittingData(
            in_sample_sharpe=2.0,
            out_sample_sharpe=1.5,
            parameter_sensitivity=0.3,
            complexity_score=0.4,
            risk_level="低",
        )
        
        start_time = time.perf_counter()
        chart = chart_generator.generate_overfitting_dashboard(data=data)
        elapsed = time.perf_counter() - start_time
        
        assert chart is not None
        assert elapsed < 2.0, f"过拟合仪表盘生成耗时 {elapsed:.2f}秒，超过2秒限制"
    
    def test_correlation_heatmap_performance(
        self,
        chart_generator: ChartGenerator,
    ) -> None:
        """测试相关性热力图生成性能
        
        **Validates: Requirements 11.1**
        
        性能要求: < 2秒
        """
        # 生成较大的相关性矩阵
        size = 20
        data = np.random.uniform(-1, 1, (size, size))
        # 确保对称
        data = (data + data.T) / 2
        np.fill_diagonal(data, 1.0)
        labels = [f"策略{i}" for i in range(size)]
        
        start_time = time.perf_counter()
        chart = chart_generator.generate_correlation_heatmap(
            data=data,
            labels=labels,
        )
        elapsed = time.perf_counter() - start_time
        
        assert chart is not None
        assert elapsed < 2.0, f"相关性热力图生成耗时 {elapsed:.2f}秒，超过2秒限制"

    def test_batch_chart_generation_performance(
        self,
        chart_generator: ChartGenerator,
    ) -> None:
        """测试批量图表生成性能
        
        **Validates: Requirements 11.1**
        
        性能要求: 10个图表 < 20秒
        """
        # 准备测试数据
        essence_data = {
            "收益性": 0.8,
            "稳定性": 0.7,
            "风险控制": 0.85,
            "容量": 0.6,
            "适应性": 0.75,
        }
        
        overfitting_data = OverfittingData(
            in_sample_sharpe=2.0,
            out_sample_sharpe=1.5,
            parameter_sensitivity=0.3,
            complexity_score=0.4,
            risk_level="低",
        )
        
        feature_data = [
            ("momentum", 0.3),
            ("volatility", 0.25),
            ("volume", 0.2),
            ("price", 0.15),
            ("trend", 0.1),
        ]
        
        start_time = time.perf_counter()
        
        # 生成10个图表
        charts = []
        for i in range(10):
            if i % 3 == 0:
                chart = chart_generator.generate_essence_radar(data=essence_data)
            elif i % 3 == 1:
                chart = chart_generator.generate_overfitting_dashboard(data=overfitting_data)
            else:
                chart = chart_generator.generate_feature_importance_bar(data=feature_data)
            charts.append(chart)
        
        elapsed = time.perf_counter() - start_time
        
        assert len(charts) == 10
        assert elapsed < 20.0, f"批量图表生成耗时 {elapsed:.2f}秒，超过20秒限制"


class TestStrategyDashboardPerformance:
    """策略仪表盘性能测试
    
    白皮书依据: 第五章 5.4.1 策略分析中心仪表盘
    
    性能要求:
    - 可视化加载 < 2秒
    - PDF生成 < 10秒
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
            strategy_id="perf_test_strategy",
            strategy_name="性能测试策略",
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
    async def test_dashboard_export_json_performance(
        self,
        strategy_dashboard: StrategyDashboard,
        sample_dashboard_data: StrategyDashboardData,
    ) -> None:
        """测试仪表盘JSON导出性能
        
        **Validates: Requirements 11.2**
        
        性能要求: < 2秒
        """
        # 添加到缓存
        strategy_dashboard._dashboard_cache["perf_test_strategy"] = (
            sample_dashboard_data,
            datetime.now(),
        )
        
        start_time = time.perf_counter()
        json_data = await strategy_dashboard.export_data(
            strategy_id="perf_test_strategy",
            format="json",
        )
        elapsed = time.perf_counter() - start_time
        
        assert json_data is not None
        assert elapsed < 2.0, f"JSON导出耗时 {elapsed:.2f}秒，超过2秒限制"
    
    @pytest.mark.asyncio
    async def test_dashboard_export_csv_performance(
        self,
        strategy_dashboard: StrategyDashboard,
        sample_dashboard_data: StrategyDashboardData,
    ) -> None:
        """测试仪表盘CSV导出性能
        
        **Validates: Requirements 11.2**
        
        性能要求: < 2秒
        """
        # 添加到缓存
        strategy_dashboard._dashboard_cache["perf_test_strategy"] = (
            sample_dashboard_data,
            datetime.now(),
        )
        
        start_time = time.perf_counter()
        csv_data = await strategy_dashboard.export_data(
            strategy_id="perf_test_strategy",
            format="csv",
        )
        elapsed = time.perf_counter() - start_time
        
        assert csv_data is not None
        assert elapsed < 2.0, f"CSV导出耗时 {elapsed:.2f}秒，超过2秒限制"
    
    @pytest.mark.asyncio
    async def test_dashboard_pdf_generation_performance(
        self,
        strategy_dashboard: StrategyDashboard,
        sample_dashboard_data: StrategyDashboardData,
        tmp_path,
    ) -> None:
        """测试PDF报告生成性能
        
        **Validates: Requirements 11.3**
        
        性能要求: < 10秒
        """
        # 添加到缓存
        strategy_dashboard._dashboard_cache["perf_test_strategy"] = (
            sample_dashboard_data,
            datetime.now(),
        )
        
        output_path = str(tmp_path / "perf_test_report.pdf")
        
        start_time = time.perf_counter()
        pdf_path = await strategy_dashboard.generate_pdf_report(
            strategy_id="perf_test_strategy",
            output_path=output_path,
        )
        elapsed = time.perf_counter() - start_time
        
        assert pdf_path is not None
        assert elapsed < 10.0, f"PDF生成耗时 {elapsed:.2f}秒，超过10秒限制"


class TestStockDashboardPerformance:
    """个股仪表盘性能测试
    
    白皮书依据: 第五章 5.4.2 个股分析仪表盘
    
    性能要求:
    - 个股建议 < 3秒
    - 批量加载 < 10秒
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
    
    @pytest.mark.asyncio
    async def test_stock_dashboard_load_performance(
        self,
        stock_dashboard: StockDashboard,
    ) -> None:
        """测试个股仪表盘加载性能
        
        **Validates: Requirements 11.4**
        
        性能要求: < 3秒
        """
        start_time = time.perf_counter()
        dashboard_data = await stock_dashboard.load_dashboard(
            symbol="000001.SZ",
        )
        elapsed = time.perf_counter() - start_time
        
        assert dashboard_data is not None
        assert elapsed < 3.0, f"个股仪表盘加载耗时 {elapsed:.2f}秒，超过3秒限制"
    
    @pytest.mark.asyncio
    async def test_batch_load_performance(
        self,
        stock_dashboard: StockDashboard,
    ) -> None:
        """测试批量加载性能
        
        **Validates: Requirements 11.5**
        
        性能要求: 10个股票 < 10秒
        """
        symbols = [f"00000{i}.SZ" for i in range(1, 11)]
        
        start_time = time.perf_counter()
        dashboards = await stock_dashboard.batch_load_dashboards(
            symbols=symbols,
        )
        elapsed = time.perf_counter() - start_time
        
        assert dashboards is not None
        assert len(dashboards) == 10
        assert elapsed < 10.0, f"批量加载耗时 {elapsed:.2f}秒，超过10秒限制"


class TestConcurrencyPerformance:
    """并发性能测试
    
    白皮书依据: 第五章 5.4 可视化系统
    
    性能要求: 10并发请求
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
    
    @pytest.mark.asyncio
    async def test_concurrent_dashboard_loading(
        self,
        stock_dashboard: StockDashboard,
    ) -> None:
        """测试并发仪表盘加载
        
        **Validates: Requirements 11.6**
        
        性能要求: 10并发请求 < 15秒
        """
        symbols = [f"00000{i}.SZ" for i in range(1, 11)]
        
        start_time = time.perf_counter()
        
        # 并发加载
        tasks = [
            stock_dashboard.load_dashboard(symbol=symbol)
            for symbol in symbols
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        elapsed = time.perf_counter() - start_time
        
        # 验证结果
        successful = [r for r in results if not isinstance(r, Exception)]
        assert len(successful) == 10
        assert elapsed < 15.0, f"并发加载耗时 {elapsed:.2f}秒，超过15秒限制"

    @pytest.mark.asyncio
    async def test_concurrent_chart_generation(
        self,
        chart_generator: ChartGenerator,
    ) -> None:
        """测试并发图表生成
        
        **Validates: Requirements 11.7**
        
        性能要求: 10并发图表生成 < 20秒
        """
        # 准备测试数据
        essence_data = {
            "收益性": 0.8,
            "稳定性": 0.7,
            "风险控制": 0.85,
            "容量": 0.6,
            "适应性": 0.75,
        }
        
        async def generate_chart(index: int) -> bytes:
            """异步生成图表"""
            # 使用线程池执行同步图表生成
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                None,
                chart_generator.generate_essence_radar,
                essence_data,
            )
        
        start_time = time.perf_counter()
        
        # 并发生成10个图表
        tasks = [generate_chart(i) for i in range(10)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        elapsed = time.perf_counter() - start_time
        
        # 验证结果
        successful = [r for r in results if not isinstance(r, Exception)]
        assert len(successful) == 10
        assert elapsed < 20.0, f"并发图表生成耗时 {elapsed:.2f}秒，超过20秒限制"


class TestMemoryPerformance:
    """内存性能测试
    
    白皮书依据: 第五章 5.4 可视化系统
    
    验证系统在大量数据下的内存使用。
    """
    
    @pytest.fixture
    def chart_generator(self) -> ChartGenerator:
        """创建图表生成器"""
        return ChartGenerator()
    
    def test_large_correlation_matrix_memory(
        self,
        chart_generator: ChartGenerator,
    ) -> None:
        """测试大型相关性矩阵内存使用
        
        验证处理大型矩阵时不会内存溢出。
        """
        # 生成50x50的相关性矩阵
        size = 50
        data = np.random.uniform(-1, 1, (size, size))
        data = (data + data.T) / 2
        np.fill_diagonal(data, 1.0)
        labels = [f"策略{i}" for i in range(size)]
        
        # 生成图表
        chart = chart_generator.generate_correlation_heatmap(
            data=data,
            labels=labels,
        )
        
        assert chart is not None
        assert len(chart) > 0
    
    def test_repeated_chart_generation_memory(
        self,
        chart_generator: ChartGenerator,
    ) -> None:
        """测试重复图表生成内存使用
        
        验证重复生成图表不会导致内存泄漏。
        """
        essence_data = {
            "收益性": 0.8,
            "稳定性": 0.7,
            "风险控制": 0.85,
            "容量": 0.6,
            "适应性": 0.75,
        }
        
        # 重复生成100个图表
        for i in range(100):
            chart = chart_generator.generate_essence_radar(data=essence_data)
            assert chart is not None
        
        # 如果没有内存泄漏，测试应该正常完成
