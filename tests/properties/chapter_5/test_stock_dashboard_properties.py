"""个股仪表盘属性测试

白皮书依据: 第五章 5.4.2 个股分析仪表盘

本模块实现了个股仪表盘的属性测试，验证：
- Property 17: 个股仪表盘数据完整性

**Validates: Requirements 6.1-6.9**
"""

import asyncio
import json
import time
from datetime import datetime
from typing import Dict, List

import pytest
from hypothesis import given, settings, strategies as st

from src.brain.visualization.stock_dashboard import (
    StockDashboard,
    StockDashboardLoadError,
    RecommendationRefreshError,
    SmartMoneyAnalysisError,
)
from src.brain.visualization.data_models import (
    StockDashboardData,
    StockRecommendation,
    SmartMoneyAnalysis,
    RecommendationAction,
    SmartMoneyType,
    BehaviorPattern,
    RiskLevel,
    PositionSuggestion,
    HoldingPeriod,
)


# ============================================================================
# 测试夹具
# ============================================================================

@pytest.fixture
def stock_dashboard():
    """创建个股仪表盘实例"""
    return StockDashboard()


@pytest.fixture
def sample_symbol():
    """创建示例股票代码"""
    return "000001"


@pytest.fixture
def sample_recommendation():
    """创建示例个股建议"""
    return StockRecommendation(
        action=RecommendationAction.BUY,
        confidence=0.75,
        current_price=15.50,
        target_price=18.00,
        stop_loss_price=14.00,
        buy_price_range=(15.00, 16.00),
        position_suggestion=PositionSuggestion.STANDARD,
        holding_period=HoldingPeriod.MEDIUM,
        support_reasons=[
            "技术面突破关键阻力位",
            "主力资金持续流入",
            "行业景气度上升",
        ],
        risk_warnings=[
            "大盘整体波动较大",
            "需关注政策风险",
        ],
    )


@pytest.fixture
def sample_smart_money_analysis():
    """创建示例主力资金分析"""
    return SmartMoneyAnalysis(
        smart_money_type=SmartMoneyType.INSTITUTION,
        position_cost=14.50,
        holding_ratio=0.25,
        current_profit=0.07,
        behavior_pattern=BehaviorPattern.ACCUMULATING,
        risk_level=RiskLevel.LOW,
    )


@pytest.fixture
def sample_dashboard_data(sample_recommendation, sample_smart_money_analysis):
    """创建示例仪表盘数据"""
    return StockDashboardData(
        symbol="000001",
        name="平安银行",
        recommendation=sample_recommendation,
        smart_money_analysis=sample_smart_money_analysis,
    )


# ============================================================================
# Hypothesis策略
# ============================================================================

@st.composite
def symbol_strategy(draw):
    """生成股票代码的策略"""
    # 生成6位数字股票代码
    code = draw(st.integers(min_value=1, max_value=999999))
    return f"{code:06d}"


@st.composite
def recommendation_action_strategy(draw):
    """生成操作建议的策略"""
    return draw(st.sampled_from(list(RecommendationAction)))


@st.composite
def smart_money_type_strategy(draw):
    """生成主力类型的策略"""
    return draw(st.sampled_from(list(SmartMoneyType)))


# ============================================================================
# Property 17: 个股仪表盘数据完整性
# ============================================================================

class TestStockDashboardDataCompleteness:
    """测试个股仪表盘数据完整性
    
    **Feature: chapter-5-darwin-visualization-redis, Property 17: Stock dashboard data completeness**
    
    **Validates: Requirements 6.1-6.9**
    """
    
    @pytest.mark.asyncio
    async def test_dashboard_contains_recommendation_action(
        self,
        stock_dashboard,
        sample_symbol,
    ):
        """测试仪表盘包含操作建议
        
        **Validates: Requirements 6.1**
        """
        dashboard_data = await stock_dashboard.load_dashboard(sample_symbol)
        
        assert hasattr(dashboard_data, 'recommendation')
        assert hasattr(dashboard_data.recommendation, 'action')
        assert isinstance(dashboard_data.recommendation.action, RecommendationAction)
    
    @pytest.mark.asyncio
    async def test_dashboard_contains_confidence(
        self,
        stock_dashboard,
        sample_symbol,
    ):
        """测试仪表盘包含置信度
        
        **Validates: Requirements 6.2**
        """
        dashboard_data = await stock_dashboard.load_dashboard(sample_symbol)
        
        assert hasattr(dashboard_data.recommendation, 'confidence')
        assert 0 <= dashboard_data.recommendation.confidence <= 1
    
    @pytest.mark.asyncio
    async def test_dashboard_contains_support_reasons(
        self,
        stock_dashboard,
        sample_symbol,
    ):
        """测试仪表盘包含支持原因
        
        **Validates: Requirements 6.3**
        """
        dashboard_data = await stock_dashboard.load_dashboard(sample_symbol)
        
        assert hasattr(dashboard_data.recommendation, 'support_reasons')
        assert isinstance(dashboard_data.recommendation.support_reasons, list)
    
    @pytest.mark.asyncio
    async def test_dashboard_contains_risk_warnings(
        self,
        stock_dashboard,
        sample_symbol,
    ):
        """测试仪表盘包含风险提示
        
        **Validates: Requirements 6.4**
        """
        dashboard_data = await stock_dashboard.load_dashboard(sample_symbol)
        
        assert hasattr(dashboard_data.recommendation, 'risk_warnings')
        assert isinstance(dashboard_data.recommendation.risk_warnings, list)
    
    @pytest.mark.asyncio
    async def test_dashboard_contains_target_price(
        self,
        stock_dashboard,
        sample_symbol,
    ):
        """测试仪表盘包含目标价
        
        **Validates: Requirements 6.5**
        """
        dashboard_data = await stock_dashboard.load_dashboard(sample_symbol)
        
        assert hasattr(dashboard_data.recommendation, 'target_price')
        assert dashboard_data.recommendation.target_price > 0
    
    @pytest.mark.asyncio
    async def test_dashboard_contains_stop_loss_price(
        self,
        stock_dashboard,
        sample_symbol,
    ):
        """测试仪表盘包含止损价
        
        **Validates: Requirements 6.5**
        """
        dashboard_data = await stock_dashboard.load_dashboard(sample_symbol)
        
        assert hasattr(dashboard_data.recommendation, 'stop_loss_price')
        assert dashboard_data.recommendation.stop_loss_price > 0
    
    @pytest.mark.asyncio
    async def test_dashboard_contains_position_suggestion(
        self,
        stock_dashboard,
        sample_symbol,
    ):
        """测试仪表盘包含仓位建议
        
        **Validates: Requirements 6.6**
        """
        dashboard_data = await stock_dashboard.load_dashboard(sample_symbol)
        
        assert hasattr(dashboard_data.recommendation, 'position_suggestion')
        assert isinstance(dashboard_data.recommendation.position_suggestion, PositionSuggestion)
    
    @pytest.mark.asyncio
    async def test_dashboard_contains_holding_period(
        self,
        stock_dashboard,
        sample_symbol,
    ):
        """测试仪表盘包含持有周期
        
        **Validates: Requirements 6.7**
        """
        dashboard_data = await stock_dashboard.load_dashboard(sample_symbol)
        
        assert hasattr(dashboard_data.recommendation, 'holding_period')
        assert isinstance(dashboard_data.recommendation.holding_period, HoldingPeriod)
    
    @pytest.mark.asyncio
    async def test_dashboard_contains_smart_money_analysis(
        self,
        stock_dashboard,
        sample_symbol,
    ):
        """测试仪表盘包含主力资金深度分析
        
        **Validates: Requirements 6.8**
        """
        dashboard_data = await stock_dashboard.load_dashboard(sample_symbol)
        
        assert hasattr(dashboard_data, 'smart_money_analysis')
        assert isinstance(dashboard_data.smart_money_analysis, SmartMoneyAnalysis)
    
    @pytest.mark.asyncio
    async def test_smart_money_analysis_contains_all_fields(
        self,
        stock_dashboard,
        sample_symbol,
    ):
        """测试主力资金分析包含所有必需字段
        
        **Validates: Requirements 6.9**
        """
        dashboard_data = await stock_dashboard.load_dashboard(sample_symbol)
        sma = dashboard_data.smart_money_analysis
        
        # 验证主力类型
        assert hasattr(sma, 'smart_money_type')
        assert isinstance(sma.smart_money_type, SmartMoneyType)
        
        # 验证建仓成本
        assert hasattr(sma, 'position_cost')
        assert sma.position_cost > 0
        
        # 验证持股比例
        assert hasattr(sma, 'holding_ratio')
        assert 0 <= sma.holding_ratio <= 1
        
        # 验证当前盈利
        assert hasattr(sma, 'current_profit')
        
        # 验证行为模式
        assert hasattr(sma, 'behavior_pattern')
        assert isinstance(sma.behavior_pattern, BehaviorPattern)
        
        # 验证风险等级
        assert hasattr(sma, 'risk_level')
        assert isinstance(sma.risk_level, RiskLevel)
    
    @given(symbol=symbol_strategy())
    @settings(max_examples=10, deadline=30000)
    def test_dashboard_data_completeness_with_random_symbols(self, symbol):
        """测试随机股票代码的仪表盘数据完整性
        
        **Validates: Requirements 6.1-6.9**
        """
        dashboard = StockDashboard()
        
        # 使用新的事件循环
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            dashboard_data = loop.run_until_complete(
                dashboard.load_dashboard(symbol)
            )
        finally:
            loop.close()
        
        # 验证所有必需字段存在
        assert dashboard_data.symbol is not None
        assert dashboard_data.name is not None
        assert dashboard_data.recommendation is not None
        assert dashboard_data.smart_money_analysis is not None
        
        # 验证建议字段
        rec = dashboard_data.recommendation
        assert isinstance(rec.action, RecommendationAction)
        assert 0 <= rec.confidence <= 1
        assert rec.current_price > 0
        assert rec.target_price > 0
        assert rec.stop_loss_price > 0
        assert isinstance(rec.position_suggestion, PositionSuggestion)
        assert isinstance(rec.holding_period, HoldingPeriod)
        
        # 验证主力资金分析字段
        sma = dashboard_data.smart_money_analysis
        assert isinstance(sma.smart_money_type, SmartMoneyType)
        assert sma.position_cost > 0
        assert 0 <= sma.holding_ratio <= 1
        assert isinstance(sma.behavior_pattern, BehaviorPattern)
        assert isinstance(sma.risk_level, RiskLevel)


# ============================================================================
# 仪表盘加载性能测试
# ============================================================================

class TestDashboardLoadPerformance:
    """测试仪表盘加载性能"""
    
    @pytest.mark.asyncio
    async def test_dashboard_loads_within_3_seconds(
        self,
        stock_dashboard,
        sample_symbol,
    ):
        """测试仪表盘加载时间 < 3秒
        
        **Validates: Performance requirement**
        """
        start_time = time.time()
        await stock_dashboard.load_dashboard(sample_symbol)
        elapsed = time.time() - start_time
        
        assert elapsed < 3.0, f"加载时间 {elapsed:.2f}s 超过3秒限制"
    
    @pytest.mark.asyncio
    async def test_cached_dashboard_loads_faster(
        self,
        stock_dashboard,
        sample_symbol,
    ):
        """测试缓存的仪表盘加载更快"""
        # 第一次加载
        await stock_dashboard.load_dashboard(sample_symbol)
        
        # 第二次加载（应该使用缓存）
        start_time = time.time()
        await stock_dashboard.load_dashboard(sample_symbol)
        cached_elapsed = time.time() - start_time
        
        # 缓存加载应该非常快
        assert cached_elapsed < 0.1, f"缓存加载时间 {cached_elapsed:.2f}s 过长"


# ============================================================================
# 刷新功能测试
# ============================================================================

class TestRefreshFunctions:
    """测试刷新功能"""
    
    @pytest.mark.asyncio
    async def test_refresh_recommendation(
        self,
        stock_dashboard,
        sample_symbol,
    ):
        """测试刷新个股建议"""
        # 先加载仪表盘
        await stock_dashboard.load_dashboard(sample_symbol)
        
        # 刷新建议
        recommendation = await stock_dashboard.refresh_recommendation(sample_symbol)
        
        assert recommendation is not None
        assert isinstance(recommendation.action, RecommendationAction)
    
    @pytest.mark.asyncio
    async def test_refresh_smart_money_analysis(
        self,
        stock_dashboard,
        sample_symbol,
    ):
        """测试刷新主力资金分析"""
        # 先加载仪表盘
        await stock_dashboard.load_dashboard(sample_symbol)
        
        # 刷新分析
        analysis = await stock_dashboard.refresh_smart_money_analysis(sample_symbol)
        
        assert analysis is not None
        assert isinstance(analysis.smart_money_type, SmartMoneyType)
    
    @pytest.mark.asyncio
    async def test_refresh_with_empty_symbol_raises_error(
        self,
        stock_dashboard,
    ):
        """测试空股票代码刷新抛出错误"""
        with pytest.raises(ValueError, match="股票代码不能为空"):
            await stock_dashboard.refresh_recommendation("")
        
        with pytest.raises(ValueError, match="股票代码不能为空"):
            await stock_dashboard.refresh_smart_money_analysis("")


# ============================================================================
# 缓存管理测试
# ============================================================================

class TestCacheManagement:
    """测试缓存管理功能"""
    
    @pytest.mark.asyncio
    async def test_clear_cache_for_symbol(
        self,
        stock_dashboard,
        sample_symbol,
    ):
        """测试清除特定股票缓存"""
        # 加载以创建缓存
        await stock_dashboard.load_dashboard(sample_symbol)
        
        # 验证缓存存在
        cached = stock_dashboard.get_cached_dashboard(sample_symbol)
        assert cached is not None
        
        # 清除缓存
        stock_dashboard.clear_cache(sample_symbol)
        
        # 验证缓存已清除
        cached = stock_dashboard.get_cached_dashboard(sample_symbol)
        assert cached is None
    
    @pytest.mark.asyncio
    async def test_clear_all_cache(
        self,
        stock_dashboard,
    ):
        """测试清除所有缓存"""
        # 加载多个股票
        await stock_dashboard.load_dashboard("000001")
        await stock_dashboard.load_dashboard("000002")
        
        # 清除所有缓存
        stock_dashboard.clear_cache()
        
        # 验证所有缓存已清除
        stats = stock_dashboard.get_cache_stats()
        assert stats['total_cached'] == 0
    
    def test_get_cache_stats(self, stock_dashboard):
        """测试获取缓存统计信息"""
        stats = stock_dashboard.get_cache_stats()
        
        assert 'total_cached' in stats
        assert 'valid_count' in stats
        assert 'expired_count' in stats
        assert 'cache_ttl' in stats


# ============================================================================
# 批量加载测试
# ============================================================================

class TestBatchLoad:
    """测试批量加载功能"""
    
    @pytest.mark.asyncio
    async def test_batch_load_dashboards(
        self,
        stock_dashboard,
    ):
        """测试批量加载个股仪表盘"""
        symbols = ["000001", "000002", "000003"]
        
        dashboards = await stock_dashboard.batch_load_dashboards(symbols)
        
        assert len(dashboards) == len(symbols)
        for symbol in symbols:
            assert symbol in dashboards
            assert isinstance(dashboards[symbol], StockDashboardData)
    
    @pytest.mark.asyncio
    async def test_batch_load_empty_list(
        self,
        stock_dashboard,
    ):
        """测试批量加载空列表"""
        dashboards = await stock_dashboard.batch_load_dashboards([])
        
        assert dashboards == {}


# ============================================================================
# 数据导出测试
# ============================================================================

class TestDataExport:
    """测试数据导出功能"""
    
    def test_export_to_dict(
        self,
        stock_dashboard,
        sample_dashboard_data,
    ):
        """测试导出为字典"""
        data_dict = stock_dashboard.export_to_dict(sample_dashboard_data)
        
        assert isinstance(data_dict, dict)
        assert 'symbol' in data_dict
        assert 'name' in data_dict
        assert 'recommendation' in data_dict
        assert 'smart_money_analysis' in data_dict
    
    def test_export_to_json(
        self,
        stock_dashboard,
        sample_dashboard_data,
    ):
        """测试导出为JSON"""
        json_str = stock_dashboard.export_to_json(sample_dashboard_data)
        
        assert isinstance(json_str, str)
        
        # 验证是有效的JSON
        parsed = json.loads(json_str)
        assert 'symbol' in parsed
    
    def test_get_recommendation_summary(
        self,
        stock_dashboard,
        sample_dashboard_data,
    ):
        """测试获取建议摘要"""
        summary = stock_dashboard.get_recommendation_summary(sample_dashboard_data)
        
        assert isinstance(summary, str)
        assert sample_dashboard_data.symbol in summary
        assert sample_dashboard_data.name in summary


# ============================================================================
# 边界情况测试
# ============================================================================

class TestEdgeCases:
    """测试边界情况"""
    
    @pytest.mark.asyncio
    async def test_empty_symbol_raises_error(self, stock_dashboard):
        """测试空股票代码抛出错误"""
        with pytest.raises(ValueError, match="股票代码不能为空"):
            await stock_dashboard.load_dashboard("")
    
    @pytest.mark.asyncio
    async def test_force_refresh_bypasses_cache(
        self,
        stock_dashboard,
        sample_symbol,
    ):
        """测试强制刷新绕过缓存"""
        # 第一次加载
        data1 = await stock_dashboard.load_dashboard(sample_symbol)
        
        # 强制刷新
        data2 = await stock_dashboard.load_dashboard(
            sample_symbol,
            force_refresh=True,
        )
        
        # 两次加载都应该成功
        assert data1 is not None
        assert data2 is not None
    
    @pytest.mark.asyncio
    async def test_symbol_normalization(
        self,
        stock_dashboard,
    ):
        """测试股票代码标准化"""
        # 测试带空格的代码
        data1 = await stock_dashboard.load_dashboard(" 000001 ")
        assert data1.symbol == "000001"
        
        # 测试小写代码
        data2 = await stock_dashboard.load_dashboard("sh000001")
        assert data2 is not None


# ============================================================================
# 数据模型序列化测试
# ============================================================================

class TestDataSerialization:
    """测试数据模型序列化"""
    
    def test_recommendation_to_dict(self, sample_recommendation):
        """测试个股建议转换为字典"""
        data_dict = sample_recommendation.to_dict()
        
        assert isinstance(data_dict, dict)
        assert data_dict['action'] == sample_recommendation.action.value
        assert data_dict['confidence'] == sample_recommendation.confidence
    
    def test_recommendation_from_dict(self, sample_recommendation):
        """测试从字典创建个股建议"""
        data_dict = sample_recommendation.to_dict()
        restored = StockRecommendation.from_dict(data_dict)
        
        assert restored.action == sample_recommendation.action
        assert restored.confidence == sample_recommendation.confidence
    
    def test_smart_money_analysis_to_dict(self, sample_smart_money_analysis):
        """测试主力资金分析转换为字典"""
        data_dict = sample_smart_money_analysis.to_dict()
        
        assert isinstance(data_dict, dict)
        assert data_dict['smart_money_type'] == sample_smart_money_analysis.smart_money_type.value
    
    def test_smart_money_analysis_from_dict(self, sample_smart_money_analysis):
        """测试从字典创建主力资金分析"""
        data_dict = sample_smart_money_analysis.to_dict()
        restored = SmartMoneyAnalysis.from_dict(data_dict)
        
        assert restored.smart_money_type == sample_smart_money_analysis.smart_money_type
        assert restored.position_cost == sample_smart_money_analysis.position_cost
    
    def test_dashboard_data_round_trip(self, sample_dashboard_data):
        """测试仪表盘数据序列化往返"""
        data_dict = sample_dashboard_data.to_dict()
        json_str = json.dumps(data_dict)
        restored_dict = json.loads(json_str)
        restored = StockDashboardData.from_dict(restored_dict)
        
        assert restored.symbol == sample_dashboard_data.symbol
        assert restored.name == sample_dashboard_data.name


# ============================================================================
# 运行测试
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
