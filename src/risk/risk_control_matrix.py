"""风险控制矩阵

白皮书依据: 第十九章 19.2 风险控制机制

风险控制限制:
1. 单只股票持仓 ≤ 20%
2. 单日亏损 ≤ 10%
3. 衍生品保证金 ≤ 30%
4. 行业集中度 ≤ 40%
"""

from typing import Dict

from loguru import logger

from src.risk.risk_identification_system import RiskLevel


class RiskControlMatrix:
    """风险控制矩阵

    白皮书依据: 第十九章 19.2.1 交易风险门闸

    根据风险等级动态调整交易限制:
    - LOW: 正常限制
    - MEDIUM: 收紧20%
    - HIGH: 收紧50%
    - CRITICAL: 禁止新开仓

    Attributes:
        base_limits: 基础风险限制
        current_risk_level: 当前风险等级
    """

    def __init__(
        self,
        single_position_ratio: float = 0.20,
        daily_loss_ratio: float = 0.10,
        margin_ratio: float = 0.30,
        sector_concentration: float = 0.40,
    ):
        """初始化风险控制矩阵

        白皮书依据: 第十九章 19.2.1 交易风险门闸

        Args:
            single_position_ratio: 单只股票持仓比例限制，默认20%
            daily_loss_ratio: 单日亏损比例限制，默认10%
            margin_ratio: 衍生品保证金比例限制，默认30%
            sector_concentration: 行业集中度限制，默认40%

        Raises:
            ValueError: 当限制参数不在有效范围时
        """
        if not 0 < single_position_ratio <= 1:
            raise ValueError(f"单只股票持仓比例必须在(0, 1]范围内: {single_position_ratio}")

        if not 0 < daily_loss_ratio <= 1:
            raise ValueError(f"单日亏损比例必须在(0, 1]范围内: {daily_loss_ratio}")

        if not 0 < margin_ratio <= 1:
            raise ValueError(f"保证金比例必须在(0, 1]范围内: {margin_ratio}")

        if not 0 < sector_concentration <= 1:
            raise ValueError(f"行业集中度必须在(0, 1]范围内: {sector_concentration}")

        self.base_limits = {
            "single_position_ratio": single_position_ratio,
            "daily_loss_ratio": daily_loss_ratio,
            "margin_ratio": margin_ratio,
            "sector_concentration": sector_concentration,
        }

        self.current_risk_level = RiskLevel.LOW

        logger.info(
            f"风险控制矩阵初始化完成 - "
            f"单只股票: {single_position_ratio:.1%}, "
            f"单日亏损: {daily_loss_ratio:.1%}, "
            f"保证金: {margin_ratio:.1%}, "
            f"行业集中度: {sector_concentration:.1%}"
        )

    def update_risk_level(self, risk_level: RiskLevel) -> None:
        """更新当前风险等级

        白皮书依据: 第十九章 19.2 风险控制机制

        Args:
            risk_level: 新的风险等级

        Raises:
            ValueError: 当risk_level不是RiskLevel枚举时
        """
        if not isinstance(risk_level, RiskLevel):
            raise ValueError(f"风险等级必须是RiskLevel枚举: {type(risk_level)}")

        old_level = self.current_risk_level
        self.current_risk_level = risk_level

        if old_level != risk_level:
            logger.info(f"风险等级更新: {old_level.value} -> {risk_level.value}")

    def get_position_limit(self, symbol: str = "") -> float:  # pylint: disable=unused-argument
        """获取持仓限制

        白皮书依据: 第十九章 19.2.1 交易风险门闸

        根据当前风险等级动态调整:
        - LOW: 20% (基础限制)
        - MEDIUM: 16% (收紧20%)
        - HIGH: 10% (收紧50%)
        - CRITICAL: 0% (禁止新开仓)

        Args:
            symbol: 股票代码（可选，用于特殊限制）

        Returns:
            持仓比例限制 (0-1)
        """
        base_limit = self.base_limits["single_position_ratio"]

        if self.current_risk_level == RiskLevel.LOW:  # pylint: disable=no-else-return
            return base_limit
        elif self.current_risk_level == RiskLevel.MEDIUM:
            return base_limit * 0.80  # 收紧20%
        elif self.current_risk_level == RiskLevel.HIGH:
            return base_limit * 0.50  # 收紧50%
        else:  # CRITICAL
            return 0.0  # 禁止新开仓

    def get_sector_limit(self, sector: str = "") -> float:  # pylint: disable=unused-argument
        """获取行业集中度限制

        白皮书依据: 第十九章 19.2.1 交易风险门闸

        根据当前风险等级动态调整:
        - LOW: 40% (基础限制)
        - MEDIUM: 32% (收紧20%)
        - HIGH: 20% (收紧50%)
        - CRITICAL: 0% (禁止新开仓)

        Args:
            sector: 行业名称（可选，用于特殊限制）

        Returns:
            行业集中度限制 (0-1)
        """
        base_limit = self.base_limits["sector_concentration"]

        if self.current_risk_level == RiskLevel.LOW:  # pylint: disable=no-else-return
            return base_limit
        elif self.current_risk_level == RiskLevel.MEDIUM:
            return base_limit * 0.80  # 收紧20%
        elif self.current_risk_level == RiskLevel.HIGH:
            return base_limit * 0.50  # 收紧50%
        else:  # CRITICAL
            return 0.0  # 禁止新开仓

    def get_stop_loss_threshold(self) -> float:
        """获取止损阈值

        白皮书依据: 第十九章 19.2.1 交易风险门闸

        根据当前风险等级动态调整:
        - LOW: 10% (基础限制)
        - MEDIUM: 8% (收紧20%)
        - HIGH: 5% (收紧50%)
        - CRITICAL: 0% (立即止损)

        Returns:
            止损阈值 (0-1)
        """
        base_threshold = self.base_limits["daily_loss_ratio"]

        if self.current_risk_level == RiskLevel.LOW:  # pylint: disable=no-else-return
            return base_threshold
        elif self.current_risk_level == RiskLevel.MEDIUM:
            return base_threshold * 0.80  # 收紧20%
        elif self.current_risk_level == RiskLevel.HIGH:
            return base_threshold * 0.50  # 收紧50%
        else:  # CRITICAL
            return 0.0  # 立即止损

    def get_margin_limit(self) -> float:
        """获取保证金限制

        白皮书依据: 第十九章 19.2.1 交易风险门闸

        根据当前风险等级动态调整:
        - LOW: 30% (基础限制)
        - MEDIUM: 24% (收紧20%)
        - HIGH: 15% (收紧50%)
        - CRITICAL: 0% (禁止衍生品交易)

        Returns:
            保证金比例限制 (0-1)
        """
        base_limit = self.base_limits["margin_ratio"]

        if self.current_risk_level == RiskLevel.LOW:  # pylint: disable=no-else-return
            return base_limit
        elif self.current_risk_level == RiskLevel.MEDIUM:
            return base_limit * 0.80  # 收紧20%
        elif self.current_risk_level == RiskLevel.HIGH:
            return base_limit * 0.50  # 收紧50%
        else:  # CRITICAL
            return 0.0  # 禁止衍生品交易

    def can_open_position(self) -> bool:
        """是否允许开新仓

        白皮书依据: 第十九章 19.2 风险控制机制

        Returns:
            True表示允许开仓，False表示禁止开仓
        """
        return self.current_risk_level != RiskLevel.CRITICAL

    def get_all_limits(self) -> Dict[str, float]:
        """获取所有当前限制

        Returns:
            包含所有限制的字典
        """
        return {
            "position_limit": self.get_position_limit(),
            "sector_limit": self.get_sector_limit(),
            "stop_loss_threshold": self.get_stop_loss_threshold(),
            "margin_limit": self.get_margin_limit(),
            "can_open_position": self.can_open_position(),
            "risk_level": self.current_risk_level.value,
        }

    def get_limit_adjustment_ratio(self) -> float:
        """获取限制调整比例

        Returns:
            限制调整比例 (0-1)，1表示无调整，0表示完全禁止
        """
        if self.current_risk_level == RiskLevel.LOW:  # pylint: disable=no-else-return
            return 1.0
        elif self.current_risk_level == RiskLevel.MEDIUM:
            return 0.80
        elif self.current_risk_level == RiskLevel.HIGH:
            return 0.50
        else:  # CRITICAL
            return 0.0

    def reset_to_default(self) -> None:
        """重置为默认风险等级（LOW）

        白皮书依据: 第十九章 19.2 风险控制机制
        """
        old_level = self.current_risk_level
        self.current_risk_level = RiskLevel.LOW

        if old_level != RiskLevel.LOW:
            logger.info(f"风险等级重置: {old_level.value} -> LOW")
