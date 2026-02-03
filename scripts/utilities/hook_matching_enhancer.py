#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Hook匹配增强脚本
"""

import re
import sys
from pathlib import Path

# 添加src目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from kiro_memory import KiroMemorySystem

class HookMatchingEnhancer:
    """Hook匹配增强器"""
    
    def __init__(self):
        self.memory_system = KiroMemorySystem('.kiro/memory', enable_learning=True)
        
        # 上下文关键词提取规则
        self.context_patterns = {
            'error_related': [
                r'错误', r'error', r'bug', r'问题', r'异常', r'失败', r'fail',
                r'不能', r'无法', r'报错', r'exception'
            ],
            'optimization_related': [
                r'优化', r'improve', r'enhance', r'better', r'faster',
                r'提升', r'改进', r'增强', r'性能'
            ],
            'development_related': [
                r'开发', r'develop', r'code', r'编程', r'programming',
                r'实现', r'implement', r'功能', r'feature'
            ],
            'testing_related': [
                r'测试', r'test', r'验证', r'check', r'validate',
                r'检查', r'确认', r'verify'
            ]
        }
        
        # 中文到英文翻译映射
        self.chinese_to_english = {
            '错误': 'error', '问题': 'issue', '修复': 'fix', '解决': 'solve',
            '优化': 'optimization', '改进': 'improve', '提升': 'enhance',
            '开发': 'development', '编程': 'programming', '代码': 'code',
            '测试': 'test', '验证': 'verify', '检查': 'check',
            '系统': 'system', '平台': 'platform', '框架': 'framework',
            '团队': 'team', '协作': 'collaboration', '管理': 'management',
            '技能': 'skill', '能力': 'ability', '学习': 'learning',
            '集成': 'integration', '整合': 'integrate',
            '配置': 'configuration', '设置': 'setting',
            '性能': 'performance', '效率': 'efficiency',
            '质量': 'quality', '标准': 'standard',
            '流程': 'process', '方法': 'method',
            '工具': 'tool', '脚本': 'script',
            '数据': 'data', '信息': 'information',
            '网络': 'network', '服务': 'service',
            '安全': 'security', '权限': 'permission',
            '监控': 'monitoring', '日志': 'log',
            '部署': 'deployment', '发布': 'release',
            '版本': 'version', '更新': 'update',
            '文档': 'documentation', '说明': 'instruction',
            '接口': 'interface', 'API': 'api',
            '数据库': 'database', '存储': 'storage',
            '算法': 'algorithm', '模型': 'model',
            '架构': 'architecture', '设计': 'design',
            '模块': 'module', '组件': 'component',
            '功能': 'feature', '特性': 'feature',
            '实现': 'implementation', '执行': 'execution',
            '分析': 'analysis', '评估': 'evaluation',
            '报告': 'report', '统计': 'statistics',
            '指标': 'metrics', '基准': 'benchmark'
        }
        
        # 同义词和相关词映射
        self.semantic_mappings = {
            'error': ['错误', 'bug', '问题', '异常', '故障', 'issue'],
            'optimization': ['优化', '改进', '提升', '增强', 'improve', 'enhance'],
            'development': ['开发', '编程', '实现', '构建', 'coding', 'programming'],
            'testing': ['测试', '验证', '检查', '校验', 'validation', 'verification'],
            'system': ['系统', '平台', '框架', 'platform', 'framework'],
            'integration': ['集成', '整合', '融合', '结合', 'combine'],
            'team': ['团队', '小组', '协作', '合作', 'collaboration'],
            'skill': ['技能', '能力', '技术', 'ability', 'capability'],
            'performance': ['性能', '效率', '速度', 'efficiency', 'speed'],
            'quality': ['质量', '标准', '规范', 'standard', 'specification']
        }
    
    def extract_context_keywords(self, prompt: str):
        """从提示中提取上下文关键词"""
        keywords = []
        prompt_lower = prompt.lower()
        
        # 1. 基于模式匹配提取关键词
        for category, patterns in self.context_patterns.items():
            for pattern in patterns:
                if re.search(pattern, prompt_lower):
                    keywords.append(category.replace('_related', ''))
                    break
        
        # 2. 提取具体的技术词汇
        tech_words = re.findall(r'[a-zA-Z]{3,}|[\u4e00-\u9fff]{2,}', prompt)
        keywords.extend([word.lower() for word in tech_words if len(word) > 2])
        
        return list(set(keywords))
    
    def enhanced_hook_search(self, prompt: str, max_results: int = 5):
        """增强的Hook搜索"""
        print(f"🎯 Hook增强搜索: '{prompt[:50]}...'")
        
        # 1. 提取上下文关键词
        keywords = self.extract_context_keywords(prompt)
        print(f"   提取关键词: {keywords}")
        
        # 2. 翻译中文关键词
        translated_keywords = self.translate_chinese_keywords(keywords)
        all_keywords = keywords + translated_keywords
        print(f"   翻译后关键词: {all_keywords}")
        
        # 3. 多轮搜索策略
        all_results = []
        seen_ids = set()
        
        # 第一轮：直接搜索原始提示
        direct_results = self.memory_system.search(prompt, max_results=max_results)
        for pattern in direct_results:
            if pattern.id not in seen_ids:
                all_results.append(pattern)
                seen_ids.add(pattern.id)
        
        # 第二轮：翻译后的提示搜索
        translated_prompt = self.translate_prompt(prompt)
        if translated_prompt != prompt:
            translated_results = self.memory_system.search(translated_prompt, max_results=3)
            for pattern in translated_results:
                if pattern.id not in seen_ids and len(all_results) < max_results:
                    all_results.append(pattern)
                    seen_ids.add(pattern.id)
        
        # 第三轮：基于关键词搜索
        if len(all_results) < max_results:
            for keyword in all_keywords[:5]:  # 限制关键词数量
                keyword_results = self.memory_system.search(keyword, max_results=2)
                for pattern in keyword_results:
                    if pattern.id not in seen_ids and len(all_results) < max_results:
                        all_results.append(pattern)
                        seen_ids.add(pattern.id)
        
        # 第四轮：语义扩展搜索
        if len(all_results) < max_results:
            semantic_queries = self.get_semantic_queries(all_keywords)
            for query in semantic_queries[:3]:  # 限制语义查询数量
                semantic_results = self.memory_system.search(query, max_results=2)
                for pattern in semantic_results:
                    if pattern.id not in seen_ids and len(all_results) < max_results:
                        all_results.append(pattern)
                        seen_ids.add(pattern.id)
        
        print(f"   找到 {len(all_results)} 个相关模式")
        return all_results
    
    def translate_chinese_keywords(self, keywords):
        """翻译中文关键词为英文"""
        translated = []
        for keyword in keywords:
            if keyword in self.chinese_to_english:
                translated.append(self.chinese_to_english[keyword])
        return translated
    
    def translate_prompt(self, prompt: str):
        """翻译提示中的中文词汇"""
        translated_prompt = prompt
        for chinese, english in self.chinese_to_english.items():
            if chinese in translated_prompt:
                translated_prompt = translated_prompt.replace(chinese, english)
        return translated_prompt
    
    def get_semantic_queries(self, keywords):
        """获取语义相关的查询词"""
        semantic_queries = []
        
        for keyword in keywords:
            if keyword in self.semantic_mappings:
                semantic_queries.extend(self.semantic_mappings[keyword][:2])
        
        return list(set(semantic_queries))
    
    def generate_enhanced_prompt(self, original_prompt: str, relevant_patterns):
        """生成增强的提示"""
        if not relevant_patterns:
            return original_prompt
        
        enhancement = "\n\n💡 相关知识模式:\n"
        for i, pattern in enumerate(relevant_patterns[:3], 1):
            description = pattern.content.get('description', '无描述')[:100]
            enhancement += f"{i}. [{pattern.type.value}] {description}...\n"
        
        return original_prompt + enhancement

if __name__ == "__main__":
    enhancer = HookMatchingEnhancer()
    
    # 测试Hook匹配增强
    test_prompts = [
        "请帮我修复Python中的错误",
        "如何优化系统性能",
        "团队技能管理最佳实践",
        "GitHub集成问题解决"
    ]
    
    for prompt in test_prompts:
        results = enhancer.enhanced_hook_search(prompt)
        enhanced_prompt = enhancer.generate_enhanced_prompt(prompt, results)
        print(f"原始提示: {prompt}")
        print(f"增强效果: 找到{len(results)}个相关模式")
        print("-" * 50)
