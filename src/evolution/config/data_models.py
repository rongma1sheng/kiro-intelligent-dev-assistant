"""Configuration Data Models

白皮书依据: 第四章 4.9 配置管理

This module defines data models for Sparta Evolution System configuration.
"""

from dataclasses import dataclass, field
from typing import Any, Dict

from loguru import logger


@dataclass
class ArenaConfig:
    """Arena测试配置

    白皮书依据: 第四章 4.9.1 Arena配置

    Attributes:
        min_ic: 最小IC阈值
        min_ir: 最小IR阈值
        min_sharpe: 最小夏普比率
        max_drawdown: 最大回撤限制
        pass_score: Arena通过分数阈值
        reality_track_weight: Reality Track权重
        hell_track_weight: Hell Track权重
        cross_market_weight: Cross-Market Track权重
    """

    min_ic: float = 0.03
    min_ir: float = 0.5
    min_sharpe: float = 1.5
    max_drawdown: float = 0.15
    pass_score: float = 0.7
    reality_track_weight: float = 0.4
    hell_track_weight: float = 0.3
    cross_market_weight: float = 0.3

    def __post_init__(self) -> None:
        """验证配置值"""
        errors = []

        if not 0.0 <= self.min_ic <= 1.0:
            errors.append(f"min_ic必须在[0, 1]范围内，当前: {self.min_ic}")

        if self.min_ir < 0:
            errors.append(f"min_ir必须 >= 0，当前: {self.min_ir}")

        if self.min_sharpe < 0:
            errors.append(f"min_sharpe必须 >= 0，当前: {self.min_sharpe}")

        if not 0.0 <= self.max_drawdown <= 1.0:
            errors.append(f"max_drawdown必须在[0, 1]范围内，当前: {self.max_drawdown}")

        if not 0.0 <= self.pass_score <= 1.0:
            errors.append(f"pass_score必须在[0, 1]范围内，当前: {self.pass_score}")

        # 验证权重之和为1
        weight_sum = self.reality_track_weight + self.hell_track_weight + self.cross_market_weight
        if abs(weight_sum - 1.0) > 0.001:
            errors.append(f"Track权重之和必须为1，当前: {weight_sum}")

        if errors:
            raise ValueError(f"ArenaConfig验证失败: {'; '.join(errors)}")


@dataclass
class SimulationConfig:
    """模拟验证配置

    白皮书依据: 第四章 4.9.2 模拟配置

    Attributes:
        duration_days: 模拟天数
        tier_1_capital: Tier 1策略资本
        tier_2_capital: Tier 2策略资本
        tier_3_capital: Tier 3策略资本
        tier_4_capital: Tier 4策略资本
        commission_rate: 佣金率
        slippage_rate: 滑点率
        min_return: 最小收益率要求
        min_sharpe: 最小夏普比率要求
        max_drawdown: 最大回撤限制
        min_win_rate: 最小胜率要求
        min_profit_factor: 最小盈亏比要求
        early_termination_drawdown: 提前终止回撤阈值
    """

    duration_days: int = 30
    tier_1_capital: float = 1_000_000.0
    tier_2_capital: float = 500_000.0
    tier_3_capital: float = 200_000.0
    tier_4_capital: float = 100_000.0
    commission_rate: float = 0.0003
    slippage_rate: float = 0.001
    min_return: float = 0.05
    min_sharpe: float = 1.2
    max_drawdown: float = 0.15
    min_win_rate: float = 0.55
    min_profit_factor: float = 1.3
    early_termination_drawdown: float = 0.20

    def __post_init__(self) -> None:
        """验证配置值"""
        errors = []

        if self.duration_days <= 0:
            errors.append(f"duration_days必须 > 0，当前: {self.duration_days}")

        if self.tier_1_capital <= 0:
            errors.append(f"tier_1_capital必须 > 0，当前: {self.tier_1_capital}")

        if self.tier_2_capital <= 0:
            errors.append(f"tier_2_capital必须 > 0，当前: {self.tier_2_capital}")

        if self.tier_3_capital <= 0:
            errors.append(f"tier_3_capital必须 > 0，当前: {self.tier_3_capital}")

        if self.tier_4_capital <= 0:
            errors.append(f"tier_4_capital必须 > 0，当前: {self.tier_4_capital}")

        if not 0.0 <= self.commission_rate <= 0.01:
            errors.append(f"commission_rate必须在[0, 0.01]范围内，当前: {self.commission_rate}")

        if not 0.0 <= self.slippage_rate <= 0.05:
            errors.append(f"slippage_rate必须在[0, 0.05]范围内，当前: {self.slippage_rate}")

        if not 0.0 <= self.min_return <= 1.0:
            errors.append(f"min_return必须在[0, 1]范围内，当前: {self.min_return}")

        if self.min_sharpe < 0:
            errors.append(f"min_sharpe必须 >= 0，当前: {self.min_sharpe}")

        if not 0.0 <= self.max_drawdown <= 1.0:
            errors.append(f"max_drawdown必须在[0, 1]范围内，当前: {self.max_drawdown}")

        if not 0.0 <= self.min_win_rate <= 1.0:
            errors.append(f"min_win_rate必须在[0, 1]范围内，当前: {self.min_win_rate}")

        if self.min_profit_factor < 0:
            errors.append(f"min_profit_factor必须 >= 0，当前: {self.min_profit_factor}")

        if not 0.0 <= self.early_termination_drawdown <= 1.0:
            errors.append(f"early_termination_drawdown必须在[0, 1]范围内，当前: {self.early_termination_drawdown}")

        if errors:
            raise ValueError(f"SimulationConfig验证失败: {'; '.join(errors)}")


@dataclass
class Z2HConfig:
    """Z2H认证配置

    白皮书依据: 第四章 4.9.3 Z2H配置

    Attributes:
        gold_sharpe_threshold: GOLD级别夏普比率阈值
        silver_sharpe_threshold: SILVER级别夏普比率阈值
        redis_ttl_days: Redis存储TTL（天）
        file_storage_enabled: 是否启用文件存储
    """

    gold_sharpe_threshold: float = 2.0
    silver_sharpe_threshold: float = 1.5
    redis_ttl_days: int = 365
    file_storage_enabled: bool = True

    def __post_init__(self) -> None:
        """验证配置值"""
        errors = []

        if self.gold_sharpe_threshold <= self.silver_sharpe_threshold:
            errors.append(
                f"gold_sharpe_threshold必须 > silver_sharpe_threshold，"
                f"当前: gold={self.gold_sharpe_threshold}, silver={self.silver_sharpe_threshold}"
            )

        if self.silver_sharpe_threshold < 0:
            errors.append(f"silver_sharpe_threshold必须 >= 0，当前: {self.silver_sharpe_threshold}")

        if self.redis_ttl_days <= 0:
            errors.append(f"redis_ttl_days必须 > 0，当前: {self.redis_ttl_days}")

        if errors:
            raise ValueError(f"Z2HConfig验证失败: {'; '.join(errors)}")


@dataclass
class DecayConfig:
    """衰减检测配置

    白皮书依据: 第四章 4.9.4 衰减配置

    Attributes:
        ic_warning_threshold: IC警告阈值
        mild_decay_days: 轻度衰减天数
        moderate_decay_days: 中度衰减天数
        severe_decay_days: 严重衰减天数
        weight_reduction_ratio: 权重降低比例
        sharpe_monitoring_threshold: 夏普比率监控阈值
    """

    ic_warning_threshold: float = 0.03
    mild_decay_days: int = 7
    moderate_decay_days: int = 15
    severe_decay_days: int = 30
    weight_reduction_ratio: float = 0.30
    sharpe_monitoring_threshold: float = 1.0

    def __post_init__(self) -> None:
        """验证配置值"""
        errors = []

        if not 0.0 <= self.ic_warning_threshold <= 1.0:
            errors.append(f"ic_warning_threshold必须在[0, 1]范围内，当前: {self.ic_warning_threshold}")

        if self.mild_decay_days <= 0:
            errors.append(f"mild_decay_days必须 > 0，当前: {self.mild_decay_days}")

        if self.moderate_decay_days <= self.mild_decay_days:
            errors.append(
                f"moderate_decay_days必须 > mild_decay_days，"
                f"当前: moderate={self.moderate_decay_days}, mild={self.mild_decay_days}"
            )

        if self.severe_decay_days <= self.moderate_decay_days:
            errors.append(
                f"severe_decay_days必须 > moderate_decay_days，"
                f"当前: severe={self.severe_decay_days}, moderate={self.moderate_decay_days}"
            )

        if not 0.0 <= self.weight_reduction_ratio <= 1.0:
            errors.append(f"weight_reduction_ratio必须在[0, 1]范围内，当前: {self.weight_reduction_ratio}")

        if self.sharpe_monitoring_threshold < 0:
            errors.append(f"sharpe_monitoring_threshold必须 >= 0，当前: {self.sharpe_monitoring_threshold}")

        if errors:
            raise ValueError(f"DecayConfig验证失败: {'; '.join(errors)}")


@dataclass
class SpartaEvolutionConfig:
    """Sparta Evolution系统总配置

    白皮书依据: 第四章 4.9 配置管理

    Attributes:
        arena: Arena配置
        simulation: 模拟配置
        z2h: Z2H配置
        decay: 衰减配置
        version: 配置版本
    """

    arena: ArenaConfig = field(default_factory=ArenaConfig)
    simulation: SimulationConfig = field(default_factory=SimulationConfig)
    z2h: Z2HConfig = field(default_factory=Z2HConfig)
    decay: DecayConfig = field(default_factory=DecayConfig)
    version: str = "1.0.0"

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SpartaEvolutionConfig":
        """从字典创建配置

        Args:
            data: 配置字典

        Returns:
            SpartaEvolutionConfig实例

        Raises:
            ValueError: 当配置无效时
        """
        try:
            arena_data = data.get("arena", {})
            simulation_data = data.get("simulation", {})
            z2h_data = data.get("z2h", {})
            decay_data = data.get("decay", {})
            version = data.get("version", "1.0.0")

            return cls(
                arena=ArenaConfig(**arena_data) if arena_data else ArenaConfig(),
                simulation=SimulationConfig(**simulation_data) if simulation_data else SimulationConfig(),
                z2h=Z2HConfig(**z2h_data) if z2h_data else Z2HConfig(),
                decay=DecayConfig(**decay_data) if decay_data else DecayConfig(),
                version=version,
            )
        except Exception as e:
            logger.error(f"从字典创建配置失败: {e}")
            raise ValueError(f"配置解析失败: {e}") from e

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典

        Returns:
            配置字典
        """
        return {
            "arena": {
                "min_ic": self.arena.min_ic,
                "min_ir": self.arena.min_ir,
                "min_sharpe": self.arena.min_sharpe,
                "max_drawdown": self.arena.max_drawdown,
                "pass_score": self.arena.pass_score,
                "reality_track_weight": self.arena.reality_track_weight,
                "hell_track_weight": self.arena.hell_track_weight,
                "cross_market_weight": self.arena.cross_market_weight,
            },
            "simulation": {
                "duration_days": self.simulation.duration_days,
                "tier_1_capital": self.simulation.tier_1_capital,
                "tier_2_capital": self.simulation.tier_2_capital,
                "tier_3_capital": self.simulation.tier_3_capital,
                "tier_4_capital": self.simulation.tier_4_capital,
                "commission_rate": self.simulation.commission_rate,
                "slippage_rate": self.simulation.slippage_rate,
                "min_return": self.simulation.min_return,
                "min_sharpe": self.simulation.min_sharpe,
                "max_drawdown": self.simulation.max_drawdown,
                "min_win_rate": self.simulation.min_win_rate,
                "min_profit_factor": self.simulation.min_profit_factor,
                "early_termination_drawdown": self.simulation.early_termination_drawdown,
            },
            "z2h": {
                "gold_sharpe_threshold": self.z2h.gold_sharpe_threshold,
                "silver_sharpe_threshold": self.z2h.silver_sharpe_threshold,
                "redis_ttl_days": self.z2h.redis_ttl_days,
                "file_storage_enabled": self.z2h.file_storage_enabled,
            },
            "decay": {
                "ic_warning_threshold": self.decay.ic_warning_threshold,
                "mild_decay_days": self.decay.mild_decay_days,
                "moderate_decay_days": self.decay.moderate_decay_days,
                "severe_decay_days": self.decay.severe_decay_days,
                "weight_reduction_ratio": self.decay.weight_reduction_ratio,
                "sharpe_monitoring_threshold": self.decay.sharpe_monitoring_threshold,
            },
            "version": self.version,
        }


def get_default_config() -> SpartaEvolutionConfig:
    """获取默认配置

    Returns:
        默认SpartaEvolutionConfig实例
    """
    return SpartaEvolutionConfig()
