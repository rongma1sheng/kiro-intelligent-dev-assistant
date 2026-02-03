"""主力雷达 - 高频Tick数据分析

白皮书依据: 第二章 2.3 Algo Hunter (主力雷达)
"""

import asyncio
import time
from pathlib import Path
from typing import Any, Dict, Optional

import numpy as np
from loguru import logger

from src.infra.event_bus import EventBus, EventPriority, EventType


class AlgoHunter:
    """主力雷达 - 高频Tick数据分析

    白皮书依据: 第二章 2.3 Algo Hunter (主力雷达)

    核心功能：
    1. 加载和管理深度学习模型(1D-CNN/TST)
    2. 实时处理高频Tick数据
    3. 推理主力资金行为概率
    4. 发布检测结果到EventBus

    Attributes:
        model: 深度学习模型实例
        model_type: 模型类型 ('1d_cnn' 或 'tst')
        device: 计算设备 ('cuda' 或 'cpu')
        event_bus: 事件总线
        inference_stats: 推理统计信息
    """

    def __init__(  # pylint: disable=too-many-positional-arguments
        self,
        model_type: str = "1d_cnn",
        model_path: Optional[str] = None,
        device: str = "cuda",
        event_bus: Optional[EventBus] = None,
        enable_mixed_precision: bool = True,
        enable_model_compile: bool = True,
        batch_size: int = 1,
    ):
        """初始化主力雷达

        Args:
            model_type: 模型类型，支持 '1d_cnn' 或 'tst'
            model_path: 模型文件路径，None则使用默认模型
            device: 计算设备，'cuda' 或 'cpu'
            event_bus: 事件总线实例，用于事件驱动通信
            enable_mixed_precision: 是否启用混合精度推理（FP16）
            enable_model_compile: 是否启用模型编译优化
            batch_size: 批处理大小，默认1

        Raises:
            ValueError: 当model_type不支持时
            FileNotFoundError: 当model_path不存在时
            RuntimeError: 当模型加载失败时
        """
        # 参数验证
        if model_type not in ["1d_cnn", "tst"]:
            raise ValueError(f"model_type必须是'1d_cnn'或'tst'，当前: {model_type}")

        if device not in ["cuda", "cpu"]:
            raise ValueError(f"device必须是'cuda'或'cpu'，当前: {device}")

        if batch_size < 1:
            raise ValueError(f"batch_size必须≥1，当前: {batch_size}")

        # 初始化属性
        self.model_type: str = model_type
        self.device: str = device
        self.event_bus: Optional[EventBus] = event_bus
        self.enable_mixed_precision: bool = enable_mixed_precision
        self.enable_model_compile: bool = enable_model_compile
        self.batch_size: int = batch_size

        # 推理统计
        self.inference_stats: Dict[str, Any] = {
            "total_inferences": 0,
            "total_latency_ms": 0.0,
            "avg_latency_ms": 0.0,
            "p99_latency_ms": 0.0,
            "latency_history": [],
            "failed_inferences": 0,
            "batch_inferences": 0,
        }

        # 加载模型
        self.model: Optional[Any] = None
        self.model_path: Optional[str] = model_path

        # 批处理队列
        self._batch_queue: list = []
        self._batch_lock: Optional[asyncio.Lock] = None

        try:
            self._load_model()
            logger.info(
                f"AlgoHunter初始化完成: "
                f"model_type={model_type}, "
                f"device={device}, "
                f"model_path={model_path}, "
                f"mixed_precision={enable_mixed_precision}, "
                f"model_compile={enable_model_compile}, "
                f"batch_size={batch_size}"
            )
        except Exception as e:
            logger.error(f"AlgoHunter初始化失败: {e}")
            raise RuntimeError(f"模型加载失败: {e}") from e

    def _load_model(self) -> None:
        """加载深度学习模型

        白皮书依据: 第二章 2.3 Algo Hunter (主力雷达)

        性能优化:
        1. 混合精度推理（FP16）- 减少内存占用，提升推理速度
        2. 模型编译优化 - 使用torch.compile加速
        3. GPU内存优化 - 使用channels_last内存格式

        Raises:
            FileNotFoundError: 当模型文件不存在时
            RuntimeError: 当模型加载失败时
        """
        try:
            # 尝试导入PyTorch
            import torch  # pylint: disable=import-outside-toplevel

            # 检查设备可用性
            if self.device == "cuda" and not torch.cuda.is_available():
                logger.warning("CUDA不可用，切换到CPU")
                self.device = "cpu"
                self.enable_mixed_precision = False  # CPU不支持混合精度

            # 如果提供了模型路径，验证文件存在
            if self.model_path is not None:
                model_file = Path(self.model_path)
                if not model_file.exists():
                    raise FileNotFoundError(f"模型文件不存在: {self.model_path}")

                # 加载模型
                logger.info(f"从文件加载模型: {self.model_path}")
                self.model = torch.load(self.model_path, map_location=self.device)
            else:
                # 使用默认模型架构
                logger.info(f"创建默认{self.model_type}模型")
                if self.model_type == "1d_cnn":
                    self.model = self._create_1d_cnn_model()
                else:  # tst
                    self.model = self._create_tst_model()

            # 将模型移到指定设备
            self.model = self.model.to(self.device)
            self.model.eval()  # 设置为评估模式

            # GPU内存优化：使用channels_last内存格式
            if self.device == "cuda" and self.model_type == "1d_cnn":
                try:
                    self.model = self.model.to(memory_format=torch.channels_last)
                    logger.info("启用channels_last内存格式")
                except Exception as e:  # pylint: disable=broad-exception-caught
                    logger.warning(f"无法启用channels_last: {e}")

            # 混合精度优化
            if self.enable_mixed_precision and self.device == "cuda":
                try:
                    self.model = self.model.half()  # 转换为FP16
                    logger.info("启用混合精度推理（FP16）")
                except Exception as e:  # pylint: disable=broad-exception-caught
                    logger.warning(f"无法启用混合精度: {e}")
                    self.enable_mixed_precision = False

            # 模型编译优化（PyTorch 2.0+）- 仅在CUDA设备上启用
            # Windows上CPU模式下torch.compile可能需要C++编译器
            if self.enable_model_compile and self.device == "cuda":
                try:
                    if hasattr(torch, "compile"):
                        self.model = torch.compile(self.model, mode="reduce-overhead")  # 优化推理延迟
                        logger.info("启用模型编译优化（torch.compile）")
                    else:
                        logger.warning("PyTorch版本不支持torch.compile")
                        self.enable_model_compile = False
                except Exception as e:  # pylint: disable=broad-exception-caught
                    logger.warning(f"模型编译失败: {e}")
                    self.enable_model_compile = False
            elif self.enable_model_compile and self.device == "cpu":
                logger.info("CPU模式下禁用torch.compile以避免编译器依赖")
                self.enable_model_compile = False

            # 模型预热
            self._warmup_model()

            logger.info(
                f"模型加载成功: {self.model_type} on {self.device}, "
                f"优化: mixed_precision={self.enable_mixed_precision}, "
                f"compile={self.enable_model_compile}"
            )

        except ImportError:
            logger.warning("PyTorch未安装，使用模拟模型")
            self.model = None
            self.device = "cpu"
        except Exception as e:
            logger.error(f"模型加载失败: {e}")
            raise RuntimeError(f"无法加载模型: {e}") from e

    def _create_1d_cnn_model(self) -> Any:
        """创建1D-CNN模型

        Returns:
            1D-CNN模型实例
        """
        import torch.nn as nn  # pylint: disable=import-outside-toplevel,r0402

        class CNN1D(nn.Module):
            """简单的1D-CNN模型

            使用全局平均池化处理可变长度输入
            """

            def __init__(self):
                super().__init__()
                self.conv1 = nn.Conv1d(in_channels=5, out_channels=32, kernel_size=3)
                self.conv2 = nn.Conv1d(in_channels=32, out_channels=64, kernel_size=3)
                self.pool = nn.MaxPool1d(kernel_size=2)

                # 使用全局平均池化，输出固定为64维
                self.global_pool = nn.AdaptiveAvgPool1d(1)

                # 全连接层输入固定为64
                self.fc1 = nn.Linear(64, 128)
                self.fc2 = nn.Linear(128, 1)
                self.relu = nn.ReLU()
                self.sigmoid = nn.Sigmoid()

            def forward(self, x):
                # x shape: (batch, 5, seq_len)
                x = self.relu(self.conv1(x))  # (batch, 32, seq_len-2)
                x = self.pool(x)  # (batch, 32, (seq_len-2)//2)
                x = self.relu(self.conv2(x))  # (batch, 64, (seq_len-2)//2-2)
                x = self.pool(x)  # (batch, 64, ((seq_len-2)//2-2)//2)

                # 全局平均池化
                x = self.global_pool(x)  # (batch, 64, 1)
                x = x.view(x.size(0), -1)  # (batch, 64)

                # 全连接层
                x = self.relu(self.fc1(x))
                x = self.sigmoid(self.fc2(x))
                return x

        return CNN1D()

    def _create_tst_model(self) -> Any:
        """创建TST(Transformer)模型

        Returns:
            TST模型实例
        """
        import torch.nn as nn  # pylint: disable=import-outside-toplevel,r0402

        class TST(nn.Module):
            """简单的Transformer模型"""

            def __init__(self):
                super().__init__()
                self.embedding = nn.Linear(5, 64)
                encoder_layer = nn.TransformerEncoderLayer(d_model=64, nhead=4, dim_feedforward=256, batch_first=True)
                self.transformer = nn.TransformerEncoder(encoder_layer, num_layers=2)
                self.fc = nn.Linear(64, 1)
                self.sigmoid = nn.Sigmoid()

            def forward(self, x):
                # x shape: (batch, seq_len, features)
                x = self.embedding(x)
                x = self.transformer(x)
                x = x.mean(dim=1)  # 全局平均池化
                x = self.sigmoid(self.fc(x))
                return x

        return TST()

    def _warmup_model(self) -> None:
        """模型预热

        白皮书依据: 第二章 2.3 Algo Hunter (主力雷达)
        性能要求: P99延迟<20ms

        性能优化:
        1. 多次预热推理，确保CUDA kernel完全初始化
        2. 使用不同输入大小预热，覆盖常见场景
        3. 清理GPU缓存，确保稳定性能
        """
        if self.model is None:
            return

        try:
            import torch  # pylint: disable=import-outside-toplevel

            logger.info("开始模型预热...")

            # 预热不同大小的输入
            warmup_sizes = [50, 100, 200]

            for size in warmup_sizes:
                # 创建虚拟输入
                if self.model_type == "1d_cnn":
                    dummy_input = torch.randn(1, 5, size).to(self.device)
                    if self.enable_mixed_precision:
                        dummy_input = dummy_input.half()
                else:  # tst
                    dummy_input = torch.randn(1, size, 5).to(self.device)
                    if self.enable_mixed_precision:
                        dummy_input = dummy_input.half()

                # 预热推理（多次）
                with torch.no_grad():
                    for _ in range(20):  # 增加预热次数
                        _ = self.model(dummy_input)

                # 同步CUDA操作
                if self.device == "cuda":
                    torch.cuda.synchronize()

            # 清理GPU缓存
            if self.device == "cuda":
                torch.cuda.empty_cache()

            logger.info("模型预热完成")

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.warning(f"模型预热失败: {e}")

    async def detect_main_force(self, tick_data: np.ndarray) -> float:
        """检测主力资金行为

        白皮书依据: 第二章 2.3 Algo Hunter (主力雷达)

        Args:
            tick_data: Tick数据，shape: (sequence_length, features)

        Returns:
            主力概率，范围 [0.0, 1.0]

        Raises:
            ValueError: 当tick_data形状不正确时
            RuntimeError: 当模型推理失败时
        """
        # 验证输入形状
        if tick_data.ndim != 2:
            raise ValueError(f"tick_data必须是2维数组，当前: {tick_data.ndim}维")

        if tick_data.shape[1] != 5:
            raise ValueError(f"tick_data特征维度必须是5，当前: {tick_data.shape[1]}")

        # 验证最小序列长度
        # 1D-CNN需要至少10个时间步（经过两次卷积和池化后仍有足够数据）
        # TST模型没有严格限制，但建议至少5个时间步
        min_seq_length = 10 if self.model_type == "1d_cnn" else 5
        if tick_data.shape[0] < min_seq_length:
            raise ValueError(f"序列长度必须≥{min_seq_length}，当前: {tick_data.shape[0]}")

        try:
            # 记录开始时间
            start_time = time.perf_counter()

            # 预处理数据
            input_tensor = await self._preprocess_tick_data(tick_data)

            # 模型推理
            probability = await self._model_inference(input_tensor)

            # 记录延迟
            latency_ms = (time.perf_counter() - start_time) * 1000
            self._update_inference_stats(latency_ms, success=True)

            # 发布检测事件
            if self.event_bus is not None:
                await self._publish_detection_event(probability, tick_data)

            logger.debug(f"主力检测完成: probability={probability:.4f}, " f"latency={latency_ms:.2f}ms")

            return probability

        except Exception as e:
            self._update_inference_stats(0.0, success=False)
            logger.error(f"主力检测失败: {e}")
            raise RuntimeError(f"模型推理失败: {e}") from e

    async def _preprocess_tick_data(self, tick_data: np.ndarray) -> Any:
        """预处理Tick数据

        标准化、归一化等预处理操作

        白皮书依据: 第二章 2.3 Algo Hunter (主力雷达)

        性能优化:
        1. 使用numpy向量化操作
        2. 避免不必要的数据复制
        3. 支持混合精度

        Args:
            tick_data: 原始Tick数据，shape: (sequence_length, features)

        Returns:
            预处理后的张量
        """
        if self.model is None:
            # 模拟模式，返回numpy数组
            # 标准化
            mean = tick_data.mean(axis=0, keepdims=True)
            std = tick_data.std(axis=0, keepdims=True) + 1e-8
            normalized = (tick_data - mean) / std
            return normalized

        try:
            import torch  # pylint: disable=import-outside-toplevel

            # 标准化（向量化操作）
            mean = tick_data.mean(axis=0, keepdims=True)
            std = tick_data.std(axis=0, keepdims=True) + 1e-8
            normalized = (tick_data - mean) / std

            # 转换为张量（避免复制）
            tensor = torch.from_numpy(normalized).float()

            # 调整形状以匹配模型输入
            if self.model_type == "1d_cnn":
                # CNN需要 (batch, channels, seq_len)
                tensor = tensor.transpose(0, 1).unsqueeze(0)
            else:  # tst
                # Transformer需要 (batch, seq_len, features)
                tensor = tensor.unsqueeze(0)

            # 移到设备
            tensor = tensor.to(self.device, non_blocking=True)  # 异步传输

            # 混合精度 - 只在CUDA设备上启用
            if self.enable_mixed_precision and self.device == "cuda":
                tensor = tensor.half()

            return tensor

        except Exception as e:
            logger.error(f"数据预处理失败: {e}")
            raise

    async def _model_inference(self, input_tensor: Any) -> float:
        """模型推理

        白皮书依据: 第二章 2.3 Algo Hunter (主力雷达)
        性能要求: P99延迟<20ms

        性能优化:
        1. 使用torch.no_grad()减少内存占用
        2. 使用torch.cuda.synchronize()确保准确计时
        3. 避免CPU-GPU数据传输

        Args:
            input_tensor: 输入张量

        Returns:
            主力概率，范围 [0.0, 1.0]
        """
        if self.model is None:
            # 模拟模式，返回随机概率
            return float(np.random.random())

        try:
            import torch  # pylint: disable=import-outside-toplevel

            # 推理
            with torch.no_grad():
                output = self.model(input_tensor)

                # 同步CUDA操作（确保推理完成）
                if self.device == "cuda":
                    torch.cuda.synchronize()

                probability = output.item()

            # 确保在[0, 1]范围内
            probability = max(0.0, min(1.0, probability))

            return probability

        except Exception as e:
            logger.error(f"模型推理失败: {e}")
            raise

    async def detect_main_force_batch(self, tick_data_list: list[np.ndarray]) -> list[float]:
        """批量检测主力资金行为

        白皮书依据: 第二章 2.3 Algo Hunter (主力雷达)
        性能优化: 批处理推理，提升吞吐量

        Args:
            tick_data_list: Tick数据列表，每个元素shape: (sequence_length, features)

        Returns:
            主力概率列表，每个元素范围 [0.0, 1.0]

        Raises:
            ValueError: 当输入数据不合法时
            RuntimeError: 当批处理推理失败时
        """
        if not tick_data_list:
            return []

        try:
            # 记录开始时间
            start_time = time.perf_counter()

            # 预处理所有数据
            input_tensors = []
            for tick_data in tick_data_list:
                # 验证输入
                if tick_data.ndim != 2 or tick_data.shape[1] != 5:
                    raise ValueError(f"tick_data必须是(seq_len, 5)形状，当前: {tick_data.shape}")

                tensor = await self._preprocess_tick_data(tick_data)
                input_tensors.append(tensor)

            # 批处理推理
            if self.model is None:
                # 模拟模式
                probabilities = [float(np.random.random()) for _ in tick_data_list]
            else:
                import torch  # pylint: disable=import-outside-toplevel

                # 合并为批次
                batch_tensor = torch.cat(input_tensors, dim=0)

                # 推理
                with torch.no_grad():
                    outputs = self.model(batch_tensor)

                    if self.device == "cuda":
                        torch.cuda.synchronize()

                    probabilities = outputs.squeeze().tolist()

                    # 确保是列表
                    if not isinstance(probabilities, list):
                        probabilities = [probabilities]

            # 记录延迟
            latency_ms = (time.perf_counter() - start_time) * 1000
            self._update_inference_stats(latency_ms / len(tick_data_list), success=True)  # 平均每个样本的延迟
            self.inference_stats["batch_inferences"] += 1

            logger.debug(
                f"批量主力检测完成: batch_size={len(tick_data_list)}, "
                f"total_latency={latency_ms:.2f}ms, "
                f"avg_latency={latency_ms/len(tick_data_list):.2f}ms"
            )

            return probabilities

        except Exception as e:
            self._update_inference_stats(0.0, success=False)
            logger.error(f"批量主力检测失败: {e}")
            raise RuntimeError(f"批处理推理失败: {e}") from e

    async def _publish_detection_event(self, probability: float, tick_data: np.ndarray) -> None:
        """发布检测结果事件

        白皮书依据: 第二章 2.3 Algo Hunter (主力雷达)
        Requirements: 6.1 (事件驱动通信)

        Args:
            probability: 主力概率
            tick_data: 原始Tick数据
        """
        if self.event_bus is None:
            return

        try:
            await self.event_bus.publish_simple(
                event_type=EventType.ANALYSIS_COMPLETED,
                source_module="algo_hunter",
                data={
                    "action": "main_force_detection",
                    "probability": probability,
                    "timestamp": time.time(),
                    "data_shape": tick_data.shape,
                    "model_type": self.model_type,
                    "device": self.device,
                },
                priority=EventPriority.HIGH,
            )

            logger.debug(f"发布主力检测事件: probability={probability:.4f}")

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.warning(f"发布检测事件失败: {e}")

    def _update_inference_stats(self, latency_ms: float, success: bool) -> None:
        """更新推理统计信息

        Args:
            latency_ms: 推理延迟（毫秒）
            success: 是否成功
        """
        self.inference_stats["total_inferences"] += 1

        if success:
            self.inference_stats["total_latency_ms"] += latency_ms
            self.inference_stats["latency_history"].append(latency_ms)

            # 保持最近1000次记录
            if len(self.inference_stats["latency_history"]) > 1000:
                self.inference_stats["latency_history"].pop(0)

            # 更新平均延迟
            self.inference_stats["avg_latency_ms"] = (
                self.inference_stats["total_latency_ms"] / self.inference_stats["total_inferences"]
            )

            # 更新P99延迟
            if self.inference_stats["latency_history"]:
                sorted_latencies = sorted(self.inference_stats["latency_history"])
                p99_index = int(len(sorted_latencies) * 0.99)
                self.inference_stats["p99_latency_ms"] = sorted_latencies[p99_index]
        else:
            self.inference_stats["failed_inferences"] += 1

    def get_inference_stats(self) -> Dict[str, Any]:
        """获取推理统计信息

        白皮书依据: 第二章 2.3 Algo Hunter (主力雷达)

        Returns:
            包含以下信息的统计：
            - total_inferences: 总推理次数
            - avg_latency_ms: 平均延迟（毫秒）
            - p99_latency_ms: P99延迟（毫秒）
            - failed_inferences: 失败次数
            - success_rate: 成功率
            - batch_inferences: 批处理推理次数
            - optimizations: 启用的优化项
        """
        total = self.inference_stats["total_inferences"]
        failed = self.inference_stats["failed_inferences"]

        return {
            "total_inferences": total,
            "avg_latency_ms": self.inference_stats["avg_latency_ms"],
            "p99_latency_ms": self.inference_stats["p99_latency_ms"],
            "failed_inferences": failed,
            "success_rate": (total - failed) / total if total > 0 else 0.0,
            "batch_inferences": self.inference_stats["batch_inferences"],
            "model_type": self.model_type,
            "device": self.device,
            "optimizations": {
                "mixed_precision": self.enable_mixed_precision,
                "model_compile": self.enable_model_compile,
                "batch_size": self.batch_size,
            },
        }
