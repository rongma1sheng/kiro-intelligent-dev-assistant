"""权限与隐私控制体系 (Access & Privacy System)

白皮书依据: 附录B 权限与隐私控制体系

核心功能:
- Guest/Admin角色区分
- 物理屏蔽机制 (Guest用户跳过敏感数据加载)
- 按钮移除逻辑 (Guest用户移除买入/卖出按钮)
- 页面访问控制
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, IntEnum
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Set

from loguru import logger


class UserRole(IntEnum):
    """用户角色枚举

    白皮书依据: 附录B 权限分级架构

    Attributes:
        GUEST: 市场扫描仪用户，权限等级0
        ADMIN: 系统拥有者，权限等级1
    """

    GUEST = 0
    ADMIN = 1


class PageAccess(Enum):
    """页面访问权限枚举

    白皮书依据: 附录B 可见页面 (Page Access)
    """

    SCANNER = "scanner"  # 全息扫描仪 - Guest可见
    COCKPIT = "cockpit"  # 驾驶舱 - Admin Only
    PORTFOLIO = "portfolio"  # 资产与归因 - Admin Only
    RADAR = "radar"  # 狩猎雷达 - Admin Only
    TACTICAL = "tactical"  # 战术复盘 - Admin Only
    WATCHLIST = "watchlist"  # 重点关注 - Admin Only
    SYSTEM = "system"  # 系统中枢 - Admin Only
    MULTI_ACCOUNT = "multi_account"  # 多账户管理 - Admin Only
    EVOLUTION = "evolution"  # 进化工厂 - Admin Only
    LIBRARY = "library"  # 藏经阁 - Admin Only
    DERIVATIVES = "derivatives"  # 衍生品实验室 - Admin Only
    AUDITOR = "auditor"  # 魔鬼审计 - Admin Only


class TradingPermission(Enum):
    """交易权限枚举

    白皮书依据: 附录B 交易权限
    """

    DISABLED = "disabled"  # 物理禁用
    UNLIMITED = "unlimited"  # 无限


@dataclass
class UserSession:
    """用户会话数据模型

    白皮书依据: 附录B 权限与隐私控制体系

    Attributes:
        user_id: 用户ID
        role: 用户角色
        login_time: 登录时间
        last_active: 最后活跃时间
        ip_address: IP地址
        device_info: 设备信息
        session_token: 会话令牌
    """

    user_id: str
    role: UserRole
    login_time: datetime = field(default_factory=datetime.now)
    last_active: datetime = field(default_factory=datetime.now)
    ip_address: str = ""
    device_info: str = ""
    session_token: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "user_id": self.user_id,
            "role": self.role.name,
            "role_level": self.role.value,
            "login_time": self.login_time.isoformat(),
            "last_active": self.last_active.isoformat(),
            "ip_address": self.ip_address,
            "device_info": self.device_info,
            "session_token": self.session_token,
        }


@dataclass
class AccessPolicy:
    """访问策略数据模型

    白皮书依据: 附录B 权限分级架构

    Attributes:
        role: 用户角色
        allowed_pages: 允许访问的页面
        trading_permission: 交易权限
        can_view_sensitive_data: 是否可查看敏感数据
        can_execute_trades: 是否可执行交易
        can_modify_settings: 是否可修改设置
    """

    role: UserRole
    allowed_pages: Set[PageAccess]
    trading_permission: TradingPermission
    can_view_sensitive_data: bool
    can_execute_trades: bool
    can_modify_settings: bool


class AccessControlManager:
    """权限控制管理器

    白皮书依据: 附录B 权限与隐私控制体系

    提供完整的权限控制功能:
    - 角色权限验证
    - 页面访问控制
    - 敏感数据屏蔽
    - 交易按钮移除

    Attributes:
        current_session: 当前用户会话
        policies: 角色策略映射
    """

    # Guest用户可见页面 (白皮书定义: 仅全息扫描仪)
    GUEST_ALLOWED_PAGES: Set[PageAccess] = {PageAccess.SCANNER}

    # Admin用户可见页面 (白皮书定义: 全部可见)
    ADMIN_ALLOWED_PAGES: Set[PageAccess] = set(PageAccess)

    # 敏感数据字段列表 (需要对Guest屏蔽)
    SENSITIVE_FIELDS: Set[str] = {
        "total_assets",
        "available_cash",
        "positions",
        "trade_history",
        "pnl_details",
        "strategy_params",
        "api_keys",
        "account_info",
        "order_history",
        "risk_metrics",
    }

    def __init__(self, default_role: UserRole = UserRole.GUEST):
        """初始化权限控制管理器

        Args:
            default_role: 默认用户角色
        """
        self.current_session: Optional[UserSession] = None
        self.policies: Dict[UserRole, AccessPolicy] = self._init_policies()
        self._default_role = default_role

        logger.info(f"AccessControlManager initialized, default_role={default_role.name}")

    def _init_policies(self) -> Dict[UserRole, AccessPolicy]:
        """初始化角色策略

        白皮书依据: 附录B 权限分级架构

        Returns:
            角色策略映射
        """
        return {
            UserRole.GUEST: AccessPolicy(
                role=UserRole.GUEST,
                allowed_pages=self.GUEST_ALLOWED_PAGES,
                trading_permission=TradingPermission.DISABLED,
                can_view_sensitive_data=False,
                can_execute_trades=False,
                can_modify_settings=False,
            ),
            UserRole.ADMIN: AccessPolicy(
                role=UserRole.ADMIN,
                allowed_pages=self.ADMIN_ALLOWED_PAGES,
                trading_permission=TradingPermission.UNLIMITED,
                can_view_sensitive_data=True,
                can_execute_trades=True,
                can_modify_settings=True,
            ),
        }

    def create_session(self, user_id: str, role: UserRole, ip_address: str = "", device_info: str = "") -> UserSession:
        """创建用户会话

        Args:
            user_id: 用户ID
            role: 用户角色
            ip_address: IP地址
            device_info: 设备信息

        Returns:
            用户会话
        """
        import secrets  # pylint: disable=import-outside-toplevel

        session = UserSession(
            user_id=user_id,
            role=role,
            ip_address=ip_address,
            device_info=device_info,
            session_token=secrets.token_urlsafe(32),
        )

        self.current_session = session

        logger.info(f"Session created: user_id={user_id}, role={role.name}, " f"ip={ip_address}")

        return session

    def get_current_role(self) -> UserRole:
        """获取当前用户角色

        Returns:
            当前用户角色，如果没有会话则返回默认角色
        """
        if self.current_session is None:
            return self._default_role
        return self.current_session.role

    def get_current_policy(self) -> AccessPolicy:
        """获取当前用户策略

        Returns:
            当前用户的访问策略
        """
        role = self.get_current_role()
        return self.policies[role]

    def is_admin(self) -> bool:
        """检查当前用户是否为Admin

        Returns:
            是否为Admin用户
        """
        return self.get_current_role() == UserRole.ADMIN

    def is_guest(self) -> bool:
        """检查当前用户是否为Guest

        Returns:
            是否为Guest用户
        """
        return self.get_current_role() == UserRole.GUEST

    def can_access_page(self, page: PageAccess) -> bool:
        """检查是否可以访问指定页面

        白皮书依据: 附录B 可见页面 (Page Access)

        Args:
            page: 页面类型

        Returns:
            是否可以访问
        """
        policy = self.get_current_policy()
        can_access = page in policy.allowed_pages

        if not can_access:
            logger.warning(f"Access denied: role={policy.role.name}, page={page.value}")

        return can_access

    def can_execute_trade(self) -> bool:
        """检查是否可以执行交易

        白皮书依据: 附录B 交易权限

        Returns:
            是否可以执行交易
        """
        policy = self.get_current_policy()
        return policy.can_execute_trades

    def can_view_sensitive_data(self) -> bool:
        """检查是否可以查看敏感数据

        白皮书依据: 附录B 隔离机制 - 物理屏蔽

        Returns:
            是否可以查看敏感数据
        """
        policy = self.get_current_policy()
        return policy.can_view_sensitive_data

    def filter_sensitive_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """过滤敏感数据

        白皮书依据: 附录B 隔离机制 - 物理屏蔽
        Guest用户在访问时，后端代码直接跳过敏感数据的加载。

        Args:
            data: 原始数据

        Returns:
            过滤后的数据 (Guest用户敏感字段被移除)
        """
        if self.can_view_sensitive_data():
            return data

        # Guest用户：移除敏感字段
        filtered = {}
        for key, value in data.items():
            if key not in self.SENSITIVE_FIELDS:
                filtered[key] = value
            else:
                logger.debug(f"Sensitive field filtered: {key}")

        return filtered

    def should_show_trade_buttons(self) -> bool:
        """检查是否应该显示交易按钮

        白皮书依据: 附录B 隔离机制 - 按钮移除
        扫描仪页面中的"买入/卖出"按钮对Guest彻底移除。

        Returns:
            是否显示交易按钮
        """
        return self.can_execute_trade()

    def get_allowed_pages(self) -> List[PageAccess]:
        """获取当前用户允许访问的页面列表

        Returns:
            允许访问的页面列表
        """
        policy = self.get_current_policy()
        return list(policy.allowed_pages)

    def get_navigation_items(self) -> List[Dict[str, Any]]:
        """获取导航菜单项

        根据用户角色返回可见的导航项。

        Returns:
            导航菜单项列表
        """
        page_info = {
            PageAccess.SCANNER: {"name": "全息扫描仪", "icon": "🔍", "order": 1},
            PageAccess.COCKPIT: {"name": "驾驶舱", "icon": "🎛️", "order": 2},
            PageAccess.PORTFOLIO: {"name": "资产与归因", "icon": "💼", "order": 3},
            PageAccess.RADAR: {"name": "狩猎雷达", "icon": "📡", "order": 4},
            PageAccess.TACTICAL: {"name": "战术复盘", "icon": "📊", "order": 5},
            PageAccess.WATCHLIST: {"name": "重点关注", "icon": "⭐", "order": 6},
            PageAccess.SYSTEM: {"name": "系统中枢", "icon": "⚙️", "order": 7},
            PageAccess.MULTI_ACCOUNT: {"name": "多账户管理", "icon": "👥", "order": 8},
            PageAccess.EVOLUTION: {"name": "进化工厂", "icon": "🧬", "order": 9},
            PageAccess.LIBRARY: {"name": "藏经阁", "icon": "📚", "order": 10},
            PageAccess.DERIVATIVES: {"name": "衍生品实验室", "icon": "🔬", "order": 11},
            PageAccess.AUDITOR: {"name": "魔鬼审计", "icon": "👹", "order": 12},
        }

        allowed_pages = self.get_allowed_pages()
        nav_items = []

        for page in allowed_pages:
            info = page_info.get(page, {})
            nav_items.append(
                {
                    "page": page.value,
                    "name": info.get("name", page.value),
                    "icon": info.get("icon", "📄"),
                    "order": info.get("order", 99),
                }
            )

        # 按order排序
        nav_items.sort(key=lambda x: x["order"])

        return nav_items

    def update_last_active(self) -> None:
        """更新最后活跃时间"""
        if self.current_session:
            self.current_session.last_active = datetime.now()

    def logout(self) -> None:
        """登出当前会话"""
        if self.current_session:
            logger.info(
                f"Session ended: user_id={self.current_session.user_id}, " f"role={self.current_session.role.name}"
            )
            self.current_session = None


def require_admin(func: Callable) -> Callable:
    """Admin权限装饰器

    白皮书依据: 附录B 权限分级架构

    用于装饰需要Admin权限的函数。

    Args:
        func: 被装饰的函数

    Returns:
        装饰后的函数

    Raises:
        PermissionError: 当用户不是Admin时
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        # 尝试从参数中获取access_control
        access_control = kwargs.get("access_control")

        if access_control is None:
            # 尝试从第一个参数获取（如果是类方法）
            if args and hasattr(args[0], "access_control"):
                access_control = args[0].access_control

        if access_control is None:
            raise PermissionError("AccessControlManager not found")

        if not access_control.is_admin():
            raise PermissionError(
                f"Admin permission required. Current role: " f"{access_control.get_current_role().name}"
            )

        return func(*args, **kwargs)

    return wrapper


def require_page_access(page: PageAccess) -> Callable:
    """页面访问权限装饰器

    白皮书依据: 附录B 可见页面 (Page Access)

    用于装饰需要特定页面访问权限的函数。

    Args:
        page: 需要访问的页面

    Returns:
        装饰器函数
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 尝试从参数中获取access_control
            access_control = kwargs.get("access_control")

            if access_control is None:
                # 尝试从第一个参数获取（如果是类方法）
                if args and hasattr(args[0], "access_control"):
                    access_control = args[0].access_control

            if access_control is None:
                raise PermissionError("AccessControlManager not found")

            if not access_control.can_access_page(page):
                raise PermissionError(
                    f"Access to {page.value} denied. Current role: " f"{access_control.get_current_role().name}"
                )

            return func(*args, **kwargs)

        return wrapper

    return decorator


class PhysicalIsolationMixin:
    """物理隔离混入类

    白皮书依据: 附录B 隔离机制

    提供物理屏蔽和按钮移除功能的混入类。
    可以被Dashboard类继承使用。
    """

    access_control: AccessControlManager

    def load_data_with_isolation(self, data_loader: Callable[[], Dict[str, Any]]) -> Dict[str, Any]:
        """带物理隔离的数据加载

        白皮书依据: 附录B 隔离机制 - 物理屏蔽
        Guest用户在访问时，后端代码直接跳过敏感数据的加载。

        Args:
            data_loader: 数据加载函数

        Returns:
            过滤后的数据
        """
        if not hasattr(self, "access_control"):
            logger.warning("access_control not found, returning full data")
            return data_loader()

        # 如果是Guest用户，跳过敏感数据加载
        if self.access_control.is_guest():
            logger.info("Guest user detected, skipping sensitive data loading")
            # 只加载非敏感数据
            full_data = data_loader()
            return self.access_control.filter_sensitive_data(full_data)

        # Admin用户加载全部数据
        return data_loader()

    def render_trade_buttons(
        self, symbol: str, on_buy: Optional[Callable] = None, on_sell: Optional[Callable] = None
    ) -> bool:
        """渲染交易按钮（带权限控制）

        白皮书依据: 附录B 隔离机制 - 按钮移除
        扫描仪页面中的"买入/卖出"按钮对Guest彻底移除。

        Args:
            symbol: 股票代码
            on_buy: 买入回调函数
            on_sell: 卖出回调函数

        Returns:
            是否渲染了按钮
        """
        if not hasattr(self, "access_control"):
            logger.warning("access_control not found, buttons not rendered")
            return False

        # Guest用户：彻底移除按钮
        if not self.access_control.should_show_trade_buttons():
            logger.debug(f"Trade buttons removed for Guest user: {symbol}")
            return False

        # Admin用户：渲染按钮
        try:
            import streamlit as st  # pylint: disable=import-outside-toplevel

            col1, col2 = st.columns(2)

            with col1:
                if st.button("🟢 买入", key=f"buy_{symbol}", type="primary", use_container_width=True):
                    if on_buy:
                        on_buy(symbol)
                    st.success(f"买入指令已发送: {symbol}")

            with col2:
                if st.button("🔴 卖出", key=f"sell_{symbol}", type="secondary", use_container_width=True):
                    if on_sell:
                        on_sell(symbol)
                    st.warning(f"卖出指令已发送: {symbol}")

            return True

        except ImportError:
            logger.warning("Streamlit not available")
            return False


class AccessControlledDashboard(PhysicalIsolationMixin):
    """带权限控制的Dashboard基类

    白皮书依据: 附录B 权限与隐私控制体系

    所有Dashboard都应该继承此类以获得权限控制功能。

    Attributes:
        access_control: 权限控制管理器
        page_type: 页面类型
    """

    def __init__(
        self, access_control: Optional[AccessControlManager] = None, page_type: PageAccess = PageAccess.SCANNER
    ):
        """初始化带权限控制的Dashboard

        Args:
            access_control: 权限控制管理器
            page_type: 页面类型
        """
        self.access_control = access_control or AccessControlManager()
        self.page_type = page_type

        logger.info(
            f"AccessControlledDashboard initialized: page={page_type.value}, "
            f"role={self.access_control.get_current_role().name}"
        )

    def check_access(self) -> bool:
        """检查页面访问权限

        Returns:
            是否有访问权限
        """
        return self.access_control.can_access_page(self.page_type)

    def render_access_denied(self) -> None:
        """渲染访问拒绝页面"""
        try:
            import streamlit as st  # pylint: disable=import-outside-toplevel

            st.error("🚫 访问被拒绝")
            st.warning(f"您当前的角色 ({self.access_control.get_current_role().name}) " f"无权访问此页面。")
            st.info("请联系管理员获取访问权限。")

        except ImportError:
            logger.error("Access denied and Streamlit not available")

    def render_with_access_check(self, render_func: Callable) -> None:
        """带访问检查的渲染

        Args:
            render_func: 渲染函数
        """
        if self.check_access():
            render_func()
        else:
            self.render_access_denied()

    def get_role_badge(self) -> str:
        """获取角色徽章

        Returns:
            角色徽章HTML
        """
        role = self.access_control.get_current_role()

        if role == UserRole.ADMIN:  # pylint: disable=no-else-return
            return "🔑 Admin"
        else:
            return "👤 Guest"
