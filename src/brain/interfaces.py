"""
AI三脑接口定义 - 解决循环依赖的核心抽象

白皮书依据: 第二章 2.1 AI三脑架构 + 架构审计报告循环依赖修复
需求: 4.4 - 定义AI三脑接口

通过接口抽象实现解耦，彻底解决AI三脑之间的循环依赖问题：
- ISoldierEngine: Soldier引擎接口（实时决策）
- ICommanderEngine: Commander引擎接口（策略分析）
- IScholarEngine: Scholar引擎接口（因子研究）

设计原则:
1. 接口隔离: 每个接口只包含必要的方法
2. 依赖倒置: 高层模块依赖抽象，不依赖具体实现
3. 单一职责: 每个接口对应一个AI脑的核心职责
4. 异步优先: 所有接口方法都是异步的，支持非阻塞调用
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List


class ISoldierEngine(ABC):
    """Soldier引擎接口 - 执行层AI大脑

    白皮书依据: 第二章 2.1 AI三脑架构 - Soldier (执行层)
    需求: 4.4 - ISoldierEngine接口定义

    核心职责:
    - 实时交易决策（延迟 < 20ms P99）
    - 多模式推理（本地/云端/离线）
    - 决策缓存和优化
    - 健康监控和自动恢复

    接口设计原则:
    - 所有方法异步执行，支持高并发
    - 返回标准化的决策结果格式
    - 支持上下文传递和状态查询
    """

    @abstractmethod
    async def decide(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """做出交易决策

        白皮书依据: 第二章 2.1 Soldier决策流程
        性能要求: P99延迟 < 20ms

        Args:
            context: 决策上下文，包含以下字段：
                - symbol: str - 股票代码
                - market_data: Dict[str, Any] - 市场数据
                - timestamp: str - 时间戳
                - request_id: str - 请求ID（可选）

        Returns:
            Dict[str, Any]: 决策结果，包含以下字段：
                - decision: Dict - 决策详情
                    - action: str - 交易动作 (buy/sell/hold/strong_buy/strong_sell)
                    - confidence: float - 置信度 [0.0, 1.0]
                    - reasoning: str - 推理依据
                    - signal_strength: float - 信号强度 [0.0, 1.0]
                    - risk_level: str - 风险等级 (low/medium/high)
                    - execution_priority: int - 执行优先级 [1-10]
                    - latency_ms: float - 推理延迟(毫秒)
                    - source_mode: str - 推理模式 (normal/degraded/offline)
                - metadata: Dict - 元数据
                    - soldier_mode: str - Soldier运行模式
                    - timestamp: str - 决策时间戳
                    - source: str - 决策来源

        Raises:
            ValueError: 当context格式无效时
            TimeoutError: 当决策超时时
            RuntimeError: 当系统故障时
        """

    @abstractmethod
    async def get_status(self) -> Dict[str, Any]:
        """获取Soldier引擎状态

        白皮书依据: 第二章 2.1 健康监控

        Returns:
            Dict[str, Any]: 状态信息，包含以下字段：
                - mode: str - 运行模式 (normal/degraded/offline)
                - state: str - 当前状态 (IDLE/DECIDING/ERROR)
                - failure_count: int - 故障计数
                - last_decision_time: str - 最后决策时间
                - stats: Dict - 统计信息
                    - total_decisions: int - 总决策数
                    - local_decisions: int - 本地决策数
                    - cloud_decisions: int - 云端决策数
                    - cache_hits: int - 缓存命中数
                    - error_count: int - 错误计数
                    - avg_latency_ms: float - 平均延迟
                    - p99_latency_ms: float - P99延迟
                    - success_rate: float - 成功率
                - cache_size: int - 缓存大小
                - memory_size: int - 短期记忆大小
                - redis_connected: bool - Redis连接状态
        """

    @abstractmethod
    def get_state(self) -> str:
        """获取当前状态

        Returns:
            str: 当前状态 (IDLE/DECIDING/ERROR/READY)
        """

    @abstractmethod
    async def initialize(self):
        """初始化Soldier引擎

        白皮书依据: 第二章 2.1 Soldier初始化流程

        初始化流程:
        1. 初始化Redis连接
        2. 初始化本地模型
        3. 设置事件订阅
        4. 启动健康检查循环

        Raises:
            RuntimeError: 当初始化失败时
        """


class ICommanderEngine(ABC):
    """Commander引擎接口 - 战略层AI大脑

    白皮书依据: 第二章 2.2 AI三脑架构 - Commander (战略层)
    需求: 4.4 - ICommanderEngine接口定义

    核心职责:
    - 策略分析和资产配置
    - 市场状态识别
    - 风险控制和限制
    - 跨脑协调和决策融合

    接口设计原则:
    - 支持多种市场状态识别
    - 提供完整的风险控制机制
    - 返回结构化的策略分析结果
    - 支持资产配置优化
    """

    @abstractmethod
    async def analyze_strategy(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """策略分析

        白皮书依据: 第二章 2.2 Commander引擎 - 策略分析流程
        性能要求: P95延迟 < 500ms
        需求: 1.1, 1.2, 1.3, 1.5 - 完整的策略分析流程

        Args:
            market_data: 市场数据，包含以下字段：
                - index_level: float - 指数水平
                - volatility: float - 波动率
                - volume: int - 成交量
                - trend: float - 趋势指标
                - turnover: float - 换手率（可选）
                - timestamp: str - 时间戳

        Returns:
            Dict[str, Any]: 策略分析结果，包含以下字段：
                - recommendation: str - 策略建议 (buy/sell/hold/reduce)
                - confidence: float - 置信度 [0.0, 1.0]
                - risk_level: str - 风险等级 (low/medium/high)
                - allocation: Dict[str, float] - 资产配置建议
                    - stocks: float - 股票配置比例
                    - bonds: float - 债券配置比例
                    - cash: float - 现金配置比例
                - reasoning: str - 分析推理
                - market_regime: str - 市场状态 (bull/bear/volatile/sideways)
                - time_horizon: str - 投资时间范围 (short/medium/long)
                - metadata: Dict - 元数据
                    - commander_mode: str - Commander模式
                    - timestamp: str - 分析时间戳
                    - source: str - 分析来源
                    - risk_controls_applied: bool - 是否应用了风险控制

        Raises:
            ValueError: 当market_data格式无效时
            TimeoutError: 当分析超时时
            RuntimeError: 当系统故障时
        """

    @abstractmethod
    async def get_allocation(self) -> Dict[str, Any]:
        """获取资产配置建议

        白皮书依据: 第二章 2.2 Commander引擎 - 资产配置

        Returns:
            Dict[str, Any]: 资产配置信息，包含以下字段：
                - allocation: Dict[str, float] - 当前配置建议
                    - stocks: float - 股票配置比例
                    - bonds: float - 债券配置比例
                    - cash: float - 现金配置比例
                - market_regime: str - 市场状态
                - risk_level: str - 风险等级
                - rebalance_needed: bool - 是否需要再平衡
                - timestamp: str - 配置时间戳
        """

    @abstractmethod
    def identify_market_regime(self, market_data: Dict[str, Any]) -> str:
        """识别市场状态

        白皮书依据: 第二章 2.2 Commander引擎 - 市场状态识别
        需求: 1.6 - 支持多种市场状态识别

        A股优化的市场状态定义（趋势优先）:
        - bull: 牛市 - 上涨趋势(trend > 0.04)，允许高波动
        - bear: 熊市 - 下跌趋势(trend < -0.04)，允许高波动
        - volatile: 震荡市 - 无明显趋势(|trend| <= 0.04) + 高波动(volatility > 0.05)
        - sideways: 横盘市 - 无明显趋势(|trend| <= 0.04) + 低波动(volatility <= 0.05)

        Args:
            market_data: 市场数据，包含trend、volatility等指标

        Returns:
            str: 市场状态 (bull/bear/volatile/sideways)
        """

    @abstractmethod
    async def initialize(self):
        """初始化Commander引擎

        白皮书依据: 第二章 2.2 Commander引擎初始化

        初始化流程:
        1. 获取事件总线
        2. 订阅相关事件
        3. 初始化LLM网关
        4. 设置风险控制参数

        Raises:
            RuntimeError: 当初始化失败时
        """


class IScholarEngine(ABC):
    """Scholar引擎接口 - 研究层AI大脑

    白皮书依据: 第二章 2.3 AI三脑架构 - Scholar (研究层)
    需求: 4.4 - IScholarEngine接口定义

    核心职责:
    - 因子研究和发现
    - 论文分析和洞察提取
    - 因子库管理和维护
    - 量化研究支持

    接口设计原则:
    - 支持多种因子类型研究
    - 提供完整的IC/IR计算
    - 返回结构化的研究结果
    - 支持论文分析和知识提取
    """

    @abstractmethod
    async def research_factor(self, factor_expression: str) -> Dict[str, Any]:
        """因子研究

                白皮书依据: 第二章 2.3 Scholar引擎 - 因子研究流程
                性能要求: P95延迟 < 2s
                需求: 2.1, 2.3, 2.5 - 完整的因子研究流程

                Args:
                    factor_expression: 因子表达式，支持以下格式：
                        - 基础表达式: "close / delay(close, 1) - 1"
                        - 带名称: "# 动量因子
        close / delay(close, 1) - 1"
                        - 复杂表达式: "rank(delta(close, 5)) / rank(volume)"

                Returns:
                    Dict[str, Any]: 因子研究结果，包含以下字段：
                        - factor_name: str - 因子名称
                        - factor_score: float - 因子评分 [0.0, 1.0]
                        - ic_mean: float - IC均值
                        - ic_std: float - IC标准差
                        - ir: float - 信息比率 (IC均值 / IC标准差)
                        - insight: str - 研究洞察
                        - confidence: float - 置信度 [0.0, 1.0]
                        - risk_metrics: Dict[str, float] - 风险指标
                            - volatility: float - 波动率
                            - max_drawdown: float - 最大回撤
                            - skewness: float - 偏度
                            - kurtosis: float - 峰度
                            - value_at_risk_95: float - 95% VaR
                        - theoretical_basis: str - 理论基础
                        - metadata: Dict[str, Any] - 元数据
                            - expression: str - 原始表达式
                            - parsed: Dict - 解析结果
                            - timestamp: str - 研究时间戳
                            - research_time_ms: float - 研究耗时

                Raises:
                    ValueError: 当factor_expression格式无效时
                    TimeoutError: 当研究超时时
                    RuntimeError: 当系统故障时
        """

    @abstractmethod
    async def analyze_paper(self, paper_content: str) -> Dict[str, Any]:
        """论文分析

        白皮书依据: 第二章 2.3 Scholar引擎 - 论文分析功能
        需求: 2.2 - 论文分析功能

        Args:
            paper_content: 论文内容，支持以下格式：
                - 纯文本内容
                - 包含标题的结构化文本
                - PDF提取的文本内容

        Returns:
            Dict[str, Any]: 论文分析结果，包含以下字段：
                - paper_title: str - 论文标题
                - key_insights: List[str] - 关键洞察列表
                - practical_applications: List[str] - 实践应用列表
                - implementation_difficulty: str - 实施难度 (easy/medium/hard)
                - relevance_score: float - 相关性评分 [0.0, 1.0]
                - innovation_level: str - 创新程度 (low/medium/high)
                - summary: str - 论文摘要
                - metadata: Dict[str, Any] - 元数据
                    - analysis_time: str - 分析时间戳
                    - word_count: int - 字数统计
                    - language: str - 语言类型

        Raises:
            ValueError: 当paper_content格式无效时
            TimeoutError: 当分析超时时
            RuntimeError: 当系统故障时
        """

    @abstractmethod
    def get_factor_library(self) -> Dict[str, List[str]]:
        """获取因子库

        白皮书依据: 第二章 2.3 Scholar引擎 - 因子库管理
        需求: 2.6 - 因子库管理

        Returns:
            Dict[str, List[str]]: 因子库，按类别组织：
                - momentum: List[str] - 动量因子列表
                - value: List[str] - 价值因子列表
                - quality: List[str] - 质量因子列表
                - growth: List[str] - 成长因子列表
                - volatility: List[str] - 波动率因子列表
                - liquidity: List[str] - 流动性因子列表
        """

    @abstractmethod
    async def initialize(self):
        """初始化Scholar引擎

        白皮书依据: 第二章 2.3 Scholar引擎初始化

        初始化流程:
        1. 获取事件总线
        2. 设置事件订阅
        3. 初始化LLM网关
        4. 加载因子库

        Raises:
            RuntimeError: 当初始化失败时
        """

    @abstractmethod
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息

        Returns:
            Dict[str, Any]: 统计信息，包含以下字段：
                - total_researches: int - 总研究数
                - factor_analyses: int - 因子分析数
                - paper_analyses: int - 论文分析数
                - cache_hits: int - 缓存命中数
                - avg_research_time_ms: float - 平均研究时间
                - error_count: int - 错误计数
                - factors_discovered: int - 发现的因子数
                - state: str - 当前状态
                - last_research_time: str - 最后研究时间
                - cache_size: int - 缓存大小
                - factor_library_size: int - 因子库大小
        """


# 接口注册函数
def register_ai_brain_interfaces():
    """注册AI三脑接口到依赖注入容器

    白皮书依据: 第二章 2.1 AI三脑架构 + 架构审计报告循环依赖修复
    需求: 4.4, 4.5 - 接口定义和依赖注入配置

    这个函数将在系统启动时调用，注册接口到依赖注入容器。
    具体的实现类将在各自的模块中注册。
    """
    from ..core.dependency_container import get_container  # pylint: disable=import-outside-toplevel

    get_container()

    # 注册接口（实现类将在各自模块中注册）
    # 这里只是声明接口存在，具体映射在实现类中完成

    logger.info("[Interfaces] AI三脑接口注册完成")  # pylint: disable=e0602
    logger.info("[Interfaces] ISoldierEngine - 执行层AI大脑接口")  # pylint: disable=e0602
    logger.info("[Interfaces] ICommanderEngine - 战略层AI大脑接口")  # pylint: disable=e0602
    logger.info("[Interfaces] IScholarEngine - 研究层AI大脑接口")  # pylint: disable=e0602


# 接口验证函数
def validate_ai_brain_interfaces():
    """验证AI三脑接口实现

    白皮书依据: 架构审计报告 - 接口合规性检查

    Returns:
        Dict[str, bool]: 验证结果
            - soldier_interface_valid: bool
            - commander_interface_valid: bool
            - scholar_interface_valid: bool
            - all_interfaces_valid: bool
    """
    from ..core.dependency_container import get_container  # pylint: disable=import-outside-toplevel

    container = get_container()
    results = {}

    # 检查Soldier接口
    try:
        if container.is_registered(ISoldierEngine):
            soldier = container.resolve(ISoldierEngine)
            results["soldier_interface_valid"] = isinstance(soldier, ISoldierEngine)
        else:
            results["soldier_interface_valid"] = False
    except Exception:  # pylint: disable=broad-exception-caught
        results["soldier_interface_valid"] = False

    # 检查Commander接口
    try:
        if container.is_registered(ICommanderEngine):
            commander = container.resolve(ICommanderEngine)
            results["commander_interface_valid"] = isinstance(commander, ICommanderEngine)
        else:
            results["commander_interface_valid"] = False
    except Exception:  # pylint: disable=broad-exception-caught
        results["commander_interface_valid"] = False

    # 检查Scholar接口
    try:
        if container.is_registered(IScholarEngine):
            scholar = container.resolve(IScholarEngine)
            results["scholar_interface_valid"] = isinstance(scholar, IScholarEngine)
        else:
            results["scholar_interface_valid"] = False
    except Exception:  # pylint: disable=broad-exception-caught
        results["scholar_interface_valid"] = False

    # 总体验证结果
    results["all_interfaces_valid"] = all(
        [results["soldier_interface_valid"], results["commander_interface_valid"], results["scholar_interface_valid"]]
    )

    return results


if __name__ == "__main__":
    # 测试接口定义
    print("AI三脑接口定义测试")
    print("=" * 50)

    # 验证接口方法签名
    import inspect

    for interface_cls in [ISoldierEngine, ICommanderEngine, IScholarEngine]:
        print(f"\n{interface_cls.__name__} 接口方法:")
        for name, method in inspect.getmembers(interface_cls, predicate=inspect.isfunction):
            if not name.startswith("_"):
                signature = inspect.signature(method)
                print(f"  - {name}{signature}")

    print("\n接口定义完成！")
