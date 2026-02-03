"""历史桥接器单元测试

白皮书依据: 第三章 3.4
"""

import pytest
import pandas as pd
from datetime import date, timedelta
from unittest.mock import Mock, patch, MagicMock

from src.infra.bridge import (
    HistoricalBridge,
    BridgeConfig,
    AssetType,
    GuojinAdapter,
    AkshareAdapter,
    DataNormalizer,
    PlatformError,
    GuojinAPIError,
    AkshareError,
    DataFormatError,
    ConfigurationError,
    InterfaceInfo,
    InterfaceTestResult
)


class TestDataNormalizer:
    """测试数据标准化器"""
    
    def test_normalize_symbol_akshare_sh(self):
        """测试Akshare上交所代码标准化"""
        normalizer = DataNormalizer()
        result = normalizer.normalize_symbol("600000", "akshare")
        assert result == "600000.SH"
    
    def test_normalize_symbol_akshare_sz(self):
        """测试Akshare深交所代码标准化"""
        normalizer = DataNormalizer()
        result = normalizer.normalize_symbol("000001", "akshare")
        assert result == "000001.SZ"
    
    def test_normalize_symbol_akshare_already_normalized(self):
        """测试已标准化的Akshare代码"""
        normalizer = DataNormalizer()
        result = normalizer.normalize_symbol("000001.SZ", "akshare")
        assert result == "000001.SZ"
    
    def test_normalize_symbol_guojin(self):
        """测试国金代码标准化（已是标准格式）"""
        normalizer = DataNormalizer()
        result = normalizer.normalize_symbol("000001.SZ", "guojin")
        assert result == "000001.SZ"
    
    def test_normalize_symbol_unknown_platform(self):
        """测试未知平台代码标准化"""
        normalizer = DataNormalizer()
        result = normalizer.normalize_symbol("TEST", "unknown")
        assert result == "TEST"
    
    def test_normalize_dataframe_akshare(self):
        """测试Akshare数据标准化"""
        normalizer = DataNormalizer()
        
        # 创建Akshare格式的数据
        df = pd.DataFrame({
            '日期': ['2024-01-01', '2024-01-02'],
            '开盘': [10.0, 10.5],
            '最高': [10.5, 11.0],
            '最低': [9.5, 10.0],
            '收盘': [10.2, 10.8],
            '成交量': [1000000, 1200000]
        })
        
        result = normalizer.normalize_dataframe(df, "akshare")
        
        # 验证列名
        assert list(result.columns) == ['open', 'high', 'low', 'close', 'volume']
        
        # 验证索引是日期
        assert isinstance(result.index, pd.DatetimeIndex)
        
        # 验证数据类型
        assert result['open'].dtype in [float, 'float64']
        assert result['volume'].dtype in [int, 'int64', float, 'float64']
        
        # 验证行数
        assert len(result) == 2
    
    def test_normalize_dataframe_guojin(self):
        """测试国金数据标准化"""
        normalizer = DataNormalizer()
        
        # 创建国金格式的数据
        df = pd.DataFrame({
            'date': ['2024-01-01', '2024-01-02'],
            'open': [10.0, 10.5],
            'high': [10.5, 11.0],
            'low': [9.5, 10.0],
            'close': [10.2, 10.8],
            'volume': [1000000, 1200000]
        })
        
        result = normalizer.normalize_dataframe(df, "guojin")
        
        # 验证列名
        assert list(result.columns) == ['open', 'high', 'low', 'close', 'volume']
        
        # 验证索引是日期
        assert isinstance(result.index, pd.DatetimeIndex)
        
        # 验证行数
        assert len(result) == 2
    
    def test_normalize_dataframe_empty(self):
        """测试空DataFrame标准化"""
        normalizer = DataNormalizer()
        df = pd.DataFrame()
        
        with pytest.raises(DataFormatError, match="Cannot normalize empty DataFrame"):
            normalizer.normalize_dataframe(df, "akshare")
    
    def test_normalize_dataframe_missing_columns(self):
        """测试缺少必需列的DataFrame"""
        normalizer = DataNormalizer()
        
        # 缺少volume列
        df = pd.DataFrame({
            '日期': ['2024-01-01'],
            '开盘': [10.0],
            '最高': [10.5],
            '最低': [9.5],
            '收盘': [10.2]
        })
        
        with pytest.raises(DataFormatError, match="Missing required columns"):
            normalizer.normalize_dataframe(df, "akshare")


class TestGuojinAdapter:
    """测试国金适配器"""
    
    def test_discover_interfaces(self):
        """测试接口发现"""
        adapter = GuojinAdapter()
        interfaces = adapter.discover_interfaces()
        
        # 验证发现了接口
        assert len(interfaces) > 0
        
        # 验证接口信息完整
        for interface in interfaces:
            assert interface.platform == "guojin"
            assert interface.interface_name
            assert isinstance(interface.asset_type, AssetType)
            assert interface.endpoint
            assert interface.supported_params
            assert 0 <= interface.quality_score <= 100
    
    def test_discover_interfaces_contains_stock(self):
        """测试发现的接口包含股票接口"""
        adapter = GuojinAdapter()
        interfaces = adapter.discover_interfaces()
        
        stock_interfaces = [i for i in interfaces if i.asset_type == AssetType.STOCK]
        assert len(stock_interfaces) > 0
    
    def test_download_data_success(self):
        """测试成功下载数据（允许重试）"""
        adapter = GuojinAdapter()
        
        # 尝试多次以应对随机失败
        max_attempts = 5
        success = False
        data = None
        
        for attempt in range(max_attempts):
            try:
                data = adapter.download_data(
                    interface="get_stock_daily",
                    symbol="000001.SZ",
                    start_date=date(2024, 1, 1),
                    end_date=date(2024, 1, 10)
                )
                success = True
                break
            except GuojinAPIError:
                # 模拟失败，重试
                continue
        
        # 至少有一次应该成功
        assert success, f"Failed after {max_attempts} attempts"
        
        # 验证返回DataFrame
        assert isinstance(data, pd.DataFrame)
        assert len(data) > 0
        
        # 验证包含必需列
        assert 'date' in data.columns
        assert 'open' in data.columns
        assert 'close' in data.columns
    
    def test_test_interface(self):
        """测试接口测试功能"""
        adapter = GuojinAdapter()
        
        result = adapter.test_interface("get_stock_daily")
        
        # 验证测试结果
        assert isinstance(result, InterfaceTestResult)
        assert result.interface == "get_stock_daily"
        
        if result.success:
            assert result.latency_ms > 0
            assert 0 <= result.coverage <= 1.0
            assert result.rows_returned >= 0
        else:
            assert result.error is not None


class TestAkshareAdapter:
    """测试Akshare适配器"""
    
    def test_discover_interfaces(self):
        """测试接口发现"""
        adapter = AkshareAdapter()
        interfaces = adapter.discover_interfaces()
        
        # 验证发现了接口
        assert len(interfaces) > 0
        
        # 验证接口信息完整
        for interface in interfaces:
            assert interface.platform == "akshare"
            assert interface.interface_name
            assert isinstance(interface.asset_type, AssetType)
            assert interface.endpoint
            assert interface.supported_params
            assert 0 <= interface.quality_score <= 100
    
    def test_discover_interfaces_contains_stock(self):
        """测试发现的接口包含股票接口"""
        adapter = AkshareAdapter()
        interfaces = adapter.discover_interfaces()
        
        stock_interfaces = [i for i in interfaces if i.asset_type == AssetType.STOCK]
        assert len(stock_interfaces) > 0
    
    def test_download_data_success(self):
        """测试成功下载数据（允许重试）"""
        adapter = AkshareAdapter()
        
        # 尝试多次以应对随机失败
        max_attempts = 5
        success = False
        data = None
        
        for attempt in range(max_attempts):
            try:
                data = adapter.download_data(
                    interface="stock_zh_a_hist",
                    symbol="000001",
                    start_date=date(2024, 1, 1),
                    end_date=date(2024, 1, 10)
                )
                success = True
                break
            except AkshareError:
                # 模拟失败，重试
                continue
        
        # 至少有一次应该成功
        assert success, f"Failed after {max_attempts} attempts"
        
        # 验证返回DataFrame
        assert isinstance(data, pd.DataFrame)
        assert len(data) > 0
        
        # 验证包含必需列（Akshare使用中文列名）
        assert '日期' in data.columns or 'date' in data.columns
    
    def test_test_interface(self):
        """测试接口测试功能"""
        adapter = AkshareAdapter()
        
        result = adapter.test_interface("stock_zh_a_hist")
        
        # 验证测试结果
        assert isinstance(result, InterfaceTestResult)
        assert result.interface == "stock_zh_a_hist"
        
        if result.success:
            assert result.latency_ms > 0
            assert 0 <= result.coverage <= 1.0
            assert result.rows_returned >= 0
        else:
            assert result.error is not None


class TestBridgeConfig:
    """测试桥接器配置"""
    
    def test_valid_config(self):
        """测试有效配置"""
        config = BridgeConfig(
            platforms=["guojin", "akshare"],
            default_platform="guojin"
        )
        
        assert config.platforms == ["guojin", "akshare"]
        assert config.default_platform == "guojin"
        assert config.timeout_seconds == 30
    
    def test_custom_timeout(self):
        """测试自定义超时"""
        config = BridgeConfig(
            platforms=["guojin"],
            timeout_seconds=60
        )
        
        assert config.timeout_seconds == 60


class TestHistoricalBridge:
    """测试历史桥接器"""
    
    def test_initialization_valid_config(self):
        """测试有效配置初始化"""
        config = BridgeConfig(
            platforms=["guojin", "akshare"],
            default_platform="guojin"
        )
        
        bridge = HistoricalBridge(config)
        
        assert bridge.config == config
        assert len(bridge.adapters) == 2
        assert "guojin" in bridge.adapters
        assert "akshare" in bridge.adapters
        assert isinstance(bridge.normalizer, DataNormalizer)
    
    def test_initialization_empty_platforms(self):
        """测试空平台列表"""
        config = BridgeConfig(platforms=[])
        
        with pytest.raises(ConfigurationError, match="At least one platform"):
            HistoricalBridge(config)
    
    def test_initialization_invalid_default(self):
        """测试无效的默认平台"""
        config = BridgeConfig(
            platforms=["guojin"],
            default_platform="invalid"
        )
        
        with pytest.raises(ConfigurationError, match="Default platform"):
            HistoricalBridge(config)
    
    def test_get_data_success(self):
        """测试成功获取数据"""
        config = BridgeConfig(platforms=["guojin"])
        bridge = HistoricalBridge(config)
        
        data = bridge.get_data(
            symbol="000001.SZ",
            asset_type=AssetType.STOCK,
            platform="guojin",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 10)
        )
        
        # 验证返回标准化的DataFrame
        assert isinstance(data, pd.DataFrame)
        assert len(data) > 0
        
        # 验证标准列名
        assert list(data.columns) == ['open', 'high', 'low', 'close', 'volume']
        
        # 验证索引是日期
        assert isinstance(data.index, pd.DatetimeIndex)
    
    def test_get_data_platform_not_configured(self):
        """测试未配置的平台"""
        config = BridgeConfig(platforms=["guojin"])
        bridge = HistoricalBridge(config)
        
        with pytest.raises(ConfigurationError, match="not configured"):
            bridge.get_data(
                symbol="000001.SZ",
                asset_type=AssetType.STOCK,
                platform="invalid",
                start_date=date(2024, 1, 1),
                end_date=date(2024, 1, 10)
            )
    
    def test_get_data_symbol_normalization(self):
        """测试标的代码自动标准化"""
        config = BridgeConfig(platforms=["akshare"], default_platform="akshare")
        bridge = HistoricalBridge(config)
        
        # 使用Akshare格式的代码（6位）
        data = bridge.get_data(
            symbol="000001",
            asset_type=AssetType.STOCK,
            platform="akshare",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 10)
        )
        
        # 应该成功返回数据
        assert isinstance(data, pd.DataFrame)
        assert len(data) > 0
    
    def test_normalize_symbol(self):
        """测试标的代码标准化"""
        config = BridgeConfig(platforms=["guojin"])
        bridge = HistoricalBridge(config)
        
        result = bridge.normalize_symbol("000001", "akshare")
        assert result == "000001.SZ"
    
    def test_get_available_platforms(self):
        """测试获取可用平台列表"""
        config = BridgeConfig(platforms=["guojin", "akshare"])
        bridge = HistoricalBridge(config)
        
        platforms = bridge.get_available_platforms()
        
        assert len(platforms) == 2
        assert "guojin" in platforms
        assert "akshare" in platforms
    
    def test_test_platform_success(self):
        """测试平台测试功能"""
        config = BridgeConfig(platforms=["guojin"])
        bridge = HistoricalBridge(config)
        
        results = bridge.test_platform("guojin")
        
        # 验证返回测试结果
        assert isinstance(results, dict)
        assert len(results) > 0
        
        # 验证每个结果
        for interface_name, result in results.items():
            assert isinstance(result, InterfaceTestResult)
            assert result.interface == interface_name
    
    def test_test_platform_not_configured(self):
        """测试未配置平台的测试"""
        config = BridgeConfig(platforms=["guojin"])
        bridge = HistoricalBridge(config)
        
        with pytest.raises(ConfigurationError, match="not configured"):
            bridge.test_platform("invalid")
    
    def test_select_interface_best_quality(self):
        """测试选择最佳质量接口"""
        config = BridgeConfig(platforms=["guojin"])
        bridge = HistoricalBridge(config)
        
        adapter = bridge.adapters["guojin"]
        interface = bridge._select_interface(adapter, AssetType.STOCK)
        
        # 应该返回一个接口名称
        assert isinstance(interface, str)
        assert len(interface) > 0
    
    def test_select_interface_no_matching(self):
        """测试没有匹配的接口"""
        config = BridgeConfig(platforms=["guojin"])
        bridge = HistoricalBridge(config)
        
        # 创建一个mock适配器，返回空接口列表
        mock_adapter = Mock(spec=GuojinAdapter)
        mock_adapter.discover_interfaces.return_value = []
        
        with pytest.raises(ConfigurationError, match="No interface found"):
            bridge._select_interface(mock_adapter, AssetType.STOCK)
    
    def test_get_data_multiple_platforms(self):
        """测试多平台数据获取"""
        config = BridgeConfig(platforms=["guojin", "akshare"])
        bridge = HistoricalBridge(config)
        
        # 尝试从两个平台获取数据（允许随机失败）
        successful_platforms = []
        data_results = []
        
        for platform, symbol in [("guojin", "000001.SZ"), ("akshare", "000001")]:
            try:
                data = bridge.get_data(
                    symbol=symbol,
                    asset_type=AssetType.STOCK,
                    platform=platform,
                    start_date=date(2024, 1, 1),
                    end_date=date(2024, 1, 10)
                )
                successful_platforms.append(platform)
                data_results.append(data)
            except (GuojinAPIError, AkshareError):
                # 模拟失败，继续
                continue
        
        # 至少有一个平台应该成功
        assert len(successful_platforms) > 0, "All platforms failed"
        
        # 所有成功的数据都应该是标准化的
        for data in data_results:
            assert isinstance(data, pd.DataFrame)
            assert list(data.columns) == ['open', 'high', 'low', 'close', 'volume']


class TestIntegration:
    """集成测试"""
    
    def test_end_to_end_data_retrieval(self):
        """测试端到端数据获取流程"""
        # 1. 创建配置
        config = BridgeConfig(
            platforms=["guojin", "akshare"],
            default_platform="guojin"
        )
        
        # 2. 初始化桥接器
        bridge = HistoricalBridge(config)
        
        # 3. 获取数据
        data = bridge.get_data(
            symbol="000001.SZ",
            asset_type=AssetType.STOCK,
            platform="guojin",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31)
        )
        
        # 4. 验证数据质量
        assert isinstance(data, pd.DataFrame)
        assert len(data) > 0
        assert list(data.columns) == ['open', 'high', 'low', 'close', 'volume']
        assert isinstance(data.index, pd.DatetimeIndex)
        
        # 5. 验证数据完整性
        assert data['open'].notna().all()
        assert data['close'].notna().all()
        assert data['volume'].notna().all()
    
    def test_platform_failover_simulation(self):
        """测试平台故障转移模拟"""
        config = BridgeConfig(platforms=["guojin", "akshare"])
        bridge = HistoricalBridge(config)
        
        # 尝试从两个平台获取数据
        platforms_tested = []
        
        for platform in ["guojin", "akshare"]:
            try:
                data = bridge.get_data(
                    symbol="000001.SZ" if platform == "guojin" else "000001",
                    asset_type=AssetType.STOCK,
                    platform=platform,
                    start_date=date(2024, 1, 1),
                    end_date=date(2024, 1, 10)
                )
                platforms_tested.append(platform)
            except PlatformError:
                # 平台失败，继续尝试下一个
                continue
        
        # 至少有一个平台应该成功
        assert len(platforms_tested) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
