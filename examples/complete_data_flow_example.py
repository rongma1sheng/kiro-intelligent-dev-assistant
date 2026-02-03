"""完整数据流程示例

白皮书依据: 第三章 3.3.1 数据探针自适应工作流程

本示例展示完整的数据流程：
1. 数据探针全量探测
2. 保存探针日志
3. 数据下载器全量下载
4. 保存下载日志
5. 数据完整性检查
6. 数据补齐（如果需要）
7. 因子挖掘（使用清洗后的数据）
"""

import asyncio
from datetime import date, timedelta
from loguru import logger

from src.infra.data_probe import DataProbe
from src.infra.data_downloader import DataDownloader
from src.infra.data_completeness_checker import DataCompletenessChecker
from src.infra.bridge import AssetType


async def complete_data_flow_example():
    """完整数据流程示例
    
    白皮书依据: 第三章 3.3.1 数据探针自适应工作流程
    
    流程：
    [阶段1] 数据探针全量探测
        ↓
    保存探针日志 (probe_discovery.json)
        ↓
    [阶段2] 数据下载器全量下载
        ↓
    保存下载日志 (data_download.log)
        ↓
    [阶段3] 数据清洗 (DataSanitizer)
        ↓
    [阶段4] 数据完整性检查
        ↓
    数据补齐（如果需要）
        ↓
    [阶段5] 因子挖掘（使用清洗后的数据）
    """
    
    logger.info("=" * 80)
    logger.info("完整数据流程示例")
    logger.info("=" * 80)
    
    # ========== 阶段1: 数据探针全量探测 ==========
    logger.info("\n[阶段1] 数据探针全量探测")
    logger.info("-" * 80)
    
    # 1.1 初始化数据探针
    probe = DataProbe(probe_interval=86400)
    logger.info(f"数据探针初始化: {probe}")
    
    # 1.2 并发探测所有数据源
    logger.info("开始探测所有数据源...")
    probe_results = await probe.probe_all_sources()
    
    # 1.3 生成可用性报告
    report = probe.generate_availability_report()
    logger.info(
        f"探测完成: 总数={report['total_sources']}, "
        f"可用={report['available_sources']}, "
        f"可用率={report['availability_rate']:.1f}%"
    )
    
    # 1.4 保存探针日志
    probe_log_path = "probe_discovery.json"
    probe.save_probe_results(probe_log_path)
    logger.info(f"探针日志已保存: {probe_log_path}")
    
    # ========== 阶段2: 数据下载器全量下载 ==========
    logger.info("\n[阶段2] 数据下载器全量下载")
    logger.info("-" * 80)
    
    # 2.1 初始化数据下载器
    downloader = DataDownloader()
    
    # 2.2 加载探针日志
    downloader.load_probe_log(probe_log_path)
    
    # 2.3 定义要下载的标的
    symbols = [
        "000001.SZ",  # 平安银行
        "600000.SH",  # 浦发银行
        "000002.SZ",  # 万科A
    ]
    
    # 2.4 定义日期范围
    end_date = date.today()
    start_date = end_date - timedelta(days=30)  # 最近30天
    
    # 2.5 全量下载数据
    logger.info(f"开始下载 {len(symbols)} 个标的的数据...")
    download_summary = downloader.download_all_symbols(
        symbols=symbols,
        start_date=start_date,
        end_date=end_date,
        asset_type=AssetType.STOCK
    )
    
    logger.info(
        f"下载完成: 成功={download_summary['summary']['success']}, "
        f"失败={download_summary['summary']['failed']}, "
        f"使用备用={download_summary['summary']['fallback_used']}"
    )
    
    # 2.6 保存下载日志
    download_log_path = "data_download.log"
    downloader.save_download_log(download_log_path)
    logger.info(f"下载日志已保存: {download_log_path}")
    
    # ========== 阶段3: 数据清洗 ==========
    logger.info("\n[阶段3] 数据清洗")
    logger.info("-" * 80)
    logger.info("数据清洗由 DataSanitizer 完成（8层清洗框架）")
    logger.info("清洗维度: NaN、价格合理性、HLOC一致性、成交量、重复值、异常值、数据缺口、公司行动")
    
    # ========== 阶段4: 数据完整性检查 ==========
    logger.info("\n[阶段4] 数据完整性检查（因子挖掘前）")
    logger.info("-" * 80)
    
    # 4.1 初始化完整性检查器
    checker = DataCompletenessChecker(download_log_path=download_log_path)
    
    # 4.2 检查数据完整性
    is_complete = checker.check_before_mining(symbols=symbols)
    
    if is_complete:
        logger.info("✅ 数据完整，可以开始因子挖掘")
    else:
        logger.warning("⚠️ 数据不完整，需要补齐")
        
        # 4.3 触发数据补齐
        logger.info("开始数据补齐流程...")
        success = checker.fill_missing_data(
            symbols=symbols,
            asset_type=AssetType.STOCK
        )
        
        if success:
            logger.info("✅ 数据补齐完成")
        else:
            logger.error("❌ 数据补齐失败")
            return
    
    # ========== 阶段5: 因子挖掘 ==========
    logger.info("\n[阶段5] 因子挖掘（使用清洗后的数据）")
    logger.info("-" * 80)
    logger.info("因子挖掘器读取清洗后的数据进行挖掘：")
    logger.info("- GeneticMiner: 遗传算法因子挖掘")
    logger.info("- AlternativeDataMiner: 另类数据因子挖掘")
    logger.info("- 其他16个专业挖掘器...")
    
    # ========== 完成 ==========
    logger.info("\n" + "=" * 80)
    logger.info("完整数据流程示例完成！")
    logger.info("=" * 80)
    
    logger.info("\n生成的文件：")
    logger.info(f"  - {probe_log_path}: 探针日志（数据源可用性）")
    logger.info(f"  - {download_log_path}: 下载日志（下载结果）")
    
    logger.info("\n数据流程总结：")
    logger.info("  1. ✅ 数据探针探测所有数据源")
    logger.info("  2. ✅ 保存探针日志")
    logger.info("  3. ✅ 数据下载器全量下载")
    logger.info("  4. ✅ 保存下载日志")
    logger.info("  5. ✅ 数据清洗（DataSanitizer）")
    logger.info("  6. ✅ 数据完整性检查")
    logger.info("  7. ✅ 数据补齐（如果需要）")
    logger.info("  8. ✅ 因子挖掘（使用清洗数据）")


if __name__ == "__main__":
    # 运行完整数据流程示例
    asyncio.run(complete_data_flow_example())
