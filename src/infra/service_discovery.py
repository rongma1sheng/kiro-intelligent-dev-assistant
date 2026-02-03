"""Service Discovery - Microservices Service Discovery

白皮书依据: 第十七章 17.1 微服务化拆分

核心功能:
- 服务注册
- 服务发现
- 健康检查
- 负载均衡
"""

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from loguru import logger


@dataclass
class ServiceInstance:
    """服务实例

    Attributes:
        service_name: 服务名称
        instance_id: 实例ID
        host: 主机地址
        port: 端口号
        metadata: 元数据
        registered_at: 注册时间
        last_heartbeat: 最后心跳时间
        status: 状态（healthy/unhealthy）
    """

    service_name: str
    instance_id: str
    host: str
    port: int
    metadata: Dict[str, Any] = field(default_factory=dict)
    registered_at: float = field(default_factory=time.time)
    last_heartbeat: float = field(default_factory=time.time)
    status: str = "healthy"

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "service_name": self.service_name,
            "instance_id": self.instance_id,
            "host": self.host,
            "port": self.port,
            "metadata": self.metadata,
            "registered_at": self.registered_at,
            "last_heartbeat": self.last_heartbeat,
            "status": self.status,
        }


class ServiceDiscovery:
    """服务发现 - 微服务服务发现

    白皮书依据: 第十七章 17.1 微服务化拆分

    核心功能:
    - 服务注册
    - 服务发现
    - 健康检查
    - 负载均衡

    Attributes:
        registry: 服务注册表
        heartbeat_timeout: 心跳超时时间（秒）
        health_check_interval: 健康检查间隔（秒）
    """

    def __init__(self, heartbeat_timeout: int = 30, health_check_interval: int = 10):
        """初始化服务发现

        Args:
            heartbeat_timeout: 心跳超时时间（秒）
            health_check_interval: 健康检查间隔（秒）

        Raises:
            ValueError: 当参数无效时
        """
        if heartbeat_timeout <= 0:
            raise ValueError(f"心跳超时时间必须 > 0: {heartbeat_timeout}")

        if health_check_interval <= 0:
            raise ValueError(f"健康检查间隔必须 > 0: {health_check_interval}")

        self.heartbeat_timeout = heartbeat_timeout
        self.health_check_interval = health_check_interval

        # 服务注册表：{service_name: {instance_id: ServiceInstance}}
        self.registry: Dict[str, Dict[str, ServiceInstance]] = {}

        # 统计信息
        self.total_registrations = 0
        self.total_deregistrations = 0
        self.total_discoveries = 0

        logger.info(
            f"[ServiceDiscovery] 初始化完成 - "
            f"心跳超时: {heartbeat_timeout}s, "
            f"健康检查间隔: {health_check_interval}s"
        )

    def register_service(  # pylint: disable=too-many-positional-arguments
        self, service_name: str, instance_id: str, host: str, port: int, metadata: Optional[Dict[str, Any]] = None
    ) -> ServiceInstance:
        """注册服务

        白皮书依据: 第十七章 17.1 微服务化拆分

        Args:
            service_name: 服务名称
            instance_id: 实例ID
            host: 主机地址
            port: 端口号
            metadata: 元数据

        Returns:
            服务实例

        Raises:
            ValueError: 当参数无效时
        """
        if not service_name:
            raise ValueError("服务名称不能为空")

        if not instance_id:
            raise ValueError("实例ID不能为空")

        if not host:
            raise ValueError("主机地址不能为空")

        if port <= 0 or port > 65535:
            raise ValueError(f"端口号必须在 1-65535 范围内: {port}")

        # 创建服务实例
        instance = ServiceInstance(
            service_name=service_name, instance_id=instance_id, host=host, port=port, metadata=metadata or {}
        )

        # 注册到注册表
        if service_name not in self.registry:
            self.registry[service_name] = {}

        self.registry[service_name][instance_id] = instance
        self.total_registrations += 1

        logger.info(
            f"[ServiceDiscovery] 服务注册成功 - "
            f"服务: {service_name}, "
            f"实例: {instance_id}, "
            f"地址: {host}:{port}"
        )

        return instance

    def deregister_service(self, service_name: str, instance_id: str) -> bool:
        """注销服务

        Args:
            service_name: 服务名称
            instance_id: 实例ID

        Returns:
            是否成功注销
        """
        if service_name not in self.registry:
            logger.warning(f"[ServiceDiscovery] 服务不存在 - 服务: {service_name}")
            return False

        if instance_id not in self.registry[service_name]:
            logger.warning(f"[ServiceDiscovery] 实例不存在 - " f"服务: {service_name}, 实例: {instance_id}")
            return False

        # 从注册表删除
        del self.registry[service_name][instance_id]
        self.total_deregistrations += 1

        # 如果服务没有实例了，删除服务
        if not self.registry[service_name]:
            del self.registry[service_name]

        logger.info(f"[ServiceDiscovery] 服务注销成功 - " f"服务: {service_name}, 实例: {instance_id}")

        return True

    def discover_service(self, service_name: str, healthy_only: bool = True) -> List[ServiceInstance]:
        """发现服务

        白皮书依据: 第十七章 17.1 微服务化拆分

        Args:
            service_name: 服务名称
            healthy_only: 是否只返回健康实例

        Returns:
            服务实例列表
        """
        if service_name not in self.registry:
            logger.debug(f"[ServiceDiscovery] 服务不存在 - 服务: {service_name}")
            return []

        instances = list(self.registry[service_name].values())

        # 过滤健康实例
        if healthy_only:
            instances = [inst for inst in instances if inst.status == "healthy"]

        self.total_discoveries += 1

        logger.debug(f"[ServiceDiscovery] 服务发现 - " f"服务: {service_name}, " f"实例数: {len(instances)}")

        return instances

    def get_service_instance(self, service_name: str, instance_id: str) -> Optional[ServiceInstance]:
        """获取服务实例

        Args:
            service_name: 服务名称
            instance_id: 实例ID

        Returns:
            服务实例，如果不存在返回None
        """
        if service_name not in self.registry:
            return None

        return self.registry[service_name].get(instance_id)

    def update_heartbeat(self, service_name: str, instance_id: str) -> bool:
        """更新心跳

        Args:
            service_name: 服务名称
            instance_id: 实例ID

        Returns:
            是否成功更新
        """
        instance = self.get_service_instance(service_name, instance_id)

        if instance is None:
            logger.warning(
                f"[ServiceDiscovery] 实例不存在，无法更新心跳 - " f"服务: {service_name}, 实例: {instance_id}"
            )
            return False

        instance.last_heartbeat = time.time()
        instance.status = "healthy"

        logger.debug(f"[ServiceDiscovery] 心跳更新 - " f"服务: {service_name}, 实例: {instance_id}")

        return True

    def health_check_services(self) -> Dict[str, Any]:
        """健康检查所有服务

        白皮书依据: 第十七章 17.1 微服务化拆分

        Returns:
            健康检查结果，包含:
            - total_services: 总服务数
            - total_instances: 总实例数
            - healthy_instances: 健康实例数
            - unhealthy_instances: 不健康实例数
            - services: 各服务健康状态
        """
        current_time = time.time()

        total_instances = 0
        healthy_instances = 0
        unhealthy_instances = 0

        services_status = {}

        for service_name, instances in self.registry.items():
            service_healthy = 0
            service_unhealthy = 0

            for instance_id, instance in instances.items():
                total_instances += 1

                # 检查心跳超时
                time_since_heartbeat = current_time - instance.last_heartbeat

                if time_since_heartbeat > self.heartbeat_timeout:
                    # 心跳超时，标记为不健康
                    instance.status = "unhealthy"
                    unhealthy_instances += 1
                    service_unhealthy += 1

                    logger.warning(
                        f"[ServiceDiscovery] 实例不健康（心跳超时） - "
                        f"服务: {service_name}, "
                        f"实例: {instance_id}, "
                        f"超时: {time_since_heartbeat:.1f}s"
                    )
                else:
                    healthy_instances += 1
                    service_healthy += 1

            services_status[service_name] = {
                "total": len(instances),
                "healthy": service_healthy,
                "unhealthy": service_unhealthy,
            }

        result = {
            "total_services": len(self.registry),
            "total_instances": total_instances,
            "healthy_instances": healthy_instances,
            "unhealthy_instances": unhealthy_instances,
            "services": services_status,
        }

        logger.info(
            f"[ServiceDiscovery] 健康检查完成 - "
            f"服务数: {result['total_services']}, "
            f"实例数: {result['total_instances']}, "
            f"健康: {result['healthy_instances']}, "
            f"不健康: {result['unhealthy_instances']}"
        )

        return result

    def get_service_url(self, service_name: str, load_balance: str = "round_robin") -> Optional[str]:
        """获取服务URL（带负载均衡）

        Args:
            service_name: 服务名称
            load_balance: 负载均衡策略（round_robin/random）

        Returns:
            服务URL，如果没有健康实例返回None
        """
        instances = self.discover_service(service_name, healthy_only=True)

        if not instances:
            logger.warning(f"[ServiceDiscovery] 没有健康实例 - 服务: {service_name}")
            return None

        # 负载均衡选择实例
        if load_balance == "round_robin":
            # 简单轮询（使用时间戳模拟）
            index = int(time.time()) % len(instances)
            instance = instances[index]
        elif load_balance == "random":
            # 随机选择
            import random  # pylint: disable=import-outside-toplevel

            instance = random.choice(instances)
        else:
            # 默认选择第一个
            instance = instances[0]

        url = f"http://{instance.host}:{instance.port}"

        logger.debug(
            f"[ServiceDiscovery] 获取服务URL - " f"服务: {service_name}, " f"URL: {url}, " f"策略: {load_balance}"
        )

        return url

    def get_all_services(self) -> List[str]:
        """获取所有服务名称

        Returns:
            服务名称列表
        """
        return list(self.registry.keys())

    def get_service_count(self) -> int:
        """获取服务数量

        Returns:
            服务数量
        """
        return len(self.registry)

    def get_instance_count(self, service_name: Optional[str] = None) -> int:
        """获取实例数量

        Args:
            service_name: 服务名称，None表示所有服务

        Returns:
            实例数量
        """
        if service_name is None:  # pylint: disable=no-else-return
            # 所有服务的实例总数
            return sum(len(instances) for instances in self.registry.values())
        else:
            # 指定服务的实例数
            if service_name not in self.registry:
                return 0
            return len(self.registry[service_name])

    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息

        Returns:
            统计信息字典
        """
        return {
            "total_services": self.get_service_count(),
            "total_instances": self.get_instance_count(),
            "total_registrations": self.total_registrations,
            "total_deregistrations": self.total_deregistrations,
            "total_discoveries": self.total_discoveries,
            "heartbeat_timeout": self.heartbeat_timeout,
            "health_check_interval": self.health_check_interval,
        }

    def clear_registry(self) -> None:
        """清空注册表"""
        self.registry.clear()
        logger.info("[ServiceDiscovery] 注册表已清空")
