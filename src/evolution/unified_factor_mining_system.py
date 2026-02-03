"""统一因子挖掘系统

白皮书依据: 第四章 4.1.17 统一因子挖掘系统
需求: 15.1, 15.2, 15.8, 15.10
设计文档: design.md - Unified Factor Mining System
"""

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

import pandas as pd
import psutil
from loguru import logger

from .genetic_miner import EvolutionConfig, GeneticMiner


class MinerType(Enum):
    """挖掘器类型

    白皮书依据: 第四章 4.1 - 16个专业因子挖掘器
    """

    GENETIC = "genetic"
    ALTERNATIVE_DATA = "alternative_data"
    AI_ENHANCED = "ai_enhanced"
    NETWORK = "network"
    HIGH_FREQUENCY = "high_frequency"
    SENTIMENT = "sentiment"
    ML_FEATURE = "ml_feature"
    TIME_SERIES_DL = "time_series_dl"
    ESG = "esg"
    PRICE_VOLUME = "price_volume"
    MACRO = "macro"
    EVENT_DRIVEN = "event_driven"
    ALTERNATIVE_EXTENDED = "alternative_extended"
    STYLE_ROTATION = "style_rotation"
    FACTOR_COMBINATION = "factor_combination"
    UNIFIED = "unified"


class MinerStatus(Enum):
    """挖掘器状态"""

    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    DISABLED = "disabled"


@dataclass
class MinerMetadata:
    """挖掘器元数据

    Attributes:
        miner_type: 挖掘器类型
        miner_name: 挖掘器名称
        status: 当前状态
        last_run_time: 上次运行时间
        total_factors_discovered: 总发现因子数
        success_rate: 成功率
        average_fitness: 平均适应度
        is_healthy: 是否健康
        error_count: 错误计数
        last_error: 最后一次错误
    """

    miner_type: MinerType
    miner_name: str
    status: MinerStatus = MinerStatus.IDLE
    last_run_time: Optional[datetime] = None
    total_factors_discovered: int = 0
    success_rate: float = 0.0
    average_fitness: float = 0.0
    is_healthy: bool = True
    error_count: int = 0
    last_error: Optional[str] = None


@dataclass
class FactorMetadata:
    """因子元数据

    白皮书依据: 第四章 4.1 因子元数据
    设计文档: design.md - Factor Metadata

    Attributes:
        factor_id: 唯一因子标识符
        factor_name: 人类可读名称
        factor_type: 因子类别
        data_source: 主要数据源
        discovery_date: 发现时间戳
        discoverer: 发现该因子的挖掘器
        expression: 因子表达式
        fitness: 适应度评分
        ic: 信息系数
        ir: 信息比率
        sharpe: 夏普比率
        lifecycle_status: 当前生命周期状态
    """

    factor_id: str
    factor_name: str
    factor_type: MinerType
    data_source: str
    discovery_date: datetime
    discoverer: str
    expression: str
    fitness: float
    ic: float = 0.0
    ir: float = 0.0
    sharpe: float = 0.0
    lifecycle_status: str = "discovered"


@dataclass
class MiningResult:
    """挖掘结果

    Attributes:
        miner_type: 挖掘器类型
        factors: 发现的因子列表
        execution_time: 执行时间（秒）
        success: 是否成功
        error: 错误信息（如果失败）
    """

    miner_type: MinerType
    factors: List[FactorMetadata]
    execution_time: float
    success: bool
    error: Optional[str] = None


class BaseMiner:
    """基础挖掘器接口

    所有专业挖掘器必须实现此接口
    """

    def __init__(self, miner_type: MinerType, miner_name: str):
        """初始化基础挖掘器

        Args:
            miner_type: 挖掘器类型
            miner_name: 挖掘器名称
        """
        self.miner_type = miner_type
        self.miner_name = miner_name
        self.metadata = MinerMetadata(miner_type=miner_type, miner_name=miner_name)

    def mine_factors(self, data: Any, returns: Any, **kwargs) -> List[FactorMetadata]:
        """挖掘因子（子类必须实现）

        Args:
            data: 输入数据
            returns: 收益率数据
            **kwargs: 额外参数

        Returns:
            发现的因子列表

        Raises:
            NotImplementedError: 子类未实现
        """
        raise NotImplementedError("子类必须实现 mine_factors 方法")

    def is_healthy(self) -> bool:
        """检查挖掘器健康状态

        Returns:
            是否健康
        """
        return self.metadata.is_healthy

    def get_metadata(self) -> MinerMetadata:
        """获取挖掘器元数据

        Returns:
            挖掘器元数据
        """
        return self.metadata


class GeneticMinerAdapter(BaseMiner):
    """遗传算法挖掘器适配器

    将GeneticMiner适配到统一接口
    """

    def __init__(self, config: Optional[EvolutionConfig] = None):
        """初始化遗传算法挖掘器适配器

        Args:
            config: 进化配置
        """
        super().__init__(MinerType.GENETIC, "GeneticMiner")
        self.config = config or EvolutionConfig()
        self.genetic_miner = GeneticMiner(self.config)

    def mine_factors(self, data: Any, returns: Any, **kwargs) -> List[FactorMetadata]:
        """使用遗传算法挖掘因子

        Args:
            data: 市场数据（DataFrame）
            returns: 收益率数据
            **kwargs: 额外参数

        Returns:
            发现的因子列表
        """
        try:
            # 提取数据列名
            import pandas as pd  # pylint: disable=import-outside-toplevel,w0621,w0404

            if isinstance(data, pd.DataFrame):
                data_columns = data.columns.tolist()
            else:
                # 如果不是DataFrame，使用默认列名
                data_columns = ["close", "volume", "open", "high", "low"]

            # 初始化种群（使用asyncio.run来运行异步方法）
            import asyncio  # pylint: disable=import-outside-toplevel

            asyncio.run(self.genetic_miner.initialize_population(data_columns))

            # 评估适应度
            asyncio.run(self.genetic_miner.evaluate_fitness(data, returns))

            # 进化
            generations = kwargs.get("generations", self.config.max_generations)
            best_individual = asyncio.run(self.genetic_miner.evolve(data, returns, generations))

            # 转换为FactorMetadata
            factor = FactorMetadata(
                factor_id=best_individual.individual_id,
                factor_name=f"genetic_factor_{best_individual.individual_id}",
                factor_type=MinerType.GENETIC,
                data_source="market_data",
                discovery_date=datetime.now(),
                discoverer=self.miner_name,
                expression=best_individual.expression,
                fitness=best_individual.fitness,
                ic=best_individual.ic,
                ir=best_individual.ir,
                sharpe=best_individual.sharpe,
            )

            # 更新元数据
            self.metadata.total_factors_discovered += 1
            self.metadata.average_fitness = (
                self.metadata.average_fitness * (self.metadata.total_factors_discovered - 1) + best_individual.fitness
            ) / self.metadata.total_factors_discovered
            self.metadata.last_run_time = datetime.now()

            return [factor]

        except Exception as e:
            logger.error(f"遗传算法挖掘失败: {e}")
            self.metadata.error_count += 1
            self.metadata.last_error = str(e)
            self.metadata.is_healthy = self.metadata.error_count < 5
            raise


# PlaceholderMiner removed - all miners will be fully implemented
# Task 7-23 will implement each specialized miner completely


class UnifiedFactorMiningSystem:
    """统一因子挖掘系统

    白皮书依据: 第四章 4.1.17 统一因子挖掘系统
    需求: 15.1, 15.2, 15.8, 15.10

    协调所有16个专业因子挖掘器，管理因子库，集成Arena，处理因子生命周期。

    Attributes:
        miners: 16个专业挖掘器字典
        factor_library: 因子注册表
        max_workers: 最大并行工作线程数
        system_load_threshold: 系统负载阈值
        executor: 线程池执行器
    """

    def __init__(self, max_workers: int = 16, system_load_threshold: float = 0.8):
        """初始化统一因子挖掘系统

        白皮书依据: 第四章 4.1.17
        需求: 15.1, 15.2

        Args:
            max_workers: 最大并行工作线程数，默认16
            system_load_threshold: 系统负载阈值，默认0.8 (80%)

        Raises:
            ValueError: 当参数不在有效范围时
        """
        if max_workers <= 0:
            raise ValueError(f"max_workers必须 > 0，当前: {max_workers}")

        if not 0 < system_load_threshold <= 1:
            raise ValueError(f"system_load_threshold必须在 (0, 1]，当前: {system_load_threshold}")

        self.max_workers = max_workers
        self.system_load_threshold = system_load_threshold
        self.executor = ThreadPoolExecutor(max_workers=max_workers)

        # 初始化挖掘器注册表
        self.miners: Dict[MinerType, BaseMiner] = {}
        self._initialize_miners()

        # 初始化因子库（简化版本，后续Task 5.1会完整实现）
        self.factor_library: Dict[str, FactorMetadata] = {}

        logger.info(
            f"统一因子挖掘系统初始化完成 - "
            f"max_workers={max_workers}, "
            f"system_load_threshold={system_load_threshold}, "
            f"registered_miners={len(self.miners)}"
        )

    def _initialize_miners(self) -> None:
        """初始化所有16个专业挖掘器

        白皮书依据: 第四章 4.1 - 16个专业因子挖掘器
        需求: 15.1

        当前状态：
        - GeneticMiner: 已完整实现 ✅
        - AlternativeDataFactorMiner: 已完整实现 ✅
        - AIEnhancedFactorMiner: 已完整实现 ✅
        - NetworkRelationshipFactorMiner: 已完整实现 ✅
        - HighFrequencyMicrostructureFactorMiner: 已完整实现 ✅
        - SentimentBehaviorFactorMiner: 已完整实现 ✅
        - MLFeatureEngineeringFactorMiner: 已完整实现 ✅
        - TimeSeriesDeepLearningFactorMiner: 已完整实现 ✅
        - ESGIntelligenceFactorMiner: 已完整实现 ✅
        - PriceVolumeRelationshipFactorMiner: 已完整实现 ✅
        - MacroCrossAssetFactorMiner: 已完整实现 ✅
        - EventDrivenFactorMiner: 已完整实现 ✅
        - AlternativeDataFactorMinerExtended: 已完整实现 ✅
        - StyleRotationFactorMiner: 已完整实现 ✅
        - FactorCombinationInteractionMiner: 已完整实现 ✅
        - MetaMiner: 已完整实现 ✅

        实现进度：16/16 (100%) 🎉
        - Task 1: GeneticMiner ✅
        - Task 7: AlternativeDataFactorMiner ✅
        - Task 8: AIEnhancedFactorMiner ✅
        - Task 9: NetworkRelationshipFactorMiner ✅
        - Task 10: HighFrequencyMicrostructureFactorMiner ✅
        - Task 12: SentimentBehaviorFactorMiner ✅
        - Task 13: MLFeatureEngineeringFactorMiner ✅
        - Task 14: TimeSeriesDeepLearningFactorMiner ✅
        - Task 15: ESGIntelligenceFactorMiner ✅
        - Task 17: PriceVolumeRelationshipFactorMiner ✅
        - Task 18: MacroCrossAssetFactorMiner ✅
        - Task 19: EventDrivenFactorMiner ✅
        - Task 20: AlternativeDataFactorMinerExtended ✅
        - Task 22: StyleRotationFactorMiner ✅
        - Task 23: FactorCombinationInteractionMiner ✅
        - MetaMiner: 元挖掘器（挖掘器的挖掘器）✅
        """
        # 导入已实现的挖掘器
        from .ai_enhanced_miner import AIEnhancedFactorMiner  # pylint: disable=import-outside-toplevel
        from .alternative_data_miner import AlternativeDataFactorMiner  # pylint: disable=import-outside-toplevel
        from .high_frequency_microstructure_miner import (  # pylint: disable=import-outside-toplevel
            HighFrequencyMicrostructureFactorMiner,
        )
        from .ml_feature_engineering_miner import (  # pylint: disable=import-outside-toplevel
            MLFeatureEngineeringFactorMiner,
        )
        from .network_relationship_miner import (  # pylint: disable=import-outside-toplevel
            NetworkRelationshipFactorMiner,
        )
        from .sentiment_behavior_miner import SentimentBehaviorFactorMiner  # pylint: disable=import-outside-toplevel

        # 1. 遗传算法挖掘器（已完整实现）
        self.miners[MinerType.GENETIC] = GeneticMinerAdapter()

        # 2. 替代数据因子挖掘器（已完整实现）
        self.miners[MinerType.ALTERNATIVE_DATA] = AlternativeDataFactorMiner()

        # 3. AI增强因子挖掘器（已完整实现）
        self.miners[MinerType.AI_ENHANCED] = AIEnhancedFactorMiner()

        # 4. 网络关系因子挖掘器（已完整实现）
        self.miners[MinerType.NETWORK] = NetworkRelationshipFactorMiner()

        # 5. 高频微观结构因子挖掘器（已完整实现）
        self.miners[MinerType.HIGH_FREQUENCY] = HighFrequencyMicrostructureFactorMiner()

        # 6. 情绪与行为因子挖掘器（已完整实现）
        self.miners[MinerType.SENTIMENT] = SentimentBehaviorFactorMiner()

        # 7. 机器学习特征工程因子挖掘器（已完整实现）
        self.miners[MinerType.ML_FEATURE] = MLFeatureEngineeringFactorMiner()

        # 8. 时序深度学习因子挖掘器（已完整实现）
        from .time_series_dl_miner import TimeSeriesDeepLearningFactorMiner  # pylint: disable=import-outside-toplevel

        self.miners[MinerType.TIME_SERIES_DL] = TimeSeriesDeepLearningFactorMiner()

        # 9. ESG智能因子挖掘器（已完整实现）
        from .esg_intelligence_miner import ESGIntelligenceFactorMiner  # pylint: disable=import-outside-toplevel

        self.miners[MinerType.ESG] = ESGIntelligenceFactorMiner()

        # 10. 量价关系因子挖掘器（已完整实现）
        from .price_volume_relationship_miner import (  # pylint: disable=import-outside-toplevel
            PriceVolumeRelationshipFactorMiner,
        )

        self.miners[MinerType.PRICE_VOLUME] = PriceVolumeRelationshipFactorMiner()

        # 11. 宏观跨资产因子挖掘器（已完整实现）
        from .macro_cross_asset_miner import MacroCrossAssetFactorMiner  # pylint: disable=import-outside-toplevel

        self.miners[MinerType.MACRO] = MacroCrossAssetFactorMiner()

        # 12. 事件驱动因子挖掘器（已完整实现）
        from .event_driven_miner import EventDrivenFactorMiner  # pylint: disable=import-outside-toplevel

        self.miners[MinerType.EVENT_DRIVEN] = EventDrivenFactorMiner()

        # 13. 替代数据因子扩展版（已完整实现）
        from .alternative_data_miner_extended import (  # pylint: disable=import-outside-toplevel
            AlternativeDataFactorMinerExtended,
        )

        self.miners[MinerType.ALTERNATIVE_EXTENDED] = AlternativeDataFactorMinerExtended()

        # 14. 风格轮动因子挖掘器（已完整实现）
        from .style_rotation_miner import StyleRotationFactorMiner  # pylint: disable=import-outside-toplevel

        self.miners[MinerType.STYLE_ROTATION] = StyleRotationFactorMiner()

        # 15. 因子组合与交互挖掘器（已完整实现）
        from .factor_combination_interaction_miner import (  # pylint: disable=import-outside-toplevel
            FactorCombinationInteractionMiner,
        )

        self.miners[MinerType.FACTOR_COMBINATION] = FactorCombinationInteractionMiner()

        # 16. 元挖掘器（已完整实现）
        from .meta_miner import MetaMiner  # pylint: disable=import-outside-toplevel

        self.meta_miner = MetaMiner()
        self.miners[MinerType.UNIFIED] = self.meta_miner

        logger.info(f"已注册 {len(self.miners)} 个挖掘器（目标: 16个专业挖掘器）")

    def register_miner(self, miner_type: MinerType, miner: BaseMiner) -> None:
        """注册新的挖掘器

        Args:
            miner_type: 挖掘器类型
            miner: 挖掘器实例

        Raises:
            ValueError: 当挖掘器类型已存在时
        """
        if miner_type in self.miners:
            raise ValueError(f"挖掘器类型已存在: {miner_type}")

        self.miners[miner_type] = miner
        logger.info(f"注册挖掘器: {miner_type.value}")

    def get_miner(self, miner_type: MinerType) -> Optional[BaseMiner]:
        """获取指定类型的挖掘器

        Args:
            miner_type: 挖掘器类型

        Returns:
            挖掘器实例，如果不存在则返回None
        """
        return self.miners.get(miner_type)

    def get_all_miners(self) -> Dict[MinerType, BaseMiner]:
        """获取所有已注册的挖掘器

        Returns:
            挖掘器字典
        """
        return self.miners.copy()

    def _check_system_load(self) -> bool:
        """检查系统负载

        需求: 15.9 - 当系统负载超过80%时，应该节流挖掘操作

        Returns:
            True如果系统负载在阈值内，False如果超过阈值
        """
        cpu_percent = psutil.cpu_percent(interval=0.1) / 100.0
        memory_percent = psutil.virtual_memory().percent / 100.0

        current_load = max(cpu_percent, memory_percent)

        if current_load > self.system_load_threshold:
            logger.warning(
                f"系统负载过高: CPU={cpu_percent:.1%}, "
                f"Memory={memory_percent:.1%}, "
                f"阈值={self.system_load_threshold:.1%}"
            )
            return False

        return True

    def _mine_single(self, miner_type: MinerType, miner: BaseMiner, data: Any, returns: Any, **kwargs) -> MiningResult:
        """执行单个挖掘器（内部方法）

        需求: 15.10 - 当挖掘器失败时，应该隔离故障并继续其他挖掘器

        Args:
            miner_type: 挖掘器类型
            miner: 挖掘器实例
            data: 输入数据
            returns: 收益率数据
            **kwargs: 额外参数

        Returns:
            挖掘结果
        """
        start_time = time.time()

        try:
            logger.info(f"开始挖掘: {miner_type.value}")

            # 执行挖掘
            factors = miner.mine_factors(data, returns, **kwargs)

            execution_time = time.time() - start_time

            logger.info(f"挖掘完成: {miner_type.value}, " f"发现因子数={len(factors)}, " f"耗时={execution_time:.2f}s")

            return MiningResult(miner_type=miner_type, factors=factors, execution_time=execution_time, success=True)

        except Exception as e:  # pylint: disable=broad-exception-caught
            execution_time = time.time() - start_time
            error_msg = f"挖掘失败: {miner_type.value}, 错误: {e}"
            logger.error(error_msg)

            return MiningResult(
                miner_type=miner_type, factors=[], execution_time=execution_time, success=False, error=str(e)
            )

    def mine_parallel(
        self, data: Any, returns: Any, miner_types: Optional[List[MinerType]] = None, **kwargs
    ) -> List[MiningResult]:
        """并行执行多个挖掘器

        白皮书依据: 第四章 4.1.17 并行调度
        需求: 15.2, 15.8, 15.9, 15.10

        Args:
            data: 输入数据
            returns: 收益率数据
            miner_types: 要执行的挖掘器类型列表，None表示执行所有
            **kwargs: 传递给挖掘器的额外参数

        Returns:
            挖掘结果列表

        Raises:
            RuntimeError: 当系统负载过高时
        """
        # 检查系统负载
        if not self._check_system_load():
            raise RuntimeError(f"系统负载超过阈值 {self.system_load_threshold:.1%}，" "拒绝启动新的挖掘任务")

        # 确定要执行的挖掘器
        if miner_types is None:
            miners_to_run = self.miners.items()
        else:
            miners_to_run = [(mt, self.miners[mt]) for mt in miner_types if mt in self.miners]

        if not miners_to_run:
            logger.warning("没有可执行的挖掘器")
            return []

        logger.info(f"开始并行挖掘，挖掘器数量: {len(miners_to_run)}")

        # 提交所有挖掘任务
        futures = {
            self.executor.submit(self._mine_single, miner_type, miner, data, returns, **kwargs): miner_type
            for miner_type, miner in miners_to_run
        }

        # 收集结果（故障隔离：即使某些挖掘器失败，也继续收集其他结果）
        results = []
        for future in as_completed(futures):
            miner_type = futures[future]
            try:
                result = future.result()
                results.append(result)

                # 记录到元挖掘器（如果存在）
                if hasattr(self, "meta_miner") and self.meta_miner:
                    self.meta_miner.record_mining_result(result, result.execution_time)

            except Exception as e:  # pylint: disable=broad-exception-caught
                # 故障隔离：记录错误但不中断其他挖掘器
                logger.error(f"挖掘器 {miner_type.value} 执行异常: {e}")
                results.append(
                    MiningResult(miner_type=miner_type, factors=[], execution_time=0.0, success=False, error=str(e))
                )

        # 统计结果
        successful = sum(1 for r in results if r.success)
        failed = len(results) - successful
        total_factors = sum(len(r.factors) for r in results)

        logger.info(f"并行挖掘完成 - " f"成功={successful}, 失败={failed}, " f"总因子数={total_factors}")

        return results

    def register_factor(self, factor: FactorMetadata) -> str:
        """注册新因子到因子库

        白皮书依据: 第四章 4.1.17 因子库接口
        需求: 15.3

        Args:
            factor: 因子元数据

        Returns:
            因子ID

        Raises:
            ValueError: 当因子ID已存在时
        """
        if factor.factor_id in self.factor_library:
            raise ValueError(f"因子ID已存在: {factor.factor_id}")

        self.factor_library[factor.factor_id] = factor
        logger.info(f"注册因子: {factor.factor_id}, 类型: {factor.factor_type.value}")

        return factor.factor_id

    def get_factor(self, factor_id: str) -> Optional[FactorMetadata]:
        """获取因子元数据

        Args:
            factor_id: 因子ID

        Returns:
            因子元数据，如果不存在则返回None
        """
        return self.factor_library.get(factor_id)

    def get_all_factors(self) -> List[FactorMetadata]:
        """获取所有因子

        Returns:
            因子列表
        """
        return list(self.factor_library.values())

    def get_factors_by_type(self, factor_type: MinerType) -> List[FactorMetadata]:
        """按类型获取因子

        Args:
            factor_type: 因子类型

        Returns:
            因子列表
        """
        return [factor for factor in self.factor_library.values() if factor.factor_type == factor_type]

    def monitor_system_health(self) -> Dict[str, Any]:
        """监控系统健康指标

        白皮书依据: 第四章 4.1.17 系统监控

        Returns:
            系统健康指标字典
        """
        healthy_miners = sum(1 for miner in self.miners.values() if miner.is_healthy())

        return {
            "active_miners": len(self.miners),
            "healthy_miners": healthy_miners,
            "total_factors": len(self.factor_library),
            "cpu_usage": psutil.cpu_percent(interval=0.1) / 100.0,
            "memory_usage": psutil.virtual_memory().percent / 100.0,
            "disk_usage": psutil.disk_usage("/").percent / 100.0,
            "system_load_ok": self._check_system_load(),
        }

    def get_miner_statistics(self) -> Dict[MinerType, Dict[str, Any]]:
        """获取所有挖掘器的统计信息

        Returns:
            挖掘器统计信息字典
        """
        stats = {}
        for miner_type, miner in self.miners.items():
            metadata = miner.get_metadata()

            # 处理两种情况：MinerMetadata对象或字典
            if isinstance(metadata, dict):
                # 字典格式（简化版挖掘器）
                stats[miner_type] = {
                    "status": metadata.get("status", "idle"),
                    "total_factors_discovered": metadata.get("total_factors_discovered", 0),
                    "success_rate": metadata.get("success_rate", 0.0),
                    "average_fitness": metadata.get("average_fitness", 0.0),
                    "is_healthy": metadata.get("is_healthy", True),
                    "error_count": metadata.get("error_count", 0),
                    "last_run_time": metadata.get("last_run_time"),
                }
            else:
                # MinerMetadata对象格式（BaseMiner子类）
                stats[miner_type] = {
                    "status": metadata.status.value,
                    "total_factors_discovered": metadata.total_factors_discovered,
                    "success_rate": metadata.success_rate,
                    "average_fitness": metadata.average_fitness,
                    "is_healthy": metadata.is_healthy,
                    "error_count": metadata.error_count,
                    "last_run_time": metadata.last_run_time.isoformat() if metadata.last_run_time else None,
                }
        return stats

    def get_meta_recommendations(self, data: pd.DataFrame) -> Optional[Any]:
        """获取元挖掘器的推荐

        白皮书依据: 第四章 4.1.16 元挖掘推荐

        Args:
            data: 市场数据，用于检测市场状态

        Returns:
            挖掘器推荐，如果元挖掘器不可用则返回None
        """
        if not hasattr(self, "meta_miner") or not self.meta_miner:
            logger.warning("元挖掘器不可用")
            return None

        try:
            # 检测市场状态
            market_regime = self.meta_miner.detect_market_regime(data)

            # 获取推荐
            recommendation = self.meta_miner.recommend_miners(market_regime)

            logger.info(
                f"元挖掘推荐 - "
                f"市场状态={recommendation.market_regime}, "
                f"推荐挖掘器={[m.value for m in recommendation.recommended_miners]}, "
                f"置信度={recommendation.confidence:.2%}"
            )

            return recommendation

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"获取元挖掘推荐失败: {e}")
            return None

    def get_meta_performance_summary(self) -> Optional[Dict[str, Any]]:
        """获取元挖掘器的性能摘要

        Returns:
            性能摘要字典，如果元挖掘器不可用则返回None
        """
        if not hasattr(self, "meta_miner") or not self.meta_miner:
            return None

        try:
            return self.meta_miner.get_performance_summary()
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"获取元挖掘性能摘要失败: {e}")
            return None

    def shutdown(self) -> None:
        """关闭系统，清理资源"""
        logger.info("关闭统一因子挖掘系统...")
        self.executor.shutdown(wait=True)
        logger.info("系统已关闭")
