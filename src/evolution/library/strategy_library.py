"""Strategy Library - Main Storage and Retrieval System

白皮书依据: 第四章 4.4 策略库管理系统
"""

import json
from pathlib import Path
from typing import Dict, List, Optional

from loguru import logger

from src.evolution.library.data_models import (
    LifecycleState,
    MarketRegime,
    StrategyMetadata,
    StrategyRecord,
    StrategyType,
)
from src.evolution.library.lifecycle_manager import LifecycleManager
from src.evolution.library.strategy_query_engine import StrategyQueryEngine


class StrategyLibrary:
    """策略库

    白皮书依据: 第四章 4.4 策略库管理系统

    主要功能：
    1. 策略存储和检索
    2. 复杂查询
    3. 生命周期管理
    4. 性能监控
    """

    def __init__(self, storage_dir: str = "data/strategy_library"):
        """初始化策略库

        Args:
            storage_dir: 存储目录
        """
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        # 内存缓存
        self.strategies: Dict[str, StrategyRecord] = {}

        # 查询引擎和生命周期管理器
        self.query_engine = StrategyQueryEngine()
        self.lifecycle_manager = LifecycleManager()

        # 加载已有策略
        self._load_strategies()

        logger.info(
            f"StrategyLibrary初始化完成 - " f"存储目录: {self.storage_dir}, " f"已加载策略数: {len(self.strategies)}"
        )

    def add_strategy(self, record: StrategyRecord) -> bool:
        """添加策略到库

        白皮书依据: 第四章 4.4.7 策略注册

        Args:
            record: 策略记录

        Returns:
            是否添加成功
        """
        if not isinstance(record, StrategyRecord):
            logger.error(f"record类型错误: {type(record)}")
            return False

        strategy_id = record.metadata.strategy_id

        # 检查是否已存在
        if strategy_id in self.strategies:
            logger.warning(f"策略已存在: {strategy_id}，将覆盖")

        # 添加到内存
        self.strategies[strategy_id] = record

        # 持久化到文件系统
        success = self._save_strategy(record)

        if success:
            logger.info(
                f"策略已添加: {strategy_id}, "
                f"类型: {record.metadata.strategy_type.value}, "
                f"Z2H认证: {record.metadata.z2h_certified}"
            )

        return success

    def get_strategy(self, strategy_id: str) -> Optional[StrategyRecord]:
        """获取策略

        Args:
            strategy_id: 策略ID

        Returns:
            策略记录，如果不存在则返回None
        """
        return self.strategies.get(strategy_id)

    def remove_strategy(self, strategy_id: str) -> bool:
        """移除策略

        Args:
            strategy_id: 策略ID

        Returns:
            是否移除成功
        """
        if strategy_id not in self.strategies:
            logger.warning(f"策略不存在: {strategy_id}")
            return False

        # 从内存移除
        del self.strategies[strategy_id]

        # 从文件系统移除
        file_path = self._get_file_path(strategy_id)
        if file_path.exists():
            file_path.unlink()

        logger.info(f"策略已移除: {strategy_id}")
        return True

    def update_strategy_metadata(self, strategy_id: str, **kwargs) -> bool:
        """更新策略元数据

        Args:
            strategy_id: 策略ID
            **kwargs: 要更新的字段

        Returns:
            是否更新成功
        """
        record = self.get_strategy(strategy_id)
        if not record:
            logger.error(f"策略不存在: {strategy_id}")
            return False

        # 更新元数据
        for key, value in kwargs.items():
            if hasattr(record.metadata, key):
                setattr(record.metadata, key, value)
            else:
                logger.warning(f"未知的元数据字段: {key}")

        # 更新时间戳
        from datetime import datetime  # pylint: disable=import-outside-toplevel

        record.metadata.last_updated = datetime.now()

        # 持久化
        success = self._save_strategy(record)

        if success:
            logger.info(f"策略元数据已更新: {strategy_id}")

        return success

    def query_strategies(  # pylint: disable=too-many-positional-arguments
        self,
        z2h_only: bool = False,
        strategy_types: Optional[List[StrategyType]] = None,
        min_sharpe: Optional[float] = None,
        max_drawdown: Optional[float] = None,
        min_win_rate: Optional[float] = None,
        suitable_regimes: Optional[List[MarketRegime]] = None,
        lifecycle_states: Optional[List[LifecycleState]] = None,
    ) -> List[StrategyMetadata]:
        """查询策略

        白皮书依据: 第四章 4.4.6 策略查询

        Args:
            z2h_only: 是否只返回Z2H认证策略
            strategy_types: 策略类型列表
            min_sharpe: 最小夏普比率
            max_drawdown: 最大回撤上限
            min_win_rate: 最小胜率
            suitable_regimes: 适用市场状态列表
            lifecycle_states: 生命周期状态列表

        Returns:
            符合条件的策略元数据列表
        """
        # 获取所有策略的元数据
        all_metadata = [record.metadata for record in self.strategies.values()]

        # 使用查询引擎过滤
        results = self.query_engine.query(
            strategies=all_metadata,
            z2h_only=z2h_only,
            strategy_types=strategy_types,
            min_sharpe=min_sharpe,
            max_drawdown=max_drawdown,
            min_win_rate=min_win_rate,
            suitable_regimes=suitable_regimes,
            lifecycle_states=lifecycle_states,
        )

        return results

    def update_lifecycle_state(
        self,
        strategy_id: str,
        recent_ic: Optional[float] = None,
        recent_sharpe: Optional[float] = None,
        recent_drawdown: Optional[float] = None,
    ) -> Optional[LifecycleState]:
        """更新策略生命周期状态

        白皮书依据: 第四章 4.4.3 生命周期管理

        Args:
            strategy_id: 策略ID
            recent_ic: 最近IC值
            recent_sharpe: 最近夏普比率
            recent_drawdown: 最近最大回撤

        Returns:
            更新后的生命周期状态，如果策略不存在则返回None
        """
        record = self.get_strategy(strategy_id)
        if not record:
            logger.error(f"策略不存在: {strategy_id}")
            return None

        # 使用生命周期管理器更新状态
        new_state = self.lifecycle_manager.update_lifecycle_state(
            metadata=record.metadata,
            recent_ic=recent_ic,
            recent_sharpe=recent_sharpe,
            recent_drawdown=recent_drawdown,
        )

        # 持久化
        self._save_strategy(record)

        return new_state

    def can_allocate_capital(self, strategy_id: str) -> bool:
        """判断策略是否可以分配新资金

        白皮书依据: Requirement 5.7 - 废弃策略禁止新资金

        Args:
            strategy_id: 策略ID

        Returns:
            是否可以分配新资金
        """
        record = self.get_strategy(strategy_id)
        if not record:
            logger.error(f"策略不存在: {strategy_id}")
            return False

        return self.lifecycle_manager.can_allocate_capital(record.metadata)

    def list_all_strategies(self) -> List[str]:
        """列出所有策略ID

        Returns:
            策略ID列表
        """
        return list(self.strategies.keys())

    def get_statistics(self) -> Dict[str, any]:
        """获取策略库统计信息

        Returns:
            统计信息字典
        """
        all_metadata = [record.metadata for record in self.strategies.values()]

        # 生命周期统计
        lifecycle_stats = self.lifecycle_manager.get_statistics(all_metadata)

        # Z2H认证统计
        z2h_count = sum(1 for m in all_metadata if m.z2h_certified)

        # 策略类型统计
        type_stats = {}
        for metadata in all_metadata:
            type_name = metadata.strategy_type.value
            type_stats[type_name] = type_stats.get(type_name, 0) + 1

        stats = {
            "total_strategies": len(self.strategies),
            "z2h_certified_count": z2h_count,
            "lifecycle_stats": lifecycle_stats,
            "type_stats": type_stats,
            "storage_dir": str(self.storage_dir),
        }

        logger.info(
            f"策略库统计: "
            f"总数={stats['total_strategies']}, "
            f"Z2H认证={z2h_count}, "
            f"ACTIVE={lifecycle_stats['ACTIVE']}"
        )

        return stats

    def _save_strategy(self, record: StrategyRecord) -> bool:
        """保存策略到文件系统

        Args:
            record: 策略记录

        Returns:
            是否保存成功
        """
        try:
            file_path = self._get_file_path(record.metadata.strategy_id)

            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(record.to_dict(), f, ensure_ascii=False, indent=2)

            logger.debug(f"策略已保存: {file_path}")
            return True

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"保存策略失败: {record.metadata.strategy_id}, 错误: {e}")
            return False

    def _load_strategies(self):
        """从文件系统加载策略"""
        try:
            for file_path in self.storage_dir.glob("*.json"):
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        data = json.load(f)

                    record = StrategyRecord.from_dict(data)
                    self.strategies[record.metadata.strategy_id] = record

                except Exception as e:  # pylint: disable=broad-exception-caught
                    logger.error(f"加载策略失败: {file_path}, 错误: {e}")

            logger.info(f"已加载{len(self.strategies)}个策略")

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"加载策略目录失败: {e}")

    def _get_file_path(self, strategy_id: str) -> Path:
        """获取策略文件路径

        Args:
            strategy_id: 策略ID

        Returns:
            文件路径
        """
        return self.storage_dir / f"{strategy_id}.json"
