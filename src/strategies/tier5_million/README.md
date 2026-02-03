# Tier 5 Million 策略 (100万-1000万元)

## 档位特征

- **资金规模**: 1,000,000 - 10,000,000 元
- **参数来源**: Arena Tier4最优策略参数 + 增强流动性约束
- **滑点基线**: 1.0%
- **流动性要求**: 高

## 策略特点

在这个档位：
- 使用Arena Tier4测试的最优参数
- 增强流动性筛选
- 优先高流动性标的
- 考虑市场冲击成本
- 可能需要TWAP执行

## 参数继承

从Arena Tier4继承参数，并增强：
```python
{
    # Arena Tier4参数
    'max_position': 0.80,
    'max_single_stock': 0.12,
    'max_industry': 0.35,
    'stop_loss_pct': -0.04,
    'take_profit_pct': 0.08,
    
    # Tier5增强约束
    'liquidity_threshold': 50000000,  # 5千万日均成交额
    'max_order_pct_of_volume': 0.03,  # 订单不超过日均3%
    'prefer_high_liquidity': True
}
```

## 流动性约束

- 只选择日均成交额 > 5千万的标的
- 订单不超过日均成交量的3%
- 优先选择流动性最好的标的
- 考虑使用TWAP分批执行
