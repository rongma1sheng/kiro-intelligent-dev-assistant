"""RiskFactorRegistry单元测试

白皮书依据: 第四章 4.1.1 专业风险因子挖掘系统 - 统一接口

测试覆盖:
1. 初始化参数验证
2. 挖掘器注册和取消注册
3. 因子收集
4. 因子查询
5. 事件发布
6. 边界条件测试
7. 异常处理测试
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch

from src.evolution.risk_mining.risk_factor_registry import RiskFactorRegistry
from src.evolution.risk_mining.risk_factor import RiskFactor
from src.infra.event_bus import EventBus


class TestRiskFactorRegistryInit:
    """测试初始化"""
    
    @pytest.fixture
    def event_bus(self):
        """创建EventBus mock"""
        bus = Mock(spec=EventBus)
        bus.publish = AsyncMock()
        return bus
    
    def test_init_default_params(self, event_bus):
        """测试默认参数初始化"""
        registry = RiskFactorRegistry(event_bus)
        
        assert registry.event_bus == event_bus
        assert registry.max_factors_per_symbol == 100
        assert len(registry.miners) == 0
        assert len(registry.factors) == 0
    
    def test_init_custom_params(self, event_bus):
        """测试自定义参数初始化"""
        registry = RiskFactorRegistry(
            event_bus,
            max_factors_per_symbol=50
        )
        
        assert registry.max_factors_per_symbol == 50
    
    def test_init_none_event_bus(self):
        """测试event_bus为None"""
        with pytest.raises(ValueError, match="event_bus不能为None"):
            RiskFactorRegistry(None)
    
    def test_init_invalid_max_factors(self, event_bus):
        """测试无效的max_factors_per_symbol"""
        with pytest.raises(ValueError, match="max_factors_per_symbol必须大于0"):
            RiskFactorRegistry(event_bus, max_factors_per_symbol=0)
        
        with pytest.raises(ValueError, match="max_factors_per_symbol必须大于0"):
            RiskFactorRegistry(event_bus, max_factors_per_symbol=-1)


class TestMinerRegistration:
    """测试挖掘器注册"""
    
    @pytest.fixture
    def event_bus(self):
        """创建EventBus mock"""
        bus = Mock(spec=EventBus)
        bus.publish = AsyncMock()
        return bus
    
    @pytest.fixture
    def registry(self, event_bus):
        """创建注册中心实例"""
        return RiskFactorRegistry(event_bus)
    
    @pytest.fixture
    def mock_miner(self):
        """创建mock挖掘器"""
        return Mock()
    
    def test_register_miner(self, registry, mock_miner):
        """测试注册挖掘器"""
        registry.register_miner(mock_miner)
        
        assert len(registry.miners) == 1
        assert mock_miner in registry.miners
        assert registry.stats['miners_registered'] == 1
    
    def test_register_multiple_miners(self, registry):
        """测试注册多个挖掘器"""
        miner1 = Mock()
        miner2 = Mock()
        miner3 = Mock()
        
        registry.register_miner(miner1)
        registry.register_miner(miner2)
        registry.register_miner(miner3)
        
        assert len(registry.miners) == 3
        assert registry.stats['miners_registered'] == 3
    
    def test_register_none_miner(self, registry):
        """测试注册None挖掘器"""
        with pytest.raises(ValueError, match="miner不能为None"):
            registry.register_miner(None)
    
    def test_register_duplicate_miner(self, registry, mock_miner):
        """测试重复注册挖掘器"""
        registry.register_miner(mock_miner)
        
        with pytest.raises(ValueError, match="挖掘器已经注册"):
            registry.register_miner(mock_miner)
    
    def test_unregister_miner(self, registry, mock_miner):
        """测试取消注册挖掘器"""
        registry.register_miner(mock_miner)
        
        result = registry.unregister_miner(mock_miner)
        
        assert result is True
        assert len(registry.miners) == 0
        assert registry.stats['miners_registered'] == 0
    
    def test_unregister_nonexistent_miner(self, registry, mock_miner):
        """测试取消注册不存在的挖掘器"""
        result = registry.unregister_miner(mock_miner)
        
        assert result is False
    
    def test_get_registered_miners(self, registry):
        """测试获取已注册的挖掘器列表"""
        miner1 = Mock()
        miner1.__class__.__name__ = 'FlowRiskFactorMiner'
        miner2 = Mock()
        miner2.__class__.__name__ = 'MicrostructureRiskFactorMiner'
        
        registry.register_miner(miner1)
        registry.register_miner(miner2)
        
        miners = registry.get_registered_miners()
        
        assert len(miners) == 2
        assert 'FlowRiskFactorMiner' in miners
        assert 'MicrostructureRiskFactorMiner' in miners


class TestFactorCollection:
    """测试因子收集"""
    
    @pytest.fixture
    def event_bus(self):
        """创建EventBus mock"""
        bus = Mock(spec=EventBus)
        bus.publish = AsyncMock()
        return bus
    
    @pytest.fixture
    def registry(self, event_bus):
        """创建注册中心实例"""
        return RiskFactorRegistry(event_bus)
    
    @pytest.fixture
    def sample_factor(self):
        """创建示例因子"""
        return RiskFactor(
            factor_type='flow',
            symbol='000001',
            risk_value=0.8,
            confidence=0.9,
            timestamp=datetime.now(),
            metadata={'risk_type': 'capital_retreat'}
        )
    
    @pytest.mark.asyncio
    async def test_add_factor(self, registry, sample_factor):
        """测试添加因子"""
        await registry.add_factor(sample_factor)
        
        assert registry.get_factor_count('000001') == 1
        assert registry.stats['factors_collected'] == 1
        assert registry.stats['factors_published'] == 1
    
    @pytest.mark.asyncio
    async def test_add_multiple_factors(self, registry):
        """测试添加多个因子"""
        for i in range(5):
            factor = RiskFactor(
                factor_type='flow',
                symbol='000001',
                risk_value=0.5 + i * 0.1,
                confidence=0.9,
                timestamp=datetime.now() + timedelta(seconds=i),
                metadata={'index': i}
            )
            await registry.add_factor(factor)
        
        assert registry.get_factor_count('000001') == 5
        assert registry.stats['factors_collected'] == 5
    
    @pytest.mark.asyncio
    async def test_add_factor_none(self, registry):
        """测试添加None因子"""
        with pytest.raises(ValueError, match="factor不能为None"):
            await registry.add_factor(None)
    
    @pytest.mark.asyncio
    async def test_add_factor_limit(self, registry):
        """测试因子数量限制"""
        # 设置较小的限制
        registry.max_factors_per_symbol = 10
        
        # 添加超过限制的因子
        for i in range(15):
            factor = RiskFactor(
                factor_type='flow',
                symbol='000001',
                risk_value=0.5,
                confidence=0.9,
                timestamp=datetime.now() + timedelta(seconds=i),
                metadata={'index': i}
            )
            await registry.add_factor(factor)
        
        # 应该只保留最新的10个
        assert registry.get_factor_count('000001') == 10
    
    @pytest.mark.asyncio
    async def test_collect_factors(self, registry):
        """测试收集因子"""
        # 添加多个因子
        timestamps = []
        for i in range(5):
            ts = datetime.now() + timedelta(seconds=i)
            timestamps.append(ts)
            factor = RiskFactor(
                factor_type='flow',
                symbol='000001',
                risk_value=0.5,
                confidence=0.9,
                timestamp=ts,
                metadata={'index': i}
            )
            await registry.add_factor(factor)
        
        # 收集因子
        factors = await registry.collect_factors('000001')
        
        assert len(factors) == 5
        # 应该按时间戳降序排列
        assert factors[0].timestamp == timestamps[4]
        assert factors[4].timestamp == timestamps[0]
    
    @pytest.mark.asyncio
    async def test_collect_factors_empty_symbol(self, registry):
        """测试收集空标的的因子"""
        with pytest.raises(ValueError, match="symbol不能为空"):
            await registry.collect_factors('')
    
    @pytest.mark.asyncio
    async def test_collect_factors_nonexistent_symbol(self, registry):
        """测试收集不存在的标的的因子"""
        factors = await registry.collect_factors('999999')
        
        assert len(factors) == 0


class TestFactorQuery:
    """测试因子查询"""
    
    @pytest.fixture
    def event_bus(self):
        """创建EventBus mock"""
        bus = Mock(spec=EventBus)
        bus.publish = AsyncMock()
        return bus
    
    @pytest.fixture
    def registry(self, event_bus):
        """创建注册中心实例"""
        return RiskFactorRegistry(event_bus)
    
    @pytest.mark.asyncio
    async def test_get_latest_factor(self, registry):
        """测试获取最新因子"""
        # 添加多个因子
        for i in range(5):
            factor = RiskFactor(
                factor_type='flow',
                symbol='000001',
                risk_value=0.5 + i * 0.1,
                confidence=0.9,
                timestamp=datetime.now() + timedelta(seconds=i),
                metadata={'index': i}
            )
            await registry.add_factor(factor)
        
        # 获取最新因子
        latest = await registry.get_latest_factor('000001', 'flow')
        
        assert latest is not None
        assert latest.metadata['index'] == 4
        assert latest.risk_value == 0.9
    
    @pytest.mark.asyncio
    async def test_get_latest_factor_by_type(self, registry):
        """测试按类型获取最新因子"""
        # 添加不同类型的因子
        flow_factor = RiskFactor(
            factor_type='flow',
            symbol='000001',
            risk_value=0.8,
            confidence=0.9,
            timestamp=datetime.now(),
            metadata={'type': 'flow'}
        )
        await registry.add_factor(flow_factor)
        
        micro_factor = RiskFactor(
            factor_type='microstructure',
            symbol='000001',
            risk_value=0.7,
            confidence=0.85,
            timestamp=datetime.now() + timedelta(seconds=1),
            metadata={'type': 'micro'}
        )
        await registry.add_factor(micro_factor)
        
        # 获取flow类型的最新因子
        latest_flow = await registry.get_latest_factor('000001', 'flow')
        assert latest_flow is not None
        assert latest_flow.factor_type == 'flow'
        assert latest_flow.metadata['type'] == 'flow'
        
        # 获取microstructure类型的最新因子
        latest_micro = await registry.get_latest_factor('000001', 'microstructure')
        assert latest_micro is not None
        assert latest_micro.factor_type == 'microstructure'
        assert latest_micro.metadata['type'] == 'micro'
    
    @pytest.mark.asyncio
    async def test_get_latest_factor_empty_symbol(self, registry):
        """测试获取空标的的最新因子"""
        with pytest.raises(ValueError, match="symbol不能为空"):
            await registry.get_latest_factor('', 'flow')
    
    @pytest.mark.asyncio
    async def test_get_latest_factor_invalid_type(self, registry):
        """测试获取无效类型的最新因子"""
        with pytest.raises(ValueError, match="无效的factor_type"):
            await registry.get_latest_factor('000001', 'invalid_type')
    
    @pytest.mark.asyncio
    async def test_get_latest_factor_nonexistent(self, registry):
        """测试获取不存在的因子"""
        latest = await registry.get_latest_factor('999999', 'flow')
        
        assert latest is None


class TestEventPublishing:
    """测试事件发布"""
    
    @pytest.fixture
    def event_bus(self):
        """创建EventBus mock"""
        bus = Mock(spec=EventBus)
        bus.publish = AsyncMock()
        return bus
    
    @pytest.fixture
    def registry(self, event_bus):
        """创建注册中心实例"""
        return RiskFactorRegistry(event_bus)
    
    @pytest.fixture
    def sample_factor(self):
        """创建示例因子"""
        return RiskFactor(
            factor_type='flow',
            symbol='000001',
            risk_value=0.8,
            confidence=0.9,
            timestamp=datetime.now(),
            metadata={'risk_type': 'capital_retreat'}
        )
    
    @pytest.mark.asyncio
    async def test_publish_factor_event(self, registry, event_bus, sample_factor):
        """测试发布因子事件"""
        await registry.add_factor(sample_factor)
        
        # 验证事件总线被调用
        assert event_bus.publish.called
        assert event_bus.publish.call_count == 1
        
        # 验证事件数据
        call_args = event_bus.publish.call_args
        event = call_args[0][0]
        
        assert event.source_module == 'risk_factor_registry'
        assert event.data['symbol'] == '000001'
        assert event.data['factor_type'] == 'flow'
        assert event.data['risk_value'] == 0.8
    
    @pytest.mark.asyncio
    async def test_publish_multiple_events(self, registry, event_bus):
        """测试发布多个事件"""
        for i in range(3):
            factor = RiskFactor(
                factor_type='flow',
                symbol=f'00000{i}',
                risk_value=0.5 + i * 0.1,
                confidence=0.9,
                timestamp=datetime.now(),
                metadata={'index': i}
            )
            await registry.add_factor(factor)
        
        # 验证事件总线被调用3次
        assert event_bus.publish.call_count == 3


class TestStatistics:
    """测试统计信息"""
    
    @pytest.fixture
    def event_bus(self):
        """创建EventBus mock"""
        bus = Mock(spec=EventBus)
        bus.publish = AsyncMock()
        return bus
    
    @pytest.fixture
    def registry(self, event_bus):
        """创建注册中心实例"""
        return RiskFactorRegistry(event_bus)
    
    @pytest.mark.asyncio
    async def test_get_factor_count_by_symbol(self, registry):
        """测试按标的获取因子数量"""
        # 添加因子
        for i in range(3):
            factor = RiskFactor(
                factor_type='flow',
                symbol='000001',
                risk_value=0.5,
                confidence=0.9,
                timestamp=datetime.now(),
                metadata={}
            )
            await registry.add_factor(factor)
        
        count = registry.get_factor_count('000001')
        assert count == 3
    
    @pytest.mark.asyncio
    async def test_get_total_factor_count(self, registry):
        """测试获取总因子数量"""
        # 添加不同标的的因子
        for symbol in ['000001', '000002', '000003']:
            for i in range(2):
                factor = RiskFactor(
                    factor_type='flow',
                    symbol=symbol,
                    risk_value=0.5,
                    confidence=0.9,
                    timestamp=datetime.now(),
                    metadata={}
                )
                await registry.add_factor(factor)
        
        total_count = registry.get_factor_count()
        assert total_count == 6
    
    @pytest.mark.asyncio
    async def test_get_stats(self, registry):
        """测试获取统计信息"""
        # 注册挖掘器
        miner = Mock()
        registry.register_miner(miner)
        
        # 添加因子
        factor = RiskFactor(
            factor_type='flow',
            symbol='000001',
            risk_value=0.5,
            confidence=0.9,
            timestamp=datetime.now(),
            metadata={}
        )
        await registry.add_factor(factor)
        
        # 查询因子
        await registry.collect_factors('000001')
        await registry.get_latest_factor('000001', 'flow')
        
        stats = registry.get_stats()
        
        assert stats['miners_registered'] == 1
        assert stats['factors_collected'] == 1
        assert stats['factors_published'] == 1
        assert stats['queries_executed'] == 2
        assert stats['total_factors'] == 1
        assert stats['symbols_tracked'] == 1
        assert 'uptime_seconds' in stats
        assert 'factors_per_second' in stats


class TestClearFactors:
    """测试清除因子"""
    
    @pytest.fixture
    def event_bus(self):
        """创建EventBus mock"""
        bus = Mock(spec=EventBus)
        bus.publish = AsyncMock()
        return bus
    
    @pytest.fixture
    def registry(self, event_bus):
        """创建注册中心实例"""
        return RiskFactorRegistry(event_bus)
    
    @pytest.mark.asyncio
    async def test_clear_factors_by_symbol(self, registry):
        """测试按标的清除因子"""
        # 添加因子
        for i in range(3):
            factor = RiskFactor(
                factor_type='flow',
                symbol='000001',
                risk_value=0.5,
                confidence=0.9,
                timestamp=datetime.now(),
                metadata={}
            )
            await registry.add_factor(factor)
        
        count = registry.clear_factors('000001')
        
        assert count == 3
        assert registry.get_factor_count('000001') == 0
    
    @pytest.mark.asyncio
    async def test_clear_all_factors(self, registry):
        """测试清除所有因子"""
        # 添加不同标的的因子
        for symbol in ['000001', '000002']:
            for i in range(2):
                factor = RiskFactor(
                    factor_type='flow',
                    symbol=symbol,
                    risk_value=0.5,
                    confidence=0.9,
                    timestamp=datetime.now(),
                    metadata={}
                )
                await registry.add_factor(factor)
        
        count = registry.clear_factors()
        
        assert count == 4
        assert registry.get_factor_count() == 0
    
    @pytest.mark.asyncio
    async def test_clear_nonexistent_symbol(self, registry):
        """测试清除不存在的标的"""
        count = registry.clear_factors('999999')
        
        assert count == 0
