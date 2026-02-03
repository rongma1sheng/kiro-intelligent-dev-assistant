"""时序深度学习因子算子库

白皮书依据: 第四章 4.1.9 时序深度学习因子挖掘器

核心算子库 (8种算子):
1. lstm_forecast_residual: LSTM预测残差
2. tcn_temporal_pattern: TCN时序模式
3. wavenet_receptive_field: WaveNet感受野
4. attention_temporal_weight: 注意力时序权重
5. seq2seq_prediction_error: Seq2Seq预测误差
6. transformer_time_embedding: Transformer时间嵌入
7. nbeats_trend_seasonality: N-BEATS趋势季节性
8. deepar_probabilistic_forecast: DeepAR概率预测
"""

from typing import Optional

import numpy as np
import pandas as pd
from loguru import logger


def lstm_forecast_residual(
    data: pd.DataFrame, hidden_dim: int = 64, sequence_length: int = 20, forecast_horizon: int = 1
) -> pd.Series:
    """LSTM预测残差

    白皮书依据: 第四章 4.1.9 - lstm_forecast_residual

    使用LSTM进行时序预测，计算预测值与实际值的残差。
    残差包含模型未能捕捉的信息，可作为补充因子。

    Args:
        data: 市场数据，包含close列
        hidden_dim: LSTM隐藏层维度
        sequence_length: 输入序列长度
        forecast_horizon: 预测步长

    Returns:
        预测残差序列

    应用场景:
        - 时序记忆提取
        - 趋势延续预测
        - 动量策略
    """
    try:
        if "close" not in data.columns:
            logger.warning("lstm_forecast_residual: 缺少close列，返回零序列")
            return pd.Series(0.0, index=data.index)

        close = data["close"].ffill().fillna(0)
        result = pd.Series(0.0, index=data.index)

        # 计算收益率
        returns = close.pct_change().fillna(0)

        # LSTM状态
        hidden_state = np.zeros(hidden_dim)
        cell_state = np.zeros(hidden_dim)

        for i in range(sequence_length, len(data) - forecast_horizon):
            # 输入序列
            input_sequence = returns.iloc[i - sequence_length : i].values

            # LSTM前向传播（简化版本）
            for t in range(len(input_sequence)):  # pylint: disable=consider-using-enumerate
                x_t = input_sequence[t]

                # 输入门
                i_t = 1.0 / (1.0 + np.exp(-(x_t + hidden_state.mean())))

                # 遗忘门
                f_t = 1.0 / (1.0 + np.exp(x_t - hidden_state.mean()))

                # 输出门
                o_t = 1.0 / (1.0 + np.exp(-abs(x_t)))

                # 更新细胞状态
                cell_state = f_t * cell_state + i_t * x_t

                # 更新隐藏状态
                hidden_state = o_t * np.tanh(cell_state) * np.ones(hidden_dim)

            # 预测
            prediction = hidden_state.mean()

            # 实际值
            actual = returns.iloc[i + forecast_horizon]

            # 残差
            residual = actual - prediction
            result.iloc[i] = residual

        return result

    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.error(f"lstm_forecast_residual计算失败: {e}")
        return pd.Series(0.0, index=data.index)


def tcn_temporal_pattern(
    data: pd.DataFrame,
    kernel_size: int = 3,
    num_filters: int = 32,  # pylint: disable=unused-argument
    dilation_rates: Optional[list] = None,  # pylint: disable=unused-argument
) -> pd.Series:
    """TCN时序模式

    白皮书依据: 第四章 4.1.9 - tcn_temporal_pattern

    使用时序卷积网络（TCN）提取时序模式。
    通过膨胀卷积扩大感受野，捕捉长期依赖。

    Args:
        data: 市场数据，包含close列
        kernel_size: 卷积核大小
        num_filters: 卷积核数量
        dilation_rates: 膨胀率列表

    Returns:
        TCN时序模式特征序列

    应用场景:
        - 长期依赖捕捉
        - 多尺度模式识别
        - 趋势预测
    """
    try:
        if "close" not in data.columns:
            logger.warning("tcn_temporal_pattern: 缺少close列，返回零序列")
            return pd.Series(0.0, index=data.index)

        if dilation_rates is None:
            dilation_rates = [1, 2, 4, 8]

        close = data["close"].ffill().fillna(0)
        result = pd.Series(0.0, index=data.index)

        # 计算收益率
        returns = close.pct_change().fillna(0)

        # TCN: 多层膨胀卷积
        for i in range(max(dilation_rates) * kernel_size, len(data)):
            features = []

            for dilation in dilation_rates:
                # 膨胀卷积：采样间隔为dilation
                receptive_field = kernel_size * dilation

                if i >= receptive_field:
                    # 提取膨胀采样的序列
                    indices = [i - j * dilation for j in range(kernel_size)]
                    indices = [idx for idx in indices if idx >= 0]

                    if len(indices) > 0:
                        dilated_sequence = returns.iloc[indices].values

                        # 卷积操作（简化：使用均值）
                        conv_output = dilated_sequence.mean()

                        # ReLU激活
                        activated = max(0, conv_output)
                        features.append(activated)

            # 聚合多尺度特征
            if len(features) > 0:
                result.iloc[i] = np.mean(features)

        return result

    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.error(f"tcn_temporal_pattern计算失败: {e}")
        return pd.Series(0.0, index=data.index)


def wavenet_receptive_field(data: pd.DataFrame, num_layers: int = 4, kernel_size: int = 2) -> pd.Series:
    """WaveNet感受野

    白皮书依据: 第四章 4.1.9 - wavenet_receptive_field

    使用WaveNet架构的指数级膨胀卷积。
    通过堆叠膨胀卷积层，实现指数级感受野增长。

    Args:
        data: 市场数据，包含close列
        num_layers: 层数
        kernel_size: 卷积核大小

    Returns:
        WaveNet感受野特征序列

    应用场景:
        - 超长期依赖
        - 多分辨率分析
        - 波动预测
    """
    try:
        if "close" not in data.columns:
            logger.warning("wavenet_receptive_field: 缺少close列，返回零序列")
            return pd.Series(0.0, index=data.index)

        close = data["close"].ffill().fillna(0)
        result = pd.Series(0.0, index=data.index)

        # 计算收益率
        returns = close.pct_change().fillna(0)

        # WaveNet: 指数级膨胀率 [1, 2, 4, 8, ...]
        dilation_rates = [2**i for i in range(num_layers)]
        max_dilation = max(dilation_rates) * kernel_size

        for i in range(max_dilation, len(data)):
            layer_outputs = []

            for layer_idx, dilation in enumerate(dilation_rates):  # pylint: disable=unused-variable
                # 膨胀卷积
                receptive_field = kernel_size * dilation

                if i >= receptive_field:
                    # 提取序列
                    indices = [i - j * dilation for j in range(kernel_size)]
                    indices = [idx for idx in indices if idx >= 0]

                    if len(indices) >= kernel_size:
                        sequence = returns.iloc[indices[:kernel_size]].values

                        # 门控激活单元（Gated Activation）
                        # tanh(W_f * x) ⊙ sigmoid(W_g * x)
                        filter_output = np.tanh(sequence.mean())
                        gate_output = 1.0 / (1.0 + np.exp(-sequence.std()))

                        gated_output = filter_output * gate_output
                        layer_outputs.append(gated_output)

            # 残差连接和跳跃连接
            if len(layer_outputs) > 0:
                skip_connections = np.array(layer_outputs)
                result.iloc[i] = skip_connections.sum()

        return result

    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.error(f"wavenet_receptive_field计算失败: {e}")
        return pd.Series(0.0, index=data.index)


def attention_temporal_weight(data: pd.DataFrame, attention_window: int = 20, num_heads: int = 4) -> pd.Series:
    """注意力时序权重

    白皮书依据: 第四章 4.1.9 - attention_temporal_weight

    使用注意力机制计算时序权重。
    动态关注历史中最相关的时间点。

    Args:
        data: 市场数据，包含close列
        attention_window: 注意力窗口大小
        num_heads: 多头注意力数量

    Returns:
        注意力时序权重序列

    应用场景:
        - 动态特征选择
        - 关键时点识别
        - 自适应预测
    """
    try:
        if "close" not in data.columns:
            logger.warning("attention_temporal_weight: 缺少close列，返回零序列")
            return pd.Series(0.0, index=data.index)

        close = data["close"].ffill().fillna(0)
        result = pd.Series(0.0, index=data.index)

        # 计算收益率
        returns = close.pct_change().fillna(0)

        # 时序注意力
        for i in range(attention_window, len(data)):
            # 提取窗口
            window_returns = returns.iloc[i - attention_window : i].values
            current_return = returns.iloc[i - 1]

            # 多头注意力
            head_outputs = []

            for head in range(num_heads):  # pylint: disable=unused-variable
                # Query: 当前时刻
                query = current_return

                # Key & Value: 历史序列
                keys = window_returns
                values = window_returns

                # 计算注意力分数
                # score = exp(query * key / sqrt(d_k))
                d_k = len(window_returns) / num_heads
                scores = np.exp((query * keys) / np.sqrt(d_k + 1e-8))

                # Softmax归一化
                attention_weights = scores / (scores.sum() + 1e-8)

                # 加权求和
                head_output = np.dot(attention_weights, values)
                head_outputs.append(head_output)

            # 多头拼接
            result.iloc[i] = np.mean(head_outputs)

        return result

    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.error(f"attention_temporal_weight计算失败: {e}")
        return pd.Series(0.0, index=data.index)


def seq2seq_prediction_error(
    data: pd.DataFrame, encoder_length: int = 20, decoder_length: int = 5, hidden_dim: int = 32
) -> pd.Series:
    """Seq2Seq预测误差

    白皮书依据: 第四章 4.1.9 - seq2seq_prediction_error

    使用Seq2Seq模型进行序列到序列预测。
    计算预测序列与实际序列的误差。

    Args:
        data: 市场数据，包含close列
        encoder_length: 编码器序列长度
        decoder_length: 解码器序列长度
        hidden_dim: 隐藏层维度

    Returns:
        Seq2Seq预测误差序列

    应用场景:
        - 多步预测
        - 序列生成
        - 趋势外推
    """
    try:
        if "close" not in data.columns:
            logger.warning("seq2seq_prediction_error: 缺少close列，返回零序列")
            return pd.Series(0.0, index=data.index)

        close = data["close"].ffill().fillna(0)
        result = pd.Series(0.0, index=data.index)

        # 计算收益率
        returns = close.pct_change().fillna(0)

        # Seq2Seq状态
        encoder_state = np.zeros(hidden_dim)

        for i in range(encoder_length + decoder_length, len(data)):
            # 编码器：处理输入序列
            encoder_input = returns.iloc[i - encoder_length - decoder_length : i - decoder_length].values

            for t in range(len(encoder_input)):  # pylint: disable=consider-using-enumerate
                x_t = encoder_input[t]
                # 简化的RNN更新
                encoder_state = np.tanh(encoder_state + x_t)

            # 解码器：生成预测序列
            decoder_state = encoder_state.copy()
            predictions = []

            for t in range(decoder_length):
                # 解码器输出
                output = decoder_state.mean()
                predictions.append(output)

                # 更新解码器状态
                decoder_state = np.tanh(decoder_state + output)

            # 实际序列
            actual_sequence = returns.iloc[i - decoder_length : i].values

            # 计算预测误差（MSE）
            if len(predictions) == len(actual_sequence):
                error = np.mean((np.array(predictions) - actual_sequence) ** 2)
                result.iloc[i] = error

        return result

    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.error(f"seq2seq_prediction_error计算失败: {e}")
        return pd.Series(0.0, index=data.index)


def transformer_time_embedding(data: pd.DataFrame, d_model: int = 64, max_len: int = 100) -> pd.Series:
    """Transformer时间嵌入

    白皮书依据: 第四章 4.1.9 - transformer_time_embedding

    使用Transformer的位置编码捕捉时序信息。
    结合正弦和余弦函数编码时间位置。

    Args:
        data: 市场数据，包含close列
        d_model: 模型维度
        max_len: 最大序列长度

    Returns:
        Transformer时间嵌入特征序列

    应用场景:
        - 时间位置编码
        - 周期性捕捉
        - 长序列建模
    """
    try:
        if "close" not in data.columns:
            logger.warning("transformer_time_embedding: 缺少close列，返回零序列")
            return pd.Series(0.0, index=data.index)

        close = data["close"].ffill().fillna(0)
        result = pd.Series(0.0, index=data.index)

        # 计算收益率
        returns = close.pct_change().fillna(0)

        # 位置编码矩阵
        position = np.arange(max_len).reshape(-1, 1)
        div_term = np.exp(np.arange(0, d_model, 2) * -(np.log(10000.0) / d_model))

        pe = np.zeros((max_len, d_model))
        pe[:, 0::2] = np.sin(position * div_term)
        pe[:, 1::2] = np.cos(position * div_term)

        # 应用位置编码
        for i in range(len(data)):
            pos = i % max_len

            # 结合收益率和位置编码
            value_embedding = returns.iloc[i]
            position_embedding = pe[pos, 0]  # 使用第一个维度

            # 融合
            combined_embedding = value_embedding + 0.1 * position_embedding
            result.iloc[i] = combined_embedding

        return result

    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.error(f"transformer_time_embedding计算失败: {e}")
        return pd.Series(0.0, index=data.index)


def nbeats_trend_seasonality(
    data: pd.DataFrame,
    stack_types: Optional[list] = None,
    num_blocks: int = 3,  # pylint: disable=unused-argument
    forecast_length: int = 5,  # pylint: disable=unused-argument
) -> pd.Series:
    """N-BEATS趋势季节性

    白皮书依据: 第四章 4.1.9 - nbeats_trend_seasonality

    使用N-BEATS架构分解趋势和季节性成分。
    通过堆叠块结构实现可解释的时序分解。

    Args:
        data: 市场数据，包含close列
        stack_types: 堆叠类型列表 ['trend', 'seasonality']
        num_blocks: 每个堆叠的块数
        forecast_length: 预测长度

    Returns:
        N-BEATS趋势季节性特征序列

    应用场景:
        - 趋势分解
        - 季节性识别
        - 可解释预测
    """
    try:
        if "close" not in data.columns:
            logger.warning("nbeats_trend_seasonality: 缺少close列，返回零序列")
            return pd.Series(0.0, index=data.index)

        if stack_types is None:
            stack_types = ["trend", "seasonality"]

        close = data["close"].ffill().fillna(0)
        result = pd.Series(0.0, index=data.index)

        # 计算收益率
        returns = close.pct_change().fillna(0)

        # N-BEATS分解
        lookback_window = 20

        for i in range(lookback_window + forecast_length, len(data)):
            # 回溯窗口
            backcast = returns.iloc[i - lookback_window : i].values

            # 趋势堆叠
            trend_component = 0.0
            if "trend" in stack_types:
                # 多项式趋势拟合
                x = np.arange(len(backcast))
                coeffs = np.polyfit(x, backcast, deg=2)
                trend_fit = np.polyval(coeffs, x)
                trend_component = trend_fit[-1]

            # 季节性堆叠
            seasonality_component = 0.0
            if "seasonality" in stack_types:
                # 傅里叶级数季节性
                period = 5  # 假设5日周期
                if len(backcast) >= period:
                    seasonal_pattern = backcast[-period:]
                    seasonality_component = seasonal_pattern.mean()

            # 组合预测
            forecast = trend_component + seasonality_component

            # 实际值
            actual = returns.iloc[i]

            # 残差作为特征
            residual = actual - forecast
            result.iloc[i] = residual

        return result

    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.error(f"nbeats_trend_seasonality计算失败: {e}")
        return pd.Series(0.0, index=data.index)


def deepar_probabilistic_forecast(
    data: pd.DataFrame, hidden_dim: int = 40, num_samples: int = 100, forecast_horizon: int = 1
) -> pd.Series:
    """DeepAR概率预测

    白皮书依据: 第四章 4.1.9 - deepar_probabilistic_forecast

    使用DeepAR进行概率时序预测。
    输出预测分布而非点估计，量化不确定性。

    Args:
        data: 市场数据，包含close列
        hidden_dim: RNN隐藏层维度
        num_samples: 采样数量
        forecast_horizon: 预测步长

    Returns:
        DeepAR概率预测特征序列（预测方差）

    应用场景:
        - 不确定性量化
        - 概率预测
        - 风险评估
    """
    try:
        if "close" not in data.columns:
            logger.warning("deepar_probabilistic_forecast: 缺少close列，返回零序列")
            return pd.Series(0.0, index=data.index)

        close = data["close"].ffill().fillna(0)
        result = pd.Series(0.0, index=data.index)

        # 计算收益率
        returns = close.pct_change().fillna(0)

        # DeepAR状态
        hidden_state = np.zeros(hidden_dim)

        lookback = 20

        for i in range(lookback + forecast_horizon, len(data)):
            # 历史序列
            history = returns.iloc[i - lookback : i].values

            # RNN编码
            for t in range(len(history)):  # pylint: disable=consider-using-enumerate
                x_t = history[t]
                hidden_state = np.tanh(hidden_state + x_t)

            # 预测分布参数（假设高斯分布）
            # mu = f_mu(hidden_state)
            # sigma = f_sigma(hidden_state)
            mu = hidden_state.mean()
            sigma = abs(hidden_state.std()) + 0.01

            # 采样生成预测分布
            samples = np.random.normal(mu, sigma, num_samples)

            # 实际值
            actual = returns.iloc[i]

            # 预测不确定性（方差）作为特征
            prediction_variance = samples.var()

            # 也可以使用预测误差
            prediction_error = abs(actual - mu)

            # 组合特征
            result.iloc[i] = prediction_variance + prediction_error

        return result

    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.error(f"deepar_probabilistic_forecast计算失败: {e}")
        return pd.Series(0.0, index=data.index)
