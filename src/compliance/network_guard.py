"""网络防护

白皮书依据: 第七章 7.4 网络防护

NetworkGuard提供网络访问控制，实现：
- 默认拒绝策略
- 白名单域名允许
- 黑名单IP段阻止
- 访问日志记录
- 违规告警发送

Author: MIA Team
Date: 2026-01-25
Version: 1.0.0
"""

import ipaddress
import re
from dataclasses import dataclass
from typing import List, Optional, Set
from urllib.parse import urlparse

from loguru import logger


@dataclass
class NetworkAccessResult:
    """网络访问结果

    白皮书依据: 第七章 7.4 网络防护

    Attributes:
        allowed: 是否允许访问
        reason: 拒绝原因（如果被拒绝）
        target: 访问目标（域名或IP）
        rule_matched: 匹配的规则类型
    """

    allowed: bool
    reason: str = ""
    target: str = ""
    rule_matched: str = ""


class NetworkViolationError(Exception):
    """网络访问违规错误

    白皮书依据: 第七章 7.4 网络防护
    """


class NetworkGuard:
    """网络防护

    白皮书依据: 第七章 7.4 网络防护

    提供网络访问控制，默认拒绝所有访问，仅允许白名单域名。

    Requirements:
    - 11.1: 默认拒绝所有网络访问
    - 11.2: 允许白名单域名（pypi.org, files.pythonhosted.org）
    - 11.3: 阻止黑名单IP段（内网IP、元数据服务）
    - 11.4: 记录所有网络访问尝试
    - 11.5: 发送违规告警

    Attributes:
        whitelist_domains: 白名单域名集合
        blacklist_ip_ranges: 黑名单IP段列表
        audit_logger: 审计日志记录器（可选）
        alert_callback: 告警回调函数（可选）
    """

    # 默认白名单域名
    DEFAULT_WHITELIST_DOMAINS = {
        "pypi.org",
        "files.pythonhosted.org",
    }

    # 默认黑名单IP段
    DEFAULT_BLACKLIST_IP_RANGES = [
        "10.0.0.0/8",  # 私有网络A类
        "172.16.0.0/12",  # 私有网络B类
        "192.168.0.0/16",  # 私有网络C类
        "169.254.169.254/32",  # AWS/云元数据服务
        "127.0.0.0/8",  # 本地回环
    ]

    def __init__(
        self,
        whitelist_domains: Optional[Set[str]] = None,
        blacklist_ip_ranges: Optional[List[str]] = None,
        audit_logger: Optional[any] = None,
        alert_callback: Optional[callable] = None,
    ):
        """初始化NetworkGuard

        白皮书依据: 第七章 7.4 网络防护

        Args:
            whitelist_domains: 白名单域名集合，None使用默认值
            blacklist_ip_ranges: 黑名单IP段列表，None使用默认值
            audit_logger: 审计日志记录器
            alert_callback: 告警回调函数
        """
        self.whitelist_domains: Set[str] = (
            whitelist_domains if whitelist_domains is not None else self.DEFAULT_WHITELIST_DOMAINS.copy()
        )

        self.blacklist_ip_ranges: List[ipaddress.IPv4Network] = []
        ip_ranges = blacklist_ip_ranges if blacklist_ip_ranges is not None else self.DEFAULT_BLACKLIST_IP_RANGES
        for ip_range in ip_ranges:
            try:
                self.blacklist_ip_ranges.append(ipaddress.IPv4Network(ip_range))
            except ValueError as e:
                logger.warning(f"无效的IP段: {ip_range} - {e}")

        self.audit_logger = audit_logger
        self.alert_callback = alert_callback

        logger.info(
            f"NetworkGuard初始化完成: "
            f"whitelist_domains={len(self.whitelist_domains)}, "
            f"blacklist_ip_ranges={len(self.blacklist_ip_ranges)}"
        )

    def check_access(self, target: str, context: Optional[str] = None) -> NetworkAccessResult:
        """检查网络访问

        白皮书依据: 第七章 7.4 网络防护
        Requirements: 11.1, 11.2, 11.3, 11.4, 11.5

        Args:
            target: 访问目标（URL、域名或IP地址）
            context: 访问上下文（用于日志记录）

        Returns:
            NetworkAccessResult对象

        Raises:
            ValueError: 当target为空时
        """
        if not target or not target.strip():
            raise ValueError("访问目标不能为空")

        target = target.strip()

        # 解析目标
        domain, ip = self._parse_target(target)

        # 检查IP黑名单
        if ip:
            ip_check_result = self._check_ip_blacklist(ip)
            if not ip_check_result.allowed:
                self._log_access(target, False, ip_check_result.reason, context)
                self._send_alert(target, ip_check_result.reason, context)
                return ip_check_result

        # 检查域名白名单
        if domain:
            domain_check_result = self._check_domain_whitelist(domain)
            self._log_access(target, domain_check_result.allowed, domain_check_result.reason, context)

            if not domain_check_result.allowed:
                self._send_alert(target, domain_check_result.reason, context)

            return domain_check_result

        # 默认拒绝（Requirement 11.1）
        result = NetworkAccessResult(
            allowed=False, reason="默认拒绝策略：目标不在白名单中", target=target, rule_matched="default_deny"
        )

        self._log_access(target, False, result.reason, context)
        self._send_alert(target, result.reason, context)

        return result

    def _parse_target(self, target: str) -> tuple[Optional[str], Optional[str]]:
        """解析访问目标

        Args:
            target: 访问目标（URL、域名或IP地址）

        Returns:
            (域名, IP地址) 元组，至少一个非None
        """
        # 尝试解析为URL
        if "://" in target:
            parsed = urlparse(target)
            hostname = parsed.hostname
            if hostname:
                # 检查是否为IP地址
                if self._is_ip_address(hostname):  # pylint: disable=no-else-return
                    return None, hostname
                else:
                    return hostname, None

        # 尝试解析为IP地址
        if self._is_ip_address(target):
            return None, target

        # 作为域名处理
        return target, None

    def _is_ip_address(self, value: str) -> bool:
        """检查是否为IP地址

        Args:
            value: 待检查的字符串

        Returns:
            True如果是有效的IP地址
        """
        try:
            ipaddress.IPv4Address(value)
            return True
        except ValueError:
            return False

    def _check_domain_whitelist(self, domain: str) -> NetworkAccessResult:
        """检查域名白名单

        白皮书依据: 第七章 7.4 网络防护
        Requirement: 11.2 允许白名单域名

        Args:
            domain: 域名

        Returns:
            NetworkAccessResult对象
        """
        # 规范化域名（转小写）
        domain = domain.lower()

        # 检查完全匹配
        if domain in self.whitelist_domains:
            return NetworkAccessResult(allowed=True, target=domain, rule_matched="whitelist_exact")

        # 检查子域名匹配
        for whitelisted_domain in self.whitelist_domains:
            if domain.endswith("." + whitelisted_domain):
                return NetworkAccessResult(allowed=True, target=domain, rule_matched="whitelist_subdomain")

        # 不在白名单中
        return NetworkAccessResult(
            allowed=False, reason=f"域名不在白名单中: {domain}", target=domain, rule_matched="whitelist_miss"
        )

    def _check_ip_blacklist(self, ip: str) -> NetworkAccessResult:
        """检查IP黑名单

        白皮书依据: 第七章 7.4 网络防护
        Requirement: 11.3 阻止黑名单IP段

        Args:
            ip: IP地址

        Returns:
            NetworkAccessResult对象
        """
        try:
            ip_addr = ipaddress.IPv4Address(ip)

            # 检查是否在黑名单IP段中
            for ip_range in self.blacklist_ip_ranges:
                if ip_addr in ip_range:
                    return NetworkAccessResult(
                        allowed=False,
                        reason=f"IP地址在黑名单段中: {ip} in {ip_range}",
                        target=ip,
                        rule_matched="blacklist_ip_range",
                    )

            # IP不在黑名单中，但仍需检查域名白名单
            return NetworkAccessResult(
                allowed=False,
                reason=f"IP地址访问需要域名白名单验证: {ip}",
                target=ip,
                rule_matched="ip_requires_domain",
            )

        except ValueError as e:
            return NetworkAccessResult(
                allowed=False, reason=f"无效的IP地址: {ip} - {e}", target=ip, rule_matched="invalid_ip"
            )

    def _log_access(self, target: str, allowed: bool, reason: str, context: Optional[str]) -> None:
        """记录网络访问日志

        白皮书依据: 第七章 7.4 网络防护
        Requirement: 11.4 记录所有网络访问尝试

        Args:
            target: 访问目标
            allowed: 是否允许
            reason: 原因
            context: 上下文
        """
        log_level = "INFO" if allowed else "WARNING"
        log_message = f"网络访问{'允许' if allowed else '拒绝'}: " f"target={target}, reason={reason}"
        if context:
            log_message += f", context={context}"

        if log_level == "INFO":
            logger.info(log_message)
        else:
            logger.warning(log_message)

        # 记录到审计日志
        if self.audit_logger:
            try:
                self.audit_logger.log_event(
                    {
                        "event_type": "NETWORK_ACCESS",
                        "target": target,
                        "allowed": allowed,
                        "reason": reason,
                        "context": context or "unknown",
                    }
                )
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.error(f"记录审计日志失败: {e}")

    def _send_alert(self, target: str, reason: str, context: Optional[str]) -> None:
        """发送违规告警

        白皮书依据: 第七章 7.4 网络防护
        Requirement: 11.5 发送违规告警

        Args:
            target: 访问目标
            reason: 拒绝原因
            context: 上下文
        """
        if self.alert_callback:
            try:
                alert_message = f"网络访问违规: target={target}, reason={reason}"
                if context:
                    alert_message += f", context={context}"

                self.alert_callback(alert_message)
                logger.info(f"已发送网络违规告警: {target}")
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.error(f"发送告警失败: {e}")

    def add_whitelist_domain(self, domain: str) -> None:
        """添加白名单域名

        Args:
            domain: 域名

        Raises:
            ValueError: 当域名为空或无效时
        """
        if not domain or not domain.strip():
            raise ValueError("域名不能为空")

        domain = domain.strip().lower()

        # 简单的域名格式验证
        if not re.match(r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?(\.[a-z0-9]([a-z0-9-]*[a-z0-9])?)*$", domain):
            raise ValueError(f"无效的域名格式: {domain}")

        self.whitelist_domains.add(domain)
        logger.info(f"添加白名单域名: {domain}")

    def remove_whitelist_domain(self, domain: str) -> None:
        """移除白名单域名

        Args:
            domain: 域名

        Raises:
            ValueError: 当域名不在白名单中时
        """
        domain = domain.strip().lower()

        if domain not in self.whitelist_domains:
            raise ValueError(f"域名不在白名单中: {domain}")

        self.whitelist_domains.remove(domain)
        logger.info(f"移除白名单域名: {domain}")

    def add_blacklist_ip_range(self, ip_range: str) -> None:
        """添加黑名单IP段

        Args:
            ip_range: IP段（CIDR格式）

        Raises:
            ValueError: 当IP段格式无效时
        """
        try:
            ip_network = ipaddress.IPv4Network(ip_range)
            self.blacklist_ip_ranges.append(ip_network)
            logger.info(f"添加黑名单IP段: {ip_range}")
        except ValueError as e:
            raise ValueError(f"无效的IP段格式: {ip_range} - {e}") from e

    def get_config(self) -> dict:
        """获取配置信息

        Returns:
            配置字典
        """
        return {
            "whitelist_domains": sorted(self.whitelist_domains),
            "blacklist_ip_ranges": [str(ip_range) for ip_range in self.blacklist_ip_ranges],
            "audit_logger_enabled": self.audit_logger is not None,
            "alert_callback_enabled": self.alert_callback is not None,
        }
