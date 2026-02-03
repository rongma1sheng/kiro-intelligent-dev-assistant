"""Commander核心类和成本追踪器

白皮书依据: 第二章 2.2 Commander (慢系统 - 云端增强)
"""

import asyncio
import json
import time
from datetime import date
from typing import Any, Dict, Optional

from loguru import logger

# 导入统一LLM网关
from ..llm_gateway import CallType, LLMGateway, LLMProvider, LLMRequest


class BudgetExceededError(Exception):
    """预算超限异常

    当API调用成本超过预算时抛出此异常
    """


class CostTracker:
    """成本追踪器

    白皮书依据: 第二章 2.2 Commander (慢系统)

    追踪API调用成本，实现预算控制和告警。
    成本计算公式: cost = tokens / 1,000,000 * ¥1.0

    Attributes:
        daily_budget: 日预算（元）
        monthly_budget: 月预算（元）
        daily_cost: 当日成本
        monthly_cost: 当月成本
        current_date: 当前日期（用于日成本重置）
        current_month: 当前月份（用于月成本重置）
        call_count: API调用次数

    Example:
        >>> tracker = CostTracker(daily_budget=50.0, monthly_budget=1500.0)
        >>> if tracker.can_afford(1.0):
        ...     tracker.record_cost(0.85)
        >>> print(f"今日成本: ¥{tracker.daily_cost:.2f}")
    """

    def __init__(self, daily_budget: float, monthly_budget: float):
        """初始化成本追踪器

        Args:
            daily_budget: 日预算（元），必须 > 0
            monthly_budget: 月预算（元），必须 > 0

        Raises:
            ValueError: 当预算值无效时
        """
        if daily_budget <= 0:
            raise ValueError(f"日预算必须 > 0，当前: {daily_budget}")

        if monthly_budget <= 0:
            raise ValueError(f"月预算必须 > 0，当前: {monthly_budget}")

        if daily_budget > monthly_budget:
            raise ValueError(f"日预算不能超过月预算: daily={daily_budget}, monthly={monthly_budget}")

        self.daily_budget = daily_budget
        self.monthly_budget = monthly_budget
        self.daily_cost = 0.0
        self.monthly_cost = 0.0
        self.current_date = date.today()
        self.current_month = (date.today().year, date.today().month)
        self.call_count = 0

        logger.info(f"成本追踪器初始化: 日预算=¥{daily_budget:.2f}, " f"月预算=¥{monthly_budget:.2f}")

    def can_afford(self, estimated_cost: float) -> bool:
        """检查是否可以承担成本

        Args:
            estimated_cost: 预估成本（元）

        Returns:
            bool: 是否可以承担
        """
        # 检查日期，必要时重置成本
        self._check_and_reset()

        # 检查日预算和月预算
        can_afford_daily = (self.daily_cost + estimated_cost) <= self.daily_budget
        can_afford_monthly = (self.monthly_cost + estimated_cost) <= self.monthly_budget

        if not can_afford_daily:
            logger.warning(
                f"日预算不足: 当前¥{self.daily_cost:.2f} + 预估¥{estimated_cost:.2f} " f"> 预算¥{self.daily_budget:.2f}"
            )

        if not can_afford_monthly:
            logger.warning(
                f"月预算不足: 当前¥{self.monthly_cost:.2f} + 预估¥{estimated_cost:.2f} "
                f"> 预算¥{self.monthly_budget:.2f}"
            )

        return can_afford_daily and can_afford_monthly

    def record_cost(self, cost: float):
        """记录成本

        Args:
            cost: 实际成本（元）
        """
        if cost < 0:
            raise ValueError(f"成本不能为负数: {cost}")

        # 检查日期，必要时重置成本
        self._check_and_reset()

        # 记录成本
        self.daily_cost += cost
        self.monthly_cost += cost
        self.call_count += 1

        logger.info(
            f"成本记录: +¥{cost:.4f}, "
            f"今日累计¥{self.daily_cost:.2f}/{self.daily_budget:.2f}, "
            f"本月累计¥{self.monthly_cost:.2f}/{self.monthly_budget:.2f}, "
            f"调用次数{self.call_count}"
        )

        # 检查告警阈值
        self._check_alerts()

    def _check_and_reset(self):
        """检查日期并重置成本（内部方法）"""
        today = date.today()
        current_month = (today.year, today.month)

        # 检查是否需要重置日成本
        if today != self.current_date:
            logger.info(f"日期变更: {self.current_date} -> {today}, " f"重置日成本: ¥{self.daily_cost:.2f} -> ¥0.00")
            self.daily_cost = 0.0
            self.current_date = today

        # 检查是否需要重置月成本
        if current_month != self.current_month:
            logger.info(
                f"月份变更: {self.current_month} -> {current_month}, " f"重置月成本: ¥{self.monthly_cost:.2f} -> ¥0.00"
            )
            self.monthly_cost = 0.0
            self.call_count = 0
            self.current_month = current_month

    def _check_alerts(self):
        """检查告警阈值（内部方法）"""
        # 日成本告警（80%阈值）
        daily_usage_ratio = self.daily_cost / self.daily_budget
        if daily_usage_ratio >= 0.8:
            logger.warning(
                f"⚠️ 日成本接近预算: ¥{self.daily_cost:.2f}/¥{self.daily_budget:.2f} " f"({daily_usage_ratio:.1%})"
            )

        # 月成本告警（80%阈值）
        monthly_usage_ratio = self.monthly_cost / self.monthly_budget
        if monthly_usage_ratio >= 0.8:
            logger.warning(
                f"⚠️ 月成本接近预算: ¥{self.monthly_cost:.2f}/¥{self.monthly_budget:.2f} "
                f"({monthly_usage_ratio:.1%})"
            )

    def get_status(self) -> Dict[str, Any]:
        """获取成本追踪状态

        Returns:
            Dict: 状态信息
        """
        self._check_and_reset()

        return {
            "daily_budget": self.daily_budget,
            "monthly_budget": self.monthly_budget,
            "daily_cost": self.daily_cost,
            "monthly_cost": self.monthly_cost,
            "daily_usage_ratio": self.daily_cost / self.daily_budget,
            "monthly_usage_ratio": self.monthly_cost / self.monthly_budget,
            "call_count": self.call_count,
            "current_date": str(self.current_date),
            "current_month": f"{self.current_month[0]}-{self.current_month[1]:02d}",
        }

    def reset_daily_cost(self):
        """手动重置日成本（用于测试）"""
        logger.info(f"手动重置日成本: ¥{self.daily_cost:.2f} -> ¥0.00")
        self.daily_cost = 0.0
        self.current_date = date.today()

    def reset_monthly_cost(self):
        """手动重置月成本（用于测试）"""
        logger.info(f"手动重置月成本: ¥{self.monthly_cost:.2f} -> ¥0.00")
        self.monthly_cost = 0.0
        self.call_count = 0
        self.current_month = (date.today().year, date.today().month)


class Commander:
    """Commander慢系统

    白皮书依据: 第二章 2.2 Commander (慢系统 - 云端增强)

    Commander是MIA的战略分析系统，负责研报阅读和战略生成。
    使用云端大模型（Qwen3-Next-80B）进行深度分析，成本控制在¥1.0/M tokens。

    核心特性:
    - 研报阅读和分析
    - 交易战略生成
    - 成本追踪和预算控制
    - Redis状态同步

    Attributes:
        api_client: Qwen-Next-80B API客户端
        cost_tracker: 成本追踪器
        redis_client: Redis客户端
        daily_budget: 日预算（元）
        monthly_budget: 月预算（元）

    Performance:
        分析延迟: < 30秒
        单次成本: < ¥1.0
        日成本: < ¥50
        月成本: < ¥1500

    Example:
        >>> commander = Commander(api_key="sk-xxx")
        >>> await commander.initialize()
        >>> result = await commander.analyze_report(report_text)
        >>> print(f"分析结果: {result['summary']}")
    """

    def __init__(  # pylint: disable=too-many-positional-arguments
        self,
        api_key: str,
        redis_host: str = "localhost",
        redis_port: int = 6379,
        daily_budget: float = 50.0,
        monthly_budget: float = 1500.0,
    ):
        """初始化Commander

        白皮书依据: 第二章 2.2

        Args:
            api_key: API密钥（Qwen-Next-80B）
            redis_host: Redis主机地址
            redis_port: Redis端口
            daily_budget: 日预算（元），默认¥50
            monthly_budget: 月预算（元），默认¥1500

        Raises:
            ValueError: 当参数无效时
        """
        # 参数验证
        if not api_key or not api_key.startswith("sk-"):
            raise ValueError("无效的API密钥格式")

        if daily_budget <= 0:
            raise ValueError(f"日预算必须 > 0，当前: {daily_budget}")

        if monthly_budget <= 0:
            raise ValueError(f"月预算必须 > 0，当前: {monthly_budget}")

        # 初始化属性
        self.llm_gateway = None  # 使用统一LLM网关替代直接API调用
        self.cost_tracker = CostTracker(daily_budget, monthly_budget)
        self.redis_client = None
        self.daily_budget = daily_budget
        self.monthly_budget = monthly_budget

        # 存储配置
        self._api_key = api_key
        self._redis_host = redis_host
        self._redis_port = redis_port

        logger.info(f"Commander初始化: daily_budget=¥{daily_budget:.2f}, " f"monthly_budget=¥{monthly_budget:.2f}")

    async def initialize(self):
        """异步初始化组件

        白皮书依据: 第二章 2.2

        按顺序初始化：
        1. 连接Redis
        2. 初始化统一LLM网关

        Raises:
            RuntimeError: 当初始化失败时
        """
        try:
            # 1. 连接Redis
            await self._connect_redis(self._redis_host, self._redis_port)

            # 2. 初始化统一LLM网关
            await self._init_llm_gateway()

            logger.info("Commander初始化完成")

        except Exception as e:
            logger.error(f"Commander初始化失败: {e}")
            raise RuntimeError(f"Commander初始化失败: {e}") from e

    async def _init_llm_gateway(self):
        """初始化统一LLM网关（内部方法）

        白皮书依据: 第二章 2.2 + 统一LLM控制架构

        使用统一LLM网关替代直接API调用，确保所有LLM调用都经过：
        - 记忆系统增强
        - 防幻觉检测
        - 成本控制
        - 审计日志

        Raises:
            RuntimeError: 当网关初始化失败时
        """
        logger.info("初始化统一LLM网关")

        try:
            # 创建LLM网关实例
            self.llm_gateway = LLMGateway(redis_client=self.redis_client)

            logger.info("统一LLM网关初始化成功")

        except Exception as e:
            logger.error(f"LLM网关初始化失败: {e}")
            raise RuntimeError(f"LLM网关初始化失败: {e}") from e

    async def _connect_redis(self, host: str, port: int):
        """连接Redis（内部方法）

        白皮书依据: 第二章 2.2

        建立Redis连接，用于战略状态同步

        Args:
            host: Redis主机地址
            port: Redis端口

        Raises:
            ConnectionError: 当Redis连接失败时
        """
        logger.info(f"连接Redis: {host}:{port}")

        try:
            import redis.asyncio as redis  # pylint: disable=import-outside-toplevel

            # 创建Redis连接池
            self.redis_client = redis.Redis(
                host=host,
                port=port,
                db=0,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
                health_check_interval=30,
            )

            # 测试连接
            await self.redis_client.ping()
            logger.info("Redis连接成功")

        except ImportError:
            logger.warning("redis库未安装，使用兼容模式")
            # 兼容模式：创建模拟客户端
            await asyncio.sleep(0.02)
            self.redis_client = {"host": host, "port": port, "connected": True, "mode": "compatible"}
            logger.info("Redis连接成功（兼容模式）")

        except Exception as e:
            logger.error(f"Redis连接失败: {e}")
            raise ConnectionError(f"Redis连接失败: {e}") from e

    def get_status(self) -> Dict[str, Any]:
        """获取Commander状态

        Returns:
            Dict: 状态信息
        """
        status = {
            "llm_gateway_initialized": self.llm_gateway is not None,
            "redis_connected": self.redis_client is not None,
            "cost_tracker": self.cost_tracker.get_status(),
        }

        return status

    async def close(self):
        """关闭Commander并清理资源"""
        try:
            if self.redis_client and hasattr(self.redis_client, "close"):
                await self.redis_client.close()
                logger.info("Redis连接已关闭")

            if self.llm_gateway:
                # LLM网关暂时不需要特殊关闭逻辑
                logger.info("LLM网关已关闭")

            logger.info("Commander已关闭")

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"关闭Commander时出错: {e}")

    async def analyze_report(self, report_text: str) -> Dict[str, Any]:
        """分析研报

        白皮书依据: 第二章 2.2 Commander (慢系统)

        使用Qwen-Next-80B分析研报，提取关键信息并生成结构化分析报告。

        Args:
            report_text: 研报文本内容

        Returns:
            Dict: 分析结果，包含以下字段：
                - industry: 行业分类
                - company: 公司名称
                - rating: 评级（买入/持有/卖出）
                - target_price: 目标价
                - key_points: 关键观点列表
                - risks: 风险提示列表
                - summary: 摘要
                - tokens_used: 使用的token数量
                - cost: 本次分析成本（元）

        Raises:
            ValueError: 当研报文本为空时
            BudgetExceededError: 当预算超限时
            RuntimeError: 当API调用失败时

        Example:
            >>> commander = Commander(api_key="sk-xxx")
            >>> await commander.initialize()
            >>> result = await commander.analyze_report(report_text)
            >>> print(f"行业: {result['industry']}, 评级: {result['rating']}")
        """
        if not report_text or not report_text.strip():
            raise ValueError("研报文本不能为空")

        # 估算成本（假设每1000字符约250 tokens）
        estimated_tokens = len(report_text) // 4
        estimated_cost = estimated_tokens / 1_000_000 * 1.0

        # 检查预算
        if not self.cost_tracker.can_afford(estimated_cost):
            logger.error(
                f"预算不足: 预估成本¥{estimated_cost:.4f}, "
                f"日剩余¥{self.daily_budget - self.cost_tracker.daily_cost:.2f}, "
                f"月剩余¥{self.monthly_budget - self.cost_tracker.monthly_cost:.2f}"
            )
            raise BudgetExceededError(f"预算不足，无法分析研报。预估成本: ¥{estimated_cost:.4f}")

        logger.info(f"开始分析研报，长度: {len(report_text)}字符，预估成本: ¥{estimated_cost:.4f}")

        try:
            # 调用统一LLM网关进行分析
            result = await self._call_llm_gateway_for_analysis(report_text)

            # 计算实际成本
            actual_cost = self._calculate_cost(result.get("tokens_used", estimated_tokens))

            # 记录成本
            self.cost_tracker.record_cost(actual_cost)

            # 添加成本信息到结果
            result["cost"] = actual_cost

            logger.info(
                f"研报分析完成: 行业={result.get('industry', 'N/A')}, "
                f"评级={result.get('rating', 'N/A')}, "
                f"实际成本=¥{actual_cost:.4f}"
            )

            return result

        except Exception as e:
            logger.error(f"研报分析失败: {e}")
            raise RuntimeError(f"研报分析失败: {e}") from e

    async def _call_llm_gateway_for_analysis(self, report_text: str) -> Dict[str, Any]:
        """使用统一LLM网关进行研报分析（内部方法）

        Args:
            report_text: 研报文本

        Returns:
            Dict: 分析结果

        Raises:
            RuntimeError: 当分析失败时
        """
        if not self.llm_gateway:
            raise RuntimeError("LLM网关未初始化")

        try:
            # 构建LLM请求
            request = LLMRequest(
                call_type=CallType.RESEARCH_ANALYSIS,
                provider=LLMProvider.QWEN_CLOUD,
                model="qwen-max",
                messages=[{"role": "user", "content": self._build_analysis_prompt(report_text)}],
                system_prompt="你是一个专业的金融分析师，擅长分析研究报告并提取关键信息。",
                max_tokens=2000,
                temperature=0.3,
                timeout=60.0,
                use_memory=True,
                enable_hallucination_filter=True,
                caller_module="commander",
                caller_function="analyze_report",
                business_context={
                    "analysis_type": "research_report",
                    "report_length": len(report_text),
                    "timestamp": time.time(),
                },
            )

            # 调用统一LLM网关
            response = await self.llm_gateway.call_llm(request)

            if not response.success:
                raise RuntimeError(f"LLM调用失败: {response.error_message}")

            # 解析JSON响应
            try:
                result = json.loads(response.content)
            except json.JSONDecodeError as e:
                logger.error(f"JSON解析失败: {e}")
                # 返回默认结果
                result = {
                    "industry": "未识别",
                    "company": "未识别",
                    "rating": "未提及",
                    "target_price": None,
                    "key_points": ["分析失败"],
                    "risks": ["解析错误"],
                    "summary": "研报分析失败",
                }

            # 添加token使用信息
            result["tokens_used"] = response.tokens_used

            logger.debug(f"研报分析成功: 成本¥{response.cost:.4f}")
            return result

        except Exception as e:
            logger.error(f"LLM网关分析失败: {e}")
            raise RuntimeError(f"LLM网关分析失败: {e}") from e

    def _build_analysis_prompt(self, report_text: str) -> str:
        """构建研报分析提示词（内部方法）

        Args:
            report_text: 研报文本

        Returns:
            str: 格式化的提示词
        """
        prompt = f"""请分析以下研究报告，提取关键信息并以JSON格式返回。

研究报告内容：
{report_text[:5000]}  # 限制长度避免超过token限制

请按以下JSON格式返回分析结果：
{{
    "industry": "行业分类（如：科技、金融、医药等）",
    "company": "公司名称",
    "rating": "评级（买入/增持/持有/减持/卖出）",
    "target_price": 目标价（数字，如果没有则为null）,
    "key_points": [
        "关键观点1",
        "关键观点2",
        "关键观点3"
    ],
    "risks": [
        "风险提示1",
        "风险提示2"
    ],
    "summary": "简要摘要（100字以内）"
}}

注意：
1. 所有字段都必须填写
2. 如果某些信息在报告中未提及，请填写"未提及"或null
3. 确保返回的是有效的JSON格式
"""
        return prompt

    def _calculate_cost(self, tokens_used: int) -> float:
        """计算API调用成本（内部方法）

        白皮书依据: 第二章 2.2 - 成本计算公式: cost = tokens / 1,000,000 * ¥1.0

        Args:
            tokens_used: 使用的token数量

        Returns:
            float: 成本（元）
        """
        cost = tokens_used / 1_000_000 * 1.0
        return cost

    async def generate_strategy(
        self, market_state: Dict[str, Any], strategy_key: str = "strategy_state"
    ) -> Dict[str, Any]:
        """生成交易战略

        白皮书依据: 第二章 2.2 Commander (慢系统)

        基于市场状态分析生成交易战略，考虑市场情绪、技术面、基本面等因素。

        Args:
            market_state: 市场状态信息，包含：
                - market_sentiment: 市场情绪 (0-1)
                - technical_indicators: 技术指标字典
                - fundamental_data: 基本面数据字典
                - recent_reports: 最近的研报分析结果列表
            strategy_key: Redis中存储战略的键名，默认"strategy_state"

        Returns:
            Dict: 生成的交易战略，包含以下字段：
                - strategy_type: 战略类型（momentum/mean_reversion/defensive等）
                - risk_level: 风险等级（low/medium/high）
                - position_limit: 仓位限制 (0-1)
                - target_sectors: 目标行业列表
                - avoid_sectors: 规避行业列表
                - reasoning: 战略理由
                - valid_until: 有效期（时间戳）
                - tokens_used: 使用的token数量
                - cost: 本次生成成本（元）

        Raises:
            ValueError: 当市场状态数据无效时
            BudgetExceededError: 当预算超限时
            RuntimeError: 当战略生成失败时

        Example:
            >>> commander = Commander(api_key="sk-xxx")
            >>> await commander.initialize()
            >>> market_state = {
            ...     "market_sentiment": 0.7,
            ...     "technical_indicators": {"rsi": 65, "macd": "bullish"},
            ...     "fundamental_data": {"pe_ratio": 15.5},
            ...     "recent_reports": [...]
            ... }
            >>> strategy = await commander.generate_strategy(market_state)
            >>> print(f"战略类型: {strategy['strategy_type']}")
        """
        # 验证输入
        if not market_state or not isinstance(market_state, dict):
            raise ValueError("市场状态数据无效")

        # 估算成本
        estimated_tokens = 2000  # 战略生成通常需要较多token
        estimated_cost = estimated_tokens / 1_000_000 * 1.0

        # 检查预算
        if not self.cost_tracker.can_afford(estimated_cost):
            logger.error(
                f"预算不足: 预估成本¥{estimated_cost:.4f}, "
                f"日剩余¥{self.daily_budget - self.cost_tracker.daily_cost:.2f}"
            )
            raise BudgetExceededError(f"预算不足，无法生成战略。预估成本: ¥{estimated_cost:.4f}")

        logger.info(f"开始生成交易战略，市场情绪: {market_state.get('market_sentiment', 'N/A')}")

        try:
            # 调用统一LLM网关生成战略
            strategy = await self._call_llm_gateway_for_strategy(market_state)

            # 计算实际成本
            actual_cost = self._calculate_cost(strategy.get("tokens_used", estimated_tokens))

            # 记录成本
            self.cost_tracker.record_cost(actual_cost)

            # 添加成本信息
            strategy["cost"] = actual_cost

            # 写入Redis
            await self._write_strategy_to_redis(strategy, strategy_key)

            # 通知Soldier（通过Redis发布订阅）
            await self._notify_soldier_strategy_update(strategy_key)

            logger.info(
                f"战略生成完成: 类型={strategy.get('strategy_type', 'N/A')}, "
                f"风险等级={strategy.get('risk_level', 'N/A')}, "
                f"实际成本=¥{actual_cost:.4f}"
            )

            return strategy

        except BudgetExceededError:
            raise
        except Exception as e:
            logger.error(f"战略生成失败: {e}")
            # 尝试使用上一次的战略
            try:
                last_strategy = await self._get_last_strategy_from_redis(strategy_key)
                if last_strategy:
                    logger.warning("使用上一次的战略")
                    return last_strategy
            except Exception as redis_error:  # pylint: disable=broad-exception-caught
                logger.error(f"无法获取上一次的战略: {redis_error}")

            raise RuntimeError(f"战略生成失败: {e}") from e

    async def _call_llm_gateway_for_strategy(self, market_state: Dict[str, Any]) -> Dict[str, Any]:
        """使用统一LLM网关生成交易战略（内部方法）

        Args:
            market_state: 市场状态信息

        Returns:
            Dict: 生成的战略

        Raises:
            RuntimeError: 当战略生成失败时
        """
        if not self.llm_gateway:
            raise RuntimeError("LLM网关未初始化")

        try:
            # 构建LLM请求
            request = LLMRequest(
                call_type=CallType.STRATEGY_ANALYSIS,
                provider=LLMProvider.QWEN_CLOUD,
                model="qwen-max",
                messages=[{"role": "user", "content": self._build_strategy_prompt(market_state)}],
                system_prompt="你是一个专业的量化交易策略师，擅长基于市场分析生成交易战略。",
                max_tokens=2000,
                temperature=0.4,
                timeout=60.0,
                use_memory=True,
                enable_hallucination_filter=True,
                caller_module="commander",
                caller_function="generate_strategy",
                business_context={
                    "strategy_generation": True,
                    "market_sentiment": market_state.get("market_sentiment", 0.5),
                    "timestamp": time.time(),
                },
            )

            # 调用统一LLM网关
            response = await self.llm_gateway.call_llm(request)

            if not response.success:
                raise RuntimeError(f"LLM调用失败: {response.error_message}")

            # 解析JSON响应
            try:
                result = json.loads(response.content)
            except json.JSONDecodeError as e:
                logger.error(f"JSON解析失败: {e}")
                # 返回默认战略
                result = {
                    "strategy_type": "balanced",
                    "risk_level": "medium",
                    "position_limit": 0.5,
                    "target_sectors": ["科技"],
                    "avoid_sectors": [],
                    "reasoning": "战略生成失败，使用默认平衡策略",
                }

            # 添加token使用信息和有效期
            result["tokens_used"] = response.tokens_used
            if "valid_until" not in result:
                result["valid_until"] = time.time() + 86400  # 24小时有效

            logger.debug(f"战略生成成功: 成本¥{response.cost:.4f}")
            return result

        except Exception as e:
            logger.error(f"LLM网关战略生成失败: {e}")
            raise RuntimeError(f"LLM网关战略生成失败: {e}") from e

    def _build_strategy_prompt(self, market_state: Dict[str, Any]) -> str:
        """构建战略生成提示词（内部方法）

        Args:
            market_state: 市场状态信息

        Returns:
            str: 格式化的提示词
        """
        market_sentiment = market_state.get("market_sentiment", 0.5)
        technical_indicators = market_state.get("technical_indicators", {})
        fundamental_data = market_state.get("fundamental_data", {})
        recent_reports = market_state.get("recent_reports", [])

        prompt = f"""请基于以下市场分析生成交易战略，以JSON格式返回。

市场状态：
- 市场情绪: {market_sentiment:.2f} (0=极度悲观, 1=极度乐观)
- 技术指标: {json.dumps(technical_indicators, ensure_ascii=False)}
- 基本面数据: {json.dumps(fundamental_data, ensure_ascii=False)}
- 最近研报数量: {len(recent_reports)}

请按以下JSON格式返回交易战略：
{{
    "strategy_type": "战略类型（momentum/mean_reversion/defensive/balanced）",
    "risk_level": "风险等级（low/medium/high）",
    "position_limit": 仓位限制（0-1之间的数字，如0.6表示最多60%仓位）,
    "target_sectors": [
        "目标行业1",
        "目标行业2"
    ],
    "avoid_sectors": [
        "规避行业1"
    ],
    "reasoning": "战略理由（200字以内）"
}}

战略类型说明：
- momentum: 动量策略，适合趋势明显的市场
- mean_reversion: 均值回归策略，适合震荡市场
- defensive: 防御策略，适合市场不确定性高的时期
- balanced: 平衡策略，适合市场方向不明确时

注意：
1. 根据市场情绪和技术指标选择合适的战略类型
2. 风险等级应与市场波动性相匹配
3. 仓位限制应考虑市场风险
4. 确保返回的是有效的JSON格式
"""
        return prompt

    async def _write_strategy_to_redis(self, strategy: Dict[str, Any], strategy_key: str):
        """将战略写入Redis（内部方法）

        Args:
            strategy: 战略数据
            strategy_key: Redis键名

        Raises:
            RuntimeError: 当Redis写入失败时
        """
        try:
            # 检查Redis客户端类型
            if isinstance(self.redis_client, dict) and self.redis_client.get("mode") == "compatible":
                # 兼容模式：模拟写入
                logger.info(f"兼容模式：模拟写入战略到Redis key={strategy_key}")
                await asyncio.sleep(0.01)
                return

            # 真实Redis写入
            strategy_json = json.dumps(strategy, ensure_ascii=False)
            await self.redis_client.set(strategy_key, strategy_json)

            # 设置过期时间（48小时）
            await self.redis_client.expire(strategy_key, 172800)

            logger.info(f"战略已写入Redis: key={strategy_key}")

        except Exception as e:
            logger.error(f"Redis写入失败: {e}")
            raise RuntimeError(f"Redis写入失败: {e}") from e

    async def _notify_soldier_strategy_update(self, strategy_key: str):
        """通知Soldier战略已更新（内部方法）

        使用Redis发布订阅机制通知Soldier

        Args:
            strategy_key: 战略键名

        Raises:
            RuntimeError: 当通知失败时
        """
        try:
            # 检查Redis客户端类型
            if isinstance(self.redis_client, dict) and self.redis_client.get("mode") == "compatible":
                # 兼容模式：模拟通知
                logger.info("兼容模式：模拟通知Soldier战略更新")
                await asyncio.sleep(0.01)
                return

            # 真实Redis发布
            message = json.dumps({"type": "strategy_update", "strategy_key": strategy_key, "timestamp": time.time()})

            await self.redis_client.publish("soldier_notifications", message)

            logger.info("已通知Soldier战略更新")

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.warning(f"通知Soldier失败: {e}")
            # 通知失败不应该阻止战略生成

    async def _get_last_strategy_from_redis(self, strategy_key: str) -> Optional[Dict[str, Any]]:
        """从Redis获取上一次的战略（内部方法）

        Args:
            strategy_key: 战略键名

        Returns:
            Dict: 上一次的战略，如果不存在则返回None
        """
        try:
            # 检查Redis客户端类型
            if isinstance(self.redis_client, dict) and self.redis_client.get("mode") == "compatible":
                # 兼容模式：返回None
                return None

            # 真实Redis读取
            strategy_json = await self.redis_client.get(strategy_key)

            if strategy_json:
                return json.loads(strategy_json)

            return None

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"从Redis读取战略失败: {e}")
            return None
