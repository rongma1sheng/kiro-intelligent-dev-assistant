# Tier 6 Ten Million 策略 (1000万元以上)

## 档位特征

- **资金规模**: 10,000,000+ 元
- **参数来源**: Arena Tier4最优策略参数 + 严格流动性约束
- **滑点基线**: 2.0%
- **流动性要求**: 极高
- **执行方式**: TWAP/VWAP强制执行

## 策略特点

在这个档位：
- 使用Arena Tier4测试的最优参数
- 严格流动性筛选
- 只选择超高流动性标的
- 强制使用TWAP/VWAP执行
- 最小化市场冲击

## 参数继承

从Arena Tier4继承参数，并严格约束：
```python
{
    # Arena Tier4参数
    'max_position': 0.80,
    'max_single_stock': 0.12,
    'max_industry': 0.35,
    'stop_loss_pct': -0.04,
    'take_profit_pct': 0.08,
    
    # Tier6严格约束
    'liquidity_threshold': 200000000,  # 2亿日均成交额
    'max_order_pct_of_volume': 0.01,   # 订单不超过日均1%
    'require_twap_vwap': True,         # 强制TWAP/VWAP
    'only_ultra_liquid': True          # 只选超高流动性
}
```

## 流动性约束

- 只选择日均成交额 > 2亿的标的
- 订单不超过日均成交量的1%
- 强制使用TWAP/VWAP分批执行
- 避免集中交易时段
- 最小化市场冲击成本

## 执行策略

- **TWAP** (Time-Weighted Average Price): 时间加权平均价格执行
- **VWAP** (Volume-Weighted Average Price): 成交量加权平均价格执行
- 订单拆分为多个小单
- 分散在不同时间段执行
