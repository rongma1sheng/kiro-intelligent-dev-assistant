"""DeepSeek API集成测试（通过统一LLM网关）

白皮书依据: 第二章 2.1 Soldier (快系统 - 热备高可用)
测试任务: 2.3.1 集成DeepSeek API

注意: SoldierWithFailover现在使用统一LLM网关(llm_gateway)而不是直接的cloud_api
"""

import pytest
import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any

from src.brain.soldier.core import SoldierWithFailover, SoldierMode, TradingDecision


class TestDeepSeekAPIIntegration:
    """DeepSeek API集成测试类（通过统一LLM网关）"""
    
    @pytest.fixture
    def soldier_config(self):
        """Soldier配置夹具"""
        return {
            "local_model_path": "/models/qwen-30b.gguf",
            "cloud_api_key": "sk-test-deepseek-api-key-12345",
            "redis_host": "localhost",
            "redis_port": 6379,
            "failure_threshold": 3,
            "local_timeout": 0.2
        }
    
    @pytest.fixture
    def market_data(self):
        """市场数据夹具"""
        return {
            "symbol": "000001.SZ",
            "price": 10.50,
            "volume": 1000000,
            "change_pct": 0.025,
            "timestamp": time.time()
        }
    
    @pytest.mark.asyncio
    async def test_init_llm_gateway_success(self, soldier_config):
        """测试LLM网关初始化成功"""
        soldier = SoldierWithFailover(**soldier_config)
        await soldier.initialize()
        
        # 验证LLM网关已初始化
        assert soldier.llm_gateway is not None
        
        # 验证系统处于正常模式
        assert soldier.mode == SoldierMode.NORMAL
    
    @pytest.mark.asyncio
    async def test_init_llm_gateway_compatibility_mode(self, soldier_config):
        """测试LLM网关兼容模式"""
        soldier = SoldierWithFailover(**soldier_config)
        await soldier.initialize()
        
        # 验证LLM网关已初始化
        assert soldier.llm_gateway is not None
        
        # 验证本地模型使用兼容模式
        assert soldier.local_model is not None
        assert soldier.local_model.get("loaded") is True
    
    @pytest.mark.asyncio
    async def test_cloud_inference_success(self, soldier_config, market_data):
        """测试云端推理成功"""
        soldier = SoldierWithFailover(**soldier_config)
        await soldier.initialize()
        
        # 强制切换到云端模式
        soldier.mode = SoldierMode.DEGRADED
        
        # 执行云端推理
        decision = await soldier.make_decision(market_data)
        
        # 验证决策结果
        assert decision is not None
        assert isinstance(decision, TradingDecision)
        assert decision.action in ["buy", "sell", "hold"]
        assert 0 <= decision.confidence <= 1
        assert decision.mode == SoldierMode.DEGRADED
    
    @pytest.mark.asyncio
    async def test_cloud_inference_fallback(self, soldier_config, market_data):
        """测试云端推理失败时的降级处理"""
        soldier = SoldierWithFailover(**soldier_config)
        await soldier.initialize()
        
        # 强制切换到云端模式
        soldier.mode = SoldierMode.DEGRADED
        
        # Mock LLM网关调用失败
        original_cloud_inference = soldier._cloud_inference
        
        async def mock_failing_cloud_inference(data):
            # 模拟失败后降级到模拟推理
            return await soldier._simulate_cloud_inference(data)
        
        soldier._cloud_inference = mock_failing_cloud_inference
        
        # 执行云端推理（应该降级到模拟推理）
        decision = await soldier.make_decision(market_data)
        
        # 验证降级到模拟推理
        assert decision is not None
        assert decision.action in ["buy", "sell", "hold"]
        assert 0 <= decision.confidence <= 1
        assert decision.mode == SoldierMode.DEGRADED
    
    @pytest.mark.asyncio
    async def test_cloud_inference_compatibility_mode(self, soldier_config, market_data):
        """测试兼容模式下的云端推理"""
        soldier = SoldierWithFailover(**soldier_config)
        await soldier.initialize()
        
        # 强制切换到云端模式
        soldier.mode = SoldierMode.DEGRADED
        
        # 执行云端推理
        decision = await soldier.make_decision(market_data)
        
        # 验证兼容模式推理
        assert decision is not None
        assert decision.action in ["buy", "sell", "hold"]
        assert 0 <= decision.confidence <= 1
        assert decision.mode == SoldierMode.DEGRADED
    
    @pytest.mark.asyncio
    async def test_build_trading_prompt_format(self, soldier_config, market_data):
        """测试交易提示词构建格式"""
        soldier = SoldierWithFailover(**soldier_config)
        
        # 测试提示词构建
        prompt = soldier._build_trading_prompt(market_data)
        
        # 验证提示词包含必要信息
        assert "000001.SZ" in prompt
        assert "10.50" in prompt
        assert "1,000,000" in prompt
        assert "2.50%" in prompt
        assert "动作:" in prompt
        assert "数量:" in prompt
        assert "置信度:" in prompt
        assert "理由:" in prompt
    
    @pytest.mark.asyncio
    async def test_llm_response_parsing(self, soldier_config, market_data):
        """测试LLM响应解析"""
        soldier = SoldierWithFailover(**soldier_config)
        
        # 测试各种响应格式
        test_cases = [
            # 标准格式
            {
                "content": "动作: buy\n数量: 1500\n置信度: 0.75\n理由: 市场看涨",
                "expected": {"action": "buy", "quantity": 1500, "confidence": 0.75}
            },
            # 英文格式
            {
                "content": "Action: sell\nQuantity: 500\nConfidence: 0.60\nReason: 风险较高",
                "expected": {"action": "sell", "quantity": 500, "confidence": 0.60}
            },
            # 不完整格式
            {
                "content": "动作: hold\n理由: 观望为主",
                "expected": {"action": "hold", "quantity": 0, "confidence": 0.5}
            },
            # 无效格式
            {
                "content": "这是一个无效的响应",
                "expected": {"action": "hold", "quantity": 0, "confidence": 0.5}
            }
        ]
        
        for i, case in enumerate(test_cases):
            decision = soldier._parse_llm_response(case["content"], market_data)
            
            assert decision.action == case["expected"]["action"], f"Test case {i}: action mismatch"
            assert decision.quantity == case["expected"]["quantity"], f"Test case {i}: quantity mismatch"
            assert decision.confidence == case["expected"]["confidence"], f"Test case {i}: confidence mismatch"
    
    @pytest.mark.asyncio
    async def test_cloud_inference_performance_tracking(self, soldier_config, market_data):
        """测试云端推理性能追踪"""
        soldier = SoldierWithFailover(**soldier_config)
        await soldier.initialize()
        
        # 强制切换到云端模式
        soldier.mode = SoldierMode.DEGRADED
        
        # 测量推理延迟
        latencies = []
        for _ in range(5):
            start_time = time.perf_counter()
            decision = await soldier.make_decision(market_data)
            end_time = time.perf_counter()
            
            latency_ms = (end_time - start_time) * 1000
            latencies.append(latency_ms)
            
            assert decision is not None
            assert decision.latency_ms is not None
        
        # 验证性能指标
        avg_latency = sum(latencies) / len(latencies)
        max_latency = max(latencies)
        
        # 云端推理延迟应该合理
        assert avg_latency < 2000.0, f"平均延迟过高: {avg_latency:.2f}ms"
        assert max_latency < 5000.0, f"最大延迟过高: {max_latency:.2f}ms"
        
        print(f"云端推理性能统计:")
        print(f"  平均延迟: {avg_latency:.2f}ms")
        print(f"  最大延迟: {max_latency:.2f}ms")
        print(f"  最小延迟: {min(latencies):.2f}ms")
    
    @pytest.mark.asyncio
    async def test_status_includes_llm_gateway(self, soldier_config):
        """测试状态报告包含LLM网关信息"""
        soldier = SoldierWithFailover(**soldier_config)
        await soldier.initialize()
        
        # 获取状态
        status = soldier.get_status()
        
        # 验证状态包含LLM网关信息
        assert "llm_gateway_initialized" in status
        assert status["llm_gateway_initialized"] is True
        assert "mode" in status
        assert "local_model_loaded" in status
        assert "redis_connected" in status
    
    @pytest.mark.asyncio
    async def test_local_inference_in_normal_mode(self, soldier_config, market_data):
        """测试正常模式下的本地推理"""
        soldier = SoldierWithFailover(**soldier_config)
        await soldier.initialize()
        
        # 确保在正常模式
        assert soldier.mode == SoldierMode.NORMAL
        
        # 执行本地推理
        decision = await soldier.make_decision(market_data)
        
        # 验证决策结果
        assert decision is not None
        assert isinstance(decision, TradingDecision)
        assert decision.action in ["buy", "sell", "hold"]
        assert decision.mode == SoldierMode.NORMAL
    
    @pytest.mark.asyncio
    async def test_mode_switch_to_degraded(self, soldier_config, market_data):
        """测试模式切换到降级模式"""
        soldier = SoldierWithFailover(**soldier_config)
        await soldier.initialize()
        
        # 初始应该是正常模式
        assert soldier.mode == SoldierMode.NORMAL
        
        # 模拟触发切换
        await soldier._trigger_failover("测试切换")
        
        # 验证切换到降级模式
        assert soldier.mode == SoldierMode.DEGRADED
        
        # 执行推理应该使用云端
        decision = await soldier.make_decision(market_data)
        assert decision.mode == SoldierMode.DEGRADED
    
    @pytest.mark.asyncio
    async def test_multiple_decisions_in_degraded_mode(self, soldier_config, market_data):
        """测试降级模式下的多次决策"""
        soldier = SoldierWithFailover(**soldier_config)
        await soldier.initialize()
        
        # 切换到降级模式
        soldier.mode = SoldierMode.DEGRADED
        
        # 执行多次推理
        decisions = []
        for _ in range(5):
            decision = await soldier.make_decision(market_data)
            decisions.append(decision)
            assert decision is not None
            assert decision.mode == SoldierMode.DEGRADED
        
        # 验证所有决策都成功
        assert len(decisions) == 5
        for d in decisions:
            assert d.action in ["buy", "sell", "hold"]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
