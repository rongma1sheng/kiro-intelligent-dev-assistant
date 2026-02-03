"""策略基类

白皮书依据: 第四章 4.2 斯巴达竞技场
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from loguru import logger

from src.strategies.data_models import Position, Signal, StrategyConfig


class Strategy(ABC):
    """策略基类

    白皮书依据: 第四章 4.2 斯巴达竞技场

    每个策略都是独立的交易单元，包含完整的风险控制逻辑。
    策略的参数来自Arena测试中的自由进化结果。
    """

    def __init__(self, name: str, config: StrategyConfig):
        """初始化策略

        Args:
            name: 策略名称
            config: 策略配置（Arena进化出的参数）
        """
        self.name = name
        self.config = config
        self.capital_tier = config.capital_tier

        # Arena进化出的参数
        self.stop_loss_pct = config.stop_loss_pct
        self.take_profit_pct = config.take_profit_pct
        self.max_position = config.max_position
        self.max_single_stock = config.max_single_stock
        self.max_industry = config.max_industry
        self.trailing_stop_enabled = config.trailing_stop_enabled

        # 策略状态
        self.is_active = True
        self.current_positions: List[Position] = []

        logger.info(
            f"策略初始化完成 - "
            f"名称: {name}, "
            f"档位: {self.capital_tier}, "
            f"止损: {self.stop_loss_pct*100:.1f}%, "
            f"止盈: {self.take_profit_pct*100:.1f}%"
        )

    @abstractmethod
    async def generate_signals(self, market_data: Dict[str, Any]) -> List[Signal]:
        """生成交易信号

        白皮书依据: Requirement 5.2

        基于市场数据生成买卖信号。这是策略的核心逻辑，
        由具体策略子类实现。

        Args:
            market_data: 市场数据，包含价格、成交量等信息

        Returns:
            交易信号列表
        """

    @abstractmethod
    async def calculate_position_sizes(self, signals: List[Signal]) -> List[Position]:
        """计算仓位大小

        白皮书依据: Requirement 5.3

        根据信号和策略配置计算每个标的的仓位。

        Args:
            signals: 交易信号列表

        Returns:
            仓位列表
        """

    async def apply_risk_controls(self, positions: List[Position]) -> List[Position]:
        """应用风险控制

        白皮书依据: Requirement 5.4

        使用策略风险管理器过滤和调整仓位。
        这个方法有默认实现，但子类可以覆盖。

        Args:
            positions: 原始仓位列表

        Returns:
            过滤后的仓位列表
        """
        # 延迟导入避免循环依赖
        from src.strategies.strategy_risk_manager import StrategyRiskManager  # pylint: disable=import-outside-toplevel

        if not hasattr(self, "risk_manager"):
            self.risk_manager = StrategyRiskManager(self.config)  # pylint: disable=w0201

        filtered_positions = await self.risk_manager.filter_positions(positions)

        logger.info(f"风险控制完成 - " f"原始仓位: {len(positions)}, " f"过滤后: {len(filtered_positions)}")

        return filtered_positions

    async def check_stop_loss(self, current_positions: Optional[List[Position]] = None) -> List[str]:
        """检查止损触发

        白皮书依据: Requirement 5.5

        Args:
            current_positions: 当前仓位列表（可选，默认使用self.current_positions）

        Returns:
            需要止损的标的列表
        """
        from src.strategies.strategy_risk_manager import StrategyRiskManager  # pylint: disable=import-outside-toplevel

        if not hasattr(self, "risk_manager"):
            self.risk_manager = StrategyRiskManager(self.config)  # pylint: disable=w0201

        positions = current_positions if current_positions is not None else self.current_positions

        stop_loss_symbols = await self.risk_manager.check_stop_loss_triggers(positions)

        if stop_loss_symbols:
            logger.warning(f"止损触发 - 标的: {stop_loss_symbols}")

        return stop_loss_symbols

    async def check_take_profit(self, current_positions: Optional[List[Position]] = None) -> List[str]:
        """检查止盈触发

        白皮书依据: Requirement 5.6

        Args:
            current_positions: 当前仓位列表（可选，默认使用self.current_positions）

        Returns:
            需要止盈的标的列表
        """
        from src.strategies.strategy_risk_manager import StrategyRiskManager  # pylint: disable=import-outside-toplevel

        if not hasattr(self, "risk_manager"):
            self.risk_manager = StrategyRiskManager(self.config)  # pylint: disable=w0201

        positions = current_positions if current_positions is not None else self.current_positions

        take_profit_symbols = await self.risk_manager.check_take_profit_triggers(positions)

        if take_profit_symbols:
            logger.info(f"止盈触发 - 标的: {take_profit_symbols}")

        return take_profit_symbols

    def update_positions(self, positions: List[Position]) -> None:
        """更新当前仓位

        Args:
            positions: 新的仓位列表
        """
        self.current_positions = positions
        logger.debug(f"仓位已更新 - 持仓数: {len(positions)}")

    def get_current_positions(self) -> List[Position]:
        """获取当前仓位

        Returns:
            当前仓位列表
        """
        return self.current_positions.copy()

    def activate(self) -> None:
        """激活策略"""
        self.is_active = True
        logger.info(f"策略已激活: {self.name}")

    def deactivate(self) -> None:
        """停用策略"""
        self.is_active = False
        logger.info(f"策略已停用: {self.name}")

    def get_config(self) -> StrategyConfig:
        """获取策略配置

        Returns:
            策略配置
        """
        return self.config

    def update_config(self, new_config: StrategyConfig) -> None:
        """更新策略配置

        Args:
            new_config: 新的策略配置
        """
        self.config = new_config

        # 更新相关参数
        self.capital_tier = new_config.capital_tier
        self.stop_loss_pct = new_config.stop_loss_pct
        self.take_profit_pct = new_config.take_profit_pct
        self.max_position = new_config.max_position
        self.max_single_stock = new_config.max_single_stock
        self.max_industry = new_config.max_industry
        self.trailing_stop_enabled = new_config.trailing_stop_enabled

        # 重新创建风险管理器
        if hasattr(self, "risk_manager"):
            from src.strategies.strategy_risk_manager import (  # pylint: disable=import-outside-toplevel
                StrategyRiskManager,
            )

            self.risk_manager = StrategyRiskManager(new_config)  # pylint: disable=w0201

        logger.info(f"策略配置已更新: {self.name}")

    def __repr__(self) -> str:
        """字符串表示"""
        return (
            f"Strategy(name={self.name}, "
            f"tier={self.capital_tier}, "
            f"active={self.is_active}, "
            f"positions={len(self.current_positions)})"
        )
