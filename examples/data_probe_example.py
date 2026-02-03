"""数据探针使用示例

白皮书依据: 第三章 3.2 数据探针
需求: requirements.md 1.1-1.10
设计: design.md 核心组件设计 - 数据探针

本文件演示数据探针的各种使用场景：
1. 基础使用：初始化和探测
2. 自定义数据源注册
3. 按类型获取可用数据源
4. 生成可用性报告
"""

import asyncio
import json
from datetime import datetime

from src.infra.data_probe import DataProbe
from src.infra.data_models import (
    DataSourceConfig,
    DataSourceType,
    DataSourceStatus
)


async def example_1_basic_usage():
    """示例1：基础使用 - 初始化和探测所有数据源"""
    print("=" * 80)
    print("示例1：基础使用 - 初始化和探测所有数据源")
    print("=" * 80)
    
    # 1. 初始化数据探针（默认24小时探测间隔）
    probe = DataProbe()
    print(f"\n✓ 数据探针初始化完成")
    print(f"  - 探测间隔: {probe.probe_interval}秒 ({probe.probe_interval/3600:.1f}小时)")
    print(f"  - 预定义数据源: {len(probe.data_sources)}个")
    
    # 2. 探测所有数据源
    print(f"\n开始探测所有数据源...")
    results = await probe.probe_all_sources()
    
    # 3. 统计结果
    available_count = sum(
        1 for r in results.values()
        if r.status == DataSourceStatus.AVAILABLE
    )
    unavailable_count = len(results) - available_count
    
    print(f"\n✓ 探测完成")
    print(f"  - 总数据源: {len(results)}")
    print(f"  - 可用: {available_count}")
    print(f"  - 不可用: {unavailable_count}")
    print(f"  - 可用率: {available_count/len(results)*100:.1f}%")
    
    # 4. 显示每个数据源的探测结果
    print(f"\n数据源详情:")
    for source_id, result in results.items():
        config = probe.data_sources[source_id]
        status_icon = "✓" if result.status == DataSourceStatus.AVAILABLE else "✗"
        print(
            f"  {status_icon} {config.source_name:20s} | "
            f"状态: {result.status.value:12s} | "
            f"响应: {result.response_time:6.0f}ms | "
            f"质量: {result.quality_score:.2f}"
        )


async def example_2_register_custom_source():
    """示例2：注册自定义数据源"""
    print("\n" + "=" * 80)
    print("示例2：注册自定义数据源")
    print("=" * 80)
    
    # 1. 初始化探针
    probe = DataProbe()
    print(f"\n初始数据源数量: {len(probe.data_sources)}")
    
    # 2. 注册自定义数据源
    custom_config = DataSourceConfig(
        source_id="my_custom_source",
        source_name="My Custom Data Source",
        source_type=DataSourceType.MARKET_DATA,
        api_endpoint="https://api.mycustom.com",
        api_key="my_secret_key",
        rate_limit=500,
        priority=10,
        is_free=False,
        requires_auth=True
    )
    
    probe.register_source(custom_config)
    print(f"\n✓ 注册自定义数据源: {custom_config.source_name}")
    print(f"  - 数据源ID: {custom_config.source_id}")
    print(f"  - 类型: {custom_config.source_type.value}")
    print(f"  - 优先级: {custom_config.priority}")
    print(f"  - 速率限制: {custom_config.rate_limit} 请求/秒")
    
    print(f"\n当前数据源数量: {len(probe.data_sources)}")
    
    # 3. 探测自定义数据源
    print(f"\n探测自定义数据源...")
    result = await probe.probe_source("my_custom_source")
    
    print(f"\n✓ 探测结果:")
    print(f"  - 状态: {result.status.value}")
    print(f"  - 响应时间: {result.response_time:.0f}ms")
    print(f"  - 数据可用: {result.data_available}")
    print(f"  - 质量评分: {result.quality_score:.2f}")


async def example_3_get_sources_by_type():
    """示例3：按类型获取可用数据源"""
    print("\n" + "=" * 80)
    print("示例3：按类型获取可用数据源")
    print("=" * 80)
    
    # 1. 初始化并探测
    probe = DataProbe()
    await probe.probe_all_sources()
    
    # 2. 获取所有可用数据源
    all_sources = probe.get_available_sources()
    print(f"\n所有可用数据源: {len(all_sources)}个")
    
    # 3. 按类型获取数据源
    source_types = [
        DataSourceType.MARKET_DATA,
        DataSourceType.SENTIMENT_DATA,
        DataSourceType.EVENT_DATA,
        DataSourceType.MACRO_DATA
    ]
    
    for source_type in source_types:
        sources = probe.get_available_sources(source_type)
        print(f"\n{source_type.value.upper()} ({len(sources)}个):")
        
        for source in sources:
            result = probe.probe_results[source.source_id]
            print(
                f"  • {source.source_name:20s} | "
                f"优先级: {source.priority:2d} | "
                f"质量: {result.quality_score:.2f} | "
                f"{'免费' if source.is_free else '付费'}"
            )


async def example_4_availability_report():
    """示例4：生成可用性报告"""
    print("\n" + "=" * 80)
    print("示例4：生成可用性报告")
    print("=" * 80)
    
    # 1. 初始化并探测
    probe = DataProbe()
    await probe.probe_all_sources()
    
    # 2. 生成报告
    report = probe.generate_availability_report()
    
    # 3. 显示总体统计
    print(f"\n总体统计:")
    print(f"  - 总数据源: {report['total_sources']}")
    print(f"  - 可用数据源: {report['available_sources']}")
    print(f"  - 不可用数据源: {report['unavailable_sources']}")
    print(f"  - 可用率: {report['availability_rate']:.1f}%")
    
    # 4. 按类型统计
    print(f"\n按类型统计:")
    for type_name, stats in report['by_type'].items():
        availability = (stats['available'] / stats['total'] * 100) if stats['total'] > 0 else 0
        print(
            f"  • {type_name:20s}: "
            f"{stats['available']}/{stats['total']} "
            f"({availability:.0f}%)"
        )
    
    # 5. 详细数据源信息
    print(f"\n详细数据源信息:")
    for source_info in report['sources']:
        status_icon = "✓" if source_info['status'] == 'available' else "✗"
        print(
            f"  {status_icon} {source_info['source_name']:20s} | "
            f"{source_info['source_type']:15s} | "
            f"响应: {source_info['response_time']:6.0f}ms | "
            f"质量: {source_info['quality_score']:.2f}"
        )
    
    # 6. 导出报告为JSON
    report_json = json.dumps(report, indent=2, ensure_ascii=False)
    print(f"\n✓ 报告已生成 (JSON格式，{len(report_json)}字节)")
    
    # 可选：保存到文件
    # with open('data_source_availability_report.json', 'w', encoding='utf-8') as f:
    #     f.write(report_json)
    # print(f"✓ 报告已保存到: data_source_availability_report.json")


async def example_5_single_source_probe():
    """示例5：探测单个数据源"""
    print("\n" + "=" * 80)
    print("示例5：探测单个数据源")
    print("=" * 80)
    
    # 1. 初始化探针
    probe = DataProbe()
    
    # 2. 探测单个数据源
    source_ids = ["akshare", "yahoo_finance", "alpha_vantage"]
    
    for source_id in source_ids:
        print(f"\n探测数据源: {source_id}")
        result = await probe.probe_source(source_id)
        
        config = probe.data_sources[source_id]
        
        print(f"  数据源名称: {config.source_name}")
        print(f"  数据源类型: {config.source_type.value}")
        print(f"  API端点: {config.api_endpoint}")
        print(f"  需要认证: {'是' if config.requires_auth else '否'}")
        print(f"  探测结果:")
        print(f"    - 状态: {result.status.value}")
        print(f"    - 响应时间: {result.response_time:.0f}ms")
        print(f"    - 数据可用: {result.data_available}")
        print(f"    - 质量评分: {result.quality_score:.2f}")
        print(f"    - 探测时间: {result.last_probe_time.strftime('%Y-%m-%d %H:%M:%S')}")


async def example_6_custom_interval():
    """示例6：自定义探测间隔"""
    print("\n" + "=" * 80)
    print("示例6：自定义探测间隔")
    print("=" * 80)
    
    # 1. 创建不同探测间隔的探针
    intervals = [
        (3600, "1小时"),
        (7200, "2小时"),
        (43200, "12小时"),
        (86400, "24小时")
    ]
    
    for interval, description in intervals:
        probe = DataProbe(probe_interval=interval)
        print(f"\n探针配置: 探测间隔={description} ({interval}秒)")
        print(f"  - 数据源数量: {len(probe.data_sources)}")
        print(f"  - 探测结果缓存: {len(probe.probe_results)}")
        print(f"  - 字符串表示: {repr(probe)}")


async def main():
    """运行所有示例"""
    print("\n" + "=" * 80)
    print("数据探针使用示例")
    print("=" * 80)
    print(f"运行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 运行所有示例
    await example_1_basic_usage()
    await example_2_register_custom_source()
    await example_3_get_sources_by_type()
    await example_4_availability_report()
    await example_5_single_source_probe()
    await example_6_custom_interval()
    
    print("\n" + "=" * 80)
    print("所有示例运行完成！")
    print("=" * 80)


if __name__ == "__main__":
    # 运行示例
    asyncio.run(main())
