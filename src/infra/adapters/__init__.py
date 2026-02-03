"""数据源适配器包 - 智能数据探针与桥接系统

白皮书依据: 第三章 3.2 基础设施与数据治理
需求: requirements.md 6.1-6.10
设计: design.md 核心组件设计 - 适配器层

本包提供数据源适配器的实现，包括：
- BaseAdapter: 抽象基类，定义统一接口
- 具体适配器: Yahoo Finance, AKShare, Alpha Vantage等

所有适配器都继承自BaseAdapter，确保接口一致性。
"""

from src.infra.adapters.base_adapter import BaseAdapter

__all__ = [
    "BaseAdapter",
]
