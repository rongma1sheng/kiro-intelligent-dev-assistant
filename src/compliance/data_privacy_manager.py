"""数据隐私管理器

白皮书依据: 第七章 6.3.1 数据隐私合规（GDPR/个保法）

DataPrivacyManager负责管理用户数据隐私，包括：
- 数据导出（GDPR第15条：数据可携带权）
- 数据删除（GDPR第17条：被遗忘权）
- 日志匿名化
- Redis缓存清理

特性：
- GDPR合规
- 个人信息保护法合规
- 审计日志记录
- 数据保留策略（交易数据保留7年）
"""

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger


class DataPrivacyError(Exception):
    """数据隐私错误

    白皮书依据: 第七章 6.3.1 数据隐私合规
    """


class UserNotFoundError(DataPrivacyError):
    """用户不存在错误"""


class DataRetentionError(DataPrivacyError):
    """数据保留期限错误"""


@dataclass
class UserDataExport:
    """用户数据导出结果

    白皮书依据: 第七章 6.3.1 数据隐私合规

    Attributes:
        user_id: 用户ID
        export_time: 导出时间
        export_file: 导出文件路径
        data_categories: 导出的数据类别
        record_count: 记录数量
    """

    user_id: str
    export_time: str
    export_file: str
    data_categories: List[str] = field(default_factory=list)
    record_count: int = 0

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "user_id": self.user_id,
            "export_time": self.export_time,
            "export_file": self.export_file,
            "data_categories": self.data_categories,
            "record_count": self.record_count,
        }


@dataclass
class DataDeletionResult:
    """数据删除结果

    白皮书依据: 第七章 6.3.1 数据隐私合规

    Attributes:
        user_id: 用户ID
        deletion_time: 删除时间
        reason: 删除原因
        deleted_categories: 已删除的数据类别
        anonymized_logs: 匿名化的日志数量
        redis_keys_deleted: 删除的Redis键数量
    """

    user_id: str
    deletion_time: str
    reason: str
    deleted_categories: List[str] = field(default_factory=list)
    anonymized_logs: int = 0
    redis_keys_deleted: int = 0

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "user_id": self.user_id,
            "deletion_time": self.deletion_time,
            "reason": self.reason,
            "deleted_categories": self.deleted_categories,
            "anonymized_logs": self.anonymized_logs,
            "redis_keys_deleted": self.redis_keys_deleted,
        }


class DataPrivacyManager:
    """数据隐私管理器

    白皮书依据: 第七章 6.3.1 数据隐私合规（GDPR/个保法）

    管理用户数据隐私，包括数据导出、删除、匿名化等功能。

    Attributes:
        export_dir: 数据导出目录
        trade_retention_years: 交易数据保留年限（默认7年）
        redis_client: Redis客户端
        audit_logger: 审计日志记录器
        user_data_provider: 用户数据提供者
    """

    REDIS_KEY_PREFIX = "mia:user"
    ANONYMOUS_PREFIX = "anon_"

    def __init__(  # pylint: disable=too-many-positional-arguments
        self,
        export_dir: Optional[Path] = None,
        trade_retention_years: int = 7,
        redis_client: Optional[Any] = None,
        audit_logger: Optional[Any] = None,
        user_data_provider: Optional[Any] = None,
    ):
        """初始化DataPrivacyManager

        白皮书依据: 第七章 6.3.1 数据隐私合规

        Args:
            export_dir: 数据导出目录，默认为当前目录下的exports
            trade_retention_years: 交易数据保留年限，默认7年
            redis_client: Redis客户端
            audit_logger: 审计日志记录器
            user_data_provider: 用户数据提供者

        Raises:
            ValueError: 当参数无效时
        """
        if trade_retention_years < 0:
            raise ValueError(f"交易数据保留年限不能为负，当前值: {trade_retention_years}")

        self.export_dir = export_dir or Path("exports")
        self.trade_retention_years = trade_retention_years
        self.redis_client = redis_client
        self.audit_logger = audit_logger
        self.user_data_provider = user_data_provider

        # 内存存储（用于测试或无外部依赖时）
        self._user_data: Dict[str, Dict[str, Any]] = {}
        self._trade_data: Dict[str, List[Dict[str, Any]]] = {}
        self._log_data: List[Dict[str, Any]] = []

        # 确保导出目录存在
        self.export_dir.mkdir(parents=True, exist_ok=True)

        logger.info(
            f"DataPrivacyManager初始化完成: "
            f"export_dir={self.export_dir}, "
            f"retention_years={trade_retention_years}"
        )

    def export_user_data(self, user_id: str) -> UserDataExport:
        """导出用户数据（GDPR第15条：数据可携带权）

        白皮书依据: 第七章 6.3.1 数据隐私合规

        Args:
            user_id: 用户ID

        Returns:
            用户数据导出结果

        Raises:
            ValueError: 当user_id为空时
            UserNotFoundError: 当用户不存在时
        """
        if not user_id or not user_id.strip():
            raise ValueError("用户ID不能为空")

        user_id = user_id.strip()
        export_time = datetime.now().isoformat()

        # 收集用户数据
        user_data = self._collect_user_data(user_id)

        if not user_data:
            raise UserNotFoundError(f"用户不存在: {user_id}")

        # 生成导出文件
        export_filename = f"user_data_{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        export_path = self.export_dir / export_filename

        # 写入文件
        with open(export_path, "w", encoding="utf-8") as f:
            json.dump(user_data, f, ensure_ascii=False, indent=2)

        # 统计数据类别和记录数
        data_categories = list(user_data.keys())
        record_count = sum(len(v) if isinstance(v, list) else 1 for v in user_data.values())

        result = UserDataExport(
            user_id=user_id,
            export_time=export_time,
            export_file=str(export_path),
            data_categories=data_categories,
            record_count=record_count,
        )

        # 记录审计日志
        self._log_event(
            {
                "event_type": "DATA_EXPORT",
                "user_id": user_id,
                "export_time": export_time,
                "export_file": str(export_path),
                "data_categories": data_categories,
                "record_count": record_count,
            }
        )

        logger.info(f"用户数据导出完成: {user_id}, 文件: {export_path}")
        return result

    def delete_user_data(self, user_id: str, reason: str = "user_request") -> DataDeletionResult:
        """删除用户数据（GDPR第17条：被遗忘权）

        白皮书依据: 第七章 6.3.1 数据隐私合规

        Args:
            user_id: 用户ID
            reason: 删除原因，默认为用户请求

        Returns:
            数据删除结果

        Raises:
            ValueError: 当user_id为空时
            DataRetentionError: 当交易数据在保留期内时
        """
        if not user_id or not user_id.strip():
            raise ValueError("用户ID不能为空")

        user_id = user_id.strip()
        deletion_time = datetime.now().isoformat()
        deleted_categories: List[str] = []

        # 记录删除请求
        self._log_event(
            {"event_type": "DATA_DELETION_REQUEST", "user_id": user_id, "reason": reason, "request_time": deletion_time}
        )

        # 检查交易数据保留期
        retention_check = self._check_trade_retention(user_id)
        if not retention_check["can_delete"]:
            raise DataRetentionError(f"交易数据在保留期内，无法删除: {retention_check['message']}")

        # 删除用户基本信息
        if self._delete_user_info(user_id):
            deleted_categories.append("user_info")

        # 删除交易数据（如果超过保留期）
        if self._delete_trade_data(user_id):
            deleted_categories.append("trade_data")

        # 删除策略配置
        if self._delete_strategy_config(user_id):
            deleted_categories.append("strategy_config")

        # 清理Redis缓存
        redis_keys_deleted = self._clear_redis_cache(user_id)

        # 匿名化审计日志
        anonymized_logs = self.anonymize_logs(user_id)

        result = DataDeletionResult(
            user_id=user_id,
            deletion_time=deletion_time,
            reason=reason,
            deleted_categories=deleted_categories,
            anonymized_logs=anonymized_logs,
            redis_keys_deleted=redis_keys_deleted,
        )

        # 记录删除完成
        self._log_event(
            {
                "event_type": "DATA_DELETION_COMPLETE",
                "user_id": self._anonymize_id(user_id),  # 使用匿名ID
                "reason": reason,
                "deletion_time": deletion_time,
                "deleted_categories": deleted_categories,
                "anonymized_logs": anonymized_logs,
                "redis_keys_deleted": redis_keys_deleted,
            }
        )

        logger.info(
            f"用户数据删除完成: {user_id}, " f"删除类别: {deleted_categories}, " f"匿名化日志: {anonymized_logs}"
        )
        return result

    def anonymize_logs(self, user_id: str) -> int:
        """匿名化日志中的用户信息

        白皮书依据: 第七章 6.3.1 数据隐私合规

        将日志中的user_id替换为匿名ID（哈希值）。

        Args:
            user_id: 用户ID

        Returns:
            匿名化的日志数量
        """
        if not user_id or not user_id.strip():
            return 0

        user_id = user_id.strip()
        anonymous_id = self._anonymize_id(user_id)
        anonymized_count = 0

        # 匿名化内存日志
        for log_entry in self._log_data:
            if log_entry.get("user_id") == user_id:
                log_entry["user_id"] = anonymous_id
                log_entry["anonymized"] = True
                anonymized_count += 1

        # 如果有审计日志记录器，也进行匿名化
        if self.audit_logger and hasattr(self.audit_logger, "anonymize_user"):
            try:
                count = self.audit_logger.anonymize_user(user_id, anonymous_id)
                anonymized_count += count
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.warning(f"审计日志匿名化失败: {e}")

        logger.debug(f"匿名化日志完成: {user_id} -> {anonymous_id}, 数量: {anonymized_count}")
        return anonymized_count

    def _collect_user_data(self, user_id: str) -> Dict[str, Any]:
        """收集用户所有数据

        Args:
            user_id: 用户ID

        Returns:
            用户数据字典
        """
        user_data: Dict[str, Any] = {}

        # 从提供者获取数据
        if self.user_data_provider:
            try:
                provider_data = self.user_data_provider.get_user_data(user_id)
                if provider_data:
                    user_data.update(provider_data)
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.warning(f"从提供者获取用户数据失败: {e}")

        # 从内存获取数据
        if user_id in self._user_data:
            user_data["user_info"] = self._user_data[user_id]

        if user_id in self._trade_data:
            user_data["trade_history"] = self._trade_data[user_id]

        # 从Redis获取数据
        if self.redis_client:
            try:
                redis_data = self._get_redis_user_data(user_id)
                if redis_data:
                    user_data["redis_data"] = redis_data
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.warning(f"从Redis获取用户数据失败: {e}")

        return user_data

    def _get_redis_user_data(self, user_id: str) -> Dict[str, Any]:
        """从Redis获取用户数据

        Args:
            user_id: 用户ID

        Returns:
            Redis中的用户数据
        """
        if not self.redis_client:
            return {}

        redis_data: Dict[str, Any] = {}

        try:
            # 获取用户相关的所有键
            pattern = f"{self.REDIS_KEY_PREFIX}:{user_id}:*"
            keys = self.redis_client.keys(pattern)

            for key in keys:
                if isinstance(key, bytes):
                    key = key.decode("utf-8")

                value = self.redis_client.get(key)
                if value:
                    if isinstance(value, bytes):
                        value = value.decode("utf-8")
                    try:
                        redis_data[key] = json.loads(value)
                    except json.JSONDecodeError:
                        redis_data[key] = value
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.warning(f"获取Redis用户数据失败: {e}")

        return redis_data

    def _check_trade_retention(self, user_id: str) -> Dict[str, Any]:
        """检查交易数据保留期

        白皮书依据: 第七章 6.3.1 数据隐私合规
        交易数据需保留7年以符合监管要求。

        Args:
            user_id: 用户ID

        Returns:
            检查结果字典
        """
        # 获取用户最近的交易时间
        trades = self._trade_data.get(user_id, [])

        if not trades:
            return {"can_delete": True, "message": "无交易数据"}

        # 找到最近的交易时间
        latest_trade_time = None
        for trade in trades:
            trade_time_str = trade.get("timestamp") or trade.get("trade_time")
            if trade_time_str:
                try:
                    trade_time = datetime.fromisoformat(trade_time_str)
                    if latest_trade_time is None or trade_time > latest_trade_time:
                        latest_trade_time = trade_time
                except (ValueError, TypeError):
                    pass

        if latest_trade_time is None:
            return {"can_delete": True, "message": "无有效交易时间"}

        # 计算保留期限
        retention_end = latest_trade_time + timedelta(days=self.trade_retention_years * 365)

        if datetime.now() < retention_end:
            return {
                "can_delete": False,
                "message": f"交易数据需保留至 {retention_end.strftime('%Y-%m-%d')}",
                "retention_end": retention_end.isoformat(),
            }

        return {"can_delete": True, "message": "交易数据已超过保留期"}

    def _delete_user_info(self, user_id: str) -> bool:
        """删除用户基本信息

        Args:
            user_id: 用户ID

        Returns:
            是否删除成功
        """
        if user_id in self._user_data:
            del self._user_data[user_id]
            return True
        return False

    def _delete_trade_data(self, user_id: str) -> bool:
        """删除交易数据

        Args:
            user_id: 用户ID

        Returns:
            是否删除成功
        """
        if user_id in self._trade_data:
            del self._trade_data[user_id]
            return True
        return False

    def _delete_strategy_config(self, user_id: str) -> bool:  # pylint: disable=unused-argument
        """删除策略配置

        Args:
            user_id: 用户ID

        Returns:
            是否删除成功
        """
        # 策略配置通常存储在Redis或数据库中
        # 这里简化处理
        return False

    def _clear_redis_cache(self, user_id: str) -> int:
        """清理Redis缓存

        白皮书依据: 第七章 6.3.1 数据隐私合规

        Args:
            user_id: 用户ID

        Returns:
            删除的键数量
        """
        if not self.redis_client:
            return 0

        deleted_count = 0

        try:
            # 获取用户相关的所有键
            pattern = f"{self.REDIS_KEY_PREFIX}:{user_id}:*"
            keys = self.redis_client.keys(pattern)

            for key in keys:
                self.redis_client.delete(key)
                deleted_count += 1

            logger.debug(f"清理Redis缓存: {user_id}, 删除键数: {deleted_count}")
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.warning(f"清理Redis缓存失败: {e}")

        return deleted_count

    def _anonymize_id(self, user_id: str) -> str:
        """生成匿名ID

        Args:
            user_id: 用户ID

        Returns:
            匿名ID（SHA256哈希的前16位）
        """
        hash_value = hashlib.sha256(user_id.encode("utf-8")).hexdigest()
        return f"{self.ANONYMOUS_PREFIX}{hash_value[:16]}"

    def _log_event(self, event_data: Dict[str, Any]) -> None:
        """记录事件到审计日志

        Args:
            event_data: 事件数据
        """
        # 添加时间戳
        event_data["timestamp"] = datetime.now().isoformat()

        # 记录到内存
        self._log_data.append(event_data.copy())

        # 记录到审计日志
        if self.audit_logger:
            try:
                self.audit_logger.log_event(event_data)
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.warning(f"记录审计日志失败: {e}")

    # ========== 管理方法 ==========

    def set_user_data(self, user_id: str, data: Dict[str, Any]) -> None:
        """设置用户数据（用于测试）

        Args:
            user_id: 用户ID
            data: 用户数据
        """
        self._user_data[user_id] = data
        logger.debug(f"设置用户数据: {user_id}")

    def set_trade_data(self, user_id: str, trades: List[Dict[str, Any]]) -> None:
        """设置交易数据（用于测试）

        Args:
            user_id: 用户ID
            trades: 交易数据列表
        """
        self._trade_data[user_id] = trades
        logger.debug(f"设置交易数据: {user_id}, 数量: {len(trades)}")

    def get_user_data(self, user_id: str) -> Optional[Dict[str, Any]]:
        """获取用户数据

        Args:
            user_id: 用户ID

        Returns:
            用户数据，如果不存在返回None
        """
        return self._user_data.get(user_id)

    def get_trade_data(self, user_id: str) -> List[Dict[str, Any]]:
        """获取交易数据

        Args:
            user_id: 用户ID

        Returns:
            交易数据列表
        """
        return self._trade_data.get(user_id, [])

    def get_logs(self) -> List[Dict[str, Any]]:
        """获取所有日志

        Returns:
            日志列表
        """
        return self._log_data.copy()

    def clear_logs(self) -> None:
        """清空日志（用于测试）"""
        self._log_data.clear()
        logger.debug("清空日志")

    def is_user_anonymized(self, user_id: str) -> bool:
        """检查用户是否已匿名化

        Args:
            user_id: 用户ID

        Returns:
            是否已匿名化
        """
        anonymous_id = self._anonymize_id(user_id)

        for log_entry in self._log_data:
            if log_entry.get("user_id") == anonymous_id:
                return True

        return False
