"""NetworkGuard单元测试

白皮书依据: 第七章 7.4 网络防护

测试NetworkGuard的网络访问控制功能。

Author: MIA Team
Date: 2026-01-25
Version: 1.0.0
"""

import pytest
from unittest.mock import Mock, MagicMock

from src.compliance.network_guard import (
    NetworkGuard,
    NetworkAccessResult,
    NetworkViolationError,
)


class TestNetworkGuardInitialization:
    """测试NetworkGuard初始化"""
    
    def test_default_initialization(self):
        """测试默认初始化"""
        guard = NetworkGuard()
        
        assert 'pypi.org' in guard.whitelist_domains
        assert 'files.pythonhosted.org' in guard.whitelist_domains
        assert len(guard.blacklist_ip_ranges) == 5
        assert guard.audit_logger is None
        assert guard.alert_callback is None
    
    def test_custom_whitelist(self):
        """测试自定义白名单"""
        custom_domains = {'example.com', 'test.org'}
        guard = NetworkGuard(whitelist_domains=custom_domains)
        
        assert guard.whitelist_domains == custom_domains
        assert 'pypi.org' not in guard.whitelist_domains
    
    def test_custom_blacklist(self):
        """测试自定义黑名单"""
        custom_ranges = ['192.168.1.0/24', '10.0.0.0/8']
        guard = NetworkGuard(blacklist_ip_ranges=custom_ranges)
        
        assert len(guard.blacklist_ip_ranges) == 2
    
    def test_with_audit_logger(self):
        """测试带审计日志"""
        mock_logger = Mock()
        guard = NetworkGuard(audit_logger=mock_logger)
        
        assert guard.audit_logger is mock_logger
    
    def test_with_alert_callback(self):
        """测试带告警回调"""
        mock_callback = Mock()
        guard = NetworkGuard(alert_callback=mock_callback)
        
        assert guard.alert_callback is mock_callback
    
    def test_invalid_ip_range_in_blacklist(self):
        """测试无效的IP段"""
        # 应该忽略无效的IP段，不抛出异常
        guard = NetworkGuard(blacklist_ip_ranges=['invalid', '10.0.0.0/8'])
        
        # 只有有效的IP段被添加
        assert len(guard.blacklist_ip_ranges) == 1


class TestNetworkGuardDefaultDeny:
    """测试默认拒绝策略
    
    Requirement: 11.1 默认拒绝所有网络访问
    """
    
    def test_deny_unknown_domain(self):
        """测试拒绝未知域名"""
        guard = NetworkGuard()
        
        result = guard.check_access('unknown.com')
        
        assert not result.allowed
        assert '默认拒绝' in result.reason or '不在白名单' in result.reason
        assert result.target == 'unknown.com'
    
    def test_deny_unknown_url(self):
        """测试拒绝未知URL"""
        guard = NetworkGuard()
        
        result = guard.check_access('https://unknown.com/path')
        
        assert not result.allowed
        assert '不在白名单' in result.reason
    
    def test_deny_empty_target(self):
        """测试拒绝空目标"""
        guard = NetworkGuard()
        
        with pytest.raises(ValueError, match="访问目标不能为空"):
            guard.check_access('')
    
    def test_deny_whitespace_target(self):
        """测试拒绝空白目标"""
        guard = NetworkGuard()
        
        with pytest.raises(ValueError, match="访问目标不能为空"):
            guard.check_access('   ')


class TestNetworkGuardWhitelist:
    """测试白名单域名允许
    
    Requirement: 11.2 允许白名单域名
    """
    
    def test_allow_whitelisted_domain(self):
        """测试允许白名单域名"""
        guard = NetworkGuard()
        
        result = guard.check_access('pypi.org')
        
        assert result.allowed
        assert result.target == 'pypi.org'
        assert result.rule_matched == 'whitelist_exact'
    
    def test_allow_whitelisted_domain_case_insensitive(self):
        """测试白名单域名大小写不敏感"""
        guard = NetworkGuard()
        
        result = guard.check_access('PyPI.ORG')
        
        assert result.allowed
        assert result.target == 'pypi.org'
    
    def test_allow_whitelisted_subdomain(self):
        """测试允许白名单子域名"""
        guard = NetworkGuard()
        
        result = guard.check_access('cdn.pypi.org')
        
        assert result.allowed
        assert result.rule_matched == 'whitelist_subdomain'
    
    def test_allow_whitelisted_url(self):
        """测试允许白名单URL"""
        guard = NetworkGuard()
        
        result = guard.check_access('https://pypi.org/simple/')
        
        assert result.allowed
    
    def test_allow_files_pythonhosted(self):
        """测试允许files.pythonhosted.org"""
        guard = NetworkGuard()
        
        result = guard.check_access('files.pythonhosted.org')
        
        assert result.allowed
    
    def test_deny_similar_domain(self):
        """测试拒绝相似但不同的域名"""
        guard = NetworkGuard()
        
        result = guard.check_access('pypi.org.evil.com')
        
        assert not result.allowed


class TestNetworkGuardIPBlacklist:
    """测试IP黑名单阻止
    
    Requirement: 11.3 阻止黑名单IP段
    """
    
    def test_block_private_network_class_a(self):
        """测试阻止A类私有网络"""
        guard = NetworkGuard()
        
        result = guard.check_access('10.0.0.1')
        
        assert not result.allowed
        assert '黑名单段' in result.reason
        assert '10.0.0.0/8' in result.reason
    
    def test_block_private_network_class_b(self):
        """测试阻止B类私有网络"""
        guard = NetworkGuard()
        
        result = guard.check_access('172.16.0.1')
        
        assert not result.allowed
        assert '黑名单段' in result.reason
    
    def test_block_private_network_class_c(self):
        """测试阻止C类私有网络"""
        guard = NetworkGuard()
        
        result = guard.check_access('192.168.1.1')
        
        assert not result.allowed
        assert '黑名单段' in result.reason
    
    def test_block_metadata_service(self):
        """测试阻止云元数据服务"""
        guard = NetworkGuard()
        
        result = guard.check_access('169.254.169.254')
        
        assert not result.allowed
        assert '黑名单段' in result.reason
    
    def test_block_localhost(self):
        """测试阻止本地回环"""
        guard = NetworkGuard()
        
        result = guard.check_access('127.0.0.1')
        
        assert not result.allowed
        assert '黑名单段' in result.reason
    
    def test_block_ip_in_url(self):
        """测试阻止URL中的IP"""
        guard = NetworkGuard()
        
        result = guard.check_access('http://192.168.1.1/api')
        
        assert not result.allowed
        assert '黑名单段' in result.reason
    
    def test_public_ip_requires_domain(self):
        """测试公网IP需要域名验证"""
        guard = NetworkGuard()
        
        result = guard.check_access('8.8.8.8')
        
        assert not result.allowed
        assert '需要域名白名单验证' in result.reason


class TestNetworkGuardLogging:
    """测试日志记录
    
    Requirement: 11.4 记录所有网络访问尝试
    """
    
    def test_log_allowed_access(self):
        """测试记录允许的访问"""
        mock_logger = Mock()
        guard = NetworkGuard(audit_logger=mock_logger)
        
        guard.check_access('pypi.org', context='test_context')
        
        mock_logger.log_event.assert_called_once()
        call_args = mock_logger.log_event.call_args[0][0]
        assert call_args['event_type'] == 'NETWORK_ACCESS'
        assert call_args['target'] == 'pypi.org'
        assert call_args['allowed'] is True
        assert call_args['context'] == 'test_context'
    
    def test_log_denied_access(self):
        """测试记录拒绝的访问"""
        mock_logger = Mock()
        guard = NetworkGuard(audit_logger=mock_logger)
        
        guard.check_access('evil.com', context='test_context')
        
        mock_logger.log_event.assert_called_once()
        call_args = mock_logger.log_event.call_args[0][0]
        assert call_args['allowed'] is False
    
    def test_log_without_context(self):
        """测试无上下文的日志记录"""
        mock_logger = Mock()
        guard = NetworkGuard(audit_logger=mock_logger)
        
        guard.check_access('pypi.org')
        
        mock_logger.log_event.assert_called_once()
        call_args = mock_logger.log_event.call_args[0][0]
        assert call_args['context'] == 'unknown'
    
    def test_log_failure_does_not_raise(self):
        """测试日志记录失败不抛出异常"""
        mock_logger = Mock()
        mock_logger.log_event.side_effect = Exception("日志失败")
        guard = NetworkGuard(audit_logger=mock_logger)
        
        # 不应该抛出异常
        result = guard.check_access('pypi.org')
        assert result.allowed


class TestNetworkGuardAlerts:
    """测试告警发送
    
    Requirement: 11.5 发送违规告警
    """
    
    def test_send_alert_on_violation(self):
        """测试违规时发送告警"""
        mock_callback = Mock()
        guard = NetworkGuard(alert_callback=mock_callback)
        
        guard.check_access('evil.com')
        
        mock_callback.assert_called_once()
        alert_message = mock_callback.call_args[0][0]
        assert '网络访问违规' in alert_message
        assert 'evil.com' in alert_message
    
    def test_send_alert_on_ip_blacklist(self):
        """测试IP黑名单违规告警"""
        mock_callback = Mock()
        guard = NetworkGuard(alert_callback=mock_callback)
        
        guard.check_access('192.168.1.1')
        
        mock_callback.assert_called_once()
        alert_message = mock_callback.call_args[0][0]
        assert '192.168.1.1' in alert_message
    
    def test_no_alert_on_allowed_access(self):
        """测试允许访问不发送告警"""
        mock_callback = Mock()
        guard = NetworkGuard(alert_callback=mock_callback)
        
        guard.check_access('pypi.org')
        
        mock_callback.assert_not_called()
    
    def test_alert_with_context(self):
        """测试带上下文的告警"""
        mock_callback = Mock()
        guard = NetworkGuard(alert_callback=mock_callback)
        
        guard.check_access('evil.com', context='test_module')
        
        alert_message = mock_callback.call_args[0][0]
        assert 'test_module' in alert_message
    
    def test_alert_failure_does_not_raise(self):
        """测试告警失败不抛出异常"""
        mock_callback = Mock()
        mock_callback.side_effect = Exception("告警失败")
        guard = NetworkGuard(alert_callback=mock_callback)
        
        # 不应该抛出异常
        result = guard.check_access('evil.com')
        assert not result.allowed


class TestNetworkGuardDomainManagement:
    """测试域名管理"""
    
    def test_add_whitelist_domain(self):
        """测试添加白名单域名"""
        guard = NetworkGuard()
        
        guard.add_whitelist_domain('example.com')
        
        assert 'example.com' in guard.whitelist_domains
        result = guard.check_access('example.com')
        assert result.allowed
    
    def test_add_whitelist_domain_case_normalization(self):
        """测试添加域名时大小写规范化"""
        guard = NetworkGuard()
        
        guard.add_whitelist_domain('Example.COM')
        
        assert 'example.com' in guard.whitelist_domains
    
    def test_add_whitelist_domain_empty(self):
        """测试添加空域名"""
        guard = NetworkGuard()
        
        with pytest.raises(ValueError, match="域名不能为空"):
            guard.add_whitelist_domain('')
    
    def test_add_whitelist_domain_invalid_format(self):
        """测试添加无效格式域名"""
        guard = NetworkGuard()
        
        with pytest.raises(ValueError, match="无效的域名格式"):
            guard.add_whitelist_domain('invalid domain!')
    
    def test_remove_whitelist_domain(self):
        """测试移除白名单域名"""
        guard = NetworkGuard()
        guard.add_whitelist_domain('example.com')
        
        guard.remove_whitelist_domain('example.com')
        
        assert 'example.com' not in guard.whitelist_domains
    
    def test_remove_nonexistent_domain(self):
        """测试移除不存在的域名"""
        guard = NetworkGuard()
        
        with pytest.raises(ValueError, match="域名不在白名单中"):
            guard.remove_whitelist_domain('nonexistent.com')
    
    def test_add_blacklist_ip_range(self):
        """测试添加黑名单IP段"""
        guard = NetworkGuard()
        initial_count = len(guard.blacklist_ip_ranges)
        
        guard.add_blacklist_ip_range('203.0.113.0/24')
        
        assert len(guard.blacklist_ip_ranges) == initial_count + 1
        result = guard.check_access('203.0.113.1')
        assert not result.allowed
    
    def test_add_blacklist_ip_range_invalid(self):
        """测试添加无效IP段"""
        guard = NetworkGuard()
        
        with pytest.raises(ValueError, match="无效的IP段格式"):
            guard.add_blacklist_ip_range('invalid')


class TestNetworkGuardConfiguration:
    """测试配置获取"""
    
    def test_get_config(self):
        """测试获取配置"""
        guard = NetworkGuard()
        
        config = guard.get_config()
        
        assert 'whitelist_domains' in config
        assert 'blacklist_ip_ranges' in config
        assert 'audit_logger_enabled' in config
        assert 'alert_callback_enabled' in config
        assert isinstance(config['whitelist_domains'], list)
        assert isinstance(config['blacklist_ip_ranges'], list)
    
    def test_get_config_with_logger(self):
        """测试带日志的配置"""
        mock_logger = Mock()
        guard = NetworkGuard(audit_logger=mock_logger)
        
        config = guard.get_config()
        
        assert config['audit_logger_enabled'] is True
    
    def test_get_config_with_callback(self):
        """测试带回调的配置"""
        mock_callback = Mock()
        guard = NetworkGuard(alert_callback=mock_callback)
        
        config = guard.get_config()
        
        assert config['alert_callback_enabled'] is True


class TestNetworkGuardEdgeCases:
    """测试边界情况"""
    
    def test_url_with_port(self):
        """测试带端口的URL"""
        guard = NetworkGuard()
        
        result = guard.check_access('https://pypi.org:443/simple/')
        
        assert result.allowed
    
    def test_url_with_query_params(self):
        """测试带查询参数的URL"""
        guard = NetworkGuard()
        
        result = guard.check_access('https://pypi.org/search?q=numpy')
        
        assert result.allowed
    
    def test_url_with_fragment(self):
        """测试带片段的URL"""
        guard = NetworkGuard()
        
        result = guard.check_access('https://pypi.org/project/numpy/#description')
        
        assert result.allowed
    
    def test_ipv4_address_direct(self):
        """测试直接IPv4地址"""
        guard = NetworkGuard()
        
        result = guard.check_access('8.8.8.8')
        
        assert not result.allowed
    
    def test_multiple_subdomain_levels(self):
        """测试多级子域名"""
        guard = NetworkGuard()
        
        result = guard.check_access('cdn.api.pypi.org')
        
        assert result.allowed
    
    def test_domain_with_hyphen(self):
        """测试带连字符的域名"""
        guard = NetworkGuard()
        guard.add_whitelist_domain('my-domain.com')
        
        result = guard.check_access('my-domain.com')
        
        assert result.allowed
    
    def test_domain_with_numbers(self):
        """测试带数字的域名"""
        guard = NetworkGuard()
        guard.add_whitelist_domain('domain123.com')
        
        result = guard.check_access('domain123.com')
        
        assert result.allowed


class TestNetworkGuardIntegration:
    """测试集成场景"""
    
    def test_full_workflow_allowed(self):
        """测试完整的允许流程"""
        mock_logger = Mock()
        mock_callback = Mock()
        guard = NetworkGuard(
            audit_logger=mock_logger,
            alert_callback=mock_callback
        )
        
        result = guard.check_access('https://pypi.org/simple/', context='pip_install')
        
        assert result.allowed
        mock_logger.log_event.assert_called_once()
        mock_callback.assert_not_called()
    
    def test_full_workflow_denied(self):
        """测试完整的拒绝流程"""
        mock_logger = Mock()
        mock_callback = Mock()
        guard = NetworkGuard(
            audit_logger=mock_logger,
            alert_callback=mock_callback
        )
        
        result = guard.check_access('https://evil.com/malware', context='suspicious_code')
        
        assert not result.allowed
        mock_logger.log_event.assert_called_once()
        mock_callback.assert_called_once()
    
    def test_multiple_checks(self):
        """测试多次检查"""
        guard = NetworkGuard()
        
        results = [
            guard.check_access('pypi.org'),
            guard.check_access('evil.com'),
            guard.check_access('192.168.1.1'),
            guard.check_access('files.pythonhosted.org'),
        ]
        
        assert results[0].allowed
        assert not results[1].allowed
        assert not results[2].allowed
        assert results[3].allowed
