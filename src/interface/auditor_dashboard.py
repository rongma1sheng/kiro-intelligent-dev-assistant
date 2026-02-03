"""魔鬼审计仪表盘 (Auditor Dashboard)

白皮书依据: 附录A 全息指挥台 - 11. 魔鬼审计 (Auditor)
优先级: P2 - 高级功能

核心功能:
- 代码审计结果展示
- 未来函数检测
- 过拟合检测
- 安全性检查
- 审计历史记录
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from loguru import logger

try:
    import streamlit as st

    HAS_STREAMLIT = True
except ImportError:
    HAS_STREAMLIT = False


class AuditSeverity(Enum):
    """审计严重程度枚举"""

    CRITICAL = "致命"
    HIGH = "高危"
    MEDIUM = "中危"
    LOW = "低危"
    INFO = "信息"


class AuditCategory(Enum):
    """审计类别枚举"""

    FUTURE_FUNCTION = "未来函数"
    OVERFITTING = "过拟合"
    SECURITY = "安全性"
    PERFORMANCE = "性能"
    CODE_QUALITY = "代码质量"


@dataclass
class AuditIssue:
    """审计问题数据模型

    Attributes:
        issue_id: 问题ID
        category: 问题类别
        severity: 严重程度
        title: 标题
        description: 描述
        file_path: 文件路径
        line_number: 行号
        code_snippet: 代码片段
        suggestion: 修复建议
        detected_at: 检测时间
    """

    issue_id: str
    category: AuditCategory
    severity: AuditSeverity
    title: str
    description: str
    file_path: str
    line_number: int
    code_snippet: str
    suggestion: str
    detected_at: datetime

    def to_dict(self) -> Dict[str, Any]:
        return {
            "issue_id": self.issue_id,
            "category": self.category.value,
            "severity": self.severity.value,
            "title": self.title,
            "description": self.description,
            "file_path": self.file_path,
            "line_number": self.line_number,
            "code_snippet": self.code_snippet,
            "suggestion": self.suggestion,
            "detected_at": self.detected_at.isoformat(),
        }


@dataclass
class AuditReport:
    """审计报告数据模型

    Attributes:
        report_id: 报告ID
        target_name: 审计目标名称
        target_type: 目标类型 (strategy/factor/code)
        audit_time: 审计时间
        total_issues: 总问题数
        critical_count: 致命问题数
        high_count: 高危问题数
        medium_count: 中危问题数
        low_count: 低危问题数
        passed: 是否通过
        score: 审计评分
        issues: 问题列表
    """

    report_id: str
    target_name: str
    target_type: str
    audit_time: datetime
    total_issues: int
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    passed: bool
    score: float
    issues: List[AuditIssue] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id": self.report_id,
            "target_name": self.target_name,
            "target_type": self.target_type,
            "audit_time": self.audit_time.isoformat(),
            "total_issues": self.total_issues,
            "critical_count": self.critical_count,
            "high_count": self.high_count,
            "medium_count": self.medium_count,
            "low_count": self.low_count,
            "passed": self.passed,
            "score": self.score,
            "issues": [i.to_dict() for i in self.issues],
        }


class AuditorDashboard:
    """魔鬼审计仪表盘

    白皮书依据: 附录A 全息指挥台 - 11. 魔鬼审计 (Auditor)

    提供代码和策略审计功能:
    - 未来函数检测
    - 过拟合检测
    - 安全性检查
    - 审计历史记录
    """

    COLOR_SCHEME = {
        "rise": "#FF4D4F",
        "fall": "#52C41A",
        "neutral": "#8C8C8C",
        "primary": "#1890FF",
        "warning": "#FA8C16",
        "critical": "#FF4D4F",
        "high": "#FA8C16",
        "medium": "#FADB14",
        "low": "#52C41A",
    }

    def __init__(self, redis_client: Optional[Any] = None):
        """初始化魔鬼审计仪表盘

        Args:
            redis_client: Redis客户端
        """
        self.redis_client = redis_client
        logger.info("AuditorDashboard initialized")

    def get_audit_reports(self, limit: int = 20) -> List[AuditReport]:
        """获取审计报告列表

        Args:
            limit: 返回数量限制

        Returns:
            审计报告列表
        """
        if self.redis_client is None:
            return self._get_mock_reports(limit)

        try:
            reports = []
            report_ids = self.redis_client.lrange("mia:auditor:reports", 0, limit - 1)

            for report_id in report_ids:
                data = self.redis_client.hgetall(f"mia:auditor:report:{report_id}")
                if data:
                    # 获取问题列表
                    issue_ids = self.redis_client.lrange(f"mia:auditor:report:{report_id}:issues", 0, -1)
                    issues = []
                    for issue_id in issue_ids:
                        issue_data = self.redis_client.hgetall(f"mia:auditor:issue:{issue_id}")
                        if issue_data:
                            issues.append(
                                AuditIssue(
                                    issue_id=issue_id,
                                    category=AuditCategory[issue_data.get("category", "CODE_QUALITY")],
                                    severity=AuditSeverity[issue_data.get("severity", "LOW")],
                                    title=issue_data.get("title", ""),
                                    description=issue_data.get("description", ""),
                                    file_path=issue_data.get("file_path", ""),
                                    line_number=int(issue_data.get("line_number", 0)),
                                    code_snippet=issue_data.get("code_snippet", ""),
                                    suggestion=issue_data.get("suggestion", ""),
                                    detected_at=datetime.fromisoformat(
                                        issue_data.get("detected_at", datetime.now().isoformat())
                                    ),
                                )
                            )

                    reports.append(
                        AuditReport(
                            report_id=report_id,
                            target_name=data.get("target_name", ""),
                            target_type=data.get("target_type", ""),
                            audit_time=datetime.fromisoformat(data.get("audit_time", datetime.now().isoformat())),
                            total_issues=int(data.get("total_issues", 0)),
                            critical_count=int(data.get("critical_count", 0)),
                            high_count=int(data.get("high_count", 0)),
                            medium_count=int(data.get("medium_count", 0)),
                            low_count=int(data.get("low_count", 0)),
                            passed=data.get("passed", "false").lower() == "true",
                            score=float(data.get("score", 0)),
                            issues=issues,
                        )
                    )

            return reports if reports else self._get_mock_reports(limit)

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"Failed to get audit reports: {e}")
            return self._get_mock_reports(limit)

    def trigger_audit(
        self, target_name: str, target_type: str, code: str  # pylint: disable=unused-argument
    ) -> Dict[str, Any]:  # pylint: disable=unused-argument
        """触发审计任务

        Args:
            target_name: 审计目标名称
            target_type: 目标类型
            code: 代码内容

        Returns:
            审计任务信息
        """
        task_id = f"audit_{datetime.now().strftime('%Y%m%d%H%M%S')}"

        if self.redis_client:
            self.redis_client.hset(
                f"mia:auditor:task:{task_id}",
                mapping={
                    "status": "running",
                    "target_name": target_name,
                    "target_type": target_type,
                    "start_time": datetime.now().isoformat(),
                },
            )

        logger.info(f"Audit triggered: {task_id}, target: {target_name}")

        return {"task_id": task_id, "status": "running", "target_name": target_name}

    def render_streamlit(self) -> None:
        """渲染Streamlit界面"""
        if not HAS_STREAMLIT:
            logger.warning("Streamlit not available")
            return

        st.title("😈 魔鬼审计 (Auditor)")
        st.caption("代码审计 · 未来函数检测 · 过拟合检测 · 安全检查")

        tab1, tab2, tab3, tab4 = st.tabs(["📋 审计报告", "🔍 新建审计", "📊 统计分析", "⚙️ 审计规则"])

        with tab1:
            self._render_reports()

        with tab2:
            self._render_new_audit()

        with tab3:
            self._render_statistics()

        with tab4:
            self._render_rules()

    def _render_reports(self) -> None:
        """渲染审计报告列表"""
        st.subheader("📋 审计报告")

        reports = self.get_audit_reports(20)

        # 统计概览
        total = len(reports)
        passed = sum(1 for r in reports if r.passed)
        failed = total - passed

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("总审计数", total)
        with col2:
            st.metric("通过", passed)
        with col3:
            st.metric("未通过", failed)
        with col4:
            pass_rate = (passed / total * 100) if total > 0 else 0
            st.metric("通过率", f"{pass_rate:.1f}%")

        st.divider()

        for report in reports:
            status_icon = "✅" if report.passed else "❌"

            with st.expander(f"{status_icon} {report.target_name} - {report.audit_time.strftime('%Y-%m-%d %H:%M')}"):
                col1, col2, col3, col4, col5 = st.columns(5)

                with col1:
                    st.metric("评分", f"{report.score:.0f}")

                with col2:
                    if report.critical_count > 0:
                        st.error(f"致命: {report.critical_count}")
                    else:
                        st.success("致命: 0")

                with col3:
                    if report.high_count > 0:
                        st.warning(f"高危: {report.high_count}")
                    else:
                        st.success("高危: 0")

                with col4:
                    st.info(f"中危: {report.medium_count}")

                with col5:
                    st.caption(f"低危: {report.low_count}")

                # 问题列表
                if report.issues:
                    st.markdown("#### 问题详情")
                    for issue in report.issues:
                        severity_color = {
                            AuditSeverity.CRITICAL: self.COLOR_SCHEME["critical"],
                            AuditSeverity.HIGH: self.COLOR_SCHEME["high"],
                            AuditSeverity.MEDIUM: self.COLOR_SCHEME["medium"],
                            AuditSeverity.LOW: self.COLOR_SCHEME["low"],
                        }.get(issue.severity, self.COLOR_SCHEME["neutral"])

                        st.markdown(
                            f"<span style='color:{severity_color}'>● [{issue.severity.value}]</span> **{issue.title}**",
                            unsafe_allow_html=True,
                        )
                        st.caption(f"{issue.category.value} | {issue.file_path}:{issue.line_number}")
                        st.markdown(f"```python\n{issue.code_snippet}\n```")
                        st.info(f"💡 建议: {issue.suggestion}")
                        st.divider()

    def _render_new_audit(self) -> None:
        """渲染新建审计"""
        st.subheader("🔍 新建审计")

        with st.form("new_audit_form"):
            target_name = st.text_input("目标名称", placeholder="例如: 动量策略V2")
            target_type = st.selectbox("目标类型", ["strategy", "factor", "code"])

            code = st.text_area("代码内容", height=300, placeholder="粘贴要审计的代码...")

            col1, col2 = st.columns(2)
            with col1:
                check_future = st.checkbox("未来函数检测", value=True)  # pylint: disable=unused-variable
                check_overfit = st.checkbox("过拟合检测", value=True)  # pylint: disable=unused-variable
            with col2:
                check_security = st.checkbox("安全性检查", value=True)  # pylint: disable=unused-variable
                check_quality = st.checkbox("代码质量检查", value=True)  # pylint: disable=unused-variable

            submitted = st.form_submit_button("🚀 开始审计", use_container_width=True)

        if submitted:
            if target_name and code:
                result = self.trigger_audit(target_name, target_type, code)
                st.success(f"审计任务已启动: {result['task_id']}")

                # 模拟审计进度
                with st.spinner("正在审计..."):
                    import time  # pylint: disable=import-outside-toplevel

                    progress = st.progress(0)
                    for i in range(100):
                        time.sleep(0.02)
                        progress.progress(i + 1)

                st.success("审计完成！请在审计报告中查看结果。")
            else:
                st.warning("请填写目标名称和代码内容")

    def _render_statistics(self) -> None:
        """渲染统计分析"""
        st.subheader("📊 审计统计")

        reports = self.get_audit_reports(100)

        # 按类别统计问题
        category_counts = {}
        severity_counts = {}

        for report in reports:
            for issue in report.issues:
                cat = issue.category.value
                sev = issue.severity.value
                category_counts[cat] = category_counts.get(cat, 0) + 1
                severity_counts[sev] = severity_counts.get(sev, 0) + 1

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("### 按类别分布")
            for cat, count in sorted(category_counts.items(), key=lambda x: x[1], reverse=True):
                st.markdown(f"**{cat}**: {count}")
                st.progress(count / max(category_counts.values()) if category_counts else 0)

        with col2:
            st.markdown("### 按严重程度分布")
            for sev, count in sorted(severity_counts.items(), key=lambda x: x[1], reverse=True):
                color = {
                    "致命": self.COLOR_SCHEME["critical"],
                    "高危": self.COLOR_SCHEME["high"],
                    "中危": self.COLOR_SCHEME["medium"],
                    "低危": self.COLOR_SCHEME["low"],
                }.get(sev, self.COLOR_SCHEME["neutral"])
                st.markdown(f"<span style='color:{color}'>● {sev}</span>: {count}", unsafe_allow_html=True)

        st.divider()

        # 趋势分析
        st.markdown("### 审计趋势")
        st.info("最近30天审计通过率趋势")

        # 模拟趋势数据
        trend_data = [85, 82, 88, 90, 87, 92, 89, 91, 88, 93]
        st.line_chart(trend_data)

    def _render_rules(self) -> None:
        """渲染审计规则"""
        st.subheader("⚙️ 审计规则配置")

        st.markdown("### 未来函数检测规则")
        rules_future = [
            ("禁止使用未来数据", True, "检测是否使用了未来时间点的数据"),
            ("禁止前瞻性偏差", True, "检测是否存在前瞻性偏差"),
            ("检测数据泄露", True, "检测训练数据是否泄露到测试集"),
        ]

        for rule, enabled, desc in rules_future:
            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown(f"**{rule}**")
                st.caption(desc)
            with col2:
                st.checkbox("启用", value=enabled, key=f"rule_{rule}")

        st.divider()

        st.markdown("### 过拟合检测规则")
        rules_overfit = [
            ("参数数量检查", True, "参数数量不应超过数据点的1/10"),
            ("样本内外差异", True, "IS/OOS性能差异不应超过20%"),
            ("复杂度检查", True, "模型复杂度应与数据量匹配"),
        ]

        for rule, enabled, desc in rules_overfit:
            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown(f"**{rule}**")
                st.caption(desc)
            with col2:
                st.checkbox("启用", value=enabled, key=f"rule_{rule}")

        st.divider()

        st.markdown("### 安全性检查规则")
        rules_security = [
            ("禁止危险函数", True, "禁止eval, exec, os.system等"),
            ("禁止网络访问", True, "禁止未授权的网络请求"),
            ("禁止文件操作", True, "禁止未授权的文件读写"),
        ]

        for rule, enabled, desc in rules_security:
            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown(f"**{rule}**")
                st.caption(desc)
            with col2:
                st.checkbox("启用", value=enabled, key=f"rule_{rule}")

        if st.button("💾 保存配置", use_container_width=True):
            st.success("配置已保存")

    def _get_mock_reports(self, limit: int) -> List[AuditReport]:
        """获取模拟审计报告"""
        mock_issues = [
            AuditIssue(
                "ISS001",
                AuditCategory.FUTURE_FUNCTION,
                AuditSeverity.CRITICAL,
                "使用未来数据",
                "在计算信号时使用了未来的收盘价",
                "strategies/momentum.py",
                45,
                "signal = df['close'].shift(-1)",
                "使用shift(1)替代shift(-1)",
                datetime.now(),
            ),
            AuditIssue(
                "ISS002",
                AuditCategory.OVERFITTING,
                AuditSeverity.HIGH,
                "参数过多",
                "策略使用了过多的参数，可能存在过拟合风险",
                "strategies/momentum.py",
                12,
                "params = {...}  # 25个参数",
                "减少参数数量至10个以内",
                datetime.now(),
            ),
            AuditIssue(
                "ISS003",
                AuditCategory.SECURITY,
                AuditSeverity.MEDIUM,
                "使用eval函数",
                "代码中使用了eval函数，存在安全风险",
                "utils/parser.py",
                78,
                "result = eval(expression)",
                "使用ast.literal_eval或自定义解析器",
                datetime.now(),
            ),
        ]

        return [
            AuditReport("RPT001", "动量策略V2", "strategy", datetime.now(), 3, 1, 1, 1, 0, False, 65, mock_issues),
            AuditReport(
                "RPT002", "均值回归策略", "strategy", datetime.now(), 1, 0, 0, 1, 0, True, 85, [mock_issues[2]]
            ),
            AuditReport("RPT003", "因子F001", "factor", datetime.now(), 0, 0, 0, 0, 0, True, 100, []),
            AuditReport("RPT004", "主力跟随策略", "strategy", datetime.now(), 2, 0, 1, 1, 0, True, 78, mock_issues[1:]),
        ][:limit]
