# Tier 3 Medium 策略 (10万-50万元)

## 档位特征

- **资金规模**: 100,000 - 500,000 元
- **Arena测试**: 零约束 + 滑点模拟
- **滑点基线**: 0.3% - 0.5%
- **流动性要求**: 中等

## 策略特点

在这个档位：
- 开始考虑滑点影响
- Arena测试时模拟真实滑点
- 策略需要适应滑点成本
- 仍然零约束，自由进化

## Arena进化参数示例

```python
{
    'max_position': 0.85,
    'max_single_stock': 0.15,
    'max_industry': 0.40,
    'stop_loss_pct': -0.05,
    'take_profit_pct': 0.10,
    'trading_frequency': 'medium',
    'holding_period_days': 5
}
```

## 滑点模拟

Arena测试时会模拟：
- 基础滑点：0.3% - 0.5%
- 订单大小影响
- 市场流动性影响
