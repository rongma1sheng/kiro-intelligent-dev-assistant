"""DataPrivacyManager单元测试

白皮书依据: 第七章 6.3.1 数据隐私合规（GDPR/个保法）

测试数据隐私管理器的各项功能：
- 数据导出（GDPR第15条）
- 数据删除（GDPR第17条）
- 日志匿名化
- Redis缓存清理
"""

import pytest
import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, MagicMock

from src.compliance.data_privacy_manager import (
    DataPrivacyManager,
    DataPrivacyError,
    UserNotFoundError,
    DataRetentionError,
    UserDataExport,
    DataDeletionResult,
)


class TestDataPrivacyManagerInit:
    """DataPrivacyManager初始化测试"""
    
    def test_init_default_values(self, tmp_path):
        """测试默认参数初始化"""
        manager = DataPrivacyManager(export_dir=tmp_path)
        
        assert manager.export_dir == tmp_path
        assert manager.trade_retention_years == 7
        assert manager.redis_client is None
        assert manager.audit_logger is None
        assert manager.user_data_provider is None
    
    def test_init_custom_values(self, tmp_path):
        """测试自定义参数初始化"""
        manager = DataPrivacyManager(
            export_dir=tmp_path,
            trade_retention_years=5
        )
        
        assert manager.trade_retention_years == 5
    
    def test_init_with_redis_client(self, tmp_path):
        """测试带Redis客户端初始化"""
        mock_redis = Mock()
        manager = DataPrivacyManager(
            export_dir=tmp_path,
            redis_client=mock_redis
        )
        
        assert manager.redis_client is mock_redis
    
    def test_init_with_audit_logger(self, tmp_path):
        """测试带审计日志记录器初始化"""
        mock_logger = Mock()
        manager = DataPrivacyManager(
            export_dir=tmp_path,
            audit_logger=mock_logger
        )
        
        assert manager.audit_logger is mock_logger
    
    def test_init_invalid_retention_years(self, tmp_path):
        """测试无效的保留年限"""
        with pytest.raises(ValueError, match="交易数据保留年限不能为负"):
            DataPrivacyManager(
                export_dir=tmp_path,
                trade_retention_years=-1
            )
    
    def test_init_creates_export_dir(self, tmp_path):
        """测试自动创建导出目录"""
        export_dir = tmp_path / "new_exports"
        manager = DataPrivacyManager(export_dir=export_dir)
        
        assert export_dir.exists()


class TestExportUserData:
    """数据导出测试"""
    
    def test_export_user_data_basic(self, tmp_path):
        """测试基本数据导出"""
        manager = DataPrivacyManager(export_dir=tmp_path)
        manager.set_user_data("user001", {
            "name": "测试用户",
            "email": "test@example.com"
        })
        
        result = manager.export_user_data("user001")
        
        assert result.user_id == "user001"
        assert "user_info" in result.data_categories
        assert result.record_count >= 1
        assert Path(result.export_file).exists()
    
    def test_export_user_data_with_trades(self, tmp_path):
        """测试包含交易数据的导出"""
        manager = DataPrivacyManager(export_dir=tmp_path)
        manager.set_user_data("user001", {"name": "测试用户"})
        manager.set_trade_data("user001", [
            {"symbol": "000001.SZ", "action": "buy", "quantity": 100},
            {"symbol": "000002.SZ", "action": "sell", "quantity": 50}
        ])
        
        result = manager.export_user_data("user001")
        
        assert "user_info" in result.data_categories
        assert "trade_history" in result.data_categories
        assert result.record_count >= 3
    
    def test_export_user_data_file_content(self, tmp_path):
        """测试导出文件内容"""
        manager = DataPrivacyManager(export_dir=tmp_path)
        manager.set_user_data("user001", {
            "name": "测试用户",
            "email": "test@example.com"
        })
        
        result = manager.export_user_data("user001")
        
        with open(result.export_file, 'r', encoding='utf-8') as f:
            exported_data = json.load(f)
        
        assert "user_info" in exported_data
        assert exported_data["user_info"]["name"] == "测试用户"
    
    def test_export_user_data_empty_user_id(self, tmp_path):
        """测试空用户ID"""
        manager = DataPrivacyManager(export_dir=tmp_path)
        
        with pytest.raises(ValueError, match="用户ID不能为空"):
            manager.export_user_data("")
        
        with pytest.raises(ValueError, match="用户ID不能为空"):
            manager.export_user_data("   ")
    
    def test_export_user_data_user_not_found(self, tmp_path):
        """测试用户不存在"""
        manager = DataPrivacyManager(export_dir=tmp_path)
        
        with pytest.raises(UserNotFoundError, match="用户不存在"):
            manager.export_user_data("nonexistent_user")
    
    def test_export_user_data_logs_event(self, tmp_path):
        """测试导出记录审计日志"""
        mock_logger = Mock()
        manager = DataPrivacyManager(
            export_dir=tmp_path,
            audit_logger=mock_logger
        )
        manager.set_user_data("user001", {"name": "测试用户"})
        
        manager.export_user_data("user001")
        
        mock_logger.log_event.assert_called()
        call_args = mock_logger.log_event.call_args[0][0]
        assert call_args['event_type'] == 'DATA_EXPORT'
        assert call_args['user_id'] == 'user001'
    
    def test_export_user_data_from_provider(self, tmp_path):
        """测试从提供者获取数据"""
        mock_provider = Mock()
        mock_provider.get_user_data.return_value = {
            "user_info": {"name": "提供者用户"},
            "preferences": {"theme": "dark"}
        }
        
        manager = DataPrivacyManager(
            export_dir=tmp_path,
            user_data_provider=mock_provider
        )
        
        result = manager.export_user_data("user001")
        
        assert "user_info" in result.data_categories
        assert "preferences" in result.data_categories



class TestDeleteUserData:
    """数据删除测试"""
    
    def test_delete_user_data_basic(self, tmp_path):
        """测试基本数据删除"""
        manager = DataPrivacyManager(export_dir=tmp_path)
        manager.set_user_data("user001", {"name": "测试用户"})
        
        result = manager.delete_user_data("user001")
        
        assert result.user_id == "user001"
        assert result.reason == "user_request"
        assert "user_info" in result.deleted_categories
    
    def test_delete_user_data_with_reason(self, tmp_path):
        """测试带原因的数据删除"""
        manager = DataPrivacyManager(export_dir=tmp_path)
        manager.set_user_data("user001", {"name": "测试用户"})
        
        result = manager.delete_user_data("user001", reason="account_closure")
        
        assert result.reason == "account_closure"
    
    def test_delete_user_data_empty_user_id(self, tmp_path):
        """测试空用户ID"""
        manager = DataPrivacyManager(export_dir=tmp_path)
        
        with pytest.raises(ValueError, match="用户ID不能为空"):
            manager.delete_user_data("")
    
    def test_delete_user_data_removes_user_info(self, tmp_path):
        """测试删除后用户信息不存在"""
        manager = DataPrivacyManager(export_dir=tmp_path)
        manager.set_user_data("user001", {"name": "测试用户"})
        
        manager.delete_user_data("user001")
        
        assert manager.get_user_data("user001") is None
    
    def test_delete_user_data_removes_trade_data(self, tmp_path):
        """测试删除后交易数据不存在"""
        manager = DataPrivacyManager(export_dir=tmp_path)
        manager.set_user_data("user001", {"name": "测试用户"})
        manager.set_trade_data("user001", [
            {"symbol": "000001.SZ", "action": "buy"}
        ])
        
        manager.delete_user_data("user001")
        
        assert len(manager.get_trade_data("user001")) == 0
    
    def test_delete_user_data_retention_check(self, tmp_path):
        """测试交易数据保留期检查"""
        manager = DataPrivacyManager(
            export_dir=tmp_path,
            trade_retention_years=7
        )
        manager.set_user_data("user001", {"name": "测试用户"})
        
        # 设置最近的交易（在保留期内）
        recent_trade_time = datetime.now() - timedelta(days=30)
        manager.set_trade_data("user001", [
            {"symbol": "000001.SZ", "timestamp": recent_trade_time.isoformat()}
        ])
        
        with pytest.raises(DataRetentionError, match="交易数据在保留期内"):
            manager.delete_user_data("user001")
    
    def test_delete_user_data_old_trades_allowed(self, tmp_path):
        """测试超过保留期的交易数据可以删除"""
        manager = DataPrivacyManager(
            export_dir=tmp_path,
            trade_retention_years=7
        )
        manager.set_user_data("user001", {"name": "测试用户"})
        
        # 设置很久以前的交易（超过保留期）
        old_trade_time = datetime.now() - timedelta(days=365 * 8)
        manager.set_trade_data("user001", [
            {"symbol": "000001.SZ", "timestamp": old_trade_time.isoformat()}
        ])
        
        result = manager.delete_user_data("user001")
        
        assert "trade_data" in result.deleted_categories
    
    def test_delete_user_data_logs_request(self, tmp_path):
        """测试删除请求记录审计日志"""
        mock_logger = Mock()
        manager = DataPrivacyManager(
            export_dir=tmp_path,
            audit_logger=mock_logger
        )
        manager.set_user_data("user001", {"name": "测试用户"})
        
        manager.delete_user_data("user001")
        
        # 应该记录删除请求和删除完成两个事件
        assert mock_logger.log_event.call_count >= 2
    
    def test_delete_user_data_clears_redis(self, tmp_path):
        """测试删除清理Redis缓存"""
        mock_redis = Mock()
        mock_redis.keys.return_value = [
            b"mia:user:user001:session",
            b"mia:user:user001:preferences"
        ]
        
        manager = DataPrivacyManager(
            export_dir=tmp_path,
            redis_client=mock_redis
        )
        manager.set_user_data("user001", {"name": "测试用户"})
        
        result = manager.delete_user_data("user001")
        
        assert result.redis_keys_deleted == 2
        assert mock_redis.delete.call_count == 2


class TestAnonymizeLogs:
    """日志匿名化测试"""
    
    def test_anonymize_logs_basic(self, tmp_path):
        """测试基本日志匿名化"""
        manager = DataPrivacyManager(export_dir=tmp_path)
        manager.set_user_data("user001", {"name": "测试用户"})
        
        # 生成一些日志
        manager.export_user_data("user001")
        
        count = manager.anonymize_logs("user001")
        
        assert count >= 1
    
    def test_anonymize_logs_replaces_user_id(self, tmp_path):
        """测试匿名化替换用户ID"""
        manager = DataPrivacyManager(export_dir=tmp_path)
        manager.set_user_data("user001", {"name": "测试用户"})
        manager.export_user_data("user001")
        
        manager.anonymize_logs("user001")
        
        logs = manager.get_logs()
        for log in logs:
            if log.get('anonymized'):
                assert log['user_id'].startswith("anon_")
                assert log['user_id'] != "user001"
    
    def test_anonymize_logs_empty_user_id(self, tmp_path):
        """测试空用户ID"""
        manager = DataPrivacyManager(export_dir=tmp_path)
        
        count = manager.anonymize_logs("")
        
        assert count == 0
    
    def test_anonymize_logs_deterministic(self, tmp_path):
        """测试匿名ID是确定性的"""
        manager = DataPrivacyManager(export_dir=tmp_path)
        
        anon_id1 = manager._anonymize_id("user001")
        anon_id2 = manager._anonymize_id("user001")
        
        assert anon_id1 == anon_id2
    
    def test_anonymize_logs_different_users(self, tmp_path):
        """测试不同用户生成不同匿名ID"""
        manager = DataPrivacyManager(export_dir=tmp_path)
        
        anon_id1 = manager._anonymize_id("user001")
        anon_id2 = manager._anonymize_id("user002")
        
        assert anon_id1 != anon_id2
    
    def test_is_user_anonymized(self, tmp_path):
        """测试检查用户是否已匿名化"""
        manager = DataPrivacyManager(export_dir=tmp_path)
        manager.set_user_data("user001", {"name": "测试用户"})
        manager.export_user_data("user001")
        
        assert not manager.is_user_anonymized("user001")
        
        manager.anonymize_logs("user001")
        
        # 匿名化后，原始user_id不再存在于日志中
        # 但匿名ID存在
        logs = manager.get_logs()
        has_anonymized = any(log.get('anonymized') for log in logs)
        assert has_anonymized


class TestRedisIntegration:
    """Redis集成测试"""
    
    def test_get_redis_user_data(self, tmp_path):
        """测试从Redis获取用户数据"""
        mock_redis = Mock()
        mock_redis.keys.return_value = [b"mia:user:user001:session"]
        mock_redis.get.return_value = b'{"token": "abc123"}'
        
        manager = DataPrivacyManager(
            export_dir=tmp_path,
            redis_client=mock_redis
        )
        
        data = manager._get_redis_user_data("user001")
        
        assert "mia:user:user001:session" in data
    
    def test_clear_redis_cache(self, tmp_path):
        """测试清理Redis缓存"""
        mock_redis = Mock()
        mock_redis.keys.return_value = [
            b"mia:user:user001:key1",
            b"mia:user:user001:key2"
        ]
        
        manager = DataPrivacyManager(
            export_dir=tmp_path,
            redis_client=mock_redis
        )
        
        count = manager._clear_redis_cache("user001")
        
        assert count == 2
        assert mock_redis.delete.call_count == 2
    
    def test_redis_exception_handled(self, tmp_path):
        """测试Redis异常被处理"""
        mock_redis = Mock()
        mock_redis.keys.side_effect = Exception("Redis错误")
        
        manager = DataPrivacyManager(
            export_dir=tmp_path,
            redis_client=mock_redis
        )
        
        # 不应该抛出异常
        count = manager._clear_redis_cache("user001")
        assert count == 0


class TestUserDataExport:
    """UserDataExport数据类测试"""
    
    def test_to_dict(self):
        """测试转换为字典"""
        export = UserDataExport(
            user_id="user001",
            export_time="2024-01-01T00:00:00",
            export_file="/path/to/file.json",
            data_categories=["user_info", "trade_history"],
            record_count=10
        )
        
        result = export.to_dict()
        
        assert result['user_id'] == "user001"
        assert result['export_time'] == "2024-01-01T00:00:00"
        assert result['export_file'] == "/path/to/file.json"
        assert result['data_categories'] == ["user_info", "trade_history"]
        assert result['record_count'] == 10


class TestDataDeletionResult:
    """DataDeletionResult数据类测试"""
    
    def test_to_dict(self):
        """测试转换为字典"""
        result = DataDeletionResult(
            user_id="user001",
            deletion_time="2024-01-01T00:00:00",
            reason="user_request",
            deleted_categories=["user_info"],
            anonymized_logs=5,
            redis_keys_deleted=3
        )
        
        result_dict = result.to_dict()
        
        assert result_dict['user_id'] == "user001"
        assert result_dict['deletion_time'] == "2024-01-01T00:00:00"
        assert result_dict['reason'] == "user_request"
        assert result_dict['deleted_categories'] == ["user_info"]
        assert result_dict['anonymized_logs'] == 5
        assert result_dict['redis_keys_deleted'] == 3


class TestManagementMethods:
    """管理方法测试"""
    
    def test_set_and_get_user_data(self, tmp_path):
        """测试设置和获取用户数据"""
        manager = DataPrivacyManager(export_dir=tmp_path)
        
        manager.set_user_data("user001", {"name": "测试用户"})
        
        data = manager.get_user_data("user001")
        assert data["name"] == "测试用户"
    
    def test_set_and_get_trade_data(self, tmp_path):
        """测试设置和获取交易数据"""
        manager = DataPrivacyManager(export_dir=tmp_path)
        
        trades = [{"symbol": "000001.SZ", "action": "buy"}]
        manager.set_trade_data("user001", trades)
        
        result = manager.get_trade_data("user001")
        assert len(result) == 1
        assert result[0]["symbol"] == "000001.SZ"
    
    def test_get_logs(self, tmp_path):
        """测试获取日志"""
        manager = DataPrivacyManager(export_dir=tmp_path)
        manager.set_user_data("user001", {"name": "测试用户"})
        manager.export_user_data("user001")
        
        logs = manager.get_logs()
        
        assert len(logs) >= 1
    
    def test_clear_logs(self, tmp_path):
        """测试清空日志"""
        manager = DataPrivacyManager(export_dir=tmp_path)
        manager.set_user_data("user001", {"name": "测试用户"})
        manager.export_user_data("user001")
        
        manager.clear_logs()
        
        assert len(manager.get_logs()) == 0
