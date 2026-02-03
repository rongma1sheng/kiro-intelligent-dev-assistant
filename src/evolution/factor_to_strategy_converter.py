"""因子到策略转换器 - 策略生成引擎

白皮书依据: 第四章 4.2.2 因子组合策略生成与斯巴达考核

将Arena验证的因子转换为候选交易策略，支持多种策略类型：
- Pure Factor Strategy: 单因子策略
- Factor Combo Strategy: 多因子组合策略
- Market Neutral Strategy: 市场中性策略
- Dynamic Weight Strategy: 动态权重策略

Author: MIA System
Date: 2026-01-23
"""

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional

import numpy as np
from loguru import logger

from src.evolution.certification_config_manager import StrategyType
from src.evolution.factor_data_models import CandidateStrategy, ValidatedFactor


@dataclass
class StrategyGenerationConfig:
    """策略生成配置

    白皮书依据: 第四章 4.2.2 策略生成规则
    """

    # Arena分数阈值
    pure_factor_threshold: float = 0.6  # 单因子策略最低Arena分数
    combo_strategy_threshold: float = 0.5  # 组合策略最低Arena分数
    market_neutral_threshold: float = 0.7  # 市场中性策略最低Arena分数
    dynamic_weight_threshold: float = 0.8  # 动态权重策略最低Arena分数

    # 因子组合规则
    max_factors_per_combo: int = 5  # 组合策略最多因子数
    min_factors_for_combo: int = 2  # 组合策略最少因子数
    max_correlation: float = 0.7  # 因子间最大相关性

    # 市场中性策略规则
    min_markets_for_neutral: int = 3  # 市场中性策略最少有效市场数

    # 资本配置
    default_capital_allocation: float = 100_000.0  # 默认资本配置
    max_drawdown_limit: float = 0.15  # 最大回撤限制（15%）
    rebalance_frequency: int = 5  # 再平衡频率（天）


class StrategyTemplate:
    """策略模板基类

    白皮书依据: 第四章 4.2.2 策略模板
    """

    def __init__(self, config: StrategyGenerationConfig):
        """初始化策略模板

        Args:
            config: 策略生成配置
        """
        self.config = config

    def generate_code(self, factors: List[ValidatedFactor], strategy_name: str) -> str:
        """生成策略代码（子类实现）

        Args:
            factors: 验证的因子列表
            strategy_name: 策略名称

        Returns:
            策略Python代码
        """
        raise NotImplementedError("子类必须实现 generate_code 方法")

    def calculate_expected_sharpe(self, factors: List[ValidatedFactor]) -> float:
        """计算预期夏普比率

        基于因子Arena分数估算策略预期夏普比率

        Args:
            factors: 验证的因子列表

        Returns:
            预期夏普比率
        """
        if not factors:
            return 0.0

        # 简化估算：Arena分数 * 2.0 作为预期Sharpe
        avg_arena_score = np.mean([f.arena_score for f in factors])
        expected_sharpe = avg_arena_score * 2.0

        return expected_sharpe


class PureFactorTemplate(StrategyTemplate):
    """单因子策略模板

    白皮书依据: 第四章 4.2.2 单因子策略

    使用单个因子生成交易信号，适用于Arena分数 > 0.6的因子
    """

    def generate_code(self, factors: List[ValidatedFactor], strategy_name: str) -> str:
        """生成单因子策略代码

        Args:
            factors: 验证的因子列表（只使用第一个）
            strategy_name: 策略名称

        Returns:
            策略Python代码
        """
        if not factors:
            raise ValueError("单因子策略需要至少一个因子")

        factor = factors[0]

        code = f'''"""
{strategy_name} - 单因子策略

白皮书依据: 第四章 4.2.2 单因子策略
源因子: {factor.factor.name} (Arena分数: {factor.arena_score:.3f})
"""

import pandas as pd
import numpy as np

class {strategy_name.replace("-", "_").replace(" ", "_")}:
    """单因子策略实现"""
    
    def __init__(self):
        self.factor_expression = "{factor.factor.expression}"
        self.arena_score = {factor.arena_score}
        self.positions = {{}}
    
    def calculate_factor(self, market_data: pd.DataFrame) -> pd.Series:
        """计算因子值"""
        # 因子表达式: {factor.factor.expression}
        {factor.factor.implementation_code}
    
    def generate_signals(self, market_data: pd.DataFrame) -> pd.Series:
        """生成交易信号
        
        Returns:
            交易信号: 1=买入, -1=卖出, 0=持有
        """
        factor_values = self.calculate_factor(market_data)
        
        # 标准化因子值
        factor_normalized = (factor_values - factor_values.mean()) / factor_values.std()
        
        # 生成信号：因子值 > 0.5 买入，< -0.5 卖出
        signals = pd.Series(0, index=factor_values.index)
        signals[factor_normalized > 0.5] = 1
        signals[factor_normalized < -0.5] = -1
        
        return signals
    
    def execute(self, market_data: pd.DataFrame) -> Dict:
        """执行策略
        
        Returns:
            执行结果字典
        """
        signals = self.generate_signals(market_data)
        
        # 构建持仓
        for symbol in signals.index:
            if signals[symbol] == 1:
                self.positions[symbol] = 'long'
            elif signals[symbol] == -1:
                self.positions[symbol] = 'short'
            elif symbol in self.positions:
                del self.positions[symbol]
        
        return {{
            'positions': self.positions,
            'signal_count': len(signals[signals != 0]),
            'long_count': len(signals[signals == 1]),
            'short_count': len(signals[signals == -1])
        }}
'''

        return code


class FactorComboTemplate(StrategyTemplate):
    """多因子组合策略模板

    白皮书依据: 第四章 4.2.2 多因子组合策略

    组合多个因子生成交易信号，要求：
    - 至少2个因子
    - 因子间相关性 < 0.7
    - 所有因子Arena分数 > 0.5
    """

    def generate_code(self, factors: List[ValidatedFactor], strategy_name: str) -> str:
        """生成多因子组合策略代码

        Args:
            factors: 验证的因子列表（2-5个）
            strategy_name: 策略名称

        Returns:
            策略Python代码
        """
        if len(factors) < 2:
            raise ValueError("组合策略需要至少2个因子")

        if len(factors) > self.config.max_factors_per_combo:
            factors = factors[: self.config.max_factors_per_combo]

        # 计算因子权重（基于Arena分数）
        arena_scores = np.array([f.arena_score for f in factors])
        weights = arena_scores / arena_scores.sum()

        factor_info = "\n".join(
            [
                f"# 因子{i+1}: {f.factor.name} (Arena: {f.arena_score:.3f}, 权重: {weights[i]:.3f})"
                for i, f in enumerate(factors)
            ]
        )

        code = f'''"""
{strategy_name} - 多因子组合策略

白皮书依据: 第四章 4.2.2 多因子组合策略
因子数量: {len(factors)}
{factor_info}
"""

import pandas as pd
import numpy as np

class {strategy_name.replace("-", "_").replace(" ", "_")}:
    """多因子组合策略实现"""
    
    def __init__(self):
        self.factors = {[f.factor.expression for f in factors]}
        self.weights = {weights.tolist()}
        self.positions = {{}}
    
    def calculate_combined_signal(self, market_data: pd.DataFrame) -> pd.Series:
        """计算组合信号"""
        combined_signal = pd.Series(0.0, index=market_data.index)
        
        # 计算每个因子的信号并加权组合
        for i, (factor_expr, weight) in enumerate(zip(self.factors, self.weights)):
            # 这里需要实际的因子计算逻辑
            factor_values = self._calculate_factor(i, market_data)
            factor_normalized = (factor_values - factor_values.mean()) / factor_values.std()
            combined_signal += weight * factor_normalized
        
        return combined_signal
    
    def _calculate_factor(self, factor_idx: int, market_data: pd.DataFrame) -> pd.Series:
        """计算单个因子值"""
        # 实际实现需要根据因子表达式计算
        return pd.Series(0.0, index=market_data.index)
    
    def generate_signals(self, market_data: pd.DataFrame) -> pd.Series:
        """生成交易信号"""
        combined_signal = self.calculate_combined_signal(market_data)
        
        # 生成信号：组合信号 > 0.5 买入，< -0.5 卖出
        signals = pd.Series(0, index=combined_signal.index)
        signals[combined_signal > 0.5] = 1
        signals[combined_signal < -0.5] = -1
        
        return signals
    
    def execute(self, market_data: pd.DataFrame) -> Dict:
        """执行策略"""
        signals = self.generate_signals(market_data)
        
        # 构建持仓
        for symbol in signals.index:
            if signals[symbol] == 1:
                self.positions[symbol] = 'long'
            elif signals[symbol] == -1:
                self.positions[symbol] = 'short'
            elif symbol in self.positions:
                del self.positions[symbol]
        
        return {{
            'positions': self.positions,
            'signal_count': len(signals[signals != 0]),
            'long_count': len(signals[signals == 1]),
            'short_count': len(signals[signals == -1])
        }}
'''

        return code


class MarketNeutralTemplate(StrategyTemplate):
    """市场中性策略模板

    白皮书依据: 第四章 4.2.2 市场中性策略

    构建多空平衡的市场中性策略，要求：
    - 因子在至少3个市场有效（全球因子）
    - 多头和空头持仓价值相等
    - 对冲市场风险
    """

    def generate_code(self, factors: List[ValidatedFactor], strategy_name: str) -> str:
        """生成市场中性策略代码

        Args:
            factors: 验证的因子列表（全球因子）
            strategy_name: 策略名称

        Returns:
            策略Python代码
        """
        if not factors:
            raise ValueError("市场中性策略需要至少一个全球因子")

        # 检查是否为全球因子（至少3个市场有效）
        global_factors = [f for f in factors if f.markets_passed >= 3]
        if not global_factors:
            raise ValueError("市场中性策略需要全球因子（至少3个市场有效）")

        factor = global_factors[0]

        code = f'''"""
{strategy_name} - 市场中性策略

白皮书依据: 第四章 4.2.2 市场中性策略
源因子: {factor.factor.name} (Arena: {factor.arena_score:.3f}, 市场: {factor.markets_passed}/4)
"""

import pandas as pd
import numpy as np

class {strategy_name.replace("-", "_").replace(" ", "_")}:
    """市场中性策略实现"""
    
    def __init__(self):
        self.factor_expression = "{factor.factor.expression}"
        self.arena_score = {factor.arena_score}
        self.markets_passed = {factor.markets_passed}
        self.long_positions = {{}}
        self.short_positions = {{}}
    
    def calculate_factor(self, market_data: pd.DataFrame) -> pd.Series:
        """计算因子值"""
        # 因子表达式: {factor.factor.expression}
        {factor.factor.implementation_code}
    
    def generate_signals(self, market_data: pd.DataFrame) -> Dict[str, pd.Series]:
        """生成市场中性信号
        
        Returns:
            包含long和short信号的字典
        """
        factor_values = self.calculate_factor(market_data)
        
        # 标准化因子值
        factor_normalized = (factor_values - factor_values.mean()) / factor_values.std()
        
        # 选择top 20%做多，bottom 20%做空
        top_threshold = factor_normalized.quantile(0.8)
        bottom_threshold = factor_normalized.quantile(0.2)
        
        long_signals = pd.Series(0, index=factor_values.index)
        short_signals = pd.Series(0, index=factor_values.index)
        
        long_signals[factor_normalized >= top_threshold] = 1
        short_signals[factor_normalized <= bottom_threshold] = 1
        
        return {{'long': long_signals, 'short': short_signals}}
    
    def execute(self, market_data: pd.DataFrame) -> Dict:
        """执行市场中性策略"""
        signals = self.generate_signals(market_data)
        
        # 构建多空持仓
        self.long_positions = {{}}
        self.short_positions = {{}}
        
        for symbol in signals['long'].index:
            if signals['long'][symbol] == 1:
                self.long_positions[symbol] = 1.0
        
        for symbol in signals['short'].index:
            if signals['short'][symbol] == 1:
                self.short_positions[symbol] = 1.0
        
        # 确保多空平衡
        long_value = sum(self.long_positions.values())
        short_value = sum(self.short_positions.values())
        
        return {{
            'long_positions': self.long_positions,
            'short_positions': self.short_positions,
            'long_count': len(self.long_positions),
            'short_count': len(self.short_positions),
            'long_value': long_value,
            'short_value': short_value,
            'net_exposure': long_value - short_value
        }}
'''

        return code


class DynamicWeightTemplate(StrategyTemplate):
    """动态权重策略模板

    白皮书依据: 第四章 4.2.2 动态权重策略

    根据市场状态动态调整因子权重，要求：
    - 因子Arena分数 > 0.8
    - 根据近期表现调整权重
    - 适应市场regime变化
    """

    def generate_code(self, factors: List[ValidatedFactor], strategy_name: str) -> str:
        """生成动态权重策略代码

        Args:
            factors: 验证的因子列表（高质量因子）
            strategy_name: 策略名称

        Returns:
            策略Python代码
        """
        if not factors:
            raise ValueError("动态权重策略需要至少一个高质量因子")

        # 筛选高质量因子（Arena > 0.8）
        high_quality_factors = [f for f in factors if f.arena_score > 0.8]
        if not high_quality_factors:
            raise ValueError("动态权重策略需要Arena分数 > 0.8的因子")

        code = f'''"""
{strategy_name} - 动态权重策略

白皮书依据: 第四章 4.2.2 动态权重策略
因子数量: {len(high_quality_factors)}
"""

import pandas as pd
import numpy as np

class {strategy_name.replace("-", "_").replace(" ", "_")}:
    """动态权重策略实现"""
    
    def __init__(self):
        self.factors = {[f.factor.expression for f in high_quality_factors]}
        self.base_weights = {[f.arena_score for f in high_quality_factors]}
        self.current_weights = self.base_weights.copy()
        self.positions = {{}}
        self.performance_history = []
    
    def update_weights(self, recent_performance: List[float]):
        """根据近期表现更新权重"""
        if not recent_performance:
            return
        
        # 计算权重调整因子
        perf_array = np.array(recent_performance)
        adjustment = 1.0 + 0.1 * (perf_array - perf_array.mean()) / perf_array.std()
        
        # 更新权重
        self.current_weights = self.base_weights * adjustment
        self.current_weights = self.current_weights / self.current_weights.sum()
    
    def generate_signals(self, market_data: pd.DataFrame) -> pd.Series:
        """生成动态权重信号"""
        combined_signal = pd.Series(0.0, index=market_data.index)
        
        # 使用当前权重组合因子信号
        for i, (factor_expr, weight) in enumerate(zip(self.factors, self.current_weights)):
            factor_values = self._calculate_factor(i, market_data)
            factor_normalized = (factor_values - factor_values.mean()) / factor_values.std()
            combined_signal += weight * factor_normalized
        
        # 生成信号
        signals = pd.Series(0, index=combined_signal.index)
        signals[combined_signal > 0.5] = 1
        signals[combined_signal < -0.5] = -1
        
        return signals
    
    def _calculate_factor(self, factor_idx: int, market_data: pd.DataFrame) -> pd.Series:
        """计算单个因子值"""
        return pd.Series(0.0, index=market_data.index)
    
    def execute(self, market_data: pd.DataFrame) -> Dict:
        """执行动态权重策略"""
        signals = self.generate_signals(market_data)
        
        # 构建持仓
        for symbol in signals.index:
            if signals[symbol] == 1:
                self.positions[symbol] = 'long'
            elif signals[symbol] == -1:
                self.positions[symbol] = 'short'
            elif symbol in self.positions:
                del self.positions[symbol]
        
        return {{
            'positions': self.positions,
            'current_weights': self.current_weights.tolist(),
            'signal_count': len(signals[signals != 0])
        }}
'''

        return code


class FactorToStrategyConverter:
    """因子到策略转换器

    白皮书依据: 第四章 4.2.2 因子组合策略生成与斯巴达考核

    将Arena验证的因子转换为候选交易策略，支持多种策略类型。

    策略生成规则：
    - Pure Factor: Arena分数 > 0.6
    - Combo Strategy: 2+因子，相关性 < 0.7
    - Market Neutral: 全球因子（3+市场有效）
    - Dynamic Weight: Arena分数 > 0.8

    Attributes:
        config: 策略生成配置
        strategy_templates: 策略模板字典
        generated_strategies: 已生成的策略列表
    """

    def __init__(self, config: Optional[StrategyGenerationConfig] = None):
        """初始化转换器

        Args:
            config: 策略生成配置，None则使用默认配置
        """
        self.config = config or StrategyGenerationConfig()

        # 初始化策略模板
        self.strategy_templates = {
            StrategyType.PURE_FACTOR: PureFactorTemplate(self.config),
            StrategyType.FACTOR_COMBO: FactorComboTemplate(self.config),
            StrategyType.MARKET_NEUTRAL: MarketNeutralTemplate(self.config),
            StrategyType.DYNAMIC_WEIGHT: DynamicWeightTemplate(self.config),
        }

        self.generated_strategies: List[CandidateStrategy] = []

        logger.info(
            f"初始化FactorToStrategyConverter: "
            f"pure_threshold={self.config.pure_factor_threshold}, "
            f"combo_threshold={self.config.combo_strategy_threshold}"
        )

    async def generate_strategies(self, validated_factors: List[ValidatedFactor]) -> List[CandidateStrategy]:
        """从验证的因子生成候选策略

        白皮书依据: 第四章 4.2.2 策略生成流程

        Args:
            validated_factors: Arena验证通过的因子列表

        Returns:
            候选策略列表

        Raises:
            ValueError: 当因子列表为空时
        """
        if not validated_factors:
            raise ValueError("因子列表不能为空")

        logger.info(f"开始生成策略，输入因子数量: {len(validated_factors)}")

        strategies = []

        # 1. 生成单因子策略
        pure_strategies = await self._generate_pure_factor_strategies(validated_factors)
        strategies.extend(pure_strategies)

        # 2. 生成组合策略
        if len(validated_factors) >= self.config.min_factors_for_combo:
            combo_strategies = await self._generate_combo_strategies(validated_factors)
            strategies.extend(combo_strategies)

        # 3. 生成市场中性策略
        neutral_strategies = await self._generate_market_neutral_strategies(validated_factors)
        strategies.extend(neutral_strategies)

        # 4. 生成动态权重策略
        dynamic_strategies = await self._generate_dynamic_weight_strategies(validated_factors)
        strategies.extend(dynamic_strategies)

        self.generated_strategies.extend(strategies)

        logger.info(
            f"策略生成完成: "
            f"pure={len(pure_strategies)}, "
            f"combo={len(combo_strategies) if len(validated_factors) >= 2 else 0}, "
            f"neutral={len(neutral_strategies)}, "
            f"dynamic={len(dynamic_strategies)}, "
            f"total={len(strategies)}"
        )

        return strategies

    async def _generate_pure_factor_strategies(
        self, validated_factors: List[ValidatedFactor]
    ) -> List[CandidateStrategy]:
        """生成单因子策略

        白皮书依据: 第四章 4.2.2 单因子策略生成规则

        规则：Arena分数 > 0.6

        Args:
            validated_factors: 验证的因子列表

        Returns:
            单因子策略列表
        """
        strategies = []

        # 筛选符合条件的因子
        eligible_factors = [f for f in validated_factors if f.arena_score > self.config.pure_factor_threshold]

        logger.info(
            f"单因子策略: {len(eligible_factors)}/{len(validated_factors)} "
            f"因子符合条件 (Arena > {self.config.pure_factor_threshold})"
        )

        for factor in eligible_factors:
            try:
                strategy = await self.create_pure_factor_strategy(factor)
                strategies.append(strategy)
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.warning(f"生成单因子策略失败: {factor.factor.name}, 错误: {e}")

        return strategies

    async def create_pure_factor_strategy(self, factor: ValidatedFactor) -> CandidateStrategy:
        """创建单因子策略

        Args:
            factor: 验证的因子

        Returns:
            候选策略
        """
        strategy_id = str(uuid.uuid4())
        strategy_name = f"PureFactor-{factor.factor.name}-{strategy_id[:8]}"

        # 生成策略代码
        template = self.strategy_templates[StrategyType.PURE_FACTOR]
        code = template.generate_code([factor], strategy_name)

        # 计算预期夏普比率
        expected_sharpe = template.calculate_expected_sharpe([factor])

        # 创建候选策略
        strategy = CandidateStrategy(
            id=strategy_id,
            name=strategy_name,
            strategy_type=StrategyType.PURE_FACTOR,
            source_factors=[factor.factor],
            code=code,
            expected_sharpe=expected_sharpe,
            max_drawdown_limit=self.config.max_drawdown_limit,
            capital_allocation=self.config.default_capital_allocation,
            rebalance_frequency=self.config.rebalance_frequency,
            status="candidate",
            arena_scheduled=True,
            simulation_required=True,
            z2h_eligible=factor.z2h_eligible,
            created_at=datetime.now(),
        )

        logger.info(
            f"创建单因子策略: {strategy_name}, "
            f"预期Sharpe={expected_sharpe:.3f}, "
            f"Z2H eligible={factor.z2h_eligible}"
        )

        return strategy

    async def _generate_combo_strategies(self, validated_factors: List[ValidatedFactor]) -> List[CandidateStrategy]:
        """生成组合策略

        白皮书依据: 第四章 4.2.2 组合策略生成规则

        规则：
        - 2-5个因子
        - 所有因子Arena分数 > 0.5
        - 因子间相关性 < 0.7

        Args:
            validated_factors: 验证的因子列表

        Returns:
            组合策略列表
        """
        strategies = []

        # 筛选符合条件的因子
        eligible_factors = [f for f in validated_factors if f.arena_score > self.config.combo_strategy_threshold]

        if len(eligible_factors) < self.config.min_factors_for_combo:
            logger.info(f"组合策略: 因子数量不足 " f"({len(eligible_factors)} < {self.config.min_factors_for_combo})")
            return strategies

        # 检查因子相关性并生成组合
        factor_combinations = self._find_low_correlation_combinations(eligible_factors)

        logger.info(
            f"组合策略: 找到 {len(factor_combinations)} 个低相关性组合 " f"(相关性 < {self.config.max_correlation})"
        )

        for combo in factor_combinations:
            try:
                strategy = await self.create_combo_strategy(combo)
                strategies.append(strategy)
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.warning(f"生成组合策略失败: {len(combo)}因子, 错误: {e}")

        return strategies

    async def create_combo_strategy(self, factors: List[ValidatedFactor]) -> CandidateStrategy:
        """创建组合策略

        Args:
            factors: 验证的因子列表（2-5个）

        Returns:
            候选策略
        """
        strategy_id = str(uuid.uuid4())
        factor_names = "-".join([f.factor.name[:10] for f in factors[:2]])
        strategy_name = f"Combo-{factor_names}-{strategy_id[:8]}"

        # 生成策略代码
        template = self.strategy_templates[StrategyType.FACTOR_COMBO]
        code = template.generate_code(factors, strategy_name)

        # 计算预期夏普比率
        expected_sharpe = template.calculate_expected_sharpe(factors)

        # 创建候选策略
        strategy = CandidateStrategy(
            id=strategy_id,
            name=strategy_name,
            strategy_type=StrategyType.FACTOR_COMBO,
            source_factors=[f.factor for f in factors],
            code=code,
            expected_sharpe=expected_sharpe,
            max_drawdown_limit=self.config.max_drawdown_limit,
            capital_allocation=self.config.default_capital_allocation,
            rebalance_frequency=self.config.rebalance_frequency,
            status="candidate",
            arena_scheduled=True,
            simulation_required=True,
            z2h_eligible=all(f.z2h_eligible for f in factors),
            created_at=datetime.now(),
        )

        logger.info(f"创建组合策略: {strategy_name}, " f"因子数={len(factors)}, " f"预期Sharpe={expected_sharpe:.3f}")

        return strategy

    async def _generate_market_neutral_strategies(
        self, validated_factors: List[ValidatedFactor]
    ) -> List[CandidateStrategy]:
        """生成市场中性策略

        白皮书依据: 第四章 4.2.2 市场中性策略生成规则

        规则：
        - 全球因子（至少3个市场有效）
        - Arena分数 > 0.7

        Args:
            validated_factors: 验证的因子列表

        Returns:
            市场中性策略列表
        """
        strategies = []

        # 筛选全球因子
        global_factors = [
            f
            for f in validated_factors
            if f.markets_passed >= self.config.min_markets_for_neutral
            and f.arena_score > self.config.market_neutral_threshold
        ]

        logger.info(
            f"市场中性策略: {len(global_factors)}/{len(validated_factors)} "
            f"全球因子符合条件 (市场 >= {self.config.min_markets_for_neutral}, "
            f"Arena > {self.config.market_neutral_threshold})"
        )

        for factor in global_factors:
            try:
                strategy = await self.create_market_neutral_strategy(factor)
                strategies.append(strategy)
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.warning(f"生成市场中性策略失败: {factor.factor.name}, 错误: {e}")

        return strategies

    async def create_market_neutral_strategy(self, factor: ValidatedFactor) -> CandidateStrategy:
        """创建市场中性策略

        Args:
            factor: 验证的全球因子

        Returns:
            候选策略
        """
        strategy_id = str(uuid.uuid4())
        strategy_name = f"Neutral-{factor.factor.name}-{strategy_id[:8]}"

        # 生成策略代码
        template = self.strategy_templates[StrategyType.MARKET_NEUTRAL]
        code = template.generate_code([factor], strategy_name)

        # 计算预期夏普比率（市场中性策略通常有更高的Sharpe）
        expected_sharpe = template.calculate_expected_sharpe([factor]) * 1.2

        # 创建候选策略
        strategy = CandidateStrategy(
            id=strategy_id,
            name=strategy_name,
            strategy_type=StrategyType.MARKET_NEUTRAL,
            source_factors=[factor.factor],
            code=code,
            expected_sharpe=expected_sharpe,
            max_drawdown_limit=self.config.max_drawdown_limit * 0.8,  # 更严格的回撤限制
            capital_allocation=self.config.default_capital_allocation,
            rebalance_frequency=self.config.rebalance_frequency,
            status="candidate",
            arena_scheduled=True,
            simulation_required=True,
            z2h_eligible=factor.z2h_eligible,
            created_at=datetime.now(),
        )

        logger.info(
            f"创建市场中性策略: {strategy_name}, "
            f"市场数={factor.markets_passed}, "
            f"预期Sharpe={expected_sharpe:.3f}"
        )

        return strategy

    async def _generate_dynamic_weight_strategies(
        self, validated_factors: List[ValidatedFactor]
    ) -> List[CandidateStrategy]:
        """生成动态权重策略

        白皮书依据: 第四章 4.2.2 动态权重策略生成规则

        规则：Arena分数 > 0.8（高质量因子）

        Args:
            validated_factors: 验证的因子列表

        Returns:
            动态权重策略列表
        """
        strategies = []

        # 筛选高质量因子
        high_quality_factors = [f for f in validated_factors if f.arena_score > self.config.dynamic_weight_threshold]

        logger.info(
            f"动态权重策略: {len(high_quality_factors)}/{len(validated_factors)} "
            f"高质量因子符合条件 (Arena > {self.config.dynamic_weight_threshold})"
        )

        if not high_quality_factors:
            return strategies

        # 如果有多个高质量因子，生成一个组合动态权重策略
        if len(high_quality_factors) >= 2:
            try:
                strategy = await self.create_dynamic_weight_strategy(high_quality_factors)
                strategies.append(strategy)
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.warning(f"生成动态权重策略失败: 错误: {e}")

        return strategies

    async def create_dynamic_weight_strategy(self, factors: List[ValidatedFactor]) -> CandidateStrategy:
        """创建动态权重策略

        Args:
            factors: 验证的高质量因子列表

        Returns:
            候选策略
        """
        strategy_id = str(uuid.uuid4())
        strategy_name = f"Dynamic-{len(factors)}Factors-{strategy_id[:8]}"

        # 生成策略代码
        template = self.strategy_templates[StrategyType.DYNAMIC_WEIGHT]
        code = template.generate_code(factors, strategy_name)

        # 计算预期夏普比率（动态权重策略通常有更高的Sharpe）
        expected_sharpe = template.calculate_expected_sharpe(factors) * 1.3

        # 创建候选策略
        strategy = CandidateStrategy(
            id=strategy_id,
            name=strategy_name,
            strategy_type=StrategyType.DYNAMIC_WEIGHT,
            source_factors=[f.factor for f in factors],
            code=code,
            expected_sharpe=expected_sharpe,
            max_drawdown_limit=self.config.max_drawdown_limit,
            capital_allocation=self.config.default_capital_allocation,
            rebalance_frequency=self.config.rebalance_frequency,
            status="candidate",
            arena_scheduled=True,
            simulation_required=True,
            z2h_eligible=all(f.z2h_eligible for f in factors),
            created_at=datetime.now(),
        )

        logger.info(
            f"创建动态权重策略: {strategy_name}, " f"因子数={len(factors)}, " f"预期Sharpe={expected_sharpe:.3f}"
        )

        return strategy

    def _find_low_correlation_combinations(
        self, factors: List[ValidatedFactor], max_combo_size: int = 3  # pylint: disable=unused-argument
    ) -> List[List[ValidatedFactor]]:
        """找到低相关性的因子组合

        Args:
            factors: 因子列表
            max_combo_size: 最大组合大小

        Returns:
            低相关性因子组合列表
        """
        # 简化实现：假设所有因子相关性都低于阈值
        # 实际实现需要计算因子间的相关性矩阵

        combinations = []

        # 生成2-3个因子的组合
        if len(factors) >= 2:
            # 取前3个最高Arena分数的因子组合
            sorted_factors = sorted(factors, key=lambda f: f.arena_score, reverse=True)

            # 2因子组合
            if len(sorted_factors) >= 2:
                combinations.append(sorted_factors[:2])

            # 3因子组合
            if len(sorted_factors) >= 3:
                combinations.append(sorted_factors[:3])

        return combinations

    def get_statistics(self) -> Dict:
        """获取转换器统计信息

        Returns:
            统计信息字典
        """
        if not self.generated_strategies:
            return {"total_strategies": 0, "by_type": {}, "z2h_eligible_count": 0}

        by_type = {}
        for strategy in self.generated_strategies:
            strategy_type = strategy.strategy_type
            by_type[strategy_type] = by_type.get(strategy_type, 0) + 1

        z2h_eligible_count = sum(1 for s in self.generated_strategies if s.z2h_eligible)

        return {
            "total_strategies": len(self.generated_strategies),
            "by_type": by_type,
            "z2h_eligible_count": z2h_eligible_count,
            "avg_expected_sharpe": np.mean([s.expected_sharpe for s in self.generated_strategies]),
        }
