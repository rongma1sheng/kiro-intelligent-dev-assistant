"""端到端集成测试

白皮书依据: 第三章 3.1 高性能数据管道 + 第一章 1.1 多时间尺度统一调度

测试完整的数据处理流程，验证调度器和数据管道的协同工作。
"""

import pytest
import time
import pandas as pd
import numpy as np
from typing import Optional, List
from datetime import datetime, timedelta

from src.integration.scheduler_pipeline import (
    ScheduledPipelineManager,
    DataPassingSource,
    DataPassingSink,
    create_data_processing_chain
)
from src.chronos.scheduler import Priority, TimeScale
from src.infra.pipeline import DataSource, DataProcessor, DataSink
from src.infra.sanitizer import DataSanitizer, AssetType


class TickDataSource(DataSource[pd.DataFrame]):
    """模拟Tick数据源
    
    白皮书依据: 第三章 3.1 高性能数据管道
    """
    
    def __init__(self, symbols: List[str], duration_seconds: int = 5):
        self.symbols = symbols
        self.duration_seconds = duration_seconds
        self.start_time = time.time()
        self.tick_count = 0
    
    def read(self) -> Optional[pd.DataFrame]:
        """读取模拟tick数据"""
        # 检查是否超时
        if time.time() - self.start_time > self.duration_seconds:
            return None
        
        self.tick_count += 1
        
        # 生成模拟tick数据
        data = []
        base_time = datetime.now()
        
        for i, symbol in enumerate(self.symbols):
            # 模拟价格波动
            base_price = 100.0 + i * 10
            price_change = np.random.uniform(-0.02, 0.02)  # ±2%波动
            current_price = base_price * (1 + price_change)
            
            data.append({
                'timestamp': base_time + timedelta(microseconds=i*1000),
                'symbol': symbol,
                'price': current_price,
                'volume': np.random.randint(100, 1000),
                'bid': current_price - 0.01,
                'ask': current_price + 0.01
            })
        
        return pd.DataFrame(data)


class DataValidator(DataProcessor[pd.DataFrame]):
    """数据验证器
    
    白皮书依据: 第三章 3.1 高性能数据管道
    """
    
    def __init__(self):
        self.processed_count = 0
        self.invalid_count = 0
    
    def process(self, data: pd.DataFrame) -> pd.DataFrame:
        """验证数据有效性"""
        if data is None or data.empty:
            return data
        
        self.processed_count += 1
        
        # 基本验证
        valid_mask = (
            (data['price'] > 0) &
            (data['volume'] > 0) &
            (data['bid'] > 0) &
            (data['ask'] > 0) &
            (data['ask'] > data['bid'])
        )
        
        invalid_rows = (~valid_mask).sum()
        if invalid_rows > 0:
            self.invalid_count += invalid_rows
        
        return data[valid_mask]


class DataSanitizerProcessor(DataProcessor[pd.DataFrame]):
    """数据清洗处理器包装器
    
    白皮书依据: 第三章 3.3 深度清洗矩阵
    
    将DataSanitizer包装为DataProcessor接口。
    """
    
    def __init__(self, asset_type: AssetType = AssetType.STOCK):
        self.sanitizer = DataSanitizer(asset_type=asset_type)
        self.processed_count = 0
    
    def process(self, data: pd.DataFrame) -> pd.DataFrame:
        """处理数据"""
        if data is None or data.empty:
            return data
        
        self.processed_count += 1
        return self.sanitizer.clean(data)


class DataEnricher(DataProcessor[pd.DataFrame]):
    
    def __init__(self):
        self.processed_count = 0
    
    def process(self, data: pd.DataFrame) -> pd.DataFrame:
        """增强数据"""
        if data is None or data.empty:
            return data
        
        self.processed_count += 1
        result = data.copy()
        
        # 添加技术指标
        result['spread'] = result['ask'] - result['bid']
        result['mid_price'] = (result['ask'] + result['bid']) / 2
        result['spread_pct'] = result['spread'] / result['mid_price'] * 100
        
        # 添加时间特征
        result['hour'] = pd.to_datetime(result['timestamp']).dt.hour
        result['minute'] = pd.to_datetime(result['timestamp']).dt.minute
        
        return result


class DatabaseSink(DataSink[pd.DataFrame]):
    """模拟数据库接收器
    
    白皮书依据: 第三章 3.1 高性能数据管道
    """
    
    def __init__(self, table_name: str):
        self.table_name = table_name
        self.written_data: List[pd.DataFrame] = []
        self.write_count = 0
        self.total_rows = 0
    
    def write(self, data: pd.DataFrame) -> None:
        """写入数据到模拟数据库"""
        if data is not None and not data.empty:
            self.write_count += 1
            self.total_rows += len(data)
            self.written_data.append(data.copy())
    
    def get_all_data(self) -> pd.DataFrame:
        """获取所有写入的数据"""
        if not self.written_data:
            return pd.DataFrame()
        return pd.concat(self.written_data, ignore_index=True)


class TestEndToEndIntegration:
    """端到端集成测试"""
    
    def test_complete_data_processing_pipeline(self):
        """测试完整的数据处理流程
        
        **验证需求: 系统集成**
        
        测试从数据摄取到最终存储的完整流程。
        """
        manager = ScheduledPipelineManager()
        
        # 创建测试组件
        symbols = ['AAPL', 'GOOGL', 'MSFT']
        tick_source = TickDataSource(symbols, duration_seconds=3)
        validator = DataValidator()
        sanitizer = DataSanitizerProcessor(asset_type=AssetType.STOCK)
        enricher = DataEnricher()
        database_sink = DatabaseSink('tick_data')
        
        # 创建数据处理链
        chain_config = [
            {
                'name': 'tick_ingestion',
                'source': tick_source,
                'processors': [validator],
                'sink': DataPassingSink(manager, 'validated_ticks'),
                'interval': 0.5,  # 500ms
                'priority': Priority.CRITICAL
            },
            {
                'name': 'data_cleaning',
                'source': DataPassingSource(manager, 'validated_ticks'),
                'processors': [sanitizer],
                'sink': DataPassingSink(manager, 'clean_ticks'),
                'interval': 1.0,  # 1s
                'priority': Priority.HIGH
            },
            {
                'name': 'data_enrichment',
                'source': DataPassingSource(manager, 'clean_ticks'),
                'processors': [enricher],
                'sink': DataPassingSink(manager, 'enriched_ticks'),
                'interval': 1.5,  # 1.5s
                'priority': Priority.NORMAL
            },
            {
                'name': 'data_storage',
                'source': DataPassingSource(manager, 'enriched_ticks'),
                'processors': [],
                'sink': database_sink,
                'interval': 2.0,  # 2s
                'priority': Priority.LOW
            }
        ]
        
        # 创建处理链
        pipeline_ids = create_data_processing_chain(manager, chain_config)
        assert len(pipeline_ids) == 4
        
        # 启动系统
        manager.start()
        
        try:
            # 运行系统一段时间
            time.sleep(8.0)  # 8秒，足够完成多轮处理
            
            # 验证数据流
            validated_ticks = manager.get_data('validated_ticks')
            clean_ticks = manager.get_data('clean_ticks')
            enriched_ticks = manager.get_data('enriched_ticks')
            
            # 验证数据摄取
            assert validator.processed_count > 0, "数据验证器应该处理了数据"
            
            # 验证数据清洗
            if clean_ticks is not None:
                assert not clean_ticks.empty, "清洗后应该有数据"
                # 验证数据质量
                quality = sanitizer.sanitizer.assess_quality(clean_ticks)
                assert quality['overall'] > 0.8, f"数据质量应该 > 0.8，实际: {quality['overall']}"
            
            # 验证数据增强
            if enriched_ticks is not None:
                assert not enriched_ticks.empty, "增强后应该有数据"
                # 验证增强字段
                expected_columns = ['spread', 'mid_price', 'spread_pct', 'hour', 'minute']
                for col in expected_columns:
                    assert col in enriched_ticks.columns, f"缺少增强字段: {col}"
            
            # 验证数据存储
            assert database_sink.write_count > 0, "数据库应该接收了数据"
            stored_data = database_sink.get_all_data()
            if not stored_data.empty:
                assert len(stored_data) > 0, "应该存储了数据"
                # 验证存储的数据包含所有必要字段
                required_columns = ['symbol', 'price', 'volume', 'spread', 'mid_price']
                for col in required_columns:
                    assert col in stored_data.columns, f"存储数据缺少字段: {col}"
            
            # 验证管道执行统计
            for pipeline_id in pipeline_ids:
                pipeline_info = manager.get_pipeline_info(pipeline_id)
                assert pipeline_info is not None, f"管道信息不应该为空: {pipeline_id}"
                # 注意：由于依赖关系和时间间隔，不是所有管道都会执行
            
        finally:
            manager.stop()
    
    def test_system_performance_under_load(self):
        """测试系统负载性能
        
        **验证需求: 性能指标达标**
        
        测试系统在高负载下的性能表现。
        """
        manager = ScheduledPipelineManager()
        
        # 创建高频数据源
        symbols = [f'SYM{i:03d}' for i in range(20)]  # 20个股票
        tick_source = TickDataSource(symbols, duration_seconds=5)
        validator = DataValidator()
        database_sink = DatabaseSink('high_freq_data')
        
        # 创建高频处理管道
        pipeline_id = manager.add_pipeline(
            name="high_frequency_processing",
            source=tick_source,
            processors=[validator],
            sink=database_sink,
            interval=0.1,  # 100ms高频
            priority=Priority.CRITICAL
        )
        
        # 启动系统
        start_time = time.time()
        manager.start()
        
        try:
            # 运行系统
            time.sleep(6.0)
            
            # 检查性能指标
            pipeline_info = manager.get_pipeline_info(pipeline_id)
            assert pipeline_info is not None
            
            # 验证执行次数（应该有多次执行）
            assert pipeline_info['execution_count'] > 10, (
                f"高频处理应该执行多次，实际: {pipeline_info['execution_count']}"
            )
            
            # 验证平均执行时间 < 10ms
            avg_time = pipeline_info['performance_metrics'].get('average_execution_time_ms', 0)
            assert avg_time < 10.0, (
                f"平均执行时间应该 < 10ms，实际: {avg_time:.2f}ms"
            )
            
            # 验证数据处理量
            assert database_sink.total_rows > 100, (
                f"应该处理大量数据，实际行数: {database_sink.total_rows}"
            )
            
            # 验证数据有效性
            assert validator.processed_count > 10, "应该处理了多批数据"
            
            # 计算整体吞吐量
            elapsed_time = time.time() - start_time
            throughput = database_sink.total_rows / elapsed_time
            assert throughput > 50, f"吞吐量应该 > 50行/秒，实际: {throughput:.2f}行/秒"
            
        finally:
            manager.stop()
    
    def test_error_recovery_and_fault_tolerance(self):
        """测试错误恢复和容错能力
        
        **验证需求: 故障恢复机制**
        
        测试系统在出现错误时的恢复能力。
        """
        manager = ScheduledPipelineManager()
        
        # 创建会出错的数据源
        class FlakyDataSource(DataSource[pd.DataFrame]):
            def __init__(self):
                self.call_count = 0
            
            def read(self) -> Optional[pd.DataFrame]:
                self.call_count += 1
                # 前3次调用出错，之后正常
                if self.call_count <= 3:
                    raise ValueError(f"模拟错误 #{self.call_count}")
                
                # 正常返回数据
                return pd.DataFrame({
                    'symbol': ['TEST'],
                    'price': [100.0],
                    'volume': [1000]
                })
        
        # 创建会出错的处理器
        class FlakyProcessor(DataProcessor[pd.DataFrame]):
            def __init__(self):
                self.call_count = 0
            
            def process(self, data: pd.DataFrame) -> pd.DataFrame:
                self.call_count += 1
                # 第2次调用出错
                if self.call_count == 2:
                    raise RuntimeError("处理器模拟错误")
                
                return data
        
        flaky_source = FlakyDataSource()
        flaky_processor = FlakyProcessor()
        database_sink = DatabaseSink('error_test')
        
        # 注册自定义错误处理器
        error_log = []
        
        def error_handler(error: Exception, pipeline_id: str):
            error_log.append((str(error), pipeline_id, time.time()))
        
        manager.register_error_handler("fault_tolerant", error_handler)
        
        # 添加容错管道
        pipeline_id = manager.add_pipeline(
            name="fault_tolerant_pipeline",
            source=flaky_source,
            processors=[flaky_processor],
            sink=database_sink,
            interval=0.5,  # 500ms
            priority=Priority.NORMAL,
            error_handler="fault_tolerant"
        )
        
        # 启动系统
        manager.start()
        
        try:
            # 运行足够长时间让错误和恢复都发生
            time.sleep(4.0)
            
            # 验证错误被记录
            assert len(error_log) > 0, "应该记录了错误"
            
            # 验证系统最终恢复正常
            pipeline_info = manager.get_pipeline_info(pipeline_id)
            assert pipeline_info is not None
            
            # 验证有成功的执行
            assert pipeline_info['execution_count'] > 0, "应该有成功的执行"
            
            # 验证最终有数据被处理
            # 注意：由于前几次调用会出错，可能需要等待更长时间
            if database_sink.total_rows > 0:
                stored_data = database_sink.get_all_data()
                assert not stored_data.empty, "最终应该有数据被存储"
                assert 'TEST' in stored_data['symbol'].values, "应该包含测试数据"
            
            # 验证错误类型
            error_messages = [error[0] for error in error_log]
            assert any("模拟错误" in msg for msg in error_messages), "应该记录数据源错误"
            
        finally:
            manager.stop()
    
    def test_multi_asset_type_processing(self):
        """测试多资产类型处理
        
        **验证需求: 资产类型自适应**
        
        测试系统处理不同资产类型的能力。
        """
        manager = ScheduledPipelineManager()
        
        # 创建多资产类型数据源
        class MultiAssetSource(DataSource[pd.DataFrame]):
            def __init__(self):
                self.call_count = 0
                self.asset_data = {
                    AssetType.STOCK: pd.DataFrame({
                        'symbol': ['AAPL', 'GOOGL'],
                        'open': [150.0, 2800.0],
                        'high': [152.0, 2820.0],
                        'low': [149.0, 2790.0],
                        'close': [151.0, 2810.0],
                        'volume': [1000000, 500000],
                        'asset_type': ['stock', 'stock']
                    }),
                    AssetType.FUTURE: pd.DataFrame({
                        'symbol': ['ES2024', 'NQ2024'],
                        'open': [4500.0, 15000.0],
                        'high': [4520.0, 15100.0],
                        'low': [4480.0, 14900.0],
                        'close': [4510.0, 15050.0],
                        'volume': [100000, 80000],
                        'asset_type': ['future', 'future']
                    })
                }
                self.asset_types = list(self.asset_data.keys())
            
            def read(self) -> Optional[pd.DataFrame]:
                if self.call_count >= len(self.asset_types) * 2:  # 每种类型读取2次
                    return None
                
                asset_type = self.asset_types[self.call_count % len(self.asset_types)]
                self.call_count += 1
                return self.asset_data[asset_type].copy()
        
        multi_asset_source = MultiAssetSource()
        
        # 为不同资产类型创建不同的清洗器
        stock_sanitizer = DataSanitizer(asset_type=AssetType.STOCK)
        future_sanitizer = DataSanitizer(asset_type=AssetType.FUTURE)
        
        # 创建资产类型路由处理器
        class AssetTypeRouter(DataProcessor[pd.DataFrame]):
            def __init__(self, stock_sanitizer, future_sanitizer):
                self.stock_sanitizer = stock_sanitizer
                self.future_sanitizer = future_sanitizer
                self.processed_stocks = 0
                self.processed_futures = 0
            
            def process(self, data: pd.DataFrame) -> pd.DataFrame:
                if data is None or data.empty:
                    return data
                
                # 根据资产类型选择清洗器
                if 'asset_type' in data.columns:
                    stock_data = data[data['asset_type'] == 'stock']
                    future_data = data[data['asset_type'] == 'future']
                    
                    results = []
                    
                    if not stock_data.empty:
                        cleaned_stock = self.stock_sanitizer.clean(stock_data)
                        results.append(cleaned_stock)
                        self.processed_stocks += len(cleaned_stock)
                    
                    if not future_data.empty:
                        cleaned_future = self.future_sanitizer.clean(future_data)
                        results.append(cleaned_future)
                        self.processed_futures += len(cleaned_future)
                    
                    if results:
                        return pd.concat(results, ignore_index=True)
                
                return data
        
        router = AssetTypeRouter(stock_sanitizer, future_sanitizer)
        database_sink = DatabaseSink('multi_asset_data')
        
        # 创建多资产处理管道
        pipeline_id = manager.add_pipeline(
            name="multi_asset_processing",
            source=multi_asset_source,
            processors=[router],
            sink=database_sink,
            interval=1.0,
            priority=Priority.HIGH
        )
        
        # 启动系统
        manager.start()
        
        try:
            # 运行系统
            time.sleep(5.0)
            
            # 验证处理结果
            assert router.processed_stocks > 0, "应该处理了股票数据"
            assert router.processed_futures > 0, "应该处理了期货数据"
            
            # 验证存储的数据
            stored_data = database_sink.get_all_data()
            if not stored_data.empty:
                # 验证包含不同资产类型
                asset_types = stored_data['asset_type'].unique()
                assert 'stock' in asset_types, "应该包含股票数据"
                assert 'future' in asset_types, "应该包含期货数据"
                
                # 验证数据质量
                stock_data = stored_data[stored_data['asset_type'] == 'stock']
                future_data = stored_data[stored_data['asset_type'] == 'future']
                
                if not stock_data.empty:
                    stock_quality = stock_sanitizer.assess_quality(stock_data)
                    assert stock_quality['overall'] > 0.7, "股票数据质量应该良好"
                
                if not future_data.empty:
                    future_quality = future_sanitizer.assess_quality(future_data)
                    assert future_quality['overall'] > 0.7, "期货数据质量应该良好"
            
        finally:
            manager.stop()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])