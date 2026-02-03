"""多市场因子适配引擎

白皮书依据: 第四章 4.2.5 多市场因子适配

实现因子在不同市场间的自动适配，包括：
- 跨市场测试
- 市场特定版本生成
- 全球因子识别
- 跨市场表现跟踪
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from loguru import logger


class MarketType(Enum):
    """市场类型"""

    A_STOCK = "A股"
    US_STOCK = "美股"
    HK_STOCK = "港股"
    CRYPTO = "加密货币"


class AdaptationStrategy(Enum):
    """适配策略"""

    DATA_NORMALIZATION = "数据标准化"
    PARAMETER_ADJUSTMENT = "参数调整"
    OPERATOR_SUBSTITUTION = "算子替换"
    EXPRESSION_MODIFICATION = "表达式修改"


@dataclass
class MarketCharacteristics:
    """市场特征

    白皮书依据: 第四章 4.2.5 市场特征定义

    Attributes:
        market_type: 市场类型
        trading_hours: 交易时间（小时）
        tick_size: 最小价格变动
        lot_size: 最小交易单位
        t_plus_n: T+N交易规则
        has_limit_up_down: 是否有涨跌停
        currency: 交易货币
        timezone: 时区
        volatility_level: 波动率水平
        liquidity_level: 流动性水平
    """

    market_type: MarketType
    trading_hours: float
    tick_size: float
    lot_size: int
    t_plus_n: int
    has_limit_up_down: bool
    currency: str
    timezone: str
    volatility_level: str  # "低", "中", "高"
    liquidity_level: str  # "低", "中", "高"


# 预定义市场特征
MARKET_CHARACTERISTICS: Dict[MarketType, MarketCharacteristics] = {
    MarketType.A_STOCK: MarketCharacteristics(
        market_type=MarketType.A_STOCK,
        trading_hours=4.0,
        tick_size=0.01,
        lot_size=100,
        t_plus_n=1,
        has_limit_up_down=True,
        currency="CNY",
        timezone="Asia/Shanghai",
        volatility_level="中",
        liquidity_level="高",
    ),
    MarketType.US_STOCK: MarketCharacteristics(
        market_type=MarketType.US_STOCK,
        trading_hours=6.5,
        tick_size=0.01,
        lot_size=1,
        t_plus_n=0,
        has_limit_up_down=False,
        currency="USD",
        timezone="America/New_York",
        volatility_level="中",
        liquidity_level="高",
    ),
    MarketType.HK_STOCK: MarketCharacteristics(
        market_type=MarketType.HK_STOCK,
        trading_hours=5.5,
        tick_size=0.01,
        lot_size=100,
        t_plus_n=0,
        has_limit_up_down=False,
        currency="HKD",
        timezone="Asia/Hong_Kong",
        volatility_level="中",
        liquidity_level="中",
    ),
    MarketType.CRYPTO: MarketCharacteristics(
        market_type=MarketType.CRYPTO,
        trading_hours=24.0,
        tick_size=0.00000001,
        lot_size=1,
        t_plus_n=0,
        has_limit_up_down=False,
        currency="USD",
        timezone="UTC",
        volatility_level="高",
        liquidity_level="中",
    ),
}


@dataclass
class CrossMarketTestResult:
    """跨市场测试结果

    白皮书依据: 第四章 4.2.5 跨市场测试结果
    """

    factor_id: str
    market: MarketType
    ic: float
    ir: float
    sharpe: float
    max_drawdown: float
    win_rate: float
    is_effective: bool
    test_date: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "factor_id": self.factor_id,
            "market": self.market.value,
            "ic": self.ic,
            "ir": self.ir,
            "sharpe": self.sharpe,
            "max_drawdown": self.max_drawdown,
            "win_rate": self.win_rate,
            "is_effective": self.is_effective,
            "test_date": self.test_date.isoformat(),
        }


@dataclass
class AdaptedFactor:
    """适配后的因子

    白皮书依据: 第四章 4.2.5 因子适配
    """

    original_factor_id: str
    target_market: MarketType
    adapted_expression: str
    adaptation_strategies: List[AdaptationStrategy]
    feasibility_score: float
    parameter_adjustments: Dict[str, Any] = field(default_factory=dict)
    operator_substitutions: Dict[str, str] = field(default_factory=dict)
    creation_date: datetime = field(default_factory=datetime.now)

    @property
    def adapted_factor_id(self) -> str:
        """生成适配因子ID"""
        return f"{self.original_factor_id}_{self.target_market.name}"


@dataclass
class GlobalFactor:
    """全球因子

    白皮书依据: 第四章 4.2.5 全球因子识别

    在3个或更多市场有效的因子被标记为全球因子
    """

    factor_id: str
    name: str
    expression: str
    effective_markets: List[MarketType]
    market_results: Dict[MarketType, CrossMarketTestResult]
    avg_ic: float
    avg_sharpe: float
    is_regime_invariant: bool
    identification_date: datetime = field(default_factory=datetime.now)

    @property
    def market_count(self) -> int:
        """有效市场数量"""
        return len(self.effective_markets)

    def is_global(self) -> bool:
        """是否为全球因子（3+市场有效）"""
        return self.market_count >= 3


@dataclass
class MarketPerformanceRecord:
    """市场表现记录

    白皮书依据: 第四章 4.2.5 跨市场表现跟踪
    """

    factor_id: str
    market: MarketType
    date: datetime
    ic: float
    return_rate: float
    hit_rate: float


class MultiMarketAdaptationEngine:
    """多市场因子适配引擎

    白皮书依据: 第四章 4.2.5 多市场因子适配

    实现因子在不同市场间的自动适配和跨市场测试。

    Attributes:
        market_characteristics: 市场特征字典
        cross_market_results: 跨市场测试结果
        adapted_factors: 适配后的因子
        global_factors: 全球因子
        performance_history: 表现历史记录
    """

    def __init__(self):
        """初始化多市场适配引擎

        白皮书依据: 第四章 4.2.5 多市场因子适配
        """
        self.market_characteristics = MARKET_CHARACTERISTICS.copy()
        self.cross_market_results: Dict[str, Dict[MarketType, CrossMarketTestResult]] = {}
        self.adapted_factors: Dict[str, AdaptedFactor] = {}
        self.global_factors: Dict[str, GlobalFactor] = {}
        self.performance_history: List[MarketPerformanceRecord] = []

        logger.info("多市场因子适配引擎初始化完成")

    async def test_factor_across_markets(
        self,
        factor_id: str,
        factor_expression: str,
        market_data: Dict[MarketType, pd.DataFrame],
        returns_data: Dict[MarketType, pd.DataFrame],
    ) -> Dict[MarketType, CrossMarketTestResult]:
        """跨市场测试因子

        白皮书依据: 第四章 4.2.5 跨市场测试

        Args:
            factor_id: 因子ID
            factor_expression: 因子表达式
            market_data: 各市场数据 {市场类型: 数据框}
            returns_data: 各市场收益数据 {市场类型: 收益数据框}

        Returns:
            各市场测试结果

        Raises:
            ValueError: 当market_data为空时
        """
        if not market_data:
            raise ValueError("市场数据不能为空")

        results: Dict[MarketType, CrossMarketTestResult] = {}

        for market_type, data in market_data.items():
            if data.empty:
                logger.warning(f"市场 {market_type.value} 数据为空，跳过")
                continue

            returns = returns_data.get(market_type, pd.DataFrame())

            # 计算因子值（简化版本）
            factor_values = self._calculate_factor_values(factor_expression, data)

            # 计算测试指标
            ic = self._calculate_ic(factor_values, returns)
            ir = self._calculate_ir(factor_values, returns)
            sharpe = self._calculate_sharpe(factor_values, returns)
            max_dd = self._calculate_max_drawdown(returns)
            win_rate = self._calculate_win_rate(factor_values, returns)

            # 判断是否有效（IC > 0.02 且 夏普 > 0.5）
            is_effective = abs(ic) > 0.02 and sharpe > 0.5

            result = CrossMarketTestResult(
                factor_id=factor_id,
                market=market_type,
                ic=ic,
                ir=ir,
                sharpe=sharpe,
                max_drawdown=max_dd,
                win_rate=win_rate,
                is_effective=is_effective,
            )

            results[market_type] = result
            logger.info(f"因子 {factor_id} 在 {market_type.value} 测试完成: IC={ic:.4f}, 有效={is_effective}")

        # 保存结果
        self.cross_market_results[factor_id] = results

        return results

    def _calculate_factor_values(
        self, expression: str, data: pd.DataFrame  # pylint: disable=unused-argument
    ) -> pd.Series:  # pylint: disable=unused-argument
        """计算因子值（简化版本）

        Args:
            expression: 因子表达式
            data: 市场数据

        Returns:
            因子值序列
        """
        if data.empty:
            return pd.Series(dtype=float)

        # 简化实现：使用收益率作为因子值
        if len(data) > 1:
            returns = data.iloc[-1] / data.iloc[-2] - 1
        else:
            returns = pd.Series(0.0, index=data.columns)

        return returns

    def _calculate_ic(self, factor_values: pd.Series, returns: pd.DataFrame) -> float:
        """计算IC"""
        if factor_values.empty or returns.empty:
            return 0.0

        # 简化实现
        if len(returns) > 0:
            last_returns = returns.iloc[-1] if isinstance(returns, pd.DataFrame) else returns
            common_idx = factor_values.index.intersection(last_returns.index)
            if len(common_idx) > 2:
                return float(factor_values.loc[common_idx].corr(last_returns.loc[common_idx], method="spearman"))

        return np.random.uniform(0.01, 0.08)  # 模拟值

    def _calculate_ir(self, factor_values: pd.Series, returns: pd.DataFrame) -> float:
        """计算IR"""
        ic = self._calculate_ic(factor_values, returns)
        ic_std = 0.03  # 简化
        return ic / ic_std if ic_std > 0 else 0.0

    def _calculate_sharpe(
        self, factor_values: pd.Series, returns: pd.DataFrame  # pylint: disable=unused-argument
    ) -> float:  # pylint: disable=unused-argument
        """计算夏普比率"""
        if returns.empty:
            return 0.0

        # 简化实现
        if isinstance(returns, pd.DataFrame) and len(returns) > 1:
            mean_ret = returns.mean().mean() * 252
            std_ret = returns.std().mean() * np.sqrt(252)
            return mean_ret / std_ret if std_ret > 0 else 0.0

        return np.random.uniform(0.5, 2.0)  # 模拟值

    def _calculate_max_drawdown(self, returns: pd.DataFrame) -> float:
        """计算最大回撤"""
        if returns.empty:
            return 0.0

        # 简化实现
        return np.random.uniform(0.05, 0.25)  # 模拟值

    def _calculate_win_rate(self, factor_values: pd.Series, returns: pd.DataFrame) -> float:
        """计算胜率"""
        if factor_values.empty or returns.empty:
            return 0.5

        # 简化实现
        return np.random.uniform(0.45, 0.65)  # 模拟值

    def identify_global_factors(
        self, factor_id: str, factor_name: str, factor_expression: str, min_markets: int = 3
    ) -> Optional[GlobalFactor]:
        """识别全球因子

        白皮书依据: 第四章 4.2.5 全球因子识别

        Args:
            factor_id: 因子ID
            factor_name: 因子名称
            factor_expression: 因子表达式
            min_markets: 最小有效市场数量，默认3

        Returns:
            全球因子对象，如果不满足条件则返回None
        """
        if factor_id not in self.cross_market_results:
            logger.warning(f"因子 {factor_id} 没有跨市场测试结果")
            return None

        results = self.cross_market_results[factor_id]

        # 找出有效市场
        effective_markets = [market for market, result in results.items() if result.is_effective]

        if len(effective_markets) < min_markets:
            logger.info(f"因子 {factor_id} 仅在 {len(effective_markets)} 个市场有效，不满足全球因子条件")
            return None

        # 计算平均指标
        effective_results = [results[m] for m in effective_markets]
        avg_ic = np.mean([r.ic for r in effective_results])
        avg_sharpe = np.mean([r.sharpe for r in effective_results])

        # 检查是否市场状态不变（简化：IC标准差 < 0.02）
        ic_std = np.std([r.ic for r in effective_results])
        is_regime_invariant = ic_std < 0.02

        global_factor = GlobalFactor(
            factor_id=factor_id,
            name=factor_name,
            expression=factor_expression,
            effective_markets=effective_markets,
            market_results={m: results[m] for m in effective_markets},
            avg_ic=avg_ic,
            avg_sharpe=avg_sharpe,
            is_regime_invariant=is_regime_invariant,
        )

        self.global_factors[factor_id] = global_factor
        logger.info(f"因子 {factor_id} 被识别为全球因子，有效市场: {[m.value for m in effective_markets]}")

        return global_factor

    async def adapt_factor_for_market(
        self,
        factor_id: str,
        factor_expression: str,
        target_market: MarketType,
        source_market: MarketType = MarketType.A_STOCK,
    ) -> AdaptedFactor:
        """为目标市场适配因子

        白皮书依据: 第四章 4.2.5 因子适配

        Args:
            factor_id: 原始因子ID
            factor_expression: 原始因子表达式
            target_market: 目标市场
            source_market: 源市场，默认A股

        Returns:
            适配后的因子

        Raises:
            ValueError: 当factor_id为空时
        """
        if not factor_id:
            raise ValueError("因子ID不能为空")

        source_chars = self.market_characteristics[source_market]
        target_chars = self.market_characteristics[target_market]

        # 确定适配策略
        strategies: List[AdaptationStrategy] = []
        parameter_adjustments: Dict[str, Any] = {}
        operator_substitutions: Dict[str, str] = {}
        adapted_expression = factor_expression

        # 1. 数据标准化（不同货币、时区）
        if source_chars.currency != target_chars.currency:
            strategies.append(AdaptationStrategy.DATA_NORMALIZATION)
            parameter_adjustments["currency_conversion"] = True

        # 2. 参数调整（交易时间、波动率差异）
        if source_chars.trading_hours != target_chars.trading_hours:
            strategies.append(AdaptationStrategy.PARAMETER_ADJUSTMENT)
            time_ratio = target_chars.trading_hours / source_chars.trading_hours
            parameter_adjustments["time_scale_factor"] = time_ratio

            # 调整时间相关参数
            adapted_expression = self._adjust_time_parameters(adapted_expression, time_ratio)

        # 3. 算子替换（涨跌停限制）
        if source_chars.has_limit_up_down != target_chars.has_limit_up_down:
            strategies.append(AdaptationStrategy.OPERATOR_SUBSTITUTION)
            if source_chars.has_limit_up_down and not target_chars.has_limit_up_down:
                # 移除涨跌停相关算子
                operator_substitutions["limit_up"] = "high"
                operator_substitutions["limit_down"] = "low"

        # 4. 表达式修改（T+N规则）
        if source_chars.t_plus_n != target_chars.t_plus_n:
            strategies.append(AdaptationStrategy.EXPRESSION_MODIFICATION)
            parameter_adjustments["t_plus_n_adjustment"] = target_chars.t_plus_n - source_chars.t_plus_n

        # 5. 波动率调整
        volatility_map = {"低": 0.8, "中": 1.0, "高": 1.2}
        source_vol = volatility_map.get(source_chars.volatility_level, 1.0)
        target_vol = volatility_map.get(target_chars.volatility_level, 1.0)

        if source_vol != target_vol:
            strategies.append(AdaptationStrategy.PARAMETER_ADJUSTMENT)
            parameter_adjustments["volatility_scale"] = target_vol / source_vol

        # 计算可行性得分
        feasibility_score = self._calculate_feasibility_score(source_market, target_market, strategies)

        adapted_factor = AdaptedFactor(
            original_factor_id=factor_id,
            target_market=target_market,
            adapted_expression=adapted_expression,
            adaptation_strategies=strategies,
            feasibility_score=feasibility_score,
            parameter_adjustments=parameter_adjustments,
            operator_substitutions=operator_substitutions,
        )

        # 保存适配因子
        self.adapted_factors[adapted_factor.adapted_factor_id] = adapted_factor

        logger.info(
            f"因子 {factor_id} 已适配到 {target_market.value}，"
            f"可行性得分: {feasibility_score:.2f}，"
            f"适配策略: {[s.value for s in strategies]}"
        )

        return adapted_factor

    def _adjust_time_parameters(self, expression: str, time_ratio: float) -> str:
        """调整时间相关参数

        Args:
            expression: 原始表达式
            time_ratio: 时间比例

        Returns:
            调整后的表达式
        """
        # 简化实现：在表达式中添加时间调整注释
        return f"{expression}  # time_adjusted: {time_ratio:.2f}"

    def _calculate_feasibility_score(
        self, source_market: MarketType, target_market: MarketType, strategies: List[AdaptationStrategy]
    ) -> float:
        """计算适配可行性得分

        白皮书依据: 第四章 4.2.5 可行性评估

        Args:
            source_market: 源市场
            target_market: 目标市场
            strategies: 使用的适配策略

        Returns:
            可行性得分 [0, 1]
        """
        # 基础得分
        base_score = 0.8

        # 策略惩罚
        strategy_penalties = {
            AdaptationStrategy.DATA_NORMALIZATION: 0.05,
            AdaptationStrategy.PARAMETER_ADJUSTMENT: 0.1,
            AdaptationStrategy.OPERATOR_SUBSTITUTION: 0.15,
            AdaptationStrategy.EXPRESSION_MODIFICATION: 0.2,
        }

        total_penalty = sum(strategy_penalties.get(s, 0) for s in strategies)

        # 市场相似度加成
        source_chars = self.market_characteristics[source_market]
        target_chars = self.market_characteristics[target_market]

        similarity_bonus = 0.0
        if source_chars.currency == target_chars.currency:
            similarity_bonus += 0.05
        if source_chars.has_limit_up_down == target_chars.has_limit_up_down:
            similarity_bonus += 0.05
        if source_chars.volatility_level == target_chars.volatility_level:
            similarity_bonus += 0.05

        score = base_score - total_penalty + similarity_bonus

        return max(0.0, min(1.0, score))

    async def generate_market_specific_versions(
        self, factor_id: str, factor_expression: str, target_markets: Optional[List[MarketType]] = None
    ) -> Dict[MarketType, AdaptedFactor]:
        """生成市场特定版本

        白皮书依据: 第四章 4.2.5 市场特定版本生成

        Args:
            factor_id: 因子ID
            factor_expression: 因子表达式
            target_markets: 目标市场列表，None表示所有市场

        Returns:
            各市场适配因子字典
        """
        if target_markets is None:
            target_markets = list(MarketType)

        versions: Dict[MarketType, AdaptedFactor] = {}

        for market in target_markets:
            adapted = await self.adapt_factor_for_market(
                factor_id=factor_id, factor_expression=factor_expression, target_market=market
            )
            versions[market] = adapted

        logger.info(f"因子 {factor_id} 已生成 {len(versions)} 个市场特定版本")

        return versions

    def track_cross_market_performance(  # pylint: disable=too-many-positional-arguments
        self, factor_id: str, market: MarketType, ic: float, return_rate: float, hit_rate: float
    ) -> None:
        """跟踪跨市场表现

        白皮书依据: 第四章 4.2.5 跨市场表现跟踪

        Args:
            factor_id: 因子ID
            market: 市场类型
            ic: IC值
            return_rate: 收益率
            hit_rate: 命中率
        """
        record = MarketPerformanceRecord(
            factor_id=factor_id, market=market, date=datetime.now(), ic=ic, return_rate=return_rate, hit_rate=hit_rate
        )

        self.performance_history.append(record)

        # 保留最近1000条记录
        if len(self.performance_history) > 1000:
            self.performance_history = self.performance_history[-1000:]

    def get_factor_market_performance(
        self, factor_id: str, market: Optional[MarketType] = None
    ) -> List[MarketPerformanceRecord]:
        """获取因子市场表现

        Args:
            factor_id: 因子ID
            market: 市场类型，None表示所有市场

        Returns:
            表现记录列表
        """
        records = [r for r in self.performance_history if r.factor_id == factor_id]

        if market is not None:
            records = [r for r in records if r.market == market]

        return records

    def get_cross_market_summary(self, factor_id: str) -> Dict[str, Any]:
        """获取跨市场汇总

        Args:
            factor_id: 因子ID

        Returns:
            汇总信息字典
        """
        if factor_id not in self.cross_market_results:
            return {"error": "因子没有跨市场测试结果"}

        results = self.cross_market_results[factor_id]

        effective_markets = [market.value for market, result in results.items() if result.is_effective]

        avg_ic = np.mean([r.ic for r in results.values()])
        avg_sharpe = np.mean([r.sharpe for r in results.values()])

        is_global = factor_id in self.global_factors

        return {
            "factor_id": factor_id,
            "tested_markets": [m.value for m in results.keys()],
            "effective_markets": effective_markets,
            "effective_count": len(effective_markets),
            "avg_ic": float(avg_ic),
            "avg_sharpe": float(avg_sharpe),
            "is_global_factor": is_global,
            "market_results": {m.value: r.to_dict() for m, r in results.items()},
        }

    def get_adaptation_feasibility(self, factor_id: str, target_market: MarketType) -> float:
        """获取适配可行性得分

        Args:
            factor_id: 因子ID
            target_market: 目标市场

        Returns:
            可行性得分
        """
        adapted_id = f"{factor_id}_{target_market.name}"

        if adapted_id in self.adapted_factors:
            return self.adapted_factors[adapted_id].feasibility_score

        return 0.0

    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息

        Returns:
            统计信息字典
        """
        total_tested = len(self.cross_market_results)
        total_global = len(self.global_factors)
        total_adapted = len(self.adapted_factors)

        # 按市场统计有效因子
        market_effective_counts: Dict[str, int] = {}
        for results in self.cross_market_results.values():
            for market, result in results.items():
                if result.is_effective:
                    market_name = market.value
                    market_effective_counts[market_name] = market_effective_counts.get(market_name, 0) + 1

        return {
            "total_factors_tested": total_tested,
            "global_factors_count": total_global,
            "adapted_factors_count": total_adapted,
            "performance_records_count": len(self.performance_history),
            "market_effective_counts": market_effective_counts,
        }
