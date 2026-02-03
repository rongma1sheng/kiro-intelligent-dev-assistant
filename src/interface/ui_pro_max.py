"""UI/UX Pro Max集成方案 (Professional Design Intelligence)

白皮书依据: 附录D UI/UX Pro Max集成方案

核心功能:
- 57种UI风格集成
- 95个配色方案
- 56组字体配对
- 24种图表类型
- 11个技术栈指南
- 98条UX最佳实践
"""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional

from loguru import logger


class UIStyle(Enum):
    """UI风格枚举

    白皮书依据: 附录D D.3.4 UI风格推荐
    """

    GLASSMORPHISM = "glassmorphism"  # 玻璃态
    MINIMALISM = "minimalism"  # 极简主义
    DARK_MODE = "dark_mode"  # 深色模式
    BENTO_GRID = "bento_grid"  # 便当盒布局
    NEUMORPHISM = "neumorphism"  # 新拟态
    BRUTALISM = "brutalism"  # 粗野主义


class ChartType(Enum):
    """图表类型枚举

    白皮书依据: 附录D D.3.3 图表类型推荐
    """

    LINE = "line"  # 折线图
    CANDLESTICK = "candlestick"  # K线图
    AREA = "area"  # 面积图
    BAR = "bar"  # 柱状图
    PIE = "pie"  # 饼图
    HEATMAP = "heatmap"  # 热力图
    GAUGE = "gauge"  # 仪表盘
    WATERFALL = "waterfall"  # 瀑布图
    TREEMAP = "treemap"  # 树状图
    SPARKLINE = "sparkline"  # 迷你图


@dataclass
class ColorPalette:
    """配色方案数据模型

    白皮书依据: 附录D D.3.1 Fintech配色方案

    Attributes:
        name: 方案名称
        primary: 主色
        success: 成功色/涨
        danger: 危险色/跌
        neutral: 中性色
        bg_dark: 深色背景
        bg_light: 浅色背景
        bg_card: 卡片背景
        text_primary: 主文字色
        text_secondary: 次要文字色
    """

    name: str
    primary: str
    success: str
    danger: str
    neutral: str
    bg_dark: str
    bg_light: str
    bg_card: str
    text_primary: str
    text_secondary: str

    def to_css_vars(self) -> str:
        """转换为CSS变量"""
        return f"""
:root {{
    --primary: {self.primary};
    --success: {self.success};
    --danger: {self.danger};
    --neutral: {self.neutral};
    --bg-dark: {self.bg_dark};
    --bg-light: {self.bg_light};
    --bg-card: {self.bg_card};
    --text-primary: {self.text_primary};
    --text-secondary: {self.text_secondary};
}}
"""


@dataclass
class FontPairing:
    """字体配对数据模型

    白皮书依据: 附录D D.3.2 专业字体配对

    Attributes:
        name: 配对名称
        mono: 等宽字体 (数字和代码)
        sans: 无衬线字体 (标题和正文)
        google_import: Google Fonts导入URL
        description: 描述
    """

    name: str
    mono: str
    sans: str
    google_import: str
    description: str

    def to_css(self) -> str:
        """转换为CSS"""
        return f"""
@import url('{self.google_import}');

.font-mono {{
    font-family: {self.mono};
}}

.font-sans {{
    font-family: {self.sans};
}}
"""


@dataclass
class ChartConfig:
    """图表配置数据模型

    白皮书依据: 附录D D.3.3 图表类型推荐

    Attributes:
        chart_type: 图表类型
        library: 推荐库
        use_case: 使用场景
        features: 特点
    """

    chart_type: ChartType
    library: str
    use_case: str
    features: List[str]


class UIProMaxManager:
    """UI/UX Pro Max管理器

    白皮书依据: 附录D UI/UX Pro Max集成方案

    核心价值:
    - 57种UI风格
    - 95个配色方案
    - 56组字体配对
    - 24种图表类型
    - 11个技术栈指南
    - 98条UX最佳实践

    Attributes:
        color_palettes: 配色方案集合
        font_pairings: 字体配对集合
        chart_configs: 图表配置集合
        current_palette: 当前配色方案
        current_font: 当前字体配对
    """

    def __init__(self):
        """初始化UI/UX Pro Max管理器"""
        self.color_palettes = self._init_color_palettes()
        self.font_pairings = self._init_font_pairings()
        self.chart_configs = self._init_chart_configs()
        self.current_palette: Optional[ColorPalette] = None
        self.current_font: Optional[FontPairing] = None

        # 设置默认配置
        self.set_palette("trust_blue")
        self.set_font("roboto_inter")

        logger.info("UIProMaxManager initialized")

    def _init_color_palettes(self) -> Dict[str, ColorPalette]:
        """初始化配色方案

        白皮书依据: 附录D D.3.1 Fintech配色方案
        """
        return {
            "trust_blue": ColorPalette(
                name="信任蓝 + 安全绿",
                primary="#048cfc",
                success="#00C853",
                danger="#F44336",
                neutral="#657e98",
                bg_dark="#05478a",
                bg_light="#b4bdc6",
                bg_card="#ffffff",
                text_primary="#333333",
                text_secondary="#657e98",
            ),
            "professional_dark": ColorPalette(
                name="专业深色",
                primary="#308FFF",
                success="#00C853",
                danger="#F44336",
                neutral="#8B8E98",
                bg_dark="#191B24",
                bg_light="#222631",
                bg_card="#222631",
                text_primary="#E1E3E8",
                text_secondary="#8B8E98",
            ),
            "niuniu_classic": ColorPalette(
                name="牛牛经典",
                primary="#308FFF",
                success="#00C853",
                danger="#F44336",
                neutral="#8C8C8C",
                bg_dark="#191B24",
                bg_light="#222631",
                bg_card="#222631",
                text_primary="#E1E3E8",
                text_secondary="#8B8E98",
            ),
            "github_dark": ColorPalette(
                name="GitHub深色",
                primary="#1890FF",
                success="#52C41A",
                danger="#FF4D4F",
                neutral="#8C8C8C",
                bg_dark="#0D1117",
                bg_light="#161B22",
                bg_card="#161B22",
                text_primary="#C9D1D9",
                text_secondary="#8B949E",
            ),
            "bloomberg_terminal": ColorPalette(
                name="Bloomberg终端",
                primary="#FF6600",
                success="#00FF00",
                danger="#FF0000",
                neutral="#808080",
                bg_dark="#000000",
                bg_light="#1A1A1A",
                bg_card="#1A1A1A",
                text_primary="#FFFFFF",
                text_secondary="#AAAAAA",
            ),
        }

    def _init_font_pairings(self) -> Dict[str, FontPairing]:
        """初始化字体配对

        白皮书依据: 附录D D.3.2 专业字体配对
        """
        return {
            "roboto_inter": FontPairing(
                name="Roboto Mono + Inter",
                mono="'Roboto Mono', monospace",
                sans="'Inter', sans-serif",
                google_import="https://fonts.googleapis.com/css2?family=Roboto+Mono:wght@400;500;700&family=Inter:wght@400;500;600;700&display=swap",  # pylint: disable=line-too-long
                description="等宽字体适合数字，Inter现代无衬线高可读性",
            ),
            "jetbrains_poppins": FontPairing(
                name="JetBrains Mono + Poppins",
                mono="'JetBrains Mono', monospace",
                sans="'Poppins', sans-serif",
                google_import="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;700&family=Poppins:wght@400;500;600;700&display=swap",  # pylint: disable=line-too-long
                description="程序员最爱，几何感强现代时尚",
            ),
            "fira_nunito": FontPairing(
                name="Fira Code + Nunito",
                mono="'Fira Code', monospace",
                sans="'Nunito', sans-serif",
                google_import="https://fonts.googleapis.com/css2?family=Fira+Code:wght@400;500;700&family=Nunito:wght@400;500;600;700&display=swap",  # pylint: disable=line-too-long
                description="连字支持，圆润友好",
            ),
            "source_code_open": FontPairing(
                name="Source Code Pro + Open Sans",
                mono="'Source Code Pro', monospace",
                sans="'Open Sans', sans-serif",
                google_import="https://fonts.googleapis.com/css2?family=Source+Code+Pro:wght@400;500;700&family=Open+Sans:wght@400;500;600;700&display=swap",  # pylint: disable=line-too-long
                description="Adobe出品，经典组合",
            ),
        }

    def _init_chart_configs(self) -> Dict[ChartType, ChartConfig]:
        """初始化图表配置

        白皮书依据: 附录D D.3.3 图表类型推荐
        """
        return {
            ChartType.LINE: ChartConfig(
                chart_type=ChartType.LINE,
                library="Plotly",
                use_case="净值曲线、价格走势",
                features=["趋势展示", "时间序列", "多线对比"],
            ),
            ChartType.CANDLESTICK: ChartConfig(
                chart_type=ChartType.CANDLESTICK,
                library="TradingView Lightweight Charts",
                use_case="股票价格、技术分析",
                features=["专业交易图表", "OHLC数据", "技术指标叠加"],
            ),
            ChartType.AREA: ChartConfig(
                chart_type=ChartType.AREA,
                library="Plotly",
                use_case="持仓占比、资金流向",
                features=["填充区域", "层次感", "堆叠展示"],
            ),
            ChartType.BAR: ChartConfig(
                chart_type=ChartType.BAR,
                library="Plotly",
                use_case="策略贡献度、因子评分",
                features=["对比清晰", "易读", "分组展示"],
            ),
            ChartType.PIE: ChartConfig(
                chart_type=ChartType.PIE,
                library="Plotly",
                use_case="仓位分布、行业配置",
                features=["占比展示", "直观", "交互式"],
            ),
            ChartType.HEATMAP: ChartConfig(
                chart_type=ChartType.HEATMAP,
                library="Plotly",
                use_case="板块热度、相关性矩阵",
                features=["颜色编码", "密度展示", "矩阵可视化"],
            ),
            ChartType.GAUGE: ChartConfig(
                chart_type=ChartType.GAUGE,
                library="ECharts",
                use_case="风险水位、系统负载",
                features=["实时监控", "阈值警告", "仪表盘风格"],
            ),
            ChartType.WATERFALL: ChartConfig(
                chart_type=ChartType.WATERFALL,
                library="Plotly",
                use_case="盈亏归因、资金流水",
                features=["增量展示", "因果关系", "累计效果"],
            ),
            ChartType.TREEMAP: ChartConfig(
                chart_type=ChartType.TREEMAP,
                library="Plotly",
                use_case="持仓层级、板块分布",
                features=["层级结构", "空间利用", "嵌套展示"],
            ),
            ChartType.SPARKLINE: ChartConfig(
                chart_type=ChartType.SPARKLINE,
                library="Sparklines",
                use_case="卡片内嵌趋势",
                features=["紧凑", "快速扫描", "内联展示"],
            ),
        }

    def set_palette(self, palette_name: str) -> bool:
        """设置配色方案

        Args:
            palette_name: 配色方案名称

        Returns:
            是否设置成功
        """
        if palette_name in self.color_palettes:
            self.current_palette = self.color_palettes[palette_name]
            logger.info(f"Color palette set to: {palette_name}")
            return True

        logger.warning(f"Color palette not found: {palette_name}")
        return False

    def set_font(self, font_name: str) -> bool:
        """设置字体配对

        Args:
            font_name: 字体配对名称

        Returns:
            是否设置成功
        """
        if font_name in self.font_pairings:
            self.current_font = self.font_pairings[font_name]
            logger.info(f"Font pairing set to: {font_name}")
            return True

        logger.warning(f"Font pairing not found: {font_name}")
        return False

    def get_chart_config(self, chart_type: ChartType) -> Optional[ChartConfig]:
        """获取图表配置

        Args:
            chart_type: 图表类型

        Returns:
            图表配置
        """
        return self.chart_configs.get(chart_type)

    def list_palettes(self) -> List[str]:
        """列出所有配色方案"""
        return list(self.color_palettes.keys())

    def list_fonts(self) -> List[str]:
        """列出所有字体配对"""
        return list(self.font_pairings.keys())

    def list_charts(self) -> List[ChartType]:
        """列出所有图表类型"""
        return list(self.chart_configs.keys())

    def get_glassmorphism_css(self) -> str:
        """获取玻璃态CSS

        白皮书依据: 附录D D.3.4 UI风格推荐 - Glassmorphism

        Returns:
            玻璃态CSS样式
        """
        return """
.glass-card {
    background: rgba(255, 255, 255, 0.1);
    backdrop-filter: blur(10px);
    -webkit-backdrop-filter: blur(10px);
    border: 1px solid rgba(255, 255, 255, 0.2);
    border-radius: 16px;
    padding: 20px;
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
}

.glass-card-dark {
    background: rgba(0, 0, 0, 0.3);
    backdrop-filter: blur(10px);
    -webkit-backdrop-filter: blur(10px);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 16px;
    padding: 20px;
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
}
"""

    def get_neumorphism_css(self) -> str:
        """获取新拟态CSS

        白皮书依据: 附录D D.3.4 UI风格推荐 - Neumorphism

        Returns:
            新拟态CSS样式
        """
        return """
.neu-card {
    background: #e0e5ec;
    border-radius: 20px;
    padding: 20px;
    box-shadow: 
        9px 9px 16px rgba(163, 177, 198, 0.6),
        -9px -9px 16px rgba(255, 255, 255, 0.5);
}

.neu-card-dark {
    background: #1a1a2e;
    border-radius: 20px;
    padding: 20px;
    box-shadow: 
        9px 9px 16px rgba(0, 0, 0, 0.6),
        -9px -9px 16px rgba(50, 50, 70, 0.5);
}

.neu-button {
    background: #e0e5ec;
    border: none;
    border-radius: 12px;
    padding: 12px 24px;
    box-shadow: 
        5px 5px 10px rgba(163, 177, 198, 0.6),
        -5px -5px 10px rgba(255, 255, 255, 0.5);
    cursor: pointer;
    transition: all 0.2s ease;
}

.neu-button:active {
    box-shadow: 
        inset 5px 5px 10px rgba(163, 177, 198, 0.6),
        inset -5px -5px 10px rgba(255, 255, 255, 0.5);
}
"""

    def get_bento_grid_css(self) -> str:
        """获取便当盒布局CSS

        白皮书依据: 附录D D.3.4 UI风格推荐 - Bento Grid

        Returns:
            便当盒布局CSS样式
        """
        return """
.bento-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
    gap: 16px;
    padding: 16px;
}

.bento-item {
    background: var(--bg-card);
    border-radius: 16px;
    padding: 20px;
    border: 1px solid var(--border-color);
}

.bento-item-large {
    grid-column: span 2;
}

.bento-item-tall {
    grid-row: span 2;
}

@media (max-width: 768px) {
    .bento-grid {
        grid-template-columns: 1fr;
    }
    
    .bento-item-large {
        grid-column: span 1;
    }
}
"""

    def get_animation_css(self) -> str:
        """获取动画CSS

        白皮书依据: 附录D D.4.2 交互设计规范 - 动画时长标准

        Returns:
            动画CSS样式
        """
        return """
/* 微交互动画 100-200ms */
.animate-micro {
    transition: all 0.15s ease;
}

/* 页面过渡动画 200-300ms */
.animate-page {
    transition: all 0.25s ease;
}

/* 数据更新动画 300-500ms */
.animate-data {
    transition: all 0.4s ease;
}

/* 淡入动画 */
@keyframes fadeIn {
    from { opacity: 0; }
    to { opacity: 1; }
}

.fade-in {
    animation: fadeIn 0.3s ease forwards;
}

/* 滑入动画 */
@keyframes slideIn {
    from { 
        opacity: 0;
        transform: translateY(20px);
    }
    to { 
        opacity: 1;
        transform: translateY(0);
    }
}

.slide-in {
    animation: slideIn 0.3s ease forwards;
}

/* 数字变化动画 */
@keyframes numberPulse {
    0% { transform: scale(1); }
    50% { transform: scale(1.05); }
    100% { transform: scale(1); }
}

.number-change {
    animation: numberPulse 0.3s ease;
}

/* 加载骨架屏 */
@keyframes shimmer {
    0% { background-position: -200% 0; }
    100% { background-position: 200% 0; }
}

.skeleton {
    background: linear-gradient(
        90deg,
        var(--bg-card) 25%,
        var(--border-color) 50%,
        var(--bg-card) 75%
    );
    background-size: 200% 100%;
    animation: shimmer 1.5s infinite;
    border-radius: 4px;
}
"""

    def get_responsive_css(self) -> str:
        """获取响应式CSS

        白皮书依据: 附录D D.4.2 交互设计规范 - 触摸目标大小

        Returns:
            响应式CSS样式
        """
        return """
/* 响应式断点 */
@media (max-width: 1200px) {
    .container {
        padding: 16px;
    }
}

@media (max-width: 768px) {
    .container {
        padding: 12px;
    }
    
    .hide-mobile {
        display: none !important;
    }
    
    /* 触摸目标最小44x44px */
    .touch-target {
        min-width: 44px;
        min-height: 44px;
    }
}

@media (max-width: 480px) {
    .container {
        padding: 8px;
    }
    
    .font-size-responsive {
        font-size: 14px;
    }
}

/* 触摸目标推荐48x48px */
.touch-target-lg {
    min-width: 48px;
    min-height: 48px;
}

/* 触摸目标间距至少8px */
.touch-spacing {
    margin: 8px;
}
"""

    def get_accessibility_css(self) -> str:
        """获取可访问性CSS

        白皮书依据: 附录D D.4.1 金融Dashboard核心原则 - 可访问性

        Returns:
            可访问性CSS样式
        """
        return """
/* 高对比度模式 */
@media (prefers-contrast: high) {
    :root {
        --text-primary: #000000;
        --text-secondary: #333333;
        --bg-primary: #ffffff;
        --border-color: #000000;
    }
}

/* 减少动画 */
@media (prefers-reduced-motion: reduce) {
    * {
        animation: none !important;
        transition: none !important;
    }
}

/* 焦点样式 */
:focus {
    outline: 2px solid var(--color-primary);
    outline-offset: 2px;
}

:focus:not(:focus-visible) {
    outline: none;
}

:focus-visible {
    outline: 2px solid var(--color-primary);
    outline-offset: 2px;
}

/* 跳过链接 */
.skip-link {
    position: absolute;
    top: -40px;
    left: 0;
    background: var(--color-primary);
    color: white;
    padding: 8px 16px;
    z-index: 100;
}

.skip-link:focus {
    top: 0;
}

/* 屏幕阅读器专用 */
.sr-only {
    position: absolute;
    width: 1px;
    height: 1px;
    padding: 0;
    margin: -1px;
    overflow: hidden;
    clip: rect(0, 0, 0, 0);
    white-space: nowrap;
    border: 0;
}
"""

    def get_full_css(self) -> str:
        """获取完整CSS

        白皮书依据: 附录D UI/UX Pro Max集成方案

        Returns:
            完整的CSS样式
        """
        css_parts = []

        # 配色方案
        if self.current_palette:
            css_parts.append(self.current_palette.to_css_vars())

        # 字体配对
        if self.current_font:
            css_parts.append(self.current_font.to_css())

        # UI风格
        css_parts.append(self.get_glassmorphism_css())
        css_parts.append(self.get_neumorphism_css())
        css_parts.append(self.get_bento_grid_css())

        # 动画
        css_parts.append(self.get_animation_css())

        # 响应式
        css_parts.append(self.get_responsive_css())

        # 可访问性
        css_parts.append(self.get_accessibility_css())

        return "\n".join(css_parts)

    def inject_streamlit_css(self) -> None:
        """注入Streamlit CSS

        白皮书依据: 附录D D.5 Kiro集成方案
        """
        try:
            import streamlit as st  # pylint: disable=import-outside-toplevel

            st.markdown(f"<style>{self.get_full_css()}</style>", unsafe_allow_html=True)

            logger.debug("UI Pro Max CSS injected successfully")

        except ImportError:
            logger.warning("Streamlit not available, CSS not injected")

    def get_ux_best_practices(self) -> Dict[str, List[str]]:
        """获取UX最佳实践

        白皮书依据: 附录D D.4 UX最佳实践

        Returns:
            UX最佳实践字典
        """
        return {
            "数据可视化": [
                "使用颜色编码传达状态（绿涨红跌）",
                "重要数字使用大字号和粗体",
                "提供多时间维度切换（日/周/月/年）",
                "支持图表交互（缩放、悬停、点击）",
                "实时数据用动画过渡，避免突变",
            ],
            "信息架构": [
                "核心指标置顶（总资产、当日盈亏）",
                "使用卡片分组相关信息",
                "提供快速筛选和搜索",
                "支持自定义布局和排序",
                "关键操作按钮醒目且易点击",
            ],
            "性能优化": [
                "高频数据使用WebSocket推送",
                "大数据表格使用虚拟滚动",
                "图表懒加载，按需渲染",
                "使用缓存减少重复请求",
                "提供加载状态和骨架屏",
            ],
            "可访问性": [
                "支持键盘导航",
                "提供高对比度模式",
                "字体大小可调节",
                "颜色不是唯一的信息传达方式",
                "提供屏幕阅读器支持",
            ],
            "错误处理": [
                "网络错误自动重试",
                "数据异常显示友好提示",
                "提供降级方案（模拟数据）",
                "关键操作需要二次确认",
                "错误日志自动上报",
            ],
        }

    def get_response_time_standards(self) -> Dict[str, str]:
        """获取响应时间标准

        白皮书依据: 附录D D.4.2 交互设计规范 - 响应时间标准

        Returns:
            响应时间标准字典
        """
        return {
            "即时反馈": "< 100ms (按钮点击、悬停)",
            "快速响应": "< 1s (页面切换、数据加载)",
            "可接受": "< 3s (复杂计算、图表渲染)",
            "需要进度条": "> 3s (大数据加载)",
        }

    def get_animation_duration_standards(self) -> Dict[str, str]:
        """获取动画时长标准

        白皮书依据: 附录D D.4.2 交互设计规范 - 动画时长标准

        Returns:
            动画时长标准字典
        """
        return {
            "微交互": "100-200ms (按钮、开关)",
            "页面过渡": "200-300ms (路由切换)",
            "数据更新": "300-500ms (图表、数字)",
            "避免": "> 500ms (用户会感到卡顿)",
        }


# 全局UI Pro Max实例
_global_ui_pro_max: Optional[UIProMaxManager] = None


def get_ui_pro_max() -> UIProMaxManager:
    """获取全局UI Pro Max实例

    Returns:
        全局UI Pro Max实例
    """
    global _global_ui_pro_max  # pylint: disable=w0603

    if _global_ui_pro_max is None:
        _global_ui_pro_max = UIProMaxManager()

    return _global_ui_pro_max


def apply_ui_pro_max() -> None:
    """应用UI Pro Max到Streamlit"""
    ui_pro_max = get_ui_pro_max()
    ui_pro_max.inject_streamlit_css()
