"""路径管理器 - 双盘物理隔离

白皮书依据: 第三章 3.1 双盘物理隔离

功能:
- 跨平台路径管理（Windows/Linux/Mac）
- C盘只读保护（Windows）
- D盘数据路由（Windows）
- 自动检测操作系统和磁盘配置

Author: MIA Team
Date: 2026-01-22
"""

import platform
from pathlib import Path
from typing import Any, Dict, Optional

from loguru import logger


class PathManager:
    """路径管理器

    白皮书依据: 第三章 3.1 双盘物理隔离

    实现跨平台的路径管理，确保：
    1. Windows: C盘只读，D盘读写
    2. Linux/Mac: /data目录读写
    3. 自动检测操作系统
    4. 统一的路径访问接口

    Attributes:
        os_type: 操作系统类型（Windows/Linux/Darwin）
        system_drive: 系统盘路径（Windows: C:/, Linux/Mac: /）
        data_drive: 数据盘路径（Windows: D:/, Linux/Mac: /data）
        readonly_enabled: 是否启用只读保护
    """

    def __init__(self, readonly_enabled: bool = True):
        """初始化路径管理器

        Args:
            readonly_enabled: 是否启用只读保护，默认True
        """
        self.os_type = platform.system()
        self.readonly_enabled = readonly_enabled

        # 检测磁盘配置
        self._detect_disk_configuration()

        logger.info(
            f"PathManager初始化完成 - "
            f"OS: {self.os_type}, "
            f"System: {self.system_drive}, "
            f"Data: {self.data_drive}, "
            f"ReadOnly: {self.readonly_enabled}"
        )

    def _detect_disk_configuration(self) -> None:
        """检测磁盘配置

        白皮书依据: 第三章 3.1 双盘物理隔离
        """
        if self.os_type == "Windows":
            # Windows: C盘系统，D盘数据
            self.system_drive = Path("C:/")
            self.data_drive = Path("D:/")

            # 检查D盘是否存在
            if not self.data_drive.exists():
                logger.warning("D盘不存在，使用C:/mia_data作为数据目录")
                self.data_drive = Path("C:/mia_data")
                self.data_drive.mkdir(parents=True, exist_ok=True)

        elif self.os_type in ["Linux", "Darwin"]:
            # Linux/Mac: / 系统，/data 数据
            self.system_drive = Path("/")
            self.data_drive = Path("/data")

            # 检查/data是否存在
            if not self.data_drive.exists():
                logger.warning("/data不存在，使用~/mia_data作为数据目录")
                self.data_drive = Path.home() / "mia_data"
                self.data_drive.mkdir(parents=True, exist_ok=True)

        else:
            raise RuntimeError(f"不支持的操作系统: {self.os_type}")

    def get_data_path(self, subdir: str = "") -> Path:
        """获取数据目录路径

        白皮书依据: 第三章 3.1 双盘物理隔离 - D盘数据存储

        Args:
            subdir: 子目录名称，如 "tick", "bar", "logs"

        Returns:
            数据目录的完整路径

        Example:
            >>> pm = PathManager()
            >>> pm.get_data_path("tick")
            WindowsPath('D:/mia/data/tick')
        """
        if subdir:
            path = self.data_drive / "mia" / "data" / subdir
        else:
            path = self.data_drive / "mia" / "data"

        # 确保目录存在
        path.mkdir(parents=True, exist_ok=True)

        return path

    def get_log_path(self, subdir: str = "") -> Path:
        """获取日志目录路径

        白皮书依据: 第三章 3.1 双盘物理隔离 - D盘日志存储

        Args:
            subdir: 子目录名称，如 "system", "trading", "audit"

        Returns:
            日志目录的完整路径
        """
        if subdir:
            path = self.data_drive / "mia" / "logs" / subdir
        else:
            path = self.data_drive / "mia" / "logs"

        path.mkdir(parents=True, exist_ok=True)
        return path

    def get_temp_path(self, subdir: str = "") -> Path:
        """获取临时文件目录路径

        白皮书依据: 第三章 3.1 双盘物理隔离 - D盘临时文件

        Args:
            subdir: 子目录名称

        Returns:
            临时目录的完整路径
        """
        if subdir:
            path = self.data_drive / "mia" / "temp" / subdir
        else:
            path = self.data_drive / "mia" / "temp"

        path.mkdir(parents=True, exist_ok=True)
        return path

    def get_docker_root(self) -> Path:
        """获取Docker根目录路径

        白皮书依据: 第三章 3.1 双盘物理隔离 - D盘Docker Root

        Returns:
            Docker根目录的完整路径
        """
        path = self.data_drive / "mia" / "docker"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def check_readonly_compliance(self, file_path: str) -> None:
        """检查只读合规性

        白皮书依据: 第三章 3.1 双盘物理隔离 - C盘只读保护

        检查文件路径是否尝试写入系统盘（C盘），如果是则抛出异常。

        Args:
            file_path: 要检查的文件路径

        Raises:
            PermissionError: 当尝试写入系统盘时

        Example:
            >>> pm = PathManager()
            >>> pm.check_readonly_compliance("C:/test.txt")
            PermissionError: 禁止写入系统盘: C:/test.txt
        """
        if not self.readonly_enabled:
            return

        # 使用字符串比较，避免跨平台路径解析问题
        path_str = str(file_path).replace("\\", "/")

        # Windows: 检查是否在C盘
        if self.os_type == "Windows":
            if path_str.upper().startswith("C:/") or path_str.upper().startswith("C:\\"):
                error_msg = f"禁止写入系统盘: {file_path}"
                logger.error(error_msg)
                raise PermissionError(error_msg)

        # Linux/Mac: 检查是否在系统关键目录
        elif self.os_type in ["Linux", "Darwin"]:
            system_dirs = ["/bin", "/sbin", "/usr", "/etc", "/boot"]
            for sys_dir in system_dirs:
                if path_str.startswith(sys_dir):
                    error_msg = f"禁止写入系统目录: {file_path}"
                    logger.error(error_msg)
                    raise PermissionError(error_msg)

    def get_config(self) -> Dict[str, Any]:
        """获取路径管理器配置信息

        Returns:
            配置信息字典
        """
        return {
            "os_type": self.os_type,
            "system_drive": str(self.system_drive),
            "data_drive": str(self.data_drive),
            "readonly_enabled": self.readonly_enabled,
            "data_path": str(self.get_data_path()),
            "log_path": str(self.get_log_path()),
            "temp_path": str(self.get_temp_path()),
            "docker_root": str(self.get_docker_root()),
        }


# 全局单例
_path_manager: Optional[PathManager] = None


def get_path_manager(readonly_enabled: bool = True) -> PathManager:
    """获取PathManager全局单例

    Args:
        readonly_enabled: 是否启用只读保护

    Returns:
        PathManager实例
    """
    global _path_manager  # pylint: disable=w0603

    if _path_manager is None:
        _path_manager = PathManager(readonly_enabled=readonly_enabled)

    return _path_manager
