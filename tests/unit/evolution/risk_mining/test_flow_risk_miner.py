"""资金流风险挖掘器单元测试

白皮书依据: 第四章 4.1.1 专业风险因子挖掘系统 - 资金流风险

测试覆盖:
- FlowRiskFactorMiner初始化
- 主力资金撤退检测
- 承接崩塌检测
- 大单砸盘检测
- 资金流向逆转检测
- 综合风险挖掘
"""

import pytest
from datetime import datetime, timedelta
from src.evolution.risk_mining.flow_risk_miner import FlowRiskFactorMiner


class TestFlowRiskFactorMinerInit:
    """FlowRiskFactorMiner初始化测试"""
    
    def test_init_with_defaults(self):
        """测试使用默认参数初始化"""
        miner = FlowRiskFactorMiner()
        
        assert miner.capital_retreat_threshold == 500_000_000
        assert miner.large_order_threshold == 1_000_000
        assert miner.detection_window_days == 5
        assert miner.acceptance_volume_ratio == 0.3
        assert miner.large_order_count_threshold == 3
        assert miner.large_order_time_window == 300
        assert miner.flow_reversal_days == 3
    
    def test_init_with_custom_params(self):
        """测试使用自定义参数初始化"""
        miner = FlowRiskFactorMiner(
            capital_retreat_threshold=1_000_000_000,
            large_order_threshold=2_000_000,
            detection_window_days=7,
            acceptance_volume_ratio=0.4,
            large_order_count_threshold=5,
            large_order_time_window=600,
            flow_reversal_days=5
        )
        
        assert miner.capital_retreat_threshold == 1_000_000_000
        assert miner.large_order_threshold == 2_000_000
        assert miner.detection_window_days == 7
        assert miner.acceptance_volume_ratio == 0.4
        assert miner.large_order_count_threshold == 5
        assert miner.large_order_time_window == 600
        assert miner.flow_reversal_days == 5
    
    def test_init_invalid_capital_retreat_threshold(self):
        """测试无效的capital_retreat_threshold"""
        with pytest.raises(ValueError, match="capital_retreat_threshold must be > 0"):
            FlowRiskFactorMiner(capital_retreat_threshold=0)
        
        with pytest.raises(ValueError, match="capital_retreat_threshold must be > 0"):
            FlowRiskFactorMiner(capital_retreat_threshold=-100)
    
    def test_init_invalid_large_order_threshold(self):
        """测试无效的large_order_threshold"""
        with pytest.raises(ValueError, match="large_order_threshold must be > 0"):
            FlowRiskFactorMiner(large_order_threshold=0)
    
    def test_init_invalid_detection_window_days(self):
        """测试无效的detection_window_days"""
        with pytest.raises(ValueError, match="detection_window_days must be > 0"):
            FlowRiskFactorMiner(detection_window_days=0)
    
    def test_init_invalid_acceptance_volume_ratio(self):
        """测试无效的acceptance_volume_ratio"""
        with pytest.raises(ValueError, match="acceptance_volume_ratio must be in"):
            FlowRiskFactorMiner(acceptance_volume_ratio=-0.1)
        
        with pytest.raises(ValueError, match="acceptance_volume_ratio must be in"):
            FlowRiskFactorMiner(acceptance_volume_ratio=1.1)
    
    def test_init_invalid_large_order_count_threshold(self):
        """测试无效的large_order_count_threshold"""
        with pytest.raises(ValueError, match="large_order_count_threshold must be > 0"):
            FlowRiskFactorMiner(large_order_count_threshold=0)
    
    def test_init_invalid_large_order_time_window(self):
        """测试无效的large_order_time_window"""
        with pytest.raises(ValueError, match="large_order_time_window must be > 0"):
            FlowRiskFactorMiner(large_order_time_window=0)
    
    def test_init_invalid_flow_reversal_days(self):
        """测试无效的flow_reversal_days"""
        with pytest.raises(ValueError, match="flow_reversal_days must be > 0"):
            FlowRiskFactorMiner(flow_reversal_days=0)


class TestCapitalRetreatDetection:
    """主力资金撤退检测测试"""
    
    def test_detect_capital_retreat_success(self):
        """测试成功检测主力资金撤退"""
        miner = FlowRiskFactorMiner(
            capital_retreat_threshold=500_000_000,
            detection_window_days=5
        )
        
        # 模拟5天持续净流出，总计6亿
        level2_data = {
            'net_outflow_history': [
                100_000_000,  # 1亿
                120_000_000,  # 1.2亿
                130_000_000,  # 1.3亿
                140_000_000,  # 1.4亿
                110_000_000   # 1.1亿
            ]  # 总计6亿
        }
        
        factor = miner.mine_flow_risk('000001.SZ', level2_data)
        
        assert factor is not None
        assert factor.factor_type == 'flow'
        assert factor.symbol == '000001.SZ'
        assert 0 < factor.risk_value <= 1
        assert 0 < factor.confidence <= 1
        assert 'capital_retreat' in [name for name, _ in factor.metadata['signals']]
    
    def test_detect_capital_retreat_below_threshold(self):
        """测试净流出未超过阈值"""
        miner = FlowRiskFactorMiner(
            capital_retreat_threshold=500_000_000,
            detection_window_days=5
        )
        
        # 模拟5天持续净流出，但总计只有3亿（低于5亿阈值）
        level2_data = {
            'net_outflow_history': [
                50_000_000,
                60_000_000,
                70_000_000,
                60_000_000,
                60_000_000
            ]  # 总计3亿
        }
        
        factor = miner.mine_flow_risk('000001.SZ', level2_data)
        
        # 应该没有检测到风险
        assert factor is None
    
    def test_detect_capital_retreat_not_continuous(self):
        """测试净流出不连续"""
        miner = FlowRiskFactorMiner(
            capital_retreat_threshold=500_000_000,
            detection_window_days=5
        )
        
        # 模拟有净流入的情况
        level2_data = {
            'net_outflow_history': [
                100_000_000,
                120_000_000,
                -50_000_000,  # 净流入（负数）
                140_000_000,
                110_000_000
            ]
        }
        
        factor = miner.mine_flow_risk('000001.SZ', level2_data)
        
        # 应该没有检测到资金撤退
        assert factor is None
    
    def test_detect_capital_retreat_insufficient_data(self):
        """测试数据不足"""
        miner = FlowRiskFactorMiner(
            capital_retreat_threshold=500_000_000,
            detection_window_days=5
        )
        
        # 只有3天数据
        level2_data = {
            'net_outflow_history': [
                100_000_000,
                120_000_000,
                130_000_000
            ]
        }
        
        factor = miner.mine_flow_risk('000001.SZ', level2_data)
        
        assert factor is None


class TestAcceptanceCollapseDetection:
    """承接崩塌检测测试"""
    
    def test_detect_acceptance_collapse_success(self):
        """测试成功检测承接崩塌"""
        miner = FlowRiskFactorMiner(acceptance_volume_ratio=0.3)
        
        # 当前成交量远低于20日均量的30%
        level2_data = {
            'volume_history': [1000, 1200, 1100, 1300, 500],  # 最新500
            'avg_volume_20d': 10000  # 20日均量10000
        }
        # 阈值 = 10000 * 0.3 = 3000
        # 当前成交量 500 < 3000，应该检测到
        
        factor = miner.mine_flow_risk('000001.SZ', level2_data)
        
        assert factor is not None
        assert 'acceptance_collapse' in [name for name, _ in factor.metadata['signals']]
    
    def test_detect_acceptance_collapse_above_threshold(self):
        """测试成交量高于阈值"""
        miner = FlowRiskFactorMiner(acceptance_volume_ratio=0.3)
        
        level2_data = {
            'volume_history': [1000, 1200, 1100, 1300, 4000],  # 最新4000
            'avg_volume_20d': 10000  # 阈值 = 3000
        }
        
        factor = miner.mine_flow_risk('000001.SZ', level2_data)
        
        # 4000 > 3000，不应该检测到承接崩塌
        assert factor is None
    
    def test_detect_acceptance_collapse_missing_data(self):
        """测试缺少数据"""
        miner = FlowRiskFactorMiner()
        
        level2_data = {
            'volume_history': [],
            'avg_volume_20d': 0
        }
        
        factor = miner.mine_flow_risk('000001.SZ', level2_data)
        
        assert factor is None


class TestLargeOrderDumpDetection:
    """大单砸盘检测测试"""
    
    def test_detect_large_order_dump_success(self):
        """测试成功检测大单砸盘"""
        miner = FlowRiskFactorMiner(
            large_order_threshold=1_000_000,
            large_order_count_threshold=3,
            large_order_time_window=300
        )
        
        current_time = datetime.now()
        
        # 5分钟内有4笔大单
        level2_data = {
            'large_orders': [
                {'amount': 1_500_000, 'timestamp': current_time - timedelta(seconds=60)},
                {'amount': 2_000_000, 'timestamp': current_time - timedelta(seconds=120)},
                {'amount': 1_800_000, 'timestamp': current_time - timedelta(seconds=180)},
                {'amount': 1_200_000, 'timestamp': current_time - timedelta(seconds=240)}
            ]
        }
        
        factor = miner.mine_flow_risk('000001.SZ', level2_data)
        
        assert factor is not None
        assert 'large_order_dump' in [name for name, _ in factor.metadata['signals']]
    
    def test_detect_large_order_dump_below_count_threshold(self):
        """测试大单数量不足"""
        miner = FlowRiskFactorMiner(
            large_order_threshold=1_000_000,
            large_order_count_threshold=3
        )
        
        current_time = datetime.now()
        
        # 只有2笔大单
        level2_data = {
            'large_orders': [
                {'amount': 1_500_000, 'timestamp': current_time - timedelta(seconds=60)},
                {'amount': 2_000_000, 'timestamp': current_time - timedelta(seconds=120)}
            ]
        }
        
        factor = miner.mine_flow_risk('000001.SZ', level2_data)
        
        assert factor is None
    
    def test_detect_large_order_dump_outside_time_window(self):
        """测试大单在时间窗口外"""
        miner = FlowRiskFactorMiner(
            large_order_threshold=1_000_000,
            large_order_count_threshold=3,
            large_order_time_window=300  # 5分钟
        )
        
        current_time = datetime.now()
        
        # 大单都在10分钟前
        level2_data = {
            'large_orders': [
                {'amount': 1_500_000, 'timestamp': current_time - timedelta(seconds=600)},
                {'amount': 2_000_000, 'timestamp': current_time - timedelta(seconds=660)},
                {'amount': 1_800_000, 'timestamp': current_time - timedelta(seconds=720)}
            ]
        }
        
        factor = miner.mine_flow_risk('000001.SZ', level2_data)
        
        assert factor is None
    
    def test_detect_large_order_dump_below_amount_threshold(self):
        """测试订单金额低于阈值"""
        miner = FlowRiskFactorMiner(
            large_order_threshold=1_000_000,
            large_order_count_threshold=3
        )
        
        current_time = datetime.now()
        
        # 订单金额都低于100万
        level2_data = {
            'large_orders': [
                {'amount': 500_000, 'timestamp': current_time - timedelta(seconds=60)},
                {'amount': 600_000, 'timestamp': current_time - timedelta(seconds=120)},
                {'amount': 700_000, 'timestamp': current_time - timedelta(seconds=180)}
            ]
        }
        
        factor = miner.mine_flow_risk('000001.SZ', level2_data)
        
        assert factor is None


class TestFlowReversalDetection:
    """资金流向逆转检测测试"""
    
    def test_detect_flow_reversal_success(self):
        """测试成功检测资金流向逆转"""
        miner = FlowRiskFactorMiner(flow_reversal_days=3)
        
        # 前3天净流入（正数），后3天净流出（负数）
        level2_data = {
            'flow_direction_history': [
                100, 120, 110,  # 前3天：平均110（流入）
                -80, -90, -100  # 后3天：平均-90（流出）
            ]
        }
        
        factor = miner.mine_flow_risk('000001.SZ', level2_data)
        
        assert factor is not None
        assert 'flow_reversal' in [name for name, _ in factor.metadata['signals']]
    
    def test_detect_flow_reversal_no_reversal(self):
        """测试没有逆转"""
        miner = FlowRiskFactorMiner(flow_reversal_days=3)
        
        # 一直是净流入
        level2_data = {
            'flow_direction_history': [
                100, 120, 110,
                90, 95, 105
            ]
        }
        
        factor = miner.mine_flow_risk('000001.SZ', level2_data)
        
        assert factor is None
    
    def test_detect_flow_reversal_insufficient_data(self):
        """测试数据不足"""
        miner = FlowRiskFactorMiner(flow_reversal_days=3)
        
        # 只有4天数据（需要6天）
        level2_data = {
            'flow_direction_history': [100, 120, -80, -90]
        }
        
        factor = miner.mine_flow_risk('000001.SZ', level2_data)
        
        assert factor is None


class TestMineFlowRisk:
    """综合风险挖掘测试"""
    
    def test_mine_flow_risk_invalid_symbol(self):
        """测试无效的symbol"""
        miner = FlowRiskFactorMiner()
        
        with pytest.raises(ValueError, match="symbol must be a non-empty string"):
            miner.mine_flow_risk('', {})
        
        with pytest.raises(ValueError, match="symbol must be a non-empty string"):
            miner.mine_flow_risk(None, {})
    
    def test_mine_flow_risk_invalid_level2_data(self):
        """测试无效的level2_data"""
        miner = FlowRiskFactorMiner()
        
        with pytest.raises(ValueError, match="level2_data must be a dict"):
            miner.mine_flow_risk('000001.SZ', "not a dict")
    
    def test_mine_flow_risk_no_risk_detected(self):
        """测试未检测到任何风险"""
        miner = FlowRiskFactorMiner()
        
        # 正常的市场数据
        level2_data = {
            'net_outflow_history': [10, 20, -30, 15, -25],  # 有流入有流出
            'volume_history': [5000, 5200, 5100, 5300, 5000],
            'avg_volume_20d': 5000,
            'large_orders': [],
            'flow_direction_history': [50, 60, 55, 58, 62, 65]  # 持续流入
        }
        
        factor = miner.mine_flow_risk('000001.SZ', level2_data)
        
        assert factor is None
    
    def test_mine_flow_risk_multiple_risks(self):
        """测试检测到多种风险"""
        miner = FlowRiskFactorMiner(
            capital_retreat_threshold=500_000_000,
            detection_window_days=5,
            acceptance_volume_ratio=0.3,
            large_order_threshold=1_000_000,
            large_order_count_threshold=3,
            flow_reversal_days=3
        )
        
        current_time = datetime.now()
        
        # 同时满足多种风险条件
        level2_data = {
            # 主力资金撤退
            'net_outflow_history': [
                100_000_000, 120_000_000, 130_000_000, 140_000_000, 110_000_000
            ],
            # 承接崩塌
            'volume_history': [1000, 1200, 1100, 1300, 500],
            'avg_volume_20d': 10000,
            # 大单砸盘
            'large_orders': [
                {'amount': 1_500_000, 'timestamp': current_time - timedelta(seconds=60)},
                {'amount': 2_000_000, 'timestamp': current_time - timedelta(seconds=120)},
                {'amount': 1_800_000, 'timestamp': current_time - timedelta(seconds=180)}
            ],
            # 资金流向逆转
            'flow_direction_history': [100, 120, 110, -80, -90, -100]
        }
        
        factor = miner.mine_flow_risk('000001.SZ', level2_data)
        
        assert factor is not None
        assert factor.factor_type == 'flow'
        assert factor.symbol == '000001.SZ'
        assert 0 < factor.risk_value <= 1
        assert 0 < factor.confidence <= 1
        
        # 应该检测到多种风险
        signal_names = [name for name, _ in factor.metadata['signals']]
        assert len(signal_names) >= 2
        assert factor.metadata['detection_count'] >= 2
    
    def test_mine_flow_risk_factor_type_correctness(self):
        """测试因子类型正确性"""
        miner = FlowRiskFactorMiner()
        
        # 创建会触发风险的数据
        level2_data = {
            'net_outflow_history': [
                100_000_000, 120_000_000, 130_000_000, 140_000_000, 110_000_000
            ]
        }
        
        factor = miner.mine_flow_risk('000001.SZ', level2_data)
        
        # 验证因子类型
        assert factor is not None
        assert factor.factor_type == 'flow'
    
    def test_mine_flow_risk_confidence_increases_with_signals(self):
        """测试置信度随检测到的风险数量增加"""
        miner = FlowRiskFactorMiner(
            capital_retreat_threshold=500_000_000,
            detection_window_days=5
        )
        
        # 只有一种风险
        level2_data_single = {
            'net_outflow_history': [
                100_000_000, 120_000_000, 130_000_000, 140_000_000, 110_000_000
            ]
        }
        
        factor_single = miner.mine_flow_risk('000001.SZ', level2_data_single)
        
        # 多种风险
        current_time = datetime.now()
        level2_data_multiple = {
            'net_outflow_history': [
                100_000_000, 120_000_000, 130_000_000, 140_000_000, 110_000_000
            ],
            'volume_history': [1000, 1200, 1100, 1300, 500],
            'avg_volume_20d': 10000,
            'large_orders': [
                {'amount': 1_500_000, 'timestamp': current_time - timedelta(seconds=60)},
                {'amount': 2_000_000, 'timestamp': current_time - timedelta(seconds=120)},
                {'amount': 1_800_000, 'timestamp': current_time - timedelta(seconds=180)}
            ]
        }
        
        factor_multiple = miner.mine_flow_risk('000001.SZ', level2_data_multiple)
        
        # 多种风险的置信度应该更高
        assert factor_single is not None
        assert factor_multiple is not None
        assert factor_multiple.confidence > factor_single.confidence
