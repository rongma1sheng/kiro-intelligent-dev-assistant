#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Emoji字符清理工具
批量移除所有Python文件中的emoji字符，确保Windows GBK编码兼容性
"""

import os
import re
import sys
from pathlib import Path
from typing import List, Dict, Tuple

class EmojiRemover:
    def __init__(self):
        # 常见emoji字符模式
        self.emoji_patterns = [
            r'[AI]|[TOOL]|[BUILD]|[DATA]|[FAST]|[TARGET]|[START]|[IDEA]|[SEARCH]|[CHART]|[REPAIR]|[STAR]|[MAGIC]|[SHINE]|[STRONG]|[ART]|[HOT]|[GEAR]|[NOTE]',
            r'|||||||||||||||',
            r'||||||||||||||||',
            r'||||||||||||||||',
            r'|||||||||||||||',
            r'|||||||||||||||',
            r'|||||||||||||||',
            r'|||||[PARTY]|[APPLE]|[HOOK]|[BOOK]|[SYNC]|[START]|[SEARCH]|[REPAIR]'
        ]
        
        # 编译正则表达式
        self.emoji_regex = re.compile('|'.join(self.emoji_patterns))
        
        # 替换映射
        self.emoji_replacements = {
            '[AI]': '[AI]',
            '[TOOL]': '[TOOL]',
            '[BUILD]': '[BUILD]',
            '[DATA]': '[DATA]',
            '[FAST]': '[FAST]',
            '[TARGET]': '[TARGET]',
            '[START]': '[START]',
            '[IDEA]': '[IDEA]',
            '[SEARCH]': '[SEARCH]',
            '[CHART]': '[CHART]',
            '[REPAIR]': '[REPAIR]',
            '[STAR]': '[STAR]',
            '[MAGIC]': '[MAGIC]',
            '[SHINE]': '[SHINE]',
            '[STRONG]': '[STRONG]',
            '[ART]': '[ART]',
            '[HOT]': '[HOT]',
            '[GEAR]': '[GEAR]',
            '[NOTE]': '[NOTE]',
            '[PARTY]': '[PARTY]',
            '[APPLE]': '[APPLE]',
            '[HOOK]': '[HOOK]',
            '[BOOK]': '[BOOK]',
            '[SYNC]': '[SYNC]'
        }
    
    def remove_emoji_from_text(self, text: str) -> Tuple[str, int]:
        """从文本中移除emoji字符"""
        original_text = text
        
        # 使用替换映射
        for emoji, replacement in self.emoji_replacements.items():
            text = text.replace(emoji, replacement)
        
        # 移除其他未映射的emoji
        text = self.emoji_regex.sub('', text)
        
        # 计算替换次数
        changes = len(original_text) - len(text) + sum(
            original_text.count(emoji) * (len(replacement) - len(emoji))
            for emoji, replacement in self.emoji_replacements.items()
        )
        
        return text, changes
    
    def process_file(self, file_path: Path) -> Dict[str, any]:
        """处理单个文件"""
        try:
            # 读取文件
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 移除emoji
            new_content, changes = self.remove_emoji_from_text(content)
            
            if changes > 0:
                # 写回文件
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                
                return {
                    'status': 'modified',
                    'changes': changes,
                    'file': str(file_path)
                }
            else:
                return {
                    'status': 'no_changes',
                    'changes': 0,
                    'file': str(file_path)
                }
                
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'file': str(file_path)
            }
    
    def scan_directory(self, directory: Path, extensions: List[str] = None) -> List[Path]:
        """扫描目录中的文件"""
        if extensions is None:
            extensions = ['.py', '.md', '.json', '.txt']
        
        files = []
        for ext in extensions:
            files.extend(directory.rglob(f'*{ext}'))
        
        return files
    
    def process_directory(self, directory: str = '.') -> Dict[str, any]:
        """处理整个目录"""
        directory_path = Path(directory)
        
        # 扫描文件
        files = self.scan_directory(directory_path, ['.py'])
        
        results = {
            'total_files': len(files),
            'modified_files': 0,
            'total_changes': 0,
            'errors': [],
            'modified_list': []
        }
        
        print(f"扫描到 {len(files)} 个Python文件")
        
        for file_path in files:
            result = self.process_file(file_path)
            
            if result['status'] == 'modified':
                results['modified_files'] += 1
                results['total_changes'] += result['changes']
                results['modified_list'].append(result['file'])
                print(f"✓ 修改: {result['file']} ({result['changes']} 个字符)")
            
            elif result['status'] == 'error':
                results['errors'].append(result)
                print(f"✗ 错误: {result['file']} - {result['error']}")
        
        return results

def main():
    """主函数"""
    print("Emoji字符清理工具")
    print("=" * 50)
    
    remover = EmojiRemover()
    
    # 处理当前目录
    results = remover.process_directory('.')
    
    print("\n清理结果:")
    print(f"总文件数: {results['total_files']}")
    print(f"修改文件数: {results['modified_files']}")
    print(f"总字符变更: {results['total_changes']}")
    print(f"错误数: {len(results['errors'])}")
    
    if results['modified_list']:
        print("\n修改的文件:")
        for file in results['modified_list']:
            print(f"  - {file}")
    
    if results['errors']:
        print("\n错误文件:")
        for error in results['errors']:
            print(f"  - {error['file']}: {error['error']}")
    
    print("\nEmoji清理完成！")

if __name__ == "__main__":
    main()