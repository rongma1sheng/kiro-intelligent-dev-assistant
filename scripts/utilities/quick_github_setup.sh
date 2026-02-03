#!/bin/bash
# Kiro智能开发助手 - GitHub仓库快速设置脚本

echo "🚀 Kiro智能开发助手 - GitHub仓库设置"
echo "=================================="

# 检查GitHub CLI
if ! command -v gh &> /dev/null; then
    echo "❌ GitHub CLI未安装，请手动创建仓库"
    echo "访问: https://github.com/new"
    echo "仓库名: kiro-intelligent-dev-assistant"
    exit 1
fi

# 创建仓库
echo "📝 创建GitHub仓库..."
gh repo create kiro-intelligent-dev-assistant --public --description "🤖 Kiro智能开发助手 - AI驱动的跨平台开发工具，集成智能代码审查、自动化测试和知识管理"

if [ $? -eq 0 ]; then
    echo "✅ 仓库创建成功"
    
    # 推送代码
    echo "📤 推送代码到GitHub..."
    git add .
    git commit -m "🚀 Initial commit: Kiro智能开发助手跨平台版本"
    git push -u origin main
    
    if [ $? -eq 0 ]; then
        echo "✅ 代码推送成功"
        echo "🎉 设置完成！访问: https://github.com/$(gh api user --jq .login)/kiro-intelligent-dev-assistant"
    else
        echo "❌ 代码推送失败，请检查权限"
    fi
else
    echo "❌ 仓库创建失败，可能已存在"
fi
