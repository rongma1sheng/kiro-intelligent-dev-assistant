"""健康检查HTTP API

白皮书依据: 第十三章 13.2 健康检查接口

提供HTTP端点用于系统健康检查:
- /health: 整体系统健康状态
- /health/redis: Redis连接状态
- /health/gpu: GPU状态
- /health/soldier: Soldier状态
- /metrics/summary: 指标摘要
"""

import subprocess
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, Optional

from loguru import logger

try:
    import psutil

    PSUTIL_AVAILABLE = True
except ImportError:
    psutil = None
    PSUTIL_AVAILABLE = False

try:
    from fastapi import FastAPI
    from fastapi.responses import JSONResponse

    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False
    FastAPI = None


class HealthStatus(Enum):
    """健康状态枚举"""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


@dataclass
class ComponentHealth:
    """组件健康状态

    Attributes:
        name: 组件名称
        healthy: 是否健康
        status: 状态描述
        latency_ms: 检查延迟（毫秒）
        details: 详细信息
        last_check: 最后检查时间
    """

    name: str
    healthy: bool
    status: str = ""
    latency_ms: float = 0.0
    details: Dict[str, Any] = field(default_factory=dict)
    last_check: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "name": self.name,
            "healthy": self.healthy,
            "status": self.status,
            "latency_ms": self.latency_ms,
            "details": self.details,
            "last_check": self.last_check.isoformat(),
        }


@dataclass
class SystemHealthReport:
    """系统健康报告

    Attributes:
        healthy: 整体是否健康
        status: 整体状态
        components: 各组件健康状态
        timestamp: 报告时间戳
    """

    healthy: bool
    status: HealthStatus
    components: Dict[str, ComponentHealth] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "healthy": self.healthy,
            "status": self.status.value,
            "components": {k: v.to_dict() for k, v in self.components.items()},
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class MetricsSummary:
    """指标摘要

    Attributes:
        cpu_percent: CPU使用率
        memory_percent: 内存使用率
        disk_percent: 磁盘使用率
        soldier_mode: Soldier模式
        portfolio_value: 组合价值
        timestamp: 时间戳
    """

    cpu_percent: float
    memory_percent: float
    disk_percent: float
    soldier_mode: str
    portfolio_value: float
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "cpu_percent": self.cpu_percent,
            "memory_percent": self.memory_percent,
            "disk_percent": self.disk_percent,
            "soldier_mode": self.soldier_mode,
            "portfolio_value": self.portfolio_value,
            "timestamp": self.timestamp.isoformat(),
        }


class HealthChecker:
    """健康检查器

    白皮书依据: 第十三章 13.2.1 系统健康检查

    Attributes:
        redis_client: Redis客户端
        memory_threshold: 内存使用阈值（百分比）
        disk_threshold: 磁盘使用阈值（百分比）
        custom_checks: 自定义检查函数
    """

    def __init__(
        self, redis_client: Optional[Any] = None, memory_threshold: float = 90.0, disk_threshold: float = 90.0
    ):
        """初始化健康检查器

        Args:
            redis_client: Redis客户端
            memory_threshold: 内存使用阈值（百分比），默认90%
            disk_threshold: 磁盘使用阈值（百分比），默认90%

        Raises:
            ValueError: 当阈值不在有效范围时
        """
        if not 0 <= memory_threshold <= 100:
            raise ValueError(f"内存阈值必须在0-100之间，当前: {memory_threshold}")

        if not 0 <= disk_threshold <= 100:
            raise ValueError(f"磁盘阈值必须在0-100之间，当前: {disk_threshold}")

        self.redis_client: Optional[Any] = redis_client
        self.memory_threshold: float = memory_threshold
        self.disk_threshold: float = disk_threshold
        self.custom_checks: Dict[str, Callable[[], ComponentHealth]] = {}

        logger.info(f"初始化HealthChecker: memory_threshold={memory_threshold}%, disk_threshold={disk_threshold}%")

    def register_check(self, name: str, check_func: Callable[[], ComponentHealth]) -> None:
        """注册自定义检查函数"""
        if not name:
            raise ValueError("检查名称不能为空")
        self.custom_checks[name] = check_func
        logger.debug(f"注册自定义检查: {name}")

    def check_redis(self) -> ComponentHealth:
        """检查Redis连接"""
        start_time = time.perf_counter()

        try:
            if self.redis_client is None:
                return ComponentHealth(name="redis", healthy=False, status="Redis客户端未配置", latency_ms=0.0)

            self.redis_client.ping()
            latency_ms = (time.perf_counter() - start_time) * 1000

            return ComponentHealth(
                name="redis", healthy=True, status="连接正常", latency_ms=latency_ms, details={"ping": "PONG"}
            )

        except Exception as e:  # pylint: disable=broad-exception-caught
            latency_ms = (time.perf_counter() - start_time) * 1000
            logger.error(f"Redis健康检查失败: {e}")
            return ComponentHealth(
                name="redis",
                healthy=False,
                status=f"连接失败: {str(e)}",
                latency_ms=latency_ms,
                details={"error": str(e)},
            )

    def check_gpu(self) -> ComponentHealth:
        """检查GPU状态"""
        start_time = time.perf_counter()

        try:
            result = subprocess.run(["rocm-smi"], capture_output=True, timeout=5, text=True)  # pylint: disable=w1510
            latency_ms = (time.perf_counter() - start_time) * 1000

            if result.returncode == 0:  # pylint: disable=no-else-return
                return ComponentHealth(
                    name="gpu",
                    healthy=True,
                    status="GPU正常",
                    latency_ms=latency_ms,
                    details={"driver": "rocm", "output": result.stdout[:200]},
                )
            else:
                return ComponentHealth(
                    name="gpu",
                    healthy=False,
                    status=f"rocm-smi返回错误: {result.returncode}",
                    latency_ms=latency_ms,
                    details={"stderr": result.stderr[:200]},
                )

        except FileNotFoundError:
            latency_ms = (time.perf_counter() - start_time) * 1000
            try:
                result = subprocess.run(  # pylint: disable=w1510
                    ["nvidia-smi"], capture_output=True, timeout=5, text=True
                )  # pylint: disable=w1510
                latency_ms = (time.perf_counter() - start_time) * 1000

                if result.returncode == 0:  # pylint: disable=no-else-return
                    return ComponentHealth(
                        name="gpu",
                        healthy=True,
                        status="GPU正常(NVIDIA)",
                        latency_ms=latency_ms,
                        details={"driver": "nvidia"},
                    )
                else:
                    return ComponentHealth(
                        name="gpu", healthy=False, status="nvidia-smi返回错误", latency_ms=latency_ms
                    )

            except FileNotFoundError:
                return ComponentHealth(
                    name="gpu",
                    healthy=False,
                    status="GPU驱动未安装",
                    latency_ms=latency_ms,
                    details={"error": "rocm-smi和nvidia-smi均未找到"},
                )

        except subprocess.TimeoutExpired:
            latency_ms = (time.perf_counter() - start_time) * 1000
            return ComponentHealth(
                name="gpu", healthy=False, status="GPU检查超时", latency_ms=latency_ms, details={"error": "timeout"}
            )

        except Exception as e:  # pylint: disable=broad-exception-caught
            latency_ms = (time.perf_counter() - start_time) * 1000
            return ComponentHealth(
                name="gpu",
                healthy=False,
                status=f"检查失败: {str(e)}",
                latency_ms=latency_ms,
                details={"error": str(e)},
            )

    def check_soldier(self) -> ComponentHealth:
        """检查Soldier状态"""
        start_time = time.perf_counter()

        try:
            if self.redis_client is None:
                return ComponentHealth(name="soldier", healthy=False, status="Redis客户端未配置", latency_ms=0.0)

            status = self.redis_client.hget("mia:soldier", "status")
            mode = self.redis_client.get("mia:soldier:mode")
            latency_ms = (time.perf_counter() - start_time) * 1000

            if isinstance(status, bytes):
                status = status.decode("utf-8")
            if isinstance(mode, bytes):
                mode = mode.decode("utf-8")

            healthy_statuses = ["NORMAL", "DEGRADED"]
            is_healthy = status in healthy_statuses if status else False

            return ComponentHealth(
                name="soldier",
                healthy=is_healthy,
                status=status or "未知",
                latency_ms=latency_ms,
                details={"mode": mode or "unknown", "raw_status": status},
            )

        except Exception as e:  # pylint: disable=broad-exception-caught
            latency_ms = (time.perf_counter() - start_time) * 1000
            return ComponentHealth(
                name="soldier",
                healthy=False,
                status=f"检查失败: {str(e)}",
                latency_ms=latency_ms,
                details={"error": str(e)},
            )

    def check_memory(self) -> ComponentHealth:
        """检查内存使用"""
        start_time = time.perf_counter()

        try:
            if not PSUTIL_AVAILABLE:
                return ComponentHealth(name="memory", healthy=False, status="psutil未安装", latency_ms=0.0)

            mem = psutil.virtual_memory()
            latency_ms = (time.perf_counter() - start_time) * 1000
            is_healthy = mem.percent < self.memory_threshold

            return ComponentHealth(
                name="memory",
                healthy=is_healthy,
                status=f"使用率: {mem.percent:.1f}%",
                latency_ms=latency_ms,
                details={
                    "percent": mem.percent,
                    "total_gb": mem.total / (1024**3),
                    "available_gb": mem.available / (1024**3),
                    "used_gb": mem.used / (1024**3),
                    "threshold": self.memory_threshold,
                },
            )

        except Exception as e:  # pylint: disable=broad-exception-caught
            latency_ms = (time.perf_counter() - start_time) * 1000
            return ComponentHealth(
                name="memory",
                healthy=False,
                status=f"检查失败: {str(e)}",
                latency_ms=latency_ms,
                details={"error": str(e)},
            )

    def check_disk(self, path: str = "D:/") -> ComponentHealth:
        """检查磁盘空间"""
        start_time = time.perf_counter()

        try:
            if not PSUTIL_AVAILABLE:
                return ComponentHealth(name="disk", healthy=False, status="psutil未安装", latency_ms=0.0)

            try:
                disk = psutil.disk_usage(path)
            except (FileNotFoundError, OSError):
                path = "C:/"
                disk = psutil.disk_usage(path)

            latency_ms = (time.perf_counter() - start_time) * 1000
            is_healthy = disk.percent < self.disk_threshold

            return ComponentHealth(
                name="disk",
                healthy=is_healthy,
                status=f"使用率: {disk.percent:.1f}%",
                latency_ms=latency_ms,
                details={
                    "path": path,
                    "percent": disk.percent,
                    "total_gb": disk.total / (1024**3),
                    "free_gb": disk.free / (1024**3),
                    "used_gb": disk.used / (1024**3),
                    "threshold": self.disk_threshold,
                },
            )

        except Exception as e:  # pylint: disable=broad-exception-caught
            latency_ms = (time.perf_counter() - start_time) * 1000
            return ComponentHealth(
                name="disk",
                healthy=False,
                status=f"检查失败: {str(e)}",
                latency_ms=latency_ms,
                details={"error": str(e)},
            )

    def check_processes(self) -> ComponentHealth:
        """检查核心进程"""
        start_time = time.perf_counter()

        try:
            if not PSUTIL_AVAILABLE:
                return ComponentHealth(name="processes", healthy=False, status="psutil未安装", latency_ms=0.0)

            required_processes = ["python.exe", "redis-server.exe"]
            running_processes = set()

            for proc in psutil.process_iter(["name"]):
                try:
                    name = proc.info["name"]
                    if name:
                        running_processes.add(name.lower())
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            latency_ms = (time.perf_counter() - start_time) * 1000

            missing = []
            found = []
            for proc_name in required_processes:
                if proc_name.lower() in running_processes:
                    found.append(proc_name)
                else:
                    missing.append(proc_name)

            is_healthy = len(missing) == 0

            return ComponentHealth(
                name="processes",
                healthy=is_healthy,
                status="所有核心进程运行中" if is_healthy else f"缺失进程: {missing}",
                latency_ms=latency_ms,
                details={"required": required_processes, "found": found, "missing": missing},
            )

        except Exception as e:  # pylint: disable=broad-exception-caught
            latency_ms = (time.perf_counter() - start_time) * 1000
            return ComponentHealth(
                name="processes",
                healthy=False,
                status=f"检查失败: {str(e)}",
                latency_ms=latency_ms,
                details={"error": str(e)},
            )

    def run_all_checks(self) -> SystemHealthReport:
        """运行所有健康检查"""
        logger.debug("开始执行系统健康检查")

        components: Dict[str, ComponentHealth] = {}

        components["redis"] = self.check_redis()
        components["gpu"] = self.check_gpu()
        components["soldier"] = self.check_soldier()
        components["memory"] = self.check_memory()
        components["disk"] = self.check_disk()
        components["processes"] = self.check_processes()

        for name, check_func in self.custom_checks.items():
            try:
                components[name] = check_func()
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.error(f"自定义检查 {name} 失败: {e}")
                components[name] = ComponentHealth(name=name, healthy=False, status=f"检查失败: {str(e)}")

        all_healthy = all(c.healthy for c in components.values())
        any_healthy = any(c.healthy for c in components.values())

        if all_healthy:
            status = HealthStatus.HEALTHY
        elif any_healthy:
            status = HealthStatus.DEGRADED
        else:
            status = HealthStatus.UNHEALTHY

        report = SystemHealthReport(healthy=all_healthy, status=status, components=components, timestamp=datetime.now())

        logger.info(
            f"健康检查完成: status={status.value}, healthy_components={sum(1 for c in components.values() if c.healthy)}/{len(components)}"  # pylint: disable=line-too-long
        )

        return report

    def get_metrics_summary(self) -> MetricsSummary:
        """获取指标摘要"""
        cpu_percent = 0.0
        memory_percent = 0.0
        disk_percent = 0.0
        soldier_mode = "unknown"
        portfolio_value = 0.0

        try:
            if PSUTIL_AVAILABLE:
                cpu_percent = psutil.cpu_percent(interval=0.1)
                memory_percent = psutil.virtual_memory().percent
                try:
                    disk_percent = psutil.disk_usage("D:/").percent
                except (FileNotFoundError, OSError):
                    disk_percent = psutil.disk_usage("C:/").percent
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"获取系统指标失败: {e}")

        try:
            if self.redis_client:
                mode = self.redis_client.get("mia:soldier:mode")
                if isinstance(mode, bytes):
                    soldier_mode = mode.decode("utf-8")
                elif mode:
                    soldier_mode = str(mode)

                value = self.redis_client.get("portfolio:total_value")
                if value:
                    if isinstance(value, bytes):
                        value = value.decode("utf-8")
                    portfolio_value = float(value)
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"获取Redis指标失败: {e}")

        return MetricsSummary(
            cpu_percent=cpu_percent,
            memory_percent=memory_percent,
            disk_percent=disk_percent,
            soldier_mode=soldier_mode,
            portfolio_value=portfolio_value,
        )


class HealthAPI:
    """健康检查HTTP API

    白皮书依据: 第十三章 13.2.2 HTTP健康检查端点

    Attributes:
        app: FastAPI应用实例
        health_checker: 健康检查器
    """

    def __init__(
        self, redis_client: Optional[Any] = None, memory_threshold: float = 90.0, disk_threshold: float = 90.0
    ):
        """初始化健康检查API"""
        if not FASTAPI_AVAILABLE:
            raise ImportError("FastAPI未安装，请运行: pip install fastapi uvicorn")

        self.health_checker = HealthChecker(
            redis_client=redis_client, memory_threshold=memory_threshold, disk_threshold=disk_threshold
        )
        self.app = FastAPI(title="MIA Health API", description="MIA系统健康检查API", version="1.0.0")
        self._register_routes()
        logger.info("HealthAPI初始化完成")

    def _register_routes(self) -> None:
        """注册API路由"""

        @self.app.get("/health")
        async def health() -> JSONResponse:
            """整体系统健康检查"""
            report = self.health_checker.run_all_checks()
            status_code = 200 if report.healthy else 503
            return JSONResponse(content=report.to_dict(), status_code=status_code)

        @self.app.get("/health/redis")
        async def health_redis() -> Dict[str, Any]:
            """Redis健康检查"""
            result = self.health_checker.check_redis()
            return result.to_dict()

        @self.app.get("/health/gpu")
        async def health_gpu() -> Dict[str, Any]:
            """GPU健康检查"""
            result = self.health_checker.check_gpu()
            return result.to_dict()

        @self.app.get("/health/soldier")
        async def health_soldier() -> Dict[str, Any]:
            """Soldier健康检查"""
            result = self.health_checker.check_soldier()
            return result.to_dict()

        @self.app.get("/health/memory")
        async def health_memory() -> Dict[str, Any]:
            """内存健康检查"""
            result = self.health_checker.check_memory()
            return result.to_dict()

        @self.app.get("/health/disk")
        async def health_disk() -> Dict[str, Any]:
            """磁盘健康检查"""
            result = self.health_checker.check_disk()
            return result.to_dict()

        @self.app.get("/metrics/summary")
        async def metrics_summary() -> Dict[str, Any]:
            """指标摘要"""
            summary = self.health_checker.get_metrics_summary()
            return summary.to_dict()

    def run(self, host: str = "0.0.0.0", port: int = 8000) -> None:
        """启动API服务"""
        try:
            import uvicorn  # pylint: disable=import-outside-toplevel

            logger.info(f"启动HealthAPI服务: {host}:{port}")
            uvicorn.run(self.app, host=host, port=port)
        except ImportError:
            raise ImportError("uvicorn未安装，请运行: pip install uvicorn")  # pylint: disable=w0707


def create_health_api(
    redis_client: Optional[Any] = None, memory_threshold: float = 90.0, disk_threshold: float = 90.0
) -> "HealthAPI":
    """创建健康检查API实例"""
    return HealthAPI(redis_client=redis_client, memory_threshold=memory_threshold, disk_threshold=disk_threshold)


def system_health_check(redis_client: Optional[Any] = None) -> Dict[str, Any]:
    """系统健康检查便捷函数"""
    checker = HealthChecker(redis_client=redis_client)
    report = checker.run_all_checks()
    return report.to_dict()


if __name__ == "__main__":
    api = create_health_api()
    api.run(host="0.0.0.0", port=8000)
