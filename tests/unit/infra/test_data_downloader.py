"""数据下载器单元测试

白皮书依据: 第三章 3.3.1 数据探针自适应工作流程 - 阶段2

测试覆盖:
- 探针日志加载
- 数据下载
- 降级和重试机制
- 下载日志保存
"""

import pytest
import json
from datetime import date
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import pandas as pd
from src.infra.data_downloader import DataDownloader
from src.infra.bridge import AssetType, BridgeConfig


class TestDataDownloader:
    """数据下载器测试"""
    
    @pytest.fixture
    def temp_probe_log(self, tmp_path):
        """临时探针日志文件"""
        log_file = tmp_path / "test_probe.json"
        return str(log_file)
    
    @pytest.fixture
    def temp_download_log(self, tmp_path):
        """临时下载日志文件"""
        log_file = tmp_path / "test_download.log"
        return str(log_file)
    
    @pytest.fixture
    def sample_probe_log(self):
        """示例探针日志"""
        return {
            "total_interfaces": 2,
            "discoveries": {
                "stock": {
                    "recommended": {
                        "primary": "guojin.get_stock_daily",
                        "backup": "akshare.stock_zh_a_hist"
                    }
                }
            }
        }
    
    @pytest.fixture
    def downloader(self):
        """创建下载器实例"""
        config = BridgeConfig(
            platforms=["guojin", "akshare"],
            default_platform="guojin"
        )
        return DataDownloader(bridge_config=config)
    
    def test_initialization(self, downloader):
        """测试初始化"""
        assert downloader.bridge is not None
        assert downloader.probe_log is None
        assert downloader.download_results == []
    
    def test_initialization_default_config(self):
        """测试默认配置初始化"""
        downloader = DataDownloader()
        
        assert downloader.bridge is not None
        assert downloader.probe_log is None
    
    def test_load_probe_log_success(self, downloader, temp_probe_log, sample_probe_log):
        """测试加载探针日志成功"""
        with open(temp_probe_log, 'w', encoding='utf-8') as f:
            json.dump(sample_probe_log, f)
        
        downloader.load_probe_log(temp_probe_log)
        
        assert downloader.probe_log is not None
        assert downloader.probe_log["total_interfaces"] == 2
    
    def test_load_probe_log_file_not_found(self, downloader):
        """测试加载不存在的探针日志"""
        with pytest.raises(FileNotFoundError):
            downloader.load_probe_log("nonexistent.json")
    
    def test_load_probe_log_invalid_json(self, downloader, temp_probe_log):
        """测试加载无效的JSON文件"""
        with open(temp_probe_log, 'w', encoding='utf-8') as f:
            f.write("invalid json")
        
        with pytest.raises(Exception):
            downloader.load_probe_log(temp_probe_log)
    
    def test_download_all_symbols_without_probe_log(self, downloader):
        """测试未加载探针日志时下载"""
        with pytest.raises(ValueError, match="探针日志未加载"):
            downloader.download_all_symbols(
                symbols=["000001.SZ"],
                start_date=date(2024, 1, 1),
                end_date=date(2024, 1, 31)
            )
    
    def test_download_all_symbols_success(self, downloader, sample_probe_log):
        """测试下载所有标的成功"""
        downloader.probe_log = sample_probe_log
        
        # Mock桥接器的get_data方法
        mock_data = pd.DataFrame({
            'date': pd.date_range('2024-01-01', periods=10),
            'close': [100.0] * 10
        })
        
        with patch.object(downloader.bridge, 'get_data', return_value=mock_data):
            result = downloader.download_all_symbols(
                symbols=["000001.SZ", "000002.SZ"],
                start_date=date(2024, 1, 1),
                end_date=date(2024, 1, 10),
                asset_type=AssetType.STOCK
            )
        
        assert result["summary"]["total_symbols"] == 2
        assert result["summary"]["success"] == 2
        assert result["summary"]["failed"] == 0
        assert len(result["downloads"]) == 2
    
    def test_download_all_symbols_partial_failure(self, downloader, sample_probe_log):
        """测试部分下载失败"""
        downloader.probe_log = sample_probe_log
        
        # Mock桥接器：第一个成功，第二个失败
        mock_data = pd.DataFrame({
            'date': pd.date_range('2024-01-01', periods=10),
            'close': [100.0] * 10
        })
        
        def mock_get_data(symbol, **kwargs):
            if symbol == "000001.SZ":
                return mock_data
            else:
                raise Exception("Download failed")
        
        with patch.object(downloader.bridge, 'get_data', side_effect=mock_get_data):
            result = downloader.download_all_symbols(
                symbols=["000001.SZ", "000002.SZ"],
                start_date=date(2024, 1, 1),
                end_date=date(2024, 1, 10)
            )
        
        assert result["summary"]["total_symbols"] == 2
        assert result["summary"]["success"] == 1
        assert result["summary"]["failed"] == 1
    
    def test_download_single_symbol_success(self, downloader, sample_probe_log):
        """测试下载单个标的成功"""
        downloader.probe_log = sample_probe_log
        
        mock_data = pd.DataFrame({
            'date': pd.date_range('2024-01-01', periods=10),
            'close': [100.0] * 10
        })
        
        with patch.object(downloader.bridge, 'get_data', return_value=mock_data):
            result = downloader._download_single_symbol(
                symbol="000001.SZ",
                start_date=date(2024, 1, 1),
                end_date=date(2024, 1, 10),
                asset_type=AssetType.STOCK
            )
        
        assert result["status"] == "SUCCESS"
        assert result["symbol"] == "000001.SZ"
        assert result["rows_downloaded"] == 10
        assert result["retry_count"] == 0
        assert result["fallback_used"] is False
    
    def test_download_single_symbol_with_retry(self, downloader, sample_probe_log):
        """测试下载失败后重试"""
        downloader.probe_log = sample_probe_log
        
        mock_data = pd.DataFrame({
            'date': pd.date_range('2024-01-01', periods=10),
            'close': [100.0] * 10
        })
        
        # 前两次失败，第三次成功
        call_count = [0]
        
        def mock_get_data(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] < 3:
                raise Exception("Temporary failure")
            return mock_data
        
        with patch.object(downloader.bridge, 'get_data', side_effect=mock_get_data):
            with patch('time.sleep'):  # 跳过等待时间
                result = downloader._download_single_symbol(
                    symbol="000001.SZ",
                    start_date=date(2024, 1, 1),
                    end_date=date(2024, 1, 10),
                    asset_type=AssetType.STOCK,
                    max_retries=3
                )
        
        assert result["status"] == "SUCCESS"
        assert result["retry_count"] == 2  # 重试了2次
    
    def test_download_single_symbol_fallback(self, downloader, sample_probe_log):
        """测试降级到备用平台"""
        downloader.probe_log = sample_probe_log
        
        mock_data = pd.DataFrame({
            'date': pd.date_range('2024-01-01', periods=10),
            'close': [100.0] * 10
        })
        
        # PRIMARY失败，BACKUP成功
        call_count = [0]
        
        def mock_get_data(symbol, platform, **kwargs):
            call_count[0] += 1
            if platform == "guojin":
                raise Exception("Primary failed")
            return mock_data
        
        with patch.object(downloader.bridge, 'get_data', side_effect=mock_get_data):
            with patch('time.sleep'):
                result = downloader._download_single_symbol(
                    symbol="000001.SZ",
                    start_date=date(2024, 1, 1),
                    end_date=date(2024, 1, 10),
                    asset_type=AssetType.STOCK,
                    max_retries=3
                )
        
        assert result["status"] == "SUCCESS"
        assert result["fallback_used"] is True
        assert result["fallback_to"] == "akshare"
    
    def test_download_single_symbol_all_failed(self, downloader, sample_probe_log):
        """测试PRIMARY和BACKUP都失败"""
        downloader.probe_log = sample_probe_log
        
        with patch.object(downloader.bridge, 'get_data', side_effect=Exception("All failed")):
            with patch('time.sleep'):
                result = downloader._download_single_symbol(
                    symbol="000001.SZ",
                    start_date=date(2024, 1, 1),
                    end_date=date(2024, 1, 10),
                    asset_type=AssetType.STOCK,
                    max_retries=3
                )
        
        assert result["status"] == "FAILED"
        assert "All failed" in result["error"] or "PRIMARY和BACKUP都失败" in result["error"]
    
    def test_get_primary_platform(self, downloader, sample_probe_log):
        """测试获取PRIMARY平台"""
        downloader.probe_log = sample_probe_log
        
        platform = downloader._get_primary_platform(AssetType.STOCK)
        
        assert platform == "guojin"
    
    def test_get_primary_platform_no_probe_log(self, downloader):
        """测试未加载探针日志时获取PRIMARY平台"""
        platform = downloader._get_primary_platform(AssetType.STOCK)
        
        # 应该返回默认值
        assert platform == "guojin"
    
    def test_get_backup_platform(self, downloader, sample_probe_log):
        """测试获取BACKUP平台"""
        downloader.probe_log = sample_probe_log
        
        platform = downloader._get_backup_platform(AssetType.STOCK)
        
        assert platform == "akshare"
    
    def test_get_backup_platform_no_probe_log(self, downloader):
        """测试未加载探针日志时获取BACKUP平台"""
        platform = downloader._get_backup_platform(AssetType.STOCK)
        
        # 应该返回默认值
        assert platform == "akshare"
    
    def test_save_download_log_success(self, downloader, temp_download_log):
        """测试保存下载日志成功"""
        # 模拟下载结果
        downloader.download_results = [
            {
                "symbol": "000001.SZ",
                "status": "SUCCESS",
                "rows_downloaded": 100
            },
            {
                "symbol": "000002.SZ",
                "status": "FAILED",
                "error": "Download failed"
            }
        ]
        
        downloader.save_download_log(temp_download_log)
        
        # 验证文件已创建
        assert Path(temp_download_log).exists()
        
        # 验证文件内容
        with open(temp_download_log, 'r', encoding='utf-8') as f:
            log_data = json.load(f)
        
        assert log_data["summary"]["total_symbols"] == 2
        assert log_data["summary"]["success"] == 1
        assert log_data["summary"]["failed"] == 1
        assert len(log_data["downloads"]) == 2
    
    def test_save_download_log_no_results(self, downloader, temp_download_log):
        """测试没有下载结果时保存日志"""
        with pytest.raises(ValueError, match="没有下载结果"):
            downloader.save_download_log(temp_download_log)
    
    def test_save_download_log_invalid_path(self, downloader):
        """测试保存到无效路径"""
        downloader.download_results = [
            {"symbol": "000001.SZ", "status": "SUCCESS"}
        ]
        
        # 使用一个无法创建的路径(模拟文件系统错误)
        with patch('builtins.open', side_effect=PermissionError("Permission denied")):
            with pytest.raises(IOError, match="无法保存下载日志"):
                downloader.save_download_log("/some/path/download.log")


class TestDataDownloaderIntegration:
    """数据下载器集成测试"""
    
    @pytest.fixture
    def temp_dir(self, tmp_path):
        """临时目录"""
        return tmp_path
    
    @pytest.fixture
    def downloader(self):
        """创建下载器实例"""
        return DataDownloader()
    
    def test_full_workflow(self, downloader, temp_dir):
        """测试完整工作流"""
        # 1. 创建探针日志
        probe_log_path = temp_dir / "probe.json"
        probe_log = {
            "total_interfaces": 2,
            "discoveries": {
                "stock": {
                    "recommended": {
                        "primary": "guojin.get_stock_daily",
                        "backup": "akshare.stock_zh_a_hist"
                    }
                }
            }
        }
        
        with open(probe_log_path, 'w', encoding='utf-8') as f:
            json.dump(probe_log, f)
        
        # 2. 加载探针日志
        downloader.load_probe_log(str(probe_log_path))
        
        # 3. Mock数据下载
        mock_data = pd.DataFrame({
            'date': pd.date_range('2024-01-01', periods=10),
            'close': [100.0] * 10
        })
        
        with patch.object(downloader.bridge, 'get_data', return_value=mock_data):
            # 4. 下载数据
            result = downloader.download_all_symbols(
                symbols=["000001.SZ", "000002.SZ"],
                start_date=date(2024, 1, 1),
                end_date=date(2024, 1, 10)
            )
        
        # 5. 验证下载结果
        assert result["summary"]["success"] == 2
        assert result["summary"]["failed"] == 0
        
        # 6. 保存下载日志
        download_log_path = temp_dir / "download.log"
        downloader.save_download_log(str(download_log_path))
        
        # 7. 验证日志文件
        assert download_log_path.exists()
        
        with open(download_log_path, 'r', encoding='utf-8') as f:
            log_data = json.load(f)
        
        assert log_data["summary"]["total_symbols"] == 2
        assert log_data["summary"]["success"] == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
