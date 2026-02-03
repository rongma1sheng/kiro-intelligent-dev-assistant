"""Data Storage Manager

白皮书依据: 第四章 4.8 数据存储与检索
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Optional

from loguru import logger

from src.evolution.storage.signature_manager import SignatureManager


class DataStorageManager:
    """数据存储管理器

    白皮书依据: 第四章 4.8 数据存储与检索

    实现双存储策略(Redis + 文件系统)和缓存优先检索。

    Attributes:
        redis_client: Redis客户端(可选)
        storage_root: 文件系统存储根目录
        signature_manager: 签名管理器
    """

    def __init__(self, redis_client: Optional[Any] = None, storage_root: str = "data/storage"):
        """初始化数据存储管理器

        Args:
            redis_client: Redis客户端,None表示仅使用文件系统
            storage_root: 文件系统存储根目录
        """
        self.redis_client = redis_client
        self.storage_root = Path(storage_root)
        self.signature_manager = SignatureManager()

        # 创建存储目录
        self.storage_root.mkdir(parents=True, exist_ok=True)
        (self.storage_root / "arena_results").mkdir(exist_ok=True)
        (self.storage_root / "z2h_capsules").mkdir(exist_ok=True)
        (self.storage_root / "simulation_data").mkdir(exist_ok=True)

        logger.info(
            f"初始化DataStorageManager: "
            f"redis={'enabled' if redis_client else 'disabled'}, "
            f"storage_root={storage_root}"
        )

    def store_arena_result(self, result_id: str, data: Dict[str, Any], ttl_days: int = 90) -> bool:
        """存储Arena测试结果

        白皮书依据: 第四章 4.8.1 Arena结果存储 - Requirements 10.1, 10.2

        Args:
            result_id: 结果ID
            data: 结果数据
            ttl_days: Redis TTL(天),默认90天

        Returns:
            是否成功存储
        """
        try:
            # 生成签名
            signature = self.signature_manager.generate_signature(data)

            # 添加签名到数据
            data_with_sig = {**data, "signature": signature, "stored_at": datetime.now().isoformat()}

            # 存储到文件系统(JSON)
            file_path = self.storage_root / "arena_results" / f"{result_id}.json"
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data_with_sig, f, indent=2, ensure_ascii=False)

            logger.info(f"Arena结果已存储到文件系统: {file_path}")

            # 存储到Redis(如果可用)
            if self.redis_client:
                redis_key = f"arena_result:{result_id}"
                self.redis_client.setex(redis_key, timedelta(days=ttl_days), json.dumps(data_with_sig))
                logger.info(f"Arena结果已存储到Redis: {redis_key}, TTL={ttl_days}天")

            return True

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"存储Arena结果失败: {e}")
            return False

    def store_z2h_capsule(self, capsule_id: str, data: Dict[str, Any], ttl_days: int = 365) -> bool:
        """存储Z2H基因胶囊

        白皮书依据: 第四章 4.8.3 Z2H胶囊存储 - Requirements 10.3, 10.4

        Args:
            capsule_id: 胶囊ID
            data: 胶囊数据
            ttl_days: Redis TTL(天),默认365天

        Returns:
            是否成功存储
        """
        try:
            # 生成签名
            signature = self.signature_manager.generate_signature(data)

            # 添加签名到数据
            data_with_sig = {**data, "signature": signature, "stored_at": datetime.now().isoformat()}

            # 存储到文件系统(JSON)
            file_path = self.storage_root / "z2h_capsules" / f"{capsule_id}.json"
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data_with_sig, f, indent=2, ensure_ascii=False)

            logger.info(f"Z2H胶囊已存储到文件系统: {file_path}")

            # 存储到Redis(如果可用)
            if self.redis_client:
                redis_key = f"z2h_capsule:{capsule_id}"
                self.redis_client.setex(redis_key, timedelta(days=ttl_days), json.dumps(data_with_sig))
                logger.info(f"Z2H胶囊已存储到Redis: {redis_key}, TTL={ttl_days}天")

            return True

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"存储Z2H胶囊失败: {e}")
            return False

    def store_simulation_data(self, simulation_id: str, data: Dict[str, Any]) -> bool:
        """存储模拟数据

        白皮书依据: 第四章 4.8.5 模拟数据存储 - Requirement 10.5

        注: 简化版本使用JSON,生产环境应使用Parquet

        Args:
            simulation_id: 模拟ID
            data: 模拟数据

        Returns:
            是否成功存储
        """
        try:
            # 生成签名
            signature = self.signature_manager.generate_signature(data)

            # 添加签名到数据
            data_with_sig = {**data, "signature": signature, "stored_at": datetime.now().isoformat()}

            # 存储到文件系统(JSON - 简化版本)
            # 生产环境应使用Parquet格式
            file_path = self.storage_root / "simulation_data" / f"{simulation_id}.json"
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data_with_sig, f, indent=2, ensure_ascii=False)

            logger.info(f"模拟数据已存储到文件系统: {file_path}")

            return True

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"存储模拟数据失败: {e}")
            return False

    def retrieve_arena_result(self, result_id: str) -> Optional[Dict[str, Any]]:
        """检索Arena测试结果

        白皮书依据: 第四章 4.8.6 缓存优先检索 - Requirement 10.6

        Args:
            result_id: 结果ID

        Returns:
            结果数据,如果不存在则返回None
        """
        try:
            # 1. 先检查Redis缓存
            if self.redis_client:
                redis_key = f"arena_result:{result_id}"
                cached_data = self.redis_client.get(redis_key)

                if cached_data:
                    logger.debug(f"从Redis缓存获取Arena结果: {redis_key}")
                    data = json.loads(cached_data)

                    # 验证签名
                    if self._verify_data_integrity(data):  # pylint: disable=no-else-return
                        return data
                    else:
                        logger.warning(f"Redis缓存数据签名验证失败: {redis_key}")

            # 2. 回退到文件系统
            file_path = self.storage_root / "arena_results" / f"{result_id}.json"

            if file_path.exists():
                logger.debug(f"从文件系统获取Arena结果: {file_path}")

                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                # 验证签名
                if self._verify_data_integrity(data):  # pylint: disable=no-else-return
                    # 重新缓存到Redis
                    if self.redis_client:
                        redis_key = f"arena_result:{result_id}"
                        self.redis_client.setex(redis_key, timedelta(days=90), json.dumps(data))
                        logger.debug(f"Arena结果已重新缓存到Redis: {redis_key}")

                    return data
                else:
                    logger.error(f"文件系统数据签名验证失败: {file_path}")
                    return None

            logger.debug(f"Arena结果不存在: {result_id}")
            return None

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"检索Arena结果失败: {e}")
            return None

    def retrieve_z2h_capsule(self, capsule_id: str) -> Optional[Dict[str, Any]]:
        """检索Z2H基因胶囊

        白皮书依据: 第四章 4.8.6 缓存优先检索 - Requirement 10.6

        Args:
            capsule_id: 胶囊ID

        Returns:
            胶囊数据,如果不存在则返回None
        """
        try:
            # 1. 先检查Redis缓存
            if self.redis_client:
                redis_key = f"z2h_capsule:{capsule_id}"
                cached_data = self.redis_client.get(redis_key)

                if cached_data:
                    logger.debug(f"从Redis缓存获取Z2H胶囊: {redis_key}")
                    data = json.loads(cached_data)

                    # 验证签名
                    if self._verify_data_integrity(data):  # pylint: disable=no-else-return
                        return data
                    else:
                        logger.warning(f"Redis缓存数据签名验证失败: {redis_key}")

            # 2. 回退到文件系统
            file_path = self.storage_root / "z2h_capsules" / f"{capsule_id}.json"

            if file_path.exists():
                logger.debug(f"从文件系统获取Z2H胶囊: {file_path}")

                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                # 验证签名
                if self._verify_data_integrity(data):  # pylint: disable=no-else-return
                    # 重新缓存到Redis
                    if self.redis_client:
                        redis_key = f"z2h_capsule:{capsule_id}"
                        self.redis_client.setex(redis_key, timedelta(days=365), json.dumps(data))
                        logger.debug(f"Z2H胶囊已重新缓存到Redis: {redis_key}")

                    return data
                else:
                    logger.error(f"文件系统数据签名验证失败: {file_path}")
                    return None

            logger.debug(f"Z2H胶囊不存在: {capsule_id}")
            return None

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"检索Z2H胶囊失败: {e}")
            return None

    def _verify_data_integrity(self, data: Dict[str, Any]) -> bool:
        """验证数据完整性

        白皮书依据: 第四章 4.8.7 数据签名 - Requirement 10.7

        Args:
            data: 包含签名的数据

        Returns:
            数据是否完整
        """
        if "signature" not in data:
            logger.warning("数据缺少签名字段")
            return False

        # 提取签名
        expected_signature = data["signature"]

        # 移除签名和存储时间戳(这些不参与签名计算)
        data_without_sig = {k: v for k, v in data.items() if k not in ["signature", "stored_at"]}

        # 验证签名
        return self.signature_manager.verify_signature(data_without_sig, expected_signature)
