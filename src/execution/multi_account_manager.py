"""多账户管理器

白皮书依据: 第十七章 17.3.1 多账户管理系统

核心功能:
- 管理多个券商的多个QMT账号
- 智能路由订单到最优账户
- 统计跨账户资金和持仓
- 监控账户健康状态
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from loguru import logger

from src.evolution.qmt_broker_api import BrokerSimulationAPI, MockBrokerAPI, QMTBrokerAPI
from src.execution.multi_account_data_models import AccountConfig, AccountStatus, OrderRoutingResult


class MultiAccountManager:
    """多账户管理器

    白皮书依据: 第十七章 17.3.1 多账户管理系统

    职责：
    - 管理多个券商的多个QMT账号
    - 智能路由订单到最优账户
    - 统计跨账户资金和持仓
    - 监控账户健康状态

    Attributes:
        accounts: 账户池 {account_id: BrokerSimulationAPI}
        account_configs: 账户配置 {account_id: AccountConfig}
        routing_strategy: 订单路由策略
        redis_client: Redis客户端（可选）
    """

    def __init__(self, routing_strategy: str = "balanced", redis_client: Optional[Any] = None):
        """初始化多账户管理器

        白皮书依据: 第十七章 17.3.1

        Args:
            routing_strategy: 路由策略
                - 'balanced': 均衡分配（默认）
                - 'priority': 优先级优先
                - 'capacity': 容量优先
                - 'hash': 哈希分片
            redis_client: Redis客户端（可选）

        Raises:
            ValueError: 当routing_strategy不支持时
        """
        if routing_strategy not in ["balanced", "priority", "capacity", "hash"]:
            raise ValueError(f"不支持的路由策略: {routing_strategy}")

        self.accounts: Dict[str, BrokerSimulationAPI] = {}
        self.account_configs: Dict[str, AccountConfig] = {}
        self.routing_strategy = routing_strategy
        self.redis_client = redis_client

        # 统计信息
        self.total_orders_routed = 0
        self.routing_stats: Dict[str, int] = {}

        logger.info(f"初始化多账户管理器，路由策略: {routing_strategy}")

    async def add_account(self, config: AccountConfig, use_mock: bool = False) -> bool:
        """添加账户

        白皮书依据: 第十七章 17.3.1

        Args:
            config: 账户配置
            use_mock: 是否使用Mock API（用于测试）

        Returns:
            bool: 是否添加成功

        Raises:
            ValueError: 当账户ID重复时
            ConnectionError: 当连接失败时
        """
        if config.account_id in self.accounts:
            raise ValueError(f"账户ID已存在: {config.account_id}")

        try:
            # 创建券商API实例
            if use_mock:
                broker_api = MockBrokerAPI()
            elif config.broker_name == "国金":
                broker_api = QMTBrokerAPI(config.qmt_config)
            else:
                raise ValueError(f"不支持的券商: {config.broker_name}")

            # 连接账户
            logger.info(f"正在连接账户: {config.account_id} ({config.broker_name})")
            connected = await broker_api.connect()

            if not connected:
                raise ConnectionError(f"账户连接失败: {config.account_id}")

            # 添加到账户池
            self.accounts[config.account_id] = broker_api
            self.account_configs[config.account_id] = config
            self.routing_stats[config.account_id] = 0

            logger.info(
                f"账户添加成功: {config.account_id} ({config.broker_name}), "
                f"最大资金: {config.max_capital:.2f}, "
                f"优先级: {config.priority}"
            )

            return True

        except Exception as e:
            logger.error(f"添加账户失败: {config.account_id}, 错误: {e}")
            raise

    async def remove_account(self, account_id: str) -> bool:
        """移除账户

        白皮书依据: 第十七章 17.3.1

        Args:
            account_id: 账户ID

        Returns:
            bool: 是否移除成功
        """
        if account_id not in self.accounts:
            logger.warning(f"账户不存在: {account_id}")
            return False

        try:
            # 断开连接
            broker_api = self.accounts[account_id]
            await broker_api.disconnect()

            # 从账户池移除
            del self.accounts[account_id]
            del self.account_configs[account_id]
            if account_id in self.routing_stats:
                del self.routing_stats[account_id]

            logger.info(f"账户已移除: {account_id}")

            return True

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"移除账户失败: {account_id}, 错误: {e}")
            return False

    async def route_order(self, order: Dict[str, Any]) -> OrderRoutingResult:
        """路由订单到最优账户

        白皮书依据: 第十七章 17.3.1 订单路由策略

        Args:
            order: 订单信息 {
                'symbol': str,
                'side': str,
                'quantity': float,
                'price': float,
                'strategy_id': str
            }

        Returns:
            OrderRoutingResult: 路由结果

        Raises:
            RuntimeError: 当没有可用账户时
            ValueError: 当订单信息不完整时
        """
        # 验证订单信息
        required_fields = ["symbol", "side", "quantity"]
        for field in required_fields:
            if field not in order:
                raise ValueError(f"订单缺少必需字段: {field}")

        # 获取可用账户
        available_accounts = await self._get_available_accounts()

        if not available_accounts:
            raise RuntimeError("没有可用账户")

        # 根据策略选择账户
        if self.routing_strategy == "balanced":
            result = await self._route_balanced(order, available_accounts)
        elif self.routing_strategy == "priority":
            result = await self._route_priority(order, available_accounts)
        elif self.routing_strategy == "capacity":
            result = await self._route_capacity(order, available_accounts)
        elif self.routing_strategy == "hash":
            result = await self._route_hash(order, available_accounts)
        else:
            raise ValueError(f"不支持的路由策略: {self.routing_strategy}")

        # 更新统计
        self.total_orders_routed += 1
        self.routing_stats[result.account_id] = self.routing_stats.get(result.account_id, 0) + 1

        logger.info(
            f"订单路由完成 - "
            f"symbol={order['symbol']}, "
            f"account={result.account_id}, "
            f"strategy={self.routing_strategy}, "
            f"reason={result.reason}"
        )

        return result

    async def get_total_assets(self) -> float:
        """获取所有账户总资产

        白皮书依据: 第十七章 17.3.1

        Returns:
            float: 总资产
        """
        total = 0.0

        for account_id, broker_api in self.accounts.items():
            try:
                status = await self._get_account_status(account_id, broker_api)
                total += status.total_assets
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.error(f"获取账户资产失败: {account_id}, {e}")

        logger.debug(f"总资产: {total:.2f}")

        return total

    async def get_all_positions(self) -> List[Dict[str, Any]]:
        """获取所有账户持仓汇总

        白皮书依据: 第十七章 17.3.1

        Returns:
            List[Dict[str, Any]]: 持仓列表，每个持仓包含account_id字段
        """
        all_positions = []

        for account_id, broker_api in self.accounts.items():  # pylint: disable=unused-variable
            try:
                # 注意：这里简化处理，实际需要维护account_id到simulation_id的映射
                # 暂时返回空列表
                positions = []

                # 添加account_id标识
                for pos in positions:
                    pos["account_id"] = account_id
                    all_positions.append(pos)

            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.error(f"获取账户持仓失败: {account_id}, {e}")

        logger.debug(f"总持仓数: {len(all_positions)}")

        return all_positions

    async def get_all_account_status(self) -> Dict[str, AccountStatus]:
        """获取所有账户状态

        白皮书依据: 第十七章 17.3.1

        Returns:
            Dict[str, AccountStatus]: 账户状态字典 {account_id: AccountStatus}
        """
        status_dict = {}

        for account_id, broker_api in self.accounts.items():
            try:
                status = await self._get_account_status(account_id, broker_api)
                status_dict[account_id] = status
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.error(f"获取账户状态失败: {account_id}, {e}")

                # 创建错误状态
                config = self.account_configs[account_id]
                status_dict[account_id] = AccountStatus(
                    account_id=account_id,
                    broker_name=config.broker_name,
                    connected=False,
                    total_assets=0.0,
                    available_cash=0.0,
                    market_value=0.0,
                    position_count=0,
                    today_pnl=0.0,
                    health_status="error",
                    last_update_time=datetime.now(),
                    error_message=str(e),
                )

        return status_dict

    async def health_check(self) -> Dict[str, Any]:
        """健康检查

        白皮书依据: 第十七章 17.3.1

        Returns:
            Dict[str, Any]: 健康检查结果 {
                'total_accounts': int,
                'healthy_accounts': int,
                'warning_accounts': int,
                'error_accounts': int,
                'total_assets': float,
                'total_orders_routed': int,
                'routing_distribution': Dict[str, int],
                'details': List[AccountStatus]
            }
        """
        all_status = await self.get_all_account_status()

        healthy = sum(1 for s in all_status.values() if s.health_status == "healthy")
        warning = sum(1 for s in all_status.values() if s.health_status == "warning")
        error = sum(1 for s in all_status.values() if s.health_status == "error")

        total_assets = sum(s.total_assets for s in all_status.values())

        result = {
            "total_accounts": len(all_status),
            "healthy_accounts": healthy,
            "warning_accounts": warning,
            "error_accounts": error,
            "total_assets": total_assets,
            "total_orders_routed": self.total_orders_routed,
            "routing_distribution": self.routing_stats.copy(),
            "details": [s.to_dict() for s in all_status.values()],
        }

        logger.info(
            f"健康检查完成 - "
            f"总账户: {result['total_accounts']}, "
            f"健康: {healthy}, "
            f"警告: {warning}, "
            f"错误: {error}"
        )

        return result

    def get_account_count(self) -> int:
        """获取账户数量

        Returns:
            int: 账户数量
        """
        return len(self.accounts)

    def get_routing_stats(self) -> Dict[str, Any]:
        """获取路由统计

        Returns:
            Dict[str, Any]: 路由统计信息
        """
        return {
            "total_orders": self.total_orders_routed,
            "routing_strategy": self.routing_strategy,
            "distribution": self.routing_stats.copy(),
        }

    # ==================== 内部方法 ====================

    async def _get_available_accounts(self) -> List[str]:
        """获取可用账户列表（内部方法）

        Returns:
            List[str]: 可用账户ID列表
        """
        available = []

        for account_id, config in self.account_configs.items():
            if config.enabled and account_id in self.accounts:
                available.append(account_id)

        return available

    async def _route_balanced(
        self, order: Dict[str, Any], available_accounts: List[str]  # pylint: disable=unused-argument
    ) -> OrderRoutingResult:  # pylint: disable=unused-argument
        """均衡路由策略（内部方法）

        选择可用资金最多的账户

        Args:
            order: 订单信息
            available_accounts: 可用账户列表

        Returns:
            OrderRoutingResult: 路由结果
        """
        max_cash = 0.0
        selected_account = None

        for account_id in available_accounts:
            broker_api = self.accounts[account_id]
            status = await self._get_account_status(account_id, broker_api)

            if status.available_cash > max_cash:
                max_cash = status.available_cash
                selected_account = account_id

        if not selected_account:
            selected_account = available_accounts[0]
            max_cash = 0.0

        return OrderRoutingResult(
            account_id=selected_account,
            reason=f"可用资金最多: {max_cash:.2f}",
            confidence=0.8,
            routing_strategy="balanced",
        )

    async def _route_priority(
        self, order: Dict[str, Any], available_accounts: List[str]  # pylint: disable=unused-argument
    ) -> OrderRoutingResult:  # pylint: disable=unused-argument
        """优先级路由策略（内部方法）

        选择优先级最高的账户

        Args:
            order: 订单信息
            available_accounts: 可用账户列表

        Returns:
            OrderRoutingResult: 路由结果
        """
        max_priority = 0
        selected_account = None

        for account_id in available_accounts:
            config = self.account_configs[account_id]
            if config.priority > max_priority:
                max_priority = config.priority
                selected_account = account_id

        if not selected_account:
            selected_account = available_accounts[0]
            max_priority = self.account_configs[selected_account].priority

        return OrderRoutingResult(
            account_id=selected_account,
            reason=f"优先级最高: {max_priority}",
            confidence=0.9,
            routing_strategy="priority",
        )

    async def _route_capacity(
        self, order: Dict[str, Any], available_accounts: List[str]  # pylint: disable=unused-argument
    ) -> OrderRoutingResult:  # pylint: disable=unused-argument
        """容量路由策略（内部方法）

        选择剩余容量最大的账户

        Args:
            order: 订单信息
            available_accounts: 可用账户列表

        Returns:
            OrderRoutingResult: 路由结果
        """
        max_remaining = 0.0
        selected_account = None

        for account_id in available_accounts:
            config = self.account_configs[account_id]
            broker_api = self.accounts[account_id]
            status = await self._get_account_status(account_id, broker_api)

            remaining = config.max_capital - status.total_assets
            if remaining > max_remaining:
                max_remaining = remaining
                selected_account = account_id

        if not selected_account:
            selected_account = available_accounts[0]
            max_remaining = 0.0

        return OrderRoutingResult(
            account_id=selected_account,
            reason=f"剩余容量最大: {max_remaining:.2f}",
            confidence=0.85,
            routing_strategy="capacity",
        )

    async def _route_hash(self, order: Dict[str, Any], available_accounts: List[str]) -> OrderRoutingResult:
        """哈希路由策略（内部方法）

        根据symbol哈希分片

        Args:
            order: 订单信息
            available_accounts: 可用账户列表

        Returns:
            OrderRoutingResult: 路由结果
        """
        symbol = order.get("symbol", "")
        shard_id = hash(symbol) % len(available_accounts)
        selected_account = available_accounts[shard_id]

        return OrderRoutingResult(
            account_id=selected_account,
            reason=f"哈希分片: shard_id={shard_id}",
            confidence=1.0,
            routing_strategy="hash",
        )

    async def _get_account_status(
        self, account_id: str, broker_api: BrokerSimulationAPI  # pylint: disable=unused-argument
    ) -> AccountStatus:  # pylint: disable=unused-argument
        """获取账户状态（内部方法）

        Args:
            account_id: 账户ID
            broker_api: 券商API实例

        Returns:
            AccountStatus: 账户状态
        """
        config = self.account_configs[account_id]

        # 简化实现：返回模拟数据
        # 实际应该调用broker_api获取真实状态
        return AccountStatus(
            account_id=account_id,
            broker_name=config.broker_name,
            connected=True,
            total_assets=1000000.0,
            available_cash=500000.0,
            market_value=500000.0,
            position_count=10,
            today_pnl=5000.0,
            health_status="healthy",
            last_update_time=datetime.now(),
        )
