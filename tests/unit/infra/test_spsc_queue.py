"""SPSC队列测试

白皮书依据: 第三章 3.1 高性能数据管道

测试SPSC队列的正确性属性：
- 属性7: FIFO顺序保证
- 属性8: 无数据丢失
- 属性9: 延迟上界
"""

import pytest
import time
import threading
from typing import List
import random

from src.infra.spsc_queue import SPSCQueue, SPSCQueueError, benchmark_spsc_queue


class TestSPSCQueue:
    """SPSC队列测试类
    
    白皮书依据: 第三章 3.1 高性能数据管道
    """
    
    @pytest.fixture
    def queue(self):
        """测试夹具：创建SPSC队列实例"""
        queue = SPSCQueue[str](capacity=16, item_size=1024)
        yield queue
        queue.close()
        try:
            queue.unlink()
        except Exception:
            pass
    
    def test_basic_enqueue_dequeue(self, queue):
        """基础入队出队测试"""
        # 测试空队列
        assert queue.is_empty()
        assert not queue.is_full()
        assert queue.size() == 0
        assert queue.dequeue() is None
        
        # 测试入队
        assert queue.enqueue("hello")
        assert not queue.is_empty()
        assert queue.size() == 1
        
        # 测试出队
        item = queue.dequeue()
        assert item == "hello"
        assert queue.is_empty()
        assert queue.size() == 0
    
    def test_property_7_fifo_order_guarantee(self, queue):
        """属性7: FIFO顺序保证
        
        白皮书依据: 第三章 3.1 SPSC队列
        验证需求: US-3.1
        
        测试场景：
        1. 按顺序入队多个元素
        2. 按顺序出队
        3. 验证出队顺序与入队顺序一致
        """
        # 入队测试数据
        test_data = [f"item_{i}" for i in range(10)]
        
        for item in test_data:
            assert queue.enqueue(item), f"Failed to enqueue {item}"
        
        # 出队并验证顺序
        result = []
        while not queue.is_empty():
            item = queue.dequeue()
            if item is not None:
                result.append(item)
        
        assert result == test_data, f"FIFO order violated: expected {test_data}, got {result}"
    
    def test_property_7_fifo_with_interleaved_operations(self, queue):
        """属性7扩展: 交替操作的FIFO保证
        
        测试场景：
        1. 交替进行入队和出队操作
        2. 验证FIFO顺序始终保持
        """
        expected_order = []
        actual_order = []
        
        # 交替操作
        for i in range(5):
            # 入队2个元素
            for j in range(2):
                item = f"batch_{i}_item_{j}"
                expected_order.append(item)
                assert queue.enqueue(item)
            
            # 出队1个元素
            item = queue.dequeue()
            if item is not None:
                actual_order.append(item)
        
        # 出队剩余元素
        while not queue.is_empty():
            item = queue.dequeue()
            if item is not None:
                actual_order.append(item)
        
        assert actual_order == expected_order, \
            f"FIFO order violated in interleaved operations: expected {expected_order}, got {actual_order}"
    
    def test_property_8_no_data_loss(self, queue):
        """属性8: 无数据丢失
        
        白皮书依据: 第三章 3.1 SPSC队列
        验证需求: US-3.1
        
        测试场景：
        1. 入队大量数据
        2. 验证所有数据都能出队
        3. 验证数据内容完整性
        """
        # 使用较小的数据集，适合16容量的队列
        test_data = [f"data_{i}_{random.randint(1000, 9999)}" for i in range(20)]
        
        # 交替入队出队，确保所有数据都能处理
        enqueued = []
        dequeued = []
        
        for item in test_data:
            # 如果队列满了，先出队一些数据
            while queue.is_full():
                dequeued_item = queue.dequeue()
                if dequeued_item is not None:
                    dequeued.append(dequeued_item)
            
            # 入队当前项
            success = queue.enqueue(item)
            assert success, f"Failed to enqueue {item} when queue should have space"
            enqueued.append(item)
        
        # 出队剩余所有数据
        while not queue.is_empty():
            item = queue.dequeue()
            if item is not None:
                dequeued.append(item)
        
        # 验证无数据丢失
        assert len(dequeued) == len(enqueued), \
            f"Data loss detected: enqueued {len(enqueued)}, dequeued {len(dequeued)}"
        
        # 验证数据完整性（FIFO顺序）
        assert dequeued == enqueued, "Data integrity violated"
    
    def test_property_8_concurrent_no_data_loss(self, queue):
        """属性8扩展: 并发场景下的无数据丢失
        
        测试场景：
        1. 一个线程持续入队
        2. 另一个线程持续出队
        3. 验证所有入队的数据都能出队
        """
        enqueued_items = []
        dequeued_items = []
        stop_flag = threading.Event()
        enqueue_lock = threading.Lock()
        dequeue_lock = threading.Lock()
        
        def producer():
            """生产者线程"""
            for i in range(100):  # 减少数量避免超时
                item = f"concurrent_item_{i}"
                # 重试直到成功入队或停止
                while not stop_flag.is_set():
                    if queue.enqueue(item):
                        with enqueue_lock:
                            enqueued_items.append(item)
                        break
                    time.sleep(0.000001)  # 1μs
                if stop_flag.is_set():
                    break
        
        def consumer():
            """消费者线程"""
            while not stop_flag.is_set() or not queue.is_empty():
                item = queue.dequeue()
                if item is not None:
                    with dequeue_lock:
                        dequeued_items.append(item)
                else:
                    time.sleep(0.000001)  # 1μs
        
        # 启动线程
        producer_thread = threading.Thread(target=producer)
        consumer_thread = threading.Thread(target=consumer)
        
        producer_thread.start()
        consumer_thread.start()
        
        # 运行一段时间后停止
        time.sleep(0.05)  # 减少运行时间
        stop_flag.set()
        
        producer_thread.join(timeout=2.0)
        consumer_thread.join(timeout=2.0)
        
        # 验证无数据丢失
        assert len(dequeued_items) == len(enqueued_items), \
            f"Concurrent data loss: enqueued {len(enqueued_items)}, dequeued {len(dequeued_items)}"
        
        # 验证FIFO顺序
        assert dequeued_items == enqueued_items, "Concurrent FIFO order violated"
    
    def test_property_9_latency_upper_bound(self, queue):
        """属性9: 延迟上界
        
        白皮书依据: 第三章 3.1 SPSC队列
        验证需求: US-3.1
        
        性能要求: 读写延迟 < 100μs
        
        测试场景：
        1. 测量单次入队延迟
        2. 测量单次出队延迟
        3. 验证99%的操作延迟 < 100μs
        """
        test_data = "x" * 512  # 512字节测试数据
        num_operations = 1000
        
        # 测量入队延迟
        enqueue_latencies = []
        for i in range(num_operations):
            start_time = time.perf_counter()
            success = queue.enqueue(f"{test_data}_{i}")
            end_time = time.perf_counter()
            
            if success:
                latency_us = (end_time - start_time) * 1_000_000
                enqueue_latencies.append(latency_us)
            else:
                # 队列满时先出队
                queue.dequeue()
                start_time = time.perf_counter()
                queue.enqueue(f"{test_data}_{i}")
                end_time = time.perf_counter()
                latency_us = (end_time - start_time) * 1_000_000
                enqueue_latencies.append(latency_us)
        
        # 测量出队延迟
        dequeue_latencies = []
        for i in range(num_operations):
            start_time = time.perf_counter()
            item = queue.dequeue()
            end_time = time.perf_counter()
            
            if item is not None:
                latency_us = (end_time - start_time) * 1_000_000
                dequeue_latencies.append(latency_us)
        
        # 计算P99延迟
        enqueue_latencies.sort()
        dequeue_latencies.sort()
        
        enqueue_p99 = enqueue_latencies[int(len(enqueue_latencies) * 0.99)]
        dequeue_p99 = dequeue_latencies[int(len(dequeue_latencies) * 0.99)]
        
        # 验证延迟要求
        assert enqueue_p99 < 100.0, f"Enqueue P99 latency {enqueue_p99:.2f}μs exceeds 100μs"
        assert dequeue_p99 < 100.0, f"Dequeue P99 latency {dequeue_p99:.2f}μs exceeds 100μs"
        
        # 记录统计信息
        avg_enqueue = sum(enqueue_latencies) / len(enqueue_latencies)
        avg_dequeue = sum(dequeue_latencies) / len(dequeue_latencies)
        
        print(f"Enqueue latency: avg={avg_enqueue:.2f}μs, p99={enqueue_p99:.2f}μs")
        print(f"Dequeue latency: avg={avg_dequeue:.2f}μs, p99={dequeue_p99:.2f}μs")
    
    def test_queue_full_behavior(self, queue):
        """队列满时的行为测试"""
        # 填满队列（容量为16，实际可用15个位置）
        for i in range(15):
            assert queue.enqueue(f"item_{i}")
        
        assert queue.is_full()
        
        # 尝试再次入队应该失败
        assert not queue.enqueue("overflow_item")
        
        # 出队一个元素后应该可以再次入队
        item = queue.dequeue()
        assert item == "item_0"
        assert queue.enqueue("new_item")
    
    def test_queue_empty_behavior(self, queue):
        """队列空时的行为测试"""
        assert queue.is_empty()
        assert queue.dequeue() is None
        
        # 入队后出队
        queue.enqueue("test")
        assert queue.dequeue() == "test"
        assert queue.is_empty()
        assert queue.dequeue() is None
    
    def test_large_items(self, queue):
        """大数据项测试"""
        # 测试接近最大大小的数据
        large_data = "x" * 1000  # 1000字节
        assert queue.enqueue(large_data)
        
        result = queue.dequeue()
        assert result == large_data
        
        # 测试超过最大大小的数据
        oversized_data = "x" * 2000  # 2000字节，超过1024字节限制
        with pytest.raises(SPSCQueueError, match="Item too large"):
            queue.enqueue(oversized_data)
    
    def test_different_data_types(self, queue):
        """不同数据类型测试"""
        test_items = [
            "string",
            123,
            [1, 2, 3],
            {"key": "value"},
            (1, 2, 3),
            None
        ]
        
        # 入队所有类型
        for item in test_items:
            assert queue.enqueue(item)
        
        # 出队并验证
        results = []
        expected_count = len(test_items)
        
        # 出队指定数量的项目，而不是检查None
        for _ in range(expected_count):
            if not queue.is_empty():
                item = queue.dequeue()
                results.append(item)
        
        assert results == test_items
    
    def test_queue_stats(self, queue):
        """队列统计信息测试"""
        # 空队列统计
        stats = queue.get_stats()
        assert stats["capacity"] == 16
        assert stats["current_size"] == 0
        assert stats["is_empty"] is True
        assert stats["is_full"] is False
        assert stats["integrity_ok"] is True
        
        # 添加一些数据
        for i in range(5):
            queue.enqueue(f"item_{i}")
        
        stats = queue.get_stats()
        assert stats["current_size"] == 5
        assert stats["is_empty"] is False
        assert stats["is_full"] is False
    
    def test_integrity_verification(self, queue):
        """完整性验证测试"""
        # 初始状态应该完整
        assert queue.verify_integrity()
        
        # 添加数据后仍应完整
        for i in range(10):
            queue.enqueue(f"item_{i}")
        
        assert queue.verify_integrity()
        
        # 出队后仍应完整
        for i in range(5):
            queue.dequeue()
        
        assert queue.verify_integrity()
    
    def test_clear_operation(self, queue):
        """清空操作测试"""
        # 添加数据
        for i in range(10):
            queue.enqueue(f"item_{i}")
        
        assert not queue.is_empty()
        
        # 清空队列
        queue.clear()
        
        assert queue.is_empty()
        assert queue.size() == 0
        assert queue.verify_integrity()
    
    def test_context_manager(self):
        """上下文管理器测试"""
        with SPSCQueue[str](capacity=16, item_size=1024) as queue:
            queue.enqueue("test")
            assert queue.dequeue() == "test"
        
        # 队列应该已经关闭
        # 注意：关闭后的行为取决于具体实现
    
    def test_invalid_parameters(self):
        """无效参数测试"""
        # 容量不是2的幂
        with pytest.raises(ValueError, match="capacity必须是2的幂"):
            SPSCQueue[str](capacity=15)
        
        # 容量为0
        with pytest.raises(ValueError, match="capacity必须是2的幂"):
            SPSCQueue[str](capacity=0)
        
        # 负的item_size
        with pytest.raises(ValueError, match="item_size必须 > 0"):
            SPSCQueue[str](capacity=16, item_size=-1)
    
    def test_concurrent_access_safety(self, queue):
        """并发访问安全性测试"""
        results = []
        errors = []
        
        def producer():
            try:
                for i in range(100):
                    while not queue.enqueue(f"item_{i}"):
                        time.sleep(0.000001)
            except Exception as e:
                errors.append(f"Producer error: {e}")
        
        def consumer():
            try:
                count = 0
                while count < 100:
                    item = queue.dequeue()
                    if item is not None:
                        results.append(item)
                        count += 1
                    else:
                        time.sleep(0.000001)
            except Exception as e:
                errors.append(f"Consumer error: {e}")
        
        # 启动并发线程
        threads = [
            threading.Thread(target=producer),
            threading.Thread(target=consumer)
        ]
        
        for thread in threads:
            thread.start()
        
        for thread in threads:
            thread.join(timeout=5.0)
        
        # 验证结果
        assert not errors, f"Concurrent access errors: {errors}"
        assert len(results) == 100, f"Expected 100 items, got {len(results)}"
        
        # 验证顺序
        expected = [f"item_{i}" for i in range(100)]
        assert results == expected, "Concurrent access violated FIFO order"


class TestSPSCQueuePerformance:
    """SPSC队列性能测试类"""
    
    def test_benchmark_performance(self):
        """性能基准测试"""
        results = benchmark_spsc_queue(
            capacity=1024,
            item_size=1024,
            num_operations=10000
        )
        
        # 验证性能指标
        assert results["avg_write_latency_us"] < 100.0, \
            f"Write latency {results['avg_write_latency_us']:.2f}μs exceeds 100μs"
        
        assert results["avg_read_latency_us"] < 100.0, \
            f"Read latency {results['avg_read_latency_us']:.2f}μs exceeds 100μs"
        
        # 验证吞吐量 (Windows系统调整期望值)
        assert results["write_ops_per_sec"] > 50000, \
            f"Write throughput {results['write_ops_per_sec']:.0f} ops/sec too low"
        
        assert results["read_ops_per_sec"] > 50000, \
            f"Read throughput {results['read_ops_per_sec']:.0f} ops/sec too low"
        
        print(f"Performance results: {results}")
    
    @pytest.mark.parametrize("capacity,item_size", [
        (64, 256),
        (256, 512),
        (1024, 1024),
        (4096, 2048),
    ])
    def test_different_configurations(self, capacity, item_size):
        """不同配置的性能测试"""
        with SPSCQueue[str](capacity=capacity, item_size=item_size) as queue:
            test_data = "x" * (item_size // 2)
            
            # 简单的读写测试
            start_time = time.perf_counter()
            
            # 写入测试
            for i in range(min(1000, capacity // 2)):
                while not queue.enqueue(f"{test_data}_{i}"):
                    time.sleep(0.000001)
            
            # 读取测试
            count = 0
            while not queue.is_empty() and count < 1000:
                item = queue.dequeue()
                if item is not None:
                    count += 1
            
            elapsed = time.perf_counter() - start_time
            
            # 基本性能验证
            assert elapsed < 1.0, f"Configuration {capacity}/{item_size} too slow: {elapsed:.3f}s"