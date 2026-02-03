"""LockBox (锁箱) - 资本基因与诺亚方舟

白皮书依据: 第六章 5.3 资本基因与诺亚方舟

核心功能：
- 自动买入GC001/ETF隔离利润
- 利润物理隔离至安全资产
- 确保系统在极端情况下能够重生
"""

from dataclasses import dataclass, field
from datetime import datetime, time
from enum import Enum
from typing import Any, Dict, List, Optional

from loguru import logger


class SafeAssetType(Enum):
    """安全资产类型"""

    GC001 = "GC001"  # 国债逆回购（1天期）
    GC002 = "GC002"  # 国债逆回购（2天期）
    GC003 = "GC003"  # 国债逆回购（3天期）
    GC007 = "GC007"  # 国债逆回购（7天期）
    MONEY_ETF = "511880"  # 货币ETF（银华日利）
    BOND_ETF = "511010"  # 国债ETF


@dataclass
class LockBoxConfig:
    """LockBox配置

    白皮书依据: 第六章 5.3 资本基因与诺亚方舟
    """

    # 利润锁定比例
    profit_lock_ratio: float = 0.3  # 锁定30%利润

    # 最小锁定金额
    min_lock_amount: float = 10000.0  # 最小1万元

    # 最大锁定比例（占总资产）
    max_lock_ratio: float = 0.5  # 最多锁定50%总资产

    # 首选安全资产
    primary_asset: SafeAssetType = SafeAssetType.GC001

    # 备选安全资产
    fallback_asset: SafeAssetType = SafeAssetType.MONEY_ETF

    # 自动锁定时间（诊疗态）
    auto_lock_time: time = time(15, 30)  # 15:30自动锁定

    # 是否启用自动锁定
    auto_lock_enabled: bool = True


@dataclass
class LockBoxState:
    """LockBox状态"""

    total_locked_amount: float = 0.0  # 已锁定总金额
    locked_assets: Dict[str, float] = field(default_factory=dict)  # 各资产锁定金额
    last_lock_time: Optional[str] = None  # 上次锁定时间
    lock_history: List[Dict[str, Any]] = field(default_factory=list)  # 锁定历史


class LockBox:
    """LockBox (锁箱) - 利润物理隔离系统

    白皮书依据: 第六章 5.3 资本基因与诺亚方舟

    核心功能：
    1. 自动计算可锁定利润
    2. 买入安全资产（GC001/货币ETF）
    3. 物理隔离利润，确保系统重生能力
    4. 记录锁定历史，支持审计

    Attributes:
        config: LockBox配置
        state: LockBox状态
        execution_engine: 执行引擎（用于下单）
    """

    def __init__(self, config: Optional[LockBoxConfig] = None, execution_engine: Optional[Any] = None):
        """初始化LockBox

        Args:
            config: LockBox配置
            execution_engine: 执行引擎
        """
        self.config = config or LockBoxConfig()
        self.state = LockBoxState()
        self.execution_engine = execution_engine

        logger.info(
            f"LockBox初始化 - "
            f"锁定比例: {self.config.profit_lock_ratio*100:.0f}%, "
            f"首选资产: {self.config.primary_asset.value}"
        )

    async def calculate_lockable_profit(self, portfolio_data: Dict[str, Any]) -> float:
        """计算可锁定利润

        白皮书依据: 第六章 5.3 资本基因与诺亚方舟

        Args:
            portfolio_data: 投资组合数据

        Returns:
            可锁定利润金额
        """
        # 获取当日盈亏
        daily_pnl = portfolio_data.get("daily_pnl", 0)

        # 获取总资产
        total_assets = portfolio_data.get("total_assets", 0)

        # 获取已锁定金额
        locked_amount = self.state.total_locked_amount

        # 计算可锁定金额
        if daily_pnl <= 0:
            logger.debug("当日无盈利，无需锁定")
            return 0.0

        # 计算应锁定金额
        target_lock = daily_pnl * self.config.profit_lock_ratio

        # 检查最小锁定金额
        if target_lock < self.config.min_lock_amount:
            logger.debug(f"锁定金额{target_lock:.2f}低于最小阈值{self.config.min_lock_amount:.2f}")
            return 0.0

        # 检查最大锁定比例
        max_lockable = total_assets * self.config.max_lock_ratio - locked_amount
        if max_lockable <= 0:
            logger.warning("已达到最大锁定比例，无法继续锁定")
            return 0.0

        lockable_amount = min(target_lock, max_lockable)

        logger.info(f"可锁定利润计算完成 - " f"当日盈利: {daily_pnl:.2f}, " f"可锁定: {lockable_amount:.2f}")

        return lockable_amount

    async def execute_lock(self, amount: float, asset_type: Optional[SafeAssetType] = None) -> Dict[str, Any]:
        """执行利润锁定

        白皮书依据: 第六章 5.3 资本基因与诺亚方舟

        Args:
            amount: 锁定金额
            asset_type: 安全资产类型（可选，默认使用首选资产）

        Returns:
            执行结果
        """
        if amount <= 0:
            return {"success": False, "message": "锁定金额必须大于0", "amount": 0}

        asset = asset_type or self.config.primary_asset

        logger.info(f"开始执行利润锁定 - 金额: {amount:.2f}, 资产: {asset.value}")

        try:
            # 根据资产类型执行不同的锁定逻辑
            if asset in [SafeAssetType.GC001, SafeAssetType.GC002, SafeAssetType.GC003, SafeAssetType.GC007]:
                result = await self._execute_repo_lock(amount, asset)
            else:
                result = await self._execute_etf_lock(amount, asset)

            if result["success"]:
                # 更新状态
                self._update_state(amount, asset, result)
                logger.info(f"利润锁定成功 - {asset.value}: {amount:.2f}")
            else:
                logger.warning(f"利润锁定失败 - {result.get('message', '未知错误')}")

            return result

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.error(f"利润锁定异常: {e}")

            # 尝试使用备选资产
            if asset != self.config.fallback_asset:
                logger.info(f"尝试使用备选资产: {self.config.fallback_asset.value}")
                return await self.execute_lock(amount, self.config.fallback_asset)

            return {"success": False, "message": str(e), "amount": 0}

    async def _execute_repo_lock(self, amount: float, asset: SafeAssetType) -> Dict[str, Any]:
        """执行国债逆回购锁定

        Args:
            amount: 锁定金额
            asset: 逆回购类型

        Returns:
            执行结果
        """
        # 国债逆回购最小单位为1000元
        repo_units = int(amount / 1000)
        actual_amount = repo_units * 1000

        if repo_units <= 0:
            return {"success": False, "message": "金额不足1000元，无法购买逆回购", "amount": 0}

        # 检查交易时间
        if not self._is_repo_trading_time():
            return {"success": False, "message": "当前非逆回购交易时间", "amount": 0}

        # 执行下单
        if self.execution_engine:  # pylint: disable=no-else-return
            order_result = await self.execution_engine.place_order(
                symbol=asset.value,
                action="sell",  # 逆回购是卖出操作
                quantity=repo_units,
                price=None,  # 市价
                order_type="market",
            )

            return {
                "success": order_result.get("success", False),
                "message": order_result.get("message", ""),
                "amount": actual_amount,
                "order_id": order_result.get("order_id"),
                "asset": asset.value,
            }
        else:
            # 模拟执行
            logger.info(f"[模拟] 逆回购锁定 - {asset.value}: {actual_amount:.2f}")
            return {
                "success": True,
                "message": "模拟执行成功",
                "amount": actual_amount,
                "order_id": f'SIM_{datetime.now().strftime("%Y%m%d%H%M%S")}',
                "asset": asset.value,
            }

    async def _execute_etf_lock(self, amount: float, asset: SafeAssetType) -> Dict[str, Any]:
        """执行ETF锁定

        Args:
            amount: 锁定金额
            asset: ETF类型

        Returns:
            执行结果
        """
        # 获取ETF当前价格
        etf_price = await self._get_etf_price(asset.value)

        if etf_price <= 0:
            return {"success": False, "message": "无法获取ETF价格", "amount": 0}

        # 计算可买数量（ETF最小单位100股）
        shares = int(amount / etf_price / 100) * 100
        actual_amount = shares * etf_price

        if shares < 100:
            return {"success": False, "message": "金额不足购买100股ETF", "amount": 0}

        # 执行下单
        if self.execution_engine:  # pylint: disable=no-else-return
            order_result = await self.execution_engine.place_order(
                symbol=asset.value, action="buy", quantity=shares, price=None, order_type="market"  # 市价
            )

            return {
                "success": order_result.get("success", False),
                "message": order_result.get("message", ""),
                "amount": actual_amount,
                "order_id": order_result.get("order_id"),
                "asset": asset.value,
                "shares": shares,
            }
        else:
            # 模拟执行
            logger.info(f"[模拟] ETF锁定 - {asset.value}: {shares}股, {actual_amount:.2f}元")
            return {
                "success": True,
                "message": "模拟执行成功",
                "amount": actual_amount,
                "order_id": f'SIM_{datetime.now().strftime("%Y%m%d%H%M%S")}',
                "asset": asset.value,
                "shares": shares,
            }

    async def _get_etf_price(self, symbol: str) -> float:
        """获取ETF当前价格

        Args:
            symbol: ETF代码

        Returns:
            当前价格
        """
        # 这里应该从数据源获取实时价格
        # 简化实现，返回模拟价格
        price_map = {
            "511880": 100.0,  # 银华日利
            "511010": 100.0,  # 国债ETF
        }
        return price_map.get(symbol, 100.0)

    def _is_repo_trading_time(self) -> bool:
        """检查是否为逆回购交易时间

        Returns:
            是否在交易时间内
        """
        now = datetime.now().time()

        # 上午交易时间: 9:30-11:30
        morning_start = time(9, 30)
        morning_end = time(11, 30)

        # 下午交易时间: 13:00-15:30
        afternoon_start = time(13, 0)
        afternoon_end = time(15, 30)

        return morning_start <= now <= morning_end or afternoon_start <= now <= afternoon_end

    def _update_state(self, amount: float, asset: SafeAssetType, result: Dict[str, Any]) -> None:
        """更新LockBox状态

        Args:
            amount: 锁定金额
            asset: 资产类型
            result: 执行结果
        """
        # 更新总锁定金额
        self.state.total_locked_amount += amount

        # 更新各资产锁定金额
        asset_key = asset.value
        if asset_key in self.state.locked_assets:
            self.state.locked_assets[asset_key] += amount
        else:
            self.state.locked_assets[asset_key] = amount

        # 更新锁定时间
        self.state.last_lock_time = datetime.now().isoformat()

        # 记录历史
        self.state.lock_history.append(
            {
                "timestamp": self.state.last_lock_time,
                "amount": amount,
                "asset": asset_key,
                "order_id": result.get("order_id"),
                "total_locked": self.state.total_locked_amount,
            }
        )

    async def auto_lock_check(self, portfolio_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """自动锁定检查（在诊疗态调用）

        白皮书依据: 第一章 1.3 State 3: 诊疗态

        Args:
            portfolio_data: 投资组合数据

        Returns:
            锁定结果或None
        """
        if not self.config.auto_lock_enabled:
            return None

        # 检查是否到达自动锁定时间
        now = datetime.now().time()
        if now < self.config.auto_lock_time:
            return None

        # 计算可锁定金额
        lockable = await self.calculate_lockable_profit(portfolio_data)

        if lockable <= 0:
            return None

        # 执行锁定
        result = await self.execute_lock(lockable)

        return result

    def get_state(self) -> Dict[str, Any]:
        """获取LockBox状态

        Returns:
            状态字典
        """
        return {
            "total_locked_amount": self.state.total_locked_amount,
            "locked_assets": self.state.locked_assets.copy(),
            "last_lock_time": self.state.last_lock_time,
            "lock_count": len(self.state.lock_history),
            "config": {
                "profit_lock_ratio": self.config.profit_lock_ratio,
                "min_lock_amount": self.config.min_lock_amount,
                "max_lock_ratio": self.config.max_lock_ratio,
                "primary_asset": self.config.primary_asset.value,
                "auto_lock_enabled": self.config.auto_lock_enabled,
            },
        }

    def get_lock_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """获取锁定历史

        Args:
            limit: 返回记录数量限制

        Returns:
            锁定历史列表
        """
        return self.state.lock_history[-limit:]

    def reset_state(self) -> None:
        """重置LockBox状态（仅用于测试）"""
        self.state = LockBoxState()
        logger.warning("LockBox状态已重置")
