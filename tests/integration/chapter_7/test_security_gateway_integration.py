"""UnifiedSecurityGateway集成测试

白皮书依据: 第七章 7.1 统一安全网关

测试安全网关与各代码执行点的集成：
- Scholar代码执行
- 因子表达式执行
- 策略代码执行
- 完整安全流程

Property 29: Security Gateway Coverage
Validates: Requirements 10.5
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, Any

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


class TestSecurityGatewayScholarIntegration:
    """安全网关与Scholar代码执行集成测试
    
    白皮书依据: 第七章 7.1 统一安全网关
    验证需求: Requirements 10.5
    """
    
    @pytest.fixture
    def mock_components(self):
        """创建Mock组件"""
        ast_validator = Mock(spec=ASTWhitelistValidator)
        ast_validator.validate.return_value = ValidationResult(
            approved=True,
            reason="验证通过"
        )
        
        sandbox = Mock(spec=DockerSandbox)
        sandbox.execute = AsyncMock(return_value=ExecutionResult(
            success=True,
            output="执行成功"
        ))
        sandbox.get_container_config.return_value = {
            'image': 'python:3.11-slim',
            'memory_limit_mb': 512
        }
        
        network_guard = Mock(spec=NetworkGuard)
        network_guard.get_config.return_value = {
            'whitelist_domains': ['pypi.org'],
            'blacklist_ip_ranges': ['10.0.0.0/8']
        }
        
        audit_logger = Mock(spec=AuditLogger)
        audit_logger.log_event.return_value = None
        
        return {
            'ast_validator': ast_validator,
            'sandbox': sandbox,
            'network_guard': network_guard,
            'audit_logger': audit_logger
        }
    
    @pytest.fixture
    def gateway(self, mock_components):
        """创建安全网关实例"""
        return UnifiedSecurityGateway(
            ast_validator=mock_components['ast_validator'],
            sandbox_manager=mock_components['sandbox'],
            network_guard=mock_components['network_guard'],
            audit_logger=mock_components['audit_logger']
        )
    
    @pytest.mark.asyncio
    async def test_scholar_code_execution_safe(self, gateway):
        """测试Scholar安全代码执行
        
        白皮书依据: 第七章 7.1 统一安全网关
        验证需求: Requirements 10.5
        
        集成流程：
        1. Scholar生成因子代码
        2. 安全网关验证代码
        3. 沙箱执行代码
        4. 返回执行结果
        """
        # Scholar生成的因子代码
        scholar_code = """
def calculate_momentum(close, period=20):
    return close / close.shift(period) - 1
"""
        
        context = SecurityContext(
            component_name="scholar",
            user_id="system",
            isolation_level=IsolationLevel.DOCKER
        )
        
        result = await gateway.validate_and_execute(
            scholar_code,
            ContentType.CODE,
            context
        )
        
        assert result.approved is True
        assert 'ast_validation' in result.layer_results
        assert 'sandbox_execution' in result.layer_results
    
    @pytest.mark.asyncio
    async def test_scholar_code_execution_blocked(self, mock_components):
        """测试Scholar危险代码被阻止
        
        白皮书依据: 第七章 7.1 统一安全网关
        验证需求: Requirements 10.5
        
        集成流程：
        1. Scholar生成包含危险函数的代码
        2. 安全网关检测到危险函数
        3. 拒绝执行并返回详细原因
        """
        # 配置AST验证器拒绝危险代码
        mock_components['ast_validator'].validate.return_value = ValidationResult(
            approved=False,
            reason="检测到黑名单函数",
            violations=["黑名单函数: eval"]
        )
        
        gateway = UnifiedSecurityGateway(
            ast_validator=mock_components['ast_validator'],
            sandbox_manager=mock_components['sandbox'],
            network_guard=mock_components['network_guard'],
            audit_logger=mock_components['audit_logger']
        )
        
        # 危险代码
        dangerous_code = "result = eval('1+1')"
        
        context = SecurityContext(
            component_name="scholar",
            user_id="system",
            isolation_level=IsolationLevel.DOCKER
        )
        
        result = await gateway.validate_and_execute(
            dangerous_code,
            ContentType.CODE,
            context
        )
        
        assert result.approved is False
        assert "AST验证失败" in result.reason
        assert len(result.violations) > 0


class TestSecurityGatewayFactorExpressionIntegration:
    """安全网关与因子表达式执行集成测试
    
    白皮书依据: 第七章 7.1 统一安全网关
    验证需求: Requirements 10.5
    """
    
    @pytest.fixture
    def mock_components(self):
        """创建Mock组件"""
        ast_validator = Mock(spec=ASTWhitelistValidator)
        ast_validator.validate.return_value = ValidationResult(
            approved=True,
            reason="验证通过"
        )
        
        sandbox = Mock(spec=DockerSandbox)
        sandbox.execute = AsyncMock(return_value=ExecutionResult(
            success=True,
            output="0.05"
        ))
        sandbox.get_container_config.return_value = {}
        
        network_guard = Mock(spec=NetworkGuard)
        network_guard.get_config.return_value = {}
        
        audit_logger = Mock(spec=AuditLogger)
        
        return {
            'ast_validator': ast_validator,
            'sandbox': sandbox,
            'network_guard': network_guard,
            'audit_logger': audit_logger
        }
    
    @pytest.fixture
    def gateway(self, mock_components):
        """创建安全网关实例"""
        return UnifiedSecurityGateway(
            ast_validator=mock_components['ast_validator'],
            sandbox_manager=mock_components['sandbox'],
            network_guard=mock_components['network_guard'],
            audit_logger=mock_components['audit_logger']
        )
    
    @pytest.mark.asyncio
    async def test_factor_expression_safe(self, gateway):
        """测试安全因子表达式执行
        
        白皮书依据: 第七章 7.1 统一安全网关
        验证需求: Requirements 10.5
        
        集成流程：
        1. 遗传算法生成因子表达式
        2. 安全网关验证表达式
        3. 沙箱执行表达式
        4. 返回因子值
        """
        # 因子表达式
        factor_expression = "rank(close) / delay(close, 1) - 1"
        
        context = SecurityContext(
            component_name="genetic_miner",
            user_id="system",
            isolation_level=IsolationLevel.DOCKER
        )
        
        result = await gateway.validate_and_execute(
            factor_expression,
            ContentType.EXPRESSION,
            context
        )
        
        assert result.approved is True
        assert result.layer_results['content_type_detection']['detected_type'] == 'expression'
    
    @pytest.mark.asyncio
    async def test_factor_expression_with_injection(self, mock_components):
        """测试因子表达式注入攻击被阻止
        
        白皮书依据: 第七章 7.1 统一安全网关
        验证需求: Requirements 10.5
        
        集成流程：
        1. 攻击者尝试在因子表达式中注入恶意代码
        2. 安全网关检测到注入
        3. 拒绝执行
        """
        # 配置AST验证器拒绝注入
        mock_components['ast_validator'].validate.return_value = ValidationResult(
            approved=False,
            reason="检测到代码注入",
            violations=["黑名单函数: __import__"]
        )
        
        gateway = UnifiedSecurityGateway(
            ast_validator=mock_components['ast_validator'],
            sandbox_manager=mock_components['sandbox'],
            network_guard=mock_components['network_guard'],
            audit_logger=mock_components['audit_logger']
        )
        
        # 注入攻击
        malicious_expression = "rank(close); __import__('os').system('rm -rf /')"
        
        context = SecurityContext(
            component_name="genetic_miner",
            user_id="system",
            isolation_level=IsolationLevel.DOCKER
        )
        
        result = await gateway.validate_and_execute(
            malicious_expression,
            ContentType.EXPRESSION,
            context
        )
        
        assert result.approved is False


class TestSecurityGatewayStrategyCodeIntegration:
    """安全网关与策略代码执行集成测试
    
    白皮书依据: 第七章 7.1 统一安全网关
    验证需求: Requirements 10.5
    """
    
    @pytest.fixture
    def mock_components(self):
        """创建Mock组件"""
        ast_validator = Mock(spec=ASTWhitelistValidator)
        ast_validator.validate.return_value = ValidationResult(
            approved=True,
            reason="验证通过"
        )
        
        sandbox = Mock(spec=DockerSandbox)
        sandbox.execute = AsyncMock(return_value=ExecutionResult(
            success=True,
            output="策略执行成功"
        ))
        sandbox.get_container_config.return_value = {}
        
        network_guard = Mock(spec=NetworkGuard)
        network_guard.get_config.return_value = {}
        
        audit_logger = Mock(spec=AuditLogger)
        
        return {
            'ast_validator': ast_validator,
            'sandbox': sandbox,
            'network_guard': network_guard,
            'audit_logger': audit_logger
        }
    
    @pytest.fixture
    def gateway(self, mock_components):
        """创建安全网关实例"""
        return UnifiedSecurityGateway(
            ast_validator=mock_components['ast_validator'],
            sandbox_manager=mock_components['sandbox'],
            network_guard=mock_components['network_guard'],
            audit_logger=mock_components['audit_logger']
        )
    
    @pytest.mark.asyncio
    async def test_strategy_code_safe(self, gateway):
        """测试安全策略代码执行
        
        白皮书依据: 第七章 7.1 统一安全网关
        验证需求: Requirements 10.5
        
        集成流程：
        1. 策略生成器生成策略代码
        2. 安全网关验证代码
        3. 沙箱执行代码
        4. 返回策略信号
        """
        # 策略代码
        strategy_code = """
class MomentumStrategy:
    def __init__(self, period=20):
        self.period = period
    
    def generate_signal(self, data):
        momentum = data['close'] / data['close'].shift(self.period) - 1
        return momentum > 0
"""
        
        context = SecurityContext(
            component_name="strategy_generator",
            user_id="system",
            isolation_level=IsolationLevel.DOCKER
        )
        
        result = await gateway.validate_and_execute(
            strategy_code,
            ContentType.CODE,
            context
        )
        
        assert result.approved is True
    
    @pytest.mark.asyncio
    async def test_strategy_code_network_access_blocked(self, gateway):
        """测试策略代码网络访问被阻止
        
        白皮书依据: 第七章 7.1 统一安全网关
        验证需求: Requirements 10.5
        
        集成流程：
        1. 策略代码尝试访问网络
        2. 安全网关检测到网络访问
        3. 拒绝执行
        """
        # 包含网络访问的策略代码
        network_code = """
import requests
response = requests.get('https://api.example.com/data')
"""
        
        context = SecurityContext(
            component_name="strategy_generator",
            user_id="system",
            isolation_level=IsolationLevel.DOCKER
        )
        
        result = await gateway.validate_and_execute(
            network_code,
            ContentType.CODE,
            context
        )
        
        assert result.approved is False
        assert "网络访问违规" in result.reason


class TestSecurityGatewayFullPipelineIntegration:
    """安全网关完整流程集成测试
    
    白皮书依据: 第七章 7.1 统一安全网关
    验证需求: Requirements 10.5
    Property 29: Security Gateway Coverage
    """
    
    @pytest.fixture
    def mock_components(self):
        """创建Mock组件"""
        ast_validator = Mock(spec=ASTWhitelistValidator)
        ast_validator.validate.return_value = ValidationResult(
            approved=True,
            reason="验证通过"
        )
        
        sandbox = Mock(spec=DockerSandbox)
        sandbox.execute = AsyncMock(return_value=ExecutionResult(
            success=True,
            output="执行成功"
        ))
        sandbox.get_container_config.return_value = {}
        
        network_guard = Mock(spec=NetworkGuard)
        network_guard.get_config.return_value = {}
        
        audit_logger = Mock(spec=AuditLogger)
        
        return {
            'ast_validator': ast_validator,
            'sandbox': sandbox,
            'network_guard': network_guard,
            'audit_logger': audit_logger
        }
    
    @pytest.fixture
    def gateway(self, mock_components):
        """创建安全网关实例"""
        return UnifiedSecurityGateway(
            ast_validator=mock_components['ast_validator'],
            sandbox_manager=mock_components['sandbox'],
            network_guard=mock_components['network_guard'],
            audit_logger=mock_components['audit_logger'],
            enable_semantic_validation=True,
            enable_resource_limiting=True
        )
    
    @pytest.mark.asyncio
    async def test_full_7_layer_defense(self, gateway, mock_components):
        """测试完整7层防御流程
        
        白皮书依据: 第七章 7.1 统一安全网关
        验证需求: Requirements 10.5
        Property 29: Security Gateway Coverage
        
        完整流程：
        1. Layer 1: 内容类型识别
        2. Layer 2: AST白名单验证
        3. Layer 3: 语义验证
        4. Layer 4: 沙箱隔离
        5. Layer 5: 网络防护
        6. Layer 6: 资源限制
        7. Layer 7: 审计日志
        """
        code = """
def safe_function(x):
    return abs(x) + min(1, 2)
"""
        
        context = SecurityContext(
            component_name="test_component",
            user_id="test_user",
            session_id="test_session",
            isolation_level=IsolationLevel.DOCKER
        )
        
        result = await gateway.validate_and_execute(
            code,
            ContentType.CODE,
            context
        )
        
        # 验证所有层都被执行
        assert result.approved is True
        assert 'content_type_detection' in result.layer_results  # Layer 1
        assert 'ast_validation' in result.layer_results  # Layer 2
        assert 'semantic_validation' in result.layer_results  # Layer 3
        assert 'sandbox_execution' in result.layer_results  # Layer 4
        assert 'network_guard' in result.layer_results  # Layer 5
        assert 'resource_limiting' in result.layer_results  # Layer 6
        
        # 验证审计日志被调用 (Layer 7)
        mock_components['audit_logger'].log_event.assert_called()
    
    @pytest.mark.asyncio
    async def test_audit_trail_completeness(self, gateway, mock_components):
        """测试审计追踪完整性
        
        白皮书依据: 第七章 7.5 审计日志
        验证需求: Requirements 10.5
        
        验证：
        1. 所有验证事件都被记录
        2. 审计日志包含完整上下文
        3. 成功和失败都被记录
        """
        code = "result = 1 + 1"
        
        context = SecurityContext(
            component_name="audit_test",
            user_id="audit_user",
            session_id="audit_session",
            isolation_level=IsolationLevel.DOCKER
        )
        
        await gateway.validate_and_execute(
            code,
            ContentType.CODE,
            context
        )
        
        # 验证审计日志被调用
        mock_components['audit_logger'].log_event.assert_called_once()
        
        # 验证审计日志内容
        call_args = mock_components['audit_logger'].log_event.call_args[0][0]
        assert call_args['event_type'] == 'SECURITY_GATEWAY_VALIDATION'
        assert call_args['component_name'] == 'audit_test'
        assert call_args['user_id'] == 'audit_user'
        assert call_args['session_id'] == 'audit_session'
        assert 'content_hash' in call_args
        assert 'execution_time_ms' in call_args
    
    @pytest.mark.asyncio
    async def test_multiple_execution_points_coverage(self, gateway):
        """测试多个执行点覆盖
        
        白皮书依据: 第七章 7.1 统一安全网关
        验证需求: Requirements 10.5
        Property 29: Security Gateway Coverage
        
        验证所有代码执行点都通过安全网关：
        1. Scholar代码执行
        2. 因子表达式执行
        3. 策略代码执行
        """
        execution_points = [
            {
                'component': 'scholar',
                'content': 'def analyze(): return 1',
                'content_type': ContentType.CODE
            },
            {
                'component': 'genetic_miner',
                'content': 'rank(close) / delay(close, 1)',
                'content_type': ContentType.EXPRESSION
            },
            {
                'component': 'strategy_generator',
                'content': 'class Strategy: pass',
                'content_type': ContentType.CODE
            }
        ]
        
        for point in execution_points:
            context = SecurityContext(
                component_name=point['component'],
                user_id="system",
                isolation_level=IsolationLevel.DOCKER
            )
            
            result = await gateway.validate_and_execute(
                point['content'],
                point['content_type'],
                context
            )
            
            assert result.approved is True, f"执行点 {point['component']} 验证失败"
    
    @pytest.mark.asyncio
    async def test_performance_under_load(self, gateway):
        """测试负载下的性能
        
        白皮书依据: 第七章 7.1 统一安全网关
        验证需求: Requirements 10.5
        
        性能要求：
        - 总验证时间 < 150ms (P99)
        """
        code = "result = abs(min(1, 2))"
        
        context = SecurityContext(
            component_name="performance_test",
            user_id="system",
            isolation_level=IsolationLevel.DOCKER
        )
        
        # 执行多次验证
        execution_times = []
        for _ in range(10):
            result = await gateway.validate_and_execute(
                code,
                ContentType.CODE,
                context
            )
            execution_times.append(result.execution_time_ms)
        
        # 验证平均执行时间
        avg_time = sum(execution_times) / len(execution_times)
        assert avg_time < 150, f"平均执行时间 {avg_time:.2f}ms 超过150ms限制"


class TestSecurityGatewayErrorHandling:
    """安全网关错误处理集成测试
    
    白皮书依据: 第七章 7.6 错误处理
    """
    
    @pytest.fixture
    def mock_components(self):
        """创建Mock组件"""
        ast_validator = Mock(spec=ASTWhitelistValidator)
        ast_validator.validate.return_value = ValidationResult(
            approved=True,
            reason="验证通过"
        )
        
        sandbox = Mock(spec=DockerSandbox)
        sandbox.execute = AsyncMock(return_value=ExecutionResult(
            success=True,
            output="执行成功"
        ))
        sandbox.get_container_config.return_value = {}
        
        network_guard = Mock(spec=NetworkGuard)
        network_guard.get_config.return_value = {}
        
        audit_logger = Mock(spec=AuditLogger)
        
        return {
            'ast_validator': ast_validator,
            'sandbox': sandbox,
            'network_guard': network_guard,
            'audit_logger': audit_logger
        }
    
    @pytest.mark.asyncio
    async def test_sandbox_failure_handling(self, mock_components):
        """测试沙箱失败处理
        
        白皮书依据: 第七章 7.6 错误处理
        
        验证：
        1. 沙箱执行失败时返回详细错误
        2. 错误被记录到审计日志
        """
        # 配置沙箱返回失败
        mock_components['sandbox'].execute = AsyncMock(return_value=ExecutionResult(
            success=False,
            error="容器启动超时"
        ))
        
        gateway = UnifiedSecurityGateway(
            ast_validator=mock_components['ast_validator'],
            sandbox_manager=mock_components['sandbox'],
            network_guard=mock_components['network_guard'],
            audit_logger=mock_components['audit_logger']
        )
        
        code = "while True: pass"
        
        context = SecurityContext(
            component_name="test",
            isolation_level=IsolationLevel.DOCKER
        )
        
        result = await gateway.validate_and_execute(
            code,
            ContentType.CODE,
            context
        )
        
        assert result.approved is False
        assert "沙箱执行失败" in result.reason
    
    @pytest.mark.asyncio
    async def test_graceful_degradation(self, mock_components):
        """测试优雅降级
        
        白皮书依据: 第七章 7.6 错误处理
        
        验证：
        1. 当Docker不可用时降级到NONE隔离级别
        2. 仍然执行AST验证
        """
        gateway = UnifiedSecurityGateway(
            ast_validator=mock_components['ast_validator'],
            sandbox_manager=mock_components['sandbox'],
            network_guard=mock_components['network_guard'],
            audit_logger=mock_components['audit_logger']
        )
        
        code = "result = 1 + 1"
        
        # 使用NONE隔离级别（跳过沙箱）
        context = SecurityContext(
            component_name="test",
            isolation_level=IsolationLevel.NONE
        )
        
        result = await gateway.validate_and_execute(
            code,
            ContentType.CODE,
            context
        )
        
        assert result.approved is True
        # 验证AST验证仍然执行
        assert 'ast_validation' in result.layer_results
        # 验证沙箱执行被跳过
        assert 'sandbox_execution' not in result.layer_results
