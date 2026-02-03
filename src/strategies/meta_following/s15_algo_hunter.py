"""S15 Algo Hunter (主力雷达) - 主力行为识别策略

白皮书依据: 第六章 5.2 模块化军火库 - Meta-Following系

策略特点：
- 基于AMD本地模型识别微观盘口
- 检测冰山单与吸筹行为
- 跟随主力建仓
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from loguru import logger

from src.strategies.base_strategy import Strategy
from src.strategies.data_models import Position, Signal, StrategyConfig


class S15AlgoHunterStrategy(Strategy):
    """S15 Algo Hunter (主力雷达) 策略

    白皮书依据: 第六章 5.2 模块化军火库 - Meta-Following系

    策略逻辑：
    1. 基于AMD本地模型分析微观盘口
    2. 识别冰山单、吸筹、洗筹等主力行为
    3. 计算主力概率
    4. 跟随主力建仓

    适用场景：
    - 主力吸筹阶段
    - 盘口异动
    - 量价背离
    """

    def __init__(self, config: StrategyConfig):
        """初始化S15主力雷达策略

        Args:
            config: 策略配置（Arena进化出的参数）
        """
        super().__init__(name="S15_Algo_Hunter", config=config)

        # 策略特有参数
        self.main_force_threshold: float = 0.7  # 主力概率阈值
        self.iceberg_detection_threshold: float = 0.6  # 冰山单检测阈值
        self.accumulation_threshold: float = 0.65  # 吸筹检测阈值
        self.min_signal_duration: int = 5  # 最小信号持续时间（分钟）

        logger.info(
            f"S15_Algo_Hunter策略初始化 - "
            f"主力阈值: {self.main_force_threshold}, "
            f"冰山单阈值: {self.iceberg_detection_threshold}"
        )

    async def generate_signals(self, market_data: Dict[str, Any]) -> List[Signal]:
        """生成交易信号

        白皮书依据: Requirement 5.2

        信号生成逻辑：
        1. 获取AlgoHunter模型输出
        2. 分析主力行为类型
        3. 计算信号强度
        4. 生成跟随信号

        Args:
            market_data: 市场数据
                {
                    'algo_hunter_signals': Dict[str, Dict],  # AlgoHunter信号
                    'tick_data': Dict[str, Dict],  # Tick数据
                    'order_book': Dict[str, Dict]  # 订单簿数据
                }

        Returns:
            交易信号列表
        """
        signals: List[Signal] = []

        algo_signals = market_data.get("algo_hunter_signals", {})
        tick_data = market_data.get("tick_data", {})
        order_book = market_data.get("order_book", {})

        for symbol, algo_data in algo_signals.items():
            try:
                signal = await self._analyze_algo_signal(
                    symbol, algo_data, tick_data.get(symbol, {}), order_book.get(symbol, {})
                )
                if signal:
                    signals.append(signal)
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.warning(f"分析{symbol}主力信号时出错: {e}")
                continue

        # 按置信度排序
        signals = sorted(signals, key=lambda x: x.confidence, reverse=True)[:5]

        logger.info(f"S15_Algo_Hunter生成{len(signals)}个主力雷达信号")
        return signals

    async def _analyze_algo_signal(
        self, symbol: str, algo_data: Dict[str, Any], _tick_data: Dict[str, Any], order_book: Dict[str, Any]
    ) -> Optional[Signal]:
        """分析AlgoHunter信号

        Args:
            symbol: 标的代码
            algo_data: AlgoHunter模型输出
            tick_data: Tick数据
            order_book: 订单簿数据

        Returns:
            交易信号或None
        """
        # 获取AlgoHunter模型输出
        main_force_prob = algo_data.get("main_force_probability", 0)
        behavior_type = algo_data.get("behavior_type", "unknown")
        iceberg_prob = algo_data.get("iceberg_probability", 0)
        accumulation_prob = algo_data.get("accumulation_probability", 0)
        signal_duration = algo_data.get("signal_duration_minutes", 0)

        # 条件1: 主力概率达标
        if main_force_prob < self.main_force_threshold:
            return None

        # 条件2: 信号持续时间达标
        if signal_duration < self.min_signal_duration:
            return None

        # 条件3: 行为类型为买入相关
        bullish_behaviors = {"accumulation", "iceberg_buy", "stealth_buy", "wash_out_end"}
        if behavior_type not in bullish_behaviors:
            return None

        # 分析订单簿
        bid_strength = self._analyze_order_book(order_book)

        # 计算置信度
        confidence = self._calculate_algo_confidence(
            main_force_prob, behavior_type, iceberg_prob, accumulation_prob, bid_strength
        )

        reason = (
            f"主力概率{main_force_prob*100:.1f}%, "
            f"行为: {behavior_type}, "
            f"持续{signal_duration}分钟, "
            f"买盘强度{bid_strength:.2f}"
        )

        logger.info(f"S15_Algo_Hunter主力信号 - {symbol}: {reason}")

        return Signal(
            symbol=symbol, action="buy", confidence=confidence, timestamp=datetime.now().isoformat(), reason=reason
        )

    def _analyze_order_book(self, order_book: Dict[str, Any]) -> float:
        """分析订单簿强度

        Args:
            order_book: 订单簿数据

        Returns:
            买盘强度 (0.0-1.0)
        """
        bid_volume = order_book.get("total_bid_volume", 0)
        ask_volume = order_book.get("total_ask_volume", 1)

        # 买卖比
        bid_ask_ratio = bid_volume / ask_volume if ask_volume > 0 else 1.0

        # 转换为0-1的强度值
        strength = min(1.0, bid_ask_ratio / 2.0)

        return strength

    def _calculate_algo_confidence(  # pylint: disable=too-many-positional-arguments
        self,
        main_force_prob: float,
        behavior_type: str,
        iceberg_prob: float,
        accumulation_prob: float,
        bid_strength: float,
    ) -> float:
        """计算主力信号置信度

        Args:
            main_force_prob: 主力概率
            behavior_type: 行为类型
            iceberg_prob: 冰山单概率
            accumulation_prob: 吸筹概率
            bid_strength: 买盘强度

        Returns:
            置信度 (0.0-1.0)
        """
        # 主力概率得分 (0-0.35)
        main_force_score = min(0.35, (main_force_prob - 0.7) * 1.17)

        # 行为类型得分 (0-0.25)
        behavior_scores = {"accumulation": 0.25, "iceberg_buy": 0.22, "stealth_buy": 0.20, "wash_out_end": 0.18}
        behavior_score = behavior_scores.get(behavior_type, 0.10)

        # 冰山单/吸筹得分 (0-0.20)
        special_score = min(0.20, max(iceberg_prob, accumulation_prob) * 0.25)

        # 买盘强度得分 (0-0.15)
        bid_score = min(0.15, bid_strength * 0.15)

        confidence = main_force_score + behavior_score + special_score + bid_score
        confidence = max(0.5, min(0.90, confidence + 0.35))

        return confidence

    async def calculate_position_sizes(self, signals: List[Signal]) -> List[Position]:
        """计算仓位大小

        白皮书依据: Requirement 5.3

        主力雷达策略特点：
        - 快速响应
        - 仓位适中
        - 跟随主力节奏

        Args:
            signals: 交易信号列表

        Returns:
            仓位列表
        """
        positions: List[Position] = []

        sorted_signals = sorted(signals, key=lambda x: x.confidence, reverse=True)

        total_allocated = 0.0
        max_total = min(self.max_position, 0.40)  # 主力雷达策略总仓位上限40%

        for signal in sorted_signals:
            if signal.action != "buy":
                continue

            base_size = self.max_single_stock * signal.confidence

            if total_allocated + base_size > max_total:
                base_size = max_total - total_allocated

            if base_size <= 0.01:
                break

            position = Position(
                symbol=signal.symbol,
                size=base_size,
                entry_price=100.0,  # 占位价格，实际交易时会更新
                current_price=100.0,  # 占位价格，实际交易时会更新
                pnl_pct=0.0,
                holding_days=0,
                industry="unknown",
            )

            positions.append(position)
            total_allocated += base_size

        logger.info(
            f"S15_Algo_Hunter仓位计算完成 - " f"标的数: {len(positions)}, " f"总仓位: {total_allocated*100:.2f}%"
        )

        return positions
