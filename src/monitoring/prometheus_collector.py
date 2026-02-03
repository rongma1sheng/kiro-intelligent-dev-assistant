"""Prometheus指标采集器

白皮书依据: 第十三章 13.1 Prometheus指标埋点
"""

import subprocess
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional

from loguru import logger

try:
    import psutil
except ImportError:
    psutil = None

try:
    from prometheus_client import REGISTRY, Counter, Gauge, Histogram, Info, start_http_server

    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    Counter = Histogram = Gauge = Info = None


class MetricType(Enum):
    """指标类型枚举"""

    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    INFO = "info"


@dataclass
class MetricDefinition:
    """指标定义

    白皮书依据: 第十三章 13.1.1 核心指标定义

    Attributes:
        name: 指标名称
        description: 指标描述
        metric_type: 指标类型
        labels: 标签列表
        buckets: 直方图桶（仅用于Histogram类型）
    """

    name: str
    description: str
    metric_type: MetricType
    labels: list = field(default_factory=list)
    buckets: tuple = field(default_factory=lambda: (0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0))


@dataclass
class CollectionResult:
    """采集结果

    Attributes:
        success: 是否成功
        metrics_count: 采集的指标数量
        duration_ms: 采集耗时（毫秒）
        errors: 错误列表
        timestamp: 采集时间戳
    """

    success: bool
    metrics_count: int
    duration_ms: float
    errors: list = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)


class PrometheusMetricsCollector:
    """Prometheus指标采集器

    白皮书依据: 第十三章 13.1 Prometheus指标埋点

    核心功能：
    1. 启动Prometheus HTTP服务器暴露指标（端口9090）
    2. 采集系统指标（CPU、内存、磁盘）
    3. 采集GPU指标（显存、利用率、温度）
    4. 采集业务指标（组合价值、PnL）
    5. 支持自定义指标注册

    Attributes:
        port: Prometheus HTTP服务器端口
        collection_interval: 采集间隔（秒）
        running: 运行状态
        metrics: 已注册的指标字典
        redis_client: Redis客户端（可选）
        registry: Prometheus注册表
    """

    # 默认指标定义
    DEFAULT_METRICS = [
        # 交易指标
        MetricDefinition(
            "mia_trades_total", "Total number of trades", MetricType.COUNTER, ["strategy", "action", "status"]
        ),
        MetricDefinition(
            "mia_trade_latency_seconds",
            "Trade execution latency",
            MetricType.HISTOGRAM,
            buckets=(0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0),
        ),
        MetricDefinition("mia_trade_volume", "Trade volume in CNY", MetricType.GAUGE, ["strategy"]),
        # Soldier指标
        MetricDefinition(
            "mia_soldier_latency_seconds",
            "Soldier decision latency",
            MetricType.HISTOGRAM,
            ["mode"],
            (0.01, 0.05, 0.1, 0.15, 0.2, 0.5, 1.0),
        ),
        MetricDefinition("mia_soldier_mode", "Soldier mode (0=local, 1=cloud)", MetricType.GAUGE),
        MetricDefinition(
            "mia_soldier_decisions_total", "Total Soldier decisions", MetricType.COUNTER, ["mode", "action"]
        ),
        # GPU指标
        MetricDefinition("mia_gpu_memory_used_bytes", "GPU memory used in bytes", MetricType.GAUGE),
        MetricDefinition("mia_gpu_memory_total_bytes", "GPU memory total in bytes", MetricType.GAUGE),
        MetricDefinition("mia_gpu_utilization_percent", "GPU utilization percentage", MetricType.GAUGE),
        MetricDefinition("mia_gpu_fragmentation_ratio", "GPU memory fragmentation ratio", MetricType.GAUGE),
        MetricDefinition("mia_gpu_temperature_celsius", "GPU temperature in Celsius", MetricType.GAUGE),
        # Redis指标
        MetricDefinition(
            "mia_redis_latency_seconds",
            "Redis operation latency",
            MetricType.HISTOGRAM,
            ["operation"],
            (0.001, 0.005, 0.01, 0.05, 0.1, 0.5),
        ),
        MetricDefinition("mia_redis_failures_total", "Total Redis connection failures", MetricType.COUNTER),
        MetricDefinition("mia_redis_connections", "Active Redis connections", MetricType.GAUGE),
        # 系统指标
        MetricDefinition("mia_system_cpu_percent", "CPU usage percentage", MetricType.GAUGE),
        MetricDefinition("mia_system_memory_percent", "Memory usage percentage", MetricType.GAUGE),
        MetricDefinition("mia_system_memory_available_gb", "Available memory in GB", MetricType.GAUGE),
        MetricDefinition("mia_system_disk_percent", "Disk usage percentage", MetricType.GAUGE, ["drive"]),
        MetricDefinition("mia_system_disk_free_gb", "Free disk space in GB", MetricType.GAUGE, ["drive"]),
        # 业务指标
        MetricDefinition("mia_portfolio_value", "Total portfolio value in CNY", MetricType.GAUGE),
        MetricDefinition("mia_portfolio_pnl", "Portfolio PnL", MetricType.GAUGE, ["period"]),
        MetricDefinition("mia_portfolio_positions", "Number of open positions", MetricType.GAUGE),
        MetricDefinition("mia_portfolio_cash", "Available cash in CNY", MetricType.GAUGE),
        # Arena指标
        MetricDefinition("mia_arena_battles_total", "Total Arena battles", MetricType.COUNTER, ["track"]),
        MetricDefinition("mia_arena_survivors", "Number of surviving strategies", MetricType.GAUGE, ["track"]),
    ]

    def __init__(
        self,
        port: int = 9090,
        collection_interval: int = 10,
        redis_client: Optional[Any] = None,
        registry: Optional[Any] = None,
    ):
        """初始化Prometheus指标采集器

        Args:
            port: Prometheus HTTP服务器端口，默认9090
            collection_interval: 采集间隔（秒），默认10秒
            redis_client: Redis客户端（可选）
            registry: Prometheus注册表（可选，用于测试）

        Raises:
            ValueError: 当端口号无效时
            ValueError: 当采集间隔无效时
        """
        if not 1 <= port <= 65535:
            raise ValueError(f"端口号必须在1-65535之间，当前: {port}")

        if collection_interval < 1:
            raise ValueError(f"采集间隔必须>=1秒，当前: {collection_interval}")

        self.port: int = port
        self.collection_interval: int = collection_interval
        self.redis_client: Optional[Any] = redis_client
        self.registry: Optional[Any] = registry

        self.running: bool = False
        self.metrics: Dict[str, Any] = {}
        self._collection_thread: Optional[threading.Thread] = None
        self._server_started: bool = False
        self._last_collection_time: Optional[datetime] = None
        self._collection_count: int = 0
        self._error_count: int = 0

        # 初始化指标
        self._initialize_metrics()

        logger.info(f"PrometheusMetricsCollector初始化完成: " f"port={port}, interval={collection_interval}s")

    def _initialize_metrics(self) -> None:
        """初始化所有默认指标

        白皮书依据: 第十三章 13.1.1 核心指标定义
        """
        if not PROMETHEUS_AVAILABLE:
            logger.warning("prometheus_client未安装，指标功能将被禁用")
            return

        registry = self.registry or REGISTRY

        for metric_def in self.DEFAULT_METRICS:
            try:
                metric = self._create_metric(metric_def, registry)
                if metric is not None:
                    self.metrics[metric_def.name] = metric
            except Exception as e:
                logger.warning(f"创建指标失败: {metric_def.name}, 错误: {e}")

        # 创建系统信息指标
        try:
            system_info = Info("mia_system", "MIA system information", registry=registry)
            system_info.info({"version": "v1.6.1", "python_version": "3.10", "platform": "Windows"})
            self.metrics["mia_system"] = system_info
        except Exception as e:
            logger.warning(f"创建系统信息指标失败: {e}")

        logger.info(f"已初始化 {len(self.metrics)} 个指标")

    def _create_metric(self, metric_def: MetricDefinition, registry: Any) -> Optional[Any]:
        """创建单个指标

        Args:
            metric_def: 指标定义
            registry: Prometheus注册表

        Returns:
            创建的指标对象，失败返回None
        """
        if not PROMETHEUS_AVAILABLE:
            return None

        if metric_def.metric_type == MetricType.COUNTER:
            return Counter(metric_def.name, metric_def.description, metric_def.labels, registry=registry)
        elif metric_def.metric_type == MetricType.GAUGE:
            return Gauge(metric_def.name, metric_def.description, metric_def.labels, registry=registry)
        elif metric_def.metric_type == MetricType.HISTOGRAM:
            return Histogram(
                metric_def.name,
                metric_def.description,
                metric_def.labels,
                buckets=metric_def.buckets,
                registry=registry,
            )
        else:
            logger.warning(f"不支持的指标类型: {metric_def.metric_type}")
            return None

    def start(self, blocking: bool = False) -> bool:
        """启动Prometheus HTTP服务器和采集循环

        白皮书依据: 第十三章 13.1.2 指标采集器

        Args:
            blocking: 是否阻塞运行，默认False（后台线程运行）

        Returns:
            是否成功启动

        Raises:
            RuntimeError: 当服务器已经启动时
        """
        if self.running:
            raise RuntimeError("采集器已经在运行中")

        if not PROMETHEUS_AVAILABLE:
            logger.error("prometheus_client未安装，无法启动服务器")
            return False

        try:
            # 启动HTTP服务器
            if not self._server_started:
                start_http_server(self.port, registry=self.registry or REGISTRY)
                self._server_started = True
                logger.info(f"[Metrics] Prometheus exporter started on port {self.port}")

            self.running = True

            if blocking:
                self._collect_loop()
            else:
                self._collection_thread = threading.Thread(
                    target=self._collect_loop, daemon=True, name="PrometheusCollector"
                )
                self._collection_thread.start()
                logger.info("采集线程已启动")

            return True

        except Exception as e:
            logger.error(f"启动Prometheus服务器失败: {e}")
            self.running = False
            return False

    def stop(self) -> None:
        """停止采集循环

        注意: Prometheus HTTP服务器无法优雅停止，只能停止采集循环
        """
        if not self.running:
            logger.warning("采集器未在运行")
            return

        self.running = False

        if self._collection_thread and self._collection_thread.is_alive():
            self._collection_thread.join(timeout=5.0)
            if self._collection_thread.is_alive():
                logger.warning("采集线程未能在5秒内停止")

        logger.info("采集器已停止")

    def _collect_loop(self) -> None:
        """指标采集循环

        白皮书依据: 第十三章 13.1.2 指标采集器
        """
        logger.info(f"开始指标采集循环，间隔: {self.collection_interval}秒")

        while self.running:
            try:
                result = self.collect_all_metrics()
                self._collection_count += 1
                self._last_collection_time = datetime.now()

                if not result.success:
                    self._error_count += 1
                    for error in result.errors:
                        logger.warning(f"采集错误: {error}")

                time.sleep(self.collection_interval)

            except Exception as e:
                self._error_count += 1
                logger.error(f"[Metrics] Collection error: {e}")
                time.sleep(self.collection_interval)

    def collect_all_metrics(self) -> CollectionResult:
        """采集所有指标

        Returns:
            采集结果
        """
        start_time = time.time()
        errors = []
        metrics_count = 0

        # 采集系统指标
        try:
            count = self.collect_system_metrics()
            metrics_count += count
        except Exception as e:
            errors.append(f"系统指标采集失败: {e}")

        # 采集GPU指标
        try:
            count = self.collect_gpu_metrics()
            metrics_count += count
        except Exception as e:
            errors.append(f"GPU指标采集失败: {e}")

        # 采集业务指标
        try:
            count = self.collect_business_metrics()
            metrics_count += count
        except Exception as e:
            errors.append(f"业务指标采集失败: {e}")

        duration_ms = (time.time() - start_time) * 1000

        return CollectionResult(
            success=len(errors) == 0,
            metrics_count=metrics_count,
            duration_ms=duration_ms,
            errors=errors,
            timestamp=datetime.now(),
        )

    def collect_system_metrics(self) -> int:
        """采集系统指标

        白皮书依据: 第十三章 13.1.2 指标采集器 - collect_system_metrics()

        采集内容：
        - CPU使用率
        - 内存使用率和可用内存
        - 磁盘使用率和可用空间

        Returns:
            采集的指标数量
        """
        if psutil is None:
            logger.warning("psutil未安装，无法采集系统指标")
            return 0

        metrics_count = 0

        # CPU使用率
        cpu_metric = self.metrics.get("mia_system_cpu_percent")
        if cpu_metric:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            cpu_metric.set(cpu_percent)
            metrics_count += 1

        # 内存
        mem = psutil.virtual_memory()

        mem_percent_metric = self.metrics.get("mia_system_memory_percent")
        if mem_percent_metric:
            mem_percent_metric.set(mem.percent)
            metrics_count += 1

        mem_available_metric = self.metrics.get("mia_system_memory_available_gb")
        if mem_available_metric:
            mem_available_gb = mem.available / (1024**3)
            mem_available_metric.set(mem_available_gb)
            metrics_count += 1

        # 磁盘
        disk_percent_metric = self.metrics.get("mia_system_disk_percent")
        disk_free_metric = self.metrics.get("mia_system_disk_free_gb")

        for drive in ["C:", "D:", "E:"]:
            try:
                disk = psutil.disk_usage(drive)

                if disk_percent_metric:
                    disk_percent_metric.labels(drive=drive).set(disk.percent)
                    metrics_count += 1

                if disk_free_metric:
                    disk_free_gb = disk.free / (1024**3)
                    disk_free_metric.labels(drive=drive).set(disk_free_gb)
                    metrics_count += 1

            except (FileNotFoundError, PermissionError):
                # 驱动器不存在或无权限访问
                pass

        return metrics_count

    def collect_gpu_metrics(self) -> int:
        """采集GPU指标

        白皮书依据: 第十三章 13.1.2 指标采集器 - collect_gpu_metrics()

        采集内容：
        - GPU显存使用量
        - GPU显存总量
        - GPU利用率
        - GPU温度
        - GPU显存碎片化率

        Returns:
            采集的指标数量
        """
        metrics_count = 0

        try:
            result = subprocess.run(
                ["rocm-smi", "--showmeminfo", "vram", "--showuse", "--showtemp"],
                capture_output=True,
                text=True,
                timeout=2,
            )

            if result.returncode != 0:
                logger.debug("rocm-smi命令执行失败")
                return 0

            output = result.stdout

            # 解析GPU显存使用量
            memory_used = self._parse_gpu_memory_used(output)
            memory_total = self._parse_gpu_memory_total(output)
            utilization = self._parse_gpu_utilization(output)
            temperature = self._parse_gpu_temperature(output)

            # 设置指标
            mem_used_metric = self.metrics.get("mia_gpu_memory_used_bytes")
            if mem_used_metric and memory_used is not None:
                mem_used_metric.set(memory_used)
                metrics_count += 1

            mem_total_metric = self.metrics.get("mia_gpu_memory_total_bytes")
            if mem_total_metric and memory_total is not None:
                mem_total_metric.set(memory_total)
                metrics_count += 1

            util_metric = self.metrics.get("mia_gpu_utilization_percent")
            if util_metric and utilization is not None:
                util_metric.set(utilization)
                metrics_count += 1

            temp_metric = self.metrics.get("mia_gpu_temperature_celsius")
            if temp_metric and temperature is not None:
                temp_metric.set(temperature)
                metrics_count += 1

            # 计算碎片化率
            frag_metric = self.metrics.get("mia_gpu_fragmentation_ratio")
            if frag_metric and memory_total and memory_total > 0 and memory_used is not None:
                fragmentation = 1.0 - (memory_used / memory_total)
                frag_metric.set(fragmentation)
                metrics_count += 1

        except FileNotFoundError:
            logger.debug("rocm-smi未找到，可能不是AMD GPU")
        except subprocess.TimeoutExpired:
            logger.warning("rocm-smi命令超时")
        except Exception as e:
            logger.warning(f"[Metrics] GPU collection failed: {e}")

        return metrics_count

    def _parse_gpu_memory_used(self, output: str) -> Optional[int]:
        """解析GPU显存使用量

        Args:
            output: rocm-smi输出

        Returns:
            显存使用量（字节），解析失败返回None
        """
        try:
            for line in output.split("\n"):
                if "VRAM" in line and "Used" in line:
                    # 格式: "VRAM Used: 1234 MB"
                    parts = line.split(":")
                    if len(parts) >= 2:
                        value_str = parts[1].strip().split()[0]
                        value_mb = int(value_str)
                        return value_mb * 1024 * 1024
        except (ValueError, IndexError):
            pass
        return None

    def _parse_gpu_memory_total(self, output: str) -> Optional[int]:
        """解析GPU显存总量

        Args:
            output: rocm-smi输出

        Returns:
            显存总量（字节），解析失败返回None
        """
        try:
            for line in output.split("\n"):
                if "VRAM" in line and "Total" in line:
                    # 格式: "VRAM Total: 32768 MB"
                    parts = line.split(":")
                    if len(parts) >= 2:
                        value_str = parts[1].strip().split()[0]
                        value_mb = int(value_str)
                        return value_mb * 1024 * 1024
        except (ValueError, IndexError):
            pass
        return None

    def _parse_gpu_utilization(self, output: str) -> Optional[float]:
        """解析GPU利用率

        Args:
            output: rocm-smi输出

        Returns:
            利用率百分比，解析失败返回None
        """
        try:
            for line in output.split("\n"):
                if "GPU use" in line or "GPU Utilization" in line:
                    # 格式: "GPU use: 45%"
                    parts = line.split(":")
                    if len(parts) >= 2:
                        value_str = parts[1].strip().replace("%", "")
                        return float(value_str)
        except (ValueError, IndexError):
            pass
        return None

    def _parse_gpu_temperature(self, output: str) -> Optional[float]:
        """解析GPU温度

        Args:
            output: rocm-smi输出

        Returns:
            温度（摄氏度），解析失败返回None
        """
        try:
            for line in output.split("\n"):
                if "Temperature" in line or "Temp" in line:
                    # 格式: "Temperature: 65.0 C"
                    parts = line.split(":")
                    if len(parts) >= 2:
                        value_str = parts[1].strip().split()[0]
                        return float(value_str)
        except (ValueError, IndexError):
            pass
        return None

    def collect_business_metrics(self) -> int:
        """采集业务指标

        白皮书依据: 第十三章 13.1.2 指标采集器 - collect_business_metrics()

        采集内容：
        - 组合总价值
        - 每日/每周/每月PnL
        - 持仓数量
        - 可用资金
        - Soldier模式

        Returns:
            采集的指标数量
        """
        if self.redis_client is None:
            logger.debug("Redis客户端未配置，跳过业务指标采集")
            return 0

        metrics_count = 0

        try:
            # 组合总价值
            portfolio_value_metric = self.metrics.get("mia_portfolio_value")
            if portfolio_value_metric:
                total_value = self._get_redis_float("portfolio:total_value", 0.0)
                portfolio_value_metric.set(total_value)
                metrics_count += 1

            # PnL
            pnl_metric = self.metrics.get("mia_portfolio_pnl")
            if pnl_metric:
                for period in ["daily", "weekly", "monthly", "total"]:
                    pnl_value = self._get_redis_float(f"portfolio:{period}_pnl", 0.0)
                    pnl_metric.labels(period=period).set(pnl_value)
                    metrics_count += 1

            # 持仓数量
            positions_metric = self.metrics.get("mia_portfolio_positions")
            if positions_metric:
                positions = self._get_redis_int("portfolio:positions_count", 0)
                positions_metric.set(positions)
                metrics_count += 1

            # 可用资金
            cash_metric = self.metrics.get("mia_portfolio_cash")
            if cash_metric:
                cash = self._get_redis_float("portfolio:available_cash", 0.0)
                cash_metric.set(cash)
                metrics_count += 1

            # Soldier模式
            soldier_mode_metric = self.metrics.get("mia_soldier_mode")
            if soldier_mode_metric:
                mode = self._get_redis_string("mia:soldier:mode", "local")
                soldier_mode_metric.set(1 if mode == "cloud" else 0)
                metrics_count += 1

        except Exception as e:
            logger.warning(f"[Metrics] Business metrics collection failed: {e}")

        return metrics_count

    def _get_redis_float(self, key: str, default: float = 0.0) -> float:
        """从Redis获取浮点数值

        Args:
            key: Redis键
            default: 默认值

        Returns:
            浮点数值
        """
        try:
            value = self.redis_client.get(key)
            if value is not None:
                if isinstance(value, bytes):
                    value = value.decode("utf-8")
                return float(value)
        except (ValueError, TypeError):
            pass
        return default

    def _get_redis_int(self, key: str, default: int = 0) -> int:
        """从Redis获取整数值

        Args:
            key: Redis键
            default: 默认值

        Returns:
            整数值
        """
        try:
            value = self.redis_client.get(key)
            if value is not None:
                if isinstance(value, bytes):
                    value = value.decode("utf-8")
                return int(float(value))
        except (ValueError, TypeError):
            pass
        return default

    def _get_redis_string(self, key: str, default: str = "") -> str:
        """从Redis获取字符串值

        Args:
            key: Redis键
            default: 默认值

        Returns:
            字符串值
        """
        try:
            value = self.redis_client.get(key)
            if value is not None:
                if isinstance(value, bytes):
                    return value.decode("utf-8")
                return str(value)
        except (ValueError, TypeError):
            pass
        return default

    def register_custom_metric(
        self,
        name: str,
        description: str,
        metric_type: MetricType,
        labels: Optional[list] = None,
        buckets: Optional[tuple] = None,
    ) -> bool:
        """注册自定义指标

        Args:
            name: 指标名称
            description: 指标描述
            metric_type: 指标类型
            labels: 标签列表
            buckets: 直方图桶（仅用于Histogram类型）

        Returns:
            是否注册成功

        Raises:
            ValueError: 当指标名称已存在时
        """
        if name in self.metrics:
            raise ValueError(f"指标已存在: {name}")

        if not PROMETHEUS_AVAILABLE:
            logger.warning("prometheus_client未安装，无法注册指标")
            return False

        metric_def = MetricDefinition(
            name=name,
            description=description,
            metric_type=metric_type,
            labels=labels or [],
            buckets=buckets or (0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0),
        )

        registry = self.registry or REGISTRY
        metric = self._create_metric(metric_def, registry)

        if metric is not None:
            self.metrics[name] = metric
            logger.info(f"已注册自定义指标: {name}")
            return True

        return False

    def get_metric(self, name: str) -> Optional[Any]:
        """获取指标对象

        Args:
            name: 指标名称

        Returns:
            指标对象，不存在返回None
        """
        return self.metrics.get(name)

    def record_trade(
        self, strategy: str, action: str, status: str, latency: Optional[float] = None, volume: Optional[float] = None
    ) -> None:
        """记录交易指标

        白皮书依据: 第十三章 13.1.3 业务代码埋点示例

        Args:
            strategy: 策略名称
            action: 交易动作（buy/sell/hold）
            status: 交易状态（success/failed）
            latency: 交易延迟（秒）
            volume: 交易金额
        """
        # 交易计数
        trades_metric = self.metrics.get("mia_trades_total")
        if trades_metric:
            trades_metric.labels(strategy=strategy, action=action, status=status).inc()

        # 交易延迟
        if latency is not None:
            latency_metric = self.metrics.get("mia_trade_latency_seconds")
            if latency_metric:
                latency_metric.observe(latency)

        # 交易金额
        if volume is not None:
            volume_metric = self.metrics.get("mia_trade_volume")
            if volume_metric:
                volume_metric.labels(strategy=strategy).set(volume)

    def record_soldier_decision(self, mode: str, action: str, latency: float) -> None:
        """记录Soldier决策指标

        白皮书依据: 第十三章 13.1.3 业务代码埋点示例

        Args:
            mode: 模式（local/cloud）
            action: 决策动作
            latency: 决策延迟（秒）
        """
        # 决策计数
        decisions_metric = self.metrics.get("mia_soldier_decisions_total")
        if decisions_metric:
            decisions_metric.labels(mode=mode, action=action).inc()

        # 决策延迟
        latency_metric = self.metrics.get("mia_soldier_latency_seconds")
        if latency_metric:
            latency_metric.labels(mode=mode).observe(latency)

    def record_redis_operation(self, operation: str, latency: float, success: bool = True) -> None:
        """记录Redis操作指标

        Args:
            operation: 操作类型（get/set/ping等）
            latency: 操作延迟（秒）
            success: 是否成功
        """
        # 操作延迟
        latency_metric = self.metrics.get("mia_redis_latency_seconds")
        if latency_metric:
            latency_metric.labels(operation=operation).observe(latency)

        # 失败计数
        if not success:
            failures_metric = self.metrics.get("mia_redis_failures_total")
            if failures_metric:
                failures_metric.inc()

    def record_arena_battle(self, track: str, survivors: int) -> None:
        """记录Arena战斗指标

        Args:
            track: 赛道（S15/S18）
            survivors: 存活策略数量
        """
        # 战斗计数
        battles_metric = self.metrics.get("mia_arena_battles_total")
        if battles_metric:
            battles_metric.labels(track=track).inc()

        # 存活数量
        survivors_metric = self.metrics.get("mia_arena_survivors")
        if survivors_metric:
            survivors_metric.labels(track=track).set(survivors)

    def get_status(self) -> Dict[str, Any]:
        """获取采集器状态

        Returns:
            状态信息字典
        """
        return {
            "running": self.running,
            "port": self.port,
            "collection_interval": self.collection_interval,
            "metrics_count": len(self.metrics),
            "collection_count": self._collection_count,
            "error_count": self._error_count,
            "last_collection_time": self._last_collection_time.isoformat() if self._last_collection_time else None,
            "server_started": self._server_started,
        }

    def get_metrics_list(self) -> list:
        """获取已注册的指标列表

        Returns:
            指标名称列表
        """
        return list(self.metrics.keys())


# 便捷函数
def create_metrics_collector(
    port: int = 9090, collection_interval: int = 10, redis_client: Optional[Any] = None
) -> PrometheusMetricsCollector:
    """创建指标采集器的便捷函数

    Args:
        port: Prometheus HTTP服务器端口
        collection_interval: 采集间隔（秒）
        redis_client: Redis客户端

    Returns:
        PrometheusMetricsCollector实例
    """
    return PrometheusMetricsCollector(port=port, collection_interval=collection_interval, redis_client=redis_client)


# 主程序入口
if __name__ == "__main__":
    import redis

    try:
        redis_client = redis.Redis(host="localhost", port=6379)
        redis_client.ping()
    except Exception:
        redis_client = None
        logger.warning("Redis连接失败，业务指标将不可用")

    collector = PrometheusMetricsCollector(port=9090, collection_interval=10, redis_client=redis_client)

    collector.start(blocking=True)
