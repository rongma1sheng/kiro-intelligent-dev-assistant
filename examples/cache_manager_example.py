"""缓存管理器使用示例

白皮书依据: 第三章 3.2 基础设施与数据治理
需求: requirements.md 9.1-9.7

本示例展示如何使用CacheManager进行数据缓存。
"""

from datetime import datetime
import pandas as pd
from src.infra.cache_manager import CacheManager


def example_basic_usage():
    """基础使用示例"""
    print("=" * 60)
    print("示例1: 基础使用")
    print("=" * 60)
    
    # 创建缓存管理器
    cache = CacheManager(
        redis_host='localhost',
        redis_port=6379,
        default_ttl=3600  # 默认1小时过期
    )
    
    # 设置缓存
    cache.set("user:1001", {"name": "张三", "age": 30})
    print("✓ 缓存已设置")
    
    # 获取缓存
    user = cache.get("user:1001")
    print(f"✓ 缓存获取: {user}")
    
    # 删除缓存
    cache.delete("user:1001")
    print("✓ 缓存已删除")
    
    # 关闭连接
    cache.close()
    print()


def example_dataframe_caching():
    """DataFrame缓存示例"""
    print("=" * 60)
    print("示例2: DataFrame缓存")
    print("=" * 60)
    
    cache = CacheManager()
    
    # 创建测试数据
    df = pd.DataFrame({
        'date': pd.date_range('2024-01-01', periods=5),
        'symbol': ['AAPL'] * 5,
        'close': [150.0, 151.5, 152.0, 151.0, 153.5],
        'volume': [1000000, 1100000, 1200000, 1150000, 1300000]
    })
    
    # 生成缓存键
    cache_key = CacheManager.generate_cache_key(
        data_type="market",
        symbol="AAPL",
        start_date=datetime(2024, 1, 1),
        end_date=datetime(2024, 1, 5),
        frequency="1d"
    )
    
    print(f"缓存键: {cache_key}")
    
    # 缓存DataFrame（24小时）
    cache.set(cache_key, df, ttl=86400)
    print("✓ DataFrame已缓存")
    
    # 获取缓存
    cached_df = cache.get(cache_key)
    print(f"✓ DataFrame已获取，行数: {len(cached_df)}")
    print(cached_df.head())
    
    # 检查TTL
    ttl = cache.get_ttl(cache_key)
    print(f"✓ 剩余过期时间: {ttl}秒")
    
    cache.close()
    print()


def example_custom_ttl():
    """自定义TTL示例"""
    print("=" * 60)
    print("示例3: 自定义TTL")
    print("=" * 60)
    
    cache = CacheManager()
    
    # 日线数据：缓存24小时
    cache.set("market:daily:AAPL", {"price": 150.0}, ttl=86400)
    print("✓ 日线数据缓存24小时")
    
    # 分钟线数据：缓存1小时
    cache.set("market:1min:AAPL", {"price": 150.5}, ttl=3600)
    print("✓ 分钟线数据缓存1小时")
    
    # 宏观数据：缓存7天
    cache.set("macro:gdp:china", {"value": 5.2}, ttl=604800)
    print("✓ 宏观数据缓存7天")
    
    cache.close()
    print()


def example_context_manager():
    """上下文管理器示例"""
    print("=" * 60)
    print("示例4: 上下文管理器")
    print("=" * 60)
    
    # 使用with语句自动管理连接
    with CacheManager() as cache:
        cache.set("temp:data", "临时数据", ttl=60)
        data = cache.get("temp:data")
        print(f"✓ 数据: {data}")
    
    print("✓ 连接已自动关闭")
    print()


def example_cache_stats():
    """缓存统计示例"""
    print("=" * 60)
    print("示例5: 缓存统计")
    print("=" * 60)
    
    cache = CacheManager()
    
    # 设置一些测试数据
    for i in range(10):
        cache.set(f"test:key:{i}", f"value_{i}", ttl=3600)
    
    # 获取统计信息
    stats = cache.get_stats()
    
    print(f"缓存启用: {stats['enabled']}")
    print(f"键数量: {stats['keys_count']}")
    print(f"内存使用: {stats.get('used_memory_human', 'N/A')}")
    print(f"命中率: {stats.get('hit_rate', 0):.2%}")
    
    # 清理测试数据
    for i in range(10):
        cache.delete(f"test:key:{i}")
    
    cache.close()
    print()


def example_error_handling():
    """错误处理示例"""
    print("=" * 60)
    print("示例6: 错误处理")
    print("=" * 60)
    
    # 禁用缓存的情况
    cache = CacheManager(enabled=False)
    
    result = cache.set("test:key", "value")
    print(f"禁用缓存时设置: {result}")  # False
    
    data = cache.get("test:key")
    print(f"禁用缓存时获取: {data}")  # None
    
    # 不可序列化对象
    cache_enabled = CacheManager()
    try:
        # Lambda函数不可序列化
        cache_enabled.set("test:lambda", lambda x: x + 1)
    except ValueError as e:
        print(f"✓ 捕获到预期错误: {e}")
    
    cache_enabled.close()
    print()


def example_cache_key_generation():
    """缓存键生成示例"""
    print("=" * 60)
    print("示例7: 缓存键生成")
    print("=" * 60)
    
    # 基础键
    key1 = CacheManager.generate_cache_key(
        data_type="market",
        symbol="AAPL"
    )
    print(f"基础键: {key1}")
    
    # 带日期的键
    key2 = CacheManager.generate_cache_key(
        data_type="market",
        symbol="AAPL",
        start_date=datetime(2024, 1, 1),
        end_date=datetime(2024, 12, 31)
    )
    print(f"带日期键: {key2}")
    
    # 带额外参数的键（会生成哈希）
    key3 = CacheManager.generate_cache_key(
        data_type="market",
        symbol="AAPL",
        start_date=datetime(2024, 1, 1),
        end_date=datetime(2024, 12, 31),
        frequency="1d",
        adjust="qfq"
    )
    print(f"带参数键: {key3}")
    
    # 验证一致性
    key4 = CacheManager.generate_cache_key(
        data_type="market",
        symbol="AAPL",
        start_date=datetime(2024, 1, 1),
        end_date=datetime(2024, 12, 31),
        adjust="qfq",  # 参数顺序不同
        frequency="1d"
    )
    print(f"参数顺序不同: {key4}")
    print(f"✓ 键一致性: {key3 == key4}")
    print()


def main():
    """运行所有示例"""
    print("\n" + "=" * 60)
    print("缓存管理器使用示例")
    print("=" * 60 + "\n")
    
    try:
        example_basic_usage()
        example_dataframe_caching()
        example_custom_ttl()
        example_context_manager()
        example_cache_stats()
        example_error_handling()
        example_cache_key_generation()
        
        print("=" * 60)
        print("所有示例运行完成！")
        print("=" * 60)
        
    except ConnectionError as e:
        print(f"\n❌ Redis连接失败: {e}")
        print("请确保Redis服务正在运行（localhost:6379）")
        print("\n启动Redis:")
        print("  Windows: redis-server.exe")
        print("  Linux/Mac: redis-server")


if __name__ == '__main__':
    main()
