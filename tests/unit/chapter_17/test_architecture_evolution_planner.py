"""Unit Tests for ArchitectureEvolutionPlanner

白皮书依据: 第十七章 17.0 架构演进规划

测试覆盖:
- 水平扩展规划
- 微服务架构设计
- 渐进式迁移规划
- 边界条件和异常情况
"""

import pytest
from src.planning.architecture_evolution_planner import (
    ArchitectureEvolutionPlanner,
    ScalingStrategy,
    MigrationPhase,
    ScalingPlan,
    MicroserviceSpec,
    MigrationPlan
)


class TestArchitectureEvolutionPlanner:
    """测试ArchitectureEvolutionPlanner类"""
    
    @pytest.fixture
    def planner(self):
        """测试夹具：创建规划器实例"""
        return ArchitectureEvolutionPlanner(
            current_architecture="monolithic",
            target_architecture="microservices"
        )
    
    def test_init_success(self):
        """测试初始化成功"""
        planner = ArchitectureEvolutionPlanner(
            current_architecture="monolithic",
            target_architecture="microservices"
        )
        
        assert planner.current_architecture == "monolithic"
        assert planner.target_architecture == "microservices"
    
    def test_init_invalid_current_architecture(self):
        """测试初始化失败：无效的当前架构"""
        with pytest.raises(ValueError, match="无效的当前架构类型"):
            ArchitectureEvolutionPlanner(
                current_architecture="invalid",
                target_architecture="microservices"
            )
    
    def test_init_invalid_target_architecture(self):
        """测试初始化失败：无效的目标架构"""
        with pytest.raises(ValueError, match="无效的目标架构类型"):
            ArchitectureEvolutionPlanner(
                current_architecture="monolithic",
                target_architecture="invalid"
            )
    
    def test_plan_horizontal_scaling_vertical_strategy(self, planner):
        """测试水平扩展规划：垂直扩展策略（2倍以内）"""
        plan = planner.plan_horizontal_scaling(
            current_aum=10_000_000,
            target_aum=15_000_000
        )
        
        assert isinstance(plan, ScalingPlan)
        assert plan.current_aum == 10_000_000
        assert plan.target_aum == 15_000_000
        assert plan.strategy == ScalingStrategy.VERTICAL
        assert len(plan.components) > 0
        assert plan.estimated_cost > 0
        assert plan.timeline_days > 0
    
    def test_plan_horizontal_scaling_hybrid_strategy(self, planner):
        """测试水平扩展规划：混合扩展策略（2-5倍）"""
        plan = planner.plan_horizontal_scaling(
            current_aum=10_000_000,
            target_aum=30_000_000
        )
        
        assert plan.strategy == ScalingStrategy.HYBRID
        assert len(plan.components) > 0
    
    def test_plan_horizontal_scaling_horizontal_strategy(self, planner):
        """测试水平扩展规划：水平扩展策略（5倍以上）"""
        plan = planner.plan_horizontal_scaling(
            current_aum=10_000_000,
            target_aum=100_000_000
        )
        
        assert plan.strategy == ScalingStrategy.HORIZONTAL
        assert len(plan.components) > 0
        # 验证包含关键组件
        component_names = [c['name'] for c in plan.components]
        assert 'Soldier Service' in component_names
        assert 'Redis Cluster' in component_names
        assert 'Execution Service' in component_names
    
    def test_plan_horizontal_scaling_invalid_current_aum(self, planner):
        """测试水平扩展规划失败：无效的当前资金规模"""
        with pytest.raises(ValueError, match="当前资金规模必须 > 0"):
            planner.plan_horizontal_scaling(
                current_aum=0,
                target_aum=100_000_000
            )
    
    def test_plan_horizontal_scaling_invalid_target_aum(self, planner):
        """测试水平扩展规划失败：目标资金规模小于当前"""
        with pytest.raises(ValueError, match="目标资金规模必须 > 当前资金规模"):
            planner.plan_horizontal_scaling(
                current_aum=100_000_000,
                target_aum=50_000_000
            )
    
    def test_design_microservices_architecture(self, planner):
        """测试微服务架构设计"""
        services = planner.design_microservices_architecture()
        
        assert isinstance(services, list)
        assert len(services) == 6  # 6个核心微服务
        
        # 验证所有服务都是MicroserviceSpec类型
        for service in services:
            assert isinstance(service, MicroserviceSpec)
            assert service.name
            assert service.description
            assert len(service.responsibilities) > 0
            assert isinstance(service.dependencies, list)
            assert len(service.api_endpoints) > 0
            assert isinstance(service.resource_requirements, dict)
        
        # 验证服务名称
        service_names = [s.name for s in services]
        assert "soldier-service" in service_names
        assert "radar-service" in service_names
        assert "execution-service" in service_names
        assert "auditor-service" in service_names
        assert "data-service" in service_names
        assert "config-service" in service_names
    
    def test_plan_gradual_migration_default_duration(self, planner):
        """测试渐进式迁移规划：默认持续时间"""
        plans = planner.plan_gradual_migration()
        
        assert isinstance(plans, list)
        assert len(plans) == 5  # 5个迁移阶段
        
        # 验证所有阶段
        phases = [p.phase for p in plans]
        assert MigrationPhase.PREPARATION in phases
        assert MigrationPhase.PILOT in phases
        assert MigrationPhase.GRADUAL_ROLLOUT in phases
        assert MigrationPhase.FULL_MIGRATION in phases
        assert MigrationPhase.OPTIMIZATION in phases
        
        # 验证时间分配
        total_duration = sum(p.duration_days for p in plans)
        assert total_duration == 90  # 默认90天
        
        # 验证每个阶段的属性
        for plan in plans:
            assert isinstance(plan, MigrationPlan)
            assert plan.duration_days > 0
            assert len(plan.tasks) > 0
            assert len(plan.success_criteria) > 0
            assert plan.rollback_plan
    
    def test_plan_gradual_migration_custom_duration(self, planner):
        """测试渐进式迁移规划：自定义持续时间"""
        plans = planner.plan_gradual_migration(total_duration_days=120)
        
        total_duration = sum(p.duration_days for p in plans)
        assert total_duration == 120
    
    def test_plan_gradual_migration_invalid_duration(self, planner):
        """测试渐进式迁移规划失败：无效的持续时间"""
        with pytest.raises(ValueError, match="总持续时间必须 > 0"):
            planner.plan_gradual_migration(total_duration_days=0)
    
    def test_plan_components_vertical(self, planner):
        """测试组件规划：垂直扩展"""
        components = planner._plan_components(1.5, ScalingStrategy.VERTICAL)
        
        assert len(components) > 0
        assert components[0]['type'] == 'hardware_upgrade'
        assert 'cpu_cores' in components[0]['details']
        assert 'memory_gb' in components[0]['details']
        assert 'gpu_memory_gb' in components[0]['details']
    
    def test_plan_components_horizontal(self, planner):
        """测试组件规划：水平扩展"""
        components = planner._plan_components(10.0, ScalingStrategy.HORIZONTAL)
        
        assert len(components) >= 3
        component_names = [c['name'] for c in components]
        assert 'Soldier Service' in component_names
        assert 'Redis Cluster' in component_names
        assert 'Execution Service' in component_names
    
    def test_plan_components_hybrid(self, planner):
        """测试组件规划：混合扩展"""
        components = planner._plan_components(3.0, ScalingStrategy.HYBRID)
        
        assert len(components) >= 2
        component_types = [c['type'] for c in components]
        assert 'hardware_upgrade' in component_types
        assert 'service_replication' in component_types
    
    def test_estimate_cost_vertical(self, planner):
        """测试成本估算：垂直扩展"""
        cost = planner._estimate_cost(2.0, ScalingStrategy.VERTICAL)
        
        assert cost > 0
        assert cost == 50000 * 2.0 * 1.5  # 基础成本 * 倍数 * 系数
    
    def test_estimate_cost_horizontal(self, planner):
        """测试成本估算：水平扩展"""
        cost = planner._estimate_cost(10.0, ScalingStrategy.HORIZONTAL)
        
        assert cost > 0
        assert cost == 50000 * 10.0  # 基础成本 * 倍数
    
    def test_estimate_cost_hybrid(self, planner):
        """测试成本估算：混合扩展"""
        cost = planner._estimate_cost(3.0, ScalingStrategy.HYBRID)
        
        assert cost > 0
        assert cost == 50000 * 3.0 * 2.0  # 基础成本 * 倍数 * 系数
    
    def test_estimate_timeline_vertical(self, planner):
        """测试时间估算：垂直扩展"""
        days = planner._estimate_timeline(2.0, ScalingStrategy.VERTICAL)
        
        assert days > 0
        assert days == int(30 * 0.5)  # 基础时间 * 系数
    
    def test_estimate_timeline_horizontal(self, planner):
        """测试时间估算：水平扩展"""
        days = planner._estimate_timeline(10.0, ScalingStrategy.HORIZONTAL)
        
        assert days > 0
        assert days == int(30 * 10.0 * 0.3)  # 基础时间 * 倍数 * 系数
    
    def test_estimate_timeline_hybrid(self, planner):
        """测试时间估算：混合扩展"""
        days = planner._estimate_timeline(3.0, ScalingStrategy.HYBRID)
        
        assert days > 0
        assert days == int(30 * 3.0 * 0.2)  # 基础时间 * 倍数 * 系数
    
    def test_design_soldier_service(self, planner):
        """测试Soldier服务设计"""
        service = planner._design_soldier_service()
        
        assert service.name == "soldier-service"
        assert service.description == "AI决策服务"
        assert len(service.responsibilities) == 3
        assert "redis" in service.dependencies
        assert "config-service" in service.dependencies
        assert len(service.api_endpoints) == 3
        assert service.resource_requirements['cpu_cores'] == 4
        assert service.resource_requirements['memory_gb'] == 8
        assert service.resource_requirements['gpu_memory_gb'] == 4
    
    def test_design_radar_service(self, planner):
        """测试Radar服务设计"""
        service = planner._design_radar_service()
        
        assert service.name == "radar-service"
        assert "redis" in service.dependencies
        assert "data-service" in service.dependencies
    
    def test_design_execution_service(self, planner):
        """测试Execution服务设计"""
        service = planner._design_execution_service()
        
        assert service.name == "execution-service"
        assert "redis" in service.dependencies
        assert "auditor-service" in service.dependencies
    
    def test_design_auditor_service(self, planner):
        """测试Auditor服务设计"""
        service = planner._design_auditor_service()
        
        assert service.name == "auditor-service"
        assert "redis" in service.dependencies
    
    def test_design_data_service(self, planner):
        """测试Data服务设计"""
        service = planner._design_data_service()
        
        assert service.name == "data-service"
        assert "redis" in service.dependencies
    
    def test_design_config_service(self, planner):
        """测试Config服务设计"""
        service = planner._design_config_service()
        
        assert service.name == "config-service"
        assert len(service.dependencies) == 0  # Config服务无依赖
    
    def test_plan_preparation_phase(self, planner):
        """测试准备阶段规划"""
        phase = planner._plan_preparation_phase()
        
        assert phase.phase == MigrationPhase.PREPARATION
        assert len(phase.tasks) == 5
        assert len(phase.success_criteria) == 4
        assert "无需回滚" in phase.rollback_plan
    
    def test_plan_pilot_phase(self, planner):
        """测试试点阶段规划"""
        phase = planner._plan_pilot_phase()
        
        assert phase.phase == MigrationPhase.PILOT
        assert len(phase.tasks) == 5
        assert len(phase.success_criteria) == 4
        assert "回退到单体架构" in phase.rollback_plan
    
    def test_plan_gradual_rollout_phase(self, planner):
        """测试渐进推出阶段规划"""
        phase = planner._plan_gradual_rollout_phase()
        
        assert phase.phase == MigrationPhase.GRADUAL_ROLLOUT
        assert len(phase.tasks) == 5
        assert len(phase.success_criteria) == 4
        assert "逐个服务回退" in phase.rollback_plan
    
    def test_plan_full_migration_phase(self, planner):
        """测试全面迁移阶段规划"""
        phase = planner._plan_full_migration_phase()
        
        assert phase.phase == MigrationPhase.FULL_MIGRATION
        assert len(phase.tasks) == 5
        assert len(phase.success_criteria) == 4
        assert "紧急回退" in phase.rollback_plan
    
    def test_plan_optimization_phase(self, planner):
        """测试优化阶段规划"""
        phase = planner._plan_optimization_phase()
        
        assert phase.phase == MigrationPhase.OPTIMIZATION
        assert len(phase.tasks) == 5
        assert len(phase.success_criteria) == 4
        assert "无需回滚" in phase.rollback_plan
    
    def test_allocate_time(self, planner):
        """测试时间分配"""
        durations = planner._allocate_time(100, 5)
        
        assert len(durations) == 5
        assert sum(durations) == 100
        
        # 验证比例大致正确（准备15%，试点20%，渐进30%，全面25%，优化10%）
        assert durations[0] == 15  # 准备阶段
        assert durations[1] == 20  # 试点阶段
        assert durations[2] == 30  # 渐进阶段
        assert durations[3] == 25  # 全面迁移
        assert durations[4] == 10  # 优化阶段
    
    def test_allocate_time_with_remainder(self, planner):
        """测试时间分配：有余数"""
        durations = planner._allocate_time(101, 5)
        
        assert sum(durations) == 101
        # 余数应该加到渐进阶段
        assert durations[2] >= 30


class TestScalingPlan:
    """测试ScalingPlan数据类"""
    
    def test_scaling_plan_creation(self):
        """测试扩展计划创建"""
        plan = ScalingPlan(
            current_aum=10_000_000,
            target_aum=100_000_000,
            strategy=ScalingStrategy.HORIZONTAL,
            components=[{'name': 'test'}],
            estimated_cost=500_000,
            timeline_days=60
        )
        
        assert plan.current_aum == 10_000_000
        assert plan.target_aum == 100_000_000
        assert plan.strategy == ScalingStrategy.HORIZONTAL
        assert len(plan.components) == 1
        assert plan.estimated_cost == 500_000
        assert plan.timeline_days == 60


class TestMicroserviceSpec:
    """测试MicroserviceSpec数据类"""
    
    def test_microservice_spec_creation(self):
        """测试微服务规格创建"""
        spec = MicroserviceSpec(
            name="test-service",
            description="测试服务",
            responsibilities=["任务1", "任务2"],
            dependencies=["redis"],
            api_endpoints=["/api/v1/test"],
            resource_requirements={'cpu_cores': 2}
        )
        
        assert spec.name == "test-service"
        assert spec.description == "测试服务"
        assert len(spec.responsibilities) == 2
        assert len(spec.dependencies) == 1
        assert len(spec.api_endpoints) == 1
        assert spec.resource_requirements['cpu_cores'] == 2


class TestMigrationPlan:
    """测试MigrationPlan数据类"""
    
    def test_migration_plan_creation(self):
        """测试迁移计划创建"""
        plan = MigrationPlan(
            phase=MigrationPhase.PILOT,
            duration_days=20,
            tasks=["任务1", "任务2"],
            success_criteria=["标准1"],
            rollback_plan="回滚方案"
        )
        
        assert plan.phase == MigrationPhase.PILOT
        assert plan.duration_days == 20
        assert len(plan.tasks) == 2
        assert len(plan.success_criteria) == 1
        assert plan.rollback_plan == "回滚方案"


class TestScalingStrategy:
    """测试ScalingStrategy枚举"""
    
    def test_scaling_strategy_values(self):
        """测试扩展策略枚举值"""
        assert ScalingStrategy.VERTICAL.value == "vertical"
        assert ScalingStrategy.HORIZONTAL.value == "horizontal"
        assert ScalingStrategy.HYBRID.value == "hybrid"


class TestMigrationPhase:
    """测试MigrationPhase枚举"""
    
    def test_migration_phase_values(self):
        """测试迁移阶段枚举值"""
        assert MigrationPhase.PREPARATION.value == "preparation"
        assert MigrationPhase.PILOT.value == "pilot"
        assert MigrationPhase.GRADUAL_ROLLOUT.value == "gradual_rollout"
        assert MigrationPhase.FULL_MIGRATION.value == "full_migration"
        assert MigrationPhase.OPTIMIZATION.value == "optimization"
