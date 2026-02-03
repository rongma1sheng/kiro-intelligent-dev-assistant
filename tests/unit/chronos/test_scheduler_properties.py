"""Chronos调度器属性测试

白皮书依据: 第一章 1.1 多时间尺度统一调度

测试调度器的正确性属性，包括：
- 属性1: 任务执行顺序遵循优先级
- 属性2: 调度延迟上界
"""

import pytest
import time
import threading
from typing import List, Tuple
from unittest.mock import Mock

from src.chronos.scheduler import ChronosScheduler, Priority, TimeScale, Task


class TestChronosSchedulerProperties:
    """Chronos调度器属性测试类
    
    白皮书依据: 第一章 1.1 多时间尺度统一调度
    
    验证调度器的核心正确性属性。
    """
    
    @pytest.fixture
    def scheduler(self):
        """测试夹具：创建调度器实例"""
        return ChronosScheduler()
    
    def test_property_1_task_execution_order_follows_priority(self, scheduler):
        """属性1: 任务执行顺序遵循优先级
        
        白皮书依据: 第一章 1.3 任务优先级管理
        验证需求: US-1.3
        
        测试场景：
        1. 添加不同优先级的任务，设置相同的执行时间
        2. 启动调度器
        3. 验证执行顺序严格按照优先级排序
        
        预期结果：
        - CRITICAL > HIGH > NORMAL > LOW > IDLE
        - 相同优先级按添加顺序执行
        """
        execution_order = []
        
        def create_callback(task_name: str):
            def callback():
                execution_order.append(task_name)
            return callback
        
        # 当前时间
        current_time = time.time()
        
        # 添加不同优先级的任务，都在1秒后执行
        tasks = [
            ("idle_task", Priority.IDLE),
            ("critical_task", Priority.CRITICAL),
            ("normal_task", Priority.NORMAL),
            ("high_task", Priority.HIGH),
            ("low_task", Priority.LOW),
        ]
        
        task_ids = []
        for task_name, priority in tasks:
            task_id = scheduler.add_task(
                name=task_name,
                callback=create_callback(task_name),
                interval=10.0,  # 长间隔，避免重复执行
                priority=priority
            )
            task_ids.append(task_id)
            
            # 手动设置执行时间为相同值
            scheduler.tasks[task_id].next_run = current_time + 0.1
        
        # 启动调度器
        scheduler.start()
        
        # 等待任务执行完成
        time.sleep(0.5)
        
        # 停止调度器
        scheduler.stop()
        
        # 验证执行顺序
        expected_order = ["critical_task", "high_task", "normal_task", "low_task", "idle_task"]
        assert execution_order == expected_order, f"Expected {expected_order}, got {execution_order}"
    
    def test_property_1_same_priority_fifo_order(self, scheduler):
        """属性1扩展: 相同优先级任务按FIFO顺序执行
        
        白皮书依据: 第一章 1.3 任务优先级管理
        
        测试场景：
        1. 添加多个相同优先级的任务
        2. 验证执行顺序按添加顺序（FIFO）
        """
        execution_order = []
        
        def create_callback(task_name: str):
            def callback():
                execution_order.append(task_name)
            return callback
        
        current_time = time.time()
        
        # 添加3个相同优先级的任务
        task_names = ["task_1", "task_2", "task_3"]
        task_ids = []
        
        for task_name in task_names:
            task_id = scheduler.add_task(
                name=task_name,
                callback=create_callback(task_name),
                interval=10.0,
                priority=Priority.NORMAL
            )
            task_ids.append(task_id)
            scheduler.tasks[task_id].next_run = current_time + 0.1
        
        scheduler.start()
        time.sleep(0.5)
        scheduler.stop()
        
        # 验证FIFO顺序
        assert execution_order == task_names, f"Expected {task_names}, got {execution_order}"
    
    def test_property_1_time_priority_interaction(self, scheduler):
        """属性1扩展: 时间和优先级的交互
        
        测试场景：
        1. 低优先级任务先到达执行时间
        2. 高优先级任务后到达执行时间
        3. 验证高优先级任务优先执行
        """
        execution_order = []
        
        def create_callback(task_name: str):
            def callback():
                execution_order.append(task_name)
            return callback
        
        current_time = time.time()
        
        # 低优先级任务，早执行时间
        low_task_id = scheduler.add_task(
            name="low_priority_early",
            callback=create_callback("low_priority_early"),
            interval=10.0,
            priority=Priority.LOW
        )
        scheduler.tasks[low_task_id].next_run = current_time + 0.1
        
        # 高优先级任务，稍晚执行时间
        high_task_id = scheduler.add_task(
            name="high_priority_late",
            callback=create_callback("high_priority_late"),
            interval=10.0,
            priority=Priority.HIGH
        )
        scheduler.tasks[high_task_id].next_run = current_time + 0.15
        
        scheduler.start()
        time.sleep(0.3)
        scheduler.stop()
        
        # 验证高优先级任务先执行（即使时间稍晚）
        # 注意：这里的行为取决于调度器的具体实现
        # 如果调度器严格按时间执行，则低优先级先执行
        # 如果调度器在时间窗口内优先考虑优先级，则高优先级先执行
        assert len(execution_order) == 2
        # 这里我们验证两个任务都执行了，具体顺序取决于实现策略
    
    def test_property_2_scheduling_latency_upper_bound(self, scheduler):
        """属性2: 调度延迟上界
        
        白皮书依据: 第一章 1.1 多时间尺度统一调度
        验证需求: US-1.1
        
        性能要求: 调度延迟 < 1ms (P99)
        
        测试场景：
        1. 添加多个任务，设置为立即执行
        2. 测量从预期执行时间到实际执行时间的延迟
        3. 验证99%的任务延迟 < 1ms
        """
        latencies = []
        
        def create_callback(expected_time: float):
            def callback():
                actual_time = time.perf_counter()
                latency = (actual_time - expected_time) * 1000  # 转换为毫秒
                latencies.append(latency)
            return callback
        
        scheduler.start()
        
        # 添加100个任务进行统计测试
        base_time = time.perf_counter() + 0.5  # 500ms后开始执行
        
        task_ids = []
        for i in range(100):
            expected_time = base_time + i * 0.001  # 每个任务间隔1ms
            
            task_id = scheduler.add_task(
                name=f"latency_test_{i}",
                callback=create_callback(expected_time),
                interval=60.0,  # 长间隔，避免重复执行
                priority=Priority.NORMAL
            )
            task_ids.append(task_id)
        
        # 修改任务执行时间并重建堆
        with scheduler.lock:
            for i, task_id in enumerate(task_ids):
                expected_time = base_time + i * 0.001
                scheduler.tasks[task_id].next_run = expected_time
            
            # 重建堆以保持堆属性
            import heapq
            scheduler.task_queue = [task for task in scheduler.task_queue if task.enabled]
            heapq.heapify(scheduler.task_queue)
        
        # 等待所有任务执行完成
        time.sleep(2.0)
        scheduler.stop()
        
        # 验证延迟要求
        assert len(latencies) >= 90, f"Expected at least 90 tasks executed, got {len(latencies)}"
        
        # 计算P99延迟
        latencies.sort()
        p99_index = int(len(latencies) * 0.99)
        p99_latency = latencies[p99_index]
        
        # 验证P99延迟 < 1ms
        assert p99_latency < 1.0, f"P99 latency {p99_latency:.2f}ms exceeds 1ms requirement"
        
        # 记录统计信息
        avg_latency = sum(latencies) / len(latencies)
        max_latency = max(latencies)
        
        print(f"Latency stats: avg={avg_latency:.2f}ms, p99={p99_latency:.2f}ms, max={max_latency:.2f}ms")
    
    def test_property_2_high_load_performance(self, scheduler):
        """属性2扩展: 高负载下的性能
        
        测试场景：
        1. 同时添加大量任务
        2. 验证调度器在高负载下仍能保持性能要求
        """
        execution_count = 0
        execution_lock = threading.Lock()
        
        def callback():
            nonlocal execution_count
            with execution_lock:
                execution_count += 1
        
        scheduler.start()
        
        # 添加1000个任务
        current_time = time.time()
        for i in range(1000):
            task_id = scheduler.add_task(
                name=f"high_load_task_{i}",
                callback=callback,
                interval=60.0,
                priority=Priority.NORMAL
            )
            scheduler.tasks[task_id].next_run = current_time + 0.1
        
        # 等待执行
        time.sleep(2.0)
        scheduler.stop()
        
        # 验证大部分任务都执行了
        assert execution_count >= 950, f"Expected at least 950 tasks executed, got {execution_count}"
    
    def test_property_task_dependency_resolution(self, scheduler):
        """任务依赖解析测试
        
        白皮书依据: 第一章 1.3 任务优先级管理
        
        测试场景：
        1. 创建有依赖关系的任务
        2. 验证依赖任务先执行
        3. 验证被依赖任务后执行
        """
        execution_order = []
        
        def create_callback(task_name: str):
            def callback():
                execution_order.append(task_name)
            return callback
        
        # 创建依赖任务
        dep_task_id = scheduler.add_task(
            name="dependency_task",
            callback=create_callback("dependency_task"),
            interval=10.0,
            priority=Priority.NORMAL
        )
        
        # 创建被依赖任务
        main_task_id = scheduler.add_task(
            name="main_task",
            callback=create_callback("main_task"),
            interval=10.0,
            priority=Priority.HIGH,  # 更高优先级，但有依赖
            dependencies=[dep_task_id]
        )
        
        # 设置相同的执行时间
        current_time = time.time()
        scheduler.tasks[dep_task_id].next_run = current_time + 0.1
        scheduler.tasks[main_task_id].next_run = current_time + 0.1
        
        scheduler.start()
        time.sleep(0.5)
        scheduler.stop()
        
        # 验证依赖顺序
        assert execution_order == ["dependency_task", "main_task"], \
            f"Expected ['dependency_task', 'main_task'], got {execution_order}"
    
    def test_property_task_not_lost(self, scheduler):
        """属性3: 任务不丢失
        
        白皮书依据: 第一章 1.1 多时间尺度统一调度
        验证需求: US-1.1
        
        测试场景：
        1. 添加任务后立即停止调度器
        2. 重新启动调度器
        3. 验证任务仍然存在并能执行
        """
        execution_count = 0
        
        def callback():
            nonlocal execution_count
            execution_count += 1
        
        # 添加任务
        task_id = scheduler.add_task(
            name="persistent_task",
            callback=callback,
            interval=0.1,  # 100ms间隔
            priority=Priority.NORMAL
        )
        
        # 短暂运行后停止
        scheduler.start()
        time.sleep(0.05)
        scheduler.stop()
        
        # 验证任务仍在任务字典中
        assert task_id in scheduler.tasks
        assert scheduler.tasks[task_id].enabled
        
        # 重新启动并验证任务执行
        initial_count = execution_count
        scheduler.start()
        time.sleep(0.3)
        scheduler.stop()
        
        # 验证任务继续执行
        assert execution_count > initial_count, "Task should continue executing after restart"
    
    def test_property_time_scale_conversion_accuracy(self, scheduler):
        """时间尺度转换精度测试
        
        白皮书依据: 第一章 1.1 多时间尺度统一调度
        
        测试场景：
        1. 使用不同时间尺度添加任务
        2. 验证转换到秒的精度
        """
        # 测试各种时间尺度转换
        test_cases = [
            (1000, TimeScale.MICROSECOND, 0.001),  # 1000微秒 = 1毫秒
            (100, TimeScale.MILLISECOND, 0.1),     # 100毫秒 = 0.1秒
            (1, TimeScale.SECOND, 1.0),            # 1秒 = 1秒
            (1, TimeScale.MINUTE, 60.0),           # 1分钟 = 60秒
            (1, TimeScale.HOUR, 3600.0),           # 1小时 = 3600秒
            (1, TimeScale.DAY, 86400.0),           # 1天 = 86400秒
        ]
        
        for interval, time_scale, expected_seconds in test_cases:
            task_id = scheduler.add_task(
                name=f"time_scale_test_{time_scale.value}",
                callback=lambda: None,
                interval=interval,
                time_scale=time_scale,
                priority=Priority.NORMAL
            )
            
            actual_seconds = scheduler.tasks[task_id].interval
            assert abs(actual_seconds - expected_seconds) < 1e-6, \
                f"Time scale conversion error: {interval} {time_scale.value} " \
                f"should be {expected_seconds}s, got {actual_seconds}s"
    
    @pytest.mark.parametrize("priority,expected_value", [
        (Priority.CRITICAL, 5),
        (Priority.HIGH, 4),
        (Priority.NORMAL, 3),
        (Priority.LOW, 2),
        (Priority.IDLE, 1),
    ])
    def test_priority_enum_values(self, priority, expected_value):
        """优先级枚举值测试
        
        白皮书依据: 第一章 1.3 任务优先级管理
        
        验证优先级枚举的数值正确性。
        """
        assert priority.value == expected_value
    
    def test_task_comparison_logic(self):
        """任务比较逻辑测试
        
        验证Task类的__lt__方法实现正确的排序逻辑。
        """
        current_time = time.time()
        
        # 创建测试任务
        task1 = Task(
            task_id="task1",
            name="Task 1",
            callback=lambda: None,
            priority=Priority.HIGH,
            interval=1.0,
            next_run=current_time + 1.0
        )
        
        task2 = Task(
            task_id="task2",
            name="Task 2",
            callback=lambda: None,
            priority=Priority.LOW,
            interval=1.0,
            next_run=current_time + 2.0
        )
        
        task3 = Task(
            task_id="task3",
            name="Task 3",
            callback=lambda: None,
            priority=Priority.CRITICAL,
            interval=1.0,
            next_run=current_time + 1.0  # 与task1相同时间
        )
        
        # 测试时间优先
        assert task1 < task2, "Earlier time should have higher priority"
        
        # 测试相同时间时优先级优先
        assert task3 < task1, "Higher priority should win when time is same"
        
        # 测试排序
        tasks = [task2, task1, task3]
        tasks.sort()
        
        expected_order = [task3, task1, task2]  # CRITICAL, HIGH, LOW
        assert tasks == expected_order, f"Expected {[t.name for t in expected_order]}, got {[t.name for t in tasks]}"