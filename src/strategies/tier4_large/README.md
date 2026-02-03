# Tier 4 Large 策略 (50万-100万元)

## 档位特征

- **资金规模**: 500,000 - 1,000,000 元
- **Arena测试**: 零约束 + 滑点模拟 + 冲击成本模拟
- **滑点基线**: 0.5%
- **流动性要求**: 中高

## 策略特点

在这个档位：
- 滑点和冲击成本显著
- Arena测试时完整模拟交易成本
- 策略需要优化执行效率
- 仍然零约束，自由进化

## Arena进化参数示例

```python
{
    'max_position': 0.80,
    'max_single_stock': 0.12,
    'max_industry': 0.35,
    'stop_loss_pct': -0.04,
    'take_profit_pct': 0.08,
    'trading_frequency': 'low',
    'holding_period_days': 7
}
```

## 成本模拟

Arena测试时会模拟：
- 基础滑点：0.5%
- 市场冲击成本
- 订单拆分需求
- 流动性约束
