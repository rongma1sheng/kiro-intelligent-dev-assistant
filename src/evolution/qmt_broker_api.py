"""QMT券商API封装

白皮书依据: 第四章 4.3.1 模拟盘验证标准

本模块封装国金证券QMT Python API，提供统一的模拟盘交易接口。
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from loguru import logger


@dataclass
class QMTConnectionConfig:
    """QMT连接配置

    Attributes:
        account_id: 资金账号
        password: 登录密码
        session_id: 会话ID（可选）
        mini_qmt_path: MiniQMT路径
    """

    account_id: str
    password: str
    session_id: Optional[str] = None
    mini_qmt_path: str = r"C:\Program Files\XtMiniQMT"


@dataclass
class SimulationStatus:
    """模拟盘状态

    Attributes:
        simulation_id: 模拟盘ID
        status: 状态（running/stopped/completed/error）
        start_time: 开始时间
        current_capital: 当前资金
        total_pnl: 总盈亏
        position_count: 持仓数量
        trade_count: 交易次数
        last_update_time: 最后更新时间
    """

    simulation_id: str
    status: str
    start_time: datetime
    current_capital: float
    total_pnl: float
    position_count: int
    trade_count: int
    last_update_time: datetime


@dataclass
class SimulationData:
    """模拟盘数据

    Attributes:
        simulation_id: 模拟盘ID
        trades: 交易记录列表
        positions: 持仓列表
        daily_pnl: 每日盈亏列表
        performance_metrics: 绩效指标
    """

    simulation_id: str
    trades: List[Dict[str, Any]]
    positions: List[Dict[str, Any]]
    daily_pnl: List[float]
    performance_metrics: Dict[str, float]


class BrokerSimulationAPI(ABC):
    """券商模拟盘API抽象接口

    白皮书依据: 第四章 4.3.1 模拟盘验证标准

    定义统一的模拟盘API接口，支持不同券商的实现。
    """

    @abstractmethod
    async def connect(self) -> bool:
        """连接到券商服务器

        Returns:
            bool: 是否连接成功
        """

    @abstractmethod
    async def disconnect(self) -> bool:
        """断开连接

        Returns:
            bool: 是否断开成功
        """

    @abstractmethod
    async def create_simulation(self, strategy_code: str, initial_capital: float, duration_days: int = 30) -> str:
        """创建模拟盘

        Args:
            strategy_code: 策略代码
            initial_capital: 初始资金
            duration_days: 运行天数

        Returns:
            str: 模拟盘ID
        """

    @abstractmethod
    async def get_simulation_status(self, simulation_id: str) -> SimulationStatus:
        """获取模拟盘状态

        Args:
            simulation_id: 模拟盘ID

        Returns:
            SimulationStatus: 模拟盘状态
        """

    @abstractmethod
    async def get_simulation_data(self, simulation_id: str) -> SimulationData:
        """获取模拟盘数据

        Args:
            simulation_id: 模拟盘ID

        Returns:
            SimulationData: 模拟盘数据
        """

    @abstractmethod
    async def stop_simulation(self, simulation_id: str) -> bool:
        """停止模拟盘

        Args:
            simulation_id: 模拟盘ID

        Returns:
            bool: 是否停止成功
        """


class QMTBrokerAPI(BrokerSimulationAPI):
    """国金证券QMT API实现

    白皮书依据: 第四章 4.3.1 模拟盘验证标准

    封装QMT Python API，提供模拟盘交易功能。

    注意：需要安装xtquant库：pip install xtquant
    """

    def __init__(self, config: QMTConnectionConfig):
        """初始化QMT API

        Args:
            config: QMT连接配置
        """
        self.config = config
        self.trader = None
        self.connected = False

        logger.info(f"初始化QMTBrokerAPI: account={config.account_id}")

    async def connect(self) -> bool:
        """连接到QMT服务器

        Returns:
            bool: 是否连接成功

        Raises:
            ConnectionError: 当连接失败时
        """
        try:
            # 导入QMT库
            try:
                from xtquant import xttrader  # pylint: disable=import-outside-toplevel
            except ImportError as e:
                raise ImportError("未安装xtquant库，请运行: pip install xtquant") from e

            # 创建交易连接
            self.trader = xttrader.XtQuantTrader(self.config.mini_qmt_path, self.config.session_id or "default_session")

            # 启动交易
            self.trader.start()

            # 连接账号
            connect_result = self.trader.connect()

            if connect_result != 0:
                raise ConnectionError(f"QMT连接失败，错误码: {connect_result}")

            # 订阅账号
            subscribe_result = self.trader.subscribe(self.config.account_id)

            if subscribe_result != 0:
                raise ConnectionError(f"QMT订阅账号失败，错误码: {subscribe_result}")

            self.connected = True
            logger.info("QMT连接成功")

            return True

        except Exception as e:
            logger.error(f"QMT连接失败: {e}")
            raise ConnectionError(f"QMT连接失败: {e}") from e

    async def disconnect(self) -> bool:
        """断开QMT连接

        Returns:
            bool: 是否断开成功
        """
        try:
            if self.trader and self.connected:
                self.trader.stop()
                self.connected = False
                logger.info("QMT连接已断开")

            return True

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"QMT断开连接失败: {e}")
            return False

    async def create_simulation(self, strategy_code: str, initial_capital: float, duration_days: int = 30) -> str:
        """创建模拟盘

        注意：QMT本身不直接支持"创建模拟盘"的概念。
        这里的实现是：
        1. 使用已有的模拟账号
        2. 记录初始资金状态
        3. 启动策略运行
        4. 返回一个唯一的simulation_id用于跟踪

        Args:
            strategy_code: 策略代码（Python脚本路径或代码字符串）
            initial_capital: 初始资金
            duration_days: 运行天数

        Returns:
            str: 模拟盘ID（格式：account_timestamp）

        Raises:
            ValueError: 当未连接或参数无效时
            RuntimeError: 当创建失败时
        """
        if not self.connected:
            raise ValueError("未连接到QMT，请先调用connect()")

        if initial_capital <= 0:
            raise ValueError(f"初始资金必须大于0: {initial_capital}")

        if duration_days <= 0:
            raise ValueError(f"运行天数必须大于0: {duration_days}")

        try:
            # 生成唯一的simulation_id
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            simulation_id = f"{self.config.account_id}_{timestamp}"

            # 获取当前账户资金状态
            account_info = self.trader.query_stock_asset(self.config.account_id)

            if not account_info:
                raise RuntimeError("无法获取账户信息")

            current_capital = account_info.get("total_asset", 0)

            logger.info(
                f"创建模拟盘 - ID: {simulation_id}, "
                f"初始资金: {initial_capital}, "
                f"当前账户资金: {current_capital}, "
                f"运行天数: {duration_days}"
            )

            # 注意：实际的策略启动需要根据QMT的策略运行机制
            # 这里假设策略代码会通过其他方式加载和运行
            # 我们只负责记录和监控

            return simulation_id

        except Exception as e:
            logger.error(f"创建模拟盘失败: {e}")
            raise RuntimeError(f"创建模拟盘失败: {e}") from e

    async def get_simulation_status(self, simulation_id: str) -> SimulationStatus:
        """获取模拟盘状态

        Args:
            simulation_id: 模拟盘ID

        Returns:
            SimulationStatus: 模拟盘状态

        Raises:
            ValueError: 当未连接或simulation_id无效时
        """
        if not self.connected:
            raise ValueError("未连接到QMT，请先调用connect()")

        try:
            # 查询账户资产
            account_info = self.trader.query_stock_asset(self.config.account_id)

            if not account_info:
                raise RuntimeError("无法获取账户信息")

            # 查询持仓
            positions = self.trader.query_stock_positions(self.config.account_id)

            # 查询成交
            trades = self.trader.query_stock_trades(self.config.account_id)

            # 构造状态对象
            status = SimulationStatus(
                simulation_id=simulation_id,
                status="running",  # 简化：假设一直在运行
                start_time=self._parse_simulation_start_time(simulation_id),
                current_capital=account_info.get("total_asset", 0),
                total_pnl=account_info.get("total_asset", 0) - account_info.get("enable_balance", 0),
                position_count=len(positions) if positions else 0,
                trade_count=len(trades) if trades else 0,
                last_update_time=datetime.now(),
            )

            return status

        except Exception as e:
            logger.error(f"获取模拟盘状态失败: {e}")
            raise RuntimeError(f"获取模拟盘状态失败: {e}") from e

    async def get_simulation_data(self, simulation_id: str) -> SimulationData:
        """获取模拟盘数据

        Args:
            simulation_id: 模拟盘ID

        Returns:
            SimulationData: 模拟盘数据

        Raises:
            ValueError: 当未连接或simulation_id无效时
        """
        if not self.connected:
            raise ValueError("未连接到QMT，请先调用connect()")

        try:
            # 查询成交记录
            trades_raw = self.trader.query_stock_trades(self.config.account_id)
            trades = self._format_trades(trades_raw) if trades_raw else []

            # 查询持仓
            positions_raw = self.trader.query_stock_positions(self.config.account_id)
            positions = self._format_positions(positions_raw) if positions_raw else []

            # 查询资金流水（用于计算每日盈亏）
            # 注意：QMT可能没有直接的每日盈亏接口，需要自己计算
            daily_pnl = self._calculate_daily_pnl(simulation_id)

            # 计算绩效指标
            performance_metrics = self._calculate_performance_metrics(trades, positions, daily_pnl)

            data = SimulationData(
                simulation_id=simulation_id,
                trades=trades,
                positions=positions,
                daily_pnl=daily_pnl,
                performance_metrics=performance_metrics,
            )

            return data

        except Exception as e:
            logger.error(f"获取模拟盘数据失败: {e}")
            raise RuntimeError(f"获取模拟盘数据失败: {e}") from e

    async def stop_simulation(self, simulation_id: str) -> bool:
        """停止模拟盘

        注意：QMT模拟盘通常不需要显式停止，
        这里主要是记录停止状态。

        Args:
            simulation_id: 模拟盘ID

        Returns:
            bool: 是否停止成功
        """
        try:
            logger.info(f"停止模拟盘: {simulation_id}")

            # 可以选择清空所有持仓
            # positions = self.trader.query_stock_positions(self.config.account_id)
            # for pos in positions:
            #     # 平仓操作
            #     pass

            return True

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"停止模拟盘失败: {e}")
            return False

    def _parse_simulation_start_time(self, simulation_id: str) -> datetime:
        """从simulation_id解析开始时间

        Args:
            simulation_id: 模拟盘ID（格式：account_timestamp）

        Returns:
            datetime: 开始时间
        """
        try:
            # simulation_id格式：account_YYYYMMDDHHmmss
            timestamp_str = simulation_id.split("_")[-1]
            return datetime.strptime(timestamp_str, "%Y%m%d%H%M%S")
        except Exception:  # pylint: disable=broad-exception-caught
            return datetime.now()

    def _format_trades(self, trades_raw: List[Any]) -> List[Dict[str, Any]]:
        """格式化成交记录

        Args:
            trades_raw: QMT原始成交记录

        Returns:
            List[Dict[str, Any]]: 格式化后的成交记录
        """
        formatted_trades = []

        for trade in trades_raw:
            formatted_trades.append(
                {
                    "trade_id": trade.get("order_id", ""),
                    "stock_code": trade.get("stock_code", ""),
                    "stock_name": trade.get("stock_name", ""),
                    "direction": trade.get("order_type", ""),  # 买/卖
                    "price": trade.get("traded_price", 0),
                    "volume": trade.get("traded_volume", 0),
                    "amount": trade.get("traded_amount", 0),
                    "commission": trade.get("commission", 0),
                    "trade_time": trade.get("traded_time", ""),
                    "status": trade.get("order_status", ""),
                }
            )

        return formatted_trades

    def _format_positions(self, positions_raw: List[Any]) -> List[Dict[str, Any]]:
        """格式化持仓记录

        Args:
            positions_raw: QMT原始持仓记录

        Returns:
            List[Dict[str, Any]]: 格式化后的持仓记录
        """
        formatted_positions = []

        for pos in positions_raw:
            formatted_positions.append(
                {
                    "stock_code": pos.get("stock_code", ""),
                    "stock_name": pos.get("stock_name", ""),
                    "volume": pos.get("volume", 0),
                    "can_use_volume": pos.get("can_use_volume", 0),
                    "open_date": pos.get("open_date", ""),
                    "market_value": pos.get("market_value", 0),
                    "price": pos.get("price", 0),
                    "cost_price": pos.get("cost_price", 0),
                    "profit": pos.get("profit", 0),
                    "profit_ratio": pos.get("profit_ratio", 0),
                }
            )

        return formatted_positions

    def _calculate_daily_pnl(self, simulation_id: str) -> List[float]:  # pylint: disable=unused-argument
        """计算每日盈亏

        注意：这是简化实现，实际需要记录每日资金快照

        Args:
            simulation_id: 模拟盘ID

        Returns:
            List[float]: 每日盈亏列表
        """
        # 简化实现：返回空列表
        # 实际应该从数据库或缓存中读取历史资金数据
        return []

    def _calculate_performance_metrics(
        self, trades: List[Dict[str, Any]], positions: List[Dict[str, Any]], daily_pnl: List[float]
    ) -> Dict[str, float]:
        """计算绩效指标

        Args:
            trades: 成交记录
            positions: 持仓记录
            daily_pnl: 每日盈亏

        Returns:
            Dict[str, float]: 绩效指标
        """
        import numpy as np  # pylint: disable=import-outside-toplevel

        metrics = {}

        # 总收益
        total_profit = sum(pos.get("profit", 0) for pos in positions)
        metrics["total_profit"] = total_profit

        # 总收益率
        total_cost = sum(pos.get("cost_price", 0) * pos.get("volume", 0) for pos in positions)
        if total_cost > 0:
            metrics["total_return"] = total_profit / total_cost
        else:
            metrics["total_return"] = 0.0

        # 胜率
        if trades:
            winning_trades = sum(
                1
                for trade in trades
                if trade.get("direction") == "卖出" and self._is_profitable_trade(trade, positions)
            )
            metrics["win_rate"] = winning_trades / len(trades) if trades else 0.0
        else:
            metrics["win_rate"] = 0.0

        # 夏普比率（简化计算）
        if daily_pnl and len(daily_pnl) > 1:
            returns = np.array(daily_pnl)
            sharpe = np.mean(returns) / np.std(returns) * np.sqrt(252) if np.std(returns) > 0 else 0.0
            metrics["sharpe_ratio"] = sharpe
        else:
            metrics["sharpe_ratio"] = 0.0

        # 最大回撤（简化计算）
        if daily_pnl:
            cumulative = np.cumsum(daily_pnl)
            running_max = np.maximum.accumulate(cumulative)
            drawdown = (cumulative - running_max) / running_max
            metrics["max_drawdown"] = abs(np.min(drawdown)) if len(drawdown) > 0 else 0.0
        else:
            metrics["max_drawdown"] = 0.0

        return metrics

    def _is_profitable_trade(self, trade: Dict[str, Any], positions: List[Dict[str, Any]]) -> bool:
        """判断交易是否盈利

        Args:
            trade: 交易记录
            positions: 持仓记录

        Returns:
            bool: 是否盈利
        """
        # 简化实现：根据持仓的盈亏判断
        stock_code = trade.get("stock_code", "")
        for pos in positions:
            if pos.get("stock_code") == stock_code:
                return pos.get("profit", 0) > 0
        return False


class MockBrokerAPI(BrokerSimulationAPI):
    """Mock券商API实现

    用于开发和测试，模拟券商API的行为。
    """

    def __init__(self):
        """初始化Mock API"""
        self.connected = False
        self.simulations: Dict[str, Dict[str, Any]] = {}

        logger.info("初始化MockBrokerAPI")

    async def connect(self) -> bool:
        """模拟连接

        Returns:
            bool: 总是返回True
        """
        self.connected = True
        logger.info("Mock API连接成功")
        return True

    async def disconnect(self) -> bool:
        """模拟断开连接

        Returns:
            bool: 总是返回True
        """
        self.connected = False
        logger.info("Mock API连接已断开")
        return True

    async def create_simulation(self, strategy_code: str, initial_capital: float, duration_days: int = 30) -> str:
        """模拟创建模拟盘

        Args:
            strategy_code: 策略代码
            initial_capital: 初始资金
            duration_days: 运行天数

        Returns:
            str: 模拟盘ID
        """
        if not self.connected:
            raise ValueError("未连接")

        simulation_id = f"mock_{datetime.now().strftime('%Y%m%d%H%M%S')}"

        self.simulations[simulation_id] = {
            "strategy_code": strategy_code,
            "initial_capital": initial_capital,
            "current_capital": initial_capital,
            "duration_days": duration_days,
            "start_time": datetime.now(),
            "status": "running",
            "trades": [],
            "positions": [],
            "daily_pnl": [],
        }

        logger.info(f"Mock创建模拟盘: {simulation_id}")

        return simulation_id

    async def get_simulation_status(self, simulation_id: str) -> SimulationStatus:
        """模拟获取状态

        Args:
            simulation_id: 模拟盘ID

        Returns:
            SimulationStatus: 模拟盘状态
        """
        if simulation_id not in self.simulations:
            raise ValueError(f"模拟盘不存在: {simulation_id}")

        sim = self.simulations[simulation_id]

        return SimulationStatus(
            simulation_id=simulation_id,
            status=sim["status"],
            start_time=sim["start_time"],
            current_capital=sim["current_capital"],
            total_pnl=sim["current_capital"] - sim["initial_capital"],
            position_count=len(sim["positions"]),
            trade_count=len(sim["trades"]),
            last_update_time=datetime.now(),
        )

    async def get_simulation_data(self, simulation_id: str) -> SimulationData:
        """模拟获取数据

        Args:
            simulation_id: 模拟盘ID

        Returns:
            SimulationData: 模拟盘数据
        """
        if simulation_id not in self.simulations:
            raise ValueError(f"模拟盘不存在: {simulation_id}")

        sim = self.simulations[simulation_id]

        return SimulationData(
            simulation_id=simulation_id,
            trades=sim["trades"],
            positions=sim["positions"],
            daily_pnl=sim["daily_pnl"],
            performance_metrics={"total_return": 0.05, "sharpe_ratio": 1.5, "max_drawdown": 0.10, "win_rate": 0.60},
        )

    async def stop_simulation(self, simulation_id: str) -> bool:
        """模拟停止

        Args:
            simulation_id: 模拟盘ID

        Returns:
            bool: 总是返回True
        """
        if simulation_id in self.simulations:
            self.simulations[simulation_id]["status"] = "stopped"
            logger.info(f"Mock停止模拟盘: {simulation_id}")

        return True
