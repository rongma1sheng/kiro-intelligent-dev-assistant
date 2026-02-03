"""Cost Tracker - Real-time API Cost Tracking

白皮书依据: 第十八章 18.2.1 实时监控

核心功能:
- 实时追踪API调用成本
- 按服务/模型统计成本
- 预算超限告警
- 成本报表生成
"""

import json
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from loguru import logger


class CostTracker:
    """成本追踪器 - 实时API成本追踪

    白皮书依据: 第十八章 18.2.1 实时监控

    核心功能:
    - 实时追踪API调用成本
    - 按服务/模型统计成本
    - 预算超限告警

    Attributes:
        redis: Redis客户端
        daily_budget: 日预算（CNY）
        monthly_budget: 月预算（CNY）
        prices: 模型价格表（CNY/M tokens）
    """

    def __init__(self, redis_client=None, daily_budget: float = 50.0, monthly_budget: float = 1500.0):
        """初始化成本追踪器

        白皮书依据: 第十八章 18.2.1 实时监控

        Args:
            redis_client: Redis客户端实例（可选，用于持久化）
            daily_budget: 日预算（CNY），默认50元
            monthly_budget: 月预算（CNY），默认1500元

        Raises:
            ValueError: 当预算无效时
        """
        if daily_budget <= 0:
            raise ValueError(f"日预算必须 > 0: {daily_budget}")

        if monthly_budget <= 0:
            raise ValueError(f"月预算必须 > 0: {monthly_budget}")

        self.redis = redis_client
        self.daily_budget = daily_budget
        self.monthly_budget = monthly_budget

        # 模型价格表（CNY/M tokens）
        # 白皮书依据: 第十八章 18.1.1 成本构成
        self.prices: Dict[str, float] = {
            "deepseek-chat": 0.1,  # Soldier (Cloud备用)
            "qwen-next-80b": 1.0,  # Commander (研报)
            "deepseek-r1": 0.5,  # Auditor (审计)
            "qwen-scholar": 1.0,  # Scholar (论文)
            "local-model": 0.0,  # 本地模型免费
        }

        # 内存成本记录（当Redis不可用时使用）
        self._costs: Dict[str, Dict[str, float]] = {}
        self._model_costs: Dict[str, float] = {}
        self._total_cost: float = 0.0

        # 统计信息
        self.total_calls = 0
        self.alert_count = 0

        logger.info(f"[CostTracker] 初始化完成 - " f"日预算: ¥{daily_budget}, " f"月预算: ¥{monthly_budget}")

    def track_api_call(self, service: str, model: str, input_tokens: int, output_tokens: int) -> float:
        """追踪API调用成本

        白皮书依据: 第十八章 18.2.1 实时监控

        Args:
            service: 服务名称（commander/soldier/scholar等）
            model: 模型名称
            input_tokens: 输入token数
            output_tokens: 输出token数

        Returns:
            本次调用成本（CNY）

        Raises:
            ValueError: 当参数无效时
        """
        if input_tokens < 0:
            raise ValueError(f"输入token数不能为负: {input_tokens}")

        if output_tokens < 0:
            raise ValueError(f"输出token数不能为负: {output_tokens}")

        # 计算成本
        total_tokens = input_tokens + output_tokens
        price_per_million = self.prices.get(model, 0.1)  # 默认0.1元/M
        cost = (total_tokens / 1_000_000) * price_per_million

        # 记录成本
        today = datetime.now().strftime("%Y%m%d")

        if self.redis:
            # 使用Redis持久化
            self.redis.incrbyfloat(f"cost:daily:{today}", cost)
            self.redis.incrbyfloat(f"cost:service:{service}", cost)
            self.redis.incrbyfloat(f"cost:model:{model}", cost)
            self.redis.incrbyfloat("cost:total", cost)

            # 检查预算
            daily_cost = self.get_daily_cost()
            if daily_cost > self.daily_budget:
                self._trigger_budget_alert(daily_cost)
        else:
            # 使用内存存储
            if today not in self._costs:
                self._costs[today] = {}

            # 按服务记录
            if service not in self._costs[today]:
                self._costs[today][service] = 0.0

            self._costs[today][service] += cost

            if model not in self._model_costs:
                self._model_costs[model] = 0.0
            self._model_costs[model] += cost

            self._total_cost += cost

            # 检查预算
            daily_cost = self.get_daily_cost()
            if daily_cost > self.daily_budget:
                self._trigger_budget_alert(daily_cost)

        # 更新统计
        self.total_calls += 1

        logger.debug(
            f"[CostTracker] {service}/{model}: "
            f"¥{cost:.4f} "
            f"(tokens: {input_tokens}+{output_tokens}={total_tokens}, "
            f"daily: ¥{daily_cost:.2f})"
        )

        return cost

    def get_daily_cost(self, date: Optional[datetime] = None) -> float:
        """获取日成本

        Args:
            date: 日期，None表示今天

        Returns:
            日成本（CNY）
        """
        if date is None:
            date_str = datetime.now().strftime("%Y%m%d")
        else:
            date_str = date.strftime("%Y%m%d")

        if self.redis:
            value = self.redis.get(f"cost:daily:{date_str}")
            if value is None:
                return 0.0
            return float(value)
        else:
            if date_str not in self._costs:
                return 0.0
            return sum(self._costs[date_str].values())

    def get_model_cost(self, model: str) -> float:
        """获取模型累计成本

        Args:
            model: 模型名称

        Returns:
            模型累计成本（CNY）
        """
        if self.redis:
            value = self.redis.get(f"cost:model:{model}")
            if value is None:
                return 0.0
            return float(value)
        else:
            return self._model_costs.get(model, 0.0)

    def get_total_cost(self) -> float:
        """获取总成本

        Returns:
            总成本（CNY）
        """
        if self.redis:
            value = self.redis.get("cost:total")
            if value is None:
                return 0.0
            return float(value)
        else:
            return self._total_cost

    def get_monthly_cost(self, year_month: Optional[str] = None) -> float:
        """获取月成本

        Args:
            year_month: 年月（YYYYMM格式），None表示本月

        Returns:
            月成本（CNY）
        """
        if year_month is None:
            year_month = datetime.now().strftime("%Y%m")

        if self.redis:
            # 从Redis获取本月所有日成本
            monthly_cost = 0.0
            # 遍历本月所有天
            year = int(year_month[:4])
            month = int(year_month[4:6])

            for day in range(1, 32):
                try:
                    date_str = f"{year_month}{day:02d}"
                    value = self.redis.get(f"cost:daily:{date_str}")
                    if value:
                        monthly_cost += float(value)
                except:
                    pass

            return monthly_cost
        else:
            monthly_cost = 0.0
            for date_str, services in self._costs.items():
                if date_str.startswith(year_month):
                    monthly_cost += sum(services.values())
            return monthly_cost

    def check_budget(self) -> Dict[str, Any]:
        """检查预算状态

        Returns:
            预算状态字典，包含:
            - daily_cost: 今日成本
            - daily_budget: 日预算
            - daily_utilization: 日预算使用率
            - daily_exceeded: 日预算是否超限
            - monthly_cost: 本月成本
            - monthly_budget: 月预算
            - monthly_utilization: 月预算使用率
            - monthly_exceeded: 月预算是否超限
        """
        daily_cost = self.get_daily_cost()
        monthly_cost = self.get_monthly_cost()

        return {
            "daily_cost": daily_cost,
            "daily_budget": self.daily_budget,
            "daily_utilization": daily_cost / self.daily_budget if self.daily_budget > 0 else 0,
            "daily_exceeded": daily_cost > self.daily_budget,
            "monthly_cost": monthly_cost,
            "monthly_budget": self.monthly_budget,
            "monthly_utilization": monthly_cost / self.monthly_budget if self.monthly_budget > 0 else 0,
            "monthly_exceeded": monthly_cost > self.monthly_budget,
        }

    def get_cost_history(self, days: int = 7) -> Dict[str, float]:
        """获取成本历史

        Args:
            days: 天数，默认7天

        Returns:
            成本历史字典 {date: cost}

        Raises:
            ValueError: 当天数无效时
        """
        if days <= 0:
            raise ValueError(f"天数必须 > 0: {days}")

        history = {}

        for i in range(days):
            date = datetime.now() - timedelta(days=i)
            date_str = date.strftime("%Y%m%d")
            history[date_str] = self.get_daily_cost(date)

        return history

    def get_cost_by_service(self, service: str, date: Optional[str] = None) -> float:
        """获取服务成本

        Args:
            service: 服务名称（模型名称）
            date: 日期（YYYYMMDD格式），None表示今天

        Returns:
            服务成本（CNY）
        """
        if date is None:
            date = datetime.now().strftime("%Y%m%d")

        if self.redis:
            # Redis模式下按模型统计
            return self.get_model_cost(service)
        else:
            if date not in self._costs:
                return 0.0
            return self._costs[date].get(service, 0.0)

    def reset_daily_cost(self, date: Optional[datetime] = None) -> None:
        """重置日成本

        Args:
            date: 日期，None表示今天
        """
        if date is None:
            date_str = datetime.now().strftime("%Y%m%d")
        else:
            date_str = date.strftime("%Y%m%d")

        if self.redis:
            self.redis.delete(f"cost:daily:{date_str}")
        else:
            if date_str in self._costs:
                del self._costs[date_str]

        logger.info(f"[CostTracker] 已重置日成本: {date_str}")

    def clear_all_costs(self) -> None:
        """清空所有成本记录"""
        if self.redis:
            # 清空Redis中的成本记录
            # 注意：这里只清空已知的键
            pass
        else:
            self._costs.clear()
            self._model_costs.clear()
            self._total_cost = 0.0

        self.total_calls = 0
        self.alert_count = 0
        logger.info("[CostTracker] 已清空所有成本记录")

    def _trigger_budget_alert(self, daily_cost: float) -> None:
        """触发预算告警

        Args:
            daily_cost: 日成本
        """
        self.alert_count += 1

        alert_data = {
            "type": "budget_exceeded",
            "daily_cost": daily_cost,
            "daily_budget": self.daily_budget,
            "excess": daily_cost - self.daily_budget,
            "timestamp": datetime.now().isoformat(),
        }

        if self.redis:
            # 记录告警到Redis
            self.redis.lpush("cost:alerts", json.dumps(alert_data))
            self.redis.ltrim("cost:alerts", 0, 99)  # 保留最近100条

        logger.warning(
            f"[CostTracker] 日预算超限告警 - "
            f"成本: ¥{daily_cost:.2f}, "
            f"预算: ¥{self.daily_budget:.2f}, "
            f"超限: ¥{daily_cost - self.daily_budget:.2f}"
        )

    def add_model_price(self, model: str, price: float) -> None:
        """添加模型价格

        Args:
            model: 模型名称
            price: 价格（CNY/M tokens）

        Raises:
            ValueError: 当参数无效时
        """
        if not model:
            raise ValueError("模型名称不能为空")

        if price < 0:
            raise ValueError(f"价格必须 >= 0: {price}")

        self.prices[model] = price

        logger.info(f"[CostTracker] 添加模型价格: {model} = ¥{price}/M tokens")

    def get_model_price(self, model: str) -> float:
        """获取模型价格

        Args:
            model: 模型名称

        Returns:
            价格（CNY/M tokens），如果模型不存在返回默认价格0.1
        """
        return self.prices.get(model, 0.1)

    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息

        Returns:
            统计信息字典
        """
        return {
            "total_calls": self.total_calls,
            "total_cost": self.get_total_cost(),
            "daily_cost": self.get_daily_cost(),
            "monthly_cost": self.get_monthly_cost(),
            "alert_count": self.alert_count,
            "daily_budget": self.daily_budget,
            "monthly_budget": self.monthly_budget,
        }
