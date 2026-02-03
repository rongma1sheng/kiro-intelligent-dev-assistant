"""NetworkGuard属性测试

白皮书依据: 第七章 7.4 网络防护

使用Property-Based Testing验证NetworkGuard的通用属性。

Author: MIA Team
Date: 2026-01-25
Version: 1.0.0
"""

import pytest
from hypothesis import given, strategies as st, assume, settings
from unittest.mock import Mock

from src.compliance.network_guard import NetworkGuard


# 策略定义
@st.composite
def whitelisted_domain(draw):
    """生成白名单域名"""
    domains = ['pypi.org', 'files.pythonhosted.org']
    return draw(st.sampled_from(domains))


@st.composite
def whitelisted_subdomain(draw):
    """生成白名单子域名"""
    prefix = draw(st.text(
        alphabet=st.characters(whitelist_categories=('Ll', 'Nd'), min_codepoint=97, max_codepoint=122),
        min_size=1,
        max_size=10
    ))
    base_domain = draw(whitelisted_domain())
    return f"{prefix}.{base_domain}"


@st.composite
def blacklisted_ip(draw):
    """生成黑名单IP地址"""
    ip_ranges = [
        ('10', st.integers(0, 255), st.integers(0, 255), st.integers(0, 255)),
        ('172', st.integers(16, 31), st.integers(0, 255), st.integers(0, 255)),
        ('192', st.integers(168, 168), st.integers(0, 255), st.integers(0, 255)),
        ('169', st.integers(254, 254), st.integers(169, 169), st.integers(254, 254)),
        ('127', st.integers(0, 255), st.integers(0, 255), st.integers(0, 255)),
    ]
    
    first_octet, second_range, third_range, fourth_range = draw(st.sampled_from(ip_ranges))
    second = draw(second_range)
    third = draw(third_range)
    fourth = draw(fourth_range)
    
    return f"{first_octet}.{second}.{third}.{fourth}"


@st.composite
def non_whitelisted_domain(draw):
    """生成非白名单域名"""
    # 生成随机域名，确保不是白名单域名
    tld = draw(st.sampled_from(['com', 'net', 'org', 'io', 'dev']))
    name = draw(st.text(
        alphabet=st.characters(whitelist_categories=('Ll', 'Nd'), min_codepoint=97, max_codepoint=122),
        min_size=3,
        max_size=15
    ))
    domain = f"{name}.{tld}"
    
    # 确保不是白名单域名或其子域名
    assume(domain not in ['pypi.org', 'files.pythonhosted.org'])
    assume(not domain.endswith('.pypi.org'))
    assume(not domain.endswith('.files.pythonhosted.org'))
    
    return domain


class TestNetworkGuardProperties:
    """NetworkGuard属性测试"""
    
    @given(domain=whitelisted_domain())
    @settings(max_examples=100)
    def test_property_17_whitelist_domain_allowance(self, domain):
        """Property 17: Network Domain Whitelist
        
        白皮书依据: 第七章 7.4 网络防护
        Validates: Requirements 11.2
        
        *For any* network access request to a whitelisted domain 
        (pypi.org, files.pythonhosted.org), the NetworkGuard SHALL 
        allow the request.
        """
        # Feature: chapter-7-security-and-chapter-6-tests, Property 17: Network Domain Whitelist
        
        guard = NetworkGuard()
        
        result = guard.check_access(domain)
        
        assert result.allowed, (
            f"白名单域名应该被允许: {domain}, "
            f"但被拒绝，原因: {result.reason}"
        )
        assert result.target == domain.lower()
        assert result.rule_matched in ['whitelist_exact', 'whitelist_subdomain']
    
    @given(subdomain=whitelisted_subdomain())
    @settings(max_examples=100)
    def test_property_17_whitelist_subdomain_allowance(self, subdomain):
        """Property 17: Network Domain Whitelist (子域名)
        
        白皮书依据: 第七章 7.4 网络防护
        Validates: Requirements 11.2
        
        *For any* subdomain of a whitelisted domain, the NetworkGuard 
        SHALL allow the request.
        """
        # Feature: chapter-7-security-and-chapter-6-tests, Property 17: Network Domain Whitelist
        
        guard = NetworkGuard()
        
        result = guard.check_access(subdomain)
        
        assert result.allowed, (
            f"白名单子域名应该被允许: {subdomain}, "
            f"但被拒绝，原因: {result.reason}"
        )
        assert result.rule_matched == 'whitelist_subdomain'
    
    @given(
        domain=whitelisted_domain(),
        path=st.text(
            alphabet=st.characters(whitelist_categories=('Ll', 'Nd', 'P'), min_codepoint=32, max_codepoint=126),
            min_size=0,
            max_size=50
        )
    )
    @settings(max_examples=100)
    def test_property_17_whitelist_url_allowance(self, domain, path):
        """Property 17: Network Domain Whitelist (URL)
        
        白皮书依据: 第七章 7.4 网络防护
        Validates: Requirements 11.2
        
        *For any* URL with a whitelisted domain, the NetworkGuard 
        SHALL allow the request.
        """
        # Feature: chapter-7-security-and-chapter-6-tests, Property 17: Network Domain Whitelist
        
        guard = NetworkGuard()
        
        # 构建URL
        url = f"https://{domain}/{path}"
        
        result = guard.check_access(url)
        
        assert result.allowed, (
            f"白名单URL应该被允许: {url}, "
            f"但被拒绝，原因: {result.reason}"
        )
    
    @given(ip=blacklisted_ip())
    @settings(max_examples=100)
    def test_property_18_ip_range_blocking(self, ip):
        """Property 18: Network IP Range Blocking
        
        白皮书依据: 第七章 7.4 网络防护
        Validates: Requirements 11.3
        
        *For any* network access request to an IP in blocked ranges 
        (10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16, 169.254.169.254/32, 
        127.0.0.0/8), the NetworkGuard SHALL block the request.
        """
        # Feature: chapter-7-security-and-chapter-6-tests, Property 18: Network IP Range Blocking
        
        guard = NetworkGuard()
        
        result = guard.check_access(ip)
        
        assert not result.allowed, (
            f"黑名单IP应该被阻止: {ip}, "
            f"但被允许"
        )
        assert '黑名单段' in result.reason
        assert result.rule_matched == 'blacklist_ip_range'
    
    @given(
        ip=blacklisted_ip(),
        path=st.text(
            alphabet=st.characters(whitelist_categories=('Ll', 'Nd', 'P'), min_codepoint=32, max_codepoint=126),
            min_size=0,
            max_size=30
        )
    )
    @settings(max_examples=100)
    def test_property_18_ip_range_blocking_in_url(self, ip, path):
        """Property 18: Network IP Range Blocking (URL中的IP)
        
        白皮书依据: 第七章 7.4 网络防护
        Validates: Requirements 11.3
        
        *For any* URL containing a blacklisted IP, the NetworkGuard 
        SHALL block the request.
        """
        # Feature: chapter-7-security-and-chapter-6-tests, Property 18: Network IP Range Blocking
        
        guard = NetworkGuard()
        
        # 构建URL
        url = f"http://{ip}/{path}"
        
        result = guard.check_access(url)
        
        assert not result.allowed, (
            f"包含黑名单IP的URL应该被阻止: {url}, "
            f"但被允许"
        )
        assert '黑名单段' in result.reason
    
    @given(domain=non_whitelisted_domain())
    @settings(max_examples=100)
    def test_default_deny_policy(self, domain):
        """默认拒绝策略
        
        白皮书依据: 第七章 7.4 网络防护
        Validates: Requirements 11.1
        
        *For any* domain not in the whitelist, the NetworkGuard 
        SHALL deny the request by default.
        """
        # Feature: chapter-7-security-and-chapter-6-tests, Default Deny Policy
        
        guard = NetworkGuard()
        
        result = guard.check_access(domain)
        
        assert not result.allowed, (
            f"非白名单域名应该被拒绝: {domain}, "
            f"但被允许"
        )
        assert '不在白名单' in result.reason or '默认拒绝' in result.reason
    
    @given(
        domain=whitelisted_domain(),
        case_variant=st.sampled_from(['lower', 'upper', 'mixed'])
    )
    @settings(max_examples=100)
    def test_case_insensitive_whitelist(self, domain, case_variant):
        """大小写不敏感的白名单
        
        白皮书依据: 第七章 7.4 网络防护
        Validates: Requirements 11.2
        
        *For any* case variant of a whitelisted domain, the NetworkGuard 
        SHALL allow the request (case-insensitive matching).
        """
        # Feature: chapter-7-security-and-chapter-6-tests, Case Insensitive Whitelist
        
        guard = NetworkGuard()
        
        # 转换大小写
        if case_variant == 'lower':
            test_domain = domain.lower()
        elif case_variant == 'upper':
            test_domain = domain.upper()
        else:  # mixed
            test_domain = ''.join(
                c.upper() if i % 2 == 0 else c.lower()
                for i, c in enumerate(domain)
            )
        
        result = guard.check_access(test_domain)
        
        assert result.allowed, (
            f"白名单域名的大小写变体应该被允许: {test_domain}, "
            f"但被拒绝，原因: {result.reason}"
        )
    
    @given(
        domain=whitelisted_domain(),
        context=st.text(min_size=1, max_size=50)
    )
    @settings(max_examples=50)
    def test_logging_completeness(self, domain, context):
        """日志记录完整性
        
        白皮书依据: 第七章 7.4 网络防护
        Validates: Requirements 11.4
        
        *For any* network access check, the NetworkGuard SHALL log 
        the access attempt with complete information.
        """
        # Feature: chapter-7-security-and-chapter-6-tests, Logging Completeness
        
        mock_logger = Mock()
        guard = NetworkGuard(audit_logger=mock_logger)
        
        guard.check_access(domain, context=context)
        
        # 验证日志被调用
        assert mock_logger.log_event.called, "应该记录访问日志"
        
        # 验证日志内容完整性
        call_args = mock_logger.log_event.call_args[0][0]
        assert 'event_type' in call_args
        assert 'target' in call_args
        assert 'allowed' in call_args
        assert 'reason' in call_args
        assert 'context' in call_args
        assert call_args['event_type'] == 'NETWORK_ACCESS'
        assert call_args['target'] == domain.lower()
        assert call_args['context'] == context
    
    @given(domain=non_whitelisted_domain())
    @settings(max_examples=50)
    def test_alert_on_violation(self, domain):
        """违规告警
        
        白皮书依据: 第七章 7.4 网络防护
        Validates: Requirements 11.5
        
        *For any* denied network access, the NetworkGuard SHALL 
        send an alert.
        """
        # Feature: chapter-7-security-and-chapter-6-tests, Alert on Violation
        
        mock_callback = Mock()
        guard = NetworkGuard(alert_callback=mock_callback)
        
        result = guard.check_access(domain)
        
        # 验证访问被拒绝
        assert not result.allowed
        
        # 验证告警被发送
        assert mock_callback.called, "应该发送违规告警"
        
        # 验证告警内容
        alert_message = mock_callback.call_args[0][0]
        assert '网络访问违规' in alert_message
        assert domain in alert_message
    
    @given(
        domain=whitelisted_domain(),
        check_count=st.integers(min_value=1, max_value=10)
    )
    @settings(max_examples=50)
    def test_idempotence(self, domain, check_count):
        """幂等性
        
        白皮书依据: 第七章 7.4 网络防护
        
        *For any* domain, multiple checks SHALL produce the same result.
        """
        # Feature: chapter-7-security-and-chapter-6-tests, Idempotence
        
        guard = NetworkGuard()
        
        results = [guard.check_access(domain) for _ in range(check_count)]
        
        # 所有结果应该一致
        first_result = results[0]
        for result in results[1:]:
            assert result.allowed == first_result.allowed, (
                f"多次检查应该产生相同结果: {domain}"
            )
            assert result.rule_matched == first_result.rule_matched


class TestNetworkGuardPropertyEdgeCases:
    """NetworkGuard属性测试边界情况"""
    
    @given(
        ip_parts=st.lists(
            st.integers(min_value=0, max_value=255),
            min_size=4,
            max_size=4
        )
    )
    @settings(max_examples=100)
    def test_all_ips_checked(self, ip_parts):
        """所有IP都被检查
        
        验证所有有效的IPv4地址都能被正确处理。
        """
        # Feature: chapter-7-security-and-chapter-6-tests, All IPs Checked
        
        guard = NetworkGuard()
        
        ip = '.'.join(str(part) for part in ip_parts)
        
        # 不应该抛出异常
        result = guard.check_access(ip)
        
        # 结果应该是有效的
        assert isinstance(result.allowed, bool)
        assert isinstance(result.reason, str)
        assert isinstance(result.target, str)
    
    @given(
        domain=st.text(
            alphabet=st.characters(whitelist_categories=('Ll', 'Nd'), min_codepoint=97, max_codepoint=122),
            min_size=1,
            max_size=253  # DNS最大长度
        )
    )
    @settings(max_examples=50)
    def test_all_domains_handled(self, domain):
        """所有域名都被处理
        
        验证所有可能的域名字符串都能被正确处理。
        """
        # Feature: chapter-7-security-and-chapter-6-tests, All Domains Handled
        
        guard = NetworkGuard()
        
        # 添加.com后缀使其成为有效域名
        test_domain = f"{domain}.com"
        
        # 不应该抛出异常
        result = guard.check_access(test_domain)
        
        # 结果应该是有效的
        assert isinstance(result.allowed, bool)
        assert isinstance(result.reason, str)
