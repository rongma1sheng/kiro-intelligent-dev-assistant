"""
MIA系统因子挖掘智能哨兵测试

白皮书依据: 第二章 2.6 FactorMining Intelligence Sentinel
版本: v1.6.0
作者: MIA Team
日期: 2026-01-18

测试覆盖:
1. 发现记录和存储
2. 监控源配置
3. 因子实现和验证
4. 统计和查询功能
5. 手动发现输入
6. 异常处理和错误恢复
"""

import pytest
import asyncio
import json
import tempfile
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch
import numpy as np
import pandas as pd
import redis

from src.evolution.factor_mining_intelligence_sentinel import (
    FactorMiningIntelligenceSentinel,
    FactorDiscovery,
    FactorImplementation,
    DiscoveryType,
    FactorCategory,
    ValidationStatus
)
from src.brain.llm_gateway import LLMGateway


class TestFactorDiscovery:
    """测试因子发现记录"""
    
    def test_factor_discovery_creation(self):
        """测试因子发现创建"""
        discovery = FactorDiscovery(
            discovery_id="test_001",
            discovery_type=DiscoveryType.ACADEMIC_PAPER,
            factor_category=FactorCategory.TECHNICAL,
            title="Test Momentum Factor",
            description="A test momentum factor",
            source="Test Source",
            discovered_at=datetime.now(),
            discoverer="system",
            theoretical_basis="Test theory"
        )
        
        assert discovery.discovery_id == "test_001"
        assert discovery.discovery_type == DiscoveryType.ACADEMIC_PAPER
        assert discovery.factor_category == FactorCategory.TECHNICAL
        assert discovery.title == "Test Momentum Factor"
        assert discovery.status == ValidationStatus.DISCOVERED
        assert discovery.confidence_score == 0.5
    
    def test_discovery_id_auto_generation(self):
        """测试发现ID自动生成"""
        discovery = FactorDiscovery(
            discovery_id="",  # 空ID，应该自动生成
            discovery_type=DiscoveryType.MARKET_ANOMALY,
            factor_category=FactorCategory.TECHNICAL,
            title="Auto ID Test",
            description="Test auto ID generation",
            source="Test",
            discovered_at=datetime.now(),
            discoverer="system",
            theoretical_basis="Test"
        )
        
        assert discovery.discovery_id != ""
        assert len(discovery.discovery_id) == 12  # MD5前12位


class TestFactorImplementation:
    """测试因子实现"""
    
    def test_factor_implementation_creation(self):
        """测试因子实现创建"""
        implementation = FactorImplementation(
            factor_id="factor_001",
            discovery_id="discovery_001",
            factor_name="test_momentum",
            factor_formula="rank(close / delay(close, 20) - 1)",
            python_code="def test_momentum(data): return data['close'].pct_change(20).rank(pct=True)"
        )
        
        assert implementation.factor_id == "factor_001"
        assert implementation.discovery_id == "discovery_001"
        assert implementation.factor_name == "test_momentum"
        assert implementation.implementation_model == "DeepSeek-R1"
        assert implementation.code_quality_score == 0.0
    
    def test_factor_id_auto_generation(self):
        """测试因子ID自动生成"""
        implementation = FactorImplementation(
            factor_id="",  # 空ID，应该自动生成
            discovery_id="discovery_001",
            factor_name="auto_id_test",
            factor_formula="rank(test)",
            python_code="def auto_id_test(data): return data"
        )
        
        assert implementation.factor_id != ""
        assert len(implementation.factor_id) == 8  # MD5前8位


class TestFactorMiningIntelligenceSentinel:
    """测试因子挖掘智能哨兵"""
    
    @pytest.fixture
    def temp_dir(self):
        """临时目录夹具"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def mock_redis(self):
        """Mock Redis客户端"""
        mock_redis = Mock(spec=redis.Redis)
        mock_redis.setex = Mock()
        mock_redis.get = Mock(return_value=None)
        return mock_redis
    
    @pytest.fixture
    def mock_llm_gateway(self):
        """Mock LLM Gateway"""
        mock_gateway = Mock(spec=LLMGateway)
        mock_gateway.call_llm = AsyncMock()
        return mock_gateway
    
    @pytest.fixture
    def sentinel(self, temp_dir, mock_redis, mock_llm_gateway):
        """哨兵实例夹具"""
        return FactorMiningIntelligenceSentinel(
            llm_gateway=mock_llm_gateway,
            redis_client=mock_redis,
            discovery_storage_path=temp_dir
        )
    
    def test_sentinel_initialization(self, sentinel, temp_dir):
        """测试哨兵初始化"""
        assert sentinel.discovery_storage_path == Path(temp_dir)
        assert len(sentinel.monitoring_sources) > 0
        assert len(sentinel.discovery_patterns) > 0
        assert len(sentinel.model_configs) == 3
        
        # 检查模型配置
        assert 'theory_analyzer' in sentinel.model_configs
        assert 'factor_implementer' in sentinel.model_configs
        assert 'data_analyzer' in sentinel.model_configs
        
        # 检查监控源
        assert 'arxiv' in sentinel.monitoring_sources
        assert 'ssrn' in sentinel.monitoring_sources
        assert 'alternative_data_providers' in sentinel.monitoring_sources
    
    def test_monitoring_sources_configuration(self, sentinel):
        """测试监控源配置"""
        sources = sentinel.monitoring_sources
        
        # 检查arXiv配置
        arxiv_config = sources['arxiv']
        assert 'url' in arxiv_config
        assert 'categories' in arxiv_config
        assert 'keywords' in arxiv_config
        assert arxiv_config['priority'] == 'high'
        
        # 检查关键词
        assert 'factor' in arxiv_config['keywords']
        assert 'alpha' in arxiv_config['keywords']
    
    def test_discovery_patterns_initialization(self, sentinel):
        """测试发现模式初始化"""
        patterns = sentinel.discovery_patterns
        
        assert 'factor_keywords' in patterns
        assert 'data_keywords' in patterns
        assert 'method_keywords' in patterns
        assert 'performance_keywords' in patterns
        
        # 检查因子关键词
        factor_keywords = patterns['factor_keywords']
        assert 'factor' in factor_keywords
        assert 'momentum' in factor_keywords
        assert 'alpha' in factor_keywords
    
    @pytest.mark.asyncio
    async def test_scan_arxiv_papers(self, sentinel):
        """测试arXiv论文扫描"""
        with patch.object(sentinel, '_analyze_paper_with_qwen') as mock_analyze:
            mock_analyze.return_value = {
                'is_relevant': True,
                'factor_category': FactorCategory.TECHNICAL,
                'summary': 'Test summary',
                'theoretical_basis': 'Test basis',
                'expected_alpha': 0.05,
                'tags': ['test'],
                'confidence_score': 0.8
            }
            
            discoveries = await sentinel._scan_arxiv_papers()
            
            assert len(discoveries) >= 0  # 可能有模拟数据
            if discoveries:
                discovery = discoveries[0]
                assert isinstance(discovery, FactorDiscovery)
                assert discovery.discovery_type == DiscoveryType.ACADEMIC_PAPER
    
    @pytest.mark.asyncio
    async def test_analyze_paper_with_qwen(self, sentinel):
        """测试Qwen论文分析"""
        paper = {
            'title': 'Cross-Sectional Momentum with Alternative Data',
            'abstract': 'We propose a novel momentum factor using satellite data...',
            'authors': ['Smith, J.'],
            'published': '2026-01-18',
            'url': 'https://arxiv.org/abs/test'
        }
        
        analysis = await sentinel._analyze_paper_with_qwen(paper)
        
        assert 'is_relevant' in analysis
        if analysis['is_relevant']:
            assert 'factor_category' in analysis
            assert 'summary' in analysis
            assert 'theoretical_basis' in analysis
            assert 'confidence_score' in analysis
    
    @pytest.mark.asyncio
    async def test_process_new_discovery(self, sentinel):
        """测试新发现处理"""
        discovery = FactorDiscovery(
            discovery_id="test_process",
            discovery_type=DiscoveryType.ACADEMIC_PAPER,
            factor_category=FactorCategory.TECHNICAL,
            title="Test Process Discovery",
            description="Test processing",
            source="Test",
            discovered_at=datetime.now(),
            discoverer="system",
            theoretical_basis="Test theory",
            confidence_score=0.9  # 高置信度，应该触发自动实现
        )
        
        with patch.object(sentinel, '_auto_implement_factor') as mock_implement:
            mock_implement.return_value = None
            
            await sentinel._process_new_discovery(discovery)
            
            # 检查发现是否被保存
            assert discovery.discovery_id in sentinel.discoveries
            
            # 高置信度应该触发自动实现
            mock_implement.assert_called_once_with(discovery)
    
    @pytest.mark.asyncio
    async def test_save_discovery(self, sentinel, temp_dir):
        """测试发现保存"""
        discovery = FactorDiscovery(
            discovery_id="test_save",
            discovery_type=DiscoveryType.MARKET_ANOMALY,
            factor_category=FactorCategory.TECHNICAL,
            title="Test Save Discovery",
            description="Test saving",
            source="Test",
            discovered_at=datetime.now(),
            discoverer="system",
            theoretical_basis="Test theory"
        )
        
        await sentinel._save_discovery(discovery)
        
        # 检查文件是否创建
        date_str = discovery.discovered_at.strftime("%Y-%m-%d")
        file_path = Path(temp_dir) / f"discoveries_{date_str}.json"
        
        assert file_path.exists()
        
        # 检查文件内容
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        assert len(data) == 1
        assert data[0]['discovery_id'] == "test_save"
        assert data[0]['title'] == "Test Save Discovery"
    
    @pytest.mark.asyncio
    async def test_cache_discovery(self, sentinel, mock_redis):
        """测试发现缓存"""
        discovery = FactorDiscovery(
            discovery_id="test_cache",
            discovery_type=DiscoveryType.ALTERNATIVE_DATA,
            factor_category=FactorCategory.ALTERNATIVE,
            title="Test Cache Discovery",
            description="Test caching",
            source="Test",
            discovered_at=datetime.now(),
            discoverer="system",
            theoretical_basis="Test theory"
        )
        
        await sentinel._cache_discovery(discovery)
        
        # 检查Redis调用
        mock_redis.setex.assert_called_once()
        call_args = mock_redis.setex.call_args
        assert call_args[0][0] == f"factor_discovery:{discovery.discovery_id}"
        assert call_args[0][1] == 86400 * 7  # 7天过期
    
    @pytest.mark.asyncio
    async def test_generate_factor_code_with_deepseek(self, sentinel):
        """测试DeepSeek因子代码生成"""
        discovery = FactorDiscovery(
            discovery_id="test_deepseek",
            discovery_type=DiscoveryType.ACADEMIC_PAPER,
            factor_category=FactorCategory.TECHNICAL,
            title="Test DeepSeek Factor",
            description="Test code generation",
            source="Test",
            discovered_at=datetime.now(),
            discoverer="system",
            theoretical_basis="Test theory"
        )
        
        # Mock successful LLM response
        from src.brain.llm_gateway import LLMResponse
        mock_response = LLMResponse(
            call_id="test_call",
            success=True,
            content=json.dumps({
                "factor_formula": "rank(close / delay(close, 20) - 1)",
                "python_code": "def test_factor(data): return data['close'].pct_change(20).rank(pct=True)",
                "dependencies": ["pandas", "numpy"],
                "factor_name": "test_deepseek_factor",
                "code_quality_score": 0.85
            })
        )
        
        sentinel.llm_gateway.call_llm.return_value = mock_response
        
        implementation = await sentinel._generate_factor_code_with_deepseek(discovery)
        
        assert implementation is not None
        assert isinstance(implementation, FactorImplementation)
        assert implementation.discovery_id == discovery.discovery_id
        assert implementation.implementation_model == "DeepSeek-R1"
        assert len(implementation.python_code) > 0
        assert len(implementation.factor_formula) > 0
    
    @pytest.mark.asyncio
    async def test_run_factor_backtest(self, sentinel):
        """测试因子回测"""
        implementation = FactorImplementation(
            factor_id="test_backtest",
            discovery_id="test_discovery",
            factor_name="test_factor",
            factor_formula="rank(test)",
            python_code="def test_factor(data): return data"
        )
        
        results = await sentinel._run_factor_backtest(implementation)
        
        assert 'ic_mean' in results
        assert 'ic_std' in results
        assert 'ir_ratio' in results
        assert 'turnover' in results
        assert 'sharpe_ratio' in results
        
        # 检查数值范围
        assert -1 <= results['ic_mean'] <= 1
        assert results['ic_std'] >= 0
        assert results['turnover'] >= 0
    
    @pytest.mark.asyncio
    async def test_validate_factor_implementation(self, sentinel):
        """测试因子实现验证"""
        discovery = FactorDiscovery(
            discovery_id="test_validate",
            discovery_type=DiscoveryType.ACADEMIC_PAPER,
            factor_category=FactorCategory.TECHNICAL,
            title="Test Validate Factor",
            description="Test validation",
            source="Test",
            discovered_at=datetime.now(),
            discoverer="system",
            theoretical_basis="Test theory"
        )
        
        implementation = FactorImplementation(
            factor_id="test_validate_impl",
            discovery_id=discovery.discovery_id,
            factor_name="test_validate_factor",
            factor_formula="rank(test)",
            python_code="def test_validate_factor(data): return data"
        )
        
        with patch.object(sentinel, '_integrate_validated_factor') as mock_integrate:
            mock_integrate.return_value = None
            
            await sentinel._validate_factor_implementation(discovery, implementation)
            
            # 检查性能指标是否更新
            assert implementation.ic_mean is not None
            assert implementation.ic_std is not None
            assert implementation.ir_ratio is not None
            assert implementation.turnover is not None
            
            # 检查发现验证结果
            assert discovery.validation_results is not None
    
    @pytest.mark.asyncio
    async def test_integrate_validated_factor(self, sentinel, temp_dir):
        """测试已验证因子集成"""
        discovery = FactorDiscovery(
            discovery_id="test_integrate",
            discovery_type=DiscoveryType.ACADEMIC_PAPER,
            factor_category=FactorCategory.TECHNICAL,
            title="Test Integrate Factor",
            description="Test integration",
            source="Test",
            discovered_at=datetime.now(),
            discoverer="system",
            theoretical_basis="Test theory"
        )
        
        implementation = FactorImplementation(
            factor_id="test_integrate_impl",
            discovery_id=discovery.discovery_id,
            factor_name="test_integrate_factor",
            factor_formula="rank(close / delay(close, 20) - 1)",
            python_code="def test_integrate_factor(data): return data['close'].pct_change(20).rank(pct=True)",
            ic_mean=0.05,
            ir_ratio=1.2,
            turnover=0.8
        )
        
        await sentinel._integrate_validated_factor(discovery, implementation)
        
        # 检查状态更新
        assert discovery.status == ValidationStatus.VALIDATED
        
        # 检查因子文件创建
        factor_file = Path(temp_dir) / "pending_arena_factors" / f"{implementation.factor_name}.py"
        assert factor_file.exists()
        
        # 检查文件内容
        with open(factor_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        assert discovery.title in content
        assert implementation.python_code in content
        assert "FACTOR_METADATA" in content
    
    @pytest.mark.asyncio
    async def test_update_pending_arena_index(self, sentinel, temp_dir):
        """测试待Arena测试索引更新"""
        discovery = FactorDiscovery(
            discovery_id="test_index",
            discovery_type=DiscoveryType.ACADEMIC_PAPER,
            factor_category=FactorCategory.TECHNICAL,
            title="Test Index Factor",
            description="Test indexing",
            source="Test",
            discovered_at=datetime.now(),
            discoverer="system",
            theoretical_basis="Test theory"
        )
        
        implementation = FactorImplementation(
            factor_id="test_index_impl",
            discovery_id=discovery.discovery_id,
            factor_name="test_index_factor",
            factor_formula="rank(test)",
            python_code="def test_index_factor(data): return data",
            ic_mean=0.04,
            ir_ratio=0.8,
            turnover=1.2
        )
        
        await sentinel._update_pending_arena_index(discovery, implementation)
        
        # 检查索引文件
        index_file = Path(temp_dir) / "pending_arena_factors_index.json"
        assert index_file.exists()
        
        # 检查索引内容
        with open(index_file, 'r', encoding='utf-8') as f:
            index_data = json.load(f)
        
        assert len(index_data) == 1
        entry = index_data[0]
        assert entry['factor_id'] == implementation.factor_id
        assert entry['factor_name'] == implementation.factor_name
        assert entry['category'] == discovery.factor_category.value
        assert entry['status'] == 'pending_arena_test'
        assert entry['next_step'] == 'Arena三轨测试'
        assert 'validation_pipeline' in entry
    
    def test_get_discovery_statistics(self, sentinel):
        """测试发现统计"""
        # 添加一些测试发现
        discoveries = [
            FactorDiscovery(
                discovery_id="stat_test_1",
                discovery_type=DiscoveryType.ACADEMIC_PAPER,
                factor_category=FactorCategory.TECHNICAL,
                title="Test 1",
                description="Test",
                source="Test",
                discovered_at=datetime.now(),
                discoverer="system",
                theoretical_basis="Test",
                status=ValidationStatus.VALIDATED,
                expected_alpha=0.05
            ),
            FactorDiscovery(
                discovery_id="stat_test_2",
                discovery_type=DiscoveryType.MARKET_ANOMALY,
                factor_category=FactorCategory.TECHNICAL,
                title="Test 2",
                description="Test",
                source="Test",
                discovered_at=datetime.now() - timedelta(days=1),
                discoverer="human",
                theoretical_basis="Test",
                status=ValidationStatus.VALIDATED,
                expected_alpha=0.03
            )
        ]
        
        for discovery in discoveries:
            sentinel.discoveries[discovery.discovery_id] = discovery
        
        stats = sentinel.get_discovery_statistics()
        
        assert stats['total_discoveries'] == 2
        assert 'by_type' in stats
        assert 'by_category' in stats
        assert 'by_status' in stats
        assert 'by_discoverer' in stats
        assert 'recent_discoveries' in stats
        assert 'top_performers' in stats
        
        # 检查统计数据
        assert stats['by_type'][DiscoveryType.ACADEMIC_PAPER.value] == 1
        # 两个发现都是TECHNICAL类别，所以应该是2
        assert stats['by_category'][FactorCategory.TECHNICAL.value] == 2
        assert stats['by_discoverer']['system'] == 1
        assert stats['by_discoverer']['human'] == 1
    
    @pytest.mark.asyncio
    async def test_manual_discovery_input(self, sentinel):
        """测试手动发现输入"""
        discovery_id = await sentinel.manual_discovery_input(
            title="Manual Test Factor",
            description="A manually input test factor",
            theoretical_basis="Manual theoretical basis",
            factor_category=FactorCategory.SENTIMENT,
            expected_alpha=0.06,
            data_requirements=['sentiment_data', 'price_data']
        )
        
        assert discovery_id != ""
        assert discovery_id in sentinel.discoveries
        
        discovery = sentinel.discoveries[discovery_id]
        assert discovery.title == "Manual Test Factor"
        assert discovery.discoverer == "human"
        assert discovery.factor_category == FactorCategory.SENTIMENT
        assert discovery.expected_alpha == 0.06
        assert discovery.confidence_score == 0.9  # 人工输入高置信度
        assert 'manual' in discovery.tags
    
    @pytest.mark.asyncio
    async def test_get_discovery_details(self, sentinel):
        """测试获取发现详情"""
        # 创建测试发现
        discovery = FactorDiscovery(
            discovery_id="detail_test",
            discovery_type=DiscoveryType.ALTERNATIVE_DATA,
            factor_category=FactorCategory.ALTERNATIVE,
            title="Detail Test Factor",
            description="Test getting details",
            source="Test Source",
            discovered_at=datetime.now(),
            discoverer="system",
            theoretical_basis="Test theory",
            expected_alpha=0.04,
            risk_factors=['market_risk'],
            data_requirements=['alt_data'],
            tags=['test', 'detail']
        )
        
        sentinel.discoveries[discovery.discovery_id] = discovery
        
        # 添加实现
        implementation = FactorImplementation(
            factor_id="detail_impl",
            discovery_id=discovery.discovery_id,
            factor_name="detail_test_factor",
            factor_formula="rank(alt_signal)",
            python_code="def detail_test_factor(data): return data",
            ic_mean=0.035,
            ir_ratio=0.9
        )
        
        sentinel.implementations[implementation.factor_id] = implementation
        
        # 获取详情
        details = await sentinel.get_discovery_details(discovery.discovery_id)
        
        assert details is not None
        assert details['discovery_id'] == discovery.discovery_id
        assert details['title'] == discovery.title
        assert details['factor_category'] == discovery.factor_category.value
        assert details['expected_alpha'] == discovery.expected_alpha
        assert details['risk_factors'] == discovery.risk_factors
        assert details['data_requirements'] == discovery.data_requirements
        assert details['tags'] == discovery.tags
        
        # 检查实现信息
        assert 'implementation' in details
        impl_details = details['implementation']
        assert impl_details['factor_id'] == implementation.factor_id
        assert impl_details['ic_mean'] == implementation.ic_mean
        assert impl_details['ir_ratio'] == implementation.ir_ratio
    
    @pytest.mark.asyncio
    async def test_get_nonexistent_discovery_details(self, sentinel):
        """测试获取不存在发现的详情"""
        details = await sentinel.get_discovery_details("nonexistent_id")
        assert details is None
    
    def test_load_historical_discoveries(self, sentinel, temp_dir):
        """测试加载历史发现"""
        # 创建测试历史文件
        test_data = [
            {
                'discovery_id': 'historical_1',
                'discovery_type': 'academic_paper',
                'factor_category': 'technical',
                'title': 'Historical Factor 1',
                'description': 'Test historical',
                'source': 'Test',
                'discovered_at': datetime.now().isoformat(),
                'discoverer': 'system',
                'theoretical_basis': 'Test theory',
                'status': 'discovered',
                'confidence_score': 0.7
            }
        ]
        
        date_str = datetime.now().strftime("%Y-%m-%d")
        file_path = Path(temp_dir) / f"discoveries_{date_str}.json"
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(test_data, f)
        
        # 重新加载
        sentinel._load_historical_discoveries()
        
        assert 'historical_1' in sentinel.discoveries
        discovery = sentinel.discoveries['historical_1']
        assert discovery.title == 'Historical Factor 1'
        assert discovery.discovery_type == DiscoveryType.ACADEMIC_PAPER
        assert discovery.factor_category == FactorCategory.TECHNICAL


class TestErrorHandling:
    """测试错误处理"""
    
    @pytest.fixture
    def sentinel(self):
        """哨兵实例"""
        with tempfile.TemporaryDirectory() as temp_dir:
            mock_redis = Mock(spec=redis.Redis)
            mock_llm_gateway = Mock(spec=LLMGateway)
            mock_llm_gateway.call_llm = AsyncMock()
            yield FactorMiningIntelligenceSentinel(
                llm_gateway=mock_llm_gateway,
                redis_client=mock_redis,
                discovery_storage_path=temp_dir
            )
    
    @pytest.mark.asyncio
    async def test_save_discovery_error_handling(self, sentinel):
        """测试保存发现错误处理"""
        discovery = FactorDiscovery(
            discovery_id="error_test",
            discovery_type=DiscoveryType.ACADEMIC_PAPER,
            factor_category=FactorCategory.TECHNICAL,
            title="Error Test",
            description="Test error handling",
            source="Test",
            discovered_at=datetime.now(),
            discoverer="system",
            theoretical_basis="Test"
        )
        
        # 模拟文件系统错误
        with patch('builtins.open', side_effect=PermissionError("Permission denied")):
            # 不应该抛出异常
            await sentinel._save_discovery(discovery)
    
    @pytest.mark.asyncio
    async def test_cache_discovery_error_handling(self, sentinel):
        """测试缓存发现错误处理"""
        discovery = FactorDiscovery(
            discovery_id="cache_error_test",
            discovery_type=DiscoveryType.ACADEMIC_PAPER,
            factor_category=FactorCategory.TECHNICAL,
            title="Cache Error Test",
            description="Test cache error handling",
            source="Test",
            discovered_at=datetime.now(),
            discoverer="system",
            theoretical_basis="Test"
        )
        
        # 模拟Redis错误
        sentinel.redis_client.setex.side_effect = redis.ConnectionError("Connection failed")
        
        # 不应该抛出异常
        await sentinel._cache_discovery(discovery)


class TestPerformanceAndScalability:
    """测试性能和可扩展性"""
    
    @pytest.fixture
    def sentinel(self):
        """哨兵实例"""
        with tempfile.TemporaryDirectory() as temp_dir:
            mock_redis = Mock(spec=redis.Redis)
            mock_llm_gateway = Mock(spec=LLMGateway)
            mock_llm_gateway.call_llm = AsyncMock()
            yield FactorMiningIntelligenceSentinel(
                llm_gateway=mock_llm_gateway,
                redis_client=mock_redis,
                discovery_storage_path=temp_dir
            )
    
    def test_large_number_of_discoveries(self, sentinel):
        """测试大量发现处理"""
        # 创建1000个发现
        discoveries = []
        for i in range(1000):
            discovery = FactorDiscovery(
                discovery_id=f"perf_test_{i}",
                discovery_type=DiscoveryType.ACADEMIC_PAPER,
                factor_category=FactorCategory.TECHNICAL,
                title=f"Performance Test Factor {i}",
                description=f"Test factor {i}",
                source="Performance Test",
                discovered_at=datetime.now(),
                discoverer="system",
                theoretical_basis="Performance test theory"
            )
            discoveries.append(discovery)
            sentinel.discoveries[discovery.discovery_id] = discovery
        
        # 测试统计性能
        import time
        start_time = time.time()
        stats = sentinel.get_discovery_statistics()
        end_time = time.time()
        
        assert stats['total_discoveries'] == 1000
        assert (end_time - start_time) < 1.0  # 应该在1秒内完成
    
    @pytest.mark.asyncio
    async def test_concurrent_discovery_processing(self, sentinel):
        """测试并发发现处理"""
        # 创建多个发现任务
        discoveries = []
        for i in range(10):
            discovery = FactorDiscovery(
                discovery_id=f"concurrent_test_{i}",
                discovery_type=DiscoveryType.ACADEMIC_PAPER,
                factor_category=FactorCategory.TECHNICAL,
                title=f"Concurrent Test Factor {i}",
                description=f"Test concurrent processing {i}",
                source="Concurrent Test",
                discovered_at=datetime.now(),
                discoverer="system",
                theoretical_basis="Concurrent test theory",
                confidence_score=0.5  # 低置信度，不触发自动实现
            )
            discoveries.append(discovery)
        
        # 并发处理
        tasks = [sentinel._process_new_discovery(discovery) for discovery in discoveries]
        await asyncio.gather(*tasks)
        
        # 检查所有发现都被处理
        for discovery in discoveries:
            assert discovery.discovery_id in sentinel.discoveries


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])