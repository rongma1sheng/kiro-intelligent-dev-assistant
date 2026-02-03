"""Arena测试管理器

白皮书依据: 第四章 4.2 斯巴达竞技场
"""

from datetime import datetime
from typing import Any, Dict, Optional

from loguru import logger

from src.strategies.base_strategy import Strategy
from src.strategies.data_models import ArenaTestResult


class ArenaTestManager:
    """Arena测试管理器

    白皮书依据: 第四章 4.2 斯巴达竞技场

    在4个资金档位中测试策略，让策略完全自由进化。

    职责：
    - 在Tier1-4四个档位测试策略
    - 让策略零约束、完全自由进化
    - 记录策略在每个档位的表现和进化参数
    - 识别策略最适合的档位
    - 模拟滑点和冲击成本（Tier3-4）
    """

    def __init__(self):
        """初始化Arena测试管理器"""
        # 四个测试档位的初始资金
        self.tier_capital_map = {
            "tier1_micro": 5000.0,  # 1千-1万，取中值5千
            "tier2_small": 50000.0,  # 1万-10万，取中值5万
            "tier3_medium": 250000.0,  # 10万-50万，取中值25万
            "tier4_large": 750000.0,  # 50万-100万，取中值75万
        }

        # 测试结果缓存
        self.test_results_cache: Dict[str, Dict[str, ArenaTestResult]] = {}

        logger.info("ArenaTestManager初始化完成")

    async def test_strategy_in_four_tiers(
        self, strategy: Strategy, test_duration_days: int = 252  # 默认测试1年
    ) -> Dict[str, Any]:
        """在4个档位测试策略

        白皮书依据: Requirement 9

        Args:
            strategy: 待测试的策略
            test_duration_days: 测试时长（天），默认252天（1年）

        Returns:
            {
                'tier1_result': ArenaTestResult,
                'tier2_result': ArenaTestResult,
                'tier3_result': ArenaTestResult,
                'tier4_result': ArenaTestResult,
                'best_tier': 'tier2_small',
                'evolved_params': {...}
            }
        """
        logger.info(f"开始四档位Arena测试 - 策略: {strategy.name}, 测试时长: {test_duration_days}天")

        results = {}

        # 在四个档位分别测试
        for tier, initial_capital in self.tier_capital_map.items():
            logger.info(f"测试档位: {tier}, 初始资金: {initial_capital:.2f}")

            try:
                tier_result = await self.test_in_tier(
                    strategy=strategy, tier=tier, initial_capital=initial_capital, test_duration_days=test_duration_days
                )
                results[f"{tier}_result"] = tier_result

            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.error(f"档位{tier}测试失败: {e}")
                # 创建失败结果
                results[f"{tier}_result"] = self._create_failed_result(strategy.name, tier, initial_capital, str(e))

        # 识别最佳档位
        best_tier = await self.identify_best_tier(results)

        # 获取最佳档位的进化参数
        best_result = results.get(f"{best_tier}_result")
        evolved_params = best_result.evolved_params if best_result else {}

        logger.info(f"四档位测试完成 - " f"策略: {strategy.name}, " f"最佳档位: {best_tier}")

        # 缓存结果
        self.test_results_cache[strategy.name] = results

        return {**results, "best_tier": best_tier, "evolved_params": evolved_params}

    async def test_in_tier(
        self, strategy: Strategy, tier: str, initial_capital: float, test_duration_days: int = 252
    ) -> ArenaTestResult:
        """在指定档位测试策略

        白皮书依据: Requirement 8

        Args:
            strategy: 待测试的策略
            tier: 资金档位
            initial_capital: 初始资金
            test_duration_days: 测试时长（天）

        Returns:
            Arena测试结果
        """
        logger.info(f"开始单档位测试 - 档位: {tier}, 策略: {strategy.name}")

        # 模拟回测（简化版）
        # 实际应该使用真实的历史数据进行回测

        # 1. 模拟策略进化参数（实际应该通过遗传算法等方式进化）
        evolved_params = self._simulate_parameter_evolution(tier)

        # 2. 模拟回测结果
        performance_metrics = self._simulate_backtest(
            strategy=strategy,
            tier=tier,
            initial_capital=initial_capital,
            evolved_params=evolved_params,
            test_duration_days=test_duration_days,
        )

        # 3. 模拟滑点和冲击成本（Tier3-4）
        slippage_impact = await self._simulate_slippage_and_impact_for_tier(
            tier=tier, avg_order_size=initial_capital * 0.1  # 假设平均订单10%资金
        )

        # 4. 创建测试结果
        test_result = ArenaTestResult(
            strategy_name=strategy.name,
            test_tier=tier,
            initial_capital=initial_capital,
            final_capital=performance_metrics["final_capital"],
            total_return_pct=performance_metrics["total_return_pct"],
            sharpe_ratio=performance_metrics["sharpe_ratio"],
            max_drawdown_pct=performance_metrics["max_drawdown_pct"],
            win_rate=performance_metrics["win_rate"],
            evolved_params=evolved_params,
            avg_slippage_pct=slippage_impact["avg_slippage_pct"],
            avg_impact_cost_pct=slippage_impact["avg_impact_cost_pct"],
            test_start_date=datetime.now().strftime("%Y-%m-%d"),
            test_end_date=datetime.now().strftime("%Y-%m-%d"),
        )

        logger.info(
            f"单档位测试完成 - "
            f"档位: {tier}, "
            f"收益率: {test_result.total_return_pct:.2f}%, "
            f"夏普: {test_result.sharpe_ratio:.2f}"
        )

        return test_result

    async def simulate_slippage_and_impact(self, tier: str, order_size: float, daily_volume: float) -> Dict[str, float]:
        """模拟滑点和冲击成本

        白皮书依据: Requirement 8.9

        根据档位和订单大小模拟真实的滑点和冲击成本

        Args:
            tier: 资金档位
            order_size: 订单金额
            daily_volume: 日均成交额

        Returns:
            {'slippage_pct': float, 'impact_cost_pct': float}
        """
        # 基础滑点（根据档位）
        tier_slippage_map = {
            "tier1_micro": 0.0015,  # 0.15%
            "tier2_small": 0.002,  # 0.20%
            "tier3_medium": 0.004,  # 0.40%
            "tier4_large": 0.005,  # 0.50%
        }

        base_slippage = tier_slippage_map.get(tier, 0.002)

        # 订单占成交量的比例
        order_volume_ratio = order_size / daily_volume if daily_volume > 0 else 0.1

        # 滑点随订单大小增加（非线性）
        slippage_pct = base_slippage * (1 + order_volume_ratio**0.5)

        # 冲击成本（订单越大，冲击越大）
        impact_cost_pct = base_slippage * 0.5 * (order_volume_ratio**0.7)

        logger.debug(
            f"滑点模拟 - 档位: {tier}, "
            f"订单/成交量: {order_volume_ratio*100:.2f}%, "
            f"滑点: {slippage_pct*100:.3f}%, "
            f"冲击: {impact_cost_pct*100:.3f}%"
        )

        return {"slippage_pct": slippage_pct, "impact_cost_pct": impact_cost_pct}

    async def identify_best_tier(self, test_results: Dict[str, Any]) -> str:
        """识别策略表现最好的档位

        白皮书依据: Requirement 9.7

        综合考虑：
        - 收益率
        - 夏普比率
        - 最大回撤
        - 稳定性

        Args:
            test_results: 测试结果字典

        Returns:
            最佳档位名称
        """
        tier_scores = {}

        for tier in ["tier1_micro", "tier2_small", "tier3_medium", "tier4_large"]:
            result_key = f"{tier}_result"
            if result_key not in test_results:
                continue

            result = test_results[result_key]
            if not isinstance(result, ArenaTestResult):
                continue

            # 综合评分（可以调整权重）
            score = (
                result.sharpe_ratio * 0.4  # 夏普比率权重40%
                + result.total_return_pct * 0.01 * 0.3  # 收益率权重30%
                + (1 - abs(result.max_drawdown_pct) * 0.01) * 0.2  # 回撤权重20%
                + result.win_rate * 0.1  # 胜率权重10%
            )

            tier_scores[tier] = score

            logger.debug(
                f"档位评分 - {tier}: {score:.4f} "
                f"(夏普: {result.sharpe_ratio:.2f}, "
                f"收益: {result.total_return_pct:.2f}%, "
                f"回撤: {result.max_drawdown_pct:.2f}%)"
            )

        if not tier_scores:
            logger.warning("无有效测试结果，默认返回tier1_micro")
            return "tier1_micro"

        # 选择评分最高的档位
        best_tier = max(tier_scores.items(), key=lambda x: x[1])[0]

        logger.info(f"最佳档位识别完成: {best_tier} (评分: {tier_scores[best_tier]:.4f})")

        return best_tier

    def get_test_results(self, strategy_name: str) -> Optional[Dict[str, Any]]:
        """获取策略的测试结果

        Args:
            strategy_name: 策略名称

        Returns:
            测试结果字典，如果不存在返回None
        """
        return self.test_results_cache.get(strategy_name)

    def _simulate_parameter_evolution(self, tier: str) -> Dict[str, Any]:
        """模拟参数进化（内部方法）

        实际应该使用遗传算法等方式让策略自由进化参数
        这里是简化的模拟版本

        Args:
            tier: 资金档位

        Returns:
            进化出的参数字典
        """
        # 不同档位的典型参数范围（仅供参考，实际由进化决定）
        tier_param_ranges = {
            "tier1_micro": {
                "max_position": (0.8, 1.0),
                "max_single_stock": (0.15, 0.30),
                "max_industry": (0.40, 0.70),
                "stop_loss_pct": (-0.10, -0.05),
                "take_profit_pct": (0.10, 0.20),
                "trading_frequency": "high",
                "holding_period_days": (1, 3),
            },
            "tier2_small": {
                "max_position": (0.75, 0.95),
                "max_single_stock": (0.12, 0.25),
                "max_industry": (0.35, 0.60),
                "stop_loss_pct": (-0.08, -0.04),
                "take_profit_pct": (0.08, 0.15),
                "trading_frequency": "medium",
                "holding_period_days": (2, 5),
            },
            "tier3_medium": {
                "max_position": (0.70, 0.90),
                "max_single_stock": (0.10, 0.20),
                "max_industry": (0.30, 0.50),
                "stop_loss_pct": (-0.06, -0.03),
                "take_profit_pct": (0.06, 0.12),
                "trading_frequency": "medium",
                "holding_period_days": (3, 7),
            },
            "tier4_large": {
                "max_position": (0.65, 0.85),
                "max_single_stock": (0.08, 0.15),
                "max_industry": (0.25, 0.45),
                "stop_loss_pct": (-0.05, -0.02),
                "take_profit_pct": (0.05, 0.10),
                "trading_frequency": "low",
                "holding_period_days": (5, 10),
            },
        }

        param_range = tier_param_ranges.get(tier, tier_param_ranges["tier1_micro"])

        # 模拟进化：在范围内随机选择（实际应该是优化算法）
        import random  # pylint: disable=import-outside-toplevel

        evolved_params = {
            "max_position": random.uniform(*param_range["max_position"]),
            "max_single_stock": random.uniform(*param_range["max_single_stock"]),
            "max_industry": random.uniform(*param_range["max_industry"]),
            "stop_loss_pct": random.uniform(*param_range["stop_loss_pct"]),
            "take_profit_pct": random.uniform(*param_range["take_profit_pct"]),
            "trading_frequency": param_range["trading_frequency"],
            "holding_period_days": random.randint(*param_range["holding_period_days"]),
            "liquidity_threshold": 1000000.0,
            "max_order_pct_of_volume": 0.05,
            "trailing_stop_enabled": random.choice([True, False]),
        }

        logger.debug(f"参数进化模拟完成 - 档位: {tier}")

        return evolved_params

    def _simulate_backtest(  # pylint: disable=too-many-positional-arguments
        self,
        strategy: Strategy,  # pylint: disable=unused-argument
        tier: str,
        initial_capital: float,
        evolved_params: Dict[str, Any],  # pylint: disable=unused-argument
        test_duration_days: int,  # pylint: disable=unused-argument
    ) -> Dict[str, Any]:
        """模拟回测（内部方法）

        实际应该使用真实历史数据进行回测
        这里是简化的模拟版本

        Args:
            strategy: 策略
            tier: 档位
            initial_capital: 初始资金
            evolved_params: 进化参数
            test_duration_days: 测试时长

        Returns:
            性能指标字典
        """
        import random  # pylint: disable=import-outside-toplevel

        # 模拟不同档位的表现差异
        tier_performance_factor = {
            "tier1_micro": 1.2,  # 小资金灵活性高
            "tier2_small": 1.1,
            "tier3_medium": 1.0,
            "tier4_large": 0.9,  # 大资金受滑点影响
        }

        factor = tier_performance_factor.get(tier, 1.0)

        # 模拟收益率（考虑档位因素）
        base_return = random.uniform(0.05, 0.25) * factor

        # 模拟波动率
        volatility = random.uniform(0.10, 0.25)

        # 计算夏普比率
        sharpe_ratio = (base_return - 0.03) / volatility if volatility > 0 else 0

        # 模拟最大回撤
        max_drawdown_pct = -random.uniform(0.05, 0.20)

        # 模拟胜率
        win_rate = random.uniform(0.45, 0.65)

        # 计算最终资金
        final_capital = initial_capital * (1 + base_return)

        return {
            "final_capital": final_capital,
            "total_return_pct": base_return * 100,
            "sharpe_ratio": sharpe_ratio,
            "max_drawdown_pct": max_drawdown_pct * 100,
            "win_rate": win_rate,
        }

    async def _simulate_slippage_and_impact_for_tier(self, tier: str, avg_order_size: float) -> Dict[str, float]:
        """为档位模拟平均滑点和冲击成本（内部方法）

        Args:
            tier: 档位
            avg_order_size: 平均订单大小

        Returns:
            平均滑点和冲击成本
        """
        # 假设平均日成交额
        avg_daily_volume = 10000000.0  # 1千万

        # 调用滑点模拟
        result = await self.simulate_slippage_and_impact(
            tier=tier, order_size=avg_order_size, daily_volume=avg_daily_volume
        )

        return {"avg_slippage_pct": result["slippage_pct"], "avg_impact_cost_pct": result["impact_cost_pct"]}

    def _create_failed_result(
        self, strategy_name: str, tier: str, initial_capital: float, error_message: str
    ) -> ArenaTestResult:
        """创建失败的测试结果（内部方法）

        Args:
            strategy_name: 策略名称
            tier: 档位
            initial_capital: 初始资金
            error_message: 错误信息

        Returns:
            失败的测试结果
        """
        return ArenaTestResult(
            strategy_name=strategy_name,
            test_tier=tier,
            initial_capital=initial_capital,
            final_capital=initial_capital,
            total_return_pct=0.0,
            sharpe_ratio=0.0,
            max_drawdown_pct=0.0,
            win_rate=0.0,
            evolved_params={"error": error_message},
            avg_slippage_pct=0.0,
            avg_impact_cost_pct=0.0,
            test_start_date=datetime.now().strftime("%Y-%m-%d"),
            test_end_date=datetime.now().strftime("%Y-%m-%d"),
        )
