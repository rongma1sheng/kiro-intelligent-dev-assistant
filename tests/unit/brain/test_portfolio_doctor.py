"""
持仓诊断器单元测试

白皮书依据: 第一章 1.5.3 诊疗态任务调度
测试范围: PortfolioDoctor的持仓健康检查和风险暴露分析功能
"""

import pytest
from datetime import date
from unittest.mock import patch, MagicMock

from src.brain.portfolio_doctor import (
    PortfolioDoctor,
    Position,
    RiskExposure,
    DiagnosisReport,
    HealthStatus,
    RiskType
)


class TestPosition:
    """Position数据类测试"""
    
    def test_position_creation(self):
        """测试持仓创建"""
        position = Position(
            symbol="000001.SZ",
            quantity=1000,
            cost_price=10.0,
            current_price=11.0,
            sector="金融"
        )
        
        assert position.symbol == "000001.SZ"
        assert position.quantity == 1000
        assert position.cost_price == 10.0
        assert position.current_price == 11.0
        assert position.sector == "金融"
    
    def test_position_auto_calculate(self):
        """测试持仓自动计算"""
        position = Position(
            symbol="000001.SZ",
            quantity=1000,
            cost_price=10.0,
            current_price=11.0
        )
        
        # 自动计算市值
        assert position.market_value == 11000.0
        # 自动计算盈亏
        assert position.pnl == 1000.0
        # 自动计算盈亏比例
        assert position.pnl_ratio == 0.1
    
    def test_position_loss(self):
        """测试亏损持仓"""
        position = Position(
            symbol="000001.SZ",
            quantity=1000,
            cost_price=10.0,
            current_price=8.0
        )
        
        assert position.pnl == -2000.0
        assert position.pnl_ratio == -0.2
    
    def test_position_to_dict(self):
        """测试持仓转字典"""
        position = Position(
            symbol="000001.SZ",
            quantity=1000,
            cost_price=10.0,
            current_price=11.0
        )
        
        result = position.to_dict()
        
        assert result["symbol"] == "000001.SZ"
        assert result["quantity"] == 1000
        assert result["pnl"] == 1000.0


class TestRiskExposure:
    """RiskExposure数据类测试"""
    
    def test_risk_exposure_creation(self):
        """测试风险暴露创建"""
        risk = RiskExposure(
            risk_type=RiskType.CONCENTRATION,
            level=0.8,
            description="集中度过高",
            affected_positions=["000001.SZ"],
            suggestion="建议分散投资"
        )
        
        assert risk.risk_type == RiskType.CONCENTRATION
        assert risk.level == 0.8
        assert risk.description == "集中度过高"
        assert "000001.SZ" in risk.affected_positions
    
    def test_risk_exposure_to_dict(self):
        """测试风险暴露转字典"""
        risk = RiskExposure(
            risk_type=RiskType.SECTOR,
            level=0.6,
            description="行业集中"
        )
        
        result = risk.to_dict()
        
        assert result["risk_type"] == "行业风险"
        assert result["level"] == 0.6


class TestHealthStatus:
    """HealthStatus枚举测试"""
    
    def test_health_status_values(self):
        """测试健康状态枚举值"""
        assert HealthStatus.HEALTHY.value == "健康"
        assert HealthStatus.WARNING.value == "警告"
        assert HealthStatus.CRITICAL.value == "危险"
        assert HealthStatus.UNKNOWN.value == "未知"


class TestRiskType:
    """RiskType枚举测试"""
    
    def test_risk_type_values(self):
        """测试风险类型枚举值"""
        assert RiskType.CONCENTRATION.value == "集中度风险"
        assert RiskType.SECTOR.value == "行业风险"
        assert RiskType.LIQUIDITY.value == "流动性风险"
        assert RiskType.DRAWDOWN.value == "回撤风险"


class TestPortfolioDoctor:
    """PortfolioDoctor诊断器测试"""
    
    @pytest.fixture
    def doctor(self):
        """创建诊断器实例"""
        return PortfolioDoctor(
            concentration_threshold=0.3,
            sector_threshold=0.5,
            drawdown_threshold=0.1
        )
    
    @pytest.fixture
    def sample_positions(self):
        """创建示例持仓"""
        return [
            Position(
                symbol="000001.SZ",
                quantity=1000,
                cost_price=10.0,
                current_price=11.0,
                sector="金融"
            ),
            Position(
                symbol="600000.SH",
                quantity=500,
                cost_price=8.0,
                current_price=8.5,
                sector="金融"
            ),
            Position(
                symbol="000002.SZ",
                quantity=800,
                cost_price=15.0,
                current_price=14.0,
                sector="房地产"
            )
        ]
    
    def test_init_default(self):
        """测试默认初始化"""
        doctor = PortfolioDoctor()
        
        assert doctor.concentration_threshold == 0.3
        assert doctor.sector_threshold == 0.5
        assert doctor.drawdown_threshold == 0.1
    
    def test_init_custom(self):
        """测试自定义初始化"""
        doctor = PortfolioDoctor(
            concentration_threshold=0.2,
            sector_threshold=0.4,
            drawdown_threshold=0.15
        )
        
        assert doctor.concentration_threshold == 0.2
        assert doctor.sector_threshold == 0.4
        assert doctor.drawdown_threshold == 0.15
    
    def test_diagnose_empty_positions(self, doctor):
        """测试空持仓诊断"""
        report = doctor.diagnose([])
        
        assert report.total_positions == 0
        assert report.total_market_value == 0.0
        assert report.overall_status == HealthStatus.HEALTHY
    
    def test_diagnose_healthy_portfolio(self, doctor, sample_positions):
        """测试健康持仓诊断"""
        report = doctor.diagnose(sample_positions)
        
        assert report.total_positions == 3
        assert report.total_market_value > 0
        assert isinstance(report.overall_status, HealthStatus)
    
    def test_diagnose_concentration_risk(self, doctor):
        """测试集中度风险检测"""
        # 创建高集中度持仓
        positions = [
            Position(
                symbol="000001.SZ",
                quantity=10000,
                cost_price=10.0,
                current_price=10.0,
                sector="金融"
            ),
            Position(
                symbol="600000.SH",
                quantity=100,
                cost_price=10.0,
                current_price=10.0,
                sector="科技"
            )
        ]
        
        report = doctor.diagnose(positions)
        
        # 应该检测到集中度风险
        concentration_risks = [
            r for r in report.risk_exposures
            if r.risk_type == RiskType.CONCENTRATION
        ]
        assert len(concentration_risks) > 0
    
    def test_diagnose_sector_risk(self, doctor):
        """测试行业风险检测"""
        # 创建行业集中持仓
        positions = [
            Position(
                symbol="000001.SZ",
                quantity=1000,
                cost_price=10.0,
                current_price=10.0,
                sector="金融"
            ),
            Position(
                symbol="600000.SH",
                quantity=1000,
                cost_price=10.0,
                current_price=10.0,
                sector="金融"
            ),
            Position(
                symbol="601398.SH",
                quantity=1000,
                cost_price=10.0,
                current_price=10.0,
                sector="金融"
            )
        ]
        
        report = doctor.diagnose(positions)
        
        # 应该检测到行业风险
        sector_risks = [
            r for r in report.risk_exposures
            if r.risk_type == RiskType.SECTOR
        ]
        assert len(sector_risks) > 0
    
    def test_diagnose_drawdown_risk(self, doctor, sample_positions):
        """测试回撤风险检测"""
        # 创建有回撤的历史净值
        historical_values = [100, 105, 110, 95, 85, 80]  # 27%回撤
        
        report = doctor.diagnose(sample_positions, historical_values)
        
        # 应该检测到回撤风险
        drawdown_risks = [
            r for r in report.risk_exposures
            if r.risk_type == RiskType.DRAWDOWN
        ]
        assert len(drawdown_risks) > 0
    
    def test_diagnose_pnl_calculation(self, doctor, sample_positions):
        """测试盈亏计算"""
        report = doctor.diagnose(sample_positions)
        
        # 验证总盈亏计算
        expected_pnl = sum(p.pnl for p in sample_positions)
        assert report.total_pnl == expected_pnl
    
    def test_check_position_health_critical(self, doctor):
        """测试单个持仓健康检查 - 危险"""
        position = Position(
            symbol="000001.SZ",
            quantity=1000,
            cost_price=10.0,
            current_price=7.5  # 亏损25%
        )
        
        status, description = doctor.check_position_health(position)
        
        assert status == HealthStatus.CRITICAL
        assert "止损" in description
    
    def test_check_position_health_warning(self, doctor):
        """测试单个持仓健康检查 - 警告"""
        position = Position(
            symbol="000001.SZ",
            quantity=1000,
            cost_price=10.0,
            current_price=8.5  # 亏损15%
        )
        
        status, description = doctor.check_position_health(position)
        
        assert status == HealthStatus.WARNING
        assert "关注" in description
    
    def test_check_position_health_healthy(self, doctor):
        """测试单个持仓健康检查 - 健康"""
        position = Position(
            symbol="000001.SZ",
            quantity=1000,
            cost_price=10.0,
            current_price=11.0  # 盈利10%
        )
        
        status, description = doctor.check_position_health(position)
        
        assert status == HealthStatus.HEALTHY
    
    def test_get_sector_distribution(self, doctor, sample_positions):
        """测试获取行业分布"""
        doctor.diagnose(sample_positions)
        distribution = doctor.get_sector_distribution()
        
        assert "金融" in distribution
        assert "房地产" in distribution
        assert sum(distribution.values()) == pytest.approx(1.0, rel=0.01)
    
    def test_get_pnl_summary(self, doctor, sample_positions):
        """测试获取盈亏汇总"""
        doctor.diagnose(sample_positions)
        summary = doctor.get_pnl_summary()
        
        assert "total_pnl" in summary
        assert "winning_count" in summary
        assert "losing_count" in summary
        assert "win_rate" in summary
    
    def test_get_pnl_summary_empty(self, doctor):
        """测试空持仓盈亏汇总"""
        summary = doctor.get_pnl_summary()
        
        assert summary["total_pnl"] == 0.0
        assert summary["winning_count"] == 0
        assert summary["win_rate"] == 0.0


class TestDiagnosisReport:
    """DiagnosisReport报告类测试"""
    
    def test_report_creation(self):
        """测试报告创建"""
        report = DiagnosisReport(
            report_date=date.today(),
            overall_status=HealthStatus.HEALTHY,
            total_positions=5,
            total_market_value=100000.0,
            total_pnl=5000.0
        )
        
        assert report.report_date == date.today()
        assert report.overall_status == HealthStatus.HEALTHY
        assert report.total_positions == 5
    
    def test_report_to_dict(self):
        """测试报告转字典"""
        report = DiagnosisReport(
            report_date=date.today(),
            overall_status=HealthStatus.WARNING,
            total_positions=3
        )
        
        result = report.to_dict()
        
        assert result["overall_status"] == "警告"
        assert result["total_positions"] == 3
        assert "timestamp" in result


class TestPortfolioDoctorAsync:
    """异步功能测试"""
    
    @pytest.fixture
    def doctor(self):
        """创建诊断器实例"""
        return PortfolioDoctor()
    
    @pytest.fixture
    def sample_positions(self):
        """创建示例持仓"""
        return [
            Position(
                symbol="000001.SZ",
                quantity=1000,
                cost_price=10.0,
                current_price=11.0
            )
        ]
    
    @pytest.mark.asyncio
    async def test_diagnose_async(self, doctor, sample_positions):
        """测试异步诊断"""
        report = await doctor.diagnose_async(sample_positions)
        
        assert isinstance(report, DiagnosisReport)
        assert report.total_positions == 1
