"""资金流风险因子挖掘器

白皮书依据: 第四章 4.1.1 专业风险因子挖掘系统 - 资金流风险

本模块实现资金流风险因子挖掘，包括：
- 主力资金撤退检测
- 承接崩塌检测
- 大单砸盘检测
- 资金流向逆转检测
"""

from datetime import datetime
from typing import Any, Dict, Optional

from loguru import logger

from .risk_factor import RiskFactor


class FlowRiskFactorMiner:
    """资金流风险挖掘器

    白皮书依据: 第四章 4.1.1 专业风险因子挖掘系统 - 资金流风险

    使用Level-2逐笔成交数据检测资金流风险，包括：
    1. 主力资金撤退：大单净流出持续N日
    2. 承接崩塌：卖盘无人承接，成交量萎缩
    3. 大单砸盘：短时间内连续大单卖出
    4. 资金流向逆转：资金流向从净流入转为净流出

    Attributes:
        capital_retreat_threshold: 资金撤退阈值（元），默认5亿
        large_order_threshold: 大单阈值（元），默认100万
        detection_window_days: 检测窗口天数，默认5天
        acceptance_volume_ratio: 承接崩塌成交量比例，默认0.3（30%）
        large_order_count_threshold: 大单砸盘数量阈值，默认3笔
        large_order_time_window: 大单砸盘时间窗口（秒），默认300秒（5分钟）
        flow_reversal_days: 资金流向逆转检测天数，默认3天
    """

    def __init__(  # pylint: disable=too-many-positional-arguments
        self,
        capital_retreat_threshold: float = 500_000_000,  # 5亿
        large_order_threshold: float = 1_000_000,  # 100万
        detection_window_days: int = 5,
        acceptance_volume_ratio: float = 0.3,  # 30%
        large_order_count_threshold: int = 3,
        large_order_time_window: int = 300,  # 5分钟
        flow_reversal_days: int = 3,
    ):
        """初始化资金流风险挖掘器

        Args:
            capital_retreat_threshold: 资金撤退阈值（元），必须 > 0
            large_order_threshold: 大单阈值（元），必须 > 0
            detection_window_days: 检测窗口天数，必须 > 0
            acceptance_volume_ratio: 承接崩塌成交量比例，范围 [0, 1]
            large_order_count_threshold: 大单砸盘数量阈值，必须 > 0
            large_order_time_window: 大单砸盘时间窗口（秒），必须 > 0
            flow_reversal_days: 资金流向逆转检测天数，必须 > 0

        Raises:
            ValueError: 当参数不在有效范围时
        """
        # 参数验证
        if capital_retreat_threshold <= 0:
            raise ValueError(f"capital_retreat_threshold must be > 0, got {capital_retreat_threshold}")

        if large_order_threshold <= 0:
            raise ValueError(f"large_order_threshold must be > 0, got {large_order_threshold}")

        if detection_window_days <= 0:
            raise ValueError(f"detection_window_days must be > 0, got {detection_window_days}")

        if not 0 <= acceptance_volume_ratio <= 1:
            raise ValueError(f"acceptance_volume_ratio must be in [0, 1], got {acceptance_volume_ratio}")

        if large_order_count_threshold <= 0:
            raise ValueError(f"large_order_count_threshold must be > 0, got {large_order_count_threshold}")

        if large_order_time_window <= 0:
            raise ValueError(f"large_order_time_window must be > 0, got {large_order_time_window}")

        if flow_reversal_days <= 0:
            raise ValueError(f"flow_reversal_days must be > 0, got {flow_reversal_days}")

        # 初始化属性
        self.capital_retreat_threshold = capital_retreat_threshold
        self.large_order_threshold = large_order_threshold
        self.detection_window_days = detection_window_days
        self.acceptance_volume_ratio = acceptance_volume_ratio
        self.large_order_count_threshold = large_order_count_threshold
        self.large_order_time_window = large_order_time_window
        self.flow_reversal_days = flow_reversal_days

        logger.info(
            f"FlowRiskFactorMiner initialized: "
            f"capital_retreat_threshold={capital_retreat_threshold}, "
            f"large_order_threshold={large_order_threshold}, "
            f"detection_window_days={detection_window_days}"
        )

    def mine_flow_risk(self, symbol: str, level2_data: Dict[str, Any]) -> Optional[RiskFactor]:
        """挖掘资金流风险因子

        白皮书依据: 第四章 4.1.1 专业风险因子挖掘系统 - 资金流风险

        检测4种资金流风险：
        1. 主力资金撤退
        2. 承接崩塌
        3. 大单砸盘
        4. 资金流向逆转

        Args:
            symbol: 标的代码，如 '000001.SZ'
            level2_data: Level-2数据，包含：
                - 'net_outflow_history': 净流出历史 List[float]
                - 'volume_history': 成交量历史 List[float]
                - 'avg_volume_20d': 20日平均成交量 float
                - 'large_orders': 大单列表 List[Dict]，每个包含 'amount', 'timestamp'
                - 'flow_direction_history': 资金流向历史 List[float]（正数=流入，负数=流出）

        Returns:
            RiskFactor: 风险因子（如果检测到风险）
            None: 未检测到风险

        Raises:
            ValueError: 当symbol为空或level2_data格式不正确时
        """
        # 验证输入
        if not symbol or not isinstance(symbol, str):
            raise ValueError(f"symbol must be a non-empty string, got '{symbol}'")

        if not isinstance(level2_data, dict):
            raise ValueError(f"level2_data must be a dict, got {type(level2_data)}")

        # 检测各种风险
        risks = []

        # 1. 主力资金撤退检测
        capital_retreat_risk = self._detect_capital_retreat(symbol, level2_data)
        if capital_retreat_risk is not None:
            risks.append(("capital_retreat", capital_retreat_risk))

        # 2. 承接崩塌检测
        acceptance_collapse_risk = self._detect_acceptance_collapse(symbol, level2_data)
        if acceptance_collapse_risk is not None:
            risks.append(("acceptance_collapse", acceptance_collapse_risk))

        # 3. 大单砸盘检测
        large_order_dump_risk = self._detect_large_order_dump(symbol, level2_data)
        if large_order_dump_risk is not None:
            risks.append(("large_order_dump", large_order_dump_risk))

        # 4. 资金流向逆转检测
        flow_reversal_risk = self._detect_flow_reversal(symbol, level2_data)
        if flow_reversal_risk is not None:
            risks.append(("flow_reversal", flow_reversal_risk))

        # 如果没有检测到任何风险，返回None
        if not risks:
            logger.debug(f"No flow risk detected for {symbol}")
            return None

        # 计算综合风险值（取最大值）
        max_risk_value = max(risk_value for _, risk_value in risks)

        # 计算置信度（检测到的风险类型越多，置信度越高）
        confidence = min(0.5 + 0.15 * len(risks), 1.0)

        # 创建风险因子
        factor = RiskFactor(
            factor_type="flow",
            symbol=symbol,
            risk_value=max_risk_value,
            confidence=confidence,
            timestamp=datetime.now(),
            metadata={"signals": risks, "detection_count": len(risks)},
        )

        logger.info(
            f"Flow risk detected for {symbol}: "
            f"risk_value={max_risk_value:.3f}, "
            f"confidence={confidence:.3f}, "
            f"signals={[name for name, _ in risks]}"
        )

        return factor

    def _detect_capital_retreat(self, symbol: str, level2_data: Dict[str, Any]) -> Optional[float]:
        """检测主力资金撤退

        白皮书依据: 第四章 4.1.1 专业风险因子挖掘系统 - 主力资金撤退

        检测逻辑：
        - 大单净流出持续N日（N=detection_window_days）
        - 净流出金额 > capital_retreat_threshold

        Args:
            symbol: 标的代码
            level2_data: Level-2数据

        Returns:
            风险值 [0, 1]，None表示未检测到
        """
        try:
            net_outflow_history = level2_data.get("net_outflow_history", [])

            if len(net_outflow_history) < self.detection_window_days:
                logger.debug(
                    f"Insufficient data for capital retreat detection: "
                    f"{len(net_outflow_history)} < {self.detection_window_days}"
                )
                return None

            # 检查最近N日是否持续净流出
            recent_outflows = net_outflow_history[-self.detection_window_days :]

            # 所有日期都必须是净流出（正数表示流出）
            if not all(outflow > 0 for outflow in recent_outflows):
                return None

            # 计算总净流出
            total_outflow = sum(recent_outflows)

            # 检查是否超过阈值
            if total_outflow < self.capital_retreat_threshold:
                return None

            # 计算风险值（超过阈值越多，风险越高）
            risk_value = min(total_outflow / (self.capital_retreat_threshold * 2), 1.0)

            logger.debug(
                f"Capital retreat detected for {symbol}: "
                f"total_outflow={total_outflow:.2f}, "
                f"risk_value={risk_value:.3f}"
            )

            return risk_value

        except (KeyError, TypeError, ValueError) as e:
            logger.warning(f"Error detecting capital retreat for {symbol}: {e}")
            return None

    def _detect_acceptance_collapse(self, symbol: str, level2_data: Dict[str, Any]) -> Optional[float]:
        """检测承接崩塌

        白皮书依据: 第四章 4.1.1 专业风险因子挖掘系统 - 承接崩塌

        检测逻辑：
        - 卖盘无人承接
        - 成交量 < 20日均量的30%

        Args:
            symbol: 标的代码
            level2_data: Level-2数据

        Returns:
            风险值 [0, 1]，None表示未检测到
        """
        try:
            volume_history = level2_data.get("volume_history", [])
            avg_volume_20d = level2_data.get("avg_volume_20d", 0)

            if not volume_history or avg_volume_20d <= 0:
                logger.debug(f"Insufficient data for acceptance collapse detection")  # pylint: disable=w1309
                return None

            # 获取最新成交量
            current_volume = volume_history[-1]

            # 计算阈值
            threshold = avg_volume_20d * self.acceptance_volume_ratio

            # 检查是否低于阈值
            if current_volume >= threshold:
                return None

            # 计算风险值（成交量越低，风险越高）
            risk_value = 1.0 - (current_volume / threshold)
            risk_value = min(max(risk_value, 0.0), 1.0)

            logger.debug(
                f"Acceptance collapse detected for {symbol}: "
                f"current_volume={current_volume:.2f}, "
                f"threshold={threshold:.2f}, "
                f"risk_value={risk_value:.3f}"
            )

            return risk_value

        except (KeyError, TypeError, ValueError, ZeroDivisionError) as e:
            logger.warning(f"Error detecting acceptance collapse for {symbol}: {e}")
            return None

    def _detect_large_order_dump(self, symbol: str, level2_data: Dict[str, Any]) -> Optional[float]:
        """检测大单砸盘

        白皮书依据: 第四章 4.1.1 专业风险因子挖掘系统 - 大单砸盘

        检测逻辑：
        - 单笔大单 > large_order_threshold
        - 时间窗口内 > large_order_count_threshold 笔大单

        Args:
            symbol: 标的代码
            level2_data: Level-2数据

        Returns:
            风险值 [0, 1]，None表示未检测到
        """
        try:
            large_orders = level2_data.get("large_orders", [])

            if not large_orders:
                return None

            # 过滤出符合大单阈值的订单
            qualified_orders = [order for order in large_orders if order.get("amount", 0) > self.large_order_threshold]

            if len(qualified_orders) < self.large_order_count_threshold:
                return None

            # 检查时间窗口内的大单数量
            current_time = datetime.now()
            recent_orders = []

            for order in qualified_orders:
                order_time = order.get("timestamp")
                if isinstance(order_time, datetime):
                    time_diff = (current_time - order_time).total_seconds()
                    if time_diff <= self.large_order_time_window:
                        recent_orders.append(order)

            if len(recent_orders) < self.large_order_count_threshold:
                return None

            # 计算风险值（大单数量越多，风险越高）
            risk_value = min(len(recent_orders) / (self.large_order_count_threshold * 2), 1.0)

            logger.debug(
                f"Large order dump detected for {symbol}: "
                f"recent_orders={len(recent_orders)}, "
                f"risk_value={risk_value:.3f}"
            )

            return risk_value

        except (KeyError, TypeError, ValueError) as e:
            logger.warning(f"Error detecting large order dump for {symbol}: {e}")
            return None

    def _detect_flow_reversal(self, symbol: str, level2_data: Dict[str, Any]) -> Optional[float]:
        """检测资金流向逆转

        白皮书依据: 第四章 4.1.1 专业风险因子挖掘系统 - 资金流向逆转

        检测逻辑：
        - 资金流向从净流入转为净流出
        - N日移动平均翻转（N=flow_reversal_days）

        Args:
            symbol: 标的代码
            level2_data: Level-2数据

        Returns:
            风险值 [0, 1]，None表示未检测到
        """
        try:
            flow_direction_history = level2_data.get("flow_direction_history", [])

            if len(flow_direction_history) < self.flow_reversal_days * 2:
                logger.debug(
                    f"Insufficient data for flow reversal detection: "
                    f"{len(flow_direction_history)} < {self.flow_reversal_days * 2}"
                )
                return None

            # 计算前N日和后N日的移动平均
            mid_point = len(flow_direction_history) - self.flow_reversal_days

            previous_avg = (
                sum(flow_direction_history[mid_point - self.flow_reversal_days : mid_point]) / self.flow_reversal_days
            )
            recent_avg = sum(flow_direction_history[mid_point:]) / self.flow_reversal_days

            # 检查是否从流入（正数）转为流出（负数）
            if previous_avg <= 0 or recent_avg >= 0:
                return None

            # 计算风险值（逆转幅度越大，风险越高）
            reversal_magnitude = abs(recent_avg - previous_avg)
            risk_value = min(reversal_magnitude / (abs(previous_avg) * 2), 1.0)

            logger.debug(
                f"Flow reversal detected for {symbol}: "
                f"previous_avg={previous_avg:.2f}, "
                f"recent_avg={recent_avg:.2f}, "
                f"risk_value={risk_value:.3f}"
            )

            return risk_value

        except (KeyError, TypeError, ValueError, ZeroDivisionError) as e:
            logger.warning(f"Error detecting flow reversal for {symbol}: {e}")
            return None
