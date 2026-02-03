"""数据管道属性测试

白皮书依据: 第三章 3.1 高性能数据管道

Property-Based Testing for:
- 属性10: 数据完整性
- 验证需求: US-3.1

使用hypothesis框架进行property-based testing。
"""

import pytest
import pandas as pd
import numpy as np
from typing import List, Optional
from hypothesis import given, strategies as st, settings, assume

from src.infra.pipeline import (
    DataSource, DataProcessor, DataSink, DataPipeline,
    DataSourceError, DataProcessError, DataSinkError
)


class PropertyTestDataSource(DataSource[pd.DataFrame]):
    """用于属性测试的数据源"""
    
    def __init__(self, data_frames: List[pd.DataFrame]):
        self.data_frames = data_frames
        self.index = 0
        self.read_count = 0
    
    def read(self) -> Optional[pd.DataFrame]:
        """读取数据
        
        Returns:
            数据框或None（表示结束）
        """
        self.read_count += 1
        
        if self.index >= len(self.data_frames):
            return None
        
        result = self.data_frames[self.index].copy()
        self.index += 1
        return result


class PropertyTestProcessor(DataProcessor[pd.DataFrame]):
    """用于属性测试的数据处理器"""
    
    def __init__(self, add_column: bool = False, multiply_factor: float = 1.0):
        self.add_column = add_column
        self.multiply_factor = multiply_factor
        self.process_count = 0
    
    def process(self, data: pd.DataFrame) -> pd.DataFrame:
        """处理数据
        
        Args:
            data: 输入数据
            
        Returns:
            处理后的数据
        """
        if data is None or data.empty:
            return data
        
        self.process_count += 1
        result = data.copy()
        
        # 只对特定的数值列应用乘法因子（排除id列）
        numeric_columns = result.select_dtypes(include=[np.number]).columns
        # 排除id列和其他标识列
        multiply_columns = [col for col in numeric_columns 
                          if col not in ['id', 'symbol_id', 'index', 'batch_order']]
        
        if len(multiply_columns) > 0:
            result[multiply_columns] = result[multiply_columns] * self.multiply_factor
        
        # 可选：添加处理标记列
        if self.add_column:
            result['processed'] = True
        
        return result


class PropertyTestSink(DataSink[pd.DataFrame]):
    """用于属性测试的数据接收器"""
    
    def __init__(self):
        self.written_data: List[pd.DataFrame] = []
        self.write_count = 0
        self.total_rows = 0
    
    def write(self, data: pd.DataFrame) -> None:
        """写入数据
        
        Args:
            data: 要写入的数据
        """
        if data is not None and not data.empty:
            self.write_count += 1
            self.total_rows += len(data)
            self.written_data.append(data.copy())
    
    def get_all_data(self) -> pd.DataFrame:
        """获取所有写入的数据
        
        Returns:
            合并后的数据框
        """
        if not self.written_data:
            return pd.DataFrame()
        
        return pd.concat(self.written_data, ignore_index=True)


def create_test_dataframe(num_rows: int, start_value: int = 0) -> pd.DataFrame:
    """创建测试数据框
    
    Args:
        num_rows: 行数
        start_value: 起始值
        
    Returns:
        测试数据框
    """
    return pd.DataFrame({
        'value': list(range(start_value, start_value + num_rows)),
        'price': [float(i + 10) for i in range(start_value, start_value + num_rows)],
        'symbol': [f'SYM{i}' for i in range(start_value, start_value + num_rows)]
    })


class TestDataPipelineProperties:
    """数据管道属性测试"""
    
    @given(
        num_batches=st.integers(min_value=1, max_value=10),
        batch_size=st.integers(min_value=1, max_value=20)
    )
    @settings(max_examples=50, deadline=5000)
    def test_property_data_integrity_no_loss(self, num_batches, batch_size):
        """属性10: 数据完整性 - 无数据丢失
        
        **验证需求: US-3.1**
        
        对于任何输入数据，管道处理后的总行数应该等于输入的总行数。
        """
        # 创建测试数据
        data_frames = []
        total_input_rows = 0
        
        for i in range(num_batches):
            df = create_test_dataframe(batch_size, start_value=i * batch_size)
            data_frames.append(df)
            total_input_rows += len(df)
        
        # 创建管道组件
        source = PropertyTestDataSource(data_frames)
        processors = [PropertyTestProcessor(multiply_factor=2.0)]
        sink = PropertyTestSink()
        
        # 创建并运行管道
        pipeline = DataPipeline(
            source=source,
            processors=processors,
            sink=sink,
            backpressure_enabled=True
        )
        
        pipeline.run()
        
        # 验证数据完整性：输出行数 = 输入行数
        assert sink.total_rows == total_input_rows, (
            f"数据丢失: 输入{total_input_rows}行，输出{sink.total_rows}行"
        )
        
        # 验证处理次数
        assert source.read_count == num_batches + 1  # +1 for final None
        assert processors[0].process_count == num_batches
        assert sink.write_count == num_batches
    
    @given(
        num_batches=st.integers(min_value=1, max_value=5),
        batch_size=st.integers(min_value=1, max_value=10),
        multiply_factor=st.floats(min_value=0.1, max_value=10.0, allow_nan=False, allow_infinity=False)
    )
    @settings(max_examples=30, deadline=5000)
    def test_property_data_integrity_content_preservation(self, num_batches, batch_size, multiply_factor):
        """属性10: 数据完整性 - 内容保持
        
        **验证需求: US-3.1**
        
        对于任何输入数据和处理因子，处理后的数据应该保持正确的变换关系。
        """
        # 创建测试数据
        data_frames = []
        for i in range(num_batches):
            df = pd.DataFrame({
                'id': list(range(i * batch_size, (i + 1) * batch_size)),
                'amount': [float(j + 1) for j in range(i * batch_size, (i + 1) * batch_size)]
            })
            data_frames.append(df)
        
        # 创建管道组件
        source = PropertyTestDataSource(data_frames)
        processors = [PropertyTestProcessor(multiply_factor=multiply_factor)]
        sink = PropertyTestSink()
        
        # 创建并运行管道
        pipeline = DataPipeline(
            source=source,
            processors=processors,
            sink=sink
        )
        
        pipeline.run()
        
        # 获取输出数据
        output_data = sink.get_all_data()
        
        # 验证数据变换的正确性
        if not output_data.empty:
            # 重新构建输入数据用于比较
            input_data = pd.concat(data_frames, ignore_index=True)
            
            # 验证行数一致
            assert len(output_data) == len(input_data)
            
            # 验证数值列的变换
            if 'amount' in output_data.columns and 'amount' in input_data.columns:
                expected_amounts = input_data['amount'] * multiply_factor
                actual_amounts = output_data['amount']
                
                # 使用相对误差比较浮点数
                np.testing.assert_allclose(
                    actual_amounts.values,
                    expected_amounts.values,
                    rtol=1e-10,
                    err_msg=f"数值变换不正确: 因子={multiply_factor}"
                )
            
            # 验证非数值列保持不变
            if 'id' in output_data.columns and 'id' in input_data.columns:
                # 转换为相同类型进行比较（处理器可能会改变数据类型）
                output_ids = output_data['id'].astype(int)
                input_ids = input_data['id'].astype(int)
                pd.testing.assert_series_equal(
                    output_ids.reset_index(drop=True),
                    input_ids.reset_index(drop=True),
                    check_names=False
                )
    
    @given(
        num_batches=st.integers(min_value=2, max_value=8),
        batch_size=st.integers(min_value=1, max_value=10)
    )
    @settings(max_examples=30, deadline=5000)
    def test_property_data_integrity_order_preservation(self, num_batches, batch_size):
        """属性10: 数据完整性 - 顺序保持
        
        **验证需求: US-3.1**
        
        对于任何输入数据序列，管道应该保持数据的处理顺序。
        """
        # 创建带有批次标记的数据
        data_frames = []
        for i in range(num_batches):
            df = pd.DataFrame({
                'value': list(range(i * batch_size, (i + 1) * batch_size)),
                'category': [f'CAT_{i % 4}'] * batch_size,
                'batch_order': [i] * batch_size
            })
            data_frames.append(df)
        
        # 创建管道组件
        source = PropertyTestDataSource(data_frames)
        processors = [PropertyTestProcessor(add_column=True)]
        sink = PropertyTestSink()
        
        # 创建并运行管道
        pipeline = DataPipeline(
            source=source,
            processors=processors,
            sink=sink
        )
        
        pipeline.run()
        
        # 验证批次顺序
        assert len(sink.written_data) == num_batches
        
        for i, written_batch in enumerate(sink.written_data):
            expected_batch_order = i
            actual_batch_orders = written_batch['batch_order'].unique()
            
            assert len(actual_batch_orders) == 1, f"批次{i}包含多个batch_order值"
            assert actual_batch_orders[0] == expected_batch_order, (
                f"批次顺序错误: 期望{expected_batch_order}, 实际{actual_batch_orders[0]}"
            )
    
    @given(
        processor_count=st.integers(min_value=1, max_value=5),
        data_size=st.integers(min_value=1, max_value=20)
    )
    @settings(max_examples=20, deadline=5000)
    def test_property_data_integrity_multiple_processors(self, processor_count, data_size):
        """属性10: 数据完整性 - 多处理器链
        
        **验证需求: US-3.1**
        
        对于任意数量的处理器，数据应该正确地通过整个处理链。
        """
        # 创建测试数据
        test_data = [pd.DataFrame({
            'value': list(range(data_size)),
            'multiplier': [2.0] * data_size
        })]
        
        # 创建多个处理器
        processors = []
        expected_factor = 1.0
        for i in range(processor_count):
            factor = 2.0
            processors.append(PropertyTestProcessor(multiply_factor=factor))
            expected_factor *= factor
        
        # 创建管道组件
        source = PropertyTestDataSource(test_data)
        sink = PropertyTestSink()
        
        # 创建并运行管道
        pipeline = DataPipeline(
            source=source,
            processors=processors,
            sink=sink
        )
        
        pipeline.run()
        
        # 验证结果
        output_data = sink.get_all_data()
        
        assert len(output_data) == data_size
        
        # 验证数值经过所有处理器的变换
        expected_values = np.array(range(data_size)) * expected_factor
        actual_values = output_data['value'].values
        
        np.testing.assert_allclose(
            actual_values,
            expected_values,
            rtol=1e-10,
            err_msg=f"多处理器链变换错误: 处理器数量={processor_count}, 期望因子={expected_factor}"
        )
        
        # 验证所有处理器都被调用
        for i, processor in enumerate(processors):
            assert processor.process_count == 1, f"处理器{i}调用次数错误"


class TestDataPipelineBackpressure:
    """数据管道背压控制测试"""
    
    def test_backpressure_basic_functionality(self):
        """测试背压控制基本功能
        
        **验证需求: US-3.1**
        """
        # 创建大量数据来测试背压
        large_data = [
            pd.DataFrame({'value': list(range(i*100, (i+1)*100))})
            for i in range(10)
        ]
        
        source = PropertyTestDataSource(large_data)
        processors = [PropertyTestProcessor()]
        sink = PropertyTestSink()
        
        # 启用背压控制
        pipeline = DataPipeline(
            source=source,
            processors=processors,
            sink=sink,
            backpressure_enabled=True
        )
        
        pipeline.run()
        
        # 验证所有数据都被处理
        assert sink.total_rows == 1000  # 10 * 100
        assert len(sink.written_data) == 10
    
    def test_backpressure_disabled(self):
        """测试禁用背压控制
        
        **验证需求: US-3.1**
        """
        test_data = [
            pd.DataFrame({'value': [1, 2, 3]}),
            pd.DataFrame({'value': [4, 5, 6]})
        ]
        
        source = PropertyTestDataSource(test_data)
        processors = [PropertyTestProcessor()]
        sink = PropertyTestSink()
        
        # 禁用背压控制
        pipeline = DataPipeline(
            source=source,
            processors=processors,
            sink=sink,
            backpressure_enabled=False
        )
        
        pipeline.run()
        
        # 验证数据仍然正确处理
        assert sink.total_rows == 6
        assert len(sink.written_data) == 2


class TestDataPipelineErrorHandling:
    """数据管道错误处理测试"""
    
    def test_source_error_propagation(self):
        """测试数据源错误传播
        
        **验证需求: US-3.1**
        """
        class FailingSource(DataSource[pd.DataFrame]):
            def read(self) -> pd.DataFrame:
                raise DataSourceError("数据源读取失败")
        
        source = FailingSource()
        processors = [PropertyTestProcessor()]
        sink = PropertyTestSink()
        
        pipeline = DataPipeline(source=source, processors=processors, sink=sink)
        
        with pytest.raises(DataSourceError, match="数据源读取失败"):
            pipeline.run()
    
    def test_processor_error_propagation(self):
        """测试处理器错误传播
        
        **验证需求: US-3.1**
        """
        class FailingProcessor(DataProcessor[pd.DataFrame]):
            def process(self, data: pd.DataFrame) -> pd.DataFrame:
                raise DataProcessError("数据处理失败")
        
        test_data = [pd.DataFrame({'value': [1, 2, 3]})]
        
        source = PropertyTestDataSource(test_data)
        processors = [FailingProcessor()]
        sink = PropertyTestSink()
        
        pipeline = DataPipeline(source=source, processors=processors, sink=sink)
        
        with pytest.raises(DataProcessError, match="数据处理失败"):
            pipeline.run()
    
    def test_sink_error_propagation(self):
        """测试接收器错误传播
        
        **验证需求: US-3.1**
        """
        class FailingSink(DataSink[pd.DataFrame]):
            def write(self, data: pd.DataFrame) -> None:
                raise DataSinkError("数据写入失败")
        
        test_data = [pd.DataFrame({'value': [1, 2, 3]})]
        
        source = PropertyTestDataSource(test_data)
        processors = [PropertyTestProcessor()]
        sink = FailingSink()
        
        pipeline = DataPipeline(source=source, processors=processors, sink=sink)
        
        with pytest.raises(DataSinkError, match="数据写入失败"):
            pipeline.run()


class TestDataPipelineEdgeCases:
    """数据管道边界情况测试"""
    
    def test_empty_data_handling(self):
        """测试空数据处理
        
        **验证需求: US-3.1**
        """
        # 空数据源
        source = PropertyTestDataSource([])
        processors = [PropertyTestProcessor()]
        sink = PropertyTestSink()
        
        pipeline = DataPipeline(source=source, processors=processors, sink=sink)
        pipeline.run()
        
        assert sink.total_rows == 0
        assert len(sink.written_data) == 0
    
    def test_single_empty_dataframe(self):
        """测试单个空数据框
        
        **验证需求: US-3.1**
        """
        empty_df = pd.DataFrame()
        source = PropertyTestDataSource([empty_df])
        processors = [PropertyTestProcessor()]
        sink = PropertyTestSink()
        
        pipeline = DataPipeline(source=source, processors=processors, sink=sink)
        pipeline.run()
        
        # 空数据框不应该被写入
        assert sink.total_rows == 0
        assert len(sink.written_data) == 0
    
    def test_mixed_empty_and_non_empty_data(self):
        """测试混合空和非空数据
        
        **验证需求: US-3.1**
        """
        mixed_data = [
            pd.DataFrame({'value': [1, 2]}),
            pd.DataFrame(),  # 空数据框
            pd.DataFrame({'value': [3, 4]}),
            pd.DataFrame()   # 空数据框
        ]
        
        source = PropertyTestDataSource(mixed_data)
        processors = [PropertyTestProcessor()]
        sink = PropertyTestSink()
        
        pipeline = DataPipeline(source=source, processors=processors, sink=sink)
        pipeline.run()
        
        # 只有非空数据框被处理
        assert sink.total_rows == 4  # 2 + 2
        assert len(sink.written_data) == 2
        
        # 验证数据内容
        all_data = sink.get_all_data()
        assert all_data['value'].tolist() == [1, 2, 3, 4]


if __name__ == "__main__":
    # 运行属性测试
    pytest.main([__file__, "-v", "--tb=short"])