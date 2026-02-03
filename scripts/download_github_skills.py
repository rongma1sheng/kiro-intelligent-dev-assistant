#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GitHub技能下载和集成脚本

从GitHub仓库下载技能并集成到团队技能元学习系统中。
"""

import sys
import os
import json
import requests
import tempfile
import zipfile
from pathlib import Path
from datetime import datetime

# 添加src目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from team_skills_meta_learning import TeamSkillsMetaLearningSystem


class GitHubSkillsDownloader:
    """GitHub技能下载器"""
    
    def __init__(self):
        self.skills_system = TeamSkillsMetaLearningSystem(
            storage_path=".kiro/team_skills",
            enable_learning=True
        )
        self.downloaded_skills = []
        
    def download_repository(self, repo_url: str, target_dir: str):
        """下载GitHub仓库"""
        print(f"📥 下载仓库: {repo_url}")
        
        # 转换GitHub URL为下载链接
        if "github.com" in repo_url:
            # 从 https://github.com/user/repo 转换为 API URL
            parts = repo_url.replace("https://github.com/", "").split("/")
            if len(parts) >= 2:
                user, repo = parts[0], parts[1]
                api_url = f"https://api.github.com/repos/{user}/{repo}"
                download_url = f"https://github.com/{user}/{repo}/archive/refs/heads/main.zip"
                
                try:
                    # 获取仓库信息
                    response = requests.get(api_url, timeout=30)
                    if response.status_code == 200:
                        repo_info = response.json()
                        print(f"   仓库: {repo_info.get('full_name', 'Unknown')}")
                        print(f"   描述: {repo_info.get('description', 'No description')}")
                        print(f"   星标: {repo_info.get('stargazers_count', 0)}")
                        
                    # 下载ZIP文件
                    print(f"   下载URL: {download_url}")
                    zip_response = requests.get(download_url, timeout=60)
                    
                    if zip_response.status_code == 200:
                        # 创建目标目录
                        os.makedirs(target_dir, exist_ok=True)
                        
                        # 保存并解压ZIP文件
                        zip_path = os.path.join(target_dir, f"{repo}.zip")
                        with open(zip_path, 'wb') as f:
                            f.write(zip_response.content)
                        
                        # 解压文件
                        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                            zip_ref.extractall(target_dir)
                        
                        # 删除ZIP文件
                        os.remove(zip_path)
                        
                        print(f"   ✅ 下载完成: {target_dir}")
                        return True
                    else:
                        print(f"   ❌ 下载失败: HTTP {zip_response.status_code}")
                        return False
                        
                except Exception as e:
                    print(f"   ❌ 下载异常: {e}")
                    return False
        
        return False
    
    def parse_anthropic_skills(self, skills_dir: str):
        """解析Anthropic技能"""
        print(f"🔍 解析Anthropic技能: {skills_dir}")
        
        skills = []
        skills_path = Path(skills_dir)
        
        # 查找所有SKILL.md文件
        for skill_file in skills_path.rglob("SKILL.md"):
            try:
                with open(skill_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # 解析YAML frontmatter
                if content.startswith('---'):
                    parts = content.split('---', 2)
                    if len(parts) >= 3:
                        import yaml
                        try:
                            metadata = yaml.safe_load(parts[1])
                            instructions = parts[2].strip()
                            
                            skill = {
                                'name': metadata.get('name', skill_file.parent.name),
                                'description': metadata.get('description', ''),
                                'category': metadata.get('category', 'general'),
                                'tags': metadata.get('tags', []),
                                'instructions': instructions,
                                'source': 'anthropic',
                                'path': str(skill_file)
                            }
                            skills.append(skill)
                            print(f"   ✅ 解析技能: {skill['name']}")
                            
                        except yaml.YAMLError as e:
                            print(f"   ⚠️ YAML解析失败: {skill_file} - {e}")
                
            except Exception as e:
                print(f"   ❌ 文件读取失败: {skill_file} - {e}")
        
        print(f"   📊 总共解析: {len(skills)} 个技能")
        return skills
    
    def parse_voltbot_skills(self, skills_dir: str):
        """解析VoltBot技能"""
        print(f"🔍 解析VoltBot技能: {skills_dir}")
        
        skills = []
        skills_path = Path(skills_dir)
        
        # 查找README.md文件来提取技能信息
        readme_file = skills_path / "README.md"
        if readme_file.exists():
            try:
                with open(readme_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # 简单解析技能列表（基于markdown格式）
                lines = content.split('\n')
                current_category = "general"
                
                for line in lines:
                    line = line.strip()
                    
                    # 检测分类标题
                    if line.startswith('##') and not line.startswith('###'):
                        current_category = line.replace('#', '').strip().lower()
                        continue
                    
                    # 检测技能项（以-开头，包含链接）
                    if line.startswith('-') and '[' in line and ']' in line:
                        try:
                            # 提取技能名称和描述
                            parts = line.split(' - ', 1)
                            if len(parts) >= 2:
                                name_part = parts[0].replace('-', '').strip()
                                description = parts[1].strip()
                                
                                # 提取技能名称（去掉markdown链接格式）
                                if '[' in name_part and ']' in name_part:
                                    name = name_part.split('[')[1].split(']')[0]
                                else:
                                    name = name_part
                                
                                skill = {
                                    'name': name,
                                    'description': description,
                                    'category': current_category,
                                    'tags': [current_category, 'voltbot', 'community'],
                                    'instructions': f"技能描述: {description}",
                                    'source': 'voltbot',
                                    'path': str(readme_file)
                                }
                                skills.append(skill)
                                
                        except Exception as e:
                            print(f"   ⚠️ 技能解析失败: {line[:50]}... - {e}")
                
            except Exception as e:
                print(f"   ❌ README读取失败: {e}")
        
        print(f"   📊 总共解析: {len(skills)} 个技能")
        return skills
    
    def integrate_skills_to_system(self, skills: list):
        """将技能集成到团队技能系统中"""
        print(f"🔗 集成技能到团队系统...")
        
        integrated_count = 0
        failed_count = 0
        
        # 技能分类映射
        skill_category_mapping = {
            'web': ['javascript_programming', 'html_css', 'web_development'],
            'frontend': ['javascript_programming', 'react', 'ui_ux_design'],
            'backend': ['python_programming', 'api_development', 'database_design'],
            'data': ['python_programming', 'data_analysis', 'machine_learning'],
            'devops': ['docker_containerization', 'kubernetes', 'ci_cd'],
            'testing': ['automation_testing', 'performance_testing', 'quality_assurance'],
            'security': ['security_analysis', 'penetration_testing', 'compliance'],
            'ai': ['machine_learning', 'ai_development', 'prompt_engineering'],
            'mobile': ['mobile_development', 'react_native', 'app_design'],
            'database': ['database_design', 'sql_optimization', 'data_modeling']
        }
        
        for skill in skills:
            try:
                # 确定技能应该分配给哪些角色
                category = skill.get('category', 'general').lower()
                skill_names = skill_category_mapping.get(category, ['general_programming'])
                
                # 为相关角色添加技能
                for role_name, profile in self.skills_system.role_profiles.items():
                    role_keywords = role_name.lower()
                    
                    # 根据角色类型匹配技能
                    should_add = False
                    if 'full-stack' in role_keywords and category in ['web', 'frontend', 'backend']:
                        should_add = True
                    elif 'ui/ux' in role_keywords and category in ['frontend', 'web', 'design']:
                        should_add = True
                    elif 'devops' in role_keywords and category in ['devops', 'infrastructure']:
                        should_add = True
                    elif 'data' in role_keywords and category in ['data', 'ai', 'analytics']:
                        should_add = True
                    elif 'security' in role_keywords and category in ['security', 'compliance']:
                        should_add = True
                    elif 'test' in role_keywords and category in ['testing', 'quality']:
                        should_add = True
                    elif category == 'general':  # 通用技能分配给所有角色
                        should_add = True
                    
                    if should_add:
                        # 通过代码分析添加技能
                        mock_code = f"# {skill['name']} skill\\n# {skill['description']}\\n# Category: {category}"
                        recognized_skills = self.skills_system.analyze_code_skills(
                            role_name, mock_code, f"skill_{skill['name']}.py"
                        )
                        
                        if recognized_skills:
                            integrated_count += 1
                
                print(f"   ✅ 集成技能: {skill['name']} ({skill['source']})")
                
            except Exception as e:
                failed_count += 1
                print(f"   ❌ 集成失败: {skill['name']} - {e}")
        
        print(f"📊 技能集成完成:")
        print(f"   ✅ 成功集成: {integrated_count} 个技能")
        print(f"   ❌ 集成失败: {failed_count} 个技能")
        
        return integrated_count, failed_count
    
    def run_download_and_integration(self):
        """运行下载和集成流程"""
        print("🚀 开始GitHub技能下载和集成流程")
        print("="*60)
        
        # 创建临时下载目录
        download_dir = ".kiro/downloads/github_skills"
        os.makedirs(download_dir, exist_ok=True)
        
        all_skills = []
        
        # 下载Anthropic技能
        anthropic_dir = os.path.join(download_dir, "anthropic_skills")
        if self.download_repository("https://github.com/anthropics/skills", anthropic_dir):
            anthropic_skills = self.parse_anthropic_skills(anthropic_dir)
            all_skills.extend(anthropic_skills)
        
        # 下载VoltBot技能
        voltbot_dir = os.path.join(download_dir, "voltbot_skills")
        if self.download_repository("https://github.com/VoltAgent/awesome-moltbot-skills", voltbot_dir):
            voltbot_skills = self.parse_voltbot_skills(voltbot_dir)
            all_skills.extend(voltbot_skills)
        
        # 集成技能到系统
        if all_skills:
            integrated, failed = self.integrate_skills_to_system(all_skills)
            
            # 保存技能信息
            skills_info = {
                "download_time": datetime.now().isoformat(),
                "total_skills": len(all_skills),
                "integrated_skills": integrated,
                "failed_integrations": failed,
                "skills": all_skills
            }
            
            info_file = os.path.join(download_dir, "skills_info.json")
            with open(info_file, 'w', encoding='utf-8') as f:
                json.dump(skills_info, f, ensure_ascii=False, indent=2)
            
            print(f"📄 技能信息已保存: {info_file}")
        
        return len(all_skills)


def main():
    """主函数"""
    try:
        downloader = GitHubSkillsDownloader()
        total_skills = downloader.run_download_and_integration()
        
        print(f"\n🎉 GitHub技能下载和集成完成！")
        print(f"   总共处理: {total_skills} 个技能")
        
        return 0
        
    except Exception as e:
        print(f"❌ 执行失败: {e}")
        return 1


if __name__ == "__main__":
    exit(main())