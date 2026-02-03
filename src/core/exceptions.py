"""MIA系统统一异常层次

白皮书依据: 第二章 AI三脑核心组件
Requirements: 7.5 (错误处理和可靠性)
"""


class MIAException(Exception):
    """MIA系统基础异常

    所有MIA系统特定异常的基类

    白皮书依据: 第二章 错误处理架构

    Attributes:
        message: 错误消息
        error_code: 错误代码（可选）
        details: 错误详情（可选）
    """

    def __init__(self, message: str, error_code: str = None, details: dict = None):
        """初始化异常

        Args:
            message: 错误消息
            error_code: 错误代码
            details: 错误详情字典
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}

    def __str__(self) -> str:
        """字符串表示"""
        if self.error_code:
            return f"[{self.error_code}] {self.message}"
        return self.message

    def to_dict(self) -> dict:
        """转换为字典格式

        Returns:
            包含异常信息的字典
        """
        return {
            "exception_type": self.__class__.__name__,
            "message": self.message,
            "error_code": self.error_code,
            "details": self.details,
        }


# ============================================================================
# 组件初始化异常
# ============================================================================


class ComponentInitializationError(MIAException):
    """组件初始化失败异常

    当组件初始化失败时抛出

    白皮书依据: 第二章 组件生命周期管理
    Requirements: 7.7 (初始化验证)
    """

    def __init__(self, component_name: str, reason: str, details: dict = None):
        """初始化异常

        Args:
            component_name: 组件名称
            reason: 失败原因
            details: 详细信息
        """
        message = f"组件'{component_name}'初始化失败: {reason}"
        super().__init__(message, error_code="INIT_ERROR", details=details)
        self.component_name = component_name
        self.reason = reason


class ConfigurationError(MIAException):
    """配置错误异常

    当配置参数无效或缺失时抛出

    Requirements: 7.7 (初始化验证)
    """

    def __init__(self, parameter: str, reason: str, expected_value: str = None):
        """初始化异常

        Args:
            parameter: 参数名称
            reason: 错误原因
            expected_value: 期望值
        """
        message = f"配置参数'{parameter}'错误: {reason}"
        if expected_value:
            message += f" (期望: {expected_value})"
        super().__init__(message, error_code="CONFIG_ERROR")
        self.parameter = parameter
        self.expected_value = expected_value


# ============================================================================
# 模型相关异常
# ============================================================================


class ModelInferenceError(MIAException):
    """模型推理失败异常

    当模型推理过程中发生错误时抛出

    白皮书依据: 第二章 2.3 Algo Hunter (主力雷达)
    Requirements: 2.4 (推理失败处理)
    """

    def __init__(self, model_type: str, reason: str, input_shape: tuple = None):
        """初始化异常

        Args:
            model_type: 模型类型
            reason: 失败原因
            input_shape: 输入数据形状
        """
        message = f"模型'{model_type}'推理失败: {reason}"
        details = {"model_type": model_type}
        if input_shape:
            details["input_shape"] = input_shape
        super().__init__(message, error_code="INFERENCE_ERROR", details=details)
        self.model_type = model_type


class ModelLoadError(MIAException):
    """模型加载失败异常

    当模型文件加载失败时抛出

    Requirements: 2.1 (模型加载)
    """

    def __init__(self, model_path: str, reason: str):
        """初始化异常

        Args:
            model_path: 模型文件路径
            reason: 失败原因
        """
        message = f"模型加载失败: {model_path} - {reason}"
        super().__init__(message, error_code="MODEL_LOAD_ERROR")
        self.model_path = model_path


class ModelTrainingError(MIAException):
    """模型训练失败异常

    当模型训练过程中发生错误时抛出

    白皮书依据: 第二章 2.2.4 风险控制元学习架构
    Requirements: 1.3 (模型训练)
    """

    def __init__(self, model_type: str, reason: str, sample_count: int = None):
        """初始化异常

        Args:
            model_type: 模型类型
            reason: 失败原因
            sample_count: 训练样本数
        """
        message = f"模型'{model_type}'训练失败: {reason}"
        details = {"model_type": model_type}
        if sample_count is not None:
            details["sample_count"] = sample_count
        super().__init__(message, error_code="TRAINING_ERROR", details=details)
        self.model_type = model_type


# ============================================================================
# 记忆系统异常
# ============================================================================


class MemoryOperationError(MIAException):
    """记忆操作失败异常

    当记忆系统操作失败时抛出

    白皮书依据: 第二章 2.8 Engram统一记忆系统
    Requirements: 4.1-4.7 (记忆系统)
    """

    def __init__(self, operation: str, reason: str, memory_address: int = None):
        """初始化异常

        Args:
            operation: 操作类型（query/store/delete）
            reason: 失败原因
            memory_address: 内存地址
        """
        message = f"记忆操作'{operation}'失败: {reason}"
        details = {"operation": operation}
        if memory_address is not None:
            details["memory_address"] = memory_address
        super().__init__(message, error_code="MEMORY_ERROR", details=details)
        self.operation = operation


class MemoryCapacityError(MIAException):
    """记忆容量不足异常

    当记忆表容量不足时抛出

    Requirements: 7.6 (资源管理)
    """

    def __init__(self, current_usage: float, max_capacity: int):
        """初始化异常

        Args:
            current_usage: 当前使用率
            max_capacity: 最大容量
        """
        message = f"记忆容量不足: 使用率{current_usage:.1%}, 最大容量{max_capacity:,}"
        super().__init__(message, error_code="CAPACITY_ERROR")
        self.current_usage = current_usage
        self.max_capacity = max_capacity


# ============================================================================
# 事件总线异常
# ============================================================================


class EventBusError(MIAException):
    """事件总线错误异常

    当事件总线操作失败时抛出

    白皮书依据: 第二章 事件驱动架构
    Requirements: 6.1-6.5 (事件驱动通信)
    """

    def __init__(self, operation: str, reason: str, event_type: str = None):
        """初始化异常

        Args:
            operation: 操作类型（publish/subscribe/unsubscribe）
            reason: 失败原因
            event_type: 事件类型
        """
        message = f"事件总线操作'{operation}'失败: {reason}"
        details = {"operation": operation}
        if event_type:
            details["event_type"] = event_type
        super().__init__(message, error_code="EVENTBUS_ERROR", details=details)
        self.operation = operation


class EventPublishError(EventBusError):
    """事件发布失败异常

    当事件发布失败时抛出

    Requirements: 6.1 (事件发布)
    """

    def __init__(self, event_type: str, reason: str):
        """初始化异常

        Args:
            event_type: 事件类型
            reason: 失败原因
        """
        super().__init__("publish", reason, event_type)


class EventTimeoutError(EventBusError):
    """事件超时异常

    当事件处理超时时抛出

    Requirements: 6.3 (请求-响应超时)
    """

    def __init__(self, event_type: str, timeout_seconds: float):
        """初始化异常

        Args:
            event_type: 事件类型
            timeout_seconds: 超时时间（秒）
        """
        reason = f"等待响应超时（{timeout_seconds}秒）"
        super().__init__("wait_response", reason, event_type)
        self.timeout_seconds = timeout_seconds


# ============================================================================
# 数据验证异常
# ============================================================================


class ValidationError(MIAException):
    """数据验证失败异常

    当数据验证失败时抛出

    Requirements: 7.7 (参数验证)
    """

    def __init__(self, field: str, value: any, reason: str):
        """初始化异常

        Args:
            field: 字段名称
            value: 字段值
            reason: 验证失败原因
        """
        message = f"字段'{field}'验证失败: {reason} (值: {value})"
        super().__init__(message, error_code="VALIDATION_ERROR")
        self.field = field
        self.value = value


class DataShapeError(ValidationError):
    """数据形状错误异常

    当数据形状不符合要求时抛出

    Requirements: 2.2 (数据预处理)
    """

    def __init__(self, expected_shape: tuple, actual_shape: tuple):
        """初始化异常

        Args:
            expected_shape: 期望形状
            actual_shape: 实际形状
        """
        reason = f"期望形状{expected_shape}, 实际形状{actual_shape}"
        super().__init__("data_shape", actual_shape, reason)
        self.expected_shape = expected_shape
        self.actual_shape = actual_shape


# ============================================================================
# 算法进化异常
# ============================================================================


class AlgorithmEvolutionError(MIAException):
    """算法进化失败异常

    当算法进化过程中发生错误时抛出

    白皮书依据: 第二章 2.5 AlgoEvolution Sentinel
    Requirements: 3.1-3.7 (算法进化)
    """

    def __init__(self, stage: str, reason: str, paper_title: str = None):
        """初始化异常

        Args:
            stage: 失败阶段（scan/filter/translate/validate/integrate）
            reason: 失败原因
            paper_title: 论文标题
        """
        message = f"算法进化阶段'{stage}'失败: {reason}"
        details = {"stage": stage}
        if paper_title:
            details["paper_title"] = paper_title
        super().__init__(message, error_code="EVOLUTION_ERROR", details=details)
        self.stage = stage


class SandboxValidationError(AlgorithmEvolutionError):
    """沙盒验证失败异常

    当算法沙盒验证失败时抛出

    Requirements: 3.4 (沙盒验证)
    """

    def __init__(self, algorithm_name: str, reason: str, validation_results: dict = None):
        """初始化异常

        Args:
            algorithm_name: 算法名称
            reason: 失败原因
            validation_results: 验证结果
        """
        super().__init__("validate", reason)
        self.algorithm_name = algorithm_name
        self.validation_results = validation_results or {}


# ============================================================================
# 资源管理异常
# ============================================================================


class ResourceExhaustedError(MIAException):
    """资源耗尽异常

    当系统资源耗尽时抛出

    Requirements: 7.6 (资源管理)
    """

    def __init__(self, resource_type: str, current_usage: float, threshold: float):
        """初始化异常

        Args:
            resource_type: 资源类型（memory/cpu/gpu/disk）
            current_usage: 当前使用率
            threshold: 阈值
        """
        message = f"资源'{resource_type}'耗尽: 使用率{current_usage:.1%} > 阈值{threshold:.1%}"
        super().__init__(message, error_code="RESOURCE_EXHAUSTED")
        self.resource_type = resource_type
        self.current_usage = current_usage
        self.threshold = threshold


class MemoryLeakError(MIAException):
    """内存泄漏异常

    当检测到内存泄漏时抛出

    Requirements: 7.6 (资源泄漏检测)
    """

    def __init__(self, component: str, leaked_bytes: int):
        """初始化异常

        Args:
            component: 组件名称
            leaked_bytes: 泄漏字节数
        """
        message = f"组件'{component}'检测到内存泄漏: {leaked_bytes:,} bytes"
        super().__init__(message, error_code="MEMORY_LEAK")
        self.component = component
        self.leaked_bytes = leaked_bytes


# ============================================================================
# 性能异常
# ============================================================================


class PerformanceError(MIAException):
    """性能不达标异常

    当性能指标不满足要求时抛出

    Requirements: 7.1-7.4 (性能要求)
    """

    def __init__(self, metric: str, actual_value: float, required_value: float, unit: str = ""):
        """初始化异常

        Args:
            metric: 性能指标名称
            actual_value: 实际值
            required_value: 要求值
            unit: 单位
        """
        message = f"性能指标'{metric}'不达标: {actual_value}{unit} (要求: {required_value}{unit})"
        super().__init__(message, error_code="PERFORMANCE_ERROR")
        self.metric = metric
        self.actual_value = actual_value
        self.required_value = required_value


class LatencyExceededError(PerformanceError):
    """延迟超标异常

    当延迟超过要求时抛出

    Requirements: 7.1 (推理延迟)
    """

    def __init__(self, operation: str, actual_latency_ms: float, max_latency_ms: float):
        """初始化异常

        Args:
            operation: 操作名称
            actual_latency_ms: 实际延迟（毫秒）
            max_latency_ms: 最大延迟（毫秒）
        """
        super().__init__(
            metric=f"{operation}_latency", actual_value=actual_latency_ms, required_value=max_latency_ms, unit="ms"
        )
        self.operation = operation


# ============================================================================
# 辅助函数
# ============================================================================


def get_exception_hierarchy() -> dict:
    """获取异常层次结构

    Returns:
        异常层次结构字典
    """
    return {
        "MIAException": {
            "ComponentInitializationError": [],
            "ConfigurationError": [],
            "ModelInferenceError": [],
            "ModelLoadError": [],
            "ModelTrainingError": [],
            "MemoryOperationError": [],
            "MemoryCapacityError": [],
            "EventBusError": {"EventPublishError": [], "EventTimeoutError": []},
            "ValidationError": {"DataShapeError": []},
            "AlgorithmEvolutionError": {"SandboxValidationError": []},
            "ResourceExhaustedError": [],
            "MemoryLeakError": [],
            "PerformanceError": {"LatencyExceededError": []},
        }
    }


def is_mia_exception(exception: Exception) -> bool:
    """判断是否为MIA系统异常

    Args:
        exception: 异常对象

    Returns:
        是否为MIA系统异常
    """
    return isinstance(exception, MIAException)
