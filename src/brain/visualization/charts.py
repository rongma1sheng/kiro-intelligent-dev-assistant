# pylint: disable=too-many-lines
"""图表生成器

白皮书依据: 第五章 5.4.3 29种可视化图表

本模块实现了图表生成器，负责生成29种专业可视化图表：
1-10: 策略分析图表
11-20: 市场分析图表
21-29: 进化和个股图表

性能要求: 单个图表渲染 < 2秒
"""

import io
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from loguru import logger

# 尝试导入可视化库
try:
    import matplotlib

    matplotlib.use("Agg")  # 使用非交互式后端
    import matplotlib.pyplot as plt

    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    logger.warning("matplotlib未安装，图表生成功能将受限")

try:
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False
    logger.warning("plotly未安装，部分图表功能将受限")


# ============================================================================
# 数据模型
# ============================================================================

from dataclasses import dataclass  # pylint: disable=c0413,c0411


@dataclass
class OverfittingData:
    """过拟合数据"""

    in_sample_sharpe: float
    out_sample_sharpe: float
    parameter_sensitivity: float
    complexity_score: float
    risk_level: str


@dataclass
class NonstationarityData:
    """非平稳性数据"""

    adf_statistic: float
    p_value: float
    rolling_mean: List[float]
    rolling_std: List[float]
    timestamps: List[datetime]


@dataclass
class SignalNoiseData:
    """信噪比数据"""

    snr_values: List[float]
    timestamps: List[datetime]
    trend: str


@dataclass
class CapacityData:
    """资金容量数据"""

    capacity_levels: List[float]
    impact_costs: List[float]
    optimal_capacity: float


@dataclass
class StopLossData:
    """止损数据"""

    strategies: List[str]
    effectiveness: List[float]
    avg_loss_reduction: List[float]


@dataclass
class TradeRecord:
    """交易记录"""

    trade_id: str
    symbol: str
    direction: str
    price: float
    quantity: int
    pnl: float
    timestamp: datetime


@dataclass
class SentimentData:
    """情绪数据"""

    timestamps: List[datetime]
    sentiment_scores: List[float]
    market_returns: List[float]


@dataclass
class SmartRetailData:
    """主力散户数据"""

    smart_money_sentiment: Dict[str, float]
    retail_sentiment: Dict[str, float]
    divergence_score: float


@dataclass
class MarketTechnicalData:
    """大盘技术面数据"""

    dates: List[datetime]
    prices: List[float]
    ma5: List[float]
    ma20: List[float]
    volume: List[float]
    rsi: List[float]


@dataclass
class LimitUpData:
    """涨停板数据"""

    sectors: List[str]
    counts: List[int]
    date: datetime


@dataclass
class SectorStrengthData:
    """行业强弱数据"""

    sectors: List[str]
    strength_scores: List[float]
    momentum_scores: List[float]


@dataclass
class SectorRotationData:
    """板块轮动数据"""

    sectors: List[str]
    rotation_sequence: List[int]
    current_leader: str


@dataclass
class DrawdownData:
    """回撤数据"""

    dates: List[datetime]
    drawdown_values: List[float]
    max_drawdown: float
    max_drawdown_date: datetime


@dataclass
class EfficientFrontierData:
    """有效前沿数据"""

    returns: List[float]
    volatilities: List[float]
    sharpe_ratios: List[float]
    optimal_portfolio: Tuple[float, float]


@dataclass
class StressTestData:
    """压力测试数据"""

    scenarios: List[str]
    impacts: List[float]
    recovery_times: List[int]


@dataclass
class TradingCostData:
    """交易成本数据"""

    cost_types: List[str]
    amounts: List[float]
    percentages: List[float]


@dataclass
class DecayData:
    """策略衰减数据"""

    dates: List[datetime]
    performance_values: List[float]
    decay_rate: float


@dataclass
class PositionData:
    """仓位数据"""

    symbols: List[str]
    weights: List[float]
    risk_contributions: List[float]


@dataclass
class FitnessEvolutionData:
    """适应度演化数据"""

    generations: List[int]
    fitness_values: List[float]
    best_fitness: float


@dataclass
class ArenaComparisonData:
    """Arena对比数据"""

    strategies: List[str]
    reality_scores: List[float]
    hell_scores: List[float]
    cross_market_scores: List[float]


@dataclass
class FactorEvolutionData:
    """因子演化数据"""

    factor_names: List[str]
    ic_values: List[float]
    ir_values: List[float]


@dataclass
class SmartMoneyCostData:
    """主力成本数据"""

    price_levels: List[float]
    volume_distribution: List[float]
    avg_cost: float


@dataclass
class StockScorecardData:
    """个股评分卡数据"""

    symbol: str
    name: str
    dimensions: List[str]
    scores: List[float]
    overall_score: float


# ============================================================================
# 图表生成器
# ============================================================================


class ChartGenerationError(Exception):
    """图表生成错误"""


class ChartGenerator:  # pylint: disable=too-many-public-methods
    """图表生成器

    白皮书依据: 第五章 5.4.3 29种可视化图表

    生成29种专业可视化图表。

    性能要求: 单个图表渲染 < 2秒

    图表类型:
    1-10: 策略分析图表
    11-20: 市场分析图表
    21-29: 进化和个股图表
    """

    # 默认图表尺寸
    DEFAULT_FIGSIZE = (10, 6)
    DEFAULT_DPI = 100

    # 颜色方案
    COLORS = {
        "primary": "#1f77b4",
        "secondary": "#ff7f0e",
        "success": "#2ca02c",
        "danger": "#d62728",
        "warning": "#ffbb78",
        "info": "#17becf",
        "neutral": "#7f7f7f",
    }

    def __init__(self) -> None:
        """初始化图表生成器"""
        self._setup_matplotlib()
        logger.info("ChartGenerator初始化完成")

    def _setup_matplotlib(self) -> None:
        """配置matplotlib"""
        if not MATPLOTLIB_AVAILABLE:
            return

        # 设置中文字体
        plt.rcParams["font.sans-serif"] = ["SimHei", "DejaVu Sans", "Arial"]
        plt.rcParams["axes.unicode_minus"] = False
        plt.rcParams["figure.dpi"] = self.DEFAULT_DPI

    def _create_figure(
        self,
        figsize: Optional[Tuple[int, int]] = None,
    ) -> Tuple[Any, Any]:
        """创建图表画布"""
        if not MATPLOTLIB_AVAILABLE:
            raise ChartGenerationError("matplotlib未安装")

        fig, ax = plt.subplots(figsize=figsize or self.DEFAULT_FIGSIZE)
        return fig, ax

    def _figure_to_bytes(self, fig: Any, format: str = "png") -> bytes:  # pylint: disable=w0622
        """将图表转换为字节数据"""
        buf = io.BytesIO()
        fig.savefig(buf, format=format, bbox_inches="tight", dpi=self.DEFAULT_DPI)
        buf.seek(0)
        plt.close(fig)
        return buf.getvalue()

    # ========================================================================
    # 策略分析图表 (1-10)
    # ========================================================================

    def generate_essence_radar(
        self,
        data: Dict[str, float],
    ) -> bytes:
        """1. 策略本质雷达图

        白皮书依据: 第五章 5.4.3 图表1

        展示策略在多个维度上的表现。

        Args:
            data: 维度名称到得分的字典

        Returns:
            bytes: PNG图像数据
        """
        if not data:
            raise ChartGenerationError("数据不能为空")

        if not MATPLOTLIB_AVAILABLE:
            return self._generate_placeholder_chart("策略本质雷达图")

        categories = list(data.keys())
        values = list(data.values())

        # 闭合雷达图
        values += values[:1]

        # 计算角度
        angles = np.linspace(0, 2 * np.pi, len(categories), endpoint=False).tolist()
        angles += angles[:1]

        fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(polar=True))  # pylint: disable=r1735

        ax.fill(angles, values, color=self.COLORS["primary"], alpha=0.25)
        ax.plot(angles, values, color=self.COLORS["primary"], linewidth=2)

        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(categories)
        ax.set_title("策略本质雷达图", fontsize=14, fontweight="bold")

        return self._figure_to_bytes(fig)

    def generate_overfitting_dashboard(
        self,
        data: OverfittingData,
    ) -> bytes:
        """2. 过拟合风险仪表盘

        白皮书依据: 第五章 5.4.3 图表2

        展示策略的过拟合风险指标。

        Args:
            data: 过拟合数据

        Returns:
            bytes: PNG图像数据
        """
        if not MATPLOTLIB_AVAILABLE:
            return self._generate_placeholder_chart("过拟合风险仪表盘")

        fig, axes = plt.subplots(2, 2, figsize=(12, 10))

        # 样本内外夏普比率对比
        ax1 = axes[0, 0]
        bars = ax1.bar(  # pylint: disable=unused-variable
            ["样本内", "样本外"],
            [data.in_sample_sharpe, data.out_sample_sharpe],
            color=[self.COLORS["primary"], self.COLORS["secondary"]],
        )
        ax1.set_title("夏普比率对比")
        ax1.set_ylabel("夏普比率")

        # 参数敏感度仪表
        ax2 = axes[0, 1]
        ax2.pie(
            [data.parameter_sensitivity, 1 - data.parameter_sensitivity],
            labels=["敏感", "稳定"],
            colors=[self.COLORS["danger"], self.COLORS["success"]],
            autopct="%1.1f%%",
        )
        ax2.set_title("参数敏感度")

        # 复杂度评分
        ax3 = axes[1, 0]
        ax3.barh(["复杂度"], [data.complexity_score], color=self.COLORS["warning"])
        ax3.set_xlim(0, 1)
        ax3.set_title("模型复杂度")

        # 风险等级
        ax4 = axes[1, 1]
        risk_colors = {"低": "green", "中": "orange", "高": "red"}
        ax4.text(
            0.5,
            0.5,
            data.risk_level,
            fontsize=48,
            ha="center",
            va="center",
            color=risk_colors.get(data.risk_level, "gray"),
        )
        ax4.set_title("过拟合风险等级")
        ax4.axis("off")

        fig.suptitle("过拟合风险仪表盘", fontsize=16, fontweight="bold")
        plt.tight_layout()

        return self._figure_to_bytes(fig)

    def generate_feature_importance_bar(
        self,
        data: List[Tuple[str, float]],
    ) -> bytes:
        """3. 特征重要性柱状图

        白皮书依据: 第五章 5.4.3 图表3

        展示各特征的重要性排名。

        Args:
            data: (特征名, 重要性)元组列表

        Returns:
            bytes: PNG图像数据
        """
        if not data:
            raise ChartGenerationError("数据不能为空")

        if not MATPLOTLIB_AVAILABLE:
            return self._generate_placeholder_chart("特征重要性柱状图")

        # 按重要性排序
        sorted_data = sorted(data, key=lambda x: x[1], reverse=True)
        features = [d[0] for d in sorted_data]
        importances = [d[1] for d in sorted_data]

        fig, ax = self._create_figure(figsize=(10, max(6, len(features) * 0.4)))

        colors = plt.cm.Blues(np.linspace(0.4, 0.9, len(features)))  # pylint: disable=no-member
        ax.barh(features, importances, color=colors)

        ax.set_xlabel("重要性")
        ax.set_title("特征重要性排名", fontsize=14, fontweight="bold")
        ax.invert_yaxis()

        return self._figure_to_bytes(fig)

    def generate_correlation_heatmap(
        self,
        data: np.ndarray,
        labels: Optional[List[str]] = None,
    ) -> bytes:
        """4. 相关性热力图

        白皮书依据: 第五章 5.4.3 图表4

        展示因子或策略之间的相关性。

        Args:
            data: 相关性矩阵
            labels: 标签列表

        Returns:
            bytes: PNG图像数据
        """
        if data.size == 0:
            raise ChartGenerationError("数据不能为空")

        if not MATPLOTLIB_AVAILABLE:
            return self._generate_placeholder_chart("相关性热力图")

        fig, ax = self._create_figure(figsize=(10, 8))

        im = ax.imshow(data, cmap="RdYlBu_r", aspect="auto", vmin=-1, vmax=1)

        if labels:
            ax.set_xticks(range(len(labels)))
            ax.set_yticks(range(len(labels)))
            ax.set_xticklabels(labels, rotation=45, ha="right")
            ax.set_yticklabels(labels)

        plt.colorbar(im, ax=ax, label="相关系数")
        ax.set_title("相关性热力图", fontsize=14, fontweight="bold")

        return self._figure_to_bytes(fig)

    def generate_nonstationarity_chart(
        self,
        data: NonstationarityData,
    ) -> bytes:
        """5. 非平稳性分析图

        白皮书依据: 第五章 5.4.3 图表5

        展示时间序列的非平稳性特征。

        Args:
            data: 非平稳性数据

        Returns:
            bytes: PNG图像数据
        """
        if not MATPLOTLIB_AVAILABLE:
            return self._generate_placeholder_chart("非平稳性分析图")

        fig, axes = plt.subplots(2, 1, figsize=(12, 8), sharex=True)

        # 滚动均值
        ax1 = axes[0]
        ax1.plot(data.timestamps, data.rolling_mean, color=self.COLORS["primary"], label="滚动均值")
        ax1.set_ylabel("均值")
        ax1.set_title(f"ADF统计量: {data.adf_statistic:.4f}, p值: {data.p_value:.4f}")
        ax1.legend()

        # 滚动标准差
        ax2 = axes[1]
        ax2.plot(data.timestamps, data.rolling_std, color=self.COLORS["secondary"], label="滚动标准差")
        ax2.set_ylabel("标准差")
        ax2.set_xlabel("时间")
        ax2.legend()

        fig.suptitle("非平稳性分析", fontsize=14, fontweight="bold")
        plt.tight_layout()

        return self._figure_to_bytes(fig)

    def generate_signal_noise_trend(
        self,
        data: SignalNoiseData,
    ) -> bytes:
        """6. 信噪比趋势图

        白皮书依据: 第五章 5.4.3 图表6

        展示策略信噪比的变化趋势。

        Args:
            data: 信噪比数据

        Returns:
            bytes: PNG图像数据
        """
        if not MATPLOTLIB_AVAILABLE:
            return self._generate_placeholder_chart("信噪比趋势图")

        fig, ax = self._create_figure()

        ax.plot(data.timestamps, data.snr_values, color=self.COLORS["primary"], linewidth=2)
        ax.axhline(y=np.mean(data.snr_values), color=self.COLORS["danger"], linestyle="--", label="平均值")

        ax.fill_between(
            data.timestamps,
            data.snr_values,
            alpha=0.3,
            color=self.COLORS["success"] if data.trend == "上升" else self.COLORS["danger"],
        )

        ax.set_xlabel("时间")
        ax.set_ylabel("信噪比")
        ax.set_title(f"信噪比趋势 (趋势: {data.trend})", fontsize=14, fontweight="bold")
        ax.legend()

        return self._figure_to_bytes(fig)

    def generate_capacity_curve(
        self,
        data: CapacityData,
    ) -> bytes:
        """7. 资金容量曲线

        白皮书依据: 第五章 5.4.3 图表7

        展示策略的资金容量与冲击成本关系。

        Args:
            data: 资金容量数据

        Returns:
            bytes: PNG图像数据
        """
        if not MATPLOTLIB_AVAILABLE:
            return self._generate_placeholder_chart("资金容量曲线")

        fig, ax = self._create_figure()

        ax.plot(data.capacity_levels, data.impact_costs, color=self.COLORS["primary"], linewidth=2)
        ax.axvline(
            x=data.optimal_capacity,
            color=self.COLORS["success"],
            linestyle="--",
            label=f"最优容量: {data.optimal_capacity:.0f}",
        )

        ax.set_xlabel("资金规模")
        ax.set_ylabel("冲击成本 (%)")
        ax.set_title("资金容量曲线", fontsize=14, fontweight="bold")
        ax.legend()

        return self._figure_to_bytes(fig)

    def generate_market_adaptation_matrix(
        self,
        data: Dict[str, Dict[str, float]],
    ) -> bytes:
        """8. 市场适配性矩阵

        白皮书依据: 第五章 5.4.3 图表8

        展示策略在不同市场环境下的表现。

        Args:
            data: 市场环境到表现的嵌套字典

        Returns:
            bytes: PNG图像数据
        """
        if not data:
            raise ChartGenerationError("数据不能为空")

        if not MATPLOTLIB_AVAILABLE:
            return self._generate_placeholder_chart("市场适配性矩阵")

        markets = list(data.keys())
        metrics = list(data[markets[0]].keys()) if markets else []

        matrix = np.array([[data[m][metric] for metric in metrics] for m in markets])

        fig, ax = self._create_figure(figsize=(10, 8))

        im = ax.imshow(matrix, cmap="RdYlGn", aspect="auto")

        ax.set_xticks(range(len(metrics)))
        ax.set_yticks(range(len(markets)))
        ax.set_xticklabels(metrics, rotation=45, ha="right")
        ax.set_yticklabels(markets)

        # 添加数值标注
        for i in range(len(markets)):
            for j in range(len(metrics)):
                ax.text(j, i, f"{matrix[i, j]:.2f}", ha="center", va="center")

        plt.colorbar(im, ax=ax, label="表现得分")
        ax.set_title("市场适配性矩阵", fontsize=14, fontweight="bold")

        return self._figure_to_bytes(fig)

    def generate_stop_loss_comparison(
        self,
        data: StopLossData,
    ) -> bytes:
        """9. 止损效果对比图

        白皮书依据: 第五章 5.4.3 图表9

        对比不同止损策略的效果。

        Args:
            data: 止损数据

        Returns:
            bytes: PNG图像数据
        """
        if not MATPLOTLIB_AVAILABLE:
            return self._generate_placeholder_chart("止损效果对比图")

        fig, ax = self._create_figure()

        x = np.arange(len(data.strategies))
        width = 0.35

        bars1 = ax.bar(  # pylint: disable=unused-variable
            x - width / 2, data.effectiveness, width, label="有效性", color=self.COLORS["primary"]
        )  # pylint: disable=unused-variable
        bars2 = ax.bar(  # pylint: disable=unused-variable
            x + width / 2, data.avg_loss_reduction, width, label="平均损失减少", color=self.COLORS["secondary"]
        )

        ax.set_xlabel("止损策略")
        ax.set_ylabel("得分")
        ax.set_title("止损效果对比", fontsize=14, fontweight="bold")
        ax.set_xticks(x)
        ax.set_xticklabels(data.strategies, rotation=45, ha="right")
        ax.legend()

        return self._figure_to_bytes(fig)

    def generate_slippage_histogram(
        self,
        data: List[float],
    ) -> bytes:
        """10. 滑点分布直方图

        白皮书依据: 第五章 5.4.3 图表10

        展示交易滑点的分布情况。

        Args:
            data: 滑点值列表

        Returns:
            bytes: PNG图像数据
        """
        if not data:
            raise ChartGenerationError("数据不能为空")

        if not MATPLOTLIB_AVAILABLE:
            return self._generate_placeholder_chart("滑点分布直方图")

        fig, ax = self._create_figure()

        ax.hist(data, bins=30, color=self.COLORS["primary"], alpha=0.7, edgecolor="black")
        ax.axvline(x=np.mean(data), color=self.COLORS["danger"], linestyle="--", label=f"平均: {np.mean(data):.4f}")
        ax.axvline(
            x=np.median(data), color=self.COLORS["success"], linestyle="--", label=f"中位数: {np.median(data):.4f}"
        )

        ax.set_xlabel("滑点 (%)")
        ax.set_ylabel("频次")
        ax.set_title("滑点分布", fontsize=14, fontweight="bold")
        ax.legend()

        return self._figure_to_bytes(fig)

    # ========================================================================
    # 市场分析图表 (11-20)
    # ========================================================================

    def generate_trade_review_timeline(
        self,
        data: List[TradeRecord],
    ) -> bytes:
        """11. 交易复盘时间线

        白皮书依据: 第五章 5.4.3 图表11

        展示交易记录的时间线。

        Args:
            data: 交易记录列表

        Returns:
            bytes: PNG图像数据
        """
        if not data:
            raise ChartGenerationError("数据不能为空")

        if not MATPLOTLIB_AVAILABLE:
            return self._generate_placeholder_chart("交易复盘时间线")

        fig, ax = self._create_figure(figsize=(14, 6))

        timestamps = [t.timestamp for t in data]
        pnls = [t.pnl for t in data]
        colors = [self.COLORS["success"] if p > 0 else self.COLORS["danger"] for p in pnls]

        ax.scatter(timestamps, pnls, c=colors, s=50, alpha=0.7)
        ax.axhline(y=0, color="black", linestyle="-", linewidth=0.5)

        ax.set_xlabel("时间")
        ax.set_ylabel("盈亏")
        ax.set_title("交易复盘时间线", fontsize=14, fontweight="bold")

        return self._figure_to_bytes(fig)

    def generate_sentiment_evolution(
        self,
        data: SentimentData,
    ) -> bytes:
        """12. 市场情绪演化曲线

        白皮书依据: 第五章 5.4.3 图表12

        展示市场情绪与收益的关系。

        Args:
            data: 情绪数据

        Returns:
            bytes: PNG图像数据
        """
        if not MATPLOTLIB_AVAILABLE:
            return self._generate_placeholder_chart("市场情绪演化曲线")

        fig, ax1 = self._create_figure()

        ax1.plot(data.timestamps, data.sentiment_scores, color=self.COLORS["primary"], label="情绪指数")
        ax1.set_xlabel("时间")
        ax1.set_ylabel("情绪指数", color=self.COLORS["primary"])
        ax1.tick_params(axis="y", labelcolor=self.COLORS["primary"])

        ax2 = ax1.twinx()
        ax2.plot(data.timestamps, data.market_returns, color=self.COLORS["secondary"], label="市场收益", alpha=0.7)
        ax2.set_ylabel("市场收益 (%)", color=self.COLORS["secondary"])
        ax2.tick_params(axis="y", labelcolor=self.COLORS["secondary"])

        fig.suptitle("市场情绪演化", fontsize=14, fontweight="bold")
        fig.legend(loc="upper right")

        return self._figure_to_bytes(fig)

    def generate_smart_vs_retail_radar(
        self,
        data: SmartRetailData,
    ) -> bytes:
        """13. 主力vs散户情绪雷达图

        白皮书依据: 第五章 5.4.3 图表13

        对比主力和散户的情绪分布。

        Args:
            data: 主力散户数据

        Returns:
            bytes: PNG图像数据
        """
        if not MATPLOTLIB_AVAILABLE:
            return self._generate_placeholder_chart("主力vs散户情绪雷达图")

        categories = list(data.smart_money_sentiment.keys())
        smart_values = list(data.smart_money_sentiment.values())
        retail_values = list(data.retail_sentiment.values())

        # 闭合雷达图
        smart_values += smart_values[:1]
        retail_values += retail_values[:1]

        angles = np.linspace(0, 2 * np.pi, len(categories), endpoint=False).tolist()
        angles += angles[:1]

        fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(polar=True))  # pylint: disable=r1735

        ax.fill(angles, smart_values, color=self.COLORS["primary"], alpha=0.25, label="主力")
        ax.plot(angles, smart_values, color=self.COLORS["primary"], linewidth=2)

        ax.fill(angles, retail_values, color=self.COLORS["secondary"], alpha=0.25, label="散户")
        ax.plot(angles, retail_values, color=self.COLORS["secondary"], linewidth=2)

        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(categories)
        ax.set_title(f"主力vs散户情绪 (分歧度: {data.divergence_score:.2f})", fontsize=14, fontweight="bold")
        ax.legend(loc="upper right")

        return self._figure_to_bytes(fig)

    def generate_market_technical_chart(
        self,
        data: MarketTechnicalData,
    ) -> bytes:
        """14. 大盘技术面分析图

        白皮书依据: 第五章 5.4.3 图表14

        展示大盘的技术分析指标。

        Args:
            data: 大盘技术面数据

        Returns:
            bytes: PNG图像数据
        """
        if not MATPLOTLIB_AVAILABLE:
            return self._generate_placeholder_chart("大盘技术面分析图")

        fig, axes = plt.subplots(3, 1, figsize=(14, 10), sharex=True)

        # 价格和均线
        ax1 = axes[0]
        ax1.plot(data.dates, data.prices, color="black", label="价格", linewidth=1.5)
        ax1.plot(data.dates, data.ma5, color=self.COLORS["primary"], label="MA5", linewidth=1)
        ax1.plot(data.dates, data.ma20, color=self.COLORS["secondary"], label="MA20", linewidth=1)
        ax1.set_ylabel("价格")
        ax1.legend(loc="upper left")
        ax1.set_title("大盘技术面分析", fontsize=14, fontweight="bold")

        # 成交量
        ax2 = axes[1]
        ax2.bar(data.dates, data.volume, color=self.COLORS["info"], alpha=0.7)
        ax2.set_ylabel("成交量")

        # RSI
        ax3 = axes[2]
        ax3.plot(data.dates, data.rsi, color=self.COLORS["primary"])
        ax3.axhline(y=70, color=self.COLORS["danger"], linestyle="--", alpha=0.5)
        ax3.axhline(y=30, color=self.COLORS["success"], linestyle="--", alpha=0.5)
        ax3.set_ylabel("RSI")
        ax3.set_xlabel("日期")
        ax3.set_ylim(0, 100)

        plt.tight_layout()

        return self._figure_to_bytes(fig)

    def generate_limit_up_heatmap(
        self,
        data: LimitUpData,
    ) -> bytes:
        """15. 涨停板分布热力图

        白皮书依据: 第五章 5.4.3 图表15

        展示各板块涨停板分布。

        Args:
            data: 涨停板数据

        Returns:
            bytes: PNG图像数据
        """
        if not MATPLOTLIB_AVAILABLE:
            return self._generate_placeholder_chart("涨停板分布热力图")

        fig, ax = self._create_figure(figsize=(12, 6))

        colors = plt.cm.Reds(  # pylint: disable=no-member
            np.array(data.counts) / max(data.counts) if max(data.counts) > 0 else np.zeros(len(data.counts))
        )
        bars = ax.barh(data.sectors, data.counts, color=colors)

        # 添加数值标注
        for bar, count in zip(bars, data.counts):  # pylint: disable=c0104
            ax.text(bar.get_width() + 0.1, bar.get_y() + bar.get_height() / 2, str(count), va="center")

        ax.set_xlabel("涨停数量")
        ax.set_title(f"涨停板分布 ({data.date.strftime('%Y-%m-%d')})", fontsize=14, fontweight="bold")

        return self._figure_to_bytes(fig)

    def generate_sector_strength_matrix(
        self,
        data: SectorStrengthData,
    ) -> bytes:
        """16. 行业强弱矩阵

        白皮书依据: 第五章 5.4.3 图表16

        展示各行业的强弱对比。

        Args:
            data: 行业强弱数据

        Returns:
            bytes: PNG图像数据
        """
        if not MATPLOTLIB_AVAILABLE:
            return self._generate_placeholder_chart("行业强弱矩阵")

        fig, ax = self._create_figure(figsize=(10, 8))

        ax.scatter(
            data.strength_scores, data.momentum_scores, s=100, alpha=0.7, c=range(len(data.sectors)), cmap="viridis"
        )

        for i, sector in enumerate(data.sectors):
            ax.annotate(sector, (data.strength_scores[i], data.momentum_scores[i]), fontsize=8)

        ax.axhline(y=0, color="gray", linestyle="--", alpha=0.5)
        ax.axvline(x=0, color="gray", linestyle="--", alpha=0.5)

        ax.set_xlabel("强度得分")
        ax.set_ylabel("动量得分")
        ax.set_title("行业强弱矩阵", fontsize=14, fontweight="bold")

        return self._figure_to_bytes(fig)

    def generate_sector_rotation_chart(
        self,
        data: SectorRotationData,
    ) -> bytes:
        """17. 板块轮动图

        白皮书依据: 第五章 5.4.3 图表17

        展示板块轮动顺序。

        Args:
            data: 板块轮动数据

        Returns:
            bytes: PNG图像数据
        """
        if not MATPLOTLIB_AVAILABLE:
            return self._generate_placeholder_chart("板块轮动图")

        fig, ax = self._create_figure(figsize=(12, 6))

        # 创建轮动序列图
        sorted_indices = np.argsort(data.rotation_sequence)
        sorted_sectors = [data.sectors[i] for i in sorted_indices]

        y_pos = range(len(sorted_sectors))
        colors = [
            self.COLORS["success"] if s == data.current_leader else self.COLORS["primary"] for s in sorted_sectors
        ]

        ax.barh(y_pos, [1] * len(sorted_sectors), color=colors, alpha=0.7)
        ax.set_yticks(y_pos)
        ax.set_yticklabels(sorted_sectors)

        # 添加箭头表示轮动方向
        for i in range(len(sorted_sectors) - 1):
            ax.annotate(
                "",
                xy=(0.5, i + 0.5),
                xytext=(0.5, i + 1.5),
                arrowprops=dict(arrowstyle="->", color="gray"),  # pylint: disable=r1735
            )  # pylint: disable=r1735

        ax.set_xlabel("轮动顺序")
        ax.set_title(f"板块轮动 (当前领涨: {data.current_leader})", fontsize=14, fontweight="bold")
        ax.set_xlim(0, 1.5)

        return self._figure_to_bytes(fig)

    def generate_drawdown_underwater(
        self,
        data: DrawdownData,
    ) -> bytes:
        """18. 回撤水下曲线

        白皮书依据: 第五章 5.4.3 图表18

        展示策略的回撤情况。

        Args:
            data: 回撤数据

        Returns:
            bytes: PNG图像数据
        """
        if not MATPLOTLIB_AVAILABLE:
            return self._generate_placeholder_chart("回撤水下曲线")

        fig, ax = self._create_figure()

        ax.fill_between(data.dates, data.drawdown_values, 0, color=self.COLORS["danger"], alpha=0.5)
        ax.plot(data.dates, data.drawdown_values, color=self.COLORS["danger"], linewidth=1)

        # 标记最大回撤点
        ax.scatter([data.max_drawdown_date], [data.max_drawdown], color="black", s=100, zorder=5)
        ax.annotate(
            f"最大回撤: {data.max_drawdown:.2%}",
            xy=(data.max_drawdown_date, data.max_drawdown),
            xytext=(10, 10),
            textcoords="offset points",
        )

        ax.set_xlabel("日期")
        ax.set_ylabel("回撤 (%)")
        ax.set_title("回撤水下曲线", fontsize=14, fontweight="bold")
        ax.set_ylim(min(data.drawdown_values) * 1.1, 0.01)

        return self._figure_to_bytes(fig)

    def generate_strategy_correlation_heatmap(
        self,
        data: np.ndarray,
        labels: Optional[List[str]] = None,
    ) -> bytes:
        """19. 策略相关性热力图

        白皮书依据: 第五章 5.4.3 图表19

        展示多策略之间的相关性。

        Args:
            data: 相关性矩阵
            labels: 策略标签

        Returns:
            bytes: PNG图像数据
        """
        # 复用相关性热力图方法
        return self.generate_correlation_heatmap(data, labels)

    def generate_efficient_frontier(
        self,
        data: EfficientFrontierData,
    ) -> bytes:
        """20. 有效前沿曲线

        白皮书依据: 第五章 5.4.3 图表20

        展示投资组合的有效前沿。

        Args:
            data: 有效前沿数据

        Returns:
            bytes: PNG图像数据
        """
        if not MATPLOTLIB_AVAILABLE:
            return self._generate_placeholder_chart("有效前沿曲线")

        fig, ax = self._create_figure()

        scatter = ax.scatter(data.volatilities, data.returns, c=data.sharpe_ratios, cmap="viridis", s=50, alpha=0.7)
        plt.colorbar(scatter, ax=ax, label="夏普比率")

        # 标记最优组合
        ax.scatter(
            [data.optimal_portfolio[0]],
            [data.optimal_portfolio[1]],
            color=self.COLORS["danger"],
            s=200,
            marker="*",
            label="最优组合",
        )

        ax.set_xlabel("波动率 (%)")
        ax.set_ylabel("收益率 (%)")
        ax.set_title("有效前沿曲线", fontsize=14, fontweight="bold")
        ax.legend()

        return self._figure_to_bytes(fig)

    # ========================================================================
    # 进化和个股图表 (21-29)
    # ========================================================================

    def generate_stress_test_result(
        self,
        data: StressTestData,
    ) -> bytes:
        """21. 压力测试结果图

        白皮书依据: 第五章 5.4.3 图表21

        展示压力测试的结果。

        Args:
            data: 压力测试数据

        Returns:
            bytes: PNG图像数据
        """
        if not MATPLOTLIB_AVAILABLE:
            return self._generate_placeholder_chart("压力测试结果图")

        fig, axes = plt.subplots(1, 2, figsize=(14, 6))

        # 影响程度
        ax1 = axes[0]
        colors = [
            self.COLORS["danger"] if i < -0.1 else self.COLORS["warning"] if i < 0 else self.COLORS["success"]
            for i in data.impacts
        ]
        ax1.barh(data.scenarios, data.impacts, color=colors)
        ax1.set_xlabel("影响程度 (%)")
        ax1.set_title("压力场景影响")
        ax1.axvline(x=0, color="black", linestyle="-", linewidth=0.5)

        # 恢复时间
        ax2 = axes[1]
        ax2.barh(data.scenarios, data.recovery_times, color=self.COLORS["info"])
        ax2.set_xlabel("恢复时间 (天)")
        ax2.set_title("恢复时间")

        fig.suptitle("压力测试结果", fontsize=14, fontweight="bold")
        plt.tight_layout()

        return self._figure_to_bytes(fig)

    def generate_trading_cost_analysis(
        self,
        data: TradingCostData,
    ) -> bytes:
        """22. 交易成本分析图

        白皮书依据: 第五章 5.4.3 图表22

        展示交易成本的构成。

        Args:
            data: 交易成本数据

        Returns:
            bytes: PNG图像数据
        """
        if not MATPLOTLIB_AVAILABLE:
            return self._generate_placeholder_chart("交易成本分析图")

        fig, axes = plt.subplots(1, 2, figsize=(12, 5))

        # 成本金额柱状图
        ax1 = axes[0]
        ax1.bar(data.cost_types, data.amounts, color=self.COLORS["primary"])
        ax1.set_ylabel("金额")
        ax1.set_title("成本金额")
        ax1.tick_params(axis="x", rotation=45)

        # 成本占比饼图
        ax2 = axes[1]
        ax2.pie(
            data.percentages,
            labels=data.cost_types,
            autopct="%1.1f%%",
            colors=plt.cm.Set3.colors,  # pylint: disable=no-member
        )  # pylint: disable=no-member
        ax2.set_title("成本占比")

        fig.suptitle("交易成本分析", fontsize=14, fontweight="bold")
        plt.tight_layout()

        return self._figure_to_bytes(fig)

    def generate_decay_trend(
        self,
        data: DecayData,
    ) -> bytes:
        """23. 策略衰减趋势图

        白皮书依据: 第五章 5.4.3 图表23

        展示策略表现的衰减趋势。

        Args:
            data: 策略衰减数据

        Returns:
            bytes: PNG图像数据
        """
        if not MATPLOTLIB_AVAILABLE:
            return self._generate_placeholder_chart("策略衰减趋势图")

        fig, ax = self._create_figure()

        ax.plot(data.dates, data.performance_values, color=self.COLORS["primary"], linewidth=2, label="实际表现")

        # 添加趋势线
        x_numeric = np.arange(len(data.dates))
        z = np.polyfit(x_numeric, data.performance_values, 1)
        p = np.poly1d(z)
        ax.plot(
            data.dates,
            p(x_numeric),
            color=self.COLORS["danger"],
            linestyle="--",
            label=f"趋势线 (衰减率: {data.decay_rate:.2%})",
        )

        ax.set_xlabel("日期")
        ax.set_ylabel("表现")
        ax.set_title("策略衰减趋势", fontsize=14, fontweight="bold")
        ax.legend()

        return self._figure_to_bytes(fig)

    def generate_position_management_matrix(
        self,
        data: PositionData,
    ) -> bytes:
        """24. 仓位管理矩阵

        白皮书依据: 第五章 5.4.3 图表24

        展示仓位分配和风险贡献。

        Args:
            data: 仓位数据

        Returns:
            bytes: PNG图像数据
        """
        if not MATPLOTLIB_AVAILABLE:
            return self._generate_placeholder_chart("仓位管理矩阵")

        fig, axes = plt.subplots(1, 2, figsize=(14, 6))

        # 仓位权重
        ax1 = axes[0]
        ax1.pie(
            data.weights, labels=data.symbols, autopct="%1.1f%%", colors=plt.cm.Set2.colors  # pylint: disable=no-member
        )  # pylint: disable=no-member
        ax1.set_title("仓位权重")

        # 风险贡献
        ax2 = axes[1]
        ax2.barh(data.symbols, data.risk_contributions, color=self.COLORS["secondary"])
        ax2.set_xlabel("风险贡献 (%)")
        ax2.set_title("风险贡献")

        fig.suptitle("仓位管理矩阵", fontsize=14, fontweight="bold")
        plt.tight_layout()

        return self._figure_to_bytes(fig)

    def generate_fitness_evolution(
        self,
        data: FitnessEvolutionData,
    ) -> bytes:
        """25. 适应度演化图

        白皮书依据: 第五章 5.4.3 图表25

        展示遗传算法的适应度演化过程。

        Args:
            data: 适应度演化数据

        Returns:
            bytes: PNG图像数据
        """
        if not MATPLOTLIB_AVAILABLE:
            return self._generate_placeholder_chart("适应度演化图")

        fig, ax = self._create_figure()

        ax.plot(
            data.generations, data.fitness_values, color=self.COLORS["primary"], linewidth=2, marker="o", markersize=4
        )
        ax.axhline(
            y=data.best_fitness,
            color=self.COLORS["success"],
            linestyle="--",
            label=f"最佳适应度: {data.best_fitness:.4f}",
        )

        ax.fill_between(data.generations, data.fitness_values, alpha=0.3, color=self.COLORS["primary"])

        ax.set_xlabel("代数")
        ax.set_ylabel("适应度")
        ax.set_title("适应度演化", fontsize=14, fontweight="bold")
        ax.legend()

        return self._figure_to_bytes(fig)

    def generate_arena_comparison(
        self,
        data: ArenaComparisonData,
    ) -> bytes:
        """26. Arena表现对比图

        白皮书依据: 第五章 5.4.3 图表26

        对比不同策略在Arena中的表现。

        Args:
            data: Arena对比数据

        Returns:
            bytes: PNG图像数据
        """
        if not MATPLOTLIB_AVAILABLE:
            return self._generate_placeholder_chart("Arena表现对比图")

        fig, ax = self._create_figure(figsize=(12, 6))

        x = np.arange(len(data.strategies))
        width = 0.25

        bars1 = ax.bar(  # pylint: disable=unused-variable
            x - width, data.reality_scores, width, label="现实轨道", color=self.COLORS["primary"]
        )  # pylint: disable=unused-variable
        bars2 = ax.bar(  # pylint: disable=unused-variable
            x, data.hell_scores, width, label="地狱轨道", color=self.COLORS["danger"]
        )  # pylint: disable=unused-variable
        bars3 = ax.bar(  # pylint: disable=unused-variable
            x + width, data.cross_market_scores, width, label="跨市场", color=self.COLORS["success"]
        )  # pylint: disable=unused-variable

        ax.set_xlabel("策略")
        ax.set_ylabel("得分")
        ax.set_title("Arena表现对比", fontsize=14, fontweight="bold")
        ax.set_xticks(x)
        ax.set_xticklabels(data.strategies, rotation=45, ha="right")
        ax.legend()
        ax.set_ylim(0, 1)

        return self._figure_to_bytes(fig)

    def generate_factor_evolution(
        self,
        data: FactorEvolutionData,
    ) -> bytes:
        """27. 因子演化图

        白皮书依据: 第五章 5.4.3 图表27

        展示因子的IC和IR演化。

        Args:
            data: 因子演化数据

        Returns:
            bytes: PNG图像数据
        """
        if not MATPLOTLIB_AVAILABLE:
            return self._generate_placeholder_chart("因子演化图")

        fig, ax = self._create_figure(figsize=(12, 6))

        x = np.arange(len(data.factor_names))
        width = 0.35

        bars1 = ax.bar(  # pylint: disable=unused-variable
            x - width / 2, data.ic_values, width, label="IC", color=self.COLORS["primary"]
        )  # pylint: disable=unused-variable
        bars2 = ax.bar(  # pylint: disable=unused-variable
            x + width / 2, data.ir_values, width, label="IR", color=self.COLORS["secondary"]
        )  # pylint: disable=unused-variable

        ax.set_xlabel("因子")
        ax.set_ylabel("值")
        ax.set_title("因子演化", fontsize=14, fontweight="bold")
        ax.set_xticks(x)
        ax.set_xticklabels(data.factor_names, rotation=45, ha="right")
        ax.legend()
        ax.axhline(y=0, color="black", linestyle="-", linewidth=0.5)

        return self._figure_to_bytes(fig)

    def generate_smart_money_cost_distribution(
        self,
        data: SmartMoneyCostData,
    ) -> bytes:
        """28. 主力成本分布图

        白皮书依据: 第五章 5.4.3 图表28

        展示主力资金的成本分布。

        Args:
            data: 主力成本数据

        Returns:
            bytes: PNG图像数据
        """
        if not MATPLOTLIB_AVAILABLE:
            return self._generate_placeholder_chart("主力成本分布图")

        fig, ax = self._create_figure()

        ax.barh(data.price_levels, data.volume_distribution, color=self.COLORS["primary"], alpha=0.7)
        ax.axhline(
            y=data.avg_cost,
            color=self.COLORS["danger"],
            linestyle="--",
            linewidth=2,
            label=f"平均成本: {data.avg_cost:.2f}",
        )

        ax.set_xlabel("成交量分布")
        ax.set_ylabel("价格")
        ax.set_title("主力成本分布", fontsize=14, fontweight="bold")
        ax.legend()

        return self._figure_to_bytes(fig)

    def generate_stock_scorecard(
        self,
        data: StockScorecardData,
    ) -> bytes:
        """29. 个股综合评分卡

        白皮书依据: 第五章 5.4.3 图表29

        展示个股的综合评分。

        Args:
            data: 个股评分卡数据

        Returns:
            bytes: PNG图像数据
        """
        if not MATPLOTLIB_AVAILABLE:
            return self._generate_placeholder_chart("个股综合评分卡")

        fig, axes = plt.subplots(1, 2, figsize=(14, 6))

        # 雷达图
        ax1 = axes[0]
        ax1 = plt.subplot(121, polar=True)

        angles = np.linspace(0, 2 * np.pi, len(data.dimensions), endpoint=False).tolist()
        scores = data.scores + data.scores[:1]
        angles += angles[:1]

        ax1.fill(angles, scores, color=self.COLORS["primary"], alpha=0.25)
        ax1.plot(angles, scores, color=self.COLORS["primary"], linewidth=2)
        ax1.set_xticks(angles[:-1])
        ax1.set_xticklabels(data.dimensions)
        ax1.set_title(f"{data.symbol} {data.name}")

        # 综合评分
        ax2 = axes[1]
        ax2.text(
            0.5,
            0.5,
            f"{data.overall_score:.1f}",
            fontsize=72,
            ha="center",
            va="center",
            color=(
                self.COLORS["success"]
                if data.overall_score >= 70
                else self.COLORS["warning"] if data.overall_score >= 50 else self.COLORS["danger"]
            ),
        )
        ax2.text(0.5, 0.2, "综合评分", fontsize=16, ha="center", va="center")
        ax2.axis("off")

        fig.suptitle("个股综合评分卡", fontsize=14, fontweight="bold")

        return self._figure_to_bytes(fig)

    # ========================================================================
    # 辅助方法
    # ========================================================================

    def _generate_placeholder_chart(self, title: str) -> bytes:
        """生成占位图表（当matplotlib不可用时）

        Args:
            title: 图表标题

        Returns:
            bytes: 占位图像数据
        """
        # 返回一个简单的占位符
        placeholder = f"[图表占位符: {title}]".encode("utf-8")
        return placeholder

    def get_available_charts(self) -> List[str]:
        """获取可用的图表类型列表

        Returns:
            List[str]: 图表类型名称列表
        """
        return [
            "1. 策略本质雷达图",
            "2. 过拟合风险仪表盘",
            "3. 特征重要性柱状图",
            "4. 相关性热力图",
            "5. 非平稳性分析图",
            "6. 信噪比趋势图",
            "7. 资金容量曲线",
            "8. 市场适配性矩阵",
            "9. 止损效果对比图",
            "10. 滑点分布直方图",
            "11. 交易复盘时间线",
            "12. 市场情绪演化曲线",
            "13. 主力vs散户情绪雷达图",
            "14. 大盘技术面分析图",
            "15. 涨停板分布热力图",
            "16. 行业强弱矩阵",
            "17. 板块轮动图",
            "18. 回撤水下曲线",
            "19. 策略相关性热力图",
            "20. 有效前沿曲线",
            "21. 压力测试结果图",
            "22. 交易成本分析图",
            "23. 策略衰减趋势图",
            "24. 仓位管理矩阵",
            "25. 适应度演化图",
            "26. Arena表现对比图",
            "27. 因子演化图",
            "28. 主力成本分布图",
            "29. 个股综合评分卡",
        ]

    def is_matplotlib_available(self) -> bool:
        """检查matplotlib是否可用"""
        return MATPLOTLIB_AVAILABLE

    def is_plotly_available(self) -> bool:
        """检查plotly是否可用"""
        return PLOTLY_AVAILABLE
