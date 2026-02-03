"""资金档位定义

白皮书依据: 第四章 4.3.5 资金分层
"""


class Tier:
    """资金档位枚举

    白皮书依据: 第四章 4.3.5 资金分层

    六档资金分层：
    - Tier1 (1千-1万): 刺客模式，高频小单
    - Tier2 (1万-10万): 狼群模式，多策略并行
    - Tier3 (10万-50万): 过渡期，策略优化
    - Tier4 (50万-100万): 稳健期，风控加强
    - Tier5 (100万-1000万): 利维坦模式，大资金运作
    - Tier6 (1000万+): 机构级，多市场配置
    """

    TIER1_MICRO = "tier1_micro"  # 1千-1万
    TIER2_SMALL = "tier2_small"  # 1万-10万
    TIER3_MEDIUM = "tier3_medium"  # 10万-50万
    TIER4_LARGE = "tier4_large"  # 50万-100万
    TIER5_MILLION = "tier5_million"  # 100万-1000万
    TIER6_TEN_MILLION = "tier6_ten_million"  # 1000万+

    @classmethod
    def from_aum(cls, aum: float) -> str:
        """根据AUM确定档位

        Args:
            aum: 当前资金规模

        Returns:
            档位字符串

        Raises:
            ValueError: 当AUM为负数时
        """
        if aum < 0:
            raise ValueError(f"AUM不能为负数: {aum}")

        if aum < 10000:  # pylint: disable=no-else-return
            return cls.TIER1_MICRO
        elif aum < 100000:
            return cls.TIER2_SMALL
        elif aum < 500000:
            return cls.TIER3_MEDIUM
        elif aum < 1000000:
            return cls.TIER4_LARGE
        elif aum < 10000000:
            return cls.TIER5_MILLION
        else:
            return cls.TIER6_TEN_MILLION

    @classmethod
    def get_tier_range(cls, tier: str) -> tuple[float, float]:
        """获取档位的资金范围

        Args:
            tier: 档位字符串

        Returns:
            (最小值, 最大值) 元组

        Raises:
            ValueError: 当档位无效时
        """
        ranges = {
            cls.TIER1_MICRO: (1000, 10000),
            cls.TIER2_SMALL: (10000, 100000),
            cls.TIER3_MEDIUM: (100000, 500000),
            cls.TIER4_LARGE: (500000, 1000000),
            cls.TIER5_MILLION: (1000000, 10000000),
            cls.TIER6_TEN_MILLION: (10000000, float("inf")),
        }

        if tier not in ranges:
            raise ValueError(f"无效的档位: {tier}")

        return ranges[tier]

    @classmethod
    def get_all_tiers(cls) -> list[str]:
        """获取所有档位列表

        Returns:
            档位列表
        """
        return [
            cls.TIER1_MICRO,
            cls.TIER2_SMALL,
            cls.TIER3_MEDIUM,
            cls.TIER4_LARGE,
            cls.TIER5_MILLION,
            cls.TIER6_TEN_MILLION,
        ]
