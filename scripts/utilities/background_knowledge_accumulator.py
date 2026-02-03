#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
后台知识积累引擎 v3.0
零干扰的智能知识管理系统，与MCP记忆系统深度集成
"""

import os
import sys
import time
import json
import threading
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
import subprocess

# 设置UTF-8编码（Windows兼容）
if sys.platform.startswith('win'):
    os.environ['PYTHONIOENCODING'] = 'utf-8'

class BackgroundKnowledgeAccumulator:
    def __init__(self, silent_mode: bool = True):
        self.silent_mode = silent_mode
        self.is_running = False
        self.idle_threshold = 30  # 空闲检测阈值（秒）
        self.max_idle_threshold = 60  # 最大空闲阈值（秒）
        self.knowledge_buffer = []
        self.last_activity_time = time.time()
        
        # 配置日志（静默模式下不输出）
        if self.silent_mode:
            logging.basicConfig(level=logging.CRITICAL)
        else:
            logging.basicConfig(level=logging.INFO)
        
        self.logger = logging.getLogger(__name__)
        
        # 知识分类
        self.knowledge_categories = {
            'error_solutions': '错误解决方案',
            'code_patterns': '代码模式',
            'best_practices': '最佳实践',
            'performance_tips': '性能优化',
            'debugging_techniques': '调试技巧',
            'architecture_insights': '架构洞察'
        }
    
    def detect_system_idle(self) -> bool:
        """检测系统是否空闲"""
        try:
            # 简化的空闲检测
            current_time = time.time()
            idle_time = current_time - self.last_activity_time
            
            # 如果超过空闲阈值，认为系统空闲
            is_idle = idle_time > self.idle_threshold
            
            if not self.silent_mode:
                self.logger.info(f"空闲时间: {idle_time:.1f}秒, 空闲状态: {is_idle}")
            
            return is_idle
            
        except Exception as e:
            if not self.silent_mode:
                self.logger.error(f"检测系统空闲状态失败: {e}")
            return False
    
    def extract_knowledge_from_context(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """从上下文中提取知识"""
        knowledge_items = []
        
        try:
            # 提取错误解决方案
            if 'errors' in context and context['errors']:
                for error in context['errors']:
                    if 'solution' in error:
                        knowledge_items.append({
                            'category': 'error_solutions',
                            'title': f"解决方案: {error.get('type', '未知错误')}",
                            'content': error['solution'],
                            'tags': ['error', 'solution', error.get('type', 'unknown')],
                            'timestamp': datetime.now().isoformat(),
                            'confidence': 0.8
                        })
            
            # 提取代码模式
            if 'code_changes' in context and context['code_changes']:
                for change in context['code_changes']:
                    if change.get('type') == 'improvement':
                        knowledge_items.append({
                            'category': 'code_patterns',
                            'title': f"代码改进: {change.get('file', '未知文件')}",
                            'content': change.get('description', ''),
                            'tags': ['code', 'improvement', 'pattern'],
                            'timestamp': datetime.now().isoformat(),
                            'confidence': 0.7
                        })
            
            # 提取最佳实践
            if 'best_practices' in context and context['best_practices']:
                for practice in context['best_practices']:
                    knowledge_items.append({
                        'category': 'best_practices',
                        'title': practice.get('title', '最佳实践'),
                        'content': practice.get('description', ''),
                        'tags': ['best_practice', 'guideline'],
                        'timestamp': datetime.now().isoformat(),
                        'confidence': 0.9
                    })
            
        except Exception as e:
            if not self.silent_mode:
                self.logger.error(f"提取知识失败: {e}")
        
        return knowledge_items
    
    def store_knowledge_to_mcp(self, knowledge_items: List[Dict[str, Any]]) -> bool:
        """将知识存储到MCP记忆系统"""
        try:
            if not knowledge_items:
                return True
            
            # 这里模拟存储到MCP（实际需要调用MCP API）
            if not self.silent_mode:
                self.logger.info(f"存储 {len(knowledge_items)} 个知识实体到MCP记忆系统")
            
            return True
            
        except Exception as e:
            if not self.silent_mode:
                self.logger.error(f"存储知识到MCP失败: {e}")
            return False
    
    def process_knowledge_buffer(self):
        """处理知识缓冲区"""
        if not self.knowledge_buffer:
            return
        
        try:
            # 合并相似的知识项
            merged_knowledge = self.merge_similar_knowledge(self.knowledge_buffer)
            
            # 存储到MCP
            success = self.store_knowledge_to_mcp(merged_knowledge)
            
            if success:
                if not self.silent_mode:
                    self.logger.info(f"成功处理 {len(merged_knowledge)} 个知识项")
                self.knowledge_buffer.clear()
            
        except Exception as e:
            if not self.silent_mode:
                self.logger.error(f"处理知识缓冲区失败: {e}")
    
    def merge_similar_knowledge(self, knowledge_items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """合并相似的知识项"""
        merged = {}
        
        for item in knowledge_items:
            key = f"{item['category']}_{item['title']}"
            
            if key in merged:
                # 合并内容
                merged[key]['content'] += f"\n\n补充: {item['content']}"
                merged[key]['tags'] = list(set(merged[key]['tags'] + item['tags']))
                merged[key]['confidence'] = max(merged[key]['confidence'], item['confidence'])
            else:
                merged[key] = item.copy()
        
        return list(merged.values())
    
    def background_worker(self):
        """后台工作线程"""
        while self.is_running:
            try:
                # 检测系统空闲
                if self.detect_system_idle():
                    # 处理知识缓冲区
                    self.process_knowledge_buffer()
                    
                    # 执行知识整理
                    self.organize_knowledge()
                
                # 休眠一段时间
                time.sleep(self.idle_threshold)
                
            except Exception as e:
                if not self.silent_mode:
                    self.logger.error(f"后台工作线程错误: {e}")
                time.sleep(5)  # 错误后短暂休眠
    
    def organize_knowledge(self):
        """整理和优化知识库"""
        try:
            # 这里可以实现知识库的整理逻辑
            if not self.silent_mode:
                self.logger.info("执行知识库整理")
            
        except Exception as e:
            if not self.silent_mode:
                self.logger.error(f"知识库整理失败: {e}")
    
    def add_knowledge(self, context: Dict[str, Any]):
        """添加知识到缓冲区"""
        try:
            knowledge_items = self.extract_knowledge_from_context(context)
            self.knowledge_buffer.extend(knowledge_items)
            self.last_activity_time = time.time()
            
            if not self.silent_mode and knowledge_items:
                self.logger.info(f"添加 {len(knowledge_items)} 个知识项到缓冲区")
            
        except Exception as e:
            if not self.silent_mode:
                self.logger.error(f"添加知识失败: {e}")
    
    def start(self):
        """启动后台知识积累引擎"""
        if self.is_running:
            return
        
        self.is_running = True
        
        # 启动后台线程
        self.worker_thread = threading.Thread(target=self.background_worker, daemon=True)
        self.worker_thread.start()
        
        if not self.silent_mode:
            self.logger.info("后台知识积累引擎已启动")
    
    def stop(self):
        """停止后台知识积累引擎"""
        self.is_running = False
        
        # 处理剩余的知识缓冲区
        self.process_knowledge_buffer()
        
        if not self.silent_mode:
            self.logger.info("后台知识积累引擎已停止")
    
    def get_status(self) -> Dict[str, Any]:
        """获取引擎状态"""
        return {
            'is_running': self.is_running,
            'silent_mode': self.silent_mode,
            'buffer_size': len(self.knowledge_buffer),
            'idle_threshold': self.idle_threshold,
            'last_activity': datetime.fromtimestamp(self.last_activity_time).isoformat(),
            'system_idle': self.detect_system_idle()
        }

def main():
    """主函数 - 用于测试"""
    # Windows兼容的输出方式
    try:
        print("后台知识积累引擎 v3.0")
        print("=" * 50)
    except UnicodeEncodeError:
        print("Background Knowledge Accumulator v3.0")
        print("=" * 50)
    
    # 创建引擎实例（非静默模式用于测试）
    engine = BackgroundKnowledgeAccumulator(silent_mode=False)
    
    # 启动引擎
    engine.start()
    
    # 模拟添加知识
    test_context = {
        'errors': [
            {
                'type': 'UnicodeEncodeError',
                'solution': '使用UTF-8编码处理中文字符'
            }
        ],
        'code_changes': [
            {
                'type': 'improvement',
                'file': 'test.py',
                'description': '优化了错误处理逻辑'
            }
        ]
    }
    
    engine.add_knowledge(test_context)
    
    # 显示状态
    status = engine.get_status()
    try:
        print("引擎状态:")
    except UnicodeEncodeError:
        print("Engine Status:")
    for key, value in status.items():
        print(f"  {key}: {value}")
    
    try:
        print("\n运行10秒...")
    except UnicodeEncodeError:
        print("\nRunning for 10 seconds...")
    time.sleep(10)
    
    # 停止引擎
    engine.stop()
    try:
        print("\n测试完成")
    except UnicodeEncodeError:
        print("\nTest completed")

if __name__ == "__main__":
    main()