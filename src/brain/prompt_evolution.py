"""
Prompt进化引擎 - 基于UCB多臂老虎机的自动进化

白皮书依据: 第四章 4.6 提示词进化引擎 (Prompt Evolution Engine)

核心思想:
让AI审计提示词自动进化，基于UCB多臂老虎机+遗传算法优化提示词性能。

功能:
- UCB多臂老虎机选择策略
- 遗传算法变异优化
- 性能追踪和统计
- 自动进化触发

设计原则:
- 探索与利用平衡（UCB算法）
- 精英保留策略
- 多样化变异策略
- 性能驱动进化
"""

import math
import random
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from loguru import logger


@dataclass
class PromptTemplate:
    """Prompt模板（进化版本）"""

    template_id: str  # 模板ID
    content: str  # 提示词内容
    generation: int  # 代数
    uses: int = 0  # 使用次数
    successes: int = 0  # 成功次数
    win_rate: float = 0.0  # 胜率
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    parent_id: Optional[str] = None  # 父模板ID
    mutation_type: Optional[str] = None  # 变异类型


class PromptEvolutionEngine:
    """Prompt进化引擎

    白皮书依据: 第四章 4.6 提示词进化引擎

    功能:
    - UCB多臂老虎机选择策略
    - 遗传算法变异优化
    - 性能追踪和统计
    - 自动进化触发
    """

    def __init__(
        self, pool_size: int = 10, evolution_interval: int = 100, elite_count: int = 3, exploration_param: float = 2.0
    ):
        """初始化Prompt进化引擎

        Args:
            pool_size: 提示词池大小
            evolution_interval: 进化间隔（使用次数）
            elite_count: 精英保留数量
            exploration_param: UCB探索参数
        """
        self.pool_size = pool_size
        self.evolution_interval = evolution_interval
        self.elite_count = elite_count
        self.exploration_param = exploration_param

        self.prompt_pool: List[PromptTemplate] = []
        self.generation = 0
        self.total_uses = 0

        # 统计信息
        self.stats = {"total_evolutions": 0, "best_win_rate": 0.0, "avg_win_rate": 0.0, "total_prompts_created": 0}

        logger.info(
            f"[PromptEvolutionEngine] Initialized: " f"pool_size={pool_size}, evolution_interval={evolution_interval}"
        )

    def initialize_prompt_pool(self, base_prompts: List[str]):
        """初始化提示词池

        Args:
            base_prompts: 基础提示词列表
        """
        self.prompt_pool = []

        for i, content in enumerate(base_prompts):
            prompt = PromptTemplate(template_id=f"prompt_{i:03d}_gen0", content=content, generation=0)
            self.prompt_pool.append(prompt)
            self.stats["total_prompts_created"] += 1

        logger.info(f"[PromptEvolutionEngine] Initialized pool with {len(base_prompts)} prompts")

    def select_prompt(self, strategy: str = "ucb") -> PromptTemplate:
        """选择提示词

        白皮书依据: 第四章 4.6 UCB策略

        Args:
            strategy: 选择策略 (ucb/greedy/random)

        Returns:
            PromptTemplate: 选中的提示词模板
        """
        if not self.prompt_pool:
            raise ValueError("Prompt pool is empty. Call initialize_prompt_pool() first.")

        if strategy == "ucb":  # pylint: disable=no-else-return
            return self._select_ucb()
        elif strategy == "greedy":
            return self._select_greedy()
        elif strategy == "random":
            return self._select_random()
        else:
            raise ValueError(f"Unknown strategy: {strategy}")

    def _select_ucb(self) -> PromptTemplate:
        """UCB选择策略

        UCB公式: 平均胜率 + sqrt(ln(总使用次数) / 该提示词使用次数) * 探索参数

        Returns:
            PromptTemplate: 选中的提示词模板
        """
        ucb_scores = []

        for prompt in self.prompt_pool:
            if prompt.uses == 0:
                # 未使用的提示词，给予无限大的UCB分数（优先探索）
                ucb_score = float("inf")
            else:
                # UCB = 平均胜率 + 探索奖励
                exploitation = prompt.win_rate
                exploration = math.sqrt(math.log(self.total_uses + 1) / prompt.uses) * self.exploration_param
                ucb_score = exploitation + exploration

            ucb_scores.append((prompt, ucb_score))

        # 选择UCB分数最高的
        selected_prompt = max(ucb_scores, key=lambda x: x[1])[0]

        logger.debug(
            f"[PromptEvolutionEngine] Selected prompt: {selected_prompt.template_id}, "
            f"win_rate={selected_prompt.win_rate:.2%}, uses={selected_prompt.uses}"
        )

        return selected_prompt

    def _select_greedy(self) -> PromptTemplate:
        """贪心选择策略（选择胜率最高的）

        Returns:
            PromptTemplate: 选中的提示词模板
        """
        return max(self.prompt_pool, key=lambda x: x.win_rate)

    def _select_random(self) -> PromptTemplate:
        """随机选择策略

        Returns:
            PromptTemplate: 选中的提示词模板
        """
        return random.choice(self.prompt_pool)

    def update_performance(
        self, template_id: str, success: bool, confidence: float = 1.0
    ):  # pylint: disable=unused-argument
        """更新提示词性能

        Args:
            template_id: 模板ID
            success: 是否成功
            confidence: 置信度（可选，用于加权）
        """
        # 查找并更新提示词
        for prompt in self.prompt_pool:
            if prompt.template_id == template_id:
                prompt.uses += 1
                if success:
                    prompt.successes += 1
                prompt.win_rate = prompt.successes / prompt.uses

                logger.debug(
                    f"[PromptEvolutionEngine] Updated {template_id}: "
                    f"win_rate={prompt.win_rate:.2%}, uses={prompt.uses}"
                )
                break

        self.total_uses += 1

        # 更新统计
        self._update_stats()

        # 检查是否需要进化
        if self.total_uses % self.evolution_interval == 0:
            self.evolve_prompts()

    def evolve_prompts(self):
        """进化提示词池

        白皮书依据: 第四章 4.6 遗传算法变异优化

        进化策略:
        1. 精英保留（保留top N）
        2. 对精英进行变异
        3. 替换表现最差的提示词
        """
        logger.info(f"[PromptEvolutionEngine] 🧬 Evolution - Generation {self.generation + 1}")

        # 排序（按胜率）
        self.prompt_pool.sort(key=lambda x: x.win_rate, reverse=True)

        # 精英保留
        elites = self.prompt_pool[: self.elite_count]
        logger.info(f"[PromptEvolutionEngine] Elite retention: {self.elite_count} prompts")
        for elite in elites:
            logger.info(f"  {elite.template_id}: win_rate={elite.win_rate:.2%}, uses={elite.uses}")

        # 生成新提示词
        new_prompts = elites.copy()

        # 对每个精英进行变异
        for elite in elites:
            # 6种变异策略
            mutations = [
                ("add_context", self._add_context),
                ("change_tone", self._change_tone),
                ("add_constraint", self._add_constraint),
                ("simplify", self._simplify),
                ("add_example", self._add_example),
                ("rephrase", self._rephrase),
            ]

            # 随机选择3种变异
            selected_mutations = random.sample(mutations, min(3, len(mutations)))

            for mutation_name, mutation_func in selected_mutations:
                mutated_content = mutation_func(elite.content)

                new_prompt = PromptTemplate(
                    template_id=f"prompt_{self.stats['total_prompts_created']:03d}_gen{self.generation+1}",
                    content=mutated_content,
                    generation=self.generation + 1,
                    parent_id=elite.template_id,
                    mutation_type=mutation_name,
                )
                new_prompts.append(new_prompt)
                self.stats["total_prompts_created"] += 1

        # 替换表现最差的提示词
        self.prompt_pool = new_prompts[: self.pool_size]
        self.generation += 1
        self.stats["total_evolutions"] += 1

        logger.info(f"[PromptEvolutionEngine] New generation pool size: {len(self.prompt_pool)}")

    # ========== 变异策略 ==========

    def _add_context(self, content: str) -> str:
        """变异策略1: 增加上下文

        Args:
            content: 原始内容

        Returns:
            str: 变异后的内容
        """
        contexts = [
            "\n\n附加上下文: 考虑近期市场波动率和风险因素。",
            "\n\n上下文: 在当前市场状态下评估。",
            "\n\n注意: 特别关注仓位管理和风险控制。",
            "\n\n背景: 结合主力资金流向和市场情绪。",
            "\n\n提示: 考虑技术指标的综合信号。",
        ]
        return content + random.choice(contexts)

    def _change_tone(self, content: str) -> str:
        """变异策略2: 改变语气

        Args:
            content: 原始内容

        Returns:
            str: 变异后的内容
        """
        tone_prefixes = ["请仔细", "务必认真", "请全面", "请深入", "请客观"]
        return random.choice(tone_prefixes) + content

    def _add_constraint(self, content: str) -> str:
        """变异策略3: 增加约束

        Args:
            content: 原始内容

        Returns:
            str: 变异后的内容
        """
        constraints = [
            "\n\n约束条件: 必须遵守风险控制规则。",
            "\n\n限制: 单股仓位不超过5%。",
            "\n\n要求: 止损线严格执行。",
            "\n\n规则: 优先考虑风险而非收益。",
            "\n\n原则: 顺势而为，不逆市操作。",
        ]
        return content + random.choice(constraints)

    def _simplify(self, content: str) -> str:
        """变异策略4: 简化表达

        Args:
            content: 原始内容

        Returns:
            str: 变异后的内容
        """
        # 移除多余的修饰词
        simplified = content.replace("请仔细", "").replace("务必认真", "")
        simplified = simplified.replace("请全面", "").replace("请深入", "")
        simplified = simplified.strip()
        return simplified if simplified else content

    def _add_example(self, content: str) -> str:
        """变异策略5: 增加示例

        Args:
            content: 原始内容

        Returns:
            str: 变异后的内容
        """
        examples = [
            "\n\n示例: 如果市场处于牛市且个股突破均线，可考虑买入。",
            "\n\n参考: 当亏损超过止损线时，应立即卖出。",
            "\n\n案例: 震荡市中，盈利未达目标位时建议持有观望。",
            "\n\n举例: 高位盈利达30%时，可考虑减仓锁定利润。",
        ]
        return content + random.choice(examples)

    def _rephrase(self, content: str) -> str:
        """变异策略6: 重新表述

        Args:
            content: 原始内容

        Returns:
            str: 变异后的内容
        """
        # 简单的同义词替换
        replacements = {"分析": "评估", "考虑": "权衡", "注意": "关注", "建议": "推荐", "决策": "判断"}

        rephrased = content
        for old, new in replacements.items():
            if old in rephrased:
                rephrased = rephrased.replace(old, new, 1)  # 只替换第一个
                break

        return rephrased

    # ========== 统计和查询 ==========

    def _update_stats(self):
        """更新统计信息"""
        if self.prompt_pool:
            win_rates = [p.win_rate for p in self.prompt_pool if p.uses > 0]
            if win_rates:
                self.stats["best_win_rate"] = max(win_rates)
                self.stats["avg_win_rate"] = sum(win_rates) / len(win_rates)

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息

        Returns:
            Dict[str, Any]: 统计信息
        """
        return {
            **self.stats,
            "generation": self.generation,
            "total_uses": self.total_uses,
            "pool_size": len(self.prompt_pool),
            "next_evolution_in": self.evolution_interval - (self.total_uses % self.evolution_interval),
        }

    def get_best_prompts(self, top_n: int = 5) -> List[PromptTemplate]:
        """获取表现最好的提示词

        Args:
            top_n: 返回前N个

        Returns:
            List[PromptTemplate]: 最佳提示词列表
        """
        sorted_prompts = sorted([p for p in self.prompt_pool if p.uses > 0], key=lambda x: x.win_rate, reverse=True)
        return sorted_prompts[:top_n]

    def export_pool(self) -> List[Dict[str, Any]]:
        """导出提示词池

        Returns:
            List[Dict[str, Any]]: 提示词池数据
        """
        return [
            {
                "template_id": p.template_id,
                "content": p.content,
                "generation": p.generation,
                "uses": p.uses,
                "successes": p.successes,
                "win_rate": p.win_rate,
                "created_at": p.created_at,
                "parent_id": p.parent_id,
                "mutation_type": p.mutation_type,
            }
            for p in self.prompt_pool
        ]


# 测试代码
if __name__ == "__main__":
    print("PromptEvolutionEngine module loaded")
    print("Classes defined:")
    print(f"  PromptEvolutionEngine: {'PromptEvolutionEngine' in globals()}")
    print(f"  PromptTemplate: {'PromptTemplate' in globals()}")
