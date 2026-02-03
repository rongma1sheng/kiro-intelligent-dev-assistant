"""认证通知服务单元测试

测试CertificationNotificationService的所有功能。
"""

import pytest
from datetime import datetime, timedelta
from src.evolution.certification_notification_service import (
    CertificationNotificationService,
    NotificationChannel,
    NotificationPriority,
    NotificationEventType,
    NotificationMessage,
    NotificationRecord
)


class TestCertificationNotificationService:
    """测试CertificationNotificationService类"""
    
    @pytest.fixture
    def service(self):
        """创建通知服务实例"""
        return CertificationNotificationService(
            default_channels=[NotificationChannel.SYSTEM],
            enable_email=True,
            enable_sms=True,
            enable_system=True,
            enable_wechat=True
        )
    
    def test_initialization(self, service):
        """测试初始化"""
        assert service.default_channels == [NotificationChannel.SYSTEM]
        assert service.enable_email is True
        assert service.enable_sms is True
        assert service.enable_system is True
        assert service.enable_wechat is True
        assert len(service.notification_history) == 0
        assert service._message_id_counter == 0
    
    def test_notify_certification_started(self, service):
        """测试认证启动通知"""
        record = service.notify_certification_started(
            strategy_id="STRAT-001",
            strategy_name="测试策略A"
        )
        
        assert isinstance(record, NotificationRecord)
        assert record.message.event_type == NotificationEventType.CERTIFICATION_STARTED
        assert "测试策略A" in record.message.title
        assert "STRAT-001" in record.message.content
        assert record.message.priority == NotificationPriority.NORMAL
        assert record.status == 'success'
        assert len(record.sent_channels) > 0
        assert len(service.notification_history) == 1
    
    def test_notify_certification_started_custom_channels(self, service):
        """测试认证启动通知（自定义渠道）"""
        custom_channels = [NotificationChannel.EMAIL, NotificationChannel.SMS]
        record = service.notify_certification_started(
            strategy_id="STRAT-002",
            strategy_name="测试策略B",
            channels=custom_channels
        )
        
        assert record.message.channels == custom_channels
        assert NotificationChannel.EMAIL in record.sent_channels
        assert NotificationChannel.SMS in record.sent_channels
    
    def test_notify_arena_completed_passed(self, service):
        """测试Arena验证完成通知（通过）"""
        layer_results = {
            '第一层': {'passed': True, 'score': 0.95},
            '第二层': {'passed': True, 'score': 0.88},
            '第三层': {'passed': True, 'score': 0.82},
            '第四层': {'passed': True, 'score': 0.90}
        }
        
        record = service.notify_arena_completed(
            strategy_id="STRAT-003",
            strategy_name="测试策略C",
            arena_passed=True,
            arena_score=0.89,
            layer_results=layer_results
        )
        
        assert record.message.event_type == NotificationEventType.ARENA_COMPLETED
        assert "通过" in record.message.title
        assert record.message.priority == NotificationPriority.NORMAL
        assert record.message.metadata['arena_passed'] is True
        assert record.message.metadata['arena_score'] == 0.89
        assert "✅ 通过" in record.message.content
    
    def test_notify_arena_completed_failed(self, service):
        """测试Arena验证完成通知（未通过）"""
        layer_results = {
            '第一层': {'passed': True, 'score': 0.85},
            '第二层': {'passed': False, 'score': 0.65},
            '第三层': {'passed': True, 'score': 0.75},
            '第四层': {'passed': False, 'score': 0.60}
        }
        
        record = service.notify_arena_completed(
            strategy_id="STRAT-004",
            strategy_name="测试策略D",
            arena_passed=False,
            arena_score=0.71,
            layer_results=layer_results
        )
        
        assert "未通过" in record.message.title
        assert record.message.priority == NotificationPriority.HIGH
        assert record.message.metadata['arena_passed'] is False
        assert "❌ 未通过" in record.message.content
    
    def test_notify_simulation_completed_passed(self, service):
        """测试模拟盘验证完成通知（通过）"""
        overall_metrics = {
            'sharpe_ratio': 2.5,
            'max_drawdown': 0.12,
            'win_rate': 0.65,
            'total_return': 0.35
        }
        
        record = service.notify_simulation_completed(
            strategy_id="STRAT-005",
            strategy_name="测试策略E",
            simulation_passed=True,
            duration_days=30,
            best_tier="Tier 3",
            overall_metrics=overall_metrics
        )
        
        assert record.message.event_type == NotificationEventType.SIMULATION_COMPLETED
        assert "通过" in record.message.title
        assert record.message.priority == NotificationPriority.NORMAL
        assert record.message.metadata['simulation_passed'] is True
        assert record.message.metadata['duration_days'] == 30
        assert "Tier 3" in record.message.content
    
    def test_notify_simulation_completed_failed(self, service):
        """测试模拟盘验证完成通知（未通过）"""
        overall_metrics = {
            'sharpe_ratio': 1.2,
            'max_drawdown': 0.18,
            'win_rate': 0.52
        }
        
        record = service.notify_simulation_completed(
            strategy_id="STRAT-006",
            strategy_name="测试策略F",
            simulation_passed=False,
            duration_days=30,
            best_tier="Tier 1",
            overall_metrics=overall_metrics
        )
        
        assert "未通过" in record.message.title
        assert record.message.priority == NotificationPriority.HIGH
        assert record.message.metadata['simulation_passed'] is False
    
    def test_notify_certification_granted_platinum(self, service):
        """测试认证颁发通知（白金级）"""
        simulation_metrics = {
            'sharpe_ratio': 3.0,
            'max_drawdown': 0.08,
            'win_rate': 0.70
        }
        
        record = service.notify_certification_granted(
            strategy_id="STRAT-007",
            strategy_name="测试策略G",
            certification_level="platinum",
            max_allocation_ratio=0.20,
            arena_score=0.92,
            simulation_metrics=simulation_metrics
        )
        
        assert record.message.event_type == NotificationEventType.CERTIFICATION_GRANTED
        assert "🏆" in record.message.title
        assert record.message.priority == NotificationPriority.HIGH
        assert "PLATINUM" in record.message.content
        assert "20.0%" in record.message.content
    
    def test_notify_certification_granted_gold(self, service):
        """测试认证颁发通知（黄金级）"""
        simulation_metrics = {
            'sharpe_ratio': 2.2,
            'max_drawdown': 0.11,
            'win_rate': 0.62
        }
        
        record = service.notify_certification_granted(
            strategy_id="STRAT-008",
            strategy_name="测试策略H",
            certification_level="gold",
            max_allocation_ratio=0.15,
            arena_score=0.85,
            simulation_metrics=simulation_metrics
        )
        
        assert "🥇" in record.message.title
        assert "GOLD" in record.message.content
        assert "15.0%" in record.message.content
    
    def test_notify_certification_granted_silver(self, service):
        """测试认证颁发通知（白银级）"""
        simulation_metrics = {
            'sharpe_ratio': 1.8,
            'max_drawdown': 0.14,
            'win_rate': 0.58
        }
        
        record = service.notify_certification_granted(
            strategy_id="STRAT-009",
            strategy_name="测试策略I",
            certification_level="silver",
            max_allocation_ratio=0.10,
            arena_score=0.78,
            simulation_metrics=simulation_metrics
        )
        
        assert "🥈" in record.message.title
        assert "SILVER" in record.message.content
        assert "10.0%" in record.message.content
    
    def test_notify_certification_failed(self, service):
        """测试认证失败通知"""
        failure_details = {
            'failed_metrics': {
                'sharpe_ratio': 1.0,
                'max_drawdown': 0.20
            },
            'threshold': {
                'min_sharpe': 1.5,
                'max_drawdown': 0.15
            }
        }
        
        record = service.notify_certification_failed(
            strategy_id="STRAT-010",
            strategy_name="测试策略J",
            failed_stage="模拟盘验证",
            failure_reason="夏普比率和最大回撤未达标",
            failure_details=failure_details
        )
        
        assert record.message.event_type == NotificationEventType.CERTIFICATION_FAILED
        assert "❌" in record.message.title
        assert record.message.priority == NotificationPriority.HIGH
        assert "模拟盘验证" in record.message.content
        assert "夏普比率和最大回撤未达标" in record.message.content
    
    def test_notify_certification_revoked(self, service):
        """测试认证撤销通知"""
        record = service.notify_certification_revoked(
            strategy_id="STRAT-011",
            strategy_name="测试策略K",
            revocation_reason="连续3个月表现不达标",
            previous_level="gold"
        )
        
        assert record.message.event_type == NotificationEventType.CERTIFICATION_REVOKED
        assert "⚠️" in record.message.title
        assert record.message.priority == NotificationPriority.URGENT
        assert "GOLD" in record.message.content
        assert "连续3个月表现不达标" in record.message.content
        assert "已从策略库中移除" in record.message.content
    
    def test_notify_certification_downgraded(self, service):
        """测试认证降级通知"""
        record = service.notify_certification_downgraded(
            strategy_id="STRAT-012",
            strategy_name="测试策略L",
            previous_level="platinum",
            new_level="gold",
            downgrade_reason="近期表现下降",
            new_allocation_ratio=0.15
        )
        
        assert record.message.event_type == NotificationEventType.CERTIFICATION_DOWNGRADED
        assert "⚠️" in record.message.title
        assert record.message.priority == NotificationPriority.URGENT
        assert "PLATINUM" in record.message.content
        assert "GOLD" in record.message.content
        assert "15.0%" in record.message.content
        assert "近期表现下降" in record.message.content
    
    def test_get_notification_history_all(self, service):
        """测试查询所有通知历史"""
        # 发送多个通知
        service.notify_certification_started("STRAT-001", "策略A")
        service.notify_certification_started("STRAT-002", "策略B")
        service.notify_arena_completed("STRAT-001", "策略A", True, 0.85, {})
        
        history = service.get_notification_history()
        assert len(history) == 3
    
    def test_get_notification_history_by_strategy_id(self, service):
        """测试按策略ID查询通知历史"""
        service.notify_certification_started("STRAT-001", "策略A")
        service.notify_certification_started("STRAT-002", "策略B")
        service.notify_arena_completed("STRAT-001", "策略A", True, 0.85, {})
        
        history = service.get_notification_history(strategy_id="STRAT-001")
        assert len(history) == 2
        assert all(r.message.metadata['strategy_id'] == "STRAT-001" for r in history)
    
    def test_get_notification_history_by_event_type(self, service):
        """测试按事件类型查询通知历史"""
        service.notify_certification_started("STRAT-001", "策略A")
        service.notify_certification_started("STRAT-002", "策略B")
        service.notify_arena_completed("STRAT-001", "策略A", True, 0.85, {})
        
        history = service.get_notification_history(
            event_type=NotificationEventType.CERTIFICATION_STARTED
        )
        assert len(history) == 2
        assert all(r.message.event_type == NotificationEventType.CERTIFICATION_STARTED for r in history)
    
    def test_get_notification_history_by_date_range(self, service):
        """测试按日期范围查询通知历史"""
        now = datetime.now()
        
        # 发送通知
        service.notify_certification_started("STRAT-001", "策略A")
        
        # 查询今天的通知
        history = service.get_notification_history(
            start_date=now - timedelta(hours=1),
            end_date=now + timedelta(hours=1)
        )
        assert len(history) == 1
        
        # 查询未来的通知（应该为空）
        history = service.get_notification_history(
            start_date=now + timedelta(days=1)
        )
        assert len(history) == 0
    
    def test_get_notification_history_combined_filters(self, service):
        """测试组合过滤条件查询通知历史"""
        service.notify_certification_started("STRAT-001", "策略A")
        service.notify_certification_started("STRAT-002", "策略B")
        service.notify_arena_completed("STRAT-001", "策略A", True, 0.85, {})
        
        history = service.get_notification_history(
            strategy_id="STRAT-001",
            event_type=NotificationEventType.CERTIFICATION_STARTED
        )
        assert len(history) == 1
        assert history[0].message.metadata['strategy_id'] == "STRAT-001"
        assert history[0].message.event_type == NotificationEventType.CERTIFICATION_STARTED
    
    def test_message_id_generation(self, service):
        """测试消息ID生成"""
        record1 = service.notify_certification_started("STRAT-001", "策略A")
        record2 = service.notify_certification_started("STRAT-002", "策略B")
        
        assert record1.message_id == "NOTIF-000001"
        assert record2.message_id == "NOTIF-000002"
        assert record1.message_id != record2.message_id
    
    def test_notification_channels_disabled(self):
        """测试禁用通知渠道"""
        service = CertificationNotificationService(
            default_channels=[NotificationChannel.EMAIL, NotificationChannel.SMS],
            enable_email=False,
            enable_sms=False,
            enable_system=True
        )
        
        record = service.notify_certification_started("STRAT-001", "策略A")
        
        # 邮件和短信应该失败（因为被禁用）
        assert NotificationChannel.EMAIL in record.failed_channels
        assert NotificationChannel.SMS in record.failed_channels
    
    def test_notification_metadata_preservation(self, service):
        """测试通知元数据保留"""
        layer_results = {
            '第一层': {'passed': True, 'score': 0.95}
        }
        
        record = service.notify_arena_completed(
            strategy_id="STRAT-001",
            strategy_name="策略A",
            arena_passed=True,
            arena_score=0.90,
            layer_results=layer_results
        )
        
        # 验证元数据完整保留
        assert record.message.metadata['strategy_id'] == "STRAT-001"
        assert record.message.metadata['strategy_name'] == "策略A"
        assert record.message.metadata['arena_passed'] is True
        assert record.message.metadata['arena_score'] == 0.90
        assert record.message.metadata['layer_results'] == layer_results
    
    def test_notification_timestamp(self, service):
        """测试通知时间戳"""
        before = datetime.now()
        record = service.notify_certification_started("STRAT-001", "策略A")
        after = datetime.now()
        
        assert before <= record.message.timestamp <= after
        assert before <= record.sent_at <= after
    
    def test_format_failure_details_simple(self, service):
        """测试格式化简单失败详情"""
        details = {
            'metric1': 'value1',
            'metric2': 'value2'
        }
        
        formatted = service._format_failure_details(details)
        assert 'metric1: value1' in formatted
        assert 'metric2: value2' in formatted
    
    def test_format_failure_details_nested(self, service):
        """测试格式化嵌套失败详情"""
        details = {
            'metrics': {
                'sharpe': 1.0,
                'drawdown': 0.20
            },
            'threshold': {
                'min_sharpe': 1.5,
                'max_drawdown': 0.15
            }
        }
        
        formatted = service._format_failure_details(details)
        assert 'metrics:' in formatted
        assert 'sharpe: 1.0' in formatted
        assert 'threshold:' in formatted
        assert 'min_sharpe: 1.5' in formatted
    
    def test_format_failure_details_empty(self, service):
        """测试格式化空失败详情"""
        details = {}
        formatted = service._format_failure_details(details)
        assert '无详细信息' in formatted
    
    def test_multiple_channels_success(self, service):
        """测试多渠道发送成功"""
        channels = [
            NotificationChannel.EMAIL,
            NotificationChannel.SMS,
            NotificationChannel.SYSTEM
        ]
        
        record = service.notify_certification_started(
            strategy_id="STRAT-001",
            strategy_name="策略A",
            channels=channels
        )
        
        assert len(record.sent_channels) == 3
        assert len(record.failed_channels) == 0
        assert record.status == 'success'
    
    def test_notification_priority_levels(self, service):
        """测试不同优先级的通知"""
        # NORMAL优先级
        record1 = service.notify_certification_started("STRAT-001", "策略A")
        assert record1.message.priority == NotificationPriority.NORMAL
        
        # HIGH优先级
        record2 = service.notify_certification_granted(
            "STRAT-002", "策略B", "platinum", 0.20, 0.92, {}
        )
        assert record2.message.priority == NotificationPriority.HIGH
        
        # URGENT优先级
        record3 = service.notify_certification_revoked(
            "STRAT-003", "策略C", "表现不达标", "gold"
        )
        assert record3.message.priority == NotificationPriority.URGENT
    
    def test_notification_content_completeness(self, service):
        """测试通知内容完整性"""
        record = service.notify_certification_granted(
            strategy_id="STRAT-001",
            strategy_name="测试策略",
            certification_level="platinum",
            max_allocation_ratio=0.20,
            arena_score=0.92,
            simulation_metrics={
                'sharpe_ratio': 3.0,
                'max_drawdown': 0.08,
                'win_rate': 0.70
            }
        )
        
        content = record.message.content
        
        # 验证所有关键信息都在内容中
        assert "测试策略" in content
        assert "STRAT-001" in content
        assert "PLATINUM" in content
        assert "20.0%" in content
        assert "0.92" in content
        assert "3.00" in content
        assert "8.00%" in content
        assert "70.00%" in content
    
    def test_certification_level_emoji_unknown(self, service):
        """测试未知认证等级的emoji"""
        record = service.notify_certification_granted(
            strategy_id="STRAT-001",
            strategy_name="测试策略",
            certification_level="unknown",
            max_allocation_ratio=0.10,
            arena_score=0.75,
            simulation_metrics={}
        )
        
        # 未知等级应该使用默认emoji
        assert "✅" in record.message.title
    
    def test_send_notification_with_exception(self):
        """测试发送通知时的异常处理"""
        # 创建一个会抛出异常的服务
        service = CertificationNotificationService(
            default_channels=[NotificationChannel.EMAIL],
            enable_email=True
        )
        
        # 模拟发送失败的情况（通过禁用渠道）
        service.enable_email = False
        
        record = service.notify_certification_started("STRAT-001", "策略A")
        
        # 应该记录失败的渠道
        assert NotificationChannel.EMAIL in record.failed_channels
        assert record.status == 'failed'
    
    def test_notification_history_empty_filters(self, service):
        """测试空过滤条件查询"""
        service.notify_certification_started("STRAT-001", "策略A")
        
        # 使用None作为所有过滤条件
        history = service.get_notification_history(
            strategy_id=None,
            event_type=None,
            start_date=None,
            end_date=None
        )
        
        assert len(history) == 1
    
    def test_simulation_metrics_with_non_float_values(self, service):
        """测试包含非浮点数值的模拟盘指标"""
        overall_metrics = {
            'sharpe_ratio': 2.5,
            'status': 'passed',  # 非浮点数
            'trade_count': 150   # 整数
        }
        
        record = service.notify_simulation_completed(
            strategy_id="STRAT-001",
            strategy_name="策略A",
            simulation_passed=True,
            duration_days=30,
            best_tier="Tier 2",
            overall_metrics=overall_metrics
        )
        
        # 验证非浮点数值也能正确处理
        assert 'status: passed' in record.message.content
        assert 'trade_count: 150' in record.message.content
    
    def test_all_channel_methods_called(self, service):
        """测试所有渠道发送方法被调用"""
        # 测试所有渠道
        channels = [
            NotificationChannel.EMAIL,
            NotificationChannel.SMS,
            NotificationChannel.SYSTEM,
            NotificationChannel.WECHAT
        ]
        
        record = service.notify_certification_started(
            strategy_id="STRAT-001",
            strategy_name="策略A",
            channels=channels
        )
        
        # 所有渠道都应该成功发送
        assert len(record.sent_channels) == 4
        assert NotificationChannel.EMAIL in record.sent_channels
        assert NotificationChannel.SMS in record.sent_channels
        assert NotificationChannel.SYSTEM in record.sent_channels
        assert NotificationChannel.WECHAT in record.sent_channels
    
    def test_get_notification_history_end_date_filter(self, service):
        """测试按结束日期过滤通知历史"""
        now = datetime.now()
        
        # 发送通知
        service.notify_certification_started("STRAT-001", "策略A")
        
        # 查询过去的通知（应该为空）
        history = service.get_notification_history(
            end_date=now - timedelta(hours=1)
        )
        assert len(history) == 0
        
        # 查询未来的通知（应该有结果）
        history = service.get_notification_history(
            end_date=now + timedelta(hours=1)
        )
        assert len(history) == 1
    
    def test_send_notification_with_real_exception(self, service):
        """测试发送通知时的真实异常"""
        # 创建一个会抛出异常的mock服务
        import unittest.mock as mock
        
        # Mock _send_email方法使其抛出异常
        with mock.patch.object(service, '_send_email', side_effect=Exception("Email service error")):
            record = service.notify_certification_started(
                strategy_id="STRAT-001",
                strategy_name="策略A",
                channels=[NotificationChannel.EMAIL]
            )
            
            # 邮件渠道应该失败
            assert NotificationChannel.EMAIL in record.failed_channels
            assert len(record.sent_channels) == 0
            assert record.status == 'failed'
    
    def test_send_notification_partial_failure(self, service):
        """测试部分渠道发送失败"""
        import unittest.mock as mock
        
        # Mock _send_email方法使其抛出异常，但其他渠道正常
        with mock.patch.object(service, '_send_email', side_effect=Exception("Email error")):
            record = service.notify_certification_started(
                strategy_id="STRAT-001",
                strategy_name="策略A",
                channels=[NotificationChannel.EMAIL, NotificationChannel.SYSTEM]
            )
            
            # 邮件失败，系统消息成功
            assert NotificationChannel.EMAIL in record.failed_channels
            assert NotificationChannel.SYSTEM in record.sent_channels
            assert record.status == 'success'  # 至少有一个渠道成功
