"""替代数据算子注册表

白皮书依据: 第四章 4.1.3 - 替代数据因子挖掘器
版本: v1.0.0

本模块实现8个替代数据专用算子:
1. satellite_parking_count - 卫星停车场数据
2. social_sentiment_momentum - 社交媒体情绪动量
3. web_traffic_growth - 网站流量增长
4. supply_chain_disruption - 供应链中断指数
5. foot_traffic_anomaly - 人流量异常检测
6. news_sentiment_shock - 新闻情绪冲击
7. search_trend_leading - 搜索趋势领先指标
8. shipping_volume_change - 航运量变化
"""

from typing import Any, Callable, Dict, Optional

import pandas as pd
from loguru import logger


class OperatorError(Exception):
    """算子计算错误"""


class DataQualityError(Exception):
    """数据质量错误"""


class AlternativeDataOperatorRegistry:
    """替代数据算子注册表

    白皮书依据: 第四章 4.1.3 - 替代数据因子挖掘器

    提供:
    1. 8个替代数据算子的注册机制
    2. 算子验证和错误处理
    3. 数据质量检查
    4. 算子计算与日志记录

    Attributes:
        operators: 算子名称到计算函数的映射
        operator_metadata: 算子名称到元数据的映射
    """

    def __init__(self):
        """初始化替代数据算子注册表

        白皮书依据: 第四章 4.1.3 - 替代数据因子挖掘器
        """
        self.operators: Dict[str, Callable] = {}
        self.operator_metadata: Dict[str, Dict[str, Any]] = {}

        # 注册所有算子
        self._register_all_operators()

        logger.info(f"AlternativeDataOperatorRegistry初始化完成，共{len(self.operators)}个算子")

    def _register_all_operators(self) -> None:
        """注册所有8个替代数据算子

        白皮书依据: 第四章 4.1.3 - 替代数据因子挖掘器
        """
        # 1. 卫星停车场数据
        self._register_operator(
            name="satellite_parking_count",
            func=self.satellite_parking_count,
            category="satellite",
            description="卫星停车场车辆计数",
            formula="rolling_mean(parking_count, window) / baseline_count",
        )

        # 2. 社交媒体情绪动量
        self._register_operator(
            name="social_sentiment_momentum",
            func=self.social_sentiment_momentum,
            category="social",
            description="社交媒体情绪动量",
            formula="(sentiment_today - sentiment_yesterday) * volume_weight",
        )

        # 3. 网站流量增长
        self._register_operator(
            name="web_traffic_growth",
            func=self.web_traffic_growth,
            category="web",
            description="网站流量增长率",
            formula="(traffic_today - traffic_ma) / traffic_ma",
        )

        # 4. 供应链中断指数
        self._register_operator(
            name="supply_chain_disruption",
            func=self.supply_chain_disruption,
            category="supply_chain",
            description="供应链中断指数",
            formula="weighted_sum(disruption_events) * severity_factor",
        )

        # 5. 人流量异常检测
        self._register_operator(
            name="foot_traffic_anomaly",
            func=self.foot_traffic_anomaly,
            category="foot_traffic",
            description="人流量异常检测",
            formula="(traffic - rolling_mean) / rolling_std > threshold",
        )

        # 6. 新闻情绪冲击
        self._register_operator(
            name="news_sentiment_shock",
            func=self.news_sentiment_shock,
            category="news",
            description="新闻情绪冲击",
            formula="abs(sentiment_change) * news_importance",
        )

        # 7. 搜索趋势领先指标
        self._register_operator(
            name="search_trend_leading",
            func=self.search_trend_leading,
            category="search",
            description="搜索趋势领先指标",
            formula="correlation(search_volume_lag, stock_returns)",
        )

        # 8. 航运量变化
        self._register_operator(
            name="shipping_volume_change",
            func=self.shipping_volume_change,
            category="shipping",
            description="航运量变化率",
            formula="(shipping_volume - baseline) / baseline",
        )

    def _register_operator(  # pylint: disable=too-many-positional-arguments
        self, name: str, func: Callable, category: str, description: str, formula: str
    ) -> None:  # pylint: disable=too-many-positional-arguments
        """注册算子及其元数据

        Args:
            name: 算子名称
            func: 算子计算函数
            category: 算子类别
            description: 算子描述
            formula: 数学公式
        """
        self.operators[name] = func
        self.operator_metadata[name] = {"category": category, "description": description, "formula": formula}

        logger.debug(f"注册算子: {name} ({category})")

    def get_operator(self, name: str) -> Optional[Callable]:
        """根据名称获取算子函数

        Args:
            name: 算子名称

        Returns:
            算子函数，如果不存在则返回None
        """
        return self.operators.get(name)

    def get_operator_names(self) -> list[str]:
        """获取所有算子名称列表

        Returns:
            算子名称列表
        """
        return list(self.operators.keys())

    def get_operators_by_category(self, category: str) -> Dict[str, Callable]:
        """获取指定类别的所有算子

        Args:
            category: 类别名称

        Returns:
            算子名称到函数的映射
        """
        return {
            name: func for name, func in self.operators.items() if self.operator_metadata[name]["category"] == category
        }

    def validate_operator_input(self, data: pd.DataFrame, required_columns: list[str]) -> None:
        """验证算子输入数据

        白皮书依据: 第四章 4.1 - 数据质量要求

        Args:
            data: 输入数据
            required_columns: 必需的列名

        Raises:
            OperatorError: 验证失败时
        """
        if data.empty:
            raise OperatorError("输入数据为空")

        missing_columns = set(required_columns) - set(data.columns)
        if missing_columns:
            raise OperatorError(f"缺少必需列: {missing_columns}")

        # 检查过多的NaN值 (>50%阈值)
        for col in required_columns:
            nan_ratio = data[col].isna().sum() / len(data)
            if nan_ratio > 0.5:
                raise DataQualityError(f"列 {col} 有 {nan_ratio:.1%} NaN值 (阈值: 50%)")

    # ========================================================================
    # 算子实现 (8个)
    # ========================================================================

    def satellite_parking_count(
        self,
        data: pd.DataFrame,
        parking_count_col: str = "parking_count",
        baseline_col: str = "baseline_count",
        window: int = 7,
    ) -> pd.Series:
        """计算卫星停车场车辆计数指标

        白皮书依据: 第四章 4.1.3 - satellite_parking_count
        公式: rolling_mean(parking_count, window) / baseline_count

        通过卫星图像识别停车场车辆数量，反映零售、商场等实体经济活跃度。

        Args:
            data: 包含停车场计数和基准计数的数据框
            parking_count_col: 停车场车辆计数列名
            baseline_col: 基准计数列名
            window: 滚动窗口大小（默认7天）

        Returns:
            停车场活跃度指标序列

        Raises:
            OperatorError: 计算失败时
            DataQualityError: 数据质量不足时
        """
        try:
            self.validate_operator_input(data, [parking_count_col, baseline_col])

            parking_count = data[parking_count_col]
            baseline = data[baseline_col]

            # 计算滚动平均
            parking_ma = parking_count.rolling(window=window).mean()

            # 归一化到基准
            parking_index = parking_ma / (baseline + 1e-8)

            logger.debug(f"计算satellite_parking_count: mean={parking_index.mean():.4f}")

            return parking_index

        except (OperatorError, DataQualityError):
            raise
        except Exception as e:
            logger.error(f"satellite_parking_count计算失败: {e}")
            raise OperatorError(f"satellite_parking_count失败: {e}") from e

    def social_sentiment_momentum(
        self,
        data: pd.DataFrame,
        sentiment_col: str = "sentiment_score",
        volume_col: str = "mention_volume",
        window: int = 5,
    ) -> pd.Series:
        """计算社交媒体情绪动量

        白皮书依据: 第四章 4.1.3 - social_sentiment_momentum
        公式: (sentiment_today - sentiment_yesterday) * volume_weight

        分析社交媒体（微博、Twitter等）上的情绪变化趋势，
        结合讨论热度，捕捉市场情绪转折点。

        Args:
            data: 包含情绪评分和讨论量的数据框
            sentiment_col: 情绪评分列名 [-1, 1]
            volume_col: 讨论量列名
            window: 滚动窗口大小（默认5天）

        Returns:
            情绪动量指标序列

        Raises:
            OperatorError: 计算失败时
        """
        try:
            self.validate_operator_input(data, [sentiment_col, volume_col])

            sentiment = data[sentiment_col]
            volume = data[volume_col]

            # 计算情绪变化
            sentiment_change = sentiment.diff()

            # 计算音量权重（归一化）
            volume_normalized = volume / (volume.rolling(window=window).mean() + 1e-8)

            # 情绪动量 = 情绪变化 * 音量权重
            sentiment_momentum = sentiment_change * volume_normalized

            logger.debug(f"计算social_sentiment_momentum: mean={sentiment_momentum.mean():.4f}")

            return sentiment_momentum

        except Exception as e:
            logger.error(f"social_sentiment_momentum计算失败: {e}")
            raise OperatorError(f"social_sentiment_momentum失败: {e}") from e

    def web_traffic_growth(self, data: pd.DataFrame, traffic_col: str = "web_traffic", window: int = 30) -> pd.Series:
        """计算网站流量增长率

        白皮书依据: 第四章 4.1.3 - web_traffic_growth
        公式: (traffic_today - traffic_ma) / traffic_ma

        监测公司官网、电商平台的访问量变化，
        反映用户兴趣和潜在销售趋势。

        Args:
            data: 包含网站流量的数据框
            traffic_col: 网站流量列名
            window: 滚动窗口大小（默认30天）

        Returns:
            流量增长率序列

        Raises:
            OperatorError: 计算失败时
        """
        try:
            self.validate_operator_input(data, [traffic_col])

            traffic = data[traffic_col]

            # 计算滚动平均
            traffic_ma = traffic.rolling(window=window).mean()

            # 计算增长率
            traffic_growth = (traffic - traffic_ma) / (traffic_ma + 1e-8)

            logger.debug(f"计算web_traffic_growth: mean={traffic_growth.mean():.4f}")

            return traffic_growth

        except Exception as e:
            logger.error(f"web_traffic_growth计算失败: {e}")
            raise OperatorError(f"web_traffic_growth失败: {e}") from e

    def supply_chain_disruption(
        self,
        data: pd.DataFrame,
        disruption_events_col: str = "disruption_events",
        severity_col: str = "severity_score",
        window: int = 14,
    ) -> pd.Series:
        """计算供应链中断指数

        白皮书依据: 第四章 4.1.3 - supply_chain_disruption
        公式: weighted_sum(disruption_events) * severity_factor

        监测供应链中断事件（港口拥堵、工厂停工等），
        评估对企业生产和物流的影响。

        Args:
            data: 包含中断事件和严重程度的数据框
            disruption_events_col: 中断事件计数列名
            severity_col: 严重程度评分列名 [0, 1]
            window: 滚动窗口大小（默认14天）

        Returns:
            供应链中断指数序列

        Raises:
            OperatorError: 计算失败时
        """
        try:
            self.validate_operator_input(data, [disruption_events_col, severity_col])

            events = data[disruption_events_col]
            severity = data[severity_col]

            # 加权事件计数
            weighted_events = events * severity

            # 滚动求和
            disruption_index = weighted_events.rolling(window=window).sum()

            logger.debug(f"计算supply_chain_disruption: mean={disruption_index.mean():.4f}")

            return disruption_index

        except Exception as e:
            logger.error(f"supply_chain_disruption计算失败: {e}")
            raise OperatorError(f"supply_chain_disruption失败: {e}") from e

    def foot_traffic_anomaly(
        self, data: pd.DataFrame, traffic_col: str = "foot_traffic", window: int = 30, threshold: float = 2.0
    ) -> pd.Series:
        """检测人流量异常

        白皮书依据: 第四章 4.1.3 - foot_traffic_anomaly
        公式: (traffic - rolling_mean) / rolling_std > threshold

        通过手机信令、摄像头等数据监测商圈、门店人流量异常，
        识别突发事件或经营状况变化。

        Args:
            data: 包含人流量的数据框
            traffic_col: 人流量列名
            window: 滚动窗口大小（默认30天）
            threshold: 异常阈值（默认2倍标准差）

        Returns:
            异常程度序列（Z-score）

        Raises:
            OperatorError: 计算失败时
        """
        try:
            self.validate_operator_input(data, [traffic_col])

            traffic = data[traffic_col]

            # 计算滚动统计量
            traffic_mean = traffic.rolling(window=window).mean()
            traffic_std = traffic.rolling(window=window).std()

            # 计算Z-score
            z_score = (traffic - traffic_mean) / (traffic_std + 1e-8)

            # 标记异常（超过阈值）
            anomaly_score = z_score.abs()

            logger.debug(
                f"计算foot_traffic_anomaly: mean={anomaly_score.mean():.4f}, "
                f"anomalies={(anomaly_score > threshold).sum()}"
            )

            return anomaly_score

        except Exception as e:
            logger.error(f"foot_traffic_anomaly计算失败: {e}")
            raise OperatorError(f"foot_traffic_anomaly失败: {e}") from e

    def news_sentiment_shock(
        self,
        data: pd.DataFrame,
        sentiment_col: str = "news_sentiment",
        importance_col: str = "news_importance",
        window: int = 3,
    ) -> pd.Series:
        """计算新闻情绪冲击

        白皮书依据: 第四章 4.1.3 - news_sentiment_shock
        公式: abs(sentiment_change) * news_importance

        分析新闻报道的情绪突变，结合新闻重要性，
        捕捉重大事件对市场的冲击。

        Args:
            data: 包含新闻情绪和重要性的数据框
            sentiment_col: 新闻情绪列名 [-1, 1]
            importance_col: 新闻重要性列名 [0, 1]
            window: 滚动窗口大小（默认3天）

        Returns:
            新闻情绪冲击序列

        Raises:
            OperatorError: 计算失败时
        """
        try:
            self.validate_operator_input(data, [sentiment_col, importance_col])

            sentiment = data[sentiment_col]
            importance = data[importance_col]

            # 计算情绪变化
            sentiment_change = sentiment.diff()

            # 计算冲击强度
            shock = sentiment_change.abs() * importance

            # 滚动平均平滑
            shock_smoothed = shock.rolling(window=window).mean()

            logger.debug(f"计算news_sentiment_shock: mean={shock_smoothed.mean():.4f}")

            return shock_smoothed

        except Exception as e:
            logger.error(f"news_sentiment_shock计算失败: {e}")
            raise OperatorError(f"news_sentiment_shock失败: {e}") from e

    def search_trend_leading(  # pylint: disable=too-many-positional-arguments
        self,
        data: pd.DataFrame,
        search_volume_col: str = "search_volume",
        returns_col: str = "returns",
        lag: int = 5,
        window: int = 60,
    ) -> pd.Series:
        """计算搜索趋势领先指标

        白皮书依据: 第四章 4.1.3 - search_trend_leading
        公式: correlation(search_volume_lag, stock_returns)

        分析搜索引擎（百度、Google）上的搜索量变化，
        发现其对股价的领先预测能力。

        Args:
            data: 包含搜索量和收益率的数据框
            search_volume_col: 搜索量列名
            returns_col: 收益率列名
            lag: 领先天数（默认5天）
            window: 滚动窗口大小（默认60天）

        Returns:
            搜索趋势领先指标序列

        Raises:
            OperatorError: 计算失败时
        """
        try:
            self.validate_operator_input(data, [search_volume_col, returns_col])

            search_volume = data[search_volume_col]
            returns = data[returns_col]

            # 搜索量滞后（领先于收益率）
            search_lagged = search_volume.shift(lag)

            # 计算滚动相关性
            leading_indicator = search_lagged.rolling(window=window).corr(returns)

            logger.debug(f"计算search_trend_leading: mean={leading_indicator.mean():.4f}")

            return leading_indicator

        except Exception as e:
            logger.error(f"search_trend_leading计算失败: {e}")
            raise OperatorError(f"search_trend_leading失败: {e}") from e

    def shipping_volume_change(
        self,
        data: pd.DataFrame,
        shipping_volume_col: str = "shipping_volume",
        baseline_col: str = "baseline_volume",
        window: int = 30,
    ) -> pd.Series:
        """计算航运量变化率

        白皮书依据: 第四章 4.1.3 - shipping_volume_change
        公式: (shipping_volume - baseline) / baseline

        监测港口吞吐量、集装箱运输量等航运数据，
        反映国际贸易和经济活动水平。

        Args:
            data: 包含航运量和基准量的数据框
            shipping_volume_col: 航运量列名
            baseline_col: 基准量列名
            window: 滚动窗口大小（默认30天）

        Returns:
            航运量变化率序列

        Raises:
            OperatorError: 计算失败时
        """
        try:
            self.validate_operator_input(data, [shipping_volume_col, baseline_col])

            shipping_volume = data[shipping_volume_col]
            baseline = data[baseline_col]

            # 计算滚动平均
            shipping_ma = shipping_volume.rolling(window=window).mean()
            baseline_ma = baseline.rolling(window=window).mean()

            # 计算变化率
            volume_change = (shipping_ma - baseline_ma) / (baseline_ma + 1e-8)

            logger.debug(f"计算shipping_volume_change: mean={volume_change.mean():.4f}")

            return volume_change

        except Exception as e:
            logger.error(f"shipping_volume_change计算失败: {e}")
            raise OperatorError(f"shipping_volume_change失败: {e}") from e
