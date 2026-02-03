"""Factor-to-Strategy Converter

白皮书依据: 第四章 4.2.2 因子组合策略生成与斯巴达考核
"""

import uuid
from typing import Dict, List, Optional

import pandas as pd
from loguru import logger

from src.evolution.arena.data_models import FactorTestResult
from src.evolution.converter.correlation_analyzer import CorrelationAnalyzer
from src.evolution.converter.data_models import (
    FactorCharacteristics,
    GeneratedStrategy,
    StrategyTemplate,
    StrategyType,
)
from src.evolution.converter.parameter_optimizer import ParameterOptimizer
from src.infra.event_bus import EventBus, EventType


class FactorToStrategyConverter:
    """Converts Arena-validated factors into tradeable strategies

    白皮书依据: 第四章 4.2.2 因子组合策略生成与斯巴达考核

    This class generates various types of strategies from factors that have
    passed Arena testing:
    1. Pure factor strategies (single factor)
    2. Multi-factor combination strategies
    3. Market neutral strategies
    4. Dynamic weight strategies

    Attributes:
        correlation_analyzer: Analyzer for factor correlations
        parameter_optimizer: Optimizer for strategy parameters
        event_bus: Event bus for publishing events
        strategy_templates: Dictionary of strategy templates by type
    """

    def __init__(self, event_bus: Optional[EventBus] = None, correlation_threshold: float = 0.7):
        """Initialize factor-to-strategy converter

        Args:
            event_bus: Event bus for publishing events (optional)
            correlation_threshold: Threshold for high correlation (default 0.7)
        """
        self.correlation_analyzer = CorrelationAnalyzer(correlation_threshold=correlation_threshold)
        self.parameter_optimizer = ParameterOptimizer()
        self.event_bus = event_bus

        # Initialize strategy templates
        self.strategy_templates = self._initialize_templates()

        logger.info(f"Initialized FactorToStrategyConverter with " f"correlation_threshold={correlation_threshold}")

    def _initialize_templates(self) -> Dict[StrategyType, StrategyTemplate]:
        """Initialize strategy code templates

        白皮书依据: 第四章 4.2.2 策略模板

        Returns:
            Dictionary mapping strategy type to template
        """
        templates = {}

        # Pure factor strategy template
        templates[StrategyType.PURE_FACTOR] = StrategyTemplate(
            strategy_type=StrategyType.PURE_FACTOR,
            required_factors=1,
            description="Pure factor strategy using single validated factor",
            template_code="""
class {strategy_class_name}:
    '''Pure factor strategy based on {factor_name}
    
    Arena Test Results:
    - Overall Score: {arena_score:.4f}
    - IC: {ic:.4f}
    - IR: {ir:.4f}
    - Hell Track Survival: {hell_survival:.2%}
    - Cross-Market Adaptability: {cross_market:.2%}
    
    Strategy Parameters:
    - Rebalance Frequency: {rebalance_freq} days
    - Position Limit: {position_limit:.2%}
    - Max Positions: {max_positions}
    - Entry Threshold: {entry_threshold:.2f}
    - Exit Threshold: {exit_threshold:.2f}
    - Stop Loss: {stop_loss:.2%}
    - Take Profit: {take_profit:.2%}
    '''
    
    def __init__(self):
        self.factor_id = "{factor_id}"
        self.rebalance_frequency = {rebalance_freq}
        self.position_limit = {position_limit}
        self.max_positions = {max_positions}
        self.entry_threshold = {entry_threshold}
        self.exit_threshold = {exit_threshold}
        self.stop_loss = {stop_loss}
        self.take_profit = {take_profit}
    
    def calculate_factor(self, market_data):
        '''Calculate factor values'''
        # Factor calculation logic
        {factor_calculation}
    
    def generate_signals(self, market_data):
        '''Generate trading signals'''
        factor_values = self.calculate_factor(market_data)
        
        signals = {{}}
        for symbol in factor_values.index:
            factor_score = factor_values[symbol]
            factor_rank = factor_values.rank(pct=True)[symbol]
            
            if factor_rank >= self.entry_threshold:
                signals[symbol] = 'BUY'
            elif factor_rank <= self.exit_threshold:
                signals[symbol] = 'SELL'
            else:
                signals[symbol] = 'HOLD'
        
        return signals
    
    def calculate_positions(self, signals, portfolio_value, current_positions):
        '''Calculate position sizes'''
        positions = {{}}
        buy_signals = [s for s in signals if signals[s] == 'BUY']
        
        if buy_signals:
            num_positions = min(len(buy_signals), self.max_positions)
            position_per_stock = (portfolio_value * self.position_limit) / num_positions
            
            for symbol in buy_signals[:num_positions]:
                positions[symbol] = position_per_stock
        
        return positions
    
    def check_risk_management(self, current_positions, market_data):
        '''Check stop loss and take profit'''
        actions = {{}}
        
        for symbol, position in current_positions.items():
            entry_price = position['entry_price']
            current_price = market_data.loc[symbol, 'close']
            
            pnl_pct = (current_price - entry_price) / entry_price
            
            if pnl_pct <= -self.stop_loss:
                actions[symbol] = 'STOP_LOSS'
            elif pnl_pct >= self.take_profit:
                actions[symbol] = 'TAKE_PROFIT'
        
        return actions
""",
        )

        # Factor combo strategy template
        templates[StrategyType.FACTOR_COMBO] = StrategyTemplate(
            strategy_type=StrategyType.FACTOR_COMBO,
            required_factors=2,
            description="Multi-factor combination strategy",
            template_code="""
class {strategy_class_name}:
    '''Multi-factor combination strategy
    
    Source Factors: {factor_names}
    Factor Weights: {factor_weights}
    
    Average Arena Score: {avg_arena_score:.4f}
    Average IC: {avg_ic:.4f}
    Average Hell Survival: {avg_hell_survival:.2%}
    
    Strategy Parameters:
    - Rebalance Frequency: {rebalance_freq} days
    - Position Limit: {position_limit:.2%}
    - Max Positions: {max_positions}
    '''
    
    def __init__(self):
        self.factor_ids = {factor_ids}
        self.factor_weights = {factor_weights}
        self.rebalance_frequency = {rebalance_freq}
        self.position_limit = {position_limit}
        self.max_positions = {max_positions}
        self.entry_threshold = {entry_threshold}
        self.exit_threshold = {exit_threshold}
        self.stop_loss = {stop_loss}
        self.take_profit = {take_profit}
    
    def calculate_factors(self, market_data):
        '''Calculate all factor values'''
        factor_values = {{}}
        {factor_calculations}
        return factor_values
    
    def calculate_composite_score(self, market_data):
        '''Calculate weighted composite factor score'''
        factor_values = self.calculate_factors(market_data)
        
        composite_score = None
        for factor_id, weight in self.factor_weights.items():
            if composite_score is None:
                composite_score = factor_values[factor_id] * weight
            else:
                composite_score += factor_values[factor_id] * weight
        
        return composite_score
    
    def generate_signals(self, market_data):
        '''Generate trading signals based on composite score'''
        composite_score = self.calculate_composite_score(market_data)
        
        signals = {{}}
        for symbol in composite_score.index:
            score = composite_score[symbol]
            score_rank = composite_score.rank(pct=True)[symbol]
            
            if score_rank >= self.entry_threshold:
                signals[symbol] = 'BUY'
            elif score_rank <= self.exit_threshold:
                signals[symbol] = 'SELL'
            else:
                signals[symbol] = 'HOLD'
        
        return signals
""",
        )

        return templates

    async def generate_pure_factor_strategy(
        self, factor_result: FactorTestResult, factor_characteristics: FactorCharacteristics
    ) -> GeneratedStrategy:
        """Generate pure factor strategy from single factor

        白皮书依据: 第四章 4.2.2 纯因子策略生成

        Args:
            factor_result: Factor Arena test result
            factor_characteristics: Factor characteristics

        Returns:
            Generated strategy

        Raises:
            ValueError: If inputs are invalid
        """
        if not factor_result.passed:
            raise ValueError(f"Factor {factor_result.factor_id} did not pass Arena testing")

        logger.info(f"Generating pure factor strategy for {factor_result.factor_id}")

        # Optimize parameters
        parameters = await self.parameter_optimizer.optimize_parameters(
            factor_characteristics=[factor_characteristics], strategy_type=StrategyType.PURE_FACTOR
        )

        # Generate strategy ID and name
        strategy_id = f"pure_factor_{factor_result.factor_id}_{uuid.uuid4().hex[:8]}"
        strategy_name = f"PureFactor_{factor_result.factor_id}"

        # Get template
        template = self.strategy_templates[StrategyType.PURE_FACTOR]

        # Fill template
        strategy_code = template.template_code.format(
            strategy_class_name=strategy_name.replace("-", "_"),
            factor_name=factor_result.factor_id,
            factor_id=factor_result.factor_id,
            arena_score=factor_result.overall_score,
            ic=factor_characteristics.ic,
            ir=factor_characteristics.ir,
            hell_survival=factor_characteristics.hell_survival_rate,
            cross_market=factor_characteristics.cross_market_adaptability,
            rebalance_freq=parameters.rebalance_frequency,
            position_limit=parameters.position_limit,
            max_positions=parameters.max_positions,
            entry_threshold=parameters.entry_threshold,
            exit_threshold=parameters.exit_threshold,
            stop_loss=parameters.stop_loss,
            take_profit=parameters.take_profit,
            factor_calculation="# Factor calculation implementation",
        )

        # Calculate expected metrics
        expected_sharpe = factor_result.overall_score * 2.0  # Rough estimate
        expected_return = factor_characteristics.ic * 0.5  # Rough estimate
        expected_drawdown = 0.15 * (1.0 - factor_characteristics.hell_survival_rate)

        # Create strategy
        strategy = GeneratedStrategy(
            strategy_id=strategy_id,
            strategy_name=strategy_name,
            strategy_type=StrategyType.PURE_FACTOR,
            source_factors=[factor_result.factor_id],
            strategy_code=strategy_code,
            parameters=parameters,
            expected_sharpe=expected_sharpe,
            expected_return=expected_return,
            expected_drawdown=expected_drawdown,
            arena_metadata={
                "factor_arena_score": factor_result.overall_score,
                "reality_score": factor_result.reality_result.reality_score,
                "hell_score": factor_result.hell_result.hell_score,
                "cross_market_score": factor_result.cross_market_result.cross_market_score,
            },
            status="candidate",
        )

        logger.info(f"Generated pure factor strategy: {strategy_id}, " f"expected_sharpe={expected_sharpe:.2f}")

        # Publish event
        if self.event_bus:
            await self.event_bus.publish(
                EventType.STRATEGY_GENERATED,
                {
                    "strategy_id": strategy_id,
                    "strategy_type": "pure_factor",
                    "source_factors": [factor_result.factor_id],
                    "expected_sharpe": expected_sharpe,
                },
            )

        return strategy

    async def generate_factor_combo_strategy(
        self,
        factor_results: List[FactorTestResult],
        factor_characteristics_list: List[FactorCharacteristics],
        factor_values: Dict[str, pd.Series],
        max_factors: int = 5,
    ) -> Optional[GeneratedStrategy]:
        """Generate multi-factor combination strategy

        白皮书依据: 第四章 4.2.2 多因子组合策略生成

        Args:
            factor_results: List of factor Arena test results
            factor_characteristics_list: List of factor characteristics
            factor_values: Dictionary mapping factor_id to factor value series
            max_factors: Maximum number of factors to combine

        Returns:
            Generated strategy or None if not enough diverse factors

        Raises:
            ValueError: If inputs are invalid
        """
        if len(factor_results) < 2:
            logger.warning("Need at least 2 factors for combination strategy")
            return None

        logger.info(f"Generating factor combo strategy from {len(factor_results)} factors")

        # Calculate correlation matrix
        correlation_matrix = await self.correlation_analyzer.calculate_correlation_matrix(
            factor_results=factor_results, factor_values=factor_values
        )

        # Select diverse factors
        selected_factor_ids = await self.correlation_analyzer.select_diverse_factors(
            factor_results=factor_results, correlation_matrix=correlation_matrix, max_factors=max_factors
        )

        if len(selected_factor_ids) < 2:
            logger.warning("Not enough diverse factors for combination strategy")
            return None

        # 过滤因子结果和特征
        selected_results = [r for r in factor_results if r.factor_id in selected_factor_ids]
        selected_characteristics = [fc for fc in factor_characteristics_list if fc.factor_id in selected_factor_ids]

        # 计算因子权重
        factor_weights = await self.correlation_analyzer.calculate_factor_weights(
            factor_results=selected_results, selected_factor_ids=selected_factor_ids
        )

        # Optimize parameters
        parameters = await self.parameter_optimizer.optimize_parameters(
            factor_characteristics=selected_characteristics, strategy_type=StrategyType.FACTOR_COMBO
        )

        # Generate strategy ID and name
        strategy_id = f"factor_combo_{uuid.uuid4().hex[:8]}"
        strategy_name = f"FactorCombo_{len(selected_factor_ids)}F"

        # Get template
        template = self.strategy_templates[StrategyType.FACTOR_COMBO]

        # Calculate average metrics
        avg_arena_score = sum(r.overall_score for r in selected_results) / len(selected_results)
        avg_ic = sum(fc.ic for fc in selected_characteristics) / len(selected_characteristics)
        avg_hell_survival = sum(fc.hell_survival_rate for fc in selected_characteristics) / len(
            selected_characteristics
        )

        # Fill template
        strategy_code = template.template_code.format(
            strategy_class_name=strategy_name.replace("-", "_"),
            factor_names=", ".join(selected_factor_ids),
            factor_weights=str(factor_weights),
            avg_arena_score=avg_arena_score,
            avg_ic=avg_ic,
            avg_hell_survival=avg_hell_survival,
            factor_ids=selected_factor_ids,
            rebalance_freq=parameters.rebalance_frequency,
            position_limit=parameters.position_limit,
            max_positions=parameters.max_positions,
            entry_threshold=parameters.entry_threshold,
            exit_threshold=parameters.exit_threshold,
            stop_loss=parameters.stop_loss,
            take_profit=parameters.take_profit,
            factor_calculations="# Factor calculations implementation",
        )

        # Calculate expected metrics
        expected_sharpe = avg_arena_score * 2.5  # Combo strategies can have higher Sharpe
        expected_return = avg_ic * 0.6
        expected_drawdown = 0.12 * (1.0 - avg_hell_survival)

        # Create strategy
        strategy = GeneratedStrategy(
            strategy_id=strategy_id,
            strategy_name=strategy_name,
            strategy_type=StrategyType.FACTOR_COMBO,
            source_factors=selected_factor_ids,
            strategy_code=strategy_code,
            parameters=parameters,
            expected_sharpe=expected_sharpe,
            expected_return=expected_return,
            expected_drawdown=expected_drawdown,
            arena_metadata={
                "num_factors": len(selected_factor_ids),
                "factor_weights": factor_weights,
                "avg_arena_score": avg_arena_score,
                "correlation_threshold": self.correlation_analyzer.correlation_threshold,
            },
            status="candidate",
        )

        logger.info(
            f"Generated factor combo strategy: {strategy_id}, "
            f"num_factors={len(selected_factor_ids)}, "
            f"expected_sharpe={expected_sharpe:.2f}"
        )

        # Publish event
        if self.event_bus:
            await self.event_bus.publish(
                EventType.STRATEGY_GENERATED,
                {
                    "strategy_id": strategy_id,
                    "strategy_type": "factor_combo",
                    "source_factors": selected_factor_ids,
                    "num_factors": len(selected_factor_ids),
                    "expected_sharpe": expected_sharpe,
                },
            )

        return strategy

    async def generate_strategies_from_factors(
        self,
        factor_results: List[FactorTestResult],
        factor_characteristics_list: List[FactorCharacteristics],
        factor_values: Dict[str, pd.Series],
    ) -> List[GeneratedStrategy]:
        """Generate all applicable strategies from validated factors

        白皮书依据: 第四章 4.2.2 策略生成流程

        Args:
            factor_results: List of factor Arena test results
            factor_characteristics_list: List of factor characteristics
            factor_values: Dictionary mapping factor_id to factor value series

        Returns:
            List of generated strategies

        Raises:
            ValueError: If inputs are invalid or empty
        """
        if not factor_results:
            raise ValueError("Factor results cannot be empty")

        if not factor_characteristics_list:
            raise ValueError("Factor characteristics cannot be empty")

        if len(factor_results) != len(factor_characteristics_list):
            raise ValueError(
                f"Mismatch: {len(factor_results)} results vs " f"{len(factor_characteristics_list)} characteristics"
            )

        logger.info(f"Generating strategies from {len(factor_results)} validated factors")

        strategies = []

        # Generate pure factor strategies for each factor
        for factor_result, factor_char in zip(factor_results, factor_characteristics_list):
            if factor_result.passed:
                try:
                    pure_strategy = await self.generate_pure_factor_strategy(
                        factor_result=factor_result, factor_characteristics=factor_char
                    )
                    strategies.append(pure_strategy)
                except Exception as e:  # pylint: disable=broad-exception-caught
                    logger.error(f"Failed to generate pure factor strategy for " f"{factor_result.factor_id}: {e}")

        # Generate factor combo strategy if we have multiple factors
        if len(factor_results) >= 2:
            try:
                combo_strategy = await self.generate_factor_combo_strategy(
                    factor_results=factor_results,
                    factor_characteristics_list=factor_characteristics_list,
                    factor_values=factor_values,
                    max_factors=5,
                )
                if combo_strategy:
                    strategies.append(combo_strategy)
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.error(f"Failed to generate factor combo strategy: {e}")

        logger.info(f"Generated {len(strategies)} strategies total")

        return strategies
