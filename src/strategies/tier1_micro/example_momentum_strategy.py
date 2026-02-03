"""示例动量策略 (Tier1 Micro)

白皮书依据: 第四章 4.2 斯巴达竞技场

这是一个简单的动量策略示例，用于演示策略基类的使用。
实际策略的参数应该来自Arena测试中的自由进化结果。
"""

from typing import Any, Dict, List

from loguru import logger

from src.strategies.base_strategy import Strategy
from src.strategies.data_models import Position, Signal, StrategyConfig


class ExampleMomentumStrategy(Strategy):
    """示例动量策略

    白皮书依据: 第四章 4.2 斯巴达竞技场

    策略逻辑：
    - 买入近期涨幅最大的股票
    - 卖出近期跌幅最大的股票
    - 使用Arena进化出的风控参数

    注意：这只是一个演示示例，实际策略应该更复杂，
    并且参数应该来自Arena测试的自由进化结果。
    """

    def __init__(self, name: str, config: StrategyConfig):
        """初始化动量策略

        Args:
            name: 策略名称
            config: 策略配置（Arena进化出的参数）
        """
        super().__init__(name, config)

        # 动量策略特定参数（可以从config中获取）
        self.lookback_days = 20  # 回看天数
        self.top_n = 10  # 选择前N个标的

        logger.info(f"ExampleMomentumStrategy初始化完成 - " f"回看期: {self.lookback_days}天, " f"选股数: {self.top_n}")

    async def generate_signals(self, market_data: Dict[str, Any]) -> List[Signal]:
        """生成交易信号

        白皮书依据: Requirement 5.2

        Args:
            market_data: 市场数据，格式：
                {
                    'prices': {symbol: [price1, price2, ...]},
                    'volumes': {symbol: [vol1, vol2, ...]},
                    'timestamp': '2026-01-20'
                }

        Returns:
            交易信号列表
        """
        signals = []

        try:
            prices = market_data.get("prices", {})
            timestamp = market_data.get("timestamp", "")

            if not prices:
                logger.warning("市场数据为空，无法生成信号")
                return signals

            # 计算动量（简化版：最近N天的收益率）
            momentum_scores = {}
            for symbol, price_list in prices.items():
                if len(price_list) >= self.lookback_days:
                    # 计算动量：(最新价 - N天前价) / N天前价
                    momentum = (price_list[-1] - price_list[-self.lookback_days]) / price_list[-self.lookback_days]
                    momentum_scores[symbol] = momentum

            if not momentum_scores:
                logger.warning("无法计算动量，数据不足")
                return signals

            # 排序：动量从高到低
            sorted_symbols = sorted(momentum_scores.items(), key=lambda x: x[1], reverse=True)

            # 生成买入信号（动量最高的top_n个）
            for symbol, momentum in sorted_symbols[: self.top_n]:
                if momentum > 0:  # 只买入正动量的
                    signal = Signal(
                        symbol=symbol,
                        action="buy",
                        confidence=min(abs(momentum) * 10, 1.0),  # 动量越大，置信度越高
                        timestamp=timestamp,
                        reason=f"正动量: {momentum*100:.2f}%",
                    )
                    signals.append(signal)

            # 生成卖出信号（动量最低的，如果持有的话）
            for symbol, momentum in sorted_symbols[-self.top_n :]:
                if momentum < 0:  # 只卖出负动量的
                    signal = Signal(
                        symbol=symbol,
                        action="sell",
                        confidence=min(abs(momentum) * 10, 1.0),
                        timestamp=timestamp,
                        reason=f"负动量: {momentum*100:.2f}%",
                    )
                    signals.append(signal)

            buy_count = len([s for s in signals if s.action == "buy"])
            sell_count = len([s for s in signals if s.action == "sell"])
            logger.info(f"生成信号完成 - 买入: {buy_count}, 卖出: {sell_count}")

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"生成信号失败: {e}")

        return signals

    async def calculate_position_sizes(self, signals: List[Signal]) -> List[Position]:
        """计算仓位大小

        白皮书依据: Requirement 5.3

        Args:
            signals: 交易信号列表

        Returns:
            仓位列表
        """
        positions = []

        try:
            buy_signals = [s for s in signals if s.action == "buy"]

            if not buy_signals:
                return positions

            # 简单的等权重分配
            # 注意：实际应该根据信号置信度、风险等因素动态调整
            n_positions = len(buy_signals)
            base_size = self.max_position / n_positions if n_positions > 0 else 0

            for signal in buy_signals:
                # 根据置信度调整仓位
                position_size = base_size * signal.confidence

                # 确保不超过单股上限
                position_size = min(position_size, self.max_single_stock)

                # 创建仓位（简化版，实际需要更多信息）
                position = Position(
                    symbol=signal.symbol,
                    size=position_size,
                    entry_price=100.0,  # 简化：实际应该从市场数据获取
                    current_price=100.0,
                    pnl_pct=0.0,
                    holding_days=0,
                    industry="未知",  # 简化：实际应该从市场数据获取
                )
                positions.append(position)

            logger.info(f"仓位计算完成 - 持仓数: {len(positions)}, 总仓位: {sum(p.size for p in positions)*100:.1f}%")

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"仓位计算失败: {e}")

        return positions

    async def apply_risk_controls(self, positions: List[Position]) -> List[Position]:
        """应用风险控制

        白皮书依据: Requirement 5.4

        使用父类的默认实现，调用StrategyRiskManager

        Args:
            positions: 原始仓位列表

        Returns:
            过滤后的仓位列表
        """
        # 调用父类的风险控制
        filtered_positions = await super().apply_risk_controls(positions)

        return filtered_positions


# 工厂函数：从Arena结果创建策略实例
def create_from_arena_result(arena_result: Dict[str, Any]) -> ExampleMomentumStrategy:
    """从Arena测试结果创建策略实例

    Args:
        arena_result: Arena测试结果，包含进化出的参数

    Returns:
        策略实例
    """
    from src.strategies.data_models import ArenaTestResult  # pylint: disable=import-outside-toplevel

    # 转换为ArenaTestResult对象
    if isinstance(arena_result, dict):
        arena_test_result = ArenaTestResult(**arena_result)
    else:
        arena_test_result = arena_result

    # 从Arena结果创建配置
    config = StrategyConfig.from_arena_result(arena_test_result)

    # 创建策略实例
    strategy = ExampleMomentumStrategy(name=arena_test_result.strategy_name, config=config)

    logger.info(f"从Arena结果创建策略: {strategy.name}")

    return strategy
