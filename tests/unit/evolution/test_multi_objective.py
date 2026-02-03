"""多目标优化系统测试

白皮书依据: 第四章 4.1 遗传算法 - 多目标优化
Phase 3升级测试
"""

import pytest
import numpy as np
from src.evolution.multi_objective import (
    MultiObjectiveFitness,
    MultiObjectiveOptimizer
)


class TestMultiObjectiveFitness:
    """测试多目标适应度类"""
    
    def test_fitness_creation(self):
        """测试适应度创建"""
        fitness = MultiObjectiveFitness(
            revenue=0.8,
            complexity=0.3,
            instability=0.2,
            weighted_fitness=0.5
        )
        
        assert fitness.revenue == 0.8
        assert fitness.complexity == 0.3
        assert fitness.instability == 0.2
        assert fitness.weighted_fitness == 0.5
        assert fitness.pareto_rank == -1
        assert fitness.crowding_distance == 0.0
    
    def test_fitness_validation(self):
        """测试适应度验证（警告但不抛出异常）"""
        # 超出范围的值应该触发警告，但不会抛出异常
        fitness = MultiObjectiveFitness(
            revenue=1.5,  # 超出 [0, 1]
            complexity=-0.1,  # 超出 [0, 1]
            instability=0.5
        )
        
        # 对象应该成功创建
        assert fitness.revenue == 1.5
        assert fitness.complexity == -0.1


class TestMultiObjectiveOptimizer:
    """测试多目标优化器"""
    
    @pytest.fixture
    def optimizer(self):
        """创建优化器实例"""
        return MultiObjectiveOptimizer(
            lambda_complexity=0.3,
            mu_instability=0.2
        )
    
    def test_optimizer_initialization(self, optimizer):
        """测试优化器初始化"""
        assert optimizer.lambda_complexity == 0.3
        assert optimizer.mu_instability == 0.2
    
    def test_calculate_multi_objective_fitness(self, optimizer):
        """测试多目标适应度计算"""
        fitness = optimizer.calculate_multi_objective_fitness(
            ic=0.05,
            ir=0.3,
            sharpe=1.2,
            expression_length=50,
            expression_depth=3,
            operator_count=10,
            ic_volatility=0.05,
            ir_volatility=0.2
        )
        
        # 验证返回类型
        assert isinstance(fitness, MultiObjectiveFitness)
        
        # 验证各维度在合理范围内
        assert 0 <= fitness.revenue <= 1
        assert 0 <= fitness.complexity <= 1
        assert 0 <= fitness.instability <= 1
        assert -1 <= fitness.weighted_fitness <= 1
    
    def test_calculate_fitness_with_high_complexity(self, optimizer):
        """测试高复杂度因子的适应度计算"""
        fitness = optimizer.calculate_multi_objective_fitness(
            ic=0.08,
            ir=0.5,
            sharpe=1.5,
            expression_length=180,  # 接近上限200
            expression_depth=4,  # 接近上限5
            operator_count=18,  # 接近上限20
            ic_volatility=0.03,
            ir_volatility=0.15
        )
        
        # 高复杂度应该导致较高的complexity评分
        assert fitness.complexity > 0.7
        
        # 加权适应度应该受到复杂度惩罚
        # fitness = revenue - λ·complexity - μ·instability
        expected_penalty = optimizer.lambda_complexity * fitness.complexity
        assert expected_penalty > 0.2
    
    def test_calculate_fitness_with_high_instability(self, optimizer):
        """测试高不稳定性因子的适应度计算"""
        fitness = optimizer.calculate_multi_objective_fitness(
            ic=0.06,
            ir=0.4,
            sharpe=1.0,
            expression_length=50,
            expression_depth=2,
            operator_count=8,
            ic_volatility=0.12,  # 高IC波动
            ir_volatility=0.6,  # 高IR波动
        )
        
        # 高不稳定性应该导致较高的instability评分
        assert fitness.instability > 0.7
        
        # 加权适应度应该受到不稳定性惩罚
        expected_penalty = optimizer.mu_instability * fitness.instability
        assert expected_penalty > 0.1
    
    def test_dominates_basic(self, optimizer):
        """测试基本的Pareto支配关系"""
        # fitness1 在所有目标上都优于 fitness2
        fitness1 = MultiObjectiveFitness(
            revenue=0.8,
            complexity=0.2,
            instability=0.1
        )
        fitness2 = MultiObjectiveFitness(
            revenue=0.6,
            complexity=0.4,
            instability=0.3
        )
        
        # fitness1 应该支配 fitness2
        assert optimizer.dominates(fitness1, fitness2) is True
        
        # fitness2 不应该支配 fitness1
        assert optimizer.dominates(fitness2, fitness1) is False
    
    def test_dominates_partial(self, optimizer):
        """测试部分支配关系"""
        # fitness1 在某些目标上更好，某些目标上更差
        fitness1 = MultiObjectiveFitness(
            revenue=0.8,  # 更好
            complexity=0.5,  # 更差
            instability=0.2
        )
        fitness2 = MultiObjectiveFitness(
            revenue=0.6,  # 更差
            complexity=0.3,  # 更好
            instability=0.2
        )
        
        # 两者都不支配对方
        assert optimizer.dominates(fitness1, fitness2) is False
        assert optimizer.dominates(fitness2, fitness1) is False
    
    def test_dominates_equal(self, optimizer):
        """测试相等情况"""
        fitness1 = MultiObjectiveFitness(
            revenue=0.7,
            complexity=0.3,
            instability=0.2
        )
        fitness2 = MultiObjectiveFitness(
            revenue=0.7,
            complexity=0.3,
            instability=0.2
        )
        
        # 相等时不支配
        assert optimizer.dominates(fitness1, fitness2) is False
        assert optimizer.dominates(fitness2, fitness1) is False
    
    def test_fast_non_dominated_sort(self, optimizer):
        """测试快速非支配排序"""
        # 创建测试种群
        population_fitness = [
            MultiObjectiveFitness(revenue=0.9, complexity=0.2, instability=0.1),  # 最优
            MultiObjectiveFitness(revenue=0.8, complexity=0.3, instability=0.2),  # 前沿
            MultiObjectiveFitness(revenue=0.7, complexity=0.4, instability=0.3),  # 第二前沿
            MultiObjectiveFitness(revenue=0.6, complexity=0.5, instability=0.4),  # 第三前沿
            MultiObjectiveFitness(revenue=0.5, complexity=0.6, instability=0.5),  # 第三前沿
        ]
        
        fronts = optimizer.fast_non_dominated_sort(population_fitness)
        
        # 验证前沿结构
        assert isinstance(fronts, list)
        assert len(fronts) > 0
        
        # 验证第一个前沿包含最优个体
        assert 0 in fronts[0]  # 索引0的个体应该在第一前沿
        
        # 验证Pareto等级已设置
        for i, fitness in enumerate(population_fitness):
            assert fitness.pareto_rank >= 0
    
    def test_fast_non_dominated_sort_single_front(self, optimizer):
        """测试单一前沿情况"""
        # 创建互不支配的个体（都在Pareto前沿上）
        population_fitness = [
            MultiObjectiveFitness(revenue=0.9, complexity=0.5, instability=0.3),
            MultiObjectiveFitness(revenue=0.7, complexity=0.3, instability=0.2),
            MultiObjectiveFitness(revenue=0.8, complexity=0.2, instability=0.4),
        ]
        
        fronts = optimizer.fast_non_dominated_sort(population_fitness)
        
        # 所有个体应该在同一前沿
        assert len(fronts) == 1
        assert len(fronts[0]) == 3
        
        # 所有个体的Pareto等级应该是0
        for fitness in population_fitness:
            assert fitness.pareto_rank == 0
    
    def test_calculate_crowding_distance(self, optimizer):
        """测试拥挤距离计算"""
        # 创建前沿
        population_fitness = [
            MultiObjectiveFitness(revenue=0.9, complexity=0.2, instability=0.1),
            MultiObjectiveFitness(revenue=0.7, complexity=0.3, instability=0.2),
            MultiObjectiveFitness(revenue=0.5, complexity=0.4, instability=0.3),
        ]
        front_indices = [0, 1, 2]
        
        optimizer.calculate_crowding_distance(front_indices, population_fitness)
        
        # 边界点应该有无穷大的拥挤距离
        assert population_fitness[0].crowding_distance == float('inf') or \
               population_fitness[2].crowding_distance == float('inf')
        
        # 中间点应该有有限的拥挤距离
        assert population_fitness[1].crowding_distance >= 0
        assert population_fitness[1].crowding_distance != float('inf')
    
    def test_calculate_crowding_distance_empty(self, optimizer):
        """测试空前沿的拥挤距离计算"""
        population_fitness = []
        front_indices = []
        
        # 不应该抛出异常
        optimizer.calculate_crowding_distance(front_indices, population_fitness)
    
    def test_select_by_pareto(self, optimizer):
        """测试基于Pareto的选择"""
        # 创建测试种群
        population_fitness = [
            MultiObjectiveFitness(revenue=0.9, complexity=0.2, instability=0.1),
            MultiObjectiveFitness(revenue=0.8, complexity=0.3, instability=0.2),
            MultiObjectiveFitness(revenue=0.7, complexity=0.4, instability=0.3),
            MultiObjectiveFitness(revenue=0.6, complexity=0.5, instability=0.4),
            MultiObjectiveFitness(revenue=0.5, complexity=0.6, instability=0.5),
        ]
        
        # 选择前3个
        selected = optimizer.select_by_pareto(population_fitness, select_count=3)
        
        # 验证选择结果
        assert len(selected) == 3
        assert all(isinstance(idx, int) for idx in selected)
        assert all(0 <= idx < len(population_fitness) for idx in selected)
        
        # 验证选中的个体Pareto等级较低
        selected_ranks = [population_fitness[idx].pareto_rank for idx in selected]
        assert all(rank >= 0 for rank in selected_ranks)
    
    def test_select_by_pareto_all(self, optimizer):
        """测试选择全部个体"""
        population_fitness = [
            MultiObjectiveFitness(revenue=0.8, complexity=0.3, instability=0.2),
            MultiObjectiveFitness(revenue=0.7, complexity=0.4, instability=0.3),
        ]
        
        selected = optimizer.select_by_pareto(population_fitness, select_count=2)
        
        assert len(selected) == 2
    
    def test_get_pareto_front(self, optimizer):
        """测试获取Pareto最优前沿"""
        population_fitness = [
            MultiObjectiveFitness(revenue=0.9, complexity=0.2, instability=0.1),
            MultiObjectiveFitness(revenue=0.8, complexity=0.3, instability=0.2),
            MultiObjectiveFitness(revenue=0.7, complexity=0.4, instability=0.3),
        ]
        
        pareto_front = optimizer.get_pareto_front(population_fitness)
        
        # 验证返回的是索引列表
        assert isinstance(pareto_front, list)
        assert len(pareto_front) > 0
        assert all(isinstance(idx, int) for idx in pareto_front)
    
    def test_get_statistics(self, optimizer):
        """测试统计信息获取"""
        population_fitness = [
            MultiObjectiveFitness(revenue=0.9, complexity=0.2, instability=0.1, weighted_fitness=0.7),
            MultiObjectiveFitness(revenue=0.8, complexity=0.3, instability=0.2, weighted_fitness=0.6),
            MultiObjectiveFitness(revenue=0.7, complexity=0.4, instability=0.3, weighted_fitness=0.5),
        ]
        
        stats = optimizer.get_statistics(population_fitness)
        
        # 验证统计信息结构
        assert isinstance(stats, dict)
        assert 'total_individuals' in stats
        assert 'pareto_front_size' in stats
        assert 'num_fronts' in stats
        assert 'avg_revenue' in stats
        assert 'avg_complexity' in stats
        assert 'avg_instability' in stats
        assert 'avg_weighted_fitness' in stats
        
        # 验证统计值
        assert stats['total_individuals'] == 3
        assert stats['pareto_front_size'] > 0
        assert 0 <= stats['avg_revenue'] <= 1
        assert 0 <= stats['avg_complexity'] <= 1
        assert 0 <= stats['avg_instability'] <= 1
    
    def test_get_statistics_empty(self, optimizer):
        """测试空种群的统计信息"""
        stats = optimizer.get_statistics([])
        
        assert stats == {}
    
    def test_weighted_fitness_calculation(self, optimizer):
        """测试加权适应度计算公式"""
        # fitness = revenue - λ·complexity - μ·instability
        fitness = optimizer.calculate_multi_objective_fitness(
            ic=0.05,  # 中等IC
            ir=0.3,  # 中等IR
            sharpe=1.0,  # 中等Sharpe
            expression_length=100,  # 中等长度
            expression_depth=3,  # 中等深度
            operator_count=10,  # 中等算子数
            ic_volatility=0.05,  # 中等IC波动
            ir_volatility=0.25  # 中等IR波动
        )
        
        # 手动验证公式
        expected_fitness = (
            fitness.revenue -
            optimizer.lambda_complexity * fitness.complexity -
            optimizer.mu_instability * fitness.instability
        )
        
        # 允许小的浮点数误差
        assert abs(fitness.weighted_fitness - expected_fitness) < 0.01
    
    def test_complexity_components(self, optimizer):
        """测试复杂度各组成部分"""
        # 测试长度复杂度
        fitness_short = optimizer.calculate_multi_objective_fitness(
            ic=0.05, ir=0.3, sharpe=1.0,
            expression_length=20,  # 短
            expression_depth=2,
            operator_count=5,
            ic_volatility=0.05, ir_volatility=0.25
        )
        
        fitness_long = optimizer.calculate_multi_objective_fitness(
            ic=0.05, ir=0.3, sharpe=1.0,
            expression_length=180,  # 长
            expression_depth=2,
            operator_count=5,
            ic_volatility=0.05, ir_volatility=0.25
        )
        
        # 长表达式应该有更高的复杂度
        assert fitness_long.complexity > fitness_short.complexity
    
    def test_instability_components(self, optimizer):
        """测试不稳定性各组成部分"""
        # 测试IC波动率
        fitness_stable = optimizer.calculate_multi_objective_fitness(
            ic=0.05, ir=0.3, sharpe=1.0,
            expression_length=50, expression_depth=2, operator_count=8,
            ic_volatility=0.02,  # 低波动
            ir_volatility=0.15
        )
        
        fitness_unstable = optimizer.calculate_multi_objective_fitness(
            ic=0.05, ir=0.3, sharpe=1.0,
            expression_length=50, expression_depth=2, operator_count=8,
            ic_volatility=0.15,  # 高波动
            ir_volatility=0.15
        )
        
        # 高波动应该有更高的不稳定性
        assert fitness_unstable.instability > fitness_stable.instability


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
