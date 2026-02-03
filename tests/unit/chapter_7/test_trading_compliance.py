"""TradingComplianceManager单元测试

白皮书依据: 第七章 7.3 合规体系

测试交易合规管理器的各项功能：
- 日交易次数检查
- 单笔金额检查
- ST股票检查
- 停牌股票检查
- 新股检查
- 保证金检查
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock

from src.compliance.trading_compliance_manager import (
    TradingComplianceManager,
    ComplianceError,
    ComplianceCheckResult,
)
from src.compliance.data_models import (
    ComplianceCheckType,
    TradeOrder,
    ComplianceViolation,
    StockInfo,
)


class TestTradingComplianceManagerInit:
    """TradingComplianceManager初始化测试"""
    
    def test_init_default_values(self):
        """测试默认参数初始化"""
        manager = TradingComplianceManager()
        
        assert manager.daily_trade_limit == 200
        assert manager.single_trade_limit == 1_000_000.0
        assert manager.new_stock_days == 5
        assert manager.margin_ratio_limit == 0.30
        assert manager.redis_client is None
        assert manager.stock_info_provider is None
        assert manager.audit_logger is None
    
    def test_init_custom_values(self):
        """测试自定义参数初始化"""
        manager = TradingComplianceManager(
            daily_trade_limit=100,
            single_trade_limit=500_000.0,
            new_stock_days=10,
            margin_ratio_limit=0.25
        )
        
        assert manager.daily_trade_limit == 100
        assert manager.single_trade_limit == 500_000.0
        assert manager.new_stock_days == 10
        assert manager.margin_ratio_limit == 0.25
    
    def test_init_with_redis_client(self):
        """测试带Redis客户端初始化"""
        mock_redis = Mock()
        manager = TradingComplianceManager(redis_client=mock_redis)
        
        assert manager.redis_client is mock_redis
    
    def test_init_with_stock_info_provider(self):
        """测试带股票信息提供者初始化"""
        mock_provider = Mock()
        manager = TradingComplianceManager(stock_info_provider=mock_provider)
        
        assert manager.stock_info_provider is mock_provider
    
    def test_init_with_audit_logger(self):
        """测试带审计日志记录器初始化"""
        mock_logger = Mock()
        manager = TradingComplianceManager(audit_logger=mock_logger)
        
        assert manager.audit_logger is mock_logger
    
    def test_init_invalid_daily_limit(self):
        """测试无效的日交易次数限制"""
        with pytest.raises(ValueError, match="日交易次数限制必须大于0"):
            TradingComplianceManager(daily_trade_limit=0)
        
        with pytest.raises(ValueError, match="日交易次数限制必须大于0"):
            TradingComplianceManager(daily_trade_limit=-1)
    
    def test_init_invalid_single_limit(self):
        """测试无效的单笔金额限制"""
        with pytest.raises(ValueError, match="单笔交易金额限制必须大于0"):
            TradingComplianceManager(single_trade_limit=0)
        
        with pytest.raises(ValueError, match="单笔交易金额限制必须大于0"):
            TradingComplianceManager(single_trade_limit=-100)
    
    def test_init_invalid_new_stock_days(self):
        """测试无效的新股限制天数"""
        with pytest.raises(ValueError, match="新股限制天数不能为负"):
            TradingComplianceManager(new_stock_days=-1)
    
    def test_init_invalid_margin_ratio(self):
        """测试无效的保证金比例限制"""
        with pytest.raises(ValueError, match="保证金比例限制必须在"):
            TradingComplianceManager(margin_ratio_limit=0)
        
        with pytest.raises(ValueError, match="保证金比例限制必须在"):
            TradingComplianceManager(margin_ratio_limit=1.5)


class TestDailyTradeLimit:
    """日交易次数检查测试"""
    
    def test_daily_limit_pass(self):
        """测试日交易次数未超限"""
        manager = TradingComplianceManager(daily_trade_limit=200)
        order = TradeOrder(
            symbol="000001.SZ",
            action="buy",
            quantity=100,
            price=10.0
        )
        
        result = manager.check_trade_compliance(order)
        assert result.passed is True
        assert len(result.violations) == 0
    
    def test_daily_limit_exceed(self):
        """测试日交易次数超限"""
        manager = TradingComplianceManager(daily_trade_limit=5)
        today = datetime.now().strftime('%Y%m%d')
        manager.set_trade_count(today, 5)
        
        order = TradeOrder(
            symbol="000001.SZ",
            action="buy",
            quantity=100,
            price=10.0
        )
        
        with pytest.raises(ComplianceError) as exc_info:
            manager.check_trade_compliance(order)
        
        assert "单日交易次数超限" in str(exc_info.value)
        assert len(exc_info.value.violations) >= 1
        
        violation = exc_info.value.violations[0]
        assert violation.check_type == ComplianceCheckType.DAILY_TRADE_LIMIT
    
    def test_daily_limit_boundary(self):
        """测试日交易次数边界值"""
        manager = TradingComplianceManager(daily_trade_limit=10)
        today = datetime.now().strftime('%Y%m%d')
        
        # 设置为9次，应该通过
        manager.set_trade_count(today, 9)
        order = TradeOrder(
            symbol="000001.SZ",
            action="buy",
            quantity=100,
            price=10.0
        )
        
        result = manager.check_trade_compliance(order)
        assert result.passed is True
    
    def test_daily_count_increment(self):
        """测试交易次数自动增加"""
        manager = TradingComplianceManager(daily_trade_limit=200)
        today = datetime.now().strftime('%Y%m%d')
        
        initial_count = manager._get_trade_count(today)
        
        order = TradeOrder(
            symbol="000001.SZ",
            action="buy",
            quantity=100,
            price=10.0
        )
        manager.check_trade_compliance(order)
        
        new_count = manager._get_trade_count(today)
        assert new_count == initial_count + 1



class TestSingleTradeAmount:
    """单笔交易金额检查测试"""
    
    def test_amount_pass(self):
        """测试单笔金额未超限"""
        manager = TradingComplianceManager(single_trade_limit=1_000_000.0)
        order = TradeOrder(
            symbol="000001.SZ",
            action="buy",
            quantity=1000,
            price=100.0  # 金额 = 100,000
        )
        
        result = manager.check_trade_compliance(order)
        assert result.passed is True
    
    def test_amount_exceed(self):
        """测试单笔金额超限"""
        manager = TradingComplianceManager(single_trade_limit=100_000.0)
        order = TradeOrder(
            symbol="000001.SZ",
            action="buy",
            quantity=10000,
            price=100.0  # 金额 = 1,000,000
        )
        
        with pytest.raises(ComplianceError) as exc_info:
            manager.check_trade_compliance(order)
        
        assert "单笔交易金额超限" in str(exc_info.value)
        
        violation = next(
            v for v in exc_info.value.violations 
            if v.check_type == ComplianceCheckType.SINGLE_TRADE_AMOUNT
        )
        assert violation is not None
    
    def test_amount_boundary(self):
        """测试单笔金额边界值"""
        manager = TradingComplianceManager(single_trade_limit=100_000.0)
        
        # 刚好等于限制，应该通过
        order = TradeOrder(
            symbol="000001.SZ",
            action="buy",
            quantity=1000,
            price=100.0  # 金额 = 100,000
        )
        
        result = manager.check_trade_compliance(order)
        assert result.passed is True
    
    def test_amount_slightly_over(self):
        """测试单笔金额略微超限"""
        manager = TradingComplianceManager(single_trade_limit=100_000.0)
        order = TradeOrder(
            symbol="000001.SZ",
            action="buy",
            quantity=1001,
            price=100.0  # 金额 = 100,100
        )
        
        with pytest.raises(ComplianceError) as exc_info:
            manager.check_trade_compliance(order)
        
        assert "单笔交易金额超限" in str(exc_info.value)


class TestSTStockCheck:
    """ST股票检查测试"""
    
    def test_st_stock_reject(self):
        """测试ST股票被拒绝"""
        manager = TradingComplianceManager()
        manager.add_st_stock("000001.SZ")
        
        order = TradeOrder(
            symbol="000001.SZ",
            action="buy",
            quantity=100,
            price=10.0
        )
        
        with pytest.raises(ComplianceError) as exc_info:
            manager.check_trade_compliance(order)
        
        assert "禁止交易ST股票" in str(exc_info.value)
        
        violation = next(
            v for v in exc_info.value.violations 
            if v.check_type == ComplianceCheckType.ST_STOCK
        )
        assert violation is not None
    
    def test_non_st_stock_pass(self):
        """测试非ST股票通过"""
        manager = TradingComplianceManager()
        manager.add_st_stock("000002.SZ")  # 添加其他股票到黑名单
        
        order = TradeOrder(
            symbol="000001.SZ",
            action="buy",
            quantity=100,
            price=10.0
        )
        
        result = manager.check_trade_compliance(order)
        assert result.passed is True
    
    def test_st_stock_from_provider(self):
        """测试从提供者获取ST股票信息"""
        mock_provider = Mock()
        mock_provider.get_stock_info.return_value = {
            'symbol': '000001.SZ',
            'name': 'ST测试',
            'is_st': True,
            'is_suspended': False,
            'list_date': None
        }
        
        manager = TradingComplianceManager(stock_info_provider=mock_provider)
        order = TradeOrder(
            symbol="000001.SZ",
            action="buy",
            quantity=100,
            price=10.0
        )
        
        with pytest.raises(ComplianceError) as exc_info:
            manager.check_trade_compliance(order)
        
        assert "禁止交易ST股票" in str(exc_info.value)
    
    def test_add_remove_st_stock(self):
        """测试添加和移除ST股票"""
        manager = TradingComplianceManager()
        
        # 添加
        manager.add_st_stock("000001.SZ")
        assert "000001.SZ" in manager.get_st_blacklist()
        
        # 移除
        manager.remove_st_stock("000001.SZ")
        assert "000001.SZ" not in manager.get_st_blacklist()


class TestSuspendedStockCheck:
    """停牌股票检查测试"""
    
    def test_suspended_stock_reject(self):
        """测试停牌股票被拒绝"""
        manager = TradingComplianceManager()
        manager.add_suspended_stock("000001.SZ")
        
        order = TradeOrder(
            symbol="000001.SZ",
            action="buy",
            quantity=100,
            price=10.0
        )
        
        with pytest.raises(ComplianceError) as exc_info:
            manager.check_trade_compliance(order)
        
        assert "禁止交易停牌股票" in str(exc_info.value)
        
        violation = next(
            v for v in exc_info.value.violations 
            if v.check_type == ComplianceCheckType.SUSPENDED_STOCK
        )
        assert violation is not None
    
    def test_non_suspended_stock_pass(self):
        """测试非停牌股票通过"""
        manager = TradingComplianceManager()
        
        order = TradeOrder(
            symbol="000001.SZ",
            action="buy",
            quantity=100,
            price=10.0
        )
        
        result = manager.check_trade_compliance(order)
        assert result.passed is True
    
    def test_suspended_stock_from_provider(self):
        """测试从提供者获取停牌股票信息"""
        mock_provider = Mock()
        mock_provider.get_stock_info.return_value = {
            'symbol': '000001.SZ',
            'name': '测试股票',
            'is_st': False,
            'is_suspended': True,
            'list_date': None
        }
        
        manager = TradingComplianceManager(stock_info_provider=mock_provider)
        order = TradeOrder(
            symbol="000001.SZ",
            action="buy",
            quantity=100,
            price=10.0
        )
        
        with pytest.raises(ComplianceError) as exc_info:
            manager.check_trade_compliance(order)
        
        assert "禁止交易停牌股票" in str(exc_info.value)
    
    def test_add_remove_suspended_stock(self):
        """测试添加和移除停牌股票"""
        manager = TradingComplianceManager()
        
        # 添加
        manager.add_suspended_stock("000001.SZ")
        assert "000001.SZ" in manager.get_suspended_set()
        
        # 移除
        manager.remove_suspended_stock("000001.SZ")
        assert "000001.SZ" not in manager.get_suspended_set()



class TestNewStockCheck:
    """新股检查测试"""
    
    def test_new_stock_reject(self):
        """测试新股被拒绝"""
        manager = TradingComplianceManager(new_stock_days=5)
        
        # 设置上市日期为2天前
        list_date = datetime.now() - timedelta(days=2)
        stock_info = StockInfo(
            symbol="000001.SZ",
            name="新股测试",
            is_st=False,
            is_suspended=False,
            list_date=list_date
        )
        manager.set_stock_info(stock_info)
        
        order = TradeOrder(
            symbol="000001.SZ",
            action="buy",
            quantity=100,
            price=10.0
        )
        
        with pytest.raises(ComplianceError) as exc_info:
            manager.check_trade_compliance(order)
        
        assert "禁止交易新股" in str(exc_info.value)
        
        violation = next(
            v for v in exc_info.value.violations 
            if v.check_type == ComplianceCheckType.NEW_STOCK
        )
        assert violation is not None
    
    def test_old_stock_pass(self):
        """测试老股通过"""
        manager = TradingComplianceManager(new_stock_days=5)
        
        # 设置上市日期为10天前
        list_date = datetime.now() - timedelta(days=10)
        stock_info = StockInfo(
            symbol="000001.SZ",
            name="老股测试",
            is_st=False,
            is_suspended=False,
            list_date=list_date
        )
        manager.set_stock_info(stock_info)
        
        order = TradeOrder(
            symbol="000001.SZ",
            action="buy",
            quantity=100,
            price=10.0
        )
        
        result = manager.check_trade_compliance(order)
        assert result.passed is True
    
    def test_new_stock_boundary(self):
        """测试新股边界值（刚好5天）"""
        manager = TradingComplianceManager(new_stock_days=5)
        
        # 设置上市日期为5天前
        list_date = datetime.now() - timedelta(days=5)
        stock_info = StockInfo(
            symbol="000001.SZ",
            name="边界测试",
            is_st=False,
            is_suspended=False,
            list_date=list_date
        )
        manager.set_stock_info(stock_info)
        
        order = TradeOrder(
            symbol="000001.SZ",
            action="buy",
            quantity=100,
            price=10.0
        )
        
        result = manager.check_trade_compliance(order)
        assert result.passed is True
    
    def test_new_stock_from_provider(self):
        """测试从提供者获取新股信息"""
        mock_provider = Mock()
        list_date = datetime.now() - timedelta(days=2)
        mock_provider.get_stock_info.return_value = {
            'symbol': '000001.SZ',
            'name': '新股测试',
            'is_st': False,
            'is_suspended': False,
            'list_date': list_date.isoformat()
        }
        
        manager = TradingComplianceManager(
            new_stock_days=5,
            stock_info_provider=mock_provider
        )
        order = TradeOrder(
            symbol="000001.SZ",
            action="buy",
            quantity=100,
            price=10.0
        )
        
        with pytest.raises(ComplianceError) as exc_info:
            manager.check_trade_compliance(order)
        
        assert "禁止交易新股" in str(exc_info.value)
    
    def test_stock_without_list_date_pass(self):
        """测试没有上市日期的股票通过"""
        manager = TradingComplianceManager(new_stock_days=5)
        
        # 没有设置股票信息，应该通过
        order = TradeOrder(
            symbol="000001.SZ",
            action="buy",
            quantity=100,
            price=10.0
        )
        
        result = manager.check_trade_compliance(order)
        assert result.passed is True


class TestMarginRatioCheck:
    """保证金比例检查测试"""
    
    def test_margin_check_for_derivative(self):
        """测试衍生品保证金检查"""
        manager = TradingComplianceManager(margin_ratio_limit=0.30)
        manager.set_margin_ratio(0.35)  # 超过30%
        
        order = TradeOrder(
            symbol="IF2401",
            action="buy",
            quantity=1,
            price=4000.0,
            is_derivative=True
        )
        
        with pytest.raises(ComplianceError) as exc_info:
            manager.check_trade_compliance(order)
        
        assert "衍生品保证金比例超限" in str(exc_info.value)
        
        violation = next(
            v for v in exc_info.value.violations 
            if v.check_type == ComplianceCheckType.MARGIN_RATIO
        )
        assert violation is not None
    
    def test_margin_check_pass_for_derivative(self):
        """测试衍生品保证金检查通过"""
        manager = TradingComplianceManager(margin_ratio_limit=0.30)
        manager.set_margin_ratio(0.25)  # 低于30%
        
        order = TradeOrder(
            symbol="IF2401",
            action="buy",
            quantity=1,
            price=4000.0,
            is_derivative=True
        )
        
        result = manager.check_trade_compliance(order)
        assert result.passed is True
    
    def test_margin_check_skip_for_stock(self):
        """测试股票不检查保证金"""
        manager = TradingComplianceManager(margin_ratio_limit=0.30)
        manager.set_margin_ratio(0.50)  # 超过30%，但股票不检查
        
        order = TradeOrder(
            symbol="000001.SZ",
            action="buy",
            quantity=100,
            price=10.0,
            is_derivative=False
        )
        
        result = manager.check_trade_compliance(order)
        assert result.passed is True
    
    def test_margin_boundary(self):
        """测试保证金边界值"""
        manager = TradingComplianceManager(margin_ratio_limit=0.30)
        manager.set_margin_ratio(0.30)  # 刚好等于30%
        
        order = TradeOrder(
            symbol="IF2401",
            action="buy",
            quantity=1,
            price=4000.0,
            is_derivative=True
        )
        
        with pytest.raises(ComplianceError) as exc_info:
            manager.check_trade_compliance(order)
        
        assert "衍生品保证金比例超限" in str(exc_info.value)
    
    def test_set_margin_ratio_invalid(self):
        """测试设置无效的保证金比例"""
        manager = TradingComplianceManager()
        
        with pytest.raises(ValueError, match="保证金比例必须在"):
            manager.set_margin_ratio(-0.1)
        
        with pytest.raises(ValueError, match="保证金比例必须在"):
            manager.set_margin_ratio(1.5)



class TestMultipleViolations:
    """多重违规测试"""
    
    def test_multiple_violations(self):
        """测试多个合规检查同时失败"""
        manager = TradingComplianceManager(
            daily_trade_limit=5,
            single_trade_limit=100_000.0
        )
        
        today = datetime.now().strftime('%Y%m%d')
        manager.set_trade_count(today, 5)  # 超过日限制
        manager.add_st_stock("000001.SZ")  # ST股票
        
        order = TradeOrder(
            symbol="000001.SZ",
            action="buy",
            quantity=10000,
            price=100.0  # 金额超限
        )
        
        with pytest.raises(ComplianceError) as exc_info:
            manager.check_trade_compliance(order)
        
        # 应该有3个违规
        assert len(exc_info.value.violations) >= 3
        
        check_types = {v.check_type for v in exc_info.value.violations}
        assert ComplianceCheckType.DAILY_TRADE_LIMIT in check_types
        assert ComplianceCheckType.SINGLE_TRADE_AMOUNT in check_types
        assert ComplianceCheckType.ST_STOCK in check_types
    
    def test_all_checks_fail(self):
        """测试所有检查都失败"""
        manager = TradingComplianceManager(
            daily_trade_limit=5,
            single_trade_limit=100_000.0,
            new_stock_days=5,
            margin_ratio_limit=0.30
        )
        
        today = datetime.now().strftime('%Y%m%d')
        manager.set_trade_count(today, 5)
        manager.add_st_stock("000001.SZ")
        manager.add_suspended_stock("000001.SZ")
        manager.set_margin_ratio(0.35)
        
        list_date = datetime.now() - timedelta(days=2)
        stock_info = StockInfo(
            symbol="000001.SZ",
            name="测试",
            is_st=True,
            is_suspended=True,
            list_date=list_date
        )
        manager.set_stock_info(stock_info)
        
        order = TradeOrder(
            symbol="000001.SZ",
            action="buy",
            quantity=10000,
            price=100.0,
            is_derivative=True
        )
        
        with pytest.raises(ComplianceError) as exc_info:
            manager.check_trade_compliance(order)
        
        # 应该有6个违规
        assert len(exc_info.value.violations) >= 6


class TestAuditLogging:
    """审计日志测试"""
    
    def test_audit_log_on_pass(self):
        """测试通过时记录审计日志"""
        mock_logger = Mock()
        manager = TradingComplianceManager(audit_logger=mock_logger)
        
        order = TradeOrder(
            symbol="000001.SZ",
            action="buy",
            quantity=100,
            price=10.0
        )
        
        manager.check_trade_compliance(order)
        
        mock_logger.log_event.assert_called_once()
        call_args = mock_logger.log_event.call_args[0][0]
        assert call_args['event_type'] == 'COMPLIANCE_CHECK'
        assert call_args['passed'] is True
    
    def test_audit_log_on_fail(self):
        """测试失败时记录审计日志"""
        mock_logger = Mock()
        manager = TradingComplianceManager(
            single_trade_limit=100.0,
            audit_logger=mock_logger
        )
        
        order = TradeOrder(
            symbol="000001.SZ",
            action="buy",
            quantity=100,
            price=10.0  # 金额超限
        )
        
        with pytest.raises(ComplianceError):
            manager.check_trade_compliance(order)
        
        mock_logger.log_event.assert_called_once()
        call_args = mock_logger.log_event.call_args[0][0]
        assert call_args['event_type'] == 'COMPLIANCE_CHECK'
        assert call_args['passed'] is False
        assert call_args['violations_count'] >= 1
    
    def test_audit_log_exception_handled(self):
        """测试审计日志异常被处理"""
        mock_logger = Mock()
        mock_logger.log_event.side_effect = Exception("日志错误")
        
        manager = TradingComplianceManager(audit_logger=mock_logger)
        
        order = TradeOrder(
            symbol="000001.SZ",
            action="buy",
            quantity=100,
            price=10.0
        )
        
        # 不应该抛出异常
        result = manager.check_trade_compliance(order)
        assert result.passed is True


class TestRedisIntegration:
    """Redis集成测试"""
    
    def test_trade_count_from_redis(self):
        """测试从Redis获取交易次数"""
        mock_redis = Mock()
        mock_redis.get.return_value = b"10"
        
        manager = TradingComplianceManager(redis_client=mock_redis)
        today = datetime.now().strftime('%Y%m%d')
        
        count = manager._get_trade_count(today)
        assert count == 10
        
        mock_redis.get.assert_called_once()
    
    def test_trade_count_increment_redis(self):
        """测试Redis交易次数增加"""
        mock_redis = Mock()
        mock_redis.get.return_value = b"0"
        
        manager = TradingComplianceManager(
            daily_trade_limit=200,
            redis_client=mock_redis
        )
        
        order = TradeOrder(
            symbol="000001.SZ",
            action="buy",
            quantity=100,
            price=10.0
        )
        
        manager.check_trade_compliance(order)
        
        mock_redis.incr.assert_called_once()
        mock_redis.expire.assert_called_once()
    
    def test_margin_ratio_from_redis(self):
        """测试从Redis获取保证金比例"""
        mock_redis = Mock()
        mock_redis.get.return_value = b"0.25"
        
        manager = TradingComplianceManager(redis_client=mock_redis)
        
        ratio = manager._get_margin_ratio()
        assert ratio == 0.25
    
    def test_redis_exception_fallback(self):
        """测试Redis异常时回退到内存缓存"""
        mock_redis = Mock()
        mock_redis.get.side_effect = Exception("Redis错误")
        
        manager = TradingComplianceManager(redis_client=mock_redis)
        today = datetime.now().strftime('%Y%m%d')
        manager._trade_count_cache[today] = 5
        
        count = manager._get_trade_count(today)
        assert count == 5


class TestComplianceCheckResult:
    """ComplianceCheckResult测试"""
    
    def test_result_to_dict(self):
        """测试结果转换为字典"""
        violations = [
            ComplianceViolation(
                check_type=ComplianceCheckType.ST_STOCK,
                message="禁止交易ST股票",
                details={'symbol': '000001.SZ'}
            )
        ]
        
        result = ComplianceCheckResult(
            passed=False,
            violations=violations
        )
        
        result_dict = result.to_dict()
        
        assert result_dict['passed'] is False
        assert len(result_dict['violations']) == 1
        assert 'checked_at' in result_dict
    
    def test_result_passed(self):
        """测试通过的结果"""
        result = ComplianceCheckResult(passed=True)
        
        assert result.passed is True
        assert len(result.violations) == 0


class TestTradeOrder:
    """TradeOrder测试"""
    
    def test_order_amount_calculation(self):
        """测试订单金额计算"""
        order = TradeOrder(
            symbol="000001.SZ",
            action="buy",
            quantity=100,
            price=10.5
        )
        
        assert order.amount == 1050.0
    
    def test_order_to_dict(self):
        """测试订单转换为字典"""
        order = TradeOrder(
            symbol="000001.SZ",
            action="buy",
            quantity=100,
            price=10.0,
            is_derivative=False,
            strategy_id="S001",
            order_id="O001"
        )
        
        order_dict = order.to_dict()
        
        assert order_dict['symbol'] == "000001.SZ"
        assert order_dict['action'] == "buy"
        assert order_dict['quantity'] == 100
        assert order_dict['price'] == 10.0
        assert order_dict['amount'] == 1000.0
        assert order_dict['is_derivative'] is False
        assert order_dict['strategy_id'] == "S001"
        assert order_dict['order_id'] == "O001"


class TestStockInfo:
    """StockInfo测试"""
    
    def test_days_since_listing(self):
        """测试上市天数计算"""
        list_date = datetime.now() - timedelta(days=10)
        stock_info = StockInfo(
            symbol="000001.SZ",
            name="测试",
            list_date=list_date
        )
        
        days = stock_info.days_since_listing()
        assert days == 10
    
    def test_days_since_listing_no_date(self):
        """测试没有上市日期时返回默认值"""
        stock_info = StockInfo(
            symbol="000001.SZ",
            name="测试"
        )
        
        days = stock_info.days_since_listing()
        assert days == 999
    
    def test_stock_info_to_dict(self):
        """测试股票信息转换为字典"""
        list_date = datetime(2024, 1, 1)
        stock_info = StockInfo(
            symbol="000001.SZ",
            name="测试股票",
            is_st=True,
            is_suspended=False,
            list_date=list_date
        )
        
        info_dict = stock_info.to_dict()
        
        assert info_dict['symbol'] == "000001.SZ"
        assert info_dict['name'] == "测试股票"
        assert info_dict['is_st'] is True
        assert info_dict['is_suspended'] is False
        assert info_dict['list_date'] == "2024-01-01T00:00:00"


class TestResetAndManagement:
    """重置和管理方法测试"""
    
    def test_reset_daily_count(self):
        """测试重置当日交易次数"""
        manager = TradingComplianceManager()
        today = datetime.now().strftime('%Y%m%d')
        
        manager.set_trade_count(today, 100)
        assert manager._get_trade_count(today) == 100
        
        manager.reset_daily_count()
        assert manager._get_trade_count(today) == 0
    
    def test_set_trade_count_invalid(self):
        """测试设置无效的交易次数"""
        manager = TradingComplianceManager()
        
        with pytest.raises(ValueError, match="交易次数不能为负"):
            manager.set_trade_count("20240101", -1)
    
    def test_set_stock_info(self):
        """测试设置股票信息"""
        manager = TradingComplianceManager()
        
        stock_info = StockInfo(
            symbol="000001.SZ",
            name="测试",
            is_st=True
        )
        manager.set_stock_info(stock_info)
        
        retrieved = manager._get_stock_info("000001.SZ")
        assert retrieved is not None
        assert retrieved.is_st is True
