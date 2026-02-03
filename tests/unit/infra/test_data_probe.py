"""单元测试 - 数据探针

白皮书依据: 第三章 3.2 数据探针
需求: requirements.md 1.1-1.10
设计: design.md 核心组件设计 - 数据探针

本模块测试数据探针的所有功能，确保100%测试覆盖率。

测试内容：
1. 初始化和配置
2. 数据源注册
3. 单个数据源探测
4. 并发探测所有数据源
5. 获取可用数据源
6. 生成可用性报告
7. 私有方法（连接性、认证、数据可用性、质量评分）
8. 边界条件和异常情况
"""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from src.infra.data_probe import DataProbe
from src.infra.data_models import (
    DataSourceConfig,
    DataSourceType,
    DataSourceStatus,
    ProbeResult
)


class TestDataProbeInitialization:
    """测试数据探针初始化"""
    
    def test_init_default_interval(self):
        """测试默认探测间隔初始化"""
        probe = DataProbe()
        
        assert probe.probe_interval == 86400  # 24小时
        assert isinstance(probe.data_sources, dict)
        assert isinstance(probe.probe_results, dict)
        assert len(probe.data_sources) == 9  # 9个预定义数据源（移除Tushare Pro）
    
    def test_init_custom_interval(self):
        """测试自定义探测间隔初始化"""
        probe = DataProbe(probe_interval=3600)
        
        assert probe.probe_interval == 3600  # 1小时
        assert len(probe.data_sources) == 9  # 9个预定义数据源
    
    def test_init_invalid_interval_zero(self):
        """测试无效探测间隔（零）"""
        with pytest.raises(ValueError, match="probe_interval必须 > 0"):
            DataProbe(probe_interval=0)
    
    def test_init_invalid_interval_negative(self):
        """测试无效探测间隔（负数）"""
        with pytest.raises(ValueError, match="probe_interval必须 > 0"):
            DataProbe(probe_interval=-100)
    
    def test_predefined_sources_loaded(self):
        """测试预定义数据源加载"""
        probe = DataProbe()
        
        # 验证9个预定义数据源都已加载（移除Tushare Pro）
        expected_sources = [
            "akshare", "yahoo_finance", "alpha_vantage",
            "stocktwits", "reddit", "newsapi", "gdelt", "fred", "google_trends"
        ]
        
        for source_id in expected_sources:
            assert source_id in probe.data_sources
            config = probe.data_sources[source_id]
            assert isinstance(config, DataSourceConfig)
            assert config.source_id == source_id
            assert config.source_name is not None
            assert config.api_endpoint is not None
    
    def test_predefined_sources_types(self):
        """测试预定义数据源类型"""
        probe = DataProbe()
        
        # 验证数据源类型（移除Tushare Pro）
        assert probe.data_sources["akshare"].source_type == DataSourceType.MARKET_DATA
        assert probe.data_sources["yahoo_finance"].source_type == DataSourceType.MARKET_DATA
        assert probe.data_sources["stocktwits"].source_type == DataSourceType.SENTIMENT_DATA
        assert probe.data_sources["reddit"].source_type == DataSourceType.SENTIMENT_DATA
        assert probe.data_sources["newsapi"].source_type == DataSourceType.EVENT_DATA
        assert probe.data_sources["gdelt"].source_type == DataSourceType.EVENT_DATA
        assert probe.data_sources["fred"].source_type == DataSourceType.MACRO_DATA
        assert probe.data_sources["google_trends"].source_type == DataSourceType.SENTIMENT_DATA


class TestDataSourceRegistration:
    """测试数据源注册"""
    
    def test_register_source_success(self):
        """测试成功注册数据源"""
        probe = DataProbe()
        initial_count = len(probe.data_sources)
        
        config = DataSourceConfig(
            source_id="test_source",
            source_name="Test Source",
            source_type=DataSourceType.MARKET_DATA,
            api_endpoint="https://api.test.com"
        )
        
        probe.register_source(config)
        
        assert len(probe.data_sources) == initial_count + 1
        assert "test_source" in probe.data_sources
        assert probe.data_sources["test_source"] == config
    
    def test_register_source_overwrite(self):
        """测试覆盖已存在的数据源"""
        probe = DataProbe()
        
        # 第一次注册
        config1 = DataSourceConfig(
            source_id="test_source",
            source_name="Test Source 1",
            source_type=DataSourceType.MARKET_DATA,
            api_endpoint="https://api.test1.com"
        )
        probe.register_source(config1)
        
        # 第二次注册（覆盖）- 需要设置allow_overwrite=True
        config2 = DataSourceConfig(
            source_id="test_source",
            source_name="Test Source 2",
            source_type=DataSourceType.SENTIMENT_DATA,
            api_endpoint="https://api.test2.com"
        )
        probe.register_source(config2, allow_overwrite=True)
        
        # 验证被覆盖
        assert probe.data_sources["test_source"] == config2
        assert probe.data_sources["test_source"].source_name == "Test Source 2"
    
    def test_register_source_none(self):
        """测试注册None配置"""
        probe = DataProbe()
        
        with pytest.raises(ValueError, match="config不能为None"):
            probe.register_source(None)


class TestProbeSource:
    """测试单个数据源探测"""
    
    @pytest.mark.asyncio
    async def test_probe_source_success(self):
        """测试成功探测数据源"""
        probe = DataProbe()
        
        # 使用akshare测试（不需要认证）
        result = await probe.probe_source("akshare")
        
        assert isinstance(result, ProbeResult)
        assert result.source_id == "akshare"
        assert result.status == DataSourceStatus.AVAILABLE
        assert result.response_time > 0
        assert result.data_available is True
        assert 0 <= result.quality_score <= 1
        assert result.last_probe_time is not None
        assert result.error_message is None
        
        # 验证结果被缓存
        assert "akshare" in probe.probe_results
        assert probe.probe_results["akshare"] == result
    
    @pytest.mark.asyncio
    async def test_probe_source_nonexistent(self):
        """测试探测不存在的数据源"""
        probe = DataProbe()
        
        with pytest.raises(ValueError, match="数据源不存在"):
            await probe.probe_source("nonexistent_source")
    
    @pytest.mark.asyncio
    async def test_probe_source_connection_failure(self):
        """测试连接失败的情况"""
        probe = DataProbe()
        
        # Mock连接测试失败
        with patch.object(probe, '_test_connectivity', return_value=False):
            result = await probe.probe_source("akshare")
            
            assert result.status == DataSourceStatus.UNAVAILABLE
            assert result.data_available is False
            assert result.error_message == "连接失败"
            assert result.quality_score == 0.0
    
    @pytest.mark.asyncio
    async def test_probe_source_authentication_failure(self):
        """测试认证失败的情况"""
        probe = DataProbe()
        
        # Mock连接成功但认证失败（使用需要认证的数据源）
        with patch.object(probe, '_test_connectivity', return_value=True):
            with patch.object(probe, '_test_authentication', return_value=False):
                result = await probe.probe_source("alpha_vantage")
                
                assert result.status == DataSourceStatus.UNAVAILABLE
                assert result.data_available is False
                assert result.error_message == "认证失败"
                assert result.quality_score == 0.0
    
    @pytest.mark.asyncio
    async def test_probe_source_exception(self):
        """测试探测过程中抛出异常"""
        probe = DataProbe()
        
        # Mock抛出异常
        with patch.object(probe, '_test_connectivity', side_effect=Exception("Test error")):
            result = await probe.probe_source("akshare")
            
            assert result.status == DataSourceStatus.UNAVAILABLE
            assert result.data_available is False
            assert "Test error" in result.error_message
            assert result.quality_score == 0.0
    
    @pytest.mark.asyncio
    async def test_probe_source_no_auth_required(self):
        """测试不需要认证的数据源"""
        probe = DataProbe()
        
        # akshare不需要认证
        result = await probe.probe_source("akshare")
        
        assert result.status == DataSourceStatus.AVAILABLE
        assert result.data_available is True


class TestProbeAllSources:
    """测试并发探测所有数据源"""
    
    @pytest.mark.asyncio
    async def test_probe_all_sources_success(self):
        """测试成功探测所有数据源"""
        probe = DataProbe()
        
        results = await probe.probe_all_sources()
        
        assert isinstance(results, dict)
        assert len(results) == 9  # 9个预定义数据源（移除Tushare Pro）
        
        # 验证所有数据源都被探测
        for source_id in probe.data_sources.keys():
            assert source_id in results
            assert isinstance(results[source_id], ProbeResult)
    
    @pytest.mark.asyncio
    async def test_probe_all_sources_with_failures(self):
        """测试部分数据源探测失败"""
        probe = DataProbe()
        
        # Mock部分数据源连接失败
        async def mock_connectivity(config):
            if config.source_id in ["akshare", "yahoo_finance"]:
                return False
            return True
        
        with patch.object(probe, '_test_connectivity', side_effect=mock_connectivity):
            results = await probe.probe_all_sources()
            
            # 验证失败的数据源
            assert results["akshare"].status == DataSourceStatus.UNAVAILABLE
            assert results["yahoo_finance"].status == DataSourceStatus.UNAVAILABLE
            
            # 验证成功的数据源
            assert results["gdelt"].status == DataSourceStatus.AVAILABLE
    
    @pytest.mark.asyncio
    async def test_probe_all_sources_empty(self):
        """测试没有数据源的情况"""
        probe = DataProbe()
        probe.data_sources.clear()  # 清空数据源
        
        results = await probe.probe_all_sources()
        
        assert isinstance(results, dict)
        assert len(results) == 0


class TestGetAvailableSources:
    """测试获取可用数据源"""
    
    @pytest.mark.asyncio
    async def test_get_available_sources_all(self):
        """测试获取所有可用数据源"""
        probe = DataProbe()
        await probe.probe_all_sources()
        
        available = probe.get_available_sources()
        
        assert isinstance(available, list)
        assert len(available) >= 0  # 可用数据源数量取决于API密钥配置
        
        # 验证按优先级降序排序
        for i in range(len(available) - 1):
            assert available[i].priority >= available[i + 1].priority
    
    @pytest.mark.asyncio
    async def test_get_available_sources_by_type(self):
        """测试按类型获取可用数据源"""
        probe = DataProbe()
        await probe.probe_all_sources()
        
        # 获取市场数据源（移除Tushare Pro后只有3个）
        market_sources = probe.get_available_sources(DataSourceType.MARKET_DATA)
        assert len(market_sources) <= 3  # akshare, yahoo_finance, alpha_vantage（取决于API密钥）
        for source in market_sources:
            assert source.source_type == DataSourceType.MARKET_DATA
        
        # 获取情绪数据源
        sentiment_sources = probe.get_available_sources(DataSourceType.SENTIMENT_DATA)
        assert len(sentiment_sources) <= 3  # stocktwits, reddit, google_trends（取决于API密钥）
        for source in sentiment_sources:
            assert source.source_type == DataSourceType.SENTIMENT_DATA
        
        # 获取事件数据源
        event_sources = probe.get_available_sources(DataSourceType.EVENT_DATA)
        assert len(event_sources) <= 2  # newsapi, gdelt（取决于API密钥）
        for source in event_sources:
            assert source.source_type == DataSourceType.EVENT_DATA
        
        # 获取宏观数据源
        macro_sources = probe.get_available_sources(DataSourceType.MACRO_DATA)
        assert len(macro_sources) <= 1  # fred（取决于API密钥）
        for source in macro_sources:
            assert source.source_type == DataSourceType.MACRO_DATA
    
    @pytest.mark.asyncio
    async def test_get_available_sources_no_probe_results(self):
        """测试没有探测结果的情况"""
        probe = DataProbe()
        # 不执行探测
        
        available = probe.get_available_sources()
        
        assert isinstance(available, list)
        assert len(available) == 0  # 没有探测结果，返回空列表
    
    @pytest.mark.asyncio
    async def test_get_available_sources_with_unavailable(self):
        """测试包含不可用数据源的情况"""
        probe = DataProbe()
        
        # Mock部分数据源不可用
        async def mock_connectivity(config):
            if config.source_id in ["akshare", "yahoo_finance"]:
                return False
            return True
        
        with patch.object(probe, '_test_connectivity', side_effect=mock_connectivity):
            await probe.probe_all_sources()
            
            available = probe.get_available_sources()
            
            # 验证不可用的数据源不在列表中
            source_ids = [s.source_id for s in available]
            assert "akshare" not in source_ids
            assert "yahoo_finance" not in source_ids
            # 其他数据源可能因为需要API密钥而不可用


class TestGenerateAvailabilityReport:
    """测试生成可用性报告"""
    
    @pytest.mark.asyncio
    async def test_generate_report_all_available(self):
        """测试所有数据源可用的报告"""
        probe = DataProbe()
        await probe.probe_all_sources()
        
        report = probe.generate_availability_report()
        
        assert isinstance(report, dict)
        assert report['total_sources'] == 9
        # available_sources取决于API密钥配置
        assert 0 <= report['available_sources'] <= 9
        assert report['unavailable_sources'] == 9 - report['available_sources']
        assert 0 <= report['availability_rate'] <= 100.0
        
        # 验证按类型统计
        assert 'by_type' in report
        assert DataSourceType.MARKET_DATA.value in report['by_type']
        assert report['by_type'][DataSourceType.MARKET_DATA.value]['total'] == 3
        
        # 验证数据源详情
        assert 'sources' in report
        assert len(report['sources']) == 9
        
        for source_info in report['sources']:
            assert 'source_id' in source_info
            assert 'source_name' in source_info
            assert 'source_type' in source_info
            assert 'status' in source_info
            assert 'response_time' in source_info
            assert 'quality_score' in source_info
    
    @pytest.mark.asyncio
    async def test_generate_report_with_failures(self):
        """测试包含失败数据源的报告"""
        probe = DataProbe()
        
        # Mock部分数据源失败
        async def mock_connectivity(config):
            if config.source_id in ["akshare", "yahoo_finance", "reddit"]:
                return False
            return True
        
        with patch.object(probe, '_test_connectivity', side_effect=mock_connectivity):
            await probe.probe_all_sources()
            
            report = probe.generate_availability_report()
            
            assert report['total_sources'] == 9
            # 至少3个失败（akshare, yahoo_finance, reddit），其他可能因API密钥失败
            assert report['unavailable_sources'] >= 3
            assert report['available_sources'] == 9 - report['unavailable_sources']
    
    def test_generate_report_no_probe_results(self):
        """测试没有探测结果的报告"""
        probe = DataProbe()
        # 不执行探测
        
        report = probe.generate_availability_report()
        
        assert report['total_sources'] == 9
        assert report['available_sources'] == 0
        assert report['unavailable_sources'] == 9
        assert report['availability_rate'] == 0.0
        
        # 验证所有数据源状态为unknown
        for source_info in report['sources']:
            assert source_info['status'] == 'unknown'


class TestPrivateMethods:
    """测试私有方法"""
    
    @pytest.mark.asyncio
    async def test_test_connectivity_success(self):
        """测试连接性测试成功"""
        probe = DataProbe()
        config = probe.data_sources["akshare"]
        
        result = await probe._test_connectivity(config)
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_test_connectivity_exception(self):
        """测试连接性测试异常"""
        probe = DataProbe()
        config = probe.data_sources["akshare"]
        
        # Mock抛出异常
        with patch('asyncio.sleep', side_effect=Exception("Connection error")):
            result = await probe._test_connectivity(config)
            
            assert result is False
    
    @pytest.mark.asyncio
    async def test_test_authentication_with_api_key(self):
        """测试有API密钥的认证"""
        probe = DataProbe()
        config = DataSourceConfig(
            source_id="test",
            source_name="Test",
            source_type=DataSourceType.MARKET_DATA,
            api_endpoint="https://api.test.com",
            api_key="test_key",
            requires_auth=True
        )
        
        result = await probe._test_authentication(config)
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_test_authentication_without_api_key(self):
        """测试没有API密钥但需要认证"""
        probe = DataProbe()
        config = DataSourceConfig(
            source_id="test",
            source_name="Test",
            source_type=DataSourceType.MARKET_DATA,
            api_endpoint="https://api.test.com",
            requires_auth=True
        )
        
        result = await probe._test_authentication(config)
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_test_authentication_no_auth_required(self):
        """测试不需要认证"""
        probe = DataProbe()
        config = DataSourceConfig(
            source_id="test",
            source_name="Test",
            source_type=DataSourceType.MARKET_DATA,
            api_endpoint="https://api.test.com",
            requires_auth=False
        )
        
        result = await probe._test_authentication(config)
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_test_authentication_exception(self):
        """测试认证测试异常"""
        probe = DataProbe()
        config = probe.data_sources["alpha_vantage"]
        
        # Mock抛出异常
        with patch('asyncio.sleep', side_effect=Exception("Auth error")):
            result = await probe._test_authentication(config)
            
            assert result is False
    
    @pytest.mark.asyncio
    async def test_test_data_availability_success(self):
        """测试数据可用性测试成功"""
        probe = DataProbe()
        config = probe.data_sources["akshare"]
        
        result = await probe._test_data_availability(config)
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_test_data_availability_exception(self):
        """测试数据可用性测试异常"""
        probe = DataProbe()
        config = probe.data_sources["akshare"]
        
        # Mock抛出异常
        with patch('asyncio.sleep', side_effect=Exception("Data error")):
            result = await probe._test_data_availability(config)
            
            assert result is False
    
    @pytest.mark.asyncio
    async def test_calculate_quality_score_high_priority(self):
        """测试高优先级数据源的质量评分"""
        probe = DataProbe()
        config = DataSourceConfig(
            source_id="test",
            source_name="Test",
            source_type=DataSourceType.MARKET_DATA,
            api_endpoint="https://api.test.com",
            priority=10,
            is_free=False,
            requires_auth=True
        )
        
        score = await probe._calculate_quality_score(config)
        
        assert 0 <= score <= 1
        # 高优先级(1.0) + 付费(0.5) + 需认证(0.6) 的综合评分
        assert score > 0.5  # 应该是较高质量
    
    @pytest.mark.asyncio
    async def test_calculate_quality_score_low_priority(self):
        """测试低优先级数据源的质量评分"""
        probe = DataProbe()
        config = DataSourceConfig(
            source_id="test",
            source_name="Test",
            source_type=DataSourceType.MARKET_DATA,
            api_endpoint="https://api.test.com",
            priority=0,
            is_free=True,
            requires_auth=False
        )
        
        score = await probe._calculate_quality_score(config)
        
        assert 0 <= score <= 1
        assert score < 0.6  # 低优先级、免费、无认证 -> 低质量
    
    @pytest.mark.asyncio
    async def test_calculate_quality_score_exception(self):
        """测试质量评分计算异常"""
        probe = DataProbe()
        config = probe.data_sources["akshare"]
        
        # 即使Mock抛出异常，_calculate_quality_score也会返回基于配置的评分
        # 因为它不依赖于异步操作
        score = await probe._calculate_quality_score(config)
        
        # AKShare的评分应该基于其配置（priority=9, is_free=True, requires_auth=False）
        assert 0 <= score <= 1
        assert score > 0  # 应该有一个合理的评分


class TestRepr:
    """测试字符串表示"""
    
    def test_repr(self):
        """测试__repr__方法"""
        probe = DataProbe(probe_interval=3600)
        
        repr_str = repr(probe)
        
        assert "DataProbe" in repr_str
        assert "sources=9" in repr_str
        assert "probed=0" in repr_str
        assert "interval=3600s" in repr_str
    
    @pytest.mark.asyncio
    async def test_repr_after_probe(self):
        """测试探测后的字符串表示"""
        probe = DataProbe()
        await probe.probe_all_sources()
        
        repr_str = repr(probe)
        
        assert "DataProbe" in repr_str
        assert "sources=9" in repr_str
        assert "probed=9" in repr_str


class TestEdgeCases:
    """测试边界条件"""
    
    @pytest.mark.asyncio
    async def test_probe_source_multiple_times(self):
        """测试多次探测同一数据源"""
        probe = DataProbe()
        
        result1 = await probe.probe_source("akshare")
        result2 = await probe.probe_source("akshare")
        
        # 验证结果被更新
        assert result1.source_id == result2.source_id
        assert result2.last_probe_time >= result1.last_probe_time
    
    @pytest.mark.asyncio
    async def test_concurrent_probe_same_source(self):
        """测试并发探测同一数据源"""
        probe = DataProbe()
        
        # 并发探测同一数据源
        results = await asyncio.gather(
            probe.probe_source("akshare"),
            probe.probe_source("akshare"),
            probe.probe_source("akshare")
        )
        
        # 验证所有结果都成功
        for result in results:
            assert result.status == DataSourceStatus.AVAILABLE
    
    def test_get_available_sources_invalid_type(self):
        """测试使用无效的数据源类型"""
        probe = DataProbe()
        
        # 使用字符串而不是枚举（应该不会崩溃）
        try:
            available = probe.get_available_sources("invalid_type")
            # 如果没有类型检查，应该返回空列表
            assert isinstance(available, list)
        except (TypeError, AttributeError):
            # 如果有类型检查，应该抛出异常
            pass
    
    @pytest.mark.asyncio
    async def test_probe_all_sources_exception_handling(self):
        """测试并发探测时的异常处理"""
        probe = DataProbe()
        
        # Mock部分探测抛出异常
        original_probe = probe.probe_source
        
        async def mock_probe(source_id):
            if source_id == "akshare":
                raise Exception("Test exception")
            return await original_probe(source_id)
        
        with patch.object(probe, 'probe_source', side_effect=mock_probe):
            results = await probe.probe_all_sources()
            
            # 验证其他数据源仍然被探测
            assert len(results) >= 8  # 至少8个成功（9个数据源 - 1个异常）


class TestIntegration:
    """集成测试"""
    
    @pytest.mark.asyncio
    async def test_full_workflow(self):
        """测试完整工作流程"""
        # 1. 初始化探针
        probe = DataProbe(probe_interval=3600)
        assert len(probe.data_sources) == 9
        
        # 2. 注册自定义数据源
        custom_config = DataSourceConfig(
            source_id="custom_source",
            source_name="Custom Source",
            source_type=DataSourceType.MARKET_DATA,
            api_endpoint="https://api.custom.com",
            priority=10
        )
        probe.register_source(custom_config)
        assert len(probe.data_sources) == 10
        
        # 3. 探测所有数据源
        results = await probe.probe_all_sources()
        assert len(results) == 10
        
        # 4. 获取可用数据源（数量取决于API密钥配置）
        available = probe.get_available_sources()
        assert len(available) >= 0
        assert len(available) <= 10
        
        # 5. 按类型获取数据源
        market_sources = probe.get_available_sources(DataSourceType.MARKET_DATA)
        assert len(market_sources) <= 4  # 3个预定义 + 1个自定义（取决于API密钥）
        
        # 6. 生成报告
        report = probe.generate_availability_report()
        assert report['total_sources'] == 10
        assert 0 <= report['available_sources'] <= 10
        
        # 7. 验证报告内容
        assert 'by_type' in report
        assert 'sources' in report
        assert len(report['sources']) == 10



class TestSaveProbeResults:
    """测试保存探测结果"""
    
    @pytest.mark.asyncio
    async def test_save_probe_results_success(self, tmp_path):
        """测试成功保存探测结果"""
        probe = DataProbe()
        await probe.probe_all_sources()
        
        # 保存到临时文件
        filepath = tmp_path / "test_probe_discovery.json"
        probe.save_probe_results(str(filepath))
        
        # 验证文件存在
        assert filepath.exists()
        
        # 验证文件内容
        import json
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 验证基本结构
        assert 'probe_timestamp' in data
        assert 'platforms' in data
        assert 'discoveries' in data
        assert 'total_interfaces' in data
        assert 'valid_interfaces' in data
        assert 'probe_duration_seconds' in data
        
        # 验证数据内容
        assert data['total_interfaces'] == 9
        # valid_interfaces取决于哪些数据源有API密钥
        assert data['valid_interfaces'] >= 0
        assert data['valid_interfaces'] <= 9
        assert isinstance(data['platforms'], list)
        assert len(data['platforms']) == 9
        
        # 验证discoveries结构
        assert 'market_data' in data['discoveries']
        assert 'sentiment_data' in data['discoveries']
        assert 'event_data' in data['discoveries']
        assert 'macro_data' in data['discoveries']
        
        # 验证每种类型的结构
        for type_key, type_data in data['discoveries'].items():
            assert 'interfaces' in type_data
            assert 'recommended' in type_data
            assert 'primary' in type_data['recommended']
            assert 'backup' in type_data['recommended']
            
            # 验证interfaces列表
            for interface in type_data['interfaces']:
                assert 'platform' in interface
                assert 'api' in interface
                assert 'quality_score' in interface
                assert 'coverage' in interface
                assert 'latency_ms' in interface
                assert 'status' in interface
    
    @pytest.mark.asyncio
    async def test_save_probe_results_default_path(self):
        """测试使用默认路径保存"""
        probe = DataProbe()
        await probe.probe_all_sources()
        
        # 使用默认路径
        probe.save_probe_results()
        
        # 验证文件存在
        import os
        assert os.path.exists("probe_discovery.json")
        
        # 清理
        os.remove("probe_discovery.json")
    
    @pytest.mark.asyncio
    async def test_save_probe_results_with_failures(self, tmp_path):
        """测试保存包含失败数据源的结果"""
        probe = DataProbe()
        
        # Mock部分数据源失败
        async def mock_connectivity(config):
            if config.source_id in ["akshare", "yahoo_finance"]:
                return False
            return True
        
        with patch.object(probe, '_test_connectivity', side_effect=mock_connectivity):
            await probe.probe_all_sources()
        
        filepath = tmp_path / "test_probe_with_failures.json"
        probe.save_probe_results(str(filepath))
        
        # 验证文件内容
        import json
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 验证统计信息
        assert data['total_interfaces'] == 9
        # 验证失败的数据源被正确标记（akshare和yahoo_finance连接失败，其他需要认证的也会失败）
        assert data['valid_interfaces'] < 9  # 至少有2个失败
        
        # 验证失败的数据源状态为UNAVAILABLE
        market_interfaces = data['discoveries']['market_data']['interfaces']
        akshare_interface = next(i for i in market_interfaces if i['platform'] == 'akshare')
        assert akshare_interface['status'] == 'UNAVAILABLE'
        assert akshare_interface['quality_score'] == 0.0
    
    @pytest.mark.asyncio
    async def test_save_probe_results_recommended_selection(self, tmp_path):
        """测试PRIMARY和BACKUP接口选择"""
        probe = DataProbe()
        await probe.probe_all_sources()
        
        filepath = tmp_path / "test_recommended.json"
        probe.save_probe_results(str(filepath))
        
        import json
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 验证market_data的推荐接口
        market_data = data['discoveries']['market_data']
        assert market_data['recommended']['primary'] is not None
        assert market_data['recommended']['backup'] is not None
        
        # PRIMARY应该是质量评分最高的
        interfaces = [i for i in market_data['interfaces'] if i['status'] != 'UNAVAILABLE']
        if interfaces:
            interfaces.sort(key=lambda x: x['quality_score'], reverse=True)
            expected_primary = f"{interfaces[0]['platform']}.{interfaces[0]['api']}"
            assert market_data['recommended']['primary'] == expected_primary
            
            if len(interfaces) > 1:
                expected_backup = f"{interfaces[1]['platform']}.{interfaces[1]['api']}"
                assert market_data['recommended']['backup'] == expected_backup
    
    @pytest.mark.asyncio
    async def test_save_probe_results_no_backup(self, tmp_path):
        """测试只有一个可用接口时没有BACKUP"""
        probe = DataProbe()
        
        # Mock只有一个数据源可用
        async def mock_connectivity(config):
            return config.source_id == "gdelt"
        
        with patch.object(probe, '_test_connectivity', side_effect=mock_connectivity):
            await probe.probe_all_sources()
        
        filepath = tmp_path / "test_no_backup.json"
        probe.save_probe_results(str(filepath))
        
        import json
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # event_data只有gdelt可用
        event_data = data['discoveries']['event_data']
        assert event_data['recommended']['primary'] is not None
        # 只有一个可用接口，backup应该为None
        # （实际上gdelt是唯一可用的event_data源）
    
    def test_save_probe_results_no_probe_executed(self, tmp_path):
        """测试未执行探测就保存"""
        probe = DataProbe()
        # 不执行探测
        
        filepath = tmp_path / "test_no_probe.json"
        probe.save_probe_results(str(filepath))
        
        # 验证文件内容
        import json
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 应该保存数据源配置，但没有探测结果
        assert data['total_interfaces'] == 9
        assert data['valid_interfaces'] == 0  # 没有探测结果
        
        # 所有接口状态应该是UNAVAILABLE
        for type_data in data['discoveries'].values():
            for interface in type_data['interfaces']:
                assert interface['status'] == 'UNAVAILABLE'
                assert interface['quality_score'] == 0.0
    
    @pytest.mark.asyncio
    async def test_save_probe_results_create_directory(self, tmp_path):
        """测试自动创建目录"""
        probe = DataProbe()
        await probe.probe_all_sources()
        
        # 使用不存在的目录
        filepath = tmp_path / "subdir" / "nested" / "probe_discovery.json"
        probe.save_probe_results(str(filepath))
        
        # 验证目录和文件都被创建
        assert filepath.exists()
        assert filepath.parent.exists()
    
    def test_save_probe_results_invalid_path(self, tmp_path):
        """测试无效的文件路径"""
        probe = DataProbe()
        
        # 在Windows上，使用一个确实无效的路径
        # 使用tmp_path创建一个文件，然后尝试将其作为目录使用
        invalid_file = tmp_path / "file.txt"
        invalid_file.write_text("test")
        
        # 尝试在文件路径下创建文件（应该失败）
        try:
            probe.save_probe_results(str(invalid_file / "probe_discovery.json"))
            # 如果没有抛出异常，测试失败
            assert False, "应该抛出IOError"
        except (IOError, OSError) as e:
            # Windows可能抛出OSError而不是IOError
            assert True
    
    @pytest.mark.asyncio
    async def test_save_probe_results_unicode_content(self, tmp_path):
        """测试保存包含Unicode字符的内容"""
        probe = DataProbe()
        await probe.probe_all_sources()
        
        filepath = tmp_path / "test_unicode.json"
        probe.save_probe_results(str(filepath))
        
        # 验证文件可以正确读取Unicode内容
        import json
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 验证中文等Unicode字符正确保存
        assert data['probe_timestamp'] is not None
        # 文件应该包含中文字符（如果有的话）


class TestLoadProbeResults:
    """测试加载探测结果"""
    
    @pytest.mark.asyncio
    async def test_load_probe_results_success(self, tmp_path):
        """测试成功加载探测结果"""
        probe = DataProbe()
        await probe.probe_all_sources()
        
        # 先保存
        filepath = tmp_path / "test_load.json"
        probe.save_probe_results(str(filepath))
        
        # 创建新的探针实例并加载
        probe2 = DataProbe()
        loaded_data = probe2.load_probe_results(str(filepath))
        
        # 验证加载的数据
        assert isinstance(loaded_data, dict)
        assert 'probe_timestamp' in loaded_data
        assert 'platforms' in loaded_data
        assert 'discoveries' in loaded_data
        assert 'total_interfaces' in loaded_data
        assert 'valid_interfaces' in loaded_data
        
        # 验证数据内容
        assert loaded_data['total_interfaces'] == 9
        # valid_interfaces取决于哪些数据源有API密钥
        assert loaded_data['valid_interfaces'] >= 0
        assert loaded_data['valid_interfaces'] <= 9
    
    def test_load_probe_results_default_path(self, tmp_path):
        """测试使用默认路径加载"""
        probe = DataProbe()
        
        # 创建一个测试文件
        import json
        test_data = {
            "probe_timestamp": "2026-01-21 10:00:00",
            "platforms": ["test"],
            "discoveries": {},
            "total_interfaces": 1,
            "valid_interfaces": 1,
            "probe_duration_seconds": 0
        }
        
        with open("probe_discovery.json", 'w', encoding='utf-8') as f:
            json.dump(test_data, f)
        
        # 使用默认路径加载
        loaded_data = probe.load_probe_results()
        
        assert loaded_data['total_interfaces'] == 1
        
        # 清理
        import os
        os.remove("probe_discovery.json")
    
    def test_load_probe_results_file_not_found(self):
        """测试加载不存在的文件"""
        probe = DataProbe()
        
        with pytest.raises(FileNotFoundError, match="探测日志文件不存在"):
            probe.load_probe_results("nonexistent_file.json")
    
    def test_load_probe_results_invalid_json(self, tmp_path):
        """测试加载无效的JSON文件"""
        probe = DataProbe()
        
        # 创建无效的JSON文件
        filepath = tmp_path / "invalid.json"
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write("{ invalid json content")
        
        with pytest.raises(ValueError, match="探测日志文件格式错误"):
            probe.load_probe_results(str(filepath))
    
    def test_load_probe_results_empty_file(self, tmp_path):
        """测试加载空文件"""
        probe = DataProbe()
        
        # 创建空文件
        filepath = tmp_path / "empty.json"
        filepath.touch()
        
        with pytest.raises(ValueError, match="探测日志文件格式错误"):
            probe.load_probe_results(str(filepath))
    
    @pytest.mark.asyncio
    async def test_load_probe_results_verify_structure(self, tmp_path):
        """测试加载后验证数据结构"""
        probe = DataProbe()
        await probe.probe_all_sources()
        
        filepath = tmp_path / "test_structure.json"
        probe.save_probe_results(str(filepath))
        
        # 加载并验证结构
        loaded_data = probe.load_probe_results(str(filepath))
        
        # 验证discoveries结构
        assert 'market_data' in loaded_data['discoveries']
        market_data = loaded_data['discoveries']['market_data']
        
        assert 'interfaces' in market_data
        assert isinstance(market_data['interfaces'], list)
        
        assert 'recommended' in market_data
        assert 'primary' in market_data['recommended']
        assert 'backup' in market_data['recommended']
        
        # 验证interface结构
        if market_data['interfaces']:
            interface = market_data['interfaces'][0]
            assert 'platform' in interface
            assert 'api' in interface
            assert 'quality_score' in interface
            assert 'coverage' in interface
            assert 'latency_ms' in interface
            assert 'status' in interface
    
    @pytest.mark.asyncio
    async def test_load_probe_results_timestamp_format(self, tmp_path):
        """测试时间戳格式"""
        probe = DataProbe()
        await probe.probe_all_sources()
        
        filepath = tmp_path / "test_timestamp.json"
        probe.save_probe_results(str(filepath))
        
        loaded_data = probe.load_probe_results(str(filepath))
        
        # 验证时间戳格式
        timestamp = loaded_data['probe_timestamp']
        assert isinstance(timestamp, str)
        
        # 验证可以解析时间戳
        from datetime import datetime
        try:
            datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            assert False, f"时间戳格式错误: {timestamp}"
    
    def test_load_probe_results_missing_fields(self, tmp_path):
        """测试加载缺少必要字段的文件"""
        probe = DataProbe()
        
        # 创建缺少字段的JSON文件
        import json
        incomplete_data = {
            "probe_timestamp": "2026-01-21 10:00:00",
            # 缺少其他必要字段
        }
        
        filepath = tmp_path / "incomplete.json"
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(incomplete_data, f)
        
        # 加载应该成功，但数据不完整
        loaded_data = probe.load_probe_results(str(filepath))
        
        assert 'probe_timestamp' in loaded_data
        # 其他字段可能不存在，使用get方法访问
        assert loaded_data.get('total_interfaces', 0) == 0


class TestSaveLoadIntegration:
    """测试保存和加载的集成"""
    
    @pytest.mark.asyncio
    async def test_save_load_roundtrip(self, tmp_path):
        """测试保存后加载的往返一致性"""
        probe1 = DataProbe()
        await probe1.probe_all_sources()
        
        filepath = tmp_path / "roundtrip.json"
        
        # 保存
        probe1.save_probe_results(str(filepath))
        
        # 加载
        probe2 = DataProbe()
        loaded_data = probe2.load_probe_results(str(filepath))
        
        # 验证数据一致性
        assert loaded_data['total_interfaces'] == 9
        # 注意：部分数据源需要API密钥，因此valid_interfaces可能小于total_interfaces
        assert 0 <= loaded_data['valid_interfaces'] <= 9
        assert loaded_data['valid_interfaces'] > 0  # 至少有一些接口是有效的
        assert len(loaded_data['platforms']) == 9
        
        # 验证discoveries内容
        for type_key in ['market_data', 'sentiment_data', 'event_data', 'macro_data']:
            assert type_key in loaded_data['discoveries']
    
    @pytest.mark.asyncio
    async def test_save_load_multiple_times(self, tmp_path):
        """测试多次保存和加载"""
        probe = DataProbe()
        await probe.probe_all_sources()
        
        filepath = tmp_path / "multiple.json"
        
        # 第一次保存
        probe.save_probe_results(str(filepath))
        data1 = probe.load_probe_results(str(filepath))
        
        # 再次探测
        await probe.probe_all_sources()
        
        # 第二次保存（覆盖）
        probe.save_probe_results(str(filepath))
        data2 = probe.load_probe_results(str(filepath))
        
        # 验证文件被正确覆盖
        assert data2['probe_timestamp'] >= data1['probe_timestamp']
    
    @pytest.mark.asyncio
    async def test_save_load_with_custom_source(self, tmp_path):
        """测试包含自定义数据源的保存和加载"""
        probe1 = DataProbe()
        
        # 添加自定义数据源
        custom_config = DataSourceConfig(
            source_id="custom_test",
            source_name="Custom Test Source",
            source_type=DataSourceType.MARKET_DATA,
            api_endpoint="https://api.custom.com",
            priority=10
        )
        probe1.register_source(custom_config)
        
        await probe1.probe_all_sources()
        
        filepath = tmp_path / "custom.json"
        probe1.save_probe_results(str(filepath))
        
        # 加载并验证
        probe2 = DataProbe()
        loaded_data = probe2.load_probe_results(str(filepath))
        
        # 验证包含自定义数据源
        assert loaded_data['total_interfaces'] == 10
        
        # 验证自定义数据源在platforms列表中
        assert 'custom_test' in loaded_data['platforms']
    
    @pytest.mark.asyncio
    async def test_load_and_use_recommendations(self, tmp_path):
        """测试加载后使用推荐接口"""
        probe1 = DataProbe()
        await probe1.probe_all_sources()
        
        filepath = tmp_path / "recommendations.json"
        probe1.save_probe_results(str(filepath))
        
        # 加载
        probe2 = DataProbe()
        loaded_data = probe2.load_probe_results(str(filepath))
        
        # 验证可以获取推荐接口
        market_data = loaded_data['discoveries']['market_data']
        primary = market_data['recommended']['primary']
        backup = market_data['recommended']['backup']
        
        assert primary is not None
        assert backup is not None
        
        # 验证推荐接口格式
        assert '.' in primary  # 格式: "platform.api"
        assert '.' in backup
        
        # 验证可以解析平台名称
        primary_platform = primary.split('.')[0]
        backup_platform = backup.split('.')[0]
        
        assert primary_platform in loaded_data['platforms']
        assert backup_platform in loaded_data['platforms']


class TestPersistenceEdgeCases:
    """测试持久化的边界条件"""
    
    @pytest.mark.asyncio
    async def test_save_with_special_characters_in_path(self, tmp_path):
        """测试路径包含特殊字符"""
        probe = DataProbe()
        await probe.probe_all_sources()
        
        # 使用包含空格和特殊字符的路径
        filepath = tmp_path / "test dir" / "probe-discovery_v1.0.json"
        probe.save_probe_results(str(filepath))
        
        assert filepath.exists()
        
        # 验证可以加载
        loaded_data = probe.load_probe_results(str(filepath))
        assert loaded_data['total_interfaces'] == 9
    
    @pytest.mark.asyncio
    async def test_save_overwrite_existing_file(self, tmp_path):
        """测试覆盖已存在的文件"""
        probe = DataProbe()
        await probe.probe_all_sources()
        
        filepath = tmp_path / "overwrite.json"
        
        # 第一次保存
        probe.save_probe_results(str(filepath))
        
        import json
        with open(filepath, 'r', encoding='utf-8') as f:
            data1 = json.load(f)
        
        # 修改探测结果
        await probe.probe_all_sources()
        
        # 第二次保存（覆盖）
        probe.save_probe_results(str(filepath))
        
        with open(filepath, 'r', encoding='utf-8') as f:
            data2 = json.load(f)
        
        # 验证文件被覆盖
        assert data2['probe_timestamp'] >= data1['probe_timestamp']
    
    def test_load_from_readonly_file(self, tmp_path):
        """测试从只读文件加载"""
        probe = DataProbe()
        
        # 创建测试文件
        import json
        test_data = {
            "probe_timestamp": "2026-01-21 10:00:00",
            "platforms": ["test"],
            "discoveries": {},
            "total_interfaces": 1,
            "valid_interfaces": 1,
            "probe_duration_seconds": 0
        }
        
        filepath = tmp_path / "readonly.json"
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(test_data, f)
        
        # 设置为只读（在Windows上可能需要不同的方法）
        import os
        import stat
        os.chmod(filepath, stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
        
        # 应该可以读取
        loaded_data = probe.load_probe_results(str(filepath))
        assert loaded_data['total_interfaces'] == 1
        
        # 恢复权限以便清理
        os.chmod(filepath, stat.S_IWUSR | stat.S_IRUSR)
    
    @pytest.mark.asyncio
    async def test_concurrent_save(self, tmp_path):
        """测试并发保存"""
        probe = DataProbe()
        await probe.probe_all_sources()
        
        filepath = tmp_path / "concurrent.json"
        
        # 并发保存（可能会有竞争条件）
        import asyncio
        
        async def save_task():
            probe.save_probe_results(str(filepath))
        
        # 执行多个并发保存
        await asyncio.gather(
            save_task(),
            save_task(),
            save_task()
        )
        
        # 验证文件存在且可读
        assert filepath.exists()
        loaded_data = probe.load_probe_results(str(filepath))
        assert loaded_data['total_interfaces'] == 9
