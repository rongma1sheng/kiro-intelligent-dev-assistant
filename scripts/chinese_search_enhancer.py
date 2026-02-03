#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
中文搜索增强脚本
"""

import re
import sys
from pathlib import Path

# 添加src目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from kiro_memory import KiroMemorySystem

class ChineseSearchEnhancer:
    """中文搜索增强器"""
    
    def __init__(self):
        self.memory_system = KiroMemorySystem('.kiro/memory', enable_learning=True)
        
        # 中文关键词映射表 - 中文到英文翻译
        self.chinese_to_english_mapping = {
            'GitHub': 'github',
            '技能': 'skill',
            '团队': 'team', 
            '系统': 'system',
            '优化': 'optimization',
            '错误': 'error',
            '测试': 'test',
            '集成': 'integration',
            '配置': 'config',
            '监控': 'monitoring',
            '代码': 'code',
            '编程': 'programming',
            '开发': 'development',
            '项目': 'project',
            '管理': 'management',
            '性能': 'performance',
            '质量': 'quality',
            '安全': 'security',
            '数据': 'data',
            '网络': 'network',
            '服务器': 'server',
            '数据库': 'database',
            '算法': 'algorithm',
            '架构': 'architecture',
            '框架': 'framework',
            '平台': 'platform',
            '工具': 'tool',
            '文档': 'documentation',
            '部署': 'deployment',
            '维护': 'maintenance',
            '修复': 'fix',
            '问题': 'issue',
            '解决': 'solution',
            '方案': 'solution',
            '实现': 'implementation',
            '功能': 'feature',
            '模块': 'module',
            '组件': 'component',
            '接口': 'interface',
            '协议': 'protocol',
            '标准': 'standard',
            '规范': 'specification',
            '流程': 'process',
            '方法': 'method',
            '策略': 'strategy',
            '模式': 'pattern',
            '设计': 'design',
            '分析': 'analysis',
            '评估': 'evaluation',
            '监控': 'monitoring',
            '日志': 'log',
            '报告': 'report',
            '统计': 'statistics',
            '指标': 'metrics',
            '基准': 'benchmark',
            '版本': 'version',
            '发布': 'release',
            '更新': 'update',
            '升级': 'upgrade',
            '迁移': 'migration',
            '备份': 'backup',
            '恢复': 'recovery',
            '同步': 'sync',
            '异步': 'async',
            '并发': 'concurrent',
            '并行': 'parallel',
            '分布式': 'distributed',
            '集群': 'cluster',
            '负载': 'load',
            '缓存': 'cache',
            '存储': 'storage',
            '内存': 'memory',
            '磁盘': 'disk',
            'CPU': 'cpu',
            'GPU': 'gpu',
            '带宽': 'bandwidth',
            '延迟': 'latency',
            '吞吐量': 'throughput',
            '可用性': 'availability',
            '可靠性': 'reliability',
            '稳定性': 'stability',
            '扩展性': 'scalability',
            '兼容性': 'compatibility',
            '可维护性': 'maintainability'
        }
        
        # 扩展的中文关键词映射表
        self.chinese_keyword_mapping = {
            'GitHub': ['github', 'Git', '代码仓库', '版本控制'],
            '技能': ['skill', 'skills', '能力', '技术'],
            '团队': ['team', '小组', '协作', '合作'],
            '系统': ['system', '平台', '框架'],
            '优化': ['optimization', 'optimize', '改进', '提升'],
            '错误': ['error', 'bug', '问题', '异常'],
            '测试': ['test', 'testing', '验证', '检查'],
            '集成': ['integration', '整合', '融合'],
            '配置': ['config', 'configuration', '设置'],
            '监控': ['monitoring', 'monitor', '观察', '跟踪']
        }
        
        # 同义词映射
        self.synonyms = {
            '问题': ['错误', 'bug', '异常', 'issue'],
            '优化': ['改进', '提升', '增强', 'improve'],
            '系统': ['平台', '框架', 'system', 'platform'],
            '技能': ['能力', '技术', 'skill', 'ability'],
            '团队': ['小组', '协作', 'team', 'group']
        }
    
    def enhanced_search(self, query: str, max_results: int = 10):
        """增强的中文搜索"""
        print(f"🔍 增强搜索: '{query}'")
        
        # 1. 直接搜索
        direct_results = self.memory_system.search(query, max_results=max_results)
        
        # 2. 中文到英文翻译搜索
        translated_queries = self.translate_chinese_to_english(query)
        
        all_results = list(direct_results)
        seen_ids = {pattern.id for pattern in direct_results}
        
        # 3. 使用翻译后的查询词搜索
        for translated_query in translated_queries:
            if translated_query != query:  # 避免重复搜索
                translated_results = self.memory_system.search(translated_query, max_results=5)
                for pattern in translated_results:
                    if pattern.id not in seen_ids and len(all_results) < max_results:
                        all_results.append(pattern)
                        seen_ids.add(pattern.id)
        
        # 4. 如果结果仍然不足，尝试扩展搜索
        if len(all_results) < 3:
            expanded_queries = self.expand_query(query)
            
            for expanded_query in expanded_queries:
                expanded_results = self.memory_system.search(expanded_query, max_results=3)
                for pattern in expanded_results:
                    if pattern.id not in seen_ids and len(all_results) < max_results:
                        all_results.append(pattern)
                        seen_ids.add(pattern.id)
        
        print(f"   找到 {len(all_results)} 个结果 (直接:{len(direct_results)}, 翻译:{len(translated_queries)})")
        return all_results
    
    def translate_chinese_to_english(self, query: str):
        """将中文查询翻译为英文"""
        translated_queries = []
        
        # 1. 直接映射翻译
        for chinese_word, english_word in self.chinese_to_english_mapping.items():
            if chinese_word in query:
                # 替换中文词为英文词
                translated_query = query.replace(chinese_word, english_word)
                translated_queries.append(translated_query)
                # 也添加纯英文词
                translated_queries.append(english_word)
        
        # 2. 提取中文词并翻译
        import re
        chinese_words = re.findall(r'[\u4e00-\u9fff]+', query)
        for chinese_word in chinese_words:
            if chinese_word in self.chinese_to_english_mapping:
                translated_queries.append(self.chinese_to_english_mapping[chinese_word])
        
        # 3. 移除重复项
        return list(set(translated_queries))
    
    def expand_query(self, query: str):
        """扩展查询词"""
        expanded_queries = []
        
        # 1. 检查中文关键词映射
        for chinese_word, english_words in self.chinese_keyword_mapping.items():
            if chinese_word in query:
                for english_word in english_words:
                    expanded_queries.append(english_word)
        
        # 2. 检查同义词
        for word, synonyms in self.synonyms.items():
            if word in query:
                expanded_queries.extend(synonyms)
        
        # 3. 拆分查询词
        words = re.findall(r'[\w\u4e00-\u9fff]+', query)
        for word in words:
            if len(word) > 1:
                expanded_queries.append(word)
        
        return list(set(expanded_queries))

if __name__ == "__main__":
    enhancer = ChineseSearchEnhancer()
    
    # 测试中文搜索
    test_queries = ["GitHub技能", "系统优化", "错误解决", "团队协作"]
    
    for query in test_queries:
        results = enhancer.enhanced_search(query, max_results=5)
        print(f"查询 '{query}' 找到 {len(results)} 个结果")
        for i, pattern in enumerate(results, 1):
            print(f"  {i}. [{pattern.type.value}] {pattern.content.get('description', '无描述')[:50]}...")
        print()
