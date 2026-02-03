"""
Kiro记忆系统检索引擎

实现基于哈希的O(1)查找和上下文感知的智能检索。
"""

import hashlib
import re
from typing import List, Dict, Any, Optional, Tuple
from collections import defaultdict
import math
import logging

from .models import MemoryPattern, QueryContext, MemoryType
from .storage import MemoryStorage


class HashRetrieval:
    """基于哈希的快速检索引擎"""
    
    def __init__(self, storage: MemoryStorage):
        self.storage = storage
        self.logger = logging.getLogger(__name__)
        
        # N-gram配置
        self.ngram_size = 3
        self.min_ngram_size = 2
        self.max_ngram_size = 5
    
    def _generate_ngrams(self, text: str, n: int = None) -> List[str]:
        """生成N-gram序列"""
        if n is None:
            n = self.ngram_size
        
        # 清理和标准化文本
        text = re.sub(r'\s+', ' ', text.lower().strip())
        
        if len(text) < n:
            return [text]
        
        ngrams = []
        for i in range(len(text) - n + 1):
            ngram = text[i:i+n]
            ngrams.append(ngram)
        
        return ngrams
    
    def _generate_hash_key(self, text: str) -> str:
        """生成文本的哈希键"""
        # 生成多个N-gram大小的哈希
        all_ngrams = []
        for n in range(self.min_ngram_size, self.max_ngram_size + 1):
            ngrams = self._generate_ngrams(text, n)
            all_ngrams.extend(ngrams)
        
        # 组合所有N-gram并生成哈希
        combined_text = ''.join(sorted(set(all_ngrams)))
        hash_obj = hashlib.sha256(combined_text.encode('utf-8'))
        return hash_obj.hexdigest()[:16]
    
    def retrieve(self, query: str, max_results: int = 10) -> List[MemoryPattern]:
        """基于哈希的快速检索"""
        try:
            # 生成查询的哈希键
            query_hash = self._generate_hash_key(query)
            
            # 从存储中获取匹配的模式
            patterns = self.storage.get_patterns_by_hash(query_hash)
            
            # 如果精确匹配没有结果，尝试模糊匹配
            if not patterns:
                patterns = self._fuzzy_retrieve(query, max_results)
            
            # 按相关性排序
            scored_patterns = []
            for pattern in patterns:
                score = self._calculate_relevance_score(query, pattern)
                scored_patterns.append((score, pattern))
            
            # 排序并返回top-k结果
            scored_patterns.sort(key=lambda x: x[0], reverse=True)
            return [pattern for _, pattern in scored_patterns[:max_results]]
            
        except Exception as e:
            self.logger.error(f"Failed to retrieve patterns for query '{query}': {e}")
            return []
    
    def _fuzzy_retrieve(self, query: str, max_results: int) -> List[MemoryPattern]:
        """模糊检索"""
        try:
            # 生成查询的N-gram
            query_ngrams = set()
            for n in range(self.min_ngram_size, self.max_ngram_size + 1):
                ngrams = self._generate_ngrams(query, n)
                query_ngrams.update(ngrams)
            
            # 同时生成查询词汇
            query_words = set(query.lower().split())
            
            # 搜索包含相似N-gram的模式
            candidate_patterns = self.storage.search_patterns(limit=max_results * 5)
            
            # 计算相似度
            fuzzy_matches = []
            for pattern in candidate_patterns:
                content_text = self._extract_searchable_text(pattern)
                
                # 计算N-gram相似度
                pattern_ngrams = set()
                for n in range(self.min_ngram_size, self.max_ngram_size + 1):
                    ngrams = self._generate_ngrams(content_text, n)
                    pattern_ngrams.update(ngrams)
                
                ngram_similarity = 0.0
                if len(query_ngrams | pattern_ngrams) > 0:
                    ngram_similarity = len(query_ngrams & pattern_ngrams) / len(query_ngrams | pattern_ngrams)
                
                # 计算词汇相似度
                pattern_words = set(content_text.lower().split())
                word_similarity = 0.0
                if len(query_words | pattern_words) > 0:
                    word_similarity = len(query_words & pattern_words) / len(query_words | pattern_words)
                
                # 组合相似度（词汇相似度权重更高）
                combined_similarity = word_similarity * 0.7 + ngram_similarity * 0.3
                
                # 降低相似度阈值，使搜索更宽松
                if combined_similarity > 0.05:  # 从0.1降低到0.05
                    fuzzy_matches.append((combined_similarity, pattern))
            
            # 按相似度排序
            fuzzy_matches.sort(key=lambda x: x[0], reverse=True)
            return [pattern for _, pattern in fuzzy_matches[:max_results]]
            
        except Exception as e:
            self.logger.error(f"Failed to perform fuzzy retrieval: {e}")
            return []
    
    def _extract_searchable_text(self, pattern: MemoryPattern) -> str:
        """从模式中提取可搜索的文本"""
        text_parts = []
        
        # 从内容中提取文本
        content = pattern.content
        if isinstance(content, dict):
            for key, value in content.items():
                if isinstance(value, str):
                    text_parts.append(value)
                elif isinstance(value, list):
                    text_parts.extend([str(item) for item in value if isinstance(item, str)])
        elif isinstance(content, str):
            text_parts.append(content)
        
        # 添加标签
        text_parts.extend(pattern.tags)
        
        return ' '.join(text_parts)
    
    def _calculate_relevance_score(self, query: str, pattern: MemoryPattern) -> float:
        """计算相关性评分"""
        score = 0.0
        
        # 基础文本相似度 (40%)
        content_text = self._extract_searchable_text(pattern)
        text_similarity = self._calculate_text_similarity(query, content_text)
        score += text_similarity * 0.4
        
        # 使用频率 (25%)
        usage_score = min(pattern.usage_count / 100.0, 1.0)
        score += usage_score * 0.25
        
        # 成功率 (20%)
        score += pattern.success_rate * 0.2
        
        # 置信度 (10%)
        score += pattern.confidence * 0.1
        
        # 新鲜度 (5%) - 最近使用的模式得分更高
        from datetime import datetime, timedelta
        days_since_used = (datetime.now() - pattern.last_used).days
        freshness_score = max(0, 1 - days_since_used / 30.0)  # 30天内的模式
        score += freshness_score * 0.05
        
        return score
    
    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """计算文本相似度"""
        # 使用简单的词汇重叠度
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = len(words1 & words2)
        union = len(words1 | words2)
        
        return intersection / union if union > 0 else 0.0


class ContextAwareRetrieval:
    """上下文感知检索引擎"""
    
    def __init__(self, storage: MemoryStorage, hash_retrieval: HashRetrieval):
        self.storage = storage
        self.hash_retrieval = hash_retrieval
        self.logger = logging.getLogger(__name__)
        
        # 上下文权重配置
        self.context_weights = {
            "file_type": 0.3,
            "current_task": 0.4,
            "recent_patterns": 0.2,
            "user_preferences": 0.1
        }
    
    def retrieve_with_context(self, context: QueryContext) -> List[MemoryPattern]:
        """基于上下文的智能检索"""
        try:
            # 1. 基础哈希检索
            base_results = self.hash_retrieval.retrieve(context.query, context.max_results * 2)
            
            # 2. 应用上下文过滤
            context_filtered = self._apply_context_filter(base_results, context)
            
            # 3. 重新排序
            reranked_results = self._rerank_with_context(context_filtered, context)
            
            # 4. 应用置信度过滤
            final_results = [
                pattern for pattern in reranked_results 
                if pattern.confidence >= context.min_confidence
            ]
            
            return final_results[:context.max_results]
            
        except Exception as e:
            self.logger.error(f"Failed to retrieve with context: {e}")
            return []
    
    def _apply_context_filter(self, patterns: List[MemoryPattern], context: QueryContext) -> List[MemoryPattern]:
        """应用上下文过滤"""
        filtered_patterns = []
        
        for pattern in patterns:
            # 文件类型过滤
            if context.file_type:
                pattern_file_type = pattern.metadata.get('file_type')
                if pattern_file_type and pattern_file_type != context.file_type:
                    # 如果文件类型不匹配，降低优先级但不完全排除
                    pattern.confidence *= 0.7
            
            # 任务类型过滤
            if context.current_task:
                if self._is_task_relevant(pattern, context.current_task):
                    pattern.confidence *= 1.2  # 提高相关任务的权重
            
            # 用户角色过滤
            if context.user_role:
                if self._is_role_relevant(pattern, context.user_role):
                    pattern.confidence *= 1.1
            
            filtered_patterns.append(pattern)
        
        return filtered_patterns
    
    def _is_task_relevant(self, pattern: MemoryPattern, task: str) -> bool:
        """判断模式是否与任务相关"""
        task_keywords = {
            "debugging": ["debug", "error", "fix", "bug", "issue"],
            "testing": ["test", "assert", "mock", "coverage"],
            "refactoring": ["refactor", "optimize", "clean", "improve"],
            "documentation": ["doc", "comment", "readme", "guide"]
        }
        
        task_lower = task.lower()
        pattern_text = self.hash_retrieval._extract_searchable_text(pattern).lower()
        
        for task_type, keywords in task_keywords.items():
            if task_type in task_lower:
                return any(keyword in pattern_text for keyword in keywords)
        
        return False
    
    def _is_role_relevant(self, pattern: MemoryPattern, role: str) -> bool:
        """判断模式是否与用户角色相关"""
        role_patterns = {
            "Security Engineer": [MemoryType.BEST_PRACTICE, MemoryType.CONFIGURATION],
            "DevOps Engineer": [MemoryType.CONFIGURATION, MemoryType.DEBUGGING_TIP],
            "Full-Stack Engineer": [MemoryType.CODE_PATTERN, MemoryType.ERROR_SOLUTION],
            "Test Engineer": [MemoryType.CODE_PATTERN, MemoryType.BEST_PRACTICE]
        }
        
        relevant_types = role_patterns.get(role, [])
        return pattern.type in relevant_types
    
    def _rerank_with_context(self, patterns: List[MemoryPattern], context: QueryContext) -> List[MemoryPattern]:
        """基于上下文重新排序"""
        scored_patterns = []
        
        for pattern in patterns:
            # 基础相关性评分
            base_score = self.hash_retrieval._calculate_relevance_score(context.query, pattern)
            
            # 上下文加权
            context_score = self._calculate_context_score(pattern, context)
            
            # 最终评分
            final_score = base_score * 0.7 + context_score * 0.3
            scored_patterns.append((final_score, pattern))
        
        # 排序
        scored_patterns.sort(key=lambda x: x[0], reverse=True)
        return [pattern for _, pattern in scored_patterns]
    
    def _calculate_context_score(self, pattern: MemoryPattern, context: QueryContext) -> float:
        """计算上下文评分"""
        score = 0.0
        
        # 文件类型匹配
        if context.file_type:
            pattern_file_type = pattern.metadata.get('file_type')
            if pattern_file_type == context.file_type:
                score += self.context_weights["file_type"]
        
        # 任务相关性
        if context.current_task and self._is_task_relevant(pattern, context.current_task):
            score += self.context_weights["current_task"]
        
        # 最近使用的模式
        if pattern.id in context.recent_patterns:
            score += self.context_weights["recent_patterns"]
        
        # 用户偏好
        if context.preferences:
            preference_score = self._calculate_preference_score(pattern, context.preferences)
            score += preference_score * self.context_weights["user_preferences"]
        
        return score
    
    def _calculate_preference_score(self, pattern: MemoryPattern, preferences: Dict[str, Any]) -> float:
        """计算用户偏好评分"""
        score = 0.0
        
        # 偏好的模式类型
        preferred_types = preferences.get('pattern_types', [])
        if pattern.type.value in preferred_types:
            score += 0.5
        
        # 偏好的标签
        preferred_tags = preferences.get('tags', [])
        if any(tag in pattern.tags for tag in preferred_tags):
            score += 0.3
        
        # 偏好的来源
        preferred_sources = preferences.get('sources', [])
        if pattern.source in preferred_sources:
            score += 0.2
        
        return min(score, 1.0)


class SmartRecommendationEngine:
    """智能推荐引擎"""
    
    def __init__(self, storage: MemoryStorage, context_retrieval: ContextAwareRetrieval):
        self.storage = storage
        self.context_retrieval = context_retrieval
        self.logger = logging.getLogger(__name__)
    
    def get_recommendations(self, context: QueryContext, recommendation_type: str = "general") -> List[MemoryPattern]:
        """获取智能推荐"""
        try:
            if recommendation_type == "similar":
                return self._get_similar_patterns(context)
            elif recommendation_type == "trending":
                return self._get_trending_patterns(context)
            elif recommendation_type == "personalized":
                return self._get_personalized_recommendations(context)
            else:
                return self._get_general_recommendations(context)
                
        except Exception as e:
            self.logger.error(f"Failed to get recommendations: {e}")
            return []
    
    def _get_similar_patterns(self, context: QueryContext) -> List[MemoryPattern]:
        """获取相似模式推荐"""
        # 基于当前查询找到相似的模式
        base_results = self.context_retrieval.retrieve_with_context(context)
        
        if not base_results:
            return []
        
        # 找到与最佳匹配相似的其他模式
        best_match = base_results[0]
        similar_patterns = []
        
        # 基于标签相似性
        for tag in best_match.tags:
            tag_patterns = self.storage.search_patterns(tags=[tag], limit=5)
            similar_patterns.extend(tag_patterns)
        
        # 去重并排序
        unique_patterns = {p.id: p for p in similar_patterns if p.id != best_match.id}
        return list(unique_patterns.values())[:5]
    
    def _get_trending_patterns(self, context: QueryContext) -> List[MemoryPattern]:
        """获取趋势模式推荐"""
        # 获取最近使用频率高的模式
        return self.storage.search_patterns(limit=10)
    
    def _get_personalized_recommendations(self, context: QueryContext) -> List[MemoryPattern]:
        """获取个性化推荐"""
        # 基于用户历史使用模式推荐
        if not context.recent_patterns:
            return self._get_general_recommendations(context)
        
        # 分析用户最近使用的模式类型和标签
        recent_types = []
        recent_tags = []
        
        for pattern_id in context.recent_patterns[-10:]:  # 最近10个
            pattern = self.storage.get_pattern(pattern_id)
            if pattern:
                recent_types.append(pattern.type)
                recent_tags.extend(pattern.tags)
        
        # 找到相似类型和标签的模式
        recommendations = []
        for pattern_type in set(recent_types):
            type_patterns = self.storage.search_patterns(pattern_type=pattern_type, limit=3)
            recommendations.extend(type_patterns)
        
        return recommendations[:10]
    
    def _get_general_recommendations(self, context: QueryContext) -> List[MemoryPattern]:
        """获取通用推荐"""
        # 基于文件类型和用户角色的通用推荐
        filters = {}
        if context.file_type:
            # 根据文件类型推荐相关模式
            pass
        
        return self.storage.search_patterns(limit=10)