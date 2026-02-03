"""
跨市场测试轨道 (Cross-Market Track)

白皮书依据: 第四章 4.2.1 因子Arena - Cross-Market Track
"""

from typing import Dict

import numpy as np
import pandas as pd
from loguru import logger

from src.evolution.arena.data_models import CrossMarketResult, Factor, MarketType
from src.evolution.arena.factor_performance_monitor import FactorPerformanceMonitor


class CrossMarketTrack:
    """跨市场测试轨道

    白皮书依据: 第四章 4.2.1 因子Arena - Cross-Market Track

    职责:
    1. 测试因子在不同市场的适应性
    2. 评估因子的跨市场泛化能力
    3. 识别市场特定的因子偏差

    测试市场:
    - A股市场 (A_STOCK)
    - 美股市场 (US_STOCK)
    - 加密货币市场 (CRYPTO)
    - 港股市场 (HK_STOCK)
    """

    def __init__(self, performance_monitor: FactorPerformanceMonitor):
        """初始化Cross-Market Track

        Args:
            performance_monitor: 性能监控器实例

        Raises:
            TypeError: 当performance_monitor类型错误时
        """
        if not isinstance(performance_monitor, FactorPerformanceMonitor):
            raise TypeError("performance_monitor必须是FactorPerformanceMonitor类型")

        self.performance_monitor = performance_monitor
        logger.info("初始化CrossMarketTrack")

    async def test_factor(
        self, factor: Factor, market_data: Dict[MarketType, pd.DataFrame], market_returns: Dict[MarketType, pd.Series]
    ) -> CrossMarketResult:
        """测试因子在Cross-Market Track上的表现

        白皮书依据: 第四章 4.2.1 因子Arena - Cross-Market Track测试

        Args:
            factor: 待测试因子
            market_data: 各市场历史数据 {market_type: data}
            market_returns: 各市场收益率数据 {market_type: returns}

        Returns:
            Cross-Market Track测试结果

        Raises:
            ValueError: 当输入数据无效时
        """
        logger.info(f"开始Cross-Market Track测试: {factor.id}")

        # 验证输入数据
        self._validate_input_data(market_data, market_returns)

        # 测试各个市场
        market_scores = {}

        # 1. A股市场
        if MarketType.A_STOCK in market_data:
            a_stock_score = await self._test_market(
                factor, MarketType.A_STOCK, market_data[MarketType.A_STOCK], market_returns[MarketType.A_STOCK]
            )
            market_scores["a_stock"] = a_stock_score
        else:
            market_scores["a_stock"] = 0.5  # 默认中性评分

        # 2. 美股市场
        if MarketType.US_STOCK in market_data:
            us_stock_score = await self._test_market(
                factor, MarketType.US_STOCK, market_data[MarketType.US_STOCK], market_returns[MarketType.US_STOCK]
            )
            market_scores["us_stock"] = us_stock_score
        else:
            market_scores["us_stock"] = 0.5

        # 3. 加密货币市场
        if MarketType.CRYPTO in market_data:
            crypto_score = await self._test_market(
                factor, MarketType.CRYPTO, market_data[MarketType.CRYPTO], market_returns[MarketType.CRYPTO]
            )
            market_scores["crypto"] = crypto_score
        else:
            market_scores["crypto"] = 0.5

        # 4. 港股市场
        if MarketType.HK_STOCK in market_data:
            hk_stock_score = await self._test_market(
                factor, MarketType.HK_STOCK, market_data[MarketType.HK_STOCK], market_returns[MarketType.HK_STOCK]
            )
            market_scores["hk_stock"] = hk_stock_score
        else:
            market_scores["hk_stock"] = 0.5

        # 计算适应性评分
        adaptability_score = self._calculate_adaptability_score(market_scores)

        # 计算Cross-Market综合评分
        cross_market_score = self.performance_monitor.calculate_cross_market_score(market_scores)

        # 创建测试结果
        result = CrossMarketResult(
            a_stock_score=market_scores["a_stock"],
            us_stock_score=market_scores["us_stock"],
            crypto_score=market_scores["crypto"],
            hk_stock_score=market_scores["hk_stock"],
            adaptability_score=adaptability_score,
            cross_market_score=cross_market_score,
            markets_tested=len([m for m in market_data.keys()]),  # pylint: disable=r1721
        )

        logger.info(
            f"Cross-Market Track测试完成: {factor.id}, "
            f"适应性={adaptability_score:.4f}, Score={cross_market_score:.4f}"
        )

        return result

    def _validate_input_data(
        self, market_data: Dict[MarketType, pd.DataFrame], market_returns: Dict[MarketType, pd.Series]
    ) -> None:
        """验证输入数据有效性

        Args:
            market_data: 各市场历史数据
            market_returns: 各市场收益率数据

        Raises:
            ValueError: 当数据无效时
        """
        if not market_data:
            raise ValueError("市场数据不能为空")

        if not market_returns:
            raise ValueError("市场收益率数据不能为空")

        if len(market_data) != len(market_returns):
            raise ValueError(f"市场数据和收益率数据数量不一致: {len(market_data)} vs {len(market_returns)}")

        # 验证每个市场的数据
        for market_type in market_data.keys():
            if market_type not in market_returns:
                raise ValueError(f"缺少市场 {market_type.value} 的收益率数据")

            data = market_data[market_type]
            returns = market_returns[market_type]

            if data.empty:
                raise ValueError(f"市场 {market_type.value} 的历史数据为空")

            if returns.empty:
                raise ValueError(f"市场 {market_type.value} 的收益率数据为空")

            if len(data) < 20:
                raise ValueError(
                    f"市场 {market_type.value} 的历史数据样本不足，" f"至少需要20个样本，当前: {len(data)}"
                )

            required_columns = ["close", "volume"]
            missing_columns = [col for col in required_columns if col not in data.columns]
            if missing_columns:
                raise ValueError(f"市场 {market_type.value} 的历史数据缺少必需的列: {missing_columns}")

    async def _test_market(
        self, factor: Factor, market_type: MarketType, historical_data: pd.DataFrame, returns_data: pd.Series
    ) -> float:
        """测试因子在特定市场的表现

        白皮书依据: 第四章 4.2.1 因子Arena - 单市场测试

        Args:
            factor: 待测试因子
            market_type: 市场类型
            historical_data: 历史数据
            returns_data: 收益率数据

        Returns:
            市场评分 [0, 1]
        """
        logger.info(f"测试市场: {market_type.value}")

        try:
            # 计算因子值
            factor_values = self._evaluate_factor_expression(factor.expression, historical_data)

            # 对齐数据
            factor_values, returns_data = self._align_data(factor_values, returns_data)

            # 计算IC
            ic = self.performance_monitor.calculate_ic(factor_values, returns_data)

            # 计算夏普比率
            sharpe_ratio = self.performance_monitor.calculate_sharpe_ratio(returns_data)

            # 计算市场评分
            # 评分公式: score = abs(IC) * 0.6 + max(Sharpe, 0) / 2.0 * 0.4
            ic_norm = min(abs(ic) / 0.15, 1.0)  # IC > 0.15视为满分
            sharpe_norm = min(max(sharpe_ratio, 0) / 2.0, 1.0)  # Sharpe > 2.0视为满分

            market_score = ic_norm * 0.6 + sharpe_norm * 0.4

            logger.info(
                f"市场 {market_type.value} 测试完成: "
                f"IC={ic:.4f}, Sharpe={sharpe_ratio:.4f}, Score={market_score:.4f}"
            )

            return float(np.clip(market_score, 0, 1))

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"市场 {market_type.value} 测试失败: {e}")
            return 0.5  # 返回中性评分

    def _evaluate_factor_expression(self, expression: str, historical_data: pd.DataFrame) -> pd.Series:
        """评估因子表达式"""
        try:
            # 简化实现: 使用收益率作为因子值
            factor_values = historical_data["close"].pct_change()
            factor_values = factor_values.dropna()

            if len(factor_values) == 0:
                raise ValueError("因子值计算结果为空")

            return factor_values

        except Exception as e:
            logger.error(f"因子表达式评估失败: {expression}, 错误: {e}")
            raise ValueError(f"因子表达式评估失败: {e}") from e

    def _align_data(self, factor_values: pd.Series, returns_data: pd.Series) -> tuple[pd.Series, pd.Series]:
        """对齐因子值和收益率数据"""
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

    def _calculate_adaptability_score(self, market_scores: Dict[str, float]) -> float:
        """计算跨市场适应性评分

        白皮书依据: 第四章 4.2.1 因子Arena - 适应性评分

        适应性评分 = 1 - std(market_scores) / mean(market_scores)

        评分越高，表示因子在不同市场的表现越稳定

        Args:
            market_scores: 各市场评分

        Returns:
            适应性评分 [0, 1]
        """
        if not market_scores:
            return 0.0

        scores = list(market_scores.values())

        mean_score = np.mean(scores)
        std_score = np.std(scores)

        if mean_score == 0:
            return 0.0

        # 适应性评分: 标准差越小，适应性越好
        adaptability = 1 - std_score / mean_score

        return float(np.clip(adaptability, 0, 1))
