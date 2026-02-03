"""
数据归档器 (Data Archiver)

白皮书依据: 第一章 1.5.3 诊疗态任务调度
- Tick数据转Parquet
- Bar数据转Parquet
- 雷达信号归档

功能:
- 将日内数据归档为Parquet格式
- 压缩存储历史数据
- 支持增量归档
"""

from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, Optional

from loguru import logger

try:
    import pandas as pd

    HAS_PARQUET = True
except ImportError:
    HAS_PARQUET = False
    logger.warning("pyarrow未安装，Parquet功能不可用")


@dataclass
class ArchiveConfig:
    """归档配置

    Attributes:
        base_path: 基础存储路径
        tick_subdir: Tick数据子目录
        bar_subdir: Bar数据子目录
        radar_subdir: 雷达信号子目录
        compression: 压缩算法
        partition_by_date: 是否按日期分区
    """

    base_path: str = "data"
    tick_subdir: str = "tick"
    bar_subdir: str = "bar"
    radar_subdir: str = "radar_archive"
    compression: str = "snappy"
    partition_by_date: bool = True


@dataclass
class ArchiveResult:
    """归档结果

    Attributes:
        success: 是否成功
        file_path: 归档文件路径
        record_count: 记录数
        file_size: 文件大小(字节)
        duration: 耗时(秒)
        error: 错误信息
    """

    success: bool
    file_path: str = ""
    record_count: int = 0
    file_size: int = 0
    duration: float = 0.0
    error: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "success": self.success,
            "file_path": self.file_path,
            "record_count": self.record_count,
            "file_size": self.file_size,
            "duration": self.duration,
            "error": self.error,
        }


class DataArchiver:
    """数据归档器

    白皮书依据: 第一章 1.5.3 诊疗态任务调度

    负责将日内交易数据归档为Parquet格式存储。

    Attributes:
        config: 归档配置
        archive_date: 归档日期

    Example:
        >>> archiver = DataArchiver()
        >>> result = archiver.archive_tick_data(tick_df)
        >>> print(f"归档{result.record_count}条记录")
    """

    def __init__(self, config: Optional[ArchiveConfig] = None):
        """初始化数据归档器

        Args:
            config: 归档配置
        """
        self.config = config or ArchiveConfig()
        self.archive_date = date.today()

        # 创建目录
        self._ensure_directories()

        logger.info(f"数据归档器初始化: 基础路径={self.config.base_path}")

    def _ensure_directories(self) -> None:
        """确保目录存在"""
        base = Path(self.config.base_path)

        for subdir in [self.config.tick_subdir, self.config.bar_subdir, self.config.radar_subdir]:
            path = base / subdir
            path.mkdir(parents=True, exist_ok=True)

    def _get_archive_path(self, data_type: str, symbol: Optional[str] = None) -> Path:
        """获取归档路径

        Args:
            data_type: 数据类型 (tick/bar/radar)
            symbol: 标的代码

        Returns:
            归档文件路径
        """
        base = Path(self.config.base_path)

        if data_type == "tick":
            subdir = self.config.tick_subdir
        elif data_type == "bar":
            subdir = self.config.bar_subdir
        elif data_type == "radar":
            subdir = self.config.radar_subdir
        else:
            subdir = data_type

        if self.config.partition_by_date:
            date_str = self.archive_date.strftime("%Y%m%d")
            if symbol:
                filename = f"{symbol}_{date_str}.parquet"
            else:
                filename = f"{data_type}_{date_str}.parquet"
        else:
            if symbol:
                filename = f"{symbol}.parquet"
            else:
                filename = f"{data_type}.parquet"

        return base / subdir / filename

    def archive_tick_data(self, data: Any, symbol: Optional[str] = None) -> ArchiveResult:
        """归档Tick数据

        白皮书依据: 第一章 1.5.3 Tick数据转Parquet

        Args:
            data: Tick数据 (DataFrame或字典列表)
            symbol: 标的代码

        Returns:
            归档结果
        """
        start_time = datetime.now()

        if not HAS_PARQUET:
            return ArchiveResult(success=False, error="pyarrow未安装")

        try:
            # 转换为DataFrame
            if isinstance(data, list):
                df = pd.DataFrame(data)
            elif isinstance(data, pd.DataFrame):
                df = data
            else:
                return ArchiveResult(success=False, error=f"不支持的数据类型: {type(data)}")

            if df.empty:
                return ArchiveResult(success=True, record_count=0)

            # 获取归档路径
            file_path = self._get_archive_path("tick", symbol)

            # 写入Parquet
            df.to_parquet(file_path, compression=self.config.compression, index=False)

            duration = (datetime.now() - start_time).total_seconds()
            file_size = file_path.stat().st_size

            logger.info(f"Tick数据归档完成: {file_path}, " f"记录数={len(df)}, 大小={file_size/1024:.1f}KB")

            return ArchiveResult(
                success=True, file_path=str(file_path), record_count=len(df), file_size=file_size, duration=duration
            )

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"Tick数据归档失败: {e}")
            return ArchiveResult(success=False, error=str(e))

    def archive_bar_data(
        self, data: Any, symbol: Optional[str] = None, timeframe: str = "1m"  # pylint: disable=unused-argument
    ) -> ArchiveResult:  # pylint: disable=unused-argument
        """归档Bar数据

        白皮书依据: 第一章 1.5.3 Bar数据转Parquet

        Args:
            data: Bar数据 (DataFrame或字典列表)
            symbol: 标的代码
            timeframe: 时间周期

        Returns:
            归档结果
        """
        start_time = datetime.now()

        if not HAS_PARQUET:
            return ArchiveResult(success=False, error="pyarrow未安装")

        try:
            # 转换为DataFrame
            if isinstance(data, list):
                df = pd.DataFrame(data)
            elif isinstance(data, pd.DataFrame):
                df = data
            else:
                return ArchiveResult(success=False, error=f"不支持的数据类型: {type(data)}")

            if df.empty:
                return ArchiveResult(success=True, record_count=0)

            # 获取归档路径
            file_path = self._get_archive_path("bar", symbol)

            # 写入Parquet
            df.to_parquet(file_path, compression=self.config.compression, index=False)

            duration = (datetime.now() - start_time).total_seconds()
            file_size = file_path.stat().st_size

            logger.info(f"Bar数据归档完成: {file_path}, " f"记录数={len(df)}, 大小={file_size/1024:.1f}KB")

            return ArchiveResult(
                success=True, file_path=str(file_path), record_count=len(df), file_size=file_size, duration=duration
            )

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"Bar数据归档失败: {e}")
            return ArchiveResult(success=False, error=str(e))

    def archive_radar_signals(self, signals: Any) -> ArchiveResult:
        """归档雷达信号

        白皮书依据: 第一章 1.5.3 雷达信号归档

        Args:
            signals: 雷达信号数据

        Returns:
            归档结果
        """
        start_time = datetime.now()

        if not HAS_PARQUET:
            return ArchiveResult(success=False, error="pyarrow未安装")

        try:
            # 转换为DataFrame
            if isinstance(signals, list):
                df = pd.DataFrame(signals)
            elif isinstance(signals, pd.DataFrame):
                df = signals
            elif isinstance(signals, dict):
                df = pd.DataFrame([signals])
            else:
                return ArchiveResult(success=False, error=f"不支持的数据类型: {type(signals)}")

            if df.empty:
                return ArchiveResult(success=True, record_count=0)

            # 获取归档路径
            file_path = self._get_archive_path("radar")

            # 写入Parquet
            df.to_parquet(file_path, compression=self.config.compression, index=False)

            duration = (datetime.now() - start_time).total_seconds()
            file_size = file_path.stat().st_size

            logger.info(f"雷达信号归档完成: {file_path}, " f"记录数={len(df)}, 大小={file_size/1024:.1f}KB")

            return ArchiveResult(
                success=True, file_path=str(file_path), record_count=len(df), file_size=file_size, duration=duration
            )

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"雷达信号归档失败: {e}")
            return ArchiveResult(success=False, error=str(e))

    def archive_all(
        self, tick_data: Optional[Any] = None, bar_data: Optional[Any] = None, radar_signals: Optional[Any] = None
    ) -> Dict[str, ArchiveResult]:
        """归档所有数据

        Args:
            tick_data: Tick数据
            bar_data: Bar数据
            radar_signals: 雷达信号

        Returns:
            各类型归档结果
        """
        results = {}

        if tick_data is not None:
            results["tick"] = self.archive_tick_data(tick_data)

        if bar_data is not None:
            results["bar"] = self.archive_bar_data(bar_data)

        if radar_signals is not None:
            results["radar"] = self.archive_radar_signals(radar_signals)

        return results

    def get_archive_stats(self) -> Dict[str, Any]:
        """获取归档统计

        Returns:
            统计信息
        """
        base = Path(self.config.base_path)
        stats = {"tick": {"count": 0, "size": 0}, "bar": {"count": 0, "size": 0}, "radar": {"count": 0, "size": 0}}

        for data_type, subdir in [
            ("tick", self.config.tick_subdir),
            ("bar", self.config.bar_subdir),
            ("radar", self.config.radar_subdir),
        ]:
            path = base / subdir
            if path.exists():
                files = list(path.glob("*.parquet"))
                stats[data_type]["count"] = len(files)
                stats[data_type]["size"] = sum(f.stat().st_size for f in files)

        return stats
