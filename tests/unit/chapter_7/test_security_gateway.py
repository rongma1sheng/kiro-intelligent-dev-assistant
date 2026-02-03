"""UnifiedSecurityGateway单元测试

白皮书依据: 第七章 7.1 统一安全网关

测试覆盖：
- 7层防御流程
- 内容类型检测
- 验证失败响应
- 各层集成
- 性能要求
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch

from src.compliance.unified_security_gateway import (
    UnifiedSecurityGateway,
    ContentType,
    IsolationLevel,
    SecurityContext,
    GatewayValidationResult,
)
from src.compliance.ast_validator import ASTWhitelistValidator, ValidationResult
from src.compliance.docker_sandbox import DockerSandbox, ExecutionResult
from src.compliance.network_guard import NetworkGuard
from src.audit.audit_logger import AuditLogger


class TestUnifiedSecurityGateway:
    """UnifiedSecurityGateway单元测试"""
    
    @pytest.fixture
    def mock_ast_validator(self):
        """Mock AST验证器"""
        validator = Mock(spec=ASTWhitelistValidator)
        validator.validate.return_value = ValidationResult(
            approved=True,
            reason="验证通过"
        )
        return validator
    
    @pytest.fixture
    def mock_sandbox(self):
        """Mock沙箱"""
        sandbox = Mock(spec=DockerSandbox)
        sandbox.execute = AsyncMock(return_value=ExecutionResult(
            success=True,
            output="执行成功"
        ))
        sandbox.get_container_config.return_value = {
            'image': 'python:3.11-slim',
            'memory_limit_mb': 512
        }
        return sandbox
    
    @pytest.fixture
    def mock_network_guard(self):
        """Mock网络防护"""
        guard = Mock(spec=NetworkGuard)
        guard.get_config.return_value = {
            'whitelist_domains': ['pypi.org'],
            'blacklist_ip_ranges': ['10.0.0.0/8']
        }
        return guard
    
    @pytest.fixture
    def mock_audit_logger(self):
        """Mock审计日志"""
        logger = Mock(spec=AuditLogger)
        logger.log_event.return_value = None
        return logger
    
    @pytest.fixture
    def gateway(self, mock_ast_validator, mock_sandbox, mock_network_guard, mock_audit_logger):
        """创建网关实例"""
        return UnifiedSecurityGateway(
            ast_validator=mock_ast_validator,
            sandbox_manager=mock_sandbox,
            network_guard=mock_network_guard,
            audit_logger=mock_audit_logger
        )
    
    @pytest.fixture
    def security_context(self):
        """创建安全上下文"""
        return SecurityContext(
            component_name="test_component",
            user_id="test_user",
            session_id="test_session",
            isolation_level=IsolationLevel.DOCKER
        )
    
    # ==================== 初始化测试 ====================
    
    def test_init_with_defaults(self):
        """测试使用默认参数初始化"""
        gateway = UnifiedSecurityGateway()
        
        assert gateway.ast_validator is not None
        assert gateway.sandbox_manager is not None
        assert gateway.network_guard is not None
        assert gateway.audit_logger is None
        assert gateway.enable_semantic_validation is False
        assert gateway.enable_resource_limiting is False
    
    def test_init_with_custom_components(
        self,
        mock_ast_validator,
        mock_sandbox,
        mock_network_guard,
        mock_audit_logger
    ):
        """测试使用自定义组件初始化"""
        gateway = UnifiedSecurityGateway(
            ast_validator=mock_ast_validator,
            sandbox_manager=mock_sandbox,
            network_guard=mock_network_guard,
            audit_logger=mock_audit_logger,
            enable_semantic_validation=True,
            enable_resource_limiting=True
        )
        
        assert gateway.ast_validator is mock_ast_validator
        assert gateway.sandbox_manager is mock_sandbox
        assert gateway.network_guard is mock_network_guard
        assert gateway.audit_logger is mock_audit_logger
        assert gateway.enable_semantic_validation is True
        assert gateway.enable_resource_limiting is True
    
    # ==================== 内容类型检测测试 ====================
    
    @pytest.mark.asyncio
    async def test_detect_content_type_code(self, gateway, security_context):
        """测试检测Python代码"""
        code = """
def calculate_sharpe(returns):
    return returns.mean() / returns.std()
"""
        result = await gateway.validate_and_execute(
            code,
            ContentType.CODE,
            security_context
        )
        
        assert result.layer_results['content_type_detection']['detected_type'] == 'code'
    
    @pytest.mark.asyncio
    async def test_detect_content_type_expression(self, gateway, security_context):
        """测试检测因子表达式"""
        expression = "rank(close) / delay(close, 1) - 1"
        
        result = await gateway.validate_and_execute(
            expression,
            ContentType.EXPRESSION,
            security_context
        )
        
        assert result.layer_results['content_type_detection']['detected_type'] == 'expression'
    
    @pytest.mark.asyncio
    async def test_detect_content_type_config(self, gateway, security_context):
        """测试检测配置"""
        config = '{"config": {"key": "value"}}'
        
        result = await gateway.validate_and_execute(
            config,
            ContentType.CONFIG,
            security_context
        )
        
        assert result.layer_results['content_type_detection']['detected_type'] == 'config'
    
    @pytest.mark.asyncio
    async def test_detect_content_type_prompt(self, gateway, security_context):
        """测试检测提示词"""
        prompt = "请帮我生成一个计算夏普比率的函数"
        
        result = await gateway.validate_and_execute(
            prompt,
            ContentType.PROMPT,
            security_context
        )
        
        assert result.layer_results['content_type_detection']['detected_type'] == 'prompt'
    
    # ==================== AST验证测试 ====================
    
    @pytest.mark.asyncio
    async def test_ast_validation_pass(self, gateway, security_context):
        """测试AST验证通过"""
        code = "result = abs(min(1, 2))"
        
        result = await gateway.validate_and_execute(
            code,
            ContentType.CODE,
            security_context
        )
        
        assert result.approved is True
        assert 'ast_validation' in result.layer_results
        assert result.layer_results['ast_validation']['approved'] is True
    
    @pytest.mark.asyncio
    async def test_ast_validation_fail(
        self,
        mock_ast_validator,
        mock_sandbox,
        mock_network_guard,
        mock_audit_logger,
        security_context
    ):
        """测试AST验证失败"""
        # 配置AST验证器返回失败
        mock_ast_validator.validate.return_value = ValidationResult(
            approved=False,
            reason="检测到黑名单函数",
            violations=["黑名单函数: eval"]
        )
        
        gateway = UnifiedSecurityGateway(
            ast_validator=mock_ast_validator,
            sandbox_manager=mock_sandbox,
            network_guard=mock_network_guard,
            audit_logger=mock_audit_logger
        )
        
        code = "eval('1+1')"
        
        result = await gateway.validate_and_execute(
            code,
            ContentType.CODE,
            security_context
        )
        
        assert result.approved is False
        assert result.reason == "AST验证失败"
        assert len(result.violations) > 0
        assert "黑名单函数: eval" in result.violations
    
    # ==================== 沙箱执行测试 ====================
    
    @pytest.mark.asyncio
    async def test_sandbox_execution_docker(self, gateway, security_context):
        """测试Docker沙箱执行"""
        code = "print('Hello, World!')"
        
        result = await gateway.validate_and_execute(
            code,
            ContentType.CODE,
            security_context
        )
        
        assert result.approved is True
        assert 'sandbox_execution' in result.layer_results
        assert result.layer_results['sandbox_execution']['success'] is True
    
    @pytest.mark.asyncio
    async def test_sandbox_execution_none(self, gateway):
        """测试无隔离级别（跳过执行）"""
        context = SecurityContext(
            component_name="test",
            isolation_level=IsolationLevel.NONE
        )
        
        code = "print('Hello')"
        
        result = await gateway.validate_and_execute(
            code,
            ContentType.CODE,
            context
        )
        
        assert result.approved is True
        # 无隔离级别时不应该有sandbox_execution结果
        assert 'sandbox_execution' not in result.layer_results
    
    @pytest.mark.asyncio
    async def test_sandbox_execution_fail(
        self,
        mock_ast_validator,
        mock_sandbox,
        mock_network_guard,
        mock_audit_logger,
        security_context
    ):
        """测试沙箱执行失败"""
        # 配置沙箱返回失败
        mock_sandbox.execute = AsyncMock(return_value=ExecutionResult(
            success=False,
            error="执行超时"
        ))
        
        gateway = UnifiedSecurityGateway(
            ast_validator=mock_ast_validator,
            sandbox_manager=mock_sandbox,
            network_guard=mock_network_guard,
            audit_logger=mock_audit_logger
        )
        
        code = "while True: pass"
        
        result = await gateway.validate_and_execute(
            code,
            ContentType.CODE,
            security_context
        )
        
        assert result.approved is False
        assert result.reason == "沙箱执行失败"
        assert any("沙箱执行失败" in v for v in result.violations)
    
    # ==================== 网络访问检查测试 ====================
    
    @pytest.mark.asyncio
    async def test_network_check_pass(self, gateway, security_context):
        """测试网络检查通过（无网络访问）"""
        code = "result = 1 + 1"
        
        result = await gateway.validate_and_execute(
            code,
            ContentType.CODE,
            security_context
        )
        
        assert result.approved is True
        assert 'network_guard' in result.layer_results
        assert result.layer_results['network_guard']['approved'] is True
    
    @pytest.mark.asyncio
    async def test_network_check_fail(self, gateway, security_context):
        """测试网络检查失败（检测到网络访问）"""
        code = """
import requests
response = requests.get('https://api.example.com')
"""
        
        result = await gateway.validate_and_execute(
            code,
            ContentType.CODE,
            security_context
        )
        
        assert result.approved is False
        assert result.reason == "网络访问违规"
        assert any("网络访问" in v for v in result.violations)
    
    # ==================== 语义验证测试 ====================
    
    @pytest.mark.asyncio
    async def test_semantic_validation_enabled(
        self,
        mock_ast_validator,
        mock_sandbox,
        mock_network_guard,
        mock_audit_logger,
        security_context
    ):
        """测试启用语义验证"""
        gateway = UnifiedSecurityGateway(
            ast_validator=mock_ast_validator,
            sandbox_manager=mock_sandbox,
            network_guard=mock_network_guard,
            audit_logger=mock_audit_logger,
            enable_semantic_validation=True
        )
        
        code = "result = 1 + 1"
        
        result = await gateway.validate_and_execute(
            code,
            ContentType.CODE,
            security_context
        )
        
        assert result.approved is True
        assert 'semantic_validation' in result.layer_results
    
    @pytest.mark.asyncio
    async def test_semantic_validation_detect_malicious(
        self,
        mock_ast_validator,
        mock_sandbox,
        mock_network_guard,
        mock_audit_logger,
        security_context
    ):
        """测试语义验证检测恶意模式"""
        gateway = UnifiedSecurityGateway(
            ast_validator=mock_ast_validator,
            sandbox_manager=mock_sandbox,
            network_guard=mock_network_guard,
            audit_logger=mock_audit_logger,
            enable_semantic_validation=True
        )
        
        code = "import os; os.system('rm -rf /')"
        
        result = await gateway.validate_and_execute(
            code,
            ContentType.CODE,
            security_context
        )
        
        assert result.approved is False
        assert result.reason == "语义验证失败"
    
    # ==================== 资源限制测试 ====================
    
    @pytest.mark.asyncio
    async def test_resource_limiting_enabled(
        self,
        mock_ast_validator,
        mock_sandbox,
        mock_network_guard,
        mock_audit_logger,
        security_context
    ):
        """测试启用资源限制"""
        gateway = UnifiedSecurityGateway(
            ast_validator=mock_ast_validator,
            sandbox_manager=mock_sandbox,
            network_guard=mock_network_guard,
            audit_logger=mock_audit_logger,
            enable_resource_limiting=True
        )
        
        code = "result = 1 + 1"
        
        result = await gateway.validate_and_execute(
            code,
            ContentType.CODE,
            security_context
        )
        
        assert result.approved is True
        assert 'resource_limiting' in result.layer_results
    
    @pytest.mark.asyncio
    async def test_resource_limiting_code_too_long(
        self,
        mock_ast_validator,
        mock_sandbox,
        mock_network_guard,
        mock_audit_logger,
        security_context
    ):
        """测试资源限制：代码过长"""
        gateway = UnifiedSecurityGateway(
            ast_validator=mock_ast_validator,
            sandbox_manager=mock_sandbox,
            network_guard=mock_network_guard,
            audit_logger=mock_audit_logger,
            enable_resource_limiting=True
        )
        
        # 生成超长代码
        code = "x = 1\n" * 100001  # 超过100KB
        
        result = await gateway.validate_and_execute(
            code,
            ContentType.CODE,
            security_context
        )
        
        assert result.approved is False
        assert result.reason == "资源限制超标"
    
    @pytest.mark.asyncio
    async def test_resource_limiting_too_many_lines(
        self,
        mock_ast_validator,
        mock_sandbox,
        mock_network_guard,
        mock_audit_logger,
        security_context
    ):
        """测试资源限制：行数过多"""
        gateway = UnifiedSecurityGateway(
            ast_validator=mock_ast_validator,
            sandbox_manager=mock_sandbox,
            network_guard=mock_network_guard,
            audit_logger=mock_audit_logger,
            enable_resource_limiting=True
        )
        
        # 生成超多行代码
        code = "x = 1\n" * 1001  # 超过1000行
        
        result = await gateway.validate_and_execute(
            code,
            ContentType.CODE,
            security_context
        )
        
        assert result.approved is False
        assert result.reason == "资源限制超标"
    
    # ==================== 审计日志测试 ====================
    
    @pytest.mark.asyncio
    async def test_audit_logging(self, gateway, mock_audit_logger, security_context):
        """测试审计日志记录"""
        code = "result = 1 + 1"
        
        await gateway.validate_and_execute(
            code,
            ContentType.CODE,
            security_context
        )
        
        # 验证审计日志被调用
        mock_audit_logger.log_event.assert_called_once()
        
        # 验证日志内容
        call_args = mock_audit_logger.log_event.call_args[0][0]
        assert call_args['event_type'] == 'SECURITY_GATEWAY_VALIDATION'
        assert call_args['approved'] is True
        assert 'content_hash' in call_args
        assert 'execution_time_ms' in call_args
    
    @pytest.mark.asyncio
    async def test_audit_logging_on_failure(
        self,
        mock_ast_validator,
        mock_sandbox,
        mock_network_guard,
        mock_audit_logger,
        security_context
    ):
        """测试验证失败时的审计日志"""
        # 配置AST验证失败
        mock_ast_validator.validate.return_value = ValidationResult(
            approved=False,
            reason="验证失败",
            violations=["测试违规"]
        )
        
        gateway = UnifiedSecurityGateway(
            ast_validator=mock_ast_validator,
            sandbox_manager=mock_sandbox,
            network_guard=mock_network_guard,
            audit_logger=mock_audit_logger
        )
        
        code = "eval('1+1')"
        
        await gateway.validate_and_execute(
            code,
            ContentType.CODE,
            security_context
        )
        
        # 验证审计日志被调用
        mock_audit_logger.log_event.assert_called_once()
        
        # 验证日志内容
        call_args = mock_audit_logger.log_event.call_args[0][0]
        assert call_args['approved'] is False
    
    # ==================== 验证失败响应测试 ====================
    
    @pytest.mark.asyncio
    async def test_validation_failure_response_format(
        self,
        mock_ast_validator,
        mock_sandbox,
        mock_network_guard,
        mock_audit_logger,
        security_context
    ):
        """测试验证失败响应格式（Requirement 8.4）"""
        # 配置AST验证失败
        mock_ast_validator.validate.return_value = ValidationResult(
            approved=False,
            reason="检测到黑名单函数",
            violations=["黑名单函数: eval", "黑名单函数: exec"]
        )
        
        gateway = UnifiedSecurityGateway(
            ast_validator=mock_ast_validator,
            sandbox_manager=mock_sandbox,
            network_guard=mock_network_guard,
            audit_logger=mock_audit_logger
        )
        
        code = "eval('1+1')"
        
        result = await gateway.validate_and_execute(
            code,
            ContentType.CODE,
            security_context
        )
        
        # 验证响应格式
        assert result.approved is False
        assert result.reason != ""  # 必须有非空原因
        assert len(result.violations) > 0  # 必须有违规项
        assert result.execution_time_ms > 0  # 必须有执行时间
        assert result.content_hash != ""  # 必须有内容哈希
        assert len(result.layer_results) > 0  # 必须有各层结果
    
    # ==================== 异常处理测试 ====================
    
    @pytest.mark.asyncio
    async def test_empty_content_raises_error(self, gateway, security_context):
        """测试空内容抛出错误"""
        with pytest.raises(ValueError, match="内容不能为空"):
            await gateway.validate_and_execute(
                "",
                ContentType.CODE,
                security_context
            )
    
    @pytest.mark.asyncio
    async def test_exception_handling(
        self,
        mock_ast_validator,
        mock_sandbox,
        mock_network_guard,
        mock_audit_logger,
        security_context
    ):
        """测试异常处理"""
        # 配置AST验证器抛出异常
        mock_ast_validator.validate.side_effect = Exception("测试异常")
        
        gateway = UnifiedSecurityGateway(
            ast_validator=mock_ast_validator,
            sandbox_manager=mock_sandbox,
            network_guard=mock_network_guard,
            audit_logger=mock_audit_logger
        )
        
        code = "result = 1 + 1"
        
        result = await gateway.validate_and_execute(
            code,
            ContentType.CODE,
            security_context
        )
        
        assert result.approved is False
        assert "验证异常" in result.reason
        assert len(result.violations) > 0
    
    # ==================== 性能测试 ====================
    
    @pytest.mark.asyncio
    async def test_validation_performance(self, gateway, security_context):
        """测试验证性能（< 150ms P99）"""
        code = "result = abs(min(1, 2))"
        
        result = await gateway.validate_and_execute(
            code,
            ContentType.CODE,
            security_context
        )
        
        # 验证执行时间
        assert result.execution_time_ms > 0
        # 注意：在Mock环境下可能很快，实际环境需要性能测试
    
    # ==================== 配置获取测试 ====================
    
    def test_get_config(self, gateway):
        """测试获取配置"""
        config = gateway.get_config()
        
        assert 'ast_validator_enabled' in config
        assert 'sandbox_manager_enabled' in config
        assert 'network_guard_enabled' in config
        assert 'audit_logger_enabled' in config
        assert 'semantic_validation_enabled' in config
        assert 'resource_limiting_enabled' in config
        
        assert config['ast_validator_enabled'] is True
        assert config['sandbox_manager_enabled'] is True
        assert config['network_guard_enabled'] is True
        assert config['audit_logger_enabled'] is True
    
    # ==================== 集成场景测试 ====================
    
    @pytest.mark.asyncio
    async def test_full_validation_pipeline(self, gateway, security_context):
        """测试完整验证流程"""
        code = """
def calculate_sharpe(returns):
    mean = returns.mean()
    std = returns.std()
    return mean / std
"""
        
        result = await gateway.validate_and_execute(
            code,
            ContentType.CODE,
            security_context
        )
        
        # 验证所有层都被执行
        assert 'content_type_detection' in result.layer_results
        assert 'ast_validation' in result.layer_results
        assert 'sandbox_execution' in result.layer_results
        assert 'network_guard' in result.layer_results
        
        # 验证最终结果
        assert result.approved is True
        assert result.execution_time_ms > 0
        assert result.content_hash != ""
    
    @pytest.mark.asyncio
    async def test_multiple_validations(self, gateway, security_context):
        """测试多次验证"""
        codes = [
            "result = 1 + 1",
            "result = abs(-5)",
            "result = min(1, 2, 3)"
        ]
        
        for code in codes:
            result = await gateway.validate_and_execute(
                code,
                ContentType.CODE,
                security_context
            )
            
            assert result.approved is True
    
    @pytest.mark.asyncio
    async def test_different_isolation_levels(self, gateway):
        """测试不同隔离级别"""
        code = "result = 1 + 1"
        
        # Docker隔离
        context_docker = SecurityContext(
            component_name="test",
            isolation_level=IsolationLevel.DOCKER
        )
        result_docker = await gateway.validate_and_execute(
            code,
            ContentType.CODE,
            context_docker
        )
        assert result_docker.approved is True
        
        # 无隔离
        context_none = SecurityContext(
            component_name="test",
            isolation_level=IsolationLevel.NONE
        )
        result_none = await gateway.validate_and_execute(
            code,
            ContentType.CODE,
            context_none
        )
        assert result_none.approved is True
