"""Circuit Breaker for Costs - Cost Limit Enforcement

白皮书依据: 第十八章 18.4 熔断与降级

核心功能:
- 成本限制检查（单次/日/月）
- 熔断器状态管理
- 非关键调用暂停
"""

from datetime import datetime
from typing import Any, Dict, Optional

from loguru import logger


class CircuitBreakerForCosts:
    """成本熔断器 - 成本限制强制执行

    白皮书依据: 第十八章 18.4 熔断与降级

    核心功能:
    - 成本限制检查（单次/日/月）
    - 熔断器状态管理
    - 非关键调用暂停

    Attributes:
        cost_tracker: 成本追踪器
        per_request_limit: 单次请求成本限制（CNY）
        daily_limit: 日成本限制（CNY）
        monthly_limit: 月成本限制（CNY）
        is_open: 熔断器是否打开
    """

    def __init__(
        self, cost_tracker, per_request_limit: float = 0.10, daily_limit: float = 50.0, monthly_limit: float = 1500.0
    ):
        """初始化成本熔断器

        Args:
            cost_tracker: CostTracker实例
            per_request_limit: 单次请求成本限制（CNY），默认0.10元
            daily_limit: 日成本限制（CNY），默认50元
            monthly_limit: 月成本限制（CNY），默认1500元

        Raises:
            ValueError: 当参数无效时
        """
        if cost_tracker is None:
            raise ValueError("cost_tracker不能为None")

        if per_request_limit <= 0:
            raise ValueError(f"单次请求成本限制必须 > 0: {per_request_limit}")

        if daily_limit <= 0:
            raise ValueError(f"日成本限制必须 > 0: {daily_limit}")

        if monthly_limit <= 0:
            raise ValueError(f"月成本限制必须 > 0: {monthly_limit}")

        self.cost_tracker = cost_tracker
        self.per_request_limit = per_request_limit
        self.daily_limit = daily_limit
        self.monthly_limit = monthly_limit

        # 熔断器状态
        self.is_open = False
        self.open_reason = None
        self.open_timestamp = None

        # 统计信息
        self.total_checks = 0
        self.blocked_requests = 0
        self.open_count = 0

        logger.info(
            f"[CircuitBreakerForCosts] 初始化完成 - "
            f"单次限制: ¥{per_request_limit}, "
            f"日限制: ¥{daily_limit}, "
            f"月限制: ¥{monthly_limit}"
        )

    def check_cost_limit(self, estimated_cost: Optional[float] = None, is_critical: bool = True) -> bool:
        """检查成本限制

        白皮书依据: 第十八章 18.4.1 熔断机制

        Args:
            estimated_cost: 预估成本（CNY），None表示不检查单次成本
            is_critical: 是否关键调用，非关键调用在熔断时会被阻止

        Returns:
            是否允许调用（True=允许，False=阻止）
        """
        self.total_checks += 1

        # 检查熔断器状态
        if self.is_open and not is_critical:
            self.blocked_requests += 1
            logger.warning(f"[CircuitBreakerForCosts] 熔断器打开，阻止非关键调用 " f"(原因: {self.open_reason})")
            return False

        # 检查单次请求成本
        if estimated_cost is not None:
            if estimated_cost > self.per_request_limit:
                self.blocked_requests += 1
                logger.warning(
                    f"[CircuitBreakerForCosts] 单次请求成本超限 - "
                    f"预估: ¥{estimated_cost:.4f}, "
                    f"限制: ¥{self.per_request_limit:.4f}"
                )
                return False

        # 检查日成本
        daily_cost = self.cost_tracker.get_daily_cost()

        if daily_cost >= self.daily_limit:
            self._open_circuit("daily_limit_exceeded", daily_cost)

            if not is_critical:
                self.blocked_requests += 1
                return False

        # 检查月成本
        monthly_cost = self.cost_tracker.get_monthly_cost()

        if monthly_cost >= self.monthly_limit:
            self._open_circuit("monthly_limit_exceeded", monthly_cost)

            if not is_critical:
                self.blocked_requests += 1
                return False

        return True

    def pause_non_critical_calls(self) -> None:
        """暂停非关键调用

        白皮书依据: 第十八章 18.4.1 熔断机制

        手动打开熔断器，暂停所有非关键调用
        """
        if not self.is_open:
            self._open_circuit("manual_pause", None)
            logger.info("[CircuitBreakerForCosts] 手动暂停非关键调用")

    def resume_calls(self) -> None:
        """恢复调用

        手动关闭熔断器，恢复所有调用
        """
        if self.is_open:
            self._close_circuit()
            logger.info("[CircuitBreakerForCosts] 恢复所有调用")

    def get_status(self) -> Dict[str, Any]:
        """获取熔断器状态

        Returns:
            状态字典，包含:
            - is_open: 是否打开
            - open_reason: 打开原因
            - open_timestamp: 打开时间
            - per_request_limit: 单次请求限制
            - daily_limit: 日限制
            - monthly_limit: 月限制
            - current_daily_cost: 当前日成本
            - current_monthly_cost: 当前月成本
        """
        return {
            "is_open": self.is_open,
            "open_reason": self.open_reason,
            "open_timestamp": self.open_timestamp,
            "per_request_limit": self.per_request_limit,
            "daily_limit": self.daily_limit,
            "monthly_limit": self.monthly_limit,
            "current_daily_cost": self.cost_tracker.get_daily_cost(),
            "current_monthly_cost": self.cost_tracker.get_monthly_cost(),
        }

    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息

        Returns:
            统计信息字典
        """
        return {
            "total_checks": self.total_checks,
            "blocked_requests": self.blocked_requests,
            "open_count": self.open_count,
            "is_open": self.is_open,
            "block_rate": self.blocked_requests / self.total_checks if self.total_checks > 0 else 0.0,
        }

    def reset_statistics(self) -> None:
        """重置统计信息"""
        self.total_checks = 0
        self.blocked_requests = 0
        self.open_count = 0
        logger.info("[CircuitBreakerForCosts] 统计信息已重置")

    def _open_circuit(self, reason: str, cost: Optional[float]) -> None:
        """打开熔断器

        Args:
            reason: 打开原因
            cost: 相关成本
        """
        if not self.is_open:
            self.is_open = True
            self.open_reason = reason
            self.open_timestamp = datetime.now().isoformat()
            self.open_count += 1

            cost_str = f"¥{cost:.2f}" if cost is not None else "N/A"

            logger.warning(f"[CircuitBreakerForCosts] 熔断器打开 - " f"原因: {reason}, " f"成本: {cost_str}")

    def _close_circuit(self) -> None:
        """关闭熔断器"""
        self.is_open = False
        self.open_reason = None
        self.open_timestamp = None

        logger.info("[CircuitBreakerForCosts] 熔断器关闭")

    def auto_reset_if_possible(self) -> bool:
        """自动重置熔断器（如果条件允许）

        检查当前成本是否低于限制，如果是则自动关闭熔断器

        Returns:
            是否成功重置
        """
        if not self.is_open:
            return False

        daily_cost = self.cost_tracker.get_daily_cost()
        monthly_cost = self.cost_tracker.get_monthly_cost()

        # 检查是否可以重置
        can_reset = (
            daily_cost < self.daily_limit * 0.9  # 日成本低于90%限制
            and monthly_cost < self.monthly_limit * 0.9  # 月成本低于90%限制
        )

        if can_reset:
            self._close_circuit()
            logger.info(
                f"[CircuitBreakerForCosts] 自动重置熔断器 - "
                f"日成本: ¥{daily_cost:.2f}, "
                f"月成本: ¥{monthly_cost:.2f}"
            )
            return True

        return False
