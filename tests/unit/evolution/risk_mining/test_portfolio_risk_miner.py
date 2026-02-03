"""PortfolioRiskFactorMiner单元测试

白皮书依据: 第四章 4.1.1 专业风险因子挖掘系统 - 组合风险

测试覆盖:
1. 初始化参数验证
2. 持仓相关性收敛检测
3. 组合VaR超限检测
4. 行业集中度检测
5. 尾部风险暴露检测
6. 边界条件测试
7. 异常处理测试
"""

import pytest
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

from src.evolution.risk_mining.portfolio_risk_miner import PortfolioRiskFactorMiner
from src.evolution.risk_mining.risk_factor import RiskFactor


class TestPortfolioRiskFactorMinerInit:
    """测试初始化"""
    
    def test_init_default_params(self):
        """测试默认参数初始化"""
        miner = PortfolioRiskFactorMiner()
        
        assert miner.correlation_threshold == 0.85
        assert miner.var_threshold == 0.05
        assert miner.concentration_threshold == 0.3
        assert miner.tail_risk_threshold == 0.1
    
    def test_init_custom_params(self):
        """测试自定义参数初始化"""
        miner = PortfolioRiskFactorMiner(
            correlation_threshold=0.9,
            var_threshold=0.03,
            concentration_threshold=0.4,
            tail_risk_threshold=0.15
        )
        
        assert miner.correlation_threshold == 0.9
        assert miner.var_threshold == 0.03
        assert miner.concentration_threshold == 0.4
        assert miner.tail_risk_threshold == 0.15
    
    def test_init_invalid_correlation_threshold(self):
        """测试无效的相关性阈值"""
        with pytest.raises(ValueError, match="correlation_threshold必须在"):
            PortfolioRiskFactorMiner(correlation_threshold=1.5)
        
        with pytest.raises(ValueError, match="correlation_threshold必须在"):
            PortfolioRiskFactorMiner(correlation_threshold=-0.1)
    
    def test_init_invalid_var_threshold(self):
        """测试无效的VaR阈值"""
        with pytest.raises(ValueError, match="var_threshold必须在"):
            PortfolioRiskFactorMiner(var_threshold=1.5)
        
        with pytest.raises(ValueError, match="var_threshold必须在"):
            PortfolioRiskFactorMiner(var_threshold=-0.1)
    
    def test_init_invalid_concentration_threshold(self):
        """测试无效的集中度阈值"""
        with pytest.raises(ValueError, match="concentration_threshold必须在"):
            PortfolioRiskFactorMiner(concentration_threshold=1.5)
        
        with pytest.raises(ValueError, match="concentration_threshold必须在"):
            PortfolioRiskFactorMiner(concentration_threshold=-0.1)
    
    def test_init_invalid_tail_risk_threshold(self):
        """测试无效的尾部风险阈值"""
        with pytest.raises(ValueError, match="tail_risk_threshold必须在"):
            PortfolioRiskFactorMiner(tail_risk_threshold=1.5)
        
        with pytest.raises(ValueError, match="tail_risk_threshold必须在"):
            PortfolioRiskFactorMiner(tail_risk_threshold=-0.1)


class TestCorrelationConvergence:
    """测试持仓相关性收敛检测"""
    
    @pytest.fixture
    def miner(self):
        """创建挖掘器实例"""
        return PortfolioRiskFactorMiner(correlation_threshold=0.85)
    
    @pytest.fixture
    def high_correlation_returns(self):
        """创建高相关性收益率数据"""
        dates = pd.date_range('2024-01-01', periods=100, freq='D')
        base_returns = np.random.randn(100) * 0.02
        
        # 创建高相关性的收益率
        returns_data = pd.DataFrame({
            '000001': base_returns + np.random.randn(100) * 0.001,
            '000002': base_returns + np.random.randn(100) * 0.001,
            '000003': base_returns + np.random.randn(100) * 0.001,
        }, index=dates)
        
        return returns_data
    
    @pytest.fixture
    def low_correlation_returns(self):
        """创建低相关性收益率数据"""
        dates = pd.date_range('2024-01-01', periods=100, freq='D')
        
        # 创建低相关性的收益率
        returns_data = pd.DataFrame({
            '000001': np.random.randn(100) * 0.02,
            '000002': np.random.randn(100) * 0.02,
            '000003': np.random.randn(100) * 0.02,
        }, index=dates)
        
        return returns_data
    
    @pytest.mark.asyncio
    async def test_detect_high_correlation(self, miner, high_correlation_returns):
        """测试检测高相关性"""
        portfolio = {
            '000001': 0.4,
            '000002': 0.3,
            '000003': 0.3
        }
        
        factors = await miner.mine_portfolio_risk(portfolio, high_correlation_returns)
        
        # 应该检测到相关性收敛
        correlation_factors = [f for f in factors if f.metadata.get('risk_type') == 'correlation_convergence']
        assert len(correlation_factors) > 0
        
        factor = correlation_factors[0]
        assert factor.factor_type == 'portfolio'
        assert factor.symbol == 'PORTFOLIO'
        assert 0 <= factor.risk_value <= 1
        assert 0 <= factor.confidence <= 1
        assert 'avg_correlation' in factor.metadata
        assert 'max_correlation' in factor.metadata
    
    @pytest.mark.asyncio
    async def test_no_detection_low_correlation(self, miner, low_correlation_returns):
        """测试低相关性不触发检测"""
        portfolio = {
            '000001': 0.4,
            '000002': 0.3,
            '000003': 0.3
        }
        
        factors = await miner.mine_portfolio_risk(portfolio, low_correlation_returns)
        
        # 不应该检测到相关性收敛
        correlation_factors = [f for f in factors if f.metadata.get('risk_type') == 'correlation_convergence']
        assert len(correlation_factors) == 0
    
    @pytest.mark.asyncio
    async def test_single_holding_no_correlation(self, miner):
        """测试单个持仓无法计算相关性"""
        portfolio = {'000001': 1.0}
        returns_data = pd.DataFrame({
            '000001': np.random.randn(100) * 0.02
        }, index=pd.date_range('2024-01-01', periods=100, freq='D'))
        
        factors = await miner.mine_portfolio_risk(portfolio, returns_data)
        
        # 不应该检测到相关性收敛
        correlation_factors = [f for f in factors if f.metadata.get('risk_type') == 'correlation_convergence']
        assert len(correlation_factors) == 0


class TestVarBreach:
    """测试组合VaR超限检测"""
    
    @pytest.fixture
    def miner(self):
        """创建挖掘器实例"""
        return PortfolioRiskFactorMiner(var_threshold=0.05)
    
    @pytest.fixture
    def high_volatility_returns(self):
        """创建高波动率收益率数据"""
        dates = pd.date_range('2024-01-01', periods=100, freq='D')
        
        # 创建高波动率的收益率
        returns_data = pd.DataFrame({
            '000001': np.random.randn(100) * 0.1,  # 10%波动率
            '000002': np.random.randn(100) * 0.1,
            '000003': np.random.randn(100) * 0.1,
        }, index=dates)
        
        return returns_data
    
    @pytest.fixture
    def low_volatility_returns(self):
        """创建低波动率收益率数据"""
        dates = pd.date_range('2024-01-01', periods=100, freq='D')
        
        # 创建低波动率的收益率
        returns_data = pd.DataFrame({
            '000001': np.random.randn(100) * 0.01,  # 1%波动率
            '000002': np.random.randn(100) * 0.01,
            '000003': np.random.randn(100) * 0.01,
        }, index=dates)
        
        return returns_data
    
    @pytest.mark.asyncio
    async def test_detect_var_breach(self, miner, high_volatility_returns):
        """测试检测VaR超限"""
        portfolio = {
            '000001': 0.4,
            '000002': 0.3,
            '000003': 0.3
        }
        
        factors = await miner.mine_portfolio_risk(portfolio, high_volatility_returns)
        
        # 应该检测到VaR超限
        var_factors = [f for f in factors if f.metadata.get('risk_type') == 'var_breach']
        assert len(var_factors) > 0
        
        factor = var_factors[0]
        assert factor.factor_type == 'portfolio'
        assert factor.symbol == 'PORTFOLIO'
        assert 0 <= factor.risk_value <= 1
        assert 0 <= factor.confidence <= 1
        assert 'var_95' in factor.metadata
        assert factor.metadata['var_95'] > miner.var_threshold
    
    @pytest.mark.asyncio
    async def test_no_detection_low_var(self, miner, low_volatility_returns):
        """测试低VaR不触发检测"""
        portfolio = {
            '000001': 0.4,
            '000002': 0.3,
            '000003': 0.3
        }
        
        factors = await miner.mine_portfolio_risk(portfolio, low_volatility_returns)
        
        # 不应该检测到VaR超限
        var_factors = [f for f in factors if f.metadata.get('risk_type') == 'var_breach']
        assert len(var_factors) == 0


class TestSectorConcentration:
    """测试行业集中度检测"""
    
    @pytest.fixture
    def miner(self):
        """创建挖掘器实例"""
        return PortfolioRiskFactorMiner(concentration_threshold=0.3)
    
    @pytest.fixture
    def returns_data(self):
        """创建收益率数据"""
        dates = pd.date_range('2024-01-01', periods=100, freq='D')
        returns_data = pd.DataFrame({
            '000001': np.random.randn(100) * 0.02,
            '000002': np.random.randn(100) * 0.02,
            '000003': np.random.randn(100) * 0.02,
            '000004': np.random.randn(100) * 0.02,
        }, index=dates)
        return returns_data
    
    @pytest.mark.asyncio
    async def test_detect_high_concentration(self, miner, returns_data):
        """测试检测高集中度"""
        portfolio = {
            '000001': 0.4,  # 科技
            '000002': 0.35,  # 科技
            '000003': 0.15,  # 金融
            '000004': 0.1   # 消费
        }
        sector_mapping = {
            '000001': '科技',
            '000002': '科技',
            '000003': '金融',
            '000004': '消费'
        }
        
        factors = await miner.mine_portfolio_risk(
            portfolio, returns_data, sector_mapping
        )
        
        # 应该检测到行业集中度过高（科技75%）
        concentration_factors = [f for f in factors if f.metadata.get('risk_type') == 'sector_concentration']
        assert len(concentration_factors) > 0
        
        factor = concentration_factors[0]
        assert factor.factor_type == 'portfolio'
        assert factor.symbol == 'PORTFOLIO'
        assert 0 <= factor.risk_value <= 1
        assert 0 <= factor.confidence <= 1
        assert factor.metadata['max_sector'] == '科技'
        assert factor.metadata['max_weight'] == 0.75
    
    @pytest.mark.asyncio
    async def test_no_detection_low_concentration(self, miner, returns_data):
        """测试低集中度不触发检测"""
        portfolio = {
            '000001': 0.25,  # 科技
            '000002': 0.25,  # 金融
            '000003': 0.25,  # 消费
            '000004': 0.25   # 医药
        }
        sector_mapping = {
            '000001': '科技',
            '000002': '金融',
            '000003': '消费',
            '000004': '医药'
        }
        
        factors = await miner.mine_portfolio_risk(
            portfolio, returns_data, sector_mapping
        )
        
        # 不应该检测到行业集中度过高
        concentration_factors = [f for f in factors if f.metadata.get('risk_type') == 'sector_concentration']
        assert len(concentration_factors) == 0
    
    @pytest.mark.asyncio
    async def test_no_sector_mapping(self, miner, returns_data):
        """测试没有行业映射时不检测集中度"""
        portfolio = {
            '000001': 0.5,
            '000002': 0.5
        }
        
        factors = await miner.mine_portfolio_risk(portfolio, returns_data)
        
        # 不应该检测到行业集中度（没有提供sector_mapping）
        concentration_factors = [f for f in factors if f.metadata.get('risk_type') == 'sector_concentration']
        assert len(concentration_factors) == 0


class TestTailRisk:
    """测试尾部风险暴露检测"""
    
    @pytest.fixture
    def miner(self):
        """创建挖掘器实例"""
        return PortfolioRiskFactorMiner(tail_risk_threshold=0.1)
    
    @pytest.fixture
    def fat_tail_returns(self):
        """创建肥尾分布收益率数据"""
        dates = pd.date_range('2024-01-01', periods=100, freq='D')
        
        # 创建肥尾分布的收益率（正态分布 + 极端值）
        base_returns = np.random.randn(100) * 0.02
        # 添加几个极端负值
        base_returns[5] = -0.15
        base_returns[25] = -0.12
        base_returns[50] = -0.18
        
        returns_data = pd.DataFrame({
            '000001': base_returns,
            '000002': base_returns * 0.8,
            '000003': base_returns * 1.2,
        }, index=dates)
        
        return returns_data
    
    @pytest.fixture
    def normal_returns(self):
        """创建正态分布收益率数据"""
        dates = pd.date_range('2024-01-01', periods=100, freq='D')
        
        returns_data = pd.DataFrame({
            '000001': np.random.randn(100) * 0.02,
            '000002': np.random.randn(100) * 0.02,
            '000003': np.random.randn(100) * 0.02,
        }, index=dates)
        
        return returns_data
    
    @pytest.mark.asyncio
    async def test_detect_tail_risk(self, miner, fat_tail_returns):
        """测试检测尾部风险"""
        portfolio = {
            '000001': 0.4,
            '000002': 0.3,
            '000003': 0.3
        }
        
        factors = await miner.mine_portfolio_risk(portfolio, fat_tail_returns)
        
        # 应该检测到尾部风险
        tail_risk_factors = [f for f in factors if f.metadata.get('risk_type') == 'tail_risk']
        assert len(tail_risk_factors) > 0
        
        factor = tail_risk_factors[0]
        assert factor.factor_type == 'portfolio'
        assert factor.symbol == 'PORTFOLIO'
        assert 0 <= factor.risk_value <= 1
        assert 0 <= factor.confidence <= 1
        assert 'cvar_95' in factor.metadata
        assert 'var_95' in factor.metadata
        assert factor.metadata['cvar_95'] > miner.tail_risk_threshold
    
    @pytest.mark.asyncio
    async def test_no_detection_normal_tail(self, miner, normal_returns):
        """测试正态分布不触发尾部风险检测"""
        portfolio = {
            '000001': 0.4,
            '000002': 0.3,
            '000003': 0.3
        }
        
        factors = await miner.mine_portfolio_risk(portfolio, normal_returns)
        
        # 不应该检测到尾部风险
        tail_risk_factors = [f for f in factors if f.metadata.get('risk_type') == 'tail_risk']
        assert len(tail_risk_factors) == 0


class TestEdgeCases:
    """测试边界条件"""
    
    @pytest.fixture
    def miner(self):
        """创建挖掘器实例"""
        return PortfolioRiskFactorMiner()
    
    @pytest.mark.asyncio
    async def test_empty_portfolio(self, miner):
        """测试空持仓"""
        portfolio = {}
        returns_data = pd.DataFrame({
            '000001': np.random.randn(100) * 0.02
        }, index=pd.date_range('2024-01-01', periods=100, freq='D'))
        
        with pytest.raises(ValueError, match="portfolio不能为空"):
            await miner.mine_portfolio_risk(portfolio, returns_data)
    
    @pytest.mark.asyncio
    async def test_empty_returns_data(self, miner):
        """测试空收益率数据"""
        portfolio = {'000001': 1.0}
        returns_data = pd.DataFrame()
        
        with pytest.raises(ValueError, match="returns_data不能为空"):
            await miner.mine_portfolio_risk(portfolio, returns_data)
    
    @pytest.mark.asyncio
    async def test_invalid_weights_sum(self, miner):
        """测试权重之和不为1.0"""
        portfolio = {
            '000001': 0.5,
            '000002': 0.3
        }
        returns_data = pd.DataFrame({
            '000001': np.random.randn(100) * 0.02,
            '000002': np.random.randn(100) * 0.02
        }, index=pd.date_range('2024-01-01', periods=100, freq='D'))
        
        with pytest.raises(ValueError, match="权重之和必须为1.0"):
            await miner.mine_portfolio_risk(portfolio, returns_data)
    
    @pytest.mark.asyncio
    async def test_missing_symbols_in_returns(self, miner):
        """测试持仓标的在收益率数据中缺失"""
        portfolio = {
            '000001': 0.5,
            '000002': 0.5
        }
        returns_data = pd.DataFrame({
            '000001': np.random.randn(100) * 0.02
            # 缺少 000002
        }, index=pd.date_range('2024-01-01', periods=100, freq='D'))
        
        # 应该能正常运行，只使用可用的标的
        factors = await miner.mine_portfolio_risk(portfolio, returns_data)
        assert isinstance(factors, list)
    
    @pytest.mark.asyncio
    async def test_all_symbols_missing(self, miner):
        """测试所有持仓标的都缺失"""
        portfolio = {
            '000001': 0.5,
            '000002': 0.5
        }
        returns_data = pd.DataFrame({
            '000003': np.random.randn(100) * 0.02
        }, index=pd.date_range('2024-01-01', periods=100, freq='D'))
        
        # 应该返回空列表
        factors = await miner.mine_portfolio_risk(portfolio, returns_data)
        assert factors == []


class TestMultipleRisks:
    """测试多个风险同时触发"""
    
    @pytest.fixture
    def miner(self):
        """创建挖掘器实例"""
        return PortfolioRiskFactorMiner(
            correlation_threshold=0.85,
            var_threshold=0.05,
            concentration_threshold=0.3,
            tail_risk_threshold=0.1
        )
    
    @pytest.fixture
    def risky_returns(self):
        """创建高风险收益率数据"""
        dates = pd.date_range('2024-01-01', periods=100, freq='D')
        
        # 高相关性 + 高波动率 + 肥尾
        base_returns = np.random.randn(100) * 0.1
        base_returns[5] = -0.15
        base_returns[25] = -0.12
        
        returns_data = pd.DataFrame({
            '000001': base_returns + np.random.randn(100) * 0.001,
            '000002': base_returns + np.random.randn(100) * 0.001,
            '000003': base_returns + np.random.randn(100) * 0.001,
        }, index=dates)
        
        return returns_data
    
    @pytest.mark.asyncio
    async def test_multiple_risks_detected(self, miner, risky_returns):
        """测试同时检测到多个风险"""
        portfolio = {
            '000001': 0.5,  # 科技
            '000002': 0.3,  # 科技
            '000003': 0.2   # 金融
        }
        sector_mapping = {
            '000001': '科技',
            '000002': '科技',
            '000003': '金融'
        }
        
        factors = await miner.mine_portfolio_risk(
            portfolio, risky_returns, sector_mapping
        )
        
        # 应该检测到多个风险
        assert len(factors) >= 2
        
        # 验证所有因子都是portfolio类型
        for factor in factors:
            assert factor.factor_type == 'portfolio'
            assert factor.symbol == 'PORTFOLIO'
            assert 0 <= factor.risk_value <= 1
            assert 0 <= factor.confidence <= 1
            assert 'risk_type' in factor.metadata
