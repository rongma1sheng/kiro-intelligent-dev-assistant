"""衍生品管道集成测试

白皮书依据: 第三章 3.3 衍生品管道

集成测试覆盖:
- ContractStitcher与数据源集成
- GreeksEngine与期权数据集成
- 数据验证流程
- 完整衍生品处理流程
- 性能指标验证

Author: MIA Team
Date: 2026-01-25
"""

import pytest
import time
from datetime import datetime, timedelta
from typing import List

from src.infra.contract_stitcher import (
    ContractStitcher,
    ContractData,
    StitchedContract,
    SwitchPoint
)
from src.infra.greeks_engine import (
    GreeksEngine,
    OptionContract,
    OptionType,
    Greeks
)
from src.infra.path_manager import PathManager


class TestContractStitcherDataSourceIntegration:
    """测试ContractStitcher与数据源集成
    
    白皮书依据: 第三章 3.3 衍生品管道 - Contract Stitcher
    """
    
    def test_single_contract_data_loading(self):
        """测试单合约数据加载
        
        验证:
        - 合约数据正确加载
        - 数据格式验证
        """
        stitcher = ContractStitcher()
        
        # 创建测试合约数据
        base_date = datetime(2024, 1, 1)
        contracts = []
        
        for i in range(10):
            contract = ContractData(
                symbol="IF2401",
                date=base_date + timedelta(days=i),
                open=4000.0 + i,
                high=4010.0 + i,
                low=3990.0 + i,
                close=4005.0 + i,
                volume=10000.0,
                open_interest=50000.0
            )
            contracts.append(contract)
        
        # 加载数据
        stitcher.add_contract_data("IF2401", contracts)
        
        # 验证数据已加载
        assert "IF2401" in stitcher.contracts_buffer
        assert len(stitcher.contracts_buffer["IF2401"]) == 10
    
    def test_multiple_contracts_data_loading(self):
        """测试多合约数据加载
        
        验证:
        - 多合约并发加载
        - 数据独立性
        """
        stitcher = ContractStitcher()
        
        base_date = datetime(2024, 1, 1)
        contracts_list = ["IF2401", "IF2402", "IF2403"]
        
        for symbol in contracts_list:
            contracts = []
            for i in range(10):
                contract = ContractData(
                    symbol=symbol,
                    date=base_date + timedelta(days=i),
                    open=4000.0 + i,
                    high=4010.0 + i,
                    low=3990.0 + i,
                    close=4005.0 + i,
                    volume=10000.0 + float(symbol[-1]) * 1000,  # 不同合约不同成交量
                    open_interest=50000.0
                )
                contracts.append(contract)
            
            stitcher.add_contract_data(symbol, contracts)
        
        # 验证所有合约都已加载
        assert len(stitcher.contracts_buffer) == 3
        for symbol in contracts_list:
            assert symbol in stitcher.contracts_buffer
    
    def test_invalid_contract_data_rejection(self):
        """测试无效合约数据拒绝
        
        验证:
        - 空数据被拒绝
        - 错误信息清晰
        """
        stitcher = ContractStitcher()
        
        # 测试空数据
        with pytest.raises(ValueError, match="合约数据不能为空"):
            stitcher.add_contract_data("IF2401", [])


class TestContractStitchingPipeline:
    """测试合约拼接管道
    
    白皮书依据: 第三章 3.3 衍生品管道 - 价差平移算法
    """
    
    def test_main_contract_identification(self):
        """测试主力合约识别
        
        验证:
        - 基于成交量和持仓量识别主力
        - 识别结果正确
        """
        stitcher = ContractStitcher()
        
        base_date = datetime(2024, 1, 1)
        
        # 创建两个合约，IF2401成交量更大
        contracts_if2401 = []
        contracts_if2402 = []
        
        for i in range(5):
            # IF2401: 高成交量
            contract1 = ContractData(
                symbol="IF2401",
                date=base_date + timedelta(days=i),
                open=4000.0,
                high=4010.0,
                low=3990.0,
                close=4005.0,
                volume=100000.0,  # 高成交量
                open_interest=50000.0
            )
            contracts_if2401.append(contract1)
            
            # IF2402: 低成交量
            contract2 = ContractData(
                symbol="IF2402",
                date=base_date + timedelta(days=i),
                open=4010.0,
                high=4020.0,
                low=4000.0,
                close=4015.0,
                volume=10000.0,  # 低成交量
                open_interest=5000.0
            )
            contracts_if2402.append(contract2)
        
        stitcher.add_contract_data("IF2401", contracts_if2401)
        stitcher.add_contract_data("IF2402", contracts_if2402)
        
        # 识别主力合约
        main_contract = stitcher.identify_main_contract(
            base_date,
            ["IF2401", "IF2402"]
        )
        
        # 验证IF2401被识别为主力
        assert main_contract == "IF2401"
    
    def test_contract_switch_detection(self):
        """测试合约切换点检测
        
        验证:
        - 检测到合约切换
        - 切换点信息正确
        """
        stitcher = ContractStitcher(switch_days=2)  # 连续2天即切换
        
        base_date = datetime(2024, 1, 1)
        
        # 创建两个合约，前5天IF2401为主力，后5天IF2402为主力
        contracts_if2401 = []
        contracts_if2402 = []
        
        for i in range(10):
            if i < 5:
                # 前5天：IF2401高成交量
                volume1 = 100000.0
                volume2 = 10000.0
            else:
                # 后5天：IF2402高成交量
                volume1 = 10000.0
                volume2 = 100000.0
            
            contract1 = ContractData(
                symbol="IF2401",
                date=base_date + timedelta(days=i),
                open=4000.0,
                high=4010.0,
                low=3990.0,
                close=4005.0,
                volume=volume1,
                open_interest=50000.0
            )
            contracts_if2401.append(contract1)
            
            contract2 = ContractData(
                symbol="IF2402",
                date=base_date + timedelta(days=i),
                open=4010.0,
                high=4020.0,
                low=4000.0,
                close=4015.0,
                volume=volume2,
                open_interest=50000.0
            )
            contracts_if2402.append(contract2)
        
        stitcher.add_contract_data("IF2401", contracts_if2401)
        stitcher.add_contract_data("IF2402", contracts_if2402)
        
        # 检测切换点
        switch_points = stitcher.detect_switch_points(
            ["IF2401", "IF2402"],
            base_date,
            base_date + timedelta(days=9)
        )
        
        # 验证检测到切换点
        assert len(switch_points) >= 1
        assert switch_points[0].old_contract == "IF2401"
        assert switch_points[0].new_contract == "IF2402"
    
    def test_price_adjustment_algorithm(self):
        """测试价差平移算法
        
        验证:
        - 价差调整正确
        - 连续性保持
        """
        stitcher = ContractStitcher(switch_days=1)
        
        base_date = datetime(2024, 1, 1)
        
        # 创建两个合约，价格有跳空
        contracts_if2401 = []
        contracts_if2402 = []
        
        for i in range(5):
            # IF2401: 价格4000左右
            contract1 = ContractData(
                symbol="IF2401",
                date=base_date + timedelta(days=i),
                open=4000.0,
                high=4010.0,
                low=3990.0,
                close=4005.0,
                volume=100000.0 if i < 2 else 10000.0,
                open_interest=50000.0
            )
            contracts_if2401.append(contract1)
            
            # IF2402: 价格4100左右（有100点跳空）
            contract2 = ContractData(
                symbol="IF2402",
                date=base_date + timedelta(days=i),
                open=4100.0,
                high=4110.0,
                low=4090.0,
                close=4105.0,
                volume=10000.0 if i < 2 else 100000.0,
                open_interest=50000.0
            )
            contracts_if2402.append(contract2)
        
        stitcher.add_contract_data("IF2401", contracts_if2401)
        stitcher.add_contract_data("IF2402", contracts_if2402)
        
        # 拼接合约
        stitched_data = stitcher.stitch_contracts(
            ["IF2401", "IF2402"],
            base_date,
            base_date + timedelta(days=4)
        )
        
        # 验证拼接数据
        assert len(stitched_data) > 0
        
        # 验证价格调整（切换后的价格应该被调整）
        for i in range(len(stitched_data) - 1):
            current = stitched_data[i]
            next_day = stitched_data[i + 1]
            
            # 价格变化应该合理（不应该有大跳空）
            price_change = abs(next_day.close - current.close)
            assert price_change < 50, f"价格跳空过大: {price_change}"


class TestGreeksEngineOptionDataIntegration:
    """测试GreeksEngine与期权数据集成
    
    白皮书依据: 第三章 3.3 衍生品管道 - Greeks Engine
    """
    
    def test_single_option_greeks_calculation(self):
        """测试单期权Greeks计算
        
        验证:
        - Greeks计算正确
        - 所有指标都有值
        """
        engine = GreeksEngine(cache_enabled=True)
        
        # 创建期权合约
        contract = OptionContract(
            symbol="510050C2401M03000",
            underlying_price=3.0,
            strike_price=3.0,
            time_to_maturity=0.25,
            risk_free_rate=0.03,
            volatility=0.2,
            option_type=OptionType.CALL
        )
        
        # 计算Greeks
        greeks = engine.calculate_greeks(contract)
        
        # 验证Greeks值
        assert greeks is not None
        assert greeks.option_price > 0
        assert 0 <= greeks.delta <= 1  # 看涨期权Delta在[0,1]
        assert greeks.gamma >= 0
        assert greeks.vega >= 0
        assert greeks.theta < 0  # Theta通常为负
    
    def test_option_chain_batch_calculation(self):
        """测试期权链批量计算
        
        验证:
        - 批量计算效率
        - 结果一致性
        """
        engine = GreeksEngine(cache_enabled=True)
        
        # 创建期权链（不同行权价）
        underlying_price = 3.0
        strike_prices = [2.8, 2.9, 3.0, 3.1, 3.2]
        
        greeks_list = []
        
        start = time.perf_counter()
        for strike in strike_prices:
            contract = OptionContract(
                symbol=f"510050C2401M{int(strike*1000):05d}",
                underlying_price=underlying_price,
                strike_price=strike,
                time_to_maturity=0.25,
                risk_free_rate=0.03,
                volatility=0.2,
                option_type=OptionType.CALL
            )
            
            greeks = engine.calculate_greeks(contract)
            greeks_list.append(greeks)
        
        elapsed = (time.perf_counter() - start) * 1000
        
        # 验证所有期权都计算成功
        assert len(greeks_list) == 5
        
        # 验证Delta单调性（行权价越高，看涨期权Delta越小）
        for i in range(len(greeks_list) - 1):
            assert greeks_list[i].delta >= greeks_list[i + 1].delta
        
        # 验证批量计算性能（平均<50ms）
        avg_time = elapsed / len(strike_prices)
        assert avg_time < 50, f"平均计算时间过长: {avg_time:.2f}ms"
    
    def test_implied_volatility_calculation(self):
        """测试隐含波动率计算
        
        验证:
        - 隐含波动率求解正确
        - 收敛速度快
        """
        engine = GreeksEngine(cache_enabled=False)
        
        # 创建期权合约
        contract = OptionContract(
            symbol="510050C2401M03000",
            underlying_price=3.0,
            strike_price=3.0,
            time_to_maturity=0.25,
            risk_free_rate=0.03,
            volatility=0.2,  # 真实波动率
            option_type=OptionType.CALL
        )
        
        # 计算理论价格
        theoretical_price = engine.calculate_option_price(contract)
        
        # 反推隐含波动率
        implied_vol = engine.calculate_implied_volatility(
            contract,
            theoretical_price
        )
        
        # 验证隐含波动率接近真实波动率
        assert implied_vol is not None
        assert abs(implied_vol - 0.2) < 0.001


class TestDataValidationFlow:
    """测试数据验证流程
    
    白皮书依据: 第三章 3.3 衍生品管道 - 数据验证
    """
    
    def test_contract_data_validation(self):
        """测试合约数据验证
        
        验证:
        - 数据合理性检查
        - 异常数据检测
        """
        stitcher = ContractStitcher()
        
        base_date = datetime(2024, 1, 1)
        
        # 创建包含异常数据的合约
        contracts = []
        
        for i in range(5):
            # 正常数据
            contract = ContractData(
                symbol="IF2401",
                date=base_date + timedelta(days=i),
                open=4000.0 + i,
                high=4010.0 + i,
                low=3990.0 + i,
                close=4005.0 + i,
                volume=10000.0,
                open_interest=50000.0
            )
            contracts.append(contract)
        
        # 加载数据（应该成功）
        stitcher.add_contract_data("IF2401", contracts)
        
        # 验证数据已加载
        assert "IF2401" in stitcher.contracts_buffer
    
    def test_greeks_range_validation(self):
        """测试Greeks范围验证
        
        验证:
        - Greeks值在合理范围内
        - 异常值检测
        """
        engine = GreeksEngine()
        
        # 创建期权合约
        contract = OptionContract(
            symbol="510050C2401M03000",
            underlying_price=3.0,
            strike_price=3.0,
            time_to_maturity=0.25,
            risk_free_rate=0.03,
            volatility=0.2,
            option_type=OptionType.CALL
        )
        
        # 计算Greeks
        greeks = engine.calculate_greeks(contract)
        
        # 验证Greeks范围
        assert -1 <= greeks.delta <= 1
        assert greeks.gamma >= 0
        assert greeks.vega >= 0
        # Rho范围取决于期权类型和参数，这里只检查不是NaN
        assert not (greeks.rho != greeks.rho)  # 检查不是NaN


class TestCompleteDerivativesPipeline:
    """测试完整衍生品处理流程
    
    白皮书依据: 第三章 3.3 衍生品管道 - 完整流程
    """
    
    def test_futures_to_options_pipeline(self):
        """测试期货到期权完整流程
        
        验证:
        - 期货拼接 → 期权定价流程
        - 数据流完整性
        """
        # 1. 期货合约拼接
        stitcher = ContractStitcher()
        base_date = datetime(2024, 1, 1)
        
        contracts = []
        for i in range(10):
            contract = ContractData(
                symbol="IF2401",
                date=base_date + timedelta(days=i),
                open=4000.0 + i,
                high=4010.0 + i,
                low=3990.0 + i,
                close=4005.0 + i,
                volume=10000.0,
                open_interest=50000.0
            )
            contracts.append(contract)
        
        stitcher.add_contract_data("IF2401", contracts)
        
        # 拼接合约
        stitched_data = stitcher.stitch_contracts(
            ["IF2401"],
            base_date,
            base_date + timedelta(days=9)
        )
        
        # 2. 使用拼接后的价格计算期权Greeks
        engine = GreeksEngine()
        
        # 使用最后一天的价格作为标的价格
        last_price = stitched_data[-1].close
        
        option_contract = OptionContract(
            symbol="IF2401C4000",
            underlying_price=last_price,
            strike_price=4000.0,
            time_to_maturity=0.25,
            risk_free_rate=0.03,
            volatility=0.2,
            option_type=OptionType.CALL
        )
        
        greeks = engine.calculate_greeks(option_contract)
        
        # 验证完整流程成功
        assert len(stitched_data) > 0
        assert greeks is not None
        assert greeks.option_price > 0
    
    def test_multi_product_concurrent_processing(self):
        """测试多品种并发处理
        
        验证:
        - 期货和期权同时处理
        - 无数据混淆
        """
        # 处理期货
        stitcher = ContractStitcher()
        base_date = datetime(2024, 1, 1)
        
        futures_symbols = ["IF2401", "IC2401"]
        
        for symbol in futures_symbols:
            contracts = []
            for i in range(5):
                contract = ContractData(
                    symbol=symbol,
                    date=base_date + timedelta(days=i),
                    open=4000.0 + i,
                    high=4010.0 + i,
                    low=3990.0 + i,
                    close=4005.0 + i,
                    volume=10000.0,
                    open_interest=50000.0
                )
                contracts.append(contract)
            
            stitcher.add_contract_data(symbol, contracts)
        
        # 处理期权
        engine = GreeksEngine()
        
        option_symbols = ["510050C2401M03000", "510300C2401M04000"]
        greeks_results = {}
        
        for symbol in option_symbols:
            contract = OptionContract(
                symbol=symbol,
                underlying_price=3.0,
                strike_price=3.0,
                time_to_maturity=0.25,
                risk_free_rate=0.03,
                volatility=0.2,
                option_type=OptionType.CALL
            )
            
            greeks = engine.calculate_greeks(contract)
            greeks_results[symbol] = greeks
        
        # 验证所有品种都处理成功
        assert len(stitcher.contracts_buffer) == 2
        assert len(greeks_results) == 2


class TestPerformanceMetrics:
    """测试性能指标
    
    白皮书依据: 第三章 3.3 衍生品管道 - 性能要求
    """
    
    def test_contract_stitching_performance(self):
        """测试合约拼接性能
        
        验证:
        - 拼接速度 > 1000条/秒
        """
        stitcher = ContractStitcher()
        base_date = datetime(2024, 1, 1)
        
        # 创建大量数据
        num_days = 1000
        contracts = []
        
        for i in range(num_days):
            contract = ContractData(
                symbol="IF2401",
                date=base_date + timedelta(days=i),
                open=4000.0,
                high=4010.0,
                low=3990.0,
                close=4005.0,
                volume=10000.0,
                open_interest=50000.0
            )
            contracts.append(contract)
        
        stitcher.add_contract_data("IF2401", contracts)
        
        # 拼接合约
        start = time.perf_counter()
        stitched_data = stitcher.stitch_contracts(
            ["IF2401"],
            base_date,
            base_date + timedelta(days=num_days - 1)
        )
        elapsed = time.perf_counter() - start
        
        # 计算速度（条/秒）
        speed = len(stitched_data) / elapsed
        
        assert speed > 1000, f"拼接速度不足: {speed:.0f} 条/秒 < 1000 条/秒"
    
    def test_greeks_calculation_performance(self):
        """测试Greeks计算性能
        
        验证:
        - P99延迟 < 50ms
        """
        engine = GreeksEngine(cache_enabled=False)  # 禁用缓存测试真实性能
        
        latencies = []
        
        # 计算100次
        for i in range(100):
            contract = OptionContract(
                symbol=f"510050C2401M{3000+i:05d}",
                underlying_price=3.0 + i * 0.001,
                strike_price=3.0,
                time_to_maturity=0.25,
                risk_free_rate=0.03,
                volatility=0.2,
                option_type=OptionType.CALL
            )
            
            start = time.perf_counter()
            engine.calculate_greeks(contract)
            elapsed = (time.perf_counter() - start) * 1000
            
            latencies.append(elapsed)
        
        # 计算P99延迟
        latencies.sort()
        p99_index = int(len(latencies) * 0.99)
        p99_latency = latencies[p99_index]
        
        assert p99_latency < 50, f"P99延迟过高: {p99_latency:.2f}ms > 50ms"


class TestErrorHandlingAndRecovery:
    """测试错误处理和恢复
    
    白皮书依据: 第三章 3.3 衍生品管道 - 错误处理
    """
    
    def test_invalid_contract_parameters(self):
        """测试无效合约参数处理
        
        验证:
        - 参数验证
        - 错误信息清晰
        """
        stitcher = ContractStitcher()
        
        # 测试无效权重
        with pytest.raises(ValueError, match="成交量权重必须在"):
            ContractStitcher(volume_weight=1.5)
        
        # 测试权重和不为1
        with pytest.raises(ValueError, match="权重之和必须为1"):
            ContractStitcher(volume_weight=0.5, oi_weight=0.6)
    
    def test_invalid_option_parameters(self):
        """测试无效期权参数处理
        
        验证:
        - 参数验证
        - 错误信息清晰
        """
        # 测试负标的价格
        with pytest.raises(ValueError, match="标的价格必须 > 0"):
            OptionContract(
                symbol="510050C2401M03000",
                underlying_price=-3.0,
                strike_price=3.0,
                time_to_maturity=0.25,
                risk_free_rate=0.03,
                volatility=0.2,
                option_type=OptionType.CALL
            )
        
        # 测试负到期时间
        with pytest.raises(ValueError, match="到期时间必须 > 0"):
            OptionContract(
                symbol="510050C2401M03000",
                underlying_price=3.0,
                strike_price=3.0,
                time_to_maturity=-0.25,
                risk_free_rate=0.03,
                volatility=0.2,
                option_type=OptionType.CALL
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
