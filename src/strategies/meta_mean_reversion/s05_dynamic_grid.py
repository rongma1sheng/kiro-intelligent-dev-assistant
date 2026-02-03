"""S05 Dynamic Grid (网格) - AI预测支撑压力位网格策略

白皮书依据: 第六章 5.2 模块化军火库 - Meta-MeanReversion系

策略特点：
- 震荡市中利用AI预测支撑压力位
- 高抛低吸的网格策略
- 适合横盘震荡行情
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger

from src.strategies.base_strategy import Strategy
from src.strategies.data_models import Position, Signal, StrategyConfig


class S05DynamicGridStrategy(Strategy):
    """S05 Dynamic Grid (网格) 策略

    白皮书依据: 第六章 5.2 模块化军火库 - Meta-MeanReversion系

    策略逻辑：
    1. AI预测支撑位和压力位
    2. 在支撑位附近买入
    3. 在压力位附近卖出
    4. 动态调整网格间距

    适用场景：
    - 横盘震荡行情
    - 区间波动明显的标的
    - 波动率适中的市场
    """

    def __init__(self, config: StrategyConfig):
        """初始化S05网格策略

        Args:
            config: 策略配置（Arena进化出的参数）
        """
        super().__init__(name="S05_Dynamic_Grid", config=config)

        # 策略特有参数
        self.grid_levels: int = 5  # 网格层数
        self.base_grid_spacing: float = 0.02  # 基础网格间距（2%）
        self.volatility_adjustment: bool = True  # 是否根据波动率调整
        self.min_grid_spacing: float = 0.01  # 最小网格间距（1%）
        self.max_grid_spacing: float = 0.05  # 最大网格间距（5%）

        # 网格状态
        self.active_grids: Dict[str, Dict] = {}  # {symbol: grid_config}

        logger.info(
            f"S05_Dynamic_Grid策略初始化 - "
            f"网格层数: {self.grid_levels}, "
            f"基础间距: {self.base_grid_spacing*100:.1f}%"
        )

    async def generate_signals(self, market_data: Dict[str, Any]) -> List[Signal]:
        """生成交易信号

        白皮书依据: Requirement 5.2

        信号生成逻辑：
        1. 识别震荡行情标的
        2. 计算支撑压力位
        3. 判断当前价格位置
        4. 生成买入/卖出信号

        Args:
            market_data: 市场数据

        Returns:
            交易信号列表
        """
        signals: List[Signal] = []

        symbols = market_data.get("symbols", [])
        prices = market_data.get("prices", {})
        indicators = market_data.get("indicators", {})
        ai_predictions = market_data.get("ai_predictions", {})

        for symbol in symbols:
            try:
                signal = await self._analyze_grid_opportunity(
                    symbol, prices.get(symbol, {}), indicators.get(symbol, {}), ai_predictions.get(symbol, {})
                )
                if signal:
                    signals.append(signal)
            except Exception as e:  # pylint: disable=broad-exception-caught
                logger.warning(f"分析{symbol}网格机会时出错: {e}")
                continue

        logger.info(f"S05_Dynamic_Grid生成{len(signals)}个网格信号")
        return signals

    async def _analyze_grid_opportunity(
        self, symbol: str, price_data: Dict[str, Any], indicator_data: Dict[str, Any], ai_prediction: Dict[str, Any]
    ) -> Optional[Signal]:
        """分析网格交易机会

        Args:
            symbol: 标的代码
            price_data: 价格数据
            indicator_data: 技术指标数据
            ai_prediction: AI预测数据

        Returns:
            交易信号或None
        """
        current_price = price_data.get("close", 0)
        volatility = indicator_data.get("volatility_20d", 0.02)

        if current_price <= 0:
            return None

        # 检查是否适合网格交易（震荡行情）
        if not self._is_range_bound(indicator_data):
            return None

        # 获取或创建网格配置
        grid_config = self._get_or_create_grid(symbol, current_price, volatility, ai_prediction)

        # 判断当前价格位置
        action, level, confidence = self._determine_grid_action(current_price, grid_config)

        if action == "hold":
            return None

        reason = (
            f"网格{action}信号, "
            f"层级{level}, "
            f"支撑{grid_config['support']:.2f}, "
            f"压力{grid_config['resistance']:.2f}"
        )

        logger.info(f"S05_Dynamic_Grid网格信号 - {symbol}: {reason}")

        return Signal(
            symbol=symbol, action=action, confidence=confidence, timestamp=datetime.now().isoformat(), reason=reason
        )

    def _is_range_bound(self, indicator_data: Dict[str, Any]) -> bool:
        """判断是否为震荡行情

        Args:
            indicator_data: 技术指标数据

        Returns:
            是否为震荡行情
        """
        # ADX < 25 表示无明显趋势
        adx = indicator_data.get("adx_14", 30)

        # 布林带宽度适中
        bb_width = indicator_data.get("bb_width", 0.1)

        # ATR相对稳定
        atr_ratio = indicator_data.get("atr_ratio", 0.02)

        is_range = adx < 25 and 0.05 < bb_width < 0.15 and atr_ratio < 0.03

        return is_range

    def _get_or_create_grid(
        self, symbol: str, current_price: float, volatility: float, ai_prediction: Dict[str, Any]
    ) -> Dict[str, Any]:
        """获取或创建网格配置

        Args:
            symbol: 标的代码
            current_price: 当前价格
            volatility: 波动率
            ai_prediction: AI预测数据

        Returns:
            网格配置
        """
        if symbol in self.active_grids:
            grid = self.active_grids[symbol]
            # 检查是否需要更新
            if abs(current_price - grid["center"]) / grid["center"] > 0.1:
                # 价格偏离中心超过10%，重新计算
                pass
            else:
                return grid

        # 计算网格间距（根据波动率调整）
        if self.volatility_adjustment:
            grid_spacing = self.base_grid_spacing * (volatility / 0.02)
            grid_spacing = max(self.min_grid_spacing, min(self.max_grid_spacing, grid_spacing))
        else:
            grid_spacing = self.base_grid_spacing

        # 使用AI预测的支撑压力位
        ai_support = ai_prediction.get("support", current_price * 0.95)
        ai_resistance = ai_prediction.get("resistance", current_price * 1.05)

        # 计算网格层级
        buy_levels = []
        sell_levels = []

        for i in range(1, self.grid_levels + 1):
            buy_price = current_price * (1 - grid_spacing * i)
            sell_price = current_price * (1 + grid_spacing * i)
            buy_levels.append(buy_price)
            sell_levels.append(sell_price)

        grid_config = {
            "center": current_price,
            "support": ai_support,
            "resistance": ai_resistance,
            "grid_spacing": grid_spacing,
            "buy_levels": buy_levels,
            "sell_levels": sell_levels,
            "executed_buys": set(),
            "executed_sells": set(),
            "created_at": datetime.now().isoformat(),
        }

        self.active_grids[symbol] = grid_config

        logger.debug(f"创建网格配置 - {symbol}: " f"中心={current_price:.2f}, " f"间距={grid_spacing*100:.2f}%")

        return grid_config

    def _determine_grid_action(self, current_price: float, grid_config: Dict[str, Any]) -> Tuple[str, int, float]:
        """判断网格交易动作

        Args:
            current_price: 当前价格
            grid_config: 网格配置

        Returns:
            (action, level, confidence)
        """
        buy_levels = grid_config["buy_levels"]
        sell_levels = grid_config["sell_levels"]
        executed_buys = grid_config["executed_buys"]
        executed_sells = grid_config["executed_sells"]

        # 检查买入层级
        for i, buy_price in enumerate(buy_levels):
            level = i + 1
            if level not in executed_buys:
                # 价格触及买入层级（允许1%误差）
                if current_price <= buy_price * 1.01:
                    confidence = 0.6 + 0.05 * level  # 越低层级置信度越高
                    confidence = min(0.85, confidence)
                    return "buy", level, confidence

        # 检查卖出层级
        for i, sell_price in enumerate(sell_levels):
            level = i + 1
            if level not in executed_sells:
                # 价格触及卖出层级（允许1%误差）
                if current_price >= sell_price * 0.99:
                    confidence = 0.6 + 0.05 * level
                    confidence = min(0.85, confidence)
                    return "sell", level, confidence

        return "hold", 0, 0.0

    async def calculate_position_sizes(self, signals: List[Signal]) -> List[Position]:
        """计算仓位大小

        白皮书依据: Requirement 5.3

        网格策略特点：
        - 分层建仓
        - 每层仓位相等
        - 总仓位控制

        Args:
            signals: 交易信号列表

        Returns:
            仓位列表
        """
        positions: List[Position] = []

        # 每层仓位 = 总仓位 / 网格层数
        per_level_size = self.max_position / self.grid_levels
        per_level_size = min(per_level_size, self.max_single_stock)

        total_allocated = 0.0

        for signal in signals:
            if signal.action != "buy":
                continue

            # 网格策略每层仓位固定
            base_size = per_level_size * signal.confidence

            if total_allocated + base_size > self.max_position:
                base_size = self.max_position - total_allocated

            if base_size <= 0.005:
                break

            position = Position(
                symbol=signal.symbol,
                size=base_size,
                entry_price=100.0,  # Placeholder price
                current_price=100.0,  # Placeholder price
                pnl_pct=0.0,
                holding_days=0,
                industry="unknown",
            )

            positions.append(position)
            total_allocated += base_size

        logger.info(
            f"S05_Dynamic_Grid仓位计算完成 - " f"标的数: {len(positions)}, " f"总仓位: {total_allocated*100:.2f}%"
        )

        return positions

    def mark_grid_executed(self, symbol: str, action: str, level: int) -> None:
        """标记网格层级已执行

        Args:
            symbol: 标的代码
            action: 动作类型
            level: 层级
        """
        if symbol not in self.active_grids:
            return

        grid = self.active_grids[symbol]

        if action == "buy":
            grid["executed_buys"].add(level)
        elif action == "sell":
            grid["executed_sells"].add(level)

        logger.debug(f"标记网格执行 - {symbol}: {action} 层级{level}")

    def reset_grid(self, symbol: str) -> None:
        """重置网格配置

        Args:
            symbol: 标的代码
        """
        if symbol in self.active_grids:
            del self.active_grids[symbol]
            logger.info(f"重置网格配置 - {symbol}")
