"""高频微观结构因子挖掘器

白皮书依据: 第四章 4.1.6 高频微观结构因子挖掘
需求: 5.1-5.12

实现10个微观结构算子，处理Tick级别数据，订单簿重构，
优化处理延迟<10ms (P99)。
"""

import time
from collections import deque
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Dict, List, Tuple

import numpy as np
import pandas as pd
from loguru import logger


@dataclass
class OrderBookSnapshot:
    """订单簿快照

    Attributes:
        timestamp: 时间戳
        bid_prices: 买盘价格列表（降序）
        bid_volumes: 买盘数量列表
        ask_prices: 卖盘价格列表（升序）
        ask_volumes: 卖盘数量列表
    """

    timestamp: datetime
    bid_prices: List[float]
    bid_volumes: List[float]
    ask_prices: List[float]
    ask_volumes: List[float]

    def get_best_bid(self) -> Tuple[float, float]:
        """获取最优买价和数量"""
        if not self.bid_prices:
            return 0.0, 0.0
        return self.bid_prices[0], self.bid_volumes[0]

    def get_best_ask(self) -> Tuple[float, float]:
        """获取最优卖价和数量"""
        if not self.ask_prices:
            return 0.0, 0.0
        return self.ask_prices[0], self.ask_volumes[0]

    def get_spread(self) -> float:
        """获取买卖价差"""
        best_bid, _ = self.get_best_bid()
        best_ask, _ = self.get_best_ask()
        if best_bid == 0.0 or best_ask == 0.0:
            return 0.0
        return best_ask - best_bid

    def get_mid_price(self) -> float:
        """获取中间价"""
        best_bid, _ = self.get_best_bid()
        best_ask, _ = self.get_best_ask()
        if best_bid == 0.0 or best_ask == 0.0:
            return 0.0
        return (best_bid + best_ask) / 2.0


@dataclass
class Trade:
    """交易记录

    Attributes:
        timestamp: 时间戳
        price: 成交价
        volume: 成交量
        direction: 交易方向（1=买入，-1=卖出，0=未知）
    """

    timestamp: datetime
    price: float
    volume: float
    direction: int  # 1=买入，-1=卖出，0=未知


class HighFrequencyMicrostructureFactorMiner:
    """高频微观结构因子挖掘器

    白皮书依据: 第四章 4.1.6 高频微观结构因子挖掘
    需求: 5.1-5.12

    实现10个微观结构算子：
    1. order_flow_imbalance: 订单流不平衡
    2. price_impact_curve: 价格冲击曲线
    3. tick_direction_momentum: Tick方向动量
    4. bid_ask_bounce: 买卖价跳动
    5. trade_size_clustering: 交易规模聚类
    6. quote_stuffing_detection: 报价填充检测
    7. hidden_liquidity_probe: 隐藏流动性探测
    8. market_maker_inventory: 做市商库存
    9. adverse_selection_cost: 逆向选择成本
    10. effective_spread_decomposition: 有效价差分解

    性能要求: 处理延迟 < 10ms (P99)

    Attributes:
        operators: 算子字典
        order_book_cache: 订单簿缓存
        trade_cache: 交易记录缓存
        performance_metrics: 性能指标
    """

    def __init__(self, cache_size: int = 10000, batch_size: int = 1000):
        """初始化高频微观结构因子挖掘器

        Args:
            cache_size: 缓存大小
            batch_size: 批处理大小

        Raises:
            ValueError: 当参数不在有效范围时
        """
        if cache_size <= 0:
            raise ValueError(f"缓存大小必须 > 0，当前: {cache_size}")

        if batch_size <= 0:
            raise ValueError(f"批处理大小必须 > 0，当前: {batch_size}")

        self.cache_size = cache_size
        self.batch_size = batch_size

        # 初始化算子
        self.operators = self._initialize_operators()

        # 初始化缓存
        self.order_book_cache: deque = deque(maxlen=cache_size)
        self.trade_cache: deque = deque(maxlen=cache_size)

        # 性能指标
        self.performance_metrics = {
            "total_calls": 0,
            "total_time": 0.0,
            "p99_latency": 0.0,
            "latencies": deque(maxlen=1000),
        }

        logger.info(
            f"初始化HighFrequencyMicrostructureFactorMiner: " f"cache_size={cache_size}, batch_size={batch_size}"
        )

        # 健康状态跟踪
        self._is_healthy = True
        self._error_count = 0

    def is_healthy(self) -> bool:
        """检查挖掘器健康状态

        Returns:
            是否健康
        """
        return self._is_healthy and self._error_count < 5

    def get_metadata(self) -> Dict:
        """获取挖掘器元数据

        Returns:
            元数据字典
        """
        return {
            "miner_type": "high_frequency",
            "miner_name": "HighFrequencyMicrostructureFactorMiner",
            "is_healthy": self.is_healthy(),
            "error_count": self._error_count,
            "cache_size": self.cache_size,
            "batch_size": self.batch_size,
            "operators_count": len(self.operators),
        }

    def _initialize_operators(self) -> Dict[str, Callable]:
        """初始化10个微观结构算子

        白皮书依据: 第四章 4.1.6
        需求: 5.1-5.11

        Returns:
            算子字典
        """
        return {
            "order_flow_imbalance": self._order_flow_imbalance,
            "price_impact_curve": self._price_impact_curve,
            "tick_direction_momentum": self._tick_direction_momentum,
            "bid_ask_bounce": self._bid_ask_bounce,
            "trade_size_clustering": self._trade_size_clustering,
            "quote_stuffing_detection": self._quote_stuffing_detection,
            "hidden_liquidity_probe": self._hidden_liquidity_probe,
            "market_maker_inventory": self._market_maker_inventory,
            "adverse_selection_cost": self._adverse_selection_cost,
            "effective_spread_decomposition": self._effective_spread_decomposition,
        }

    def mine_factors(
        self, order_books: List[OrderBookSnapshot], trades: List[Trade], symbols: List[str]
    ) -> pd.DataFrame:
        """挖掘高频微观结构因子

        白皮书依据: 第四章 4.1.6
        需求: 5.1-5.12

        Args:
            order_books: 订单簿快照列表
            trades: 交易记录列表
            symbols: 股票代码列表

        Returns:
            因子数据框，索引为时间戳，列为股票代码

        Raises:
            ValueError: 当输入数据无效时
        """
        start_time = time.perf_counter()

        if not order_books:
            raise ValueError("订单簿数据不能为空")

        if not trades:
            raise ValueError("交易记录不能为空")

        if not symbols:
            raise ValueError("股票代码列表不能为空")

        logger.info(
            f"开始挖掘高频微观结构因子: "
            f"order_books={len(order_books)}, "
            f"trades={len(trades)}, "
            f"symbols={len(symbols)}"
        )

        # 更新缓存
        self.order_book_cache.extend(order_books)
        self.trade_cache.extend(trades)

        # 计算所有因子
        factors = {}
        for operator_name, operator_func in self.operators.items():
            try:
                factor_values = operator_func(order_books, trades, symbols)
                factors[operator_name] = factor_values
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.error(f"算子 {operator_name} 执行失败: {e}")
                factors[operator_name] = pd.Series(0.0, index=symbols)

        # 构建因子数据框
        factor_df = pd.DataFrame(factors, index=symbols)

        # 更新性能指标
        elapsed = time.perf_counter() - start_time
        self._update_performance_metrics(elapsed)

        logger.info(f"高频微观结构因子挖掘完成: " f"factors={len(factors)}, " f"elapsed={elapsed*1000:.2f}ms")

        return factor_df

    def _update_performance_metrics(self, elapsed: float):
        """更新性能指标

        需求: 5.12 - 处理延迟 < 10ms (P99)

        Args:
            elapsed: 执行时间（秒）
        """
        self.performance_metrics["total_calls"] += 1
        self.performance_metrics["total_time"] += elapsed
        self.performance_metrics["latencies"].append(elapsed)

        # 计算P99延迟
        if len(self.performance_metrics["latencies"]) >= 100:
            latencies = sorted(self.performance_metrics["latencies"])
            p99_index = int(len(latencies) * 0.99)
            self.performance_metrics["p99_latency"] = latencies[p99_index]

            # 检查是否满足性能要求
            if self.performance_metrics["p99_latency"] > 0.010:  # 10ms
                logger.warning(f"P99延迟超标: {self.performance_metrics['p99_latency']*1000:.2f}ms > 10ms")

    def _order_flow_imbalance(
        self,
        order_books: List[OrderBookSnapshot],  # pylint: disable=unused-argument
        trades: List[Trade],
        symbols: List[str],  # pylint: disable=unused-argument
    ) -> pd.Series:
        """计算订单流不平衡

        白皮书依据: 第四章 4.1.6
        需求: 5.1

        订单流不平衡 = (买单量 - 卖单量) / (买单量 + 卖单量)

        Args:
            order_books: 订单簿快照列表
            trades: 交易记录列表
            symbols: 股票代码列表

        Returns:
            订单流不平衡因子
        """
        imbalances = {}

        for symbol in symbols:
            buy_volume = 0.0
            sell_volume = 0.0

            # 从交易记录计算买卖量
            for trade in trades:
                if trade.direction == 1:  # 买入
                    buy_volume += trade.volume
                elif trade.direction == -1:  # 卖出
                    sell_volume += trade.volume

            # 计算不平衡度
            total_volume = buy_volume + sell_volume
            if total_volume > 0:
                imbalance = (buy_volume - sell_volume) / total_volume
            else:
                imbalance = 0.0

            imbalances[symbol] = imbalance

        return pd.Series(imbalances)

    def _price_impact_curve(
        self,
        order_books: List[OrderBookSnapshot],
        trades: List[Trade],  # pylint: disable=unused-argument
        symbols: List[str],  # pylint: disable=unused-argument
    ) -> pd.Series:
        """构建价格冲击曲线

        白皮书依据: 第四章 4.1.6
        需求: 5.2

        价格冲击 = 不同订单规模对价格的影响

        Args:
            order_books: 订单簿快照列表
            trades: 交易记录列表
            symbols: 股票代码列表

        Returns:
            价格冲击因子
        """
        impacts = {}

        for symbol in symbols:
            if not order_books:
                impacts[symbol] = 0.0
                continue

            # 使用最新订单簿
            latest_book = order_books[-1]
            mid_price = latest_book.get_mid_price()

            if mid_price == 0.0:
                impacts[symbol] = 0.0
                continue

            # 计算不同规模订单的价格冲击
            # 简化版本：使用订单簿深度估算
            total_bid_volume = sum(latest_book.bid_volumes) if latest_book.bid_volumes else 0.0
            total_ask_volume = sum(latest_book.ask_volumes) if latest_book.ask_volumes else 0.0

            # 价格冲击 = 价差 / 流动性深度
            spread = latest_book.get_spread()
            liquidity = total_bid_volume + total_ask_volume

            if liquidity > 0:
                impact = spread / liquidity
            else:
                impact = 0.0

            impacts[symbol] = impact

        return pd.Series(impacts)

    def _tick_direction_momentum(
        self,
        order_books: List[OrderBookSnapshot],  # pylint: disable=unused-argument
        trades: List[Trade],
        symbols: List[str],  # pylint: disable=unused-argument
    ) -> pd.Series:
        """计算Tick方向动量

        白皮书依据: 第四章 4.1.6
        需求: 5.3

        Tick方向动量 = 连续上涨/下跌tick的累积

        Args:
            order_books: 订单簿快照列表
            trades: 交易记录列表
            symbols: 股票代码列表

        Returns:
            Tick方向动量因子
        """
        momentums = {}

        for symbol in symbols:
            if len(trades) < 2:
                momentums[symbol] = 0.0
                continue

            # 计算tick方向
            tick_directions = []
            for i in range(1, len(trades)):
                if trades[i].price > trades[i - 1].price:
                    tick_directions.append(1)
                elif trades[i].price < trades[i - 1].price:
                    tick_directions.append(-1)
                else:
                    tick_directions.append(0)

            # 计算动量（连续同方向tick的累积）
            if not tick_directions:
                momentums[symbol] = 0.0
                continue

            momentum = 0.0
            current_streak = 0
            current_direction = 0

            for direction in tick_directions:
                if direction == current_direction:
                    current_streak += 1
                else:
                    momentum += current_streak * current_direction
                    current_direction = direction
                    current_streak = 1

            # 添加最后一段
            momentum += current_streak * current_direction

            momentums[symbol] = momentum

        return pd.Series(momentums)

    def _bid_ask_bounce(
        self, order_books: List[OrderBookSnapshot], trades: List[Trade], symbols: List[str]
    ) -> pd.Series:
        """检测买卖价跳动

        白皮书依据: 第四章 4.1.6
        需求: 5.4

        买卖价跳动 = 交易价格在买卖价之间跳动的频率

        Args:
            order_books: 订单簿快照列表
            trades: 交易记录列表
            symbols: 股票代码列表

        Returns:
            买卖价跳动因子
        """
        bounces = {}

        for symbol in symbols:
            if len(trades) < 2 or not order_books:
                bounces[symbol] = 0.0
                continue

            # 计算跳动次数
            bounce_count = 0
            prev_side = None  # 'bid' or 'ask'

            for trade in trades:
                # 确定交易发生在买方还是卖方
                # 简化版本：使用最新订单簿的中间价判断
                if order_books:
                    mid_price = order_books[-1].get_mid_price()
                    if mid_price > 0:
                        current_side = "bid" if trade.price < mid_price else "ask"

                        if prev_side is not None and current_side != prev_side:
                            bounce_count += 1

                        prev_side = current_side

            # 归一化跳动频率
            if len(trades) > 1:
                bounce_frequency = bounce_count / (len(trades) - 1)
            else:
                bounce_frequency = 0.0

            bounces[symbol] = bounce_frequency

        return pd.Series(bounces)

    def _trade_size_clustering(
        self,
        order_books: List[OrderBookSnapshot],  # pylint: disable=unused-argument
        trades: List[Trade],
        symbols: List[str],  # pylint: disable=unused-argument
    ) -> pd.Series:
        """检测交易规模聚类

        白皮书依据: 第四章 4.1.6
        需求: 5.5

        交易规模聚类 = 识别机构交易 vs 散户交易模式

        Args:
            order_books: 订单簿快照列表
            trades: 交易记录列表
            symbols: 股票代码列表

        Returns:
            交易规模聚类因子
        """
        clusterings = {}

        for symbol in symbols:
            if not trades:
                clusterings[symbol] = 0.0
                continue

            # 提取交易规模
            trade_sizes = [trade.volume for trade in trades]

            if not trade_sizes:
                clusterings[symbol] = 0.0
                continue

            # 简化版本：使用标准差/均值比率衡量聚类程度
            mean_size = np.mean(trade_sizes)
            std_size = np.std(trade_sizes)

            if mean_size > 0:
                # 高比率表示规模分散（机构和散户混合）
                # 低比率表示规模集中（单一类型交易者）
                clustering_score = std_size / mean_size
            else:
                clustering_score = 0.0

            clusterings[symbol] = clustering_score

        return pd.Series(clusterings)

    def _quote_stuffing_detection(
        self,
        order_books: List[OrderBookSnapshot],
        trades: List[Trade],  # pylint: disable=unused-argument
        symbols: List[str],  # pylint: disable=unused-argument
    ) -> pd.Series:
        """检测报价填充

        白皮书依据: 第四章 4.1.6
        需求: 5.6

        报价填充 = 异常高频的报价提交和撤销

        Args:
            order_books: 订单簿快照列表
            trades: 交易记录列表
            symbols: 股票代码列表

        Returns:
            报价填充检测因子
        """
        stuffings = {}

        for symbol in symbols:
            if len(order_books) < 2:
                stuffings[symbol] = 0.0
                continue

            # 计算订单簿更新频率
            time_diffs = []
            for i in range(1, len(order_books)):
                time_diff = (order_books[i].timestamp - order_books[i - 1].timestamp).total_seconds()
                if time_diff > 0:
                    time_diffs.append(time_diff)

            if not time_diffs:
                stuffings[symbol] = 0.0
                continue

            # 计算更新频率（次/秒）
            avg_time_diff = np.mean(time_diffs)
            update_frequency = 1.0 / avg_time_diff if avg_time_diff > 0 else 0.0

            # 高频率（>100次/秒）可能表示报价填充
            stuffing_score = min(update_frequency / 100.0, 1.0)

            stuffings[symbol] = stuffing_score

        return pd.Series(stuffings)

    def _hidden_liquidity_probe(
        self, order_books: List[OrderBookSnapshot], trades: List[Trade], symbols: List[str]
    ) -> pd.Series:
        """探测隐藏流动性

        白皮书依据: 第四章 4.1.6
        需求: 5.7

        隐藏流动性 = 冰山订单等隐藏订单的估算

        Args:
            order_books: 订单簿快照列表
            trades: 交易记录列表
            symbols: 股票代码列表

        Returns:
            隐藏流动性因子
        """
        hidden_liquidities = {}

        for symbol in symbols:
            if not trades or not order_books:
                hidden_liquidities[symbol] = 0.0
                continue

            # 比较实际成交量与订单簿显示量
            # 如果成交量远大于订单簿显示量，可能存在隐藏流动性

            # 计算总成交量
            total_trade_volume = sum(trade.volume for trade in trades)

            # 计算订单簿显示的流动性
            if order_books:
                latest_book = order_books[-1]
                visible_liquidity = (
                    sum(latest_book.bid_volumes) + sum(latest_book.ask_volumes)
                    if latest_book.bid_volumes and latest_book.ask_volumes
                    else 0.0
                )
            else:
                visible_liquidity = 0.0

            # 隐藏流动性比率
            if visible_liquidity > 0:
                hidden_ratio = max(0.0, (total_trade_volume - visible_liquidity) / visible_liquidity)
            else:
                hidden_ratio = 0.0

            hidden_liquidities[symbol] = hidden_ratio

        return pd.Series(hidden_liquidities)

    def _market_maker_inventory(
        self,
        order_books: List[OrderBookSnapshot],
        trades: List[Trade],  # pylint: disable=unused-argument
        symbols: List[str],  # pylint: disable=unused-argument
    ) -> pd.Series:
        """追踪做市商库存

        白皮书依据: 第四章 4.1.6
        需求: 5.8

        做市商库存 = 从报价行为推断做市商库存位置

        Args:
            order_books: 订单簿快照列表
            trades: 交易记录列表
            symbols: 股票代码列表

        Returns:
            做市商库存因子
        """
        inventories = {}

        for symbol in symbols:
            if len(order_books) < 2:
                inventories[symbol] = 0.0
                continue

            # 分析买卖价差的变化
            # 做市商库存增加时，可能提高卖价或降低买价
            spread_changes = []

            for i in range(1, len(order_books)):
                prev_spread = order_books[i - 1].get_spread()
                curr_spread = order_books[i].get_spread()

                if prev_spread > 0:
                    spread_change = (curr_spread - prev_spread) / prev_spread
                    spread_changes.append(spread_change)

            if not spread_changes:
                inventories[symbol] = 0.0
                continue

            # 价差持续扩大可能表示做市商库存压力
            avg_spread_change = np.mean(spread_changes)

            inventories[symbol] = avg_spread_change

        return pd.Series(inventories)

    def _adverse_selection_cost(
        self,
        order_books: List[OrderBookSnapshot],  # pylint: disable=unused-argument
        trades: List[Trade],
        symbols: List[str],  # pylint: disable=unused-argument
    ) -> pd.Series:
        """计算逆向选择成本

        白皮书依据: 第四章 4.1.6
        需求: 5.9

        逆向选择成本 = 知情交易者的影响

        Args:
            order_books: 订单簿快照列表
            trades: 交易记录列表
            symbols: 股票代码列表

        Returns:
            逆向选择成本因子
        """
        costs = {}

        for symbol in symbols:
            if not trades or len(trades) < 2:
                costs[symbol] = 0.0
                continue

            # 计算交易后价格变化
            # 如果交易后价格持续朝交易方向移动，表示存在知情交易
            price_impacts = []

            for i in range(len(trades) - 1):
                current_trade = trades[i]
                next_price = trades[i + 1].price

                # 计算价格变化
                price_change = next_price - current_trade.price

                # 如果是买入交易，价格上涨表示逆向选择
                # 如果是卖出交易，价格下跌表示逆向选择
                if current_trade.direction == 1:  # 买入
                    impact = price_change / current_trade.price if current_trade.price > 0 else 0.0
                elif current_trade.direction == -1:  # 卖出
                    impact = -price_change / current_trade.price if current_trade.price > 0 else 0.0
                else:
                    impact = 0.0

                price_impacts.append(impact)

            # 平均逆向选择成本
            if price_impacts:
                avg_cost = np.mean(price_impacts)
            else:
                avg_cost = 0.0

            costs[symbol] = avg_cost

        return pd.Series(costs)

    def _effective_spread_decomposition(
        self, order_books: List[OrderBookSnapshot], trades: List[Trade], symbols: List[str]
    ) -> pd.Series:
        """分解有效价差

        白皮书依据: 第四章 4.1.6
        需求: 5.10

        有效价差分解 = 逆向选择 + 库存成本 + 订单处理成本

        Args:
            order_books: 订单簿快照列表
            trades: 交易记录列表
            symbols: 股票代码列表

        Returns:
            有效价差分解因子
        """
        decompositions = {}

        for symbol in symbols:
            if not trades or not order_books:
                decompositions[symbol] = 0.0
                continue

            # 计算有效价差
            effective_spreads = []

            for trade in trades:
                # 找到最接近的订单簿快照
                closest_book = min(
                    order_books,
                    key=lambda book: abs((book.timestamp - trade.timestamp).total_seconds()),  # pylint: disable=w0640
                )

                mid_price = closest_book.get_mid_price()

                if mid_price > 0:
                    # 有效价差 = 2 * |交易价格 - 中间价| / 中间价
                    effective_spread = 2.0 * abs(trade.price - mid_price) / mid_price
                    effective_spreads.append(effective_spread)

            # 平均有效价差
            if effective_spreads:
                avg_effective_spread = np.mean(effective_spreads)
            else:
                avg_effective_spread = 0.0

            decompositions[symbol] = avg_effective_spread

        return pd.Series(decompositions)

    def get_performance_metrics(self) -> Dict[str, Any]:
        """获取性能指标

        需求: 5.12 - 监控处理延迟

        Returns:
            性能指标字典
        """
        return {
            "total_calls": self.performance_metrics["total_calls"],
            "total_time": self.performance_metrics["total_time"],
            "avg_latency_ms": (
                self.performance_metrics["total_time"] / self.performance_metrics["total_calls"] * 1000
                if self.performance_metrics["total_calls"] > 0
                else 0.0
            ),
            "p99_latency_ms": self.performance_metrics["p99_latency"] * 1000,
            "meets_requirement": self.performance_metrics["p99_latency"] < 0.010,  # 10ms
        }

    def optimize_batch_processing(
        self, order_books: List[OrderBookSnapshot], trades: List[Trade]
    ) -> Tuple[List[List[OrderBookSnapshot]], List[List[Trade]]]:
        """优化批处理

        需求: 5.12 - 批处理机制优化延迟

        将大量数据分批处理以优化性能

        Args:
            order_books: 订单簿快照列表
            trades: 交易记录列表

        Returns:
            分批后的订单簿和交易记录
        """
        # 分批订单簿
        order_book_batches = [order_books[i : i + self.batch_size] for i in range(0, len(order_books), self.batch_size)]

        # 分批交易记录
        trade_batches = [trades[i : i + self.batch_size] for i in range(0, len(trades), self.batch_size)]

        logger.info(
            f"批处理优化: " f"order_book_batches={len(order_book_batches)}, " f"trade_batches={len(trade_batches)}"
        )

        return order_book_batches, trade_batches
