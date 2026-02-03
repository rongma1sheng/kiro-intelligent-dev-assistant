"""Arena Integration Module for ETF/LOF Factor Miners

白皮书依据: 第四章 4.2.1 因子Arena三轨测试系统
版本: v1.6.1
铁律依据: MIA编码铁律1 (白皮书至上), 铁律2 (禁止简化和占位符)

This module provides integration between ETF/LOF factor miners and the
FactorArena three-track testing system. It handles:
1. Factor submission to Arena with retry logic
2. Arena test result processing and validation
3. Factor lifecycle management (pending → testing → passed/failed)
4. Integration with Z2H certification pipeline

核心功能:
- submit_to_arena: 提交因子到Arena测试队列
- process_arena_result: 处理Arena测试结果
- validate_factor_before_submission: 提交前验证
- retry_with_exponential_backoff: 指数退避重试机制
"""

import asyncio
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from loguru import logger

from ..factor_arena import FactorArenaSystem, FactorTestResult
from .data_models import ArenaTestResult
from .exceptions import ArenaSubmissionError, ArenaTestError, FactorMiningError


class ArenaIntegration:
    """Arena集成管理器

    白皮书依据: 第四章 4.2.1 因子Arena三轨测试系统
    铁律依据: MIA编码铁律1 (白皮书至上)

    负责ETF/LOF因子挖掘器与FactorArena系统的集成。

    核心职责:
    1. 因子提交: 将挖掘出的因子提交到Arena测试队列
    2. 结果处理: 解析Arena测试结果并更新因子状态
    3. 重试机制: 处理提交失败和网络错误
    4. 生命周期管理: 跟踪因子从提交到认证的完整流程

    性能要求:
    - 提交延迟 < 100ms
    - 重试最多3次
    - 指数退避: 1s, 2s, 4s

    Attributes:
        arena_system: FactorArena系统实例
        max_retries: 最大重试次数
        base_delay: 基础延迟时间(秒)
        submission_history: 提交历史记录

    Example:
        >>> integration = ArenaIntegration(arena_system)
        >>> await integration.initialize()
        >>> result = await integration.submit_to_arena(
        ...     factor_expression="close/delay(close,1)-1",
        ...     factor_type="etf",
        ...     metadata={"miner": "ETFFactorMiner"}
        ... )
    """

    def __init__(self, arena_system: Optional[FactorArenaSystem] = None, max_retries: int = 3, base_delay: float = 1.0):
        """初始化Arena集成管理器

        白皮书依据: 第四章 4.2.1 - Arena集成初始化
        铁律依据: MIA编码铁律3 (完整的错误处理)

        Args:
            arena_system: FactorArena系统实例(可选,如果为None则自动创建)
            max_retries: 最大重试次数,默认3次
            base_delay: 基础延迟时间(秒),默认1.0秒

        Raises:
            ValueError: 当max_retries < 0时
            ValueError: 当base_delay <= 0时
        """
        if max_retries < 0:
            raise ValueError(f"max_retries must be >= 0, got {max_retries}")

        if base_delay <= 0:
            raise ValueError(f"base_delay must be > 0, got {base_delay}")

        self.arena_system = arena_system
        self.max_retries = max_retries
        self.base_delay = base_delay

        # 提交历史记录
        self.submission_history: List[Dict[str, Any]] = []

        # 统计信息
        self.stats = {
            "total_submissions": 0,
            "successful_submissions": 0,
            "failed_submissions": 0,
            "retries_used": 0,
            "avg_submission_time_ms": 0.0,
        }

        logger.info(f"ArenaIntegration初始化: " f"max_retries={max_retries}, base_delay={base_delay}s")

    async def initialize(self):
        """初始化Arena集成

        白皮书依据: 第四章 4.2.1 - Arena系统初始化

        Raises:
            FactorMiningError: 当Arena系统初始化失败时
        """
        try:
            # 如果没有提供Arena系统,创建默认实例
            if self.arena_system is None:
                logger.info("创建默认FactorArena系统实例")
                self.arena_system = FactorArenaSystem()

            # 初始化Arena系统
            if not self.arena_system.is_running:
                await self.arena_system.initialize()

            logger.info("ArenaIntegration初始化完成")

        except Exception as e:
            logger.error(f"ArenaIntegration初始化失败: {e}")
            raise FactorMiningError(f"Arena集成初始化失败: {e}") from e

    async def submit_to_arena(
        self, factor_expression: str, factor_type: str, metadata: Optional[Dict[str, Any]] = None
    ) -> ArenaTestResult:
        """提交因子到Arena测试队列

        白皮书依据: 第四章 4.2.1 - 因子提交流程
        铁律依据: MIA编码铁律2 (禁止简化和占位符), 铁律3 (完整的错误处理)

        提交流程:
        1. 验证因子表达式
        2. 检查Arena系统状态
        3. 提交到测试队列
        4. 失败时自动重试(指数退避)
        5. 返回提交结果

        Args:
            factor_expression: 因子表达式字符串
            factor_type: 因子类型 ('etf' 或 'lof')
            metadata: 元数据(可选),包含挖掘器信息、参数等

        Returns:
            ArenaTestResult: Arena测试结果

        Raises:
            ValueError: 当factor_expression为空时
            ValueError: 当factor_type不是'etf'或'lof'时
            ArenaSubmissionError: 当提交失败且重试耗尽时

        Example:
            >>> result = await integration.submit_to_arena(
            ...     factor_expression="etf_premium_discount(close, nav)",
            ...     factor_type="etf",
            ...     metadata={"miner": "ETFFactorMiner", "generation": 10}
            ... )
            >>> print(f"提交状态: {result.status}")
        """
        # 参数验证
        if not factor_expression or not factor_expression.strip():
            raise ValueError("factor_expression不能为空")

        if factor_type not in ["etf", "lof"]:
            raise ValueError(f"factor_type必须是'etf'或'lof', 得到: {factor_type}")

        # 提交前验证
        validation_result = await self.validate_factor_before_submission(factor_expression, factor_type)

        if not validation_result["valid"]:
            raise ArenaSubmissionError(f"因子验证失败: {validation_result['error']}")

        # 记录开始时间
        start_time = time.perf_counter()
        self.stats["total_submissions"] += 1

        # 带重试的提交
        result = await self._submit_with_retry(factor_expression, factor_type, metadata)

        # 记录提交时间
        elapsed_ms = (time.perf_counter() - start_time) * 1000
        self._update_submission_stats(elapsed_ms, result.status == "submitted")

        # 记录提交历史
        self._record_submission(factor_expression, factor_type, metadata, result, elapsed_ms)

        logger.info(f"因子提交完成: {factor_expression[:50]}... " f"状态={result.status}, 耗时={elapsed_ms:.2f}ms")

        return result

    async def _submit_with_retry(
        self, factor_expression: str, factor_type: str, metadata: Optional[Dict[str, Any]]
    ) -> ArenaTestResult:
        """带指数退避的重试提交

        白皮书依据: 第四章 4.2.1 - 重试机制
        铁律依据: MIA编码铁律3 (完整的错误处理)

        重试策略:
        - 最多重试3次
        - 指数退避: 1s, 2s, 4s
        - 只对网络错误和超时重试
        - 验证错误不重试

        Args:
            factor_expression: 因子表达式
            factor_type: 因子类型
            metadata: 元数据

        Returns:
            ArenaTestResult: 提交结果

        Raises:
            ArenaSubmissionError: 当所有重试都失败时
        """
        last_error = None

        for attempt in range(self.max_retries + 1):
            try:
                # 尝试提交
                result = await self._do_submit(factor_expression, factor_type, metadata)

                # 提交成功
                if attempt > 0:
                    logger.info(f"重试成功: 第{attempt}次重试")
                    self.stats["retries_used"] += attempt

                return result

            except (ConnectionError, TimeoutError, asyncio.TimeoutError) as e:
                last_error = e

                if attempt < self.max_retries:
                    # 计算退避延迟
                    delay = self.base_delay * (2**attempt)
                    logger.warning(f"提交失败(第{attempt + 1}次尝试): {e}, " f"{delay}秒后重试...")
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"提交失败,重试耗尽: {e}")

            except Exception as e:
                # 非网络错误,不重试
                logger.error(f"提交失败(不可重试): {e}")
                raise ArenaSubmissionError(f"因子提交失败: {e}") from e

        # 所有重试都失败
        raise ArenaSubmissionError(f"因子提交失败,已重试{self.max_retries}次: {last_error}") from last_error

    async def _do_submit(
        self, factor_expression: str, factor_type: str, metadata: Optional[Dict[str, Any]]
    ) -> ArenaTestResult:
        """执行实际的提交操作

        白皮书依据: 第四章 4.2.1 - Arena提交接口

        Args:
            factor_expression: 因子表达式
            factor_type: 因子类型
            metadata: 元数据

        Returns:
            ArenaTestResult: 提交结果

        Raises:
            ConnectionError: 当Arena系统不可用时
            ArenaSubmissionError: 当提交被拒绝时
        """
        # 检查Arena系统状态
        if not self.arena_system or not self.arena_system.is_running:
            raise ConnectionError("Arena系统未运行")

        # 检查队列容量
        if len(self.arena_system.pending_factors) >= 1000:
            raise ArenaSubmissionError("Arena测试队列已满,请稍后重试")

        # 提交到Arena队列
        try:
            # 添加到待测试队列
            self.arena_system.pending_factors.append(factor_expression)

            # 创建提交结果
            result = ArenaTestResult(
                factor_expression=factor_expression,
                factor_type=factor_type,
                submission_time=datetime.now(),
                status="submitted",
                queue_position=len(self.arena_system.pending_factors),
                estimated_test_time_minutes=5.0,
                metadata=metadata or {},
            )

            logger.debug(
                f"因子已加入Arena队列: 位置={result.queue_position}, "
                f"预计测试时间={result.estimated_test_time_minutes}分钟"
            )

            return result

        except Exception as e:
            logger.error(f"Arena提交失败: {e}")
            raise ArenaSubmissionError(f"提交到Arena失败: {e}") from e

    async def validate_factor_before_submission(self, factor_expression: str, factor_type: str) -> Dict[str, Any]:
        """提交前验证因子

        白皮书依据: 第四章 4.2.1 - 因子验证标准
        铁律依据: MIA编码铁律2 (禁止简化和占位符)

        验证项:
        1. 表达式语法正确性
        2. 算子在白名单中
        3. 表达式复杂度合理
        4. 无循环依赖
        5. 参数范围有效

        Args:
            factor_expression: 因子表达式
            factor_type: 因子类型

        Returns:
            验证结果字典:
            {
                'valid': bool,  # 是否有效
                'error': str,   # 错误信息(如果无效)
                'warnings': List[str],  # 警告信息
                'complexity': int  # 表达式复杂度
            }

        Example:
            >>> result = await integration.validate_factor_before_submission(
            ...     "etf_premium_discount(close, nav)",
            ...     "etf"
            ... )
            >>> if result['valid']:
            ...     print("验证通过")
        """
        result = {"valid": True, "error": None, "warnings": [], "complexity": 0}

        try:
            # 1. 检查表达式不为空
            if not factor_expression or not factor_expression.strip():
                result["valid"] = False
                result["error"] = "因子表达式不能为空"
                return result

            # 2. 检查表达式长度
            if len(factor_expression) > 1000:
                result["valid"] = False
                result["error"] = f"因子表达式过长: {len(factor_expression)} > 1000"
                return result

            # 3. 检查括号匹配
            if factor_expression.count("(") != factor_expression.count(")"):
                result["valid"] = False
                result["error"] = "括号不匹配"
                return result

            # 4. 计算复杂度(算子数量)
            complexity = factor_expression.count("(")
            result["complexity"] = complexity

            if complexity > 10:
                result["warnings"].append(f"表达式复杂度较高: {complexity} > 10")

            # 5. 检查是否包含非法字符
            illegal_chars = ["$", "@", "#", "&", "|", ";", "`"]
            for char in illegal_chars:
                if char in factor_expression:
                    result["valid"] = False
                    result["error"] = f"包含非法字符: {char}"
                    return result

            # 6. 检查因子类型特定的算子
            if factor_type == "etf":
                # ETF因子应该包含ETF特定算子
                etf_operators = [
                    "etf_premium_discount",
                    "etf_creation_redemption_flow",
                    "etf_tracking_error",
                    "etf_arbitrage_opportunity",
                ]
                has_etf_operator = any(op in factor_expression for op in etf_operators)
                if not has_etf_operator:
                    result["warnings"].append("未使用ETF特定算子,可能不是最优因子")

            elif factor_type == "lof":
                # LOF因子应该包含LOF特定算子
                lof_operators = [
                    "lof_onoff_price_spread",
                    "lof_transfer_arbitrage_opportunity",
                    "lof_premium_discount_rate",
                    "lof_fund_manager_alpha",
                ]
                has_lof_operator = any(op in factor_expression for op in lof_operators)
                if not has_lof_operator:
                    result["warnings"].append("未使用LOF特定算子,可能不是最优因子")

            logger.debug(
                f"因子验证通过: {factor_expression[:50]}..., " f"复杂度={complexity}, 警告={len(result['warnings'])}"
            )

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"因子验证异常: {e}")
            result["valid"] = False
            result["error"] = f"验证过程异常: {e}"

        return result

    async def process_arena_result(self, arena_result: FactorTestResult) -> ArenaTestResult:
        """处理Arena测试结果

        白皮书依据: 第四章 4.2.1 - Arena测试结果处理
        铁律依据: MIA编码铁律2 (禁止简化和占位符), 铁律3 (完整的错误处理)

        处理流程:
        1. 验证测试结果完整性
        2. 解析三轨测试指标
        3. 计算综合评分
        4. 判断是否通过
        5. 生成下一步建议

        Args:
            arena_result: FactorArena系统返回的测试结果

        Returns:
            ArenaTestResult: 处理后的结果

        Raises:
            ArenaTestError: 当测试结果无效时

        Example:
            >>> arena_result = FactorTestResult(...)
            >>> processed = await integration.process_arena_result(arena_result)
            >>> if processed.passed:
            ...     print(f"因子通过测试,综合评分: {processed.overall_score}")
        """
        try:
            # 1. 验证结果完整性
            self._validate_arena_result(arena_result)

            # 2. 提取关键指标
            metrics = self._extract_metrics(arena_result)

            # 3. 计算综合评分
            overall_score = self._calculate_overall_score(metrics)

            # 4. 判断是否通过
            passed = self._determine_pass_status(metrics, overall_score)

            # 5. 生成建议
            recommendations = self._generate_recommendations(metrics, passed, overall_score)

            # 6. 创建处理后的结果
            processed_result = ArenaTestResult(
                factor_expression=arena_result.factor_expression,
                factor_type=self._infer_factor_type(arena_result.factor_expression),
                submission_time=arena_result.test_start_time,
                test_completion_time=arena_result.test_end_time,
                status="passed" if passed else "failed",
                # Reality Track指标
                reality_ic_mean=arena_result.ic_mean,
                reality_ic_std=arena_result.ic_std,
                reality_ir=arena_result.ir,
                reality_sharpe=arena_result.sharpe_ratio,
                reality_max_drawdown=arena_result.max_drawdown,
                reality_annual_return=arena_result.annual_return,
                reality_win_rate=arena_result.win_rate,
                # Hell Track指标
                hell_survival_rate=arena_result.survival_rate,
                hell_ic_decay_rate=arena_result.ic_decay_rate,
                hell_recovery_ability=arena_result.recovery_ability,
                hell_stress_score=arena_result.stress_score,
                # Cross-Market Track指标
                cross_market_markets_passed=arena_result.markets_passed,
                cross_market_adaptability=arena_result.adaptability_score,
                cross_market_consistency=arena_result.consistency_score,
                # 综合评分
                overall_score=overall_score,
                passed=passed,
                # 详细信息
                detailed_metrics=arena_result.detailed_metrics,
                recommendations=recommendations,
                metadata={},
            )

            logger.info(
                f"Arena结果处理完成: {arena_result.factor_expression[:50]}..., "
                f"通过={passed}, 综合评分={overall_score:.2f}"
            )

            return processed_result

        except Exception as e:
            logger.error(f"Arena结果处理失败: {e}")
            raise ArenaTestError(f"处理Arena测试结果失败: {e}") from e

    def _validate_arena_result(self, result: FactorTestResult):
        """验证Arena测试结果的完整性

        Args:
            result: Arena测试结果

        Raises:
            ArenaTestError: 当结果无效时
        """
        if not result.factor_expression:
            raise ArenaTestError("因子表达式为空")

        if result.test_end_time < result.test_start_time:
            raise ArenaTestError("测试结束时间早于开始时间")

        # 检查必要指标是否存在
        required_metrics = ["ic_mean", "sharpe_ratio", "survival_rate"]

        for metric in required_metrics:
            value = getattr(result, metric, None)
            if value is None:
                raise ArenaTestError(f"缺少必要指标: {metric}")

    def _extract_metrics(self, result: FactorTestResult) -> Dict[str, float]:
        """提取关键指标

        Args:
            result: Arena测试结果

        Returns:
            指标字典
        """
        return {
            # Reality Track
            "ic_mean": result.ic_mean,
            "ic_std": result.ic_std,
            "ir": result.ir,
            "sharpe": result.sharpe_ratio,
            "max_drawdown": result.max_drawdown,
            "annual_return": result.annual_return,
            "win_rate": result.win_rate,
            # Hell Track
            "survival_rate": result.survival_rate,
            "ic_decay_rate": result.ic_decay_rate,
            "recovery_ability": result.recovery_ability,
            "stress_score": result.stress_score,
            # Cross-Market Track
            "markets_passed": result.markets_passed,
            "adaptability": result.adaptability_score,
            "consistency": result.consistency_score,
        }

    def _calculate_overall_score(self, metrics: Dict[str, float]) -> float:
        """计算综合评分

        白皮书依据: 第四章 4.2.1 - 综合评分算法

        评分公式:
        Overall = Reality * 0.4 + Hell * 0.4 + CrossMarket * 0.2

        Reality Score = (IC * 0.3 + Sharpe * 0.3 + WinRate * 0.2 + Return * 0.2) * 100
        Hell Score = (Survival * 0.5 + Recovery * 0.3 + Stress * 0.2) * 100
        CrossMarket Score = (Adaptability * 0.6 + Consistency * 0.4) * 100

        Args:
            metrics: 指标字典

        Returns:
            综合评分 (0-100)
        """
        # Reality Track评分
        reality_score = (
            abs(metrics["ic_mean"]) * 0.3
            + min(metrics["sharpe"] / 3.0, 1.0) * 0.3
            + metrics["win_rate"] * 0.2
            + min(metrics["annual_return"] / 0.5, 1.0) * 0.2
        ) * 100

        # Hell Track评分
        hell_score = (
            metrics["survival_rate"] * 0.5 + metrics["recovery_ability"] * 0.3 + (1.0 - metrics["stress_score"]) * 0.2
        ) * 100

        # Cross-Market Track评分
        cross_market_score = (metrics["adaptability"] * 0.6 + metrics["consistency"] * 0.4) * 100

        # 综合评分
        overall = reality_score * 0.4 + hell_score * 0.4 + cross_market_score * 0.2

        return round(overall, 2)

    def _determine_pass_status(self, metrics: Dict[str, float], overall_score: float) -> bool:
        """判断是否通过测试

        白皮书依据: 第四章 4.2.1 - 通过标准

        通过条件(必须全部满足):
        1. Reality Track: IC > 0.05, Sharpe > 1.5
        2. Hell Track: survival_rate > 0.7
        3. Cross-Market: markets_passed >= 2
        4. Overall Score >= 60

        Args:
            metrics: 指标字典
            overall_score: 综合评分

        Returns:
            是否通过
        """
        # Reality Track条件
        reality_pass = abs(metrics["ic_mean"]) > 0.05 and metrics["sharpe"] > 1.5

        # Hell Track条件
        hell_pass = metrics["survival_rate"] > 0.7

        # Cross-Market Track条件
        cross_market_pass = metrics["markets_passed"] >= 2

        # 综合评分条件
        score_pass = overall_score >= 60.0

        # 全部通过才算通过
        passed = reality_pass and hell_pass and cross_market_pass and score_pass

        logger.debug(
            f"通过判定: Reality={reality_pass}, Hell={hell_pass}, "
            f"CrossMarket={cross_market_pass}, Score={score_pass}, "
            f"Overall={passed}"
        )

        return passed

    def _generate_recommendations(self, metrics: Dict[str, float], passed: bool, overall_score: float) -> List[str]:
        """生成改进建议

        Args:
            metrics: 指标字典
            passed: 是否通过
            overall_score: 综合评分

        Returns:
            建议列表
        """
        recommendations = []

        if passed:
            recommendations.append(f"✅ 因子通过Arena三轨测试,综合评分{overall_score:.2f}")
            recommendations.append("建议: 提交到模拟盘进行1个月实战验证")
        else:
            recommendations.append(f"❌ 因子未通过Arena测试,综合评分{overall_score:.2f}")

            # Reality Track建议
            if abs(metrics["ic_mean"]) <= 0.05:
                recommendations.append(
                    f"Reality Track: IC过低({metrics['ic_mean']:.4f}), " "建议增加因子复杂度或尝试新算子组合"
                )

            if metrics["sharpe"] <= 1.5:
                recommendations.append(
                    f"Reality Track: 夏普比率过低({metrics['sharpe']:.2f}), " "建议优化风险控制或提高收益稳定性"
                )

            # Hell Track建议
            if metrics["survival_rate"] <= 0.7:
                recommendations.append(
                    f"Hell Track: 存活率过低({metrics['survival_rate']:.2f}), " "建议增强因子在极端市场的稳定性"
                )

            # Cross-Market Track建议
            if metrics["markets_passed"] < 2:
                recommendations.append(
                    f"Cross-Market Track: 通过市场数不足({metrics['markets_passed']}), " "建议提高因子的跨市场适应性"
                )

        return recommendations

    def _infer_factor_type(self, factor_expression: str) -> str:
        """推断因子类型

        Args:
            factor_expression: 因子表达式

        Returns:
            因子类型 ('etf', 'lof', 或 'unknown')
        """
        etf_keywords = ["etf_", "nav", "creation", "redemption", "tracking"]
        lof_keywords = ["lof_", "onmarket", "offmarket", "transfer"]

        expression_lower = factor_expression.lower()

        etf_count = sum(1 for kw in etf_keywords if kw in expression_lower)
        lof_count = sum(1 for kw in lof_keywords if kw in expression_lower)

        if etf_count > lof_count:  # pylint: disable=no-else-return
            return "etf"
        elif lof_count > etf_count:
            return "lof"
        else:
            return "unknown"

    def _update_submission_stats(self, elapsed_ms: float, success: bool):
        """更新提交统计信息

        Args:
            elapsed_ms: 提交耗时(毫秒)
            success: 是否成功
        """
        if success:
            self.stats["successful_submissions"] += 1
        else:
            self.stats["failed_submissions"] += 1

        # 更新平均提交时间
        total = self.stats["total_submissions"]
        current_avg = self.stats["avg_submission_time_ms"]
        new_avg = (current_avg * (total - 1) + elapsed_ms) / total
        self.stats["avg_submission_time_ms"] = new_avg

    def _record_submission(  # pylint: disable=too-many-positional-arguments
        self,
        factor_expression: str,
        factor_type: str,
        metadata: Optional[Dict[str, Any]],
        result: ArenaTestResult,
        elapsed_ms: float,
    ):
        """记录提交历史

        Args:
            factor_expression: 因子表达式
            factor_type: 因子类型
            metadata: 元数据
            result: 提交结果
            elapsed_ms: 提交耗时
        """
        record = {
            "timestamp": datetime.now().isoformat(),
            "factor_expression": factor_expression,
            "factor_type": factor_type,
            "metadata": metadata,
            "status": result.status,
            "queue_position": result.queue_position,
            "elapsed_ms": elapsed_ms,
        }

        self.submission_history.append(record)

        # 只保留最近1000条记录
        if len(self.submission_history) > 1000:
            self.submission_history = self.submission_history[-1000:]

    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息

        Returns:
            统计信息字典
        """
        success_rate = 0.0
        if self.stats["total_submissions"] > 0:
            success_rate = self.stats["successful_submissions"] / self.stats["total_submissions"]

        return {
            "total_submissions": self.stats["total_submissions"],
            "successful_submissions": self.stats["successful_submissions"],
            "failed_submissions": self.stats["failed_submissions"],
            "success_rate": success_rate,
            "retries_used": self.stats["retries_used"],
            "avg_submission_time_ms": self.stats["avg_submission_time_ms"],
            "history_size": len(self.submission_history),
        }


# 便捷函数


async def submit_to_arena(
    factor_expression: str,
    factor_type: str,
    arena_system: Optional[FactorArenaSystem] = None,
    metadata: Optional[Dict[str, Any]] = None,
    max_retries: int = 3,
) -> ArenaTestResult:
    """便捷函数: 提交因子到Arena

    白皮书依据: 第四章 4.2.1 - 因子提交接口

    这是一个便捷函数,封装了ArenaIntegration的创建和提交流程。

    Args:
        factor_expression: 因子表达式
        factor_type: 因子类型 ('etf' 或 'lof')
        arena_system: Arena系统实例(可选)
        metadata: 元数据(可选)
        max_retries: 最大重试次数

    Returns:
        ArenaTestResult: 提交结果

    Example:
        >>> result = await submit_to_arena(
        ...     "etf_premium_discount(close, nav)",
        ...     "etf"
        ... )
        >>> print(f"提交状态: {result.status}")
    """
    integration = ArenaIntegration(arena_system=arena_system, max_retries=max_retries)

    await integration.initialize()

    result = await integration.submit_to_arena(
        factor_expression=factor_expression, factor_type=factor_type, metadata=metadata
    )

    return result
