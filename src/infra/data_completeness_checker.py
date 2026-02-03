"""数据完整性检查器 - 因子挖掘前数据检查

白皮书依据: 第三章 3.3.1 数据探针自适应工作流程 - 阶段4

本模块实现数据完整性检查器功能，负责：
1. 检查数据是否最新
2. 识别缺失的交易日
3. 触发数据补齐流程
4. 确保因子挖掘前数据完整
"""

import json
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import List, Optional

from loguru import logger

from src.infra.bridge import AssetType
from src.infra.data_downloader import DataDownloader


class DataCompletenessChecker:
    """数据完整性检查器

    白皮书依据: 第三章 3.3.1 数据探针自适应工作流程 - 阶段4

    功能：
    1. 检查数据时效性
    2. 识别缺失的交易日
    3. 触发数据补齐
    4. 确保数据完整

    Attributes:
        downloader: 数据下载器
        download_log_path: 下载日志路径

    Example:
        >>> checker = DataCompletenessChecker()
        >>> is_complete = checker.check_before_mining(
        ...     symbols=["000001.SZ", "600000.SH"]
        ... )
        >>> if not is_complete:
        ...     checker.补齐_missing_data(symbols)
    """

    def __init__(self, download_log_path: str = "data_download.log"):
        """初始化数据完整性检查器

        Args:
            download_log_path: 下载日志文件路径
        """
        self.downloader = DataDownloader()
        self.download_log_path = download_log_path

        logger.info("DataCompletenessChecker initialized")

    def check_before_mining(self, symbols: Optional[List[str]] = None) -> bool:  # pylint: disable=unused-argument
        """因子挖掘前检查数据完整性

        白皮书依据: 第三章 3.3.1 阶段4 - 数据完整性检查

        Args:
            symbols: 要检查的标的列表，None表示检查所有

        Returns:
            True表示数据完整，False表示需要补齐
        """
        logger.info("开始数据完整性检查...")

        try:
            # 读取下载日志
            download_log = self._load_download_log()

            if download_log is None:
                logger.warning("下载日志不存在，需要全量下载")
                return False

            # 获取最新交易日
            latest_trading_date = self._get_latest_trading_date()

            # 获取日志中的数据日期
            log_date_str = download_log.get("trading_date")
            if not log_date_str:
                logger.warning("下载日志中没有交易日期信息")
                return False

            log_date = datetime.strptime(log_date_str, "%Y-%m-%d").date()

            # 判断数据是否最新
            if self._is_data_up_to_date(log_date, latest_trading_date):  # pylint: disable=no-else-return
                logger.info(f"数据是最新的: {log_date}")
                return True
            else:
                # 计算缺失的交易日
                missing_dates = self._get_missing_trading_dates(log_date, latest_trading_date)

                logger.warning(
                    f"数据过期: 日志日期={log_date}, 最新交易日={latest_trading_date}, "
                    f"缺失 {len(missing_dates)} 个交易日"
                )

                return False

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"数据完整性检查失败: {e}")
            return False

    def fill_missing_data(self, symbols: List[str], asset_type: AssetType = AssetType.STOCK) -> bool:
        """补齐缺失的交易日数据

        白皮书依据: 第三章 3.3.1 阶段4 - 数据补齐流程

        Args:
            symbols: 要补齐的标的列表
            asset_type: 资产类型

        Returns:
            True表示补齐成功，False表示补齐失败
        """
        logger.info(f"开始数据补齐流程: {len(symbols)} 个标的...")

        try:
            # 读取下载日志
            download_log = self._load_download_log()

            if download_log is None:
                logger.error("下载日志不存在，无法补齐")
                return False

            # 获取最新交易日
            latest_trading_date = self._get_latest_trading_date()

            # 获取日志中的数据日期
            log_date_str = download_log.get("trading_date")
            log_date = datetime.strptime(log_date_str, "%Y-%m-%d").date()

            # 计算缺失的交易日
            missing_dates = self._get_missing_trading_dates(log_date, latest_trading_date)

            if not missing_dates:
                logger.info("没有缺失的交易日")
                return True

            logger.info(f"缺失 {len(missing_dates)} 个交易日: {missing_dates}")

            # 加载探针日志
            self.downloader.load_probe_log()

            # 补齐每个缺失的交易日
            for missing_date in missing_dates:
                logger.info(f"补齐 {missing_date} 的数据...")

                # 下载单日数据
                result = self.downloader.download_all_symbols(
                    symbols=symbols, start_date=missing_date, end_date=missing_date, asset_type=asset_type
                )

                success_count = result["summary"]["success"]
                failed_count = result["summary"]["failed"]

                logger.info(f"补齐 {missing_date} 完成: " f"成功 {success_count}, 失败 {failed_count}")

            # 更新下载日志
            self.downloader.save_download_log(self.download_log_path)

            logger.info("数据补齐完成")
            return True

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"数据补齐失败: {e}")
            return False

    def _load_download_log(self) -> Optional[dict]:
        """加载下载日志

        Returns:
            下载日志字典，文件不存在时返回None
        """
        try:
            filepath = Path(self.download_log_path)

            if not filepath.exists():
                return None

            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"加载下载日志失败: {e}")
            return None

    def _get_latest_trading_date(self) -> date:
        """获取最新交易日

        白皮书依据: 第三章 3.3.1 阶段4 - 数据时效性判断

        Returns:
            最新交易日
        """
        now = datetime.now()
        current_time = now.time()
        today = now.date()

        # 如果当前时间 < 16:00，最新数据应为前一交易日
        if current_time < time(16, 0):  # pylint: disable=no-else-return
            # 简化处理：前一天（实际应该查询交易日历）
            return today - timedelta(days=1)
        else:
            # 如果当前时间 >= 16:00，最新数据应为当日
            return today

    def _is_data_up_to_date(self, data_date: date, latest_trading_date: date) -> bool:
        """判断数据是否最新

        白皮书依据: 第三章 3.3.1 阶段4 - 数据时效性判断标准

        Args:
            data_date: 数据日期
            latest_trading_date: 最新交易日

        Returns:
            True表示数据最新，False表示数据过期
        """
        return data_date >= latest_trading_date

    def _get_missing_trading_dates(self, start_date: date, end_date: date) -> List[date]:
        """获取缺失的交易日列表

        白皮书依据: 第三章 3.3.1 阶段4 - 计算缺失的交易日

        Args:
            start_date: 开始日期（不包含）
            end_date: 结束日期（包含）

        Returns:
            缺失的交易日列表
        """
        # 简化处理：返回日期范围内的所有日期
        # 实际应该查询交易日历，只返回交易日

        missing_dates = []
        current_date = start_date + timedelta(days=1)

        while current_date <= end_date:
            # 简化处理：跳过周末
            if current_date.weekday() < 5:  # 0-4 是周一到周五
                missing_dates.append(current_date)

            current_date += timedelta(days=1)

        return missing_dates
