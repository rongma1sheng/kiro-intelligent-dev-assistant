#!/usr/bin/env python3
"""
MIA系统项目清理脚本
删除所有临时文件和过程文档，只保留核心必需文件
"""

import os
import shutil
from pathlib import Path

class ProjectCleaner:
    def __init__(self):
        self.root = Path(".")
        self.deleted_files = []
        self.deleted_dirs = []
        self.errors = []
        
    def clean(self, dry_run=True):
        """清理项目
        
        Args:
            dry_run: True=仅显示将删除的文件，False=实际删除
        """
        print("="*80)
        print("MIA系统项目清理")
        print("="*80)
        print(f"模式: {'预览模式（不会实际删除）' if dry_run else '执行模式（将实际删除）'}")
        print()
        
        # 要删除的文件列表
        files_to_delete = [
            # 过程文档
            "00_核心文档/CONSISTENCY_CHECK_REPORT.md",
            "00_核心文档/CONSISTENCY_CHECK_FINAL.md",
            "00_核心文档/CONSISTENCY_ACHIEVED.md",
            "00_核心文档/FULL_COMPARISON_REPORT.md",
            "00_核心文档/MISSING_CONTENT_ANALYSIS.md",
            "00_核心文档/DOCUMENTATION_COMPLETION_REPORT.md",
            "00_核心文档/FULL_ALIGNMENT_REPORT.md",
            
            # 临时脚本
            "scripts/full_comparison.py",
            "scripts/check_consistency.py",
            "scripts/analyze_whitepaper_completeness.py",
            "cleanup_new_folder.py",
            
            # 临时总结
            "FINAL_SUMMARY.md",
            "WORK_COMPLETED.md",
            "START_HERE.md",
        ]
        
        # 要删除的目录列表
        dirs_to_delete = [
            "01_开发过程文档",
            "02_清理脚本",
            "03_整理脚本",
        ]
        
        # 删除文件
        print("📄 将删除的文件:")
        print("-" * 80)
        for file_path in files_to_delete:
            full_path = self.root / file_path
            if full_path.exists():
                print(f"  ❌ {file_path}")
                if not dry_run:
                    try:
                        full_path.unlink()
                        self.deleted_files.append(file_path)
                    except Exception as e:
                        self.errors.append(f"删除文件失败 {file_path}: {e}")
            else:
                print(f"  ⚠️  {file_path} (不存在)")
        
        print()
        
        # 删除目录
        print("📁 将删除的目录:")
        print("-" * 80)
        for dir_path in dirs_to_delete:
            full_path = self.root / dir_path
            if full_path.exists():
                file_count = len(list(full_path.rglob("*")))
                print(f"  ❌ {dir_path}/ ({file_count} 个文件)")
                if not dry_run:
                    try:
                        shutil.rmtree(full_path)
                        self.deleted_dirs.append(dir_path)
                    except Exception as e:
                        self.errors.append(f"删除目录失败 {dir_path}: {e}")
            else:
                print(f"  ⚠️  {dir_path}/ (不存在)")
        
        print()
        
        # 显示结果
        self.show_summary(dry_run)
        
    def show_summary(self, dry_run):
        """显示清理摘要"""
        print("="*80)
        print("清理摘要")
        print("="*80)
        
        if dry_run:
            print("⚠️  这是预览模式，没有实际删除任何文件")
            print()
            print("如果确认要删除，请运行:")
            print("  python scripts/cleanup_project.py --execute")
        else:
            print(f"✅ 已删除 {len(self.deleted_files)} 个文件")
            print(f"✅ 已删除 {len(self.deleted_dirs)} 个目录")
            
            if self.errors:
                print(f"\n❌ 发生 {len(self.errors)} 个错误:")
                for error in self.errors:
                    print(f"  - {error}")
            else:
                print("\n🎉 清理完成！项目已精简。")
        
        print()
        print("保留的核心文件:")
        print("  ✅ 00_核心文档/ (9个核心文档)")
        print("  ✅ scripts/ (4个核心脚本)")
        print("  ✅ 根目录配置文件 (7个)")
        print("  ✅ 源代码和测试目录结构")

def main():
    import sys
    
    cleaner = ProjectCleaner()
    
    # 检查命令行参数
    if len(sys.argv) > 1 and sys.argv[1] == "--execute":
        # 二次确认
        print("⚠️  警告: 这将永久删除临时文件和过程文档！")
        print()
        response = input("确认要继续吗？(输入 'yes' 确认): ")
        
        if response.lower() == 'yes':
            cleaner.clean(dry_run=False)
        else:
            print("已取消清理操作")
    else:
        # 预览模式
        cleaner.clean(dry_run=True)

if __name__ == "__main__":
    main()
