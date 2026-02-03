"""
归因分析器测试

测试覆盖:
- AlphaBetaDecomposition数据模型
- StrategyContribution数据模型  
- FactorExposure数据模型
- SectorAttribution数据模型
- AttributionAnalyzer核心功能
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime, date
from typing import Dict, List, Any

from src.brain.analyzers.attribution_analyzer import (
    AttributionType,
    AlphaBetaDecomposition,
    StrategyContribution,
    FactorExposure,
    SectorAttribution,
    AttributionReport,
    AttributionAnalyzer
)


class TestAlphaBetaDecomposition:
    """Alpha/Beta分解测试"""
    
    def test_alpha_beta_decomposition_creation(self):
        """测试Alpha/Beta分解对象创建"""
        decomp = AlphaBetaDecomposition(
            alpha=0.02,
            beta=1.1,
            benchmark_return=0.08,
            portfolio_return=0.10,
            tracking_error=0.05,
            information_ratio=0.4,
            r_squared=0.85
        )
        
        assert decomp.alpha == 0.02
        assert decomp.beta == 1.1
        assert decomp.benchmark_return == 0.08
        assert decomp.portfolio_return == 0.10
        assert decomp.tracking_error == 0.05
        assert decomp.information_ratio == 0.4
        assert decomp.r_squared == 0.85
    
    def test_alpha_beta_decomposition_defaults(self):
        """测试Alpha/Beta分解默认值"""
        decomp = AlphaBetaDecomposition(
            alpha=0.02,
            beta=1.1,
            benchmark_return=0.08,
            portfolio_return=0.10
        )
        
        assert decomp.tracking_error == 0.0
        assert decomp.information_ratio == 0.0
        assert decomp.r_squared == 0.0
    
    def test_alpha_beta_to_dict(self):
        """测试Alpha/Beta分解转字典"""
        decomp = AlphaBetaDecomposition(
            alpha=0.02,
            beta=1.1,
            benchmark_return=0.08,
            portfolio_return=0.10,
            tracking_error=0.05
        )
        
        result = decomp.to_dict()
        
        expected = {
            "alpha": 0.02,
            "beta": 1.1,
            "benchmark_return": 0.08,
            "portfolio_return": 0.10,
            "tracking_error": 0.05,
            "information_ratio": 0.0,
            "r_squared": 0.0
        }
        
        assert result == expected


class TestStrategyContribution:
    """策略贡献测试"""
    
    def test_strategy_contribution_creation(self):
        """测试策略贡献对象创建"""
        contrib = StrategyContribution(
            strategy_name="momentum_strategy",
            return_contribution=0.03,
            weight=0.4,
            sharpe_ratio=1.2,
            win_rate=0.65,
            trade_count=150
        )
        
        assert contrib.strategy_name == "momentum_strategy"
        assert contrib.return_contribution == 0.03
        assert contrib.weight == 0.4
        assert contrib.sharpe_ratio == 1.2
        assert contrib.win_rate == 0.65
        assert contrib.trade_count == 150
    
    def test_strategy_contribution_defaults(self):
        """测试策略贡献默认值"""
        contrib = StrategyContribution(
            strategy_name="test_strategy",
            return_contribution=0.02
        )
        
        assert contrib.weight == 0.0
        assert contrib.sharpe_ratio == 0.0
        assert contrib.win_rate == 0.0
        assert contrib.trade_count == 0
    
    def test_strategy_contribution_to_dict(self):
        """测试策略贡献转字典"""
        contrib = StrategyContribution(
            strategy_name="test_strategy",
            return_contribution=0.02,
            weight=0.3,
            sharpe_ratio=1.0
        )
        
        result = contrib.to_dict()
        
        expected = {
            "strategy_name": "test_strategy",
            "return_contribution": 0.02,
            "weight": 0.3,
            "sharpe_ratio": 1.0,
            "win_rate": 0.0,
            "trade_count": 0
        }
        
        assert result == expected


class TestFactorExposure:
    """因子暴露测试"""
    
    def test_factor_exposure_creation(self):
        """测试因子暴露对象创建"""
        exposure = FactorExposure(
            factor_name="momentum",
            exposure=0.5,
            return_contribution=0.02,
            t_stat=2.5,
            is_significant=True
        )
        
        assert exposure.factor_name == "momentum"
        assert exposure.exposure == 0.5
        assert exposure.return_contribution == 0.02
        assert exposure.t_stat == 2.5
        assert exposure.is_significant is True
    
    def test_factor_exposure_defaults(self):
        """测试因子暴露默认值"""
        exposure = FactorExposure(
            factor_name="value",
            exposure=0.3
        )
        
        assert exposure.return_contribution == 0.0
        assert exposure.t_stat == 0.0
        assert exposure.is_significant is False
    
    def test_factor_exposure_to_dict(self):
        """测试因子暴露转字典"""
        exposure = FactorExposure(
            factor_name="quality",
            exposure=0.4,
            return_contribution=0.015,
            t_stat=1.8
        )
        
        result = exposure.to_dict()
        
        expected = {
            "factor_name": "quality",
            "exposure": 0.4,
            "return_contribution": 0.015,
            "t_stat": 1.8,
            "is_significant": False
        }
        
        assert result == expected


class TestSectorAttribution:
    """行业归因测试"""
    
    def test_sector_attribution_creation(self):
        """测试行业归因对象创建"""
        attribution = SectorAttribution(
            sector="Technology",
            allocation_effect=0.02,
            selection_effect=0.015,
            interaction_effect=0.005
        )
        
        assert attribution.sector == "Technology"
        assert attribution.allocation_effect == 0.02
        assert attribution.selection_effect == 0.015
        assert attribution.interaction_effect == 0.005
        # total_effect应该在__post_init__中计算
        assert attribution.total_effect == 0.04  # 0.02 + 0.015 + 0.005
    
    def test_sector_attribution_defaults(self):
        """测试行业归因默认值"""
        attribution = SectorAttribution(
            sector="Finance",
            allocation_effect=0.01,
            selection_effect=0.02
        )
        
        assert attribution.interaction_effect == 0.0
        assert attribution.total_effect == 0.03  # 0.01 + 0.02 + 0.0
    
    def test_sector_attribution_to_dict(self):
        """测试行业归因转字典"""
        attribution = SectorAttribution(
            sector="Healthcare",
            allocation_effect=0.015,
            selection_effect=0.01,
            interaction_effect=0.002
        )
        
        result = attribution.to_dict()
        
        expected = {
            "sector": "Healthcare",
            "allocation_effect": 0.015,
            "selection_effect": 0.01,
            "interaction_effect": 0.002,
            "total_effect": 0.027
        }
        
        # 使用pytest.approx处理浮点数精度问题
        assert result["sector"] == expected["sector"]
        assert result["allocation_effect"] == pytest.approx(expected["allocation_effect"])
        assert result["selection_effect"] == pytest.approx(expected["selection_effect"])
        assert result["interaction_effect"] == pytest.approx(expected["interaction_effect"])
        assert result["total_effect"] == pytest.approx(expected["total_effect"])


class TestAttributionReport:
    """归因分析报告测试"""
    
    def test_attribution_report_creation(self):
        """测试归因报告创建"""
        from datetime import date, datetime
        
        report_date = date(2024, 1, 15)
        period_start = date(2024, 1, 1)
        period_end = date(2024, 1, 15)
        
        alpha_beta = AlphaBetaDecomposition(
            alpha=0.02, beta=1.1, benchmark_return=0.08, portfolio_return=0.10
        )
        
        report = AttributionReport(
            report_date=report_date,
            period_start=period_start,
            period_end=period_end,
            alpha_beta=alpha_beta,
            total_return=0.10,
            benchmark_return=0.08,
            excess_return=0.02
        )
        
        assert report.report_date == report_date
        assert report.period_start == period_start
        assert report.period_end == period_end
        assert report.alpha_beta == alpha_beta
        assert report.total_return == 0.10
        assert report.benchmark_return == 0.08
        assert report.excess_return == 0.02
        assert isinstance(report.timestamp, datetime)
    
    def test_attribution_report_defaults(self):
        """测试归因报告默认值"""
        from datetime import date
        
        report = AttributionReport(
            report_date=date.today(),
            period_start=date.today(),
            period_end=date.today()
        )
        
        assert report.alpha_beta is None
        assert report.strategy_contributions == []
        assert report.factor_exposures == []
        assert report.sector_attributions == []
        assert report.total_return == 0.0
        assert report.benchmark_return == 0.0
        assert report.excess_return == 0.0
    
    def test_attribution_report_to_dict(self):
        """测试归因报告转字典"""
        from datetime import date
        
        report_date = date(2024, 1, 15)
        period_start = date(2024, 1, 1)
        period_end = date(2024, 1, 15)
        
        report = AttributionReport(
            report_date=report_date,
            period_start=period_start,
            period_end=period_end,
            total_return=0.05
        )
        
        result = report.to_dict()
        
        assert result["report_date"] == "2024-01-15"
        assert result["period_start"] == "2024-01-01"
        assert result["period_end"] == "2024-01-15"
        assert result["alpha_beta"] is None
        assert result["strategy_contributions"] == []
        assert result["factor_exposures"] == []
        assert result["sector_attributions"] == []
        assert result["total_return"] == 0.05


class TestAttributionType:
    """归因类型枚举测试"""
    
    def test_attribution_type_values(self):
        """测试归因类型枚举值"""
        assert AttributionType.ALPHA_BETA.value == "Alpha/Beta分解"
        assert AttributionType.STRATEGY.value == "策略贡献"
        assert AttributionType.FACTOR.value == "因子暴露"
        assert AttributionType.SECTOR.value == "行业归因"
        assert AttributionType.TIMING.value == "择时归因"
        assert AttributionType.SELECTION.value == "选股归因"
    
    def test_attribution_type_membership(self):
        """测试归因类型成员检查"""
        assert AttributionType.ALPHA_BETA in AttributionType
        assert AttributionType.STRATEGY in AttributionType
        assert AttributionType.FACTOR in AttributionType


class TestAttributionAnalyzer:
    """归因分析器测试"""
    
    @pytest.fixture
    def analyzer(self):
        """归因分析器夹具"""
        return AttributionAnalyzer(risk_free_rate=0.03, significance_level=0.05)
    
    def test_analyzer_creation(self, analyzer):
        """测试分析器创建"""
        assert analyzer is not None
        assert analyzer.risk_free_rate == 0.03
        assert analyzer.significance_level == 0.05
        assert hasattr(analyzer, 'analyze')
        assert hasattr(analyzer, '_decompose_alpha_beta')
        assert hasattr(analyzer, '_analyze_strategy_contributions')
        assert hasattr(analyzer, '_analyze_factor_exposures')
    
    def test_analyzer_default_creation(self):
        """测试分析器默认参数创建"""
        analyzer = AttributionAnalyzer()
        assert analyzer.risk_free_rate == 0.03
        assert analyzer.significance_level == 0.05
    
    def test_decompose_alpha_beta(self, analyzer):
        """测试Alpha/Beta分解"""
        portfolio_returns = [0.01, 0.02, -0.01, 0.03, 0.015]
        benchmark_returns = [0.008, 0.015, -0.005, 0.025, 0.012]
        
        result = analyzer._decompose_alpha_beta(portfolio_returns, benchmark_returns)
        
        assert isinstance(result, AlphaBetaDecomposition)
        assert isinstance(result.alpha, float)
        assert isinstance(result.beta, float)
        assert result.portfolio_return != 0
        assert result.benchmark_return != 0
        assert result.tracking_error >= 0
        assert result.r_squared >= 0
    
    def test_decompose_alpha_beta_empty_data(self, analyzer):
        """测试空数据的Alpha/Beta分解"""
        result = analyzer._decompose_alpha_beta([], [])
        
        assert result.alpha == 0.0
        assert result.beta == 1.0
        assert result.benchmark_return == 0.0
        assert result.portfolio_return == 0.0
    
    def test_analyze_strategy_contributions(self, analyzer):
        """测试策略贡献分析"""
        strategy_returns = {
            "momentum": [0.01, 0.02, 0.015],
            "value": [0.008, 0.012, 0.01],
            "quality": [0.005, 0.008, 0.006]
        }
        portfolio_returns = [0.023, 0.04, 0.031]
        
        result = analyzer._analyze_strategy_contributions(strategy_returns, portfolio_returns)
        
        assert isinstance(result, list)
        assert len(result) == 3
        assert all(isinstance(contrib, StrategyContribution) for contrib in result)
        
        # 检查权重分配
        total_weight = sum(contrib.weight for contrib in result)
        assert abs(total_weight - 1.0) < 0.001  # 应该接近1.0
        
        # 检查排序（按贡献降序）
        contributions = [contrib.return_contribution for contrib in result]
        assert contributions == sorted(contributions, reverse=True)
    
    def test_analyze_factor_exposures(self, analyzer):
        """测试因子暴露分析"""
        portfolio_returns = [0.01, 0.02, -0.01, 0.03]
        factor_returns = {
            "momentum": [0.008, 0.015, -0.005, 0.025],
            "value": [0.005, 0.01, -0.002, 0.015],
            "size": [0.003, 0.008, -0.001, 0.012]
        }
        
        result = analyzer._analyze_factor_exposures(portfolio_returns, factor_returns)
        
        assert isinstance(result, list)
        assert len(result) == 3
        assert all(isinstance(exposure, FactorExposure) for exposure in result)
        
        # 检查排序（按暴露度绝对值降序）
        exposures = [abs(exposure.exposure) for exposure in result]
        assert exposures == sorted(exposures, reverse=True)
        
        # 检查显著性判断
        for exposure in result:
            if abs(exposure.t_stat) > 2.0:
                assert exposure.is_significant
            else:
                assert not exposure.is_significant
    
    def test_analyze_sector_attribution(self, analyzer):
        """测试行业归因分析"""
        sector_data = {
            "Technology": {
                "portfolio_weight": 0.4,
                "benchmark_weight": 0.3,
                "portfolio_return": 0.05,
                "benchmark_return": 0.04
            },
            "Finance": {
                "portfolio_weight": 0.3,
                "benchmark_weight": 0.35,
                "portfolio_return": 0.03,
                "benchmark_return": 0.035
            }
        }
        
        result = analyzer._analyze_sector_attribution(sector_data)
        
        assert isinstance(result, list)
        assert len(result) == 2
        assert all(isinstance(attr, SectorAttribution) for attr in result)
        
        # 验证Brinson模型计算
        tech_attr = next(attr for attr in result if attr.sector == "Technology")
        expected_allocation = (0.4 - 0.3) * 0.04  # 0.004
        expected_selection = 0.3 * (0.05 - 0.04)  # 0.003
        expected_interaction = (0.4 - 0.3) * (0.05 - 0.04)  # 0.001
        
        assert abs(tech_attr.allocation_effect - expected_allocation) < 0.0001
        assert abs(tech_attr.selection_effect - expected_selection) < 0.0001
        assert abs(tech_attr.interaction_effect - expected_interaction) < 0.0001
    
    def test_calculate_sharpe_ratio(self, analyzer):
        """测试夏普比率计算"""
        returns = [0.01, 0.02, -0.01, 0.03, 0.015]
        
        # 测试年化夏普比率
        sharpe_annual = analyzer.calculate_sharpe_ratio(returns, annualize=True)
        assert isinstance(sharpe_annual, float)
        
        # 测试非年化夏普比率
        sharpe_daily = analyzer.calculate_sharpe_ratio(returns, annualize=False)
        assert isinstance(sharpe_daily, float)
        
        # 年化版本应该更大（乘以sqrt(252)）
        assert abs(sharpe_annual - sharpe_daily * (252**0.5)) < 0.0001
    
    def test_calculate_sharpe_ratio_empty_returns(self, analyzer):
        """测试空收益序列的夏普比率"""
        assert analyzer.calculate_sharpe_ratio([]) == 0.0
    
    def test_calculate_sharpe_ratio_zero_std(self, analyzer):
        """测试零标准差的夏普比率"""
        returns = [0.01, 0.01, 0.01, 0.01]  # 相同收益
        sharpe = analyzer.calculate_sharpe_ratio(returns)
        assert sharpe == 0.0
    
    def test_calculate_information_ratio(self, analyzer):
        """测试信息比率计算"""
        portfolio_returns = [0.01, 0.02, -0.01, 0.03, 0.015]
        benchmark_returns = [0.008, 0.015, -0.005, 0.025, 0.012]
        
        ir = analyzer.calculate_information_ratio(portfolio_returns, benchmark_returns)
        assert isinstance(ir, float)
    
    def test_calculate_information_ratio_empty_data(self, analyzer):
        """测试空数据的信息比率"""
        assert analyzer.calculate_information_ratio([], []) == 0.0
        assert analyzer.calculate_information_ratio([0.01], []) == 0.0
    
    def test_analyze_full_report(self, analyzer):
        """测试完整归因分析"""
        from datetime import date
        
        portfolio_returns = [0.01, 0.02, -0.01, 0.03, 0.015]
        benchmark_returns = [0.008, 0.015, -0.005, 0.025, 0.012]
        
        strategy_returns = {
            "momentum": [0.005, 0.01, -0.002, 0.015, 0.008],
            "value": [0.003, 0.008, -0.003, 0.01, 0.005]
        }
        
        factor_returns = {
            "size": [0.002, 0.005, -0.001, 0.008, 0.003],
            "value": [0.004, 0.007, -0.002, 0.012, 0.006]
        }
        
        sector_data = {
            "Technology": {
                "portfolio_weight": 0.4,
                "benchmark_weight": 0.3,
                "portfolio_return": 0.05,
                "benchmark_return": 0.04
            }
        }
        
        report = analyzer.analyze(
            portfolio_returns=portfolio_returns,
            benchmark_returns=benchmark_returns,
            strategy_returns=strategy_returns,
            factor_returns=factor_returns,
            sector_data=sector_data,
            period_start=date(2024, 1, 1),
            period_end=date(2024, 1, 31)
        )
        
        assert isinstance(report, AttributionReport)
        assert report.alpha_beta is not None
        assert len(report.strategy_contributions) == 2
        assert len(report.factor_exposures) == 2
        assert len(report.sector_attributions) == 1
        assert report.total_return != 0
        assert report.benchmark_return != 0
        assert report.excess_return == report.total_return - report.benchmark_return
    
    @pytest.mark.asyncio
    async def test_analyze_async(self, analyzer):
        """测试异步归因分析"""
        portfolio_returns = [0.01, 0.02, -0.01, 0.03]
        benchmark_returns = [0.008, 0.015, -0.005, 0.025]
        
        report = await analyzer.analyze_async(portfolio_returns, benchmark_returns)
        
        assert isinstance(report, AttributionReport)
        assert report.alpha_beta is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])