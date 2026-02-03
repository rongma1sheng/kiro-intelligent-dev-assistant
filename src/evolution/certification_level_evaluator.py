"""认证等级评估器

白皮书依据: 第四章 4.3.2 认证等级评定标准

本模块实现认证等级评估器，根据Arena验证结果和模拟盘验证结果自动评定策略的认证等级。
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger

from .z2h_data_models import CertificationLevel


@dataclass
class LayerScore:
    """层级评分

    Attributes:
        layer_name: 层级名称
        score: 评分（0.0-1.0）
        passed: 是否通过
        rating: 评级（EXCELLENT/GOOD/QUALIFIED/FAILED）
    """

    layer_name: str
    score: float
    passed: bool
    rating: str


@dataclass
class LevelEvaluationResult:
    """等级评估结果

    Attributes:
        certification_level: 认证等级
        overall_score: 综合评分
        layer_scores: 各层级评分
        passed_layers: 通过的层数
        failed_layers: 失败的层级列表
        evaluation_reason: 评定原因
        meets_requirements: 是否满足认证要求
    """

    certification_level: CertificationLevel
    overall_score: float
    layer_scores: List[LayerScore]
    passed_layers: int
    failed_layers: List[str]
    evaluation_reason: str
    meets_requirements: bool


class CertificationLevelEvaluator:
    """认证等级评估器

    白皮书依据: 第四章 4.3.2 认证等级评定标准

    根据Arena验证结果和模拟盘验证结果自动评定策略的认证等级。

    认证等级标准（完整版）：

    PLATINUM（白金级）:
    - Arena综合评分 ≥ 0.90
    - Layer 1（投研级指标）≥ 0.95
    - Layer 2（时间稳定性）≥ 0.85
    - Layer 3（防过拟合）≥ 0.80
    - Layer 4（压力测试）≥ 0.85
    - 模拟盘夏普比率 ≥ 2.5
    - 模拟盘最大回撤 ≤ 10%
    - 模拟盘胜率 ≥ 65%

    GOLD（黄金级）:
    - Arena综合评分 ≥ 0.80
    - Layer 1 ≥ 0.85, Layer 2 ≥ 0.75, Layer 3 ≥ 0.70, Layer 4 ≥ 0.75
    - 模拟盘夏普比率 ≥ 2.0, 最大回撤 ≤ 12%, 胜率 ≥ 60%

    SILVER（白银级）:
    - Arena综合评分 ≥ 0.75
    - Layer 1 ≥ 0.80, Layer 2 ≥ 0.70, Layer 3 ≥ 0.60, Layer 4 ≥ 0.70
    - 模拟盘夏普比率 ≥ 1.5, 最大回撤 ≤ 15%, 胜率 ≥ 55%

    Attributes:
        platinum_threshold: 白金级Arena综合评分阈值，默认0.90
        gold_threshold: 黄金级Arena综合评分阈值，默认0.80
        silver_threshold: 白银级Arena综合评分阈值，默认0.75
        layer_excellent_threshold: 层级优秀阈值，默认0.90
        layer_good_threshold: 层级良好阈值，默认0.80
        layer_qualified_threshold: 层级合格阈值，默认0.75
    """

    # Arena各层特定阈值（按认证等级）
    CERTIFICATION_LAYER_THRESHOLDS = {
        "PLATINUM": {
            "layer_1": 0.95,  # 投研级指标
            "layer_2": 0.85,  # 时间稳定性
            "layer_3": 0.80,  # 防过拟合
            "layer_4": 0.85,  # 压力测试
        },
        "GOLD": {"layer_1": 0.85, "layer_2": 0.75, "layer_3": 0.70, "layer_4": 0.75},
        "SILVER": {"layer_1": 0.80, "layer_2": 0.70, "layer_3": 0.60, "layer_4": 0.70},
    }

    # 模拟盘指标阈值（按认证等级）
    SIMULATION_THRESHOLDS = {
        "PLATINUM": {"min_sharpe": 2.5, "max_drawdown": 0.10, "min_win_rate": 0.65},
        "GOLD": {"min_sharpe": 2.0, "max_drawdown": 0.12, "min_win_rate": 0.60},
        "SILVER": {"min_sharpe": 1.5, "max_drawdown": 0.15, "min_win_rate": 0.55},
    }

    def __init__(  # pylint: disable=too-many-positional-arguments
        self,
        platinum_threshold: float = 0.90,
        gold_threshold: float = 0.80,
        silver_threshold: float = 0.75,
        layer_excellent_threshold: float = 0.90,
        layer_good_threshold: float = 0.80,
        layer_qualified_threshold: float = 0.75,
    ):
        """初始化认证等级评估器

        Args:
            platinum_threshold: 白金级阈值，范围[0, 1]
            gold_threshold: 黄金级阈值，范围[0, 1]
            silver_threshold: 白银级阈值，范围[0, 1]
            layer_excellent_threshold: 层级优秀阈值，范围[0, 1]
            layer_good_threshold: 层级良好阈值，范围[0, 1]
            layer_qualified_threshold: 层级合格阈值，范围[0, 1]

        Raises:
            ValueError: 当阈值不在有效范围或顺序不正确时
        """
        # 验证阈值范围
        if not 0.0 <= platinum_threshold <= 1.0:
            raise ValueError(f"白金级阈值必须在[0, 1]范围内: {platinum_threshold}")

        if not 0.0 <= gold_threshold <= 1.0:
            raise ValueError(f"黄金级阈值必须在[0, 1]范围内: {gold_threshold}")

        if not 0.0 <= silver_threshold <= 1.0:
            raise ValueError(f"白银级阈值必须在[0, 1]范围内: {silver_threshold}")

        # 验证阈值顺序
        if not (platinum_threshold >= gold_threshold >= silver_threshold):  # pylint: disable=superfluous-parens
            raise ValueError(
                f"阈值顺序必须满足: platinum >= gold >= silver, "
                f"当前: {platinum_threshold} >= {gold_threshold} >= {silver_threshold}"
            )

        # 验证层级阈值
        if not 0.0 <= layer_excellent_threshold <= 1.0:
            raise ValueError(f"层级优秀阈值必须在[0, 1]范围内: {layer_excellent_threshold}")

        if not 0.0 <= layer_good_threshold <= 1.0:
            raise ValueError(f"层级良好阈值必须在[0, 1]范围内: {layer_good_threshold}")

        if not 0.0 <= layer_qualified_threshold <= 1.0:
            raise ValueError(f"层级合格阈值必须在[0, 1]范围内: {layer_qualified_threshold}")

        if not (
            layer_excellent_threshold >= layer_good_threshold >= layer_qualified_threshold
        ):  # pylint: disable=superfluous-parens
            raise ValueError(
                f"层级阈值顺序必须满足: excellent >= good >= qualified, "
                f"当前: {layer_excellent_threshold} >= {layer_good_threshold} >= {layer_qualified_threshold}"
            )

        self.platinum_threshold = platinum_threshold
        self.gold_threshold = gold_threshold
        self.silver_threshold = silver_threshold
        self.layer_excellent_threshold = layer_excellent_threshold
        self.layer_good_threshold = layer_good_threshold
        self.layer_qualified_threshold = layer_qualified_threshold

        logger.info(
            f"初始化CertificationLevelEvaluator: "
            f"PLATINUM≥{platinum_threshold}, GOLD≥{gold_threshold}, SILVER≥{silver_threshold}"
        )

    def evaluate_level(
        self,
        arena_overall_score: float,
        arena_layer_results: Dict[str, Dict[str, Any]],
        simulation_passed: bool = True,
        simulation_metrics: Optional[Dict[str, float]] = None,
    ) -> LevelEvaluationResult:
        """评估认证等级

        白皮书依据: Requirement 4.1-4.6

        根据Arena综合评分、各层级评分和模拟盘指标评定认证等级。

        Args:
            arena_overall_score: Arena综合评分，范围[0, 1]
            arena_layer_results: Arena各层级结果，格式为 {layer_name: {score: float, passed: bool, ...}}
            simulation_passed: 模拟盘是否通过，默认True
            simulation_metrics: 模拟盘指标，包含 sharpe_ratio, max_drawdown, win_rate

        Returns:
            LevelEvaluationResult: 等级评估结果

        Raises:
            ValueError: 当输入参数无效时
        """
        # 验证输入
        if not 0.0 <= arena_overall_score <= 1.0:
            raise ValueError(f"Arena综合评分必须在[0, 1]范围内: {arena_overall_score}")

        if not arena_layer_results:
            raise ValueError("Arena层级结果不能为空")

        logger.info(
            f"开始评估认证等级 - Arena综合评分: {arena_overall_score:.4f}, "
            f"层级数: {len(arena_layer_results)}, 模拟盘通过: {simulation_passed}"
        )

        # 解析层级评分
        layer_scores = self._parse_layer_scores(arena_layer_results)

        # 统计通过和失败的层级
        passed_layers = sum(1 for ls in layer_scores if ls.passed)
        failed_layers = [ls.layer_name for ls in layer_scores if not ls.passed]

        # 检查是否所有层级都通过
        all_layers_passed = len(failed_layers) == 0

        # 如果模拟盘未通过，直接拒绝认证
        if not simulation_passed:
            logger.warning("模拟盘验证未通过，拒绝认证")
            return LevelEvaluationResult(
                certification_level=CertificationLevel.NONE,
                overall_score=arena_overall_score,
                layer_scores=layer_scores,
                passed_layers=passed_layers,
                failed_layers=failed_layers,
                evaluation_reason="模拟盘验证未通过",
                meets_requirements=False,
            )

        # 如果有层级未通过，直接拒绝认证
        if not all_layers_passed:
            logger.warning(f"存在未通过的层级: {failed_layers}，拒绝认证")
            return LevelEvaluationResult(
                certification_level=CertificationLevel.NONE,
                overall_score=arena_overall_score,
                layer_scores=layer_scores,
                passed_layers=passed_layers,
                failed_layers=failed_layers,
                evaluation_reason=f"层级未通过: {', '.join(failed_layers)}",
                meets_requirements=False,
            )

        # 评定认证等级
        certification_level, reason = self._determine_level(arena_overall_score, layer_scores, simulation_metrics)

        meets_requirements = certification_level != CertificationLevel.NONE

        logger.info(
            f"认证等级评估完成 - 等级: {certification_level.value}, "
            f"综合评分: {arena_overall_score:.4f}, 原因: {reason}"
        )

        return LevelEvaluationResult(
            certification_level=certification_level,
            overall_score=arena_overall_score,
            layer_scores=layer_scores,
            passed_layers=passed_layers,
            failed_layers=failed_layers,
            evaluation_reason=reason,
            meets_requirements=meets_requirements,
        )

    def _parse_layer_scores(self, arena_layer_results: Dict[str, Dict[str, Any]]) -> List[LayerScore]:
        """解析层级评分

        从Arena层级结果中提取评分信息。

        Args:
            arena_layer_results: Arena各层级结果

        Returns:
            List[LayerScore]: 层级评分列表

        Raises:
            ValueError: 当层级结果格式不正确时
        """
        layer_scores = []

        for layer_name, layer_result in arena_layer_results.items():
            # 提取评分
            if "score" not in layer_result:
                raise ValueError(f"层级 {layer_name} 缺少 'score' 字段")

            score = layer_result["score"]

            if not isinstance(score, (int, float)):
                raise ValueError(f"层级 {layer_name} 的评分必须是数字: {score}")

            if not 0.0 <= score <= 1.0:
                raise ValueError(f"层级 {layer_name} 的评分必须在[0, 1]范围内: {score}")

            # 提取通过状态
            passed = layer_result.get("passed", score >= self.layer_qualified_threshold)

            # 确定评级
            rating = self._determine_layer_rating(score)

            layer_scores.append(LayerScore(layer_name=layer_name, score=score, passed=passed, rating=rating))

        return layer_scores

    def _determine_layer_rating(self, score: float) -> str:
        """确定层级评级

        根据评分确定层级评级。

        Args:
            score: 层级评分

        Returns:
            str: 评级（EXCELLENT/GOOD/QUALIFIED/FAILED）
        """
        if score >= self.layer_excellent_threshold:  # pylint: disable=no-else-return
            return "EXCELLENT"
        elif score >= self.layer_good_threshold:
            return "GOOD"
        elif score >= self.layer_qualified_threshold:
            return "QUALIFIED"
        else:
            return "FAILED"

    def _check_layer_requirements(self, layer_scores: List[LayerScore], certification_level: str) -> Tuple[bool, str]:
        """检查是否满足特定等级的各层要求

        白皮书依据: Requirement 4.2-4.4

        根据认证等级检查各层是否达到特定阈值。

        Args:
            layer_scores: 层级评分列表
            certification_level: 认证等级（PLATINUM/GOLD/SILVER）

        Returns:
            Tuple[bool, str]: (是否满足, 不满足原因)
        """
        if certification_level not in self.CERTIFICATION_LAYER_THRESHOLDS:
            return False, f"未知的认证等级: {certification_level}"

        thresholds = self.CERTIFICATION_LAYER_THRESHOLDS[certification_level]

        # 层级名称映射，支持多种命名格式
        layer_name_mapping = {
            "layer1_reality": "layer_1",
            "layer2_hell": "layer_2",
            "layer3_cross_market": "layer_3",
            "layer4_stress": "layer_4",
            "layer_1_basic": "layer_1",
            "layer_2_stability": "layer_2",
            "layer_3_overfitting": "layer_3",
            "layer_4_stress": "layer_4",
        }

        for ls in layer_scores:
            # 尝试映射层级名称
            normalized_name = layer_name_mapping.get(ls.layer_name, ls.layer_name)
            required_score = thresholds.get(normalized_name, 0.75)
            if ls.score < required_score:
                return False, f"{ls.layer_name} 评分 {ls.score:.4f} 低于 {certification_level} 要求 {required_score}"

        return True, ""

    def _check_simulation_requirements(
        self, simulation_metrics: Dict[str, float], certification_level: str
    ) -> Tuple[bool, str]:
        """检查是否满足特定等级的模拟盘要求

        白皮书依据: Requirement 4.2-4.4

        根据认证等级检查模拟盘指标是否达标。

        Args:
            simulation_metrics: 模拟盘指标，包含 sharpe_ratio, max_drawdown, win_rate
            certification_level: 认证等级（PLATINUM/GOLD/SILVER）

        Returns:
            Tuple[bool, str]: (是否满足, 不满足原因)
        """
        if certification_level not in self.SIMULATION_THRESHOLDS:
            return False, f"未知的认证等级: {certification_level}"

        thresholds = self.SIMULATION_THRESHOLDS[certification_level]

        sharpe_ratio = simulation_metrics.get("sharpe_ratio", 0.0)
        max_drawdown = simulation_metrics.get("max_drawdown", 1.0)
        win_rate = simulation_metrics.get("win_rate", 0.0)

        # 检查夏普比率
        if sharpe_ratio < thresholds["min_sharpe"]:
            return False, f"夏普比率 {sharpe_ratio:.2f} 低于 {certification_level} 要求 {thresholds['min_sharpe']}"

        # 检查最大回撤
        if max_drawdown > thresholds["max_drawdown"]:
            return (
                False,
                f"最大回撤 {max_drawdown:.2%} 高于 {certification_level} 要求 {thresholds['max_drawdown']:.2%}",
            )

        # 检查胜率
        if win_rate < thresholds["min_win_rate"]:
            return False, f"胜率 {win_rate:.2%} 低于 {certification_level} 要求 {thresholds['min_win_rate']:.2%}"

        return True, ""

    def _determine_level(  # pylint: disable=too-many-branches
        self,
        overall_score: float,
        layer_scores: List[LayerScore],
        simulation_metrics: Optional[Dict[str, float]] = None,
    ) -> Tuple[CertificationLevel, str]:
        """确定认证等级

        白皮书依据: Requirement 4.2-4.5

        根据综合评分、层级评分和模拟盘指标确定认证等级。

        Args:
            overall_score: 综合评分
            layer_scores: 层级评分列表
            simulation_metrics: 模拟盘指标（可选）

        Returns:
            Tuple[CertificationLevel, str]: (认证等级, 评定原因)
        """
        # 检查综合评分是否达到最低要求
        if overall_score < self.silver_threshold:
            return (CertificationLevel.NONE, f"Arena综合评分 {overall_score:.4f} 低于最低要求 {self.silver_threshold}")

        # 尝试评定PLATINUM
        if overall_score >= self.platinum_threshold:
            # 检查Arena各层是否满足PLATINUM要求
            layer_ok, layer_reason = self._check_layer_requirements(layer_scores, "PLATINUM")

            if layer_ok:
                # 如果提供了模拟盘指标，检查是否满足PLATINUM要求
                if simulation_metrics:
                    sim_ok, sim_reason = self._check_simulation_requirements(simulation_metrics, "PLATINUM")
                    if sim_ok:  # pylint: disable=no-else-return
                        return (
                            CertificationLevel.PLATINUM,
                            f"Arena综合评分 {overall_score:.4f} ≥ {self.platinum_threshold}，"
                            f"所有层级达标，模拟盘指标达标",
                        )
                    else:
                        logger.info(f"PLATINUM层级达标但模拟盘不达标: {sim_reason}")
                else:
                    # 没有模拟盘指标，仅基于Arena评分
                    return (
                        CertificationLevel.PLATINUM,
                        f"Arena综合评分 {overall_score:.4f} ≥ {self.platinum_threshold}，所有层级达标",
                    )
            else:
                logger.info(f"PLATINUM综合评分达标但层级不达标: {layer_reason}")

        # 尝试评定GOLD
        if overall_score >= self.gold_threshold:
            # 检查Arena各层是否满足GOLD要求
            layer_ok, layer_reason = self._check_layer_requirements(layer_scores, "GOLD")

            if layer_ok:
                # 如果提供了模拟盘指标，检查是否满足GOLD要求
                if simulation_metrics:
                    sim_ok, sim_reason = self._check_simulation_requirements(simulation_metrics, "GOLD")
                    if sim_ok:  # pylint: disable=no-else-return
                        return (
                            CertificationLevel.GOLD,
                            f"Arena综合评分 {overall_score:.4f} ≥ {self.gold_threshold}，"
                            f"所有层级达标，模拟盘指标达标",
                        )
                    else:
                        logger.info(f"GOLD层级达标但模拟盘不达标: {sim_reason}")
                else:
                    # 没有模拟盘指标，仅基于Arena评分
                    return (
                        CertificationLevel.GOLD,
                        f"Arena综合评分 {overall_score:.4f} ≥ {self.gold_threshold}，所有层级达标",
                    )
            else:
                logger.info(f"GOLD综合评分达标但层级不达标: {layer_reason}")

        # 尝试评定SILVER
        if overall_score >= self.silver_threshold:
            # 检查Arena各层是否满足SILVER要求
            layer_ok, layer_reason = self._check_layer_requirements(layer_scores, "SILVER")

            if layer_ok:
                # 如果提供了模拟盘指标，检查是否满足SILVER要求
                if simulation_metrics:
                    sim_ok, sim_reason = self._check_simulation_requirements(simulation_metrics, "SILVER")
                    if sim_ok:  # pylint: disable=no-else-return
                        return (
                            CertificationLevel.SILVER,
                            f"Arena综合评分 {overall_score:.4f} ≥ {self.silver_threshold}，"
                            f"所有层级达标，模拟盘指标达标",
                        )
                    else:
                        logger.info(f"SILVER层级达标但模拟盘不达标: {sim_reason}")
                else:
                    # 没有模拟盘指标，仅基于Arena评分
                    return (
                        CertificationLevel.SILVER,
                        f"Arena综合评分 {overall_score:.4f} ≥ {self.silver_threshold}，所有层级达标",
                    )
            else:
                logger.info(f"SILVER综合评分达标但层级不达标: {layer_reason}")

        # 所有等级都不满足
        return (
            CertificationLevel.NONE,
            f"Arena综合评分 {overall_score:.4f} 或层级��分或模拟盘指标未达到任何认证等级要求",
        )
