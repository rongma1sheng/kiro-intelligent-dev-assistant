# pylint: disable=too-many-lines
"""
因子性能监控器 (Factor Performance Monitor)

白皮书依据: 第四章 4.2.1 因子Arena三轨测试系统
白皮书依据: 第四章 4.2.4 因子生命周期管理
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from loguru import logger


class DegradationSeverity(Enum):
    """因子衰减严重程度

    白皮书依据: 第四章 4.2.4 因子生命周期管理 - 衰减处理
    """

    NONE = "none"
    MILD = "mild"
    MODERATE = "moderate"
    SEVERE = "severe"


@dataclass
class PerformanceMetrics:
    """因子性能指标

    白皮书依据: 第四章 4.2.4 因子生命周期管理 - 性能监控

    Attributes:
        factor_id: 因子ID
        timestamp: 计算时间戳
        rolling_ic: 滚动IC字典 {period: ic_value}
        ir: 信息比率
        sharpe_ratio: 夏普比率
        turnover_rate: 换手率
        health_score: 健康评分 [0, 1]
        ic_decay_rate: IC衰减率
    """

    factor_id: str
    timestamp: datetime
    rolling_ic: Dict[int, float] = field(default_factory=dict)
    ir: float = 0.0
    sharpe_ratio: float = 0.0
    turnover_rate: float = 0.0
    health_score: float = 1.0
    ic_decay_rate: float = 0.0


@dataclass
class FactorDecayStatus:
    """因子衰减状态

    白皮书依据: 第四章 4.2.4 因子生命周期管理 - 衰减检测

    Attributes:
        factor_id: 因子ID
        is_decaying: 是否正在衰减
        severity: 衰减严重程度
        health_score: 当前健康评分
        ic_decay_rate: IC衰减率
        recommendation: 处理建议
    """

    factor_id: str
    is_decaying: bool
    severity: DegradationSeverity
    health_score: float
    ic_decay_rate: float
    recommendation: str


@dataclass
class RiskFactor:
    """风险因子（由失效因子转换）

    白皮书依据: 第四章 4.1 因子评估标准 - 反向进化

    Attributes:
        original_factor_id: 原始因子ID
        risk_type: 风险类型
        risk_value: 风险值 [0, 1]
        confidence: 置信度 [0, 1]
        exit_levels: 退出价格水平
        created_at: 创建时间
    """

    original_factor_id: str
    risk_type: str
    risk_value: float
    confidence: float
    exit_levels: Dict[str, float] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)


class FactorPerformanceMonitor:
    """因子性能监控器

    白皮书依据: 第四章 4.2.1 因子Arena - 性能指标计算
    白皮书依据: 第四章 4.2.4 因子生命周期管理

    职责:
    1. 计算IC (信息系数)
    2. 计算IR (信息比率)
    3. 计算夏普比率
    4. 计算最大回撤
    5. 计算胜率
    6. 计算综合评分
    7. 计算滚动IC (1d, 5d, 10d, 20d)
    8. 计算健康评分
    9. 检测因子衰减
    10. 维护因子相关性矩阵
    11. 转换失效因子为风险因子
    """

    # 健康评分阈值
    HEALTH_THRESHOLD_RETIREMENT = 0.3  # 低于此值触发退役
    HEALTH_THRESHOLD_WARNING = 0.5  # 低于此值发出警告

    # IC衰减阈值
    IC_DECAY_WARNING = 0.6  # IC衰减超过60%发出警告

    # 相关性阈值
    CORRELATION_REDUNDANT = 0.9  # 相关性超过0.9视为冗余

    def __init__(self):
        """初始化因子性能监控器

        白皮书依据: MIA编码铁律2 - 禁止简化和占位符
        """
        logger.info("初始化FactorPerformanceMonitor")

        # 因子性能历史记录
        self._performance_history: Dict[str, List[PerformanceMetrics]] = {}

        # 因子相关性矩阵
        self._correlation_matrix: Optional[pd.DataFrame] = None

        # 因子基准IC（用于计算衰减）
        self._baseline_ic: Dict[str, float] = {}

        # 风险因子注册表
        self._risk_factors: Dict[str, RiskFactor] = {}

    def calculate_ic(self, factor_values: pd.Series, returns: pd.Series, method: str = "spearman") -> float:
        """计算信息系数 (IC)

        白皮书依据: 第四章 4.1 因子评估标准 - IC (信息系数)

        Args:
            factor_values: 因子值序列
            returns: 收益率序列
            method: 相关系数方法 ('pearson' 或 'spearman')

        Returns:
            信息系数 [-1, 1]

        Raises:
            ValueError: 当输入数据无效时
        """
        if len(factor_values) != len(returns):
            raise ValueError(f"因子值和收益率长度不一致: {len(factor_values)} vs {len(returns)}")

        if len(factor_values) == 0:
            raise ValueError("因子值序列不能为空")

        if method not in ["pearson", "spearman"]:
            raise ValueError(f"不支持的相关系数方法: {method}")

        # 对齐索引
        common_index = factor_values.index.intersection(returns.index)
        if len(common_index) == 0:
            raise ValueError("因子值和收益率没有共同的索引")

        factor_aligned = factor_values.loc[common_index]
        returns_aligned = returns.loc[common_index]

        # 移除NaN值
        valid_mask = ~(factor_aligned.isna() | returns_aligned.isna())
        factor_clean = factor_aligned[valid_mask]
        returns_clean = returns_aligned[valid_mask]

        if len(factor_clean) < 2:
            logger.warning("有效样本数量不足，返回IC=0")
            return 0.0

        # 计算相关系数
        ic = factor_clean.corr(returns_clean, method=method)

        # 处理NaN情况
        if pd.isna(ic):
            logger.warning("IC计算结果为NaN，返回0")
            return 0.0

        return float(ic)

    def calculate_ir(self, factor_values: pd.Series, returns: pd.Series, method: str = "spearman") -> float:
        """计算信息比率 (IR)

        白皮书依据: 第四章 4.1 因子评估标准 - IR (信息比率)

        IR = IC均值 / IC标准差

        Args:
            factor_values: 因子值序列
            returns: 收益率序列
            method: 相关系数方法

        Returns:
            信息比率

        Raises:
            ValueError: 当输入数据无效时
        """
        if len(factor_values) < 20:
            raise ValueError(f"样本数量不足，至少需要20个样本，当前: {len(factor_values)}")

        # 滚动计算IC
        window_size = 20
        ic_series = []

        for i in range(window_size, len(factor_values) + 1):
            window_factor = factor_values.iloc[i - window_size : i]
            window_returns = returns.iloc[i - window_size : i]

            try:
                ic = self.calculate_ic(window_factor, window_returns, method)
                ic_series.append(ic)
            except ValueError:
                continue

        if len(ic_series) < 2:
            logger.warning("IC序列样本不足，返回IR=0")
            return 0.0

        # 计算IR
        ic_mean = np.mean(ic_series)
        ic_std = np.std(ic_series)

        if ic_std == 0:
            logger.warning("IC标准差为0，返回IR=0")
            return 0.0

        ir = ic_mean / ic_std

        return float(ir)

    def calculate_sharpe_ratio(
        self, returns: pd.Series, risk_free_rate: float = 0.03, periods_per_year: int = 252
    ) -> float:
        """计算夏普比率

        白皮书依据: 第四章 4.1 因子评估标准 - 夏普比率

        Args:
            returns: 收益率序列
            risk_free_rate: 无风险利率 (年化)
            periods_per_year: 每年交易周期数 (默认252个交易日)

        Returns:
            夏普比率

        Raises:
            ValueError: 当输入数据无效时
        """
        if len(returns) == 0:
            raise ValueError("收益率序列不能为空")

        # 移除NaN值
        returns_clean = returns.dropna()

        if len(returns_clean) < 2:
            logger.warning("有效样本数量不足，返回Sharpe=0")
            return 0.0

        # 计算超额收益
        excess_returns = returns_clean - risk_free_rate / periods_per_year

        # 计算夏普比率
        mean_excess = excess_returns.mean()
        std_excess = excess_returns.std()

        if std_excess == 0:
            logger.warning("收益率标准差为0，返回Sharpe=0")
            return 0.0

        sharpe = mean_excess / std_excess * np.sqrt(periods_per_year)

        return float(sharpe)

    def calculate_max_drawdown(self, returns: pd.Series) -> float:
        """计算最大回撤

        白皮书依据: 第四章 4.1 因子评估标准 - 最大回撤

        Args:
            returns: 收益率序列

        Returns:
            最大回撤 (正数，如0.15表示15%回撤)

        Raises:
            ValueError: 当输入数据无效时
        """
        if len(returns) == 0:
            raise ValueError("收益率序列不能为空")

        # 移除NaN值
        returns_clean = returns.dropna()

        if len(returns_clean) == 0:
            logger.warning("没有有效的收益率数据，返回最大回撤=0")
            return 0.0

        # 计算累计收益
        cumulative_returns = (1 + returns_clean).cumprod()

        # 计算历史最高点
        running_max = cumulative_returns.expanding().max()

        # 计算回撤
        drawdown = (cumulative_returns - running_max) / running_max

        # 最大回撤
        max_dd = abs(drawdown.min())

        return float(max_dd)

    def calculate_win_rate(self, factor_values: pd.Series, returns: pd.Series) -> float:
        """计算胜率

        白皮书依据: 第四章 4.1 因子评估标准 - 胜率

        胜率 = 因子值为正且收益为正的比例

        Args:
            factor_values: 因子值序列
            returns: 收益率序列

        Returns:
            胜率 [0, 1]

        Raises:
            ValueError: 当输入数据无效时
        """
        if len(factor_values) != len(returns):
            raise ValueError(f"因子值和收益率长度不一致: {len(factor_values)} vs {len(returns)}")

        # 对齐索引
        common_index = factor_values.index.intersection(returns.index)
        factor_aligned = factor_values.loc[common_index]
        returns_aligned = returns.loc[common_index]

        # 移除NaN值
        valid_mask = ~(factor_aligned.isna() | returns_aligned.isna())
        factor_clean = factor_aligned[valid_mask]
        returns_clean = returns_aligned[valid_mask]

        if len(factor_clean) == 0:
            logger.warning("没有有效样本，返回胜率=0")
            return 0.0

        # 计算胜率
        wins = ((factor_clean > 0) & (returns_clean > 0)).sum()
        total = len(factor_clean)

        win_rate = wins / total

        return float(win_rate)

    def calculate_reality_score(  # pylint: disable=too-many-positional-arguments
        self, ic: float, ir: float, sharpe_ratio: float, max_drawdown: float, win_rate: float
    ) -> float:
        """计算Reality Track综合评分

        白皮书依据: 第四章 4.2.1 因子Arena - Reality Track评分

        评分公式:
        reality_score = (
            abs(IC) * 0.25 +
            abs(IR) * 0.20 +
            max(Sharpe, 0) * 0.20 +
            (1 - max_drawdown) * 0.20 +
            win_rate * 0.15
        )

        Args:
            ic: 信息系数
            ir: 信息比率
            sharpe_ratio: 夏普比率
            max_drawdown: 最大回撤
            win_rate: 胜率

        Returns:
            Reality评分 [0, 1]
        """
        # 归一化各指标
        ic_norm = min(abs(ic) / 0.15, 1.0)  # IC > 0.15视为满分
        ir_norm = min(abs(ir) / 3.0, 1.0)  # IR > 3.0视为满分
        sharpe_norm = min(max(sharpe_ratio, 0) / 2.0, 1.0)  # Sharpe > 2.0视为满分
        dd_norm = max(1 - max_drawdown / 0.3, 0)  # 回撤 < 30%视为满分
        wr_norm = win_rate  # 胜率已经在[0, 1]范围内

        # 加权计算综合评分
        reality_score = ic_norm * 0.25 + ir_norm * 0.20 + sharpe_norm * 0.20 + dd_norm * 0.20 + wr_norm * 0.15

        return float(np.clip(reality_score, 0, 1))

    def calculate_hell_score(self, survival_rate: float, scenario_performances: Dict[str, float]) -> float:
        """计算Hell Track综合评分

        白皮书依据: 第四章 4.2.1 因子Arena - Hell Track评分

        评分公式:
        hell_score = survival_rate * 0.5 + avg(scenario_performances) * 0.5

        Args:
            survival_rate: 存活率 [0, 1]
            scenario_performances: 各场景表现 {scenario: score}

        Returns:
            Hell评分 [0, 1]
        """
        if not 0 <= survival_rate <= 1:
            raise ValueError(f"存活率必须在[0, 1]范围内，当前值: {survival_rate}")

        if not scenario_performances:
            raise ValueError("场景表现不能为空")

        # 计算场景平均表现
        avg_performance = np.mean(list(scenario_performances.values()))

        # 加权计算综合评分
        hell_score = survival_rate * 0.5 + avg_performance * 0.5

        return float(np.clip(hell_score, 0, 1))

    def calculate_cross_market_score(self, market_scores: Dict[str, float]) -> float:
        """计算Cross-Market Track综合评分

        白皮书依据: 第四章 4.2.1 因子Arena - Cross-Market Track评分

        评分公式:
        cross_market_score = avg(market_scores) * 0.6 + min(market_scores) * 0.4

        考虑平均表现和最差市场表现

        Args:
            market_scores: 各市场评分 {market: score}

        Returns:
            Cross-Market评分 [0, 1]
        """
        if not market_scores:
            raise ValueError("市场评分不能为空")

        scores = list(market_scores.values())

        # 计算平均分和最低分
        avg_score = np.mean(scores)
        min_score = np.min(scores)

        # 加权计算综合评分
        cross_market_score = avg_score * 0.6 + min_score * 0.4

        return float(np.clip(cross_market_score, 0, 1))

    def calculate_overall_score(self, reality_score: float, hell_score: float, cross_market_score: float) -> float:
        """计算Arena综合评分

        白皮书依据: 第四章 4.2.1 因子Arena - 综合评分

        评分公式:
        overall_score = (reality_score + hell_score + cross_market_score) / 3

        Args:
            reality_score: Reality Track评分
            hell_score: Hell Track评分
            cross_market_score: Cross-Market Track评分

        Returns:
            综合评分 [0, 1]
        """
        if not 0 <= reality_score <= 1:
            raise ValueError(f"Reality评分必须在[0, 1]范围内，当前值: {reality_score}")
        if not 0 <= hell_score <= 1:
            raise ValueError(f"Hell评分必须在[0, 1]范围内，当前值: {hell_score}")
        if not 0 <= cross_market_score <= 1:
            raise ValueError(f"Cross-Market评分必须在[0, 1]范围内，当前值: {cross_market_score}")

        # 简单平均
        overall_score = (reality_score + hell_score + cross_market_score) / 3

        return float(np.clip(overall_score, 0, 1))

    # ========== Task 15: Real-Time Monitoring Methods ==========

    def calculate_rolling_ic(
        self, factor_values: pd.Series, returns: pd.Series, periods: List[int] = None
    ) -> Dict[int, float]:
        """计算多周期滚动IC

        白皮书依据: 第四章 4.2.4 因子生命周期管理 - 性能监控
        **Validates: Requirements 7.1**

        Args:
            factor_values: 因子值序列
            returns: 收益率序列
            periods: 周期列表，默认 [1, 5, 10, 20]

        Returns:
            各周期IC字典 {period: ic_value}

        Raises:
            ValueError: 当输入数据无效时
        """
        if periods is None:
            periods = [1, 5, 10, 20]

        if len(factor_values) == 0:
            raise ValueError("因子值序列不能为空")

        if len(returns) == 0:
            raise ValueError("收益率序列不能为空")

        rolling_ic = {}

        for period in periods:
            if len(factor_values) < period:
                logger.warning(f"样本数量不足以计算{period}日IC，跳过")
                rolling_ic[period] = 0.0
                continue

            try:
                # 计算滞后收益率
                lagged_returns = returns.shift(-period)

                # 移除NaN
                valid_mask = ~(factor_values.isna() | lagged_returns.isna())
                factor_clean = factor_values[valid_mask]
                returns_clean = lagged_returns[valid_mask]

                if len(factor_clean) < 2:
                    rolling_ic[period] = 0.0
                    continue

                # 计算IC
                ic = factor_clean.corr(returns_clean, method="spearman")
                rolling_ic[period] = float(ic) if not pd.isna(ic) else 0.0

            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.warning(f"计算{period}日IC失败: {e}")
                rolling_ic[period] = 0.0

        return rolling_ic

    def calculate_turnover_rate(self, factor_values: pd.Series, previous_factor_values: pd.Series) -> float:
        """计算因子换手率

        白皮书依据: 第四章 4.2.4 因子生命周期管理 - 换手率监控
        **Validates: Requirements 7.1**

        换手率 = 因子排名变化的股票比例

        Args:
            factor_values: 当前因子值序列
            previous_factor_values: 前期因子值序列

        Returns:
            换手率 [0, 1]

        Raises:
            ValueError: 当输入数据无效时
        """
        if len(factor_values) == 0 or len(previous_factor_values) == 0:
            raise ValueError("因子值序列不能为空")

        # 对齐索引
        common_index = factor_values.index.intersection(previous_factor_values.index)

        if len(common_index) == 0:
            logger.warning("没有共同的索引，返回换手率=1.0")
            return 1.0

        current = factor_values.loc[common_index]
        previous = previous_factor_values.loc[common_index]

        # 计算排名
        current_rank = current.rank(pct=True)
        previous_rank = previous.rank(pct=True)

        # 计算排名变化
        rank_change = (current_rank - previous_rank).abs()

        # 换手率 = 平均排名变化 * 2 (归一化到[0, 1])
        turnover = float(rank_change.mean() * 2)

        return float(np.clip(turnover, 0, 1))

    def calculate_health_score(  # pylint: disable=too-many-positional-arguments
        self,
        factor_id: str,  # pylint: disable=unused-argument
        rolling_ic: Dict[int, float],
        ir: float,
        sharpe_ratio: float,
        turnover_rate: float,  # pylint: disable=unused-argument
    ) -> float:
        """计算因子健康评分

        白皮书依据: 第四章 4.2.4 因子生命周期管理 - 健康评分
        **Validates: Requirements 7.2**

        健康评分综合考虑:
        - IC稳定性 (40%)
        - IR表现 (25%)
        - 夏普比率 (20%)
        - 换手率合理性 (15%)

        Args:
            factor_id: 因子ID
            rolling_ic: 滚动IC字典
            ir: 信息比率
            sharpe_ratio: 夏普比率
            turnover_rate: 换手率

        Returns:
            健康评分 [0, 1]
        """
        # 1. IC稳定性评分 (40%)
        ic_values = list(rolling_ic.values())
        if ic_values:
            avg_ic = np.mean([abs(ic) for ic in ic_values])
            ic_std = np.std(ic_values) if len(ic_values) > 1 else 0

            # IC均值评分
            ic_mean_score = min(avg_ic / 0.1, 1.0)  # IC > 0.1视为满分

            # IC稳定性评分 (标准差越小越好)
            ic_stability_score = max(1 - ic_std / 0.1, 0)

            ic_score = ic_mean_score * 0.6 + ic_stability_score * 0.4
        else:
            ic_score = 0.0

        # 2. IR评分 (25%)
        ir_score = min(abs(ir) / 2.0, 1.0)  # IR > 2.0视为满分

        # 3. 夏普比率评分 (20%)
        sharpe_score = min(max(sharpe_ratio, 0) / 1.5, 1.0)  # Sharpe > 1.5视为满分

        # 4. 换手率合理性评分 (15%)
        # 换手率在0.1-0.5之间最佳
        if 0.1 <= turnover_rate <= 0.5:
            turnover_score = 1.0
        elif turnover_rate < 0.1:
            turnover_score = turnover_rate / 0.1
        else:
            turnover_score = max(1 - (turnover_rate - 0.5) / 0.5, 0)

        # 综合健康评分
        health_score = ic_score * 0.40 + ir_score * 0.25 + sharpe_score * 0.20 + turnover_score * 0.15

        return float(np.clip(health_score, 0, 1))

    def calculate_ic_decay_rate(self, factor_id: str, current_ic: float) -> float:
        """计算IC衰减率

        白皮书依据: 第四章 4.2.4 因子生命周期管理 - 衰减检测
        **Validates: Requirements 7.2**

        衰减率 = (baseline_ic - current_ic) / baseline_ic

        Args:
            factor_id: 因子ID
            current_ic: 当前IC值

        Returns:
            IC衰减率 [0, 1]，正值表示衰减
        """
        baseline_ic = self._baseline_ic.get(factor_id)

        if baseline_ic is None or baseline_ic == 0:
            logger.warning(f"因子{factor_id}没有基准IC，返回衰减率=0")
            return 0.0

        # 计算衰减率
        decay_rate = (abs(baseline_ic) - abs(current_ic)) / abs(baseline_ic)

        return float(np.clip(decay_rate, 0, 1))

    def set_baseline_ic(self, factor_id: str, baseline_ic: float) -> None:
        """设置因子基准IC

        白皮书依据: 第四章 4.2.4 因子生命周期管理 - 基准设置

        Args:
            factor_id: 因子ID
            baseline_ic: 基准IC值
        """
        if not factor_id:
            raise ValueError("因子ID不能为空")

        self._baseline_ic[factor_id] = baseline_ic
        logger.info(f"设置因子{factor_id}基准IC: {baseline_ic:.4f}")

    def detect_degradation(self, factor_id: str, health_score: float, ic_decay_rate: float) -> FactorDecayStatus:
        """检测因子衰减

        白皮书依据: 第四章 4.2.4 因子生命周期管理 - 衰减检测
        **Validates: Requirements 7.2**

        衰减判定标准:
        - 健康评分 < 0.3: 严重衰减，触发退役
        - 健康评分 < 0.5 或 IC衰减 > 60%: 中度衰减
        - 健康评分 < 0.7: 轻微衰减

        Args:
            factor_id: 因子ID
            health_score: 健康评分
            ic_decay_rate: IC衰减率

        Returns:
            因子衰减状态
        """
        if not 0 <= health_score <= 1:
            raise ValueError(f"健康评分必须在[0, 1]范围内，当前值: {health_score}")

        if not 0 <= ic_decay_rate <= 1:
            raise ValueError(f"IC衰减率必须在[0, 1]范围内，当前值: {ic_decay_rate}")

        # 判定衰减严重程度
        if health_score < self.HEALTH_THRESHOLD_RETIREMENT:
            severity = DegradationSeverity.SEVERE
            is_decaying = True
            recommendation = "立即退役，转换为风险因子"
        elif health_score < self.HEALTH_THRESHOLD_WARNING or ic_decay_rate > self.IC_DECAY_WARNING:
            severity = DegradationSeverity.MODERATE
            is_decaying = True
            recommendation = "暂停使用，重新进行Arena测试"
        elif health_score < 0.7:
            severity = DegradationSeverity.MILD
            is_decaying = True
            recommendation = "降低权重30%，持续监控"
        else:
            severity = DegradationSeverity.NONE
            is_decaying = False
            recommendation = "状态良好，继续使用"

        return FactorDecayStatus(
            factor_id=factor_id,
            is_decaying=is_decaying,
            severity=severity,
            health_score=health_score,
            ic_decay_rate=ic_decay_rate,
            recommendation=recommendation,
        )

    async def monitor_factor(
        self,
        factor_id: str,
        factor_values: pd.Series,
        returns: pd.Series,
        previous_factor_values: Optional[pd.Series] = None,
    ) -> PerformanceMetrics:
        """监控因子实时性能

        白皮书依据: 第四章 4.2.4 因子生命周期管理 - 实时监控
        **Validates: Requirements 7.1**

        Args:
            factor_id: 因子ID
            factor_values: 因子值序列
            returns: 收益率序列
            previous_factor_values: 前期因子值序列（用于计算换手率）

        Returns:
            性能指标
        """
        # 计算滚动IC
        rolling_ic = self.calculate_rolling_ic(factor_values, returns)

        # 计算IR
        try:
            ir = self.calculate_ir(factor_values, returns)
        except ValueError:
            ir = 0.0

        # 计算夏普比率
        try:
            sharpe_ratio = self.calculate_sharpe_ratio(returns)
        except ValueError:
            sharpe_ratio = 0.0

        # 计算换手率
        if previous_factor_values is not None:
            try:
                turnover_rate = self.calculate_turnover_rate(factor_values, previous_factor_values)
            except ValueError:
                turnover_rate = 0.5
        else:
            turnover_rate = 0.5  # 默认中等换手率

        # 计算健康评分
        health_score = self.calculate_health_score(factor_id, rolling_ic, ir, sharpe_ratio, turnover_rate)

        # 计算IC衰减率
        current_ic = rolling_ic.get(5, 0.0)  # 使用5日IC作为当前IC
        ic_decay_rate = self.calculate_ic_decay_rate(factor_id, current_ic)

        # 创建性能指标
        metrics = PerformanceMetrics(
            factor_id=factor_id,
            timestamp=datetime.now(),
            rolling_ic=rolling_ic,
            ir=ir,
            sharpe_ratio=sharpe_ratio,
            turnover_rate=turnover_rate,
            health_score=health_score,
            ic_decay_rate=ic_decay_rate,
        )

        # 记录历史
        if factor_id not in self._performance_history:
            self._performance_history[factor_id] = []
        self._performance_history[factor_id].append(metrics)

        # 限制历史记录长度
        if len(self._performance_history[factor_id]) > 100:
            self._performance_history[factor_id] = self._performance_history[factor_id][-100:]

        logger.debug(
            f"因子{factor_id}性能监控: "
            f"IC_5d={rolling_ic.get(5, 0):.4f}, "
            f"IR={ir:.4f}, "
            f"Sharpe={sharpe_ratio:.4f}, "
            f"Health={health_score:.4f}"
        )

        return metrics

    def update_correlation_matrix(self, factor_values_dict: Dict[str, pd.Series]) -> pd.DataFrame:
        """更新因子相关性矩阵

        白皮书依据: 第四章 4.2.4 因子生命周期管理 - 相关性分析
        **Validates: Requirements 7.3, 7.6**

        Args:
            factor_values_dict: 因子值字典 {factor_id: factor_values}

        Returns:
            相关性矩阵 DataFrame

        Raises:
            ValueError: 当输入数据无效时
        """
        if not factor_values_dict:
            raise ValueError("因子值字典不能为空")

        # 构建因子值DataFrame
        factor_df = pd.DataFrame(factor_values_dict)

        # 计算相关性矩阵
        self._correlation_matrix = factor_df.corr(method="spearman")

        logger.info(f"更新因子相关性矩阵，包含{len(factor_values_dict)}个因子")

        return self._correlation_matrix

    def detect_redundant_factors(self, threshold: float = None) -> List[Tuple[str, str, float]]:
        """检测冗余因子

        白皮书依据: 第四章 4.2.4 因子生命周期管理 - 冗余检测
        **Validates: Requirements 7.3, 7.6**

        Args:
            threshold: 相关性阈值，默认0.9

        Returns:
            冗余因子对列表 [(factor1, factor2, correlation), ...]
        """
        if threshold is None:
            threshold = self.CORRELATION_REDUNDANT

        if self._correlation_matrix is None:
            logger.warning("相关性矩阵未初始化，无法检测冗余因子")
            return []

        redundant_pairs = []
        factors = self._correlation_matrix.columns.tolist()

        for i, factor1 in enumerate(factors):
            for factor2 in factors[i + 1 :]:
                corr = self._correlation_matrix.loc[factor1, factor2]
                if abs(corr) > threshold:
                    redundant_pairs.append((factor1, factor2, float(corr)))
                    logger.warning(f"检测到冗余因子对: {factor1} - {factor2}, " f"相关性: {corr:.4f}")

        return redundant_pairs

    def get_correlation_matrix(self) -> Optional[pd.DataFrame]:
        """获取因子相关性矩阵

        Returns:
            相关性矩阵，如果未初始化则返回None
        """
        return self._correlation_matrix

    async def convert_to_risk_factor(
        self, factor_id: str, factor_values: pd.Series, returns: pd.Series, current_price: float
    ) -> RiskFactor:
        """将失效因子转换为风险因子

        白皮书依据: 第四章 4.1 因子评估标准 - 反向进化
        白皮书依据: 第四章 4.2.4 因子生命周期管理 - 风险转换
        **Validates: Requirements 7.5**

        失效因子的反向信号可以用于风险预警和退出决策

        Args:
            factor_id: 原始因子ID
            factor_values: 因子值序列
            returns: 收益率序列
            current_price: 当前价格

        Returns:
            风险因子
        """
        # 计算反向相关性
        try:
            ic = self.calculate_ic(factor_values, returns)
        except ValueError:
            ic = 0.0

        # 风险值 = 1 - abs(IC)，IC越低风险越高
        risk_value = 1 - abs(ic)

        # 置信度基于样本量
        sample_size = len(factor_values.dropna())
        confidence = min(sample_size / 100, 1.0)

        # 计算退出价格水平
        exit_levels = self._calculate_exit_levels(factor_values, returns, current_price)

        risk_factor = RiskFactor(
            original_factor_id=factor_id,
            risk_type="factor_decay",
            risk_value=float(np.clip(risk_value, 0, 1)),
            confidence=float(np.clip(confidence, 0, 1)),
            exit_levels=exit_levels,
            created_at=datetime.now(),
        )

        # 注册风险因子
        self._risk_factors[factor_id] = risk_factor

        logger.info(
            f"因子{factor_id}转换为风险因子: "
            f"risk_value={risk_factor.risk_value:.4f}, "
            f"confidence={risk_factor.confidence:.4f}"
        )

        return risk_factor

    def _calculate_exit_levels(
        self, factor_values: pd.Series, returns: pd.Series, current_price: float  # pylint: disable=unused-argument
    ) -> Dict[str, float]:
        """计算退出价格水平

        白皮书依据: 第四章 4.1.2 增强非流动性因子挖掘器 - 退出水平

        Args:
            factor_values: 因子值序列
            returns: 收益率序列
            current_price: 当前价格

        Returns:
            退出价格水平字典
        """
        # 计算收益率统计
        returns_clean = returns.dropna()

        if len(returns_clean) < 10:
            # 样本不足，使用默认值
            return {
                "immediate_exit": current_price * 0.95,
                "warning_level": current_price * 0.97,
                "stop_loss": current_price * 0.90,
            }

        # 计算波动率
        volatility = returns_clean.std()

        # 计算退出水平
        exit_levels = {
            "immediate_exit": current_price * (1 - volatility * 1.5),
            "warning_level": current_price * (1 - volatility * 1.0),
            "stop_loss": current_price * (1 - volatility * 2.5),
        }

        return exit_levels

    def get_risk_factor(self, factor_id: str) -> Optional[RiskFactor]:
        """获取风险因子

        Args:
            factor_id: 原始因子ID

        Returns:
            风险因子，如果不存在则返回None
        """
        return self._risk_factors.get(factor_id)

    def get_performance_history(self, factor_id: str) -> List[PerformanceMetrics]:
        """获取因子性能历史

        Args:
            factor_id: 因子ID

        Returns:
            性能指标历史列表
        """
        return self._performance_history.get(factor_id, [])
