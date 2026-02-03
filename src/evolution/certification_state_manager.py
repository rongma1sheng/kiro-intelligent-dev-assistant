"""认证状态管理器

白皮书依据: 第四章 4.3.2 认证状态管理

本模块实现认证状态管理器，负责跟踪策略的认证状态、记录状态变更历史、
执行月度复核和自动降级/撤销。
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

from loguru import logger

from .z2h_data_models import CertificationLevel, CertificationStatus, CertifiedStrategy


class StateChangeReason(Enum):
    """状态变更原因"""

    INITIAL_CERTIFICATION = "initial_certification"  # 初次认证
    MONTHLY_REVIEW_PASS = "monthly_review_pass"  # 月度复核通过
    MONTHLY_REVIEW_FAIL = "monthly_review_fail"  # 月度复核失败
    PERFORMANCE_DEGRADATION = "performance_degradation"  # 性能下降
    RISK_LIMIT_BREACH = "risk_limit_breach"  # 风险限制突破
    MANUAL_REVOCATION = "manual_revocation"  # 人工撤销
    MANUAL_DOWNGRADE = "manual_downgrade"  # 人工降级
    AUTO_DOWNGRADE = "auto_downgrade"  # 自动降级
    AUTO_REVOCATION = "auto_revocation"  # 自动撤销


@dataclass
class StateChangeRecord:
    """状态变更记录

    Attributes:
        strategy_id: 策略ID
        timestamp: 变更时间
        old_status: 旧状态
        new_status: 新状态
        old_level: 旧等级（可选）
        new_level: 新等级（可选）
        reason: 变更原因
        details: 详细信息
        operator: 操作者（人工操作时）
    """

    strategy_id: str
    timestamp: datetime
    old_status: CertificationStatus
    new_status: CertificationStatus
    old_level: Optional[CertificationLevel]
    new_level: Optional[CertificationLevel]
    reason: StateChangeReason
    details: str
    operator: Optional[str] = None


@dataclass
class ReviewResult:
    """复核结果

    Attributes:
        strategy_id: 策略ID
        review_date: 复核日期
        passed: 是否通过
        current_metrics: 当前指标
        threshold_violations: 阈值违规列表
        recommendation: 建议（MAINTAIN/DOWNGRADE/REVOKE）
        details: 详细说明
    """

    strategy_id: str
    review_date: datetime
    passed: bool
    current_metrics: Dict[str, float]
    threshold_violations: List[str]
    recommendation: str
    details: str


class CertificationStateManager:
    """认证状态管理器

    白皮书依据: 第四章 4.3.2 认证状态管理

    核心功能：
    - 跟踪策略认证状态
    - 记录状态变更历史
    - 执行月度复核
    - 自动降级/撤销触发

    Attributes:
        state_change_history: 状态变更历史记录
        review_history: 复核历史记录
        review_thresholds: 复核阈值配置
    """

    # 复核阈值配置（更严格的多维度标准）
    DEFAULT_REVIEW_THRESHOLDS = {
        # 收益指标
        "min_sharpe_ratio": {
            CertificationLevel.PLATINUM: 2.5,
            CertificationLevel.GOLD: 2.0,
            CertificationLevel.SILVER: 1.5,
        },
        "min_calmar_ratio": {
            CertificationLevel.PLATINUM: 2.0,
            CertificationLevel.GOLD: 1.5,
            CertificationLevel.SILVER: 1.0,
        },
        "min_information_ratio": {
            CertificationLevel.PLATINUM: 1.5,
            CertificationLevel.GOLD: 1.0,
            CertificationLevel.SILVER: 0.8,
        },
        "min_monthly_return": {
            CertificationLevel.PLATINUM: 0.05,  # 5%
            CertificationLevel.GOLD: 0.03,  # 3%
            CertificationLevel.SILVER: 0.02,  # 2%
        },
        # 风险指标
        "max_drawdown": {
            CertificationLevel.PLATINUM: 0.10,  # 10%
            CertificationLevel.GOLD: 0.12,  # 12%
            CertificationLevel.SILVER: 0.15,  # 15%
        },
        "max_var_95": {
            CertificationLevel.PLATINUM: 0.03,  # 3%
            CertificationLevel.GOLD: 0.04,  # 4%
            CertificationLevel.SILVER: 0.05,  # 5%
        },
        "max_volatility": {
            CertificationLevel.PLATINUM: 0.15,  # 15%
            CertificationLevel.GOLD: 0.20,  # 20%
            CertificationLevel.SILVER: 0.25,  # 25%
        },
        # 稳定性指标
        "min_win_rate": {
            CertificationLevel.PLATINUM: 0.65,  # 65%
            CertificationLevel.GOLD: 0.60,  # 60%
            CertificationLevel.SILVER: 0.55,  # 55%
        },
        "min_profit_factor": {
            CertificationLevel.PLATINUM: 2.0,
            CertificationLevel.GOLD: 1.5,
            CertificationLevel.SILVER: 1.3,
        },
        "max_consecutive_losses": {
            CertificationLevel.PLATINUM: 3,
            CertificationLevel.GOLD: 5,
            CertificationLevel.SILVER: 7,
        },
        # 市场适应性指标
        "min_market_correlation": {
            CertificationLevel.PLATINUM: 0.3,  # 与市场相关性不能太低
            CertificationLevel.GOLD: 0.2,
            CertificationLevel.SILVER: 0.1,
        },
        "max_market_correlation": {
            CertificationLevel.PLATINUM: 0.6,  # 与市场相关性不能太高
            CertificationLevel.GOLD: 0.7,
            CertificationLevel.SILVER: 0.8,
        },
        "min_alpha": {
            CertificationLevel.PLATINUM: 0.03,  # 月度超额收益
            CertificationLevel.GOLD: 0.02,
            CertificationLevel.SILVER: 0.01,
        },
        # 交易效率指标
        "max_turnover_rate": {
            CertificationLevel.PLATINUM: 3.0,  # 月换手率<300%
            CertificationLevel.GOLD: 4.0,  # <400%
            CertificationLevel.SILVER: 5.0,  # <500%
        },
        "min_avg_holding_days": {
            CertificationLevel.PLATINUM: 3,  # 平均持仓≥3天
            CertificationLevel.GOLD: 2,  # ≥2天
            CertificationLevel.SILVER: 1,  # ≥1天
        },
    }

    def __init__(self, review_thresholds: Optional[Dict[str, Dict[CertificationLevel, float]]] = None):
        """初始化认证状态管理器

        Args:
            review_thresholds: 自定义复核阈值（可选）
        """
        self.state_change_history: Dict[str, List[StateChangeRecord]] = {}
        self.review_history: Dict[str, List[ReviewResult]] = {}

        if review_thresholds:
            self.review_thresholds = review_thresholds
        else:
            self.review_thresholds = self.DEFAULT_REVIEW_THRESHOLDS.copy()

        logger.info("CertificationStateManager初始化完成")

    def record_state_change(  # pylint: disable=too-many-positional-arguments
        self,
        strategy_id: str,
        old_status: CertificationStatus,
        new_status: CertificationStatus,
        reason: StateChangeReason,
        details: str,
        old_level: Optional[CertificationLevel] = None,
        new_level: Optional[CertificationLevel] = None,
        operator: Optional[str] = None,
    ) -> StateChangeRecord:
        """记录状态变更

        白皮书依据: Requirement 7.7

        记录策略认证状态的变更，包括状态、等级、原因等信息。

        Args:
            strategy_id: 策略ID
            old_status: 旧状态
            new_status: 新状态
            reason: 变更原因
            details: 详细信息
            old_level: 旧等级（可选）
            new_level: 新等级（可选）
            operator: 操作者（可选）

        Returns:
            StateChangeRecord: 状态变更记录
        """
        record = StateChangeRecord(
            strategy_id=strategy_id,
            timestamp=datetime.now(),
            old_status=old_status,
            new_status=new_status,
            old_level=old_level,
            new_level=new_level,
            reason=reason,
            details=details,
            operator=operator,
        )

        # 保存到历史记录
        if strategy_id not in self.state_change_history:
            self.state_change_history[strategy_id] = []

        self.state_change_history[strategy_id].append(record)

        logger.info(
            f"记录状态变更 - 策略: {strategy_id}, "
            f"{old_status.value} -> {new_status.value}, "
            f"原因: {reason.value}"
        )

        return record

    def get_state_change_history(
        self, strategy_id: str, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None
    ) -> List[StateChangeRecord]:
        """获取状态变更历史

        Args:
            strategy_id: 策略ID
            start_date: 开始日期（可选）
            end_date: 结束日期（可选）

        Returns:
            List[StateChangeRecord]: 状态变更记录列表
        """
        if strategy_id not in self.state_change_history:
            return []

        records = self.state_change_history[strategy_id]

        # 按日期过滤
        if start_date or end_date:
            filtered_records = []
            for record in records:
                if start_date and record.timestamp < start_date:
                    continue
                if end_date and record.timestamp > end_date:
                    continue
                filtered_records.append(record)
            return filtered_records

        return records

    async def perform_monthly_review(  # pylint: disable=too-many-branches
        self, certified_strategy: CertifiedStrategy, current_metrics: Dict[str, float]
    ) -> ReviewResult:
        """执行月度复核

        白皮书依据: Requirement 7.5

        对已认证策略进行月度复核，检查当前表现是否符合认证等级要求。

        Args:
            certified_strategy: 已认证策略
            current_metrics: 当前性能指标

        Returns:
            ReviewResult: 复核结果
        """
        strategy_id = certified_strategy.strategy_id
        current_level = certified_strategy.certification_level

        logger.info(f"开始月度复核 - 策略: {certified_strategy.strategy_name}, " f"等级: {current_level.value}")

        # 检查各项指标（多维度严格检查）
        threshold_violations = []

        # === 收益指标 ===
        # 1. 夏普比率
        sharpe_ratio = current_metrics.get("sharpe_ratio", 0)
        min_sharpe = self.review_thresholds["min_sharpe_ratio"][current_level]
        if sharpe_ratio < min_sharpe:
            threshold_violations.append(f"夏普比率{sharpe_ratio:.2f} < {min_sharpe:.2f}")

        # 2. 卡玛比率
        calmar_ratio = current_metrics.get("calmar_ratio", 0)
        min_calmar = self.review_thresholds["min_calmar_ratio"][current_level]
        if calmar_ratio < min_calmar:
            threshold_violations.append(f"卡玛比率{calmar_ratio:.2f} < {min_calmar:.2f}")

        # 3. 信息比率
        information_ratio = current_metrics.get("information_ratio", 0)
        min_ir = self.review_thresholds["min_information_ratio"][current_level]
        if information_ratio < min_ir:
            threshold_violations.append(f"信息比率{information_ratio:.2f} < {min_ir:.2f}")

        # 4. 月收益
        monthly_return = current_metrics.get("monthly_return", 0)
        min_return = self.review_thresholds["min_monthly_return"][current_level]
        if monthly_return < min_return:
            threshold_violations.append(f"月收益{monthly_return:.2%} < {min_return:.2%}")

        # === 风险指标 ===
        # 5. 最大回撤
        max_drawdown = current_metrics.get("max_drawdown", 1.0)
        max_dd_threshold = self.review_thresholds["max_drawdown"][current_level]
        if max_drawdown > max_dd_threshold:
            threshold_violations.append(f"最大回撤{max_drawdown:.2%} > {max_dd_threshold:.2%}")

        # 6. VaR 95%
        var_95 = current_metrics.get("var_95", 1.0)
        max_var = self.review_thresholds["max_var_95"][current_level]
        if var_95 > max_var:
            threshold_violations.append(f"VaR95%{var_95:.2%} > {max_var:.2%}")

        # 7. 波动率
        volatility = current_metrics.get("volatility", 1.0)
        max_vol = self.review_thresholds["max_volatility"][current_level]
        if volatility > max_vol:
            threshold_violations.append(f"波动率{volatility:.2%} > {max_vol:.2%}")

        # === 稳定性指标 ===
        # 8. 胜率
        win_rate = current_metrics.get("win_rate", 0)
        min_win_rate = self.review_thresholds["min_win_rate"][current_level]
        if win_rate < min_win_rate:
            threshold_violations.append(f"胜率{win_rate:.2%} < {min_win_rate:.2%}")

        # 9. 盈利因子
        profit_factor = current_metrics.get("profit_factor", 0)
        min_pf = self.review_thresholds["min_profit_factor"][current_level]
        if profit_factor < min_pf:
            threshold_violations.append(f"盈利因子{profit_factor:.2f} < {min_pf:.2f}")

        # 10. 连续亏损次数
        consecutive_losses = current_metrics.get("consecutive_losses", 0)
        max_losses = self.review_thresholds["max_consecutive_losses"][current_level]
        if consecutive_losses > max_losses:
            threshold_violations.append(f"连续亏损{consecutive_losses}次 > {max_losses}次")

        # === 市场适应性指标 ===
        # 11. 市场相关性（不能太高也不能太低）
        market_corr = current_metrics.get("market_correlation", 0.5)
        min_corr = self.review_thresholds["min_market_correlation"][current_level]
        max_corr = self.review_thresholds["max_market_correlation"][current_level]
        if market_corr < min_corr:
            threshold_violations.append(f"市场相关性{market_corr:.2f} < {min_corr:.2f}（过低）")
        if market_corr > max_corr:
            threshold_violations.append(f"市场相关性{market_corr:.2f} > {max_corr:.2f}（过高）")

        # 12. Alpha（超额收益）
        alpha = current_metrics.get("alpha", 0)
        min_alpha = self.review_thresholds["min_alpha"][current_level]
        if alpha < min_alpha:
            threshold_violations.append(f"Alpha{alpha:.2%} < {min_alpha:.2%}")

        # === 交易效率指标 ===
        # 13. 换手率
        turnover_rate = current_metrics.get("turnover_rate", 0)
        max_turnover = self.review_thresholds["max_turnover_rate"][current_level]
        if turnover_rate > max_turnover:
            threshold_violations.append(f"换手率{turnover_rate:.1f} > {max_turnover:.1f}")

        # 14. 平均持仓天数
        avg_holding_days = current_metrics.get("avg_holding_days", 0)
        min_holding = self.review_thresholds["min_avg_holding_days"][current_level]
        if avg_holding_days < min_holding:
            threshold_violations.append(f"平均持仓{avg_holding_days:.1f}天 < {min_holding}天")

        # 判断是否通过（更严格的标准）
        # PLATINUM: 不允许任何违规
        # GOLD: 最多允许2项违规
        # SILVER: 最多允许3项违规
        if current_level == CertificationLevel.PLATINUM:
            passed = len(threshold_violations) == 0
        elif current_level == CertificationLevel.GOLD:
            passed = len(threshold_violations) <= 2
        else:  # SILVER
            passed = len(threshold_violations) <= 3

        # 确定建议（基于违规严重程度）
        if passed:
            recommendation = "MAINTAIN"
            details = f"符合{current_level.value}级要求，维持当前认证等级"
        elif len(threshold_violations) <= 4:
            recommendation = "DOWNGRADE"
            details = f"部分指标不达标（{len(threshold_violations)}项），建议降级"
        else:
            recommendation = "REVOKE"
            details = f"多项指标严重不达标（{len(threshold_violations)}项），建议撤销认证"

        result = ReviewResult(
            strategy_id=strategy_id,
            review_date=datetime.now(),
            passed=passed,
            current_metrics=current_metrics,
            threshold_violations=threshold_violations,
            recommendation=recommendation,
            details=details,
        )

        # 保存复核记录
        if strategy_id not in self.review_history:
            self.review_history[strategy_id] = []

        self.review_history[strategy_id].append(result)

        logger.info(
            f"月度复核完成 - 策略: {certified_strategy.strategy_name}, " f"通过: {passed}, 建议: {recommendation}"
        )

        return result

    async def auto_downgrade_if_needed(
        self, certified_strategy: CertifiedStrategy, review_result: ReviewResult
    ) -> Optional[CertificationLevel]:
        """自动降级（如需要）

        白皮书依据: Requirement 7.6

        根据复核结果自动降级策略的认证等级。

        Args:
            certified_strategy: 已认证策略
            review_result: 复核结果

        Returns:
            Optional[CertificationLevel]: 新的认证等级，如果未降级返回None
        """
        if review_result.recommendation != "DOWNGRADE":
            return None

        current_level = certified_strategy.certification_level

        # 确定新等级
        if current_level == CertificationLevel.PLATINUM:
            new_level = CertificationLevel.GOLD
        elif current_level == CertificationLevel.GOLD:
            new_level = CertificationLevel.SILVER
        else:
            # SILVER级别不能再降级，只能撤销
            logger.warning(f"策略{certified_strategy.strategy_name}已是SILVER级别，" f"无法降级，建议撤销")
            return None

        logger.warning(
            f"自动降级 - 策略: {certified_strategy.strategy_name}, " f"{current_level.value} -> {new_level.value}"
        )

        # 记录状态变更
        self.record_state_change(
            strategy_id=certified_strategy.strategy_id,
            old_status=certified_strategy.status,
            new_status=CertificationStatus.DOWNGRADED,
            old_level=current_level,
            new_level=new_level,
            reason=StateChangeReason.AUTO_DOWNGRADE,
            details=f"月度复核不达标，自动降级。违规项: {', '.join(review_result.threshold_violations)}",
        )

        # 更新策略状态
        certified_strategy.certification_level = new_level
        certified_strategy.gene_capsule.certification_level = new_level
        certified_strategy.status = CertificationStatus.DOWNGRADED
        certified_strategy.last_review_date = review_result.review_date
        certified_strategy.next_review_date = review_result.review_date + timedelta(days=30)

        return new_level

    async def auto_revoke_if_needed(self, certified_strategy: CertifiedStrategy, review_result: ReviewResult) -> bool:
        """自动撤销（如需要）

        白皮书依据: Requirement 7.6

        根据复核结果自动撤销策略的认证。

        Args:
            certified_strategy: 已认证策略
            review_result: 复核结果

        Returns:
            bool: 是否撤销了认证
        """
        if review_result.recommendation != "REVOKE":
            return False

        logger.warning(f"自动撤销认证 - 策略: {certified_strategy.strategy_name}, " f"原因: 多项指标严重不达标")

        # 记录状态变更
        self.record_state_change(
            strategy_id=certified_strategy.strategy_id,
            old_status=certified_strategy.status,
            new_status=CertificationStatus.REVOKED,
            old_level=certified_strategy.certification_level,
            new_level=None,
            reason=StateChangeReason.AUTO_REVOCATION,
            details=f"月度复核严重不达标，自动撤销认证。违规项: {', '.join(review_result.threshold_violations)}",
        )

        # 更新策略状态
        certified_strategy.status = CertificationStatus.REVOKED
        certified_strategy.last_review_date = review_result.review_date
        certified_strategy.next_review_date = None

        return True

    def get_review_history(self, strategy_id: str, limit: Optional[int] = None) -> List[ReviewResult]:
        """获取复核历史

        Args:
            strategy_id: 策略ID
            limit: 返回记录数量限制（可选）

        Returns:
            List[ReviewResult]: 复核结果列表
        """
        if strategy_id not in self.review_history:
            return []

        reviews = self.review_history[strategy_id]

        # 按时间倒序排列
        reviews_sorted = sorted(reviews, key=lambda r: r.review_date, reverse=True)

        if limit:
            return reviews_sorted[:limit]

        return reviews_sorted

    def get_strategies_due_for_review(
        self, certified_strategies: List[CertifiedStrategy], days_ahead: int = 7
    ) -> List[CertifiedStrategy]:
        """获取需要复核的策略列表

        Args:
            certified_strategies: 已认证策略列表
            days_ahead: 提前天数（默认7天）

        Returns:
            List[CertifiedStrategy]: 需要复核的策略列表
        """
        due_date = datetime.now() + timedelta(days=days_ahead)

        due_strategies = []
        for strategy in certified_strategies:
            # 只检查已认证状态的策略
            if strategy.status != CertificationStatus.CERTIFIED:
                continue

            # 检查是否到期
            if strategy.next_review_date and strategy.next_review_date <= due_date:
                due_strategies.append(strategy)

        logger.info(f"发现{len(due_strategies)}个策略需要在{days_ahead}天内复核")

        return due_strategies

    def generate_audit_report(
        self, strategy_id: str, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """生成审计报告

        白皮书依据: Requirement 8.7

        生成策略的完整审计报告，包括状态变更历史和复核历史。

        Args:
            strategy_id: 策略ID
            start_date: 开始日期（可选）
            end_date: 结束日期（可选）

        Returns:
            Dict[str, Any]: 审计报告
        """
        # 获取状态变更历史
        state_changes = self.get_state_change_history(strategy_id, start_date, end_date)

        # 获取复核历史
        reviews = self.get_review_history(strategy_id)

        # 过滤复核历史
        if start_date or end_date:
            filtered_reviews = []
            for review in reviews:
                if start_date and review.review_date < start_date:
                    continue
                if end_date and review.review_date > end_date:
                    continue
                filtered_reviews.append(review)
            reviews = filtered_reviews

        # 统计信息
        total_state_changes = len(state_changes)
        total_reviews = len(reviews)
        passed_reviews = sum(1 for r in reviews if r.passed)
        failed_reviews = total_reviews - passed_reviews

        # 状态变更统计
        reason_counts = {}
        for change in state_changes:
            reason = change.reason.value
            reason_counts[reason] = reason_counts.get(reason, 0) + 1

        report = {
            "strategy_id": strategy_id,
            "report_date": datetime.now().isoformat(),
            "period": {
                "start_date": start_date.isoformat() if start_date else None,
                "end_date": end_date.isoformat() if end_date else None,
            },
            "summary": {
                "total_state_changes": total_state_changes,
                "total_reviews": total_reviews,
                "passed_reviews": passed_reviews,
                "failed_reviews": failed_reviews,
                "review_pass_rate": passed_reviews / total_reviews if total_reviews > 0 else 0,
            },
            "state_change_breakdown": reason_counts,
            "state_changes": [
                {
                    "timestamp": change.timestamp.isoformat(),
                    "old_status": change.old_status.value,
                    "new_status": change.new_status.value,
                    "old_level": change.old_level.value if change.old_level else None,
                    "new_level": change.new_level.value if change.new_level else None,
                    "reason": change.reason.value,
                    "details": change.details,
                    "operator": change.operator,
                }
                for change in state_changes
            ],
            "reviews": [
                {
                    "review_date": review.review_date.isoformat(),
                    "passed": review.passed,
                    "current_metrics": review.current_metrics,
                    "threshold_violations": review.threshold_violations,
                    "recommendation": review.recommendation,
                    "details": review.details,
                }
                for review in reviews
            ],
        }

        logger.info(
            f"生成审计报告 - 策略: {strategy_id}, " f"状态变更: {total_state_changes}次, " f"复核: {total_reviews}次"
        )

        return report
