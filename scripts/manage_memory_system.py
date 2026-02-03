#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Kiro记忆系统管理脚本

提供记忆系统的维护、优化和管理功能。
"""

import sys
import os
import argparse
from pathlib import Path
from datetime import datetime, timedelta

# 添加src目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from kiro_memory import KiroMemorySystem


class MemorySystemManager:
    """记忆系统管理器"""
    
    def __init__(self):
        self.memory_system = KiroMemorySystem(
            storage_path=".kiro/memory",
            enable_learning=True
        )
    
    def show_stats(self):
        """显示系统统计信息"""
        print("📊 Kiro记忆系统统计信息")
        print("="*50)
        
        stats = self.memory_system.get_stats()
        
        print(f"总模式数: {stats.total_patterns}")
        print(f"存储大小: {stats.storage_size_mb:.2f} MB")
        
        print("\n📋 按类型分布:")
        for pattern_type, count in stats.patterns_by_type.items():
            print(f"  {pattern_type}: {count}")
        
        print(f"\n🔥 最常用模式 (前5个):")
        for i, pattern_id in enumerate(stats.most_used_patterns[:5], 1):
            pattern = self.memory_system.get_pattern(pattern_id)
            if pattern:
                print(f"  {i}. {pattern.content.get('description', pattern_id[:8])}... (使用{pattern.usage_count}次)")
    
    def search_patterns(self, query: str, max_results: int = 10):
        """搜索模式"""
        print(f"🔍 搜索: '{query}'")
        print("="*50)
        
        results = self.memory_system.search(query, max_results=max_results)
        
        if not results:
            print("❌ 没有找到匹配的模式")
            return
        
        print(f"✅ 找到 {len(results)} 个匹配的模式:")
        for i, pattern in enumerate(results, 1):
            print(f"\n{i}. [{pattern.type.value}] {pattern.content.get('description', '无描述')}")
            print(f"   ID: {pattern.id}")
            print(f"   标签: {', '.join(pattern.tags)}")
            print(f"   使用次数: {pattern.usage_count}")
            print(f"   成功率: {pattern.success_rate:.2%}")
            print(f"   置信度: {pattern.confidence:.2f}")
    
    def add_code_pattern(self, code: str, description: str, file_type: str, tags: str = ""):
        """添加代码模式"""
        tag_list = [tag.strip() for tag in tags.split(",") if tag.strip()] if tags else []
        
        pattern_id = self.memory_system.store_code_pattern(
            code=code,
            description=description,
            file_type=file_type,
            tags=tag_list
        )
        
        print(f"✅ 成功添加代码模式: {pattern_id}")
        print(f"   描述: {description}")
        print(f"   文件类型: {file_type}")
        print(f"   标签: {', '.join(tag_list)}")
    
    def add_error_solution(self, error_desc: str, solution: str, error_type: str = "general", tags: str = ""):
        """添加错误解决方案"""
        tag_list = [tag.strip() for tag in tags.split(",") if tag.strip()] if tags else []
        
        pattern_id = self.memory_system.store_error_solution(
            error_description=error_desc,
            solution=solution,
            error_type=error_type,
            tags=tag_list
        )
        
        print(f"✅ 成功添加错误解决方案: {pattern_id}")
        print(f"   错误描述: {error_desc}")
        print(f"   解决方案: {solution}")
        print(f"   错误类型: {error_type}")
    
    def add_best_practice(self, title: str, description: str, category: str, tags: str = ""):
        """添加最佳实践"""
        tag_list = [tag.strip() for tag in tags.split(",") if tag.strip()] if tags else []
        
        pattern_id = self.memory_system.store_best_practice(
            title=title,
            description=description,
            category=category,
            tags=tag_list
        )
        
        print(f"✅ 成功添加最佳实践: {pattern_id}")
        print(f"   标题: {title}")
        print(f"   分类: {category}")
        print(f"   标签: {', '.join(tag_list)}")
    
    def cleanup_old_patterns(self, days: int = 30):
        """清理旧模式"""
        print(f"🧹 清理 {days} 天前的未使用模式...")
        
        cleaned_count = self.memory_system.cleanup(days)
        print(f"✅ 清理了 {cleaned_count} 个旧模式")
    
    def optimize_system(self):
        """优化系统"""
        print("⚡ 优化记忆系统...")
        
        self.memory_system.optimize_system()
        print("✅ 系统优化完成")
    
    def export_patterns(self, output_file: str):
        """导出模式到文件"""
        print(f"📤 导出模式到 {output_file}...")
        
        # 获取所有模式
        all_patterns = self.memory_system.storage.search_patterns(limit=1000)
        
        import json
        export_data = {
            "export_time": datetime.now().isoformat(),
            "total_patterns": len(all_patterns),
            "patterns": [pattern.to_dict() for pattern in all_patterns]
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)
        
        print(f"✅ 成功导出 {len(all_patterns)} 个模式")
    
    def import_patterns(self, input_file: str):
        """从文件导入模式"""
        print(f"📥 从 {input_file} 导入模式...")
        
        import json
        with open(input_file, 'r', encoding='utf-8') as f:
            import_data = json.load(f)
        
        patterns = import_data.get('patterns', [])
        imported_count = 0
        
        for pattern_data in patterns:
            try:
                from kiro_memory.models import MemoryPattern
                pattern = MemoryPattern.from_dict(pattern_data)
                self.memory_system.storage.store_pattern(pattern)
                imported_count += 1
            except Exception as e:
                print(f"⚠️ 导入模式失败: {e}")
        
        print(f"✅ 成功导入 {imported_count} 个模式")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="Kiro记忆系统管理工具")
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # 统计信息
    subparsers.add_parser('stats', help='显示系统统计信息')
    
    # 搜索模式
    search_parser = subparsers.add_parser('search', help='搜索模式')
    search_parser.add_argument('query', help='搜索查询')
    search_parser.add_argument('--max-results', type=int, default=10, help='最大结果数')
    
    # 添加代码模式
    code_parser = subparsers.add_parser('add-code', help='添加代码模式')
    code_parser.add_argument('--code', required=True, help='代码内容')
    code_parser.add_argument('--description', required=True, help='描述')
    code_parser.add_argument('--file-type', required=True, help='文件类型')
    code_parser.add_argument('--tags', default='', help='标签（逗号分隔）')
    
    # 添加错误解决方案
    error_parser = subparsers.add_parser('add-error', help='添加错误解决方案')
    error_parser.add_argument('--error', required=True, help='错误描述')
    error_parser.add_argument('--solution', required=True, help='解决方案')
    error_parser.add_argument('--type', default='general', help='错误类型')
    error_parser.add_argument('--tags', default='', help='标签（逗号分隔）')
    
    # 添加最佳实践
    practice_parser = subparsers.add_parser('add-practice', help='添加最佳实践')
    practice_parser.add_argument('--title', required=True, help='标题')
    practice_parser.add_argument('--description', required=True, help='描述')
    practice_parser.add_argument('--category', required=True, help='分类')
    practice_parser.add_argument('--tags', default='', help='标签（逗号分隔）')
    
    # 清理
    cleanup_parser = subparsers.add_parser('cleanup', help='清理旧模式')
    cleanup_parser.add_argument('--days', type=int, default=30, help='清理多少天前的模式')
    
    # 优化
    subparsers.add_parser('optimize', help='优化系统')
    
    # 导出
    export_parser = subparsers.add_parser('export', help='导出模式')
    export_parser.add_argument('output_file', help='输出文件路径')
    
    # 导入
    import_parser = subparsers.add_parser('import', help='导入模式')
    import_parser.add_argument('input_file', help='输入文件路径')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    try:
        manager = MemorySystemManager()
        
        if args.command == 'stats':
            manager.show_stats()
        elif args.command == 'search':
            manager.search_patterns(args.query, args.max_results)
        elif args.command == 'add-code':
            manager.add_code_pattern(args.code, args.description, args.file_type, args.tags)
        elif args.command == 'add-error':
            manager.add_error_solution(args.error, args.solution, args.type, args.tags)
        elif args.command == 'add-practice':
            manager.add_best_practice(args.title, args.description, args.category, args.tags)
        elif args.command == 'cleanup':
            manager.cleanup_old_patterns(args.days)
        elif args.command == 'optimize':
            manager.optimize_system()
        elif args.command == 'export':
            manager.export_patterns(args.output_file)
        elif args.command == 'import':
            manager.import_patterns(args.input_file)
        
    except Exception as e:
        print(f"❌ 执行失败: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())