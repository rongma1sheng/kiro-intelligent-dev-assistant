"""SHA256 Signature Manager

白皮书依据: 第四章 4.8.7 数据签名
"""

import hashlib
import json
from typing import Any, Dict

from loguru import logger


class SignatureManager:
    """SHA256签名管理器

    白皮书依据: 第四章 4.8.7 数据签名

    为所有存储的数据生成和验证SHA256签名,确保数据完整性。
    """

    @staticmethod
    def generate_signature(data: Dict[str, Any]) -> str:
        """生成SHA256签名

        白皮书依据: 第四章 4.8.7 数据签名 - Requirement 10.7

        Args:
            data: 要签名的数据字典

        Returns:
            SHA256签名字符串

        Raises:
            ValueError: 当data无效时
        """
        if not isinstance(data, dict):
            raise TypeError(f"data必须是字典类型，当前: {type(data)}")

        # 将数据转换为JSON字符串(排序键以确保一致性)
        json_str = json.dumps(data, sort_keys=True, ensure_ascii=False)

        # 计算SHA256哈希
        signature = hashlib.sha256(json_str.encode("utf-8")).hexdigest()

        logger.debug(f"生成签名: {signature[:16]}...")

        return signature

    @staticmethod
    def verify_signature(data: Dict[str, Any], expected_signature: str) -> bool:
        """验证SHA256签名

        白皮书依据: 第四章 4.8.7 数据签名 - Requirement 10.7

        Args:
            data: 要验证的数据字典
            expected_signature: 预期的签名

        Returns:
            签名是否匹配

        Raises:
            ValueError: 当参数无效时
        """
        if not isinstance(data, dict):
            raise TypeError(f"data必须是字典类型，当前: {type(data)}")

        if not expected_signature:
            raise ValueError("expected_signature不能为空")

        # 生成当前数据的签名
        actual_signature = SignatureManager.generate_signature(data)

        # 比较签名
        is_valid = actual_signature == expected_signature

        if not is_valid:
            logger.warning(
                f"签名验证失败: " f"expected={expected_signature[:16]}..., " f"actual={actual_signature[:16]}..."
            )
        else:
            logger.debug("签名验证成功")

        return is_valid
