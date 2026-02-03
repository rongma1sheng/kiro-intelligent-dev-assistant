"""认证数据持久化服务

白皮书依据: 第四章 4.3.2 Z2H认证系统 - 数据持久化

本模块实现认证数据的持久化存储，使用JSON文件存储确保数据的完整性和可恢复性。

核心功能：
- 策略元数据持久化
- Z2H基因胶囊持久化
- Arena验证结果持久化
- 模拟盘验证结果持久化
- 认证状态变更历史持久化
- 数据备份和恢复
- 事务支持

Author: MIA System
Version: 1.0.0
"""

import json
import shutil
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from threading import RLock
from typing import Any, Dict, List, Optional

from loguru import logger

from src.evolution.z2h_data_models import Z2HGeneCapsule, serialize_arena_result


@dataclass
class PersistenceConfig:
    """持久化配置

    Attributes:
        data_dir: 数据目录
        backup_dir: 备份目录
        enable_backup: 是否启用自动备份
        max_backups: 最大备份数量
    """

    data_dir: str = "data/z2h_certification"
    backup_dir: str = "data/z2h_certification/backups"
    enable_backup: bool = True
    max_backups: int = 10


class CertificationPersistenceService:
    """认证数据持久化服务

    白皮书依据: 第四章 4.3.2 Z2H认证系统 - 数据持久化

    使用JSON文件存储实现数据持久化，提供：
    1. 策略元数据持久化
    2. Z2H基因胶囊持久化
    3. Arena验证结果持久化
    4. 模拟盘验证结果持久化
    5. 认证状态变更历史持久化
    6. 数据备份和恢复
    7. 事务支持（通过临时文件+原子重命名）

    Attributes:
        config: 持久化配置
        _lock: 可重入锁，确保并发安全并支持嵌套调用
        _transaction_active: 事务是否激活
        _transaction_data: 事务数据缓存
    """

    def __init__(self, config: Optional[PersistenceConfig] = None):
        """初始化持久化服务

        Args:
            config: 持久化配置，None则使用默认配置
        """
        self.config = config or PersistenceConfig()
        self._lock = RLock()  # 使用可重入锁避免死锁
        self._transaction_active = False
        self._transaction_data: Dict[str, Any] = {}

        # 创建数据目录
        self._ensure_directories()

        logger.info(f"初始化CertificationPersistenceService - " f"data_dir={self.config.data_dir}")

    def _ensure_directories(self) -> None:
        """确保数据目录存在"""
        Path(self.config.data_dir).mkdir(parents=True, exist_ok=True)
        if self.config.enable_backup:
            Path(self.config.backup_dir).mkdir(parents=True, exist_ok=True)

    def save_strategy_metadata(self, strategy_id: str, metadata: Dict[str, Any]) -> bool:
        """保存策略元数据

        白皮书依据: Requirement 12.1

        Args:
            strategy_id: 策略ID
            metadata: 元数据字典

        Returns:
            bool: 保存是否成功

        Raises:
            IOError: 当文件写入失败时
        """
        with self._lock:
            try:
                file_path = self._get_metadata_path(strategy_id)

                # 添加时间戳
                metadata["last_updated"] = datetime.now().isoformat()

                # 写入文件（使用临时文件+原子重命名确保原子性）
                self._atomic_write(file_path, metadata)

                logger.info(f"策略元数据已保存 - strategy_id={strategy_id}")
                return True

            except Exception as e:
                logger.error(f"保存策略元数据失败: {e}")
                raise IOError(f"无法保存策略元数据: {strategy_id}") from e

    def load_strategy_metadata(self, strategy_id: str) -> Optional[Dict[str, Any]]:
        """加载策略元数据

        白皮书依据: Requirement 12.1

        Args:
            strategy_id: 策略ID

        Returns:
            Optional[Dict[str, Any]]: 元数据字典，不存在则返回None

        Raises:
            ValueError: 当数据格式不正确时
        """
        with self._lock:
            try:
                file_path = self._get_metadata_path(strategy_id)

                if not file_path.exists():
                    return None

                with open(file_path, "r", encoding="utf-8") as f:
                    metadata = json.load(f)

                logger.info(f"策略元数据已加载 - strategy_id={strategy_id}")
                return metadata

            except json.JSONDecodeError as e:
                logger.error(f"解析策略元数据失败: {e}")
                raise ValueError(f"策略元数据格式不正确: {strategy_id}") from e
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.error(f"加载策略元数据失败: {e}")
                return None

    def save_gene_capsule(self, strategy_id: str, gene_capsule: Z2HGeneCapsule) -> bool:
        """保存Z2H基因胶囊

        白皮书依据: Requirement 12.2

        Args:
            strategy_id: 策略ID
            gene_capsule: Z2H基因胶囊

        Returns:
            bool: 保存是否成功

        Raises:
            IOError: 当文件写入失败时
        """
        with self._lock:
            try:
                file_path = self._get_gene_capsule_path(strategy_id)

                # 序列化基因胶囊
                capsule_data = gene_capsule.to_dict()

                # 写入文件
                self._atomic_write(file_path, capsule_data)

                logger.info(f"Z2H基因胶囊已保存 - strategy_id={strategy_id}")
                return True

            except Exception as e:
                logger.error(f"保存Z2H基因胶囊失败: {e}")
                raise IOError(f"无法保存Z2H基因胶囊: {strategy_id}") from e

    def load_gene_capsule(self, strategy_id: str) -> Optional[Z2HGeneCapsule]:
        """加载Z2H基因胶囊

        白皮书依据: Requirement 12.2

        Args:
            strategy_id: 策略ID

        Returns:
            Optional[Z2HGeneCapsule]: 基因胶囊，不存在则返回None

        Raises:
            ValueError: 当数据格式不正确时
        """
        with self._lock:
            try:
                file_path = self._get_gene_capsule_path(strategy_id)

                if not file_path.exists():
                    return None

                with open(file_path, "r", encoding="utf-8") as f:
                    capsule_data = json.load(f)

                # 反序列化基因胶囊
                gene_capsule = Z2HGeneCapsule.from_dict(capsule_data)

                logger.info(f"Z2H基因胶囊已加载 - strategy_id={strategy_id}")
                return gene_capsule

            except (json.JSONDecodeError, ValueError) as e:
                logger.error(f"解析Z2H基因胶囊失败: {e}")
                raise ValueError(f"Z2H基因胶囊格式不正确: {strategy_id}") from e
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.error(f"加载Z2H基因胶囊失败: {e}")
                return None

    def save_arena_result(self, strategy_id: str, arena_result: Any) -> bool:
        """保存Arena验证结果

        白皮书依据: Requirement 12.3

        Args:
            strategy_id: 策略ID
            arena_result: Arena验证结果

        Returns:
            bool: 保存是否成功

        Raises:
            IOError: 当文件写入失败时
        """
        with self._lock:
            try:
                file_path = self._get_arena_result_path(strategy_id)

                # 序列化Arena结果
                result_data = serialize_arena_result(arena_result)
                result_data["saved_at"] = datetime.now().isoformat()

                # 写入文件
                self._atomic_write(file_path, result_data)

                logger.info(f"Arena验证结果已保存 - strategy_id={strategy_id}")
                return True

            except Exception as e:
                logger.error(f"保存Arena验证结果失败: {e}")
                raise IOError(f"无法保存Arena验证结果: {strategy_id}") from e

    def load_arena_result(self, strategy_id: str) -> Optional[Dict[str, Any]]:
        """加载Arena验证结果

        白皮书依据: Requirement 12.3

        Args:
            strategy_id: 策略ID

        Returns:
            Optional[Dict[str, Any]]: Arena结果字典，不存在则返回None

        Raises:
            ValueError: 当数据格式不正确时
        """
        with self._lock:
            try:
                file_path = self._get_arena_result_path(strategy_id)

                if not file_path.exists():
                    return None

                with open(file_path, "r", encoding="utf-8") as f:
                    result_data = json.load(f)

                logger.info(f"Arena验证结果已加载 - strategy_id={strategy_id}")
                return result_data

            except json.JSONDecodeError as e:
                logger.error(f"解析Arena验证结果失败: {e}")
                raise ValueError(f"Arena验证结果格式不正确: {strategy_id}") from e
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.error(f"加载Arena验证结果失败: {e}")
                return None

    def save_simulation_result(self, strategy_id: str, simulation_result: Dict[str, Any]) -> bool:
        """保存模拟盘验证结果

        白皮书依据: Requirement 12.4

        Args:
            strategy_id: 策略ID
            simulation_result: 模拟盘验证结果

        Returns:
            bool: 保存是否成功

        Raises:
            IOError: 当文件写入失败时
        """
        with self._lock:
            try:
                file_path = self._get_simulation_result_path(strategy_id)

                # 如果是SimulationResult对象，转换为字典
                if hasattr(simulation_result, "__dict__"):
                    result_dict = self._convert_to_serializable(simulation_result.__dict__)
                else:
                    result_dict = self._convert_to_serializable(simulation_result)

                # 添加时间戳
                result_dict["saved_at"] = datetime.now().isoformat()

                # 写入文件
                self._atomic_write(file_path, result_dict)

                logger.info(f"模拟盘验证结果已保存 - strategy_id={strategy_id}")
                return True

            except Exception as e:
                logger.error(f"保存模拟盘验证结果失败: {e}")
                raise IOError(f"无法保存模拟盘验证结果: {strategy_id}") from e

    def load_simulation_result(self, strategy_id: str) -> Optional[Dict[str, Any]]:
        """加载模拟盘验证结果

        白皮书依据: Requirement 12.4

        Args:
            strategy_id: 策略ID

        Returns:
            Optional[Dict[str, Any]]: 模拟盘结果字典，不存在则返回None

        Raises:
            ValueError: 当数据格式不正确时
        """
        with self._lock:
            try:
                file_path = self._get_simulation_result_path(strategy_id)

                if not file_path.exists():
                    return None

                with open(file_path, "r", encoding="utf-8") as f:
                    result_data = json.load(f)

                logger.info(f"模拟盘验证结果已加载 - strategy_id={strategy_id}")
                return result_data

            except json.JSONDecodeError as e:
                logger.error(f"解析模拟盘验证结果失败: {e}")
                raise ValueError(f"模拟盘验证结果格式不正确: {strategy_id}") from e
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.error(f"加载模拟盘验证结果失败: {e}")
                return None

    def save_status_change(self, strategy_id: str, change_record: Dict[str, Any]) -> bool:
        """保存认证状态变更记录

        白皮书依据: Requirement 12.5

        Args:
            strategy_id: 策略ID
            change_record: 状态变更记录

        Returns:
            bool: 保存是否成功

        Raises:
            IOError: 当文件写入失败时
        """
        with self._lock:
            try:
                file_path = self._get_status_history_path(strategy_id)

                # 加载现有历史
                history = []
                if file_path.exists():
                    with open(file_path, "r", encoding="utf-8") as f:
                        history = json.load(f)

                # 添加新记录
                change_record["timestamp"] = datetime.now().isoformat()
                history.append(change_record)

                # 写入文件
                self._atomic_write(file_path, history)

                logger.info(f"认证状态变更已保存 - strategy_id={strategy_id}")
                return True

            except Exception as e:
                logger.error(f"保存认证状态变更失败: {e}")
                raise IOError(f"无法保存认证状态变更: {strategy_id}") from e

    def load_status_history(self, strategy_id: str) -> List[Dict[str, Any]]:
        """加载认证状态变更历史

        白皮书依据: Requirement 12.5

        Args:
            strategy_id: 策略ID

        Returns:
            List[Dict[str, Any]]: 状态变更历史列表

        Raises:
            ValueError: 当数据格式不正确时
        """
        with self._lock:
            try:
                file_path = self._get_status_history_path(strategy_id)

                if not file_path.exists():
                    return []

                with open(file_path, "r", encoding="utf-8") as f:
                    history = json.load(f)

                logger.info(f"认证状态变更历史已加载 - strategy_id={strategy_id}, count={len(history)}")
                return history

            except json.JSONDecodeError as e:
                logger.error(f"解析认证状态变更历史失败: {e}")
                raise ValueError(f"认证状态变更历史格式不正确: {strategy_id}") from e
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.error(f"加载认证状态变更历史失败: {e}")
                return []

    def backup_data(self, backup_name: Optional[str] = None) -> str:
        """备份所有数据

        白皮书依据: Requirement 12.6

        Args:
            backup_name: 备份名称，None则使用时间戳

        Returns:
            str: 备份目录路径

        Raises:
            IOError: 当备份失败时
        """
        with self._lock:
            try:
                if not self.config.enable_backup:
                    raise IOError("备份功能未启用")

                # 生成备份名称
                if backup_name is None:
                    backup_name = datetime.now().strftime("%Y%m%d_%H%M%S")

                backup_path = Path(self.config.backup_dir) / backup_name

                # 复制数据目录
                shutil.copytree(self.config.data_dir, backup_path, ignore=shutil.ignore_patterns("backups"))

                # 清理旧备份
                self._cleanup_old_backups()

                logger.info(f"数据备份完成 - backup_path={backup_path}")
                return str(backup_path)

            except Exception as e:
                logger.error(f"数据备份失败: {e}")
                raise IOError(f"无法备份数据") from e  # pylint: disable=w1309

    def restore_data(self, backup_name: str) -> bool:
        """恢复数据

        白皮书依据: Requirement 12.6

        Args:
            backup_name: 备份名称

        Returns:
            bool: 恢复是否成功

        Raises:
            IOError: 当恢复失败时
        """
        with self._lock:
            try:  # pylint: disable=r1702
                backup_path = Path(self.config.backup_dir) / backup_name

                if not backup_path.exists():
                    raise IOError(f"备份不存在: {backup_name}")

                # 先备份当前数据
                current_backup = self.backup_data(f"before_restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}")

                try:
                    # 删除当前数据
                    data_path = Path(self.config.data_dir)
                    if data_path.exists():
                        for item in data_path.iterdir():
                            if item.name != "backups":
                                if item.is_file():
                                    item.unlink()
                                elif item.is_dir():
                                    shutil.rmtree(item)

                    # 恢复备份数据
                    for item in backup_path.iterdir():
                        if item.is_file():
                            shutil.copy2(item, data_path / item.name)
                        elif item.is_dir():
                            shutil.copytree(item, data_path / item.name)

                    logger.info(f"数据恢复完成 - backup_name={backup_name}")
                    return True

                except Exception as e:
                    # 恢复失败，回滚到之前的备份
                    logger.error(f"数据恢复失败，尝试回滚: {e}")
                    self.restore_data(Path(current_backup).name)
                    raise

            except Exception as e:
                logger.error(f"数据恢复失败: {e}")
                raise IOError(f"无法恢复数据: {backup_name}") from e

    def list_backups(self) -> List[str]:
        """列出所有备份

        Returns:
            List[str]: 备份名称列表
        """
        with self._lock:
            try:
                backup_path = Path(self.config.backup_dir)

                if not backup_path.exists():
                    return []

                backups = [item.name for item in backup_path.iterdir() if item.is_dir()]

                return sorted(backups, reverse=True)

            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.error(f"列出备份失败: {e}")
                return []

    def begin_transaction(self) -> None:
        """开始事务

        白皮书依据: Requirement 12.7

        Raises:
            RuntimeError: 当事务已激活时
        """
        with self._lock:
            if self._transaction_active:
                raise RuntimeError("事务已激活")

            self._transaction_active = True
            self._transaction_data = {}

            logger.info("事务已开始")

    def commit_transaction(self) -> bool:
        """提交事务

        白皮书依据: Requirement 12.7

        Returns:
            bool: 提交是否成功

        Raises:
            RuntimeError: 当事务未激活时
        """
        with self._lock:
            if not self._transaction_active:
                raise RuntimeError("事务未激活")

            try:
                # 执行所有缓存的写操作
                for key, data in self._transaction_data.items():  # pylint: disable=unused-variable
                    operation, args = data
                    if operation == "save_metadata":
                        self.save_strategy_metadata(*args)
                    elif operation == "save_gene_capsule":
                        self.save_gene_capsule(*args)
                    elif operation == "save_arena_result":
                        self.save_arena_result(*args)
                    elif operation == "save_simulation_result":
                        self.save_simulation_result(*args)
                    elif operation == "save_status_change":
                        self.save_status_change(*args)

                self._transaction_active = False
                self._transaction_data = {}

                logger.info("事务已提交")
                return True

            except Exception as e:
                logger.error(f"事务提交失败: {e}")
                self.rollback_transaction()
                raise

    def rollback_transaction(self) -> None:
        """回滚事务

        白皮书依据: Requirement 12.7

        Raises:
            RuntimeError: 当事务未激活时
        """
        with self._lock:
            if not self._transaction_active:
                raise RuntimeError("事务未激活")

            self._transaction_active = False
            self._transaction_data = {}

            logger.info("事务已回滚")

    def _atomic_write(self, file_path: Path, data: Any) -> None:
        """原子写入文件

        使用临时文件+原子重命名确保写入的原子性

        Args:
            file_path: 文件路径
            data: 要写入的数据
        """
        temp_path = file_path.with_suffix(".tmp")

        try:
            # 写入临时文件
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2, default=self._json_serializer)

            # 原子重命名
            temp_path.replace(file_path)

        except Exception as e:  # pylint: disable=unused-variable
            # 清理临时文件
            if temp_path.exists():
                temp_path.unlink()
            raise

    def _convert_to_serializable(self, obj):
        """递归转换对象为可序列化格式"""
        from enum import Enum  # pylint: disable=import-outside-toplevel

        if isinstance(obj, dict):  # pylint: disable=no-else-return
            # 转换字典，处理枚举key
            result = {}
            for k, v in obj.items():
                # 转换key
                if isinstance(k, Enum):
                    key = k.value
                else:
                    key = str(k)
                # 递归转换value
                result[key] = self._convert_to_serializable(v)
            return result
        elif isinstance(obj, (list, tuple)):
            return [self._convert_to_serializable(item) for item in obj]
        elif isinstance(obj, Enum):
            return obj.value
        elif isinstance(obj, (datetime, date)):
            return obj.isoformat()
        elif hasattr(obj, "__dict__"):
            return self._convert_to_serializable(obj.__dict__)
        else:
            return obj

    def _json_serializer(self, obj):
        """自定义JSON序列化器，处理枚举和其他特殊对象"""
        from enum import Enum  # pylint: disable=import-outside-toplevel

        if isinstance(obj, Enum):  # pylint: disable=no-else-return
            return obj.value
        elif isinstance(obj, (datetime, date)):
            return obj.isoformat()
        elif hasattr(obj, "__dict__"):
            return obj.__dict__
        else:
            return str(obj)

    def _cleanup_old_backups(self) -> None:
        """清理旧备份"""
        try:
            backups = self.list_backups()

            if len(backups) > self.config.max_backups:
                # 删除最旧的备份
                for backup_name in backups[self.config.max_backups :]:
                    backup_path = Path(self.config.backup_dir) / backup_name
                    shutil.rmtree(backup_path)
                    logger.info(f"已删除旧备份: {backup_name}")

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.warning(f"清理旧备份失败: {e}")

    def _get_metadata_path(self, strategy_id: str) -> Path:
        """获取元数据文件路径"""
        metadata_dir = Path(self.config.data_dir) / "metadata"
        metadata_dir.mkdir(parents=True, exist_ok=True)
        return metadata_dir / f"{strategy_id}.json"

    def _get_gene_capsule_path(self, strategy_id: str) -> Path:
        """获取基因胶囊文件路径"""
        capsule_dir = Path(self.config.data_dir) / "gene_capsules"
        capsule_dir.mkdir(parents=True, exist_ok=True)
        return capsule_dir / f"{strategy_id}.json"

    def _get_arena_result_path(self, strategy_id: str) -> Path:
        """获取Arena结果文件路径"""
        arena_dir = Path(self.config.data_dir) / "arena_results"
        arena_dir.mkdir(parents=True, exist_ok=True)
        return arena_dir / f"{strategy_id}.json"

    def _get_simulation_result_path(self, strategy_id: str) -> Path:
        """获取模拟盘结果文件路径"""
        sim_dir = Path(self.config.data_dir) / "simulation_results"
        sim_dir.mkdir(parents=True, exist_ok=True)
        return sim_dir / f"{strategy_id}.json"

    def _get_status_history_path(self, strategy_id: str) -> Path:
        """获取状态历史文件路径"""
        history_dir = Path(self.config.data_dir) / "status_history"
        history_dir.mkdir(parents=True, exist_ok=True)
        return history_dir / f"{strategy_id}.json"
