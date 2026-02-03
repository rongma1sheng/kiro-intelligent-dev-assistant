"""
斯巴达Arena四层验证评估器

白皮书依据: 第四章 4.3.1 统一验证流程 - 斯巴达Arena考核

整合四层验证体系:
- 第一层: 投研级指标评价 (StrategyEvaluator)
- 第二层: 时间稳定性验证 (RollingBacktest)
- 第三层: 防过拟合验证 (WalkForwardAnalysis)
- 第四层: 极限压力测试 (StressTestAnalyzer)

作者: MIA Team
日期: 2026-01-20
版本: v1.0.0
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from src.evolution.rolling_backtest import RollingBacktest, WindowMode
from src.evolution.strategy_evaluator import MarketType, StrategyEvaluator
from src.evolution.stress_test_analyzer import StressTestAnalyzer
from src.evolution.walk_forward_analysis import WalkForwardAnalysis, WalkForwardMode

logger = logging.getLogger(__name__)


class ValidationLayer(Enum):
    """验证层级"""

    LAYER_1_BASIC = "layer_1_basic"  # 第一层：投研级指标
    LAYER_2_STABILITY = "layer_2_stability"  # 第二层：时间稳定性
    LAYER_3_OVERFITTING = "layer_3_overfitting"  # 第三层：防过拟合
    LAYER_4_STRESS = "layer_4_stress"  # 第四层：极限压力


@dataclass
class LayerResult:
    """单层验证结果"""

    layer: ValidationLayer
    passed: bool
    score: float  # 0-1之间

    # 详细结果
    details: Dict[str, Any] = field(default_factory=dict)

    # 失败原因
    failure_reason: Optional[str] = None

    # 评级 (仅第一层有)
    rating: Optional[str] = None  # EXCELLENT, QUALIFIED, UNQUALIFIED


@dataclass
class ArenaTestResult:
    """Arena测试综合结果"""

    passed: bool
    overall_score: float

    # 各层结果
    layer_results: Dict[str, LayerResult] = field(default_factory=dict)

    # 统计信息
    layers_passed: int = 0
    layers_failed: int = 0
    total_layers: int = 4

    # 失败层级列表
    failed_layers: List[str] = field(default_factory=list)

    # 测试时间
    test_date: datetime = field(default_factory=datetime.now)

    # 策略信息
    strategy_name: Optional[str] = None
    strategy_type: Optional[str] = None


class SpartaArenaEvaluator:
    """斯巴达Arena四层验证评估器

    白皮书依据: 第四章 4.3.1 统一验证流程

    执行完整的四层验证:
    1. 投研级指标评价 (30%) - 必须达到"合格"级别
    2. 时间稳定性验证 (15%) - 正收益窗口≥70%
    3. 防过拟合验证 (15%) - 效率比率≥0.5
    4. 极限压力测试 (40%) - 至少4个场景通过

    综合通过标准:
    - 各层都必须达标
    - 综合评分 ≥ 0.75
    """

    # 各层权重 (白皮书定义)
    LAYER_WEIGHTS = {
        "layer_1_basic": 0.30,  # 投研级指标权重30%
        "layer_2_stability": 0.15,  # 时间稳定性权重15%
        "layer_3_overfitting": 0.15,  # 防过拟合权重15%
        "layer_4_stress": 0.40,  # 极限压力权重40%
    }

    # 各层通过标准
    LAYER_PASS_CRITERIA = {
        "layer_1_basic": 0.8,  # 投研级≥合格 (评分≥0.8)
        "layer_2_stability": 0.7,  # 时间稳定性≥70%
        "layer_3_overfitting": 0.6,  # 防过拟合≥60%
        "layer_4_stress": 0.7,  # 压力测试≥70%
    }

    def __init__(self, market_type: str = "A_STOCK"):
        """初始化斯巴达Arena评估器

        Args:
            market_type: 市场类型 ('A_STOCK', 'FUTURES', 'CRYPTO')
        """
        self.market_type = market_type

        # 初始化各层评估器
        self.strategy_evaluator = StrategyEvaluator(market_type=MarketType[market_type])

        self.rolling_backtest = RollingBacktest(
            market_type=MarketType[market_type],
            window_mode=WindowMode.FIXED,
            window_size_days=126,  # 最小窗口大小（半年）
            step_size_days=20,
        )

        self.walk_forward = WalkForwardAnalysis(
            market_type=MarketType[market_type], mode=WalkForwardMode.ROLLING, is_ratio=0.7
        )

        self.stress_test = StressTestAnalyzer(market_type=market_type)

        logger.info(  # pylint: disable=logging-fstring-interpolation
            f"初始化SpartaArenaEvaluator: market_type={market_type}"
        )  # pylint: disable=logging-fstring-interpolation

    async def evaluate_strategy(  # pylint: disable=too-many-positional-arguments
        self,
        strategy_returns: pd.Series,
        market_returns: pd.Series,
        market_volume: Optional[pd.Series] = None,
        strategy_name: str = "Unknown",
        strategy_type: str = "Unknown",
    ) -> ArenaTestResult:
        """执行完整的四层验证

        白皮书依据: 第四章 4.3.1 - 斯巴达Arena综合评估

        Args:
            strategy_returns: 策略收益率序列
            market_returns: 市场收益率序列
            market_volume: 市场成交量序列 (可选)
            strategy_name: 策略名称
            strategy_type: 策略类型

        Returns:
            ArenaTestResult: Arena测试综合结果
        """
        logger.info(f"开始斯巴达Arena四层验证: {strategy_name}")  # pylint: disable=logging-fstring-interpolation

        layer_results = {}

        # ==================== 第一层：投研级指标评价 ====================
        logger.info("执行第一层验证: 投研级指标评价")
        layer1_result = await self._evaluate_layer1_basic(strategy_returns, market_returns)
        layer_results["layer_1_basic"] = layer1_result

        # 第一层必须达到"合格"级别才能继续
        if not layer1_result.passed:
            logger.warning(  # pylint: disable=logging-fstring-interpolation
                f"第一层验证未通过: {layer1_result.failure_reason}"
            )  # pylint: disable=logging-fstring-interpolation
            return self._create_early_failure_result(
                layer_results, strategy_name, strategy_type, failed_at_layer="第一层：投研级指标评价"
            )

        # ==================== 第二层：时间稳定性验证 ====================
        logger.info("执行第二层验证: 时间稳定性验证")
        layer2_result = await self._evaluate_layer2_stability(strategy_returns)
        layer_results["layer_2_stability"] = layer2_result

        # ==================== 第三层：防过拟合验证 ====================
        logger.info("执行第三层验证: 防过拟合验证")
        layer3_result = await self._evaluate_layer3_overfitting(strategy_returns, market_returns)
        layer_results["layer_3_overfitting"] = layer3_result

        # ==================== 第四层：极限压力测试 ====================
        logger.info("执行第四层验证: 极限压力测试")
        layer4_result = await self._evaluate_layer4_stress(strategy_returns, market_returns, market_volume)
        layer_results["layer_4_stress"] = layer4_result

        # ==================== 综合评分 ====================
        overall_score = self._calculate_overall_score(layer_results)

        # 统计通过情况
        layers_passed = sum(1 for result in layer_results.values() if result.passed)
        layers_failed = 4 - layers_passed
        failed_layers = [layer for layer, result in layer_results.items() if not result.passed]

        # 判断整体是否通过
        # 标准: 各层都必须达标 且 综合评分≥0.75
        passed = layers_passed == 4 and overall_score >= 0.75

        logger.info(  # pylint: disable=logging-fstring-interpolation
            f"斯巴达Arena验证完成: {strategy_name}\n"
            f"  通过层级: {layers_passed}/4\n"
            f"  综合评分: {overall_score:.2%}\n"
            f"  整体结果: {'✅ 通过' if passed else '❌ 未通过'}"
        )

        return ArenaTestResult(
            passed=passed,
            overall_score=overall_score,
            layer_results=layer_results,
            layers_passed=layers_passed,
            layers_failed=layers_failed,
            failed_layers=failed_layers,
            strategy_name=strategy_name,
            strategy_type=strategy_type,
        )

    async def _evaluate_layer1_basic(
        self, strategy_returns: pd.Series, market_returns: pd.Series  # pylint: disable=unused-argument
    ) -> LayerResult:  # pylint: disable=unused-argument
        """第一层：投研级指标评价

        工具: StrategyEvaluator
        权重: 30%
        标准: 必须达到"合格"级别 (评分≥0.8)
        """
        try:
            # 将收益率转换为净值曲线
            equity = (1 + strategy_returns).cumprod()

            # 使用StrategyEvaluator进行评价
            eval_result = self.strategy_evaluator.evaluate_strategy(equity=equity, trades=None, freq=252)

            # 使用check_thresholds检查是否达标
            threshold_result = self.strategy_evaluator.check_thresholds(eval_result)

            # 计算评分 (基于评级)
            rating_scores = {"优秀": 1.0, "合格": 0.8, "不合格": 0.5}
            grade = threshold_result.get("grade", "不合格")
            score = rating_scores.get(grade, 0.5)

            # 转换为英文评级（用于测试兼容性）
            rating_map = {"优秀": "EXCELLENT", "合格": "QUALIFIED", "不合格": "UNQUALIFIED"}
            rating = rating_map.get(grade, "UNQUALIFIED")

            # 判断是否通过 (必须达到"合格"级别)
            passed = threshold_result.get("qualified", False)

            failure_reason = None if passed else f"投研级评级为{grade}，未达到合格标准"

            return LayerResult(
                layer=ValidationLayer.LAYER_1_BASIC,
                passed=passed,
                score=score,
                rating=rating,  # 使用英文评级
                details={"metrics": eval_result, "threshold_result": threshold_result},
                failure_reason=failure_reason,
            )

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"第一层验证失败: {e}")  # pylint: disable=logging-fstring-interpolation
            return LayerResult(
                layer=ValidationLayer.LAYER_1_BASIC, passed=False, score=0.0, failure_reason=f"评估异常: {str(e)}"
            )

    async def _evaluate_layer2_stability(self, strategy_returns: pd.Series) -> LayerResult:
        """第二层：时间稳定性验证

        工具: RollingBacktest
        权重: 15%
        标准: 正收益窗口占比≥70%, 变异系数达标
        """
        try:
            # 创建简单的策略函数：直接返回净值曲线
            (1 + strategy_returns).cumprod()

            # 创建数据框（使用日期索引）
            data = pd.DataFrame({"returns": strategy_returns}, index=strategy_returns.index)

            # 定义策略函数
            def strategy_func(window_data):
                window_returns = window_data["returns"]
                window_equity = (1 + window_returns).cumprod()
                return window_equity, None

            # 使用RollingBacktest进行验证
            rolling_result = self.rolling_backtest.run_backtest(strategy_func=strategy_func, data=data, freq=252)

            # 提取稳定性指标
            stability_metrics = rolling_result.stability_metrics
            positive_ratio = stability_metrics.get("positive_window_ratio", 0)
            return_cv = stability_metrics.get("return_coefficient_variation", 999)
            sharpe_cv = stability_metrics.get("sharpe_coefficient_variation", 999)

            # 计算评分
            positive_score = min(1.0, positive_ratio / 0.7)
            cv_score = max(0, 1 - return_cv / 2.0) * 0.5 + max(0, 1 - sharpe_cv / 1.0) * 0.5
            score = positive_score * 0.7 + cv_score * 0.3

            # 判断是否通过
            passed = positive_ratio >= 0.70 and return_cv <= 1.0 and sharpe_cv <= 0.5

            failure_reason = (
                None
                if passed
                else f"稳定性不达标: 正收益占比{positive_ratio:.1%}, 收益CV{return_cv:.2f}, 夏普CV{sharpe_cv:.2f}"
            )

            return LayerResult(
                layer=ValidationLayer.LAYER_2_STABILITY,
                passed=passed,
                score=score,
                details={
                    "stability_metrics": stability_metrics,
                    "aggregated_metrics": rolling_result.aggregated_metrics,
                },
                failure_reason=failure_reason,
            )

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"第二层验证失败: {e}")  # pylint: disable=logging-fstring-interpolation
            return LayerResult(
                layer=ValidationLayer.LAYER_2_STABILITY, passed=False, score=0.0, failure_reason=f"评估异常: {str(e)}"
            )

    async def _evaluate_layer3_overfitting(
        self, strategy_returns: pd.Series, market_returns: pd.Series  # pylint: disable=unused-argument
    ) -> LayerResult:  # pylint: disable=unused-argument
        """第三层：防过拟合验证

        工具: WalkForwardAnalysis
        权重: 15%
        标准: 效率比率≥0.5, IS-OOS一致性≥60%
        """
        try:
            # 简化实现：基于收益率序列计算过拟合指标
            # 将数据分为IS和OOS两部分
            split_point = int(len(strategy_returns) * 0.7)
            is_returns = strategy_returns.iloc[:split_point]
            oos_returns = strategy_returns.iloc[split_point:]

            # 计算IS和OOS的夏普比率
            is_sharpe = is_returns.mean() / is_returns.std() * np.sqrt(252) if is_returns.std() > 0 else 0
            oos_sharpe = oos_returns.mean() / oos_returns.std() * np.sqrt(252) if oos_returns.std() > 0 else 0

            # 计算效率比率
            efficiency_ratio = oos_sharpe / is_sharpe if is_sharpe > 0 else 0

            # 计算夏普衰减
            sharpe_degradation = max(0, (is_sharpe - oos_sharpe) / is_sharpe) if is_sharpe > 0 else 1.0

            # 计算IS-OOS一致性（收益方向一致性）
            is_positive = (is_returns > 0).sum() / len(is_returns) if len(is_returns) > 0 else 0
            oos_positive = (oos_returns > 0).sum() / len(oos_returns) if len(oos_returns) > 0 else 0
            consistency = 1 - abs(is_positive - oos_positive)

            # 计算OOS失败率（负收益天数占比）
            oos_failure_rate = (oos_returns < 0).sum() / len(oos_returns) if len(oos_returns) > 0 else 1.0

            # 计算评分
            efficiency_score = min(1.0, efficiency_ratio / 0.5)
            consistency_score = min(1.0, consistency / 0.6)
            degradation_score = max(0, 1 - sharpe_degradation / 1.0)
            failure_score = max(0, 1 - oos_failure_rate / 0.3)

            score = efficiency_score * 0.35 + consistency_score * 0.35 + degradation_score * 0.15 + failure_score * 0.15

            # 判断是否通过
            passed = (
                efficiency_ratio >= 0.5  # pylint: disable=r1716
                and consistency >= 0.60
                and sharpe_degradation <= 0.5
                and oos_failure_rate <= 0.30
            )

            failure_reason = (
                None
                if passed
                else f"过拟合风险: 效率比{efficiency_ratio:.2f}, 一致性{consistency:.1%}, "
                f"夏普衰减{sharpe_degradation:.2f}, OOS失败率{oos_failure_rate:.1%}"
            )

            return LayerResult(
                layer=ValidationLayer.LAYER_3_OVERFITTING,
                passed=passed,
                score=score,
                details={
                    "efficiency_ratio": efficiency_ratio,
                    "is_oos_consistency": consistency,
                    "sharpe_degradation": sharpe_degradation,
                    "oos_failure_rate": oos_failure_rate,
                    "is_sharpe": is_sharpe,
                    "oos_sharpe": oos_sharpe,
                },
                failure_reason=failure_reason,
            )

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"第三层验证失败: {e}")  # pylint: disable=logging-fstring-interpolation
            return LayerResult(
                layer=ValidationLayer.LAYER_3_OVERFITTING, passed=False, score=0.0, failure_reason=f"评估异常: {str(e)}"
            )

    async def _evaluate_layer4_stress(
        self, strategy_returns: pd.Series, market_returns: pd.Series, market_volume: Optional[pd.Series]
    ) -> LayerResult:
        """第四层：极限压力测试

        工具: StressTestAnalyzer
        权重: 40%
        标准: 至少4个场景通过, 综合评分≥0.7
        """
        try:
            # 使用StressTestAnalyzer进行验证
            stress_result = await self.stress_test.run_all_scenarios(strategy_returns, market_returns, market_volume)

            # 提取压力测试指标
            overall_score = stress_result.overall_score
            scenarios_passed = stress_result.scenarios_passed
            failed_scenarios = stress_result.failed_scenarios

            # 判断是否通过
            passed = scenarios_passed >= 4 and overall_score >= 0.7

            failure_reason = (
                None
                if passed
                else f"压力测试不达标: 通过{scenarios_passed}/5个场景, "
                f"综合评分{overall_score:.1%}, 失败场景: {', '.join(failed_scenarios)}"
            )

            return LayerResult(
                layer=ValidationLayer.LAYER_4_STRESS,
                passed=passed,
                score=overall_score,
                details={
                    "scenarios_passed": scenarios_passed,
                    "scenarios_failed": stress_result.scenarios_failed,
                    "failed_scenarios": failed_scenarios,
                    "scenario_results": {
                        name: {"passed": result.passed, "score": result.score, "failure_reason": result.failure_reason}
                        for name, result in stress_result.scenario_results.items()
                    },
                },
                failure_reason=failure_reason,
            )

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"第四层验证失败: {e}")  # pylint: disable=logging-fstring-interpolation
            return LayerResult(
                layer=ValidationLayer.LAYER_4_STRESS, passed=False, score=0.0, failure_reason=f"评估异常: {str(e)}"
            )

    def _calculate_overall_score(self, layer_results: Dict[str, LayerResult]) -> float:
        """计算综合评分

        白皮书依据: 第四章 4.3.1 - 综合评分算法

        综合评分 = Σ(各层评分 × 各层权重)
        """
        overall_score = 0.0

        for layer_name, result in layer_results.items():
            weight = self.LAYER_WEIGHTS.get(layer_name, 0)
            overall_score += result.score * weight

        return overall_score

    def _create_early_failure_result(
        self, layer_results: Dict[str, LayerResult], strategy_name: str, strategy_type: str, failed_at_layer: str
    ) -> ArenaTestResult:
        """创建提前失败的结果

        当第一层验证未通过时，不继续后续验证
        """
        overall_score = self._calculate_overall_score(layer_results)

        return ArenaTestResult(
            passed=False,
            overall_score=overall_score,
            layer_results=layer_results,
            layers_passed=0,
            layers_failed=1,
            failed_layers=[failed_at_layer],
            strategy_name=strategy_name,
            strategy_type=strategy_type,
        )

    def generate_detailed_report(self, result: ArenaTestResult) -> str:
        """生成详细的验证报告

        Args:
            result: Arena测试结果

        Returns:
            str: 格式化的详细报告
        """
        report = []
        report.append("=" * 80)
        report.append(f"斯巴达Arena四层验证报告")  # pylint: disable=w1309
        report.append("=" * 80)
        report.append(f"策略名称: {result.strategy_name}")
        report.append(f"策略类型: {result.strategy_type}")
        report.append(f"测试时间: {result.test_date.strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"")  # pylint: disable=w1309
        report.append(f"综合结果: {'✅ 通过' if result.passed else '❌ 未通过'}")
        report.append(f"综合评分: {result.overall_score:.2%}")
        report.append(f"通过层级: {result.layers_passed}/{result.total_layers}")
        report.append("")

        # 各层详细结果
        report.append("-" * 80)
        report.append("各层验证详情:")
        report.append("-" * 80)

        layer_names = {
            "layer_1_basic": "第一层：投研级指标评价",
            "layer_2_stability": "第二层：时间稳定性验证",
            "layer_3_overfitting": "第三层：防过拟合验证",
            "layer_4_stress": "第四层：极限压力测试",
        }

        for layer_key, layer_name in layer_names.items():
            if layer_key in result.layer_results:
                layer_result = result.layer_results[layer_key]
                weight = self.LAYER_WEIGHTS[layer_key]

                report.append(f"\n{layer_name} (权重{weight:.0%})")
                report.append(f"  状态: {'✅ 通过' if layer_result.passed else '❌ 未通过'}")
                report.append(f"  评分: {layer_result.score:.2%}")

                if layer_result.rating:
                    report.append(f"  评级: {layer_result.rating}")

                if not layer_result.passed and layer_result.failure_reason:
                    report.append(f"  失败原因: {layer_result.failure_reason}")

        report.append("")
        report.append("=" * 80)

        return "\n".join(report)
