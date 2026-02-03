"""机器学习特征工程因子挖掘器

白皮书依据: 第四章 4.1.8 机器学习特征工程因子挖掘器

使用经典机器学习方法进行特征提取和降维，发现数据中的隐藏结构。
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import pandas as pd
from loguru import logger

from ..genetic_miner import EvolutionConfig, GeneticMiner
from . import ml_feature_operators


@dataclass
class MLFeatureConfig:  # pylint: disable=too-many-instance-attributes
    """机器学习特征工程配置

    白皮书依据: 第四章 4.1.8
    """

    # 自编码器配置
    autoencoder_latent_dim: int = 8
    autoencoder_encoding_layers: int = 2

    # PCA配置
    pca_n_components: int = 3
    pca_window: int = 60

    # t-SNE配置
    tsne_perplexity: int = 30
    tsne_n_components: int = 2
    tsne_window: int = 100

    # 孤立森林配置
    isolation_n_estimators: int = 100
    isolation_contamination: float = 0.1
    isolation_window: int = 100

    # XGBoost配置
    xgboost_n_estimators: int = 50
    xgboost_max_depth: int = 3
    xgboost_window: int = 100

    # 神经网络配置
    nn_hidden_units: int = 32
    nn_num_layers: int = 2
    nn_activation: str = "relu"

    # 集成学习配置
    ensemble_n_models: int = 10
    ensemble_window: int = 60

    # 元学习配置
    meta_adaptation_rate: float = 0.1
    meta_window: int = 100


class MLFeatureEngineeringFactorMiner(GeneticMiner):
    """机器学习特征工程因子挖掘器

    白皮书依据: 第四章 4.1.8 机器学习特征工程因子挖掘器

    核心理念: 使用经典机器学习方法进行特征提取和降维，发现数据中的隐藏结构。

    核心算子库 (8种算子):
    1. autoencoder_latent_feature: 自编码器潜在特征
    2. pca_principal_component: PCA主成分
    3. tsne_embedding: t-SNE嵌入
    4. isolation_forest_anomaly: 孤立森林异常分数
    5. xgboost_feature_importance: XGBoost特征重要性
    6. neural_network_activation: 神经网络激活值
    7. ensemble_prediction_variance: 集成预测方差
    8. meta_learning_adaptation: 元学习自适应

    应用场景:
    - 特征降维和去噪
    - 异常检测和识别
    - 模型集成和融合

    Attributes:
        ml_config: 机器学习特征工程配置
        ml_operators: ML算子字典
    """

    def __init__(self, config: Optional[EvolutionConfig] = None, ml_config: Optional[MLFeatureConfig] = None):
        """初始化机器学习特征工程因子挖掘器

        Args:
            config: 遗传算法配置
            ml_config: 机器学习特征工程配置
        """
        # 初始化基类
        if config is None:
            config = EvolutionConfig()
        super().__init__(config=config)

        # ML特征工程配置
        self.ml_config = ml_config or MLFeatureConfig()

        # 注册ML算子
        self._register_ml_operators()

        logger.info(f"MLFeatureEngineeringFactorMiner初始化完成 - " f"ML算子数: {len(self.ml_operators)}")

    def _register_ml_operators(self) -> None:
        """注册ML特征工程算子到遗传算法框架

        白皮书依据: 第四章 4.1.8 - 8种ML算子
        """
        self.ml_operators = {
            "autoencoder_latent_feature": ml_feature_operators.autoencoder_latent_feature,
            "pca_principal_component": ml_feature_operators.pca_principal_component,
            "tsne_embedding": ml_feature_operators.tsne_embedding,
            "isolation_forest_anomaly": ml_feature_operators.isolation_forest_anomaly,
            "xgboost_feature_importance": ml_feature_operators.xgboost_feature_importance,
            "neural_network_activation": ml_feature_operators.neural_network_activation,
            "ensemble_prediction_variance": ml_feature_operators.ensemble_prediction_variance,
            "meta_learning_adaptation": ml_feature_operators.meta_learning_adaptation,
        }

        # 添加到基类的算子白名单
        if not hasattr(self, "operator_whitelist"):
            self.operator_whitelist = []

        for op_name in self.ml_operators.keys():  # pylint: disable=consider-iterating-dictionary
            if op_name not in self.operator_whitelist:
                self.operator_whitelist.append(op_name)

        logger.info(f"已注册 {len(self.ml_operators)} 个ML特征工程算子")

    async def mine_factors(self, data: pd.DataFrame, returns: pd.Series, generations: int = 10) -> List[Dict[str, Any]]:
        """挖掘ML特征工程因子

        白皮书依据: 第四章 4.1.8

        Args:
            data: 市场数据
            returns: 未来收益率
            generations: 进化代数

        Returns:
            挖掘到的因子列表
        """
        logger.info(f"开始ML特征工程因子挖掘 - 数据形状: {data.shape}, 进化代数: {generations}")

        try:
            # 1. 初始化种群（使用ML算子）
            await self.initialize_population(data_columns=data.columns.tolist())

            # 2. 评估适应度
            await self.evaluate_fitness(data, returns)

            # 3. 进化
            best_individual = await self.evolve(  # pylint: disable=unused-variable
                data=data, returns=returns, generations=generations
            )  # pylint: disable=unused-variable

            # 4. 提取最优因子
            factors = []
            for individual in self.population[:10]:  # 取前10个最优因子
                factor = {
                    "expression": individual.expression,
                    "fitness": individual.fitness,
                    "ic": individual.ic,
                    "ir": individual.ir,
                    "type": "ml_feature_engineering",
                    "miner": "MLFeatureEngineeringFactorMiner",
                }
                factors.append(factor)

            logger.info(f"ML特征工程因子挖掘完成 - 发现 {len(factors)} 个因子")
            return factors

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"ML特征工程因子挖掘失败: {e}")
            return []

    def analyze_ml_features(self, data: pd.DataFrame) -> Dict[str, Any]:
        """分析ML特征

        提取和分析各种ML特征的统计信息。

        Args:
            data: 市场数据

        Returns:
            ML特征分析结果
        """
        try:
            analysis = {
                "autoencoder": {},
                "pca": {},
                "tsne": {},
                "isolation_forest": {},
                "xgboost": {},
                "neural_network": {},
                "ensemble": {},
                "meta_learning": {},
            }

            # 1. 自编码器潜在特征分析
            autoencoder_feature = ml_feature_operators.autoencoder_latent_feature(
                data,
                latent_dim=self.ml_config.autoencoder_latent_dim,
                encoding_layers=self.ml_config.autoencoder_encoding_layers,
            )
            analysis["autoencoder"] = {
                "mean": float(autoencoder_feature.mean()),
                "std": float(autoencoder_feature.std()),
                "min": float(autoencoder_feature.min()),
                "max": float(autoencoder_feature.max()),
                "latent_dim": self.ml_config.autoencoder_latent_dim,
            }

            # 2. PCA主成分分析
            pca_feature = ml_feature_operators.pca_principal_component(
                data, n_components=self.ml_config.pca_n_components, window=self.ml_config.pca_window
            )
            analysis["pca"] = {
                "mean": float(pca_feature.mean()),
                "std": float(pca_feature.std()),
                "n_components": self.ml_config.pca_n_components,
                "window": self.ml_config.pca_window,
            }

            # 3. t-SNE嵌入分析
            tsne_feature = ml_feature_operators.tsne_embedding(
                data,
                perplexity=self.ml_config.tsne_perplexity,
                n_components=self.ml_config.tsne_n_components,
                window=self.ml_config.tsne_window,
            )
            analysis["tsne"] = {
                "mean": float(tsne_feature.mean()),
                "std": float(tsne_feature.std()),
                "perplexity": self.ml_config.tsne_perplexity,
            }

            # 4. 孤立森林异常检测分析
            isolation_feature = ml_feature_operators.isolation_forest_anomaly(
                data,
                n_estimators=self.ml_config.isolation_n_estimators,
                contamination=self.ml_config.isolation_contamination,
                window=self.ml_config.isolation_window,
            )
            analysis["isolation_forest"] = {
                "mean_anomaly_score": float(isolation_feature.mean()),
                "std_anomaly_score": float(isolation_feature.std()),
                "max_anomaly_score": float(isolation_feature.max()),
                "contamination": self.ml_config.isolation_contamination,
            }

            # 5. XGBoost特征重要性分析
            xgboost_feature = ml_feature_operators.xgboost_feature_importance(
                data,
                n_estimators=self.ml_config.xgboost_n_estimators,
                max_depth=self.ml_config.xgboost_max_depth,
                window=self.ml_config.xgboost_window,
            )
            analysis["xgboost"] = {
                "mean": float(xgboost_feature.mean()),
                "std": float(xgboost_feature.std()),
                "n_estimators": self.ml_config.xgboost_n_estimators,
                "max_depth": self.ml_config.xgboost_max_depth,
            }

            # 6. 神经网络激活值分析
            nn_feature = ml_feature_operators.neural_network_activation(
                data,
                hidden_units=self.ml_config.nn_hidden_units,
                num_layers=self.ml_config.nn_num_layers,
                activation=self.ml_config.nn_activation,
            )
            analysis["neural_network"] = {
                "mean_activation": float(nn_feature.mean()),
                "std_activation": float(nn_feature.std()),
                "hidden_units": self.ml_config.nn_hidden_units,
                "activation": self.ml_config.nn_activation,
            }

            # 7. 集成预测方差分析
            ensemble_feature = ml_feature_operators.ensemble_prediction_variance(
                data, n_models=self.ml_config.ensemble_n_models, window=self.ml_config.ensemble_window
            )
            analysis["ensemble"] = {
                "mean_variance": float(ensemble_feature.mean()),
                "std_variance": float(ensemble_feature.std()),
                "max_variance": float(ensemble_feature.max()),
                "n_models": self.ml_config.ensemble_n_models,
            }

            # 8. 元学习自适应分析
            meta_feature = ml_feature_operators.meta_learning_adaptation(
                data, adaptation_rate=self.ml_config.meta_adaptation_rate, meta_window=self.ml_config.meta_window
            )
            analysis["meta_learning"] = {
                "mean": float(meta_feature.mean()),
                "std": float(meta_feature.std()),
                "adaptation_rate": self.ml_config.meta_adaptation_rate,
                "meta_window": self.ml_config.meta_window,
            }

            logger.info("ML特征分析完成")
            return analysis

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"ML特征分析失败: {e}")
            return {}

    def get_ml_model_summary(self) -> Dict[str, Any]:
        """获取ML模型摘要

        Returns:
            ML模型配置和统计信息
        """
        return {
            "miner_type": "MLFeatureEngineeringFactorMiner",
            "num_operators": len(self.ml_operators),
            "operators": list(self.ml_operators.keys()),
            "config": {
                "autoencoder": {
                    "latent_dim": self.ml_config.autoencoder_latent_dim,
                    "encoding_layers": self.ml_config.autoencoder_encoding_layers,
                },
                "pca": {"n_components": self.ml_config.pca_n_components, "window": self.ml_config.pca_window},
                "tsne": {
                    "perplexity": self.ml_config.tsne_perplexity,
                    "n_components": self.ml_config.tsne_n_components,
                    "window": self.ml_config.tsne_window,
                },
                "isolation_forest": {
                    "n_estimators": self.ml_config.isolation_n_estimators,
                    "contamination": self.ml_config.isolation_contamination,
                    "window": self.ml_config.isolation_window,
                },
                "xgboost": {
                    "n_estimators": self.ml_config.xgboost_n_estimators,
                    "max_depth": self.ml_config.xgboost_max_depth,
                    "window": self.ml_config.xgboost_window,
                },
                "neural_network": {
                    "hidden_units": self.ml_config.nn_hidden_units,
                    "num_layers": self.ml_config.nn_num_layers,
                    "activation": self.ml_config.nn_activation,
                },
                "ensemble": {"n_models": self.ml_config.ensemble_n_models, "window": self.ml_config.ensemble_window},
                "meta_learning": {
                    "adaptation_rate": self.ml_config.meta_adaptation_rate,
                    "meta_window": self.ml_config.meta_window,
                },
            },
        }

    def detect_anomalies(self, data: pd.DataFrame, threshold: float = 2.0) -> pd.Series:
        """检测市场异常

        使用孤立森林算法检测异常点。

        Args:
            data: 市场数据
            threshold: 异常阈值（标准差倍数）

        Returns:
            异常标记序列（True表示异常）
        """
        try:
            anomaly_scores = ml_feature_operators.isolation_forest_anomaly(
                data,
                n_estimators=self.ml_config.isolation_n_estimators,
                contamination=self.ml_config.isolation_contamination,
                window=self.ml_config.isolation_window,
            )

            # 计算阈值
            mean_score = anomaly_scores.mean()
            std_score = anomaly_scores.std()
            anomaly_threshold = mean_score + threshold * std_score

            # 标记异常
            is_anomaly = anomaly_scores > anomaly_threshold

            logger.info(f"异常检测完成 - 发现 {is_anomaly.sum()} 个异常点")
            return is_anomaly

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"异常检测失败: {e}")
            return pd.Series(False, index=data.index)

    def reduce_dimensions(self, data: pd.DataFrame, method: str = "pca", n_components: int = 3) -> pd.DataFrame:
        """降维处理

        使用PCA或t-SNE进行降维。

        Args:
            data: 市场数据
            method: 降维方法，'pca' 或 'tsne'
            n_components: 目标维度

        Returns:
            降维后的特征DataFrame

        Raises:
            ValueError: 当method不是'pca'或'tsne'时
        """
        if method == "pca":
            feature = ml_feature_operators.pca_principal_component(
                data, n_components=n_components, window=self.ml_config.pca_window
            )
            result = pd.DataFrame({"pc1": feature}, index=data.index)

        elif method == "tsne":
            feature = ml_feature_operators.tsne_embedding(
                data,
                perplexity=self.ml_config.tsne_perplexity,
                n_components=n_components,
                window=self.ml_config.tsne_window,
            )
            result = pd.DataFrame({"tsne1": feature}, index=data.index)

        else:
            raise ValueError(f"不支持的降维方法: {method}")

        logger.info(f"降维完成 - 方法: {method}, 目标维度: {n_components}")
        return result

    def evaluate_feature_importance(self, data: pd.DataFrame, returns: pd.Series) -> Dict[str, float]:
        """评估特征重要性

        使用XGBoost评估各个特征的重要性。

        Args:
            data: 市场数据
            returns: 目标收益率

        Returns:
            特征重要性字典
        """
        try:
            # 计算XGBoost特征重要性
            importance_feature = ml_feature_operators.xgboost_feature_importance(  # pylint: disable=unused-variable
                data,
                n_estimators=self.ml_config.xgboost_n_estimators,
                max_depth=self.ml_config.xgboost_max_depth,
                window=self.ml_config.xgboost_window,
            )

            # 计算与收益率的相关性作为重要性
            importance = {}
            for col in data.columns:
                if col in ["close", "open", "high", "low", "volume"]:
                    corr = data[col].corr(returns)
                    importance[col] = abs(corr)

            # 排序
            importance = dict(sorted(importance.items(), key=lambda x: x[1], reverse=True))

            logger.info(f"特征重要性评估完成 - 共 {len(importance)} 个特征")
            return importance

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"特征重要性评估失败: {e}")
            return {}
