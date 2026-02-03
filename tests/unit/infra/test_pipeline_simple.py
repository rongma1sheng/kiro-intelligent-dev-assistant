"""数据管道简化单元测试

白皮书依据: 第三章 3.1 数据管道架构

测试覆盖:
- 抽象基类接口
- DataPipeline核心功能
- 基本错误处理
"""

import pytest
import pandas as pd
import numpy as np
from typing import List, Optional

from src.infra.pipeline import (
    DataSource, DataProcessor, DataSink, DataPipeline,
    MemorySource, MemorySink
)


class MockDataSource(DataSource):
    """测试用数据源"""
    
    def __init__(self, data: List[pd.DataFrame]):
        self.data = data
        self.index = 0
    
    def read(self) -> pd.DataFrame:
        if self.index >= len(self.data):
            return None  # 返回None表示结束
        
        result = self.data[self.index]
        self.index += 1
        return result
    
    def close(self) -> None:
        pass


class MockDataProcessor(DataProcessor):
    """测试用数据处理器"""
    
    def __init__(self, multiply_factor: float = 2.0):
        self.multiply_factor = multiply_factor
    
    def process(self, data: pd.DataFrame) -> pd.DataFrame:
        if data is None or data.empty:
            return data
        
        result = data.copy()
        # 简单处理：数值列乘以因子
        numeric_columns = result.select_dtypes(include=[np.number]).columns
        result[numeric_columns] = result[numeric_columns] * self.multiply_factor
        return result


class MockDataSink(DataSink):
    """测试用数据接收器"""
    
    def __init__(self):
        self.written_data: List[pd.DataFrame] = []
    
    def write(self, data: pd.DataFrame) -> None:
        if data is not None and not data.empty:
            self.written_data.append(data.copy())
    
    def close(self) -> None:
        pass


class FailingDataSource(DataSource):
    """会失败的数据源"""
    
    def read(self) -> pd.DataFrame:
        raise RuntimeError("Data source failed")
    
    def close(self) -> None:
        pass


class FailingDataProcessor(DataProcessor):
    """会失败的数据处理器"""
    
    def process(self, data: pd.DataFrame) -> pd.DataFrame:
        raise RuntimeError("Data processor failed")


class FailingDataSink(DataSink):
    """会失败的数据接收器"""
    
    def write(self, data: pd.DataFrame) -> None:
        raise RuntimeError("Data sink failed")
    
    def close(self) -> None:
        pass


class TestDataSource:
    """DataSource抽象基类测试"""
    
    def test_data_source_is_abstract(self):
        """测试DataSource是抽象类"""
        with pytest.raises(TypeError):
            DataSource()
    
    def test_mock_data_source(self):
        """测试Mock数据源"""
        test_data = [
            pd.DataFrame({'value': [1, 2, 3]}),
            pd.DataFrame({'value': [4, 5, 6]})
        ]
        
        source = MockDataSource(test_data)
        
        # 读取第一批数据
        data1 = source.read()
        assert len(data1) == 3
        assert data1['value'].tolist() == [1, 2, 3]
        
        # 读取第二批数据
        data2 = source.read()
        assert len(data2) == 3
        assert data2['value'].tolist() == [4, 5, 6]
        
        # 读取完毕，返回None
        data3 = source.read()
        assert data3 is None


class TestDataProcessor:
    """DataProcessor抽象基类测试"""
    
    def test_data_processor_is_abstract(self):
        """测试DataProcessor是抽象类"""
        with pytest.raises(TypeError):
            DataProcessor()
    
    def test_mock_data_processor(self):
        """测试Mock数据处理器"""
        processor = MockDataProcessor(multiply_factor=3.0)
        
        input_data = pd.DataFrame({
            'value': [1, 2, 3],
            'price': [10.0, 20.0, 30.0]
        })
        
        result = processor.process(input_data)
        
        assert len(result) == 3
        assert result['value'].tolist() == [3, 6, 9]
        assert result['price'].tolist() == [30.0, 60.0, 90.0]
    
    def test_mock_data_processor_empty_data(self):
        """测试处理空数据"""
        processor = MockDataProcessor()
        
        empty_data = pd.DataFrame()
        result = processor.process(empty_data)
        
        assert result.empty
    
    def test_mock_data_processor_none_data(self):
        """测试处理None数据"""
        processor = MockDataProcessor()
        
        result = processor.process(None)
        
        assert result is None


class TestDataSink:
    """DataSink抽象基类测试"""
    
    def test_data_sink_is_abstract(self):
        """测试DataSink是抽象类"""
        with pytest.raises(TypeError):
            DataSink()
    
    def test_mock_data_sink(self):
        """测试Mock数据接收器"""
        sink = MockDataSink()
        
        test_data1 = pd.DataFrame({'value': [1, 2, 3]})
        test_data2 = pd.DataFrame({'value': [4, 5, 6]})
        
        sink.write(test_data1)
        sink.write(test_data2)
        
        assert len(sink.written_data) == 2
        assert sink.written_data[0]['value'].tolist() == [1, 2, 3]
        assert sink.written_data[1]['value'].tolist() == [4, 5, 6]
    
    def test_mock_data_sink_empty_data(self):
        """测试写入空数据"""
        sink = MockDataSink()
        
        empty_data = pd.DataFrame()
        sink.write(empty_data)
        
        assert len(sink.written_data) == 0  # 空数据不写入
    
    def test_mock_data_sink_none_data(self):
        """测试写入None数据"""
        sink = MockDataSink()
        
        sink.write(None)
        
        assert len(sink.written_data) == 0  # None数据不写入


class TestDataPipeline:
    """DataPipeline类测试"""
    
    @pytest.fixture
    def sample_data(self):
        """示例数据"""
        return [
            pd.DataFrame({'value': [1, 2, 3], 'price': [10.0, 20.0, 30.0]}),
            pd.DataFrame({'value': [4, 5, 6], 'price': [40.0, 50.0, 60.0]}),
            pd.DataFrame({'value': [7, 8, 9], 'price': [70.0, 80.0, 90.0]})
        ]
    
    @pytest.fixture
    def basic_pipeline(self, sample_data):
        """基础管道"""
        source = MockDataSource(sample_data)
        processors = [MockDataProcessor(multiply_factor=2.0)]
        sink = MockDataSink()
        
        return DataPipeline(source=source, processors=processors, sink=sink)
    
    def test_pipeline_initialization(self, sample_data):
        """测试管道初始化"""
        source = MockDataSource(sample_data)
        processors = [MockDataProcessor()]
        sink = MockDataSink()
        
        pipeline = DataPipeline(
            source=source,
            processors=processors,
            sink=sink,
            backpressure_enabled=True
        )
        
        assert pipeline.source == source
        assert pipeline.processors == processors
        assert pipeline.sink == sink
        assert pipeline.backpressure_enabled is True
        assert pipeline.running is False
    
    def test_pipeline_initialization_invalid_source(self, sample_data):
        """测试无效数据源"""
        processors = [MockDataProcessor()]
        sink = MockDataSink()
        
        with pytest.raises(ValueError, match="source不能为空"):
            DataPipeline(source=None, processors=processors, sink=sink)
    
    def test_pipeline_initialization_invalid_sink(self, sample_data):
        """测试无效数据接收器"""
        source = MockDataSource(sample_data)
        processors = [MockDataProcessor()]
        
        with pytest.raises(ValueError, match="sink不能为空"):
            DataPipeline(source=source, processors=processors, sink=None)
    
    def test_pipeline_initialization_empty_processors(self, sample_data):
        """测试空处理器列表"""
        source = MockDataSource(sample_data)
        sink = MockDataSink()
        
        pipeline = DataPipeline(source=source, processors=[], sink=sink)
        
        assert pipeline.processors == []
    
    def test_pipeline_initialization_none_processors(self, sample_data):
        """测试None处理器列表"""
        source = MockDataSource(sample_data)
        sink = MockDataSink()
        
        pipeline = DataPipeline(source=source, processors=None, sink=sink)
        
        assert pipeline.processors == []
    
    def test_pipeline_run_success(self, basic_pipeline):
        """测试管道成功运行"""
        basic_pipeline.run()
        
        # 检查处理结果
        sink = basic_pipeline.sink
        assert len(sink.written_data) == 3
        
        # 检查数据被正确处理（乘以2）
        assert sink.written_data[0]['value'].tolist() == [2, 4, 6]
        assert sink.written_data[0]['price'].tolist() == [20.0, 40.0, 60.0]
        
        assert sink.written_data[1]['value'].tolist() == [8, 10, 12]
        assert sink.written_data[1]['price'].tolist() == [80.0, 100.0, 120.0]
        
        assert sink.written_data[2]['value'].tolist() == [14, 16, 18]
        assert sink.written_data[2]['price'].tolist() == [140.0, 160.0, 180.0]
    
    def test_pipeline_run_empty_source(self):
        """测试空数据源"""
        source = MockDataSource([])  # 空数据
        processors = [MockDataProcessor()]
        sink = MockDataSink()
        
        pipeline = DataPipeline(source=source, processors=processors, sink=sink)
        pipeline.run()
        
        assert len(sink.written_data) == 0
    
    def test_pipeline_run_no_processors(self, sample_data):
        """测试无处理器的管道"""
        source = MockDataSource(sample_data)
        sink = MockDataSink()
        
        pipeline = DataPipeline(source=source, processors=[], sink=sink)
        pipeline.run()
        
        # 数据应该直接从源传到接收器，不经过处理
        assert len(sink.written_data) == 3
        assert sink.written_data[0]['value'].tolist() == [1, 2, 3]  # 未处理
        assert sink.written_data[0]['price'].tolist() == [10.0, 20.0, 30.0]  # 未处理
    
    def test_pipeline_run_multiple_processors(self, sample_data):
        """测试多个处理器"""
        source = MockDataSource(sample_data)
        processors = [
            MockDataProcessor(multiply_factor=2.0),
            MockDataProcessor(multiply_factor=3.0)
        ]
        sink = MockDataSink()
        
        pipeline = DataPipeline(source=source, processors=processors, sink=sink)
        pipeline.run()
        
        # 数据应该经过两次处理：先乘以2，再乘以3，总共乘以6
        assert len(sink.written_data) == 3
        assert sink.written_data[0]['value'].tolist() == [6, 12, 18]  # 1*2*3, 2*2*3, 3*2*3
        assert sink.written_data[0]['price'].tolist() == [60.0, 120.0, 180.0]  # 10*2*3, 20*2*3, 30*2*3
    
    def test_pipeline_run_source_failure(self):
        """测试数据源失败"""
        source = FailingDataSource()
        processors = [MockDataProcessor()]
        sink = MockDataSink()
        
        pipeline = DataPipeline(source=source, processors=processors, sink=sink)
        
        with pytest.raises(RuntimeError, match="Data source failed"):
            pipeline.run()
    
    def test_pipeline_run_processor_failure(self, sample_data):
        """测试数据处理器失败"""
        source = MockDataSource(sample_data)
        processors = [FailingDataProcessor()]
        sink = MockDataSink()
        
        pipeline = DataPipeline(source=source, processors=processors, sink=sink)
        
        with pytest.raises(RuntimeError, match="Data processor failed"):
            pipeline.run()
    
    def test_pipeline_run_sink_failure(self, sample_data):
        """测试数据接收器失败"""
        source = MockDataSource(sample_data)
        processors = [MockDataProcessor()]
        sink = FailingDataSink()
        
        pipeline = DataPipeline(source=source, processors=processors, sink=sink)
        
        with pytest.raises(RuntimeError, match="Data sink failed"):
            pipeline.run()
    
    def test_pipeline_run_already_running(self, sample_data):
        """测试重复运行管道"""
        source = MockDataSource(sample_data)
        processors = [MockDataProcessor()]
        sink = MockDataSink()
        
        pipeline = DataPipeline(source=source, processors=processors, sink=sink)
        
        # 模拟管道正在运行
        pipeline.running = True
        
        with pytest.raises(RuntimeError, match="数据管道已经在运行"):
            pipeline.run()
    
    def test_pipeline_stop(self, basic_pipeline):
        """测试停止管道"""
        # 停止未运行的管道应该没有问题
        basic_pipeline.stop()
        
        assert basic_pipeline.running is False
    
    def test_pipeline_mixed_data_types(self):
        """测试混合数据类型"""
        mixed_data = [
            pd.DataFrame({
                'int_col': [1, 2, 3],
                'float_col': [1.1, 2.2, 3.3],
                'str_col': ['a', 'b', 'c'],
                'bool_col': [True, False, True]
            })
        ]
        
        source = MockDataSource(mixed_data)
        processors = [MockDataProcessor(multiply_factor=2.0)]
        sink = MockDataSink()
        
        pipeline = DataPipeline(source=source, processors=processors, sink=sink)
        pipeline.run()
        
        result = sink.written_data[0]
        
        # 数值列应该被处理
        assert result['int_col'].tolist() == [2, 4, 6]
        assert result['float_col'].tolist() == [2.2, 4.4, 6.6]
        
        # 非数值列应该保持不变
        assert result['str_col'].tolist() == ['a', 'b', 'c']
        assert result['bool_col'].tolist() == [True, False, True]


class TestDataPipelineIntegration:
    """数据管道集成测试"""
    
    def test_end_to_end_data_flow(self):
        """测试端到端数据流"""
        # 创建真实的数据处理场景
        raw_data = [
            pd.DataFrame({
                'timestamp': pd.date_range('2024-01-01', periods=5, freq='h'),
                'symbol': ['AAPL'] * 5,
                'price': [150.0, 151.0, 149.0, 152.0, 153.0],
                'volume': [1000, 1100, 900, 1200, 1300]
            }),
            pd.DataFrame({
                'timestamp': pd.date_range('2024-01-01 05:00:00', periods=5, freq='h'),
                'symbol': ['GOOGL'] * 5,
                'price': [2800.0, 2810.0, 2790.0, 2820.0, 2830.0],
                'volume': [500, 550, 450, 600, 650]
            })
        ]
        
        class PriceNormalizer(DataProcessor):
            """价格标准化处理器"""
            def process(self, data: pd.DataFrame) -> pd.DataFrame:
                if data is None or data.empty or 'price' not in data.columns:
                    return data
                
                result = data.copy()
                # 简单的价格标准化：除以100
                result['normalized_price'] = result['price'] / 100
                return result
        
        source = MockDataSource(raw_data)
        processors = [PriceNormalizer()]
        sink = MockDataSink()
        
        pipeline = DataPipeline(source=source, processors=processors, sink=sink)
        pipeline.run()
        
        # 验证处理结果
        assert len(sink.written_data) == 2
        
        # 检查AAPL数据
        aapl_data = sink.written_data[0]
        assert 'normalized_price' in aapl_data.columns
        assert aapl_data['normalized_price'].tolist() == [1.5, 1.51, 1.49, 1.52, 1.53]
        
        # 检查GOOGL数据
        googl_data = sink.written_data[1]
        assert 'normalized_price' in googl_data.columns
        assert googl_data['normalized_price'].tolist() == [28.0, 28.1, 27.9, 28.2, 28.3]


class TestDataSourceAdvanced:
    """DataSource高级测试"""
    
    def test_mock_data_source_close(self):
        """测试Mock数据源关闭"""
        test_data = [pd.DataFrame({'value': [1, 2, 3]})]
        source = MockDataSource(test_data)
        
        # 关闭应该不抛出异常
        source.close()


class TestDataSinkAdvanced:
    """DataSink高级测试"""
    
    def test_mock_data_sink_close(self):
        """测试Mock数据接收器关闭"""
        sink = MockDataSink()
        
        # 关闭应该不抛出异常
        sink.close()


class TestMemorySourceSink:
    """MemorySource和MemorySink测试"""
    
    def test_memory_source_read_all(self):
        """测试MemorySource读取所有数据"""
        test_data = pd.DataFrame({
            'id': [1, 2, 3, 4, 5],
            'value': [10, 20, 30, 40, 50]
        })
        
        source = MemorySource(test_data)
        
        # 读取所有数据
        read_count = 0
        while True:
            data = source.read()
            if data is None:
                break
            read_count += 1
            assert len(data) == 1  # 每次读取一行
        
        assert read_count == 5
    
    def test_memory_source_empty_data(self):
        """测试MemorySource空数据"""
        empty_data = pd.DataFrame()
        source = MemorySource(empty_data)
        
        # 读取应该立即返回None
        result = source.read()
        assert result is None
    
    def test_memory_sink_write_and_get(self):
        """测试MemorySink写入和获取"""
        sink = MemorySink()
        
        # 写入多个DataFrame
        data1 = pd.DataFrame({'id': [1], 'value': [10]})
        data2 = pd.DataFrame({'id': [2], 'value': [20]})
        data3 = pd.DataFrame({'id': [3], 'value': [30]})
        
        sink.write(data1)
        sink.write(data2)
        sink.write(data3)
        
        # 获取合并后的数据
        result = sink.get_data()
        
        assert len(result) == 3
        assert result['id'].tolist() == [1, 2, 3]
        assert result['value'].tolist() == [10, 20, 30]
    
    def test_memory_sink_get_empty(self):
        """测试MemorySink获取空数据"""
        sink = MemorySink()
        
        # 未写入任何数据
        result = sink.get_data()
        
        assert result.empty
    
    def test_memory_source_sink_pipeline(self):
        """测试MemorySource和MemorySink的完整管道"""
        # 创建测试数据
        test_data = pd.DataFrame({
            'id': [1, 2, 3],
            'value': [10, 20, 30]
        })
        
        source = MemorySource(test_data)
        sink = MemorySink()
        
        # 创建管道（无处理器）
        pipeline = DataPipeline(source=source, processors=[], sink=sink)
        pipeline.run()
        
        # 验证数据完整性
        result = sink.get_data()
        assert len(result) == 3
        assert result['id'].tolist() == [1, 2, 3]
        assert result['value'].tolist() == [10, 20, 30]


class TestDataPipelineEdgeCases:
    """数据管道边界情况测试"""
    
    def test_pipeline_with_none_data_in_middle(self):
        """测试管道中间出现None数据"""
        class NoneReturningSource(DataSource):
            def __init__(self):
                self.count = 0
            
            def read(self) -> Optional[pd.DataFrame]:
                self.count += 1
                if self.count == 1:
                    return pd.DataFrame({'value': [1]})
                return None
            
            def close(self) -> None:
                pass
        
        source = NoneReturningSource()
        sink = MockDataSink()
        
        pipeline = DataPipeline(source=source, processors=[], sink=sink)
        pipeline.run()
        
        # 应该只写入一个数据
        assert len(sink.written_data) == 1
    
    def test_pipeline_backpressure_disabled(self):
        """测试禁用背压控制"""
        test_data = [pd.DataFrame({'value': [1, 2, 3]})]
        source = MockDataSource(test_data)
        sink = MockDataSink()
        
        pipeline = DataPipeline(
            source=source,
            processors=[],
            sink=sink,
            backpressure_enabled=False
        )
        
        assert pipeline.backpressure_enabled is False
        
        pipeline.run()
        
        # 数据应该正常处理
        assert len(sink.written_data) == 1
    
    def test_pipeline_stop_before_run(self):
        """测试运行前停止管道"""
        test_data = [pd.DataFrame({'value': [1, 2, 3]})]
        source = MockDataSource(test_data)
        sink = MockDataSink()
        
        pipeline = DataPipeline(source=source, processors=[], sink=sink)
        
        # 停止未运行的管道
        pipeline.stop()
        
        assert pipeline.running is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])