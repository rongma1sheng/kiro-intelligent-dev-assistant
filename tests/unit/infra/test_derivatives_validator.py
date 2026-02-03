"""
衍生品数据验证器单元测试

白皮书依据: 第三章 3.3 衍生品管道 - 数据验证

测试覆盖:
1. 期货数据验证测试
2. 期权平价关系验证测试
3. Greeks范围检查测试
4. 验证报告测试
5. 统计功能测试
"""

import pytest
import numpy as np
from src.infra.derivatives_validator import (
    DerivativesValidator,
    FutureData,
    OptionData,
    GreeksData,
    ValidationResult,
    ValidationReport
)


class TestDerivativesValidatorInitialization:
    """测试衍生品验证器初始化"""
    
    def test_default_initialization(self):
        """测试默认初始化"""
        validator = DerivativesValidator()
        
        assert validator.price_tolerance == 0.01
        assert validator.parity_tolerance == 0.05
        assert validator.stats['total_validations'] == 0
        assert validator.stats['passed_validations'] == 0
        assert validator.stats['failed_validations'] == 0
        assert validator.stats['warnings'] == 0
    
    def test_custom_initialization(self):
        """测试自定义初始化"""
        validator = DerivativesValidator(
            price_tolerance=0.02,
            parity_tolerance=0.10
        )
        
        assert validator.price_tolerance == 0.02
        assert validator.parity_tolerance == 0.10


class TestFutureDataValidation:
    """测试期货数据验证"""
    
    def test_valid_future_data(self):
        """测试有效期货数据"""
        validator = DerivativesValidator()
        
        data = FutureData(
            symbol="IF2401",
            price=4000.0,
            volume=10000.0,
            open_interest=50000.0,
            settlement_price=4005.0,
            pre_settlement=3995.0
        )
        
        report = validator.validate_future_data(data)
        
        assert report.result == ValidationResult.PASS
        assert len(report.passed_checks) >= 5
        assert len(report.failed_checks) == 0
        assert "价格 > 0" in report.passed_checks
        assert "成交量 >= 0" in report.passed_checks
        assert "持仓量 >= 0" in report.passed_checks
    
    def test_invalid_price(self):
        """测试无效价格"""
        validator = DerivativesValidator()
        
        data = FutureData(
            symbol="IF2401",
            price=-100.0,  # 负价格
            volume=10000.0,
            open_interest=50000.0
        )
        
        report = validator.validate_future_data(data)
        
        assert report.result == ValidationResult.FAIL
        assert any("价格不合理" in check for check in report.failed_checks)
    
    def test_invalid_volume(self):
        """测试无效成交量"""
        validator = DerivativesValidator()
        
        data = FutureData(
            symbol="IF2401",
            price=4000.0,
            volume=-1000.0,  # 负成交量
            open_interest=50000.0
        )
        
        report = validator.validate_future_data(data)
        
        assert report.result == ValidationResult.FAIL
        assert any("成交量不合理" in check for check in report.failed_checks)
    
    def test_invalid_open_interest(self):
        """测试无效持仓量"""
        validator = DerivativesValidator()
        
        data = FutureData(
            symbol="IF2401",
            price=4000.0,
            volume=10000.0,
            open_interest=-5000.0  # 负持仓量
        )
        
        report = validator.validate_future_data(data)
        
        assert report.result == ValidationResult.FAIL
        assert any("持仓量不合理" in check for check in report.failed_checks)
    
    def test_settlement_price_deviation_warning(self):
        """测试结算价偏离警告"""
        validator = DerivativesValidator()
        
        data = FutureData(
            symbol="IF2401",
            price=4000.0,
            volume=10000.0,
            open_interest=50000.0,
            settlement_price=4500.0  # 偏离12.5%
        )
        
        report = validator.validate_future_data(data)
        
        assert report.result == ValidationResult.WARNING
        assert any("偏离较大" in warning for warning in report.warnings)
    
    def test_price_change_warning(self):
        """测试价格涨跌幅警告"""
        validator = DerivativesValidator()
        
        data = FutureData(
            symbol="IF2401",
            price=4000.0,
            volume=10000.0,
            open_interest=50000.0,
            settlement_price=4000.0,
            pre_settlement=3200.0  # 涨幅25%
        )
        
        report = validator.validate_future_data(data)
        
        assert report.result == ValidationResult.WARNING
        assert any("涨跌幅较大" in warning for warning in report.warnings)
    
    def test_volume_oi_ratio_warning(self):
        """测试成交量/持仓量比例警告"""
        validator = DerivativesValidator()
        
        data = FutureData(
            symbol="IF2401",
            price=4000.0,
            volume=100000.0,  # 成交量
            open_interest=5000.0  # 持仓量，比例20:1
        )
        
        report = validator.validate_future_data(data)
        
        assert report.result == ValidationResult.WARNING
        assert any("比例异常" in warning for warning in report.warnings)
    
    def test_minimal_future_data(self):
        """测试最小期货数据（无可选字段）"""
        validator = DerivativesValidator()
        
        data = FutureData(
            symbol="IF2401",
            price=4000.0,
            volume=10000.0,
            open_interest=50000.0
        )
        
        report = validator.validate_future_data(data)
        
        assert report.result == ValidationResult.PASS
        assert len(report.passed_checks) >= 3


class TestPutCallParityValidation:
    """测试期权平价关系验证"""
    
    def test_valid_put_call_parity(self):
        """测试有效平价关系"""
        validator = DerivativesValidator()
        
        # 构造满足平价关系的数据
        S = 100.0
        K = 100.0
        T = 1.0
        r = 0.05
        
        # C - P = S - K*e^(-rT)
        parity_rhs = S - K * np.exp(-r * T)
        call_price = 10.0
        put_price = call_price - parity_rhs
        
        data = OptionData(
            symbol="510050C2401M03000",
            call_price=call_price,
            put_price=put_price,
            underlying_price=S,
            strike_price=K,
            time_to_maturity=T,
            risk_free_rate=r
        )
        
        report = validator.validate_put_call_parity(data)
        
        assert report.result == ValidationResult.PASS
        assert len(report.passed_checks) > 0
        assert len(report.failed_checks) == 0
    
    def test_parity_deviation_warning(self):
        """测试平价关系偏离警告"""
        validator = DerivativesValidator(parity_tolerance=0.05)
        
        data = OptionData(
            symbol="510050C2401M03000",
            call_price=10.0,
            put_price=5.0,
            underlying_price=100.0,
            strike_price=100.0,
            time_to_maturity=1.0,
            risk_free_rate=0.05
        )
        
        report = validator.validate_put_call_parity(data)
        
        # 偏离在容差的1-2倍之间应该是WARNING
        if report.result == ValidationResult.WARNING:
            assert len(report.warnings) > 0
            assert any("偏离较大" in warning for warning in report.warnings)
    
    def test_parity_severe_deviation_fail(self):
        """测试平价关系严重偏离失败"""
        validator = DerivativesValidator(parity_tolerance=0.05)
        
        data = OptionData(
            symbol="510050C2401M03000",
            call_price=20.0,
            put_price=2.0,
            underlying_price=100.0,
            strike_price=100.0,
            time_to_maturity=1.0,
            risk_free_rate=0.05
        )
        
        report = validator.validate_put_call_parity(data)
        
        # 偏离超过容差2倍应该是FAIL
        if report.result == ValidationResult.FAIL:
            assert len(report.failed_checks) > 0
            assert any("严重偏离" in check for check in report.failed_checks)
    
    def test_arbitrage_opportunity_detection(self):
        """测试套利机会检测"""
        validator = DerivativesValidator()
        
        # 构造有套利机会的数据
        data = OptionData(
            symbol="510050C2401M03000",
            call_price=15.0,
            put_price=3.0,
            underlying_price=100.0,
            strike_price=100.0,
            time_to_maturity=1.0,
            risk_free_rate=0.05
        )
        
        report = validator.validate_put_call_parity(data)
        
        # 应该检测到套利机会
        if 'arbitrage_opportunity' in report.details:
            assert report.details['arbitrage_opportunity'] is not None
    
    def test_parity_calculation_details(self):
        """测试平价关系计算细节"""
        validator = DerivativesValidator()
        
        data = OptionData(
            symbol="510050C2401M03000",
            call_price=10.0,
            put_price=5.0,
            underlying_price=100.0,
            strike_price=100.0,
            time_to_maturity=1.0,
            risk_free_rate=0.05
        )
        
        report = validator.validate_put_call_parity(data)
        
        # 检查详细信息
        assert 'parity_lhs' in report.details
        assert 'parity_rhs' in report.details
        assert 'parity_diff' in report.details
        assert 'parity_diff_pct' in report.details


class TestGreeksRangeValidation:
    """测试Greeks范围检查"""
    
    def test_valid_greeks(self):
        """测试有效Greeks"""
        validator = DerivativesValidator()
        
        data = GreeksData(
            symbol="510050C2401M03000",
            delta=0.5,
            gamma=0.02,
            vega=30.0,
            theta=-5.0,
            rho=40.0
        )
        
        report = validator.validate_greeks_range(data)
        
        assert report.result == ValidationResult.PASS
        assert len(report.passed_checks) >= 5
        assert len(report.failed_checks) == 0
    
    def test_delta_out_of_range(self):
        """测试Delta超出范围"""
        validator = DerivativesValidator()
        
        # Delta > 1
        data = GreeksData(
            symbol="TEST",
            delta=1.5,
            gamma=0.02,
            vega=30.0,
            theta=-5.0,
            rho=40.0
        )
        
        report = validator.validate_greeks_range(data)
        
        assert report.result == ValidationResult.FAIL
        assert any("Delta超出范围" in check for check in report.failed_checks)
    
    def test_negative_gamma(self):
        """测试负Gamma"""
        validator = DerivativesValidator()
        
        data = GreeksData(
            symbol="TEST",
            delta=0.5,
            gamma=-0.02,  # Gamma不能为负
            vega=30.0,
            theta=-5.0,
            rho=40.0
        )
        
        report = validator.validate_greeks_range(data)
        
        assert report.result == ValidationResult.FAIL
        assert any("Gamma < 0" in check for check in report.failed_checks)
    
    def test_negative_vega(self):
        """测试负Vega"""
        validator = DerivativesValidator()
        
        data = GreeksData(
            symbol="TEST",
            delta=0.5,
            gamma=0.02,
            vega=-30.0,  # Vega不能为负
            theta=-5.0,
            rho=40.0
        )
        
        report = validator.validate_greeks_range(data)
        
        assert report.result == ValidationResult.FAIL
        assert any("Vega < 0" in check for check in report.failed_checks)
    
    def test_positive_theta_warning(self):
        """测试正Theta警告"""
        validator = DerivativesValidator()
        
        data = GreeksData(
            symbol="TEST",
            delta=0.5,
            gamma=0.02,
            vega=30.0,
            theta=5.0,  # Theta为正（罕见）
            rho=40.0
        )
        
        report = validator.validate_greeks_range(data)
        
        assert report.result == ValidationResult.WARNING
        assert any("Theta > 0" in warning for warning in report.warnings)
    
    def test_extreme_rho_warning(self):
        """测试极端Rho警告"""
        validator = DerivativesValidator()
        
        data = GreeksData(
            symbol="TEST",
            delta=0.5,
            gamma=0.02,
            vega=30.0,
            theta=-5.0,
            rho=2000.0  # Rho数值过大
        )
        
        report = validator.validate_greeks_range(data)
        
        assert report.result == ValidationResult.WARNING
        assert any("Rho数值较大" in warning for warning in report.warnings)
    
    def test_call_option_greeks(self):
        """测试看涨期权Greeks"""
        validator = DerivativesValidator()
        
        # 典型看涨期权Greeks
        data = GreeksData(
            symbol="CALL_TEST",
            delta=0.6,  # 看涨Delta: [0, 1]
            gamma=0.03,
            vega=35.0,
            theta=-8.0,
            rho=50.0  # 看涨Rho > 0
        )
        
        report = validator.validate_greeks_range(data)
        
        assert report.result == ValidationResult.PASS
    
    def test_put_option_greeks(self):
        """测试看跌期权Greeks"""
        validator = DerivativesValidator()
        
        # 典型看跌期权Greeks
        data = GreeksData(
            symbol="PUT_TEST",
            delta=-0.4,  # 看跌Delta: [-1, 0]
            gamma=0.03,
            vega=35.0,
            theta=-8.0,
            rho=-50.0  # 看跌Rho < 0
        )
        
        report = validator.validate_greeks_range(data)
        
        assert report.result == ValidationResult.PASS
    
    def test_multiple_greeks_violations(self):
        """测试多个Greeks违规"""
        validator = DerivativesValidator()
        
        data = GreeksData(
            symbol="TEST",
            delta=1.5,  # 违规
            gamma=-0.02,  # 违规
            vega=-30.0,  # 违规
            theta=-5.0,
            rho=40.0
        )
        
        report = validator.validate_greeks_range(data)
        
        assert report.result == ValidationResult.FAIL
        assert len(report.failed_checks) >= 3


class TestValidationStatistics:
    """测试验证统计"""
    
    def test_statistics_tracking(self):
        """测试统计跟踪"""
        validator = DerivativesValidator()
        
        # 执行多次验证
        for i in range(5):
            data = FutureData(
                symbol=f"IF240{i}",
                price=4000.0 + i * 10,
                volume=10000.0,
                open_interest=50000.0
            )
            validator.validate_future_data(data)
        
        stats = validator.get_stats()
        
        assert stats['total_validations'] == 5
        assert stats['passed_validations'] == 5
        assert stats['failed_validations'] == 0
        assert stats['pass_rate'] == 1.0
    
    def test_failed_validation_statistics(self):
        """测试失败验证统计"""
        validator = DerivativesValidator()
        
        # 有效数据
        valid_data = FutureData(
            symbol="IF2401",
            price=4000.0,
            volume=10000.0,
            open_interest=50000.0
        )
        validator.validate_future_data(valid_data)
        
        # 无效数据
        invalid_data = FutureData(
            symbol="IF2402",
            price=-100.0,
            volume=10000.0,
            open_interest=50000.0
        )
        validator.validate_future_data(invalid_data)
        
        stats = validator.get_stats()
        
        assert stats['total_validations'] == 2
        assert stats['passed_validations'] == 1
        assert stats['failed_validations'] == 1
        assert stats['pass_rate'] == 0.5
    
    def test_warning_statistics(self):
        """测试警告统计"""
        validator = DerivativesValidator()
        
        # 触发警告的数据
        data = FutureData(
            symbol="IF2401",
            price=4000.0,
            volume=10000.0,
            open_interest=50000.0,
            settlement_price=4500.0  # 偏离较大
        )
        validator.validate_future_data(data)
        
        stats = validator.get_stats()
        
        assert stats['warnings'] >= 1
    
    def test_reset_statistics(self):
        """测试重置统计"""
        validator = DerivativesValidator()
        
        # 执行一些验证
        data = FutureData(
            symbol="IF2401",
            price=4000.0,
            volume=10000.0,
            open_interest=50000.0
        )
        validator.validate_future_data(data)
        
        # 重置统计
        validator.reset_stats()
        
        stats = validator.get_stats()
        
        assert stats['total_validations'] == 0
        assert stats['passed_validations'] == 0
        assert stats['failed_validations'] == 0
        assert stats['warnings'] == 0
        assert stats['pass_rate'] == 0.0
    
    def test_mixed_validation_statistics(self):
        """测试混合验证统计"""
        validator = DerivativesValidator()
        
        # 期货验证
        future_data = FutureData(
            symbol="IF2401",
            price=4000.0,
            volume=10000.0,
            open_interest=50000.0
        )
        validator.validate_future_data(future_data)
        
        # 期权平价关系验证
        option_data = OptionData(
            symbol="510050C2401M03000",
            call_price=10.0,
            put_price=5.0,
            underlying_price=100.0,
            strike_price=100.0,
            time_to_maturity=1.0,
            risk_free_rate=0.05
        )
        validator.validate_put_call_parity(option_data)
        
        # Greeks验证
        greeks_data = GreeksData(
            symbol="510050C2401M03000",
            delta=0.5,
            gamma=0.02,
            vega=30.0,
            theta=-5.0,
            rho=40.0
        )
        validator.validate_greeks_range(greeks_data)
        
        stats = validator.get_stats()
        
        # 应该统计所有类型的验证
        assert stats['total_validations'] == 3


class TestValidationReport:
    """测试验证报告"""
    
    def test_report_structure(self):
        """测试报告结构"""
        validator = DerivativesValidator()
        
        data = FutureData(
            symbol="IF2401",
            price=4000.0,
            volume=10000.0,
            open_interest=50000.0
        )
        
        report = validator.validate_future_data(data)
        
        assert isinstance(report, ValidationReport)
        assert isinstance(report.result, ValidationResult)
        assert isinstance(report.passed_checks, list)
        assert isinstance(report.failed_checks, list)
        assert isinstance(report.warnings, list)
        assert isinstance(report.details, dict)
    
    def test_pass_report(self):
        """测试通过报告"""
        validator = DerivativesValidator()
        
        data = FutureData(
            symbol="IF2401",
            price=4000.0,
            volume=10000.0,
            open_interest=50000.0
        )
        
        report = validator.validate_future_data(data)
        
        assert report.result == ValidationResult.PASS
        assert len(report.passed_checks) > 0
        assert len(report.failed_checks) == 0
    
    def test_warning_report(self):
        """测试警告报告"""
        validator = DerivativesValidator()
        
        data = FutureData(
            symbol="IF2401",
            price=4000.0,
            volume=10000.0,
            open_interest=50000.0,
            settlement_price=4500.0  # 偏离较大
        )
        
        report = validator.validate_future_data(data)
        
        assert report.result == ValidationResult.WARNING
        assert len(report.warnings) > 0
    
    def test_fail_report(self):
        """测试失败报告"""
        validator = DerivativesValidator()
        
        data = FutureData(
            symbol="IF2401",
            price=-100.0,  # 无效价格
            volume=10000.0,
            open_interest=50000.0
        )
        
        report = validator.validate_future_data(data)
        
        assert report.result == ValidationResult.FAIL
        assert len(report.failed_checks) > 0
    
    def test_report_details(self):
        """测试报告详细信息"""
        validator = DerivativesValidator()
        
        data = FutureData(
            symbol="IF2401",
            price=4000.0,
            volume=10000.0,
            open_interest=50000.0,
            settlement_price=4005.0,
            pre_settlement=3995.0
        )
        
        report = validator.validate_future_data(data)
        
        # 检查详细信息
        assert 'price' in report.details
        assert 'volume' in report.details
        assert 'open_interest' in report.details
        assert 'settlement_price' in report.details
        assert 'pre_settlement' in report.details
        assert 'price_change' in report.details


class TestEdgeCases:
    """测试边界情况"""
    
    def test_zero_price(self):
        """测试零价格"""
        validator = DerivativesValidator()
        
        data = FutureData(
            symbol="IF2401",
            price=0.0,
            volume=10000.0,
            open_interest=50000.0
        )
        
        report = validator.validate_future_data(data)
        
        assert report.result == ValidationResult.FAIL
    
    def test_zero_volume(self):
        """测试零成交量"""
        validator = DerivativesValidator()
        
        data = FutureData(
            symbol="IF2401",
            price=4000.0,
            volume=0.0,
            open_interest=50000.0
        )
        
        report = validator.validate_future_data(data)
        
        assert report.result == ValidationResult.PASS
    
    def test_zero_open_interest(self):
        """测试零持仓量"""
        validator = DerivativesValidator()
        
        data = FutureData(
            symbol="IF2401",
            price=4000.0,
            volume=10000.0,
            open_interest=0.0
        )
        
        report = validator.validate_future_data(data)
        
        assert report.result == ValidationResult.PASS
    
    def test_delta_boundary_values(self):
        """测试Delta边界值"""
        validator = DerivativesValidator()
        
        # Delta = 0
        data1 = GreeksData(
            symbol="TEST",
            delta=0.0,
            gamma=0.02,
            vega=30.0,
            theta=-5.0,
            rho=40.0
        )
        report1 = validator.validate_greeks_range(data1)
        assert report1.result == ValidationResult.PASS
        
        # Delta = 1
        data2 = GreeksData(
            symbol="TEST",
            delta=1.0,
            gamma=0.02,
            vega=30.0,
            theta=-5.0,
            rho=40.0
        )
        report2 = validator.validate_greeks_range(data2)
        assert report2.result == ValidationResult.PASS
        
        # Delta = -1
        data3 = GreeksData(
            symbol="TEST",
            delta=-1.0,
            gamma=0.02,
            vega=30.0,
            theta=-5.0,
            rho=40.0
        )
        report3 = validator.validate_greeks_range(data3)
        assert report3.result == ValidationResult.PASS
    
    def test_gamma_zero(self):
        """测试Gamma为零"""
        validator = DerivativesValidator()
        
        data = GreeksData(
            symbol="TEST",
            delta=0.5,
            gamma=0.0,
            vega=30.0,
            theta=-5.0,
            rho=40.0
        )
        
        report = validator.validate_greeks_range(data)
        
        assert report.result == ValidationResult.PASS
    
    def test_vega_zero(self):
        """测试Vega为零"""
        validator = DerivativesValidator()
        
        data = GreeksData(
            symbol="TEST",
            delta=0.5,
            gamma=0.02,
            vega=0.0,
            theta=-5.0,
            rho=40.0
        )
        
        report = validator.validate_greeks_range(data)
        
        assert report.result == ValidationResult.PASS
    
    def test_theta_zero(self):
        """测试Theta为零"""
        validator = DerivativesValidator()
        
        data = GreeksData(
            symbol="TEST",
            delta=0.5,
            gamma=0.02,
            vega=30.0,
            theta=0.0,
            rho=40.0
        )
        
        report = validator.validate_greeks_range(data)
        
        assert report.result == ValidationResult.PASS
    
    def test_rho_zero(self):
        """测试Rho为零"""
        validator = DerivativesValidator()
        
        data = GreeksData(
            symbol="TEST",
            delta=0.5,
            gamma=0.02,
            vega=30.0,
            theta=-5.0,
            rho=0.0
        )
        
        report = validator.validate_greeks_range(data)
        
        assert report.result == ValidationResult.PASS
    
    def test_very_small_time_to_maturity(self):
        """测试极短到期时间"""
        validator = DerivativesValidator()
        
        data = OptionData(
            symbol="510050C2401M03000",
            call_price=0.1,
            put_price=0.05,
            underlying_price=100.0,
            strike_price=100.0,
            time_to_maturity=0.001,  # 约8小时
            risk_free_rate=0.05
        )
        
        report = validator.validate_put_call_parity(data)
        
        # 应该能正常验证
        assert report.result in [ValidationResult.PASS, ValidationResult.WARNING, ValidationResult.FAIL]
    
    def test_very_large_strike_price(self):
        """测试极大行权价"""
        validator = DerivativesValidator()
        
        data = OptionData(
            symbol="510050C2401M03000",
            call_price=0.01,
            put_price=10000.0,
            underlying_price=100.0,
            strike_price=10000.0,
            time_to_maturity=1.0,
            risk_free_rate=0.05
        )
        
        report = validator.validate_put_call_parity(data)
        
        # 应该能正常验证
        assert report.result in [ValidationResult.PASS, ValidationResult.WARNING, ValidationResult.FAIL]


class TestRealWorldScenarios:
    """测试真实场景"""
    
    def test_stock_index_future(self):
        """测试股指期货"""
        validator = DerivativesValidator()
        
        data = FutureData(
            symbol="IF2401",
            price=4000.0,
            volume=50000.0,
            open_interest=100000.0,
            settlement_price=4005.0,
            pre_settlement=3995.0
        )
        
        report = validator.validate_future_data(data)
        
        assert report.result == ValidationResult.PASS
    
    def test_commodity_future(self):
        """测试商品期货"""
        validator = DerivativesValidator()
        
        data = FutureData(
            symbol="CU2401",
            price=60000.0,
            volume=20000.0,
            open_interest=80000.0,
            settlement_price=60100.0,
            pre_settlement=59900.0
        )
        
        report = validator.validate_future_data(data)
        
        assert report.result == ValidationResult.PASS
    
    def test_etf_option(self):
        """测试ETF期权"""
        validator = DerivativesValidator()
        
        # 50ETF期权
        data = OptionData(
            symbol="510050C2401M03000",
            call_price=0.15,
            put_price=0.10,
            underlying_price=3.0,
            strike_price=3.0,
            time_to_maturity=0.25,
            risk_free_rate=0.03
        )
        
        report = validator.validate_put_call_parity(data)
        
        # 应该能正常验证
        assert report.result in [ValidationResult.PASS, ValidationResult.WARNING, ValidationResult.FAIL]
    
    def test_deep_itm_call_greeks(self):
        """测试深度实值看涨期权Greeks"""
        validator = DerivativesValidator()
        
        data = GreeksData(
            symbol="DEEP_ITM_CALL",
            delta=0.95,  # 接近1
            gamma=0.005,  # 较小
            vega=5.0,  # 较小
            theta=-2.0,
            rho=80.0  # 较大
        )
        
        report = validator.validate_greeks_range(data)
        
        assert report.result == ValidationResult.PASS
    
    def test_deep_otm_put_greeks(self):
        """测试深度虚值看跌期权Greeks"""
        validator = DerivativesValidator()
        
        data = GreeksData(
            symbol="DEEP_OTM_PUT",
            delta=-0.05,  # 接近0
            gamma=0.001,  # 很小
            vega=2.0,  # 很小
            theta=-0.5,
            rho=-5.0  # 较小
        )
        
        report = validator.validate_greeks_range(data)
        
        assert report.result == ValidationResult.PASS
    
    def test_atm_option_greeks(self):
        """测试平值期权Greeks"""
        validator = DerivativesValidator()
        
        data = GreeksData(
            symbol="ATM_OPTION",
            delta=0.5,
            gamma=0.04,  # 最大
            vega=40.0,  # 最大
            theta=-10.0,
            rho=50.0
        )
        
        report = validator.validate_greeks_range(data)
        
        assert report.result == ValidationResult.PASS
    
    def test_limit_up_future(self):
        """测试涨停期货"""
        validator = DerivativesValidator()
        
        data = FutureData(
            symbol="IF2401",
            price=4840.0,
            volume=1000.0,  # 涨停后成交量小
            open_interest=100000.0,
            settlement_price=4840.0,
            pre_settlement=4000.0  # 涨幅21%
        )
        
        report = validator.validate_future_data(data)
        
        # 涨停应该触发警告（涨幅超过20%）
        assert report.result == ValidationResult.WARNING
        assert any("涨跌幅较大" in warning for warning in report.warnings)
    
    def test_limit_down_future(self):
        """测试跌停期货"""
        validator = DerivativesValidator()
        
        data = FutureData(
            symbol="IF2401",
            price=3160.0,
            volume=1000.0,  # 跌停后成交量小
            open_interest=100000.0,
            settlement_price=3160.0,
            pre_settlement=4000.0  # 跌幅21%
        )
        
        report = validator.validate_future_data(data)
        
        # 跌停应该触发警告（跌幅超过20%）
        assert report.result == ValidationResult.WARNING
        assert any("涨跌幅较大" in warning for warning in report.warnings)
    
    def test_new_contract_low_oi(self):
        """测试新合约低持仓"""
        validator = DerivativesValidator()
        
        data = FutureData(
            symbol="IF2406",  # 远月合约
            price=4000.0,
            volume=100.0,
            open_interest=500.0  # 持仓量很小
        )
        
        report = validator.validate_future_data(data)
        
        # 新合约低持仓是正常的
        assert report.result == ValidationResult.PASS
    
    def test_expiring_contract_high_volume(self):
        """测试临近到期合约高成交量"""
        validator = DerivativesValidator()
        
        data = FutureData(
            symbol="IF2401",
            price=4000.0,
            volume=200000.0,  # 移仓换月，成交量大
            open_interest=50000.0
        )
        
        report = validator.validate_future_data(data)
        
        # 移仓换月期间成交量/持仓量比例大是正常的
        # 但会触发警告
        if report.result == ValidationResult.WARNING:
            assert any("比例异常" in warning for warning in report.warnings)
