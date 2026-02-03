"""S14 Cross-Domain Arb (跨域套利) - 期货/现货联动套利策略

白皮书依据: 第六章 5.2 模块化军火库 - Meta-Arbitrage系

策略特点：
- 基于期货/现货或产业链上下游价格传导的联动套利
- 监控期现价差异常
- 利用产业链价格传导时滞获利
"""

from datetime import datetime
from typing import Any, Dict, List

from loguru import logger

from src.strategies.base_strategy import Strategy
from src.strategies.data_models import Position, Signal, StrategyConfig


class S14CrossDomainArbStrategy(Strategy):
    """S14 Cross-Domain Arb (跨域套利) 策略

    白皮书依据: 第六章 5.2 模块化军火库 - Meta-Arbitrage系

    策略逻辑：
    1. 监控期货与现货的价差（基差）
    2. 识别产业链上下游价格传导机会
    3. 利用价格传导时滞进行套利
    4. 严格控制风险敞口

    适用场景：
    - 期现基差异常扩大/收窄
    - 产业链价格传导延迟
    - 跨市场价格失衡
    """

    def __init__(self, config: StrategyConfig):
        """初始化S14跨域套利策略

        Args:
            config: 策略配置（Arena进化出的参数）
        """
        super().__init__(name="S14_Cross_Domain_Arb", config=config)

        # 策略特有参数
        self.basis_threshold: float = 0.02  # 基差阈值（2%）
        self.spread_threshold: float = 0.015  # 价差阈值（1.5%）
        self.min_correlation: float = 0.7  # 最小相关性
        self.max_holding_days: int = 10  # 最大持仓天数

        # 产业链配对关系
        self.industry_pairs: Dict[str, List[str]] = {
            "steel": ["iron_ore", "coking_coal", "rebar"],
            "oil": ["crude_oil", "gasoline", "diesel"],
            "copper": ["copper_futures", "copper_etf"],
            "gold": ["gold_futures", "gold_etf"],
        }

        logger.info(
            f"S14_Cross_Domain_Arb策略初始化 - "
            f"基差阈值: {self.basis_threshold*100:.1f}%, "
            f"价差阈值: {self.spread_threshold*100:.1f}%"
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

        # 期现套利信号
        futures_data = market_data.get("futures", {})
        spot_data = market_data.get("spot", {})

        basis_signals = await self._analyze_basis_arbitrage(futures_data, spot_data)
        signals.extend(basis_signals)

        # 产业链套利信号
        chain_signals = await self._analyze_industry_chain(market_data)
        signals.extend(chain_signals)

        signals = sorted(signals, key=lambda x: x.confidence, reverse=True)[:3]
        logger.info(f"S14_Cross_Domain_Arb生成{len(signals)}个跨域套利信号")
        return signals

    async def _analyze_basis_arbitrage(self, futures_data: Dict[str, Any], spot_data: Dict[str, Any]) -> List[Signal]:
        """分析期现基差套利机会

        Args:
            futures_data: 期货数据
            spot_data: 现货数据

        Returns:
            交易信号列表
        """
        signals: List[Signal] = []

        for symbol, futures_info in futures_data.items():
            try:
                spot_symbol = self._get_spot_symbol(symbol)
                if spot_symbol not in spot_data:
                    continue

                spot_info = spot_data[spot_symbol]

                futures_price = futures_info.get("price", 0)
                spot_price = spot_info.get("price", 0)

                if futures_price <= 0 or spot_price <= 0:
                    continue

                # 计算基差率
                basis_rate = (futures_price - spot_price) / spot_price

                # 获取历史基差均值
                hist_basis_mean = futures_info.get("hist_basis_mean", 0)
                hist_basis_std = futures_info.get("hist_basis_std", 0.01)

                # 计算基差偏离度
                if hist_basis_std > 0:
                    basis_zscore = (basis_rate - hist_basis_mean) / hist_basis_std
                else:
                    basis_zscore = 0

                # 判断套利方向
                action = "hold"
                if basis_zscore > 2.0 and basis_rate > self.basis_threshold:
                    # 基差过大，做空期货做多现货
                    action = "sell"  # 卖出期货
                elif basis_zscore < -2.0 and basis_rate < -self.basis_threshold:
                    # 基差过小，做多期货做空现货
                    action = "buy"  # 买入期货

                if action == "hold":
                    continue

                confidence = self._calculate_basis_confidence(basis_rate, basis_zscore, futures_info.get("volume", 0))

                reason = (
                    f"期现基差{basis_rate*100:.2f}%, "
                    f"Z-Score: {basis_zscore:.2f}, "
                    f"历史均值: {hist_basis_mean*100:.2f}%"
                )

                logger.info(f"S14_Cross_Domain_Arb基差信号 - {symbol}: {reason}")

                signals.append(
                    Signal(
                        symbol=symbol,
                        action=action,
                        confidence=confidence,
                        timestamp=datetime.now().isoformat(),
                        reason=reason,
                    )
                )

            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.warning(f"分析{symbol}基差时出错: {e}")
                continue

        return signals

    async def _analyze_industry_chain(self, market_data: Dict[str, Any]) -> List[Signal]:
        """分析产业链套利机会

        Args:
            market_data: 市场数据

        Returns:
            交易信号列表
        """
        signals: List[Signal] = []

        chain_data = market_data.get("industry_chain", {})

        for chain_name, related_symbols in self.industry_pairs.items():  # pylint: disable=unused-variable
            try:
                chain_info = chain_data.get(chain_name, {})
                if not chain_info:
                    continue

                # 获取上下游价格变化
                upstream_change = chain_info.get("upstream_change", 0)
                downstream_change = chain_info.get("downstream_change", 0)

                # 计算价格传导差异
                spread = upstream_change - downstream_change

                if abs(spread) < self.spread_threshold:
                    continue

                # 判断套利方向
                action = "hold"
                target_symbol = ""

                if spread > self.spread_threshold:
                    # 上游涨幅大于下游，买入下游
                    action = "buy"
                    target_symbol = chain_info.get("downstream_symbol", "")
                elif spread < -self.spread_threshold:
                    # 下游涨幅大于上游，买入上游
                    action = "buy"
                    target_symbol = chain_info.get("upstream_symbol", "")

                if action == "hold" or not target_symbol:
                    continue

                confidence = self._calculate_chain_confidence(spread, chain_info.get("correlation", 0.5))

                reason = (
                    f"产业链{chain_name}价差{spread*100:.2f}%, "
                    f"上游涨跌{upstream_change*100:.2f}%, "
                    f"下游涨跌{downstream_change*100:.2f}%"
                )

                logger.info(f"S14_Cross_Domain_Arb产业链信号 - {target_symbol}: {reason}")

                signals.append(
                    Signal(
                        symbol=target_symbol,
                        action=action,
                        confidence=confidence,
                        timestamp=datetime.now().isoformat(),
                        reason=reason,
                    )
                )

            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.warning(f"分析{chain_name}产业链时出错: {e}")
                continue

        return signals

    def _get_spot_symbol(self, futures_symbol: str) -> str:
        """获取期货对应的现货标的"""
        mapping = {
            "IF": "510300.SH",  # 沪深300ETF
            "IC": "510500.SH",  # 中证500ETF
            "IM": "159845.SZ",  # 中证1000ETF
            "IH": "510050.SH",  # 上证50ETF
        }
        prefix = futures_symbol[:2] if len(futures_symbol) >= 2 else futures_symbol
        return mapping.get(prefix, "")

    def _calculate_basis_confidence(self, basis_rate: float, basis_zscore: float, volume: float) -> float:
        """计算基差套利信号置信度"""
        basis_score = min(0.30, abs(basis_rate) * 10)
        zscore_score = min(0.30, abs(basis_zscore) / 10)
        volume_score = min(0.20, volume / 1e9)

        confidence = basis_score + zscore_score + volume_score
        confidence = max(0.5, min(0.85, confidence + 0.3))
        return confidence

    def _calculate_chain_confidence(self, spread: float, correlation: float) -> float:
        """计算产业链套利信号置信度"""
        spread_score = min(0.35, abs(spread) * 15)
        corr_score = min(0.30, correlation * 0.4)

        confidence = spread_score + corr_score
        confidence = max(0.5, min(0.80, confidence + 0.3))
        return confidence

    async def calculate_position_sizes(self, signals: List[Signal]) -> List[Position]:
        """计算仓位大小"""
        positions: List[Position] = []
        total_allocated = 0.0
        max_total = min(self.max_position, 0.15)  # 跨域套利总仓位上限15%

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
                    industry="cross_domain_arb",
                )
            )
            total_allocated += base_size

        logger.info(f"S14_Cross_Domain_Arb仓位计算完成 - 标的数: {len(positions)}, 总仓位: {total_allocated*100:.2f}%")
        return positions
