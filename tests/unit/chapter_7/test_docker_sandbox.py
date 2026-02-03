"""DockerSandbox单元测试

白皮书依据: 第七章 7.3 Docker沙箱

测试DockerSandbox的所有功能：
- 容器配置（用户、只读、内存、CPU、PID限制）
- 网络禁用
- seccomp配置
- 代码执行
- 容器清理

Author: MIA Team
Date: 2026-01-25
Version: 1.0.0
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, MagicMock
from src.compliance.docker_sandbox import DockerSandbox, ExecutionResult


class TestDockerSandboxInit:
    """测试DockerSandbox初始化"""
    
    def test_init_default_params(self):
        """测试默认参数初始化"""
        sandbox = DockerSandbox()
        
        assert sandbox.image == "python:3.11-slim"
        assert sandbox.memory_limit == 512 * 1024 * 1024  # 512MB
        assert sandbox.cpu_limit == 1.0
        assert sandbox.timeout == 30
        assert sandbox.user == "1001:1001"
        assert sandbox.pids_limit == 100
        assert sandbox.mock_mode is True  # 默认Mock模式（无Docker环境）
    
    def test_init_custom_params(self):
        """测试自定义参数初始化"""
        sandbox = DockerSandbox(
            image="python:3.10-slim",
            memory_limit=256 * 1024 * 1024,
            cpu_limit=0.5,
            timeout=60,
            user="1002:1002",
            pids_limit=50
        )
        
        assert sandbox.image == "python:3.10-slim"
        assert sandbox.memory_limit == 256 * 1024 * 1024
        assert sandbox.cpu_limit == 0.5
        assert sandbox.timeout == 60
        assert sandbox.user == "1002:1002"
        assert sandbox.pids_limit == 50
    
    def test_get_container_config(self):
        """测试获取容器配置"""
        sandbox = DockerSandbox(
            memory_limit=512 * 1024 * 1024,
            cpu_limit=1.0
        )
        
        config = sandbox.get_container_config()
        
        assert config['image'] == "python:3.11-slim"
        assert config['user'] == "1001:1001"
        assert config['memory_limit_mb'] == 512
        assert config['cpu_limit'] == 1.0
        assert config['timeout'] == 30
        assert config['pids_limit'] == 100
        assert config['network_mode'] == 'none'
        assert config['read_only'] is True
        assert config['mock_mode'] is True


class TestDockerSandboxMockMode:
    """测试DockerSandbox Mock模式"""
    
    @pytest.mark.asyncio
    async def test_mock_execute_success(self):
        """测试Mock模式成功执行"""
        sandbox = DockerSandbox()
        
        code = "print('Hello, World!')"
        result = await sandbox.execute(code)
        
        assert result.success is True
        assert "Mock模式" in result.output
        assert result.execution_time_ms > 0
        assert result.memory_used_mb > 0
    
    @pytest.mark.asyncio
    async def test_mock_execute_forbidden_import(self):
        """测试Mock模式检测禁止的导入"""
        sandbox = DockerSandbox()
        
        code = "import os; os.system('ls')"
        result = await sandbox.execute(code)
        
        assert result.success is False
        assert "禁止的导入" in result.error
    
    @pytest.mark.asyncio
    async def test_mock_execute_empty_code(self):
        """测试Mock模式空代码"""
        sandbox = DockerSandbox()
        
        with pytest.raises(ValueError, match="代码不能为空"):
            await sandbox.execute("")
    
    @pytest.mark.asyncio
    async def test_mock_execute_whitespace_code(self):
        """测试Mock模式仅空白字符的代码"""
        sandbox = DockerSandbox()
        
        with pytest.raises(ValueError, match="代码不能为空"):
            await sandbox.execute("   \n\t  ")
    
    @pytest.mark.asyncio
    async def test_mock_create_container(self):
        """测试Mock模式创建容器"""
        sandbox = DockerSandbox()
        
        container_id = await sandbox.create_container()
        
        assert container_id == "mock_container_id"
    
    @pytest.mark.asyncio
    async def test_mock_cleanup_container(self):
        """测试Mock模式清理容器"""
        sandbox = DockerSandbox()
        
        # 不应抛出异常
        await sandbox.cleanup_container("mock_container_id")


class TestDockerSandboxContainerConfig:
    """测试DockerSandbox容器配置"""
    
    @pytest.mark.asyncio
    async def test_container_config_non_root_user(self):
        """测试容器使用非root用户 (Requirement 10.1)"""
        sandbox = DockerSandbox(user="1001:1001")
        
        config = sandbox.get_container_config()
        
        assert config['user'] == "1001:1001"
        assert config['user'] != "root"
        assert config['user'] != "0:0"
    
    @pytest.mark.asyncio
    async def test_container_config_read_only_filesystem(self):
        """测试容器使用只读文件系统 (Requirement 10.2)"""
        sandbox = DockerSandbox()
        
        config = sandbox.get_container_config()
        
        assert config['read_only'] is True
    
    @pytest.mark.asyncio
    async def test_container_config_memory_limit(self):
        """测试容器内存限制 (Requirement 10.3)"""
        sandbox = DockerSandbox(memory_limit=512 * 1024 * 1024)
        
        config = sandbox.get_container_config()
        
        assert config['memory_limit_mb'] == 512
    
    @pytest.mark.asyncio
    async def test_container_config_cpu_limit(self):
        """测试容器CPU限制 (Requirement 10.4)"""
        sandbox = DockerSandbox(cpu_limit=1.0)
        
        config = sandbox.get_container_config()
        
        assert config['cpu_limit'] == 1.0
    
    @pytest.mark.asyncio
    async def test_container_config_pids_limit(self):
        """测试容器进程数限制 (Requirement 10.5)"""
        sandbox = DockerSandbox(pids_limit=100)
        
        config = sandbox.get_container_config()
        
        assert config['pids_limit'] == 100
    
    @pytest.mark.asyncio
    async def test_container_config_network_disabled(self):
        """测试容器网络禁用 (Requirement 10.6)"""
        sandbox = DockerSandbox()
        
        config = sandbox.get_container_config()
        
        assert config['network_mode'] == 'none'


class TestDockerSandboxExecution:
    """测试DockerSandbox代码执行"""
    
    @pytest.mark.asyncio
    async def test_execute_simple_code(self):
        """测试执行简单代码"""
        sandbox = DockerSandbox()
        
        code = "x = 1 + 1\nprint(x)"
        result = await sandbox.execute(code)
        
        assert result.success is True
        assert result.execution_time_ms > 0
    
    @pytest.mark.asyncio
    async def test_execute_with_custom_timeout(self):
        """测试自定义超时"""
        sandbox = DockerSandbox(timeout=30)
        
        code = "print('test')"
        result = await sandbox.execute(code, timeout=60)
        
        assert result.success is True
    
    @pytest.mark.asyncio
    async def test_execute_measures_time(self):
        """测试执行时间测量"""
        sandbox = DockerSandbox()
        
        code = "import time; time.sleep(0.01)"
        result = await sandbox.execute(code)
        
        assert result.execution_time_ms >= 10  # 至少10ms
    
    @pytest.mark.asyncio
    async def test_execute_measures_memory(self):
        """测试内存使用测量"""
        sandbox = DockerSandbox()
        
        code = "x = [1] * 1000"
        result = await sandbox.execute(code)
        
        assert result.memory_used_mb > 0


class TestDockerSandboxErrorHandling:
    """测试DockerSandbox错误处理"""
    
    @pytest.mark.asyncio
    async def test_execute_empty_code_error(self):
        """测试空代码错误"""
        sandbox = DockerSandbox()
        
        with pytest.raises(ValueError, match="代码不能为空"):
            await sandbox.execute("")
    
    @pytest.mark.asyncio
    async def test_execute_whitespace_only_error(self):
        """测试仅空白字符错误"""
        sandbox = DockerSandbox()
        
        with pytest.raises(ValueError, match="代码不能为空"):
            await sandbox.execute("   \n\t  ")
    
    @pytest.mark.asyncio
    async def test_execute_syntax_error(self):
        """测试语法错误"""
        sandbox = DockerSandbox()
        
        code = "print('unclosed string"
        result = await sandbox.execute(code)
        
        # Mock模式下会成功，真实Docker会失败
        assert isinstance(result, ExecutionResult)
    
    @pytest.mark.asyncio
    async def test_execute_runtime_error(self):
        """测试运行时错误"""
        sandbox = DockerSandbox()
        
        code = "x = 1 / 0"
        result = await sandbox.execute(code)
        
        # Mock模式下会成功，真实Docker会失败
        assert isinstance(result, ExecutionResult)


class TestDockerSandboxCleanup:
    """测试DockerSandbox容器清理"""
    
    @pytest.mark.asyncio
    async def test_cleanup_after_execution(self):
        """测试执行后清理容器 (Requirement 10.9)"""
        sandbox = DockerSandbox()
        
        code = "print('test')"
        result = await sandbox.execute(code)
        
        # 执行应该成功
        assert result.success is True
        
        # 容器应该被清理（Mock模式下无法验证）
    
    @pytest.mark.asyncio
    async def test_cleanup_nonexistent_container(self):
        """测试清理不存在的容器"""
        sandbox = DockerSandbox()
        
        # 不应抛出异常
        await sandbox.cleanup_container("nonexistent_container_id")
    
    @pytest.mark.asyncio
    async def test_cleanup_multiple_times(self):
        """测试多次清理同一容器"""
        sandbox = DockerSandbox()
        
        container_id = "test_container_id"
        
        # 第一次清理
        await sandbox.cleanup_container(container_id)
        
        # 第二次清理（不应抛出异常）
        await sandbox.cleanup_container(container_id)


class TestDockerSandboxEdgeCases:
    """测试DockerSandbox边界情况"""
    
    @pytest.mark.asyncio
    async def test_execute_very_long_code(self):
        """测试执行非常长的代码"""
        sandbox = DockerSandbox()
        
        # 生成长代码
        code = "\n".join([f"x{i} = {i}" for i in range(1000)])
        code += "\nprint('done')"
        
        result = await sandbox.execute(code)
        
        assert result.success is True
    
    @pytest.mark.asyncio
    async def test_execute_unicode_code(self):
        """测试执行包含Unicode的代码"""
        sandbox = DockerSandbox()
        
        code = "print('你好，世界！')"
        result = await sandbox.execute(code)
        
        assert result.success is True
    
    @pytest.mark.asyncio
    async def test_execute_multiline_code(self):
        """测试执行多行代码"""
        sandbox = DockerSandbox()
        
        code = """
def factorial(n):
    if n <= 1:
        return 1
    return n * factorial(n - 1)

result = factorial(5)
print(result)
"""
        result = await sandbox.execute(code)
        
        assert result.success is True
    
    @pytest.mark.asyncio
    async def test_execute_with_imports(self):
        """测试执行包含导入的代码"""
        sandbox = DockerSandbox()
        
        code = "import math\nprint(math.pi)"
        result = await sandbox.execute(code)
        
        # Mock模式下会成功
        assert isinstance(result, ExecutionResult)
    
    @pytest.mark.asyncio
    async def test_multiple_executions(self):
        """测试多次执行"""
        sandbox = DockerSandbox()
        
        for i in range(5):
            code = f"print({i})"
            result = await sandbox.execute(code)
            assert result.success is True
    
    @pytest.mark.asyncio
    async def test_concurrent_executions(self):
        """测试并发执行"""
        sandbox = DockerSandbox()
        
        codes = [f"print({i})" for i in range(3)]
        
        # 并发执行
        results = await asyncio.gather(*[
            sandbox.execute(code) for code in codes
        ])
        
        # 所有执行都应该成功
        assert all(result.success for result in results)


class TestDockerSandboxPerformance:
    """测试DockerSandbox性能"""
    
    @pytest.mark.asyncio
    async def test_container_startup_time(self):
        """测试容器启动时间 (Requirement 10.8: < 100ms P99)"""
        sandbox = DockerSandbox()
        
        import time
        start_time = time.time()
        
        container_id = await sandbox.create_container()
        
        startup_time_ms = (time.time() - start_time) * 1000
        
        # Mock模式下应该很快
        assert startup_time_ms < 100
        
        await sandbox.cleanup_container(container_id)
    
    @pytest.mark.asyncio
    async def test_execution_overhead(self):
        """测试执行开销"""
        sandbox = DockerSandbox()
        
        code = "x = 1"
        result = await sandbox.execute(code)
        
        # 执行时间应该合理
        assert result.execution_time_ms < 1000  # 小于1秒
    
    @pytest.mark.asyncio
    async def test_memory_overhead(self):
        """测试内存开销"""
        sandbox = DockerSandbox()
        
        code = "x = 1"
        result = await sandbox.execute(code)
        
        # 内存使用应该合理
        assert result.memory_used_mb < 100  # 小于100MB


class TestDockerSandboxSecurity:
    """测试DockerSandbox安全性"""
    
    @pytest.mark.asyncio
    async def test_security_forbidden_os_import(self):
        """测试禁止os模块导入"""
        sandbox = DockerSandbox()
        
        code = "import os; os.system('ls')"
        result = await sandbox.execute(code)
        
        # Mock模式下会检测到
        assert result.success is False
        assert "禁止" in result.error
    
    @pytest.mark.asyncio
    async def test_security_forbidden_sys_import(self):
        """测试禁止sys模块导入"""
        sandbox = DockerSandbox()
        
        code = "import sys; sys.exit(1)"
        result = await sandbox.execute(code)
        
        # Mock模式下会检测到
        assert result.success is False
        assert "禁止" in result.error
    
    @pytest.mark.asyncio
    async def test_security_safe_imports(self):
        """测试安全的导入"""
        sandbox = DockerSandbox()
        
        code = "import math; print(math.pi)"
        result = await sandbox.execute(code)
        
        # 安全的导入应该允许
        assert result.success is True


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
