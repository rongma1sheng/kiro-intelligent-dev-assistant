"""Simulation Validation System

白皮书依据: 第四章 4.5 模拟验证系统

This module implements the 1-month simulation validation system for strategies
that have passed Arena testing. It validates strategies using real market data,
realistic transaction costs, and daily performance monitoring.
"""

from src.evolution.simulation.cost_model import CostModel
from src.evolution.simulation.data_models import (
    DailyResult,
    SimulationConfig,
    SimulationResult,
    SimulationState,
    StrategyTier,
)
from src.evolution.simulation.performance_tracker import PerformanceTracker
from src.evolution.simulation.simulation_engine import SimulationEngine
from src.evolution.simulation.simulation_manager import SimulationManager

__all__ = [
    "SimulationConfig",
    "SimulationState",
    "DailyResult",
    "SimulationResult",
    "StrategyTier",
    "SimulationManager",
    "SimulationEngine",
    "CostModel",
    "PerformanceTracker",
]
