"""风险控制矩阵单元测试

白皮书依据: 第十九章 19.2 风险控制机制
"""

import pytest

from src.risk.risk_control_matrix import RiskControlMatrix
from src.risk.risk_identification_system import RiskLevel


class TestRiskControlMatrix:
    """风险控制矩阵测试"""
    
    @pytest.fixture
    def matrix(self):
        """创建风险控制矩阵实例"""
        return RiskControlMatrix(
            single_position_ratio=0.20,
            daily_loss_ratio=0.10,
            margin_ratio=0.30,
            sector_concentration=0.40
        )
    
    def test_init_success(self):
        """测试初始化成功"""
        matrix = RiskControlMatrix()
        
        assert matrix.base_limits['single_position_ratio'] == 0.20
        assert matrix.base_limits['daily_loss_ratio'] == 0.10
        assert matrix.base_limits['margin_ratio'] == 0.30
        assert matrix.base_limits['sector_concentration'] == 0.40
        assert matrix.current_risk_level == RiskLevel.LOW
    
    def test_init_invalid_position_ratio(self):
        """测试无效的持仓比例"""
        with pytest.raises(ValueError, match="单只股票持仓比例必须在\\(0, 1\\]范围内"):
            RiskControlMatrix(single_position_ratio=1.5)
    
    def test_init_invalid_daily_loss(self):
        """测试无效的单日亏损比例"""
        with pytest.raises(ValueError, match="单日亏损比例必须在\\(0, 1\\]范围内"):
            RiskControlMatrix(daily_loss_ratio=0)
    
    def test_init_invalid_margin_ratio(self):
        """测试无效的保证金比例"""
        with pytest.raises(ValueError, match="保证金比例必须在\\(0, 1\\]范围内"):
            RiskControlMatrix(margin_ratio=1.5)
    
    def test_init_invalid_sector_concentration(self):
        """测试无效的行业集中度"""
        with pytest.raises(ValueError, match="行业集中度必须在\\(0, 1\\]范围内"):
            RiskControlMatrix(sector_concentration=0)
    
    def test_update_risk_level(self, matrix):
        """测试更新风险等级"""
        matrix.update_risk_level(RiskLevel.HIGH)
        assert matrix.current_risk_level == RiskLevel.HIGH
    
    def test_update_risk_level_invalid(self, matrix):
        """测试无效的风险等级"""
        with pytest.raises(ValueError, match="风险等级必须是RiskLevel枚举"):
            matrix.update_risk_level("high")
    
    def test_get_position_limit_low(self, matrix):
        """测试低风险时的持仓限制"""
        matrix.update_risk_level(RiskLevel.LOW)
        limit = matrix.get_position_limit()
        assert limit == 0.20  # 基础限制
    
    def test_get_position_limit_medium(self, matrix):
        """测试中风险时的持仓限制"""
        matrix.update_risk_level(RiskLevel.MEDIUM)
        limit = matrix.get_position_limit()
        assert limit == pytest.approx(0.16)  # 收紧20%
    
    def test_get_position_limit_high(self, matrix):
        """测试高风险时的持仓限制"""
        matrix.update_risk_level(RiskLevel.HIGH)
        limit = matrix.get_position_limit()
        assert limit == 0.10  # 收紧50%
    
    def test_get_position_limit_critical(self, matrix):
        """测试极高风险时的持仓限制"""
        matrix.update_risk_level(RiskLevel.CRITICAL)
        limit = matrix.get_position_limit()
        assert limit == 0.0  # 禁止新开仓
    
    def test_get_sector_limit_low(self, matrix):
        """测试低风险时的行业限制"""
        matrix.update_risk_level(RiskLevel.LOW)
        limit = matrix.get_sector_limit()
        assert limit == 0.40
    
    def test_get_sector_limit_medium(self, matrix):
        """测试中风险时的行业限制"""
        matrix.update_risk_level(RiskLevel.MEDIUM)
        limit = matrix.get_sector_limit()
        assert limit == pytest.approx(0.32)  # 收紧20%
    
    def test_get_sector_limit_high(self, matrix):
        """测试高风险时的行业限制"""
        matrix.update_risk_level(RiskLevel.HIGH)
        limit = matrix.get_sector_limit()
        assert limit == 0.20  # 收紧50%
    
    def test_get_sector_limit_critical(self, matrix):
        """测试极高风险时的行业限制"""
        matrix.update_risk_level(RiskLevel.CRITICAL)
        limit = matrix.get_sector_limit()
        assert limit == 0.0
    
    def test_get_stop_loss_threshold_low(self, matrix):
        """测试低风险时的止损阈值"""
        matrix.update_risk_level(RiskLevel.LOW)
        threshold = matrix.get_stop_loss_threshold()
        assert threshold == 0.10
    
    def test_get_stop_loss_threshold_medium(self, matrix):
        """测试中风险时的止损阈值"""
        matrix.update_risk_level(RiskLevel.MEDIUM)
        threshold = matrix.get_stop_loss_threshold()
        assert threshold == pytest.approx(0.08)  # 收紧20%
    
    def test_get_stop_loss_threshold_high(self, matrix):
        """测试高风险时的止损阈值"""
        matrix.update_risk_level(RiskLevel.HIGH)
        threshold = matrix.get_stop_loss_threshold()
        assert threshold == 0.05  # 收紧50%
    
    def test_get_stop_loss_threshold_critical(self, matrix):
        """测试极高风险时的止损阈值"""
        matrix.update_risk_level(RiskLevel.CRITICAL)
        threshold = matrix.get_stop_loss_threshold()
        assert threshold == 0.0  # 立即止损
    
    def test_get_margin_limit_low(self, matrix):
        """测试低风险时的保证金限制"""
        matrix.update_risk_level(RiskLevel.LOW)
        limit = matrix.get_margin_limit()
        assert limit == 0.30
    
    def test_get_margin_limit_medium(self, matrix):
        """测试中风险时的保证金限制"""
        matrix.update_risk_level(RiskLevel.MEDIUM)
        limit = matrix.get_margin_limit()
        assert limit == 0.24  # 收紧20%
    
    def test_get_margin_limit_high(self, matrix):
        """测试高风险时的保证金限制"""
        matrix.update_risk_level(RiskLevel.HIGH)
        limit = matrix.get_margin_limit()
        assert limit == 0.15  # 收紧50%
    
    def test_get_margin_limit_critical(self, matrix):
        """测试极高风险时的保证金限制"""
        matrix.update_risk_level(RiskLevel.CRITICAL)
        limit = matrix.get_margin_limit()
        assert limit == 0.0  # 禁止衍生品交易
    
    def test_can_open_position_low(self, matrix):
        """测试低风险时可以开仓"""
        matrix.update_risk_level(RiskLevel.LOW)
        assert matrix.can_open_position() is True
    
    def test_can_open_position_medium(self, matrix):
        """测试中风险时可以开仓"""
        matrix.update_risk_level(RiskLevel.MEDIUM)
        assert matrix.can_open_position() is True
    
    def test_can_open_position_high(self, matrix):
        """测试高风险时可以开仓"""
        matrix.update_risk_level(RiskLevel.HIGH)
        assert matrix.can_open_position() is True
    
    def test_can_open_position_critical(self, matrix):
        """测试极高风险时禁止开仓"""
        matrix.update_risk_level(RiskLevel.CRITICAL)
        assert matrix.can_open_position() is False
    
    def test_get_all_limits(self, matrix):
        """测试获取所有限制"""
        matrix.update_risk_level(RiskLevel.MEDIUM)
        limits = matrix.get_all_limits()
        
        assert 'position_limit' in limits
        assert 'sector_limit' in limits
        assert 'stop_loss_threshold' in limits
        assert 'margin_limit' in limits
        assert 'can_open_position' in limits
        assert 'risk_level' in limits
        assert limits['risk_level'] == 'medium'
    
    def test_get_limit_adjustment_ratio_low(self, matrix):
        """测试低风险时的调整比例"""
        matrix.update_risk_level(RiskLevel.LOW)
        ratio = matrix.get_limit_adjustment_ratio()
        assert ratio == 1.0
    
    def test_get_limit_adjustment_ratio_medium(self, matrix):
        """测试中风险时的调整比例"""
        matrix.update_risk_level(RiskLevel.MEDIUM)
        ratio = matrix.get_limit_adjustment_ratio()
        assert ratio == 0.80
    
    def test_get_limit_adjustment_ratio_high(self, matrix):
        """测试高风险时的调整比例"""
        matrix.update_risk_level(RiskLevel.HIGH)
        ratio = matrix.get_limit_adjustment_ratio()
        assert ratio == 0.50
    
    def test_get_limit_adjustment_ratio_critical(self, matrix):
        """测试极高风险时的调整比例"""
        matrix.update_risk_level(RiskLevel.CRITICAL)
        ratio = matrix.get_limit_adjustment_ratio()
        assert ratio == 0.0
    
    def test_reset_to_default(self, matrix):
        """测试重置为默认风险等级"""
        matrix.update_risk_level(RiskLevel.CRITICAL)
        assert matrix.current_risk_level == RiskLevel.CRITICAL
        
        matrix.reset_to_default()
        assert matrix.current_risk_level == RiskLevel.LOW
    
    def test_risk_level_transitions(self, matrix):
        """测试风险等级转换"""
        # LOW -> MEDIUM
        matrix.update_risk_level(RiskLevel.MEDIUM)
        assert matrix.get_position_limit() == pytest.approx(0.16)
        
        # MEDIUM -> HIGH
        matrix.update_risk_level(RiskLevel.HIGH)
        assert matrix.get_position_limit() == 0.10
        
        # HIGH -> CRITICAL
        matrix.update_risk_level(RiskLevel.CRITICAL)
        assert matrix.get_position_limit() == 0.0
        
        # CRITICAL -> LOW
        matrix.update_risk_level(RiskLevel.LOW)
        assert matrix.get_position_limit() == 0.20
