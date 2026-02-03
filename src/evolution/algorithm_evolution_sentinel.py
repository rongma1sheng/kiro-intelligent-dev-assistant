"""Algorithm Evolution Sentinel

白皮书依据: 第十一章 11.2 算法进化哨兵

This module re-exports the AlgoEvolutionSentinel implementation from Chapter 2
for use in Chapter 11. The implementation is located in:
src/brain/algo_evolution/algo_evolution_sentinel.py

The sentinel monitors frontier algorithms from arXiv, conferences, and GitHub,
translates them to executable code using LLM, validates in Docker sandbox,
and integrates validated algorithms with safety checks.
"""

from src.brain.algo_evolution.algo_evolution_sentinel import AlgoEvolutionSentinel as AlgorithmEvolutionSentinel
from src.brain.algo_evolution.algo_evolution_sentinel import (
    Algorithm,
    Paper,
)

__all__ = ["AlgorithmEvolutionSentinel", "Paper", "Algorithm"]
