"""
Kiro记忆系统学习引擎

实现使用模式学习、错误模式识别和智能优化功能。
"""

from typing import List, Dict, Any, Optional, Tuple
from collections import defaultdict, Counter
from datetime import datetime, timedelta
import logging
import json
import math

from .models import MemoryPattern, LearningEvent, MemoryType, QueryContext
from .storage import MemoryStorage


class UsageLearning:
    """使用模式学习引擎"""
    
    def __init__(self, storage: MemoryStorage):
        self.storage = storage
        self.logger = logging.getLogger(__name__)
        
        # 学习参数
        self.learning_rate = 0.1
        self.decay_factor = 0.95
        self.min_usage_threshold = 3
        self.success_threshold = 0.7
    
    def learn_from_interaction(self, pattern_id: str, context: Dict[str, Any], success: bool):
        """从用户交互中学习"""
        try:
            # 记录学习事件
            event = LearningEvent(
                pattern_id=pattern_id,
                event_type="usage_feedback",
                context=context,
                metadata={"success": success}
            )
            self.storage.record_learning_event(event)
            
            # 更新模式统计
            self.storage.update_pattern_usage(pattern_id, success)
            
            # 分析使用模式
            self._analyze_usage_pattern(pattern_id, context, success)
            
            # 如果成功，强化相关模式
            if success:
                self._reinforce_related_patterns(pattern_id, context)
            else:
                self._analyze_failure_pattern(pattern_id, context)
                
        except Exception as e:
            self.logger.error(f"Failed to learn from interaction: {e}")
    
    def _analyze_usage_pattern(self, pattern_id: str, context: Dict[str, Any], success: bool):
        """分析使用模式"""
        pattern = self.storage.get_pattern(pattern_id)
        if not pattern:
            return
        
        # 更新模式的上下文信息
        if 'usage_contexts' not in pattern.metadata:
            pattern.metadata['usage_contexts'] = []
        
        usage_context = {
            'file_type': context.get('file_type'),
            'task_type': context.get('current_task'),
            'user_role': context.get('user_role'),
            'success': success,
            'timestamp': datetime.now().isoformat()
        }
        
        pattern.metadata['usage_contexts'].append(usage_context)
        
        # 保持最近100个使用记录
        if len(pattern.metadata['usage_contexts']) > 100:
            pattern.metadata['usage_contexts'] = pattern.metadata['usage_contexts'][-100:]
        
        # 重新存储模式
        self.storage.store_pattern(pattern)
    
    def _reinforce_related_patterns(self, pattern_id: str, context: Dict[str, Any]):
        """强化相关模式"""
        pattern = self.storage.get_pattern(pattern_id)
        if not pattern:
            return
        
        # 找到相关模式
        related_patterns = self._find_related_patterns(pattern, context)
        
        # 轻微提升相关模式的权重
        for related_pattern in related_patterns:
            related_pattern.confidence = min(1.0, related_pattern.confidence * 1.05)
            self.storage.store_pattern(related_pattern)
    
    def _find_related_patterns(self, pattern: MemoryPattern, context: Dict[str, Any]) -> List[MemoryPattern]:
        """找到相关模式"""
        related_patterns = []
        
        # 基于标签相似性
        if pattern.tags:
            for tag in pattern.tags:
                tag_patterns = self.storage.search_patterns(tags=[tag], limit=5)
                related_patterns.extend([p for p in tag_patterns if p.id != pattern.id])
        
        # 基于类型相似性
        type_patterns = self.storage.search_patterns(pattern_type=pattern.type, limit=5)
        related_patterns.extend([p for p in type_patterns if p.id != pattern.id])
        
        # 去重
        unique_patterns = {p.id: p for p in related_patterns}
        return list(unique_patterns.values())
    
    def _analyze_failure_pattern(self, pattern_id: str, context: Dict[str, Any]):
        """分析失败模式"""
        pattern = self.storage.get_pattern(pattern_id)
        if not pattern:
            return
        
        # 记录失败上下文
        if 'failure_contexts' not in pattern.metadata:
            pattern.metadata['failure_contexts'] = []
        
        failure_context = {
            'file_type': context.get('file_type'),
            'task_type': context.get('current_task'),
            'user_role': context.get('user_role'),
            'timestamp': datetime.now().isoformat()
        }
        
        pattern.metadata['failure_contexts'].append(failure_context)
        
        # 如果失败率过高，降低置信度
        if pattern.success_rate < self.success_threshold and pattern.usage_count >= self.min_usage_threshold:
            pattern.confidence *= 0.9
            self.storage.store_pattern(pattern)
    
    def discover_new_patterns(self, recent_interactions: List[Dict[str, Any]]) -> List[MemoryPattern]:
        """发现新的使用模式"""
        try:
            # 分析最近的交互数据
            pattern_candidates = self._extract_pattern_candidates(recent_interactions)
            
            # 验证模式的有效性
            validated_patterns = []
            for candidate in pattern_candidates:
                if self._validate_pattern_candidate(candidate):
                    new_pattern = self._create_pattern_from_candidate(candidate)
                    validated_patterns.append(new_pattern)
            
            return validated_patterns
            
        except Exception as e:
            self.logger.error(f"Failed to discover new patterns: {e}")
            return []
    
    def _extract_pattern_candidates(self, interactions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """从交互中提取模式候选"""
        candidates = []
        
        # 按上下文分组交互
        context_groups = defaultdict(list)
        for interaction in interactions:
            context_key = (
                interaction.get('file_type'),
                interaction.get('current_task'),
                interaction.get('user_role')
            )
            context_groups[context_key].append(interaction)
        
        # 找到频繁出现的模式
        for context_key, group_interactions in context_groups.items():
            if len(group_interactions) >= 3:  # 至少出现3次
                # 分析成功的交互
                successful_interactions = [i for i in group_interactions if i.get('success', False)]
                if len(successful_interactions) >= 2:
                    candidate = {
                        'context': {
                            'file_type': context_key[0],
                            'current_task': context_key[1],
                            'user_role': context_key[2]
                        },
                        'interactions': successful_interactions,
                        'frequency': len(successful_interactions),
                        'success_rate': len(successful_interactions) / len(group_interactions)
                    }
                    candidates.append(candidate)
        
        return candidates
    
    def _validate_pattern_candidate(self, candidate: Dict[str, Any]) -> bool:
        """验证模式候选的有效性"""
        # 检查频率阈值
        if candidate['frequency'] < 3:
            return False
        
        # 检查成功率阈值
        if candidate['success_rate'] < 0.6:
            return False
        
        # 检查是否已存在类似模式
        existing_patterns = self.storage.search_patterns(limit=100)
        for pattern in existing_patterns:
            if self._is_similar_pattern(pattern, candidate):
                return False
        
        return True
    
    def _is_similar_pattern(self, pattern: MemoryPattern, candidate: Dict[str, Any]) -> bool:
        """检查是否为相似模式"""
        # 简单的相似性检查
        pattern_context = pattern.metadata.get('context', {})
        candidate_context = candidate['context']
        
        similarity_score = 0
        total_fields = 0
        
        for key in ['file_type', 'current_task', 'user_role']:
            if key in pattern_context and key in candidate_context:
                total_fields += 1
                if pattern_context[key] == candidate_context[key]:
                    similarity_score += 1
        
        return (similarity_score / total_fields) > 0.7 if total_fields > 0 else False
    
    def _create_pattern_from_candidate(self, candidate: Dict[str, Any]) -> MemoryPattern:
        """从候选创建新模式"""
        import uuid
        
        pattern_id = str(uuid.uuid4())
        
        # 从交互中提取内容
        content = {
            'type': 'discovered_pattern',
            'context': candidate['context'],
            'frequency': candidate['frequency'],
            'success_rate': candidate['success_rate'],
            'interactions': candidate['interactions'][:5]  # 保留前5个示例
        }
        
        pattern = MemoryPattern(
            id=pattern_id,
            type=MemoryType.BEST_PRACTICE,
            content=content,
            hash_key="",  # 将在存储时生成
            metadata={
                'discovered': True,
                'discovery_date': datetime.now().isoformat(),
                'context': candidate['context']
            },
            confidence=min(0.8, candidate['success_rate']),
            tags=['discovered', 'pattern'],
            source='learning_engine'
        )
        
        return pattern


class ErrorPatternDetector:
    """错误模式检测器"""
    
    def __init__(self, storage: MemoryStorage):
        self.storage = storage
        self.logger = logging.getLogger(__name__)
        
        # 检测参数
        self.error_threshold = 0.3  # 错误率阈值
        self.min_occurrences = 3    # 最小出现次数
        self.time_window_days = 7   # 时间窗口
    
    def detect_error_patterns(self, recent_failures: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """检测错误模式"""
        try:
            # 按错误特征分组
            error_groups = self._group_errors_by_signature(recent_failures)
            
            # 识别频繁错误模式
            error_patterns = []
            for signature, errors in error_groups.items():
                if len(errors) >= self.min_occurrences:
                    pattern = self._analyze_error_pattern(signature, errors)
                    if pattern:
                        error_patterns.append(pattern)
            
            return error_patterns
            
        except Exception as e:
            self.logger.error(f"Failed to detect error patterns: {e}")
            return []
    
    def _group_errors_by_signature(self, failures: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """按错误签名分组"""
        error_groups = defaultdict(list)
        
        for failure in failures:
            signature = self._extract_error_signature(failure)
            error_groups[signature].append(failure)
        
        return error_groups
    
    def _extract_error_signature(self, failure: Dict[str, Any]) -> str:
        """提取错误签名"""
        # 提取关键错误特征
        features = []
        
        # 错误类型
        error_type = failure.get('error_type', 'unknown')
        features.append(f"type:{error_type}")
        
        # 文件类型
        file_type = failure.get('file_type', 'unknown')
        features.append(f"file:{file_type}")
        
        # 任务类型
        task_type = failure.get('current_task', 'unknown')
        features.append(f"task:{task_type}")
        
        # 错误消息关键词
        error_message = failure.get('error_message', '')
        keywords = self._extract_error_keywords(error_message)
        features.extend([f"keyword:{kw}" for kw in keywords])
        
        return '|'.join(sorted(features))
    
    def _extract_error_keywords(self, error_message: str) -> List[str]:
        """提取错误消息关键词"""
        import re
        
        # 常见错误关键词
        error_keywords = [
            'timeout', 'connection', 'permission', 'not found', 'syntax error',
            'import error', 'type error', 'value error', 'key error',
            'attribute error', 'index error', 'unicode', 'encoding'
        ]
        
        message_lower = error_message.lower()
        found_keywords = []
        
        for keyword in error_keywords:
            if keyword in message_lower:
                found_keywords.append(keyword)
        
        # 提取异常类名
        exception_pattern = r'(\w+Error|\w+Exception)'
        exceptions = re.findall(exception_pattern, error_message)
        found_keywords.extend([ex.lower() for ex in exceptions])
        
        return list(set(found_keywords))[:5]  # 最多5个关键词
    
    def _analyze_error_pattern(self, signature: str, errors: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """分析错误模式"""
        if len(errors) < self.min_occurrences:
            return None
        
        # 计算错误频率
        time_span = self._calculate_time_span(errors)
        frequency = len(errors) / max(time_span.days, 1)
        
        # 分析错误上下文
        contexts = [error.get('context', {}) for error in errors]
        common_context = self._find_common_context(contexts)
        
        # 查找可能的解决方案
        potential_solutions = self._find_potential_solutions(signature, errors)
        
        pattern = {
            'signature': signature,
            'frequency': frequency,
            'occurrences': len(errors),
            'time_span_days': time_span.days,
            'common_context': common_context,
            'potential_solutions': potential_solutions,
            'severity': self._calculate_severity(errors),
            'examples': errors[:3]  # 保留前3个示例
        }
        
        return pattern
    
    def _calculate_time_span(self, errors: List[Dict[str, Any]]) -> timedelta:
        """计算错误时间跨度"""
        timestamps = []
        for error in errors:
            timestamp_str = error.get('timestamp')
            if timestamp_str:
                try:
                    timestamp = datetime.fromisoformat(timestamp_str)
                    timestamps.append(timestamp)
                except:
                    pass
        
        if len(timestamps) < 2:
            return timedelta(days=1)
        
        return max(timestamps) - min(timestamps)
    
    def _find_common_context(self, contexts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """找到共同上下文"""
        if not contexts:
            return {}
        
        common = {}
        
        # 找到所有上下文中的共同键值对
        first_context = contexts[0]
        for key, value in first_context.items():
            if all(ctx.get(key) == value for ctx in contexts):
                common[key] = value
        
        return common
    
    def _find_potential_solutions(self, signature: str, errors: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """查找潜在解决方案"""
        solutions = []
        
        # 从现有成功模式中查找解决方案
        successful_patterns = self.storage.search_patterns(
            pattern_type=MemoryType.ERROR_SOLUTION,
            min_confidence=0.7,
            limit=10
        )
        
        for pattern in successful_patterns:
            # 检查是否与当前错误模式相关
            if self._is_solution_relevant(pattern, signature, errors):
                solution = {
                    'pattern_id': pattern.id,
                    'content': pattern.content,
                    'confidence': pattern.confidence,
                    'success_rate': pattern.success_rate
                }
                solutions.append(solution)
        
        return solutions[:3]  # 最多3个解决方案
    
    def _is_solution_relevant(self, pattern: MemoryPattern, signature: str, errors: List[Dict[str, Any]]) -> bool:
        """检查解决方案是否相关"""
        # 简单的关键词匹配
        pattern_text = str(pattern.content).lower()
        signature_keywords = signature.lower().split('|')
        
        # 检查是否有共同关键词
        for keyword in signature_keywords:
            if keyword.split(':')[1] in pattern_text:  # 移除前缀
                return True
        
        return False
    
    def _calculate_severity(self, errors: List[Dict[str, Any]]) -> str:
        """计算错误严重程度"""
        # 基于频率和影响范围计算严重程度
        frequency = len(errors)
        
        if frequency >= 10:
            return "critical"
        elif frequency >= 5:
            return "high"
        elif frequency >= 3:
            return "medium"
        else:
            return "low"
    
    def create_error_solution_pattern(self, error_pattern: Dict[str, Any], solution: Dict[str, Any]) -> MemoryPattern:
        """创建错误解决方案模式"""
        import uuid
        
        pattern_id = str(uuid.uuid4())
        
        content = {
            'error_signature': error_pattern['signature'],
            'error_description': error_pattern.get('description', ''),
            'solution_steps': solution.get('steps', []),
            'solution_code': solution.get('code', ''),
            'prevention_tips': solution.get('prevention', []),
            'related_errors': error_pattern.get('examples', [])
        }
        
        # 从错误签名提取标签
        tags = ['error_solution']
        signature_parts = error_pattern['signature'].split('|')
        for part in signature_parts:
            if ':' in part:
                tag_type, tag_value = part.split(':', 1)
                tags.append(f"{tag_type}_{tag_value}")
        
        pattern = MemoryPattern(
            id=pattern_id,
            type=MemoryType.ERROR_SOLUTION,
            content=content,
            hash_key="",  # 将在存储时生成
            metadata={
                'error_pattern': error_pattern,
                'created_from_detection': True,
                'severity': error_pattern.get('severity', 'medium')
            },
            confidence=0.8,
            tags=tags[:10],  # 限制标签数量
            source='error_detector'
        )
        
        return pattern


class AdaptiveLearning:
    """自适应学习引擎"""
    
    def __init__(self, storage: MemoryStorage, usage_learning: UsageLearning, error_detector: ErrorPatternDetector):
        self.storage = storage
        self.usage_learning = usage_learning
        self.error_detector = error_detector
        self.logger = logging.getLogger(__name__)
        
        # 学习配置
        self.adaptation_interval = timedelta(hours=24)  # 每24小时适应一次
        self.last_adaptation = datetime.now() - self.adaptation_interval
    
    def adapt_system(self):
        """自适应系统优化"""
        try:
            current_time = datetime.now()
            if current_time - self.last_adaptation < self.adaptation_interval:
                return  # 还未到适应时间
            
            self.logger.info("Starting adaptive learning process...")
            
            # 1. 分析系统性能
            performance_metrics = self._analyze_system_performance()
            
            # 2. 优化模式权重
            self._optimize_pattern_weights(performance_metrics)
            
            # 3. 清理低效模式
            self._cleanup_ineffective_patterns()
            
            # 4. 发现新模式
            self._discover_and_create_patterns()
            
            # 5. 更新学习参数
            self._update_learning_parameters(performance_metrics)
            
            self.last_adaptation = current_time
            self.logger.info("Adaptive learning process completed")
            
        except Exception as e:
            self.logger.error(f"Failed to adapt system: {e}")
    
    def _analyze_system_performance(self) -> Dict[str, Any]:
        """分析系统性能"""
        # 获取存储统计
        storage_stats = self.storage.get_storage_stats()
        
        # 分析模式使用情况
        all_patterns = self.storage.search_patterns(limit=1000)
        
        usage_stats = {
            'total_patterns': len(all_patterns),
            'active_patterns': len([p for p in all_patterns if p.usage_count > 0]),
            'high_success_patterns': len([p for p in all_patterns if p.success_rate > 0.8]),
            'low_success_patterns': len([p for p in all_patterns if p.success_rate < 0.3 and p.usage_count > 3]),
            'unused_patterns': len([p for p in all_patterns if p.usage_count == 0]),
            'average_success_rate': sum(p.success_rate for p in all_patterns) / len(all_patterns) if all_patterns else 0
        }
        
        return {
            'storage_stats': storage_stats,
            'usage_stats': usage_stats,
            'timestamp': datetime.now().isoformat()
        }
    
    def _optimize_pattern_weights(self, performance_metrics: Dict[str, Any]):
        """优化模式权重"""
        all_patterns = self.storage.search_patterns(limit=1000)
        
        for pattern in all_patterns:
            old_confidence = pattern.confidence
            
            # 基于成功率调整权重
            if pattern.usage_count >= 3:
                if pattern.success_rate > 0.8:
                    pattern.confidence = min(1.0, pattern.confidence * 1.1)
                elif pattern.success_rate < 0.3:
                    pattern.confidence = max(0.1, pattern.confidence * 0.8)
            
            # 基于使用频率调整权重
            if pattern.usage_count > 10:
                pattern.confidence = min(1.0, pattern.confidence * 1.05)
            
            # 如果权重有变化，更新存储
            if abs(old_confidence - pattern.confidence) > 0.01:
                self.storage.store_pattern(pattern)
    
    def _cleanup_ineffective_patterns(self):
        """清理低效模式"""
        # 清理30天未使用的模式
        cleaned_count = self.storage.cleanup_old_patterns(days=30)
        
        # 清理成功率极低的模式
        all_patterns = self.storage.search_patterns(limit=1000)
        low_performance_patterns = [
            p for p in all_patterns 
            if p.success_rate < 0.2 and p.usage_count >= 5
        ]
        
        for pattern in low_performance_patterns:
            # 降低置信度而不是删除
            pattern.confidence = max(0.1, pattern.confidence * 0.5)
            self.storage.store_pattern(pattern)
        
        self.logger.info(f"Cleaned up {cleaned_count} old patterns and downgraded {len(low_performance_patterns)} low-performance patterns")
    
    def _discover_and_create_patterns(self):
        """发现并创建新模式"""
        # 这里可以实现更复杂的模式发现逻辑
        # 目前只是一个占位符
        pass
    
    def _update_learning_parameters(self, performance_metrics: Dict[str, Any]):
        """更新学习参数"""
        usage_stats = performance_metrics['usage_stats']
        
        # 根据系统性能调整学习率
        if usage_stats['average_success_rate'] > 0.8:
            self.usage_learning.learning_rate = min(0.2, self.usage_learning.learning_rate * 1.1)
        elif usage_stats['average_success_rate'] < 0.6:
            self.usage_learning.learning_rate = max(0.05, self.usage_learning.learning_rate * 0.9)
        
        self.logger.info(f"Updated learning rate to {self.usage_learning.learning_rate}")