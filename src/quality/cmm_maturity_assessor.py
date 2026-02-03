"""CMM成熟度评估器

白皮书依据: 第十四章 14.1.3 CMM成熟度模型
"""

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional

from loguru import logger


class CMMLevel(Enum):
    """CMM成熟度级别

    白皮书依据: 第十四章 14.1.3 CMM成熟度模型
    """

    INITIAL = 1  # 初始级：混乱，成功依赖个人
    REPEATABLE = 2  # 可重复级：建立基本流程
    DEFINED = 3  # 已定义级：流程标准化文档化
    MANAGED = 4  # 已管理级：量化管理
    OPTIMIZING = 5  # 优化级：持续改进


@dataclass
class DimensionScore:
    """维度评分

    Attributes:
        dimension_name: 维度名称
        score: 评分 (0-5)
        level: CMM级别
        strengths: 优势列表
        gaps: 差距列表
    """

    dimension_name: str
    score: float
    level: CMMLevel
    strengths: List[str]
    gaps: List[str]


@dataclass
class MaturityAssessment:
    """成熟度评估结果

    白皮书依据: 第十四章 14.1.3 CMM成熟度模型

    Attributes:
        overall_score: 总体评分 (0-5)
        overall_level: 总体CMM级别
        dimension_scores: 各维度评分
        recommendations: 改进建议
        target_level: 目标级别
    """

    overall_score: float
    overall_level: CMMLevel
    dimension_scores: Dict[str, DimensionScore]
    recommendations: List[str]
    target_level: CMMLevel


class CMMMaturityAssessor:
    """CMM成熟度评估器

    白皮书依据: 第十四章 14.1.3 CMM成熟度模型

    核心功能：
    1. 评估系统在7个维度的成熟度
    2. 计算总体成熟度评分
    3. 识别差距和改进机会
    4. 生成改进建议

    七个评估维度：
    1. 可靠性 (Reliability)
    2. 测试覆盖 (Test Coverage)
    3. 监控体系 (Monitoring)
    4. 安全合规 (Security & Compliance)
    5. 性能优化 (Performance)
    6. 文档完整 (Documentation)
    7. 运维标准 (Operations)

    Attributes:
        project_root: 项目根目录
        target_level: 目标CMM级别
    """

    def __init__(self, project_root: Optional[Path] = None, target_level: CMMLevel = CMMLevel.DEFINED):
        """初始化CMM成熟度评估器

        Args:
            project_root: 项目根目录，默认为当前目录
            target_level: 目标CMM级别，默认为Level 3 (已定义级)
        """
        self.project_root = project_root or Path.cwd()
        self.target_level = target_level

        logger.info(
            f"初始化CMMMaturityAssessor: " f"project_root={self.project_root}, " f"target_level={target_level.name}"
        )

    def assess_maturity(self) -> MaturityAssessment:
        """评估系统成熟度

        白皮书依据: 第十四章 14.1.3 CMM成熟度模型

        评估七个维度：
        1. 可靠性 (Reliability)
        2. 测试覆盖 (Test Coverage)
        3. 监控体系 (Monitoring)
        4. 安全合规 (Security & Compliance)
        5. 性能优化 (Performance)
        6. 文档完整 (Documentation)
        7. 运维标准 (Operations)

        Returns:
            成熟度评估结果
        """
        logger.info("开始评估CMM成熟度")

        # 评估各维度
        dimension_scores = {}

        dimension_scores["reliability"] = self._assess_reliability()
        dimension_scores["test_coverage"] = self._assess_test_coverage()
        dimension_scores["monitoring"] = self._assess_monitoring()
        dimension_scores["security"] = self._assess_security()
        dimension_scores["performance"] = self._assess_performance()
        dimension_scores["documentation"] = self._assess_documentation()
        dimension_scores["operations"] = self._assess_operations()

        # 计算总体评分
        overall_score = sum(d.score for d in dimension_scores.values()) / len(dimension_scores)

        # 确定总体级别
        overall_level = self._score_to_level(overall_score)

        # 生成改进建议
        recommendations = self._generate_recommendations(dimension_scores, overall_level)

        assessment = MaturityAssessment(
            overall_score=overall_score,
            overall_level=overall_level,
            dimension_scores=dimension_scores,
            recommendations=recommendations,
            target_level=self.target_level,
        )

        logger.info(f"CMM成熟度评估完成: " f"overall_score={overall_score:.2f}, " f"overall_level={overall_level.name}")

        return assessment

    def _assess_reliability(self) -> DimensionScore:
        """评估可靠性维度

        白皮书依据: 第十四章 14.3.1 七维度评估

        评估标准：
        - Redis高可用配置
        - 故障恢复机制
        - 热备切换能力
        - 系统监控告警
        """
        strengths = []
        gaps = []
        score = 0.0

        # 检查Redis配置
        redis_config = self.project_root / "config" / "redis.conf"
        if redis_config.exists():
            strengths.append("Redis配置文件存在")
            score += 0.5
        else:
            gaps.append("缺少Redis高可用配置")

        # 检查故障恢复机制
        health_checker = self.project_root / "src" / "core" / "health_checker.py"
        if health_checker.exists():
            strengths.append("健康检查机制已实现")
            score += 1.0
        else:
            gaps.append("缺少健康检查机制")

        # 检查热备切换
        soldier_failover = self.project_root / "src" / "brain" / "soldier_failover.py"
        if soldier_failover.exists():
            strengths.append("Soldier热备切换已实现")
            score += 1.0
        else:
            gaps.append("缺少Soldier热备切换机制")

        # 检查监控告警
        alert_manager = self.project_root / "src" / "monitoring" / "alert_manager.py"
        if alert_manager.exists():
            strengths.append("告警管理器已实现")
            score += 0.5
        else:
            gaps.append("缺少告警管理器")

        # 基础分
        score += 0.5

        level = self._score_to_level(score)

        return DimensionScore(dimension_name="可靠性", score=score, level=level, strengths=strengths, gaps=gaps)

    def _assess_test_coverage(self) -> DimensionScore:
        """评估测试覆盖维度

        白皮书依据: 第十四章 14.3.1 七维度评估

        评估标准：
        - 单元测试覆盖率
        - 集成测试覆盖率
        - 属性测试覆盖率
        - 测试自动化程度
        """
        strengths = []
        gaps = []
        score = 0.0

        # 检查测试目录结构
        tests_dir = self.project_root / "tests"
        if tests_dir.exists():
            strengths.append("测试目录结构完整")
            score += 0.5

            # 检查单元测试
            unit_tests = list(tests_dir.glob("unit/**/*.py"))
            if len(unit_tests) > 50:
                strengths.append(f"单元测试充足 ({len(unit_tests)}个)")
                score += 1.0
            elif len(unit_tests) > 20:
                strengths.append(f"单元测试基本覆盖 ({len(unit_tests)}个)")
                score += 0.5
            else:
                gaps.append(f"单元测试不足 ({len(unit_tests)}个)")

            # 检查集成测试
            integration_tests = list(tests_dir.glob("integration/**/*.py"))
            if len(integration_tests) > 10:
                strengths.append(f"集成测试完善 ({len(integration_tests)}个)")
                score += 0.5
            else:
                gaps.append(f"集成测试不足 ({len(integration_tests)}个)")

            # 检查属性测试
            property_tests = list(tests_dir.glob("properties/**/*.py"))
            if len(property_tests) > 5:
                strengths.append(f"属性测试完善 ({len(property_tests)}个)")
                score += 0.5
            else:
                gaps.append(f"属性测试不足 ({len(property_tests)}个)")
        else:
            gaps.append("缺少测试目录")

        # 检查CI配置
        ci_config = self.project_root / ".github" / "workflows" / "ci.yml"
        if ci_config.exists():
            strengths.append("CI/CD自动化已配置")
            score += 0.5
        else:
            gaps.append("缺少CI/CD自动化")

        level = self._score_to_level(score)

        return DimensionScore(dimension_name="测试覆盖", score=score, level=level, strengths=strengths, gaps=gaps)

    def _assess_monitoring(self) -> DimensionScore:
        """评估监控体系维度

        白皮书依据: 第十四章 14.3.1 七维度评估

        评估标准：
        - Prometheus指标收集
        - Grafana可视化
        - 告警规则配置
        - 日志聚合分析
        """
        strengths = []
        gaps = []
        score = 0.0

        # 检查Prometheus
        prometheus_collector = self.project_root / "src" / "monitoring" / "prometheus_collector.py"
        if prometheus_collector.exists():
            strengths.append("Prometheus指标收集已实现")
            score += 1.0
        else:
            gaps.append("缺少Prometheus指标收集")

        # 检查Grafana配置
        grafana_dashboard = self.project_root / "monitoring" / "grafana_dashboard.json"
        if grafana_dashboard.exists():
            strengths.append("Grafana仪表板已配置")
            score += 1.0
        else:
            gaps.append("缺少Grafana仪表板")

        # 检查告警规则
        alert_rules = self.project_root / "monitoring" / "alert_rules.yml"
        if alert_rules.exists():
            strengths.append("告警规则已配置")
            score += 0.5
        else:
            gaps.append("缺少告警规则配置")

        # 检查日志系统
        logs_dir = self.project_root / "logs"
        if logs_dir.exists():
            strengths.append("日志系统已部署")
            score += 0.5
        else:
            gaps.append("缺少日志系统")

        level = self._score_to_level(score)

        return DimensionScore(dimension_name="监控体系", score=score, level=level, strengths=strengths, gaps=gaps)

    def _assess_security(self) -> DimensionScore:
        """评估安全合规维度

        白皮书依据: 第十四章 14.3.1 七维度评估

        评估标准：
        - 安全网关配置
        - 数据加密存储
        - 访问控制机制
        - 安全审计日志
        """
        strengths = []
        gaps = []
        score = 0.0

        # 检查安全网关
        security_gateway = self.project_root / "src" / "security" / "unified_security_gateway.py"
        if security_gateway.exists():
            strengths.append("统一安全网关已实现")
            score += 1.5
        else:
            gaps.append("缺少统一安全网关")

        # 检查认证管理
        auth_manager = self.project_root / "src" / "security" / "auth_manager.py"
        if auth_manager.exists():
            strengths.append("认证管理器已实现")
            score += 0.5
        else:
            gaps.append("缺少认证管理器")

        # 检查审计日志
        audit_logger = self.project_root / "src" / "audit" / "audit_logger.py"
        if audit_logger.exists():
            strengths.append("审计日志已实现")
            score += 0.5
        else:
            gaps.append("缺少审计日志")

        # 检查配置加密
        secure_config = self.project_root / "src" / "security" / "secure_config.py"
        if secure_config.exists():
            strengths.append("配置加密已实现")
            score += 0.5
        else:
            gaps.append("缺少配置加密")

        level = self._score_to_level(score)

        return DimensionScore(dimension_name="安全合规", score=score, level=level, strengths=strengths, gaps=gaps)

    def _assess_performance(self) -> DimensionScore:
        """评估性能优化维度

        白皮书依据: 第十四章 14.3.1 七维度评估

        评估标准：
        - Soldier决策延迟
        - Redis吞吐量
        - GPU利用率
        - 性能基准测试
        """
        strengths = []
        gaps = []
        score = 1.0  # 基础分

        # 检查性能优化器
        performance_optimizer = self.project_root / "src" / "optimization" / "performance_optimizer.py"
        if performance_optimizer.exists():
            strengths.append("性能优化器已实现")
            score += 1.0
        else:
            gaps.append("缺少性能优化器")

        # 检查性能监控
        performance_monitor = self.project_root / "src" / "monitoring" / "performance_monitor.py"
        if performance_monitor.exists():
            strengths.append("性能监控已实现")
            score += 0.5
        else:
            gaps.append("缺少性能监控")

        # 检查性能测试
        perf_tests = (
            list((self.project_root / "tests").glob("performance/**/*.py"))
            if (self.project_root / "tests").exists()
            else []
        )
        if len(perf_tests) > 5:
            strengths.append(f"性能测试完善 ({len(perf_tests)}个)")
            score += 1.0
        elif len(perf_tests) > 0:
            strengths.append(f"性能测试基本覆盖 ({len(perf_tests)}个)")
            score += 0.5
        else:
            gaps.append("缺少性能测试")

        level = self._score_to_level(score)

        return DimensionScore(dimension_name="性能优化", score=score, level=level, strengths=strengths, gaps=gaps)

    def _assess_documentation(self) -> DimensionScore:
        """评估文档完整维度

        白皮书依据: 第十四章 14.3.1 七维度评估

        评估标准：
        - 白皮书完整性
        - API文档覆盖
        - 开发指南完善
        - 架构文档清晰
        """
        strengths = []
        gaps = []
        score = 0.0

        # 检查白皮书
        whitepaper = self.project_root / "00_核心文档" / "mia.md"
        if whitepaper.exists():
            strengths.append("白皮书完整")
            score += 1.5
        else:
            gaps.append("缺少白皮书")

        # 检查开发指南
        dev_guide = self.project_root / "00_核心文档" / "DEVELOPMENT_GUIDE.md"
        if dev_guide.exists():
            strengths.append("开发指南完善")
            score += 0.5
        else:
            gaps.append("缺少开发指南")

        # 检查API文档
        api_docs = self.project_root / "docs" / "api"
        if api_docs.exists():
            strengths.append("API文档存在")
            score += 0.5
        else:
            gaps.append("缺少API文档")

        # 检查README
        readme = self.project_root / "README.md"
        if readme.exists():
            strengths.append("README完整")
            score += 0.5
        else:
            gaps.append("缺少README")

        # 检查架构文档
        arch_docs = list(self.project_root.glob("ARCHITECTURE_*.md"))
        if len(arch_docs) > 0:
            strengths.append(f"架构文档完善 ({len(arch_docs)}个)")
            score += 1.0
        else:
            gaps.append("缺少架构文档")

        level = self._score_to_level(score)

        return DimensionScore(dimension_name="文档完整", score=score, level=level, strengths=strengths, gaps=gaps)

    def _assess_operations(self) -> DimensionScore:
        """评估运维标准维度

        白皮书依据: 第十四章 14.3.1 七维度评估

        评估标准：
        - 部署自动化
        - 配置管理
        - 备份恢复
        - 运维文档
        """
        strengths = []
        gaps = []
        score = 0.0

        # 检查Docker配置
        docker_compose = self.project_root / "docker" / "docker-compose.yml"
        if docker_compose.exists():
            strengths.append("Docker部署配置完整")
            score += 1.0
        else:
            gaps.append("缺少Docker部署配置")

        # 检查配置文件
        config_dir = self.project_root / "config"
        if config_dir.exists():
            config_files = list(config_dir.glob("*.yaml")) + list(config_dir.glob("*.yml"))
            if len(config_files) > 0:
                strengths.append(f"配置管理完善 ({len(config_files)}个)")
                score += 0.5
            else:
                gaps.append("配置文件不足")
        else:
            gaps.append("缺少配置目录")

        # 检查备份脚本
        backups_dir = self.project_root / "data" / "backups"
        if backups_dir.exists():
            strengths.append("备份目录已创建")
            score += 0.5
        else:
            gaps.append("缺少备份机制")

        # 检查运维文档
        ops_docs = list(self.project_root.glob("*RUNBOOK*.md")) + list(self.project_root.glob("*DEPLOYMENT*.md"))
        if len(ops_docs) > 0:
            strengths.append(f"运维文档完善 ({len(ops_docs)}个)")
            score += 1.0
        else:
            gaps.append("缺少运维文档")

        level = self._score_to_level(score)

        return DimensionScore(dimension_name="运维标准", score=score, level=level, strengths=strengths, gaps=gaps)

    def _score_to_level(self, score: float) -> CMMLevel:
        """将评分转换为CMM级别

        Args:
            score: 评分 (0-5)

        Returns:
            CMM级别
        """
        if score >= 4.5:  # pylint: disable=no-else-return
            return CMMLevel.OPTIMIZING
        elif score >= 3.5:
            return CMMLevel.MANAGED
        elif score >= 2.5:
            return CMMLevel.DEFINED
        elif score >= 1.5:
            return CMMLevel.REPEATABLE
        else:
            return CMMLevel.INITIAL

    def calculate_overall_score(self, dimension_scores: Dict[str, DimensionScore]) -> float:
        """计算总体评分

        白皮书依据: 第十四章 14.3.2 当前评分

        Args:
            dimension_scores: 各维度评分

        Returns:
            总体评分 (0-5)
        """
        if not dimension_scores:
            return 0.0

        total_score = sum(d.score for d in dimension_scores.values())
        overall_score = total_score / len(dimension_scores)

        return overall_score

    def identify_gaps(self, assessment: MaturityAssessment) -> List[str]:
        """识别差距

        白皮书依据: 第十四章 14.3.2 当前评分

        Args:
            assessment: 成熟度评估结果

        Returns:
            差距列表
        """
        all_gaps = []

        for dimension_name, dimension_score in assessment.dimension_scores.items():
            if dimension_score.level.value < self.target_level.value:
                all_gaps.extend([f"[{dimension_name}] {gap}" for gap in dimension_score.gaps])

        return all_gaps

    def _generate_recommendations(
        self, dimension_scores: Dict[str, DimensionScore], overall_level: CMMLevel
    ) -> List[str]:
        """生成改进建议

        Args:
            dimension_scores: 各维度评分
            overall_level: 总体级别

        Returns:
            改进建议列表
        """
        recommendations = []

        # 根据总体级别给出建议
        if overall_level.value < self.target_level.value:
            recommendations.append(f"当前级别为{overall_level.name}，" f"需要提升至{self.target_level.name}级别")

        # 针对每个维度给出具体建议
        for dimension_name, dimension_score in dimension_scores.items():
            if dimension_score.level.value < self.target_level.value:
                recommendations.append(
                    f"提升{dimension_name}维度：当前{dimension_score.level.name}级别，"
                    f"评分{dimension_score.score:.2f}"
                )

                # 添加具体的改进措施
                for gap in dimension_score.gaps[:3]:  # 只显示前3个
                    recommendations.append(f"  - {gap}")

        return recommendations
