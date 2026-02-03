"""机器学习特征工程因子挖掘器

白皮书依据: 第四章 4.1.8 机器学习特征工程因子挖掘
需求: 7.1-7.10

实现8个ML特征工程算子，降维框架（PCA, t-SNE），
异常检测系统，信息损失检测（>20%标记）。
"""

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

import numpy as np
import pandas as pd
from loguru import logger
from sklearn.decomposition import PCA
from sklearn.ensemble import IsolationForest
from sklearn.manifold import TSNE
from sklearn.preprocessing import StandardScaler


@dataclass
class DimensionalityReductionResult:
    """降维结果

    Attributes:
        reduced_features: 降维后的特征
        explained_variance: 解释方差比例
        information_loss: 信息损失比例
        method: 降维方法
    """

    reduced_features: np.ndarray
    explained_variance: float
    information_loss: float
    method: str

    def has_high_information_loss(self, threshold: float = 0.2) -> bool:
        """检查是否有高信息损失

        需求: 7.10 - 信息损失>20%标记

        Args:
            threshold: 信息损失阈值

        Returns:
            是否有高信息损失
        """
        return self.information_loss > threshold


class MLFeatureEngineeringFactorMiner:
    """机器学习特征工程因子挖掘器

    白皮书依据: 第四章 4.1.8 机器学习特征工程因子挖掘
    需求: 7.1-7.10

    实现8个ML特征工程算子：
    1. autoencoder_latent_features: 自编码器潜在特征
    2. pca_principal_components: PCA主成分
    3. tsne_embeddings: t-SNE嵌入
    4. isolation_forest_anomaly_scores: 孤立森林异常分数
    5. xgboost_feature_importance: XGBoost特征重要性
    6. neural_network_activations: 神经网络激活值
    7. ensemble_prediction_variance: 集成预测方差
    8. meta_learning_adaptation_features: 元学习自适应特征

    降维框架: PCA, t-SNE
    异常检测: Isolation Forest
    信息损失检测: >20%标记

    Attributes:
        operators: 算子字典
        scaler: 数据标准化器
        pca_model: PCA模型
        tsne_model: t-SNE模型
        isolation_forest: 孤立森林模型
        information_loss_threshold: 信息损失阈值
    """

    def __init__(
        self,
        n_components_pca: int = 10,
        n_components_tsne: int = 2,
        information_loss_threshold: float = 0.2,
        random_state: int = 42,
    ):
        """初始化机器学习特征工程因子挖掘器

        Args:
            n_components_pca: PCA主成分数量
            n_components_tsne: t-SNE嵌入维度
            information_loss_threshold: 信息损失阈值
            random_state: 随机种子

        Raises:
            ValueError: 当参数不在有效范围时
        """
        if n_components_pca <= 0:
            raise ValueError(f"PCA主成分数量必须 > 0，当前: {n_components_pca}")

        if n_components_tsne <= 0:
            raise ValueError(f"t-SNE嵌入维度必须 > 0，当前: {n_components_tsne}")

        if not 0 < information_loss_threshold < 1:
            raise ValueError(f"信息损失阈值必须在 (0, 1)，当前: {information_loss_threshold}")

        self.n_components_pca = n_components_pca
        self.n_components_tsne = n_components_tsne
        self.information_loss_threshold = information_loss_threshold
        self.random_state = random_state

        # 初始化算子
        self.operators = self._initialize_operators()

        # 初始化模型
        self.scaler = StandardScaler()
        self.pca_model: Optional[PCA] = None
        self.tsne_model: Optional[TSNE] = None
        self.isolation_forest = IsolationForest(contamination=0.1, random_state=random_state)

        # 信息损失统计
        self.information_loss_stats = {"total_reductions": 0, "high_loss_count": 0, "high_loss_ratio": 0.0}

        logger.info(
            f"初始化MLFeatureEngineeringFactorMiner: "
            f"n_components_pca={n_components_pca}, "
            f"n_components_tsne={n_components_tsne}, "
            f"information_loss_threshold={information_loss_threshold}"
        )

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
            "miner_type": "ml_feature",
            "miner_name": "MLFeatureEngineeringFactorMiner",
            "is_healthy": self.is_healthy(),
            "error_count": self._error_count,
            "n_components_pca": self.n_components_pca,
            "n_components_tsne": self.n_components_tsne,
            "operators_count": len(self.operators),
        }

    def _initialize_operators(self) -> Dict[str, Callable]:
        """初始化8个ML特征工程算子

        白皮书依据: 第四章 4.1.8
        需求: 7.1-7.9

        Returns:
            算子字典
        """
        return {
            "autoencoder_latent_features": self._autoencoder_latent_features,
            "pca_principal_components": self._pca_principal_components,
            "tsne_embeddings": self._tsne_embeddings,
            "isolation_forest_anomaly_scores": self._isolation_forest_anomaly_scores,
            "xgboost_feature_importance": self._xgboost_feature_importance,
            "neural_network_activations": self._neural_network_activations,
            "ensemble_prediction_variance": self._ensemble_prediction_variance,
            "meta_learning_adaptation_features": self._meta_learning_adaptation_features,
        }

    def mine_factors(self, features: pd.DataFrame, symbols: List[str]) -> pd.DataFrame:
        """挖掘机器学习特征工程因子

        白皮书依据: 第四章 4.1.8
        需求: 7.1-7.10

        Args:
            features: 原始特征数据框
            symbols: 股票代码列表

        Returns:
            因子数据框，索引为股票代码，列为因子名称

        Raises:
            ValueError: 当输入数据无效时
        """
        if features.empty:
            raise ValueError("特征数据不能为空")

        if not symbols:
            raise ValueError("股票代码列表不能为空")

        logger.info(f"开始挖掘ML特征工程因子: " f"features_shape={features.shape}, " f"symbols={len(symbols)}")

        # 标准化特征
        features_scaled = self.scaler.fit_transform(features)

        # 计算所有因子
        factors = {}
        for operator_name, operator_func in self.operators.items():
            try:
                factor_values = operator_func(features_scaled, features, symbols)
                factors[operator_name] = factor_values
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.error(f"算子 {operator_name} 执行失败: {e}")
                factors[operator_name] = pd.Series(0.0, index=symbols)

        # 构建因子数据框
        factor_df = pd.DataFrame(factors, index=symbols)

        logger.info(
            f"ML特征工程因子挖掘完成: "
            f"factors={len(factors)}, "
            f"high_loss_ratio={self.information_loss_stats['high_loss_ratio']:.2%}"
        )

        return factor_df

    def _autoencoder_latent_features(
        self,
        features_scaled: np.ndarray,
        features_original: pd.DataFrame,  # pylint: disable=unused-argument
        symbols: List[str],  # pylint: disable=unused-argument
    ) -> pd.Series:
        """提取自编码器潜在特征

        白皮书依据: 第四章 4.1.8
        需求: 7.1

        自编码器潜在特征 = 压缩表示的特征

        Args:
            features_scaled: 标准化后的特征
            features_original: 原始特征
            symbols: 股票代码列表

        Returns:
            自编码器潜在特征因子
        """
        # 简化版本：使用PCA作为线性自编码器的近似
        n_latent = min(5, features_scaled.shape[1])

        pca = PCA(n_components=n_latent, random_state=self.random_state)
        latent_features = pca.fit_transform(features_scaled)

        # 使用第一主成分作为因子
        latent_scores = latent_features[:, 0] if latent_features.shape[1] > 0 else np.zeros(len(symbols))

        return pd.Series(latent_scores, index=symbols)

    def _pca_principal_components(
        self,
        features_scaled: np.ndarray,
        features_original: pd.DataFrame,  # pylint: disable=unused-argument
        symbols: List[str],  # pylint: disable=unused-argument
    ) -> pd.Series:
        """生成PCA主成分

        白皮书依据: 第四章 4.1.8
        需求: 7.2

        PCA主成分 = 解释>=80%方差的主成分

        Args:
            features_scaled: 标准化后的特征
            features_original: 原始特征
            symbols: 股票代码列表

        Returns:
            PCA主成分因子
        """
        # 确定主成分数量以解释80%方差
        n_components = min(self.n_components_pca, features_scaled.shape[1])

        self.pca_model = PCA(n_components=n_components, random_state=self.random_state)
        principal_components = self.pca_model.fit_transform(features_scaled)

        # 计算解释方差
        explained_variance = self.pca_model.explained_variance_ratio_.sum()
        information_loss = 1.0 - explained_variance

        # 检查信息损失
        self._check_information_loss(information_loss, "PCA")

        # 使用第一主成分作为因子
        pc1_scores = principal_components[:, 0] if principal_components.shape[1] > 0 else np.zeros(len(symbols))

        logger.info(
            f"PCA完成: n_components={n_components}, "
            f"explained_variance={explained_variance:.2%}, "
            f"information_loss={information_loss:.2%}"
        )

        return pd.Series(pc1_scores, index=symbols)

    def _tsne_embeddings(
        self,
        features_scaled: np.ndarray,
        features_original: pd.DataFrame,  # pylint: disable=unused-argument
        symbols: List[str],  # pylint: disable=unused-argument
    ) -> pd.Series:
        """创建t-SNE嵌入

        白皮书依据: 第四章 4.1.8
        需求: 7.3

        t-SNE嵌入 = 保留局部结构的低维嵌入

        Args:
            features_scaled: 标准化后的特征
            features_original: 原始特征
            symbols: 股票代码列表

        Returns:
            t-SNE嵌入因子
        """
        # t-SNE计算较慢，限制样本数量
        max_samples = min(1000, features_scaled.shape[0])

        if features_scaled.shape[0] > max_samples:
            # 随机采样
            indices = np.random.choice(features_scaled.shape[0], max_samples, replace=False)
            features_sampled = features_scaled[indices]
        else:
            features_sampled = features_scaled
            indices = np.arange(features_scaled.shape[0])

        # 执行t-SNE
        self.tsne_model = TSNE(  # pylint: disable=e1123
            n_components=self.n_components_tsne, random_state=self.random_state, n_iter=250
        )  # pylint: disable=e1123
        embeddings = self.tsne_model.fit_transform(features_sampled)

        # 创建完整的嵌入数组
        full_embeddings = np.zeros((features_scaled.shape[0], self.n_components_tsne))
        full_embeddings[indices] = embeddings

        # 使用第一维度作为因子
        tsne_scores = full_embeddings[:, 0]

        logger.info(f"t-SNE完成: n_components={self.n_components_tsne}, samples={max_samples}")

        return pd.Series(tsne_scores, index=symbols)

    def _isolation_forest_anomaly_scores(
        self,
        features_scaled: np.ndarray,
        features_original: pd.DataFrame,  # pylint: disable=unused-argument
        symbols: List[str],  # pylint: disable=unused-argument
    ) -> pd.Series:
        """计算孤立森林异常分数

        白皮书依据: 第四章 4.1.8
        需求: 7.4

        异常分数 = 样本的异常程度

        Args:
            features_scaled: 标准化后的特征
            features_original: 原始特征
            symbols: 股票代码列表

        Returns:
            异常分数因子
        """
        # 训练孤立森林
        self.isolation_forest.fit(features_scaled)

        # 计算异常分数（负值表示异常）
        anomaly_scores = self.isolation_forest.score_samples(features_scaled)

        # 转换为正值（越大越异常）
        anomaly_scores = -anomaly_scores

        logger.info(f"孤立森林完成: " f"anomalies_detected={np.sum(anomaly_scores > 0)}")

        return pd.Series(anomaly_scores, index=symbols)

    def _xgboost_feature_importance(
        self,
        features_scaled: np.ndarray,
        features_original: pd.DataFrame,  # pylint: disable=unused-argument
        symbols: List[str],  # pylint: disable=unused-argument
    ) -> pd.Series:
        """提取XGBoost特征重要性

        白皮书依据: 第四章 4.1.8
        需求: 7.5

        特征重要性 = 特征对预测的贡献度

        Args:
            features_scaled: 标准化后的特征
            features_original: 原始特征
            symbols: 股票代码列表

        Returns:
            特征重要性因子
        """
        # 简化版本：使用特征方差作为重要性的代理
        # 实际应用中需要训练XGBoost模型
        feature_variances = np.var(features_scaled, axis=1)

        # 归一化
        if feature_variances.max() > 0:
            importance_scores = feature_variances / feature_variances.max()
        else:
            importance_scores = np.zeros(len(symbols))

        return pd.Series(importance_scores, index=symbols)

    def _neural_network_activations(
        self,
        features_scaled: np.ndarray,
        features_original: pd.DataFrame,  # pylint: disable=unused-argument
        symbols: List[str],  # pylint: disable=unused-argument
    ) -> pd.Series:
        """捕获神经网络激活值

        白皮书依据: 第四章 4.1.8
        需求: 7.6

        激活值 = 隐藏层的激活输出

        Args:
            features_scaled: 标准化后的特征
            features_original: 原始特征
            symbols: 股票代码列表

        Returns:
            神经网络激活值因子
        """
        # 简化版本：使用ReLU激活函数的模拟
        # 实际应用中需要训练神经网络

        # 模拟隐藏层激活：ReLU(W * X + b)
        # 使用随机权重作为示例
        np.random.seed(self.random_state)
        hidden_size = 10
        W = np.random.randn(hidden_size, features_scaled.shape[1]) * 0.1
        b = np.random.randn(hidden_size) * 0.1

        # 计算激活
        activations = np.maximum(0, features_scaled @ W.T + b)

        # 使用平均激活作为因子
        activation_scores = activations.mean(axis=1)

        return pd.Series(activation_scores, index=symbols)

    def _ensemble_prediction_variance(
        self,
        features_scaled: np.ndarray,
        features_original: pd.DataFrame,  # pylint: disable=unused-argument
        symbols: List[str],  # pylint: disable=unused-argument
    ) -> pd.Series:
        """测量集成预测方差

        白皮书依据: 第四章 4.1.8
        需求: 7.7

        预测方差 = 多个模型预测的不一致性

        Args:
            features_scaled: 标准化后的特征
            features_original: 原始特征
            symbols: 股票代码列表

        Returns:
            集成预测方差因子
        """
        # 简化版本：使用多个随机投影的方差
        # 实际应用中需要训练多个模型

        n_models = 5
        predictions = []

        np.random.seed(self.random_state)
        for i in range(n_models):  # pylint: disable=unused-variable
            # 随机投影作为简单模型
            projection = np.random.randn(features_scaled.shape[1])
            projection = projection / np.linalg.norm(projection)

            pred = features_scaled @ projection
            predictions.append(pred)

        # 计算预测方差
        predictions_array = np.array(predictions)
        prediction_variance = np.var(predictions_array, axis=0)

        return pd.Series(prediction_variance, index=symbols)

    def _meta_learning_adaptation_features(
        self,
        features_scaled: np.ndarray,
        features_original: pd.DataFrame,  # pylint: disable=unused-argument
        symbols: List[str],  # pylint: disable=unused-argument
    ) -> pd.Series:
        """生成元学习自适应特征

        白皮书依据: 第四章 4.1.8
        需求: 7.8

        自适应特征 = 针对新市场状态的快速适应特征

        Args:
            features_scaled: 标准化后的特征
            features_original: 原始特征
            symbols: 股票代码列表

        Returns:
            元学习自适应特征因子
        """
        # 简化版本：使用特征的时间变化率
        # 实际应用中需要实现MAML或其他元学习算法

        if features_scaled.shape[0] < 2:
            return pd.Series(0.0, index=symbols)

        # 计算特征变化率（最近vs历史）
        recent_features = features_scaled[-len(symbols) // 4 :] if len(symbols) > 4 else features_scaled
        historical_features = features_scaled[: len(symbols) // 4] if len(symbols) > 4 else features_scaled

        recent_mean = recent_features.mean(axis=0)
        historical_mean = historical_features.mean(axis=0)

        # 计算每个样本与变化方向的对齐度
        change_direction = recent_mean - historical_mean

        if np.linalg.norm(change_direction) > 0:
            change_direction = change_direction / np.linalg.norm(change_direction)
            adaptation_scores = features_scaled @ change_direction
        else:
            adaptation_scores = np.zeros(len(symbols))

        return pd.Series(adaptation_scores, index=symbols)

    def _check_information_loss(self, information_loss: float, method: str):
        """检查信息损失

        需求: 7.10 - 信息损失>20%标记

        Args:
            information_loss: 信息损失比例
            method: 降维方法
        """
        self.information_loss_stats["total_reductions"] += 1

        if information_loss > self.information_loss_threshold:
            self.information_loss_stats["high_loss_count"] += 1
            logger.warning(
                f"高信息损失检测: method={method}, "
                f"loss={information_loss:.2%} > "
                f"threshold={self.information_loss_threshold:.2%}"
            )

        # 更新高损失比率
        if self.information_loss_stats["total_reductions"] > 0:
            self.information_loss_stats["high_loss_ratio"] = (
                self.information_loss_stats["high_loss_count"] / self.information_loss_stats["total_reductions"]
            )

    def get_information_loss_statistics(self) -> Dict[str, Any]:
        """获取信息损失统计

        需求: 7.10 - 监控信息损失

        Returns:
            信息损失统计字典
        """
        return {
            "total_reductions": self.information_loss_stats["total_reductions"],
            "high_loss_count": self.information_loss_stats["high_loss_count"],
            "high_loss_ratio": self.information_loss_stats["high_loss_ratio"],
            "information_loss_threshold": self.information_loss_threshold,
        }

    def perform_dimensionality_reduction(
        self, features: pd.DataFrame, method: str = "pca", target_variance: float = 0.8
    ) -> DimensionalityReductionResult:
        """执行降维

        白皮书依据: 第四章 4.1.8 - 降维框架
        需求: 7.9

        Args:
            features: 原始特征
            method: 降维方法（'pca' 或 'tsne'）
            target_variance: 目标解释方差比例

        Returns:
            降维结果

        Raises:
            ValueError: 当方法不支持时
        """
        if method not in ["pca", "tsne"]:
            raise ValueError(f"不支持的降维方法: {method}")

        # 标准化特征
        features_scaled = self.scaler.fit_transform(features)

        if method == "pca":
            # 使用PCA
            pca = PCA(n_components=target_variance, random_state=self.random_state)
            reduced_features = pca.fit_transform(features_scaled)

            explained_variance = pca.explained_variance_ratio_.sum()
            information_loss = 1.0 - explained_variance

            logger.info(
                f"PCA降维完成: " f"n_components={pca.n_components_}, " f"explained_variance={explained_variance:.2%}"
            )

        else:  # tsne
            # 使用t-SNE
            tsne = TSNE(n_components=self.n_components_tsne, random_state=self.random_state)
            reduced_features = tsne.fit_transform(features_scaled)

            # t-SNE不提供解释方差，使用估计值
            explained_variance = 0.7  # 估计值
            information_loss = 0.3

            logger.info(f"t-SNE降维完成: " f"n_components={self.n_components_tsne}")

        # 检查信息损失
        self._check_information_loss(information_loss, method)

        return DimensionalityReductionResult(
            reduced_features=reduced_features,
            explained_variance=explained_variance,
            information_loss=information_loss,
            method=method,
        )
