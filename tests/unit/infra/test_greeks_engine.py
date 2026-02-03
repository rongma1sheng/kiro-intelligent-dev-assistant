"""
Greeks Engine单元测试

白皮书依据: 第三章 3.3 衍生品管道 - Greeks Engine

测试覆盖:
1. 期权定价测试
2. Delta计算测试
3. Gamma计算测试
4. Vega计算测试
5. Theta计算测试
6. Rho计算测试
7. 缓存机制测试
8. 性能测试
"""

import pytest
import numpy as np
from src.infra.greeks_engine import (
    GreeksEngine,
    OptionContract,
    OptionType,
    Greeks
)


class TestGreeksEngineInitialization:
    """测试Greeks Engine初始化"""
    
    def test_default_initialization(self):
        """测试默认初始化"""
        engine = GreeksEngine()
        
        assert engine.cache_enabled is True
        assert len(engine.cache) == 0
        assert engine.stats['total_calculations'] == 0
    
    def test_cache_disabled_initialization(self):
        """测试禁用缓存初始化"""
        engine = GreeksEngine(cache_enabled=False)
        
        assert engine.cache_enabled is False
        assert len(engine.cache) == 0


class TestOptionContractValidation:
    """测试期权合约验证"""
    
    def test_valid_contract(self):
        """测试有效合约"""
        contract = OptionContract(
            symbol="510050C2401M03000",
            underlying_price=3.0,
            strike_price=3.0,
            time_to_maturity=0.25,
            risk_free_rate=0.03,
            volatility=0.2,
            option_type=OptionType.CALL
        )
        
        assert contract.symbol == "510050C2401M03000"
        assert contract.underlying_price == 3.0
        assert contract.strike_price == 3.0
    
    def test_invalid_underlying_price(self):
        """测试无效标的价格"""
        with pytest.raises(ValueError, match="标的价格必须 > 0"):
            OptionContract(
                symbol="TEST",
                underlying_price=0,
                strike_price=100,
                time_to_maturity=1.0,
                risk_free_rate=0.03,
                volatility=0.2,
                option_type=OptionType.CALL
            )
    
    def test_invalid_strike_price(self):
        """测试无效行权价"""
        with pytest.raises(ValueError, match="行权价必须 > 0"):
            OptionContract(
                symbol="TEST",
                underlying_price=100,
                strike_price=-10,
                time_to_maturity=1.0,
                risk_free_rate=0.03,
                volatility=0.2,
                option_type=OptionType.CALL
            )
    
    def test_invalid_time_to_maturity(self):
        """测试无效到期时间"""
        with pytest.raises(ValueError, match="到期时间必须 > 0"):
            OptionContract(
                symbol="TEST",
                underlying_price=100,
                strike_price=100,
                time_to_maturity=0,
                risk_free_rate=0.03,
                volatility=0.2,
                option_type=OptionType.CALL
            )
    
    def test_invalid_volatility(self):
        """测试无效波动率"""
        with pytest.raises(ValueError, match="波动率必须 >= 0"):
            OptionContract(
                symbol="TEST",
                underlying_price=100,
                strike_price=100,
                time_to_maturity=1.0,
                risk_free_rate=0.03,
                volatility=-0.1,
                option_type=OptionType.CALL
            )


class TestOptionPricing:
    """测试期权定价"""
    
    def test_atm_call_option_pricing(self):
        """测试平值看涨期权定价"""
        engine = GreeksEngine()
        
        contract = OptionContract(
            symbol="TEST_CALL",
            underlying_price=100.0,
            strike_price=100.0,
            time_to_maturity=1.0,
            risk_free_rate=0.05,
            volatility=0.2,
            option_type=OptionType.CALL
        )
        
        price = engine.calculate_option_price(contract)
        
        # ATM期权价格应该合理（约10左右）
        assert 8.0 < price < 12.0
        assert price > 0
    
    def test_atm_put_option_pricing(self):
        """测试平值看跌期权定价"""
        engine = GreeksEngine()
        
        contract = OptionContract(
            symbol="TEST_PUT",
            underlying_price=100.0,
            strike_price=100.0,
            time_to_maturity=1.0,
            risk_free_rate=0.05,
            volatility=0.2,
            option_type=OptionType.PUT
        )
        
        price = engine.calculate_option_price(contract)
        
        # ATM期权价格应该合理
        assert 5.0 < price < 10.0
        assert price > 0
    
    def test_itm_call_option_pricing(self):
        """测试实值看涨期权定价"""
        engine = GreeksEngine()
        
        contract = OptionContract(
            symbol="TEST_CALL_ITM",
            underlying_price=110.0,
            strike_price=100.0,
            time_to_maturity=1.0,
            risk_free_rate=0.05,
            volatility=0.2,
            option_type=OptionType.CALL
        )
        
        price = engine.calculate_option_price(contract)
        
        # ITM看涨期权价格应该 > 内在价值(10)
        assert price > 10.0
        assert price < 20.0
    
    def test_otm_call_option_pricing(self):
        """测试虚值看涨期权定价"""
        engine = GreeksEngine()
        
        contract = OptionContract(
            symbol="TEST_CALL_OTM",
            underlying_price=90.0,
            strike_price=100.0,
            time_to_maturity=1.0,
            risk_free_rate=0.05,
            volatility=0.2,
            option_type=OptionType.CALL
        )
        
        price = engine.calculate_option_price(contract)
        
        # OTM看涨期权价格应该较小
        assert 0 < price < 6.0
    
    def test_put_call_parity(self):
        """测试看涨看跌平价关系"""
        engine = GreeksEngine()
        
        # 相同参数的看涨和看跌期权
        S = 100.0
        K = 100.0
        T = 1.0
        r = 0.05
        
        call_contract = OptionContract(
            symbol="TEST_CALL",
            underlying_price=S,
            strike_price=K,
            time_to_maturity=T,
            risk_free_rate=r,
            volatility=0.2,
            option_type=OptionType.CALL
        )
        
        put_contract = OptionContract(
            symbol="TEST_PUT",
            underlying_price=S,
            strike_price=K,
            time_to_maturity=T,
            risk_free_rate=r,
            volatility=0.2,
            option_type=OptionType.PUT
        )
        
        call_price = engine.calculate_option_price(call_contract)
        put_price = engine.calculate_option_price(put_contract)
        
        # 看涨看跌平价关系: C - P = S - K*e^(-rT)
        parity_lhs = call_price - put_price
        parity_rhs = S - K * np.exp(-r * T)
        
        # 允许小误差
        assert abs(parity_lhs - parity_rhs) < 0.01


class TestDeltaCalculation:
    """测试Delta计算"""
    
    def test_atm_call_delta(self):
        """测试平值看涨期权Delta"""
        engine = GreeksEngine()
        
        contract = OptionContract(
            symbol="TEST",
            underlying_price=100.0,
            strike_price=100.0,
            time_to_maturity=1.0,
            risk_free_rate=0.05,
            volatility=0.2,
            option_type=OptionType.CALL
        )
        
        delta = engine.calculate_delta(contract)
        
        # ATM看涨期权Delta约0.5-0.65（考虑无风险利率影响）
        assert 0.45 < delta < 0.70
    
    def test_atm_put_delta(self):
        """测试平值看跌期权Delta"""
        engine = GreeksEngine()
        
        contract = OptionContract(
            symbol="TEST",
            underlying_price=100.0,
            strike_price=100.0,
            time_to_maturity=1.0,
            risk_free_rate=0.05,
            volatility=0.2,
            option_type=OptionType.PUT
        )
        
        delta = engine.calculate_delta(contract)
        
        # ATM看跌期权Delta约-0.3到-0.5（考虑无风险利率影响）
        assert -0.55 < delta < -0.30
    
    def test_itm_call_delta(self):
        """测试实值看涨期权Delta"""
        engine = GreeksEngine()
        
        contract = OptionContract(
            symbol="TEST",
            underlying_price=110.0,
            strike_price=100.0,
            time_to_maturity=1.0,
            risk_free_rate=0.05,
            volatility=0.2,
            option_type=OptionType.CALL
        )
        
        delta = engine.calculate_delta(contract)
        
        # ITM看涨期权Delta接近1
        assert 0.7 < delta < 1.0
    
    def test_otm_call_delta(self):
        """测试虚值看涨期权Delta"""
        engine = GreeksEngine()
        
        contract = OptionContract(
            symbol="TEST",
            underlying_price=90.0,
            strike_price=100.0,
            time_to_maturity=1.0,
            risk_free_rate=0.05,
            volatility=0.2,
            option_type=OptionType.CALL
        )
        
        delta = engine.calculate_delta(contract)
        
        # OTM看涨期权Delta较小
        assert 0.0 < delta < 0.5
    
    def test_delta_range_call(self):
        """测试看涨期权Delta范围"""
        engine = GreeksEngine()
        
        contract = OptionContract(
            symbol="TEST",
            underlying_price=100.0,
            strike_price=100.0,
            time_to_maturity=1.0,
            risk_free_rate=0.05,
            volatility=0.2,
            option_type=OptionType.CALL
        )
        
        delta = engine.calculate_delta(contract)
        
        # 看涨期权Delta ∈ [0, 1]
        assert 0 <= delta <= 1
    
    def test_delta_range_put(self):
        """测试看跌期权Delta范围"""
        engine = GreeksEngine()
        
        contract = OptionContract(
            symbol="TEST",
            underlying_price=100.0,
            strike_price=100.0,
            time_to_maturity=1.0,
            risk_free_rate=0.05,
            volatility=0.2,
            option_type=OptionType.PUT
        )
        
        delta = engine.calculate_delta(contract)
        
        # 看跌期权Delta ∈ [-1, 0]
        assert -1 <= delta <= 0


class TestGammaCalculation:
    """测试Gamma计算"""
    
    def test_atm_gamma(self):
        """测试平值期权Gamma"""
        engine = GreeksEngine()
        
        contract = OptionContract(
            symbol="TEST",
            underlying_price=100.0,
            strike_price=100.0,
            time_to_maturity=1.0,
            risk_free_rate=0.05,
            volatility=0.2,
            option_type=OptionType.CALL
        )
        
        gamma = engine.calculate_gamma(contract)
        
        # ATM期权Gamma最大
        assert gamma > 0
        assert 0.01 < gamma < 0.05
    
    def test_gamma_non_negative(self):
        """测试Gamma非负性"""
        engine = GreeksEngine()
        
        # 测试多个场景
        scenarios = [
            (90.0, 100.0),   # OTM
            (100.0, 100.0),  # ATM
            (110.0, 100.0),  # ITM
        ]
        
        for S, K in scenarios:
            contract = OptionContract(
                symbol="TEST",
                underlying_price=S,
                strike_price=K,
                time_to_maturity=1.0,
                risk_free_rate=0.05,
                volatility=0.2,
                option_type=OptionType.CALL
            )
            
            gamma = engine.calculate_gamma(contract)
            assert gamma >= 0
    
    def test_gamma_symmetry(self):
        """测试Gamma对称性（看涨看跌相同）"""
        engine = GreeksEngine()
        
        call_contract = OptionContract(
            symbol="TEST_CALL",
            underlying_price=100.0,
            strike_price=100.0,
            time_to_maturity=1.0,
            risk_free_rate=0.05,
            volatility=0.2,
            option_type=OptionType.CALL
        )
        
        put_contract = OptionContract(
            symbol="TEST_PUT",
            underlying_price=100.0,
            strike_price=100.0,
            time_to_maturity=1.0,
            risk_free_rate=0.05,
            volatility=0.2,
            option_type=OptionType.PUT
        )
        
        call_gamma = engine.calculate_gamma(call_contract)
        put_gamma = engine.calculate_gamma(put_contract)
        
        # 看涨和看跌期权Gamma相同
        assert abs(call_gamma - put_gamma) < 1e-10


class TestVegaCalculation:
    """测试Vega计算"""
    
    def test_atm_vega(self):
        """测试平值期权Vega"""
        engine = GreeksEngine()
        
        contract = OptionContract(
            symbol="TEST",
            underlying_price=100.0,
            strike_price=100.0,
            time_to_maturity=1.0,
            risk_free_rate=0.05,
            volatility=0.2,
            option_type=OptionType.CALL
        )
        
        vega = engine.calculate_vega(contract)
        
        # ATM期权Vega最大
        assert vega > 0
        assert 20.0 < vega < 50.0
    
    def test_vega_non_negative(self):
        """测试Vega非负性"""
        engine = GreeksEngine()
        
        contract = OptionContract(
            symbol="TEST",
            underlying_price=100.0,
            strike_price=100.0,
            time_to_maturity=1.0,
            risk_free_rate=0.05,
            volatility=0.2,
            option_type=OptionType.CALL
        )
        
        vega = engine.calculate_vega(contract)
        assert vega >= 0
    
    def test_vega_symmetry(self):
        """测试Vega对称性（看涨看跌相同）"""
        engine = GreeksEngine()
        
        call_contract = OptionContract(
            symbol="TEST_CALL",
            underlying_price=100.0,
            strike_price=100.0,
            time_to_maturity=1.0,
            risk_free_rate=0.05,
            volatility=0.2,
            option_type=OptionType.CALL
        )
        
        put_contract = OptionContract(
            symbol="TEST_PUT",
            underlying_price=100.0,
            strike_price=100.0,
            time_to_maturity=1.0,
            risk_free_rate=0.05,
            volatility=0.2,
            option_type=OptionType.PUT
        )
        
        call_vega = engine.calculate_vega(call_contract)
        put_vega = engine.calculate_vega(put_contract)
        
        # 看涨和看跌期权Vega相同
        assert abs(call_vega - put_vega) < 1e-10


class TestThetaCalculation:
    """测试Theta计算"""
    
    def test_theta_negative(self):
        """测试Theta为负（时间衰减）"""
        engine = GreeksEngine()
        
        contract = OptionContract(
            symbol="TEST",
            underlying_price=100.0,
            strike_price=100.0,
            time_to_maturity=1.0,
            risk_free_rate=0.05,
            volatility=0.2,
            option_type=OptionType.CALL
        )
        
        theta = engine.calculate_theta(contract)
        
        # Theta通常为负
        assert theta < 0
    
    def test_theta_magnitude(self):
        """测试Theta数量级"""
        engine = GreeksEngine()
        
        contract = OptionContract(
            symbol="TEST",
            underlying_price=100.0,
            strike_price=100.0,
            time_to_maturity=1.0,
            risk_free_rate=0.05,
            volatility=0.2,
            option_type=OptionType.CALL
        )
        
        theta = engine.calculate_theta(contract)
        
        # Theta数量级合理
        assert -20.0 < theta < 0.0


class TestRhoCalculation:
    """测试Rho计算"""
    
    def test_call_rho_positive(self):
        """测试看涨期权Rho为正"""
        engine = GreeksEngine()
        
        contract = OptionContract(
            symbol="TEST",
            underlying_price=100.0,
            strike_price=100.0,
            time_to_maturity=1.0,
            risk_free_rate=0.05,
            volatility=0.2,
            option_type=OptionType.CALL
        )
        
        rho = engine.calculate_rho(contract)
        
        # 看涨期权Rho > 0
        assert rho > 0
        assert 20.0 < rho < 60.0
    
    def test_put_rho_negative(self):
        """测试看跌期权Rho为负"""
        engine = GreeksEngine()
        
        contract = OptionContract(
            symbol="TEST",
            underlying_price=100.0,
            strike_price=100.0,
            time_to_maturity=1.0,
            risk_free_rate=0.05,
            volatility=0.2,
            option_type=OptionType.PUT
        )
        
        rho = engine.calculate_rho(contract)
        
        # 看跌期权Rho < 0
        assert rho < 0
        assert -60.0 < rho < -20.0


class TestGreeksCalculation:
    """测试Greeks综合计算"""
    
    def test_calculate_all_greeks(self):
        """测试计算所有Greeks"""
        engine = GreeksEngine()
        
        contract = OptionContract(
            symbol="TEST",
            underlying_price=100.0,
            strike_price=100.0,
            time_to_maturity=1.0,
            risk_free_rate=0.05,
            volatility=0.2,
            option_type=OptionType.CALL
        )
        
        greeks = engine.calculate_greeks(contract)
        
        assert isinstance(greeks, Greeks)
        assert greeks.option_price > 0
        assert 0 <= greeks.delta <= 1
        assert greeks.gamma >= 0
        assert greeks.vega >= 0
        assert greeks.theta < 0
        assert greeks.rho > 0
    
    def test_greeks_consistency(self):
        """测试Greeks一致性"""
        engine = GreeksEngine()
        
        contract = OptionContract(
            symbol="TEST",
            underlying_price=100.0,
            strike_price=100.0,
            time_to_maturity=1.0,
            risk_free_rate=0.05,
            volatility=0.2,
            option_type=OptionType.CALL
        )
        
        # 分别计算
        delta_separate = engine.calculate_delta(contract)
        gamma_separate = engine.calculate_gamma(contract)
        
        # 综合计算
        greeks = engine.calculate_greeks(contract)
        
        # 结果应该一致
        assert abs(greeks.delta - delta_separate) < 1e-10
        assert abs(greeks.gamma - gamma_separate) < 1e-10


class TestCacheMechanism:
    """测试缓存机制"""
    
    def test_cache_hit(self):
        """测试缓存命中"""
        engine = GreeksEngine(cache_enabled=True)
        
        contract = OptionContract(
            symbol="TEST",
            underlying_price=100.0,
            strike_price=100.0,
            time_to_maturity=1.0,
            risk_free_rate=0.05,
            volatility=0.2,
            option_type=OptionType.CALL
        )
        
        # 第一次计算
        price1 = engine.calculate_option_price(contract)
        stats1 = engine.get_stats()
        
        # 第二次计算（应该命中缓存）
        price2 = engine.calculate_option_price(contract)
        stats2 = engine.get_stats()
        
        assert price1 == price2
        assert stats2['cache_hits'] == stats1['cache_hits'] + 1
    
    def test_cache_disabled(self):
        """测试禁用缓存"""
        engine = GreeksEngine(cache_enabled=False)
        
        contract = OptionContract(
            symbol="TEST",
            underlying_price=100.0,
            strike_price=100.0,
            time_to_maturity=1.0,
            risk_free_rate=0.05,
            volatility=0.2,
            option_type=OptionType.CALL
        )
        
        # 计算两次
        engine.calculate_option_price(contract)
        engine.calculate_option_price(contract)
        
        stats = engine.get_stats()
        
        # 禁用缓存时不应该有缓存命中
        assert stats['cache_hits'] == 0
    
    def test_clear_cache(self):
        """测试清空缓存"""
        engine = GreeksEngine(cache_enabled=True)
        
        contract = OptionContract(
            symbol="TEST",
            underlying_price=100.0,
            strike_price=100.0,
            time_to_maturity=1.0,
            risk_free_rate=0.05,
            volatility=0.2,
            option_type=OptionType.CALL
        )
        
        # 计算并缓存
        engine.calculate_option_price(contract)
        assert len(engine.cache) > 0
        
        # 清空缓存
        engine.clear_cache()
        assert len(engine.cache) == 0


class TestPerformance:
    """测试性能"""
    
    def test_single_calculation_performance(self):
        """测试单次计算性能"""
        engine = GreeksEngine()
        
        contract = OptionContract(
            symbol="TEST",
            underlying_price=100.0,
            strike_price=100.0,
            time_to_maturity=1.0,
            risk_free_rate=0.05,
            volatility=0.2,
            option_type=OptionType.CALL
        )
        
        # 计算Greeks
        engine.calculate_greeks(contract)
        
        stats = engine.get_stats()
        
        # 性能目标: P99 < 50ms
        assert stats['avg_calculation_time_ms'] < 50.0
    
    def test_batch_calculation_performance(self):
        """测试批量计算性能"""
        engine = GreeksEngine()
        
        # 创建100个期权合约
        contracts = []
        for i in range(100):
            contract = OptionContract(
                symbol=f"TEST_{i}",
                underlying_price=100.0 + i * 0.1,
                strike_price=100.0,
                time_to_maturity=1.0,
                risk_free_rate=0.05,
                volatility=0.2,
                option_type=OptionType.CALL
            )
            contracts.append(contract)
        
        # 批量计算
        import time
        start_time = time.perf_counter()
        
        for contract in contracts:
            engine.calculate_greeks(contract)
        
        elapsed = (time.perf_counter() - start_time) * 1000
        
        # 性能目标: > 100个/秒 = < 10ms/个
        avg_time_per_contract = elapsed / len(contracts)
        assert avg_time_per_contract < 10.0
    
    def test_statistics_tracking(self):
        """测试统计跟踪"""
        engine = GreeksEngine(cache_enabled=False)  # 禁用缓存以准确统计
        
        contract = OptionContract(
            symbol="TEST",
            underlying_price=100.0,
            strike_price=100.0,
            time_to_maturity=1.0,
            risk_free_rate=0.05,
            volatility=0.2,
            option_type=OptionType.CALL
        )
        
        # 执行多次计算
        for _ in range(10):
            engine.calculate_greeks(contract)
        
        stats = engine.get_stats()
        
        # 禁用缓存时，每次calculate_greeks会调用calculate_option_price一次
        # 所以total_calculations应该是10（greeks）+ 10（price）= 20
        assert stats['total_calculations'] >= 10
        assert stats['avg_calculation_time_ms'] > 0
        assert stats['total_calculation_time_ms'] > 0


class TestImpliedVolatility:
    """测试隐含波动率计算"""
    
    def test_atm_implied_volatility(self):
        """测试平值期权隐含波动率"""
        engine = GreeksEngine()
        
        # 已知波动率
        true_volatility = 0.25
        
        contract = OptionContract(
            symbol="TEST",
            underlying_price=100.0,
            strike_price=100.0,
            time_to_maturity=1.0,
            risk_free_rate=0.05,
            volatility=true_volatility,
            option_type=OptionType.CALL
        )
        
        # 计算理论价格
        market_price = engine.calculate_option_price(contract)
        
        # 反推隐含波动率
        implied_vol = engine.calculate_implied_volatility(contract, market_price)
        
        assert implied_vol is not None
        # 允许小误差
        assert abs(implied_vol - true_volatility) < 0.001
    
    def test_itm_implied_volatility(self):
        """测试实值期权隐含波动率"""
        engine = GreeksEngine()
        
        true_volatility = 0.30
        
        contract = OptionContract(
            symbol="TEST",
            underlying_price=110.0,
            strike_price=100.0,
            time_to_maturity=1.0,
            risk_free_rate=0.05,
            volatility=true_volatility,
            option_type=OptionType.CALL
        )
        
        market_price = engine.calculate_option_price(contract)
        implied_vol = engine.calculate_implied_volatility(contract, market_price)
        
        assert implied_vol is not None
        assert abs(implied_vol - true_volatility) < 0.001
    
    def test_otm_implied_volatility(self):
        """测试虚值期权隐含波动率"""
        engine = GreeksEngine()
        
        true_volatility = 0.20
        
        contract = OptionContract(
            symbol="TEST",
            underlying_price=90.0,
            strike_price=100.0,
            time_to_maturity=1.0,
            risk_free_rate=0.05,
            volatility=true_volatility,
            option_type=OptionType.CALL
        )
        
        market_price = engine.calculate_option_price(contract)
        implied_vol = engine.calculate_implied_volatility(contract, market_price)
        
        assert implied_vol is not None
        assert abs(implied_vol - true_volatility) < 0.001
    
    def test_put_implied_volatility(self):
        """测试看跌期权隐含波动率"""
        engine = GreeksEngine()
        
        true_volatility = 0.25
        
        contract = OptionContract(
            symbol="TEST",
            underlying_price=100.0,
            strike_price=100.0,
            time_to_maturity=1.0,
            risk_free_rate=0.05,
            volatility=true_volatility,
            option_type=OptionType.PUT
        )
        
        market_price = engine.calculate_option_price(contract)
        implied_vol = engine.calculate_implied_volatility(contract, market_price)
        
        assert implied_vol is not None
        assert abs(implied_vol - true_volatility) < 0.001
    
    def test_convergence_speed(self):
        """测试收敛速度"""
        engine = GreeksEngine()
        
        contract = OptionContract(
            symbol="TEST",
            underlying_price=100.0,
            strike_price=100.0,
            time_to_maturity=1.0,
            risk_free_rate=0.05,
            volatility=0.25,
            option_type=OptionType.CALL
        )
        
        market_price = engine.calculate_option_price(contract)
        
        # 使用较少的最大迭代次数测试
        implied_vol = engine.calculate_implied_volatility(
            contract,
            market_price,
            max_iterations=10
        )
        
        # 应该在10次迭代内收敛
        assert implied_vol is not None
    
    def test_invalid_market_price(self):
        """测试无效市场价格"""
        engine = GreeksEngine()
        
        contract = OptionContract(
            symbol="TEST",
            underlying_price=100.0,
            strike_price=100.0,
            time_to_maturity=1.0,
            risk_free_rate=0.05,
            volatility=0.25,
            option_type=OptionType.CALL
        )
        
        # 负价格应该抛出异常
        with pytest.raises(ValueError, match="市场价格必须 > 0"):
            engine.calculate_implied_volatility(contract, -1.0)
        
        # 零价格应该抛出异常
        with pytest.raises(ValueError, match="市场价格必须 > 0"):
            engine.calculate_implied_volatility(contract, 0.0)
    
    def test_extreme_volatility(self):
        """测试极端波动率"""
        engine = GreeksEngine()
        
        # 测试高波动率
        high_vol_contract = OptionContract(
            symbol="TEST",
            underlying_price=100.0,
            strike_price=100.0,
            time_to_maturity=1.0,
            risk_free_rate=0.05,
            volatility=0.80,
            option_type=OptionType.CALL
        )
        
        market_price = engine.calculate_option_price(high_vol_contract)
        implied_vol = engine.calculate_implied_volatility(high_vol_contract, market_price)
        
        assert implied_vol is not None
        assert abs(implied_vol - 0.80) < 0.01
    
    def test_short_maturity(self):
        """测试短期期权"""
        engine = GreeksEngine()
        
        contract = OptionContract(
            symbol="TEST",
            underlying_price=100.0,
            strike_price=100.0,
            time_to_maturity=0.1,  # 约36天
            risk_free_rate=0.05,
            volatility=0.25,
            option_type=OptionType.CALL
        )
        
        market_price = engine.calculate_option_price(contract)
        implied_vol = engine.calculate_implied_volatility(contract, market_price)
        
        assert implied_vol is not None
        assert abs(implied_vol - 0.25) < 0.01
    
    def test_numerical_stability(self):
        """测试数值稳定性"""
        engine = GreeksEngine()
        
        # 测试多个场景
        scenarios = [
            (100.0, 100.0, 0.25),  # ATM
            (110.0, 100.0, 0.30),  # ITM
            (90.0, 100.0, 0.20),   # OTM
            (100.0, 120.0, 0.35),  # Deep OTM
            (120.0, 100.0, 0.40),  # Deep ITM
        ]
        
        for S, K, vol in scenarios:
            contract = OptionContract(
                symbol="TEST",
                underlying_price=S,
                strike_price=K,
                time_to_maturity=1.0,
                risk_free_rate=0.05,
                volatility=vol,
                option_type=OptionType.CALL
            )
            
            market_price = engine.calculate_option_price(contract)
            implied_vol = engine.calculate_implied_volatility(contract, market_price)
            
            assert implied_vol is not None
            assert abs(implied_vol - vol) < 0.01
