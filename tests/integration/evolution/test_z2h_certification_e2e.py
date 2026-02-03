"""Z2H认证系统端到端测试

白皮书依据: 第四章 4.2-4.3 完整验证流程

本模块测试完整的6阶段认证流程，从因子发现到实盘部署。

测试场景：
1. 完整认证流程成功场景
2. 各阶段失败场景
3. 不同认证等级场景
4. 并发认证场景
"""

from datetime import datetime
from typing import Any, Dict

import pytest

from src.evolution.multi_tier_simulation_manager import SimulationManager
from src.evolution.z2h_certification_pipeline import CertificationError, Factor, Strategy, Z2HCertificationPipeline
from src.evolution.z2h_certification_v2 import Z2HCertificationV2
from src.evolution.z2h_data_models import CertificationLevel, CertificationStatus


@pytest.fixture
def mock_broker_api():
    """创建Mock券商API"""
    from unittest.mock import AsyncMock, MagicMock

    from src.evolution.qmt_broker_api import BrokerSimulationAPI, SimulationData, SimulationStatus

    mock_api = AsyncMock(spec=BrokerSimulationAPI)

    # Mock create_simulation
    async def mock_create_simulation(strategy_code, initial_capital, duration_days):
        return f"sim_{initial_capital}_{datetime.now().timestamp()}"

    mock_api.create_simulation = mock_create_simulation

    # Mock get_simulation_data - 确保满足PLATINUM认证要求
    async def mock_get_simulation_data(simulation_id):
        data = MagicMock(spec=SimulationData)
        # PLATINUM要求: 夏普比率≥2.5, 最大回撤≤10%, 胜率≥65%
        data.performance_metrics = {
            "total_profit": 5000,
            "sharpe_ratio": 2.8,  # 满足PLATINUM要求(≥2.5)
            "max_drawdown": 0.08,  # 满足PLATINUM要求(≤0.10)
            "win_rate": 0.68,  # 满足PLATINUM要求(≥0.65)
        }
        # 生成30天的正向盈利数据
        data.daily_pnl = [100, 150, -50, 200, 120, 180, 90, 160, 110, 140] * 3  # 30天数据
        data.trades = [
            {"profit": 100, "symbol": "000001"},
            {"profit": 150, "symbol": "000002"},
            {"profit": -50, "symbol": "000003"},
            {"profit": 200, "symbol": "000004"},
            {"profit": 120, "symbol": "000005"},
        ]
        return data

    mock_api.get_simulation_data = mock_get_simulation_data

    # Mock get_simulation_status
    async def mock_get_simulation_status(simulation_id):
        status = MagicMock(spec=SimulationStatus)
        status.current_capital = 55000
        status.total_pnl = 5000
        status.position_count = 5
        status.status = "running"
        return status

    mock_api.get_simulation_status = mock_get_simulation_status

    # Mock stop_simulation
    async def mock_stop_simulation(simulation_id):
        return True

    mock_api.stop_simulation = mock_stop_simulation

    return mock_api


@pytest.fixture
def simulation_manager(mock_broker_api):
    """创建模拟盘管理器"""
    return SimulationManager(broker_api=mock_broker_api)


@pytest.fixture
def z2h_certification():
    """创建Z2H认证系统"""
    return Z2HCertificationV2()


@pytest.fixture
def certification_pipeline(z2h_certification, simulation_manager):
    """创建认证流程编排器"""
    return Z2HCertificationPipeline(z2h_certification=z2h_certification, simulation_manager=simulation_manager)


@pytest.fixture
def test_factor():
    """创建测试因子"""
    return Factor(
        factor_id="factor_001",
        factor_name="测试因子1",
        factor_expression="close / delay(close, 1) - 1",
        creation_date=datetime.now(),
    )


@pytest.fixture
def test_strategy():
    """创建测试策略"""
    return Strategy(
        strategy_id="strategy_001",
        strategy_name="测试策略1",
        strategy_type="multi_factor",
        strategy_code="# 策略代码",
        source_factors=["factor1", "factor2"],
        creation_date=datetime.now(),
    )


class TestZ2HCertificationE2E:
    """Z2H认证系统端到端测试"""

    @pytest.mark.asyncio
    async def test_complete_certification_flow_with_factor_input(self, certification_pipeline, test_factor):
        """测试从因子输入的完整认证流程

        验证6个阶段：
        1. 因子Arena三轨测试
        2. 因子组合策略生成
        3. 斯巴达Arena策略考核
        4. 模拟盘1个月验证
        5. Z2H基因胶囊认证
        6. 实盘交易部署
        """
        # 运行完整认证流程
        result = await certification_pipeline.run_complete_certification(input_entity=test_factor)

        # 验证认证成功
        assert result.passed is True
        assert result.certification_level is not None
        assert result.gene_capsule is not None
        assert result.failed_stage is None
        assert result.failure_reason is None
        assert result.certification_date is not None

        # 验证基因胶囊内容
        gene_capsule = result.gene_capsule
        assert gene_capsule.strategy_id == result.strategy_id
        assert gene_capsule.certification_level in [
            CertificationLevel.PLATINUM,
            CertificationLevel.GOLD,
            CertificationLevel.SILVER,
        ]
        assert gene_capsule.arena_overall_score > 0
        assert len(gene_capsule.arena_layer_results) == 4
        assert gene_capsule.simulation_duration_days == 30

    @pytest.mark.asyncio
    async def test_complete_certification_flow_with_strategy_input(self, certification_pipeline, test_strategy):
        """测试从策略输入的完整认证流程

        跳过因子Arena和策略生成阶段，直接从斯巴达Arena开始。
        """
        # 运行完整认证流程（跳过因子Arena）
        result = await certification_pipeline.run_complete_certification(
            input_entity=test_strategy, skip_factor_arena=True
        )

        # 验证认证成功
        assert result.passed is True
        assert result.strategy_id == test_strategy.strategy_id
        assert result.certification_level is not None
        assert result.gene_capsule is not None

        # 验证基因胶囊包含策略信息
        gene_capsule = result.gene_capsule
        assert gene_capsule.strategy_name == test_strategy.strategy_name
        assert gene_capsule.strategy_type == test_strategy.strategy_type
        assert gene_capsule.source_factors == test_strategy.source_factors

    @pytest.mark.asyncio
    async def test_certification_flow_failure_at_arena_stage(self, certification_pipeline, test_strategy, monkeypatch):
        """测试Arena阶段失败的场景"""

        # Mock Arena评估器，使其返回失败结果
        async def mock_arena_evaluation(strategy):
            from src.evolution.z2h_certification_pipeline import ArenaTestResult

            return ArenaTestResult(
                passed=False,
                overall_score=0.65,  # 低于最低要求0.75
                layer_results={
                    "layer1_investment_metrics": {"score": 0.70, "passed": False},
                    "layer2_time_stability": {"score": 0.65, "passed": False},
                    "layer3_overfitting_prevention": {"score": 0.60, "passed": False},
                    "layer4_stress_test": {"score": 0.65, "passed": False},
                },
                test_date=datetime.now(),
            )

        monkeypatch.setattr(certification_pipeline, "_stage3_sparta_arena_evaluation", mock_arena_evaluation)

        # 运行认证流程
        result = await certification_pipeline.run_complete_certification(input_entity=test_strategy)

        # 验证认证失败
        assert result.passed is False
        assert result.failed_stage == "stage3_sparta_arena"
        assert result.failure_reason == "斯巴达Arena考核未通过"
        assert result.certification_level is None
        assert result.gene_capsule is None

    @pytest.mark.asyncio
    async def test_certification_flow_failure_at_simulation_stage(
        self, certification_pipeline, test_strategy, monkeypatch
    ):
        """测试模拟盘阶段失败的场景"""

        # Mock模拟盘管理器，使其返回失败结果
        async def mock_simulation_validation(strategy, arena_result):
            from src.evolution.z2h_data_models import CapitalTier, SimulationResult

            return SimulationResult(
                passed=False,
                duration_days=30,
                tier_results={},
                best_tier=CapitalTier.TIER_1,
                overall_metrics={},
                risk_metrics={},
                market_environment_performance={},
                passed_criteria_count=6,  # 只通过6/10项标准
                failed_criteria=["月收益<5%", "夏普比率<1.2", "胜率<55%", "信息比率<0.8"],
            )

        monkeypatch.setattr(certification_pipeline, "_stage4_simulation_validation", mock_simulation_validation)

        # 运行认证流程
        result = await certification_pipeline.run_complete_certification(input_entity=test_strategy)

        # 验证认证失败
        assert result.passed is False
        assert result.failed_stage == "stage4_simulation"
        assert "模拟盘验证未通过" in result.failure_reason
        assert result.certification_level is None
        assert result.gene_capsule is None

    @pytest.mark.asyncio
    async def test_different_certification_levels(self, certification_pipeline, monkeypatch):
        """测试不同认证等级的场景"""
        # 测试数据：(Arena评分, 预期等级)
        test_cases = [
            (0.925, CertificationLevel.PLATINUM),
            (0.85, CertificationLevel.GOLD),
            (0.78, CertificationLevel.SILVER),
        ]

        for arena_score, expected_level in test_cases:
            # Mock Arena评估器，返回特定评分
            async def mock_arena_evaluation(strategy):
                from src.evolution.z2h_certification_pipeline import ArenaTestResult

                return ArenaTestResult(
                    passed=True,
                    overall_score=arena_score,
                    layer_results={
                        "layer1_investment_metrics": {"score": arena_score, "passed": True},
                        "layer2_time_stability": {"score": arena_score, "passed": True},
                        "layer3_overfitting_prevention": {"score": arena_score, "passed": True},
                        "layer4_stress_test": {"score": arena_score, "passed": True},
                    },
                    test_date=datetime.now(),
                )

            monkeypatch.setattr(certification_pipeline, "_stage3_sparta_arena_evaluation", mock_arena_evaluation)

            # 创建测试策略
            strategy = Strategy(
                strategy_id=f"strategy_{arena_score}",
                strategy_name=f"测试策略_{expected_level.value}",
                strategy_type="multi_factor",
                strategy_code="# 策略代码",
                source_factors=["factor1"],
                creation_date=datetime.now(),
            )

            # 运行认证流程
            result = await certification_pipeline.run_complete_certification(input_entity=strategy)

            # 验证认证等级
            assert result.passed is True
            assert result.certification_level == expected_level
            assert result.gene_capsule.certification_level == expected_level

    @pytest.mark.asyncio
    async def test_concurrent_certifications(self, certification_pipeline):
        """测试并发认证场景"""
        import asyncio

        # 创建多个测试策略
        strategies = [
            Strategy(
                strategy_id=f"strategy_{i:03d}",
                strategy_name=f"并发测试策略{i}",
                strategy_type="multi_factor",
                strategy_code="# 策略代码",
                source_factors=[f"factor{i}"],
                creation_date=datetime.now(),
            )
            for i in range(5)
        ]

        # 并发运行认证流程
        tasks = [certification_pipeline.run_complete_certification(input_entity=strategy) for strategy in strategies]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 验证所有认证都成功
        successful_results = [r for r in results if not isinstance(r, Exception)]
        assert len(successful_results) == 5

        for result in successful_results:
            assert result.passed is True
            assert result.certification_level is not None
            assert result.gene_capsule is not None

    @pytest.mark.asyncio
    async def test_certification_with_status_transitions(self, certification_pipeline, test_strategy):
        """测试认证状态转换的完整流程"""
        # 1. 运行认证流程
        result = await certification_pipeline.run_complete_certification(input_entity=test_strategy)

        assert result.passed is True

        # 2. 获取已认证策略
        z2h_cert = certification_pipeline.z2h_certification
        certified_strategy = z2h_cert.get_certified_strategy(result.strategy_id)

        assert certified_strategy is not None
        assert certified_strategy.status == CertificationStatus.CERTIFIED

        # 3. 降级认证（注意：需要降到更低的等级）
        # 如果当前是GOLD，降到SILVER；如果是PLATINUM，降到GOLD
        current_level = certified_strategy.certification_level

        # 确定新等级（降一级）
        level_order = [CertificationLevel.PLATINUM, CertificationLevel.GOLD, CertificationLevel.SILVER]
        current_index = level_order.index(current_level)

        if current_index < len(level_order) - 1:
            new_level = level_order[current_index + 1]

            success = await z2h_cert.downgrade_certification(
                strategy_id=result.strategy_id, new_level=new_level, reason="性能下降"
            )

            assert success is True

            # 4. 验证降级后状态
            certified_strategy = z2h_cert.get_certified_strategy(result.strategy_id)
            assert certified_strategy.status == CertificationStatus.DOWNGRADED
            assert certified_strategy.certification_level == new_level
        else:
            # 已经是最低等级，无法降级，跳过此部分测试
            pass

        # 5. 撤销认证
        success = await z2h_cert.revoke_certification(strategy_id=result.strategy_id, reason="严重违规")

        assert success is True

        # 6. 验证撤销后状态
        certified_strategy = z2h_cert.get_certified_strategy(result.strategy_id)
        assert certified_strategy.status == CertificationStatus.REVOKED

    @pytest.mark.asyncio
    async def test_certification_error_handling(self, certification_pipeline):
        """测试认证流程的错误处理"""
        # 测试无效输入
        with pytest.raises(ValueError, match="输入实体不能为空"):
            await certification_pipeline.run_complete_certification(input_entity=None)

        # 测试不支持的输入类型
        class UnsupportedEntity:
            pass

        # 修改：期望ValueError而不是CertificationError
        with pytest.raises(ValueError, match="不支持的输入类型"):
            await certification_pipeline.run_complete_certification(input_entity=UnsupportedEntity())

    @pytest.mark.asyncio
    async def test_gene_capsule_persistence_and_retrieval(self, certification_pipeline, test_strategy):
        """测试基因胶囊的持久化和检索"""
        # 运行认证流程
        result = await certification_pipeline.run_complete_certification(input_entity=test_strategy)

        assert result.passed is True

        # 获取基因胶囊
        gene_capsule = result.gene_capsule

        # 序列化基因胶囊
        gene_dict = gene_capsule.to_dict()

        # 验证序列化数据完整性
        assert "strategy_id" in gene_dict
        assert "certification_level" in gene_dict
        assert "arena_overall_score" in gene_dict
        assert "arena_layer_results" in gene_dict
        assert "simulation_duration_days" in gene_dict
        assert "max_allocation_ratio" in gene_dict

        # 反序列化基因胶囊
        from src.evolution.z2h_data_models import Z2HGeneCapsule

        restored_capsule = Z2HGeneCapsule.from_dict(gene_dict)

        # 验证反序列化后的数据一致性
        assert restored_capsule.strategy_id == gene_capsule.strategy_id
        assert restored_capsule.certification_level == gene_capsule.certification_level
        assert restored_capsule.arena_overall_score == gene_capsule.arena_overall_score
        assert len(restored_capsule.arena_layer_results) == len(gene_capsule.arena_layer_results)
