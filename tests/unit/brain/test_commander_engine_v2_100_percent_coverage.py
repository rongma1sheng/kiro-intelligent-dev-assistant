"""
Commander引擎 v2.0 100%覆盖率测试

专门针对剩余的分支进行测试，确保达到100%覆盖率
"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, Mock, patch
import asyncio

from src.brain.commander_engine_v2 import CommanderEngineV2


class TestFinal100PercentCoverage:
    """测试剩余的分支以达到100%覆盖率"""

    @pytest_asyncio.fixture
    async def commander(self):
        """创建Commander引擎实例"""
        llm_gateway = AsyncMock()
        llm_gateway.initialize = AsyncMock()
        llm_gateway.generate_cloud = AsyncMock(return_value="Test response")

        hallucination_filter = AsyncMock()
        hallucination_filter.detect_hallucination = AsyncMock(
            return_value={"is_hallucination": False, "confidence": 0.9}
        )

        commander = CommanderEngineV2(llm_gateway=llm_gateway, hallucination_filter=hallucination_filter)

        event_bus = AsyncMock()
        event_bus.subscribe = AsyncMock()
        event_bus.publish = AsyncMock()
        commander.event_bus = event_bus

        await commander.initialize()

        return commander

    @pytest.mark.asyncio
    async def test_branch_518_519_parse_llm_response_text_path(self, commander):
        """测试分支[518, 519]：_parse_llm_response文本路径"""
        # 设置纯文本响应，不包含任何关键词
        response_text = "This is a plain text response without keywords"
        
        # 直接调用_parse_llm_response方法，确保走文本解析路径
        result = commander._parse_llm_response(response_text, {"symbol": "TEST"})
        
        # 验证走了文本路径并返回默认的hold推荐（第519行）
        assert result.recommendation == "hold"
        assert result.confidence == 0.6
        assert result.reasoning == response_text[:200]

    @pytest.mark.asyncio
    async def test_branch_553_557_apply_risk_controls_deprecated_high_risk(self, commander):
        """测试分支[553, 557]：apply_risk_controls废弃版本高风险检测"""
        # 创建高风险的策略分析结果
        analysis = Mock()
        analysis.risk_level = "high"
        analysis.confidence = 0.9
        analysis.recommendation = "buy"
        analysis.allocation = {"stocks": 0.8, "bonds": 0.2}
        
        # 确保风险控制已废弃
        assert commander._risk_limits_deprecated == True
        
        # 应用风险控制（现在只记录日志）
        result = commander._apply_risk_controls(analysis)
        
        # 验证结果未被修改（因为已废弃）
        assert result == analysis  # 原样返回
        assert result.confidence == 0.9  # 未被修改
        assert result.risk_level == "high"
        
        # 验证统计信息被更新
        assert commander.stats["risk_alerts"] >= 1

    @pytest.mark.asyncio
    async def test_branch_569_575_apply_risk_controls_deprecated_no_modification(self, commander):
        """测试分支[569, 575]：apply_risk_controls废弃版本不修改仓位"""
        # 创建超过仓位限制的策略分析结果
        analysis = Mock()
        analysis.risk_level = "medium"
        analysis.confidence = 0.8
        analysis.recommendation = "buy"
        analysis.allocation = {"stocks": 0.98, "bonds": 0.02}  # 超过95%限制
        
        # 应用风险控制（已废弃，不再修改）
        result = commander._apply_risk_controls(analysis)
        
        # 验证仓位未被修改（因为风险控制已废弃）
        assert result == analysis  # 原样返回
        assert result.allocation["stocks"] == 0.98  # 未被限制

    @pytest.mark.asyncio
    async def test_branch_600_607_apply_risk_controls_no_alert_trigger(self, commander):
        """测试分支[600, 607]：apply_risk_controls不再触发风险警报"""
        # 创建需要触发警报的策略分析结果
        analysis = Mock()
        analysis.risk_level = "medium"  # 非高风险，不会触发警报
        analysis.confidence = 0.9
        analysis.recommendation = "buy"
        analysis.allocation = {"stocks": 0.9, "bonds": 0.1}
        
        # Mock _trigger_risk_alert方法
        commander._trigger_risk_alert = Mock()
        
        # 应用风险控制
        result = commander._apply_risk_controls(analysis)
        
        # 验证风险警报未被触发（因为不是高风险）
        commander._trigger_risk_alert.assert_not_called()
        assert result == analysis

    @pytest.mark.asyncio
    async def test_branch_712_exit_trigger_risk_alert_exception(self, commander):
        """测试分支[712, -696]：_trigger_risk_alert异常处理"""
        # Mock event_bus.publish抛出异常
        commander.event_bus.publish = Mock(side_effect=Exception("Event bus error"))
        
        # 调用_trigger_risk_alert，应该捕获异常
        try:
            await commander._trigger_risk_alert("high_risk", {"test": "data"})
            # 不应该抛出异常，应该被内部捕获
        except Exception:
            pytest.fail("_trigger_risk_alert should handle exceptions internally")

    @pytest.mark.asyncio
    async def test_branch_1027_1028_assess_risk_from_tier_default(self, commander):
        """测试分支[1027, 1028]：_assess_risk_from_tier默认情况"""
        # 测试不在预定义tier列表中的情况
        test_cases = [
            "tier1_micro",      # 小资金tier
            "tier2_small",      # 小资金tier
            "unknown_tier",     # 未知tier
            "",                 # 空字符串
            None,               # None值
        ]
        
        for tier in test_cases:
            # 调用_assess_risk_from_tier方法
            risk_level = commander._assess_risk_from_tier(tier)
            
            # 验证返回默认的"medium"（第1028行）
            assert risk_level == "medium", f"Failed for tier: {tier}"

    @pytest.mark.asyncio
    async def test_complete_workflow_with_all_branches(self, commander):
        """完整工作流测试，确保所有分支都被覆盖"""
        # 设置LLM返回纯文本（触发518->519分支）
        commander.llm_gateway.generate_cloud = AsyncMock(
            return_value="Market analysis shows mixed signals"
        )
        
        # 设置外部数据包含小资金tier（触发1027->1028分支）
        commander.external_data = {
            "capital": {"tier": "tier1_micro"},
            "positions": {"AAPL": 0.3}
        }
        
        market_data = {
            "symbol": "TEST",
            "price": 100.0,
            "index_level": 3000,
            "volatility": 0.02,
            "volume": 1000000
        }

        # 执行完整的策略分析
        result = await commander.analyze_strategy(market_data)

        # 验证结果
        assert result is not None
        assert "recommendation" in result
        assert "confidence" in result
        assert "risk_level" in result
        assert "allocation" in result

    @pytest.mark.asyncio
    async def test_edge_case_combinations(self, commander):
        """测试边界情况组合"""
        # 测试1：纯文本响应 + 高风险控制
        commander.llm_gateway.generate_cloud = AsyncMock(
            return_value="High risk market conditions detected"
        )
        
        # 不需要Mock风险评估，因为风险控制已废弃
        market_data = {"symbol": "TEST", "price": 100.0}
        result = await commander.analyze_strategy(market_data)
        
        # 验证结果
        assert result["recommendation"] == "hold"  # 来自文本解析
        # 风险等级由市场状态决定，不再由废弃的风险控制决定
        assert "risk_level" in result

    @pytest.mark.asyncio
    async def test_risk_alert_with_event_bus_none(self, commander):
        """测试event_bus为None时的风险警报"""
        # 设置event_bus为None
        commander.event_bus = None
        
        # 调用_trigger_risk_alert，应该不抛出异常
        try:
            await commander._trigger_risk_alert("high_risk", {"test": "data"})
        except Exception:
            pytest.fail("_trigger_risk_alert should handle None event_bus gracefully")

    @pytest.mark.asyncio
    async def test_all_missing_branches_coverage(self, commander):
        """综合测试确保所有缺失的分支都被覆盖"""
        
        # 1. 测试[518, 519]分支：文本解析路径
        text_result = commander._parse_llm_response("Plain text without JSON", {"symbol": "TEST"})
        assert text_result.recommendation == "hold"
        
        # 2. 测试[553, 557]分支：废弃的风险控制，高风险检测
        high_risk_analysis = Mock()
        high_risk_analysis.risk_level = "high"
        high_risk_analysis.confidence = 0.9
        high_risk_analysis.recommendation = "buy"
        high_risk_analysis.allocation = {"stocks": 0.7}
        
        # 风险控制已废弃，不会修改结果
        risk_result = commander._apply_risk_controls(high_risk_analysis)
        assert risk_result == high_risk_analysis  # 原样返回
        assert commander.stats["risk_alerts"] >= 1  # 但会记录警报
        
        # 3. 测试[569, 575]分支：废弃的风险控制，不再限制仓位
        over_limit_analysis = Mock()
        over_limit_analysis.risk_level = "medium"
        over_limit_analysis.confidence = 0.8
        over_limit_analysis.recommendation = "buy"
        over_limit_analysis.allocation = {"stocks": 0.98}
        
        # 风险控制已废弃，不会修改仓位
        limit_result = commander._apply_risk_controls(over_limit_analysis)
        assert limit_result == over_limit_analysis  # 原样返回
        
        # 4. 测试[600, 607]分支：废弃的风险控制，不再触发警报
        commander._trigger_risk_alert = AsyncMock()
        alert_analysis = Mock()
        alert_analysis.risk_level = "medium"  # 非高风险，不会触发警报
        alert_analysis.confidence = 0.9
        alert_analysis.recommendation = "buy"
        alert_analysis.allocation = {"stocks": 0.9}
        
        commander._apply_risk_controls(alert_analysis)
        commander._trigger_risk_alert.assert_not_called()  # 不会被调用
        
        # 5. 测试[712, -696]分支：异常处理
        # 使用AsyncMock而不是Mock
        commander.event_bus = AsyncMock()
        commander.event_bus.publish = AsyncMock(side_effect=Exception("Test error"))
        
        # 应该不抛出异常
        await commander._trigger_risk_alert("high_risk", {"test": "data"})
        
        # 6. 测试[1027, 1028]分支：默认风险评估
        default_risk = commander._assess_risk_from_tier("unknown_tier")
        assert default_risk == "medium"

    @pytest.mark.asyncio
    async def test_specific_branch_coverage_verification(self, commander):
        """专门验证特定分支的覆盖"""
        
        # 测试JSON解析失败时的文本路径（518->519）
        json_fail_response = "This is plain text without any JSON structure"
        result = commander._parse_llm_response(json_fail_response, {"symbol": "TEST"})
        assert result.recommendation == "hold"
        assert result.confidence == 0.6
        
        # 测试包含buy关键词的文本解析
        buy_response = "I recommend to buy this stock based on analysis"
        result = commander._parse_llm_response(buy_response, {"symbol": "TEST"})
        assert result.recommendation == "buy"
        
        # 测试包含sell关键词的文本解析
        sell_response = "Market conditions suggest we should sell positions"
        result = commander._parse_llm_response(sell_response, {"symbol": "TEST"})
        assert result.recommendation == "sell"
        
        # 测试包含reduce关键词的文本解析
        reduce_response = "We should reduce our exposure to this sector"
        result = commander._parse_llm_response(reduce_response, {"symbol": "TEST"})
        assert result.recommendation == "reduce"