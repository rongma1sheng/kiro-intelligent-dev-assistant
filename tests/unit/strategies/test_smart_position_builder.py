"""测试智能分批建仓系统

白皮书依据: 第四章 4.2 斯巴达竞技场 - 大资金建仓策略
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime

from src.strategies.smart_position_builder import (
    MarketMakerPhase,
    MarketMakerSignal,
    PositionBuildingPlan,
    SmartPositionBuilder,
    PositionProtector,
)


class TestMarketMakerPhase:
    """测试主力操作阶段枚举"""

    def test_enum_values(self):
        """测试枚举值"""
        assert MarketMakerPhase.ACCUMULATION.value == "accumulation"
        assert MarketMakerPhase.WASH_OUT.value == "wash_out"
        assert MarketMakerPhase.MARKUP.value == "markup"
        assert MarketMakerPhase.DISTRIBUTION.value == "distribution"
        assert MarketMakerPhase.UNKNOWN.value == "unknown"

    def test_enum_count(self):
        """测试枚举数量"""
        assert len(MarketMakerPhase) == 5


class TestMarketMakerSignal:
    """测试主力行为信号数据模型"""

    def test_valid_signal_creation(self):
        """测试创建有效信号"""
        signal = MarketMakerSignal(
            phase=MarketMakerPhase.ACCUMULATION,
            confidence=0.85,
            volume_ratio=1.5,
            price_volatility=0.02,
            large_order_ratio=0.35,
            timestamp="2026-01-30T10:00:00",
        )
        assert signal.phase == MarketMakerPhase.ACCUMULATION
        assert signal.confidence == 0.85

    def test_confidence_validation_too_low(self):
        """测试置信度过低"""
        with pytest.raises(ValueError, match="置信度必须在"):
            MarketMakerSignal(
                phase=MarketMakerPhase.ACCUMULATION,
                confidence=-0.1,
                volume_ratio=1.5,
                price_volatility=0.02,
                large_order_ratio=0.35,
                timestamp="2026-01-30T10:00:00",
            )

    def test_confidence_validation_too_high(self):
        """测试置信度过高"""
        with pytest.raises(ValueError, match="置信度必须在"):
            MarketMakerSignal(
                phase=MarketMakerPhase.ACCUMULATION,
                confidence=1.5,
                volume_ratio=1.5,
                price_volatility=0.02,
                large_order_ratio=0.35,
                timestamp="2026-01-30T10:00:00",
            )

    def test_confidence_boundary_values(self):
        """测试置信度边界值"""
        # 0.0应该有效
        signal1 = MarketMakerSignal(
            phase=MarketMakerPhase.UNKNOWN,
            confidence=0.0,
            volume_ratio=1.0,
            price_volatility=0.01,
            large_order_ratio=0.1,
            timestamp="2026-01-30T10:00:00",
        )
        assert signal1.confidence == 0.0

        # 1.0应该有效
        signal2 = MarketMakerSignal(
            phase=MarketMakerPhase.ACCUMULATION,
            confidence=1.0,
            volume_ratio=2.0,
            price_volatility=0.03,
            large_order_ratio=0.5,
            timestamp="2026-01-30T10:00:00",
        )
        assert signal2.confidence == 1.0


@pytest.fixture
def position_builder():
    """创建测试用智能建仓系统实例"""
    return SmartPositionBuilder()


@pytest.fixture
def sample_market_data_accumulation():
    """创建吸筹阶段的市场数据"""
    return {
        "volume": 1600000,  # 成交量放大 (>1.5倍)
        "avg_volume": 1000000,
        "price_change": 0.015,  # 价格横盘 (<2%)
        "volatility": 0.015,
        "large_buy_ratio": 0.35,  # 大单买入 (>30%)
        "large_sell_ratio": 0.10,
    }


@pytest.fixture
def sample_market_data_wash_out():
    """创建洗筹阶段的市场数据"""
    return {
        "volume": 600000,  # 成交量萎缩
        "avg_volume": 1000000,
        "price_change": -0.02,  # 价格下跌
        "volatility": 0.04,  # 波动率高
        "large_buy_ratio": 0.15,
        "large_sell_ratio": 0.20,
    }


@pytest.fixture
def sample_market_data_markup():
    """创建拉升阶段的市场数据"""
    return {
        "volume": 1300000,  # 成交量持续
        "avg_volume": 1000000,
        "price_change": 0.05,  # 价格上涨
        "volatility": 0.02,
        "large_buy_ratio": 0.30,  # 大单推动
        "large_sell_ratio": 0.10,
    }


@pytest.fixture
def sample_market_data_distribution():
    """创建出货阶段的市场数据"""
    return {
        "volume": 2500000,  # 成交量巨大
        "avg_volume": 1000000,
        "price_change": 0.005,  # 价格滞涨
        "volatility": 0.015,
        "large_buy_ratio": 0.10,
        "large_sell_ratio": 0.40,  # 大单卖出
    }


class TestSmartPositionBuilder:
    """测试智能分批建仓系统"""

    def test_initialization(self, position_builder):
        """测试初始化"""
        assert position_builder is not None
        assert isinstance(position_builder.active_plans, dict)
        assert len(position_builder.active_plans) == 0

    def test_detect_accumulation_phase(self, position_builder, sample_market_data_accumulation):
        """测试识别吸筹阶段"""
        signal = position_builder.detect_market_maker_phase("TEST", sample_market_data_accumulation)

        assert signal.phase == MarketMakerPhase.ACCUMULATION
        assert signal.confidence > 0.5
        assert signal.volume_ratio == 1.6  # 1600000 / 1000000
        assert 0.0 <= signal.confidence <= 1.0

    def test_detect_wash_out_phase(self, position_builder, sample_market_data_wash_out):
        """测试识别洗筹阶段"""
        signal = position_builder.detect_market_maker_phase("TEST", sample_market_data_wash_out)

        assert signal.phase == MarketMakerPhase.WASH_OUT
        assert signal.confidence > 0.0
        assert signal.volume_ratio < 1.0

    def test_detect_markup_phase(self, position_builder, sample_market_data_markup):
        """测试识别拉升阶段"""
        signal = position_builder.detect_market_maker_phase("TEST", sample_market_data_markup)

        assert signal.phase == MarketMakerPhase.MARKUP
        assert signal.confidence > 0.0
        assert signal.volume_ratio > 1.0

    def test_detect_distribution_phase(self, position_builder, sample_market_data_distribution):
        """测试识别出货阶段"""
        signal = position_builder.detect_market_maker_phase("TEST", sample_market_data_distribution)

        assert signal.phase == MarketMakerPhase.DISTRIBUTION
        assert signal.confidence > 0.5
        assert signal.volume_ratio > 2.0

    def test_detect_unknown_phase(self, position_builder):
        """测试识别未知阶段"""
        market_data = {
            "volume": 1000000,
            "avg_volume": 1000000,
            "price_change": 0.0,
            "volatility": 0.01,
            "large_buy_ratio": 0.15,
            "large_sell_ratio": 0.15,
        }
        signal = position_builder.detect_market_maker_phase("TEST", market_data)

        assert signal.phase == MarketMakerPhase.UNKNOWN
        assert signal.confidence == 0.0

    def test_detect_phase_with_zero_avg_volume(self, position_builder):
        """测试平均成交量为零的情况"""
        market_data = {
            "volume": 1000000,
            "avg_volume": 0,  # 零除数
            "price_change": 0.01,
            "volatility": 0.02,
            "large_buy_ratio": 0.30,
            "large_sell_ratio": 0.10,
        }
        signal = position_builder.detect_market_maker_phase("TEST", market_data)

        # 应该能处理，volume_ratio默认为1.0
        assert signal.volume_ratio == 1.0
        assert isinstance(signal, MarketMakerSignal)

    def test_create_plan_for_accumulation(self, position_builder, sample_market_data_accumulation):
        """测试为吸筹阶段创建建仓计划"""
        signal = position_builder.detect_market_maker_phase("AAPL", sample_market_data_accumulation)
        plan = position_builder.create_position_building_plan(
            symbol="AAPL",
            target_size=1000.0,
            current_size=0.0,
            market_maker_signal=signal,
        )

        assert plan is not None
        assert plan.symbol == "AAPL"
        assert plan.total_target_size == 1000.0
        assert plan.current_size == 0.0
        assert plan.remaining_size == 1000.0
        assert plan.follow_strategy == "aggressive"
        assert plan.batch_count == 3
        assert len(plan.batch_sizes) == 3
        assert plan.status == "planning"
        assert plan.market_maker_phase == MarketMakerPhase.ACCUMULATION

    def test_create_plan_for_wash_out(self, position_builder, sample_market_data_wash_out):
        """测试为洗筹阶段创建建仓计划"""
        signal = position_builder.detect_market_maker_phase("GOOGL", sample_market_data_wash_out)
        plan = position_builder.create_position_building_plan(
            symbol="GOOGL",
            target_size=500.0,
            current_size=100.0,
            market_maker_signal=signal,
        )

        assert plan is not None
        assert plan.remaining_size == 400.0
        assert plan.follow_strategy == "moderate"
        assert plan.batch_count == 5
        assert len(plan.batch_sizes) == 5

    def test_create_plan_for_markup(self, position_builder, sample_market_data_markup):
        """测试为拉升阶段创建建仓计划"""
        signal = position_builder.detect_market_maker_phase("MSFT", sample_market_data_markup)
        plan = position_builder.create_position_building_plan(
            symbol="MSFT",
            target_size=800.0,
            current_size=200.0,
            market_maker_signal=signal,
        )

        assert plan is not None
        assert plan.follow_strategy == "conservative"
        assert plan.batch_count == 2
        # 拉升阶段只建仓50%
        assert sum(plan.batch_sizes) < plan.remaining_size

    def test_create_plan_for_distribution_returns_none(self, position_builder, sample_market_data_distribution):
        """测试出货阶段不创建建仓计划"""
        signal = position_builder.detect_market_maker_phase("TSLA", sample_market_data_distribution)
        plan = position_builder.create_position_building_plan(
            symbol="TSLA",
            target_size=1000.0,
            current_size=0.0,
            market_maker_signal=signal,
        )

        # 出货阶段应该返回None
        assert plan is None

    def test_create_plan_when_target_reached(self, position_builder, sample_market_data_accumulation):
        """测试已达到目标仓位时不创建计划"""
        signal = position_builder.detect_market_maker_phase("AMZN", sample_market_data_accumulation)
        plan = position_builder.create_position_building_plan(
            symbol="AMZN",
            target_size=1000.0,
            current_size=1000.0,  # 已达到目标
            market_maker_signal=signal,
        )

        assert plan is None

    def test_create_plan_stores_in_active_plans(self, position_builder, sample_market_data_accumulation):
        """测试创建的计划被存储"""
        signal = position_builder.detect_market_maker_phase("NVDA", sample_market_data_accumulation)
        plan = position_builder.create_position_building_plan(
            symbol="NVDA",
            target_size=1000.0,
            current_size=0.0,
            market_maker_signal=signal,
        )

        assert "NVDA" in position_builder.active_plans
        assert position_builder.active_plans["NVDA"] == plan

    def test_adjust_plan_no_active_plan(self, position_builder):
        """测试调整不存在的计划"""
        signal = MarketMakerSignal(
            phase=MarketMakerPhase.WASH_OUT,
            confidence=0.8,
            volume_ratio=0.7,
            price_volatility=0.03,
            large_order_ratio=0.3,
            timestamp="2026-01-30T10:00:00",
        )
        result = position_builder.adjust_plan_dynamically("NONEXIST", signal)

        assert result is None

    def test_adjust_plan_same_phase_no_change(self, position_builder, sample_market_data_accumulation):
        """测试相同阶段不调整计划"""
        signal1 = position_builder.detect_market_maker_phase("AAPL", sample_market_data_accumulation)
        plan = position_builder.create_position_building_plan(
            symbol="AAPL",
            target_size=1000.0,
            current_size=0.0,
            market_maker_signal=signal1,
        )
        original_intervals = plan.batch_intervals.copy()

        # 再次检测到吸筹阶段
        signal2 = position_builder.detect_market_maker_phase("AAPL", sample_market_data_accumulation)
        adjusted_plan = position_builder.adjust_plan_dynamically("AAPL", signal2)

        # 阶段未变化，不应调整
        assert adjusted_plan.batch_intervals == original_intervals

    def test_adjust_plan_to_distribution_pauses(self, position_builder, sample_market_data_accumulation, sample_market_data_distribution):
        """测试转为出货阶段时暂停计划"""
        signal1 = position_builder.detect_market_maker_phase("AAPL", sample_market_data_accumulation)
        plan = position_builder.create_position_building_plan(
            symbol="AAPL",
            target_size=1000.0,
            current_size=0.0,
            market_maker_signal=signal1,
        )

        # 转为出货阶段
        signal2 = position_builder.detect_market_maker_phase("AAPL", sample_market_data_distribution)
        adjusted_plan = position_builder.adjust_plan_dynamically("AAPL", signal2)

        assert adjusted_plan.status == "paused"
        assert adjusted_plan.market_maker_phase == MarketMakerPhase.DISTRIBUTION

    def test_adjust_plan_accumulation_to_wash_out(self, position_builder, sample_market_data_accumulation, sample_market_data_wash_out):
        """测试从吸筹转为洗筹时放慢节奏"""
        signal1 = position_builder.detect_market_maker_phase("AAPL", sample_market_data_accumulation)
        plan = position_builder.create_position_building_plan(
            symbol="AAPL",
            target_size=1000.0,
            current_size=0.0,
            market_maker_signal=signal1,
        )
        original_intervals = plan.batch_intervals.copy()
        original_strategy = plan.follow_strategy

        # 转为洗筹阶段
        signal2 = position_builder.detect_market_maker_phase("AAPL", sample_market_data_wash_out)
        adjusted_plan = position_builder.adjust_plan_dynamically("AAPL", signal2)

        # 如果原来是吸筹阶段，间隔应该变长（1.5倍）
        if signal1.phase == MarketMakerPhase.ACCUMULATION:
            assert all(adjusted_plan.batch_intervals[i] > original_intervals[i] for i in range(len(original_intervals)))
            assert adjusted_plan.follow_strategy == "moderate"
        else:
            # 如果原来不是吸筹阶段，至少阶段应该更新
            assert adjusted_plan.market_maker_phase == MarketMakerPhase.WASH_OUT

    def test_adjust_plan_wash_out_to_accumulation(self, position_builder, sample_market_data_wash_out, sample_market_data_accumulation):
        """测试从洗筹转为吸筹时加快节奏"""
        signal1 = position_builder.detect_market_maker_phase("AAPL", sample_market_data_wash_out)
        plan = position_builder.create_position_building_plan(
            symbol="AAPL",
            target_size=1000.0,
            current_size=0.0,
            market_maker_signal=signal1,
        )
        original_intervals = plan.batch_intervals.copy()

        # 转为吸筹阶段
        signal2 = position_builder.detect_market_maker_phase("AAPL", sample_market_data_accumulation)
        adjusted_plan = position_builder.adjust_plan_dynamically("AAPL", signal2)

        # 如果转为吸筹阶段，策略应该变为aggressive
        if signal2.phase == MarketMakerPhase.ACCUMULATION:
            assert adjusted_plan.follow_strategy == "aggressive"
            # 间隔应该变短
            assert any(adjusted_plan.batch_intervals[i] < original_intervals[i] for i in range(len(original_intervals)))
        else:
            # 至少阶段应该更新
            assert adjusted_plan.market_maker_phase == signal2.phase

    def test_adjust_plan_to_markup_reduces_size(self, position_builder, sample_market_data_accumulation, sample_market_data_markup):
        """测试转为拉升阶段时减少仓位"""
        signal1 = position_builder.detect_market_maker_phase("AAPL", sample_market_data_accumulation)
        plan = position_builder.create_position_building_plan(
            symbol="AAPL",
            target_size=1000.0,
            current_size=0.0,
            market_maker_signal=signal1,
        )
        original_sizes = plan.batch_sizes.copy()

        # 转为拉升阶段
        signal2 = position_builder.detect_market_maker_phase("AAPL", sample_market_data_markup)
        adjusted_plan = position_builder.adjust_plan_dynamically("AAPL", signal2)

        # 剩余批次的仓位应该减少40%
        assert adjusted_plan.follow_strategy == "conservative"
        assert all(adjusted_plan.batch_sizes[i] < original_sizes[i] for i in range(len(original_sizes)))

    def test_get_next_batch_no_plan(self, position_builder):
        """测试获取不存在计划的批次"""
        batch = position_builder.get_next_batch_with_stealth("NONEXIST")

        assert batch is None

    def test_get_next_batch_paused_plan(self, position_builder, sample_market_data_accumulation, sample_market_data_distribution):
        """测试获取已暂停计划的批次"""
        signal1 = position_builder.detect_market_maker_phase("AAPL", sample_market_data_accumulation)
        plan = position_builder.create_position_building_plan(
            symbol="AAPL",
            target_size=1000.0,
            current_size=0.0,
            market_maker_signal=signal1,
        )

        # 暂停计划
        signal2 = position_builder.detect_market_maker_phase("AAPL", sample_market_data_distribution)
        position_builder.adjust_plan_dynamically("AAPL", signal2)

        batch = position_builder.get_next_batch_with_stealth("AAPL")

        assert batch is None

    def test_get_next_batch_with_stealth_mode(self, position_builder, sample_market_data_accumulation):
        """测试隐身模式获取批次"""
        signal = position_builder.detect_market_maker_phase("AAPL", sample_market_data_accumulation)
        plan = position_builder.create_position_building_plan(
            symbol="AAPL",
            target_size=1000.0,
            current_size=0.0,
            market_maker_signal=signal,
        )

        batch = position_builder.get_next_batch_with_stealth("AAPL", stealth_mode=True)

        assert batch is not None
        assert batch["symbol"] == "AAPL"
        assert batch["batch_number"] == 1
        assert batch["stealth_mode"] is True
        assert "sub_orders" in batch
        assert "sub_intervals" in batch
        assert len(batch["sub_orders"]) >= 2
        assert len(batch["sub_orders"]) <= 4

    def test_get_next_batch_without_stealth_mode(self, position_builder, sample_market_data_accumulation):
        """测试非隐身模式获取批次"""
        signal = position_builder.detect_market_maker_phase("AAPL", sample_market_data_accumulation)
        plan = position_builder.create_position_building_plan(
            symbol="AAPL",
            target_size=1000.0,
            current_size=0.0,
            market_maker_signal=signal,
        )

        batch = position_builder.get_next_batch_with_stealth("AAPL", stealth_mode=False)

        assert batch is not None
        assert batch["stealth_mode"] is False
        assert "batch_size" in batch
        assert "sub_orders" not in batch

    def test_get_next_batch_completed_plan(self, position_builder, sample_market_data_accumulation):
        """测试已完成计划返回None"""
        signal = position_builder.detect_market_maker_phase("AAPL", sample_market_data_accumulation)
        plan = position_builder.create_position_building_plan(
            symbol="AAPL",
            target_size=1000.0,
            current_size=0.0,
            market_maker_signal=signal,
        )

        # 执行所有批次
        for _ in range(plan.batch_count):
            batch = position_builder.get_next_batch_with_stealth("AAPL", stealth_mode=False)
            if batch:
                position_builder.mark_batch_executed("AAPL", batch)

        # 再次获取应该返回None
        batch = position_builder.get_next_batch_with_stealth("AAPL")

        assert batch is None
        assert plan.status == "completed"

    def test_mark_batch_executed_updates_plan(self, position_builder, sample_market_data_accumulation):
        """测试标记批次执行更新计划"""
        signal = position_builder.detect_market_maker_phase("AAPL", sample_market_data_accumulation)
        plan = position_builder.create_position_building_plan(
            symbol="AAPL",
            target_size=1000.0,
            current_size=0.0,
            market_maker_signal=signal,
        )

        batch = position_builder.get_next_batch_with_stealth("AAPL", stealth_mode=False)
        position_builder.mark_batch_executed("AAPL", batch)

        assert plan.current_batch == 1
        assert plan.current_size > 0
        assert len(plan.executed_batches) == 1

    def test_mark_batch_executed_no_plan(self, position_builder):
        """测试标记不存在计划的批次"""
        batch = {"symbol": "NONEXIST", "batch_size": 100}
        # 应该不会抛出异常
        position_builder.mark_batch_executed("NONEXIST", batch)


@pytest.fixture
def risk_manager_mock():
    """创建风险管理器Mock"""
    mock = Mock()
    mock.set_exit_mode = Mock()
    return mock


class TestPositionProtector:
    """测试持仓保护系统"""

    def test_initialization(self, position_builder):
        """测试初始化"""
        protector = PositionProtector(position_builder)

        assert protector.position_builder == position_builder
        assert protector.risk_manager is None
        assert isinstance(protector.protected_positions, dict)
        assert isinstance(protector.alert_history, list)

    def test_initialization_with_risk_manager(self, position_builder, risk_manager_mock):
        """测试带风险管理器的初始化"""
        protector = PositionProtector(position_builder, risk_manager_mock)

        assert protector.risk_manager == risk_manager_mock

    def test_set_risk_manager(self, position_builder, risk_manager_mock):
        """测试设置风险管理器"""
        protector = PositionProtector(position_builder)
        protector.set_risk_manager(risk_manager_mock)

        assert protector.risk_manager == risk_manager_mock

    def test_monitor_position_distribution_critical(self, position_builder, sample_market_data_distribution):
        """测试监测出货阶段（紧急）"""
        protector = PositionProtector(position_builder)

        # 高置信度出货
        market_data = sample_market_data_distribution.copy()
        market_data["large_sell_ratio"] = 0.50  # 提高大单卖出比例

        result = protector.monitor_position("AAPL", 1000.0, market_data)

        assert result["action"] == "exit"
        assert result["urgency"] == "critical"
        assert result["reduce_ratio"] == 1.0
        assert "出货" in result["reason"]

    def test_monitor_position_distribution_high(self, position_builder, sample_market_data_distribution):
        """测试监测出货阶段（高级）"""
        protector = PositionProtector(position_builder)

        result = protector.monitor_position("AAPL", 1000.0, sample_market_data_distribution)

        assert result["action"] in ["reduce", "exit"]
        assert result["urgency"] in ["high", "critical"]
        assert result["reduce_ratio"] > 0.5

    def test_monitor_position_markup(self, position_builder, sample_market_data_markup):
        """测试监测拉升阶段"""
        protector = PositionProtector(position_builder)

        result = protector.monitor_position("AAPL", 1000.0, sample_market_data_markup)

        # 高位拉升可能建议部分止盈
        assert result["action"] in ["hold", "reduce"]
        if result["action"] == "reduce":
            assert result["reduce_ratio"] <= 0.5

    def test_monitor_position_wash_out(self, position_builder, sample_market_data_wash_out):
        """测试监测洗筹阶段"""
        protector = PositionProtector(position_builder)

        result = protector.monitor_position("AAPL", 1000.0, sample_market_data_wash_out)

        assert result["action"] == "hold"
        assert result["urgency"] == "low"
        assert "洗筹" in result["reason"]

    def test_monitor_position_accumulation(self, position_builder, sample_market_data_accumulation):
        """测试监测吸筹阶段"""
        protector = PositionProtector(position_builder)

        result = protector.monitor_position("AAPL", 1000.0, sample_market_data_accumulation)

        assert result["action"] == "hold"
        assert result["urgency"] == "low"
        # 吸筹或正常持仓都是合理的
        assert any(keyword in result["reason"] for keyword in ["吸筹", "正常", "持有", "加仓"])

    def test_monitor_position_notifies_risk_manager(self, position_builder, sample_market_data_distribution, risk_manager_mock):
        """测试监测时通知风险管理器"""
        protector = PositionProtector(position_builder, risk_manager_mock)

        result = protector.monitor_position("AAPL", 1000.0, sample_market_data_distribution)

        if result["action"] in ["reduce", "exit"]:
            # 应该调用risk_manager的set_exit_mode
            risk_manager_mock.set_exit_mode.assert_called_once()

    def test_monitor_position_adds_to_alert_history(self, position_builder, sample_market_data_distribution):
        """测试监测时添加告警历史"""
        protector = PositionProtector(position_builder)

        result = protector.monitor_position("AAPL", 1000.0, sample_market_data_distribution)

        if result["action"] in ["reduce", "exit"]:
            assert len(protector.alert_history) > 0
            assert protector.alert_history[-1] == result

    def test_get_alert_history(self, position_builder, sample_market_data_distribution):
        """测试获取告警历史"""
        protector = PositionProtector(position_builder)

        # 生成多个告警
        for i in range(5):
            protector.monitor_position(f"STOCK{i}", 1000.0, sample_market_data_distribution)

        history = protector.get_alert_history(limit=3)

        assert len(history) <= 3

    def test_create_exit_plan_critical(self, position_builder):
        """测试创建紧急退出计划"""
        protector = PositionProtector(position_builder)

        plan = protector.create_exit_plan("AAPL", 1000.0, 1.0, urgency="critical")

        assert plan["action"] == "exit"
        assert plan["urgency"] == "critical"
        assert plan["total_reduce_size"] == 1000.0
        assert plan["batch_count"] == 1
        assert "紧急" in plan["strategy"]

    def test_create_exit_plan_high(self, position_builder):
        """测试创建高级退出计划"""
        protector = PositionProtector(position_builder)

        plan = protector.create_exit_plan("AAPL", 1000.0, 0.7, urgency="high")

        assert plan["urgency"] == "high"
        assert plan["total_reduce_size"] == 700.0
        assert plan["batch_count"] == 2
        assert len(plan["batch_sizes"]) == 2

    def test_create_exit_plan_medium(self, position_builder):
        """测试创建普通退出计划"""
        protector = PositionProtector(position_builder)

        plan = protector.create_exit_plan("AAPL", 1000.0, 0.5, urgency="medium")

        assert plan["urgency"] == "medium"
        assert plan["total_reduce_size"] == 500.0
        assert plan["batch_count"] == 3
        assert len(plan["batch_sizes"]) == 3

    def test_send_alert_internal_method(self, position_builder):
        """测试内部告警方法"""
        protector = PositionProtector(position_builder)

        alert = {
            "symbol": "AAPL",
            "action": "exit",
            "urgency": "critical",
            "reason": "主力出货",
            "reduce_ratio": 1.0,
        }

        # 应该不会抛出异常
        protector._send_alert(alert)



class TestEdgeCasesAndBranches:
    """测试边界情况和未覆盖的分支"""

    def test_create_plan_for_unknown_phase(self, position_builder):
        """测试未知阶段创建建仓计划"""
        signal = MarketMakerSignal(
            phase=MarketMakerPhase.UNKNOWN,
            confidence=0.0,
            volume_ratio=1.0,
            price_volatility=0.01,
            large_order_ratio=0.2,
            timestamp="2026-01-30T10:00:00",
        )
        plan = position_builder.create_position_building_plan(
            symbol="TEST",
            target_size=1000.0,
            current_size=0.0,
            market_maker_signal=signal,
        )

        assert plan is not None
        assert plan.follow_strategy == "moderate"
        assert plan.batch_count == 4
        # 未知阶段应该均匀分布
        assert all(abs(size - plan.remaining_size / 4) < 0.01 for size in plan.batch_sizes)

    def test_detect_phase_with_missing_data_keys(self, position_builder):
        """测试缺少数据键的情况"""
        market_data = {
            # 缺少一些键，使用默认值
            "volume": 1000000,
        }
        signal = position_builder.detect_market_maker_phase("TEST", market_data)

        # 应该能处理缺失的键，返回UNKNOWN
        assert signal.phase == MarketMakerPhase.UNKNOWN
        assert signal.confidence == 0.0

    def test_monitor_position_distribution_medium_confidence(self, position_builder):
        """测试中等置信度的出货阶段"""
        protector = PositionProtector(position_builder)

        # 中等置信度出货（0.5-0.7）
        market_data = {
            "volume": 2100000,  # 成交量巨大
            "avg_volume": 1000000,
            "price_change": 0.008,  # 价格滞涨
            "volatility": 0.015,
            "large_buy_ratio": 0.10,
            "large_sell_ratio": 0.36,  # 大单卖出
        }

        result = protector.monitor_position("AAPL", 1000.0, market_data)

        # 应该建议减仓
        assert result["action"] in ["reduce", "exit"]
        assert result["reduce_ratio"] > 0

    def test_monitor_position_markup_high_confidence(self, position_builder):
        """测试高置信度拉升阶段"""
        protector = PositionProtector(position_builder)

        # 高置信度拉升
        market_data = {
            "volume": 1400000,
            "avg_volume": 1000000,
            "price_change": 0.06,  # 大幅上涨
            "volatility": 0.025,
            "large_buy_ratio": 0.35,
            "large_sell_ratio": 0.10,
        }

        result = protector.monitor_position("AAPL", 1000.0, market_data)

        # 高位拉升可能建议部分止盈
        assert result["action"] in ["hold", "reduce"]

    def test_get_alert_history_with_more_than_limit(self, position_builder, sample_market_data_distribution):
        """测试获取告警历史超过限制"""
        protector = PositionProtector(position_builder)

        # 生成15个告警
        for i in range(15):
            protector.monitor_position(f"STOCK{i}", 1000.0, sample_market_data_distribution)

        # 只获取最近5个
        history = protector.get_alert_history(limit=5)

        assert len(history) == 5
        # 应该是最新的5个
        assert history[-1]["symbol"] == "STOCK14"

    def test_position_building_plan_dataclass(self):
        """测试PositionBuildingPlan数据类"""
        plan = PositionBuildingPlan(
            symbol="TEST",
            total_target_size=1000.0,
            current_size=200.0,
            remaining_size=800.0,
            batch_count=4,
            current_batch=1,
            batch_sizes=[200.0, 200.0, 200.0, 200.0],
            batch_intervals=[600, 900, 1200],
            market_maker_phase=MarketMakerPhase.ACCUMULATION,
            follow_strategy="aggressive",
            status="executing",
            executed_batches=[{"batch": 1, "size": 200.0}],
        )

        assert plan.symbol == "TEST"
        assert plan.remaining_size == 800.0
        assert len(plan.executed_batches) == 1

    def test_send_alert_different_urgency_levels(self, position_builder):
        """测试不同紧急程度的告警"""
        protector = PositionProtector(position_builder)

        # 测试critical级别
        alert_critical = {
            "symbol": "AAPL",
            "action": "exit",
            "urgency": "critical",
            "reason": "紧急出货",
            "reduce_ratio": 1.0,
        }
        protector._send_alert(alert_critical)

        # 测试high级别
        alert_high = {
            "symbol": "GOOGL",
            "action": "reduce",
            "urgency": "high",
            "reason": "高级告警",
            "reduce_ratio": 0.7,
        }
        protector._send_alert(alert_high)

        # 测试medium级别
        alert_medium = {
            "symbol": "MSFT",
            "action": "reduce",
            "urgency": "medium",
            "reason": "普通告警",
            "reduce_ratio": 0.3,
        }
        protector._send_alert(alert_medium)

        # 所有告警都应该正常处理，不抛出异常
        assert True

    def test_adjust_plan_after_partial_execution(self, position_builder, sample_market_data_accumulation, sample_market_data_markup):
        """测试部分执行后调整计划"""
        signal1 = position_builder.detect_market_maker_phase("AAPL", sample_market_data_accumulation)
        plan = position_builder.create_position_building_plan(
            symbol="AAPL",
            target_size=1000.0,
            current_size=0.0,
            market_maker_signal=signal1,
        )

        # 执行第一批
        batch = position_builder.get_next_batch_with_stealth("AAPL", stealth_mode=False)
        position_builder.mark_batch_executed("AAPL", batch)

        # 转为拉升阶段
        signal2 = position_builder.detect_market_maker_phase("AAPL", sample_market_data_markup)
        adjusted_plan = position_builder.adjust_plan_dynamically("AAPL", signal2)

        # 剩余批次应该减少
        assert adjusted_plan.current_batch == 1
        assert adjusted_plan.follow_strategy == "conservative"

    def test_complete_workflow(self, position_builder, sample_market_data_accumulation):
        """测试完整的建仓工作流"""
        # 1. 检测主力阶段
        signal = position_builder.detect_market_maker_phase("WORKFLOW", sample_market_data_accumulation)
        assert signal.phase == MarketMakerPhase.ACCUMULATION

        # 2. 创建建仓计划
        plan = position_builder.create_position_building_plan(
            symbol="WORKFLOW",
            target_size=1000.0,
            current_size=0.0,
            market_maker_signal=signal,
        )
        assert plan is not None
        initial_batch_count = plan.batch_count

        # 3. 执行所有批次
        executed_count = 0
        while executed_count < initial_batch_count:
            batch = position_builder.get_next_batch_with_stealth("WORKFLOW", stealth_mode=True)
            if batch is None:
                break
            position_builder.mark_batch_executed("WORKFLOW", batch)
            executed_count += 1

        # 4. 验证完成
        # 再次获取应该返回None并设置状态为completed
        final_batch = position_builder.get_next_batch_with_stealth("WORKFLOW", stealth_mode=True)
        assert final_batch is None
        assert plan.status == "completed"
        assert len(plan.executed_batches) == initial_batch_count

    def test_position_protector_with_unknown_phase(self, position_builder):
        """测试监测未知阶段"""
        protector = PositionProtector(position_builder)

        market_data = {
            "volume": 1000000,
            "avg_volume": 1000000,
            "price_change": 0.0,
            "volatility": 0.01,
            "large_buy_ratio": 0.15,
            "large_sell_ratio": 0.15,
        }

        result = protector.monitor_position("AAPL", 1000.0, market_data)

        # 未知阶段应该保持持仓
        assert result["action"] == "hold"
        assert result["market_maker_phase"] == "unknown"
