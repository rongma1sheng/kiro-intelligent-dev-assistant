#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置锁定管理器 - 保护.kiro配置文件不被意外修改

🔒 Security Engineer 负责配置安全保护
遵循零号铁律：只能修复"已被明确判定为缺失"的内容，不得修改任何已通过认证的章节或功能

功能：
1. 配置文件锁定/解锁
2. 修改权限验证
3. 配置完整性检查
4. 自动备份和恢复
5. 修改审计日志

使用方法：
    python3 .kiro/scripts/config_lock_manager.py lock    # 锁定配置
    python3 .kiro/scripts/config_lock_manager.py unlock  # 解锁配置
    python3 .kiro/scripts/config_lock_manager.py status  # 查看状态
    python3 .kiro/scripts/config_lock_manager.py verify  # 验证完整性
"""

import hashlib
import json
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class ConfigLockManager:
    """配置锁定管理器"""
    
    def __init__(self):
        self.kiro_root = Path(".kiro")
        self.lock_file = self.kiro_root / ".config_lock"
        self.backup_dir = self.kiro_root / "backups"
        self.audit_log = self.kiro_root / "config_audit.log"
        
        # 需要保护的配置文件
        self.protected_files = [
            # Hook配置
            "hooks/auto-deploy-test.kiro.hook",
            "hooks/context-consistency-anchor.kiro.hook", 
            "hooks/global-debug-360.kiro.hook",
            "hooks/llm-execution-monitor.kiro.hook",
            "hooks/pm-task-assignment.kiro.hook",
            "hooks/prd-sync-on-change.kiro.hook",
            "hooks/real-time-quality-guard.kiro.hook",
            "hooks/task-lifecycle-management.kiro.hook",
            "hooks/unified-quality-check.kiro.hook",
            "hooks/HOOK_ARCHITECTURE.md",
            
            # Settings配置
            "settings/llm-behavior-constraints.json",
            "settings/mcp.json",
            "settings/mcp_mac.json",
            
            # Steering配置
            "steering/silicon-valley-team-config-optimized.md",
            "steering/task-hierarchy-management.md",
            "steering/role-permission-matrix.md", 
            "steering/pm-project-planning-requirements.md",
            "steering/llm-anti-drift-system.md",
            
            # Specs配置
            "specs/unified-bug-detection-system/requirements.md",
            "specs/unified-bug-detection-system/design.md",
            "specs/unified-bug-detection-system/tasks.md",
            
            # Scripts配置
            "scripts/config_validator.py",
            "scripts/hook_trigger_tester.py",
            "scripts/trigger_analysis_report.py",
            
            # 状态报告
            "CONFIG_STATUS_REPORT.md"
        ]
        
        # 确保目录存在
        self.backup_dir.mkdir(exist_ok=True)
    
    def calculate_file_hash(self, file_path: Path) -> str:
        """计算文件哈希值"""
        if not file_path.exists():
            return ""
        
        with open(file_path, 'rb') as f:
            return hashlib.sha256(f.read()).hexdigest()
    
    def get_config_fingerprint(self) -> Dict[str, str]:
        """获取配置文件指纹"""
        fingerprint = {}
        
        for rel_path in self.protected_files:
            file_path = self.kiro_root / rel_path
            fingerprint[rel_path] = self.calculate_file_hash(file_path)
        
        return fingerprint
    
    def create_backup(self) -> str:
        """创建配置备份"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"config_backup_{timestamp}"
        backup_path = self.backup_dir / backup_name
        
        backup_path.mkdir(exist_ok=True)
        
        # 备份所有保护的文件
        for rel_path in self.protected_files:
            src_file = self.kiro_root / rel_path
            if src_file.exists():
                dst_file = backup_path / rel_path
                dst_file.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src_file, dst_file)
        
        # 保存指纹
        fingerprint = self.get_config_fingerprint()
        fingerprint_file = backup_path / "fingerprint.json"
        with open(fingerprint_file, 'w', encoding='utf-8') as f:
            json.dump(fingerprint, f, indent=2, ensure_ascii=False)
        
        self.log_audit(f"配置备份创建: {backup_name}")
        return backup_name
    
    def lock_config(self) -> bool:
        """锁定配置"""
        if self.is_locked():
            print("⚠️ 配置已经处于锁定状态")
            return True
        
        # 创建备份
        backup_name = self.create_backup()
        
        # 获取当前指纹
        fingerprint = self.get_config_fingerprint()
        
        # 创建锁定文件
        lock_data = {
            "locked_at": datetime.now().isoformat(),
            "backup_name": backup_name,
            "fingerprint": fingerprint,
            "version": "v4.0.0",
            "locked_by": "ConfigLockManager",
            "protection_level": "STRICT",
            "modification_policy": "USER_APPROVAL_REQUIRED"
        }
        
        with open(self.lock_file, 'w', encoding='utf-8') as f:
            json.dump(lock_data, f, indent=2, ensure_ascii=False)
        
        # 设置文件为只读
        self._set_readonly_permissions()
        
        self.log_audit("配置锁定激活")
        print("🔒 配置锁定成功")
        print(f"   备份名称: {backup_name}")
        print(f"   保护文件: {len(self.protected_files)} 个")
        print(f"   锁定时间: {lock_data['locked_at']}")
        
        return True
    
    def unlock_config(self, force: bool = False) -> bool:
        """解锁配置"""
        if not self.is_locked():
            print("⚠️ 配置未处于锁定状态")
            return True
        
        if not force:
            print("🚨 警告：解锁配置将允许修改关键配置文件")
            confirm = input("确认解锁？(输入 'UNLOCK' 确认): ")
            if confirm != "UNLOCK":
                print("❌ 解锁操作已取消")
                return False
        
        # 恢复文件权限
        self._restore_permissions()
        
        # 删除锁定文件
        if self.lock_file.exists():
            self.lock_file.unlink()
        
        self.log_audit("配置锁定解除")
        print("🔓 配置解锁成功")
        
        return True
    
    def is_locked(self) -> bool:
        """检查是否已锁定"""
        return self.lock_file.exists()
    
    def get_lock_status(self) -> Dict:
        """获取锁定状态"""
        if not self.is_locked():
            return {
                "locked": False,
                "message": "配置未锁定"
            }
        
        with open(self.lock_file, 'r', encoding='utf-8') as f:
            lock_data = json.load(f)
        
        return {
            "locked": True,
            "locked_at": lock_data.get("locked_at"),
            "backup_name": lock_data.get("backup_name"),
            "version": lock_data.get("version"),
            "protection_level": lock_data.get("protection_level"),
            "protected_files_count": len(self.protected_files)
        }
    
    def verify_integrity(self) -> Tuple[bool, List[str]]:
        """验证配置完整性"""
        if not self.is_locked():
            return True, ["配置未锁定，跳过完整性检查"]
        
        with open(self.lock_file, 'r', encoding='utf-8') as f:
            lock_data = json.load(f)
        
        original_fingerprint = lock_data.get("fingerprint", {})
        current_fingerprint = self.get_config_fingerprint()
        
        issues = []
        
        # 检查文件修改
        for rel_path in self.protected_files:
            original_hash = original_fingerprint.get(rel_path, "")
            current_hash = current_fingerprint.get(rel_path, "")
            
            if original_hash != current_hash:
                if original_hash == "":
                    issues.append(f"新增文件: {rel_path}")
                elif current_hash == "":
                    issues.append(f"文件丢失: {rel_path}")
                else:
                    issues.append(f"文件修改: {rel_path}")
        
        is_intact = len(issues) == 0
        
        if is_intact:
            print("✅ 配置完整性验证通过")
        else:
            print(f"❌ 发现 {len(issues)} 个完整性问题:")
            for issue in issues:
                print(f"   - {issue}")
        
        return is_intact, issues
    
    def _set_readonly_permissions(self):
        """设置文件为只读"""
        for rel_path in self.protected_files:
            file_path = self.kiro_root / rel_path
            if file_path.exists():
                # 设置为只读
                file_path.chmod(0o444)
    
    def _restore_permissions(self):
        """恢复文件权限"""
        for rel_path in self.protected_files:
            file_path = self.kiro_root / rel_path
            if file_path.exists():
                # 恢复读写权限
                file_path.chmod(0o644)
    
    def log_audit(self, message: str):
        """记录审计日志"""
        timestamp = datetime.now().isoformat()
        log_entry = f"[{timestamp}] {message}\n"
        
        with open(self.audit_log, 'a', encoding='utf-8') as f:
            f.write(log_entry)
    
    def show_status(self):
        """显示详细状态"""
        print("🔒 配置锁定管理器状态")
        print("=" * 50)
        
        status = self.get_lock_status()
        
        if status["locked"]:
            print("🔒 状态: 已锁定")
            print(f"🕐 锁定时间: {status['locked_at']}")
            print(f"📦 备份名称: {status['backup_name']}")
            print(f"📋 版本: {status['version']}")
            print(f"🛡️ 保护级别: {status['protection_level']}")
            print(f"📁 保护文件: {status['protected_files_count']} 个")
            
            # 验证完整性
            print("\n🔍 完整性检查:")
            is_intact, issues = self.verify_integrity()
            
        else:
            print("🔓 状态: 未锁定")
            print("⚠️ 配置文件可以被修改")
        
        # 显示备份信息
        backups = list(self.backup_dir.glob("config_backup_*"))
        print(f"\n📦 可用备份: {len(backups)} 个")
        for backup in sorted(backups)[-5:]:  # 显示最近5个
            print(f"   - {backup.name}")
        
        print("=" * 50)
    
    def list_protected_files(self):
        """列出受保护的文件"""
        print("🛡️ 受保护的配置文件:")
        print("=" * 50)
        
        for i, rel_path in enumerate(self.protected_files, 1):
            file_path = self.kiro_root / rel_path
            status = "✅" if file_path.exists() else "❌"
            print(f"{i:2d}. {status} {rel_path}")
        
        print("=" * 50)
        print(f"总计: {len(self.protected_files)} 个文件")


def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("配置锁定管理器")
        print()
        print("使用方法:")
        print("  python3 .kiro/scripts/config_lock_manager.py lock     # 锁定配置")
        print("  python3 .kiro/scripts/config_lock_manager.py unlock   # 解锁配置")
        print("  python3 .kiro/scripts/config_lock_manager.py status   # 查看状态")
        print("  python3 .kiro/scripts/config_lock_manager.py verify   # 验证完整性")
        print("  python3 .kiro/scripts/config_lock_manager.py list     # 列出保护文件")
        print()
        print("🔒 保护级别: STRICT - 需要用户明确批准才能修改")
        sys.exit(1)
    
    command = sys.argv[1].lower()
    manager = ConfigLockManager()
    
    if command == "lock":
        success = manager.lock_config()
        sys.exit(0 if success else 1)
    elif command == "unlock":
        force = "--force" in sys.argv
        success = manager.unlock_config(force)
        sys.exit(0 if success else 1)
    elif command == "status":
        manager.show_status()
        sys.exit(0)
    elif command == "verify":
        is_intact, issues = manager.verify_integrity()
        sys.exit(0 if is_intact else 1)
    elif command == "list":
        manager.list_protected_files()
        sys.exit(0)
    else:
        print(f"未知命令: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()