"""策略风险管理器

白皮书依据: 第四章 4.2 斯巴达竞技场
"""

from typing import Dict, List, Optional

from loguru import logger

from src.strategies.data_models import Position, StrategyConfig


class StrategyRiskManager:
    """策略风险管理器

    白皮书依据: 第四章 4.2 斯巴达竞技场

    每个策略有自己的风险管理器，使用Arena进化出的参数
    """

    def __init__(self, config: StrategyConfig):
        """初始化风险管理器

        Args:
            config: 策略配置（Arena进化出的参数）
        """
        self.config = config
        self.max_position = config.max_position
        self.max_single_stock = config.max_single_stock
        self.max_industry = config.max_industry
        self.stop_loss_pct = config.stop_loss_pct
        self.take_profit_pct = config.take_profit_pct
        self.liquidity_threshold = config.liquidity_threshold
        self.max_order_pct_of_volume = config.max_order_pct_of_volume

        # 出货监测协调机制
        self.exit_mode: Dict[str, Dict[str, any]] = (
            {}
        )  # {symbol: {'urgency': str, 'reduce_ratio': float, 'timestamp': str}}

        logger.info(
            f"StrategyRiskManager初始化完成 - "
            f"最大仓位: {self.max_position*100:.1f}%, "
            f"单股上限: {self.max_single_stock*100:.1f}%, "
            f"止损: {self.stop_loss_pct*100:.1f}%"
        )

    async def filter_positions(self, positions: List[Position]) -> List[Position]:
        """过滤仓位，应用风控规则

        白皮书依据: Requirement 6.1

        检查：
        1. 总仓位不超过max_position
        2. 单股仓位不超过max_single_stock
        3. 单行业仓位不超过max_industry
        4. 流动性满足要求

        Args:
            positions: 原始仓位列表

        Returns:
            过滤后的仓位列表
        """
        if not positions:
            return []

        logger.debug(f"开始过滤仓位 - 原始数量: {len(positions)}")

        # 1. 过滤单股仓位超限的
        filtered = self._filter_single_stock_limit(positions)

        # 2. 过滤行业仓位超限的
        filtered = self._filter_industry_limit(filtered)

        # 3. 调整总仓位
        filtered = self._adjust_total_position(filtered)

        # 4. 过滤流动性不足的（模拟，实际需要市场数据）
        # filtered = await self._filter_liquidity(filtered)

        logger.info(f"仓位过滤完成 - " f"原始: {len(positions)}, " f"过滤后: {len(filtered)}")

        return filtered

    async def check_position_limit(self, symbol: str, proposed_size: float) -> float:
        """检查仓位限制

        白皮书依据: Requirement 6.2

        Args:
            symbol: 标的代码
            proposed_size: 建议仓位大小

        Returns:
            调整后的仓位大小（考虑流动性约束）
        """
        # 应用单股仓位限制
        adjusted_size = min(proposed_size, self.max_single_stock)

        if adjusted_size < proposed_size:
            logger.warning(
                f"仓位调整 - {symbol}: "
                f"{proposed_size*100:.2f}% → {adjusted_size*100:.2f}% "
                f"(单股上限: {self.max_single_stock*100:.1f}%)"
            )

        return adjusted_size

    async def check_stop_loss_triggers(self, positions: List[Position]) -> List[str]:
        """检查止损触发（协调出货监测）

        白皮书依据: Requirement 6.5

        协调机制：
        - 如果标的处于exit_mode（出货监测触发），则跳过常规止损检查
        - Critical/High级别出货优先级高于止损

        Args:
            positions: 当前仓位列表

        Returns:
            需要止损的标的列表
        """
        stop_loss_symbols = []

        for position in positions:
            symbol = position.symbol

            # 检查是否处于出货监测模式
            if symbol in self.exit_mode:
                exit_info = self.exit_mode[symbol]
                urgency = exit_info["urgency"]

                # Critical/High级别出货：跳过常规止损，由出货监测接管
                if urgency in ["critical", "high"]:  # pylint: disable=r1724
                    logger.info(f"止损检查跳过 - {symbol}: " f"出货监测已触发({urgency}级别)，由出货保护接管")
                    continue

                # Medium级别出货：与止损协调，取最大减仓比例
                elif urgency == "medium":
                    if position.pnl_pct <= self.stop_loss_pct:
                        # 止损也触发了，取最大减仓比例
                        exit_reduce_ratio = exit_info["reduce_ratio"]
                        stop_loss_reduce_ratio = 1.0  # 止损通常是全部清仓

                        if stop_loss_reduce_ratio > exit_reduce_ratio:
                            stop_loss_symbols.append(symbol)
                            logger.warning(
                                f"止损触发（协调模式）- {symbol}: "
                                f"盈亏 {position.pnl_pct*100:.2f}% <= 止损线 {self.stop_loss_pct*100:.1f}%, "
                                f"出货监测建议减仓{exit_reduce_ratio:.0%}，止损建议清仓，采用止损"
                            )
                        else:
                            logger.info(
                                f"止损检查协调 - {symbol}: "
                                f"出货监测减仓{exit_reduce_ratio:.0%} > 止损清仓，采用出货监测"
                            )
                    continue

            # 常规止损检查
            if position.pnl_pct <= self.stop_loss_pct:
                stop_loss_symbols.append(symbol)
                logger.warning(
                    f"止损触发 - {symbol}: "
                    f"盈亏 {position.pnl_pct*100:.2f}% <= "
                    f"止损线 {self.stop_loss_pct*100:.1f}%"
                )

        return stop_loss_symbols

    async def check_take_profit_triggers(self, positions: List[Position]) -> List[str]:
        """检查止盈触发（协调出货监测）

        白皮书依据: Requirement 6.6

        协调机制：
        - Critical级别出货：暂停止盈，立即清仓
        - High级别出货：暂停止盈，大幅减仓
        - Medium级别出货：与止盈协调，取最大减仓比例

        Args:
            positions: 当前仓位列表

        Returns:
            需要止盈的标的列表
        """
        take_profit_symbols = []

        for position in positions:
            symbol = position.symbol

            # 检查是否处于出货监测模式
            if symbol in self.exit_mode:
                exit_info = self.exit_mode[symbol]
                urgency = exit_info["urgency"]

                # Critical级别出货：暂停止盈，由出货监测接管
                if urgency == "critical":  # pylint: disable=r1724
                    logger.info(f"止盈检查暂停 - {symbol}: " f"Critical级别出货监测触发，立即清仓优先")
                    continue

                # High级别出货：暂停止盈，由出货监测接管
                elif urgency == "high":
                    logger.info(f"止盈检查暂停 - {symbol}: " f"High级别出货监测触发，大幅减仓优先")
                    continue

                # Medium级别出货：与止盈协调
                elif urgency == "medium":
                    if position.pnl_pct >= self.take_profit_pct:
                        # 止盈也触发了，取最大减仓比例
                        exit_reduce_ratio = exit_info["reduce_ratio"]
                        take_profit_reduce_ratio = 0.5  # 止盈通常是部分减仓50%

                        if take_profit_reduce_ratio > exit_reduce_ratio:
                            take_profit_symbols.append(symbol)
                            logger.info(
                                f"止盈触发（协调模式）- {symbol}: "
                                f"盈亏 {position.pnl_pct*100:.2f}% >= 止盈线 {self.take_profit_pct*100:.1f}%, "
                                f"出货监测建议减仓{exit_reduce_ratio:.0%}，止盈建议减仓{take_profit_reduce_ratio:.0%}，采用止盈"
                            )
                        else:
                            logger.info(
                                f"止盈检查协调 - {symbol}: "
                                f"出货监测减仓{exit_reduce_ratio:.0%} > 止盈减仓{take_profit_reduce_ratio:.0%}，采用出货监测"
                            )
                    continue

            # 常规止盈检查
            if position.pnl_pct >= self.take_profit_pct:
                take_profit_symbols.append(symbol)
                logger.info(
                    f"止盈触发 - {symbol}: "
                    f"盈亏 {position.pnl_pct*100:.2f}% >= "
                    f"止盈线 {self.take_profit_pct*100:.1f}%"
                )

        return take_profit_symbols

    async def calculate_slippage_and_impact(
        self, symbol: str, order_size: float, daily_volume: float, tier: str = "tier1_micro"
    ) -> Dict[str, float]:
        """计算滑点和冲击成本

        白皮书依据: Requirement 14

        Args:
            symbol: 标的代码
            order_size: 订单金额
            daily_volume: 日均成交额
            tier: 资金档位

        Returns:
            {'slippage_pct': float, 'impact_cost_pct': float}
        """
        # 基础滑点（根据档位）
        tier_slippage_map = {
            "tier1_micro": 0.0015,  # 0.15%
            "tier2_small": 0.002,  # 0.20%
            "tier3_medium": 0.004,  # 0.40%
            "tier4_large": 0.005,  # 0.50%
            "tier5_million": 0.010,  # 1.00%
            "tier6_ten_million": 0.020,  # 2.00%
        }

        base_slippage = tier_slippage_map.get(tier, 0.002)

        # 订单占成交量的比例
        order_volume_ratio = order_size / daily_volume if daily_volume > 0 else 1.0

        # 滑点随订单大小增加（非线性）
        slippage_pct = base_slippage * (1 + order_volume_ratio**0.5)

        # 冲击成本（订单越大，冲击越大）
        impact_cost_pct = base_slippage * 0.5 * (order_volume_ratio**0.7)

        logger.debug(
            f"滑点计算 - {symbol}: "
            f"订单/成交量={order_volume_ratio*100:.2f}%, "
            f"滑点={slippage_pct*100:.3f}%, "
            f"冲击={impact_cost_pct*100:.3f}%"
        )

        return {"slippage_pct": slippage_pct, "impact_cost_pct": impact_cost_pct}

    async def filter_by_liquidity(
        self, positions: List[Position], market_data: Dict[str, Dict], tier: str = "tier1_micro"
    ) -> List[Position]:
        """根据流动性过滤仓位（Tier5-6增强版）

        白皮书依据: Requirement 11 - Tier5-6大资金档位流动性约束

        Args:
            positions: 仓位列表
            market_data: 市场数据 {symbol: {'daily_volume': float, 'turnover_rate': float}}
            tier: 资金档位

        Returns:
            过滤后的仓位列表
        """
        if tier not in ["tier5_million", "tier6_ten_million"]:
            # Tier1-4不需要额外的流动性过滤
            return positions

        logger.info(f"开始{tier}流动性过滤 - 原始仓位数: {len(positions)}")

        filtered = []

        for position in positions:
            symbol = position.symbol

            # 获取市场数据
            if symbol not in market_data:
                logger.warning(f"缺少市场数据 - {symbol}，跳过")
                continue

            data = market_data[symbol]
            daily_volume = data.get("daily_volume", 0)
            turnover_rate = data.get("turnover_rate", 0)

            # Tier5流动性要求
            if tier == "tier5_million":
                # 日均成交额 >= 5000万
                if daily_volume < 50_000_000:
                    logger.warning(f"Tier5流动性不足 - {symbol}: " f"日均成交额 {daily_volume/1e6:.1f}M < 50M")
                    continue

                # 换手率 >= 1%
                if turnover_rate < 0.01:
                    logger.warning(f"Tier5换手率不足 - {symbol}: " f"换手率 {turnover_rate*100:.2f}% < 1%")
                    continue

            # Tier6流动性要求（更严格）
            elif tier == "tier6_ten_million":
                # 日均成交额 >= 2亿
                if daily_volume < 200_000_000:
                    logger.warning(f"Tier6流动性不足 - {symbol}: " f"日均成交额 {daily_volume/1e6:.1f}M < 200M")
                    continue

                # 换手率 >= 2%
                if turnover_rate < 0.02:
                    logger.warning(f"Tier6换手率不足 - {symbol}: " f"换手率 {turnover_rate*100:.2f}% < 2%")
                    continue

            filtered.append(position)

        logger.info(f"{tier}流动性过滤完成 - " f"原始: {len(positions)}, " f"过滤后: {len(filtered)}")

        return filtered

    async def calculate_enhanced_impact_cost(  # pylint: disable=too-many-positional-arguments
        self,
        symbol: str,
        order_size: float,
        market_data: Dict[str, float],
        tier: str = "tier1_micro",
        stealth_mode: bool = False,
    ) -> Dict[str, float]:
        """计算增强版市场冲击成本（Tier5-6专用）

        白皮书依据: Requirement 11.2, 11.5

        Args:
            symbol: 标的代码
            order_size: 订单金额
            market_data: 市场数据 {'daily_volume': float, 'bid_ask_spread': float}
            tier: 资金档位
            stealth_mode: 是否启用隐身模式（模拟散户操作）

        Returns:
            {
                'slippage_pct': float,
                'impact_cost_pct': float,
                'total_cost_pct': float,
                'recommended_split': int,  # 建议拆分订单数
                'stealth_strategy': dict  # 隐身策略（如果启用）
            }
        """
        daily_volume = market_data.get("daily_volume", 0)
        bid_ask_spread = market_data.get("bid_ask_spread", 0.001)  # 默认0.1%

        # 订单占日成交量的比例
        order_volume_ratio = order_size / daily_volume if daily_volume > 0 else 1.0

        # Tier5-6使用更精确的冲击成本模型
        if tier in ["tier5_million", "tier6_ten_million"]:  # pylint: disable=no-else-return
            # 基础滑点
            base_slippage = 0.010 if tier == "tier5_million" else 0.020

            # 滑点 = 基础滑点 + 买卖价差 + 订单冲击
            slippage_pct = base_slippage + bid_ask_spread + (order_volume_ratio * 0.05)

            # 市场冲击成本（非线性模型）
            # 参考Kyle模型: Impact = λ * sqrt(Order Size / Daily Volume)
            impact_cost_pct = 0.02 * (order_volume_ratio**0.5)

            # 总成本
            total_cost_pct = slippage_pct + impact_cost_pct

            # 建议拆分订单数（订单越大，拆分越多）
            if order_volume_ratio > 0.10:  # 超过日成交量10%
                recommended_split = max(5, int(order_volume_ratio * 50))
            elif order_volume_ratio > 0.05:  # 超过日成交量5%
                recommended_split = 3
            else:
                recommended_split = 1

            result = {
                "slippage_pct": slippage_pct,
                "impact_cost_pct": impact_cost_pct,
                "total_cost_pct": total_cost_pct,
                "recommended_split": recommended_split,
            }

            # 隐身模式：生成散户化拆单策略
            if stealth_mode:
                result["stealth_strategy"] = self._generate_stealth_strategy(
                    order_size, recommended_split, order_volume_ratio
                )

            logger.info(
                f"{tier}冲击成本计算 - {symbol}: "
                f"订单/成交量={order_volume_ratio*100:.2f}%, "
                f"滑点={slippage_pct*100:.3f}%, "
                f"冲击={impact_cost_pct*100:.3f}%, "
                f"总成本={total_cost_pct*100:.3f}%, "
                f"建议拆分={recommended_split}单"
                f"{' (隐身模式)' if stealth_mode else ''}"
            )

            return result
        else:
            # Tier1-4使用简化模型
            return await self.calculate_slippage_and_impact(symbol, order_size, daily_volume, tier)

    def set_exit_mode(self, symbol: str, urgency: str, reduce_ratio: float, reason: str = "") -> None:
        """设置出货监测模式（由PositionProtector调用）

        白皮书依据: Requirement 6.7 - 出货监测与止损止盈协调

        Args:
            symbol: 标的代码
            urgency: 紧急程度 ('critical' | 'high' | 'medium')
            reduce_ratio: 建议减仓比例
            reason: 触发原因
        """
        from datetime import datetime  # pylint: disable=import-outside-toplevel

        self.exit_mode[symbol] = {
            "urgency": urgency,
            "reduce_ratio": reduce_ratio,
            "reason": reason,
            "timestamp": datetime.now().isoformat(),
        }

        logger.warning(
            f"出货监测模式启动 - {symbol}: " f"紧急程度={urgency}, " f"建议减仓={reduce_ratio:.0%}, " f"原因={reason}"
        )

    def clear_exit_mode(self, symbol: str) -> None:
        """清除出货监测模式

        Args:
            symbol: 标的代码
        """
        if symbol in self.exit_mode:
            del self.exit_mode[symbol]
            logger.info(f"出货监测模式清除 - {symbol}")

    def is_in_exit_mode(self, symbol: str) -> bool:
        """检查是否处于出货监测模式

        Args:
            symbol: 标的代码

        Returns:
            是否处于出货监测模式
        """
        return symbol in self.exit_mode

    def get_exit_mode_info(self, symbol: str) -> Optional[Dict[str, any]]:
        """获取出货监测模式信息

        Args:
            symbol: 标的代码

        Returns:
            出货监测信息，如果不在exit_mode则返回None
        """
        return self.exit_mode.get(symbol)

    def suggest_execution_algorithm(self, order_size: float, daily_volume: float, tier: str = "tier1_micro") -> str:
        """建议执行算法（Tier6专用）

        白皮书依据: Requirement 11.6

        Args:
            order_size: 订单金额
            daily_volume: 日均成交额
            tier: 资金档位

        Returns:
            执行算法名称 ('MARKET', 'TWAP', 'VWAP', 'POV')
        """
        if tier != "tier6_ten_million":
            return "MARKET"  # Tier1-5使用市价单

        order_volume_ratio = order_size / daily_volume if daily_volume > 0 else 1.0

        # Tier6根据订单大小选择算法
        if order_volume_ratio > 0.10:
            # 超过日成交量10%，使用POV（参与成交量比例）
            algorithm = "POV"
        elif order_volume_ratio > 0.05:
            # 超过日成交量5%，使用VWAP（成交量加权平均价）
            algorithm = "VWAP"
        elif order_volume_ratio > 0.02:
            # 超过日成交量2%，使用TWAP（时间加权平均价）
            algorithm = "TWAP"
        else:
            # 小订单，使用市价单
            algorithm = "MARKET"

        logger.info(f"Tier6执行算法建议 - " f"订单/成交量={order_volume_ratio*100:.2f}%, " f"算法={algorithm}")

        return algorithm

    def _filter_single_stock_limit(self, positions: List[Position]) -> List[Position]:
        """过滤单股仓位超限的（内部方法）

        Args:
            positions: 仓位列表

        Returns:
            过滤后的仓位列表
        """
        filtered = []

        for position in positions:
            if position.size <= self.max_single_stock:
                filtered.append(position)
            else:
                # 调整仓位到上限
                adjusted_position = Position(
                    symbol=position.symbol,
                    size=self.max_single_stock,
                    entry_price=position.entry_price,
                    current_price=position.current_price,
                    pnl_pct=position.pnl_pct,
                    holding_days=position.holding_days,
                    industry=position.industry,
                )
                filtered.append(adjusted_position)

                logger.warning(
                    f"单股仓位调整 - {position.symbol}: " f"{position.size*100:.2f}% → {self.max_single_stock*100:.2f}%"
                )

        return filtered

    def _filter_industry_limit(self, positions: List[Position]) -> List[Position]:
        """过滤行业仓位超限的（内部方法）

        Args:
            positions: 仓位列表

        Returns:
            过滤后的仓位列表
        """
        # 按行业分组
        industry_positions: Dict[str, List[Position]] = {}
        for position in positions:
            industry = position.industry
            if industry not in industry_positions:
                industry_positions[industry] = []
            industry_positions[industry].append(position)

        filtered = []

        for industry, industry_pos in industry_positions.items():
            # 计算行业总仓位
            industry_total = sum(p.size for p in industry_pos)

            if industry_total <= self.max_industry:
                # 行业仓位未超限，全部保留
                filtered.extend(industry_pos)
            else:
                # 行业仓位超限，按比例缩减
                scale_factor = self.max_industry / industry_total

                for position in industry_pos:
                    adjusted_position = Position(
                        symbol=position.symbol,
                        size=position.size * scale_factor,
                        entry_price=position.entry_price,
                        current_price=position.current_price,
                        pnl_pct=position.pnl_pct,
                        holding_days=position.holding_days,
                        industry=position.industry,
                    )
                    filtered.append(adjusted_position)

                logger.warning(
                    f"行业仓位调整 - {industry}: "
                    f"{industry_total*100:.2f}% → {self.max_industry*100:.2f}% "
                    f"(缩减比例: {scale_factor*100:.1f}%)"
                )

        return filtered

    def _adjust_total_position(self, positions: List[Position]) -> List[Position]:
        """调整总仓位（内部方法）

        Args:
            positions: 仓位列表

        Returns:
            调整后的仓位列表
        """
        total_position = sum(p.size for p in positions)

        if total_position <= self.max_position:
            return positions

        # 总仓位超限，按比例缩减
        scale_factor = self.max_position / total_position

        adjusted = []
        for position in positions:
            adjusted_position = Position(
                symbol=position.symbol,
                size=position.size * scale_factor,
                entry_price=position.entry_price,
                current_price=position.current_price,
                pnl_pct=position.pnl_pct,
                holding_days=position.holding_days,
                industry=position.industry,
            )
            adjusted.append(adjusted_position)

        logger.warning(
            f"总仓位调整: "
            f"{total_position*100:.2f}% → {self.max_position*100:.2f}% "
            f"(缩减比例: {scale_factor*100:.1f}%)"
        )

        return adjusted

    def _generate_stealth_strategy(
        self, order_size: float, base_split: int, order_volume_ratio: float
    ) -> Dict[str, any]:
        """生成隐身拆单策略（模拟散户操作）

        核心思路：
        1. 随机化订单大小 - 避免规律性
        2. 随机化时间间隔 - 模拟散户不规律下单
        3. 混合订单类型 - 限价单+市价单组合
        4. 避开敏感时段 - 避开集合竞价、尾盘等主力监控时段

        Args:
            order_size: 总订单金额
            base_split: 基础拆分数量
            order_volume_ratio: 订单占日成交量比例

        Returns:
            隐身策略字典
        """
        import random  # pylint: disable=import-outside-toplevel

        import numpy as np  # pylint: disable=import-outside-toplevel

        # 1. 增加拆单数量（比基础拆分多20%-50%）
        stealth_split = int(base_split * random.uniform(1.2, 1.5))
        stealth_split = max(stealth_split, base_split + 2)  # 至少多拆2单

        # 2. 生成随机订单大小（使用正态分布，模拟散户随机性）
        mean_size = order_size / stealth_split
        std_dev = mean_size * 0.3  # 标准差为均值的30%

        order_sizes = []
        remaining = order_size

        for i in range(stealth_split - 1):  # pylint: disable=unused-variable
            # 生成随机订单大小，但确保在合理范围内
            size = np.random.normal(mean_size, std_dev)
            size = max(mean_size * 0.5, min(size, mean_size * 1.5))  # 限制在50%-150%范围
            size = min(size, remaining * 0.8)  # 不超过剩余的80%
            order_sizes.append(size)
            remaining -= size

        # 最后一单是剩余金额
        order_sizes.append(remaining)

        # 3. 生成随机时间间隔（秒）
        # 散户特征：间隔不规律，有时快有时慢
        time_intervals = []
        for i in range(stealth_split - 1):
            if order_volume_ratio > 0.10:
                # 大订单：间隔更长，避免连续冲击
                interval = random.uniform(120, 600)  # 2-10分钟
            elif order_volume_ratio > 0.05:
                # 中等订单：中等间隔
                interval = random.uniform(60, 300)  # 1-5分钟
            else:
                # 小订单：间隔较短
                interval = random.uniform(30, 180)  # 30秒-3分钟

            time_intervals.append(int(interval))

        # 4. 混合订单类型（70%限价单 + 30%市价单，模拟散户习惯）
        order_types = []
        for i in range(stealth_split):
            if random.random() < 0.7:
                order_types.append("LIMIT")  # 限价单
            else:
                order_types.append("MARKET")  # 市价单

        # 5. 避开敏感时段（集合竞价、尾盘）
        avoid_periods = [
            {"start": "09:15", "end": "09:30", "reason": "集合竞价"},
            {"start": "14:45", "end": "15:00", "reason": "尾盘"},
        ]

        # 6. 限价单价格策略（随机偏离当前价）
        limit_price_offsets = []
        for order_type in order_types:
            if order_type == "LIMIT":
                # 买单：略低于市价（-0.1% ~ -0.5%）
                # 卖单：略高于市价（+0.1% ~ +0.5%）
                offset = random.uniform(-0.005, -0.001)  # 假设是买单
                limit_price_offsets.append(offset)
            else:
                limit_price_offsets.append(0.0)  # 市价单无偏移

        strategy = {
            "mode": "stealth",
            "total_splits": stealth_split,
            "order_sizes": [round(size, 2) for size in order_sizes],
            "time_intervals_seconds": time_intervals,
            "order_types": order_types,
            "limit_price_offsets": limit_price_offsets,
            "avoid_periods": avoid_periods,
            "description": f"隐身拆单：{stealth_split}单，随机大小+随机间隔+混合类型",
            "estimated_duration_minutes": sum(time_intervals) / 60,
            "tips": [
                "订单大小随机化，避免规律性",
                "时间间隔不规律，模拟散户行为",
                "70%限价单+30%市价单混合",
                "避开集合竞价和尾盘敏感时段",
                "限价单价格略偏离市价，增加隐蔽性",
            ],
        }

        logger.info(
            f"隐身拆单策略生成 - "
            f"拆分{stealth_split}单, "
            f"预计耗时{strategy['estimated_duration_minutes']:.1f}分钟"
        )

        return strategy
