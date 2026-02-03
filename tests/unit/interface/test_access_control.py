"""权限与隐私控制体系测试

白皮书依据: 附录B 权限与隐私控制体系
"""

import pytest
from datetime import datetime

from src.interface.access_control import (
    UserRole,
    PageAccess,
    TradingPermission,
    UserSession,
    AccessPolicy,
    AccessControlManager,
    PhysicalIsolationMixin,
    AccessControlledDashboard,
    require_admin,
    require_page_access
)


class TestUserRole:
    """用户角色测试"""
    
    def test_guest_role_value(self):
        """测试Guest角色值"""
        assert UserRole.GUEST.value == 0
    
    def test_admin_role_value(self):
        """测试Admin角色值"""
        assert UserRole.ADMIN.value == 1
    
    def test_role_comparison(self):
        """测试角色比较"""
        assert UserRole.GUEST < UserRole.ADMIN


class TestPageAccess:
    """页面访问权限测试"""
    
    def test_scanner_page(self):
        """测试扫描仪页面"""
        assert PageAccess.SCANNER.value == "scanner"
    
    def test_all_pages_defined(self):
        """测试所有页面已定义"""
        expected_pages = [
            "scanner", "cockpit", "portfolio", "radar",
            "tactical", "watchlist", "system", "multi_account",
            "evolution", "library", "derivatives", "auditor"
        ]
        actual_pages = [p.value for p in PageAccess]
        for page in expected_pages:
            assert page in actual_pages


class TestUserSession:
    """用户会话测试"""
    
    def test_create_session(self):
        """测试创建会话"""
        session = UserSession(
            user_id="test_user",
            role=UserRole.ADMIN
        )
        assert session.user_id == "test_user"
        assert session.role == UserRole.ADMIN
        assert isinstance(session.login_time, datetime)
    
    def test_session_to_dict(self):
        """测试会话转字典"""
        session = UserSession(
            user_id="test_user",
            role=UserRole.GUEST,
            ip_address="127.0.0.1"
        )
        data = session.to_dict()
        assert data['user_id'] == "test_user"
        assert data['role'] == "GUEST"
        assert data['role_level'] == 0
        assert data['ip_address'] == "127.0.0.1"


class TestAccessControlManager:
    """权限控制管理器测试"""
    
    @pytest.fixture
    def manager(self):
        """测试夹具"""
        return AccessControlManager()
    
    @pytest.fixture
    def admin_manager(self):
        """Admin管理器夹具"""
        manager = AccessControlManager()
        manager.create_session("admin_user", UserRole.ADMIN)
        return manager
    
    @pytest.fixture
    def guest_manager(self):
        """Guest管理器夹具"""
        manager = AccessControlManager()
        manager.create_session("guest_user", UserRole.GUEST)
        return manager
    
    def test_default_role_is_guest(self, manager):
        """测试默认角色为Guest"""
        assert manager.get_current_role() == UserRole.GUEST
    
    def test_create_admin_session(self, manager):
        """测试创建Admin会话"""
        session = manager.create_session("admin", UserRole.ADMIN)
        assert session.role == UserRole.ADMIN
        assert manager.is_admin()
        assert not manager.is_guest()
    
    def test_create_guest_session(self, manager):
        """测试创建Guest会话"""
        session = manager.create_session("guest", UserRole.GUEST)
        assert session.role == UserRole.GUEST
        assert manager.is_guest()
        assert not manager.is_admin()
    
    def test_guest_can_access_scanner(self, guest_manager):
        """测试Guest可以访问扫描仪
        
        白皮书依据: 附录B - Guest仅可见全息扫描仪
        """
        assert guest_manager.can_access_page(PageAccess.SCANNER)
    
    def test_guest_cannot_access_cockpit(self, guest_manager):
        """测试Guest不能访问驾驶舱
        
        白皮书依据: 附录B - Guest仅可见全息扫描仪
        """
        assert not guest_manager.can_access_page(PageAccess.COCKPIT)
    
    def test_guest_cannot_access_portfolio(self, guest_manager):
        """测试Guest不能访问资产与归因"""
        assert not guest_manager.can_access_page(PageAccess.PORTFOLIO)
    
    def test_admin_can_access_all_pages(self, admin_manager):
        """测试Admin可以访问所有页面
        
        白皮书依据: 附录B - Admin全部可见
        """
        for page in PageAccess:
            assert admin_manager.can_access_page(page)
    
    def test_guest_cannot_execute_trade(self, guest_manager):
        """测试Guest不能执行交易
        
        白皮书依据: 附录B - Guest交易权限物理禁用
        """
        assert not guest_manager.can_execute_trade()
    
    def test_admin_can_execute_trade(self, admin_manager):
        """测试Admin可以执行交易
        
        白皮书依据: 附录B - Admin交易权限无限
        """
        assert admin_manager.can_execute_trade()
    
    def test_guest_cannot_view_sensitive_data(self, guest_manager):
        """测试Guest不能查看敏感数据
        
        白皮书依据: 附录B - 物理屏蔽
        """
        assert not guest_manager.can_view_sensitive_data()
    
    def test_admin_can_view_sensitive_data(self, admin_manager):
        """测试Admin可以查看敏感数据"""
        assert admin_manager.can_view_sensitive_data()
    
    def test_filter_sensitive_data_for_guest(self, guest_manager):
        """测试Guest敏感数据过滤
        
        白皮书依据: 附录B - 物理屏蔽
        """
        data = {
            'symbol': '000001',
            'name': '平安银行',
            'total_assets': 1000000,  # 敏感
            'positions': [{'symbol': '000001'}],  # 敏感
            'price': 12.50
        }
        filtered = guest_manager.filter_sensitive_data(data)
        
        assert 'symbol' in filtered
        assert 'name' in filtered
        assert 'price' in filtered
        assert 'total_assets' not in filtered
        assert 'positions' not in filtered
    
    def test_filter_sensitive_data_for_admin(self, admin_manager):
        """测试Admin敏感数据不过滤"""
        data = {
            'symbol': '000001',
            'total_assets': 1000000,
            'positions': [{'symbol': '000001'}]
        }
        filtered = admin_manager.filter_sensitive_data(data)
        
        assert filtered == data
    
    def test_guest_should_not_show_trade_buttons(self, guest_manager):
        """测试Guest不显示交易按钮
        
        白皮书依据: 附录B - 按钮移除
        """
        assert not guest_manager.should_show_trade_buttons()
    
    def test_admin_should_show_trade_buttons(self, admin_manager):
        """测试Admin显示交易按钮"""
        assert admin_manager.should_show_trade_buttons()
    
    def test_get_allowed_pages_for_guest(self, guest_manager):
        """测试Guest允许的页面列表"""
        pages = guest_manager.get_allowed_pages()
        assert len(pages) == 1
        assert PageAccess.SCANNER in pages
    
    def test_get_allowed_pages_for_admin(self, admin_manager):
        """测试Admin允许的页面列表"""
        pages = admin_manager.get_allowed_pages()
        assert len(pages) == len(PageAccess)
    
    def test_get_navigation_items(self, admin_manager):
        """测试获取导航菜单项"""
        nav_items = admin_manager.get_navigation_items()
        assert len(nav_items) > 0
        assert all('page' in item for item in nav_items)
        assert all('name' in item for item in nav_items)
        assert all('icon' in item for item in nav_items)
    
    def test_logout(self, admin_manager):
        """测试登出"""
        assert admin_manager.is_admin()
        admin_manager.logout()
        assert admin_manager.is_guest()  # 回到默认角色


class TestAccessPolicy:
    """访问策略测试"""
    
    def test_guest_policy(self):
        """测试Guest策略"""
        policy = AccessPolicy(
            role=UserRole.GUEST,
            allowed_pages={PageAccess.SCANNER},
            trading_permission=TradingPermission.DISABLED,
            can_view_sensitive_data=False,
            can_execute_trades=False,
            can_modify_settings=False
        )
        assert policy.role == UserRole.GUEST
        assert PageAccess.SCANNER in policy.allowed_pages
        assert policy.trading_permission == TradingPermission.DISABLED
        assert not policy.can_view_sensitive_data
        assert not policy.can_execute_trades
    
    def test_admin_policy(self):
        """测试Admin策略"""
        policy = AccessPolicy(
            role=UserRole.ADMIN,
            allowed_pages=set(PageAccess),
            trading_permission=TradingPermission.UNLIMITED,
            can_view_sensitive_data=True,
            can_execute_trades=True,
            can_modify_settings=True
        )
        assert policy.role == UserRole.ADMIN
        assert len(policy.allowed_pages) == len(PageAccess)
        assert policy.trading_permission == TradingPermission.UNLIMITED
        assert policy.can_view_sensitive_data
        assert policy.can_execute_trades


class TestDecorators:
    """装饰器测试"""
    
    def test_require_admin_with_admin(self):
        """测试Admin权限装饰器 - Admin用户"""
        manager = AccessControlManager()
        manager.create_session("admin", UserRole.ADMIN)
        
        @require_admin
        def admin_only_func(access_control=None):
            return "success"
        
        result = admin_only_func(access_control=manager)
        assert result == "success"
    
    def test_require_admin_with_guest(self):
        """测试Admin权限装饰器 - Guest用户"""
        manager = AccessControlManager()
        manager.create_session("guest", UserRole.GUEST)
        
        @require_admin
        def admin_only_func(access_control=None):
            return "success"
        
        with pytest.raises(PermissionError):
            admin_only_func(access_control=manager)
    
    def test_require_page_access_allowed(self):
        """测试页面访问装饰器 - 允许访问"""
        manager = AccessControlManager()
        manager.create_session("guest", UserRole.GUEST)
        
        @require_page_access(PageAccess.SCANNER)
        def scanner_func(access_control=None):
            return "success"
        
        result = scanner_func(access_control=manager)
        assert result == "success"
    
    def test_require_page_access_denied(self):
        """测试页面访问装饰器 - 拒绝访问"""
        manager = AccessControlManager()
        manager.create_session("guest", UserRole.GUEST)
        
        @require_page_access(PageAccess.COCKPIT)
        def cockpit_func(access_control=None):
            return "success"
        
        with pytest.raises(PermissionError):
            cockpit_func(access_control=manager)


class TestAccessControlledDashboard:
    """带权限控制的Dashboard测试"""
    
    def test_create_dashboard(self):
        """测试创建Dashboard"""
        dashboard = AccessControlledDashboard(
            page_type=PageAccess.SCANNER
        )
        assert dashboard.page_type == PageAccess.SCANNER
    
    def test_check_access_guest_scanner(self):
        """测试Guest访问扫描仪"""
        manager = AccessControlManager()
        manager.create_session("guest", UserRole.GUEST)
        
        dashboard = AccessControlledDashboard(
            access_control=manager,
            page_type=PageAccess.SCANNER
        )
        assert dashboard.check_access()
    
    def test_check_access_guest_cockpit(self):
        """测试Guest访问驾驶舱"""
        manager = AccessControlManager()
        manager.create_session("guest", UserRole.GUEST)
        
        dashboard = AccessControlledDashboard(
            access_control=manager,
            page_type=PageAccess.COCKPIT
        )
        assert not dashboard.check_access()
    
    def test_get_role_badge_admin(self):
        """测试Admin角色徽章"""
        manager = AccessControlManager()
        manager.create_session("admin", UserRole.ADMIN)
        
        dashboard = AccessControlledDashboard(access_control=manager)
        badge = dashboard.get_role_badge()
        assert "Admin" in badge
    
    def test_get_role_badge_guest(self):
        """测试Guest角色徽章"""
        manager = AccessControlManager()
        manager.create_session("guest", UserRole.GUEST)
        
        dashboard = AccessControlledDashboard(access_control=manager)
        badge = dashboard.get_role_badge()
        assert "Guest" in badge


class TestPhysicalIsolation:
    """物理隔离测试"""
    
    def test_load_data_with_isolation_admin(self):
        """测试Admin数据加载"""
        manager = AccessControlManager()
        manager.create_session("admin", UserRole.ADMIN)
        
        class TestDashboard(PhysicalIsolationMixin):
            def __init__(self):
                self.access_control = manager
        
        dashboard = TestDashboard()
        
        def loader():
            return {
                'symbol': '000001',
                'total_assets': 1000000,
                'positions': []
            }
        
        data = dashboard.load_data_with_isolation(loader)
        assert 'total_assets' in data
        assert 'positions' in data
    
    def test_load_data_with_isolation_guest(self):
        """测试Guest数据加载 - 敏感数据被过滤"""
        manager = AccessControlManager()
        manager.create_session("guest", UserRole.GUEST)
        
        class TestDashboard(PhysicalIsolationMixin):
            def __init__(self):
                self.access_control = manager
        
        dashboard = TestDashboard()
        
        def loader():
            return {
                'symbol': '000001',
                'total_assets': 1000000,
                'positions': []
            }
        
        data = dashboard.load_data_with_isolation(loader)
        assert 'symbol' in data
        assert 'total_assets' not in data
        assert 'positions' not in data
