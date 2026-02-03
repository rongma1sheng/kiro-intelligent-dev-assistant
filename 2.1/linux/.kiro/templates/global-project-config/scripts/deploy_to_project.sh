#!/bin/bash
# 通用项目管理配置部署脚本


# Mac环境检测和适配
if [[ "$OSTYPE" == "darwin"* ]]; then
    echo "🍎 检测到macOS环境，启用Mac适配..."
    
    # 检测芯片架构
    ARCH=$(uname -m)
    if [[ "$ARCH" == "arm64" ]]; then
        echo "🔧 Apple Silicon芯片已检测"
        export HOMEBREW_PREFIX="/opt/homebrew"
    else
        echo "🔧 Intel芯片已检测"
        export HOMEBREW_PREFIX="/usr/local"
    fi
    
    # 设置Mac环境变量
    export PATH="$HOMEBREW_PREFIX/bin:$PATH"
    export SHELL="/bin/zsh"
    
    # 使用python3命令
    PYTHON_CMD="python3"
    PIP_CMD="pip3"
else
    PYTHON_CMD="python"
    PIP_CMD="pip"
fi

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 默认参数
PROJECT_ROOT="."
PROJECT_TYPE="medium"
LANGUAGE="python"
TEAM_SIZE=6
FORCE=false

# 帮助信息
show_help() {
    echo "通用项目管理配置部署脚本"
    echo ""
    echo "用法: $0 [选项]"
    echo ""
    echo "选项:"
    echo "  -p, --project-root PATH    项目根目录 (默认: .)"
    echo "  -t, --project-type TYPE    项目类型 (small|medium|large, 默认: medium)"
    echo "  -l, --language LANG        主要编程语言 (python|javascript|java|cpp|go|rust, 默认: python)"
    echo "  -s, --team-size SIZE       团队规模 (默认: 6)"
    echo "  -f, --force               强制覆盖现有配置"
    echo "  -h, --help                显示此帮助信息"
    echo ""
    echo "示例:"
    echo "  $0 --project-type small --language javascript --team-size 3"
    echo "  $0 --project-root /path/to/project --force"
}

# 解析命令行参数
while [[ $# -gt 0 ]]; do
    case $1 in
        -p|--project-root)
            PROJECT_ROOT="$2"
            shift 2
            ;;
        -t|--project-type)
            PROJECT_TYPE="$2"
            shift 2
            ;;
        -l|--language)
            LANGUAGE="$2"
            shift 2
            ;;
        -s|--team-size)
            TEAM_SIZE="$2"
            shift 2
            ;;
        -f|--force)
            FORCE=true
            shift
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            echo -e "${RED}错误: 未知参数 $1${NC}"
            show_help
            exit 1
            ;;
    esac
done

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEMPLATE_ROOT="$(dirname "$SCRIPT_DIR")"

echo -e "${BLUE}🚀 开始部署通用项目管理配置${NC}"
echo -e "${BLUE}项目根目录: $PROJECT_ROOT${NC}"
echo -e "${BLUE}项目类型: $PROJECT_TYPE${NC}"
echo -e "${BLUE}编程语言: $LANGUAGE${NC}"
echo -e "${BLUE}团队规模: $TEAM_SIZE${NC}"

# 检查项目根目录
if [[ ! -d "$PROJECT_ROOT" ]]; then
    echo -e "${RED}❌ 项目根目录不存在: $PROJECT_ROOT${NC}"
    exit 1
fi

# 切换到项目根目录
cd "$PROJECT_ROOT"

# 检查是否已存在配置
if [[ -d ".kiro" && "$FORCE" != true ]]; then
    echo -e "${YELLOW}⚠️ 检测到现有.kiro配置目录${NC}"
    echo -e "${YELLOW}使用 --force 参数强制覆盖，或手动备份现有配置${NC}"
    exit 1
fi

# 备份现有配置（如果存在）
if [[ -d ".kiro" && "$FORCE" == true ]]; then
    BACKUP_DIR=".kiro.backup.$(date +%Y%m%d_%H%M%S)"
    echo -e "${YELLOW}📦 备份现有配置到: $BACKUP_DIR${NC}"
    mv ".kiro" "$BACKUP_DIR"
fi

# 创建目录结构
echo -e "${GREEN}📁 创建目录结构${NC}"
mkdir -p .kiro/{steering,hooks,scripts,specs}
mkdir -p tests/{unit,integration}
mkdir -p {docs,reports}

# 复制配置文件
echo -e "${GREEN}📋 复制配置模板${NC}"

# 复制steering文件
cp "$TEMPLATE_ROOT/steering/task-hierarchy-management-template.md" ".kiro/steering/task-hierarchy-management.md"
cp "$TEMPLATE_ROOT/steering/silicon-valley-team-config-template.md" ".kiro/steering/silicon-valley-team-config.md"

# 复制hook文件
cp "$TEMPLATE_ROOT/hooks/task-lifecycle-management-template.kiro.hook" ".kiro/hooks/task-lifecycle-management.kiro.hook"
cp "$TEMPLATE_ROOT/hooks/quality-gate-enforcement-template.kiro.hook" ".kiro/hooks/quality-gate-enforcement.kiro.hook"
cp "$TEMPLATE_ROOT/hooks/test-coverage-monitor-template.kiro.hook" ".kiro/hooks/test-coverage-monitor.kiro.hook"

# 复制脚本文件
cp "$TEMPLATE_ROOT/scripts/universal_quality_gate.py" ".kiro/scripts/"
cp "$TEMPLATE_ROOT/scripts/project_initializer.py" ".kiro/scripts/"

# 复制文档
cp "$TEMPLATE_ROOT/README.md" ".kiro/"
cp "$TEMPLATE_ROOT/USAGE_GUIDE.md" ".kiro/"

# 使用Python脚本进行项目特定配置
echo -e "${GREEN}⚙️ 配置项目特定设置${NC}"
if command -v python3 &> /dev/null; then
    python3 "$TEMPLATE_ROOT/scripts/project_initializer.py" \
        --project-root "." \
        --project-type "$PROJECT_TYPE" \
        --language "$LANGUAGE" \
        --team-size "$TEAM_SIZE"
else
    echo -e "${YELLOW}⚠️ 未找到python3，跳过自动配置${NC}"
    echo -e "${YELLOW}请手动运行: python3 .kiro/scripts/project_initializer.py${NC}"
fi

# 设置脚本执行权限
chmod +x .kiro/scripts/*.py
chmod +x .kiro/scripts/*.sh 2>/dev/null || true

# 创建基本的gitignore（如果不存在）
if [[ ! -f ".gitignore" ]]; then
    echo -e "${GREEN}📝 创建基本.gitignore文件${NC}"
    cat > .gitignore << EOF
# 通用忽略文件
__pycache__/
*.pyc
*.pyo
*.pyd
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# 测试和覆盖率
.coverage
.pytest_cache/
htmlcov/
.tox/
coverage.xml
*.cover
.hypothesis/

# 环境变量
.env
.venv
env/
venv/
ENV/
env.bak/
venv.bak/

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# 操作系统
.DS_Store
Thumbs.db

# 项目特定
reports/
logs/
*.log
EOF
fi

# 验证部署
echo -e "${GREEN}✅ 验证部署结果${NC}"

# 检查必需文件
REQUIRED_FILES=(
    ".kiro/steering/task-hierarchy-management.md"
    ".kiro/steering/silicon-valley-team-config.md"
    ".kiro/hooks/task-lifecycle-management.kiro.hook"
    ".kiro/scripts/universal_quality_gate.py"
)

ALL_GOOD=true
for file in "${REQUIRED_FILES[@]}"; do
    if [[ -f "$file" ]]; then
        echo -e "${GREEN}✓ $file${NC}"
    else
        echo -e "${RED}✗ $file${NC}"
        ALL_GOOD=false
    fi
done

if [[ "$ALL_GOOD" == true ]]; then
    echo -e "${GREEN}🎉 部署成功完成！${NC}"
    echo ""
    echo -e "${BLUE}📋 后续步骤:${NC}"
    echo -e "${BLUE}1. 查看项目配置: cat .kiro/project_config.json${NC}"
    echo -e "${BLUE}2. 运行质量检查: $PYTHON_CMD .kiro/scripts/universal_quality_gate.py${NC}"
    echo -e "${BLUE}3. 查看使用指南: cat .kiro/USAGE_GUIDE.md${NC}"
    echo -e "${BLUE}4. 开始开发工作，Hook会自动执行质量门禁${NC}"
    echo ""
    echo -e "${GREEN}🚀 项目已准备就绪！${NC}"
else
    echo -e "${RED}❌ 部署过程中出现问题，请检查上述错误${NC}"
    exit 1
fi