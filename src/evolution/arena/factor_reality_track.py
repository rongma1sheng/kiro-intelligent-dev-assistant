"""
因子Reality Track测试轨道 (Factor Reality Track)

白皮书依据: 第四章 4.2.1 因子Arena - Reality Track
"""

import pandas as pd
from loguru import logger

from src.evolution.arena.data_models import Factor, RealityTrackResult
from src.evolution.arena.factor_performance_monitor import FactorPerformanceMonitor


class FactorRealityTrack:
    """因子Reality Track测试轨道

    白皮书依据: 第四章 4.2.1 因子Arena - Reality Track

    职责:
    1. 使用真实历史数据测试因子
    2. 计算IC、IR、夏普比率等指标
    3. 评估因子在正常市场环境下的表现

    测试标准:
    - IC > 0.03: 有效因子
    - IR > 1.0: 稳定因子
    - Sharpe > 1.0: 优质因子
    """

    def __init__(self, performance_monitor: FactorPerformanceMonitor):
        """初始化Reality Track

        Args:
            performance_monitor: 性能监控器实例

        Raises:
            TypeError: 当performance_monitor类型错误时
        """
        if not isinstance(performance_monitor, FactorPerformanceMonitor):
            raise TypeError("performance_monitor必须是FactorPerformanceMonitor类型")

        self.performance_monitor = performance_monitor
        logger.info("初始化FactorRealityTrack")

    async def test_factor(
        self, factor: Factor, historical_data: pd.DataFrame, returns_data: pd.Series
    ) -> RealityTrackResult:
        """测试因子在Reality Track上的表现

        白皮书依据: 第四章 4.2.1 因子Arena - Reality Track测试

        Args:
            factor: 待测试因子
            historical_data: 历史数据 (包含OHLCV等)
            returns_data: 收益率数据

        Returns:
            Reality Track测试结果

        Raises:
            ValueError: 当输入数据无效时
        """
        logger.info(f"开始Reality Track测试: {factor.id}")

        # 验证输入数据
        self._validate_input_data(historical_data, returns_data)

        # 计算因子值
        factor_values = self._evaluate_factor_expression(factor.expression, historical_data)

        # 对齐因子值和收益率
        factor_values, returns_data = self._align_data(factor_values, returns_data)

        # 计算性能指标
        ic = self.performance_monitor.calculate_ic(factor_values, returns_data)
        ir = self.performance_monitor.calculate_ir(factor_values, returns_data)
        sharpe_ratio = self.performance_monitor.calculate_sharpe_ratio(returns_data)
        max_drawdown = self.performance_monitor.calculate_max_drawdown(returns_data)
        win_rate = self.performance_monitor.calculate_win_rate(factor_values, returns_data)

        # 计算年化收益率
        annual_return = self._calculate_annual_return(returns_data)

        # 计算Reality评分
        reality_score = self.performance_monitor.calculate_reality_score(
            ic=ic, ir=ir, sharpe_ratio=sharpe_ratio, max_drawdown=max_drawdown, win_rate=win_rate
        )

        # 创建测试结果
        result = RealityTrackResult(
            ic=ic,
            ir=ir,
            sharpe_ratio=sharpe_ratio,
            annual_return=annual_return,
            max_drawdown=max_drawdown,
            win_rate=win_rate,
            reality_score=reality_score,
            test_period_days=len(returns_data),
            sample_count=len(factor_values),
        )

        logger.info(
            f"Reality Track测试完成: {factor.id}, "
            f"IC={ic:.4f}, IR={ir:.4f}, Sharpe={sharpe_ratio:.4f}, "
            f"Score={reality_score:.4f}"
        )

        return result

    def _validate_input_data(self, historical_data: pd.DataFrame, returns_data: pd.Series) -> None:
        """验证输入数据有效性

        Args:
            historical_data: 历史数据
            returns_data: 收益率数据

        Raises:
            ValueError: 当数据无效时
        """
        if historical_data.empty:
            raise ValueError("历史数据不能为空")

        if returns_data.empty:
            raise ValueError("收益率数据不能为空")

        if len(historical_data) < 20:
            raise ValueError(f"历史数据样本不足，至少需要20个样本，当前: {len(historical_data)}")

        if len(returns_data) < 20:
            raise ValueError(f"收益率数据样本不足，至少需要20个样本，当前: {len(returns_data)}")

        # 检查必需的列
        required_columns = ["close", "volume"]
        missing_columns = [col for col in required_columns if col not in historical_data.columns]
        if missing_columns:
            raise ValueError(f"历史数据缺少必需的列: {missing_columns}")

    def _evaluate_factor_expression(self, expression: str, historical_data: pd.DataFrame) -> pd.Series:
        """评估因子表达式

        白皮书依据: 第四章 4.1 因子表达式评估

        Args:
            expression: 因子表达式
            historical_data: 历史数据

        Returns:
            因子值序列

        Raises:
            ValueError: 当表达式无效时
        """
        try:
            # 简化实现: 使用close价格作为因子值
            # 实际实现中应该解析和执行因子表达式
            # 这里为了演示，使用收益率作为因子值
            factor_values = historical_data["close"].pct_change()

            # 移除NaN值
            factor_values = factor_values.dropna()

            if len(factor_values) == 0:
                raise ValueError("因子值计算结果为空")

            return factor_values

        except Exception as e:
            logger.error(f"因子表达式评估失败: {expression}, 错误: {e}")
            raise ValueError(f"因子表达式评估失败: {e}") from e

    def _align_data(self, factor_values: pd.Series, returns_data: pd.Series) -> tuple[pd.Series, pd.Series]:
        """对齐因子值和收益率数据

        Args:
            factor_values: 因子值序列
            returns_data: 收益率序列

        Returns:
            对齐后的(因子值, 收益率)元组

        Raises:
            ValueError: 当无法对齐数据时
        """
        # 找到共同的索引
        common_index = factor_values.index.intersection(returns_data.index)

        if len(common_index) == 0:
            raise ValueError("因子值和收益率没有共同的索引")

        if len(common_index) < 20:
            raise ValueError(f"对齐后的样本数量不足，至少需要20个样本，当前: {len(common_index)}")

        # 对齐数据
        factor_aligned = factor_values.loc[common_index]
        returns_aligned = returns_data.loc[common_index]

        # 移除NaN值
        valid_mask = ~(factor_aligned.isna() | returns_aligned.isna())
        factor_clean = factor_aligned[valid_mask]
        returns_clean = returns_aligned[valid_mask]

        if len(factor_clean) < 20:
            raise ValueError(f"清洗后的样本数量不足，至少需要20个样本，当前: {len(factor_clean)}")

        return factor_clean, returns_clean

    def _calculate_annual_return(self, returns_data: pd.Series, periods_per_year: int = 252) -> float:
        """计算年化收益率

        Args:
            returns_data: 收益率序列
            periods_per_year: 每年交易周期数

        Returns:
            年化收益率
        """
        if len(returns_data) == 0:
            return 0.0

        # 计算累计收益
        cumulative_return = (1 + returns_data).prod() - 1

        # 计算年化收益率
        num_periods = len(returns_data)
        years = num_periods / periods_per_year

        if years <= 0:
            return 0.0

        annual_return = (1 + cumulative_return) ** (1 / years) - 1

        return float(annual_return)
