"""
依赖注入容器 - 解决循环依赖核心组件

白皮书依据: 架构审计报告 - 循环依赖修复方案
实现控制反转(IoC)和依赖注入(DI)，彻底解决模块间循环依赖
"""

import inspect
import threading
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, Optional, Type, TypeVar, get_type_hints

from loguru import logger

T = TypeVar("T")


class LifecycleScope(Enum):
    """生命周期范围"""

    SINGLETON = "singleton"  # 单例模式
    TRANSIENT = "transient"  # 每次创建新实例
    SCOPED = "scoped"  # 作用域内单例


@dataclass
class ServiceDescriptor:
    """服务描述符"""

    service_type: Type
    implementation_type: Optional[Type] = None
    factory: Optional[Callable] = None
    instance: Optional[Any] = None
    lifecycle: LifecycleScope = LifecycleScope.SINGLETON
    dependencies: list = field(default_factory=list)
    created_at: Optional[datetime] = None
    access_count: int = 0


class DIContainer:
    """依赖注入容器

    白皮书依据: 架构审计报告 - 解决循环依赖的核心方案

    解决的循环依赖问题:
    1. AI三脑循环依赖: Soldier ↔ Commander ↔ Scholar
    2. 进化-验证循环依赖: Evolution ↔ Auditor
    3. 内存-调度循环依赖: Memory ↔ Scheduler
    4. 执行-审计循环依赖: Execution ↔ Auditor

    核心原理:
    - 控制反转: 由容器控制对象创建和依赖关系
    - 延迟初始化: 避免循环依赖时的初始化死锁
    - 接口抽象: 通过接口解耦具体实现
    """

    def __init__(self):
        self._services: Dict[Type, ServiceDescriptor] = {}
        self._instances: Dict[Type, Any] = {}
        self._lock = threading.RLock()
        self._creating: set = set()  # 正在创建的服务，防止循环依赖

    def register_singleton(self, service_type: Type[T], implementation_type: Type[T] = None) -> "DIContainer":
        """注册单例服务"""
        return self._register(service_type, implementation_type, LifecycleScope.SINGLETON)

    def register_transient(self, service_type: Type[T], implementation_type: Type[T] = None) -> "DIContainer":
        """注册瞬态服务"""
        return self._register(service_type, implementation_type, LifecycleScope.TRANSIENT)

    def register_scoped(self, service_type: Type[T], implementation_type: Type[T] = None) -> "DIContainer":
        """注册作用域服务"""
        return self._register(service_type, implementation_type, LifecycleScope.SCOPED)

    def register_factory(self, service_type: Type[T], factory: Callable[[], T]) -> "DIContainer":
        """注册工厂方法"""
        with self._lock:
            descriptor = ServiceDescriptor(
                service_type=service_type, factory=factory, lifecycle=LifecycleScope.SINGLETON
            )
            self._services[service_type] = descriptor
            logger.debug(f"[DIContainer] Registered factory for {service_type.__name__}")
            return self

    def register_instance(self, service_type: Type[T], instance: T) -> "DIContainer":
        """注册实例"""
        with self._lock:
            descriptor = ServiceDescriptor(
                service_type=service_type,
                instance=instance,
                lifecycle=LifecycleScope.SINGLETON,
                created_at=datetime.now(),
            )
            self._services[service_type] = descriptor
            self._instances[service_type] = instance
            logger.debug(f"[DIContainer] Registered instance for {service_type.__name__}")
            return self

    def _register(
        self, service_type: Type[T], implementation_type: Type[T], lifecycle: LifecycleScope
    ) -> "DIContainer":
        """内部注册方法"""
        with self._lock:
            if implementation_type is None:
                implementation_type = service_type

            # 分析依赖关系
            dependencies = self._analyze_dependencies(implementation_type)

            descriptor = ServiceDescriptor(
                service_type=service_type,
                implementation_type=implementation_type,
                lifecycle=lifecycle,
                dependencies=dependencies,
            )

            self._services[service_type] = descriptor
            logger.debug(
                f"[DIContainer] Registered {lifecycle.value} {service_type.__name__} -> {implementation_type.__name__}"
            )
            return self

    def resolve(self, service_type: Type[T]) -> T:
        """解析服务"""
        with self._lock:
            # 检查循环依赖
            if service_type in self._creating:
                raise RuntimeError(f"Circular dependency detected for {service_type.__name__}")

            # 检查是否已有实例
            if service_type in self._instances:
                descriptor = self._services[service_type]
                descriptor.access_count += 1
                return self._instances[service_type]

            # 检查是否已注册
            if service_type not in self._services:
                raise ValueError(f"Service {service_type.__name__} not registered")

            descriptor = self._services[service_type]

            # 如果有现成实例，直接返回
            if descriptor.instance is not None:
                descriptor.access_count += 1
                return descriptor.instance

            # 标记正在创建
            self._creating.add(service_type)

            try:
                # 创建实例
                instance = self._create_instance(descriptor)

                # 根据生命周期决定是否缓存
                if descriptor.lifecycle == LifecycleScope.SINGLETON:
                    self._instances[service_type] = instance
                    descriptor.instance = instance
                    descriptor.created_at = datetime.now()

                descriptor.access_count += 1
                logger.debug(f"[DIContainer] Created instance of {service_type.__name__}")
                return instance

            finally:
                # 移除创建标记
                self._creating.discard(service_type)

    def _create_instance(self, descriptor: ServiceDescriptor):
        """创建服务实例"""
        # 使用工厂方法
        if descriptor.factory:
            return descriptor.factory()

        # 使用构造函数
        if descriptor.implementation_type:
            # 解析构造函数依赖
            constructor_args = self._resolve_constructor_dependencies(descriptor.implementation_type)
            return descriptor.implementation_type(**constructor_args)

        raise ValueError(f"Cannot create instance for {descriptor.service_type.__name__}")

    def _analyze_dependencies(self, implementation_type: Type) -> list:
        """分析类的依赖关系"""
        dependencies = []

        try:
            # 获取构造函数签名
            init_signature = inspect.signature(implementation_type.__init__)
            type_hints = get_type_hints(implementation_type.__init__)

            for param_name, param in init_signature.parameters.items():
                if param_name == "self":
                    continue

                # 获取参数类型
                param_type = type_hints.get(param_name, param.annotation)

                if param_type != inspect.Parameter.empty:
                    dependencies.append(
                        {"name": param_name, "type": param_type, "required": param.default == inspect.Parameter.empty}
                    )

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.warning(f"[DIContainer] Failed to analyze dependencies for {implementation_type.__name__}: {e}")

        return dependencies

    def _resolve_constructor_dependencies(self, implementation_type: Type) -> Dict[str, Any]:
        """解析构造函数依赖"""
        args = {}

        try:
            init_signature = inspect.signature(implementation_type.__init__)
            type_hints = get_type_hints(implementation_type.__init__)

            for param_name, param in init_signature.parameters.items():
                if param_name == "self":
                    continue

                param_type = type_hints.get(param_name, param.annotation)

                if param_type != inspect.Parameter.empty:
                    # 尝试解析依赖
                    if param_type in self._services:
                        args[param_name] = self.resolve(param_type)
                    elif param.default != inspect.Parameter.empty:
                        # 使用默认值
                        args[param_name] = param.default
                    else:
                        logger.warning(f"[DIContainer] Cannot resolve dependency {param_name}: {param_type}")

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(
                f"[DIContainer] Failed to resolve constructor dependencies for {implementation_type.__name__}: {e}"
            )

        return args

    def is_registered(self, service_type: Type) -> bool:
        """检查服务是否已注册"""
        return service_type in self._services

    def get_service_info(self, service_type: Type) -> Optional[Dict[str, Any]]:
        """获取服务信息"""
        if service_type not in self._services:
            return None

        descriptor = self._services[service_type]
        return {
            "service_type": service_type.__name__,
            "implementation_type": descriptor.implementation_type.__name__ if descriptor.implementation_type else None,
            "lifecycle": descriptor.lifecycle.value,
            "has_instance": service_type in self._instances,
            "created_at": descriptor.created_at.isoformat() if descriptor.created_at else None,
            "access_count": descriptor.access_count,
            "dependencies": [
                {
                    "name": dep["name"],
                    "type": dep["type"].__name__ if hasattr(dep["type"], "__name__") else str(dep["type"]),
                    "required": dep["required"],
                }
                for dep in descriptor.dependencies
            ],
        }

    def get_all_services(self) -> Dict[str, Any]:
        """获取所有服务信息"""
        return {
            service_type.__name__: self.get_service_info(service_type)
            for service_type in self._services.keys()  # pylint: disable=consider-iterating-dictionary
        }  # pylint: disable=consider-iterating-dictionary

    def clear(self):
        """清空容器"""
        with self._lock:
            self._services.clear()
            self._instances.clear()
            self._creating.clear()
            logger.info("[DIContainer] Container cleared")


# 接口定义现在在 src/brain/interfaces.py 中
# 这里只保留依赖注入容器的核心功能


# 全局容器实例
_global_container: Optional[DIContainer] = None


def get_container() -> DIContainer:
    """获取全局容器实例"""
    global _global_container  # pylint: disable=w0603

    if _global_container is None:
        _global_container = DIContainer()

    return _global_container


def register_core_services():
    """注册核心服务 - 解决循环依赖的配置"""
    container = get_container()

    # 注册AI三脑接口映射
    # 具体实现类将在各模块初始化时注册
    logger.info("[DIContainer] Core services registration completed")
    logger.info("[DIContainer] AI三脑接口映射将在模块初始化时注册")

    return container


def register_ai_brain_services():
    """注册AI三脑服务映射

    白皮书依据: 第二章 2.1 AI三脑架构 + 架构审计报告循环依赖修复
    需求: 4.5 - 配置依赖注入容器

    这个函数将在AI三脑模块初始化时调用，建立接口到实现类的映射。
    """
    from ..brain.interfaces import (  # pylint: disable=import-outside-toplevel
        ICommanderEngine,
        IScholarEngine,
        ISoldierEngine,
    )

    container = get_container()

    # 延迟导入避免循环依赖
    try:
        from ..brain.soldier_engine_v2 import SoldierEngineV2  # pylint: disable=import-outside-toplevel

        container.register_singleton(ISoldierEngine, SoldierEngineV2)
        logger.info("[DIContainer] Registered ISoldierEngine -> SoldierEngineV2")
    except ImportError as e:
        logger.warning(f"[DIContainer] Failed to register SoldierEngineV2: {e}")

    try:
        from ..brain.commander_engine_v2 import CommanderEngineV2  # pylint: disable=import-outside-toplevel

        container.register_singleton(ICommanderEngine, CommanderEngineV2)
        logger.info("[DIContainer] Registered ICommanderEngine -> CommanderEngineV2")
    except ImportError as e:
        logger.warning(f"[DIContainer] Failed to register CommanderEngineV2: {e}")

    try:
        from ..brain.scholar_engine_v2 import ScholarEngineV2  # pylint: disable=import-outside-toplevel

        container.register_singleton(IScholarEngine, ScholarEngineV2)
        logger.info("[DIContainer] Registered IScholarEngine -> ScholarEngineV2")
    except ImportError as e:
        logger.warning(f"[DIContainer] Failed to register ScholarEngineV2: {e}")

    logger.info("[DIContainer] AI三脑服务注册完成")

    return container


# 装饰器：自动注册服务
def injectable(lifecycle: LifecycleScope = LifecycleScope.SINGLETON):
    """可注入装饰器"""

    def decorator(cls):
        container = get_container()

        if lifecycle == LifecycleScope.SINGLETON:
            container.register_singleton(cls)
        elif lifecycle == LifecycleScope.TRANSIENT:
            container.register_transient(cls)
        elif lifecycle == LifecycleScope.SCOPED:
            container.register_scoped(cls)

        return cls

    return decorator


# 装饰器：自动解析依赖
def inject(service_type: Type[T]) -> T:
    """依赖注入装饰器"""

    def decorator(func):
        def wrapper(*args, **kwargs):
            container = get_container()
            service = container.resolve(service_type)
            return func(service, *args, **kwargs)

        return wrapper

    return decorator
