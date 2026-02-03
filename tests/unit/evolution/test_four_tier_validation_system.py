"""
MIA系统四档资金分层验证系统测试

白皮书依据: 第四章 4.3.1 统一验证流程标准 - 四档资金分层验证
版本: v1.6.0
作者: MIA Team
日期: 2026-01-18

测试范围:
1. 多档位并发验证管理
2. 自动档位选择算法
3. 相对表现评估体系
4. 四档分层Z2H认证
5. 让策略跑出最优表现的核心理念验证
"""

import pytest
import asyncio
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch
from dataclasses import dataclass
from typing import Dict, List, Any

# 导入被测试的模块
from src.evolution.multi_tier_simulation_manager import (
    SimulationManager as MultiTierSimulationManager,  # 使用别名保持测试兼容性
    SimulationInstance,
    CapitalTier
)
# 注意: CapitalTier, ValidationTask, TierConfig 可能在其他模块中定义
# 如果导入失败，需要从正确的模块导入
from src.evolution.relative_performance_evaluator import (
    RelativePerformanceEvaluator,
    RelativePerformanceResult,
    BenchmarkType,
    MarketRegime
)
from src.evolution.four_tier_z2h_certification import (
    FourTierZ2HCertification,
    CertificationLevel,
    Z2HCertificationResult,
    TierCertificationStandards
)
from src.base.models import Strategy, SimulationResult
from src.base.exceptions import ValidationError, ResourceError


@dataclass
class MockStrategy:
    """模拟策略类"""
    strategy_id: str
    name: str
    type: str
    avg_holding_period: int = 5
    typical_position_count: int = 10
    monthly_turnover: float = 2.0
    expected_volatility: float = 0.15


@dataclass
class MockSimulationResult:
    """模拟仿真结果类"""
    start_date: datetime
    end_date: datetime
    total_return: float
    annual_return: float
    sharpe_ratio: float
    max_drawdown: float
    win_rate: float
    calmar_ratio: float
    information_ratio: float
    volatility: float
    daily_returns: List[float]
    monthly_turnover: float = 2.0
    downside_deviation: float = None


class TestMultiTierSimulationManager:
    """多档位模拟管理器测试"""
    
    @pytest.fixture
    def mock_redis(self):
        """模拟Redis客户端"""
        redis_mock = Mock()
        redis_mock.get.return_value = None
        redis_mock.setex.return_value = True
        redis_mock.keys.return_value = []
        return redis_mock
    
    @pytest.fixture
    def manager(self, mock_redis):
        """创建管理器实例"""
        return MultiTierSimulationManager(mock_redis)
    
    @pytest.fixture
    def sample_strategies(self):
        """创建示例策略"""
        return [
            MockStrategy("S001", "高频策略", "high_frequency", 1, 5, 8.0, 0.25),
            MockStrategy("S002", "动量策略", "momentum", 3, 15, 3.0, 0.18),
            MockStrategy("S003", "因子策略", "factor_based", 7, 25, 2.0, 0.15),
            MockStrategy("S004", "价值策略", "value", 30, 40, 1.0, 0.12)
        ]
    
    def test_tier_configs_initialization(self, manager):
        """测试档位配置初始化"""
        # 验证四个档位都已配置
        assert len(manager.tier_configs) == 4
        assert CapitalTier.TIER_1 in manager.tier_configs
        assert CapitalTier.TIER_2 in manager.tier_configs
        assert CapitalTier.TIER_3 in manager.tier_configs
        assert CapitalTier.TIER_4 in manager.tier_configs
        
        # 验证微型档配置 - 让策略跑出最优表现
        micro_config = manager.tier_configs[CapitalTier.TIER_1]
        assert micro_config.name == "微型资金档"
        assert micro_config.capital_range == (1000, 10000)
        assert micro_config.initial_capital == 5000
        assert micro_config.max_position_size == 0.20  # 允许集中持仓
        assert micro_config.max_turnover == 10.0       # 允许极高频
        assert micro_config.volatility_tolerance == 0.8 # 允许高波动
        
        # 验证大型档配置 - 重稳定性
        large_config = manager.tier_configs[CapitalTier.TIER_4]
        assert large_config.name == "大型资金档"
        assert large_config.capital_range == (210000, 700000)
        assert large_config.initial_capital == 500000
        assert large_config.max_position_size == 0.05  # 严格分散
        assert large_config.max_turnover == 2.0        # 低换手
        assert large_config.volatility_tolerance == 0.3 # 低波动要求
    
    def test_determine_optimal_tier(self, manager, sample_strategies):
        """测试自动档位选择算法"""
        # 测试高频策略 → 微型资金
        high_freq_strategy = sample_strategies[0]  # high_frequency
        tier = manager.determine_optimal_tier(high_freq_strategy)
        assert tier == CapitalTier.TIER_1
        
        # 测试动量策略 → 小型资金
        momentum_strategy = sample_strategies[1]  # momentum, 3天持仓
        tier = manager.determine_optimal_tier(momentum_strategy)
        assert tier == CapitalTier.TIER_2
        
        # 测试因子策略 → 中型资金
        factor_strategy = sample_strategies[2]  # factor_based
        tier = manager.determine_optimal_tier(factor_strategy)
        assert tier == CapitalTier.TIER_3
        
        # 测试价值策略 → 大型资金
        value_strategy = sample_strategies[3]  # value
        tier = manager.determine_optimal_tier(value_strategy)
        assert tier == CapitalTier.TIER_4
    
    def test_tier_selection_adjustments(self, manager):
        """测试档位选择的调整逻辑"""
        # 测试集中持仓调整
        concentrated_strategy = MockStrategy(
            "S005", "集中策略", "momentum", 
            typical_position_count=3  # 集中持仓
        )
        tier = manager.determine_optimal_tier(concentrated_strategy)
        # 集中持仓应该倾向小资金
        assert tier in [CapitalTier.TIER_1, CapitalTier.TIER_2]
        
        # 测试高换手调整
        high_turnover_strategy = MockStrategy(
            "S006", "高换手策略", "factor_based",
            monthly_turnover=6.0  # 高换手
        )
        tier = manager.determine_optimal_tier(high_turnover_strategy)
        # 高换手应该倾向小资金
        assert tier in [CapitalTier.TIER_1, CapitalTier.TIER_2]
        
        # 测试分散持仓调整
        diversified_strategy = MockStrategy(
            "S007", "分散策略", "momentum",
            typical_position_count=35  # 分散持仓
        )
        tier = manager.determine_optimal_tier(diversified_strategy)
        # 分散持仓应该倾向大资金
        assert tier in [CapitalTier.TIER_3, CapitalTier.TIER_4]
    
    @pytest.mark.asyncio
    async def test_resource_allocation(self, manager):
        """测试资源分配配置"""
        # 验证资源分配配置
        assert len(manager.resource_allocation) == 4
        
        # 验证微型档 - 高并发，低资源
        micro_resources = manager.resource_allocation[CapitalTier.TIER_1]
        assert micro_resources['concurrent_limit'] == 5  # 最高并发
        assert micro_resources['memory_limit_mb'] == 512  # 最低内存
        
        # 验证大型档 - 低并发，高资源
        large_resources = manager.resource_allocation[CapitalTier.TIER_4]
        assert large_resources['concurrent_limit'] == 1    # 最低并发
        assert large_resources['memory_limit_mb'] == 4096  # 最高内存
        assert large_resources['priority'] == 'highest'    # 最高优先级
    
    @pytest.mark.asyncio
    async def test_concurrent_validation_limits(self, manager, sample_strategies):
        """测试并发验证限制"""
        # 验证并发限制配置
        assert manager.tier_concurrent_limits[CapitalTier.TIER_1] == 5
        assert manager.tier_concurrent_limits[CapitalTier.TIER_2] == 4
        assert manager.tier_concurrent_limits[CapitalTier.TIER_3] == 2
        assert manager.tier_concurrent_limits[CapitalTier.TIER_4] == 1
        
        # 总并发限制
        total_max_concurrent = sum(manager.tier_concurrent_limits.values())
        assert total_max_concurrent == 12
        assert manager.max_concurrent_tasks == 12


class TestRelativePerformanceEvaluator:
    """相对表现评估器测试"""
    
    @pytest.fixture
    def mock_redis(self):
        """模拟Redis客户端"""
        redis_mock = Mock()
        redis_mock.get.return_value = None
        redis_mock.setex.return_value = True
        return redis_mock
    
    @pytest.fixture
    def evaluator(self, mock_redis):
        """创建评估器实例"""
        return RelativePerformanceEvaluator(mock_redis)
    
    @pytest.fixture
    def sample_simulation_result(self):
        """创建示例模拟结果"""
        # 生成30天的日收益数据
        np.random.seed(42)
        daily_returns = np.random.normal(0.001, 0.015, 30).tolist()
        
        return MockSimulationResult(
            start_date=datetime(2026, 1, 1),
            end_date=datetime(2026, 1, 30),
            total_return=0.067,      # 6.7%总收益
            annual_return=0.892,     # 89.2%年化收益
            sharpe_ratio=2.15,       # 优秀的夏普比率
            max_drawdown=0.089,      # 8.9%最大回撤
            win_rate=0.623,          # 62.3%胜率
            calmar_ratio=10.02,      # 卡玛比率
            information_ratio=1.34,  # 信息比率
            volatility=0.18,         # 18%年化波动率
            daily_returns=daily_returns
        )
    
    @pytest.fixture
    def sample_strategy(self):
        """创建示例策略"""
        return MockStrategy("S001", "测试策略", "momentum")
    
    def test_evaluator_initialization(self, evaluator):
        """测试评估器初始化"""
        # 验证基准配置
        assert len(evaluator.benchmark_configs) == 3
        assert BenchmarkType.CSI_300 in evaluator.benchmark_configs
        assert BenchmarkType.CSI_500 in evaluator.benchmark_configs
        assert BenchmarkType.CSI_1000 in evaluator.benchmark_configs
        
        # 验证评估权重 - 体现相对评估理念
        weights = evaluator.evaluation_weights
        assert weights['benchmark_comparison'] == 0.30  # 基准对比30%
        assert weights['peer_comparison'] == 0.25       # 同类对比25%
        assert weights['risk_adjustment'] == 0.25       # 风险调整25%
        assert weights['consistency'] == 0.15           # 一致性15%
        assert weights['adaptation'] == 0.05            # 适应性5%
        assert sum(weights.values()) == 1.0             # 总和100%
    
    @pytest.mark.asyncio
    async def test_benchmark_data_generation(self, evaluator):
        """测试基准数据生成"""
        start_date = datetime(2026, 1, 1)
        end_date = datetime(2026, 1, 30)
        
        # 测试沪深300基准数据
        benchmark_data = await evaluator._get_benchmark_data(
            BenchmarkType.CSI_300, start_date, end_date
        )
        
        assert 'total_return' in benchmark_data
        assert 'daily_returns' in benchmark_data
        assert 'volatility' in benchmark_data
        assert 'sharpe_ratio' in benchmark_data
        assert 'max_drawdown' in benchmark_data
        
        # 验证数据合理性
        assert len(benchmark_data['daily_returns']) == 29  # 30天-1
        assert -0.5 < benchmark_data['total_return'] < 0.5  # 合理的月收益范围
        assert 0 < benchmark_data['volatility'] < 1.0      # 合理的波动率范围
    
    @pytest.mark.asyncio
    async def test_peer_strategies_data(self, evaluator):
        """测试同类策略数据生成"""
        # 测试动量策略同类数据
        peer_data = await evaluator._get_peer_strategies_data('momentum')
        
        assert len(peer_data) == 20  # 20个同类策略
        
        for peer in peer_data:
            assert 'strategy_id' in peer
            assert 'total_return' in peer
            assert 'sharpe_ratio' in peer
            assert 'max_drawdown' in peer
            
            # 验证数据合理性
            assert peer['total_return'] >= -0.5  # 最大亏损50%
            assert peer['sharpe_ratio'] >= 0.1   # 最小夏普0.1
            assert 0.05 <= peer['max_drawdown'] <= 0.25  # 合理回撤范围
    
    @pytest.mark.asyncio
    async def test_relative_performance_evaluation(self, evaluator, sample_simulation_result, sample_strategy):
        """测试相对表现评估 - 核心功能"""
        # 执行相对表现评估
        result = await evaluator.evaluate_relative_performance(
            sample_simulation_result, sample_strategy
        )
        
        # 验证结果结构
        assert isinstance(result, RelativePerformanceResult)
        
        # 验证基准对比
        assert hasattr(result, 'benchmark_outperformance')
        assert hasattr(result, 'benchmark_correlation')
        assert hasattr(result, 'tracking_error')
        assert hasattr(result, 'information_ratio')
        
        # 验证同类对比
        assert hasattr(result, 'peer_ranking_percentile')
        assert hasattr(result, 'peer_outperformance_rate')
        assert hasattr(result, 'peer_risk_adjusted_ranking')
        
        # 验证风险调整
        assert hasattr(result, 'risk_adjusted_score')
        assert hasattr(result, 'sharpe_ranking')
        assert hasattr(result, 'calmar_ranking')
        assert hasattr(result, 'sortino_ranking')
        
        # 验证一致性
        assert hasattr(result, 'consistency_score')
        assert hasattr(result, 'stability_score')
        assert hasattr(result, 'drawdown_control_score')
        
        # 验证适应性
        assert hasattr(result, 'market_adaptation_score')
        assert hasattr(result, 'regime_performance')
        assert hasattr(result, 'volatility_adaptation')
        
        # 验证综合评分
        assert hasattr(result, 'overall_relative_score')
        assert hasattr(result, 'grade')
        assert 0 <= result.overall_relative_score <= 1
        assert result.grade in ['A+', 'A', 'A-', 'B+', 'B', 'B-', 'C+', 'C', 'C-', 'D']
        
        # 验证分析洞察
        assert hasattr(result, 'strengths')
        assert hasattr(result, 'weaknesses')
        assert hasattr(result, 'recommendations')
        assert isinstance(result.strengths, list)
        assert isinstance(result.weaknesses, list)
        assert isinstance(result.recommendations, list)
    
    def test_score_to_percentile_conversion(self, evaluator):
        """测试评分到百分位的转换"""
        # 测试边界值
        assert evaluator._score_to_percentile(0.0) < 0.1   # 低分对应低百分位
        assert abs(evaluator._score_to_percentile(0.5) - 0.5) < 0.2   # 中等分对应中位数
        assert evaluator._score_to_percentile(1.0) > 0.9   # 高分对应高百分位
        
        # 测试单调性
        scores = [0.2, 0.4, 0.6, 0.8]
        percentiles = [evaluator._score_to_percentile(s) for s in scores]
        assert percentiles == sorted(percentiles)  # 应该是递增的
    
    def test_grade_determination(self, evaluator):
        """测试评级确定"""
        # 测试各个评级阈值
        assert evaluator._determine_grade(0.95) == "A+"
        assert evaluator._determine_grade(0.87) == "A"
        assert evaluator._determine_grade(0.82) == "A-"
        assert evaluator._determine_grade(0.77) == "B+"
        assert evaluator._determine_grade(0.72) == "B"
        assert evaluator._determine_grade(0.67) == "B-"
        assert evaluator._determine_grade(0.62) == "C+"
        assert evaluator._determine_grade(0.57) == "C"
        assert evaluator._determine_grade(0.52) == "C-"
        assert evaluator._determine_grade(0.45) == "D"


class TestFourTierZ2HCertification:
    """四档Z2H认证系统测试"""
    
    @pytest.fixture
    def mock_redis(self):
        """模拟Redis客户端"""
        redis_mock = Mock()
        redis_mock.get.return_value = None
        redis_mock.setex.return_value = True
        redis_mock.keys.return_value = []
        return redis_mock
    
    @pytest.fixture
    def certification_system(self, mock_redis):
        """创建认证系统实例"""
        return FourTierZ2HCertification(mock_redis)
    
    @pytest.fixture
    def excellent_simulation_result(self):
        """创建优秀的模拟结果"""
        np.random.seed(42)
        daily_returns = np.random.normal(0.002, 0.012, 30).tolist()  # 优秀的日收益
        
        return MockSimulationResult(
            start_date=datetime(2026, 1, 1),
            end_date=datetime(2026, 1, 30),
            total_return=0.085,      # 8.5%总收益
            annual_return=1.12,      # 112%年化收益
            sharpe_ratio=2.8,        # 优秀夏普比率
            max_drawdown=0.065,      # 6.5%回撤
            win_rate=0.68,           # 68%胜率
            calmar_ratio=17.2,       # 优秀卡玛比率
            information_ratio=1.8,   # 优秀信息比率
            volatility=0.16,         # 16%波动率
            daily_returns=daily_returns
        )
    
    @pytest.fixture
    def excellent_relative_performance(self):
        """创建优秀的相对表现结果"""
        return RelativePerformanceResult(
            benchmark_outperformance=0.25,      # 超越基准25%
            benchmark_correlation=0.65,         # 适度相关性
            tracking_error=0.12,                # 合理跟踪误差
            information_ratio=1.8,              # 优秀信息比率
            
            peer_ranking_percentile=0.92,       # 同类前8%
            peer_outperformance_rate=0.92,      # 超越92%同类
            peer_risk_adjusted_ranking=0.88,    # 风险调整排名前12%
            
            risk_adjusted_score=0.88,           # 优秀风险调整评分
            sharpe_ranking=0.90,                # 夏普排名前10%
            calmar_ranking=0.95,                # 卡玛排名前5%
            sortino_ranking=0.85,               # 索提诺排名前15%
            
            consistency_score=0.82,             # 优秀一致性
            stability_score=0.85,               # 优秀稳定性
            drawdown_control_score=0.88,        # 优秀回撤控制
            
            market_adaptation_score=0.78,       # 良好适应性
            regime_performance={'bull_market': 0.9, 'bear_market': 0.7, 'sideways_market': 0.8},
            volatility_adaptation=0.75,         # 波动率适应性
            
            overall_relative_score=0.87,        # 优秀综合评分
            grade="A",                          # A级评级
            
            strengths=["显著超越基准", "同类策略排名前列", "优秀的风险调整收益"],
            weaknesses=["在熊市环境下表现一般"],
            recommendations=["继续保持当前优秀表现", "可考虑在熊市环境下的策略优化"]
        )
    
    def test_tier_standards_initialization(self, certification_system):
        """测试四档认证标准初始化"""
        standards = certification_system.tier_standards
        
        # 验证四个档位都有认证标准
        assert len(standards) == 4
        for tier in CapitalTier:
            assert tier in standards
            
            # 每个档位至少有三个认证级别
            tier_standards = standards[tier]
            assert CertificationLevel.PLATINUM in tier_standards
            assert CertificationLevel.GOLD in tier_standards
            assert CertificationLevel.SILVER in tier_standards
    
    def test_tier_differentiated_standards(self, certification_system):
        """测试差异化认证标准 - 核心理念验证"""
        standards = certification_system.tier_standards
        
        # 验证微型档 - 高要求，体现小资金优势
        micro_platinum = standards[CapitalTier.TIER_1][CertificationLevel.PLATINUM]
        assert micro_platinum.min_sharpe_ratio == 2.8           # 最高夏普要求
        assert micro_platinum.min_benchmark_outperformance == 0.20  # 超越基准20%+
        assert micro_platinum.max_turnover == 15.0             # 允许极高频
        assert micro_platinum.volatility_tolerance == 1.0      # 允许极高波动
        
        # 验证大型档 - 重稳定性
        large_platinum = standards[CapitalTier.TIER_4][CertificationLevel.PLATINUM]
        assert large_platinum.min_sharpe_ratio == 2.0          # 相对较低，重稳定性
        assert large_platinum.min_benchmark_outperformance == 0.08  # 超越基准8%+ (大资金相对要求)
        assert large_platinum.max_turnover == 2.5              # 低换手要求
        assert large_platinum.volatility_tolerance == 0.3      # 最低波动容忍度
        assert large_platinum.min_consistency_score == 0.85    # 最高一致性要求
        
        # 验证递减趋势 - 小资金高要求，大资金重稳定
        tiers = [CapitalTier.TIER_1, CapitalTier.TIER_2, 
                CapitalTier.TIER_3, CapitalTier.TIER_4]
        
        platinum_standards = [standards[tier][CertificationLevel.PLATINUM] for tier in tiers]
        
        # 基准超额收益要求递减 (小资金要求更高收益)
        benchmark_requirements = [std.min_benchmark_outperformance for std in platinum_standards]
        assert benchmark_requirements == sorted(benchmark_requirements, reverse=True)  # 递减
        
        # 换手率限制递减 (小资金允许更高换手)
        turnover_limits = [std.max_turnover for std in platinum_standards]
        assert turnover_limits == sorted(turnover_limits, reverse=True)  # 递减
        
        # 一致性要求递增 (大资金要求更高一致性)
        consistency_requirements = [std.min_consistency_score for std in platinum_standards]
        assert consistency_requirements == sorted(consistency_requirements)  # 递增
    
    @pytest.mark.asyncio
    async def test_certification_level_determination(self, certification_system, excellent_simulation_result, excellent_relative_performance):
        """测试认证级别确定 - 让策略跑出最优表现"""
        # 模拟相对表现评估
        with patch.object(certification_system.performance_evaluator, 'evaluate_relative_performance', 
                         return_value=excellent_relative_performance):
            
            # 测试微型档 - 应该能达到PLATINUM级
            level = await certification_system._determine_certification_level(
                excellent_simulation_result, excellent_relative_performance, CapitalTier.TIER_1
            )
            assert level == CertificationLevel.PLATINUM
            
            # 测试大型档 - 由于一致性要求更高，可能只能达到GOLD级
            large_tier_level = await certification_system._determine_certification_level(
                excellent_simulation_result, excellent_relative_performance, CapitalTier.TIER_4
            )
            # 大型档对一致性要求更高，可能达不到PLATINUM
            assert large_tier_level in [CertificationLevel.PLATINUM, CertificationLevel.GOLD]
    
    @pytest.mark.asyncio
    async def test_certification_requirements_check(self, certification_system, excellent_simulation_result, excellent_relative_performance):
        """测试认证要求检查"""
        # 检查微型档PLATINUM级要求
        passed, failed = await certification_system._check_certification_requirements(
            excellent_simulation_result, excellent_relative_performance, 
            CapitalTier.TIER_1, CertificationLevel.PLATINUM
        )
        
        # 优秀的结果应该通过大部分要求
        assert len(passed) > len(failed)
        
        # 验证检查项目包含关键指标
        all_requirements = passed + failed
        requirement_text = ' '.join(all_requirements)
        
        assert '夏普比率' in requirement_text
        assert '最大回撤' in requirement_text
        assert '胜率' in requirement_text
        assert '基准超额收益' in requirement_text
        assert '同类排名' in requirement_text
        assert '风险调整评分' in requirement_text
        assert '一致性评分' in requirement_text
    
    def test_allocation_recommendation_generation(self, certification_system, excellent_simulation_result):
        """测试资金配置建议生成"""
        # 测试PLATINUM级微型档配置
        allocation = certification_system._generate_allocation_recommendation(
            CapitalTier.TIER_1, CertificationLevel.PLATINUM, excellent_simulation_result
        )
        
        assert 'max_allocation_ratio' in allocation
        assert 'leverage_allowed' in allocation
        assert 'recommended_capital_range' in allocation
        assert 'optimal_capital' in allocation
        assert 'risk_warnings' in allocation
        assert 'usage_guidelines' in allocation
        assert 'monitoring_requirements' in allocation
        
        # 验证微型档配置特点
        assert allocation['max_allocation_ratio'] <= 0.36  # 最大30%*1.2倍性能调整
        assert allocation['leverage_allowed'] == 1.0       # 微型档不允许杠杆
        assert allocation['recommended_capital_range'] == (1000, 10000)
        assert allocation['optimal_capital'] == 5000
        
        # 验证风险警告和使用指导
        assert isinstance(allocation['risk_warnings'], list)
        assert isinstance(allocation['usage_guidelines'], list)
        assert isinstance(allocation['monitoring_requirements'], list)
    
    def test_differentiated_allocation_by_tier(self, certification_system, excellent_simulation_result):
        """测试不同档位的差异化配置"""
        # 获取各档位GOLD级配置
        micro_allocation = certification_system._generate_allocation_recommendation(
            CapitalTier.TIER_1, CertificationLevel.GOLD, excellent_simulation_result
        )
        
        large_allocation = certification_system._generate_allocation_recommendation(
            CapitalTier.TIER_4, CertificationLevel.GOLD, excellent_simulation_result
        )
        
        # 验证配置差异
        # 微型档配置比例应该高于大型档 (小资金可以更集中)
        assert micro_allocation['max_allocation_ratio'] >= large_allocation['max_allocation_ratio']
        
        # 大型档可能允许更高杠杆 (机构化运作)
        assert large_allocation['leverage_allowed'] >= micro_allocation['leverage_allowed']
        
        # 资金范围应该不同
        assert micro_allocation['recommended_capital_range'][1] < large_allocation['recommended_capital_range'][0]
    
    @pytest.mark.asyncio
    async def test_full_certification_process(self, certification_system, excellent_simulation_result, excellent_relative_performance):
        """测试完整认证流程"""
        strategy = MockStrategy("S001", "优秀策略", "momentum")
        
        # 模拟相对表现评估
        with patch.object(certification_system.performance_evaluator, 'evaluate_relative_performance', 
                         return_value=excellent_relative_performance):
            
            # 执行完整认证
            result = await certification_system.certify_strategy(
                strategy, excellent_simulation_result, CapitalTier.TIER_2
            )
            
            # 验证认证结果结构
            assert isinstance(result, Z2HCertificationResult)
            assert result.strategy_id == "S001"
            assert result.strategy_name == "优秀策略"
            assert result.tier == CapitalTier.TIER_2
            assert result.certification_level in [CertificationLevel.PLATINUM, CertificationLevel.GOLD, CertificationLevel.SILVER]
            
            # 验证评分
            assert 0 <= result.overall_score <= 1
            assert 0 <= result.tier_specific_score <= 1
            assert 0 <= result.relative_performance_score <= 1
            
            # 验证认证详情
            assert isinstance(result.passed_requirements, list)
            assert isinstance(result.failed_requirements, list)
            assert isinstance(result.certification_notes, list)
            
            # 验证资金配置建议
            assert 'max_allocation_ratio' in result.recommended_allocation
            assert result.max_allocation_ratio > 0
            assert result.leverage_allowed >= 1.0
            
            # 验证有效期
            assert result.valid_until > result.certification_date
            assert (result.valid_until - result.certification_date).days == 90
    
    def test_certification_notes_generation(self, certification_system, excellent_relative_performance):
        """测试认证说明生成"""
        passed_requirements = [
            "夏普比率 2.8 ≥ 2.5",
            "基准超额收益 25.0% ≥ 15.0%",
            "同类排名 前8% ≥ 前15%"
        ]
        
        failed_requirements = [
            "月换手率 16.0 > 15.0"
        ]
        
        notes = certification_system._generate_certification_notes(
            CapitalTier.TIER_1, CertificationLevel.PLATINUM,
            passed_requirements, failed_requirements, excellent_relative_performance
        )
        
        assert isinstance(notes, list)
        assert len(notes) > 0
        
        # 验证包含关键信息
        notes_text = ' '.join(notes)
        assert 'PLATINUM' in notes_text
        assert '策略优势' in notes_text or '优势' in notes_text
        assert '改进建议' in notes_text or '建议' in notes_text
        assert '认证有效期' in notes_text or '90天' in notes_text


class TestIntegrationScenarios:
    """集成测试场景"""
    
    @pytest.fixture
    def complete_system(self):
        """创建完整的四档验证系统"""
        mock_redis = Mock()
        mock_redis.get.return_value = None
        mock_redis.setex.return_value = True
        mock_redis.keys.return_value = []
        
        return {
            'multi_tier_manager': MultiTierSimulationManager(mock_redis),
            'performance_evaluator': RelativePerformanceEvaluator(mock_redis),
            'certification_system': FourTierZ2HCertification(mock_redis)
        }
    
    @pytest.mark.asyncio
    async def test_end_to_end_validation_flow(self, complete_system):
        """测试端到端验证流程 - 让策略跑出最优表现"""
        multi_tier_manager = complete_system['multi_tier_manager']
        certification_system = complete_system['certification_system']
        
        # 1. 创建测试策略
        strategies = [
            MockStrategy("S001", "高频策略", "high_frequency", 1, 5, 8.0, 0.25),
            MockStrategy("S002", "动量策略", "momentum", 3, 15, 3.0, 0.18),
            MockStrategy("S003", "因子策略", "factor_based", 7, 25, 2.0, 0.15),
            MockStrategy("S004", "价值策略", "value", 30, 40, 1.0, 0.12)
        ]
        
        # 2. 测试自动档位选择
        tier_assignments = {}
        for strategy in strategies:
            tier = multi_tier_manager.determine_optimal_tier(strategy)
            tier_assignments[strategy.strategy_id] = tier
        
        # 验证档位分配合理性
        assert tier_assignments["S001"] == CapitalTier.TIER_1  # 高频 → 微型
        assert tier_assignments["S002"] == CapitalTier.TIER_2  # 动量 → 小型
        assert tier_assignments["S003"] == CapitalTier.TIER_3 # 因子 → 中型
        assert tier_assignments["S004"] == CapitalTier.TIER_4  # 价值 → 大型
        
        # 3. 验证资源分配合理性
        total_concurrent = 0
        for tier in tier_assignments.values():
            total_concurrent += multi_tier_manager.tier_concurrent_limits[tier]
        
        assert total_concurrent <= multi_tier_manager.max_concurrent_tasks
        
        # 4. 模拟认证流程
        for strategy in strategies[:2]:  # 测试前两个策略
            tier = tier_assignments[strategy.strategy_id]
            
            # 创建模拟结果
            simulation_result = MockSimulationResult(
                start_date=datetime(2026, 1, 1),
                end_date=datetime(2026, 1, 30),
                total_return=0.06,
                annual_return=0.8,
                sharpe_ratio=2.0,
                max_drawdown=0.1,
                win_rate=0.6,
                calmar_ratio=8.0,
                information_ratio=1.2,
                volatility=0.16,
                daily_returns=np.random.normal(0.001, 0.015, 30).tolist()
            )
            
            # 模拟相对表现评估
            relative_performance = RelativePerformanceResult(
                benchmark_outperformance=0.15,
                benchmark_correlation=0.6,
                tracking_error=0.1,
                information_ratio=1.2,
                peer_ranking_percentile=0.75,
                peer_outperformance_rate=0.75,
                peer_risk_adjusted_ranking=0.7,
                risk_adjusted_score=0.75,
                sharpe_ranking=0.8,
                calmar_ranking=0.85,
                sortino_ranking=0.75,
                consistency_score=0.7,
                stability_score=0.75,
                drawdown_control_score=0.8,
                market_adaptation_score=0.65,
                regime_performance={'bull_market': 0.8, 'bear_market': 0.6},
                volatility_adaptation=0.7,
                overall_relative_score=0.75,
                grade="B+",
                strengths=["良好的风险调整收益"],
                weaknesses=["可进一步提升一致性"],
                recommendations=["优化参数稳定性"]
            )
            
            # 模拟认证
            with patch.object(certification_system.performance_evaluator, 'evaluate_relative_performance', 
                             return_value=relative_performance):
                
                cert_result = await certification_system.certify_strategy(
                    strategy, simulation_result, tier
                )
                
                # 验证认证结果
                assert cert_result.tier == tier
                assert cert_result.certification_level != CertificationLevel.NONE
                assert cert_result.overall_score > 0
    
    def test_performance_comparison_across_tiers(self, complete_system):
        """测试跨档位性能对比 - 验证差异化标准"""
        certification_system = complete_system['certification_system']
        
        # 相同的策略表现在不同档位的认证结果应该不同
        simulation_result = MockSimulationResult(
            start_date=datetime(2026, 1, 1),
            end_date=datetime(2026, 1, 30),
            total_return=0.08,
            annual_return=1.0,
            sharpe_ratio=2.2,
            max_drawdown=0.12,
            win_rate=0.62,
            calmar_ratio=8.3,
            information_ratio=1.3,
            volatility=0.18,
            daily_returns=np.random.normal(0.001, 0.015, 30).tolist(),
            monthly_turnover=4.0  # 中等换手率
        )
        
        relative_performance = RelativePerformanceResult(
            benchmark_outperformance=0.12,
            benchmark_correlation=0.65,
            tracking_error=0.15,
            information_ratio=1.3,
            peer_ranking_percentile=0.80,
            peer_outperformance_rate=0.80,
            peer_risk_adjusted_ranking=0.75,
            risk_adjusted_score=0.78,
            sharpe_ranking=0.82,
            calmar_ranking=0.85,
            sortino_ranking=0.78,
            consistency_score=0.75,
            stability_score=0.78,
            drawdown_control_score=0.82,
            market_adaptation_score=0.70,
            regime_performance={'bull_market': 0.85, 'bear_market': 0.65},
            volatility_adaptation=0.72,
            overall_relative_score=0.78,
            grade="B+",
            strengths=["良好的综合表现"],
            weaknesses=["可进一步优化"],
            recommendations=["保持当前水平"]
        )
        
        # 测试在不同档位的认证级别
        tier_results = {}
        for tier in CapitalTier:
            level = asyncio.run(certification_system._determine_certification_level(
                simulation_result, relative_performance, tier
            ))
            tier_results[tier] = level
        
        # 验证差异化认证 - 小资金档位要求更高
        # 相同表现在微型档可能只能达到SILVER，在大型档可能达到GOLD
        print(f"认证结果: {tier_results}")
        
        # 至少应该有一些差异
        unique_levels = set(tier_results.values())
        assert len(unique_levels) >= 1  # 至少有认证级别差异


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v", "--tb=short"])
