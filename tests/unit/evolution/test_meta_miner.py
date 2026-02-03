"""元挖掘器单元测试

白皮书依据: 第四章 4.1.16 元挖掘与自适应优化
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

from src.evolution.meta_miner import (
    MetaMiner,
    MinerPerformance,
    MinerRecommendation
)
from src.evolution.unified_factor_mining_system import (
    MinerType,
    FactorMetadata,
    MinerStatus,
    MiningResult
)


class TestMetaMinerInit:
    """测试MetaMiner初始化"""
    
    def test_init_default_params(self):
        """测试默认参数初始化"""
        miner = MetaMiner()
        
        assert miner.optimization_window == 30
        assert miner.min_samples == 10
        assert len(miner.performance_history) == 0
        assert len(miner.market_regime_history) == 0
    
    def test_init_custom_params(self):
        """测试自定义参数初始化"""
        miner = MetaMiner(optimization_window=60, min_samples=20)
        
        assert miner.optimization_window == 60
        assert miner.min_samples == 20

    def test_init_invalid_optimization_window(self):
        """测试无效的优化窗口参数"""
        with pytest.raises(ValueError, match="optimization_window必须 > 0"):
            MetaMiner(optimization_window=0)
        
        with pytest.raises(ValueError, match="optimization_window必须 > 0"):
            MetaMiner(optimization_window=-10)
    
    def test_init_invalid_min_samples(self):
        """测试无效的最小样本数参数"""
        with pytest.raises(ValueError, match="min_samples必须 > 0"):
            MetaMiner(min_samples=0)
        
        with pytest.raises(ValueError, match="min_samples必须 > 0"):
            MetaMiner(min_samples=-5)


class TestRecordMiningResult:
    """测试记录挖掘结果"""
    
    @pytest.fixture
    def miner(self):
        """创建测试用的MetaMiner实例"""
        return MetaMiner(optimization_window=30, min_samples=3)
    
    @pytest.fixture
    def sample_factors(self):
        """创建测试用的因子列表"""
        return [
            FactorMetadata(
                factor_id="factor_1",
                factor_name="TestFactor1",
                factor_type=MinerType.GENETIC,
                data_source="test",
                discovery_date=datetime.now(),
                discoverer="test_miner",
                expression="close / open",
                fitness=0.8,
                ic=0.05,
                ir=0.3,
                sharpe=1.5
            ),
            FactorMetadata(
                factor_id="factor_2",
                factor_name="TestFactor2",
                factor_type=MinerType.GENETIC,
                data_source="test",
                discovery_date=datetime.now(),
                discoverer="test_miner",
                expression="volume / delay(volume, 1)",
                fitness=0.7,
                ic=0.04,
                ir=0.25,
                sharpe=1.2
            )
        ]
    
    def test_record_successful_result(self, miner, sample_factors):
        """测试记录成功的挖掘结果"""
        result = MiningResult(
            miner_type=MinerType.GENETIC,
            factors=sample_factors,
            execution_time=5.0,
            success=True,
            error=None
        )
        
        miner.record_mining_result(result, execution_time=5.0)
        
        assert MinerType.GENETIC in miner.performance_history
        assert len(miner.performance_history[MinerType.GENETIC]) == 1
        
        perf = miner.performance_history[MinerType.GENETIC][0]
        assert perf.miner_type == MinerType.GENETIC
        assert perf.success_rate == 1.0
        assert perf.avg_fitness == 0.75  # (0.8 + 0.7) / 2
        assert perf.avg_ic == 0.045  # (0.05 + 0.04) / 2
        assert perf.factor_count == 2
        assert perf.execution_time == 5.0

    def test_record_failed_result(self, miner):
        """测试记录失败的挖掘结果"""
        result = MiningResult(
            miner_type=MinerType.GENETIC,
            factors=[],
            execution_time=1.0,
            success=False,
            error="Test error"
        )
        
        miner.record_mining_result(result, execution_time=1.0)
        
        # 失败的结果不应该被记录
        assert len(miner.performance_history.get(MinerType.GENETIC, [])) == 0
    
    def test_record_empty_factors(self, miner):
        """测试记录空因子列表的结果"""
        result = MiningResult(
            miner_type=MinerType.GENETIC,
            factors=[],
            execution_time=2.0,
            success=True,
            error=None
        )
        
        miner.record_mining_result(result, execution_time=2.0)
        
        assert len(miner.performance_history[MinerType.GENETIC]) == 1
        perf = miner.performance_history[MinerType.GENETIC][0]
        assert perf.avg_fitness == 0.0
        assert perf.avg_ic == 0.0
        assert perf.factor_count == 0
    
    def test_record_multiple_results(self, miner, sample_factors):
        """测试记录多个挖掘结果"""
        for i in range(5):
            result = MiningResult(
                miner_type=MinerType.GENETIC,
                factors=sample_factors,
                execution_time=float(i + 1),
                success=True,
                error=None
            )
            miner.record_mining_result(result, execution_time=float(i + 1))
        
        assert len(miner.performance_history[MinerType.GENETIC]) == 5


class TestDetectMarketRegime:
    """测试市场状态检测"""
    
    @pytest.fixture
    def miner(self):
        """创建测试用的MetaMiner实例"""
        return MetaMiner()
    
    def test_detect_bull_market(self, miner):
        """测试检测牛市"""
        # 创建上涨趋势数据
        np.random.seed(42)
        dates = pd.date_range(start='2025-01-01', periods=100, freq='D')
        returns = pd.Series(
            np.random.normal(0.002, 0.01, 100),  # 正收益
            index=dates
        )
        data = pd.DataFrame({'returns': returns})
        
        regime = miner.detect_market_regime(data)
        
        assert regime in ['bull', 'stable', 'volatile']

    def test_detect_bear_market(self, miner):
        """测试检测熊市"""
        # 创建下跌趋势数据
        np.random.seed(42)
        dates = pd.date_range(start='2025-01-01', periods=100, freq='D')
        returns = pd.Series(
            np.random.normal(-0.002, 0.01, 100),  # 负收益
            index=dates
        )
        data = pd.DataFrame({'returns': returns})
        
        regime = miner.detect_market_regime(data)
        
        assert regime in ['bear', 'stable', 'volatile', 'crisis']
    
    def test_detect_volatile_market(self, miner):
        """测试检测高波动市场"""
        # 创建高波动数据
        np.random.seed(42)
        dates = pd.date_range(start='2025-01-01', periods=100, freq='D')
        returns = pd.Series(
            np.random.normal(0, 0.05, 100),  # 高波动
            index=dates
        )
        data = pd.DataFrame({'returns': returns})
        
        regime = miner.detect_market_regime(data)
        
        assert regime in ['volatile', 'crisis', 'bull', 'bear', 'stable']
    
    def test_detect_crisis_market(self, miner):
        """测试检测危机市场"""
        # 创建大幅下跌数据
        np.random.seed(42)
        dates = pd.date_range(start='2025-01-01', periods=100, freq='D')
        returns = pd.Series(
            np.concatenate([
                np.random.normal(0, 0.01, 80),
                np.array([-0.05] * 20)  # 连续大跌
            ]),
            index=dates
        )
        data = pd.DataFrame({'returns': returns})
        
        regime = miner.detect_market_regime(data)
        
        assert regime in ['crisis', 'bear', 'volatile']
    
    def test_detect_missing_returns_column(self, miner):
        """测试缺少returns列的情况"""
        data = pd.DataFrame({'close': [100, 101, 102]})
        
        regime = miner.detect_market_regime(data)
        
        assert regime == 'unknown'
    
    def test_market_regime_history_recorded(self, miner):
        """测试市场状态历史记录"""
        np.random.seed(42)
        dates = pd.date_range(start='2025-01-01', periods=100, freq='D')
        returns = pd.Series(np.random.normal(0, 0.01, 100), index=dates)
        data = pd.DataFrame({'returns': returns})
        
        miner.detect_market_regime(data)
        
        assert len(miner.market_regime_history) == 1
        assert isinstance(miner.market_regime_history[0][0], datetime)
        assert isinstance(miner.market_regime_history[0][1], str)


class TestAnalyzeMinerPerformance:
    """测试挖掘器性能分析"""
    
    @pytest.fixture
    def miner_with_history(self):
        """创建带有历史记录的MetaMiner实例"""
        miner = MetaMiner(optimization_window=30, min_samples=3)
        
        # 添加历史记录
        for i in range(5):
            perf = MinerPerformance(
                miner_type=MinerType.GENETIC,
                success_rate=0.9,
                avg_fitness=0.7 + i * 0.02,
                avg_ic=0.04 + i * 0.005,
                avg_ir=0.25 + i * 0.01,
                execution_time=5.0 + i,
                factor_count=10 + i,
                last_update=datetime.now()
            )
            miner.performance_history[MinerType.GENETIC].append(perf)
        
        return miner
    
    def test_analyze_with_sufficient_samples(self, miner_with_history):
        """测试有足够样本时的性能分析"""
        result = miner_with_history.analyze_miner_performance(MinerType.GENETIC)
        
        assert result is not None
        assert 'success_rate' in result
        assert 'avg_fitness' in result
        assert 'avg_ic' in result
        assert 'avg_ir' in result
        assert 'avg_execution_time' in result
        assert 'total_factors' in result
        assert 'fitness_trend' in result
        assert 'sample_count' in result
        
        assert result['sample_count'] == 5
        assert result['success_rate'] == 0.9
    
    def test_analyze_with_insufficient_samples(self):
        """测试样本不足时的性能分析"""
        miner = MetaMiner(min_samples=10)
        
        # 只添加2个样本
        for i in range(2):
            perf = MinerPerformance(
                miner_type=MinerType.GENETIC,
                success_rate=0.9,
                avg_fitness=0.7,
                avg_ic=0.04,
                avg_ir=0.25,
                execution_time=5.0,
                factor_count=10,
                last_update=datetime.now()
            )
            miner.performance_history[MinerType.GENETIC].append(perf)
        
        result = miner.analyze_miner_performance(MinerType.GENETIC)
        
        assert result is None
    
    def test_analyze_nonexistent_miner(self):
        """测试分析不存在的挖掘器"""
        miner = MetaMiner()
        
        result = miner.analyze_miner_performance(MinerType.SENTIMENT)
        
        assert result is None


class TestRecommendMiners:
    """测试挖掘器推荐"""
    
    @pytest.fixture
    def miner_with_multiple_histories(self):
        """创建带有多个挖掘器历史记录的MetaMiner实例"""
        miner = MetaMiner(optimization_window=30, min_samples=3)
        
        # 为多个挖掘器添加历史记录
        miner_types = [
            MinerType.GENETIC,
            MinerType.SENTIMENT,
            MinerType.HIGH_FREQUENCY,
            MinerType.NETWORK
        ]
        
        for miner_type in miner_types:
            for i in range(5):
                perf = MinerPerformance(
                    miner_type=miner_type,
                    success_rate=0.8 + np.random.random() * 0.2,
                    avg_fitness=0.6 + np.random.random() * 0.3,
                    avg_ic=0.03 + np.random.random() * 0.04,
                    avg_ir=0.2 + np.random.random() * 0.2,
                    execution_time=5.0 + np.random.random() * 10,
                    factor_count=5 + int(np.random.random() * 10),
                    last_update=datetime.now()
                )
                miner.performance_history[miner_type].append(perf)
        
        return miner
    
    def test_recommend_miners_bull_market(self, miner_with_multiple_histories):
        """测试牛市推荐"""
        recommendation = miner_with_multiple_histories.recommend_miners(
            market_regime='bull',
            top_k=3
        )
        
        assert isinstance(recommendation, MinerRecommendation)
        assert len(recommendation.recommended_miners) <= 3
        assert recommendation.market_regime == 'bull'
        assert 0 <= recommendation.confidence <= 1
        assert len(recommendation.reasoning) > 0
    
    def test_recommend_miners_bear_market(self, miner_with_multiple_histories):
        """测试熊市推荐"""
        recommendation = miner_with_multiple_histories.recommend_miners(
            market_regime='bear',
            top_k=3
        )
        
        assert isinstance(recommendation, MinerRecommendation)
        assert recommendation.market_regime == 'bear'
    
    def test_recommend_miners_volatile_market(self, miner_with_multiple_histories):
        """测试高波动市场推荐"""
        recommendation = miner_with_multiple_histories.recommend_miners(
            market_regime='volatile',
            top_k=3
        )
        
        assert isinstance(recommendation, MinerRecommendation)
        assert recommendation.market_regime == 'volatile'
    
    def test_recommend_miners_crisis_market(self, miner_with_multiple_histories):
        """测试危机市场推荐"""
        recommendation = miner_with_multiple_histories.recommend_miners(
            market_regime='crisis',
            top_k=3
        )
        
        assert isinstance(recommendation, MinerRecommendation)
        assert recommendation.market_regime == 'crisis'

    def test_recommend_miners_stable_market(self, miner_with_multiple_histories):
        """测试稳定市场推荐"""
        recommendation = miner_with_multiple_histories.recommend_miners(
            market_regime='stable',
            top_k=3
        )
        
        assert isinstance(recommendation, MinerRecommendation)
        assert recommendation.market_regime == 'stable'
    
    def test_recommend_miners_no_history(self):
        """测试无历史记录时的推荐"""
        miner = MetaMiner()
        
        recommendation = miner.recommend_miners(market_regime='bull', top_k=3)
        
        assert isinstance(recommendation, MinerRecommendation)
        # 无历史记录时可能返回空推荐或默认推荐
        assert recommendation.market_regime == 'bull'
    
    def test_recommend_miners_priority_scores(self, miner_with_multiple_histories):
        """测试推荐优先级得分"""
        recommendation = miner_with_multiple_histories.recommend_miners(
            market_regime='bull',
            top_k=5
        )
        
        # 验证优先级得分
        for miner_type in recommendation.recommended_miners:
            assert miner_type in recommendation.priority_scores
            assert recommendation.priority_scores[miner_type] >= 0


class TestMineFactors:
    """测试元挖掘因子"""
    
    @pytest.fixture
    def miner(self):
        """创建测试用的MetaMiner实例"""
        return MetaMiner()
    
    @pytest.fixture
    def sample_data(self):
        """创建测试用的市场数据"""
        np.random.seed(42)
        dates = pd.date_range(start='2025-01-01', periods=100, freq='D')
        returns = pd.Series(np.random.normal(0, 0.01, 100), index=dates)
        data = pd.DataFrame({
            'close': 100 * (1 + returns).cumprod(),
            'returns': returns
        })
        return data, returns
    
    def test_mine_factors_basic(self, miner, sample_data):
        """测试基本的元挖掘"""
        data, returns = sample_data
        
        factors = miner.mine_factors(data, returns)
        
        assert isinstance(factors, list)
        # 元挖掘器返回推荐因子
        for factor in factors:
            assert isinstance(factor, FactorMetadata)
            assert factor.factor_type == MinerType.UNIFIED
    
    def test_mine_factors_empty_data(self, miner):
        """测试空数据的元挖掘"""
        data = pd.DataFrame()
        returns = pd.Series(dtype='float64')
        
        with pytest.raises(ValueError, match="输入数据不能为空"):
            miner.mine_factors(data, returns)

    def test_mine_factors_empty_returns(self, miner):
        """测试空收益率的元挖掘"""
        data = pd.DataFrame({'close': [100, 101, 102]})
        returns = pd.Series(dtype='float64')
        
        with pytest.raises(ValueError, match="收益率数据不能为空"):
            miner.mine_factors(data, returns)
    
    def test_mine_factors_updates_metadata(self, miner, sample_data):
        """测试元挖掘更新元数据"""
        data, returns = sample_data
        
        initial_factor_count = miner.metadata.total_factors_discovered
        
        factors = miner.mine_factors(data, returns)
        
        assert miner.metadata.status == MinerStatus.COMPLETED
        assert miner.metadata.total_factors_discovered >= initial_factor_count
        assert miner.metadata.last_run_time is not None
    
    def test_mine_factors_without_returns_column(self, miner):
        """测试数据中没有returns列的情况"""
        np.random.seed(42)
        dates = pd.date_range(start='2025-01-01', periods=100, freq='D')
        returns = pd.Series(np.random.normal(0, 0.01, 100), index=dates)
        data = pd.DataFrame({
            'close': 100 * (1 + returns).cumprod()
        })
        
        factors = miner.mine_factors(data, returns)
        
        assert isinstance(factors, list)


class TestGetPerformanceSummary:
    """测试获取性能摘要"""
    
    @pytest.fixture
    def miner_with_data(self):
        """创建带有数据的MetaMiner实例"""
        miner = MetaMiner(min_samples=3)
        
        # 添加历史记录
        for miner_type in [MinerType.GENETIC, MinerType.SENTIMENT]:
            for i in range(5):
                perf = MinerPerformance(
                    miner_type=miner_type,
                    success_rate=0.9,
                    avg_fitness=0.7 + i * 0.02,
                    avg_ic=0.04,
                    avg_ir=0.25,
                    execution_time=5.0,
                    factor_count=10,
                    last_update=datetime.now()
                )
                miner.performance_history[miner_type].append(perf)
        
        # 添加市场状态历史
        miner.market_regime_history.append((datetime.now(), 'bull'))
        
        return miner
    
    def test_get_performance_summary(self, miner_with_data):
        """测试获取性能摘要"""
        summary = miner_with_data.get_performance_summary()
        
        assert 'total_miners_tracked' in summary
        assert 'total_records' in summary
        assert 'market_regime_history_length' in summary
        assert 'current_market_regime' in summary
        assert 'top_performers' in summary
        
        assert summary['total_miners_tracked'] == 2
        assert summary['total_records'] == 10
        assert summary['market_regime_history_length'] == 1
        assert summary['current_market_regime'] == 'bull'

    def test_get_performance_summary_empty(self):
        """测试空数据时获取性能摘要"""
        miner = MetaMiner()
        
        summary = miner.get_performance_summary()
        
        assert summary['total_miners_tracked'] == 0
        assert summary['total_records'] == 0
        assert summary['current_market_regime'] == 'unknown'
        assert len(summary['top_performers']) == 0
    
    def test_top_performers_sorted(self, miner_with_data):
        """测试top_performers按适应度排序"""
        summary = miner_with_data.get_performance_summary()
        
        top_performers = summary['top_performers']
        
        if len(top_performers) > 1:
            for i in range(len(top_performers) - 1):
                assert top_performers[i]['avg_fitness'] >= top_performers[i + 1]['avg_fitness']


class TestRegimeBonus:
    """测试市场状态适配加成"""
    
    @pytest.fixture
    def miner(self):
        """创建测试用的MetaMiner实例"""
        return MetaMiner()
    
    def test_bull_market_bonus(self, miner):
        """测试牛市加成"""
        # 牛市应该对情绪挖掘器有加成
        sentiment_bonus = miner._get_regime_bonus(MinerType.SENTIMENT, 'bull')
        
        # 检查是否返回数值（可能是0或正数）
        assert isinstance(sentiment_bonus, float)
    
    def test_bear_market_bonus(self, miner):
        """测试熊市加成"""
        # 熊市应该对价量挖掘器有加成
        price_volume_bonus = miner._get_regime_bonus(MinerType.PRICE_VOLUME, 'bear')
        
        assert isinstance(price_volume_bonus, float)
    
    def test_volatile_market_bonus(self, miner):
        """测试高波动市场加成"""
        # 高波动市场应该对高频和事件驱动挖掘器有加成
        hf_bonus = miner._get_regime_bonus(MinerType.HIGH_FREQUENCY, 'volatile')
        event_bonus = miner._get_regime_bonus(MinerType.EVENT_DRIVEN, 'volatile')
        
        assert isinstance(hf_bonus, float)
        assert isinstance(event_bonus, float)
    
    def test_crisis_market_bonus(self, miner):
        """测试危机市场加成"""
        # 危机市场应该对网络挖掘器有加成
        network_bonus = miner._get_regime_bonus(MinerType.NETWORK, 'crisis')
        
        assert isinstance(network_bonus, float)
    
    def test_unknown_regime_bonus(self, miner):
        """测试未知市场状态加成"""
        bonus = miner._get_regime_bonus(MinerType.GENETIC, 'unknown')
        
        assert bonus == 0.0


class TestMinerPerformanceDataclass:
    """测试MinerPerformance数据类"""
    
    def test_create_miner_performance(self):
        """测试创建MinerPerformance实例"""
        perf = MinerPerformance(
            miner_type=MinerType.GENETIC,
            success_rate=0.9,
            avg_fitness=0.75,
            avg_ic=0.05,
            avg_ir=0.3,
            execution_time=5.0,
            factor_count=10,
            last_update=datetime.now()
        )
        
        assert perf.miner_type == MinerType.GENETIC
        assert perf.success_rate == 0.9
        assert perf.avg_fitness == 0.75
        assert perf.avg_ic == 0.05
        assert perf.avg_ir == 0.3
        assert perf.execution_time == 5.0
        assert perf.factor_count == 10


class TestMinerRecommendationDataclass:
    """测试MinerRecommendation数据类"""
    
    def test_create_miner_recommendation(self):
        """测试创建MinerRecommendation实例"""
        recommendation = MinerRecommendation(
            recommended_miners=[MinerType.GENETIC, MinerType.SENTIMENT],
            priority_scores={MinerType.GENETIC: 0.8, MinerType.SENTIMENT: 0.7},
            reasoning="Test reasoning",
            market_regime='bull',
            confidence=0.85
        )
        
        assert len(recommendation.recommended_miners) == 2
        assert MinerType.GENETIC in recommendation.recommended_miners
        assert recommendation.priority_scores[MinerType.GENETIC] == 0.8
        assert recommendation.reasoning == "Test reasoning"
        assert recommendation.market_regime == 'bull'
        assert recommendation.confidence == 0.85


class TestGenerateReasoning:
    """测试生成推荐理由"""
    
    @pytest.fixture
    def miner(self):
        """创建测试用的MetaMiner实例"""
        return MetaMiner()
    
    def test_generate_reasoning_with_miners(self, miner):
        """测试有推荐挖掘器时生成理由"""
        recommended_miners = [MinerType.GENETIC, MinerType.SENTIMENT]
        priority_scores = {MinerType.GENETIC: 0.8, MinerType.SENTIMENT: 0.7}
        
        reasoning = miner._generate_reasoning(
            recommended_miners,
            priority_scores,
            'bull'
        )
        
        assert 'bull' in reasoning
        assert 'genetic' in reasoning.lower()
        assert '0.8' in reasoning
    
    def test_generate_reasoning_empty_miners(self, miner):
        """测试无推荐挖掘器时生成理由"""
        reasoning = miner._generate_reasoning([], {}, 'bull')
        
        assert reasoning == "无可用推荐"


class TestCalculateConfidence:
    """测试计算推荐置信度"""
    
    @pytest.fixture
    def miner_with_history(self):
        """创建带有历史记录的MetaMiner实例"""
        miner = MetaMiner(min_samples=3)
        
        # 添加历史记录
        for i in range(5):
            perf = MinerPerformance(
                miner_type=MinerType.GENETIC,
                success_rate=0.9,
                avg_fitness=0.7,
                avg_ic=0.04,
                avg_ir=0.25,
                execution_time=5.0,
                factor_count=10,
                last_update=datetime.now()
            )
            miner.performance_history[MinerType.GENETIC].append(perf)
        
        return miner
    
    def test_calculate_confidence_with_scores(self, miner_with_history):
        """测试有得分时计算置信度"""
        miner_scores = {
            MinerType.GENETIC: 0.8,
            MinerType.SENTIMENT: 0.5
        }
        
        confidence = miner_with_history._calculate_confidence(miner_scores)
        
        assert 0 <= confidence <= 1
    
    def test_calculate_confidence_empty_scores(self, miner_with_history):
        """测试空得分时计算置信度"""
        confidence = miner_with_history._calculate_confidence({})
        
        assert confidence == 0.0
    
    def test_calculate_confidence_single_score(self, miner_with_history):
        """测试单个得分时计算置信度"""
        miner_scores = {MinerType.GENETIC: 0.8}
        
        confidence = miner_with_history._calculate_confidence(miner_scores)
        
        assert 0 <= confidence <= 1


class TestWindowManagement:
    """测试窗口管理"""
    
    def test_performance_history_window(self):
        """测试性能历史窗口管理"""
        miner = MetaMiner(optimization_window=1)  # 1天窗口
        
        # 添加旧记录
        old_perf = MinerPerformance(
            miner_type=MinerType.GENETIC,
            success_rate=0.9,
            avg_fitness=0.7,
            avg_ic=0.04,
            avg_ir=0.25,
            execution_time=5.0,
            factor_count=10,
            last_update=datetime.now() - timedelta(days=2)  # 2天前
        )
        miner.performance_history[MinerType.GENETIC].append(old_perf)
        
        # 添加新记录
        factors = [
            FactorMetadata(
                factor_id="factor_1",
                factor_name="TestFactor",
                factor_type=MinerType.GENETIC,
                data_source="test",
                discovery_date=datetime.now(),
                discoverer="test",
                expression="close",
                fitness=0.8,
                ic=0.05,
                ir=0.3,
                sharpe=1.5
            )
        ]
        result = MiningResult(
            miner_type=MinerType.GENETIC,
            factors=factors,
            execution_time=5.0,
            success=True,
            error=None
        )
        miner.record_mining_result(result, execution_time=5.0)
        
        # 旧记录应该被清理
        assert len(miner.performance_history[MinerType.GENETIC]) == 1

    def test_market_regime_history_window(self):
        """测试市场状态历史窗口管理"""
        miner = MetaMiner(optimization_window=1)  # 1天窗口
        
        # 添加旧记录
        miner.market_regime_history.append(
            (datetime.now() - timedelta(days=2), 'bull')
        )
        
        # 检测新的市场状态
        np.random.seed(42)
        dates = pd.date_range(start='2025-01-01', periods=100, freq='D')
        returns = pd.Series(np.random.normal(0, 0.01, 100), index=dates)
        data = pd.DataFrame({'returns': returns})
        
        miner.detect_market_regime(data)
        
        # 旧记录应该被清理
        assert len(miner.market_regime_history) == 1


class TestEdgeCases:
    """测试边界情况"""
    
    def test_very_small_data(self):
        """测试非常小的数据集"""
        miner = MetaMiner()
        
        dates = pd.date_range(start='2025-01-01', periods=5, freq='D')
        returns = pd.Series([0.01, -0.01, 0.02, -0.02, 0.01], index=dates)
        data = pd.DataFrame({'returns': returns})
        
        # 应该能处理小数据集
        regime = miner.detect_market_regime(data)
        assert regime in ['bull', 'bear', 'volatile', 'stable', 'crisis', 'unknown']
    
    def test_all_zero_returns(self):
        """测试全零收益率"""
        miner = MetaMiner()
        
        dates = pd.date_range(start='2025-01-01', periods=100, freq='D')
        returns = pd.Series(np.zeros(100), index=dates)
        data = pd.DataFrame({'returns': returns})
        
        regime = miner.detect_market_regime(data)
        assert regime in ['stable', 'unknown']
    
    def test_extreme_returns(self):
        """测试极端收益率"""
        miner = MetaMiner()
        
        dates = pd.date_range(start='2025-01-01', periods=100, freq='D')
        returns = pd.Series(
            np.concatenate([
                np.array([0.5] * 50),  # 极端正收益
                np.array([-0.5] * 50)  # 极端负收益
            ]),
            index=dates
        )
        data = pd.DataFrame({'returns': returns})
        
        regime = miner.detect_market_regime(data)
        assert regime in ['volatile', 'crisis', 'bull', 'bear']
    
    def test_nan_in_returns(self):
        """测试收益率中包含NaN"""
        miner = MetaMiner()
        
        dates = pd.date_range(start='2025-01-01', periods=100, freq='D')
        returns = pd.Series(np.random.normal(0, 0.01, 100), index=dates)
        returns.iloc[50] = np.nan
        data = pd.DataFrame({'returns': returns})
        
        # 应该能处理NaN
        regime = miner.detect_market_regime(data)
        assert isinstance(regime, str)
