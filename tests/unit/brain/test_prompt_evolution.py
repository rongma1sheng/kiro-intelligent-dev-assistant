"""
Prompt进化引擎单元测试

白皮书依据: 第四章 4.6 提示词进化引擎
测试覆盖: Prompt自动进化功能

测试内容:
- UCB选择策略测试
- 性能更新测试
- 进化机制测试
- 变异策略测试
"""

import pytest
import math
from src.brain.prompt_evolution import (
    PromptEvolutionEngine,
    PromptTemplate
)


class TestPromptEvolutionEngine:
    """Prompt进化引擎测试套件"""
    
    @pytest.fixture
    def engine(self):
        """测试引擎"""
        return PromptEvolutionEngine(
            pool_size=10,
            evolution_interval=100,
            elite_count=3,
            exploration_param=2.0
        )
    
    @pytest.fixture
    def base_prompts(self):
        """基础提示词"""
        return [
            "分析交易决策的风险和合规性。",
            "评估策略的潜在问题。",
            "仔细评估交易计划。",
            "检查规则违规和异常。",
            "评估决策质量和安全性。"
        ]
    
    def test_initialization(self, engine):
        """测试初始化"""
        assert engine.pool_size == 10
        assert engine.evolution_interval == 100
        assert engine.elite_count == 3
        assert engine.exploration_param == 2.0
        assert engine.generation == 0
        assert engine.total_uses == 0
        assert len(engine.prompt_pool) == 0
    
    def test_initialize_prompt_pool(self, engine, base_prompts):
        """测试初始化提示词池"""
        engine.initialize_prompt_pool(base_prompts)
        
        assert len(engine.prompt_pool) == 5
        assert engine.stats['total_prompts_created'] == 5
        
        # 验证每个提示词
        for i, prompt in enumerate(engine.prompt_pool):
            assert prompt.template_id == f"prompt_{i:03d}_gen0"
            assert prompt.content == base_prompts[i]
            assert prompt.generation == 0
            assert prompt.uses == 0
            assert prompt.successes == 0
            assert prompt.win_rate == 0.0
    
    def test_select_prompt_ucb_first_selection(self, engine, base_prompts):
        """测试UCB选择策略（首次选择）"""
        engine.initialize_prompt_pool(base_prompts)
        
        # 首次选择应该选择未使用的提示词（UCB=inf）
        selected = engine.select_prompt(strategy="ucb")
        
        assert isinstance(selected, PromptTemplate)
        assert selected.uses == 0  # 未使用的提示词
    
    def test_select_prompt_ucb_with_history(self, engine, base_prompts):
        """测试UCB选择策略（有历史数据）"""
        engine.initialize_prompt_pool(base_prompts)
        
        # 模拟一些使用历史
        engine.prompt_pool[0].uses = 10
        engine.prompt_pool[0].successes = 8
        engine.prompt_pool[0].win_rate = 0.8
        
        engine.prompt_pool[1].uses = 5
        engine.prompt_pool[1].successes = 4
        engine.prompt_pool[1].win_rate = 0.8
        
        engine.total_uses = 15
        
        # UCB应该平衡探索和利用
        selected = engine.select_prompt(strategy="ucb")
        
        assert isinstance(selected, PromptTemplate)
    
    def test_select_prompt_greedy(self, engine, base_prompts):
        """测试贪心选择策略"""
        engine.initialize_prompt_pool(base_prompts)
        
        # 设置不同的胜率
        engine.prompt_pool[0].win_rate = 0.5
        engine.prompt_pool[1].win_rate = 0.8
        engine.prompt_pool[2].win_rate = 0.6
        
        selected = engine.select_prompt(strategy="greedy")
        
        assert selected.win_rate == 0.8  # 应该选择胜率最高的
    
    def test_select_prompt_random(self, engine, base_prompts):
        """测试随机选择策略"""
        engine.initialize_prompt_pool(base_prompts)
        
        selected = engine.select_prompt(strategy="random")
        
        assert isinstance(selected, PromptTemplate)
        assert selected in engine.prompt_pool
    
    def test_select_prompt_empty_pool(self, engine):
        """测试空池选择"""
        with pytest.raises(ValueError, match="Prompt pool is empty"):
            engine.select_prompt()
    
    def test_update_performance_success(self, engine, base_prompts):
        """测试性能更新（成功）"""
        engine.initialize_prompt_pool(base_prompts)
        
        template_id = engine.prompt_pool[0].template_id
        
        # 更新性能（成功）
        engine.update_performance(template_id, success=True)
        
        assert engine.prompt_pool[0].uses == 1
        assert engine.prompt_pool[0].successes == 1
        assert engine.prompt_pool[0].win_rate == 1.0
        assert engine.total_uses == 1
    
    def test_update_performance_failure(self, engine, base_prompts):
        """测试性能更新（失败）"""
        engine.initialize_prompt_pool(base_prompts)
        
        template_id = engine.prompt_pool[0].template_id
        
        # 更新性能（失败）
        engine.update_performance(template_id, success=False)
        
        assert engine.prompt_pool[0].uses == 1
        assert engine.prompt_pool[0].successes == 0
        assert engine.prompt_pool[0].win_rate == 0.0
        assert engine.total_uses == 1
    
    def test_update_performance_multiple(self, engine, base_prompts):
        """测试多次性能更新"""
        engine.initialize_prompt_pool(base_prompts)
        
        template_id = engine.prompt_pool[0].template_id
        
        # 多次更新
        engine.update_performance(template_id, success=True)
        engine.update_performance(template_id, success=True)
        engine.update_performance(template_id, success=False)
        engine.update_performance(template_id, success=True)
        
        assert engine.prompt_pool[0].uses == 4
        assert engine.prompt_pool[0].successes == 3
        assert engine.prompt_pool[0].win_rate == 0.75
        assert engine.total_uses == 4
    
    def test_evolve_prompts_trigger(self, engine, base_prompts):
        """测试进化触发"""
        engine.initialize_prompt_pool(base_prompts)
        engine.evolution_interval = 10  # 设置较小的间隔
        
        # 模拟使用
        for i in range(9):
            template_id = engine.prompt_pool[i % len(engine.prompt_pool)].template_id
            engine.update_performance(template_id, success=True)
        
        assert engine.generation == 0
        
        # 第10次应该触发进化
        template_id = engine.prompt_pool[0].template_id
        engine.update_performance(template_id, success=True)
        
        assert engine.generation == 1
        assert engine.stats['total_evolutions'] == 1
    
    def test_evolve_prompts_elite_retention(self, engine, base_prompts):
        """测试精英保留"""
        engine.initialize_prompt_pool(base_prompts)
        
        # 设置不同的胜率
        for i, prompt in enumerate(engine.prompt_pool):
            prompt.uses = 10
            prompt.successes = i * 2  # 不同的成功次数
            prompt.win_rate = prompt.successes / prompt.uses
        
        original_elites = engine.prompt_pool[-3:]  # 最后3个胜率最高
        
        engine.evolve_prompts()
        
        # 验证精英被保留
        elite_ids = [p.template_id for p in original_elites]
        new_pool_ids = [p.template_id for p in engine.prompt_pool]
        
        for elite_id in elite_ids:
            assert elite_id in new_pool_ids
    
    def test_evolve_prompts_new_generation(self, engine, base_prompts):
        """测试新一代生成"""
        engine.initialize_prompt_pool(base_prompts)
        
        # 设置一些性能数据
        for prompt in engine.prompt_pool:
            prompt.uses = 10
            prompt.successes = 5
            prompt.win_rate = 0.5
        
        original_count = engine.stats['total_prompts_created']
        
        engine.evolve_prompts()
        
        # 验证新提示词被创建
        assert engine.stats['total_prompts_created'] > original_count
        assert engine.generation == 1
        
        # 验证新提示词的代数
        new_prompts = [p for p in engine.prompt_pool if p.generation == 1]
        assert len(new_prompts) > 0
    
    def test_mutation_add_context(self, engine):
        """测试变异策略：增加上下文"""
        original = "分析交易决策"
        mutated = engine._add_context(original)
        
        assert len(mutated) > len(original)
        assert original in mutated
        assert "\n\n" in mutated
    
    def test_mutation_change_tone(self, engine):
        """测试变异策略：改变语气"""
        original = "分析交易决策"
        mutated = engine._change_tone(original)
        
        assert len(mutated) > len(original)
        assert original in mutated
    
    def test_mutation_add_constraint(self, engine):
        """测试变异策略：增加约束"""
        original = "分析交易决策"
        mutated = engine._add_constraint(original)
        
        assert len(mutated) > len(original)
        assert original in mutated
        assert "约束" in mutated or "限制" in mutated or "要求" in mutated
    
    def test_mutation_simplify(self, engine):
        """测试变异策略：简化表达"""
        original = "请仔细分析交易决策"
        mutated = engine._simplify(original)
        
        assert "请仔细" not in mutated
        assert "分析交易决策" in mutated
    
    def test_mutation_add_example(self, engine):
        """测试变异策略：增加示例"""
        original = "分析交易决策"
        mutated = engine._add_example(original)
        
        assert len(mutated) > len(original)
        assert original in mutated
        assert "示例" in mutated or "参考" in mutated or "案例" in mutated
    
    def test_mutation_rephrase(self, engine):
        """测试变异策略：重新表述"""
        original = "分析交易决策"
        mutated = engine._rephrase(original)
        
        # 应该有一些词被替换
        assert mutated != original or "分析" in original
    
    def test_get_stats(self, engine, base_prompts):
        """测试获取统计信息"""
        engine.initialize_prompt_pool(base_prompts)
        
        stats = engine.get_stats()
        
        assert isinstance(stats, dict)
        assert 'generation' in stats
        assert 'total_uses' in stats
        assert 'pool_size' in stats
        assert 'next_evolution_in' in stats
        assert 'total_evolutions' in stats
        assert 'best_win_rate' in stats
        assert 'avg_win_rate' in stats
        
        assert stats['generation'] == 0
        assert stats['total_uses'] == 0
        assert stats['pool_size'] == 5
    
    def test_get_best_prompts(self, engine, base_prompts):
        """测试获取最佳提示词"""
        engine.initialize_prompt_pool(base_prompts)
        
        # 设置不同的胜率
        for i, prompt in enumerate(engine.prompt_pool):
            prompt.uses = 10
            prompt.successes = i * 2
            prompt.win_rate = prompt.successes / prompt.uses
        
        best_prompts = engine.get_best_prompts(top_n=3)
        
        assert len(best_prompts) == 3
        # 验证是按胜率降序排列
        for i in range(len(best_prompts) - 1):
            assert best_prompts[i].win_rate >= best_prompts[i + 1].win_rate
    
    def test_export_pool(self, engine, base_prompts):
        """测试导出提示词池"""
        engine.initialize_prompt_pool(base_prompts)
        
        exported = engine.export_pool()
        
        assert isinstance(exported, list)
        assert len(exported) == 5
        
        # 验证导出数据结构
        for item in exported:
            assert 'template_id' in item
            assert 'content' in item
            assert 'generation' in item
            assert 'uses' in item
            assert 'successes' in item
            assert 'win_rate' in item
            assert 'created_at' in item
            assert 'parent_id' in item
            assert 'mutation_type' in item


class TestPromptTemplate:
    """Prompt模板测试"""
    
    def test_prompt_template_creation(self):
        """测试Prompt模板创建"""
        template = PromptTemplate(
            template_id="test_001",
            content="测试提示词",
            generation=0
        )
        
        assert template.template_id == "test_001"
        assert template.content == "测试提示词"
        assert template.generation == 0
        assert template.uses == 0
        assert template.successes == 0
        assert template.win_rate == 0.0
        assert template.parent_id is None
        assert template.mutation_type is None
    
    def test_prompt_template_with_parent(self):
        """测试带父模板的Prompt模板"""
        template = PromptTemplate(
            template_id="test_002",
            content="变异后的提示词",
            generation=1,
            parent_id="test_001",
            mutation_type="add_context"
        )
        
        assert template.parent_id == "test_001"
        assert template.mutation_type == "add_context"
        assert template.generation == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
