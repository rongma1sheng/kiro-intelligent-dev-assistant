"""
数据归档器单元测试

白皮书依据: 第一章 1.5.3 诊疗态任务调度
测试范围: DataArchiver的Tick/Bar/雷达信号归档功能
"""

import os
import pytest
import tempfile
import shutil
from datetime import date
from pathlib import Path
from unittest.mock import patch, MagicMock

# 尝试导入pandas和pyarrow
try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False

try:
    import pyarrow
    HAS_PARQUET = True
except ImportError:
    HAS_PARQUET = False

from src.infra.data_archiver import (
    DataArchiver,
    ArchiveConfig,
    ArchiveResult
)


class TestArchiveConfig:
    """ArchiveConfig配置类测试"""
    
    def test_default_config(self):
        """测试默认配置"""
        config = ArchiveConfig()
        
        assert config.base_path == "data"
        assert config.tick_subdir == "tick"
        assert config.bar_subdir == "bar"
        assert config.radar_subdir == "radar_archive"
        assert config.compression == "snappy"
        assert config.partition_by_date is True
    
    def test_custom_config(self):
        """测试自定义配置"""
        config = ArchiveConfig(
            base_path="/custom/path",
            tick_subdir="ticks",
            bar_subdir="bars",
            radar_subdir="radar",
            compression="gzip",
            partition_by_date=False
        )
        
        assert config.base_path == "/custom/path"
        assert config.tick_subdir == "ticks"
        assert config.bar_subdir == "bars"
        assert config.radar_subdir == "radar"
        assert config.compression == "gzip"
        assert config.partition_by_date is False


class TestArchiveResult:
    """ArchiveResult结果类测试"""
    
    def test_success_result(self):
        """测试成功结果"""
        result = ArchiveResult(
            success=True,
            file_path="/data/tick/000001_20260127.parquet",
            record_count=1000,
            file_size=10240,
            duration=0.5
        )
        
        assert result.success is True
        assert result.file_path == "/data/tick/000001_20260127.parquet"
        assert result.record_count == 1000
        assert result.file_size == 10240
        assert result.duration == 0.5
        assert result.error == ""
    
    def test_failure_result(self):
        """测试失败结果"""
        result = ArchiveResult(
            success=False,
            error="文件写入失败"
        )
        
        assert result.success is False
        assert result.error == "文件写入失败"
        assert result.record_count == 0
    
    def test_to_dict(self):
        """测试转换为字典"""
        result = ArchiveResult(
            success=True,
            file_path="/data/test.parquet",
            record_count=100,
            file_size=1024,
            duration=0.1
        )
        
        result_dict = result.to_dict()
        
        assert result_dict["success"] is True
        assert result_dict["file_path"] == "/data/test.parquet"
        assert result_dict["record_count"] == 100
        assert result_dict["file_size"] == 1024
        assert result_dict["duration"] == 0.1
        assert result_dict["error"] == ""


class TestDataArchiver:
    """DataArchiver归档器测试"""
    
    @pytest.fixture
    def temp_dir(self):
        """创建临时目录"""
        temp_path = tempfile.mkdtemp()
        yield temp_path
        # 清理
        if os.path.exists(temp_path):
            shutil.rmtree(temp_path)
    
    @pytest.fixture
    def archiver(self, temp_dir):
        """创建归档器实例"""
        config = ArchiveConfig(base_path=temp_dir)
        return DataArchiver(config=config)
    
    def test_init_default(self, temp_dir):
        """测试默认初始化"""
        config = ArchiveConfig(base_path=temp_dir)
        archiver = DataArchiver(config=config)
        
        assert archiver.config.base_path == temp_dir
        assert archiver.archive_date == date.today()
    
    def test_init_creates_directories(self, temp_dir):
        """测试初始化创建目录"""
        config = ArchiveConfig(base_path=temp_dir)
        archiver = DataArchiver(config=config)
        
        # 检查目录是否创建
        assert (Path(temp_dir) / "tick").exists()
        assert (Path(temp_dir) / "bar").exists()
        assert (Path(temp_dir) / "radar_archive").exists()
    
    def test_get_archive_path_with_date_partition(self, archiver):
        """测试带日期分区的归档路径"""
        path = archiver._get_archive_path("tick", "000001.SZ")
        
        date_str = date.today().strftime("%Y%m%d")
        expected_filename = f"000001.SZ_{date_str}.parquet"
        
        assert path.name == expected_filename
        assert "tick" in str(path)
    
    def test_get_archive_path_without_symbol(self, archiver):
        """测试无标的代码的归档路径"""
        path = archiver._get_archive_path("radar")
        
        date_str = date.today().strftime("%Y%m%d")
        expected_filename = f"radar_{date_str}.parquet"
        
        assert path.name == expected_filename
    
    def test_get_archive_path_no_date_partition(self, temp_dir):
        """测试无日期分区的归档路径"""
        config = ArchiveConfig(base_path=temp_dir, partition_by_date=False)
        archiver = DataArchiver(config=config)
        
        path = archiver._get_archive_path("tick", "000001.SZ")
        
        assert path.name == "000001.SZ.parquet"
    
    @pytest.mark.skipif(not HAS_PANDAS or not HAS_PARQUET, reason="需要pandas和pyarrow")
    def test_archive_tick_data_dataframe(self, archiver):
        """测试归档Tick数据(DataFrame)"""
        # 创建测试数据
        df = pd.DataFrame({
            "symbol": ["000001.SZ"] * 10,
            "price": [10.0 + i * 0.01 for i in range(10)],
            "volume": [100 * (i + 1) for i in range(10)]
        })
        
        result = archiver.archive_tick_data(df, "000001.SZ")
        
        assert result.success is True
        assert result.record_count == 10
        assert result.file_size > 0
        assert result.duration >= 0
        assert Path(result.file_path).exists()
    
    @pytest.mark.skipif(not HAS_PANDAS or not HAS_PARQUET, reason="需要pandas和pyarrow")
    def test_archive_tick_data_list(self, archiver):
        """测试归档Tick数据(列表)"""
        data = [
            {"symbol": "000001.SZ", "price": 10.0, "volume": 100},
            {"symbol": "000001.SZ", "price": 10.01, "volume": 200}
        ]
        
        result = archiver.archive_tick_data(data, "000001.SZ")
        
        assert result.success is True
        assert result.record_count == 2
    
    @pytest.mark.skipif(not HAS_PANDAS or not HAS_PARQUET, reason="需要pandas和pyarrow")
    def test_archive_tick_data_empty(self, archiver):
        """测试归档空数据"""
        df = pd.DataFrame()
        
        result = archiver.archive_tick_data(df)
        
        assert result.success is True
        assert result.record_count == 0
    
    def test_archive_tick_data_invalid_type(self, archiver):
        """测试归档无效数据类型"""
        result = archiver.archive_tick_data("invalid_data")
        
        assert result.success is False
        assert "不支持的数据类型" in result.error
    
    @pytest.mark.skipif(not HAS_PANDAS or not HAS_PARQUET, reason="需要pandas和pyarrow")
    def test_archive_bar_data(self, archiver):
        """测试归档Bar数据"""
        df = pd.DataFrame({
            "symbol": ["000001.SZ"] * 5,
            "open": [10.0, 10.1, 10.2, 10.3, 10.4],
            "high": [10.1, 10.2, 10.3, 10.4, 10.5],
            "low": [9.9, 10.0, 10.1, 10.2, 10.3],
            "close": [10.05, 10.15, 10.25, 10.35, 10.45],
            "volume": [1000, 2000, 3000, 4000, 5000]
        })
        
        result = archiver.archive_bar_data(df, "000001.SZ", "1m")
        
        assert result.success is True
        assert result.record_count == 5
        assert Path(result.file_path).exists()
    
    @pytest.mark.skipif(not HAS_PANDAS or not HAS_PARQUET, reason="需要pandas和pyarrow")
    def test_archive_radar_signals_list(self, archiver):
        """测试归档雷达信号(列表)"""
        signals = [
            {"signal_type": "buy", "symbol": "000001.SZ", "strength": 0.8},
            {"signal_type": "sell", "symbol": "600000.SH", "strength": 0.6}
        ]
        
        result = archiver.archive_radar_signals(signals)
        
        assert result.success is True
        assert result.record_count == 2
    
    @pytest.mark.skipif(not HAS_PANDAS or not HAS_PARQUET, reason="需要pandas和pyarrow")
    def test_archive_radar_signals_dict(self, archiver):
        """测试归档雷达信号(单个字典)"""
        signal = {"signal_type": "buy", "symbol": "000001.SZ", "strength": 0.8}
        
        result = archiver.archive_radar_signals(signal)
        
        assert result.success is True
        assert result.record_count == 1
    
    @pytest.mark.skipif(not HAS_PANDAS or not HAS_PARQUET, reason="需要pandas和pyarrow")
    def test_archive_all(self, archiver):
        """测试归档所有数据"""
        tick_df = pd.DataFrame({
            "symbol": ["000001.SZ"] * 5,
            "price": [10.0 + i * 0.01 for i in range(5)],
            "volume": [100 * (i + 1) for i in range(5)]
        })
        
        bar_df = pd.DataFrame({
            "symbol": ["000001.SZ"] * 3,
            "open": [10.0, 10.1, 10.2],
            "close": [10.05, 10.15, 10.25],
            "volume": [1000, 2000, 3000]
        })
        
        radar_signals = [
            {"signal_type": "buy", "symbol": "000001.SZ"}
        ]
        
        results = archiver.archive_all(
            tick_data=tick_df,
            bar_data=bar_df,
            radar_signals=radar_signals
        )
        
        assert "tick" in results
        assert "bar" in results
        assert "radar" in results
        assert results["tick"].success is True
        assert results["bar"].success is True
        assert results["radar"].success is True
    
    @pytest.mark.skipif(not HAS_PANDAS or not HAS_PARQUET, reason="需要pandas和pyarrow")
    def test_get_archive_stats(self, archiver):
        """测试获取归档统计"""
        # 先归档一些数据
        df = pd.DataFrame({
            "symbol": ["000001.SZ"] * 5,
            "price": [10.0 + i * 0.01 for i in range(5)],
            "volume": [100 * (i + 1) for i in range(5)]
        })
        archiver.archive_tick_data(df, "000001.SZ")
        
        stats = archiver.get_archive_stats()
        
        assert "tick" in stats
        assert "bar" in stats
        assert "radar" in stats
        assert stats["tick"]["count"] >= 1
        assert stats["tick"]["size"] > 0


class TestDataArchiverWithoutParquet:
    """无pyarrow环境测试"""
    
    @pytest.fixture
    def temp_dir(self):
        """创建临时目录"""
        temp_path = tempfile.mkdtemp()
        yield temp_path
        if os.path.exists(temp_path):
            shutil.rmtree(temp_path)
    
    def test_archive_without_parquet(self, temp_dir):
        """测试无pyarrow时的归档"""
        config = ArchiveConfig(base_path=temp_dir)
        
        # 模拟pyarrow未安装
        with patch('src.infra.data_archiver.HAS_PARQUET', False):
            archiver = DataArchiver(config=config)
            result = archiver.archive_tick_data([{"price": 10.0}])
            
            assert result.success is False
            assert "pyarrow未安装" in result.error


class TestDataArchiverEdgeCases:
    """边界条件测试"""
    
    @pytest.fixture
    def temp_dir(self):
        """创建临时目录"""
        temp_path = tempfile.mkdtemp()
        yield temp_path
        if os.path.exists(temp_path):
            shutil.rmtree(temp_path)
    
    @pytest.fixture
    def archiver(self, temp_dir):
        """创建归档器实例"""
        config = ArchiveConfig(base_path=temp_dir)
        return DataArchiver(config=config)
    
    @pytest.mark.skipif(not HAS_PANDAS or not HAS_PARQUET, reason="需要pandas和pyarrow")
    def test_archive_large_dataset(self, archiver):
        """测试归档大数据集"""
        # 创建10000条记录
        df = pd.DataFrame({
            "symbol": ["000001.SZ"] * 10000,
            "price": [10.0 + i * 0.0001 for i in range(10000)],
            "volume": [100 * (i % 100 + 1) for i in range(10000)]
        })
        
        result = archiver.archive_tick_data(df, "000001.SZ")
        
        assert result.success is True
        assert result.record_count == 10000
    
    @pytest.mark.skipif(not HAS_PANDAS or not HAS_PARQUET, reason="需要pandas和pyarrow")
    def test_archive_special_characters_in_symbol(self, archiver):
        """测试标的代码包含特殊字符"""
        df = pd.DataFrame({
            "symbol": ["000001.SZ"] * 5,
            "price": [10.0] * 5
        })
        
        result = archiver.archive_tick_data(df, "000001.SZ")
        
        assert result.success is True
    
    @pytest.mark.skipif(not HAS_PANDAS or not HAS_PARQUET, reason="需要pandas和pyarrow")
    def test_archive_with_nan_values(self, archiver):
        """测试包含NaN值的数据"""
        import numpy as np
        
        df = pd.DataFrame({
            "symbol": ["000001.SZ"] * 5,
            "price": [10.0, np.nan, 10.2, np.nan, 10.4],
            "volume": [100, 200, np.nan, 400, 500]
        })
        
        result = archiver.archive_tick_data(df, "000001.SZ")
        
        assert result.success is True
        assert result.record_count == 5
    
    def test_archive_none_data(self, archiver):
        """测试归档None数据"""
        results = archiver.archive_all(
            tick_data=None,
            bar_data=None,
            radar_signals=None
        )
        
        # 应该返回空字典
        assert results == {}
