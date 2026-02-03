#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分析下载的GitHub技能脚本

分析从GitHub下载的技能并生成报告。
"""

import json
import sys
from pathlib import Path
from collections import Counter

def analyze_skills():
    """分析下载的技能"""
    print("📊 分析下载的GitHub技能")
    print("="*60)
    
    # 读取技能信息
    skills_info_file = ".kiro/downloads/github_skills/skills_info.json"
    
    if not Path(skills_info_file).exists():
        print(f"❌ 技能信息文件不存在: {skills_info_file}")
        return
    
    with open(skills_info_file, 'r', encoding='utf-8') as f:
        skills_info = json.load(f)
    
    skills = skills_info.get('skills', [])
    
    print(f"📈 总体统计:")
    print(f"   下载时间: {skills_info.get('download_time', 'Unknown')}")
    print(f"   总技能数: {skills_info.get('total_skills', 0)}")
    print(f"   集成技能数: {skills_info.get('integrated_skills', 0)}")
    print(f"   集成失败数: {skills_info.get('failed_integrations', 0)}")
    
    # 按来源分析
    sources = Counter(skill.get('source', 'unknown') for skill in skills)
    print(f"\n📊 按来源分布:")
    for source, count in sources.items():
        print(f"   {source}: {count} 个技能")
    
    # 按分类分析
    categories = Counter(skill.get('category', 'general') for skill in skills)
    print(f"\n🏷️ 按分类分布:")
    for category, count in categories.most_common():
        print(f"   {category}: {count} 个技能")
    
    # 详细技能列表
    print(f"\n📋 详细技能列表:")
    for i, skill in enumerate(skills, 1):
        name = skill.get('name', 'Unknown')
        description = skill.get('description', 'No description')[:100]
        source = skill.get('source', 'unknown')
        category = skill.get('category', 'general')
        
        print(f"\n{i:2d}. {name} ({source})")
        print(f"     分类: {category}")
        print(f"     描述: {description}{'...' if len(skill.get('description', '')) > 100 else ''}")
        
        # 显示标签
        tags = skill.get('tags', [])
        if tags:
            print(f"     标签: {', '.join(tags[:5])}{'...' if len(tags) > 5 else ''}")
    
    # 技能价值分析
    print(f"\n💎 技能价值分析:")
    
    # 开发相关技能
    dev_skills = [s for s in skills if any(keyword in s.get('description', '').lower() 
                                          for keyword in ['code', 'programming', 'development', 'frontend', 'backend', 'web'])]
    print(f"   开发相关技能: {len(dev_skills)} 个")
    
    # 设计相关技能
    design_skills = [s for s in skills if any(keyword in s.get('description', '').lower() 
                                             for keyword in ['design', 'visual', 'art', 'ui', 'ux', 'canvas'])]
    print(f"   设计相关技能: {len(design_skills)} 个")
    
    # 文档相关技能
    doc_skills = [s for s in skills if any(keyword in s.get('description', '').lower() 
                                          for keyword in ['document', 'doc', 'writing', 'text', 'pdf', 'docx'])]
    print(f"   文档相关技能: {len(doc_skills)} 个")
    
    # 测试相关技能
    test_skills = [s for s in skills if any(keyword in s.get('description', '').lower() 
                                           for keyword in ['test', 'testing', 'webapp'])]
    print(f"   测试相关技能: {len(test_skills)} 个")
    
    # 推荐的技能应用
    print(f"\n🎯 推荐技能应用:")
    
    high_value_skills = [
        ('frontend-design', '前端开发和UI设计'),
        ('webapp-testing', 'Web应用测试'),
        ('docx', '文档处理和编辑'),
        ('mcp-builder', 'MCP服务器构建'),
        ('doc-coauthoring', '文档协作编写'),
        ('algorithmic-art', '算法艺术生成')
    ]
    
    for skill_name, description in high_value_skills:
        matching_skills = [s for s in skills if s.get('name') == skill_name]
        if matching_skills:
            print(f"   ✅ {skill_name}: {description}")
        else:
            print(f"   ❌ {skill_name}: 未找到 ({description})")
    
    print(f"\n🚀 建议下一步:")
    print(f"   1. 将这些技能模式添加到记忆系统中")
    print(f"   2. 为团队角色分配相关技能")
    print(f"   3. 创建基于技能的学习计划")
    print(f"   4. 测试高价值技能的实际应用")


if __name__ == "__main__":
    analyze_skills()