"""Commander研报分析功能测试

白皮书依据: 第二章 2.2 Commander (慢系统)
验证需求: 需求4.1, 需求4.2, 需求4.3, 需求4.4
"""

import json
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from src.brain.commander.core import (
    BudgetExceededError,
    Commander
)


class TestReportAnalysis:
    """测试研报分析功能
    
    白皮书依据: 第二章 2.2 Commander (慢系统)
    验证需求: 需求4.1, 需求4.2, 需求4.3
    """
    
    @pytest.mark.asyncio
    async def test_analyze_report_success_compatible_mode(self):
        """测试研报分析成功（兼容模式）"""
        commander = Commander(api_key="sk-test-key")
        
        # 设置兼容模式
        commander.api_client = {"mode": "compatible"}
        
        report_text = """
        【公司研究】某科技公司2026年度投资价值分析
        
        一、公司概况
        某科技公司是国内领先的人工智能企业，主营业务包括...
        
        二、财务分析
        2025年营收100亿元，同比增长30%...
        
        三、投资建议
        我们给予公司"买入"评级，目标价120元...
        """
        
        # Mock LLM网关调用
        mock_result = {
            "industry": "人工智能",
            "company": "某科技公司",
            "rating": "买入",
            "target_price": 120.0,
            "key_points": ["营收增长30%", "行业领先"],
            "risks": ["市场竞争加剧"],
            "summary": "公司基本面良好，建议买入",
            "tokens_used": 500
        }
        
        with patch.object(commander, '_call_llm_gateway_for_analysis', new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = mock_result
            result = await commander.analyze_report(report_text)
        
        # 验证返回结果结构
        assert "industry" in result
        assert "company" in result
        assert "rating" in result
        assert "target_price" in result
        assert "key_points" in result
        assert "risks" in result
        assert "summary" in result
        assert "tokens_used" in result
        assert "cost" in result
        
        # 验证数据类型
        assert isinstance(result["industry"], str)
        assert isinstance(result["company"], str)
        assert isinstance(result["rating"], str)
        assert isinstance(result["key_points"], list)
        assert isinstance(result["risks"], list)
        assert isinstance(result["summary"], str)
        assert isinstance(result["tokens_used"], int)
        assert isinstance(result["cost"], float)
        
        # 验证成本已记录
        assert commander.cost_tracker.daily_cost > 0
        assert commander.cost_tracker.call_count == 1
    
    @pytest.mark.asyncio
    async def test_analyze_report_empty_text(self):
        """测试空研报文本"""
        commander = Commander(api_key="sk-test-key")
        
        with pytest.raises(ValueError, match="研报文本不能为空"):
            await commander.analyze_report("")
        
        with pytest.raises(ValueError, match="研报文本不能为空"):
            await commander.analyze_report("   ")
    
    @pytest.mark.asyncio
    async def test_analyze_report_budget_exceeded(self):
        """测试预算超限"""
        commander = Commander(
            api_key="sk-test-key",
            daily_budget=0.001,  # 极小的预算
            monthly_budget=0.01
        )
        
        report_text = "这是一个很长的研报..." * 1000
        
        with pytest.raises(BudgetExceededError, match="预算不足"):
            await commander.analyze_report(report_text)
    
    @pytest.mark.asyncio
    async def test_analyze_report_with_real_api(self):
        """测试研报分析（通过Mock LLM网关）"""
        # Mock LLM网关响应
        mock_llm_response = MagicMock()
        mock_llm_response.success = True
        mock_llm_response.content = json.dumps({
            "industry": "科技",
            "company": "某科技公司",
            "rating": "买入",
            "target_price": 120.0,
            "key_points": [
                "营收增长强劲",
                "技术创新领先",
                "市场份额扩大"
            ],
            "risks": [
                "市场竞争加剧",
                "政策风险"
            ],
            "summary": "公司基本面良好，建议买入"
        })
        mock_llm_response.tokens_used = 500
        mock_llm_response.cost = 0.002
        mock_llm_response.error_message = None
        
        # Mock Redis
        mock_redis = MagicMock()
        mock_redis_client = AsyncMock()
        mock_redis_client.ping = AsyncMock()
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
            
            report_text = "某科技公司研究报告..."
            result = await commander.analyze_report(report_text)
            
            # 验证结果
            assert result["industry"] == "科技"
            assert result["company"] == "某科技公司"
            assert result["rating"] == "买入"
            assert result["target_price"] == 120.0
            assert len(result["key_points"]) == 3
            assert len(result["risks"]) == 2
            assert result["tokens_used"] == 500
            
            # 验证LLM网关被调用
            mock_gateway.call_llm.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_analyze_report_api_failure(self):
        """测试API调用失败"""
        commander = Commander(api_key="sk-test-key")
        
        # 直接设置API客户端为真实模式，但会失败
        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(
            side_effect=Exception("API调用失败")
        )
        commander.api_client = mock_client
        
        report_text = "测试研报"
        
        with pytest.raises(RuntimeError, match="研报分析失败"):
            await commander.analyze_report(report_text)
    
    @pytest.mark.asyncio
    async def test_analyze_report_invalid_json_response(self):
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
        
        report_text = "测试研报"
        
        # 当JSON解析失败时，会返回默认结构而不是抛出异常
        result = await commander.analyze_report(report_text)
        assert result["industry"] == "未识别"
        assert result["company"] == "未识别"
    
    @pytest.mark.asyncio
    async def test_analyze_report_empty_api_response(self):
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
        
        report_text = "测试研报"
        
        # 当返回空内容时，会返回默认结构
        result = await commander.analyze_report(report_text)
        assert result["industry"] == "未识别"
        assert result["company"] == "未识别"
    
    @pytest.mark.asyncio
    async def test_analyze_multiple_reports(self):
        """测试分析多个研报"""
        commander = Commander(api_key="sk-test-key")
        
        # Mock LLM网关响应
        mock_llm_response = MagicMock()
        mock_llm_response.success = True
        mock_llm_response.content = json.dumps({
            "industry": "科技",
            "company": "测试公司",
            "rating": "买入",
            "target_price": 100.0,
            "key_points": ["增长强劲"],
            "risks": ["市场风险"],
            "summary": "建议买入"
        })
        mock_llm_response.tokens_used = 200
        mock_llm_response.cost = 0.001
        mock_llm_response.error_message = None
        
        # Mock LLM网关
        mock_gateway = AsyncMock()
        mock_gateway.call_llm = AsyncMock(return_value=mock_llm_response)
        commander.llm_gateway = mock_gateway
        commander._initialized = True
        
        reports = [
            "研报1内容...",
            "研报2内容...",
            "研报3内容..."
        ]
        
        for i, report in enumerate(reports, 1):
            result = await commander.analyze_report(report)
            
            # 验证每次分析都成功
            assert "industry" in result
            assert "cost" in result
            
            # 验证成本累积
            assert commander.cost_tracker.call_count == i
            assert commander.cost_tracker.daily_cost > 0
    
    def test_calculate_cost(self):
        """测试成本计算"""
        commander = Commander(api_key="sk-test-key")
        
        # 测试不同token数量的成本计算
        assert commander._calculate_cost(1_000_000) == 1.0
        assert commander._calculate_cost(500_000) == 0.5
        assert commander._calculate_cost(100_000) == 0.1
        assert commander._calculate_cost(10_000) == 0.01
        assert commander._calculate_cost(1_000) == 0.001
    
    def test_build_analysis_prompt(self):
        """测试构建分析提示词"""
        commander = Commander(api_key="sk-test-key")
        
        report_text = "这是一个测试研报" * 100
        prompt = commander._build_analysis_prompt(report_text)
        
        # 验证提示词包含必要内容
        assert "请分析以下研究报告" in prompt
        assert "JSON格式" in prompt
        assert "industry" in prompt
        assert "company" in prompt
        assert "rating" in prompt
        assert "key_points" in prompt
        assert "risks" in prompt
        assert "summary" in prompt
        
        # 验证提示词长度限制
        assert len(prompt) < 10000  # 避免超过token限制


class TestReportAnalysisIntegration:
    """测试研报分析集成场景"""
    
    @pytest.mark.asyncio
    async def test_full_analysis_workflow(self):
        """测试完整的分析工作流"""
        # Mock LLM网关响应
        mock_llm_response = MagicMock()
        mock_llm_response.success = True
        mock_llm_response.content = json.dumps({
            "industry": "金融",
            "company": "某银行",
            "rating": "持有",
            "target_price": 50.0,
            "key_points": ["资产质量稳定", "盈利能力良好"],
            "risks": ["利率风险", "信用风险"],
            "summary": "银行基本面稳健"
        })
        mock_llm_response.tokens_used = 300
        mock_llm_response.cost = 0.002
        mock_llm_response.error_message = None
        
        # Mock Redis
        mock_redis = MagicMock()
        mock_redis_client = AsyncMock()
        mock_redis_client.ping = AsyncMock()
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
            
            # 3. 分析研报
            report_text = "某银行2026年度投资价值分析..."
            result = await commander.analyze_report(report_text)
            
            # 4. 验证结果
            assert result["industry"] == "金融"
            assert result["company"] == "某银行"
            assert result["rating"] == "持有"
            assert result["cost"] > 0
            
            # 5. 验证成本追踪
            status = commander.get_status()
            assert status["cost_tracker"]["daily_cost"] > 0
            assert status["cost_tracker"]["call_count"] == 1
            
            # 6. 关闭
            await commander.close()
