"""Auditor单元测试

白皮书依据: 第七章 6.2.1 独立审计进程

测试Auditor的核心功能：
- 影子账本同步
- 交易验证
- 对账逻辑
- 差异告警
"""

import json
from datetime import datetime
from unittest.mock import MagicMock, AsyncMock, patch

import pytest

from src.audit.auditor import (
    Auditor,
    AuditError,
    InsufficientPositionError,
    ReconciliationError
)
from src.audit.data_models import ShadowPosition, ReconciliationDiscrepancy


class TestAuditorInitialization:
    """Auditor初始化测试
    
    白皮书依据: 第七章 6.2.1 独立审计进程
    """
    
    def test_init_without_dependencies(self):
        """测试无依赖初始化"""
        auditor = Auditor()
        
        assert auditor.shadow_ledger == {}
        assert auditor.redis_client is None
        assert auditor.broker_api is None
        assert auditor.audit_logger is None
    
    def test_init_with_redis(self):
        """测试带Redis初始化"""
        mock_redis = MagicMock()
        mock_redis.hgetall.return_value = {}
        
        auditor = Auditor(redis_client=mock_redis)
        
        assert auditor.redis_client is mock_redis
        mock_redis.hgetall.assert_called_once()
    
    def test_init_loads_from_redis(self):
        """测试从Redis加载影子账本"""
        mock_redis = MagicMock()
        mock_redis.hgetall.return_value = {
            '000001.SZ': json.dumps({
                'symbol': '000001.SZ',
                'quantity': 100,
                'avg_cost': 10.0,
                'last_sync': '2026-01-25T10:00:00'
            })
        }
        
        auditor = Auditor(redis_client=mock_redis)
        
        assert '000001.SZ' in auditor.shadow_ledger
        assert auditor.shadow_ledger['000001.SZ'].quantity == 100
    
    def test_init_with_broker_api(self):
        """测试带券商API初始化"""
        mock_broker = MagicMock()
        
        auditor = Auditor(broker_api=mock_broker)
        
        assert auditor.broker_api is mock_broker


class TestAuditorVerifyTrade:
    """Auditor交易验证测试
    
    白皮书依据: 第七章 6.2.1 独立审计进程
    Requirements: 3.2, 3.4
    """
    
    @pytest.fixture
    def auditor_with_positions(self):
        """创建带持仓的Auditor"""
        auditor = Auditor()
        auditor.shadow_ledger = {
            '000001.SZ': ShadowPosition(
                symbol='000001.SZ',
                quantity=100,
                avg_cost=10.0,
                last_sync='2026-01-25T10:00:00'
            ),
            '600000.SH': ShadowPosition(
                symbol='600000.SH',
                quantity=200,
                avg_cost=15.0,
                last_sync='2026-01-25T10:00:00'
            )
        }
        return auditor
    
    def test_verify_buy_trade_always_passes(self, auditor_with_positions):
        """测试买入交易总是通过
        
        Requirements: 3.4
        """
        result = auditor_with_positions.verify_trade({
            'symbol': '000001.SZ',
            'action': 'buy',
            'quantity': 1000  # 任意数量
        })
        
        assert result is True
    
    def test_verify_buy_new_symbol_passes(self, auditor_with_positions):
        """测试买入新股票通过"""
        result = auditor_with_positions.verify_trade({
            'symbol': '300001.SZ',  # 不在持仓中
            'action': 'buy',
            'quantity': 100
        })
        
        assert result is True
    
    def test_verify_sell_with_sufficient_position(self, auditor_with_positions):
        """测试卖出有足够持仓时通过
        
        Requirements: 3.4
        """
        result = auditor_with_positions.verify_trade({
            'symbol': '000001.SZ',
            'action': 'sell',
            'quantity': 50  # 持仓100，卖50
        })
        
        assert result is True
    
    def test_verify_sell_exact_position(self, auditor_with_positions):
        """测试卖出全部持仓通过"""
        result = auditor_with_positions.verify_trade({
            'symbol': '000001.SZ',
            'action': 'sell',
            'quantity': 100  # 持仓100，卖100
        })
        
        assert result is True
    
    def test_verify_sell_insufficient_position(self, auditor_with_positions):
        """测试卖出持仓不足时失败
        
        Requirements: 3.4
        """
        with pytest.raises(InsufficientPositionError) as exc_info:
            auditor_with_positions.verify_trade({
                'symbol': '000001.SZ',
                'action': 'sell',
                'quantity': 150  # 持仓100，卖150
            })
        
        assert '持仓不足' in str(exc_info.value) or 'insufficient' in str(exc_info.value).lower()
    
    def test_verify_sell_no_position(self, auditor_with_positions):
        """测试卖出无持仓股票失败
        
        Requirements: 3.4
        """
        with pytest.raises(InsufficientPositionError) as exc_info:
            auditor_with_positions.verify_trade({
                'symbol': '300001.SZ',  # 不在持仓中
                'action': 'sell',
                'quantity': 100
            })
        
        assert '不在影子账本' in str(exc_info.value)
    
    def test_verify_trade_missing_symbol(self, auditor_with_positions):
        """测试缺少symbol字段"""
        with pytest.raises(ValueError) as exc_info:
            auditor_with_positions.verify_trade({
                'action': 'buy',
                'quantity': 100
            })
        
        assert 'symbol' in str(exc_info.value)
    
    def test_verify_trade_missing_action(self, auditor_with_positions):
        """测试缺少action字段"""
        with pytest.raises(ValueError) as exc_info:
            auditor_with_positions.verify_trade({
                'symbol': '000001.SZ',
                'quantity': 100
            })
        
        assert 'action' in str(exc_info.value)
    
    def test_verify_trade_missing_quantity(self, auditor_with_positions):
        """测试缺少quantity字段"""
        with pytest.raises(ValueError) as exc_info:
            auditor_with_positions.verify_trade({
                'symbol': '000001.SZ',
                'action': 'buy'
            })
        
        assert 'quantity' in str(exc_info.value)
    
    def test_verify_trade_invalid_action(self, auditor_with_positions):
        """测试无效的action"""
        with pytest.raises(ValueError) as exc_info:
            auditor_with_positions.verify_trade({
                'symbol': '000001.SZ',
                'action': 'invalid',
                'quantity': 100
            })
        
        assert 'action' in str(exc_info.value).lower() or '动作' in str(exc_info.value)
    
    def test_verify_trade_zero_quantity(self, auditor_with_positions):
        """测试数量为0"""
        with pytest.raises(ValueError) as exc_info:
            auditor_with_positions.verify_trade({
                'symbol': '000001.SZ',
                'action': 'buy',
                'quantity': 0
            })
        
        assert 'quantity' in str(exc_info.value).lower() or '数量' in str(exc_info.value)
    
    def test_verify_trade_negative_quantity(self, auditor_with_positions):
        """测试负数量"""
        with pytest.raises(ValueError) as exc_info:
            auditor_with_positions.verify_trade({
                'symbol': '000001.SZ',
                'action': 'buy',
                'quantity': -100
            })
        
        assert 'quantity' in str(exc_info.value).lower() or '数量' in str(exc_info.value)


class TestAuditorUpdatePosition:
    """Auditor持仓更新测试
    
    白皮书依据: 第七章 6.2.1 独立审计进程
    """
    
    @pytest.fixture
    def auditor(self):
        """创建空Auditor"""
        return Auditor()
    
    def test_update_position_buy_new(self, auditor):
        """测试买入新股票"""
        auditor.update_position('000001.SZ', 'buy', 100, 10.0)
        
        assert '000001.SZ' in auditor.shadow_ledger
        position = auditor.shadow_ledger['000001.SZ']
        assert position.quantity == 100
        assert position.avg_cost == 10.0
    
    def test_update_position_buy_existing(self, auditor):
        """测试买入已有股票（加仓）"""
        # 初始持仓
        auditor.update_position('000001.SZ', 'buy', 100, 10.0)
        
        # 加仓
        auditor.update_position('000001.SZ', 'buy', 100, 12.0)
        
        position = auditor.shadow_ledger['000001.SZ']
        assert position.quantity == 200
        # 平均成本 = (100*10 + 100*12) / 200 = 11
        assert abs(position.avg_cost - 11.0) < 0.001
    
    def test_update_position_sell_partial(self, auditor):
        """测试部分卖出"""
        auditor.update_position('000001.SZ', 'buy', 100, 10.0)
        auditor.update_position('000001.SZ', 'sell', 30, 12.0)
        
        position = auditor.shadow_ledger['000001.SZ']
        assert position.quantity == 70
    
    def test_update_position_sell_all(self, auditor):
        """测试全部卖出"""
        auditor.update_position('000001.SZ', 'buy', 100, 10.0)
        auditor.update_position('000001.SZ', 'sell', 100, 12.0)
        
        # 全部卖出后应该从账本中删除
        assert '000001.SZ' not in auditor.shadow_ledger
    
    def test_update_position_sell_no_position(self, auditor):
        """测试卖出无持仓股票"""
        with pytest.raises(ValueError):
            auditor.update_position('000001.SZ', 'sell', 100, 10.0)
    
    def test_update_position_sell_insufficient(self, auditor):
        """测试卖出超过持仓"""
        auditor.update_position('000001.SZ', 'buy', 100, 10.0)
        
        with pytest.raises(ValueError):
            auditor.update_position('000001.SZ', 'sell', 150, 12.0)
    
    def test_update_position_invalid_action(self, auditor):
        """测试无效动作"""
        with pytest.raises(ValueError):
            auditor.update_position('000001.SZ', 'invalid', 100, 10.0)
    
    def test_update_position_invalid_quantity(self, auditor):
        """测试无效数量"""
        with pytest.raises(ValueError):
            auditor.update_position('000001.SZ', 'buy', 0, 10.0)
        
        with pytest.raises(ValueError):
            auditor.update_position('000001.SZ', 'buy', -100, 10.0)
    
    def test_update_position_invalid_price(self, auditor):
        """测试无效价格"""
        with pytest.raises(ValueError):
            auditor.update_position('000001.SZ', 'buy', 100, 0)
        
        with pytest.raises(ValueError):
            auditor.update_position('000001.SZ', 'buy', 100, -10.0)


class TestAuditorReconcile:
    """Auditor对账测试
    
    白皮书依据: 第七章 6.2.1 独立审计进程
    Requirements: 3.6, 3.7
    """
    
    @pytest.fixture
    def auditor_with_positions(self):
        """创建带持仓的Auditor"""
        auditor = Auditor()
        auditor.shadow_ledger = {
            '000001.SZ': ShadowPosition(
                symbol='000001.SZ',
                quantity=100,
                avg_cost=10.0,
                last_sync='2026-01-25T10:00:00'
            ),
            '600000.SH': ShadowPosition(
                symbol='600000.SH',
                quantity=200,
                avg_cost=15.0,
                last_sync='2026-01-25T10:00:00'
            )
        }
        return auditor
    
    def test_reconcile_no_discrepancy(self, auditor_with_positions):
        """测试无差异对账
        
        Requirements: 3.6
        """
        execution_ledger = {
            '000001.SZ': 100,
            '600000.SH': 200
        }
        
        discrepancies = auditor_with_positions.reconcile(execution_ledger)
        
        assert len(discrepancies) == 0
    
    def test_reconcile_quantity_mismatch(self, auditor_with_positions):
        """测试数量不匹配
        
        Requirements: 3.6
        """
        execution_ledger = {
            '000001.SZ': 90,  # 影子账本100，执行记录90
            '600000.SH': 200
        }
        
        discrepancies = auditor_with_positions.reconcile(execution_ledger)
        
        assert len(discrepancies) == 1
        assert discrepancies[0].symbol == '000001.SZ'
        assert discrepancies[0].shadow_quantity == 100
        assert discrepancies[0].execution_quantity == 90
        assert discrepancies[0].difference == 10
    
    def test_reconcile_missing_in_execution(self, auditor_with_positions):
        """测试执行记录缺少股票
        
        Requirements: 3.6
        """
        execution_ledger = {
            '000001.SZ': 100
            # 缺少600000.SH
        }
        
        discrepancies = auditor_with_positions.reconcile(execution_ledger)
        
        assert len(discrepancies) == 1
        assert discrepancies[0].symbol == '600000.SH'
        assert discrepancies[0].shadow_quantity == 200
        assert discrepancies[0].execution_quantity == 0
    
    def test_reconcile_extra_in_execution(self, auditor_with_positions):
        """测试执行记录多出股票
        
        Requirements: 3.6
        """
        execution_ledger = {
            '000001.SZ': 100,
            '600000.SH': 200,
            '300001.SZ': 50  # 影子账本没有
        }
        
        discrepancies = auditor_with_positions.reconcile(execution_ledger)
        
        assert len(discrepancies) == 1
        assert discrepancies[0].symbol == '300001.SZ'
        assert discrepancies[0].shadow_quantity == 0
        assert discrepancies[0].execution_quantity == 50
    
    def test_reconcile_multiple_discrepancies(self, auditor_with_positions):
        """测试多个差异
        
        Requirements: 3.6
        """
        execution_ledger = {
            '000001.SZ': 90,   # 差异10
            '600000.SH': 180,  # 差异20
        }
        
        discrepancies = auditor_with_positions.reconcile(execution_ledger)
        
        assert len(discrepancies) == 2
    
    def test_reconcile_no_execution_ledger_no_broker(self, auditor_with_positions):
        """测试无执行记录且无券商API"""
        with pytest.raises(AuditError):
            auditor_with_positions.reconcile()
    
    def test_reconcile_logs_discrepancies(self, auditor_with_positions):
        """测试对账记录审计日志
        
        Requirements: 3.7
        """
        mock_logger = MagicMock()
        auditor_with_positions.audit_logger = mock_logger
        
        execution_ledger = {
            '000001.SZ': 90,
            '600000.SH': 200
        }
        
        auditor_with_positions.reconcile(execution_ledger)
        
        mock_logger.log_event.assert_called_once()
        call_args = mock_logger.log_event.call_args[0][0]
        assert call_args['event_type'] == 'ALERT_TRIGGERED'
        assert call_args['alert_type'] == 'reconciliation_discrepancy'


class TestAuditorSyncFromBroker:
    """Auditor券商同步测试
    
    白皮书依据: 第七章 6.2.1 独立审计进程
    Requirements: 3.2
    """
    
    @pytest.fixture
    def mock_broker_api(self):
        """创建Mock券商API"""
        mock_api = MagicMock()
        mock_api.get_positions = AsyncMock(return_value=[
            {'symbol': '000001.SZ', 'quantity': 100, 'avg_cost': 10.0},
            {'symbol': '600000.SH', 'quantity': 200, 'avg_cost': 15.0},
        ])
        return mock_api
    
    @pytest.mark.asyncio
    async def test_sync_from_broker_success(self, mock_broker_api):
        """测试成功同步
        
        Requirements: 3.2
        """
        auditor = Auditor(broker_api=mock_broker_api)
        
        await auditor.sync_from_broker()
        
        assert len(auditor.shadow_ledger) == 2
        assert '000001.SZ' in auditor.shadow_ledger
        assert '600000.SH' in auditor.shadow_ledger
        assert auditor.shadow_ledger['000001.SZ'].quantity == 100
    
    @pytest.mark.asyncio
    async def test_sync_from_broker_no_api(self):
        """测试无券商API"""
        auditor = Auditor()
        
        with pytest.raises(AuditError) as exc_info:
            await auditor.sync_from_broker()
        
        assert '券商API' in str(exc_info.value) or 'broker' in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    async def test_sync_from_broker_saves_to_redis(self, mock_broker_api):
        """测试同步后保存到Redis"""
        mock_redis = MagicMock()
        mock_redis.hgetall.return_value = {}
        
        auditor = Auditor(redis_client=mock_redis, broker_api=mock_broker_api)
        
        await auditor.sync_from_broker()
        
        # 验证保存到Redis
        mock_redis.delete.assert_called()
        mock_redis.hset.assert_called()
    
    @pytest.mark.asyncio
    async def test_sync_from_broker_logs_event(self, mock_broker_api):
        """测试同步记录审计日志"""
        mock_logger = MagicMock()
        auditor = Auditor(broker_api=mock_broker_api, audit_logger=mock_logger)
        
        await auditor.sync_from_broker()
        
        mock_logger.log_event.assert_called_once()
        call_args = mock_logger.log_event.call_args[0][0]
        assert call_args['event_type'] == 'POSITION_CHANGE'
        assert call_args['action'] == 'sync_from_broker'


class TestAuditorHelperMethods:
    """Auditor辅助方法测试"""
    
    @pytest.fixture
    def auditor_with_positions(self):
        """创建带持仓的Auditor"""
        auditor = Auditor()
        auditor.shadow_ledger = {
            '000001.SZ': ShadowPosition(
                symbol='000001.SZ',
                quantity=100,
                avg_cost=10.0,
                last_sync='2026-01-25T10:00:00'
            ),
            '600000.SH': ShadowPosition(
                symbol='600000.SH',
                quantity=200,
                avg_cost=15.0,
                last_sync='2026-01-25T10:00:00'
            )
        }
        return auditor
    
    def test_get_position_exists(self, auditor_with_positions):
        """测试获取存在的持仓"""
        position = auditor_with_positions.get_position('000001.SZ')
        
        assert position is not None
        assert position.quantity == 100
    
    def test_get_position_not_exists(self, auditor_with_positions):
        """测试获取不存在的持仓"""
        position = auditor_with_positions.get_position('300001.SZ')
        
        assert position is None
    
    def test_get_all_positions(self, auditor_with_positions):
        """测试获取所有持仓"""
        positions = auditor_with_positions.get_all_positions()
        
        assert len(positions) == 2
        assert '000001.SZ' in positions
        assert '600000.SH' in positions
    
    def test_get_total_value(self, auditor_with_positions):
        """测试计算总市值"""
        prices = {
            '000001.SZ': 12.0,
            '600000.SH': 18.0
        }
        
        total = auditor_with_positions.get_total_value(prices)
        
        # 100 * 12 + 200 * 18 = 1200 + 3600 = 4800
        assert total == 4800.0
    
    def test_get_total_value_missing_price(self, auditor_with_positions):
        """测试缺少价格时使用成本价"""
        prices = {
            '000001.SZ': 12.0
            # 缺少600000.SH的价格
        }
        
        total = auditor_with_positions.get_total_value(prices)
        
        # 100 * 12 + 200 * 15(成本价) = 1200 + 3000 = 4200
        assert total == 4200.0
    
    def test_clear_ledger(self, auditor_with_positions):
        """测试清空账本"""
        auditor_with_positions.clear_ledger()
        
        assert len(auditor_with_positions.shadow_ledger) == 0



class TestAuditorCoverageCompletion:
    """Auditor覆盖率完成测试
    
    专门测试缺失的覆盖率行，确保100%覆盖率
    """

    def test_load_from_redis_bytes_decoding(self):
        """测试从Redis加载时的bytes解码处理
        
        覆盖行93, 95: bytes类型的symbol和position_json解码
        """
        mock_redis = MagicMock()
        data1 = '{"symbol": "000001.SZ", "quantity": 100.0, "avg_cost": 10.0, "last_sync": "2026-01-01T10:00:00"}'
        data2 = '{"symbol": "600000.SH", "quantity": 200.0, "avg_cost": 15.0, "last_sync": "2026-01-01T11:00:00"}'
        mock_redis.hgetall.return_value = {
            b'000001.SZ': data1.encode(),
            b'600000.SH': data2.encode()
        }
        
        auditor = Auditor(redis_client=mock_redis)
        
        assert len(auditor.shadow_ledger) == 2
        assert '000001.SZ' in auditor.shadow_ledger
        assert '600000.SH' in auditor.shadow_ledger

    def test_load_from_redis_exception_handling(self):
        """测试从Redis加载时的异常处理
        
        覆盖行105-106: Redis加载失败时的异常处理
        """
        mock_redis = MagicMock()
        mock_redis.hgetall.side_effect = Exception("Redis连接失败")
        
        auditor = Auditor(redis_client=mock_redis)
        
        assert len(auditor.shadow_ledger) == 0
        mock_redis.hgetall.assert_called_once()

    def test_save_to_redis_exception_handling(self):
        """测试保存到Redis时的异常处理
        
        覆盖行126-127: Redis保存失败时的异常处理
        """
        mock_redis = MagicMock()
        mock_redis.delete.side_effect = Exception("Redis delete失败")
        
        auditor = Auditor(redis_client=mock_redis)
        auditor.shadow_ledger['000001.SZ'] = ShadowPosition(
            symbol='000001.SZ', quantity=100.0, avg_cost=10.0, last_sync='2026-01-01T10:00:00'
        )
        
        auditor._save_to_redis()
        mock_redis.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_sync_from_broker_exception_handling(self):
        """测试从券商同步时的异常处理
        
        覆盖行172-174: sync_from_broker中的异常处理
        """
        mock_broker = AsyncMock()
        mock_broker.get_positions.side_effect = Exception("券商API调用失败")
        
        auditor = Auditor(broker_api=mock_broker)
        
        with pytest.raises(AuditError) as exc_info:
            await auditor.sync_from_broker()
        
        assert "同步持仓失败" in str(exc_info.value)
        mock_broker.get_positions.assert_called_once()

    def test_reconcile_no_execution_ledger_with_broker(self):
        """测试对账时有券商API但无执行记录的情况
        
        覆盖行313: reconcile中execution_ledger为None但有broker_api的情况
        """
        mock_broker = MagicMock()
        auditor = Auditor(broker_api=mock_broker)
        
        with pytest.raises(AuditError) as exc_info:
            auditor.reconcile(execution_ledger=None)
        
        assert "无法对账: 请提供执行记录或先调用sync_from_broker" in str(exc_info.value)

    def test_mixed_string_bytes_redis_data(self):
        """测试Redis数据中字符串和bytes混合的情况
        
        确保能正确处理各种数据类型组合
        """
        mock_redis = MagicMock()
        data = '{"symbol": "000001.SZ", "quantity": 100.0, "avg_cost": 10.0, "last_sync": "2026-01-01T10:00:00"}'
        mock_redis.hgetall.return_value = {
            '000001.SZ': data.encode(),  # str key, bytes value
            b'600000.SH': data,  # bytes key, str value
            b'300001.SZ': data.encode()  # both bytes
        }
        
        auditor = Auditor(redis_client=mock_redis)
        
        assert len(auditor.shadow_ledger) == 3
        assert '000001.SZ' in auditor.shadow_ledger
        assert '600000.SH' in auditor.shadow_ledger
        assert '300001.SZ' in auditor.shadow_ledger