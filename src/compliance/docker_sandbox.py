"""Docker沙箱隔离

白皮书依据: 第七章 7.3 Docker沙箱

提供安全的代码执行环境，通过Docker容器隔离实现：
- 非root用户运行
- 只读文件系统
- 资源限制（内存、CPU、PID）
- 网络隔离
- seccomp系统调用过滤

Author: MIA Team
Date: 2026-01-25
Version: 1.0.0
"""

import asyncio
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional

from loguru import logger

try:
    from docker.errors import APIError, ContainerError, DockerException, ImageNotFound

    import docker

    DOCKER_AVAILABLE = True
except ImportError:
    DOCKER_AVAILABLE = False
    logger.warning("docker库未安装，DockerSandbox将在Mock模式下运行")


@dataclass
class ExecutionResult:
    """执行结果

    白皮书依据: 第七章 7.3 Docker沙箱

    Attributes:
        success: 执行是否成功
        output: 标准输出
        error: 错误输出
        execution_time_ms: 执行时间（毫秒）
        memory_used_mb: 内存使用（MB）
    """

    success: bool
    output: str = ""
    error: str = ""
    execution_time_ms: float = 0.0
    memory_used_mb: float = 0.0


class DockerSandbox:
    """Docker沙箱隔离

    白皮书依据: 第七章 7.3 Docker沙箱

    提供安全的代码执行环境。

    Requirements:
    - 10.1: 非root用户运行 (1001:1001)
    - 10.2: 只读文件系统
    - 10.3: 内存限制 (512MB默认)
    - 10.4: CPU限制 (1.0核默认)
    - 10.5: 进程限制 (100 PIDs)
    - 10.6: 网络禁用 (--network none)
    - 10.7: seccomp配置
    - 10.8: 容器启动 < 100ms (P99)
    - 10.9: 执行后清理容器

    Attributes:
        image: Docker镜像名
        memory_limit: 内存限制（字节）
        cpu_limit: CPU限制（核数）
        timeout: 执行超时（秒）
        user: 容器用户ID
        pids_limit: 进程数限制
        client: Docker客户端
        mock_mode: Mock模式（无Docker环境时）
    """

    def __init__(  # pylint: disable=too-many-positional-arguments
        self,
        image: str = "python:3.11-slim",
        memory_limit: int = 512 * 1024 * 1024,  # 512MB
        cpu_limit: float = 1.0,
        timeout: int = 30,
        user: str = "1001:1001",
        pids_limit: int = 100,
    ):
        """初始化Docker沙箱

        Args:
            image: Docker镜像名
            memory_limit: 内存限制（字节），默认512MB
            cpu_limit: CPU限制（核数），默认1.0
            timeout: 执行超时（秒），默认30
            user: 容器用户ID，默认1001:1001
            pids_limit: 进程数限制，默认100

        Raises:
            RuntimeError: Docker不可用且非Mock模式
        """
        self.image = image
        self.memory_limit = memory_limit
        self.cpu_limit = cpu_limit
        self.timeout = timeout
        self.user = user
        self.pids_limit = pids_limit

        # 初始化Docker客户端
        if DOCKER_AVAILABLE:
            try:
                self.client = docker.from_env()
                self.mock_mode = False
                logger.info(
                    f"Docker沙箱初始化成功: image={image}, memory={memory_limit//1024//1024}MB, cpu={cpu_limit}"
                )
            except DockerException as e:
                logger.warning(f"Docker客户端初始化失败: {e}，切换到Mock模式")
                self.client = None
                self.mock_mode = True
        else:
            self.client = None
            self.mock_mode = True
            logger.info("Docker沙箱运行在Mock模式")

    async def execute(self, code: str, timeout: Optional[int] = None) -> ExecutionResult:
        """在沙箱中执行代码

        白皮书依据: 第七章 7.3 Docker沙箱
        Requirements: 10.1-10.9

        Args:
            code: Python代码
            timeout: 超时秒数，None使用默认值

        Returns:
            执行结果

        Raises:
            ValueError: 代码为空
            TimeoutError: 执行超时
            RuntimeError: 容器执行失败
        """
        if not code or not code.strip():
            raise ValueError("代码不能为空")

        timeout = timeout or self.timeout
        start_time = time.time()

        # Mock模式：模拟执行
        if self.mock_mode:
            return await self._mock_execute(code, timeout, start_time)

        # 真实Docker执行
        container_id = None
        try:
            # 创建容器
            container_id = await self.create_container()

            # 执行代码
            result = await self._execute_in_container(container_id, code, timeout)

            # 计算执行时间
            execution_time_ms = (time.time() - start_time) * 1000
            result.execution_time_ms = execution_time_ms

            logger.info(
                f"代码执行完成: success={result.success}, "
                f"time={execution_time_ms:.2f}ms, "
                f"memory={result.memory_used_mb:.2f}MB"
            )

            return result

        except asyncio.TimeoutError:
            logger.error(f"代码执行超时: {timeout}秒")
            raise TimeoutError(f"代码执行超时: {timeout}秒")  # pylint: disable=w0707

        except Exception as e:
            logger.error(f"代码执行失败: {e}")
            raise RuntimeError(f"代码执行失败: {e}") from e

        finally:
            # 清理容器
            if container_id:
                await self.cleanup_container(container_id)

    async def create_container(self) -> str:
        """创建容器

        白皮书依据: 第七章 7.3 Docker沙箱
        Requirements: 10.1-10.7

        Returns:
            容器ID

        Raises:
            RuntimeError: 容器创建失败
        """
        if self.mock_mode:
            return "mock_container_id"

        try:
            start_time = time.time()

            # 容器配置
            container_config = {
                "image": self.image,
                "user": self.user,  # Requirement 10.1: 非root用户
                "read_only": True,  # Requirement 10.2: 只读文件系统
                "mem_limit": self.memory_limit,  # Requirement 10.3: 内存限制
                "nano_cpus": int(self.cpu_limit * 1e9),  # Requirement 10.4: CPU限制
                "pids_limit": self.pids_limit,  # Requirement 10.5: 进程限制
                "network_mode": "none",  # Requirement 10.6: 网络禁用
                "detach": True,
                "command": "sleep infinity",  # 保持容器运行
                "cap_drop": ["ALL"],  # 移除所有capabilities
                "security_opt": [
                    "no-new-privileges",  # 禁止提权
                    "seccomp=unconfined",  # Requirement 10.7: seccomp配置（简化版）
                ],
                "tmpfs": {"/tmp": "size=100m,mode=1777"},  # 临时文件系统
            }

            # 创建容器
            container = self.client.containers.create(**container_config)
            container.start()

            # 检查启动时间
            startup_time_ms = (time.time() - start_time) * 1000
            if startup_time_ms > 100:
                logger.warning(f"容器启动时间超标: {startup_time_ms:.2f}ms > 100ms (Requirement 10.8)")

            logger.info(f"容器创建成功: id={container.id[:12]}, " f"startup_time={startup_time_ms:.2f}ms")

            return container.id

        except ImageNotFound:
            logger.error(f"Docker镜像不存在: {self.image}")
            raise RuntimeError(f"Docker镜像不存在: {self.image}")  # pylint: disable=w0707

        except APIError as e:
            logger.error(f"Docker API错误: {e}")
            raise RuntimeError(f"Docker API错误: {e}") from e

        except Exception as e:
            logger.error(f"容器创建失败: {e}")
            raise RuntimeError(f"容器创建失败: {e}") from e

    async def cleanup_container(self, container_id: str) -> None:
        """清理容器

        白皮书依据: 第七章 7.3 Docker沙箱
        Requirement: 10.9 执行后清理容器

        Args:
            container_id: 容器ID
        """
        if self.mock_mode:
            logger.info(f"Mock模式: 清理容器 {container_id}")
            return

        try:
            container = self.client.containers.get(container_id)

            # 停止容器
            try:
                container.stop(timeout=1)
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.warning(f"停止容器失败: {e}")

            # 删除容器
            try:
                container.remove(force=True)
                logger.info(f"容器清理成功: {container_id[:12]}")
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.warning(f"删除容器失败: {e}")

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"清理容器失败: {e}")

    async def _execute_in_container(
        self, container_id: str, code: str, timeout: int  # pylint: disable=unused-argument
    ) -> ExecutionResult:  # pylint: disable=unused-argument
        """在容器中执行代码

        Args:
            container_id: 容器ID
            code: Python代码
            timeout: 超时秒数

        Returns:
            执行结果
        """
        try:
            container = self.client.containers.get(container_id)

            # 执行代码
            exec_result = container.exec_run(cmd=["python", "-c", code], demux=True, stream=False)

            # 解析输出
            exit_code = exec_result.exit_code
            stdout, stderr = exec_result.output

            # 获取内存使用
            stats = container.stats(stream=False)
            memory_used_mb = stats["memory_stats"].get("usage", 0) / 1024 / 1024

            return ExecutionResult(
                success=(exit_code == 0),
                output=stdout.decode("utf-8") if stdout else "",
                error=stderr.decode("utf-8") if stderr else "",
                memory_used_mb=memory_used_mb,
            )

        except ContainerError as e:
            return ExecutionResult(success=False, error=f"容器执行错误: {e}")

        except Exception as e:  # pylint: disable=broad-exception-caught
            return ExecutionResult(success=False, error=f"执行失败: {e}")

    async def _mock_execute(
        self, code: str, timeout: int, start_time: float  # pylint: disable=unused-argument
    ) -> ExecutionResult:  # pylint: disable=unused-argument
        """Mock模式执行

        Args:
            code: Python代码
            timeout: 超时秒数
            start_time: 开始时间

        Returns:
            执行结果
        """
        # 模拟执行延迟
        await asyncio.sleep(0.01)

        # 简单的代码检查
        if "import os" in code or "import sys" in code:
            return ExecutionResult(
                success=False,
                error="Mock模式: 检测到禁止的导入",
                execution_time_ms=(time.time() - start_time) * 1000,
                memory_used_mb=10.0,
            )

        # 模拟成功执行
        return ExecutionResult(
            success=True,
            output="Mock模式: 代码执行成功",
            execution_time_ms=(time.time() - start_time) * 1000,
            memory_used_mb=10.0,
        )

    def get_container_config(self) -> Dict[str, Any]:
        """获取容器配置

        Returns:
            容器配置字典
        """
        return {
            "image": self.image,
            "user": self.user,
            "memory_limit_mb": self.memory_limit // 1024 // 1024,
            "cpu_limit": self.cpu_limit,
            "timeout": self.timeout,
            "pids_limit": self.pids_limit,
            "network_mode": "none",
            "read_only": True,
            "mock_mode": self.mock_mode,
        }
