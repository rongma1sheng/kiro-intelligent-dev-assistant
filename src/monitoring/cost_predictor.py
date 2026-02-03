"""Cost Predictor - Monthly Cost Prediction

白皮书依据: 第十八章 18.1.2 成本预测

核心功能:
- 预测月度成本
- 预算超限预警
- 成本趋势分析
"""

import math
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from loguru import logger


class CostPredictor:
    """成本预测器 - 月度成本预测

    白皮书依据: 第十八章 18.1.2 成本预测

    核心功能:
    - 预测月度成本
    - 预算超限预警
    - 成本趋势分析

    Attributes:
        redis: Redis客户端
        prediction_window: 预测使用的历史天数
        monthly_budget: 月预算
    """

    def __init__(self, redis_client=None, prediction_window: int = 7, monthly_budget: float = 1500.0):
        """初始化成本预测器

        Args:
            redis_client: Redis客户端实例
            prediction_window: 预测使用的历史天数，默认7天
            monthly_budget: 月预算，默认1500元

        Raises:
            ValueError: 当参数无效时
        """
        if prediction_window <= 0:
            raise ValueError(f"预测窗口必须 > 0: {prediction_window}")

        self.redis = redis_client
        self.prediction_window = prediction_window
        self.monthly_budget = monthly_budget

        logger.info(f"[CostPredictor] 初始化完成 - " f"预测天数: {prediction_window}")

    def predict_monthly_cost(self) -> Dict[str, Any]:
        """预测月度成本

        白皮书依据: 第十八章 18.1.2 成本预测

        基于最近N天的平均日成本预测本月总成本

        Returns:
            预测结果字典，包含:
            - avg_daily_cost: 平均日成本
            - predicted_monthly: 预测月成本
            - budget_monthly: 月预算
            - budget_utilization: 预算使用率
            - sample_size: 样本数量
            - confidence: 置信度
        """
        # 获取最近N天的日成本
        daily_costs = self._get_recent_daily_costs(self.prediction_window)

        # 计算平均日成本
        if not daily_costs:
            avg_daily_cost = 0.0
            confidence = 0.0
        else:
            avg_daily_cost = sum(daily_costs) / len(daily_costs)
            confidence = self._calculate_confidence(daily_costs)

        # 预测月成本（假设30天）
        predicted_monthly = avg_daily_cost * 30

        # 预算使用率
        budget_utilization = predicted_monthly / self.monthly_budget if self.monthly_budget > 0 else 0

        result = {
            "avg_daily_cost": avg_daily_cost,
            "predicted_monthly": predicted_monthly,
            "budget_monthly": self.monthly_budget,
            "budget_utilization": budget_utilization,
            "sample_size": len(daily_costs),
            "confidence": confidence,
            "is_over_budget": predicted_monthly > self.monthly_budget,
        }

        logger.info(
            f"[CostPredictor] 月度成本预测 - "
            f"平均日成本: ¥{avg_daily_cost:.2f}, "
            f"预测月成本: ¥{predicted_monthly:.2f}, "
            f"预算使用率: {budget_utilization:.1%}"
        )

        return result

    def predict_daily_cost(self, days_ahead: int = 1) -> Dict[str, Any]:
        """预测未来日成本

        Args:
            days_ahead: 预测未来天数，默认1天

        Returns:
            预测结果字典

        Raises:
            ValueError: 当天数无效时
        """
        if days_ahead <= 0:
            raise ValueError(f"预测天数必须 > 0: {days_ahead}")

        # 获取最近N天的日成本
        daily_costs = self._get_recent_daily_costs(self.prediction_window)

        if not daily_costs:
            return {"predicted_cost": 0.0, "days_ahead": days_ahead, "confidence": 0.0, "sample_size": 0}

        # 计算平均日成本
        avg_daily_cost = sum(daily_costs) / len(daily_costs)
        confidence = self._calculate_confidence(daily_costs)

        return {
            "predicted_cost": avg_daily_cost * days_ahead,
            "days_ahead": days_ahead,
            "confidence": confidence,
            "sample_size": len(daily_costs),
            "avg_daily_cost": avg_daily_cost,
        }

    def predict_model_cost(self, model: str, days: int = 30) -> Dict[str, Any]:
        """预测模型成本

        Args:
            model: 模型名称
            days: 预测天数，默认30天

        Returns:
            模型成本预测字典

        Raises:
            ValueError: 当参数无效时
        """
        if days <= 0:
            raise ValueError(f"预测天数必须 > 0: {days}")

        # 获取模型累计成本
        if self.redis:
            value = self.redis.get(f"cost:model:{model}")
            total_cost = float(value) if value else 0.0
        else:
            total_cost = 0.0

        # 计算平均日成本（假设数据覆盖prediction_window天）
        avg_daily_cost = total_cost / days if days > 0 else 0.0

        return {
            "model": model,
            "days": days,
            "total_cost": total_cost,
            "avg_daily_cost": avg_daily_cost,
            "predicted_cost": avg_daily_cost * days,
        }

    def _get_recent_daily_costs(self, days: int) -> List[float]:
        """获取最近N天的日成本

        Args:
            days: 天数

        Returns:
            日成本列表（只包含有数据的天）
        """
        daily_costs = []

        for i in range(days):
            date = datetime.now() - timedelta(days=i)
            date_str = date.strftime("%Y%m%d")

            if self.redis:
                value = self.redis.get(f"cost:daily:{date_str}")
                if value is not None:
                    daily_costs.append(float(value))
            else:
                # 无Redis时返回空列表
                pass

        return daily_costs

    def _calculate_confidence(self, daily_costs: List[float]) -> float:
        """计算预测置信度

        基于数据的变异系数计算置信度。
        变异系数越小，数据越稳定，置信度越高。

        Args:
            daily_costs: 日成本列表

        Returns:
            置信度（0-1之间）
        """
        if len(daily_costs) <= 1:
            return 0.5  # 数据不足，返回默认置信度

        mean = sum(daily_costs) / len(daily_costs)

        if mean == 0:
            return 0.5  # 零均值，返回默认置信度

        # 计算标准差
        variance = sum((x - mean) ** 2 for x in daily_costs) / len(daily_costs)
        std_dev = math.sqrt(variance)

        # 计算变异系数 (CV)
        cv = std_dev / mean

        # 将CV转换为置信度
        # 使用调整后的公式，使置信度更好地匹配期望范围
        # CV = 0 -> confidence ≈ 0.95 (完全稳定)
        # CV = 0.13 -> confidence ≈ 0.80 (中等波动)
        # CV = 0.65 -> confidence ≈ 0.55 (高波动)
        confidence = 0.95 * math.exp(-cv * 0.9)

        # 确保在0-1范围内
        confidence = max(0.0, min(1.0, confidence))

        return confidence

    def alert_if_over_budget(self) -> Optional[Dict[str, Any]]:
        """预算超限预警

        Returns:
            如果预测超预算，返回告警信息字典；否则返回None
        """
        prediction = self.predict_monthly_cost()

        if prediction["is_over_budget"]:
            alert = {
                "type": "budget_exceeded",
                "predicted_monthly": prediction["predicted_monthly"],
                "budget_monthly": prediction["budget_monthly"],
                "excess_amount": prediction["predicted_monthly"] - prediction["budget_monthly"],
                "budget_utilization": prediction["budget_utilization"],
                "message": (
                    f"预测月成本超预算: "
                    f"¥{prediction['predicted_monthly']:.2f} > "
                    f"¥{prediction['budget_monthly']:.2f}"
                ),
            }

            logger.warning(f"[CostPredictor] {alert['message']} " f"(超出: ¥{alert['excess_amount']:.2f})")

            return alert

        return None

    def get_cost_trend(self, days: int = 30) -> Dict[str, Any]:
        """获取成本趋势

        Args:
            days: 分析天数，默认30天

        Returns:
            成本趋势字典

        Raises:
            ValueError: 当天数无效时
        """
        if days <= 0:
            raise ValueError(f"天数必须 > 0: {days}")

        # 获取历史成本
        daily_costs = self._get_recent_daily_costs(days)

        if not daily_costs:
            return {"daily_costs": [], "trend": "stable", "avg_cost": 0.0, "max_cost": 0.0, "min_cost": 0.0}

        # 计算统计信息
        avg_cost = sum(daily_costs) / len(daily_costs)
        max_cost = max(daily_costs)
        min_cost = min(daily_costs)

        # 分析趋势
        trend = self._analyze_trend(daily_costs)

        return {
            "daily_costs": daily_costs,
            "trend": trend,
            "avg_cost": avg_cost,
            "max_cost": max_cost,
            "min_cost": min_cost,
        }

    def _analyze_trend(self, costs: List[float]) -> str:
        """分析成本趋势

        Args:
            costs: 成本列表

        Returns:
            趋势（increasing/decreasing/stable）
        """
        if len(costs) < 2:
            return "stable"

        # 简单线性回归：计算斜率
        n = len(costs)
        x_mean = (n - 1) / 2
        y_mean = sum(costs) / n

        numerator = sum((i - x_mean) * (costs[i] - y_mean) for i in range(n))
        denominator = sum((i - x_mean) ** 2 for i in range(n))

        if denominator == 0:
            return "stable"

        slope = numerator / denominator

        # 判断趋势
        threshold = y_mean * 0.05 if y_mean > 0 else 0.01

        if slope > threshold:
            return "increasing"
        if slope < -threshold:
            return "decreasing"
        return "stable"
