"""历史数据注入桥接器

白皮书依据: 第三章 3.4 历史数据注入桥接器

实现平台无关的数据访问抽象层，支持国金和akshare等多个数据平台。
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date
from enum import Enum
from typing import Any, Dict, List, Optional

import pandas as pd
from loguru import logger


class AssetType(Enum):
    """资产类型枚举

    白皮书依据: 第三章 3.4
    """

    STOCK = "stock"
    FUTURES = "futures"
    OPTIONS = "options"
    FUND = "fund"
    INDEX = "index"


@dataclass
class InterfaceInfo:
    """接口信息

    Attributes:
        platform: 平台名称
        interface_name: 接口名称
        asset_type: 资产类型
        endpoint: 接口端点
        supported_params: 支持的参数列表
        quality_score: 质量评分 (0-100)
    """

    platform: str
    interface_name: str
    asset_type: AssetType
    endpoint: str
    supported_params: List[str]
    quality_score: float = 0.0


@dataclass
class InterfaceTestResult:
    """接口测试结果

    Attributes:
        interface: 接口名称
        success: 是否成功
        latency_ms: 延迟(毫秒)
        coverage: 覆盖率 (0-1)
        rows_returned: 返回行数
        error: 错误信息
    """

    interface: str
    success: bool
    latency_ms: float = 0.0
    coverage: float = 0.0
    rows_returned: int = 0
    error: Optional[str] = None


# 异常定义


class PlatformError(Exception):
    """平台错误基类"""


class GuojinAPIError(PlatformError):
    """国金API错误"""


class AkshareError(PlatformError):
    """Akshare错误"""


class DataFormatError(Exception):
    """数据格式错误"""


class ConfigurationError(Exception):
    """配置错误"""


# 平台适配器接口


class PlatformAdapter(ABC):
    """平台适配器抽象基类

    白皮书依据: 第三章 3.4 历史数据注入桥接器

    所有数据平台适配器必须实现此接口。
    """

    @abstractmethod
    def discover_interfaces(self) -> List[InterfaceInfo]:
        """发现平台上的可用接口

        Returns:
            发现的接口信息列表
        """

    @abstractmethod
    def download_data(self, interface: str, symbol: str, start_date: date, end_date: date) -> pd.DataFrame:
        """使用指定接口下载数据

        Args:
            interface: 接口名称
            symbol: 标的代码
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            原始数据DataFrame

        Raises:
            PlatformError: 平台特定错误
        """

    @abstractmethod
    def test_interface(self, interface: str) -> InterfaceTestResult:
        """测试接口质量和性能

        Args:
            interface: 接口名称

        Returns:
            测试结果，包含延迟、覆盖率、可靠性
        """


class GuojinAdapter(PlatformAdapter):
    """国金数据平台适配器

    白皮书依据: 第三章 3.4
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """初始化国金适配器

        Args:
            config: 国金特定配置
        """
        self.config = config or {}
        logger.info("GuojinAdapter initialized")

    def discover_interfaces(self) -> List[InterfaceInfo]:
        """发现国金平台接口

        Returns:
            可用接口列表
        """
        logger.info("Discovering Guojin interfaces...")

        interfaces = [
            InterfaceInfo(
                platform="guojin",
                interface_name="get_stock_daily",
                asset_type=AssetType.STOCK,
                endpoint="/api/stock/daily",
                supported_params=["symbol", "start_date", "end_date"],
                quality_score=95.0,
            ),
            InterfaceInfo(
                platform="guojin",
                interface_name="get_stock_minute",
                asset_type=AssetType.STOCK,
                endpoint="/api/stock/minute",
                supported_params=["symbol", "start_date", "end_date", "frequency"],
                quality_score=92.0,
            ),
            InterfaceInfo(
                platform="guojin",
                interface_name="get_futures_daily",
                asset_type=AssetType.FUTURES,
                endpoint="/api/futures/daily",
                supported_params=["symbol", "start_date", "end_date"],
                quality_score=93.0,
            ),
            InterfaceInfo(
                platform="guojin",
                interface_name="get_options_daily",
                asset_type=AssetType.OPTIONS,
                endpoint="/api/options/daily",
                supported_params=["symbol", "start_date", "end_date"],
                quality_score=90.0,
            ),
            InterfaceInfo(
                platform="guojin",
                interface_name="get_fund_nav",
                asset_type=AssetType.FUND,
                endpoint="/api/fund/nav",
                supported_params=["symbol", "start_date", "end_date"],
                quality_score=91.0,
            ),
            InterfaceInfo(
                platform="guojin",
                interface_name="get_index_daily",
                asset_type=AssetType.INDEX,
                endpoint="/api/index/daily",
                supported_params=["symbol", "start_date", "end_date"],
                quality_score=94.0,
            ),
        ]

        logger.info(f"Discovered {len(interfaces)} Guojin interfaces")
        return interfaces

    def download_data(self, interface: str, symbol: str, start_date: date, end_date: date) -> pd.DataFrame:
        """从国金下载数据

        Args:
            interface: 国金接口名称
            symbol: 股票/期货代码
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            原始DataFrame

        Raises:
            GuojinAPIError: API调用失败
        """
        logger.info(f"Downloading from Guojin: {interface}, {symbol}, {start_date} to {end_date}")

        try:
            # 模拟国金API调用
            # 实际实现中会调用真实的国金API
            import random  # pylint: disable=import-outside-toplevel
            import time  # pylint: disable=import-outside-toplevel

            # 模拟网络延迟
            time.sleep(random.uniform(0.05, 0.2))

            # 模拟成功率
            if random.random() < 0.05:  # 5%失败率
                raise GuojinAPIError(f"Simulated API failure for {interface}")

            # 生成模拟数据
            (end_date - start_date).days + 1  # pylint: disable=w0104
            dates = pd.date_range(start=start_date, end=end_date, freq="D")

            data = pd.DataFrame(
                {
                    "date": dates,
                    "symbol": [symbol] * len(dates),
                    "open": [100 + random.random() * 10 for _ in range(len(dates))],
                    "high": [105 + random.random() * 10 for _ in range(len(dates))],
                    "low": [95 + random.random() * 10 for _ in range(len(dates))],
                    "close": [100 + random.random() * 10 for _ in range(len(dates))],
                    "volume": [random.randint(1000000, 10000000) for _ in range(len(dates))],
                }
            )

            logger.info(f"Downloaded {len(data)} rows from Guojin")
            return data

        except Exception as e:
            logger.error(f"Guojin download failed: {e}")
            raise GuojinAPIError(f"Failed to download from {interface}: {e}") from e

    def test_interface(self, interface: str) -> InterfaceTestResult:
        """测试国金接口质量

        Args:
            interface: 接口名称

        Returns:
            测试结果
        """
        import time  # pylint: disable=import-outside-toplevel
        from datetime import timedelta  # pylint: disable=import-outside-toplevel

        start_time = time.perf_counter()

        try:
            # 使用样本代码测试
            test_symbol = "000001.SZ"
            test_end = date.today()
            test_start = test_end - timedelta(days=30)

            data = self.download_data(interface, test_symbol, test_start, test_end)

            latency_ms = (time.perf_counter() - start_time) * 1000
            coverage = min(len(data) / 20, 1.0)  # 预期30天约20个交易日

            return InterfaceTestResult(
                interface=interface, success=True, latency_ms=latency_ms, coverage=coverage, rows_returned=len(data)
            )

        except Exception as e:  # pylint: disable=broad-exception-caught
            return InterfaceTestResult(interface=interface, success=False, error=str(e))


class AkshareAdapter(PlatformAdapter):
    """Akshare数据平台适配器

    白皮书依据: 第三章 3.4
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """初始化Akshare适配器

        Args:
            config: Akshare特定配置
        """
        self.config = config or {}
        logger.info("AkshareAdapter initialized")

    def discover_interfaces(self) -> List[InterfaceInfo]:
        """发现Akshare平台接口

        Returns:
            可用接口列表
        """
        logger.info("Discovering Akshare interfaces...")

        interfaces = [
            InterfaceInfo(
                platform="akshare",
                interface_name="stock_zh_a_hist",
                asset_type=AssetType.STOCK,
                endpoint="stock_zh_a_hist",
                supported_params=["symbol", "start_date", "end_date", "adjust"],
                quality_score=88.0,
            ),
            InterfaceInfo(
                platform="akshare",
                interface_name="stock_zh_a_minute",
                asset_type=AssetType.STOCK,
                endpoint="stock_zh_a_minute",
                supported_params=["symbol", "period", "adjust"],
                quality_score=85.0,
            ),
            InterfaceInfo(
                platform="akshare",
                interface_name="futures_zh_hist",
                asset_type=AssetType.FUTURES,
                endpoint="futures_zh_hist",
                supported_params=["symbol", "start_date", "end_date"],
                quality_score=86.0,
            ),
            InterfaceInfo(
                platform="akshare",
                interface_name="option_finance_board",
                asset_type=AssetType.OPTIONS,
                endpoint="option_finance_board",
                supported_params=["symbol"],
                quality_score=82.0,
            ),
            InterfaceInfo(
                platform="akshare",
                interface_name="fund_etf_hist_sina",
                asset_type=AssetType.FUND,
                endpoint="fund_etf_hist_sina",
                supported_params=["symbol", "start_date", "end_date"],
                quality_score=84.0,
            ),
            InterfaceInfo(
                platform="akshare",
                interface_name="stock_zh_index_daily",
                asset_type=AssetType.INDEX,
                endpoint="stock_zh_index_daily",
                supported_params=["symbol"],
                quality_score=87.0,
            ),
        ]

        logger.info(f"Discovered {len(interfaces)} Akshare interfaces")
        return interfaces

    def download_data(self, interface: str, symbol: str, start_date: date, end_date: date) -> pd.DataFrame:
        """从Akshare下载数据

        Args:
            interface: Akshare函数名
            symbol: 股票/期货代码
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            原始DataFrame

        Raises:
            AkshareError: Akshare调用失败
        """
        logger.info(f"Downloading from Akshare: {interface}, {symbol}, {start_date} to {end_date}")

        try:
            # 模拟Akshare调用
            # 实际实现中会调用真实的akshare库
            import random  # pylint: disable=import-outside-toplevel
            import time  # pylint: disable=import-outside-toplevel

            # 模拟网络延迟
            time.sleep(random.uniform(0.1, 0.3))

            # 模拟成功率
            if random.random() < 0.15:  # 15%失败率（比国金高）
                raise AkshareError(f"Simulated Akshare failure for {interface}")

            # 生成模拟数据
            dates = pd.date_range(start=start_date, end=end_date, freq="D")

            data = pd.DataFrame(
                {
                    "日期": dates,
                    "股票代码": [symbol] * len(dates),
                    "开盘": [100 + random.random() * 10 for _ in range(len(dates))],
                    "最高": [105 + random.random() * 10 for _ in range(len(dates))],
                    "最低": [95 + random.random() * 10 for _ in range(len(dates))],
                    "收盘": [100 + random.random() * 10 for _ in range(len(dates))],
                    "成交量": [random.randint(1000000, 10000000) for _ in range(len(dates))],
                }
            )

            logger.info(f"Downloaded {len(data)} rows from Akshare")
            return data

        except Exception as e:
            logger.error(f"Akshare download failed: {e}")
            raise AkshareError(f"Failed to download from {interface}: {e}") from e

    def test_interface(self, interface: str) -> InterfaceTestResult:
        """测试Akshare接口质量

        Args:
            interface: 接口名称

        Returns:
            测试结果
        """
        import time  # pylint: disable=import-outside-toplevel
        from datetime import timedelta  # pylint: disable=import-outside-toplevel

        start_time = time.perf_counter()

        try:
            # 使用样本代码测试（Akshare使用不同格式）
            test_symbol = "000001"
            test_end = date.today()
            test_start = test_end - timedelta(days=30)

            data = self.download_data(interface, test_symbol, test_start, test_end)

            latency_ms = (time.perf_counter() - start_time) * 1000
            coverage = min(len(data) / 20, 1.0)

            return InterfaceTestResult(
                interface=interface, success=True, latency_ms=latency_ms, coverage=coverage, rows_returned=len(data)
            )

        except Exception as e:  # pylint: disable=broad-exception-caught
            return InterfaceTestResult(interface=interface, success=False, error=str(e))


class DataNormalizer:
    """数据标准化器

    白皮书依据: 第三章 3.4

    将不同平台的数据格式标准化为统一格式。
    """

    def normalize_symbol(self, symbol: str, platform: str) -> str:
        """标准化标的代码

        Args:
            symbol: 平台特定的标的代码
            platform: 源平台名称

        Returns:
            标准化的标的代码 (格式: XXXXXX.XX)

        Example:
            >>> normalizer = DataNormalizer()
            >>> normalizer.normalize_symbol("000001", "akshare")
            '000001.SZ'
            >>> normalizer.normalize_symbol("000001.SZ", "guojin")
            '000001.SZ'
        """
        if platform == "akshare":  # pylint: disable=no-else-return
            # Akshare使用6位代码，需要添加交易所后缀
            if len(symbol) == 6 and "." not in symbol:
                # 判断交易所
                if symbol.startswith("6"):  # pylint: disable=no-else-return
                    return f"{symbol}.SH"  # 上交所
                else:
                    return f"{symbol}.SZ"  # 深交所
            return symbol

        elif platform == "guojin":
            # 国金已经使用标准格式
            return symbol

        else:
            # 未知平台，返回原样
            logger.warning(f"Unknown platform: {platform}, returning symbol as-is")
            return symbol

    def normalize_dataframe(self, df: pd.DataFrame, platform: str) -> pd.DataFrame:
        """标准化DataFrame格式

        Args:
            df: 原始DataFrame
            platform: 源平台名称

        Returns:
            标准化的DataFrame，列名和数据类型统一

        Raises:
            DataFormatError: 数据格式无法标准化
        """
        if df.empty:
            raise DataFormatError("Cannot normalize empty DataFrame")

        try:
            normalized = df.copy()

            # 标准化列名
            column_mapping = self._get_column_mapping(platform)
            normalized = normalized.rename(columns=column_mapping)

            # 确保必需列存在
            required_columns = ["date", "open", "high", "low", "close", "volume"]
            missing_columns = set(required_columns) - set(normalized.columns)

            if missing_columns:
                raise DataFormatError(f"Missing required columns: {missing_columns}")

            # 标准化数据类型
            normalized["date"] = pd.to_datetime(normalized["date"])
            normalized["open"] = pd.to_numeric(normalized["open"], errors="coerce")
            normalized["high"] = pd.to_numeric(normalized["high"], errors="coerce")
            normalized["low"] = pd.to_numeric(normalized["low"], errors="coerce")
            normalized["close"] = pd.to_numeric(normalized["close"], errors="coerce")
            normalized["volume"] = pd.to_numeric(normalized["volume"], errors="coerce")

            # 设置日期为索引
            normalized = normalized.set_index("date")
            normalized = normalized.sort_index()

            # 只保留标准列
            normalized = normalized[["open", "high", "low", "close", "volume"]]

            logger.info(f"Normalized DataFrame: {len(normalized)} rows, {len(normalized.columns)} columns")
            return normalized

        except Exception as e:
            raise DataFormatError(f"Failed to normalize DataFrame: {e}") from e

    def _get_column_mapping(self, platform: str) -> Dict[str, str]:
        """获取平台特定的列名映射

        Args:
            platform: 平台名称

        Returns:
            列名映射字典
        """
        if platform == "akshare":  # pylint: disable=no-else-return
            return {
                "日期": "date",
                "开盘": "open",
                "最高": "high",
                "最低": "low",
                "收盘": "close",
                "成交量": "volume",
                "股票代码": "symbol",
            }
        elif platform == "guojin":
            return {
                "date": "date",
                "open": "open",
                "high": "high",
                "low": "low",
                "close": "close",
                "volume": "volume",
                "symbol": "symbol",
            }
        else:
            return {}


@dataclass
class BridgeConfig:
    """桥接器配置

    Attributes:
        platforms: 启用的平台列表
        default_platform: 默认平台
        timeout_seconds: 超时时间(秒)
    """

    platforms: List[str]
    default_platform: str = "guojin"
    timeout_seconds: int = 30


class HistoricalBridge:
    """历史数据注入桥接器

    白皮书依据: 第三章 3.4 历史数据注入桥接器

    提供统一的接口访问多个数据平台的历史数据。

    Attributes:
        config: 桥接器配置
        adapters: 平台适配器字典
        normalizer: 数据标准化器

    Example:
        >>> config = BridgeConfig(platforms=["guojin", "akshare"])
        >>> bridge = HistoricalBridge(config)
        >>> data = bridge.get_data(
        ...     symbol="000001.SZ",
        ...     asset_type=AssetType.STOCK,
        ...     platform="guojin",
        ...     start_date=date(2024, 1, 1),
        ...     end_date=date(2024, 1, 31)
        ... )
    """

    def __init__(self, config: BridgeConfig):
        """初始化历史桥接器

        Args:
            config: 桥接器配置

        Raises:
            ConfigurationError: 配置无效
        """
        if not config.platforms:
            raise ConfigurationError("至少需要配置一个平台")

        if config.default_platform not in config.platforms:
            raise ConfigurationError(f"Default platform '{config.default_platform}' not in platforms list")

        self.config = config
        self.adapters = self._initialize_adapters()
        self.normalizer = DataNormalizer()

        logger.info(
            f"HistoricalBridge initialized with platforms: {config.platforms}, " f"default: {config.default_platform}"
        )

    def _initialize_adapters(self) -> Dict[str, PlatformAdapter]:
        """初始化平台适配器

        Returns:
            平台适配器字典
        """
        adapters = {}

        for platform in self.config.platforms:
            if platform == "guojin":
                adapters[platform] = GuojinAdapter()
            elif platform == "akshare":
                adapters[platform] = AkshareAdapter()
            else:
                logger.warning(f"Unknown platform: {platform}, skipping")

        logger.info(f"Initialized {len(adapters)} platform adapters")
        return adapters

    def get_data(  # pylint: disable=too-many-positional-arguments
        self, symbol: str, asset_type: AssetType, platform: str, start_date: date, end_date: date
    ) -> pd.DataFrame:
        """从指定平台获取历史数据

        白皮书依据: 第三章 3.4

        Args:
            symbol: 标的代码
            asset_type: 资产类型
            platform: 平台名称
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            标准化的DataFrame

        Raises:
            PlatformError: 平台特定错误
            DataFormatError: 数据无法标准化
            ConfigurationError: 平台未配置
        """
        if platform not in self.adapters:
            raise ConfigurationError(f"平台 '{platform}' 未配置")

        logger.info(f"Getting data: {symbol} ({asset_type.value}) from {platform}, " f"{start_date} to {end_date}")

        try:
            # 标准化标的代码
            normalized_symbol = self.normalizer.normalize_symbol(symbol, platform)

            # 获取适配器
            adapter = self.adapters[platform]

            # 选择合适的接口
            interface = self._select_interface(adapter, asset_type)

            # 下载数据
            raw_data = adapter.download_data(
                interface=interface, symbol=normalized_symbol, start_date=start_date, end_date=end_date
            )

            # 标准化数据
            normalized_data = self.normalizer.normalize_dataframe(raw_data, platform)

            logger.info(f"Successfully retrieved {len(normalized_data)} rows")
            return normalized_data

        except PlatformError:
            raise
        except Exception as e:
            logger.error(f"Failed to get data: {e}")
            raise PlatformError(f"Failed to get data from {platform}: {e}") from e

    def _select_interface(self, adapter: PlatformAdapter, asset_type: AssetType) -> str:
        """选择合适的接口

        Args:
            adapter: 平台适配器
            asset_type: 资产类型

        Returns:
            接口名称

        Raises:
            ConfigurationError: 没有找到合适的接口
        """
        interfaces = adapter.discover_interfaces()

        # 筛选匹配资产类型的接口
        matching = [iface for iface in interfaces if iface.asset_type == asset_type]

        if not matching:
            raise ConfigurationError(f"No interface found for asset type {asset_type.value}")

        # 选择质量评分最高的接口
        best = max(matching, key=lambda x: x.quality_score)

        logger.info(f"Selected interface: {best.interface_name} (score: {best.quality_score})")
        return best.interface_name

    def normalize_symbol(self, symbol: str, platform: str) -> str:
        """标准化标的代码

        Args:
            symbol: 平台特定的标的代码
            platform: 源平台名称

        Returns:
            标准化的标的代码
        """
        return self.normalizer.normalize_symbol(symbol, platform)

    def get_available_platforms(self) -> List[str]:
        """获取可用平台列表

        Returns:
            平台名称列表
        """
        return list(self.adapters.keys())

    def test_platform(self, platform: str) -> Dict[str, InterfaceTestResult]:
        """测试平台的所有接口

        Args:
            platform: 平台名称

        Returns:
            接口测试结果字典

        Raises:
            ConfigurationError: 平台未配置
        """
        if platform not in self.adapters:
            raise ConfigurationError(f"平台 '{platform}' 未配置")

        logger.info(f"Testing platform: {platform}")

        adapter = self.adapters[platform]
        interfaces = adapter.discover_interfaces()

        results = {}
        for interface_info in interfaces:
            result = adapter.test_interface(interface_info.interface_name)
            results[interface_info.interface_name] = result

        logger.info(f"Tested {len(results)} interfaces on {platform}")
        return results
