# Tier 2 Small 策略 (1万-10万元)

## 档位特征

- **资金规模**: 10,000 - 100,000 元
- **Arena测试**: 零约束，完全自由进化
- **滑点基线**: 0.2%
- **流动性要求**: 低

## 策略特点

在这个档位，策略可以：
- 中高频交易
- 适度分散（但仍可集中，由Arena决定）
- 灵活调仓
- 平衡收益与风险

## Arena进化参数示例

```python
{
    'max_position': 0.90,
    'max_single_stock': 0.20,
    'max_industry': 0.50,
    'stop_loss_pct': -0.06,
    'take_profit_pct': 0.12,
    'trading_frequency': 'medium',
    'holding_period_days': 3
}
```

## 注意事项

参数由Arena自由进化，无预设约束。
