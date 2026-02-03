"""Commander战略生成功能测试

白皮书依据: 第二章 2.2 Commander (慢系统)
验证需求: 需求5.1, 需求5.2, 需求5.3, 需求5.4, 需求5.5
"""

import pytest
import asyncio
import json
import time
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from src.brain.commander.core import (
    BudgetExceededError,
    Commander
)


class TestStrategyGeneration:
    """测试战略生成功能
    
    白皮书依据: 第二章 2.2 Commander (慢系统)
    验证需求: 需求5.1, 需求5.2, 需求5.3, 需求5.4
    """
    
    @pytest.mark.asyncio
    async def test_generate_strategy_success_compatible_mode(self):
        """测试战略生成成功（通过Mock LLM网关）"""
        commander = Commander(api_key="sk-test-key")
        
        # Mock LLM网关响应
        mock_llm_response = MagicMock()
        mock_llm_response.success = True
        mock_llm_response.content = json.dumps({
            "strategy_type": "momentum",
            "risk_level": "medium",
            "position_limit": 0.6,
            "target_sectors": ["科技", "新能源"],
            "avoid_sectors": ["房地产"],
            "reasoning": "市场情绪积极，建议采用动量策略"
        })
        mock_llm_response.tokens_used = 500
        mock_llm_response.cost = 0.001
        mock_llm_response.error_message = None
        
        # Mock LLM网关
        mock_gateway = AsyncMock()
        mock_gateway.call_llm = AsyncMock(return_value=mock_llm_response)
        commander.llm_gateway = mock_gateway
        commander._initialized = True
        commander.redis_client = {"mode": "compatible"}
        
        market_state = {
            "market_sentiment": 0.7,
            "technical_indicators": {
                "rsi": 65,
                "macd": "bullish",
                "moving_average": "golden_cross"
            },
            "fundamental_data": {
                "pe_ratio": 15.5,
                "pb_ratio": 2.3
            },
            "recent_reports": [
                {"industry": "科技", "rating": "买入"},
                {"industry": "新能源", "rating": "增持"}
            ]
        }
        
        result = await commander.generate_strategy(market_state)
        
        # 验证返回结果结构
        assert "strategy_type" in result
        assert "risk_level" in result
        assert "position_limit" in result
        assert "target_sectors" in result
        assert "avoid_sectors" in result
        assert "reasoning" in result
        assert "valid_until" in result
        assert "tokens_used" in result
        assert "cost" in result
        
        # 验证数据类型
        assert isinstance(result["strategy_type"], str)
        assert result["strategy_type"] in ["momentum", "mean_reversion", "defensive", "balanced"]
        
        assert isinstance(result["risk_level"], str)
        assert result["risk_level"] in ["low", "medium", "high"]
        
        assert isinstance(result["position_limit"], (int, float))
        assert 0 <= result["position_limit"] <= 1
        
        assert isinstance(result["target_sectors"], list)
        assert isinstance(result["avoid_sectors"], list)
        assert isinstance(result["reasoning"], str)
        assert isinstance(result["valid_until"], (int, float))
        assert isinstance(result["tokens_used"], int)
        assert isinstance(result["cost"], float)
        
        # 验证成本已记录
        assert commander.cost_tracker.daily_cost > 0
        assert commander.cost_tracker.call_count == 1
    
    @pytest.mark.asyncio
    async def test_generate_strategy_empty_market_state(self):
        """测试空市场状态输入"""
        commander = Commander(api_key="sk-test-key")
        
        # 测试None
        with pytest.raises(ValueError, match="市场状态数据无效"):
            await commander.generate_strategy(None)
        
        # 测试空字典
        with pytest.raises(ValueError, match="市场状态数据无效"):
            await commander.generate_strategy({})
        
        # 测试非字典类型
        with pytest.raises(ValueError, match="市场状态数据无效"):
            await commander.generate_strategy("invalid")
    
    @pytest.mark.asyncio
    async def test_generate_strategy_budget_exceeded(self):
        """测试预算超限"""
        commander = Commander(
            api_key="sk-test-key",
            daily_budget=0.001,  # 极小的预算
            monthly_budget=0.01
        )
        
        market_state = {
            "market_sentiment": 0.5,
            "technical_indicators": {},
            "fundamental_data": {},
            "recent_reports": []
        }
        
        with pytest.raises(BudgetExceededError, match="预算不足"):
            await commander.generate_strategy(market_state)
    
    @pytest.mark.asyncio
    async def test_generate_strategy_with_real_api(self):
        """测试战略生成（通过Mock LLM网关）"""
        # Mock LLM网关响应
        mock_llm_response = MagicMock()
        mock_llm_response.success = True
        mock_llm_response.content = json.dumps({
            "strategy_type": "momentum",
            "risk_level": "medium",
            "position_limit": 0.6,
            "target_sectors": ["科技", "新能源", "医药"],
            "avoid_sectors": ["房地产", "传统制造"],
            "reasoning": "市场情绪积极，技术面强势，建议采用动量策略。重点关注科技、新能源等高成长行业，规避房地产等周期性行业。"
        })
        mock_llm_response.tokens_used = 1500
        mock_llm_response.cost = 0.003
        mock_llm_response.error_message = None
        
        # Mock Redis
        mock_redis = MagicMock()
        mock_redis_client = AsyncMock()
        mock_redis_client.ping = AsyncMock()
        mock_redis_client.set = AsyncMock()
        mock_redis_client.expire = AsyncMock()
        mock_redis_client.publish = AsyncMock()
        mock_redis.Redis.return_value = mock_redis_client
        
        with patch.dict('sys.modules', {
            'redis.asyncio': mock_redis
        }):
            commander = Commander(api_key="sk-test-key")
            
            # Mock LLM网关
            mock_gateway = AsyncMock()
            mock_gateway.call_llm = AsyncMock(return_value=mock_llm_response)
            commander.llm_gateway = mock_gateway
            commander._initialized = True
            commander.redis_client = mock_redis_client
            
            market_state = {
                "market_sentiment": 0.7,
                "technical_indicators": {"rsi": 65},
                "fundamental_data": {"pe_ratio": 15.5},
                "recent_reports": []
            }
            
            result = await commander.generate_strategy(market_state)
            
            # 验证结果
            assert result["strategy_type"] == "momentum"
            assert result["risk_level"] == "medium"
            assert result["position_limit"] == 0.6
            assert len(result["target_sectors"]) == 3
            assert len(result["avoid_sectors"]) == 2
            assert result["tokens_used"] == 1500
            
            # 验证Redis写入被调用
            mock_redis_client.set.assert_called_once()
            mock_redis_client.expire.assert_called_once()
            mock_redis_client.publish.assert_called_once()
            
            # 验证LLM网关被调用
            mock_gateway.call_llm.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_generate_strategy_api_failure(self):
        """测试API调用失败"""
        commander = Commander(api_key="sk-test-key")
        
        # 直接设置API客户端为真实模式，但会失败
        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(
            side_effect=Exception("API调用失败")
        )
        commander.api_client = mock_client
        
        # 设置Redis客户端（兼容模式）
        commander.redis_client = {"mode": "compatible"}
        
        market_state = {
            "market_sentiment": 0.5,
            "technical_indicators": {},
            "fundamental_data": {},
            "recent_reports": []
        }
        
        with pytest.raises(RuntimeError, match="战略生成失败"):
            await commander.generate_strategy(market_state)
    
    @pytest.mark.asyncio
    async def test_generate_strategy_redis_write_failure(self):
        """测试Redis写入失败"""
        commander = Commander(api_key="sk-test-key")
        
        # Mock LLM网关响应
        mock_llm_response = MagicMock()
        mock_llm_response.success = True
        mock_llm_response.content = json.dumps({
            "strategy_type": "balanced",
            "risk_level": "medium",
            "position_limit": 0.5,
            "target_sectors": ["科技"],
            "avoid_sectors": ["房地产"],
            "reasoning": "测试战略"
        })
        mock_llm_response.tokens_used = 500
        mock_llm_response.cost = 0.001
        mock_llm_response.error_message = None
        
        # Mock LLM网关
        mock_gateway = AsyncMock()
        mock_gateway.call_llm = AsyncMock(return_value=mock_llm_response)
        commander.llm_gateway = mock_gateway
        commander._initialized = True
        
        # 设置Redis客户端为真实模式，但会失败
        mock_redis_client = AsyncMock()
        mock_redis_client.set = AsyncMock(side_effect=Exception("Redis写入失败"))
        commander.redis_client = mock_redis_client
        
        market_state = {
            "market_sentiment": 0.5,
            "technical_indicators": {},
            "fundamental_data": {},
            "recent_reports": []
        }
        
        with pytest.raises(RuntimeError, match="Redis写入失败"):
            await commander.generate_strategy(market_state)
    
    @pytest.mark.asyncio
    async def test_generate_strategy_use_last_strategy_on_failure(self):
        """测试失败时使用上次战略"""
        # Mock LLM网关响应 - 失败
        mock_llm_response = MagicMock()
        mock_llm_response.success = False
        mock_llm_response.content = None
        mock_llm_response.tokens_used = 0
        mock_llm_response.cost = 0.0
        mock_llm_response.error_message = "API调用失败"
        
        # Mock Redis - 有上次战略
        mock_redis = MagicMock()
        mock_redis_client = AsyncMock()
        mock_redis_client.ping = AsyncMock()
        
        last_strategy = {
            "strategy_type": "defensive",
            "risk_level": "low",
            "position_limit": 0.3,
            "target_sectors": ["消费"],
            "avoid_sectors": ["科技"],
            "reasoning": "上次的战略",
            "valid_until": time.time() + 86400,
            "tokens_used": 1000
        }
        
        mock_redis_client.get = AsyncMock(
            return_value=json.dumps(last_strategy)
        )
        mock_redis.Redis.return_value = mock_redis_client
        
        with patch.dict('sys.modules', {
            'redis.asyncio': mock_redis
        }):
            commander = Commander(api_key="sk-test-key")
            
            # Mock LLM网关
            mock_gateway = AsyncMock()
            mock_gateway.call_llm = AsyncMock(return_value=mock_llm_response)
            commander.llm_gateway = mock_gateway
            commander._initialized = True
            commander.redis_client = mock_redis_client
            
            market_state = {
                "market_sentiment": 0.5,
                "technical_indicators": {},
                "fundamental_data": {},
                "recent_reports": []
            }
            
            result = await commander.generate_strategy(market_state)
            
            # 验证返回的是上次战略
            assert result["strategy_type"] == "defensive"
            assert result["risk_level"] == "low"
            assert result["reasoning"] == "上次的战略"
    
    @pytest.mark.asyncio
    async def test_generate_strategy_notify_soldier(self):
        """测试通知Soldier"""
        # Mock LLM网关响应
        mock_llm_response = MagicMock()
        mock_llm_response.success = True
        mock_llm_response.content = json.dumps({
            "strategy_type": "balanced",
            "risk_level": "medium",
            "position_limit": 0.5,
            "target_sectors": ["科技"],
            "avoid_sectors": ["房地产"],
            "reasoning": "测试战略"
        })
        mock_llm_response.tokens_used = 500
        mock_llm_response.cost = 0.001
        mock_llm_response.error_message = None
        
        # Mock Redis
        mock_redis = MagicMock()
        mock_redis_client = AsyncMock()
        mock_redis_client.ping = AsyncMock()
        mock_redis_client.set = AsyncMock()
        mock_redis_client.expire = AsyncMock()
        mock_redis_client.publish = AsyncMock()
        mock_redis.Redis.return_value = mock_redis_client
        
        with patch.dict('sys.modules', {'redis.asyncio': mock_redis}):
            commander = Commander(api_key="sk-test-key")
            
            # Mock LLM网关
            mock_gateway = AsyncMock()
            mock_gateway.call_llm = AsyncMock(return_value=mock_llm_response)
            commander.llm_gateway = mock_gateway
            commander._initialized = True
            commander.redis_client = mock_redis_client
            
            market_state = {
                "market_sentiment": 0.5,
                "technical_indicators": {},
                "fundamental_data": {},
                "recent_reports": []
            }
            
            result = await commander.generate_strategy(market_state, strategy_key="test_strategy")
            
            # 验证Redis发布被调用
            mock_redis_client.publish.assert_called_once()
            
            # 验证发布的消息格式
            call_args = mock_redis_client.publish.call_args
            assert call_args[0][0] == "soldier_notifications"
            
            message = json.loads(call_args[0][1])
            assert message["type"] == "strategy_update"
            assert message["strategy_key"] == "test_strategy"
            assert "timestamp" in message

    @pytest.mark.asyncio
    async def test_generate_multiple_strategies(self):
        """测试连续生成多个战略"""
        commander = Commander(api_key="sk-test-key")
        
        # Mock LLM网关响应
        mock_llm_response = MagicMock()
        mock_llm_response.success = True
        mock_llm_response.content = json.dumps({
            "strategy_type": "balanced",
            "risk_level": "medium",
            "position_limit": 0.5,
            "target_sectors": ["科技"],
            "avoid_sectors": ["房地产"],
            "reasoning": "测试战略"
        })
        mock_llm_response.tokens_used = 500
        mock_llm_response.cost = 0.001
        mock_llm_response.error_message = None
        
        # Mock LLM网关
        mock_gateway = AsyncMock()
        mock_gateway.call_llm = AsyncMock(return_value=mock_llm_response)
        commander.llm_gateway = mock_gateway
        commander._initialized = True
        commander.redis_client = {"mode": "compatible"}
        
        market_states = [
            {
                "market_sentiment": 0.8,
                "technical_indicators": {"rsi": 70},
                "fundamental_data": {},
                "recent_reports": []
            },
            {
                "market_sentiment": 0.5,
                "technical_indicators": {"rsi": 50},
                "fundamental_data": {},
                "recent_reports": []
            },
            {
                "market_sentiment": 0.3,
                "technical_indicators": {"rsi": 30},
                "fundamental_data": {},
                "recent_reports": []
            }
        ]
        
        for i, market_state in enumerate(market_states, 1):
            result = await commander.generate_strategy(market_state)
            
            # 验证每次生成都成功
            assert "strategy_type" in result
            assert "cost" in result
            
            # 验证成本累积
            assert commander.cost_tracker.call_count == i
            assert commander.cost_tracker.daily_cost > 0
    
    @pytest.mark.asyncio
    async def test_generate_strategy_invalid_json_response(self):
        """测试API返回无效JSON"""
        commander = Commander(api_key="sk-test-key")
        
        # Mock LLM网关返回无效JSON
        mock_llm_response = MagicMock()
        mock_llm_response.success = True
        mock_llm_response.content = "这不是有效的JSON"
        mock_llm_response.tokens_used = 100
        mock_llm_response.cost = 0.001
        mock_llm_response.error_message = None
        
        # Mock LLM网关
        mock_gateway = AsyncMock()
        mock_gateway.call_llm = AsyncMock(return_value=mock_llm_response)
        commander.llm_gateway = mock_gateway
        commander._initialized = True
        commander.redis_client = {"mode": "compatible"}
        
        market_state = {
            "market_sentiment": 0.5,
            "technical_indicators": {},
            "fundamental_data": {},
            "recent_reports": []
        }
        
        # 当JSON解析失败时，会返回默认结构而不是抛出异常
        result = await commander.generate_strategy(market_state)
        assert result["strategy_type"] == "balanced"
        assert result["risk_level"] == "medium"
    
    @pytest.mark.asyncio
    async def test_generate_strategy_empty_api_response(self):
        """测试API返回空响应"""
        commander = Commander(api_key="sk-test-key")
        
        # Mock LLM网关返回空内容
        mock_llm_response = MagicMock()
        mock_llm_response.success = True
        mock_llm_response.content = ""
        mock_llm_response.tokens_used = 0
        mock_llm_response.cost = 0.0
        mock_llm_response.error_message = None
        
        # Mock LLM网关
        mock_gateway = AsyncMock()
        mock_gateway.call_llm = AsyncMock(return_value=mock_llm_response)
        commander.llm_gateway = mock_gateway
        commander._initialized = True
        commander.redis_client = {"mode": "compatible"}
        
        market_state = {
            "market_sentiment": 0.5,
            "technical_indicators": {},
            "fundamental_data": {},
            "recent_reports": []
        }
        
        # 当返回空内容时，会返回默认结构
        result = await commander.generate_strategy(market_state)
        assert result["strategy_type"] == "balanced"
        assert result["risk_level"] == "medium"
    
    def test_build_strategy_prompt(self):
        """测试构建战略提示词"""
        commander = Commander(api_key="sk-test-key")
        
        market_state = {
            "market_sentiment": 0.7,
            "technical_indicators": {
                "rsi": 65,
                "macd": "bullish"
            },
            "fundamental_data": {
                "pe_ratio": 15.5
            },
            "recent_reports": [
                {"industry": "科技", "rating": "买入"},
                {"industry": "新能源", "rating": "增持"}
            ]
        }
        
        prompt = commander._build_strategy_prompt(market_state)
        
        # 验证提示词包含必要内容
        assert "请基于以下市场分析生成交易战略" in prompt
        assert "JSON格式" in prompt
        assert "0.70" in prompt  # 市场情绪
        assert "strategy_type" in prompt
        assert "risk_level" in prompt
        assert "position_limit" in prompt
        assert "target_sectors" in prompt
        assert "avoid_sectors" in prompt
        assert "reasoning" in prompt
        
        # 验证战略类型说明
        assert "momentum" in prompt
        assert "mean_reversion" in prompt
        assert "defensive" in prompt
        assert "balanced" in prompt
        
        # 验证提示词长度合理
        assert len(prompt) < 5000


class TestStrategyGenerationIntegration:
    """测试战略生成集成场景"""
    
    @pytest.mark.asyncio
    async def test_full_strategy_workflow(self):
        """测试完整的战略生成工作流"""
        # Mock LLM网关响应
        mock_llm_response = MagicMock()
        mock_llm_response.success = True
        mock_llm_response.content = json.dumps({
            "strategy_type": "balanced",
            "risk_level": "medium",
            "position_limit": 0.5,
            "target_sectors": ["科技", "消费", "医药"],
            "avoid_sectors": ["房地产"],
            "reasoning": "市场方向不明确，建议采用平衡策略，分散投资于多个行业。"
        })
        mock_llm_response.tokens_used = 1200
        mock_llm_response.cost = 0.002
        mock_llm_response.error_message = None
        
        # Mock Redis
        mock_redis = MagicMock()
        mock_redis_client = AsyncMock()
        mock_redis_client.ping = AsyncMock()
        mock_redis_client.set = AsyncMock()
        mock_redis_client.expire = AsyncMock()
        mock_redis_client.publish = AsyncMock()
        mock_redis_client.close = AsyncMock()
        mock_redis.Redis.return_value = mock_redis_client
        
        with patch.dict('sys.modules', {
            'redis.asyncio': mock_redis
        }):
            # 1. 创建Commander
            commander = Commander(
                api_key="sk-test-key",
                daily_budget=50.0,
                monthly_budget=1500.0
            )
            
            # 2. Mock LLM网关
            mock_gateway = AsyncMock()
            mock_gateway.call_llm = AsyncMock(return_value=mock_llm_response)
            mock_gateway.close = AsyncMock()
            commander.llm_gateway = mock_gateway
            commander._initialized = True
            commander.redis_client = mock_redis_client
            
            # 3. 生成战略
            market_state = {
                "market_sentiment": 0.5,
                "technical_indicators": {
                    "rsi": 50,
                    "macd": "neutral"
                },
                "fundamental_data": {
                    "pe_ratio": 18.0
                },
                "recent_reports": []
            }
            
            result = await commander.generate_strategy(market_state, strategy_key="daily_strategy")
            
            # 4. 验证结果
            assert result["strategy_type"] == "balanced"
            assert result["risk_level"] == "medium"
            assert result["position_limit"] == 0.5
            assert result["cost"] > 0
            
            # 5. 验证Redis写入
            mock_redis_client.set.assert_called_once()
            call_args = mock_redis_client.set.call_args
            assert call_args[0][0] == "daily_strategy"
            
            # 验证写入的数据
            written_data = json.loads(call_args[0][1])
            assert written_data["strategy_type"] == "balanced"
            
            # 6. 验证过期时间设置
            mock_redis_client.expire.assert_called_once_with("daily_strategy", 172800)
            
            # 7. 验证Soldier通知
            mock_redis_client.publish.assert_called_once()
            publish_args = mock_redis_client.publish.call_args
            assert publish_args[0][0] == "soldier_notifications"
            
            notification = json.loads(publish_args[0][1])
            assert notification["type"] == "strategy_update"
            assert notification["strategy_key"] == "daily_strategy"
            
            # 8. 验证成本追踪
            status = commander.get_status()
            assert status["cost_tracker"]["daily_cost"] > 0
            assert status["cost_tracker"]["call_count"] == 1
            
            # 9. 关闭
            await commander.close()
    
    @pytest.mark.asyncio
    async def test_strategy_generation_with_different_market_conditions(self):
        """测试不同市场条件下的战略生成"""
        commander = Commander(api_key="sk-test-key")
        
        # Mock LLM网关响应
        mock_llm_response = MagicMock()
        mock_llm_response.success = True
        mock_llm_response.content = json.dumps({
            "strategy_type": "balanced",
            "risk_level": "medium",
            "position_limit": 0.5,
            "target_sectors": ["科技"],
            "avoid_sectors": ["房地产"],
            "reasoning": "测试战略"
        })
        mock_llm_response.tokens_used = 500
        mock_llm_response.cost = 0.001
        mock_llm_response.error_message = None
        
        # Mock LLM网关
        mock_gateway = AsyncMock()
        mock_gateway.call_llm = AsyncMock(return_value=mock_llm_response)
        commander.llm_gateway = mock_gateway
        commander._initialized = True
        commander.redis_client = {"mode": "compatible"}
        
        # 测试场景1: 牛市（高情绪）
        bull_market = {
            "market_sentiment": 0.9,
            "technical_indicators": {"rsi": 75},
            "fundamental_data": {},
            "recent_reports": []
        }
        
        result1 = await commander.generate_strategy(bull_market)
        # 验证返回的战略类型是有效的
        assert result1["strategy_type"] in ["momentum", "mean_reversion", "defensive", "balanced"]
        
        # 测试场景2: 熊市（低情绪）
        bear_market = {
            "market_sentiment": 0.2,
            "technical_indicators": {"rsi": 25},
            "fundamental_data": {},
            "recent_reports": []
        }
        
        result2 = await commander.generate_strategy(bear_market)
        # 验证返回的战略类型是有效的
        assert result2["strategy_type"] in ["momentum", "mean_reversion", "defensive", "balanced"]
        
        # 测试场景3: 震荡市（中等情绪）
        sideways_market = {
            "market_sentiment": 0.5,
            "technical_indicators": {"rsi": 50},
            "fundamental_data": {},
            "recent_reports": []
        }
        
        result3 = await commander.generate_strategy(sideways_market)
        # 验证返回的战略类型是有效的
        assert result3["strategy_type"] in ["momentum", "mean_reversion", "defensive", "balanced"]
        
        # 验证所有战略都有效
        for result in [result1, result2, result3]:
            assert 0 <= result["position_limit"] <= 1
            assert result["risk_level"] in ["low", "medium", "high"]
            assert len(result["target_sectors"]) > 0
    
    @pytest.mark.asyncio
    async def test_strategy_generation_cost_tracking(self):
        """测试战略生成的成本追踪"""
        commander = Commander(
            api_key="sk-test-key",
            daily_budget=10.0,
            monthly_budget=300.0
        )
        
        # Mock LLM网关响应
        mock_llm_response = MagicMock()
        mock_llm_response.success = True
        mock_llm_response.content = json.dumps({
            "strategy_type": "balanced",
            "risk_level": "medium",
            "position_limit": 0.5,
            "target_sectors": ["科技"],
            "avoid_sectors": ["房地产"],
            "reasoning": "测试战略"
        })
        mock_llm_response.tokens_used = 500
        mock_llm_response.cost = 0.001
        mock_llm_response.error_message = None
        
        # Mock LLM网关
        mock_gateway = AsyncMock()
        mock_gateway.call_llm = AsyncMock(return_value=mock_llm_response)
        commander.llm_gateway = mock_gateway
        commander._initialized = True
        commander.redis_client = {"mode": "compatible"}
        
        market_state = {
            "market_sentiment": 0.5,
            "technical_indicators": {},
            "fundamental_data": {},
            "recent_reports": []
        }
        
        # 生成多个战略
        for i in range(5):
            result = await commander.generate_strategy(market_state)
            assert result["cost"] > 0
        
        # 验证成本累积
        status = commander.get_status()
        assert status["cost_tracker"]["call_count"] == 5
        assert status["cost_tracker"]["daily_cost"] > 0
        assert status["cost_tracker"]["daily_usage_ratio"] > 0
        
        # 验证成本在预算内
        assert status["cost_tracker"]["daily_cost"] < 10.0
        assert status["cost_tracker"]["monthly_cost"] < 300.0
