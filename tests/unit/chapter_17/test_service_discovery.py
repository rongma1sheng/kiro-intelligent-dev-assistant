"""Unit Tests for ServiceDiscovery

白皮书依据: 第十七章 17.1 微服务化拆分

测试覆盖:
- 服务注册和注销
- 服务发现
- 健康检查
- 负载均衡
- 边界条件和异常情况
"""

import pytest
import time
from src.infra.service_discovery import (
    ServiceDiscovery,
    ServiceInstance
)


class TestServiceDiscovery:
    """测试ServiceDiscovery类"""
    
    @pytest.fixture
    def discovery(self):
        """测试夹具：创建服务发现实例"""
        return ServiceDiscovery(
            heartbeat_timeout=30,
            health_check_interval=10
        )
    
    def test_init_success(self):
        """测试初始化成功"""
        discovery = ServiceDiscovery(
            heartbeat_timeout=30,
            health_check_interval=10
        )
        
        assert discovery.heartbeat_timeout == 30
        assert discovery.health_check_interval == 10
        assert len(discovery.registry) == 0
        assert discovery.total_registrations == 0
        assert discovery.total_deregistrations == 0
        assert discovery.total_discoveries == 0
    
    def test_init_invalid_heartbeat_timeout(self):
        """测试初始化失败：无效的心跳超时时间"""
        with pytest.raises(ValueError, match="心跳超时时间必须 > 0"):
            ServiceDiscovery(heartbeat_timeout=0)
    
    def test_init_invalid_health_check_interval(self):
        """测试初始化失败：无效的健康检查间隔"""
        with pytest.raises(ValueError, match="健康检查间隔必须 > 0"):
            ServiceDiscovery(health_check_interval=-1)
    
    def test_register_service_success(self, discovery):
        """测试服务注册成功"""
        instance = discovery.register_service(
            service_name="test-service",
            instance_id="instance-1",
            host="localhost",
            port=8080,
            metadata={'version': '1.0.0'}
        )
        
        assert isinstance(instance, ServiceInstance)
        assert instance.service_name == "test-service"
        assert instance.instance_id == "instance-1"
        assert instance.host == "localhost"
        assert instance.port == 8080
        assert instance.metadata == {'version': '1.0.0'}
        assert instance.status == "healthy"
        assert discovery.total_registrations == 1
    
    def test_register_service_empty_service_name(self, discovery):
        """测试服务注册失败：空服务名称"""
        with pytest.raises(ValueError, match="服务名称不能为空"):
            discovery.register_service(
                service_name="",
                instance_id="instance-1",
                host="localhost",
                port=8080
            )
    
    def test_register_service_empty_instance_id(self, discovery):
        """测试服务注册失败：空实例ID"""
        with pytest.raises(ValueError, match="实例ID不能为空"):
            discovery.register_service(
                service_name="test-service",
                instance_id="",
                host="localhost",
                port=8080
            )
    
    def test_register_service_empty_host(self, discovery):
        """测试服务注册失败：空主机地址"""
        with pytest.raises(ValueError, match="主机地址不能为空"):
            discovery.register_service(
                service_name="test-service",
                instance_id="instance-1",
                host="",
                port=8080
            )
    
    def test_register_service_invalid_port_zero(self, discovery):
        """测试服务注册失败：端口号为0"""
        with pytest.raises(ValueError, match="端口号必须在 1-65535 范围内"):
            discovery.register_service(
                service_name="test-service",
                instance_id="instance-1",
                host="localhost",
                port=0
            )
    
    def test_register_service_invalid_port_too_large(self, discovery):
        """测试服务注册失败：端口号超出范围"""
        with pytest.raises(ValueError, match="端口号必须在 1-65535 范围内"):
            discovery.register_service(
                service_name="test-service",
                instance_id="instance-1",
                host="localhost",
                port=70000
            )
    
    def test_register_multiple_instances(self, discovery):
        """测试注册多个实例"""
        discovery.register_service(
            service_name="test-service",
            instance_id="instance-1",
            host="localhost",
            port=8080
        )
        
        discovery.register_service(
            service_name="test-service",
            instance_id="instance-2",
            host="localhost",
            port=8081
        )
        
        assert discovery.total_registrations == 2
        assert len(discovery.registry["test-service"]) == 2
    
    def test_deregister_service_success(self, discovery):
        """测试服务注销成功"""
        discovery.register_service(
            service_name="test-service",
            instance_id="instance-1",
            host="localhost",
            port=8080
        )
        
        result = discovery.deregister_service(
            service_name="test-service",
            instance_id="instance-1"
        )
        
        assert result is True
        assert discovery.total_deregistrations == 1
        assert "test-service" not in discovery.registry
    
    def test_deregister_service_nonexistent_service(self, discovery):
        """测试服务注销失败：服务不存在"""
        result = discovery.deregister_service(
            service_name="nonexistent-service",
            instance_id="instance-1"
        )
        
        assert result is False
    
    def test_deregister_service_nonexistent_instance(self, discovery):
        """测试服务注销失败：实例不存在"""
        discovery.register_service(
            service_name="test-service",
            instance_id="instance-1",
            host="localhost",
            port=8080
        )
        
        result = discovery.deregister_service(
            service_name="test-service",
            instance_id="nonexistent-instance"
        )
        
        assert result is False
    
    def test_deregister_last_instance_removes_service(self, discovery):
        """测试注销最后一个实例时删除服务"""
        discovery.register_service(
            service_name="test-service",
            instance_id="instance-1",
            host="localhost",
            port=8080
        )
        
        discovery.deregister_service(
            service_name="test-service",
            instance_id="instance-1"
        )
        
        assert "test-service" not in discovery.registry
    
    def test_discover_service_success(self, discovery):
        """测试服务发现成功"""
        discovery.register_service(
            service_name="test-service",
            instance_id="instance-1",
            host="localhost",
            port=8080
        )
        
        instances = discovery.discover_service("test-service")
        
        assert len(instances) == 1
        assert instances[0].instance_id == "instance-1"
        assert discovery.total_discoveries == 1
    
    def test_discover_service_nonexistent(self, discovery):
        """测试服务发现：服务不存在"""
        instances = discovery.discover_service("nonexistent-service")
        
        assert len(instances) == 0
    
    def test_discover_service_healthy_only(self, discovery):
        """测试服务发现：只返回健康实例"""
        # 注册两个实例
        discovery.register_service(
            service_name="test-service",
            instance_id="instance-1",
            host="localhost",
            port=8080
        )
        
        discovery.register_service(
            service_name="test-service",
            instance_id="instance-2",
            host="localhost",
            port=8081
        )
        
        # 标记一个实例为不健康
        instance = discovery.get_service_instance("test-service", "instance-2")
        instance.status = "unhealthy"
        
        # 只返回健康实例
        instances = discovery.discover_service("test-service", healthy_only=True)
        assert len(instances) == 1
        assert instances[0].instance_id == "instance-1"
        
        # 返回所有实例
        instances = discovery.discover_service("test-service", healthy_only=False)
        assert len(instances) == 2
    
    def test_get_service_instance_success(self, discovery):
        """测试获取服务实例成功"""
        discovery.register_service(
            service_name="test-service",
            instance_id="instance-1",
            host="localhost",
            port=8080
        )
        
        instance = discovery.get_service_instance("test-service", "instance-1")
        
        assert instance is not None
        assert instance.instance_id == "instance-1"
    
    def test_get_service_instance_nonexistent_service(self, discovery):
        """测试获取服务实例：服务不存在"""
        instance = discovery.get_service_instance("nonexistent-service", "instance-1")
        
        assert instance is None
    
    def test_get_service_instance_nonexistent_instance(self, discovery):
        """测试获取服务实例：实例不存在"""
        discovery.register_service(
            service_name="test-service",
            instance_id="instance-1",
            host="localhost",
            port=8080
        )
        
        instance = discovery.get_service_instance("test-service", "nonexistent-instance")
        
        assert instance is None
    
    def test_update_heartbeat_success(self, discovery):
        """测试更新心跳成功"""
        discovery.register_service(
            service_name="test-service",
            instance_id="instance-1",
            host="localhost",
            port=8080
        )
        
        # 获取初始心跳时间
        instance = discovery.get_service_instance("test-service", "instance-1")
        initial_heartbeat = instance.last_heartbeat
        
        # 等待一小段时间
        time.sleep(0.1)
        
        # 更新心跳
        result = discovery.update_heartbeat("test-service", "instance-1")
        
        assert result is True
        assert instance.last_heartbeat > initial_heartbeat
        assert instance.status == "healthy"
    
    def test_update_heartbeat_nonexistent_instance(self, discovery):
        """测试更新心跳失败：实例不存在"""
        result = discovery.update_heartbeat("nonexistent-service", "instance-1")
        
        assert result is False
    
    def test_health_check_services_all_healthy(self, discovery):
        """测试健康检查：所有实例健康"""
        discovery.register_service(
            service_name="service-1",
            instance_id="instance-1",
            host="localhost",
            port=8080
        )
        
        discovery.register_service(
            service_name="service-2",
            instance_id="instance-2",
            host="localhost",
            port=8081
        )
        
        result = discovery.health_check_services()
        
        assert result['total_services'] == 2
        assert result['total_instances'] == 2
        assert result['healthy_instances'] == 2
        assert result['unhealthy_instances'] == 0
        assert 'service-1' in result['services']
        assert 'service-2' in result['services']
    
    def test_health_check_services_with_timeout(self, discovery):
        """测试健康检查：心跳超时"""
        # 使用短超时时间
        discovery_short = ServiceDiscovery(heartbeat_timeout=1)
        
        discovery_short.register_service(
            service_name="test-service",
            instance_id="instance-1",
            host="localhost",
            port=8080
        )
        
        # 等待超过心跳超时时间
        time.sleep(1.5)
        
        result = discovery_short.health_check_services()
        
        assert result['total_instances'] == 1
        assert result['healthy_instances'] == 0
        assert result['unhealthy_instances'] == 1
        
        # 验证实例状态被标记为不健康
        instance = discovery_short.get_service_instance("test-service", "instance-1")
        assert instance.status == "unhealthy"
    
    def test_get_service_url_round_robin(self, discovery):
        """测试获取服务URL：轮询负载均衡"""
        discovery.register_service(
            service_name="test-service",
            instance_id="instance-1",
            host="host1",
            port=8080
        )
        
        discovery.register_service(
            service_name="test-service",
            instance_id="instance-2",
            host="host2",
            port=8081
        )
        
        url = discovery.get_service_url("test-service", load_balance="round_robin")
        
        assert url is not None
        assert url.startswith("http://")
        assert "host" in url
    
    def test_get_service_url_random(self, discovery):
        """测试获取服务URL：随机负载均衡"""
        discovery.register_service(
            service_name="test-service",
            instance_id="instance-1",
            host="host1",
            port=8080
        )
        
        url = discovery.get_service_url("test-service", load_balance="random")
        
        assert url is not None
        assert url == "http://host1:8080"
    
    def test_get_service_url_default(self, discovery):
        """测试获取服务URL：默认策略"""
        discovery.register_service(
            service_name="test-service",
            instance_id="instance-1",
            host="host1",
            port=8080
        )
        
        url = discovery.get_service_url("test-service", load_balance="unknown")
        
        assert url is not None
        assert url == "http://host1:8080"
    
    def test_get_service_url_no_healthy_instances(self, discovery):
        """测试获取服务URL：没有健康实例"""
        discovery.register_service(
            service_name="test-service",
            instance_id="instance-1",
            host="localhost",
            port=8080
        )
        
        # 标记为不健康
        instance = discovery.get_service_instance("test-service", "instance-1")
        instance.status = "unhealthy"
        
        url = discovery.get_service_url("test-service")
        
        assert url is None
    
    def test_get_service_url_nonexistent_service(self, discovery):
        """测试获取服务URL：服务不存在"""
        url = discovery.get_service_url("nonexistent-service")
        
        assert url is None
    
    def test_get_all_services(self, discovery):
        """测试获取所有服务名称"""
        discovery.register_service(
            service_name="service-1",
            instance_id="instance-1",
            host="localhost",
            port=8080
        )
        
        discovery.register_service(
            service_name="service-2",
            instance_id="instance-2",
            host="localhost",
            port=8081
        )
        
        services = discovery.get_all_services()
        
        assert len(services) == 2
        assert "service-1" in services
        assert "service-2" in services
    
    def test_get_service_count(self, discovery):
        """测试获取服务数量"""
        assert discovery.get_service_count() == 0
        
        discovery.register_service(
            service_name="service-1",
            instance_id="instance-1",
            host="localhost",
            port=8080
        )
        
        assert discovery.get_service_count() == 1
        
        discovery.register_service(
            service_name="service-2",
            instance_id="instance-2",
            host="localhost",
            port=8081
        )
        
        assert discovery.get_service_count() == 2
    
    def test_get_instance_count_all_services(self, discovery):
        """测试获取实例数量：所有服务"""
        discovery.register_service(
            service_name="service-1",
            instance_id="instance-1",
            host="localhost",
            port=8080
        )
        
        discovery.register_service(
            service_name="service-1",
            instance_id="instance-2",
            host="localhost",
            port=8081
        )
        
        discovery.register_service(
            service_name="service-2",
            instance_id="instance-3",
            host="localhost",
            port=8082
        )
        
        assert discovery.get_instance_count() == 3
    
    def test_get_instance_count_specific_service(self, discovery):
        """测试获取实例数量：指定服务"""
        discovery.register_service(
            service_name="service-1",
            instance_id="instance-1",
            host="localhost",
            port=8080
        )
        
        discovery.register_service(
            service_name="service-1",
            instance_id="instance-2",
            host="localhost",
            port=8081
        )
        
        assert discovery.get_instance_count("service-1") == 2
    
    def test_get_instance_count_nonexistent_service(self, discovery):
        """测试获取实例数量：服务不存在"""
        assert discovery.get_instance_count("nonexistent-service") == 0
    
    def test_get_statistics(self, discovery):
        """测试获取统计信息"""
        discovery.register_service(
            service_name="service-1",
            instance_id="instance-1",
            host="localhost",
            port=8080
        )
        
        discovery.discover_service("service-1")
        
        stats = discovery.get_statistics()
        
        assert stats['total_services'] == 1
        assert stats['total_instances'] == 1
        assert stats['total_registrations'] == 1
        assert stats['total_deregistrations'] == 0
        assert stats['total_discoveries'] == 1
        assert stats['heartbeat_timeout'] == 30
        assert stats['health_check_interval'] == 10
    
    def test_clear_registry(self, discovery):
        """测试清空注册表"""
        discovery.register_service(
            service_name="service-1",
            instance_id="instance-1",
            host="localhost",
            port=8080
        )
        
        discovery.clear_registry()
        
        assert len(discovery.registry) == 0
        assert discovery.get_service_count() == 0


class TestServiceInstance:
    """测试ServiceInstance数据类"""
    
    def test_service_instance_creation(self):
        """测试服务实例创建"""
        instance = ServiceInstance(
            service_name="test-service",
            instance_id="instance-1",
            host="localhost",
            port=8080,
            metadata={'version': '1.0.0'}
        )
        
        assert instance.service_name == "test-service"
        assert instance.instance_id == "instance-1"
        assert instance.host == "localhost"
        assert instance.port == 8080
        assert instance.metadata == {'version': '1.0.0'}
        assert instance.status == "healthy"
        assert instance.registered_at > 0
        assert instance.last_heartbeat > 0
    
    def test_service_instance_to_dict(self):
        """测试服务实例转换为字典"""
        instance = ServiceInstance(
            service_name="test-service",
            instance_id="instance-1",
            host="localhost",
            port=8080,
            metadata={'version': '1.0.0'}
        )
        
        data = instance.to_dict()
        
        assert isinstance(data, dict)
        assert data['service_name'] == "test-service"
        assert data['instance_id'] == "instance-1"
        assert data['host'] == "localhost"
        assert data['port'] == 8080
        assert data['metadata'] == {'version': '1.0.0'}
        assert data['status'] == "healthy"
        assert 'registered_at' in data
        assert 'last_heartbeat' in data
    
    def test_service_instance_default_metadata(self):
        """测试服务实例默认元数据"""
        instance = ServiceInstance(
            service_name="test-service",
            instance_id="instance-1",
            host="localhost",
            port=8080
        )
        
        assert instance.metadata == {}
