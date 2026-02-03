"""基础适配器使用示例

白皮书依据: 第三章 3.2 基础设施与数据治理
需求: requirements.md 6.1-6.10
设计: design.md 核心组件设计 - 适配器层

本示例展示如何：
1. 继承BaseAdapter创建自定义适配器
2. 实现必需的抽象方法
3. 使用重试机制和速率限制
4. 处理错误和异常
"""

import asyncio
import pandas as pd
from typing import Dict, Any
from datetime import datetime

from src.infra.adapters.base_adapter import BaseAdapter
from src.infra.data_exceptions import DataFetchError, AuthenticationError


# ============================================================================
# 示例1: 创建简单的自定义适配器
# ============================================================================

class SimpleAdapter(BaseAdapter):
    """简单的自定义适配器示例
    
    演示如何实现BaseAdapter的所有必需方法。
    """
    
    def __init__(self, api_key: str = None):
        """初始化适配器
        
        Args:
            api_key: API密钥（可选）
        """
        super().__init__(
            source_id="simple_adapter",
            max_retries=3,
            rate_limit=100
        )
        self.api_key = api_key
    
    async def fetch_data(self, request_params: Dict[str, Any]) -> pd.DataFrame:
        """获取数据
        
        Args:
            request_params: 请求参数，包含symbol, start_date, end_date等
        
        Returns:
            标准化的数据DataFrame
        """
        symbol = request_params.get('symbol')
        start_date = request_params.get('start_date', '2024-01-01')
        end_date = request_params.get('end_date', '2024-12-31')
        
        print(f"正在获取 {symbol} 的数据 ({start_date} 到 {end_date})...")
        
        # 模拟API调用
        await asyncio.sleep(0.1)
        
        # 模拟返回数据
        raw_data = {
            'date': ['2024-01-01', '2024-01-02', '2024-01-03'],
            'price_open': [100.0, 101.0, 102.0],
            'price_high': [105.0, 106.0, 107.0],
            'price_low': [99.0, 100.0, 101.0],
            'price_close': [103.0, 104.0, 105.0],
            'vol': [1000000, 1100000, 1200000]
        }
        
        # 标准化数据
        return self.standardize_data(raw_data)
    
    async def test_connectivity(self) -> bool:
        """测试连接性
        
        Returns:
            True表示连接正常
        """
        print("测试连接性...")
        
        # 模拟连接测试
        await asyncio.sleep(0.05)
        
        # 假设连接正常
        return True
    
    async def test_authentication(self) -> bool:
        """测试认证
        
        Returns:
            True表示认证成功
        """
        print("测试认证...")
        
        # 模拟认证测试
        await asyncio.sleep(0.05)
        
        # 检查API密钥
        if self.api_key:
            print(f"使用API密钥: {self.api_key[:4]}****")
            return True
        else:
            print("未提供API密钥")
            return False
    
    def standardize_data(self, raw_data: Any) -> pd.DataFrame:
        """数据标准化
        
        Args:
            raw_data: 原始数据字典
        
        Returns:
            标准化的DataFrame
        """
        # 转换为DataFrame
        df = pd.DataFrame(raw_data)
        
        # 重命名列
        df = df.rename(columns={
            'date': 'datetime',
            'price_open': 'open',
            'price_high': 'high',
            'price_low': 'low',
            'price_close': 'close',
            'vol': 'volume'
        })
        
        # 转换日期类型
        df['datetime'] = pd.to_datetime(df['datetime'])
        
        # 验证数据格式
        self._validate_standard_data(df)
        
        return df


# ============================================================================
# 示例2: 带错误处理的适配器
# ============================================================================

class RobustAdapter(BaseAdapter):
    """带完整错误处理的适配器示例
    
    演示如何处理各种错误情况。
    """
    
    def __init__(self, fail_probability: float = 0.0):
        """初始化适配器
        
        Args:
            fail_probability: 失败概率（0-1），用于模拟错误
        """
        super().__init__(
            source_id="robust_adapter",
            max_retries=3,
            rate_limit=50
        )
        self.fail_probability = fail_probability
        self.call_count = 0
    
    async def fetch_data(self, request_params: Dict[str, Any]) -> pd.DataFrame:
        """获取数据（带错误模拟）
        
        Args:
            request_params: 请求参数
        
        Returns:
            标准化的数据DataFrame
        
        Raises:
            DataFetchError: 当数据获取失败时
        """
        self.call_count += 1
        
        # 模拟随机失败
        import random
        if random.random() < self.fail_probability:
            self._log_error(
                "DataFetchError",
                f"模拟失败（第 {self.call_count} 次尝试）",
                {"fail_probability": self.fail_probability}
            )
            raise DataFetchError(
                f"模拟失败（第 {self.call_count} 次尝试）",
                source_id=self.source_id
            )
        
        # 成功获取数据
        print(f"✓ 第 {self.call_count} 次尝试成功")
        
        return pd.DataFrame({
            'datetime': [pd.Timestamp('2024-01-01')],
            'open': [100.0],
            'high': [105.0],
            'low': [99.0],
            'close': [103.0],
            'volume': [1000000.0]
        })
    
    async def test_connectivity(self) -> bool:
        """测试连接性"""
        return True
    
    async def test_authentication(self) -> bool:
        """测试认证"""
        return True
    
    def standardize_data(self, raw_data: Any) -> pd.DataFrame:
        """数据标准化"""
        return raw_data


# ============================================================================
# 使用示例
# ============================================================================

async def example_1_basic_usage():
    """示例1: 基本使用"""
    print("\n" + "="*70)
    print("示例1: 基本使用")
    print("="*70)
    
    # 创建适配器
    adapter = SimpleAdapter(api_key="test_key_12345")
    
    # 测试连接性
    is_connected = await adapter.test_connectivity()
    print(f"连接状态: {'✓ 正常' if is_connected else '✗ 失败'}")
    
    # 测试认证
    is_authenticated = await adapter.test_authentication()
    print(f"认证状态: {'✓ 成功' if is_authenticated else '✗ 失败'}")
    
    # 获取数据
    data = await adapter.fetch_data({
        'symbol': '000001.SZ',
        'start_date': '2024-01-01',
        'end_date': '2024-01-03'
    })
    
    print(f"\n获取到 {len(data)} 行数据:")
    print(data)


async def example_2_retry_mechanism():
    """示例2: 重试机制"""
    print("\n" + "="*70)
    print("示例2: 重试机制（模拟50%失败率）")
    print("="*70)
    
    # 创建带失败概率的适配器
    adapter = RobustAdapter(fail_probability=0.5)
    
    try:
        # 使用重试机制获取数据
        data = await adapter.fetch_data_with_retry({
            'symbol': '000001.SZ'
        })
        
        print(f"\n✓ 数据获取成功（共尝试 {adapter.call_count} 次）")
        print(f"数据行数: {len(data)}")
        
    except DataFetchError as e:
        print(f"\n✗ 数据获取失败: {e}")


async def example_3_rate_limit():
    """示例3: 速率限制"""
    print("\n" + "="*70)
    print("示例3: 速率限制（10请求/秒）")
    print("="*70)
    
    # 创建低速率限制的适配器
    adapter = SimpleAdapter()
    adapter.rate_limit = 10  # 10请求/秒 = 0.1秒/请求
    
    import time
    start_time = time.time()
    
    # 连续发送5个请求
    for i in range(5):
        await adapter.fetch_data_with_retry({
            'symbol': f'00000{i}.SZ'
        })
        print(f"✓ 完成第 {i+1} 个请求")
    
    elapsed_time = time.time() - start_time
    print(f"\n总耗时: {elapsed_time:.2f}秒")
    print(f"平均速率: {5/elapsed_time:.1f} 请求/秒")


async def example_4_data_validation():
    """示例4: 数据验证"""
    print("\n" + "="*70)
    print("示例4: 数据验证")
    print("="*70)
    
    adapter = SimpleAdapter()
    
    # 测试有效数据
    print("\n测试1: 有效数据")
    valid_data = pd.DataFrame({
        'datetime': [pd.Timestamp('2024-01-01')],
        'open': [100.0],
        'high': [105.0],
        'low': [99.0],
        'close': [103.0],
        'volume': [1000000.0]
    })
    
    try:
        adapter._validate_standard_data(valid_data)
        print("✓ 数据验证通过")
    except DataFetchError as e:
        print(f"✗ 数据验证失败: {e}")
    
    # 测试无效数据（缺少列）
    print("\n测试2: 无效数据（缺少列）")
    invalid_data = pd.DataFrame({
        'datetime': [pd.Timestamp('2024-01-01')],
        'open': [100.0]
        # 缺少 high, low, close, volume
    })
    
    try:
        adapter._validate_standard_data(invalid_data)
        print("✓ 数据验证通过")
    except DataFetchError as e:
        print(f"✗ 数据验证失败: {e}")


async def main():
    """主函数"""
    print("\n" + "="*70)
    print("BaseAdapter 使用示例")
    print("="*70)
    
    # 运行所有示例
    await example_1_basic_usage()
    await example_2_retry_mechanism()
    await example_3_rate_limit()
    await example_4_data_validation()
    
    print("\n" + "="*70)
    print("所有示例运行完成！")
    print("="*70)


if __name__ == '__main__':
    asyncio.run(main())
