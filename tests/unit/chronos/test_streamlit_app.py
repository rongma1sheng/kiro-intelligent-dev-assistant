"""
Streamlit应用测试

测试覆盖:
- StreamlitApp类初始化
- 主界面渲染
- 侧边栏控制
- 系统状态显示
- 服务状态管理
- 控制面板操作
- WebSocket状态监控
- 实时数据展示
- 错误处理
- 配置管理

遵循测试铁律:
- 严禁跳过任何测试
- 测试超时必须溯源修复
- 发现问题立刻修复
"""

import unittest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, Mock, call, patch

import pandas as pd
import pytest

from src.chronos.orchestrator import MainOrchestrator, SystemState

# 导入被测试的模块
from src.chronos.streamlit_app import StreamlitApp, main


class MockContextManager:
    """Mock上下文管理器"""

    def __init__(self):
        self.mock = Mock()

    def __enter__(self):
        return self.mock

    def __exit__(self, exc_type, exc_val, exc_tb):
        return None


class TestStreamlitApp(unittest.TestCase):
    """StreamlitApp测试类"""

    def setUp(self):
        """测试前置设置"""
        # Mock streamlit
        self.st_mock = Mock()
        self.st_patcher = patch("src.chronos.streamlit_app.st", self.st_mock)
        self.st_patcher.start()

        # Mock plotly
        self.px_mock = Mock()
        self.px_patcher = patch("src.chronos.streamlit_app.px", self.px_mock)
        self.px_patcher.start()

        # Mock pandas
        self.pd_mock = Mock()
        self.pd_patcher = patch("src.chronos.streamlit_app.pd", self.pd_mock)
        self.pd_patcher.start()

        # Mock websocket server
        self.websocket_mock = Mock()
        self.websocket_patcher = patch(
            "src.chronos.streamlit_app.get_websocket_server", return_value=self.websocket_mock
        )
        self.websocket_patcher.start()

        # 设置session_state mock - 支持in操作符
        self.session_state_mock = Mock()
        self.session_state_mock.__contains__ = Mock(return_value=True)  # 默认包含所有属性
        self.st_mock.session_state = self.session_state_mock

        # 设置columns mock - 返回足够数量的MockContextManager对象
        def create_columns(count):
            if isinstance(count, list):
                count = len(count)
            elif isinstance(count, int):
                pass
            else:
                count = 4  # 默认4列
            return [MockContextManager() for _ in range(count)]

        self.st_mock.columns.side_effect = create_columns
        self.st_mock.sidebar.columns.side_effect = create_columns

        # 创建测试实例
        self.app = StreamlitApp()

    def tearDown(self):
        """测试后置清理"""
        self.st_patcher.stop()
        self.px_patcher.stop()
        self.pd_patcher.stop()
        self.websocket_patcher.stop()

    def test_init(self):
        """测试StreamlitApp初始化"""
        # 验证初始化
        self.assertIsNone(self.app.orchestrator)
        self.assertEqual(self.app.websocket_server, self.websocket_mock)

        # 验证页面配置调用
        self.st_mock.set_page_config.assert_called_once_with(
            page_title="MIA系统控制台", page_icon="🤖", layout="wide", initial_sidebar_state="expanded"
        )

    @patch("src.chronos.streamlit_app.MainOrchestrator")
    def test_run_first_time(self, mock_orchestrator_class):
        """测试首次运行应用"""
        # 设置mock
        mock_orchestrator = Mock()
        mock_orchestrator_class.return_value = mock_orchestrator

        # 模拟首次运行（session_state没有orchestrator属性）
        self.session_state_mock.__contains__.return_value = False  # "orchestrator" not in session_state

        with patch.object(self.app, "render_main_interface") as mock_render:
            self.app.run()

            # 验证orchestrator被创建并存储
            mock_orchestrator_class.assert_called_once()
            self.assertEqual(self.app.orchestrator, mock_orchestrator)

            # 验证主界面被渲染
            mock_render.assert_called_once()

    def test_run_existing_session(self):
        """测试已有session的运行"""
        # 设置已存在的orchestrator
        mock_orchestrator = Mock()
        self.session_state_mock.orchestrator = mock_orchestrator
        self.session_state_mock.__contains__.return_value = True  # "orchestrator" in session_state

        with patch.object(self.app, "render_main_interface") as mock_render:
            self.app.run()

            # 验证使用现有orchestrator
            self.assertEqual(self.app.orchestrator, mock_orchestrator)
            mock_render.assert_called_once()

    def test_render_main_interface(self):
        """测试主界面渲染"""
        # 设置mock
        self.app.orchestrator = Mock()

        with (
            patch.object(self.app, "render_sidebar") as mock_sidebar,
            patch.object(self.app, "render_system_status") as mock_system,
            patch.object(self.app, "render_service_status") as mock_service,
            patch.object(self.app, "render_control_panel") as mock_control,
            patch.object(self.app, "render_websocket_status") as mock_websocket,
        ):

            self.app.render_main_interface()

            # 验证标题和分隔线
            self.st_mock.title.assert_called_once_with("🤖 MIA系统控制台")
            self.st_mock.markdown.assert_called_with("---")

            # 验证列布局
            self.st_mock.columns.assert_called_once_with([2, 1])

            # 验证各组件渲染
            mock_sidebar.assert_called_once()
            mock_system.assert_called_once()
            mock_service.assert_called_once()
            mock_control.assert_called_once()
            mock_websocket.assert_called_once()

    def test_render_sidebar_basic(self):
        """测试侧边栏基本渲染"""
        # 设置mock orchestrator
        mock_orchestrator = Mock()
        mock_orchestrator.get_current_state.return_value = SystemState.WAR
        mock_orchestrator.is_running = True
        self.app.orchestrator = mock_orchestrator

        # 设置button返回值
        self.st_mock.sidebar.selectbox.return_value = "WAR"
        self.st_mock.sidebar.button.return_value = False

        self.app.render_sidebar()

        # 验证标题
        self.st_mock.sidebar.title.assert_called_once_with("🎛️ 系统控制")

        # 验证状态显示
        self.st_mock.sidebar.metric.assert_any_call("当前状态", "WAR")
        self.st_mock.sidebar.metric.assert_any_call("运行状态", "🟢 运行中")

    def test_render_system_status(self):
        """测试系统状态渲染"""
        # 设置mock orchestrator
        mock_orchestrator = Mock()
        mock_status = {
            "current_state": "WAR",
            "is_running": True,
            "uptime": 7200,  # 2小时
            "services": {"service1": {}, "service2": {}},
        }
        mock_orchestrator.get_system_status.return_value = mock_status
        self.app.orchestrator = mock_orchestrator

        with patch.object(self.app, "render_state_history_chart") as mock_chart:
            self.app.render_system_status()

            # 验证子标题
            self.st_mock.subheader.assert_called_with("📊 系统状态")

            # 验证图表渲染
            mock_chart.assert_called_once()

    def test_render_state_history_chart_with_data(self):
        """测试状态历史图表渲染 - 有数据"""
        # 设置mock orchestrator
        mock_orchestrator = Mock()
        mock_history = [
            (datetime.now() - timedelta(hours=2), SystemState.MAINTENANCE),
            (datetime.now() - timedelta(hours=1), SystemState.PREP),
            (datetime.now(), SystemState.WAR),
        ]
        mock_orchestrator.get_state_history.return_value = mock_history
        self.app.orchestrator = mock_orchestrator

        # 设置DataFrame mock
        mock_df = Mock()
        self.pd_mock.DataFrame.return_value = mock_df
        mock_df.iterrows.return_value = [(0, {"时间": datetime.now(), "状态值": 2, "状态": "WAR"})]

        # 设置plotly mock
        mock_fig = Mock()
        self.px_mock.line.return_value = mock_fig

        self.app.render_state_history_chart()

        # 验证DataFrame创建
        self.pd_mock.DataFrame.assert_called_once()

        # 验证图表创建
        self.px_mock.line.assert_called_once()
        self.st_mock.plotly_chart.assert_called_once_with(mock_fig, use_container_width=True)

    def test_render_state_history_chart_no_data(self):
        """测试状态历史图表渲染 - 无数据"""
        # 设置mock orchestrator
        mock_orchestrator = Mock()
        mock_orchestrator.get_state_history.return_value = [(datetime.now(), SystemState.MAINTENANCE)]  # 只有一条记录
        self.app.orchestrator = mock_orchestrator

        self.app.render_state_history_chart()

        # 验证显示信息提示
        self.st_mock.info.assert_called_once_with("暂无状态历史数据")

    def test_render_service_status_with_services(self):
        """测试服务状态渲染 - 有服务"""
        # 设置mock orchestrator
        mock_orchestrator = Mock()
        mock_services = {
            "service1": {"status": "running", "uptime": 3600},
            "service2": {"status": "error", "uptime": 0},
            "service3": {"status": "stopped"},
        }
        mock_orchestrator.get_service_manager_status.return_value = mock_services
        self.app.orchestrator = mock_orchestrator

        # 设置DataFrame mock
        mock_df = Mock()
        mock_styled_df = Mock()
        self.pd_mock.DataFrame.return_value = mock_df
        mock_df.style.applymap.return_value = mock_styled_df

        self.app.render_service_status()

        # 验证子标题
        self.st_mock.subheader.assert_called_with("🔧 服务状态")

        # 验证DataFrame创建
        expected_data = [
            {"服务名称": "service1", "状态": "running", "运行时间": "3600.0秒"},
            {"服务名称": "service2", "状态": "error", "运行时间": "0.0秒"},
            {"服务名称": "service3", "状态": "stopped", "运行时间": "0.0秒"},
        ]
        self.pd_mock.DataFrame.assert_called_once_with(expected_data)

        # 验证样式应用
        mock_df.style.applymap.assert_called_once()
        self.st_mock.dataframe.assert_called_once_with(mock_styled_df, use_container_width=True)

    def test_render_service_status_no_services(self):
        """测试服务状态渲染 - 无服务"""
        # 设置mock orchestrator
        mock_orchestrator = Mock()
        mock_orchestrator.get_service_manager_status.return_value = {}
        self.app.orchestrator = mock_orchestrator

        self.app.render_service_status()

        # 验证显示信息提示
        self.st_mock.info.assert_called_once_with("暂无服务状态数据")

    def test_render_control_panel_basic(self):
        """测试控制面板基本渲染"""
        # 设置mock orchestrator
        mock_orchestrator = Mock()
        mock_orchestrator.get_service_manager_status.return_value = {}
        mock_orchestrator.config = {"key": "value"}
        self.app.orchestrator = mock_orchestrator

        self.app.render_control_panel()

        # 验证子标题
        self.st_mock.subheader.assert_called_with("🎮 控制面板")

        # 验证配置显示
        self.st_mock.json.assert_called_once_with({"key": "value"})

    def test_render_websocket_status_basic(self):
        """测试WebSocket状态基本渲染"""
        # 设置mock orchestrator
        mock_orchestrator = Mock()
        mock_ws_status = {"running": False, "port": 8502}
        mock_orchestrator.get_websocket_status.return_value = mock_ws_status
        self.app.orchestrator = mock_orchestrator

        self.app.render_websocket_status()

        # 验证子标题
        self.st_mock.subheader.assert_called_with("🌐 WebSocket状态")

    def test_render_realtime_data_initial(self):
        """测试实时数据渲染 - 初始状态"""
        self.app.render_realtime_data()

        # 验证子标题和信息
        self.st_mock.subheader.assert_called_with("📡 实时数据")
        self.st_mock.info.assert_called_with("实时数据功能开发中...")

    def test_render_realtime_data_refresh_clicked(self):
        """测试实时数据渲染 - 刷新按钮点击"""
        # 模拟刷新按钮被点击
        self.st_mock.button.return_value = True

        # 设置DataFrame mock
        mock_df = Mock()
        self.pd_mock.DataFrame.return_value = mock_df

        # 设置plotly mock
        mock_fig = Mock()
        self.px_mock.line.return_value = mock_fig

        self.app.render_realtime_data()

        # 验证数据生成和图表显示
        self.pd_mock.DataFrame.assert_called_once()
        self.px_mock.line.assert_called_once()
        self.st_mock.plotly_chart.assert_called_once_with(mock_fig, use_container_width=True)

    def test_color_status_function(self):
        """测试状态颜色函数"""
        # 这个函数在render_service_status中定义，我们需要通过调用来测试
        mock_orchestrator = Mock()
        mock_services = {"service1": {"status": "running"}}
        mock_orchestrator.get_service_manager_status.return_value = mock_services
        self.app.orchestrator = mock_orchestrator

        # 设置DataFrame mock
        mock_df = Mock()
        self.pd_mock.DataFrame.return_value = mock_df

        # 调用方法
        self.app.render_service_status()

        # 验证applymap被调用
        mock_df.style.applymap.assert_called_once()

        # 获取传递给applymap的函数
        color_func = mock_df.style.applymap.call_args[0][0]

        # 测试不同状态的颜色
        self.assertEqual(color_func("running"), "background-color: #90EE90")
        self.assertEqual(color_func("error"), "background-color: #FFB6C1")
        self.assertEqual(color_func("stopped"), "background-color: #D3D3D3")

    def test_sidebar_start_button_success(self):
        """测试侧边栏启动按钮成功"""
        # 设置mock orchestrator
        mock_orchestrator = Mock()
        mock_orchestrator.get_current_state.return_value = SystemState.MAINTENANCE
        mock_orchestrator.is_running = False
        self.app.orchestrator = mock_orchestrator

        # 模拟启动按钮被点击
        col1_mock = self.st_mock.sidebar.columns.return_value[0]
        col1_mock.mock.button.return_value = True

        col2_mock = self.st_mock.sidebar.columns.return_value[1]
        col2_mock.mock.button.return_value = False

        self.st_mock.sidebar.selectbox.return_value = "MAINTENANCE"
        self.st_mock.sidebar.button.return_value = False

        self.app.render_sidebar()

        # 验证启动方法被调用
        mock_orchestrator.start.assert_called_once()

    def test_sidebar_start_button_error(self):
        """测试侧边栏启动按钮失败"""
        # 设置mock orchestrator
        mock_orchestrator = Mock()
        mock_orchestrator.get_current_state.return_value = SystemState.MAINTENANCE
        mock_orchestrator.is_running = False
        mock_orchestrator.start.side_effect = Exception("启动失败")
        self.app.orchestrator = mock_orchestrator

        # 模拟启动按钮被点击
        col1_mock = self.st_mock.sidebar.columns.return_value[0]
        col1_mock.mock.button.return_value = True

        col2_mock = self.st_mock.sidebar.columns.return_value[1]
        col2_mock.mock.button.return_value = False

        self.st_mock.sidebar.selectbox.return_value = "MAINTENANCE"
        self.st_mock.sidebar.button.return_value = False

        self.app.render_sidebar()

        # 验证错误处理
        self.st_mock.error.assert_called_once_with("启动失败: 启动失败")

    def test_sidebar_stop_button_success(self):
        """测试侧边栏停止按钮成功"""
        # 设置mock orchestrator
        mock_orchestrator = Mock()
        mock_orchestrator.get_current_state.return_value = SystemState.WAR
        mock_orchestrator.is_running = True
        self.app.orchestrator = mock_orchestrator

        # 模拟停止按钮被点击
        col1_mock = self.st_mock.sidebar.columns.return_value[0]
        col1_mock.mock.button.return_value = False

        col2_mock = self.st_mock.sidebar.columns.return_value[1]
        col2_mock.mock.button.return_value = True

        self.st_mock.sidebar.selectbox.return_value = "WAR"
        self.st_mock.sidebar.button.return_value = False

        self.app.render_sidebar()

        # 验证停止方法被调用
        mock_orchestrator.stop.assert_called_once()

    def test_sidebar_state_transition_success(self):
        """测试侧边栏状态转换成功"""
        # 设置mock orchestrator
        mock_orchestrator = Mock()
        mock_orchestrator.get_current_state.return_value = SystemState.MAINTENANCE
        mock_orchestrator.is_running = False
        self.app.orchestrator = mock_orchestrator

        # 设置button返回值
        col1_mock = self.st_mock.sidebar.columns.return_value[0]
        col1_mock.mock.button.return_value = False

        col2_mock = self.st_mock.sidebar.columns.return_value[1]
        col2_mock.mock.button.return_value = False

        self.st_mock.sidebar.selectbox.return_value = "PREP"  # 选择新状态
        self.st_mock.sidebar.button.return_value = True  # 状态转换按钮被点击

        self.app.render_sidebar()

        # 验证状态转换
        mock_orchestrator.transition_to.assert_called_once_with(SystemState.PREP)

    def test_websocket_status_running_with_metrics(self):
        """测试WebSocket状态运行中并获取性能指标"""
        # 设置mock orchestrator
        mock_orchestrator = Mock()
        mock_ws_status = {"running": True, "port": 8502}
        mock_orchestrator.get_websocket_status.return_value = mock_ws_status
        self.app.orchestrator = mock_orchestrator

        # 设置websocket server mock
        mock_server_status = {"client_count": 5, "messages_sent": 100, "queue_size": 10}
        mock_metrics = {"uptime_seconds": 3600, "messages_per_second": 2.5, "bytes_per_second": 1024}
        self.websocket_mock.get_server_status.return_value = mock_server_status
        self.websocket_mock.get_performance_metrics.return_value = mock_metrics

        self.app.render_websocket_status()

        # 验证性能指标获取
        self.websocket_mock.get_server_status.assert_called_once()
        self.websocket_mock.get_performance_metrics.assert_called_once()

    def test_websocket_status_error_handling(self):
        """测试WebSocket状态错误处理"""
        # 设置mock orchestrator
        mock_orchestrator = Mock()
        mock_ws_status = {"running": True, "port": 8502}
        mock_orchestrator.get_websocket_status.return_value = mock_ws_status
        self.app.orchestrator = mock_orchestrator

        # 设置websocket server mock抛出异常
        self.websocket_mock.get_server_status.side_effect = Exception("连接失败")

        self.app.render_websocket_status()

        # 验证错误处理
        self.st_mock.error.assert_called_once_with("获取WebSocket性能指标失败: 连接失败")

    def test_control_panel_with_services(self):
        """测试控制面板有服务时的渲染"""
        # 设置mock orchestrator
        mock_orchestrator = Mock()
        mock_services = {"service1": {"status": "running"}, "service2": {"status": "stopped"}}
        mock_orchestrator.get_service_manager_status.return_value = mock_services
        mock_orchestrator.config = {"key": "value"}
        self.app.orchestrator = mock_orchestrator

        # 设置button返回值
        col1_mock = self.st_mock.columns.return_value[0]
        col2_mock = self.st_mock.columns.return_value[1]
        col3_mock = self.st_mock.columns.return_value[2] if len(self.st_mock.columns.return_value) > 2 else Mock()

        # 模拟没有按钮被点击
        col2_mock.mock.button.return_value = False
        col3_mock.mock.button.return_value = False

        self.app.render_control_panel()

        # 验证子标题
        self.st_mock.subheader.assert_called_with("🎮 控制面板")

    def test_control_panel_service_start_clicked(self):
        """测试控制面板服务启动按钮点击"""
        # 设置mock orchestrator
        mock_orchestrator = Mock()
        mock_services = {"service1": {"status": "stopped"}}
        mock_orchestrator.get_service_manager_status.return_value = mock_services
        mock_orchestrator.config = {}
        self.app.orchestrator = mock_orchestrator

        # 模拟启动按钮被点击 - 第2列是启动按钮
        columns = self.st_mock.columns.side_effect([2, 1, 1])  # 3列布局
        col1_mock, col2_mock, col3_mock = columns

        col2_mock.mock.button.return_value = True  # 启动按钮被点击
        col3_mock.mock.button.return_value = False  # 停止按钮未点击

        self.app.render_control_panel()

        # 验证信息显示
        self.st_mock.info.assert_called_with("启动服务 service1")

    def test_system_status_metrics(self):
        """测试系统状态指标显示"""
        # 设置mock orchestrator
        mock_orchestrator = Mock()
        mock_status = {
            "current_state": "PREP",
            "is_running": False,
            "uptime": 1800,  # 0.5小时
            "services": {"service1": {}},
        }
        mock_orchestrator.get_system_status.return_value = mock_status
        self.app.orchestrator = mock_orchestrator

        # 重新设置columns mock以支持4列
        self.st_mock.columns.return_value = [
            MockContextManager(),
            MockContextManager(),
            MockContextManager(),
            MockContextManager(),
        ]

        with patch.object(self.app, "render_state_history_chart") as mock_chart:
            self.app.render_system_status()

            # 验证子标题
            self.st_mock.subheader.assert_called_with("📊 系统状态")

            # 验证图表渲染
            mock_chart.assert_called_once()


class TestMainFunction(unittest.TestCase):
    """main函数测试类"""

    @patch("src.chronos.streamlit_app.StreamlitApp")
    def test_main(self, mock_app_class):
        """测试main函数"""
        # 设置mock
        mock_app = Mock()
        mock_app_class.return_value = mock_app

        # 调用main函数
        main()

        # 验证应用创建和运行
        mock_app_class.assert_called_once()
        mock_app.run.assert_called_once()


class TestStreamlitAppIntegration(unittest.TestCase):
    """StreamlitApp集成测试类"""

    def setUp(self):
        """测试前置设置"""
        # Mock所有外部依赖
        self.patches = []

        # Mock streamlit
        self.st_mock = Mock()
        self.session_state_mock = Mock()
        self.st_mock.session_state = self.session_state_mock
        self.patches.append(patch("src.chronos.streamlit_app.st", self.st_mock))

        # Mock plotly
        self.px_mock = Mock()
        self.patches.append(patch("src.chronos.streamlit_app.px", self.px_mock))

        # Mock pandas
        self.pd_mock = Mock()
        self.patches.append(patch("src.chronos.streamlit_app.pd", self.pd_mock))

        # Mock websocket server
        self.websocket_mock = Mock()
        self.patches.append(patch("src.chronos.streamlit_app.get_websocket_server", return_value=self.websocket_mock))

        # Mock MainOrchestrator
        self.orchestrator_mock = Mock()
        self.patches.append(patch("src.chronos.streamlit_app.MainOrchestrator", return_value=self.orchestrator_mock))

        # 设置columns mock
        self.st_mock.columns.return_value = [MockContextManager(), MockContextManager()]
        self.st_mock.sidebar.columns.return_value = [MockContextManager(), MockContextManager()]

        # 启动所有patches
        for p in self.patches:
            p.start()

    def tearDown(self):
        """测试后置清理"""
        for p in self.patches:
            p.stop()

    def test_full_workflow(self):
        """测试完整工作流程"""
        # 设置orchestrator状态
        self.orchestrator_mock.get_current_state.return_value = SystemState.WAR
        self.orchestrator_mock.is_running = True
        self.orchestrator_mock.get_system_status.return_value = {
            "current_state": "WAR",
            "is_running": True,
            "uptime": 3600,
            "services": {"service1": {}},
        }
        self.orchestrator_mock.get_service_manager_status.return_value = {
            "service1": {"status": "running", "uptime": 3600}
        }
        self.orchestrator_mock.get_websocket_status.return_value = {"running": True, "port": 8502}
        self.orchestrator_mock.get_state_history.return_value = [
            (datetime.now() - timedelta(hours=1), SystemState.PREP),
            (datetime.now(), SystemState.WAR),
        ]

        # 设置UI mock返回值
        self.st_mock.sidebar.selectbox.return_value = "WAR"
        self.st_mock.sidebar.button.return_value = False
        self.st_mock.button.return_value = False

        # 设置DataFrame和图表mock
        mock_df = Mock()
        self.pd_mock.DataFrame.return_value = mock_df
        mock_df.style.applymap.return_value = Mock()
        mock_df.iterrows.return_value = []

        mock_fig = Mock()
        self.px_mock.line.return_value = mock_fig

        # 模拟首次运行
        def side_effect(obj, attr):
            if attr == "orchestrator":
                return False
            return True

        with patch("builtins.hasattr", side_effect=side_effect):
            # 创建并运行应用
            app = StreamlitApp()
            app.run()

            # 验证关键调用
            self.st_mock.set_page_config.assert_called_once()
            self.st_mock.title.assert_called_once_with("🤖 MIA系统控制台")
            self.orchestrator_mock.get_system_status.assert_called_once()
            self.orchestrator_mock.get_service_manager_status.assert_called()
            self.orchestrator_mock.get_websocket_status.assert_called_once()


if __name__ == "__main__":
    unittest.main()
