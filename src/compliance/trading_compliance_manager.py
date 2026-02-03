"""交易合规管理器

白皮书依据: 第七章 7.3 合规体系

TradingComplianceManager负责检查交易是否符合合规要求，包括：
- 单日交易次数限制（≤200笔）
- 单笔交易金额限制（≤100万元）
- ST股票禁止交易
- 停牌股票禁止交易
- 新股限制（上市不足5天）
- 衍生品保证金比例限制（<30%）

特性：
- 多维度合规检查
- 审计日志记录
- Redis缓存支持
- 实时股票信息查询
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Set

from loguru import logger

from src.compliance.data_models import (
    ComplianceCheckType,
    ComplianceViolation,
    StockInfo,
    TradeOrder,
)


class ComplianceError(Exception):
    """合规错误

    白皮书依据: 第七章 7.3 合规体系

    Attributes:
        violations: 违规列表
    """

    def __init__(self, message: str, violations: List[ComplianceViolation] = None):
        """初始化合规错误

        Args:
            message: 错误消息
            violations: 违规列表
        """
        super().__init__(message)
        self.violations = violations or []


@dataclass
class ComplianceCheckResult:
    """合规检查结果

    白皮书依据: 第七章 7.3 合规体系

    Attributes:
        passed: 是否通过
        violations: 违规列表
        checked_at: 检查时间
    """

    passed: bool
    violations: List[ComplianceViolation] = field(default_factory=list)
    checked_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "passed": self.passed,
            "violations": [v.to_dict() for v in self.violations],
            "checked_at": self.checked_at,
        }


class TradingComplianceManager:
    """交易合规管理器

    白皮书依据: 第七章 7.3 合规体系

    检查交易是否符合合规要求，包括日交易次数、单笔金额、
    ST股票、停牌股票、新股、保证金比例等限制。

    Attributes:
        daily_trade_limit: 单日交易次数限制（默认200）
        single_trade_limit: 单笔交易金额限制（默认100万元）
        new_stock_days: 新股限制天数（默认5天）
        margin_ratio_limit: 衍生品保证金比例限制（默认30%）
        redis_client: Redis客户端
        stock_info_provider: 股票信息提供者
        audit_logger: 审计日志记录器
    """

    REDIS_KEY_TRADE_COUNT = "mia:compliance:trade_count"
    REDIS_KEY_MARGIN = "mia:compliance:margin"

    def __init__(  # pylint: disable=too-many-positional-arguments
        self,
        daily_trade_limit: int = 200,
        single_trade_limit: float = 1_000_000.0,
        new_stock_days: int = 5,
        margin_ratio_limit: float = 0.30,
        redis_client: Optional[Any] = None,
        stock_info_provider: Optional[Any] = None,
        audit_logger: Optional[Any] = None,
    ):
        """初始化TradingComplianceManager

        白皮书依据: 第七章 7.3 合规体系

        Args:
            daily_trade_limit: 单日交易次数限制，默认200
            single_trade_limit: 单笔交易金额限制（元），默认100万
            new_stock_days: 新股限制天数，默认5天
            margin_ratio_limit: 衍生品保证金比例限制，默认30%
            redis_client: Redis客户端，用于存储交易计数
            stock_info_provider: 股票信息提供者，用于查询ST/停牌/上市日期
            audit_logger: 审计日志记录器

        Raises:
            ValueError: 当参数无效时
        """
        # 参数验证
        if daily_trade_limit <= 0:
            raise ValueError(f"日交易次数限制必须大于0，当前值: {daily_trade_limit}")

        if single_trade_limit <= 0:
            raise ValueError(f"单笔交易金额限制必须大于0，当前值: {single_trade_limit}")

        if new_stock_days < 0:
            raise ValueError(f"新股限制天数不能为负，当前值: {new_stock_days}")

        if not 0 < margin_ratio_limit <= 1:
            raise ValueError(f"保证金比例限制必须在(0, 1]范围内，当前值: {margin_ratio_limit}")

        self.daily_trade_limit = daily_trade_limit
        self.single_trade_limit = single_trade_limit
        self.new_stock_days = new_stock_days
        self.margin_ratio_limit = margin_ratio_limit
        self.redis_client = redis_client
        self.stock_info_provider = stock_info_provider
        self.audit_logger = audit_logger

        # 内存缓存（当Redis不可用时使用）
        self._trade_count_cache: Dict[str, int] = {}
        self._margin_cache: float = 0.0
        self._st_blacklist: Set[str] = set()
        self._suspended_set: Set[str] = set()
        self._stock_info_cache: Dict[str, StockInfo] = {}

        logger.info(
            f"TradingComplianceManager初始化完成: "
            f"daily_limit={daily_trade_limit}, "
            f"single_limit={single_trade_limit}, "
            f"new_stock_days={new_stock_days}, "
            f"margin_limit={margin_ratio_limit}"
        )

    def check_trade_compliance(self, order: TradeOrder) -> ComplianceCheckResult:
        """检查交易合规性

        白皮书依据: 第七章 7.3 合规体系

        执行所有合规检查，返回检查结果。

        Args:
            order: 交易订单

        Returns:
            合规检查结果

        Raises:
            ComplianceError: 当合规检查失败时
        """
        violations: List[ComplianceViolation] = []

        # 1. 检查日交易次数
        daily_check = self._check_daily_limit()
        if not daily_check["passed"]:
            violations.append(
                ComplianceViolation(
                    check_type=ComplianceCheckType.DAILY_TRADE_LIMIT,
                    message=daily_check["message"],
                    details=daily_check["details"],
                )
            )

        # 2. 检查单笔金额
        amount_check = self._check_single_amount(order)
        if not amount_check["passed"]:
            violations.append(
                ComplianceViolation(
                    check_type=ComplianceCheckType.SINGLE_TRADE_AMOUNT,
                    message=amount_check["message"],
                    details=amount_check["details"],
                )
            )

        # 3. 检查ST股票
        st_check = self._check_st_stock(order.symbol)
        if not st_check["passed"]:
            violations.append(
                ComplianceViolation(
                    check_type=ComplianceCheckType.ST_STOCK, message=st_check["message"], details=st_check["details"]
                )
            )

        # 4. 检查停牌股票
        suspended_check = self._check_suspended_stock(order.symbol)
        if not suspended_check["passed"]:
            violations.append(
                ComplianceViolation(
                    check_type=ComplianceCheckType.SUSPENDED_STOCK,
                    message=suspended_check["message"],
                    details=suspended_check["details"],
                )
            )

        # 5. 检查新股
        new_stock_check = self._check_new_stock(order.symbol)
        if not new_stock_check["passed"]:
            violations.append(
                ComplianceViolation(
                    check_type=ComplianceCheckType.NEW_STOCK,
                    message=new_stock_check["message"],
                    details=new_stock_check["details"],
                )
            )

        # 6. 检查保证金（仅衍生品）
        if order.is_derivative:
            margin_check = self._check_margin_ratio()
            if not margin_check["passed"]:
                violations.append(
                    ComplianceViolation(
                        check_type=ComplianceCheckType.MARGIN_RATIO,
                        message=margin_check["message"],
                        details=margin_check["details"],
                    )
                )

        # 构建结果
        passed = len(violations) == 0
        result = ComplianceCheckResult(passed=passed, violations=violations)

        # 记录审计日志
        self._log_compliance_check(order, result)

        # 如果检查失败，抛出异常
        if not passed:
            violation_messages = [v.message for v in violations]
            raise ComplianceError(f"合规检查失败: {'; '.join(violation_messages)}", violations=violations)

        # 检查通过，增加交易计数
        self._increment_trade_count()

        logger.debug(f"合规检查通过: {order.symbol}, amount={order.amount}")
        return result

    def _check_daily_limit(self) -> Dict[str, Any]:
        """检查单日交易次数

        白皮书依据: 第七章 7.3 合规体系

        Returns:
            检查结果字典，包含passed, message, details
        """
        today = datetime.now().strftime("%Y%m%d")
        trade_count = self._get_trade_count(today)

        if trade_count >= self.daily_trade_limit:
            return {
                "passed": False,
                "message": f"单日交易次数超限: {trade_count}/{self.daily_trade_limit}",
                "details": {"current_count": trade_count, "limit": self.daily_trade_limit, "date": today},
            }

        return {
            "passed": True,
            "message": "",
            "details": {"current_count": trade_count, "limit": self.daily_trade_limit},
        }

    def _check_single_amount(self, order: TradeOrder) -> Dict[str, Any]:
        """检查单笔交易金额

        白皮书依据: 第七章 7.3 合规体系

        Args:
            order: 交易订单

        Returns:
            检查结果字典
        """
        amount = order.amount

        if amount > self.single_trade_limit:
            return {
                "passed": False,
                "message": f"单笔交易金额超限: {amount:.2f}/{self.single_trade_limit:.2f}",
                "details": {"amount": amount, "limit": self.single_trade_limit, "symbol": order.symbol},
            }

        return {"passed": True, "message": "", "details": {"amount": amount, "limit": self.single_trade_limit}}

    def _check_st_stock(self, symbol: str) -> Dict[str, Any]:
        """检查是否为ST股票

        白皮书依据: 第七章 7.3 合规体系

        Args:
            symbol: 股票代码

        Returns:
            检查结果字典
        """
        stock_info = self._get_stock_info(symbol)

        if stock_info and stock_info.is_st:
            return {
                "passed": False,
                "message": f"禁止交易ST股票: {symbol}",
                "details": {"symbol": symbol, "name": stock_info.name, "is_st": True},
            }

        # 检查内存黑名单
        if symbol in self._st_blacklist:
            return {
                "passed": False,
                "message": f"禁止交易ST股票: {symbol}",
                "details": {"symbol": symbol, "is_st": True, "source": "blacklist"},
            }

        return {"passed": True, "message": "", "details": {"symbol": symbol, "is_st": False}}

    def _check_suspended_stock(self, symbol: str) -> Dict[str, Any]:
        """检查是否为停牌股票

        白皮书依据: 第七章 7.3 合规体系

        Args:
            symbol: 股票代码

        Returns:
            检查结果字典
        """
        stock_info = self._get_stock_info(symbol)

        if stock_info and stock_info.is_suspended:
            return {
                "passed": False,
                "message": f"禁止交易停牌股票: {symbol}",
                "details": {"symbol": symbol, "name": stock_info.name, "is_suspended": True},
            }

        # 检查内存停牌集合
        if symbol in self._suspended_set:
            return {
                "passed": False,
                "message": f"禁止交易停牌股票: {symbol}",
                "details": {"symbol": symbol, "is_suspended": True, "source": "suspended_set"},
            }

        return {"passed": True, "message": "", "details": {"symbol": symbol, "is_suspended": False}}

    def _check_new_stock(self, symbol: str) -> Dict[str, Any]:
        """检查是否为新股（上市不足指定天数）

        白皮书依据: 第七章 7.3 合规体系

        Args:
            symbol: 股票代码

        Returns:
            检查结果字典
        """
        stock_info = self._get_stock_info(symbol)

        if stock_info and stock_info.list_date:
            days_since_listing = stock_info.days_since_listing()

            if days_since_listing < self.new_stock_days:
                return {
                    "passed": False,
                    "message": f"禁止交易新股: {symbol}上市仅{days_since_listing}天",
                    "details": {
                        "symbol": symbol,
                        "days_since_listing": days_since_listing,
                        "required_days": self.new_stock_days,
                        "list_date": stock_info.list_date.isoformat(),
                    },
                }

        return {"passed": True, "message": "", "details": {"symbol": symbol, "is_new_stock": False}}

    def _check_margin_ratio(self) -> Dict[str, Any]:
        """检查衍生品保证金比例

        白皮书依据: 第七章 7.3 合规体系

        Returns:
            检查结果字典
        """
        margin_ratio = self._get_margin_ratio()

        if margin_ratio >= self.margin_ratio_limit:
            return {
                "passed": False,
                "message": f"衍生品保证金比例超限: {margin_ratio:.2%}/{self.margin_ratio_limit:.2%}",
                "details": {"current_ratio": margin_ratio, "limit": self.margin_ratio_limit},
            }

        return {
            "passed": True,
            "message": "",
            "details": {"current_ratio": margin_ratio, "limit": self.margin_ratio_limit},
        }

    def _get_trade_count(self, date: str) -> int:
        """获取指定日期的交易次数

        Args:
            date: 日期字符串（YYYYMMDD格式）

        Returns:
            交易次数
        """
        if self.redis_client:
            try:
                key = f"{self.REDIS_KEY_TRADE_COUNT}:{date}"
                count = self.redis_client.get(key)
                if count:
                    if isinstance(count, bytes):
                        count = count.decode("utf-8")
                    return int(count)
                return 0
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.warning(f"从Redis获取交易次数失败: {e}")

        # 使用内存缓存
        return self._trade_count_cache.get(date, 0)

    def _increment_trade_count(self) -> None:
        """增加当日交易次数"""
        today = datetime.now().strftime("%Y%m%d")

        if self.redis_client:
            try:
                key = f"{self.REDIS_KEY_TRADE_COUNT}:{today}"
                self.redis_client.incr(key)
                # 设置过期时间为2天
                self.redis_client.expire(key, 172800)
                return
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.warning(f"Redis增加交易次数失败: {e}")

        # 使用内存缓存
        self._trade_count_cache[today] = self._trade_count_cache.get(today, 0) + 1

    def _get_stock_info(self, symbol: str) -> Optional[StockInfo]:
        """获取股票信息

        Args:
            symbol: 股票代码

        Returns:
            股票信息，如果不存在返回None
        """
        # 先检查缓存
        if symbol in self._stock_info_cache:
            return self._stock_info_cache[symbol]

        # 从提供者获取
        if self.stock_info_provider:
            try:
                info = self.stock_info_provider.get_stock_info(symbol)
                if info:
                    stock_info = StockInfo(
                        symbol=info.get("symbol", symbol),
                        name=info.get("name", ""),
                        is_st=info.get("is_st", False),
                        is_suspended=info.get("is_suspended", False),
                        list_date=datetime.fromisoformat(info["list_date"]) if info.get("list_date") else None,
                    )
                    self._stock_info_cache[symbol] = stock_info
                    return stock_info
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.warning(f"获取股票信息失败: {symbol}, {e}")

        return None

    def _get_margin_ratio(self) -> float:
        """获取当前衍生品保证金比例

        Returns:
            保证金比例（0-1之间）
        """
        if self.redis_client:
            try:
                ratio = self.redis_client.get(self.REDIS_KEY_MARGIN)
                if ratio:
                    if isinstance(ratio, bytes):
                        ratio = ratio.decode("utf-8")
                    return float(ratio)
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.warning(f"从Redis获取保证金比例失败: {e}")

        return self._margin_cache

    def _log_compliance_check(self, order: TradeOrder, result: ComplianceCheckResult) -> None:
        """记录合规检查到审计日志

        Args:
            order: 交易订单
            result: 检查结果
        """
        if self.audit_logger is None:
            return

        try:
            self.audit_logger.log_event(
                {
                    "event_type": "COMPLIANCE_CHECK",
                    "order": order.to_dict(),
                    "result": result.to_dict(),
                    "passed": result.passed,
                    "violations_count": len(result.violations),
                }
            )
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.warning(f"记录合规检查审计日志失败: {e}")

    # ========== 管理方法 ==========

    def add_st_stock(self, symbol: str) -> None:
        """添加ST股票到黑名单

        Args:
            symbol: 股票代码
        """
        self._st_blacklist.add(symbol)
        logger.info(f"添加ST股票到黑名单: {symbol}")

    def remove_st_stock(self, symbol: str) -> None:
        """从黑名单移除ST股票

        Args:
            symbol: 股票代码
        """
        self._st_blacklist.discard(symbol)
        logger.info(f"从黑名单移除ST股票: {symbol}")

    def add_suspended_stock(self, symbol: str) -> None:
        """添加停牌股票

        Args:
            symbol: 股票代码
        """
        self._suspended_set.add(symbol)
        logger.info(f"添加停牌股票: {symbol}")

    def remove_suspended_stock(self, symbol: str) -> None:
        """移除停牌股票

        Args:
            symbol: 股票代码
        """
        self._suspended_set.discard(symbol)
        logger.info(f"移除停牌股票: {symbol}")

    def set_stock_info(self, stock_info: StockInfo) -> None:
        """设置股票信息（用于测试或手动更新）

        Args:
            stock_info: 股票信息
        """
        self._stock_info_cache[stock_info.symbol] = stock_info
        logger.debug(f"设置股票信息: {stock_info.symbol}")

    def set_margin_ratio(self, ratio: float) -> None:
        """设置保证金比例（用于测试或手动更新）

        Args:
            ratio: 保证金比例（0-1之间）

        Raises:
            ValueError: 当比例无效时
        """
        if not 0 <= ratio <= 1:
            raise ValueError(f"保证金比例必须在[0, 1]范围内，当前值: {ratio}")

        self._margin_cache = ratio

        if self.redis_client:
            try:
                self.redis_client.set(self.REDIS_KEY_MARGIN, str(ratio))
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.warning(f"设置Redis保证金比例失败: {e}")

        logger.debug(f"设置保证金比例: {ratio:.2%}")

    def set_trade_count(self, date: str, count: int) -> None:
        """设置交易次数（用于测试或手动更新）

        Args:
            date: 日期字符串（YYYYMMDD格式）
            count: 交易次数

        Raises:
            ValueError: 当次数为负时
        """
        if count < 0:
            raise ValueError(f"交易次数不能为负，当前值: {count}")

        self._trade_count_cache[date] = count

        if self.redis_client:
            try:
                key = f"{self.REDIS_KEY_TRADE_COUNT}:{date}"
                self.redis_client.set(key, str(count))
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.warning(f"设置Redis交易次数失败: {e}")

        logger.debug(f"设置交易次数: {date}={count}")

    def get_st_blacklist(self) -> Set[str]:
        """获取ST股票黑名单

        Returns:
            ST股票代码集合
        """
        return self._st_blacklist.copy()

    def get_suspended_set(self) -> Set[str]:
        """获取停牌股票集合

        Returns:
            停牌股票代码集合
        """
        return self._suspended_set.copy()

    def reset_daily_count(self) -> None:
        """重置当日交易次数（用于测试）"""
        today = datetime.now().strftime("%Y%m%d")
        self._trade_count_cache[today] = 0

        if self.redis_client:
            try:
                key = f"{self.REDIS_KEY_TRADE_COUNT}:{today}"
                self.redis_client.delete(key)
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.warning(f"重置Redis交易次数失败: {e}")

        logger.debug("重置当日交易次数")
