"""Signature Manager for Z2H Gene Capsules

白皮书依据: 第四章 4.3.2 Z2H基因胶囊认证系统
"""

import hashlib
import json
from typing import Any, Dict

from loguru import logger

from src.evolution.z2h.data_models import Z2HGeneCapsule


class SignatureManager:
    """签名管理器

    白皮书依据: 第四章 4.3.2 Z2H基因胶囊认证系统

    使用SHA256算法对基因胶囊进行签名和验证，确保数据完整性和防篡改
    """

    def __init__(self):
        """初始化签名管理器"""
        self.hash_algorithm = "sha256"
        logger.info(f"SignatureManager初始化完成，使用{self.hash_algorithm}算法")

    def generate_signature(self, capsule: Z2HGeneCapsule) -> str:
        """生成基因胶囊的SHA256签名

        白皮书依据: 第四章 4.3.2 SHA256签名

        Args:
            capsule: Z2H基因胶囊

        Returns:
            SHA256签名字符串

        Raises:
            ValueError: 当capsule无效时
        """
        if not isinstance(capsule, Z2HGeneCapsule):
            raise ValueError(f"capsule必须是Z2HGeneCapsule类型，当前: {type(capsule)}")

        # 构建签名数据（排除signature字段本身）
        signature_data = {
            "strategy_id": capsule.strategy_id,
            "strategy_name": capsule.strategy_name,
            "source_factors": sorted(capsule.source_factors),  # 排序确保一致性
            "arena_score": capsule.arena_score,
            "simulation_metrics": self._sort_dict(capsule.simulation_metrics),
            "certification_date": capsule.certification_date.isoformat(),
            "certification_level": capsule.certification_level.value,
            "metadata": self._sort_dict(capsule.metadata),
        }

        # 转换为JSON字符串（确保键排序）
        json_str = json.dumps(signature_data, sort_keys=True, ensure_ascii=False)

        # 计算SHA256哈希
        signature = hashlib.sha256(json_str.encode("utf-8")).hexdigest()

        logger.debug(f"生成签名: {capsule.strategy_id} -> {signature[:16]}...")

        return signature

    def verify_signature(self, capsule: Z2HGeneCapsule) -> bool:
        """验证基因胶囊的签名

        白皮书依据: 第四章 4.3.2 签名验证

        Args:
            capsule: Z2H基因胶囊

        Returns:
            签名是否有效
        """
        if not isinstance(capsule, Z2HGeneCapsule):
            logger.error(f"capsule类型错误: {type(capsule)}")
            return False

        if not capsule.signature:
            logger.error(f"基因胶囊缺少签名: {capsule.strategy_id}")
            return False

        # 重新计算签名
        expected_signature = self.generate_signature(capsule)

        # 比较签名
        is_valid = expected_signature == capsule.signature

        if is_valid:
            logger.info(f"签名验证通过: {capsule.strategy_id}")
        else:
            logger.error(
                f"签名验证失败: {capsule.strategy_id}, "
                f"期望: {expected_signature[:16]}..., "
                f"实际: {capsule.signature[:16]}..."
            )

        return is_valid

    def sign_capsule(self, capsule: Z2HGeneCapsule) -> Z2HGeneCapsule:
        """为基因胶囊签名（修改capsule对象）

        Args:
            capsule: Z2H基因胶囊

        Returns:
            已签名的基因胶囊（同一对象）
        """
        signature = self.generate_signature(capsule)
        capsule.signature = signature

        logger.info(f"基因胶囊已签名: {capsule.strategy_id}")

        return capsule

    def detect_tampering(self, capsule: Z2HGeneCapsule) -> bool:
        """检测基因胶囊是否被篡改

        Args:
            capsule: Z2H基因胶囊

        Returns:
            是否被篡改（True表示被篡改）
        """
        is_valid = self.verify_signature(capsule)

        if not is_valid:
            logger.warning(f"检测到数据篡改: {capsule.strategy_id}")
            return True

        return False

    def _sort_dict(self, d: Dict[str, Any]) -> Dict[str, Any]:
        """递归排序字典（确保签名一致性）

        Args:
            d: 输入字典

        Returns:
            排序后的字典
        """
        if not isinstance(d, dict):
            return d

        sorted_dict = {}
        for key in sorted(d.keys()):
            value = d[key]
            if isinstance(value, dict):
                sorted_dict[key] = self._sort_dict(value)
            elif isinstance(value, list):
                # 列表中的字典也需要排序
                sorted_dict[key] = [self._sort_dict(item) if isinstance(item, dict) else item for item in value]
            else:
                sorted_dict[key] = value

        return sorted_dict

    def generate_signature_from_dict(self, data: Dict[str, Any]) -> str:
        """从字典数据生成签名（用于验证存储的数据）

        Args:
            data: 字典数据

        Returns:
            SHA256签名
        """
        # 排除signature字段
        signature_data = {k: v for k, v in data.items() if k != "signature"}

        # 排序并转换为JSON
        json_str = json.dumps(signature_data, sort_keys=True, ensure_ascii=False)

        # 计算SHA256
        signature = hashlib.sha256(json_str.encode("utf-8")).hexdigest()

        return signature

    def verify_dict_signature(self, data: Dict[str, Any]) -> bool:
        """验证字典数据的签名

        Args:
            data: 包含signature字段的字典数据

        Returns:
            签名是否有效
        """
        if "signature" not in data:
            logger.error("数据缺少signature字段")
            return False

        stored_signature = data["signature"]
        expected_signature = self.generate_signature_from_dict(data)

        is_valid = expected_signature == stored_signature

        if not is_valid:
            logger.error(
                f"字典签名验证失败, " f"期望: {expected_signature[:16]}..., " f"实际: {stored_signature[:16]}..."
            )

        return is_valid
