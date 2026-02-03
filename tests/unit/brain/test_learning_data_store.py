"""学习数据存储单元测试

白皮书依据: 第二章 2.2.4 风险控制元学习架构 - 数据管理

测试范围：
1. 数据保存
2. 数据加载
3. 数据归档
4. 数据清理

Author: MIA Team
Date: 2026-01-22
Version: v1.0
"""

import pytest
import tempfile
import shutil
import gzip
import json
from pathlib import Path
from datetime import datetime, timedelta

from src.brain.learning_data_store import LearningDataStore
from src.brain.risk_control_meta_learner import (
    LearningDataPoint,
    MarketContext,
    PerformanceMetrics
)


class TestLearningDataStore:
    """测试学习数据存储"""
    
    @pytest.fixture
    def temp_dir(self):
        """创建临时目录"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        # 清理
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    @pytest.fixture
    def store(self, temp_dir):
        """创建数据存储实例"""
        return LearningDataStore(
            data_dir=temp_dir,
            retention_days=365
        )
    
    @pytest.fixture
    def sample_data_point(self):
        """创建示例数据点"""
        market_context = MarketContext(
            volatility=0.25,
            liquidity=1000000.0,
            trend_strength=0.5,
            regime='bull',
            aum=100000.0,
            portfolio_concentration=0.3,
            recent_drawdown=-0.05
        )
        
        perf_a = PerformanceMetrics(
            sharpe_ratio=1.5,
            max_drawdown=-0.10,
            win_rate=0.6,
            profit_factor=2.0,
            calmar_ratio=15.0,
            sortino_ratio=1.8,
            decision_latency_ms=10.0
        )
        
        perf_b = PerformanceMetrics(
            sharpe_ratio=1.2,
            max_drawdown=-0.15,
            win_rate=0.55,
            profit_factor=1.8,
            calmar_ratio=8.0,
            sortino_ratio=1.4,
            decision_latency_ms=50.0
        )
        
        return LearningDataPoint(
            timestamp=datetime.now().isoformat(),
            market_context=market_context,
            architecture_a_performance=perf_a,
            architecture_b_performance=perf_b,
            winner='strategy_a',
            metadata={'test': True}
        )
    
    def test_initialization(self, temp_dir):
        """测试初始化"""
        store = LearningDataStore(data_dir=temp_dir, retention_days=365)
        
        # 验证
        assert store.data_dir == Path(temp_dir)
        assert store.retention_days == 365
        assert store.data_dir.exists()
        assert store.stats['total_saved'] == 0
    
    def test_initialization_invalid_retention(self, temp_dir):
        """测试无效保留天数"""
        with pytest.raises(ValueError, match="retention_days必须 > 0"):
            LearningDataStore(data_dir=temp_dir, retention_days=0)
    
    def test_save_data_point(self, store, sample_data_point):
        """测试保存数据点"""
        # 保存数据点
        success = store.save_data_point(sample_data_point)
        
        # 验证
        assert success
        assert store.stats['total_saved'] == 1
        assert store.current_file.exists()
        
        # 验证文件内容
        with open(store.current_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            assert len(lines) == 1
            data = json.loads(lines[0])
            assert data['winner'] == 'strategy_a'
            assert data['market_context']['volatility'] == 0.25
    
    def test_save_multiple_data_points(self, store, sample_data_point):
        """测试保存多个数据点"""
        # 保存多个数据点
        for i in range(10):
            success = store.save_data_point(sample_data_point)
            assert success
        
        # 验证
        assert store.stats['total_saved'] == 10
        
        # 验证文件内容
        with open(store.current_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            assert len(lines) == 10
    
    def test_load_historical_data(self, store, sample_data_point):
        """测试加载历史数据"""
        # 保存数据点
        for _ in range(5):
            store.save_data_point(sample_data_point)
        
        # 加载数据
        data = store.load_historical_data()
        
        # 验证
        assert len(data) == 5
        assert store.stats['total_loaded'] == 5
        assert all('winner' in d for d in data)
    
    def test_load_historical_data_with_max_samples(self, store, sample_data_point):
        """测试加载历史数据（限制样本数）"""
        # 保存数据点
        for _ in range(10):
            store.save_data_point(sample_data_point)
        
        # 加载数据（限制3个样本）
        data = store.load_historical_data(max_samples=3)
        
        # 验证
        assert len(data) == 3
    
    def test_load_historical_data_empty(self, store):
        """测试加载空数据"""
        # 加载数据（没有数据）
        data = store.load_historical_data()
        
        # 验证
        assert len(data) == 0
    
    def test_archive_file(self, store, sample_data_point):
        """测试归档文件"""
        # 保存数据点
        store.save_data_point(sample_data_point)
        
        # 归档文件
        success = store._archive_file(store.current_file)
        
        # 验证
        assert success
        assert store.stats['total_archived'] == 1
        
        # 验证压缩文件存在
        compressed_file = store.current_file.with_suffix('.jsonl.gz')
        assert compressed_file.exists()
        
        # 验证原文件已删除
        assert not store.current_file.exists()
        
        # 验证压缩文件内容
        with gzip.open(compressed_file, 'rt', encoding='utf-8') as f:
            lines = f.readlines()
            assert len(lines) == 1
            data = json.loads(lines[0])
            assert data['winner'] == 'strategy_a'
    
    def test_archive_nonexistent_file(self, store):
        """测试归档不存在的文件"""
        # 归档不存在的文件
        fake_file = store.data_dir / 'nonexistent.jsonl'
        success = store._archive_file(fake_file)
        
        # 验证
        assert not success
    
    def test_load_compressed_file(self, store, sample_data_point):
        """测试加载压缩文件"""
        # 保存并归档数据点
        store.save_data_point(sample_data_point)
        store._archive_file(store.current_file)
        
        # 加载数据（包含压缩文件）
        data = store.load_historical_data()
        
        # 验证
        assert len(data) == 1
        assert data[0]['winner'] == 'strategy_a'
    
    def test_cleanup_old_data(self, store, sample_data_point):
        """测试清理过期数据"""
        # 创建过期文件（模拟）
        old_date = (datetime.now() - timedelta(days=400)).strftime('%Y-%m')
        old_file = store.data_dir / f"risk_control_learning_{old_date}.jsonl"
        
        # 写入数据
        with open(old_file, 'w', encoding='utf-8') as f:
            f.write('{"test": true}\n')
        
        # 清理过期数据
        deleted_count = store.cleanup_old_data()
        
        # 验证
        assert deleted_count == 1
        assert store.stats['total_deleted'] == 1
        assert not old_file.exists()
    
    def test_cleanup_old_data_no_files(self, store):
        """测试清理过期数据（无文件）"""
        # 清理过期数据
        deleted_count = store.cleanup_old_data()
        
        # 验证
        assert deleted_count == 0
    
    def test_get_statistics(self, store, sample_data_point):
        """测试获取统计信息"""
        # 保存数据点
        for _ in range(5):
            store.save_data_point(sample_data_point)
        
        # 加载数据
        store.load_historical_data()
        
        # 获取统计信息
        stats = store.get_statistics()
        
        # 验证
        assert stats['total_saved'] == 5
        assert stats['total_loaded'] == 5
        assert stats['file_count'] >= 1
        assert stats['total_size_bytes'] > 0
        assert 'data_dir' in stats
        assert 'retention_days' in stats
    
    def test_extract_date_from_filename(self, store):
        """测试从文件名提取日期"""
        # 测试JSONL文件
        date1 = store._extract_date_from_filename('risk_control_learning_2026-01.jsonl')
        assert date1 == '2026-01'
        
        # 测试压缩文件
        date2 = store._extract_date_from_filename('risk_control_learning_2025-12.jsonl.gz')
        assert date2 == '2025-12'
        
        # 测试无效文件名
        date3 = store._extract_date_from_filename('invalid_filename.txt')
        assert date3 is None
    
    def test_get_data_files(self, store, sample_data_point):
        """测试获取数据文件列表"""
        # 保存数据点
        store.save_data_point(sample_data_point)
        
        # 获取数据文件
        files = store._get_data_files()
        
        # 验证
        assert len(files) >= 1
        assert all(isinstance(f, Path) for f in files)
    
    def test_get_data_files_with_date_range(self, store):
        """测试获取数据文件列表（日期范围）"""
        # 创建多个月份的文件
        dates = ['2026-01', '2025-12', '2025-11']
        for date in dates:
            file_path = store.data_dir / f"risk_control_learning_{date}.jsonl"
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write('{"test": true}\n')
        
        # 获取数据文件（指定日期范围）
        files = store._get_data_files(start_date='2025-12', end_date='2026-01')
        
        # 验证
        assert len(files) == 2
        assert any('2026-01' in f.name for f in files)
        assert any('2025-12' in f.name for f in files)
        assert not any('2025-11' in f.name for f in files)
    
    def test_repr(self, store):
        """测试字符串表示"""
        repr_str = repr(store)
        
        # 验证
        assert 'LearningDataStore' in repr_str
        assert 'retention_days=365' in repr_str


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
