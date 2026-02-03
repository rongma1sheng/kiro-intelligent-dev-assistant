"""历史桥接器演示脚本

白皮书依据: 第三章 3.4

演示历史数据注入桥接器的功能。
"""

from datetime import date, timedelta
from src.infra.bridge import (
    HistoricalBridge,
    BridgeConfig,
    AssetType
)
from loguru import logger


def demo_basic_usage():
    """演示基本使用"""
    logger.info("=" * 60)
    logger.info("演示1: 基本使用")
    logger.info("=" * 60)
    
    # 创建配置
    config = BridgeConfig(
        platforms=["guojin", "akshare"],
        default_platform="guojin"
    )
    
    # 初始化桥接器
    bridge = HistoricalBridge(config)
    
    # 获取数据
    end_date = date.today()
    start_date = end_date - timedelta(days=30)
    
    logger.info(f"从国金获取数据: 000001.SZ, {start_date} 到 {end_date}")
    data = bridge.get_data(
        symbol="000001.SZ",
        asset_type=AssetType.STOCK,
        platform="guojin",
        start_date=start_date,
        end_date=end_date
    )
    
    logger.info(f"成功获取 {len(data)} 行数据")
    logger.info(f"列名: {list(data.columns)}")
    logger.info(f"数据预览:\n{data.head()}")


def demo_symbol_normalization():
    """演示标的代码标准化"""
    logger.info("\n" + "=" * 60)
    logger.info("演示2: 标的代码标准化")
    logger.info("=" * 60)
    
    config = BridgeConfig(platforms=["guojin", "akshare"])
    bridge = HistoricalBridge(config)
    
    # 测试不同格式的代码
    test_symbols = [
        ("000001", "akshare"),
        ("600000", "akshare"),
        ("000001.SZ", "guojin"),
        ("600000.SH", "guojin")
    ]
    
    for symbol, platform in test_symbols:
        normalized = bridge.normalize_symbol(symbol, platform)
        logger.info(f"{platform:10s} | {symbol:12s} -> {normalized}")


def demo_multi_platform():
    """演示多平台数据获取"""
    logger.info("\n" + "=" * 60)
    logger.info("演示3: 多平台数据获取")
    logger.info("=" * 60)
    
    config = BridgeConfig(platforms=["guojin", "akshare"])
    bridge = HistoricalBridge(config)
    
    end_date = date.today()
    start_date = end_date - timedelta(days=10)
    
    # 从不同平台获取相同股票的数据
    platforms_data = {}
    
    for platform, symbol in [("guojin", "000001.SZ"), ("akshare", "000001")]:
        try:
            logger.info(f"从 {platform} 获取数据...")
            data = bridge.get_data(
                symbol=symbol,
                asset_type=AssetType.STOCK,
                platform=platform,
                start_date=start_date,
                end_date=end_date
            )
            platforms_data[platform] = data
            logger.info(f"  成功: {len(data)} 行")
        except Exception as e:
            logger.error(f"  失败: {e}")
    
    # 比较数据
    if len(platforms_data) >= 2:
        logger.info("\n数据对比:")
        for platform, data in platforms_data.items():
            logger.info(f"  {platform}: {len(data)} 行, 列名: {list(data.columns)}")


def demo_platform_testing():
    """演示平台测试"""
    logger.info("\n" + "=" * 60)
    logger.info("演示4: 平台测试")
    logger.info("=" * 60)
    
    config = BridgeConfig(platforms=["guojin", "akshare"])
    bridge = HistoricalBridge(config)
    
    # 测试所有平台
    for platform in bridge.get_available_platforms():
        logger.info(f"\n测试平台: {platform}")
        
        try:
            results = bridge.test_platform(platform)
            
            logger.info(f"  测试了 {len(results)} 个接口:")
            for interface_name, result in results.items():
                if result.success:
                    logger.info(
                        f"    ✓ {interface_name}: "
                        f"延迟={result.latency_ms:.1f}ms, "
                        f"覆盖率={result.coverage:.2%}, "
                        f"行数={result.rows_returned}"
                    )
                else:
                    logger.warning(f"    ✗ {interface_name}: {result.error}")
        except Exception as e:
            logger.error(f"  测试失败: {e}")


def demo_different_asset_types():
    """演示不同资产类型"""
    logger.info("\n" + "=" * 60)
    logger.info("演示5: 不同资产类型")
    logger.info("=" * 60)
    
    config = BridgeConfig(platforms=["guojin"])
    bridge = HistoricalBridge(config)
    
    end_date = date.today()
    start_date = end_date - timedelta(days=10)
    
    # 测试不同资产类型
    test_cases = [
        (AssetType.STOCK, "000001.SZ", "股票"),
        (AssetType.INDEX, "000001.SH", "指数"),
    ]
    
    for asset_type, symbol, name in test_cases:
        try:
            logger.info(f"\n获取{name}数据: {symbol}")
            data = bridge.get_data(
                symbol=symbol,
                asset_type=asset_type,
                platform="guojin",
                start_date=start_date,
                end_date=end_date
            )
            logger.info(f"  成功: {len(data)} 行")
            logger.info(f"  数据范围: {data.index[0]} 到 {data.index[-1]}")
        except Exception as e:
            logger.error(f"  失败: {e}")


def main():
    """主函数"""
    logger.info("历史桥接器演示")
    logger.info("白皮书依据: 第三章 3.4")
    
    try:
        # 运行所有演示
        demo_basic_usage()
        demo_symbol_normalization()
        demo_multi_platform()
        demo_platform_testing()
        demo_different_asset_types()
        
        logger.info("\n" + "=" * 60)
        logger.info("所有演示完成！")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"演示失败: {e}")
        raise


if __name__ == "__main__":
    main()
