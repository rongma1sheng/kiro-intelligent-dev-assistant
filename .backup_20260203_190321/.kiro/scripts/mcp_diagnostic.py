#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MCP配置诊断工具 v1.0

检查MCP服务器配置和连接状态，诊断常见问题
"""

import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Any, Tuple


class MCPDiagnostic:
    """MCP配置诊断器"""
    
    def __init__(self):
        self.results = []
        self.config_files = [
            ".kiro/settings/mcp.json",
            ".kiro/settings/mcp_mac.json", 
            ".kiro/settings/mcp_windows_fixed.json"
        ]
    
    def run_full_diagnostic(self) -> bool:
        """运行完整诊断"""
        print("🔍 MCP配置诊断开始...")
        print("=" * 60)
        
        # 1. 检查Node.js环境
        self._check_nodejs_environment()
        
        # 2. 检查MCP配置文件
        self._check_config_files()
        
        # 3. 测试MCP服务器连接
        self._test_mcp_servers()
        
        # 4. 检查权限和路径
        self._check_permissions_and_paths()
        
        # 5. 生成诊断报告
        return self._generate_report()
    
    def _check_nodejs_environment(self):
        """检查Node.js环境"""
        print("\n📦 检查Node.js环境...")
        
        try:
            # 检查Node.js版本
            result = subprocess.run(["node", "--version"], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                node_version = result.stdout.strip()
                print(f"✅ Node.js版本: {node_version}")
                self.results.append(("nodejs", True, f"Node.js {node_version}"))
            else:
                print("❌ Node.js未安装或不可用")
                self.results.append(("nodejs", False, "Node.js不可用"))
                return
        except Exception as e:
            print(f"❌ Node.js检查失败: {e}")
            self.results.append(("nodejs", False, f"检查失败: {e}"))
            return
        
        try:
            # 检查npx版本
            result = subprocess.run(["npx", "--version"], 
                                  capture_output=True, text=True, timeout=10, shell=True)
            if result.returncode == 0:
                npx_version = result.stdout.strip()
                print(f"✅ npx版本: {npx_version}")
                self.results.append(("npx", True, f"npx {npx_version}"))
            else:
                print("❌ npx不可用")
                self.results.append(("npx", False, "npx不可用"))
        except Exception as e:
            print(f"❌ npx检查失败: {e}")
            self.results.append(("npx", False, f"检查失败: {e}"))
    
    def _check_config_files(self):
        """检查MCP配置文件"""
        print("\n📋 检查MCP配置文件...")
        
        for config_file in self.config_files:
            config_path = Path(config_file)
            
            if not config_path.exists():
                print(f"⚠️ 配置文件不存在: {config_file}")
                self.results.append((f"config_{config_path.name}", False, "文件不存在"))
                continue
            
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                
                # 验证配置结构
                if "mcpServers" not in config:
                    print(f"❌ 配置文件格式错误: {config_file}")
                    self.results.append((f"config_{config_path.name}", False, "缺少mcpServers"))
                    continue
                
                servers = config["mcpServers"]
                print(f"✅ 配置文件有效: {config_file} ({len(servers)} 个服务器)")
                self.results.append((f"config_{config_path.name}", True, f"{len(servers)} 个服务器"))
                
                # 检查每个服务器配置
                for server_name, server_config in servers.items():
                    if not server_config.get("command"):
                        print(f"  ❌ 服务器 {server_name}: 缺少command")
                        self.results.append((f"server_{server_name}", False, "缺少command"))
                    elif server_config.get("disabled", False):
                        print(f"  ⚠️ 服务器 {server_name}: 已禁用")
                        self.results.append((f"server_{server_name}", False, "已禁用"))
                    else:
                        print(f"  ✅ 服务器 {server_name}: 配置正常")
                        self.results.append((f"server_{server_name}", True, "配置正常"))
                        
            except json.JSONDecodeError as e:
                print(f"❌ 配置文件JSON格式错误: {config_file} - {e}")
                self.results.append((f"config_{config_path.name}", False, f"JSON错误: {e}"))
            except Exception as e:
                print(f"❌ 读取配置文件失败: {config_file} - {e}")
                self.results.append((f"config_{config_path.name}", False, f"读取失败: {e}"))
    
    def _test_mcp_servers(self):
        """测试MCP服务器连接"""
        print("\n🔌 测试MCP服务器连接...")
        
        # 测试filesystem服务器
        self._test_filesystem_server()
        
        # 测试memory服务器
        self._test_memory_server()
    
    def _test_filesystem_server(self):
        """测试filesystem服务器"""
        print("\n  📁 测试Filesystem服务器...")
        
        try:
            # 测试MCP包是否可以正确下载和执行
            cmd = ["npx", "-y", "@modelcontextprotocol/server-filesystem", "."]
            
            process = subprocess.Popen(
                cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                text=True,
                cwd=".",
                shell=True
            )
            
            # 等待2秒看是否能正常启动
            time.sleep(2)
            
            if process.poll() is None:
                # 进程仍在运行，说明MCP服务器正常启动
                print("  ✅ Filesystem服务器可正常启动")
                self.results.append(("filesystem_server", True, "可正常启动"))
                process.terminate()
                try:
                    process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    process.kill()
            else:
                # 进程已退出，可能是错误
                stdout, stderr = process.communicate()
                if "running on stdio" in stdout or "running on stdio" in stderr:
                    # 实际上是正常的，MCP服务器输出了启动信息后等待输入
                    print("  ✅ Filesystem服务器正常（stdio模式）")
                    self.results.append(("filesystem_server", True, "正常启动"))
                else:
                    print(f"  ❌ Filesystem服务器启动异常")
                    print(f"     输出: {stdout[:100]}...")
                    print(f"     错误: {stderr[:100]}...")
                    self.results.append(("filesystem_server", False, f"启动异常"))
                
        except Exception as e:
            print(f"  ❌ Filesystem服务器测试异常: {e}")
            self.results.append(("filesystem_server", False, f"测试异常: {e}"))
    
    def _test_memory_server(self):
        """测试memory服务器"""
        print("\n  🧠 测试Memory服务器...")
        
        try:
            # 测试memory服务器启动
            cmd = ["npx", "-y", "@modelcontextprotocol/server-memory"]
            
            process = subprocess.Popen(
                cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                text=True,
                shell=True
            )
            
            # 等待2秒看是否能正常启动
            time.sleep(2)
            
            if process.poll() is None:
                # 进程仍在运行，说明MCP服务器正常启动
                print("  ✅ Memory服务器可正常启动")
                self.results.append(("memory_server", True, "可正常启动"))
                process.terminate()
                try:
                    process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    process.kill()
            else:
                # 进程已退出，检查是否是正常的stdio等待
                stdout, stderr = process.communicate()
                if "running on stdio" in stdout or "running on stdio" in stderr:
                    print("  ✅ Memory服务器正常（stdio模式）")
                    self.results.append(("memory_server", True, "正常启动"))
                else:
                    print(f"  ❌ Memory服务器启动异常")
                    print(f"     输出: {stdout[:100]}...")
                    print(f"     错误: {stderr[:100]}...")
                    self.results.append(("memory_server", False, f"启动异常"))
                
        except Exception as e:
            print(f"  ❌ Memory服务器测试异常: {e}")
            self.results.append(("memory_server", False, f"测试异常: {e}"))                
        except Exception as e:
            print(f"  ❌ Memory服务器测试异常: {e}")
            self.results.append(("memory_server", False, f"测试异常: {e}"))
    
    def _check_permissions_and_paths(self):
        """检查权限和路径"""
        print("\n🔐 检查权限和路径...")
        
        # 检查工作目录权限
        try:
            test_file = Path("C:\\mia\\.kiro\\test_write_permission.tmp")
            test_file.write_text("test")
            test_file.unlink()
            print("✅ 工作目录写权限正常")
            self.results.append(("write_permission", True, "写权限正常"))
        except Exception as e:
            print(f"❌ 工作目录写权限问题: {e}")
            self.results.append(("write_permission", False, f"写权限问题: {e}"))
        
        # 检查内存存储目录
        memory_dir = Path("C:\\mia\\.kiro\\memory")
        try:
            memory_dir.mkdir(parents=True, exist_ok=True)
            print("✅ 内存存储目录创建成功")
            self.results.append(("memory_dir", True, "目录创建成功"))
        except Exception as e:
            print(f"❌ 内存存储目录创建失败: {e}")
            self.results.append(("memory_dir", False, f"目录创建失败: {e}"))
    
    def _generate_report(self) -> bool:
        """生成诊断报告"""
        print("\n" + "=" * 60)
        print("📊 MCP诊断报告")
        print("=" * 60)
        
        total_checks = len(self.results)
        passed_checks = sum(1 for _, passed, _ in self.results if passed)
        failed_checks = total_checks - passed_checks
        
        print(f"总检查项: {total_checks}")
        print(f"通过: {passed_checks}")
        print(f"失败: {failed_checks}")
        print(f"通过率: {(passed_checks/total_checks*100):.1f}%")
        print()
        
        # 显示失败的检查项
        if failed_checks > 0:
            print("❌ 失败的检查项:")
            for check_name, passed, message in self.results:
                if not passed:
                    print(f"  - {check_name}: {message}")
            print()
        
        # 生成修复建议
        print("🔧 修复建议:")
        
        # 检查Node.js相关问题
        nodejs_failed = any(name in ["nodejs", "npx"] and not passed 
                           for name, passed, _ in self.results)
        if nodejs_failed:
            print("1. 安装或更新Node.js:")
            print("   - 访问 https://nodejs.org 下载最新版本")
            print("   - 确保npx可用")
            print()
        
        # 检查服务器启动问题
        server_failed = any("server" in name and not passed 
                           for name, passed, _ in self.results)
        if server_failed:
            print("2. 修复MCP服务器问题:")
            print("   - 使用修复后的配置文件: .kiro/settings/mcp_windows_fixed.json")
            print("   - 检查网络连接和防火墙设置")
            print("   - 清理npm缓存: npm cache clean --force")
            print()
        
        # 检查权限问题
        permission_failed = any("permission" in name and not passed 
                               for name, passed, _ in self.results)
        if permission_failed:
            print("3. 修复权限问题:")
            print("   - 以管理员身份运行Kiro")
            print("   - 检查文件夹权限设置")
            print()
        
        print("=" * 60)
        
        if failed_checks == 0:
            print("🎉 所有MCP配置检查通过！")
            return True
        else:
            print("💥 发现MCP配置问题，请按照修复建议处理")
            return False


def main():
    """主函数"""
    diagnostic = MCPDiagnostic()
    success = diagnostic.run_full_diagnostic()
    return 0 if success else 1


if __name__ == "__main__":
    exit(main())