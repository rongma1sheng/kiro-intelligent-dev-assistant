"""单元测试 - 数据模型

白皮书依据: 第三章 3.2 基础设施与数据治理
需求: 1.1-1.10, 2.1-2.10
测试覆盖: data_models.py

测试内容:
- 数据源类型和状态枚举
- 数据源配置验证
- 探测结果验证
- 降级链配置验证
- 质量指标验证
- 路由策略枚举
"""

import pytest
from datetime import datetime
from src.infra.data_models import (
    DataSourceType,
    DataSourceStatus,
    DataSourceConfig,
    ProbeResult,
    FallbackChain,
    QualityMetrics,
    RoutingStrategy
)


class TestDataSourceType:
    """测试数据源类型枚举"""
    
    def test_all_types_defined(self):
        """测试所有数据源类型都已定义"""
        expected_types = {
            "market_data",
            "financial_data",
            "alternative_data",
            "sentiment_data",
            "event_data",
            "macro_data"
        }
        actual_types = {t.value for t in DataSourceType}
        assert actual_types == expected_types
    
    def test_type_values(self):
        """测试数据源类型的值"""
        assert DataSourceType.MARKET_DATA.value == "market_data"
        assert DataSourceType.FINANCIAL_DATA.value == "financial_data"
        assert DataSourceType.SENTIMENT_DATA.value == "sentiment_data"


class TestDataSourceStatus:
    """测试数据源状态枚举"""
    
    def test_all_statuses_defined(self):
        """测试所有状态都已定义"""
        expected_statuses = {
            "available",
            "unavailable",
            "degraded",
            "testing"
        }
        actual_statuses = {s.value for s in DataSourceStatus}
        assert actual_statuses == expected_statuses
    
    def test_status_values(self):
        """测试状态的值"""
        assert DataSourceStatus.AVAILABLE.value == "available"
        assert DataSourceStatus.UNAVAILABLE.value == "unavailable"


class TestDataSourceConfig:
    """测试数据源配置"""
    
    def test_valid_config(self):
        """测试有效的配置"""
        config = DataSourceConfig(
            source_id="test_source",
            source_name="Test Source",
            source_type=DataSourceType.MARKET_DATA,
            api_endpoint="https://api.test.com"
        )
        
        assert config.source_id == "test_source"
        assert config.source_name == "Test Source"
        assert config.source_type == DataSourceType.MARKET_DATA
        assert config.api_endpoint == "https://api.test.com"
        assert config.rate_limit == 100  # 默认值
        assert config.cost_per_request == 0.0  # 默认值
        assert config.priority == 5  # 默认值
        assert config.is_free is True  # 默认值
        assert config.requires_auth is False  # 默认值
    
    def test_custom_config(self):
        """测试自定义配置"""
        config = DataSourceConfig(
            source_id="akshare",
            source_name="AKShare",
            source_type=DataSourceType.MARKET_DATA,
            api_endpoint="https://akshare.akfamily.xyz",
            api_key="test_key_123",
            rate_limit=100,
            cost_per_request=0.01,
            priority=8,
            is_free=False,
            requires_auth=True
        )
        
        assert config.api_key == "test_key_123"
        assert config.rate_limit == 100
        assert config.cost_per_request == 0.01
        assert config.priority == 8
        assert config.is_free is False
        assert config.requires_auth is True
    
    def test_empty_source_id(self):
        """测试空的source_id"""
        with pytest.raises(ValueError, match="source_id不能为空"):
            DataSourceConfig(
                source_id="",
                source_name="Test",
                source_type=DataSourceType.MARKET_DATA,
                api_endpoint="https://api.test.com"
            )
    
    def test_empty_source_name(self):
        """测试空的source_name"""
        with pytest.raises(ValueError, match="source_name不能为空"):
            DataSourceConfig(
                source_id="test",
                source_name="",
                source_type=DataSourceType.MARKET_DATA,
                api_endpoint="https://api.test.com"
            )
    
    def test_empty_api_endpoint(self):
        """测试空的api_endpoint"""
        with pytest.raises(ValueError, match="api_endpoint不能为空"):
            DataSourceConfig(
                source_id="test",
                source_name="Test",
                source_type=DataSourceType.MARKET_DATA,
                api_endpoint=""
            )
    
    def test_invalid_rate_limit(self):
        """测试无效的rate_limit"""
        with pytest.raises(ValueError, match="rate_limit必须 > 0"):
            DataSourceConfig(
                source_id="test",
                source_name="Test",
                source_type=DataSourceType.MARKET_DATA,
                api_endpoint="https://api.test.com",
                rate_limit=0
            )
    
    def test_negative_cost(self):
        """测试负数成本"""
        with pytest.raises(ValueError, match="cost_per_request必须 >= 0"):
            DataSourceConfig(
                source_id="test",
                source_name="Test",
                source_type=DataSourceType.MARKET_DATA,
                api_endpoint="https://api.test.com",
                cost_per_request=-0.01
            )
    
    def test_invalid_priority(self):
        """测试无效的优先级"""
        with pytest.raises(ValueError, match="priority必须在 \\[0, 10\\]"):
            DataSourceConfig(
                source_id="test",
                source_name="Test",
                source_type=DataSourceType.MARKET_DATA,
                api_endpoint="https://api.test.com",
                priority=11
            )


class TestProbeResult:
    """测试探测结果"""
    
    def test_valid_result(self):
        """测试有效的探测结果"""
        now = datetime.now()
        result = ProbeResult(
            source_id="test_source",
            status=DataSourceStatus.AVAILABLE,
            response_time=150.5,
            data_available=True,
            quality_score=0.95,
            last_probe_time=now
        )
        
        assert result.source_id == "test_source"
        assert result.status == DataSourceStatus.AVAILABLE
        assert result.response_time == 150.5
        assert result.data_available is True
        assert result.quality_score == 0.95
        assert result.last_probe_time == now
        assert result.error_message is None
    
    def test_failed_result(self):
        """测试失败的探测结果"""
        result = ProbeResult(
            source_id="test_source",
            status=DataSourceStatus.UNAVAILABLE,
            response_time=5000.0,
            data_available=False,
            error_message="连接超时",
            quality_score=0.0
        )
        
        assert result.status == DataSourceStatus.UNAVAILABLE
        assert result.data_available is False
        assert result.error_message == "连接超时"
        assert result.quality_score == 0.0
    
    def test_auto_timestamp(self):
        """测试自动生成时间戳"""
        result = ProbeResult(
            source_id="test",
            status=DataSourceStatus.AVAILABLE,
            response_time=100.0,
            data_available=True
        )
        
        assert result.last_probe_time is not None
        assert isinstance(result.last_probe_time, datetime)
    
    def test_empty_source_id(self):
        """测试空的source_id"""
        with pytest.raises(ValueError, match="source_id不能为空"):
            ProbeResult(
                source_id="",
                status=DataSourceStatus.AVAILABLE,
                response_time=100.0,
                data_available=True
            )
    
    def test_negative_response_time(self):
        """测试负数响应时间"""
        with pytest.raises(ValueError, match="response_time必须 >= 0"):
            ProbeResult(
                source_id="test",
                status=DataSourceStatus.AVAILABLE,
                response_time=-100.0,
                data_available=True
            )
    
    def test_invalid_quality_score(self):
        """测试无效的质量评分"""
        with pytest.raises(ValueError, match="quality_score必须在 \\[0, 1\\]"):
            ProbeResult(
                source_id="test",
                status=DataSourceStatus.AVAILABLE,
                response_time=100.0,
                data_available=True,
                quality_score=1.5
            )


class TestFallbackChain:
    """测试降级链配置"""
    
    def test_valid_chain(self):
        """测试有效的降级链"""
        chain = FallbackChain(
            data_type=DataSourceType.MARKET_DATA,
            primary_source="akshare",
            fallback_sources=["yahoo_finance", "alpha_vantage"]
        )
        
        assert chain.data_type == DataSourceType.MARKET_DATA
        assert chain.primary_source == "akshare"
        assert chain.fallback_sources == ["yahoo_finance", "alpha_vantage"]
    
    def test_get_all_sources(self):
        """测试获取所有数据源"""
        chain = FallbackChain(
            data_type=DataSourceType.MARKET_DATA,
            primary_source="akshare",
            fallback_sources=["yahoo_finance", "alpha_vantage"]
        )
        
        all_sources = chain.get_all_sources()
        assert all_sources == ["akshare", "yahoo_finance", "alpha_vantage"]
    
    def test_empty_primary_source(self):
        """测试空的主数据源"""
        with pytest.raises(ValueError, match="primary_source不能为空"):
            FallbackChain(
                data_type=DataSourceType.MARKET_DATA,
                primary_source="",
                fallback_sources=["akshare"]
            )
    
    def test_empty_fallback_sources(self):
        """测试空的降级源列表"""
        with pytest.raises(ValueError, match="fallback_sources不能为空"):
            FallbackChain(
                data_type=DataSourceType.MARKET_DATA,
                primary_source="akshare",
                fallback_sources=[]
            )
    
    def test_primary_in_fallback(self):
        """测试主源出现在降级源中"""
        with pytest.raises(ValueError, match="primary_source不能出现在fallback_sources中"):
            FallbackChain(
                data_type=DataSourceType.MARKET_DATA,
                primary_source="akshare",
                fallback_sources=["akshare", "yahoo_finance"]
            )


class TestQualityMetrics:
    """测试质量指标"""
    
    def test_valid_metrics(self):
        """测试有效的质量指标"""
        metrics = QualityMetrics(
            completeness=0.98,
            timeliness=0.95,
            accuracy=0.92,
            consistency=0.99,
            overall_score=0.96
        )
        
        assert metrics.completeness == 0.98
        assert metrics.timeliness == 0.95
        assert metrics.accuracy == 0.92
        assert metrics.consistency == 0.99
        assert metrics.overall_score == 0.96
    
    def test_is_acceptable_above_threshold(self):
        """测试质量可接受（高于阈值）"""
        metrics = QualityMetrics(
            completeness=0.9,
            timeliness=0.9,
            accuracy=0.9,
            consistency=0.9,
            overall_score=0.9
        )
        
        assert metrics.is_acceptable(threshold=0.5) is True
        assert metrics.is_acceptable(threshold=0.8) is True
    
    def test_is_acceptable_below_threshold(self):
        """测试质量不可接受（低于阈值）"""
        metrics = QualityMetrics(
            completeness=0.4,
            timeliness=0.4,
            accuracy=0.4,
            consistency=0.4,
            overall_score=0.4
        )
        
        assert metrics.is_acceptable(threshold=0.5) is False
        assert metrics.is_acceptable(threshold=0.3) is True
    
    def test_invalid_completeness(self):
        """测试无效的完整性"""
        with pytest.raises(ValueError, match="completeness必须在 \\[0, 1\\]"):
            QualityMetrics(
                completeness=1.5,
                timeliness=0.9,
                accuracy=0.9,
                consistency=0.9,
                overall_score=0.9
            )
    
    def test_invalid_overall_score(self):
        """测试无效的综合评分"""
        with pytest.raises(ValueError, match="overall_score必须在 \\[0, 1\\]"):
            QualityMetrics(
                completeness=0.9,
                timeliness=0.9,
                accuracy=0.9,
                consistency=0.9,
                overall_score=-0.1
            )


class TestRoutingStrategy:
    """测试路由策略枚举"""
    
    def test_all_strategies_defined(self):
        """测试所有路由策略都已定义"""
        expected_strategies = {
            "quality_first",
            "cost_first",
            "latency_first",
            "region_aware"
        }
        actual_strategies = {s.value for s in RoutingStrategy}
        assert actual_strategies == expected_strategies
    
    def test_strategy_values(self):
        """测试路由策略的值"""
        assert RoutingStrategy.QUALITY_FIRST.value == "quality_first"
        assert RoutingStrategy.COST_FIRST.value == "cost_first"
        assert RoutingStrategy.LATENCY_FIRST.value == "latency_first"
        assert RoutingStrategy.REGION_AWARE.value == "region_aware"
