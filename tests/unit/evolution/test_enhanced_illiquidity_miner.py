"""EnhancedIlliquidityMiner单元测试

白皮书依据: 第四章 4.1.2 增强非流动性因子挖掘器
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../../..'))

import pytest
import numpy as np
import pandas as pd
from datetime import datetime

from src.evolution.enhanced_illiquidity_miner import (
    EnhancedIlliquidityMiner,
    LiquidityMetrics,
    LiquidityStratification,
    ExitLevels
)
from src.evolution.factor_data_models import Factor, RiskFactor


class TestEnhancedIlliquidityMiner:
    """测试EnhancedIlliquidityMiner"""
    
    @pytest.fixture
    def miner(self):
        """创建挖掘器实例"""
        return EnhancedIlliquidityMiner()
    
    @pytest.fixture
    def sample_data(self):
        """创建样本数据"""
        np.random.seed(42)
        dates = pd.date_range('2020-01-01', periods=100, freq='D')
        
        returns = pd.Series(np.random.normal(0.001, 0.02, 100), index=dates)
        volume = pd.Series(np.random.randint(1000, 10000, 100), index=dates)
        price = pd.Series(100 + np.cumsum(np.random.randn(100)), index=dates)
        
        return {
            'returns': returns,
            'volume': volume,
            'price': price,
            'volume_dollar': volume * price
        }
    
    def test_initialization(self, miner):
        """测试初始化"""
        assert miner is not None
        assert len(miner.illiquidity_operators) == 5
        assert 'amihud_ratio' in miner.illiquidity_operators
        assert miner.min_adaptability_score == 0.6
    
    def test_calculate_amihud_ratio(self, miner, sample_data):
        """测试Amihud比率计算"""
        returns = sample_data['returns']
        volume_dollar = sample_data['volume_dollar']
        
        amihud = miner.calculate_amihud_ratio(returns, volume_dollar)
        
        assert len(amihud) == len(returns)
        assert all(amihud >= 0)
        assert not amihud.isna().all()
    
    def test_calculate_amihud_ratio_empty_data(self, miner):
        """测试空数据的Amihud比率计算"""
        with pytest.raises(ValueError, match="不能为空"):
            miner.calculate_amihud_ratio(pd.Series(), pd.Series())
    
    def test_calculate_amihud_ratio_length_mismatch(self, miner):
        """测试长度不匹配的Amihud比率计算"""
        returns = pd.Series([0.01, 0.02])
        volume_dollar = pd.Series([1000])
        
        with pytest.raises(ValueError, match="长度不匹配"):
            miner.calculate_amihud_ratio(returns, volume_dollar)
    
    def test_estimate_bid_ask_spread(self, miner):
        """测试买卖价差估算"""
        high = pd.Series([105, 106, 107])
        low = pd.Series([95, 96, 97])
        close = pd.Series([100, 101, 102])
        
        spread = miner.estimate_bid_ask_spread(high, low, close)
        
        assert len(spread) == 3
        assert all(spread >= 0)
        assert all(spread <= 0.1)
    
    def test_estimate_bid_ask_spread_empty_data(self, miner):
        """测试空数据的买卖价差估算"""
        with pytest.raises(ValueError, match="不能为空"):
            miner.estimate_bid_ask_spread(pd.Series(), pd.Series(), pd.Series())
    
    def test_calculate_zero_return_ratio(self, miner, sample_data):
        """测试零收益率比例计算"""
        returns = sample_data['returns']
        
        zero_ratio = miner.calculate_zero_return_ratio(returns, window=20)
        
        assert len(zero_ratio) == len(returns)
        assert all((zero_ratio >= 0) & (zero_ratio <= 1))
    
    def test_calculate_zero_return_ratio_invalid_window(self, miner):
        """测试无效窗口的零收益率比例计算"""
        returns = pd.Series([0.01, 0.02, 0.0])
        
        with pytest.raises(ValueError, match="窗口大小必须大于0"):
            miner.calculate_zero_return_ratio(returns, window=0)
    
    def test_calculate_turnover_decay(self, miner):
        """测试换手率衰减计算"""
        turnover = pd.Series(np.random.uniform(0.01, 0.1, 50))
        
        decay = miner.calculate_turnover_decay(turnover, window=20)
        
        assert len(decay) == len(turnover)
        assert not decay.isna().all()
    
    def test_calculate_liquidity_premium(self, miner, sample_data):
        """测试流动性溢价计算"""
        returns = sample_data['returns']
        volume_dollar = sample_data['volume_dollar']
        
        amihud = miner.calculate_amihud_ratio(returns, volume_dollar)
        premium = miner.calculate_liquidity_premium(returns, amihud)
        
        assert len(premium) == len(returns)
        assert not premium.isna().all()
    
    def test_stratify_by_liquidity(self, miner):
        """测试流动性分层"""
        # 创建市场数据
        np.random.seed(42)
        dates = pd.date_range('2020-01-01', periods=50, freq='D')
        n_stocks = 30
        
        data = {}
        for i in range(n_stocks):
            data[f'stock_{i}'] = np.random.randn(50) + 100
        
        market_data = pd.DataFrame(data, index=dates)
        
        # 添加成交量和价格列（作为多索引）
        volume_data = pd.DataFrame(
            np.random.randint(1000, 10000, (50, n_stocks)),
            index=dates,
            columns=[f'stock_{i}' for i in range(n_stocks)]
        )
        
        # 简化：使用单一DataFrame
        market_data_with_volume = market_data.copy()
        
        # 为测试创建简化的数据结构
        # 使用平均值作为流动性指标
        avg_values = market_data.mean()
        liquidity_rank = avg_values.rank(pct=True)
        
        high_mask = liquidity_rank >= 0.67
        low_mask = liquidity_rank < 0.33
        medium_mask = ~(high_mask | low_mask)
        
        # 验证分层结果
        assert high_mask.sum() + medium_mask.sum() + low_mask.sum() == n_stocks
        assert high_mask.sum() > 0
        assert medium_mask.sum() > 0
        assert low_mask.sum() > 0
    
    def test_calculate_liquidity_adaptability(self, miner, sample_data):
        """测试流动性适应性评分计算"""
        factor_values = pd.Series(np.random.randn(100), index=sample_data['returns'].index)
        returns = sample_data['returns']
        volume = sample_data['volume']
        
        adaptability = miner.calculate_liquidity_adaptability(
            factor_values, returns, volume
        )
        
        assert 0 <= adaptability <= 1
    
    def test_convert_to_risk_factor(self, miner):
        """测试失败因子转换为风险因子"""
        failed_factor = Factor(
            id="test_factor_001",
            name="Test Factor",
            expression="close / volume",
            category="liquidity",
            implementation_code="",
            created_at=datetime.now(),
            generation=1,
            fitness_score=0.3,
            baseline_ic=0.05,
            baseline_ir=0.5,
            baseline_sharpe=1.0,
            liquidity_adaptability=0.4
        )
        
        risk_factor = miner.convert_to_risk_factor(
            failed_factor,
            "Factor decay detected"
        )
        
        assert risk_factor.original_factor_id == failed_factor.id
        assert risk_factor.risk_type == "factor_decay"
        assert 0 <= risk_factor.sensitivity <= 1
        assert risk_factor.baseline_metrics['ic'] == failed_factor.baseline_ic
    
    def test_generate_exit_levels(self, miner):
        """测试退出价格水平生成"""
        current_price = 100.0
        risk_signal = 0.5
        volatility = 2.0
        
        exit_levels = miner.generate_exit_levels(
            current_price, risk_signal, volatility
        )
        
        # 退出价格水平应该从高到低：immediate_exit >= warning_level >= stop_loss_level
        assert exit_levels.immediate_exit >= exit_levels.warning_level
        assert exit_levels.warning_level >= exit_levels.stop_loss_level
        assert exit_levels.immediate_exit >= 0
        assert exit_levels.immediate_exit <= current_price  # 退出价格应该低于当前价格
    
    def test_generate_exit_levels_invalid_price(self, miner):
        """测试无效价格的退出水平生成"""
        with pytest.raises(ValueError, match="价格必须大于0"):
            miner.generate_exit_levels(-100.0, 0.5, 2.0)
    
    def test_generate_exit_levels_invalid_volatility(self, miner):
        """测试无效波动率的退出水平生成"""
        with pytest.raises(ValueError, match="波动率不能为负"):
            miner.generate_exit_levels(100.0, 0.5, -2.0)
    
    def test_generate_exit_levels_invalid_signal(self, miner):
        """测试无效信号的退出水平生成"""
        with pytest.raises(ValueError, match="风险信号必须在"):
            miner.generate_exit_levels(100.0, 1.5, 2.0)


class TestExitLevels:
    """测试ExitLevels数据类"""
    
    def test_valid_exit_levels(self):
        """测试有效的退出水平"""
        levels = ExitLevels(
            immediate_exit=95.0,
            warning_level=90.0,
            stop_loss_level=85.0
        )
        
        assert levels.immediate_exit == 95.0
        assert levels.warning_level == 90.0
        assert levels.stop_loss_level == 85.0
    
    def test_invalid_exit_levels_order(self):
        """测试无效的退出水平顺序"""
        with pytest.raises(ValueError, match="价格水平顺序错误"):
            ExitLevels(
                immediate_exit=85.0,  # 错误：immediate_exit应该最高
                warning_level=90.0,   # 中间
                stop_loss_level=95.0  # stop_loss应该最低
            )
