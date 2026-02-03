"""统一安全网关

白皮书依据: 第七章 7.1 统一安全网关

UnifiedSecurityGateway提供7层纵深防御，所有AI生成的代码必须通过此网关。

7层防御架构：
1. ContentTypeDetector - 内容类型识别
2. ASTWhitelistValidator - AST白名单验证
3. SemanticValidator - 语义验证
4. SandboxManager - 沙箱隔离
5. NetworkGuard - 网络防护
6. ResourceLimiter - 资源限制
7. AuditLogger - 审计日志

Author: MIA Team
Date: 2026-01-25
Version: 1.0.0
"""

import hashlib
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from loguru import logger

from src.audit.audit_logger import AuditLogger
from src.compliance.ast_validator import ASTWhitelistValidator, ValidationResult
from src.compliance.docker_sandbox import DockerSandbox, ExecutionResult
from src.compliance.network_guard import NetworkGuard


class ContentType(Enum):
    """内容类型

    白皮书依据: 第七章 7.1 统一安全网关
    """

    CODE = "code"
    PROMPT = "prompt"
    CONFIG = "config"
    EXPRESSION = "expression"


class IsolationLevel(Enum):
    """隔离级别

    白皮书依据: 第七章 7.1 统一安全网关
    """

    FIRECRACKER = "firecracker"
    GVISOR = "gvisor"
    DOCKER = "docker"
    BUBBLEWRAP = "bubblewrap"
    NONE = "none"


class SecurityErrorType(Enum):
    """安全错误类型

    白皮书依据: 第七章 7.1 统一安全网关
    """

    VALIDATION_FAILED = "validation_failed"
    BLACKLIST_DETECTED = "blacklist_detected"
    SANDBOX_FAILED = "sandbox_failed"
    TIMEOUT_EXCEEDED = "timeout_exceeded"
    MEMORY_EXCEEDED = "memory_exceeded"
    NETWORK_VIOLATION = "network_violation"
    EXECUTION_FAILED = "execution_failed"


@dataclass
class SecurityContext:
    """安全上下文

    白皮书依据: 第七章 7.1 统一安全网关

    Attributes:
        component_name: 组件名称
        user_id: 用户ID
        session_id: 会话ID
        isolation_level: 隔离级别
        timeout_ms: 超时时间（毫秒）
        memory_mb: 内存限制（MB）
        cpu_cores: CPU核数
    """

    component_name: str
    user_id: str = "system"
    session_id: str = ""
    isolation_level: IsolationLevel = IsolationLevel.DOCKER
    timeout_ms: int = 30000
    memory_mb: int = 512
    cpu_cores: float = 1.0


@dataclass
class GatewayValidationResult:
    """网关验证结果

    白皮书依据: 第七章 7.1 统一安全网关

    Attributes:
        approved: 是否通过验证
        reason: 验证失败原因
        violations: 违规项列表
        execution_time_ms: 验证耗时（毫秒）
        content_hash: 内容哈希
        layer_results: 各层验证结果
    """

    approved: bool
    reason: str = ""
    violations: List[str] = field(default_factory=list)
    execution_time_ms: float = 0.0
    content_hash: str = ""
    layer_results: Dict[str, Any] = field(default_factory=dict)


class UnifiedSecurityGateway:
    """统一安全网关

    白皮书依据: 第七章 7.1 统一安全网关

    提供7层纵深防御，所有AI代码必须通过此网关。

    Requirements:
    - 8.1: 提供7层防御
    - 8.2: 识别内容类型
    - 8.3: 支持多种隔离级别
    - 8.4: 验证失败返回详细原因
    - 8.5: 记录审计日志
    - 性能要求: 总验证时间 < 150ms (P99)

    Attributes:
        ast_validator: AST验证器
        sandbox_manager: 沙箱管理器
        network_guard: 网络防护
        audit_logger: 审计日志
        enable_semantic_validation: 是否启用语义验证
        enable_resource_limiting: 是否启用资源限制
    """

    def __init__(  # pylint: disable=too-many-positional-arguments
        self,
        ast_validator: Optional[ASTWhitelistValidator] = None,
        sandbox_manager: Optional[DockerSandbox] = None,
        network_guard: Optional[NetworkGuard] = None,
        audit_logger: Optional[AuditLogger] = None,
        enable_semantic_validation: bool = False,
        enable_resource_limiting: bool = False,
    ):
        """初始化统一安全网关

        白皮书依据: 第七章 7.1 统一安全网关

        Args:
            ast_validator: AST验证器，None则创建默认实例
            sandbox_manager: 沙箱管理器，None则创建默认实例
            network_guard: 网络防护，None则创建默认实例
            audit_logger: 审计日志，None则不记录审计
            enable_semantic_validation: 是否启用语义验证（简化版）
            enable_resource_limiting: 是否启用资源限制（简化版）
        """
        # Layer 2: AST验证器
        self.ast_validator = ast_validator or ASTWhitelistValidator()

        # Layer 4: 沙箱管理器
        self.sandbox_manager = sandbox_manager or DockerSandbox()

        # Layer 5: 网络防护
        self.network_guard = network_guard or NetworkGuard(audit_logger=audit_logger)

        # Layer 7: 审计日志
        self.audit_logger = audit_logger

        # Layer 3: 语义验证（简化版）
        self.enable_semantic_validation = enable_semantic_validation

        # Layer 6: 资源限制（简化版）
        self.enable_resource_limiting = enable_resource_limiting

        logger.info(
            f"UnifiedSecurityGateway初始化完成: "
            f"ast_validator={ast_validator is not None}, "
            f"sandbox={sandbox_manager is not None}, "
            f"network_guard={network_guard is not None}, "
            f"audit_logger={audit_logger is not None}, "
            f"semantic_validation={enable_semantic_validation}, "
            f"resource_limiting={enable_resource_limiting}"
        )

    async def validate_and_execute(
        self, content: str, content_type: ContentType, context: SecurityContext
    ) -> GatewayValidationResult:
        """验证并执行内容

        白皮书依据: 第七章 7.1 统一安全网关
        Requirements: 8.1, 8.2, 8.3, 8.4, 8.5

        7层防御流程：
        1. ContentTypeDetector - 内容类型识别
        2. ASTWhitelistValidator - AST白名单验证
        3. SemanticValidator - 语义验证
        4. SandboxManager - 沙箱隔离
        5. NetworkGuard - 网络防护
        6. ResourceLimiter - 资源限制
        7. AuditLogger - 审计日志

        Args:
            content: 要验证的内容
            content_type: 内容类型
            context: 安全上下文

        Returns:
            GatewayValidationResult对象

        Raises:
            ValueError: 当content为空时
        """
        if not content or not content.strip():
            raise ValueError("内容不能为空")

        start_time = time.perf_counter()
        layer_results = {}
        violations = []

        # 计算内容哈希
        content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()

        try:
            # Layer 1: 内容类型检测 (Requirement 8.2)
            detected_type = self._detect_content_type(content, content_type)
            layer_results["content_type_detection"] = {
                "detected_type": detected_type.value,
                "provided_type": content_type.value,
                "match": detected_type == content_type,
            }

            # Layer 2: AST白名单验证
            ast_result = self._validate_ast(content, detected_type)
            layer_results["ast_validation"] = {
                "approved": ast_result.approved,
                "reason": ast_result.reason,
                "violations": ast_result.violations,
                "execution_time_ms": ast_result.execution_time_ms,
            }

            if not ast_result.approved:
                violations.extend(ast_result.violations)

                # 记录审计日志（失败情况）
                execution_time_ms = (time.perf_counter() - start_time) * 1000
                self._log_validation(
                    content_hash=content_hash,
                    content_type=detected_type,
                    context=context,
                    approved=False,
                    execution_time_ms=execution_time_ms,
                    layer_results=layer_results,
                )

                return self._create_failure_result(
                    reason="AST验证失败",
                    violations=violations,
                    execution_time_ms=execution_time_ms,
                    content_hash=content_hash,
                    layer_results=layer_results,
                )

            # Layer 3: 语义验证（简化版）
            if self.enable_semantic_validation:
                semantic_result = self._validate_semantics(content, detected_type)
                layer_results["semantic_validation"] = semantic_result

                if not semantic_result["approved"]:
                    violations.extend(semantic_result.get("violations", []))
                    return self._create_failure_result(
                        reason="语义验证失败",
                        violations=violations,
                        execution_time_ms=(time.perf_counter() - start_time) * 1000,
                        content_hash=content_hash,
                        layer_results=layer_results,
                    )

            # Layer 4: 沙箱隔离执行 (Requirement 8.3)
            if context.isolation_level != IsolationLevel.NONE and detected_type == ContentType.CODE:
                sandbox_result = await self._execute_in_sandbox(content, context)
                layer_results["sandbox_execution"] = {
                    "success": sandbox_result.success,
                    "output": sandbox_result.output[:200] if sandbox_result.output else "",
                    "error": sandbox_result.error[:200] if sandbox_result.error else "",
                    "execution_time_ms": sandbox_result.execution_time_ms,
                    "memory_used_mb": sandbox_result.memory_used_mb,
                }

                if not sandbox_result.success:
                    violations.append(f"沙箱执行失败: {sandbox_result.error}")
                    return self._create_failure_result(
                        reason="沙箱执行失败",
                        violations=violations,
                        execution_time_ms=(time.perf_counter() - start_time) * 1000,
                        content_hash=content_hash,
                        layer_results=layer_results,
                    )

            # Layer 5: 网络防护（检查代码中的网络访问）
            network_result = self._check_network_access(content)
            layer_results["network_guard"] = network_result

            if not network_result["approved"]:
                violations.extend(network_result.get("violations", []))
                return self._create_failure_result(
                    reason="网络访问违规",
                    violations=violations,
                    execution_time_ms=(time.perf_counter() - start_time) * 1000,
                    content_hash=content_hash,
                    layer_results=layer_results,
                )

            # Layer 6: 资源限制（简化版）
            if self.enable_resource_limiting:
                resource_result = self._check_resource_limits(content, context)
                layer_results["resource_limiting"] = resource_result

                if not resource_result["approved"]:
                    violations.extend(resource_result.get("violations", []))
                    return self._create_failure_result(
                        reason="资源限制超标",
                        violations=violations,
                        execution_time_ms=(time.perf_counter() - start_time) * 1000,
                        content_hash=content_hash,
                        layer_results=layer_results,
                    )

            # 计算总执行时间
            execution_time_ms = (time.perf_counter() - start_time) * 1000

            # 检查性能要求 (< 150ms P99)
            if execution_time_ms > 150:
                logger.warning(f"验证时间超标: {execution_time_ms:.2f}ms > 150ms (P99要求)")

            # Layer 7: 审计日志 (Requirement 8.5)
            self._log_validation(
                content_hash=content_hash,
                content_type=detected_type,
                context=context,
                approved=True,
                execution_time_ms=execution_time_ms,
                layer_results=layer_results,
            )

            logger.info(f"安全网关验证通过: " f"content_type={detected_type.value}, " f"time={execution_time_ms:.2f}ms")

            return GatewayValidationResult(
                approved=True,
                reason="验证通过",
                violations=[],
                execution_time_ms=execution_time_ms,
                content_hash=content_hash,
                layer_results=layer_results,
            )

        except Exception as e:  # pylint: disable=broad-exception-caught
            execution_time_ms = (time.perf_counter() - start_time) * 1000
            logger.error(f"安全网关验证异常: {e}")

            # 记录审计日志
            self._log_validation(
                content_hash=content_hash,
                content_type=content_type,
                context=context,
                approved=False,
                execution_time_ms=execution_time_ms,
                layer_results=layer_results,
                error=str(e),
            )

            return self._create_failure_result(
                reason=f"验证异常: {e}",
                violations=[f"异常: {e}"],
                execution_time_ms=execution_time_ms,
                content_hash=content_hash,
                layer_results=layer_results,
            )

    def _detect_content_type(
        self, content: str, provided_type: ContentType  # pylint: disable=unused-argument
    ) -> ContentType:  # pylint: disable=unused-argument
        """检测内容类型

        白皮书依据: 第七章 7.1 统一安全网关
        Requirement: 8.2 识别内容类型

        Args:
            content: 内容字符串
            provided_type: 用户提供的类型

        Returns:
            检测到的内容类型
        """
        # 简化版本：基于关键词和语法特征检测

        # 检查是否为Python代码（包括函数调用）
        code_indicators = [
            "def ",
            "class ",
            "import ",
            "from ",
            "return ",
            "if ",
            "for ",
            "while ",
            "try:",
            "except:",
            "eval(",
            "exec(",
            "compile(",
            "print(",
            "=",
        ]
        if any(indicator in content for indicator in code_indicators):
            return ContentType.CODE

        # 检查是否为因子表达式
        expression_indicators = [
            "rank(",
            "delay(",
            "delta(",
            "ts_sum(",
            "ts_mean(",
            "close",
            "open",
            "high",
            "low",
            "volume",
        ]
        if any(indicator in content for indicator in expression_indicators):
            return ContentType.EXPRESSION

        # 检查是否为配置
        config_indicators = ["{", "}", ":", "config", "settings"]
        if any(indicator in content for indicator in config_indicators):
            return ContentType.CONFIG

        # 默认为prompt
        return ContentType.PROMPT

    def _validate_ast(self, content: str, content_type: ContentType) -> ValidationResult:
        """AST验证

        白皮书依据: 第七章 7.2 AST白名单验证

        Args:
            content: 内容字符串
            content_type: 内容类型

        Returns:
            ValidationResult对象
        """
        # 只对代码和表达式进行AST验证
        if content_type not in (ContentType.CODE, ContentType.EXPRESSION):
            return ValidationResult(approved=True, reason="非代码内容，跳过AST验证")

        return self.ast_validator.validate(content)

    def _validate_semantics(
        self, content: str, content_type: ContentType  # pylint: disable=unused-argument
    ) -> Dict[str, Any]:  # pylint: disable=unused-argument
        """语义验证（简化版）

        白皮书依据: 第七章 7.1 统一安全网关

        Args:
            content: 内容字符串
            content_type: 内容类型

        Returns:
            验证结果字典
        """
        # 简化版本：检查一些基本的语义问题
        violations = []

        # 检查是否有明显的恶意模式
        malicious_patterns = [
            "rm -rf",
            "format c:",
            "del /f /s /q",
            "DROP TABLE",
            "DELETE FROM",
            "TRUNCATE",
            '__import__("os")',
            '__import__("sys")',
        ]

        for pattern in malicious_patterns:
            if pattern in content:
                violations.append(f"检测到恶意模式: {pattern}")

        return {
            "approved": len(violations) == 0,
            "violations": violations,
            "reason": "语义验证通过" if len(violations) == 0 else "检测到恶意模式",
        }

    async def _execute_in_sandbox(self, content: str, context: SecurityContext) -> ExecutionResult:
        """在沙箱中执行

        白皮书依据: 第七章 7.3 Docker沙箱
        Requirement: 8.3 支持多种隔离级别

        Args:
            content: 代码内容
            context: 安全上下文

        Returns:
            ExecutionResult对象
        """
        timeout_seconds = context.timeout_ms // 1000

        if context.isolation_level == IsolationLevel.DOCKER:  # pylint: disable=no-else-return
            return await self.sandbox_manager.execute(content, timeout=timeout_seconds)
        elif context.isolation_level == IsolationLevel.BUBBLEWRAP:
            # 简化版本：使用Docker作为fallback
            logger.warning("BUBBLEWRAP隔离级别暂不支持，使用DOCKER作为fallback")
            return await self.sandbox_manager.execute(content, timeout=timeout_seconds)
        elif context.isolation_level == IsolationLevel.NONE:
            # 不执行，只验证
            return ExecutionResult(success=True, output="隔离级别为NONE，跳过执行")
        else:
            logger.warning(f"不支持的隔离级别: {context.isolation_level}，使用DOCKER")
            return await self.sandbox_manager.execute(content, timeout=timeout_seconds)

    def _check_network_access(self, content: str) -> Dict[str, Any]:
        """检查网络访问

        白皮书依据: 第七章 7.4 网络防护

        Args:
            content: 内容字符串

        Returns:
            检查结果字典
        """
        violations = []

        # 检查是否有网络相关的导入或调用
        network_patterns = [
            "import requests",
            "import urllib",
            "import socket",
            "import http",
            "from requests",
            "from urllib",
            "requests.get",
            "requests.post",
            "urllib.request",
            "socket.socket",
            "http.client",
        ]

        for pattern in network_patterns:
            if pattern in content:
                violations.append(f"检测到网络访问: {pattern}")

        return {
            "approved": len(violations) == 0,
            "violations": violations,
            "reason": "无网络访问" if len(violations) == 0 else "检测到网络访问",
        }

    def _check_resource_limits(
        self, content: str, context: SecurityContext  # pylint: disable=unused-argument
    ) -> Dict[str, Any]:  # pylint: disable=unused-argument
        """检查资源限制（简化版）

        白皮书依据: 第七章 7.1 统一安全网关

        Args:
            content: 内容字符串
            context: 安全上下文

        Returns:
            检查结果字典
        """
        violations = []

        # 检查代码长度
        if len(content) > 100000:  # 100KB
            violations.append(f"代码过长: {len(content)} > 100000字节")

        # 检查行数
        lines = content.count("\n") + 1
        if lines > 1000:
            violations.append(f"代码行数过多: {lines} > 1000行")

        return {
            "approved": len(violations) == 0,
            "violations": violations,
            "reason": "资源限制检查通过" if len(violations) == 0 else "资源限制超标",
        }

    def _log_validation(  # pylint: disable=too-many-positional-arguments
        self,
        content_hash: str,
        content_type: ContentType,
        context: SecurityContext,
        approved: bool,
        execution_time_ms: float,
        layer_results: Dict[str, Any],
        error: Optional[str] = None,
    ) -> None:
        """记录验证审计日志

        白皮书依据: 第七章 7.1 统一安全网关
        Requirement: 8.5 记录审计日志

        Args:
            content_hash: 内容哈希
            content_type: 内容类型
            context: 安全上下文
            approved: 是否通过
            execution_time_ms: 执行时间
            layer_results: 各层结果
            error: 错误信息
        """
        if self.audit_logger is None:
            return

        try:
            event_data = {
                "event_type": "SECURITY_GATEWAY_VALIDATION",
                "content_hash": content_hash,
                "content_type": content_type.value,
                "component_name": context.component_name,
                "user_id": context.user_id,
                "session_id": context.session_id,
                "isolation_level": context.isolation_level.value,
                "approved": approved,
                "execution_time_ms": execution_time_ms,
                "layer_results": layer_results,
                "error": error,
            }

            self.audit_logger.log_event(event_data)
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"记录审计日志失败: {e}")

    def _create_failure_result(  # pylint: disable=too-many-positional-arguments
        self,
        reason: str,
        violations: List[str],
        execution_time_ms: float,
        content_hash: str,
        layer_results: Dict[str, Any],
    ) -> GatewayValidationResult:
        """创建失败结果

        白皮书依据: 第七章 7.1 统一安全网关
        Requirement: 8.4 验证失败返回详细原因

        Args:
            reason: 失败原因
            violations: 违规项列表
            execution_time_ms: 执行时间
            content_hash: 内容哈希
            layer_results: 各层结果

        Returns:
            GatewayValidationResult对象
        """
        logger.warning(
            f"安全网关验证失败: reason={reason}, " f"violations={len(violations)}, " f"time={execution_time_ms:.2f}ms"
        )

        return GatewayValidationResult(
            approved=False,
            reason=reason,
            violations=violations,
            execution_time_ms=execution_time_ms,
            content_hash=content_hash,
            layer_results=layer_results,
        )

    def get_config(self) -> Dict[str, Any]:
        """获取配置信息

        Returns:
            配置字典
        """
        return {
            "ast_validator_enabled": self.ast_validator is not None,
            "sandbox_manager_enabled": self.sandbox_manager is not None,
            "sandbox_config": self.sandbox_manager.get_container_config() if self.sandbox_manager else None,
            "network_guard_enabled": self.network_guard is not None,
            "network_guard_config": self.network_guard.get_config() if self.network_guard else None,
            "audit_logger_enabled": self.audit_logger is not None,
            "semantic_validation_enabled": self.enable_semantic_validation,
            "resource_limiting_enabled": self.enable_resource_limiting,
        }
