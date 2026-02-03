"""认证配置管理器

白皮书依据: 第四章 4.3.2 Z2H认证系统 - 配置管理

本模块实现认证系统的配置管理功能，支持灵活配置认证标准和规则。
"""

import copy
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from loguru import logger


class MarketType(Enum):
    """市场类型"""

    A_STOCK = "a_stock"
    US_STOCK = "us_stock"
    HK_STOCK = "hk_stock"
    CRYPTO = "crypto"


class StrategyType(Enum):
    """策略类型

    白皮书依据: 第四章 4.2.2 策略类型定义
    """

    # 原有策略类型
    MOMENTUM = "momentum"
    MEAN_REVERSION = "mean_reversion"
    ARBITRAGE = "arbitrage"
    EVENT_DRIVEN = "event_driven"
    FOLLOWING = "following"

    # Chapter 4 策略类型
    PURE_FACTOR = "pure_factor"  # 单因子策略
    FACTOR_COMBO = "factor_combo"  # 多因子组合策略
    MARKET_NEUTRAL = "market_neutral"  # 市场中性策略
    DYNAMIC_WEIGHT = "dynamic_weight"  # 动态权重策略


@dataclass
class ArenaWeightConfig:
    """Arena权重配置

    白皮书依据: 第四章 4.2 斯巴达Arena四层验证

    Attributes:
        layer1_weight: 第一层权重（投研级指标）
        layer2_weight: 第二层权重（时间稳定性）
        layer3_weight: 第三层权重（防过拟合）
        layer4_weight: 第四层权重（压力测试）
    """

    layer1_weight: float = 0.35
    layer2_weight: float = 0.25
    layer3_weight: float = 0.20
    layer4_weight: float = 0.20

    def __post_init__(self):
        """验证权重总和为1.0"""
        total = self.layer1_weight + self.layer2_weight + self.layer3_weight + self.layer4_weight
        if abs(total - 1.0) > 0.001:
            raise ValueError(f"Arena权重总和必须为1.0，当前: {total}")


@dataclass
class ValidationThresholdConfig:
    """验证阈值配置

    Attributes:
        layer1_threshold: 第一层通过阈值
        layer2_threshold: 第二层通过阈值
        layer3_threshold: 第三层通过阈值
        layer4_threshold: 第四层通过阈值
        overall_threshold: 综合评分通过阈值
    """

    layer1_threshold: float = 0.75
    layer2_threshold: float = 0.70
    layer3_threshold: float = 0.65
    layer4_threshold: float = 0.70
    overall_threshold: float = 0.75


@dataclass
class CertificationLevelStandard:
    """认证等级标准配置

    白皮书依据: 第四章 4.3.2 认证等级评定标准

    Attributes:
        min_arena_score: 最低Arena综合评分
        min_layer1_score: 最低第一层评分
        min_layer2_score: 最低第二层评分
        min_layer3_score: 最低第三层评分
        min_layer4_score: 最低第四层评分
        min_simulation_sharpe: 最低模拟盘夏普比率
        max_simulation_drawdown: 最大模拟盘回撤
        min_simulation_win_rate: 最低模拟盘胜率
    """

    min_arena_score: float
    min_layer1_score: float
    min_layer2_score: float
    min_layer3_score: float
    min_layer4_score: float
    min_simulation_sharpe: float
    max_simulation_drawdown: float
    min_simulation_win_rate: float


@dataclass
class CapitalAllocationConfig:
    """资金配置规则配置

    白皮书依据: 第四章 4.3.2 资金配置规则

    Attributes:
        platinum_max_ratio: 白金级最大配置比例
        gold_max_ratio: 黄金级最大配置比例
        silver_max_ratio: 白银级最大配置比例
        position_limit_per_stock: 单股仓位限制
        sector_exposure_limit: 行业敞口限制
        max_leverage: 最大杠杆倍数
    """

    platinum_max_ratio: float = 0.20
    gold_max_ratio: float = 0.15
    silver_max_ratio: float = 0.10
    position_limit_per_stock: float = 0.05
    sector_exposure_limit: float = 0.30
    max_leverage: float = 1.0


@dataclass
class SimulationStandard:
    """模拟盘达标标准配置

    白皮书依据: 第四章 4.3.1 模拟盘验证标准

    Attributes:
        min_monthly_return: 最低月收益率
        min_sharpe_ratio: 最低夏普比率
        max_drawdown: 最大回撤
        min_win_rate: 最低胜率
        max_var_95: 最大95% VaR
        min_profit_factor: 最低盈利因子
        max_turnover_rate: 最大月换手率
        min_calmar_ratio: 最低卡玛比率
        max_benchmark_correlation: 最大基准相关性
        min_information_ratio: 最低信息比率
    """

    min_monthly_return: float = 0.05
    min_sharpe_ratio: float = 1.2
    max_drawdown: float = 0.15
    min_win_rate: float = 0.55
    max_var_95: float = 0.05
    min_profit_factor: float = 1.3
    max_turnover_rate: float = 5.0
    min_calmar_ratio: float = 1.0
    max_benchmark_correlation: float = 0.7
    min_information_ratio: float = 0.8


@dataclass
class ConfigChangeRecord:
    """配置变更记录

    Attributes:
        change_id: 变更ID
        config_type: 配置类型
        config_key: 配置键
        old_value: 旧值
        new_value: 新值
        changed_by: 变更人
        changed_at: 变更时间
        effective_at: 生效时间
        reason: 变更原因
    """

    change_id: str
    config_type: str
    config_key: str
    old_value: Any
    new_value: Any
    changed_by: str
    changed_at: datetime
    effective_at: datetime
    reason: str


class CertificationConfigManager:
    """认证配置管理器

    白皮书依据: 第四章 4.3.2 Z2H认证系统 - 配置管理

    实现认证系统的配置管理功能：
    - Arena权重配置
    - 验证阈值配置
    - 认证等级标准配置
    - 资金配置规则配置
    - 模拟盘达标标准配置
    - 市场类型配置
    - 策略类型配置
    - 配置变更历史记录
    """

    def __init__(self):
        """初始化认证配置管理器"""
        # Arena权重配置
        self.arena_weights = ArenaWeightConfig()

        # 验证阈值配置
        self.validation_thresholds = ValidationThresholdConfig()

        # 认证等级标准配置
        self.certification_standards = {
            "platinum": CertificationLevelStandard(
                min_arena_score=0.90,
                min_layer1_score=0.95,
                min_layer2_score=0.85,
                min_layer3_score=0.80,
                min_layer4_score=0.85,
                min_simulation_sharpe=2.5,
                max_simulation_drawdown=0.10,
                min_simulation_win_rate=0.65,
            ),
            "gold": CertificationLevelStandard(
                min_arena_score=0.80,
                min_layer1_score=0.85,
                min_layer2_score=0.75,
                min_layer3_score=0.70,
                min_layer4_score=0.75,
                min_simulation_sharpe=2.0,
                max_simulation_drawdown=0.12,
                min_simulation_win_rate=0.60,
            ),
            "silver": CertificationLevelStandard(
                min_arena_score=0.75,
                min_layer1_score=0.80,
                min_layer2_score=0.70,
                min_layer3_score=0.60,
                min_layer4_score=0.70,
                min_simulation_sharpe=1.5,
                max_simulation_drawdown=0.15,
                min_simulation_win_rate=0.55,
            ),
        }

        # 资金配置规则
        self.capital_allocation = CapitalAllocationConfig()

        # 模拟盘达标标准
        self.simulation_standards = SimulationStandard()

        # 市场类型特定配置
        self.market_configs: Dict[MarketType, Dict[str, Any]] = {
            MarketType.A_STOCK: {"trading_hours": "09:30-15:00", "min_liquidity": 1000000, "max_position_size": 0.05},
            MarketType.US_STOCK: {"trading_hours": "09:30-16:00", "min_liquidity": 5000000, "max_position_size": 0.10},
            MarketType.HK_STOCK: {"trading_hours": "09:30-16:00", "min_liquidity": 2000000, "max_position_size": 0.08},
        }

        # 策略类型特定配置
        self.strategy_configs: Dict[StrategyType, Dict[str, Any]] = {
            StrategyType.MOMENTUM: {"min_holding_period": 5, "max_turnover": 3.0, "min_sharpe": 1.5},
            StrategyType.MEAN_REVERSION: {"min_holding_period": 1, "max_turnover": 10.0, "min_sharpe": 1.2},
            StrategyType.ARBITRAGE: {"min_holding_period": 0.1, "max_turnover": 50.0, "min_sharpe": 2.0},
        }

        # 配置变更历史
        self.change_history: List[ConfigChangeRecord] = []

        # 变更ID计数器
        self._change_id_counter = 0

        logger.info("初始化CertificationConfigManager完成")

    def update_arena_weights(  # pylint: disable=too-many-positional-arguments
        self,
        layer1_weight: Optional[float] = None,
        layer2_weight: Optional[float] = None,
        layer3_weight: Optional[float] = None,
        layer4_weight: Optional[float] = None,
        changed_by: str = "system",
        reason: str = "配置更新",
    ) -> ArenaWeightConfig:
        """更新Arena权重配置

        白皮书依据: 第四章 4.2 Arena权重配置

        Args:
            layer1_weight: 第一层权重
            layer2_weight: 第二层权重
            layer3_weight: 第三层权重
            layer4_weight: 第四层权重
            changed_by: 变更人
            reason: 变更原因

        Returns:
            ArenaWeightConfig: 更新后的配置

        Raises:
            ValueError: 当权重总和不为1.0时
        """
        old_config = copy.deepcopy(self.arena_weights)

        # 更新权重
        if layer1_weight is not None:
            self.arena_weights.layer1_weight = layer1_weight
        if layer2_weight is not None:
            self.arena_weights.layer2_weight = layer2_weight
        if layer3_weight is not None:
            self.arena_weights.layer3_weight = layer3_weight
        if layer4_weight is not None:
            self.arena_weights.layer4_weight = layer4_weight

        # 验证权重总和
        total = (
            self.arena_weights.layer1_weight
            + self.arena_weights.layer2_weight
            + self.arena_weights.layer3_weight
            + self.arena_weights.layer4_weight
        )

        if abs(total - 1.0) > 0.001:
            # 恢复旧配置
            self.arena_weights = old_config
            raise ValueError(f"Arena权重总和必须为1.0，当前: {total}")

        # 记录变更
        self._record_change(
            config_type="arena_weights",
            config_key="all",
            old_value=asdict(old_config),
            new_value=asdict(self.arena_weights),
            changed_by=changed_by,
            reason=reason,
        )

        logger.info(f"Arena权重配置已更新: {asdict(self.arena_weights)}")

        return self.arena_weights

    def update_validation_thresholds(  # pylint: disable=too-many-positional-arguments
        self,
        layer1_threshold: Optional[float] = None,
        layer2_threshold: Optional[float] = None,
        layer3_threshold: Optional[float] = None,
        layer4_threshold: Optional[float] = None,
        overall_threshold: Optional[float] = None,
        changed_by: str = "system",
        reason: str = "配置更新",
    ) -> ValidationThresholdConfig:
        """更新验证阈值配置

        白皮书依据: 第四章 4.2 验证阈值配置

        Args:
            layer1_threshold: 第一层阈值
            layer2_threshold: 第二层阈值
            layer3_threshold: 第三层阈值
            layer4_threshold: 第四层阈值
            overall_threshold: 综合阈值
            changed_by: 变更人
            reason: 变更原因

        Returns:
            ValidationThresholdConfig: 更新后的配置
        """
        old_config = copy.deepcopy(self.validation_thresholds)

        # 更新阈值
        if layer1_threshold is not None:
            self.validation_thresholds.layer1_threshold = layer1_threshold
        if layer2_threshold is not None:
            self.validation_thresholds.layer2_threshold = layer2_threshold
        if layer3_threshold is not None:
            self.validation_thresholds.layer3_threshold = layer3_threshold
        if layer4_threshold is not None:
            self.validation_thresholds.layer4_threshold = layer4_threshold
        if overall_threshold is not None:
            self.validation_thresholds.overall_threshold = overall_threshold

        # 记录变更
        self._record_change(
            config_type="validation_thresholds",
            config_key="all",
            old_value=asdict(old_config),
            new_value=asdict(self.validation_thresholds),
            changed_by=changed_by,
            reason=reason,
        )

        logger.info(f"验证阈值配置已更新: {asdict(self.validation_thresholds)}")

        return self.validation_thresholds

    def update_certification_standard(
        self, level: str, standard: CertificationLevelStandard, changed_by: str = "system", reason: str = "配置更新"
    ) -> CertificationLevelStandard:
        """更新认证等级标准配置

        白皮书依据: 第四章 4.3.2 认证等级标准

        Args:
            level: 认证等级（platinum/gold/silver）
            standard: 新的标准配置
            changed_by: 变更人
            reason: 变更原因

        Returns:
            CertificationLevelStandard: 更新后的配置

        Raises:
            ValueError: 当等级不存在时
        """
        if level not in self.certification_standards:
            raise ValueError(f"未知的认证等级: {level}")

        old_standard = copy.deepcopy(self.certification_standards[level])

        # 更新标准
        self.certification_standards[level] = standard

        # 记录变更
        self._record_change(
            config_type="certification_standard",
            config_key=level,
            old_value=asdict(old_standard),
            new_value=asdict(standard),
            changed_by=changed_by,
            reason=reason,
        )

        logger.info(f"认证等级标准已更新: {level} = {asdict(standard)}")

        return standard

    def update_capital_allocation(  # pylint: disable=too-many-positional-arguments
        self,
        platinum_max_ratio: Optional[float] = None,
        gold_max_ratio: Optional[float] = None,
        silver_max_ratio: Optional[float] = None,
        position_limit_per_stock: Optional[float] = None,
        sector_exposure_limit: Optional[float] = None,
        max_leverage: Optional[float] = None,
        changed_by: str = "system",
        reason: str = "配置更新",
    ) -> CapitalAllocationConfig:
        """更新资金配置规则

        白皮书依据: 第四章 4.3.2 资金配置规则

        Args:
            platinum_max_ratio: 白金级最大配置比例
            gold_max_ratio: 黄金级最大配置比例
            silver_max_ratio: 白银级最大配置比例
            position_limit_per_stock: 单股仓位限制
            sector_exposure_limit: 行业敞口限制
            max_leverage: 最大杠杆倍数
            changed_by: 变更人
            reason: 变更原因

        Returns:
            CapitalAllocationConfig: 更新后的配置
        """
        old_config = copy.deepcopy(self.capital_allocation)

        # 更新配置
        if platinum_max_ratio is not None:
            self.capital_allocation.platinum_max_ratio = platinum_max_ratio
        if gold_max_ratio is not None:
            self.capital_allocation.gold_max_ratio = gold_max_ratio
        if silver_max_ratio is not None:
            self.capital_allocation.silver_max_ratio = silver_max_ratio
        if position_limit_per_stock is not None:
            self.capital_allocation.position_limit_per_stock = position_limit_per_stock
        if sector_exposure_limit is not None:
            self.capital_allocation.sector_exposure_limit = sector_exposure_limit
        if max_leverage is not None:
            self.capital_allocation.max_leverage = max_leverage

        # 记录变更
        self._record_change(
            config_type="capital_allocation",
            config_key="all",
            old_value=asdict(old_config),
            new_value=asdict(self.capital_allocation),
            changed_by=changed_by,
            reason=reason,
        )

        logger.info(f"资金配置规则已更新: {asdict(self.capital_allocation)}")

        return self.capital_allocation

    def update_simulation_standards(
        self, standards: Dict[str, float], changed_by: str = "system", reason: str = "配置更新"
    ) -> SimulationStandard:
        """更新模拟盘达标标准

        白皮书依据: 第四章 4.3.1 模拟盘验证标准

        Args:
            standards: 标准字典
            changed_by: 变更人
            reason: 变更原因

        Returns:
            SimulationStandard: 更新后的配置
        """
        old_config = copy.deepcopy(self.simulation_standards)

        # 更新标准
        for key, value in standards.items():
            if hasattr(self.simulation_standards, key):
                setattr(self.simulation_standards, key, value)

        # 记录变更
        self._record_change(
            config_type="simulation_standards",
            config_key="all",
            old_value=asdict(old_config),
            new_value=asdict(self.simulation_standards),
            changed_by=changed_by,
            reason=reason,
        )

        logger.info(f"模拟盘达标标准已更新: {asdict(self.simulation_standards)}")

        return self.simulation_standards

    def update_market_config(
        self, market_type: MarketType, config: Dict[str, Any], changed_by: str = "system", reason: str = "配置更新"
    ) -> Dict[str, Any]:
        """更新市场类型配置

        白皮书依据: 第四章 4.3.2 市场类型配置

        Args:
            market_type: 市场类型
            config: 配置字典
            changed_by: 变更人
            reason: 变更原因

        Returns:
            Dict[str, Any]: 更新后的配置
        """
        old_config = copy.deepcopy(self.market_configs.get(market_type, {}))

        # 更新配置
        if market_type not in self.market_configs:
            self.market_configs[market_type] = {}

        self.market_configs[market_type].update(config)

        # 记录变更
        self._record_change(
            config_type="market_config",
            config_key=market_type.value,
            old_value=old_config,
            new_value=self.market_configs[market_type],
            changed_by=changed_by,
            reason=reason,
        )

        logger.info(f"市场类型配置已更新: {market_type.value} = {self.market_configs[market_type]}")

        return self.market_configs[market_type]

    def update_strategy_config(
        self, strategy_type: StrategyType, config: Dict[str, Any], changed_by: str = "system", reason: str = "配置更新"
    ) -> Dict[str, Any]:
        """更新策略类型配置

        白皮书依据: 第四章 4.3.2 策略类型配置

        Args:
            strategy_type: 策略类型
            config: 配置字典
            changed_by: 变更人
            reason: 变更原因

        Returns:
            Dict[str, Any]: 更新后的配置
        """
        old_config = copy.deepcopy(self.strategy_configs.get(strategy_type, {}))

        # 更新配置
        if strategy_type not in self.strategy_configs:
            self.strategy_configs[strategy_type] = {}

        self.strategy_configs[strategy_type].update(config)

        # 记录变更
        self._record_change(
            config_type="strategy_config",
            config_key=strategy_type.value,
            old_value=old_config,
            new_value=self.strategy_configs[strategy_type],
            changed_by=changed_by,
            reason=reason,
        )

        logger.info(f"策略类型配置已更新: {strategy_type.value} = {self.strategy_configs[strategy_type]}")

        return self.strategy_configs[strategy_type]

    def get_change_history(
        self,
        config_type: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        changed_by: Optional[str] = None,
    ) -> List[ConfigChangeRecord]:
        """查询配置变更历史

        Args:
            config_type: 配置类型，None表示所有类型
            start_date: 开始日期，None表示不限
            end_date: 结束日期，None表示不限
            changed_by: 变更人，None表示所有人

        Returns:
            List[ConfigChangeRecord]: 变更记录列表
        """
        results = []

        for record in self.change_history:
            # 配置类型过滤
            if config_type and record.config_type != config_type:
                continue

            # 日期范围过滤
            if start_date and record.changed_at < start_date:
                continue
            if end_date and record.changed_at > end_date:
                continue

            # 变更人过滤
            if changed_by and record.changed_by != changed_by:
                continue

            results.append(record)

        return results

    def export_config(self) -> Dict[str, Any]:
        """导出完整配置

        Returns:
            Dict[str, Any]: 配置字典
        """
        return {
            "arena_weights": asdict(self.arena_weights),
            "validation_thresholds": asdict(self.validation_thresholds),
            "certification_standards": {
                level: asdict(standard) for level, standard in self.certification_standards.items()
            },
            "capital_allocation": asdict(self.capital_allocation),
            "simulation_standards": asdict(self.simulation_standards),
            "market_configs": {market_type.value: config for market_type, config in self.market_configs.items()},
            "strategy_configs": {
                strategy_type.value: config for strategy_type, config in self.strategy_configs.items()
            },
        }

    def import_config(self, config: Dict[str, Any], changed_by: str = "system", reason: str = "配置导入") -> None:
        """导入完整配置

        Args:
            config: 配置字典
            changed_by: 变更人
            reason: 变更原因
        """
        # 导入Arena权重
        if "arena_weights" in config:
            self.arena_weights = ArenaWeightConfig(**config["arena_weights"])

        # 导入验证阈值
        if "validation_thresholds" in config:
            self.validation_thresholds = ValidationThresholdConfig(**config["validation_thresholds"])

        # 导入认证标准
        if "certification_standards" in config:
            for level, standard_dict in config["certification_standards"].items():
                self.certification_standards[level] = CertificationLevelStandard(**standard_dict)

        # 导入资金配置
        if "capital_allocation" in config:
            self.capital_allocation = CapitalAllocationConfig(**config["capital_allocation"])

        # 导入模拟盘标准
        if "simulation_standards" in config:
            self.simulation_standards = SimulationStandard(**config["simulation_standards"])

        # 记录变更
        self._record_change(
            config_type="全局配置",
            config_key="import",
            old_value={},
            new_value=config,
            changed_by=changed_by,
            reason=reason,
        )

        logger.info("配置导入完成")

    def _record_change(  # pylint: disable=too-many-positional-arguments
        self, config_type: str, config_key: str, old_value: Any, new_value: Any, changed_by: str, reason: str
    ) -> ConfigChangeRecord:
        """记录配置变更（内部方法）

        Args:
            config_type: 配置类型
            config_key: 配置键
            old_value: 旧值
            new_value: 新值
            changed_by: 变更人
            reason: 变更原因

        Returns:
            ConfigChangeRecord: 变更记录
        """
        self._change_id_counter += 1
        change_id = f"CONFIG-{self._change_id_counter:06d}"

        now = datetime.now()

        record = ConfigChangeRecord(
            change_id=change_id,
            config_type=config_type,
            config_key=config_key,
            old_value=old_value,
            new_value=new_value,
            changed_by=changed_by,
            changed_at=now,
            effective_at=now,
            reason=reason,
        )

        self.change_history.append(record)

        logger.info(f"配置变更已记录: change_id={change_id}, " f"type={config_type}, key={config_key}, by={changed_by}")

        return record
