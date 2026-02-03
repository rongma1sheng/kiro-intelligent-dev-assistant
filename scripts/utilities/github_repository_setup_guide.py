#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GitHub仓库设置指南生成器
为用户提供详细的GitHub仓库创建和配置步骤
"""

import json
from datetime import datetime
from pathlib import Path

class GitHubRepositorySetupGuide:
    def __init__(self):
        self.repo_name = "kiro-intelligent-dev-assistant"
        self.setup_steps = []
        self.seo_config = {}
        
    def generate_setup_guide(self):
        """生成完整的GitHub仓库设置指南"""
        
        guide_content = f"""
# 🚀 GitHub仓库创建和配置指南

## 📋 仓库基本信息
- **仓库名称**: `{self.repo_name}`
- **可见性**: Public（公开，提高SEO效果）
- **描述**: 🤖 Kiro智能开发助手 - AI驱动的跨平台开发工具，集成智能代码审查、自动化测试和知识管理

## 🎯 第一步：创建GitHub仓库

### 方法1：通过GitHub网页创建
1. 访问 https://github.com/new
2. 填写仓库信息：
   - Repository name: `{self.repo_name}`
   - Description: `🤖 Kiro智能开发助手 - AI驱动的跨平台开发工具，集成智能代码审查、自动化测试和知识管理`
   - Visibility: ✅ Public
   - Initialize repository: ❌ 不要勾选（我们已有内容）
3. 点击 "Create repository"

### 方法2：通过GitHub CLI创建
```bash
# 安装GitHub CLI (如果未安装)
# Windows: winget install GitHub.cli
# macOS: brew install gh
# Linux: 参考 https://cli.github.com/

# 登录GitHub
gh auth login

# 创建仓库
gh repo create {self.repo_name} --public --description "🤖 Kiro智能开发助手 - AI驱动的跨平台开发工具，集成智能代码审查、自动化测试和知识管理"
```

## 🔧 第二步：配置仓库设置

### Topics标签设置
在仓库页面点击设置图标，添加以下Topics：
```
artificial-intelligence
intelligent-assistant
code-review
automated-testing
knowledge-management
cross-platform
python
windows
macos
linux
development-tools
ai-powered
smart-coding
quality-assurance
```

### 仓库描述优化
```
🤖 Kiro智能开发助手 - AI驱动的跨平台开发工具 | 集成智能代码审查、自动化测试、知识管理和Hook系统 | 支持Windows/macOS/Linux
```

## 📤 第三步：推送代码

### 推送命令序列
```bash
# 确认当前Git状态
git status

# 添加所有文件到暂存区
git add .

# 提交更改
git commit -m "🚀 Initial commit: Kiro智能开发助手跨平台版本"

# 推送到GitHub
git push -u origin main
```

### 如果推送失败，执行以下命令：
```bash
# 强制推送（谨慎使用）
git push -u origin main --force

# 或者重新设置远程地址
git remote remove origin
git remote add origin https://github.com/你的用户名/{self.repo_name}.git
git push -u origin main
```

## 📊 第四步：SEO优化配置

### README.md更新
- ✅ 已生成优化版README建议
- 📍 位置: `.kiro/reports/seo_optimization_recommendations.md`
- 🎯 包含跨平台关键词和安装指南

### GitHub Pages设置（可选）
1. 进入仓库Settings
2. 滚动到Pages部分
3. Source选择"Deploy from a branch"
4. Branch选择"main"，文件夹选择"/ (root)"
5. 保存设置

### 项目徽章添加
在README.md中添加以下徽章：
```markdown
[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Windows](https://img.shields.io/badge/Windows-0078D6?style=flat&logo=windows&logoColor=white)](https://github.com/你的用户名/{self.repo_name})
[![macOS](https://img.shields.io/badge/macOS-000000?style=flat&logo=apple&logoColor=white)](https://github.com/你的用户名/{self.repo_name})
[![Linux](https://img.shields.io/badge/Linux-FCC624?style=flat&logo=linux&logoColor=black)](https://github.com/你的用户名/{self.repo_name})
```

## 🎯 第五步：验证设置

### 检查清单
- [ ] 仓库已创建并设为Public
- [ ] Topics标签已添加
- [ ] 仓库描述已优化
- [ ] 代码已成功推送
- [ ] README.md显示正常
- [ ] 安装脚本可访问
- [ ] 跨平台配置文件完整

### 测试安装脚本
```bash
# 克隆仓库测试
git clone https://github.com/你的用户名/{self.repo_name}.git
cd {self.repo_name}

# Windows测试
setup_windows.bat

# macOS/Linux测试
chmod +x setup_mac.sh
./setup_mac.sh

# 通用Python测试
python setup.py
```

## 📈 第六步：推广和优化

### 立即行动
1. **社交媒体分享**: 在Twitter、LinkedIn分享项目
2. **技术社区**: 在Reddit r/Python、r/MachineLearning分享
3. **文档完善**: 添加更多使用示例和教程
4. **Issue模板**: 创建Issue和PR模板

### 持续优化
1. **监控指标**: 关注Stars、Forks、Issues数量
2. **用户反馈**: 收集和响应用户反馈
3. **功能迭代**: 基于用户需求持续改进
4. **社区建设**: 建立活跃的用户社区

## 🚨 常见问题解决

### 推送权限问题
```bash
# 检查远程地址
git remote -v

# 使用HTTPS认证
git remote set-url origin https://github.com/你的用户名/{self.repo_name}.git

# 或使用SSH认证
git remote set-url origin git@github.com:你的用户名/{self.repo_name}.git
```

### 文件过大问题
```bash
# 检查大文件
find . -size +100M -type f

# 使用Git LFS（如果需要）
git lfs track "*.model"
git lfs track "*.data"
```

---

**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
**智能助手**: 🧠 Knowledge Engineer  
**状态**: 准备执行
"""
        
        return guide_content
    
    def create_quick_setup_script(self):
        """创建快速设置脚本"""
        
        script_content = f'''#!/bin/bash
# Kiro智能开发助手 - GitHub仓库快速设置脚本

echo "🚀 Kiro智能开发助手 - GitHub仓库设置"
echo "=================================="

# 检查GitHub CLI
if ! command -v gh &> /dev/null; then
    echo "❌ GitHub CLI未安装，请手动创建仓库"
    echo "访问: https://github.com/new"
    echo "仓库名: {self.repo_name}"
    exit 1
fi

# 创建仓库
echo "📝 创建GitHub仓库..."
gh repo create {self.repo_name} --public --description "🤖 Kiro智能开发助手 - AI驱动的跨平台开发工具，集成智能代码审查、自动化测试和知识管理"

if [ $? -eq 0 ]; then
    echo "✅ 仓库创建成功"
    
    # 推送代码
    echo "📤 推送代码到GitHub..."
    git add .
    git commit -m "🚀 Initial commit: Kiro智能开发助手跨平台版本"
    git push -u origin main
    
    if [ $? -eq 0 ]; then
        echo "✅ 代码推送成功"
        echo "🎉 设置完成！访问: https://github.com/$(gh api user --jq .login)/{self.repo_name}"
    else
        echo "❌ 代码推送失败，请检查权限"
    fi
else
    echo "❌ 仓库创建失败，可能已存在"
fi
'''
        
        return script_content

def main():
    """主函数"""
    guide_generator = GitHubRepositorySetupGuide()
    
    # 生成设置指南
    guide_content = guide_generator.generate_setup_guide()
    
    # 保存指南文件
    guide_path = Path(".kiro/reports/github_repository_setup_guide.md")
    guide_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(guide_path, 'w', encoding='utf-8') as f:
        f.write(guide_content)
    
    # 生成快速设置脚本
    script_content = guide_generator.create_quick_setup_script()
    script_path = Path("scripts/utilities/quick_github_setup.sh")
    
    with open(script_path, 'w', encoding='utf-8') as f:
        f.write(script_content)
    
    # 设置脚本执行权限（Unix系统）
    import os
    import stat
    if os.name != 'nt':  # 非Windows系统
        os.chmod(script_path, stat.S_IRWXU | stat.S_IRGRP | stat.S_IROTH)
    
    print("✅ GitHub仓库设置指南已生成")
    print(f"📍 指南位置: {guide_path}")
    print(f"📍 快速脚本: {script_path}")
    
    return {
        "guide_path": str(guide_path),
        "script_path": str(script_path),
        "repo_name": "kiro-intelligent-dev-assistant",
        "status": "ready_for_setup"
    }

if __name__ == "__main__":
    result = main()
    print(f"🎯 下一步：按照指南创建GitHub仓库 '{result['repo_name']}'")