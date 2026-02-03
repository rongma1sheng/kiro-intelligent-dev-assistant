"""可视化仪表盘

白皮书依据: 第五章 5.4 可视化系统
"""

from typing import Any, Dict, List, Optional

from loguru import logger

from src.brain.analyzers.data_models import (
    ComprehensiveAnalysisReport,
    KLineChartData,
    SectorCapitalFlowMonitoring,
    SectorFlowData,
    SectorFlowTrend,
    SectorRotationAnalysis,
)


class VisualizationDashboard:
    """可视化仪表盘

    白皮书依据: 第五章 5.4 可视化系统

    提供31种图表生成器（29种原有 + 2种新增）：
    1. 策略分析中心仪表盘
    2. 个股分析仪表盘（含结论性建议）
    3. K线图可视化系统（红涨绿跌）⭐新增
    4. 板块资金异动监控仪表盘 ⭐新增
    5. 其他29种分析维度图表

    Attributes:
        chart_generators: 图表生成器字典
        color_scheme: 色彩方案（红涨绿跌）
    """

    def __init__(self):
        """初始化可视化仪表盘"""
        self.chart_generators = self._init_chart_generators()
        self.color_scheme = self._init_color_scheme()

        logger.info("VisualizationDashboard initialized with 31 chart generators")

    def _init_color_scheme(self) -> Dict[str, str]:
        """初始化色彩方案（红涨绿跌 - 中国A股标准）

        白皮书依据: 第五章 5.4 可视化系统
        UI/UX依据: MIA_UI_UX_DESIGN_REQUIREMENTS.md

        Returns:
            色彩方案字典
        """
        return {
            # 上涨色（红色系）
            "rise_primary": "#FF4D4F",  # 主红色（涨停、强势上涨）
            "rise_secondary": "#FF7875",  # 次红色（普通上涨）
            "rise_light": "#FFA39E",  # 浅红色（微涨、背景）
            "rise_extra_light": "#FFCCC7",  # 极浅红（区间背景）
            # 下跌色（绿色系）
            "fall_primary": "#52C41A",  # 主绿色（跌停、强势下跌）
            "fall_secondary": "#73D13D",  # 次绿色（普通下跌）
            "fall_light": "#95DE64",  # 浅绿色（微跌、背景）
            "fall_extra_light": "#B7EB8F",  # 极浅绿（区间背景）
            # 中性色（灰色系）
            "neutral_dark": "#262626",  # 深灰（主要文字）
            "neutral_medium": "#595959",  # 中灰（次要文字）
            "neutral_light": "#8C8C8C",  # 浅灰（辅助文字）
            "neutral_extra_light": "#D9D9D9",  # 极浅灰（边框、分割线）
            "neutral_bg": "#F5F5F5",  # 背景灰（页面背景）
            # 功能色
            "primary_blue": "#1890FF",  # 主题蓝（链接、按钮）
            "warning_orange": "#FA8C16",  # 警告橙（警告、主力成本线）
            "danger_red": "#F5222D",  # 危险红（错误、风险）
            "success_green": "#52C41A",  # 成功绿（成功、确认）
            # 均线色彩
            "ma5_color": "#FFFFFF",  # MA5（白色）
            "ma10_color": "#FAAD14",  # MA10（黄色）
            "ma20_color": "#722ED1",  # MA20（紫色）
            "ma60_color": "#1890FF",  # MA60（蓝色）
            # 主力成本线
            "cost_line_color": "#FA8C16",  # 橙色虚线
        }

    def _init_chart_generators(self) -> Dict[str, callable]:
        """初始化图表生成器

        白皮书依据: 第五章 5.4 可视化系统

        Returns:
            图表生成器字典
        """
        return {
            # 核心仪表盘（4个）
            "strategy_dashboard": self.generate_strategy_dashboard,
            "stock_dashboard": self.generate_stock_dashboard,
            "kline_chart": self.generate_kline_chart,
            "sector_flow_dashboard": self.generate_sector_flow_dashboard,
            # 策略分析图表（10个）
            "strategy_essence_radar": self._generate_strategy_essence_radar,
            "risk_matrix_heatmap": self._generate_risk_matrix_heatmap,
            "feature_importance_chart": self._generate_feature_importance_chart,
            "market_adaptation_matrix": self._generate_market_adaptation_matrix,
            "evolution_process_chart": self._generate_evolution_process_chart,
            "overfitting_detection_chart": self._generate_overfitting_detection_chart,
            "decay_analysis_chart": self._generate_decay_analysis_chart,
            "capacity_curve_chart": self._generate_capacity_curve_chart,
            "stress_test_chart": self._generate_stress_test_chart,
            "signal_noise_chart": self._generate_signal_noise_chart,
            # 市场分析图表（8个）
            "macro_analysis_chart": self._generate_macro_analysis_chart,
            "microstructure_chart": self._generate_microstructure_chart,
            "sector_analysis_chart": self._generate_sector_analysis_chart,
            "sentiment_analysis_chart": self._generate_sentiment_analysis_chart,
            "retail_sentiment_chart": self._generate_retail_sentiment_chart,
            "sector_rotation_chart": self._generate_sector_rotation_chart,
            "capital_flow_chart": self._generate_capital_flow_chart,
            "market_regime_chart": self._generate_market_regime_chart,
            # 风险控制图表（7个）
            "risk_assessment_chart": self._generate_risk_assessment_chart,
            "stop_loss_optimization_chart": self._generate_stop_loss_optimization_chart,
            "slippage_analysis_chart": self._generate_slippage_analysis_chart,
            "transaction_cost_chart": self._generate_transaction_cost_chart,
            "position_sizing_chart": self._generate_position_sizing_chart,
            "correlation_matrix_chart": self._generate_correlation_matrix_chart,
            "portfolio_optimization_chart": self._generate_portfolio_optimization_chart,
            # 其他分析图表（6个）
            "trade_review_chart": self._generate_trade_review_chart,
            "nonstationarity_chart": self._generate_nonstationarity_chart,
            "regime_adaptation_chart": self._generate_regime_adaptation_chart,
            "factor_exposure_chart": self._generate_factor_exposure_chart,
            "smart_money_analysis_chart": self._generate_smart_money_analysis_chart,
            "stock_recommendation_card": self._generate_stock_recommendation_card,
        }

    # ========================================================================
    # 核心仪表盘生成方法
    # ========================================================================

    def generate_strategy_dashboard(self, analysis_report: ComprehensiveAnalysisReport) -> Dict[str, Any]:
        """生成策略分析中心仪表盘

        白皮书依据: 第五章 5.4.1 策略分析中心仪表盘

        Args:
            analysis_report: 综合分析报告

        Returns:
            仪表盘配置字典（ECharts格式）
        """
        logger.info(f"Generating strategy dashboard for {analysis_report.strategy_id}")

        dashboard = {
            "title": f"策略分析中心 - {analysis_report.strategy_id}",
            "overall_score": analysis_report.overall_score,
            "charts": {},
        }

        # 1. 策略本质雷达图
        if analysis_report.essence_report:
            dashboard["charts"]["essence_radar"] = self._generate_strategy_essence_radar(analysis_report.essence_report)

        # 2. 风险矩阵热力图
        if analysis_report.risk_report:
            dashboard["charts"]["risk_heatmap"] = self._generate_risk_matrix_heatmap(analysis_report.risk_report)

        # 3. 特征重要性排名
        if analysis_report.feature_report:
            dashboard["charts"]["feature_importance"] = self._generate_feature_importance_chart(
                analysis_report.feature_report
            )

        # 4. 市场适配性矩阵
        if analysis_report.essence_report:
            dashboard["charts"]["market_adaptation"] = self._generate_market_adaptation_matrix(
                analysis_report.essence_report
            )

        # 5. 进化过程可视化
        dashboard["charts"]["evolution_process"] = self._generate_evolution_process_chart(analysis_report)

        logger.info(f"Strategy dashboard generated with {len(dashboard['charts'])} charts")
        return dashboard

    def generate_stock_dashboard(
        self, symbol: str, analysis_report: ComprehensiveAnalysisReport, kline_data: Optional[KLineChartData] = None
    ) -> Dict[str, Any]:
        """生成个股分析仪表盘（含结论性建议）

        白皮书依据: 第五章 5.4.2 个股分析仪表盘

        Args:
            symbol: 股票代码
            analysis_report: 综合分析报告
            kline_data: K线图数据（可选）

        Returns:
            仪表盘配置字典
        """
        logger.info(f"Generating stock dashboard for {symbol}")

        dashboard = {"symbol": symbol, "title": f"个股分析 - {symbol}", "sections": {}}

        # 1. 结论性建议卡片
        if analysis_report.recommendation:
            dashboard["sections"]["recommendation"] = self._generate_stock_recommendation_card(
                analysis_report.recommendation
            )

        # 2. 主力资金深度分析
        if analysis_report.smart_money_report:
            dashboard["sections"]["smart_money"] = self._generate_smart_money_analysis_chart(
                analysis_report.smart_money_report
            )

        # 3. K线图与技术分析
        if kline_data:
            dashboard["sections"]["kline_chart"] = self.generate_kline_chart(kline_data)

        logger.info(f"Stock dashboard generated for {symbol}")
        return dashboard

    def generate_kline_chart(self, kline_data: KLineChartData) -> Dict[str, Any]:
        """生成K线图（红涨绿跌）⭐新增

        白皮书依据: 第五章 5.4.4 K线图可视化系统
        UI/UX依据: MIA_UI_UX_DESIGN_REQUIREMENTS.md

        Args:
            kline_data: K线图数据

        Returns:
            K线图配置字典（ECharts格式）
        """
        logger.info(f"Generating K-line chart for {kline_data.symbol} ({kline_data.period})")

        # 提取日期和K线数据
        dates = [k.date.strftime("%Y-%m-%d") for k in kline_data.klines]
        kline_values = [[k.open, k.close, k.low, k.high] for k in kline_data.klines]  # ECharts candlestick格式

        # 构建ECharts配置
        chart_config = {
            "title": {"text": f"{kline_data.name} ({kline_data.symbol}) - {kline_data.period}", "left": "center"},
            "tooltip": {
                "trigger": "axis",
                "axisPointer": {"type": "cross"},
                "formatter": self._kline_tooltip_formatter(),
            },
            "legend": {"data": ["K线", "MA5", "MA10", "MA20", "MA60", "主力成本线"], "top": 30},
            "grid": [
                {"left": "10%", "right": "10%", "top": "15%", "height": "50%"},
                {"left": "10%", "right": "10%", "top": "70%", "height": "15%"},
            ],
            "xAxis": [
                {
                    "type": "category",
                    "data": dates,
                    "scale": True,
                    "boundaryGap": False,
                    "axisLine": {"onZero": False},
                    "splitLine": {"show": False},
                    "min": "dataMin",
                    "max": "dataMax",
                },
                {
                    "type": "category",
                    "gridIndex": 1,
                    "data": dates,
                    "scale": True,
                    "boundaryGap": False,
                    "axisLine": {"onZero": False},
                    "axisTick": {"show": False},
                    "splitLine": {"show": False},
                    "axisLabel": {"show": False},
                    "min": "dataMin",
                    "max": "dataMax",
                },
            ],
            "yAxis": [
                {"scale": True, "splitArea": {"show": True}},
                {
                    "scale": True,
                    "gridIndex": 1,
                    "splitNumber": 2,
                    "axisLabel": {"show": False},
                    "axisLine": {"show": False},
                    "axisTick": {"show": False},
                    "splitLine": {"show": False},
                },
            ],
            "dataZoom": [
                {"type": "inside", "xAxisIndex": [0, 1], "start": 50, "end": 100},
                {"show": True, "xAxisIndex": [0, 1], "type": "slider", "bottom": "5%", "start": 50, "end": 100},
            ],
            "series": [],
        }

        # 添加K线系列
        chart_config["series"].append(
            {
                "name": "K线",
                "type": "candlestick",
                "data": kline_values,
                "itemStyle": {
                    "color": self.color_scheme["rise_primary"],  # 上涨K线（红色）
                    "color0": self.color_scheme["fall_primary"],  # 下跌K线（绿色）
                    "borderColor": self.color_scheme["rise_primary"],
                    "borderColor0": self.color_scheme["fall_primary"],
                },
            }
        )

        # 添加均线系列
        for period, ma_data in kline_data.ma_lines.items():
            chart_config["series"].append(
                {
                    "name": f"MA{period}",
                    "type": "line",
                    "data": ma_data,
                    "smooth": True,
                    "lineStyle": {"width": 1.5, "color": self.color_scheme.get(f"ma{period}_color", "#FFFFFF")},
                    "showSymbol": False,
                }
            )

        # 添加主力成本线
        if kline_data.main_force_cost_line:
            cost_line = kline_data.main_force_cost_line
            chart_config["series"].append(
                {
                    "name": "主力成本线",
                    "type": "line",
                    "data": [cost_line.cost_basis] * len(dates),
                    "lineStyle": {"width": 2, "type": "dashed", "color": self.color_scheme["cost_line_color"]},
                    "markArea": {
                        "itemStyle": {"color": f"rgba(250, 140, 22, 0.1)"},  # 成本区间阴影  # pylint: disable=w1309
                        "data": [[{"yAxis": cost_line.cost_range_lower}, {"yAxis": cost_line.cost_range_upper}]],
                    },
                    "showSymbol": False,
                }
            )

        # 添加买卖点标注
        if kline_data.buy_signals:
            buy_points = [
                {
                    "coord": [s.date.strftime("%Y-%m-%d"), s.price],
                    "value": "B",
                    "itemStyle": {"color": self.color_scheme["success_green"]},
                }
                for s in kline_data.buy_signals
            ]
            chart_config["series"][0]["markPoint"] = {
                "symbol": "arrow",
                "symbolSize": 16,
                "symbolRotate": 180,
                "data": buy_points,
            }

        if kline_data.sell_signals:
            sell_points = [
                {
                    "coord": [s.date.strftime("%Y-%m-%d"), s.price],
                    "value": "S",
                    "itemStyle": {"color": self.color_scheme["danger_red"]},
                }
                for s in kline_data.sell_signals
            ]
            if "markPoint" in chart_config["series"][0]:
                chart_config["series"][0]["markPoint"]["data"].extend(sell_points)
            else:
                chart_config["series"][0]["markPoint"] = {"symbol": "arrow", "symbolSize": 16, "data": sell_points}

        # 添加成交量系列
        volume_data = [v.volume for v in kline_data.volumes]
        volume_colors = [
            self.color_scheme["rise_primary"] if v.color == "red" else self.color_scheme["fall_primary"]
            for v in kline_data.volumes
        ]

        chart_config["series"].append(
            {
                "name": "成交量",
                "type": "bar",
                "xAxisIndex": 1,
                "yAxisIndex": 1,
                "data": volume_data,
                "itemStyle": {"color": lambda params: volume_colors[params.dataIndex]},
            }
        )

        logger.info(f"K-line chart generated with {len(kline_data.klines)} candles")
        return chart_config

    def _kline_tooltip_formatter(self) -> str:
        """K线图悬停提示格式化器

        Returns:
            JavaScript格式化函数字符串
        """
        return """
        function(params) {
            var data = params[0].data;
            return '日期: ' + params[0].name + '<br/>' +
                   '开盘: ' + data[0] + '<br/>' +
                   '收盘: ' + data[1] + '<br/>' +
                   '最低: ' + data[2] + '<br/>' +
                   '最高: ' + data[3] + '<br/>' +
                   '涨跌幅: ' + ((data[1] - data[0]) / data[0] * 100).toFixed(2) + '%';
        }
        """

    def generate_sector_flow_dashboard(self, flow_data: SectorCapitalFlowMonitoring) -> Dict[str, Any]:
        """生成板块资金异动监控仪表盘 ⭐新增

        白皮书依据: 第五章 5.4.3 板块资金异动监控仪表盘

        Args:
            flow_data: 板块资金流向监控数据

        Returns:
            仪表盘配置字典
        """
        logger.info(f"Generating sector flow dashboard for {flow_data.timestamp}")

        dashboard = {
            "title": f'板块资金异动监控 - {flow_data.timestamp.strftime("%Y-%m-%d %H:%M")}',
            "period": flow_data.period,
            "sections": {},
        }

        # 1. 热点板块（资金净流入TOP10）
        dashboard["sections"]["top_inflow"] = self._generate_top_inflow_sectors_table(flow_data.top_inflow_sectors)

        # 2. 资金流出板块（资金净流出TOP10）
        dashboard["sections"]["top_outflow"] = self._generate_top_outflow_sectors_table(flow_data.top_outflow_sectors)

        # 3. 板块资金流向热力图
        dashboard["sections"]["flow_heatmap"] = self._generate_sector_flow_heatmap(
            flow_data.top_inflow_sectors + flow_data.top_outflow_sectors
        )

        # 4. 板块轮动分析
        dashboard["sections"]["rotation_analysis"] = self._generate_sector_rotation_analysis_card(
            flow_data.rotation_analysis
        )

        # 5. 板块资金流向趋势
        dashboard["sections"]["flow_trends"] = self._generate_sector_flow_trends_chart(flow_data.flow_trends)

        logger.info(f"Sector flow dashboard generated with {len(dashboard['sections'])} sections")
        return dashboard

    def _generate_top_inflow_sectors_table(self, sectors: List[SectorFlowData]) -> Dict[str, Any]:
        """生成热点板块表格

        Args:
            sectors: 板块流向数据列表

        Returns:
            表格配置字典
        """
        table_data = []
        for rank, sector in enumerate(sectors[:10], 1):
            table_data.append(
                {
                    "rank": rank,
                    "sector_name": sector.sector_name,
                    "net_inflow": f"+{sector.net_inflow:.1f}亿",
                    "price_change_pct": f"+{sector.price_change_pct:.2f}%",
                    "leading_stock": sector.leading_stocks[0].name if sector.leading_stocks else "-",
                    "stock_count": sector.stock_count,
                    "rising_count": sector.rising_stock_count,
                }
            )

        return {
            "type": "table",
            "title": "🔥 今日热点板块（资金净流入TOP10）",
            "columns": ["排名", "板块名称", "净流入", "涨幅", "领涨股", "股票数", "上涨数"],
            "data": table_data,
        }

    def _generate_top_outflow_sectors_table(self, sectors: List[SectorFlowData]) -> Dict[str, Any]:
        """生成资金流出板块表格

        Args:
            sectors: 板块流向数据列表

        Returns:
            表格配置字典
        """
        table_data = []
        for rank, sector in enumerate(sectors[:10], 1):
            table_data.append(
                {
                    "rank": rank,
                    "sector_name": sector.sector_name,
                    "net_outflow": f"{sector.net_inflow:.1f}亿",  # 负值
                    "price_change_pct": f"{sector.price_change_pct:.2f}%",
                    "leading_stock": sector.leading_stocks[0].name if sector.leading_stocks else "-",
                    "stock_count": sector.stock_count,
                    "falling_count": sector.falling_stock_count,
                }
            )

        return {
            "type": "table",
            "title": "❄️ 资金流出板块（资金净流出TOP10）",
            "columns": ["排名", "板块名称", "净流出", "跌幅", "领跌股", "股票数", "下跌数"],
            "data": table_data,
        }

    def _generate_sector_flow_heatmap(self, sectors: List[SectorFlowData]) -> Dict[str, Any]:
        """生成板块资金流向热力图

        Args:
            sectors: 板块流向数据列表

        Returns:
            热力图配置字典（ECharts格式）
        """
        # 准备热力图数据
        sector_names = [s.sector_name for s in sectors]
        heatmap_data = [[i, 0, s.net_inflow] for i, s in enumerate(sectors)]

        # 计算色彩映射范围
        max_inflow = max([s.net_inflow for s in sectors if s.net_inflow > 0], default=100)  # pylint: disable=r1728
        max_outflow = abs(
            min([s.net_inflow for s in sectors if s.net_inflow < 0], default=-50)  # pylint: disable=r1728
        )  # pylint: disable=r1728

        chart_config = {
            "title": {"text": "📊 板块资金流向热力图（红=流入 绿=流出）", "left": "center"},
            "tooltip": {
                "position": "top",
                "formatter": lambda params: f"{sector_names[params['value'][0]]}<br/>净流入: {params['value'][2]:.1f}亿",
            },
            "grid": {"height": "50%", "top": "10%"},
            "xAxis": {
                "type": "category",
                "data": sector_names,
                "splitArea": {"show": True},
                "axisLabel": {"rotate": 45, "interval": 0},
            },
            "yAxis": {"type": "category", "data": ["资金流向"], "splitArea": {"show": True}},
            "visualMap": {
                "min": -max_outflow,
                "max": max_inflow,
                "calculable": True,
                "orient": "horizontal",
                "left": "center",
                "bottom": "15%",
                "inRange": {
                    "color": [
                        self.color_scheme["fall_primary"],  # 深绿（大量流出）
                        self.color_scheme["fall_light"],  # 浅绿（少量流出）
                        self.color_scheme["neutral_extra_light"],  # 灰色（中性）
                        self.color_scheme["rise_light"],  # 浅红（少量流入）
                        self.color_scheme["rise_primary"],  # 深红（大量流入）
                    ]
                },
            },
            "series": [
                {
                    "name": "资金流向",
                    "type": "heatmap",
                    "data": heatmap_data,
                    "label": {
                        "show": True,
                        "formatter": lambda params: (
                            f"+{params['value'][2]:.1f}亿" if params["value"][2] > 0 else f"{params['value'][2]:.1f}亿"
                        ),
                    },
                    "emphasis": {"itemStyle": {"shadowBlur": 10, "shadowColor": "rgba(0, 0, 0, 0.5)"}},
                }
            ],
        }

        return chart_config

    def _generate_sector_rotation_analysis_card(self, rotation_analysis: SectorRotationAnalysis) -> Dict[str, Any]:
        """生成板块轮动分析卡片

        Args:
            rotation_analysis: 板块轮动分析数据

        Returns:
            卡片配置字典
        """
        return {
            "type": "card",
            "title": "🔄 板块轮动分析",
            "content": {
                "current_stage": rotation_analysis.current_stage,
                "dominant_sectors": rotation_analysis.dominant_sectors,
                "rotation_prediction": rotation_analysis.rotation_prediction,
                "confidence": f"{rotation_analysis.confidence * 100:.0f}%",
                "allocation_suggestion": rotation_analysis.allocation_suggestion,
            },
        }

    def _generate_sector_flow_trends_chart(self, flow_trends: Dict[str, SectorFlowTrend]) -> Dict[str, Any]:
        """生成板块资金流向趋势图

        Args:
            flow_trends: 板块资金流向趋势字典

        Returns:
            趋势图配置字典（ECharts格式）
        """
        chart_config = {
            "title": {"text": "📈 板块资金流向趋势", "left": "center"},
            "tooltip": {"trigger": "axis"},
            "legend": {"data": list(flow_trends.keys()), "top": 30},
            "grid": {"left": "3%", "right": "4%", "bottom": "3%", "containLabel": True},
            "xAxis": {
                "type": "category",
                "boundaryGap": False,
                "data": [
                    f"Day {i+1}"
                    for i in range(max([len(t.daily_flows) for t in flow_trends.values()]))  # pylint: disable=r1728
                ],  # pylint: disable=r1728
            },
            "yAxis": {"type": "value", "name": "累计净流入（亿元）"},
            "series": [],
        }

        for sector_name, trend in flow_trends.items():
            # 根据趋势方向选择颜色
            if trend.trend_direction == "inflow":
                line_color = self.color_scheme["rise_primary"]
            elif trend.trend_direction == "outflow":
                line_color = self.color_scheme["fall_primary"]
            else:
                line_color = self.color_scheme["neutral_light"]

            chart_config["series"].append(
                {
                    "name": sector_name,
                    "type": "line",
                    "data": trend.daily_flows,
                    "smooth": True,
                    "lineStyle": {"color": line_color, "width": 2},
                    "areaStyle": {"opacity": 0.1},
                }
            )

        return chart_config

    # ========================================================================
    # 策略分析图表生成方法（10个）
    # ========================================================================

    def _generate_strategy_essence_radar(self, essence_report) -> Dict[str, Any]:  # pylint: disable=unused-argument
        """生成策略本质雷达图"""
        # PRD-REQ: 实现策略本质雷达图 (白皮书 5.4.5 可视化图表完整列表)
        return {"type": "radar", "title": "策略本质雷达图"}

    def _generate_risk_matrix_heatmap(self, risk_report) -> Dict[str, Any]:  # pylint: disable=unused-argument
        """生成风险矩阵热力图"""
        # PRD-REQ: 实现风险矩阵热力图 (白皮书 5.4.5 可视化图表完整列表)
        return {"type": "heatmap", "title": "风险矩阵热力图"}

    def _generate_feature_importance_chart(self, feature_report) -> Dict[str, Any]:  # pylint: disable=unused-argument
        """生成特征重要性排名图"""
        # PRD-REQ: 实现特征重要性排名图 (白皮书 5.4.5 可视化图表完整列表)
        return {"type": "bar", "title": "特征重要性排名"}

    def _generate_market_adaptation_matrix(self, essence_report) -> Dict[str, Any]:  # pylint: disable=unused-argument
        """生成市场适配性矩阵"""
        # PRD-REQ: 实现市场适配性矩阵 (白皮书 5.4.5 可视化图表完整列表)
        return {"type": "matrix", "title": "市场适配性矩阵"}

    def _generate_evolution_process_chart(self, analysis_report) -> Dict[str, Any]:  # pylint: disable=unused-argument
        """生成进化过程可视化图"""
        # PRD-REQ: 实现进化过程可视化图 (白皮书 5.4.1 策略分析中心仪表盘)
        return {"type": "line", "title": "进化过程可视化"}

    def _generate_overfitting_detection_chart(
        self, overfitting_report  # pylint: disable=unused-argument
    ) -> Dict[str, Any]:  # pylint: disable=unused-argument
        """生成过拟合检测图"""
        # PRD-REQ: 实现过拟合检测图 (白皮书 5.4.5 可视化图表完整列表)
        return {"type": "scatter", "title": "过拟合检测"}

    def _generate_decay_analysis_chart(self, decay_report) -> Dict[str, Any]:  # pylint: disable=unused-argument
        """生成策略衰减分析图"""
        # PRD-REQ: 实现策略衰减分析图 (白皮书 5.4.5 可视化图表完整列表)
        return {"type": "line", "title": "策略衰减分析"}

    def _generate_capacity_curve_chart(self, capacity_report) -> Dict[str, Any]:  # pylint: disable=unused-argument
        """生成资金容量曲线图"""
        # PRD-REQ: 实现资金容量曲线图 (白皮书 5.4.5 可视化图表完整列表)
        return {"type": "line", "title": "资金容量曲线"}

    def _generate_stress_test_chart(self, stress_test_report) -> Dict[str, Any]:  # pylint: disable=unused-argument
        """生成压力测试图"""
        # PRD-REQ: 实现压力测试图 (白皮书 5.4.5 可视化图表完整列表)
        return {"type": "bar", "title": "压力测试"}

    def _generate_signal_noise_chart(self, signal_noise_report) -> Dict[str, Any]:  # pylint: disable=unused-argument
        """生成信噪比分析图"""
        # PRD-REQ: 实现信噪比分析图 (白皮书 5.4.5 可视化图表完整列表)
        return {"type": "gauge", "title": "信噪比分析"}

    # ========================================================================
    # 市场分析图表生成方法（8个）
    # ========================================================================

    def _generate_macro_analysis_chart(self, macro_report) -> Dict[str, Any]:  # pylint: disable=unused-argument
        """生成宏观分析图"""
        # PRD-REQ: 实现宏观分析图 (白皮书 5.4.5 可视化图表完整列表)
        return {"type": "mixed", "title": "宏观分析"}

    def _generate_microstructure_chart(
        self, microstructure_report  # pylint: disable=unused-argument
    ) -> Dict[str, Any]:  # pylint: disable=unused-argument
        """生成市场微观结构图"""
        # PRD-REQ: 实现市场微观结构图 (白皮书 5.4.5 可视化图表完整列表)
        return {"type": "bar", "title": "市场微观结构"}

    def _generate_sector_analysis_chart(self, sector_report) -> Dict[str, Any]:  # pylint: disable=unused-argument
        """生成行业板块分析图"""
        # PRD-REQ: 实现行业板块分析图 (白皮书 5.4.5 可视化图表完整列表)
        return {"type": "treemap", "title": "行业板块分析"}

    def _generate_sentiment_analysis_chart(self, sentiment_report) -> Dict[str, Any]:  # pylint: disable=unused-argument
        """生成市场情绪分析图"""
        # PRD-REQ: 实现市场情绪分析图 (白皮书 5.4.5 可视化图表完整列表)
        return {"type": "gauge", "title": "市场情绪分析"}

    def _generate_retail_sentiment_chart(
        self, retail_sentiment_report  # pylint: disable=unused-argument
    ) -> Dict[str, Any]:  # pylint: disable=unused-argument
        """生成散户情绪分析图"""
        # PRD-REQ: 实现散户情绪分析图 (白皮书 5.4.5 可视化图表完整列表)
        return {"type": "gauge", "title": "散户情绪分析"}

    def _generate_sector_rotation_chart(self, sector_report) -> Dict[str, Any]:  # pylint: disable=unused-argument
        """生成板块轮动图"""
        # PRD-REQ: 实现板块轮动图 (白皮书 5.4.5 可视化图表完整列表)
        return {"type": "sankey", "title": "板块轮动"}

    def _generate_capital_flow_chart(self, sector_report) -> Dict[str, Any]:  # pylint: disable=unused-argument
        """生成资金流向图"""
        # PRD-REQ: 实现资金流向图 (白皮书 5.4.5 可视化图表完整列表)
        return {"type": "bar", "title": "资金流向"}

    def _generate_market_regime_chart(self, macro_report) -> Dict[str, Any]:  # pylint: disable=unused-argument
        """生成市场状态图"""
        # PRD-REQ: 实现市场状态图 (白皮书 5.4.5 可视化图表完整列表)
        return {"type": "timeline", "title": "市场状态"}

    # ========================================================================
    # 风险控制图表生成方法（7个）
    # ========================================================================

    def _generate_risk_assessment_chart(self, risk_report) -> Dict[str, Any]:  # pylint: disable=unused-argument
        """生成风险评估图"""
        # PRD-REQ: 实现风险评估图 (白皮书 5.4.5 可视化图表完整列表)
        return {"type": "radar", "title": "风险评估"}

    def _generate_stop_loss_optimization_chart(
        self, stop_loss_report  # pylint: disable=unused-argument
    ) -> Dict[str, Any]:  # pylint: disable=unused-argument
        """生成止损优化图"""
        # PRD-REQ: 实现止损优化图 (白皮书 5.4.5 可视化图表完整列表)
        return {"type": "line", "title": "止损优化"}

    def _generate_slippage_analysis_chart(self, slippage_report) -> Dict[str, Any]:  # pylint: disable=unused-argument
        """生成滑点分析图"""
        # PRD-REQ: 实现滑点分析图 (白皮书 5.4.5 可视化图表完整列表)
        return {"type": "box", "title": "滑点分析"}

    def _generate_transaction_cost_chart(
        self, transaction_cost_report  # pylint: disable=unused-argument
    ) -> Dict[str, Any]:  # pylint: disable=unused-argument
        """生成交易成本图"""
        # PRD-REQ: 实现交易成本图 (白皮书 5.4.5 可视化图表完整列表)
        return {"type": "pie", "title": "交易成本"}

    def _generate_position_sizing_chart(
        self, position_sizing_report  # pylint: disable=unused-argument
    ) -> Dict[str, Any]:  # pylint: disable=unused-argument
        """生成仓位管理图"""
        # PRD-REQ: 实现仓位管理图 (白皮书 5.4.5 可视化图表完整列表)
        return {"type": "bar", "title": "仓位管理"}

    def _generate_correlation_matrix_chart(
        self, correlation_report  # pylint: disable=unused-argument
    ) -> Dict[str, Any]:  # pylint: disable=unused-argument
        """生成相关性矩阵图"""
        # PRD-REQ: 实现相关性矩阵图 (白皮书 5.4.5 可视化图表完整列表)
        return {"type": "heatmap", "title": "相关性矩阵"}

    def _generate_portfolio_optimization_chart(
        self, portfolio_optimization_report  # pylint: disable=unused-argument
    ) -> Dict[str, Any]:  # pylint: disable=unused-argument
        """生成投资组合优化图"""
        # PRD-REQ: 实现投资组合优化图 (白皮书 5.4.5 可视化图表完整列表)
        return {"type": "scatter", "title": "投资组合优化"}

    # ========================================================================
    # 其他分析图表生成方法（6个）
    # ========================================================================

    def _generate_trade_review_chart(self, trade_review_report) -> Dict[str, Any]:  # pylint: disable=unused-argument
        """生成交易复盘图"""
        # PRD-REQ: 实现交易复盘图 (白皮书 5.4.5 可视化图表完整列表)
        return {"type": "timeline", "title": "交易复盘"}

    def _generate_nonstationarity_chart(
        self, nonstationarity_report  # pylint: disable=unused-argument
    ) -> Dict[str, Any]:  # pylint: disable=unused-argument
        """生成非平稳性分析图"""
        # PRD-REQ: 实现非平稳性分析图 (白皮书 5.4.5 可视化图表完整列表)
        return {"type": "line", "title": "非平稳性分析"}

    def _generate_regime_adaptation_chart(
        self, regime_adaptation_report  # pylint: disable=unused-argument
    ) -> Dict[str, Any]:  # pylint: disable=unused-argument
        """生成市场状态适应图"""
        # PRD-REQ: 实现市场状态适应图 (白皮书 5.4.5 可视化图表完整列表)
        return {"type": "matrix", "title": "市场状态适应"}

    def _generate_factor_exposure_chart(
        self, factor_exposure_report  # pylint: disable=unused-argument
    ) -> Dict[str, Any]:  # pylint: disable=unused-argument
        """生成因子暴露图"""
        # PRD-REQ: 实现因子暴露图 (白皮书 5.4.5 可视化图表完整列表)
        return {"type": "bar", "title": "因子暴露"}

    def _generate_smart_money_analysis_chart(
        self, smart_money_report  # pylint: disable=unused-argument
    ) -> Dict[str, Any]:  # pylint: disable=unused-argument
        """生成主力资金分析图"""
        # PRD-REQ: 实现主力资金分析图 (白皮书 5.4.5 可视化图表完整列表)
        return {"type": "mixed", "title": "主力资金分析"}

    def _generate_stock_recommendation_card(self, recommendation) -> Dict[str, Any]:
        """生成个股结论性建议卡片"""
        return {
            "type": "card",
            "title": "🎯 结论性建议",
            "content": {
                "action": recommendation.action.value,
                "confidence": f"{recommendation.confidence * 100:.0f}%",
                "entry_price": recommendation.entry_price,
                "stop_loss": recommendation.stop_loss,
                "target_price": recommendation.target_price,
                "position_size": recommendation.position_size.value,
                "holding_period": recommendation.holding_period.value,
                "reasons": recommendation.reasons,
                "risks": recommendation.risks,
            },
        }
