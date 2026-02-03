"""
Greeks Engine - 期权定价与Greeks计算引擎

白皮书依据: 第三章 3.3 衍生品管道 - Greeks Engine
版本: v1.0.0
作者: MIA Team
日期: 2026-01-22

功能:
1. Black-Scholes期权定价
2. Greeks计算 (Delta, Gamma, Vega, Theta, Rho)
3. 隐含波动率求解
4. 批量计算优化

性能要求:
- 单期权计算延迟: P99 < 50ms
- 期权链批量计算: > 100个/秒
- 隐含波动率收敛: < 10次迭代
"""

import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional

import numpy as np
from loguru import logger
from scipy.stats import norm


class OptionType(Enum):
    """期权类型"""

    CALL = "call"
    PUT = "put"


@dataclass
class OptionContract:
    """期权合约数据结构

    Attributes:
        symbol: 期权代码
        underlying_price: 标的价格
        strike_price: 行权价
        time_to_maturity: 到期时间（年）
        risk_free_rate: 无风险利率
        volatility: 波动率
        option_type: 期权类型（看涨/看跌）
        dividend_yield: 股息率，默认0
    """

    symbol: str
    underlying_price: float
    strike_price: float
    time_to_maturity: float
    risk_free_rate: float
    volatility: float
    option_type: OptionType
    dividend_yield: float = 0.0

    def __post_init__(self):
        """验证参数合理性"""
        if self.underlying_price <= 0:
            raise ValueError(f"标的价格必须 > 0，当前: {self.underlying_price}")

        if self.strike_price <= 0:
            raise ValueError(f"行权价必须 > 0，当前: {self.strike_price}")

        if self.time_to_maturity <= 0:
            raise ValueError(f"到期时间必须 > 0，当前: {self.time_to_maturity}")

        if self.volatility < 0:
            raise ValueError(f"波动率必须 >= 0，当前: {self.volatility}")


@dataclass
class Greeks:
    """Greeks指标数据结构

    Attributes:
        delta: Delta (价格敏感度)
        gamma: Gamma (Delta变化率)
        vega: Vega (波动率敏感度)
        theta: Theta (时间衰减)
        rho: Rho (利率敏感度)
        option_price: 期权理论价格
    """

    delta: float
    gamma: float
    vega: float
    theta: float
    rho: float
    option_price: float


class GreeksEngine:
    """Greeks Engine - 期权定价与Greeks计算引擎

    白皮书依据: 第三章 3.3 衍生品管道 - Greeks Engine

    使用Black-Scholes模型进行期权定价和Greeks计算。
    支持欧式看涨和看跌期权。

    Attributes:
        cache_enabled: 是否启用结果缓存
        cache: 计算结果缓存
        stats: 性能统计
    """

    def __init__(self, cache_enabled: bool = True):
        """初始化Greeks Engine

        Args:
            cache_enabled: 是否启用结果缓存，默认True
        """
        self.cache_enabled = cache_enabled
        self.cache: Dict[str, Dict[str, Any]] = {}

        # 性能统计
        self.stats = {
            "total_calculations": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "avg_calculation_time_ms": 0.0,
            "total_calculation_time_ms": 0.0,
        }

        logger.info(f"GreeksEngine初始化完成 - cache_enabled={cache_enabled}")

    def calculate_option_price(self, contract: OptionContract) -> float:
        """计算期权理论价格

        白皮书依据: 第三章 3.3 衍生品管道 - Black-Scholes定价

        使用Black-Scholes公式计算欧式期权理论价格。

        Args:
            contract: 期权合约

        Returns:
            期权理论价格

        Raises:
            ValueError: 当参数不合理时
        """
        start_time = time.perf_counter()

        try:
            # 检查缓存
            cache_key = self._generate_cache_key(contract, "price")
            if self.cache_enabled and cache_key in self.cache:
                self.stats["cache_hits"] += 1
                return self.cache[cache_key]["value"]

            self.stats["cache_misses"] += 1

            # 计算d1和d2
            d1, d2 = self._calculate_d1_d2(contract)

            # 计算期权价格
            S = contract.underlying_price
            K = contract.strike_price
            T = contract.time_to_maturity
            r = contract.risk_free_rate
            q = contract.dividend_yield

            if contract.option_type == OptionType.CALL:
                # 看涨期权: C = S*e^(-qT)*N(d1) - K*e^(-rT)*N(d2)
                price = S * np.exp(-q * T) * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)
            else:
                # 看跌期权: P = K*e^(-rT)*N(-d2) - S*e^(-qT)*N(-d1)
                price = K * np.exp(-r * T) * norm.cdf(-d2) - S * np.exp(-q * T) * norm.cdf(-d1)

            # 更新缓存
            if self.cache_enabled:
                self.cache[cache_key] = {"value": price, "timestamp": time.time()}

            # 更新统计
            elapsed = (time.perf_counter() - start_time) * 1000
            self._update_stats(elapsed)

            return price

        except Exception as e:
            logger.error(f"计算期权价格失败: {e}")
            raise

    def calculate_greeks(self, contract: OptionContract) -> Greeks:
        """计算期权Greeks

        白皮书依据: 第三章 3.3 衍生品管道 - Greeks计算

        计算期权的所有Greeks指标：Delta, Gamma, Vega, Theta, Rho。

        Args:
            contract: 期权合约

        Returns:
            Greeks指标

        Raises:
            ValueError: 当参数不合理时
        """
        start_time = time.perf_counter()

        try:
            # 检查缓存
            cache_key = self._generate_cache_key(contract, "greeks")
            if self.cache_enabled and cache_key in self.cache:
                self.stats["cache_hits"] += 1
                return self.cache[cache_key]["value"]

            self.stats["cache_misses"] += 1

            # 计算期权价格
            option_price = self.calculate_option_price(contract)

            # 计算各个Greeks
            delta = self.calculate_delta(contract)
            gamma = self.calculate_gamma(contract)
            vega = self.calculate_vega(contract)
            theta = self.calculate_theta(contract)
            rho = self.calculate_rho(contract)

            greeks = Greeks(delta=delta, gamma=gamma, vega=vega, theta=theta, rho=rho, option_price=option_price)

            # 更新缓存
            if self.cache_enabled:
                self.cache[cache_key] = {"value": greeks, "timestamp": time.time()}

            # 更新统计
            elapsed = (time.perf_counter() - start_time) * 1000
            self._update_stats(elapsed)

            return greeks

        except Exception as e:
            logger.error(f"计算Greeks失败: {e}")
            raise

    def calculate_delta(self, contract: OptionContract) -> float:
        """计算Delta

        白皮书依据: 第三章 3.3 衍生品管道 - Delta计算

        Delta衡量期权价格对标的价格变化的敏感度。
        看涨期权: Delta ∈ [0, 1]
        看跌期权: Delta ∈ [-1, 0]

        Args:
            contract: 期权合约

        Returns:
            Delta值
        """
        d1, _ = self._calculate_d1_d2(contract)
        q = contract.dividend_yield
        T = contract.time_to_maturity

        if contract.option_type == OptionType.CALL:
            delta = np.exp(-q * T) * norm.cdf(d1)
        else:
            delta = -np.exp(-q * T) * norm.cdf(-d1)

        return delta

    def calculate_gamma(self, contract: OptionContract) -> float:
        """计算Gamma

        白皮书依据: 第三章 3.3 衍生品管道 - Gamma计算

        Gamma衡量Delta对标的价格变化的敏感度。
        Gamma对看涨和看跌期权相同，且总是非负。

        Args:
            contract: 期权合约

        Returns:
            Gamma值
        """
        d1, _ = self._calculate_d1_d2(contract)
        S = contract.underlying_price
        sigma = contract.volatility
        T = contract.time_to_maturity
        q = contract.dividend_yield

        gamma = (np.exp(-q * T) * norm.pdf(d1)) / (S * sigma * np.sqrt(T))

        return gamma

    def calculate_vega(self, contract: OptionContract) -> float:
        """计算Vega

        白皮书依据: 第三章 3.3 衍生品管道 - Vega计算

        Vega衡量期权价格对波动率变化的敏感度。
        Vega对看涨和看跌期权相同，且总是非负。

        Args:
            contract: 期权合约

        Returns:
            Vega值
        """
        d1, _ = self._calculate_d1_d2(contract)
        S = contract.underlying_price
        T = contract.time_to_maturity
        q = contract.dividend_yield

        vega = S * np.exp(-q * T) * norm.pdf(d1) * np.sqrt(T)

        return vega

    def calculate_theta(self, contract: OptionContract) -> float:
        """计算Theta

        白皮书依据: 第三章 3.3 衍生品管道 - Theta计算

        Theta衡量期权价格对时间流逝的敏感度（时间衰减）。
        Theta通常为负值（期权价值随时间衰减）。

        Args:
            contract: 期权合约

        Returns:
            Theta值
        """
        d1, d2 = self._calculate_d1_d2(contract)
        S = contract.underlying_price
        K = contract.strike_price
        T = contract.time_to_maturity
        r = contract.risk_free_rate
        sigma = contract.volatility
        q = contract.dividend_yield

        if contract.option_type == OptionType.CALL:
            theta = (
                -S * np.exp(-q * T) * norm.pdf(d1) * sigma / (2 * np.sqrt(T))
                - r * K * np.exp(-r * T) * norm.cdf(d2)
                + q * S * np.exp(-q * T) * norm.cdf(d1)
            )
        else:
            theta = (
                -S * np.exp(-q * T) * norm.pdf(d1) * sigma / (2 * np.sqrt(T))
                + r * K * np.exp(-r * T) * norm.cdf(-d2)
                - q * S * np.exp(-q * T) * norm.cdf(-d1)
            )

        return theta

    def calculate_rho(self, contract: OptionContract) -> float:
        """计算Rho

        白皮书依据: 第三章 3.3 衍生品管道 - Rho计算

        Rho衡量期权价格对无风险利率变化的敏感度。
        看涨期权: Rho > 0
        看跌期权: Rho < 0

        Args:
            contract: 期权合约

        Returns:
            Rho值
        """
        _, d2 = self._calculate_d1_d2(contract)
        K = contract.strike_price
        T = contract.time_to_maturity
        r = contract.risk_free_rate

        if contract.option_type == OptionType.CALL:
            rho = K * T * np.exp(-r * T) * norm.cdf(d2)
        else:
            rho = -K * T * np.exp(-r * T) * norm.cdf(-d2)

        return rho

    def calculate_implied_volatility(
        self, contract: OptionContract, market_price: float, max_iterations: int = 100, tolerance: float = 1e-6
    ) -> Optional[float]:
        """计算隐含波动率

        白皮书依据: 第三章 3.3 衍生品管道 - 隐含波动率计算

        使用Newton-Raphson迭代法求解隐含波动率。
        给定期权市场价格，反推波动率参数。

        Args:
            contract: 期权合约（volatility字段将被忽略）
            market_price: 期权市场价格
            max_iterations: 最大迭代次数，默认100
            tolerance: 收敛容差，默认1e-6

        Returns:
            隐含波动率，如果无法收敛则返回None

        Raises:
            ValueError: 当市场价格不合理时
        """
        if market_price <= 0:
            raise ValueError(f"市场价格必须 > 0，当前: {market_price}")

        # 初始猜测：使用简单估计
        # IV ≈ sqrt(2π/T) * (market_price / S)
        S = contract.underlying_price
        T = contract.time_to_maturity
        initial_guess = np.sqrt(2 * np.pi / T) * (market_price / S)

        # 确保初始猜测在合理范围内
        sigma = max(0.01, min(initial_guess, 5.0))

        for iteration in range(max_iterations):
            # 创建临时合约用于计算
            temp_contract = OptionContract(
                symbol=contract.symbol,
                underlying_price=contract.underlying_price,
                strike_price=contract.strike_price,
                time_to_maturity=contract.time_to_maturity,
                risk_free_rate=contract.risk_free_rate,
                volatility=sigma,
                option_type=contract.option_type,
                dividend_yield=contract.dividend_yield,
            )

            # 计算理论价格
            theoretical_price = self.calculate_option_price(temp_contract)

            # 计算价格差异
            price_diff = theoretical_price - market_price

            # 检查收敛
            if abs(price_diff) < tolerance:
                logger.debug(
                    f"隐含波动率收敛: {sigma:.6f}, " f"迭代次数: {iteration + 1}, " f"价格误差: {price_diff:.6f}"
                )
                return sigma

            # 计算Vega（对波动率的导数）
            vega = self.calculate_vega(temp_contract)

            # 检查Vega是否太小（避免除零）
            if abs(vega) < 1e-10:
                logger.warning(f"Vega太小，无法继续迭代: {vega}")
                return None

            # Newton-Raphson更新
            sigma_new = sigma - price_diff / vega

            # 确保波动率在合理范围内
            sigma_new = max(0.001, min(sigma_new, 5.0))

            # 检查更新幅度
            if abs(sigma_new - sigma) < tolerance:
                logger.debug(f"隐含波动率收敛（更新幅度小）: {sigma_new:.6f}, " f"迭代次数: {iteration + 1}")
                return sigma_new

            sigma = sigma_new

        # 未收敛
        logger.warning(
            f"隐含波动率未收敛: "
            f"最大迭代次数={max_iterations}, "
            f"最终sigma={sigma:.6f}, "
            f"价格误差={price_diff:.6f}"
        )
        return None

    def get_stats(self) -> Dict[str, Any]:
        """获取性能统计

        Returns:
            性能统计字典
        """
        cache_hit_rate = 0.0
        if self.stats["total_calculations"] > 0:
            cache_hit_rate = self.stats["cache_hits"] / self.stats["total_calculations"]

        return {
            "total_calculations": self.stats["total_calculations"],
            "cache_hits": self.stats["cache_hits"],
            "cache_misses": self.stats["cache_misses"],
            "cache_hit_rate": cache_hit_rate,
            "avg_calculation_time_ms": self.stats["avg_calculation_time_ms"],
            "total_calculation_time_ms": self.stats["total_calculation_time_ms"],
        }

    def clear_cache(self) -> None:
        """清空缓存"""
        self.cache.clear()
        logger.info("Greeks Engine缓存已清空")

    # ==================== 内部方法 ====================

    def _calculate_d1_d2(self, contract: OptionContract) -> tuple:
        """计算Black-Scholes公式中的d1和d2（内部方法）

        Args:
            contract: 期权合约

        Returns:
            (d1, d2)元组
        """
        S = contract.underlying_price
        K = contract.strike_price
        T = contract.time_to_maturity
        r = contract.risk_free_rate
        sigma = contract.volatility
        q = contract.dividend_yield

        # d1 = [ln(S/K) + (r - q + σ²/2)T] / (σ√T)
        d1 = (np.log(S / K) + (r - q + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))

        # d2 = d1 - σ√T
        d2 = d1 - sigma * np.sqrt(T)

        return d1, d2

    def _generate_cache_key(self, contract: OptionContract, calc_type: str) -> str:
        """生成缓存键（内部方法）

        Args:
            contract: 期权合约
            calc_type: 计算类型 ('price' 或 'greeks')

        Returns:
            缓存键字符串
        """
        return (
            f"{contract.symbol}_{calc_type}_"
            f"{contract.underlying_price:.2f}_"
            f"{contract.strike_price:.2f}_"
            f"{contract.time_to_maturity:.4f}_"
            f"{contract.volatility:.4f}_"
            f"{contract.option_type.value}"
        )

    def _update_stats(self, elapsed_ms: float) -> None:
        """更新性能统计（内部方法）

        Args:
            elapsed_ms: 计算耗时（毫秒）
        """
        self.stats["total_calculations"] += 1
        self.stats["total_calculation_time_ms"] += elapsed_ms
        self.stats["avg_calculation_time_ms"] = (
            self.stats["total_calculation_time_ms"] / self.stats["total_calculations"]
        )


# 全局单例实例
_greeks_engine_instance: Optional[GreeksEngine] = None


def get_greeks_engine() -> GreeksEngine:
    """获取Greeks引擎单例实例

    Returns:
        GreeksEngine实例
    """
    global _greeks_engine_instance  # pylint: disable=w0603
    if _greeks_engine_instance is None:
        _greeks_engine_instance = GreeksEngine()
    return _greeks_engine_instance
