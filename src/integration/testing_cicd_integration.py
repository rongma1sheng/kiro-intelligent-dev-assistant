"""Testing-CI/CD Integration - 测试与CI/CD集成

白皮书依据: 第十四章 14.1 质量标准, 第十二章 12.2 测试与CI/CD集成
版本: v1.0.0
作者: MIA Team
日期: 2026-01-27

核心功能:
1. 集成测试覆盖率分析器与CI/CD流程
2. 集成代码质量检查器与CI/CD流程
3. 发布跨章节事件通知质量问题
4. 自动化质量门禁检查
"""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger

from src.infra.cross_chapter_event_bus import CrossChapterEvent, CrossChapterEventBus, CrossChapterEventType
from src.infra.event_bus import EventPriority
from src.quality.code_quality_checker import CodeQualityChecker, QualityMetrics
from src.quality.test_coverage_analyzer import CoverageTarget, TestCoverageAnalyzer


@dataclass
class QualityGateResult:
    """质量门禁检查结果

    白皮书依据: 第十四章 14.1.1 测试覆盖率目标

    Attributes:
        passed: 是否通过
        coverage_passed: 覆盖率检查是否通过
        quality_passed: 质量检查是否通过
        coverage_result: 覆盖率检查结果
        quality_metrics: 质量指标
        violations: 违规项列表
        timestamp: 检查时间
    """

    passed: bool
    coverage_passed: bool
    quality_passed: bool
    coverage_result: Dict[str, Any]
    quality_metrics: QualityMetrics
    violations: List[Dict[str, Any]]
    timestamp: datetime


class TestingCICDIntegration:
    """测试与CI/CD集成

    白皮书依据: 第十四章 14.1 质量标准, 第十二章 12.2 测试与CI/CD集成

    核心功能:
    1. 自动化测试覆盖率检查
    2. 自动化代码质量检查
    3. 质量门禁强制执行
    4. 跨章节事件发布（质量问题通知）

    集成流程:
    1. 代码提交 → 触发CI/CD
    2. 运行测试 → 生成覆盖率报告
    3. 执行质量检查 → 生成质量报告
    4. 强制执行门禁 → 通过/失败
    5. 发布跨章节事件 → 通知相关章节

    使用示例:
        >>> integration = TestingCICDIntegration(
        ...     project_root=Path.cwd(),
        ...     event_bus=cross_chapter_bus
        ... )
        >>> await integration.initialize()
        >>>
        >>> # 执行质量门禁检查
        >>> result = await integration.run_quality_gates()
        >>> if not result.passed:
        ...     print(f"质量门禁失败: {result.violations}")
    """

    def __init__(
        self,
        project_root: Optional[Path] = None,
        event_bus: Optional[CrossChapterEventBus] = None,
        coverage_targets: Optional[CoverageTarget] = None,
    ):
        """初始化测试与CI/CD集成

        Args:
            project_root: 项目根目录，默认为当前目录
            event_bus: 跨章节事件总线实例
            coverage_targets: 覆盖率目标，默认使用标准目标
        """
        self.project_root = project_root or Path.cwd()
        self.event_bus = event_bus

        # 初始化测试覆盖率分析器
        self.coverage_analyzer = TestCoverageAnalyzer(project_root=self.project_root)
        if coverage_targets:
            self.coverage_analyzer.coverage_targets = coverage_targets

        # 初始化代码质量检查器
        self.quality_checker = CodeQualityChecker(project_root=self.project_root)

        # 统计信息
        self.stats = {
            "total_checks": 0,
            "passed_checks": 0,
            "failed_checks": 0,
            "coverage_failures": 0,
            "quality_failures": 0,
            "events_published": 0,
            "start_time": None,
        }

        logger.info(f"测试与CI/CD集成初始化完成: project_root={self.project_root}")

    async def initialize(self):
        """初始化集成模块"""
        try:
            # 如果没有提供事件总线，获取全局实例
            if self.event_bus is None:
                from src.infra.cross_chapter_event_bus import (  # pylint: disable=import-outside-toplevel
                    get_cross_chapter_event_bus,
                )

                self.event_bus = await get_cross_chapter_event_bus()

            self.stats["start_time"] = datetime.now()

            logger.info("测试与CI/CD集成启动成功")

        except Exception as e:
            logger.error(f"测试与CI/CD集成初始化失败: {e}")
            raise

    async def run_quality_gates(
        self, coverage_file: Optional[Path] = None, target_path: Optional[Path] = None
    ) -> QualityGateResult:
        """执行质量门禁检查

        白皮书依据: 第十四章 14.1 质量标准

        执行流程:
        1. 分析测试覆盖率
        2. 强制执行覆盖率门禁
        3. 执行代码质量检查
        4. 综合评估是否通过
        5. 发布跨章节事件（如果失败）

        Args:
            coverage_file: 覆盖率数据文件路径
            target_path: 目标代码路径

        Returns:
            质量门禁检查结果

        Raises:
            ValueError: 当检查失败时
        """
        self.stats["total_checks"] += 1

        logger.info("开始执行质量门禁检查")

        violations = []

        # 1. 分析测试覆盖率
        try:
            logger.info("步骤 1/3: 分析测试覆盖率")
            self.coverage_analyzer.analyze_coverage(coverage_file)

            # 2. 强制执行覆盖率门禁
            logger.info("步骤 2/3: 强制执行覆盖率门禁")
            coverage_result = self.coverage_analyzer.enforce_coverage_gates()

            coverage_passed = coverage_result["passed"]

            if not coverage_passed:
                self.stats["coverage_failures"] += 1
                violations.extend(coverage_result["violations"])

                # 发布覆盖率门禁失败事件
                await self._publish_coverage_gate_failed_event(coverage_result)

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"覆盖率检查失败: {e}")
            coverage_passed = False
            coverage_result = {
                "passed": False,
                "overall_coverage": 0.0,
                "category_coverage": {},
                "violations": [{"message": f"覆盖率检查异常: {e}"}],
            }
            violations.append({"message": f"覆盖率检查异常: {e}"})

        # 3. 执行代码质量检查
        try:
            logger.info("步骤 3/3: 执行代码质量检查")
            quality_metrics = self.quality_checker.check_all(target_path)

            quality_passed = quality_metrics.passed

            if not quality_passed:
                self.stats["quality_failures"] += 1

                # 添加质量违规项
                if quality_metrics.complexity_score < 80.0:
                    violations.append(
                        {
                            "category": "complexity",
                            "message": f"圈复杂度评分不达标: {quality_metrics.complexity_score:.2f} < 80.0",
                        }
                    )

                if quality_metrics.style_score < 80.0:
                    violations.append(
                        {
                            "category": "style",
                            "message": f"代码风格评分不达标: {quality_metrics.style_score:.2f} < 80.0",
                        }
                    )

                if quality_metrics.type_coverage < 70.0:
                    violations.append(
                        {
                            "category": "type_coverage",
                            "message": f"类型注解覆盖率不达标: {quality_metrics.type_coverage:.2f} < 70.0",
                        }
                    )

                if quality_metrics.security_issues > 0:
                    violations.append(
                        {"category": "security", "message": f"发现安全问题: {quality_metrics.security_issues} 个"}
                    )

                # 发布质量检查失败事件
                await self._publish_quality_check_failed_event(quality_metrics)

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"质量检查失败: {e}")
            quality_passed = False
            quality_metrics = QualityMetrics(
                complexity_score=0.0, style_score=0.0, type_coverage=0.0, security_issues=999, passed=False
            )
            violations.append({"message": f"质量检查异常: {e}"})

        # 综合评估
        passed = coverage_passed and quality_passed

        if passed:
            self.stats["passed_checks"] += 1
            logger.info("✅ 质量门禁检查通过")
        else:
            self.stats["failed_checks"] += 1
            logger.error(f"❌ 质量门禁检查失败，共 {len(violations)} 项违规")
            for violation in violations:
                logger.error(f"  - {violation.get('message', violation)}")

        result = QualityGateResult(
            passed=passed,
            coverage_passed=coverage_passed,
            quality_passed=quality_passed,
            coverage_result=coverage_result,
            quality_metrics=quality_metrics,
            violations=violations,
            timestamp=datetime.now(),
        )

        return result

    async def _publish_coverage_gate_failed_event(self, coverage_result: Dict[str, Any]):
        """发布覆盖率门禁失败事件

        白皮书依据: 第十二章 12.2 测试与CI/CD集成

        事件路由: Chapter 14 (Testing) -> Chapter 17 (CI/CD)

        Args:
            coverage_result: 覆盖率检查结果
        """
        try:
            if self.event_bus is None:
                logger.warning("事件总线未初始化，跳过事件发布")
                return

            event = CrossChapterEvent(
                event_type=CrossChapterEventType.COVERAGE_GATE_FAILED,
                source_chapter=14,
                target_chapter=17,
                data={
                    "overall_coverage": coverage_result["overall_coverage"],
                    "category_coverage": coverage_result["category_coverage"],
                    "violations": coverage_result["violations"],
                    "timestamp": datetime.now().isoformat(),
                },
                priority=EventPriority.HIGH,
            )

            success = await self.event_bus.publish(event)

            if success:
                self.stats["events_published"] += 1
                logger.info("覆盖率门禁失败事件已发布 (Chapter 14 -> 17)")

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"发布覆盖率门禁失败事件失败: {e}")

    async def _publish_quality_check_failed_event(self, quality_metrics: QualityMetrics):
        """发布质量检查失败事件

        白皮书依据: 第十二章 12.2 测试与CI/CD集成

        事件路由: Chapter 14 (Testing) -> Chapter 17 (CI/CD)

        Args:
            quality_metrics: 质量指标
        """
        try:
            if self.event_bus is None:
                logger.warning("事件总线未初始化，跳过事件发布")
                return

            event = CrossChapterEvent(
                event_type=CrossChapterEventType.QUALITY_CHECK_FAILED,
                source_chapter=14,
                target_chapter=17,
                data={
                    "complexity_score": quality_metrics.complexity_score,
                    "style_score": quality_metrics.style_score,
                    "type_coverage": quality_metrics.type_coverage,
                    "security_issues": quality_metrics.security_issues,
                    "timestamp": datetime.now().isoformat(),
                },
                priority=EventPriority.HIGH,
            )

            success = await self.event_bus.publish(event)

            if success:
                self.stats["events_published"] += 1
                logger.info("质量检查失败事件已发布 (Chapter 14 -> 17)")

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"发布质量检查失败事件失败: {e}")

    async def check_coverage_only(self, coverage_file: Optional[Path] = None) -> Dict[str, Any]:
        """仅检查测试覆盖率

        Args:
            coverage_file: 覆盖率数据文件路径

        Returns:
            覆盖率检查结果
        """
        try:
            logger.info("开始检查测试覆盖率")

            # 分析覆盖率
            self.coverage_analyzer.analyze_coverage(coverage_file)

            # 强制执行门禁
            coverage_result = self.coverage_analyzer.enforce_coverage_gates()

            if not coverage_result["passed"]:
                # 发布事件
                await self._publish_coverage_gate_failed_event(coverage_result)

            return coverage_result

        except Exception as e:
            logger.error(f"覆盖率检查失败: {e}")
            raise

    async def check_quality_only(self, target_path: Optional[Path] = None) -> QualityMetrics:
        """仅检查代码质量

        Args:
            target_path: 目标代码路径

        Returns:
            质量指标
        """
        try:
            logger.info("开始检查代码质量")

            # 执行质量检查
            quality_metrics = self.quality_checker.check_all(target_path)

            if not quality_metrics.passed:
                # 发布事件
                await self._publish_quality_check_failed_event(quality_metrics)

            return quality_metrics

        except Exception as e:
            logger.error(f"质量检查失败: {e}")
            raise

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息

        Returns:
            统计信息字典
        """
        uptime = (datetime.now() - self.stats["start_time"]).total_seconds() if self.stats["start_time"] else 0

        success_rate = self.stats["passed_checks"] / max(self.stats["total_checks"], 1)

        return {
            **self.stats,
            "uptime_seconds": uptime,
            "success_rate": success_rate,
            "coverage_failure_rate": (self.stats["coverage_failures"] / max(self.stats["total_checks"], 1)),
            "quality_failure_rate": (self.stats["quality_failures"] / max(self.stats["total_checks"], 1)),
        }


# 全局集成实例
_global_testing_cicd_integration: Optional[TestingCICDIntegration] = None


async def get_testing_cicd_integration(
    project_root: Optional[Path] = None, event_bus: Optional[CrossChapterEventBus] = None
) -> TestingCICDIntegration:
    """获取全局测试与CI/CD集成实例

    Args:
        project_root: 项目根目录
        event_bus: 跨章节事件总线实例

    Returns:
        测试与CI/CD集成实例
    """
    global _global_testing_cicd_integration  # pylint: disable=w0603

    if _global_testing_cicd_integration is None:
        _global_testing_cicd_integration = TestingCICDIntegration(project_root=project_root, event_bus=event_bus)
        await _global_testing_cicd_integration.initialize()

    return _global_testing_cicd_integration


async def run_ci_quality_gates(
    coverage_file: Optional[Path] = None, target_path: Optional[Path] = None
) -> QualityGateResult:
    """全局CI质量门禁检查函数

    Args:
        coverage_file: 覆盖率数据文件路径
        target_path: 目标代码路径

    Returns:
        质量门禁检查结果
    """
    integration = await get_testing_cicd_integration()
    return await integration.run_quality_gates(coverage_file, target_path)
