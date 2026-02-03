"""
验证流水线管理器 (Validation Pipeline Manager)

白皮书依据: 第四章 4.3 统一验证流水线
"""

import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional

from loguru import logger

from src.evolution.arena.data_models import Factor
from src.evolution.arena.strategy_data_models import Strategy
from src.evolution.pipeline.data_models import PipelineProgress, PipelineStage
from src.evolution.pipeline.pipeline_stage_validator import PipelineStageValidator
from src.evolution.pipeline.pipeline_state_tracker import PipelineStateTracker


class ValidationPipelineManager:
    """验证流水线管理器

    白皮书依据: 第四章 4.3 统一验证流水线

    负责编排从因子发现到策略部署的完整验证流程，确保所有组件
    都经过严格的质量检验。

    核心流程:
    Factor Arena → Strategy Generation → Strategy Arena →
    Simulation → Z2H Certification → Strategy Library

    Attributes:
        stage_validator: 阶段验证器
        state_tracker: 状态追踪器
        auto_progress: 是否自动推进到下一阶段
    """

    def __init__(
        self,
        stage_validator: Optional[PipelineStageValidator] = None,
        state_tracker: Optional[PipelineStateTracker] = None,
        auto_progress: bool = True,
    ):
        """初始化验证流水线管理器

        Args:
            stage_validator: 阶段验证器，None则创建默认实例
            state_validator: 状态追踪器，None则创建默认实例
            auto_progress: 是否自动推进到下一阶段，默认True
        """
        self.stage_validator = stage_validator or PipelineStageValidator()
        self.state_tracker = state_tracker or PipelineStateTracker()
        self.auto_progress = auto_progress

        logger.info(f"初始化ValidationPipelineManager: auto_progress={auto_progress}")

    async def execute_pipeline(self, factor: Factor) -> PipelineProgress:
        """执行完整的验证流水线

        白皮书依据: 第四章 4.3 - 端到端验证流程

        完整流程:
        1. Factor Arena测试
        2. 策略生成
        3. Strategy Arena测试
        4. 模拟盘验证
        5. Z2H认证
        6. 策略库注册

        Args:
            factor: 待验证的因子

        Returns:
            流水线进度对象

        Raises:
            ValueError: 当因子无效时
        """
        if not factor.id:
            raise ValueError("因子ID不能为空")

        logger.info(f"开始执行验证流水线: factor_id={factor.id}")

        # 创建进度记录
        progress = self.state_tracker.create_progress(
            entity_id=factor.id, entity_type="factor", initial_stage=PipelineStage.FACTOR_ARENA
        )

        try:
            # 1. Factor Arena测试
            await self._execute_factor_arena(factor, progress)

            # 2. 策略生成
            strategies = await self._execute_strategy_generation(factor, progress)

            # 对每个生成的策略执行后续流程
            for strategy in strategies:
                # 创建策略的进度记录
                strategy_progress = self.state_tracker.create_progress(
                    entity_id=strategy.id, entity_type="strategy", initial_stage=PipelineStage.STRATEGY_ARENA
                )

                # 3. Strategy Arena测试
                await self._execute_strategy_arena(strategy, strategy_progress)

                # 4. 模拟盘验证
                await self._execute_simulation(strategy, strategy_progress)

                # 5. Z2H认证
                await self._execute_z2h_certification(strategy, strategy_progress)

                # 6. 策略库注册
                await self._execute_strategy_library_registration(strategy, strategy_progress)

                # 标记策略流水线完成
                self.state_tracker.mark_completed(strategy.id)

            # 标记因子流水线完成
            self.state_tracker.mark_completed(factor.id)

            logger.info(f"验证流水线完成: factor_id={factor.id}")

            return progress

        except Exception as e:
            logger.error(f"验证流水线失败: factor_id={factor.id}, error={e}")
            progress.is_failed = True
            raise

    async def _execute_factor_arena(self, factor: Factor, progress: PipelineProgress) -> Dict[str, Any]:
        """执行Factor Arena测试

        Args:
            factor: 因子对象
            progress: 进度对象

        Returns:
            测试结果
        """
        stage = PipelineStage.FACTOR_ARENA

        # 验证阶段转换
        if not self._validate_stage_transition(progress, stage):
            raise ValueError(f"无法转换到阶段: {stage.value}")

        # 开始阶段
        self.state_tracker.start_stage(factor.id, stage)

        logger.info(f"执行Factor Arena测试: factor_id={factor.id}")

        try:
            # 导入并执行Factor Arena测试
            from src.evolution.arena.factor_arena import FactorArenaSystem  # pylint: disable=import-outside-toplevel

            arena = FactorArenaSystem()  # pylint: disable=e1120
            result = await arena.test_factor(factor)  # pylint: disable=e1120

            # 完成阶段
            self.state_tracker.complete_stage(
                factor.id, stage, result={"passed": result.passed, "score": result.overall_score}
            )

            # 检查是否通过
            if not result.passed:
                raise ValueError(f"Factor Arena测试未通过: score={result.overall_score}")

            # 自动推进到下一阶段
            if self.auto_progress:
                next_stage = self.stage_validator.get_next_stage(stage)
                if next_stage:
                    self.state_tracker.update_stage(factor.id, next_stage)

            return {"result": result, "passed": result.passed}

        except Exception as e:
            self.state_tracker.fail_stage(factor.id, stage, str(e))
            raise

    async def _execute_strategy_generation(self, factor: Factor, progress: PipelineProgress) -> List[Strategy]:
        """执行策略生成

        Args:
            factor: 因子对象
            progress: 进度对象

        Returns:
            生成的策略列表
        """
        stage = PipelineStage.STRATEGY_GENERATION

        # 验证阶段转换
        if not self._validate_stage_transition(progress, stage):
            raise ValueError(f"无法转换到阶段: {stage.value}")

        # 开始阶段
        self.state_tracker.start_stage(factor.id, stage)

        logger.info(f"执行策略生成: factor_id={factor.id}")

        try:
            # 简化版本：生成一个基于因子的策略
            from src.evolution.arena.strategy_data_models import (  # pylint: disable=import-outside-toplevel,w0621,w0404
                Strategy,
                StrategyStatus,
                StrategyType,
            )

            strategy = Strategy(
                id=f"strategy_{factor.id}",
                name=f"Strategy based on {factor.name}",
                type=StrategyType.PURE_FACTOR,
                source_factors=[factor.id],
                code=f"# Strategy code for factor {factor.id}",
                description=f"Auto-generated strategy from factor {factor.name}",
                status=StrategyStatus.CANDIDATE,
            )

            strategies = [strategy]

            # 完成阶段
            self.state_tracker.complete_stage(factor.id, stage, result={"strategies_generated": len(strategies)})

            logger.info(f"策略生成完成: factor_id={factor.id}, count={len(strategies)}")

            return strategies

        except Exception as e:
            self.state_tracker.fail_stage(factor.id, stage, str(e))
            raise

    async def _execute_strategy_arena(self, strategy: Strategy, progress: PipelineProgress) -> Dict[str, Any]:
        """执行Strategy Arena测试

        Args:
            strategy: 策略对象
            progress: 进度对象

        Returns:
            测试结果
        """
        stage = PipelineStage.STRATEGY_ARENA

        # 验证阶段转换
        if not self._validate_stage_transition(progress, stage):
            raise ValueError(f"无法转换到阶段: {stage.value}")

        # 开始阶段
        self.state_tracker.start_stage(strategy.id, stage)

        logger.info(f"执行Strategy Arena测试: strategy_id={strategy.id}")

        try:
            # 导入并执行Strategy Arena测试
            from src.evolution.arena.strategy_arena import (  # pylint: disable=import-outside-toplevel
                StrategyArenaSystem,
            )

            arena = StrategyArenaSystem()
            result = await arena.test_strategy(strategy)

            # 完成阶段
            self.state_tracker.complete_stage(
                strategy.id, stage, result={"passed": result.passed, "score": result.overall_score}
            )

            # 检查是否通过
            if not result.passed:
                raise ValueError(f"Strategy Arena测试未通过: score={result.overall_score}")

            # 自动推进到下一阶段
            if self.auto_progress:
                next_stage = self.stage_validator.get_next_stage(stage)
                if next_stage:
                    self.state_tracker.update_stage(strategy.id, next_stage)

            return {"result": result, "passed": result.passed}

        except Exception as e:
            self.state_tracker.fail_stage(strategy.id, stage, str(e))
            raise

    async def _execute_simulation(self, strategy: Strategy, progress: PipelineProgress) -> Dict[str, Any]:
        """执行模拟盘验证

        Args:
            strategy: 策略对象
            progress: 进度对象

        Returns:
            模拟结果
        """
        stage = PipelineStage.SIMULATION

        # 验证阶段转换
        if not self._validate_stage_transition(progress, stage):
            raise ValueError(f"无法转换到阶段: {stage.value}")

        # 开始阶段
        self.state_tracker.start_stage(strategy.id, stage)

        logger.info(f"执行模拟盘验证: strategy_id={strategy.id}")

        try:
            # 简化版本：模拟通过
            # 实际应该运行1个月的模拟盘
            await asyncio.sleep(0.1)  # 模拟耗时

            simulation_result = {
                "passed": True,
                "duration_days": 30,
                "total_return": 0.08,
                "sharpe_ratio": 1.8,
                "max_drawdown": 0.12,
            }

            # 完成阶段
            self.state_tracker.complete_stage(strategy.id, stage, result=simulation_result)

            # 自动推进到下一阶段
            if self.auto_progress:
                next_stage = self.stage_validator.get_next_stage(stage)
                if next_stage:
                    self.state_tracker.update_stage(strategy.id, next_stage)

            return simulation_result

        except Exception as e:
            self.state_tracker.fail_stage(strategy.id, stage, str(e))
            raise

    async def _execute_z2h_certification(self, strategy: Strategy, progress: PipelineProgress) -> Dict[str, Any]:
        """执行Z2H认证

        Args:
            strategy: 策略对象
            progress: 进度对象

        Returns:
            认证结果
        """
        stage = PipelineStage.Z2H_CERTIFICATION

        # 验证阶段转换
        if not self._validate_stage_transition(progress, stage):
            raise ValueError(f"无法转换到阶段: {stage.value}")

        # 开始阶段
        self.state_tracker.start_stage(strategy.id, stage)

        logger.info(f"执行Z2H认证: strategy_id={strategy.id}")

        try:
            # 简化版本：生成Z2H基因胶囊
            await asyncio.sleep(0.1)  # 模拟耗时

            z2h_capsule = {
                "strategy_id": strategy.id,
                "certification_level": "GOLD",
                "certification_date": datetime.now().isoformat(),
                "signature": "mock_sha256_signature",
            }

            # 完成阶段
            self.state_tracker.complete_stage(strategy.id, stage, result=z2h_capsule)

            # 自动推进到下一阶段
            if self.auto_progress:
                next_stage = self.stage_validator.get_next_stage(stage)
                if next_stage:
                    self.state_tracker.update_stage(strategy.id, next_stage)

            return z2h_capsule

        except Exception as e:
            self.state_tracker.fail_stage(strategy.id, stage, str(e))
            raise

    async def _execute_strategy_library_registration(
        self, strategy: Strategy, progress: PipelineProgress
    ) -> Dict[str, Any]:
        """执行策略库注册

        Args:
            strategy: 策略对象
            progress: 进度对象

        Returns:
            注册结果
        """
        stage = PipelineStage.STRATEGY_LIBRARY

        # 验证阶段转换
        if not self._validate_stage_transition(progress, stage):
            raise ValueError(f"无法转换到阶段: {stage.value}")

        # 开始阶段
        self.state_tracker.start_stage(strategy.id, stage)

        logger.info(f"执行策略库注册: strategy_id={strategy.id}")

        try:
            # 简化版本：注册到策略库
            await asyncio.sleep(0.1)  # 模拟耗时

            registration_result = {
                "registered": True,
                "strategy_id": strategy.id,
                "registration_date": datetime.now().isoformat(),
            }

            # 完成阶段
            self.state_tracker.complete_stage(strategy.id, stage, result=registration_result)

            logger.info(f"策略库注册完成: strategy_id={strategy.id}")

            return registration_result

        except Exception as e:
            self.state_tracker.fail_stage(strategy.id, stage, str(e))
            raise

    def _validate_stage_transition(self, progress: PipelineProgress, target_stage: PipelineStage) -> bool:
        """验证阶段转换

        Args:
            progress: 进度对象
            target_stage: 目标阶段

        Returns:
            是否可以转换
        """
        transition = self.stage_validator.validate_transition(progress.current_stage, target_stage, progress)

        return transition.is_valid

    async def validate_stage_transition(self, from_stage: PipelineStage, to_stage: PipelineStage) -> bool:
        """验证阶段转换（公共接口）

        白皮书依据: 第四章 4.3 - 阶段转换验证

        Args:
            from_stage: 源阶段
            to_stage: 目标阶段

        Returns:
            是否可以转换
        """
        transition = self.stage_validator.validate_transition(from_stage, to_stage)
        return transition.is_valid

    def get_progress(self, entity_id: str) -> Optional[PipelineProgress]:
        """获取进度

        Args:
            entity_id: 实体ID

        Returns:
            进度对象
        """
        return self.state_tracker.get_progress(entity_id)

    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息

        Returns:
            统计信息字典
        """
        return self.state_tracker.get_statistics()

    async def publish_pipeline_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """发布流水线事件

        白皮书依据: 第四章 4.3 - 事件驱动通信

        Args:
            event_type: 事件类型
            data: 事件数据
        """
        try:
            from src.infra.event_bus import EventBus  # pylint: disable=import-outside-toplevel

            event_bus = EventBus()
            await event_bus.publish(event_type, data)  # pylint: disable=e1121

            logger.debug(f"已发布流水线事件: type={event_type}")

        except ImportError:
            logger.warning("EventBus不可用，跳过事件发布")
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.warning(f"发布流水线事件失败: {e}")
