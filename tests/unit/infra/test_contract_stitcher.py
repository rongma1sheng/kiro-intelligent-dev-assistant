"""
期货合约拼接器单元测试

白皮书依据: 第三章 3.3 衍生品管道 - Contract Stitcher

测试覆盖:
1. 初始化测试
2. 主力合约识别测试
3. 切换点检测测试
4. 价差平移算法测试
5. 多品种支持测试
6. 性能测试
"""

import pytest
from datetime import datetime, timedelta
from src.infra.contract_stitcher import (
    ContractStitcher,
    ContractData,
    StitchedContract,
    SwitchPoint
)


class TestContractStitcherInitialization:
    """测试合约拼接器初始化"""
    
    def test_default_initialization(self):
        """测试默认初始化"""
        stitcher = ContractStitcher()
        
        assert stitcher.volume_weight == 0.6
        assert stitcher.oi_weight == 0.4
        assert stitcher.switch_threshold == 1.2
        assert stitcher.switch_days == 3
        assert len(stitcher.contracts_buffer) == 0
        assert len(stitcher.switch_points) == 0
    
    def test_custom_initialization(self):
        """测试自定义初始化"""
        stitcher = ContractStitcher(
            volume_weight=0.7,
            oi_weight=0.3,
            switch_threshold=1.5,
            switch_days=5
        )
        
        assert stitcher.volume_weight == 0.7
        assert stitcher.oi_weight == 0.3
        assert stitcher.switch_threshold == 1.5
        assert stitcher.switch_days == 5
    
    def test_invalid_volume_weight(self):
        """测试无效成交量权重"""
        with pytest.raises(ValueError, match="成交量权重必须在"):
            ContractStitcher(volume_weight=1.5, oi_weight=0.4)
    
    def test_invalid_weight_sum(self):
        """测试权重之和不为1"""
        with pytest.raises(ValueError, match="权重之和必须为1"):
            ContractStitcher(volume_weight=0.5, oi_weight=0.3)
    
    def test_invalid_switch_threshold(self):
        """测试无效切换阈值"""
        with pytest.raises(ValueError, match="切换阈值必须 > 1.0"):
            ContractStitcher(switch_threshold=0.9)
    
    def test_invalid_switch_days(self):
        """测试无效连续天数"""
        with pytest.raises(ValueError, match="连续天数必须 >= 1"):
            ContractStitcher(switch_days=0)


class TestContractDataManagement:
    """测试合约数据管理"""
    
    def test_add_contract_data(self):
        """测试添加合约数据"""
        stitcher = ContractStitcher()
        
        data = [
            ContractData(
                symbol="IF2401",
                date=datetime(2024, 1, 1),
                open=4000.0,
                high=4050.0,
                low=3950.0,
                close=4020.0,
                volume=10000.0,
                open_interest=50000.0
            )
        ]
        
        stitcher.add_contract_data("IF2401", data)
        
        assert "IF2401" in stitcher.contracts_buffer
        assert len(stitcher.contracts_buffer["IF2401"]) == 1
        assert stitcher.stats['total_contracts'] == 1
    
    def test_add_empty_data(self):
        """测试添加空数据"""
        stitcher = ContractStitcher()
        
        with pytest.raises(ValueError, match="合约数据不能为空"):
            stitcher.add_contract_data("IF2401", [])
    
    def test_data_sorting(self):
        """测试数据自动排序"""
        stitcher = ContractStitcher()
        
        # 添加乱序数据
        data = [
            ContractData(
                symbol="IF2401",
                date=datetime(2024, 1, 3),
                open=4000.0, high=4050.0, low=3950.0, close=4020.0,
                volume=10000.0, open_interest=50000.0
            ),
            ContractData(
                symbol="IF2401",
                date=datetime(2024, 1, 1),
                open=4000.0, high=4050.0, low=3950.0, close=4020.0,
                volume=10000.0, open_interest=50000.0
            ),
            ContractData(
                symbol="IF2401",
                date=datetime(2024, 1, 2),
                open=4000.0, high=4050.0, low=3950.0, close=4020.0,
                volume=10000.0, open_interest=50000.0
            )
        ]
        
        stitcher.add_contract_data("IF2401", data)
        
        # 验证排序
        sorted_data = stitcher.contracts_buffer["IF2401"]
        assert sorted_data[0].date == datetime(2024, 1, 1)
        assert sorted_data[1].date == datetime(2024, 1, 2)
        assert sorted_data[2].date == datetime(2024, 1, 3)


class TestMainContractIdentification:
    """测试主力合约识别"""
    
    def test_identify_single_contract(self):
        """测试单个合约识别"""
        stitcher = ContractStitcher()
        
        data = [
            ContractData(
                symbol="IF2401",
                date=datetime(2024, 1, 1),
                open=4000.0, high=4050.0, low=3950.0, close=4020.0,
                volume=10000.0, open_interest=50000.0
            )
        ]
        
        stitcher.add_contract_data("IF2401", data)
        
        main = stitcher.identify_main_contract(
            datetime(2024, 1, 1),
            ["IF2401"]
        )
        
        assert main == "IF2401"
    
    def test_identify_main_by_volume(self):
        """测试基于成交量识别主力"""
        stitcher = ContractStitcher(volume_weight=1.0, oi_weight=0.0)
        
        # IF2401成交量更大
        data1 = [
            ContractData(
                symbol="IF2401",
                date=datetime(2024, 1, 1),
                open=4000.0, high=4050.0, low=3950.0, close=4020.0,
                volume=20000.0,  # 更大
                open_interest=40000.0
            )
        ]
        
        # IF2402成交量较小
        data2 = [
            ContractData(
                symbol="IF2402",
                date=datetime(2024, 1, 1),
                open=4010.0, high=4060.0, low=3960.0, close=4030.0,
                volume=10000.0,  # 较小
                open_interest=60000.0  # 持仓量更大但权重为0
            )
        ]
        
        stitcher.add_contract_data("IF2401", data1)
        stitcher.add_contract_data("IF2402", data2)
        
        main = stitcher.identify_main_contract(
            datetime(2024, 1, 1),
            ["IF2401", "IF2402"]
        )
        
        assert main == "IF2401"
    
    def test_identify_main_by_open_interest(self):
        """测试基于持仓量识别主力"""
        stitcher = ContractStitcher(volume_weight=0.0, oi_weight=1.0)
        
        data1 = [
            ContractData(
                symbol="IF2401",
                date=datetime(2024, 1, 1),
                open=4000.0, high=4050.0, low=3950.0, close=4020.0,
                volume=20000.0,  # 成交量更大但权重为0
                open_interest=40000.0
            )
        ]
        
        data2 = [
            ContractData(
                symbol="IF2402",
                date=datetime(2024, 1, 1),
                open=4010.0, high=4060.0, low=3960.0, close=4030.0,
                volume=10000.0,
                open_interest=60000.0  # 持仓量更大
            )
        ]
        
        stitcher.add_contract_data("IF2401", data1)
        stitcher.add_contract_data("IF2402", data2)
        
        main = stitcher.identify_main_contract(
            datetime(2024, 1, 1),
            ["IF2401", "IF2402"]
        )
        
        assert main == "IF2402"
    
    def test_identify_main_weighted(self):
        """测试加权识别主力"""
        stitcher = ContractStitcher(volume_weight=0.6, oi_weight=0.4)
        
        data1 = [
            ContractData(
                symbol="IF2401",
                date=datetime(2024, 1, 1),
                open=4000.0, high=4050.0, low=3950.0, close=4020.0,
                volume=15000.0,
                open_interest=45000.0
            )
        ]
        
        data2 = [
            ContractData(
                symbol="IF2402",
                date=datetime(2024, 1, 1),
                open=4010.0, high=4060.0, low=3960.0, close=4030.0,
                volume=12000.0,
                open_interest=50000.0
            )
        ]
        
        stitcher.add_contract_data("IF2401", data1)
        stitcher.add_contract_data("IF2402", data2)
        
        main = stitcher.identify_main_contract(
            datetime(2024, 1, 1),
            ["IF2401", "IF2402"]
        )
        
        # IF2401评分 = 0.6*15000 + 0.4*45000 = 9000 + 18000 = 27000
        # IF2402评分 = 0.6*12000 + 0.4*50000 = 7200 + 20000 = 27200
        assert main == "IF2402"
    
    def test_identify_no_data(self):
        """测试无数据时识别"""
        stitcher = ContractStitcher()
        
        main = stitcher.identify_main_contract(
            datetime(2024, 1, 1),
            ["IF2401"]
        )
        
        assert main is None
    
    def test_identify_empty_contracts(self):
        """测试空合约列表"""
        stitcher = ContractStitcher()
        
        main = stitcher.identify_main_contract(
            datetime(2024, 1, 1),
            []
        )
        
        assert main is None


class TestSwitchPointDetection:
    """测试切换点检测"""
    
    def test_detect_simple_switch(self):
        """测试简单切换检测"""
        stitcher = ContractStitcher(
            volume_weight=1.0,
            oi_weight=0.0,
            switch_threshold=1.5,
            switch_days=2
        )
        
        # 准备数据：IF2401 → IF2402切换
        dates = [datetime(2024, 1, i) for i in range(1, 6)]
        
        # IF2401: 前2天是主力，后3天成交量下降
        data1 = [
            ContractData(
                symbol="IF2401", date=dates[0],
                open=4000.0, high=4050.0, low=3950.0, close=4020.0,
                volume=20000.0, open_interest=50000.0
            ),
            ContractData(
                symbol="IF2401", date=dates[1],
                open=4020.0, high=4070.0, low=3970.0, close=4040.0,
                volume=18000.0, open_interest=48000.0
            ),
            ContractData(
                symbol="IF2401", date=dates[2],
                open=4040.0, high=4090.0, low=3990.0, close=4060.0,
                volume=10000.0, open_interest=40000.0
            ),
            ContractData(
                symbol="IF2401", date=dates[3],
                open=4060.0, high=4110.0, low=4010.0, close=4080.0,
                volume=8000.0, open_interest=35000.0
            ),
            ContractData(
                symbol="IF2401", date=dates[4],
                open=4080.0, high=4130.0, low=4030.0, close=4100.0,
                volume=6000.0, open_interest=30000.0
            )
        ]
        
        # IF2402: 前2天成交量小，后3天成交量大（成为主力）
        data2 = [
            ContractData(
                symbol="IF2402", date=dates[0],
                open=4010.0, high=4060.0, low=3960.0, close=4030.0,
                volume=5000.0, open_interest=20000.0
            ),
            ContractData(
                symbol="IF2402", date=dates[1],
                open=4030.0, high=4080.0, low=3980.0, close=4050.0,
                volume=8000.0, open_interest=25000.0
            ),
            ContractData(
                symbol="IF2402", date=dates[2],
                open=4050.0, high=4100.0, low=4000.0, close=4070.0,
                volume=18000.0, open_interest=45000.0  # 超过阈值
            ),
            ContractData(
                symbol="IF2402", date=dates[3],
                open=4070.0, high=4120.0, low=4020.0, close=4090.0,
                volume=20000.0, open_interest=50000.0  # 连续超过
            ),
            ContractData(
                symbol="IF2402", date=dates[4],
                open=4090.0, high=4140.0, low=4040.0, close=4110.0,
                volume=22000.0, open_interest=55000.0
            )
        ]
        
        stitcher.add_contract_data("IF2401", data1)
        stitcher.add_contract_data("IF2402", data2)
        
        switch_points = stitcher.detect_switch_points(
            ["IF2401", "IF2402"],
            dates[0],
            dates[4]
        )
        
        # 应该检测到1个切换点
        assert len(switch_points) >= 1
        assert switch_points[0].old_contract == "IF2401"
        assert switch_points[0].new_contract == "IF2402"
    
    def test_no_switch_detected(self):
        """测试无切换情况"""
        stitcher = ContractStitcher()
        
        dates = [datetime(2024, 1, i) for i in range(1, 4)]
        
        # IF2401始终是主力
        data1 = [
            ContractData(
                symbol="IF2401", date=date,
                open=4000.0, high=4050.0, low=3950.0, close=4020.0,
                volume=20000.0, open_interest=50000.0
            )
            for date in dates
        ]
        
        stitcher.add_contract_data("IF2401", data1)
        
        switch_points = stitcher.detect_switch_points(
            ["IF2401"],
            dates[0],
            dates[2]
        )
        
        assert len(switch_points) == 0


class TestContractStitching:
    """测试合约拼接"""
    
    def test_stitch_without_switch(self):
        """测试无切换的拼接"""
        stitcher = ContractStitcher()
        
        dates = [datetime(2024, 1, i) for i in range(1, 4)]
        
        data = [
            ContractData(
                symbol="IF2401", date=dates[0],
                open=4000.0, high=4050.0, low=3950.0, close=4020.0,
                volume=20000.0, open_interest=50000.0
            ),
            ContractData(
                symbol="IF2401", date=dates[1],
                open=4020.0, high=4070.0, low=3970.0, close=4040.0,
                volume=20000.0, open_interest=50000.0
            ),
            ContractData(
                symbol="IF2401", date=dates[2],
                open=4040.0, high=4090.0, low=3990.0, close=4060.0,
                volume=20000.0, open_interest=50000.0
            )
        ]
        
        stitcher.add_contract_data("IF2401", data)
        
        stitched = stitcher.stitch_contracts(
            ["IF2401"],
            dates[0],
            dates[2]
        )
        
        assert len(stitched) == 3
        # 无切换，价格不应调整
        assert stitched[0].close == 4020.0
        assert stitched[1].close == 4040.0
        assert stitched[2].close == 4060.0
        assert all(s.adjustment == 0.0 for s in stitched)
    
    def test_stitch_with_switch(self):
        """测试有切换的拼接"""
        stitcher = ContractStitcher(
            volume_weight=1.0,
            oi_weight=0.0,
            switch_threshold=1.5,
            switch_days=1  # 简化测试，1天即切换
        )
        
        dates = [datetime(2024, 1, i) for i in range(1, 4)]
        
        # IF2401: 第1天是主力
        data1 = [
            ContractData(
                symbol="IF2401", date=dates[0],
                open=4000.0, high=4050.0, low=3950.0, close=4020.0,
                volume=20000.0, open_interest=50000.0
            ),
            ContractData(
                symbol="IF2401", date=dates[1],
                open=4020.0, high=4070.0, low=3970.0, close=4040.0,
                volume=5000.0, open_interest=20000.0  # 成交量大幅下降
            ),
            ContractData(
                symbol="IF2401", date=dates[2],
                open=4040.0, high=4090.0, low=3990.0, close=4060.0,
                volume=3000.0, open_interest=15000.0
            )
        ]
        
        # IF2402: 第2天开始成为主力
        data2 = [
            ContractData(
                symbol="IF2402", date=dates[0],
                open=4010.0, high=4060.0, low=3960.0, close=4030.0,
                volume=5000.0, open_interest=20000.0
            ),
            ContractData(
                symbol="IF2402", date=dates[1],
                open=4050.0, high=4100.0, low=4000.0, close=4070.0,  # 价格跳空
                volume=25000.0, open_interest=60000.0  # 成为主力
            ),
            ContractData(
                symbol="IF2402", date=dates[2],
                open=4070.0, high=4120.0, low=4020.0, close=4090.0,
                volume=25000.0, open_interest=60000.0
            )
        ]
        
        stitcher.add_contract_data("IF2401", data1)
        stitcher.add_contract_data("IF2402", data2)
        
        stitched = stitcher.stitch_contracts(
            ["IF2401", "IF2402"],
            dates[0],
            dates[2]
        )
        
        assert len(stitched) >= 2
        # 应该检测到切换
        assert stitcher.stats['total_switches'] >= 1
    
    def test_stitch_empty_contracts(self):
        """测试空合约列表"""
        stitcher = ContractStitcher()
        
        with pytest.raises(ValueError, match="合约列表不能为空"):
            stitcher.stitch_contracts(
                [],
                datetime(2024, 1, 1),
                datetime(2024, 1, 3)
            )


class TestStatistics:
    """测试统计功能"""
    
    def test_get_stats(self):
        """测试获取统计"""
        stitcher = ContractStitcher()
        
        dates = [datetime(2024, 1, i) for i in range(1, 4)]
        
        data = [
            ContractData(
                symbol="IF2401", date=date,
                open=4000.0, high=4050.0, low=3950.0, close=4020.0,
                volume=20000.0, open_interest=50000.0
            )
            for date in dates
        ]
        
        stitcher.add_contract_data("IF2401", data)
        stitcher.stitch_contracts(["IF2401"], dates[0], dates[2])
        
        stats = stitcher.get_stats()
        
        assert stats['total_contracts'] == 1
        assert stats['total_stitched'] == 3
        assert stats['processing_time_ms'] > 0
    
    def test_reset_stats(self):
        """测试重置统计"""
        stitcher = ContractStitcher()
        
        stitcher.stats['total_contracts'] = 10
        stitcher.stats['total_switches'] = 5
        
        stitcher.reset_stats()
        
        assert stitcher.stats['total_contracts'] == 0
        assert stitcher.stats['total_switches'] == 0
    
    def test_clear_buffer(self):
        """测试清空缓冲区"""
        stitcher = ContractStitcher()
        
        data = [
            ContractData(
                symbol="IF2401",
                date=datetime(2024, 1, 1),
                open=4000.0, high=4050.0, low=3950.0, close=4020.0,
                volume=20000.0, open_interest=50000.0
            )
        ]
        
        stitcher.add_contract_data("IF2401", data)
        assert len(stitcher.contracts_buffer) == 1
        
        stitcher.clear_buffer()
        assert len(stitcher.contracts_buffer) == 0
        assert len(stitcher.switch_points) == 0


class TestPerformance:
    """测试性能"""
    
    def test_stitching_performance(self):
        """测试拼接性能"""
        stitcher = ContractStitcher()
        
        # 生成100天数据
        dates = [datetime(2024, 1, 1) + timedelta(days=i) for i in range(100)]
        
        data = [
            ContractData(
                symbol="IF2401", date=date,
                open=4000.0, high=4050.0, low=3950.0, close=4020.0,
                volume=20000.0, open_interest=50000.0
            )
            for date in dates
        ]
        
        stitcher.add_contract_data("IF2401", data)
        
        stitched = stitcher.stitch_contracts(
            ["IF2401"],
            dates[0],
            dates[-1]
        )
        
        stats = stitcher.get_stats()
        
        # 性能目标: > 1000条/秒 = < 1ms/条
        assert stats['avg_time_per_record_ms'] < 1.0
        assert len(stitched) == 100



class TestEdgeCases:
    """测试边界情况"""
    
    def test_invalid_oi_weight(self):
        """测试无效持仓量权重"""
        with pytest.raises(ValueError, match="持仓量权重必须在"):
            ContractStitcher(volume_weight=0.6, oi_weight=1.5)
    
    def test_switch_with_zero_score(self):
        """测试旧合约评分为0的切换"""
        stitcher = ContractStitcher(
            volume_weight=1.0,
            oi_weight=0.0,
            switch_threshold=1.5,
            switch_days=1
        )
        
        dates = [datetime(2024, 1, i) for i in range(1, 4)]
        
        # IF2401: 第2天成交量为0
        data1 = [
            ContractData(
                symbol="IF2401", date=dates[0],
                open=4000.0, high=4050.0, low=3950.0, close=4020.0,
                volume=20000.0, open_interest=50000.0
            ),
            ContractData(
                symbol="IF2401", date=dates[1],
                open=4020.0, high=4070.0, low=3970.0, close=4040.0,
                volume=0.0, open_interest=0.0  # 评分为0
            ),
            ContractData(
                symbol="IF2401", date=dates[2],
                open=4040.0, high=4090.0, low=3990.0, close=4060.0,
                volume=0.0, open_interest=0.0
            )
        ]
        
        # IF2402: 第2天开始有成交量
        data2 = [
            ContractData(
                symbol="IF2402", date=dates[0],
                open=4010.0, high=4060.0, low=3960.0, close=4030.0,
                volume=5000.0, open_interest=20000.0
            ),
            ContractData(
                symbol="IF2402", date=dates[1],
                open=4050.0, high=4100.0, low=4000.0, close=4070.0,
                volume=25000.0, open_interest=60000.0
            ),
            ContractData(
                symbol="IF2402", date=dates[2],
                open=4070.0, high=4120.0, low=4020.0, close=4090.0,
                volume=25000.0, open_interest=60000.0
            )
        ]
        
        stitcher.add_contract_data("IF2401", data1)
        stitcher.add_contract_data("IF2402", data2)
        
        switch_points = stitcher.detect_switch_points(
            ["IF2401", "IF2402"],
            dates[0],
            dates[2]
        )
        
        # 应该检测到切换（评分比例为无穷大）
        assert len(switch_points) >= 1
    
    def test_switch_below_threshold(self):
        """测试未达到切换阈值"""
        stitcher = ContractStitcher(
            volume_weight=1.0,
            oi_weight=0.0,
            switch_threshold=2.0,  # 高阈值
            switch_days=1
        )
        
        dates = [datetime(2024, 1, i) for i in range(1, 4)]
        
        # IF2401: 成交量逐渐下降
        data1 = [
            ContractData(
                symbol="IF2401", date=dates[0],
                open=4000.0, high=4050.0, low=3950.0, close=4020.0,
                volume=20000.0, open_interest=50000.0
            ),
            ContractData(
                symbol="IF2401", date=dates[1],
                open=4020.0, high=4070.0, low=3970.0, close=4040.0,
                volume=15000.0, open_interest=45000.0
            ),
            ContractData(
                symbol="IF2401", date=dates[2],
                open=4040.0, high=4090.0, low=3990.0, close=4060.0,
                volume=12000.0, open_interest=40000.0
            )
        ]
        
        # IF2402: 成交量增加但未达到2倍
        data2 = [
            ContractData(
                symbol="IF2402", date=dates[0],
                open=4010.0, high=4060.0, low=3960.0, close=4030.0,
                volume=5000.0, open_interest=20000.0
            ),
            ContractData(
                symbol="IF2402", date=dates[1],
                open=4050.0, high=4100.0, low=4000.0, close=4070.0,
                volume=20000.0, open_interest=40000.0  # 1.33倍，未达到2.0
            ),
            ContractData(
                symbol="IF2402", date=dates[2],
                open=4070.0, high=4120.0, low=4020.0, close=4090.0,
                volume=18000.0, open_interest=38000.0  # 1.5倍，未达到2.0
            )
        ]
        
        stitcher.add_contract_data("IF2401", data1)
        stitcher.add_contract_data("IF2402", data2)
        
        switch_points = stitcher.detect_switch_points(
            ["IF2401", "IF2402"],
            dates[0],
            dates[2]
        )
        
        # 不应该检测到切换
        assert len(switch_points) == 0
    
    def test_switch_candidate_changes(self):
        """测试候选主力变化"""
        stitcher = ContractStitcher(
            volume_weight=1.0,
            oi_weight=0.0,
            switch_threshold=1.5,
            switch_days=2
        )
        
        dates = [datetime(2024, 1, i) for i in range(1, 6)]
        
        # IF2401: 主力合约
        data1 = [
            ContractData(
                symbol="IF2401", date=date,
                open=4000.0, high=4050.0, low=3950.0, close=4020.0,
                volume=20000.0, open_interest=50000.0
            )
            for date in dates
        ]
        
        # IF2402: 第2天成交量大，第3天又小，第4-5天又大
        data2 = [
            ContractData(
                symbol="IF2402", date=dates[0],
                open=4010.0, high=4060.0, low=3960.0, close=4030.0,
                volume=5000.0, open_interest=20000.0
            ),
            ContractData(
                symbol="IF2402", date=dates[1],
                open=4030.0, high=4080.0, low=3980.0, close=4050.0,
                volume=35000.0, open_interest=60000.0  # 候选
            ),
            ContractData(
                symbol="IF2402", date=dates[2],
                open=4050.0, high=4100.0, low=4000.0, close=4070.0,
                volume=10000.0, open_interest=30000.0  # 不满足，重置
            ),
            ContractData(
                symbol="IF2402", date=dates[3],
                open=4070.0, high=4120.0, low=4020.0, close=4090.0,
                volume=35000.0, open_interest=60000.0  # 新候选
            ),
            ContractData(
                symbol="IF2402", date=dates[4],
                open=4090.0, high=4140.0, low=4040.0, close=4110.0,
                volume=35000.0, open_interest=60000.0  # 连续2天，切换
            )
        ]
        
        stitcher.add_contract_data("IF2401", data1)
        stitcher.add_contract_data("IF2402", data2)
        
        switch_points = stitcher.detect_switch_points(
            ["IF2401", "IF2402"],
            dates[0],
            dates[4]
        )
        
        # 应该在第4-5天检测到切换
        assert len(switch_points) >= 1
    
    def test_get_contract_score_no_buffer(self):
        """测试获取不存在合约的评分"""
        stitcher = ContractStitcher()
        
        score = stitcher._get_contract_score(
            datetime(2024, 1, 1),
            "NONEXISTENT"
        )
        
        assert score == 0.0
    
    def test_get_contract_price_no_buffer(self):
        """测试获取不存在合约的价格"""
        stitcher = ContractStitcher()
        
        price = stitcher._get_contract_price(
            datetime(2024, 1, 1),
            "NONEXISTENT"
        )
        
        assert price is None
    
    def test_get_contract_data_no_buffer(self):
        """测试获取不存在合约的数据"""
        stitcher = ContractStitcher()
        
        data = stitcher._get_contract_data(
            datetime(2024, 1, 1),
            "NONEXISTENT"
        )
        
        assert data is None
    
    def test_get_contract_score_no_date(self):
        """测试获取不存在日期的评分"""
        stitcher = ContractStitcher()
        
        data = [
            ContractData(
                symbol="IF2401",
                date=datetime(2024, 1, 1),
                open=4000.0, high=4050.0, low=3950.0, close=4020.0,
                volume=20000.0, open_interest=50000.0
            )
        ]
        
        stitcher.add_contract_data("IF2401", data)
        
        score = stitcher._get_contract_score(
            datetime(2024, 1, 2),  # 不存在的日期
            "IF2401"
        )
        
        assert score == 0.0
    
    def test_get_contract_price_no_date(self):
        """测试获取不存在日期的价格"""
        stitcher = ContractStitcher()
        
        data = [
            ContractData(
                symbol="IF2401",
                date=datetime(2024, 1, 1),
                open=4000.0, high=4050.0, low=3950.0, close=4020.0,
                volume=20000.0, open_interest=50000.0
            )
        ]
        
        stitcher.add_contract_data("IF2401", data)
        
        price = stitcher._get_contract_price(
            datetime(2024, 1, 2),  # 不存在的日期
            "IF2401"
        )
        
        assert price is None
    
    def test_get_contract_data_no_date(self):
        """测试获取不存在日期的数据"""
        stitcher = ContractStitcher()
        
        data = [
            ContractData(
                symbol="IF2401",
                date=datetime(2024, 1, 1),
                open=4000.0, high=4050.0, low=3950.0, close=4020.0,
                volume=20000.0, open_interest=50000.0
            )
        ]
        
        stitcher.add_contract_data("IF2401", data)
        
        contract_data = stitcher._get_contract_data(
            datetime(2024, 1, 2),  # 不存在的日期
            "IF2401"
        )
        
        assert contract_data is None
    
    def test_stitch_with_missing_data(self):
        """测试数据缺失时的拼接"""
        stitcher = ContractStitcher()
        
        dates = [datetime(2024, 1, i) for i in range(1, 6)]
        
        # 只有第1、3、5天有数据
        data = [
            ContractData(
                symbol="IF2401", date=dates[0],
                open=4000.0, high=4050.0, low=3950.0, close=4020.0,
                volume=20000.0, open_interest=50000.0
            ),
            ContractData(
                symbol="IF2401", date=dates[2],
                open=4040.0, high=4090.0, low=3990.0, close=4060.0,
                volume=20000.0, open_interest=50000.0
            ),
            ContractData(
                symbol="IF2401", date=dates[4],
                open=4080.0, high=4130.0, low=4030.0, close=4100.0,
                volume=20000.0, open_interest=50000.0
            )
        ]
        
        stitcher.add_contract_data("IF2401", data)
        
        stitched = stitcher.stitch_contracts(
            ["IF2401"],
            dates[0],
            dates[4]
        )
        
        # 只应该有3条数据（跳过缺失的日期）
        assert len(stitched) == 3
        assert stitched[0].date == dates[0]
        assert stitched[1].date == dates[2]
        assert stitched[2].date == dates[4]
    
    def test_stitch_with_no_main_contract_data(self):
        """测试主力合约无数据时的拼接"""
        stitcher = ContractStitcher()
        
        dates = [datetime(2024, 1, i) for i in range(1, 4)]
        
        # IF2401: 只有第1天有数据
        data1 = [
            ContractData(
                symbol="IF2401", date=dates[0],
                open=4000.0, high=4050.0, low=3950.0, close=4020.0,
                volume=20000.0, open_interest=50000.0
            )
        ]
        
        # IF2402: 没有数据
        data2 = []
        
        stitcher.add_contract_data("IF2401", data1)
        
        # 尝试拼接，但第2-3天没有任何合约数据
        stitched = stitcher.stitch_contracts(
            ["IF2401", "IF2402"],
            dates[0],
            dates[2]
        )
        
        # 只应该有第1天的数据
        assert len(stitched) == 1
        assert stitched[0].date == dates[0]
    
    def test_stitch_with_main_contract_missing_day_data(self):
        """测试主力合约某天数据缺失"""
        stitcher = ContractStitcher()
        
        dates = [datetime(2024, 1, i) for i in range(1, 5)]
        
        # IF2401: 第1、3天有数据，第2天缺失
        data1 = [
            ContractData(
                symbol="IF2401", date=dates[0],
                open=4000.0, high=4050.0, low=3950.0, close=4020.0,
                volume=20000.0, open_interest=50000.0
            ),
            # 第2天数据缺失
            ContractData(
                symbol="IF2401", date=dates[2],
                open=4040.0, high=4090.0, low=3990.0, close=4060.0,
                volume=20000.0, open_interest=50000.0
            ),
            ContractData(
                symbol="IF2401", date=dates[3],
                open=4060.0, high=4110.0, low=4010.0, close=4080.0,
                volume=20000.0, open_interest=50000.0
            )
        ]
        
        stitcher.add_contract_data("IF2401", data1)
        
        # 拼接时，第2天应该被跳过（因为主力合约IF2401没有该天数据）
        stitched = stitcher.stitch_contracts(
            ["IF2401"],
            dates[0],
            dates[3]
        )
        
        # 应该有3条数据（跳过第2天）
        assert len(stitched) == 3
        assert stitched[0].date == dates[0]
        assert stitched[1].date == dates[2]
        assert stitched[2].date == dates[3]
    
    def test_stitch_after_switch_with_missing_data(self):
        """测试切换后新主力合约数据缺失"""
        stitcher = ContractStitcher(
            volume_weight=1.0,
            oi_weight=0.0,
            switch_threshold=1.5,
            switch_days=1
        )
        
        dates = [datetime(2024, 1, i) for i in range(1, 6)]
        
        # IF2401: 第1-2天是主力
        data1 = [
            ContractData(
                symbol="IF2401", date=dates[0],
                open=4000.0, high=4050.0, low=3950.0, close=4020.0,
                volume=20000.0, open_interest=50000.0
            ),
            ContractData(
                symbol="IF2401", date=dates[1],
                open=4020.0, high=4070.0, low=3970.0, close=4040.0,
                volume=5000.0, open_interest=20000.0
            )
        ]
        
        # IF2402: 第2天成为主力，但第3天数据缺失
        data2 = [
            ContractData(
                symbol="IF2402", date=dates[1],
                open=4050.0, high=4100.0, low=4000.0, close=4070.0,
                volume=25000.0, open_interest=60000.0
            ),
            # 第3天数据缺失
            ContractData(
                symbol="IF2402", date=dates[3],
                open=4090.0, high=4140.0, low=4040.0, close=4110.0,
                volume=25000.0, open_interest=60000.0
            ),
            ContractData(
                symbol="IF2402", date=dates[4],
                open=4110.0, high=4160.0, low=4060.0, close=4130.0,
                volume=25000.0, open_interest=60000.0
            )
        ]
        
        stitcher.add_contract_data("IF2401", data1)
        stitcher.add_contract_data("IF2402", data2)
        
        stitched = stitcher.stitch_contracts(
            ["IF2401", "IF2402"],
            dates[0],
            dates[4]
        )
        
        # 第3天应该被跳过（新主力IF2402没有数据）
        assert len(stitched) == 4  # 第1、2、4、5天
        dates_in_stitched = [s.date for s in stitched]
        assert dates[2] not in dates_in_stitched  # 第3天不在结果中
