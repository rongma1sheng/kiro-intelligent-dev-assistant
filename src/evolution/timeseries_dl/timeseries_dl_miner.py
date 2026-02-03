"""时序深度学习因子挖掘器

白皮书依据: 第四章 4.1.9 时序深度学习因子挖掘器

专门针对时间序列数据的深度学习模型，捕捉复杂的时序依赖关系。
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import pandas as pd
from loguru import logger

from ..genetic_miner import EvolutionConfig, GeneticMiner
from . import timeseries_dl_operators


@dataclass
class TimeSeriesDLConfig:  # pylint: disable=too-many-instance-attributes
    """时序深度学习配置

    白皮书依据: 第四章 4.1.9
    """

    # LSTM配置
    lstm_hidden_dim: int = 64
    lstm_sequence_length: int = 20
    lstm_forecast_horizon: int = 1

    # TCN配置
    tcn_kernel_size: int = 3
    tcn_num_filters: int = 32
    tcn_dilation_rates: list = None

    # WaveNet配置
    wavenet_num_layers: int = 4
    wavenet_kernel_size: int = 2

    # 注意力配置
    attention_window: int = 20
    attention_num_heads: int = 4

    # Seq2Seq配置
    seq2seq_encoder_length: int = 20
    seq2seq_decoder_length: int = 5
    seq2seq_hidden_dim: int = 32

    # Transformer配置
    transformer_d_model: int = 64
    transformer_max_len: int = 100

    # N-BEATS配置
    nbeats_stack_types: list = None
    nbeats_num_blocks: int = 3
    nbeats_forecast_length: int = 5

    # DeepAR配置
    deepar_hidden_dim: int = 40
    deepar_num_samples: int = 100
    deepar_forecast_horizon: int = 1

    def __post_init__(self):
        """初始化后处理"""
        if self.tcn_dilation_rates is None:
            self.tcn_dilation_rates = [1, 2, 4, 8]
        if self.nbeats_stack_types is None:
            self.nbeats_stack_types = ["trend", "seasonality"]


class TimeSeriesDeepLearningFactorMiner(GeneticMiner):
    """时序深度学习因子挖掘器

    白皮书依据: 第四章 4.1.9 时序深度学习因子挖掘器

    核心理念: 专门针对时间序列数据的深度学习模型，捕捉复杂的时序依赖关系。

    核心算子库 (8种算子):
    1. lstm_forecast_residual: LSTM预测残差
    2. tcn_temporal_pattern: TCN时序模式
    3. wavenet_receptive_field: WaveNet感受野
    4. attention_temporal_weight: 注意力时序权重
    5. seq2seq_prediction_error: Seq2Seq预测误差
    6. transformer_time_embedding: Transformer时间嵌入
    7. nbeats_trend_seasonality: N-BEATS趋势季节性
    8. deepar_probabilistic_forecast: DeepAR概率预测

    应用场景:
    - 时间序列预测
    - 趋势和季节性识别
    - 波动率预测

    Attributes:
        ts_config: 时序深度学习配置
        ts_operators: 时序DL算子字典
    """

    def __init__(self, config: Optional[EvolutionConfig] = None, ts_config: Optional[TimeSeriesDLConfig] = None):
        """初始化时序深度学习因子挖掘器

        Args:
            config: 遗传算法配置
            ts_config: 时序深度学习配置
        """
        # 初始化基类
        if config is None:
            config = EvolutionConfig()
        super().__init__(config=config)

        # 时序DL配置
        self.ts_config = ts_config or TimeSeriesDLConfig()

        # 注册时序DL算子
        self._register_ts_operators()

        logger.info(f"TimeSeriesDeepLearningFactorMiner初始化完成 - " f"时序DL算子数: {len(self.ts_operators)}")

    def _register_ts_operators(self) -> None:
        """注册时序深度学习算子到遗传算法框架

        白皮书依据: 第四章 4.1.9 - 8种时序DL算子
        """
        self.ts_operators = {
            "lstm_forecast_residual": timeseries_dl_operators.lstm_forecast_residual,
            "tcn_temporal_pattern": timeseries_dl_operators.tcn_temporal_pattern,
            "wavenet_receptive_field": timeseries_dl_operators.wavenet_receptive_field,
            "attention_temporal_weight": timeseries_dl_operators.attention_temporal_weight,
            "seq2seq_prediction_error": timeseries_dl_operators.seq2seq_prediction_error,
            "transformer_time_embedding": timeseries_dl_operators.transformer_time_embedding,
            "nbeats_trend_seasonality": timeseries_dl_operators.nbeats_trend_seasonality,
            "deepar_probabilistic_forecast": timeseries_dl_operators.deepar_probabilistic_forecast,
        }

        # 添加到基类的算子白名单
        if not hasattr(self, "operator_whitelist"):
            self.operator_whitelist = []

        for op_name in self.ts_operators.keys():  # pylint: disable=consider-iterating-dictionary
            if op_name not in self.operator_whitelist:
                self.operator_whitelist.append(op_name)

        logger.info(f"已注册 {len(self.ts_operators)} 个时序深度学习算子")

    async def mine_factors(self, data: pd.DataFrame, returns: pd.Series, generations: int = 10) -> List[Dict[str, Any]]:
        """挖掘时序深度学习因子

        白皮书依据: 第四章 4.1.9

        Args:
            data: 市场数据
            returns: 未来收益率
            generations: 进化代数

        Returns:
            挖掘到的因子列表
        """
        logger.info(f"开始时序深度学习因子挖掘 - 数据形状: {data.shape}, 进化代数: {generations}")

        try:
            # 1. 初始化种群（使用时序DL算子）
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
                    "type": "timeseries_dl",
                    "miner": "TimeSeriesDeepLearningFactorMiner",
                }
                factors.append(factor)

            logger.info(f"时序深度学习因子挖掘完成 - 发现 {len(factors)} 个因子")
            return factors

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"时序深度学习因子挖掘失败: {e}")
            return []

    def analyze_ts_features(self, data: pd.DataFrame) -> Dict[str, Any]:
        """分析时序深度学习特征

        提取和分析各种时序DL特征的统计信息。

        Args:
            data: 市场数据

        Returns:
            时序DL特征分析结果
        """
        try:
            analysis = {
                "lstm": {},
                "tcn": {},
                "wavenet": {},
                "attention": {},
                "seq2seq": {},
                "transformer": {},
                "nbeats": {},
                "deepar": {},
            }

            # 1. LSTM预测残差分析
            lstm_feature = timeseries_dl_operators.lstm_forecast_residual(
                data,
                hidden_dim=self.ts_config.lstm_hidden_dim,
                sequence_length=self.ts_config.lstm_sequence_length,
                forecast_horizon=self.ts_config.lstm_forecast_horizon,
            )
            analysis["lstm"] = {
                "mean_residual": float(lstm_feature.mean()),
                "std_residual": float(lstm_feature.std()),
                "mae": float(lstm_feature.abs().mean()),
                "hidden_dim": self.ts_config.lstm_hidden_dim,
            }

            # 2. TCN时序模式分析
            tcn_feature = timeseries_dl_operators.tcn_temporal_pattern(
                data,
                kernel_size=self.ts_config.tcn_kernel_size,
                num_filters=self.ts_config.tcn_num_filters,
                dilation_rates=self.ts_config.tcn_dilation_rates,
            )
            analysis["tcn"] = {
                "mean": float(tcn_feature.mean()),
                "std": float(tcn_feature.std()),
                "num_filters": self.ts_config.tcn_num_filters,
                "dilation_rates": self.ts_config.tcn_dilation_rates,
            }

            # 3. WaveNet感受野分析
            wavenet_feature = timeseries_dl_operators.wavenet_receptive_field(
                data, num_layers=self.ts_config.wavenet_num_layers, kernel_size=self.ts_config.wavenet_kernel_size
            )
            analysis["wavenet"] = {
                "mean": float(wavenet_feature.mean()),
                "std": float(wavenet_feature.std()),
                "num_layers": self.ts_config.wavenet_num_layers,
                "receptive_field": 2**self.ts_config.wavenet_num_layers * self.ts_config.wavenet_kernel_size,
            }

            # 4. 注意力时序权重分析
            attention_feature = timeseries_dl_operators.attention_temporal_weight(
                data, attention_window=self.ts_config.attention_window, num_heads=self.ts_config.attention_num_heads
            )
            analysis["attention"] = {
                "mean_weight": float(attention_feature.mean()),
                "std_weight": float(attention_feature.std()),
                "num_heads": self.ts_config.attention_num_heads,
            }

            # 5. Seq2Seq预测误差分析
            seq2seq_feature = timeseries_dl_operators.seq2seq_prediction_error(
                data,
                encoder_length=self.ts_config.seq2seq_encoder_length,
                decoder_length=self.ts_config.seq2seq_decoder_length,
                hidden_dim=self.ts_config.seq2seq_hidden_dim,
            )
            analysis["seq2seq"] = {
                "mean_error": float(seq2seq_feature.mean()),
                "std_error": float(seq2seq_feature.std()),
                "encoder_length": self.ts_config.seq2seq_encoder_length,
                "decoder_length": self.ts_config.seq2seq_decoder_length,
            }

            # 6. Transformer时间嵌入分析
            transformer_feature = timeseries_dl_operators.transformer_time_embedding(
                data, d_model=self.ts_config.transformer_d_model, max_len=self.ts_config.transformer_max_len
            )
            analysis["transformer"] = {
                "mean": float(transformer_feature.mean()),
                "std": float(transformer_feature.std()),
                "d_model": self.ts_config.transformer_d_model,
            }

            # 7. N-BEATS趋势季节性分析
            nbeats_feature = timeseries_dl_operators.nbeats_trend_seasonality(
                data,
                stack_types=self.ts_config.nbeats_stack_types,
                num_blocks=self.ts_config.nbeats_num_blocks,
                forecast_length=self.ts_config.nbeats_forecast_length,
            )
            analysis["nbeats"] = {
                "mean_residual": float(nbeats_feature.mean()),
                "std_residual": float(nbeats_feature.std()),
                "stack_types": self.ts_config.nbeats_stack_types,
                "num_blocks": self.ts_config.nbeats_num_blocks,
            }

            # 8. DeepAR概率预测分析
            deepar_feature = timeseries_dl_operators.deepar_probabilistic_forecast(
                data,
                hidden_dim=self.ts_config.deepar_hidden_dim,
                num_samples=self.ts_config.deepar_num_samples,
                forecast_horizon=self.ts_config.deepar_forecast_horizon,
            )
            analysis["deepar"] = {
                "mean_uncertainty": float(deepar_feature.mean()),
                "std_uncertainty": float(deepar_feature.std()),
                "num_samples": self.ts_config.deepar_num_samples,
            }

            logger.info("时序深度学习特征分析完成")
            return analysis

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"时序深度学习特征分析失败: {e}")
            return {}

    def get_ts_model_summary(self) -> Dict[str, Any]:
        """获取时序DL模型摘要

        Returns:
            时序DL模型配置和统计信息
        """
        return {
            "miner_type": "TimeSeriesDeepLearningFactorMiner",
            "num_operators": len(self.ts_operators),
            "operators": list(self.ts_operators.keys()),
            "config": {
                "lstm": {
                    "hidden_dim": self.ts_config.lstm_hidden_dim,
                    "sequence_length": self.ts_config.lstm_sequence_length,
                    "forecast_horizon": self.ts_config.lstm_forecast_horizon,
                },
                "tcn": {
                    "kernel_size": self.ts_config.tcn_kernel_size,
                    "num_filters": self.ts_config.tcn_num_filters,
                    "dilation_rates": self.ts_config.tcn_dilation_rates,
                },
                "wavenet": {
                    "num_layers": self.ts_config.wavenet_num_layers,
                    "kernel_size": self.ts_config.wavenet_kernel_size,
                },
                "attention": {
                    "window": self.ts_config.attention_window,
                    "num_heads": self.ts_config.attention_num_heads,
                },
                "seq2seq": {
                    "encoder_length": self.ts_config.seq2seq_encoder_length,
                    "decoder_length": self.ts_config.seq2seq_decoder_length,
                    "hidden_dim": self.ts_config.seq2seq_hidden_dim,
                },
                "transformer": {
                    "d_model": self.ts_config.transformer_d_model,
                    "max_len": self.ts_config.transformer_max_len,
                },
                "nbeats": {
                    "stack_types": self.ts_config.nbeats_stack_types,
                    "num_blocks": self.ts_config.nbeats_num_blocks,
                    "forecast_length": self.ts_config.nbeats_forecast_length,
                },
                "deepar": {
                    "hidden_dim": self.ts_config.deepar_hidden_dim,
                    "num_samples": self.ts_config.deepar_num_samples,
                    "forecast_horizon": self.ts_config.deepar_forecast_horizon,
                },
            },
        }

    def forecast_sequence(self, data: pd.DataFrame, forecast_horizon: int = 5, method: str = "lstm") -> pd.Series:
        """序列预测

        使用指定的时序DL方法进行多步预测。

        Args:
            data: 市场数据
            forecast_horizon: 预测步长
            method: 预测方法 ('lstm', 'seq2seq', 'nbeats', 'deepar')

        Returns:
            预测序列

        Raises:
            ValueError: 当method不支持时
        """
        if method == "lstm":  # pylint: disable=no-else-return
            return timeseries_dl_operators.lstm_forecast_residual(
                data,
                hidden_dim=self.ts_config.lstm_hidden_dim,
                sequence_length=self.ts_config.lstm_sequence_length,
                forecast_horizon=forecast_horizon,
            )
        elif method == "seq2seq":
            return timeseries_dl_operators.seq2seq_prediction_error(
                data,
                encoder_length=self.ts_config.seq2seq_encoder_length,
                decoder_length=forecast_horizon,
                hidden_dim=self.ts_config.seq2seq_hidden_dim,
            )
        elif method == "nbeats":
            return timeseries_dl_operators.nbeats_trend_seasonality(
                data,
                stack_types=self.ts_config.nbeats_stack_types,
                num_blocks=self.ts_config.nbeats_num_blocks,
                forecast_length=forecast_horizon,
            )
        elif method == "deepar":
            return timeseries_dl_operators.deepar_probabilistic_forecast(
                data,
                hidden_dim=self.ts_config.deepar_hidden_dim,
                num_samples=self.ts_config.deepar_num_samples,
                forecast_horizon=forecast_horizon,
            )
        else:
            raise ValueError(f"不支持的预测方法: {method}")

    def decompose_timeseries(self, data: pd.DataFrame) -> Dict[str, pd.Series]:
        """时序分解

        使用N-BEATS分解趋势和季节性成分。

        Args:
            data: 市场数据

        Returns:
            分解后的成分字典
        """
        try:
            # 使用N-BEATS进行分解
            residual = timeseries_dl_operators.nbeats_trend_seasonality(
                data,
                stack_types=["trend", "seasonality"],
                num_blocks=self.ts_config.nbeats_num_blocks,
                forecast_length=self.ts_config.nbeats_forecast_length,
            )

            # 计算原始序列
            if "close" in data.columns:  # pylint: disable=no-else-return
                close = data["close"].ffill().fillna(0)
                returns = close.pct_change().fillna(0)

                # 简化的分解（实际应该更复杂）
                trend = returns.rolling(window=20, min_periods=1).mean()
                seasonality = returns - trend

                return {"trend": trend, "seasonality": seasonality, "residual": residual}
            else:
                return {"residual": residual}

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"时序分解失败: {e}")
            return {}

    def quantify_uncertainty(self, data: pd.DataFrame) -> pd.Series:
        """量化预测不确定性

        使用DeepAR量化预测的不确定性。

        Args:
            data: 市场数据

        Returns:
            不确定性序列
        """
        try:
            uncertainty = timeseries_dl_operators.deepar_probabilistic_forecast(
                data,
                hidden_dim=self.ts_config.deepar_hidden_dim,
                num_samples=self.ts_config.deepar_num_samples,
                forecast_horizon=self.ts_config.deepar_forecast_horizon,
            )

            logger.info(f"不确定性量化完成 - 平均不确定性: {uncertainty.mean():.4f}")
            return uncertainty

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"不确定性量化失败: {e}")
            return pd.Series(0.0, index=data.index)
