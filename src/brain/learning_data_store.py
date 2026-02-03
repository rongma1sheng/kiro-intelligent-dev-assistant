"""学习数据存储

白皮书依据: 第二章 2.2.4 风险控制元学习架构 - 数据管理

核心功能：
1. 保存学习数据点（JSONL格式）
2. 加载历史数据
3. 数据归档和压缩
4. 数据清理和保留策略

数据格式：
- 使用JSONL（JSON Lines）格式，每行一个JSON对象
- 支持增量写入，不需要加载整个文件
- 支持gzip压缩，节省存储空间

Author: MIA Team
Date: 2026-01-22
Version: v1.0
"""

import gzip
import json
from dataclasses import asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger

from src.brain.risk_control_meta_learner import LearningDataPoint


class LearningDataStore:
    """学习数据存储

    白皮书依据: 第二章 2.2.4 风险控制元学习架构 - 数据管理

    核心职责：
    1. 保存学习数据点到JSONL文件
    2. 加载历史学习数据
    3. 数据归档和压缩（gzip）
    4. 数据清理和保留策略（默认365天）
    5. 数据统计和查询

    数据存储结构：
    ```
    data/learning/
    ├── risk_control_learning_2026-01.jsonl      # 当前月份数据
    ├── risk_control_learning_2025-12.jsonl.gz   # 历史数据（压缩）
    ├── risk_control_learning_2025-11.jsonl.gz
    └── ...
    ```

    Attributes:
        data_dir: 数据存储目录
        retention_days: 数据保留天数（默认365天）
        current_file: 当前写入的文件路径
        stats: 数据统计信息
    """

    def __init__(self, data_dir: str = "data/learning", retention_days: int = 365):
        """初始化学习数据存储

        白皮书依据: 第二章 2.2.4 风险控制元学习架构

        Args:
            data_dir: 数据存储目录（默认data/learning）
            retention_days: 数据保留天数（默认365天）

        Raises:
            ValueError: 当retention_days <= 0时
        """
        if retention_days <= 0:
            raise ValueError(f"retention_days必须 > 0，当前: {retention_days}")

        self.data_dir = Path(data_dir)
        self.retention_days = retention_days

        # 创建数据目录
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # 当前写入的文件
        self.current_file = self._get_current_file_path()

        # 统计信息
        self.stats = {"total_saved": 0, "total_loaded": 0, "total_archived": 0, "total_deleted": 0}

        logger.info(f"[LearningDataStore] 初始化完成 - " f"数据目录: {self.data_dir}, " f"保留天数: {retention_days}")

    def _get_current_file_path(self) -> Path:
        """获取当前文件路径

        文件命名格式：risk_control_learning_YYYY-MM.jsonl

        Returns:
            Path: 当前文件路径
        """
        current_month = datetime.now().strftime("%Y-%m")
        filename = f"risk_control_learning_{current_month}.jsonl"
        return self.data_dir / filename

    def save_data_point(self, data_point: LearningDataPoint) -> bool:
        """保存学习数据点

        白皮书依据: 第二章 2.2.4 风险控制元学习架构

        数据格式：JSONL（每行一个JSON对象）

        Args:
            data_point: 学习数据点

        Returns:
            bool: 是否保存成功

        Example:
            >>> store = LearningDataStore()
            >>> data_point = LearningDataPoint(...)
            >>> success = store.save_data_point(data_point)
            >>> print(f"保存成功: {success}")
        """
        try:
            # 检查是否需要切换文件（新月份）
            current_file = self._get_current_file_path()
            if current_file != self.current_file:
                # 归档旧文件
                self._archive_file(self.current_file)
                self.current_file = current_file

            # 转换为字典
            data_dict = self._data_point_to_dict(data_point)

            # 追加写入JSONL文件
            with open(self.current_file, "a", encoding="utf-8") as f:
                json.dump(data_dict, f, ensure_ascii=False)
                f.write("\n")

            self.stats["total_saved"] += 1

            logger.debug(f"[LearningDataStore] 数据点已保存 - " f"文件: {self.current_file.name}")

            return True

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"[LearningDataStore] 保存数据点失败: {e}")
            return False

    def _data_point_to_dict(self, data_point: LearningDataPoint) -> Dict[str, Any]:
        """将数据点转换为字典

        Args:
            data_point: 学习数据点

        Returns:
            Dict[str, Any]: 字典表示
        """
        return {
            "timestamp": data_point.timestamp,
            "market_context": asdict(data_point.market_context),
            "architecture_a_performance": asdict(data_point.architecture_a_performance),
            "architecture_b_performance": asdict(data_point.architecture_b_performance),
            "winner": data_point.winner,
            "metadata": data_point.metadata,
        }

    def load_historical_data(
        self, start_date: Optional[str] = None, end_date: Optional[str] = None, max_samples: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """加载历史学习数据

        白皮书依据: 第二章 2.2.4 风险控制元学习架构

        Args:
            start_date: 开始日期（格式：YYYY-MM-DD，可选）
            end_date: 结束日期（格式：YYYY-MM-DD，可选）
            max_samples: 最大样本数（可选）

        Returns:
            List[Dict[str, Any]]: 历史数据列表

        Example:
            >>> store = LearningDataStore()
            >>> data = store.load_historical_data(
            ...     start_date='2026-01-01',
            ...     end_date='2026-01-31',
            ...     max_samples=1000
            ... )
            >>> print(f"加载了 {len(data)} 个样本")
        """
        try:
            # 获取所有数据文件
            data_files = self._get_data_files(start_date, end_date)

            # 加载数据
            all_data = []

            for file_path in data_files:
                # 判断是否为压缩文件
                if file_path.suffix == ".gz":
                    data = self._load_compressed_file(file_path)
                else:
                    data = self._load_jsonl_file(file_path)

                all_data.extend(data)

                # 检查是否达到最大样本数
                if max_samples and len(all_data) >= max_samples:
                    all_data = all_data[:max_samples]
                    break

            self.stats["total_loaded"] += len(all_data)

            logger.info(
                f"[LearningDataStore] 历史数据加载完成 - " f"样本数: {len(all_data)}, " f"文件数: {len(data_files)}"
            )

            return all_data

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"[LearningDataStore] 加载历史数据失败: {e}")
            return []

    def _get_data_files(self, start_date: Optional[str] = None, end_date: Optional[str] = None) -> List[Path]:
        """获取数据文件列表

        Args:
            start_date: 开始日期（可选）
            end_date: 结束日期（可选）

        Returns:
            List[Path]: 数据文件路径列表（按时间排序）
        """
        # 获取所有JSONL和JSONL.GZ文件
        jsonl_files = list(self.data_dir.glob("risk_control_learning_*.jsonl"))
        gz_files = list(self.data_dir.glob("risk_control_learning_*.jsonl.gz"))

        all_files = jsonl_files + gz_files

        # 过滤日期范围
        if start_date or end_date:
            filtered_files = []
            for file_path in all_files:
                file_date = self._extract_date_from_filename(file_path.name)
                if file_date:
                    if start_date and file_date < start_date:
                        continue
                    if end_date and file_date > end_date:
                        continue
                    filtered_files.append(file_path)
            all_files = filtered_files

        # 按文件名排序（时间顺序）
        all_files.sort()

        return all_files

    def _extract_date_from_filename(self, filename: str) -> Optional[str]:
        """从文件名提取日期

        文件名格式：risk_control_learning_YYYY-MM.jsonl[.gz]

        Args:
            filename: 文件名

        Returns:
            Optional[str]: 日期字符串（YYYY-MM）
        """
        try:
            # 检查文件名格式
            if not filename.startswith("risk_control_learning_"):
                return None

            # 移除扩展名
            name = filename.replace(".jsonl.gz", "").replace(".jsonl", "")
            # 提取日期部分
            date_str = name.split("_")[-1]

            # 验证日期格式（YYYY-MM）
            if len(date_str) == 7 and date_str[4] == "-":  # pylint: disable=no-else-return
                return date_str
            else:
                return None
        except Exception:  # pylint: disable=broad-exception-caught
            return None

    def _load_jsonl_file(self, file_path: Path) -> List[Dict[str, Any]]:
        """加载JSONL文件

        Args:
            file_path: 文件路径

        Returns:
            List[Dict[str, Any]]: 数据列表
        """
        data = []

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        data.append(json.loads(line))
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.warning(f"[LearningDataStore] 加载文件失败: {file_path}, 错误: {e}")

        return data

    def _load_compressed_file(self, file_path: Path) -> List[Dict[str, Any]]:
        """加载压缩文件

        Args:
            file_path: 文件路径

        Returns:
            List[Dict[str, Any]]: 数据列表
        """
        data = []

        try:
            with gzip.open(file_path, "rt", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        data.append(json.loads(line))
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.warning(f"[LearningDataStore] 加载压缩文件失败: {file_path}, 错误: {e}")

        return data

    def _archive_file(self, file_path: Path) -> bool:
        """归档文件（压缩）

        白皮书依据: 第二章 2.2.4 风险控制元学习架构 - 数据归档

        Args:
            file_path: 文件路径

        Returns:
            bool: 是否归档成功
        """
        if not file_path.exists():
            return False

        try:
            # 压缩文件
            compressed_path = file_path.with_suffix(".jsonl.gz")

            with open(file_path, "rb") as f_in:
                with gzip.open(compressed_path, "wb") as f_out:
                    f_out.writelines(f_in)

            # 删除原文件
            file_path.unlink()

            self.stats["total_archived"] += 1

            logger.info(
                f"[LearningDataStore] 文件已归档 - " f"原文件: {file_path.name}, " f"压缩文件: {compressed_path.name}"
            )

            return True

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"[LearningDataStore] 归档文件失败: {file_path}, 错误: {e}")
            return False

    def cleanup_old_data(self) -> int:
        """清理过期数据

        白皮书依据: 第二章 2.2.4 风险控制元学习架构 - 数据清理

        删除超过保留期限的数据文件。

        Returns:
            int: 删除的文件数量

        Example:
            >>> store = LearningDataStore(retention_days=365)
            >>> deleted_count = store.cleanup_old_data()
            >>> print(f"删除了 {deleted_count} 个过期文件")
        """
        try:
            # 计算截止日期
            cutoff_date = datetime.now() - timedelta(days=self.retention_days)
            cutoff_str = cutoff_date.strftime("%Y-%m")

            # 获取所有数据文件
            all_files = self._get_data_files()

            # 删除过期文件
            deleted_count = 0

            for file_path in all_files:
                file_date = self._extract_date_from_filename(file_path.name)

                if file_date and file_date < cutoff_str:
                    try:
                        file_path.unlink()
                        deleted_count += 1
                        self.stats["total_deleted"] += 1

                        logger.info(
                            f"[LearningDataStore] 删除过期文件 - " f"文件: {file_path.name}, " f"日期: {file_date}"
                        )
                    except Exception as e:  # pylint: disable=broad-exception-caught
                        logger.warning(f"[LearningDataStore] 删除文件失败: {file_path}, 错误: {e}")

            logger.info(
                f"[LearningDataStore] 数据清理完成 - " f"删除文件数: {deleted_count}, " f"截止日期: {cutoff_str}"
            )

            return deleted_count

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"[LearningDataStore] 数据清理失败: {e}")
            return 0

    def get_statistics(self) -> Dict[str, Any]:
        """获取数据统计信息

        Returns:
            Dict[str, Any]: 统计信息
        """
        # 统计文件数量和大小
        all_files = self._get_data_files()

        total_size = 0
        file_count = 0
        compressed_count = 0

        for file_path in all_files:
            if file_path.exists():
                total_size += file_path.stat().st_size
                file_count += 1
                if file_path.suffix == ".gz":
                    compressed_count += 1

        return {
            "total_saved": self.stats["total_saved"],
            "total_loaded": self.stats["total_loaded"],
            "total_archived": self.stats["total_archived"],
            "total_deleted": self.stats["total_deleted"],
            "file_count": file_count,
            "compressed_count": compressed_count,
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "data_dir": str(self.data_dir),
            "retention_days": self.retention_days,
            "current_file": str(self.current_file),
            "timestamp": datetime.now().isoformat(),
        }

    def __repr__(self) -> str:
        """字符串表示"""
        return (
            f"LearningDataStore("
            f"data_dir={self.data_dir}, "
            f"retention_days={self.retention_days}, "
            f"total_saved={self.stats['total_saved']})"
        )
