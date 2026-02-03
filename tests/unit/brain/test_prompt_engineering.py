"""
Prompt工程系统单元测试

白皮书依据: 第二章 2.1.3 决策流程
测试覆盖: Task 18.4 - Prompt工程的单元测试

测试内容:
- Prompt模板生成测试
- 上下文注入测试
- Few-shot示例测试
- 版本管理测试
"""

import pytest
from src.brain.prompt_engineering import (
    PromptTemplate,
    PromptManager,
    PromptVersion,
    DecisionType,
    MarketContext,
    PositionContext,
    RiskContext,
    FewShotExample
)


class TestPromptTemplate:
    """Prompt模板测试套件"""
    
    @pytest.fixture
    def template(self):
        """测试模板"""
        return PromptTemplate(PromptVersion.V2_0)
    
    @pytest.fixture
    def market_ctx(self):
        """测试市场上下文"""
        return MarketContext(
            market_regime="牛市",
            market_sentiment=0.7,
            volatility=0.15,
            symbol="000001",
            current_price=10.50,
            price_change_pct=0.03,
            volume_ratio=1.5,
            turnover_rate=0.05,
            ma5=10.20,
            ma20=9.80,
            rsi=65.0,
            macd=0.05,
            main_force_inflow=1000.0,
            main_force_probability=0.75
        )
    
    @pytest.fixture
    def position_ctx(self):
        """测试持仓上下文"""
        return PositionContext(
            symbol="000001",
            quantity=1000,
            cost_price=10.00,
            current_price=10.50,
            profit_loss_pct=0.05,
            position_ratio=0.10,
            available_cash=90000.0,
            total_assets=100000.0
        )
    
    @pytest.fixture
    def risk_ctx(self):
        """测试风险上下文"""
        return RiskContext(
            risk_level="低风险",
            max_position_ratio=0.95,
            max_single_stock_ratio=0.05,
            stop_loss_ratio=-0.03,
            portfolio_volatility=0.15,
            max_drawdown=-0.10,
            sharpe_ratio=1.5
        )
    
    def test_initialization(self, template):
        """测试初始化"""
        assert template.version == PromptVersion.V2_0
        assert len(template.few_shot_examples) == 5
        assert all(isinstance(ex, FewShotExample) for ex in template.few_shot_examples)
    
    def test_load_few_shot_examples(self, template):
        """测试Few-shot示例加载"""
        examples = template.few_shot_examples
        
        assert len(examples) == 5
        
        # 验证示例1: 牛市突破买入
        assert examples[0].scenario == "牛市突破买入"
        assert "BUY" in examples[0].decision
        assert "牛市" in examples[0].reasoning
        
        # 验证示例2: 止损卖出
        assert examples[1].scenario == "止损卖出"
        assert "SELL" in examples[1].decision
        assert "止损" in examples[1].reasoning
        
        # 验证示例3: 震荡市持有
        assert examples[2].scenario == "震荡市持有"
        assert "HOLD" in examples[2].decision
        
        # 验证示例4: 高位减仓
        assert examples[3].scenario == "高位减仓"
        assert "REDUCE" in examples[3].decision
        
        # 验证示例5: 熊市空仓
        assert examples[4].scenario == "熊市空仓"
        assert "HOLD" in examples[4].decision
        assert "熊市" in examples[4].reasoning
    
    def test_generate_system_prompt(self, template):
        """测试系统提示词生成"""
        system_prompt = template.generate_system_prompt()
        
        assert isinstance(system_prompt, str)
        assert len(system_prompt) > 0
        
        # 验证关键内容
        assert "MIA量化交易系统" in system_prompt
        assert "Soldier决策引擎" in system_prompt
        assert "风险控制优先" in system_prompt
        assert "顺势而为" in system_prompt
        assert "主力跟踪" in system_prompt
        assert "技术分析" in system_prompt
        assert "情绪感知" in system_prompt
        
        # 验证输出格式说明
        assert "decision" in system_prompt
        assert "confidence" in system_prompt
        assert "reasoning" in system_prompt
    
    def test_generate_few_shot_prompt(self, template):
        """测试Few-shot提示词生成"""
        few_shot_prompt = template.generate_few_shot_prompt()
        
        assert isinstance(few_shot_prompt, str)
        assert len(few_shot_prompt) > 0
        
        # 验证包含所有示例
        assert "示例1" in few_shot_prompt
        assert "示例2" in few_shot_prompt
        assert "示例3" in few_shot_prompt
        assert "示例4" in few_shot_prompt
        assert "示例5" in few_shot_prompt
        
        # 验证示例结构
        assert "市场上下文" in few_shot_prompt
        assert "持仓上下文" in few_shot_prompt
        assert "决策" in few_shot_prompt
        assert "推理" in few_shot_prompt
    
    def test_generate_user_prompt_with_market_only(self, template, market_ctx):
        """测试仅市场上下文的用户提示词生成"""
        user_prompt = template.generate_user_prompt(market_ctx)
        
        assert isinstance(user_prompt, str)
        assert len(user_prompt) > 0
        
        # 验证市场信息
        assert market_ctx.symbol in user_prompt
        assert str(market_ctx.current_price) in user_prompt
        assert market_ctx.market_regime in user_prompt
        
        # 验证技术指标
        assert "MA5" in user_prompt
        assert "MA20" in user_prompt
        assert "RSI" in user_prompt
        assert "MACD" in user_prompt
        
        # 验证主力资金
        assert "主力净流入" in user_prompt
        assert "主力概率" in user_prompt
        
        # 验证空仓提示
        assert "空仓" in user_prompt
    
    def test_generate_user_prompt_with_position(self, template, market_ctx, position_ctx):
        """测试包含持仓上下文的用户提示词生成"""
        user_prompt = template.generate_user_prompt(market_ctx, position_ctx)
        
        assert isinstance(user_prompt, str)
        
        # 验证持仓信息
        assert str(position_ctx.quantity) in user_prompt
        assert str(position_ctx.cost_price) in user_prompt
        assert "盈亏" in user_prompt
        assert "仓位占比" in user_prompt
        assert "可用资金" in user_prompt
        
        # 不应该有空仓提示
        assert "空仓" not in user_prompt
    
    def test_generate_user_prompt_with_risk(self, template, market_ctx, risk_ctx):
        """测试包含风险上下文的用户提示词生成"""
        user_prompt = template.generate_user_prompt(market_ctx, None, risk_ctx)
        
        assert isinstance(user_prompt, str)
        
        # 验证风险信息
        assert risk_ctx.risk_level in user_prompt
        assert "最大仓位" in user_prompt
        assert "单股限制" in user_prompt
        assert "止损线" in user_prompt
        assert "夏普比率" in user_prompt
    
    def test_generate_user_prompt_complete(self, template, market_ctx, position_ctx, risk_ctx):
        """测试完整的用户提示词生成"""
        user_prompt = template.generate_user_prompt(market_ctx, position_ctx, risk_ctx)
        
        assert isinstance(user_prompt, str)
        assert len(user_prompt) > 400  # 完整提示词应该较长
        
        # 验证所有部分都存在
        assert market_ctx.symbol in user_prompt
        assert str(position_ctx.quantity) in user_prompt
        assert risk_ctx.risk_level in user_prompt
        assert "请根据以上信息，做出交易决策并说明理由" in user_prompt
    
    def test_generate_complete_prompt_without_few_shot(self, template, market_ctx):
        """测试不包含Few-shot的完整Prompt生成"""
        prompt = template.generate_complete_prompt(market_ctx, include_few_shot=False)
        
        assert isinstance(prompt, dict)
        assert 'system' in prompt
        assert 'user' in prompt
        assert 'version' in prompt
        assert 'timestamp' in prompt
        
        # 验证版本
        assert prompt['version'] == PromptVersion.V2_0.value
        
        # 验证不包含Few-shot示例
        assert "示例1" not in prompt['system']
        assert "示例2" not in prompt['system']
    
    def test_generate_complete_prompt_with_few_shot(self, template, market_ctx, position_ctx, risk_ctx):
        """测试包含Few-shot的完整Prompt生成"""
        prompt = template.generate_complete_prompt(
            market_ctx, position_ctx, risk_ctx, include_few_shot=True
        )
        
        assert isinstance(prompt, dict)
        assert 'system' in prompt
        assert 'user' in prompt
        
        # 验证包含Few-shot示例
        assert "示例1" in prompt['system']
        assert "示例2" in prompt['system']
        assert "示例3" in prompt['system']
        assert "示例4" in prompt['system']
        assert "示例5" in prompt['system']
        
        # 验证系统提示词
        assert "MIA量化交易系统" in prompt['system']
        
        # 验证用户提示词
        assert market_ctx.symbol in prompt['user']


class TestPromptManager:
    """Prompt管理器测试套件"""
    
    @pytest.fixture
    def manager(self):
        """测试管理器"""
        return PromptManager()
    
    @pytest.fixture
    def market_ctx(self):
        """测试市场上下文"""
        return MarketContext(
            market_regime="震荡",
            market_sentiment=0.2,
            volatility=0.20,
            symbol="600000",
            current_price=15.00,
            price_change_pct=0.01,
            volume_ratio=1.2,
            turnover_rate=0.03,
            ma5=14.80,
            ma20=14.50,
            rsi=55.0,
            macd=0.02,
            main_force_inflow=500.0,
            main_force_probability=0.60
        )
    
    def test_initialization(self, manager):
        """测试初始化"""
        assert manager.current_version == PromptVersion.V2_0
        assert len(manager.templates) == 1  # 预加载当前版本
        assert PromptVersion.V2_0 in manager.templates
        assert manager.stats['total_prompts_generated'] == 0
    
    def test_load_template(self, manager):
        """测试模板加载"""
        # 加载新版本
        template = manager._load_template(PromptVersion.V1_0)
        
        assert isinstance(template, PromptTemplate)
        assert template.version == PromptVersion.V1_0
        assert PromptVersion.V1_0 in manager.templates
        
        # 重复加载应该返回缓存的模板
        template2 = manager._load_template(PromptVersion.V1_0)
        assert template is template2
    
    def test_generate_prompt_default_version(self, manager, market_ctx):
        """测试使用默认版本生成Prompt"""
        prompt = manager.generate_prompt(market_ctx)
        
        assert isinstance(prompt, dict)
        assert prompt['version'] == PromptVersion.V2_0.value
        assert manager.stats['total_prompts_generated'] == 1
    
    def test_generate_prompt_specific_version(self, manager, market_ctx):
        """测试使用指定版本生成Prompt"""
        prompt = manager.generate_prompt(market_ctx, version=PromptVersion.V1_0)
        
        assert isinstance(prompt, dict)
        assert prompt['version'] == PromptVersion.V1_0.value
        assert PromptVersion.V1_0 in manager.templates
    
    def test_generate_prompt_with_all_contexts(self, manager, market_ctx):
        """测试使用所有上下文生成Prompt"""
        position_ctx = PositionContext(
            symbol="600000",
            quantity=500,
            cost_price=14.50,
            current_price=15.00,
            profit_loss_pct=0.034,
            position_ratio=0.075,
            available_cash=92500.0,
            total_assets=100000.0
        )
        
        risk_ctx = RiskContext(
            risk_level="中风险",
            max_position_ratio=0.80,
            max_single_stock_ratio=0.03,
            stop_loss_ratio=-0.05,
            portfolio_volatility=0.18,
            max_drawdown=-0.12,
            sharpe_ratio=1.2
        )
        
        prompt = manager.generate_prompt(market_ctx, position_ctx, risk_ctx)
        
        assert isinstance(prompt, dict)
        assert market_ctx.symbol in prompt['user']
        assert str(position_ctx.quantity) in prompt['user']
        assert risk_ctx.risk_level in prompt['user']
    
    def test_update_stats(self, manager, market_ctx):
        """测试统计信息更新"""
        # 生成多个Prompt
        for _ in range(5):
            manager.generate_prompt(market_ctx)
        
        stats = manager.get_stats()
        
        assert stats['total_prompts_generated'] == 5
        assert PromptVersion.V2_0.value in stats['prompts_by_version']
        assert stats['prompts_by_version'][PromptVersion.V2_0.value] == 5
        assert stats['avg_prompt_length'] > 0
    
    def test_get_stats(self, manager):
        """测试获取统计信息"""
        stats = manager.get_stats()
        
        assert isinstance(stats, dict)
        assert 'total_prompts_generated' in stats
        assert 'prompts_by_version' in stats
        assert 'avg_prompt_length' in stats
        assert 'current_version' in stats
        assert 'loaded_versions' in stats
        
        assert stats['current_version'] == PromptVersion.V2_0.value
        assert PromptVersion.V2_0.value in stats['loaded_versions']
    
    def test_set_version(self, manager):
        """测试设置版本"""
        # 切换到V1.0
        manager.set_version(PromptVersion.V1_0)
        
        assert manager.current_version == PromptVersion.V1_0
        assert PromptVersion.V1_0 in manager.templates
        
        # 切换回V2.0
        manager.set_version(PromptVersion.V2_0)
        
        assert manager.current_version == PromptVersion.V2_0
    
    def test_version_statistics(self, manager, market_ctx):
        """测试版本统计"""
        # 使用不同版本生成Prompt
        manager.generate_prompt(market_ctx, version=PromptVersion.V1_0)
        manager.generate_prompt(market_ctx, version=PromptVersion.V1_0)
        manager.generate_prompt(market_ctx, version=PromptVersion.V2_0)
        
        stats = manager.get_stats()
        
        assert stats['total_prompts_generated'] == 3
        assert stats['prompts_by_version'][PromptVersion.V1_0.value] == 2
        assert stats['prompts_by_version'][PromptVersion.V2_0.value] == 1


class TestMarketContext:
    """市场上下文测试"""
    
    def test_market_context_creation(self):
        """测试市场上下文创建"""
        ctx = MarketContext(
            market_regime="牛市",
            market_sentiment=0.8,
            volatility=0.12,
            symbol="000001",
            current_price=20.00,
            price_change_pct=0.05,
            volume_ratio=2.0,
            turnover_rate=0.08,
            ma5=19.50,
            ma20=18.00,
            rsi=70.0,
            macd=0.10,
            main_force_inflow=2000.0,
            main_force_probability=0.85
        )
        
        assert ctx.market_regime == "牛市"
        assert ctx.market_sentiment == 0.8
        assert ctx.symbol == "000001"
        assert ctx.current_price == 20.00


class TestPositionContext:
    """持仓上下文测试"""
    
    def test_position_context_creation(self):
        """测试持仓上下文创建"""
        ctx = PositionContext(
            symbol="000001",
            quantity=2000,
            cost_price=18.00,
            current_price=20.00,
            profit_loss_pct=0.111,
            position_ratio=0.20,
            available_cash=80000.0,
            total_assets=100000.0
        )
        
        assert ctx.symbol == "000001"
        assert ctx.quantity == 2000
        assert ctx.cost_price == 18.00
        assert ctx.profit_loss_pct == 0.111


class TestRiskContext:
    """风险上下文测试"""
    
    def test_risk_context_creation(self):
        """测试风险上下文创建"""
        ctx = RiskContext(
            risk_level="高风险",
            max_position_ratio=0.60,
            max_single_stock_ratio=0.02,
            stop_loss_ratio=-0.08,
            portfolio_volatility=0.25,
            max_drawdown=-0.15,
            sharpe_ratio=0.8
        )
        
        assert ctx.risk_level == "高风险"
        assert ctx.max_position_ratio == 0.60
        assert ctx.stop_loss_ratio == -0.08


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
