"""微结构风险因子挖掘器

白皮书依据: 第四章 4.1.1 专业风险因子挖掘系统 - 微结构风险

本模块实现微结构风险因子挖掘，包括：
- 流动性枯竭检测
- 订单簿失衡检测
- 买卖价差扩大检测
- 深度不足检测
"""

from datetime import datetime
from typing import Any, Dict, Optional

from loguru import logger

from .risk_factor import RiskFactor


class MicrostructureRiskFactorMiner:
    """微结构风险挖掘器

    白皮书依据: 第四章 4.1.1 专业风险因子挖掘系统 - 微结构风险

    使用订单簿快照数据检测微结构风险，包括：
    1. 流动性枯竭：订单簿深度骤降
    2. 订单簿失衡：买卖盘严重失衡
    3. 买卖价差扩大：价差异常扩大
    4. 深度不足：支撑位下方深度不足

    Attributes:
        liquidity_threshold: 流动性阈值，默认0.5（50%）
        imbalance_threshold: 失衡阈值，默认3.0（3倍）
        spread_multiplier: 价差扩大倍数，默认2.0（2倍）
        depth_shortage_ratio: 深度不足比例，默认0.3（30%）
    """

    def __init__(
        self,
        liquidity_threshold: float = 0.5,  # 50%
        imbalance_threshold: float = 3.0,  # 3倍
        spread_multiplier: float = 2.0,  # 2倍
        depth_shortage_ratio: float = 0.3,  # 30%
    ):
        """初始化微结构风险挖掘器

        Args:
            liquidity_threshold: 流动性阈值，范围 [0, 1]
            imbalance_threshold: 失衡阈值，必须 > 1
            spread_multiplier: 价差扩大倍数，必须 > 1
            depth_shortage_ratio: 深度不足比例，范围 [0, 1]

        Raises:
            ValueError: 当参数不在有效范围时
        """
        # 参数验证
        if not 0 <= liquidity_threshold <= 1:
            raise ValueError(f"liquidity_threshold must be in [0, 1], got {liquidity_threshold}")

        if imbalance_threshold <= 1:
            raise ValueError(f"imbalance_threshold must be > 1, got {imbalance_threshold}")

        if spread_multiplier <= 1:
            raise ValueError(f"spread_multiplier must be > 1, got {spread_multiplier}")

        if not 0 <= depth_shortage_ratio <= 1:
            raise ValueError(f"depth_shortage_ratio must be in [0, 1], got {depth_shortage_ratio}")

        # 初始化属性
        self.liquidity_threshold = liquidity_threshold
        self.imbalance_threshold = imbalance_threshold
        self.spread_multiplier = spread_multiplier
        self.depth_shortage_ratio = depth_shortage_ratio

        logger.info(
            f"MicrostructureRiskFactorMiner initialized: "
            f"liquidity_threshold={liquidity_threshold}, "
            f"imbalance_threshold={imbalance_threshold}, "
            f"spread_multiplier={spread_multiplier}, "
            f"depth_shortage_ratio={depth_shortage_ratio}"
        )

    def mine_microstructure_risk(self, symbol: str, orderbook: Dict[str, Any]) -> Optional[RiskFactor]:
        """挖掘微结构风险因子

        白皮书依据: 第四章 4.1.1 专业风险因子挖掘系统 - 微结构风险

        检测4种微结构风险：
        1. 流动性枯竭
        2. 订单簿失衡
        3. 买卖价差扩大
        4. 深度不足

        Args:
            symbol: 标的代码，如 '000001.SZ'
            orderbook: 订单簿数据，包含：
                - 'bid_volumes': 买盘量列表 [买一量, 买二量, ..., 买五量]
                - 'ask_volumes': 卖盘量列表 [卖一量, 卖二量, ..., 卖五量]
                - 'bid_prices': 买盘价格列表 [买一价, 买二价, ..., 买五价]
                - 'ask_prices': 卖盘价格列表 [卖一价, 卖二价, ..., 卖五价]
                - 'avg_bid_volume_20d': 20日平均买盘量
                - 'spread_history': 买卖价差历史
                - 'avg_spread_20d': 20日平均价差

        Returns:
            RiskFactor: 风险因子（如果检测到风险）
            None: 未检测到风险

        Raises:
            ValueError: 当symbol为空或orderbook格式不正确时
        """
        # 验证输入
        if not symbol or not isinstance(symbol, str):
            raise ValueError(f"symbol must be a non-empty string, got '{symbol}'")

        if not isinstance(orderbook, dict):
            raise ValueError(f"orderbook must be a dict, got {type(orderbook)}")

        # 检测各种风险
        risks = []

        # 1. 流动性枯竭检测
        liquidity_drought_risk = self._detect_liquidity_drought(symbol, orderbook)
        if liquidity_drought_risk is not None:
            risks.append(("liquidity_drought", liquidity_drought_risk))

        # 2. 订单簿失衡检测
        orderbook_imbalance_risk = self._detect_orderbook_imbalance(symbol, orderbook)
        if orderbook_imbalance_risk is not None:
            risks.append(("orderbook_imbalance", orderbook_imbalance_risk))

        # 3. 买卖价差扩大检测
        spread_widening_risk = self._detect_spread_widening(symbol, orderbook)
        if spread_widening_risk is not None:
            risks.append(("spread_widening", spread_widening_risk))

        # 4. 深度不足检测
        depth_shortage_risk = self._detect_depth_shortage(symbol, orderbook)
        if depth_shortage_risk is not None:
            risks.append(("depth_shortage", depth_shortage_risk))

        # 如果没有检测到任何风险，返回None
        if not risks:
            logger.debug(f"No microstructure risk detected for {symbol}")
            return None

        # 计算综合风险值（取最大值）
        max_risk_value = max(risk_value for _, risk_value in risks)

        # 计算置信度（检测到的风险类型越多，置信度越高）
        confidence = min(0.5 + 0.15 * len(risks), 1.0)

        # 创建风险因子
        factor = RiskFactor(
            factor_type="microstructure",
            symbol=symbol,
            risk_value=max_risk_value,
            confidence=confidence,
            timestamp=datetime.now(),
            metadata={"signals": risks, "detection_count": len(risks)},
        )

        logger.info(
            f"Microstructure risk detected for {symbol}: "
            f"risk_value={max_risk_value:.3f}, "
            f"confidence={confidence:.3f}, "
            f"signals={[name for name, _ in risks]}"
        )

        return factor

    def _detect_liquidity_drought(self, symbol: str, orderbook: Dict[str, Any]) -> Optional[float]:
        """检测流动性枯竭

        白皮书依据: 第四章 4.1.1 专业风险因子挖掘系统 - 流动性枯竭

        检测逻辑：
        - 订单簿深度骤降
        - 买一到买五总量 < 20日均量的50%

        Args:
            symbol: 标的代码
            orderbook: 订单簿数据

        Returns:
            风险值 [0, 1]，None表示未检测到
        """
        try:
            bid_volumes = orderbook.get("bid_volumes", [])
            avg_bid_volume_20d = orderbook.get("avg_bid_volume_20d", 0)

            if not bid_volumes or avg_bid_volume_20d <= 0:
                logger.debug(f"Insufficient data for liquidity drought detection")  # pylint: disable=w1309
                return None

            # 计算当前买盘总量（买一到买五）
            current_bid_volume = sum(bid_volumes[:5])

            # 计算阈值
            threshold = avg_bid_volume_20d * self.liquidity_threshold

            # 检查是否低于阈值
            if current_bid_volume >= threshold:
                return None

            # 计算风险值（深度越低，风险越高）
            risk_value = 1.0 - (current_bid_volume / threshold)
            risk_value = min(max(risk_value, 0.0), 1.0)

            logger.debug(
                f"Liquidity drought detected for {symbol}: "
                f"current_bid_volume={current_bid_volume:.2f}, "
                f"threshold={threshold:.2f}, "
                f"risk_value={risk_value:.3f}"
            )

            return risk_value

        except (KeyError, TypeError, ValueError, ZeroDivisionError) as e:
            logger.warning(f"Error detecting liquidity drought for {symbol}: {e}")
            return None

    def _detect_orderbook_imbalance(self, symbol: str, orderbook: Dict[str, Any]) -> Optional[float]:
        """检测订单簿失衡

        白皮书依据: 第四章 4.1.1 专业风险因子挖掘系统 - 订单簿失衡

        检测逻辑：
        - 买卖盘严重失衡
        - 卖盘/买盘 > 3

        Args:
            symbol: 标的代码
            orderbook: 订单簿数据

        Returns:
            风险值 [0, 1]，None表示未检测到
        """
        try:
            bid_volumes = orderbook.get("bid_volumes", [])
            ask_volumes = orderbook.get("ask_volumes", [])

            if not bid_volumes or not ask_volumes:
                logger.debug(f"Insufficient data for orderbook imbalance detection")  # pylint: disable=w1309
                return None

            # 计算买卖盘总量
            total_bid = sum(bid_volumes[:5])
            total_ask = sum(ask_volumes[:5])

            if total_bid <= 0:
                logger.debug(f"Invalid bid volume for {symbol}: {total_bid}")
                return None

            # 计算失衡比例
            imbalance_ratio = total_ask / total_bid

            # 检查是否超过阈值
            if imbalance_ratio < self.imbalance_threshold:
                return None

            # 计算风险值（失衡越严重，风险越高）
            risk_value = min((imbalance_ratio - self.imbalance_threshold) / self.imbalance_threshold, 1.0)

            logger.debug(
                f"Orderbook imbalance detected for {symbol}: "
                f"imbalance_ratio={imbalance_ratio:.2f}, "
                f"risk_value={risk_value:.3f}"
            )

            return risk_value

        except (KeyError, TypeError, ValueError, ZeroDivisionError) as e:
            logger.warning(f"Error detecting orderbook imbalance for {symbol}: {e}")
            return None

    def _detect_spread_widening(self, symbol: str, orderbook: Dict[str, Any]) -> Optional[float]:
        """检测买卖价差扩大

        白皮书依据: 第四章 4.1.1 专业风险因子挖掘系统 - 买卖价差扩大

        检测逻辑：
        - 买卖价差异常扩大
        - 价差 > 20日均值的2倍

        Args:
            symbol: 标的代码
            orderbook: 订单簿数据

        Returns:
            风险值 [0, 1]，None表示未检测到
        """
        try:
            bid_prices = orderbook.get("bid_prices", [])
            ask_prices = orderbook.get("ask_prices", [])
            avg_spread_20d = orderbook.get("avg_spread_20d", 0)

            if not bid_prices or not ask_prices or avg_spread_20d <= 0:
                logger.debug(f"Insufficient data for spread widening detection")  # pylint: disable=w1309
                return None

            # 计算当前价差
            current_spread = ask_prices[0] - bid_prices[0]

            if current_spread < 0:
                logger.warning(f"Invalid spread for {symbol}: {current_spread}")
                return None

            # 计算阈值
            threshold = avg_spread_20d * self.spread_multiplier

            # 检查是否超过阈值
            if current_spread < threshold:
                return None

            # 计算风险值（价差越大，风险越高）
            risk_value = min((current_spread - threshold) / threshold, 1.0)

            logger.debug(
                f"Spread widening detected for {symbol}: "
                f"current_spread={current_spread:.4f}, "
                f"threshold={threshold:.4f}, "
                f"risk_value={risk_value:.3f}"
            )

            return risk_value

        except (KeyError, TypeError, ValueError, ZeroDivisionError, IndexError) as e:
            logger.warning(f"Error detecting spread widening for {symbol}: {e}")
            return None

    def _detect_depth_shortage(self, symbol: str, orderbook: Dict[str, Any]) -> Optional[float]:
        """检测深度不足

        白皮书依据: 第四章 4.1.1 专业风险因子挖掘系统 - 深度不足

        检测逻辑：
        - 支撑位下方深度不足
        - 下方深度 < 上方深度的30%

        Args:
            symbol: 标的代码
            orderbook: 订单簿数据

        Returns:
            风险值 [0, 1]，None表示未检测到
        """
        try:
            bid_volumes = orderbook.get("bid_volumes", [])
            ask_volumes = orderbook.get("ask_volumes", [])

            if not bid_volumes or not ask_volumes:
                logger.debug(f"Insufficient data for depth shortage detection")  # pylint: disable=w1309
                return None

            # 计算下方深度（买盘）和上方深度（卖盘）
            lower_depth = sum(bid_volumes[:5])
            upper_depth = sum(ask_volumes[:5])

            if upper_depth <= 0:
                logger.debug(f"Invalid upper depth for {symbol}: {upper_depth}")
                return None

            # 计算阈值
            threshold = upper_depth * self.depth_shortage_ratio

            # 检查下方深度是否不足
            if lower_depth >= threshold:
                return None

            # 计算风险值（深度越不足，风险越高）
            risk_value = 1.0 - (lower_depth / threshold)
            risk_value = min(max(risk_value, 0.0), 1.0)

            logger.debug(
                f"Depth shortage detected for {symbol}: "
                f"lower_depth={lower_depth:.2f}, "
                f"threshold={threshold:.2f}, "
                f"risk_value={risk_value:.3f}"
            )

            return risk_value

        except (KeyError, TypeError, ValueError, ZeroDivisionError) as e:
            logger.warning(f"Error detecting depth shortage for {symbol}: {e}")
            return None
