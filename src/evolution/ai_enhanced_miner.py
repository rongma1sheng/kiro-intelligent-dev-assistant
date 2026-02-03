# pylint: disable=too-many-lines
"""AI增强因子挖掘器

白皮书依据: 第四章 4.1.4 AI增强因子挖掘
需求: 3.1-3.10
设计文档: design.md - AI-Enhanced Factor Miner
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List

import numpy as np
import pandas as pd
from loguru import logger

from .unified_factor_mining_system import BaseMiner, FactorMetadata, MinerType


class AIModelType(Enum):
    """AI模型类型"""

    TRANSFORMER = "transformer"
    GNN = "gnn"
    RL = "rl"
    MULTIMODAL = "multimodal"
    GAN = "gan"
    LSTM = "lstm"
    CNN = "cnn"
    ATTENTION = "attention"


@dataclass
class ModelConfidence:
    """模型置信度评分

    Attributes:
        prediction_confidence: 预测置信度 (0-1)
        model_stability: 模型稳定性 (0-1)
        feature_importance: 特征重要性一致性 (0-1)
        overall: 综合置信度 (0-1)
    """

    prediction_confidence: float
    model_stability: float
    feature_importance: float
    overall: float

    def is_acceptable(self, threshold: float = 0.6) -> bool:
        """检查置信度是否可接受

        Args:
            threshold: 置信度阈值，默认0.6

        Returns:
            True如果置信度可接受，False否则
        """
        return self.overall >= threshold


class AIEnhancedFactorMiner(BaseMiner):
    """AI增强因子挖掘器

    白皮书依据: 第四章 4.1.4
    需求: 3.1-3.10

    使用Transformer、GNN、RL、多模态融合、GAN、LSTM、CNN、
    注意力机制等AI模型生成高级因子。

    支持8个核心AI增强算子：
    1. transformer_attention: Transformer注意力权重
    2. gnn_node_embedding: 图神经网络节点嵌入
    3. rl_adaptive_weight: 强化学习自适应权重
    4. multimodal_fusion: 多模态数据融合
    5. gan_synthetic_feature: GAN合成特征
    6. lstm_hidden_state: LSTM隐藏状态
    7. cnn_feature_map: CNN特征图
    8. attention_mechanism: 注意力机制

    Attributes:
        operators: 8个算子的字典
        model_confidence_threshold: 模型置信度阈值 (默认0.6)
        cross_validation_folds: 交叉验证折数 (默认5)
        regularization_strength: 正则化强度 (默认0.01)
    """

    def __init__(
        self,
        model_confidence_threshold: float = 0.6,
        cross_validation_folds: int = 5,
        regularization_strength: float = 0.01,
    ):
        """初始化AI增强因子挖掘器

        白皮书依据: 第四章 4.1.4
        需求: 3.1-3.10

        Args:
            model_confidence_threshold: 模型置信度阈值，默认0.6
            cross_validation_folds: 交叉验证折数，默认5
            regularization_strength: 正则化强度，默认0.01

        Raises:
            ValueError: 当参数不在有效范围时
        """
        super().__init__(MinerType.AI_ENHANCED, "AIEnhancedFactorMiner")

        if not 0 < model_confidence_threshold <= 1:
            raise ValueError(f"model_confidence_threshold必须在 (0, 1]，当前: {model_confidence_threshold}")

        if cross_validation_folds < 2:
            raise ValueError(f"cross_validation_folds必须 >= 2，当前: {cross_validation_folds}")

        if regularization_strength < 0:
            raise ValueError(f"regularization_strength必须 >= 0，当前: {regularization_strength}")

        self.model_confidence_threshold = model_confidence_threshold
        self.cross_validation_folds = cross_validation_folds
        self.regularization_strength = regularization_strength
        self.operators = self._initialize_operators()

        # 模型缓存（避免重复训练）
        self.model_cache: Dict[str, Any] = {}

        logger.info(
            f"AIEnhancedFactorMiner初始化完成 - "
            f"confidence_threshold={model_confidence_threshold}, "
            f"cv_folds={cross_validation_folds}, "
            f"regularization={regularization_strength}, "
            f"operators={len(self.operators)}"
        )

    def _initialize_operators(self) -> Dict[str, Callable]:
        """初始化8个AI增强算子

        白皮书依据: 第四章 4.1.4
        需求: 3.8

        Returns:
            算子名称到函数的字典
        """
        return {
            "transformer_attention": self._transformer_attention,
            "gnn_node_embedding": self._gnn_node_embedding,
            "rl_adaptive_weight": self._rl_adaptive_weight,
            "multimodal_fusion": self._multimodal_fusion,
            "gan_synthetic_feature": self._gan_synthetic_feature,
            "lstm_hidden_state": self._lstm_hidden_state,
            "cnn_feature_map": self._cnn_feature_map,
            "attention_mechanism": self._attention_mechanism,
        }

    def mine_factors(self, data: pd.DataFrame, returns: pd.Series, **kwargs) -> List[FactorMetadata]:
        """挖掘AI增强因子

        白皮书依据: 第四章 4.1.4
        需求: 3.1-3.10

        Args:
            data: 市场数据（DataFrame），包含价格、成交量等
            returns: 收益率数据
            **kwargs: 额外参数
                - ai_data: AI模型输入数据字典 {model_type: data}
                - symbols: 股票代码列表
                - operators: 要使用的算子列表（默认使用所有）

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
        ai_data = kwargs.get("ai_data", {})
        symbols = kwargs.get("symbols", data.index.tolist() if hasattr(data.index, "tolist") else [])
        operators_to_use = kwargs.get("operators", list(self.operators.keys()))

        logger.info(
            f"开始挖掘AI增强因子 - "
            f"data_shape={data.shape}, "
            f"ai_models={len(ai_data)}, "
            f"operators={len(operators_to_use)}"
        )

        factors = []

        # 对每个算子执行挖掘
        for operator_name in operators_to_use:
            if operator_name not in self.operators:
                logger.warning(f"未知算子: {operator_name}，跳过")
                continue

            try:
                # 获取算子函数
                operator_func = self.operators[operator_name]

                # 执行算子
                factor_values = operator_func(data, ai_data, symbols, returns)

                # 评估模型置信度
                confidence_score = self._evaluate_model_confidence(factor_values, operator_name, data, returns)

                # 检查置信度阈值
                if not confidence_score.is_acceptable(self.model_confidence_threshold):
                    logger.warning(
                        f"算子 {operator_name} 模型置信度不达标: "
                        f"{confidence_score.overall:.3f} < {self.model_confidence_threshold}"
                    )
                    continue

                # 计算因子指标
                ic = self._calculate_ic(factor_values, returns)
                ir = self._calculate_ir(factor_values, returns)
                sharpe = self._calculate_sharpe(factor_values, returns)

                # 计算综合适应度
                fitness = self._calculate_fitness(ic, ir, sharpe)

                # 创建因子元数据
                factor = FactorMetadata(
                    factor_id=f"ai_enhanced_{operator_name}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                    factor_name=f"AIEnhanced_{operator_name}",
                    factor_type=MinerType.AI_ENHANCED,
                    data_source=self._get_model_type_for_operator(operator_name),
                    discovery_date=datetime.now(),
                    discoverer=self.miner_name,
                    expression=f"{operator_name}(ai_model, data, symbols)",
                    fitness=fitness,
                    ic=ic,
                    ir=ir,
                    sharpe=sharpe,
                )

                factors.append(factor)

                logger.info(
                    f"发现因子: {factor.factor_id}, "
                    f"IC={ic:.4f}, IR={ir:.4f}, Sharpe={sharpe:.4f}, "
                    f"fitness={fitness:.4f}, confidence={confidence_score.overall:.4f}"
                )

            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.error(f"算子 {operator_name} 执行失败: {e}")
                self.metadata.error_count += 1
                self.metadata.last_error = str(e)
                continue

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
            f"AI增强因子挖掘完成 - " f"发现因子数={len(factors)}, " f"平均fitness={self.metadata.average_fitness:.4f}"
        )

        return factors

    # ==================== 8个核心算子实现 ====================

    def _transformer_attention(
        self,
        data: pd.DataFrame,
        ai_data: Dict[str, Any],  # pylint: disable=unused-argument
        symbols: List[str],  # pylint: disable=unused-argument
        returns: pd.Series,  # pylint: disable=unused-argument
    ) -> pd.Series:
        """Transformer注意力权重算子

        白皮书依据: 第四章 4.1.4
        需求: 3.1

        从Transformer模型中提取注意力权重作为因子特征。

        Args:
            data: 市场数据
            ai_data: AI模型数据字典
            symbols: 股票代码列表
            returns: 收益率数据

        Returns:
            因子值序列
        """
        # 准备序列数据（使用价格和成交量）
        if "close" not in data.columns or "volume" not in data.columns:
            raise ValueError("数据中缺少 close 或 volume 列")

        # 构建时间序列特征
        sequence_length = 20
        features = []

        for i in range(sequence_length, len(data)):
            window_data = data.iloc[i - sequence_length : i]
            # 标准化价格和成交量
            price_norm = (window_data["close"] - window_data["close"].mean()) / window_data["close"].std()
            volume_norm = (window_data["volume"] - window_data["volume"].mean()) / window_data["volume"].std()
            features.append(np.concatenate([price_norm.values, volume_norm.values]))

        if not features:
            return pd.Series(0, index=data.index)

        features_array = np.array(features)

        # 简化的注意力机制（自注意力）
        # Q, K, V = features @ W_q, features @ W_k, features @ W_v
        # Attention = softmax(Q @ K^T / sqrt(d_k)) @ V

        d_model = features_array.shape[1]
        d_k = d_model // 2

        # 随机初始化权重矩阵（实际应该训练）
        np.random.seed(42)
        W_q = np.random.randn(d_model, d_k) * 0.01
        W_k = np.random.randn(d_model, d_k) * 0.01
        W_v = np.random.randn(d_model, d_k) * 0.01

        # 计算Q, K, V
        Q = features_array @ W_q
        K = features_array @ W_k
        features_array @ W_v  # pylint: disable=w0104

        # 计算注意力分数
        attention_scores = Q @ K.T / np.sqrt(d_k)

        # Softmax
        attention_weights = np.exp(attention_scores) / np.exp(attention_scores).sum(axis=1, keepdims=True)

        # 提取注意力权重的统计特征作为因子
        # 使用最后一个时间步的注意力权重
        last_attention = attention_weights[-1, :]

        # 创建因子值序列
        factor_values = pd.Series(0.0, index=data.index)
        factor_values.iloc[sequence_length:] = last_attention[: len(factor_values) - sequence_length]

        logger.debug(f"transformer_attention: 计算完成，非零值={(factor_values != 0).sum()}")

        return factor_values

    def _gnn_node_embedding(
        self,
        data: pd.DataFrame,
        ai_data: Dict[str, Any],  # pylint: disable=unused-argument
        symbols: List[str],  # pylint: disable=unused-argument
        returns: pd.Series,  # pylint: disable=unused-argument
    ) -> pd.Series:
        """图神经网络节点嵌入算子

        白皮书依据: 第四章 4.1.4
        需求: 3.2

        从图神经网络中生成节点嵌入表示股票关系。

        Args:
            data: 市场数据
            ai_data: AI模型数据字典
            symbols: 股票代码列表
            returns: 收益率数据

        Returns:
            因子值序列
        """
        # 构建股票相关性图
        if "close" not in data.columns:
            raise ValueError("数据中缺少 close 列")

        # 计算收益率相关性矩阵
        window = 60
        if len(data) < window:
            return pd.Series(0, index=data.index)

        price_data = data["close"].iloc[-window:]
        returns_data = price_data.pct_change().dropna()

        # 简化的GNN：使用相关性作为边权重
        # 节点嵌入 = 邻居节点特征的加权平均

        # 计算节点特征（使用收益率统计）
        node_features = np.array([returns_data.mean(), returns_data.std(), returns_data.skew(), returns_data.kurt()])

        # 简化的图卷积：embedding = feature + neighbor_aggregation
        # 这里使用自身特征作为嵌入（简化版本）
        embedding_value = np.mean(node_features)

        # 创建因子值序列
        factor_values = pd.Series(embedding_value, index=data.index)

        logger.debug(f"gnn_node_embedding: 计算完成，嵌入值={embedding_value:.4f}")

        return factor_values

    def _rl_adaptive_weight(
        self,
        data: pd.DataFrame,
        ai_data: Dict[str, Any],  # pylint: disable=unused-argument
        symbols: List[str],  # pylint: disable=unused-argument
        returns: pd.Series,  # pylint: disable=unused-argument
    ) -> pd.Series:
        """强化学习自适应权重算子

        白皮书依据: 第四章 4.1.4
        需求: 3.3

        使用强化学习生成根据市场条件自适应调整的权重。

        Args:
            data: 市场数据
            ai_data: AI模型数据字典
            symbols: 股票代码列表
            returns: 收益率数据

        Returns:
            因子值序列
        """
        if "close" not in data.columns or "volume" not in data.columns:
            raise ValueError("数据中缺少 close 或 volume 列")

        # 简化的RL：基于市场状态（波动率、趋势）调整权重
        # State: [volatility, trend, volume_change]
        # Action: weight adjustment
        # Reward: returns

        # 计算市场状态特征
        window = 20
        volatility = data["close"].pct_change().rolling(window=window).std()
        trend = data["close"].rolling(window=window).mean() / data["close"] - 1
        data["volume"].pct_change()

        # 简化的Q-learning：根据状态选择权重
        # 高波动率 -> 低权重，低波动率 -> 高权重
        # 正趋势 -> 高权重，负趋势 -> 低权重

        adaptive_weight = (1 - volatility / volatility.max()) * 0.5 + (trend + 1) / 2 * 0.5  # 波动率因素  # 趋势因素

        factor_values = adaptive_weight.fillna(0.5)

        logger.debug(f"rl_adaptive_weight: 计算完成，平均权重={factor_values.mean():.4f}")

        return factor_values

    def _multimodal_fusion(
        self,
        data: pd.DataFrame,
        ai_data: Dict[str, Any],  # pylint: disable=unused-argument
        symbols: List[str],  # pylint: disable=unused-argument
        returns: pd.Series,  # pylint: disable=unused-argument
    ) -> pd.Series:
        """多模态数据融合算子

        白皮书依据: 第四章 4.1.4
        需求: 3.4

        融合价格、成交量、新闻、情绪等多模态数据。

        Args:
            data: 市场数据
            ai_data: AI模型数据字典
            symbols: 股票代码列表
            returns: 收益率数据

        Returns:
            因子值序列
        """
        if "close" not in data.columns or "volume" not in data.columns:
            raise ValueError("数据中缺少 close 或 volume 列")

        # 多模态融合：价格模态 + 成交量模态
        # 使用注意力机制融合不同模态

        # 模态1：价格动量
        price_momentum = data["close"].pct_change(periods=5)

        # 模态2：成交量动量
        volume_momentum = data["volume"].pct_change(periods=5)

        # 简化的注意力融合：加权平均
        # 权重基于各模态的信息量（标准差）
        price_std = price_momentum.std()
        volume_std = volume_momentum.std()

        total_std = price_std + volume_std
        if total_std > 0:
            price_weight = price_std / total_std
            volume_weight = volume_std / total_std
        else:
            price_weight = volume_weight = 0.5

        # 融合特征
        fused_feature = price_momentum * price_weight + volume_momentum * volume_weight

        factor_values = fused_feature.fillna(0)

        logger.debug(
            f"multimodal_fusion: 计算完成，" f"price_weight={price_weight:.3f}, volume_weight={volume_weight:.3f}"
        )

        return factor_values

    def _gan_synthetic_feature(
        self,
        data: pd.DataFrame,
        ai_data: Dict[str, Any],  # pylint: disable=unused-argument
        symbols: List[str],  # pylint: disable=unused-argument
        returns: pd.Series,  # pylint: disable=unused-argument
    ) -> pd.Series:
        """GAN合成特征算子

        白皮书依据: 第四章 4.1.4
        需求: 3.5

        使用GAN生成合成特征增强训练数据。

        Args:
            data: 市场数据
            ai_data: AI模型数据字典
            symbols: 股票代码列表
            returns: 收益率数据

        Returns:
            因子值序列
        """
        if "close" not in data.columns:
            raise ValueError("数据中缺少 close 列")

        # 简化的GAN：生成器生成合成价格特征
        # Generator: noise -> synthetic_feature
        # Discriminator: real/synthetic -> probability

        # 提取真实特征
        real_features = data["close"].pct_change().dropna()

        # 生成器：使用噪声生成合成特征
        np.random.seed(42)
        noise = np.random.randn(len(real_features))

        # 简化的生成：noise * std + mean
        synthetic_features = noise * real_features.std() + real_features.mean()

        # 混合真实和合成特征（50-50）
        mixed_features = (real_features.values + synthetic_features) / 2

        # 创建因子值序列
        factor_values = pd.Series(0.0, index=data.index)
        factor_values.iloc[1 : len(mixed_features) + 1] = mixed_features

        logger.debug(f"gan_synthetic_feature: 计算完成，合成特征数={len(synthetic_features)}")

        return factor_values

    def _lstm_hidden_state(
        self,
        data: pd.DataFrame,
        ai_data: Dict[str, Any],  # pylint: disable=unused-argument
        symbols: List[str],  # pylint: disable=unused-argument
        returns: pd.Series,  # pylint: disable=unused-argument
    ) -> pd.Series:
        """LSTM隐藏状态算子

        白皮书依据: 第四章 4.1.4
        需求: 3.6

        从LSTM模型中提取隐藏状态捕获时序依赖。

        Args:
            data: 市场数据
            ai_data: AI模型数据字典
            symbols: 股票代码列表
            returns: 收益率数据

        Returns:
            因子值序列
        """
        if "close" not in data.columns:
            raise ValueError("数据中缺少 close 列")

        # 简化的LSTM：使用指数移动平均模拟隐藏状态
        # h_t = tanh(W_h * h_{t-1} + W_x * x_t)

        # 输入序列
        input_sequence = data["close"].pct_change().fillna(0)

        # 简化的LSTM单元：使用EMA作为隐藏状态
        # 短期记忆（快速EMA）
        short_memory = input_sequence.ewm(span=5).mean()

        # 长期记忆（慢速EMA）
        long_memory = input_sequence.ewm(span=20).mean()

        # 隐藏状态：短期和长期记忆的组合
        hidden_state = short_memory - long_memory

        factor_values = hidden_state.fillna(0)

        logger.debug(f"lstm_hidden_state: 计算完成，非零值={(factor_values != 0).sum()}")

        return factor_values

    def _cnn_feature_map(
        self,
        data: pd.DataFrame,
        ai_data: Dict[str, Any],  # pylint: disable=unused-argument
        symbols: List[str],  # pylint: disable=unused-argument
        returns: pd.Series,  # pylint: disable=unused-argument
    ) -> pd.Series:
        """CNN特征图算子

        白皮书依据: 第四章 4.1.4
        需求: 3.7

        从CNN模型中生成特征图提取价格-成交量模式。

        Args:
            data: 市场数据
            ai_data: AI模型数据字典
            symbols: 股票代码列表
            returns: 收益率数据

        Returns:
            因子值序列
        """
        if "close" not in data.columns or "volume" not in data.columns:
            raise ValueError("数据中缺少 close 或 volume 列")

        # 简化的CNN：使用卷积核提取局部模式
        # Conv1D: input -> feature_map

        # 构建2D输入（价格和成交量）
        price_norm = (data["close"] - data["close"].mean()) / data["close"].std()
        volume_norm = (data["volume"] - data["volume"].mean()) / data["volume"].std()

        # 简化的卷积：使用滑动窗口
        kernel_size = 5
        feature_maps = []

        for i in range(kernel_size, len(data)):
            window_price = price_norm.iloc[i - kernel_size : i].values
            window_volume = volume_norm.iloc[i - kernel_size : i].values

            # 简单的卷积核：检测上升/下降模式
            price_trend = np.sum(np.diff(window_price))
            volume_trend = np.sum(np.diff(window_volume))

            # 特征图：价格和成交量趋势的组合
            feature = price_trend * 0.6 + volume_trend * 0.4
            feature_maps.append(feature)

        # 创建因子值序列
        factor_values = pd.Series(0.0, index=data.index)
        if feature_maps:
            factor_values.iloc[kernel_size : kernel_size + len(feature_maps)] = feature_maps

        logger.debug(f"cnn_feature_map: 计算完成，特征图数={len(feature_maps)}")

        return factor_values

    def _attention_mechanism(
        self,
        data: pd.DataFrame,
        ai_data: Dict[str, Any],  # pylint: disable=unused-argument
        symbols: List[str],  # pylint: disable=unused-argument
        returns: pd.Series,  # pylint: disable=unused-argument
    ) -> pd.Series:
        """注意力机制算子

        白皮书依据: 第四章 4.1.4
        需求: 3.8

        使用注意力机制识别重要的时间步和特征。

        Args:
            data: 市场数据
            ai_data: AI模型数据字典
            symbols: 股票代码列表
            returns: 收益率数据

        Returns:
            因子值序列
        """
        if "close" not in data.columns or "volume" not in data.columns:
            raise ValueError("数据中缺少 close 或 volume 列")

        # 注意力机制：计算每个时间步的重要性权重
        # Attention(Q, K, V) = softmax(Q @ K^T / sqrt(d_k)) @ V

        # 特征：价格变化和成交量变化
        price_change = data["close"].pct_change().fillna(0)
        volume_change = data["volume"].pct_change().fillna(0)

        # 计算注意力分数：基于特征的重要性
        # 重要性 = |price_change| + |volume_change|
        importance = np.abs(price_change) + np.abs(volume_change)

        # Softmax归一化
        window = 20
        attention_weights = importance.rolling(window=window).apply(
            lambda x: np.exp(x) / np.exp(x).sum() if len(x) > 0 else 0, raw=True
        )

        # 加权特征
        attended_feature = price_change * attention_weights

        factor_values = attended_feature.fillna(0)

        logger.debug(f"attention_mechanism: 计算完成，非零值={(factor_values != 0).sum()}")

        return factor_values

    # ==================== 辅助方法实现 ====================

    def _evaluate_model_confidence(
        self,
        factor_values: pd.Series,
        operator_name: str,  # pylint: disable=unused-argument
        data: pd.DataFrame,  # pylint: disable=unused-argument
        returns: pd.Series,  # pylint: disable=unused-argument
    ) -> ModelConfidence:
        """评估模型置信度

        白皮书依据: 第四章 4.1.4
        需求: 3.9

        Args:
            factor_values: 因子值序列
            operator_name: 算子名称
            data: 市场数据
            returns: 收益率数据

        Returns:
            模型置信度评分
        """
        # 1. 预测置信度：基于因子值的稳定性
        if len(factor_values) > 1:
            # 计算因子值的变异系数
            cv = factor_values.std() / (abs(factor_values.mean()) + 1e-8)
            prediction_confidence = 1.0 / (1.0 + cv)
        else:
            prediction_confidence = 0.5

        # 2. 模型稳定性：使用交叉验证评估
        model_stability = self._cross_validate_stability(factor_values, returns, self.cross_validation_folds)

        # 3. 特征重要性一致性：检查因子与收益的相关性稳定性
        window = 60
        if len(factor_values) >= window * 2:
            correlations = []
            for i in range(window, len(factor_values), window // 2):
                factor_window = factor_values.iloc[i - window : i]
                returns_window = returns.iloc[i - window : i]

                # 对齐索引
                common_index = factor_window.index.intersection(returns_window.index)
                if len(common_index) > 10:
                    corr = factor_window.loc[common_index].corr(returns_window.loc[common_index])
                    if not np.isnan(corr):
                        correlations.append(corr)

            if correlations:
                # 相关性的标准差越小，一致性越高
                feature_importance = 1.0 / (1.0 + np.std(correlations))
            else:
                feature_importance = 0.5
        else:
            feature_importance = 0.5

        # 综合置信度评分（加权平均）
        overall = prediction_confidence * 0.3 + model_stability * 0.4 + feature_importance * 0.3

        return ModelConfidence(
            prediction_confidence=prediction_confidence,
            model_stability=model_stability,
            feature_importance=feature_importance,
            overall=overall,
        )

    def _cross_validate_stability(self, factor_values: pd.Series, returns: pd.Series, n_folds: int) -> float:
        """交叉验证评估模型稳定性

        白皮书依据: 第四章 4.1.4
        需求: 3.10

        Args:
            factor_values: 因子值序列
            returns: 收益率序列
            n_folds: 交叉验证折数

        Returns:
            稳定性评分 (0-1)
        """
        # 对齐索引
        common_index = factor_values.index.intersection(returns.index)
        if len(common_index) < n_folds * 10:
            return 0.5

        factor_aligned = factor_values.loc[common_index]
        returns_aligned = returns.loc[common_index]

        # K-fold交叉验证
        fold_size = len(common_index) // n_folds
        fold_scores = []

        for i in range(n_folds):
            # 划分训练集和验证集
            val_start = i * fold_size
            val_end = (i + 1) * fold_size if i < n_folds - 1 else len(common_index)

            val_indices = common_index[val_start:val_end]
            train_indices = common_index.difference(val_indices)

            if len(train_indices) < 10 or len(val_indices) < 10:
                continue

            # 在验证集上计算IC
            val_factor = factor_aligned.loc[val_indices]
            val_returns = returns_aligned.loc[val_indices]

            # 移除NaN
            valid_mask = ~(val_factor.isna() | val_returns.isna())
            val_factor_clean = val_factor[valid_mask]
            val_returns_clean = val_returns[valid_mask]

            if len(val_factor_clean) >= 2:
                try:
                    ic = val_factor_clean.corr(val_returns_clean, method="spearman")
                    if not np.isnan(ic):
                        fold_scores.append(abs(ic))
                except Exception:  # pylint: disable=broad-exception-caught
                    pass

        if not fold_scores:
            return 0.5

        # 稳定性 = 1 - (IC标准差 / IC均值)
        mean_ic = np.mean(fold_scores)
        std_ic = np.std(fold_scores)

        if mean_ic > 0:
            stability = 1.0 - min(std_ic / mean_ic, 1.0)
        else:
            stability = 0.5

        return stability

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
        if factor_aligned.std() > 0:
            factor_normalized = (factor_aligned - factor_aligned.mean()) / factor_aligned.std()
        else:
            return 0.0

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

    def _get_model_type_for_operator(self, operator_name: str) -> str:
        """获取算子对应的模型类型

        Args:
            operator_name: 算子名称

        Returns:
            模型类型名称
        """
        model_mapping = {
            "transformer_attention": "transformer",
            "gnn_node_embedding": "gnn",
            "rl_adaptive_weight": "reinforcement_learning",
            "multimodal_fusion": "multimodal",
            "gan_synthetic_feature": "gan",
            "lstm_hidden_state": "lstm",
            "cnn_feature_map": "cnn",
            "attention_mechanism": "attention",
        }

        return model_mapping.get(operator_name, "unknown")
