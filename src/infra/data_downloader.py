"""数据下载器 - 全量数据下载

白皮书依据: 第三章 3.3.1 数据探针自适应工作流程 - 阶段2

本模块实现数据下载器功能，负责：
1. 读取探针日志
2. 使用推荐接口全量下载数据
3. 记录下载结果
4. 自动降级和重试
"""

import json
import time
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger

from src.infra.bridge import AssetType, BridgeConfig, HistoricalBridge


class DataDownloader:
    """数据下载器

    白皮书依据: 第三章 3.3.1 数据探针自适应工作流程 - 阶段2

    功能：
    1. 读取探针日志获取推荐接口
    2. 全量下载数据
    3. 记录下载结果
    4. 自动降级和重试

    Attributes:
        bridge: 历史数据桥接器
        probe_log: 探针日志
        download_results: 下载结果列表

    Example:
        >>> downloader = DataDownloader()
        >>> downloader.load_probe_log("probe_discovery.json")
        >>> results = downloader.download_all_symbols(
        ...     symbols=["000001.SZ", "600000.SH"],
        ...     start_date=date(2024, 1, 1),
        ...     end_date=date(2024, 12, 31)
        ... )
        >>> downloader.save_download_log("data_download.log")
    """

    def __init__(self, bridge_config: Optional[BridgeConfig] = None):
        """初始化数据下载器

        Args:
            bridge_config: 桥接器配置，默认使用guojin和akshare
        """
        if bridge_config is None:
            bridge_config = BridgeConfig(platforms=["guojin", "akshare"], default_platform="guojin")

        self.bridge = HistoricalBridge(bridge_config)
        self.probe_log: Optional[Dict[str, Any]] = None
        self.download_results: List[Dict[str, Any]] = []

        logger.info("DataDownloader initialized")

    def load_probe_log(self, filepath: str = "probe_discovery.json") -> None:
        """加载探针日志

        白皮书依据: 第三章 3.3.1 阶段2 - 读取探针日志

        Args:
            filepath: 探针日志文件路径

        Raises:
            FileNotFoundError: 文件不存在时
            ValueError: 文件格式错误时
        """
        try:
            filepath_obj = Path(filepath)

            if not filepath_obj.exists():
                raise FileNotFoundError(f"探针日志文件不存在: {filepath}")

            with open(filepath, "r", encoding="utf-8") as f:
                self.probe_log = json.load(f)

            logger.info(f"已加载探针日志: {self.probe_log.get('total_interfaces', 0)} 个接口")

        except Exception as e:
            logger.error(f"加载探针日志失败: {e}")
            raise

    def download_all_symbols(
        self, symbols: List[str], start_date: date, end_date: date, asset_type: AssetType = AssetType.STOCK
    ) -> Dict[str, Any]:
        """全量下载数据

        白皮书依据: 第三章 3.3.1 阶段2 - 数据下载

        Args:
            symbols: 标的代码列表
            start_date: 开始日期
            end_date: 结束日期
            asset_type: 资产类型

        Returns:
            下载结果摘要

        Raises:
            ValueError: 探针日志未加载时
        """
        if self.probe_log is None:
            raise ValueError("探针日志未加载，请先调用 load_probe_log()")

        logger.info(f"开始全量下载: {len(symbols)} 个标的, " f"{start_date} 到 {end_date}")

        start_time = time.time()
        self.download_results = []

        success_count = 0
        failed_count = 0
        fallback_count = 0

        for symbol in symbols:
            result = self._download_single_symbol(
                symbol=symbol, start_date=start_date, end_date=end_date, asset_type=asset_type
            )

            self.download_results.append(result)

            if result["status"] == "SUCCESS":
                success_count += 1
            elif result["status"] == "FAILED":
                failed_count += 1

            if result.get("fallback_used"):
                fallback_count += 1

        duration = time.time() - start_time

        summary = {
            "download_timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "trading_date": end_date.strftime("%Y-%m-%d"),
            "downloads": self.download_results,
            "summary": {
                "total_symbols": len(symbols),
                "success": success_count,
                "failed": failed_count,
                "fallback_used": fallback_count,
                "total_duration_seconds": int(duration),
            },
        }

        logger.info(
            f"下载完成: 成功 {success_count}, 失败 {failed_count}, " f"使用备用 {fallback_count}, 耗时 {duration:.1f}秒"
        )

        return summary

    def _download_single_symbol(  # pylint: disable=too-many-positional-arguments
        self, symbol: str, start_date: date, end_date: date, asset_type: AssetType, max_retries: int = 3
    ) -> Dict[str, Any]:
        """下载单个标的数据（带重试和降级）

        白皮书依据: 第三章 3.3.1 阶段2 - 下载流程

        Args:
            symbol: 标的代码
            start_date: 开始日期
            end_date: 结束日期
            asset_type: 资产类型
            max_retries: 最大重试次数

        Returns:
            下载结果字典
        """
        # 获取推荐接口
        primary_platform = self._get_primary_platform(asset_type)
        backup_platform = self._get_backup_platform(asset_type)

        result = {
            "symbol": symbol,
            "asset_type": asset_type.value,
            "interface_used": None,
            "status": "FAILED",
            "rows_downloaded": 0,
            "download_time_ms": 0,
            "data_range": {"start_date": start_date.strftime("%Y-%m-%d"), "end_date": end_date.strftime("%Y-%m-%d")},
            "error": None,
            "retry_count": 0,
            "fallback_to": None,
            "fallback_used": False,
        }

        # 尝试PRIMARY接口
        for attempt in range(max_retries):
            try:
                start_time = time.perf_counter()

                data = self.bridge.get_data(
                    symbol=symbol,
                    asset_type=asset_type,
                    platform=primary_platform,
                    start_date=start_date,
                    end_date=end_date,
                )

                elapsed_ms = (time.perf_counter() - start_time) * 1000

                result.update(
                    {
                        "interface_used": f"{primary_platform}.get_data",
                        "status": "SUCCESS",
                        "rows_downloaded": len(data),
                        "download_time_ms": int(elapsed_ms),
                    }
                )

                logger.debug(f"[{symbol}] 下载成功: {len(data)} 行, {elapsed_ms:.0f}ms")

                return result

            except Exception as e:  # pylint: disable=broad-exception-caught
                result["retry_count"] = attempt + 1
                result["error"] = str(e)

                logger.warning(f"[{symbol}] PRIMARY失败 (尝试 {attempt + 1}/{max_retries}): {e}")

                if attempt < max_retries - 1:
                    # 指数退避
                    wait_time = 2**attempt
                    time.sleep(wait_time)

        # PRIMARY失败，切换到BACKUP
        if backup_platform:
            logger.warning(f"[{symbol}] PRIMARY失败，切换到BACKUP: {backup_platform}")

            try:
                start_time = time.perf_counter()

                data = self.bridge.get_data(
                    symbol=symbol,
                    asset_type=asset_type,
                    platform=backup_platform,
                    start_date=start_date,
                    end_date=end_date,
                )

                elapsed_ms = (time.perf_counter() - start_time) * 1000

                result.update(
                    {
                        "interface_used": f"{backup_platform}.get_data",
                        "status": "SUCCESS",
                        "rows_downloaded": len(data),
                        "download_time_ms": int(elapsed_ms),
                        "fallback_to": backup_platform,
                        "fallback_used": True,
                    }
                )

                logger.info(f"[{symbol}] BACKUP成功: {len(data)} 行, {elapsed_ms:.0f}ms")

                return result

            except Exception as e:  # pylint: disable=broad-exception-caught
                result["error"] = f"PRIMARY和BACKUP都失败: {e}"
                logger.error(f"[{symbol}] BACKUP也失败: {e}")

        return result

    def _get_primary_platform(self, asset_type: AssetType) -> str:
        """获取PRIMARY平台

        Args:
            asset_type: 资产类型

        Returns:
            平台名称
        """
        if self.probe_log is None:
            return "guojin"  # 默认

        type_key = asset_type.value
        discoveries = self.probe_log.get("discoveries", {})

        if type_key in discoveries:
            primary = discoveries[type_key].get("recommended", {}).get("primary")
            if primary:
                # 格式: "guojin.get_stock_daily"
                return primary.split(".")[0]

        return "guojin"  # 默认

    def _get_backup_platform(self, asset_type: AssetType) -> Optional[str]:
        """获取BACKUP平台

        Args:
            asset_type: 资产类型

        Returns:
            平台名称或None
        """
        if self.probe_log is None:
            return "akshare"  # 默认

        type_key = asset_type.value
        discoveries = self.probe_log.get("discoveries", {})

        if type_key in discoveries:
            backup = discoveries[type_key].get("recommended", {}).get("backup")
            if backup:
                # 格式: "akshare.stock_zh_a_hist"
                return backup.split(".")[0]

        return "akshare"  # 默认

    def save_download_log(self, filepath: str = "data_download.log") -> None:
        """保存下载日志

        白皮书依据: 第三章 3.3.1 阶段2 - 生成下载日志

        Args:
            filepath: 日志文件路径

        Raises:
            ValueError: 没有下载结果时
        """
        if not self.download_results:
            raise ValueError("没有下载结果，请先调用 download_all_symbols()")

        try:
            # 构建下载日志
            success_count = sum(1 for r in self.download_results if r["status"] == "SUCCESS")
            failed_count = len(self.download_results) - success_count
            fallback_count = sum(1 for r in self.download_results if r.get("fallback_used", False))

            download_log = {
                "download_timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "trading_date": datetime.now().strftime("%Y-%m-%d"),
                "downloads": self.download_results,
                "summary": {
                    "total_symbols": len(self.download_results),
                    "success": success_count,
                    "failed": failed_count,
                    "fallback_used": fallback_count,
                    "total_duration_seconds": 0,  # 简化处理
                },
            }

            # 保存到文件
            filepath_obj = Path(filepath)
            filepath_obj.parent.mkdir(parents=True, exist_ok=True)

            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(download_log, f, indent=2, ensure_ascii=False)

            logger.info(f"下载日志已保存到: {filepath} " f"(成功: {success_count}, 失败: {failed_count})")

        except Exception as e:
            logger.error(f"保存下载日志失败: {e}")
            raise IOError(f"无法保存下载日志到 {filepath}: {e}") from e
