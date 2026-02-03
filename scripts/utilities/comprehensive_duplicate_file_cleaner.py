#!/usr/bin/env python3
"""
全面重复文件清理器

作为🔍 Code Review Specialist，我负责对整个代码库进行全面检查，
识别并删除重复文件，优化库结构，提升代码质量。
"""

import os
import hashlib
import json
import shutil
from datetime import datetime
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Set, Tuple

class ComprehensiveDuplicateCleaner:
    """全面重复文件清理器"""
    
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
            "htmlcov_single_test", ".kiro/memory", "backup_20260203_135753"
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
        except (IOError, OSError) as e:
            print(f"⚠️ 无法读取文件 {file_path}: {e}")
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
        print("🔍 开始扫描重复文件...")
        
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
    
    def analyze_duplicates(self):
        """分析重复文件"""
        print("📊 分析重复文件...")
        
        analysis = {
            "by_extension": defaultdict(int),
            "by_size": defaultdict(int),
            "by_directory": defaultdict(int),
            "large_duplicates": [],
            "critical_duplicates": []
        }
        
        for group in self.duplicate_groups:
            files = group["files"]
            size = group["size"]
            
            # 按扩展名分析
            for file_path in files:
                ext = file_path.suffix or "无扩展名"
                analysis["by_extension"][ext] += 1
            
            # 按大小分析
            if size > 1024 * 1024:  # > 1MB
                analysis["large_duplicates"].append(group)
            
            # 按目录分析
            for file_path in files:
                dir_name = str(file_path.parent)
                analysis["by_directory"][dir_name] += 1
            
            # 识别关键重复文件
            critical_extensions = {".py", ".js", ".ts", ".json", ".yaml", ".yml"}
            if any(f.suffix in critical_extensions for f in files):
                analysis["critical_duplicates"].append(group)
        
        return analysis
    
    def prioritize_file_for_keeping(self, files: List[Path]) -> Path:
        """优先选择要保留的文件"""
        # 优先级规则：
        # 1. 在主要目录中的文件（src/, scripts/, tests/）
        # 2. 路径较短的文件
        # 3. 最近修改的文件
        
        priority_dirs = ["src", "scripts", "tests", "docs", "config"]
        
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
    
    def create_backup_before_deletion(self, files_to_delete: List[Path]):
        """删除前创建备份"""
        if not files_to_delete:
            return
        
        backup_dir = Path(".kiro/backups/duplicate_cleanup")
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        backup_info = {
            "backup_date": datetime.now().isoformat(),
            "files": []
        }
        
        for file_path in files_to_delete:
            if file_path.exists():
                # 创建相对路径的备份
                relative_path = file_path.relative_to(self.base_path)
                backup_path = backup_dir / relative_path
                backup_path.parent.mkdir(parents=True, exist_ok=True)
                
                try:
                    shutil.copy2(file_path, backup_path)
                    backup_info["files"].append({
                        "original": str(file_path),
                        "backup": str(backup_path),
                        "size": file_path.stat().st_size
                    })
                except Exception as e:
                    print(f"⚠️ 备份文件失败 {file_path}: {e}")
        
        # 保存备份信息
        backup_info_path = backup_dir / "backup_info.json"
        with open(backup_info_path, "w", encoding="utf-8") as f:
            json.dump(backup_info, f, indent=2, ensure_ascii=False)
        
        print(f"💾 已备份 {len(backup_info['files'])} 个文件到 {backup_dir}")
    
    def clean_duplicates(self, interactive: bool = True):
        """清理重复文件"""
        print("🧹 开始清理重复文件...")
        
        files_to_delete = []
        
        for i, group in enumerate(self.duplicate_groups):
            files = group["files"]
            size = group["size"]
            
            print(f"\n📁 重复组 {i+1}/{len(self.duplicate_groups)}:")
            print(f"   文件大小: {size:,} 字节")
            
            # 显示所有重复文件
            for j, file_path in enumerate(files):
                print(f"   {j+1}. {file_path}")
            
            # 选择要保留的文件
            keep_file = self.prioritize_file_for_keeping(files)
            files_to_remove = [f for f in files if f != keep_file]
            
            print(f"   ✅ 保留: {keep_file}")
            print(f"   🗑️ 删除: {len(files_to_remove)} 个文件")
            
            if interactive:
                response = input("   确认删除这些重复文件? (y/N): ").strip().lower()
                if response != 'y':
                    print("   ⏭️ 跳过此组")
                    continue
            
            files_to_delete.extend(files_to_remove)
            
            # 记录操作
            self.cleanup_log.append({
                "group_id": i + 1,
                "kept_file": str(keep_file),
                "deleted_files": [str(f) for f in files_to_remove],
                "size_saved": size * len(files_to_remove)
            })
        
        # 创建备份
        if files_to_delete:
            self.create_backup_before_deletion(files_to_delete)
        
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
                    print(f"🗑️ 已删除: {file_path}")
            except Exception as e:
                print(f"❌ 删除失败 {file_path}: {e}")
        
        self.stats["files_deleted"] = deleted_count
        self.stats["space_saved"] = space_saved
        
        print(f"\n✅ 清理完成:")
        print(f"   删除文件: {deleted_count} 个")
        print(f"   节省空间: {space_saved:,} 字节 ({space_saved/1024/1024:.2f} MB)")
    
    def identify_other_cleanup_opportunities(self):
        """识别其他清理机会"""
        print("🔍 识别其他清理机会...")
        
        opportunities = {
            "empty_directories": [],
            "large_files": [],
            "old_backup_files": [],
            "temporary_files": [],
            "unused_test_files": []
        }
        
        for file_path in self.base_path.rglob("*"):
            if self.should_exclude_file(file_path):
                continue
            
            if file_path.is_dir():
                # 检查空目录
                try:
                    if not any(file_path.iterdir()):
                        opportunities["empty_directories"].append(file_path)
                except OSError:
                    pass
            elif file_path.is_file():
                try:
                    stat = file_path.stat()
                    
                    # 检查大文件 (>10MB)
                    if stat.st_size > 10 * 1024 * 1024:
                        opportunities["large_files"].append({
                            "path": file_path,
                            "size": stat.st_size
                        })
                    
                    # 检查备份文件
                    if any(pattern in file_path.name.lower() 
                           for pattern in ["backup", "bak", ".old", ".orig", "~"]):
                        opportunities["old_backup_files"].append(file_path)
                    
                    # 检查临时文件
                    if any(pattern in file_path.name.lower() 
                           for pattern in ["temp", "tmp", ".cache"]):
                        opportunities["temporary_files"].append(file_path)
                    
                    # 检查可能未使用的测试文件
                    if (file_path.name.startswith("test_") and 
                        file_path.suffix == ".py" and
                        stat.st_size < 1024):  # 小于1KB的测试文件可能是空的
                        opportunities["unused_test_files"].append(file_path)
                        
                except OSError:
                    pass
        
        return opportunities
    
    def generate_cleanup_report(self, analysis, opportunities):
        """生成清理报告"""
        print("📊 生成清理报告...")
        
        report = {
            "metadata": {
                "cleanup_date": datetime.now().isoformat(),
                "cleaner": "🔍 Code Review Specialist",
                "total_files_scanned": self.stats["total_files_scanned"]
            },
            "duplicate_analysis": {
                "duplicate_groups_found": len(self.duplicate_groups),
                "duplicate_files_found": self.stats["duplicate_files_found"],
                "files_deleted": self.stats["files_deleted"],
                "space_saved_bytes": self.stats["space_saved"],
                "space_saved_mb": round(self.stats["space_saved"] / 1024 / 1024, 2)
            },
            "duplicate_breakdown": {
                "by_extension": dict(analysis["by_extension"]),
                "by_directory": dict(analysis["by_directory"]),
                "large_duplicates_count": len(analysis["large_duplicates"]),
                "critical_duplicates_count": len(analysis["critical_duplicates"])
            },
            "cleanup_opportunities": {
                "empty_directories": len(opportunities["empty_directories"]),
                "large_files": len(opportunities["large_files"]),
                "old_backup_files": len(opportunities["old_backup_files"]),
                "temporary_files": len(opportunities["temporary_files"]),
                "unused_test_files": len(opportunities["unused_test_files"])
            },
            "cleanup_log": self.cleanup_log,
            "recommendations": [
                "定期运行重复文件检查",
                "建立文件命名规范避免重复",
                "使用版本控制系统管理文件历史",
                "定期清理临时文件和备份文件",
                "监控大文件的增长"
            ],
            "quality_improvements": {
                "code_organization": "删除重复文件提升了代码组织性",
                "storage_efficiency": f"节省了 {self.stats['space_saved']} 字节存储空间",
                "maintenance_burden": "减少了维护负担和混淆风险",
                "build_performance": "可能提升构建和搜索性能"
            }
        }
        
        # 保存报告
        report_path = Path(".kiro/reports/comprehensive_duplicate_cleanup_report.json")
        report_path.parent.mkdir(exist_ok=True)
        
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"✅ 清理报告已保存到: {report_path}")
        return report
    
    def execute_comprehensive_cleanup(self, interactive: bool = False):
        """执行全面清理"""
        print("🧹 开始执行全面重复文件清理...")
        print("=" * 60)
        
        try:
            # 1. 扫描重复文件
            self.scan_for_duplicates()
            
            # 2. 分析重复文件
            analysis = self.analyze_duplicates()
            
            # 3. 清理重复文件
            if self.duplicate_groups:
                self.clean_duplicates(interactive=interactive)
            else:
                print("✅ 未发现重复文件")
            
            # 4. 识别其他清理机会
            opportunities = self.identify_other_cleanup_opportunities()
            
            # 5. 生成报告
            report = self.generate_cleanup_report(analysis, opportunities)
            
            print("=" * 60)
            print("🎉 全面清理完成!")
            print(f"📊 扫描文件: {self.stats['total_files_scanned']} 个")
            print(f"🔍 重复文件组: {len(self.duplicate_groups)} 组")
            print(f"🗑️ 删除文件: {self.stats['files_deleted']} 个")
            print(f"💾 节省空间: {self.stats['space_saved']:,} 字节")
            
            # 显示其他清理机会
            if any(opportunities.values()):
                print("\n🔍 发现其他清理机会:")
                for category, items in opportunities.items():
                    if items:
                        print(f"   {category}: {len(items)} 个")
            
            return True
            
        except Exception as e:
            print(f"❌ 清理过程中出现错误: {str(e)}")
            return False

def main():
    """主函数"""
    print("🔍 全面重复文件清理器")
    print("作为Code Review Specialist，我将对整个代码库进行清理")
    print()
    
    cleaner = ComprehensiveDuplicateCleaner()
    
    # 询问是否交互模式
    interactive = input("是否使用交互模式确认每个删除操作? (y/N): ").strip().lower() == 'y'
    
    success = cleaner.execute_comprehensive_cleanup(interactive=interactive)
    
    if success:
        print("\n🎯 清理成功完成!")
        print("📚 代码库现在更加整洁和高效")
        print("💡 建议定期运行此清理工具")
    else:
        print("\n⚠️ 清理过程中遇到问题")

if __name__ == "__main__":
    main()