"""末日开关 - Doomsday Switch

白皮书依据: 第十二章 12.3 末日开关与应急响应

功能:
1. 检查触发条件（Redis失败、GPU失败、内存/磁盘临界、亏损阈值）
2. 触发紧急停止（创建锁文件、Redis标记、停止交易）
3. 密码认证复位

触发条件:
- Redis连续失败3次
- GPU连续失败3次
- 内存使用>95%
- 磁盘使用>95%
- 单日亏损>10%
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, List, Optional

from loguru import logger

try:
    import psutil

    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    logger.warning("psutil不可用，部分系统检查将被跳过")


class DoomsdayTriggerType(Enum):
    """末日开关触发类型

    白皮书依据: 第十二章 12.3 末日开关与应急响应
    """

    REDIS_FAILURE = "redis_failure"
    GPU_FAILURE = "gpu_failure"
    MEMORY_CRITICAL = "memory_critical"
    DISK_CRITICAL = "disk_critical"
    LOSS_THRESHOLD = "loss_threshold"
    MANUAL = "manual"


@dataclass
class DoomsdayTriggerConfig:
    """末日开关触发配置

    白皮书依据: 第十二章 12.3 末日开关与应急响应

    Attributes:
        redis_failure_threshold: Redis连续失败阈值，默认3
        gpu_failure_threshold: GPU连续失败阈值，默认3
        memory_critical_threshold: 内存临界阈值，默认0.95（95%）
        disk_critical_threshold: 磁盘临界阈值，默认0.95（95%）
        loss_threshold: 单日亏损阈值，默认-0.10（-10%）
        lock_file_path: 锁文件路径
        disk_path: 磁盘检查路径
    """

    redis_failure_threshold: int = 3
    gpu_failure_threshold: int = 3
    memory_critical_threshold: float = 0.95
    disk_critical_threshold: float = 0.95
    loss_threshold: float = -0.10
    lock_file_path: str = "D:/MIA_Data/DOOMSDAY_SWITCH.lock"
    disk_path: str = "D:/"


@dataclass
class DoomsdayStatus:
    """末日开关状态

    白皮书依据: 第十二章 12.3 末日开关与应急响应

    Attributes:
        is_triggered: 是否已触发
        trigger_time: 触发时间
        trigger_reason: 触发原因
        triggers_fired: 触发的条件列表
    """

    is_triggered: bool = False
    trigger_time: Optional[datetime] = None
    trigger_reason: Optional[str] = None
    triggers_fired: List[str] = None

    def __post_init__(self):
        if self.triggers_fired is None:
            self.triggers_fired = []


class DoomsdaySwitch:
    """末日开关

    白皮书依据: 第十二章 12.3 末日开关与应急响应

    提供系统级紧急停止机制，在检测到严重故障时自动触发。

    Attributes:
        redis_client: Redis客户端
        config: 触发配置
        status: 当前状态
        _lock_file: 锁文件路径
    """

    # Redis键常量
    REDIS_KEY_DOOMSDAY = "mia:doomsday"
    REDIS_KEY_DOOMSDAY_REASON = "mia:doomsday:reason"
    REDIS_KEY_REDIS_FAILURES = "system:redis_failures"
    REDIS_KEY_GPU_FAILURES = "system:gpu_failures"
    REDIS_KEY_DAILY_PNL = "portfolio:daily_pnl"
    REDIS_KEY_INITIAL_CAPITAL = "portfolio:initial_capital"
    REDIS_KEY_RESET_PASSWORD = "config:doomsday:password"

    def __init__(self, redis_client: Optional[Any] = None, config: Optional[DoomsdayTriggerConfig] = None):
        """初始化末日开关

        Args:
            redis_client: Redis客户端
            config: 触发配置
        """
        self.redis = redis_client
        self.config: DoomsdayTriggerConfig = config or DoomsdayTriggerConfig()
        self.status: DoomsdayStatus = DoomsdayStatus()

        self._lock_file: Path = Path(self.config.lock_file_path)

        # 检查是否已经触发（锁文件存在）
        if self._lock_file.exists():
            self.status.is_triggered = True
            logger.warning(f"[DOOMSDAY] Lock file exists: {self._lock_file}")

        logger.info(f"初始化DoomsdaySwitch: " f"lock_file={self.config.lock_file_path}")

    def check_triggers(self) -> List[str]:
        """检查触发条件

        白皮书依据: 第十二章 12.3 末日开关与应急响应

        Returns:
            触发的条件列表
        """
        triggers_fired: List[str] = []

        # 检查Redis健康
        redis_failures = self._get_redis_failures()
        if redis_failures >= self.config.redis_failure_threshold:
            triggers_fired.append(f"Redis failures: {redis_failures}")

        # 检查GPU健康
        gpu_failures = self._get_gpu_failures()
        if gpu_failures >= self.config.gpu_failure_threshold:
            triggers_fired.append(f"GPU failures: {gpu_failures}")

        # 检查内存
        memory_percent = self._get_memory_percent()
        if memory_percent > self.config.memory_critical_threshold:
            triggers_fired.append(f"Memory critical: {memory_percent:.1%}")

        # 检查磁盘
        disk_percent = self._get_disk_percent()
        if disk_percent > self.config.disk_critical_threshold:
            triggers_fired.append(f"Disk critical: {disk_percent:.1%}")

        # 检查亏损
        pnl_ratio = self._get_pnl_ratio()
        if pnl_ratio < self.config.loss_threshold:
            triggers_fired.append(f"Loss threshold: {pnl_ratio:.2%}")

        return triggers_fired

    def trigger(self, reason: str) -> None:
        """触发末日开关

        白皮书依据: 第十二章 12.3 末日开关与应急响应

        Args:
            reason: 触发原因
        """
        logger.critical(f"[DOOMSDAY] 🚨 TRIGGERED: {reason}")

        # 更新状态
        self.status.is_triggered = True
        self.status.trigger_time = datetime.now()
        self.status.trigger_reason = reason

        # 1. 创建锁文件
        self._create_lock_file(reason)

        # 2. Redis标记
        self._update_redis_status(reason)

        # 3. 停止所有交易
        self._stop_trading()

        # 4. 清仓（可选）
        if self._should_liquidate():
            self._emergency_liquidate()

        # 5. 通知
        self._send_alert(reason)

    def reset(self, password: str) -> bool:
        """人工复位（需要密码）

        白皮书依据: 第十二章 12.3 末日开关与应急响应

        Args:
            password: 复位密码

        Returns:
            复位是否成功
        """
        # 验证密码
        correct_password = self._get_reset_password()
        if password != correct_password:
            logger.error("[DOOMSDAY] Invalid reset password")
            return False

        # 删除锁文件
        if self._lock_file.exists():
            self._lock_file.unlink()
            logger.info(f"[DOOMSDAY] Lock file removed: {self._lock_file}")

        # 清除Redis标记
        if self.redis is not None:
            try:
                self.redis.delete(self.REDIS_KEY_DOOMSDAY)
                self.redis.set(self.REDIS_KEY_REDIS_FAILURES, 0)
                self.redis.set(self.REDIS_KEY_GPU_FAILURES, 0)
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.warning(f"[DOOMSDAY] Failed to clear Redis: {e}")

        # 更新状态
        self.status.is_triggered = False
        self.status.trigger_time = None
        self.status.trigger_reason = None
        self.status.triggers_fired = []

        logger.info("[DOOMSDAY] Reset successful")
        return True

    def is_triggered(self) -> bool:
        """检查是否已触发

        Returns:
            是否已触发
        """
        return self.status.is_triggered or self._lock_file.exists()

    def get_status(self) -> DoomsdayStatus:
        """获取当前状态

        Returns:
            当前状态
        """
        return self.status

    def _get_redis_failures(self) -> int:
        """获取Redis失败次数（内部方法）

        Returns:
            Redis连续失败次数
        """
        if self.redis is None:
            return 0

        try:
            value = self.redis.get(self.REDIS_KEY_REDIS_FAILURES)
            return int(value) if value else 0
        except Exception:  # pylint: disable=broad-exception-caught
            return 0

    def _get_gpu_failures(self) -> int:
        """获取GPU失败次数（内部方法）

        Returns:
            GPU连续失败次数
        """
        if self.redis is None:
            return 0

        try:
            value = self.redis.get(self.REDIS_KEY_GPU_FAILURES)
            return int(value) if value else 0
        except Exception:  # pylint: disable=broad-exception-caught
            return 0

    def _get_memory_percent(self) -> float:
        """获取内存使用率（内部方法）

        Returns:
            内存使用率（0-1）
        """
        if not PSUTIL_AVAILABLE:
            return 0.0

        try:
            return psutil.virtual_memory().percent / 100
        except Exception:  # pylint: disable=broad-exception-caught
            return 0.0

    def _get_disk_percent(self) -> float:
        """获取磁盘使用率（内部方法）

        Returns:
            磁盘使用率（0-1）
        """
        if not PSUTIL_AVAILABLE:
            return 0.0

        try:
            return psutil.disk_usage(self.config.disk_path).percent / 100
        except Exception:  # pylint: disable=broad-exception-caught
            return 0.0

    def _get_pnl_ratio(self) -> float:
        """获取盈亏比率（内部方法）

        Returns:
            盈亏比率
        """
        if self.redis is None:
            return 0.0

        try:
            daily_pnl = float(self.redis.get(self.REDIS_KEY_DAILY_PNL) or 0)
            initial_capital = float(self.redis.get(self.REDIS_KEY_INITIAL_CAPITAL) or 1000000)
            return daily_pnl / initial_capital if initial_capital > 0 else 0.0
        except Exception:  # pylint: disable=broad-exception-caught
            return 0.0

    def _get_reset_password(self) -> Optional[str]:
        """获取复位密码（内部方法）

        Returns:
            复位密码
        """
        if self.redis is None:
            return None

        try:
            value = self.redis.get(self.REDIS_KEY_RESET_PASSWORD)
            return value.decode() if isinstance(value, bytes) else value
        except Exception:  # pylint: disable=broad-exception-caught
            return None

    def _create_lock_file(self, reason: str) -> None:
        """创建锁文件（内部方法）

        Args:
            reason: 触发原因
        """
        try:
            # 确保目录存在
            self._lock_file.parent.mkdir(parents=True, exist_ok=True)

            # 创建锁文件
            with open(self._lock_file, "w") as f:  # pylint: disable=w1514
                f.write(f"Triggered at: {datetime.now().isoformat()}\n")
                f.write(f"Reason: {reason}\n")

            logger.info(f"[DOOMSDAY] Lock file created: {self._lock_file}")

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"[DOOMSDAY] Failed to create lock file: {e}")

    def _update_redis_status(self, reason: str) -> None:
        """更新Redis状态（内部方法）

        Args:
            reason: 触发原因
        """
        if self.redis is None:
            return

        try:
            self.redis.set(self.REDIS_KEY_DOOMSDAY, "triggered")
            self.redis.set(self.REDIS_KEY_DOOMSDAY_REASON, reason)
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.warning(f"[DOOMSDAY] Failed to update Redis: {e}")

    def _stop_trading(self) -> None:
        """停止所有交易（内部方法）

        白皮书依据: 第十二章 12.3 末日开关与应急响应
        """
        if self.redis is None:
            return

        try:
            self.redis.publish("trading:emergency_stop", "doomsday")
            logger.info("[DOOMSDAY] Trading stop signal sent")
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.warning(f"[DOOMSDAY] Failed to send stop signal: {e}")

    def _should_liquidate(self) -> bool:
        """判断是否需要清仓（内部方法）

        白皮书依据: 第十二章 12.3 末日开关与应急响应

        Returns:
            是否需要清仓
        """
        # 仅在严重亏损时清仓（>15%）
        pnl_ratio = self._get_pnl_ratio()
        return pnl_ratio < -0.15

    def _emergency_liquidate(self) -> None:
        """紧急清仓（内部方法）

        白皮书依据: 第十二章 12.3 末日开关与应急响应
        """
        logger.critical("[DOOMSDAY] 🚨 Emergency liquidation")

        if self.redis is None:
            return

        try:
            self.redis.publish("trading:liquidate_all", "emergency")
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"[DOOMSDAY] Failed to send liquidation signal: {e}")

    def _send_alert(self, reason: str) -> None:
        """发送告警（内部方法）

        Args:
            reason: 触发原因
        """
        # 这里可以集成企业微信等告警渠道
        logger.critical(f"[DOOMSDAY] 🚨 末日开关触发\n" f"原因: {reason}\n" f"时间: {datetime.now().isoformat()}")
