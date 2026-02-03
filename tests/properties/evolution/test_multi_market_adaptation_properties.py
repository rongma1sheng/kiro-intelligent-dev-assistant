"""多市场因子适配引擎属性测试

白皮书依据: 第四章 4.2.5 多市场因子适配

测试多市场因子适配引擎的核心属性：
- Property 33: Cross-Market Testing Coverage
- Property 34: Market Adaptation Feasibility
- Property 35: Market-Specific Version Generation
- Property 36: Cross-Market Performance Tracking
"""

import pytest
import asyncio
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from hypothesis import given, strategies as st, settings, HealthCheck
from typing import Dict, List, Any

from src.evolution.multi_market_adaptation import (
    MultiMarketAdaptationEngine,
    MarketType,
    AdaptationStrategy,
    CrossMarketTestResult,
    AdaptedFactor,
    GlobalFactor,
    MarketCharacteristics,
    MARKET_CHARACTERISTICS
)


# ============================================================================
# 测试数据生成策略
# ============================================================================

@st.composite
def market_data_strategy(draw, n_stocks: int = 10) -> Dict[MarketType, pd.DataFrame]:
    """生成各市场数据"""
    n_days = draw(st.integers(min_value=20, max_value=50))
    
    market_data = {}
    for market in MarketType:
        dates = pd.date_range(end=datetime.now(), periods=n_days, freq='D')
        symbols = [f"{market.name}_{i:03d}" for i in range(n_stocks)]
        
        data = {}
        for symbol in symbols:
            base_price = draw(st.floats(min_value=10.0, max_value=100.0))
            returns = np.random.normal(0.001, 0.02, n_days)
            prices = base_price * np.cumprod(1 + returns)
            data[symbol] = prices
        
        market_data[market] = pd.DataFrame(data, index=dates)
    
    return market_data


@st.composite
def returns_data_strategy(draw, market_data: Dict[MarketType, pd.DataFrame]) -> Dict[MarketType, pd.DataFrame]:
    """生成各市场收益数据"""
    returns_data = {}
    
    for market, data in market_data.items():
        if len(data) > 1:
            returns = data.pct_change().dropna()
        else:
            returns = pd.DataFrame(0.0, index=data.index, columns=data.columns)
        returns_data[market] = returns
    
    return returns_data


# ============================================================================
# Property 33: Cross-Market Testing Coverage
# ============================================================================

class TestProperty33CrossMarketTestingCoverage:
    """Property 33: 跨市场测试覆盖
    
    **Validates: Requirements 9.1, 9.4**
    
    验证因子能够在所有4个市场进行测试，
    并正确识别全球因子（3+市场有效）。
    """
    
    @pytest.fixture
    def engine(self):
        """创建多市场适配引擎"""
        return MultiMarketAdaptationEngine()
    
    def test_all_four_markets_tested(self, engine):
        """测试所有4个市场都被测试
        
        **Validates: Requirements 9.1**
        """
        # 创建测试数据
        n_days = 30
        n_stocks = 10
        
        market_data = {}
        returns_data = {}
        
        for market in MarketType:
            dates = pd.date_range(end=datetime.now(), periods=n_days, freq='D')
            symbols = [f"{market.name}_{i:03d}" for i in range(n_stocks)]
            
            data = pd.DataFrame(
                np.random.uniform(10, 100, (n_days, n_stocks)),
                index=dates,
                columns=symbols
            )
            market_data[market] = data
            returns_data[market] = data.pct_change().dropna()
        
        # 执行跨市场测试
        results = asyncio.run(engine.test_factor_across_markets(
            factor_id="test_factor",
            factor_expression="close / delay(close, 1) - 1",
            market_data=market_data,
            returns_data=returns_data
        ))
        
        # 验证：所有4个市场都有结果
        assert len(results) == 4
        for market in MarketType:
            assert market in results
    
    def test_global_factor_identification(self, engine):
        """测试全球因子识别
        
        **Validates: Requirements 9.4**
        """
        # 模拟跨市场测试结果（3个市场有效）
        engine.cross_market_results["global_factor"] = {
            MarketType.A_STOCK: CrossMarketTestResult(
                factor_id="global_factor",
                market=MarketType.A_STOCK,
                ic=0.05,
                ir=1.5,
                sharpe=1.2,
                max_drawdown=0.1,
                win_rate=0.55,
                is_effective=True
            ),
            MarketType.US_STOCK: CrossMarketTestResult(
                factor_id="global_factor",
                market=MarketType.US_STOCK,
                ic=0.04,
                ir=1.3,
                sharpe=1.0,
                max_drawdown=0.12,
                win_rate=0.52,
                is_effective=True
            ),
            MarketType.HK_STOCK: CrossMarketTestResult(
                factor_id="global_factor",
                market=MarketType.HK_STOCK,
                ic=0.03,
                ir=1.0,
                sharpe=0.8,
                max_drawdown=0.15,
                win_rate=0.50,
                is_effective=True
            ),
            MarketType.CRYPTO: CrossMarketTestResult(
                factor_id="global_factor",
                market=MarketType.CRYPTO,
                ic=0.01,
                ir=0.3,
                sharpe=0.3,
                max_drawdown=0.25,
                win_rate=0.45,
                is_effective=False
            )
        }
        
        # 识别全球因子
        global_factor = engine.identify_global_factors(
            factor_id="global_factor",
            factor_name="全球动量因子",
            factor_expression="close / delay(close, 20) - 1"
        )
        
        # 验证：被识别为全球因子
        assert global_factor is not None
        assert global_factor.is_global()
        assert len(global_factor.effective_markets) >= 3
    
    def test_non_global_factor_not_identified(self, engine):
        """测试非全球因子不被识别
        
        **Validates: Requirements 9.4**
        """
        # 模拟跨市场测试结果（仅2个市场有效）
        engine.cross_market_results["local_factor"] = {
            MarketType.A_STOCK: CrossMarketTestResult(
                factor_id="local_factor",
                market=MarketType.A_STOCK,
                ic=0.05,
                ir=1.5,
                sharpe=1.2,
                max_drawdown=0.1,
                win_rate=0.55,
                is_effective=True
            ),
            MarketType.US_STOCK: CrossMarketTestResult(
                factor_id="local_factor",
                market=MarketType.US_STOCK,
                ic=0.04,
                ir=1.3,
                sharpe=1.0,
                max_drawdown=0.12,
                win_rate=0.52,
                is_effective=True
            ),
            MarketType.HK_STOCK: CrossMarketTestResult(
                factor_id="local_factor",
                market=MarketType.HK_STOCK,
                ic=0.01,
                ir=0.3,
                sharpe=0.3,
                max_drawdown=0.2,
                win_rate=0.48,
                is_effective=False
            ),
            MarketType.CRYPTO: CrossMarketTestResult(
                factor_id="local_factor",
                market=MarketType.CRYPTO,
                ic=0.005,
                ir=0.1,
                sharpe=0.2,
                max_drawdown=0.3,
                win_rate=0.45,
                is_effective=False
            )
        }
        
        # 尝试识别全球因子
        global_factor = engine.identify_global_factors(
            factor_id="local_factor",
            factor_name="本地因子",
            factor_expression="close / delay(close, 5) - 1"
        )
        
        # 验证：不被识别为全球因子
        assert global_factor is None
    
    @settings(
        max_examples=20,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    @given(n_effective=st.integers(min_value=0, max_value=4))
    def test_global_factor_threshold(self, engine, n_effective):
        """测试全球因子阈值
        
        **Validates: Requirements 9.4**
        """
        # 创建测试结果
        markets = list(MarketType)
        results = {}
        
        for i, market in enumerate(markets):
            is_effective = i < n_effective
            results[market] = CrossMarketTestResult(
                factor_id="test_factor",
                market=market,
                ic=0.05 if is_effective else 0.01,
                ir=1.5 if is_effective else 0.3,
                sharpe=1.2 if is_effective else 0.3,
                max_drawdown=0.1,
                win_rate=0.55 if is_effective else 0.45,
                is_effective=is_effective
            )
        
        engine.cross_market_results["test_factor"] = results
        
        global_factor = engine.identify_global_factors(
            factor_id="test_factor",
            factor_name="测试因子",
            factor_expression="test"
        )
        
        # 验证：3+市场有效才是全球因子
        if n_effective >= 3:
            assert global_factor is not None
            assert global_factor.is_global()
        else:
            assert global_factor is None


# ============================================================================
# Property 34: Market Adaptation Feasibility
# ============================================================================

class TestProperty34MarketAdaptationFeasibility:
    """Property 34: 市场适配可行性
    
    **Validates: Requirements 9.2, 9.3**
    
    验证因子适配的可行性得分计算正确，
    且得分 > 0.5 才能部署到目标市场。
    """
    
    @pytest.fixture
    def engine(self):
        """创建引擎"""
        return MultiMarketAdaptationEngine()
    
    @settings(
        max_examples=50,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    @given(
        source_market=st.sampled_from(list(MarketType)),
        target_market=st.sampled_from(list(MarketType))
    )
    def test_feasibility_score_in_valid_range(self, engine, source_market, target_market):
        """测试可行性得分在有效范围内
        
        **Validates: Requirements 9.3**
        """
        adapted = asyncio.run(engine.adapt_factor_for_market(
            factor_id="test_factor",
            factor_expression="close / delay(close, 1) - 1",
            target_market=target_market,
            source_market=source_market
        ))
        
        # 验证：可行性得分在 [0, 1] 范围内
        assert 0.0 <= adapted.feasibility_score <= 1.0
    
    def test_same_market_high_feasibility(self, engine):
        """测试同市场适配高可行性
        
        **Validates: Requirements 9.3**
        """
        adapted = asyncio.run(engine.adapt_factor_for_market(
            factor_id="test_factor",
            factor_expression="close / delay(close, 1) - 1",
            target_market=MarketType.A_STOCK,
            source_market=MarketType.A_STOCK
        ))
        
        # 验证：同市场适配可行性最高
        assert adapted.feasibility_score >= 0.8
    
    def test_different_market_lower_feasibility(self, engine):
        """测试不同市场适配较低可行性
        
        **Validates: Requirements 9.3**
        """
        # A股到加密货币（差异最大）
        adapted = asyncio.run(engine.adapt_factor_for_market(
            factor_id="test_factor",
            factor_expression="close / delay(close, 1) - 1",
            target_market=MarketType.CRYPTO,
            source_market=MarketType.A_STOCK
        ))
        
        # 验证：不同市场适配可行性较低
        assert adapted.feasibility_score < 0.9
    
    def test_adaptation_strategies_recorded(self, engine):
        """测试适配策略被记录
        
        **Validates: Requirements 9.2**
        """
        adapted = asyncio.run(engine.adapt_factor_for_market(
            factor_id="test_factor",
            factor_expression="close / delay(close, 1) - 1",
            target_market=MarketType.US_STOCK,
            source_market=MarketType.A_STOCK
        ))
        
        # 验证：有适配策略
        assert len(adapted.adaptation_strategies) > 0
        
        # 验证：策略是有效的枚举值
        for strategy in adapted.adaptation_strategies:
            assert isinstance(strategy, AdaptationStrategy)


# ============================================================================
# Property 35: Market-Specific Version Generation
# ============================================================================

class TestProperty35MarketSpecificVersionGeneration:
    """Property 35: 市场特定版本生成
    
    **Validates: Requirements 9.5, 9.6**
    
    验证能够为每个目标市场生成专门版本，
    并应用数据标准化、参数调整、算子替换等策略。
    """
    
    @pytest.fixture
    def engine(self):
        """创建引擎"""
        return MultiMarketAdaptationEngine()
    
    def test_generate_all_market_versions(self, engine):
        """测试生成所有市场版本
        
        **Validates: Requirements 9.5**
        """
        versions = asyncio.run(engine.generate_market_specific_versions(
            factor_id="momentum",
            factor_expression="close / delay(close, 20) - 1"
        ))
        
        # 验证：为所有市场生成版本
        assert len(versions) == len(MarketType)
        for market in MarketType:
            assert market in versions
    
    def test_generate_selected_market_versions(self, engine):
        """测试生成选定市场版本
        
        **Validates: Requirements 9.5**
        """
        target_markets = [MarketType.A_STOCK, MarketType.US_STOCK]
        
        versions = asyncio.run(engine.generate_market_specific_versions(
            factor_id="momentum",
            factor_expression="close / delay(close, 20) - 1",
            target_markets=target_markets
        ))
        
        # 验证：只为选定市场生成版本
        assert len(versions) == 2
        assert MarketType.A_STOCK in versions
        assert MarketType.US_STOCK in versions
    
    def test_adaptation_strategies_applied(self, engine):
        """测试适配策略被应用
        
        **Validates: Requirements 9.6**
        """
        versions = asyncio.run(engine.generate_market_specific_versions(
            factor_id="test_factor",
            factor_expression="close / delay(close, 1) - 1"
        ))
        
        # 验证：每个版本都有适配策略
        for market, adapted in versions.items():
            # 验证：有适配因子ID
            assert adapted.adapted_factor_id == f"test_factor_{market.name}"
            
            # 验证：有目标市场
            assert adapted.target_market == market
    
    @settings(
        max_examples=20,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    @given(target_market=st.sampled_from(list(MarketType)))
    def test_parameter_adjustments_recorded(self, engine, target_market):
        """测试参数调整被记录
        
        **Validates: Requirements 9.6**
        """
        adapted = asyncio.run(engine.adapt_factor_for_market(
            factor_id="test_factor",
            factor_expression="close / delay(close, 1) - 1",
            target_market=target_market,
            source_market=MarketType.A_STOCK
        ))
        
        # 验证：参数调整是字典
        assert isinstance(adapted.parameter_adjustments, dict)
        
        # 验证：算子替换是字典
        assert isinstance(adapted.operator_substitutions, dict)



# ============================================================================
# Property 36: Cross-Market Performance Tracking
# ============================================================================

class TestProperty36CrossMarketPerformanceTracking:
    """Property 36: 跨市场表现跟踪
    
    **Validates: Requirements 9.7, 9.8**
    
    验证能够跟踪因子在所有部署市场的有效性，
    并识别市场状态不变的因子。
    """
    
    @pytest.fixture
    def engine(self):
        """创建引擎"""
        return MultiMarketAdaptationEngine()
    
    def test_performance_tracking(self, engine):
        """测试表现跟踪
        
        **Validates: Requirements 9.7**
        """
        # 记录多条表现
        for i in range(10):
            engine.track_cross_market_performance(
                factor_id="test_factor",
                market=MarketType.A_STOCK,
                ic=0.05 + np.random.normal(0, 0.01),
                return_rate=0.01 + np.random.normal(0, 0.005),
                hit_rate=0.55 + np.random.normal(0, 0.02)
            )
        
        # 验证：记录被保存
        records = engine.get_factor_market_performance("test_factor")
        assert len(records) == 10
    
    def test_performance_by_market(self, engine):
        """测试按市场获取表现
        
        **Validates: Requirements 9.7**
        """
        # 记录多个市场的表现
        for market in [MarketType.A_STOCK, MarketType.US_STOCK]:
            for i in range(5):
                engine.track_cross_market_performance(
                    factor_id="test_factor",
                    market=market,
                    ic=0.05,
                    return_rate=0.01,
                    hit_rate=0.55
                )
        
        # 验证：按市场筛选
        a_stock_records = engine.get_factor_market_performance(
            "test_factor", MarketType.A_STOCK
        )
        assert len(a_stock_records) == 5
        
        us_stock_records = engine.get_factor_market_performance(
            "test_factor", MarketType.US_STOCK
        )
        assert len(us_stock_records) == 5
    
    def test_regime_invariant_identification(self, engine):
        """测试市场状态不变因子识别
        
        **Validates: Requirements 9.8**
        """
        # 创建IC稳定的测试结果
        engine.cross_market_results["stable_factor"] = {
            MarketType.A_STOCK: CrossMarketTestResult(
                factor_id="stable_factor",
                market=MarketType.A_STOCK,
                ic=0.050,
                ir=1.5,
                sharpe=1.2,
                max_drawdown=0.1,
                win_rate=0.55,
                is_effective=True
            ),
            MarketType.US_STOCK: CrossMarketTestResult(
                factor_id="stable_factor",
                market=MarketType.US_STOCK,
                ic=0.051,
                ir=1.4,
                sharpe=1.1,
                max_drawdown=0.12,
                win_rate=0.54,
                is_effective=True
            ),
            MarketType.HK_STOCK: CrossMarketTestResult(
                factor_id="stable_factor",
                market=MarketType.HK_STOCK,
                ic=0.049,
                ir=1.3,
                sharpe=1.0,
                max_drawdown=0.11,
                win_rate=0.53,
                is_effective=True
            )
        }
        
        global_factor = engine.identify_global_factors(
            factor_id="stable_factor",
            factor_name="稳定因子",
            factor_expression="test"
        )
        
        # 验证：被识别为市场状态不变
        assert global_factor is not None
        assert global_factor.is_regime_invariant
    
    def test_cross_market_summary(self, engine):
        """测试跨市场汇总
        
        **Validates: Requirements 9.7**
        """
        # 创建测试结果
        engine.cross_market_results["summary_factor"] = {
            MarketType.A_STOCK: CrossMarketTestResult(
                factor_id="summary_factor",
                market=MarketType.A_STOCK,
                ic=0.05,
                ir=1.5,
                sharpe=1.2,
                max_drawdown=0.1,
                win_rate=0.55,
                is_effective=True
            ),
            MarketType.US_STOCK: CrossMarketTestResult(
                factor_id="summary_factor",
                market=MarketType.US_STOCK,
                ic=0.04,
                ir=1.3,
                sharpe=1.0,
                max_drawdown=0.12,
                win_rate=0.52,
                is_effective=True
            )
        }
        
        summary = engine.get_cross_market_summary("summary_factor")
        
        # 验证：汇总包含必要信息
        assert "factor_id" in summary
        assert "tested_markets" in summary
        assert "effective_markets" in summary
        assert "avg_ic" in summary
        assert "avg_sharpe" in summary
        assert "is_global_factor" in summary
    
    @settings(
        max_examples=20,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    @given(n_records=st.integers(min_value=1, max_value=100))
    def test_performance_history_limit(self, engine, n_records):
        """测试表现历史限制
        
        **Validates: Requirements 9.7**
        """
        # 记录多条表现
        for i in range(n_records):
            engine.track_cross_market_performance(
                factor_id=f"factor_{i % 5}",
                market=list(MarketType)[i % 4],
                ic=0.05,
                return_rate=0.01,
                hit_rate=0.55
            )
        
        # 验证：历史记录不超过1000条
        assert len(engine.performance_history) <= 1000


# ============================================================================
# 边界条件测试
# ============================================================================

class TestEdgeCases:
    """边界条件测试"""
    
    @pytest.fixture
    def engine(self):
        """创建引擎"""
        return MultiMarketAdaptationEngine()
    
    def test_empty_market_data_raises_error(self, engine):
        """测试空市场数据抛出错误"""
        with pytest.raises(ValueError, match="市场数据不能为空"):
            asyncio.run(engine.test_factor_across_markets(
                factor_id="test",
                factor_expression="test",
                market_data={},
                returns_data={}
            ))
    
    def test_empty_factor_id_raises_error(self, engine):
        """测试空因子ID抛出错误"""
        with pytest.raises(ValueError, match="因子ID不能为空"):
            asyncio.run(engine.adapt_factor_for_market(
                factor_id="",
                factor_expression="test",
                target_market=MarketType.A_STOCK
            ))
    
    def test_no_cross_market_results(self, engine):
        """测试无跨市场结果时的全球因子识别"""
        result = engine.identify_global_factors(
            factor_id="nonexistent",
            factor_name="不存在的因子",
            factor_expression="test"
        )
        
        assert result is None
    
    def test_get_nonexistent_factor_performance(self, engine):
        """测试获取不存在因子的表现"""
        records = engine.get_factor_market_performance("nonexistent")
        assert records == []
    
    def test_get_nonexistent_factor_summary(self, engine):
        """测试获取不存在因子的汇总"""
        summary = engine.get_cross_market_summary("nonexistent")
        assert "error" in summary
    
    def test_get_adaptation_feasibility_not_adapted(self, engine):
        """测试获取未适配因子的可行性"""
        score = engine.get_adaptation_feasibility("nonexistent", MarketType.A_STOCK)
        assert score == 0.0
    
    def test_statistics_empty(self, engine):
        """测试空引擎的统计信息"""
        stats = engine.get_statistics()
        
        assert stats["total_factors_tested"] == 0
        assert stats["global_factors_count"] == 0
        assert stats["adapted_factors_count"] == 0


# ============================================================================
# 市场特征测试
# ============================================================================

class TestMarketCharacteristics:
    """市场特征测试"""
    
    def test_all_markets_have_characteristics(self):
        """测试所有市场都有特征定义"""
        for market in MarketType:
            assert market in MARKET_CHARACTERISTICS
    
    def test_market_characteristics_valid(self):
        """测试市场特征有效"""
        for market, chars in MARKET_CHARACTERISTICS.items():
            assert chars.market_type == market
            assert chars.trading_hours > 0
            assert chars.tick_size > 0
            assert chars.lot_size > 0
            assert chars.t_plus_n >= 0
            assert chars.currency in ["CNY", "USD", "HKD"]
            assert chars.volatility_level in ["低", "中", "高"]
            assert chars.liquidity_level in ["低", "中", "高"]
    
    def test_a_stock_has_limit_up_down(self):
        """测试A股有涨跌停"""
        assert MARKET_CHARACTERISTICS[MarketType.A_STOCK].has_limit_up_down
    
    def test_us_stock_no_limit_up_down(self):
        """测试美股无涨跌停"""
        assert not MARKET_CHARACTERISTICS[MarketType.US_STOCK].has_limit_up_down
    
    def test_crypto_24h_trading(self):
        """测试加密货币24小时交易"""
        assert MARKET_CHARACTERISTICS[MarketType.CRYPTO].trading_hours == 24.0


# ============================================================================
# 数据类测试
# ============================================================================

class TestDataClasses:
    """数据类测试"""
    
    def test_cross_market_test_result_to_dict(self):
        """测试跨市场测试结果转字典"""
        result = CrossMarketTestResult(
            factor_id="test",
            market=MarketType.A_STOCK,
            ic=0.05,
            ir=1.5,
            sharpe=1.2,
            max_drawdown=0.1,
            win_rate=0.55,
            is_effective=True
        )
        
        d = result.to_dict()
        
        assert d["factor_id"] == "test"
        assert d["market"] == "A股"
        assert d["ic"] == 0.05
        assert d["is_effective"] == True
    
    def test_adapted_factor_id_generation(self):
        """测试适配因子ID生成"""
        adapted = AdaptedFactor(
            original_factor_id="momentum",
            target_market=MarketType.US_STOCK,
            adapted_expression="test",
            adaptation_strategies=[],
            feasibility_score=0.8
        )
        
        assert adapted.adapted_factor_id == "momentum_US_STOCK"
    
    def test_global_factor_is_global(self):
        """测试全球因子判断"""
        # 3个市场有效
        global_factor = GlobalFactor(
            factor_id="test",
            name="测试",
            expression="test",
            effective_markets=[MarketType.A_STOCK, MarketType.US_STOCK, MarketType.HK_STOCK],
            market_results={},
            avg_ic=0.05,
            avg_sharpe=1.2,
            is_regime_invariant=True
        )
        
        assert global_factor.is_global()
        assert global_factor.market_count == 3
    
    def test_global_factor_not_global(self):
        """测试非全球因子判断"""
        # 2个市场有效
        local_factor = GlobalFactor(
            factor_id="test",
            name="测试",
            expression="test",
            effective_markets=[MarketType.A_STOCK, MarketType.US_STOCK],
            market_results={},
            avg_ic=0.05,
            avg_sharpe=1.2,
            is_regime_invariant=True
        )
        
        assert not local_factor.is_global()
        assert local_factor.market_count == 2
