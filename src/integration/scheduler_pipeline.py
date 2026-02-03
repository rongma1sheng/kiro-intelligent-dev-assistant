"""调度器与数据管道集成

白皮书依据: 第三章 3.1 高性能数据管道 + 第一章 1.1 多时间尺度统一调度

实现调度器驱动的数据处理，支持任务间数据传递和统一错误处理。
"""

import time
from dataclasses import dataclass, field
from threading import Lock
from typing import Any, Callable, Dict, List, Optional

from loguru import logger

from src.chronos.scheduler import ChronosScheduler, Priority, TimeScale
from src.infra.pipeline import DataPipeline, DataProcessor, DataSink, DataSource


@dataclass
class PipelineTask:
    """管道任务配置

    白皮书依据: 第三章 3.1 高性能数据管道

    封装数据管道的配置信息，用于调度器管理。

    Attributes:
        pipeline_id: 管道唯一标识
        name: 管道名称
        pipeline: 数据管道实例
        enabled: 是否启用
        execution_count: 执行次数
        last_execution_time: 上次执行时间
        last_error: 上次执行错误
        performance_metrics: 性能指标
    """

    pipeline_id: str
    name: str
    pipeline: DataPipeline
    enabled: bool = True
    execution_count: int = field(default=0, init=False)
    last_execution_time: Optional[float] = field(default=None, init=False)
    last_error: Optional[str] = field(default=None, init=False)
    performance_metrics: Dict[str, float] = field(default_factory=dict, init=False)


class ScheduledPipelineManager:
    """调度管道管理器

    白皮书依据: 第三章 3.1 高性能数据管道 + 第一章 1.1 多时间尺度统一调度

    集成Chronos调度器和数据管道，实现调度器驱动的数据处理。
    支持任务间数据传递、统一错误处理、性能监控等功能。

    Attributes:
        scheduler: Chronos调度器实例
        pipelines: 管道任务字典
        data_store: 任务间数据存储
        error_handlers: 错误处理器字典
        lock: 线程锁

    Performance:
        调度延迟: < 1ms (P99)
        数据处理延迟: < 10ms (P99)

    Example:
        >>> manager = ScheduledPipelineManager()
        >>> pipeline_id = manager.add_pipeline(
        ...     name="tick_data_processing",
        ...     source=TickDataSource(),
        ...     processors=[DataSanitizer()],
        ...     sink=DatabaseSink(),
        ...     interval=1.0,
        ...     priority=Priority.HIGH
        ... )
        >>> manager.start()
    """

    def __init__(self):
        """初始化调度管道管理器"""
        self.scheduler = ChronosScheduler()
        self.pipelines: Dict[str, PipelineTask] = {}
        self.data_store: Dict[str, Any] = {}
        self.error_handlers: Dict[str, Callable[[Exception, str], None]] = {}
        self.lock = Lock()

        # 注册默认错误处理器
        self.error_handlers["default"] = self._default_error_handler

        logger.info("ScheduledPipelineManager initialized")

    def add_pipeline(  # pylint: disable=too-many-positional-arguments
        self,
        name: str,
        source: DataSource,
        processors: List[DataProcessor],
        sink: DataSink,
        interval: float,
        priority: Priority = Priority.NORMAL,
        time_scale: TimeScale = TimeScale.SECOND,
        dependencies: Optional[List[str]] = None,
        backpressure_enabled: bool = True,
        error_handler: Optional[str] = None,
    ) -> str:
        """添加调度管道

        白皮书依据: 第三章 3.1 高性能数据管道

        Args:
            name: 管道名称
            source: 数据源
            processors: 数据处理器列表
            sink: 数据接收器
            interval: 执行间隔
            priority: 任务优先级
            time_scale: 时间尺度
            dependencies: 依赖的管道ID列表
            backpressure_enabled: 是否启用背压控制
            error_handler: 错误处理器名称

        Returns:
            管道ID

        Raises:
            ValueError: 当参数不合法时
        """
        if not name:
            raise ValueError("管道名称不能为空")

        if not source:
            raise ValueError("数据源不能为空")

        if not sink:
            raise ValueError("数据接收器不能为空")

        # 创建数据管道
        pipeline = DataPipeline(
            source=source, processors=processors or [], sink=sink, backpressure_enabled=backpressure_enabled
        )

        # 生成管道ID
        pipeline_id = f"{name}_{int(time.time() * 1000000)}"

        # 创建管道任务
        pipeline_task = PipelineTask(pipeline_id=pipeline_id, name=name, pipeline=pipeline)

        # 创建执行回调
        def pipeline_callback():
            self._execute_pipeline(pipeline_id, error_handler or "default")

        # 添加到调度器
        task_id = self.scheduler.add_task(  # pylint: disable=unused-variable
            name=f"pipeline_{name}",
            callback=pipeline_callback,
            interval=interval,
            priority=priority,
            time_scale=time_scale,
            dependencies=dependencies,
        )

        # 存储管道任务
        with self.lock:
            self.pipelines[pipeline_id] = pipeline_task

        logger.info(
            f"Pipeline added: {name} (id={pipeline_id}, "
            f"interval={interval}{time_scale.value}, priority={priority.name})"
        )

        return pipeline_id

    def remove_pipeline(self, pipeline_id: str) -> bool:
        """移除调度管道

        Args:
            pipeline_id: 管道ID

        Returns:
            是否移除成功
        """
        with self.lock:
            if pipeline_id not in self.pipelines:
                return False

            pipeline_task = self.pipelines.pop(pipeline_id)

            # 从调度器中移除对应的任务
            # 注意：这里需要根据任务名称查找，实际实现中可能需要维护task_id映射
            logger.info(f"Pipeline removed: {pipeline_task.name} (id={pipeline_id})")
            return True

    def start(self) -> None:
        """启动调度管道管理器

        Raises:
            RuntimeError: 当管理器已经运行时
        """
        self.scheduler.start()
        logger.info("ScheduledPipelineManager started")

    def stop(self) -> None:
        """停止调度管道管理器"""
        self.scheduler.stop()
        logger.info("ScheduledPipelineManager stopped")

    def get_pipeline_info(self, pipeline_id: str) -> Optional[Dict[str, Any]]:
        """获取管道信息

        Args:
            pipeline_id: 管道ID

        Returns:
            管道信息字典，不存在时返回None
        """
        with self.lock:
            pipeline_task = self.pipelines.get(pipeline_id)
            if not pipeline_task:
                return None

            return {
                "pipeline_id": pipeline_task.pipeline_id,
                "name": pipeline_task.name,
                "enabled": pipeline_task.enabled,
                "execution_count": pipeline_task.execution_count,
                "last_execution_time": pipeline_task.last_execution_time,
                "last_error": pipeline_task.last_error,
                "performance_metrics": pipeline_task.performance_metrics.copy(),
            }

    def get_all_pipelines_info(self) -> Dict[str, Dict[str, Any]]:
        """获取所有管道信息

        Returns:
            所有管道信息字典
        """
        with self.lock:
            return {
                pipeline_id: self.get_pipeline_info(pipeline_id)
                for pipeline_id in self.pipelines.keys()  # pylint: disable=consider-iterating-dictionary
            }  # pylint: disable=consider-iterating-dictionary

    def set_data(self, key: str, value: Any) -> None:
        """设置任务间共享数据

        Args:
            key: 数据键
            value: 数据值
        """
        with self.lock:
            self.data_store[key] = value

    def get_data(self, key: str, default: Any = None) -> Any:
        """获取任务间共享数据

        Args:
            key: 数据键
            default: 默认值

        Returns:
            数据值
        """
        with self.lock:
            return self.data_store.get(key, default)

    def register_error_handler(self, name: str, handler: Callable[[Exception, str], None]) -> None:
        """注册错误处理器

        Args:
            name: 处理器名称
            handler: 错误处理函数，接收(异常, 管道ID)参数
        """
        self.error_handlers[name] = handler
        logger.info(f"Error handler registered: {name}")

    def _execute_pipeline(self, pipeline_id: str, error_handler_name: str) -> None:
        """执行管道（内部方法）

        Args:
            pipeline_id: 管道ID
            error_handler_name: 错误处理器名称
        """
        with self.lock:
            pipeline_task = self.pipelines.get(pipeline_id)
            if not pipeline_task or not pipeline_task.enabled:
                return

        start_time = time.perf_counter()

        try:
            # 执行单次数据处理（而不是运行整个管道）
            pipeline = pipeline_task.pipeline

            # 读取数据
            data = pipeline.source.read()
            if data is None:
                # 没有数据可处理
                return

            # 处理数据
            processed_data = data
            for processor in pipeline.processors:
                processed_data = processor.process(processed_data)

            # 写入数据
            pipeline.sink.write(processed_data)

            # 更新执行统计
            elapsed = time.perf_counter() - start_time

            with self.lock:
                pipeline_task.execution_count += 1
                pipeline_task.last_execution_time = time.time()
                pipeline_task.last_error = None
                pipeline_task.performance_metrics.update(
                    {
                        "last_execution_time_ms": elapsed * 1000,
                        "average_execution_time_ms": (
                            pipeline_task.performance_metrics.get("average_execution_time_ms", 0)
                            * (pipeline_task.execution_count - 1)
                            + elapsed * 1000
                        )
                        / pipeline_task.execution_count,
                    }
                )

            logger.debug(
                f"Pipeline executed: {pipeline_task.name} "
                f"(elapsed={elapsed*1000:.2f}ms, count={pipeline_task.execution_count})"
            )

        except Exception as e:  # pylint: disable=broad-exception-caught
            # 记录错误
            with self.lock:
                pipeline_task.last_error = str(e)

            # 调用错误处理器
            error_handler = self.error_handlers.get(error_handler_name, self._default_error_handler)
            error_handler(e, pipeline_id)

            logger.error(f"Pipeline execution failed: {pipeline_task.name} " f"(id={pipeline_id}), error={e}")

    def _default_error_handler(self, error: Exception, pipeline_id: str) -> None:
        """默认错误处理器（内部方法）

        Args:
            error: 异常对象
            pipeline_id: 管道ID
        """
        # 默认错误处理：记录日志，不中断调度
        logger.error(f"Pipeline error in {pipeline_id}: {error}")

        # 可以在这里添加更多错误处理逻辑，如：
        # - 发送告警通知
        # - 记录到错误数据库
        # - 触发故障恢复流程
        # - 暂时禁用出错的管道


class DataPassingSource(DataSource):
    """数据传递源

    白皮书依据: 第三章 3.1 高性能数据管道

    用于任务间数据传递的数据源，从共享数据存储中读取数据。
    """

    def __init__(self, manager: ScheduledPipelineManager, data_key: str):
        """初始化数据传递源

        Args:
            manager: 调度管道管理器
            data_key: 数据键
        """
        self.manager = manager
        self.data_key = data_key

    def read(self):
        """读取数据

        Returns:
            从共享存储中读取的数据
        """
        return self.manager.get_data(self.data_key)


class DataPassingSink(DataSink):
    """数据传递接收器

    白皮书依据: 第三章 3.1 高性能数据管道

    用于任务间数据传递的数据接收器，将数据写入共享数据存储。
    """

    def __init__(self, manager: ScheduledPipelineManager, data_key: str):
        """初始化数据传递接收器

        Args:
            manager: 调度管道管理器
            data_key: 数据键
        """
        self.manager = manager
        self.data_key = data_key

    def write(self, data) -> None:
        """写入数据

        Args:
            data: 要写入的数据
        """
        self.manager.set_data(self.data_key, data)


# 便利函数


def create_data_processing_chain(manager: ScheduledPipelineManager, chain_config: List[Dict[str, Any]]) -> List[str]:
    """创建数据处理链

    白皮书依据: 第三章 3.1 高性能数据管道

    Args:
        manager: 调度管道管理器
        chain_config: 处理链配置列表

    Returns:
        管道ID列表

    Example:
        >>> chain_config = [
        ...     {
        ...         'name': 'data_ingestion',
        ...         'source': TickDataSource(),
        ...         'processors': [DataValidator()],
        ...         'sink': DataPassingSink(manager, 'raw_data'),
        ...         'interval': 1.0,
        ...         'priority': Priority.HIGH
        ...     },
        ...     {
        ...         'name': 'data_processing',
        ...         'source': DataPassingSource(manager, 'raw_data'),
        ...         'processors': [DataSanitizer(), DataEnricher()],
        ...         'sink': DataPassingSink(manager, 'processed_data'),
        ...         'interval': 5.0,
        ...         'priority': Priority.NORMAL,
        ...         'dependencies': ['data_ingestion']
        ...     }
        ... ]
        >>> pipeline_ids = create_data_processing_chain(manager, chain_config)
    """
    pipeline_ids = []
    task_names = []  # 记录任务名称用于依赖关系

    for i, config in enumerate(chain_config):
        # 记录当前任务名称
        task_name = config["name"]
        task_names.append(task_name)

        # 设置依赖关系（使用任务名称而不是管道ID）
        if i > 0 and "dependencies" not in config:
            # 默认依赖前一个任务
            prev_task_name = task_names[i - 1]
            config["dependencies"] = [f"pipeline_{prev_task_name}"]
        elif "dependencies" in config:
            # 转换依赖名称为任务名称格式
            config["dependencies"] = [f"pipeline_{dep}" for dep in config["dependencies"]]

        # 添加管道
        pipeline_id = manager.add_pipeline(**config)
        pipeline_ids.append(pipeline_id)

    return pipeline_ids
