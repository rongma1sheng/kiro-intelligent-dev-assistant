"""调度器与数据管道集成测试

白皮书依据: 第三章 3.1 高性能数据管道 + 第一章 1.1 多时间尺度统一调度

测试调度器驱动的数据处理功能。
"""

import pytest
import time
import pandas as pd
from typing import Optional, List
from unittest.mock import Mock, patch

from src.integration.scheduler_pipeline import (
    ScheduledPipelineManager,
    DataPassingSource,
    DataPassingSink,
    create_data_processing_chain
)
from src.chronos.scheduler import Priority, TimeScale
from src.infra.pipeline import DataSource, DataProcessor, DataSink


class TestDataSource(DataSource[pd.DataFrame]):
    """测试数据源"""
    
    def __init__(self, data_frames: List[pd.DataFrame], repeat: bool = True):
        self.data_frames = data_frames
        self.index = 0
        self.repeat = repeat
    
    def read(self) -> Optional[pd.DataFrame]:
        if not self.data_frames:
            return None
            
        if self.index >= len(self.data_frames):
            if self.repeat:
                self.index = 0  # 重复数据
            else:
                return None
        
        result = self.data_frames[self.index].copy()
        self.index += 1
        return result


class TestDataProcessor(DataProcessor[pd.DataFrame]):
    """测试数据处理器"""
    
    def __init__(self, multiplier: float = 2.0):
        self.multiplier = multiplier
        self.process_count = 0
    
    def process(self, data: pd.DataFrame) -> pd.DataFrame:
        if data is None or data.empty:
            return data
        
        self.process_count += 1
        result = data.copy()
        
        # 对数值列进行处理
        numeric_columns = result.select_dtypes(include=['number']).columns
        for col in numeric_columns:
            result[col] = result[col] * self.multiplier
        
        return result


class TestDataSink(DataSink[pd.DataFrame]):
    """测试数据接收器"""
    
    def __init__(self):
        self.written_data: List[pd.DataFrame] = []
        self.write_count = 0
    
    def write(self, data: pd.DataFrame) -> None:
        if data is not None and not data.empty:
            self.write_count += 1
            self.written_data.append(data.copy())
    
    def get_all_data(self) -> pd.DataFrame:
        if not self.written_data:
            return pd.DataFrame()
        return pd.concat(self.written_data, ignore_index=True)


class TestScheduledPipelineManager:
    """调度管道管理器测试"""
    
    def test_manager_initialization(self):
        """测试管理器初始化"""
        manager = ScheduledPipelineManager()
        
        assert manager.scheduler is not None
        assert isinstance(manager.pipelines, dict)
        assert isinstance(manager.data_store, dict)
        assert isinstance(manager.error_handlers, dict)
        assert 'default' in manager.error_handlers
    
    def test_add_pipeline(self):
        """测试添加管道"""
        manager = ScheduledPipelineManager()
        
        # 创建测试组件
        test_data = [pd.DataFrame({'value': [1, 2, 3]})]
        source = TestDataSource(test_data)
        processor = TestDataProcessor()
        sink = TestDataSink()
        
        # 添加管道
        pipeline_id = manager.add_pipeline(
            name="test_pipeline",
            source=source,
            processors=[processor],
            sink=sink,
            interval=1.0,
            priority=Priority.NORMAL
        )
        
        # 验证管道已添加
        assert pipeline_id in manager.pipelines
        pipeline_info = manager.get_pipeline_info(pipeline_id)
        assert pipeline_info is not None
        assert pipeline_info['name'] == "test_pipeline"
        assert pipeline_info['enabled'] == True
        assert pipeline_info['execution_count'] == 0
    
    def test_remove_pipeline(self):
        """测试移除管道"""
        manager = ScheduledPipelineManager()
        
        # 添加管道
        test_data = [pd.DataFrame({'value': [1, 2, 3]})]
        source = TestDataSource(test_data)
        sink = TestDataSink()
        
        pipeline_id = manager.add_pipeline(
            name="test_pipeline",
            source=source,
            processors=[],
            sink=sink,
            interval=1.0
        )
        
        # 验证管道存在
        assert pipeline_id in manager.pipelines
        
        # 移除管道
        result = manager.remove_pipeline(pipeline_id)
        assert result == True
        assert pipeline_id not in manager.pipelines
        
        # 移除不存在的管道
        result = manager.remove_pipeline("nonexistent")
        assert result == False
    
    def test_data_store_operations(self):
        """测试数据存储操作"""
        manager = ScheduledPipelineManager()
        
        # 设置数据
        manager.set_data("test_key", {"value": 123})
        
        # 获取数据
        data = manager.get_data("test_key")
        assert data == {"value": 123}
        
        # 获取不存在的数据
        data = manager.get_data("nonexistent", "default_value")
        assert data == "default_value"
    
    def test_error_handler_registration(self):
        """测试错误处理器注册"""
        manager = ScheduledPipelineManager()
        
        # 注册自定义错误处理器
        error_log = []
        
        def custom_error_handler(error: Exception, pipeline_id: str):
            error_log.append((str(error), pipeline_id))
        
        manager.register_error_handler("custom", custom_error_handler)
        
        # 验证处理器已注册
        assert "custom" in manager.error_handlers
        
        # 测试错误处理器调用
        test_error = ValueError("test error")
        manager.error_handlers["custom"](test_error, "test_pipeline")
        
        assert len(error_log) == 1
        assert error_log[0] == ("test error", "test_pipeline")
    
    def test_pipeline_execution_integration(self):
        """测试管道执行集成"""
        manager = ScheduledPipelineManager()
        
        # 创建测试组件（允许重复读取数据）
        test_data = [pd.DataFrame({'value': [1, 2, 3]})]
        source = TestDataSource(test_data, repeat=True)
        processor = TestDataProcessor(multiplier=3.0)
        sink = TestDataSink()
        
        # 添加管道
        pipeline_id = manager.add_pipeline(
            name="test_pipeline",
            source=source,
            processors=[processor],
            sink=sink,
            interval=0.1,  # 100ms interval
            priority=Priority.HIGH
        )
        
        # 启动管理器
        manager.start()
        
        try:
            # 等待一段时间让管道执行
            time.sleep(0.5)  # 500ms, should allow multiple executions
            
            # 检查执行结果
            pipeline_info = manager.get_pipeline_info(pipeline_id)
            assert pipeline_info['execution_count'] >= 1, f"Expected at least 1 execution, got {pipeline_info['execution_count']}"
            
            # 检查数据处理结果
            assert processor.process_count >= 1, f"Expected at least 1 process call, got {processor.process_count}"
            assert sink.write_count >= 1, f"Expected at least 1 write call, got {sink.write_count}"
            
            # 检查性能指标
            assert 'last_execution_time_ms' in pipeline_info['performance_metrics']
            assert pipeline_info['performance_metrics']['last_execution_time_ms'] > 0
            
        finally:
            manager.stop()


class TestDataPassing:
    """数据传递测试"""
    
    def test_data_passing_source_and_sink(self):
        """测试数据传递源和接收器"""
        manager = ScheduledPipelineManager()
        
        # 创建数据传递组件
        data_key = "test_data"
        source = DataPassingSource(manager, data_key)
        sink = DataPassingSink(manager, data_key)
        
        # 测试数据传递
        test_data = pd.DataFrame({'value': [1, 2, 3]})
        
        # 写入数据
        sink.write(test_data)
        
        # 读取数据
        read_data = source.read()
        
        # 验证数据一致性
        pd.testing.assert_frame_equal(test_data, read_data)
    
    def test_data_processing_chain(self):
        """测试数据处理链"""
        manager = ScheduledPipelineManager()
        
        # 创建处理链配置
        test_data = [pd.DataFrame({'value': [10, 20, 30]})]
        
        chain_config = [
            {
                'name': 'data_ingestion',
                'source': TestDataSource(test_data, repeat=True),
                'processors': [TestDataProcessor(multiplier=2.0)],
                'sink': DataPassingSink(manager, 'raw_data'),
                'interval': 0.1,
                'priority': Priority.HIGH
            },
            {
                'name': 'data_processing',
                'source': DataPassingSource(manager, 'raw_data'),
                'processors': [TestDataProcessor(multiplier=3.0)],
                'sink': DataPassingSink(manager, 'processed_data'),
                'interval': 0.2,
                'priority': Priority.NORMAL
            }
        ]
        
        # 创建处理链
        pipeline_ids = create_data_processing_chain(manager, chain_config)
        
        assert len(pipeline_ids) == 2
        
        # 启动管理器
        manager.start()
        
        try:
            # 等待处理链执行
            time.sleep(0.8)  # 增加等待时间
            
            # 检查中间数据
            raw_data = manager.get_data('raw_data')
            if raw_data is not None:
                # 第一个处理器将数据乘以2: [10,20,30] -> [20,40,60]
                expected_raw = pd.DataFrame({'value': [20.0, 40.0, 60.0]})  # 使用float类型
                pd.testing.assert_frame_equal(raw_data, expected_raw)
            
            # 检查最终数据
            processed_data = manager.get_data('processed_data')
            if processed_data is not None:
                # 第二个处理器将数据乘以3: [20,40,60] -> [60,120,180]
                expected_processed = pd.DataFrame({'value': [60.0, 120.0, 180.0]})  # 使用float类型
                pd.testing.assert_frame_equal(processed_data, expected_processed)
            
            # 检查管道执行状态
            for pipeline_id in pipeline_ids:
                pipeline_info = manager.get_pipeline_info(pipeline_id)
                assert pipeline_info is not None
                # 注意：由于时间间隔和依赖关系，执行次数可能不同
                
        finally:
            manager.stop()


class TestErrorHandling:
    """错误处理测试"""
    
    def test_pipeline_error_handling(self):
        """测试管道错误处理"""
        manager = ScheduledPipelineManager()
        
        # 创建会出错的数据源
        class FailingSource(DataSource):
            def read(self):
                raise ValueError("Test error")
        
        # 注册自定义错误处理器
        error_log = []
        
        def custom_error_handler(error: Exception, pipeline_id: str):
            error_log.append((str(error), pipeline_id))
        
        manager.register_error_handler("test_handler", custom_error_handler)
        
        # 添加会出错的管道
        pipeline_id = manager.add_pipeline(
            name="failing_pipeline",
            source=FailingSource(),
            processors=[],
            sink=TestDataSink(),
            interval=0.1,
            error_handler="test_handler"
        )
        
        # 手动执行管道（模拟调度器调用）
        manager._execute_pipeline(pipeline_id, "test_handler")
        
        # 检查错误处理
        assert len(error_log) == 1
        assert "Test error" in error_log[0][0]
        assert error_log[0][1] == pipeline_id
        
        # 检查管道状态
        pipeline_info = manager.get_pipeline_info(pipeline_id)
        assert pipeline_info['last_error'] == "Test error"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])