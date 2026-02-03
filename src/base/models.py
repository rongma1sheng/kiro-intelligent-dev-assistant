"""
MIA系统基础数据模型

版本: v1.6.0
作者: MIA Team
日期: 2026-01-18
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class Strategy:
    """策略基础模型"""

    strategy_id: str
    name: str
    type: str
    description: str
    version: str = "1.0.0"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    parameters: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()


@dataclass
class SimulationResult:  # pylint: disable=too-many-instance-attributes
    """模拟回测结果模型"""

    strategy_id: str
    start_date: datetime
    end_date: datetime
    initial_capital: float
    final_capital: float

    # 基础收益指标
    total_return: float
    annual_return: float

    # 风险指标
    sharpe_ratio: float
    max_drawdown: float
    volatility: float

    # 交易指标
    win_rate: float

    # 详细数据
    daily_returns: List[float]

    # 其他指标
    calmar_ratio: float
    information_ratio: Optional[float] = None
    downside_deviation: Optional[float] = None

    # 扩展属性
    monthly_turnover: Optional[float] = None
    position_count: Optional[int] = None

    def __post_init__(self):
        """计算派生指标"""
        if self.information_ratio is None and self.daily_returns:
            # 简化的信息比率计算
            import numpy as np  # pylint: disable=import-outside-toplevel

            excess_returns = np.array(self.daily_returns)
            if len(excess_returns) > 1:
                std_returns = np.std(excess_returns)
                if std_returns > 0:
                    self.information_ratio = np.mean(excess_returns) / std_returns * np.sqrt(252)
                else:
                    self.information_ratio = 0.0
            else:
                self.information_ratio = 0.0

        if self.downside_deviation is None and self.daily_returns:
            # 计算下行偏差
            import numpy as np  # pylint: disable=import-outside-toplevel

            negative_returns = [r for r in self.daily_returns if r < 0]
            if negative_returns:
                self.downside_deviation = np.std(negative_returns) * np.sqrt(252)
            else:
                self.downside_deviation = 0.0


@dataclass
class TickData:
    """Tick数据模型"""

    symbol: str
    timestamp: datetime
    price: float
    volume: int
    bid: Optional[float] = None
    ask: Optional[float] = None
    bid_size: Optional[int] = None
    ask_size: Optional[int] = None


@dataclass
class OrderData:
    """订单数据模型"""

    order_id: str
    symbol: str
    side: str  # 'buy' or 'sell'
    quantity: int
    price: float
    order_type: str  # 'market', 'limit', etc.
    timestamp: datetime
    status: str = "pending"


@dataclass
class BarData:
    """K线数据模型"""

    symbol: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int
    interval: str = "1d"  # '1m', '5m', '1h', '1d', etc.
