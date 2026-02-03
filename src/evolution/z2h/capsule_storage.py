"""Capsule Storage for Z2H Gene Capsules

白皮书依据: 第四章 4.3.2 Z2H基因胶囊认证系统
"""

import json
from datetime import timedelta
from pathlib import Path
from typing import List, Optional

from loguru import logger

try:
    import redis

    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("Redis未安装，将仅使用文件系统存储")

from src.evolution.z2h.data_models import Z2HGeneCapsule
from src.evolution.z2h.signature_manager import SignatureManager


class CapsuleStorage:
    """胶囊存储系统

    白皮书依据: 第四章 4.3.2 Z2H基因胶囊认证系统

    实现双重存储策略：
    1. Redis存储（1年TTL）- 快速访问
    2. 文件系统存储（JSON）- 持久化备份
    """

    def __init__(  # pylint: disable=too-many-positional-arguments
        self,
        redis_host: str = "localhost",
        redis_port: int = 6379,
        redis_db: int = 0,
        storage_dir: str = "data/z2h_capsules",
        redis_ttl_days: int = 365,
    ):
        """初始化胶囊存储系统

        Args:
            redis_host: Redis主机地址
            redis_port: Redis端口
            redis_db: Redis数据库编号
            storage_dir: 文件系统存储目录
            redis_ttl_days: Redis存储过期天数（默认365天）
        """
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        self.redis_ttl = timedelta(days=redis_ttl_days)
        self.signature_manager = SignatureManager()

        # 初始化Redis连接
        self.redis_client = None
        if REDIS_AVAILABLE:
            try:
                self.redis_client = redis.Redis(
                    host=redis_host,
                    port=redis_port,
                    db=redis_db,
                    decode_responses=True,
                    socket_connect_timeout=0.5,  # 减少超时时间到0.5秒
                    socket_timeout=0.5,
                )
                # 测试连接
                self.redis_client.ping()
                logger.info(f"Redis连接成功: {redis_host}:{redis_port}/{redis_db}")
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.debug(f"Redis连接失败: {e}，将仅使用文件系统存储")
                self.redis_client = None

        logger.info(f"CapsuleStorage初始化完成 - " f"存储目录: {self.storage_dir}, " f"Redis TTL: {redis_ttl_days}天")

    def store(self, capsule: Z2HGeneCapsule) -> bool:
        """存储基因胶囊（双重存储）

        白皮书依据: 第四章 4.3.2 双重存储策略

        Args:
            capsule: Z2H基因胶囊

        Returns:
            是否存储成功
        """
        if not isinstance(capsule, Z2HGeneCapsule):
            logger.error(f"capsule类型错误: {type(capsule)}")
            return False

        # 验证签名
        if not capsule.signature:
            logger.error(f"基因胶囊缺少签名: {capsule.strategy_id}")
            return False

        if not self.signature_manager.verify_signature(capsule):
            logger.error(f"基因胶囊签名验证失败: {capsule.strategy_id}")
            return False

        success = True

        # 1. 存储到Redis
        if self.redis_client:
            try:
                redis_key = self._get_redis_key(capsule.strategy_id)
                capsule_json = json.dumps(capsule.to_dict(), ensure_ascii=False)

                self.redis_client.setex(redis_key, self.redis_ttl, capsule_json)

                logger.info(f"基因胶囊已存储到Redis: {capsule.strategy_id}, " f"TTL: {self.redis_ttl.days}天")
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.error(f"Redis存储失败: {capsule.strategy_id}, 错误: {e}")
                success = False

        # 2. 存储到文件系统
        try:
            file_path = self._get_file_path(capsule.strategy_id)

            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(capsule.to_dict(), f, ensure_ascii=False, indent=2)

            logger.info(f"基因胶囊已存储到文件系统: {file_path}")
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"文件系统存储失败: {capsule.strategy_id}, 错误: {e}")
            success = False

        return success

    def retrieve(self, strategy_id: str) -> Optional[Z2HGeneCapsule]:
        """检索基因胶囊（缓存优先策略）

        白皮书依据: 第四章 4.3.2 缓存优先检索

        检索顺序：
        1. 先查Redis缓存
        2. 缓存未命中则查文件系统
        3. 从文件系统加载后回填Redis

        Args:
            strategy_id: 策略ID

        Returns:
            Z2H基因胶囊，如果不存在则返回None
        """
        # 1. 尝试从Redis加载
        if self.redis_client:
            try:
                redis_key = self._get_redis_key(strategy_id)
                capsule_json = self.redis_client.get(redis_key)

                if capsule_json:
                    capsule_dict = json.loads(capsule_json)

                    # 验证签名
                    if not self.signature_manager.verify_dict_signature(capsule_dict):
                        logger.error(f"Redis中的基因胶囊签名验证失败: {strategy_id}")
                        return None

                    capsule = Z2HGeneCapsule.from_dict(capsule_dict)
                    logger.info(f"从Redis加载基因胶囊: {strategy_id}")
                    return capsule
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.warning(f"从Redis加载失败: {strategy_id}, 错误: {e}")

        # 2. 从文件系统加载
        try:
            file_path = self._get_file_path(strategy_id)

            if not file_path.exists():
                logger.warning(f"基因胶囊不存在: {strategy_id}")
                return None

            with open(file_path, "r", encoding="utf-8") as f:
                capsule_dict = json.load(f)

            # 验证签名
            if not self.signature_manager.verify_dict_signature(capsule_dict):
                logger.error(f"文件系统中的基因胶囊签名验证失败: {strategy_id}")
                return None

            capsule = Z2HGeneCapsule.from_dict(capsule_dict)
            logger.info(f"从文件系统加载基因胶囊: {strategy_id}")

            # 3. 回填Redis缓存
            if self.redis_client:
                try:
                    redis_key = self._get_redis_key(strategy_id)
                    capsule_json = json.dumps(capsule_dict, ensure_ascii=False)
                    self.redis_client.setex(redis_key, self.redis_ttl, capsule_json)
                    logger.debug(f"基因胶囊已回填Redis缓存: {strategy_id}")
                except Exception as e:  # pylint: disable=broad-exception-caught
                    logger.warning(f"Redis缓存回填失败: {strategy_id}, 错误: {e}")

            return capsule

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"从文件系统加载失败: {strategy_id}, 错误: {e}")
            return None

    def delete(self, strategy_id: str) -> bool:
        """删除基因胶囊（双重删除）

        Args:
            strategy_id: 策略ID

        Returns:
            是否删除成功
        """
        success = True

        # 1. 从Redis删除
        if self.redis_client:
            try:
                redis_key = self._get_redis_key(strategy_id)
                self.redis_client.delete(redis_key)
                logger.info(f"从Redis删除基因胶囊: {strategy_id}")
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.error(f"从Redis删除失败: {strategy_id}, 错误: {e}")
                success = False

        # 2. 从文件系统删除
        try:
            file_path = self._get_file_path(strategy_id)

            if file_path.exists():
                file_path.unlink()
                logger.info(f"从文件系统删除基因胶囊: {strategy_id}")
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"从文件系统删除失败: {strategy_id}, 错误: {e}")
            success = False

        return success

    def list_all(self) -> List[str]:
        """列出所有基因胶囊的策略ID

        Returns:
            策略ID列表
        """
        strategy_ids = []

        try:
            for file_path in self.storage_dir.glob("*.json"):
                strategy_id = file_path.stem
                strategy_ids.append(strategy_id)

            logger.info(f"找到{len(strategy_ids)}个基因胶囊")
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"列出基因胶囊失败: {e}")

        return sorted(strategy_ids)

    def exists(self, strategy_id: str) -> bool:
        """检查基因胶囊是否存在

        Args:
            strategy_id: 策略ID

        Returns:
            是否存在
        """
        # 先查Redis
        if self.redis_client:
            try:
                redis_key = self._get_redis_key(strategy_id)
                if self.redis_client.exists(redis_key):
                    return True
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.warning(f"Redis查询失败: {strategy_id}, 错误: {e}")

        # 再查文件系统
        file_path = self._get_file_path(strategy_id)
        return file_path.exists()

    def _get_redis_key(self, strategy_id: str) -> str:
        """获取Redis键名

        Args:
            strategy_id: 策略ID

        Returns:
            Redis键名
        """
        return f"z2h:capsule:{strategy_id}"

    def _get_file_path(self, strategy_id: str) -> Path:
        """获取文件路径

        Args:
            strategy_id: 策略ID

        Returns:
            文件路径
        """
        return self.storage_dir / f"{strategy_id}.json"

    def get_statistics(self) -> dict:
        """获取存储统计信息

        Returns:
            统计信息字典
        """
        stats = {
            "total_capsules": len(self.list_all()),
            "storage_dir": str(self.storage_dir),
            "redis_available": self.redis_client is not None,
        }

        if self.redis_client:
            try:
                redis_keys = self.redis_client.keys("z2h:capsule:*")
                stats["redis_cached_count"] = len(redis_keys)
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.warning(f"获取Redis统计失败: {e}")
                stats["redis_cached_count"] = 0

        return stats
