"""多账户管理仪表盘

白皮书依据: 第十七章 17.3.1 多账户管理系统
UI依据: 附录A 7.5 多账户管理

核心功能:
- 账户总览（总资产、可用资金、持仓市值、今日盈亏）
- 账户列表（状态、资产、操作）
- 账户添加表单
- 路由策略配置
- 健康监控
"""

import asyncio
from typing import Any, Optional

import plotly.express as px
import streamlit as st
from loguru import logger

from src.evolution.qmt_broker_api import QMTConnectionConfig
from src.execution.multi_account_data_models import AccountConfig
from src.execution.multi_account_manager import MultiAccountManager

# ==================== 色彩常量（红涨绿跌） ====================
COLOR_UP = "#FF4D4F"  # 上涨红
COLOR_DOWN = "#52C41A"  # 下跌绿
COLOR_NEUTRAL = "#8C8C8C"  # 中性灰
COLOR_HEALTHY = "#52C41A"  # 健康绿
COLOR_WARNING = "#FA8C16"  # 警告橙
COLOR_ERROR = "#F5222D"  # 错误红
COLOR_PRIMARY = "#1890FF"  # 主题蓝


class MultiAccountDashboard:
    """多账户管理仪表盘

    白皮书依据: 第十七章 17.3.1 多账户管理系统

    Attributes:
        manager: 多账户管理器实例
        redis_client: Redis客户端（可选）
    """

    def __init__(self, manager: Optional[MultiAccountManager] = None, redis_client: Optional[Any] = None):
        """初始化仪表盘

        Args:
            manager: 多账户管理器实例
            redis_client: Redis客户端
        """
        self.manager = manager or MultiAccountManager()
        self.redis_client = redis_client

        logger.info("初始化多账户管理仪表盘")

    def render(self) -> None:
        """渲染完整仪表盘

        白皮书依据: 附录A 7.5 多账户管理
        """
        st.title("💼 多账户管理中心")
        st.caption("白皮书依据: 第十七章 17.3.1 多账户管理系统")

        # 账户总览
        self._render_account_overview()

        st.divider()

        # 账户列表和操作
        col1, col2 = st.columns([2, 1])

        with col1:
            self._render_account_list()

        with col2:
            self._render_routing_config()

        st.divider()

        # 添加账户表单
        self._render_add_account_form()

    def _render_account_overview(self) -> None:
        """渲染账户总览

        显示所有账户的汇总信息
        """
        st.subheader("📊 账户总览")

        # 获取健康检查数据
        health_data = asyncio.run(self.manager.health_check())

        # 计算汇总数据
        total_assets = health_data.get("total_assets", 0)
        total_accounts = health_data.get("total_accounts", 0)
        healthy_accounts = health_data.get("healthy_accounts", 0)
        warning_accounts = health_data.get("warning_accounts", 0)
        error_accounts = health_data.get("error_accounts", 0)

        # 从详情中计算更多数据
        details = health_data.get("details", [])
        available_cash = sum(d.get("available_cash", 0) for d in details)
        market_value = sum(d.get("market_value", 0) for d in details)
        today_pnl = sum(d.get("today_pnl", 0) for d in details)

        # 显示指标卡片
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric(label="总资产", value=f"¥{total_assets:,.0f}", delta=None)

        with col2:
            st.metric(label="可用资金", value=f"¥{available_cash:,.0f}", delta=None)

        with col3:
            st.metric(label="持仓市值", value=f"¥{market_value:,.0f}", delta=None)

        with col4:
            pnl_color = "normal" if today_pnl >= 0 else "inverse"
            pnl_prefix = "+" if today_pnl >= 0 else ""
            st.metric(
                label="今日盈亏",
                value=f"¥{today_pnl:,.0f}",
                delta=f"{pnl_prefix}{today_pnl/total_assets*100:.2f}%" if total_assets > 0 else "0%",
                delta_color=pnl_color,
            )

        # 账户状态统计
        st.markdown(
            f"**账户状态**: "
            f"🟢 {healthy_accounts}健康 "
            f"🟡 {warning_accounts}警告 "
            f"🔴 {error_accounts}错误 "
            f"(共{total_accounts}个账户)"
        )

    def _render_account_list(self) -> None:
        """渲染账户列表

        显示所有账户的详细信息和操作按钮
        """
        st.subheader("📋 账户列表")

        # 获取所有账户状态
        status_dict = asyncio.run(self.manager.get_all_account_status())

        if not status_dict:
            st.info("暂无账户，请添加账户")
            return

        # 构建表格数据
        table_data = []
        for account_id, status in status_dict.items():
            config = self.manager.account_configs.get(account_id)

            # 状态图标
            if status.health_status == "healthy":
                status_icon = "🟢"
            elif status.health_status == "warning":
                status_icon = "🟡"
            else:
                status_icon = "🔴"

            # 盈亏颜色
            pnl_str = f"+¥{status.today_pnl:,.0f}" if status.today_pnl >= 0 else f"¥{status.today_pnl:,.0f}"

            table_data.append(
                {
                    "账户ID": account_id,
                    "券商": status.broker_name,
                    "类型": config.account_type if config else "未知",
                    "状态": status_icon,
                    "总资产": f"¥{status.total_assets:,.0f}",
                    "可用资金": f"¥{status.available_cash:,.0f}",
                    "今日盈亏": pnl_str,
                    "优先级": config.priority if config else 5,
                    "持仓数": status.position_count,
                }
            )

        # 显示表格
        st.dataframe(table_data, use_container_width=True, hide_index=True)

        # 账户操作
        st.markdown("**账户操作**")

        col1, col2, col3 = st.columns(3)

        with col1:
            selected_account = st.selectbox("选择账户", options=list(status_dict.keys()), key="account_select")

        with col2:
            if st.button("🔄 刷新状态", key="refresh_status"):
                st.rerun()

        with col3:
            if st.button("🗑️ 移除账户", key="remove_account"):
                if selected_account:
                    asyncio.run(self.manager.remove_account(selected_account))
                    st.success(f"已移除账户: {selected_account}")
                    st.rerun()

    def _render_routing_config(self) -> None:
        """渲染路由策略配置

        显示当前路由策略和订单分布
        """
        st.subheader("🔀 路由策略")

        # 路由策略选择
        strategy_options = {
            "balanced": "均衡分配",
            "priority": "优先级优先",
            "capacity": "容量优先",
            "hash": "哈希分片",
        }

        current_strategy = self.manager.routing_strategy

        new_strategy = st.selectbox(
            "当前策略",
            options=list(strategy_options.keys()),
            format_func=lambda x: strategy_options[x],
            index=list(strategy_options.keys()).index(current_strategy),
            key="routing_strategy_select",
        )

        if new_strategy != current_strategy:
            self.manager.routing_strategy = new_strategy
            st.success(f"路由策略已更新为: {strategy_options[new_strategy]}")

        # 路由统计
        stats = self.manager.get_routing_stats()

        st.metric(label="总路由订单数", value=stats["total_orders"])

        # 订单分布饼图
        distribution = stats.get("distribution", {})

        if distribution:
            fig = px.pie(
                values=list(distribution.values()),
                names=list(distribution.keys()),
                title="订单分布",
                color_discrete_sequence=px.colors.qualitative.Set3,
            )
            fig.update_layout(height=250, margin=dict(l=20, r=20, t=40, b=20))  # pylint: disable=r1735
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("暂无路由记录")

    def _render_add_account_form(self) -> None:
        """渲染添加账户表单"""
        st.subheader("➕ 添加账户")

        with st.form("add_account_form"):
            col1, col2 = st.columns(2)

            with col1:
                broker_name = st.selectbox("券商", options=["国金", "华泰", "中信", "国泰君安"], key="broker_select")

                account_id = st.text_input("账户ID", placeholder="例如: guojin_qmt_001", key="account_id_input")

                account_type = st.selectbox("账户类型", options=["模拟盘", "实盘"], key="account_type_select")

                qmt_account = st.text_input("QMT资金账号", placeholder="例如: 123456789", key="qmt_account_input")

            with col2:
                qmt_path = st.text_input("QMT路径", value=r"C:\Program Files\XtMiniQMT", key="qmt_path_input")

                max_capital = st.number_input(
                    "最大资金容量",
                    min_value=100000.0,
                    max_value=100000000.0,
                    value=10000000.0,
                    step=1000000.0,
                    format="%.0f",
                    key="max_capital_input",
                )

                priority = st.slider("优先级", min_value=1, max_value=10, value=5, key="priority_slider")

                use_mock = st.checkbox("使用Mock模式（测试）", value=True, key="use_mock_checkbox")

            col1, col2 = st.columns(2)

            with col1:
                test_button = st.form_submit_button("🔍 测试连接")

            with col2:
                add_button = st.form_submit_button("✅ 添加账户")

            if test_button or add_button:
                if not account_id:
                    st.error("请输入账户ID")
                elif not qmt_account:
                    st.error("请输入QMT资金账号")
                else:
                    try:
                        # 创建配置
                        config = AccountConfig(
                            account_id=account_id,
                            broker_name=broker_name,
                            account_type=account_type,
                            qmt_config=QMTConnectionConfig(
                                account_id=qmt_account, password="", mini_qmt_path=qmt_path  # 实际使用时需要安全输入
                            ),
                            max_capital=max_capital,
                            priority=priority,
                        )

                        if test_button:
                            st.info("正在测试连接...")
                            # 测试连接（使用Mock）
                            result = asyncio.run(self.manager.add_account(config, use_mock=True))
                            if result:
                                st.success("✅ 连接测试成功！")
                                # 测试后移除
                                asyncio.run(self.manager.remove_account(account_id))
                            else:
                                st.error("❌ 连接测试失败")

                        if add_button:
                            result = asyncio.run(self.manager.add_account(config, use_mock=use_mock))
                            if result:
                                st.success(f"✅ 账户添加成功: {account_id}")
                                st.rerun()
                            else:
                                st.error("❌ 账户添加失败")

                    except ValueError as e:
                        st.error(f"配置错误: {e}")
                    except Exception as e:  # pylint: disable=broad-exception-caught
                        st.error(f"添加失败: {e}")


def render_multi_account_page(manager: Optional[MultiAccountManager] = None) -> None:
    """渲染多账户管理页面

    白皮书依据: 附录A 7.5 多账户管理

    Args:
        manager: 多账户管理器实例
    """
    dashboard = MultiAccountDashboard(manager=manager)
    dashboard.render()


# ==================== Streamlit入口 ====================
if __name__ == "__main__":
    st.set_page_config(page_title="MIA - 多账户管理", page_icon="💼", layout="wide")

    # 初始化session state
    if "multi_account_manager" not in st.session_state:
        st.session_state.multi_account_manager = MultiAccountManager()

    render_multi_account_page(st.session_state.multi_account_manager)
