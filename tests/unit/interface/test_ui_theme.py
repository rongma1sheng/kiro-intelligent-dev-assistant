"""UI/UX设计规范测试

白皮书依据: 附录C UI/UX设计规范
"""

import pytest

from src.interface.ui_theme import (
    ThemeMode,
    ColorScheme,
    ThemeColors,
    FontConfig,
    SpacingConfig,
    NiuNiuTheme,
    get_theme,
    set_theme,
    apply_theme
)


class TestThemeMode:
    """主题模式测试"""
    
    def test_light_mode(self):
        """测试浅色模式"""
        assert ThemeMode.LIGHT.value == "light"
    
    def test_dark_mode(self):
        """测试深色模式"""
        assert ThemeMode.DARK.value == "dark"


class TestColorScheme:
    """配色方案测试"""
    
    def test_niuniu_scheme(self):
        """测试牛牛配色"""
        assert ColorScheme.NIUNIU.value == "niuniu"
    
    def test_fintech_scheme(self):
        """测试金融科技配色"""
        assert ColorScheme.FINTECH.value == "fintech"
    
    def test_professional_scheme(self):
        """测试专业深色配色"""
        assert ColorScheme.PROFESSIONAL.value == "professional"


class TestThemeColors:
    """主题颜色测试"""
    
    def test_default_colors(self):
        """测试默认颜色
        
        白皮书依据: 附录C 核心配色方案
        """
        colors = ThemeColors()
        assert colors.bg_primary == "#191B24"  # 深空灰
        assert colors.bg_card == "#222631"  # 模块灰
        assert colors.rise == "#F44336"  # A股红
        assert colors.fall == "#00C853"  # A股绿
        assert colors.primary == "#308FFF"  # 牛牛蓝
        assert colors.text_primary == "#E1E3E8"  # 亮灰白
    
    def test_colors_to_dict(self):
        """测试颜色转字典"""
        colors = ThemeColors()
        data = colors.to_dict()
        assert 'bg_primary' in data
        assert 'rise' in data
        assert 'fall' in data
        assert 'primary' in data


class TestFontConfig:
    """字体配置测试"""
    
    def test_default_fonts(self):
        """测试默认字体
        
        白皮书依据: 附录C CSS深度定制 - Roboto Mono
        """
        fonts = FontConfig()
        assert "Roboto Mono" in fonts.mono
        assert "Inter" in fonts.sans
    
    def test_font_sizes(self):
        """测试字体大小"""
        fonts = FontConfig()
        assert fonts.size_xs == "10px"
        assert fonts.size_sm == "12px"
        assert fonts.size_md == "14px"
        assert fonts.size_lg == "16px"
        assert fonts.size_xl == "20px"
    
    def test_font_weights(self):
        """测试字体粗细"""
        fonts = FontConfig()
        assert fonts.weight_normal == 400
        assert fonts.weight_medium == 500
        assert fonts.weight_bold == 700
    
    def test_fonts_to_dict(self):
        """测试字体转字典"""
        fonts = FontConfig()
        data = fonts.to_dict()
        assert 'mono' in data
        assert 'sans' in data
        assert 'size_md' in data


class TestSpacingConfig:
    """间距配置测试"""
    
    def test_default_spacing(self):
        """测试默认间距
        
        白皮书依据: 附录C CSS深度定制 - 紧凑型Metric卡片
        """
        spacing = SpacingConfig()
        assert spacing.xs == "4px"
        assert spacing.sm == "8px"
        assert spacing.md == "12px"
        assert spacing.lg == "16px"
        assert spacing.xl == "24px"
    
    def test_card_spacing(self):
        """测试卡片间距"""
        spacing = SpacingConfig()
        assert spacing.card_padding == "12px"
        assert spacing.card_margin == "8px"
        assert spacing.card_radius == "8px"
    
    def test_spacing_to_dict(self):
        """测试间距转字典"""
        spacing = SpacingConfig()
        data = spacing.to_dict()
        assert 'xs' in data
        assert 'card_padding' in data


class TestNiuNiuTheme:
    """牛牛主题测试"""
    
    @pytest.fixture
    def theme(self):
        """测试夹具"""
        return NiuNiuTheme()
    
    def test_default_mode(self, theme):
        """测试默认模式"""
        assert theme.mode == ThemeMode.DARK
    
    def test_default_scheme(self, theme):
        """测试默认配色"""
        assert theme.scheme == ColorScheme.NIUNIU
    
    def test_google_fonts_import(self, theme):
        """测试Google Fonts导入"""
        css = theme.get_google_fonts_import()
        assert "fonts.googleapis.com" in css
        assert "Roboto+Mono" in css
        assert "Inter" in css
    
    def test_css_variables(self, theme):
        """测试CSS变量"""
        css = theme.get_css_variables()
        assert "--bg-primary" in css
        assert "--color-rise" in css
        assert "--color-fall" in css
        assert "--color-primary" in css
        assert "--font-mono" in css
    
    def test_base_styles(self, theme):
        """测试基础样式"""
        css = theme.get_base_styles()
        assert ".rise" in css
        assert ".fall" in css
        assert ".font-mono" in css
    
    def test_card_styles(self, theme):
        """测试卡片样式
        
        白皮书依据: 附录C CSS深度定制 - 紧凑型Metric卡片
        """
        css = theme.get_card_styles()
        assert ".card" in css
        assert ".metric-card" in css
        assert "border-radius" in css
    
    def test_button_styles(self, theme):
        """测试按钮样式"""
        css = theme.get_button_styles()
        assert ".btn" in css
        assert ".btn-primary" in css
        assert ".btn-buy" in css
        assert ".btn-sell" in css
    
    def test_table_styles(self, theme):
        """测试表格样式"""
        css = theme.get_table_styles()
        assert ".table" in css
        assert "border-collapse" in css
    
    def test_streamlit_overrides(self, theme):
        """测试Streamlit样式覆盖
        
        白皮书依据: 附录C CSS深度定制 - 强制覆盖Streamlit样式
        """
        css = theme.get_streamlit_overrides()
        assert ".stApp" in css
        assert ".stMetric" in css
        assert ".stTabs" in css
        assert ".stButton" in css
    
    def test_full_css(self, theme):
        """测试完整CSS"""
        css = theme.get_full_css()
        assert len(css) > 1000  # 应该有足够的内容
        assert "@import" in css
        assert ":root" in css
    
    def test_format_price_positive(self, theme):
        """测试格式化价格 - 上涨"""
        html = theme.format_price(12.50, 2.35)
        assert "12.50" in html
        assert "2.35" in html
        assert "rise" in html
    
    def test_format_price_negative(self, theme):
        """测试格式化价格 - 下跌"""
        html = theme.format_price(12.50, -1.25)
        assert "12.50" in html
        assert "-1.25" in html
        assert "fall" in html
    
    def test_format_pnl_positive(self, theme):
        """测试格式化盈亏 - 盈利"""
        html = theme.format_pnl(1000.50)
        assert "1,000.50" in html
        assert "rise" in html
        assert "+" in html
    
    def test_format_pnl_negative(self, theme):
        """测试格式化盈亏 - 亏损"""
        html = theme.format_pnl(-500.25)
        assert "500.25" in html
        assert "fall" in html
    
    def test_format_percent(self, theme):
        """测试格式化百分比"""
        html = theme.format_percent(5.25)
        assert "5.25%" in html
        assert "rise" in html
    
    def test_get_color_for_value(self, theme):
        """测试根据值获取颜色"""
        assert theme.get_color_for_value(1.0) == theme.colors.rise
        assert theme.get_color_for_value(-1.0) == theme.colors.fall
        assert theme.get_color_for_value(0.0) == theme.colors.neutral
    
    def test_switch_scheme(self, theme):
        """测试切换配色方案"""
        original_primary = theme.colors.primary
        theme.switch_scheme(ColorScheme.FINTECH)
        assert theme.scheme == ColorScheme.FINTECH
        assert theme.colors.primary != original_primary
    
    def test_to_dict(self, theme):
        """测试转字典"""
        data = theme.to_dict()
        assert data['mode'] == 'dark'
        assert data['scheme'] == 'niuniu'
        assert 'colors' in data
        assert 'fonts' in data
        assert 'spacing' in data


class TestGlobalTheme:
    """全局主题测试"""
    
    def test_get_theme(self):
        """测试获取全局主题"""
        theme = get_theme()
        assert isinstance(theme, NiuNiuTheme)
    
    def test_set_theme(self):
        """测试设置全局主题"""
        new_theme = NiuNiuTheme(
            mode=ThemeMode.LIGHT,
            scheme=ColorScheme.FINTECH
        )
        set_theme(new_theme)
        
        theme = get_theme()
        assert theme.mode == ThemeMode.LIGHT
        assert theme.scheme == ColorScheme.FINTECH
        
        # 恢复默认
        set_theme(NiuNiuTheme())


class TestColorSchemes:
    """配色方案测试"""
    
    def test_niuniu_colors(self):
        """测试牛牛配色"""
        theme = NiuNiuTheme(scheme=ColorScheme.NIUNIU)
        assert theme.colors.bg_primary == "#191B24"
        assert theme.colors.primary == "#308FFF"
    
    def test_fintech_colors(self):
        """测试金融科技配色"""
        theme = NiuNiuTheme(scheme=ColorScheme.FINTECH)
        assert theme.colors.primary == "#048cfc"
        assert theme.colors.bg_primary == "#05478a"
    
    def test_professional_colors(self):
        """测试专业深色配色"""
        theme = NiuNiuTheme(scheme=ColorScheme.PROFESSIONAL)
        assert theme.colors.bg_primary == "#0D1117"
        assert theme.colors.primary == "#1890FF"
