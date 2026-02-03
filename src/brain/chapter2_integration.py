"""Chapter 2 AI三脑组件集成模块

白皮书依据: 第二章 AI三脑架构
铁律9依据: 文档同步律

本模块负责集成第二章的4个核心组件:
1. RiskControlMetaLearner - 风险控制元学习器
2. AlgoHunter - 主力雷达
3. AlgoEvolutionSentinel - 算法进化哨兵
4. EngramMemory - Engram记忆系统

集成特点:
- 事件驱动架构，避免循环依赖
- 统一生命周期管理
- 依赖注入配置
- 优雅启动和关闭
"""

import asyncio
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from loguru import logger

from src.brain.algo_evolution.algo_evolution_sentinel import AlgoEvolutionSentinel
from src.brain.algo_hunter.algo_hunter import AlgoHunter
from src.brain.memory.engram_memory import EngramMemory
from src.brain.meta_learning.risk_control_meta_learner import RiskControlMetaLearner
from src.core.exceptions import ComponentInitializationError
from src.infra.event_bus import EventBus


@dataclass
class IntegrationConfig:
    """集成配置

    白皮书依据: 第二章 2.1 系统架构

    Attributes:
        enable_meta_learner: 是否启用元学习器
        enable_algo_hunter: 是否启用主力雷达
        enable_algo_sentinel: 是否启用算法哨兵
        enable_engram_memory: 是否启用记忆系统
        meta_learner_config: 元学习器配置
        algo_hunter_config: 主力雷达配置
        algo_sentinel_config: 算法哨兵配置
        engram_memory_config: 记忆系统配置
    """

    enable_meta_learner: bool = True
    enable_algo_hunter: bool = True
    enable_algo_sentinel: bool = True
    enable_engram_memory: bool = True

    meta_learner_config: Dict[str, Any] = None
    algo_hunter_config: Dict[str, Any] = None
    algo_sentinel_config: Dict[str, Any] = None
    engram_memory_config: Dict[str, Any] = None

    def __post_init__(self):
        """初始化默认配置"""
        if self.meta_learner_config is None:
            self.meta_learner_config = {
                "model_type": "random_forest",
                "learning_rate": 0.01,
                "min_samples_for_training": 100,
            }

        if self.algo_hunter_config is None:
            self.algo_hunter_config = {"model_type": "1d_cnn", "model_path": None, "device": "cuda"}

        if self.algo_sentinel_config is None:
            self.algo_sentinel_config = {
                "scan_interval_hours": 1,
                "enable_arxiv": True,
                "enable_github": True,
                "enable_conferences": False,
            }

        if self.engram_memory_config is None:
            self.engram_memory_config = {
                "ngram_size": 4,
                "embedding_dim": 512,
                "memory_size": 10_000,  # 使用较小的内存大小用于测试
                "storage_backend": "ram",
            }


class Chapter2Integration:
    """第二章AI三脑组件集成器

    白皮书依据: 第二章 AI三脑架构
    铁律9依据: 文档同步律

    核心职责:
    1. 组件生命周期管理（初始化、启动、停止、清理）
    2. 事件总线配置和管理
    3. 组件间通信协调
    4. 健康检查和监控
    5. 优雅启动和关闭

    Attributes:
        config: 集成配置
        event_bus: 事件总线
        meta_learner: 风险控制元学习器
        algo_hunter: 主力雷达
        algo_sentinel: 算法进化哨兵
        engram_memory: Engram记忆系统
        is_running: 运行状态
        start_time: 启动时间
    """

    def __init__(self, config: Optional[IntegrationConfig] = None):
        """初始化集成器

        Args:
            config: 集成配置，None则使用默认配置

        Raises:
            ValueError: 当配置无效时
        """
        self.config = config or IntegrationConfig()

        # 验证配置
        self._validate_config()

        # 初始化事件总线
        self.event_bus = EventBus()

        # 组件实例（延迟初始化）
        self.meta_learner: Optional[RiskControlMetaLearner] = None
        self.algo_hunter: Optional[AlgoHunter] = None
        self.algo_sentinel: Optional[AlgoEvolutionSentinel] = None
        self.engram_memory: Optional[EngramMemory] = None

        # 运行状态
        self.is_running = False
        self.start_time: Optional[datetime] = None

        # 后台任务
        self._background_tasks: List[asyncio.Task] = []

        logger.info("Chapter2Integration initialized")

    def _validate_config(self) -> None:
        """验证配置

        Raises:
            ValueError: 当配置无效时
        """
        if not isinstance(self.config, IntegrationConfig):
            raise ValueError(f"config must be IntegrationConfig, got {type(self.config)}")

        # 至少启用一个组件
        if not any(
            [
                self.config.enable_meta_learner,
                self.config.enable_algo_hunter,
                self.config.enable_algo_sentinel,
                self.config.enable_engram_memory,
            ]
        ):
            raise ValueError("At least one component must be enabled")

        logger.debug("Configuration validated successfully")

    async def initialize(self) -> None:
        """初始化所有组件

        按照依赖顺序初始化:
        1. EngramMemory (无依赖)
        2. RiskControlMetaLearner (可选依赖EngramMemory)
        3. AlgoHunter (可选依赖EngramMemory)
        4. AlgoEvolutionSentinel (可选依赖EngramMemory)

        Raises:
            ComponentInitializationError: 当组件初始化失败时
        """
        logger.info("Starting component initialization...")

        try:
            # 1. 初始化EngramMemory
            if self.config.enable_engram_memory:
                await self._initialize_engram_memory()

            # 2. 初始化RiskControlMetaLearner
            if self.config.enable_meta_learner:
                await self._initialize_meta_learner()

            # 3. 初始化AlgoHunter
            if self.config.enable_algo_hunter:
                await self._initialize_algo_hunter()

            # 4. 初始化AlgoEvolutionSentinel
            if self.config.enable_algo_sentinel:
                await self._initialize_algo_sentinel()

            logger.info("All components initialized successfully")

        except Exception as e:
            logger.error(f"Component initialization failed: {e}")
            # 清理已初始化的组件
            await self.cleanup()
            raise ComponentInitializationError("Chapter2Integration", f"组件初始化失败: {e}") from e

    async def _initialize_engram_memory(self) -> None:
        """初始化Engram记忆系统

        Raises:
            ComponentInitializationError: 当初始化失败时
        """
        try:
            logger.info("Initializing EngramMemory...")

            config = self.config.engram_memory_config
            self.engram_memory = EngramMemory(
                ngram_size=config["ngram_size"],
                embedding_dim=config["embedding_dim"],
                memory_size=config["memory_size"],
                storage_backend=config["storage_backend"],
            )

            logger.info(
                f"EngramMemory initialized: "
                f"memory_size={config['memory_size']:,}, "
                f"backend={config['storage_backend']}"
            )

        except Exception as e:
            logger.error(f"Failed to initialize EngramMemory: {e}")
            raise ComponentInitializationError("EngramMemory", f"初始化失败: {e}") from e

    async def _initialize_meta_learner(self) -> None:
        """初始化风险控制元学习器

        Raises:
            ComponentInitializationError: 当初始化失败时
        """
        try:
            logger.info("Initializing RiskControlMetaLearner...")

            config = self.config.meta_learner_config
            self.meta_learner = RiskControlMetaLearner(
                model_type=config["model_type"],
                learning_rate=config["learning_rate"],
                min_samples_for_training=config["min_samples_for_training"],
                event_bus=self.event_bus,
            )

            logger.info(f"RiskControlMetaLearner initialized: " f"model_type={config['model_type']}")

        except Exception as e:
            logger.error(f"Failed to initialize RiskControlMetaLearner: {e}")
            raise ComponentInitializationError("RiskControlMetaLearner", f"初始化失败: {e}") from e

    async def _initialize_algo_hunter(self) -> None:
        """初始化主力雷达

        Raises:
            ComponentInitializationError: 当初始化失败时
        """
        try:
            logger.info("Initializing AlgoHunter...")

            config = self.config.algo_hunter_config
            self.algo_hunter = AlgoHunter(
                model_type=config["model_type"],
                model_path=config["model_path"],
                device=config["device"],
                event_bus=self.event_bus,
            )

            logger.info(f"AlgoHunter initialized: " f"model_type={config['model_type']}, " f"device={config['device']}")

        except Exception as e:
            logger.error(f"Failed to initialize AlgoHunter: {e}")
            raise ComponentInitializationError("AlgoHunter", f"initialization failed: {e}") from e

    async def _initialize_algo_sentinel(self) -> None:
        """初始化算法进化哨兵

        Raises:
            ComponentInitializationError: 当初始化失败时
        """
        try:
            logger.info("Initializing AlgoEvolutionSentinel...")

            config = self.config.algo_sentinel_config
            self.algo_sentinel = AlgoEvolutionSentinel(
                event_bus=self.event_bus, scan_interval=config["scan_interval_hours"] * 3600  # 转换为秒
            )

            logger.info(f"AlgoEvolutionSentinel initialized: " f"scan_interval={config['scan_interval_hours']}h")

        except Exception as e:
            logger.error(f"Failed to initialize AlgoEvolutionSentinel: {e}")
            raise ComponentInitializationError("AlgoEvolutionSentinel", f"初始化失败: {e}") from e

    async def start(self) -> None:
        """启动所有组件

        启动顺序:
        1. 启动事件总线
        2. 启动各个组件
        3. 启动后台监控任务

        Raises:
            RuntimeError: 当组件未初始化或已在运行时
        """
        if self.is_running:
            raise RuntimeError("Integration is already running")

        if not any([self.meta_learner, self.algo_hunter, self.algo_sentinel, self.engram_memory]):
            raise RuntimeError("No components initialized. Call initialize() first")

        logger.info("Starting Chapter 2 integration...")

        try:
            # 启动算法哨兵的持续监控（如果启用）
            if self.algo_sentinel:
                task = asyncio.create_task(self.algo_sentinel.run_continuous_monitoring())
                self._background_tasks.append(task)
                logger.info("AlgoEvolutionSentinel monitoring started")

            # 标记为运行中
            self.is_running = True
            self.start_time = datetime.now()

            logger.info("Chapter 2 integration started successfully")

        except Exception as e:
            logger.error(f"Failed to start integration: {e}")
            await self.stop()
            raise RuntimeError(f"Failed to start integration: {e}") from e

    async def stop(self) -> None:
        """停止所有组件

        停止顺序:
        1. 停止后台任务
        2. 停止各个组件
        3. 停止事件总线
        """
        if not self.is_running:
            logger.warning("Integration is not running")
            return

        logger.info("Stopping Chapter 2 integration...")

        try:
            # 取消所有后台任务
            for task in self._background_tasks:
                if not task.done():
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass

            self._background_tasks.clear()

            # 标记为已停止
            self.is_running = False

            # 计算运行时长
            if self.start_time:
                uptime = datetime.now() - self.start_time
                logger.info(f"Integration stopped. Uptime: {uptime}")

            logger.info("Chapter 2 integration stopped successfully")

        except Exception as e:
            logger.error(f"Error during stop: {e}")
            raise RuntimeError(f"Failed to stop integration: {e}") from e

    async def cleanup(self) -> None:
        """清理所有资源

        清理顺序:
        1. 停止组件（如果在运行）
        2. 清理各个组件资源
        3. 清理事件总线
        """
        logger.info("Cleaning up Chapter 2 integration...")

        try:
            # 先停止（如果在运行）
            if self.is_running:
                await self.stop()

            # 清理各个组件
            if self.algo_hunter:
                # AlgoHunter可能需要释放GPU资源
                logger.debug("Cleaning up AlgoHunter...")
                self.algo_hunter = None

            if self.meta_learner:
                logger.debug("Cleaning up RiskControlMetaLearner...")
                self.meta_learner = None

            if self.algo_sentinel:
                logger.debug("Cleaning up AlgoEvolutionSentinel...")
                self.algo_sentinel = None

            if self.engram_memory:
                logger.debug("Cleaning up EngramMemory...")
                self.engram_memory = None

            logger.info("Chapter 2 integration cleaned up successfully")

        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
            raise RuntimeError(f"Failed to cleanup integration: {e}") from e

    def get_status(self) -> Dict[str, Any]:
        """获取集成状态

        Returns:
            包含以下信息的状态字典:
            - is_running: 是否运行中
            - start_time: 启动时间
            - uptime_seconds: 运行时长（秒）
            - components: 各组件状态
            - event_bus_stats: 事件总线统计
        """
        status = {
            "is_running": self.is_running,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "uptime_seconds": (datetime.now() - self.start_time).total_seconds() if self.start_time else 0,
            "components": {
                "meta_learner": {
                    "enabled": self.config.enable_meta_learner,
                    "initialized": self.meta_learner is not None,
                    "stats": self.meta_learner.get_learning_report() if self.meta_learner else None,
                },
                "algo_hunter": {
                    "enabled": self.config.enable_algo_hunter,
                    "initialized": self.algo_hunter is not None,
                    "stats": self.algo_hunter.get_inference_stats() if self.algo_hunter else None,
                },
                "algo_sentinel": {
                    "enabled": self.config.enable_algo_sentinel,
                    "initialized": self.algo_sentinel is not None,
                    "stats": None,  # AlgoEvolutionSentinel没有统计方法
                },
                "engram_memory": {
                    "enabled": self.config.enable_engram_memory,
                    "initialized": self.engram_memory is not None,
                    "stats": self.engram_memory.get_statistics() if self.engram_memory else None,
                },
            },
            "background_tasks": len(self._background_tasks),
            "active_tasks": sum(1 for task in self._background_tasks if not task.done()),
        }

        return status

    async def health_check(self) -> Dict[str, Any]:
        """健康检查

        Returns:
            健康检查结果:
            - healthy: 总体健康状态
            - components: 各组件健康状态
            - issues: 发现的问题列表
        """
        issues = []
        component_health = {}

        # 检查各组件
        if self.config.enable_meta_learner:
            if self.meta_learner is None:
                issues.append("RiskControlMetaLearner not initialized")
                component_health["meta_learner"] = False
            else:
                component_health["meta_learner"] = True

        if self.config.enable_algo_hunter:
            if self.algo_hunter is None:
                issues.append("AlgoHunter not initialized")
                component_health["algo_hunter"] = False
            else:
                component_health["algo_hunter"] = True

        if self.config.enable_algo_sentinel:
            if self.algo_sentinel is None:
                issues.append("AlgoEvolutionSentinel not initialized")
                component_health["algo_sentinel"] = False
            else:
                component_health["algo_sentinel"] = True

        if self.config.enable_engram_memory:
            if self.engram_memory is None:
                issues.append("EngramMemory not initialized")
                component_health["engram_memory"] = False
            else:
                component_health["engram_memory"] = True

        # 检查后台任务
        failed_tasks = sum(1 for task in self._background_tasks if task.done() and task.exception())
        if failed_tasks > 0:
            issues.append(f"{failed_tasks} background tasks failed")

        # 总体健康状态
        healthy = len(issues) == 0 and self.is_running

        return {
            "healthy": healthy,
            "components": component_health,
            "issues": issues,
            "timestamp": datetime.now().isoformat(),
        }

    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self.initialize()
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.cleanup()
        return False
