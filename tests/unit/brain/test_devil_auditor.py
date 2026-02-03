"""魔鬼审计器测试

白皮书依据: 第二章 2.4 The Devil (魔鬼审计)
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from src.brain.devil_auditor import (
    DevilAuditorV2, AuditResult, AuditIssue, AuditSeverity
)


class TestDevilAuditorV2:
    """测试魔鬼审计器 v2.0"""
    
    @pytest.fixture
    def auditor(self):
        """创建审计器实例"""
        with patch('src.brain.devil_auditor.get_container') as mock_container:
            mock_llm_gateway = Mock()
            mock_llm_gateway.call_llm = AsyncMock(return_value=Mock(content='{"issues": [], "overall_assessment": "OK", "confidence": 0.9}'))
            mock_event_bus = Mock()
            mock_event_bus.publish = AsyncMock()
            mock_container.return_value.resolve.side_effect = lambda x: {
                'LLMGateway': mock_llm_gateway,
                'EventBus': mock_event_bus
            }.get(x.__name__, Mock())
            
            return DevilAuditorV2()
    
    @pytest.mark.asyncio
    async def test_audit_strategy_valid_code(self, auditor):
        """测试审计有效代码"""
        valid_code = """
def calculate_factor(data):
    return data['close'].rolling(20).mean()
"""
        
        result = await auditor.audit_strategy(valid_code)
        
        assert isinstance(result, AuditResult)
        assert result.execution_time > 0
        assert result.audit_hash
        assert len(result.audit_hash) == 16
    
    @pytest.mark.asyncio
    async def test_audit_strategy_empty_code(self, auditor):
        """测试审计空代码"""
        with pytest.raises(ValueError, match="策略代码不能为空"):
            await auditor.audit_strategy("")
    
    @pytest.mark.asyncio
    async def test_audit_strategy_syntax_error(self, auditor):
        """测试语法错误检测"""
        invalid_code = """
def calculate_factor(data):
    return data['close'].rolling(20).mean(
"""  # 缺少右括号
        
        result = await auditor.audit_strategy(invalid_code)
        
        assert not result.approved
        assert result.confidence < 0.5
        assert any(issue.issue_type == "syntax_error" for issue in result.issues)
        assert any(issue.severity == AuditSeverity.CRITICAL for issue in result.issues)
    
    @pytest.mark.asyncio
    async def test_future_function_detection(self, auditor):
        """测试未来函数检测"""
        future_function_code = """
def calculate_factor(data):
    return data['close'].shift(-1)  # 使用未来数据
"""
        
        result = await auditor.audit_strategy(future_function_code)
        
        assert not result.approved
        future_issues = [issue for issue in result.issues if issue.issue_type == "future_function"]
        assert len(future_issues) > 0
        assert all(issue.severity == AuditSeverity.CRITICAL for issue in future_issues)
    
    @pytest.mark.asyncio
    async def test_dangerous_function_detection(self, auditor):
        """测试危险函数检测"""
        dangerous_code = """
def calculate_factor(data):
    eval("malicious_code")  # 危险函数
    return data['close']
"""
        
        result = await auditor.audit_strategy(dangerous_code)
        
        assert not result.approved
        dangerous_issues = [issue for issue in result.issues if issue.issue_type == "dangerous_function"]
        assert len(dangerous_issues) > 0
        assert all(issue.severity == AuditSeverity.CRITICAL for issue in dangerous_issues)
    
    @pytest.mark.asyncio
    async def test_network_access_detection(self, auditor):
        """测试网络访问检测"""
        network_code = """
import requests
def calculate_factor(data):
    response = requests.get("http://example.com")  # 网络访问
    return data['close']
"""
        
        result = await auditor.audit_strategy(network_code)
        
        network_issues = [issue for issue in result.issues if issue.issue_type == "network_access"]
        assert len(network_issues) > 0
        assert all(issue.severity == AuditSeverity.HIGH for issue in network_issues)
    
    @pytest.mark.asyncio
    async def test_file_access_detection(self, auditor):
        """测试文件访问检测"""
        file_code = """
def calculate_factor(data):
    with open("file.txt", "r") as f:  # 文件访问
        content = f.read()
    return data['close']
"""
        
        result = await auditor.audit_strategy(file_code)
        
        file_issues = [issue for issue in result.issues if issue.issue_type == "file_access"]
        assert len(file_issues) > 0
        assert all(issue.severity == AuditSeverity.HIGH for issue in file_issues)
    
    @pytest.mark.asyncio
    async def test_overfitting_detection(self, auditor):
        """测试过拟合检测"""
        overfitting_code = """
def calculate_factor(data):
    # 大量参数和复杂条件
    """ + "param = 1.234567\n" * 60 + """
    if data['close'] > 10 and data['volume'] > 1000 and data['high'] > data['low']:
        return data['close'] * param
    return data['close']
"""
        
        result = await auditor.audit_strategy(overfitting_code)
        
        overfitting_issues = [
            issue for issue in result.issues 
            if issue.issue_type in ["too_many_parameters", "magic_numbers"]
        ]
        assert len(overfitting_issues) > 0
    
    @pytest.mark.asyncio
    async def test_code_complexity_detection(self, auditor):
        """测试代码复杂度检测"""
        complex_code = """
def calculate_factor(data):
    # 超长代码
    """ + "    line = data['close']\n" * 1100 + """
    return line
"""
        
        result = await auditor.audit_strategy(complex_code)
        
        complexity_issues = [issue for issue in result.issues if issue.issue_type == "code_too_long"]
        assert len(complexity_issues) > 0
        assert all(issue.severity == AuditSeverity.MEDIUM for issue in complexity_issues)
    
    @pytest.mark.asyncio
    async def test_deep_reasoning_audit_success(self, auditor):
        """测试DeepSeek-R1推理审计成功"""
        # Mock LLM响应
        mock_response = Mock()
        mock_response.content = '''
        {
            "issues": [
                {
                    "type": "logic_error",
                    "severity": "medium",
                    "description": "逻辑可能存在问题",
                    "suggestion": "检查计算逻辑"
                }
            ],
            "overall_assessment": "策略基本可行",
            "confidence": 0.8
        }
        '''
        
        auditor.llm_gateway.call_llm = AsyncMock(return_value=mock_response)
        
        code = "def factor(data): return data['close']"
        result = await auditor.audit_strategy(code)
        
        # 验证LLM被调用
        auditor.llm_gateway.call_llm.assert_called_once()
        
        # 验证解析出的问题
        llm_issues = [issue for issue in result.issues if issue.location == "LLM分析"]
        assert len(llm_issues) > 0
    
    @pytest.mark.asyncio
    async def test_deep_reasoning_audit_failure(self, auditor):
        """测试DeepSeek-R1推理审计失败"""
        # Mock LLM调用失败
        auditor.llm_gateway.call_llm = AsyncMock(side_effect=Exception("LLM调用失败"))
        
        code = "def factor(data): return data['close']"
        result = await auditor.audit_strategy(code)
        
        # 验证有失败问题记录
        failure_issues = [issue for issue in result.issues if issue.issue_type == "reasoning_audit_failed"]
        assert len(failure_issues) > 0
    
    @pytest.mark.asyncio
    async def test_batch_audit(self, auditor):
        """测试批量审计"""
        strategies = [
            {"code": "def factor1(data): return data['close']", "metadata": {"name": "factor1"}},
            {"code": "def factor2(data): return data['volume']", "metadata": {"name": "factor2"}},
            {"code": "invalid syntax", "metadata": {"name": "invalid"}}
        ]
        
        results = await auditor.batch_audit(strategies)
        
        assert len(results) == 3
        assert all(isinstance(result, AuditResult) for result in results)
        
        # 第三个策略应该失败
        assert not results[2].approved
        # audit_hash应该是一个有效的hash，不是"failed"
        assert results[2].audit_hash
        assert len(results[2].audit_hash) == 16
    
    def test_statistics_tracking(self, auditor):
        """测试统计信息跟踪"""
        # 初始统计
        stats = auditor.get_statistics()
        assert stats['audit_count'] == 0
        assert stats['approval_rate'] == 0.0
        assert stats['avg_confidence'] == 0.0
        
        # 模拟更新统计
        mock_result = AuditResult(
            approved=True,
            confidence=0.8,
            issues=[],
            suggestions=[],
            execution_time=1.0,
            audit_hash="test123"
        )
        
        auditor._update_statistics(mock_result)
        
        stats = auditor.get_statistics()
        assert stats['audit_count'] == 1
        assert stats['approval_rate'] == 1.0
        assert stats['avg_confidence'] == 0.8
    
    def test_audit_issue_validation(self):
        """测试审计问题数据验证"""
        # 有效的审计问题
        issue = AuditIssue(
            issue_type="test_issue",
            severity=AuditSeverity.MEDIUM,
            description="测试问题",
            location="第1行",
            suggestion="修复建议"
        )
        
        assert issue.issue_type == "test_issue"
        assert issue.severity == AuditSeverity.MEDIUM
        assert issue.description == "测试问题"
    
    def test_audit_result_validation(self):
        """测试审计结果数据验证"""
        issues = [
            AuditIssue(
                issue_type="test",
                severity=AuditSeverity.LOW,
                description="测试",
                location="测试",
                suggestion="测试"
            )
        ]
        
        result = AuditResult(
            approved=True,
            confidence=0.9,
            issues=issues,
            suggestions=["建议1", "建议2"],
            execution_time=2.5,
            audit_hash="abc123def456"
        )
        
        assert result.approved is True
        assert result.confidence == 0.9
        assert len(result.issues) == 1
        assert len(result.suggestions) == 2
        assert result.execution_time == 2.5
        assert result.audit_hash == "abc123def456"


class TestAuditIssue:
    """测试审计问题类"""
    
    def test_audit_issue_creation(self):
        """测试审计问题创建"""
        issue = AuditIssue(
            issue_type="syntax_error",
            severity=AuditSeverity.CRITICAL,
            description="语法错误",
            location="第5行",
            suggestion="修复语法",
            code_snippet="invalid code"
        )
        
        assert issue.issue_type == "syntax_error"
        assert issue.severity == AuditSeverity.CRITICAL
        assert issue.description == "语法错误"
        assert issue.location == "第5行"
        assert issue.suggestion == "修复语法"
        assert issue.code_snippet == "invalid code"


class TestAuditResult:
    """测试审计结果类"""
    
    def test_audit_result_creation(self):
        """测试审计结果创建"""
        issues = [
            AuditIssue(
                issue_type="warning",
                severity=AuditSeverity.LOW,
                description="警告",
                location="全局",
                suggestion="优化代码"
            )
        ]
        
        result = AuditResult(
            approved=False,
            confidence=0.6,
            issues=issues,
            suggestions=["建议1"],
            execution_time=1.5,
            audit_hash="hash123"
        )
        
        assert result.approved is False
        assert result.confidence == 0.6
        assert len(result.issues) == 1
        assert result.issues[0].issue_type == "warning"
        assert len(result.suggestions) == 1
        assert result.execution_time == 1.5
        assert result.audit_hash == "hash123"


class TestAuditSeverity:
    """测试审计严重程度枚举"""
    
    def test_severity_values(self):
        """测试严重程度值"""
        assert AuditSeverity.LOW.value == "low"
        assert AuditSeverity.MEDIUM.value == "medium"
        assert AuditSeverity.HIGH.value == "high"
        assert AuditSeverity.CRITICAL.value == "critical"
    
    def test_severity_comparison(self):
        """测试严重程度比较"""
        severities = [
            AuditSeverity.LOW,
            AuditSeverity.MEDIUM,
            AuditSeverity.HIGH,
            AuditSeverity.CRITICAL
        ]
        
        # 验证枚举值存在
        for severity in severities:
            assert severity in AuditSeverity


if __name__ == "__main__":
    pytest.main([__file__])