"""
Kiro记忆系统核心模块

统一的记忆系统接口，整合存储、检索和学习功能。
"""

import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

from .models import (
    MemoryPattern, ProjectContext, TeamKnowledge, QueryContext, 
    MemoryType, Priority, MemoryStats, LearningEvent
)
from .storage import MemoryStorage
from .retrieval import HashRetrieval, ContextAwareRetrieval, SmartRecommendationEngine
from .learning import UsageLearning, ErrorPatternDetector, AdaptiveLearning


class KiroMemorySystem:
    """Kiro记忆系统主类"""
    
    def __init__(self, storage_path: str = ".kiro/memory", enable_learning: bool = True):
        """
        初始化记忆系统
        
        Args:
            storage_path: 存储路径
            enable_learning: 是否启用学习功能
        """
        # 初始化存储层
        self.storage = MemoryStorage(storage_path)
        
        # 初始化检索引擎
        self.hash_retrieval = HashRetrieval(self.storage)
        self.context_retrieval = ContextAwareRetrieval(self.storage, self.hash_retrieval)
        self.recommendation_engine = SmartRecommendationEngine(self.storage, self.context_retrieval)
        
        # 初始化学习引擎
        self.enable_learning = enable_learning
        if enable_learning:
            self.usage_learning = UsageLearning(self.storage)
            self.error_detector = ErrorPatternDetector(self.storage)
            self.adaptive_learning = AdaptiveLearning(
                self.storage, self.usage_learning, self.error_detector
            )
        
        # 设置日志
        self.logger = logging.getLogger(__name__)
        self.logger.info("Kiro Memory System initialized")
    
    # ==================== 模式管理 ====================
    
    def store_pattern(self, 
                     content: Dict[str, Any],
                     pattern_type: MemoryType,
                     tags: List[str] = None,
                     metadata: Dict[str, Any] = None,
                     priority: Priority = Priority.MEDIUM,
                     source: str = "user") -> str:
        """
        存储记忆模式
        
        Args:
            content: 模式内容
            pattern_type: 模式类型
            tags: 标签列表
            metadata: 元数据
            priority: 优先级
            source: 来源
            
        Returns:
            模式ID
        """
        try:
            pattern_id = str(uuid.uuid4())
            
            pattern = MemoryPattern(
                id=pattern_id,
                type=pattern_type,
                content=content,
                hash_key="",  # 将在存储时生成
                metadata=metadata or {},
                tags=tags or [],
                priority=priority,
                source=source
            )
            
            stored_id = self.storage.store_pattern(pattern)
            self.logger.info(f"Stored pattern {stored_id} of type {pattern_type.value}")
            
            return stored_id
            
        except Exception as e:
            self.logger.error(f"Failed to store pattern: {e}")
            raise
    
    def get_pattern(self, pattern_id: str) -> Optional[MemoryPattern]:
        """获取记忆模式"""
        return self.storage.get_pattern(pattern_id)
    
    def update_pattern(self, pattern: MemoryPattern) -> bool:
        """更新记忆模式"""
        try:
            self.storage.store_pattern(pattern)
            return True
        except Exception as e:
            self.logger.error(f"Failed to update pattern {pattern.id}: {e}")
            return False
    
    def delete_pattern(self, pattern_id: str) -> bool:
        """删除记忆模式"""
        # 注意：当前实现不支持物理删除，只是标记为删除
        try:
            pattern = self.storage.get_pattern(pattern_id)
            if pattern:
                pattern.metadata['deleted'] = True
                pattern.confidence = 0.0
                self.storage.store_pattern(pattern)
                return True
            return False
        except Exception as e:
            self.logger.error(f"Failed to delete pattern {pattern_id}: {e}")
            return False
    
    # ==================== 检索功能 ====================
    
    def search(self, 
               query: str,
               file_type: str = None,
               current_task: str = None,
               user_role: str = None,
               max_results: int = 10,
               min_confidence: float = 0.5) -> List[MemoryPattern]:
        """
        智能搜索记忆模式
        
        Args:
            query: 搜索查询
            file_type: 文件类型
            current_task: 当前任务
            user_role: 用户角色
            max_results: 最大结果数
            min_confidence: 最小置信度
            
        Returns:
            匹配的模式列表
        """
        try:
            context = QueryContext(
                query=query,
                file_type=file_type,
                current_task=current_task,
                user_role=user_role,
                max_results=max_results,
                min_confidence=min_confidence
            )
            
            results = self.context_retrieval.retrieve_with_context(context)
            
            # 记录搜索事件（如果启用学习）
            if self.enable_learning:
                for result in results:
                    event = LearningEvent(
                        pattern_id=result.id,
                        event_type="search_result",
                        context=context.to_dict()
                    )
                    self.storage.record_learning_event(event)
            
            return results
            
        except Exception as e:
            self.logger.error(f"Failed to search patterns: {e}")
            return []
    
    def get_recommendations(self, 
                          context: QueryContext,
                          recommendation_type: str = "general") -> List[MemoryPattern]:
        """获取智能推荐"""
        try:
            return self.recommendation_engine.get_recommendations(context, recommendation_type)
        except Exception as e:
            self.logger.error(f"Failed to get recommendations: {e}")
            return []
    
    # ==================== 学习功能 ====================
    
    def record_usage(self, 
                    pattern_id: str,
                    context: Dict[str, Any],
                    success: bool = True):
        """记录模式使用情况"""
        if not self.enable_learning:
            return
        
        try:
            self.usage_learning.learn_from_interaction(pattern_id, context, success)
            self.logger.debug(f"Recorded usage for pattern {pattern_id}: success={success}")
        except Exception as e:
            self.logger.error(f"Failed to record usage: {e}")
    
    def report_error(self, 
                    error_info: Dict[str, Any],
                    context: Dict[str, Any] = None):
        """报告错误信息"""
        if not self.enable_learning:
            return
        
        try:
            # 记录错误事件
            event = LearningEvent(
                pattern_id="error_event",
                event_type="error_report",
                context={
                    "error_info": error_info,
                    "context": context or {}
                }
            )
            self.storage.record_learning_event(event)
            
            self.logger.info("Error reported to learning system")
        except Exception as e:
            self.logger.error(f"Failed to report error: {e}")
    
    def detect_error_patterns(self) -> List[Dict[str, Any]]:
        """检测错误模式"""
        if not self.enable_learning:
            return []
        
        try:
            # 获取最近的错误事件
            # 这里需要实现从学习事件中提取错误的逻辑
            recent_failures = []  # 占位符
            
            return self.error_detector.detect_error_patterns(recent_failures)
        except Exception as e:
            self.logger.error(f"Failed to detect error patterns: {e}")
            return []
    
    # ==================== 项目上下文管理 ====================
    
    def update_project_context(self, 
                              file_path: str,
                              file_type: str,
                              metadata: Dict[str, Any] = None):
        """更新项目上下文"""
        try:
            context = ProjectContext(
                file_path=file_path,
                file_type=file_type,
                **metadata or {}
            )
            
            self.storage.store_project_context(context)
            self.logger.debug(f"Updated project context for {file_path}")
        except Exception as e:
            self.logger.error(f"Failed to update project context: {e}")
    
    def get_project_context(self, file_path: str) -> Optional[ProjectContext]:
        """获取项目上下文"""
        return self.storage.get_project_context(file_path)
    
    # ==================== 系统管理 ====================
    
    def get_stats(self) -> MemoryStats:
        """获取系统统计信息"""
        try:
            storage_stats = self.storage.get_storage_stats()
            
            stats = MemoryStats(
                total_patterns=storage_stats.get('total_patterns', 0),
                patterns_by_type=storage_stats.get('patterns_by_type', {}),
                storage_size_mb=storage_stats.get('storage_size_mb', 0.0),
                most_used_patterns=storage_stats.get('most_used_patterns', [])
            )
            
            return stats
        except Exception as e:
            self.logger.error(f"Failed to get stats: {e}")
            return MemoryStats()
    
    def optimize_system(self):
        """优化系统性能"""
        if not self.enable_learning:
            self.logger.info("Learning disabled, skipping system optimization")
            return
        
        try:
            self.adaptive_learning.adapt_system()
            self.logger.info("System optimization completed")
        except Exception as e:
            self.logger.error(f"Failed to optimize system: {e}")
    
    def cleanup(self, days: int = 30) -> int:
        """清理旧数据"""
        try:
            cleaned_count = self.storage.cleanup_old_patterns(days)
            self.logger.info(f"Cleaned up {cleaned_count} old patterns")
            return cleaned_count
        except Exception as e:
            self.logger.error(f"Failed to cleanup: {e}")
            return 0
    
    # ==================== 便捷方法 ====================
    
    def store_code_pattern(self, 
                          code: str,
                          description: str,
                          file_type: str,
                          tags: List[str] = None) -> str:
        """存储代码模式"""
        content = {
            "code": code,
            "description": description,
            "file_type": file_type
        }
        
        return self.store_pattern(
            content=content,
            pattern_type=MemoryType.CODE_PATTERN,
            tags=(tags or []) + [file_type, "code"],
            metadata={"file_type": file_type}
        )
    
    def store_error_solution(self,
                           error_description: str,
                           solution: str,
                           error_type: str = None,
                           tags: List[str] = None) -> str:
        """存储错误解决方案"""
        content = {
            "error_description": error_description,
            "solution": solution,
            "error_type": error_type or "general"
        }
        
        return self.store_pattern(
            content=content,
            pattern_type=MemoryType.ERROR_SOLUTION,
            tags=(tags or []) + ["error", "solution"],
            metadata={"error_type": error_type}
        )
    
    def store_best_practice(self,
                           title: str,
                           description: str,
                           category: str,
                           tags: List[str] = None) -> str:
        """存储最佳实践"""
        content = {
            "title": title,
            "description": description,
            "category": category
        }
        
        return self.store_pattern(
            content=content,
            pattern_type=MemoryType.BEST_PRACTICE,
            tags=(tags or []) + [category, "best_practice"],
            metadata={"category": category}
        )
    
    def find_similar_code(self, code_snippet: str, file_type: str = None) -> List[MemoryPattern]:
        """查找相似代码"""
        return self.search(
            query=code_snippet,
            file_type=file_type,
            current_task="code_search",
            max_results=5
        )
    
    def get_error_solutions(self, error_message: str) -> List[MemoryPattern]:
        """获取错误解决方案"""
        return self.search(
            query=error_message,
            current_task="error_solving",
            max_results=3
        )
    
    def get_context_help(self, 
                        file_path: str,
                        current_line: str = None) -> Dict[str, Any]:
        """获取上下文帮助"""
        try:
            # 获取项目上下文
            project_context = self.get_project_context(file_path)
            
            # 基于文件类型搜索相关模式
            file_type = file_path.split('.')[-1] if '.' in file_path else 'unknown'
            
            query = current_line or f"help for {file_type} file"
            relevant_patterns = self.search(
                query=query,
                file_type=file_type,
                current_task="context_help",
                max_results=5
            )
            
            # 获取推荐
            context = QueryContext(
                query=query,
                file_path=file_path,
                file_type=file_type,
                current_task="context_help"
            )
            recommendations = self.get_recommendations(context, "similar")
            
            return {
                "project_context": project_context.to_dict() if project_context else None,
                "relevant_patterns": [p.to_dict() for p in relevant_patterns],
                "recommendations": [p.to_dict() for p in recommendations],
                "file_type": file_type
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get context help: {e}")
            return {}
    
    # ==================== Hook系统集成 ====================
    
    def enhance_hook_prompt(self, 
                           hook_name: str,
                           original_prompt: str,
                           context: Dict[str, Any]) -> str:
        """增强Hook提示"""
        try:
            # 搜索相关的记忆模式
            relevant_patterns = self.search(
                query=original_prompt,
                file_type=context.get('file_type'),
                current_task=context.get('current_task'),
                user_role=context.get('user_role'),
                max_results=3
            )
            
            if not relevant_patterns:
                return original_prompt
            
            # 构建增强提示
            enhanced_parts = [original_prompt]
            enhanced_parts.append("\n🧠 相关记忆模式:")
            
            for i, pattern in enumerate(relevant_patterns, 1):
                pattern_info = f"\n{i}. {pattern.type.value}: {pattern.content.get('description', '无描述')}"
                if pattern.tags:
                    pattern_info += f" (标签: {', '.join(pattern.tags[:3])})"
                enhanced_parts.append(pattern_info)
            
            enhanced_prompt = ''.join(enhanced_parts)
            
            # 记录使用情况
            for pattern in relevant_patterns:
                self.record_usage(pattern.id, context, success=True)
            
            return enhanced_prompt
            
        except Exception as e:
            self.logger.error(f"Failed to enhance hook prompt: {e}")
            return original_prompt