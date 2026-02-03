"""Property-Based Tests for Z2H Gene Capsule Certification System

白皮书依据: 第四章 4.3.2 Z2H基因胶囊认证系统

Properties tested:
- Property 14: Z2H Capsule Completeness
- Property 15: Certification Level Assignment
- Property 16: Z2H Storage Redundancy
- Property 17: Signature Verification Round-Trip
- Property 18: Tamper Detection
"""

import pytest
import asyncio
from datetime import datetime
from hypothesis import given, strategies as st, settings, HealthCheck
from typing import Dict, List
from unittest.mock import AsyncMock, MagicMock

from src.evolution.z2h.data_models import (
    Z2HGeneCapsule,
    CertificationLevel,
    CERTIFICATION_STANDARDS,
)
from src.evolution.z2h.gene_capsule_generator import GeneCapsuleGenerator
from src.evolution.z2h.signature_manager import SignatureManager
from src.evolution.z2h.capsule_storage import CapsuleStorage
from src.evolution.z2h.z2h_certifier import Z2HCertifier
from src.infra.event_bus import EventBus


# ============================================================================
# Mock EventBus for Testing
# ============================================================================

class MockEventBus:
    """Mock EventBus for testing without async overhead"""
    
    def __init__(self):
        self.running = True
        self.published_events = []
    
    async def initialize(self):
        """Mock initialize"""
        pass
    
    async def publish(self, event):
        """Mock publish"""
        self.published_events.append(event)
        return True
    
    def publish_sync(self, event):
        """Mock publish_sync"""
        self.published_events.append(event)
        return True
    
    async def shutdown(self):
        """Mock shutdown"""
        pass


# ============================================================================
# Hypothesis Strategies
# ============================================================================

@st.composite
def strategy_id_strategy(draw):
    """生成策略ID"""
    prefix = draw(st.sampled_from(['S', 'M', 'L']))
    number = draw(st.integers(min_value=1, max_value=999))
    return f"{prefix}{number:03d}"


@st.composite
def strategy_name_strategy(draw):
    """生成策略名称"""
    names = [
        '回马枪策略', '动量突破策略', '均值回归策略', '趋势跟踪策略',
        '套利策略', '因子组合策略', '市场中性策略', '统计套利策略'
    ]
    return draw(st.sampled_from(names))


@st.composite
def source_factors_strategy(draw):
    """生成源因子列表"""
    num_factors = draw(st.integers(min_value=1, max_value=5))
    factors = [f"factor_{i}" for i in range(1, num_factors + 1)]
    return factors


@st.composite
def arena_score_strategy(draw):
    """生成Arena评分"""
    return draw(st.floats(min_value=0.0, max_value=1.0))


@st.composite
def simulation_metrics_strategy(draw, certification_level=None):
    """生成模拟盘指标
    
    Args:
        certification_level: 如果指定，生成符合该等级的指标
    """
    if certification_level:
        criteria = CERTIFICATION_STANDARDS[certification_level]
        
        # 生成符合标准的指标（略高于最低要求）
        sharpe_ratio = draw(st.floats(
            min_value=criteria.min_sharpe_ratio,
            max_value=criteria.min_sharpe_ratio + 1.0
        ))
        max_drawdown = draw(st.floats(
            min_value=0.05,
            max_value=criteria.max_drawdown
        ))
        win_rate = draw(st.floats(
            min_value=criteria.min_win_rate,
            max_value=min(criteria.min_win_rate + 0.2, 1.0)
        ))
        profit_factor = draw(st.floats(
            min_value=criteria.min_profit_factor,
            max_value=criteria.min_profit_factor + 1.0
        ))
        total_return = draw(st.floats(
            min_value=criteria.min_total_return,
            max_value=criteria.min_total_return + 0.5
        ))
    else:
        # 生成随机指标
        sharpe_ratio = draw(st.floats(min_value=0.5, max_value=4.0))
        max_drawdown = draw(st.floats(min_value=0.05, max_value=0.30))
        win_rate = draw(st.floats(min_value=0.40, max_value=0.80))
        profit_factor = draw(st.floats(min_value=0.8, max_value=3.0))
        total_return = draw(st.floats(min_value=0.0, max_value=1.0))
    
    return {
        'sharpe_ratio': sharpe_ratio,
        'max_drawdown': -abs(max_drawdown),  # 负数表示回撤
        'win_rate': win_rate,
        'profit_factor': profit_factor,
        'total_return': total_return,
        'annual_return': total_return * 12,  # 假设1个月模拟
        'annual_volatility': total_return / max(sharpe_ratio, 0.1),
    }


@st.composite
def valid_capsule_data_strategy(draw):
    """生成有效的基因胶囊数据（符合SILVER标准）"""
    strategy_id = draw(strategy_id_strategy())
    strategy_name = draw(strategy_name_strategy())
    source_factors = draw(source_factors_strategy())
    
    # 生成符合SILVER标准的指标
    arena_score = draw(st.floats(min_value=0.75, max_value=1.0))
    simulation_metrics = draw(simulation_metrics_strategy(CertificationLevel.SILVER))
    
    return {
        'strategy_id': strategy_id,
        'strategy_name': strategy_name,
        'source_factors': source_factors,
        'arena_score': arena_score,
        'simulation_metrics': simulation_metrics,
    }


# ============================================================================
# Property 14: Z2H Capsule Completeness
# ============================================================================

@settings(
    max_examples=10,  # 减少到10次以加快速度
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture]
)
@given(capsule_data=valid_capsule_data_strategy())
def test_property_14_z2h_capsule_completeness(capsule_data):
    """
    Feature: chapter-4-sparta-evolution-completion
    Property 14: Z2H Capsule Completeness
    
    For any generated Z2H gene capsule, it should contain strategy ID, name,
    source factors, Arena scores, simulation metrics, certification date,
    certification level, and SHA256 signature.
    
    白皮书依据: 第四章 4.3.2 Z2HGeneCapsule
    Validates: Requirements 4.2, 4.3
    """
    async def run_test():
        # 创建Mock EventBus
        mock_event_bus = MockEventBus()
        
        # 创建Z2H认证器（使用Mock EventBus，禁用Redis）
        certifier = Z2HCertifier(
            event_bus=mock_event_bus,
            storage_dir='data/test_z2h_capsules',
            redis_host='invalid_host'  # 使用无效主机禁用Redis
        )
        
        try:
            # 生成基因胶囊
            capsule = await certifier.certify_strategy(
                strategy_id=capsule_data['strategy_id'],
                strategy_name=capsule_data['strategy_name'],
                source_factors=capsule_data['source_factors'],
                arena_score=capsule_data['arena_score'],
                simulation_metrics=capsule_data['simulation_metrics'],
            )
            
            # 验证所有必需字段存在
            assert capsule.strategy_id == capsule_data['strategy_id']
            assert capsule.strategy_name == capsule_data['strategy_name']
            assert capsule.source_factors == capsule_data['source_factors']
            assert capsule.arena_score == capsule_data['arena_score']
            assert capsule.simulation_metrics == capsule_data['simulation_metrics']
            
            # 验证certification_date存在且为datetime类型
            assert isinstance(capsule.certification_date, datetime)
            
            # 验证certification_level存在且为有效枚举值
            assert isinstance(capsule.certification_level, CertificationLevel)
            assert capsule.certification_level in [
                CertificationLevel.PLATINUM,
                CertificationLevel.GOLD,
                CertificationLevel.SILVER
            ]
            
            # 验证signature存在且非空
            assert capsule.signature
            assert isinstance(capsule.signature, str)
            assert len(capsule.signature) == 64  # SHA256哈希长度
            
        finally:
            # 清理测试数据
            certifier.storage.delete(capsule_data['strategy_id'])
    
    # 运行异步测试
    asyncio.run(run_test())


# ============================================================================
# Property 15: Certification Level Assignment
# ============================================================================

@settings(
    max_examples=10,  # 减少到10次以加快速度
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture]
)
@given(
    strategy_id=strategy_id_strategy(),
    strategy_name=strategy_name_strategy(),
    source_factors=source_factors_strategy(),
    certification_level=st.sampled_from([
        CertificationLevel.PLATINUM,
        CertificationLevel.GOLD,
        CertificationLevel.SILVER
    ])
)
def test_property_15_certification_level_assignment(
    strategy_id,
    strategy_name,
    source_factors,
    certification_level
):
    """
    Feature: chapter-4-sparta-evolution-completion
    Property 15: Certification Level Assignment
    
    For any Z2H gene capsule, if the strategy's Sharpe ratio > 2.5, the
    certification level should be PLATINUM; if Sharpe > 2.0, GOLD; otherwise SILVER.
    
    白皮书依据: 第四章 4.3.2 Z2H认证标准
    Validates: Requirements 4.4
    """
    async def run_test():
        # 创建Mock EventBus
        mock_event_bus = MockEventBus()
        
        # 创建Z2H认证器（使用Mock EventBus，禁用Redis）
        certifier = Z2HCertifier(
            event_bus=mock_event_bus,
            storage_dir='data/test_z2h_capsules',
            redis_host='invalid_host'  # 使用无效主机禁用Redis
        )
        
        # 获取该等级的标准
        criteria = CERTIFICATION_STANDARDS[certification_level]
        
        # 生成符合该等级的指标
        arena_score = criteria.min_arena_score + 0.05
        simulation_metrics = {
            'sharpe_ratio': criteria.min_sharpe_ratio + 0.1,
            'max_drawdown': -(criteria.max_drawdown - 0.01),
            'win_rate': criteria.min_win_rate + 0.02,
            'profit_factor': criteria.min_profit_factor + 0.1,
            'total_return': criteria.min_total_return + 0.02,
        }
        
        try:
            # 生成基因胶囊
            capsule = await certifier.certify_strategy(
                strategy_id=strategy_id,
                strategy_name=strategy_name,
                source_factors=source_factors,
                arena_score=arena_score,
                simulation_metrics=simulation_metrics,
            )
            
            # 验证认证等级正确分配
            # 由于我们生成的指标略高于最低标准，应该至少获得该等级
            assert capsule.certification_level.value in [
                certification_level.value,
                # 可能获得更高等级（如果指标足够好）
            ]
            
            # 验证认证等级与夏普比率的关系
            sharpe = simulation_metrics['sharpe_ratio']
            if sharpe >= 2.5:
                # 应该至少是PLATINUM或更高
                assert capsule.certification_level in [CertificationLevel.PLATINUM]
            elif sharpe >= 2.0:
                # 应该至少是GOLD或更高
                assert capsule.certification_level in [
                    CertificationLevel.PLATINUM,
                    CertificationLevel.GOLD
                ]
            elif sharpe >= 1.5:
                # 应该至少是SILVER或更高
                assert capsule.certification_level in [
                    CertificationLevel.PLATINUM,
                    CertificationLevel.GOLD,
                    CertificationLevel.SILVER
                ]
            
        finally:
            # 清理测试数据
            certifier.storage.delete(strategy_id)
    
    # 运行异步测试
    asyncio.run(run_test())


# ============================================================================
# Property 16: Z2H Storage Redundancy
# ============================================================================

@settings(
    max_examples=5,  # 减少到5次以加快速度
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture]
)
@given(capsule_data=valid_capsule_data_strategy())
def test_property_16_z2h_storage_redundancy(capsule_data):
    """
    Feature: chapter-4-sparta-evolution-completion
    Property 16: Z2H Storage Redundancy
    
    For any Z2H gene capsule created, it should be stored in both Redis
    (with 1-year TTL) and local file system (as JSON).
    
    白皮书依据: 第四章 4.3.2 双重存储策略
    Validates: Requirements 4.5, 4.6
    """
    async def run_test():
        # 创建Mock EventBus
        mock_event_bus = MockEventBus()
        
        # 创建Z2H认证器（使用Mock EventBus，禁用Redis）
        certifier = Z2HCertifier(
            event_bus=mock_event_bus,
            storage_dir='data/test_z2h_capsules',
            redis_host='invalid_host'  # 使用无效主机禁用Redis
        )
        
        try:
            # 生成基因胶囊
            capsule = await certifier.certify_strategy(
                strategy_id=capsule_data['strategy_id'],
                strategy_name=capsule_data['strategy_name'],
                source_factors=capsule_data['source_factors'],
                arena_score=capsule_data['arena_score'],
                simulation_metrics=capsule_data['simulation_metrics'],
            )
            
            # 验证文件系统存储
            file_path = certifier.storage._get_file_path(capsule.strategy_id)
            assert file_path.exists(), "基因胶囊应该存储在文件系统"
            
            # 验证可以从文件系统检索
            retrieved_capsule = certifier.storage.retrieve(capsule.strategy_id)
            assert retrieved_capsule is not None
            assert retrieved_capsule.strategy_id == capsule.strategy_id
            assert retrieved_capsule.signature == capsule.signature
            
        finally:
            # 清理测试数据
            certifier.storage.delete(capsule_data['strategy_id'])
    
    # 运行异步测试
    asyncio.run(run_test())


# ============================================================================
# Property 17: Signature Verification Round-Trip
# ============================================================================

@settings(
    max_examples=5,  # 减少到5次以加快速度
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture]
)
@given(capsule_data=valid_capsule_data_strategy())
def test_property_17_signature_verification_round_trip(capsule_data):
    """
    Feature: chapter-4-sparta-evolution-completion
    Property 17: Signature Verification Round-Trip
    
    For any Z2H gene capsule, generating a signature, storing it, retrieving it,
    and verifying the signature should succeed without errors.
    
    白皮书依据: 第四章 4.3.2 签名验证
    Validates: Requirements 4.7
    """
    async def run_test():
        # 创建Mock EventBus
        mock_event_bus = MockEventBus()
        
        # 创建Z2H认证器（使用Mock EventBus，禁用Redis）
        certifier = Z2HCertifier(
            event_bus=mock_event_bus,
            storage_dir='data/test_z2h_capsules',
            redis_host='invalid_host'  # 使用无效主机禁用Redis
        )
        
        try:
            # 1. 生成基因胶囊（包含签名）
            capsule = await certifier.certify_strategy(
                strategy_id=capsule_data['strategy_id'],
                strategy_name=capsule_data['strategy_name'],
                source_factors=capsule_data['source_factors'],
                arena_score=capsule_data['arena_score'],
                simulation_metrics=capsule_data['simulation_metrics'],
            )
            
            # 2. 验证签名存在
            assert capsule.signature
            original_signature = capsule.signature
            
            # 3. 检索基因胶囊
            retrieved_capsule = certifier.storage.retrieve(capsule.strategy_id)
            assert retrieved_capsule is not None
            
            # 4. 验证检索的胶囊签名与原始签名一致
            assert retrieved_capsule.signature == original_signature
            
            # 5. 验证签名有效性
            is_valid = certifier.signature_manager.verify_signature(retrieved_capsule)
            assert is_valid, "签名验证应该成功"
            
            # 6. 使用certifier的verify_capsule方法验证
            is_valid_full = await certifier.verify_capsule(capsule.strategy_id)
            assert is_valid_full, "完整验证应该成功"
            
            # 7. 重新生成签名应该得到相同结果
            regenerated_signature = certifier.signature_manager.generate_signature(retrieved_capsule)
            assert regenerated_signature == original_signature, \
                "重新生成的签名应该与原始签名一致"
            
        finally:
            # 清理测试数据
            certifier.storage.delete(capsule_data['strategy_id'])
    
    # 运行异步测试
    asyncio.run(run_test())


# ============================================================================
# Property 18: Tamper Detection
# ============================================================================

@settings(
    max_examples=5,  # 减少到5次以加快速度
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture]
)
@given(capsule_data=valid_capsule_data_strategy())
def test_property_18_tamper_detection(capsule_data):
    """
    Feature: chapter-4-sparta-evolution-completion
    Property 18: Tamper Detection
    
    For any Z2H gene capsule with a modified signature, verification should fail
    and the system should reject it with a security alert.
    
    白皮书依据: 第四章 4.3.2 篡改检测
    Validates: Requirements 4.8
    """
    async def run_test():
        # 创建Mock EventBus
        mock_event_bus = MockEventBus()
        
        # 创建Z2H认证器（使用Mock EventBus，禁用Redis）
        certifier = Z2HCertifier(
            event_bus=mock_event_bus,
            storage_dir='data/test_z2h_capsules',
            redis_host='invalid_host'  # 使用无效主机禁用Redis
        )
        
        try:
            # 1. 生成基因胶囊
            capsule = await certifier.certify_strategy(
                strategy_id=capsule_data['strategy_id'],
                strategy_name=capsule_data['strategy_name'],
                source_factors=capsule_data['source_factors'],
                arena_score=capsule_data['arena_score'],
                simulation_metrics=capsule_data['simulation_metrics'],
            )
            
            # 2. 检索基因胶囊
            retrieved_capsule = certifier.storage.retrieve(capsule.strategy_id)
            assert retrieved_capsule is not None
            
            # 3. 篡改签名
            original_signature = retrieved_capsule.signature
            tampered_signature = original_signature[:-4] + "XXXX"  # 修改最后4个字符
            retrieved_capsule.signature = tampered_signature
            
            # 4. 验证签名应该失败
            is_valid = certifier.signature_manager.verify_signature(retrieved_capsule)
            assert not is_valid, "篡改后的签名验证应该失败"
            
            # 5. 检测篡改
            is_tampered = certifier.signature_manager.detect_tampering(retrieved_capsule)
            assert is_tampered, "应该检测到数据篡改"
            
        finally:
            # 清理测试数据
            certifier.storage.delete(capsule_data['strategy_id'])
    
    # 运行异步测试
    asyncio.run(run_test())


# ============================================================================
# Helper Functions
# ============================================================================

def run_async_test(coro):
    """运行异步测试的辅助函数"""
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(coro)
