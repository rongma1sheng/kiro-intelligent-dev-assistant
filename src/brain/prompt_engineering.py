"""
Prompt工程系统 - 交易决策Prompt模板管理

白皮书依据: 第二章 2.1.3 决策流程

功能:
- 交易决策Prompt模板管理
- 上下文注入（市场数据、持仓信息、风险参数）
- Few-shot示例管理
- Prompt版本控制
- 动态Prompt生成

设计原则:
- 模板化设计，易于维护和扩展
- 上下文注入灵活，支持多种数据源
- Few-shot示例真实可信，覆盖典型场景
- 版本控制完整，支持A/B测试
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from loguru import logger


class PromptVersion(Enum):
    """Prompt版本枚举"""

    V1_0 = "v1.0"  # 基础版本
    V1_1 = "v1.1"  # 增强风险控制
    V1_2 = "v1.2"  # 优化市场状态感知
    V2_0 = "v2.0"  # 重构版本（当前）


class DecisionType(Enum):
    """决策类型"""

    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"
    REDUCE = "reduce"  # 减仓
    INCREASE = "increase"  # 加仓


@dataclass
class MarketContext:
    """市场上下文"""

    # 市场状态
    market_regime: str  # 牛市/熊市/震荡/横盘
    market_sentiment: float  # 市场情绪 [-1, 1]
    volatility: float  # 波动率

    # 个股信息
    symbol: str  # 股票代码
    current_price: float  # 当前价格
    price_change_pct: float  # 涨跌幅
    volume_ratio: float  # 量比
    turnover_rate: float  # 换手率

    # 技术指标
    ma5: float  # 5日均线
    ma20: float  # 20日均线
    rsi: float  # RSI指标
    macd: float  # MACD指标

    # 主力资金
    main_force_inflow: float  # 主力资金净流入
    main_force_probability: float  # 主力概率


@dataclass
class PositionContext:
    """持仓上下文"""

    # 持仓信息
    symbol: str  # 股票代码
    quantity: int  # 持仓数量
    cost_price: float  # 成本价
    current_price: float  # 当前价
    profit_loss_pct: float  # 盈亏比例

    # 仓位信息
    position_ratio: float  # 仓位占比
    available_cash: float  # 可用资金
    total_assets: float  # 总资产


@dataclass
class RiskContext:
    """风险上下文"""

    # 风险等级
    risk_level: str  # 低/中/高

    # 风险限制
    max_position_ratio: float  # 最大仓位比例
    max_single_stock_ratio: float  # 单股最大比例
    stop_loss_ratio: float  # 止损比例

    # 风险指标
    portfolio_volatility: float  # 组合波动率
    max_drawdown: float  # 最大回撤
    sharpe_ratio: float  # 夏普比率


@dataclass
class FewShotExample:
    """Few-shot示例"""

    scenario: str  # 场景描述
    market_context: str  # 市场上下文
    position_context: str  # 持仓上下文
    decision: str  # 决策
    reasoning: str  # 推理过程


class PromptTemplate:
    """Prompt模板基类"""

    def __init__(self, version: PromptVersion = PromptVersion.V2_0):
        """初始化Prompt模板

        Args:
            version: Prompt版本
        """
        self.version = version
        self.few_shot_examples = self._load_few_shot_examples()
        logger.info(f"[PromptTemplate] Initialized with version: {version.value}")

    def _load_few_shot_examples(self) -> List[FewShotExample]:
        """加载Few-shot示例

        Returns:
            List[FewShotExample]: Few-shot示例列表
        """
        examples = [
            # 示例1: 牛市突破买入
            FewShotExample(
                scenario="牛市突破买入",
                market_context="市场状态: 牛市, 情绪: 0.7, 波动率: 0.15",
                position_context="持仓: 0股, 可用资金: 100000元",
                decision="BUY 1000股",
                reasoning="市场处于牛市，个股突破20日均线，主力资金净流入，RSI未超买，建议买入",
            ),
            # 示例2: 止损卖出
            FewShotExample(
                scenario="止损卖出",
                market_context="市场状态: 震荡, 情绪: -0.3, 波动率: 0.25",
                position_context="持仓: 1000股, 成本价: 10.0元, 当前价: 9.2元, 亏损: -8%",
                decision="SELL 1000股",
                reasoning="亏损超过止损线(-3%)，市场情绪转弱，建议止损离场",
            ),
            # 示例3: 震荡市持有
            FewShotExample(
                scenario="震荡市持有",
                market_context="市场状态: 震荡, 情绪: 0.1, 波动率: 0.20",
                position_context="持仓: 500股, 成本价: 10.0元, 当前价: 10.5元, 盈利: +5%",
                decision="HOLD",
                reasoning="市场震荡，个股盈利但未达目标位，主力资金流入放缓，建议持有观望",
            ),
            # 示例4: 高位减仓
            FewShotExample(
                scenario="高位减仓",
                market_context="市场状态: 牛市, 情绪: 0.9, 波动率: 0.30",
                position_context="持仓: 2000股, 成本价: 10.0元, 当前价: 13.0元, 盈利: +30%",
                decision="REDUCE 1000股",
                reasoning="盈利达到目标位，市场情绪过热，波动率上升，建议减仓锁定利润",
            ),
            # 示例5: 熊市空仓
            FewShotExample(
                scenario="熊市空仓",
                market_context="市场状态: 熊市, 情绪: -0.8, 波动率: 0.35",
                position_context="持仓: 0股, 可用资金: 100000元",
                decision="HOLD",
                reasoning="市场处于熊市，情绪极度悲观，波动率高，建议空仓观望，等待市场企稳",
            ),
        ]

        logger.info(f"[PromptTemplate] Loaded {len(examples)} few-shot examples")
        return examples

    def generate_system_prompt(self) -> str:
        """生成系统提示词

        Returns:
            str: 系统提示词
        """
        system_prompt = """你是MIA量化交易系统的Soldier决策引擎，负责快速、准确地做出交易决策。

你的职责:
1. 分析市场状态和个股技术指标
2. 评估持仓情况和风险水平
3. 做出买入/卖出/持有/加仓/减仓决策
4. 提供清晰的决策理由

决策原则:
1. 风险控制优先: 严格遵守止损线和仓位限制
2. 顺势而为: 根据市场状态调整策略
3. 主力跟踪: 关注主力资金流向
4. 技术分析: 结合均线、RSI、MACD等指标
5. 情绪感知: 考虑市场情绪和波动率

输出格式:
{
    "decision": "BUY/SELL/HOLD/REDUCE/INCREASE",
    "quantity": 数量,
    "confidence": 0.0-1.0,
    "reasoning": "决策理由",
    "risk_assessment": "风险评估"
}
"""
        return system_prompt

    def generate_few_shot_prompt(self) -> str:
        """生成Few-shot提示词

        Returns:
            str: Few-shot提示词
        """
        few_shot_prompt = "\n以下是一些典型的决策示例:\n\n"

        for i, example in enumerate(self.few_shot_examples, 1):
            few_shot_prompt += f"示例{i}: {example.scenario}\n"
            few_shot_prompt += f"市场上下文: {example.market_context}\n"
            few_shot_prompt += f"持仓上下文: {example.position_context}\n"
            few_shot_prompt += f"决策: {example.decision}\n"
            few_shot_prompt += f"推理: {example.reasoning}\n\n"

        return few_shot_prompt

    def generate_user_prompt(
        self,
        market_ctx: MarketContext,
        position_ctx: Optional[PositionContext] = None,
        risk_ctx: Optional[RiskContext] = None,
    ) -> str:
        """生成用户提示词

        Args:
            market_ctx: 市场上下文
            position_ctx: 持仓上下文（可选）
            risk_ctx: 风险上下文（可选）

        Returns:
            str: 用户提示词
        """
        # 构建市场上下文部分
        market_section = f"""
当前市场状态:
- 市场环境: {market_ctx.market_regime}
- 市场情绪: {market_ctx.market_sentiment:.2f} (范围: -1到1)
- 波动率: {market_ctx.volatility:.2%}

个股信息:
- 股票代码: {market_ctx.symbol}
- 当前价格: {market_ctx.current_price:.2f}元
- 涨跌幅: {market_ctx.price_change_pct:+.2%}
- 量比: {market_ctx.volume_ratio:.2f}
- 换手率: {market_ctx.turnover_rate:.2%}

技术指标:
- MA5: {market_ctx.ma5:.2f}元
- MA20: {market_ctx.ma20:.2f}元
- RSI: {market_ctx.rsi:.2f}
- MACD: {market_ctx.macd:.4f}

主力资金:
- 主力净流入: {market_ctx.main_force_inflow:+.2f}万元
- 主力概率: {market_ctx.main_force_probability:.2%}
"""

        # 构建持仓上下文部分
        position_section = ""
        if position_ctx:
            position_section = f"""
当前持仓:
- 持仓数量: {position_ctx.quantity}股
- 成本价: {position_ctx.cost_price:.2f}元
- 当前价: {position_ctx.current_price:.2f}元
- 盈亏: {position_ctx.profit_loss_pct:+.2%}
- 仓位占比: {position_ctx.position_ratio:.2%}
- 可用资金: {position_ctx.available_cash:.2f}元
- 总资产: {position_ctx.total_assets:.2f}元
"""
        else:
            position_section = "\n当前持仓: 空仓\n"

        # 构建风险上下文部分
        risk_section = ""
        if risk_ctx:
            risk_section = f"""
风险控制:
- 风险等级: {risk_ctx.risk_level}
- 最大仓位: {risk_ctx.max_position_ratio:.2%}
- 单股限制: {risk_ctx.max_single_stock_ratio:.2%}
- 止损线: {risk_ctx.stop_loss_ratio:.2%}
- 组合波动率: {risk_ctx.portfolio_volatility:.2%}
- 最大回撤: {risk_ctx.max_drawdown:.2%}
- 夏普比率: {risk_ctx.sharpe_ratio:.2f}
"""

        # 组合完整提示词
        user_prompt = market_section + position_section + risk_section
        user_prompt += "\n请根据以上信息，做出交易决策并说明理由。"

        return user_prompt

    def generate_complete_prompt(
        self,
        market_ctx: MarketContext,
        position_ctx: Optional[PositionContext] = None,
        risk_ctx: Optional[RiskContext] = None,
        include_few_shot: bool = True,
    ) -> Dict[str, str]:
        """生成完整的Prompt

        Args:
            market_ctx: 市场上下文
            position_ctx: 持仓上下文（可选）
            risk_ctx: 风险上下文（可选）
            include_few_shot: 是否包含Few-shot示例

        Returns:
            Dict[str, str]: 包含system和user的完整Prompt
        """
        system_prompt = self.generate_system_prompt()

        if include_few_shot:
            system_prompt += "\n" + self.generate_few_shot_prompt()

        user_prompt = self.generate_user_prompt(market_ctx, position_ctx, risk_ctx)

        logger.debug(f"[PromptTemplate] Generated complete prompt for {market_ctx.symbol}")

        return {
            "system": system_prompt,
            "user": user_prompt,
            "version": self.version.value,
            "timestamp": datetime.now().isoformat(),
        }


class PromptManager:
    """Prompt管理器

    白皮书依据: 第二章 2.1.3 决策流程

    功能:
    - Prompt版本管理
    - Prompt模板缓存
    - A/B测试支持
    - 性能统计
    """

    def __init__(self):
        """初始化Prompt管理器"""
        self.templates: Dict[PromptVersion, PromptTemplate] = {}
        self.current_version = PromptVersion.V2_0
        self.stats = {"total_prompts_generated": 0, "prompts_by_version": {}, "avg_prompt_length": 0}

        # 预加载当前版本模板
        self._load_template(self.current_version)

        logger.info(f"[PromptManager] Initialized with version: {self.current_version.value}")

    def _load_template(self, version: PromptVersion) -> PromptTemplate:
        """加载Prompt模板

        Args:
            version: Prompt版本

        Returns:
            PromptTemplate: Prompt模板实例
        """
        if version not in self.templates:
            self.templates[version] = PromptTemplate(version)
            logger.info(f"[PromptManager] Loaded template version: {version.value}")

        return self.templates[version]

    def generate_prompt(  # pylint: disable=too-many-positional-arguments
        self,
        market_ctx: MarketContext,
        position_ctx: Optional[PositionContext] = None,
        risk_ctx: Optional[RiskContext] = None,
        version: Optional[PromptVersion] = None,
        include_few_shot: bool = True,
    ) -> Dict[str, str]:
        """生成Prompt

        Args:
            market_ctx: 市场上下文
            position_ctx: 持仓上下文（可选）
            risk_ctx: 风险上下文（可选）
            version: Prompt版本（可选，默认使用当前版本）
            include_few_shot: 是否包含Few-shot示例

        Returns:
            Dict[str, str]: 完整的Prompt
        """
        # 使用指定版本或当前版本
        template_version = version or self.current_version
        template = self._load_template(template_version)

        # 生成Prompt
        prompt = template.generate_complete_prompt(market_ctx, position_ctx, risk_ctx, include_few_shot)

        # 更新统计
        self._update_stats(template_version, prompt)

        return prompt

    def _update_stats(self, version: PromptVersion, prompt: Dict[str, str]):
        """更新统计信息

        Args:
            version: Prompt版本
            prompt: 生成的Prompt
        """
        self.stats["total_prompts_generated"] += 1

        # 按版本统计
        version_key = version.value
        if version_key not in self.stats["prompts_by_version"]:
            self.stats["prompts_by_version"][version_key] = 0
        self.stats["prompts_by_version"][version_key] += 1

        # 计算平均长度
        prompt_length = len(prompt["system"]) + len(prompt["user"])
        total = self.stats["total_prompts_generated"]
        old_avg = self.stats["avg_prompt_length"]
        self.stats["avg_prompt_length"] = (old_avg * (total - 1) + prompt_length) / total

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息

        Returns:
            Dict[str, Any]: 统计信息
        """
        return {
            **self.stats,
            "current_version": self.current_version.value,
            "loaded_versions": [
                v.value for v in self.templates.keys()  # pylint: disable=consider-iterating-dictionary
            ],  # pylint: disable=consider-iterating-dictionary
        }

    def set_version(self, version: PromptVersion):
        """设置当前版本

        Args:
            version: Prompt版本
        """
        self.current_version = version
        self._load_template(version)
        logger.info(f"[PromptManager] Switched to version: {version.value}")


# 测试代码
if __name__ == "__main__":
    print("PromptEngineering module loaded")
    print("Classes defined:")
    print(f"  PromptTemplate: {'PromptTemplate' in globals()}")
    print(f"  PromptManager: {'PromptManager' in globals()}")
    print(f"  MarketContext: {'MarketContext' in globals()}")
    print(f"  PositionContext: {'PositionContext' in globals()}")
    print(f"  RiskContext: {'RiskContext' in globals()}")
