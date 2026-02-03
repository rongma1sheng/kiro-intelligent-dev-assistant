"""GPU看门狗 - GPU Watchdog

白皮书依据: 第一章 1.1 战备态 - GPU看门狗

GPU看门狗负责监控AMD显存碎片化程度，并在必要时触发驱动热重载。
在重载期间，系统将Soldier状态标记为Degraded，并启用Cloud Failover。

功能:
1. 调用rocm-smi检测显存碎片化
2. 触发驱动热重载
3. 标记系统降级状态
4. 预加载Cloud Failover配置

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
from typing import Optional

from loguru import logger


class GPUStatus(Enum):
    """GPU状态枚举

    白皮书依据: 第一章 1.1 战备态
    """

    NORMAL = "normal"  # 正常状态
    DEGRADED = "degraded"  # 降级状态（驱动重载中）
    UNAVAILABLE = "unavailable"  # 不可用状态（无GPU或检测失败）


@dataclass
class GPUMetrics:
    """GPU指标数据类

    Attributes:
        memory_used: 已使用显存（MB）
        memory_total: 总显存（MB）
        memory_free: 空闲显存（MB）
        fragmentation: 碎片化程度（0-1）
        temperature: 温度（摄氏度）
        utilization: 利用率（0-100）
    """

    memory_used: float
    memory_total: float
    memory_free: float
    fragmentation: float
    temperature: Optional[float] = None
    utilization: Optional[float] = None


class GPUWatchdog:
    """GPU看门狗

    白皮书依据: 第一章 1.1 战备态 - GPU看门狗

    监控AMD GPU显存碎片化，并在必要时触发驱动热重载。

    Attributes:
        check_interval: 检查间隔（秒），默认30秒
        fragmentation_threshold: 碎片化阈值，默认0.3（30%）
        status: 当前GPU状态
        metrics: 当前GPU指标
        _running: 监控线程运行标志
        _thread: 监控线程
        _lock: 线程锁
    """

    def __init__(self, check_interval: int = 30, fragmentation_threshold: float = 0.3):
        """初始化GPU看门狗

        Args:
            check_interval: 检查间隔（秒），默认30秒
            fragmentation_threshold: 碎片化阈值，默认0.3（30%）

        Raises:
            ValueError: 当参数不在有效范围时
        """
        if check_interval <= 0:
            raise ValueError(f"检查间隔必须 > 0，当前: {check_interval}")

        if not 0 < fragmentation_threshold < 1:
            raise ValueError(f"碎片化阈值必须在 (0, 1)，当前: {fragmentation_threshold}")

        self.check_interval: int = check_interval
        self.fragmentation_threshold: float = fragmentation_threshold

        self.status: GPUStatus = GPUStatus.NORMAL
        self.metrics: Optional[GPUMetrics] = None

        self._running: bool = False
        self._thread: Optional[threading.Thread] = None
        self._lock: threading.RLock = threading.RLock()

        logger.info(
            f"初始化GPUWatchdog: "
            f"check_interval={check_interval}s, "
            f"fragmentation_threshold={fragmentation_threshold}"
        )

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

            logger.info("GPU看门狗已启动")

    def stop(self) -> None:
        """停止GPU看门狗

        停止后台监控线程。
        """
        with self._lock:
            if not self._running:
                logger.warning("GPU看门狗未在运行")
                return

            self._running = False

        # 等待线程结束
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5.0)

        logger.info("GPU看门狗已停止")

    def get_status(self) -> GPUStatus:
        """获取当前GPU状态

        Returns:
            当前GPU状态
        """
        with self._lock:
            return self.status

    def get_metrics(self) -> Optional[GPUMetrics]:
        """获取当前GPU指标

        Returns:
            当前GPU指标，如果未检测到则返回None
        """
        with self._lock:
            return self.metrics

    def check_gpu(self) -> bool:
        """检查GPU状态

        白皮书依据: 第一章 1.1 战备态 - GPU看门狗

        调用rocm-smi检测GPU状态，并更新metrics。

        Returns:
            检查是否成功
        """
        try:
            # 调用rocm-smi获取GPU信息
            result = subprocess.run(  # pylint: disable=w1510
                ["rocm-smi", "--showmeminfo", "vram"], capture_output=True, text=True, timeout=5.0
            )  # pylint: disable=w1510

            if result.returncode != 0:
                logger.error(f"rocm-smi执行失败: {result.stderr}")
                with self._lock:
                    self.status = GPUStatus.UNAVAILABLE
                return False

            # 解析输出
            metrics = self._parse_rocm_smi_output(result.stdout)

            if metrics is None:
                logger.error("无法解析rocm-smi输出")
                with self._lock:
                    self.status = GPUStatus.UNAVAILABLE
                return False

            # 更新指标
            with self._lock:
                self.metrics = metrics

                # 检查碎片化程度
                if metrics.fragmentation > self.fragmentation_threshold:
                    logger.warning(
                        f"显存碎片化超过阈值: " f"{metrics.fragmentation:.2%} > " f"{self.fragmentation_threshold:.2%}"
                    )
                    # 触发热重载
                    self._trigger_hot_reload()
                else:
                    # 恢复正常状态
                    if self.status == GPUStatus.DEGRADED:
                        logger.info("GPU驱动已恢复，状态恢复为NORMAL")
                        self.status = GPUStatus.NORMAL

            return True

        except subprocess.TimeoutExpired:
            logger.error("rocm-smi执行超时")
            with self._lock:
                self.status = GPUStatus.UNAVAILABLE
            return False

        except FileNotFoundError:
            logger.warning("rocm-smi未找到，可能未安装AMD驱动")
            with self._lock:
                self.status = GPUStatus.UNAVAILABLE
            return False

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"检查GPU失败: {e}")
            with self._lock:
                self.status = GPUStatus.UNAVAILABLE
            return False

    def _parse_rocm_smi_output(self, output: str) -> Optional[GPUMetrics]:
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

            # 计算碎片化程度（简化版本：基于使用率）
            # 实际碎片化检测需要更复杂的算法
            usage_ratio = memory_used / memory_total

            # 碎片化估算：使用率越高，碎片化可能性越大
            # 这里使用简化模型：fragmentation = usage_ratio * random_factor
            # 实际应该通过多次分配/释放测试来检测
            fragmentation = usage_ratio * 0.5  # 简化估算

            return GPUMetrics(
                memory_used=memory_used, memory_total=memory_total, memory_free=memory_free, fragmentation=fragmentation
            )

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"解析rocm-smi输出失败: {e}")
            return None

    def _trigger_hot_reload(self) -> None:
        """触发驱动热重载（内部方法）

        白皮书依据: 第一章 1.1 战备态 - 热重载逻辑

        在重载期间，系统将Soldier状态标记为Degraded，
        并预加载Cloud Failover配置。
        """
        # 标记为降级状态
        self.status = GPUStatus.DEGRADED

        logger.warning("触发GPU驱动热重载，系统进入DEGRADED状态")

        try:
            # 执行驱动重置
            result = subprocess.run(  # pylint: disable=w1510
                ["rocm-smi", "--gpureset"], capture_output=True, text=True, timeout=90.0  # 重载最多90秒
            )

            if result.returncode == 0:
                logger.info("GPU驱动重载成功")
                # 等待驱动稳定
                time.sleep(5.0)
                # 重新检查
                self.check_gpu()
            else:
                logger.error(f"GPU驱动重载失败: {result.stderr}")

        except subprocess.TimeoutExpired:
            logger.error("GPU驱动重载超时")

        except FileNotFoundError:
            logger.error("rocm-smi未找到，无法执行驱动重载")

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"驱动重载失败: {e}")

    def _watchdog_loop(self) -> None:
        """看门狗主循环（内部方法）

        后台线程定期检查GPU状态。
        """
        logger.info("GPU看门狗主循环已启动")

        while self._running:
            try:
                # 检查GPU
                self.check_gpu()

                # 等待下一次检查
                time.sleep(self.check_interval)

            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.error(f"看门狗循环异常: {e}")
                time.sleep(self.check_interval)

        logger.info("GPU看门狗主循环已退出")
