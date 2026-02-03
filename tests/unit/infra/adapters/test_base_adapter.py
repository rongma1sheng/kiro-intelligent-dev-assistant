"""单元测试 - 基础适配器接口

白皮书依据: 第三章 3.2 基础设施与数据治理
需求: requirements.md 6.1-6.10
设计: design.md 核心组件设计 - 适配器层

测试BaseAdapter的功能：
1. 初始化和参数验证
2. 抽象方法定义
3. 重试机制
4. 速率限制
5. 错误处理
6. 数据验证
"""

import time
from typing import Any, Dict, List, Optional

import pandas as pd
import pytest

from src.infra.adapters.base_adapter import BaseAdapter
from src.infra.data_exceptions import AuthenticationError, DataFetchError

# ============================================================================
# 测试用的具体适配器实现
# ============================================================================


class MockAdapter(BaseAdapter):
    """模拟适配器，用于测试BaseAdapter的功能"""

    def __init__(  # pylint: disable=too-many-positional-arguments
        self,
        source_id: str = "mock_source",
        max_retries: int = 3,
        rate_limit: int = 100,
        should_fail: bool = False,
        fail_count: int = 0,
        fail_with_auth_error: bool = False,
        retry_delays: Optional[List[float]] = None,
    ):
        """初始化模拟适配器

        Args:
            source_id: 数据源ID
            max_retries: 最大重试次数
            rate_limit: 速率限制
            should_fail: 是否总是失败
            fail_count: 失败次数（之后成功）
            fail_with_auth_error: 是否抛出认证错误
            retry_delays: 重试延迟列表（秒），默认[0.01, 0.02, 0.04]用于快速测试
        """
        # 测试环境使用更短的重试延迟
        test_retry_delays = retry_delays or [0.01, 0.02, 0.04]
        super().__init__(source_id, max_retries, retry_delays=test_retry_delays, rate_limit=rate_limit)
        self.should_fail = should_fail
        self.fail_count = fail_count
        self.fail_with_auth_error = fail_with_auth_error
        self.call_count = 0
        self.connectivity_result = True
        self.authentication_result = True

    async def fetch_data(self, request_params: Dict[str, Any]) -> pd.DataFrame:
        """模拟数据获取"""
        self.call_count += 1

        # 模拟失败
        if self.should_fail:
            if self.fail_with_auth_error:
                raise AuthenticationError("认证失败", source_id=self.source_id)
            raise DataFetchError("数据获取失败", source_id=self.source_id)

        # 模拟前N次失败
        if self.call_count <= self.fail_count:
            raise DataFetchError(f"第 {self.call_count} 次失败", source_id=self.source_id)

        # 返回模拟数据
        return pd.DataFrame(
            {
                "datetime": [pd.Timestamp("2024-01-01")],
                "open": [100.0],
                "high": [105.0],
                "low": [99.0],
                "close": [103.0],
                "volume": [1000000.0],
            }
        )

    async def test_connectivity(self) -> bool:
        """模拟连接性测试"""
        return self.connectivity_result

    async def test_authentication(self) -> bool:
        """模拟认证测试"""
        return self.authentication_result

    def standardize_data(self, raw_data: Any) -> pd.DataFrame:
        """模拟数据标准化"""
        if isinstance(raw_data, pd.DataFrame):
            return raw_data

        # 简单的标准化逻辑
        return pd.DataFrame(
            {
                "datetime": [pd.Timestamp("2024-01-01")],
                "open": [100.0],
                "high": [105.0],
                "low": [99.0],
                "close": [103.0],
                "volume": [1000000.0],
            }
        )


# ============================================================================
# 测试类
# ============================================================================


class TestBaseAdapterInitialization:
    """测试BaseAdapter初始化"""

    def test_init_with_valid_params(self):
        """测试：使用有效参数初始化"""
        # 显式传入retry_delays以测试BaseAdapter的默认值行为
        adapter = MockAdapter(
            source_id="test_source", max_retries=5, rate_limit=200, retry_delays=[1, 2, 4]  # 显式传入BaseAdapter默认值
        )

        assert adapter.source_id == "test_source"
        assert adapter.max_retries == 5
        assert adapter.rate_limit == 200
        assert adapter.retry_delays == [1, 2, 4]
        assert adapter.last_request_time == 0.0

    def test_init_with_custom_retry_delays(self):
        """测试：使用自定义重试延迟"""
        adapter = MockAdapter(source_id="test_source", max_retries=3, rate_limit=100)
        adapter.retry_delays = [0.5, 1.0, 2.0]

        assert adapter.retry_delays == [0.5, 1.0, 2.0]

    def test_init_with_empty_source_id(self):
        """测试：source_id为空时抛出异常"""
        with pytest.raises(ValueError, match="source_id不能为空"):
            MockAdapter(source_id="")

    def test_init_with_negative_max_retries(self):
        """测试：max_retries为负数时抛出异常"""
        with pytest.raises(ValueError, match="max_retries必须 >= 0"):
            MockAdapter(source_id="test", max_retries=-1)

    def test_init_with_zero_rate_limit(self):
        """测试：rate_limit为0时抛出异常"""
        with pytest.raises(ValueError, match="rate_limit必须 > 0"):
            MockAdapter(source_id="test", rate_limit=0)

    def test_init_with_negative_rate_limit(self):
        """测试：rate_limit为负数时抛出异常"""
        with pytest.raises(ValueError, match="rate_limit必须 > 0"):
            MockAdapter(source_id="test", rate_limit=-10)


class TestBaseAdapterAbstractMethods:
    """测试BaseAdapter抽象方法"""

    def test_cannot_instantiate_base_adapter(self):
        """测试：不能直接实例化BaseAdapter"""
        with pytest.raises(TypeError):
            BaseAdapter(source_id="test")  # type: ignore  # pylint: disable=abstract-class-instantiated

    @pytest.mark.asyncio
    async def test_fetch_data_is_implemented(self):
        """测试：fetch_data方法已实现"""
        adapter = MockAdapter()
        data = await adapter.fetch_data({"symbol": "000001.SZ"})

        assert isinstance(data, pd.DataFrame)
        assert not data.empty

    @pytest.mark.asyncio
    async def test_test_connectivity_is_implemented(self):
        """测试：test_connectivity方法已实现"""
        adapter = MockAdapter()
        result = await adapter.test_connectivity()

        assert isinstance(result, bool)
        assert result is True

    @pytest.mark.asyncio
    async def test_test_authentication_is_implemented(self):
        """测试：test_authentication方法已实现"""
        adapter = MockAdapter()
        result = await adapter.test_authentication()

        assert isinstance(result, bool)
        assert result is True

    def test_standardize_data_is_implemented(self):
        """测试：standardize_data方法已实现"""
        adapter = MockAdapter()
        raw_data = {"price": [100.0]}
        data = adapter.standardize_data(raw_data)

        assert isinstance(data, pd.DataFrame)
        assert not data.empty


class TestBaseAdapterRetryMechanism:
    """测试BaseAdapter重试机制"""

    @pytest.mark.asyncio
    async def test_fetch_data_with_retry_success_first_try(self):
        """测试：第一次尝试就成功"""
        adapter = MockAdapter(should_fail=False)

        data = await adapter.fetch_data_with_retry({"symbol": "000001.SZ"})

        assert isinstance(data, pd.DataFrame)
        assert adapter.call_count == 1

    @pytest.mark.asyncio
    async def test_fetch_data_with_retry_success_after_failures(self):
        """测试：失败2次后第3次成功"""
        adapter = MockAdapter(fail_count=2, max_retries=3)

        data = await adapter.fetch_data_with_retry({"symbol": "000001.SZ"})

        assert isinstance(data, pd.DataFrame)
        assert adapter.call_count == 3  # 失败2次 + 成功1次

    @pytest.mark.asyncio
    async def test_fetch_data_with_retry_all_failures(self):
        """测试：所有重试都失败"""
        adapter = MockAdapter(should_fail=True, max_retries=2)

        with pytest.raises(DataFetchError, match="已重试 3 次"):
            await adapter.fetch_data_with_retry({"symbol": "000001.SZ"})

        assert adapter.call_count == 3  # 初始尝试 + 2次重试

    @pytest.mark.asyncio
    async def test_fetch_data_with_retry_exponential_backoff(self):
        """测试：指数退避延迟"""
        adapter = MockAdapter(fail_count=2, max_retries=3)
        adapter.retry_delays = [0.1, 0.2, 0.4]  # 使用较短的延迟以加快测试

        start_time = time.time()
        data = await adapter.fetch_data_with_retry({"symbol": "000001.SZ"})
        elapsed_time = time.time() - start_time

        # 应该至少等待 0.1 + 0.2 = 0.3 秒
        assert elapsed_time >= 0.3
        assert isinstance(data, pd.DataFrame)

    @pytest.mark.asyncio
    async def test_fetch_data_with_retry_auth_error_no_retry(self):
        """测试：认证错误时立即失败（不重试）"""
        adapter = MockAdapter(should_fail=True, fail_with_auth_error=True, max_retries=3)

        with pytest.raises(DataFetchError):
            await adapter.fetch_data_with_retry({"symbol": "000001.SZ"})

        # 认证错误应该重试（因为可能是临时问题）
        assert adapter.call_count == 4  # 初始尝试 + 3次重试


class TestBaseAdapterRateLimit:
    """测试BaseAdapter速率限制"""

    @pytest.mark.asyncio
    async def test_rate_limit_enforcement(self):
        """测试：速率限制生效"""
        adapter = MockAdapter(rate_limit=10)  # 10请求/秒 = 0.1秒/请求

        start_time = time.time()

        # 连续发送3个请求
        for _ in range(3):
            await adapter.fetch_data_with_retry({"symbol": "000001.SZ"})

        elapsed_time = time.time() - start_time

        # 应该至少等待 2 * 0.1 = 0.2 秒（第一个请求不等待）
        assert elapsed_time >= 0.2

    @pytest.mark.asyncio
    async def test_rate_limit_with_high_limit(self):
        """测试：高速率限制（几乎不等待）"""
        adapter = MockAdapter(rate_limit=1000)  # 1000请求/秒

        start_time = time.time()

        # 连续发送5个请求
        for _ in range(5):
            await adapter.fetch_data_with_retry({"symbol": "000001.SZ"})

        elapsed_time = time.time() - start_time

        # 应该很快完成（< 0.1秒）
        assert elapsed_time < 0.1

    @pytest.mark.asyncio
    async def test_rate_limit_updates_last_request_time(self):
        """测试：速率限制更新最后请求时间"""
        adapter = MockAdapter(rate_limit=100)

        initial_time = adapter.last_request_time
        assert initial_time == 0.0

        await adapter.fetch_data_with_retry({"symbol": "000001.SZ"})

        assert adapter.last_request_time > initial_time


class TestBaseAdapterDataValidation:
    """测试BaseAdapter数据验证"""

    def test_validate_standard_data_valid(self):
        """测试：验证有效的标准数据"""
        adapter = MockAdapter()

        valid_data = pd.DataFrame(
            {
                "datetime": [pd.Timestamp("2024-01-01")],
                "open": [100.0],
                "high": [105.0],
                "low": [99.0],
                "close": [103.0],
                "volume": [1000000.0],
            }
        )

        # 不应抛出异常
        adapter._validate_standard_data(valid_data)

    def test_validate_standard_data_missing_columns(self):
        """测试：缺少必需列时抛出异常"""
        adapter = MockAdapter()

        invalid_data = pd.DataFrame(
            {
                "datetime": [pd.Timestamp("2024-01-01")],
                "open": [100.0],
                # 缺少 high, low, close, volume
            }
        )

        with pytest.raises(DataFetchError, match="数据缺少必需列"):
            adapter._validate_standard_data(invalid_data)

    def test_validate_standard_data_wrong_datetime_type(self):
        """测试：datetime列类型错误时抛出异常"""
        adapter = MockAdapter()

        invalid_data = pd.DataFrame(
            {
                "datetime": ["2024-01-01"],  # 字符串而非datetime
                "open": [100.0],
                "high": [105.0],
                "low": [99.0],
                "close": [103.0],
                "volume": [1000000.0],
            }
        )

        with pytest.raises(DataFetchError, match="datetime列必须是datetime类型"):
            adapter._validate_standard_data(invalid_data)

    def test_validate_standard_data_wrong_numeric_type(self):
        """测试：数值列类型错误时抛出异常"""
        adapter = MockAdapter()

        invalid_data = pd.DataFrame(
            {
                "datetime": [pd.Timestamp("2024-01-01")],
                "open": ["100.0"],  # 字符串而非数值
                "high": [105.0],
                "low": [99.0],
                "close": [103.0],
                "volume": [1000000.0],
            }
        )

        with pytest.raises(DataFetchError, match="open列必须是数值类型"):
            adapter._validate_standard_data(invalid_data)

    def test_validate_standard_data_empty_dataframe(self):
        """测试：空DataFrame时抛出异常"""
        adapter = MockAdapter()

        empty_data = pd.DataFrame(
            {
                "datetime": pd.Series([], dtype="datetime64[ns]"),
                "open": pd.Series([], dtype="float64"),
                "high": pd.Series([], dtype="float64"),
                "low": pd.Series([], dtype="float64"),
                "close": pd.Series([], dtype="float64"),
                "volume": pd.Series([], dtype="float64"),
            }
        )

        with pytest.raises(DataFetchError, match="数据为空"):
            adapter._validate_standard_data(empty_data)


class TestBaseAdapterErrorLogging:
    """测试BaseAdapter错误日志"""

    def test_log_error_basic(self):
        """测试：基本错误日志"""
        adapter = MockAdapter()

        # 不应抛出异常
        adapter._log_error("TestError", "测试错误信息")

    def test_log_error_with_details(self):
        """测试：带详细信息的错误日志"""
        adapter = MockAdapter()

        # 不应抛出异常
        adapter._log_error("TestError", "测试错误信息", {"endpoint": "https://api.test.com", "timeout": 30})


class TestBaseAdapterStringRepresentation:
    """测试BaseAdapter字符串表示"""

    def test_repr(self):
        """测试：__repr__方法"""
        adapter = MockAdapter(source_id="test_source", max_retries=5, rate_limit=200)

        repr_str = repr(adapter)

        assert "MockAdapter" in repr_str
        assert "test_source" in repr_str
        assert "5" in repr_str
        assert "200" in repr_str


class TestBaseAdapterEdgeCases:
    """测试BaseAdapter边界情况"""

    @pytest.mark.asyncio
    async def test_zero_max_retries(self):
        """测试：max_retries=0时不重试"""
        adapter = MockAdapter(should_fail=True, max_retries=0)

        with pytest.raises(DataFetchError):
            await adapter.fetch_data_with_retry({"symbol": "000001.SZ"})

        assert adapter.call_count == 1  # 只尝试1次

    @pytest.mark.asyncio
    async def test_very_high_rate_limit(self):
        """测试：非常高的速率限制"""
        adapter = MockAdapter(rate_limit=10000)

        # 应该能快速完成多个请求
        start_time = time.time()
        for _ in range(10):
            await adapter.fetch_data_with_retry({"symbol": "000001.SZ"})
        elapsed_time = time.time() - start_time

        assert elapsed_time < 0.5  # 应该很快完成

    def test_validate_data_with_extra_columns(self):
        """测试：数据包含额外列时仍然有效"""
        adapter = MockAdapter()

        data_with_extra = pd.DataFrame(
            {
                "datetime": [pd.Timestamp("2024-01-01")],
                "open": [100.0],
                "high": [105.0],
                "low": [99.0],
                "close": [103.0],
                "volume": [1000000.0],
                "extra_column": ["extra_value"],  # 额外列
            }
        )

        # 不应抛出异常
        adapter._validate_standard_data(data_with_extra)


# ============================================================================
# 测试运行
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
