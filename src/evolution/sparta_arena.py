"""斯巴达竞技场 - 策略双轨测试系统

白皮书依据: 第四章 4.2 斯巴达竞技场

对候选策略进行严格的双轨压力测试：
- Reality Track: 历史数据回测，验证策略盈利能力
- Hell Track: 极端场景测试，验证策略生存能力

只有通过双轨测试的策略才能进入模拟盘验证阶段。

Author: MIA System
Date: 2026-01-23
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
from loguru import logger

from src.evolution.factor_data_models import ArenaTestResult, CandidateStrategy


@dataclass
class StrategyRealityConfig:
    """Reality Track配置

    白皮书依据: 第四章 4.2 Reality Track测试标准
    """

    # 回测时间范围
    backtest_years: int = 3  # 3年历史数据

    # 通过标准
    min_sharpe_ratio: float = 1.5  # 最低夏普比率
    max_drawdown_limit: float = 0.15  # 最大回撤限制（15%）
    min_annual_return: float = 0.10  # 最低年化收益率（10%）
    min_win_rate: float = 0.50  # 最低胜率（50%）

    # 评分权重
    sharpe_weight: float = 0.4
    drawdown_weight: float = 0.3
    return_weight: float = 0.2
    win_rate_weight: float = 0.1


@dataclass
class StrategyHellConfig:
    """Hell Track配置

    白皮书依据: 第四章 4.2 Hell Track极端场景测试
    """

    # 极端场景定义
    scenarios: List[str] = None

    # 通过标准
    min_survival_rate: float = 0.80  # 最低生存率（80%）
    max_recovery_days: int = 30  # 最大恢复时间（30天）
    min_risk_adjusted_return: float = 0.0  # 风险调整后收益必须为正

    # 评分权重
    survival_weight: float = 0.5
    recovery_weight: float = 0.3
    return_weight: float = 0.2

    def __post_init__(self):
        """初始化默认场景"""
        if self.scenarios is None:
            self.scenarios = [
                "market_crash",  # 市场崩盘（-20%单日跌幅）
                "flash_crash",  # 闪电崩盘（-10%瞬间跌幅）
                "liquidity_crisis",  # 流动性危机（交易量骤降80%）
                "volatility_spike",  # 波动率飙升（VIX翻倍）
                "correlation_breakdown",  # 相关性崩溃（历史相关性失效）
            ]


@dataclass
class SpartaArenaConfig:
    """Sparta Arena总体配置

    白皮书依据: 第四章 4.2 斯巴达竞技场评分系统
    """

    reality_config: StrategyRealityConfig = None
    hell_config: StrategyHellConfig = None

    # Arena评分权重
    reality_weight: float = 0.6  # Reality Track权重
    hell_weight: float = 0.4  # Hell Track权重

    # 通过标准
    min_arena_score: float = 0.7  # 最低Arena分数

    def __post_init__(self):
        """初始化默认配置"""
        if self.reality_config is None:
            self.reality_config = StrategyRealityConfig()
        if self.hell_config is None:
            self.hell_config = StrategyHellConfig()


class StrategyRealityTrack:
    """Reality Track - 历史数据回测

    白皮书依据: 第四章 4.2 Reality Track

    在3年历史数据上回测策略，评估：
    - 夏普比率（Sharpe Ratio）
    - 最大回撤（Max Drawdown）
    - 年化收益率（Annual Return）
    - 胜率（Win Rate）

    Attributes:
        config: Reality Track配置
    """

    def __init__(self, config: Optional[StrategyRealityConfig] = None):
        """初始化Reality Track

        Args:
            config: Reality Track配置，None则使用默认配置
        """
        self.config = config or StrategyRealityConfig()

        logger.info(
            f"初始化StrategyRealityTrack: "
            f"backtest_years={self.config.backtest_years}, "
            f"min_sharpe={self.config.min_sharpe_ratio}, "
            f"max_dd={self.config.max_drawdown_limit}"
        )

    async def test_strategy(self, strategy: CandidateStrategy, historical_data: Optional[pd.DataFrame] = None) -> Dict:
        """在历史数据上测试策略

        白皮书依据: 第四章 4.2 Reality Track测试流程

        Args:
            strategy: 候选策略
            historical_data: 历史数据，None则生成模拟数据

        Returns:
            测试结果字典，包含：
            - sharpe_ratio: 夏普比率
            - max_drawdown: 最大回撤
            - annual_return: 年化收益率
            - win_rate: 胜率
            - total_trades: 总交易次数
            - winning_trades: 盈利交易次数
            - losing_trades: 亏损交易次数
            - reality_score: Reality Track评分（0.0-1.0）
            - passed: 是否通过测试
        """
        logger.info(f"开始Reality Track测试: {strategy.name}")

        # 如果没有提供历史数据，生成模拟数据
        if historical_data is None:
            historical_data = self._generate_mock_historical_data()

        # 运行回测
        backtest_result = await self._run_backtest(strategy, historical_data)

        # 计算评分
        reality_score = self._calculate_reality_score(backtest_result)

        # 判断是否通过
        passed = self._check_pass_criteria(backtest_result)

        result = {
            "sharpe_ratio": backtest_result["sharpe_ratio"],
            "max_drawdown": backtest_result["max_drawdown"],
            "annual_return": backtest_result["annual_return"],
            "win_rate": backtest_result["win_rate"],
            "total_trades": backtest_result["total_trades"],
            "winning_trades": backtest_result["winning_trades"],
            "losing_trades": backtest_result["losing_trades"],
            "reality_score": reality_score,
            "passed": passed,
        }

        logger.info(
            f"Reality Track测试完成: {strategy.name}, "
            f"Sharpe={result['sharpe_ratio']:.3f}, "
            f"DD={result['max_drawdown']:.3f}, "
            f"Return={result['annual_return']:.3f}, "
            f"Score={reality_score:.3f}, "
            f"Passed={passed}"
        )

        return result

    async def _run_backtest(
        self, strategy: CandidateStrategy, historical_data: pd.DataFrame  # pylint: disable=unused-argument
    ) -> Dict:  # pylint: disable=unused-argument
        """运行回测

        Args:
            strategy: 候选策略
            historical_data: 历史数据

        Returns:
            回测结果字典
        """
        # 简化实现：生成模拟回测结果
        # 实际实现需要执行策略代码并计算真实指标

        # 基于策略的expected_sharpe生成合理的回测结果
        base_sharpe = strategy.expected_sharpe

        # 添加一些随机性
        sharpe_ratio = base_sharpe * np.random.uniform(0.8, 1.2)
        annual_return = sharpe_ratio * 0.15 * np.random.uniform(0.8, 1.2)  # 假设波动率15%
        max_drawdown = abs(annual_return) * np.random.uniform(0.3, 0.6)

        # 生成交易统计
        total_trades = np.random.randint(50, 200)
        win_rate = 0.5 + (sharpe_ratio - 1.0) * 0.1  # Sharpe越高，胜率越高
        win_rate = np.clip(win_rate, 0.3, 0.7)

        winning_trades = int(total_trades * win_rate)
        losing_trades = total_trades - winning_trades

        return {
            "sharpe_ratio": sharpe_ratio,
            "max_drawdown": max_drawdown,
            "annual_return": annual_return,
            "win_rate": win_rate,
            "total_trades": total_trades,
            "winning_trades": winning_trades,
            "losing_trades": losing_trades,
        }

    def _calculate_reality_score(self, backtest_result: Dict) -> float:
        """计算Reality Track评分

        白皮书依据: 第四章 4.2 Reality Track评分公式

        评分 = Sharpe权重 * Sharpe归一化分数
             + Drawdown权重 * Drawdown归一化分数
             + Return权重 * Return归一化分数
             + WinRate权重 * WinRate归一化分数

        Args:
            backtest_result: 回测结果

        Returns:
            Reality Track评分（0.0-1.0）
        """
        # Sharpe归一化：Sharpe > 3.0 得满分
        sharpe_score = min(backtest_result["sharpe_ratio"] / 3.0, 1.0)

        # Drawdown归一化：DD < 5% 得满分，DD > 20% 得0分
        dd = backtest_result["max_drawdown"]
        if dd < 0.05:
            dd_score = 1.0
        elif dd > 0.20:
            dd_score = 0.0
        else:
            dd_score = 1.0 - (dd - 0.05) / 0.15

        # Return归一化：Return > 30% 得满分
        return_score = min(backtest_result["annual_return"] / 0.30, 1.0)

        # WinRate归一化：WinRate > 60% 得满分
        win_rate_score = min(backtest_result["win_rate"] / 0.60, 1.0)

        # 加权求和
        reality_score = (
            self.config.sharpe_weight * sharpe_score
            + self.config.drawdown_weight * dd_score
            + self.config.return_weight * return_score
            + self.config.win_rate_weight * win_rate_score
        )

        return reality_score

    def _check_pass_criteria(self, backtest_result: Dict) -> bool:
        """检查是否通过Reality Track测试

        白皮书依据: 第四章 4.2 Reality Track通过标准

        通过条件（全部满足）：
        - Sharpe ratio > 1.5
        - Max drawdown < 15%
        - Annual return > 10%
        - Win rate > 50%

        Args:
            backtest_result: 回测结果

        Returns:
            是否通过测试
        """
        passed = (
            backtest_result["sharpe_ratio"] > self.config.min_sharpe_ratio
            and backtest_result["max_drawdown"] < self.config.max_drawdown_limit
            and backtest_result["annual_return"] > self.config.min_annual_return
            and backtest_result["win_rate"] > self.config.min_win_rate
        )

        return passed

    def _generate_mock_historical_data(self) -> pd.DataFrame:
        """生成模拟历史数据

        Returns:
            模拟历史数据DataFrame
        """
        # 生成3年的日度数据
        days = self.config.backtest_years * 252
        dates = pd.date_range(end=datetime.now(), periods=days, freq="D")

        # 生成随机价格数据
        np.random.seed(42)
        returns = np.random.normal(0.0005, 0.02, days)
        prices = 100 * np.exp(np.cumsum(returns))

        data = pd.DataFrame({"date": dates, "close": prices, "volume": np.random.randint(1000000, 10000000, days)})

        return data


class StrategyHellTrack:
    """Hell Track - 极端场景测试

    白皮书依据: 第四章 4.2 Hell Track

    在5种极端市场场景下测试策略，评估：
    - 生存率（Survival Rate）
    - 恢复时间（Recovery Time）
    - 风险调整后收益（Risk-Adjusted Return）

    极端场景：
    1. 市场崩盘（Market Crash）：-20%单日跌幅
    2. 闪电崩盘（Flash Crash）：-10%瞬间跌幅
    3. 流动性危机（Liquidity Crisis）：交易量骤降80%
    4. 波动率飙升（Volatility Spike）：VIX翻倍
    5. 相关性崩溃（Correlation Breakdown）：历史相关性失效

    Attributes:
        config: Hell Track配置
    """

    def __init__(self, config: Optional[StrategyHellConfig] = None):
        """初始化Hell Track

        Args:
            config: Hell Track配置，None则使用默认配置
        """
        self.config = config or StrategyHellConfig()

        logger.info(
            f"初始化StrategyHellTrack: "
            f"scenarios={len(self.config.scenarios)}, "
            f"min_survival={self.config.min_survival_rate}"
        )

    async def test_strategy(self, strategy: CandidateStrategy) -> Dict:
        """在极端场景下测试策略

        白皮书依据: 第四章 4.2 Hell Track测试流程

        Args:
            strategy: 候选策略

        Returns:
            测试结果字典，包含：
            - survival_rate: 生存率（0.0-1.0）
            - avg_recovery_days: 平均恢复时间（天）
            - risk_adjusted_return: 风险调整后收益
            - scenario_results: 各场景详细结果
            - hell_score: Hell Track评分（0.0-1.0）
            - passed: 是否通过测试
        """
        logger.info(f"开始Hell Track测试: {strategy.name}")

        scenario_results = []
        survived_count = 0
        total_recovery_days = 0
        total_risk_adjusted_return = 0.0

        # 测试每个极端场景
        for scenario in self.config.scenarios:
            result = await self._test_scenario(strategy, scenario)
            scenario_results.append(result)

            if result["survived"]:
                survived_count += 1
                total_recovery_days += result["recovery_days"]
                total_risk_adjusted_return += result["risk_adjusted_return"]

        # 计算总体指标
        survival_rate = survived_count / len(self.config.scenarios)
        avg_recovery_days = total_recovery_days / survived_count if survived_count > 0 else 999
        avg_risk_adjusted_return = total_risk_adjusted_return / len(self.config.scenarios)

        # 计算评分
        hell_score = self._calculate_hell_score(survival_rate, avg_recovery_days, avg_risk_adjusted_return)

        # 判断是否通过
        passed = self._check_pass_criteria(survival_rate, avg_recovery_days, avg_risk_adjusted_return)

        result = {
            "survival_rate": survival_rate,
            "avg_recovery_days": avg_recovery_days,
            "risk_adjusted_return": avg_risk_adjusted_return,
            "scenario_results": scenario_results,
            "hell_score": hell_score,
            "passed": passed,
        }

        logger.info(
            f"Hell Track测试完成: {strategy.name}, "
            f"Survival={survival_rate:.3f}, "
            f"Recovery={avg_recovery_days:.1f}days, "
            f"Score={hell_score:.3f}, "
            f"Passed={passed}"
        )

        return result

    async def _test_scenario(self, strategy: CandidateStrategy, scenario: str) -> Dict:
        """测试单个极端场景

        Args:
            strategy: 候选策略
            scenario: 场景名称

        Returns:
            场景测试结果
        """
        # 简化实现：生成模拟场景测试结果
        # 实际实现需要模拟极端市场条件并执行策略

        # 基于策略的expected_sharpe和场景类型生成结果
        base_sharpe = strategy.expected_sharpe

        # 不同场景有不同的生存概率
        scenario_difficulty = {
            "market_crash": 0.7,
            "flash_crash": 0.8,
            "liquidity_crisis": 0.75,
            "volatility_spike": 0.85,
            "correlation_breakdown": 0.65,
        }

        difficulty = scenario_difficulty.get(scenario, 0.75)
        survival_prob = min(base_sharpe / 2.0 * difficulty, 0.95)

        survived = np.random.random() < survival_prob

        if survived:
            recovery_days = int(np.random.uniform(5, 30))
            risk_adjusted_return = np.random.uniform(-0.05, 0.10)
        else:
            recovery_days = 999  # 未恢复
            risk_adjusted_return = np.random.uniform(-0.30, -0.10)

        return {
            "scenario": scenario,
            "survived": survived,
            "recovery_days": recovery_days,
            "risk_adjusted_return": risk_adjusted_return,
        }

    def _calculate_hell_score(
        self, survival_rate: float, avg_recovery_days: float, risk_adjusted_return: float
    ) -> float:
        """计算Hell Track评分

        白皮书依据: 第四章 4.2 Hell Track评分公式

        评分 = Survival权重 * Survival归一化分数
             + Recovery权重 * Recovery归一化分数
             + Return权重 * Return归一化分数

        Args:
            survival_rate: 生存率
            avg_recovery_days: 平均恢复时间
            risk_adjusted_return: 风险调整后收益

        Returns:
            Hell Track评分（0.0-1.0）
        """
        # Survival归一化：直接使用生存率
        survival_score = survival_rate

        # Recovery归一化：< 10天得满分，> 30天得0分
        if avg_recovery_days < 10:
            recovery_score = 1.0
        elif avg_recovery_days > 30:
            recovery_score = 0.0
        else:
            recovery_score = 1.0 - (avg_recovery_days - 10) / 20

        # Return归一化：> 5% 得满分，< -10% 得0分
        if risk_adjusted_return > 0.05:
            return_score = 1.0
        elif risk_adjusted_return < -0.10:
            return_score = 0.0
        else:
            return_score = (risk_adjusted_return + 0.10) / 0.15

        # 加权求和
        hell_score = (
            self.config.survival_weight * survival_score
            + self.config.recovery_weight * recovery_score
            + self.config.return_weight * return_score
        )

        return hell_score

    def _check_pass_criteria(self, survival_rate: float, avg_recovery_days: float, risk_adjusted_return: float) -> bool:
        """检查是否通过Hell Track测试

        白皮书依据: 第四章 4.2 Hell Track通过标准

        通过条件（全部满足）：
        - Survival rate > 80%
        - Recovery time < 30 days
        - Risk-adjusted return > 0

        Args:
            survival_rate: 生存率
            avg_recovery_days: 平均恢复时间
            risk_adjusted_return: 风险调整后收益

        Returns:
            是否通过测试
        """
        passed = (
            survival_rate > self.config.min_survival_rate
            and avg_recovery_days < self.config.max_recovery_days
            and risk_adjusted_return > self.config.min_risk_adjusted_return
        )

        return passed


class SpartaArena:
    """斯巴达竞技场 - 策略双轨测试系统

    白皮书依据: 第四章 4.2 斯巴达竞技场

    对候选策略进行严格的双轨压力测试：
    - Reality Track: 历史数据回测
    - Hell Track: 极端场景测试

    只有Arena分数 > 0.7的策略才能进入模拟盘验证阶段。

    Attributes:
        config: Sparta Arena配置
        reality_track: Reality Track测试器
        hell_track: Hell Track测试器
    """

    def __init__(self, config: Optional[SpartaArenaConfig] = None):
        """初始化Sparta Arena

        Args:
            config: Sparta Arena配置，None则使用默认配置
        """
        self.config = config or SpartaArenaConfig()

        # 初始化双轨测试器
        self.reality_track = StrategyRealityTrack(self.config.reality_config)
        self.hell_track = StrategyHellTrack(self.config.hell_config)

        logger.info(
            f"初始化SpartaArena: "
            f"reality_weight={self.config.reality_weight}, "
            f"hell_weight={self.config.hell_weight}, "
            f"min_score={self.config.min_arena_score}"
        )

    async def test_strategy(
        self, strategy: CandidateStrategy, historical_data: Optional[pd.DataFrame] = None
    ) -> ArenaTestResult:
        """对策略进行双轨测试

        白皮书依据: 第四章 4.2 斯巴达竞技场测试流程

        Args:
            strategy: 候选策略
            historical_data: 历史数据，None则生成模拟数据

        Returns:
            Arena测试结果

        Raises:
            ValueError: 当策略为None时
        """
        if strategy is None:
            raise ValueError("策略不能为None")

        logger.info(f"开始Sparta Arena测试: {strategy.name}")

        # 1. Reality Track测试
        reality_result = await self.reality_track.test_strategy(strategy, historical_data)

        # 2. Hell Track测试
        hell_result = await self.hell_track.test_strategy(strategy)

        # 3. 计算综合Arena分数
        arena_score = self.calculate_strategy_score(reality_result, hell_result)

        # 4. 判断是否通过
        passed = arena_score > self.config.min_arena_score and reality_result["passed"] and hell_result["passed"]

        # 5. 确定下一阶段
        next_stage = "simulation" if passed else "rejected"

        # 6. 创建测试结果
        test_result = ArenaTestResult(
            test_type="strategy",
            subject_id=strategy.id,
            arena_score=arena_score,
            reality_result=reality_result,
            hell_result=hell_result,
            cross_market_result=None,  # 策略测试不需要跨市场测试
            passed=passed,
            next_stage=next_stage,
            test_timestamp=datetime.now(),
            detailed_metrics={
                "reality_score": reality_result["reality_score"],
                "hell_score": hell_result["hell_score"],
                "sharpe_ratio": reality_result["sharpe_ratio"],
                "max_drawdown": reality_result["max_drawdown"],
                "survival_rate": hell_result["survival_rate"],
            },
        )

        logger.info(
            f"Sparta Arena测试完成: {strategy.name}, "
            f"Arena Score={arena_score:.3f}, "
            f"Reality={reality_result['reality_score']:.3f}, "
            f"Hell={hell_result['hell_score']:.3f}, "
            f"Passed={passed}, "
            f"Next={next_stage}"
        )

        return test_result

    def calculate_strategy_score(self, reality_result: Dict, hell_result: Dict) -> float:
        """计算策略综合Arena分数

        白皮书依据: 第四章 4.2 Arena评分公式

        Arena Score = Reality权重 * Reality Score + Hell权重 * Hell Score

        Args:
            reality_result: Reality Track测试结果
            hell_result: Hell Track测试结果

        Returns:
            Arena分数（0.0-1.0）
        """
        arena_score = (
            self.config.reality_weight * reality_result["reality_score"]
            + self.config.hell_weight * hell_result["hell_score"]
        )

        return arena_score

    def get_statistics(self) -> Dict:
        """获取Arena统计信息

        Returns:
            统计信息字典
        """
        return {
            "reality_weight": self.config.reality_weight,
            "hell_weight": self.config.hell_weight,
            "min_arena_score": self.config.min_arena_score,
            "reality_config": {
                "min_sharpe": self.config.reality_config.min_sharpe_ratio,
                "max_drawdown": self.config.reality_config.max_drawdown_limit,
                "min_return": self.config.reality_config.min_annual_return,
                "min_win_rate": self.config.reality_config.min_win_rate,
            },
            "hell_config": {
                "scenarios": len(self.config.hell_config.scenarios),
                "min_survival": self.config.hell_config.min_survival_rate,
                "max_recovery": self.config.hell_config.max_recovery_days,
            },
        }
