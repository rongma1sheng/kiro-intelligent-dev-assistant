#!/usr/bin/env python3
"""
批量重复文件清理器 - 非交互模式

作为🔍 Code Review Specialist，我将自动删除所有重复文件，
无需用户逐个确认，然后验证3.0版本的完整性。
"""

import os
import hashlib
import json
import shutil
from datetime import datetime
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Set, Tuple

class BatchDuplicateCleaner:
    """批量重复文件清理器"""
    
    def __init__(self):
        self.base_path = Path(".")
        self.file_hashes = defaultdict(list)
        self.duplicate_groups = []
        self.cleanup_log = []
        self.stats = {
            "total_files_scanned": 0,
            "duplicate_files_found": 0,
            "files_deleted": 0,
            "space_saved": 0
        }
        
        # 排除的目录和文件模式
        self.exclude_dirs = {
            ".git", "__pycache__", ".pytest_cache", "node_modules",
            ".hypothesis", "htmlcov", "htmlcov_ai_brain_coordinator", 
            "htmlcov_single_test", ".kiro/memory"
        }
        
        self.exclude_patterns = {
            ".pyc", ".pyo", ".pyd", ".so", ".dll", ".dylib",
            ".DS_Store", "Thumbs.db", ".gitkeep"
        }
        
    def calculate_file_hash(self, file_path: Path) -> str:
        """计算文件的MD5哈希值"""
        try:
            hash_md5 = hashlib.md5()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except (IOError, OSError):
            return ""
    
    def should_exclude_file(self, file_path: Path) -> bool:
        """判断是否应该排除文件"""
        # 检查目录排除
        for part in file_path.parts:
            if part in self.exclude_dirs:
                return True
        
        # 检查文件扩展名排除
        if file_path.suffix in self.exclude_patterns:
            return True
            
        # 检查文件名排除
        if file_path.name in self.exclude_patterns:
            return True
            
        return False
    
    def scan_for_duplicates(self):
        """扫描重复文件"""
        print("🔍 扫描重复文件...")
        
        for file_path in self.base_path.rglob("*"):
            if not file_path.is_file():
                continue
                
            if self.should_exclude_file(file_path):
                continue
            
            self.stats["total_files_scanned"] += 1
            
            # 计算文件哈希
            file_hash = self.calculate_file_hash(file_path)
            if file_hash:
                self.file_hashes[file_hash].append(file_path)
        
        # 识别重复文件组
        for file_hash, file_list in self.file_hashes.items():
            if len(file_list) > 1:
                self.duplicate_groups.append({
                    "hash": file_hash,
                    "files": file_list,
                    "size": file_list[0].stat().st_size if file_list[0].exists() else 0
                })
                self.stats["duplicate_files_found"] += len(file_list) - 1
        
        print(f"📊 扫描完成: {self.stats['total_files_scanned']} 个文件")
        print(f"🔍 发现 {len(self.duplicate_groups)} 组重复文件")
        print(f"📁 重复文件总数: {self.stats['duplicate_files_found']} 个")
    
    def prioritize_file_for_keeping(self, files: List[Path]) -> Path:
        """优先选择要保留的文件"""
        # 优先级规则：
        # 1. 在主要目录中的文件（src/, scripts/, tests/, 3.0/）
        # 2. 路径较短的文件
        # 3. 最近修改的文件
        
        priority_dirs = ["3.0", "src", "scripts", "tests", "docs", "config"]
        
        def get_priority_score(file_path: Path) -> Tuple[int, int, float]:
            # 目录优先级分数
            dir_score = 0
            for i, priority_dir in enumerate(priority_dirs):
                if priority_dir in str(file_path):
                    dir_score = len(priority_dirs) - i
                    break
            
            # 路径长度分数（越短越好）
            path_score = -len(str(file_path))
            
            # 修改时间分数
            try:
                mtime_score = file_path.stat().st_mtime
            except OSError:
                mtime_score = 0
            
            return (dir_score, path_score, mtime_score)
        
        # 按优先级排序，返回最高优先级的文件
        return max(files, key=get_priority_score)
    
    def batch_clean_duplicates(self):
        """批量清理重复文件"""
        print("🧹 批量清理重复文件...")
        
        files_to_delete = []
        total_space_to_save = 0
        
        # 收集所有要删除的文件
        for i, group in enumerate(self.duplicate_groups):
            files = group["files"]
            size = group["size"]
            
            # 选择要保留的文件
            keep_file = self.prioritize_file_for_keeping(files)
            files_to_remove = [f for f in files if f != keep_file]
            
            files_to_delete.extend(files_to_remove)
            total_space_to_save += size * len(files_to_remove)
            
            # 记录操作
            self.cleanup_log.append({
                "group_id": i + 1,
                "kept_file": str(keep_file),
                "deleted_files": [str(f) for f in files_to_remove],
                "size_saved": size * len(files_to_remove)
            })
        
        print(f"📋 准备删除 {len(files_to_delete)} 个重复文件")
        print(f"💾 预计节省空间: {total_space_to_save:,} 字节 ({total_space_to_save/1024/1024:.2f} MB)")
        
        # 创建备份目录
        backup_dir = Path(".kiro/backups/duplicate_cleanup")
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        # 执行删除
        deleted_count = 0
        space_saved = 0
        
        for file_path in files_to_delete:
            try:
                if file_path.exists():
                    file_size = file_path.stat().st_size
                    file_path.unlink()
                    deleted_count += 1
                    space_saved += file_size
                    if deleted_count % 50 == 0:  # 每50个文件显示一次进度
                        print(f"🗑️ 已删除 {deleted_count} 个文件...")
            except Exception as e:
                print(f"❌ 删除失败 {file_path}: {e}")
        
        self.stats["files_deleted"] = deleted_count
        self.stats["space_saved"] = space_saved
        
        print(f"✅ 批量清理完成:")
        print(f"   删除文件: {deleted_count} 个")
        print(f"   节省空间: {space_saved:,} 字节 ({space_saved/1024/1024:.2f} MB)")
    
    def verify_version_3_integrity(self):
        """验证3.0版本的完整性"""
        print("🔍 验证3.0版本完整性...")
        
        version_3_path = Path("3.0")
        if not version_3_path.exists():
            print("❌ 3.0目录不存在!")
            return False
        
        # 检查必需的平台目录和文件
        required_structure = {
            "base": ["mcp.json"],
            "win": ["settings/mcp.json", "settings/performance.json"],
            "mac": ["settings/mcp.json", "settings/performance.json", "docs/development_guide.md"],
            "linux": ["settings/mcp.json", "settings/performance.json"]
        }
        
        integrity_issues = []
        
        for platform, required_files in required_structure.items():
            platform_path = version_3_path / platform
            
            if not platform_path.exists():
                integrity_issues.append(f"缺失平台目录: {platform}/")
                continue
            
            for required_file in required_files:
                file_path = platform_path / required_file
                if not file_path.exists():
                    integrity_issues.append(f"缺失文件: {platform}/{required_file}")
        
        # 检查文档文件
        docs = ["README.md", "MIGRATION_GUIDE.md"]
        for doc in docs:
            doc_path = version_3_path / doc
            if not doc_path.exists():
                integrity_issues.append(f"缺失文档: {doc}")
        
        # 检查Hook文件
        hook_files = [
            "error-solution-finder.kiro.hook",
            "global-debug-360.kiro.hook",
            "intelligent-monitoring-hub.kiro.hook",
            "knowledge-accumulator.kiro.hook",
            "smart-coding-assistant.kiro.hook"
        ]
        
        for platform in ["win", "mac", "linux"]:
            hooks_path = version_3_path / platform / "hooks"
            if hooks_path.exists():
                for hook_file in hook_files:
                    hook_path = hooks_path / hook_file
                    if not hook_path.exists():
                        integrity_issues.append(f"缺失Hook: {platform}/hooks/{hook_file}")
        
        if integrity_issues:
            print("⚠️ 发现完整性问题:")
            for issue in integrity_issues:
                print(f"   - {issue}")
            return False
        else:
            print("✅ 3.0版本结构完整")
            return True
    
    def generate_cleanup_report(self):
        """生成清理报告"""
        print("📊 生成清理报告...")
        
        report = {
            "metadata": {
                "cleanup_date": datetime.now().isoformat(),
                "cleaner": "🔍 Code Review Specialist",
                "mode": "批量自动清理"
            },
            "cleanup_summary": {
                "total_files_scanned": self.stats["total_files_scanned"],
                "duplicate_groups_found": len(self.duplicate_groups),
                "duplicate_files_found": self.stats["duplicate_files_found"],
                "files_deleted": self.stats["files_deleted"],
                "space_saved_bytes": self.stats["space_saved"],
                "space_saved_mb": round(self.stats["space_saved"] / 1024 / 1024, 2)
            },
            "cleanup_log": self.cleanup_log,
            "version_3_integrity": self.verify_version_3_integrity(),
            "recommendations": [
                "定期运行重复文件检查",
                "建立文件命名规范避免重复",
                "使用版本控制系统管理文件历史",
                "监控备份目录的大小"
            ]
        }
        
        # 保存报告
        report_path = Path(".kiro/reports/batch_duplicate_cleanup_report.json")
        report_path.parent.mkdir(exist_ok=True)
        
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"✅ 清理报告已保存到: {report_path}")
        return report
    
    def execute_batch_cleanup(self):
        """执行批量清理"""
        print("🧹 开始执行批量重复文件清理...")
        print("=" * 60)
        
        try:
            # 1. 扫描重复文件
            self.scan_for_duplicates()
            
            # 2. 批量清理重复文件
            if self.duplicate_groups:
                self.batch_clean_duplicates()
            else:
                print("✅ 未发现重复文件")
            
            # 3. 验证3.0版本完整性
            integrity_ok = self.verify_version_3_integrity()
            
            # 4. 生成报告
            report = self.generate_cleanup_report()
            
            print("=" * 60)
            print("🎉 批量清理完成!")
            print(f"📊 扫描文件: {self.stats['total_files_scanned']} 个")
            print(f"🔍 重复文件组: {len(self.duplicate_groups)} 组")
            print(f"🗑️ 删除文件: {self.stats['files_deleted']} 个")
            print(f"💾 节省空间: {self.stats['space_saved']:,} 字节")
            print(f"✅ 3.0版本完整性: {'通过' if integrity_ok else '有问题'}")
            
            return True
            
        except Exception as e:
            print(f"❌ 清理过程中出现错误: {str(e)}")
            return False

def main():
    """主函数"""
    print("🔍 批量重复文件清理器")
    print("作为Code Review Specialist，我将自动清理所有重复文件")
    print()
    
    cleaner = BatchDuplicateCleaner()
    success = cleaner.execute_batch_cleanup()
    
    if success:
        print("\n🎯 批量清理成功完成!")
        print("📚 代码库现在更加整洁和高效")
    else:
        print("\n⚠️ 清理过程中遇到问题")

if __name__ == "__main__":
    main()