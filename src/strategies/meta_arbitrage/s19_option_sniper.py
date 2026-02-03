"""S19 Option Sniper (期权狙击) [Shadow Mode] - 舆情驱动期权交易策略

白皮书依据: 第六章 5.2 模块化军火库 - Meta-Arbitrage系

策略特点：
- 舆情爆发时买入虚值期权（Gamma Scalping）
- 保持Delta Neutral对冲
- 默认仅模拟（Shadow Mode）
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger

from src.strategies.base_strategy import Strategy
from src.strategies.data_models import Position, Signal, StrategyConfig


class S19OptionSniperStrategy(Strategy):
    """S19 Option Sniper (期权狙击) 策略 [Shadow Mode]

    白皮书依据: 第六章 5.2 模块化军火库 - Meta-Arbitrage系

    策略逻辑：
    1. 监控舆情爆发事件
    2. 舆情爆发时买入虚值期权
    3. 利用Gamma Scalping获利
    4. 保持Delta Neutral对冲

    适用场景：
    - 重大舆情事件爆发
    - 市场波动率即将上升
    - 期权定价相对便宜

    注意：默认为Shadow Mode（仅模拟），需手动开启实盘
    """

    def __init__(self, config: StrategyConfig):
        """初始化S19期权狙击策略

        Args:
            config: 策略配置（Arena进化出的参数）
        """
        super().__init__(name="S19_Option_Sniper", config=config)

        # Shadow Mode标志
        self.shadow_mode: bool = True  # 默认仅模拟

        # 策略特有参数
        self.sentiment_threshold: float = 0.7  # 舆情强度阈值
        self.iv_percentile_threshold: float = 30  # IV百分位阈值（低于30%时买入）
        self.otm_delta_range: Tuple[float, float] = (0.15, 0.35)  # 虚值期权Delta范围
        self.max_days_to_expiry: int = 30  # 最大到期天数
        self.min_days_to_expiry: int = 7  # 最小到期天数

        # Delta对冲参数
        self.delta_neutral_threshold: float = 0.1  # Delta中性阈值
        self.rebalance_frequency: int = 60  # 再平衡频率（分钟）

        logger.info(
            f"S19_Option_Sniper策略初始化 [Shadow Mode: {self.shadow_mode}] - "
            f"舆情阈值: {self.sentiment_threshold}, "
            f"IV百分位阈值: {self.iv_percentile_threshold}%"
        )

    def enable_live_trading(self) -> None:
        """开启实盘交易（退出Shadow Mode）"""
        self.shadow_mode = False
        logger.warning("S19_Option_Sniper已开启实盘交易模式！请确认风险！")

    def disable_live_trading(self) -> None:
        """关闭实盘交易（进入Shadow Mode）"""
        self.shadow_mode = True
        logger.info("S19_Option_Sniper已切换至Shadow Mode（仅模拟）")

    async def generate_signals(self, market_data: Dict[str, Any]) -> List[Signal]:
        """生成交易信号

        白皮书依据: Requirement 5.2

        Args:
            market_data: 市场数据

        Returns:
            交易信号列表
        """
        signals: List[Signal] = []

        # 获取舆情数据
        sentiment_data = market_data.get("sentiment", {})
        options_data = market_data.get("options", {})

        # 检测舆情爆发
        sentiment_events = await self._detect_sentiment_events(sentiment_data)

        for event in sentiment_events:
            try:
                underlying = event.get("underlying", "")
                if not underlying:
                    continue

                # 获取对应期权数据
                option_chain = options_data.get(underlying, {})
                if not option_chain:
                    continue

                # 选择最优期权合约
                best_option = await self._select_best_option(underlying, option_chain, event)

                if best_option:
                    signals.append(best_option)

            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.warning(f"分析舆情事件时出错: {e}")
                continue

        signals = sorted(signals, key=lambda x: x.confidence, reverse=True)[:2]

        if self.shadow_mode:
            logger.info(f"S19_Option_Sniper [Shadow Mode] 生成{len(signals)}个模拟信号")
        else:
            logger.info(f"S19_Option_Sniper [Live Mode] 生成{len(signals)}个实盘信号")

        return signals

    async def _detect_sentiment_events(self, sentiment_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """检测舆情爆发事件

        Args:
            sentiment_data: 舆情数据

        Returns:
            舆情事件列表
        """
        events: List[Dict[str, Any]] = []

        for symbol, sentiment_info in sentiment_data.items():
            try:
                sentiment_score = sentiment_info.get("score", 0)
                sentiment_change = sentiment_info.get("change_1h", 0)
                news_count = sentiment_info.get("news_count_1h", 0)

                # 检测舆情爆发条件
                is_event = False
                event_type = "neutral"

                if sentiment_score > self.sentiment_threshold and sentiment_change > 0.3:
                    # 正面舆情爆发
                    is_event = True
                    event_type = "positive"
                elif sentiment_score < -self.sentiment_threshold and sentiment_change < -0.3:
                    # 负面舆情爆发
                    is_event = True
                    event_type = "negative"
                elif news_count > 50 and abs(sentiment_change) > 0.2:
                    # 新闻量爆发
                    is_event = True
                    event_type = "volume_spike"

                if is_event:
                    events.append(
                        {
                            "underlying": symbol,
                            "sentiment_score": sentiment_score,
                            "sentiment_change": sentiment_change,
                            "news_count": news_count,
                            "event_type": event_type,
                        }
                    )

            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.warning(f"检测{symbol}舆情时出错: {e}")
                continue

        return events

    async def _select_best_option(
        self, underlying: str, option_chain: Dict[str, Any], event: Dict[str, Any]  # pylint: disable=unused-argument
    ) -> Optional[Signal]:
        """选择最优期权合约

        Args:
            underlying: 标的代码
            option_chain: 期权链数据
            event: 舆情事件

        Returns:
            交易信号或None
        """
        event_type = event.get("event_type", "neutral")

        # 根据舆情方向选择期权类型
        if event_type == "positive":
            option_type = "call"
        elif event_type == "negative":
            option_type = "put"
        else:
            # 中性事件，买入跨式组合（这里简化为买入call）
            option_type = "call"

        # 筛选符合条件的期权
        candidates: List[Dict[str, Any]] = []

        for contract, option_info in option_chain.items():
            try:
                if option_info.get("type") != option_type:
                    continue

                delta = abs(option_info.get("delta", 0))
                days_to_expiry = option_info.get("days_to_expiry", 0)
                iv_percentile = option_info.get("iv_percentile", 50)

                # 检查Delta范围（虚值期权）
                if not self.otm_delta_range[0] <= delta <= self.otm_delta_range[1]:
                    continue

                # 检查到期天数
                if not self.min_days_to_expiry <= days_to_expiry <= self.max_days_to_expiry:
                    continue

                # 检查IV百分位（寻找便宜的期权）
                if iv_percentile > self.iv_percentile_threshold:
                    continue

                candidates.append(
                    {
                        "contract": contract,
                        "delta": delta,
                        "gamma": option_info.get("gamma", 0),
                        "theta": option_info.get("theta", 0),
                        "vega": option_info.get("vega", 0),
                        "iv": option_info.get("implied_volatility", 0),
                        "iv_percentile": iv_percentile,
                        "days_to_expiry": days_to_expiry,
                        "price": option_info.get("price", 0),
                        "volume": option_info.get("volume", 0),
                    }
                )

            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.warning(f"筛选期权{contract}时出错: {e}")
                continue

        if not candidates:
            return None

        # 选择Gamma最大的期权（Gamma Scalping）
        best_candidate = max(candidates, key=lambda x: x["gamma"])

        confidence = self._calculate_option_confidence(event, best_candidate)

        mode_tag = "[Shadow]" if self.shadow_mode else "[Live]"
        reason = (
            f"{mode_tag} 舆情{event_type}, "
            f"Delta: {best_candidate['delta']:.2f}, "
            f"Gamma: {best_candidate['gamma']:.4f}, "
            f"IV百分位: {best_candidate['iv_percentile']:.0f}%"
        )

        logger.info(f"S19_Option_Sniper信号 - {best_candidate['contract']}: {reason}")

        return Signal(
            symbol=best_candidate["contract"],
            action="buy",
            confidence=confidence,
            timestamp=datetime.now().isoformat(),
            reason=reason,
        )

    def _calculate_option_confidence(self, event: Dict[str, Any], option: Dict[str, Any]) -> float:
        """计算期权信号置信度"""
        # 舆情强度得分
        sentiment_score = abs(event.get("sentiment_score", 0))
        sentiment_conf = min(0.30, sentiment_score * 0.4)

        # Gamma得分（Gamma越大，Gamma Scalping潜力越大）
        gamma = option.get("gamma", 0)
        gamma_conf = min(0.25, gamma * 50)

        # IV百分位得分（越低越好）
        iv_percentile = option.get("iv_percentile", 50)
        iv_conf = min(0.25, (50 - iv_percentile) / 100)

        # 流动性得分
        volume = option.get("volume", 0)
        volume_conf = min(0.15, volume / 10000)

        confidence = sentiment_conf + gamma_conf + iv_conf + volume_conf
        confidence = max(0.5, min(0.80, confidence + 0.2))
        return confidence

    async def calculate_delta_hedge(
        self, option_positions: List[Position], market_data: Dict[str, Any]
    ) -> Dict[str, float]:
        """计算Delta对冲需求

        Args:
            option_positions: 期权持仓
            market_data: 市场数据

        Returns:
            对冲需求字典 {underlying: hedge_quantity}
        """
        hedge_requirements: Dict[str, float] = {}

        options_data = market_data.get("options", {})

        for position in option_positions:
            try:
                option_info = options_data.get(position.symbol, {})
                if not option_info:
                    continue

                underlying = option_info.get("underlying", "")
                delta = option_info.get("delta", 0)
                contract_multiplier = option_info.get("multiplier", 10000)

                # 计算持仓Delta
                position_delta = delta * position.size * contract_multiplier

                # 累加到对应标的
                if underlying in hedge_requirements:
                    hedge_requirements[underlying] += position_delta
                else:
                    hedge_requirements[underlying] = position_delta

            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.warning(f"计算{position.symbol}Delta对冲时出错: {e}")
                continue

        # 转换为对冲数量（负Delta需要买入标的对冲）
        for underlying in hedge_requirements:
            hedge_requirements[underlying] = -hedge_requirements[underlying]

        return hedge_requirements

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
                        industry="option_shadow",
                    )
                )
            logger.info(f"S19_Option_Sniper [Shadow Mode] 模拟仓位: {len(positions)}个标的")
            return positions

        # Live Mode正常分配仓位
        total_allocated = 0.0
        max_total = min(self.max_position, 0.05)  # 期权狙击总仓位上限5%

        for signal in sorted(signals, key=lambda x: x.confidence, reverse=True):
            if signal.action != "buy":
                continue

            # 期权仓位较小
            base_size = min(self.max_single_stock, 0.02) * signal.confidence

            if total_allocated + base_size > max_total:
                base_size = max_total - total_allocated

            if base_size <= 0.002:
                break

            positions.append(
                Position(
                    symbol=signal.symbol,
                    size=base_size,
                    entry_price=1.0,  # 占位价格，实际执行时更新
                    current_price=1.0,  # 占位价格，实际执行时更新
                    pnl_pct=0.0,
                    holding_days=0,
                    industry="option",
                )
            )
            total_allocated += base_size

        logger.info(
            f"S19_Option_Sniper [Live Mode] 仓位计算完成 - 标的数: {len(positions)}, 总仓位: {total_allocated*100:.2f}%"
        )
        return positions
