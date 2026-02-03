"""专业风险因子挖掘系统

白皮书依据: 第四章 4.1.1 专业风险因子挖掘系统

架构版本: v2.0 (2026-01-23)
系统定位: 风险信号提供者（非退出执行器）

核心组件:
- RiskFactor: 风险因子数据模型
- FlowRiskFactorMiner: 资金流风险挖掘器
- MicrostructureRiskFactorMiner: 微结构风险挖掘器
- PortfolioRiskFactorMiner: 组合风险挖掘器
- RiskFactorRegistry: 风险因子注册中心
"""

__version__ = "2.0.0"
__author__ = "MIA System"

from .flow_risk_miner import FlowRiskFactorMiner
from .microstructure_risk_miner import MicrostructureRiskFactorMiner
from .portfolio_risk_miner import PortfolioRiskFactorMiner
from .risk_factor import RiskEvent, RiskEventType, RiskFactor
from .risk_factor_registry import RiskFactorRegistry

__all__ = [
    "RiskFactor",
    "RiskEventType",
    "RiskEvent",
    "FlowRiskFactorMiner",
    "MicrostructureRiskFactorMiner",
    "PortfolioRiskFactorMiner",
    "RiskFactorRegistry",
]
