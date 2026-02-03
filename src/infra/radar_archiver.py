"""
雷达信号归档器 (Radar Archiver)

白皮书依据: 第一章 1.5.3 诊疗态任务调度
- 雷达信号归档
- 信号历史存储
- 信号回溯查询

功能:
- 归档雷达扫描信号
- 存储信号历史
- 支持信号回溯分析
"""

import asyncio
import json
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger

try:
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False

try:
    HAS_PARQUET = True
except ImportError:
    HAS_PARQUET = False


class SignalType(Enum):
    """信号类型"""

    BUY = "买入"
    SELL = "卖出"
    HOLD = "持有"
    ALERT = "预警"
    RISK = "风险"


class SignalSource(Enum):
    """信号来源"""

    FACTOR = "因子"
    STRATEGY = "策略"
    RISK_CONTROL = "风控"
    SENTIMENT = "舆情"
    TECHNICAL = "技术"


@dataclass
class RadarSignal:
    """雷达信号

    Attributes:
        signal_id: 信号ID
        symbol: 标的代码
        signal_type: 信号类型
        source: 信号来源
        strength: 信号强度 (0-1)
        confidence: 置信度 (0-1)
        reason: 信号原因
        metadata: 元数据
        timestamp: 时间戳
    """

    signal_id: str
    symbol: str
    signal_type: SignalType
    source: SignalSource
    strength: float = 0.5
    confidence: float = 0.5
    reason: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "signal_id": self.signal_id,
            "symbol": self.symbol,
            "signal_type": self.signal_type.value,
            "source": self.source.value,
            "strength": self.strength,
            "confidence": self.confidence,
            "reason": self.reason,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RadarSignal":
        """从字典创建"""
        return cls(
            signal_id=data["signal_id"],
            symbol=data["symbol"],
            signal_type=SignalType(data["signal_type"]),
            source=SignalSource(data["source"]),
            strength=data.get("strength", 0.5),
            confidence=data.get("confidence", 0.5),
            reason=data.get("reason", ""),
            metadata=data.get("metadata", {}),
            timestamp=datetime.fromisoformat(data["timestamp"]),
        )


@dataclass
class ArchiveStats:
    """归档统计

    Attributes:
        total_signals: 总信号数
        signals_by_type: 各类型信号数
        signals_by_source: 各来源信号数
        date_range: 日期范围
        file_count: 文件数
        total_size_mb: 总大小(MB)
    """

    total_signals: int = 0
    signals_by_type: Dict[str, int] = field(default_factory=dict)
    signals_by_source: Dict[str, int] = field(default_factory=dict)
    date_range: Tuple[str, str] = ("", "")
    file_count: int = 0
    total_size_mb: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "total_signals": self.total_signals,
            "signals_by_type": self.signals_by_type,
            "signals_by_source": self.signals_by_source,
            "date_range": self.date_range,
            "file_count": self.file_count,
            "total_size_mb": self.total_size_mb,
        }


from typing import Tuple  # pylint: disable=w0404,c0413,c0411


class RadarArchiver:
    """雷达信号归档器

    白皮书依据: 第一章 1.5.3 诊疗态任务调度

    负责归档和管理雷达扫描信号。

    Attributes:
        archive_path: 归档路径
        retention_days: 保留天数

    Example:
        >>> archiver = RadarArchiver()
        >>> archiver.archive_signal(signal)
        >>> signals = archiver.query_signals(symbol="000001.SZ")
    """

    def __init__(self, archive_path: str = "data/radar_archive", retention_days: int = 90):
        """初始化雷达归档器

        Args:
            archive_path: 归档路径
            retention_days: 保留天数
        """
        self.archive_path = Path(archive_path)
        self.retention_days = retention_days

        # 确保目录存在
        self.archive_path.mkdir(parents=True, exist_ok=True)

        # 内存缓存 (当日信号)
        self._today_signals: List[RadarSignal] = []
        self._signal_count = 0

        logger.info(f"雷达归档器初始化: " f"路径={archive_path}, " f"保留天数={retention_days}")

    def archive_signal(self, signal: RadarSignal) -> bool:
        """归档单个信号

        Args:
            signal: 雷达信号

        Returns:
            是否成功
        """
        try:
            self._today_signals.append(signal)
            self._signal_count += 1

            logger.debug(f"归档信号: {signal.symbol} " f"{signal.signal_type.value} " f"from {signal.source.value}")

            return True

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"归档信号失败: {e}")
            return False

    def archive_signals(self, signals: List[RadarSignal]) -> int:
        """批量归档信号

        Args:
            signals: 信号列表

        Returns:
            成功归档数量
        """
        success_count = 0

        for signal in signals:
            if self.archive_signal(signal):
                success_count += 1

        return success_count

    def flush_to_disk(self) -> bool:
        """将缓存信号写入磁盘

        Returns:
            是否成功
        """
        if not self._today_signals:
            return True

        try:
            today_str = date.today().strftime("%Y%m%d")
            file_path = self.archive_path / f"signals_{today_str}.json"

            # 读取已有数据
            existing_signals = []
            if file_path.exists():
                with open(file_path, "r", encoding="utf-8") as f:
                    existing_signals = json.load(f)

            # 合并新数据
            all_signals = existing_signals + [s.to_dict() for s in self._today_signals]

            # 写入文件
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(all_signals, f, ensure_ascii=False, indent=2)

            logger.info(f"信号已写入磁盘: {file_path}, 数量={len(self._today_signals)}")

            # 清空缓存
            self._today_signals.clear()

            return True

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"写入磁盘失败: {e}")
            return False

    def query_signals(  # pylint: disable=too-many-positional-arguments
        self,
        symbol: Optional[str] = None,
        signal_type: Optional[SignalType] = None,
        source: Optional[SignalSource] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        limit: int = 100,
    ) -> List[RadarSignal]:
        """查询信号

        Args:
            symbol: 标的代码
            signal_type: 信号类型
            source: 信号来源
            start_date: 开始日期
            end_date: 结束日期
            limit: 返回数量限制

        Returns:
            信号列表
        """
        results = []

        # 先查询内存缓存
        for signal in self._today_signals:
            if self._match_signal(signal, symbol, signal_type, source):
                results.append(signal)

        # 再查询磁盘文件
        if start_date is None:
            start_date = date.today() - timedelta(days=7)
        if end_date is None:
            end_date = date.today()

        current_date = start_date
        while current_date <= end_date and len(results) < limit:  # pylint: disable=r1702
            date_str = current_date.strftime("%Y%m%d")
            file_path = self.archive_path / f"signals_{date_str}.json"

            if file_path.exists():
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        signals_data = json.load(f)

                    for data in signals_data:
                        signal = RadarSignal.from_dict(data)
                        if self._match_signal(signal, symbol, signal_type, source):
                            results.append(signal)
                            if len(results) >= limit:
                                break

                except Exception as e:  # pylint: disable=broad-exception-caught
                    logger.warning(f"读取{file_path}失败: {e}")

            current_date += timedelta(days=1)

        return results[:limit]

    def _match_signal(
        self,
        signal: RadarSignal,
        symbol: Optional[str],
        signal_type: Optional[SignalType],
        source: Optional[SignalSource],
    ) -> bool:
        """检查信号是否匹配条件"""
        if symbol and signal.symbol != symbol:
            return False
        if signal_type and signal.signal_type != signal_type:
            return False
        if source and signal.source != source:
            return False
        return True

    def get_today_signals(self) -> List[RadarSignal]:
        """获取今日信号

        Returns:
            今日信号列表
        """
        return self._today_signals.copy()

    def get_signal_count(self, symbol: Optional[str] = None, days: int = 1) -> int:
        """获取信号数量

        Args:
            symbol: 标的代码
            days: 天数

        Returns:
            信号数量
        """
        signals = self.query_signals(symbol=symbol, start_date=date.today() - timedelta(days=days), limit=10000)
        return len(signals)

    def get_statistics(self) -> ArchiveStats:
        """获取归档统计

        Returns:
            统计信息
        """
        stats = ArchiveStats()

        # 统计文件
        files = list(self.archive_path.glob("signals_*.json"))
        stats.file_count = len(files)
        stats.total_size_mb = sum(f.stat().st_size for f in files) / (1024 * 1024)

        # 统计信号
        signals_by_type: Dict[str, int] = {}
        signals_by_source: Dict[str, int] = {}
        total_signals = 0
        min_date = None
        max_date = None

        for file_path in files:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    signals_data = json.load(f)

                total_signals += len(signals_data)

                for data in signals_data:
                    signal_type = data.get("signal_type", "未知")
                    source = data.get("source", "未知")

                    signals_by_type[signal_type] = signals_by_type.get(signal_type, 0) + 1
                    signals_by_source[source] = signals_by_source.get(source, 0) + 1

                    # 更新日期范围
                    timestamp = data.get("timestamp", "")
                    if timestamp:
                        signal_date = timestamp[:10]
                        if min_date is None or signal_date < min_date:
                            min_date = signal_date
                        if max_date is None or signal_date > max_date:
                            max_date = signal_date

            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.warning(f"读取{file_path}统计失败: {e}")

        # 加上内存中的信号
        total_signals += len(self._today_signals)
        for signal in self._today_signals:
            signals_by_type[signal.signal_type.value] = signals_by_type.get(signal.signal_type.value, 0) + 1
            signals_by_source[signal.source.value] = signals_by_source.get(signal.source.value, 0) + 1

        stats.total_signals = total_signals
        stats.signals_by_type = signals_by_type
        stats.signals_by_source = signals_by_source
        stats.date_range = (min_date or "", max_date or "")

        return stats

    def cleanup_old_files(self) -> int:
        """清理过期文件

        Returns:
            删除的文件数
        """
        cutoff_date = date.today() - timedelta(days=self.retention_days)
        deleted_count = 0

        for file_path in self.archive_path.glob("signals_*.json"):
            try:
                # 从文件名提取日期
                date_str = file_path.stem.replace("signals_", "")
                file_date = datetime.strptime(date_str, "%Y%m%d").date()

                if file_date < cutoff_date:
                    file_path.unlink()
                    deleted_count += 1
                    logger.info(f"删除过期文件: {file_path}")

            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.warning(f"处理{file_path}失败: {e}")

        return deleted_count

    def clear_cache(self) -> None:
        """清空内存缓存"""
        self._today_signals.clear()
        logger.info("雷达信号缓存已清空")

    async def flush_to_disk_async(self) -> bool:
        """异步写入磁盘

        Returns:
            是否成功
        """
        return await asyncio.to_thread(self.flush_to_disk)

    async def query_signals_async(self, **kwargs) -> List[RadarSignal]:
        """异步查询信号

        Returns:
            信号列表
        """
        return await asyncio.to_thread(self.query_signals, **kwargs)
