"""单元测试 - 数据异常类

白皮书依据: 第三章 3.2 基础设施与数据治理
需求: 1.1-1.10, 2.1-2.10, 3.1-3.10
测试覆盖: data_exceptions.py

测试内容:
- 基础异常类
- 数据不可用异常
- 数据获取异常
- 数据质量异常
- 认证异常
- 速率限制异常
"""

import pytest
from src.infra.data_exceptions import (
    DataProbeException,
    DataUnavailableError,
    DataFetchError,
    DataQualityError,
    AuthenticationError,
    RateLimitError
)


class TestDataProbeException:
    """测试基础异常类"""
    
    def test_basic_exception(self):
        """测试基础异常"""
        exc = DataProbeException("测试错误")
        assert str(exc) == "测试错误"
        assert exc.message == "测试错误"
        assert exc.source_id is None
        assert exc.details == {}
    
    def test_exception_with_source_id(self):
        """测试带数据源ID的异常"""
        exc = DataProbeException("测试错误", source_id="test_source")
        assert str(exc) == "[test_source] 测试错误"
        assert exc.source_id == "test_source"
    
    def test_exception_with_details(self):
        """测试带详细信息的异常"""
        details = {"key1": "value1", "key2": 123}
        exc = DataProbeException("测试错误", details=details)
        assert "key1=value1" in str(exc)
        assert "key2=123" in str(exc)
        assert exc.details == details
    
    def test_exception_with_all_params(self):
        """测试带所有参数的异常"""
        details = {"error_code": 500}
        exc = DataProbeException(
            "测试错误",
            source_id="test_source",
            details=details
        )
        assert "[test_source]" in str(exc)
        assert "测试错误" in str(exc)
        assert "error_code=500" in str(exc)


class TestDataUnavailableError:
    """测试数据不可用异常"""
    
    def test_default_message(self):
        """测试默认错误信息"""
        exc = DataUnavailableError()
        assert "数据不可用" in str(exc)
    
    def test_custom_message(self):
        """测试自定义错误信息"""
        exc = DataUnavailableError("所有市场数据源都不可用")
        assert "所有市场数据源都不可用" in str(exc)
    
    def test_with_source_id(self):
        """测试带数据源ID"""
        exc = DataUnavailableError(
            "数据源不可用",
            source_id="akshare"
        )
        assert "[akshare]" in str(exc)
    
    def test_with_details(self):
        """测试带详细信息"""
        details = {
            "tried_sources": ["akshare", "yahoo_finance", "alpha_vantage"],
            "last_error": "连接超时"
        }
        exc = DataUnavailableError(
            "所有数据源都不可用",
            details=details
        )
        assert "tried_sources" in str(exc)
        assert "last_error" in str(exc)
    
    def test_inheritance(self):
        """测试继承关系"""
        exc = DataUnavailableError()
        assert isinstance(exc, DataProbeException)
        assert isinstance(exc, Exception)


class TestDataFetchError:
    """测试数据获取异常"""
    
    def test_default_message(self):
        """测试默认错误信息"""
        exc = DataFetchError()
        assert "数据获取失败" in str(exc)
    
    def test_custom_message(self):
        """测试自定义错误信息"""
        exc = DataFetchError("API请求超时")
        assert "API请求超时" in str(exc)
    
    def test_with_api_details(self):
        """测试带API详细信息"""
        details = {
            "endpoint": "https://akshare.akfamily.xyz/stock_zh_a_hist",
            "status_code": 500,
            "timeout": 30
        }
        exc = DataFetchError(
            "API请求失败",
            source_id="akshare",
            details=details
        )
        assert "endpoint" in str(exc)
        assert "status_code" in str(exc)
        assert "timeout" in str(exc)
    
    def test_inheritance(self):
        """测试继承关系"""
        exc = DataFetchError()
        assert isinstance(exc, DataProbeException)


class TestDataQualityError:
    """测试数据质量异常"""
    
    def test_default_message(self):
        """测试默认错误信息"""
        exc = DataQualityError()
        assert "数据质量不达标" in str(exc)
    
    def test_custom_message(self):
        """测试自定义错误信息"""
        exc = DataQualityError("数据质量评分过低")
        assert "数据质量评分过低" in str(exc)
    
    def test_with_quality_metrics(self):
        """测试带质量指标"""
        details = {
            "quality_score": 0.45,
            "threshold": 0.50,
            "completeness": 0.60,
            "timeliness": 0.40,
            "accuracy": 0.50,
            "consistency": 0.30
        }
        exc = DataQualityError(
            "数据质量不达标",
            source_id="akshare",
            details=details
        )
        assert "quality_score" in str(exc)
        assert "threshold" in str(exc)
        assert "completeness" in str(exc)
    
    def test_inheritance(self):
        """测试继承关系"""
        exc = DataQualityError()
        assert isinstance(exc, DataProbeException)


class TestAuthenticationError:
    """测试认证异常"""
    
    def test_default_message(self):
        """测试默认错误信息"""
        exc = AuthenticationError()
        assert "认证失败" in str(exc)
    
    def test_custom_message(self):
        """测试自定义错误信息"""
        exc = AuthenticationError("API密钥无效")
        assert "API密钥无效" in str(exc)
    
    def test_with_auth_details(self):
        """测试带认证详细信息"""
        details = {
            "api_key": "****1234",
            "status_code": 401,
            "message": "Invalid API key"
        }
        exc = AuthenticationError(
            "认证失败",
            source_id="alpha_vantage",
            details=details
        )
        assert "api_key" in str(exc)
        assert "status_code" in str(exc)
    
    def test_inheritance(self):
        """测试继承关系"""
        exc = AuthenticationError()
        assert isinstance(exc, DataProbeException)


class TestRateLimitError:
    """测试速率限制异常"""
    
    def test_default_message(self):
        """测试默认错误信息"""
        exc = RateLimitError()
        assert "超过速率限制" in str(exc)
    
    def test_custom_message(self):
        """测试自定义错误信息"""
        exc = RateLimitError("超过API速率限制")
        assert "超过API速率限制" in str(exc)
    
    def test_with_rate_limit_details(self):
        """测试带速率限制详细信息"""
        details = {
            "rate_limit": 5,
            "current_rate": 10,
            "reset_time": "2026-01-21 15:30:00",
            "retry_after": 60
        }
        exc = RateLimitError(
            "超过速率限制",
            source_id="alpha_vantage",
            details=details
        )
        assert "rate_limit" in str(exc)
        assert "current_rate" in str(exc)
        assert "retry_after" in str(exc)
    
    def test_inheritance(self):
        """测试继承关系"""
        exc = RateLimitError()
        assert isinstance(exc, DataProbeException)


class TestExceptionRaising:
    """测试异常抛出和捕获"""
    
    def test_raise_and_catch_data_unavailable(self):
        """测试抛出和捕获数据不可用异常"""
        with pytest.raises(DataUnavailableError) as exc_info:
            raise DataUnavailableError("测试异常")
        
        assert "测试异常" in str(exc_info.value)
    
    def test_raise_and_catch_data_fetch(self):
        """测试抛出和捕获数据获取异常"""
        with pytest.raises(DataFetchError) as exc_info:
            raise DataFetchError("测试异常")
        
        assert "测试异常" in str(exc_info.value)
    
    def test_catch_base_exception(self):
        """测试捕获基础异常"""
        with pytest.raises(DataProbeException):
            raise DataUnavailableError("测试异常")
    
    def test_exception_chaining(self):
        """测试异常链"""
        try:
            try:
                raise ValueError("原始错误")
            except ValueError as e:
                raise DataFetchError("数据获取失败") from e
        except DataFetchError as exc:
            assert exc.__cause__ is not None
            assert isinstance(exc.__cause__, ValueError)
