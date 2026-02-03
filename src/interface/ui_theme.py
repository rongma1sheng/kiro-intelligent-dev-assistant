"""UI/UX设计规范 (The NiuNiu Aesthetic)

白皮书依据: 附录C UI/UX设计规范

核心功能:
- 复刻富途牛牛/Webull专业交易终端体验
- Obsidian Dark (黑曜石色) + Futu Blue (牛牛蓝)
- CSS深度定制
- Roboto Mono字体集成
- 紧凑型Metric卡片样式
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional

from loguru import logger


class ThemeMode(Enum):
    """主题模式枚举

    白皮书依据: 附录C UI/UX设计规范
    """

    LIGHT = "light"
    DARK = "dark"


class ColorScheme(Enum):
    """配色方案枚举

    白皮书依据: 附录C 核心配色方案
    """

    NIUNIU = "niuniu"  # 牛牛风格 (默认)
    FINTECH = "fintech"  # 金融科技风格
    PROFESSIONAL = "professional"  # 专业深色


@dataclass
class ThemeColors:
    """主题颜色配置

    白皮书依据: 附录C 核心配色方案 (Color Palette)

    Attributes:
        bg_primary: 背景色 (#191B24 深空灰)
        bg_card: 卡片背景 (#222631 模块灰)
        rise: 涨/利好 (#F44336 A股红)
        fall: 跌/利空 (#00C853 A股绿)
        primary: 主强调色 (#308FFF 牛牛蓝)
        text_primary: 文字主色 (#E1E3E8 亮灰白)
        text_secondary: 文字次色
        warning: 警告色
        neutral: 中性色
        border: 边框色
        shadow: 阴影色
    """

    bg_primary: str = "#191B24"
    bg_card: str = "#222631"
    rise: str = "#F44336"
    fall: str = "#00C853"
    primary: str = "#308FFF"
    text_primary: str = "#E1E3E8"
    text_secondary: str = "#8B8E98"
    warning: str = "#FFC107"
    neutral: str = "#8C8C8C"
    border: str = "#2A2D3A"
    shadow: str = "rgba(0, 0, 0, 0.3)"

    def to_dict(self) -> Dict[str, str]:
        """转换为字典"""
        return {
            "bg_primary": self.bg_primary,
            "bg_card": self.bg_card,
            "rise": self.rise,
            "fall": self.fall,
            "primary": self.primary,
            "text_primary": self.text_primary,
            "text_secondary": self.text_secondary,
            "warning": self.warning,
            "neutral": self.neutral,
            "border": self.border,
            "shadow": self.shadow,
        }


@dataclass
class FontConfig:
    """字体配置

    白皮书依据: 附录C CSS深度定制 - 无衬线字体 (Roboto Mono)

    Attributes:
        mono: 等宽字体 (数字和代码)
        sans: 无衬线字体 (标题和正文)
        size_xs: 超小字号
        size_sm: 小字号
        size_md: 中等字号
        size_lg: 大字号
        size_xl: 超大字号
        size_2xl: 特大字号
        weight_normal: 正常字重
        weight_medium: 中等字重
        weight_bold: 粗体字重
    """

    mono: str = "'Roboto Mono', 'Courier New', monospace"
    sans: str = "'Inter', -apple-system, BlinkMacSystemFont, sans-serif"
    size_xs: str = "10px"
    size_sm: str = "12px"
    size_md: str = "14px"
    size_lg: str = "16px"
    size_xl: str = "20px"
    size_2xl: str = "24px"
    weight_normal: int = 400
    weight_medium: int = 500
    weight_bold: int = 700

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "mono": self.mono,
            "sans": self.sans,
            "size_xs": self.size_xs,
            "size_sm": self.size_sm,
            "size_md": self.size_md,
            "size_lg": self.size_lg,
            "size_xl": self.size_xl,
            "size_2xl": self.size_2xl,
            "weight_normal": self.weight_normal,
            "weight_medium": self.weight_medium,
            "weight_bold": self.weight_bold,
        }


@dataclass
class SpacingConfig:
    """间距配置

    白皮书依据: 附录C CSS深度定制 - 紧凑型Metric卡片

    Attributes:
        xs: 超小间距
        sm: 小间距
        md: 中等间距
        lg: 大间距
        xl: 超大间距
        card_padding: 卡片内边距
        card_margin: 卡片外边距
        card_radius: 卡片圆角
    """

    xs: str = "4px"
    sm: str = "8px"
    md: str = "12px"
    lg: str = "16px"
    xl: str = "24px"
    card_padding: str = "12px"
    card_margin: str = "8px"
    card_radius: str = "8px"

    def to_dict(self) -> Dict[str, str]:
        """转换为字典"""
        return {
            "xs": self.xs,
            "sm": self.sm,
            "md": self.md,
            "lg": self.lg,
            "xl": self.xl,
            "card_padding": self.card_padding,
            "card_margin": self.card_margin,
            "card_radius": self.card_radius,
        }


class NiuNiuTheme:
    """牛牛主题管理器

    白皮书依据: 附录C UI/UX设计规范 (The NiuNiu Aesthetic)

    设计目标: 复刻富途牛牛/Webull的专业交易终端体验
    核心色调: Obsidian Dark (黑曜石色) + Futu Blue (牛牛蓝)

    Attributes:
        mode: 主题模式 (light/dark)
        scheme: 配色方案
        colors: 颜色配置
        fonts: 字体配置
        spacing: 间距配置
    """

    # 预定义配色方案
    COLOR_SCHEMES: Dict[ColorScheme, ThemeColors] = {
        ColorScheme.NIUNIU: ThemeColors(
            bg_primary="#191B24",
            bg_card="#222631",
            rise="#F44336",
            fall="#00C853",
            primary="#308FFF",
            text_primary="#E1E3E8",
            text_secondary="#8B8E98",
            warning="#FFC107",
            neutral="#8C8C8C",
            border="#2A2D3A",
            shadow="rgba(0, 0, 0, 0.3)",
        ),
        ColorScheme.FINTECH: ThemeColors(
            bg_primary="#05478a",
            bg_card="#ffffff",
            rise="#F44336",
            fall="#00C853",
            primary="#048cfc",
            text_primary="#333333",
            text_secondary="#657e98",
            warning="#FFC107",
            neutral="#657e98",
            border="#b4bdc6",
            shadow="rgba(0, 0, 0, 0.1)",
        ),
        ColorScheme.PROFESSIONAL: ThemeColors(
            bg_primary="#0D1117",
            bg_card="#161B22",
            rise="#FF4D4F",
            fall="#52C41A",
            primary="#1890FF",
            text_primary="#C9D1D9",
            text_secondary="#8B949E",
            warning="#FA8C16",
            neutral="#8C8C8C",
            border="#30363D",
            shadow="rgba(0, 0, 0, 0.4)",
        ),
    }

    def __init__(self, mode: ThemeMode = ThemeMode.DARK, scheme: ColorScheme = ColorScheme.NIUNIU):
        """初始化牛牛主题

        Args:
            mode: 主题模式
            scheme: 配色方案
        """
        self.mode = mode
        self.scheme = scheme
        self.colors = self.COLOR_SCHEMES.get(scheme, self.COLOR_SCHEMES[ColorScheme.NIUNIU])
        self.fonts = FontConfig()
        self.spacing = SpacingConfig()

        logger.info(f"NiuNiuTheme initialized: mode={mode.value}, scheme={scheme.value}")

    def get_google_fonts_import(self) -> str:
        """获取Google Fonts导入CSS

        白皮书依据: 附录C CSS深度定制 - 无衬线字体 (Roboto Mono)

        Returns:
            Google Fonts导入CSS
        """
        return """
@import url('https://fonts.googleapis.com/css2?family=Roboto+Mono:wght@400;500;700&family=Inter:wght@400;500;600;700&display=swap');
"""

    def get_css_variables(self) -> str:
        """获取CSS变量定义

        白皮书依据: 附录C 核心配色方案

        Returns:
            CSS变量定义
        """
        return f"""
:root {{
    /* 颜色变量 */
    --bg-primary: {self.colors.bg_primary};
    --bg-card: {self.colors.bg_card};
    --color-rise: {self.colors.rise};
    --color-fall: {self.colors.fall};
    --color-primary: {self.colors.primary};
    --text-primary: {self.colors.text_primary};
    --text-secondary: {self.colors.text_secondary};
    --color-warning: {self.colors.warning};
    --color-neutral: {self.colors.neutral};
    --border-color: {self.colors.border};
    --shadow-color: {self.colors.shadow};
    
    /* 字体变量 */
    --font-mono: {self.fonts.mono};
    --font-sans: {self.fonts.sans};
    --font-size-xs: {self.fonts.size_xs};
    --font-size-sm: {self.fonts.size_sm};
    --font-size-md: {self.fonts.size_md};
    --font-size-lg: {self.fonts.size_lg};
    --font-size-xl: {self.fonts.size_xl};
    --font-size-2xl: {self.fonts.size_2xl};
    
    /* 间距变量 */
    --spacing-xs: {self.spacing.xs};
    --spacing-sm: {self.spacing.sm};
    --spacing-md: {self.spacing.md};
    --spacing-lg: {self.spacing.lg};
    --spacing-xl: {self.spacing.xl};
    --card-padding: {self.spacing.card_padding};
    --card-margin: {self.spacing.card_margin};
    --card-radius: {self.spacing.card_radius};
}}
"""

    def get_base_styles(self) -> str:
        """获取基础样式

        白皮书依据: 附录C CSS深度定制

        Returns:
            基础CSS样式
        """
        return """  # pylint: disable=w1309
/* 全局样式 */
* {{
    font-family: var(--font-sans);
    box-sizing: border-box;
}}

body {{
    background-color: var(--bg-primary);
    color: var(--text-primary);
    margin: 0;
    padding: 0;
}}

/* 数字和价格使用等宽字体 */
.font-mono, .metric-value, .price, .pnl, .number {{
    font-family: var(--font-mono);
    font-variant-numeric: tabular-nums;
}}

/* 涨跌颜色 */
.rise, .positive {{
    color: var(--color-rise) !important;
}}

.fall, .negative {{
    color: var(--color-fall) !important;
}}

.neutral {{
    color: var(--color-neutral) !important;
}}

/* 主强调色 */
.primary {{
    color: var(--color-primary) !important;
}}

.warning {{
    color: var(--color-warning) !important;
}}
"""

    def get_card_styles(self) -> str:
        """获取卡片样式

        白皮书依据: 附录C CSS深度定制 - 紧凑型Metric卡片

        Returns:
            卡片CSS样式
        """
        return f"""
/* 紧凑型卡片样式 */
.card {{
    background-color: var(--bg-card);
    border: 1px solid var(--border-color);
    border-radius: var(--card-radius);
    padding: var(--card-padding);
    margin: var(--card-margin);
    box-shadow: 0 2px 8px var(--shadow-color);
}}

.card-header {{
    font-size: var(--font-size-sm);
    color: var(--text-secondary);
    margin-bottom: var(--spacing-sm);
    text-transform: uppercase;
    letter-spacing: 0.5px;
}}

.card-value {{
    font-family: var(--font-mono);
    font-size: var(--font-size-xl);
    font-weight: {self.fonts.weight_bold};
    color: var(--text-primary);
}}

.card-delta {{
    font-family: var(--font-mono);
    font-size: var(--font-size-sm);
    margin-top: var(--spacing-xs);
}}

/* Metric卡片 */
.metric-card {{
    display: flex;
    flex-direction: column;
    gap: var(--spacing-xs);
}}

.metric-label {{
    font-size: var(--font-size-xs);
    color: var(--text-secondary);
    text-transform: uppercase;
}}

.metric-value {{
    font-family: var(--font-mono);
    font-size: var(--font-size-lg);
    font-weight: {self.fonts.weight_medium};
}}

.metric-delta {{
    font-family: var(--font-mono);
    font-size: var(--font-size-xs);
}}
"""

    def get_button_styles(self) -> str:
        """获取按钮样式

        白皮书依据: 附录C 核心配色方案 - 主强调色用于按钮

        Returns:
            按钮CSS样式
        """
        return f"""
/* 按钮样式 */
.btn {{
    font-family: var(--font-sans);
    font-size: var(--font-size-md);
    font-weight: {self.fonts.weight_medium};
    padding: var(--spacing-sm) var(--spacing-lg);
    border-radius: var(--card-radius);
    border: none;
    cursor: pointer;
    transition: all 0.2s ease;
}}

.btn-primary {{
    background-color: var(--color-primary);
    color: white;
}}

.btn-primary:hover {{
    filter: brightness(1.1);
}}

.btn-buy {{
    background-color: var(--color-rise);
    color: white;
}}

.btn-sell {{
    background-color: var(--color-fall);
    color: white;
}}

.btn-outline {{
    background-color: transparent;
    border: 1px solid var(--border-color);
    color: var(--text-primary);
}}

.btn-outline:hover {{
    background-color: var(--bg-card);
}}
"""

    def get_table_styles(self) -> str:
        """获取表格样式

        Returns:
            表格CSS样式
        """
        return f"""
/* 表格样式 */
.table {{
    width: 100%;
    border-collapse: collapse;
    font-size: var(--font-size-sm);
}}

.table th {{
    background-color: var(--bg-card);
    color: var(--text-secondary);
    font-weight: {self.fonts.weight_medium};
    text-align: left;
    padding: var(--spacing-sm);
    border-bottom: 1px solid var(--border-color);
}}

.table td {{
    padding: var(--spacing-sm);
    border-bottom: 1px solid var(--border-color);
}}

.table tr:hover {{
    background-color: var(--bg-card);
}}

/* 数字列右对齐 */
.table .number {{
    text-align: right;
    font-family: var(--font-mono);
}}
"""

    def get_streamlit_overrides(self) -> str:
        """获取Streamlit样式覆盖

        白皮书依据: 附录C CSS深度定制 - 强制覆盖Streamlit样式

        Returns:
            Streamlit覆盖CSS
        """
        return """  # pylint: disable=w1309
/* Streamlit样式覆盖 */
.stApp {{
    background-color: var(--bg-primary);
}}

.stMetric {{
    background-color: var(--bg-card);
    border: 1px solid var(--border-color);
    border-radius: var(--card-radius);
    padding: var(--card-padding);
}}

.stMetric label {{
    color: var(--text-secondary) !important;
    font-size: var(--font-size-xs) !important;
}}

.stMetric [data-testid="stMetricValue"] {{
    font-family: var(--font-mono) !important;
    color: var(--text-primary) !important;
}}

.stMetric [data-testid="stMetricDelta"] {{
    font-family: var(--font-mono) !important;
}}

/* Tab样式 */
.stTabs [data-baseweb="tab-list"] {{
    background-color: var(--bg-card);
    border-radius: var(--card-radius);
}}

.stTabs [data-baseweb="tab"] {{
    color: var(--text-secondary);
}}

.stTabs [aria-selected="true"] {{
    color: var(--color-primary) !important;
    border-bottom-color: var(--color-primary) !important;
}}

/* 按钮样式 */
.stButton > button {{
    background-color: var(--color-primary);
    color: white;
    border: none;
    border-radius: var(--card-radius);
}}

.stButton > button:hover {{
    filter: brightness(1.1);
}}

/* 输入框样式 */
.stTextInput > div > div > input {{
    background-color: var(--bg-card);
    color: var(--text-primary);
    border: 1px solid var(--border-color);
    border-radius: var(--card-radius);
}}

/* 选择框样式 */
.stSelectbox > div > div {{
    background-color: var(--bg-card);
    border: 1px solid var(--border-color);
    border-radius: var(--card-radius);
}}

/* 侧边栏样式 */
[data-testid="stSidebar"] {{
    background-color: var(--bg-card);
}}

/* 分隔线样式 */
hr {{
    border-color: var(--border-color);
}}

/* 警告和信息框 */
.stAlert {{
    border-radius: var(--card-radius);
}}
"""

    def get_full_css(self) -> str:
        """获取完整CSS

        白皮书依据: 附录C UI/UX设计规范

        Returns:
            完整的CSS样式
        """
        return f"""
{self.get_google_fonts_import()}
{self.get_css_variables()}
{self.get_base_styles()}
{self.get_card_styles()}
{self.get_button_styles()}
{self.get_table_styles()}
{self.get_streamlit_overrides()}
"""

    def inject_streamlit_css(self) -> None:
        """注入Streamlit CSS

        白皮书依据: 附录C CSS深度定制
        在dashboard.py注入自定义CSS，强制覆盖Streamlit样式
        """
        try:
            import streamlit as st  # pylint: disable=import-outside-toplevel

            st.markdown(f"<style>{self.get_full_css()}</style>", unsafe_allow_html=True)

            logger.debug("Streamlit CSS injected successfully")

        except ImportError:
            logger.warning("Streamlit not available, CSS not injected")

    def format_price(self, price: float, change_pct: Optional[float] = None) -> str:
        """格式化价格显示

        Args:
            price: 价格
            change_pct: 涨跌幅

        Returns:
            格式化的HTML
        """
        price_str = f"¥{price:,.2f}"

        if change_pct is None:
            return f'<span class="font-mono">{price_str}</span>'

        color_class = "rise" if change_pct >= 0 else "fall"
        sign = "+" if change_pct >= 0 else ""

        return f"""
<span class="font-mono {color_class}">{price_str}</span>
<span class="font-mono {color_class}">({sign}{change_pct:.2f}%)</span>
"""

    def format_pnl(self, pnl: float) -> str:
        """格式化盈亏显示

        Args:
            pnl: 盈亏金额

        Returns:
            格式化的HTML
        """
        color_class = "rise" if pnl >= 0 else "fall"
        sign = "+" if pnl >= 0 else ""

        return f'<span class="font-mono {color_class}">{sign}¥{pnl:,.2f}</span>'

    def format_percent(self, value: float) -> str:
        """格式化百分比显示

        Args:
            value: 百分比值

        Returns:
            格式化的HTML
        """
        color_class = "rise" if value >= 0 else "fall"
        sign = "+" if value >= 0 else ""

        return f'<span class="font-mono {color_class}">{sign}{value:.2f}%</span>'

    def get_color_for_value(self, value: float) -> str:
        """根据值获取颜色

        Args:
            value: 数值

        Returns:
            颜色代码
        """
        if value > 0:  # pylint: disable=no-else-return
            return self.colors.rise
        elif value < 0:
            return self.colors.fall
        else:
            return self.colors.neutral

    def switch_scheme(self, scheme: ColorScheme) -> None:
        """切换配色方案

        Args:
            scheme: 新的配色方案
        """
        self.scheme = scheme
        self.colors = self.COLOR_SCHEMES.get(scheme, self.COLOR_SCHEMES[ColorScheme.NIUNIU])

        logger.info(f"Color scheme switched to: {scheme.value}")

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典

        Returns:
            主题配置字典
        """
        return {
            "mode": self.mode.value,
            "scheme": self.scheme.value,
            "colors": self.colors.to_dict(),
            "fonts": self.fonts.to_dict(),
            "spacing": self.spacing.to_dict(),
        }


# 全局主题实例
_global_theme: Optional[NiuNiuTheme] = None


def get_theme() -> NiuNiuTheme:
    """获取全局主题实例

    Returns:
        全局主题实例
    """
    global _global_theme  # pylint: disable=w0603

    if _global_theme is None:
        _global_theme = NiuNiuTheme()

    return _global_theme


def set_theme(theme: NiuNiuTheme) -> None:
    """设置全局主题实例

    Args:
        theme: 主题实例
    """
    global _global_theme  # pylint: disable=w0603
    _global_theme = theme

    logger.info(f"Global theme set: mode={theme.mode.value}, scheme={theme.scheme.value}")


def apply_theme() -> None:
    """应用全局主题到Streamlit"""
    theme = get_theme()
    theme.inject_streamlit_css()
