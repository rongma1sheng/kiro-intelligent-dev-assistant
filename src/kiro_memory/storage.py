"""
Kiro记忆系统存储层

实现基于SQLite + JSON的混合存储架构，提供高效的数据持久化和检索。
"""

import sqlite3
import json
import hashlib
import os
import gzip
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import logging

from .models import MemoryPattern, ProjectContext, TeamKnowledge, MemoryType, LearningEvent


class MemoryStorage:
    """记忆存储管理器"""
    
    def __init__(self, storage_path: str = ".kiro/memory"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # 数据库文件路径
        self.db_path = self.storage_path / "memory.db"
        self.patterns_dir = self.storage_path / "patterns"
        self.context_dir = self.storage_path / "context"
        self.knowledge_dir = self.storage_path / "knowledge"
        
        # 创建目录
        self.patterns_dir.mkdir(exist_ok=True)
        self.context_dir.mkdir(exist_ok=True)
        self.knowledge_dir.mkdir(exist_ok=True)
        
        # 初始化数据库
        self._init_database()
        
        # 设置日志
        self.logger = logging.getLogger(__name__)
    
    def _init_database(self):
        """初始化SQLite数据库"""
        with sqlite3.connect(self.db_path) as conn:
            # 创建记忆模式索引表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS memory_patterns (
                    id TEXT PRIMARY KEY,
                    type TEXT NOT NULL,
                    hash_key TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    last_used TEXT NOT NULL,
                    usage_count INTEGER DEFAULT 0,
                    success_rate REAL DEFAULT 0.0,
                    priority INTEGER DEFAULT 2,
                    source TEXT DEFAULT 'user',
                    confidence REAL DEFAULT 1.0,
                    file_path TEXT,
                    tags TEXT  -- JSON array
                )
            """)
            
            # 创建哈希索引表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS hash_index (
                    hash_key TEXT PRIMARY KEY,
                    pattern_ids TEXT  -- JSON array of pattern IDs
                )
            """)
            
            # 创建项目上下文表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS project_context (
                    file_path TEXT PRIMARY KEY,
                    file_type TEXT,
                    last_modified TEXT,
                    complexity_score REAL DEFAULT 0.0,
                    coverage_percentage REAL DEFAULT 0.0,
                    change_frequency REAL DEFAULT 0.0,
                    error_count INTEGER DEFAULT 0,
                    success_count INTEGER DEFAULT 0
                )
            """)
            
            # 创建学习事件表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS learning_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    pattern_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    context TEXT  -- JSON
                )
            """)
            
            # 创建索引
            conn.execute("CREATE INDEX IF NOT EXISTS idx_hash_key ON memory_patterns(hash_key)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_type ON memory_patterns(type)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_last_used ON memory_patterns(last_used)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_usage_count ON memory_patterns(usage_count)")
            
            conn.commit()
    
    def _generate_hash_key(self, content: Dict[str, Any]) -> str:
        """生成内容的哈希键"""
        # 将内容转换为标准化字符串
        content_str = json.dumps(content, sort_keys=True, ensure_ascii=False)
        
        # 生成SHA256哈希
        hash_obj = hashlib.sha256(content_str.encode('utf-8'))
        return hash_obj.hexdigest()[:16]  # 使用前16位作为哈希键
    
    def store_pattern(self, pattern: MemoryPattern) -> str:
        """存储记忆模式"""
        try:
            # 生成哈希键（如果没有）
            if not pattern.hash_key:
                pattern.hash_key = self._generate_hash_key(pattern.content)
            
            # 存储到数据库索引
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO memory_patterns 
                    (id, type, hash_key, created_at, last_used, usage_count, 
                     success_rate, priority, source, confidence, file_path, tags)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    pattern.id,
                    pattern.type.value,
                    pattern.hash_key,
                    pattern.created_at.isoformat(),
                    pattern.last_used.isoformat(),
                    pattern.usage_count,
                    pattern.success_rate,
                    pattern.priority.value,
                    pattern.source,
                    pattern.confidence,
                    pattern.metadata.get('file_path'),
                    json.dumps(pattern.tags)
                ))
                
                # 更新哈希索引
                self._update_hash_index(conn, pattern.hash_key, pattern.id)
                
                conn.commit()
            
            # 存储内容到JSON文件
            pattern_file = self.patterns_dir / f"{pattern.id}.json"
            with open(pattern_file, 'w', encoding='utf-8') as f:
                json.dump(pattern.to_dict(), f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"Stored pattern {pattern.id} with hash {pattern.hash_key}")
            return pattern.id
            
        except Exception as e:
            self.logger.error(f"Failed to store pattern {pattern.id}: {e}")
            raise
    
    def _update_hash_index(self, conn: sqlite3.Connection, hash_key: str, pattern_id: str):
        """更新哈希索引"""
        # 获取现有的模式ID列表
        cursor = conn.execute("SELECT pattern_ids FROM hash_index WHERE hash_key = ?", (hash_key,))
        row = cursor.fetchone()
        
        if row:
            # 更新现有索引
            existing_ids = json.loads(row[0])
            if pattern_id not in existing_ids:
                existing_ids.append(pattern_id)
                conn.execute(
                    "UPDATE hash_index SET pattern_ids = ? WHERE hash_key = ?",
                    (json.dumps(existing_ids), hash_key)
                )
        else:
            # 创建新索引
            conn.execute(
                "INSERT INTO hash_index (hash_key, pattern_ids) VALUES (?, ?)",
                (hash_key, json.dumps([pattern_id]))
            )
    
    def get_pattern(self, pattern_id: str) -> Optional[MemoryPattern]:
        """获取记忆模式"""
        try:
            pattern_file = self.patterns_dir / f"{pattern_id}.json"
            if not pattern_file.exists():
                return None
            
            with open(pattern_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            return MemoryPattern.from_dict(data)
            
        except Exception as e:
            self.logger.error(f"Failed to get pattern {pattern_id}: {e}")
            return None
    
    def get_patterns_by_hash(self, hash_key: str) -> List[MemoryPattern]:
        """根据哈希键获取模式列表"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("SELECT pattern_ids FROM hash_index WHERE hash_key = ?", (hash_key,))
                row = cursor.fetchone()
                
                if not row:
                    return []
                
                pattern_ids = json.loads(row[0])
                patterns = []
                
                for pattern_id in pattern_ids:
                    pattern = self.get_pattern(pattern_id)
                    if pattern:
                        patterns.append(pattern)
                
                return patterns
                
        except Exception as e:
            self.logger.error(f"Failed to get patterns by hash {hash_key}: {e}")
            return []
    
    def search_patterns(self, 
                       query: str = None,
                       pattern_type: MemoryType = None,
                       tags: List[str] = None,
                       min_confidence: float = 0.0,
                       limit: int = 10) -> List[MemoryPattern]:
        """搜索记忆模式"""
        try:
            conditions = []
            params = []
            
            if pattern_type:
                conditions.append("type = ?")
                params.append(pattern_type.value)
            
            if min_confidence > 0:
                conditions.append("confidence >= ?")
                params.append(min_confidence)
            
            # 构建SQL查询
            sql = "SELECT id FROM memory_patterns"
            if conditions:
                sql += " WHERE " + " AND ".join(conditions)
            
            sql += " ORDER BY usage_count DESC, success_rate DESC LIMIT ?"
            params.append(limit)
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(sql, params)
                pattern_ids = [row[0] for row in cursor.fetchall()]
            
            # 获取完整的模式对象
            patterns = []
            for pattern_id in pattern_ids:
                pattern = self.get_pattern(pattern_id)
                if pattern:
                    # 如果有标签过滤
                    if tags and not any(tag in pattern.tags for tag in tags):
                        continue
                    patterns.append(pattern)
            
            return patterns
            
        except Exception as e:
            self.logger.error(f"Failed to search patterns: {e}")
            return []
    
    def update_pattern_usage(self, pattern_id: str, success: bool = True):
        """更新模式使用统计"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # 获取当前统计
                cursor = conn.execute(
                    "SELECT usage_count, success_rate FROM memory_patterns WHERE id = ?",
                    (pattern_id,)
                )
                row = cursor.fetchone()
                
                if not row:
                    return
                
                usage_count, success_rate = row
                new_usage_count = usage_count + 1
                
                # 计算新的成功率
                if success:
                    new_success_rate = (success_rate * usage_count + 1) / new_usage_count
                else:
                    new_success_rate = (success_rate * usage_count) / new_usage_count
                
                # 更新数据库
                conn.execute("""
                    UPDATE memory_patterns 
                    SET usage_count = ?, success_rate = ?, last_used = ?
                    WHERE id = ?
                """, (new_usage_count, new_success_rate, datetime.now().isoformat(), pattern_id))
                
                conn.commit()
                
        except Exception as e:
            self.logger.error(f"Failed to update pattern usage {pattern_id}: {e}")
    
    def store_project_context(self, context: ProjectContext):
        """存储项目上下文"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO project_context
                    (file_path, file_type, last_modified, complexity_score,
                     coverage_percentage, change_frequency, error_count, success_count)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    context.file_path,
                    context.file_type,
                    context.last_modified.isoformat(),
                    context.complexity_score,
                    context.coverage_percentage,
                    context.change_frequency,
                    context.error_count,
                    context.success_count
                ))
                conn.commit()
            
            # 存储详细信息到JSON
            context_file = self.context_dir / f"{hashlib.md5(context.file_path.encode()).hexdigest()}.json"
            with open(context_file, 'w', encoding='utf-8') as f:
                json.dump(context.to_dict(), f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            self.logger.error(f"Failed to store project context for {context.file_path}: {e}")
    
    def get_project_context(self, file_path: str) -> Optional[ProjectContext]:
        """获取项目上下文"""
        try:
            context_file = self.context_dir / f"{hashlib.md5(file_path.encode()).hexdigest()}.json"
            if not context_file.exists():
                return None
            
            with open(context_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            return ProjectContext(
                file_path=data["file_path"],
                file_type=data["file_type"],
                dependencies=data.get("dependencies", []),
                imports=data.get("imports", []),
                functions=data.get("functions", []),
                classes=data.get("classes", []),
                test_files=data.get("test_files", []),
                complexity_score=data.get("complexity_score", 0.0),
                coverage_percentage=data.get("coverage_percentage", 0.0),
                last_modified=datetime.fromisoformat(data["last_modified"]),
                change_frequency=data.get("change_frequency", 0.0),
                error_count=data.get("error_count", 0),
                success_count=data.get("success_count", 0),
                related_files=data.get("related_files", [])
            )
            
        except Exception as e:
            self.logger.error(f"Failed to get project context for {file_path}: {e}")
            return None
    
    def record_learning_event(self, event: LearningEvent):
        """记录学习事件"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO learning_events (pattern_id, event_type, timestamp, context)
                    VALUES (?, ?, ?, ?)
                """, (
                    event.pattern_id,
                    event.event_type,
                    event.timestamp.isoformat(),
                    json.dumps(event.context)
                ))
                conn.commit()
                
        except Exception as e:
            self.logger.error(f"Failed to record learning event: {e}")
    
    def get_storage_stats(self) -> Dict[str, Any]:
        """获取存储统计信息"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # 总模式数
                cursor = conn.execute("SELECT COUNT(*) FROM memory_patterns")
                total_patterns = cursor.fetchone()[0]
                
                # 按类型统计
                cursor = conn.execute("SELECT type, COUNT(*) FROM memory_patterns GROUP BY type")
                patterns_by_type = dict(cursor.fetchall())
                
                # 最常用的模式
                cursor = conn.execute("""
                    SELECT id FROM memory_patterns 
                    ORDER BY usage_count DESC LIMIT 10
                """)
                most_used = [row[0] for row in cursor.fetchall()]
            
            # 计算存储大小
            storage_size = sum(
                f.stat().st_size for f in self.storage_path.rglob('*') if f.is_file()
            ) / (1024 * 1024)  # MB
            
            return {
                "total_patterns": total_patterns,
                "patterns_by_type": patterns_by_type,
                "storage_size_mb": round(storage_size, 2),
                "most_used_patterns": most_used
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get storage stats: {e}")
            return {}
    
    def cleanup_old_patterns(self, days: int = 30):
        """清理旧的未使用模式"""
        try:
            cutoff_date = datetime.now().replace(day=datetime.now().day - days)
            
            with sqlite3.connect(self.db_path) as conn:
                # 获取要删除的模式ID
                cursor = conn.execute("""
                    SELECT id FROM memory_patterns 
                    WHERE last_used < ? AND usage_count = 0
                """, (cutoff_date.isoformat(),))
                
                pattern_ids = [row[0] for row in cursor.fetchall()]
                
                # 删除数据库记录
                conn.execute("""
                    DELETE FROM memory_patterns 
                    WHERE last_used < ? AND usage_count = 0
                """, (cutoff_date.isoformat(),))
                
                conn.commit()
            
            # 删除文件
            for pattern_id in pattern_ids:
                pattern_file = self.patterns_dir / f"{pattern_id}.json"
                if pattern_file.exists():
                    pattern_file.unlink()
            
            self.logger.info(f"Cleaned up {len(pattern_ids)} old patterns")
            return len(pattern_ids)
            
        except Exception as e:
            self.logger.error(f"Failed to cleanup old patterns: {e}")
            return 0