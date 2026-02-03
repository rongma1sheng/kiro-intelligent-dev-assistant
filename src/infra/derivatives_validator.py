"""
衍生品数据验证器 - Derivatives Data Validator

白皮书依据: 第三章 3.3 衍生品管道 - 数据验证
版本: v1.0.0
作者: MIA Team
日期: 2026-01-22

功能:
1. 期货数据合理性验证
2. 期权平价关系验证
3. Greeks范围检查
4. 异常数据标记

验证标准:
- 价格合理性: 价格 > 0
- 成交量合理性: 成交量 >= 0
- 持仓量合理性: 持仓量 >= 0
- Delta范围: [-1, 1]
- Gamma范围: [0, +∞)
- Vega范围: [0, +∞)
- Theta范围: (-∞, 0]
- Rho范围: (-∞, +∞)
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional

import numpy as np
from loguru import logger


class ValidationResult(Enum):
    """验证结果"""

    PASS = "pass"
    WARNING = "warning"
    FAIL = "fail"


@dataclass
class FutureData:
    """期货数据结构

    Attributes:
        symbol: 期货代码
        price: 价格
        volume: 成交量
        open_interest: 持仓量
        settlement_price: 结算价
        pre_settlement: 前结算价
    """

    symbol: str
    price: float
    volume: float
    open_interest: float
    settlement_price: Optional[float] = None
    pre_settlement: Optional[float] = None


@dataclass
class OptionData:
    """期权数据结构

    Attributes:
        symbol: 期权代码
        call_price: 看涨期权价格
        put_price: 看跌期权价格
        underlying_price: 标的价格
        strike_price: 行权价
        time_to_maturity: 到期时间（年）
        risk_free_rate: 无风险利率
    """

    symbol: str
    call_price: float
    put_price: float
    underlying_price: float
    strike_price: float
    time_to_maturity: float
    risk_free_rate: float


@dataclass
class GreeksData:
    """Greeks数据结构

    Attributes:
        symbol: 期权代码
        delta: Delta
        gamma: Gamma
        vega: Vega
        theta: Theta
        rho: Rho
    """

    symbol: str
    delta: float
    gamma: float
    vega: float
    theta: float
    rho: float


@dataclass
class ValidationReport:
    """验证报告

    Attributes:
        result: 验证结果
        passed_checks: 通过的检查项
        failed_checks: 失败的检查项
        warnings: 警告信息
        details: 详细信息
    """

    result: ValidationResult
    passed_checks: List[str]
    failed_checks: List[str]
    warnings: List[str]
    details: Dict[str, Any]


class DerivativesValidator:
    """衍生品数据验证器

    白皮书依据: 第三章 3.3 衍生品管道 - 数据验证

    验证期货和期权数据的合理性，检测异常数据。

    Attributes:
        price_tolerance: 价格容差，默认0.01
        parity_tolerance: 平价关系容差，默认0.05
        stats: 验证统计
    """

    def __init__(self, price_tolerance: float = 0.01, parity_tolerance: float = 0.05):
        """初始化衍生品数据验证器

        Args:
            price_tolerance: 价格容差，默认0.01
            parity_tolerance: 平价关系容差，默认0.05
        """
        self.price_tolerance = price_tolerance
        self.parity_tolerance = parity_tolerance

        # 验证统计
        self.stats = {"total_validations": 0, "passed_validations": 0, "failed_validations": 0, "warnings": 0}

        logger.info(
            f"DerivativesValidator初始化完成 - "
            f"price_tolerance={price_tolerance}, "
            f"parity_tolerance={parity_tolerance}"
        )

    def validate_future_data(self, data: FutureData) -> ValidationReport:  # pylint: disable=too-many-branches
        """验证期货数据

        白皮书依据: 第三章 3.3 衍生品管道 - 期货数据验证

        验证期货数据的合理性，包括价格、成交量、持仓量等。

        Args:
            data: 期货数据

        Returns:
            验证报告
        """
        self.stats["total_validations"] += 1

        passed_checks = []
        failed_checks = []
        warnings = []
        details = {}

        # 检查1: 价格合理性
        if data.price > 0:
            passed_checks.append("价格 > 0")
            details["price"] = data.price
        else:
            failed_checks.append(f"价格不合理: {data.price}")

        # 检查2: 成交量合理性
        if data.volume >= 0:
            passed_checks.append("成交量 >= 0")
            details["volume"] = data.volume
        else:
            failed_checks.append(f"成交量不合理: {data.volume}")

        # 检查3: 持仓量合理性
        if data.open_interest >= 0:
            passed_checks.append("持仓量 >= 0")
            details["open_interest"] = data.open_interest
        else:
            failed_checks.append(f"持仓量不合理: {data.open_interest}")

        # 检查4: 结算价合理性
        if data.settlement_price is not None:
            if data.settlement_price > 0:
                passed_checks.append("结算价 > 0")
                details["settlement_price"] = data.settlement_price

                # 检查结算价与价格的偏离
                price_diff = abs(data.settlement_price - data.price) / data.price
                if price_diff > 0.1:  # 偏离超过10%
                    warnings.append(f"结算价与价格偏离较大: {price_diff:.2%}")
            else:
                failed_checks.append(f"结算价不合理: {data.settlement_price}")

        # 检查5: 前结算价合理性
        if data.pre_settlement is not None:
            if data.pre_settlement > 0:
                passed_checks.append("前结算价 > 0")
                details["pre_settlement"] = data.pre_settlement

                # 检查价格涨跌幅
                if data.settlement_price is not None:
                    price_change = (data.settlement_price - data.pre_settlement) / data.pre_settlement
                    details["price_change"] = price_change

                    # 涨跌幅超过20%发出警告
                    if abs(price_change) > 0.2:
                        warnings.append(f"价格涨跌幅较大: {price_change:.2%}")
            else:
                failed_checks.append(f"前结算价不合理: {data.pre_settlement}")

        # 检查6: 成交量与持仓量关系
        if data.volume > 0 and data.open_interest > 0:
            volume_oi_ratio = data.volume / data.open_interest
            details["volume_oi_ratio"] = volume_oi_ratio

            # 成交量远大于持仓量可能异常
            if volume_oi_ratio > 10:
                warnings.append(f"成交量/持仓量比例异常: {volume_oi_ratio:.2f}")

        # 确定验证结果
        if failed_checks:
            result = ValidationResult.FAIL
            self.stats["failed_validations"] += 1
        elif warnings:
            result = ValidationResult.WARNING
            self.stats["passed_validations"] += 1
            self.stats["warnings"] += 1
        else:
            result = ValidationResult.PASS
            self.stats["passed_validations"] += 1

        report = ValidationReport(
            result=result, passed_checks=passed_checks, failed_checks=failed_checks, warnings=warnings, details=details
        )

        if result == ValidationResult.FAIL:
            logger.warning(f"期货数据验证失败: {data.symbol}, " f"失败项: {failed_checks}")
        elif result == ValidationResult.WARNING:
            logger.debug(f"期货数据验证警告: {data.symbol}, " f"警告: {warnings}")

        return report

    def validate_put_call_parity(self, data: OptionData) -> ValidationReport:
        """验证期权平价关系

        白皮书依据: 第三章 3.3 衍生品管道 - 期权平价关系验证

        验证看涨看跌期权平价关系: C - P = S - K*e^(-rT)

        Args:
            data: 期权数据

        Returns:
            验证报告
        """
        self.stats["total_validations"] += 1

        passed_checks = []
        failed_checks = []
        warnings = []
        details = {}

        # 计算平价关系左侧: C - P
        parity_lhs = data.call_price - data.put_price
        details["parity_lhs"] = parity_lhs

        # 计算平价关系右侧: S - K*e^(-rT)
        parity_rhs = data.underlying_price - data.strike_price * np.exp(-data.risk_free_rate * data.time_to_maturity)
        details["parity_rhs"] = parity_rhs

        # 计算偏离
        parity_diff = abs(parity_lhs - parity_rhs)
        parity_diff_pct = parity_diff / data.underlying_price
        details["parity_diff"] = parity_diff
        details["parity_diff_pct"] = parity_diff_pct

        # 检查平价关系
        if parity_diff_pct <= self.parity_tolerance:
            passed_checks.append(f"平价关系偏离 <= {self.parity_tolerance:.2%}")
            result = ValidationResult.PASS
            self.stats["passed_validations"] += 1
        elif parity_diff_pct <= self.parity_tolerance * 2:
            warnings.append(f"平价关系偏离较大: {parity_diff_pct:.2%}")
            result = ValidationResult.WARNING
            self.stats["passed_validations"] += 1
            self.stats["warnings"] += 1
        else:
            failed_checks.append(f"平价关系严重偏离: {parity_diff_pct:.2%}")
            result = ValidationResult.FAIL
            self.stats["failed_validations"] += 1

        # 检查套利机会
        if parity_diff_pct > 0.01:  # 偏离超过1%
            if parity_lhs > parity_rhs:
                details["arbitrage_opportunity"] = "买入看跌，卖出看涨"
            else:
                details["arbitrage_opportunity"] = "买入看涨，卖出看跌"

        report = ValidationReport(
            result=result, passed_checks=passed_checks, failed_checks=failed_checks, warnings=warnings, details=details
        )

        if result == ValidationResult.FAIL:
            logger.warning(f"期权平价关系验证失败: {data.symbol}, " f"偏离: {parity_diff_pct:.2%}")

        return report

    def validate_greeks_range(self, data: GreeksData) -> ValidationReport:
        """验证Greeks范围

        白皮书依据: 第三章 3.3 衍生品管道 - Greeks范围检查

        验证Greeks是否在合理范围内：
        - Delta: [-1, 1]
        - Gamma: [0, +∞)
        - Vega: [0, +∞)
        - Theta: (-∞, 0]
        - Rho: (-∞, +∞)

        Args:
            data: Greeks数据

        Returns:
            验证报告
        """
        self.stats["total_validations"] += 1

        passed_checks = []
        failed_checks = []
        warnings = []
        details = {"delta": data.delta, "gamma": data.gamma, "vega": data.vega, "theta": data.theta, "rho": data.rho}

        # 检查1: Delta范围 [-1, 1]
        if -1 <= data.delta <= 1:
            passed_checks.append(f"Delta在范围内: {data.delta:.4f}")
        else:
            failed_checks.append(f"Delta超出范围: {data.delta:.4f}")

        # 检查2: Gamma范围 [0, +∞)
        if data.gamma >= 0:
            passed_checks.append(f"Gamma >= 0: {data.gamma:.6f}")
        else:
            failed_checks.append(f"Gamma < 0: {data.gamma:.6f}")

        # 检查3: Vega范围 [0, +∞)
        if data.vega >= 0:
            passed_checks.append(f"Vega >= 0: {data.vega:.4f}")
        else:
            failed_checks.append(f"Vega < 0: {data.vega:.4f}")

        # 检查4: Theta范围 (-∞, 0]
        if data.theta <= 0:
            passed_checks.append(f"Theta <= 0: {data.theta:.4f}")
        else:
            # Theta为正可能是深度实值期权或特殊情况
            warnings.append(f"Theta > 0（罕见）: {data.theta:.4f}")

        # 检查5: Rho范围 (-∞, +∞) - 无限制，但检查合理性
        if abs(data.rho) < 1000:  # 合理范围
            passed_checks.append(f"Rho在合理范围: {data.rho:.4f}")
        else:
            warnings.append(f"Rho数值较大: {data.rho:.4f}")

        # 确定验证结果
        if failed_checks:
            result = ValidationResult.FAIL
            self.stats["failed_validations"] += 1
        elif warnings:
            result = ValidationResult.WARNING
            self.stats["passed_validations"] += 1
            self.stats["warnings"] += 1
        else:
            result = ValidationResult.PASS
            self.stats["passed_validations"] += 1

        report = ValidationReport(
            result=result, passed_checks=passed_checks, failed_checks=failed_checks, warnings=warnings, details=details
        )

        if result == ValidationResult.FAIL:
            logger.warning(f"Greeks范围验证失败: {data.symbol}, " f"失败项: {failed_checks}")

        return report

    def get_stats(self) -> Dict[str, Any]:
        """获取验证统计

        Returns:
            验证统计字典
        """
        pass_rate = 0.0
        if self.stats["total_validations"] > 0:
            pass_rate = self.stats["passed_validations"] / self.stats["total_validations"]

        return {
            "total_validations": self.stats["total_validations"],
            "passed_validations": self.stats["passed_validations"],
            "failed_validations": self.stats["failed_validations"],
            "warnings": self.stats["warnings"],
            "pass_rate": pass_rate,
        }

    def reset_stats(self) -> None:
        """重置统计"""
        self.stats = {"total_validations": 0, "passed_validations": 0, "failed_validations": 0, "warnings": 0}
        logger.info("验证统计已重置")
