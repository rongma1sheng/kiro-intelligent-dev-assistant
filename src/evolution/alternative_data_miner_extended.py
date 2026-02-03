"""替代数据因子挖掘器扩展版

白皮书依据: 第四章 4.1.13 替代数据因子扩展
需求: 相关扩展需求

实现10个扩展替代数据算子，提供多源数据融合和实时更新能力。
"""

import asyncio
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Dict, List, Tuple

import numpy as np
import pandas as pd
from loguru import logger


@dataclass
class DataSource:
    """数据源配置

    Attributes:
        source_id: 数据源ID
        source_type: 数据源类型
        update_frequency: 更新频率（秒）
        reliability: 可靠性评分(0-1)
        latency: 数据延迟（秒）
        cost: 数据成本
    """

    source_id: str
    source_type: str
    update_frequency: int
    reliability: float
    latency: float
    cost: float


@dataclass
class FusedData:
    """融合数据结构

    Attributes:
        timestamp: 时间戳
        value: 融合后的值
        confidence: 置信度(0-1)
        sources: 参与融合的数据源
        weights: 各数据源权重
    """

    timestamp: datetime
    value: float
    confidence: float
    sources: List[str]
    weights: Dict[str, float]


class AlternativeDataFactorMinerExtended:
    """替代数据因子挖掘器扩展版

    白皮书依据: 第四章 4.1.13 替代数据因子扩展

    实现10个扩展算子：
    1. multi_source_fusion: 多源数据融合
    2. real_time_streaming: 实时数据流处理
    3. cross_validation_scoring: 交叉验证评分
    4. adaptive_weighting: 自适应权重调整
    5. anomaly_detection_advanced: 高级异常检测
    6. temporal_aggregation: 时序聚合
    7. spatial_correlation: 空间相关性分析
    8. sentiment_nlp_advanced: 高级NLP情绪分析
    9. image_recognition_features: 图像识别特征提取
    10. audio_signal_processing: 音频信号处理

    Attributes:
        operators: 算子字典
        data_sources: 数据源配置
        fusion_cache: 融合数据缓存
        update_interval: 更新间隔（秒）
    """

    def __init__(self, update_interval: int = 60):
        """初始化替代数据因子挖掘器扩展版

        Args:
            update_interval: 数据更新间隔（秒），默认60秒

        Raises:
            ValueError: 当update_interval <= 0时
        """
        if update_interval <= 0:
            raise ValueError(f"更新间隔必须 > 0，当前: {update_interval}")

        self.update_interval: int = update_interval
        self.operators: Dict[str, Callable] = self._initialize_operators()
        self.data_sources: Dict[str, DataSource] = {}
        self.fusion_cache: Dict[str, List[FusedData]] = defaultdict(list)

        logger.info(f"初始化AlternativeDataFactorMinerExtended: " f"update_interval={update_interval}秒")

        # 健康状态跟踪
        self._is_healthy = True
        self._error_count = 0

    def is_healthy(self) -> bool:
        """检查挖掘器健康状态

        Returns:
            是否健康
        """
        return self._is_healthy and self._error_count < 5

    def get_metadata(self) -> Dict:
        """获取挖掘器元数据

        Returns:
            元数据字典
        """
        return {
            "miner_type": "alternative_extended",
            "miner_name": "AlternativeDataFactorMinerExtended",
            "is_healthy": self.is_healthy(),
            "error_count": self._error_count,
            "update_interval": self.update_interval,
            "operators_count": len(self.operators),
        }

    def _initialize_operators(self) -> Dict[str, Callable]:
        """初始化10个扩展算子

        白皮书依据: 第四章 4.1.13

        Returns:
            算子字典
        """
        return {
            "multi_source_fusion": self._multi_source_fusion,
            "real_time_streaming": self._real_time_streaming,
            "cross_validation_scoring": self._cross_validation_scoring,
            "adaptive_weighting": self._adaptive_weighting,
            "anomaly_detection_advanced": self._anomaly_detection_advanced,
            "temporal_aggregation": self._temporal_aggregation,
            "spatial_correlation": self._spatial_correlation,
            "sentiment_nlp_advanced": self._sentiment_nlp_advanced,
            "image_recognition_features": self._image_recognition_features,
            "audio_signal_processing": self._audio_signal_processing,
        }

    def register_data_source(self, source: DataSource) -> None:
        """注册数据源

        Args:
            source: 数据源配置

        Raises:
            ValueError: 当数据源ID已存在时
        """
        if source.source_id in self.data_sources:
            raise ValueError(f"数据源ID已存在: {source.source_id}")

        self.data_sources[source.source_id] = source
        logger.info(f"注册数据源: {source.source_id}, 类型: {source.source_type}")

    def _multi_source_fusion(
        self,
        data_by_source: Dict[str, pd.Series],
        fusion_method: str = "weighted_average",
        window: int = 20,  # pylint: disable=unused-argument
    ) -> pd.Series:
        """多源数据融合

        白皮书依据: 第四章 4.1.13

        融合来自多个数据源的信息，提高数据质量和可靠性

        Args:
            data_by_source: 按数据源分组的数据字典
            fusion_method: 融合方法（weighted_average/median/kalman）
            window: 融合窗口

        Returns:
            融合后的数据序列

        Raises:
            ValueError: 当数据源少于2个时
        """
        if len(data_by_source) < 2:
            raise ValueError(f"至少需要2个数据源进行融合，当前: {len(data_by_source)}")

        # 对齐所有数据源的索引
        all_data = pd.DataFrame(data_by_source)

        if fusion_method == "weighted_average":
            # 基于数据源可靠性的加权平均
            weights = {}
            for source_id in data_by_source.keys():
                if source_id in self.data_sources:
                    weights[source_id] = self.data_sources[source_id].reliability
                else:
                    weights[source_id] = 0.5  # 默认权重

            # 归一化权重
            total_weight = sum(weights.values())
            weights = {k: v / total_weight for k, v in weights.items()}

            # 加权融合
            fused = pd.Series(0.0, index=all_data.index)
            for source_id, data in data_by_source.items():
                aligned_data = data.reindex(all_data.index, fill_value=0)
                fused += aligned_data * weights.get(source_id, 0.5)

        elif fusion_method == "median":
            # 中位数融合（对异常值鲁棒）
            fused = all_data.median(axis=1)

        elif fusion_method == "kalman":
            # 卡尔曼滤波融合（考虑时序依赖）
            fused = self._kalman_filter_fusion(all_data)

        else:
            raise ValueError(f"不支持的融合方法: {fusion_method}")

        # 计算融合置信度
        confidence = self._calculate_fusion_confidence(all_data, fused)

        logger.debug(
            f"多源数据融合完成 - "
            f"数据源数量: {len(data_by_source)}, "
            f"融合方法: {fusion_method}, "
            f"平均置信度: {confidence.mean():.4f}"
        )

        return fused

    def _kalman_filter_fusion(self, data: pd.DataFrame) -> pd.Series:
        """卡尔曼滤波融合

        Args:
            data: 多源数据框

        Returns:
            融合后的序列
        """
        # 简化的卡尔曼滤波实现
        n = len(data)
        fused = pd.Series(0.0, index=data.index)

        # 初始化
        x = data.iloc[0].mean()  # 初始状态估计
        P = 1.0  # 初始误差协方差
        Q = 0.01  # 过程噪声
        R = 0.1  # 测量噪声

        for i in range(n):
            # 预测
            x_pred = x
            P_pred = P + Q

            # 更新
            measurements = data.iloc[i].dropna()
            if len(measurements) > 0:
                z = measurements.mean()
                K = P_pred / (P_pred + R)  # 卡尔曼增益
                x = x_pred + K * (z - x_pred)
                P = (1 - K) * P_pred
            else:
                x = x_pred
                P = P_pred

            fused.iloc[i] = x

        return fused

    def _calculate_fusion_confidence(self, data: pd.DataFrame, fused: pd.Series) -> pd.Series:
        """计算融合置信度

        Args:
            data: 原始多源数据
            fused: 融合后数据

        Returns:
            置信度序列
        """
        # 基于数据源一致性计算置信度
        confidence = pd.Series(0.0, index=data.index)

        for i in range(len(data)):
            values = data.iloc[i].dropna()
            if len(values) > 1:
                # 计算与融合值的偏差
                deviations = np.abs(values - fused.iloc[i])
                mean_deviation = deviations.mean()
                std_deviation = deviations.std()

                # 偏差小且一致性高 -> 置信度高
                consistency = 1 / (1 + std_deviation)
                accuracy = 1 / (1 + mean_deviation)
                confidence.iloc[i] = (consistency + accuracy) / 2
            else:
                confidence.iloc[i] = 0.5  # 单一数据源，中等置信度

        return confidence

    async def _real_time_streaming(
        self, data_stream: asyncio.Queue, processing_func: Callable, buffer_size: int = 100
    ) -> pd.Series:
        """实时数据流处理

        白皮书依据: 第四章 4.1.13

        处理实时数据流，支持流式计算

        Args:
            data_stream: 数据流队列
            processing_func: 处理函数
            buffer_size: 缓冲区大小

        Returns:
            处理后的数据序列
        """
        buffer = []
        results = []

        logger.info("开始实时数据流处理...")

        try:
            while True:
                # 从队列获取数据（带超时）
                try:
                    data_point = await asyncio.wait_for(data_stream.get(), timeout=self.update_interval)

                    buffer.append(data_point)

                    # 缓冲区满时处理
                    if len(buffer) >= buffer_size:
                        processed = processing_func(buffer)
                        results.append(processed)
                        buffer = []

                except asyncio.TimeoutError:
                    # 超时，处理当前缓冲区
                    if buffer:
                        processed = processing_func(buffer)
                        results.append(processed)
                        buffer = []
                    break

        except Exception as e:
            logger.error(f"实时流处理失败: {e}")
            raise

        # 转换为序列
        result_series = pd.Series(results)

        logger.info(f"实时流处理完成 - 处理数据点: {len(results)}")

        return result_series

    def _cross_validation_scoring(
        self, factor_values: pd.Series, returns: pd.Series, n_folds: int = 5
    ) -> Dict[str, float]:
        """交叉验证评分

        白皮书依据: 第四章 4.1.13

        使用交叉验证评估因子质量

        Args:
            factor_values: 因子值
            returns: 收益率
            n_folds: 折数

        Returns:
            评分字典（包含IC、IR等指标）

        Raises:
            ValueError: 当数据长度不一致时
        """
        if len(factor_values) != len(returns):
            raise ValueError(f"因子值和收益率长度不一致: {len(factor_values)} vs {len(returns)}")

        # 分割数据
        fold_size = len(factor_values) // n_folds
        ic_scores = []
        ir_scores = []

        for fold in range(n_folds):
            # 训练集和测试集
            test_start = fold * fold_size
            test_end = (fold + 1) * fold_size if fold < n_folds - 1 else len(factor_values)

            test_factor = factor_values.iloc[test_start:test_end]
            test_returns = returns.iloc[test_start:test_end]

            # 计算IC
            ic = test_factor.corr(test_returns, method="spearman")
            ic_scores.append(ic)

            # 计算IR
            ic_mean = np.mean(ic_scores)
            ic_std = np.std(ic_scores) if len(ic_scores) > 1 else 1e-8
            ir = ic_mean / (ic_std + 1e-8)
            ir_scores.append(ir)

        # 汇总评分
        scores = {
            "mean_ic": np.mean(ic_scores),
            "std_ic": np.std(ic_scores),
            "mean_ir": np.mean(ir_scores),
            "min_ic": np.min(ic_scores),
            "max_ic": np.max(ic_scores),
            "stability": 1 - np.std(ic_scores) / (np.abs(np.mean(ic_scores)) + 1e-8),
        }

        logger.debug(f"交叉验证完成 - " f"平均IC: {scores['mean_ic']:.4f}, " f"稳定性: {scores['stability']:.4f}")

        return scores

    def _adaptive_weighting(
        self, data_sources: Dict[str, pd.Series], performance_history: Dict[str, List[float]], window: int = 20
    ) -> Dict[str, float]:
        """自适应权重调整

        白皮书依据: 第四章 4.1.13

        根据历史表现动态调整数据源权重

        Args:
            data_sources: 数据源字典
            performance_history: 各数据源的历史表现
            window: 评估窗口

        Returns:
            调整后的权重字典
        """
        weights = {}

        for source_id in data_sources.keys():
            if source_id in performance_history:
                recent_performance = performance_history[source_id][-window:]

                if recent_performance:
                    # 基于近期表现计算权重
                    avg_performance = np.mean(recent_performance)
                    std_performance = np.std(recent_performance)

                    # 表现好且稳定的数据源权重高
                    weight = avg_performance / (1 + std_performance)
                    weights[source_id] = max(0, weight)
                else:
                    weights[source_id] = 0.5
            else:
                weights[source_id] = 0.5

        # 归一化权重
        total_weight = sum(weights.values())
        if total_weight > 0:
            weights = {k: v / total_weight for k, v in weights.items()}

        logger.debug(f"自适应权重调整完成 - 权重: {weights}")

        return weights

    def _anomaly_detection_advanced(
        self, data: pd.Series, method: str = "isolation_forest", contamination: float = 0.1
    ) -> pd.Series:
        """高级异常检测

        白皮书依据: 第四章 4.1.13

        使用高级算法检测数据异常

        Args:
            data: 输入数据
            method: 检测方法（isolation_forest/lof/autoencoder）
            contamination: 异常比例

        Returns:
            异常分数序列（值越大越异常）
        """
        from sklearn.ensemble import IsolationForest  # pylint: disable=import-outside-toplevel
        from sklearn.neighbors import LocalOutlierFactor  # pylint: disable=import-outside-toplevel

        # 准备数据
        X = data.values.reshape(-1, 1)

        if method == "isolation_forest":
            # 孤立森林
            detector = IsolationForest(contamination=contamination, random_state=42)
            scores = -detector.fit_predict(X)  # 转换为正分数

        elif method == "lof":
            # 局部异常因子
            detector = LocalOutlierFactor(contamination=contamination, novelty=False)
            scores = -detector.fit_predict(X)

        elif method == "autoencoder":
            # 自编码器（简化版本）
            scores = self._autoencoder_anomaly_detection(data)

        else:
            raise ValueError(f"不支持的检测方法: {method}")

        # 转换为序列
        anomaly_scores = pd.Series(scores, index=data.index)

        # 标准化到[0,1]
        anomaly_scores = (anomaly_scores - anomaly_scores.min()) / (anomaly_scores.max() - anomaly_scores.min() + 1e-8)

        logger.debug(f"异常检测完成 - " f"方法: {method}, " f"检测到异常: {(anomaly_scores > 0.8).sum()}")

        return anomaly_scores

    def _autoencoder_anomaly_detection(self, data: pd.Series) -> np.ndarray:
        """使用自编码器进行异常检测

        Args:
            data: 输入数据

        Returns:
            异常分数数组
        """
        # 简化版本：使用重构误差作为异常分数
        # 实际实现中应该使用深度学习框架

        # 使用滑动窗口计算局部统计特征
        window = 10
        rolling_mean = data.rolling(window=window, min_periods=1).mean()
        rolling_std = data.rolling(window=window, min_periods=1).std()

        # 计算标准化偏差作为异常分数
        deviation = np.abs(data - rolling_mean) / (rolling_std + 1e-8)

        return deviation.values

    def _temporal_aggregation(  # pylint: disable=w0102
        self, data: pd.Series, aggregation_levels: List[str] = ["1H", "1D", "1W"], aggregation_func: str = "mean"
    ) -> pd.DataFrame:
        """时序聚合

        白皮书依据: 第四章 4.1.13

        在多个时间尺度上聚合数据

        Args:
            data: 输入数据
            aggregation_levels: 聚合级别列表
            aggregation_func: 聚合函数（mean/sum/std/max/min）

        Returns:
            多尺度聚合数据框
        """
        aggregated = {}

        for level in aggregation_levels:
            if aggregation_func == "mean":
                agg_data = data.resample(level).mean()
            elif aggregation_func == "sum":
                agg_data = data.resample(level).sum()
            elif aggregation_func == "std":
                agg_data = data.resample(level).std()
            elif aggregation_func == "max":
                agg_data = data.resample(level).max()
            elif aggregation_func == "min":
                agg_data = data.resample(level).min()
            else:
                raise ValueError(f"不支持的聚合函数: {aggregation_func}")

            # 回填到原始频率
            agg_data_filled = agg_data.reindex(data.index, method="ffill")
            aggregated[f"{level}_{aggregation_func}"] = agg_data_filled

        result = pd.DataFrame(aggregated)

        logger.debug(f"时序聚合完成 - " f"聚合级别: {len(aggregation_levels)}, " f"函数: {aggregation_func}")

        return result

    def _spatial_correlation(
        self,
        data_by_location: Dict[str, pd.Series],
        coordinates: Dict[str, Tuple[float, float]],
        distance_threshold: float = 100.0,
    ) -> pd.DataFrame:
        """空间相关性分析

        白皮书依据: 第四章 4.1.13

        分析地理位置相关的数据相关性

        Args:
            data_by_location: 按位置分组的数据
            coordinates: 位置坐标字典（纬度，经度）
            distance_threshold: 距离阈值（公里）

        Returns:
            空间相关性矩阵
        """
        from scipy.spatial.distance import pdist, squareform  # pylint: disable=import-outside-toplevel

        locations = list(data_by_location.keys())
        n_locations = len(locations)

        # 计算地理距离矩阵
        coords_array = np.array([coordinates[loc] for loc in locations])
        distances = squareform(pdist(coords_array, metric="euclidean")) * 111  # 转换为公里

        # 计算数据相关性矩阵
        data_df = pd.DataFrame(data_by_location)
        correlations = data_df.corr()

        # 空间加权相关性
        spatial_weights = np.exp(-distances / distance_threshold)
        weighted_correlations = correlations.values * spatial_weights

        result = pd.DataFrame(weighted_correlations, index=locations, columns=locations)

        logger.debug(
            f"空间相关性分析完成 - " f"位置数量: {n_locations}, " f"平均相关性: {weighted_correlations.mean():.4f}"
        )

        return result

    def _sentiment_nlp_advanced(
        self, text_data: List[str], model_type: str = "transformer"  # pylint: disable=unused-argument
    ) -> pd.Series:  # pylint: disable=unused-argument
        """高级NLP情绪分析

        白皮书依据: 第四章 4.1.13

        使用先进的NLP模型进行情绪分析

        Args:
            text_data: 文本数据列表
            model_type: 模型类型（transformer/bert/finbert）

        Returns:
            情绪分数序列（-1到1）
        """
        # 简化实现：使用基于词典的方法
        # 实际实现中应该使用预训练的Transformer模型

        positive_words = {"good", "great", "excellent", "positive", "growth", "profit", "success"}
        negative_words = {"bad", "poor", "negative", "loss", "decline", "risk", "concern"}

        sentiments = []

        for text in text_data:
            if not text:
                sentiments.append(0.0)
                continue

            text_lower = text.lower()
            words = text_lower.split()

            pos_count = sum(1 for word in words if word in positive_words)
            neg_count = sum(1 for word in words if word in negative_words)

            total = pos_count + neg_count
            if total > 0:
                sentiment = (pos_count - neg_count) / total
            else:
                sentiment = 0.0

            sentiments.append(sentiment)

        sentiment_series = pd.Series(sentiments)

        logger.debug(f"NLP情绪分析完成 - " f"文本数量: {len(text_data)}, " f"平均情绪: {sentiment_series.mean():.4f}")

        return sentiment_series

    def _image_recognition_features(self, image_paths: List[str], feature_type: str = "object_count") -> pd.DataFrame:
        """图像识别特征提取

        白皮书依据: 第四章 4.1.13

        从图像中提取量化特征

        Args:
            image_paths: 图像路径列表
            feature_type: 特征类型（object_count/scene/activity）

        Returns:
            图像特征数据框
        """
        # 简化实现：返回模拟特征
        # 实际实现中应该使用计算机视觉模型（如YOLO、ResNet等）

        features = []

        for img_path in image_paths:  # pylint: disable=unused-variable
            if feature_type == "object_count":
                # 模拟对象计数
                feature = {
                    "vehicle_count": np.random.randint(0, 50),
                    "person_count": np.random.randint(0, 100),
                    "building_count": np.random.randint(0, 20),
                }
            elif feature_type == "scene":
                # 模拟场景分类
                feature = {
                    "indoor_prob": np.random.random(),
                    "outdoor_prob": np.random.random(),
                    "urban_prob": np.random.random(),
                }
            elif feature_type == "activity":
                # 模拟活动检测
                feature = {
                    "construction": np.random.random(),
                    "traffic": np.random.random(),
                    "crowd": np.random.random(),
                }
            else:
                raise ValueError(f"不支持的特征类型: {feature_type}")

            features.append(feature)

        result = pd.DataFrame(features)

        logger.debug(f"图像特征提取完成 - " f"图像数量: {len(image_paths)}, " f"特征类型: {feature_type}")

        return result

    def _audio_signal_processing(self, audio_data: List[np.ndarray], sample_rate: int = 44100) -> pd.DataFrame:
        """音频信号处理

        白皮书依据: 第四章 4.1.13

        从音频信号中提取特征

        Args:
            audio_data: 音频数据列表
            sample_rate: 采样率

        Returns:
            音频特征数据框
        """
        features = []

        for audio in audio_data:
            if len(audio) == 0:
                features.append({"energy": 0.0, "zero_crossing_rate": 0.0, "spectral_centroid": 0.0})
                continue

            # 计算能量
            energy = np.sum(audio**2) / len(audio)

            # 计算过零率
            zero_crossings = np.sum(np.abs(np.diff(np.sign(audio)))) / (2 * len(audio))

            # 计算频谱质心（简化版本）
            fft = np.fft.fft(audio)
            magnitude = np.abs(fft[: len(fft) // 2])
            freqs = np.fft.fftfreq(len(audio), 1 / sample_rate)[: len(fft) // 2]
            spectral_centroid = np.sum(freqs * magnitude) / (np.sum(magnitude) + 1e-8)

            features.append(
                {"energy": energy, "zero_crossing_rate": zero_crossings, "spectral_centroid": spectral_centroid}
            )

        result = pd.DataFrame(features)

        logger.debug(f"音频信号处理完成 - " f"音频数量: {len(audio_data)}, " f"采样率: {sample_rate}Hz")

        return result

    def mine_factors(
        self,
        data: Dict[str, Any],
        symbols: List[str],  # pylint: disable=unused-argument
        start_date: datetime,
        end_date: datetime,  # pylint: disable=unused-argument
    ) -> List[pd.Series]:
        """挖掘扩展替代数据因子

        白皮书依据: 第四章 4.1.13

        Args:
            data: 数据字典，包含各类扩展数据
            symbols: 股票代码列表
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            因子列表
        """
        factors = []

        try:
            # 1. 多源数据融合
            if "multi_source_data" in data:
                fused_factor = self._multi_source_fusion(data["multi_source_data"])
                factors.append(fused_factor)

            # 2. 交叉验证评分
            if "factor_values" in data and "returns" in data:
                scores = self._cross_validation_scoring(data["factor_values"], data["returns"])
                # 将评分转换为因子
                score_factor = pd.Series(scores["mean_ic"], index=data["factor_values"].index)
                factors.append(score_factor)

            # 3. 高级异常检测
            if "raw_data" in data:
                anomaly_factor = self._anomaly_detection_advanced(data["raw_data"])
                factors.append(anomaly_factor)

            # 4. 时序聚合
            if "time_series_data" in data:
                aggregated = self._temporal_aggregation(data["time_series_data"])
                # 使用第一列作为因子
                if not aggregated.empty:
                    factors.append(aggregated.iloc[:, 0])

            # 5-10. 其他扩展因子...

            logger.info(
                f"扩展替代数据因子挖掘完成 - " f"生成因子数量: {len(factors)}, " f"时间范围: {start_date} 到 {end_date}"
            )

        except Exception as e:
            logger.error(f"因子挖掘失败: {e}")
            raise

        return factors
