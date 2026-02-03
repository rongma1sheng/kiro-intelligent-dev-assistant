#!/usr/bin/env python3
"""
Mac配置适配器
将所有配置文件适配到macOS环境

执行者：DevOps Engineer
目标：完成Mac适配和Git库管理
"""

import json
import os
from datetime import datetime

def create_mac_mcp_config():
    """创建Mac MCP配置"""
    print("🍎 创建Mac MCP配置...")
    
    mac_config = {
        "_extends": "mcp.json",
        "_metadata": {
            "platform": "darwin",
            "description": "macOS优化MCP配置",
            "last_updated": datetime.now().isoformat()
        },
        "mcpServers": {
            "filesystem": {
                "env": {
                    "SHELL": "/bin/zsh",
                    "PATH": "/opt/homebrew/bin:/usr/local/bin:$PATH",
                    "TMPDIR": "/tmp",
                    "HOME": "$HOME"
                }
            },
            "memory": {
                "env": {
                    "TMPDIR": "/tmp",
                    "MEMORY_STORAGE_PATH": "$HOME/.kiro/memory"
                }
            }
        },
        "global_settings": {
            "connection_timeout": 45000,
            "max_concurrent_servers": 8,
            "darwin_specific": {
                "use_zsh_shell": True,
                "homebrew_support": True,
                "path_separator": "/"
            }
        }
    }
    
    with open(".kiro/settings/mcp_darwin.json", 'w', encoding='utf-8') as f:
        json.dump(mac_config, f, ensure_ascii=False, indent=2)
    
    print("✅ Mac MCP配置已创建")

def create_mac_development_hook():
    """创建Mac开发环境Hook"""
    print("🪝 创建Mac开发Hook...")
    
    mac_hook = {
        "name": "Mac开发环境优化",
        "version": "1.0.0",
        "description": "针对macOS开发环境的优化",
        "when": {
            "type": "userTriggered"
        },
        "then": {
            "type": "askAgent",
            "prompt": """🍎 Mac开发环境优化已激活

执行macOS特定检查：
1. Homebrew环境验证
2. Xcode工具链检查
3. Python/Node.js环境配置
4. Git配置优化

提供具体的优化建议。"""
        },
        "_metadata": {
            "platform": "darwin",
            "priority": "medium",
            "created": datetime.now().isoformat()
        }
    }
    
    with open(".kiro/hooks/mac-development-environment.kiro.hook", 'w', encoding='utf-8') as f:
        json.dump(mac_hook, f, ensure_ascii=False, indent=2)
    
    print("✅ Mac开发Hook已创建")

def execute_mac_adaptation():
    """执行Mac适配"""
    print("🚀 开始Mac配置适配...")
    
    try:
        create_mac_mcp_config()
        create_mac_development_hook()
        
        print("🎉 Mac配置适配完成！")
        return True
    except Exception as e:
        print(f"❌ 适配失败: {e}")
        return False

if __name__ == "__main__":
    execute_mac_adaptation()