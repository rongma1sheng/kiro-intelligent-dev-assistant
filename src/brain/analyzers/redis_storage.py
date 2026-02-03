"""Redis存储管理器

白皮书依据: 第五章 5.5 Redis数据结构
职责: 分析结果缓存、TTL配置、批量查询
"""

import json
from typing import Any, Dict, List, Optional

from loguru import logger

try:
    import redis.asyncio as redis

    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("redis.asyncio not available, using mock implementation")


class RedisStorageManager:
    """Redis存储管理器

    白皮书依据: 第五章 5.5 Redis数据结构

    核心功能:
    - 分析结果缓存
    - TTL配置管理
    - 批量查询接口
    - 连接池管理

    性能要求:
    - 单次写入延迟: <10ms
    - 单次读取延迟: <5ms
    - 批量查询延迟: <50ms
    - 连接池大小: 50个连接
    """

    def __init__(  # pylint: disable=too-many-positional-arguments
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        password: Optional[str] = None,
        max_connections: int = 50,
    ):
        """初始化Redis存储管理器

        Args:
            host: Redis服务器地址
            port: Redis端口
            db: 数据库编号
            password: 密码（可选）
            max_connections: 最大连接数
        """
        self.host = host
        self.port = port
        self.db = db
        self.password = password
        self.max_connections = max_connections

        self.redis_client: Optional[redis.Redis] = None
        self._initialized = False

        # TTL配置（秒）- 白皮书依据: 第五章 5.5.1
        self.ttl_config = {
            "essence": None,  # 永久
            "risk": None,  # 永久
            "overfitting": None,  # 永久
            "feature": None,  # 永久
            "macro": 3600,  # 1小时
            "microstructure": 3600,  # 1小时
            "sector": 2592000,  # 30天
            "smart_money": 3600,  # 1小时
            "recommendation": 3600,  # 1小时
            "trading_cost": None,  # 永久
            "decay": None,  # 永久
            "stop_loss": None,  # 永久
            "slippage": None,  # 永久
            "nonstationarity": None,  # 永久
            "signal_noise": None,  # 永久
            "capacity": None,  # 永久
            "stress_test": None,  # 永久
            "trade_review": 7776000,  # 90天
            "sentiment": 3600,  # 1小时
            "retail_sentiment": 3600,  # 1小时
            "correlation": None,  # 永久
            "position_sizing": None,  # 永久
            "portfolio_optimization": None,  # 永久
            "regime_adaptation": None,  # 永久
            "factor_exposure": None,  # 永久
            "transaction_cost_deep": None,  # 永久
            "comprehensive": 3600,  # 综合分析1小时
        }

        logger.info(
            f"初始化RedisStorageManager: " f"host={host}, port={port}, db={db}, " f"max_connections={max_connections}"
        )

    async def initialize(self) -> bool:
        """初始化Redis连接

        Returns:
            bool: 初始化是否成功
        """
        if self._initialized:
            logger.warning("RedisStorageManager已经初始化")
            return True

        if not REDIS_AVAILABLE:
            logger.warning("Redis不可用，使用Mock模式")
            self._initialized = True
            return True

        try:
            # 创建连接池
            pool = redis.ConnectionPool(
                host=self.host,
                port=self.port,
                db=self.db,
                password=self.password,
                max_connections=self.max_connections,
                decode_responses=True,
            )

            # 创建Redis客户端
            self.redis_client = redis.Redis(connection_pool=pool)

            # 测试连接
            await self.redis_client.ping()

            self._initialized = True
            logger.info("Redis连接初始化成功")
            return True

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"Redis连接初始化失败: {e}")
            self._initialized = False
            return False

    async def close(self):
        """关闭Redis连接"""
        if self.redis_client:
            await self.redis_client.close()
            logger.info("Redis连接已关闭")

    async def store_analysis_result(
        self, dimension: str, strategy_id: str, result: Dict[str, Any], custom_ttl: Optional[int] = None
    ) -> bool:
        """存储分析结果

        白皮书依据: 第五章 5.5.1 分析结果存储

        Args:
            dimension: 分析维度（如 'essence', 'risk'）
            strategy_id: 策略ID
            result: 分析结果字典
            custom_ttl: 自定义TTL（秒），None使用默认配置

        Returns:
            bool: 存储是否成功
        """
        if not self._initialized or not self.redis_client:
            logger.debug("Redis未初始化，跳过存储")
            return False

        try:
            # 构建Redis键
            key = f"mia:analysis:{dimension}:{strategy_id}"

            # 序列化结果
            value = json.dumps(result, ensure_ascii=False)

            # 确定TTL
            ttl = custom_ttl if custom_ttl is not None else self.ttl_config.get(dimension)

            # 存储到Redis
            if ttl is not None:
                await self.redis_client.setex(key, ttl, value)
            else:
                await self.redis_client.set(key, value)

            logger.debug(f"分析结果已存储: {key}, TTL={ttl}")
            return True

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"存储分析结果失败: {e}")
            return False

    async def get_analysis_result(self, dimension: str, strategy_id: str) -> Optional[Dict[str, Any]]:
        """获取分析结果

        Args:
            dimension: 分析维度
            strategy_id: 策略ID

        Returns:
            Optional[Dict[str, Any]]: 分析结果，不存在返回None
        """
        if not self._initialized or not self.redis_client:
            logger.debug("Redis未初始化，返回None")
            return None

        try:
            # 构建Redis键
            key = f"mia:analysis:{dimension}:{strategy_id}"

            # 从Redis读取
            value = await self.redis_client.get(key)

            if value is None:
                logger.debug(f"分析结果不存在: {key}")
                return None

            # 反序列化
            result = json.loads(value)
            logger.debug(f"分析结果已读取: {key}")
            return result

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"读取分析结果失败: {e}")
            return None

    async def batch_get_analysis_results(
        self, dimension: str, strategy_ids: List[str]
    ) -> Dict[str, Optional[Dict[str, Any]]]:
        """批量获取分析结果

        白皮书依据: 第五章 5.5.1 分析结果存储

        Args:
            dimension: 分析维度
            strategy_ids: 策略ID列表

        Returns:
            Dict[str, Optional[Dict[str, Any]]]: 策略ID -> 分析结果映射
        """
        if not self._initialized or not self.redis_client:
            logger.debug("Redis未初始化，返回空字典")
            return {sid: None for sid in strategy_ids}

        try:
            # 构建所有键
            keys = [f"mia:analysis:{dimension}:{sid}" for sid in strategy_ids]

            # 批量读取
            values = await self.redis_client.mget(keys)

            # 构建结果字典
            results = {}
            for strategy_id, value in zip(strategy_ids, values):
                if value is not None:
                    try:
                        results[strategy_id] = json.loads(value)
                    except json.JSONDecodeError:
                        results[strategy_id] = None
                else:
                    results[strategy_id] = None

            logger.debug(f"批量读取完成: {len(strategy_ids)}个策略")
            return results

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"批量读取分析结果失败: {e}")
            return {sid: None for sid in strategy_ids}

    async def delete_analysis_result(self, dimension: str, strategy_id: str) -> bool:
        """删除分析结果

        Args:
            dimension: 分析维度
            strategy_id: 策略ID

        Returns:
            bool: 删除是否成功
        """
        if not self._initialized or not self.redis_client:
            logger.debug("Redis未初始化，跳过删除")
            return False

        try:
            key = f"mia:analysis:{dimension}:{strategy_id}"
            await self.redis_client.delete(key)
            logger.debug(f"分析结果已删除: {key}")
            return True

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"删除分析结果失败: {e}")
            return False

    async def store_comprehensive_analysis(self, strategy_id: str, report: Dict[str, Any]) -> bool:
        """存储综合分析报告

        白皮书依据: 第五章 5.5.1 分析结果存储

        Args:
            strategy_id: 策略ID
            report: 综合分析报告

        Returns:
            bool: 存储是否成功
        """
        return await self.store_analysis_result(dimension="comprehensive", strategy_id=strategy_id, result=report)

    async def get_comprehensive_analysis(self, strategy_id: str) -> Optional[Dict[str, Any]]:
        """获取综合分析报告

        Args:
            strategy_id: 策略ID

        Returns:
            Optional[Dict[str, Any]]: 综合分析报告
        """
        return await self.get_analysis_result(dimension="comprehensive", strategy_id=strategy_id)

    async def store_stock_recommendation(self, symbol: str, recommendation: Dict[str, Any]) -> bool:
        """存储个股建议

        白皮书依据: 第五章 5.5.1 个股结论性建议

        Args:
            symbol: 股票代码
            recommendation: 个股建议

        Returns:
            bool: 存储是否成功
        """
        if not self._initialized or not self.redis_client:
            logger.debug("Redis未初始化，跳过存储")
            return False

        try:
            # 存储当前建议
            key = f"mia:recommendation:{symbol}"
            value = json.dumps(recommendation, ensure_ascii=False)
            await self.redis_client.setex(key, 3600, value)  # 1小时TTL

            # 添加到历史记录
            history_key = f"mia:recommendation:history:{symbol}"
            await self.redis_client.lpush(history_key, value)
            await self.redis_client.ltrim(history_key, 0, 99)  # 保留最近100条
            await self.redis_client.expire(history_key, 7776000)  # 90天TTL

            logger.debug(f"个股建议已存储: {symbol}")
            return True

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"存储个股建议失败: {e}")
            return False

    async def get_stock_recommendation(self, symbol: str) -> Optional[Dict[str, Any]]:
        """获取个股建议

        Args:
            symbol: 股票代码

        Returns:
            Optional[Dict[str, Any]]: 个股建议
        """
        if not self._initialized or not self.redis_client:
            logger.debug("Redis未初始化，返回None")
            return None

        try:
            key = f"mia:recommendation:{symbol}"
            value = await self.redis_client.get(key)

            if value is None:
                return None

            return json.loads(value)

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"读取个股建议失败: {e}")
            return None

    async def get_stock_recommendation_history(self, symbol: str, limit: int = 10) -> List[Dict[str, Any]]:
        """获取个股建议历史

        Args:
            symbol: 股票代码
            limit: 返回数量限制

        Returns:
            List[Dict[str, Any]]: 历史建议列表
        """
        if not self._initialized or not self.redis_client:
            logger.debug("Redis未初始化，返回空列表")
            return []

        try:
            key = f"mia:recommendation:history:{symbol}"
            values = await self.redis_client.lrange(key, 0, limit - 1)

            history = []
            for value in values:
                try:
                    history.append(json.loads(value))
                except json.JSONDecodeError:
                    continue

            return history

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"读取个股建议历史失败: {e}")
            return []

    async def store_smart_money_analysis(self, symbol: str, analysis: Dict[str, Any]) -> bool:
        """存储主力资金分析

        白皮书依据: 第五章 5.5.1 主力资金深度分析

        Args:
            symbol: 股票代码
            analysis: 主力资金分析

        Returns:
            bool: 存储是否成功
        """
        if not self._initialized or not self.redis_client:
            logger.debug("Redis未初始化，跳过存储")
            return False

        try:
            key = f"mia:smart_money:deep_analysis:{symbol}"
            value = json.dumps(analysis, ensure_ascii=False)
            await self.redis_client.setex(key, 3600, value)  # 1小时TTL

            logger.debug(f"主力资金分析已存储: {symbol}")
            return True

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"存储主力资金分析失败: {e}")
            return False

    async def get_smart_money_analysis(self, symbol: str) -> Optional[Dict[str, Any]]:
        """获取主力资金分析

        Args:
            symbol: 股票代码

        Returns:
            Optional[Dict[str, Any]]: 主力资金分析
        """
        if not self._initialized or not self.redis_client:
            logger.debug("Redis未初始化，返回None")
            return None

        try:
            key = f"mia:smart_money:deep_analysis:{symbol}"
            value = await self.redis_client.get(key)

            if value is None:
                return None

            return json.loads(value)

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"读取主力资金分析失败: {e}")
            return None

    async def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息

        Returns:
            Dict[str, Any]: 缓存统计信息
        """
        if not self._initialized or not self.redis_client:
            return {"initialized": False, "total_keys": 0, "memory_used": 0}

        try:
            info = await self.redis_client.info("stats")
            keyspace = await self.redis_client.info("keyspace")

            total_keys = 0
            if f"db{self.db}" in keyspace:
                db_info = keyspace[f"db{self.db}"]
                total_keys = db_info.get("keys", 0)

            return {
                "initialized": True,
                "total_keys": total_keys,
                "total_commands_processed": info.get("total_commands_processed", 0),
                "instantaneous_ops_per_sec": info.get("instantaneous_ops_per_sec", 0),
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0),
                "hit_rate": self._calculate_hit_rate(info.get("keyspace_hits", 0), info.get("keyspace_misses", 0)),
            }

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"获取缓存统计失败: {e}")
            return {"initialized": True, "error": str(e)}

    def _calculate_hit_rate(self, hits: int, misses: int) -> float:
        """计算缓存命中率

        Args:
            hits: 命中次数
            misses: 未命中次数

        Returns:
            float: 命中率 0-1
        """
        total = hits + misses
        if total == 0:
            return 0.0
        return hits / total


# 全局单例
_redis_storage_manager: Optional[RedisStorageManager] = None


async def get_redis_storage_manager() -> RedisStorageManager:
    """获取Redis存储管理器单例

    Returns:
        RedisStorageManager: Redis存储管理器实例
    """
    global _redis_storage_manager  # pylint: disable=w0603

    if _redis_storage_manager is None:
        _redis_storage_manager = RedisStorageManager()
        await _redis_storage_manager.initialize()

    return _redis_storage_manager
