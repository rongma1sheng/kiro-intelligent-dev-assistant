"""策略仪表盘属性测试

白皮书依据: 第五章 5.4.1 策略分析中心仪表盘

本模块实现了策略仪表盘的属性测试，验证：
- Property 16: 策略仪表盘数据完整性

**Validates: Requirements 5.1-5.9**
"""

import asyncio
import json
import time
from datetime import datetime
from typing import Dict, List, Tuple

import pytest
from hypothesis import given, settings, strategies as st

from src.brain.visualization.strategy_dashboard import (
    StrategyDashboard,
    DashboardLoadError,
    PDFGenerationError,
    DataExportError,
)
from src.brain.visualization.data_models import (
    StrategyDashboardData,
    OverfittingRiskLevel,
    MarketAdaptation,
)
from src.brain.visualization.charts import ChartGenerator


# ============================================================================
# 测试夹具
# ============================================================================

@pytest.fixture
def strategy_dashboard():
    """创建策略仪表盘实例"""
    return StrategyDashboard()


@pytest.fixture
def sample_strategy_id():
    """创建示例策略ID"""
    return "test_strategy_001"


@pytest.fixture
def sample_dashboard_data():
    """创建示例仪表盘数据"""
    return StrategyDashboardData(
        strategy_id="test_strategy_001",
        strategy_name="测试策略",
        overall_score=75.5,
        overfitting_risk=OverfittingRiskLevel.LOW,
        market_adaptation=MarketAdaptation.HIGH,
        essence_radar_data={
            "动量": 0.8,
            "价值": 0.6,
            "质量": 0.7,
            "波动": 0.5,
            "流动性": 0.9,
        },
        risk_matrix_data=[
            [0.3, 0.5, 0.2],
            [0.4, 0.3, 0.4],
            [0.2, 0.4, 0.3],
        ],
        feature_importance_data=[
            ("动量因子", 0.25),
            ("价值因子", 0.20),
            ("质量因子", 0.18),
        ],
        market_adaptation_matrix={
            "牛市": {"收益": 0.8, "风险": 0.3, "稳定性": 0.7},
            "熊市": {"收益": 0.4, "风险": 0.6, "稳定性": 0.5},
        },
        evolution_visualization_data={
            "generations": [0, 1, 2, 3, 4],
            "fitness_values": [0.5, 0.55, 0.6, 0.65, 0.7],
        },
    )


# ============================================================================
# Hypothesis策略
# ============================================================================

@st.composite
def strategy_id_strategy(draw):
    """生成策略ID的策略"""
    prefix = draw(st.sampled_from(["strategy", "test", "prod", "dev"]))
    suffix = draw(st.integers(min_value=1, max_value=9999))
    return f"{prefix}_{suffix:04d}"


@st.composite
def essence_radar_strategy(draw):
    """生成策略本质雷达图数据的策略"""
    dimensions = ["动量", "价值", "质量", "波动", "流动性"]
    values = [draw(st.floats(min_value=0, max_value=1)) for _ in dimensions]
    return dict(zip(dimensions, values))


@st.composite
def feature_importance_strategy(draw):
    """生成特征重要性数据的策略"""
    num_features = draw(st.integers(min_value=3, max_value=10))
    features = [f"特征{i}" for i in range(num_features)]
    importances = [draw(st.floats(min_value=0, max_value=1)) for _ in range(num_features)]
    return list(zip(features, importances))


# ============================================================================
# Property 16: 策略仪表盘数据完整性
# ============================================================================

class TestStrategyDashboardDataCompleteness:
    """测试策略仪表盘数据完整性
    
    **Feature: chapter-5-darwin-visualization-redis, Property 16: Strategy dashboard data completeness**
    
    **Validates: Requirements 5.1-5.9**
    """
    
    @pytest.mark.asyncio
    async def test_dashboard_contains_overall_score(
        self,
        strategy_dashboard,
        sample_strategy_id,
    ):
        """测试仪表盘包含综合评分
        
        **Validates: Requirements 5.1**
        """
        dashboard_data = await strategy_dashboard.load_dashboard(sample_strategy_id)
        
        assert hasattr(dashboard_data, 'overall_score')
        assert 0 <= dashboard_data.overall_score <= 100
    
    @pytest.mark.asyncio
    async def test_dashboard_contains_overfitting_risk(
        self,
        strategy_dashboard,
        sample_strategy_id,
    ):
        """测试仪表盘包含过拟合风险等级
        
        **Validates: Requirements 5.2**
        """
        dashboard_data = await strategy_dashboard.load_dashboard(sample_strategy_id)
        
        assert hasattr(dashboard_data, 'overfitting_risk')
        assert isinstance(dashboard_data.overfitting_risk, OverfittingRiskLevel)
    
    @pytest.mark.asyncio
    async def test_dashboard_contains_market_adaptation(
        self,
        strategy_dashboard,
        sample_strategy_id,
    ):
        """测试仪表盘包含市场适配度
        
        **Validates: Requirements 5.3**
        """
        dashboard_data = await strategy_dashboard.load_dashboard(sample_strategy_id)
        
        assert hasattr(dashboard_data, 'market_adaptation')
        assert isinstance(dashboard_data.market_adaptation, MarketAdaptation)
    
    @pytest.mark.asyncio
    async def test_dashboard_contains_essence_radar_data(
        self,
        strategy_dashboard,
        sample_strategy_id,
    ):
        """测试仪表盘包含策略本质雷达图数据
        
        **Validates: Requirements 5.4**
        """
        dashboard_data = await strategy_dashboard.load_dashboard(sample_strategy_id)
        
        assert hasattr(dashboard_data, 'essence_radar_data')
        assert isinstance(dashboard_data.essence_radar_data, dict)
        assert len(dashboard_data.essence_radar_data) > 0
        
        # 验证所有值在有效范围内
        for dimension, value in dashboard_data.essence_radar_data.items():
            assert isinstance(dimension, str)
            assert 0 <= value <= 1
    
    @pytest.mark.asyncio
    async def test_dashboard_contains_risk_matrix_data(
        self,
        strategy_dashboard,
        sample_strategy_id,
    ):
        """测试仪表盘包含风险矩阵热力图数据
        
        **Validates: Requirements 5.5**
        """
        dashboard_data = await strategy_dashboard.load_dashboard(sample_strategy_id)
        
        assert hasattr(dashboard_data, 'risk_matrix_data')
        assert isinstance(dashboard_data.risk_matrix_data, list)
        assert len(dashboard_data.risk_matrix_data) > 0
        
        # 验证矩阵结构
        for row in dashboard_data.risk_matrix_data:
            assert isinstance(row, list)
            for value in row:
                assert isinstance(value, (int, float))
    
    @pytest.mark.asyncio
    async def test_dashboard_contains_feature_importance_data(
        self,
        strategy_dashboard,
        sample_strategy_id,
    ):
        """测试仪表盘包含特征重要性排名数据
        
        **Validates: Requirements 5.6**
        """
        dashboard_data = await strategy_dashboard.load_dashboard(sample_strategy_id)
        
        assert hasattr(dashboard_data, 'feature_importance_data')
        assert isinstance(dashboard_data.feature_importance_data, list)
        assert len(dashboard_data.feature_importance_data) > 0
        
        # 验证数据结构
        for item in dashboard_data.feature_importance_data:
            assert isinstance(item, tuple)
            assert len(item) == 2
            feature_name, importance = item
            assert isinstance(feature_name, str)
            assert isinstance(importance, (int, float))
    
    @pytest.mark.asyncio
    async def test_dashboard_contains_market_adaptation_matrix(
        self,
        strategy_dashboard,
        sample_strategy_id,
    ):
        """测试仪表盘包含市场适配性矩阵数据
        
        **Validates: Requirements 5.7**
        """
        dashboard_data = await strategy_dashboard.load_dashboard(sample_strategy_id)
        
        assert hasattr(dashboard_data, 'market_adaptation_matrix')
        assert isinstance(dashboard_data.market_adaptation_matrix, dict)
        assert len(dashboard_data.market_adaptation_matrix) > 0
        
        # 验证矩阵结构
        for market_type, metrics in dashboard_data.market_adaptation_matrix.items():
            assert isinstance(market_type, str)
            assert isinstance(metrics, dict)
    
    @pytest.mark.asyncio
    async def test_dashboard_contains_evolution_visualization_data(
        self,
        strategy_dashboard,
        sample_strategy_id,
    ):
        """测试仪表盘包含进化过程可视化数据
        
        **Validates: Requirements 5.8**
        """
        dashboard_data = await strategy_dashboard.load_dashboard(sample_strategy_id)
        
        assert hasattr(dashboard_data, 'evolution_visualization_data')
        assert isinstance(dashboard_data.evolution_visualization_data, dict)
    
    @given(strategy_id=strategy_id_strategy())
    @settings(max_examples=10, deadline=30000)
    def test_dashboard_data_completeness_with_random_ids(self, strategy_id):
        """测试随机策略ID的仪表盘数据完整性
        
        **Validates: Requirements 5.1-5.9**
        """
        dashboard = StrategyDashboard()
        
        # 使用新的事件循环
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            dashboard_data = loop.run_until_complete(
                dashboard.load_dashboard(strategy_id)
            )
        finally:
            loop.close()
        
        # 验证所有必需字段存在
        assert dashboard_data.strategy_id == strategy_id
        assert dashboard_data.strategy_name is not None
        assert 0 <= dashboard_data.overall_score <= 100
        assert isinstance(dashboard_data.overfitting_risk, OverfittingRiskLevel)
        assert isinstance(dashboard_data.market_adaptation, MarketAdaptation)
        assert isinstance(dashboard_data.essence_radar_data, dict)
        assert isinstance(dashboard_data.risk_matrix_data, list)
        assert isinstance(dashboard_data.feature_importance_data, list)
        assert isinstance(dashboard_data.market_adaptation_matrix, dict)
        assert isinstance(dashboard_data.evolution_visualization_data, dict)


# ============================================================================
# 仪表盘加载性能测试
# ============================================================================

class TestDashboardLoadPerformance:
    """测试仪表盘加载性能
    
    **Validates: Requirements 5.9**
    """
    
    @pytest.mark.asyncio
    async def test_dashboard_loads_within_2_seconds(
        self,
        strategy_dashboard,
        sample_strategy_id,
    ):
        """测试仪表盘加载时间 < 2秒
        
        **Validates: Requirements 5.9**
        """
        start_time = time.time()
        await strategy_dashboard.load_dashboard(sample_strategy_id)
        elapsed = time.time() - start_time
        
        assert elapsed < 2.0, f"加载时间 {elapsed:.2f}s 超过2秒限制"
    
    @pytest.mark.asyncio
    async def test_cached_dashboard_loads_faster(
        self,
        strategy_dashboard,
        sample_strategy_id,
    ):
        """测试缓存的仪表盘加载更快"""
        # 第一次加载
        await strategy_dashboard.load_dashboard(sample_strategy_id)
        
        # 第二次加载（应该使用缓存）
        start_time = time.time()
        await strategy_dashboard.load_dashboard(sample_strategy_id)
        cached_elapsed = time.time() - start_time
        
        # 缓存加载应该非常快
        assert cached_elapsed < 0.1, f"缓存加载时间 {cached_elapsed:.2f}s 过长"


# ============================================================================
# 数据导出测试
# ============================================================================

class TestDataExport:
    """测试数据导出功能"""
    
    @pytest.mark.asyncio
    async def test_export_as_json(
        self,
        strategy_dashboard,
        sample_strategy_id,
    ):
        """测试导出为JSON格式"""
        data = await strategy_dashboard.export_data(sample_strategy_id, format='json')
        
        assert data is not None
        assert len(data) > 0
        
        # 验证是有效的JSON
        parsed = json.loads(data.decode('utf-8'))
        assert 'strategy_id' in parsed
        assert 'strategy_name' in parsed
        assert 'overall_score' in parsed
    
    @pytest.mark.asyncio
    async def test_export_as_csv(
        self,
        strategy_dashboard,
        sample_strategy_id,
    ):
        """测试导出为CSV格式"""
        data = await strategy_dashboard.export_data(sample_strategy_id, format='csv')
        
        assert data is not None
        assert len(data) > 0
        
        # 验证CSV内容
        content = data.decode('utf-8')
        assert '策略ID' in content or 'strategy_id' in content.lower()
    
    @pytest.mark.asyncio
    async def test_export_invalid_format_raises_error(
        self,
        strategy_dashboard,
        sample_strategy_id,
    ):
        """测试无效格式抛出错误"""
        with pytest.raises(ValueError, match="不支持的导出格式"):
            await strategy_dashboard.export_data(sample_strategy_id, format='xml')


# ============================================================================
# 历史记录测试
# ============================================================================

class TestHistoryRecords:
    """测试历史记录功能"""
    
    @pytest.mark.asyncio
    async def test_get_history_returns_list(
        self,
        strategy_dashboard,
        sample_strategy_id,
    ):
        """测试获取历史记录返回列表"""
        # 先加载一次以创建历史记录
        await strategy_dashboard.load_dashboard(sample_strategy_id)
        
        history = await strategy_dashboard.get_history(sample_strategy_id)
        
        assert isinstance(history, list)
    
    @pytest.mark.asyncio
    async def test_history_respects_limit(
        self,
        strategy_dashboard,
        sample_strategy_id,
    ):
        """测试历史记录遵守数量限制"""
        # 多次加载以创建多条历史记录
        for _ in range(5):
            await strategy_dashboard.load_dashboard(sample_strategy_id, force_refresh=True)
        
        history = await strategy_dashboard.get_history(sample_strategy_id, limit=3)
        
        assert len(history) <= 3
    
    @pytest.mark.asyncio
    async def test_history_invalid_limit_raises_error(
        self,
        strategy_dashboard,
        sample_strategy_id,
    ):
        """测试无效limit参数抛出错误"""
        with pytest.raises(ValueError, match="limit必须大于0"):
            await strategy_dashboard.get_history(sample_strategy_id, limit=0)


# ============================================================================
# 缓存管理测试
# ============================================================================

class TestCacheManagement:
    """测试缓存管理功能"""
    
    @pytest.mark.asyncio
    async def test_clear_cache_for_strategy(
        self,
        strategy_dashboard,
        sample_strategy_id,
    ):
        """测试清除特定策略缓存"""
        # 加载以创建缓存
        await strategy_dashboard.load_dashboard(sample_strategy_id)
        
        # 验证缓存存在
        cached = strategy_dashboard.get_cached_dashboard(sample_strategy_id)
        assert cached is not None
        
        # 清除缓存
        strategy_dashboard.clear_cache(sample_strategy_id)
        
        # 验证缓存已清除
        cached = strategy_dashboard.get_cached_dashboard(sample_strategy_id)
        assert cached is None
    
    @pytest.mark.asyncio
    async def test_clear_all_cache(
        self,
        strategy_dashboard,
    ):
        """测试清除所有缓存"""
        # 加载多个策略
        await strategy_dashboard.load_dashboard("strategy_001")
        await strategy_dashboard.load_dashboard("strategy_002")
        
        # 清除所有缓存
        strategy_dashboard.clear_cache()
        
        # 验证所有缓存已清除
        stats = strategy_dashboard.get_cache_stats()
        assert stats['total_cached'] == 0
    
    def test_get_cache_stats(self, strategy_dashboard):
        """测试获取缓存统计信息"""
        stats = strategy_dashboard.get_cache_stats()
        
        assert 'total_cached' in stats
        assert 'valid_count' in stats
        assert 'expired_count' in stats
        assert 'cache_ttl' in stats


# ============================================================================
# 边界情况测试
# ============================================================================

class TestEdgeCases:
    """测试边界情况"""
    
    @pytest.mark.asyncio
    async def test_empty_strategy_id_raises_error(self, strategy_dashboard):
        """测试空策略ID抛出错误"""
        with pytest.raises(ValueError, match="策略ID不能为空"):
            await strategy_dashboard.load_dashboard("")
    
    @pytest.mark.asyncio
    async def test_force_refresh_bypasses_cache(
        self,
        strategy_dashboard,
        sample_strategy_id,
    ):
        """测试强制刷新绕过缓存"""
        # 第一次加载
        data1 = await strategy_dashboard.load_dashboard(sample_strategy_id)
        
        # 强制刷新
        data2 = await strategy_dashboard.load_dashboard(
            sample_strategy_id,
            force_refresh=True,
        )
        
        # 两次加载都应该成功
        assert data1 is not None
        assert data2 is not None


# ============================================================================
# 数据模型序列化测试
# ============================================================================

class TestDataSerialization:
    """测试数据模型序列化"""
    
    def test_dashboard_data_to_dict(self, sample_dashboard_data):
        """测试仪表盘数据转换为字典"""
        data_dict = sample_dashboard_data.to_dict()
        
        assert isinstance(data_dict, dict)
        assert data_dict['strategy_id'] == sample_dashboard_data.strategy_id
        assert data_dict['strategy_name'] == sample_dashboard_data.strategy_name
        assert data_dict['overall_score'] == sample_dashboard_data.overall_score
    
    def test_dashboard_data_from_dict(self, sample_dashboard_data):
        """测试从字典创建仪表盘数据"""
        data_dict = sample_dashboard_data.to_dict()
        restored = StrategyDashboardData.from_dict(data_dict)
        
        assert restored.strategy_id == sample_dashboard_data.strategy_id
        assert restored.strategy_name == sample_dashboard_data.strategy_name
        assert restored.overall_score == sample_dashboard_data.overall_score
    
    def test_dashboard_data_round_trip(self, sample_dashboard_data):
        """测试仪表盘数据序列化往返"""
        data_dict = sample_dashboard_data.to_dict()
        json_str = json.dumps(data_dict)
        restored_dict = json.loads(json_str)
        restored = StrategyDashboardData.from_dict(restored_dict)
        
        assert restored.strategy_id == sample_dashboard_data.strategy_id
        assert restored.overall_score == sample_dashboard_data.overall_score


# ============================================================================
# 运行测试
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
