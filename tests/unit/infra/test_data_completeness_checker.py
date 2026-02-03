"""数据完整性检查器单元测试

白皮书依据: 第三章 3.3.1 数据探针自适应工作流程 - 阶段4

测试覆盖:
- 数据完整性检查
- 缺失交易日识别
- 数据补齐流程
- 下载日志管理
"""

import pytest
import json
from datetime import date, datetime, time, timedelta
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from src.infra.data_completeness_checker import DataCompletenessChecker
from src.infra.bridge import AssetType


class TestDataCompletenessChecker:
    """数据完整性检查器测试"""
    
    @pytest.fixture
    def temp_log_file(self, tmp_path):
        """临时日志文件"""
        log_file = tmp_path / "test_download.log"
        return str(log_file)
    
    @pytest.fixture
    def checker(self, temp_log_file):
        """创建检查器实例"""
        return DataCompletenessChecker(download_log_path=temp_log_file)
    
    @pytest.fixture
    def sample_download_log(self):
        """示例下载日志"""
        return {
            "download_timestamp": "2024-01-15 16:00:00",
            "trading_date": "2024-01-15",
            "downloads": [
                {
                    "symbol": "000001.SZ",
                    "status": "SUCCESS",
                    "rows_downloaded": 100
                }
            ],
            "summary": {
                "total_symbols": 1,
                "success": 1,
                "failed": 0
            }
        }
    
    def test_initialization(self, checker, temp_log_file):
        """测试初始化"""
        assert checker.downloader is not None
        assert checker.download_log_path == temp_log_file
    
    def test_check_before_mining_no_log(self, checker):
        """测试检查时日志不存在"""
        result = checker.check_before_mining(symbols=["000001.SZ"])
        
        assert result is False
    
    def test_check_before_mining_log_exists_up_to_date(self, checker, temp_log_file, sample_download_log):
        """测试检查时数据最新"""
        # 创建最新的下载日志
        today = date.today()
        sample_download_log["trading_date"] = today.strftime("%Y-%m-%d")
        
        with open(temp_log_file, 'w', encoding='utf-8') as f:
            json.dump(sample_download_log, f)
        
        with patch.object(checker, '_get_latest_trading_date', return_value=today):
            result = checker.check_before_mining(symbols=["000001.SZ"])
        
        assert result is True
    
    def test_check_before_mining_log_exists_outdated(self, checker, temp_log_file, sample_download_log):
        """测试检查时数据过期"""
        # 创建过期的下载日志
        old_date = date.today() - timedelta(days=5)
        sample_download_log["trading_date"] = old_date.strftime("%Y-%m-%d")
        
        with open(temp_log_file, 'w', encoding='utf-8') as f:
            json.dump(sample_download_log, f)
        
        with patch.object(checker, '_get_latest_trading_date', return_value=date.today()):
            result = checker.check_before_mining(symbols=["000001.SZ"])
        
        assert result is False
    
    def test_check_before_mining_no_trading_date(self, checker, temp_log_file):
        """测试日志中没有交易日期"""
        log_data = {"downloads": []}
        
        with open(temp_log_file, 'w', encoding='utf-8') as f:
            json.dump(log_data, f)
        
        result = checker.check_before_mining(symbols=["000001.SZ"])
        
        assert result is False
    
    def test_load_download_log_success(self, checker, temp_log_file, sample_download_log):
        """测试加载下载日志成功"""
        with open(temp_log_file, 'w', encoding='utf-8') as f:
            json.dump(sample_download_log, f)
        
        log = checker._load_download_log()
        
        assert log is not None
        assert log["trading_date"] == "2024-01-15"
        assert log["summary"]["success"] == 1
    
    def test_load_download_log_file_not_exists(self, checker):
        """测试加载不存在的日志文件"""
        log = checker._load_download_log()
        
        assert log is None
    
    def test_load_download_log_invalid_json(self, checker, temp_log_file):
        """测试加载无效的JSON文件"""
        with open(temp_log_file, 'w', encoding='utf-8') as f:
            f.write("invalid json")
        
        log = checker._load_download_log()
        
        assert log is None
    
    def test_get_latest_trading_date_before_16(self, checker):
        """测试获取最新交易日（16点前）"""
        # Mock当前时间为15:00
        mock_now = datetime(2024, 1, 15, 15, 0, 0)
        
        with patch('src.infra.data_completeness_checker.datetime') as mock_datetime:
            mock_datetime.now.return_value = mock_now
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
            
            latest_date = checker._get_latest_trading_date()
        
        # 应该返回前一天
        expected_date = date(2024, 1, 14)
        assert latest_date == expected_date
    
    def test_get_latest_trading_date_after_16(self, checker):
        """测试获取最新交易日（16点后）"""
        # Mock当前时间为17:00
        mock_now = datetime(2024, 1, 15, 17, 0, 0)
        
        with patch('src.infra.data_completeness_checker.datetime') as mock_datetime:
            mock_datetime.now.return_value = mock_now
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
            
            latest_date = checker._get_latest_trading_date()
        
        # 应该返回当天
        expected_date = date(2024, 1, 15)
        assert latest_date == expected_date
    
    def test_is_data_up_to_date_true(self, checker):
        """测试数据是最新的"""
        data_date = date(2024, 1, 15)
        latest_date = date(2024, 1, 15)
        
        result = checker._is_data_up_to_date(data_date, latest_date)
        
        assert result is True
    
    def test_is_data_up_to_date_false(self, checker):
        """测试数据过期"""
        data_date = date(2024, 1, 10)
        latest_date = date(2024, 1, 15)
        
        result = checker._is_data_up_to_date(data_date, latest_date)
        
        assert result is False
    
    def test_get_missing_trading_dates(self, checker):
        """测试获取缺失的交易日"""
        start_date = date(2024, 1, 10)  # 周三
        end_date = date(2024, 1, 15)    # 周一
        
        missing_dates = checker._get_missing_trading_dates(start_date, end_date)
        
        # 应该包含：1/11(周四), 1/12(周五), 1/15(周一)
        # 不包含：1/13(周六), 1/14(周日)
        assert len(missing_dates) == 3
        assert date(2024, 1, 11) in missing_dates
        assert date(2024, 1, 12) in missing_dates
        assert date(2024, 1, 15) in missing_dates
        assert date(2024, 1, 13) not in missing_dates  # 周六
        assert date(2024, 1, 14) not in missing_dates  # 周日
    
    def test_get_missing_trading_dates_same_day(self, checker):
        """测试同一天没有缺失"""
        start_date = date(2024, 1, 15)
        end_date = date(2024, 1, 15)
        
        missing_dates = checker._get_missing_trading_dates(start_date, end_date)
        
        assert len(missing_dates) == 0
    
    def test_fill_missing_data_no_log(self, checker):
        """测试补齐数据时日志不存在"""
        result = checker.fill_missing_data(symbols=["000001.SZ"])
        
        assert result is False
    
    def test_fill_missing_data_success(self, checker, temp_log_file, sample_download_log):
        """测试补齐数据成功"""
        # 创建过期的下载日志
        old_date = date.today() - timedelta(days=2)
        sample_download_log["trading_date"] = old_date.strftime("%Y-%m-%d")
        
        with open(temp_log_file, 'w', encoding='utf-8') as f:
            json.dump(sample_download_log, f)
        
        # Mock下载器方法
        mock_download_result = {
            "summary": {
                "success": 1,
                "failed": 0
            }
        }
        
        with patch.object(checker.downloader, 'load_probe_log'):
            with patch.object(checker.downloader, 'download_all_symbols', return_value=mock_download_result):
                with patch.object(checker.downloader, 'save_download_log'):
                    with patch.object(checker, '_get_latest_trading_date', return_value=date.today()):
                        result = checker.fill_missing_data(symbols=["000001.SZ"])
        
        assert result is True
    
    def test_fill_missing_data_no_missing_dates(self, checker, temp_log_file, sample_download_log):
        """测试没有缺失的交易日"""
        # 创建最新的下载日志
        today = date.today()
        sample_download_log["trading_date"] = today.strftime("%Y-%m-%d")
        
        with open(temp_log_file, 'w', encoding='utf-8') as f:
            json.dump(sample_download_log, f)
        
        with patch.object(checker, '_get_latest_trading_date', return_value=today):
            with patch.object(checker.downloader, 'load_probe_log'):
                result = checker.fill_missing_data(symbols=["000001.SZ"])
        
        assert result is True
    
    def test_fill_missing_data_download_failure(self, checker, temp_log_file, sample_download_log):
        """测试补齐数据时下载失败"""
        # 创建过期的下载日志
        old_date = date.today() - timedelta(days=2)
        sample_download_log["trading_date"] = old_date.strftime("%Y-%m-%d")
        
        with open(temp_log_file, 'w', encoding='utf-8') as f:
            json.dump(sample_download_log, f)
        
        # Mock下载器方法抛出异常，同时mock缺失日期
        missing_dates = [date.today() - timedelta(days=1)]
        with patch.object(checker.downloader, 'load_probe_log'):
            with patch.object(checker.downloader, 'download_all_symbols', side_effect=Exception("Download failed")):
                with patch.object(checker, '_get_latest_trading_date', return_value=date.today()):
                    with patch.object(checker, '_get_missing_trading_dates', return_value=missing_dates):
                        result = checker.fill_missing_data(symbols=["000001.SZ"])
        
        assert result is False
    
    def test_fill_missing_data_with_asset_type(self, checker, temp_log_file, sample_download_log):
        """测试指定资产类型补齐数据"""
        old_date = date.today() - timedelta(days=2)
        sample_download_log["trading_date"] = old_date.strftime("%Y-%m-%d")
        
        with open(temp_log_file, 'w', encoding='utf-8') as f:
            json.dump(sample_download_log, f)
        
        mock_download_result = {
            "summary": {
                "success": 1,
                "failed": 0
            }
        }
        
        # Mock缺失日期以触发下载流程
        missing_dates = [date.today() - timedelta(days=1)]
        with patch.object(checker.downloader, 'load_probe_log'):
            with patch.object(checker.downloader, 'download_all_symbols', return_value=mock_download_result) as mock_download:
                with patch.object(checker.downloader, 'save_download_log'):
                    with patch.object(checker, '_get_latest_trading_date', return_value=date.today()):
                        with patch.object(checker, '_get_missing_trading_dates', return_value=missing_dates):
                            result = checker.fill_missing_data(
                                symbols=["000001.SZ"],
                                asset_type=AssetType.FUTURES
                            )
        
        # 验证调用时使用了正确的资产类型
        assert mock_download.called
        call_args = mock_download.call_args
        assert call_args[1]['asset_type'] == AssetType.FUTURES


class TestDataCompletenessCheckerIntegration:
    """数据完整性检查器集成测试"""
    
    @pytest.fixture
    def temp_log_file(self, tmp_path):
        """临时日志文件"""
        log_file = tmp_path / "integration_download.log"
        return str(log_file)
    
    @pytest.fixture
    def checker(self, temp_log_file):
        """创建检查器实例"""
        return DataCompletenessChecker(download_log_path=temp_log_file)
    
    def test_full_workflow_data_up_to_date(self, checker, temp_log_file):
        """测试完整工作流：数据最新"""
        # 创建最新的下载日志
        today = date.today()
        log_data = {
            "trading_date": today.strftime("%Y-%m-%d"),
            "downloads": [],
            "summary": {"success": 0, "failed": 0}
        }
        
        with open(temp_log_file, 'w', encoding='utf-8') as f:
            json.dump(log_data, f)
        
        with patch.object(checker, '_get_latest_trading_date', return_value=today):
            # 检查数据完整性
            is_complete = checker.check_before_mining(symbols=["000001.SZ"])
        
        # 数据最新，不需要补齐
        assert is_complete is True
    
    def test_full_workflow_data_outdated(self, checker, temp_log_file):
        """测试完整工作流：数据过期需要补齐"""
        # 创建过期的下载日志
        old_date = date.today() - timedelta(days=3)
        log_data = {
            "trading_date": old_date.strftime("%Y-%m-%d"),
            "downloads": [],
            "summary": {"success": 0, "failed": 0}
        }
        
        with open(temp_log_file, 'w', encoding='utf-8') as f:
            json.dump(log_data, f)
        
        with patch.object(checker, '_get_latest_trading_date', return_value=date.today()):
            # 检查数据完整性
            is_complete = checker.check_before_mining(symbols=["000001.SZ"])
        
        # 数据过期，需要补齐
        assert is_complete is False
        
        # 补齐数据
        mock_download_result = {
            "summary": {"success": 1, "failed": 0}
        }
        
        with patch.object(checker.downloader, 'load_probe_log'):
            with patch.object(checker.downloader, 'download_all_symbols', return_value=mock_download_result):
                with patch.object(checker.downloader, 'save_download_log'):
                    with patch.object(checker, '_get_latest_trading_date', return_value=date.today()):
                        result = checker.fill_missing_data(symbols=["000001.SZ"])
        
        assert result is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
