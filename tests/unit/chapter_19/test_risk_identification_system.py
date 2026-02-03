"""风险识别系统单元测试

白皮书依据: 第十九章 19.1 风险识别与评估
"""

import pytest
from datetime import datetime, timedelta

from src.risk.risk_identification_system import (
    RiskIdentificationSystem,
    RiskLevel,
    RiskEvent
)


class TestRiskIdentificationSystem:
    """风险识别系统测试"""
    
    @pytest.fixture
    def system(self):
        """创建风险识别系统实例"""
        return RiskIdentificationSystem(
            market_volatility_threshold=0.05,
            daily_loss_threshold=0.10,
            liquidity_threshold=0.20,
            system_health_threshold=0.80
        )
    
    def test_init_success(self):
        """测试初始化成功"""
        system = RiskIdentificationSystem()
        
        assert system.risk_thresholds['market_volatility'] == 0.05
        assert system.risk_thresholds['daily_loss'] == 0.10
        assert system.risk_thresholds['liquidity'] == 0.20
        assert system.risk_thresholds['system_health'] == 0.80
        assert system.risk_events == []
    
    def test_init_invalid_market_volatility(self):
        """测试无效的市场波动率阈值"""
        with pytest.raises(ValueError, match="市场波动率阈值必须在\\(0, 1\\)范围内"):
            RiskIdentificationSystem(market_volatility_threshold=1.5)
    
    def test_init_invalid_daily_loss(self):
        """测试无效的单日亏损阈值"""
        with pytest.raises(ValueError, match="单日亏损阈值必须在\\(0, 1\\)范围内"):
            RiskIdentificationSystem(daily_loss_threshold=0)
    
    def test_monitor_market_risk_high_volatility(self, system):
        """测试市场波动率过高"""
        event = system.monitor_market_risk(
            volatility=0.10,  # 超过5%阈值，2倍阈值触发CRITICAL
            daily_pnl_ratio=0.02
        )
        
        assert event is not None
        assert event.risk_type == "market_risk"
        assert event.risk_level == RiskLevel.CRITICAL  # 2倍阈值触发CRITICAL
        assert "市场波动率过高" in event.description
        assert len(system.risk_events) == 1
    
    def test_monitor_market_risk_daily_loss(self, system):
        """测试单日亏损超阈值"""
        event = system.monitor_market_risk(
            volatility=0.02,
            daily_pnl_ratio=-0.15  # 亏损15%，超过10%阈值
        )
        
        assert event is not None
        assert event.risk_type == "market_risk"
        assert event.risk_level == RiskLevel.CRITICAL
        assert "单日亏损超阈值" in event.description
    
    def test_monitor_market_risk_crash(self, system):
        """测试市场崩盘"""
        event = system.monitor_market_risk(
            volatility=0.03,
            daily_pnl_ratio=0.01,
            market_trend="crash"
        )
        
        assert event is not None
        assert event.risk_level == RiskLevel.CRITICAL
        assert "市场崩盘风险" in event.description
    
    def test_monitor_market_risk_normal(self, system):
        """测试正常市场状态"""
        event = system.monitor_market_risk(
            volatility=0.03,
            daily_pnl_ratio=0.02,
            market_trend="normal"
        )
        
        assert event is None
        assert len(system.risk_events) == 0
    
    def test_monitor_market_risk_invalid_volatility(self, system):
        """测试无效的波动率"""
        with pytest.raises(ValueError, match="市场波动率必须在\\[0, 1\\]范围内"):
            system.monitor_market_risk(volatility=1.5, daily_pnl_ratio=0.01)
    
    def test_monitor_market_risk_invalid_pnl(self, system):
        """测试无效的盈亏比例"""
        with pytest.raises(ValueError, match="单日盈亏比例必须在\\[-1, 1\\]范围内"):
            system.monitor_market_risk(volatility=0.03, daily_pnl_ratio=-1.5)
    
    def test_monitor_market_risk_invalid_trend(self, system):
        """测试无效的市场趋势"""
        with pytest.raises(ValueError, match="市场趋势必须是"):
            system.monitor_market_risk(
                volatility=0.03,
                daily_pnl_ratio=0.01,
                market_trend="unknown"
            )
    
    def test_monitor_system_risk_redis_failure(self, system):
        """测试Redis故障"""
        event = system.monitor_system_risk(
            redis_health=0.50,  # 低于80%阈值
            gpu_health=0.95,
            network_health=0.90
        )
        
        assert event is not None
        assert event.risk_type == "system_risk"
        assert "Redis" in event.description
    
    def test_monitor_system_risk_multiple_failures(self, system):
        """测试多个组件故障"""
        event = system.monitor_system_risk(
            redis_health=0.70,
            gpu_health=0.60,
            network_health=0.75
        )
        
        assert event is not None
        assert "Redis" in event.description
        assert "GPU" in event.description
    
    def test_monitor_system_risk_normal(self, system):
        """测试系统正常状态"""
        event = system.monitor_system_risk(
            redis_health=0.95,
            gpu_health=0.90,
            network_health=0.85
        )
        
        assert event is None
    
    def test_monitor_system_risk_invalid_health(self, system):
        """测试无效的健康度"""
        with pytest.raises(ValueError, match="Redis健康度必须在\\[0, 1\\]范围内"):
            system.monitor_system_risk(
                redis_health=1.5,
                gpu_health=0.90,
                network_health=0.85
            )
    
    def test_monitor_operational_risk_low_sharpe(self, system):
        """测试策略夏普比率过低"""
        event = system.monitor_operational_risk(
            strategy_sharpe=0.3,  # 低于1.0
            data_quality_score=0.90,
            overfitting_score=0.30
        )
        
        assert event is not None
        assert event.risk_type == "operational_risk"
        assert "夏普比率过低" in event.description
    
    def test_monitor_operational_risk_low_data_quality(self, system):
        """测试数据质量过低"""
        event = system.monitor_operational_risk(
            strategy_sharpe=1.5,
            data_quality_score=0.70,  # 低于80%
            overfitting_score=0.30
        )
        
        assert event is not None
        assert "数据质量过低" in event.description
    
    def test_monitor_operational_risk_overfitting(self, system):
        """测试策略过拟合"""
        event = system.monitor_operational_risk(
            strategy_sharpe=1.5,
            data_quality_score=0.90,
            overfitting_score=0.80  # 超过70%
        )
        
        assert event is not None
        assert "过拟合风险" in event.description
    
    def test_monitor_operational_risk_normal(self, system):
        """测试运营正常状态"""
        event = system.monitor_operational_risk(
            strategy_sharpe=1.5,
            data_quality_score=0.90,
            overfitting_score=0.30
        )
        
        assert event is None
    
    def test_monitor_liquidity_risk_high_spread(self, system):
        """测试买卖价差过大"""
        event = system.monitor_liquidity_risk(
            bid_ask_spread=0.25,  # 超过20%阈值
            volume_ratio=0.80,
            market_depth=0.70
        )
        
        assert event is not None
        assert event.risk_type == "liquidity_risk"
        assert "买卖价差过大" in event.description
    
    def test_monitor_liquidity_risk_low_volume(self, system):
        """测试成交量过低"""
        event = system.monitor_liquidity_risk(
            bid_ask_spread=0.10,
            volume_ratio=0.20,  # 低于30%
            market_depth=0.70
        )
        
        assert event is not None
        assert "成交量过低" in event.description
    
    def test_monitor_liquidity_risk_low_depth(self, system):
        """测试市场深度不足"""
        event = system.monitor_liquidity_risk(
            bid_ask_spread=0.10,
            volume_ratio=0.80,
            market_depth=0.40  # 低于50%
        )
        
        assert event is not None
        assert "市场深度不足" in event.description
    
    def test_monitor_liquidity_risk_normal(self, system):
        """测试流动性正常状态"""
        event = system.monitor_liquidity_risk(
            bid_ask_spread=0.10,
            volume_ratio=0.80,
            market_depth=0.70
        )
        
        assert event is None
    
    def test_monitor_counterparty_risk_low_rating(self, system):
        """测试券商评级过低"""
        event = system.monitor_counterparty_risk(
            broker_rating=0.60,  # 低于70%
            settlement_delay=1,
            credit_exposure=0.20
        )
        
        assert event is not None
        assert event.risk_type == "counterparty_risk"
        assert "券商评级过低" in event.description
    
    def test_monitor_counterparty_risk_settlement_delay(self, system):
        """测试结算延迟过长"""
        event = system.monitor_counterparty_risk(
            broker_rating=0.80,
            settlement_delay=5,  # T+5，超过T+2
            credit_exposure=0.20
        )
        
        assert event is not None
        assert "结算延迟过长" in event.description
    
    def test_monitor_counterparty_risk_high_exposure(self, system):
        """测试信用敞口过大"""
        event = system.monitor_counterparty_risk(
            broker_rating=0.80,
            settlement_delay=1,
            credit_exposure=0.40  # 超过30%
        )
        
        assert event is not None
        assert "信用敞口过大" in event.description
    
    def test_monitor_counterparty_risk_normal(self, system):
        """测试对手方正常状态"""
        event = system.monitor_counterparty_risk(
            broker_rating=0.80,
            settlement_delay=1,
            credit_exposure=0.20
        )
        
        assert event is None
    
    def test_get_overall_risk_level_no_events(self, system):
        """测试无风险事件时的整体风险等级"""
        level = system.get_overall_risk_level()
        assert level == RiskLevel.LOW
    
    def test_get_overall_risk_level_with_events(self, system):
        """测试有风险事件时的整体风险等级"""
        # 触发一个高风险事件（2倍阈值触发CRITICAL）
        system.monitor_market_risk(volatility=0.10, daily_pnl_ratio=0.02)
        
        level = system.get_overall_risk_level()
        assert level == RiskLevel.CRITICAL  # 2倍阈值触发CRITICAL
    
    def test_get_overall_risk_level_critical(self, system):
        """测试极高风险等级"""
        # 触发一个极高风险事件
        system.monitor_market_risk(volatility=0.03, daily_pnl_ratio=-0.15)
        
        level = system.get_overall_risk_level()
        assert level == RiskLevel.CRITICAL
    
    def test_get_risk_summary(self, system):
        """测试风险摘要"""
        # 触发几个风险事件
        system.monitor_market_risk(volatility=0.10, daily_pnl_ratio=0.02)
        system.monitor_system_risk(redis_health=0.70, gpu_health=0.90, network_health=0.85)
        
        summary = system.get_risk_summary()
        
        assert 'overall_risk_level' in summary
        assert 'total_events' in summary
        assert summary['total_events'] == 2
        assert 'risk_counts' in summary
        assert 'level_counts' in summary
        assert 'recent_events' in summary
    
    def test_clear_old_events(self, system):
        """测试清理旧事件"""
        # 创建一些风险事件
        system.monitor_market_risk(volatility=0.10, daily_pnl_ratio=0.02)
        system.monitor_system_risk(redis_health=0.70, gpu_health=0.90, network_health=0.85)
        
        assert len(system.risk_events) == 2
        
        # 清理（保留24小时内的）
        system.clear_old_events(hours=24)
        
        # 由于事件是刚创建的，应该都保留
        assert len(system.risk_events) == 2
    
    def test_clear_old_events_invalid_hours(self, system):
        """测试无效的保留时间"""
        with pytest.raises(ValueError, match="保留时间必须 > 0"):
            system.clear_old_events(hours=0)
