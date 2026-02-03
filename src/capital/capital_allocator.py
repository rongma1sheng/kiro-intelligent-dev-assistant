"""资本分配器

白皮书依据: 第一章 1.3 资本分配
核心哲学: 资本物理 (Capital Physics)
"""

import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional

from loguru import logger

from src.capital.aum_sensor import AUMSensor
from src.capital.strategy_selector import StrategySelector
from src.capital.tier import Tier
from src.capital.weight_adjuster import WeightAdjuster


class CapitalMode:
    """资本运作模式

    白皮书依据: 第0章 资本物理 (Capital Physics)

    根据AUM切换行为模式：
    - 刺客模式 (Assassin): 小资金，高频快进快出
    - 狼群模式 (Wolf Pack): 中等资金，多策略并行
    - 利维坦模式 (Leviathan): 大资金，稳健运作
    """

    ASSASSIN = "assassin"  # 刺客模式：1千-10万
    WOLF_PACK = "wolf_pack"  # 狼群模式：10万-100万
    LEVIATHAN = "leviathan"  # 利维坦模式：100万+

    @classmethod
    def from_aum(cls, aum: float) -> str:
        """根据AUM确定运作模式

        Args:
            aum: 当前资金规模

        Returns:
            运作模式字符串
        """
        if aum < 100000:  # <10万  # pylint: disable=no-else-return
            return cls.ASSASSIN
        elif aum < 1000000:  # 10万-100万
            return cls.WOLF_PACK
        else:  # >=100万
            return cls.LEVIATHAN

    @classmethod
    def get_mode_characteristics(cls, mode: str) -> Dict[str, Any]:
        """获取模式特征

        Args:
            mode: 运作模式

        Returns:
            模式特征字典
        """
        characteristics = {
            cls.ASSASSIN: {
                "description": "刺客模式 - 小资金高频快进快出",
                "max_position_size": 0.20,  # 单笔最大20%
                "preferred_holding_period": "intraday",  # 日内
                "liquidity_requirement": "high",  # 高流动性
                "strategy_count": 3,  # 3个策略
                "risk_tolerance": "high",  # 高风险容忍度
            },
            cls.WOLF_PACK: {
                "description": "狼群模式 - 中等资金多策略并行",
                "max_position_size": 0.10,  # 单笔最大10%
                "preferred_holding_period": "swing",  # 波段
                "liquidity_requirement": "medium",  # 中等流动性
                "strategy_count": 5,  # 5个策略
                "risk_tolerance": "medium",  # 中等风险容忍度
            },
            cls.LEVIATHAN: {
                "description": "利维坦模式 - 大资金稳健运作",
                "max_position_size": 0.05,  # 单笔最大5%
                "preferred_holding_period": "position",  # 趋势
                "liquidity_requirement": "very_high",  # 极高流动性
                "strategy_count": 8,  # 8个策略
                "risk_tolerance": "low",  # 低风险容忍度
            },
        }

        return characteristics.get(mode, characteristics[cls.ASSASSIN])


class CapitalAllocator:
    """资本分配器

    白皮书依据: 第一章 1.3 资本分配
    核心哲学: 资本物理 (Capital Physics)

    职责：
    - 感知当前AUM并确定资金档位
    - 根据档位选择最优策略组合
    - 动态调整策略权重
    - 监控策略表现并重新分配资金
    """

    def __init__(
        self,
        aum_sensor: Optional[AUMSensor] = None,
        strategy_selector: Optional[StrategySelector] = None,
        weight_adjuster: Optional[WeightAdjuster] = None,
    ):
        """初始化资本分配器

        Args:
            aum_sensor: AUM感知器（可选，用于依赖注入）
            strategy_selector: 策略选择器（可选，用于依赖注入）
            weight_adjuster: 权重调整器（可选，用于依赖注入）
        """
        self.aum_sensor = aum_sensor or AUMSensor()
        self.strategy_selector = strategy_selector or StrategySelector()
        self.weight_adjuster = weight_adjuster or WeightAdjuster()

        # 当前状态
        self.current_aum: float = 0.0
        self.current_tier: str = Tier.TIER1_MICRO
        self.current_mode: str = CapitalMode.ASSASSIN
        self.strategy_pool: Dict[str, Any] = {}
        self.strategy_weights: Dict[str, float] = {}

        # 决策历史
        self.decision_history: List[Dict[str, Any]] = []

        logger.info("CapitalAllocator初始化完成")

    async def initialize(self) -> None:
        """初始化资本分配器

        白皮书依据: Requirement 1.1

        系统启动时初始化并感知当前AUM
        """
        try:
            self.current_aum = await self.sense_aum()
            self.current_tier = self.determine_tier(self.current_aum)

            logger.info(f"资本分配器初始化完成 - " f"AUM: {self.current_aum:.2f}, " f"档位: {self.current_tier}")
        except Exception as e:
            logger.error(f"资本分配器初始化失败: {e}")
            raise

    async def sense_aum(self) -> float:
        """感知当前AUM

        白皮书依据: 第0章 资本物理

        Returns:
            当前资金规模
        """
        try:
            aum = await self.aum_sensor.get_current_aum()
            self.current_aum = aum
            return aum
        except Exception as e:
            logger.error(f"感知AUM失败: {e}")
            # 使用缓存的AUM值
            if self.current_aum > 0:
                logger.warning(f"使用缓存的AUM值: {self.current_aum}")
                return self.current_aum
            raise

    async def sense_capital_physics(self) -> Dict[str, Any]:
        """感知资本物理状态

        白皮书依据: 第0章 资本物理 (Capital Physics)

        MIA具备真实的体感。她知道自己的资金规模(AUM)，并据此切换行为模式
        （刺客/狼群/利维坦）。每一笔交易都经过流动性与冲击成本的精密计算。

        功能：
        1. 感知当前AUM
        2. 判定资金档位（6档分层）
        3. 确定运作模式（刺客/狼群/利维坦）
        4. 返回资本物理状态

        Returns:
            资本物理状态字典 {
                'aum': float,
                'tier': str,
                'mode': str,
                'mode_characteristics': Dict,
                'tier_range': Tuple[float, float],
                'timestamp': str
            }

        Raises:
            CapitalPhysicsError: 当无法感知资本物理状态时
        """
        try:
            logger.info("开始感知资本物理状态...")

            # 1. 感知当前AUM
            aum = await self.sense_aum()

            # 2. 判定资金档位（6档分层）
            tier = self.determine_tier(aum)

            # 3. 确定运作模式（刺客/狼群/利维坦）
            mode = CapitalMode.from_aum(aum)

            # 4. 获取模式特征
            mode_characteristics = CapitalMode.get_mode_characteristics(mode)

            # 5. 获取档位范围
            tier_range = Tier.get_tier_range(tier)

            # 6. 更新当前状态
            old_mode = self.current_mode
            self.current_mode = mode

            # 7. 检测模式切换
            if old_mode != mode:
                logger.info(f"资本运作模式切换: {old_mode} → {mode} " f"({mode_characteristics['description']})")
                # 发布模式切换事件
                await self._publish_mode_change_event(old_mode, mode, aum)

            # 8. 构建资本物理状态
            capital_physics = {
                "aum": aum,
                "tier": tier,
                "mode": mode,
                "mode_characteristics": mode_characteristics,
                "tier_range": tier_range,
                "timestamp": datetime.now().isoformat(),
            }

            logger.info(
                f"资本物理状态 - "
                f"AUM: {aum:.2f}, "
                f"档位: {tier}, "
                f"模式: {mode} ({mode_characteristics['description']})"
            )

            return capital_physics

        except Exception as e:
            logger.error(f"感知资本物理状态失败: {e}")
            raise CapitalPhysicsError(f"无法感知资本物理状态: {e}") from e

    def determine_tier(self, aum: float) -> str:
        """确定资金档位

        白皮书依据: Requirement 2

        Args:
            aum: 资金规模

        Returns:
            档位字符串
        """
        old_tier = self.current_tier
        new_tier = Tier.from_aum(aum)

        if old_tier != new_tier:
            logger.info(f"档位切换: {old_tier} → {new_tier}")
            # 发布档位切换事件（通过事件总线）
            asyncio.create_task(self._publish_tier_change_event(old_tier, new_tier))

        return new_tier

    async def select_strategies(self, tier: str, market_regime: Optional[str] = None) -> List[Any]:
        """选择适合当前档位的策略组合

        白皮书依据: Requirement 3

        从Arena测试结果中选择该档位表现最好的策略

        Args:
            tier: 资金档位
            market_regime: 市场环境（可选）

        Returns:
            策略列表
        """
        try:
            strategies = await self.strategy_selector.select_for_tier(
                tier=tier, market_regime=market_regime or "neutral"
            )

            logger.info(f"为档位{tier}选择了{len(strategies)}个策略")
            return strategies

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"策略选择失败: {e}")
            return []

    async def adjust_weights(
        self, strategies: List[Any], performance_metrics: Optional[Dict[str, float]] = None
    ) -> Dict[str, float]:
        """动态调整策略权重

        白皮书依据: Requirement 4

        基于策略近期表现调整权重，确保：
        - 所有权重之和 = 1.0
        - 单个策略权重 ∈ [0.05, 0.40]

        Args:
            strategies: 策略列表
            performance_metrics: 策略表现指标（可选）

        Returns:
            策略权重字典 {strategy_name: weight}
        """
        try:
            weights = await self.weight_adjuster.adjust_weights(
                strategies=strategies, performance_metrics=performance_metrics or {}
            )

            self.strategy_weights = weights

            logger.info(f"权重调整完成: {weights}")
            return weights

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"权重调整失败: {e}")
            # 使用均等权重作为后备
            if strategies:
                equal_weight = 1.0 / len(strategies)
                weights = {s.name: equal_weight for s in strategies}
                logger.warning(f"使用均等权重: {weights}")
                return weights
            return {}

    async def reallocate_capital(self) -> Dict[str, Any]:
        """重新分配资金

        白皮书依据: Requirement 1.3

        当AUM变化导致档位切换时，重新分配资金到新档位的最优策略

        Returns:
            分配结果 {
                'tier': str,
                'strategies': List[Strategy],
                'weights': Dict[str, float],
                'timestamp': str
            }
        """
        try:
            # 1. 感知当前AUM
            aum = await self.sense_aum()

            # 2. 确定档位
            tier = self.determine_tier(aum)

            # 3. 选择策略
            strategies = await self.select_strategies(tier)

            if not strategies:
                logger.warning(f"档位{tier}无可用策略")
                return {"tier": tier, "strategies": [], "weights": {}, "timestamp": datetime.now().isoformat()}

            # 4. 调整权重
            weights = await self.adjust_weights(strategies)

            # 5. 记录决策
            decision = {
                "tier": tier,
                "aum": aum,
                "strategies": [s.get("strategy_name", s) if isinstance(s, dict) else s.name for s in strategies],
                "weights": weights,
                "timestamp": datetime.now().isoformat(),
            }

            self._record_decision(decision)

            logger.info(f"资本重新分配完成 - " f"档位: {tier}, " f"策略数: {len(strategies)}")

            return {"tier": tier, "strategies": strategies, "weights": weights, "timestamp": decision["timestamp"]}

        except Exception as e:
            logger.error(f"资本重新分配失败: {e}")
            raise

    def register_strategy(self, strategy_metadata: Dict[str, Any]) -> None:
        """注册策略到策略池

        白皮书依据: Requirement 1.5

        Args:
            strategy_metadata: 策略元数据
        """
        strategy_name = strategy_metadata.get("strategy_name")
        if not strategy_name:
            raise ValueError("策略元数据缺少strategy_name")

        self.strategy_pool[strategy_name] = strategy_metadata
        logger.info(f"策略已注册: {strategy_name}")

    def get_strategy_pool(self) -> Dict[str, Any]:
        """获取策略池

        Returns:
            策略池字典
        """
        return self.strategy_pool.copy()

    def _record_decision(self, decision: Dict[str, Any]) -> None:
        """记录资本分配决策

        白皮书依据: Requirement 1.6

        Args:
            decision: 决策信息
        """
        self.decision_history.append(decision)

        # 保留最近1000条决策记录
        if len(self.decision_history) > 1000:
            self.decision_history = self.decision_history[-1000:]

        logger.debug(f"决策已记录: {decision}")

    def get_decision_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """获取决策历史

        Args:
            limit: 返回的记录数量

        Returns:
            决策历史列表
        """
        return self.decision_history[-limit:]

    async def _publish_tier_change_event(self, old_tier: str, new_tier: str) -> None:
        """发布档位切换事件

        白皮书依据: Requirement 2.7

        Args:
            old_tier: 旧档位
            new_tier: 新档位
        """
        # PRD-REQ: 集成事件总线后实现 (白皮书 2.4.3 EventBus事件总线)
        logger.info(f"档位切换事件: {old_tier} → {new_tier}")

    async def _publish_mode_change_event(self, old_mode: str, new_mode: str, aum: float) -> None:
        """发布运作模式切换事件

        白皮书依据: 第0章 资本物理

        Args:
            old_mode: 旧模式
            new_mode: 新模式
            aum: 当前AUM
        """
        event = {  # pylint: disable=unused-variable
            "event_type": "mode_change",
            "old_mode": old_mode,
            "new_mode": new_mode,
            "aum": aum,
            "timestamp": datetime.now().isoformat(),
        }

        logger.info(f"运作模式切换事件: {old_mode} → {new_mode} " f"(AUM: {aum:.2f})")

        # PRD-REQ: 集成事件总线后实现 (白皮书 2.4.3 EventBus事件总线)
        # await self.event_bus.publish('capital.mode_change', event)


class CapitalPhysicsError(Exception):
    """资本物理异常"""
