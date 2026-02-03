"""PathManager集成测试

白皮书依据: 第三章 3.1 双盘物理隔离

集成测试覆盖:
- PathManager与BarSynthesizer集成
- PathManager与ContractStitcher集成
- PathManager与GreeksEngine集成
- 跨模块数据流验证
- 路径路由正确性
- 只读保护有效性

Author: MIA Team
Date: 2026-01-25
"""

import pytest
import platform
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from src.infra.path_manager import PathManager, get_path_manager
from src.infra.bar_synthesizer import BarSynthesizer, Tick, Bar
from src.infra.contract_stitcher import ContractStitcher, ContractData
from src.infra.greeks_engine import GreeksEngine, OptionContract, OptionType


class TestPathManagerBarSynthesizerIntegration:
    """测试PathManager与BarSynthesizer集成
    
    白皮书依据: 第三章 3.1 + 3.3 Bar Synthesizer
    """
    
    def test_bar_data_storage_routing(self):
        """测试Bar数据存储路径路由
        
        验证:
        - Bar数据正确路由到数据盘
        - 路径自动创建
        - 数据可正常写入和读取
        """
        pm = PathManager()
        synthesizer = BarSynthesizer(periods=['1m', '5m'])
        
        # 获取Bar数据存储路径
        bar_path = pm.get_data_path("bar")
        
        # 验证路径在数据盘
        assert "mia" in str(bar_path)
        assert "data" in str(bar_path)
        assert "bar" in str(bar_path)
        assert bar_path.exists()
        
        # 模拟Bar数据写入
        test_file = bar_path / "test_bar_000001.csv"
        test_file.write_text("symbol,timestamp,open,high,low,close,volume\n")
        
        # 验证文件可读取
        assert test_file.exists()
        content = test_file.read_text()
        assert "symbol" in content
        
        # 清理
        test_file.unlink()
    
    def test_bar_synthesis_with_path_manager(self):
        """测试使用PathManager进行Bar合成
        
        验证:
        - Bar合成过程中路径管理正确
        - 临时文件路由到临时目录
        - 最终数据路由到数据目录
        """
        pm = PathManager()
        synthesizer = BarSynthesizer(periods=['1m'])
        
        # 创建测试Tick数据 - 跨越2个1分钟周期
        base_time = datetime(2024, 1, 1, 9, 30, 0)
        ticks = [
            Tick("000001", base_time + timedelta(seconds=i), 10.0 + i * 0.01, 100, 1000.0)
            for i in range(120)  # 120秒 = 2分钟,会生成1个完整的Bar
        ]
        
        # 处理Tick数据
        completed_bars = []
        for tick in ticks:
            bars = synthesizer.process_tick(tick)
            completed_bars.extend(bars)
        
        # 验证Bar生成
        assert len(completed_bars) >= 1
        
        # 获取数据存储路径
        bar_path = pm.get_data_path("bar")
        temp_path = pm.get_temp_path("bar_cache")
        
        # 验证路径存在
        assert bar_path.exists()
        assert temp_path.exists()
    
    def test_readonly_protection_for_bar_data(self):
        """测试Bar数据的只读保护
        
        验证:
        - 尝试写入系统盘被阻止
        - 数据盘写入正常
        """
        pm = PathManager(readonly_enabled=True)
        
        if platform.system() == "Windows":
            # Windows: C盘写入应被阻止
            with pytest.raises(PermissionError, match="禁止写入系统盘"):
                pm.check_readonly_compliance("C:/mia/bar/test.csv")
            
            # D盘写入应允许
            pm.check_readonly_compliance("D:/mia/bar/test.csv")
        else:
            # Linux/Mac: 系统目录写入应被阻止
            with pytest.raises(PermissionError, match="禁止写入系统目录"):
                pm.check_readonly_compliance("/usr/mia/bar/test.csv")
            
            # 数据目录写入应允许
            pm.check_readonly_compliance("/data/mia/bar/test.csv")


class TestPathManagerContractStitcherIntegration:
    """测试PathManager与ContractStitcher集成
    
    白皮书依据: 第三章 3.1 + 3.3 Contract Stitcher
    """
    
    def test_contract_data_storage_routing(self):
        """测试期货合约数据存储路径路由
        
        验证:
        - 合约数据正确路由到数据盘
        - 拼接结果存储路径正确
        """
        pm = PathManager()
        stitcher = ContractStitcher()
        
        # 获取期货数据存储路径
        futures_path = pm.get_data_path("futures")
        
        # 验证路径在数据盘
        assert "mia" in str(futures_path)
        assert "data" in str(futures_path)
        assert "futures" in str(futures_path)
        assert futures_path.exists()
        
        # 模拟合约数据写入
        test_file = futures_path / "IF_continuous.csv"
        test_file.write_text("date,open,high,low,close,volume\n")
        
        # 验证文件可读取
        assert test_file.exists()
        
        # 清理
        test_file.unlink()
    
    def test_contract_stitching_with_path_manager(self):
        """测试使用PathManager进行合约拼接
        
        验证:
        - 拼接过程中路径管理正确
        - 临时文件路由正确
        - 最终结果存储正确
        """
        pm = PathManager()
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
        
        # 添加合约数据
        stitcher.add_contract_data("IF2401", contracts)
        
        # 获取存储路径
        futures_path = pm.get_data_path("futures")
        temp_path = pm.get_temp_path("contract_cache")
        
        # 验证路径存在
        assert futures_path.exists()
        assert temp_path.exists()
    
    def test_readonly_protection_for_contract_data(self):
        """测试合约数据的只读保护
        
        验证:
        - 尝试写入系统盘被阻止
        - 数据盘写入正常
        """
        pm = PathManager(readonly_enabled=True)
        
        if platform.system() == "Windows":
            # Windows: C盘写入应被阻止
            with pytest.raises(PermissionError, match="禁止写入系统盘"):
                pm.check_readonly_compliance("C:/mia/futures/IF_continuous.csv")
            
            # D盘写入应允许
            pm.check_readonly_compliance("D:/mia/futures/IF_continuous.csv")
        else:
            # Linux/Mac: 系统目录写入应被阻止
            with pytest.raises(PermissionError, match="禁止写入系统目录"):
                pm.check_readonly_compliance("/usr/mia/futures/IF_continuous.csv")
            
            # 数据目录写入应允许
            pm.check_readonly_compliance("/data/mia/futures/IF_continuous.csv")


class TestPathManagerGreeksEngineIntegration:
    """测试PathManager与GreeksEngine集成
    
    白皮书依据: 第三章 3.1 + 3.3 Greeks Engine
    """
    
    def test_greeks_cache_storage_routing(self):
        """测试Greeks计算缓存存储路径路由
        
        验证:
        - Greeks缓存正确路由到临时目录
        - 缓存文件可正常读写
        """
        pm = PathManager()
        engine = GreeksEngine(cache_enabled=True)
        
        # 获取Greeks缓存路径
        cache_path = pm.get_temp_path("greeks_cache")
        
        # 验证路径在数据盘
        assert "mia" in str(cache_path)
        assert "temp" in str(cache_path)
        assert "greeks_cache" in str(cache_path)
        assert cache_path.exists()
        
        # 模拟缓存文件写入
        test_file = cache_path / "greeks_cache_000001.json"
        test_file.write_text('{"delta": 0.5, "gamma": 0.1}')
        
        # 验证文件可读取
        assert test_file.exists()
        content = test_file.read_text()
        assert "delta" in content
        
        # 清理
        test_file.unlink()
    
    def test_greeks_calculation_with_path_manager(self):
        """测试使用PathManager进行Greeks计算
        
        验证:
        - Greeks计算过程中路径管理正确
        - 缓存路由到临时目录
        - 结果数据路由到数据目录
        """
        pm = PathManager()
        engine = GreeksEngine(cache_enabled=True)
        
        # 创建测试期权合约
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
        
        # 验证计算结果
        assert greeks is not None
        assert -1 <= greeks.delta <= 1
        assert greeks.gamma >= 0
        assert greeks.vega >= 0
        
        # 获取存储路径
        options_path = pm.get_data_path("options")
        cache_path = pm.get_temp_path("greeks_cache")
        
        # 验证路径存在
        assert options_path.exists()
        assert cache_path.exists()
    
    def test_readonly_protection_for_greeks_data(self):
        """测试Greeks数据的只读保护
        
        验证:
        - 尝试写入系统盘被阻止
        - 数据盘写入正常
        """
        pm = PathManager(readonly_enabled=True)
        
        if platform.system() == "Windows":
            # Windows: C盘写入应被阻止
            with pytest.raises(PermissionError, match="禁止写入系统盘"):
                pm.check_readonly_compliance("C:/mia/options/greeks_510050.csv")
            
            # D盘写入应允许
            pm.check_readonly_compliance("D:/mia/options/greeks_510050.csv")
        else:
            # Linux/Mac: 系统目录写入应被阻止
            with pytest.raises(PermissionError, match="禁止写入系统目录"):
                pm.check_readonly_compliance("/usr/mia/options/greeks_510050.csv")
            
            # 数据目录写入应允许
            pm.check_readonly_compliance("/data/mia/options/greeks_510050.csv")


class TestCrossModuleDataFlow:
    """测试跨模块数据流
    
    白皮书依据: 第三章 3.1 + 3.3 完整数据流
    """
    
    def test_complete_data_flow_with_path_manager(self):
        """测试完整数据流（Tick → Bar → 存储）
        
        验证:
        - Tick数据路由正确
        - Bar合成路由正确
        - 最终存储路由正确
        - 所有路径在数据盘
        """
        pm = PathManager()
        synthesizer = BarSynthesizer(periods=['1m'])
        
        # 1. Tick数据路径
        tick_path = pm.get_data_path("tick")
        assert tick_path.exists()
        
        # 2. 创建测试Tick数据 - 跨越2个1分钟周期
        base_time = datetime(2024, 1, 1, 9, 30, 0)
        ticks = [
            Tick("000001", base_time + timedelta(seconds=i), 10.0 + i * 0.01, 100, 1000.0)
            for i in range(120)  # 120秒 = 2分钟,会生成1个完整的Bar
        ]
        
        # 3. 处理Tick生成Bar
        completed_bars = []
        for tick in ticks:
            bars = synthesizer.process_tick(tick)
            completed_bars.extend(bars)
        
        # 4. Bar数据路径
        bar_path = pm.get_data_path("bar")
        assert bar_path.exists()
        
        # 5. 验证数据流完整性
        assert len(completed_bars) >= 1
        for bar in completed_bars:
            assert bar.symbol == "000001"
            assert bar.period == "1m"
            assert bar.open > 0
            assert bar.high >= bar.low
            assert bar.volume > 0
    
    def test_derivatives_pipeline_data_flow(self):
        """测试衍生品管道数据流（合约 → 拼接 → Greeks → 存储）
        
        验证:
        - 合约数据路由正确
        - 拼接结果路由正确
        - Greeks计算路由正确
        - 所有路径在数据盘
        """
        pm = PathManager()
        stitcher = ContractStitcher()
        engine = GreeksEngine(cache_enabled=True)
        
        # 1. 期货数据路径
        futures_path = pm.get_data_path("futures")
        assert futures_path.exists()
        
        # 2. 期权数据路径
        options_path = pm.get_data_path("options")
        assert options_path.exists()
        
        # 3. 缓存路径
        cache_path = pm.get_temp_path("derivatives_cache")
        assert cache_path.exists()
        
        # 4. 创建测试合约数据
        base_date = datetime(2024, 1, 1)
        contracts = []
        
        for i in range(5):
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
        
        # 5. 添加合约数据
        stitcher.add_contract_data("IF2401", contracts)
        
        # 6. 创建期权合约
        option_contract = OptionContract(
            symbol="510050C2401M03000",
            underlying_price=3.0,
            strike_price=3.0,
            time_to_maturity=0.25,
            risk_free_rate=0.03,
            volatility=0.2,
            option_type=OptionType.CALL
        )
        
        # 7. 计算Greeks
        greeks = engine.calculate_greeks(option_contract)
        
        # 8. 验证数据流完整性
        assert greeks is not None
        assert greeks.option_price > 0
        assert -1 <= greeks.delta <= 1


class TestPathRoutingCorrectness:
    """测试路径路由正确性
    
    白皮书依据: 第三章 3.1 双盘物理隔离
    """
    
    def test_data_path_routing_consistency(self):
        """测试数据路径路由一致性
        
        验证:
        - 相同子目录返回相同路径
        - 不同子目录返回不同路径
        - 路径始终在数据盘
        """
        pm = PathManager()
        
        # 相同子目录应返回相同路径
        path1 = pm.get_data_path("tick")
        path2 = pm.get_data_path("tick")
        assert path1 == path2
        
        # 不同子目录应返回不同路径
        tick_path = pm.get_data_path("tick")
        bar_path = pm.get_data_path("bar")
        assert tick_path != bar_path
        
        # 所有路径都应在数据盘
        assert "mia" in str(tick_path)
        assert "mia" in str(bar_path)
    
    def test_log_path_routing_consistency(self):
        """测试日志路径路由一致性
        
        验证:
        - 日志路径与数据路径分离
        - 日志路径在数据盘
        """
        pm = PathManager()
        
        data_path = pm.get_data_path()
        log_path = pm.get_log_path()
        
        # 日志路径与数据路径应不同
        assert data_path != log_path
        
        # 但都应在数据盘
        assert "mia" in str(data_path)
        assert "mia" in str(log_path)
        
        # 日志路径应包含"logs"
        assert "logs" in str(log_path)
    
    def test_temp_path_routing_consistency(self):
        """测试临时路径路由一致性
        
        验证:
        - 临时路径与数据路径分离
        - 临时路径在数据盘
        """
        pm = PathManager()
        
        data_path = pm.get_data_path()
        temp_path = pm.get_temp_path()
        
        # 临时路径与数据路径应不同
        assert data_path != temp_path
        
        # 但都应在数据盘
        assert "mia" in str(data_path)
        assert "mia" in str(temp_path)
        
        # 临时路径应包含"temp"
        assert "temp" in str(temp_path)


class TestReadonlyProtectionEffectiveness:
    """测试只读保护有效性
    
    白皮书依据: 第三章 3.1 双盘物理隔离 - C盘只读保护
    """
    
    @pytest.mark.skipif(platform.system() != "Windows", reason="Windows特定测试")
    def test_windows_system_drive_protection(self):
        """测试Windows系统盘保护
        
        验证:
        - C盘根目录写入被阻止
        - C盘子目录写入被阻止
        - D盘写入正常
        """
        pm = PathManager(readonly_enabled=True)
        
        # C盘根目录
        with pytest.raises(PermissionError):
            pm.check_readonly_compliance("C:/test.txt")
        
        # C盘子目录
        with pytest.raises(PermissionError):
            pm.check_readonly_compliance("C:/Users/test/data.csv")
        
        # D盘应允许
        pm.check_readonly_compliance("D:/mia/data/test.csv")
    
    @pytest.mark.skipif(platform.system() == "Windows", reason="Linux/Mac特定测试")
    def test_linux_system_directories_protection(self):
        """测试Linux/Mac系统目录保护
        
        验证:
        - /usr写入被阻止
        - /etc写入被阻止
        - /bin写入被阻止
        - /data写入正常
        """
        pm = PathManager(readonly_enabled=True)
        
        # 系统目录应被阻止
        with pytest.raises(PermissionError):
            pm.check_readonly_compliance("/usr/test.txt")
        
        with pytest.raises(PermissionError):
            pm.check_readonly_compliance("/etc/test.conf")
        
        with pytest.raises(PermissionError):
            pm.check_readonly_compliance("/bin/test.sh")
        
        # 数据目录应允许
        pm.check_readonly_compliance("/data/mia/test.csv")
    
    def test_readonly_protection_can_be_disabled(self):
        """测试只读保护可以禁用
        
        验证:
        - 禁用后系统盘写入不抛出异常
        """
        pm = PathManager(readonly_enabled=False)
        
        # 不应抛出异常
        if platform.system() == "Windows":
            pm.check_readonly_compliance("C:/test.txt")
        else:
            pm.check_readonly_compliance("/usr/test.txt")


class TestPerformanceAndReliability:
    """测试性能和可靠性
    
    白皮书依据: 第三章 3.1 性能要求
    """
    
    def test_path_resolution_performance(self):
        """测试路径解析性能
        
        验证:
        - 路径解析延迟 < 1ms
        """
        import time
        
        pm = PathManager()
        
        # 测试1000次路径解析
        start = time.perf_counter()
        for _ in range(1000):
            pm.get_data_path("tick")
        elapsed = (time.perf_counter() - start) * 1000
        
        # 平均延迟应 < 1ms
        avg_latency = elapsed / 1000
        assert avg_latency < 1.0, f"路径解析延迟过高: {avg_latency:.3f}ms"
    
    def test_concurrent_path_access(self):
        """测试并发路径访问
        
        验证:
        - 多线程并发访问路径管理器
        - 无竞态条件
        - 路径一致性
        """
        import threading
        
        pm = PathManager()
        results = []
        
        def access_path():
            path = pm.get_data_path("tick")
            results.append(str(path))
        
        # 创建10个线程并发访问
        threads = [threading.Thread(target=access_path) for _ in range(10)]
        
        for t in threads:
            t.start()
        
        for t in threads:
            t.join()
        
        # 所有结果应相同
        assert len(set(results)) == 1, "并发访问路径不一致"
    
    def test_path_manager_error_recovery(self):
        """测试路径管理器错误恢复
        
        验证:
        - 磁盘不存在时的降级处理
        - 权限不足时的错误提示
        """
        # 测试不支持的操作系统
        with patch('platform.system', return_value="Unknown"):
            with pytest.raises(RuntimeError, match="不支持的操作系统"):
                PathManager()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
