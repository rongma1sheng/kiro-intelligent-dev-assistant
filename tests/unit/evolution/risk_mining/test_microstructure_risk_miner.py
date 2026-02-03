"""微结构风险挖掘器单元测试

白皮书依据: 第四章 4.1.1 专业风险因子挖掘系统 - 微结构风险

测试覆盖:
- MicrostructureRiskFactorMiner初始化
- 流动性枯竭检测
- 订单簿失衡检测
- 买卖价差扩大检测
- 深度不足检测
- 综合风险挖掘
"""

import pytest
from src.evolution.risk_mining.microstructure_risk_miner import MicrostructureRiskFactorMiner


class TestMicrostructureRiskFactorMinerInit:
    """MicrostructureRiskFactorMiner初始化测试"""
    
    def test_init_with_defaults(self):
        """测试使用默认参数初始化"""
        miner = MicrostructureRiskFactorMiner()
        
        assert miner.liquidity_threshold == 0.5
        assert miner.imbalance_threshold == 3.0
        assert miner.spread_multiplier == 2.0
        assert miner.depth_shortage_ratio == 0.3
    
    def test_init_with_custom_params(self):
        """测试使用自定义参数初始化"""
        miner = MicrostructureRiskFactorMiner(
            liquidity_threshold=0.6,
            imbalance_threshold=4.0,
            spread_multiplier=3.0,
            depth_shortage_ratio=0.4
        )
        
        assert miner.liquidity_threshold == 0.6
        assert miner.imbalance_threshold == 4.0
        assert miner.spread_multiplier == 3.0
        assert miner.depth_shortage_ratio == 0.4
    
    def test_init_invalid_liquidity_threshold(self):
        """测试无效的liquidity_threshold"""
        with pytest.raises(ValueError, match="liquidity_threshold must be in"):
            MicrostructureRiskFactorMiner(liquidity_threshold=-0.1)
        
        with pytest.raises(ValueError, match="liquidity_threshold must be in"):
            MicrostructureRiskFactorMiner(liquidity_threshold=1.1)
    
    def test_init_invalid_imbalance_threshold(self):
        """测试无效的imbalance_threshold"""
        with pytest.raises(ValueError, match="imbalance_threshold must be > 1"):
            MicrostructureRiskFactorMiner(imbalance_threshold=1.0)
        
        with pytest.raises(ValueError, match="imbalance_threshold must be > 1"):
            MicrostructureRiskFactorMiner(imbalance_threshold=0.5)
    
    def test_init_invalid_spread_multiplier(self):
        """测试无效的spread_multiplier"""
        with pytest.raises(ValueError, match="spread_multiplier must be > 1"):
            MicrostructureRiskFactorMiner(spread_multiplier=1.0)
        
        with pytest.raises(ValueError, match="spread_multiplier must be > 1"):
            MicrostructureRiskFactorMiner(spread_multiplier=0.5)
    
    def test_init_invalid_depth_shortage_ratio(self):
        """测试无效的depth_shortage_ratio"""
        with pytest.raises(ValueError, match="depth_shortage_ratio must be in"):
            MicrostructureRiskFactorMiner(depth_shortage_ratio=-0.1)
        
        with pytest.raises(ValueError, match="depth_shortage_ratio must be in"):
            MicrostructureRiskFactorMiner(depth_shortage_ratio=1.1)


class TestLiquidityDroughtDetection:
    """流动性枯竭检测测试"""
    
    def test_detect_liquidity_drought_success(self):
        """测试成功检测流动性枯竭"""
        miner = MicrostructureRiskFactorMiner(liquidity_threshold=0.5)
        
        # 当前买盘量远低于20日均量的50%
        orderbook = {
            'bid_volumes': [100, 80, 70, 60, 50],  # 总计360
            'avg_bid_volume_20d': 2000  # 阈值 = 2000 * 0.5 = 1000
        }
        # 360 < 1000，应该检测到
        
        factor = miner.mine_microstructure_risk('000001.SZ', orderbook)
        
        assert factor is not None
        assert factor.factor_type == 'microstructure'
        assert 'liquidity_drought' in [name for name, _ in factor.metadata['signals']]
    
    def test_detect_liquidity_drought_above_threshold(self):
        """测试买盘量高于阈值"""
        miner = MicrostructureRiskFactorMiner(liquidity_threshold=0.5)
        
        orderbook = {
            'bid_volumes': [500, 400, 300, 200, 100],  # 总计1500
            'avg_bid_volume_20d': 2000  # 阈值 = 1000
        }
        # 1500 > 1000，不应该检测到
        
        factor = miner.mine_microstructure_risk('000001.SZ', orderbook)
        
        assert factor is None
    
    def test_detect_liquidity_drought_missing_data(self):
        """测试缺少数据"""
        miner = MicrostructureRiskFactorMiner()
        
        orderbook = {
            'bid_volumes': [],
            'avg_bid_volume_20d': 0
        }
        
        factor = miner.mine_microstructure_risk('000001.SZ', orderbook)
        
        assert factor is None


class TestOrderbookImbalanceDetection:
    """订单簿失衡检测测试"""
    
    def test_detect_orderbook_imbalance_success(self):
        """测试成功检测订单簿失衡"""
        miner = MicrostructureRiskFactorMiner(imbalance_threshold=3.0)
        
        # 卖盘/买盘 = 4000/1000 = 4 > 3
        orderbook = {
            'bid_volumes': [200, 200, 200, 200, 200],  # 总计1000
            'ask_volumes': [800, 800, 800, 800, 800]   # 总计4000
        }
        
        factor = miner.mine_microstructure_risk('000001.SZ', orderbook)
        
        assert factor is not None
        assert 'orderbook_imbalance' in [name for name, _ in factor.metadata['signals']]
    
    def test_detect_orderbook_imbalance_below_threshold(self):
        """测试失衡比例低于阈值"""
        miner = MicrostructureRiskFactorMiner(imbalance_threshold=3.0)
        
        # 卖盘/买盘 = 2000/1000 = 2 < 3
        orderbook = {
            'bid_volumes': [200, 200, 200, 200, 200],  # 总计1000
            'ask_volumes': [400, 400, 400, 400, 400]   # 总计2000
        }
        
        factor = miner.mine_microstructure_risk('000001.SZ', orderbook)
        
        assert factor is None
    
    def test_detect_orderbook_imbalance_zero_bid(self):
        """测试买盘为零"""
        miner = MicrostructureRiskFactorMiner()
        
        orderbook = {
            'bid_volumes': [0, 0, 0, 0, 0],
            'ask_volumes': [400, 400, 400, 400, 400]
        }
        
        factor = miner.mine_microstructure_risk('000001.SZ', orderbook)
        
        # 虽然订单簿失衡检测返回None，但深度不足会触发
        # 所以factor不为None，但不应该包含orderbook_imbalance信号
        if factor is not None:
            signal_names = [name for name, _ in factor.metadata['signals']]
            assert 'orderbook_imbalance' not in signal_names


class TestSpreadWideningDetection:
    """买卖价差扩大检测测试"""
    
    def test_detect_spread_widening_success(self):
        """测试成功检测买卖价差扩大"""
        miner = MicrostructureRiskFactorMiner(spread_multiplier=2.0)
        
        # 当前价差 = 10.5 - 10.0 = 0.5
        # 阈值 = 0.1 * 2 = 0.2
        # 0.5 > 0.2，应该检测到
        orderbook = {
            'bid_prices': [10.0, 9.99, 9.98, 9.97, 9.96],
            'ask_prices': [10.5, 10.51, 10.52, 10.53, 10.54],
            'avg_spread_20d': 0.1
        }
        
        factor = miner.mine_microstructure_risk('000001.SZ', orderbook)
        
        assert factor is not None
        assert 'spread_widening' in [name for name, _ in factor.metadata['signals']]
    
    def test_detect_spread_widening_below_threshold(self):
        """测试价差低于阈值"""
        miner = MicrostructureRiskFactorMiner(spread_multiplier=2.0)
        
        # 当前价差 = 10.05 - 10.0 = 0.05
        # 阈值 = 0.1 * 2 = 0.2
        # 0.05 < 0.2，不应该检测到
        orderbook = {
            'bid_prices': [10.0, 9.99, 9.98, 9.97, 9.96],
            'ask_prices': [10.05, 10.06, 10.07, 10.08, 10.09],
            'avg_spread_20d': 0.1
        }
        
        factor = miner.mine_microstructure_risk('000001.SZ', orderbook)
        
        assert factor is None
    
    def test_detect_spread_widening_missing_data(self):
        """测试缺少数据"""
        miner = MicrostructureRiskFactorMiner()
        
        orderbook = {
            'bid_prices': [],
            'ask_prices': [],
            'avg_spread_20d': 0
        }
        
        factor = miner.mine_microstructure_risk('000001.SZ', orderbook)
        
        assert factor is None


class TestDepthShortageDetection:
    """深度不足检测测试"""
    
    def test_detect_depth_shortage_success(self):
        """测试成功检测深度不足"""
        miner = MicrostructureRiskFactorMiner(depth_shortage_ratio=0.3)
        
        # 下方深度（买盘）= 500
        # 上方深度（卖盘）= 5000
        # 阈值 = 5000 * 0.3 = 1500
        # 500 < 1500，应该检测到
        orderbook = {
            'bid_volumes': [100, 100, 100, 100, 100],  # 总计500
            'ask_volumes': [1000, 1000, 1000, 1000, 1000]  # 总计5000
        }
        
        factor = miner.mine_microstructure_risk('000001.SZ', orderbook)
        
        assert factor is not None
        assert 'depth_shortage' in [name for name, _ in factor.metadata['signals']]
    
    def test_detect_depth_shortage_above_threshold(self):
        """测试深度高于阈值"""
        miner = MicrostructureRiskFactorMiner(depth_shortage_ratio=0.3)
        
        # 下方深度 = 2000
        # 上方深度 = 5000
        # 阈值 = 1500
        # 2000 > 1500，不应该检测到
        orderbook = {
            'bid_volumes': [400, 400, 400, 400, 400],  # 总计2000
            'ask_volumes': [1000, 1000, 1000, 1000, 1000]  # 总计5000
        }
        
        factor = miner.mine_microstructure_risk('000001.SZ', orderbook)
        
        assert factor is None
    
    def test_detect_depth_shortage_zero_upper_depth(self):
        """测试上方深度为零"""
        miner = MicrostructureRiskFactorMiner()
        
        orderbook = {
            'bid_volumes': [100, 100, 100, 100, 100],
            'ask_volumes': [0, 0, 0, 0, 0]
        }
        
        factor = miner.mine_microstructure_risk('000001.SZ', orderbook)
        
        assert factor is None


class TestMineMicrostructureRisk:
    """综合风险挖掘测试"""
    
    def test_mine_microstructure_risk_invalid_symbol(self):
        """测试无效的symbol"""
        miner = MicrostructureRiskFactorMiner()
        
        with pytest.raises(ValueError, match="symbol must be a non-empty string"):
            miner.mine_microstructure_risk('', {})
        
        with pytest.raises(ValueError, match="symbol must be a non-empty string"):
            miner.mine_microstructure_risk(None, {})
    
    def test_mine_microstructure_risk_invalid_orderbook(self):
        """测试无效的orderbook"""
        miner = MicrostructureRiskFactorMiner()
        
        with pytest.raises(ValueError, match="orderbook must be a dict"):
            miner.mine_microstructure_risk('000001.SZ', "not a dict")
    
    def test_mine_microstructure_risk_no_risk_detected(self):
        """测试未检测到任何风险"""
        miner = MicrostructureRiskFactorMiner()
        
        # 正常的订单簿数据
        orderbook = {
            'bid_volumes': [500, 400, 300, 200, 100],  # 总计1500
            'ask_volumes': [500, 400, 300, 200, 100],  # 总计1500，平衡
            'bid_prices': [10.0, 9.99, 9.98, 9.97, 9.96],
            'ask_prices': [10.05, 10.06, 10.07, 10.08, 10.09],  # 正常价差
            'avg_bid_volume_20d': 1000,  # 1500 > 1000 * 0.5
            'avg_spread_20d': 0.1  # 0.05 < 0.1 * 2
        }
        
        factor = miner.mine_microstructure_risk('000001.SZ', orderbook)
        
        assert factor is None
    
    def test_mine_microstructure_risk_multiple_risks(self):
        """测试检测到多种风险"""
        miner = MicrostructureRiskFactorMiner(
            liquidity_threshold=0.5,
            imbalance_threshold=3.0,
            spread_multiplier=2.0,
            depth_shortage_ratio=0.3
        )
        
        # 同时满足多种风险条件
        orderbook = {
            # 流动性枯竭：360 < 2000 * 0.5 = 1000
            'bid_volumes': [100, 80, 70, 60, 50],
            'avg_bid_volume_20d': 2000,
            # 订单簿失衡：4000/360 > 3
            'ask_volumes': [800, 800, 800, 800, 800],
            # 买卖价差扩大：0.5 > 0.1 * 2 = 0.2
            'bid_prices': [10.0, 9.99, 9.98, 9.97, 9.96],
            'ask_prices': [10.5, 10.51, 10.52, 10.53, 10.54],
            'avg_spread_20d': 0.1
            # 深度不足：360 < 4000 * 0.3 = 1200
        }
        
        factor = miner.mine_microstructure_risk('000001.SZ', orderbook)
        
        assert factor is not None
        assert factor.factor_type == 'microstructure'
        assert factor.symbol == '000001.SZ'
        assert 0 < factor.risk_value <= 1
        assert 0 < factor.confidence <= 1
        
        # 应该检测到多种风险
        signal_names = [name for name, _ in factor.metadata['signals']]
        assert len(signal_names) >= 2
        assert factor.metadata['detection_count'] >= 2
    
    def test_mine_microstructure_risk_factor_type_correctness(self):
        """测试因子类型正确性"""
        miner = MicrostructureRiskFactorMiner()
        
        # 创建会触发风险的数据
        orderbook = {
            'bid_volumes': [100, 80, 70, 60, 50],
            'avg_bid_volume_20d': 2000
        }
        
        factor = miner.mine_microstructure_risk('000001.SZ', orderbook)
        
        # 验证因子类型
        assert factor is not None
        assert factor.factor_type == 'microstructure'
    
    def test_mine_microstructure_risk_confidence_increases_with_signals(self):
        """测试置信度随检测到的风险数量增加"""
        miner = MicrostructureRiskFactorMiner()
        
        # 只有一种风险
        orderbook_single = {
            'bid_volumes': [100, 80, 70, 60, 50],
            'avg_bid_volume_20d': 2000
        }
        
        factor_single = miner.mine_microstructure_risk('000001.SZ', orderbook_single)
        
        # 多种风险
        orderbook_multiple = {
            'bid_volumes': [100, 80, 70, 60, 50],
            'avg_bid_volume_20d': 2000,
            'ask_volumes': [800, 800, 800, 800, 800],
            'bid_prices': [10.0, 9.99, 9.98, 9.97, 9.96],
            'ask_prices': [10.5, 10.51, 10.52, 10.53, 10.54],
            'avg_spread_20d': 0.1
        }
        
        factor_multiple = miner.mine_microstructure_risk('000001.SZ', orderbook_multiple)
        
        # 多种风险的置信度应该更高
        assert factor_single is not None
        assert factor_multiple is not None
        assert factor_multiple.confidence > factor_single.confidence
