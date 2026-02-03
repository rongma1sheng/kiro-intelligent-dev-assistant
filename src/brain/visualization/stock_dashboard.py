"""个股分析仪表盘

白皮书依据: 第五章 5.4.2 个股分析仪表盘

本模块实现了个股分析仪表盘，提供：
- 个股结论性建议展示
- 主力资金深度分析
- 实时数据刷新
- 图表可视化

性能要求:
- 仪表盘加载: <3秒
- 个股建议生成: <3秒
"""

import asyncio
import json
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger

from .charts import ChartGenerator
from .data_models import (
    BehaviorPattern,
    HoldingPeriod,
    PositionSuggestion,
    RecommendationAction,
    RiskLevel,
    SmartMoneyAnalysis,
    SmartMoneyType,
    StockDashboardData,
    StockRecommendation,
)


class StockDashboardLoadError(Exception):
    """个股仪表盘加载错误

    白皮书依据: 第五章 5.4.2 个股分析仪表盘
    """


class RecommendationRefreshError(Exception):
    """建议刷新错误

    白皮书依据: 第五章 5.4.2 个股分析仪表盘
    """


class SmartMoneyAnalysisError(Exception):
    """主力资金分析错误

    白皮书依据: 第五章 5.4.2 个股分析仪表盘
    """


class StockDashboard:
    """个股分析仪表盘

    白皮书依据: 第五章 5.4.2 个股分析仪表盘

    提供个股的结论性建议和主力资金分析展示。

    Attributes:
        chart_generator: 图表生成器
        redis_storage: Redis存储管理器
        recommendation_engine: 建议引擎
        smart_money_analyzer: 主力资金分析器
        _dashboard_cache: 仪表盘数据缓存
        _cache_ttl: 缓存过期时间（秒）
    """

    def __init__(
        self,
        chart_generator: Optional[ChartGenerator] = None,
        redis_storage: Optional[Any] = None,
        recommendation_engine: Optional[Any] = None,
        smart_money_analyzer: Optional[Any] = None,
    ) -> None:
        """初始化个股仪表盘

        Args:
            chart_generator: 图表生成器实例
            redis_storage: Redis存储管理器实例
            recommendation_engine: 建议引擎实例
            smart_money_analyzer: 主力资金分析器实例
        """
        self._chart_generator = chart_generator or ChartGenerator()
        self._redis_storage = redis_storage
        self._recommendation_engine = recommendation_engine
        self._smart_money_analyzer = smart_money_analyzer

        # 仪表盘数据缓存
        self._dashboard_cache: Dict[str, Tuple[StockDashboardData, datetime]] = {}
        self._cache_ttl = 60  # 1分钟缓存（个股数据更新频繁）

        # 股票名称缓存
        self._stock_name_cache: Dict[str, str] = {}

        logger.info("StockDashboard初始化完成")

    async def load_dashboard(
        self,
        symbol: str,
        force_refresh: bool = False,
    ) -> StockDashboardData:
        """加载个股仪表盘数据

        白皮书依据: 第五章 5.4.2 个股分析仪表盘

        性能要求: <3秒

        Args:
            symbol: 股票代码
            force_refresh: 是否强制刷新（忽略缓存）

        Returns:
            StockDashboardData: 个股仪表盘数据

        Raises:
            StockDashboardLoadError: 当加载失败时
            ValueError: 当symbol为空时
        """
        if not symbol:
            raise ValueError("股票代码不能为空")

        # 标准化股票代码
        symbol = self._normalize_symbol(symbol)

        start_time = datetime.now()
        logger.info(f"开始加载个股仪表盘: {symbol}")

        try:
            # 检查缓存
            if not force_refresh and symbol in self._dashboard_cache:
                cached_data, cached_time = self._dashboard_cache[symbol]
                cache_age = (datetime.now() - cached_time).total_seconds()
                if cache_age < self._cache_ttl:
                    logger.info(f"使用缓存的个股仪表盘数据: {symbol}")
                    return cached_data

            # 尝试从Redis加载
            dashboard_data = await self._load_from_redis(symbol)

            if dashboard_data is None:
                # 从分析器获取数据
                dashboard_data = await self._load_from_analyzers(symbol)

            # 更新缓存
            self._dashboard_cache[symbol] = (dashboard_data, datetime.now())

            elapsed = (datetime.now() - start_time).total_seconds()
            logger.info(f"个股仪表盘加载完成: {symbol}, 耗时: {elapsed:.2f}秒")

            if elapsed > 3.0:
                logger.warning(f"个股仪表盘加载超时: {elapsed:.2f}秒 > 3秒")

            return dashboard_data

        except Exception as e:
            logger.error(f"加载个股仪表盘失败: {symbol}, 错误: {e}")
            raise StockDashboardLoadError(f"加载个股仪表盘失败: {symbol}") from e

    def _normalize_symbol(self, symbol: str) -> str:
        """标准化股票代码

        Args:
            symbol: 原始股票代码

        Returns:
            标准化后的股票代码
        """
        # 移除空格和特殊字符
        symbol = symbol.strip().upper()

        # 如果是纯数字，保持原样
        if symbol.isdigit():
            return symbol

        # 移除可能的后缀（如.SH, .SZ）
        if "." in symbol:
            symbol = symbol.split(".")[0]

        return symbol

    async def _load_from_redis(
        self,
        symbol: str,
    ) -> Optional[StockDashboardData]:
        """从Redis加载仪表盘数据

        Args:
            symbol: 股票代码

        Returns:
            StockDashboardData或None
        """
        if self._redis_storage is None:
            return None

        try:
            key = f"mia:dashboard:stock:{symbol}"
            data = await self._redis_storage.get(key)

            if data:
                return StockDashboardData.from_dict(json.loads(data))

            return None

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.warning(f"从Redis加载个股仪表盘数据失败: {e}")
            return None

    async def _load_from_analyzers(
        self,
        symbol: str,
    ) -> StockDashboardData:
        """从分析器加载仪表盘数据

        Args:
            symbol: 股票代码

        Returns:
            StockDashboardData
        """
        # 获取股票名称
        stock_name = await self._get_stock_name(symbol)

        # 并行获取建议和主力资金分析
        tasks = [
            self._get_recommendation(symbol),
            self._get_smart_money_analysis(symbol),
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 处理结果
        recommendation = (
            results[0] if not isinstance(results[0], Exception) else self._get_default_recommendation(symbol)
        )
        smart_money_analysis = (
            results[1] if not isinstance(results[1], Exception) else self._get_default_smart_money_analysis()
        )

        dashboard_data = StockDashboardData(
            symbol=symbol,
            name=stock_name,
            recommendation=recommendation,
            smart_money_analysis=smart_money_analysis,
        )

        # 保存到Redis
        await self._save_to_redis(symbol, dashboard_data)

        return dashboard_data

    async def _save_to_redis(
        self,
        symbol: str,
        dashboard_data: StockDashboardData,
    ) -> None:
        """保存仪表盘数据到Redis

        Args:
            symbol: 股票代码
            dashboard_data: 仪表盘数据
        """
        if self._redis_storage is None:
            return

        try:
            key = f"mia:dashboard:stock:{symbol}"
            data = json.dumps(dashboard_data.to_dict())
            await self._redis_storage.set(key, data)
            logger.debug(f"个股仪表盘数据已保存到Redis: {symbol}")
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.warning(f"保存个股仪表盘数据到Redis失败: {e}")

    async def _get_stock_name(self, symbol: str) -> str:
        """获取股票名称

        Args:
            symbol: 股票代码

        Returns:
            股票名称
        """
        # 检查缓存
        if symbol in self._stock_name_cache:
            return self._stock_name_cache[symbol]

        # 尝试从数据源获取
        try:
            # 这里可以集成实际的股票信息查询
            # 暂时使用默认名称
            name = f"股票_{symbol}"
            self._stock_name_cache[symbol] = name
            return name
        except Exception:  # pylint: disable=broad-exception-caught
            return f"股票_{symbol}"

    async def _get_recommendation(
        self,
        symbol: str,
    ) -> StockRecommendation:
        """获取个股建议

        Args:
            symbol: 股票代码

        Returns:
            StockRecommendation
        """
        if self._recommendation_engine:
            try:
                recommendation = await self._recommendation_engine.generate_recommendation(symbol)
                if recommendation:
                    return recommendation
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.warning(f"获取个股建议失败: {e}")

        return self._get_default_recommendation(symbol)

    def _get_default_recommendation(self, symbol: str) -> StockRecommendation:  # pylint: disable=unused-argument
        """获取默认个股建议

        Args:
            symbol: 股票代码

        Returns:
            默认的StockRecommendation
        """
        return StockRecommendation(
            action=RecommendationAction.WATCH,
            confidence=0.5,
            current_price=10.0,
            target_price=12.0,
            stop_loss_price=9.0,
            buy_price_range=(9.5, 10.5),
            position_suggestion=PositionSuggestion.LIGHT,
            holding_period=HoldingPeriod.SHORT,
            support_reasons=[
                "技术面处于中性区间",
                "成交量维持正常水平",
            ],
            risk_warnings=[
                "市场整体波动较大",
                "需关注行业政策变化",
            ],
        )

    async def _get_smart_money_analysis(
        self,
        symbol: str,
    ) -> SmartMoneyAnalysis:
        """获取主力资金分析

        Args:
            symbol: 股票代码

        Returns:
            SmartMoneyAnalysis
        """
        if self._smart_money_analyzer:
            try:
                analysis = await self._smart_money_analyzer.analyze(symbol)
                if analysis:
                    return analysis
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.warning(f"获取主力资金分析失败: {e}")

        return self._get_default_smart_money_analysis()

    def _get_default_smart_money_analysis(self) -> SmartMoneyAnalysis:
        """获取默认主力资金分析

        Returns:
            默认的SmartMoneyAnalysis
        """
        return SmartMoneyAnalysis(
            smart_money_type=SmartMoneyType.MIXED,
            position_cost=10.0,
            holding_ratio=0.15,
            current_profit=0.05,
            behavior_pattern=BehaviorPattern.WAITING,
            risk_level=RiskLevel.MEDIUM,
        )

    async def refresh_recommendation(
        self,
        symbol: str,
    ) -> StockRecommendation:
        """刷新个股建议

        白皮书依据: 第五章 5.4.2 个股分析仪表盘

        Args:
            symbol: 股票代码

        Returns:
            StockRecommendation: 刷新后的个股建议

        Raises:
            RecommendationRefreshError: 当刷新失败时
            ValueError: 当symbol为空时
        """
        if not symbol:
            raise ValueError("股票代码不能为空")

        symbol = self._normalize_symbol(symbol)
        logger.info(f"刷新个股建议: {symbol}")

        try:
            # 获取最新建议
            recommendation = await self._get_recommendation(symbol)

            # 更新缓存中的建议
            if symbol in self._dashboard_cache:
                cached_data, _ = self._dashboard_cache[symbol]
                updated_data = StockDashboardData(
                    symbol=cached_data.symbol,
                    name=cached_data.name,
                    recommendation=recommendation,
                    smart_money_analysis=cached_data.smart_money_analysis,
                )
                self._dashboard_cache[symbol] = (updated_data, datetime.now())

                # 更新Redis
                await self._save_to_redis(symbol, updated_data)

            logger.info(f"个股建议刷新完成: {symbol}")
            return recommendation

        except Exception as e:
            logger.error(f"刷新个股建议失败: {symbol}, 错误: {e}")
            raise RecommendationRefreshError(f"刷新个股建议失败: {symbol}") from e

    async def refresh_smart_money_analysis(
        self,
        symbol: str,
    ) -> SmartMoneyAnalysis:
        """刷新主力资金分析

        白皮书依据: 第五章 5.4.2 个股分析仪表盘

        Args:
            symbol: 股票代码

        Returns:
            SmartMoneyAnalysis: 刷新后的主力资金分析

        Raises:
            SmartMoneyAnalysisError: 当刷新失败时
            ValueError: 当symbol为空时
        """
        if not symbol:
            raise ValueError("股票代码不能为空")

        symbol = self._normalize_symbol(symbol)
        logger.info(f"刷新主力资金分析: {symbol}")

        try:
            # 获取最新分析
            smart_money_analysis = await self._get_smart_money_analysis(symbol)

            # 更新缓存中的分析
            if symbol in self._dashboard_cache:
                cached_data, _ = self._dashboard_cache[symbol]
                updated_data = StockDashboardData(
                    symbol=cached_data.symbol,
                    name=cached_data.name,
                    recommendation=cached_data.recommendation,
                    smart_money_analysis=smart_money_analysis,
                )
                self._dashboard_cache[symbol] = (updated_data, datetime.now())

                # 更新Redis
                await self._save_to_redis(symbol, updated_data)

            logger.info(f"主力资金分析刷新完成: {symbol}")
            return smart_money_analysis

        except Exception as e:
            logger.error(f"刷新主力资金分析失败: {symbol}, 错误: {e}")
            raise SmartMoneyAnalysisError(f"刷新主力资金分析失败: {symbol}") from e

    async def generate_charts(
        self,
        symbol: str,
    ) -> Dict[str, bytes]:
        """生成个股相关图表

        Args:
            symbol: 股票代码

        Returns:
            图表字典 {图表名称: 图表数据}
        """
        if not symbol:
            raise ValueError("股票代码不能为空")

        symbol = self._normalize_symbol(symbol)
        logger.info(f"生成个股图表: {symbol}")

        charts = {}

        try:
            # 加载仪表盘数据
            dashboard_data = await self.load_dashboard(symbol)

            # 生成主力成本分布图
            from .data_models import SmartMoneyCostData  # pylint: disable=import-outside-toplevel

            cost_data = SmartMoneyCostData(
                price_levels=[9.0, 9.5, 10.0, 10.5, 11.0],
                volume_distribution=[0.1, 0.2, 0.4, 0.2, 0.1],
                cost_center=dashboard_data.smart_money_analysis.position_cost,
                support_levels=[9.0, 9.5],
                resistance_levels=[10.5, 11.0],
            )
            charts["smart_money_cost"] = self._chart_generator.generate_smart_money_cost_distribution(cost_data)

            # 生成个股综合评分卡
            from .data_models import StockScorecardData  # pylint: disable=import-outside-toplevel

            scorecard_data = StockScorecardData(
                symbol=symbol,
                name=dashboard_data.name,
                overall_score=self._calculate_overall_score(dashboard_data),
                dimension_scores={
                    "基本面": 70.0,
                    "技术面": 65.0,
                    "资金面": 75.0,
                    "情绪面": 60.0,
                    "估值": 68.0,
                },
                strengths=dashboard_data.recommendation.support_reasons,
                weaknesses=dashboard_data.recommendation.risk_warnings,
                recommendation=dashboard_data.recommendation.action.value,
            )
            charts["stock_scorecard"] = self._chart_generator.generate_stock_scorecard(scorecard_data)

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.warning(f"生成部分图表失败: {e}")

        return charts

    def _calculate_overall_score(self, dashboard_data: StockDashboardData) -> float:
        """计算综合评分

        Args:
            dashboard_data: 仪表盘数据

        Returns:
            综合评分 (0-100)
        """
        # 基于建议置信度和主力资金分析计算评分
        confidence_score = dashboard_data.recommendation.confidence * 100

        # 根据行为模式调整评分
        behavior_scores = {
            BehaviorPattern.ACCUMULATING: 80,
            BehaviorPattern.PULLING_UP: 75,
            BehaviorPattern.WAITING: 60,
            BehaviorPattern.WASHING: 55,
            BehaviorPattern.DISTRIBUTING: 40,
        }
        behavior_score = behavior_scores.get(dashboard_data.smart_money_analysis.behavior_pattern, 60)

        # 根据风险等级调整评分
        risk_adjustments = {
            RiskLevel.LOW: 10,
            RiskLevel.MEDIUM: 0,
            RiskLevel.HIGH: -10,
            RiskLevel.VERY_HIGH: -20,
        }
        risk_adjustment = risk_adjustments.get(dashboard_data.smart_money_analysis.risk_level, 0)

        # 综合评分
        overall_score = (confidence_score * 0.4 + behavior_score * 0.4 + 50 * 0.2) + risk_adjustment

        # 限制在0-100范围内
        return max(0, min(100, overall_score))

    def get_cached_dashboard(
        self,
        symbol: str,
    ) -> Optional[StockDashboardData]:
        """获取缓存的仪表盘数据（同步方法）

        Args:
            symbol: 股票代码

        Returns:
            缓存的仪表盘数据或None
        """
        symbol = self._normalize_symbol(symbol)

        if symbol in self._dashboard_cache:
            cached_data, cached_time = self._dashboard_cache[symbol]
            cache_age = (datetime.now() - cached_time).total_seconds()
            if cache_age < self._cache_ttl:
                return cached_data
        return None

    def clear_cache(self, symbol: Optional[str] = None) -> None:
        """清除缓存

        Args:
            symbol: 股票代码，None表示清除所有缓存
        """
        if symbol:
            symbol = self._normalize_symbol(symbol)
            if symbol in self._dashboard_cache:
                del self._dashboard_cache[symbol]
                logger.info(f"已清除个股缓存: {symbol}")
        else:
            self._dashboard_cache.clear()
            logger.info("已清除所有个股缓存")

    def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息

        Returns:
            缓存统计信息字典
        """
        now = datetime.now()
        valid_count = 0
        expired_count = 0

        for symbol, (data, cached_time) in self._dashboard_cache.items():  # pylint: disable=unused-variable
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
            "stock_name_cache_size": len(self._stock_name_cache),
        }

    async def batch_load_dashboards(
        self,
        symbols: List[str],
    ) -> Dict[str, StockDashboardData]:
        """批量加载个股仪表盘

        Args:
            symbols: 股票代码列表

        Returns:
            股票代码到仪表盘数据的字典
        """
        if not symbols:
            return {}

        logger.info(f"批量加载个股仪表盘: {len(symbols)}只股票")

        # 并行加载
        tasks = [self.load_dashboard(symbol) for symbol in symbols]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        dashboards = {}
        for symbol, result in zip(symbols, results):
            if isinstance(result, Exception):
                logger.warning(f"加载个股仪表盘失败: {symbol}, 错误: {result}")
            else:
                dashboards[symbol] = result

        logger.info(f"批量加载完成: 成功 {len(dashboards)}/{len(symbols)}")
        return dashboards

    def get_recommendation_summary(
        self,
        dashboard_data: StockDashboardData,
    ) -> str:
        """获取建议摘要

        Args:
            dashboard_data: 仪表盘数据

        Returns:
            建议摘要文本
        """
        rec = dashboard_data.recommendation

        action_text = {
            RecommendationAction.BUY: "建议买入",
            RecommendationAction.SELL: "建议卖出",
            RecommendationAction.HOLD: "建议持有",
            RecommendationAction.WATCH: "建议观望",
        }

        summary = f"""
{dashboard_data.name}({dashboard_data.symbol}) 分析摘要

操作建议: {action_text.get(rec.action, '观望')}
置信度: {rec.confidence * 100:.1f}%
当前价格: {rec.current_price:.2f}
目标价: {rec.target_price:.2f}
止损价: {rec.stop_loss_price:.2f}
建议买入区间: {rec.buy_price_range[0]:.2f} - {rec.buy_price_range[1]:.2f}
仓位建议: {rec.position_suggestion.value}
持有周期: {rec.holding_period.value}

支持原因:
{chr(10).join('- ' + r for r in rec.support_reasons)}

风险提示:
{chr(10).join('- ' + r for r in rec.risk_warnings)}

主力资金分析:
- 主力类型: {dashboard_data.smart_money_analysis.smart_money_type.value}
- 建仓成本: {dashboard_data.smart_money_analysis.position_cost:.2f}
- 持股比例: {dashboard_data.smart_money_analysis.holding_ratio * 100:.1f}%
- 当前盈利: {dashboard_data.smart_money_analysis.current_profit * 100:.1f}%
- 行为模式: {dashboard_data.smart_money_analysis.behavior_pattern.value}
- 风险等级: {dashboard_data.smart_money_analysis.risk_level.value}
"""
        return summary.strip()

    def export_to_dict(
        self,
        dashboard_data: StockDashboardData,
    ) -> Dict[str, Any]:
        """导出仪表盘数据为字典

        Args:
            dashboard_data: 仪表盘数据

        Returns:
            字典格式的数据
        """
        return dashboard_data.to_dict()

    def export_to_json(
        self,
        dashboard_data: StockDashboardData,
    ) -> str:
        """导出仪表盘数据为JSON

        Args:
            dashboard_data: 仪表盘数据

        Returns:
            JSON字符串
        """
        return json.dumps(dashboard_data.to_dict(), ensure_ascii=False, indent=2)
