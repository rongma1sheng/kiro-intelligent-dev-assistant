"""
Streamlit Web界面

白皮书依据: 第一章 1.1, 第七章 7.3 全息指挥台
实现MIA系统的Web控制面板和数据展示界面
"""

from datetime import datetime, timedelta
from typing import Optional

import pandas as pd
import plotly.express as px
import streamlit as st

# 导入系统组件
from .orchestrator import MainOrchestrator, SystemState
from .websocket_server import get_websocket_server


class StreamlitApp:
    """Streamlit应用主类

    白皮书依据: 第七章 7.3 全息指挥台

    提供MIA系统的Web控制面板，包括：
    - 系统状态监控
    - 服务管理
    - 实时数据展示
    - 控制操作
    """

    def __init__(self):
        """初始化Streamlit应用"""
        self.orchestrator: Optional[MainOrchestrator] = None
        self.websocket_server = get_websocket_server()

        # 页面配置
        st.set_page_config(page_title="MIA系统控制台", page_icon="🤖", layout="wide", initial_sidebar_state="expanded")

    def run(self):
        """运行Streamlit应用"""
        # 初始化会话状态
        if "orchestrator" not in st.session_state:
            st.session_state.orchestrator = MainOrchestrator()

        self.orchestrator = st.session_state.orchestrator

        # 主界面
        self.render_main_interface()

    def render_main_interface(self):
        """渲染主界面"""
        # 标题
        st.title("🤖 MIA系统控制台")
        st.markdown("---")

        # 侧边栏
        self.render_sidebar()

        # 主内容区域
        col1, col2 = st.columns([2, 1])

        with col1:
            self.render_system_status()
            self.render_service_status()

        with col2:
            self.render_control_panel()
            self.render_websocket_status()

    def render_sidebar(self):
        """渲染侧边栏"""
        st.sidebar.title("🎛️ 系统控制")

        # 系统状态
        current_state = self.orchestrator.get_current_state()
        st.sidebar.metric("当前状态", current_state.name)

        # 运行状态
        is_running = self.orchestrator.is_running
        status_color = "🟢" if is_running else "🔴"
        st.sidebar.metric("运行状态", f"{status_color} {'运行中' if is_running else '已停止'}")

        # 控制按钮
        st.sidebar.markdown("### 系统控制")

        col1, col2 = st.sidebar.columns(2)

        with col1:
            if st.button("▶️ 启动", disabled=is_running):
                try:
                    self.orchestrator.start()
                    st.success("系统启动成功")
                    st.rerun()
                except Exception as e:  # pylint: disable=broad-exception-caught
                    st.error(f"启动失败: {e}")

        with col2:
            if st.button("⏹️ 停止", disabled=not is_running):
                try:
                    self.orchestrator.stop()
                    st.success("系统停止成功")
                    st.rerun()
                except Exception as e:  # pylint: disable=broad-exception-caught
                    st.error(f"停止失败: {e}")

        # 状态转换
        st.sidebar.markdown("### 状态转换")

        target_state = st.sidebar.selectbox(
            "目标状态", options=[state.name for state in SystemState], index=list(SystemState).index(current_state)
        )

        if st.sidebar.button("🔄 转换状态"):
            try:
                new_state = SystemState[target_state]
                self.orchestrator.transition_to(new_state)
                st.success(f"状态转换成功: {new_state.name}")
                st.rerun()
            except Exception as e:  # pylint: disable=broad-exception-caught
                st.error(f"状态转换失败: {e}")

    def render_system_status(self):
        """渲染系统状态"""
        st.subheader("📊 系统状态")

        # 获取系统状态
        system_status = self.orchestrator.get_system_status()

        # 状态指标
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("当前状态", system_status["current_state"])

        with col2:
            running_status = "运行中" if system_status["is_running"] else "已停止"
            st.metric("运行状态", running_status)

        with col3:
            uptime_hours = system_status["uptime"] / 3600
            st.metric("运行时间", f"{uptime_hours:.1f}小时")

        with col4:
            service_count = len(system_status["services"])
            st.metric("服务数量", service_count)

        # 状态历史图表
        self.render_state_history_chart()

    def render_state_history_chart(self):
        """渲染状态历史图表"""
        st.subheader("📈 状态历史")

        # 获取状态历史
        state_history = self.orchestrator.get_state_history()

        if len(state_history) > 1:
            # 创建数据框
            df = pd.DataFrame(
                [{"时间": timestamp, "状态": state.name, "状态值": state.value} for timestamp, state in state_history]
            )

            # 创建时间线图表
            fig = px.line(
                df, x="时间", y="状态值", title="系统状态变化时间线", labels={"状态值": "状态", "时间": "时间"}
            )

            # 添加状态标签
            for i, row in df.iterrows():  # pylint: disable=unused-variable
                fig.add_annotation(x=row["时间"], y=row["状态值"], text=row["状态"], showarrow=True, arrowhead=2)

            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("暂无状态历史数据")

    def render_service_status(self):
        """渲染服务状态"""
        st.subheader("🔧 服务状态")

        # 获取服务状态
        services_status = self.orchestrator.get_service_manager_status()

        if services_status:
            # 创建服务状态表格
            service_data = []
            for service_name, status in services_status.items():
                service_data.append(
                    {"服务名称": service_name, "状态": status["status"], "运行时间": f"{status.get('uptime', 0):.1f}秒"}
                )

            df = pd.DataFrame(service_data)

            # 添加状态颜色
            def color_status(val):
                if val == "running":  # pylint: disable=no-else-return
                    return "background-color: #90EE90"  # 浅绿色
                elif val == "error":
                    return "background-color: #FFB6C1"  # 浅红色
                else:
                    return "background-color: #D3D3D3"  # 浅灰色

            styled_df = df.style.applymap(color_status, subset=["状态"])
            st.dataframe(styled_df, use_container_width=True)
        else:
            st.info("暂无服务状态数据")

    def render_control_panel(self):
        """渲染控制面板"""
        st.subheader("🎮 控制面板")

        # 服务控制
        st.markdown("#### 服务控制")

        services_status = self.orchestrator.get_service_manager_status()

        if services_status:
            for service_name, status in services_status.items():
                col1, col2, col3 = st.columns([2, 1, 1])

                with col1:
                    st.text(f"{service_name}: {status['status']}")

                with col2:
                    if st.button(f"启动", key=f"start_{service_name}"):  # pylint: disable=w1309
                        st.info(f"启动服务 {service_name}")

                with col3:
                    if st.button(f"停止", key=f"stop_{service_name}"):  # pylint: disable=w1309
                        st.info(f"停止服务 {service_name}")

        # 系统配置
        st.markdown("#### 系统配置")

        config = self.orchestrator.config

        # 显示配置信息
        st.json(config)

    def render_websocket_status(self):
        """渲染WebSocket状态"""
        st.subheader("🌐 WebSocket状态")

        # 获取WebSocket状态
        ws_status = self.orchestrator.get_websocket_status()

        # 状态指标
        col1, col2 = st.columns(2)

        with col1:
            status_text = "运行中" if ws_status["running"] else "已停止"
            status_color = "🟢" if ws_status["running"] else "🔴"
            st.metric("状态", f"{status_color} {status_text}")

        with col2:
            st.metric("端口", ws_status["port"])

        # WebSocket服务器性能指标
        if ws_status["running"]:
            try:
                server_status = self.websocket_server.get_server_status()

                col1, col2, col3 = st.columns(3)

                with col1:
                    st.metric("客户端数", server_status["client_count"])

                with col2:
                    st.metric("消息数", server_status["messages_sent"])

                with col3:
                    st.metric("队列大小", server_status["queue_size"])

                # 性能图表
                metrics = self.websocket_server.get_performance_metrics()

                if metrics["uptime_seconds"] > 0:
                    st.metric("消息/秒", f"{metrics['messages_per_second']:.1f}")
                    st.metric("字节/秒", f"{metrics['bytes_per_second']:.0f}")

            except Exception as e:  # pylint: disable=broad-exception-caught
                st.error(f"获取WebSocket性能指标失败: {e}")

    def render_realtime_data(self):
        """渲染实时数据（预留）"""
        st.subheader("📡 实时数据")

        # 这里将来集成雷达信号、市场数据等实时信息
        st.info("实时数据功能开发中...")

        # 模拟数据展示
        if st.button("刷新数据"):
            # 生成模拟数据
            data = {
                "时间": [datetime.now() - timedelta(minutes=i) for i in range(10, 0, -1)],
                "信号强度": [0.1 + 0.8 * (i % 3) / 2 for i in range(10)],
            }

            df = pd.DataFrame(data)

            fig = px.line(df, x="时间", y="信号强度", title="模拟雷达信号")
            st.plotly_chart(fig, use_container_width=True)


def main():
    """主函数"""
    app = StreamlitApp()
    app.run()


if __name__ == "__main__":
    main()
