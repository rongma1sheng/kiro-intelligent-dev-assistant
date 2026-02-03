"""成本熔断器

白皮书依据: 第八章 8.4.1 熔断机制
"""

from datetime import datetime

from loguru import logger


class CostCircuitBreaker:
    """成本熔断器

    白皮书依据: 第八章 8.4.1 熔断机制

    当成本超过预算时触发熔断，降级到本地模式。

    Attributes:
        redis: Redis客户端
        daily_budget: 日预算
        monthly_budget: 月预算
    """

    def __init__(self, redis_client, daily_budget: float = 50.0, monthly_budget: float = 1500.0):
        """初始化成本熔断器

        Args:
            redis_client: Redis客户端实例
            daily_budget: 日预算，默认¥50
            monthly_budget: 月预算，默认¥1500

        Raises:
            ValueError: 当预算参数无效时
        """
        if daily_budget <= 0:
            raise ValueError(f"日预算必须 > 0，当前: {daily_budget}")

        if monthly_budget <= 0:
            raise ValueError(f"月预算必须 > 0，当前: {monthly_budget}")

        self.redis = redis_client
        self.daily_budget = daily_budget
        self.monthly_budget = monthly_budget

        logger.info(f"成本熔断器初始化: 日预算=¥{daily_budget}, 月预算=¥{monthly_budget}")

    def check_budget(self) -> bool:
        """检查预算是否充足

        白皮书依据: 第八章 8.4.1 熔断机制

        Returns:
            True表示预算充足，False表示超预算
        """
        today = datetime.now().strftime("%Y%m%d")
        daily_cost = float(self.redis.get(f"cost:daily:{today}") or 0)

        if daily_cost > self.daily_budget:
            logger.warning(f"[Cost] 日预算超限: ¥{daily_cost:.2f} > ¥{self.daily_budget}, " "触发熔断器")
            self.redis.set("cost:circuit_breaker", "open")
            return False

        return True

    def is_open(self) -> bool:
        """检查熔断器状态

        Returns:
            True表示熔断器打开（超预算），False表示熔断器关闭（正常）
        """
        status = self.redis.get("cost:circuit_breaker")
        return status == b"open" if isinstance(status, bytes) else status == "open"

    def close(self):
        """关闭熔断器（手动恢复）"""
        self.redis.delete("cost:circuit_breaker")
        logger.info("[Cost] 熔断器已关闭")

    def get_status(self) -> dict:
        """获取熔断器状态详情

        Returns:
            状态详情字典
        """
        today = datetime.now().strftime("%Y%m%d")
        daily_cost = float(self.redis.get(f"cost:daily:{today}") or 0)
        is_open = self.is_open()

        return {
            "is_open": is_open,
            "daily_cost": daily_cost,
            "daily_budget": self.daily_budget,
            "daily_remaining": max(0, self.daily_budget - daily_cost),
            "daily_utilization": daily_cost / self.daily_budget,
        }

    def force_open(self):
        """强制打开熔断器（用于测试）"""
        self.redis.set("cost:circuit_breaker", "open")
        logger.warning("[Cost] 熔断器已强制打开")
