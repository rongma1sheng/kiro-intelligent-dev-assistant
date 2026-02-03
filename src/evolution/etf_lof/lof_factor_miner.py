"""LOF Factor Miner - Genetic Algorithm for LOF Factor Mining

白皮书依据: 第四章 4.1.18 - LOF基金因子挖掘器
版本: v1.6.1

LOFFactorMiner是专门用于LOF（上市开放式基金）的遗传算法因子挖掘器。
继承自GeneticMiner基类，针对LOF产品的特性进行了专门化。

LOF特点:
- 场内外双重交易机制
- 转托管套利机会
- 基金经理选择能力
- 流动性分层特征

核心功能:
1. 使用20个LOF专用算子生成因子表达式
2. 评估因子在LOF市场数据上的表现
3. 通过遗传算法进化出高质量因子
4. 支持Arena三轨测试集成
"""

import random
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from loguru import logger

from src.evolution.etf_lof.data_models import LOFMarketData
from src.evolution.etf_lof.exceptions import DataQualityError, FactorMiningError, OperatorError
from src.evolution.etf_lof.lof_operators import LOFOperators
from src.evolution.genetic_miner import EvolutionConfig, GeneticMiner


class LOFFactorMiner(GeneticMiner):
    """LOF因子挖掘器

    白皮书依据: 第四章 4.1.18 - LOF基金因子挖掘器

    使用遗传算法挖掘LOF产品的量化因子。继承自GeneticMiner基类，
    针对LOF产品的特性进行了专门化。

    LOF算子分类:
    - 场内外价差算子（5个）: 价差、套利、折溢价、流动性
    - 基金分析算子（5个）: 流动性分层、投资者结构、基金经理Alpha、风格、持仓集中度
    - 性能算子（10个）: 行业配置、换手率、业绩持续性、费率影响、分红收益率等

    Attributes:
        market_data: LOF市场数据
        lof_operators: LOF算子白名单（20个）
        common_operators: 通用算子（8个）
        operator_registry: 算子注册表
        config: 进化配置

    Example:
        >>> market_data = LOFMarketData(...)
        >>> miner = LOFFactorMiner(market_data=market_data, population_size=50)
        >>> miner.initialize_population()
        >>> miner.evolve(generations=10)
    """

    def __init__(  # pylint: disable=too-many-positional-arguments
        self,
        market_data: Optional[LOFMarketData] = None,
        population_size: int = 50,
        mutation_rate: float = 0.2,
        crossover_rate: float = 0.7,
        elite_ratio: float = 0.1,
        config: Optional[EvolutionConfig] = None,
    ):
        """初始化LOF因子挖掘器

        白皮书依据: 第四章 4.1.18 - LOF基金因子挖掘器

        Args:
            market_data: LOF市场数据，包含场内外价格、净值、成交量等
            population_size: 种群大小，必须 > 0，默认50
            mutation_rate: 变异概率，范围[0, 1]，默认0.2
            crossover_rate: 交叉概率，范围[0, 1]，默认0.7
            elite_ratio: 精英比例，范围[0, 1]，默认0.1
            config: 进化配置对象，如果提供则覆盖单独参数

        Raises:
            ValueError: 当参数不在有效范围时
            FactorMiningError: 当算子注册失败时

        Example:
            >>> miner = LOFFactorMiner(population_size=100, mutation_rate=0.3)
        """
        # 参数验证
        if population_size <= 0:
            raise ValueError(f"population_size must be > 0, got {population_size}")

        if not 0 <= mutation_rate <= 1:
            raise ValueError(f"mutation_rate must be in [0, 1], got {mutation_rate}")

        if not 0 <= crossover_rate <= 1:
            raise ValueError(f"crossover_rate must be in [0, 1], got {crossover_rate}")

        if not 0 <= elite_ratio <= 1:
            raise ValueError(f"elite_ratio must be in [0, 1], got {elite_ratio}")

        # 如果提供了config，使用config的参数
        if config is not None:
            population_size = config.population_size
            mutation_rate = config.mutation_rate
            crossover_rate = config.crossover_rate
            elite_ratio = config.elite_ratio
        else:
            # 创建默认config
            config = EvolutionConfig(
                population_size=population_size,
                mutation_rate=mutation_rate,
                crossover_rate=crossover_rate,
                elite_ratio=elite_ratio,
            )

        # 调用父类初始化（只传递config）
        super().__init__(config=config)

        # 保存配置和市场数据
        self.config = config
        self.market_data = market_data

        # 初始化LOF算子白名单（20个）
        self.lof_operators = [
            # 场内外价差算子（5个）
            "lof_onoff_price_spread",  # 场内外价差
            "lof_transfer_arbitrage_opportunity",  # 转托管套利机会
            "lof_premium_discount_rate",  # 折溢价率
            "lof_onmarket_liquidity",  # 场内流动性
            "lof_offmarket_liquidity",  # 场外流动性
            # 基金分析算子（5个）
            "lof_liquidity_stratification",  # 流动性分层
            "lof_investor_structure",  # 投资者结构
            "lof_fund_manager_alpha",  # 基金经理Alpha
            "lof_fund_manager_style",  # 基金经理风格
            "lof_holding_concentration",  # 持仓集中度
            # 性能算子（10个）
            "lof_sector_allocation_shift",  # 行业配置变化
            "lof_turnover_rate",  # 换手率
            "lof_performance_persistence",  # 业绩持续性
            "lof_expense_ratio_impact",  # 费率影响
            "lof_dividend_yield_signal",  # 分红收益率信号
            "lof_nav_momentum",  # 净值动量
            "lof_redemption_pressure",  # 赎回压力
            "lof_benchmark_tracking_quality",  # 基准跟踪质量
            "lof_market_impact_cost",  # 市场冲击成本
            "lof_cross_sectional_momentum",  # 横截面动量
        ]

        # 通用算子（8个）
        self.common_operators = [
            "rank",  # 排名
            "delay",  # 延迟
            "delta",  # 差分
            "ts_mean",  # 时间序列均值
            "ts_std",  # 时间序列标准差
            "correlation",  # 相关性
            "covariance",  # 协方差
            "regression_residual",  # 回归残差
        ]

        # 构建算子注册表
        self.operator_registry = self._build_operator_registry()

        logger.info(
            "LOFFactorMiner initialized",
            extra={
                "component": "LOFFactorMiner",
                "action": "initialize",
                "population_size": population_size,
                "mutation_rate": mutation_rate,
                "crossover_rate": crossover_rate,
                "elite_ratio": elite_ratio,
                "lof_operators_count": len(self.lof_operators),
                "common_operators_count": len(self.common_operators),
                "total_operators": len(self.lof_operators) + len(self.common_operators),
            },
        )

    def _get_operator_whitelist(self) -> List[str]:
        """获取LOF算子白名单

        白皮书依据: 第四章 4.1.18 - LOF算子白名单

        Returns:
            包含28个算子的列表（20个LOF专用 + 8个通用）

        Example:
            >>> miner = LOFFactorMiner()
            >>> operators = miner._get_operator_whitelist()
            >>> len(operators)
            28
        """
        return self.lof_operators + self.common_operators

    def _generate_random_expression(self, data_columns: List[str]) -> str:
        """生成随机因子表达式

        白皮书依据: 第四章 4.1.18 - LOF因子表达式生成

        使用LOF算子白名单生成随机因子表达式。70%概率使用LOF专用算子，
        30%概率使用通用算子。表达式复杂度为1-3层嵌套。

        Args:
            data_columns: 可用的数据列名列表

        Returns:
            因子表达式字符串

        Raises:
            ValueError: 当data_columns为空时

        Example:
            >>> miner = LOFFactorMiner()
            >>> expr = miner._generate_random_expression(['onmarket_price', 'offmarket_price'])
            >>> print(expr)
            'lof_onoff_price_spread(onmarket_price, offmarket_price)'
        """
        if not data_columns:
            raise ValueError("data_columns cannot be empty")

        # 70%概率使用LOF专用算子，30%概率使用通用算子
        if random.random() < 0.7:
            operator = random.choice(self.lof_operators)
        else:
            operator = random.choice(self.common_operators)

        # 根据算子类型生成表达式
        if operator in self.lof_operators:  # pylint: disable=no-else-return
            return self._generate_lof_expression(operator, data_columns)
        else:
            return self._generate_common_expression(operator, data_columns)

    def _generate_lof_expression(  # pylint: disable=too-many-branches,r0911
        self, operator: str, data_columns: List[str]
    ) -> str:  # pylint: disable=too-many-branches
        """生成LOF算子表达式

        Args:
            operator: LOF算子名称
            data_columns: 可用的数据列名列表

        Returns:
            LOF算子表达式字符串
        """
        # 场内外价差算子
        if operator == "lof_onoff_price_spread":  # pylint: disable=no-else-return
            return f"{operator}(onmarket_price, offmarket_price)"

        elif operator == "lof_transfer_arbitrage_opportunity":
            threshold = random.choice([0.01, 0.02, 0.03])
            return f"{operator}(onmarket_price, offmarket_price, {threshold})"

        elif operator == "lof_premium_discount_rate":
            return f"{operator}(onmarket_price, nav)"

        elif operator == "lof_onmarket_liquidity":
            window = random.choice([5, 10, 20])
            return f"{operator}(onmarket_volume, onmarket_turnover, {window})"

        elif operator == "lof_offmarket_liquidity":
            window = random.choice([5, 10, 20])
            return f"{operator}(subscription_amount, redemption_amount, {window})"

        # 基金分析算子
        elif operator == "lof_liquidity_stratification":
            return f"{operator}(onmarket_volume, subscription_amount, redemption_amount)"

        elif operator == "lof_investor_structure":
            return f"{operator}(institutional_holding, retail_holding)"

        elif operator == "lof_fund_manager_alpha":
            window = random.choice([20, 30, 60])
            return f"{operator}(returns, benchmark_returns, {window})"

        elif operator == "lof_fund_manager_style":
            return f"{operator}(holdings)"

        elif operator == "lof_holding_concentration":
            return f"{operator}(holdings)"

        # 性能算子
        elif operator == "lof_sector_allocation_shift":
            window = random.choice([10, 20, 30])
            return f"{operator}(sector_weights, {window})"

        elif operator == "lof_turnover_rate":
            window = random.choice([20, 30, 60])
            return f"{operator}(turnover, {window})"

        elif operator == "lof_performance_persistence":
            window = random.choice([20, 30, 60])
            return f"{operator}(returns, {window})"

        elif operator == "lof_expense_ratio_impact":
            return f"{operator}(returns, expense_ratio)"

        elif operator == "lof_dividend_yield_signal":
            return f"{operator}(dividend, nav)"

        elif operator == "lof_nav_momentum":
            window = random.choice([5, 10, 20])
            return f"{operator}(nav, {window})"

        elif operator == "lof_redemption_pressure":
            window = random.choice([5, 10, 20])
            return f"{operator}(redemption_amount, aum, {window})"

        elif operator == "lof_benchmark_tracking_quality":
            window = random.choice([20, 30, 60])
            return f"{operator}(returns, benchmark_returns, {window})"

        elif operator == "lof_market_impact_cost":
            return f"{operator}(volume, trade_size)"

        elif operator == "lof_cross_sectional_momentum":
            window = random.choice([5, 10, 20])
            return f"{operator}(returns, {window})"

        else:
            # 默认：使用第一个可用列
            col = random.choice(data_columns)
            return f"{operator}({col})"

    def _generate_common_expression(self, operator: str, data_columns: List[str]) -> str:
        """生成通用算子表达式

        Args:
            operator: 通用算子名称
            data_columns: 可用的数据列名列表

        Returns:
            通用算子表达式字符串
        """
        col = random.choice(data_columns)

        if operator == "rank":  # pylint: disable=no-else-return
            return f"rank({col})"

        elif operator in ["delay", "delta"]:
            period = random.choice([1, 2, 5, 10])
            return f"{operator}({col}, {period})"

        elif operator in ["ts_mean", "ts_std"]:
            window = random.choice([5, 10, 20, 30])
            return f"{operator}({col}, {window})"

        elif operator in ["correlation", "covariance"]:
            col2 = random.choice(data_columns)
            window = random.choice([10, 20, 30])
            return f"{operator}({col}, {col2}, {window})"

        elif operator == "regression_residual":
            col2 = random.choice(data_columns)
            window = random.choice([20, 30, 60])
            return f"{operator}({col}, {col2}, {window})"

        else:
            return f"{operator}({col})"

    def _evaluate_expression(self, expression: str, data: pd.DataFrame) -> Optional[pd.Series]:
        """评估因子表达式

        白皮书依据: 第四章 4.1.18 - LOF因子评估

        在LOF市场数据上评估因子表达式，返回因子值序列。

        Args:
            expression: 因子表达式字符串
            data: LOF市场数据DataFrame

        Returns:
            因子值序列，如果评估失败则返回None

        Raises:
            OperatorError: 当算子执行失败时
            DataQualityError: 当数据质量不足时

        Example:
            >>> miner = LOFFactorMiner()
            >>> data = pd.DataFrame(...)
            >>> result = miner._evaluate_expression('lof_onoff_price_spread(onmarket_price, offmarket_price)', data)
        """
        try:
            # 解析表达式：提取算子名称和参数
            if "(" not in expression:
                # 简单列引用
                if expression in data.columns:  # pylint: disable=no-else-return
                    return data[expression]
                else:
                    logger.warning(f"Column not found: {expression}")
                    return None

            # 提取算子名称和参数
            operator_name = expression.split("(")[0]
            params_str = expression.split("(")[1].rstrip(")")
            params = [p.strip() for p in params_str.split(",")]

            # 从算子注册表获取算子函数
            if operator_name not in self.operator_registry:
                logger.warning(f"Operator not found: {operator_name}")
                return None

            operator_func = self.operator_registry[operator_name]

            # 准备参数：列引用或数值
            args = []
            for param in params:
                if param in data.columns:
                    args.append(data[param])
                else:
                    try:
                        # 尝试转换为整数
                        args.append(int(param))
                    except ValueError:
                        try:
                            # 尝试转换为浮点数
                            args.append(float(param))
                        except ValueError:
                            logger.warning(f"Invalid parameter: {param}")
                            return None

            # 调用算子函数
            result = operator_func(*args)

            # 验证结果
            if result is None:
                return None

            # 数据质量检查
            self._validate_result(result)

            return result

        except (OperatorError, DataQualityError, ValueError) as e:
            logger.warning(f"Expression evaluation failed: {expression}, error: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error evaluating expression: {expression}, error: {e}")
            raise OperatorError(f"Failed to evaluate expression: {expression}") from e

    def _validate_result(self, result: pd.Series) -> None:
        """验证因子计算结果的数据质量

        白皮书依据: 第四章 4.1.18 - 数据质量要求

        Args:
            result: 因子值序列

        Raises:
            DataQualityError: 当NaN比例超过50%时
        """
        if result is None or len(result) == 0:
            raise DataQualityError("Result is None or empty")

        # 替换无穷值为NaN
        result = result.replace([np.inf, -np.inf], np.nan)

        # 检查NaN比例
        nan_ratio = result.isna().sum() / len(result)
        if nan_ratio > 0.5:
            raise DataQualityError(f"Too many NaN values in result: {nan_ratio:.2%} > 50%")

    def _build_operator_registry(self) -> Dict[str, Any]:
        """构建算子注册表

        白皮书依据: 第四章 4.1.18 - LOF算子注册

        Returns:
            算子名称到函数的映射字典

        Raises:
            FactorMiningError: 当算子注册失败时
        """
        registry = {}

        try:
            # 注册LOF算子（20个）
            lof_ops = LOFOperators()
            for op_name in self.lof_operators:
                registry[op_name] = lof_ops.get_operator(op_name)

            # 注册通用算子（8个）
            registry["rank"] = lambda x: x.rank(pct=True)
            registry["delay"] = lambda x, n: x.shift(n)
            registry["delta"] = lambda x, n: x.diff(n)
            registry["ts_mean"] = lambda x, n: x.rolling(window=n).mean()
            registry["ts_std"] = lambda x, n: x.rolling(window=n).std()
            registry["correlation"] = lambda x, y, n: x.rolling(window=n).corr(y)
            registry["covariance"] = lambda x, y, n: x.rolling(window=n).cov(y)
            registry["regression_residual"] = lambda x, y, n: x - x.rolling(window=n).apply(
                lambda vals: np.polyfit(range(len(vals)), vals, 1)[0] * (len(vals) - 1)
                + np.polyfit(range(len(vals)), vals, 1)[1]
            )

            logger.info(
                "Operator registry built",
                extra={
                    "component": "LOFFactorMiner",
                    "action": "build_registry",
                    "total_operators": len(registry),
                    "lof_operators": len([k for k in registry if k.startswith("lof_")]),
                    "common_operators": len([k for k in registry if not k.startswith("lof_")]),
                },
            )
            return registry

        except Exception as e:
            logger.error(
                "Failed to build operator registry",
                extra={
                    "component": "LOFFactorMiner",
                    "action": "build_registry",
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
            )
            raise FactorMiningError("Failed to build operator registry") from e
