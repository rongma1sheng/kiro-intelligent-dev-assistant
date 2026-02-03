"""UI/UX Pro Max集成方案测试

白皮书依据: 附录D UI/UX Pro Max集成方案
"""

import pytest

from src.interface.ui_pro_max import (
    UIStyle,
    ChartType,
    ColorPalette,
    FontPairing,
    ChartConfig,
    UIProMaxManager,
    get_ui_pro_max,
    apply_ui_pro_max
)


class TestUIStyle:
    """UI风格测试"""
    
    def test_glassmorphism(self):
        """测试玻璃态风格"""
        assert UIStyle.GLASSMORPHISM.value == "glassmorphism"
    
    def test_minimalism(self):
        """测试极简主义风格"""
        assert UIStyle.MINIMALISM.value == "minimalism"
    
    def test_dark_mode(self):
        """测试深色模式风格"""
        assert UIStyle.DARK_MODE.value == "dark_mode"
    
    def test_bento_grid(self):
        """测试便当盒布局风格"""
        assert UIStyle.BENTO_GRID.value == "bento_grid"
    
    def test_neumorphism(self):
        """测试新拟态风格"""
        assert UIStyle.NEUMORPHISM.value == "neumorphism"
    
    def test_brutalism(self):
        """测试粗野主义风格"""
        assert UIStyle.BRUTALISM.value == "brutalism"


class TestChartType:
    """图表类型测试"""
    
    def test_line_chart(self):
        """测试折线图"""
        assert ChartType.LINE.value == "line"
    
    def test_candlestick_chart(self):
        """测试K线图"""
        assert ChartType.CANDLESTICK.value == "candlestick"
    
    def test_area_chart(self):
        """测试面积图"""
        assert ChartType.AREA.value == "area"
    
    def test_all_chart_types(self):
        """测试所有图表类型"""
        expected_types = [
            "line", "candlestick", "area", "bar", "pie",
            "heatmap", "gauge", "waterfall", "treemap", "sparkline"
        ]
        actual_types = [c.value for c in ChartType]
        for chart_type in expected_types:
            assert chart_type in actual_types


class TestColorPalette:
    """配色方案测试"""
    
    def test_create_palette(self):
        """测试创建配色方案"""
        palette = ColorPalette(
            name="测试方案",
            primary="#048cfc",
            success="#00C853",
            danger="#F44336",
            neutral="#657e98",
            bg_dark="#05478a",
            bg_light="#b4bdc6",
            bg_card="#ffffff",
            text_primary="#333333",
            text_secondary="#657e98"
        )
        assert palette.name == "测试方案"
        assert palette.primary == "#048cfc"
        assert palette.success == "#00C853"
        assert palette.danger == "#F44336"
    
    def test_palette_to_css_vars(self):
        """测试配色方案转CSS变量"""
        palette = ColorPalette(
            name="测试方案",
            primary="#048cfc",
            success="#00C853",
            danger="#F44336",
            neutral="#657e98",
            bg_dark="#05478a",
            bg_light="#b4bdc6",
            bg_card="#ffffff",
            text_primary="#333333",
            text_secondary="#657e98"
        )
        css = palette.to_css_vars()
        assert "--primary: #048cfc" in css
        assert "--success: #00C853" in css
        assert "--danger: #F44336" in css


class TestFontPairing:
    """字体配对测试"""
    
    def test_create_font_pairing(self):
        """测试创建字体配对"""
        font = FontPairing(
            name="Roboto Mono + Inter",
            mono="'Roboto Mono', monospace",
            sans="'Inter', sans-serif",
            google_import="https://fonts.googleapis.com/css2?family=Roboto+Mono",
            description="等宽字体适合数字"
        )
        assert font.name == "Roboto Mono + Inter"
        assert "Roboto Mono" in font.mono
        assert "Inter" in font.sans
    
    def test_font_to_css(self):
        """测试字体配对转CSS"""
        font = FontPairing(
            name="Roboto Mono + Inter",
            mono="'Roboto Mono', monospace",
            sans="'Inter', sans-serif",
            google_import="https://fonts.googleapis.com/css2?family=Roboto+Mono",
            description="等宽字体适合数字"
        )
        css = font.to_css()
        assert "@import" in css
        assert ".font-mono" in css
        assert ".font-sans" in css


class TestChartConfig:
    """图表配置测试"""
    
    def test_create_chart_config(self):
        """测试创建图表配置"""
        config = ChartConfig(
            chart_type=ChartType.LINE,
            library="Plotly",
            use_case="净值曲线、价格走势",
            features=["趋势展示", "时间序列"]
        )
        assert config.chart_type == ChartType.LINE
        assert config.library == "Plotly"
        assert "趋势展示" in config.features


class TestUIProMaxManager:
    """UI/UX Pro Max管理器测试"""
    
    @pytest.fixture
    def manager(self):
        """测试夹具"""
        return UIProMaxManager()
    
    def test_init(self, manager):
        """测试初始化"""
        assert manager.current_palette is not None
        assert manager.current_font is not None
    
    def test_default_palette(self, manager):
        """测试默认配色方案
        
        白皮书依据: 附录D D.3.1 Fintech配色方案 - 信任蓝+安全绿
        """
        assert manager.current_palette.name == "信任蓝 + 安全绿"
        assert manager.current_palette.primary == "#048cfc"
    
    def test_default_font(self, manager):
        """测试默认字体配对
        
        白皮书依据: 附录D D.3.2 专业字体配对 - Roboto Mono + Inter
        """
        assert manager.current_font.name == "Roboto Mono + Inter"
        assert "Roboto Mono" in manager.current_font.mono
    
    def test_list_palettes(self, manager):
        """测试列出配色方案"""
        palettes = manager.list_palettes()
        assert "trust_blue" in palettes
        assert "professional_dark" in palettes
        assert "niuniu_classic" in palettes
    
    def test_list_fonts(self, manager):
        """测试列出字体配对"""
        fonts = manager.list_fonts()
        assert "roboto_inter" in fonts
        assert "jetbrains_poppins" in fonts
    
    def test_list_charts(self, manager):
        """测试列出图表类型"""
        charts = manager.list_charts()
        assert ChartType.LINE in charts
        assert ChartType.CANDLESTICK in charts
        assert ChartType.HEATMAP in charts
    
    def test_set_palette(self, manager):
        """测试设置配色方案"""
        result = manager.set_palette("professional_dark")
        assert result is True
        assert manager.current_palette.name == "专业深色"
    
    def test_set_palette_invalid(self, manager):
        """测试设置无效配色方案"""
        result = manager.set_palette("invalid_palette")
        assert result is False
    
    def test_set_font(self, manager):
        """测试设置字体配对"""
        result = manager.set_font("jetbrains_poppins")
        assert result is True
        assert manager.current_font.name == "JetBrains Mono + Poppins"
    
    def test_set_font_invalid(self, manager):
        """测试设置无效字体配对"""
        result = manager.set_font("invalid_font")
        assert result is False
    
    def test_get_chart_config(self, manager):
        """测试获取图表配置"""
        config = manager.get_chart_config(ChartType.LINE)
        assert config is not None
        assert config.library == "Plotly"
        assert "净值曲线" in config.use_case
    
    def test_get_chart_config_candlestick(self, manager):
        """测试获取K线图配置
        
        白皮书依据: 附录D D.3.3 图表类型推荐 - Candlestick
        """
        config = manager.get_chart_config(ChartType.CANDLESTICK)
        assert config is not None
        assert "TradingView" in config.library
        assert "技术分析" in config.use_case


class TestUIStyles:
    """UI风格CSS测试"""
    
    @pytest.fixture
    def manager(self):
        """测试夹具"""
        return UIProMaxManager()
    
    def test_glassmorphism_css(self, manager):
        """测试玻璃态CSS
        
        白皮书依据: 附录D D.3.4 UI风格推荐 - Glassmorphism
        """
        css = manager.get_glassmorphism_css()
        assert ".glass-card" in css
        assert "backdrop-filter" in css
        assert "blur" in css
    
    def test_neumorphism_css(self, manager):
        """测试新拟态CSS
        
        白皮书依据: 附录D D.3.4 UI风格推荐 - Neumorphism
        """
        css = manager.get_neumorphism_css()
        assert ".neu-card" in css
        assert "box-shadow" in css
    
    def test_bento_grid_css(self, manager):
        """测试便当盒布局CSS
        
        白皮书依据: 附录D D.3.4 UI风格推荐 - Bento Grid
        """
        css = manager.get_bento_grid_css()
        assert ".bento-grid" in css
        assert "display: grid" in css
        assert ".bento-item" in css
    
    def test_animation_css(self, manager):
        """测试动画CSS
        
        白皮书依据: 附录D D.4.2 交互设计规范 - 动画时长标准
        """
        css = manager.get_animation_css()
        assert ".animate-micro" in css
        assert ".animate-page" in css
        assert ".animate-data" in css
        assert "@keyframes fadeIn" in css
        assert ".skeleton" in css
    
    def test_responsive_css(self, manager):
        """测试响应式CSS
        
        白皮书依据: 附录D D.4.2 交互设计规范 - 触摸目标大小
        """
        css = manager.get_responsive_css()
        assert "@media" in css
        assert ".touch-target" in css
        assert "44px" in css  # 最小触摸目标
        assert "48px" in css  # 推荐触摸目标
    
    def test_accessibility_css(self, manager):
        """测试可访问性CSS
        
        白皮书依据: 附录D D.4.1 金融Dashboard核心原则 - 可访问性
        """
        css = manager.get_accessibility_css()
        assert "prefers-contrast" in css
        assert "prefers-reduced-motion" in css
        assert ":focus" in css
        assert ".sr-only" in css
    
    def test_full_css(self, manager):
        """测试完整CSS"""
        css = manager.get_full_css()
        assert len(css) > 2000  # 应该有足够的内容
        assert ":root" in css
        assert ".glass-card" in css
        assert ".bento-grid" in css


class TestUXBestPractices:
    """UX最佳实践测试"""
    
    @pytest.fixture
    def manager(self):
        """测试夹具"""
        return UIProMaxManager()
    
    def test_get_ux_best_practices(self, manager):
        """测试获取UX最佳实践
        
        白皮书依据: 附录D D.4 UX最佳实践
        """
        practices = manager.get_ux_best_practices()
        
        assert "数据可视化" in practices
        assert "信息架构" in practices
        assert "性能优化" in practices
        assert "可访问性" in practices
        assert "错误处理" in practices
        
        # 检查具体实践
        assert "使用颜色编码传达状态" in practices["数据可视化"][0]
        assert "核心指标置顶" in practices["信息架构"][0]
    
    def test_get_response_time_standards(self, manager):
        """测试获取响应时间标准
        
        白皮书依据: 附录D D.4.2 交互设计规范 - 响应时间标准
        """
        standards = manager.get_response_time_standards()
        
        assert "即时反馈" in standards
        assert "快速响应" in standards
        assert "可接受" in standards
        assert "需要进度条" in standards
        
        assert "< 100ms" in standards["即时反馈"]
        assert "< 1s" in standards["快速响应"]
        assert "< 3s" in standards["可接受"]
        assert "> 3s" in standards["需要进度条"]
    
    def test_get_animation_duration_standards(self, manager):
        """测试获取动画时长标准
        
        白皮书依据: 附录D D.4.2 交互设计规范 - 动画时长标准
        """
        standards = manager.get_animation_duration_standards()
        
        assert "微交互" in standards
        assert "页面过渡" in standards
        assert "数据更新" in standards
        assert "避免" in standards
        
        assert "100-200ms" in standards["微交互"]
        assert "200-300ms" in standards["页面过渡"]
        assert "300-500ms" in standards["数据更新"]
        assert "> 500ms" in standards["避免"]


class TestGlobalUIProMax:
    """全局UI Pro Max测试"""
    
    def test_get_ui_pro_max(self):
        """测试获取全局实例"""
        ui_pro_max = get_ui_pro_max()
        assert isinstance(ui_pro_max, UIProMaxManager)
    
    def test_get_ui_pro_max_singleton(self):
        """测试单例模式"""
        ui1 = get_ui_pro_max()
        ui2 = get_ui_pro_max()
        assert ui1 is ui2


class TestColorPalettes:
    """配色方案详细测试"""
    
    @pytest.fixture
    def manager(self):
        """测试夹具"""
        return UIProMaxManager()
    
    def test_trust_blue_palette(self, manager):
        """测试信任蓝配色
        
        白皮书依据: 附录D D.3.1 方案1: 信任蓝 + 安全绿
        """
        manager.set_palette("trust_blue")
        palette = manager.current_palette
        
        assert palette.primary == "#048cfc"
        assert palette.success == "#00C853"
        assert palette.danger == "#F44336"
    
    def test_professional_dark_palette(self, manager):
        """测试专业深色配色
        
        白皮书依据: 附录D D.3.1 方案2: 专业深色
        """
        manager.set_palette("professional_dark")
        palette = manager.current_palette
        
        assert palette.primary == "#308FFF"
        assert palette.bg_dark == "#191B24"
    
    def test_bloomberg_terminal_palette(self, manager):
        """测试Bloomberg终端配色"""
        manager.set_palette("bloomberg_terminal")
        palette = manager.current_palette
        
        assert palette.primary == "#FF6600"
        assert palette.bg_dark == "#000000"


class TestFontPairings:
    """字体配对详细测试"""
    
    @pytest.fixture
    def manager(self):
        """测试夹具"""
        return UIProMaxManager()
    
    def test_roboto_inter_pairing(self, manager):
        """测试Roboto Mono + Inter配对
        
        白皮书依据: 附录D D.3.2 配对1: Roboto Mono + Inter
        """
        manager.set_font("roboto_inter")
        font = manager.current_font
        
        assert "Roboto Mono" in font.mono
        assert "Inter" in font.sans
        assert "等宽字体" in font.description
    
    def test_jetbrains_poppins_pairing(self, manager):
        """测试JetBrains Mono + Poppins配对
        
        白皮书依据: 附录D D.3.2 配对2: JetBrains Mono + Poppins
        """
        manager.set_font("jetbrains_poppins")
        font = manager.current_font
        
        assert "JetBrains Mono" in font.mono
        assert "Poppins" in font.sans
        assert "程序员" in font.description
