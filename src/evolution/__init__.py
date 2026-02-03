"""Evolution module

白皮书依据: 第十一章 11.2 算法进化哨兵
"""

# Re-export from brain.algo_evolution for backward compatibility
from src.brain.algo_evolution.algo_evolution_sentinel import AlgoEvolutionSentinel as AlgorithmEvolutionSentinel
from src.brain.algo_evolution.algo_evolution_sentinel import (
    Algorithm,
    Paper,
)

__all__ = ["AlgorithmEvolutionSentinel", "Paper", "Algorithm"]
