"""
MIA系统异常类测试

测试目标: src/base/exceptions.py
覆盖率目标: 100%
测试策略: 全面测试所有异常类的实例化、继承关系和异常处理
"""

import sys

import pytest

# 添加src路径
sys.path.insert(0, "src")

from base.exceptions import (
    ArenaTestError,
    CertificationError,
    DataDownloadError,
    DataError,
    MIABaseException,
    ResourceError,
    ValidationError,
)


class TestMIABaseException:
    """测试MIA基础异常类"""

    def test_mia_base_exception_creation(self):
        """测试MIA基础异常创建"""
        # 测试无参数创建
        exc = MIABaseException()
        assert isinstance(exc, Exception)
        assert isinstance(exc, MIABaseException)
        assert str(exc) == ""

    def test_mia_base_exception_with_message(self):
        """测试带消息的MIA基础异常"""
        message = "测试异常消息"
        exc = MIABaseException(message)
        assert str(exc) == message
        assert exc.args == (message,)

    def test_mia_base_exception_with_multiple_args(self):
        """测试多参数MIA基础异常"""
        args = ("错误代码", "错误消息", 500)
        exc = MIABaseException(*args)
        assert exc.args == args
        assert str(exc) == "('错误代码', '错误消息', 500)"

    def test_mia_base_exception_inheritance(self):
        """测试MIA基础异常继承关系"""
        exc = MIABaseException("测试")
        assert isinstance(exc, Exception)
        assert issubclass(MIABaseException, Exception)

    def test_mia_base_exception_raise_and_catch(self):
        """测试MIA基础异常抛出和捕获"""
        with pytest.raises(MIABaseException) as exc_info:
            raise MIABaseException("测试异常")

        assert str(exc_info.value) == "测试异常"
        assert isinstance(exc_info.value, MIABaseException)

    def test_mia_base_exception_repr(self):
        """测试MIA基础异常字符串表示"""
        exc = MIABaseException("测试消息")
        repr_str = repr(exc)
        assert "MIABaseException" in repr_str
        assert "测试消息" in repr_str


class TestValidationError:
    """测试验证错误异常类"""

    def test_validation_error_creation(self):
        """测试验证错误创建"""
        exc = ValidationError()
        assert isinstance(exc, ValidationError)
        assert isinstance(exc, MIABaseException)
        assert isinstance(exc, Exception)

    def test_validation_error_with_message(self):
        """测试带消息的验证错误"""
        message = "字段验证失败"
        exc = ValidationError(message)
        assert str(exc) == message

    def test_validation_error_inheritance(self):
        """测试验证错误继承关系"""
        assert issubclass(ValidationError, MIABaseException)
        assert issubclass(ValidationError, Exception)

    def test_validation_error_raise_and_catch(self):
        """测试验证错误抛出和捕获"""
        with pytest.raises(ValidationError) as exc_info:
            raise ValidationError("参数验证失败")

        assert str(exc_info.value) == "参数验证失败"

        # 测试作为MIABaseException捕获
        with pytest.raises(MIABaseException):
            raise ValidationError("基类捕获测试")

    def test_validation_error_with_field_info(self):
        """测试带字段信息的验证错误"""
        field_name = "username"
        error_msg = f"字段 {field_name} 不能为空"
        exc = ValidationError(error_msg)
        assert field_name in str(exc)


class TestArenaTestError:
    """测试Arena测试错误异常类"""

    def test_arena_test_error_creation(self):
        """测试Arena测试错误创建"""
        exc = ArenaTestError()
        assert isinstance(exc, ArenaTestError)
        assert isinstance(exc, MIABaseException)

    def test_arena_test_error_with_test_info(self):
        """测试带测试信息的Arena错误"""
        test_name = "momentum_strategy_test"
        error_msg = f"Arena测试失败: {test_name}"
        exc = ArenaTestError(error_msg)
        assert test_name in str(exc)

    def test_arena_test_error_inheritance(self):
        """测试Arena测试错误继承关系"""
        assert issubclass(ArenaTestError, MIABaseException)

    def test_arena_test_error_raise_and_catch(self):
        """测试Arena测试错误抛出和捕获"""
        with pytest.raises(ArenaTestError) as exc_info:
            raise ArenaTestError("策略测试超时")

        assert "策略测试超时" in str(exc_info.value)


class TestCertificationError:
    """测试认证错误异常类"""

    def test_certification_error_creation(self):
        """测试认证错误创建"""
        exc = CertificationError()
        assert isinstance(exc, CertificationError)
        assert isinstance(exc, MIABaseException)

    def test_certification_error_with_cert_info(self):
        """测试带认证信息的认证错误"""
        cert_level = "Z2H_TIER_1"
        error_msg = f"认证失败: {cert_level}"
        exc = CertificationError(error_msg)
        assert cert_level in str(exc)

    def test_certification_error_inheritance(self):
        """测试认证错误继承关系"""
        assert issubclass(CertificationError, MIABaseException)

    def test_certification_error_raise_and_catch(self):
        """测试认证错误抛出和捕获"""
        with pytest.raises(CertificationError) as exc_info:
            raise CertificationError("Z2H认证失败")

        assert "Z2H认证失败" in str(exc_info.value)


class TestDataError:
    """测试数据错误异常类"""

    def test_data_error_creation(self):
        """测试数据错误创建"""
        exc = DataError()
        assert isinstance(exc, DataError)
        assert isinstance(exc, MIABaseException)

    def test_data_error_with_data_info(self):
        """测试带数据信息的数据错误"""
        data_source = "market_data"
        error_msg = f"数据错误: {data_source} 数据不完整"
        exc = DataError(error_msg)
        assert data_source in str(exc)

    def test_data_error_inheritance(self):
        """测试数据错误继承关系"""
        assert issubclass(DataError, MIABaseException)

    def test_data_error_raise_and_catch(self):
        """测试数据错误抛出和捕获"""
        with pytest.raises(DataError) as exc_info:
            raise DataError("数据格式错误")

        assert "数据格式错误" in str(exc_info.value)


class TestResourceError:
    """测试资源错误异常类"""

    def test_resource_error_creation(self):
        """测试资源错误创建"""
        exc = ResourceError()
        assert isinstance(exc, ResourceError)
        assert isinstance(exc, MIABaseException)

    def test_resource_error_with_resource_info(self):
        """测试带资源信息的资源错误"""
        resource_type = "GPU"
        error_msg = f"资源不足: {resource_type} 内存不够"
        exc = ResourceError(error_msg)
        assert resource_type in str(exc)

    def test_resource_error_inheritance(self):
        """测试资源错误继承关系"""
        assert issubclass(ResourceError, MIABaseException)

    def test_resource_error_raise_and_catch(self):
        """测试资源错误抛出和捕获"""
        with pytest.raises(ResourceError) as exc_info:
            raise ResourceError("内存不足")

        assert "内存不足" in str(exc_info.value)


class TestDataDownloadError:
    """测试数据下载错误异常类"""

    def test_data_download_error_creation(self):
        """测试数据下载错误创建"""
        exc = DataDownloadError()
        assert isinstance(exc, DataDownloadError)
        assert isinstance(exc, MIABaseException)

    def test_data_download_error_with_url_info(self):
        """测试带URL信息的数据下载错误"""
        url = "https://api.example.com/data"
        error_msg = f"数据下载失败: {url}"
        exc = DataDownloadError(error_msg)
        assert url in str(exc)

    def test_data_download_error_inheritance(self):
        """测试数据下载错误继承关系"""
        assert issubclass(DataDownloadError, MIABaseException)

    def test_data_download_error_raise_and_catch(self):
        """测试数据下载错误抛出和捕获"""
        with pytest.raises(DataDownloadError) as exc_info:
            raise DataDownloadError("网络连接超时")

        assert "网络连接超时" in str(exc_info.value)


class TestExceptionHierarchy:
    """测试异常层次结构"""

    def test_all_exceptions_inherit_from_base(self):
        """测试所有异常都继承自MIA基础异常"""
        exception_classes = [
            ValidationError,
            ArenaTestError,
            CertificationError,
            DataError,
            ResourceError,
            DataDownloadError,
        ]

        for exc_class in exception_classes:
            assert issubclass(exc_class, MIABaseException)
            assert issubclass(exc_class, Exception)

    def test_exception_mro(self):
        """测试异常方法解析顺序"""
        # 测试ValidationError的MRO
        mro = ValidationError.__mro__
        assert ValidationError in mro
        assert MIABaseException in mro
        assert Exception in mro
        assert object in mro

    def test_catch_all_with_base_exception(self):
        """测试使用基础异常捕获所有MIA异常"""
        exception_classes = [
            ValidationError,
            ArenaTestError,
            CertificationError,
            DataError,
            ResourceError,
            DataDownloadError,
        ]

        for exc_class in exception_classes:
            with pytest.raises(MIABaseException):
                raise exc_class("测试消息")


class TestExceptionUsageScenarios:
    """测试异常使用场景"""

    def test_nested_exception_handling(self):
        """测试嵌套异常处理"""

        def inner_function():
            raise ValidationError("内部验证失败")

        def outer_function():
            try:
                inner_function()
            except ValidationError as e:
                raise DataError(f"数据处理失败: {str(e)}") from e

        with pytest.raises(DataError) as exc_info:
            outer_function()

        assert "数据处理失败" in str(exc_info.value)
        assert "内部验证失败" in str(exc_info.value)

    def test_exception_chaining(self):
        """测试异常链"""
        original_error = ValueError("原始错误")

        try:
            raise original_error
        except ValueError as e:
            mia_error = MIABaseException("MIA处理错误")

            with pytest.raises(MIABaseException) as exc_info:
                raise mia_error from e

            assert exc_info.value.__cause__ is original_error

    def test_exception_with_context_manager(self):
        """测试异常与上下文管理器"""

        class TestContextManager:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc_val, exc_tb):
                if exc_type is ValidationError:
                    # 处理ValidationError
                    return True  # 抑制异常
                return False  # 不抑制其他异常

        # 测试ValidationError被抑制
        with TestContextManager():
            raise ValidationError("被抑制的错误")

        # 测试其他异常不被抑制
        with pytest.raises(DataError):
            with TestContextManager():
                raise DataError("不被抑制的错误")

    def test_exception_attributes(self):
        """测试异常属性"""
        error_code = "E001"
        error_msg = "系统错误"

        exc = MIABaseException(error_code, error_msg)

        # 测试args属性
        assert exc.args == (error_code, error_msg)

        # 测试自定义属性
        exc.error_code = error_code
        exc.timestamp = "2026-02-01T13:35:00"

        assert exc.error_code == error_code
        assert hasattr(exc, "timestamp")

    def test_exception_equality(self):
        """测试异常相等性"""
        exc1 = ValidationError("测试错误")
        exc2 = ValidationError("测试错误")
        exc3 = ValidationError("不同错误")

        # 异常实例不相等（即使消息相同）
        assert exc1 is not exc2
        assert exc1.args == exc2.args
        assert exc1.args != exc3.args


class TestExceptionDocumentation:
    """测试异常文档和元数据"""

    def test_exception_docstrings(self):
        """测试异常类文档字符串"""
        assert MIABaseException.__doc__ == "MIA系统基础异常"
        assert ValidationError.__doc__ == "验证错误"
        assert ArenaTestError.__doc__ == "Arena测试错误"
        assert CertificationError.__doc__ == "认证错误"
        assert DataError.__doc__ == "数据错误"
        assert ResourceError.__doc__ == "资源错误"
        assert DataDownloadError.__doc__ == "数据下载错误"

    def test_exception_module_info(self):
        """测试异常模块信息"""
        assert MIABaseException.__module__ == "base.exceptions"
        assert ValidationError.__module__ == "base.exceptions"

    def test_exception_class_names(self):
        """测试异常类名"""
        assert MIABaseException.__name__ == "MIABaseException"
        assert ValidationError.__name__ == "ValidationError"
        assert ArenaTestError.__name__ == "ArenaTestError"
        assert CertificationError.__name__ == "CertificationError"
        assert DataError.__name__ == "DataError"
        assert ResourceError.__name__ == "ResourceError"
        assert DataDownloadError.__name__ == "DataDownloadError"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
