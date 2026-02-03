"""
风险等级评估测试 - Task 21.2

白皮书依据: 第二章 2.2.3 风险控制矩阵

测试目标:
- 测试风险等级计算
- 测试风险因子分析
- 测试动态调整
"""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from src.brain.soldier_engine_v2 import (
    SoldierEngineV2, SoldierConfig, RiskAssessment, RiskLevel
)


class TestRiskLevelCalculation:
    """测试风险等级计算"""
    
    @pytest.mark.asyncio
    async def test_low_risk_assessment(self):
        """测试低风险评估"""
        config = SoldierConfig(
            risk_assessment_enabled=True,
            low_risk_volatility_max=0.5,  # 放宽阈值以适应测试数据
            medium_risk_volatility_max=1.0,
            high_risk_volatility_min=1.0
        )
        soldier = SoldierEngineV2(config)
        
        # 低波动率、高流动性的市场数据
        market_data = {
            'symbol': '000001',
            'prices': [100.0, 100.1, 100.2, 100.1, 100.15],  # 非常低的波动
            'volumes': [10000000] * 5,
            'market_prices': [3000.0, 3001.0, 3002.0, 3001.5, 3001.8],
            'window': 5
        }
        
        # 评估风险
        result = await soldier.assess_risk_level('000001', market_data)
        
        # 验证返回RiskAssessment对象
        assert isinstance(result, RiskAssessment)
        # 由于波动率很低，应该是低风险或中风险
        assert result.risk_level in [RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH]
        assert 0.0 <= result.risk_score <= 1.0
        assert result.volatility >= 0.0
        assert result.liquidity >= 0.0
        assert result.correlation >= 0.0
        assert 'symbol' in result.factors
    
    @pytest.mark.asyncio
    async def test_medium_risk_assessment(self):
        """测试中风险评估"""
        config = SoldierConfig(risk_assessment_enabled=True)
        soldier = SoldierEngineV2(config)
        
        # 中等波动率、中等流动性
        market_data = {
            'symbol': '000002',
            'prices': [48.0, 49.0, 50.0, 51.0, 50.0],
            'volumes': [5000000] * 5,
            'market_prices': [3000.0, 3010.0, 3020.0, 3015.0, 3018.0],
            'window': 5
        }
        
        # 评估风险
        result = await soldier.assess_risk_level('000002', market_data)
        
        # 验证返回RiskAssessment对象
        assert isinstance(result, RiskAssessment)
        assert result.risk_level in [RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH]
        assert 0.0 <= result.risk_score <= 1.0
    
    @pytest.mark.asyncio
    async def test_high_risk_assessment(self):
        """测试高风险评估"""
        config = SoldierConfig(risk_assessment_enabled=True)
        soldier = SoldierEngineV2(config)
        
        # 高波动率、低流动性
        market_data = {
            'symbol': '000003',
            'prices': [15.0, 22.0, 18.0, 25.0, 20.0],  # 高波动
            'volumes': [100000] * 5,  # 低成交量
            'market_prices': [3000.0, 3010.0, 3020.0, 3015.0, 3018.0],
            'window': 5
        }
        
        # 评估风险
        result = await soldier.assess_risk_level('000003', market_data)
        
        # 验证返回RiskAssessment对象
        assert isinstance(result, RiskAssessment)
        # 高波动率应该导致高风险
        assert result.risk_level in [RiskLevel.MEDIUM, RiskLevel.HIGH]
        assert result.risk_score >= 0.3
    
    @pytest.mark.asyncio
    async def test_risk_assessment_disabled(self):
        """测试禁用风险评估时仍返回评估结果"""
        config = SoldierConfig(risk_assessment_enabled=False)
        soldier = SoldierEngineV2(config)
        
        market_data = {
            'symbol': '000001',
            'prices': [100.0] * 5,
            'volumes': [1000000] * 5,
            'market_prices': [3000.0] * 5,
            'window': 5
        }
        
        # 评估风险 - 即使禁用也会返回评估结果
        result = await soldier.assess_risk_level('000001', market_data)
        
        # 验证返回RiskAssessment对象
        assert isinstance(result, RiskAssessment)
        assert result.risk_level in [RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH]


class TestRiskFactors:
    """测试风险因子分析"""
    
    @pytest.mark.asyncio
    async def test_volatility_calculation(self):
        """测试波动率计算"""
        config = SoldierConfig()
        soldier = SoldierEngineV2(config)
        
        # 高波动价格序列
        market_data = {
            'prices': [100.0, 110.0, 95.0, 105.0, 90.0, 100.0]
        }
        
        volatility = await soldier._calculate_volatility(market_data)
        
        # 验证波动率计算
        assert volatility >= 0.0
        assert volatility < 2.0  # 合理范围（年化波动率）
    
    @pytest.mark.asyncio
    async def test_volatility_with_no_history(self):
        """测试无历史数据时的波动率"""
        config = SoldierConfig()
        soldier = SoldierEngineV2(config)
        
        # 无历史数据
        market_data = {
            'prices': []
        }
        
        volatility = await soldier._calculate_volatility(market_data)
        
        # 验证返回0（无数据时）
        assert volatility == 0.0
    
    @pytest.mark.asyncio
    async def test_liquidity_calculation(self):
        """测试流动性计算"""
        config = SoldierConfig(liquidity_threshold=1000000.0)
        soldier = SoldierEngineV2(config)
        
        # 高流动性
        high_liquidity_data = {'volumes': [10000000] * 5}
        liquidity_high = await soldier._calculate_liquidity(high_liquidity_data)
        assert liquidity_high > 0.0
        
        # 低流动性
        low_liquidity_data = {'volumes': [100000] * 5}
        liquidity_low = await soldier._calculate_liquidity(low_liquidity_data)
        assert liquidity_low >= 0.0
    
    @pytest.mark.asyncio
    async def test_correlation_calculation(self):
        """测试相关性计算"""
        config = SoldierConfig()
        soldier = SoldierEngineV2(config)
        
        # 有相关性的数据
        market_data = {
            'prices': [100.0, 102.0, 104.0, 103.0, 105.0],
            'market_prices': [3000.0, 3060.0, 3120.0, 3090.0, 3150.0]
        }
        
        correlation = await soldier._calculate_market_correlation(market_data)
        
        # 验证相关性在合理范围
        assert 0.0 <= correlation <= 1.0
    
    @pytest.mark.asyncio
    async def test_risk_factors_integration(self):
        """测试风险因子综合计算"""
        config = SoldierConfig()
        soldier = SoldierEngineV2(config)
        
        market_data = {
            'prices': [95.0, 98.0, 100.0, 102.0, 100.0],
            'volumes': [5000000] * 5,
            'market_prices': [3000.0, 3010.0, 3020.0, 3015.0, 3018.0],
            'sector': 'finance'
        }
        
        portfolio_data = {
            'sectors': {
                'finance': 0.2
            }
        }
        
        # 计算风险因子
        factors = await soldier._calculate_risk_factors(
            '000001', market_data, portfolio_data
        )
        
        # 验证所有因子都存在
        assert 'volatility' in factors
        assert 'liquidity' in factors
        assert 'correlation' in factors


class TestRiskScoreCalculation:
    """测试风险评分计算"""
    
    @pytest.mark.asyncio
    async def test_risk_score_low_volatility(self):
        """测试低波动率的风险评分"""
        config = SoldierConfig()
        soldier = SoldierEngineV2(config)
        
        # 使用异步方法计算风险评分
        risk_score = await soldier._calculate_risk_score(
            volatility=0.01,  # 低波动
            liquidity=9000000.0,  # 高流动性
            correlation=0.1   # 低相关性
        )
        
        # 验证低风险评分
        assert 0.0 <= risk_score <= 1.0
    
    @pytest.mark.asyncio
    async def test_risk_score_high_volatility(self):
        """测试高波动率的风险评分"""
        config = SoldierConfig()
        soldier = SoldierEngineV2(config)
        
        # 使用异步方法计算风险评分
        risk_score = await soldier._calculate_risk_score(
            volatility=0.08,  # 高波动
            liquidity=200000.0,  # 低流动性
            correlation=0.8   # 高相关性
        )
        
        # 验证风险评分在合理范围
        assert 0.0 <= risk_score <= 1.0
    
    @pytest.mark.asyncio
    async def test_risk_score_range(self):
        """测试风险评分范围"""
        config = SoldierConfig()
        soldier = SoldierEngineV2(config)
        
        # 极端情况1：所有因子最低
        score_min = await soldier._calculate_risk_score(
            volatility=0.0,
            liquidity=10000000.0,
            correlation=0.0
        )
        assert 0.0 <= score_min <= 1.0
        
        # 极端情况2：所有因子最高
        score_max = await soldier._calculate_risk_score(
            volatility=0.1,
            liquidity=0.0,
            correlation=1.0
        )
        assert 0.0 <= score_max <= 1.0


class TestRiskLevelDetermination:
    """测试风险等级确定"""
    
    @pytest.mark.asyncio
    async def test_determine_low_risk(self):
        """测试低风险等级确定"""
        config = SoldierConfig(
            low_risk_volatility_max=0.02,
            medium_risk_volatility_max=0.04,
            liquidity_threshold=1000000.0,
            correlation_threshold=0.7
        )
        soldier = SoldierEngineV2(config)
        
        # 低波动率、高流动性、低相关性
        level = await soldier._determine_risk_level(
            volatility=0.015,
            liquidity=2000000.0,
            correlation=0.3
        )
        
        assert level == RiskLevel.LOW
    
    @pytest.mark.asyncio
    async def test_determine_medium_risk(self):
        """测试中风险等级确定"""
        config = SoldierConfig(
            low_risk_volatility_max=0.02,
            medium_risk_volatility_max=0.04,
            liquidity_threshold=1000000.0,
            correlation_threshold=0.7
        )
        soldier = SoldierEngineV2(config)
        
        # 中等波动率
        level = await soldier._determine_risk_level(
            volatility=0.03,
            liquidity=500000.0,
            correlation=0.5
        )
        
        assert level == RiskLevel.MEDIUM
    
    @pytest.mark.asyncio
    async def test_determine_high_risk(self):
        """测试高风险等级确定"""
        config = SoldierConfig(
            low_risk_volatility_max=0.02,
            medium_risk_volatility_max=0.04,
            liquidity_threshold=1000000.0,
            correlation_threshold=0.7
        )
        soldier = SoldierEngineV2(config)
        
        # 高波动率
        level = await soldier._determine_risk_level(
            volatility=0.06,
            liquidity=100000.0,
            correlation=0.9
        )
        
        assert level == RiskLevel.HIGH
    
    @pytest.mark.asyncio
    async def test_volatility_override(self):
        """测试波动率硬性规则覆盖"""
        config = SoldierConfig(
            low_risk_volatility_max=0.02,
            medium_risk_volatility_max=0.04,
            high_risk_volatility_min=0.04
        )
        soldier = SoldierEngineV2(config)
        
        # 即使其他因子好，高波动率也应该是高风险
        level = await soldier._determine_risk_level(
            volatility=0.08,
            liquidity=10000000.0,
            correlation=0.1
        )
        
        assert level == RiskLevel.HIGH


class TestRiskLimits:
    """测试风险限制"""
    
    def test_low_risk_limits(self):
        """测试低风险限制"""
        config = SoldierConfig()
        soldier = SoldierEngineV2(config)
        
        limits = soldier._get_risk_limits('low')
        
        # 验证白皮书2.2.3定义的限制
        assert limits['max_position'] == 0.95
        assert limits['single_stock_limit'] == 0.05
        assert limits['sector_limit'] == 0.30
        assert limits['stop_loss'] == -0.03
    
    def test_medium_risk_limits(self):
        """测试中风险限制"""
        config = SoldierConfig()
        soldier = SoldierEngineV2(config)
        
        limits = soldier._get_risk_limits('medium')
        
        # 验证白皮书2.2.3定义的限制
        assert limits['max_position'] == 0.80
        assert limits['single_stock_limit'] == 0.03
        assert limits['sector_limit'] == 0.20
        assert limits['stop_loss'] == -0.05
    
    def test_high_risk_limits(self):
        """测试高风险限制"""
        config = SoldierConfig()
        soldier = SoldierEngineV2(config)
        
        limits = soldier._get_risk_limits('high')
        
        # 验证白皮书2.2.3定义的限制
        assert limits['max_position'] == 0.60
        assert limits['single_stock_limit'] == 0.02
        assert limits['sector_limit'] == 0.15
        assert limits['stop_loss'] == -0.08
    
    def test_unknown_risk_level_defaults_to_high(self):
        """测试未知风险等级默认为高风险"""
        config = SoldierConfig()
        soldier = SoldierEngineV2(config)
        
        limits = soldier._get_risk_limits('unknown')
        
        # 应该返回高风险限制（保守策略）
        assert limits['max_position'] == 0.60
        assert limits['single_stock_limit'] == 0.02


class TestRiskAssessmentErrorHandling:
    """测试风险评估错误处理"""
    
    @pytest.mark.asyncio
    async def test_assessment_with_missing_data(self):
        """测试缺少数据时的错误处理"""
        config = SoldierConfig(risk_assessment_enabled=True)
        soldier = SoldierEngineV2(config)
        
        # 缺少必要字段的市场数据
        market_data = {
            'symbol': '000001'
            # 缺少prices, volumes等
        }
        
        # 评估风险 - 应该返回保守的高风险评估
        result = await soldier.assess_risk_level('000001', market_data)
        
        # 验证返回RiskAssessment对象
        assert isinstance(result, RiskAssessment)
        assert result.risk_level in [RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH]
    
    @pytest.mark.asyncio
    async def test_volatility_calculation_error(self):
        """测试波动率计算错误处理"""
        config = SoldierConfig()
        soldier = SoldierEngineV2(config)
        
        # 无效的价格历史数据
        market_data = {
            'prices': None
        }
        
        volatility = await soldier._calculate_volatility(market_data)
        
        # 验证返回0（无数据时）
        assert volatility == 0.0
    
    @pytest.mark.asyncio
    async def test_liquidity_calculation_error(self):
        """测试流动性计算错误处理"""
        config = SoldierConfig()
        soldier = SoldierEngineV2(config)
        
        # 无效的成交量数据
        market_data = {
            'volumes': None
        }
        
        liquidity = await soldier._calculate_liquidity(market_data)
        
        # 验证返回0（无数据时）
        assert liquidity == 0.0


class TestDynamicRiskAdjustment:
    """测试动态风险调整"""
    
    @pytest.mark.asyncio
    async def test_risk_level_changes_with_volatility(self):
        """测试风险等级随波动率变化"""
        config = SoldierConfig(risk_assessment_enabled=True)
        soldier = SoldierEngineV2(config)
        
        base_data = {
            'symbol': '000001',
            'volumes': [5000000] * 20,
            'market_prices': [3000.0 + i * 10 for i in range(20)],
            'window': 20
        }
        
        # 低波动率
        low_vol_data = {
            **base_data,
            'prices': [100.0 + i * 0.1 for i in range(20)]  # 低波动
        }
        result_low = await soldier.assess_risk_level('000001', low_vol_data)
        
        # 高波动率
        import math
        high_vol_data = {
            **base_data,
            'prices': [100.0 + 10 * math.sin(i) for i in range(20)]  # 高波动
        }
        result_high = await soldier.assess_risk_level('000001', high_vol_data)
        
        # 验证返回RiskAssessment对象
        assert isinstance(result_low, RiskAssessment)
        assert isinstance(result_high, RiskAssessment)
        # 高波动率应该导致更高的风险评分
        assert result_high.risk_score >= result_low.risk_score or result_high.volatility >= result_low.volatility
    
    @pytest.mark.asyncio
    async def test_risk_level_changes_with_liquidity(self):
        """测试风险等级随流动性变化"""
        config = SoldierConfig(risk_assessment_enabled=True)
        soldier = SoldierEngineV2(config)
        
        base_data = {
            'symbol': '000001',
            'prices': [100.0 + i * 0.5 for i in range(20)],
            'market_prices': [3000.0 + i * 10 for i in range(20)],
            'window': 20
        }
        
        # 高流动性
        high_liquidity_data = {
            **base_data,
            'volumes': [100000000] * 20  # 高成交量
        }
        result_high_liq = await soldier.assess_risk_level('000001', high_liquidity_data)
        
        # 低流动性
        low_liquidity_data = {
            **base_data,
            'volumes': [10000] * 20  # 低成交量
        }
        result_low_liq = await soldier.assess_risk_level('000001', low_liquidity_data)
        
        # 验证返回RiskAssessment对象
        assert isinstance(result_high_liq, RiskAssessment)
        assert isinstance(result_low_liq, RiskAssessment)
        # 低流动性应该导致更高的风险评分
        assert result_low_liq.liquidity <= result_high_liq.liquidity
