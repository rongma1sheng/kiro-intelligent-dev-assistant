"""Chronos调度器单元测试

白皮书依据: 第一章 柯罗诺斯生物钟与资源调度

测试覆盖:
- 枚举值有效性
- Task数据类创建和验证
- ChronosScheduler基础功能
- 边界条件和异常情况
"""

import pytest
import time
from unittest.mock import Mock, patch
from threading import Event

from src.chronos.scheduler import (
    Priority, TimeScale, Task, ChronosScheduler
)


class TestPriority:
    """Priority枚举测试"""
    
    def test_priority_values(self):
        """测试优先级数值"""
        assert Priority.CRITICAL.value == 5
        assert Priority.HIGH.value == 4
        assert Priority.NORMAL.value == 3
        assert Priority.LOW.value == 2
        assert Priority.IDLE.value == 1
    
    def test_priority_ordering(self):
        """测试优先级排序"""
        priorities = [Priority.IDLE, Priority.CRITICAL, Priority.NORMAL]
        sorted_priorities = sorted(priorities, key=lambda p: p.value, reverse=True)
        
        assert sorted_priorities == [Priority.CRITICAL, Priority.NORMAL, Priority.IDLE]
    
    def test_priority_enum_completeness(self):
        """测试优先级枚举完整性"""
        expected_priorities = {'CRITICAL', 'HIGH', 'NORMAL', 'LOW', 'IDLE'}
        actual_priorities = {p.name for p in Priority}
        
        assert actual_priorities == expected_priorities


class TestTimeScale:
    """TimeScale枚举测试"""
    
    def test_time_scale_values(self):
        """测试时间尺度值"""
        assert TimeScale.MICROSECOND.value == "microsecond"
        assert TimeScale.MILLISECOND.value == "millisecond"
        assert TimeScale.SECOND.value == "second"
        assert TimeScale.MINUTE.value == "minute"
        assert TimeScale.HOUR.value == "hour"
        assert TimeScale.DAY.value == "day"
        assert TimeScale.YEAR.value == "year"
    
    def test_time_scale_completeness(self):
        """测试时间尺度枚举完整性"""
        expected_scales = {
            'MICROSECOND', 'MILLISECOND', 'SECOND', 
            'MINUTE', 'HOUR', 'DAY', 'YEAR'
        }
        actual_scales = {ts.name for ts in TimeScale}
        
        assert actual_scales == expected_scales


class TestTask:
    """Task数据类测试"""
    
    @pytest.fixture
    def mock_callback(self):
        """测试回调函数"""
        return Mock()
    
    @pytest.fixture
    def valid_task_data(self, mock_callback):
        """有效的任务数据"""
        return {
            "task_id": "test_task_001",
            "name": "测试任务",
            "callback": mock_callback,
            "priority": Priority.NORMAL,
            "interval": 60.0,
            "next_run": time.time() + 60.0
        }
    
    def test_task_creation_valid(self, valid_task_data):
        """测试有效任务创建"""
        task = Task(**valid_task_data)
        
        assert task.task_id == "test_task_001"
        assert task.name == "测试任务"
        assert task.priority == Priority.NORMAL
        assert task.interval == 60.0
        assert task.enabled is True
        assert task.dependencies == []
        assert task.execution_count == 0
        assert task.last_execution_time is None
    
    def test_task_creation_with_dependencies(self, valid_task_data):
        """测试带依赖的任务创建"""
        valid_task_data["dependencies"] = ["dep1", "dep2"]
        task = Task(**valid_task_data)
        
        assert task.dependencies == ["dep1", "dep2"]
    
    def test_task_creation_invalid_task_id(self, valid_task_data):
        """测试无效task_id"""
        valid_task_data["task_id"] = ""
        
        with pytest.raises(ValueError, match="task_id不能为空"):
            Task(**valid_task_data)
    
    def test_task_creation_invalid_name(self, valid_task_data):
        """测试无效name"""
        valid_task_data["name"] = ""
        
        with pytest.raises(ValueError, match="name不能为空"):
            Task(**valid_task_data)
    
    def test_task_creation_invalid_callback(self, valid_task_data):
        """测试无效callback"""
        valid_task_data["callback"] = "not_callable"
        
        with pytest.raises(ValueError, match="callback必须是可调用对象"):
            Task(**valid_task_data)
    
    def test_task_creation_invalid_interval(self, valid_task_data):
        """测试无效interval"""
        valid_task_data["interval"] = -1.0
        
        with pytest.raises(ValueError, match="interval必须 > 0"):
            Task(**valid_task_data)
        
        valid_task_data["interval"] = 0.0
        
        with pytest.raises(ValueError, match="interval必须 > 0"):
            Task(**valid_task_data)
    
    def test_task_creation_invalid_next_run(self, valid_task_data):
        """测试无效next_run"""
        valid_task_data["next_run"] = -1.0
        
        with pytest.raises(ValueError, match="next_run必须 > 0"):
            Task(**valid_task_data)
        
        valid_task_data["next_run"] = 0.0
        
        with pytest.raises(ValueError, match="next_run必须 > 0"):
            Task(**valid_task_data)
    
    def test_task_comparison_by_time(self, mock_callback):
        """测试任务按时间排序"""
        current_time = time.time()
        
        task1 = Task(
            task_id="task1", name="Task 1", callback=mock_callback,
            priority=Priority.NORMAL, interval=60.0, next_run=current_time + 10
        )
        
        task2 = Task(
            task_id="task2", name="Task 2", callback=mock_callback,
            priority=Priority.NORMAL, interval=60.0, next_run=current_time + 20
        )
        
        assert task1 < task2
        assert not (task2 < task1)
    
    def test_task_comparison_by_priority(self, mock_callback):
        """测试任务按优先级排序（时间相同时）"""
        current_time = time.time()
        next_run = current_time + 60
        
        task_high = Task(
            task_id="task_high", name="High Priority", callback=mock_callback,
            priority=Priority.HIGH, interval=60.0, next_run=next_run
        )
        
        task_low = Task(
            task_id="task_low", name="Low Priority", callback=mock_callback,
            priority=Priority.LOW, interval=60.0, next_run=next_run
        )
        
        # 优先级高的任务应该"小于"优先级低的任务（在优先队列中先执行）
        assert task_high < task_low
        assert not (task_low < task_high)
    
    def test_should_execute_enabled_and_time_reached(self, valid_task_data):
        """测试应该执行：启用且时间到达"""
        valid_task_data["next_run"] = time.time() - 1  # 1秒前
        task = Task(**valid_task_data)
        
        assert task.should_execute(time.time())
    
    def test_should_execute_disabled(self, valid_task_data):
        """测试不应该执行：任务禁用"""
        valid_task_data["next_run"] = time.time() - 1  # 1秒前
        valid_task_data["enabled"] = False
        task = Task(**valid_task_data)
        
        assert not task.should_execute(time.time())
    
    def test_should_execute_time_not_reached(self, valid_task_data):
        """测试不应该执行：时间未到"""
        valid_task_data["next_run"] = time.time() + 60  # 1分钟后
        task = Task(**valid_task_data)
        
        assert not task.should_execute(time.time())
    
    def test_update_next_run(self, valid_task_data):
        """测试更新下次执行时间"""
        task = Task(**valid_task_data)
        current_time = time.time()
        original_count = task.execution_count
        
        task.update_next_run(current_time)
        
        assert task.next_run == current_time + task.interval
        assert task.execution_count == original_count + 1
        assert task.last_execution_time == current_time


class TestChronosScheduler:
    """ChronosScheduler类测试"""
    
    @pytest.fixture
    def scheduler(self):
        """调度器实例"""
        return ChronosScheduler()
    
    @pytest.fixture
    def mock_callback(self):
        """测试回调函数"""
        return Mock()
    
    def test_scheduler_initialization(self, scheduler):
        """测试调度器初始化"""
        assert scheduler.tasks == {}
        assert scheduler.task_queue == []
        assert scheduler.running is False
        assert scheduler.scheduler_thread is None
        assert scheduler.lock is not None
        assert scheduler._time_scale_conversions is not None
    
    def test_time_scale_conversions(self, scheduler):
        """测试时间尺度转换"""
        conversions = scheduler._time_scale_conversions
        
        assert conversions[TimeScale.MICROSECOND] == 1e-6
        assert conversions[TimeScale.MILLISECOND] == 1e-3
        assert conversions[TimeScale.SECOND] == 1.0
        assert conversions[TimeScale.MINUTE] == 60.0
        assert conversions[TimeScale.HOUR] == 3600.0
        assert conversions[TimeScale.DAY] == 86400.0
        assert conversions[TimeScale.YEAR] == 31536000.0
    
    def test_convert_to_seconds(self, scheduler):
        """测试时间转换为秒"""
        assert scheduler._convert_to_seconds(1, TimeScale.MICROSECOND) == 1e-6
        assert scheduler._convert_to_seconds(1, TimeScale.MILLISECOND) == 1e-3
        assert scheduler._convert_to_seconds(1, TimeScale.SECOND) == 1.0
        assert scheduler._convert_to_seconds(1, TimeScale.MINUTE) == 60.0
        assert scheduler._convert_to_seconds(1, TimeScale.HOUR) == 3600.0
        assert scheduler._convert_to_seconds(1, TimeScale.DAY) == 86400.0
        assert scheduler._convert_to_seconds(1, TimeScale.YEAR) == 31536000.0
    
    def test_add_task_valid(self, scheduler, mock_callback):
        """测试添加有效任务"""
        task_id = scheduler.add_task(
            name="test_task",
            callback=mock_callback,
            interval=1.0,
            priority=Priority.NORMAL
        )
        
        assert task_id is not None
        assert task_id.startswith("test_task_")
        assert task_id in scheduler.tasks
        assert len(scheduler.task_queue) == 1
        
        task = scheduler.tasks[task_id]
        assert task.name == "test_task"
        assert task.callback == mock_callback
        assert task.interval == 1.0
        assert task.priority == Priority.NORMAL
    
    def test_add_task_with_time_scale(self, scheduler, mock_callback):
        """测试添加带时间尺度的任务"""
        task_id = scheduler.add_task(
            name="minute_task",
            callback=mock_callback,
            interval=1.0,
            time_scale=TimeScale.MINUTE
        )
        
        task = scheduler.tasks[task_id]
        assert task.interval == 60.0  # 1分钟 = 60秒
    
    def test_add_task_with_dependencies(self, scheduler, mock_callback):
        """测试添加带依赖的任务"""
        task_id = scheduler.add_task(
            name="dependent_task",
            callback=mock_callback,
            interval=1.0,
            dependencies=["dep1", "dep2"]
        )
        
        task = scheduler.tasks[task_id]
        assert task.dependencies == ["dep1", "dep2"]
    
    def test_add_task_invalid_name(self, scheduler, mock_callback):
        """测试添加无效名称的任务"""
        with pytest.raises(ValueError, match="任务名称不能为空"):
            scheduler.add_task(
                name="",
                callback=mock_callback,
                interval=1.0
            )
    
    def test_add_task_invalid_callback(self, scheduler):
        """测试添加无效回调的任务"""
        with pytest.raises(ValueError, match="callback必须是可调用对象"):
            scheduler.add_task(
                name="test_task",
                callback="not_callable",
                interval=1.0
            )
    
    def test_add_task_invalid_interval(self, scheduler, mock_callback):
        """测试添加无效间隔的任务"""
        with pytest.raises(ValueError, match="interval必须 > 0"):
            scheduler.add_task(
                name="test_task",
                callback=mock_callback,
                interval=-1.0
            )
        
        with pytest.raises(ValueError, match="interval必须 > 0"):
            scheduler.add_task(
                name="test_task",
                callback=mock_callback,
                interval=0.0
            )
    
    def test_remove_task_existing(self, scheduler, mock_callback):
        """测试移除存在的任务"""
        task_id = scheduler.add_task(
            name="test_task",
            callback=mock_callback,
            interval=1.0
        )
        
        result = scheduler.remove_task(task_id)
        
        assert result is True
        assert task_id not in scheduler.tasks
    
    def test_remove_task_nonexistent(self, scheduler):
        """测试移除不存在的任务"""
        result = scheduler.remove_task("nonexistent_task")
        
        assert result is False
    
    def test_get_task_info_existing(self, scheduler, mock_callback):
        """测试获取存在任务的信息"""
        task_id = scheduler.add_task(
            name="test_task",
            callback=mock_callback,
            interval=60.0,
            priority=Priority.HIGH,
            dependencies=["dep1"]
        )
        
        info = scheduler.get_task_info(task_id)
        
        assert info is not None
        assert info["task_id"] == task_id
        assert info["name"] == "test_task"
        assert info["priority"] == "HIGH"
        assert info["interval"] == 60.0
        assert info["enabled"] is True
        assert info["execution_count"] == 0
        assert info["last_execution_time"] is None
        assert info["dependencies"] == ["dep1"]
    
    def test_get_task_info_nonexistent(self, scheduler):
        """测试获取不存在任务的信息"""
        info = scheduler.get_task_info("nonexistent_task")
        
        assert info is None
    
    def test_start_scheduler(self, scheduler):
        """测试启动调度器"""
        scheduler.start()
        
        assert scheduler.running is True
        assert scheduler.scheduler_thread is not None
        assert scheduler.scheduler_thread.is_alive()
        
        # 清理
        scheduler.stop()
    
    def test_start_scheduler_already_running(self, scheduler):
        """测试启动已运行的调度器"""
        scheduler.start()
        
        with pytest.raises(RuntimeError, match="调度器已经在运行"):
            scheduler.start()
        
        # 清理
        scheduler.stop()
    
    def test_stop_scheduler(self, scheduler):
        """测试停止调度器"""
        scheduler.start()
        assert scheduler.running is True
        
        scheduler.stop()
        
        assert scheduler.running is False
    
    def test_stop_scheduler_not_running(self, scheduler):
        """测试停止未运行的调度器"""
        # 应该不抛出异常
        scheduler.stop()
        
        assert scheduler.running is False
    
    def test_check_dependencies_no_dependencies(self, scheduler, mock_callback):
        """测试检查无依赖的任务"""
        task_id = scheduler.add_task(
            name="test_task",
            callback=mock_callback,
            interval=1.0
        )
        
        task = scheduler.tasks[task_id]
        result = scheduler._check_dependencies(task)
        
        assert result is True
    
    def test_check_dependencies_missing_dependency(self, scheduler, mock_callback):
        """测试检查缺失依赖的任务"""
        task_id = scheduler.add_task(
            name="test_task",
            callback=mock_callback,
            interval=1.0,
            dependencies=["nonexistent_dep"]
        )
        
        task = scheduler.tasks[task_id]
        result = scheduler._check_dependencies(task)
        
        assert result is False
    
    def test_check_dependencies_unexecuted_dependency(self, scheduler, mock_callback):
        """测试检查未执行依赖的任务"""
        # 添加依赖任务
        dep_id = scheduler.add_task(
            name="dependency_task",
            callback=mock_callback,
            interval=1.0
        )
        
        # 添加主任务
        task_id = scheduler.add_task(
            name="main_task",
            callback=mock_callback,
            interval=1.0,
            dependencies=[dep_id]
        )
        
        task = scheduler.tasks[task_id]
        result = scheduler._check_dependencies(task)
        
        assert result is False  # 依赖任务未执行
    
    def test_check_dependencies_executed_dependency(self, scheduler, mock_callback):
        """测试检查已执行依赖的任务"""
        # 添加依赖任务
        dep_id = scheduler.add_task(
            name="dependency_task",
            callback=mock_callback,
            interval=1.0
        )
        
        # 模拟依赖任务已执行
        scheduler.tasks[dep_id].execution_count = 1
        
        # 添加主任务
        task_id = scheduler.add_task(
            name="main_task",
            callback=mock_callback,
            interval=1.0,
            dependencies=[dep_id]
        )
        
        task = scheduler.tasks[task_id]
        result = scheduler._check_dependencies(task)
        
        assert result is True  # 依赖任务已执行
    
    def test_execute_task_success(self, scheduler, mock_callback):
        """测试成功执行任务"""
        task_id = scheduler.add_task(
            name="test_task",
            callback=mock_callback,
            interval=1.0
        )
        
        task = scheduler.tasks[task_id]
        scheduler._execute_task(task)
        
        mock_callback.assert_called_once()
    
    def test_execute_task_exception(self, scheduler):
        """测试任务执行异常"""
        def failing_callback():
            raise RuntimeError("Task failed")
        
        task_id = scheduler.add_task(
            name="failing_task",
            callback=failing_callback,
            interval=1.0
        )
        
        task = scheduler.tasks[task_id]
        
        # 应该不抛出异常，只记录日志
        scheduler._execute_task(task)
    
    @pytest.mark.parametrize("priority,expected_order", [
        ([Priority.LOW, Priority.HIGH, Priority.NORMAL], 
         [Priority.HIGH, Priority.NORMAL, Priority.LOW]),
        ([Priority.IDLE, Priority.CRITICAL, Priority.LOW], 
         [Priority.CRITICAL, Priority.LOW, Priority.IDLE]),
    ])
    def test_task_priority_ordering(self, scheduler, mock_callback, priority, expected_order):
        """测试任务优先级排序"""
        current_time = time.time()
        next_run = current_time + 60  # 相同的执行时间
        
        task_ids = []
        for i, p in enumerate(priority):
            task_id = scheduler.add_task(
                name=f"task_{i}",
                callback=mock_callback,
                interval=1.0,
                priority=p
            )
            # 设置相同的执行时间
            scheduler.tasks[task_id].next_run = next_run
            task_ids.append(task_id)
        
        # 重建优先队列以确保排序
        import heapq
        scheduler.task_queue = list(scheduler.tasks.values())
        heapq.heapify(scheduler.task_queue)
        
        # 检查排序顺序
        sorted_tasks = []
        temp_queue = scheduler.task_queue.copy()
        while temp_queue:
            task = heapq.heappop(temp_queue)
            sorted_tasks.append(task.priority)
        
        assert sorted_tasks == expected_order


class TestTaskIntegration:
    """任务集成测试"""
    
    def test_task_execution_flow(self):
        """测试任务执行流程"""
        scheduler = ChronosScheduler()
        execution_order = []
        
        def callback1():
            execution_order.append("task1")
        
        def callback2():
            execution_order.append("task2")
        
        # 添加任务，task1优先级更高
        task1_id = scheduler.add_task(
            name="high_priority_task",
            callback=callback1,
            interval=0.1,  # 100ms
            priority=Priority.HIGH
        )
        
        task2_id = scheduler.add_task(
            name="normal_priority_task",
            callback=callback2,
            interval=0.1,  # 100ms
            priority=Priority.NORMAL
        )
        
        # 设置相同的执行时间
        current_time = time.time()
        scheduler.tasks[task1_id].next_run = current_time
        scheduler.tasks[task2_id].next_run = current_time
        
        # 启动调度器
        scheduler.start()
        
        # 等待任务执行
        time.sleep(0.2)
        
        # 停止调度器
        scheduler.stop()
        
        # 验证执行顺序（高优先级先执行）
        assert len(execution_order) >= 2
        assert execution_order[0] == "task1"  # 高优先级任务先执行
    
    def test_task_dependency_execution(self):
        """测试任务依赖执行"""
        scheduler = ChronosScheduler()
        execution_order = []
        
        def dep_callback():
            execution_order.append("dependency")
        
        def main_callback():
            execution_order.append("main")
        
        # 添加依赖任务
        dep_id = scheduler.add_task(
            name="dependency_task",
            callback=dep_callback,
            interval=0.1
        )
        
        # 添加主任务（依赖于dep_id）
        main_id = scheduler.add_task(
            name="main_task",
            callback=main_callback,
            interval=0.1,
            dependencies=[dep_id]
        )
        
        # 设置执行时间
        current_time = time.time()
        scheduler.tasks[dep_id].next_run = current_time
        scheduler.tasks[main_id].next_run = current_time
        
        # 启动调度器
        scheduler.start()
        
        # 等待任务执行
        time.sleep(0.3)
        
        # 停止调度器
        scheduler.stop()
        
        # 验证执行顺序（依赖任务先执行）
        assert len(execution_order) >= 2
        first_dep_index = execution_order.index("dependency")
        first_main_index = execution_order.index("main")
        assert first_dep_index < first_main_index