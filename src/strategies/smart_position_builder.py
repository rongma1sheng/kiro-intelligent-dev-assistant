"""智能分批建仓系统

白皮书依据: 第四章 4.2 斯巴达竞技场 - 大资金建仓策略

核心思路：
1. 识别主力行为（吸筹/洗筹/拉升/出货）
2. 根据主力行为调整建仓节奏
3. 结合隐身拆单，避免被主力察觉
"""

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Dict, List, Optional

from loguru import logger

if TYPE_CHECKING:
    from src.strategies.strategy_risk_manager import StrategyRiskManager


class MarketMakerPhase(Enum):
    """主力操作阶段"""

    ACCUMULATION = "accumulation"  # 吸筹阶段
    WASH_OUT = "wash_out"  # 洗筹阶段
    MARKUP = "markup"  # 拉升阶段
    DISTRIBUTION = "distribution"  # 出货阶段
    UNKNOWN = "unknown"  # 未知阶段


@dataclass
class MarketMakerSignal:
    """主力行为信号"""

    phase: MarketMakerPhase
    confidence: float  # 置信度 0.0-1.0
    volume_ratio: float  # 成交量比率（相对于平均值）
    price_volatility: float  # 价格波动率
    large_order_ratio: float  # 大单占比
    timestamp: str

    def __post_init__(self):
        """验证数据"""
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"置信度必须在[0.0, 1.0]范围内: {self.confidence}")


@dataclass
class PositionBuildingPlan:
    """建仓计划"""

    symbol: str
    total_target_size: float  # 目标总仓位
    current_size: float  # 当前仓位
    remaining_size: float  # 剩余待建仓位

    # 分批建仓参数
    batch_count: int  # 总批次数
    current_batch: int  # 当前批次
    batch_sizes: List[float]  # 每批大小
    batch_intervals: List[int]  # 批次间隔（秒）

    # 主力跟随策略
    market_maker_phase: MarketMakerPhase
    follow_strategy: str  # 'aggressive' | 'moderate' | 'conservative'

    # 执行状态
    status: str  # 'planning' | 'executing' | 'paused' | 'completed'
    executed_batches: List[Dict]  # 已执行批次记录


class SmartPositionBuilder:
    """智能分批建仓系统

    白皮书依据: 第四章 4.2 斯巴达竞技场

    功能：
    1. 识别主力行为阶段
    2. 制定分批建仓计划
    3. 动态调整建仓节奏
    4. 结合隐身拆单策略
    """

    def __init__(self):
        """初始化智能建仓系统"""
        self.active_plans: Dict[str, PositionBuildingPlan] = {}

        logger.info("SmartPositionBuilder初始化完成")

    def detect_market_maker_phase(self, symbol: str, market_data: Dict[str, any]) -> MarketMakerSignal:
        """识别主力操作阶段

        通过技术指标识别主力行为：
        1. 吸筹：成交量放大 + 价格横盘 + 大单买入
        2. 洗筹：成交量萎缩 + 价格震荡 + 散户恐慌
        3. 拉升：成交量持续 + 价格上涨 + 大单推动
        4. 出货：成交量巨大 + 价格滞涨 + 大单卖出

        Args:
            symbol: 标的代码
            market_data: 市场数据
                {
                    'volume': float,  # 当前成交量
                    'avg_volume': float,  # 平均成交量
                    'price_change': float,  # 价格变化
                    'volatility': float,  # 波动率
                    'large_buy_ratio': float,  # 大单买入占比
                    'large_sell_ratio': float,  # 大单卖出占比
                }

        Returns:
            主力行为信号
        """
        volume = market_data.get("volume", 0)
        avg_volume = market_data.get("avg_volume", 1)
        price_change = market_data.get("price_change", 0)
        volatility = market_data.get("volatility", 0)
        large_buy_ratio = market_data.get("large_buy_ratio", 0)
        large_sell_ratio = market_data.get("large_sell_ratio", 0)

        volume_ratio = volume / avg_volume if avg_volume > 0 else 1.0
        large_order_ratio = large_buy_ratio + large_sell_ratio

        # 识别逻辑
        phase = MarketMakerPhase.UNKNOWN
        confidence = 0.0

        # 1. 吸筹阶段特征
        if (
            volume_ratio > 1.5 and abs(price_change) < 0.02 and large_buy_ratio > 0.3  # 成交量放大  # 价格横盘（±2%）
        ):  # 大单买入占比 > 30%

            phase = MarketMakerPhase.ACCUMULATION
            confidence = min(0.9, volume_ratio * 0.3 + large_buy_ratio * 0.7)

            logger.info(
                f"{symbol} 检测到吸筹阶段 - "
                f"成交量比率={volume_ratio:.2f}, "
                f"大单买入={large_buy_ratio*100:.1f}%, "
                f"置信度={confidence:.2f}"
            )

        # 2. 洗筹阶段特征
        elif volume_ratio < 0.7 and volatility > 0.03 and price_change < 0:  # 成交量萎缩  # 波动率 > 3%  # 价格下跌

            phase = MarketMakerPhase.WASH_OUT
            confidence = min(0.85, (1 - volume_ratio) * 0.4 + volatility * 10 * 0.6)

            logger.info(
                f"{symbol} 检测到洗筹阶段 - "
                f"成交量比率={volume_ratio:.2f}, "
                f"波动率={volatility*100:.1f}%, "
                f"置信度={confidence:.2f}"
            )

        # 3. 拉升阶段特征
        elif (
            volume_ratio > 1.2 and price_change > 0.03 and large_buy_ratio > 0.25  # 成交量持续  # 价格上涨 > 3%
        ):  # 大单推动

            phase = MarketMakerPhase.MARKUP
            confidence = min(0.9, price_change * 10 * 0.5 + large_buy_ratio * 0.5)

            logger.info(
                f"{symbol} 检测到拉升阶段 - "
                f"价格涨幅={price_change*100:.1f}%, "
                f"成交量比率={volume_ratio:.2f}, "
                f"置信度={confidence:.2f}"
            )

        # 4. 出货阶段特征
        elif (
            volume_ratio > 2.0 and abs(price_change) < 0.01 and large_sell_ratio > 0.35  # 成交量巨大  # 价格滞涨
        ):  # 大单卖出 > 35%

            phase = MarketMakerPhase.DISTRIBUTION
            confidence = min(0.95, volume_ratio * 0.3 + large_sell_ratio * 0.7)

            logger.warning(
                f"{symbol} 检测到出货阶段 - "
                f"成交量比率={volume_ratio:.2f}, "
                f"大单卖出={large_sell_ratio*100:.1f}%, "
                f"置信度={confidence:.2f}"
            )

        from datetime import datetime  # pylint: disable=import-outside-toplevel

        return MarketMakerSignal(
            phase=phase,
            confidence=confidence,
            volume_ratio=volume_ratio,
            price_volatility=volatility,
            large_order_ratio=large_order_ratio,
            timestamp=datetime.now().isoformat(),
        )

    def create_position_building_plan(  # pylint: disable=too-many-positional-arguments
        self,
        symbol: str,
        target_size: float,
        current_size: float,
        market_maker_signal: MarketMakerSignal,
        tier: str = "tier5_million",  # pylint: disable=unused-argument
    ) -> PositionBuildingPlan:
        """创建分批建仓计划

        根据主力行为调整建仓策略：
        - 吸筹阶段：激进跟随，快速建仓
        - 洗筹阶段：逐步进场，低位吸筹
        - 拉升阶段：谨慎追高，小仓位试探
        - 出货阶段：停止建仓，考虑减仓

        Args:
            symbol: 标的代码
            target_size: 目标仓位
            current_size: 当前仓位
            market_maker_signal: 主力行为信号
            tier: 资金档位

        Returns:
            建仓计划
        """
        remaining_size = target_size - current_size

        if remaining_size <= 0:
            logger.info(f"{symbol} 已达到目标仓位，无需建仓")
            return None

        phase = market_maker_signal.phase
        confidence = market_maker_signal.confidence

        # 根据主力阶段制定策略
        if phase == MarketMakerPhase.ACCUMULATION:
            # 吸筹阶段：激进跟随
            follow_strategy = "aggressive"
            batch_count = 3  # 3批快速建仓
            batch_intervals = [300, 600]  # 5分钟、10分钟

            # 批次大小：前期多，后期少（40%, 35%, 25%）
            batch_sizes = [remaining_size * 0.40, remaining_size * 0.35, remaining_size * 0.25]

            logger.info(f"{symbol} 吸筹阶段建仓计划 - " f"激进跟随，3批快速建仓，置信度={confidence:.2f}")

        elif phase == MarketMakerPhase.WASH_OUT:
            # 洗筹阶段：逐步进场
            follow_strategy = "moderate"
            batch_count = 5  # 5批逐步建仓
            batch_intervals = [600, 900, 1200, 1800]  # 10分钟-30分钟

            # 批次大小：均匀分布，略微递增（15%, 18%, 20%, 22%, 25%）
            batch_sizes = [
                remaining_size * 0.15,
                remaining_size * 0.18,
                remaining_size * 0.20,
                remaining_size * 0.22,
                remaining_size * 0.25,
            ]

            logger.info(f"{symbol} 洗筹阶段建仓计划 - " f"逐步进场，5批分散建仓，置信度={confidence:.2f}")

        elif phase == MarketMakerPhase.MARKUP:
            # 拉升阶段：谨慎追高
            follow_strategy = "conservative"
            batch_count = 2  # 2批小仓位试探
            batch_intervals = [1800]  # 30分钟

            # 批次大小：小仓位（30%, 20%，剩余50%观望）
            batch_sizes = [remaining_size * 0.30, remaining_size * 0.20]

            logger.warning(f"{symbol} 拉升阶段建仓计划 - " f"谨慎追高，仅建仓50%，置信度={confidence:.2f}")

        elif phase == MarketMakerPhase.DISTRIBUTION:
            # 出货阶段：停止建仓
            logger.warning(f"{symbol} 出货阶段 - 停止建仓，置信度={confidence:.2f}")
            return None

        else:
            # 未知阶段：保守建仓
            follow_strategy = "moderate"
            batch_count = 4
            batch_intervals = [900, 1200, 1800]
            batch_sizes = [remaining_size / 4] * 4

            logger.info(f"{symbol} 未知阶段 - 保守建仓，4批均匀分布")

        plan = PositionBuildingPlan(
            symbol=symbol,
            total_target_size=target_size,
            current_size=current_size,
            remaining_size=remaining_size,
            batch_count=batch_count,
            current_batch=0,
            batch_sizes=batch_sizes,
            batch_intervals=batch_intervals,
            market_maker_phase=phase,
            follow_strategy=follow_strategy,
            status="planning",
            executed_batches=[],
        )

        self.active_plans[symbol] = plan

        return plan

    def adjust_plan_dynamically(
        self, symbol: str, new_market_maker_signal: MarketMakerSignal
    ) -> Optional[PositionBuildingPlan]:
        """动态调整建仓计划

        根据主力行为变化实时调整：
        - 吸筹→洗筹：放慢节奏，等待更低价位
        - 洗筹→吸筹：加快节奏，抓住机会
        - 任何→出货：立即停止建仓

        Args:
            symbol: 标的代码
            new_market_maker_signal: 新的主力行为信号

        Returns:
            调整后的建仓计划
        """
        if symbol not in self.active_plans:
            logger.warning(f"{symbol} 没有活跃的建仓计划")
            return None

        plan = self.active_plans[symbol]
        old_phase = plan.market_maker_phase
        new_phase = new_market_maker_signal.phase

        if old_phase == new_phase:
            # 阶段未变化，不调整
            return plan

        logger.info(
            f"{symbol} 主力阶段变化: {old_phase.value} → {new_phase.value}, "
            f"置信度={new_market_maker_signal.confidence:.2f}"
        )

        # 关键调整逻辑
        if new_phase == MarketMakerPhase.DISTRIBUTION:
            # 进入出货阶段：立即停止建仓
            plan.status = "paused"
            logger.warning(f"{symbol} 检测到出货阶段，暂停建仓计划")

        elif old_phase == MarketMakerPhase.ACCUMULATION and new_phase == MarketMakerPhase.WASH_OUT:
            # 吸筹→洗筹：放慢节奏
            plan.batch_intervals = [x * 1.5 for x in plan.batch_intervals]
            plan.follow_strategy = "moderate"
            logger.info(f"{symbol} 吸筹转洗筹，放慢建仓节奏")

        elif old_phase == MarketMakerPhase.WASH_OUT and new_phase == MarketMakerPhase.ACCUMULATION:
            # 洗筹→吸筹：加快节奏
            plan.batch_intervals = [max(300, int(x * 0.7)) for x in plan.batch_intervals]
            plan.follow_strategy = "aggressive"
            logger.info(f"{symbol} 洗筹转吸筹，加快建仓节奏")

        elif new_phase == MarketMakerPhase.MARKUP:
            # 进入拉升：谨慎追高
            plan.follow_strategy = "conservative"
            # 减少剩余批次的仓位
            remaining_batches = plan.batch_count - plan.current_batch
            if remaining_batches > 0:
                for i in range(plan.current_batch, plan.batch_count):
                    plan.batch_sizes[i] *= 0.6  # 减少40%
            logger.warning(f"{symbol} 进入拉升阶段，减少剩余建仓量")

        plan.market_maker_phase = new_phase

        return plan

    def get_next_batch_with_stealth(self, symbol: str, stealth_mode: bool = True) -> Optional[Dict]:
        """获取下一批建仓订单（结合隐身拆单）

        Args:
            symbol: 标的代码
            stealth_mode: 是否启用隐身模式

        Returns:
            下一批订单详情
        """
        if symbol not in self.active_plans:
            return None

        plan = self.active_plans[symbol]

        if plan.status == "paused":
            logger.warning(f"{symbol} 建仓计划已暂停")
            return None

        if plan.current_batch >= plan.batch_count:
            plan.status = "completed"
            logger.info(f"{symbol} 建仓计划已完成")
            return None

        batch_size = plan.batch_sizes[plan.current_batch]

        # 结合隐身拆单
        if stealth_mode:
            # 将批次再拆分成更小的随机订单
            import random  # pylint: disable=import-outside-toplevel

            sub_split = random.randint(2, 4)  # 每批再拆2-4单
            sub_sizes = []
            remaining = batch_size

            for i in range(sub_split - 1):  # pylint: disable=unused-variable
                size = remaining * random.uniform(0.2, 0.4)
                sub_sizes.append(size)
                remaining -= size
            sub_sizes.append(remaining)

            # 随机间隔
            sub_intervals = [random.randint(60, 300) for _ in range(sub_split - 1)]

            batch_detail = {
                "symbol": symbol,
                "batch_number": plan.current_batch + 1,
                "total_batch_size": batch_size,
                "sub_orders": sub_sizes,
                "sub_intervals": sub_intervals,
                "stealth_mode": True,
                "market_maker_phase": plan.market_maker_phase.value,
                "follow_strategy": plan.follow_strategy,
            }
        else:
            batch_detail = {
                "symbol": symbol,
                "batch_number": plan.current_batch + 1,
                "batch_size": batch_size,
                "stealth_mode": False,
                "market_maker_phase": plan.market_maker_phase.value,
                "follow_strategy": plan.follow_strategy,
            }

        logger.info(
            f"{symbol} 第{plan.current_batch + 1}/{plan.batch_count}批建仓 - "
            f"大小={batch_size:.4f}, "
            f"阶段={plan.market_maker_phase.value}, "
            f"隐身模式={'开启' if stealth_mode else '关闭'}"
        )

        return batch_detail

    def mark_batch_executed(self, symbol: str, batch_detail: Dict) -> None:
        """标记批次已执行

        Args:
            symbol: 标的代码
            batch_detail: 批次详情
        """
        if symbol not in self.active_plans:
            return

        plan = self.active_plans[symbol]
        plan.executed_batches.append(batch_detail)
        plan.current_batch += 1
        plan.current_size += batch_detail.get("total_batch_size", batch_detail.get("batch_size", 0))

        logger.info(
            f"{symbol} 批次执行完成 - "
            f"当前仓位={plan.current_size:.4f}, "
            f"目标仓位={plan.total_target_size:.4f}, "
            f"进度={plan.current_size/plan.total_target_size*100:.1f}%"
        )


class PositionProtector:
    """持仓保护系统

    实时监测主力出货行为，保护已建仓位
    """

    def __init__(self, position_builder: SmartPositionBuilder, risk_manager: Optional["StrategyRiskManager"] = None):
        """初始化持仓保护系统

        Args:
            position_builder: 智能建仓系统实例
            risk_manager: 策略风险管理器（可选，用于协调止损止盈）
        """
        self.position_builder = position_builder
        self.risk_manager = risk_manager
        self.protected_positions: Dict[str, Dict] = {}
        self.alert_history: List[Dict] = []

        logger.info("PositionProtector初始化完成")

    def set_risk_manager(self, risk_manager: "StrategyRiskManager") -> None:
        """设置风险管理器（用于协调）

        Args:
            risk_manager: 策略风险管理器
        """
        self.risk_manager = risk_manager
        logger.info("PositionProtector已关联StrategyRiskManager，启用协调机制")

    def monitor_position(self, symbol: str, current_position: float, market_data: Dict[str, any]) -> Dict[str, any]:
        """监测持仓，检测出货风险

        Args:
            symbol: 标的代码
            current_position: 当前仓位大小
            market_data: 市场数据

        Returns:
            {
                'action': 'hold' | 'reduce' | 'exit',  # 建议操作
                'urgency': 'low' | 'medium' | 'high' | 'critical',  # 紧急程度
                'reduce_ratio': float,  # 建议减仓比例
                'reason': str,  # 原因说明
                'market_maker_phase': str,  # 主力阶段
                'confidence': float  # 置信度
            }
        """
        # 识别主力行为
        signal = self.position_builder.detect_market_maker_phase(symbol, market_data)

        action = "hold"
        urgency = "low"
        reduce_ratio = 0.0
        reason = "正常持仓"

        # 根据主力阶段判断
        if signal.phase == MarketMakerPhase.DISTRIBUTION:
            # 出货阶段：高度危险
            if signal.confidence >= 0.90:
                action = "exit"
                urgency = "critical"
                reduce_ratio = 1.0  # 全部清仓
                reason = f"主力出货（置信度{signal.confidence:.0%}），立即清仓"

                logger.critical(
                    f"{symbol} 【紧急】主力出货 - "
                    f"成交量{signal.volume_ratio:.1f}倍, "
                    f"大单卖出占比高, "
                    f"建议立即清仓"
                )

            elif signal.confidence >= 0.70:
                action = "reduce"
                urgency = "high"
                reduce_ratio = 0.70  # 减仓70%
                reason = f"疑似主力出货（置信度{signal.confidence:.0%}），大幅减仓"

                logger.warning(f"{symbol} 【警告】疑似出货 - " f"建议减仓70%")

            else:
                action = "reduce"
                urgency = "medium"
                reduce_ratio = 0.30  # 减仓30%
                reason = f"可能出货（置信度{signal.confidence:.0%}），部分减仓"

                logger.info(f"{symbol} 【提示】可能出货 - 建议减仓30%")

        elif signal.phase == MarketMakerPhase.MARKUP:
            # 拉升阶段：注意风险
            if signal.confidence >= 0.80:
                # 高位拉升，可能是诱多
                action = "reduce"
                urgency = "medium"
                reduce_ratio = 0.30  # 减仓30%，落袋为安
                reason = f"高位拉升（置信度{signal.confidence:.0%}），部分止盈"

                logger.info(f"{symbol} 【提示】高位拉升 - " f"建议部分止盈，落袋为安")

        elif signal.phase == MarketMakerPhase.WASH_OUT:
            # 洗筹阶段：正常持仓
            action = "hold"
            urgency = "low"
            reason = "主力洗筹，正常持仓"

            logger.debug(f"{symbol} 主力洗筹 - 正常持仓")

        elif signal.phase == MarketMakerPhase.ACCUMULATION:
            # 吸筹阶段：可以加仓
            action = "hold"
            urgency = "low"
            reason = "主力吸筹，可以持有或加仓"

            logger.debug(f"{symbol} 主力吸筹 - 可以持有")

        # 记录监测结果
        result = {
            "symbol": symbol,
            "action": action,
            "urgency": urgency,
            "reduce_ratio": reduce_ratio,
            "reason": reason,
            "market_maker_phase": signal.phase.value,
            "confidence": signal.confidence,
            "current_position": current_position,
            "timestamp": signal.timestamp,
        }

        # 如果是减仓或清仓，记录告警并通知risk_manager
        if action in ["reduce", "exit"]:
            self.alert_history.append(result)

            # 发送告警通知（实际应用中可以接入钉钉、微信等）
            self._send_alert(result)

            # 通知risk_manager进入exit_mode（协调止损止盈）
            if self.risk_manager:
                self.risk_manager.set_exit_mode(
                    symbol=symbol, urgency=urgency, reduce_ratio=reduce_ratio, reason=reason
                )
                logger.info(f"已通知StrategyRiskManager - {symbol}: " f"进入出货监测模式，协调止损止盈")

        return result

    def _send_alert(self, alert: Dict) -> None:
        """发送告警通知（内部方法）

        Args:
            alert: 告警信息
        """
        symbol = alert["symbol"]
        action = alert["action"]
        urgency = alert["urgency"]
        reason = alert["reason"]

        # 根据紧急程度选择通知方式
        if urgency == "critical":
            # 紧急告警：电话、短信、钉钉
            logger.critical(
                f"【紧急告警】{symbol} - {reason}\n" f"建议操作: {action}\n" f"减仓比例: {alert['reduce_ratio']:.0%}"
            )
            # TODO: 接入钉钉/微信/短信通知

        elif urgency == "high":
            # 高级告警：钉钉、微信
            logger.warning(
                f"【高级告警】{symbol} - {reason}\n" f"建议操作: {action}\n" f"减仓比例: {alert['reduce_ratio']:.0%}"
            )
            # TODO: 接入钉钉/微信通知

        else:
            # 普通告警：日志记录
            logger.info(f"【告警】{symbol} - {reason}")

    def get_alert_history(self, limit: int = 10) -> List[Dict]:
        """获取告警历史

        Args:
            limit: 返回数量限制

        Returns:
            告警历史列表
        """
        return self.alert_history[-limit:]

    def create_exit_plan(
        self, symbol: str, current_position: float, reduce_ratio: float, urgency: str = "high"
    ) -> Dict:
        """创建退出计划（分批减仓）

        Args:
            symbol: 标的代码
            current_position: 当前仓位
            reduce_ratio: 减仓比例
            urgency: 紧急程度

        Returns:
            退出计划
        """
        reduce_size = current_position * reduce_ratio

        if urgency == "critical":
            # 紧急清仓：1批快速退出
            batch_count = 1
            batch_sizes = [reduce_size]
            batch_intervals = []
            strategy = "紧急清仓，立即执行"

        elif urgency == "high":
            # 高级告警：2批快速退出
            batch_count = 2
            batch_sizes = [reduce_size * 0.6, reduce_size * 0.4]
            batch_intervals = [300]  # 5分钟
            strategy = "快速减仓，2批完成"

        else:
            # 普通减仓：3批逐步退出
            batch_count = 3
            batch_sizes = [reduce_size * 0.4, reduce_size * 0.35, reduce_size * 0.25]
            batch_intervals = [600, 900]  # 10分钟、15分钟
            strategy = "逐步减仓，3批完成"

        exit_plan = {
            "symbol": symbol,
            "action": "exit",
            "urgency": urgency,
            "total_reduce_size": reduce_size,
            "batch_count": batch_count,
            "batch_sizes": batch_sizes,
            "batch_intervals": batch_intervals,
            "strategy": strategy,
            "status": "planning",
        }

        logger.info(f"{symbol} 退出计划 - " f"减仓{reduce_ratio:.0%}, " f"{batch_count}批, " f"策略: {strategy}")

        return exit_plan
