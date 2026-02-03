"""期货品种配置

白皮书依据: 第三章 3.3 衍生品管道

Author: MIA Team
Date: 2026-01-22
"""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional


class FutureType(Enum):
    """期货类型枚举"""

    STOCK_INDEX = "stock_index"  # 股指期货
    COMMODITY = "commodity"  # 商品期货
    TREASURY = "treasury"  # 国债期货


@dataclass
class FutureProductConfig:
    """期货品种配置

    白皮书依据: 第三章 3.3 衍生品管道

    Attributes:
        code: 品种代码（如 'IF', 'CU', 'T'）
        name: 品种名称
        future_type: 期货类型
        contract_multiplier: 合约乘数
        tick_size: 最小变动价位
        expiry_day_threshold: 到期日阈值（天）
        volume_threshold_ratio: 成交量相近阈值
    """

    code: str
    name: str
    future_type: FutureType
    contract_multiplier: int
    tick_size: float
    expiry_day_threshold: int = 7
    volume_threshold_ratio: float = 0.2


# 预定义的期货品种配置
FUTURE_PRODUCTS: Dict[str, FutureProductConfig] = {
    # 股指期货
    "IF": FutureProductConfig(
        code="IF",
        name="沪深300股指期货",
        future_type=FutureType.STOCK_INDEX,
        contract_multiplier=300,
        tick_size=0.2,
        expiry_day_threshold=7,
        volume_threshold_ratio=0.2,
    ),
    "IC": FutureProductConfig(
        code="IC",
        name="中证500股指期货",
        future_type=FutureType.STOCK_INDEX,
        contract_multiplier=200,
        tick_size=0.2,
        expiry_day_threshold=7,
        volume_threshold_ratio=0.2,
    ),
    "IH": FutureProductConfig(
        code="IH",
        name="上证50股指期货",
        future_type=FutureType.STOCK_INDEX,
        contract_multiplier=300,
        tick_size=0.2,
        expiry_day_threshold=7,
        volume_threshold_ratio=0.2,
    ),
    "IM": FutureProductConfig(
        code="IM",
        name="中证1000股指期货",
        future_type=FutureType.STOCK_INDEX,
        contract_multiplier=200,
        tick_size=0.2,
        expiry_day_threshold=7,
        volume_threshold_ratio=0.2,
    ),
    # 商品期货
    "CU": FutureProductConfig(
        code="CU",
        name="沪铜期货",
        future_type=FutureType.COMMODITY,
        contract_multiplier=5,
        tick_size=10.0,
        expiry_day_threshold=7,
        volume_threshold_ratio=0.2,
    ),
    "AL": FutureProductConfig(
        code="AL",
        name="沪铝期货",
        future_type=FutureType.COMMODITY,
        contract_multiplier=5,
        tick_size=5.0,
        expiry_day_threshold=7,
        volume_threshold_ratio=0.2,
    ),
    "RB": FutureProductConfig(
        code="RB",
        name="螺纹钢期货",
        future_type=FutureType.COMMODITY,
        contract_multiplier=10,
        tick_size=1.0,
        expiry_day_threshold=7,
        volume_threshold_ratio=0.2,
    ),
    # 国债期货
    "T": FutureProductConfig(
        code="T",
        name="10年期国债期货",
        future_type=FutureType.TREASURY,
        contract_multiplier=10000,
        tick_size=0.005,
        expiry_day_threshold=7,
        volume_threshold_ratio=0.2,
    ),
    "TF": FutureProductConfig(
        code="TF",
        name="5年期国债期货",
        future_type=FutureType.TREASURY,
        contract_multiplier=10000,
        tick_size=0.005,
        expiry_day_threshold=7,
        volume_threshold_ratio=0.2,
    ),
    "TS": FutureProductConfig(
        code="TS",
        name="2年期国债期货",
        future_type=FutureType.TREASURY,
        contract_multiplier=20000,
        tick_size=0.005,
        expiry_day_threshold=7,
        volume_threshold_ratio=0.2,
    ),
}


def get_product_config(product_code: str) -> Optional[FutureProductConfig]:
    """获取期货品种配置

    Args:
        product_code: 品种代码（如 'IF', 'CU'）

    Returns:
        品种配置，如果不存在返回None
    """
    return FUTURE_PRODUCTS.get(product_code.upper())


def extract_product_code(contract_code: str) -> str:
    """从合约代码提取品种代码

    Args:
        contract_code: 合约代码（如 'IF2401', 'CU2403'）

    Returns:
        品种代码（如 'IF', 'CU'）
    """
    # 提取字母部分作为品种代码
    product_code = "".join(c for c in contract_code if c.isalpha())
    return product_code.upper()
