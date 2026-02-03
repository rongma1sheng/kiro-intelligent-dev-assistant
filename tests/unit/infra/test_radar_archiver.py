"""
雷达信号归档器单元测试

白皮书依据: 第一章 1.5.3 诊疗态任务调度
测试范围: RadarArchiver的信号归档和查询功能
"""

import pytest
import tempfile
import shutil
import json
from datetime import date, datetime, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.infra.radar_archiver import (
    RadarArchiver,
    RadarSignal,
    ArchiveStats,
    SignalType,
    SignalSource
)


class TestSignalType:
    """SignalType枚举测试"""
    
    def test_signal_type_values(self):
        """测试信号类型枚举值"""
        assert SignalType.BUY.value == "买入"
        assert SignalType.SELL.value == "卖出"
        assert SignalType.HOLD.value == "持有"
        assert SignalType.ALERT.value == "预警"
        assert SignalType.RISK.value == "风险"


class TestSignalSource:
    """SignalSource枚举测试"""
    
    def test_signal_source_values(self):
        """测试信号来源枚举值"""
        assert SignalSource.FACTOR.value == "因子"
        assert SignalSource.STRATEGY.value == "策略"
        assert SignalSource.RISK_CONTROL.value == "风控"
        assert SignalSource.SENTIMENT.value == "舆情"


class TestRadarSignal:
    """RadarSignal数据类测试"""
    
    def test_signal_creation(self):
        """测试信号创建"""
        signal = RadarSignal(
            signal_id="sig_001",
            symbol="000001.SZ",
            signal_type=SignalType.BUY,
            source=SignalSource.FACTOR,
            strength=0.8,
            confidence=0.9,
            reason="动量突破"
        )
        
        assert signal.signal_id == "sig_001"
        assert signal.symbol == "000001.SZ"
        assert signal.signal_type == SignalType.BUY
        assert signal.strength == 0.8
    
    def test_signal_defaults(self):
        """测试信号默认值"""
        signal = RadarSignal(
            signal_id="sig_001",
            symbol="000001.SZ",
            signal_type=SignalType.BUY,
            source=SignalSource.FACTOR
        )
        
        assert signal.strength == 0.5
        assert signal.confidence == 0.5
        assert signal.reason == ""
    
    def test_signal_to_dict(self):
        """测试信号转字典"""
        signal = RadarSignal(
            signal_id="sig_001",
            symbol="000001.SZ",
            signal_type=SignalType.BUY,
            source=SignalSource.FACTOR
        )
        
        result = signal.to_dict()
        
        assert result["signal_id"] == "sig_001"
        assert result["signal_type"] == "买入"
        assert result["source"] == "因子"
    
    def test_signal_from_dict(self):
        """测试从字典创建信号"""
        data = {
            "signal_id": "sig_001",
            "symbol": "000001.SZ",
            "signal_type": "买入",
            "source": "因子",
            "strength": 0.8,
            "confidence": 0.9,
            "reason": "测试",
            "metadata": {},
            "timestamp": datetime.now().isoformat()
        }
        
        signal = RadarSignal.from_dict(data)
        
        assert signal.signal_id == "sig_001"
        assert signal.signal_type == SignalType.BUY
        assert signal.source == SignalSource.FACTOR


class TestRadarArchiver:
    """RadarArchiver归档器测试"""
    
    @pytest.fixture
    def temp_dir(self):
        """创建临时目录"""
        temp_path = tempfile.mkdtemp()
        yield temp_path
        if Path(temp_path).exists():
            shutil.rmtree(temp_path)
    
    @pytest.fixture
    def archiver(self, temp_dir):
        """创建归档器实例"""
        return RadarArchiver(
            archive_path=temp_dir,
            retention_days=30
        )
    
    @pytest.fixture
    def sample_signal(self):
        """创建示例信号"""
        return RadarSignal(
            signal_id="sig_001",
            symbol="000001.SZ",
            signal_type=SignalType.BUY,
            source=SignalSource.FACTOR,
            strength=0.8,
            reason="测试信号"
        )
    
    def test_init(self, temp_dir):
        """测试初始化"""
        archiver = RadarArchiver(
            archive_path=temp_dir,
            retention_days=60
        )
        
        assert archiver.retention_days == 60
        assert archiver.archive_path.exists()
    
    def test_archive_signal(self, archiver, sample_signal):
        """测试归档单个信号"""
        result = archiver.archive_signal(sample_signal)
        
        assert result is True
        assert len(archiver.get_today_signals()) == 1
    
    def test_archive_signals_batch(self, archiver):
        """测试批量归档信号"""
        signals = [
            RadarSignal(
                signal_id=f"sig_{i}",
                symbol="000001.SZ",
                signal_type=SignalType.BUY,
                source=SignalSource.FACTOR
            )
            for i in range(5)
        ]
        
        count = archiver.archive_signals(signals)
        
        assert count == 5
        assert len(archiver.get_today_signals()) == 5
    
    def test_flush_to_disk(self, archiver, sample_signal):
        """测试写入磁盘"""
        archiver.archive_signal(sample_signal)
        
        result = archiver.flush_to_disk()
        
        assert result is True
        assert len(archiver.get_today_signals()) == 0
        
        # 检查文件是否创建
        today_str = date.today().strftime("%Y%m%d")
        file_path = archiver.archive_path / f"signals_{today_str}.json"
        assert file_path.exists()
    
    def test_query_signals_from_cache(self, archiver, sample_signal):
        """测试从缓存查询信号"""
        archiver.archive_signal(sample_signal)
        
        signals = archiver.query_signals(symbol="000001.SZ")
        
        assert len(signals) == 1
        assert signals[0].symbol == "000001.SZ"
    
    def test_query_signals_from_disk(self, archiver, sample_signal):
        """测试从磁盘查询信号"""
        archiver.archive_signal(sample_signal)
        archiver.flush_to_disk()
        
        signals = archiver.query_signals(symbol="000001.SZ")
        
        assert len(signals) == 1
    
    def test_query_signals_by_type(self, archiver):
        """测试按类型查询"""
        signals = [
            RadarSignal(
                signal_id="sig_1",
                symbol="000001.SZ",
                signal_type=SignalType.BUY,
                source=SignalSource.FACTOR
            ),
            RadarSignal(
                signal_id="sig_2",
                symbol="000001.SZ",
                signal_type=SignalType.SELL,
                source=SignalSource.FACTOR
            )
        ]
        
        archiver.archive_signals(signals)
        
        buy_signals = archiver.query_signals(signal_type=SignalType.BUY)
        
        assert len(buy_signals) == 1
        assert buy_signals[0].signal_type == SignalType.BUY
    
    def test_query_signals_by_source(self, archiver):
        """测试按来源查询"""
        signals = [
            RadarSignal(
                signal_id="sig_1",
                symbol="000001.SZ",
                signal_type=SignalType.BUY,
                source=SignalSource.FACTOR
            ),
            RadarSignal(
                signal_id="sig_2",
                symbol="000001.SZ",
                signal_type=SignalType.BUY,
                source=SignalSource.SENTIMENT
            )
        ]
        
        archiver.archive_signals(signals)
        
        factor_signals = archiver.query_signals(source=SignalSource.FACTOR)
        
        assert len(factor_signals) == 1
        assert factor_signals[0].source == SignalSource.FACTOR
    
    def test_query_signals_with_limit(self, archiver):
        """测试限制查询数量"""
        signals = [
            RadarSignal(
                signal_id=f"sig_{i}",
                symbol="000001.SZ",
                signal_type=SignalType.BUY,
                source=SignalSource.FACTOR
            )
            for i in range(10)
        ]
        
        archiver.archive_signals(signals)
        
        result = archiver.query_signals(limit=5)
        
        assert len(result) == 5
    
    def test_get_today_signals(self, archiver, sample_signal):
        """测试获取今日信号"""
        archiver.archive_signal(sample_signal)
        
        signals = archiver.get_today_signals()
        
        assert len(signals) == 1
    
    def test_get_signal_count(self, archiver):
        """测试获取信号数量"""
        signals = [
            RadarSignal(
                signal_id=f"sig_{i}",
                symbol="000001.SZ",
                signal_type=SignalType.BUY,
                source=SignalSource.FACTOR
            )
            for i in range(5)
        ]
        
        archiver.archive_signals(signals)
        
        count = archiver.get_signal_count()
        
        assert count == 5
    
    def test_get_signal_count_by_symbol(self, archiver):
        """测试按标的获取信号数量"""
        signals = [
            RadarSignal(
                signal_id="sig_1",
                symbol="000001.SZ",
                signal_type=SignalType.BUY,
                source=SignalSource.FACTOR
            ),
            RadarSignal(
                signal_id="sig_2",
                symbol="600000.SH",
                signal_type=SignalType.BUY,
                source=SignalSource.FACTOR
            )
        ]
        
        archiver.archive_signals(signals)
        
        count = archiver.get_signal_count(symbol="000001.SZ")
        
        assert count == 1
    
    def test_get_statistics(self, archiver):
        """测试获取统计"""
        signals = [
            RadarSignal(
                signal_id="sig_1",
                symbol="000001.SZ",
                signal_type=SignalType.BUY,
                source=SignalSource.FACTOR
            ),
            RadarSignal(
                signal_id="sig_2",
                symbol="000001.SZ",
                signal_type=SignalType.SELL,
                source=SignalSource.SENTIMENT
            )
        ]
        
        archiver.archive_signals(signals)
        
        stats = archiver.get_statistics()
        
        assert stats.total_signals == 2
        assert "买入" in stats.signals_by_type
        assert "因子" in stats.signals_by_source
    
    def test_clear_cache(self, archiver, sample_signal):
        """测试清空缓存"""
        archiver.archive_signal(sample_signal)
        archiver.clear_cache()
        
        assert len(archiver.get_today_signals()) == 0
    
    def test_cleanup_old_files(self, archiver, temp_dir):
        """测试清理过期文件"""
        # 创建一个旧文件
        old_date = (date.today() - timedelta(days=100)).strftime("%Y%m%d")
        old_file = Path(temp_dir) / f"signals_{old_date}.json"
        old_file.write_text("[]")
        
        deleted = archiver.cleanup_old_files()
        
        assert deleted == 1
        assert not old_file.exists()


class TestArchiveStats:
    """ArchiveStats统计类测试"""
    
    def test_stats_creation(self):
        """测试统计创建"""
        stats = ArchiveStats(
            total_signals=100,
            signals_by_type={"买入": 60, "卖出": 40},
            file_count=10,
            total_size_mb=5.5
        )
        
        assert stats.total_signals == 100
        assert stats.file_count == 10
    
    def test_stats_to_dict(self):
        """测试统计转字典"""
        stats = ArchiveStats(total_signals=50)
        
        result = stats.to_dict()
        
        assert result["total_signals"] == 50


class TestRadarArchiverAsync:
    """异步功能测试"""
    
    @pytest.fixture
    def temp_dir(self):
        """创建临时目录"""
        temp_path = tempfile.mkdtemp()
        yield temp_path
        if Path(temp_path).exists():
            shutil.rmtree(temp_path)
    
    @pytest.fixture
    def archiver(self, temp_dir):
        """创建归档器实例"""
        return RadarArchiver(archive_path=temp_dir)
    
    @pytest.mark.asyncio
    async def test_flush_to_disk_async(self, archiver):
        """测试异步写入磁盘"""
        signal = RadarSignal(
            signal_id="sig_001",
            symbol="000001.SZ",
            signal_type=SignalType.BUY,
            source=SignalSource.FACTOR
        )
        
        archiver.archive_signal(signal)
        result = await archiver.flush_to_disk_async()
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_query_signals_async(self, archiver):
        """测试异步查询"""
        signal = RadarSignal(
            signal_id="sig_001",
            symbol="000001.SZ",
            signal_type=SignalType.BUY,
            source=SignalSource.FACTOR
        )
        
        archiver.archive_signal(signal)
        signals = await archiver.query_signals_async(symbol="000001.SZ")
        
        assert len(signals) == 1
