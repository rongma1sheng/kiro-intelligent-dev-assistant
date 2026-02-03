# pylint: disable=too-many-lines
"""替代数据因子挖掘器

白皮书依据: 第四章 4.1.3 替代数据因子挖掘
需求: 6.1-6.8 (Alternative Data Factor Integration)
设计文档: design.md - Alternative Data Factor Miner

核心功能:
1. 从卫星图像、社交媒体、网络流量、供应链、地理位置等非传统数据源挖掘因子
2. 与传统因子相同的Arena三轨测试验证
3. 数据源可靠性监控（质量评分、更新频率）
4. 优雅降级机制（当数据质量不达标时）
"""

import asyncio
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List

import numpy as np
import pandas as pd
from loguru import logger

from .unified_factor_mining_system import BaseMiner, FactorMetadata, MinerType


class DataSourceType(Enum):
    """替代数据源类型

    白皮书依据: 第四章 4.1.3
    需求: 6.1-6.5
    """

    SATELLITE = "satellite"
    SOCIAL_MEDIA = "social_media"
    WEB_TRAFFIC = "web_traffic"
    SUPPLY_CHAIN = "supply_chain"
    GEOLOCATION = "geolocation"
    NEWS = "news"
    SEARCH_TRENDS = "search_trends"
    SHIPPING = "shipping"


@dataclass
class DataQualityScore:
    """数据质量评分

    白皮书依据: 第四章 4.1.3
    需求: 6.7

    Attributes:
        completeness: 完整性评分 (0-1)
        freshness: 新鲜度评分 (0-1)
        accuracy: 准确性评分 (0-1)
        consistency: 一致性评分 (0-1)
        overall: 综合质量评分 (0-1)
    """

    completeness: float
    freshness: float
    accuracy: float
    consistency: float
    overall: float

    def is_acceptable(self, threshold: float = 0.7) -> bool:
        """检查质量是否可接受

        Args:
            threshold: 质量阈值，默认0.7

        Returns:
            True如果质量可接受，False否则
        """
        return self.overall >= threshold


@dataclass
class DataSourceReliability:
    """数据源可靠性监控

    白皮书依据: 第四章 4.1.3
    需求: 6.7, 6.8

    Attributes:
        source_type: 数据源类型
        quality_score: 当前质量评分
        update_frequency_hours: 预期更新频率（小时）
        last_update_time: 最后更新时间
        consecutive_failures: 连续失败次数
        is_available: 数据源是否可用
        fallback_triggered: 是否已触发降级
    """

    source_type: DataSourceType
    quality_score: float = 1.0
    update_frequency_hours: float = 24.0
    last_update_time: datetime = field(default_factory=datetime.now)
    consecutive_failures: int = 0
    is_available: bool = True
    fallback_triggered: bool = False

    def check_update_delay(self) -> bool:
        """检查更新是否延迟

        需求: 6.8 - 当更新延迟超过2倍预期频率时触发降级

        Returns:
            True如果更新延迟，False否则
        """
        expected_interval = timedelta(hours=self.update_frequency_hours)
        actual_delay = datetime.now() - self.last_update_time

        # 延迟超过2倍预期频率
        return actual_delay > (expected_interval * 2)

    def should_trigger_fallback(self) -> bool:
        """判断是否应触发降级

        需求: 6.8 - 质量 < 0.5 或更新延迟超过2倍时触发降级

        Returns:
            True如果应触发降级，False否则
        """
        return self.quality_score < 0.5 or self.check_update_delay()


@dataclass
class AlternativeDataFactor:
    """替代数据因子

    白皮书依据: 第四章 4.1.3
    需求: 6.1-6.6

    Attributes:
        factor_id: 因子ID
        factor_name: 因子名称
        data_source: 数据源类型
        expression: 因子表达式
        values: 因子值序列
        quality_score: 数据质量评分
        arena_validated: 是否通过Arena验证
        arena_score: Arena综合评分
        ic: 信息系数
        ir: 信息比率
        sharpe: 夏普比率
        created_at: 创建时间
    """

    factor_id: str
    factor_name: str
    data_source: DataSourceType
    expression: str
    values: pd.Series = field(default_factory=pd.Series)
    quality_score: float = 0.0
    arena_validated: bool = False
    arena_score: float = 0.0
    ic: float = 0.0
    ir: float = 0.0
    sharpe: float = 0.0
    created_at: datetime = field(default_factory=datetime.now)


class AlternativeDataFactorMiner(BaseMiner):
    """替代数据因子挖掘器

    白皮书依据: 第四章 4.1.3
    需求: 6.1-6.8 (Alternative Data Factor Integration)

    从卫星图像、社交媒体、网络流量、供应链、地理位置等
    非传统数据源挖掘因子。

    支持8个核心替代数据算子：
    1. satellite_parking_count: 卫星停车场计数 (需求6.1)
    2. social_sentiment_momentum: 社交情绪动量 (需求6.2)
    3. web_traffic_growth: 网络流量增长 (需求6.3)
    4. supply_chain_disruption: 供应链中断 (需求6.4)
    5. foot_traffic_anomaly: 客流量异常 (需求6.5)
    6. news_sentiment_shock: 新闻情绪冲击 (需求6.2)
    7. search_trend_leading: 搜索趋势领先 (需求6.3)
    8. shipping_volume_change: 航运量变化 (需求6.4)

    核心特性:
    - 与传统因子相同的Arena三轨测试验证 (需求6.6)
    - 数据源可靠性监控（质量评分、更新频率）(需求6.7)
    - 优雅降级机制（当数据质量不达标时）(需求6.8)

    Attributes:
        operators: 8个算子的字典
        data_quality_threshold: 数据质量阈值 (默认0.7)
        fallback_enabled: 是否启用优雅降级 (默认True)
        data_source_reliability: 数据源可靠性监控字典
        arena_validation_enabled: 是否启用Arena验证 (默认True)
    """

    def __init__(
        self, data_quality_threshold: float = 0.7, fallback_enabled: bool = True, arena_validation_enabled: bool = True
    ):
        """初始化替代数据因子挖掘器

        白皮书依据: 第四章 4.1.3
        需求: 6.1-6.8

        Args:
            data_quality_threshold: 数据质量阈值，默认0.7
            fallback_enabled: 是否启用优雅降级，默认True
            arena_validation_enabled: 是否启用Arena验证，默认True

        Raises:
            ValueError: 当参数不在有效范围时
        """
        super().__init__(MinerType.ALTERNATIVE_DATA, "AlternativeDataFactorMiner")

        if not 0 < data_quality_threshold <= 1:
            raise ValueError(f"data_quality_threshold必须在 (0, 1]，当前: {data_quality_threshold}")

        self.data_quality_threshold = data_quality_threshold
        self.fallback_enabled = fallback_enabled
        self.arena_validation_enabled = arena_validation_enabled
        self.operators = self._initialize_operators()

        # 初始化数据源可靠性监控 (需求6.7, 6.8)
        self.data_source_reliability: Dict[DataSourceType, DataSourceReliability] = {}
        self._initialize_reliability_monitoring()

        # 因子缓存
        self.discovered_factors: Dict[str, AlternativeDataFactor] = {}

        logger.info(
            f"AlternativeDataFactorMiner初始化完成 - "
            f"quality_threshold={data_quality_threshold}, "
            f"fallback_enabled={fallback_enabled}, "
            f"arena_validation_enabled={arena_validation_enabled}, "
            f"operators={len(self.operators)}"
        )

    def _initialize_reliability_monitoring(self) -> None:
        """初始化数据源可靠性监控

        白皮书依据: 第四章 4.1.3
        需求: 6.7, 6.8
        """
        # 为每种数据源类型创建可靠性监控
        source_configs = {
            DataSourceType.SATELLITE: 24.0,  # 卫星数据每24小时更新
            DataSourceType.SOCIAL_MEDIA: 1.0,  # 社交媒体每小时更新
            DataSourceType.WEB_TRAFFIC: 6.0,  # 网络流量每6小时更新
            DataSourceType.SUPPLY_CHAIN: 12.0,  # 供应链每12小时更新
            DataSourceType.GEOLOCATION: 4.0,  # 地理位置每4小时更新
            DataSourceType.NEWS: 0.5,  # 新闻每30分钟更新
            DataSourceType.SEARCH_TRENDS: 6.0,  # 搜索趋势每6小时更新
            DataSourceType.SHIPPING: 24.0,  # 航运数据每24小时更新
        }

        for source_type, update_freq in source_configs.items():
            self.data_source_reliability[source_type] = DataSourceReliability(
                source_type=source_type, update_frequency_hours=update_freq
            )

    def _initialize_operators(self) -> Dict[str, Callable]:
        """初始化8个替代数据算子

        白皮书依据: 第四章 4.1.3
        需求: 6.1-6.5

        算子映射:
        - satellite_parking_count: 卫星停车场计数 (需求6.1)
        - social_sentiment_momentum: 社交情绪动量 (需求6.2)
        - web_traffic_growth: 网络流量增长 (需求6.3)
        - supply_chain_disruption: 供应链中断 (需求6.4)
        - foot_traffic_anomaly: 客流量异常 (需求6.5)
        - news_sentiment_shock: 新闻情绪冲击 (需求6.2)
        - search_trend_leading: 搜索趋势领先 (需求6.3)
        - shipping_volume_change: 航运量变化 (需求6.4)

        Returns:
            算子名称到函数的字典
        """
        return {
            "satellite_parking_count": self._satellite_parking_count,
            "social_sentiment_momentum": self._social_sentiment_momentum,
            "web_traffic_growth": self._web_traffic_growth,
            "supply_chain_disruption": self._supply_chain_disruption,
            "foot_traffic_anomaly": self._foot_traffic_anomaly,
            "news_sentiment_shock": self._news_sentiment_shock,
            "search_trend_leading": self._search_trend_leading,
            "shipping_volume_change": self._shipping_volume_change,
        }

    def get_operator_data_source(self, operator_name: str) -> DataSourceType:
        """获取算子对应的数据源类型

        白皮书依据: 第四章 4.1.3
        需求: 6.1-6.5

        Args:
            operator_name: 算子名称

        Returns:
            数据源类型
        """
        source_mapping = {
            "satellite_parking_count": DataSourceType.SATELLITE,
            "social_sentiment_momentum": DataSourceType.SOCIAL_MEDIA,
            "web_traffic_growth": DataSourceType.WEB_TRAFFIC,
            "supply_chain_disruption": DataSourceType.SUPPLY_CHAIN,
            "foot_traffic_anomaly": DataSourceType.GEOLOCATION,
            "news_sentiment_shock": DataSourceType.NEWS,
            "search_trend_leading": DataSourceType.SEARCH_TRENDS,
            "shipping_volume_change": DataSourceType.SHIPPING,
        }

        return source_mapping.get(operator_name, DataSourceType.SATELLITE)

    def mine_factors(  # pylint: disable=too-many-branches
        self, data: pd.DataFrame, returns: pd.Series, **kwargs
    ) -> List[FactorMetadata]:  # pylint: disable=too-many-branches
        """挖掘替代数据因子

        白皮书依据: 第四章 4.1.3
        需求: 6.1-6.8

        核心流程:
        1. 对每个算子执行因子挖掘 (需求6.1-6.5)
        2. 评估数据质量 (需求6.7)
        3. 检查数据源可靠性 (需求6.7, 6.8)
        4. 应用优雅降级（如需要）(需求6.8)
        5. 计算因子指标
        6. 提交Arena验证（与传统因子相同）(需求6.6)

        Args:
            data: 市场数据（DataFrame），包含价格、成交量等
            returns: 收益率数据
            **kwargs: 额外参数
                - alt_data: 替代数据字典 {data_source: DataFrame}
                - symbols: 股票代码列表
                - operators: 要使用的算子列表（默认使用所有）
                - skip_arena_validation: 是否跳过Arena验证（默认False）

        Returns:
            发现的因子列表

        Raises:
            ValueError: 当输入数据无效时
        """
        if data.empty:
            raise ValueError("输入数据不能为空")

        if returns.empty:
            raise ValueError("收益率数据不能为空")

        # 提取参数
        alt_data = kwargs.get("alt_data", {})
        symbols = kwargs.get("symbols", data.index.tolist() if hasattr(data.index, "tolist") else [])
        operators_to_use = kwargs.get("operators", list(self.operators.keys()))
        kwargs.get("skip_arena_validation", False)

        logger.info(
            f"开始挖掘替代数据因子 - "
            f"data_shape={data.shape}, "
            f"alt_sources={len(alt_data)}, "
            f"operators={len(operators_to_use)}"
        )

        factors = []

        # 对每个算子执行挖掘
        for operator_name in operators_to_use:
            if operator_name not in self.operators:
                logger.warning(f"未知算子: {operator_name}，跳过")
                continue

            # 获取数据源类型
            data_source_type = self.get_operator_data_source(operator_name)

            # 检查数据源可靠性 (需求6.7, 6.8)
            reliability = self.data_source_reliability.get(data_source_type)
            if reliability and reliability.should_trigger_fallback():
                logger.warning(
                    f"数据源 {data_source_type.value} 可靠性不足，"
                    f"quality={reliability.quality_score:.3f}, "
                    f"delay={reliability.check_update_delay()}"
                )

                if self.fallback_enabled:
                    # 应用优雅降级 (需求6.8)
                    factor_values = self._apply_fallback(operator_name, data, symbols)
                    reliability.fallback_triggered = True
                    logger.info(f"算子 {operator_name} 已应用优雅降级")
                else:
                    logger.warning(f"跳过算子 {operator_name}，降级未启用")
                    continue
            else:
                try:
                    # 获取算子函数
                    operator_func = self.operators[operator_name]

                    # 执行算子
                    factor_values = operator_func(data, alt_data, symbols)

                    # 更新数据源可靠性 (需求6.7)
                    if reliability:
                        reliability.last_update_time = datetime.now()
                        reliability.consecutive_failures = 0
                        reliability.is_available = True
                        reliability.fallback_triggered = False

                except Exception as e:  # pylint: disable=broad-exception-caught
                    logger.error(f"算子 {operator_name} 执行失败: {e}")

                    # 更新失败计数
                    if reliability:
                        reliability.consecutive_failures += 1
                        if reliability.consecutive_failures >= 3:
                            reliability.is_available = False

                    # 尝试优雅降级 (需求6.8)
                    if self.fallback_enabled:
                        factor_values = self._apply_fallback(operator_name, data, symbols)
                        if reliability:
                            reliability.fallback_triggered = True
                        logger.info(f"算子 {operator_name} 执行失败，已应用优雅降级")
                    else:
                        self.metadata.error_count += 1
                        self.metadata.last_error = str(e)
                        continue

            # 评估数据质量 (需求6.7)
            quality_score = self._evaluate_data_quality(factor_values, operator_name)

            # 更新数据源质量评分
            if reliability:
                reliability.quality_score = quality_score.overall

            # 检查质量阈值
            if not quality_score.is_acceptable(self.data_quality_threshold):
                logger.warning(
                    f"算子 {operator_name} 数据质量不达标: "
                    f"{quality_score.overall:.3f} < {self.data_quality_threshold}"
                )

                # 尝试优雅降级 (需求6.8)
                if self.fallback_enabled:
                    factor_values = self._apply_fallback(operator_name, data, symbols)
                    if reliability:
                        reliability.fallback_triggered = True
                    logger.info(f"算子 {operator_name} 已应用优雅降级")
                else:
                    continue

            # 计算因子指标
            ic = self._calculate_ic(factor_values, returns)
            ir = self._calculate_ir(factor_values, returns)
            sharpe = self._calculate_sharpe(factor_values, returns)

            # 计算综合适应度
            fitness = self._calculate_fitness(ic, ir, sharpe)

            # 创建替代数据因子
            factor_id = f"alt_data_{operator_name}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            alt_factor = AlternativeDataFactor(
                factor_id=factor_id,
                factor_name=f"AlternativeData_{operator_name}",
                data_source=data_source_type,
                expression=f"{operator_name}(alt_data, symbols)",
                values=factor_values,
                quality_score=quality_score.overall,
                ic=ic,
                ir=ir,
                sharpe=sharpe,
            )

            # 存储因子
            self.discovered_factors[factor_id] = alt_factor

            # 创建因子元数据
            factor = FactorMetadata(
                factor_id=factor_id,
                factor_name=f"AlternativeData_{operator_name}",
                factor_type=MinerType.ALTERNATIVE_DATA,
                data_source=data_source_type.value,
                discovery_date=datetime.now(),
                discoverer=self.miner_name,
                expression=f"{operator_name}(alt_data, symbols)",
                fitness=fitness,
                ic=ic,
                ir=ir,
                sharpe=sharpe,
            )

            factors.append(factor)

            logger.info(
                f"发现因子: {factor.factor_id}, "
                f"IC={ic:.4f}, IR={ir:.4f}, Sharpe={sharpe:.4f}, "
                f"fitness={fitness:.4f}, quality={quality_score.overall:.4f}"
            )

        # 更新元数据
        self.metadata.total_factors_discovered += len(factors)
        if factors:
            avg_fitness = np.mean([f.fitness for f in factors])
            self.metadata.average_fitness = (
                self.metadata.average_fitness * (self.metadata.total_factors_discovered - len(factors))
                + avg_fitness * len(factors)
            ) / self.metadata.total_factors_discovered
        self.metadata.last_run_time = datetime.now()
        self.metadata.is_healthy = self.metadata.error_count < 5

        logger.info(
            f"替代数据因子挖掘完成 - " f"发现因子数={len(factors)}, " f"平均fitness={self.metadata.average_fitness:.4f}"
        )

        return factors

    async def submit_to_arena_validation(
        self, factor: AlternativeDataFactor, arena_system: Any = None
    ) -> Dict[str, Any]:
        """提交因子到Arena进行验证

        白皮书依据: 第四章 4.1.3
        需求: 6.6 - 替代数据因子需要与传统因子相同的Arena三轨测试

        Args:
            factor: 替代数据因子
            arena_system: Arena系统实例（可选）

        Returns:
            Arena验证结果
        """
        logger.info(f"提交替代数据因子到Arena验证: {factor.factor_id}")

        if arena_system is None:
            # 如果没有提供Arena系统，返回模拟结果
            logger.warning("Arena系统未提供，使用模拟验证")
            return self._simulate_arena_validation(factor)

        try:
            # 提交到Arena系统进行三轨测试
            task_id = await arena_system.submit_factor_for_testing(
                factor_expression=factor.expression,
                metadata={
                    "factor_id": factor.factor_id,
                    "factor_name": factor.factor_name,
                    "data_source": factor.data_source.value,
                    "quality_score": factor.quality_score,
                    "is_alternative_data": True,
                },
            )

            # 等待测试完成
            max_wait_time = 300  # 最多等待5分钟
            start_time = time.time()

            while time.time() - start_time < max_wait_time:
                status = await arena_system.get_test_status(task_id)

                if status.get("status") in ["passed", "failed"]:
                    # 更新因子的Arena验证状态
                    factor.arena_validated = status.get("status") == "passed"
                    factor.arena_score = status.get("overall_result", {}).get("score", 0.0)

                    logger.info(
                        f"Arena验证完成: {factor.factor_id}, "
                        f"passed={factor.arena_validated}, "
                        f"score={factor.arena_score:.2f}"
                    )

                    return status

                await asyncio.sleep(1)

            logger.warning(f"Arena验证超时: {factor.factor_id}")
            return {"status": "timeout", "error": "Arena validation timed out"}

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"Arena验证失败: {factor.factor_id}, error={e}")
            return {"status": "error", "error": str(e)}

    def _simulate_arena_validation(self, factor: AlternativeDataFactor) -> Dict[str, Any]:
        """模拟Arena验证（用于测试）

        白皮书依据: 第四章 4.1.3
        需求: 6.6

        Args:
            factor: 替代数据因子

        Returns:
            模拟的Arena验证结果
        """
        # 基于因子指标计算模拟的Arena评分
        ic_score = min(abs(factor.ic) / 0.05, 1.0) * 40
        sharpe_score = min(max(factor.sharpe, 0) / 1.5, 1.0) * 40
        quality_score = factor.quality_score * 20

        arena_score = ic_score + sharpe_score + quality_score
        passed = arena_score >= 70.0

        factor.arena_validated = passed
        factor.arena_score = arena_score

        return {
            "status": "passed" if passed else "failed",
            "overall_result": {
                "score": arena_score,
                "passed": passed,
                "reality_score": ic_score + sharpe_score * 0.5,
                "hell_score": sharpe_score * 0.5 + quality_score * 0.5,
                "cross_market_score": quality_score * 0.5,
            },
        }

    def get_data_source_reliability_report(self) -> Dict[str, Any]:
        """获取数据源可靠性报告

        白皮书依据: 第四章 4.1.3
        需求: 6.7, 6.8

        Returns:
            数据源可靠性报告
        """
        report = {
            "timestamp": datetime.now().isoformat(),
            "sources": {},
            "summary": {
                "total_sources": len(self.data_source_reliability),
                "available_sources": 0,
                "degraded_sources": 0,
                "unavailable_sources": 0,
            },
        }

        for source_type, reliability in self.data_source_reliability.items():
            source_status = "available"
            if not reliability.is_available:
                source_status = "unavailable"
                report["summary"]["unavailable_sources"] += 1
            elif reliability.fallback_triggered:
                source_status = "degraded"
                report["summary"]["degraded_sources"] += 1
            else:
                report["summary"]["available_sources"] += 1

            report["sources"][source_type.value] = {
                "status": source_status,
                "quality_score": reliability.quality_score,
                "update_frequency_hours": reliability.update_frequency_hours,
                "last_update_time": reliability.last_update_time.isoformat(),
                "consecutive_failures": reliability.consecutive_failures,
                "update_delayed": reliability.check_update_delay(),
                "fallback_triggered": reliability.fallback_triggered,
            }

        return report

    def update_data_source_reliability(
        self, source_type: DataSourceType, quality_score: float, update_time: datetime = None
    ) -> None:
        """更新数据源可靠性

        白皮书依据: 第四章 4.1.3
        需求: 6.7

        Args:
            source_type: 数据源类型
            quality_score: 质量评分
            update_time: 更新时间（默认当前时间）
        """
        if source_type not in self.data_source_reliability:
            logger.warning(f"未知数据源类型: {source_type}")
            return

        reliability = self.data_source_reliability[source_type]
        reliability.quality_score = quality_score
        reliability.last_update_time = update_time or datetime.now()

        # 检查是否需要触发降级
        if reliability.should_trigger_fallback():
            logger.warning(
                f"数据源 {source_type.value} 触发降级条件: "
                f"quality={quality_score:.3f}, "
                f"delay={reliability.check_update_delay()}"
            )

        logger.debug(f"更新数据源可靠性: {source_type.value}, " f"quality={quality_score:.3f}")

    # ==================== 8个核心算子实现 ====================

    def _satellite_parking_count(
        self,
        data: pd.DataFrame,  # pylint: disable=unused-argument
        alt_data: Dict[str, pd.DataFrame],
        symbols: List[str],  # pylint: disable=unused-argument
    ) -> pd.Series:
        """卫星停车场计数算子

        白皮书依据: 第四章 4.1.3
        需求: 6.1 - 从卫星数据生成停车场车辆数和工厂活动指数因子

        从卫星图像中提取停车场占用率，作为零售商客流量的代理指标。

        Args:
            data: 市场数据
            alt_data: 替代数据字典
            symbols: 股票代码列表

        Returns:
            因子值序列
        """
        if "satellite" not in alt_data:
            raise ValueError("缺少卫星数据")

        satellite_data = alt_data["satellite"]

        # 计算停车场占用率变化
        if "parking_occupancy" in satellite_data.columns:  # pylint: disable=no-else-return
            # 计算7天移动平均
            occupancy_ma7 = satellite_data["parking_occupancy"].rolling(window=7).mean()

            # 计算30天移动平均
            occupancy_ma30 = satellite_data["parking_occupancy"].rolling(window=30).mean()

            # 计算动量：短期均值 / 长期均值 - 1
            factor_values = (occupancy_ma7 / occupancy_ma30 - 1).fillna(0)

            logger.debug(f"satellite_parking_count: 计算完成，非零值={(factor_values != 0).sum()}")

            return factor_values
        else:
            raise ValueError("卫星数据中缺少 parking_occupancy 列")

    def _social_sentiment_momentum(
        self,
        data: pd.DataFrame,  # pylint: disable=unused-argument
        alt_data: Dict[str, pd.DataFrame],
        symbols: List[str],  # pylint: disable=unused-argument
    ) -> pd.Series:
        """社交情绪动量算子

        白皮书依据: 第四章 4.1.3
        需求: 6.2 - 从社交媒体数据创建情绪动量和新闻冲击因子

        从社交媒体数据中计算情绪动量指标。

        Args:
            data: 市场数据
            alt_data: 替代数据字典
            symbols: 股票代码列表

        Returns:
            因子值序列
        """
        if "social_media" not in alt_data:
            raise ValueError("缺少社交媒体数据")

        social_data = alt_data["social_media"]

        # 计算情绪动量
        if "sentiment_score" in social_data.columns:  # pylint: disable=no-else-return
            # 计算情绪变化率
            sentiment_change = social_data["sentiment_score"].pct_change(periods=5)

            # 计算情绪加速度（二阶导数）
            sentiment_acceleration = sentiment_change.diff()

            # 综合动量：变化率 + 0.5 * 加速度
            factor_values = (sentiment_change + 0.5 * sentiment_acceleration).fillna(0)

            logger.debug(f"social_sentiment_momentum: 计算完成，非零值={(factor_values != 0).sum()}")

            return factor_values
        else:
            raise ValueError("社交媒体数据中缺少 sentiment_score 列")

    def _web_traffic_growth(
        self,
        data: pd.DataFrame,  # pylint: disable=unused-argument
        alt_data: Dict[str, pd.DataFrame],
        symbols: List[str],  # pylint: disable=unused-argument
    ) -> pd.Series:
        """网络流量增长算子

        白皮书依据: 第四章 4.1.3
        需求: 6.3 - 从网络流量数据生成网站访问增长和搜索趋势因子

        从网络流量数据中计算增长率指标。

        Args:
            data: 市场数据
            alt_data: 替代数据字典
            symbols: 股票代码列表

        Returns:
            因子值序列
        """
        if "web_traffic" not in alt_data:
            raise ValueError("缺少网络流量数据")

        traffic_data = alt_data["web_traffic"]

        # 计算流量增长率
        if "page_views" in traffic_data.columns:  # pylint: disable=no-else-return
            # 计算同比增长率（与30天前比较）
            growth_rate = traffic_data["page_views"].pct_change(periods=30)

            # 计算增长加速度
            growth_rate.diff()

            # 标准化
            factor_values = ((growth_rate - growth_rate.mean()) / growth_rate.std()).fillna(0)

            logger.debug(f"web_traffic_growth: 计算完成，非零值={(factor_values != 0).sum()}")

            return factor_values
        else:
            raise ValueError("网络流量数据中缺少 page_views 列")

    def _supply_chain_disruption(
        self,
        data: pd.DataFrame,  # pylint: disable=unused-argument
        alt_data: Dict[str, pd.DataFrame],
        symbols: List[str],  # pylint: disable=unused-argument
    ) -> pd.Series:
        """供应链中断算子

        白皮书依据: 第四章 4.1.3
        需求: 6.4 - 从供应链数据创建航运量和中断指数因子

        从供应链数据中检测中断事件。

        Args:
            data: 市场数据
            alt_data: 替代数据字典
            symbols: 股票代码列表

        Returns:
            因子值序列
        """
        if "supply_chain" not in alt_data:
            raise ValueError("缺少供应链数据")

        supply_data = alt_data["supply_chain"]

        # 检测供应链中断
        if "delivery_delay" in supply_data.columns:  # pylint: disable=no-else-return
            # 计算延迟异常（超过均值2个标准差）
            delay_mean = supply_data["delivery_delay"].rolling(window=30).mean()
            delay_std = supply_data["delivery_delay"].rolling(window=30).std()

            # 标准化延迟
            delay_zscore = (supply_data["delivery_delay"] - delay_mean) / delay_std

            # 中断信号：Z-score > 2
            disruption_signal = (delay_zscore > 2).astype(float)

            # 计算中断强度
            factor_values = (disruption_signal * delay_zscore).fillna(0)

            logger.debug(f"supply_chain_disruption: 计算完成，中断事件={disruption_signal.sum()}")

            return factor_values
        else:
            raise ValueError("供应链数据中缺少 delivery_delay 列")

    def _foot_traffic_anomaly(
        self,
        data: pd.DataFrame,  # pylint: disable=unused-argument
        alt_data: Dict[str, pd.DataFrame],
        symbols: List[str],  # pylint: disable=unused-argument
    ) -> pd.Series:
        """客流量异常算子

        白皮书依据: 第四章 4.1.3
        需求: 6.5 - 从地理位置数据生成客流量和区域活动因子

        从地理位置数据中检测客流量异常。

        Args:
            data: 市场数据
            alt_data: 替代数据字典
            symbols: 股票代码列表

        Returns:
            因子值序列
        """
        if "geolocation" not in alt_data:
            raise ValueError("缺少地理位置数据")

        geo_data = alt_data["geolocation"]

        # 检测客流量异常
        if "foot_traffic" in geo_data.columns:  # pylint: disable=no-else-return
            # 计算历史均值和标准差（使用60天窗口）
            traffic_mean = geo_data["foot_traffic"].rolling(window=60).mean()
            traffic_std = geo_data["foot_traffic"].rolling(window=60).std()

            # 计算Z-score
            traffic_zscore = (geo_data["foot_traffic"] - traffic_mean) / traffic_std

            # 异常信号：|Z-score| > 2
            anomaly_signal = (np.abs(traffic_zscore) > 2).astype(float)

            # 异常强度（保留符号）
            factor_values = (anomaly_signal * traffic_zscore).fillna(0)

            logger.debug(f"foot_traffic_anomaly: 计算完成，异常事件={anomaly_signal.sum()}")

            return factor_values
        else:
            raise ValueError("地理位置数据中缺少 foot_traffic 列")

    def _news_sentiment_shock(
        self,
        data: pd.DataFrame,  # pylint: disable=unused-argument
        alt_data: Dict[str, pd.DataFrame],
        symbols: List[str],  # pylint: disable=unused-argument
    ) -> pd.Series:
        """新闻情绪冲击算子

        白皮书依据: 第四章 4.1.3
        需求: 6.2 - 从社交媒体数据创建情绪动量和新闻冲击因子

        从新闻数据中检测情绪冲击事件。

        Args:
            data: 市场数据
            alt_data: 替代数据字典
            symbols: 股票代码列表

        Returns:
            因子值序列
        """
        if "news" not in alt_data:
            raise ValueError("缺少新闻数据")

        news_data = alt_data["news"]

        # 检测新闻情绪冲击
        if "news_sentiment" in news_data.columns:  # pylint: disable=no-else-return
            # 计算情绪变化
            sentiment_change = news_data["news_sentiment"].diff()

            # 计算历史波动率
            sentiment_volatility = sentiment_change.rolling(window=30).std()

            # 冲击信号：变化超过2倍波动率
            shock_threshold = 2 * sentiment_volatility
            shock_signal = (np.abs(sentiment_change) > shock_threshold).astype(float)

            # 冲击强度（保留符号）
            factor_values = (shock_signal * sentiment_change / sentiment_volatility).fillna(0)

            logger.debug(f"news_sentiment_shock: 计算完成，冲击事件={shock_signal.sum()}")

            return factor_values
        else:
            raise ValueError("新闻数据中缺少 news_sentiment 列")

    def _search_trend_leading(
        self,
        data: pd.DataFrame,  # pylint: disable=unused-argument
        alt_data: Dict[str, pd.DataFrame],
        symbols: List[str],  # pylint: disable=unused-argument
    ) -> pd.Series:
        """搜索趋势领先算子

        白皮书依据: 第四章 4.1.3
        需求: 6.3 - 从网络流量数据生成网站访问增长和搜索趋势因子

        从搜索趋势数据中提取领先指标。

        Args:
            data: 市场数据
            alt_data: 替代数据字典
            symbols: 股票代码列表

        Returns:
            因子值序列
        """
        if "search_trends" not in alt_data:
            raise ValueError("缺少搜索趋势数据")

        search_data = alt_data["search_trends"]

        # 计算搜索趋势领先指标
        if "search_volume" in search_data.columns:  # pylint: disable=no-else-return
            # 计算搜索量变化率
            search_change = search_data["search_volume"].pct_change(periods=7)

            # 计算搜索量动量
            search_momentum = search_change.rolling(window=14).mean()

            # 标准化
            factor_values = ((search_momentum - search_momentum.mean()) / search_momentum.std()).fillna(0)

            logger.debug(f"search_trend_leading: 计算完成，非零值={(factor_values != 0).sum()}")

            return factor_values
        else:
            raise ValueError("搜索趋势数据中缺少 search_volume 列")

    def _shipping_volume_change(
        self,
        data: pd.DataFrame,  # pylint: disable=unused-argument
        alt_data: Dict[str, pd.DataFrame],
        symbols: List[str],  # pylint: disable=unused-argument
    ) -> pd.Series:
        """航运量变化算子

        白皮书依据: 第四章 4.1.3
        需求: 6.4 - 从供应链数据创建航运量和中断指数因子

        从航运数据中计算运输量变化。

        Args:
            data: 市场数据
            alt_data: 替代数据字典
            symbols: 股票代码列表

        Returns:
            因子值序列
        """
        if "shipping" not in alt_data:
            raise ValueError("缺少航运数据")

        shipping_data = alt_data["shipping"]

        # 计算航运量变化
        if "shipping_volume" in shipping_data.columns:  # pylint: disable=no-else-return
            # 计算同比变化率（与30天前比较）
            volume_change = shipping_data["shipping_volume"].pct_change(periods=30)

            # 计算变化趋势（14天移动平均）
            volume_trend = volume_change.rolling(window=14).mean()

            # 标准化
            factor_values = ((volume_trend - volume_trend.mean()) / volume_trend.std()).fillna(0)

            logger.debug(f"shipping_volume_change: 计算完成，非零值={(factor_values != 0).sum()}")

            return factor_values
        else:
            raise ValueError("航运数据中缺少 shipping_volume 列")

    # ==================== 辅助方法实现 ====================

    def _evaluate_data_quality(
        self, factor_values: pd.Series, operator_name: str  # pylint: disable=unused-argument
    ) -> DataQualityScore:  # pylint: disable=unused-argument
        """评估数据质量

        白皮书依据: 第四章 4.1.3
        需求: 6.7 - 跟踪数据质量评分和更新频率

        Args:
            factor_values: 因子值序列
            operator_name: 算子名称

        Returns:
            数据质量评分
        """
        # 计算完整性（非空值比例）
        completeness = 1.0 - (factor_values.isna().sum() / len(factor_values))

        # 计算新鲜度（假设数据是最新的，实际应检查时间戳）
        freshness = 1.0  # 简化版本，实际应检查数据时间戳

        # 计算准确性（基于数据分布的合理性）
        # 检查是否有异常值（超过5个标准差）
        if factor_values.std() > 0:
            z_scores = np.abs((factor_values - factor_values.mean()) / factor_values.std())
            outlier_ratio = (z_scores > 5).sum() / len(factor_values)
            accuracy = 1.0 - outlier_ratio
        else:
            accuracy = 0.5  # 标准差为0表示数据可能有问题

        # 计算一致性（数据变化的平滑性）
        if len(factor_values) > 1:
            changes = factor_values.diff().abs()
            # 计算变化的标准差，标准差越小越一致
            change_std = changes.std()
            consistency = 1.0 / (1.0 + change_std) if not np.isnan(change_std) else 0.5
        else:
            consistency = 0.5

        # 综合质量评分（加权平均）
        overall = completeness * 0.3 + freshness * 0.2 + accuracy * 0.3 + consistency * 0.2

        return DataQualityScore(
            completeness=completeness, freshness=freshness, accuracy=accuracy, consistency=consistency, overall=overall
        )

    def _apply_fallback(
        self, operator_name: str, data: pd.DataFrame, symbols: List[str]  # pylint: disable=unused-argument
    ) -> pd.Series:  # pylint: disable=unused-argument
        """应用优雅降级

        白皮书依据: 第四章 4.1.3
        需求: 6.8 - 当数据质量 < 0.5 或更新延迟超过2倍时实现降级机制

        当替代数据质量不达标时，使用传统数据作为替代。

        Args:
            operator_name: 算子名称
            data: 市场数据
            symbols: 股票代码列表

        Returns:
            降级后的因子值序列
        """
        logger.info(f"应用优雅降级: {operator_name}")

        # 根据算子类型选择合适的传统数据替代
        fallback_mapping = {
            "satellite_parking_count": "volume",  # 用成交量代替停车场数据
            "social_sentiment_momentum": "returns",  # 用收益率代替情绪动量
            "web_traffic_growth": "volume",  # 用成交量代替网络流量
            "supply_chain_disruption": "volatility",  # 用波动率代替供应链中断
            "foot_traffic_anomaly": "volume",  # 用成交量代替客流量
            "news_sentiment_shock": "returns",  # 用收益率代替新闻情绪
            "search_trend_leading": "volume",  # 用成交量代替搜索趋势
            "shipping_volume_change": "volume",  # 用成交量代替航运量
        }

        fallback_feature = fallback_mapping.get(operator_name, "returns")

        # 从市场数据中提取替代特征
        if fallback_feature == "volume" and "volume" in data.columns:
            # 计算成交量变化率
            factor_values = data["volume"].pct_change(periods=5).fillna(0)
        elif fallback_feature == "returns" and "close" in data.columns:
            # 计算收益率
            factor_values = data["close"].pct_change(periods=1).fillna(0)
        elif fallback_feature == "volatility" and "close" in data.columns:
            # 计算波动率
            returns = data["close"].pct_change()
            factor_values = returns.rolling(window=20).std().fillna(0)
        else:
            # 如果没有合适的替代，返回零序列
            factor_values = pd.Series(0, index=data.index)

        return factor_values

    def _calculate_ic(self, factor_values: pd.Series, returns: pd.Series) -> float:
        """计算信息系数(IC)

        白皮书依据: 第四章 4.1 因子评估标准

        Args:
            factor_values: 因子值序列
            returns: 收益率序列

        Returns:
            信息系数
        """
        # 对齐索引
        common_index = factor_values.index.intersection(returns.index)
        if len(common_index) == 0:
            return 0.0

        factor_aligned = factor_values.loc[common_index]
        returns_aligned = returns.loc[common_index]

        # 移除NaN值
        valid_mask = ~(factor_aligned.isna() | returns_aligned.isna())
        factor_clean = factor_aligned[valid_mask]
        returns_clean = returns_aligned[valid_mask]

        if len(factor_clean) < 2:
            return 0.0

        # 计算Spearman相关系数
        try:
            ic = factor_clean.corr(returns_clean, method="spearman")
            return ic if not np.isnan(ic) else 0.0
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.warning(f"IC计算失败: {e}")
            return 0.0

    def _calculate_ir(self, factor_values: pd.Series, returns: pd.Series) -> float:
        """计算信息比率(IR)

        白皮书依据: 第四章 4.1 因子评估标准

        Args:
            factor_values: 因子值序列
            returns: 收益率序列

        Returns:
            信息比率
        """
        # 计算滚动IC
        window = 20
        if len(factor_values) < window:
            return 0.0

        ic_series = []
        for i in range(window, len(factor_values)):
            factor_window = factor_values.iloc[i - window : i]
            returns_window = returns.iloc[i - window : i]
            ic = self._calculate_ic(factor_window, returns_window)
            ic_series.append(ic)

        if len(ic_series) == 0:
            return 0.0

        # IR = IC均值 / IC标准差
        ic_mean = np.mean(ic_series)
        ic_std = np.std(ic_series)

        if ic_std == 0:
            return 0.0

        ir = ic_mean / ic_std
        return ir if not np.isnan(ir) else 0.0

    def _calculate_sharpe(self, factor_values: pd.Series, returns: pd.Series) -> float:
        """计算夏普比率

        白皮书依据: 第四章 4.1 因子评估标准

        Args:
            factor_values: 因子值序列
            returns: 收益率序列

        Returns:
            夏普比率
        """
        # 对齐索引
        common_index = factor_values.index.intersection(returns.index)
        if len(common_index) == 0:
            return 0.0

        factor_aligned = factor_values.loc[common_index]
        returns_aligned = returns.loc[common_index]

        # 构建因子组合收益（简化版本：因子值作为权重）
        # 标准化因子值
        factor_normalized = (factor_aligned - factor_aligned.mean()) / factor_aligned.std()

        # 计算组合收益
        portfolio_returns = factor_normalized * returns_aligned

        # 移除NaN
        portfolio_returns_clean = portfolio_returns.dropna()

        if len(portfolio_returns_clean) < 2:
            return 0.0

        # 计算夏普比率
        mean_return = portfolio_returns_clean.mean()
        std_return = portfolio_returns_clean.std()

        if std_return == 0:
            return 0.0

        # 年化夏普比率（假设日频数据）
        sharpe = (mean_return / std_return) * np.sqrt(252)

        return sharpe if not np.isnan(sharpe) else 0.0

    def _calculate_fitness(self, ic: float, ir: float, sharpe: float) -> float:
        """计算综合适应度

        白皮书依据: 第四章 4.1 因子评估标准

        Args:
            ic: 信息系数
            ir: 信息比率
            sharpe: 夏普比率

        Returns:
            综合适应度评分
        """
        # 加权组合
        # IC: 30%, IR: 30%, Sharpe: 40%
        fitness = abs(ic) * 0.3 + abs(ir) * 0.3 + max(0, sharpe) * 0.4

        return fitness
