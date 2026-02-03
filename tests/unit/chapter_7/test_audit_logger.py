"""AuditLogger单元测试

白皮书依据: 第六章 6.2.2 审计日志系统

测试AuditLogger的核心功能：
- 日志写入
- 签名生成
- 完整性验证
- 篡改检测
"""

import json
import os
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.audit.audit_logger import AuditLogger, IntegrityError
from src.audit.data_models import AuditEventType, AuditEntry


class TestAuditLogger:
    """AuditLogger单元测试套件
    
    白皮书依据: 第六章 6.2.2 审计日志系统
    Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7
    """
    
    @pytest.fixture
    def temp_log_dir(self):
        """创建临时日志目录"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        # 清理
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    @pytest.fixture
    def audit_logger(self, temp_log_dir):
        """创建AuditLogger实例"""
        return AuditLogger(log_dir=temp_log_dir)
    
    def test_log_trade_basic(self, audit_logger):
        """测试基本交易日志记录
        
        白皮书依据: 第六章 6.2.2 审计日志系统
        Requirements: 4.1
        
        验证：
        1. 可以记录交易日志
        2. 返回AuditEntry对象
        3. 日志文件被创建
        """
        trade_data = {
            'symbol': '000001.SZ',
            'action': 'buy',
            'quantity': 100,
            'price': 10.5,
        }
        
        entry = audit_logger.log_trade(trade_data)
        
        assert isinstance(entry, AuditEntry)
        assert entry.event_type == AuditEventType.TRADE_EXECUTION
        assert entry.data['symbol'] == '000001.SZ'
        assert entry.data['action'] == 'buy'
        assert entry.data['quantity'] == 100
        assert entry.data['price'] == 10.5
        assert entry.audit_signature is not None
        assert len(entry.audit_signature) == 64  # SHA256 hex length
        
        # 验证日志文件存在
        assert audit_logger.log_file.exists()
    
    def test_log_trade_with_all_fields(self, audit_logger):
        """测试带所有字段的交易日志
        
        Requirements: 4.1
        """
        trade_data = {
            'symbol': '600000.SH',
            'action': 'sell',
            'quantity': 200,
            'price': 15.0,
            'amount': 3000.0,
            'order_id': 'ORD_001',
            'strategy_id': 'S01',
            'user_id': 'admin',
        }
        
        entry = audit_logger.log_trade(trade_data)
        
        assert entry.data['symbol'] == '600000.SH'
        assert entry.data['action'] == 'sell'
        assert entry.data['amount'] == 3000.0
        assert entry.data['order_id'] == 'ORD_001'
        assert entry.data['strategy_id'] == 'S01'
        assert entry.user_id == 'admin'
    
    def test_log_trade_calculates_amount(self, audit_logger):
        """测试自动计算金额
        
        Requirements: 4.1
        """
        trade_data = {
            'symbol': '000001.SZ',
            'action': 'buy',
            'quantity': 100,
            'price': 10.0,
        }
        
        entry = audit_logger.log_trade(trade_data)
        
        assert entry.data['amount'] == 1000.0  # 100 * 10.0
    
    def test_log_trade_missing_required_fields(self, audit_logger):
        """测试缺少必需字段
        
        Requirements: 4.1
        """
        # 缺少symbol
        with pytest.raises(ValueError) as exc_info:
            audit_logger.log_trade({
                'action': 'buy',
                'quantity': 100,
                'price': 10.0,
            })
        assert 'symbol' in str(exc_info.value)
        
        # 缺少action
        with pytest.raises(ValueError) as exc_info:
            audit_logger.log_trade({
                'symbol': '000001.SZ',
                'quantity': 100,
                'price': 10.0,
            })
        assert 'action' in str(exc_info.value)
    
    def test_log_trade_invalid_action(self, audit_logger):
        """测试无效的交易动作
        
        Requirements: 4.1
        """
        with pytest.raises(ValueError) as exc_info:
            audit_logger.log_trade({
                'symbol': '000001.SZ',
                'action': 'invalid',
                'quantity': 100,
                'price': 10.0,
            })
        # 检查错误消息包含无效值或中文关键词
        error_msg = str(exc_info.value)
        assert 'invalid' in error_msg or '无效' in error_msg or '动作' in error_msg
    
    def test_log_event_basic(self, audit_logger):
        """测试基本事件日志记录
        
        白皮书依据: 第六章 6.2.2 审计日志系统
        Requirements: 4.3
        """
        event_data = {
            'event_type': 'USER_LOGIN',
            'user_id': 'admin',
            'ip_address': '192.168.1.1',
        }
        
        entry = audit_logger.log_event(event_data)
        
        assert isinstance(entry, AuditEntry)
        assert entry.event_type == AuditEventType.USER_LOGIN
        assert entry.user_id == 'admin'
        assert entry.data['ip_address'] == '192.168.1.1'
    
    def test_log_event_all_types(self, audit_logger):
        """测试所有事件类型
        
        Requirements: 4.3
        """
        for event_type in AuditEventType:
            event_data = {
                'event_type': event_type.value,
                'test_field': 'test_value',
            }
            
            entry = audit_logger.log_event(event_data)
            
            assert entry.event_type == event_type
    
    def test_log_event_invalid_type(self, audit_logger):
        """测试无效的事件类型
        
        Requirements: 4.3
        """
        with pytest.raises(ValueError) as exc_info:
            audit_logger.log_event({
                'event_type': 'INVALID_TYPE',
            })
        # 检查错误消息包含无效值或中文关键词
        error_msg = str(exc_info.value)
        assert 'INVALID_TYPE' in error_msg or '无效' in error_msg or '事件类型' in error_msg
    
    def test_log_event_missing_type(self, audit_logger):
        """测试缺少事件类型
        
        Requirements: 4.3
        """
        with pytest.raises(ValueError) as exc_info:
            audit_logger.log_event({
                'some_field': 'some_value',
            })
        assert 'event_type' in str(exc_info.value)
    
    def test_signature_generation(self, audit_logger):
        """测试签名生成
        
        白皮书依据: 第六章 6.2.2 审计日志系统
        Requirements: 4.2
        
        验证：
        1. 签名是SHA256格式（64字符十六进制）
        2. 相同数据产生相同签名
        3. 不同数据产生不同签名
        """
        entry1 = {
            'timestamp': '2026-01-25T10:00:00',
            'event_type': 'TEST',
            'data': 'test_data',
        }
        
        entry2 = {
            'timestamp': '2026-01-25T10:00:00',
            'event_type': 'TEST',
            'data': 'test_data',
        }
        
        entry3 = {
            'timestamp': '2026-01-25T10:00:00',
            'event_type': 'TEST',
            'data': 'different_data',
        }
        
        sig1 = audit_logger._generate_signature(entry1)
        sig2 = audit_logger._generate_signature(entry2)
        sig3 = audit_logger._generate_signature(entry3)
        
        # SHA256格式验证
        assert len(sig1) == 64
        assert all(c in '0123456789abcdef' for c in sig1)
        
        # 相同数据相同签名
        assert sig1 == sig2
        
        # 不同数据不同签名
        assert sig1 != sig3
    
    def test_signature_excludes_signature_field(self, audit_logger):
        """测试签名排除audit_signature字段
        
        Requirements: 4.2
        """
        entry_without_sig = {
            'timestamp': '2026-01-25T10:00:00',
            'event_type': 'TEST',
        }
        
        entry_with_sig = {
            'timestamp': '2026-01-25T10:00:00',
            'event_type': 'TEST',
            'audit_signature': 'some_existing_signature',
        }
        
        sig1 = audit_logger._generate_signature(entry_without_sig)
        sig2 = audit_logger._generate_signature(entry_with_sig)
        
        # 签名应该相同（audit_signature被排除）
        assert sig1 == sig2
    
    def test_verify_integrity_valid(self, audit_logger):
        """测试验证有效日志的完整性
        
        白皮书依据: 第六章 6.2.3 完整性验证
        Requirements: 4.5
        """
        # 写入一些日志
        audit_logger.log_trade({
            'symbol': '000001.SZ',
            'action': 'buy',
            'quantity': 100,
            'price': 10.0,
        })
        
        audit_logger.log_event({
            'event_type': 'USER_LOGIN',
            'user_id': 'admin',
        })
        
        # 验证完整性
        result = audit_logger.verify_integrity()
        
        assert result is True
    
    def test_verify_integrity_tampered(self, audit_logger):
        """测试检测篡改的日志
        
        白皮书依据: 第六章 6.2.3 完整性验证
        Requirements: 4.5, 4.6
        
        验证：
        1. 篡改后的日志被检测到
        2. 抛出IntegrityError
        """
        # 写入日志
        audit_logger.log_trade({
            'symbol': '000001.SZ',
            'action': 'buy',
            'quantity': 100,
            'price': 10.0,
        })
        
        # 篡改日志文件
        with open(audit_logger.log_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 修改数量
        tampered_content = content.replace('"quantity": 100', '"quantity": 200')
        
        with open(audit_logger.log_file, 'w', encoding='utf-8') as f:
            f.write(tampered_content)
        
        # 验证应该失败
        with pytest.raises(IntegrityError) as exc_info:
            audit_logger.verify_integrity()
        
        assert 'mismatch' in str(exc_info.value).lower()
    
    def test_verify_integrity_missing_signature(self, audit_logger):
        """测试检测缺少签名的日志
        
        Requirements: 4.5
        """
        # 直接写入没有签名的日志
        entry = {
            'timestamp': datetime.now().isoformat(),
            'event_type': 'TEST',
        }
        
        with open(audit_logger.log_file, 'w', encoding='utf-8') as f:
            f.write(json.dumps(entry) + '\n')
        
        with pytest.raises(IntegrityError) as exc_info:
            audit_logger.verify_integrity()
        
        assert 'audit_signature' in str(exc_info.value)
    
    def test_verify_integrity_file_not_found(self, audit_logger):
        """测试验证不存在的文件
        
        Requirements: 4.5
        """
        with pytest.raises(FileNotFoundError):
            audit_logger.verify_integrity(Path('/nonexistent/file.log'))
    
    def test_get_recent_logs(self, audit_logger):
        """测试获取最近日志
        
        Requirements: 4.4
        """
        # 写入多条日志
        for i in range(5):
            audit_logger.log_event({
                'event_type': 'API_CALL',
                'call_id': i,
            })
        
        # 获取最近3条
        logs = audit_logger.get_recent_logs(3)
        
        assert len(logs) == 3
        # 最近的日志在前面
        assert logs[0]['data']['call_id'] == 4
    
    def test_get_recent_logs_invalid_count(self, audit_logger):
        """测试无效的日志数量
        
        Requirements: 4.4
        """
        with pytest.raises(ValueError):
            audit_logger.get_recent_logs(0)
        
        with pytest.raises(ValueError):
            audit_logger.get_recent_logs(-1)
    
    def test_get_logs_by_date(self, audit_logger):
        """测试按日期获取日志
        
        Requirements: 4.4
        """
        # 写入日志
        audit_logger.log_event({
            'event_type': 'USER_LOGIN',
        })
        
        # 获取今天的日志
        logs = audit_logger.get_logs_by_date(datetime.now())
        
        assert len(logs) >= 1
        assert logs[0]['event_type'] == 'USER_LOGIN'
    
    def test_get_logs_by_event_type(self, audit_logger):
        """测试按事件类型获取日志
        
        Requirements: 4.4
        """
        # 写入不同类型的日志
        audit_logger.log_event({'event_type': 'USER_LOGIN'})
        audit_logger.log_event({'event_type': 'API_CALL'})
        audit_logger.log_event({'event_type': 'USER_LOGIN'})
        
        # 获取USER_LOGIN类型
        logs = audit_logger.get_logs_by_event_type(AuditEventType.USER_LOGIN)
        
        assert len(logs) == 2
        for log in logs:
            assert log['event_type'] == 'USER_LOGIN'
    
    def test_verify_all_logs(self, audit_logger):
        """测试验证所有日志文件
        
        Requirements: 4.5
        """
        # 写入日志
        audit_logger.log_event({'event_type': 'USER_LOGIN'})
        
        # 验证所有日志
        results = audit_logger.verify_all_logs()
        
        assert len(results) >= 1
        assert all(v is True for v in results.values())


class TestAuditLoggerRedisSync:
    """AuditLogger Redis同步测试
    
    白皮书依据: 第六章 6.2.2 审计日志系统
    Requirements: 4.7
    """
    
    @pytest.fixture
    def temp_log_dir(self):
        """创建临时日志目录"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    @pytest.fixture
    def mock_redis(self):
        """创建Mock Redis客户端"""
        redis_mock = MagicMock()
        redis_mock.lpush = MagicMock()
        redis_mock.ltrim = MagicMock()
        redis_mock.lrange = MagicMock(return_value=[])
        return redis_mock
    
    @pytest.fixture
    def audit_logger_with_redis(self, temp_log_dir, mock_redis):
        """创建带Redis的AuditLogger实例"""
        return AuditLogger(log_dir=temp_log_dir, redis_client=mock_redis)
    
    def test_sync_to_redis_on_log_trade(self, audit_logger_with_redis, mock_redis):
        """测试交易日志同步到Redis
        
        Requirements: 4.7
        """
        audit_logger_with_redis.log_trade({
            'symbol': '000001.SZ',
            'action': 'buy',
            'quantity': 100,
            'price': 10.0,
        })
        
        # 验证Redis调用
        mock_redis.lpush.assert_called_once()
        mock_redis.ltrim.assert_called_once()
        
        # 验证lpush的key
        call_args = mock_redis.lpush.call_args
        assert call_args[0][0] == 'mia:audit:recent_logs'
    
    def test_sync_to_redis_on_log_event(self, audit_logger_with_redis, mock_redis):
        """测试事件日志同步到Redis
        
        Requirements: 4.7
        """
        audit_logger_with_redis.log_event({
            'event_type': 'USER_LOGIN',
        })
        
        mock_redis.lpush.assert_called_once()
        mock_redis.ltrim.assert_called_once()
    
    def test_redis_trim_to_max_recent_logs(self, temp_log_dir, mock_redis):
        """测试Redis列表长度限制
        
        Requirements: 4.7
        """
        max_logs = 500
        logger = AuditLogger(
            log_dir=temp_log_dir,
            redis_client=mock_redis,
            max_recent_logs=max_logs
        )
        
        logger.log_event({'event_type': 'USER_LOGIN'})
        
        # 验证ltrim参数
        call_args = mock_redis.ltrim.call_args
        assert call_args[0][2] == max_logs - 1
    
    def test_get_recent_logs_from_redis(self, audit_logger_with_redis, mock_redis):
        """测试从Redis获取最近日志
        
        Requirements: 4.7
        """
        # 设置Redis返回值
        mock_redis.lrange.return_value = [
            json.dumps({'event_type': 'USER_LOGIN', 'timestamp': '2026-01-25T10:00:00'}),
            json.dumps({'event_type': 'API_CALL', 'timestamp': '2026-01-25T09:00:00'}),
        ]
        
        logs = audit_logger_with_redis.get_recent_logs(10)
        
        assert len(logs) == 2
        mock_redis.lrange.assert_called_once()
    
    def test_redis_failure_fallback_to_file(self, audit_logger_with_redis, mock_redis):
        """测试Redis失败时回退到文件
        
        Requirements: 4.7
        """
        # 模拟Redis失败
        mock_redis.lrange.side_effect = Exception("Redis connection failed")
        
        # 先写入一些日志到文件
        audit_logger_with_redis.log_event({'event_type': 'USER_LOGIN'})
        
        # 重置mock以模拟获取时失败
        mock_redis.lrange.side_effect = Exception("Redis connection failed")
        
        # 应该从文件获取
        logs = audit_logger_with_redis.get_recent_logs(10)
        
        assert len(logs) >= 1


class TestAuditLoggerInitialization:
    """AuditLogger初始化测试
    
    白皮书依据: 第六章 6.2.2 审计日志系统
    """
    
    def test_init_creates_log_dir(self):
        """测试初始化创建日志目录"""
        temp_dir = tempfile.mkdtemp()
        log_dir = os.path.join(temp_dir, 'new_audit_dir')
        
        try:
            logger = AuditLogger(log_dir=log_dir)
            assert os.path.exists(log_dir)
        finally:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    def test_init_invalid_max_recent_logs(self):
        """测试无效的max_recent_logs"""
        with pytest.raises(ValueError):
            AuditLogger(max_recent_logs=0)
        
        with pytest.raises(ValueError):
            AuditLogger(max_recent_logs=-1)
    
    def test_init_default_values(self):
        """测试默认值"""
        temp_dir = tempfile.mkdtemp()
        try:
            logger = AuditLogger(log_dir=temp_dir)
            assert logger.max_recent_logs == 1000
            assert logger.redis_client is None
        finally:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)
