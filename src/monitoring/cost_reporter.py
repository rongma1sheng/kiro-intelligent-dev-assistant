"""成本报表生成器

白皮书依据: 第八章 8.2.2 成本报表
"""

from datetime import datetime, timedelta
from typing import Dict

from loguru import logger


class CostReporter:
    """成本报表生成器

    白皮书依据: 第八章 8.2.2 成本报表

    生成日报、周报、月报。

    Attributes:
        redis: Redis客户端
    """

    def __init__(self, redis_client):
        """初始化成本报表生成器

        Args:
            redis_client: Redis客户端实例
        """
        self.redis = redis_client
        logger.info("成本报表生成器初始化完成")

    def generate_daily_report(self, date: datetime) -> Dict[str, any]:
        """生成日成本报表

        白皮书依据: 第八章 8.2.2 成本报表

        Args:
            date: 报表日期

        Returns:
            日报表字典
        """
        date_str = date.strftime("%Y%m%d")

        # 获取各模型成本
        models = ["deepseek-chat", "qwen-next-80b", "deepseek-r1", "qwen-scholar"]
        model_costs = {}

        for model in models:
            cost = float(self.redis.get(f"cost:model:{model}") or 0)
            model_costs[model] = cost

        # 总成本
        total_cost = float(self.redis.get(f"cost:daily:{date_str}") or 0)

        # 预算使用率
        daily_budget = 50.0
        budget_utilization = total_cost / daily_budget if daily_budget > 0 else 0

        report = {
            "date": date_str,
            "total_cost": total_cost,
            "model_costs": model_costs,
            "budget": daily_budget,
            "budget_utilization": budget_utilization,
            "exceeded": total_cost > daily_budget,
        }

        logger.info(f"[Cost] 日报表生成: {date_str}, 总成本=¥{total_cost:.2f}, " f"预算使用率={budget_utilization:.1%}")

        return report

    def generate_weekly_report(self, end_date: datetime) -> Dict[str, any]:
        """生成周成本报表

        Args:
            end_date: 报表结束日期

        Returns:
            周报表字典
        """
        # 获取最近7天的数据
        daily_reports = []
        total_cost = 0.0

        for i in range(7):
            date = end_date - timedelta(days=i)
            daily_report = self.generate_daily_report(date)
            daily_reports.append(daily_report)
            total_cost += daily_report["total_cost"]

        # 计算平均日成本
        avg_daily_cost = total_cost / 7

        # 周预算
        weekly_budget = 50.0 * 7
        budget_utilization = total_cost / weekly_budget if weekly_budget > 0 else 0

        report = {
            "end_date": end_date.strftime("%Y%m%d"),
            "total_cost": total_cost,
            "avg_daily_cost": avg_daily_cost,
            "budget": weekly_budget,
            "budget_utilization": budget_utilization,
            "exceeded": total_cost > weekly_budget,
            "daily_reports": daily_reports,
        }

        logger.info(f"[Cost] 周报表生成: 总成本=¥{total_cost:.2f}, " f"日均=¥{avg_daily_cost:.2f}")

        return report

    def generate_monthly_report(self, year: int, month: int) -> Dict[str, any]:
        """生成月成本报表

        Args:
            year: 年份
            month: 月份

        Returns:
            月报表字典

        Raises:
            ValueError: 当参数无效时
        """
        if month < 1 or month > 12:
            raise ValueError(f"月份必须在1-12之间，当前: {month}")

        # 获取该月所有天的数据
        daily_reports = []
        total_cost = 0.0

        # 计算该月天数
        if month == 12:
            next_month = datetime(year + 1, 1, 1)
        else:
            next_month = datetime(year, month + 1, 1)

        current_date = datetime(year, month, 1)

        while current_date < next_month:
            daily_report = self.generate_daily_report(current_date)
            daily_reports.append(daily_report)
            total_cost += daily_report["total_cost"]
            current_date += timedelta(days=1)

        # 计算平均日成本
        days_in_month = len(daily_reports)
        avg_daily_cost = total_cost / days_in_month if days_in_month > 0 else 0

        # 月预算
        monthly_budget = 1500.0
        budget_utilization = total_cost / monthly_budget if monthly_budget > 0 else 0

        # 按模型统计
        model_costs = {}
        models = ["deepseek-chat", "qwen-next-80b", "deepseek-r1", "qwen-scholar"]

        for model in models:
            cost = float(self.redis.get(f"cost:model:{model}") or 0)
            model_costs[model] = cost

        report = {
            "year": year,
            "month": month,
            "total_cost": total_cost,
            "avg_daily_cost": avg_daily_cost,
            "budget": monthly_budget,
            "budget_utilization": budget_utilization,
            "exceeded": total_cost > monthly_budget,
            "days_in_month": days_in_month,
            "model_costs": model_costs,
            "daily_reports": daily_reports,
        }

        logger.info(
            f"[Cost] 月报表生成: {year}-{month:02d}, 总成本=¥{total_cost:.2f}, "
            f"日均=¥{avg_daily_cost:.2f}, 预算使用率={budget_utilization:.1%}"
        )

        return report

    def generate_model_comparison_report(self) -> Dict[str, any]:
        """生成模型成本对比报表

        Returns:
            模型对比报表字典
        """
        models = ["deepseek-chat", "qwen-next-80b", "deepseek-r1", "qwen-scholar"]
        model_costs = {}
        total_cost = 0.0

        for model in models:
            cost = float(self.redis.get(f"cost:model:{model}") or 0)
            model_costs[model] = cost
            total_cost += cost

        # 计算占比
        model_percentages = {}
        for model, cost in model_costs.items():
            percentage = (cost / total_cost * 100) if total_cost > 0 else 0
            model_percentages[model] = percentage

        report = {
            "total_cost": total_cost,
            "model_costs": model_costs,
            "model_percentages": model_percentages,
            "most_expensive": max(model_costs, key=model_costs.get) if model_costs else None,
        }

        logger.info(f"[Cost] 模型对比报表生成: 总成本=¥{total_cost:.2f}")

        return report
