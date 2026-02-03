"""健康检查系统

白皮书依据: 第十章 10.1 健康检查系统
"""

import subprocess
import time
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Dict, Optional

from loguru import logger

try:
    import redis
except ImportError:
    redis = None


class ComponentStatus(str, Enum):
    """组件状态枚举"""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class OverallStatus(str, Enum):
    """整体系统状态枚举"""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    CRITICAL = "critical"


@dataclass
class ComponentHealth:
    """单个组件健康状态

    白皮书依据: 第十章 10.1 健康检查系统

    Attributes:
        status: 组件状态 (healthy/degraded/unhealthy)
        message: 状态描述信息
        metrics: 组件相关指标
    """

    status: ComponentStatus
    message: str
    metrics: Dict[str, float]


@dataclass
class HealthCheckResult:
    """系统健康检查结果

    白皮书依据: 第十章 10.1 健康检查系统

    Attributes:
        overall_status: 整体状态
        components: 各组件健康状态字典
        timestamp: 检查时间戳
    """

    overall_status: OverallStatus
    components: Dict[str, ComponentHealth]
    timestamp: datetime


class HealthChecker:
    """系统健康检查器

    白皮书依据: 第十章 10.1 健康检查系统

    监控Redis、Dashboard、磁盘空间、内存、CPU和GPU，每30秒执行一次健康检查。
    当Redis连接失败时，自动尝试恢复（指数退避：1s, 2s, 4s）。

    Attributes:
        redis_host: Redis主机地址
        redis_port: Redis端口
        redis_timeout: Redis连接超时时间（秒）
        check_interval: 健康检查间隔（秒）
    """

    def __init__(
        self, redis_host: str = "localhost", redis_port: int = 6379, redis_timeout: int = 5, check_interval: int = 30
    ):
        """初始化健康检查器

        白皮书依据: 第十章 10.1 健康检查系统

        Args:
            redis_host: Redis主机地址，默认localhost
            redis_port: Redis端口，默认6379
            redis_timeout: Redis连接超时时间（秒），默认5秒
            check_interval: 健康检查间隔（秒），默认30秒

        Raises:
            ValueError: 当参数不在有效范围时
        """
        if redis_timeout <= 0:
            raise ValueError(f"Redis超时时间必须 > 0，当前: {redis_timeout}")

        if check_interval <= 0:
            raise ValueError(f"检查间隔必须 > 0，当前: {check_interval}")

        self.redis_host = redis_host
        self.redis_port = redis_port
        self.redis_timeout = redis_timeout
        self.check_interval = check_interval

        self._redis_client: Optional[redis.Redis] = None

        logger.info(
            f"初始化HealthChecker: "
            f"redis={redis_host}:{redis_port}, "
            f"timeout={redis_timeout}s, "
            f"interval={check_interval}s"
        )

    def run_health_check(self) -> HealthCheckResult:
        """运行综合健康检查

        白皮书依据: 第十章 10.1 健康检查系统

        检查所有组件：Redis、Dashboard、磁盘、内存、CPU、GPU

        Returns:
            HealthCheckResult: 包含所有组件状态的健康检查结果
        """
        logger.info("开始健康检查")

        components: Dict[str, ComponentHealth] = {}

        # 检查Redis
        components["redis"] = self.check_redis()

        # 检查Dashboard（端口8501和8502）
        components["dashboard_8501"] = self._check_port(8501, "Dashboard 8501")
        components["dashboard_8502"] = self._check_port(8502, "Dashboard 8502")

        # 检查磁盘空间
        components["disk"] = self._check_disk_space()

        # 检查内存
        components["memory"] = self._check_memory()

        # 检查CPU
        components["cpu"] = self._check_cpu()

        # 检查GPU
        components["gpu"] = self.check_gpu()

        # 确定整体状态
        overall_status = self._determine_overall_status(components)

        result = HealthCheckResult(overall_status=overall_status, components=components, timestamp=datetime.now())

        logger.info(f"健康检查完成: 整体状态={overall_status.value}")

        return result

    def check_redis(self) -> ComponentHealth:
        """检查Redis连接（5秒超时）

        白皮书依据: 第十章 10.1 健康检查系统

        Returns:
            ComponentHealth: Redis组件健康状态
        """
        if redis is None:
            return ComponentHealth(status=ComponentStatus.UNHEALTHY, message="Redis库未安装", metrics={})

        try:
            # 创建或重用Redis客户端
            if self._redis_client is None:
                self._redis_client = redis.Redis(
                    host=self.redis_host,
                    port=self.redis_port,
                    socket_timeout=self.redis_timeout,
                    socket_connect_timeout=self.redis_timeout,
                    decode_responses=True,
                )

            # 执行PING命令测试连接
            start_time = time.perf_counter()
            response = self._redis_client.ping()
            latency = time.perf_counter() - start_time

            if response:  # pylint: disable=no-else-return
                # 获取Redis信息
                info = self._redis_client.info()
                used_memory_mb = info.get("used_memory", 0) / (1024 * 1024)
                connected_clients = info.get("connected_clients", 0)

                return ComponentHealth(
                    status=ComponentStatus.HEALTHY,
                    message=f"Redis连接正常，延迟{latency*1000:.2f}ms",
                    metrics={
                        "latency_ms": latency * 1000,
                        "used_memory_mb": used_memory_mb,
                        "connected_clients": float(connected_clients),
                    },
                )
            else:
                return ComponentHealth(status=ComponentStatus.UNHEALTHY, message="Redis PING失败", metrics={})

        except redis.ConnectionError as e:
            logger.warning(f"Redis连接失败: {e}")
            self._redis_client = None  # 重置客户端
            return ComponentHealth(status=ComponentStatus.UNHEALTHY, message=f"Redis连接失败: {str(e)}", metrics={})

        except redis.TimeoutError as e:
            logger.warning(f"Redis超时: {e}")
            self._redis_client = None  # 重置客户端
            return ComponentHealth(status=ComponentStatus.UNHEALTHY, message=f"Redis超时: {str(e)}", metrics={})

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"Redis检查异常: {e}", exc_info=True)
            self._redis_client = None  # 重置客户端
            return ComponentHealth(status=ComponentStatus.UNHEALTHY, message=f"Redis检查异常: {str(e)}", metrics={})

    def check_gpu(self) -> ComponentHealth:
        """检查GPU状态（使用rocm-smi）

        白皮书依据: 第十章 10.1 健康检查系统

        Returns:
            ComponentHealth: GPU组件健康状态
        """
        try:
            # 尝试执行rocm-smi命令
            result = subprocess.run(  # pylint: disable=w1510
                ["rocm-smi", "--showmeminfo", "vram"], capture_output=True, text=True, timeout=5
            )  # pylint: disable=w1510

            if result.returncode == 0:
                # 解析输出获取GPU信息
                output = result.stdout

                # 简化版本：检查是否有输出
                if output and len(output) > 0:  # pylint: disable=no-else-return
                    return ComponentHealth(
                        status=ComponentStatus.HEALTHY, message="GPU状态正常", metrics={"available": 1.0}
                    )
                else:
                    return ComponentHealth(
                        status=ComponentStatus.DEGRADED, message="GPU信息为空", metrics={"available": 0.5}
                    )
            else:
                return ComponentHealth(
                    status=ComponentStatus.UNHEALTHY,
                    message=f"rocm-smi执行失败: {result.stderr}",
                    metrics={"available": 0.0},
                )

        except FileNotFoundError:
            # rocm-smi未安装
            return ComponentHealth(
                status=ComponentStatus.DEGRADED, message="rocm-smi未安装，无法检查GPU", metrics={"available": 0.0}
            )

        except subprocess.TimeoutExpired:
            logger.warning("GPU检查超时")
            return ComponentHealth(status=ComponentStatus.UNHEALTHY, message="GPU检查超时", metrics={"available": 0.0})

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"GPU检查异常: {e}", exc_info=True)
            return ComponentHealth(
                status=ComponentStatus.UNHEALTHY, message=f"GPU检查异常: {str(e)}", metrics={"available": 0.0}
            )

    def attempt_redis_recovery(self) -> bool:
        """尝试Redis恢复（指数退避：1s, 2s, 4s）

        白皮书依据: 第十章 10.1 健康检查系统

        使用指数退避策略尝试重新连接Redis：
        - 第1次尝试：等待1秒
        - 第2次尝试：等待2秒
        - 第3次尝试：等待4秒

        Returns:
            bool: 恢复成功返回True，否则返回False
        """
        logger.info("开始Redis恢复尝试（指数退避：1s, 2s, 4s）")

        backoff_delays = [1, 2, 4]  # 指数退避延迟序列

        for attempt, delay in enumerate(backoff_delays, start=1):
            logger.info(f"Redis恢复尝试 {attempt}/3，等待{delay}秒...")
            time.sleep(delay)

            # 尝试连接
            health = self.check_redis()

            if health.status == ComponentStatus.HEALTHY:  # pylint: disable=no-else-return
                logger.info(f"Redis恢复成功（第{attempt}次尝试）")
                return True
            else:
                logger.warning(f"Redis恢复失败（第{attempt}次尝试）: {health.message}")

        logger.error("Redis恢复失败，已达最大重试次数")
        return False

    def _check_port(self, port: int, name: str) -> ComponentHealth:
        """检查端口是否可访问

        Args:
            port: 端口号
            name: 组件名称

        Returns:
            ComponentHealth: 端口健康状态
        """
        try:
            import socket  # pylint: disable=import-outside-toplevel

            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            result = sock.connect_ex(("localhost", port))
            sock.close()

            if result == 0:  # pylint: disable=no-else-return
                return ComponentHealth(
                    status=ComponentStatus.HEALTHY,
                    message=f"{name}端口{port}可访问",
                    metrics={"port": float(port), "accessible": 1.0},
                )
            else:
                return ComponentHealth(
                    status=ComponentStatus.UNHEALTHY,
                    message=f"{name}端口{port}不可访问",
                    metrics={"port": float(port), "accessible": 0.0},
                )

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"端口检查异常: {e}", exc_info=True)
            return ComponentHealth(
                status=ComponentStatus.UNHEALTHY,
                message=f"端口检查异常: {str(e)}",
                metrics={"port": float(port), "accessible": 0.0},
            )

    def _check_disk_space(self) -> ComponentHealth:
        """检查磁盘空间

        Returns:
            ComponentHealth: 磁盘健康状态
        """
        try:
            import shutil  # pylint: disable=import-outside-toplevel

            # 检查当前目录所在磁盘
            total, used, free = shutil.disk_usage(".")

            free_pct = (free / total) * 100
            used_pct = (used / total) * 100

            if free_pct > 20:
                status = ComponentStatus.HEALTHY
                message = f"磁盘空间充足: {free_pct:.1f}%可用"
            elif free_pct > 10:
                status = ComponentStatus.DEGRADED
                message = f"磁盘空间偏低: {free_pct:.1f}%可用"
            else:
                status = ComponentStatus.UNHEALTHY
                message = f"磁盘空间不足: {free_pct:.1f}%可用"

            return ComponentHealth(
                status=status,
                message=message,
                metrics={
                    "total_gb": total / (1024**3),
                    "used_gb": used / (1024**3),
                    "free_gb": free / (1024**3),
                    "used_pct": used_pct,
                    "free_pct": free_pct,
                },
            )

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"磁盘检查异常: {e}", exc_info=True)
            return ComponentHealth(status=ComponentStatus.UNHEALTHY, message=f"磁盘检查异常: {str(e)}", metrics={})

    def _check_memory(self) -> ComponentHealth:
        """检查内存使用

        Returns:
            ComponentHealth: 内存健康状态
        """
        try:
            import psutil  # pylint: disable=import-outside-toplevel

            memory = psutil.virtual_memory()

            available_gb = memory.available / (1024**3)
            used_pct = memory.percent

            if used_pct < 80:
                status = ComponentStatus.HEALTHY
                message = f"内存使用正常: {used_pct:.1f}%"
            elif used_pct < 90:
                status = ComponentStatus.DEGRADED
                message = f"内存使用偏高: {used_pct:.1f}%"
            else:
                status = ComponentStatus.UNHEALTHY
                message = f"内存使用过高: {used_pct:.1f}%"

            return ComponentHealth(
                status=status,
                message=message,
                metrics={"total_gb": memory.total / (1024**3), "available_gb": available_gb, "used_pct": used_pct},
            )

        except ImportError:
            return ComponentHealth(status=ComponentStatus.DEGRADED, message="psutil未安装，无法检查内存", metrics={})

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"内存检查异常: {e}", exc_info=True)
            return ComponentHealth(status=ComponentStatus.UNHEALTHY, message=f"内存检查异常: {str(e)}", metrics={})

    def _check_cpu(self) -> ComponentHealth:
        """检查CPU使用

        Returns:
            ComponentHealth: CPU健康状态
        """
        try:
            import psutil  # pylint: disable=import-outside-toplevel

            cpu_percent = psutil.cpu_percent(interval=1)

            if cpu_percent < 80:
                status = ComponentStatus.HEALTHY
                message = f"CPU使用正常: {cpu_percent:.1f}%"
            elif cpu_percent < 95:
                status = ComponentStatus.DEGRADED
                message = f"CPU使用偏高: {cpu_percent:.1f}%"
            else:
                status = ComponentStatus.UNHEALTHY
                message = f"CPU使用过高: {cpu_percent:.1f}%"

            return ComponentHealth(status=status, message=message, metrics={"cpu_percent": cpu_percent})

        except ImportError:
            return ComponentHealth(status=ComponentStatus.DEGRADED, message="psutil未安装，无法检查CPU", metrics={})

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"CPU检查异常: {e}", exc_info=True)
            return ComponentHealth(status=ComponentStatus.UNHEALTHY, message=f"CPU检查异常: {str(e)}", metrics={})

    def _determine_overall_status(self, components: Dict[str, ComponentHealth]) -> OverallStatus:
        """确定整体系统状态

        规则：
        - 如果任何组件UNHEALTHY，整体为CRITICAL
        - 如果任何组件DEGRADED，整体为DEGRADED
        - 否则整体为HEALTHY

        Args:
            components: 各组件健康状态字典

        Returns:
            OverallStatus: 整体系统状态
        """
        has_unhealthy = any(c.status == ComponentStatus.UNHEALTHY for c in components.values())

        has_degraded = any(c.status == ComponentStatus.DEGRADED for c in components.values())

        if has_unhealthy:  # pylint: disable=no-else-return
            return OverallStatus.CRITICAL
        elif has_degraded:
            return OverallStatus.DEGRADED
        else:
            return OverallStatus.HEALTHY
