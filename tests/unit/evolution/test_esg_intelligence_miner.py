"""ESG智能因子挖掘器单元测试

白皮书依据: 第四章 4.1.10 ESG智能因子挖掘器

测试ESG智能因子挖掘器的所有功能，包括8种核心算子和分析方法。

Author: MIA Team
Date: 2026-01-25
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from src.evolution.esg_intelligence.esg_intelligence_miner import (
    ESGIntelligenceFactorMiner,
    ESGIntelligenceConfig
)
from src.evolution.esg_intelligence.esg_intelligence_operators import (
    ESGIntelligenceOperatorRegistry
)


@pytest.fixture
def sample_data():
    """生成测试数据"""
    dates = pd.date_range(start='2023-01-01', periods=300, freq='D')
    np.random.seed(42)
    
    data = pd.DataFrame({
        'close': 100 + np.cumsum(np.random.randn(300) * 0.5),
        'open': 100 + np.cumsum(np.random.randn(300) * 0.5),
        'high': 100 + np.cumsum(np.random.randn(300) * 0.5) + 1,
        'low': 100 + np.cumsum(np.random.randn(300) * 0.5) - 1,
        'volume': np.random.randint(1000000, 10000000, 300),
        'esg_score': np.random.uniform(0.3, 0.9, 300),
        'carbon_emission': 1000 + np.cumsum(np.random.randn(300) * 10),
        'employee_satisfaction': np.random.uniform(0.5, 0.9, 300),
        'board_diversity': np.random.uniform(0.3, 0.8, 300),
        'green_investment': np.random.uniform(0.1, 0.5, 300),
        'sustainability_score': np.random.uniform(0.4, 0.9, 300)
    }, index=dates)
    
    return data


@pytest.fixture
def sample_returns(sample_data):
    """生成收益率数据"""
    return sample_data['close'].pct_change().fillna(0)


@pytest.fixture
def esg_config():
    """生成ESG配置"""
    return ESGIntelligenceConfig(
        esg_threshold=0.6,
        controversy_threshold=0.5,
        carbon_reduction_target=0.05,
        sustainability_window=252
    )


@pytest.fixture
def operator_registry():
    """创建算子注册表"""
    return ESGIntelligenceOperatorRegistry()


@pytest.fixture
def esg_miner(esg_config):
    """创建ESG智能因子挖掘器"""
    return ESGIntelligenceFactorMiner(config=esg_config)


# ==================== 算子测试 ====================

class TestESGIntelligenceOperators:
    """测试ESG智能算子"""
    
    def test_esg_controversy_shock_with_data(self, operator_registry, sample_data):
        """测试ESG争议冲击算子（有ESG数据）"""
        sample_data['esg_controversy'] = np.random.uniform(0, 1, len(sample_data))
        result = operator_registry.esg_controversy_shock(sample_data)
        
        assert isinstance(result, pd.Series)
        assert len(result) == len(sample_data)
        assert not result.isna().all()
    
    def test_esg_controversy_shock_without_data(self, operator_registry, sample_data):
        """测试ESG争议冲击算子（无ESG数据，使用代理）"""
        result = operator_registry.esg_controversy_shock(sample_data)
        
        assert isinstance(result, pd.Series)
        assert len(result) == len(sample_data)
        assert result.min() >= 0  # 争议冲击应该是非负的
    
    def test_esg_controversy_shock_empty_data(self, operator_registry):
        """测试ESG争议冲击算子（空数据）"""
        empty_data = pd.DataFrame()
        result = operator_registry.esg_controversy_shock(empty_data)
        
        assert isinstance(result, pd.Series)
        assert len(result) == 0
    
    def test_carbon_emission_trend_with_data(self, operator_registry, sample_data):
        """测试碳排放趋势算子（有碳排放数据）"""
        result = operator_registry.carbon_emission_trend(sample_data)
        
        assert isinstance(result, pd.Series)
        assert len(result) == len(sample_data)
        assert not result.isna().all()
    
    def test_carbon_emission_trend_without_data(self, operator_registry):
        """测试碳排放趋势算子（无碳排放数据，使用代理）"""
        data = pd.DataFrame({
            'close': 100 + np.cumsum(np.random.randn(300) * 0.5)
        }, index=pd.date_range('2023-01-01', periods=300))
        
        result = operator_registry.carbon_emission_trend(data)
        
        assert isinstance(result, pd.Series)
        assert len(result) == len(data)
        assert result.abs().max() <= 5  # 应该被clip到[-5, 5]
    
    def test_employee_satisfaction_with_data(self, operator_registry, sample_data):
        """测试员工满意度算子（有满意度数据）"""
        result = operator_registry.employee_satisfaction(sample_data)
        
        assert isinstance(result, pd.Series)
        assert len(result) == len(sample_data)
        assert not result.isna().all()
    
    def test_employee_satisfaction_without_data(self, operator_registry):
        """测试员工满意度算子（无满意度数据，使用代理）"""
        data = pd.DataFrame({
            'close': 100 + np.cumsum(np.random.randn(300) * 0.5)
        }, index=pd.date_range('2023-01-01', periods=300))
        
        result = operator_registry.employee_satisfaction(data)
        
        assert isinstance(result, pd.Series)
        assert len(result) == len(data)
        assert result.abs().max() <= 3  # 应该被clip到[-3, 3]
    
    def test_board_diversity_score_with_data(self, operator_registry, sample_data):
        """测试董事会多样性算子（有多样性数据）"""
        result = operator_registry.board_diversity_score(sample_data)
        
        assert isinstance(result, pd.Series)
        assert len(result) == len(sample_data)
        assert not result.isna().all()
    
    def test_board_diversity_score_without_data(self, operator_registry):
        """测试董事会多样性算子（无多样性数据，使用代理）"""
        data = pd.DataFrame({
            'close': 100 + np.cumsum(np.random.randn(300) * 0.5)
        }, index=pd.date_range('2023-01-01', periods=300))
        
        result = operator_registry.board_diversity_score(data)
        
        assert isinstance(result, pd.Series)
        assert len(result) == len(data)
        assert result.abs().max() <= 3  # 应该被clip到[-3, 3]
    
    def test_green_investment_ratio_with_data(self, operator_registry, sample_data):
        """测试绿色投资比例算子（有绿色投资数据）"""
        result = operator_registry.green_investment_ratio(sample_data)
        
        assert isinstance(result, pd.Series)
        assert len(result) == len(sample_data)
        assert not result.isna().all()
    
    def test_green_investment_ratio_without_data(self, operator_registry):
        """测试绿色投资比例算子（无绿色投资数据，使用代理）"""
        data = pd.DataFrame({
            'close': 100 + np.cumsum(np.random.randn(300) * 0.5)
        }, index=pd.date_range('2023-01-01', periods=300))
        
        result = operator_registry.green_investment_ratio(data)
        
        assert isinstance(result, pd.Series)
        assert len(result) == len(data)
        assert result.abs().max() <= 5  # 应该被clip到[-5, 5]
    
    def test_esg_momentum_with_data(self, operator_registry, sample_data):
        """测试ESG改善动量算子（有ESG评分数据）"""
        result = operator_registry.esg_momentum(sample_data)
        
        assert isinstance(result, pd.Series)
        assert len(result) == len(sample_data)
        assert not result.isna().all()
    
    def test_esg_momentum_without_data(self, operator_registry):
        """测试ESG改善动量算子（无ESG数据，使用代理）"""
        data = pd.DataFrame({
            'close': 100 + np.cumsum(np.random.randn(300) * 0.5)
        }, index=pd.date_range('2023-01-01', periods=300))
        
        result = operator_registry.esg_momentum(data)
        
        assert isinstance(result, pd.Series)
        assert len(result) == len(data)
        assert result.abs().max() <= 3  # 应该被clip到[-3, 3]
    
    def test_sustainability_score_with_data(self, operator_registry, sample_data):
        """测试可持续性评分算子（有可持续性数据）"""
        result = operator_registry.sustainability_score(sample_data)
        
        assert isinstance(result, pd.Series)
        assert len(result) == len(sample_data)
        assert not result.isna().all()
    
    def test_sustainability_score_without_data(self, operator_registry):
        """测试可持续性评分算子（无可持续性数据，使用代理）"""
        data = pd.DataFrame({
            'close': 100 + np.cumsum(np.random.randn(300) * 0.5)
        }, index=pd.date_range('2023-01-01', periods=300))
        
        result = operator_registry.sustainability_score(data)
        
        assert isinstance(result, pd.Series)
        assert len(result) == len(data)
        assert result.abs().max() <= 3  # 应该被clip到[-3, 3]
    
    def test_esg_risk_premium_with_data(self, operator_registry, sample_data):
        """测试ESG风险溢价算子（有ESG评分数据）"""
        result = operator_registry.esg_risk_premium(sample_data)
        
        assert isinstance(result, pd.Series)
        assert len(result) == len(sample_data)
        assert not result.isna().all()
    
    def test_esg_risk_premium_without_data(self, operator_registry):
        """测试ESG风险溢价算子（无ESG数据，使用代理）"""
        data = pd.DataFrame({
            'close': 100 + np.cumsum(np.random.randn(300) * 0.5)
        }, index=pd.date_range('2023-01-01', periods=300))
        
        result = operator_registry.esg_risk_premium(data)
        
        assert isinstance(result, pd.Series)
        assert len(result) == len(data)
        assert result.abs().max() <= 3  # 应该被clip到[-3, 3]


# ==================== 配置测试 ====================

class TestESGIntelligenceConfig:
    """测试ESG智能配置"""
    
    def test_default_config(self):
        """测试默认配置"""
        config = ESGIntelligenceConfig()
        
        assert config.esg_threshold == 0.6
        assert config.controversy_threshold == 0.5
        assert config.carbon_reduction_target == 0.05
        assert config.sustainability_window == 252
    
    def test_custom_config(self):
        """测试自定义配置"""
        config = ESGIntelligenceConfig(
            esg_threshold=0.7,
            controversy_threshold=0.6,
            carbon_reduction_target=0.1,
            sustainability_window=180
        )
        
        assert config.esg_threshold == 0.7
        assert config.controversy_threshold == 0.6
        assert config.carbon_reduction_target == 0.1
        assert config.sustainability_window == 180
    
    def test_invalid_esg_threshold(self):
        """测试无效的ESG阈值"""
        with pytest.raises(ValueError, match="esg_threshold必须在\\[0, 1\\]范围内"):
            config = ESGIntelligenceConfig(esg_threshold=1.5)
            miner = ESGIntelligenceFactorMiner(config=config)
    
    def test_invalid_controversy_threshold(self):
        """测试无效的争议阈值"""
        with pytest.raises(ValueError, match="controversy_threshold必须在\\[0, 1\\]范围内"):
            config = ESGIntelligenceConfig(controversy_threshold=-0.1)
            miner = ESGIntelligenceFactorMiner(config=config)
    
    def test_invalid_carbon_reduction_target(self):
        """测试无效的碳减排目标"""
        with pytest.raises(ValueError, match="carbon_reduction_target必须在\\[0, 1\\]范围内"):
            config = ESGIntelligenceConfig(carbon_reduction_target=1.5)
            miner = ESGIntelligenceFactorMiner(config=config)
    
    def test_invalid_sustainability_window(self):
        """测试无效的可持续性窗口"""
        with pytest.raises(ValueError, match="sustainability_window必须 > 0"):
            config = ESGIntelligenceConfig(sustainability_window=0)
            miner = ESGIntelligenceFactorMiner(config=config)


# ==================== 挖掘器测试 ====================

class TestESGIntelligenceFactorMiner:
    """测试ESG智能因子挖掘器"""
    
    def test_initialization(self, esg_miner):
        """测试初始化"""
        assert esg_miner is not None
        assert esg_miner.esg_config is not None
        assert esg_miner.operator_registry is not None
        assert isinstance(esg_miner.esg_analysis, dict)
    
    def test_initialization_with_default_config(self):
        """测试使用默认配置初始化"""
        miner = ESGIntelligenceFactorMiner()
        
        assert miner.esg_config.esg_threshold == 0.6
        assert miner.esg_config.controversy_threshold == 0.5
    
    def test_operator_whitelist_extension(self, esg_miner):
        """测试算子白名单扩展"""
        expected_operators = [
            'esg_controversy_shock',
            'carbon_emission_trend',
            'employee_satisfaction',
            'board_diversity_score',
            'green_investment_ratio',
            'esg_momentum',
            'sustainability_score',
            'esg_risk_premium'
        ]
        
        for operator in expected_operators:
            assert operator in esg_miner.operator_whitelist
    
    def test_detect_esg_risks(self, esg_miner, sample_data):
        """测试ESG风险检测"""
        risks = esg_miner.detect_esg_risks(sample_data)
        
        assert isinstance(risks, pd.Series)
        assert len(risks) == len(sample_data)
        assert risks.dtype == int
        assert set(risks.unique()).issubset({0, 1})
    
    def test_detect_esg_risks_empty_data(self, esg_miner):
        """测试ESG风险检测（空数据）"""
        empty_data = pd.DataFrame()
        risks = esg_miner.detect_esg_risks(empty_data)
        
        assert isinstance(risks, pd.Series)
        assert len(risks) == 0
    
    def test_detect_esg_opportunities(self, esg_miner, sample_data):
        """测试ESG投资机会检测"""
        opportunities = esg_miner.detect_esg_opportunities(sample_data)
        
        assert isinstance(opportunities, pd.Series)
        assert len(opportunities) == len(sample_data)
        assert opportunities.dtype == int
        assert set(opportunities.unique()).issubset({0, 1})
    
    def test_detect_esg_opportunities_empty_data(self, esg_miner):
        """测试ESG投资机会检测（空数据）"""
        empty_data = pd.DataFrame()
        opportunities = esg_miner.detect_esg_opportunities(empty_data)
        
        assert isinstance(opportunities, pd.Series)
        assert len(opportunities) == 0
    
    def test_analyze_esg_impact(self, esg_miner, sample_data):
        """测试ESG影响分析"""
        impacts = esg_miner.analyze_esg_impact(sample_data)
        
        assert isinstance(impacts, dict)
        assert len(impacts) > 0
        
        expected_keys = [
            'carbon_trend',
            'green_investment',
            'employee_satisfaction',
            'board_diversity',
            'esg_momentum',
            'sustainability',
            'esg_premium',
            'controversy_shock'
        ]
        
        for key in expected_keys:
            assert key in impacts
            assert isinstance(impacts[key], pd.Series)
            assert len(impacts[key]) == len(sample_data)
    
    def test_analyze_esg_impact_empty_data(self, esg_miner):
        """测试ESG影响分析（空数据）"""
        empty_data = pd.DataFrame()
        impacts = esg_miner.analyze_esg_impact(empty_data)
        
        assert isinstance(impacts, dict)
        assert len(impacts) == 0
    
    def test_calculate_esg_composite_score(self, esg_miner, sample_data):
        """测试ESG综合评分"""
        composite_score = esg_miner.calculate_esg_composite_score(sample_data)
        
        assert isinstance(composite_score, pd.Series)
        assert len(composite_score) == len(sample_data)
        assert composite_score.abs().max() <= 1  # 应该在[-1, 1]范围内
    
    def test_calculate_esg_composite_score_empty_data(self, esg_miner):
        """测试ESG综合评分（空数据）"""
        empty_data = pd.DataFrame()
        composite_score = esg_miner.calculate_esg_composite_score(empty_data)
        
        assert isinstance(composite_score, pd.Series)
        assert len(composite_score) == 0
    
    def test_identify_esg_leaders(self, esg_miner, sample_data):
        """测试ESG领先企业识别"""
        leaders = esg_miner.identify_esg_leaders(sample_data, threshold=0.5)
        
        assert isinstance(leaders, list)
        
        for leader in leaders:
            assert 'date' in leader
            assert 'score' in leader
            assert 'rank' in leader
            assert 'magnitude' in leader
            assert leader['rank'] == 'leader'
            assert leader['score'] > 0.5
    
    def test_identify_esg_leaders_empty_data(self, esg_miner):
        """测试ESG领先企业识别（空数据）"""
        empty_data = pd.DataFrame()
        leaders = esg_miner.identify_esg_leaders(empty_data)
        
        assert isinstance(leaders, list)
        assert len(leaders) == 0
    
    @pytest.mark.asyncio
    async def test_mine_factors(self, esg_miner, sample_data, sample_returns):
        """测试因子挖掘"""
        factors = await esg_miner.mine_factors(
            data=sample_data,
            returns=sample_returns,
            generations=2
        )
        
        assert isinstance(factors, list)
        assert len(factors) > 0
        assert len(factors) <= 10  # 返回前10个最优因子
        
        for factor in factors:
            assert hasattr(factor, 'expression')
            assert hasattr(factor, 'fitness')
    
    @pytest.mark.asyncio
    async def test_mine_factors_empty_data(self, esg_miner):
        """测试因子挖掘（空数据）"""
        empty_data = pd.DataFrame()
        empty_returns = pd.Series()
        
        with pytest.raises(ValueError, match="输入数据为空"):
            await esg_miner.mine_factors(
                data=empty_data,
                returns=empty_returns,
                generations=2
            )
    
    def test_get_esg_report(self, esg_miner):
        """测试ESG分析报告"""
        report = esg_miner.get_esg_report()
        
        assert isinstance(report, dict)
        assert 'total_esg_analysis' in report
        assert 'analysis_by_type' in report
        assert 'esg_threshold' in report
        assert 'controversy_threshold' in report
        assert 'carbon_reduction_target' in report
        assert 'sustainability_window' in report
        
        assert report['esg_threshold'] == 0.6
        assert report['controversy_threshold'] == 0.5
        assert report['carbon_reduction_target'] == 0.05
        assert report['sustainability_window'] == 252


# ==================== 集成测试 ====================

class TestESGIntelligenceIntegration:
    """测试ESG智能因子挖掘器集成"""
    
    @pytest.mark.asyncio
    async def test_full_pipeline(self, esg_miner, sample_data, sample_returns):
        """测试完整流程"""
        # 1. 检测ESG风险
        risks = esg_miner.detect_esg_risks(sample_data)
        assert len(risks) == len(sample_data)
        
        # 2. 检测ESG投资机会
        opportunities = esg_miner.detect_esg_opportunities(sample_data)
        assert len(opportunities) == len(sample_data)
        
        # 3. 分析ESG影响
        impacts = esg_miner.analyze_esg_impact(sample_data)
        assert len(impacts) > 0
        
        # 4. 计算ESG综合评分
        composite_score = esg_miner.calculate_esg_composite_score(sample_data)
        assert len(composite_score) == len(sample_data)
        
        # 5. 识别ESG领先企业
        leaders = esg_miner.identify_esg_leaders(sample_data)
        assert isinstance(leaders, list)
        
        # 6. 挖掘因子
        factors = await esg_miner.mine_factors(
            data=sample_data,
            returns=sample_returns,
            generations=2
        )
        assert len(factors) > 0
        
        # 7. 获取报告
        report = esg_miner.get_esg_report()
        assert isinstance(report, dict)
    
    def test_esg_analysis_consistency(self, esg_miner, sample_data):
        """测试ESG分析一致性"""
        # 多次分析应该得到相同结果
        impacts1 = esg_miner.analyze_esg_impact(sample_data)
        impacts2 = esg_miner.analyze_esg_impact(sample_data)
        
        for key in impacts1.keys():
            pd.testing.assert_series_equal(impacts1[key], impacts2[key])
    
    def test_esg_score_range(self, esg_miner, sample_data):
        """测试ESG评分范围"""
        composite_score = esg_miner.calculate_esg_composite_score(sample_data)
        
        # ESG综合评分应该在合理范围内
        assert composite_score.min() >= -1
        assert composite_score.max() <= 1
    
    def test_esg_risk_opportunity_balance(self, esg_miner, sample_data):
        """测试ESG风险和机会的平衡"""
        risks = esg_miner.detect_esg_risks(sample_data)
        opportunities = esg_miner.detect_esg_opportunities(sample_data)
        
        # 风险和机会不应该同时出现在同一时刻
        risk_opportunity_overlap = (risks & opportunities).sum()
        
        # 允许少量重叠（由于不同指标的独立性）
        assert risk_opportunity_overlap < len(sample_data) * 0.1
