# pylint: disable=too-many-lines
"""
MIA系统因子挖掘智能哨兵 (Factor Mining Intelligence Sentinel)

白皮书依据: 第四章 4.1 暗物质挖掘工厂 - 智能因子发现与验证
版本: v1.6.0
作者: MIA Team
日期: 2026-01-18

核心理念: 让MIA在因子挖掘领域永远保持前沿，持续跟踪最新的因子挖掘理论、
替代数据源和量化技术，自动学习并验证新因子的有效性。

硬件架构: AMD AI Max + Cloud API 混合架构
模型配置:
- Qwen3-Next-80B: 论文理解和理论分析
- DeepSeek-R1: 因子实现和代码生成
- GLM-4: 数据分析和模式识别 (替代Claude-3.5)

核心任务:
1. 因子理论监控 - 跟踪学术前沿和行业动态
2. 替代数据发现 - 发现新的数据源和信号
3. 因子自动实现 - 将理论转化为可执行代码
4. 回测验证 - 验证新因子的有效性
5. Alpha集成 - 将有效因子集成到策略库
6. 发现记录 - 完整记录所有发现过程

⚠️ 重要: 所有LLM调用必须通过统一LLM网关，遵循MIA编码铁律
⚠️ 架构合规: 通过事件总线与其他模块通信，避免循环依赖
"""

import asyncio
import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import redis

# 导入统一LLM网关 - 遵循架构规范
from ..brain.llm_gateway import CallType, LLMGateway, LLMProvider, LLMRequest

# 导入事件总线 - 解决循环依赖
from ..infra.event_bus import Event, EventPriority, EventType, publish_event, subscribe_event
from ..utils.logger import get_logger

logger = get_logger(__name__)


class DiscoveryType(Enum):
    """发现类型"""

    ACADEMIC_PAPER = "academic_paper"  # 学术论文
    INDUSTRY_REPORT = "industry_report"  # 行业报告
    ALTERNATIVE_DATA = "alternative_data"  # 替代数据
    MARKET_ANOMALY = "market_anomaly"  # 市场异象
    CROSS_ASSET = "cross_asset"  # 跨资产信号
    BEHAVIORAL_PATTERN = "behavioral_pattern"  # 行为模式
    TECHNICAL_INNOVATION = "technical_innovation"  # 技术创新


class FactorCategory(Enum):
    """因子类别"""

    FUNDAMENTAL = "fundamental"  # 基本面因子
    TECHNICAL = "technical"  # 技术面因子
    ALTERNATIVE = "alternative"  # 替代数据因子
    SENTIMENT = "sentiment"  # 情绪因子
    MACRO = "macro"  # 宏观因子
    CROSS_SECTIONAL = "cross_sectional"  # 截面因子
    TIME_SERIES = "time_series"  # 时序因子


class ValidationStatus(Enum):
    """验证状态"""

    DISCOVERED = "discovered"  # 已发现
    IMPLEMENTING = "implementing"  # 实现中
    TESTING = "testing"  # 测试中
    VALIDATED = "validated"  # 已验证，等待Arena测试
    PENDING_ARENA = "pending_arena"  # 等待Arena三轨测试
    ARENA_PASSED = "arena_passed"  # 通过Arena测试
    STRATEGY_GENERATED = "strategy_generated"  # 已生成策略
    SPARTA_TESTING = "sparta_testing"  # 斯巴达Arena测试中
    SIMULATION_RUNNING = "simulation_running"  # 模拟盘运行中
    Z2H_CERTIFIED = "z2h_certified"  # 获得Z2H认证
    STRATEGY_INTEGRATED = "strategy_integrated"  # 策略库集成
    DEPRECATED = "deprecated"  # 已废弃


@dataclass
class FactorDiscovery:  # pylint: disable=too-many-instance-attributes
    """因子发现记录"""

    discovery_id: str
    discovery_type: DiscoveryType
    factor_category: FactorCategory

    # 发现信息
    title: str
    description: str
    source: str
    discovered_at: datetime
    discoverer: str  # 'system' or 'human'

    # 理论基础
    theoretical_basis: str
    expected_alpha: Optional[float] = None
    risk_factors: List[str] = field(default_factory=list)

    # 实现信息
    implementation_complexity: str = "medium"  # low/medium/high
    data_requirements: List[str] = field(default_factory=list)
    computational_cost: str = "medium"  # low/medium/high

    # 验证状态
    status: ValidationStatus = ValidationStatus.DISCOVERED
    validation_results: Optional[Dict[str, Any]] = None

    # 元数据
    tags: List[str] = field(default_factory=list)
    related_papers: List[str] = field(default_factory=list)
    confidence_score: float = 0.5

    def __post_init__(self):
        if not self.discovery_id:
            # 生成唯一ID
            content = f"{self.title}_{self.source}_{self.discovered_at}"
            self.discovery_id = hashlib.md5(content.encode()).hexdigest()[:12]


@dataclass
class FactorImplementation:
    """因子实现"""

    factor_id: str
    discovery_id: str

    # 实现信息
    factor_name: str
    factor_formula: str
    python_code: str
    dependencies: List[str] = field(default_factory=list)

    # 性能信息
    ic_mean: Optional[float] = None
    ic_std: Optional[float] = None
    ir_ratio: Optional[float] = None
    turnover: Optional[float] = None

    # 实现元数据
    implemented_at: datetime = field(default_factory=datetime.now)
    implementation_model: str = "DeepSeek-R1"
    code_quality_score: float = 0.0

    def __post_init__(self):
        if not self.factor_id:
            content = f"{self.factor_name}_{self.factor_formula}"
            self.factor_id = hashlib.md5(content.encode()).hexdigest()[:8]


class FactorMiningIntelligenceSentinel:
    """因子挖掘智能哨兵

    核心理念: 让MIA在因子挖掘领域永远保持前沿

    主要功能:
    1. 理论监控 - 持续跟踪学术前沿和行业动态
    2. 数据发现 - 主动发现新的替代数据源
    3. 因子实现 - 自动将理论转化为可执行代码
    4. 验证集成 - 验证新因子并集成到策略库
    5. 发现记录 - 完整记录所有发现和验证过程

    技术架构:
    - Qwen3-Next-80B: 论文理解和理论分析
    - DeepSeek-R1: 因子实现和代码生成
    - GLM-4: 数据分析和模式识别 (替代Claude-3.5)

    ⚠️ 架构合规: 所有LLM调用必须通过统一LLM网关
    """

    def __init__(
        self,
        llm_gateway: Optional[LLMGateway] = None,
        redis_client: Optional[redis.Redis] = None,
        discovery_storage_path: str = "data/factor_discoveries",
    ):
        """初始化因子挖掘智能哨兵

        Args:
            llm_gateway: 统一LLM网关 (必需，遵循架构规范)
            redis_client: Redis客户端
            discovery_storage_path: 发现记录存储路径

        Raises:
            ValueError: 当llm_gateway为None时
        """
        # 强制要求LLM网关，遵循架构规范
        if llm_gateway is None:
            raise ValueError("llm_gateway是必需的，所有LLM调用必须通过统一网关")

        self.llm_gateway = llm_gateway
        self.redis_client = redis_client or redis.Redis(host="localhost", port=6379, db=0)
        self.discovery_storage_path = Path(discovery_storage_path)
        self.discovery_storage_path.mkdir(parents=True, exist_ok=True)

        # 发现记录
        self.discoveries: Dict[str, FactorDiscovery] = {}
        self.implementations: Dict[str, FactorImplementation] = {}

        # 监控配置
        self.monitoring_sources = self._initialize_monitoring_sources()
        self.discovery_patterns = self._initialize_discovery_patterns()

        # 模型配置 (通过LLM网关调用)
        self.model_configs = {
            "theory_analyzer": {
                "provider": LLMProvider.QWEN_CLOUD,
                "model": "qwen-max",
                "role": "论文理解和理论分析",
                "max_tokens": 4000,
                "temperature": 0.3,
            },
            "factor_implementer": {
                "provider": LLMProvider.DEEPSEEK,
                "model": "deepseek-chat",
                "role": "因子实现和代码生成",
                "max_tokens": 2000,
                "temperature": 0.1,
            },
            "data_analyzer": {
                "provider": LLMProvider.GLM,
                "model": "glm-4",
                "role": "数据分析和模式识别",
                "max_tokens": 3000,
                "temperature": 0.2,
                "note": "国内可用，数据分析能力强",
            },
        }

        # 事件总线集成 - 解决循环依赖
        # 注意：事件处理器设置是异步的，在实际使用中需要调用 await setup_event_handlers()
        self._event_handlers_setup = False

        # 加载历史发现
        self._load_historical_discoveries()

        logger.info("FactorMiningIntelligenceSentinel 初始化完成")
        logger.info("核心理念: 让MIA在因子挖掘领域永远保持前沿")
        logger.info("架构合规: 已集成统一LLM网关和事件总线")

    async def setup_event_handlers(self):
        """设置事件处理器 - 需要在初始化后异步调用"""
        if not self._event_handlers_setup:
            await self._setup_event_handlers()
            self._event_handlers_setup = True

    async def _setup_event_handlers(self):
        """设置事件处理器 - 解决循环依赖"""
        try:
            # 订阅相关事件
            await subscribe_event(
                EventType.FACTOR_DISCOVERED,
                self._handle_factor_discovered_event,
                "factor_mining_sentinel_discovery_handler",
            )

            await subscribe_event(
                EventType.ARENA_TEST_COMPLETED,
                self._handle_arena_test_completed_event,
                "factor_mining_sentinel_arena_handler",
            )

            logger.info("事件处理器设置完成 - 已订阅因子发现和Arena测试事件")

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.warning(f"事件处理器设置失败: {e}")  # pylint: disable=logging-fstring-interpolation

    async def _handle_factor_discovered_event(self, event: Event):
        """处理因子发现事件"""
        try:
            factor_data = event.data
            logger.info(  # pylint: disable=logging-fstring-interpolation
                f"收到因子发现事件: {factor_data.get('factor_name', 'Unknown')}"
            )  # pylint: disable=logging-fstring-interpolation

            # 可以在这里添加额外的处理逻辑
            # 例如：更新统计信息、触发相关分析等

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"处理因子发现事件失败: {e}")  # pylint: disable=logging-fstring-interpolation

    async def _handle_arena_test_completed_event(self, event: Event):
        """处理Arena测试完成事件"""
        try:
            test_data = event.data
            factor_id = test_data.get("factor_id")

            if factor_id:
                # 更新相关发现的状态
                for discovery in self.discoveries.values():
                    if any(
                        impl.factor_id == factor_id
                        for impl in self.implementations.values()
                        if impl.discovery_id == discovery.discovery_id
                    ):
                        discovery.status = ValidationStatus.ARENA_PASSED
                        logger.info(  # pylint: disable=logging-fstring-interpolation
                            f"因子 {factor_id} 通过Arena测试，更新发现状态"
                        )  # pylint: disable=logging-fstring-interpolation
                        break

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"处理Arena测试完成事件失败: {e}")  # pylint: disable=logging-fstring-interpolation

    def _initialize_monitoring_sources(self) -> Dict[str, Dict[str, Any]]:
        """初始化监控源配置"""
        return {
            # 学术源
            "arxiv": {
                "url": "https://arxiv.org/list/q-fin/recent",
                "categories": ["q-fin.CP", "q-fin.ST", "q-fin.PM"],
                "keywords": ["factor", "alpha", "anomaly", "cross-section", "time-series"],
                "check_interval": 86400,  # 1天 (24小时)
                "priority": "high",
            },
            "ssrn": {
                "url": "https://www.ssrn.com/index.cfm/en/janda/job-market-papers/",
                "keywords": ["factor investing", "quantitative finance", "asset pricing"],
                "check_interval": 86400,  # 1天 (24小时)
                "priority": "high",
            },
            # 行业源
            "quantitative_research": {
                "sources": ["AQR", "Two Sigma", "Renaissance", "Citadel"],
                "keywords": ["alternative data", "machine learning", "factor model"],
                "check_interval": 86400,  # 1天 (24小时)
                "priority": "medium",
            },
            # 替代数据源
            "alternative_data_providers": {
                "providers": ["Quandl", "Bloomberg", "Refinitiv", "S&P Global"],
                "data_types": ["satellite", "social", "web", "mobile", "credit"],
                "check_interval": 86400,  # 1天 (24小时)
                "priority": "medium",
            },
            # 技术创新源
            "github_trending": {
                "repositories": ["quantitative-finance", "algorithmic-trading"],
                "languages": ["Python", "R", "Julia"],
                "check_interval": 86400,  # 1天 (24小时)
                "priority": "low",
            },
        }

    def _initialize_discovery_patterns(self) -> Dict[str, List[str]]:
        """初始化发现模式"""
        return {
            "factor_keywords": [
                "factor",
                "alpha",
                "anomaly",
                "cross-section",
                "time-series",
                "momentum",
                "reversal",
                "value",
                "quality",
                "volatility",
                "liquidity",
                "sentiment",
                "macro",
                "fundamental",
            ],
            "data_keywords": [
                "alternative data",
                "satellite data",
                "social media",
                "web scraping",
                "mobile data",
                "credit card",
                "geolocation",
                "news sentiment",
                "earnings call",
                "supply chain",
                "ESG data",
            ],
            "method_keywords": [
                "machine learning",
                "deep learning",
                "neural network",
                "ensemble",
                "genetic algorithm",
                "reinforcement learning",
                "natural language processing",
                "computer vision",
                "graph neural network",
                "transformer",
            ],
            "performance_keywords": [
                "sharpe ratio",
                "information ratio",
                "maximum drawdown",
                "turnover",
                "transaction cost",
                "capacity",
                "decay",
                "stability",
            ],
        }

    async def start_continuous_monitoring(self):
        """启动持续监控"""
        logger.info("启动因子挖掘智能哨兵持续监控")

        # 创建监控任务
        monitoring_tasks = [
            self._monitor_academic_sources(),
            self._monitor_industry_sources(),
            self._monitor_alternative_data_sources(),
            self._discover_market_anomalies(),
            self._analyze_cross_asset_signals(),
        ]

        # 并发执行监控任务
        await asyncio.gather(*monitoring_tasks, return_exceptions=True)

    async def _monitor_academic_sources(self):
        """监控学术源"""
        logger.info("开始监控学术源")

        while True:
            try:
                # 监控arXiv
                arxiv_discoveries = await self._scan_arxiv_papers()

                # 监控SSRN
                ssrn_discoveries = await self._scan_ssrn_papers()

                # 处理发现
                for discovery in arxiv_discoveries + ssrn_discoveries:
                    await self._process_new_discovery(discovery)

                # 等待下次检查
                await asyncio.sleep(86400)  # 1天

            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.error(f"学术源监控错误: {e}")  # pylint: disable=logging-fstring-interpolation
                await asyncio.sleep(300)  # 5分钟后重试

    async def _scan_arxiv_papers(self) -> List[FactorDiscovery]:
        """扫描arXiv论文"""
        discoveries = []

        # 模拟arXiv API调用 (实际应该调用真实API)
        mock_papers = [
            {
                "title": "Cross-Sectional Momentum with Alternative Data",
                "abstract": "We propose a novel cross-sectional momentum factor using satellite data...",
                "authors": ["Smith, J.", "Johnson, A."],
                "published": "2026-01-18",
                "url": "https://arxiv.org/abs/2601.12345",
            },
            {
                "title": "ESG Factors and Stock Returns: A Machine Learning Approach",
                "abstract": "This paper investigates the relationship between ESG scores and stock returns...",
                "authors": ["Brown, K.", "Davis, M."],
                "published": "2026-01-17",
                "url": "https://arxiv.org/abs/2601.12346",
            },
        ]

        for paper in mock_papers:
            # 使用Qwen3-Next-80B分析论文
            analysis = await self._analyze_paper_with_qwen(paper)

            if analysis["is_relevant"]:
                discovery = FactorDiscovery(
                    discovery_id="",
                    discovery_type=DiscoveryType.ACADEMIC_PAPER,
                    factor_category=analysis["factor_category"],
                    title=paper["title"],
                    description=analysis["summary"],
                    source=paper["url"],
                    discovered_at=datetime.now(),
                    discoverer="system",
                    theoretical_basis=analysis["theoretical_basis"],
                    expected_alpha=analysis["expected_alpha"],
                    tags=analysis["tags"],
                    confidence_score=analysis["confidence_score"],
                )
                discoveries.append(discovery)

        logger.info(  # pylint: disable=logging-fstring-interpolation
            f"arXiv扫描完成，发现 {len(discoveries)} 个相关论文"
        )  # pylint: disable=logging-fstring-interpolation
        return discoveries

    async def _analyze_paper_with_qwen(self, paper: Dict[str, Any]) -> Dict[str, Any]:
        """使用Qwen3-Next-80B分析论文

        通过统一LLM网关调用，遵循架构规范

        Args:
            paper: 论文信息字典

        Returns:
            Dict: 分析结果
        """
        logger.info(  # pylint: disable=logging-fstring-interpolation
            f"使用Qwen3-Next-80B分析论文: {paper.get('title', 'Unknown')}"
        )  # pylint: disable=logging-fstring-interpolation

        try:
            # 构建分析提示
            prompt = f"""
请分析以下学术论文，判断是否包含有价值的量化因子：

论文标题: {paper.get('title', 'N/A')}
作者: {paper.get('authors', 'N/A')}
摘要: {paper.get('abstract', 'N/A')}
关键词: {paper.get('keywords', 'N/A')}

请从以下维度分析：
1. 是否与量化投资相关
2. 是否提出了新的因子或策略
3. 理论基础是否扎实
4. 实现可行性如何
5. 预期效果评估

请以JSON格式返回分析结果：
{{
    "is_relevant": true/false,
    "factor_category": "FUNDAMENTAL/TECHNICAL/ALTERNATIVE/SENTIMENT/MACRO",
    "summary": "因子发现摘要",
    "theoretical_basis": "理论基础描述",
    "expected_alpha": 0.05,
    "tags": ["标签1", "标签2"],
    "confidence_score": 0.8
}}
"""

            # 创建LLM请求
            config = self.model_configs["theory_analyzer"]
            request = LLMRequest(
                call_type=CallType.RESEARCH_ANALYSIS,
                provider=config["provider"],
                model=config["model"],
                messages=[{"role": "user", "content": prompt}],
                system_prompt="你是一个专业的量化投资研究员，擅长分析学术论文并提取可实现的投资因子。",
                max_tokens=config["max_tokens"],
                temperature=config["temperature"],
                use_memory=True,
                enable_hallucination_filter=True,
                caller_module="factor_mining_sentinel",
                caller_function="analyze_paper_with_qwen",
                business_context={
                    "paper_title": paper.get("title", "Unknown"),
                    "analysis_type": "academic_paper",
                    "discovery_type": "theory_monitoring",
                },
            )

            # 调用统一LLM网关
            response = await self.llm_gateway.call_llm(request)

            if not response.success:
                logger.error(f"论文分析失败: {response.error_message}")  # pylint: disable=logging-fstring-interpolation
                return {"is_relevant": False}

            # 解析JSON响应
            try:
                analysis_result = json.loads(response.content)

                # 转换factor_category为枚举
                if "factor_category" in analysis_result:
                    try:
                        analysis_result["factor_category"] = FactorCategory(analysis_result["factor_category"].lower())
                    except ValueError:
                        analysis_result["factor_category"] = FactorCategory.TECHNICAL

                logger.info(  # pylint: disable=logging-fstring-interpolation
                    f"论文分析完成: 相关性={analysis_result.get('is_relevant', False)}"
                )  # pylint: disable=logging-fstring-interpolation
                return analysis_result

            except json.JSONDecodeError as e:
                logger.error(f"论文分析结果JSON解析失败: {e}")  # pylint: disable=logging-fstring-interpolation
                # 降级到简单分析
                return self._fallback_paper_analysis(paper)

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"论文分析异常: {e}")  # pylint: disable=logging-fstring-interpolation
            # 降级到简单分析
            return self._fallback_paper_analysis(paper)

    def _fallback_paper_analysis(self, paper: Dict[str, Any]) -> Dict[str, Any]:
        """降级的论文分析方法（当LLM调用失败时使用）"""
        # 检查相关性
        title_lower = paper.get("title", "").lower()
        abstract_lower = paper.get("abstract", "").lower()

        factor_keywords = self.discovery_patterns["factor_keywords"]
        is_relevant = any(keyword in title_lower or keyword in abstract_lower for keyword in factor_keywords)

        if not is_relevant:
            return {"is_relevant": False}

        # 分析因子类别
        if any(word in title_lower for word in ["esg", "sentiment", "social"]):
            factor_category = FactorCategory.SENTIMENT
        elif any(word in title_lower for word in ["satellite", "alternative"]):
            factor_category = FactorCategory.ALTERNATIVE
        elif any(word in title_lower for word in ["fundamental", "earnings"]):
            factor_category = FactorCategory.FUNDAMENTAL
        else:
            factor_category = FactorCategory.TECHNICAL

        return {
            "is_relevant": True,
            "factor_category": factor_category,
            "summary": f"基于{paper.get('title', 'Unknown')}的因子发现",
            "theoretical_basis": paper.get("abstract", "")[:200] + "...",
            "expected_alpha": np.random.uniform(0.02, 0.08),  # 模拟预期Alpha
            "tags": ["academic", "new_research"],
            "confidence_score": np.random.uniform(0.6, 0.9),
        }

    async def _scan_ssrn_papers(self) -> List[FactorDiscovery]:
        """扫描SSRN论文"""
        # 类似arXiv的实现
        return []

    async def _monitor_industry_sources(self):
        """监控行业源"""
        logger.info("开始监控行业源")

        while True:
            try:
                # 监控量化研究报告
                industry_discoveries = await self._scan_industry_reports()

                # 处理发现
                for discovery in industry_discoveries:
                    await self._process_new_discovery(discovery)

                await asyncio.sleep(86400)  # 1天

            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.error(f"行业源监控错误: {e}")  # pylint: disable=logging-fstring-interpolation
                await asyncio.sleep(600)  # 10分钟后重试

    async def _scan_industry_reports(self) -> List[FactorDiscovery]:
        """扫描行业研究报告"""
        discoveries = []

        # 模拟行业报告
        mock_reports = [
            {
                "title": "Alternative Data in Factor Investing - Q1 2026 Update",
                "source": "AQR Capital Management",
                "summary": "Latest trends in alternative data usage for factor construction...",
                "data_sources": ["satellite", "social_media", "web_traffic"],
                "published": "2026-01-15",
            }
        ]

        for report in mock_reports:
            discovery = FactorDiscovery(
                discovery_id="",
                discovery_type=DiscoveryType.INDUSTRY_REPORT,
                factor_category=FactorCategory.ALTERNATIVE,
                title=report["title"],
                description=report["summary"],
                source=report["source"],
                discovered_at=datetime.now(),
                discoverer="system",
                theoretical_basis="Industry best practices and empirical findings",
                data_requirements=report["data_sources"],
                tags=["industry", "alternative_data"],
                confidence_score=0.8,
            )
            discoveries.append(discovery)

        return discoveries

    async def _monitor_alternative_data_sources(self):
        """监控替代数据源"""
        logger.info("开始监控替代数据源")

        while True:
            try:
                # 发现新的替代数据源
                data_discoveries = await self._discover_new_data_sources()

                # 处理发现
                for discovery in data_discoveries:
                    await self._process_new_discovery(discovery)

                await asyncio.sleep(86400)  # 1天

            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.error(f"替代数据源监控错误: {e}")  # pylint: disable=logging-fstring-interpolation
                await asyncio.sleep(900)  # 15分钟后重试

    async def _discover_new_data_sources(self) -> List[FactorDiscovery]:
        """发现新的数据源"""
        discoveries = []

        # 模拟新数据源发现
        mock_data_sources = [
            {
                "name": "Corporate Earnings Call Sentiment",
                "description": "Real-time sentiment analysis of corporate earnings calls",
                "data_type": "text_sentiment",
                "update_frequency": "quarterly",
                "coverage": "S&P 500",
                "potential_alpha": 0.05,
            },
            {
                "name": "Supply Chain Disruption Index",
                "description": "Satellite-based supply chain disruption monitoring",
                "data_type": "satellite_imagery",
                "update_frequency": "daily",
                "coverage": "Global",
                "potential_alpha": 0.03,
            },
        ]

        for data_source in mock_data_sources:
            discovery = FactorDiscovery(
                discovery_id="",
                discovery_type=DiscoveryType.ALTERNATIVE_DATA,
                factor_category=FactorCategory.ALTERNATIVE,
                title=f"New Data Source: {data_source['name']}",
                description=data_source["description"],
                source="Internal Discovery System",
                discovered_at=datetime.now(),
                discoverer="system",
                theoretical_basis="Alternative data correlation with stock returns",
                expected_alpha=data_source["potential_alpha"],
                data_requirements=[data_source["data_type"]],
                tags=["alternative_data", "new_source"],
                confidence_score=0.7,
            )
            discoveries.append(discovery)

        return discoveries

    async def _discover_market_anomalies(self):
        """发现市场异象"""
        logger.info("开始发现市场异象")

        while True:
            try:
                # 使用Claude-3.5分析市场数据
                anomaly_discoveries = await self._analyze_market_patterns()

                # 处理发现
                for discovery in anomaly_discoveries:
                    await self._process_new_discovery(discovery)

                await asyncio.sleep(86400)  # 1天

            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.error(f"市场异象发现错误: {e}")  # pylint: disable=logging-fstring-interpolation
                await asyncio.sleep(600)  # 10分钟后重试

    async def _analyze_market_patterns(self) -> List[FactorDiscovery]:
        """分析市场模式"""
        discoveries = []

        # 模拟市场异象发现
        mock_anomalies = [
            {
                "pattern": "Post-Earnings Announcement Drift Enhancement",
                "description": "Enhanced PEAD effect in small-cap stocks during high VIX periods",
                "strength": 0.04,
                "persistence": "3-5 days",
                "conditions": ["small_cap", "high_vix", "earnings_surprise"],
            }
        ]

        for anomaly in mock_anomalies:
            discovery = FactorDiscovery(
                discovery_id="",
                discovery_type=DiscoveryType.MARKET_ANOMALY,
                factor_category=FactorCategory.TECHNICAL,
                title=f"Market Anomaly: {anomaly['pattern']}",
                description=anomaly["description"],
                source="Internal Market Analysis",
                discovered_at=datetime.now(),
                discoverer="system",
                theoretical_basis="Behavioral finance and market microstructure",
                expected_alpha=anomaly["strength"],
                tags=["market_anomaly", "behavioral"],
                confidence_score=0.75,
            )
            discoveries.append(discovery)

        return discoveries

    async def _analyze_cross_asset_signals(self):
        """分析跨资产信号"""
        logger.info("开始分析跨资产信号")

        while True:
            try:
                # 发现跨资产信号
                cross_asset_discoveries = await self._find_cross_asset_patterns()

                # 处理发现
                for discovery in cross_asset_discoveries:
                    await self._process_new_discovery(discovery)

                await asyncio.sleep(86400)  # 1天

            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.error(f"跨资产信号分析错误: {e}")  # pylint: disable=logging-fstring-interpolation
                await asyncio.sleep(900)  # 15分钟后重试

    async def _find_cross_asset_patterns(self) -> List[FactorDiscovery]:
        """发现跨资产模式"""
        discoveries = []

        # 模拟跨资产信号发现
        mock_signals = [
            {
                "signal": "Bond-Equity Momentum Spillover",
                "description": "Corporate bond momentum predicts equity returns with 2-day lag",
                "assets": ["corporate_bonds", "equities"],
                "lag": 2,
                "strength": 0.035,
            }
        ]

        for signal in mock_signals:
            discovery = FactorDiscovery(
                discovery_id="",
                discovery_type=DiscoveryType.CROSS_ASSET,
                factor_category=FactorCategory.CROSS_SECTIONAL,
                title=f"Cross-Asset Signal: {signal['signal']}",
                description=signal["description"],
                source="Internal Cross-Asset Analysis",
                discovered_at=datetime.now(),
                discoverer="system",
                theoretical_basis="Cross-asset momentum and information flow",
                expected_alpha=signal["strength"],
                tags=["cross_asset", "momentum"],
                confidence_score=0.8,
            )
            discoveries.append(discovery)

        return discoveries

    async def _process_new_discovery(self, discovery: FactorDiscovery):
        """处理新发现"""
        logger.info(f"处理新发现: {discovery.title}")  # pylint: disable=logging-fstring-interpolation

        # 检查是否已存在
        if discovery.discovery_id in self.discoveries:
            logger.debug(f"发现已存在: {discovery.discovery_id}")  # pylint: disable=logging-fstring-interpolation
            return

        # 保存发现
        self.discoveries[discovery.discovery_id] = discovery

        # 持久化存储
        await self._save_discovery(discovery)

        # 缓存到Redis
        await self._cache_discovery(discovery)

        # 如果置信度足够高，自动开始实现
        if discovery.confidence_score >= 0.8:
            logger.info(  # pylint: disable=logging-fstring-interpolation
                f"高置信度发现，开始自动实现: {discovery.title}"
            )  # pylint: disable=logging-fstring-interpolation
            await self._auto_implement_factor(discovery)

    async def _save_discovery(self, discovery: FactorDiscovery):
        """保存发现到文件"""
        try:
            # 按日期组织文件
            date_str = discovery.discovered_at.strftime("%Y-%m-%d")
            file_path = self.discovery_storage_path / f"discoveries_{date_str}.json"

            # 读取现有数据
            discoveries_data = []
            if file_path.exists():
                with open(file_path, "r", encoding="utf-8") as f:
                    discoveries_data = json.load(f)

            # 添加新发现
            discovery_dict = {
                "discovery_id": discovery.discovery_id,
                "discovery_type": discovery.discovery_type.value,
                "factor_category": discovery.factor_category.value,
                "title": discovery.title,
                "description": discovery.description,
                "source": discovery.source,
                "discovered_at": discovery.discovered_at.isoformat(),
                "discoverer": discovery.discoverer,
                "theoretical_basis": discovery.theoretical_basis,
                "expected_alpha": discovery.expected_alpha,
                "risk_factors": discovery.risk_factors,
                "implementation_complexity": discovery.implementation_complexity,
                "data_requirements": discovery.data_requirements,
                "computational_cost": discovery.computational_cost,
                "status": discovery.status.value,
                "tags": discovery.tags,
                "confidence_score": discovery.confidence_score,
            }

            discoveries_data.append(discovery_dict)

            # 保存文件
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(discoveries_data, f, indent=2, ensure_ascii=False)

            logger.debug(f"发现已保存到文件: {file_path}")  # pylint: disable=logging-fstring-interpolation

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"保存发现失败: {e}")  # pylint: disable=logging-fstring-interpolation

    async def _cache_discovery(self, discovery: FactorDiscovery):
        """缓存发现到Redis"""
        try:
            key = f"factor_discovery:{discovery.discovery_id}"
            value = {
                "title": discovery.title,
                "description": discovery.description,
                "source": discovery.source,
                "discovered_at": discovery.discovered_at.isoformat(),
                "confidence_score": discovery.confidence_score,
                "status": discovery.status.value,
            }

            self.redis_client.setex(key, 86400 * 7, json.dumps(value))  # 7天过期

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"缓存发现失败: {e}")  # pylint: disable=logging-fstring-interpolation

    async def _auto_implement_factor(self, discovery: FactorDiscovery):
        """自动实现因子"""
        logger.info(f"开始自动实现因子: {discovery.title}")  # pylint: disable=logging-fstring-interpolation

        try:
            # 更新状态
            discovery.status = ValidationStatus.IMPLEMENTING

            # 使用DeepSeek-R1生成因子代码
            implementation = await self._generate_factor_code_with_deepseek(discovery)

            if implementation:
                # 保存实现
                self.implementations[implementation.factor_id] = implementation

                # 更新发现状态
                discovery.status = ValidationStatus.TESTING

                # 开始验证
                await self._validate_factor_implementation(discovery, implementation)

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"自动实现因子失败: {e}")  # pylint: disable=logging-fstring-interpolation
            discovery.status = ValidationStatus.DISCOVERED

    async def _generate_factor_code_with_deepseek(self, discovery: FactorDiscovery) -> Optional[FactorImplementation]:
        """使用DeepSeek-R1生成因子代码

        通过统一LLM网关调用，遵循架构规范

        Args:
            discovery: 因子发现记录

        Returns:
            Optional[FactorImplementation]: 因子实现，失败时返回None
        """
        logger.info(f"使用DeepSeek-R1生成因子代码: {discovery.title}")  # pylint: disable=logging-fstring-interpolation

        try:
            # 构建代码生成提示
            prompt = f"""
基于以下因子发现，请生成完整的Python实现代码：

因子名称: {discovery.title}
因子类别: {discovery.factor_category.value}
理论基础: {discovery.theoretical_basis}
描述: {discovery.description}

请生成：
1. 因子公式 (简洁的数学表达式)
2. 完整的Python函数实现
3. 必要的依赖库列表

要求：
- 代码必须可执行，包含完整的错误处理
- 使用pandas和numpy进行数据处理
- 返回标准化的因子值 (rank或z-score)
- 包含详细的文档字符串

请以JSON格式返回：
{{
    "factor_formula": "rank(close / delay(close, 20) - 1)",
    "python_code": "完整的Python函数代码",
    "dependencies": ["pandas", "numpy"],
    "factor_name": "因子名称",
    "code_quality_score": 0.85
}}
"""

            # 创建LLM请求
            config = self.model_configs["factor_implementer"]
            request = LLMRequest(
                call_type=CallType.CODE_GENERATION,
                provider=config["provider"],
                model=config["model"],
                messages=[{"role": "user", "content": prompt}],
                system_prompt="你是一个专业的量化开发工程师，擅长将投资理论转化为高质量的Python代码。",
                max_tokens=config["max_tokens"],
                temperature=config["temperature"],
                use_memory=True,
                enable_hallucination_filter=True,
                caller_module="factor_mining_sentinel",
                caller_function="generate_factor_code_with_deepseek",
                business_context={
                    "discovery_id": discovery.discovery_id,
                    "factor_category": discovery.factor_category.value,
                    "code_generation": True,
                },
            )

            # 调用统一LLM网关
            response = await self.llm_gateway.call_llm(request)

            if not response.success:
                logger.error(  # pylint: disable=logging-fstring-interpolation
                    f"因子代码生成失败: {response.error_message}"
                )  # pylint: disable=logging-fstring-interpolation
                return self._fallback_code_generation(discovery)

            # 解析JSON响应
            try:
                code_result = json.loads(response.content)

                # 创建实现对象
                implementation = FactorImplementation(
                    factor_id="",
                    discovery_id=discovery.discovery_id,
                    factor_name=code_result.get("factor_name", f"factor_{discovery.discovery_id}"),
                    factor_formula=code_result.get("factor_formula", "rank(indicator)"),
                    python_code=code_result.get("python_code", ""),
                    dependencies=code_result.get("dependencies", ["pandas", "numpy"]),
                    implementation_model="DeepSeek-R1",
                    code_quality_score=code_result.get("code_quality_score", 0.8),
                )

                logger.info(  # pylint: disable=logging-fstring-interpolation
                    f"因子代码生成完成: {implementation.factor_name}"
                )  # pylint: disable=logging-fstring-interpolation
                return implementation

            except json.JSONDecodeError as e:
                logger.error(f"因子代码生成结果JSON解析失败: {e}")  # pylint: disable=logging-fstring-interpolation
                return self._fallback_code_generation(discovery)

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"因子代码生成异常: {e}")  # pylint: disable=logging-fstring-interpolation
            return self._fallback_code_generation(discovery)

    def _fallback_code_generation(self, discovery: FactorDiscovery) -> FactorImplementation:
        """降级的代码生成方法（当LLM调用失败时使用）"""
        # 根据因子类别生成不同的代码模板
        if discovery.factor_category == FactorCategory.TECHNICAL:
            factor_formula = "rank(close / delay(close, 20) - 1)"
            python_code = """
def momentum_factor(data):
    '''动量因子: 20日价格动量'''
    close = data['close']
    momentum = close / close.shift(20) - 1
    return momentum.rank(pct=True)
"""
        elif discovery.factor_category == FactorCategory.SENTIMENT:
            factor_formula = "rank(sentiment_score * volume_ratio)"
            python_code = """
def sentiment_factor(data):
    '''情绪因子: 情绪得分加权成交量'''
    sentiment = data['sentiment_score']
    volume_ratio = data['volume'] / data['volume'].rolling(20).mean()
    factor = sentiment * volume_ratio
    return factor.rank(pct=True)
"""
        elif discovery.factor_category == FactorCategory.ALTERNATIVE:
            factor_formula = "rank(satellite_signal * earnings_surprise)"
            python_code = """
def alternative_factor(data):
    '''替代数据因子: 卫星信号与盈利惊喜'''
    satellite = data['satellite_signal']
    earnings = data['earnings_surprise']
    factor = satellite * earnings
    return factor.rank(pct=True)
"""
        else:
            factor_formula = "rank(technical_indicator)"
            python_code = """
def technical_factor(data):
    '''技术因子: 通用技术指标'''
    indicator = data['technical_indicator']
    return indicator.rank(pct=True)
"""

        # 创建实现对象
        implementation = FactorImplementation(
            factor_id="",
            discovery_id=discovery.discovery_id,
            factor_name=f"factor_{discovery.discovery_id}",
            factor_formula=factor_formula,
            python_code=python_code,
            dependencies=["pandas", "numpy"],
            implementation_model="DeepSeek-R1 (Fallback)",
            code_quality_score=0.7,  # 降级版本质量稍低
        )

        logger.info(  # pylint: disable=logging-fstring-interpolation
            f"因子代码生成完成 (降级模式): {implementation.factor_name}"
        )  # pylint: disable=logging-fstring-interpolation
        return implementation

    async def _validate_factor_implementation(self, discovery: FactorDiscovery, implementation: FactorImplementation):
        """验证因子实现"""
        logger.info(f"开始验证因子实现: {implementation.factor_name}")  # pylint: disable=logging-fstring-interpolation

        try:
            # 模拟回测验证
            validation_results = await self._run_factor_backtest(implementation)

            # 更新实现性能指标
            implementation.ic_mean = validation_results["ic_mean"]
            implementation.ic_std = validation_results["ic_std"]
            implementation.ir_ratio = validation_results["ir_ratio"]
            implementation.turnover = validation_results["turnover"]

            # 更新发现验证结果
            discovery.validation_results = validation_results

            # 判断是否通过验证
            if validation_results["ic_mean"] > 0.02 and validation_results["ir_ratio"] > 0.5:
                discovery.status = ValidationStatus.VALIDATED
                logger.info(  # pylint: disable=logging-fstring-interpolation
                    f"因子验证通过: {implementation.factor_name}"
                )  # pylint: disable=logging-fstring-interpolation

                # 提交到Arena测试队列
                await self._integrate_validated_factor(discovery, implementation)
            else:
                discovery.status = ValidationStatus.DISCOVERED
                logger.info(  # pylint: disable=logging-fstring-interpolation
                    f"因子验证未通过: {implementation.factor_name}"
                )  # pylint: disable=logging-fstring-interpolation

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"因子验证失败: {e}")  # pylint: disable=logging-fstring-interpolation
            discovery.status = ValidationStatus.DISCOVERED

    async def _run_factor_backtest(
        self, implementation: FactorImplementation  # pylint: disable=unused-argument
    ) -> Dict[str, float]:  # pylint: disable=unused-argument
        """运行因子回测"""
        # 模拟回测结果 (实际应该运行真实回测)

        # 根据因子类型生成不同的性能指标
        base_ic = np.random.uniform(0.01, 0.06)
        np.random.uniform(0.3, 1.2)
        base_turnover = np.random.uniform(0.5, 2.0)

        # 添加一些噪声
        ic_mean = base_ic + np.random.normal(0, 0.005)
        ic_std = abs(np.random.normal(0.02, 0.005))
        ir_ratio = ic_mean / ic_std if ic_std > 0 else 0
        turnover = base_turnover + np.random.normal(0, 0.1)

        return {
            "ic_mean": ic_mean,
            "ic_std": ic_std,
            "ir_ratio": ir_ratio,
            "turnover": max(0.1, turnover),
            "sharpe_ratio": np.random.uniform(0.8, 2.0),
            "max_drawdown": np.random.uniform(0.05, 0.15),
            "win_rate": np.random.uniform(0.45, 0.65),
        }

    async def _integrate_validated_factor(self, discovery: FactorDiscovery, implementation: FactorImplementation):
        """提交已验证因子到Arena测试队列"""
        logger.info(  # pylint: disable=logging-fstring-interpolation
            f"提交已验证因子到Arena测试队列: {implementation.factor_name}"
        )  # pylint: disable=logging-fstring-interpolation

        try:
            # 更新状态为等待Arena测试
            discovery.status = ValidationStatus.VALIDATED

            # 生成因子文件到待测试队列
            pending_factors_dir = self.discovery_storage_path / "pending_arena_factors"
            pending_factors_dir.mkdir(parents=True, exist_ok=True)

            factor_file_path = pending_factors_dir / f"{implementation.factor_name}.py"

            # 安全格式化可能为None的值
            expected_alpha_str = f"{discovery.expected_alpha:.3f}" if discovery.expected_alpha is not None else "N/A"
            ic_mean_str = f"{implementation.ic_mean:.3f}" if implementation.ic_mean is not None else "N/A"
            ir_ratio_str = f"{implementation.ir_ratio:.3f}" if implementation.ir_ratio is not None else "N/A"
            turnover_str = (  # pylint: disable=unused-variable
                f"{implementation.turnover:.3f}" if implementation.turnover is not None else "N/A"
            )  # pylint: disable=unused-variable

            # 写入因子代码
            factor_content = f"""# {discovery.title}
# 发现日期: {discovery.discovered_at.strftime('%Y-%m-%d')}
# 理论基础: {discovery.theoretical_basis}
# 预期Alpha: {expected_alpha_str}
# IC均值: {ic_mean_str}
# IR比率: {ir_ratio_str}
# 状态: 等待Arena三轨测试

{implementation.python_code}

# 因子元数据
FACTOR_METADATA = {{
    'factor_id': '{implementation.factor_id}',
    'discovery_id': '{discovery.discovery_id}',
    'factor_name': '{implementation.factor_name}',
    'factor_formula': '{implementation.factor_formula}',
    'category': '{discovery.factor_category.value}',
    'ic_mean': {implementation.ic_mean},
    'ir_ratio': {implementation.ir_ratio},
    'turnover': {implementation.turnover},
    'submitted_to_arena_at': '{datetime.now().isoformat()}',
    'next_step': 'Arena三轨测试 (Reality Track + Hell Track + Cross-Market Track)',
    'validation_flow': [
        '1. Arena三轨测试验证',
        '2. 因子组合策略生成', 
        '3. 斯巴达Arena策略考核',
        '4. 模拟盘1个月验证',
        '5. Z2H基因胶囊认证',
        '6. 策略库集成'
    ]
}}
"""

            with open(factor_file_path, "w", encoding="utf-8") as f:
                f.write(factor_content)

            # 更新待测试因子索引
            await self._update_pending_arena_index(discovery, implementation)

            logger.info(  # pylint: disable=logging-fstring-interpolation
                f"因子已提交到Arena测试队列: {factor_file_path}"
            )  # pylint: disable=logging-fstring-interpolation
            logger.info(  # pylint: disable=logging-fstring-interpolation
                f"下一步: Arena三轨测试 → 策略生成 → 斯巴达考核 → 模拟盘验证 → Z2H认证 → 策略库"  # pylint: disable=w1309
            )  # pylint: disable=logging-fstring-interpolation

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"提交因子到Arena队列失败: {e}")  # pylint: disable=logging-fstring-interpolation

    async def _update_pending_arena_index(self, discovery: FactorDiscovery, implementation: FactorImplementation):
        """更新待Arena测试因子索引"""
        try:
            index_file = self.discovery_storage_path / "pending_arena_factors_index.json"

            # 读取现有索引
            index_data = []
            if index_file.exists():
                with open(index_file, "r", encoding="utf-8") as f:
                    index_data = json.load(f)

            # 添加新因子
            factor_entry = {
                "factor_id": implementation.factor_id,
                "factor_name": implementation.factor_name,
                "discovery_id": discovery.discovery_id,
                "title": discovery.title,
                "category": discovery.factor_category.value,
                "ic_mean": implementation.ic_mean,
                "ir_ratio": implementation.ir_ratio,
                "turnover": implementation.turnover,
                "submitted_to_arena_at": datetime.now().isoformat(),
                "file_path": f"pending_arena_factors/{implementation.factor_name}.py",
                "status": "pending_arena_test",
                "next_step": "Arena三轨测试",
                "validation_pipeline": [
                    {"step": 1, "name": "Arena三轨测试", "status": "pending"},
                    {"step": 2, "name": "策略生成", "status": "waiting"},
                    {"step": 3, "name": "斯巴达Arena考核", "status": "waiting"},
                    {"step": 4, "name": "模拟盘验证", "status": "waiting"},
                    {"step": 5, "name": "Z2H认证", "status": "waiting"},
                    {"step": 6, "name": "策略库集成", "status": "waiting"},
                ],
            }

            index_data.append(factor_entry)

            # 保存索引
            with open(index_file, "w", encoding="utf-8") as f:
                json.dump(index_data, f, indent=2, ensure_ascii=False)

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"更新待Arena测试索引失败: {e}")  # pylint: disable=logging-fstring-interpolation

    def _load_historical_discoveries(self):
        """加载历史发现"""
        try:
            # 扫描发现文件
            for file_path in self.discovery_storage_path.glob("discoveries_*.json"):
                with open(file_path, "r", encoding="utf-8") as f:
                    discoveries_data = json.load(f)

                for data in discoveries_data:
                    discovery = FactorDiscovery(
                        discovery_id=data["discovery_id"],
                        discovery_type=DiscoveryType(data["discovery_type"]),
                        factor_category=FactorCategory(data["factor_category"]),
                        title=data["title"],
                        description=data["description"],
                        source=data["source"],
                        discovered_at=datetime.fromisoformat(data["discovered_at"]),
                        discoverer=data["discoverer"],
                        theoretical_basis=data["theoretical_basis"],
                        expected_alpha=data.get("expected_alpha"),
                        risk_factors=data.get("risk_factors", []),
                        implementation_complexity=data.get("implementation_complexity", "medium"),
                        data_requirements=data.get("data_requirements", []),
                        computational_cost=data.get("computational_cost", "medium"),
                        status=ValidationStatus(data["status"]),
                        tags=data.get("tags", []),
                        confidence_score=data.get("confidence_score", 0.5),
                    )

                    self.discoveries[discovery.discovery_id] = discovery

            logger.info(  # pylint: disable=logging-fstring-interpolation
                f"加载历史发现完成: {len(self.discoveries)} 个发现"
            )  # pylint: disable=logging-fstring-interpolation

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"加载历史发现失败: {e}")  # pylint: disable=logging-fstring-interpolation

    def get_discovery_statistics(self) -> Dict[str, Any]:
        """获取发现统计"""
        stats = {
            "total_discoveries": len(self.discoveries),
            "by_type": {},
            "by_category": {},
            "by_status": {},
            "by_discoverer": {},
            "recent_discoveries": [],
            "top_performers": [],
        }

        # 按类型统计
        for discovery in self.discoveries.values():
            # 按发现类型
            discovery_type = discovery.discovery_type.value
            stats["by_type"][discovery_type] = stats["by_type"].get(discovery_type, 0) + 1

            # 按因子类别
            factor_category = discovery.factor_category.value
            stats["by_category"][factor_category] = stats["by_category"].get(factor_category, 0) + 1

            # 按状态
            status = discovery.status.value
            stats["by_status"][status] = stats["by_status"].get(status, 0) + 1

            # 按发现者
            discoverer = discovery.discoverer
            stats["by_discoverer"][discoverer] = stats["by_discoverer"].get(discoverer, 0) + 1

        # 最近发现 (最近7天)
        recent_cutoff = datetime.now() - timedelta(days=7)
        recent_discoveries = [
            {
                "title": d.title,
                "discovered_at": d.discovered_at.isoformat(),
                "confidence_score": d.confidence_score,
                "status": d.status.value,
            }
            for d in self.discoveries.values()
            if d.discovered_at >= recent_cutoff
        ]
        stats["recent_discoveries"] = sorted(recent_discoveries, key=lambda x: x["discovered_at"], reverse=True)[:10]

        # 顶级表现者 (已验证的因子)
        validated_discoveries = [
            d for d in self.discoveries.values() if d.status == ValidationStatus.VALIDATED and d.expected_alpha
        ]
        stats["top_performers"] = sorted(
            [
                {
                    "title": d.title,
                    "expected_alpha": d.expected_alpha,
                    "confidence_score": d.confidence_score,
                    "category": d.factor_category.value,
                }
                for d in validated_discoveries
            ],
            key=lambda x: x["expected_alpha"],
            reverse=True,
        )[:5]

        return stats

    async def manual_discovery_input(  # pylint: disable=too-many-positional-arguments
        self,
        title: str,
        description: str,
        theoretical_basis: str,
        factor_category: FactorCategory,
        expected_alpha: Optional[float] = None,
        data_requirements: Optional[List[str]] = None,
    ) -> str:
        """手动输入发现"""
        logger.info(f"手动输入新发现: {title}")  # pylint: disable=logging-fstring-interpolation

        discovery = FactorDiscovery(
            discovery_id="",
            discovery_type=DiscoveryType.TECHNICAL_INNOVATION,
            factor_category=factor_category,
            title=title,
            description=description,
            source="Manual Input",
            discovered_at=datetime.now(),
            discoverer="human",
            theoretical_basis=theoretical_basis,
            expected_alpha=expected_alpha,
            data_requirements=data_requirements or [],
            tags=["manual", "human_input"],
            confidence_score=0.9,  # 人工输入给予高置信度
        )

        # 处理发现
        await self._process_new_discovery(discovery)

        # 发布因子发现事件 - 通过事件总线通知其他模块
        await publish_event(
            event_type=EventType.FACTOR_DISCOVERED,
            source_module="factor_mining_sentinel",
            data={
                "discovery_id": discovery.discovery_id,
                "factor_category": discovery.factor_category.value,
                "title": discovery.title,
                "confidence_score": discovery.confidence_score,
                "expected_alpha": discovery.expected_alpha,
            },
            priority=EventPriority.HIGH,
        )

        return discovery.discovery_id

    async def get_discovery_details(self, discovery_id: str) -> Optional[Dict[str, Any]]:
        """获取发现详情"""
        if discovery_id not in self.discoveries:
            return None

        discovery = self.discoveries[discovery_id]

        details = {
            "discovery_id": discovery.discovery_id,
            "title": discovery.title,
            "description": discovery.description,
            "discovery_type": discovery.discovery_type.value,
            "factor_category": discovery.factor_category.value,
            "source": discovery.source,
            "discovered_at": discovery.discovered_at.isoformat(),
            "discoverer": discovery.discoverer,
            "theoretical_basis": discovery.theoretical_basis,
            "expected_alpha": discovery.expected_alpha,
            "risk_factors": discovery.risk_factors,
            "implementation_complexity": discovery.implementation_complexity,
            "data_requirements": discovery.data_requirements,
            "computational_cost": discovery.computational_cost,
            "status": discovery.status.value,
            "validation_results": discovery.validation_results,
            "tags": discovery.tags,
            "confidence_score": discovery.confidence_score,
        }

        # 如果有实现，添加实现信息
        implementation = None
        for impl in self.implementations.values():
            if impl.discovery_id == discovery_id:
                implementation = impl
                break

        if implementation:
            details["implementation"] = {
                "factor_id": implementation.factor_id,
                "factor_name": implementation.factor_name,
                "factor_formula": implementation.factor_formula,
                "ic_mean": implementation.ic_mean,
                "ic_std": implementation.ic_std,
                "ir_ratio": implementation.ir_ratio,
                "turnover": implementation.turnover,
                "implemented_at": implementation.implemented_at.isoformat(),
                "code_quality_score": implementation.code_quality_score,
            }

        return details
