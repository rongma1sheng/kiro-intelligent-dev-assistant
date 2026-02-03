"""审计日志系统

白皮书依据: 第六章 6.2.2 审计日志系统

AuditLogger负责记录系统中的所有关键操作，包括：
- 交易执行
- 持仓变动
- 资金变动
- 配置修改
- 用户登录
- API调用
- 告警触发

特性：
- 追加写入（Append-Only）
- SHA256签名防篡改
- 完整性验证
- Redis同步
"""

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from loguru import logger

from src.audit.data_models import AuditEntry, AuditEventType


class IntegrityError(Exception):
    """审计日志完整性错误

    白皮书依据: 第六章 6.2.2 审计日志系统
    """


class AuditLogger:
    """审计日志记录器

    白皮书依据: 第六章 6.2.2 审计日志系统

    不可变日志设计：
    - 追加写入（Append-Only）
    - SHA256签名防篡改
    - 完整性验证

    Attributes:
        log_dir: 日志目录
        log_file: 当前日志文件
        redis_client: Redis客户端（可选）
        max_recent_logs: Redis中保存的最近日志数量
    """

    DEFAULT_LOG_DIR = "D:/MIA_Data/logs/audit"
    DEFAULT_MAX_RECENT_LOGS = 1000

    def __init__(
        self,
        log_dir: Optional[str] = None,
        redis_client: Optional[Any] = None,
        max_recent_logs: int = DEFAULT_MAX_RECENT_LOGS,
    ):
        """初始化AuditLogger

        白皮书依据: 第六章 6.2.2 审计日志系统

        Args:
            log_dir: 日志目录，默认D:/MIA_Data/logs/audit
            redis_client: Redis客户端，用于同步最近日志
            max_recent_logs: Redis中保存的最近日志数量，默认1000

        Raises:
            ValueError: 当max_recent_logs <= 0时
        """
        if max_recent_logs <= 0:
            raise ValueError(f"max_recent_logs必须大于0，当前值: {max_recent_logs}")

        self.log_dir: Path = Path(log_dir or self.DEFAULT_LOG_DIR)
        self.redis_client = redis_client
        self.max_recent_logs: int = max_recent_logs

        # 创建日志目录
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # 当前日志文件
        self._update_log_file()

        logger.info(f"AuditLogger初始化完成: log_dir={self.log_dir}, " f"redis_enabled={redis_client is not None}")

    def _update_log_file(self) -> None:
        """更新当前日志文件路径（按日期）"""
        date_str = datetime.now().strftime("%Y%m%d")
        self.log_file: Path = self.log_dir / f"audit_{date_str}.log"

    def log_trade(self, trade_data: Dict[str, Any]) -> AuditEntry:
        """记录交易审计日志

        白皮书依据: 第六章 6.2.2 审计日志系统

        Args:
            trade_data: 交易数据，必须包含symbol, action, quantity, price

        Returns:
            AuditEntry对象

        Raises:
            ValueError: 当必需字段缺失时
        """
        # 验证必需字段
        required_fields = ["symbol", "action", "quantity", "price"]
        missing_fields = [f for f in required_fields if f not in trade_data]
        if missing_fields:
            raise ValueError(f"交易数据缺少必需字段: {missing_fields}")

        # 验证action
        if trade_data["action"] not in ("buy", "sell"):
            raise ValueError(f"无效的交易动作: {trade_data['action']}. 必须是'buy'或'sell'")

        # 计算金额
        amount = trade_data.get("amount")
        if amount is None:
            amount = trade_data["quantity"] * trade_data["price"]

        # 构建审计条目
        audit_entry = {
            "timestamp": datetime.now().isoformat(),
            "event_type": AuditEventType.TRADE_EXECUTION.value,
            "symbol": trade_data["symbol"],
            "action": trade_data["action"],
            "quantity": trade_data["quantity"],
            "price": trade_data["price"],
            "amount": amount,
            "order_id": trade_data.get("order_id"),
            "strategy_id": trade_data.get("strategy_id"),
            "user_id": trade_data.get("user_id", "system"),
        }

        # 生成审计签名
        audit_entry["audit_signature"] = self._generate_signature(audit_entry)

        # 写入日志
        self._write_log(audit_entry)

        # 同步到Redis
        self._sync_to_redis(audit_entry)

        logger.debug(
            f"记录交易审计: symbol={trade_data['symbol']}, "
            f"action={trade_data['action']}, quantity={trade_data['quantity']}"
        )

        return AuditEntry(
            timestamp=datetime.fromisoformat(audit_entry["timestamp"]),
            event_type=AuditEventType.TRADE_EXECUTION,
            data={
                k: v
                for k, v in audit_entry.items()
                if k not in ("timestamp", "event_type", "audit_signature", "user_id")
            },
            audit_signature=audit_entry["audit_signature"],
            user_id=audit_entry["user_id"],
        )

    def log_event(self, event_data: Dict[str, Any]) -> AuditEntry:
        """记录通用审计事件

        白皮书依据: 第六章 6.2.2 审计日志系统

        Args:
            event_data: 事件数据，必须包含event_type

        Returns:
            AuditEntry对象

        Raises:
            ValueError: 当event_type缺失或无效时
        """
        # 验证event_type
        if "event_type" not in event_data:
            raise ValueError("事件数据必须包含event_type字段")

        event_type_str = event_data["event_type"]
        try:
            event_type = AuditEventType(event_type_str)
        except ValueError:
            valid_types = [e.value for e in AuditEventType]
            raise ValueError(f"无效的事件类型: {event_type_str}. 有效类型: {valid_types}")  # pylint: disable=w0707

        # 构建审计条目
        audit_entry = {
            "timestamp": datetime.now().isoformat(),
            "event_type": event_type.value,
            "user_id": event_data.get("user_id", "system"),
            "data": {k: v for k, v in event_data.items() if k not in ("event_type", "user_id")},
        }

        # 生成审计签名
        audit_entry["audit_signature"] = self._generate_signature(audit_entry)

        # 写入日志
        self._write_log(audit_entry)

        # 同步到Redis
        self._sync_to_redis(audit_entry)

        logger.debug(f"记录审计事件: event_type={event_type.value}")

        return AuditEntry(
            timestamp=datetime.fromisoformat(audit_entry["timestamp"]),
            event_type=event_type,
            data=audit_entry["data"],
            audit_signature=audit_entry["audit_signature"],
            user_id=audit_entry["user_id"],
        )

    def _generate_signature(self, entry: Dict[str, Any]) -> str:
        """生成SHA256签名

        白皮书依据: 第六章 6.2.2 审计日志系统

        Args:
            entry: 审计条目（不包含audit_signature字段）

        Returns:
            SHA256签名字符串
        """
        # 排除signature字段本身
        entry_copy = {k: v for k, v in entry.items() if k != "audit_signature"}

        # 按key排序，确保一致性
        entry_str = json.dumps(entry_copy, sort_keys=True, ensure_ascii=False)

        return hashlib.sha256(entry_str.encode()).hexdigest()

    def _write_log(self, entry: Dict[str, Any]) -> None:
        """写入日志文件（追加模式）

        Args:
            entry: 审计条目
        """
        # 确保使用当天的日志文件
        self._update_log_file()

        # 追加写入（不可变）
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def _sync_to_redis(self, entry: Dict[str, Any]) -> None:
        """同步到Redis

        Args:
            entry: 审计条目
        """
        if self.redis_client is None:
            return

        try:
            # 添加到最近日志列表
            self.redis_client.lpush("mia:audit:recent_logs", json.dumps(entry, ensure_ascii=False))
            # 保持列表长度
            self.redis_client.ltrim("mia:audit:recent_logs", 0, self.max_recent_logs - 1)
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.warning(f"同步到Redis失败: {e}")

    def verify_integrity(self, log_file: Optional[Union[str, Path]] = None) -> bool:
        """验证审计日志完整性

        白皮书依据: 第六章 6.2.3 完整性验证

        Args:
            log_file: 要验证的日志文件，默认为当前日志文件

        Returns:
            True如果验证通过

        Raises:
            IntegrityError: 当发现签名不匹配时
            FileNotFoundError: 当日志文件不存在时
        """
        log_file = Path(log_file) if log_file else self.log_file

        if not log_file.exists():
            raise FileNotFoundError(f"日志文件不存在: {log_file}")

        with open(log_file, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue

                try:
                    entry = json.loads(line)
                except json.JSONDecodeError as e:
                    raise IntegrityError(f"Line {line_num}: JSON解析失败 - {e}")  # pylint: disable=w0707

                stored_signature = entry.get("audit_signature")
                if not stored_signature:
                    raise IntegrityError(f"Line {line_num}: 缺少audit_signature字段")

                # 重新计算签名
                calculated_signature = self._generate_signature(entry)

                if stored_signature != calculated_signature:
                    raise IntegrityError(
                        f"Line {line_num}: Signature mismatch. "
                        f"Log may have been tampered. "
                        f"Expected: {calculated_signature}, Got: {stored_signature}"
                    )

        logger.info(f"审计日志完整性验证通过: {log_file}")
        return True

    def get_recent_logs(self, count: int = 100) -> List[Dict[str, Any]]:
        """获取最近的审计日志

        Args:
            count: 获取的日志数量

        Returns:
            审计日志列表
        """
        if count <= 0:
            raise ValueError(f"count必须大于0，当前值: {count}")

        # 优先从Redis获取
        if self.redis_client:
            try:
                logs = self.redis_client.lrange("mia:audit:recent_logs", 0, count - 1)
                return [json.loads(log) for log in logs]
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.warning(f"从Redis获取日志失败: {e}")

        # 从文件获取
        return self._get_logs_from_file(count)

    def _get_logs_from_file(self, count: int) -> List[Dict[str, Any]]:
        """从文件获取最近的日志

        Args:
            count: 获取的日志数量

        Returns:
            审计日志列表
        """
        logs = []

        if not self.log_file.exists():
            return logs

        with open(self.log_file, "r", encoding="utf-8") as f:
            lines = f.readlines()

        # 获取最后count条
        for line in reversed(lines[-count:]):
            line = line.strip()
            if line:
                try:
                    logs.append(json.loads(line))
                except json.JSONDecodeError:
                    continue

        return logs

    def get_logs_by_date(self, date: datetime) -> List[Dict[str, Any]]:
        """获取指定日期的审计日志

        Args:
            date: 日期

        Returns:
            审计日志列表
        """
        date_str = date.strftime("%Y%m%d")
        log_file = self.log_dir / f"audit_{date_str}.log"

        if not log_file.exists():
            return []

        logs = []
        with open(log_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        logs.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue

        return logs

    def get_logs_by_event_type(self, event_type: AuditEventType, limit: int = 100) -> List[Dict[str, Any]]:
        """获取指定类型的审计日志

        Args:
            event_type: 事件类型
            limit: 最大返回数量

        Returns:
            审计日志列表
        """
        all_logs = self.get_recent_logs(self.max_recent_logs)

        filtered_logs = [log for log in all_logs if log.get("event_type") == event_type.value]

        return filtered_logs[:limit]

    def verify_all_logs(self) -> Dict[str, bool]:
        """验证所有审计日志文件

        Returns:
            文件名到验证结果的字典
        """
        results = {}

        for log_file in self.log_dir.glob("audit_*.log"):
            try:
                self.verify_integrity(log_file)
                results[log_file.name] = True
            except IntegrityError as e:
                logger.error(f"日志验证失败: {log_file.name} - {e}")
                results[log_file.name] = False

        return results
