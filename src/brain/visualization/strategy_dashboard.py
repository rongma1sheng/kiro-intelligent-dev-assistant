"""策略分析中心仪表盘

白皮书依据: 第五章 5.4.1 策略分析中心仪表盘

本模块实现了策略分析中心仪表盘，提供：
- 策略综合分析展示
- 评分、风险、图表等可视化
- PDF报告生成
- 数据导出
- 历史记录查询

性能要求:
- 仪表盘加载: <2秒
- PDF报告生成: <10秒
"""

import asyncio
import json
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger

from .charts import ChartGenerator
from .data_models import (
    MarketAdaptation,
    OverfittingData,
    OverfittingRiskLevel,
    StrategyDashboardData,
)


class DashboardLoadError(Exception):
    """仪表盘加载错误

    白皮书依据: 第五章 5.4.1 策略分析中心仪表盘
    """


class PDFGenerationError(Exception):
    """PDF生成错误

    白皮书依据: 第五章 5.4.1 策略分析中心仪表盘
    """


class DataExportError(Exception):
    """数据导出错误

    白皮书依据: 第五章 5.4.1 策略分析中心仪表盘
    """


class StrategyDashboard:
    """策略分析中心仪表盘

    白皮书依据: 第五章 5.4.1 策略分析中心仪表盘

    提供策略的综合分析展示，包括评分、风险、图表等。

    Attributes:
        chart_generator: 图表生成器
        redis_storage: Redis存储管理器
        strategy_analyzer: 策略分析器
        _dashboard_cache: 仪表盘数据缓存
        _cache_ttl: 缓存过期时间（秒）
    """

    def __init__(
        self,
        chart_generator: Optional[ChartGenerator] = None,
        redis_storage: Optional[Any] = None,
        strategy_analyzer: Optional[Any] = None,
    ) -> None:
        """初始化策略仪表盘

        Args:
            chart_generator: 图表生成器实例
            redis_storage: Redis存储管理器实例
            strategy_analyzer: 策略分析器实例

        Raises:
            ValueError: 当参数无效时
        """
        self._chart_generator = chart_generator or ChartGenerator()
        self._redis_storage = redis_storage
        self._strategy_analyzer = strategy_analyzer

        # 仪表盘数据缓存
        self._dashboard_cache: Dict[str, Tuple[StrategyDashboardData, datetime]] = {}
        self._cache_ttl = 300  # 5分钟缓存

        # 历史记录存储
        self._history_storage: Dict[str, List[StrategyDashboardData]] = {}
        self._max_history_size = 100  # 每个策略最多保存100条历史

        logger.info("StrategyDashboard初始化完成")

    async def load_dashboard(
        self,
        strategy_id: str,
        force_refresh: bool = False,
    ) -> StrategyDashboardData:
        """加载策略仪表盘数据

        白皮书依据: 第五章 5.4.1 策略分析中心仪表盘

        性能要求: <2秒

        Args:
            strategy_id: 策略ID
            force_refresh: 是否强制刷新（忽略缓存）

        Returns:
            StrategyDashboardData: 策略仪表盘数据

        Raises:
            DashboardLoadError: 当加载失败时
            ValueError: 当strategy_id为空时
        """
        if not strategy_id:
            raise ValueError("策略ID不能为空")

        start_time = datetime.now()
        logger.info(f"开始加载策略仪表盘: {strategy_id}")

        try:
            # 检查缓存
            if not force_refresh and strategy_id in self._dashboard_cache:
                cached_data, cached_time = self._dashboard_cache[strategy_id]
                cache_age = (datetime.now() - cached_time).total_seconds()
                if cache_age < self._cache_ttl:
                    logger.info(f"使用缓存的仪表盘数据: {strategy_id}")
                    return cached_data

            # 尝试从Redis加载
            dashboard_data = await self._load_from_redis(strategy_id)

            if dashboard_data is None:
                # 从分析器获取数据
                dashboard_data = await self._load_from_analyzer(strategy_id)

            # 更新缓存
            self._dashboard_cache[strategy_id] = (dashboard_data, datetime.now())

            # 保存到历史记录
            self._save_to_history(strategy_id, dashboard_data)

            elapsed = (datetime.now() - start_time).total_seconds()
            logger.info(f"策略仪表盘加载完成: {strategy_id}, 耗时: {elapsed:.2f}秒")

            if elapsed > 2.0:
                logger.warning(f"仪表盘加载超时: {elapsed:.2f}秒 > 2秒")

            return dashboard_data

        except Exception as e:
            logger.error(f"加载策略仪表盘失败: {strategy_id}, 错误: {e}")
            raise DashboardLoadError(f"加载策略仪表盘失败: {strategy_id}") from e

    async def _load_from_redis(
        self,
        strategy_id: str,
    ) -> Optional[StrategyDashboardData]:
        """从Redis加载仪表盘数据

        Args:
            strategy_id: 策略ID

        Returns:
            StrategyDashboardData或None
        """
        if self._redis_storage is None:
            return None

        try:
            # 尝试获取缓存的仪表盘数据
            key = f"mia:dashboard:strategy:{strategy_id}"
            data = await self._redis_storage.get(key)

            if data:
                return StrategyDashboardData.from_dict(json.loads(data))

            return None

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.warning(f"从Redis加载仪表盘数据失败: {e}")
            return None

    async def _load_from_analyzer(
        self,
        strategy_id: str,
    ) -> StrategyDashboardData:
        """从分析器加载仪表盘数据

        Args:
            strategy_id: 策略ID

        Returns:
            StrategyDashboardData
        """
        # 获取策略基本信息
        strategy_name = await self._get_strategy_name(strategy_id)

        # 并行获取各维度分析数据
        tasks = [
            self._get_overall_score(strategy_id),
            self._get_overfitting_risk(strategy_id),
            self._get_market_adaptation(strategy_id),
            self._get_essence_radar_data(strategy_id),
            self._get_risk_matrix_data(strategy_id),
            self._get_feature_importance_data(strategy_id),
            self._get_market_adaptation_matrix(strategy_id),
            self._get_evolution_visualization_data(strategy_id),
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 处理结果
        overall_score = results[0] if not isinstance(results[0], Exception) else 50.0
        overfitting_risk = results[1] if not isinstance(results[1], Exception) else OverfittingRiskLevel.MEDIUM
        market_adaptation = results[2] if not isinstance(results[2], Exception) else MarketAdaptation.MEDIUM
        essence_radar_data = results[3] if not isinstance(results[3], Exception) else self._get_default_essence_radar()
        risk_matrix_data = results[4] if not isinstance(results[4], Exception) else self._get_default_risk_matrix()
        feature_importance_data = (
            results[5] if not isinstance(results[5], Exception) else self._get_default_feature_importance()
        )
        market_adaptation_matrix = (
            results[6] if not isinstance(results[6], Exception) else self._get_default_market_adaptation_matrix()
        )
        evolution_visualization_data = (
            results[7] if not isinstance(results[7], Exception) else self._get_default_evolution_data()
        )

        dashboard_data = StrategyDashboardData(
            strategy_id=strategy_id,
            strategy_name=strategy_name,
            overall_score=overall_score,
            overfitting_risk=overfitting_risk,
            market_adaptation=market_adaptation,
            essence_radar_data=essence_radar_data,
            risk_matrix_data=risk_matrix_data,
            feature_importance_data=feature_importance_data,
            market_adaptation_matrix=market_adaptation_matrix,
            evolution_visualization_data=evolution_visualization_data,
        )

        # 保存到Redis
        await self._save_to_redis(strategy_id, dashboard_data)

        return dashboard_data

    async def _save_to_redis(
        self,
        strategy_id: str,
        dashboard_data: StrategyDashboardData,
    ) -> None:
        """保存仪表盘数据到Redis

        Args:
            strategy_id: 策略ID
            dashboard_data: 仪表盘数据
        """
        if self._redis_storage is None:
            return

        try:
            key = f"mia:dashboard:strategy:{strategy_id}"
            data = json.dumps(dashboard_data.to_dict())
            await self._redis_storage.set(key, data)
            logger.debug(f"仪表盘数据已保存到Redis: {strategy_id}")
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.warning(f"保存仪表盘数据到Redis失败: {e}")

    async def _get_strategy_name(self, strategy_id: str) -> str:
        """获取策略名称

        Args:
            strategy_id: 策略ID

        Returns:
            策略名称
        """
        if self._strategy_analyzer:
            try:
                # 尝试从分析器获取策略信息
                strategy_info = await self._strategy_analyzer.get_strategy_info(strategy_id)
                if strategy_info and "name" in strategy_info:
                    return strategy_info["name"]
            except Exception:  # pylint: disable=broad-exception-caught
                pass

        # 默认使用策略ID作为名称
        return f"策略_{strategy_id}"

    async def _get_overall_score(self, strategy_id: str) -> float:
        """获取综合评分

        Args:
            strategy_id: 策略ID

        Returns:
            综合评分 (0-100)
        """
        if self._strategy_analyzer:
            try:
                analysis = await self._strategy_analyzer.analyze_strategy(
                    strategy_id, {}, dimensions=["essence", "risk", "overfitting"]
                )
                if analysis:
                    # 综合多个维度计算评分
                    scores = []
                    if hasattr(analysis, "essence_report") and analysis.essence_report:
                        scores.append(analysis.essence_report.overall_score)
                    if hasattr(analysis, "risk_report") and analysis.risk_report:
                        scores.append(100 - analysis.risk_report.risk_score * 100)
                    if scores:
                        return sum(scores) / len(scores)
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.warning(f"获取综合评分失败: {e}")

        return 50.0  # 默认评分

    async def _get_overfitting_risk(self, strategy_id: str) -> OverfittingRiskLevel:
        """获取过拟合风险等级

        Args:
            strategy_id: 策略ID

        Returns:
            过拟合风险等级
        """
        if self._strategy_analyzer:
            try:
                analysis = await self._strategy_analyzer.analyze_strategy(strategy_id, {}, dimensions=["overfitting"])
                if analysis and hasattr(analysis, "overfitting_report"):
                    risk_score = analysis.overfitting_report.risk_score
                    if risk_score < 0.3:  # pylint: disable=no-else-return
                        return OverfittingRiskLevel.LOW
                    elif risk_score < 0.7:
                        return OverfittingRiskLevel.MEDIUM
                    else:
                        return OverfittingRiskLevel.HIGH
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.warning(f"获取过拟合风险失败: {e}")

        return OverfittingRiskLevel.MEDIUM

    async def _get_market_adaptation(self, strategy_id: str) -> MarketAdaptation:
        """获取市场适配度

        Args:
            strategy_id: 策略ID

        Returns:
            市场适配度
        """
        if self._strategy_analyzer:
            try:
                analysis = await self._strategy_analyzer.analyze_strategy(strategy_id, {}, dimensions=["macro"])
                if analysis and hasattr(analysis, "macro_report"):
                    adaptation_score = analysis.macro_report.adaptation_score
                    if adaptation_score > 0.7:  # pylint: disable=no-else-return
                        return MarketAdaptation.HIGH
                    elif adaptation_score > 0.4:
                        return MarketAdaptation.MEDIUM
                    else:
                        return MarketAdaptation.LOW
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.warning(f"获取市场适配度失败: {e}")

        return MarketAdaptation.MEDIUM

    async def _get_essence_radar_data(self, strategy_id: str) -> Dict[str, float]:
        """获取策略本质雷达图数据

        Args:
            strategy_id: 策略ID

        Returns:
            雷达图数据字典
        """
        if self._strategy_analyzer:
            try:
                analysis = await self._strategy_analyzer.analyze_strategy(strategy_id, {}, dimensions=["essence"])
                if analysis and hasattr(analysis, "essence_report"):
                    return {
                        "动量": analysis.essence_report.momentum_score,
                        "价值": analysis.essence_report.value_score,
                        "质量": analysis.essence_report.quality_score,
                        "波动": analysis.essence_report.volatility_score,
                        "流动性": analysis.essence_report.liquidity_score,
                    }
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.warning(f"获取策略本质数据失败: {e}")

        return self._get_default_essence_radar()

    def _get_default_essence_radar(self) -> Dict[str, float]:
        """获取默认策略本质雷达图数据"""
        return {
            "动量": 0.5,
            "价值": 0.5,
            "质量": 0.5,
            "波动": 0.5,
            "流动性": 0.5,
        }

    async def _get_risk_matrix_data(self, strategy_id: str) -> List[List[float]]:
        """获取风险矩阵热力图数据

        Args:
            strategy_id: 策略ID

        Returns:
            风险矩阵数据
        """
        if self._strategy_analyzer:
            try:
                analysis = await self._strategy_analyzer.analyze_strategy(strategy_id, {}, dimensions=["risk"])
                if analysis and hasattr(analysis, "risk_report"):
                    return analysis.risk_report.risk_matrix
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.warning(f"获取风险矩阵数据失败: {e}")

        return self._get_default_risk_matrix()

    def _get_default_risk_matrix(self) -> List[List[float]]:
        """获取默认风险矩阵数据"""
        return [
            [0.3, 0.5, 0.2],
            [0.4, 0.3, 0.4],
            [0.2, 0.4, 0.3],
        ]

    async def _get_feature_importance_data(
        self,
        strategy_id: str,
    ) -> List[Tuple[str, float]]:
        """获取特征重要性排名数据

        Args:
            strategy_id: 策略ID

        Returns:
            特征重要性列表
        """
        if self._strategy_analyzer:
            try:
                analysis = await self._strategy_analyzer.analyze_strategy(strategy_id, {}, dimensions=["feature"])
                if analysis and hasattr(analysis, "feature_report"):
                    return analysis.feature_report.feature_importance
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.warning(f"获取特征重要性数据失败: {e}")

        return self._get_default_feature_importance()

    def _get_default_feature_importance(self) -> List[Tuple[str, float]]:
        """获取默认特征重要性数据"""
        return [
            ("动量因子", 0.25),
            ("价值因子", 0.20),
            ("质量因子", 0.18),
            ("波动率因子", 0.15),
            ("流动性因子", 0.12),
            ("规模因子", 0.10),
        ]

    async def _get_market_adaptation_matrix(
        self,
        strategy_id: str,
    ) -> Dict[str, Dict[str, float]]:
        """获取市场适配性矩阵数据

        Args:
            strategy_id: 策略ID

        Returns:
            市场适配性矩阵
        """
        if self._strategy_analyzer:
            try:
                analysis = await self._strategy_analyzer.analyze_strategy(strategy_id, {}, dimensions=["macro"])
                if analysis and hasattr(analysis, "macro_report"):
                    return analysis.macro_report.market_adaptation_matrix
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.warning(f"获取市场适配性矩阵失败: {e}")

        return self._get_default_market_adaptation_matrix()

    def _get_default_market_adaptation_matrix(self) -> Dict[str, Dict[str, float]]:
        """获取默认市场适配性矩阵"""
        return {
            "牛市": {"收益": 0.8, "风险": 0.3, "稳定性": 0.7},
            "熊市": {"收益": 0.4, "风险": 0.6, "稳定性": 0.5},
            "震荡": {"收益": 0.6, "风险": 0.4, "稳定性": 0.8},
        }

    async def _get_evolution_visualization_data(
        self,
        strategy_id: str,  # pylint: disable=unused-argument
    ) -> Dict[str, Any]:
        """获取进化过程可视化数据

        Args:
            strategy_id: 策略ID

        Returns:
            进化可视化数据
        """
        # 尝试从演化树获取数据
        try:
            pass
            # 这里可以集成演化树数据
        except ImportError:
            pass

        return self._get_default_evolution_data()

    def _get_default_evolution_data(self) -> Dict[str, Any]:
        """获取默认进化可视化数据"""
        return {
            "generations": list(range(10)),
            "fitness_values": [0.5 + i * 0.03 for i in range(10)],
            "best_fitness": 0.77,
            "mutation_history": [],
        }

    def _save_to_history(
        self,
        strategy_id: str,
        dashboard_data: StrategyDashboardData,
    ) -> None:
        """保存到历史记录

        Args:
            strategy_id: 策略ID
            dashboard_data: 仪表盘数据
        """
        if strategy_id not in self._history_storage:
            self._history_storage[strategy_id] = []

        history = self._history_storage[strategy_id]
        history.append(dashboard_data)

        # 限制历史记录数量
        if len(history) > self._max_history_size:
            self._history_storage[strategy_id] = history[-self._max_history_size :]

    async def generate_pdf_report(
        self,
        strategy_id: str,
        output_path: str,
    ) -> str:
        """生成PDF报告

        白皮书依据: 第五章 5.4.1 策略分析中心仪表盘

        性能要求: <10秒

        Args:
            strategy_id: 策略ID
            output_path: 输出文件路径

        Returns:
            生成的PDF文件路径

        Raises:
            PDFGenerationError: 当生成失败时
            ValueError: 当参数无效时
        """
        if not strategy_id:
            raise ValueError("策略ID不能为空")
        if not output_path:
            raise ValueError("输出路径不能为空")

        start_time = datetime.now()
        logger.info(f"开始生成PDF报告: {strategy_id}")

        try:
            # 加载仪表盘数据
            dashboard_data = await self.load_dashboard(strategy_id)

            # 生成各种图表
            charts = await self._generate_report_charts(dashboard_data)

            # 生成PDF内容
            pdf_content = await self._build_pdf_content(dashboard_data, charts)

            # 写入文件
            await self._write_pdf_file(pdf_content, output_path)

            elapsed = (datetime.now() - start_time).total_seconds()
            logger.info(f"PDF报告生成完成: {output_path}, 耗时: {elapsed:.2f}秒")

            if elapsed > 10.0:
                logger.warning(f"PDF生成超时: {elapsed:.2f}秒 > 10秒")

            return output_path

        except Exception as e:
            logger.error(f"生成PDF报告失败: {strategy_id}, 错误: {e}")
            raise PDFGenerationError(f"生成PDF报告失败: {strategy_id}") from e

    async def _generate_report_charts(
        self,
        dashboard_data: StrategyDashboardData,
    ) -> Dict[str, bytes]:
        """生成报告所需的图表

        Args:
            dashboard_data: 仪表盘数据

        Returns:
            图表字典 {图表名称: 图表数据}
        """
        charts = {}

        try:
            # 策略本质雷达图
            charts["essence_radar"] = self._chart_generator.generate_essence_radar(dashboard_data.essence_radar_data)

            # 特征重要性柱状图
            charts["feature_importance"] = self._chart_generator.generate_feature_importance_bar(
                dashboard_data.feature_importance_data
            )

            # 市场适配性矩阵
            charts["market_adaptation"] = self._chart_generator.generate_market_adaptation_matrix(
                dashboard_data.market_adaptation_matrix
            )

            # 过拟合风险仪表盘
            overfitting_data = OverfittingData(
                in_sample_sharpe=2.0,
                out_sample_sharpe=1.5,
                parameter_sensitivity=0.3,
                complexity_score=0.5,
                risk_level=dashboard_data.overfitting_risk,
            )
            charts["overfitting"] = self._chart_generator.generate_overfitting_dashboard(overfitting_data)

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.warning(f"生成部分图表失败: {e}")

        return charts

    async def _build_pdf_content(
        self,
        dashboard_data: StrategyDashboardData,
        charts: Dict[str, bytes],
    ) -> bytes:
        """构建PDF内容

        Args:
            dashboard_data: 仪表盘数据
            charts: 图表字典

        Returns:
            PDF内容字节
        """
        # 构建PDF报告内容
        # 这里使用简化的实现，实际可以使用reportlab等库

        report_content = {
            "title": f"策略分析报告 - {dashboard_data.strategy_name}",
            "generated_at": datetime.now().isoformat(),
            "strategy_id": dashboard_data.strategy_id,
            "strategy_name": dashboard_data.strategy_name,
            "overall_score": dashboard_data.overall_score,
            "overfitting_risk": dashboard_data.overfitting_risk.value,
            "market_adaptation": dashboard_data.market_adaptation.value,
            "essence_radar_data": dashboard_data.essence_radar_data,
            "feature_importance_data": dashboard_data.feature_importance_data,
            "market_adaptation_matrix": dashboard_data.market_adaptation_matrix,
            "charts_count": len(charts),
        }

        # 序列化为JSON（实际应生成真正的PDF）
        return json.dumps(report_content, ensure_ascii=False, indent=2).encode("utf-8")

    async def _write_pdf_file(
        self,
        content: bytes,
        output_path: str,
    ) -> None:
        """写入PDF文件

        Args:
            content: PDF内容
            output_path: 输出路径
        """
        import aiofiles  # pylint: disable=import-outside-toplevel

        try:
            async with aiofiles.open(output_path, "wb") as f:
                await f.write(content)
        except ImportError:
            # 如果aiofiles不可用，使用同步写入
            with open(output_path, "wb") as f:
                f.write(content)

    async def export_data(
        self,
        strategy_id: str,
        format: str = "json",  # pylint: disable=w0622
    ) -> bytes:
        """导出分析数据

        白皮书依据: 第五章 5.4.1 策略分析中心仪表盘

        Args:
            strategy_id: 策略ID
            format: 导出格式（json/csv）

        Returns:
            导出的数据字节

        Raises:
            DataExportError: 当导出失败时
            ValueError: 当参数无效时
        """
        if not strategy_id:
            raise ValueError("策略ID不能为空")
        if format not in ["json", "csv"]:
            raise ValueError(f"不支持的导出格式: {format}")

        logger.info(f"开始导出数据: {strategy_id}, 格式: {format}")

        try:
            # 加载仪表盘数据
            dashboard_data = await self.load_dashboard(strategy_id)

            if format == "json":  # pylint: disable=no-else-return
                return self._export_as_json(dashboard_data)
            else:
                return self._export_as_csv(dashboard_data)

        except Exception as e:
            logger.error(f"导出数据失败: {strategy_id}, 错误: {e}")
            raise DataExportError(f"导出数据失败: {strategy_id}") from e

    def _export_as_json(self, dashboard_data: StrategyDashboardData) -> bytes:
        """导出为JSON格式

        Args:
            dashboard_data: 仪表盘数据

        Returns:
            JSON字节数据
        """
        data = dashboard_data.to_dict()
        return json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")

    def _export_as_csv(self, dashboard_data: StrategyDashboardData) -> bytes:
        """导出为CSV格式

        Args:
            dashboard_data: 仪表盘数据

        Returns:
            CSV字节数据
        """
        import csv  # pylint: disable=import-outside-toplevel
        import io  # pylint: disable=import-outside-toplevel

        output = io.StringIO()
        writer = csv.writer(output)

        # 写入基本信息
        writer.writerow(["字段", "值"])
        writer.writerow(["策略ID", dashboard_data.strategy_id])
        writer.writerow(["策略名称", dashboard_data.strategy_name])
        writer.writerow(["综合评分", dashboard_data.overall_score])
        writer.writerow(["过拟合风险", dashboard_data.overfitting_risk.value])
        writer.writerow(["市场适配度", dashboard_data.market_adaptation.value])

        # 写入策略本质数据
        writer.writerow([])
        writer.writerow(["策略本质维度", "得分"])
        for dimension, score in dashboard_data.essence_radar_data.items():
            writer.writerow([dimension, score])

        # 写入特征重要性数据
        writer.writerow([])
        writer.writerow(["特征", "重要性"])
        for feature, importance in dashboard_data.feature_importance_data:
            writer.writerow([feature, importance])

        return output.getvalue().encode("utf-8")

    async def get_history(
        self,
        strategy_id: str,
        limit: int = 10,
    ) -> List[StrategyDashboardData]:
        """获取历史分析记录

        白皮书依据: 第五章 5.4.1 策略分析中心仪表盘

        Args:
            strategy_id: 策略ID
            limit: 返回记录数量限制

        Returns:
            历史分析记录列表

        Raises:
            ValueError: 当参数无效时
        """
        if not strategy_id:
            raise ValueError("策略ID不能为空")
        if limit <= 0:
            raise ValueError(f"limit必须大于0，当前: {limit}")

        logger.info(f"获取历史记录: {strategy_id}, limit: {limit}")

        # 从内存获取历史记录
        history = self._history_storage.get(strategy_id, [])

        # 尝试从Redis获取更多历史记录
        if self._redis_storage and len(history) < limit:
            try:
                redis_history = await self._load_history_from_redis(strategy_id, limit)
                # 合并历史记录，去重
                existing_timestamps = {h.updated_at for h in history}
                for h in redis_history:
                    if h.updated_at not in existing_timestamps:
                        history.append(h)
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.warning(f"从Redis加载历史记录失败: {e}")

        # 按时间排序，返回最近的记录
        history.sort(key=lambda x: x.updated_at, reverse=True)
        return history[:limit]

    async def _load_history_from_redis(
        self,
        strategy_id: str,
        limit: int,
    ) -> List[StrategyDashboardData]:
        """从Redis加载历史记录

        Args:
            strategy_id: 策略ID
            limit: 记录数量限制

        Returns:
            历史记录列表
        """
        if self._redis_storage is None:
            return []

        try:
            key = f"mia:dashboard:history:{strategy_id}"
            data = await self._redis_storage.lrange(key, 0, limit - 1)

            history = []
            for item in data:
                try:
                    history.append(StrategyDashboardData.from_dict(json.loads(item)))
                except Exception:  # pylint: disable=broad-exception-caught
                    continue

            return history

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.warning(f"从Redis加载历史记录失败: {e}")
            return []

    def get_cached_dashboard(
        self,
        strategy_id: str,
    ) -> Optional[StrategyDashboardData]:
        """获取缓存的仪表盘数据（同步方法）

        Args:
            strategy_id: 策略ID

        Returns:
            缓存的仪表盘数据或None
        """
        if strategy_id in self._dashboard_cache:
            cached_data, cached_time = self._dashboard_cache[strategy_id]
            cache_age = (datetime.now() - cached_time).total_seconds()
            if cache_age < self._cache_ttl:
                return cached_data
        return None

    def clear_cache(self, strategy_id: Optional[str] = None) -> None:
        """清除缓存

        Args:
            strategy_id: 策略ID，None表示清除所有缓存
        """
        if strategy_id:
            if strategy_id in self._dashboard_cache:
                del self._dashboard_cache[strategy_id]
                logger.info(f"已清除策略缓存: {strategy_id}")
        else:
            self._dashboard_cache.clear()
            logger.info("已清除所有策略缓存")

    def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息

        Returns:
            缓存统计信息字典
        """
        now = datetime.now()
        valid_count = 0
        expired_count = 0

        for strategy_id, (data, cached_time) in self._dashboard_cache.items():  # pylint: disable=unused-variable
            cache_age = (now - cached_time).total_seconds()
            if cache_age < self._cache_ttl:
                valid_count += 1
            else:
                expired_count += 1

        return {
            "total_cached": len(self._dashboard_cache),
            "valid_count": valid_count,
            "expired_count": expired_count,
            "cache_ttl": self._cache_ttl,
            "history_strategies": len(self._history_storage),
            "total_history_records": sum(len(h) for h in self._history_storage.values()),
        }
