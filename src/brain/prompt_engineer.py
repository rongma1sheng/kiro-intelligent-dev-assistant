"""
Soldier决策Prompt工程系统

白皮书依据: 第二章 2.1.3 决策流程

功能:
- 交易决策Prompt模板管理
- 上下文注入（市场数据、持仓信息、风险参数）
- Few-shot示例管理
- Prompt版本控制
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import List, Optional

from loguru import logger


class PromptVersion(Enum):
    """Prompt版本枚举"""

    V1_0 = "v1.0"  # 基础版本
    V1_1 = "v1.1"  # 增强风险控制
    V1_2 = "v1.2"  # 优化Few-shot示例


@dataclass
class MarketContext:
    """市场上下文数据"""

    symbol: str
    current_price: float
    price_change_pct: float
    volume: float
    volume_ratio: float  # 量比
    turnover_rate: float  # 换手率
    market_regime: str  # 市场状态：牛市/熊市/震荡/横盘
    sector: str  # 行业
    timestamp: datetime


@dataclass
class PositionContext:
    """持仓上下文数据"""

    symbol: str
    quantity: int
    avg_cost: float
    current_price: float
    unrealized_pnl: float
    unrealized_pnl_pct: float
    holding_days: int


@dataclass
class RiskContext:
    """风险控制上下文"""

    total_position_pct: float  # 总仓位百分比
    max_position_limit: float  # 最大仓位限制
    single_stock_limit: float  # 单股限制
    sector_limit: float  # 行业限制
    stop_loss_line: float  # 止损线
    risk_level: str  # 风险等级：低/中/高


@dataclass
class FewShotExample:
    """Few-shot示例"""

    scenario: str  # 场景描述
    market_context: str  # 市场上下文
    decision: str  # 决策
    reasoning: str  # 推理过程


class PromptEngineer:
    """Soldier决策Prompt工程师

    白皮书依据: 第二章 2.1.3 决策流程

    功能:
    - 生成交易决策Prompt
    - 注入市场/持仓/风险上下文
    - 管理Few-shot示例
    - 版本控制
    """

    def __init__(self, version: PromptVersion = PromptVersion.V1_2):
        """初始化Prompt工程师

        Args:
            version: Prompt版本，默认使用最新版本
        """
        self.version = version
        self.few_shot_examples = self._load_few_shot_examples()

        logger.info(f"[PromptEngineer] Initialized with version: {version.value}")

    def generate_decision_prompt(
        self,
        market_context: MarketContext,
        position_context: Optional[PositionContext] = None,
        risk_context: Optional[RiskContext] = None,
        include_few_shot: bool = True,
    ) -> str:
        """生成交易决策Prompt

        白皮书依据: 第二章 2.1.3 决策流程

        Args:
            market_context: 市场上下文数据
            position_context: 持仓上下文数据（可选）
            risk_context: 风险控制上下文（可选）
            include_few_shot: 是否包含Few-shot示例

        Returns:
            str: 完整的决策Prompt
        """
        # 构建Prompt各部分
        system_prompt = self._build_system_prompt()
        market_info = self._build_market_info(market_context)
        position_info = self._build_position_info(position_context) if position_context else ""
        risk_info = self._build_risk_info(risk_context) if risk_context else ""
        few_shot = self._build_few_shot_examples() if include_few_shot else ""
        task_instruction = self._build_task_instruction()

        # 组装完整Prompt
        prompt = f"""{system_prompt}

{few_shot}

## 当前市场信息
{market_info}

{position_info}

{risk_info}

## 决策任务
{task_instruction}

请基于以上信息，给出你的交易决策和理由。"""

        logger.debug(f"[PromptEngineer] Generated prompt for {market_context.symbol}, length: {len(prompt)}")
        return prompt

    def _build_system_prompt(self) -> str:
        """构建系统提示词

        Returns:
            str: 系统提示词
        """
        return """# 角色定义
你是MIA系统的Soldier Engine（快系统），负责实时交易决策。你的目标是在毫秒级延迟内做出准确的买入/卖出/持有决策。

# 核心原则
1. **快速反应**: 基于实时市场数据快速决策
2. **风险控制**: 严格遵守仓位限制和止损线
3. **理性决策**: 避免情绪化交易，基于数据和逻辑
4. **适应市场**: 根据市场状态调整策略

# 决策框架
- **买入信号**: 价格突破、成交量放大、市场情绪积极
- **卖出信号**: 触及止损线、获利了结、市场转弱
- **持有信号**: 趋势延续、无明显信号、等待更好时机"""

    def _build_market_info(self, context: MarketContext) -> str:
        """构建市场信息

        Args:
            context: 市场上下文

        Returns:
            str: 格式化的市场信息
        """
        return f"""**股票代码**: {context.symbol}
**当前价格**: ¥{context.current_price:.2f}
**涨跌幅**: {context.price_change_pct:+.2f}%
**成交量**: {context.volume:,.0f}
**量比**: {context.volume_ratio:.2f}
**换手率**: {context.turnover_rate:.2f}%
**市场状态**: {context.market_regime}
**所属行业**: {context.sector}
**时间戳**: {context.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"""

    def _build_position_info(self, context: PositionContext) -> str:
        """构建持仓信息

        Args:
            context: 持仓上下文

        Returns:
            str: 格式化的持仓信息
        """
        return f"""## 当前持仓信息
**持仓数量**: {context.quantity}股
**持仓成本**: ¥{context.avg_cost:.2f}
**当前价格**: ¥{context.current_price:.2f}
**浮动盈亏**: ¥{context.unrealized_pnl:+,.2f} ({context.unrealized_pnl_pct:+.2f}%)
**持仓天数**: {context.holding_days}天"""

    def _build_risk_info(self, context: RiskContext) -> str:
        """构建风险控制信息

        Args:
            context: 风险上下文

        Returns:
            str: 格式化的风险信息
        """
        return f"""## 风险控制参数
**当前总仓位**: {context.total_position_pct:.1f}%
**最大仓位限制**: {context.max_position_limit:.1f}%
**单股限制**: {context.single_stock_limit:.1f}%
**行业限制**: {context.sector_limit:.1f}%
**止损线**: {context.stop_loss_line:+.1f}%
**风险等级**: {context.risk_level}"""

    def _build_few_shot_examples(self) -> str:
        """构建Few-shot示例

        Returns:
            str: 格式化的Few-shot示例
        """
        if not self.few_shot_examples:
            return ""

        examples_text = "## 决策示例\n\n"
        for i, example in enumerate(self.few_shot_examples, 1):
            examples_text += f"""### 示例 {i}: {example.scenario}

**市场情况**:
{example.market_context}

**决策**: {example.decision}

**推理过程**:
{example.reasoning}

---

"""
        return examples_text

    def _build_task_instruction(self) -> str:
        """构建任务指令

        Returns:
            str: 任务指令
        """
        return """请分析当前市场情况，给出你的交易决策。

**输出格式**:
```json
{
    "action": "buy|sell|hold",
    "confidence": 0.0-1.0,
    "reasoning": "决策理由（简洁明了）",
    "risk_assessment": "风险评估",
    "target_price": 目标价格（可选）,
    "stop_loss": 止损价格（可选）
}
```

**注意事项**:
1. 决策必须基于数据和逻辑，避免主观臆断
2. 严格遵守风险控制参数
3. 考虑市场状态和行业特征
4. 给出明确的置信度评分"""

    def _load_few_shot_examples(self) -> List[FewShotExample]:
        """加载Few-shot示例

        白皮书依据: 第二章 2.1.3 决策流程

        Returns:
            List[FewShotExample]: Few-shot示例列表
        """
        examples = [
            FewShotExample(
                scenario="突破买入",
                market_context="""股票代码: 600519
当前价格: ¥1850.00
涨跌幅: +3.5%
成交量: 5,200,000
量比: 2.3
换手率: 1.8%
市场状态: 牛市
所属行业: 白酒""",
                decision="buy",
                reasoning="""1. 价格突破前期高点，形成向上突破
2. 成交量显著放大（量比2.3），确认突破有效性
3. 市场处于牛市状态，整体环境有利
4. 白酒行业基本面稳健，长期看好
5. 建议买入，目标价¥1950，止损¥1800""",
            ),
            FewShotExample(
                scenario="止损卖出",
                market_context="""股票代码: 000001
当前价格: ¥12.50
涨跌幅: -5.2%
持仓成本: ¥13.50
浮动盈亏: -7.4%
市场状态: 震荡
所属行业: 银行""",
                decision="sell",
                reasoning="""1. 当前浮动亏损-7.4%，已触及止损线（-3%）
2. 价格持续下跌，未见企稳迹象
3. 市场处于震荡状态，不确定性较高
4. 严格执行风险控制，及时止损
5. 建议卖出，避免损失进一步扩大""",
            ),
            FewShotExample(
                scenario="趋势持有",
                market_context="""股票代码: 300750
当前价格: ¥580.00
涨跌幅: +1.2%
持仓成本: ¥520.00
浮动盈亏: +11.5%
市场状态: 牛市
所属行业: 医药""",
                decision="hold",
                reasoning="""1. 当前盈利+11.5%，处于良好状态
2. 价格保持上涨趋势，未见顶部信号
3. 市场处于牛市，整体环境支持持有
4. 医药行业景气度高，基本面支撑
5. 建议继续持有，等待更好的卖出时机""",
            ),
            FewShotExample(
                scenario="高风险规避",
                market_context="""股票代码: 002xxx
当前价格: ¥25.00
涨跌幅: +8.5%
当前总仓位: 92%
单股限制: 5%
风险等级: 高""",
                decision="hold",
                reasoning="""1. 虽然股票表现强势，但当前总仓位已达92%
2. 接近最大仓位限制（95%），风险敞口过大
3. 当前风险等级为"高"，需要谨慎
4. 不宜继续加仓，避免风险集中
5. 建议持有观望，等待仓位降低后再考虑""",
            ),
            FewShotExample(
                scenario="获利了结",
                market_context="""股票代码: 601318
当前价格: ¥68.00
涨跌幅: +0.5%
持仓成本: ¥55.00
浮动盈亏: +23.6%
持仓天数: 45天
市场状态: 横盘""",
                decision="sell",
                reasoning="""1. 当前盈利+23.6%，已达到较好的收益水平
2. 市场转入横盘状态，上涨动能减弱
3. 持仓45天，短期获利目标已实现
4. 及时锁定利润，落袋为安
5. 建议卖出，将资金转向更有潜力的标的""",
            ),
        ]

        logger.info(f"[PromptEngineer] Loaded {len(examples)} few-shot examples")
        return examples

    def get_version(self) -> str:
        """获取当前Prompt版本

        Returns:
            str: 版本号
        """
        return self.version.value

    def update_version(self, version: PromptVersion):
        """更新Prompt版本

        Args:
            version: 新版本
        """
        old_version = self.version
        self.version = version
        self.few_shot_examples = self._load_few_shot_examples()

        logger.info(f"[PromptEngineer] Updated version: {old_version.value} → {version.value}")


# 测试代码
if __name__ == "__main__":
    print("PromptEngineer module loaded")
    print("Classes defined:")
    print(f"  PromptEngineer: {'PromptEngineer' in globals()}")
    print(f"  MarketContext: {'MarketContext' in globals()}")
    print(f"  PositionContext: {'PositionContext' in globals()}")
    print(f"  RiskContext: {'RiskContext' in globals()}")
    print(f"  FewShotExample: {'FewShotExample' in globals()}")
    print(f"  PromptVersion: {'PromptVersion' in globals()}")
