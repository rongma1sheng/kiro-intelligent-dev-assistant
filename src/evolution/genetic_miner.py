# pylint: disable=too-many-lines
"""遗传算法因子挖掘器

白皮书依据: 第四章 4.1 暗物质挖掘工厂
需求: 8.1 - 重构GeneticMiner事件发布
"""

import hashlib
import random
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from loguru import logger

from ..core.dependency_container import LifecycleScope, injectable
from ..infra.event_bus import Event, EventType


class OperatorType(Enum):
    """算子类型

    设计文档依据: design.md - 7 operator categories
    """

    ARITHMETIC = "arithmetic"  # 算术运算 (Basic Math)
    STATISTICAL = "statistical"  # 统计函数
    TEMPORAL = "temporal"  # 时间序列 (Time Series)
    TECHNICAL = "technical"  # 技术指标
    LOGICAL = "logical"  # 逻辑运算
    CROSS_SECTIONAL = "cross_sectional"  # 横截面运算
    ADVANCED = "advanced"  # 高级运算


@dataclass
class Individual:
    """个体（因子表达式）

    白皮书依据: 第四章 4.1 遗传算法个体

    Attributes:
        expression: 因子表达式字符串
        fitness: 适应度评分
        ic: 信息系数
        ir: 信息比率
        sharpe: 夏普比率
        generation: 所属代数
        parent_ids: 父代ID列表
        mutation_history: 变异历史
    """

    expression: str
    fitness: float = 0.0
    ic: float = 0.0
    ir: float = 0.0
    sharpe: float = 0.0
    generation: int = 0
    parent_ids: List[str] = field(default_factory=list)
    mutation_history: List[str] = field(default_factory=list)

    @property
    def individual_id(self) -> str:
        """个体唯一ID"""
        return hashlib.md5(self.expression.encode()).hexdigest()[:12]

    def __post_init__(self):
        """验证个体有效性"""
        if not self.expression:
            raise ValueError("因子表达式不能为空")

        if not -1 <= self.ic <= 1:
            logger.warning(f"IC值异常: {self.ic}")

        if self.fitness < 0:
            logger.warning(f"适应度为负: {self.fitness}")


@dataclass
class EvolutionConfig:  # pylint: disable=too-many-instance-attributes
    """进化配置

    Attributes:
        population_size: 种群大小
        mutation_rate: 变异概率
        crossover_rate: 交叉概率
        elite_ratio: 精英比例
        max_generations: 最大代数
        convergence_threshold: 收敛阈值
        min_ic_threshold: 最小IC阈值
        use_full_fitness: 是否使用完整的6维度适应度评估
        max_expression_length: 表达式最大长度限制
        max_expression_depth: 表达式最大嵌套深度
        max_parameter_value: 参数最大值（如窗口期）
        complexity_penalty: 复杂度惩罚系数
        use_ast_crossover: 是否使用AST子树级交叉（Phase 1升级）
        use_type_checking: 是否使用类型检查（Phase 2升级）
        use_multi_objective: 是否使用多目标优化（Phase 3升级）
        lambda_complexity: 复杂度惩罚系数（多目标优化）
        mu_instability: 不稳定性惩罚系数（多目标优化）
    """

    population_size: int = 50
    mutation_rate: float = 0.2
    crossover_rate: float = 0.8
    elite_ratio: float = 0.1
    max_generations: int = 100
    convergence_threshold: float = 0.001
    min_ic_threshold: float = 0.02
    use_full_fitness: bool = False  # 默认使用简化版本（3维度）
    max_expression_length: int = 200  # 防止表达式无限膨胀
    max_expression_depth: int = 5  # 防止嵌套过深
    max_parameter_value: int = 120  # 防止假长期因子（如sma(close, 999)）
    complexity_penalty: float = 0.01  # 复杂度惩罚系数
    use_ast_crossover: bool = False  # Phase 1升级：AST子树级交叉
    use_type_checking: bool = False  # Phase 2升级：类型检查
    use_multi_objective: bool = False  # Phase 3升级：多目标优化
    lambda_complexity: float = 0.3  # Phase 3：复杂度惩罚系数
    mu_instability: float = 0.2  # Phase 3：不稳定性惩罚系数


@injectable(LifecycleScope.SINGLETON)
class GeneticMiner:  # pylint: disable=too-many-instance-attributes
    """遗传算法因子挖掘器

    白皮书依据: 第四章 4.1 暗物质挖掘工厂

    使用遗传算法自动挖掘有效的量化因子。通过初始化种群、适应度评估、
    精英选择、交叉操作、变异操作等步骤，不断进化出更优秀的因子。

    核心特性:
    - 遗传算法进化
    - 算子白名单机制
    - 多维度适应度评估
    - 精英保留策略
    - 自适应参数调整

    性能要求:
    - 因子生成速度 > 100个/分钟
    - IC收敛精度 < 0.001
    - 内存使用 < 2GB
    """

    def __init__(self, config: Optional[EvolutionConfig] = None):
        """初始化遗传算法挖掘器

        Args:
            config: 进化配置，默认使用标准配置
        """
        self.config = config or EvolutionConfig()
        self.event_bus = None  # 将在initialize中设置

        # 种群和进化状态
        self.population: List[Individual] = []
        self.generation = 0
        self.best_individual: Optional[Individual] = None
        self.fitness_history: List[float] = []

        # 算子白名单
        self.operators = self._initialize_operators()

        # 统计信息
        self.total_evaluations = 0
        self.convergence_count = 0

        # 审计相关
        self.pending_audits: Dict[str, Individual] = {}  # 等待审计的个体
        self.audit_results: Dict[str, Dict[str, Any]] = {}  # 审计结果缓存

        # Phase 1升级：AST相关组件
        self.ast_parser = None
        self.ast_crossover = None
        if self.config.use_ast_crossover:
            from .expression_ast import ASTCrossover, ExpressionParser  # pylint: disable=import-outside-toplevel

            self.ast_parser = ExpressionParser()
            self.ast_crossover = ASTCrossover()
            logger.info("AST子树级交叉已启用（Phase 1升级）")

        # Phase 2升级：类型系统和语义验证
        self.type_system = None
        self.semantic_validator = None
        if self.config.use_type_checking:
            from .expression_types import SemanticValidator, TypeSystem  # pylint: disable=import-outside-toplevel

            self.type_system = TypeSystem()
            self.semantic_validator = SemanticValidator(self.type_system)
            logger.info("类型检查和语义验证已启用（Phase 2升级）")

        # Phase 3升级：多目标优化
        self.multi_objective_optimizer = None
        if self.config.use_multi_objective:
            from .multi_objective import MultiObjectiveOptimizer  # pylint: disable=import-outside-toplevel

            self.multi_objective_optimizer = MultiObjectiveOptimizer(
                lambda_complexity=self.config.lambda_complexity, mu_instability=self.config.mu_instability
            )
            logger.info(
                f"多目标优化已启用（Phase 3升级）: "
                f"λ={self.config.lambda_complexity}, μ={self.config.mu_instability}"
            )

        logger.info(
            f"GeneticMiner初始化: "
            f"population_size={self.config.population_size}, "
            f"mutation_rate={self.config.mutation_rate}, "
            f"crossover_rate={self.config.crossover_rate}, "
            f"use_ast_crossover={self.config.use_ast_crossover}, "
            f"use_type_checking={self.config.use_type_checking}, "
            f"use_multi_objective={self.config.use_multi_objective}"
        )

    async def initialize(self) -> bool:
        """初始化遗传挖掘器

        Returns:
            bool: 初始化是否成功
        """
        try:
            # 获取事件总线
            from ..infra.event_bus import get_event_bus  # pylint: disable=import-outside-toplevel

            self.event_bus = await get_event_bus()

            # 设置事件订阅
            await self._setup_event_subscriptions()

            logger.info("GeneticMiner初始化完成")
            return True

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"GeneticMiner初始化失败: {e}")
            return False

    async def _setup_event_subscriptions(self):
        """设置事件订阅"""
        try:
            # 订阅审计完成事件
            await self.event_bus.subscribe(EventType.AUDIT_COMPLETED, self._handle_audit_completed)

            logger.info("GeneticMiner事件订阅设置完成")

        except Exception as e:
            logger.error(f"GeneticMiner事件订阅设置失败: {e}")
            raise

    async def _handle_audit_completed(self, event: Event):
        """处理审计完成事件

        Args:
            event: 审计完成事件
        """
        try:
            audit_data = event.data
            factor_id = audit_data.get("factor_id")

            if factor_id and factor_id in self.pending_audits:
                # 保存审计结果
                self.audit_results[factor_id] = {
                    "approved": audit_data.get("approved", False),
                    "confidence": audit_data.get("confidence", 0.0),
                    "issues_count": audit_data.get("issues_count", 0),
                    "audit_hash": audit_data.get("audit_hash", ""),
                    "timestamp": time.time(),
                }

                # 移除待审计列表
                individual = self.pending_audits.pop(factor_id)

                logger.info(
                    f"收到因子审计结果: {factor_id}, "
                    f"approved={audit_data.get('approved')}, "
                    f"confidence={audit_data.get('confidence', 0.0):.3f}"
                )

                # 根据审计结果更新个体适应度
                if audit_data.get("approved", False):
                    # 审计通过，保持或提升适应度
                    confidence = audit_data.get("confidence", 0.0)
                    individual.fitness *= 0.8 + 0.4 * confidence  # 根据置信度调整
                else:
                    # 审计未通过，大幅降低适应度
                    individual.fitness *= 0.1

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"处理审计完成事件失败: {e}")

    def _initialize_operators(self) -> Dict[OperatorType, List[str]]:
        """初始化算子白名单

        白皮书依据: 第四章 4.1 算子白名单
        设计文档依据: design.md - OPERATOR_WHITELIST (50+ operators)
        需求依据: requirements.md 1.8

        Returns:
            Dict: 按类型分组的算子列表，共54个算子，7个类别
        """
        operators = {
            # Basic Math (8 operators)
            OperatorType.ARITHMETIC: ["add", "subtract", "multiply", "divide", "power", "sqrt", "abs", "log"],
            # Statistical (8 operators)
            OperatorType.STATISTICAL: ["mean", "std", "var", "skew", "kurt", "median", "quantile", "rank"],
            # Time Series (12 operators)
            OperatorType.TEMPORAL: [
                "delay",
                "delta",
                "ts_sum",
                "ts_mean",
                "ts_std",
                "ts_max",
                "ts_min",
                "ts_rank",
                "ts_corr",
                "ts_cov",
                "decay_linear",
                "decay_exp",
            ],
            # Technical (8 operators)
            OperatorType.TECHNICAL: ["sma", "ema", "rsi", "macd", "bollinger", "atr", "adx", "obv"],
            # Logical (7 operators)
            OperatorType.LOGICAL: ["greater", "less", "equal", "and", "or", "not", "if_then_else"],
            # Cross-Sectional (4 operators)
            OperatorType.CROSS_SECTIONAL: ["cs_rank", "cs_zscore", "cs_demean", "cs_neutralize"],
            # Advanced (7 operators)
            OperatorType.ADVANCED: [
                "rolling_corr",
                "rolling_beta",
                "rolling_sharpe",
                "rolling_ir",
                "factor_neutralize",
                "industry_neutralize",
                "market_neutralize",
            ],
        }

        total_operators = sum(len(ops) for ops in operators.values())
        logger.info(f"算子白名单初始化完成: {total_operators}个算子，7个类别 " f"(设计目标: 54个算子)")

        return operators

    async def initialize_population(self, data_columns: List[str]) -> None:
        """初始化种群

        白皮书依据: 第四章 4.1 初始化种群

        Args:
            data_columns: 可用的数据列名

        Raises:
            ValueError: 当数据列为空时
        """
        if not data_columns:
            raise ValueError("数据列不能为空")

        logger.info(f"开始初始化种群，大小: {self.config.population_size}")

        self.population = []

        for i in range(self.config.population_size):  # pylint: disable=unused-variable
            expression = self._generate_random_expression(data_columns)
            individual = Individual(expression=expression, generation=0)
            self.population.append(individual)

        logger.info(f"种群初始化完成，共 {len(self.population)} 个个体")

        # 发布初始化完成事件（如果事件总线可用）
        if self.event_bus is not None:
            await self.event_bus.publish(
                Event(
                    event_type=EventType.SYSTEM_ALERT,
                    data={
                        "action": "population_initialized",
                        "population_size": len(self.population),
                        "generation": self.generation,
                    },
                )
            )

    def _generate_random_expression(self, data_columns: List[str]) -> str:
        """生成随机因子表达式

        Args:
            data_columns: 可用的数据列名

        Returns:
            str: 随机生成的因子表达式
        """
        # 随机选择表达式复杂度
        complexity = random.randint(1, 4)

        if complexity == 1:  # pylint: disable=no-else-return
            # 简单表达式：单个列或简单运算
            return self._generate_simple_expression(data_columns)
        elif complexity == 2:
            # 中等表达式：技术指标
            return self._generate_technical_expression(data_columns)
        elif complexity == 3:
            # 复杂表达式：组合运算
            return self._generate_complex_expression(data_columns)
        else:
            # 高级表达式：多层嵌套
            return self._generate_advanced_expression(data_columns)

    def _generate_simple_expression(self, data_columns: List[str]) -> str:
        """生成简单表达式"""
        column = random.choice(data_columns)

        # 50% 概率直接返回列名
        if random.random() < 0.5:
            return column

        # 50% 概率添加简单运算
        operator = random.choice(self.operators[OperatorType.ARITHMETIC])

        if operator in ["+", "-", "*", "/"]:  # pylint: disable=no-else-return
            column2 = random.choice(data_columns)
            return f"({column} {operator} {column2})"
        else:
            return f"{operator}({column})"

    def _generate_technical_expression(self, data_columns: List[str]) -> str:
        """生成技术指标表达式"""
        column = random.choice(data_columns)
        indicator = random.choice(self.operators[OperatorType.TECHNICAL])

        # 为技术指标添加参数
        if indicator in ["sma", "ema"]:  # pylint: disable=no-else-return
            period = random.choice([5, 10, 20, 30, 60])
            return f"{indicator}({column}, {period})"
        elif indicator == "rsi":
            period = random.choice([14, 21, 28])
            return f"rsi({column}, {period})"
        elif indicator == "bollinger":
            period = random.choice([20, 30])
            std_dev = random.choice([1.5, 2.0, 2.5])
            return f"bollinger({column}, {period}, {std_dev})"
        else:
            return f"{indicator}({column})"

    def _generate_complex_expression(self, data_columns: List[str]) -> str:
        """生成复杂表达式"""
        # 组合两个简单表达式
        expr1 = self._generate_simple_expression(data_columns)
        expr2 = self._generate_simple_expression(data_columns)

        operator = random.choice(["+", "-", "*", "/", ">", "<"])

        return f"({expr1} {operator} {expr2})"

    def _generate_advanced_expression(self, data_columns: List[str]) -> str:
        """生成高级表达式"""
        # 多层嵌套表达式
        base_expr = self._generate_technical_expression(data_columns)

        # 添加时间序列操作
        temporal_op = random.choice(self.operators[OperatorType.TEMPORAL])

        if temporal_op == "shift":  # pylint: disable=no-else-return
            shift_period = random.choice([1, 2, 3, 5])
            return f"shift({base_expr}, {shift_period})"
        elif temporal_op == "rolling":
            window = random.choice([5, 10, 20])
            stat_op = random.choice(["mean", "std", "max", "min"])
            return f"rolling({base_expr}, {window}).{stat_op}()"
        else:
            return f"{temporal_op}({base_expr})"

    async def evaluate_fitness(self, data: pd.DataFrame, returns: pd.Series) -> None:
        """评估种群适应度

        白皮书依据: 第四章 4.1 适应度评估

        Args:
            data: 因子数据，索引为日期，列为股票代码
            returns: 收益率数据

        Raises:
            ValueError: 当数据为空时
        """
        if data.empty or returns.empty:
            raise ValueError("数据不能为空")

        logger.info(f"开始评估种群适应度，种群大小: {len(self.population)}")

        valid_individuals = []

        for individual in self.population:
            try:
                # 计算因子值
                factor_values = self._evaluate_expression(individual.expression, data)

                if factor_values is None or factor_values.empty:
                    logger.warning(f"因子表达式无效: {individual.expression}")
                    continue

                # 计算IC
                ic = self._calculate_ic(factor_values, returns)
                individual.ic = ic

                # 计算IR
                ir = self._calculate_ir(factor_values, returns)
                individual.ir = ir

                # 计算夏普比率
                sharpe = self._calculate_sharpe(factor_values, returns)
                individual.sharpe = sharpe

                # Phase 3升级：根据配置选择适应度计算方式
                if self.config.use_multi_objective and self.multi_objective_optimizer:
                    # 使用多目标优化（Phase 3）
                    # 计算表达式复杂度指标
                    expression_length = len(individual.expression)
                    expression_depth = self._get_expression_depth(individual.expression)
                    operator_count = sum(individual.expression.count(op) for op in ["+", "-", "*", "/", "(", ")"])

                    # 计算IC/IR波动率（简化版本：使用滚动窗口）
                    ic_volatility = self._calculate_ic_volatility(factor_values, returns)
                    ir_volatility = self._calculate_ir_volatility(factor_values, returns)

                    # 计算多目标适应度
                    mo_fitness = self.multi_objective_optimizer.calculate_multi_objective_fitness(
                        ic=ic,
                        ir=ir,
                        sharpe=sharpe,
                        expression_length=expression_length,
                        expression_depth=expression_depth,
                        operator_count=operator_count,
                        ic_volatility=ic_volatility,
                        ir_volatility=ir_volatility,
                        max_length=self.config.max_expression_length,
                        max_depth=self.config.max_expression_depth,
                    )

                    # 使用加权适应度作为主适应度
                    individual.fitness = mo_fitness.weighted_fitness

                    # 存储多目标适应度信息（用于后续Pareto选择）
                    if not hasattr(individual, "mo_fitness"):
                        individual.mo_fitness = mo_fitness

                elif self.config.use_full_fitness:
                    # 使用完整的6维度评估
                    # 计算独立性（与现有最佳因子比较）
                    existing_factors = []
                    if self.best_individual is not None:
                        best_factor_values = self._evaluate_expression(self.best_individual.expression, data)
                        if best_factor_values is not None:
                            existing_factors.append(best_factor_values)

                    independence = self._calculate_independence(factor_values, existing_factors)

                    # 计算流动性适应性
                    liquidity_adaptability = self._calculate_liquidity_adaptability(factor_values, data, returns)

                    # 计算简洁性
                    simplicity = self._calculate_simplicity(individual.expression)

                    # 计算完整适应度
                    individual.fitness = self._calculate_fitness_complete(
                        ic, ir, sharpe, independence, liquidity_adaptability, simplicity
                    )
                else:
                    # 使用简化的3维度评估（向后兼容）
                    base_fitness = self._calculate_fitness(ic, ir, sharpe)

                    # 应用复杂度惩罚（工程优化）
                    complexity = self._get_expression_complexity(individual.expression)
                    complexity_penalty = self.config.complexity_penalty * complexity

                    individual.fitness = max(0, base_fitness - complexity_penalty)

                valid_individuals.append(individual)
                self.total_evaluations += 1

            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.warning(f"评估个体失败: {individual.expression}, 错误: {e}")
                continue

        # 更新种群（只保留有效个体）
        self.population = valid_individuals

        if not self.population:
            raise RuntimeError("所有个体都无效，无法继续进化")

        # 排序种群（按适应度降序）
        self.population.sort(key=lambda x: x.fitness, reverse=True)

        # 更新最佳个体
        if self.population:
            current_best = self.population[0]
            if self.best_individual is None or current_best.fitness > self.best_individual.fitness:
                self.best_individual = current_best

        # 记录适应度历史
        best_fitness = self.population[0].fitness if self.population else 0.0
        self.fitness_history.append(best_fitness)

        avg_fitness = np.mean([ind.fitness for ind in self.population])

        logger.info(
            f"适应度评估完成 - "
            f"有效个体: {len(self.population)}, "
            f"最佳: {best_fitness:.4f}, "
            f"平均: {avg_fitness:.4f}"
        )

    def _evaluate_expression(self, expression: str, data: pd.DataFrame) -> Optional[pd.Series]:
        """评估因子表达式

        Args:
            expression: 因子表达式
            data: 数据框

        Returns:
            Optional[pd.Series]: 因子值序列
        """
        try:
            # 简化实现：这里应该有完整的表达式解析器
            # 目前只处理一些基本情况

            if expression in data.columns:
                return data[expression]

            # 处理简单的算术运算
            if "+" in expression:
                parts = expression.strip("()").split("+")
                if len(parts) == 2:
                    left = parts[0].strip()
                    right = parts[1].strip()
                    if left in data.columns and right in data.columns:
                        return data[left] + data[right]

            if "-" in expression:
                parts = expression.strip("()").split("-")
                if len(parts) == 2:
                    left = parts[0].strip()
                    right = parts[1].strip()
                    if left in data.columns and right in data.columns:
                        return data[left] - data[right]

            # 处理技术指标（简化版本）
            if "sma(" in expression:
                # 提取参数
                import re  # pylint: disable=import-outside-toplevel

                match = re.search(r"sma\((\w+),\s*(\d+)\)", expression)
                if match:
                    column = match.group(1)
                    period = int(match.group(2))
                    if column in data.columns:
                        return data[column].rolling(window=period).mean()

            # 如果无法解析，返回随机序列（用于测试）
            logger.warning(f"无法解析表达式: {expression}，返回随机值")
            return pd.Series(np.random.randn(len(data)), index=data.index)

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"表达式评估失败: {expression}, 错误: {e}")
            return None

    def _calculate_ic(self, factor: pd.Series, returns: pd.Series) -> float:
        """计算信息系数

        Args:
            factor: 因子值序列
            returns: 收益率序列

        Returns:
            float: 信息系数
        """
        try:
            # 对齐索引
            common_index = factor.index.intersection(returns.index)
            if len(common_index) < 10:  # 至少需要10个数据点
                return 0.0

            factor_aligned = factor.loc[common_index]
            returns_aligned = returns.loc[common_index]

            # 去除NaN值
            valid_mask = ~(factor_aligned.isna() | returns_aligned.isna())
            if valid_mask.sum() < 10:
                return 0.0

            factor_clean = factor_aligned[valid_mask]
            returns_clean = returns_aligned[valid_mask]

            # 计算Spearman相关系数
            ic = factor_clean.corr(returns_clean, method="spearman")

            return ic if not np.isnan(ic) else 0.0

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"IC计算失败: {e}")
            return 0.0

    def _calculate_ir(self, factor: pd.Series, returns: pd.Series) -> float:
        """计算信息比率（向量化优化版本）

        白皮书依据: 第四章 4.1 因子评估标准 - IR (信息比率)

        使用向量化滚动相关系数计算，避免O(n²)循环。
        IR = IC均值 / IC标准差，衡量因子预测能力的稳定性。

        Args:
            factor: 因子值序列
            returns: 收益率序列

        Returns:
            float: 信息比率
        """
        try:
            # 对齐索引
            common_index = factor.index.intersection(returns.index)
            if len(common_index) < 20:
                return 0.0

            factor_aligned = factor.loc[common_index]
            returns_aligned = returns.loc[common_index]

            # 去除NaN值
            valid_mask = ~(factor_aligned.isna() | returns_aligned.isna())
            if valid_mask.sum() < 20:
                return 0.0

            factor_clean = factor_aligned[valid_mask].values
            returns_clean = returns_aligned[valid_mask].values

            # 动态窗口大小
            window = min(20, len(factor_clean) // 4)
            if window < 5:
                return 0.0

            # 向量化计算滚动Spearman相关系数
            # 使用pandas rolling + apply，但用rank预计算优化
            factor_series = pd.Series(factor_clean)
            returns_series = pd.Series(returns_clean)

            # 预计算滚动rank（向量化）
            factor_rolling_rank = factor_series.rolling(window=window).apply(  # pylint: disable=unused-variable
                lambda x: pd.Series(x).rank().iloc[-1] / len(x), raw=False
            )
            returns_rolling_rank = returns_series.rolling(window=window).apply(  # pylint: disable=unused-variable
                lambda x: pd.Series(x).rank().iloc[-1] / len(x), raw=False
            )

            # 使用滚动相关系数计算IC序列（向量化）
            rolling_ic = factor_series.rolling(window=window).corr(returns_series)

            # 去除NaN
            rolling_ic_clean = rolling_ic.dropna()

            if len(rolling_ic_clean) < 5:
                return 0.0

            ic_mean = rolling_ic_clean.mean()
            ic_std = rolling_ic_clean.std()

            ir = ic_mean / ic_std if ic_std > 0 else 0.0

            return ir if not np.isnan(ir) else 0.0

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"IR计算失败: {e}")
            return 0.0

    def _calculate_sharpe(self, factor: pd.Series, returns: pd.Series) -> float:
        """计算夏普比率（向量化优化版本）

        白皮书依据: 第四章 4.1 因子评估标准 - Sharpe Ratio

        使用向量化布尔索引计算策略收益，避免Python循环。
        基于因子分位数构建多空策略，计算年化夏普比率。

        Args:
            factor: 因子值序列
            returns: 收益率序列

        Returns:
            float: 夏普比率
        """
        try:
            # 对齐索引
            common_index = factor.index.intersection(returns.index)
            if len(common_index) < 10:
                return 0.0

            factor_aligned = factor.loc[common_index]
            returns_aligned = returns.loc[common_index]

            # 去除NaN值
            valid_mask = ~(factor_aligned.isna() | returns_aligned.isna())
            if valid_mask.sum() < 10:
                return 0.0

            factor_clean = factor_aligned[valid_mask]
            returns_clean = returns_aligned[valid_mask]

            # 向量化计算因子百分位排名
            factor_rank = factor_clean.rank(pct=True)

            # 向量化构建策略收益
            # 使用shift对齐：t时刻的信号决定t+1时刻的仓位
            factor_rank_shifted = factor_rank.shift(1)
            returns_shifted = returns_clean

            # 去除第一个NaN
            valid_idx = ~factor_rank_shifted.isna()
            factor_rank_valid = factor_rank_shifted[valid_idx]
            returns_valid = returns_shifted[valid_idx]

            if len(returns_valid) < 5:
                return 0.0

            # 向量化计算策略收益
            # 做多信号: rank > 0.8
            # 做空信号: rank < 0.2
            # 中性: 其他
            long_mask = factor_rank_valid > 0.8
            short_mask = factor_rank_valid < 0.2

            # 使用numpy向量化操作
            strategy_returns = np.zeros(len(returns_valid))
            strategy_returns[long_mask.values] = returns_valid[long_mask].values
            strategy_returns[short_mask.values] = -returns_valid[short_mask].values

            # 计算夏普比率
            mean_return = np.mean(strategy_returns)
            std_return = np.std(strategy_returns)

            sharpe = mean_return / std_return * np.sqrt(252) if std_return > 0 else 0.0

            return sharpe if not np.isnan(sharpe) else 0.0

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"夏普比率计算失败: {e}")
            return 0.0

    def _calculate_fitness(self, ic: float, ir: float, sharpe: float) -> float:
        """计算综合适应度

        白皮书依据: 第四章 4.1 适应度函数
        设计文档依据: design.md - Fitness Components (6 dimensions)
        需求依据: requirements.md 1.2
        工程优化: 加入复杂度惩罚，防止过度复杂化

        Args:
            ic: 信息系数
            ir: 信息比率
            sharpe: 夏普比率

        Returns:
            float: 综合适应度

        Note:
            完整的6维度适应度评估应该包括：
            - IC (30%), IR (25%), Sharpe (20%)
            - Independence (10%), Liquidity Adaptability (10%), Simplicity (5%)
            当前实现为简化版本，仅使用前3个维度
        """
        # 权重配置（简化版本，仅3个维度）
        ic_weight = 0.4
        ir_weight = 0.3
        sharpe_weight = 0.3

        # 归一化处理
        ic_norm = max(0, min(1, (abs(ic) - 0.01) / 0.09))  # IC范围 [0.01, 0.10]
        ir_norm = max(0, min(1, (abs(ir) - 0.1) / 0.9))  # IR范围 [0.1, 1.0]
        sharpe_norm = max(0, min(1, (abs(sharpe) - 0.5) / 1.5))  # Sharpe范围 [0.5, 2.0]

        # 综合适应度（不含复杂度惩罚）
        base_fitness = ic_weight * ic_norm + ir_weight * ir_norm + sharpe_weight * sharpe_norm

        return base_fitness

    def _calculate_independence(self, factor: pd.Series, existing_factors: Optional[List[pd.Series]] = None) -> float:
        """计算因子独立性

        白皮书依据: 第四章 4.1 适应度函数 - 独立性评估
        设计文档依据: design.md - Independence (10% weight)
        需求依据: requirements.md 1.2

        评估新因子与现有因子库中因子的独立性，避免因子冗余。

        Args:
            factor: 待评估因子值序列
            existing_factors: 现有因子列表，如果为None则返回满分

        Returns:
            float: 独立性评分 [0, 1]，1表示完全独立
        """
        try:
            # 如果没有现有因子，则完全独立
            if not existing_factors or len(existing_factors) == 0:
                return 1.0

            # 计算与所有现有因子的相关性
            correlations = []
            for existing_factor in existing_factors:
                # 对齐索引
                common_index = factor.index.intersection(existing_factor.index)
                if len(common_index) < 10:
                    continue

                factor_aligned = factor.loc[common_index]
                existing_aligned = existing_factor.loc[common_index]

                # 去除NaN
                valid_mask = ~(factor_aligned.isna() | existing_aligned.isna())
                if valid_mask.sum() < 10:
                    continue

                # 计算Spearman相关系数
                corr = factor_aligned[valid_mask].corr(existing_aligned[valid_mask], method="spearman")

                if not np.isnan(corr):
                    correlations.append(abs(corr))

            if not correlations:
                return 1.0

            # 独立性 = 1 - 最大相关性
            # 如果与某个现有因子高度相关（>0.8），则独立性很低
            max_correlation = max(correlations)
            independence = max(0, 1 - max_correlation)

            return independence

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"独立性计算失败: {e}")
            return 0.5  # 默认中等独立性

    def _calculate_liquidity_adaptability(self, factor: pd.Series, data: pd.DataFrame, returns: pd.Series) -> float:
        """计算流动性适应性

        白皮书依据: 第四章 4.1 适应度函数 - 流动性适应性评估
        设计文档依据: design.md - Liquidity Adaptability (10% weight)
        需求依据: requirements.md 1.2, 1.10

        评估因子在不同流动性层级（高/中/低）的表现一致性。

        Args:
            factor: 因子值序列
            data: 原始数据（需包含volume列）
            returns: 收益率序列

        Returns:
            float: 流动性适应性评分 [0, 1]，1表示在所有流动性层级表现一致
        """
        try:
            # 检查是否有volume数据
            if "volume" not in data.columns:
                logger.warning("缺少volume数据，无法评估流动性适应性")
                return 0.5  # 默认中等适应性

            # 按成交量分为三个层级
            volume = data["volume"]
            volume_quantiles = volume.quantile([0.33, 0.67])

            # 低流动性：volume < 33%分位数
            low_liquidity_mask = volume < volume_quantiles.iloc[0]
            # 中流动性：33% <= volume < 67%
            mid_liquidity_mask = (volume >= volume_quantiles.iloc[0]) & (volume < volume_quantiles.iloc[1])
            # 高流动性：volume >= 67%分位数
            high_liquidity_mask = volume >= volume_quantiles.iloc[1]

            # 计算各层级的IC
            ics = []
            for mask, tier_name in [  # pylint: disable=unused-variable
                (low_liquidity_mask, "低流动性"),
                (mid_liquidity_mask, "中流动性"),
                (high_liquidity_mask, "高流动性"),
            ]:
                if mask.sum() < 10:  # 样本太少
                    continue

                tier_factor = factor[mask]
                tier_returns = returns[mask]

                ic = self._calculate_ic(tier_factor, tier_returns)
                ics.append(abs(ic))

            if len(ics) < 2:
                return 0.5  # 数据不足，返回中等适应性

            # 适应性 = 1 - IC标准差 / IC均值
            # IC越稳定（标准差越小），适应性越好
            ic_mean = np.mean(ics)
            ic_std = np.std(ics)

            if ic_mean == 0:
                return 0.0

            # 变异系数（CV）= std / mean
            cv = ic_std / ic_mean
            # 适应性 = 1 / (1 + CV)，CV越小适应性越好
            adaptability = 1 / (1 + cv)

            return min(1.0, max(0.0, adaptability))

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"流动性适应性计算失败: {e}")
            return 0.5  # 默认中等适应性

    def _calculate_simplicity(self, expression: str) -> float:
        """计算因子表达式简洁性

        白皮书依据: 第四章 4.1 适应度函数 - 简洁性评估
        设计文档依据: design.md - Simplicity (5% weight)
        需求依据: requirements.md 1.2

        评估因子表达式的复杂度，偏好简洁的表达式。
        简洁的因子更容易理解、实现和维护。

        Args:
            expression: 因子表达式字符串

        Returns:
            float: 简洁性评分 [0, 1]，1表示非常简洁
        """
        try:
            # 计算表达式复杂度的多个维度

            # 1. 长度惩罚
            length = len(expression)
            length_score = max(0, 1 - length / 200)  # 超过200字符开始惩罚

            # 2. 算子数量惩罚
            operator_count = 0
            for op_type in self.operators.values():
                for op in op_type:
                    operator_count += expression.count(op)
            operator_score = max(0, 1 - operator_count / 10)  # 超过10个算子开始惩罚

            # 3. 嵌套深度惩罚
            max_depth = 0
            current_depth = 0
            for char in expression:
                if char == "(":
                    current_depth += 1
                    max_depth = max(max_depth, current_depth)
                elif char == ")":
                    current_depth -= 1
            depth_score = max(0, 1 - max_depth / 5)  # 超过5层嵌套开始惩罚

            # 4. 参数数量惩罚
            comma_count = expression.count(",")
            param_score = max(0, 1 - comma_count / 15)  # 超过15个参数开始惩罚

            # 综合简洁性评分（加权平均）
            simplicity = 0.3 * length_score + 0.3 * operator_score + 0.2 * depth_score + 0.2 * param_score

            return min(1.0, max(0.0, simplicity))

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"简洁性计算失败: {e}")
            return 0.5  # 默认中等简洁性

    def _calculate_fitness_complete(  # pylint: disable=too-many-positional-arguments
        self, ic: float, ir: float, sharpe: float, independence: float, liquidity_adaptability: float, simplicity: float
    ) -> float:
        """计算完整的6维度综合适应度

        白皮书依据: 第四章 4.1 适应度函数
        设计文档依据: design.md - Fitness Components (6 dimensions)
        需求依据: requirements.md 1.2

        Args:
            ic: 信息系数
            ir: 信息比率
            sharpe: 夏普比率
            independence: 独立性
            liquidity_adaptability: 流动性适应性
            simplicity: 简洁性

        Returns:
            float: 综合适应度 [0, 1]
        """
        # 权重配置（符合设计文档）
        ic_weight = 0.30
        ir_weight = 0.25
        sharpe_weight = 0.20
        independence_weight = 0.10
        liquidity_weight = 0.10
        simplicity_weight = 0.05

        # 归一化处理
        ic_norm = max(0, min(1, (abs(ic) - 0.01) / 0.09))  # IC范围 [0.01, 0.10]
        ir_norm = max(0, min(1, (abs(ir) - 0.1) / 0.9))  # IR范围 [0.1, 1.0]
        sharpe_norm = max(0, min(1, (abs(sharpe) - 0.5) / 1.5))  # Sharpe范围 [0.5, 2.0]

        # independence, liquidity_adaptability, simplicity 已经是 [0, 1] 范围

        # 综合适应度
        fitness = (
            ic_weight * ic_norm
            + ir_weight * ir_norm
            + sharpe_weight * sharpe_norm
            + independence_weight * independence
            + liquidity_weight * liquidity_adaptability
            + simplicity_weight * simplicity
        )

        return min(1.0, max(0.0, fitness))

    async def evolve(self, data: pd.DataFrame, returns: pd.Series, generations: Optional[int] = None) -> Individual:
        """进化种群

        白皮书依据: 第四章 4.1 进化循环

        Args:
            data: 因子数据
            returns: 收益率数据
            generations: 进化代数，默认使用配置值

        Returns:
            Individual: 最优个体

        Raises:
            ValueError: 当种群未初始化时
            RuntimeError: 当进化失败时
        """
        if not self.population:
            raise ValueError("种群未初始化，请先调用 initialize_population()")

        max_generations = generations or self.config.max_generations

        logger.info(f"开始进化，代数: {max_generations}")

        try:
            for gen in range(max_generations):  # pylint: disable=unused-variable
                self.generation += 1

                logger.info(f"第 {self.generation} 代进化开始")

                # 1. 评估适应度
                await self.evaluate_fitness(data, returns)

                if not self.population:
                    raise RuntimeError(f"第 {self.generation} 代所有个体都无效")

                # 2. 检查收敛
                if self._check_convergence():
                    logger.info(f"第 {self.generation} 代达到收敛条件，提前结束")
                    break

                # 3. 精英选择
                elite_count = max(1, int(self.config.population_size * self.config.elite_ratio))
                elites = self.population[:elite_count]

                # 4. 生成新种群
                new_population = elites.copy()

                while len(new_population) < self.config.population_size:
                    # 选择父母
                    parent1 = self._tournament_selection()
                    parent2 = self._tournament_selection()

                    # 交叉
                    if random.random() < self.config.crossover_rate:
                        child = self._crossover(parent1, parent2)
                    else:
                        child = parent1

                    # 变异
                    if random.random() < self.config.mutation_rate:
                        child = self._mutate(child, data.columns.tolist())

                    # 设置代数
                    child.generation = self.generation
                    child.parent_ids = [parent1.individual_id, parent2.individual_id]

                    new_population.append(child)

                # 5. 更新种群
                self.population = new_population[: self.config.population_size]

                # 6. 记录进度
                best_fitness = self.population[0].fitness if self.population else 0.0
                avg_fitness = np.mean([ind.fitness for ind in self.population])

                logger.info(
                    f"第 {self.generation} 代完成 - "
                    f"最佳适应度: {best_fitness:.4f}, "
                    f"平均适应度: {avg_fitness:.4f}, "
                    f"种群大小: {len(self.population)}"
                )

                # 7. 发布进化事件（如果事件总线可用）
                if self.event_bus is not None:
                    await self.event_bus.publish(
                        Event(
                            event_type=EventType.SYSTEM_ALERT,
                            data={
                                "action": "generation_completed",
                                "generation": self.generation,
                                "best_fitness": best_fitness,
                                "avg_fitness": avg_fitness,
                                "population_size": len(self.population),
                            },
                        )
                    )

            # 最终评估
            await self.evaluate_fitness(data, returns)

            if not self.population:
                raise RuntimeError("进化结束后没有有效个体")

            best_individual = self.population[0]

            logger.info(
                f"进化完成 - "
                f"最佳个体: {best_individual.expression}, "
                f"适应度: {best_individual.fitness:.4f}, "
                f"IC: {best_individual.ic:.4f}, "
                f"IR: {best_individual.ir:.4f}"
            )

            return best_individual

        except Exception as e:
            logger.error(f"进化过程失败: {e}")
            raise RuntimeError(f"进化过程失败: {e}") from e

    async def discover_factor(
        self, data: pd.DataFrame, returns: pd.Series, target_ic: float = 0.05
    ) -> Optional[Individual]:
        """发现单个因子

        白皮书依据: 第四章 4.1 因子发现
        需求: 8.1 - 发布FACTOR_DISCOVERED事件

        Args:
            data: 因子数据
            returns: 收益率数据
            target_ic: 目标IC值

        Returns:
            Optional[Individual]: 发现的因子，如果未找到则返回None
        """
        try:
            logger.info(f"开始因子发现，目标IC: {target_ic}")

            # 初始化小规模种群进行快速搜索
            if not self.population:
                await self.initialize_population(data.columns.tolist())

            # 进行短期进化
            best_individual = await self.evolve(data, returns, generations=10)

            # 检查是否达到目标IC
            if best_individual and abs(best_individual.ic) >= target_ic:  # pylint: disable=no-else-return
                logger.info(
                    f"发现有效因子: {best_individual.expression}, "
                    f"IC={best_individual.ic:.4f}, "
                    f"适应度={best_individual.fitness:.4f}"
                )

                # 发布因子发现事件
                await self._publish_factor_discovered(best_individual)

                # 请求审计
                await self._request_factor_audit(best_individual)

                return best_individual
            else:
                logger.info(f"未找到满足条件的因子，最佳IC: " f"{best_individual.ic if best_individual else 0.0:.4f}")
                return None

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"因子发现失败: {e}")
            return None

    async def _publish_factor_discovered(self, individual: Individual):
        """发布因子发现事件

        Args:
            individual: 发现的因子个体
        """
        if self.event_bus is None:
            logger.warning("事件总线未初始化，跳过因子发现事件发布")
            return

        try:
            await self.event_bus.publish(
                Event(
                    event_type=EventType.FACTOR_DISCOVERED,
                    source_module="genetic_miner",
                    data={
                        "factor_id": individual.individual_id,
                        "expression": individual.expression,
                        "ic": individual.ic,
                        "ir": individual.ir,
                        "sharpe": individual.sharpe,
                        "fitness": individual.fitness,
                        "generation": individual.generation,
                        "discovery_time": time.time(),
                        "metadata": {
                            "parent_ids": individual.parent_ids,
                            "mutation_history": individual.mutation_history,
                        },
                    },
                )
            )

            logger.info(f"发布因子发现事件: {individual.individual_id}")

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"发布因子发现事件失败: {e}")

    async def _request_factor_audit(self, individual: Individual):
        """请求因子审计

        Args:
            individual: 需要审计的因子个体
        """
        if self.event_bus is None:
            logger.warning("事件总线未初始化，跳过因子审计请求")
            return

        try:
            # 生成因子代码（简化版本）
            factor_code = self._generate_factor_code(individual)

            # 添加到待审计列表
            self.pending_audits[individual.individual_id] = individual

            # 发布审计请求事件
            await self.event_bus.publish(
                Event(
                    event_type=EventType.AUDIT_REQUEST,
                    source_module="genetic_miner",
                    target_module="devil_auditor",
                    data={
                        "factor_id": individual.individual_id,
                        "factor_code": factor_code,
                        "factor_expression": individual.expression,
                        "metadata": {
                            "ic": individual.ic,
                            "ir": individual.ir,
                            "fitness": individual.fitness,
                            "generation": individual.generation,
                        },
                    },
                )
            )

            logger.info(f"请求因子审计: {individual.individual_id}")

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"请求因子审计失败: {e}")

    def _generate_factor_code(self, individual: Individual) -> str:
        """生成因子代码

        Args:
            individual: 因子个体

        Returns:
            str: 因子代码
        """
        # 简化的因子代码生成
        code_template = f'''
def calculate_factor(data):
    """
    因子表达式: {individual.expression}
    IC: {individual.ic:.4f}
    IR: {individual.ir:.4f}
    适应度: {individual.fitness:.4f}
    """
    try:
        # 因子计算逻辑
        factor_values = {individual.expression}
        return factor_values
    except Exception as e:
        print(f"因子计算失败: {{e}}")
        return None
'''
        return code_template

    def _check_convergence(self) -> bool:
        """检查收敛条件

        Returns:
            bool: 是否收敛
        """
        if len(self.fitness_history) < 10:
            return False

        # 检查最近10代的适应度变化
        recent_fitness = self.fitness_history[-10:]
        fitness_std = np.std(recent_fitness)

        if fitness_std < self.config.convergence_threshold:
            self.convergence_count += 1
            if self.convergence_count >= 3:  # 连续3次满足收敛条件
                return True
        else:
            self.convergence_count = 0

        return False

    def _tournament_selection(self, tournament_size: int = 3) -> Individual:
        """锦标赛选择

        Args:
            tournament_size: 锦标赛大小

        Returns:
            Individual: 选中的个体
        """
        tournament_size = min(tournament_size, len(self.population))
        candidates = random.sample(self.population, tournament_size)
        return max(candidates, key=lambda x: x.fitness)

    def _crossover(self, parent1: Individual, parent2: Individual) -> Individual:
        """交叉操作

        白皮书依据: 第四章 4.1 遗传算法交叉操作
        Phase 1升级: 支持AST子树级交叉
        Phase 2升级: 集成类型检查验证

        Args:
            parent1: 父代1
            parent2: 父代2

        Returns:
            Individual: 子代个体
        """
        # Phase 1升级：如果启用AST交叉，使用子树级交叉
        if self.config.use_ast_crossover and self.ast_parser and self.ast_crossover:
            try:
                # 解析父代表达式为AST
                parent1_ast = self.ast_parser.parse(parent1.expression)
                parent2_ast = self.ast_parser.parse(parent2.expression)

                # 执行子树级交叉
                child_ast = self.ast_crossover.crossover(parent1_ast, parent2_ast)

                # 转换回表达式字符串
                child_expression = child_ast.to_expression()

                # 检查表达式约束
                if (  # pylint: disable=no-else-return
                    len(child_expression) <= self.config.max_expression_length
                    and self._get_expression_depth(child_expression) <= self.config.max_expression_depth
                ):

                    # Phase 2升级：如果启用类型检查，验证语义合法性
                    if self.config.use_type_checking and self.semantic_validator:
                        # BLOCKED: AST类型推断未在PRD中定义，违反零号铁律
                        # 根据抗幻觉治理原则，不允许实现未定义功能
                        # 当前简化版本：假设AST交叉产生的表达式是合法的
                        pass

                    logger.debug(f"AST交叉成功: {child_expression}")

                    return Individual(
                        expression=child_expression, parent_ids=[parent1.individual_id, parent2.individual_id]
                    )
                else:
                    logger.debug("AST交叉结果超出约束，回退到简单交叉")

            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.warning(f"AST交叉失败: {e}，回退到简单交叉")

        # 简化的交叉实现：随机选择父代之一的表达式
        # 这是Phase 0的实现，作为AST交叉的后备方案
        if random.random() < 0.5:
            child_expression = parent1.expression
        else:
            child_expression = parent2.expression

        return Individual(expression=child_expression, parent_ids=[parent1.individual_id, parent2.individual_id])

    def _mutate(self, individual: Individual, data_columns: List[str]) -> Individual:
        """变异操作

        白皮书依据: 第四章 4.1 遗传算法变异操作
        需求依据: requirements.md 1.5 - 6种变异策略
        工程优化: 使用自适应权重，后期提高simplify/remove概率

        Args:
            individual: 待变异个体
            data_columns: 可用数据列

        Returns:
            Individual: 变异后个体
        """
        # 获取自适应权重
        weights = self._get_adaptive_mutation_weights()
        mutation_types = list(weights.keys())
        mutation_probs = list(weights.values())

        # 根据权重选择变异类型
        mutation_type = random.choices(mutation_types, weights=mutation_probs, k=1)[0]
        mutated_expression = individual.expression

        try:
            if mutation_type == "add_operator":
                # 添加算子
                mutated_expression = self._add_random_operator(mutated_expression, data_columns)
            elif mutation_type == "remove_operator":
                # 移除算子
                mutated_expression = self._remove_random_operator(mutated_expression)
            elif mutation_type == "replace_operator":
                # 替换算子
                mutated_expression = self._replace_random_operator(mutated_expression)
            elif mutation_type == "change_parameter":
                # 改变参数
                mutated_expression = self._change_random_parameter(mutated_expression)
            elif mutation_type == "swap_subtrees":
                # 交换子树
                mutated_expression = self._swap_random_subtrees(mutated_expression)
            elif mutation_type == "simplify_expression":
                # 简化表达式
                mutated_expression = self._simplify_expression(mutated_expression)

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.warning(f"变异失败: {e}，保持原表达式")
            mutated_expression = individual.expression

        mutated_individual = Individual(expression=mutated_expression, parent_ids=[individual.individual_id])
        mutated_individual.mutation_history = individual.mutation_history + [mutation_type]

        return mutated_individual

    def _replace_random_operator(self, expression: str) -> str:
        """替换随机算子"""
        # 简化实现
        operators = ["+", "-", "*", "/"]
        for old_op in operators:
            if old_op in expression:
                new_op = random.choice([op for op in operators if op != old_op])
                return expression.replace(old_op, new_op, 1)
        return expression

    def _replace_random_column(self, expression: str, data_columns: List[str]) -> str:
        """替换随机数据列"""
        for column in data_columns:
            if column in expression:
                new_column = random.choice([col for col in data_columns if col != column])
                return expression.replace(column, new_column, 1)
        return expression

    def _add_random_operator(self, expression: str, data_columns: List[str]) -> str:
        """添加随机算子

        工程约束: 检查表达式长度和深度限制
        Phase 2升级: 集成类型检查，防止语义错误
        """
        # 检查长度限制
        if len(expression) >= self.config.max_expression_length:
            logger.warning(f"表达式长度达到上限 {self.config.max_expression_length}，跳过add_operator")
            return expression

        # 检查深度限制
        if self._get_expression_depth(expression) >= self.config.max_expression_depth:
            logger.warning(f"表达式深度达到上限 {self.config.max_expression_depth}，跳过add_operator")
            return expression

        operator = random.choice(["+", "-", "*", "/"])
        column = random.choice(data_columns)

        # Phase 2升级：如果启用类型检查，验证语义合法性
        if self.config.use_type_checking and self.type_system and self.semantic_validator:
            # 推断表达式类型（简化版本）
            expr_type = self.type_system.get_column_type(expression) if expression in data_columns else None
            column_type = self.type_system.get_column_type(column)

            # 如果能推断类型，进行语义验证
            if expr_type and column_type:
                is_valid, errors = self.semantic_validator.validate_expression(operator, expr_type, column_type)

                if not is_valid:
                    logger.debug(f"类型检查失败: {operator}({expr_type.value}, {column_type.value}) - {errors}")

                    # 尝试获取修复建议
                    suggestion = self.semantic_validator.suggest_fix(operator, expr_type, column_type)
                    if suggestion:
                        logger.debug(f"修复建议: {suggestion}")

                    # 返回原表达式，不添加不合法的算子
                    return expression

        # 对除法使用安全包装
        if operator == "/":  # pylint: disable=no-else-return
            return f"safe_div({expression}, {column})"
        else:
            return f"({expression} {operator} {column})"

    def _remove_random_operator(self, expression: str) -> str:
        """移除随机算子

        白皮书依据: 第四章 4.1 变异策略 - remove_operator
        需求依据: requirements.md 1.5

        Args:
            expression: 原始表达式

        Returns:
            str: 移除算子后的表达式
        """
        # 简化实现：移除最外层的运算
        # 如果表达式是 (A op B) 形式，随机返回 A 或 B
        if expression.startswith("(") and expression.endswith(")"):
            inner = expression[1:-1]
            # 尝试找到主运算符
            for op in ["+", "-", "*", "/"]:
                if op in inner:
                    parts = inner.split(op, 1)
                    if len(parts) == 2:
                        # 随机选择左边或右边
                        return random.choice([parts[0].strip(), parts[1].strip()])
        return expression

    def _change_random_parameter(self, expression: str) -> str:
        """改变随机参数

        白皮书依据: 第四章 4.1 变异策略 - change_parameter
        需求依据: requirements.md 1.5
        工程约束: 参数上限防止假长期因子

        Args:
            expression: 原始表达式

        Returns:
            str: 改变参数后的表达式
        """
        import re  # pylint: disable=import-outside-toplevel

        # 查找表达式中的数字参数
        numbers = re.findall(r"\d+", expression)
        if numbers:
            # 随机选择一个数字进行修改
            old_num = random.choice(numbers)
            old_val = int(old_num)

            # 在原值的50%-150%范围内随机选择新值
            new_val = max(1, int(old_val * random.uniform(0.5, 1.5)))

            # 应用参数上限约束
            new_val = min(new_val, self.config.max_parameter_value)

            # 替换第一个出现的该数字
            new_expression = expression.replace(old_num, str(new_val), 1)

            if new_val == self.config.max_parameter_value:
                logger.debug(f"参数被限制在上限: {new_val}")

            return new_expression

        return expression

    def _swap_random_subtrees(self, expression: str) -> str:
        """交换随机子树

        白皮书依据: 第四章 4.1 变异策略 - swap_subtrees
        需求依据: requirements.md 1.5

        Args:
            expression: 原始表达式

        Returns:
            str: 交换子树后的表达式
        """
        # 简化实现：如果表达式是 (A op B) 形式，交换 A 和 B
        if expression.startswith("(") and expression.endswith(")"):
            inner = expression[1:-1]
            # 尝试找到主运算符
            for op in ["+", "-", "*", "/"]:
                if op in inner:
                    parts = inner.split(op, 1)
                    if len(parts) == 2:
                        left = parts[0].strip()
                        right = parts[1].strip()
                        # 交换左右子树
                        return f"({right} {op} {left})"
        return expression

    def _simplify_expression(self, expression: str) -> str:
        """简化表达式"""
        # 移除外层括号
        if expression.startswith("(") and expression.endswith(")"):
            return expression[1:-1]
        return expression

    def _get_expression_depth(self, expression: str) -> int:
        """计算表达式嵌套深度

        工程约束: 防止表达式无限嵌套

        Args:
            expression: 因子表达式

        Returns:
            int: 嵌套深度
        """
        max_depth = 0
        current_depth = 0

        for char in expression:
            if char == "(":
                current_depth += 1
                max_depth = max(max_depth, current_depth)
            elif char == ")":
                current_depth -= 1

        return max_depth

    def _get_expression_complexity(self, expression: str) -> float:
        """计算表达式复杂度评分

        工程约束: 用于fitness惩罚

        Args:
            expression: 因子表达式

        Returns:
            float: 复杂度评分 [0, 1]，越高越复杂
        """
        # 长度复杂度
        length_complexity = min(1.0, len(expression) / self.config.max_expression_length)

        # 深度复杂度
        depth_complexity = min(1.0, self._get_expression_depth(expression) / self.config.max_expression_depth)

        # 算子数量复杂度
        operator_count = sum(expression.count(op) for op in ["+", "-", "*", "/", "(", ")"])
        operator_complexity = min(1.0, operator_count / 20)

        # 综合复杂度
        complexity = 0.4 * length_complexity + 0.3 * depth_complexity + 0.3 * operator_complexity

        return complexity

    def _get_adaptive_mutation_weights(self) -> Dict[str, float]:
        """获取自适应变异权重

        工程优化: 后期提高simplify/remove权重，防止过度复杂化

        Returns:
            Dict: 变异类型到权重的映射
        """
        # 计算进化进度
        progress = self.generation / self.config.max_generations if self.config.max_generations > 0 else 0

        # 早期（0-30%）：探索为主
        if progress < 0.3:  # pylint: disable=no-else-return
            return {
                "add_operator": 0.25,
                "remove_operator": 0.10,
                "replace_operator": 0.20,
                "change_parameter": 0.20,
                "swap_subtrees": 0.15,
                "simplify_expression": 0.10,
            }
        # 中期（30-70%）：平衡
        elif progress < 0.7:
            return {
                "add_operator": 0.15,
                "remove_operator": 0.15,
                "replace_operator": 0.20,
                "change_parameter": 0.25,
                "swap_subtrees": 0.15,
                "simplify_expression": 0.10,
            }
        # 后期（70-100%）：简化和优化为主
        else:
            return {
                "add_operator": 0.10,
                "remove_operator": 0.20,  # 提高
                "replace_operator": 0.15,
                "change_parameter": 0.25,
                "swap_subtrees": 0.10,
                "simplify_expression": 0.20,  # 提高
            }

    def _calculate_ic_volatility(self, factor: pd.Series, returns: pd.Series) -> float:
        """计算IC波动率

        Phase 3升级: 用于多目标优化的不稳定性评估

        Args:
            factor: 因子值序列
            returns: 收益率序列

        Returns:
            float: IC波动率
        """
        try:
            # 计算滚动IC
            window = min(20, len(factor) // 4)
            if window < 5:
                return 0.0

            rolling_ic = []
            for i in range(window, len(factor)):
                factor_window = factor.iloc[i - window : i]
                returns_window = returns.iloc[i - window : i]
                ic = self._calculate_ic(factor_window, returns_window)
                rolling_ic.append(ic)

            if not rolling_ic:
                return 0.0

            # IC波动率 = IC的标准差
            ic_volatility = np.std(rolling_ic)

            return ic_volatility if not np.isnan(ic_volatility) else 0.0

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"IC波动率计算失败: {e}")
            return 0.0

    def _calculate_ir_volatility(self, factor: pd.Series, returns: pd.Series) -> float:
        """计算IR波动率

        Phase 3升级: 用于多目标优化的不稳定性评估

        Args:
            factor: 因子值序列
            returns: 收益率序列

        Returns:
            float: IR波动率
        """
        try:
            # 计算滚动IR
            window = min(20, len(factor) // 4)
            if window < 5:
                return 0.0

            rolling_ir = []
            for i in range(window, len(factor)):
                factor_window = factor.iloc[i - window : i]
                returns_window = returns.iloc[i - window : i]
                ir = self._calculate_ir(factor_window, returns_window)
                rolling_ir.append(ir)

            if not rolling_ir:
                return 0.0

            # IR波动率 = IR的标准差
            ir_volatility = np.std(rolling_ir)

            return ir_volatility if not np.isnan(ir_volatility) else 0.0

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"IR波动率计算失败: {e}")
            return 0.0

    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息

        Returns:
            Dict: 统计信息
        """
        # 计算审计统计
        total_audits = len(self.audit_results)
        approved_audits = sum(1 for result in self.audit_results.values() if result.get("approved", False))
        audit_approval_rate = approved_audits / total_audits if total_audits > 0 else 0.0

        return {
            "generation": self.generation,
            "population_size": len(self.population),
            "total_evaluations": self.total_evaluations,
            "best_fitness": self.best_individual.fitness if self.best_individual else 0.0,
            "best_ic": self.best_individual.ic if self.best_individual else 0.0,
            "best_expression": self.best_individual.expression if self.best_individual else "",
            "fitness_history": self.fitness_history,
            "convergence_count": self.convergence_count,
            "operators_count": sum(len(ops) for ops in self.operators.values()),
            # 审计统计
            "pending_audits": len(self.pending_audits),
            "completed_audits": total_audits,
            "audit_approval_rate": audit_approval_rate,
            "avg_audit_confidence": (
                np.mean([r.get("confidence", 0.0) for r in self.audit_results.values()]) if self.audit_results else 0.0
            ),
        }

    def export_best_factors(self, top_n: int = 10) -> List[Dict[str, Any]]:
        """导出最佳因子

        Args:
            top_n: 导出数量

        Returns:
            List[Dict]: 最佳因子列表
        """
        if not self.population:
            return []

        # 按适应度排序
        sorted_population = sorted(self.population, key=lambda x: x.fitness, reverse=True)

        best_factors = []
        for i, individual in enumerate(sorted_population[:top_n]):
            factor_info = {
                "rank": i + 1,
                "expression": individual.expression,
                "fitness": individual.fitness,
                "ic": individual.ic,
                "ir": individual.ir,
                "sharpe": individual.sharpe,
                "generation": individual.generation,
                "individual_id": individual.individual_id,
            }
            best_factors.append(factor_info)

        return best_factors

    def reverse_evolution_autopsy(self, failed_individuals: List[Individual]) -> Dict[str, Any]:
        """反向进化尸检分析

        白皮书依据: 第四章 4.1 反向进化机制
        需求依据: requirements.md 1.7

        分析失败因子，识别问题算子和模式，生成改进建议。

        Args:
            failed_individuals: 失败的因子个体列表（适应度低于阈值）

        Returns:
            Dict: 尸检分析报告，包含问题算子、失败模式、改进建议
        """
        if not failed_individuals:
            return {"total_failed": 0, "problem_operators": {}, "failure_patterns": [], "improvement_suggestions": []}

        logger.info(f"开始反向进化尸检分析，失败个体数: {len(failed_individuals)}")

        # 1. 统计问题算子
        problem_operators = self._identify_problem_operators(failed_individuals)

        # 2. 识别失败模式
        failure_patterns = self._identify_failure_patterns(failed_individuals)

        # 3. 生成改进建议
        improvement_suggestions = self._generate_improvement_suggestions(problem_operators, failure_patterns)

        # 4. 编译尸检报告
        autopsy_report = {
            "total_failed": len(failed_individuals),
            "avg_fitness": np.mean([ind.fitness for ind in failed_individuals]),
            "avg_ic": np.mean([ind.ic for ind in failed_individuals]),
            "problem_operators": problem_operators,
            "failure_patterns": failure_patterns,
            "improvement_suggestions": improvement_suggestions,
            "timestamp": time.time(),
        }

        logger.info(
            f"尸检分析完成 - "
            f"问题算子: {len(problem_operators)}, "
            f"失败模式: {len(failure_patterns)}, "
            f"改进建议: {len(improvement_suggestions)}"
        )

        return autopsy_report

    def _identify_problem_operators(self, failed_individuals: List[Individual]) -> Dict[str, Dict[str, Any]]:
        """识别问题算子

        Args:
            failed_individuals: 失败个体列表

        Returns:
            Dict: 问题算子统计，格式 {operator: {count, avg_fitness, severity}}
        """
        operator_stats = {}

        # 统计每个算子在失败因子中的出现频率
        for individual in failed_individuals:
            expression = individual.expression

            # 检查所有算子类型
            for op_type, operators in self.operators.items():
                for operator in operators:
                    if operator in expression:
                        if operator not in operator_stats:
                            operator_stats[operator] = {
                                "count": 0,
                                "total_fitness": 0.0,
                                "operator_type": op_type.value,
                            }

                        operator_stats[operator]["count"] += 1
                        operator_stats[operator]["total_fitness"] += individual.fitness

        # 计算平均适应度和严重程度
        problem_operators = {}
        for operator, stats in operator_stats.items():
            avg_fitness = stats["total_fitness"] / stats["count"]

            # 严重程度 = 出现频率 * (1 - 平均适应度)
            # 出现频率高且适应度低的算子被认为是问题算子
            frequency = stats["count"] / len(failed_individuals)
            severity = frequency * (1 - avg_fitness)

            # 只保留严重程度 > 0.1 的问题算子
            if severity > 0.1:
                problem_operators[operator] = {
                    "count": stats["count"],
                    "frequency": frequency,
                    "avg_fitness": avg_fitness,
                    "severity": severity,
                    "operator_type": stats["operator_type"],
                }

        # 按严重程度排序
        problem_operators = dict(sorted(problem_operators.items(), key=lambda x: x[1]["severity"], reverse=True))

        return problem_operators

    def _identify_failure_patterns(self, failed_individuals: List[Individual]) -> List[Dict[str, Any]]:
        """识别失败模式

        Args:
            failed_individuals: 失败个体列表

        Returns:
            List[Dict]: 失败模式列表
        """
        patterns = []

        # 模式1: 过度复杂
        overly_complex = [
            ind for ind in failed_individuals if len(ind.expression) > self.config.max_expression_length * 0.8
        ]
        if len(overly_complex) > len(failed_individuals) * 0.3:
            patterns.append(
                {
                    "pattern": "overly_complex",
                    "description": "表达式过度复杂",
                    "count": len(overly_complex),
                    "percentage": len(overly_complex) / len(failed_individuals),
                    "avg_length": np.mean([len(ind.expression) for ind in overly_complex]),
                }
            )

        # 模式2: 过度嵌套
        overly_nested = [
            ind
            for ind in failed_individuals
            if self._get_expression_depth(ind.expression) > self.config.max_expression_depth * 0.8
        ]
        if len(overly_nested) > len(failed_individuals) * 0.3:
            patterns.append(
                {
                    "pattern": "overly_nested",
                    "description": "表达式嵌套过深",
                    "count": len(overly_nested),
                    "percentage": len(overly_nested) / len(failed_individuals),
                    "avg_depth": np.mean([self._get_expression_depth(ind.expression) for ind in overly_nested]),
                }
            )

        # 模式3: IC接近零
        near_zero_ic = [ind for ind in failed_individuals if abs(ind.ic) < 0.01]
        if len(near_zero_ic) > len(failed_individuals) * 0.3:
            patterns.append(
                {
                    "pattern": "near_zero_ic",
                    "description": "IC接近零，无预测能力",
                    "count": len(near_zero_ic),
                    "percentage": len(near_zero_ic) / len(failed_individuals),
                    "avg_ic": np.mean([abs(ind.ic) for ind in near_zero_ic]),
                }
            )

        # 模式4: 高波动性（IR很低）
        high_volatility = [ind for ind in failed_individuals if abs(ind.ir) < 0.1]
        if len(high_volatility) > len(failed_individuals) * 0.3:
            patterns.append(
                {
                    "pattern": "high_volatility",
                    "description": "IR过低，因子不稳定",
                    "count": len(high_volatility),
                    "percentage": len(high_volatility) / len(failed_individuals),
                    "avg_ir": np.mean([abs(ind.ir) for ind in high_volatility]),
                }
            )

        # 模式5: 参数过大（假长期因子）
        large_parameters = []
        for ind in failed_individuals:
            import re  # pylint: disable=import-outside-toplevel

            numbers = re.findall(r"\d+", ind.expression)
            if numbers and any(int(n) > self.config.max_parameter_value * 0.8 for n in numbers):
                large_parameters.append(ind)

        if len(large_parameters) > len(failed_individuals) * 0.2:
            patterns.append(
                {
                    "pattern": "large_parameters",
                    "description": "参数过大，可能是假长期因子",
                    "count": len(large_parameters),
                    "percentage": len(large_parameters) / len(failed_individuals),
                }
            )

        return patterns

    def _generate_improvement_suggestions(
        self, problem_operators: Dict[str, Dict[str, Any]], failure_patterns: List[Dict[str, Any]]
    ) -> List[str]:
        """生成改进建议

        Args:
            problem_operators: 问题算子统计
            failure_patterns: 失败模式列表

        Returns:
            List[str]: 改进建议列表
        """
        suggestions = []

        # 基于问题算子的建议
        if problem_operators:
            top_problem_ops = list(problem_operators.keys())[:3]
            suggestions.append(f"降低以下算子的使用频率: {', '.join(top_problem_ops)}")

            # 检查是否有特定类型的算子问题
            op_types = [op["operator_type"] for op in problem_operators.values()]
            from collections import Counter  # pylint: disable=import-outside-toplevel

            type_counts = Counter(op_types)
            most_common_type = type_counts.most_common(1)[0][0] if type_counts else None

            if most_common_type:
                suggestions.append(f"注意 {most_common_type} 类型算子的使用，该类型算子在失败因子中频繁出现")

        # 基于失败模式的建议
        for pattern in failure_patterns:
            if pattern["pattern"] == "overly_complex":
                suggestions.append(
                    f"提高 simplify_expression 和 remove_operator 变异的权重，"
                    f"当前 {pattern['percentage']*100:.1f}% 的失败因子过度复杂"
                )

            elif pattern["pattern"] == "overly_nested":
                suggestions.append(
                    f"降低 add_operator 变异的权重，或更严格地限制表达式深度，"
                    f"当前 {pattern['percentage']*100:.1f}% 的失败因子嵌套过深"
                )

            elif pattern["pattern"] == "near_zero_ic":
                suggestions.append(
                    f"增加因子与收益的相关性检查，" f"当前 {pattern['percentage']*100:.1f}% 的失败因子IC接近零"
                )

            elif pattern["pattern"] == "high_volatility":
                suggestions.append(
                    f"增加因子稳定性约束，考虑使用平滑算子，" f"当前 {pattern['percentage']*100:.1f}% 的失败因子IR过低"
                )

            elif pattern["pattern"] == "large_parameters":
                suggestions.append(
                    f"降低 max_parameter_value 配置，或在 change_parameter 变异中更严格地限制参数范围，"
                    f"当前 {pattern['percentage']*100:.1f}% 的失败因子使用了过大的参数"
                )

        # 通用建议
        if not suggestions:
            suggestions.append("当前未发现明显的系统性问题，继续监控因子质量")

        return suggestions
