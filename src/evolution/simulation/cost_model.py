"""Cost Model for Transaction Costs and Slippage

白皮书依据: 第四章 4.5.4 交易成本模型
"""

from loguru import logger


class CostModel:
    """交易成本模型

    白皮书依据: 第四章 4.5.4 交易成本模型

    计算真实的交易成本，包括佣金和滑点。

    Attributes:
        commission_rate: 佣金费率
        slippage_rate: 滑点率
    """

    def __init__(self, commission_rate: float = 0.0003, slippage_rate: float = 0.0005):
        """初始化成本模型

        Args:
            commission_rate: 佣金费率，默认0.03%
            slippage_rate: 滑点率，默认0.05%

        Raises:
            ValueError: 当费率不在有效范围时
        """
        if not 0 <= commission_rate <= 1:
            raise ValueError(f"commission_rate必须在[0,1]，当前: {commission_rate}")

        if not 0 <= slippage_rate <= 1:
            raise ValueError(f"slippage_rate必须在[0,1]，当前: {slippage_rate}")

        self.commission_rate = commission_rate
        self.slippage_rate = slippage_rate

        logger.info(
            f"初始化CostModel: " f"commission_rate={commission_rate:.4f}, " f"slippage_rate={slippage_rate:.4f}"
        )

    def calculate_transaction_cost(self, trade_value: float, is_buy: bool = True) -> float:
        """计算交易成本

        白皮书依据: 第四章 4.5.4 交易成本模型 - Requirement 6.4

        交易成本 = 交易金额 × (佣金费率 + 滑点率)

        Args:
            trade_value: 交易金额（绝对值）
            is_buy: 是否为买入交易

        Returns:
            交易成本（正数）

        Raises:
            ValueError: 当trade_value为负时
        """
        if trade_value < 0:
            raise ValueError(f"trade_value不能为负，当前: {trade_value}")

        # 计算佣金
        commission = trade_value * self.commission_rate

        # 计算滑点
        slippage = trade_value * self.slippage_rate

        # 总成本
        total_cost = commission + slippage

        logger.debug(
            f"计算交易成本: "
            f"trade_value={trade_value:.2f}, "
            f"is_buy={is_buy}, "
            f"commission={commission:.2f}, "
            f"slippage={slippage:.2f}, "
            f"total_cost={total_cost:.2f}"
        )

        return total_cost

    def apply_costs_to_trades(self, trades: list) -> float:
        """对交易列表应用成本

        Args:
            trades: 交易列表，每个交易包含 'value' 和 'side' 字段

        Returns:
            总交易成本
        """
        total_cost = 0.0

        for trade in trades:
            trade_value = abs(trade.get("value", 0.0))
            is_buy = trade.get("side", "buy") == "buy"

            cost = self.calculate_transaction_cost(trade_value, is_buy)
            total_cost += cost

            # 将成本添加到交易记录
            trade["cost"] = cost

        return total_cost

    def get_effective_price(self, market_price: float, is_buy: bool = True) -> float:
        """获取考虑滑点后的有效价格

        Args:
            market_price: 市场价格
            is_buy: 是否为买入

        Returns:
            有效价格（买入时更高，卖出时更低）
        """
        if market_price <= 0:
            raise ValueError(f"market_price必须>0，当前: {market_price}")

        if is_buy:
            # 买入时价格更高
            effective_price = market_price * (1 + self.slippage_rate)
        else:
            # 卖出时价格更低
            effective_price = market_price * (1 - self.slippage_rate)

        return effective_price
