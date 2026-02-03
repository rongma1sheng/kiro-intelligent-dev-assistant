"""多目标优化系统

白皮书依据: 第四章 4.1 遗传算法 - 多目标优化
工程目标: Phase 3 升级 - Pareto 前沿优化
"""

from dataclasses import dataclass
from typing import Any, Dict, List

import numpy as np
from loguru import logger


@dataclass
class MultiObjectiveFitness:
    """多目标适应度

    白皮书依据: 第四章 4.1 多目标适应度函数
    Phase 3 升级: fitness = 收益 - λ·复杂度 - μ·不稳定性

    Attributes:
        revenue: 收益指标 (IC, IR, Sharpe 的综合)
        complexity: 复杂度指标 (表达式长度、深度、算子数量)
        instability: 不稳定性指标 (IC 波动、IR 波动)
        weighted_fitness: 加权适应度
        pareto_rank: Pareto 等级 (0 = 最优前沿)
        crowding_distance: 拥挤距离
    """

    revenue: float = 0.0
    complexity: float = 0.0
    instability: float = 0.0
    weighted_fitness: float = 0.0
    pareto_rank: int = -1
    crowding_distance: float = 0.0

    def __post_init__(self):
        """验证适应度值"""
        if not 0 <= self.revenue <= 1:
            logger.warning(f"收益指标超出范围 [0, 1]: {self.revenue}")

        if not 0 <= self.complexity <= 1:
            logger.warning(f"复杂度指标超出范围 [0, 1]: {self.complexity}")

        if not 0 <= self.instability <= 1:
            logger.warning(f"不稳定性指标超出范围 [0, 1]: {self.instability}")


class MultiObjectiveOptimizer:
    """多目标优化器

    白皮书依据: 第四章 4.1 多目标优化
    Phase 3 升级: 使用 Pareto 前沿进行多目标优化

    核心思想:
    - 不是单一适应度，而是多个目标的权衡
    - 使用 Pareto 支配关系进行排序
    - 保持解的多样性（拥挤距离）
    """

    def __init__(self, lambda_complexity: float = 0.3, mu_instability: float = 0.2):
        """初始化多目标优化器

        Args:
            lambda_complexity: 复杂度惩罚系数
            mu_instability: 不稳定性惩罚系数
        """
        self.lambda_complexity = lambda_complexity
        self.mu_instability = mu_instability

        logger.info(f"多目标优化器初始化: " f"λ(complexity)={lambda_complexity}, " f"μ(instability)={mu_instability}")

    def calculate_multi_objective_fitness(  # pylint: disable=too-many-positional-arguments
        self,
        ic: float,
        ir: float,
        sharpe: float,
        expression_length: int,
        expression_depth: int,
        operator_count: int,
        ic_volatility: float,
        ir_volatility: float,
        max_length: int = 200,
        max_depth: int = 5,
    ) -> MultiObjectiveFitness:
        """计算多目标适应度

        白皮书依据: 第四章 4.1 多目标适应度函数

        Args:
            ic: 信息系数
            ir: 信息比率
            sharpe: 夏普比率
            expression_length: 表达式长度
            expression_depth: 表达式深度
            operator_count: 算子数量
            ic_volatility: IC 波动率
            ir_volatility: IR 波动率
            max_length: 最大表达式长度
            max_depth: 最大表达式深度

        Returns:
            MultiObjectiveFitness: 多目标适应度
        """
        # 1. 计算收益指标 (Revenue)
        # 归一化 IC, IR, Sharpe
        ic_norm = max(0, min(1, (abs(ic) - 0.01) / 0.09))
        ir_norm = max(0, min(1, (abs(ir) - 0.1) / 0.9))
        sharpe_norm = max(0, min(1, (abs(sharpe) - 0.5) / 1.5))

        # 收益 = IC (40%) + IR (30%) + Sharpe (30%)
        revenue = 0.4 * ic_norm + 0.3 * ir_norm + 0.3 * sharpe_norm

        # 2. 计算复杂度指标 (Complexity)
        # 长度复杂度
        length_complexity = min(1.0, expression_length / max_length)

        # 深度复杂度
        depth_complexity = min(1.0, expression_depth / max_depth)

        # 算子数量复杂度
        operator_complexity = min(1.0, operator_count / 20)

        # 综合复杂度 = 加权平均
        complexity = 0.4 * length_complexity + 0.3 * depth_complexity + 0.3 * operator_complexity

        # 3. 计算不稳定性指标 (Instability)
        # IC 波动率归一化
        ic_instability = min(1.0, ic_volatility / 0.1)  # IC 波动率 > 0.1 视为不稳定

        # IR 波动率归一化
        ir_instability = min(1.0, ir_volatility / 0.5)  # IR 波动率 > 0.5 视为不稳定

        # 综合不稳定性
        instability = 0.6 * ic_instability + 0.4 * ir_instability

        # 4. 计算加权适应度
        # fitness = revenue - λ·complexity - μ·instability
        weighted_fitness = revenue - self.lambda_complexity * complexity - self.mu_instability * instability

        # 确保适应度在合理范围内
        weighted_fitness = max(-1.0, min(1.0, weighted_fitness))

        return MultiObjectiveFitness(
            revenue=revenue, complexity=complexity, instability=instability, weighted_fitness=weighted_fitness
        )

    def dominates(self, fitness1: MultiObjectiveFitness, fitness2: MultiObjectiveFitness) -> bool:
        """判断 fitness1 是否 Pareto 支配 fitness2

        白皮书依据: 第四章 4.1 Pareto 支配关系

        支配条件:
        - fitness1 在所有目标上都不差于 fitness2
        - fitness1 在至少一个目标上严格优于 fitness2

        目标:
        - 最大化 revenue
        - 最小化 complexity
        - 最小化 instability

        Args:
            fitness1: 适应度1
            fitness2: 适应度2

        Returns:
            bool: fitness1 是否支配 fitness2
        """
        # 转换为最大化问题（复杂度和不稳定性取负）
        obj1 = [fitness1.revenue, -fitness1.complexity, -fitness1.instability]
        obj2 = [fitness2.revenue, -fitness2.complexity, -fitness2.instability]

        # 检查是否在所有目标上都不差于 fitness2
        not_worse = all(o1 >= o2 for o1, o2 in zip(obj1, obj2))

        # 检查是否在至少一个目标上严格优于 fitness2
        strictly_better = any(o1 > o2 for o1, o2 in zip(obj1, obj2))

        return not_worse and strictly_better

    def fast_non_dominated_sort(self, population_fitness: List[MultiObjectiveFitness]) -> List[List[int]]:
        """快速非支配排序

        白皮书依据: 第四章 4.1 Pareto 前沿计算
        算法: NSGA-II 的快速非支配排序

        Args:
            population_fitness: 种群适应度列表

        Returns:
            List[List[int]]: Pareto 前沿列表，每个前沿包含个体索引
        """
        n = len(population_fitness)

        # 初始化
        domination_count = [0] * n  # 被支配次数
        dominated_solutions = [[] for _ in range(n)]  # 支配的解集合
        fronts = [[]]  # Pareto 前沿列表

        # 计算支配关系
        for i in range(n):
            for j in range(i + 1, n):
                if self.dominates(population_fitness[i], population_fitness[j]):
                    # i 支配 j
                    dominated_solutions[i].append(j)
                    domination_count[j] += 1
                elif self.dominates(population_fitness[j], population_fitness[i]):
                    # j 支配 i
                    dominated_solutions[j].append(i)
                    domination_count[i] += 1

        # 找到第一个前沿（未被支配的解）
        for i in range(n):
            if domination_count[i] == 0:
                population_fitness[i].pareto_rank = 0
                fronts[0].append(i)

        # 构建后续前沿
        front_index = 0
        while front_index < len(fronts) and fronts[front_index]:
            next_front = []
            for i in fronts[front_index]:
                for j in dominated_solutions[i]:
                    domination_count[j] -= 1
                    if domination_count[j] == 0:
                        population_fitness[j].pareto_rank = front_index + 1
                        next_front.append(j)

            if next_front:
                fronts.append(next_front)
            front_index += 1

        logger.debug(f"非支配排序完成: {len(fronts)} 个前沿")

        return fronts

    def calculate_crowding_distance(
        self, front_indices: List[int], population_fitness: List[MultiObjectiveFitness]
    ) -> None:
        """计算拥挤距离

        白皮书依据: 第四章 4.1 拥挤距离计算
        目的: 保持解的多样性

        Args:
            front_indices: 前沿中的个体索引列表
            population_fitness: 种群适应度列表
        """
        n = len(front_indices)

        if n == 0:
            return

        # 初始化拥挤距离
        for i in front_indices:
            population_fitness[i].crowding_distance = 0.0

        # 对每个目标计算拥挤距离
        objectives = ["revenue", "complexity", "instability"]

        for obj in objectives:
            # 按目标值排序
            sorted_indices = sorted(
                front_indices, key=lambda i: getattr(population_fitness[i], obj)  # pylint: disable=w0640
            )  # pylint: disable=w0640

            # 边界点设置为无穷大
            population_fitness[sorted_indices[0]].crowding_distance = float("inf")
            population_fitness[sorted_indices[-1]].crowding_distance = float("inf")

            # 计算目标值范围
            obj_min = getattr(population_fitness[sorted_indices[0]], obj)
            obj_max = getattr(population_fitness[sorted_indices[-1]], obj)
            obj_range = obj_max - obj_min

            if obj_range == 0:
                continue

            # 计算中间点的拥挤距离
            for i in range(1, n - 1):
                idx = sorted_indices[i]
                idx_prev = sorted_indices[i - 1]
                idx_next = sorted_indices[i + 1]

                obj_prev = getattr(population_fitness[idx_prev], obj)
                obj_next = getattr(population_fitness[idx_next], obj)

                # 累加拥挤距离
                population_fitness[idx].crowding_distance += (obj_next - obj_prev) / obj_range

        logger.debug(f"拥挤距离计算完成: {n} 个个体")

    def select_by_pareto(self, population_fitness: List[MultiObjectiveFitness], select_count: int) -> List[int]:
        """基于 Pareto 前沿选择个体

        白皮书依据: 第四章 4.1 Pareto 选择

        选择策略:
        1. 优先选择 Pareto 等级低的个体（前沿靠前）
        2. 同一前沿内，优先选择拥挤距离大的个体（多样性）

        Args:
            population_fitness: 种群适应度列表
            select_count: 选择数量

        Returns:
            List[int]: 选中的个体索引列表
        """
        # 1. 非支配排序
        fronts = self.fast_non_dominated_sort(population_fitness)

        # 2. 计算每个前沿的拥挤距离
        for front in fronts:
            self.calculate_crowding_distance(front, population_fitness)

        # 3. 选择个体
        selected = []

        for front in fronts:
            if len(selected) + len(front) <= select_count:
                # 整个前沿都选择
                selected.extend(front)
            else:
                # 需要从当前前沿中选择部分个体
                remaining = select_count - len(selected)

                # 按拥挤距离降序排序
                sorted_front = sorted(front, key=lambda i: population_fitness[i].crowding_distance, reverse=True)

                selected.extend(sorted_front[:remaining])
                break

        logger.debug(f"Pareto 选择完成: 选择 {len(selected)} 个个体")

        return selected

    def get_pareto_front(self, population_fitness: List[MultiObjectiveFitness]) -> List[int]:
        """获取 Pareto 最优前沿

        Args:
            population_fitness: 种群适应度列表

        Returns:
            List[int]: Pareto 最优前沿的个体索引列表
        """
        fronts = self.fast_non_dominated_sort(population_fitness)

        if fronts:  # pylint: disable=no-else-return
            return fronts[0]
        else:
            return []

    def get_statistics(self, population_fitness: List[MultiObjectiveFitness]) -> Dict[str, Any]:
        """获取多目标优化统计信息

        Args:
            population_fitness: 种群适应度列表

        Returns:
            Dict: 统计信息
        """
        if not population_fitness:
            return {}

        # 计算 Pareto 前沿
        fronts = self.fast_non_dominated_sort(population_fitness)
        pareto_front = fronts[0] if fronts else []

        # 统计信息
        stats = {
            "total_individuals": len(population_fitness),
            "pareto_front_size": len(pareto_front),
            "num_fronts": len(fronts),
            "avg_revenue": np.mean([f.revenue for f in population_fitness]),
            "avg_complexity": np.mean([f.complexity for f in population_fitness]),
            "avg_instability": np.mean([f.instability for f in population_fitness]),
            "avg_weighted_fitness": np.mean([f.weighted_fitness for f in population_fitness]),
        }

        # Pareto 前沿统计
        if pareto_front:
            pareto_fitness = [population_fitness[i] for i in pareto_front]
            stats["pareto_avg_revenue"] = np.mean([f.revenue for f in pareto_fitness])
            stats["pareto_avg_complexity"] = np.mean([f.complexity for f in pareto_fitness])
            stats["pareto_avg_instability"] = np.mean([f.instability for f in pareto_fitness])

        return stats
