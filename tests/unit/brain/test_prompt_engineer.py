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
from datetime import datetime

from src.brain.prompt_engineer import (
    PromptEngineer,
    PromptVersion,
    MarketContext,
    PositionContext,
    RiskContext,
    FewShotExample
)


class TestPromptEngineer:
    """Prompt工程师测试套件"""
    
    @pytest.fixture
    def engineer(self):
        """Prompt工程师实例"""
        return PromptEngineer()
    
    @pytest.fixture
    def market_context(self):
        """市场上下文数据"""
        return MarketContext(
            symbol="600519",
            current_price=1850.00,
            price_change_pct=3.5,
            volume=5200000,
            volume_ratio=2.3,
            turnover_rate=1.8,
            market_regime="牛市",
            sector="白酒",
            timestamp=datetime(2026, 1, 19, 14, 30, 0)
        )
    
    @pytest.fixture
    def position_context(self):
        """持仓上下文数据"""
        return PositionContext(
            symbol="600519",
            quantity=1000,
            avg_cost=1750.00,
            current_price=1850.00,
            unrealized_pnl=100000.00,
            unrealized_pnl_pct=5.71,
            holding_days=15
        )
    
    @pytest.fixture
    def risk_context(self):
        """风险控制上下文"""
        return RiskContext(
            total_position_pct=75.0,
            max_position_limit=95.0,
            single_stock_limit=5.0,
            sector_limit=30.0,
            stop_loss_line=-3.0,
            risk_level="中"
        )
    
    def test_initialization(self, engineer):
        """测试初始化"""
        assert engineer.version == PromptVersion.V1_2
        assert len(engineer.few_shot_examples) > 0
    
    def test_initialization_with_custom_version(self):
        """测试使用自定义版本初始化"""
        engineer = PromptEngineer(version=PromptVersion.V1_0)
        assert engineer.version == PromptVersion.V1_0
    
    def test_generate_decision_prompt_basic(self, engineer, market_context):
        """测试基础Prompt生成"""
        prompt = engineer.generate_decision_prompt(
            market_context=market_context,
            include_few_shot=False
        )
        
        assert prompt is not None
        assert len(prompt) > 0
        
        # 验证包含关键信息
        assert "600519" in prompt
        assert "1850.00" in prompt
        assert "+3.50%" in prompt  # 修复：使用格式化后的百分比
        assert "牛市" in prompt
        assert "白酒" in prompt
    
    def test_generate_decision_prompt_with_position(
        self, engineer, market_context, position_context
    ):
        """测试包含持仓信息的Prompt生成"""
        prompt = engineer.generate_decision_prompt(
            market_context=market_context,
            position_context=position_context,
            include_few_shot=False
        )
        
        assert "当前持仓信息" in prompt
        assert "1000股" in prompt
        assert "1750.00" in prompt
        assert "100,000.00" in prompt  # 修复：使用千位分隔符格式
        assert "5.71%" in prompt
        assert "15天" in prompt
    
    def test_generate_decision_prompt_with_risk(
        self, engineer, market_context, risk_context
    ):
        """测试包含风险控制信息的Prompt生成"""
        prompt = engineer.generate_decision_prompt(
            market_context=market_context,
            risk_context=risk_context,
            include_few_shot=False
        )
        
        assert "风险控制参数" in prompt
        assert "75.0%" in prompt
        assert "95.0%" in prompt
        assert "5.0%" in prompt
        assert "30.0%" in prompt
        assert "-3.0%" in prompt
        assert "中" in prompt
    
    def test_generate_decision_prompt_full(
        self, engineer, market_context, position_context, risk_context
    ):
        """测试完整Prompt生成（包含所有上下文）"""
        prompt = engineer.generate_decision_prompt(
            market_context=market_context,
            position_context=position_context,
            risk_context=risk_context,
            include_few_shot=True
        )
        
        # 验证所有部分都存在
        assert "角色定义" in prompt
        assert "决策示例" in prompt
        assert "当前市场信息" in prompt
        assert "当前持仓信息" in prompt
        assert "风险控制参数" in prompt
        assert "决策任务" in prompt
        
        # 验证输出格式要求
        assert "action" in prompt
        assert "confidence" in prompt
        assert "reasoning" in prompt
    
    def test_generate_decision_prompt_without_few_shot(
        self, engineer, market_context
    ):
        """测试不包含Few-shot示例的Prompt生成"""
        prompt = engineer.generate_decision_prompt(
            market_context=market_context,
            include_few_shot=False
        )
        
        assert "决策示例" not in prompt
        assert "示例 1" not in prompt
    
    def test_build_system_prompt(self, engineer):
        """测试系统提示词构建"""
        system_prompt = engineer._build_system_prompt()
        
        assert "角色定义" in system_prompt
        assert "Soldier Engine" in system_prompt
        assert "核心原则" in system_prompt
        assert "决策框架" in system_prompt
        assert "买入信号" in system_prompt
        assert "卖出信号" in system_prompt
        assert "持有信号" in system_prompt
    
    def test_build_market_info(self, engineer, market_context):
        """测试市场信息构建"""
        market_info = engineer._build_market_info(market_context)
        
        assert "600519" in market_info
        assert "1850.00" in market_info
        assert "+3.50%" in market_info
        assert "5,200,000" in market_info
        assert "2.30" in market_info
        assert "1.80%" in market_info
        assert "牛市" in market_info
        assert "白酒" in market_info
        assert "2026-01-19 14:30:00" in market_info
    
    def test_build_position_info(self, engineer, position_context):
        """测试持仓信息构建"""
        position_info = engineer._build_position_info(position_context)
        
        assert "1000股" in position_info
        assert "1750.00" in position_info
        assert "1850.00" in position_info
        assert "100,000.00" in position_info
        assert "+5.71%" in position_info
        assert "15天" in position_info
    
    def test_build_risk_info(self, engineer, risk_context):
        """测试风险控制信息构建"""
        risk_info = engineer._build_risk_info(risk_context)
        
        assert "75.0%" in risk_info
        assert "95.0%" in risk_info
        assert "5.0%" in risk_info
        assert "30.0%" in risk_info
        assert "-3.0%" in risk_info
        assert "中" in risk_info
    
    def test_build_few_shot_examples(self, engineer):
        """测试Few-shot示例构建"""
        few_shot = engineer._build_few_shot_examples()
        
        assert "决策示例" in few_shot
        assert "示例 1" in few_shot
        assert "突破买入" in few_shot or "止损卖出" in few_shot
        assert "市场情况" in few_shot
        assert "决策" in few_shot
        assert "推理过程" in few_shot
    
    def test_build_few_shot_examples_empty(self):
        """测试空Few-shot示例构建"""
        # 创建一个没有few-shot示例的工程师实例
        engineer = PromptEngineer()
        # 清空few_shot_examples来测试空情况
        engineer.few_shot_examples = []
        
        few_shot = engineer._build_few_shot_examples()
        
        # 当没有示例时，应该返回空字符串
        assert few_shot == ""
    
    def test_build_task_instruction(self, engineer):
        """测试任务指令构建"""
        task_instruction = engineer._build_task_instruction()
        
        assert "交易决策" in task_instruction
        assert "输出格式" in task_instruction
        assert "action" in task_instruction
        assert "confidence" in task_instruction
        assert "reasoning" in task_instruction
        assert "注意事项" in task_instruction
    
    def test_load_few_shot_examples(self, engineer):
        """测试Few-shot示例加载"""
        examples = engineer._load_few_shot_examples()
        
        assert len(examples) >= 3  # 至少3个示例
        assert len(examples) <= 5  # 最多5个示例
        
        # 验证示例结构
        for example in examples:
            assert isinstance(example, FewShotExample)
            assert example.scenario
            assert example.market_context
            assert example.decision in ["buy", "sell", "hold"]
            assert example.reasoning
    
    def test_few_shot_examples_content(self, engineer):
        """测试Few-shot示例内容"""
        examples = engineer.few_shot_examples
        
        # 验证包含不同类型的决策示例
        decisions = [ex.decision for ex in examples]
        assert "buy" in decisions
        assert "sell" in decisions
        assert "hold" in decisions
        
        # 验证示例场景多样性
        scenarios = [ex.scenario for ex in examples]
        assert len(set(scenarios)) == len(scenarios)  # 所有场景都不同
    
    def test_get_version(self, engineer):
        """测试获取版本"""
        version = engineer.get_version()
        assert version == "v1.2"
    
    def test_update_version(self, engineer):
        """测试更新版本"""
        # 初始版本
        assert engineer.version == PromptVersion.V1_2
        
        # 更新版本
        engineer.update_version(PromptVersion.V1_0)
        assert engineer.version == PromptVersion.V1_0
        assert engineer.get_version() == "v1.0"
        
        # 再次更新
        engineer.update_version(PromptVersion.V1_1)
        assert engineer.version == PromptVersion.V1_1
        assert engineer.get_version() == "v1.1"
    
    def test_prompt_length_reasonable(self, engineer, market_context):
        """测试Prompt长度合理性"""
        # 不包含Few-shot的Prompt
        prompt_without_few_shot = engineer.generate_decision_prompt(
            market_context=market_context,
            include_few_shot=False
        )
        assert 500 < len(prompt_without_few_shot) < 2000
        
        # 包含Few-shot的Prompt
        prompt_with_few_shot = engineer.generate_decision_prompt(
            market_context=market_context,
            include_few_shot=True
        )
        assert 1500 < len(prompt_with_few_shot) < 10000  # 修复：调整下限为1500
    
    def test_prompt_structure_consistency(self, engineer, market_context):
        """测试Prompt结构一致性"""
        # 生成多个Prompt
        prompt1 = engineer.generate_decision_prompt(market_context, include_few_shot=False)
        prompt2 = engineer.generate_decision_prompt(market_context, include_few_shot=False)
        
        # 验证结构一致（除了时间戳）
        assert prompt1.count("##") == prompt2.count("##")
        assert prompt1.count("**") == prompt2.count("**")


class TestMarketContext:
    """市场上下文测试"""
    
    def test_market_context_creation(self):
        """测试市场上下文创建"""
        context = MarketContext(
            symbol="600519",
            current_price=1850.00,
            price_change_pct=3.5,
            volume=5200000,
            volume_ratio=2.3,
            turnover_rate=1.8,
            market_regime="牛市",
            sector="白酒",
            timestamp=datetime(2026, 1, 19, 14, 30, 0)
        )
        
        assert context.symbol == "600519"
        assert context.current_price == 1850.00
        assert context.price_change_pct == 3.5
        assert context.volume == 5200000
        assert context.volume_ratio == 2.3
        assert context.turnover_rate == 1.8
        assert context.market_regime == "牛市"
        assert context.sector == "白酒"
        assert context.timestamp.year == 2026


class TestPositionContext:
    """持仓上下文测试"""
    
    def test_position_context_creation(self):
        """测试持仓上下文创建"""
        context = PositionContext(
            symbol="600519",
            quantity=1000,
            avg_cost=1750.00,
            current_price=1850.00,
            unrealized_pnl=100000.00,
            unrealized_pnl_pct=5.71,
            holding_days=15
        )
        
        assert context.symbol == "600519"
        assert context.quantity == 1000
        assert context.avg_cost == 1750.00
        assert context.current_price == 1850.00
        assert context.unrealized_pnl == 100000.00
        assert context.unrealized_pnl_pct == 5.71
        assert context.holding_days == 15


class TestRiskContext:
    """风险控制上下文测试"""
    
    def test_risk_context_creation(self):
        """测试风险控制上下文创建"""
        context = RiskContext(
            total_position_pct=75.0,
            max_position_limit=95.0,
            single_stock_limit=5.0,
            sector_limit=30.0,
            stop_loss_line=-3.0,
            risk_level="中"
        )
        
        assert context.total_position_pct == 75.0
        assert context.max_position_limit == 95.0
        assert context.single_stock_limit == 5.0
        assert context.sector_limit == 30.0
        assert context.stop_loss_line == -3.0
        assert context.risk_level == "中"


class TestFewShotExample:
    """Few-shot示例测试"""
    
    def test_few_shot_example_creation(self):
        """测试Few-shot示例创建"""
        example = FewShotExample(
            scenario="突破买入",
            market_context="股票代码: 600519\n当前价格: ¥1850.00",
            decision="buy",
            reasoning="价格突破前期高点，成交量放大"
        )
        
        assert example.scenario == "突破买入"
        assert "600519" in example.market_context
        assert example.decision == "buy"
        assert "突破" in example.reasoning


class TestPromptVersion:
    """Prompt版本测试"""
    
    def test_prompt_version_enum(self):
        """测试Prompt版本枚举"""
        assert PromptVersion.V1_0.value == "v1.0"
        assert PromptVersion.V1_1.value == "v1.1"
        assert PromptVersion.V1_2.value == "v1.2"
    
    def test_prompt_version_comparison(self):
        """测试Prompt版本比较"""
        assert PromptVersion.V1_0 != PromptVersion.V1_1
        assert PromptVersion.V1_1 != PromptVersion.V1_2
        assert PromptVersion.V1_0 == PromptVersion.V1_0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
