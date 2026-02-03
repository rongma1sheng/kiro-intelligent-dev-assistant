#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Hook触发测试文件

🧪 测试目的：验证 global-debug-360.kiro.hook 的 fileEdited 触发功能
📁 触发条件：编辑 src/**/*.py 文件
⚡ 预期行为：应该触发源代码360度调试系统
"""

def test_hook_trigger():
    """测试Hook触发功能"""
    print("🧪 Hook fileEdited 触发测试")
    print("✅ 如果看到这个消息，说明文件编辑成功")
    return True

if __name__ == "__main__":
    test_hook_trigger()