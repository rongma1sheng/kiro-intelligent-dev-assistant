"""风险因子注册中心

白皮书依据: 第四章 4.1.1 专业风险因子挖掘系统 - 统一接口

该模块实现风险因子注册中心，提供统一的风险因子管理接口：
1. 注册风险因子挖掘器
2. 收集风险因子
3. 查询最新因子
4. 发布风险因子事件
"""

from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional

from loguru import logger

from src.evolution.risk_mining.risk_factor import RiskEvent, RiskEventType, RiskFactor
from src.infra.event_bus import Event, EventBus, EventType


class RiskFactorRegistry:
    """风险因子注册中心

    白皮书依据: 第四章 4.1.1 专业风险因子挖掘系统 - 统一接口

    提供统一的风险因子管理接口，负责：
    - 注册和管理风险因子挖掘器
    - 收集和存储风险因子
    - 提供因子查询接口
    - 通过事件总线发布风险因子

    Attributes:
        event_bus: 事件总线实例
        miners: 注册的挖掘器列表
        factors: 风险因子存储 {symbol: [RiskFactor]}
        max_factors_per_symbol: 每个标的最大因子数量
    """

    def __init__(self, event_bus: EventBus, max_factors_per_symbol: int = 100):
        """初始化风险因子注册中心

        Args:
            event_bus: 事件总线实例
            max_factors_per_symbol: 每个标的最大因子数量，默认100

        Raises:
            ValueError: 当event_bus为None时
            ValueError: 当max_factors_per_symbol <= 0时
        """
        if event_bus is None:
            raise ValueError("event_bus不能为None")

        if max_factors_per_symbol <= 0:
            raise ValueError(f"max_factors_per_symbol必须大于0，当前值: {max_factors_per_symbol}")

        self.event_bus = event_bus
        self.max_factors_per_symbol = max_factors_per_symbol

        # 注册的挖掘器列表
        self.miners: List[Any] = []

        # 风险因子存储 {symbol: [RiskFactor]}
        self.factors: Dict[str, List[RiskFactor]] = defaultdict(list)

        # 统计信息
        self.stats = {
            "miners_registered": 0,
            "factors_collected": 0,
            "factors_published": 0,
            "queries_executed": 0,
            "start_time": datetime.now(),
        }

        logger.info(f"初始化RiskFactorRegistry: " f"max_factors_per_symbol={max_factors_per_symbol}")

    def register_miner(self, miner: Any) -> None:
        """注册风险因子挖掘器

        白皮书依据: 第四章 4.1.1 - 挖掘器注册

        Args:
            miner: 风险因子挖掘器实例

        Raises:
            ValueError: 当miner为None时
            ValueError: 当miner已经注册时
        """
        if miner is None:
            raise ValueError("miner不能为None")

        if miner in self.miners:
            raise ValueError("挖掘器已经注册")

        self.miners.append(miner)
        self.stats["miners_registered"] += 1

        miner_type = type(miner).__name__
        logger.info(f"注册风险因子挖掘器: {miner_type}")

    def unregister_miner(self, miner: Any) -> bool:
        """取消注册风险因子挖掘器

        Args:
            miner: 风险因子挖掘器实例

        Returns:
            是否成功取消注册
        """
        if miner in self.miners:
            self.miners.remove(miner)
            self.stats["miners_registered"] -= 1

            miner_type = type(miner).__name__
            logger.info(f"取消注册风险因子挖掘器: {miner_type}")
            return True

        return False

    async def collect_factors(self, symbol: str) -> List[RiskFactor]:
        """收集指定标的的所有风险因子

        白皮书依据: 第四章 4.1.1 - 因子收集

        从存储中获取指定标的的所有风险因子，按时间戳降序排列。

        Args:
            symbol: 标的代码

        Returns:
            风险因子列表，按时间戳降序排列

        Raises:
            ValueError: 当symbol为空时
        """
        if not symbol:
            raise ValueError("symbol不能为空")

        self.stats["queries_executed"] += 1

        # 获取因子列表
        factors = self.factors.get(symbol, [])

        # 按时间戳降序排列
        sorted_factors = sorted(factors, key=lambda f: f.timestamp, reverse=True)

        logger.debug(f"收集风险因子: symbol={symbol}, " f"count={len(sorted_factors)}")

        return sorted_factors

    async def get_latest_factor(self, symbol: str, factor_type: str) -> Optional[RiskFactor]:
        """获取最新的风险因子

        白皮书依据: 第四章 4.1.1 - 因子查询

        获取指定标的和类型的最新风险因子。

        Args:
            symbol: 标的代码
            factor_type: 因子类型 (flow/microstructure/portfolio)

        Returns:
            最新的风险因子，如果不存在返回None

        Raises:
            ValueError: 当symbol为空时
            ValueError: 当factor_type无效时
        """
        if not symbol:
            raise ValueError("symbol不能为空")

        if factor_type not in ["flow", "microstructure", "portfolio"]:
            raise ValueError(f"无效的factor_type: {factor_type}，" f"必须是 flow/microstructure/portfolio")

        self.stats["queries_executed"] += 1

        # 获取因子列表
        factors = self.factors.get(symbol, [])

        # 过滤指定类型的因子
        typed_factors = [f for f in factors if f.factor_type == factor_type]

        if not typed_factors:
            logger.debug(f"未找到风险因子: symbol={symbol}, " f"factor_type={factor_type}")
            return None

        # 返回最新的因子
        latest_factor = max(typed_factors, key=lambda f: f.timestamp)

        logger.debug(
            f"获取最新风险因子: symbol={symbol}, "
            f"factor_type={factor_type}, "
            f"risk_value={latest_factor.risk_value:.4f}"
        )

        return latest_factor

    async def add_factor(self, factor: RiskFactor) -> None:
        """添加风险因子到存储

        白皮书依据: 第四章 4.1.1 - 因子存储

        将风险因子添加到存储，并通过事件总线发布。
        如果因子数量超过限制，删除最旧的因子。

        Args:
            factor: 风险因子

        Raises:
            ValueError: 当factor为None时
        """
        if factor is None:
            raise ValueError("factor不能为None")

        symbol = factor.symbol

        # 添加到存储
        self.factors[symbol].append(factor)
        self.stats["factors_collected"] += 1

        # 限制因子数量
        if len(self.factors[symbol]) > self.max_factors_per_symbol:
            # 按时间戳排序
            self.factors[symbol].sort(key=lambda f: f.timestamp)
            # 删除最旧的因子
            removed_factor = self.factors[symbol].pop(0)
            logger.debug(f"删除最旧的风险因子: symbol={symbol}, " f"timestamp={removed_factor.timestamp}")

        # 发布风险因子事件
        await self._publish_factor_event(factor)

        logger.info(
            f"添加风险因子: symbol={symbol}, "
            f"factor_type={factor.factor_type}, "
            f"risk_value={factor.risk_value:.4f}, "
            f"total_factors={len(self.factors[symbol])}"
        )

    async def _publish_factor_event(self, factor: RiskFactor) -> None:
        """发布风险因子事件

        白皮书依据: 第四章 4.1.1 - 事件发布

        通过事件总线发布风险因子生成事件。

        Args:
            factor: 风险因子
        """
        try:
            # 创建风险事件
            risk_event = RiskEvent(
                event_type=RiskEventType.RISK_FACTOR_GENERATED,
                symbol=factor.symbol,
                factor=factor,
                timestamp=datetime.now(),
            )

            # 发布到事件总线
            event = Event(
                event_type=EventType.SYSTEM_ALERT,  # 使用系统告警类型
                source_module="risk_factor_registry",
                data={
                    "risk_event_type": risk_event.event_type.value,
                    "symbol": risk_event.symbol,
                    "factor_type": factor.factor_type,
                    "risk_value": factor.risk_value,
                    "confidence": factor.confidence,
                    "metadata": factor.metadata,
                },
            )

            await self.event_bus.publish(event)
            self.stats["factors_published"] += 1

            logger.debug(f"发布风险因子事件: symbol={factor.symbol}, " f"factor_type={factor.factor_type}")

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"发布风险因子事件失败: {e}")

    def get_registered_miners(self) -> List[str]:
        """获取已注册的挖掘器列表

        Returns:
            挖掘器类型名称列表
        """
        return [type(miner).__name__ for miner in self.miners]

    def get_factor_count(self, symbol: Optional[str] = None) -> int:
        """获取因子数量

        Args:
            symbol: 标的代码，None表示获取所有因子数量

        Returns:
            因子数量
        """
        if symbol:  # pylint: disable=no-else-return
            return len(self.factors.get(symbol, []))
        else:
            return sum(len(factors) for factors in self.factors.values())

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息

        Returns:
            统计信息字典
        """
        uptime = (datetime.now() - self.stats["start_time"]).total_seconds()

        return {
            **self.stats,
            "uptime_seconds": uptime,
            "total_factors": self.get_factor_count(),
            "symbols_tracked": len(self.factors),
            "factors_per_second": self.stats["factors_collected"] / max(uptime, 1),
        }

    def clear_factors(self, symbol: Optional[str] = None) -> int:
        """清除风险因子

        Args:
            symbol: 标的代码，None表示清除所有因子

        Returns:
            清除的因子数量
        """
        if symbol:  # pylint: disable=no-else-return
            count = len(self.factors.get(symbol, []))
            if symbol in self.factors:
                del self.factors[symbol]
            logger.info(f"清除风险因子: symbol={symbol}, count={count}")
            return count
        else:
            count = self.get_factor_count()
            self.factors.clear()
            logger.info(f"清除所有风险因子: count={count}")
            return count
