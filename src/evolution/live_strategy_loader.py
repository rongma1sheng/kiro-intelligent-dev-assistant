"""实盘策略加载器

白皮书依据: 第四章 4.2 斯巴达竞技场

负责从Arena测试结果加载策略配置，实现参数继承。
"""

from datetime import datetime
from typing import Any, Dict, Optional

from loguru import logger

from src.strategies.base_strategy import Strategy
from src.strategies.data_models import ArenaTestResult, StrategyConfig, StrategyMetadata


class LiveStrategyLoader:
    """实盘策略加载器

    白皮书依据: Requirement 10

    职责：
    - 从Arena结果加载策略配置
    - 实现参数验证和完整性检查
    - 记录参数来源日志
    - 确保实盘策略使用Arena进化出的最优参数
    """

    def __init__(self):
        """初始化实盘策略加载器"""
        # 加载历史记录
        self.load_history: list[Dict[str, Any]] = []

        logger.info("LiveStrategyLoader初始化完成")

    async def load_strategy_config_from_arena(
        self, strategy_metadata: StrategyMetadata, target_tier: str
    ) -> StrategyConfig:
        """从Arena结果加载策略配置

        白皮书依据: Requirement 10.1, 10.2

        Args:
            strategy_metadata: 策略元数据（包含Arena测试结果）
            target_tier: 目标档位

        Returns:
            策略配置

        Raises:
            ValueError: 当Arena结果不存在或不完整时
        """
        logger.info(f"从Arena加载策略配置 - " f"策略: {strategy_metadata.strategy_name}, " f"目标档位: {target_tier}")

        # 1. 验证策略元数据
        self._validate_metadata(strategy_metadata)

        # 2. 选择合适的Arena测试结果
        arena_result = self._select_arena_result(strategy_metadata, target_tier)

        # 3. 从Arena结果创建配置
        config = StrategyConfig.from_arena_result(arena_result)

        # 4. 验证配置完整性
        self._validate_config(config)

        # 5. 记录参数来源
        await self._log_parameter_source(
            strategy_name=strategy_metadata.strategy_name,
            target_tier=target_tier,
            arena_tier=arena_result.test_tier,
            config=config,
        )

        logger.info(
            f"策略配置加载完成 - "
            f"策略: {strategy_metadata.strategy_name}, "
            f"Arena档位: {arena_result.test_tier}, "
            f"目标档位: {target_tier}"
        )

        return config

    async def load_strategy_for_tier(
        self, strategy_metadata: StrategyMetadata, tier: str, strategy_class: type
    ) -> Strategy:
        """为指定档位加载策略实例

        白皮书依据: Requirement 10.1

        Args:
            strategy_metadata: 策略元数据
            tier: 资金档位
            strategy_class: 策略类

        Returns:
            策略实例
        """
        logger.info(f"为档位加载策略 - " f"策略: {strategy_metadata.strategy_name}, " f"档位: {tier}")

        # 1. 加载配置
        config = await self.load_strategy_config_from_arena(strategy_metadata, tier)

        # 2. 创建策略实例
        strategy = strategy_class(name=strategy_metadata.strategy_name, config=config)

        logger.info(f"策略实例创建完成: {strategy.name}")

        return strategy

    def _validate_metadata(self, metadata: StrategyMetadata) -> None:
        """验证策略元数据（内部方法）

        Args:
            metadata: 策略元数据

        Raises:
            ValueError: 当元数据不完整时
        """
        if not metadata.z2h_certified:
            raise ValueError(f"策略未获得Z2H认证: {metadata.strategy_name}")

        if not metadata.arena_results:
            raise ValueError(f"策略缺少Arena测试结果: {metadata.strategy_name}")

        if not metadata.best_tier:
            raise ValueError(f"策略未识别最佳档位: {metadata.strategy_name}")

        logger.debug(f"元数据验证通过: {metadata.strategy_name}")

    def _select_arena_result(self, metadata: StrategyMetadata, target_tier: str) -> ArenaTestResult:
        """选择合适的Arena测试结果（内部方法）

        白皮书依据: Requirement 10.1

        选择逻辑：
        - Tier1-4: 使用对应档位的Arena结果
        - Tier5: 使用Tier4的Arena结果
        - Tier6: 使用Tier4的Arena结果

        Args:
            metadata: 策略元数据
            target_tier: 目标档位

        Returns:
            Arena测试结果

        Raises:
            ValueError: 当找不到合适的Arena结果时
        """
        # Tier5-6使用Tier4的结果
        tier_mapping = {
            "tier1_micro": "tier1_micro",
            "tier2_small": "tier2_small",
            "tier3_medium": "tier3_medium",
            "tier4_large": "tier4_large",
            "tier5_million": "tier4_large",  # Tier5使用Tier4参数
            "tier6_ten_million": "tier4_large",  # Tier6使用Tier4参数
        }

        arena_tier = tier_mapping.get(target_tier)

        if not arena_tier:
            raise ValueError(f"无效的目标档位: {target_tier}")

        arena_result = metadata.arena_results.get(arena_tier)

        if not arena_result:
            # 降级：使用最佳档位的结果
            logger.warning(f"目标档位{target_tier}对应的Arena结果不存在，" f"使用最佳档位{metadata.best_tier}的结果")
            arena_result = metadata.arena_results.get(metadata.best_tier)

        if not arena_result:
            raise ValueError(
                f"找不到合适的Arena测试结果 - " f"策略: {metadata.strategy_name}, " f"目标档位: {target_tier}"
            )

        logger.debug(f"选择Arena结果 - " f"目标档位: {target_tier}, " f"Arena档位: {arena_result.test_tier}")

        return arena_result

    def _validate_config(self, config: StrategyConfig) -> None:
        """验证配置完整性（内部方法）

        白皮书依据: Requirement 10.3

        Args:
            config: 策略配置

        Raises:
            ValueError: 当配置不完整或无效时
        """
        # 验证必需字段
        required_fields = [
            "strategy_name",
            "capital_tier",
            "max_position",
            "max_single_stock",
            "max_industry",
            "stop_loss_pct",
            "take_profit_pct",
        ]

        for field in required_fields:
            if not hasattr(config, field):
                raise ValueError(f"配置缺少必需字段: {field}")

            value = getattr(config, field)
            if value is None:
                raise ValueError(f"配置字段值为None: {field}")

        # 验证参数范围（已在StrategyConfig.__post_init__中验证）

        logger.debug(f"配置验证通过: {config.strategy_name}")

    async def _log_parameter_source(
        self, strategy_name: str, target_tier: str, arena_tier: str, config: StrategyConfig
    ) -> None:
        """记录参数来源日志

        白皮书依据: Requirement 10.8

        Args:
            strategy_name: 策略名称
            target_tier: 目标档位
            arena_tier: Arena测试档位
            config: 策略配置
        """
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "strategy_name": strategy_name,
            "target_tier": target_tier,
            "arena_tier": arena_tier,
            "parameters": {
                "max_position": config.max_position,
                "max_single_stock": config.max_single_stock,
                "max_industry": config.max_industry,
                "stop_loss_pct": config.stop_loss_pct,
                "take_profit_pct": config.take_profit_pct,
                "trading_frequency": config.trading_frequency,
                "holding_period_days": config.holding_period_days,
            },
        }

        self.load_history.append(log_entry)

        logger.info(
            f"参数来源已记录 - " f"策略: {strategy_name}, " f"Arena档位: {arena_tier} → 目标档位: {target_tier}"
        )

    def get_load_history(self, strategy_name: Optional[str] = None) -> list[Dict[str, Any]]:
        """获取加载历史

        Args:
            strategy_name: 策略名称（可选），如果指定则只返回该策略的历史

        Returns:
            加载历史列表
        """
        if strategy_name:
            return [entry for entry in self.load_history if entry["strategy_name"] == strategy_name]
        return self.load_history.copy()


class ParameterInheritanceValidator:
    """参数继承验证器

    白皮书依据: Requirement 10.4, 10.5, 10.6, 10.7

    验证实盘策略的参数是否正确继承自Arena测试结果
    """

    def __init__(self):
        """初始化参数继承验证器"""
        logger.info("ParameterInheritanceValidator初始化完成")

    def validate_parameter_inheritance(
        self, live_config: StrategyConfig, arena_result: ArenaTestResult
    ) -> Dict[str, Any]:
        """验证参数继承

        Args:
            live_config: 实盘策略配置
            arena_result: Arena测试结果

        Returns:
            验证结果 {
                'valid': bool,
                'matched_params': List[str],
                'mismatched_params': List[Dict[str, Any]]
            }
        """
        logger.info(f"验证参数继承 - 策略: {live_config.strategy_name}")

        matched_params = []
        mismatched_params = []

        # 需要验证的参数
        params_to_check = [
            "max_position",
            "max_single_stock",
            "max_industry",
            "stop_loss_pct",
            "take_profit_pct",
            "trading_frequency",
            "holding_period_days",
        ]

        for param in params_to_check:
            live_value = getattr(live_config, param, None)
            arena_value = arena_result.evolved_params.get(param)

            if live_value == arena_value:
                matched_params.append(param)
            else:
                mismatched_params.append({"param": param, "live_value": live_value, "arena_value": arena_value})

        valid = len(mismatched_params) == 0

        if valid:
            logger.info(f"参数继承验证通过 - 所有{len(matched_params)}个参数匹配")
        else:
            logger.warning(f"参数继承验证失败 - " f"匹配: {len(matched_params)}, " f"不匹配: {len(mismatched_params)}")

        return {"valid": valid, "matched_params": matched_params, "mismatched_params": mismatched_params}
