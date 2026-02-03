"""MIA系统界面模块

白皮书依据: 附录A-D

包含:
- 全息指挥台 (The Trinity HUD) - 12个Dashboard
- 权限与隐私控制体系 (Access & Privacy System)
- UI/UX设计规范 (The NiuNiu Aesthetic)
- UI/UX Pro Max集成方案
"""

# 附录B: 权限与隐私控制
from src.interface.access_control import (
    AccessControlledDashboard,
    AccessControlManager,
    AccessPolicy,
    PageAccess,
    PhysicalIsolationMixin,
    TradingPermission,
    UserRole,
    UserSession,
    require_admin,
    require_page_access,
)
from src.interface.auditor_dashboard import AuditorDashboard

# P0 核心Dashboard
from src.interface.cockpit_dashboard import CockpitDashboard
from src.interface.derivatives_lab_dashboard import DerivativesLabDashboard

# P2 高级Dashboard
from src.interface.evolution_dashboard import EvolutionDashboard
from src.interface.library_dashboard import LibraryDashboard
from src.interface.multi_account_dashboard import MultiAccountDashboard
from src.interface.portfolio_dashboard import PortfolioDashboard

# P1 重要Dashboard
from src.interface.radar_dashboard import RadarDashboard
from src.interface.scanner_dashboard import ScannerDashboard
from src.interface.system_dashboard import SystemDashboard
from src.interface.tactical_dashboard import TacticalDashboard

# 附录D: UI/UX Pro Max
from src.interface.ui_pro_max import (
    ChartConfig,
    ChartType,
    ColorPalette,
    FontPairing,
    UIProMaxManager,
    UIStyle,
    apply_ui_pro_max,
    get_ui_pro_max,
)

# 附录C: UI/UX设计规范
from src.interface.ui_theme import (
    ColorScheme,
    FontConfig,
    NiuNiuTheme,
    SpacingConfig,
    ThemeColors,
    ThemeMode,
    apply_theme,
    get_theme,
    set_theme,
)
from src.interface.watchlist_dashboard import WatchlistDashboard

__all__ = [
    # P0 核心Dashboard
    "CockpitDashboard",
    "ScannerDashboard",
    "PortfolioDashboard",
    # P1 重要Dashboard
    "RadarDashboard",
    "TacticalDashboard",
    "WatchlistDashboard",
    "SystemDashboard",
    "MultiAccountDashboard",
    # P2 高级Dashboard
    "EvolutionDashboard",
    "LibraryDashboard",
    "DerivativesLabDashboard",
    "AuditorDashboard",
    # 附录B: 权限与隐私控制
    "UserRole",
    "PageAccess",
    "TradingPermission",
    "UserSession",
    "AccessPolicy",
    "AccessControlManager",
    "PhysicalIsolationMixin",
    "AccessControlledDashboard",
    "require_admin",
    "require_page_access",
    # 附录C: UI/UX设计规范
    "ThemeMode",
    "ColorScheme",
    "ThemeColors",
    "FontConfig",
    "SpacingConfig",
    "NiuNiuTheme",
    "get_theme",
    "set_theme",
    "apply_theme",
    # 附录D: UI/UX Pro Max
    "UIStyle",
    "ChartType",
    "ColorPalette",
    "FontPairing",
    "ChartConfig",
    "UIProMaxManager",
    "get_ui_pro_max",
    "apply_ui_pro_max",
]
