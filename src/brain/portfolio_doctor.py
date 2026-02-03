"""
持仓诊断器 (Portfolio Doctor)

白皮书依据: 第一章 1.5.3 诊疗态任务调度
- 持仓健康检查
- 风险暴露分析
- 生成诊断报告

功能:
- 分析持仓健康状态
- 检测风险暴露
- 生成诊断报告和建议
"""

import asyncio
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger

try:
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False
    logger.warning("numpy/pandas未安装，部分功能不可用")


class HealthStatus(Enum):
    """健康状态"""

    HEALTHY = "健康"
    WARNING = "警告"
    CRITICAL = "危险"
    UNKNOWN = "未知"


class RiskType(Enum):
    """风险类型"""

    CONCENTRATION = "集中度风险"
    SECTOR = "行业风险"
    LIQUIDITY = "流动性风险"
    VOLATILITY = "波动率风险"
    DRAWDOWN = "回撤风险"
    CORRELATION = "相关性风险"


@dataclass
class Position:
    """持仓信息

    Attributes:
        symbol: 标的代码
        quantity: 持仓数量
        cost_price: 成本价
        current_price: 当前价
        market_value: 市值
        pnl: 盈亏
        pnl_ratio: 盈亏比例
        sector: 所属行业
        weight: 持仓权重
    """

    symbol: str
    quantity: int
    cost_price: float
    current_price: float
    market_value: float = 0.0
    pnl: float = 0.0
    pnl_ratio: float = 0.0
    sector: str = ""
    weight: float = 0.0

    def __post_init__(self):
        """计算衍生字段"""
        if self.market_value == 0.0:
            self.market_value = self.quantity * self.current_price
        if self.pnl == 0.0:
            self.pnl = (self.current_price - self.cost_price) * self.quantity
        if self.pnl_ratio == 0.0 and self.cost_price > 0:
            self.pnl_ratio = (self.current_price - self.cost_price) / self.cost_price

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "symbol": self.symbol,
            "quantity": self.quantity,
            "cost_price": self.cost_price,
            "current_price": self.current_price,
            "market_value": self.market_value,
            "pnl": self.pnl,
            "pnl_ratio": self.pnl_ratio,
            "sector": self.sector,
            "weight": self.weight,
        }


@dataclass
class RiskExposure:
    """风险暴露

    Attributes:
        risk_type: 风险类型
        level: 风险等级 (0-1)
        description: 风险描述
        affected_positions: 受影响的持仓
        suggestion: 建议措施
    """

    risk_type: RiskType
    level: float
    description: str
    affected_positions: List[str] = field(default_factory=list)
    suggestion: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "risk_type": self.risk_type.value,
            "level": self.level,
            "description": self.description,
            "affected_positions": self.affected_positions,
            "suggestion": self.suggestion,
        }


@dataclass
class DiagnosisReport:
    """诊断报告

    Attributes:
        report_date: 报告日期
        overall_status: 整体健康状态
        total_positions: 持仓数量
        total_market_value: 总市值
        total_pnl: 总盈亏
        total_pnl_ratio: 总盈亏比例
        risk_exposures: 风险暴露列表
        position_details: 持仓详情
        suggestions: 建议列表
        timestamp: 生成时间
    """

    report_date: date
    overall_status: HealthStatus
    total_positions: int = 0
    total_market_value: float = 0.0
    total_pnl: float = 0.0
    total_pnl_ratio: float = 0.0
    risk_exposures: List[RiskExposure] = field(default_factory=list)
    position_details: List[Position] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "report_date": self.report_date.isoformat(),
            "overall_status": self.overall_status.value,
            "total_positions": self.total_positions,
            "total_market_value": self.total_market_value,
            "total_pnl": self.total_pnl,
            "total_pnl_ratio": self.total_pnl_ratio,
            "risk_exposures": [r.to_dict() for r in self.risk_exposures],
            "position_details": [p.to_dict() for p in self.position_details],
            "suggestions": self.suggestions,
            "timestamp": self.timestamp.isoformat(),
        }


class PortfolioDoctor:
    """持仓诊断器

    白皮书依据: 第一章 1.5.3 诊疗态任务调度

    负责分析持仓健康状态，检测风险暴露，生成诊断报告。

    Attributes:
        concentration_threshold: 集中度阈值
        sector_threshold: 行业集中度阈值
        drawdown_threshold: 回撤阈值
        volatility_threshold: 波动率阈值

    Example:
        >>> doctor = PortfolioDoctor()
        >>> report = doctor.diagnose(positions)
        >>> print(f"健康状态: {report.overall_status.value}")
    """

    def __init__(
        self,
        concentration_threshold: float = 0.3,
        sector_threshold: float = 0.5,
        drawdown_threshold: float = 0.1,
        volatility_threshold: float = 0.3,
    ):
        """初始化持仓诊断器

        Args:
            concentration_threshold: 单一持仓集中度阈值
            sector_threshold: 行业集中度阈值
            drawdown_threshold: 回撤警告阈值
            volatility_threshold: 波动率警告阈值
        """
        self.concentration_threshold = concentration_threshold
        self.sector_threshold = sector_threshold
        self.drawdown_threshold = drawdown_threshold
        self.volatility_threshold = volatility_threshold

        self._positions: List[Position] = []
        self._total_value: float = 0.0

        logger.info(f"持仓诊断器初始化: " f"集中度阈值={concentration_threshold}, " f"行业阈值={sector_threshold}")

    def diagnose(self, positions: List[Position], historical_values: Optional[List[float]] = None) -> DiagnosisReport:
        """执行持仓诊断

        白皮书依据: 第一章 1.5.3 持仓诊断

        Args:
            positions: 持仓列表
            historical_values: 历史净值序列（用于计算回撤）

        Returns:
            诊断报告
        """
        logger.info(f"开始持仓诊断，持仓数量: {len(positions)}")

        self._positions = positions
        self._total_value = sum(p.market_value for p in positions)

        # 计算持仓权重
        self._calculate_weights()

        # 检测各类风险
        risk_exposures = []

        # 1. 集中度风险
        concentration_risk = self._check_concentration_risk()
        if concentration_risk:
            risk_exposures.append(concentration_risk)

        # 2. 行业风险
        sector_risk = self._check_sector_risk()
        if sector_risk:
            risk_exposures.append(sector_risk)

        # 3. 回撤风险
        if historical_values:
            drawdown_risk = self._check_drawdown_risk(historical_values)
            if drawdown_risk:
                risk_exposures.append(drawdown_risk)

        # 4. 盈亏风险
        pnl_risk = self._check_pnl_risk()
        if pnl_risk:
            risk_exposures.append(pnl_risk)

        # 计算总盈亏
        total_pnl = sum(p.pnl for p in positions)
        total_cost = sum(p.cost_price * p.quantity for p in positions)
        total_pnl_ratio = total_pnl / total_cost if total_cost > 0 else 0.0

        # 确定整体健康状态
        overall_status = self._determine_overall_status(risk_exposures)

        # 生成建议
        suggestions = self._generate_suggestions(risk_exposures)

        report = DiagnosisReport(
            report_date=date.today(),
            overall_status=overall_status,
            total_positions=len(positions),
            total_market_value=self._total_value,
            total_pnl=total_pnl,
            total_pnl_ratio=total_pnl_ratio,
            risk_exposures=risk_exposures,
            position_details=positions,
            suggestions=suggestions,
        )

        logger.info(f"持仓诊断完成: 状态={overall_status.value}, " f"风险数={len(risk_exposures)}")

        return report

    def _calculate_weights(self) -> None:
        """计算持仓权重"""
        if self._total_value <= 0:
            return

        for position in self._positions:
            position.weight = position.market_value / self._total_value

    def _check_concentration_risk(self) -> Optional[RiskExposure]:
        """检查集中度风险

        白皮书依据: 第一章 1.5.3 风险暴露分析
        """
        high_concentration = []
        max_weight = 0.0

        for position in self._positions:
            if position.weight > self.concentration_threshold:
                high_concentration.append(position.symbol)
            max_weight = max(max_weight, position.weight)

        if high_concentration:
            level = min(max_weight / self.concentration_threshold, 1.0)
            return RiskExposure(
                risk_type=RiskType.CONCENTRATION,
                level=level,
                description=f"单一持仓集中度过高，最高权重{max_weight:.1%}",
                affected_positions=high_concentration,
                suggestion="建议分散投资，降低单一持仓比例",
            )

        return None

    def _check_sector_risk(self) -> Optional[RiskExposure]:
        """检查行业风险

        白皮书依据: 第一章 1.5.3 风险暴露分析
        """
        sector_weights: Dict[str, float] = defaultdict(float)
        sector_positions: Dict[str, List[str]] = defaultdict(list)

        for position in self._positions:
            if position.sector:
                sector_weights[position.sector] += position.weight
                sector_positions[position.sector].append(position.symbol)

        high_sector = None
        max_sector_weight = 0.0

        for sector, weight in sector_weights.items():
            if weight > self.sector_threshold and weight > max_sector_weight:
                high_sector = sector
                max_sector_weight = weight

        if high_sector:
            level = min(max_sector_weight / self.sector_threshold, 1.0)
            return RiskExposure(
                risk_type=RiskType.SECTOR,
                level=level,
                description=f"行业{high_sector}集中度过高，权重{max_sector_weight:.1%}",
                affected_positions=sector_positions[high_sector],
                suggestion=f"建议减少{high_sector}行业持仓，增加其他行业配置",
            )

        return None

    def _check_drawdown_risk(self, historical_values: List[float]) -> Optional[RiskExposure]:
        """检查回撤风险

        白皮书依据: 第一章 1.5.3 风险暴露分析
        """
        if not historical_values or len(historical_values) < 2:
            return None

        # 计算最大回撤
        peak = historical_values[0]
        max_drawdown = 0.0

        for value in historical_values:
            if value > peak:  # pylint: disable=r1731
                peak = value
            drawdown = (peak - value) / peak if peak > 0 else 0
            max_drawdown = max(max_drawdown, drawdown)

        if max_drawdown > self.drawdown_threshold:
            level = min(max_drawdown / self.drawdown_threshold, 1.0)
            return RiskExposure(
                risk_type=RiskType.DRAWDOWN,
                level=level,
                description=f"最大回撤{max_drawdown:.1%}，超过阈值{self.drawdown_threshold:.1%}",
                affected_positions=[p.symbol for p in self._positions],
                suggestion="建议检查止损策略，考虑减仓控制风险",
            )

        return None

    def _check_pnl_risk(self) -> Optional[RiskExposure]:
        """检查盈亏风险"""
        losing_positions = []
        severe_loss_positions = []

        for position in self._positions:
            if position.pnl_ratio < -0.05:  # 亏损超过5%
                losing_positions.append(position.symbol)
            if position.pnl_ratio < -0.15:  # 亏损超过15%
                severe_loss_positions.append(position.symbol)

        if severe_loss_positions:
            level = len(severe_loss_positions) / len(self._positions)
            return RiskExposure(
                risk_type=RiskType.DRAWDOWN,
                level=level,
                description=f"{len(severe_loss_positions)}个持仓亏损超过15%",
                affected_positions=severe_loss_positions,
                suggestion="建议评估这些持仓是否需要止损",
            )

        return None

    def _determine_overall_status(self, risk_exposures: List[RiskExposure]) -> HealthStatus:
        """确定整体健康状态"""
        if not risk_exposures:
            return HealthStatus.HEALTHY

        max_level = max(r.level for r in risk_exposures)

        if max_level >= 0.8:  # pylint: disable=no-else-return
            return HealthStatus.CRITICAL
        elif max_level >= 0.5:
            return HealthStatus.WARNING
        else:
            return HealthStatus.HEALTHY

    def _generate_suggestions(self, risk_exposures: List[RiskExposure]) -> List[str]:
        """生成建议"""
        suggestions = []

        for risk in risk_exposures:
            if risk.suggestion:
                suggestions.append(risk.suggestion)

        if not suggestions:
            suggestions.append("持仓状态良好，继续保持当前策略")

        return suggestions

    def check_position_health(self, position: Position) -> Tuple[HealthStatus, str]:
        """检查单个持仓健康状态

        Args:
            position: 持仓信息

        Returns:
            (健康状态, 描述)
        """
        if position.pnl_ratio < -0.2:  # pylint: disable=no-else-return
            return HealthStatus.CRITICAL, f"亏损{abs(position.pnl_ratio):.1%}，建议止损"
        elif position.pnl_ratio < -0.1:
            return HealthStatus.WARNING, f"亏损{abs(position.pnl_ratio):.1%}，需关注"
        elif position.pnl_ratio > 0.3:
            return HealthStatus.HEALTHY, f"盈利{position.pnl_ratio:.1%}，考虑止盈"
        else:
            return HealthStatus.HEALTHY, "持仓正常"

    def get_sector_distribution(self) -> Dict[str, float]:
        """获取行业分布

        Returns:
            {行业: 权重}
        """
        distribution: Dict[str, float] = defaultdict(float)

        for position in self._positions:
            sector = position.sector or "未分类"
            distribution[sector] += position.weight

        return dict(distribution)

    def get_pnl_summary(self) -> Dict[str, Any]:
        """获取盈亏汇总

        Returns:
            盈亏汇总信息
        """
        if not self._positions:
            return {
                "total_pnl": 0.0,
                "winning_count": 0,
                "losing_count": 0,
                "win_rate": 0.0,
                "avg_win": 0.0,
                "avg_loss": 0.0,
            }

        winning = [p for p in self._positions if p.pnl > 0]
        losing = [p for p in self._positions if p.pnl < 0]

        total_pnl = sum(p.pnl for p in self._positions)
        win_rate = len(winning) / len(self._positions) if self._positions else 0
        avg_win = sum(p.pnl for p in winning) / len(winning) if winning else 0
        avg_loss = sum(p.pnl for p in losing) / len(losing) if losing else 0

        return {
            "total_pnl": total_pnl,
            "winning_count": len(winning),
            "losing_count": len(losing),
            "win_rate": win_rate,
            "avg_win": avg_win,
            "avg_loss": avg_loss,
        }

    async def diagnose_async(
        self, positions: List[Position], historical_values: Optional[List[float]] = None
    ) -> DiagnosisReport:
        """异步执行持仓诊断

        Args:
            positions: 持仓列表
            historical_values: 历史净值序列

        Returns:
            诊断报告
        """
        return await asyncio.to_thread(self.diagnose, positions, historical_values)
