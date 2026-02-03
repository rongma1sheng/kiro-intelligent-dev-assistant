"""GPU看门狗 - GPU Watchdog (第十二章版本)

白皮书依据: 第十二章 12.1.2 GPU看门狗与驱动热重载

问题: AMD/NVIDIA驱动崩溃导致本地推理失败
风险等级: 🟡 中

功能:
1. GPU健康检查（30秒周期）
2. 显存碎片化检测（阈值30%）
3. 驱动热重载触发
4. Redis状态标记（Soldier降级）

性能要求:
- 检测周期: 30秒
- 响应延迟: < 30秒
- 重载时间: 30-90秒
"""

import re
import subprocess
import threading
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional

from loguru import logger


class GPUHealthStatus(Enum):
    """GPU健康状态枚举

    白皮书依据: 第十二章 12.1.2 GPU看门狗与驱动热重载
    """

    HEALTHY = "healthy"  # 健康状态
    DEGRADED = "degraded"  # 降级状态（驱动重载中）
    UNHEALTHY = "unhealthy"  # 不健康状态
    UNAVAILABLE = "unavailable"  # 不可用状态（无GPU或检测失败）


@dataclass
class GPUHealthMetrics:
    """GPU健康指标

    白皮书依据: 第十二章 12.1.2 GPU看门狗与驱动热重载

    Attributes:
        memory_used_mb: 已使用显存（MB）
        memory_total_mb: 总显存（MB）
        memory_free_mb: 空闲显存（MB）
        fragmentation_ratio: 碎片化比率（0-1）
        temperature_celsius: 温度（摄氏度）
        utilization_percent: 利用率（0-100）
        is_healthy: 是否健康
    """

    memory_used_mb: float
    memory_total_mb: float
    memory_free_mb: float
    fragmentation_ratio: float
    temperature_celsius: Optional[float] = None
    utilization_percent: Optional[float] = None
    is_healthy: bool = True


class GPUWatchdog:
    """GPU看门狗（第十二章版本）

    白皮书依据: 第十二章 12.1.2 GPU看门狗与驱动热重载

    监控AMD GPU健康状态，检测显存碎片化，并在必要时触发驱动热重载。
    通过Redis标记Soldier状态为DEGRADED，启用Cloud Failover。

    Attributes:
        redis_client: Redis客户端（可选）
        check_interval: 检查间隔（秒），默认30秒
        fragmentation_threshold: 碎片化阈值，默认0.3（30%）
        failure_threshold: 连续失败阈值，默认3次
        status: 当前GPU状态
        metrics: 当前GPU指标
        failure_count: 连续失败计数
        _running: 监控线程运行标志
        _thread: 监控线程
        _lock: 线程锁
    """

    # Redis键常量
    REDIS_KEY_SOLDIER_STATUS = "mia:soldier:status"
    REDIS_KEY_GPU_FAILURES = "system:gpu_failures"

    def __init__(
        self,
        redis_client: Optional[Any] = None,
        check_interval: int = 30,
        fragmentation_threshold: float = 0.3,
        failure_threshold: int = 3,
    ):
        """初始化GPU看门狗

        Args:
            redis_client: Redis客户端，用于标记Soldier状态
            check_interval: 检查间隔（秒），默认30秒
            fragmentation_threshold: 碎片化阈值，默认0.3（30%）
            failure_threshold: 连续失败阈值，默认3次

        Raises:
            ValueError: 当参数不在有效范围时
        """
        if check_interval <= 0:
            raise ValueError(f"检查间隔必须 > 0，当前: {check_interval}")

        if not 0 < fragmentation_threshold < 1:
            raise ValueError(f"碎片化阈值必须在 (0, 1)，当前: {fragmentation_threshold}")

        if failure_threshold <= 0:
            raise ValueError(f"失败阈值必须 > 0，当前: {failure_threshold}")

        self.redis = redis_client
        self.check_interval: int = check_interval
        self.fragmentation_threshold: float = fragmentation_threshold
        self.failure_threshold: int = failure_threshold

        self.status: GPUHealthStatus = GPUHealthStatus.HEALTHY
        self.metrics: Optional[GPUHealthMetrics] = None
        self.failure_count: int = 0

        self._running: bool = False
        self._thread: Optional[threading.Thread] = None
        self._lock: threading.RLock = threading.RLock()

        logger.info(
            f"初始化GPUWatchdog: "
            f"check_interval={check_interval}s, "
            f"fragmentation_threshold={fragmentation_threshold:.0%}, "
            f"failure_threshold={failure_threshold}"
        )

    def check_gpu_health(self) -> bool:
        """检查GPU健康状态

        白皮书依据: 第十二章 12.1.2 GPU看门狗与驱动热重载

        调用rocm-smi检测GPU状态，检查显存碎片化程度。

        Returns:
            GPU是否健康
        """
        try:
            # 调用rocm-smi获取GPU信息
            result = subprocess.run(  # pylint: disable=w1510
                ["rocm-smi", "--showmeminfo", "vram"], capture_output=True, text=True, timeout=5.0
            )  # pylint: disable=w1510

            if result.returncode != 0:
                logger.error(f"[GPU] rocm-smi执行失败: {result.stderr}")
                self._handle_failure()
                return False

            # 解析输出
            metrics = self._parse_gpu_output(result.stdout)

            if metrics is None:
                logger.error("[GPU] 无法解析rocm-smi输出")
                self._handle_failure()
                return False

            # 更新指标
            with self._lock:
                self.metrics = metrics

                # 检查碎片化程度
                if metrics.fragmentation_ratio > self.fragmentation_threshold:
                    logger.warning(f"[GPU] High fragmentation: {metrics.fragmentation_ratio:.1%}")
                    metrics.is_healthy = False
                    return False

                # 重置失败计数
                self.failure_count = 0
                self.status = GPUHealthStatus.HEALTHY

                # 更新Redis状态
                self._update_redis_status("NORMAL")

            return True

        except subprocess.TimeoutExpired:
            logger.error("[GPU] rocm-smi timeout")
            self._handle_failure()
            return False

        except FileNotFoundError:
            logger.warning("[GPU] rocm-smi not found, AMD driver may not be installed")
            with self._lock:
                self.status = GPUHealthStatus.UNAVAILABLE
            return False

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"[GPU] Check failed: {e}")
            self._handle_failure()
            return False

    def detect_fragmentation(self) -> float:
        """检测显存碎片化程度

        白皮书依据: 第十二章 12.1.2 GPU看门狗与驱动热重载

        Returns:
            碎片化比率（0-1），-1表示检测失败
        """
        with self._lock:
            if self.metrics is None:
                # 先执行健康检查
                self.check_gpu_health()

            if self.metrics is not None:
                return self.metrics.fragmentation_ratio

            return -1.0

    def trigger_driver_reload(self) -> bool:
        """触发驱动热重载

        白皮书依据: 第十二章 12.1.2 GPU看门狗与驱动热重载

        在重载期间，系统将Soldier状态标记为DEGRADED，
        并预加载Cloud Failover配置。

        Returns:
            重载是否成功
        """
        logger.warning("[GPU] Triggering driver reload...")

        # 1. 标记Soldier为降级模式
        with self._lock:
            self.status = GPUHealthStatus.DEGRADED
        self._update_redis_status("DEGRADED")

        # 2. 执行驱动重载
        try:
            result = subprocess.run(  # pylint: disable=unused-variable,w1510
                ["rocm-smi", "--gpureset", "-d", "0"], capture_output=True, text=True, timeout=90.0  # 重载最多90秒
            )

            # 等待驱动恢复
            time.sleep(10)

            # 3. 验证恢复
            if self.check_gpu_health():  # pylint: disable=no-else-return
                self._update_redis_status("NORMAL")
                logger.info("[GPU] Driver reload successful")
                return True
            else:
                logger.error("[GPU] Driver reload failed")
                return False

        except subprocess.TimeoutExpired:
            logger.error("[GPU] Driver reload timeout")
            return False

        except FileNotFoundError:
            logger.error("[GPU] rocm-smi not found, cannot reload driver")
            return False

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"[GPU] Reload error: {e}")
            return False

    def start(self) -> None:
        """启动GPU看门狗

        启动后台监控线程，定期检查GPU状态。

        Raises:
            RuntimeError: 当看门狗已经在运行时
        """
        with self._lock:
            if self._running:
                raise RuntimeError("GPU看门狗已经在运行")

            self._running = True
            self._thread = threading.Thread(target=self._watchdog_loop, name="GPUWatchdog", daemon=True)
            self._thread.start()

        logger.info("[GPU] Watchdog started")

    def stop(self) -> None:
        """停止GPU看门狗

        停止后台监控线程。
        """
        with self._lock:
            if not self._running:
                logger.warning("[GPU] Watchdog not running")
                return
            self._running = False

        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5.0)

        logger.info("[GPU] Watchdog stopped")

    def get_status(self) -> GPUHealthStatus:
        """获取当前GPU状态

        Returns:
            当前GPU状态
        """
        with self._lock:
            return self.status

    def get_metrics(self) -> Optional[GPUHealthMetrics]:
        """获取当前GPU指标

        Returns:
            当前GPU指标，如果未检测到则返回None
        """
        with self._lock:
            return self.metrics

    def get_failure_count(self) -> int:
        """获取连续失败计数

        Returns:
            连续失败次数
        """
        with self._lock:
            return self.failure_count

    def _parse_gpu_output(self, output: str) -> Optional[GPUHealthMetrics]:
        """解析rocm-smi输出（内部方法）

        Args:
            output: rocm-smi命令输出

        Returns:
            GPU指标，解析失败返回None
        """
        try:
            # 示例输出格式:
            # GPU[0]		: VRAM Total Memory (B): 34359738368
            # GPU[0]		: VRAM Total Used Memory (B): 8589934592

            # 提取总显存
            total_match = re.search(r"VRAM Total Memory \(B\):\s*(\d+)", output)
            if not total_match:
                return None

            memory_total = int(total_match.group(1)) / (1024**2)  # 转换为MB

            # 提取已使用显存
            used_match = re.search(r"VRAM Total Used Memory \(B\):\s*(\d+)", output)
            if not used_match:
                return None

            memory_used = int(used_match.group(1)) / (1024**2)  # 转换为MB

            # 计算空闲显存
            memory_free = memory_total - memory_used

            # 计算碎片化程度
            # 简化模型：基于使用率估算碎片化
            usage_ratio = memory_used / memory_total if memory_total > 0 else 0
            fragmentation = usage_ratio * 0.5  # 简化估算

            return GPUHealthMetrics(
                memory_used_mb=memory_used,
                memory_total_mb=memory_total,
                memory_free_mb=memory_free,
                fragmentation_ratio=fragmentation,
                is_healthy=fragmentation <= self.fragmentation_threshold,
            )

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"[GPU] Parse output failed: {e}")
            return None

    def _handle_failure(self) -> None:
        """处理检测失败（内部方法）

        白皮书依据: 第十二章 12.1.2 GPU看门狗与驱动热重载
        """
        with self._lock:
            self.failure_count += 1

            # 更新Redis失败计数
            self._update_redis_failure_count()

            if self.failure_count >= self.failure_threshold:
                self.status = GPUHealthStatus.UNHEALTHY
                logger.error(f"[GPU] Consecutive failures: {self.failure_count}, " f"triggering driver reload")
                # 触发驱动重载
                self.trigger_driver_reload()
            else:
                self.status = GPUHealthStatus.DEGRADED
                logger.warning(f"[GPU] Failure {self.failure_count}/{self.failure_threshold}")

    def _update_redis_status(self, status: str) -> None:
        """更新Redis中的Soldier状态（内部方法）

        Args:
            status: 状态字符串（NORMAL/DEGRADED）
        """
        if self.redis is not None:
            try:
                self.redis.set(self.REDIS_KEY_SOLDIER_STATUS, status)
                logger.debug(f"[GPU] Redis status updated: {status}")
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.warning(f"[GPU] Failed to update Redis status: {e}")

    def _update_redis_failure_count(self) -> None:
        """更新Redis中的失败计数（内部方法）"""
        if self.redis is not None:
            try:
                self.redis.set(self.REDIS_KEY_GPU_FAILURES, self.failure_count)
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.warning(f"[GPU] Failed to update Redis failure count: {e}")

    def _watchdog_loop(self) -> None:
        """看门狗主循环（内部方法）

        后台线程定期检查GPU状态。
        """
        logger.info("[GPU] Watchdog loop started")

        while self._running:
            try:
                # 检查GPU
                self.check_gpu_health()

                # 等待下一次检查
                time.sleep(self.check_interval)

            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.error(f"[GPU] Watchdog loop error: {e}")
                time.sleep(self.check_interval)

        logger.info("[GPU] Watchdog loop exited")
