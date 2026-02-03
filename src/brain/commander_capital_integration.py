"""Commander与资本分配器集成模块

白皮书依据: 第二章 2.2 Commander (慢系统)

将资本分配器集成到Commander，实现档位感知的策略建议。
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from loguru import logger

from src.capital.capital_allocator import CapitalAllocator


class CommanderCapitalIntegration:
    """Commander与资本分配器集成

    白皮书依据: Requirement 16

    职责：
    - 集成资本分配器到Commander
    - 提供档位感知的策略建议
    - 移除硬编码的风险控制矩阵
    """

    def __init__(self, capital_allocator: Optional[CapitalAllocator] = None):
        """初始化集成模块

        Args:
            capital_allocator: 资本分配器实例（可选，用于依赖注入）
        """
        self.capital_allocator = capital_allocator or CapitalAllocator()

        logger.info("CommanderCapitalIntegration初始化完成")

    async def analyze_strategy_with_capital_context(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """策略分析（带资本上下文）

        白皮书依据: Requirement 16.2, 16.3

        Args:
            market_data: 市场数据

        Returns:
            策略分析结果，包含当前档位和推荐策略
        """
        logger.info("开始策略分析（带资本上下文）")

        try:
            # 1. 获取当前档位
            current_aum = await self.capital_allocator.sense_aum()
            current_tier = self.capital_allocator.determine_tier(current_aum)

            # 2. 识别市场环境
            market_regime = self._identify_market_regime(market_data)

            # 3. 生成策略建议
            recommendation = await self.generate_strategy_recommendation(
                market_regime=market_regime, current_tier=current_tier
            )

            logger.info(
                f"策略分析完成 - "
                f"档位: {current_tier}, "
                f"市场环境: {market_regime}, "
                f"推荐策略数: {len(recommendation['recommended_strategies'])}"
            )

            return {
                "current_tier": current_tier,
                "current_aum": current_aum,
                "market_regime": market_regime,
                "recommendation": recommendation,
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"策略分析失败: {e}")
            raise

    async def generate_strategy_recommendation(self, market_regime: str, current_tier: str) -> Dict[str, Any]:
        """生成策略建议

        白皮书依据: Requirement 16.4

        Args:
            market_regime: 市场环境 (bull/bear/sideways/neutral)
            current_tier: 当前资金档位

        Returns:
            {
                'recommended_strategies': List[StrategyMetadata],
                'weights': Dict[str, float],
                'rationale': str
            }
        """
        logger.info(f"生成策略建议 - " f"市场环境: {market_regime}, " f"档位: {current_tier}")

        try:
            # 1. 选择适合当前档位的策略
            strategies = await self.capital_allocator.select_strategies(tier=current_tier, market_regime=market_regime)

            if not strategies:
                logger.warning(f"档位{current_tier}无可用策略")
                return {"recommended_strategies": [], "weights": {}, "rationale": f"档位{current_tier}暂无可用策略"}

            # 2. 调整策略权重
            weights = await self.capital_allocator.adjust_weights(strategies)

            # 3. 生成建议理由
            rationale = self._generate_rationale(
                strategies=strategies, weights=weights, market_regime=market_regime, current_tier=current_tier
            )

            logger.info(f"策略建议生成完成 - " f"策略数: {len(strategies)}, " f"权重: {weights}")

            return {"recommended_strategies": strategies, "weights": weights, "rationale": rationale}

        except Exception as e:
            logger.error(f"策略建议生成失败: {e}")
            raise

    def _identify_market_regime(self, market_data: Dict[str, Any]) -> str:
        """识别市场环境（内部方法）

        Args:
            market_data: 市场数据

        Returns:
            市场环境 (bull/bear/sideways/neutral)
        """
        # 简化版本：基于市场数据识别环境
        # 实际应该使用更复杂的算法（技术指标、机器学习等）

        try:
            # 获取市场趋势指标
            trend = market_data.get("trend", 0.0)
            volatility = market_data.get("volatility", 0.0)

            # 简单的规则判断
            if trend > 0.05:  # pylint: disable=no-else-return
                return "bull"  # 牛市
            elif trend < -0.05:
                return "bear"  # 熊市
            elif volatility < 0.10:
                return "sideways"  # 震荡市
            else:
                return "neutral"  # 中性市场

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.warning(f"市场环境识别失败: {e}，使用默认值neutral")
            return "neutral"

    def _generate_rationale(
        self, strategies: List[Any], weights: Dict[str, float], market_regime: str, current_tier: str
    ) -> str:
        """生成建议理由（内部方法）

        Args:
            strategies: 策略列表
            weights: 策略权重
            market_regime: 市场环境
            current_tier: 当前档位

        Returns:
            建议理由文本
        """
        # 构建理由文本
        rationale_parts = []

        # 1. 档位说明
        tier_desc = {
            "tier1_micro": "小资金（1千-1万）",
            "tier2_small": "小资金（1万-10万）",
            "tier3_medium": "中等资金（10万-50万）",
            "tier4_large": "大资金（50万-100万）",
            "tier5_million": "百万级资金（100万-1000万）",
            "tier6_ten_million": "千万级资金（1000万以上）",
        }
        rationale_parts.append(f"当前档位：{tier_desc.get(current_tier, current_tier)}")

        # 2. 市场环境说明
        regime_desc = {
            "bull": "牛市环境，适合动量策略",
            "bear": "熊市环境，适合防御策略",
            "sideways": "震荡市场，适合套利策略",
            "neutral": "中性市场，适合均衡配置",
        }
        rationale_parts.append(f"市场环境：{regime_desc.get(market_regime, market_regime)}")

        # 3. 策略说明
        if strategies:
            strategy_names = [getattr(s, "name", s.get("strategy_name", "unknown")) for s in strategies]
            rationale_parts.append(f"推荐策略：{', '.join(strategy_names[:3])}")

            # 权重说明
            if weights:
                top_strategy = max(weights.items(), key=lambda x: x[1])
                rationale_parts.append(f"主要配置：{top_strategy[0]} ({top_strategy[1]*100:.1f}%)")

        return "。".join(rationale_parts) + "。"


class CommanderStrategyAnalyzer:
    """Commander策略分析器

    白皮书依据: Requirement 16.5

    提供市场环境分析和策略评估功能
    """

    def __init__(self):
        """初始化策略分析器"""
        logger.info("CommanderStrategyAnalyzer初始化完成")

    async def analyze_market_environment(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """分析市场环境

        Args:
            market_data: 市场数据

        Returns:
            市场环境分析结果
        """
        logger.info("开始市场环境分析")

        try:
            # 简化版本：基本的市场分析
            # 实际应该包含更复杂的技术分析、基本面分析等

            analysis = {
                "trend": self._analyze_trend(market_data),
                "volatility": self._analyze_volatility(market_data),
                "momentum": self._analyze_momentum(market_data),
                "support_resistance": self._analyze_support_resistance(market_data),
                "timestamp": datetime.now().isoformat(),
            }

            logger.info("市场环境分析完成")

            return analysis

        except Exception as e:
            logger.error(f"市场环境分析失败: {e}")
            raise

    def _analyze_trend(self, market_data: Dict[str, Any]) -> Dict[str, Any]:  # pylint: disable=unused-argument
        """分析趋势（内部方法）"""
        # 简化实现
        return {"direction": "up", "strength": 0.7, "confidence": 0.8}

    def _analyze_volatility(self, market_data: Dict[str, Any]) -> Dict[str, Any]:  # pylint: disable=unused-argument
        """分析波动率（内部方法）"""
        # 简化实现
        return {"level": "medium", "value": 0.15, "trend": "stable"}

    def _analyze_momentum(self, market_data: Dict[str, Any]) -> Dict[str, Any]:  # pylint: disable=unused-argument
        """分析动量（内部方法）"""
        # 简化实现
        return {"strength": 0.6, "direction": "positive", "acceleration": 0.1}

    def _analyze_support_resistance(
        self, market_data: Dict[str, Any]  # pylint: disable=unused-argument
    ) -> Dict[str, Any]:  # pylint: disable=unused-argument
        """分析支撑阻力（内部方法）"""
        # 简化实现
        return {"support_levels": [95.0, 90.0], "resistance_levels": [105.0, 110.0], "current_position": "mid"}
