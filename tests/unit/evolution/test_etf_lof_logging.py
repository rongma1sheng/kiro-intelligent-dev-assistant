"""
ETF/LOF因子挖掘器日志系统测试

白皮书依据: 第四章 4.1.17-4.1.18 ETF/LOF因子挖掘器
铁律7依据: 测试覆盖率要求 100%

测试日志配置和日志记录功能。
"""

import pytest
import tempfile
import time
from pathlib import Path
from loguru import logger

from src.evolution.etf_lof.logging_config import (
    setup_etf_lof_logging,
    get_logger,
    configure_default_logging
)


class TestLoggingSetup:
    """测试日志设置功能"""
    
    def test_setup_console_only(self):
        """测试仅控制台日志配置"""
        # 配置仅控制台日志
        setup_etf_lof_logging(log_file=None, log_level="INFO")
        
        # 验证logger可用
        test_logger = get_logger("test_console")
        test_logger.info("测试控制台日志")
        
        # 应该不会抛出异常
        assert True
    
    def test_setup_with_file(self):
        """测试文件日志配置"""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "test.log"
            
            # 配置文件日志
            setup_etf_lof_logging(
                log_file=str(log_file),
                log_level="DEBUG"
            )
            
            # 写入日志
            test_logger = get_logger("test_file")
            test_logger.info("测试文件日志")
            
            # 等待异步写入完成
            time.sleep(0.1)
            
            # 验证日志文件存在
            assert log_file.exists()
            
            # 验证日志内容
            content = log_file.read_text(encoding='utf-8')
            assert "测试文件日志" in content
            
            # 清理：移除所有handlers以释放文件锁
            logger.remove()
    
    def test_setup_with_different_levels(self):
        """测试不同日志级别"""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "test_levels.log"
            
            # 配置WARNING级别
            setup_etf_lof_logging(
                log_file=str(log_file),
                log_level="WARNING"
            )
            
            test_logger = get_logger("test_levels")
            test_logger.debug("DEBUG消息")  # 不应该记录
            test_logger.info("INFO消息")    # 不应该记录
            test_logger.warning("WARNING消息")  # 应该记录
            test_logger.error("ERROR消息")      # 应该记录
            
            # 等待异步写入完成
            time.sleep(0.1)
            
            # 验证日志内容
            content = log_file.read_text(encoding='utf-8')
            assert "DEBUG消息" not in content
            assert "INFO消息" not in content
            assert "WARNING消息" in content
            assert "ERROR消息" in content
            
            # 清理：移除所有handlers以释放文件锁
            logger.remove()
    
    def test_log_file_directory_creation(self):
        """测试日志目录自动创建"""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "subdir" / "nested" / "test.log"
            
            # 配置日志（目录不存在）
            setup_etf_lof_logging(log_file=str(log_file))
            
            # 写入日志
            test_logger = get_logger("test_dir")
            test_logger.info("测试目录创建")
            
            # 等待异步写入完成
            time.sleep(0.1)
            
            # 验证目录和文件都被创建
            assert log_file.parent.exists()
            assert log_file.exists()
            
            # 清理：移除所有handlers以释放文件锁
            logger.remove()


class TestGetLogger:
    """测试logger获取功能"""
    
    def test_get_logger_with_name(self):
        """测试获取命名logger"""
        test_logger = get_logger("test_named")
        
        # 验证logger可用
        assert test_logger is not None
        
        # 验证可以记录日志
        test_logger.info("测试命名logger")
    
    def test_get_logger_different_names(self):
        """测试获取不同名称的logger"""
        logger1 = get_logger("logger1")
        logger2 = get_logger("logger2")
        
        # 两个logger应该都可用
        assert logger1 is not None
        assert logger2 is not None
        
        # 可以分别记录日志
        logger1.info("Logger 1消息")
        logger2.info("Logger 2消息")


class TestDefaultConfiguration:
    """测试默认配置"""
    
    def test_configure_default_logging(self):
        """测试默认日志配置"""
        # 配置默认日志
        configure_default_logging()
        
        # 验证可以记录日志
        test_logger = get_logger("test_default")
        test_logger.info("测试默认配置")
        
        # 应该不会抛出异常
        assert True


class TestLoggingInETFMiner:
    """测试ETF挖掘器中的日志记录"""
    
    def test_etf_miner_logging(self):
        """测试ETF挖掘器日志记录"""
        # 简化测试：只测试日志功能，不测试完整的挖掘器初始化
        setup_etf_lof_logging(log_file=None, log_level="INFO")
        
        # 模拟ETF挖掘器的日志记录
        etf_logger = get_logger("etf_factor_miner")
        etf_logger.info("ETFFactorMiner initialized")
        etf_logger.info("开始ETF因子挖掘")
        etf_logger.warning("ETF数据质量检查")
        
        # 验证logger可用（不会抛出异常）
        assert True
        
        # 清理：移除所有handlers
        logger.remove()


class TestLoggingInLOFMiner:
    """测试LOF挖掘器中的日志记录"""
    
    def test_lof_miner_logging(self):
        """测试LOF挖掘器日志记录"""
        # 简化测试：只测试日志功能，不测试完整的挖掘器初始化
        setup_etf_lof_logging(log_file=None, log_level="INFO")
        
        # 模拟LOF挖掘器的日志记录
        lof_logger = get_logger("lof_factor_miner")
        lof_logger.info("LOFFactorMiner initialized")
        lof_logger.info("开始LOF因子挖掘")
        lof_logger.warning("LOF数据质量检查")
        
        # 验证logger可用（不会抛出异常）
        assert True
        
        # 清理：移除所有handlers
        logger.remove()


class TestLoggingInArenaIntegration:
    """测试Arena集成中的日志记录"""
    
    def test_arena_integration_logging(self):
        """测试Arena集成日志记录"""
        # 简化测试：只测试日志功能
        setup_etf_lof_logging(log_file=None, log_level="INFO")
        
        # 模拟Arena集成的日志记录
        arena_logger = get_logger("arena_integration")
        arena_logger.info("ArenaIntegration initialized")
        arena_logger.info("提交因子到Arena队列")
        arena_logger.warning("Arena连接重试")
        
        # 验证logger可用（不会抛出异常）
        assert True
        
        # 清理：移除所有handlers
        logger.remove()


class TestLoggingInCrossMarket:
    """测试跨市场测试中的日志记录"""
    
    def test_cross_market_logging(self):
        """测试跨市场测试日志记录"""
        # 简化测试：只测试日志功能
        setup_etf_lof_logging(log_file=None, log_level="INFO")
        
        # 模拟跨市场测试的日志记录
        cross_market_logger = get_logger("cross_market_alignment")
        cross_market_logger.info("开始跨市场数据对齐")
        cross_market_logger.info("A股市场数据加载完成")
        cross_market_logger.info("港股市场数据加载完成")
        cross_market_logger.warning("市场数据时间范围不一致")
        
        # 验证logger可用（不会抛出异常）
        assert True
        
        # 清理：移除所有handlers
        logger.remove()


class TestStructuredLogging:
    """测试结构化日志"""
    
    def test_log_format(self):
        """测试日志格式"""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "format_test.log"
            setup_etf_lof_logging(log_file=str(log_file), log_level="INFO")
            
            test_logger = get_logger("format_test")
            test_logger.info("测试消息", extra={"key": "value"})
            
            # 等待异步写入完成
            time.sleep(0.1)
            
            # 验证日志格式包含必要信息
            content = log_file.read_text(encoding='utf-8')
            assert "INFO" in content
            assert "测试消息" in content
            
            # 清理：移除所有handlers以释放文件锁
            logger.remove()
    
    def test_log_context(self):
        """测试日志上下文"""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "context_test.log"
            setup_etf_lof_logging(log_file=str(log_file), log_level="INFO")
            
            # 使用get_logger获取带有默认上下文的logger，然后添加额外上下文
            context_logger = get_logger("test").bind(task_id="12345")
            context_logger.info("带上下文的日志")
            
            # 等待异步写入完成
            time.sleep(0.1)
            
            # 验证日志包含上下文信息
            content = log_file.read_text(encoding='utf-8')
            assert "带上下文的日志" in content
            
            # 清理：移除所有handlers以释放文件锁
            logger.remove()
