"""
数据预热器单元测试

白皮书依据: 第一章 1.5.1 战备态任务调度
测试范围: DataPreheater的数据预加载和因子预计算功能
"""

import pytest
import tempfile
import shutil
from datetime import date
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.infra.data_preheater import (
    DataPreheater,
    PreheatConfig,
    PreheatResult,
    PreheatStatus,
    DataType
)


class TestPreheatConfig:
    """PreheatConfig配置类测试"""
    
    def test_default_config(self):
        """测试默认配置"""
        config = PreheatConfig()
        
        assert config.lookback_days == 60
        assert "1d" in config.bar_types
        assert config.precompute_factors is True
        assert config.cache_size_mb == 1024
    
    def test_custom_config(self):
        """测试自定义配置"""
        config = PreheatConfig(
            symbols=["000001.SZ", "600000.SH"],
            lookback_days=30,
            bar_types=["1d"],
            precompute_factors=False
        )
        
        assert len(config.symbols) == 2
        assert config.lookback_days == 30
        assert config.precompute_factors is False


class TestPreheatResult:
    """PreheatResult结果类测试"""
    
    def test_success_result(self):
        """测试成功结果"""
        result = PreheatResult(
            success=True,
            symbols_loaded=10,
            bars_loaded=1000,
            factors_computed=60,
            duration=5.5,
            memory_used_mb=50.0
        )
        
        assert result.success is True
        assert result.symbols_loaded == 10
        assert result.bars_loaded == 1000
    
    def test_failure_result(self):
        """测试失败结果"""
        result = PreheatResult(
            success=False,
            errors=["加载失败"]
        )
        
        assert result.success is False
        assert len(result.errors) == 1
    
    def test_to_dict(self):
        """测试转换为字典"""
        result = PreheatResult(
            success=True,
            symbols_loaded=5
        )
        
        result_dict = result.to_dict()
        
        assert result_dict["success"] is True
        assert result_dict["symbols_loaded"] == 5


class TestPreheatStatus:
    """PreheatStatus枚举测试"""
    
    def test_status_values(self):
        """测试状态枚举值"""
        assert PreheatStatus.IDLE.value == "空闲"
        assert PreheatStatus.LOADING.value == "加载中"
        assert PreheatStatus.COMPUTING.value == "计算中"
        assert PreheatStatus.READY.value == "就绪"
        assert PreheatStatus.ERROR.value == "错误"


class TestDataPreheater:
    """DataPreheater预热器测试"""
    
    @pytest.fixture
    def preheater(self):
        """创建预热器实例"""
        config = PreheatConfig(
            lookback_days=10,
            precompute_factors=True
        )
        return DataPreheater(config=config)
    
    def test_init_default(self):
        """测试默认初始化"""
        preheater = DataPreheater()
        
        assert preheater.status == PreheatStatus.IDLE
        assert preheater.config.lookback_days == 60
    
    def test_init_custom_config(self):
        """测试自定义配置初始化"""
        config = PreheatConfig(lookback_days=30)
        preheater = DataPreheater(config=config)
        
        assert preheater.config.lookback_days == 30
    
    def test_preheat_empty_symbols(self, preheater):
        """测试空标的预热"""
        result = preheater.preheat([])
        
        assert result.success is True
        assert result.symbols_loaded == 0
    
    def test_preheat_single_symbol(self, preheater):
        """测试单个标的预热"""
        result = preheater.preheat(["000001.SZ"])
        
        assert result.success is True
        assert result.symbols_loaded == 1
        assert result.bars_loaded > 0
    
    def test_preheat_multiple_symbols(self, preheater):
        """测试多个标的预热"""
        symbols = ["000001.SZ", "600000.SH", "000002.SZ"]
        result = preheater.preheat(symbols)
        
        assert result.success is True
        assert result.symbols_loaded == 3
    
    def test_preheat_with_factors(self, preheater):
        """测试预热包含因子计算"""
        result = preheater.preheat(["000001.SZ"])
        
        assert result.success is True
        assert result.factors_computed > 0
    
    def test_preheat_without_factors(self):
        """测试预热不计算因子"""
        config = PreheatConfig(
            lookback_days=10,
            precompute_factors=False
        )
        preheater = DataPreheater(config=config)
        
        result = preheater.preheat(["000001.SZ"])
        
        assert result.success is True
        assert result.factors_computed == 0
    
    def test_get_bars(self, preheater):
        """测试获取缓存K线"""
        preheater.preheat(["000001.SZ"])
        
        bars = preheater.get_bars("000001.SZ", "1d")
        
        assert bars is not None
        assert len(bars) > 0
    
    def test_get_bars_not_preheated(self, preheater):
        """测试获取未预热标的的K线"""
        bars = preheater.get_bars("999999.SZ", "1d")
        
        assert bars is None
    
    def test_get_factor(self, preheater):
        """测试获取缓存因子"""
        preheater.preheat(["000001.SZ"])
        
        momentum = preheater.get_factor("000001.SZ", "momentum_5")
        
        assert momentum is not None
    
    def test_get_all_factors(self, preheater):
        """测试获取所有因子"""
        preheater.preheat(["000001.SZ"])
        
        factors = preheater.get_all_factors("000001.SZ")
        
        assert "momentum_5" in factors
        assert "momentum_20" in factors
        assert "volatility_20" in factors
    
    def test_clear_cache(self, preheater):
        """测试清除缓存"""
        preheater.preheat(["000001.SZ"])
        preheater.clear_cache()
        
        assert preheater.status == PreheatStatus.IDLE
        assert preheater.get_bars("000001.SZ", "1d") is None
    
    def test_is_ready(self, preheater):
        """测试就绪状态检查"""
        assert preheater.is_ready() is False
        
        preheater.preheat(["000001.SZ"])
        
        assert preheater.is_ready() is True
    
    def test_get_status(self, preheater):
        """测试获取状态信息"""
        preheater.preheat(["000001.SZ"])
        
        status = preheater.get_status()
        
        assert status["status"] == "就绪"
        assert status["symbols_cached"] == 1
    
    def test_progress_callback(self, preheater):
        """测试进度回调"""
        progress_values = []
        
        def on_progress(progress, message):
            progress_values.append(progress)
        
        preheater.on_progress = on_progress
        preheater.preheat(["000001.SZ"])
        
        assert len(progress_values) > 0
        assert progress_values[-1] == 1.0
    
    def test_stop(self, preheater):
        """测试停止预热"""
        preheater.stop()
        
        # 停止后预热应该提前结束
        result = preheater.preheat(["000001.SZ", "600000.SH"])
        
        # 可能部分完成
        assert result is not None


class TestDataPreheaterAsync:
    """异步功能测试"""
    
    @pytest.fixture
    def preheater(self):
        """创建预热器实例"""
        config = PreheatConfig(lookback_days=5)
        return DataPreheater(config=config)
    
    @pytest.mark.asyncio
    async def test_preheat_async(self, preheater):
        """测试异步预热"""
        result = await preheater.preheat_async(["000001.SZ"])
        
        assert isinstance(result, PreheatResult)
        assert result.success is True
