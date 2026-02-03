"""S17 Derivatives Linkage (期现联动) - 衍生品先行指标策略

白皮书依据: 第六章 5.2 模块化军火库 - Meta-Arbitrage系

策略特点：
- 监控期权隐含波动率或期货升贴水异动
- 作为现货先行指标
- 利用衍生品市场的信息优势
"""

from datetime import datetime
from typing import Any, Dict, List

from loguru import logger

from src.strategies.base_strategy import Strategy
from src.strategies.data_models import Position, Signal, StrategyConfig


class S17DerivativesLinkageStrategy(Strategy):
    """S17 Derivatives Linkage (期现联动) 策略

    白皮书依据: 第六章 5.2 模块化军火库 - Meta-Arbitrage系

    策略逻辑：
    1. 监控期权隐含波动率（IV）变化
    2. 监控期货升贴水异动
    3. 将衍生品信号作为现货先行指标
    4. 在现货市场执行交易

    适用场景：
    - 期权IV异常上升（预示大波动）
    - 期货升水/贴水异常（预示方向）
    - 衍生品市场出现异常交易
    """

    def __init__(self, config: StrategyConfig):
        """初始化S17期现联动策略

        Args:
            config: 策略配置（Arena进化出的参数）
        """
        super().__init__(name="S17_Derivatives_Linkage", config=config)

        # 策略特有参数
        self.iv_change_threshold: float = 0.15  # IV变化阈值（15%）
        self.premium_threshold: float = 0.01  # 升贴水阈值（1%）
        self.pcr_threshold: float = 1.5  # Put/Call Ratio阈值
        self.min_option_volume: float = 10000  # 最小期权成交量

        # 标的映射
        self.derivatives_to_spot: Dict[str, str] = {
            "510050": "510050.SH",  # 50ETF期权 -> 50ETF
            "510300": "510300.SH",  # 300ETF期权 -> 300ETF
            "159919": "159919.SZ",  # 300ETF期权 -> 300ETF
            "510500": "510500.SH",  # 500ETF期权 -> 500ETF
        }

        logger.info(
            f"S17_Derivatives_Linkage策略初始化 - "
            f"IV阈值: {self.iv_change_threshold*100:.0f}%, "
            f"升贴水阈值: {self.premium_threshold*100:.1f}%"
        )

    async def generate_signals(self, market_data: Dict[str, Any]) -> List[Signal]:
        """生成交易信号

        白皮书依据: Requirement 5.2

        Args:
            market_data: 市场数据

        Returns:
            交易信号列表
        """
        signals: List[Signal] = []

        # 期权IV信号
        options_data = market_data.get("options", {})
        iv_signals = await self._analyze_iv_signals(options_data)
        signals.extend(iv_signals)

        # 期货升贴水信号
        futures_data = market_data.get("futures", {})
        spot_data = market_data.get("spot", {})
        premium_signals = await self._analyze_premium_signals(futures_data, spot_data)
        signals.extend(premium_signals)

        # PCR信号
        pcr_signals = await self._analyze_pcr_signals(options_data)
        signals.extend(pcr_signals)

        signals = sorted(signals, key=lambda x: x.confidence, reverse=True)[:3]
        logger.info(f"S17_Derivatives_Linkage生成{len(signals)}个期现联动信号")
        return signals

    async def _analyze_iv_signals(self, options_data: Dict[str, Any]) -> List[Signal]:
        """分析期权隐含波动率信号

        Args:
            options_data: 期权数据

        Returns:
            交易信号列表
        """
        signals: List[Signal] = []

        for underlying, option_info in options_data.items():
            try:
                current_iv = option_info.get("implied_volatility", 0)
                hist_iv_mean = option_info.get("hist_iv_mean", 0.2)
                hist_iv_std = option_info.get("hist_iv_std", 0.05)
                option_volume = option_info.get("volume", 0)

                if current_iv <= 0 or option_volume < self.min_option_volume:
                    continue

                # 计算IV变化率
                iv_change = (current_iv - hist_iv_mean) / hist_iv_mean if hist_iv_mean > 0 else 0

                # 计算IV Z-Score
                iv_zscore = (current_iv - hist_iv_mean) / hist_iv_std if hist_iv_std > 0 else 0

                if abs(iv_change) < self.iv_change_threshold:
                    continue

                # 获取对应现货标的
                spot_symbol = self.derivatives_to_spot.get(underlying, "")
                if not spot_symbol:
                    continue

                # IV上升通常预示大波动，但方向需要结合其他指标
                # 这里简化为：IV大幅上升时保持观望，IV回落时可能是买入机会
                action = "hold"
                if iv_change < -self.iv_change_threshold and iv_zscore < -1.5:
                    # IV回落，波动率收敛，可能是买入机会
                    action = "buy"
                elif iv_change > self.iv_change_threshold * 2 and iv_zscore > 2.5:
                    # IV大幅上升，可能预示下跌风险
                    action = "sell"

                if action == "hold":
                    continue

                confidence = self._calculate_iv_confidence(iv_change, iv_zscore, option_volume)

                reason = f"IV变化{iv_change*100:.1f}%, " f"当前IV: {current_iv*100:.1f}%, " f"Z-Score: {iv_zscore:.2f}"

                logger.info(f"S17_Derivatives_Linkage IV信号 - {spot_symbol}: {reason}")

                signals.append(
                    Signal(
                        symbol=spot_symbol,
                        action=action,
                        confidence=confidence,
                        timestamp=datetime.now().isoformat(),
                        reason=reason,
                    )
                )

            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.warning(f"分析{underlying}期权IV时出错: {e}")
                continue

        return signals

    async def _analyze_premium_signals(self, futures_data: Dict[str, Any], spot_data: Dict[str, Any]) -> List[Signal]:
        """分析期货升贴水信号

        Args:
            futures_data: 期货数据
            spot_data: 现货数据

        Returns:
            交易信号列表
        """
        signals: List[Signal] = []

        for symbol, futures_info in futures_data.items():
            try:
                futures_price = futures_info.get("price", 0)
                spot_symbol = futures_info.get("spot_symbol", "")

                if not spot_symbol or spot_symbol not in spot_data:
                    continue

                spot_price = spot_data[spot_symbol].get("price", 0)

                if futures_price <= 0 or spot_price <= 0:
                    continue

                # 计算升贴水率
                premium_rate = (futures_price - spot_price) / spot_price

                # 获取历史升贴水数据
                hist_premium_mean = futures_info.get("hist_premium_mean", 0)
                hist_premium_std = futures_info.get("hist_premium_std", 0.005)

                # 计算升贴水偏离度
                premium_zscore = (premium_rate - hist_premium_mean) / hist_premium_std if hist_premium_std > 0 else 0

                if abs(premium_rate - hist_premium_mean) < self.premium_threshold:
                    continue

                # 判断交易方向
                action = "hold"
                if premium_rate > hist_premium_mean + self.premium_threshold and premium_zscore > 2.0:
                    # 期货升水异常，可能预示现货上涨
                    action = "buy"
                elif premium_rate < hist_premium_mean - self.premium_threshold and premium_zscore < -2.0:
                    # 期货贴水异常，可能预示现货下跌
                    action = "sell"

                if action == "hold":
                    continue

                confidence = self._calculate_premium_confidence(premium_rate, premium_zscore)

                reason = (
                    f"升贴水{premium_rate*100:.2f}%, "
                    f"历史均值{hist_premium_mean*100:.2f}%, "
                    f"Z-Score: {premium_zscore:.2f}"
                )

                logger.info(f"S17_Derivatives_Linkage升贴水信号 - {spot_symbol}: {reason}")

                signals.append(
                    Signal(
                        symbol=spot_symbol,
                        action=action,
                        confidence=confidence,
                        timestamp=datetime.now().isoformat(),
                        reason=reason,
                    )
                )

            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.warning(f"分析{symbol}升贴水时出错: {e}")
                continue

        return signals

    async def _analyze_pcr_signals(self, options_data: Dict[str, Any]) -> List[Signal]:
        """分析Put/Call Ratio信号

        Args:
            options_data: 期权数据

        Returns:
            交易信号列表
        """
        signals: List[Signal] = []

        for underlying, option_info in options_data.items():
            try:
                put_volume = option_info.get("put_volume", 0)
                call_volume = option_info.get("call_volume", 0)

                if call_volume <= 0:
                    continue

                pcr = put_volume / call_volume
                hist_pcr_mean = option_info.get("hist_pcr_mean", 1.0)

                spot_symbol = self.derivatives_to_spot.get(underlying, "")
                if not spot_symbol:
                    continue

                # 判断交易方向
                action = "hold"
                if pcr > self.pcr_threshold and pcr > hist_pcr_mean * 1.5:
                    # PCR过高，市场过度悲观，可能是反向买入机会
                    action = "buy"
                elif pcr < 1 / self.pcr_threshold and pcr < hist_pcr_mean * 0.6:
                    # PCR过低，市场过度乐观，可能是卖出信号
                    action = "sell"

                if action == "hold":
                    continue

                confidence = self._calculate_pcr_confidence(pcr, hist_pcr_mean)

                reason = (
                    f"PCR: {pcr:.2f}, " f"历史均值: {hist_pcr_mean:.2f}, " f"Put量: {put_volume}, Call量: {call_volume}"
                )

                logger.info(f"S17_Derivatives_Linkage PCR信号 - {spot_symbol}: {reason}")

                signals.append(
                    Signal(
                        symbol=spot_symbol,
                        action=action,
                        confidence=confidence,
                        timestamp=datetime.now().isoformat(),
                        reason=reason,
                    )
                )

            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.warning(f"分析{underlying}PCR时出错: {e}")
                continue

        return signals

    def _calculate_iv_confidence(self, iv_change: float, iv_zscore: float, volume: float) -> float:
        """计算IV信号置信度"""
        change_score = min(0.30, abs(iv_change) * 1.5)
        zscore_score = min(0.25, abs(iv_zscore) / 8)
        volume_score = min(0.20, volume / 100000)

        confidence = change_score + zscore_score + volume_score
        confidence = max(0.5, min(0.80, confidence + 0.3))
        return confidence

    def _calculate_premium_confidence(self, premium_rate: float, premium_zscore: float) -> float:
        """计算升贴水信号置信度"""
        premium_score = min(0.35, abs(premium_rate) * 20)
        zscore_score = min(0.30, abs(premium_zscore) / 8)

        confidence = premium_score + zscore_score
        confidence = max(0.5, min(0.80, confidence + 0.3))
        return confidence

    def _calculate_pcr_confidence(self, pcr: float, hist_pcr_mean: float) -> float:
        """计算PCR信号置信度"""
        deviation = abs(pcr - hist_pcr_mean) / hist_pcr_mean if hist_pcr_mean > 0 else 0
        deviation_score = min(0.40, deviation * 0.8)

        confidence = deviation_score
        confidence = max(0.5, min(0.75, confidence + 0.4))
        return confidence

    async def calculate_position_sizes(self, signals: List[Signal]) -> List[Position]:
        """计算仓位大小"""
        positions: List[Position] = []
        total_allocated = 0.0
        max_total = min(self.max_position, 0.15)  # 期现联动总仓位上限15%

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
                    industry="derivatives_linkage",
                )
            )
            total_allocated += base_size

        logger.info(
            f"S17_Derivatives_Linkage仓位计算完成 - 标的数: {len(positions)}, 总仓位: {total_allocated*100:.2f}%"
        )
        return positions
