#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
清空Git仓库所有内容
删除所有文件，准备上传新的干净版本
"""

import os
import sys
import subprocess
from pathlib import Path
from datetime import datetime

# 设置UTF-8编码（Windows兼容）
if sys.platform.startswith('win'):
    os.environ['PYTHONIOENCODING'] = 'utf-8'

class GitRepositoryCleaner:
    def __init__(self):
        self.timestamp = datetime.now()
        
    def run_git_command(self, command):
        """运行Git命令"""
        try:
            result = subprocess.run(command, shell=True, capture_output=True, text=True, encoding='utf-8')
            return result.returncode == 0, result.stdout, result.stderr
        except Exception as e:
            return False, "", str(e)
    
    def clear_git_repository(self):
        """清空Git仓库"""
        print("开始清空Git仓库...")
        
        # 1. 删除所有文件（保留.git目录）
        print("1. 删除所有跟踪的文件...")
        success, stdout, stderr = self.run_git_command("git rm -rf .")
        if success:
            print("   成功删除所有跟踪的文件")
        else:
            print(f"   删除文件失败: {stderr}")
        
        # 2. 提交删除操作
        print("2. 提交删除操作...")
        commit_msg = f"清空仓库 - 准备上传新版本 {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
        success, stdout, stderr = self.run_git_command(f'git commit -m "{commit_msg}"')
        if success:
            print("   成功提交删除操作")
        else:
            print(f"   提交失败: {stderr}")
        
        # 3. 强制推送到远程仓库
        print("3. 强制推送到远程仓库...")
        success, stdout, stderr = self.run_git_command("git push --force-with-lease origin main")
        if success:
            print("   成功推送到远程仓库")
        else:
            print(f"   推送失败: {stderr}")
            # 尝试普通推送
            print("   尝试普通强制推送...")
            success, stdout, stderr = self.run_git_command("git push --force origin main")
            if success:
                print("   强制推送成功")
            else:
                print(f"   强制推送也失败: {stderr}")
        
        return success
    
    def check_remote_repository(self):
        """检查远程仓库状态"""
        print("\n检查远程仓库状态...")
        
        # 获取远程仓库信息
        success, stdout, stderr = self.run_git_command("git ls-remote --heads origin")
        if success:
            print("远程仓库连接正常")
            if stdout.strip():
                print("远程仓库内容:")
                print(stdout)
            else:
                print("远程仓库为空")
        else:
            print(f"无法连接远程仓库: {stderr}")
        
        return success
    
    def run_cleanup(self):
        """运行完整清理"""
        print("Git仓库清理工具")
        print("=" * 50)
        print(f"时间: {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # 检查Git状态
        success, stdout, stderr = self.run_git_command("git status")
        if not success:
            print("错误: 当前目录不是Git仓库")
            return False
        
        # 清空仓库
        success = self.clear_git_repository()
        
        # 检查远程仓库
        self.check_remote_repository()
        
        if success:
            print("\n" + "="*50)
            print("Git仓库清理完成！")
            print("="*50)
            print("远程仓库已清空，可以上传新内容")
        else:
            print("\n" + "="*50)
            print("Git仓库清理失败！")
            print("="*50)
            print("请检查网络连接和Git配置")
        
        return success

def main():
    """主函数"""
    cleaner = GitRepositoryCleaner()
    return cleaner.run_cleanup()

if __name__ == "__main__":
    main()