"""组合风险因子挖掘器

白皮书依据: 第四章 4.1.1 专业风险因子挖掘系统 - 组合风险

该模块实现组合风险因子挖掘器，检测持仓组合的系统性风险：
1. 持仓相关性收敛检测
2. 组合VaR超限检测
3. 行业集中度检测
4. 尾部风险暴露检测
"""

from datetime import datetime
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
from loguru import logger

from src.evolution.risk_mining.risk_factor import RiskFactor


class PortfolioRiskFactorMiner:
    """组合风险因子挖掘器

    白皮书依据: 第四章 4.1.1 专业风险因子挖掘系统 - 组合风险

    检测持仓组合的系统性风险，包括：
    - 持仓相关性收敛：检测持仓之间相关性是否过高
    - 组合VaR超限：检测组合风险价值是否超过阈值
    - 行业集中度：检测是否过度集中在某个行业
    - 尾部风险暴露：检测极端情况下的潜在损失

    Attributes:
        correlation_threshold: 相关性阈值，默认0.85
        var_threshold: VaR阈值，默认0.05 (5%)
        concentration_threshold: 集中度阈值，默认0.3 (30%)
        tail_risk_threshold: 尾部风险阈值，默认0.1 (10%)
    """

    def __init__(
        self,
        correlation_threshold: float = 0.85,
        var_threshold: float = 0.05,
        concentration_threshold: float = 0.3,
        tail_risk_threshold: float = 0.1,
    ):
        """初始化组合风险因子挖掘器

        Args:
            correlation_threshold: 相关性阈值，范围 [0, 1]
            var_threshold: VaR阈值，范围 [0, 1]
            concentration_threshold: 集中度阈值，范围 [0, 1]
            tail_risk_threshold: 尾部风险阈值，范围 [0, 1]

        Raises:
            ValueError: 当参数不在有效范围时
        """
        # 参数验证
        if not 0 <= correlation_threshold <= 1:
            raise ValueError(f"correlation_threshold必须在[0, 1]范围内，当前值: {correlation_threshold}")

        if not 0 <= var_threshold <= 1:
            raise ValueError(f"var_threshold必须在[0, 1]范围内，当前值: {var_threshold}")

        if not 0 <= concentration_threshold <= 1:
            raise ValueError(f"concentration_threshold必须在[0, 1]范围内，当前值: {concentration_threshold}")

        if not 0 <= tail_risk_threshold <= 1:
            raise ValueError(f"tail_risk_threshold必须在[0, 1]范围内，当前值: {tail_risk_threshold}")

        self.correlation_threshold = correlation_threshold
        self.var_threshold = var_threshold
        self.concentration_threshold = concentration_threshold
        self.tail_risk_threshold = tail_risk_threshold

        logger.info(
            f"初始化PortfolioRiskFactorMiner: "
            f"correlation_threshold={correlation_threshold}, "
            f"var_threshold={var_threshold}, "
            f"concentration_threshold={concentration_threshold}, "
            f"tail_risk_threshold={tail_risk_threshold}"
        )

    async def mine_portfolio_risk(
        self, portfolio: Dict[str, float], returns_data: pd.DataFrame, sector_mapping: Optional[Dict[str, str]] = None
    ) -> List[RiskFactor]:
        """挖掘组合风险因子

        白皮书依据: 第四章 4.1.1 专业风险因子挖掘系统 - 组合风险

        Args:
            portfolio: 持仓组合 {symbol: weight}，权重之和应为1.0
            returns_data: 收益率数据，索引为日期，列为股票代码
            sector_mapping: 行业映射 {symbol: sector}，可选

        Returns:
            风险因子列表

        Raises:
            ValueError: 当portfolio为空时
            ValueError: 当returns_data为空时
            ValueError: 当权重之和不为1.0时
        """
        if not portfolio:
            raise ValueError("portfolio不能为空")

        if returns_data.empty:
            raise ValueError("returns_data不能为空")

        # 验证权重之和
        total_weight = sum(portfolio.values())
        if not np.isclose(total_weight, 1.0, atol=0.01):
            raise ValueError(f"权重之和必须为1.0，当前值: {total_weight:.4f}")

        factors = []
        timestamp = datetime.now()

        # 检测1: 持仓相关性收敛
        correlation_factor = self._detect_correlation_convergence(portfolio, returns_data, timestamp)
        if correlation_factor:
            factors.append(correlation_factor)

        # 检测2: 组合VaR超限
        var_factor = self._detect_var_breach(portfolio, returns_data, timestamp)
        if var_factor:
            factors.append(var_factor)

        # 检测3: 行业集中度
        if sector_mapping:
            concentration_factor = self._detect_sector_concentration(portfolio, sector_mapping, timestamp)
            if concentration_factor:
                factors.append(concentration_factor)

        # 检测4: 尾部风险暴露
        tail_risk_factor = self._detect_tail_risk(portfolio, returns_data, timestamp)
        if tail_risk_factor:
            factors.append(tail_risk_factor)

        if factors:
            logger.info(f"检测到{len(factors)}个组合风险因子: " f"{[f.metadata.get('risk_type') for f in factors]}")

        return factors

    def _detect_correlation_convergence(
        self, portfolio: Dict[str, float], returns_data: pd.DataFrame, timestamp: datetime
    ) -> Optional[RiskFactor]:
        """检测持仓相关性收敛

        白皮书依据: 第四章 4.1.1 - 持仓相关性收敛检测

        当持仓之间的平均相关性超过阈值时，表示组合分散化不足，
        系统性风险增加。

        Args:
            portfolio: 持仓组合
            returns_data: 收益率数据
            timestamp: 时间戳

        Returns:
            风险因子（如果检测到）
        """
        # 获取持仓标的的收益率
        symbols = list(portfolio.keys())
        available_symbols = [s for s in symbols if s in returns_data.columns]

        if len(available_symbols) < 2:
            logger.debug("持仓标的少于2个，无法计算相关性")
            return None

        # 计算相关性矩阵
        portfolio_returns = returns_data[available_symbols]
        correlation_matrix = portfolio_returns.corr()

        # 计算平均相关性（排除对角线）
        n = len(available_symbols)
        if n < 2:
            return None

        # 提取上三角矩阵（排除对角线）
        upper_triangle = np.triu(correlation_matrix.values, k=1)
        correlations = upper_triangle[upper_triangle != 0]

        if len(correlations) == 0:
            return None

        avg_correlation = np.mean(correlations)
        max_correlation = np.max(correlations)

        # 判断是否超过阈值
        if avg_correlation > self.correlation_threshold:
            # 计算风险值：超过阈值的程度
            risk_value = min(1.0, avg_correlation / self.correlation_threshold)

            # 计算置信度：基于样本数量
            confidence = min(1.0, len(correlations) / 100)

            logger.warning(
                f"检测到持仓相关性收敛: "
                f"平均相关性={avg_correlation:.4f}, "
                f"最大相关性={max_correlation:.4f}, "
                f"阈值={self.correlation_threshold}"
            )

            return RiskFactor(
                factor_type="portfolio",
                symbol="PORTFOLIO",
                risk_value=risk_value,
                confidence=confidence,
                timestamp=timestamp,
                metadata={
                    "risk_type": "correlation_convergence",
                    "avg_correlation": float(avg_correlation),
                    "max_correlation": float(max_correlation),
                    "threshold": self.correlation_threshold,
                    "num_holdings": len(available_symbols),
                },
            )

        return None

    def _detect_var_breach(
        self, portfolio: Dict[str, float], returns_data: pd.DataFrame, timestamp: datetime
    ) -> Optional[RiskFactor]:
        """检测组合VaR超限

        白皮书依据: 第四章 4.1.1 - 组合VaR超限检测

        计算组合的风险价值(VaR)，当VaR超过阈值时触发风险因子。
        使用历史模拟法计算95%置信度的VaR。

        Args:
            portfolio: 持仓组合
            returns_data: 收益率数据
            timestamp: 时间戳

        Returns:
            风险因子（如果检测到）
        """
        # 获取持仓标的的收益率
        symbols = list(portfolio.keys())
        available_symbols = [s for s in symbols if s in returns_data.columns]

        if not available_symbols:
            logger.debug("没有可用的收益率数据")
            return None

        # 计算组合收益率
        portfolio_returns = pd.Series(0.0, index=returns_data.index)
        for symbol in available_symbols:
            weight = portfolio.get(symbol, 0.0)
            portfolio_returns += returns_data[symbol] * weight

        # 计算VaR (95%置信度)
        var_95 = np.percentile(portfolio_returns, 5)
        var_95_abs = abs(var_95)

        # 判断是否超过阈值
        if var_95_abs > self.var_threshold:
            # 计算风险值：超过阈值的程度
            risk_value = min(1.0, var_95_abs / self.var_threshold)

            # 计算置信度：基于样本数量
            confidence = min(1.0, len(portfolio_returns) / 252)

            logger.warning(f"检测到组合VaR超限: " f"VaR(95%)={var_95_abs:.4f}, " f"阈值={self.var_threshold}")

            return RiskFactor(
                factor_type="portfolio",
                symbol="PORTFOLIO",
                risk_value=risk_value,
                confidence=confidence,
                timestamp=timestamp,
                metadata={
                    "risk_type": "var_breach",
                    "var_95": float(var_95_abs),
                    "threshold": self.var_threshold,
                    "num_holdings": len(available_symbols),
                },
            )

        return None

    def _detect_sector_concentration(
        self, portfolio: Dict[str, float], sector_mapping: Dict[str, str], timestamp: datetime
    ) -> Optional[RiskFactor]:
        """检测行业集中度

        白皮书依据: 第四章 4.1.1 - 行业集中度检测

        计算各行业的权重占比，当某个行业权重超过阈值时触发风险因子。

        Args:
            portfolio: 持仓组合
            sector_mapping: 行业映射
            timestamp: 时间戳

        Returns:
            风险因子（如果检测到）
        """
        # 计算各行业权重
        sector_weights: Dict[str, float] = {}
        for symbol, weight in portfolio.items():
            sector = sector_mapping.get(symbol, "UNKNOWN")
            sector_weights[sector] = sector_weights.get(sector, 0.0) + weight

        # 找出最大行业权重
        if not sector_weights:
            return None

        max_sector = max(sector_weights, key=sector_weights.get)
        max_weight = sector_weights[max_sector]

        # 判断是否超过阈值
        if max_weight > self.concentration_threshold:
            # 计算风险值：超过阈值的程度
            risk_value = min(1.0, max_weight / self.concentration_threshold)

            # 计算置信度：基于行业数量
            confidence = min(1.0, len(sector_weights) / 10)

            logger.warning(
                f"检测到行业集中度过高: "
                f"行业={max_sector}, "
                f"权重={max_weight:.4f}, "
                f"阈值={self.concentration_threshold}"
            )

            return RiskFactor(
                factor_type="portfolio",
                symbol="PORTFOLIO",
                risk_value=risk_value,
                confidence=confidence,
                timestamp=timestamp,
                metadata={
                    "risk_type": "sector_concentration",
                    "max_sector": max_sector,
                    "max_weight": float(max_weight),
                    "threshold": self.concentration_threshold,
                    "sector_weights": {k: float(v) for k, v in sector_weights.items()},
                },
            )

        return None

    def _detect_tail_risk(
        self, portfolio: Dict[str, float], returns_data: pd.DataFrame, timestamp: datetime
    ) -> Optional[RiskFactor]:
        """检测尾部风险暴露

        白皮书依据: 第四章 4.1.1 - 尾部风险暴露检测

        计算组合的条件风险价值(CVaR)，衡量极端情况下的潜在损失。
        CVaR是VaR之外的平均损失。

        Args:
            portfolio: 持仓组合
            returns_data: 收益率数据
            timestamp: 时间戳

        Returns:
            风险因子（如果检测到）
        """
        # 获取持仓标的的收益率
        symbols = list(portfolio.keys())
        available_symbols = [s for s in symbols if s in returns_data.columns]

        if not available_symbols:
            logger.debug("没有可用的收益率数据")
            return None

        # 计算组合收益率
        portfolio_returns = pd.Series(0.0, index=returns_data.index)
        for symbol in available_symbols:
            weight = portfolio.get(symbol, 0.0)
            portfolio_returns += returns_data[symbol] * weight

        # 计算CVaR (95%置信度)
        var_95 = np.percentile(portfolio_returns, 5)
        tail_returns = portfolio_returns[portfolio_returns <= var_95]

        if len(tail_returns) == 0:
            return None

        cvar_95 = abs(tail_returns.mean())

        # 判断是否超过阈值
        if cvar_95 > self.tail_risk_threshold:
            # 计算风险值：超过阈值的程度
            risk_value = min(1.0, cvar_95 / self.tail_risk_threshold)

            # 计算置信度：基于样本数量
            confidence = min(1.0, len(portfolio_returns) / 252)

            logger.warning(f"检测到尾部风险暴露: " f"CVaR(95%)={cvar_95:.4f}, " f"阈值={self.tail_risk_threshold}")

            return RiskFactor(
                factor_type="portfolio",
                symbol="PORTFOLIO",
                risk_value=risk_value,
                confidence=confidence,
                timestamp=timestamp,
                metadata={
                    "risk_type": "tail_risk",
                    "cvar_95": float(cvar_95),
                    "var_95": float(abs(var_95)),
                    "threshold": self.tail_risk_threshold,
                    "num_holdings": len(available_symbols),
                },
            )

        return None
