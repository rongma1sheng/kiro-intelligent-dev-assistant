"""PathManager单元测试

白皮书依据: 第三章 3.1 双盘物理隔离

测试覆盖:
- 路径路由（Windows/Linux/Mac）
- 只读检查
- 异常处理
- 配置信息

Author: MIA Team
Date: 2026-01-22
"""

import pytest
import platform
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.infra.path_manager import PathManager, get_path_manager


class TestPathManagerInitialization:
    """测试PathManager初始化"""
    
    def test_initialization_default(self):
        """测试默认初始化"""
        pm = PathManager()
        
        assert pm.os_type in ["Windows", "Linux", "Darwin"]
        assert pm.readonly_enabled is True
        assert pm.system_drive is not None
        assert pm.data_drive is not None
    
    def test_initialization_readonly_disabled(self):
        """测试禁用只读保护"""
        pm = PathManager(readonly_enabled=False)
        
        assert pm.readonly_enabled is False
    
    @patch('platform.system')
    def test_windows_disk_detection(self, mock_system):
        """测试Windows磁盘检测"""
        mock_system.return_value = "Windows"
        
        pm = PathManager()
        
        assert pm.os_type == "Windows"
        assert pm.system_drive == Path("C:/")
        # D盘可能不存在，所以检查是否有数据盘配置
        assert pm.data_drive is not None
    
    @patch('platform.system')
    def test_linux_disk_detection(self, mock_system):
        """测试Linux磁盘检测"""
        mock_system.return_value = "Linux"
        
        pm = PathManager()
        
        assert pm.os_type == "Linux"
        assert pm.system_drive == Path("/")
        assert pm.data_drive is not None
    
    @patch('platform.system')
    def test_unsupported_os(self, mock_system):
        """测试不支持的操作系统"""
        mock_system.return_value = "Unknown"
        
        with pytest.raises(RuntimeError, match="不支持的操作系统"):
            PathManager()


class TestPathRouting:
    """测试路径路由"""
    
    def test_get_data_path_no_subdir(self):
        """测试获取数据路径（无子目录）"""
        pm = PathManager()
        path = pm.get_data_path()
        
        assert "mia" in str(path)
        assert "data" in str(path)
        assert path.exists()
    
    def test_get_data_path_with_subdir(self):
        """测试获取数据路径（有子目录）"""
        pm = PathManager()
        path = pm.get_data_path("tick")
        
        assert "mia" in str(path)
        assert "data" in str(path)
        assert "tick" in str(path)
        assert path.exists()
    
    def test_get_log_path_no_subdir(self):
        """测试获取日志路径（无子目录）"""
        pm = PathManager()
        path = pm.get_log_path()
        
        assert "mia" in str(path)
        assert "logs" in str(path)
        assert path.exists()
    
    def test_get_log_path_with_subdir(self):
        """测试获取日志路径（有子目录）"""
        pm = PathManager()
        path = pm.get_log_path("system")
        
        assert "mia" in str(path)
        assert "logs" in str(path)
        assert "system" in str(path)
        assert path.exists()

    def test_get_temp_path_no_subdir(self):
        """测试获取临时路径（无子目录）"""
        pm = PathManager()
        path = pm.get_temp_path()
        
        assert "mia" in str(path)
        assert "temp" in str(path)
        assert path.exists()
    
    def test_get_temp_path_with_subdir(self):
        """测试获取临时路径（有子目录）"""
        pm = PathManager()
        path = pm.get_temp_path("cache")
        
        assert "mia" in str(path)
        assert "temp" in str(path)
        assert "cache" in str(path)
        assert path.exists()
    
    def test_get_docker_root(self):
        """测试获取Docker根目录"""
        pm = PathManager()
        path = pm.get_docker_root()
        
        assert "mia" in str(path)
        assert "docker" in str(path)
        assert path.exists()


class TestReadonlyCompliance:
    """测试只读合规性检查"""
    
    @patch('platform.system')
    def test_windows_c_drive_write_blocked(self, mock_system):
        """测试Windows C盘写入被阻止"""
        mock_system.return_value = "Windows"
        pm = PathManager(readonly_enabled=True)
        
        with pytest.raises(PermissionError, match="禁止写入系统盘"):
            pm.check_readonly_compliance("C:/test.txt")
    
    @patch('platform.system')
    def test_windows_d_drive_write_allowed(self, mock_system):
        """测试Windows D盘写入允许"""
        mock_system.return_value = "Windows"
        pm = PathManager(readonly_enabled=True)
        
        # 不应该抛出异常
        pm.check_readonly_compliance("D:/test.txt")
    
    @patch('platform.system')
    @patch('pathlib.Path.resolve')
    def test_linux_system_dir_write_blocked(self, mock_resolve, mock_system):
        """测试Linux系统目录写入被阻止"""
        mock_system.return_value = "Linux"
        # 模拟Linux路径解析
        mock_resolve.return_value = Path("/usr/test.txt")
        
        pm = PathManager(readonly_enabled=True)
        
        with pytest.raises(PermissionError, match="禁止写入系统目录"):
            pm.check_readonly_compliance("/usr/test.txt")
    
    @patch('platform.system')
    def test_linux_data_dir_write_allowed(self, mock_system):
        """测试Linux数据目录写入允许"""
        mock_system.return_value = "Linux"
        pm = PathManager(readonly_enabled=True)
        
        # 不应该抛出异常
        pm.check_readonly_compliance("/data/test.txt")
    
    def test_readonly_disabled_allows_all_writes(self):
        """测试禁用只读保护允许所有写入"""
        pm = PathManager(readonly_enabled=False)
        
        # 不应该抛出异常
        if platform.system() == "Windows":
            pm.check_readonly_compliance("C:/test.txt")
        else:
            pm.check_readonly_compliance("/usr/test.txt")


class TestConfiguration:
    """测试配置信息"""
    
    def test_get_config(self):
        """测试获取配置信息"""
        pm = PathManager()
        config = pm.get_config()
        
        assert "os_type" in config
        assert "system_drive" in config
        assert "data_drive" in config
        assert "readonly_enabled" in config
        assert "data_path" in config
        assert "log_path" in config
        assert "temp_path" in config
        assert "docker_root" in config
        
        assert config["os_type"] in ["Windows", "Linux", "Darwin"]
        assert config["readonly_enabled"] is True


class TestGlobalSingleton:
    """测试全局单例"""
    
    def test_singleton_returns_same_instance(self):
        """测试单例返回相同实例"""
        pm1 = get_path_manager()
        pm2 = get_path_manager()
        
        assert pm1 is pm2
    
    def test_singleton_configuration(self):
        """测试单例配置"""
        pm = get_path_manager(readonly_enabled=True)
        
        assert pm.readonly_enabled is True
        assert pm.os_type in ["Windows", "Linux", "Darwin"]


class TestEdgeCases:
    """测试边界条件"""
    
    def test_empty_subdir_string(self):
        """测试空字符串子目录"""
        pm = PathManager()
        
        path1 = pm.get_data_path("")
        path2 = pm.get_data_path()
        
        assert path1 == path2
    
    def test_nested_subdir(self):
        """测试嵌套子目录"""
        pm = PathManager()
        path = pm.get_data_path("level1/level2/level3")
        
        assert "level1" in str(path)
        assert "level2" in str(path)
        assert "level3" in str(path)
        assert path.exists()
    
    def test_special_characters_in_subdir(self):
        """测试子目录中的特殊字符"""
        pm = PathManager()
        
        # 测试下划线和连字符
        path = pm.get_data_path("test_data-2024")
        assert path.exists()
