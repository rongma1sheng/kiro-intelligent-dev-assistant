#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Hook触发测试 - 测试文件版本

🧪 测试目的：验证 real-time-quality-guard.kiro.hook 的 fileEdited 触发功能
📁 触发条件：编辑 tests/**/*.py 文件
⚡ 预期行为：应该触发测试文件质量防护系统
"""

import pytest

def test_hook_trigger_for_tests():
    """测试Hook触发功能 - 测试文件版本"""
    print("🧪 Hook fileEdited 触发测试 (测试文件)")
    print("✅ 如果看到这个消息，说明测试文件编辑成功")
    assert True

if __name__ == "__main__":
    test_hook_trigger_for_tests()