"""
MIA系统斯巴达Arena压力测试标准

白皮书依据: 第四章 4.2 斯巴达竞技场 - 双轨压力测试
版本: v1.6.0
作者: MIA Team
日期: 2026-01-18

核心功能:
1. Reality Track - 真实历史数据压力测试
2. Hell Track - 极端行情模拟压力测试
3. 双轨综合评分算法
4. 压力测试通过标准
5. 策略生存能力评估
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import redis

from ..base.models import SimulationResult, Strategy
from ..utils.logger import get_logger

logger = get_logger(__name__)


class TrackType(Enum):
    """测试轨道类型"""

    REALITY = "reality"  # 真实历史数据轨道
    HELL = "hell"  # 极端行情模拟轨道


class MarketScenario(Enum):
    """市场场景类型"""

    # Reality Track 场景
    BULL_MARKET = "bull_market"  # 牛市行情
    BEAR_MARKET = "bear_market"  # 熊市行情
    SIDEWAYS_MARKET = "sideways_market"  # 震荡市行情
    VOLATILE_MARKET = "volatile_market"  # 高波动市场

    # Hell Track 场景
    FLASH_CRASH = "flash_crash"  # 闪崩场景
    CIRCUIT_BREAKER = "circuit_breaker"  # 熔断场景
    LIQUIDITY_CRISIS = "liquidity_crisis"  # 流动性枯竭
    BLACK_SWAN = "black_swan"  # 黑天鹅事件
    EXTREME_VOLATILITY = "extreme_vol"  # 极端波动


@dataclass
class ArenaTestConfig:
    """Arena测试配置"""

    track_type: TrackType
    scenario: MarketScenario
    test_duration_days: int
    initial_capital: float
    max_drawdown_threshold: float
    min_sharpe_threshold: float
    survival_rate_threshold: float
    stress_multiplier: float = 1.0


@dataclass
class ArenaTestResult:  # pylint: disable=too-many-instance-attributes
    """Arena测试结果"""

    strategy_id: str
    strategy_name: str
    track_type: TrackType
    scenario: MarketScenario
    test_date: datetime

    # 基础指标
    total_return: float
    annual_return: float
    sharpe_ratio: float
    max_drawdown: float
    volatility: float
    win_rate: float

    # 压力测试特有指标
    survival_rate: float  # 生存率 (未爆仓的时间比例)
    recovery_factor: float  # 恢复因子 (从最大回撤恢复的能力)
    stress_resistance: float  # 抗压能力 (极端情况下的表现)
    adaptation_speed: float  # 适应速度 (对市场变化的反应)

    # 通过状态
    passed: bool
    pass_score: float
    failure_reasons: List[str]

    # 详细数据
    daily_returns: List[float]
    drawdown_series: List[float]
    position_data: Optional[Dict[str, Any]] = None


class SpartaArenaStandards:
    """斯巴达Arena压力测试标准

    白皮书依据: 第四章 4.2 斯巴达竞技场

    核心理念: 双轨压力测试，全面评估策略在不同市场环境下的表现

    测试轨道:
    1. Reality Track - 使用真实历史数据测试策略的实际表现
    2. Hell Track - 使用极端模拟场景测试策略的抗压能力

    评分体系:
    - 基础指标 (40%): 收益、夏普、回撤、胜率
    - 压力指标 (40%): 生存率、恢复因子、抗压能力
    - 稳定性指标 (20%): 适应速度、表现一致性
    """

    def __init__(self, redis_client: Optional[redis.Redis] = None):
        """初始化斯巴达Arena测试标准

        Args:
            redis_client: Redis客户端，用于缓存测试数据
        """
        self.redis_client = redis_client or redis.Redis(host="localhost", port=6379, db=0)

        # 测试配置
        self.test_configs = self._initialize_test_configs()

        # 通过标准
        self.pass_standards = self._initialize_pass_standards()

        # 评分权重
        self.scoring_weights = {
            "basic_metrics": 0.40,  # 基础指标权重40%
            "stress_metrics": 0.40,  # 压力指标权重40%
            "stability_metrics": 0.20,  # 稳定性指标权重20%
        }

        logger.info("SpartaArenaStandards 初始化完成")
        logger.info("双轨压力测试: Reality Track + Hell Track")

    def _initialize_test_configs(self) -> Dict[TrackType, Dict[MarketScenario, ArenaTestConfig]]:
        """初始化测试配置

        Returns:
            测试配置字典
        """
        return {
            # Reality Track - 真实历史数据测试
            TrackType.REALITY: {
                MarketScenario.BULL_MARKET: ArenaTestConfig(
                    track_type=TrackType.REALITY,
                    scenario=MarketScenario.BULL_MARKET,
                    test_duration_days=252,  # 1年牛市数据
                    initial_capital=100000.0,
                    max_drawdown_threshold=0.15,  # 最大回撤15%
                    min_sharpe_threshold=1.5,  # 最低夏普1.5
                    survival_rate_threshold=0.95,  # 生存率95%
                    stress_multiplier=1.0,
                ),
                MarketScenario.BEAR_MARKET: ArenaTestConfig(
                    track_type=TrackType.REALITY,
                    scenario=MarketScenario.BEAR_MARKET,
                    test_duration_days=252,  # 1年熊市数据
                    initial_capital=100000.0,
                    max_drawdown_threshold=0.25,  # 熊市允许更大回撤
                    min_sharpe_threshold=0.8,  # 熊市降低夏普要求
                    survival_rate_threshold=0.90,  # 生存率90%
                    stress_multiplier=1.2,
                ),
                MarketScenario.SIDEWAYS_MARKET: ArenaTestConfig(
                    track_type=TrackType.REALITY,
                    scenario=MarketScenario.SIDEWAYS_MARKET,
                    test_duration_days=252,  # 1年震荡市数据
                    initial_capital=100000.0,
                    max_drawdown_threshold=0.12,  # 震荡市严格控制回撤
                    min_sharpe_threshold=1.2,  # 中等夏普要求
                    survival_rate_threshold=0.92,  # 生存率92%
                    stress_multiplier=1.1,
                ),
                MarketScenario.VOLATILE_MARKET: ArenaTestConfig(
                    track_type=TrackType.REALITY,
                    scenario=MarketScenario.VOLATILE_MARKET,
                    test_duration_days=126,  # 半年高波动数据
                    initial_capital=100000.0,
                    max_drawdown_threshold=0.20,  # 高波动允许较大回撤
                    min_sharpe_threshold=1.0,  # 降低夏普要求
                    survival_rate_threshold=0.85,  # 生存率85%
                    stress_multiplier=1.5,
                ),
            },
            # Hell Track - 极端场景模拟测试
            TrackType.HELL: {
                MarketScenario.FLASH_CRASH: ArenaTestConfig(
                    track_type=TrackType.HELL,
                    scenario=MarketScenario.FLASH_CRASH,
                    test_duration_days=5,  # 5天闪崩测试
                    initial_capital=100000.0,
                    max_drawdown_threshold=0.30,  # 极端情况允许30%回撤
                    min_sharpe_threshold=0.0,  # 不要求正夏普
                    survival_rate_threshold=0.70,  # 生存率70%
                    stress_multiplier=3.0,  # 3倍压力
                ),
                MarketScenario.CIRCUIT_BREAKER: ArenaTestConfig(
                    track_type=TrackType.HELL,
                    scenario=MarketScenario.CIRCUIT_BREAKER,
                    test_duration_days=10,  # 10天熔断测试
                    initial_capital=100000.0,
                    max_drawdown_threshold=0.25,  # 熔断情况25%回撤
                    min_sharpe_threshold=0.0,
                    survival_rate_threshold=0.75,  # 生存率75%
                    stress_multiplier=2.5,
                ),
                MarketScenario.LIQUIDITY_CRISIS: ArenaTestConfig(
                    track_type=TrackType.HELL,
                    scenario=MarketScenario.LIQUIDITY_CRISIS,
                    test_duration_days=21,  # 21天流动性危机
                    initial_capital=100000.0,
                    max_drawdown_threshold=0.35,  # 流动性危机35%回撤
                    min_sharpe_threshold=-0.5,  # 允许负夏普
                    survival_rate_threshold=0.65,  # 生存率65%
                    stress_multiplier=2.8,
                ),
                MarketScenario.BLACK_SWAN: ArenaTestConfig(
                    track_type=TrackType.HELL,
                    scenario=MarketScenario.BLACK_SWAN,
                    test_duration_days=30,  # 30天黑天鹅事件
                    initial_capital=100000.0,
                    max_drawdown_threshold=0.40,  # 黑天鹅40%回撤
                    min_sharpe_threshold=-1.0,  # 允许大幅负夏普
                    survival_rate_threshold=0.60,  # 生存率60%
                    stress_multiplier=4.0,  # 4倍压力
                ),
                MarketScenario.EXTREME_VOLATILITY: ArenaTestConfig(
                    track_type=TrackType.HELL,
                    scenario=MarketScenario.EXTREME_VOLATILITY,
                    test_duration_days=63,  # 3个月极端波动
                    initial_capital=100000.0,
                    max_drawdown_threshold=0.45,  # 极端波动45%回撤
                    min_sharpe_threshold=-0.8,  # 允许负夏普
                    survival_rate_threshold=0.55,  # 生存率55%
                    stress_multiplier=3.5,
                ),
            },
        }

    def _initialize_pass_standards(self) -> Dict[str, Dict[str, float]]:
        """初始化通过标准

        Returns:
            通过标准字典
        """
        return {
            # Reality Track 通过标准
            "reality_track": {
                "min_overall_score": 0.60,  # 总分60%以上
                "min_basic_score": 0.50,  # 基础指标50%以上
                "min_stress_score": 0.40,  # 压力指标40%以上
                "min_stability_score": 0.50,  # 稳定性指标50%以上
                "max_failure_scenarios": 1,  # 最多1个场景失败
                "min_survival_rate": 0.85,  # 最低生存率85%
            },
            # Hell Track 通过标准
            "hell_track": {
                "min_overall_score": 0.40,  # 总分40%以上 (Hell Track更宽松)
                "min_basic_score": 0.30,  # 基础指标30%以上
                "min_stress_score": 0.35,  # 压力指标35%以上
                "min_stability_score": 0.30,  # 稳定性指标30%以上
                "max_failure_scenarios": 2,  # 最多2个场景失败
                "min_survival_rate": 0.60,  # 最低生存率60%
            },
            # 综合通过标准
            "combined": {
                "min_reality_score": 0.60,  # Reality Track最低60%
                "min_hell_score": 0.40,  # Hell Track最低40%
                "min_combined_score": 0.50,  # 综合最低50%
                "reality_weight": 0.70,  # Reality Track权重70%
                "hell_weight": 0.30,  # Hell Track权重30%
            },
        }

    async def run_arena_test(
        self, strategy: Strategy, track_type: TrackType, scenarios: Optional[List[MarketScenario]] = None
    ) -> Dict[MarketScenario, ArenaTestResult]:
        """运行Arena压力测试

        Args:
            strategy: 待测试策略
            track_type: 测试轨道类型
            scenarios: 测试场景列表 (None表示测试所有场景)

        Returns:
            测试结果字典 {scenario: result}
        """
        logger.info(  # pylint: disable=logging-fstring-interpolation
            f"开始 {track_type.value} 轨道测试: {strategy.name}"
        )  # pylint: disable=logging-fstring-interpolation

        # 确定测试场景
        if scenarios is None:
            scenarios = list(self.test_configs[track_type].keys())

        results = {}

        for scenario in scenarios:
            logger.info(f"测试场景: {scenario.value}")  # pylint: disable=logging-fstring-interpolation

            try:
                result = await self._run_single_scenario_test(strategy, track_type, scenario)
                results[scenario] = result

                logger.info(  # pylint: disable=logging-fstring-interpolation
                    f"场景 {scenario.value} 测试完成: {'通过' if result.passed else '失败'}"
                )  # pylint: disable=logging-fstring-interpolation

            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.error(f"场景 {scenario.value} 测试失败: {e}")  # pylint: disable=logging-fstring-interpolation

                # 创建失败结果
                self.test_configs[track_type][scenario]  # pylint: disable=w0104
                results[scenario] = ArenaTestResult(
                    strategy_id=strategy.strategy_id,
                    strategy_name=strategy.name,
                    track_type=track_type,
                    scenario=scenario,
                    test_date=datetime.now(),
                    total_return=-1.0,
                    annual_return=-1.0,
                    sharpe_ratio=-10.0,
                    max_drawdown=1.0,
                    volatility=1.0,
                    win_rate=0.0,
                    survival_rate=0.0,
                    recovery_factor=0.0,
                    stress_resistance=0.0,
                    adaptation_speed=0.0,
                    passed=False,
                    pass_score=0.0,
                    failure_reasons=[f"测试执行失败: {str(e)}"],
                    daily_returns=[],
                    drawdown_series=[],
                )

        logger.info(  # pylint: disable=logging-fstring-interpolation
            f"{track_type.value} 轨道测试完成，共测试 {len(results)} 个场景"
        )  # pylint: disable=logging-fstring-interpolation
        return results

    async def _run_single_scenario_test(
        self, strategy: Strategy, track_type: TrackType, scenario: MarketScenario
    ) -> ArenaTestResult:
        """运行单个场景测试

        Args:
            strategy: 待测试策略
            track_type: 测试轨道类型
            scenario: 测试场景

        Returns:
            测试结果
        """
        config = self.test_configs[track_type][scenario]

        # 1. 生成测试数据
        test_data = await self._generate_test_data(track_type, scenario, config)

        # 2. 运行策略回测
        simulation_result = await self._run_strategy_simulation(strategy, test_data, config)

        # 3. 计算压力测试指标
        stress_metrics = self._calculate_stress_metrics(simulation_result, config)

        # 4. 评估通过状态
        passed, pass_score, failure_reasons = self._evaluate_pass_status(simulation_result, stress_metrics, config)

        # 5. 构建测试结果
        result = ArenaTestResult(
            strategy_id=strategy.strategy_id,
            strategy_name=strategy.name,
            track_type=track_type,
            scenario=scenario,
            test_date=datetime.now(),
            # 基础指标
            total_return=simulation_result.total_return,
            annual_return=simulation_result.annual_return,
            sharpe_ratio=simulation_result.sharpe_ratio,
            max_drawdown=simulation_result.max_drawdown,
            volatility=simulation_result.volatility,
            win_rate=simulation_result.win_rate,
            # 压力测试指标
            survival_rate=stress_metrics["survival_rate"],
            recovery_factor=stress_metrics["recovery_factor"],
            stress_resistance=stress_metrics["stress_resistance"],
            adaptation_speed=stress_metrics["adaptation_speed"],
            # 通过状态
            passed=passed,
            pass_score=pass_score,
            failure_reasons=failure_reasons,
            # 详细数据
            daily_returns=simulation_result.daily_returns,
            drawdown_series=stress_metrics["drawdown_series"],
        )

        return result

    async def _generate_test_data(
        self, track_type: TrackType, scenario: MarketScenario, config: ArenaTestConfig
    ) -> pd.DataFrame:
        """生成测试数据

        Args:
            track_type: 测试轨道类型
            scenario: 测试场景
            config: 测试配置

        Returns:
            测试数据DataFrame
        """
        logger.debug(  # pylint: disable=logging-fstring-interpolation
            f"生成 {track_type.value} - {scenario.value} 测试数据"
        )  # pylint: disable=logging-fstring-interpolation

        if track_type == TrackType.REALITY:  # pylint: disable=no-else-return
            return await self._generate_reality_data(scenario, config)
        else:
            return await self._generate_hell_data(scenario, config)

    async def _generate_reality_data(self, scenario: MarketScenario, config: ArenaTestConfig) -> pd.DataFrame:
        """生成Reality Track真实历史数据

        Args:
            scenario: 市场场景
            config: 测试配置

        Returns:
            历史数据DataFrame
        """
        # 这里应该从真实数据源获取历史数据
        # 暂时使用模拟数据，但保持真实市场特征

        days = config.test_duration_days
        dates = pd.date_range(start="2023-01-01", periods=days, freq="D")

        # 根据场景设置不同的市场特征
        if scenario == MarketScenario.BULL_MARKET:
            daily_return_mean = 0.0008  # 牛市日均收益0.08%
            daily_volatility = 0.015  # 日波动率1.5%
            trend_factor = 1.2  # 上升趋势

        elif scenario == MarketScenario.BEAR_MARKET:
            daily_return_mean = -0.0005  # 熊市日均收益-0.05%
            daily_volatility = 0.025  # 日波动率2.5%
            trend_factor = 0.8  # 下降趋势

        elif scenario == MarketScenario.SIDEWAYS_MARKET:
            daily_return_mean = 0.0001  # 震荡市日均收益0.01%
            daily_volatility = 0.018  # 日波动率1.8%
            trend_factor = 1.0  # 无明显趋势

        else:  # VOLATILE_MARKET
            daily_return_mean = 0.0003  # 高波动日均收益0.03%
            daily_volatility = 0.035  # 日波动率3.5%
            trend_factor = 1.1  # 轻微上升

        # 生成价格序列
        np.random.seed(hash(scenario.value) % 2**32)  # 固定种子确保可重复

        returns = np.random.normal(daily_return_mean, daily_volatility, days)

        # 添加趋势和聚类效应
        for i in range(1, len(returns)):
            returns[i] += returns[i - 1] * 0.1 * trend_factor  # 趋势延续
            if abs(returns[i - 1]) > daily_volatility * 2:  # 极端值聚类
                returns[i] += returns[i - 1] * 0.3

        # 计算价格
        prices = 100 * np.cumprod(1 + returns)

        # 构建DataFrame
        data = pd.DataFrame(
            {"date": dates, "close": prices, "returns": returns, "volume": np.random.lognormal(15, 0.5, days)}  # 成交量
        )

        # 添加OHLC数据
        data["high"] = data["close"] * (1 + np.abs(np.random.normal(0, 0.01, days)))
        data["low"] = data["close"] * (1 - np.abs(np.random.normal(0, 0.01, days)))
        data["open"] = data["close"].shift(1).fillna(data["close"].iloc[0])

        logger.debug(  # pylint: disable=logging-fstring-interpolation
            f"Reality数据生成完成: {len(data)}天, 场景={scenario.value}"
        )  # pylint: disable=logging-fstring-interpolation
        return data

    async def _generate_hell_data(self, scenario: MarketScenario, config: ArenaTestConfig) -> pd.DataFrame:
        """生成Hell Track极端场景数据

        Args:
            scenario: 极端场景
            config: 测试配置

        Returns:
            极端场景数据DataFrame
        """
        days = config.test_duration_days
        dates = pd.date_range(start="2023-01-01", periods=days, freq="D")

        np.random.seed(hash(scenario.value) % 2**32)

        if scenario == MarketScenario.FLASH_CRASH:
            # 闪崩: 第2-3天暴跌，然后缓慢恢复
            returns = np.random.normal(0.0001, 0.01, days)
            returns[1] = -0.15  # 第2天跌15%
            returns[2] = -0.08  # 第3天跌8%
            returns[3:] = np.random.normal(0.002, 0.02, days - 3)  # 后续恢复

        elif scenario == MarketScenario.CIRCUIT_BREAKER:
            # 熔断: 连续几天大幅波动，触发熔断
            returns = np.random.normal(0, 0.02, days)
            for i in range(1, min(5, days)):
                returns[i] = np.random.choice([-0.10, 0.10])  # 连续涨跌停

        elif scenario == MarketScenario.LIQUIDITY_CRISIS:
            # 流动性危机: 持续下跌，波动率逐渐增大
            base_return = -0.002
            base_vol = 0.015
            returns = []
            for i in range(days):
                vol = base_vol * (1 + i * 0.05)  # 波动率递增
                ret = np.random.normal(base_return, vol)
                returns.append(ret)
            returns = np.array(returns)

        elif scenario == MarketScenario.BLACK_SWAN:
            # 黑天鹅: 随机极端事件
            returns = np.random.normal(0, 0.02, days)
            # 随机插入极端事件
            extreme_days = np.random.choice(days, size=3, replace=False)
            for day in extreme_days:
                returns[day] = np.random.choice([-0.20, -0.15, 0.15])

        else:  # EXTREME_VOLATILITY
            # 极端波动: 高波动率，频繁大幅波动
            returns = np.random.normal(0, 0.05, days)
            # 增加极端值频率
            for i in range(days):
                if np.random.random() < 0.2:  # 20%概率极端波动
                    returns[i] *= 3

        # 计算价格
        prices = 100 * np.cumprod(1 + returns)

        # 构建DataFrame
        data = pd.DataFrame(
            {
                "date": dates,
                "close": prices,
                "returns": returns,
                "volume": np.random.lognormal(15, 1.0, days),  # 极端情况下成交量更不稳定
            }
        )

        # 添加OHLC数据
        data["high"] = data["close"] * (1 + np.abs(np.random.normal(0, 0.02, days)))
        data["low"] = data["close"] * (1 - np.abs(np.random.normal(0, 0.02, days)))
        data["open"] = data["close"].shift(1).fillna(data["close"].iloc[0])

        logger.debug(  # pylint: disable=logging-fstring-interpolation
            f"Hell数据生成完成: {len(data)}天, 场景={scenario.value}"
        )  # pylint: disable=logging-fstring-interpolation
        return data

    async def _run_strategy_simulation(
        self, strategy: Strategy, test_data: pd.DataFrame, config: ArenaTestConfig
    ) -> SimulationResult:
        """运行策略模拟

        Args:
            strategy: 策略对象
            test_data: 测试数据
            config: 测试配置

        Returns:
            模拟结果
        """
        # 这里应该调用真实的策略回测引擎
        # 暂时使用简化的模拟逻辑

        returns = test_data["returns"].values
        prices = test_data["close"].values

        # 简化的策略模拟 (实际应该根据策略类型实现)
        strategy_returns = []
        positions = []

        for i in range(len(returns)):  # pylint: disable=consider-using-enumerate
            # 简化的信号生成逻辑
            if i == 0:
                position = 0.5  # 初始仓位50%
            else:
                # 基于价格动量的简单策略
                momentum = (prices[i] - prices[max(0, i - 5)]) / prices[max(0, i - 5)]
                if momentum > 0.02:
                    position = min(1.0, position + 0.1)  # 增仓
                elif momentum < -0.02:
                    position = max(0.0, position - 0.1)  # 减仓
                else:
                    position = position  # 保持  # pylint: disable=w0127

            positions.append(position)

            # 计算策略收益
            strategy_return = returns[i] * position
            strategy_returns.append(strategy_return)

        strategy_returns = np.array(strategy_returns)

        # 计算绩效指标
        total_return = np.prod(1 + strategy_returns) - 1
        annual_return = (1 + total_return) ** (252 / len(strategy_returns)) - 1
        volatility = np.std(strategy_returns) * np.sqrt(252)
        sharpe_ratio = annual_return / volatility if volatility > 0 else 0

        # 计算回撤
        cumulative_returns = np.cumprod(1 + strategy_returns)
        peak = np.maximum.accumulate(cumulative_returns)
        drawdown = (cumulative_returns - peak) / peak
        max_drawdown = abs(np.min(drawdown))

        # 计算胜率
        win_rate = np.sum(strategy_returns > 0) / len(strategy_returns)

        # 构建模拟结果
        result = SimulationResult(
            strategy_id=strategy.strategy_id,
            start_date=test_data["date"].iloc[0],
            end_date=test_data["date"].iloc[-1],
            initial_capital=config.initial_capital,
            final_capital=config.initial_capital * (1 + total_return),
            total_return=total_return,
            annual_return=annual_return,
            sharpe_ratio=sharpe_ratio,
            max_drawdown=max_drawdown,
            volatility=volatility,
            win_rate=win_rate,
            daily_returns=strategy_returns.tolist(),
            calmar_ratio=annual_return / max_drawdown if max_drawdown > 0 else 0,
        )

        return result

    def _calculate_stress_metrics(
        self, simulation_result: SimulationResult, config: ArenaTestConfig  # pylint: disable=unused-argument
    ) -> Dict[str, Any]:  # pylint: disable=unused-argument
        """计算压力测试指标

        Args:
            simulation_result: 模拟结果
            config: 测试配置

        Returns:
            压力测试指标字典
        """
        daily_returns = np.array(simulation_result.daily_returns)

        # 1. 生存率 (未爆仓的时间比例)
        cumulative_returns = np.cumprod(1 + daily_returns)
        survival_mask = cumulative_returns > 0.5  # 假设50%亏损为爆仓线
        survival_rate = np.sum(survival_mask) / len(survival_mask)

        # 2. 恢复因子 (从最大回撤恢复的能力)
        peak = np.maximum.accumulate(cumulative_returns)
        drawdown = (cumulative_returns - peak) / peak

        # 找到最大回撤点
        max_dd_idx = np.argmin(drawdown)
        if max_dd_idx < len(drawdown) - 1:
            # 计算从最大回撤点到结束的恢复程度
            recovery = (cumulative_returns[-1] - cumulative_returns[max_dd_idx]) / abs(drawdown[max_dd_idx])
            recovery_factor = max(0, min(2, recovery))  # 限制在[0, 2]范围
        else:
            recovery_factor = 0.0

        # 3. 抗压能力 (极端情况下的表现)
        # 计算极端收益日的表现
        extreme_threshold = np.percentile(np.abs(daily_returns), 95)  # 95%分位数
        extreme_days = np.abs(daily_returns) > extreme_threshold

        if np.sum(extreme_days) > 0:
            extreme_returns = daily_returns[extreme_days]
            avg_extreme_return = np.mean(extreme_returns)
            # 抗压能力 = 1 - (极端日平均亏损 / 极端阈值)
            stress_resistance = max(0, 1 + avg_extreme_return / extreme_threshold)
        else:
            stress_resistance = 1.0

        # 4. 适应速度 (对市场变化的反应速度)
        # 计算收益序列的自相关性，低自相关表示快速适应
        if len(daily_returns) > 1:
            autocorr = np.corrcoef(daily_returns[:-1], daily_returns[1:])[0, 1]
            adaptation_speed = max(0, 1 - abs(autocorr))  # 自相关越低，适应越快
        else:
            adaptation_speed = 0.5

        return {
            "survival_rate": survival_rate,
            "recovery_factor": recovery_factor,
            "stress_resistance": stress_resistance,
            "adaptation_speed": adaptation_speed,
            "drawdown_series": drawdown.tolist(),
        }

    def _evaluate_pass_status(  # pylint: disable=too-many-branches
        self, simulation_result: SimulationResult, stress_metrics: Dict[str, Any], config: ArenaTestConfig
    ) -> Tuple[bool, float, List[str]]:
        """评估通过状态

        Args:
            simulation_result: 模拟结果
            stress_metrics: 压力测试指标
            config: 测试配置

        Returns:
            (是否通过, 通过评分, 失败原因列表)
        """
        failure_reasons = []

        # 1. 基础指标检查
        basic_score = 0.0
        basic_checks = 0

        # 夏普比率检查
        if simulation_result.sharpe_ratio >= config.min_sharpe_threshold:
            basic_score += 0.25
        else:
            failure_reasons.append(
                f"夏普比率不达标: {simulation_result.sharpe_ratio:.2f} < {config.min_sharpe_threshold}"
            )
        basic_checks += 1

        # 最大回撤检查
        if simulation_result.max_drawdown <= config.max_drawdown_threshold:
            basic_score += 0.25
        else:
            failure_reasons.append(
                f"最大回撤超标: {simulation_result.max_drawdown:.1%} > {config.max_drawdown_threshold:.1%}"
            )
        basic_checks += 1

        # 收益检查 (Hell Track可以为负)
        if config.track_type == TrackType.REALITY:
            if simulation_result.total_return > 0:
                basic_score += 0.25
            else:
                failure_reasons.append(f"总收益为负: {simulation_result.total_return:.1%}")
        else:  # Hell Track
            if simulation_result.total_return > -0.5:  # 不超过50%亏损
                basic_score += 0.25
            else:
                failure_reasons.append(f"亏损过大: {simulation_result.total_return:.1%} < -50%")
        basic_checks += 1

        # 胜率检查
        min_win_rate = 0.45 if config.track_type == TrackType.REALITY else 0.30
        if simulation_result.win_rate >= min_win_rate:
            basic_score += 0.25
        else:
            failure_reasons.append(f"胜率不达标: {simulation_result.win_rate:.1%} < {min_win_rate:.1%}")
        basic_checks += 1

        # 2. 压力指标检查
        stress_score = 0.0

        # 生存率检查
        if stress_metrics["survival_rate"] >= config.survival_rate_threshold:
            stress_score += 0.4
        else:
            failure_reasons.append(
                f"生存率不达标: {stress_metrics['survival_rate']:.1%} < {config.survival_rate_threshold:.1%}"
            )

        # 恢复因子检查
        min_recovery = 0.5 if config.track_type == TrackType.REALITY else 0.2
        if stress_metrics["recovery_factor"] >= min_recovery:
            stress_score += 0.3
        else:
            failure_reasons.append(f"恢复因子不达标: {stress_metrics['recovery_factor']:.2f} < {min_recovery}")

        # 抗压能力检查
        min_resistance = 0.6 if config.track_type == TrackType.REALITY else 0.3
        if stress_metrics["stress_resistance"] >= min_resistance:
            stress_score += 0.3
        else:
            failure_reasons.append(f"抗压能力不达标: {stress_metrics['stress_resistance']:.2f} < {min_resistance}")

        # 3. 稳定性指标检查
        stability_score = 0.0

        # 适应速度检查
        if stress_metrics["adaptation_speed"] >= 0.4:
            stability_score += 0.5
        else:
            failure_reasons.append(f"适应速度不达标: {stress_metrics['adaptation_speed']:.2f} < 0.4")

        # 波动率检查
        max_vol = 0.3 if config.track_type == TrackType.REALITY else 0.5
        if simulation_result.volatility <= max_vol:
            stability_score += 0.5
        else:
            failure_reasons.append(f"波动率过高: {simulation_result.volatility:.1%} > {max_vol:.1%}")

        # 4. 计算综合评分
        weights = self.scoring_weights
        overall_score = (
            basic_score * weights["basic_metrics"]
            + stress_score * weights["stress_metrics"]
            + stability_score * weights["stability_metrics"]
        )

        # 5. 判断是否通过
        track_standards = self.pass_standards[f"{config.track_type.value}_track"]

        passed = bool(
            overall_score >= track_standards["min_overall_score"]
            and basic_score >= track_standards["min_basic_score"]
            and stress_score >= track_standards["min_stress_score"]
            and stability_score >= track_standards["min_stability_score"]
            and stress_metrics["survival_rate"] >= track_standards["min_survival_rate"]
        )

        logger.debug(  # pylint: disable=logging-fstring-interpolation
            f"评估结果: 通过={passed}, 评分={overall_score:.2f}, 失败原因={len(failure_reasons)}个"
        )  # pylint: disable=logging-fstring-interpolation

        return passed, overall_score, failure_reasons

    def calculate_combined_arena_score(
        self,
        reality_results: Dict[MarketScenario, ArenaTestResult],
        hell_results: Dict[MarketScenario, ArenaTestResult],
    ) -> Dict[str, Any]:
        """计算Arena综合评分

        Args:
            reality_results: Reality Track测试结果
            hell_results: Hell Track测试结果

        Returns:
            综合评分结果
        """
        logger.info("计算Arena综合评分")

        # 1. 计算Reality Track平均分
        reality_scores = [result.pass_score for result in reality_results.values()]
        reality_avg_score = np.mean(reality_scores) if reality_scores else 0.0
        reality_pass_count = sum(1 for result in reality_results.values() if result.passed)

        # 2. 计算Hell Track平均分
        hell_scores = [result.pass_score for result in hell_results.values()]
        hell_avg_score = np.mean(hell_scores) if hell_scores else 0.0
        hell_pass_count = sum(1 for result in hell_results.values() if result.passed)

        # 3. 计算综合评分
        combined_standards = self.pass_standards["combined"]
        reality_weight = combined_standards["reality_weight"]
        hell_weight = combined_standards["hell_weight"]

        combined_score = reality_avg_score * reality_weight + hell_avg_score * hell_weight

        # 4. 判断综合通过状态
        combined_passed = (
            reality_avg_score >= combined_standards["min_reality_score"]
            and hell_avg_score >= combined_standards["min_hell_score"]
            and combined_score >= combined_standards["min_combined_score"]
            and reality_pass_count
            >= len(reality_results) - self.pass_standards["reality_track"]["max_failure_scenarios"]
            and hell_pass_count >= len(hell_results) - self.pass_standards["hell_track"]["max_failure_scenarios"]
        )

        # 5. 生成评级
        if combined_score >= 0.85:
            grade = "A+"
        elif combined_score >= 0.75:
            grade = "A"
        elif combined_score >= 0.65:
            grade = "B+"
        elif combined_score >= 0.55:
            grade = "B"
        elif combined_score >= 0.45:
            grade = "C+"
        elif combined_score >= 0.35:
            grade = "C"
        else:
            grade = "D"

        result = {
            "combined_passed": combined_passed,
            "combined_score": combined_score,
            "grade": grade,
            "reality_track": {
                "avg_score": reality_avg_score,
                "pass_count": reality_pass_count,
                "total_scenarios": len(reality_results),
                "pass_rate": reality_pass_count / len(reality_results) if reality_results else 0,
            },
            "hell_track": {
                "avg_score": hell_avg_score,
                "pass_count": hell_pass_count,
                "total_scenarios": len(hell_results),
                "pass_rate": hell_pass_count / len(hell_results) if hell_results else 0,
            },
            "summary": {
                "total_scenarios": len(reality_results) + len(hell_results),
                "total_passed": reality_pass_count + hell_pass_count,
                "overall_pass_rate": (
                    (reality_pass_count + hell_pass_count) / (len(reality_results) + len(hell_results))
                    if (reality_results or hell_results)
                    else 0
                ),
            },
        }

        logger.info(  # pylint: disable=logging-fstring-interpolation
            f"Arena综合评分完成: {grade} ({combined_score:.2f})"
        )  # pylint: disable=logging-fstring-interpolation
        logger.info(  # pylint: disable=logging-fstring-interpolation
            f"Reality Track: {reality_pass_count}/{len(reality_results)} 通过"
        )  # pylint: disable=logging-fstring-interpolation
        logger.info(  # pylint: disable=logging-fstring-interpolation
            f"Hell Track: {hell_pass_count}/{len(hell_results)} 通过"
        )  # pylint: disable=logging-fstring-interpolation

        return result
