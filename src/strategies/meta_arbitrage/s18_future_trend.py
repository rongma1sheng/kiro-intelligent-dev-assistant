"""S18 Future Trend (期指趋势) [Shadow Mode] - 股指期货趋势跟踪策略

白皮书依据: 第六章 5.2 模块化军火库 - Meta-Arbitrage系

策略特点：
- 对IC/IM主力合约进行趋势跟踪
- 默认仅模拟（Shadow Mode）
- 需要手动开启实盘交易
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from loguru import logger

from src.strategies.base_strategy import Strategy
from src.strategies.data_models import Position, Signal, StrategyConfig


class S18FutureTrendStrategy(Strategy):
    """S18 Future Trend (期指趋势) 策略 [Shadow Mode]

    白皮书依据: 第六章 5.2 模块化军火库 - Meta-Arbitrage系

    策略逻辑：
    1. 监控IC/IM主力合约价格走势
    2. 使用多周期趋势确认
    3. 结合成交量和持仓量变化
    4. 趋势跟踪交易

    适用场景：
    - 股指期货趋势明确
    - 市场波动率适中
    - 流动性充足

    注意：默认为Shadow Mode（仅模拟），需手动开启实盘
    """

    def __init__(self, config: StrategyConfig):
        """初始化S18期指趋势策略

        Args:
            config: 策略配置（Arena进化出的参数）
        """
        super().__init__(name="S18_Future_Trend", config=config)

        # Shadow Mode标志
        self.shadow_mode: bool = True  # 默认仅模拟

        # 策略特有参数
        self.trend_threshold: float = 0.02  # 趋势确认阈值（2%）
        self.volume_ratio_threshold: float = 1.5  # 成交量放大阈值
        self.oi_change_threshold: float = 0.05  # 持仓量变化阈值（5%）
        self.ma_periods: List[int] = [5, 10, 20, 60]  # 均线周期

        # 监控的期货合约
        self.target_contracts: List[str] = [
            "IC",  # 中证500股指期货
            "IM",  # 中证1000股指期货
            "IF",  # 沪深300股指期货
            "IH",  # 上证50股指期货
        ]

        logger.info(
            f"S18_Future_Trend策略初始化 [Shadow Mode: {self.shadow_mode}] - "
            f"趋势阈值: {self.trend_threshold*100:.0f}%, "
            f"量比阈值: {self.volume_ratio_threshold:.1f}"
        )

    def enable_live_trading(self) -> None:
        """开启实盘交易（退出Shadow Mode）"""
        self.shadow_mode = False
        logger.warning("S18_Future_Trend已开启实盘交易模式！请确认风险！")

    def disable_live_trading(self) -> None:
        """关闭实盘交易（进入Shadow Mode）"""
        self.shadow_mode = True
        logger.info("S18_Future_Trend已切换至Shadow Mode（仅模拟）")

    async def generate_signals(self, market_data: Dict[str, Any]) -> List[Signal]:
        """生成交易信号

        白皮书依据: Requirement 5.2

        Args:
            market_data: 市场数据

        Returns:
            交易信号列表
        """
        signals: List[Signal] = []

        futures_data = market_data.get("index_futures", {})

        for contract_prefix in self.target_contracts:
            try:
                # 获取主力合约数据
                main_contract = self._get_main_contract(contract_prefix, futures_data)
                if not main_contract:
                    continue

                contract_data = futures_data.get(main_contract, {})
                if not contract_data:
                    continue

                signal = await self._analyze_trend(main_contract, contract_data)
                if signal:
                    signals.append(signal)

            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.warning(f"分析{contract_prefix}期指趋势时出错: {e}")
                continue

        signals = sorted(signals, key=lambda x: x.confidence, reverse=True)[:2]

        if self.shadow_mode:
            logger.info(f"S18_Future_Trend [Shadow Mode] 生成{len(signals)}个模拟信号")
        else:
            logger.info(f"S18_Future_Trend [Live Mode] 生成{len(signals)}个实盘信号")

        return signals

    def _get_main_contract(self, contract_prefix: str, futures_data: Dict[str, Any]) -> Optional[str]:
        """获取主力合约代码

        Args:
            contract_prefix: 合约前缀（如IC、IM）
            futures_data: 期货数据

        Returns:
            主力合约代码或None
        """
        # 查找成交量最大的合约作为主力合约
        max_volume = 0
        main_contract = None

        for contract, data in futures_data.items():
            if contract.startswith(contract_prefix):
                volume = data.get("volume", 0)
                if volume > max_volume:
                    max_volume = volume
                    main_contract = contract

        return main_contract

    async def _analyze_trend(self, contract: str, contract_data: Dict[str, Any]) -> Optional[Signal]:
        """分析期指趋势

        Args:
            contract: 合约代码
            contract_data: 合约数据

        Returns:
            交易信号或None
        """
        price = contract_data.get("price", 0)
        volume = contract_data.get("volume", 0)
        open_interest = contract_data.get("open_interest", 0)

        if price <= 0:
            return None

        # 获取均线数据
        ma_values = {}
        for period in self.ma_periods:
            ma_key = f"ma{period}"
            ma_values[period] = contract_data.get(ma_key, price)

        # 获取历史数据
        prev_volume = contract_data.get("prev_volume", volume)
        prev_oi = contract_data.get("prev_open_interest", open_interest)

        # 计算趋势强度
        trend_score = self._calculate_trend_score(price, ma_values)

        # 计算量比
        volume_ratio = volume / prev_volume if prev_volume > 0 else 1.0

        # 计算持仓量变化
        oi_change = (open_interest - prev_oi) / prev_oi if prev_oi > 0 else 0

        # 判断交易方向
        action = "hold"
        if trend_score > 0.6 and volume_ratio > self.volume_ratio_threshold:
            # 多头趋势确认
            if oi_change > self.oi_change_threshold:
                # 持仓量增加，趋势可能延续
                action = "buy"
        elif trend_score < -0.6 and volume_ratio > self.volume_ratio_threshold:
            # 空头趋势确认
            if oi_change > self.oi_change_threshold:
                # 持仓量增加，趋势可能延续
                action = "sell"

        if action == "hold":
            return None

        confidence = self._calculate_trend_confidence(trend_score, volume_ratio, oi_change)

        mode_tag = "[Shadow]" if self.shadow_mode else "[Live]"
        reason = f"{mode_tag} 趋势得分{trend_score:.2f}, " f"量比{volume_ratio:.2f}, " f"持仓变化{oi_change*100:.1f}%"

        logger.info(f"S18_Future_Trend信号 - {contract}: {reason}")

        return Signal(
            symbol=contract, action=action, confidence=confidence, timestamp=datetime.now().isoformat(), reason=reason
        )

    def _calculate_trend_score(self, price: float, ma_values: Dict[int, float]) -> float:
        """计算趋势得分

        Args:
            price: 当前价格
            ma_values: 各周期均线值

        Returns:
            趋势得分 (-1.0 到 1.0)
        """
        score = 0.0
        weights = {5: 0.4, 10: 0.3, 20: 0.2, 60: 0.1}

        for period, weight in weights.items():
            ma = ma_values.get(period, price)
            if ma > 0:
                deviation = (price - ma) / ma
                # 将偏离度转换为得分
                if deviation > self.trend_threshold:
                    score += weight
                elif deviation < -self.trend_threshold:
                    score -= weight

        # 检查均线排列
        ma_list = [ma_values.get(p, price) for p in sorted(self.ma_periods)]
        if all(ma_list[i] >= ma_list[i + 1] for i in range(len(ma_list) - 1)):
            # 多头排列
            score += 0.2
        elif all(ma_list[i] <= ma_list[i + 1] for i in range(len(ma_list) - 1)):
            # 空头排列
            score -= 0.2

        return max(-1.0, min(1.0, score))

    def _calculate_trend_confidence(self, trend_score: float, volume_ratio: float, oi_change: float) -> float:
        """计算趋势信号置信度"""
        trend_conf = min(0.35, abs(trend_score) * 0.35)
        volume_conf = min(0.25, (volume_ratio - 1) * 0.15)
        oi_conf = min(0.20, abs(oi_change) * 2)

        confidence = trend_conf + volume_conf + oi_conf
        confidence = max(0.5, min(0.80, confidence + 0.3))
        return confidence

    async def calculate_position_sizes(self, signals: List[Signal]) -> List[Position]:
        """计算仓位大小"""
        positions: List[Position] = []

        # Shadow Mode下不分配实际仓位
        if self.shadow_mode:
            for signal in signals:
                positions.append(
                    Position(
                        symbol=signal.symbol,
                        size=0.0,  # Shadow Mode仓位为0
                        entry_price=1.0,  # 占位价格
                        current_price=1.0,  # 占位价格
                        pnl_pct=0.0,
                        holding_days=0,
                        industry="index_futures_shadow",
                    )
                )
            logger.info(f"S18_Future_Trend [Shadow Mode] 模拟仓位: {len(positions)}个标的")
            return positions

        # Live Mode正常分配仓位
        total_allocated = 0.0
        max_total = min(self.max_position, 0.10)  # 期指趋势总仓位上限10%

        for signal in sorted(signals, key=lambda x: x.confidence, reverse=True):
            if signal.action not in ["buy", "sell"]:
                continue

            base_size = min(self.max_single_stock, 0.05) * signal.confidence

            if total_allocated + base_size > max_total:
                base_size = max_total - total_allocated

            if base_size <= 0.005:
                break

            positions.append(
                Position(
                    symbol=signal.symbol,
                    size=base_size,
                    entry_price=1.0,  # 占位价格，实际执行时更新
                    current_price=1.0,  # 占位价格，实际执行时更新
                    pnl_pct=0.0,
                    holding_days=0,
                    industry="index_futures",
                )
            )
            total_allocated += base_size

        logger.info(
            f"S18_Future_Trend [Live Mode] 仓位计算完成 - 标的数: {len(positions)}, 总仓位: {total_allocated*100:.2f}%"
        )
        return positions
