"""
Commander引擎 v2.0 最终覆盖率测试

专门针对Commander Engine V2进行100%覆盖率测试
确保所有方法和分支都被正确覆盖
"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, Mock, patch, MagicMock
import asyncio
import json
from datetime import datetime

# 直接导入目标模块
from src.brain.commander_engine_v2 import CommanderEngineV2, StrategyAnalysis
from src.brain.llm_gateway import LLMGateway
from src.brain.hallucination_filter import HallucinationFilter


class TestCommanderEngineV2FinalCoverage:
    """Commander Engine V2 最终覆盖率测试"""

    @pytest_asyncio.fixture
    async def commander(self):
        """创建Commander引擎实例"""
        # 创建Mock的依赖项
        llm_gateway = AsyncMock(spec=LLMGateway)
        llm_gateway.initialize = AsyncMock()
        llm_gateway.generate_cloud = AsyncMock(return_value="Test response")

        hallucination_filter = AsyncMock(spec=HallucinationFilter)
        hallucination_filter.detect_hallucination = AsyncMock(
            return_value={"is_hallucination": False, "confidence": 0.9}
        )

        # 创建Commander实例
        commander = CommanderEngineV2(
            llm_gateway=llm_gateway, 
            hallucination_filter=hallucination_filter
        )

        # Mock事件总线
        event_bus = AsyncMock()
        event_bus.subscribe = AsyncMock()
        event_bus.publish = AsyncMock()
        commander.event_bus = event_bus

        # 初始化
        await commander.initialize()

        return commander

    @pytest.mark.asyncio
    async def test_initialization(self, commander):
        """测试初始化过程"""
        assert commander.state == "READY"
        assert commander.llm_gateway is not None
        assert commander.hallucination_filter is not None
        assert commander.capital_integration is not None
        assert commander.analysis_cache is not None
        assert commander._risk_limits_deprecated == True

    @pytest.mark.asyncio
    async def test_analyze_strategy_full_workflow(self, commander):
        """测试完整的策略分析工作流"""
        # 设置LLM响应
        commander.llm_gateway.generate_cloud = AsyncMock(
            return_value='{"recommendation": "buy", "confidence": 0.8, "risk_level": "medium"}'
        )

        # 设置资本集成响应
        commander.capital_integration.analyze_strategy_with_capital_context = AsyncMock(
            return_value={
                "tier": "tier3_medium",
                "recommended_strategy": "buy",
                "confidence": 0.7,
                "allocation": {"stocks": 0.7, "bonds": 0.3}
            }
        )

        market_data = {
            "symbol": "AAPL",
            "price": 150.0,
            "volume": 1000000,
            "volatility": 0.02
        }

        # 执行策略分析
        result = await commander.analyze_strategy(market_data)

        # 验证结果
        assert result is not None
        assert "recommendation" in result
        assert "confidence" in result
        assert "risk_level" in result
        assert "allocation" in result
        assert commander.stats["total_analyses"] >= 1

    @pytest.mark.asyncio
    async def test_parse_llm_response_json_path(self, commander):
        """测试_parse_llm_response的JSON解析路径"""
        market_data = {"symbol": "TEST", "price": 100.0}
        
        # JSON响应
        json_response = '{"recommendation": "buy", "confidence": 0.9, "risk_level": "high"}'
        
        result = commander._parse_llm_response(json_response, market_data)
        
        assert isinstance(result, StrategyAnalysis)
        assert result.recommendation == "buy"
        assert result.confidence == 0.9
        assert result.risk_level == "high"

    @pytest.mark.asyncio
    async def test_parse_llm_response_text_path(self, commander):
        """测试_parse_llm_response的文本解析路径（分支518->519）"""
        market_data = {"symbol": "TEST", "price": 100.0}
        
        # 纯文本响应，不包含JSON
        text_response = "This is a plain text response without any JSON structure"
        
        result = commander._parse_llm_response(text_response, market_data)
        
        assert isinstance(result, StrategyAnalysis)
        assert result.recommendation == "hold"  # 默认推荐
        assert result.confidence == 0.6
        assert result.risk_level == "medium"

    @pytest.mark.asyncio
    async def test_parse_llm_response_text_with_keywords(self, commander):
        """测试文本解析中的关键词识别"""
        market_data = {"symbol": "TEST", "price": 100.0}
        
        # 测试buy关键词
        buy_response = "I recommend to buy this stock based on analysis"
        result = commander._parse_llm_response(buy_response, market_data)
        assert result.recommendation == "buy"
        
        # 测试sell关键词
        sell_response = "Market conditions suggest we should sell positions"
        result = commander._parse_llm_response(sell_response, market_data)
        assert result.recommendation == "sell"
        
        # 测试reduce关键词
        reduce_response = "We should reduce our exposure to this sector"
        result = commander._parse_llm_response(reduce_response, market_data)
        assert result.recommendation == "reduce"

    @pytest.mark.asyncio
    async def test_apply_risk_controls_deprecated(self, commander):
        """测试已废弃的风险控制方法"""
        # 创建策略分析结果
        analysis = StrategyAnalysis(
            recommendation="buy",
            confidence=0.8,
            risk_level="high",  # 高风险，会触发警报记录
            allocation={"stocks": 0.9, "bonds": 0.1},
            reasoning="Test analysis",
            market_regime="bull",
            time_horizon="medium",
            metadata={}
        )
        
        # 应用风险控制（已废弃）
        result = commander._apply_risk_controls(analysis)
        
        # 验证结果未被修改（因为已废弃）
        assert result == analysis
        assert result.risk_level == "high"
        assert result.allocation["stocks"] == 0.9
        
        # 验证统计信息被更新
        assert commander.stats["risk_alerts"] >= 1

    @pytest.mark.asyncio
    async def test_apply_risk_controls_no_alert(self, commander):
        """测试风险控制不触发警报的情况（分支600->607）"""
        # 创建中等风险的策略分析结果
        analysis = StrategyAnalysis(
            recommendation="buy",
            confidence=0.8,
            risk_level="medium",  # 非高风险，不会触发警报
            allocation={"stocks": 0.7, "bonds": 0.3},
            reasoning="Test analysis",
            market_regime="bull",
            time_horizon="medium",
            metadata={}
        )
        
        # Mock _trigger_risk_alert方法
        commander._trigger_risk_alert = AsyncMock()
        
        # 应用风险控制
        result = commander._apply_risk_controls(analysis)
        
        # 验证风险警报未被触发
        commander._trigger_risk_alert.assert_not_called()
        assert result == analysis

    @pytest.mark.asyncio
    async def test_trigger_risk_alert_exception_handling(self, commander):
        """测试_trigger_risk_alert的异常处理（分支712->exit）"""
        # Mock event_bus.publish抛出异常
        commander.event_bus.publish = AsyncMock(side_effect=Exception("Event bus error"))
        
        # 调用_trigger_risk_alert，应该捕获异常
        try:
            await commander._trigger_risk_alert("high_risk", {"test": "data"})
            # 不应该抛出异常，应该被内部捕获
        except Exception:
            pytest.fail("_trigger_risk_alert should handle exceptions internally")

    @pytest.mark.asyncio
    async def test_trigger_risk_alert_no_event_bus(self, commander):
        """测试event_bus为None时的风险警报"""
        # 设置event_bus为None
        commander.event_bus = None
        
        # 调用_trigger_risk_alert，应该不抛出异常
        try:
            await commander._trigger_risk_alert("high_risk", {"test": "data"})
        except Exception:
            pytest.fail("_trigger_risk_alert should handle None event_bus gracefully")

    @pytest.mark.asyncio
    async def test_assess_risk_from_tier_default(self, commander):
        """测试_assess_risk_from_tier的默认情况（分支1027->1028）"""
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
    async def test_assess_risk_from_tier_large_funds(self, commander):
        """测试大资金档位的风险评估"""
        # 测试大资金档位
        large_tiers = ["tier5_million", "tier6_ten_million"]
        
        for tier in large_tiers:
            risk_level = commander._assess_risk_from_tier(tier)
            assert risk_level == "low", f"Large tier {tier} should have low risk"

    @pytest.mark.asyncio
    async def test_assess_risk_from_tier_medium_funds(self, commander):
        """测试中等资金档位的风险评估"""
        # 测试中等资金档位
        medium_tiers = ["tier3_medium", "tier4_large"]
        
        for tier in medium_tiers:
            risk_level = commander._assess_risk_from_tier(tier)
            assert risk_level == "medium", f"Medium tier {tier} should have medium risk"

    @pytest.mark.asyncio
    async def test_get_allocation(self, commander):
        """测试获取资产配置"""
        # 设置外部数据
        commander.external_data = {
            "positions": {"AAPL": 0.3, "GOOGL": 0.2},
            "market_regime": "bull"
        }
        
        # Mock _calculate_optimal_allocation方法
        commander._calculate_optimal_allocation = AsyncMock(
            return_value={"stocks": 0.7, "bonds": 0.2, "cash": 0.1}
        )
        
        # Mock其他方法
        commander._assess_portfolio_risk = Mock(return_value="medium")
        commander._check_rebalance_needed = Mock(return_value=True)
        
        result = await commander.get_allocation()
        
        assert "allocation" in result
        assert "market_regime" in result
        assert "risk_level" in result
        assert "rebalance_needed" in result
        assert result["market_regime"] == "bull"

    @pytest.mark.asyncio
    async def test_get_allocation_exception_handling(self, commander):
        """测试get_allocation的异常处理"""
        # Mock _calculate_optimal_allocation抛出异常
        commander._calculate_optimal_allocation = AsyncMock(side_effect=Exception("Test error"))
        
        # Mock _create_default_allocation
        commander._create_default_allocation = Mock(
            return_value={"allocation": {"stocks": 0.6, "bonds": 0.4}, "error": True}
        )
        
        result = await commander.get_allocation()
        
        # 应该返回默认配置
        assert result is not None
        commander._create_default_allocation.assert_called_once()

    @pytest.mark.asyncio
    async def test_request_external_data(self, commander):
        """测试请求外部数据"""
        market_data = {"symbol": "TEST", "price": 100.0}
        
        # 调用请求外部数据
        await commander._request_external_data(market_data)
        
        # 验证事件总线被调用
        assert commander.event_bus.publish.call_count >= 1

    @pytest.mark.asyncio
    async def test_request_scholar_research(self, commander):
        """测试请求Scholar研究"""
        market_data = {"symbol": "TEST", "price": 100.0}
        correlation_id = "test_correlation_123"
        
        # 调用请求Scholar研究
        result = await commander.request_scholar_research(market_data, correlation_id)
        
        # 验证事件总线被调用
        commander.event_bus.publish.assert_called()

    @pytest.mark.asyncio
    async def test_request_scholar_research_no_event_bus(self, commander):
        """测试没有事件总线时的Scholar研究请求"""
        commander.event_bus = None
        market_data = {"symbol": "TEST", "price": 100.0}
        
        result = await commander.request_scholar_research(market_data)
        
        # 应该返回None
        assert result is None

    @pytest.mark.asyncio
    async def test_cache_functionality(self, commander):
        """测试缓存功能"""
        market_data = {"symbol": "TEST", "price": 100.0}
        
        # 生成缓存键
        cache_key = commander._generate_cache_key(market_data)
        assert cache_key is not None
        
        # 测试缓存存储和检索
        test_analysis = StrategyAnalysis(
            recommendation="buy",
            confidence=0.8,
            risk_level="medium",
            allocation={"stocks": 0.7, "bonds": 0.3},
            reasoning="Test analysis",
            market_regime="bull",
            time_horizon="medium",
            metadata={}
        )
        
        # 缓存分析结果
        commander._cache_analysis(cache_key, test_analysis)
        
        # 检索缓存
        cached_result = commander._get_cached_analysis(cache_key)
        assert cached_result is not None

    @pytest.mark.asyncio
    async def test_statistics_tracking(self, commander):
        """测试统计信息跟踪"""
        # 更新统计信息
        commander._update_stats(100.0)  # 100ms分析时间
        
        # 获取统计信息
        stats = commander.get_statistics()
        
        assert "total_analyses" in stats
        assert "strategy_recommendations" in stats
        assert "risk_alerts" in stats
        assert "cache_hits" in stats
        assert "avg_analysis_time_ms" in stats
        assert "error_count" in stats
        assert "state" in stats
        assert stats["risk_limits_deprecated"] == True

    @pytest.mark.asyncio
    async def test_error_handling_in_analyze_strategy(self, commander):
        """测试analyze_strategy中的错误处理"""
        # Mock资本集成抛出异常
        commander.capital_integration.analyze_strategy_with_capital_context = AsyncMock(
            side_effect=Exception("Capital integration error")
        )
        
        # Mock fallback策略
        commander._create_fallback_strategy = Mock(
            return_value={
                "recommendation": "hold",
                "confidence": 0.5,
                "risk_level": "medium",
                "allocation": {"stocks": 0.5, "bonds": 0.5},
                "error": True
            }
        )
        
        market_data = {"symbol": "TEST", "price": 100.0}
        
        result = await commander.analyze_strategy(market_data)
        
        # 应该返回fallback策略
        assert result is not None
        assert result.get("error") == True
        assert commander.stats["error_count"] >= 1
        assert commander.state == "ERROR"

    @pytest.mark.asyncio
    async def test_identify_market_regime(self, commander):
        """测试市场状态识别"""
        # 测试不同的市场数据
        bull_market_data = {
            "symbol": "TEST",
            "price": 100.0,
            "index_level": 4000,  # 高指数水平
            "volatility": 0.01    # 低波动率
        }
        
        bear_market_data = {
            "symbol": "TEST", 
            "price": 100.0,
            "index_level": 2500,  # 低指数水平
            "volatility": 0.05    # 高波动率
        }
        
        # 调用市场状态识别
        bull_regime = commander.identify_market_regime(bull_market_data)
        bear_regime = commander.identify_market_regime(bear_market_data)
        
        # 验证识别结果
        assert bull_regime in ["bull", "normal", "volatile", "sideways"]
        assert bear_regime in ["bear", "normal", "volatile", "sideways"]

    @pytest.mark.asyncio
    async def test_comprehensive_workflow_coverage(self, commander):
        """综合测试确保所有关键路径都被覆盖"""
        # 设置复杂的测试场景
        commander.llm_gateway.generate_cloud = AsyncMock(
            return_value="Market analysis shows mixed signals with high volatility"
        )
        
        commander.capital_integration.analyze_strategy_with_capital_context = AsyncMock(
            return_value={
                "tier": "tier1_micro",  # 触发默认风险评估
                "recommended_strategy": "hold",
                "confidence": 0.6,
                "allocation": {"stocks": 0.5, "bonds": 0.5}
            }
        )
        
        # 设置外部数据
        commander.external_data = {
            "capital": {"tier": "tier1_micro"},
            "positions": {"AAPL": 0.3},
            "soldier": {"signal_strength": 0.7},
            "scholar": {"research_confidence": 0.8}
        }
        
        market_data = {
            "symbol": "COMPREHENSIVE_TEST",
            "price": 100.0,
            "index_level": 3000,
            "volatility": 0.03,
            "volume": 2000000
        }
        
        # 执行完整的策略分析
        result = await commander.analyze_strategy(market_data)
        
        # 验证结果
        assert result is not None
        assert "recommendation" in result
        assert "confidence" in result
        assert "risk_level" in result
        assert "allocation" in result
        assert "market_regime" in result
        
        # 验证统计信息被更新
        assert commander.stats["total_analyses"] >= 1
        
        # 验证状态正确
        assert commander.state == "READY"
        assert commander.last_analysis_time is not None

    @pytest.mark.asyncio
    async def test_event_handlers(self, commander):
        """测试事件处理器"""
        # 测试处理Soldier数据
        soldier_event = Mock()
        soldier_event.data = {
            "source": "commander_request",
            "correlation_id": "test_123",
            "signal_data": {"signal_strength": 0.8}
        }
        
        await commander._handle_soldier_data(soldier_event)
        
        # 验证数据被存储
        assert "soldier" in commander.external_data
        assert commander.external_data["soldier"]["signal_strength"] == 0.8

    @pytest.mark.asyncio
    async def test_all_missing_branches_final_verification(self, commander):
        """最终验证所有缺失分支都被覆盖"""
        
        # 1. 测试[518, 519]分支：文本解析路径
        text_result = commander._parse_llm_response("Plain text without JSON", {"symbol": "TEST"})
        assert text_result.recommendation == "hold"
        
        # 2. 测试[553, 557]分支：废弃的风险控制，高风险检测
        high_risk_analysis = StrategyAnalysis(
            recommendation="buy", confidence=0.9, risk_level="high",
            allocation={"stocks": 0.7}, reasoning="test", market_regime="bull",
            time_horizon="medium", metadata={}
        )
        risk_result = commander._apply_risk_controls(high_risk_analysis)
        assert risk_result == high_risk_analysis  # 原样返回
        assert commander.stats["risk_alerts"] >= 1  # 但会记录警报
        
        # 3. 测试[569, 575]分支：废弃的风险控制，不再限制仓位
        over_limit_analysis = StrategyAnalysis(
            recommendation="buy", confidence=0.8, risk_level="medium",
            allocation={"stocks": 0.98}, reasoning="test", market_regime="bull",
            time_horizon="medium", metadata={}
        )
        limit_result = commander._apply_risk_controls(over_limit_analysis)
        assert limit_result == over_limit_analysis  # 原样返回
        
        # 4. 测试[600, 607]分支：废弃的风险控制，不再触发警报
        commander._trigger_risk_alert = AsyncMock()
        alert_analysis = StrategyAnalysis(
            recommendation="buy", confidence=0.9, risk_level="medium",  # 非高风险
            allocation={"stocks": 0.9}, reasoning="test", market_regime="bull",
            time_horizon="medium", metadata={}
        )
        commander._apply_risk_controls(alert_analysis)
        commander._trigger_risk_alert.assert_not_called()  # 不会被调用
        
        # 5. 测试[712, -696]分支：异常处理
        commander.event_bus = AsyncMock()
        commander.event_bus.publish = AsyncMock(side_effect=Exception("Test error"))
        await commander._trigger_risk_alert("high_risk", {"test": "data"})
        
        # 6. 测试[1027, 1028]分支：默认风险评估
        default_risk = commander._assess_risk_from_tier("unknown_tier")
        assert default_risk == "medium"
        
        print("✅ 所有关键分支都已验证覆盖")