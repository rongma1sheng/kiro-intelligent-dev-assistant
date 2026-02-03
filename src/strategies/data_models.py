"""策略数据模型

白皮书依据: 第四章 4.2 斯巴达竞技场
"""

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Literal, Optional


@dataclass
class Signal:
    """交易信号

    策略生成的买卖信号
    """

    symbol: str  # 标的代码
    action: Literal["buy", "sell", "hold"]  # 操作
    confidence: float  # 信号置信度 (0.0-1.0)
    timestamp: str  # 信号生成时间
    reason: str  # 信号原因

    def __post_init__(self):
        """验证数据"""
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"置信度必须在[0.0, 1.0]范围内: {self.confidence}")

        if self.action not in ["buy", "sell", "hold"]:
            raise ValueError(f"无效的操作类型: {self.action}")


@dataclass
class Position:
    """仓位

    策略持有的仓位信息
    """

    symbol: str  # 标的代码
    size: float  # 仓位大小 (0.0-1.0)
    entry_price: float  # 入场价格
    current_price: float  # 当前价格
    pnl_pct: float  # 盈亏百分比
    holding_days: int  # 持仓天数
    industry: str  # 所属行业

    def __post_init__(self):
        """验证数据"""
        if not 0.0 <= self.size <= 1.0:
            raise ValueError(f"仓位大小必须在[0.0, 1.0]范围内: {self.size}")

        if self.entry_price <= 0:
            raise ValueError(f"入场价格必须大于0: {self.entry_price}")

        if self.current_price <= 0:
            raise ValueError(f"当前价格必须大于0: {self.current_price}")

        if self.holding_days < 0:
            raise ValueError(f"持仓天数不能为负: {self.holding_days}")

    def calculate_pnl(self) -> float:
        """计算盈亏百分比"""
        return (self.current_price - self.entry_price) / self.entry_price

    def update_pnl(self) -> None:
        """更新盈亏百分比"""
        self.pnl_pct = self.calculate_pnl()


@dataclass
class ArenaTestResult:
    """Arena测试结果

    白皮书依据: 第四章 4.2 斯巴达竞技场
    """

    strategy_name: str
    test_tier: str  # 测试档位
    initial_capital: float
    final_capital: float

    # 性能指标
    total_return_pct: float
    sharpe_ratio: float
    max_drawdown_pct: float
    win_rate: float

    # 策略进化出的参数
    evolved_params: Dict[str, Any]

    # 滑点和冲击成本
    avg_slippage_pct: float
    avg_impact_cost_pct: float

    # 测试时间
    test_start_date: str
    test_end_date: str

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ArenaTestResult":
        """从字典创建"""
        return cls(**data)


@dataclass
class StrategyConfig:  # pylint: disable=too-many-instance-attributes
    """策略配置

    白皮书依据: 第四章 4.2 斯巴达竞技场

    这些参数来自Arena测试中策略的自由进化结果
    """

    # 基本信息
    strategy_name: str
    capital_tier: str  # tier1_micro ~ tier6_ten_million

    # Arena进化出的风控参数
    max_position: float  # 最大总仓位 (0.0-1.0)
    max_single_stock: float  # 单股最大仓位 (0.0-1.0)
    max_industry: float  # 单行业最大仓位 (0.0-1.0)

    # Arena进化出的止损止盈参数
    stop_loss_pct: float  # 止损百分比 (负数)
    take_profit_pct: float  # 止盈百分比 (正数)
    trailing_stop_enabled: bool  # 是否启用移动止损
    trailing_stop_pct: Optional[float] = None  # 移动止损百分比

    # Arena进化出的流动性参数
    liquidity_threshold: float = 1000000.0  # 流动性阈值（日均成交额）
    max_order_pct_of_volume: float = 0.05  # 订单占日均成交量的最大比例

    # Arena进化出的交易频率参数
    trading_frequency: str = "medium"  # 'high' | 'medium' | 'low'
    holding_period_days: int = 5  # 持仓周期（天）

    # Z2H认证信息
    z2h_certified: bool = False
    z2h_certification_date: Optional[str] = None
    arena_test_tier: Optional[str] = None  # Arena测试时的档位
    arena_performance_metrics: Optional[Dict[str, float]] = None

    def __post_init__(self):
        """验证配置参数"""
        # 验证仓位参数
        if not 0.0 < self.max_position <= 1.0:
            raise ValueError(f"max_position必须在(0.0, 1.0]范围内: {self.max_position}")

        if not 0.0 < self.max_single_stock <= 1.0:
            raise ValueError(f"max_single_stock必须在(0.0, 1.0]范围内: {self.max_single_stock}")

        if not 0.0 < self.max_industry <= 1.0:
            raise ValueError(f"max_industry必须在(0.0, 1.0]范围内: {self.max_industry}")

        # 验证止损止盈参数
        if self.stop_loss_pct >= 0:
            raise ValueError(f"stop_loss_pct必须为负数: {self.stop_loss_pct}")

        if self.take_profit_pct <= 0:
            raise ValueError(f"take_profit_pct必须为正数: {self.take_profit_pct}")

        # 验证流动性参数
        if self.liquidity_threshold <= 0:
            raise ValueError(f"liquidity_threshold必须大于0: {self.liquidity_threshold}")

        if not 0.0 < self.max_order_pct_of_volume <= 1.0:
            raise ValueError(f"max_order_pct_of_volume必须在(0.0, 1.0]范围内: {self.max_order_pct_of_volume}")

        # 验证交易频率
        if self.trading_frequency not in ["high", "medium", "low"]:
            raise ValueError(f"trading_frequency必须是'high', 'medium'或'low': {self.trading_frequency}")

        if self.holding_period_days <= 0:
            raise ValueError(f"holding_period_days必须大于0: {self.holding_period_days}")

    @classmethod
    def from_arena_result(cls, arena_result: ArenaTestResult) -> "StrategyConfig":
        """从Arena测试结果创建配置

        Args:
            arena_result: Arena测试结果，包含策略进化出的所有参数

        Returns:
            StrategyConfig实例
        """
        evolved_params = arena_result.evolved_params

        return cls(
            strategy_name=arena_result.strategy_name,
            capital_tier=arena_result.test_tier,
            max_position=evolved_params.get("max_position", 0.8),
            max_single_stock=evolved_params.get("max_single_stock", 0.1),
            max_industry=evolved_params.get("max_industry", 0.3),
            stop_loss_pct=evolved_params.get("stop_loss_pct", -0.05),
            take_profit_pct=evolved_params.get("take_profit_pct", 0.10),
            trailing_stop_enabled=evolved_params.get("trailing_stop_enabled", False),
            trailing_stop_pct=evolved_params.get("trailing_stop_pct"),
            liquidity_threshold=evolved_params.get("liquidity_threshold", 1000000.0),
            max_order_pct_of_volume=evolved_params.get("max_order_pct_of_volume", 0.05),
            trading_frequency=evolved_params.get("trading_frequency", "medium"),
            holding_period_days=evolved_params.get("holding_period_days", 5),
            z2h_certified=False,  # 新创建的配置默认未认证
            arena_test_tier=arena_result.test_tier,
            arena_performance_metrics={
                "total_return_pct": arena_result.total_return_pct,
                "sharpe_ratio": arena_result.sharpe_ratio,
                "max_drawdown_pct": arena_result.max_drawdown_pct,
                "win_rate": arena_result.win_rate,
            },
        )

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StrategyConfig":
        """从字典创建"""
        return cls(**data)


@dataclass
class StrategyMetadata:
    """策略元数据

    策略池中存储的策略信息
    """

    strategy_name: str
    strategy_class: str  # 策略类名

    # Z2H认证信息
    z2h_certified: bool
    z2h_certification_date: Optional[str] = None

    # Arena测试结果
    best_tier: str = "tier1_micro"  # 表现最好的档位
    arena_results: Dict[str, ArenaTestResult] = field(default_factory=dict)  # 各档位测试结果

    # 策略配置
    config: Optional[StrategyConfig] = None

    # 实盘表现
    live_performance: Optional[Dict[str, float]] = None

    # 策略类型
    strategy_type: str = "unknown"  # momentum, mean_reversion, arbitrage, etc.

    # 是否支持多档位
    multi_tier_compatible: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        data = asdict(self)
        # 转换ArenaTestResult对象
        if self.arena_results:
            data["arena_results"] = {
                tier: result.to_dict() if isinstance(result, ArenaTestResult) else result
                for tier, result in self.arena_results.items()
            }
        # 转换StrategyConfig对象
        if self.config:
            data["config"] = self.config.to_dict() if isinstance(self.config, StrategyConfig) else self.config
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StrategyMetadata":
        """从字典创建"""
        # 转换arena_results
        if "arena_results" in data and data["arena_results"]:
            data["arena_results"] = {
                tier: ArenaTestResult.from_dict(result) if isinstance(result, dict) else result
                for tier, result in data["arena_results"].items()
            }

        # 转换config
        if "config" in data and data["config"] and isinstance(data["config"], dict):
            data["config"] = StrategyConfig.from_dict(data["config"])

        return cls(**data)
