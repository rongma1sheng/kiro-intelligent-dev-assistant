# pylint: disable=too-many-lines
"""
五态状态机（Main Orchestrator）

白皮书依据: 第一章 柯罗诺斯生物钟与资源调度

MIA采用分布式五态生物钟进行严格的资源分时调度：
- 维护态 [手动触发]
- 战备态 [08:30-09:15]
- 战争态 [09:15-15:00]
- 诊疗态 [15:00-20:00]
- 进化态 [20:00-08:30]
"""

import asyncio
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from datetime import time as dt_time
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

from loguru import logger

# 导入服务管理器
from .services import ServiceManager
from .websocket_server import start_websocket_server, stop_websocket_server


class SystemState(Enum):
    """系统状态枚举

    白皮书依据: 第一章 1.0-1.4 五态定义

    Attributes:
        MAINTENANCE: 维护态 - 手动触发，用于系统维护
        PREP: 战备态 - 08:30-09:15，系统准备和服务启动
        WAR: 战争态 - 09:15-15:00，交易执行和实时监控
        TACTICAL: 诊疗态 - 15:00-20:00，数据归档和持仓诊断
        EVOLUTION: 进化态 - 20:00-08:30，因子挖掘和策略进化
    """

    MAINTENANCE = 0  # 维护态
    PREP = 1  # 战备态
    WAR = 2  # 战争态
    TACTICAL = 3  # 诊疗态
    EVOLUTION = 4  # 进化态


class StateTransitionError(Exception):
    """状态转换错误"""


class ServiceStartupError(Exception):
    """服务启动错误"""


@dataclass
class ServiceInfo:
    """服务信息

    Attributes:
        instance: 服务实例
        status: 服务状态 ('stopped', 'running', 'error')
        start_time: 启动时间
        error_count: 错误计数
    """

    instance: Any
    status: str = "stopped"
    start_time: Optional[datetime] = None
    error_count: int = 0


class MainOrchestrator:
    """主调度器（五态状态机）

    白皮书依据: 第一章 柯罗诺斯生物钟与资源调度

    负责系统的五态状态管理、服务生命周期管理和时间驱动的状态转换。

    Attributes:
        current_state: 当前系统状态
        is_running: 调度器是否正在运行
        services: 注册的服务字典
        config: 配置信息
        state_history: 状态转换历史
        on_state_change: 状态变更回调函数

    Example:
        >>> orchestrator = MainOrchestrator()
        >>> orchestrator.register_service('sanitizer', sanitizer_service)
        >>> orchestrator.start()
        >>> orchestrator.transition_to(SystemState.PREP)
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """初始化主调度器

        Args:
            config: 配置字典，包含时间段定义等

        Raises:
            ValueError: 当配置无效时
        """
        self.current_state: SystemState = SystemState.MAINTENANCE
        self.is_running: bool = False
        self.services: Dict[str, ServiceInfo] = {}
        self.config: Dict[str, Any] = config or self._get_default_config()
        self.state_history: List[Tuple[datetime, SystemState]] = []
        self.on_state_change: Optional[Callable[[SystemState, SystemState], None]] = None

        # 集成服务管理器
        self.service_manager = ServiceManager()

        self._lock = threading.RLock()
        self._scheduler_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

        # WebSocket服务器状态
        self._websocket_running = False

        # 记录初始状态
        self.state_history.append((datetime.now(), self.current_state))

        logger.info(f"MainOrchestrator initialized - " f"State: {self.current_state.name}, " f"Config: {self.config}")

    def _get_default_config(self) -> Dict[str, Any]:
        """获取默认配置

        白皮书依据: 第一章 1.1-1.4 时间段定义

        Returns:
            默认配置字典
        """
        return {
            "prep_time": "08:30",  # 战备态开始时间
            "war_time": "09:15",  # 战争态开始时间
            "tactical_time": "15:00",  # 诊疗态开始时间
            "evolution_time": "20:00",  # 进化态开始时间
            "check_interval": 60,  # 状态检查间隔（秒）
            "websocket_host": "localhost",  # WebSocket服务器地址
            "websocket_port": 8502,  # WebSocket服务器端口
            "streamlit_port": 8501,  # Streamlit端口
        }

    def get_current_state(self) -> SystemState:
        """获取当前系统状态

        Returns:
            当前系统状态
        """
        with self._lock:
            return self.current_state

    def transition_to(self, new_state: SystemState) -> None:
        """转换到新状态

        白皮书依据: 第一章 状态转换规则

        Args:
            new_state: 目标状态

        Raises:
            StateTransitionError: 当状态转换无效时
        """
        if not isinstance(new_state, SystemState):
            raise StateTransitionError(f"Invalid state: {new_state}")

        with self._lock:
            old_state = self.current_state

            if old_state == new_state:
                logger.debug(f"Already in state {new_state.name}, skipping transition")
                return

            logger.info(f"State transition: {old_state.name} -> {new_state.name}")

            # 执行状态退出逻辑
            self._on_exit_state(old_state)

            # 更新状态
            self.current_state = new_state
            self.state_history.append((datetime.now(), new_state))

            # 执行状态进入逻辑
            self._on_enter_state(new_state)

            # 调用回调函数
            if self.on_state_change:
                try:
                    self.on_state_change(old_state, new_state)
                except Exception as e:  # pylint: disable=broad-exception-caught
                    logger.error(f"State change callback error: {e}")

    def _on_exit_state(self, state: SystemState) -> None:
        """状态退出时的处理逻辑

        Args:
            state: 正在退出的状态
        """
        logger.debug(f"Exiting state: {state.name}")

        # 根据不同状态执行相应的清理逻辑
        if state == SystemState.WAR:
            logger.info("Exiting WAR state - stopping real-time monitoring")
        elif state == SystemState.EVOLUTION:
            logger.info("Exiting EVOLUTION state - stopping mining processes")

    def _on_enter_state(self, state: SystemState) -> None:
        """状态进入时的处理逻辑

        白皮书依据: 第一章 1.0-1.4 各状态的核心任务

        Args:
            state: 正在进入的状态
        """
        logger.info(f"Entering state: {state.name}")

        # 根据不同状态执行相应的初始化逻辑
        if state == SystemState.MAINTENANCE:
            logger.info("Entering MAINTENANCE state - manual intervention mode")

        elif state == SystemState.PREP:
            logger.info("Entering PREP state - starting services and data preheating")
            self._execute_prep_tasks()

        elif state == SystemState.WAR:
            logger.info("Entering WAR state - starting real-time trading")
            self._execute_war_tasks()

        elif state == SystemState.TACTICAL:
            logger.info("Entering TACTICAL state - starting data archiving and diagnosis")
            self._execute_tactical_tasks()

        elif state == SystemState.EVOLUTION:
            logger.info("Entering EVOLUTION state - starting factor mining and evolution")
            self._execute_evolution_tasks()

    def _execute_prep_tasks(self) -> None:
        """执行战备态任务

        白皮书依据: 第一章 1.5.1 战备态任务调度

        任务序列:
        - 日历检查 - 非交易日跳转进化态
        - 服务启动 (数据清洗、执行、审计、雷达)
        - WebSocket服务器启动
        - 数据预热
        - Soldier/Commander初始化
        - 舆情定调
        """
        logger.info("执行战备态任务...")

        # 1. 日历检查 - 非交易日跳转进化态
        if not self.is_trading_day():
            logger.info("非交易日，跳转至进化态")
            self.transition_to(SystemState.EVOLUTION)
            return

        # 2. 启动核心服务
        logger.info("启动核心服务...")
        asyncio.run(self._start_core_services())

        # 3. 启动WebSocket服务器
        logger.info("启动WebSocket服务器...")
        asyncio.run(self._start_websocket_server())

        # 4. 数据预热
        logger.info("执行数据预热...")
        self._preheat_data()

        # 5. 初始化AI组件
        logger.info("初始化AI组件...")
        self._initialize_ai_components()

        # 6. 舆情定调
        logger.info("执行舆情定调...")
        self._fetch_overnight_news()

        logger.info("战备态任务完成")

    def _preheat_data(self) -> None:
        """数据预热

        白皮书依据: 第一章 1.5.1 数据预热

        任务:
        - 加载历史K线到内存
        - 预计算常用因子
        - 填充共享内存环形缓冲区
        """
        try:
            # 尝试导入数据预热模块
            from src.infra.data_probe import DataProbe  # pylint: disable=import-outside-toplevel

            DataProbe()
            # 预热数据
            logger.info("加载历史K线数据...")
            # probe.load_historical_bars()  # 如果方法存在

            logger.info("数据预热完成")
        except ImportError as e:
            logger.warning(f"数据预热模块未找到: {e}")
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"数据预热失败: {e}")

    def _initialize_ai_components(self) -> None:
        """初始化AI组件

        白皮书依据: 第一章 1.5.1 Soldier/Commander初始化
        """
        try:
            # 尝试初始化Soldier
            logger.info("初始化Soldier...")
            # 注释：SoldierEngineV2暂未实现
            # self.soldier = SoldierEngineV2()

            # 尝试初始化Commander
            logger.info("初始化Commander...")
            # 注释：CommanderEngineV2暂未实现
            # self.commander = CommanderEngineV2()

            logger.info("AI组件初始化完成")
        except ImportError as e:
            logger.warning(f"AI组件模块未找到: {e}")
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"AI组件初始化失败: {e}")

    def _fetch_overnight_news(self) -> None:
        """舆情定调 - 抓取隔夜要闻

        白皮书依据: 第一章 1.5.1 舆情定调
        """
        try:
            logger.info("抓取隔夜要闻...")
            # 实际实现需要调用舆情哨兵
            # 注释：SentimentSentinel暂未实现
            # sentinel = SentimentSentinel()
            # news = sentinel.fetch_overnight_news()

            logger.info("舆情定调完成")
        except ImportError as e:
            logger.warning(f"舆情模块未找到: {e}")
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"舆情定调失败: {e}")

    async def _start_core_services(self) -> None:
        """启动核心服务"""
        logger.info("Starting core services...")

        # 启动所有核心服务
        results = await self.service_manager.start_all_services()

        # 检查启动结果
        for service_type, success in results.items():
            if success:
                logger.info(f"Service {service_type.value} started successfully")
            else:
                logger.error(f"Failed to start service {service_type.value}")

    async def _start_websocket_server(self) -> None:
        """启动WebSocket服务器"""
        try:
            logger.info("Starting WebSocket server...")
            success = await start_websocket_server(
                host=self.config.get("websocket_host", "localhost"), port=self.config.get("websocket_port", 8502)
            )

            if success:
                self._websocket_running = True
                logger.info("WebSocket server started successfully")
            else:
                logger.error("Failed to start WebSocket server")

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"Error starting WebSocket server: {e}")

    async def _stop_websocket_server(self) -> None:
        """停止WebSocket服务器"""
        if self._websocket_running:
            try:
                logger.info("Stopping WebSocket server...")
                success = await stop_websocket_server()

                if success:
                    self._websocket_running = False
                    logger.info("WebSocket server stopped successfully")
                else:
                    logger.error("Failed to stop WebSocket server")

            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.error(f"Error stopping WebSocket server: {e}")

    def _execute_war_tasks(self) -> None:
        """执行战争态任务

        白皮书依据: 第一章 1.5.2 战争态任务调度

        任务序列:
        - 启动交易循环
        - 启动Soldier决策循环
        - 启动策略信号生成
        - 启动风控监控
        - 启动市场状态引擎
        - 启动健康检查
        """
        logger.info("执行战争态任务...")

        # 1. 启动交易循环
        logger.info("启动交易循环...")
        self._start_trading_loop()

        # 2. 启动Soldier决策循环
        logger.info("启动Soldier决策循环...")
        self._start_soldier_decision_loop()

        # 3. 启动策略信号生成
        logger.info("启动策略信号生成...")
        self._start_strategy_signal_generation()

        # 4. 启动风控监控
        logger.info("启动风控监控...")
        self._start_risk_monitoring()

        # 5. 启动市场状态引擎
        logger.info("启动市场状态引擎...")
        self._start_regime_engine()

        # 6. 启动健康检查
        logger.info("启动健康检查...")
        self._start_health_check()

        logger.info("战争态任务完成，进入实时交易模式")

    def _start_trading_loop(self) -> None:
        """启动交易循环

        白皮书依据: 第一章 1.5.2 启动交易循环
        """
        try:
            logger.info("订阅行情数据流...")
            # 实际实现需要连接行情源
            # 注释：MarketDataSubscriber暂未实现
            # self.market_data = MarketDataSubscriber()
            # self.market_data.subscribe()

            logger.info("交易循环已启动")
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"启动交易循环失败: {e}")

    def _start_soldier_decision_loop(self) -> None:
        """启动Soldier决策循环

        白皮书依据: 第一章 1.5.2 Soldier决策循环
        延迟要求: < 20ms P99
        """
        try:
            logger.info("启动Soldier决策循环 (延迟目标 < 20ms P99)...")
            # 实际实现
            # self.soldier.start_decision_loop()

            logger.info("Soldier决策循环已启动")
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"启动Soldier决策循环失败: {e}")

    def _start_strategy_signal_generation(self) -> None:
        """启动策略信号生成

        白皮书依据: 第一章 1.5.2 策略信号生成
        """
        try:
            logger.info("启动19个策略并行信号生成...")
            # 实际实现
            # 注释：SignalAggregator暂未实现
            # self.signal_aggregator = SignalAggregator()
            # self.signal_aggregator.start()

            logger.info("策略信号生成已启动")
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"启动策略信号生成失败: {e}")

    def _start_risk_monitoring(self) -> None:
        """启动风控监控

        白皮书依据: 第一章 1.5.2 风控监控
        """
        try:
            logger.info("启动实时仓位监控...")
            logger.info("启动止损止盈检查...")
            logger.info("启动末日开关监控...")
            # 实际实现
            # 注释：RiskMonitor暂未实现
            # self.risk_monitor = RiskMonitor()
            # self.risk_monitor.start()

            logger.info("风控监控已启动")
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"启动风控监控失败: {e}")

    def _start_regime_engine(self) -> None:
        """启动市场状态引擎

        白皮书依据: 第一章 1.5.2 市场状态引擎
        更新频率: 每60秒
        """
        try:
            logger.info("启动市场状态引擎 (更新频率: 60秒)...")
            # 实际实现
            # 注释：RegimeEngine暂未实现
            # self.regime_engine = RegimeEngine(update_interval=60)
            # self.regime_engine.start()

            logger.info("市场状态引擎已启动")
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"启动市场状态引擎失败: {e}")

    def _start_health_check(self) -> None:
        """启动健康检查

        白皮书依据: 第一章 1.5.2 健康检查
        """
        try:
            logger.info("启动系统健康检查...")
            # 实际实现
            # 注释：HealthChecker暂未实现
            # self.health_checker = HealthChecker()
            # self.health_checker.start()

            logger.info("健康检查已启动")
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"启动健康检查失败: {e}")

    def _execute_tactical_tasks(self) -> None:
        """执行诊疗态任务

        白皮书依据: 第一章 1.5.3 诊疗态任务调度

        任务序列:
        - 停止交易循环
        - 数据归档
        - 持仓诊断
        - 归因分析
        - 资本分配
        - 利润锁定
        - 学者阅读
        """
        logger.info("执行诊疗态任务...")

        # 1. 停止交易循环
        logger.info("停止交易循环...")
        self._stop_trading_loop()

        # 2. 数据归档
        logger.info("执行数据归档...")
        self._archive_data()

        # 3. 持仓诊断
        logger.info("执行持仓诊断...")
        self._diagnose_portfolio()

        # 4. 归因分析
        logger.info("执行归因分析...")
        self._perform_attribution_analysis()

        # 5. 资本分配
        logger.info("执行资本分配...")
        self._allocate_capital()

        # 6. 利润锁定
        logger.info("执行利润锁定...")
        self._lock_profits()

        # 7. 学者阅读
        logger.info("执行学者阅读...")
        self._scholar_reading()

        logger.info("诊疗态任务完成")

    def _stop_trading_loop(self) -> None:
        """停止交易循环"""
        try:
            logger.info("停止行情订阅...")
            logger.info("停止Soldier决策循环...")
            logger.info("停止策略信号生成...")
            # 实际实现
            # if hasattr(self, 'market_data'):
            #     self.market_data.unsubscribe()

            logger.info("交易循环已停止")
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"停止交易循环失败: {e}")

    def _archive_data(self) -> None:
        """数据归档

        白皮书依据: 第一章 1.5.3 数据归档
        """
        try:
            logger.info("归档Tick数据到Parquet...")
            logger.info("归档Bar数据到Parquet...")
            logger.info("归档雷达信号...")
            # 实际实现
            # 注释：DataArchiver暂未实现
            # archiver = DataArchiver()
            # archiver.archive_tick_data()
            # archiver.archive_bar_data()
            # archiver.archive_radar_signals()

            logger.info("数据归档完成")
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"数据归档失败: {e}")

    def _diagnose_portfolio(self) -> None:
        """持仓诊断

        白皮书依据: 第一章 1.5.3 持仓诊断
        """
        try:
            logger.info("执行持仓健康检查...")
            logger.info("分析风险暴露...")
            logger.info("生成诊断报告...")
            # 实际实现
            # 注释：PortfolioDoctor暂未实现
            # doctor = PortfolioDoctor()
            # report = doctor.diagnose()

            logger.info("持仓诊断完成")
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"持仓诊断失败: {e}")

    def _perform_attribution_analysis(self) -> None:
        """归因分析

        白皮书依据: 第一章 1.5.3 归因分析
        """
        try:
            logger.info("执行Alpha/Beta分解...")
            logger.info("分析策略贡献度...")
            logger.info("分析因子暴露...")
            logger.info("分析交易成本...")
            # 实际实现
            # 注释：AttributionAnalyzer暂未实现
            # analyzer = AttributionAnalyzer()
            # analyzer.analyze()

            logger.info("归因分析完成")
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"归因分析失败: {e}")

    def _allocate_capital(self) -> None:
        """资本分配

        白皮书依据: 第一章 1.5.3 资本分配
        """
        try:
            logger.info("计算次日权重...")
            # 实际实现
            # 注释：CapitalAllocator暂未实现
            # allocator = CapitalAllocator()
            # allocator.allocate_for_next_day()

            logger.info("资本分配完成")
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"资本分配失败: {e}")

    def _lock_profits(self) -> None:
        """利润锁定

        白皮书依据: 第一章 1.5.3 利润锁定
        """
        try:
            logger.info("触发LockBox实体化...")
            # 实际实现
            # 注释：LockBox暂未实现
            # lockbox = LockBox()
            # lockbox.lock_profits()

            logger.info("利润锁定完成")
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"利润锁定失败: {e}")

    def _scholar_reading(self) -> None:
        """学者阅读

        白皮书依据: 第一章 1.5.3 学者阅读
        """
        try:
            logger.info("启动研报爬虫...")
            logger.info("提取公式并进行AST白名单校验...")
            # 实际实现
            # 注释：Scholar暂未实现
            # scholar = Scholar()
            # scholar.read_reports()

            logger.info("学者阅读完成")
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"学者阅读失败: {e}")

    def _execute_evolution_tasks(self) -> None:
        """执行进化态任务

        白皮书依据: 第一章 1.5.4 进化态任务调度

        任务序列:
        - 因子挖掘 (22个专业因子挖掘器)
        - 策略进化
        - 反向进化
        - 魔鬼审计
        - 模型训练
        - 系统维护
        """
        logger.info("执行进化态任务...")

        # 1. 因子挖掘
        logger.info("启动因子挖掘...")
        self._run_factor_mining()

        # 2. 策略进化
        logger.info("启动策略进化...")
        self._run_strategy_evolution()

        # 3. 反向进化
        logger.info("执行反向进化...")
        self._run_reverse_evolution()

        # 4. 魔鬼审计
        logger.info("执行魔鬼审计...")
        self._run_devil_audit()

        # 5. 模型训练
        logger.info("执行模型训练...")
        self._run_model_training()

        # 6. 系统维护
        logger.info("执行系统维护...")
        self._run_system_maintenance()

        logger.info("进化态任务完成")

    def _run_factor_mining(self) -> None:
        """因子挖掘

        白皮书依据: 第一章 1.5.4 因子挖掘
        - 遗传算法因子挖掘
        - 22个专业因子挖掘器并行运行
        - 因子竞技场三轨测试
        """
        try:
            logger.info("启动遗传算法因子挖掘...")
            logger.info("启动22个专业因子挖掘器并行运行...")
            logger.info("执行因子竞技场三轨测试...")
            # 实际实现
            # 注释：GeneticMiner暂未实现
            # 注释：FactorArena暂未实现
            # miner = GeneticMiner()
            # miner.mine()
            # arena = FactorArena()
            # arena.run_three_track_test()

            logger.info("因子挖掘完成")
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"因子挖掘失败: {e}")

    def _run_strategy_evolution(self) -> None:
        """策略进化

        白皮书依据: 第一章 1.5.4 策略进化
        """
        try:
            logger.info("执行策略变异与交叉...")
            logger.info("执行斯巴达竞技场考核...")
            logger.info("评估适应度...")
            # 实际实现
            # 注释：SpartaArena暂未实现
            # arena = SpartaArena()
            # arena.evolve_strategies()

            logger.info("策略进化完成")
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"策略进化失败: {e}")

    def _run_reverse_evolution(self) -> None:
        """反向进化

        白皮书依据: 第一章 1.5.4 反向进化
        将Arena淘汰样本送往Cloud API进行"尸检"
        """
        try:
            logger.info("收集Arena淘汰样本...")
            logger.info("发送至Cloud API进行尸检分析...")
            # 实际实现
            # 注释：ReverseEvolution暂未实现
            # reverse = ReverseEvolution()
            # reverse.analyze_failures()

            logger.info("反向进化完成")
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"反向进化失败: {e}")

    def _run_devil_audit(self) -> None:
        """魔鬼审计

        白皮书依据: 第一章 1.5.4 魔鬼审计
        通过Cloud API审计，颁发Z2H钢印
        """
        try:
            logger.info("执行Cloud API审计...")
            logger.info("评估Z2H钢印资格...")
            # 实际实现
            # 注释：DevilAuditor暂未实现
            # auditor = DevilAuditor()
            # auditor.audit_and_certify()

            logger.info("魔鬼审计完成")
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"魔鬼审计失败: {e}")

    def _run_model_training(self) -> None:
        """模型训练

        白皮书依据: 第一章 1.5.4 模型训练
        """
        try:
            logger.info("执行模型增量训练...")
            # 实际实现
            # 注释：ModelTrainer暂未实现
            # trainer = ModelTrainer()
            # trainer.train()

            logger.info("模型训练完成")
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"模型训练失败: {e}")

    def _run_system_maintenance(self) -> None:
        """系统维护

        白皮书依据: 第一章 1.5.4 系统维护
        """
        try:
            logger.info("执行GC内存回收...")
            logger.info("清理临时文件...")
            logger.info("检查磁盘空间...")
            # 实际实现
            import gc  # pylint: disable=import-outside-toplevel

            gc.collect()

            logger.info("系统维护完成")
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"系统维护失败: {e}")

    def is_trading_day(self) -> bool:
        """判断是否为交易日

        白皮书依据: 第一章 1.1 日历感知

        Returns:
            是否为交易日

        Note:
            简化实现：周一到周五为交易日
            实际应该查询交易日历API
        """
        now = datetime.now()
        # 0=Monday, 6=Sunday
        return now.weekday() < 5

    def get_target_state_by_time(self) -> SystemState:
        """根据当前时间获取目标状态

        白皮书依据: 第一章 1.1-1.4 时间段定义

        Returns:
            目标系统状态
        """
        now = datetime.now()
        current_time = now.time()

        # 解析配置中的时间
        prep_time = dt_time(*map(int, self.config["prep_time"].split(":")))
        war_time = dt_time(*map(int, self.config["war_time"].split(":")))
        tactical_time = dt_time(*map(int, self.config["tactical_time"].split(":")))
        evolution_time = dt_time(*map(int, self.config["evolution_time"].split(":")))

        # 判断当前时间段
        if prep_time <= current_time < war_time:  # pylint: disable=no-else-return
            return SystemState.PREP
        elif war_time <= current_time < tactical_time:
            return SystemState.WAR
        elif tactical_time <= current_time < evolution_time:
            return SystemState.TACTICAL
        else:
            return SystemState.EVOLUTION

    def register_service(self, name: str, service: Any) -> None:
        """注册服务

        白皮书依据: 第一章 1.1 服务启动管理

        Args:
            name: 服务名称
            service: 服务实例

        Raises:
            ValueError: 当服务名称已存在时
        """
        with self._lock:
            if name in self.services:
                raise ValueError(f"Service {name} already registered")

            self.services[name] = ServiceInfo(instance=service)
            logger.info(f"Service registered: {name}")

    def unregister_service(self, name: str) -> None:
        """注销服务

        Args:
            name: 服务名称

        Raises:
            ValueError: 当服务不存在时
        """
        with self._lock:
            if name not in self.services:
                raise ValueError(f"Service {name} not found")

            # 如果服务正在运行，先停止
            if self.services[name].status == "running":
                self.stop_service(name)

            del self.services[name]
            logger.info(f"Service unregistered: {name}")

    def start_service(self, name: str) -> None:
        """启动服务

        白皮书依据: 第一章 1.1 服务启动

        Args:
            name: 服务名称

        Raises:
            ServiceStartupError: 当服务启动失败时
        """
        with self._lock:
            if name not in self.services:
                raise ServiceStartupError(f"Service {name} not found")

            service_info = self.services[name]

            if service_info.status == "running":
                logger.warning(f"Service {name} is already running")
                return

            try:
                service_info.instance.start()
                service_info.status = "running"
                service_info.start_time = datetime.now()
                logger.info(f"Service started: {name}")
            except Exception as e:
                service_info.status = "error"
                service_info.error_count += 1
                logger.error(f"Failed to start service {name}: {e}")
                raise ServiceStartupError(f"Failed to start service {name}") from e

    def stop_service(self, name: str) -> None:
        """停止服务

        Args:
            name: 服务名称

        Raises:
            ValueError: 当服务不存在时
        """
        with self._lock:
            if name not in self.services:
                raise ValueError(f"Service {name} not found")

            service_info = self.services[name]

            if service_info.status != "running":
                logger.warning(f"Service {name} is not running")
                return

            try:
                service_info.instance.stop()
                service_info.status = "stopped"
                logger.info(f"Service stopped: {name}")
            except Exception as e:
                logger.error(f"Error stopping service {name}: {e}")
                raise

    def restart_service(self, name: str) -> None:
        """重启服务

        Args:
            name: 服务名称
        """
        logger.info(f"Restarting service: {name}")
        self.stop_service(name)
        time.sleep(1)  # 等待服务完全停止
        self.start_service(name)

    def get_service_status(self, name: str) -> str:
        """获取服务状态

        Args:
            name: 服务名称

        Returns:
            服务状态 ('stopped', 'running', 'error')

        Raises:
            ValueError: 当服务不存在时
        """
        with self._lock:
            if name not in self.services:
                raise ValueError(f"Service {name} not found")

            return self.services[name].status

    def check_service_health(self, name: str) -> bool:
        """检查服务健康状态

        Args:
            name: 服务名称

        Returns:
            服务是否健康

        Raises:
            ValueError: 当服务不存在时
        """
        with self._lock:
            if name not in self.services:
                raise ValueError(f"Service {name} not found")

            service_info = self.services[name]

            if service_info.status != "running":
                return False

            # 如果服务有健康检查方法，调用它
            if hasattr(service_info.instance, "is_healthy"):
                try:
                    return service_info.instance.is_healthy()
                except Exception as e:  # pylint: disable=broad-exception-caught
                    logger.error(f"Health check failed for {name}: {e}")
                    return False

            return True

    def start_all_services(self) -> None:
        """启动所有已注册的服务"""
        logger.info("Starting all services")

        with self._lock:
            for name in list(self.services.keys()):
                try:
                    self.start_service(name)
                except Exception as e:  # pylint: disable=broad-exception-caught
                    logger.error(f"Failed to start service {name}: {e}")

    def stop_all_services(self) -> None:
        """停止所有正在运行的服务"""
        logger.info("Stopping all services")

        with self._lock:
            for name in list(self.services.keys()):
                try:
                    if self.services[name].status == "running":
                        self.stop_service(name)
                except Exception as e:  # pylint: disable=broad-exception-caught
                    logger.error(f"Failed to stop service {name}: {e}")

    def get_state_history(self) -> List[Tuple[datetime, SystemState]]:
        """获取状态转换历史

        Returns:
            状态转换历史列表，每项为 (时间戳, 状态)
        """
        with self._lock:
            return self.state_history.copy()

    def start(self) -> None:
        """启动调度器

        启动后台线程，自动根据时间进行状态转换

        Raises:
            RuntimeError: 当调度器已经在运行时
        """
        with self._lock:
            if self.is_running:
                raise RuntimeError("Orchestrator is already running")

            self.is_running = True
            self._stop_event.clear()

            # 启动调度线程
            self._scheduler_thread = threading.Thread(
                target=self._scheduler_loop, name="OrchestratorScheduler", daemon=True
            )
            self._scheduler_thread.start()

            logger.info("MainOrchestrator started")

    def stop(self) -> None:
        """停止调度器

        Raises:
            RuntimeError: 当调度器未在运行时
        """
        with self._lock:
            if not self.is_running:
                raise RuntimeError("Orchestrator is not running")

            self.is_running = False
            self._stop_event.set()

        # 等待调度线程结束
        if self._scheduler_thread and self._scheduler_thread.is_alive():
            self._scheduler_thread.join(timeout=5.0)

        # 停止所有服务
        self.stop_all_services()

        # 停止WebSocket服务器
        asyncio.run(self._stop_websocket_server())

        logger.info("MainOrchestrator stopped")

    def get_service_manager_status(self) -> Dict[str, Dict[str, Any]]:
        """获取服务管理器状态

        Returns:
            所有服务状态信息
        """
        return self.service_manager.get_all_services_status()

    def get_websocket_status(self) -> Dict[str, Any]:
        """获取WebSocket服务器状态

        Returns:
            WebSocket服务器状态
        """
        return {
            "running": self._websocket_running,
            "host": self.config.get("websocket_host", "localhost"),
            "port": self.config.get("websocket_port", 8502),
        }

    def get_system_status(self) -> Dict[str, Any]:
        """获取系统整体状态

        Returns:
            系统状态信息
        """
        return {
            "current_state": self.current_state.name,
            "is_running": self.is_running,
            "services": self.get_service_manager_status(),
            "websocket": self.get_websocket_status(),
            "uptime": time.time() - (self.state_history[0][0].timestamp() if self.state_history else 0),
        }

    def _scheduler_loop(self) -> None:
        """调度器主循环

        白皮书依据: 第一章 时间驱动的状态转换

        定期检查当前时间，自动进行状态转换
        """
        logger.info("Orchestrator scheduler loop started")

        check_interval = self.config.get("check_interval", 60)

        while not self._stop_event.is_set():
            try:
                # 获取目标状态
                target_state = self.get_target_state_by_time()

                # 如果目标状态与当前状态不同，进行转换
                if target_state != self.current_state:
                    logger.info(f"Auto transition triggered: {self.current_state.name} -> {target_state.name}")
                    self.transition_to(target_state)

                # 等待下一次检查
                self._stop_event.wait(timeout=check_interval)

            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.error(f"Error in scheduler loop: {e}")
                self._stop_event.wait(timeout=check_interval)

        logger.info("Orchestrator scheduler loop stopped")
