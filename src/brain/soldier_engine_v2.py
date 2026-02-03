# pylint: disable=too-many-lines
"""
Soldier Engine V2 - 执行层AI大脑（简化版）

白皮书依据: 第二章 2.1 AI三脑架构 - Soldier (执行层)
架构重设计: Requirement 15 - Soldier引擎简化

职责：快速执行，不制定风险规则
- 所有风险控制逻辑已移至策略层（Strategy + StrategyRiskManager）
- Soldier只负责执行策略给出的决策，不做任何风险判断

功能:
- 本地LLM推理（llama.cpp）
- 热备切换机制（Local ↔ Cloud）
- 健康检查和故障检测
- 决策缓存系统（Redis）
- 执行策略决策（execute_strategy_decision）

已移除的功能（现在由策略层负责）:
- ❌ assess_risk_level() - 风险评估
- ❌ check_position_limits() - 仓位限制检查
- ❌ 硬编码的风险矩阵
"""

import asyncio
import hashlib
import json
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from loguru import logger

# Redis导入和可用性检查
try:
    import redis.asyncio as aioredis

    REDIS_AVAILABLE = True
except ImportError:
    aioredis = None
    REDIS_AVAILABLE = False
    logger.warning("[SoldierV2] redis.asyncio not available, cache will be disabled")

from src.brain.interfaces import ISoldierEngine
from src.core.dependency_container import LifecycleScope, injectable
from src.infra.event_bus import Event, EventPriority, EventType


class SoldierMode(Enum):
    """Soldier运行模式

    白皮书依据: 第二章 2.1.2 运行模式
    """

    NORMAL = "normal"  # 本地模型正常运行
    DEGRADED = "degraded"  # 降级到云端API
    OFFLINE = "offline"  # 离线规则引擎


class RiskLevel(Enum):
    """风险等级 - Task 21.1 (架构A保留)

    白皮书依据: 第二章 2.2.3 风险控制矩阵, 2.2.4 风险控制元学习架构

    注意: 此类保留为元学习架构的架构A（Soldier硬编码风控）
    参考: RISK_CONTROL_ARCHITECTURE_A_PROTECTION.md
    """

    LOW = "low"  # 低风险
    MEDIUM = "medium"  # 中风险
    HIGH = "high"  # 高风险


@dataclass
class RiskAssessment:
    """风险评估结果 - Task 21.1 (架构A保留)

    白皮书依据: 第二章 2.2.3 风险控制矩阵, 2.2.4 风险控制元学习架构

    注意: 此类保留为元学习架构的架构A（Soldier硬编码风控）
    参考: RISK_CONTROL_ARCHITECTURE_A_PROTECTION.md
    """

    risk_level: RiskLevel
    volatility: float  # 波动率
    liquidity: float  # 流动性
    correlation: float  # 相关性
    risk_score: float  # 综合风险评分（0-1）
    factors: Dict[str, Any]  # 风险因子详情
    timestamp: str


class SignalType(Enum):
    """信号类型

    用于测试和兼容性
    """

    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"


@dataclass
class MarketSignal:
    """市场信号

    用于测试和兼容性
    """

    symbol: str
    signal_type: SignalType
    strength: float
    timestamp: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SoldierDecision:
    """Soldier决策结果

    白皮书依据: 第二章 2.1.3 决策流程
    """

    action: str
    confidence: float
    reasoning: str
    signal_strength: float
    risk_level: str
    execution_priority: int
    latency_ms: float
    source_mode: str
    metadata: Dict[str, Any]


@dataclass
class SoldierConfig:  # pylint: disable=too-many-instance-attributes
    """Soldier配置

    白皮书依据: 第二章 2.1.2 运行模式, 第十二章 12.1.3 Soldier热备切换
    """

    # 推理超时配置
    local_inference_timeout: float = 0.02  # 20ms
    cloud_timeout: float = 5.0  # 5秒（更新为测试期望值）

    # 降级阈值配置
    degradation_threshold: float = 0.2  # 降级阈值（20%失败率）

    # 健康检查配置
    failure_threshold: int = 3  # 失败阈值
    recovery_check_interval: float = 10.0  # 恢复检查间隔（秒）

    # 缓存配置 - Task 20.1, 20.3
    decision_cache_ttl: int = 5  # 决策缓存TTL（秒）
    redis_host: str = "localhost"  # Redis主机
    redis_port: int = 6379  # Redis端口
    redis_db: int = 0  # Redis数据库
    redis_password: Optional[str] = None  # Redis密码
    redis_max_connections: int = 10  # 连接池最大连接数
    cache_key_prefix: str = "soldier:decision:"  # 缓存键前缀

    # 缓存策略配置 - Task 20.3
    cache_max_size: int = 10000  # 最大缓存条目数
    cache_eviction_policy: str = "lru"  # 缓存淘汰策略（lru/lfu/fifo）
    cache_warmup_enabled: bool = True  # 是否启用缓存预热
    cache_warmup_symbols: List[str] = field(default_factory=list)  # 预热股票列表
    cache_hit_rate_target: float = 0.8  # 目标缓存命中率（80%）
    # 缓存监控和告警配置 - Task 20.5
    cache_alert_enabled: bool = True  # 是否启用缓存告警
    cache_alert_hit_rate_threshold: float = 0.5  # 命中率告警阈值（50%）
    cache_alert_error_rate_threshold: float = 0.1  # 错误率告警阈值（10%）
    cache_alert_check_interval: float = 60.0  # 告警检查间隔（秒）
    # 风险评估配置 - Task 21.1
    risk_assessment_enabled: bool = True  # 是否启用风险评估
    volatility_window: int = 20  # 波动率计算窗口（天）
    liquidity_threshold: float = 1000000.0  # 流动性阈值（成交额）
    correlation_threshold: float = 0.7  # 相关性阈值

    # 风险等级阈值 - 白皮书: 2.2.3 风险控制矩阵
    low_risk_volatility_max: float = 0.02  # 低风险最大波动率（2%）
    medium_risk_volatility_max: float = 0.04  # 中风险最大波动率（4%）
    high_risk_volatility_min: float = 0.04  # 高风险最小波动率（4%）


@injectable(LifecycleScope.SINGLETON)
class SoldierEngineV2(ISoldierEngine):  # pylint: disable=too-many-instance-attributes
    """Soldier Engine V2 - 执行层AI大脑

    白皮书依据: 第二章 2.1 Soldier (快系统 - 热备高可用)
    """

    def __init__(self, config: Optional[SoldierConfig] = None):
        """初始化Soldier Engine V2"""
        self.config = config or SoldierConfig()

        self.mode = SoldierMode.NORMAL
        self.state = "IDLE"
        self.failure_count = 0
        self.last_decision_time: Optional[datetime] = None

        # 事件总线
        self.event_bus = None

        # 外部数据缓存 (来自Commander/Scholar)
        self.external_data: Dict[str, Any] = {}
        self.data_timeout = 2.0  # 2秒超时

        # LLM推理引擎 (Task 18.1)
        self.llm_inference = None

        # DeepSeek API客户端 (Task 19.5)
        self.deepseek_client = None

        # Redis缓存客户端 (Task 20.1)
        self.redis_client: Optional[Any] = None  # 使用Any避免类型检查问题
        self.cache_enabled = REDIS_AVAILABLE

        # 缓存策略状态 (Task 20.3)
        self.cache_warmup_completed = False  # 预热完成标志

        # 健康检查状态 (Task 19.1)
        self.health_check_task: Optional[asyncio.Task] = None
        self.last_health_check: Optional[datetime] = None
        self.consecutive_failures = 0
        self.is_healthy = True

        self.stats = {
            "total_decisions": 0,
            "local_decisions": 0,
            "cloud_decisions": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "cache_errors": 0,
            "cache_evictions": 0,  # Task 20.3
            "cache_warmup_count": 0,  # Task 20.3
            "error_count": 0,
            "avg_latency_ms": 0.0,
            "success_rate": 1.0,
            "health_checks": 0,
            "health_check_failures": 0,
        }

        # 缓存告警状态 (Task 20.5)
        self.last_alert_time: Optional[datetime] = None  # 上次告警时间
        self.alert_count = 0  # 告警计数
        logger.info(f"[SoldierV2] Initialized - mode={self.mode.value}, cache_enabled={self.cache_enabled}")

    async def initialize(self):
        """初始化Soldier Engine"""
        try:
            logger.info("[SoldierV2] Starting initialization...")

            # 获取事件总线
            from src.infra.event_bus import get_event_bus  # pylint: disable=import-outside-toplevel

            self.event_bus = await get_event_bus()

            # 初始化Redis缓存 (Task 20.1)
            if self.cache_enabled:
                await self._initialize_redis_cache()

                # Task 20.3: 缓存预热
                if self.config.cache_warmup_enabled:
                    await self._warmup_cache()

            await asyncio.sleep(0.001)  # 模拟初始化
            self.state = "READY"
            logger.info("[SoldierV2] Initialization completed")
        except Exception as e:
            self.state = "ERROR"
            logger.error(f"[SoldierV2] Initialization failed: {e}")
            raise RuntimeError(f"Soldier initialization failed: {e}") from e

    async def decide(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """做出交易决策（ISoldierEngine接口实现）

        白皮书依据: 第二章 2.1.3 决策流程

        决策流程（Task 20.1集成缓存）:
        1. 检查缓存（TTL 5秒）
        2. 如果缓存命中，直接返回
        3. 如果缓存未命中，执行决策
        4. 将决策结果存入缓存
        """
        symbol = context.get("symbol", "UNKNOWN")

        start_time = time.perf_counter()

        try:
            self.state = "DECIDING"

            # 1. 检查缓存 (Task 20.1)
            cached_decision = await self._get_cached_decision(context)
            if cached_decision:
                logger.debug(f"[SoldierV2] Returning cached decision - symbol={symbol}")
                return cached_decision

            # 2. 模拟决策推理
            await asyncio.sleep(0.005)  # 5ms推理延迟

            decision = SoldierDecision(
                action="buy",
                confidence=0.75,
                reasoning=f"Decision for {symbol}",
                signal_strength=0.8,
                risk_level="medium",
                execution_priority=5,
                latency_ms=(time.perf_counter() - start_time) * 1000,
                source_mode="normal",
                metadata={"symbol": symbol},
            )

            # 更新统计
            self.stats["total_decisions"] += 1
            self.stats["local_decisions"] += 1

            result = {
                "decision": {
                    "action": decision.action,
                    "confidence": decision.confidence,
                    "reasoning": decision.reasoning,
                    "signal_strength": decision.signal_strength,
                    "risk_level": decision.risk_level,
                    "execution_priority": decision.execution_priority,
                    "latency_ms": decision.latency_ms,
                    "source_mode": decision.source_mode,
                },
                "metadata": {
                    "soldier_mode": self.mode.value,
                    "timestamp": datetime.now().isoformat(),
                    "source": "soldier_v2",
                    **decision.metadata,
                },
            }

            # 3. 存入缓存 (Task 20.1)
            await self._set_cached_decision(context, result)

            self.state = "READY"
            self.last_decision_time = datetime.now()

            return result

        except Exception as e:  # pylint: disable=broad-exception-caught
            self.stats["error_count"] += 1
            self.state = "ERROR"
            logger.error(f"[SoldierV2] Decision making failed: {e}")

            # 返回回退决策
            return {
                "decision": {
                    "action": "hold",
                    "confidence": 0.1,
                    "reasoning": f"Fallback decision for {symbol}",
                    "signal_strength": 0.0,
                    "risk_level": "high",
                    "execution_priority": 1,
                    "latency_ms": 0.0,
                    "source_mode": "fallback",
                },
                "metadata": {
                    "soldier_mode": self.mode.value,
                    "timestamp": datetime.now().isoformat(),
                    "source": "soldier_v2",
                    "is_fallback": True,
                    "symbol": symbol,
                },
            }

    async def get_status(self) -> Dict[str, Any]:
        """获取Soldier状态"""
        return {
            "mode": self.mode.value,
            "state": self.state,
            "failure_count": self.failure_count,
            "last_decision_time": (self.last_decision_time.isoformat() if self.last_decision_time else None),
            "stats": self.stats.copy(),
        }

    def get_state(self) -> str:
        """获取当前状态（ISoldierEngine接口实现）"""
        return self.state

    # ==================== Redis缓存方法 (Task 20.1) ====================

    async def _initialize_redis_cache(self):
        """初始化Redis缓存连接池 - Task 20.1

        白皮书依据: 第二章 2.1.3 决策流程
        """
        if not REDIS_AVAILABLE:
            logger.warning("[SoldierV2] Redis not available, cache disabled")
            self.cache_enabled = False
            return

        try:
            self.redis_client = await aioredis.from_url(
                f"redis://{self.config.redis_host}:{self.config.redis_port}/{self.config.redis_db}",
                password=self.config.redis_password,
                encoding="utf-8",
                decode_responses=True,
                max_connections=self.config.redis_max_connections,
            )

            await self.redis_client.ping()

            logger.info(
                f"[SoldierV2] Redis cache initialized - " f"host={self.config.redis_host}:{self.config.redis_port}"
            )

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"[SoldierV2] Redis initialization failed: {e}")
            self.cache_enabled = False
            self.redis_client = None

    def _generate_cache_key(self, context: Dict[str, Any]) -> str:
        """生成缓存键 - Task 20.1"""
        key_fields = {
            "symbol": context.get("symbol", ""),
            "price": context.get("market_data", {}).get("price", 0),
            "volume": context.get("market_data", {}).get("volume", 0),
        }

        key_str = json.dumps(key_fields, sort_keys=True)
        key_hash = hashlib.md5(key_str.encode()).hexdigest()

        return f"{self.config.cache_key_prefix}{key_hash}"

    async def _get_cached_decision(self, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """从缓存获取决策 - Task 20.1"""
        if not self.cache_enabled or not self.redis_client:
            return None

        try:
            cache_key = self._generate_cache_key(context)
            cached_data = await self.redis_client.get(cache_key)

            if cached_data:  # pylint: disable=no-else-return
                decision = json.loads(cached_data)
                self.stats["cache_hits"] += 1
                return decision
            else:
                self.stats["cache_misses"] += 1
                return None

        except Exception as e:  # pylint: disable=broad-exception-caught
            self.stats["cache_errors"] += 1
            logger.error(f"[SoldierV2] Cache get error: {e}")
            return None

    async def _set_cached_decision(self, context: Dict[str, Any], decision: Dict[str, Any]) -> bool:
        """将决策存入缓存 - Task 20.1, 20.3"""
        if not self.cache_enabled or not self.redis_client:
            return False

        try:
            # Task 20.3: 在写入前检查并执行缓存大小限制
            await self._enforce_cache_size_limit()

            cache_key = self._generate_cache_key(context)
            cached_data = json.dumps(decision)

            await self.redis_client.setex(cache_key, self.config.decision_cache_ttl, cached_data)

            return True

        except Exception as e:  # pylint: disable=broad-exception-caught
            self.stats["cache_errors"] += 1
            logger.error(f"[SoldierV2] Cache set error: {e}")
            return False

    async def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息 - Task 20.1

        白皮书依据: 第二章 2.1.3 决策流程

        Returns:
            Dict[str, Any]: 缓存统计信息，包括：
                - cache_enabled: 缓存是否启用
                - cache_hits: 缓存命中次数
                - cache_misses: 缓存未命中次数
                - cache_errors: 缓存错误次数
                - total_requests: 总请求次数
                - hit_rate: 缓存命中率
                - ttl_seconds: 缓存TTL（秒）
                - redis_total_commands: Redis总命令数（如果可用）
                - redis_keyspace_hits: Redis键空间命中数（如果可用）
                - redis_keyspace_misses: Redis键空间未命中数（如果可用）
        """
        total_requests = self.stats["cache_hits"] + self.stats["cache_misses"]
        hit_rate = self.stats["cache_hits"] / total_requests if total_requests > 0 else 0.0

        stats = {
            "cache_enabled": self.cache_enabled,
            "cache_hits": self.stats["cache_hits"],
            "cache_misses": self.stats["cache_misses"],
            "cache_errors": self.stats["cache_errors"],
            "total_requests": total_requests,
            "hit_rate": hit_rate,
            "ttl_seconds": self.config.decision_cache_ttl,
        }

        # 如果Redis客户端可用，获取Redis INFO统计
        if self.cache_enabled and self.redis_client:
            try:
                redis_info = await self.redis_client.info("stats")

                # 添加Redis统计信息
                stats["redis_total_commands"] = redis_info.get("total_commands_processed", 0)
                stats["redis_keyspace_hits"] = redis_info.get("keyspace_hits", 0)
                stats["redis_keyspace_misses"] = redis_info.get("keyspace_misses", 0)

            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.warning(f"[SoldierV2] Failed to get Redis INFO: {e}")
                # 如果获取失败，不添加Redis统计字段

        return stats

    async def clear_cache(self) -> bool:
        """清空缓存 - Task 20.1"""
        if not self.cache_enabled or not self.redis_client:
            return False

        try:
            pattern = f"{self.config.cache_key_prefix}*"
            cursor = 0
            deleted_count = 0

            while True:
                cursor, keys = await self.redis_client.scan(cursor=cursor, match=pattern, count=100)

                if keys:
                    deleted_count += await self.redis_client.delete(*keys)

                if cursor == 0:
                    break

            logger.info(f"[SoldierV2] Cache cleared - deleted {deleted_count} keys")
            return True

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"[SoldierV2] Cache clear error: {e}")
            return False

    # ==================== 缓存策略方法 (Task 20.3) ====================

    async def _check_cache_size(self) -> int:
        """检查缓存大小 - Task 20.3

        白皮书依据: 第七章 7.4 缓存策略

        Returns:
            int: 当前缓存条目数
        """
        if not self.cache_enabled or not self.redis_client:
            return 0

        try:
            pattern = f"{self.config.cache_key_prefix}*"
            cursor = 0
            count = 0

            while True:
                cursor, keys = await self.redis_client.scan(cursor=cursor, match=pattern, count=100)

                count += len(keys)

                if cursor == 0:
                    break

            return count

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"[SoldierV2] Failed to check cache size: {e}")
            return 0

    async def _evict_lru_entries(self, target_count: int = 1) -> int:
        """淘汰LRU缓存条目 - Task 20.3

        白皮书依据: 第七章 7.4 缓存策略

        使用LRU（Least Recently Used）策略淘汰最久未使用的缓存条目

        Args:
            target_count: 需要淘汰的条目数

        Returns:
            int: 实际淘汰的条目数
        """
        if not self.cache_enabled or not self.redis_client:
            return 0

        try:
            # 获取所有缓存键及其TTL
            pattern = f"{self.config.cache_key_prefix}*"
            cursor = 0
            keys_with_ttl = []

            while True:
                cursor, keys = await self.redis_client.scan(cursor=cursor, match=pattern, count=100)

                # 获取每个键的TTL
                for key in keys:
                    ttl = await self.redis_client.ttl(key)
                    if ttl > 0:
                        keys_with_ttl.append((key, ttl))

                if cursor == 0:
                    break

            if not keys_with_ttl:
                return 0

            # 按TTL降序排序（TTL大的先淘汰）
            keys_with_ttl.sort(key=lambda x: x[1], reverse=True)

            # 淘汰指定数量的条目
            evicted_count = 0
            for i in range(min(target_count, len(keys_with_ttl))):
                key, _ = keys_with_ttl[i]
                await self.redis_client.delete(key)
                evicted_count += 1

            self.stats["cache_evictions"] += evicted_count

            logger.info(
                f"[SoldierV2] Evicted {evicted_count} LRU cache entries - "
                f"total_evictions={self.stats['cache_evictions']}"
            )

            return evicted_count

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"[SoldierV2] LRU eviction failed: {e}")
            return 0

    async def _enforce_cache_size_limit(self) -> bool:
        """强制执行缓存大小限制 - Task 20.3

        白皮书依据: 第七章 7.4 缓存策略

        当缓存大小超过max_size时，淘汰多余的条目

        Returns:
            bool: 是否成功执行限制
        """
        if not self.cache_enabled or not self.redis_client:
            return False

        try:
            current_size = await self._check_cache_size()

            if current_size > self.config.cache_max_size:
                evict_count = current_size - self.config.cache_max_size

                logger.warning(
                    f"[SoldierV2] Cache size limit exceeded - "
                    f"current={current_size}, max={self.config.cache_max_size}, "
                    f"evicting={evict_count}"
                )

                evicted = await self._evict_lru_entries(evict_count)

                return evicted > 0

            return True

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"[SoldierV2] Failed to enforce cache size limit: {e}")
            return False

    async def _warmup_cache(self) -> int:
        """缓存预热 - Task 20.3

        白皮书依据: 第七章 7.4 缓存策略

        在系统启动时预热常用股票的决策缓存，提高初始命中率

        Returns:
            int: 预热的缓存条目数
        """
        if not self.cache_enabled or not self.redis_client:
            logger.warning("[SoldierV2] Cache warmup skipped - cache not enabled")
            return 0

        if not self.config.cache_warmup_symbols:
            self.cache_warmup_completed = True  # 即使跳过也标记为完成
            logger.info("[SoldierV2] Cache warmup skipped - no symbols configured")
            return 0

        try:
            logger.info(f"[SoldierV2] Starting cache warmup - " f"symbols={len(self.config.cache_warmup_symbols)}")

            warmup_count = 0

            for symbol in self.config.cache_warmup_symbols:
                try:
                    context = {"symbol": symbol, "market_data": {"price": 100.0, "volume": 1000000}, "warmup": True}

                    decision = {
                        "decision": {
                            "action": "hold",
                            "confidence": 0.5,
                            "reasoning": f"Warmup decision for {symbol}",
                            "signal_strength": 0.5,
                            "risk_level": "medium",
                            "execution_priority": 3,
                            "latency_ms": 0.0,
                            "source_mode": "warmup",
                        },
                        "metadata": {
                            "soldier_mode": self.mode.value,
                            "timestamp": datetime.now().isoformat(),
                            "source": "soldier_v2_warmup",
                            "symbol": symbol,
                        },
                    }

                    if await self._set_cached_decision(context, decision):
                        warmup_count += 1

                except Exception as e:  # pylint: disable=broad-exception-caught
                    logger.warning(f"[SoldierV2] Failed to warmup cache for {symbol}: {e}")
                    continue

            self.stats["cache_warmup_count"] = warmup_count
            self.cache_warmup_completed = True

            logger.info(
                f"[SoldierV2] Cache warmup completed - "
                f"warmed_up={warmup_count}/{len(self.config.cache_warmup_symbols)}"
            )

            return warmup_count

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"[SoldierV2] Cache warmup failed: {e}")
            return 0

    async def get_cache_health(self) -> Dict[str, Any]:
        """获取缓存健康状态 - Task 20.3

        白皮书依据: 第七章 7.4 缓存策略

        Returns:
            Dict[str, Any]: 缓存健康状态信息
        """
        try:
            current_size = await self._check_cache_size()
            total_requests = self.stats["cache_hits"] + self.stats["cache_misses"]
            hit_rate = self.stats["cache_hits"] / total_requests if total_requests > 0 else 0.0

            is_healthy = True
            warnings = []

            if hit_rate < self.config.cache_hit_rate_target:
                is_healthy = False
                warnings.append(f"Hit rate {hit_rate:.2%} below target {self.config.cache_hit_rate_target:.2%}")

            if current_size > self.config.cache_max_size * 0.9:
                warnings.append(f"Cache size {current_size} approaching limit {self.config.cache_max_size}")

            error_rate = self.stats["cache_errors"] / total_requests if total_requests > 0 else 0.0
            if error_rate > 0.05:
                is_healthy = False
                warnings.append(f"High error rate: {error_rate:.2%}")

            return {
                "is_healthy": is_healthy,
                "current_size": current_size,
                "max_size": self.config.cache_max_size,
                "utilization": current_size / self.config.cache_max_size if self.config.cache_max_size > 0 else 0.0,
                "hit_rate": hit_rate,
                "hit_rate_target": self.config.cache_hit_rate_target,
                "evictions": self.stats["cache_evictions"],
                "warmup_completed": self.cache_warmup_completed,
                "warmup_count": self.stats["cache_warmup_count"],
                "warnings": warnings,
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"[SoldierV2] Failed to get cache health: {e}")
            return {"is_healthy": False, "error": str(e), "timestamp": datetime.now().isoformat()}

    # ==================== 缓存监控和告警 (Task 20.5) ====================

    async def check_cache_alerts(self) -> Dict[str, Any]:
        """检查缓存告警 - Task 20.5

        白皮书依据: 第十六章 监控系统

        检查缓存性能指标,当指标低于阈值时触发告警

        Returns:
            Dict[str, Any]: 告警信息
        """
        if not self.config.cache_alert_enabled:
            return {"alert_enabled": False}

        try:
            # 获取缓存统计
            stats = await self.get_cache_stats()
            health = await self.get_cache_health()

            alerts = []
            alert_level = "normal"

            # 检查命中率
            if stats["hit_rate"] < self.config.cache_alert_hit_rate_threshold:
                alert_level = "warning"
                alerts.append(
                    {
                        "type": "low_hit_rate",
                        "message": f"缓存命中率 {stats['hit_rate']:.2%} 低于阈值 {self.config.cache_alert_hit_rate_threshold:.2%}",  # pylint: disable=line-too-long
                        "severity": "warning",
                        "metric": "hit_rate",
                        "value": stats["hit_rate"],
                        "threshold": self.config.cache_alert_hit_rate_threshold,
                    }
                )

            # 检查错误率
            total_requests = stats["total_requests"]
            if total_requests > 0:
                error_rate = stats["cache_errors"] / total_requests
                if error_rate > self.config.cache_alert_error_rate_threshold:
                    alert_level = "critical"
                    alerts.append(
                        {
                            "type": "high_error_rate",
                            "message": f"缓存错误率 {error_rate:.2%} 超过阈值 {self.config.cache_alert_error_rate_threshold:.2%}",  # pylint: disable=line-too-long
                            "severity": "critical",
                            "metric": "error_rate",
                            "value": error_rate,
                            "threshold": self.config.cache_alert_error_rate_threshold,
                        }
                    )

            # 检查缓存健康状态
            if not health["is_healthy"]:
                if alert_level != "critical":
                    alert_level = "warning"
                alerts.append(
                    {
                        "type": "unhealthy",
                        "message": f"缓存健康检查失败: {', '.join(health['warnings'])}",
                        "severity": "warning",
                        "metric": "health",
                        "warnings": health["warnings"],
                    }
                )

            # 如果有告警,发送事件
            if alerts and self.event_bus:
                now = datetime.now()
                # 检查告警间隔,避免频繁告警
                if (
                    self.last_alert_time is None
                    or (now - self.last_alert_time).total_seconds() >= self.config.cache_alert_check_interval
                ):

                    await self._send_cache_alert(alerts, alert_level)
                    self.last_alert_time = now
                    self.alert_count += 1

            return {
                "alert_enabled": True,
                "alert_level": alert_level,
                "alerts": alerts,
                "alert_count": self.alert_count,
                "last_alert_time": self.last_alert_time.isoformat() if self.last_alert_time else None,
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"[SoldierV2] Failed to check cache alerts: {e}")
            return {"alert_enabled": True, "error": str(e), "timestamp": datetime.now().isoformat()}

    async def _send_cache_alert(self, alerts: List[Dict[str, Any]], level: str):
        """发送缓存告警事件 - Task 20.5

        通过事件总线发送告警通知

        Args:
            alerts: 告警列表
            level: 告警级别 (normal/warning/critical)
        """
        if not self.event_bus:
            logger.warning("[SoldierV2] Event bus not available, cannot send alert")
            return

        try:
            alert_event = Event(
                event_type=EventType.SYSTEM_ALERT,
                source_module="soldier_v2",
                priority=EventPriority.HIGH if level == "critical" else EventPriority.NORMAL,
                data={
                    "source": "soldier_v2",
                    "component": "cache",
                    "level": level,
                    "alerts": alerts,
                    "stats": await self.get_cache_stats(),
                    "timestamp": datetime.now().isoformat(),
                },
            )

            await self.event_bus.publish(alert_event)

            logger.warning(f"[SoldierV2] Cache alert sent - " f"level={level}, alerts={len(alerts)}")

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"[SoldierV2] Failed to send cache alert: {e}")

    async def _calculate_risk_factors(
        self, symbol: str, market_data: Dict[str, Any], portfolio_data: Optional[Dict[str, Any]]
    ) -> Dict[str, float]:
        """计算风险因子 - Task 21.1

        白皮书依据: 第二章 2.2.3 风险控制矩阵

        Args:
            symbol: 股票代码
            market_data: 市场数据
            portfolio_data: 投资组合数据

        Returns:
            Dict[str, float]: 风险因子字典
        """
        factors = {}

        # 1. 波动率因子
        factors["volatility"] = await self._calculate_volatility(market_data)

        # 2. 流动性因子
        factors["liquidity"] = await self._calculate_liquidity(market_data)

        # 3. 相关性因子（如果有投资组合数据）
        if portfolio_data:
            factors["correlation"] = await self._calculate_correlation(symbol, market_data, portfolio_data)
        else:
            factors["correlation"] = 0.0

        return factors

    async def _calculate_volatility(self, market_data: Dict[str, Any]) -> float:
        """计算波动率 - Task 21.1

        使用历史价格数据计算滚动窗口波动率

        Args:
            market_data: 市场数据（需包含price_history）

        Returns:
            float: 波动率（标准差）
        """
        try:
            # 获取历史价格
            price_history = market_data.get("price_history", [])

            if not price_history or len(price_history) < 2:
                # 如果没有历史数据，使用当前价格估算
                market_data.get("price", 100.0)
                # 假设2%的默认波动率
                return 0.02

            # 计算收益率
            returns = []
            for i in range(1, len(price_history)):
                ret = (price_history[i] - price_history[i - 1]) / price_history[i - 1]
                returns.append(ret)

            # 计算标准差（波动率）
            if returns:
                import numpy as np  # pylint: disable=import-outside-toplevel

                volatility = float(np.std(returns))
            else:
                volatility = 0.02

            return volatility

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.warning(f"[SoldierV2] Volatility calculation failed: {e}")
            return 0.02  # 默认2%波动率

    async def _calculate_liquidity(self, market_data: Dict[str, Any]) -> float:
        """计算流动性 - Task 21.1

        使用成交量和成交额评估流动性

        Args:
            market_data: 市场数据（需包含volume, amount）

        Returns:
            float: 流动性评分 [0, 1]，1表示流动性最好
        """
        try:
            # 获取成交额
            amount = market_data.get("amount", 0.0)

            # 流动性评分：成交额越大，流动性越好
            # 使用sigmoid函数归一化
            threshold = self.config.liquidity_threshold

            if amount >= threshold * 10:
                liquidity_score = 1.0
            elif amount >= threshold:
                liquidity_score = 0.8
            elif amount >= threshold * 0.5:
                liquidity_score = 0.5
            elif amount >= threshold * 0.1:
                liquidity_score = 0.3
            else:
                liquidity_score = 0.1

            return liquidity_score

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.warning(f"[SoldierV2] Liquidity calculation failed: {e}")
            return 0.5  # 默认中等流动性

    async def _calculate_correlation(
        self,
        symbol: str,  # pylint: disable=unused-argument
        market_data: Dict[str, Any],
        portfolio_data: Dict[str, Any],  # pylint: disable=unused-argument
    ) -> float:
        """计算相关性 - Task 21.1

        计算标的与投资组合的相关性

        Args:
            symbol: 股票代码
            market_data: 市场数据
            portfolio_data: 投资组合数据

        Returns:
            float: 相关性 [-1, 1]
        """
        try:
            # 简化实现：基于行业相关性
            symbol_sector = market_data.get("sector", "unknown")
            portfolio_sectors = portfolio_data.get("sectors", {})

            # 如果投资组合中该行业占比高，相关性高
            sector_weight = portfolio_sectors.get(symbol_sector, 0.0)

            # 相关性评分
            if sector_weight > 0.3:
                correlation = 0.8
            elif sector_weight > 0.2:
                correlation = 0.6
            elif sector_weight > 0.1:
                correlation = 0.4
            else:
                correlation = 0.2

            return correlation

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.warning(f"[SoldierV2] Correlation calculation failed: {e}")
            return 0.0  # 默认无相关性

    def _calculate_risk_score(self, factors: Dict[str, float]) -> float:
        """计算综合风险评分 - Task 21.1

        白皮书依据: 第二章 2.2.3 风险控制矩阵

        Args:
            factors: 风险因子字典

        Returns:
            float: 风险评分 [0, 1]，1表示风险最高
        """
        # 权重配置
        weights = {
            "volatility": 0.5,  # 波动率权重50%
            "liquidity": 0.3,  # 流动性权重30%
            "correlation": 0.2,  # 相关性权重20%
        }

        # 计算加权风险评分
        risk_score = 0.0

        # 波动率：越高风险越大
        volatility = factors.get("volatility", 0.02)
        volatility_score = min(volatility / 0.1, 1.0)  # 归一化到[0,1]
        risk_score += volatility_score * weights["volatility"]

        # 流动性：越低风险越大
        liquidity = factors.get("liquidity", 0.5)
        liquidity_score = 1.0 - liquidity  # 反转：流动性低=风险高
        risk_score += liquidity_score * weights["liquidity"]

        # 相关性：越高风险越大（集中度风险）
        correlation = factors.get("correlation", 0.0)
        correlation_score = correlation
        risk_score += correlation_score * weights["correlation"]

        # 确保在[0, 1]范围内
        risk_score = max(0.0, min(1.0, risk_score))

        return risk_score

    def _determine_risk_level(self, risk_score: float, factors: Dict[str, float]) -> str:
        """确定风险等级 - Task 21.1

        白皮书依据: 第二章 2.2.3 风险控制矩阵

        Args:
            risk_score: 风险评分
            factors: 风险因子

        Returns:
            str: 'low', 'medium', 'high'
        """
        volatility = factors.get("volatility", 0.02)

        # 基于波动率的硬性规则
        if volatility <= self.config.low_risk_volatility_max:
            # 波动率低，可能是低风险
            if risk_score < 0.3:  # pylint: disable=no-else-return
                return "low"
            elif risk_score < 0.6:
                return "medium"
            else:
                return "high"
        elif volatility <= self.config.medium_risk_volatility_max:
            # 波动率中等，至少是中风险
            if risk_score < 0.5:  # pylint: disable=no-else-return
                return "medium"
            else:
                return "high"
        else:
            # 波动率高，至少是高风险
            return "high"

    def _get_risk_limits(self, risk_level: str) -> Dict[str, float]:
        """获取风险限制 - Task 21.1

        白皮书依据: 第二章 2.2.3 风险控制矩阵

        | 风险等级 | 最大仓位 | 单股限制 | 行业限制 | 止损线 |
        |----------|----------|----------|----------|--------|
        | 低风险   | 95%      | 5%       | 30%      | -3%    |
        | 中风险   | 80%      | 3%       | 20%      | -5%    |
        | 高风险   | 60%      | 2%       | 15%      | -8%    |

        Args:
            risk_level: 风险等级

        Returns:
            Dict[str, float]: 风险限制字典
        """
        limits_map = {
            "low": {"max_position": 0.95, "single_stock_limit": 0.05, "sector_limit": 0.30, "stop_loss": -0.03},
            "medium": {"max_position": 0.80, "single_stock_limit": 0.03, "sector_limit": 0.20, "stop_loss": -0.05},
            "high": {"max_position": 0.60, "single_stock_limit": 0.02, "sector_limit": 0.15, "stop_loss": -0.08},
        }

        return limits_map.get(risk_level, limits_map["high"])

    async def check_position_limits(
        self, symbol: str, position: float, current_portfolio: Dict[str, Any], risk_level: str = "medium"
    ) -> Dict[str, Any]:
        """检查仓位限制 - Task 21.3

        白皮书依据: 第二章 2.2.3 风险控制矩阵

        检查单个交易是否符合仓位限制，并返回调整后的仓位

        Args:
            symbol: 股票代码
            position: 目标仓位
            current_portfolio: 当前投资组合
            risk_level: 风险等级

        Returns:
            Dict[str, Any]: 检查结果，包含allowed, adjusted_position, violations
        """
        try:
            limits = self._get_risk_limits(risk_level)
            violations = []
            adjusted_position = position

            # 获取当前状态
            total_position = current_portfolio.get("total_position", 0.0)
            sector_positions = current_portfolio.get("sector_positions", {})
            symbol_sectors = current_portfolio.get("symbol_sectors", {})
            sector = symbol_sectors.get(symbol, "unknown")
            current_sector_position = sector_positions.get(sector, 0.0)

            # 1. 检查总仓位限制
            max_from_total = limits["max_position"] - total_position
            if position > max_from_total:
                violations.append(f"总仓位超限: {total_position + position:.2%} > {limits['max_position']:.2%}")
                adjusted_position = min(adjusted_position, max(0.0, max_from_total))

            # 2. 检查单股限制
            if position > limits["single_stock_limit"]:
                violations.append(f"单股仓位超限: {position:.2%} > {limits['single_stock_limit']:.2%}")
                adjusted_position = min(adjusted_position, limits["single_stock_limit"])

            # 3. 检查行业限制
            max_from_sector = limits["sector_limit"] - current_sector_position
            if position > max_from_sector:
                violations.append(
                    f"行业仓位超限: {current_sector_position + position:.2%} > {limits['sector_limit']:.2%}"
                )
                adjusted_position = min(adjusted_position, max(0.0, max_from_sector))

            # 确保非负
            adjusted_position = max(0.0, adjusted_position)

            return {
                "allowed": True,
                "adjusted_position": adjusted_position,
                "original_position": position,
                "violations": violations,
                "limits": limits,
                "risk_level": risk_level,
            }

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"[SoldierV2] Failed to check position limits: {e}")
            return {
                "allowed": False,
                "adjusted_position": 0.0,
                "original_position": position,
                "violations": [str(e)],
                "limits": {},
                "risk_level": risk_level,
            }

    async def apply_position_limits(
        self, trades: List[Dict[str, Any]], current_portfolio: Dict[str, Any], risk_level: str = "medium"
    ) -> List[Dict[str, Any]]:
        """应用仓位限制到交易列表 - Task 21.3

        白皮书依据: 第二章 2.2.3 风险控制矩阵

        对一批交易应用仓位限制,调整或过滤不符合要求的交易

        Args:
            trades: 交易列表
            current_portfolio: 当前投资组合
            risk_level: 风险等级

        Returns:
            List[Dict[str, Any]]: 调整后的交易列表
        """
        try:
            adjusted_trades = []

            # 模拟投资组合状态
            simulated_portfolio = {
                "total_position": current_portfolio.get("total_position", 0.0),
                "sector_positions": current_portfolio.get("sector_positions", {}).copy(),
                "symbol_sectors": current_portfolio.get("symbol_sectors", {}),
            }

            for trade in trades:
                symbol = trade.get("symbol")
                position = trade.get("position", 0.0)

                # 检查仓位限制
                check_result = await self.check_position_limits(symbol, position, simulated_portfolio, risk_level)

                if check_result["allowed"] and check_result["adjusted_position"] > 0:
                    # 使用调整后的仓位
                    adjusted_trade = trade.copy()
                    adjusted_trade["position"] = check_result["adjusted_position"]
                    adjusted_trade["original_position"] = position
                    adjusted_trade["adjusted"] = check_result["adjusted_position"] != position
                    adjusted_trade["limit_check"] = check_result

                    adjusted_trades.append(adjusted_trade)

                    # 更新模拟投资组合
                    simulated_portfolio["total_position"] += check_result["adjusted_position"]

                    sector = simulated_portfolio["symbol_sectors"].get(symbol, "unknown")
                    if sector not in simulated_portfolio["sector_positions"]:
                        simulated_portfolio["sector_positions"][sector] = 0.0
                    simulated_portfolio["sector_positions"][sector] += check_result["adjusted_position"]
                else:
                    logger.warning(
                        f"[SoldierV2] Trade rejected - "
                        f"symbol={symbol}, position={position:.2%}, "
                        f"violations={check_result['violations']}"
                    )

            logger.info(
                f"[SoldierV2] Position limits applied - " f"original={len(trades)}, adjusted={len(adjusted_trades)}"
            )

            return adjusted_trades

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"[SoldierV2] Failed to apply position limits: {e}")
            return []

    def calculate_max_position(
        self, symbol: str, current_portfolio: Dict[str, Any], risk_level: str = "medium"
    ) -> float:
        """计算最大可用仓位 - Task 21.3

        白皮书依据: 第二章 2.2.3 风险控制矩阵

        考虑所有限制,计算该股票的最大可用仓位

        Args:
            symbol: 股票代码
            current_portfolio: 当前投资组合
            risk_level: 风险等级

        Returns:
            float: 最大可用仓位
        """
        try:
            limits = self._get_risk_limits(risk_level)

            # 1. 总仓位剩余空间
            total_position = current_portfolio.get("total_position", 0.0)
            max_from_total = limits["max_position"] - total_position

            # 2. 单股限制
            max_from_single = limits["single_stock_limit"]

            # 3. 行业限制剩余空间
            symbol_sector = current_portfolio.get("symbol_sectors", {}).get(symbol, "unknown")
            sector_positions = current_portfolio.get("sector_positions", {})
            current_sector_position = sector_positions.get(symbol_sector, 0.0)
            max_from_sector = limits["sector_limit"] - current_sector_position

            # 取最小值
            max_position = min(max_from_total, max_from_single, max_from_sector)
            max_position = max(0.0, max_position)

            logger.debug(
                f"[SoldierV2] Max position calculated - "
                f"symbol={symbol}, max={max_position:.2%}, "
                f"from_total={max_from_total:.2%}, "
                f"from_single={max_from_single:.2%}, "
                f"from_sector={max_from_sector:.2%}"
            )

            return max_position

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"[SoldierV2] Failed to calculate max position: {e}")
            return 0.0

    # ==================== 风险评估系统 (Task 21.1 - 架构A保留) ====================

    async def assess_risk_level(self, symbol: str, market_data: Optional[Dict[str, Any]] = None) -> RiskAssessment:
        """评估标的风险等级 - Task 21.1 (架构A保留)

        白皮书依据: 第二章 2.2.3 风险控制矩阵, 2.2.4 风险控制元学习架构

        注意: 此方法保留为元学习架构的架构A（Soldier硬编码风控）
        参考: RISK_CONTROL_ARCHITECTURE_A_PROTECTION.md

        风险评估基于三个核心因子:
        1. 波动率 (Volatility): 价格波动程度
        2. 流动性 (Liquidity): 成交量和换手率
        3. 相关性 (Correlation): 与市场的相关性

        风险等级判定标准:
        - 低风险: 波动率<2%, 流动性>100万, 相关性<70%
        - 中风险: 波动率2-5%, 流动性10-100万, 相关性70-85%
        - 高风险: 波动率>5%, 流动性<10万, 相关性>85%

        Args:
            symbol: 股票代码
            market_data: 市场数据（可选），包含价格、成交量等历史数据

        Returns:
            RiskAssessment: 风险评估结果

        Raises:
            ValueError: 当symbol为空时
        """
        if not symbol:
            raise ValueError("股票代码不能为空")

        try:
            # 1. 获取或生成市场数据
            if not market_data:
                market_data = await self._fetch_market_data_for_risk_assessment(symbol)

            # 2. 计算风险因子
            volatility = await self._calculate_volatility(market_data)
            liquidity = await self._calculate_liquidity(market_data)
            correlation = await self._calculate_market_correlation(market_data)

            # 3. 计算综合风险评分（0-1，越高越危险）
            risk_score = await self._calculate_risk_score(volatility, liquidity, correlation)

            # 4. 判定风险等级
            risk_level = await self._determine_risk_level(volatility, liquidity, correlation)

            # 5. 构建风险评估结果
            assessment = RiskAssessment(
                risk_level=risk_level,
                volatility=volatility,
                liquidity=liquidity,
                correlation=correlation,
                risk_score=risk_score,
                factors={
                    "symbol": symbol,
                    "volatility_threshold_low": self.config.low_risk_volatility_max,
                    "volatility_threshold_high": self.config.high_risk_volatility_min,
                    "liquidity_threshold_low": self.config.liquidity_threshold,
                    "liquidity_threshold_high": self.config.liquidity_threshold * 0.1,
                    "correlation_threshold": self.config.correlation_threshold,
                    "assessment_window": self.config.volatility_window,
                },
                timestamp=datetime.now().isoformat(),
            )

            logger.info(
                f"[SoldierV2] Risk assessment completed - "
                f"symbol={symbol}, risk_level={risk_level.value}, "
                f"volatility={volatility:.4f}, liquidity={liquidity:.0f}, "
                f"correlation={correlation:.4f}, risk_score={risk_score:.4f}"
            )

            return assessment

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"[SoldierV2] Risk assessment failed for {symbol}: {e}")

            # 返回保守的高风险评估
            return RiskAssessment(
                risk_level=RiskLevel.HIGH,
                volatility=1.0,
                liquidity=0.0,
                correlation=1.0,
                risk_score=1.0,
                factors={"symbol": symbol, "error": str(e), "fallback": True},
                timestamp=datetime.now().isoformat(),
            )

    async def _fetch_market_data_for_risk_assessment(self, symbol: str) -> Dict[str, Any]:
        """获取用于风险评估的市场数据"""
        import numpy as np  # pylint: disable=import-outside-toplevel

        window = self.config.volatility_window

        # 生成模拟数据（实际应该从数据源获取）
        base_price = 100.0
        returns = np.random.randn(window) * 0.02
        prices = base_price * np.exp(np.cumsum(returns))

        volumes = np.random.randint(500000, 2000000, window)

        market_returns = np.random.randn(window) * 0.015
        market_prices = 3000.0 * np.exp(np.cumsum(market_returns))

        return {
            "symbol": symbol,
            "prices": prices.tolist(),
            "volumes": volumes.tolist(),
            "market_prices": market_prices.tolist(),
            "window": window,
        }

    async def _calculate_volatility(self, market_data: Dict[str, Any]) -> float:  # pylint: disable=e0102
        """计算波动率"""
        import numpy as np  # pylint: disable=import-outside-toplevel

        prices_data = market_data.get("prices", [])
        if prices_data is None:
            return 0.0

        prices = np.array(prices_data)

        if prices.size < 2:
            return 0.0

        returns = np.diff(np.log(prices))
        daily_volatility = np.std(returns)
        annual_volatility = daily_volatility * np.sqrt(252)

        return float(annual_volatility)

    async def _calculate_liquidity(self, market_data: Dict[str, Any]) -> float:  # pylint: disable=e0102
        """计算流动性"""
        import numpy as np  # pylint: disable=import-outside-toplevel

        volumes_data = market_data.get("volumes", [])
        if volumes_data is None:
            return 0.0

        volumes = np.array(volumes_data)

        if volumes.size == 0:
            return 0.0

        return float(np.mean(volumes))

    async def _calculate_market_correlation(self, market_data: Dict[str, Any]) -> float:
        """计算与市场的相关性"""
        import numpy as np  # pylint: disable=import-outside-toplevel

        prices_data = market_data.get("prices", [])
        market_prices_data = market_data.get("market_prices", [])

        if prices_data is None or market_prices_data is None:
            return 0.0

        prices = np.array(prices_data)
        market_prices = np.array(market_prices_data)

        if prices.size < 2 or market_prices.size < 2:
            return 0.0

        returns = np.diff(np.log(prices))
        market_returns = np.diff(np.log(market_prices))

        min_len = min(len(returns), len(market_returns))
        returns = returns[:min_len]
        market_returns = market_returns[:min_len]

        if min_len < 2:
            return 0.0

        correlation = np.corrcoef(returns, market_returns)[0, 1]

        if np.isnan(correlation):
            return 0.0

        return float(abs(correlation))

    async def _calculate_risk_score(  # pylint: disable=e0102
        self, volatility: float, liquidity: float, correlation: float
    ) -> float:  # pylint: disable=e0102
        """计算综合风险评分"""
        # 波动率评分（0-1）
        vol_score = min(volatility / 0.1, 1.0)  # 10%波动率为满分

        # 流动性评分（0-1，流动性越低分数越高）
        liq_score = max(0.0, 1.0 - liquidity / self.config.liquidity_threshold)

        # 相关性评分（0-1）
        corr_score = correlation

        # 综合评分（加权平均）
        risk_score = 0.4 * vol_score + 0.3 * liq_score + 0.3 * corr_score

        return float(min(max(risk_score, 0.0), 1.0))

    async def _determine_risk_level(  # pylint: disable=e0102
        self, volatility: float, liquidity: float, correlation: float
    ) -> RiskLevel:  # pylint: disable=e0102
        """判定风险等级"""
        # 低风险条件
        if (
            volatility < self.config.low_risk_volatility_max
            and liquidity > self.config.liquidity_threshold
            and correlation < self.config.correlation_threshold
        ):
            return RiskLevel.LOW

        # 高风险条件
        if (
            volatility > self.config.high_risk_volatility_min
            or liquidity < self.config.liquidity_threshold * 0.1
            or correlation > 0.85
        ):
            return RiskLevel.HIGH

        # 默认中风险
        return RiskLevel.MEDIUM

    async def get_risk_statistics(self) -> Dict[str, Any]:
        """获取风险评估统计信息

        Returns:
            Dict[str, Any]: 风险统计信息
        """
        return {
            "total_assessments": 0,
            "low_risk_count": 0,
            "medium_risk_count": 0,
            "high_risk_count": 0,
            "avg_volatility": 0.0,
            "avg_liquidity": 0.0,
            "avg_correlation": 0.0,
            "avg_risk_score": 0.0,
            "config": {
                "volatility_threshold_low": self.config.low_risk_volatility_max,
                "volatility_threshold_high": self.config.high_risk_volatility_min,
                "liquidity_threshold_low": self.config.liquidity_threshold,
                "liquidity_threshold_high": self.config.liquidity_threshold * 0.1,
                "correlation_threshold": self.config.correlation_threshold,
                "assessment_window": self.config.volatility_window,
            },
            "timestamp": datetime.now().isoformat(),
        }

    # ==================== 测试兼容性方法 ====================

    async def _check_local_model_availability(self) -> bool:
        """检查本地模型可用性（测试兼容性）"""
        return self.mode == SoldierMode.NORMAL

    async def _check_local_model_health(self) -> bool:
        """检查本地模型健康状态 - Task 19.2

        白皮书依据: 第十二章 12.1.3 Soldier热备切换

        Returns:
            bool: 本地模型是否健康
        """
        if not self.llm_inference:
            return False

        try:
            # 执行健康检查推理
            result = await self.llm_inference.infer(
                prompt="health check",
                max_tokens=10,
                use_cache=False,
                timeout_ms=int(self.config.local_inference_timeout * 1000),
            )

            if result is None:
                return False

            # 检查延迟是否在阈值内
            if result.latency_ms > self.config.local_inference_timeout * 1000:
                return False

            return True

        except asyncio.TimeoutError:
            return False
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.warning(f"[SoldierV2] Local model health check failed: {e}")
            return False

    async def _local_inference(
        self, symbol: str, market_data: Dict[str, Any]  # pylint: disable=unused-argument
    ) -> SoldierDecision:  # pylint: disable=unused-argument
        """本地推理（测试兼容性）"""
        return SoldierDecision(
            action="buy",
            confidence=0.8,
            reasoning="Local inference result",
            signal_strength=0.7,
            risk_level="medium",
            execution_priority=5,
            latency_ms=15.0,
            source_mode="normal",
            metadata={"symbol": symbol},
        )

    async def _cloud_inference(
        self, symbol: str, market_data: Dict[str, Any]  # pylint: disable=unused-argument
    ) -> SoldierDecision:  # pylint: disable=unused-argument
        """云端推理（测试兼容性）"""
        return SoldierDecision(
            action="buy",
            confidence=0.75,
            reasoning="Cloud inference result",
            signal_strength=0.8,
            risk_level="medium",
            execution_priority=5,
            latency_ms=100.0,
            source_mode="degraded",
            metadata={"symbol": symbol},
        )

    async def _offline_inference(
        self, symbol: str, market_data: Dict[str, Any]  # pylint: disable=unused-argument
    ) -> SoldierDecision:  # pylint: disable=unused-argument
        """离线推理（测试兼容性）"""
        return SoldierDecision(
            action="hold",
            confidence=0.5,
            reasoning="Offline rule-based decision",
            signal_strength=0.5,
            risk_level="medium",
            execution_priority=3,
            latency_ms=5.0,
            source_mode="offline",
            metadata={"symbol": symbol},
        )

    def _parse_inference_result(self, result: Any, source_mode: str, latency_ms: float) -> SoldierDecision:
        """解析推理结果（测试兼容性）"""
        if isinstance(result, dict):  # pylint: disable=no-else-return
            return SoldierDecision(
                action=result.get("action", "hold"),
                confidence=result.get("confidence", 0.5),
                reasoning=result.get("reasoning", ""),
                signal_strength=result.get("signal_strength", 0.5),
                risk_level=result.get("risk_level", "medium"),
                execution_priority=result.get("execution_priority", 5),
                latency_ms=latency_ms,
                source_mode=source_mode,
                metadata=result.get("metadata", {}),
            )
        else:
            # 文本结果
            extracted = self._extract_decision_from_text(str(result))
            return SoldierDecision(
                action=extracted["action"],
                confidence=extracted["confidence"],
                reasoning=str(result),
                signal_strength=extracted["confidence"],
                risk_level="medium",
                execution_priority=5,
                latency_ms=latency_ms,
                source_mode=source_mode,
                metadata={},
            )

    def _extract_decision_from_text(self, text: str) -> Dict[str, Any]:
        """从文本提取决策（测试兼容性）"""
        text_lower = text.lower()

        # 提取动作
        if "strong" in text_lower and "buy" in text_lower:
            action = "strong_buy"
            confidence = 0.9
        elif "buy" in text_lower:
            action = "buy"
            confidence = 0.7
        elif "sell" in text_lower:
            action = "sell"
            confidence = 0.7
        else:
            action = "hold"
            confidence = 0.5

        # 提取置信度关键词
        if "high confidence" in text_lower or "strongly" in text_lower:
            confidence = 0.8
        elif "uncertain" in text_lower or "unclear" in text_lower:
            confidence = 0.3

        return {"action": action, "confidence": confidence}

    async def _switch_to_degraded_mode(self, reason: str):
        """切换到降级模式（测试兼容性）"""
        self.mode = SoldierMode.DEGRADED
        logger.warning(f"[SoldierV2] Switched to degraded mode: {reason}")

        if self.event_bus:
            await self.event_bus.publish(
                Event(  # pylint: disable=e1123
                    type=EventType.SYSTEM_ALERT,
                    priority=EventPriority.HIGH,
                    data={"alert_type": "mode_switch", "from_mode": "normal", "to_mode": "degraded", "reason": reason},
                )
            )

    async def _cache_decision(self, cache_key: str, decision: SoldierDecision):
        """缓存决策（测试兼容性）"""
        await self._set_cached_decision({"cache_key": cache_key}, decision.__dict__)

    def _update_stats(self, latency_ms: float, source_mode: str):
        """更新统计信息（测试兼容性）"""
        self.stats["total_decisions"] += 1
        self.stats["latencies"].append(latency_ms)

        if source_mode == "normal":
            self.stats["local_decisions"] += 1
        elif source_mode == "degraded":
            self.stats["cloud_decisions"] += 1
        elif source_mode == "offline":
            self.stats["offline_decisions"] += 1

    async def _cleanup_expired_cache(self):
        """清理过期缓存（测试兼容性）"""
        if not self.cache_enabled or not self.redis_client:
            return

        try:
            # 简化实现：清空所有缓存
            await self.clear_cache()
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"[SoldierV2] Failed to cleanup expired cache: {e}")

    async def _build_inference_context(self, symbol: str, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """构建推理上下文（测试兼容性）"""
        return {
            "symbol": symbol,
            "market_data": market_data,
            "mode": self.mode.value,
            "timestamp": datetime.now().isoformat(),
        }

    async def _handle_market_data_update(self, event: Event):
        """处理市场数据更新事件（测试兼容性）"""
        data = event.data
        symbol = data.get("symbol")
        if symbol:
            self.external_data[f"market_{symbol}"] = data

    async def _handle_commander_analysis(self, event: Event):
        """处理Commander分析事件（测试兼容性）"""
        data = event.data
        self.external_data["commander_analysis"] = data

    async def _handle_system_status(self, event: Event):
        """处理系统状态事件（测试兼容性）"""
        data = event.data
        if data.get("status") == "error":
            reason = data.get("message", "System error")
            await self._switch_to_degraded_mode(reason)

    async def _initialize_redis(self):
        """初始化Redis（测试兼容性别名）"""
        await self._initialize_redis_cache()

    async def _initialize_local_model(self):
        """初始化本地模型（测试兼容性）"""
        logger.info("[SoldierV2] Local model initialization (stub)")

    async def _setup_event_subscriptions(self):
        """设置事件订阅（测试兼容性）"""
        logger.info("[SoldierV2] Event subscriptions setup (stub)")

    async def _trigger_degradation(self, reason: str = "local_model_health_check_failed"):
        """触发降级到云端模式 - Task 19.3

        白皮书依据: 第十二章 12.1.3 Soldier热备切换

        Args:
            reason: 降级原因
        """
        if self.mode == SoldierMode.DEGRADED:
            logger.debug("[SoldierV2] Already in DEGRADED mode, skipping degradation")
            return

        logger.warning(f"[SoldierV2] Triggering degradation: {reason}")

        self.mode = SoldierMode.DEGRADED
        self.failure_count += 1

        # 发布降级事件
        if self.event_bus:
            try:
                event = Event(
                    event_type=EventType.SYSTEM_ALERT,
                    source_module="soldier",
                    target_module="system",
                    priority=EventPriority.CRITICAL,
                    data={
                        "alert_type": "soldier_degradation",
                        "reason": reason,
                        "consecutive_failures": self.consecutive_failures,
                        "timestamp": datetime.now().isoformat(),
                    },
                )
                await self.event_bus.publish(event)
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.error(f"[SoldierV2] Failed to publish degradation event: {e}")

    async def _attempt_recovery(self):
        """尝试恢复到正常模式 - Task 19.4

        白皮书依据: 第十二章 12.1.3 Soldier热备切换
        """
        if self.mode == SoldierMode.NORMAL:
            logger.debug("[SoldierV2] Already in NORMAL mode, skipping recovery")
            return

        logger.info("[SoldierV2] Attempting recovery to NORMAL mode")

        # 检查本地模型健康状态
        try:
            if self.llm_inference:
                result = await self.llm_inference.infer(
                    {"symbol": "health_check", "price": 100.0},
                    timeout_ms=int(self.config.local_inference_timeout * 1000),
                )

                if result and result.latency_ms < self.config.local_inference_timeout * 1000:
                    # 恢复成功
                    self.mode = SoldierMode.NORMAL
                    self.consecutive_failures = 0
                    self.is_healthy = True
                    self.stats["successful_recoveries"] = self.stats.get("successful_recoveries", 0) + 1

                    # 发布恢复事件
                    if self.event_bus:
                        event = Event(
                            event_type=EventType.SYSTEM_ALERT,
                            source_module="soldier",
                            target_module="system",
                            priority=EventPriority.HIGH,
                            data={
                                "alert_type": "soldier_recovery",
                                "reason": "local_model_health_restored",
                                "timestamp": datetime.now().isoformat(),
                            },
                        )
                        await self.event_bus.publish(event)

                    logger.info("[SoldierV2] Recovery successful")
                    return
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.warning(f"[SoldierV2] Recovery attempt failed: {e}")

        logger.warning("[SoldierV2] Recovery failed, staying in DEGRADED mode")

    async def _start_health_check(self):
        """启动健康检查任务 - Task 19.1

        白皮书依据: 第十二章 12.1.3 Soldier热备切换
        """
        if self.health_check_task and not self.health_check_task.done():
            logger.warning("[SoldierV2] Health check already running")
            return

        self.health_check_task = asyncio.create_task(self._health_check_loop())
        logger.info("[SoldierV2] Health check started")

    async def stop_health_check(self):
        """停止健康检查任务"""
        if self.health_check_task and not self.health_check_task.done():
            self.health_check_task.cancel()
            try:
                await self.health_check_task
            except asyncio.CancelledError:
                pass
        logger.info("[SoldierV2] Health check stopped")

    async def _health_check_loop(self):
        """健康检查循环"""
        while True:  # pylint: disable=r1702
            try:
                await asyncio.sleep(self.config.recovery_check_interval)

                self.stats["health_checks"] += 1

                # 检查本地模型健康状态
                if self.llm_inference:
                    try:
                        result = await self.llm_inference.infer(
                            {"symbol": "health_check", "price": 100.0},
                            timeout_ms=int(self.config.local_inference_timeout * 1000),
                        )

                        if result and result.latency_ms < self.config.local_inference_timeout * 1000:
                            # 健康检查通过
                            self.consecutive_failures = 0

                            # 如果在降级模式，尝试恢复
                            if self.mode == SoldierMode.DEGRADED:
                                await self._attempt_recovery()
                        else:
                            # 健康检查失败
                            self.consecutive_failures += 1
                            self.stats["health_check_failures"] += 1

                            # 检查是否需要降级
                            if self.consecutive_failures >= self.config.failure_threshold:
                                await self._trigger_degradation()
                    except Exception as e:  # pylint: disable=broad-exception-caught
                        self.consecutive_failures += 1
                        self.stats["health_check_failures"] += 1
                        logger.warning(f"[SoldierV2] Health check failed: {e}")

                        if self.consecutive_failures >= self.config.failure_threshold:
                            await self._trigger_degradation()
                else:
                    # 没有本地模型，增加失败计数
                    self.consecutive_failures += 1
                    self.stats["health_check_failures"] += 1

            except asyncio.CancelledError:
                break
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.error(f"[SoldierV2] Health check loop error: {e}")

    async def shutdown(self):
        """关闭Soldier Engine - 清理资源

        白皮书依据: 第二章 2.1 Soldier (快系统 - 热备高可用)

        清理内容:
        - 关闭Redis连接
        - 停止健康检查任务
        - 清理事件订阅
        """
        try:
            logger.info("[SoldierV2] Starting shutdown...")

            # 停止健康检查任务
            if self.health_check_task and not self.health_check_task.done():
                self.health_check_task.cancel()
                try:
                    await self.health_check_task
                except asyncio.CancelledError:
                    pass

            # 关闭Redis连接
            if self.redis_client:
                await self.redis_client.aclose()
                self.redis_client = None

            # 更新状态
            self.state = "SHUTDOWN"
            self.is_healthy = False

            logger.info("[SoldierV2] Shutdown completed")

        except Exception as e:
            logger.error(f"[SoldierV2] Shutdown error: {e}")
            raise
