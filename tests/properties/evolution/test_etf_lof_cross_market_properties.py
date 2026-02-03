"""
ETF/LOF因子挖掘器跨市场测试属性测试

白皮书依据: 第四章 4.1.17-4.1.18 ETF/LOF因子挖掘器
铁律7依据: 测试覆盖率要求 100%

Properties tested:
- Property 12: Cross-Market Performance Divergence Detection
- Property 13: Cross-Market IC Correlation Calculation

**Feature: etf-lof-factor-miners**
**Validates: Requirements 6.7, 6.8**
"""

import pytest
import pandas as pd
import numpy as np
from hypothesis import given, strategies as st, settings, assume
from typing import Dict

from src.evolution.etf_lof.cross_market_alignment import (
    MarketType,
    calculate_cross_market_ic_correlation,
    detect_market_specific_factors
)


# ============================================================================
# Property 12: Cross-Market Performance Divergence Detection
# ============================================================================

class TestProperty12CrossMarketDivergenceDetection:
    """Property 12: 跨市场表现差异检测
    
    白皮书依据: 第四章 4.2.1 - 跨市场因子验证
    
    **Property 12: Cross-Market Performance Divergence Detection**
    
    **Validates: Requirements 6.7, 6.9**
    
    该属性验证系统能够正确检测因子在不同市场的表现差异：
    1. 当IC标准差超过阈值时，标记为市场特定因子
    2. 当跨市场相关性低于阈值时，标记为市场特定因子
    3. 返回完整的诊断指标
    """
    
    @given(
        ic_a_stock=st.floats(min_value=-0.2, max_value=0.2),
        ic_hk_stock=st.floats(min_value=-0.2, max_value=0.2),
        ic_us_stock=st.floats(min_value=-0.2, max_value=0.2)
    )
    @settings(max_examples=100, deadline=None)
    def test_divergence_detection_with_random_ic(
        self,
        ic_a_stock: float,
        ic_hk_stock: float,
        ic_us_stock: float
    ):
        """测试随机IC值的差异检测
        
        验证:
        1. 函数能处理任意有效的IC值
        2. 返回值格式正确
        3. 诊断指标完整
        """
        # 过滤掉所有IC都接近0的情况（无意义）
        assume(max(abs(ic_a_stock), abs(ic_hk_stock), abs(ic_us_stock)) > 0.01)
        
        ic_dict = {
            MarketType.A_STOCK: ic_a_stock,
            MarketType.HK_STOCK: ic_hk_stock,
            MarketType.US_STOCK: ic_us_stock
        }
        
        # 执行检测
        is_specific, metrics = detect_market_specific_factors(ic_dict)
        
        # 验证返回值类型
        assert isinstance(is_specific, bool)
        assert isinstance(metrics, dict)
        
        # 验证必需的metrics字段
        required_fields = [
            'ic_mean', 'ic_std', 'ic_min', 'ic_max',
            'avg_correlation', 'min_correlation',
            'ic_std_threshold', 'min_correlation_threshold',
            'std_exceeded', 'correlation_below_threshold'
        ]
        for field in required_fields:
            assert field in metrics, f"缺少metrics字段: {field}"
        
        # 验证统计量的合理性（使用容差处理浮点精度问题）
        assert metrics['ic_min'] - 1e-10 <= metrics['ic_mean'] <= metrics['ic_max'] + 1e-10
        assert metrics['ic_std'] >= 0
        assert -1.0 <= metrics['avg_correlation'] <= 1.0
        assert -1.0 <= metrics['min_correlation'] <= 1.0
    
    def test_high_divergence_detected(self):
        """测试高差异因子被正确检测
        
        验证:
        1. IC标准差大的因子被标记为市场特定
        2. 诊断指标正确反映差异程度
        """
        # 构造高差异的IC值
        ic_dict = {
            MarketType.A_STOCK: 0.15,   # 高IC
            MarketType.HK_STOCK: 0.02,  # 低IC
            MarketType.US_STOCK: 0.01   # 低IC
        }
        
        is_specific, metrics = detect_market_specific_factors(
            ic_dict,
            ic_std_threshold=0.05
        )
        
        # 验证被标记为市场特定因子
        assert is_specific
        
        # 验证IC标准差超过阈值
        assert metrics['ic_std'] > 0.05
        assert metrics['std_exceeded']
    
    def test_low_divergence_not_detected(self):
        """测试低差异因子不被标记
        
        验证:
        1. IC值接近的因子不被标记为市场特定
        2. 诊断指标正确反映一致性
        """
        # 构造低差异的IC值
        ic_dict = {
            MarketType.A_STOCK: 0.08,
            MarketType.HK_STOCK: 0.07,
            MarketType.US_STOCK: 0.09
        }
        
        is_specific, metrics = detect_market_specific_factors(
            ic_dict,
            ic_std_threshold=0.05,
            min_correlation=0.3
        )
        
        # 验证不被标记为市场特定因子
        assert not is_specific
        
        # 验证IC标准差未超过阈值
        assert metrics['ic_std'] <= 0.05
        assert not metrics['std_exceeded']
    
    @given(
        threshold=st.floats(min_value=0.01, max_value=0.10)
    )
    @settings(max_examples=50, deadline=None)
    def test_threshold_sensitivity(self, threshold: float):
        """测试阈值敏感性
        
        验证:
        1. 不同阈值产生不同的检测结果
        2. 阈值被正确记录在metrics中
        """
        # 固定的IC值
        ic_dict = {
            MarketType.A_STOCK: 0.10,
            MarketType.HK_STOCK: 0.05,
            MarketType.US_STOCK: 0.03
        }
        
        is_specific, metrics = detect_market_specific_factors(
            ic_dict,
            ic_std_threshold=threshold
        )
        
        # 验证阈值被正确记录
        assert metrics['ic_std_threshold'] == threshold
        
        # 验证检测逻辑一致性
        if metrics['ic_std'] > threshold:
            assert metrics['std_exceeded']
        else:
            assert not metrics['std_exceeded']


# ============================================================================
# Property 13: Cross-Market IC Correlation Calculation
# ============================================================================

class TestProperty13CrossMarketICCorrelation:
    """Property 13: 跨市场IC相关性计算
    
    白皮书依据: 第四章 4.2.1 - 跨市场IC相关性分析
    
    **Property 13: Cross-Market IC Correlation Calculation**
    
    **Validates: Requirements 6.8**
    
    该属性验证跨市场IC相关性矩阵的正确性：
    1. 相关性矩阵是对称的
    2. 对角线元素为1.0
    3. 非对角线元素在[-1, 1]范围内
    4. 相似IC值产生高相关性
    """
    
    @given(
        ic_a_stock=st.floats(min_value=-0.2, max_value=0.2),
        ic_hk_stock=st.floats(min_value=-0.2, max_value=0.2)
    )
    @settings(max_examples=100, deadline=None)
    def test_correlation_matrix_properties(
        self,
        ic_a_stock: float,
        ic_hk_stock: float
    ):
        """测试相关性矩阵的数学属性
        
        验证:
        1. 矩阵是对称的
        2. 对角线为1.0
        3. 所有元素在[-1, 1]范围内
        """
        ic_dict = {
            MarketType.A_STOCK: ic_a_stock,
            MarketType.HK_STOCK: ic_hk_stock
        }
        
        corr_matrix = calculate_cross_market_ic_correlation(ic_dict)
        
        # 验证矩阵形状
        assert corr_matrix.shape == (2, 2)
        
        # 验证对称性
        assert np.allclose(corr_matrix.values, corr_matrix.values.T)
        
        # 验证对角线为1.0
        assert np.allclose(np.diag(corr_matrix.values), 1.0)
        
        # 验证所有元素在[-1, 1]范围内
        assert np.all(corr_matrix.values >= -1.0)
        assert np.all(corr_matrix.values <= 1.0)
    
    def test_identical_ic_high_correlation(self):
        """测试相同IC值产生高相关性
        
        验证:
        1. 完全相同的IC值产生1.0相关性
        2. 非对角线元素接近1.0
        """
        # 相同的IC值
        ic_value = 0.08
        ic_dict = {
            MarketType.A_STOCK: ic_value,
            MarketType.HK_STOCK: ic_value,
            MarketType.US_STOCK: ic_value
        }
        
        corr_matrix = calculate_cross_market_ic_correlation(ic_dict)
        
        # 所有非对角线元素应该接近1.0
        n = len(ic_dict)
        for i in range(n):
            for j in range(n):
                if i != j:
                    assert corr_matrix.iloc[i, j] >= 0.95
    
    def test_opposite_ic_low_correlation(self):
        """测试相反IC值产生低相关性
        
        验证:
        1. 差异大的IC值产生低相关性
        2. 相关性随IC差异增大而降低
        """
        # 差异大的IC值
        ic_dict = {
            MarketType.A_STOCK: 0.15,
            MarketType.HK_STOCK: 0.01,
            MarketType.US_STOCK: 0.02
        }
        
        corr_matrix = calculate_cross_market_ic_correlation(ic_dict)
        
        # A股与其他市场的相关性应该较低
        assert corr_matrix.loc[MarketType.A_STOCK.value, MarketType.HK_STOCK.value] < 0.9
        assert corr_matrix.loc[MarketType.A_STOCK.value, MarketType.US_STOCK.value] < 0.9
    
    @given(
        n_markets=st.integers(min_value=2, max_value=3)  # 只有3个市场类型
    )
    @settings(max_examples=20, deadline=None)
    def test_correlation_matrix_size(self, n_markets: int):
        """测试不同市场数量的相关性矩阵
        
        验证:
        1. 矩阵大小与市场数量匹配
        2. 矩阵属性在不同规模下保持
        """
        # 生成n个市场的IC值
        markets = [MarketType.A_STOCK, MarketType.HK_STOCK, MarketType.US_STOCK]
        ic_dict = {
            markets[i]: 0.05 + i * 0.01
            for i in range(n_markets)
        }
        
        corr_matrix = calculate_cross_market_ic_correlation(ic_dict)
        
        # 验证矩阵大小
        assert corr_matrix.shape == (n_markets, n_markets)
        
        # 验证对称性
        assert np.allclose(corr_matrix.values, corr_matrix.values.T)
        
        # 验证对角线
        assert np.allclose(np.diag(corr_matrix.values), 1.0)
    
    def test_zero_ic_values(self):
        """测试零IC值的处理
        
        验证:
        1. 零IC值不导致除零错误
        2. 相关性矩阵仍然有效
        """
        ic_dict = {
            MarketType.A_STOCK: 0.0,
            MarketType.HK_STOCK: 0.0
        }
        
        corr_matrix = calculate_cross_market_ic_correlation(ic_dict)
        
        # 验证矩阵有效
        assert corr_matrix.shape == (2, 2)
        assert np.allclose(np.diag(corr_matrix.values), 1.0)
        
        # 当两个IC都为0时，相关性应该为1.0
        assert corr_matrix.iloc[0, 1] == 1.0
    
    def test_negative_ic_values(self):
        """测试负IC值的处理
        
        验证:
        1. 负IC值被正确处理
        2. 相关性计算考虑符号
        """
        ic_dict = {
            MarketType.A_STOCK: -0.08,
            MarketType.HK_STOCK: -0.07,
            MarketType.US_STOCK: 0.06
        }
        
        corr_matrix = calculate_cross_market_ic_correlation(ic_dict)
        
        # 验证矩阵有效
        assert corr_matrix.shape == (3, 3)
        assert np.all(corr_matrix.values >= -1.0)
        assert np.all(corr_matrix.values <= 1.0)
        
        # 负IC值之间应该有较高相关性
        assert corr_matrix.loc[MarketType.A_STOCK.value, MarketType.HK_STOCK.value] > 0.8


# ============================================================================
# 边界条件和错误处理测试
# ============================================================================

class TestCrossMarketPropertiesBoundaryConditions:
    """跨市场属性测试的边界条件
    
    验证:
    1. 单市场输入被正确拒绝
    2. 无效IC值被正确拒绝
    3. 极端IC值被正确处理
    """
    
    def test_single_market_rejected(self):
        """测试单市场输入被拒绝"""
        ic_dict = {
            MarketType.A_STOCK: 0.08
        }
        
        with pytest.raises(ValueError, match="需要至少2个市场"):
            calculate_cross_market_ic_correlation(ic_dict)
        
        with pytest.raises(ValueError, match="需要至少2个市场"):
            detect_market_specific_factors(ic_dict)
    
    def test_nan_ic_rejected(self):
        """测试NaN IC值被拒绝"""
        ic_dict = {
            MarketType.A_STOCK: 0.08,
            MarketType.HK_STOCK: float('nan')
        }
        
        with pytest.raises(ValueError, match="IC值无效"):
            calculate_cross_market_ic_correlation(ic_dict)
    
    def test_infinite_ic_rejected(self):
        """测试无穷大IC值被拒绝"""
        ic_dict = {
            MarketType.A_STOCK: 0.08,
            MarketType.HK_STOCK: float('inf')
        }
        
        with pytest.raises(ValueError, match="IC值无效"):
            calculate_cross_market_ic_correlation(ic_dict)
    
    def test_extreme_ic_values(self):
        """测试极端IC值的处理
        
        验证:
        1. 极端IC值不导致数值错误
        2. 相关性计算仍然有效
        """
        ic_dict = {
            MarketType.A_STOCK: 0.20,   # 极高IC
            MarketType.HK_STOCK: -0.20,  # 极低IC
            MarketType.US_STOCK: 0.0     # 零IC
        }
        
        # 应该能正常计算
        corr_matrix = calculate_cross_market_ic_correlation(ic_dict)
        is_specific, metrics = detect_market_specific_factors(ic_dict)
        
        # 验证结果有效
        assert corr_matrix.shape == (3, 3)
        assert isinstance(is_specific, bool)
        assert metrics['ic_std'] > 0
