"""LockBox Manager - Profit Locking to GC001 Reverse Repo

白皮书依据: 第十五章 15.1 LockBox实体化交易

核心功能:
- 真实执行利润锁定（买入GC001逆回购）
- 计算可转金额
- 构建逆回购订单（GC001代码: 204001）
- 记录锁定历史
"""

import json
from datetime import datetime
from typing import Any, Dict, Optional

from loguru import logger


class LockBoxManager:
    """LockBox管理器 - 利润锁定到GC001逆回购

    白皮书依据: 第十五章 15.1 LockBox实体化交易

    诺亚方舟哲学: MIA追求永存。强制执行LockBox机制，将利润物理隔离至
    安全资产（国债逆回购GC001）。无论市场发生何种黑天鹅事件导致前线
    资金归零，这颗种子都能让她在废墟中重生。

    Attributes:
        redis: Redis客户端
        broker: 券商接口
        min_transfer_amount: 最小转移金额（默认10000元）
        gc001_symbol: GC001代码（204001）
        gc001_exchange: 交易所（SSE）
        gc001_unit: 交易单位（1000份）
    """

    def __init__(self, redis_client, broker):
        """初始化LockBox管理器

        Args:
            redis_client: Redis客户端实例
            broker: 券商接口实例

        Raises:
            ValueError: 当redis_client或broker为None时
        """
        if redis_client is None:
            raise ValueError("redis_client不能为None")
        if broker is None:
            raise ValueError("broker不能为None")

        self.redis = redis_client
        self.broker = broker

        # 配置参数
        self.min_transfer_amount: float = 10000.0  # 最小1万
        self.gc001_symbol: str = "204001"  # GC001代码
        self.gc001_exchange: str = "SSE"  # 上交所
        self.gc001_unit: int = 1000  # 1000份倍数

        logger.info(
            f"[LockBox] 初始化完成 - "
            f"最小转移金额: {self.min_transfer_amount:,.2f}, "
            f"GC001代码: {self.gc001_symbol}"
        )

    def execute_lockbox_transfer(self, amount: float) -> Optional[Dict[str, Any]]:
        """真实执行利润锁定（买入GC001）

        白皮书依据: 第十五章 15.1 LockBox实体化交易

        执行流程:
        1. 计算可转金额（取amount和可用资金的较小值）
        2. 检查最小转移金额（10000元）
        3. 构建逆回购订单（GC001代码: 204001，1000份倍数）
        4. 提交订单到券商
        5. 记录锁定历史到Redis

        Args:
            amount: 要锁定的金额

        Returns:
            订单结果字典，包含:
            - status: 订单状态
            - order_id: 订单ID
            - amount: 实际锁定金额
            - symbol: 交易代码
            - timestamp: 时间戳

            如果失败返回None

        Raises:
            ValueError: 当amount <= 0时
        """
        if amount <= 0:
            raise ValueError(f"转移金额必须 > 0，当前: {amount}")

        logger.info(f"[LockBox] 开始执行利润锁定，目标金额: {amount:,.2f}")

        # 1. 计算可转金额
        available = self._get_available_cash()
        transfer_amount = min(amount, available)

        logger.debug(f"[LockBox] 可用资金: {available:,.2f}, " f"实际转移: {transfer_amount:,.2f}")

        # 2. 检查最小转移金额
        if transfer_amount < self.min_transfer_amount:
            logger.warning(
                f"[LockBox] 转移金额过小: {transfer_amount:,.2f} < " f"{self.min_transfer_amount:,.2f}，跳过"
            )
            return None

        # 3. 构建逆回购订单
        order = self._build_gc001_order(transfer_amount)

        logger.info(
            f"[LockBox] 构建订单 - "
            f"代码: {order['symbol']}, "
            f"数量: {order['amount']}份, "
            f"金额: {transfer_amount:,.2f}"
        )

        # 4. 提交订单
        try:
            result = self.broker.submit_order(order)
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"[LockBox] 提交订单失败: {e}")
            return None

        # 5. 处理订单结果
        if result.get("status") == "success":  # pylint: disable=no-else-return
            # 记录到Redis
            self._record_transfer(transfer_amount, result.get("order_id"))

            logger.info(
                f"[LockBox] ✅ 利润锁定成功 - " f"金额: {transfer_amount:,.2f}, " f"订单ID: {result.get('order_id')}"
            )

            return {
                "status": "success",
                "order_id": result.get("order_id"),
                "amount": transfer_amount,
                "symbol": self.gc001_symbol,
                "timestamp": datetime.now().isoformat(),
            }
        else:
            logger.error(f"[LockBox] 利润锁定失败 - " f"原因: {result.get('message', 'Unknown')}")
            return None

    def _get_available_cash(self) -> float:
        """获取可用资金

        从Redis读取portfolio:available_cash键

        Returns:
            可用资金金额，如果键不存在返回0.0
        """
        try:
            cash_str = self.redis.get("portfolio:available_cash")
            if cash_str is None:
                logger.warning("[LockBox] 可用资金键不存在，返回0.0")
                return 0.0

            cash = float(cash_str)
            logger.debug(f"[LockBox] 读取可用资金: {cash:,.2f}")
            return cash

        except (ValueError, TypeError) as e:
            logger.error(f"[LockBox] 读取可用资金失败: {e}")
            return 0.0

    def _build_gc001_order(self, amount: float) -> Dict[str, Any]:
        """构建GC001逆回购订单

        白皮书依据: 第十五章 15.1 LockBox实体化交易

        订单规则:
        - 代码: 204001 (GC001)
        - 交易所: SSE (上交所)
        - 方向: buy (买入)
        - 数量: 1000份倍数
        - 价格: 0 (市价)
        - 类型: market (市价单)

        Args:
            amount: 转移金额

        Returns:
            订单字典
        """
        # 计算份数（1000份倍数，向下取整）
        shares = int(amount / 100000) * self.gc001_unit

        order = {
            "symbol": self.gc001_symbol,
            "exchange": self.gc001_exchange,
            "action": "buy",
            "amount": shares,
            "price": 0,  # 市价
            "order_type": "market",
        }

        logger.debug(f"[LockBox] 构建订单 - " f"金额: {amount:,.2f}, " f"份数: {shares}")

        return order

    def _record_transfer(self, amount: float, order_id: str) -> None:
        """记录锁定历史到Redis

        记录到两个键:
        1. mia:lockbox - 哈希表，存储每次转移记录
        2. lockbox:total_locked - 累计锁定总额

        Args:
            amount: 锁定金额
            order_id: 订单ID
        """
        try:
            # 生成记录键
            timestamp = datetime.now().isoformat()
            record_key = f"transfer_{timestamp}"

            # 记录详情
            record_data = {"amount": amount, "order_id": order_id, "timestamp": timestamp}

            # 存储到Redis哈希表
            self.redis.hset("mia:lockbox", record_key, json.dumps(record_data))

            # 更新累计锁定总额
            self.redis.incrbyfloat("lockbox:total_locked", amount)

            logger.debug(f"[LockBox] 记录锁定历史 - " f"金额: {amount:,.2f}, " f"订单ID: {order_id}")

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"[LockBox] 记录锁定历史失败: {e}")

    def get_total_locked(self) -> float:
        """获取累计锁定总额

        Returns:
            累计锁定总额，如果键不存在返回0.0
        """
        try:
            total_str = self.redis.get("lockbox:total_locked")
            if total_str is None:
                return 0.0

            total = float(total_str)
            logger.debug(f"[LockBox] 累计锁定总额: {total:,.2f}")
            return total

        except (ValueError, TypeError) as e:
            logger.error(f"[LockBox] 读取累计锁定总额失败: {e}")
            return 0.0

    def get_transfer_history(self, limit: int = 10) -> list:
        """获取锁定历史记录

        Args:
            limit: 返回记录数量限制

        Returns:
            锁定历史记录列表，每条记录包含:
            - amount: 锁定金额
            - order_id: 订单ID
            - timestamp: 时间戳
        """
        try:
            # 获取所有记录
            all_records = self.redis.hgetall("mia:lockbox")

            # 解析并排序
            records = []
            for key, value in all_records.items():
                try:
                    record = json.loads(value)
                    records.append(record)
                except json.JSONDecodeError as e:
                    logger.warning(f"[LockBox] 解析记录失败: {key}, {e}")

            # 按时间戳降序排序
            records.sort(key=lambda x: x.get("timestamp", ""), reverse=True)

            # 返回限制数量
            return records[:limit]

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"[LockBox] 获取锁定历史失败: {e}")
            return []

    def calculate_transfer_amount(self, profit: float, transfer_ratio: float = 0.5) -> float:
        """计算应转移金额

        根据利润和转移比例计算应锁定的金额

        Args:
            profit: 利润金额
            transfer_ratio: 转移比例（默认50%）

        Returns:
            应转移金额

        Raises:
            ValueError: 当profit < 0或transfer_ratio不在[0, 1]范围时
        """
        if profit < 0:
            raise ValueError(f"利润不能为负数: {profit}")

        if not 0 <= transfer_ratio <= 1:
            raise ValueError(f"转移比例必须在[0, 1]范围内: {transfer_ratio}")

        transfer_amount = profit * transfer_ratio

        logger.debug(
            f"[LockBox] 计算转移金额 - "
            f"利润: {profit:,.2f}, "
            f"比例: {transfer_ratio:.1%}, "
            f"转移: {transfer_amount:,.2f}"
        )

        return transfer_amount
