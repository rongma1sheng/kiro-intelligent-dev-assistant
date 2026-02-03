#!/bin/bash
# MIA系统测试运行脚本

set -e  # 遇到错误立即退出

echo "======================================"
echo "MIA系统测试套件"
echo "======================================"
echo ""

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 检查是否在虚拟环境中
if [ -z "$VIRTUAL_ENV" ]; then
    echo -e "${YELLOW}⚠️  警告: 未检测到虚拟环境${NC}"
    echo "建议先激活虚拟环境: source venv/bin/activate"
    echo ""
fi

# 1. 运行单元测试
echo "======================================"
echo "1. 运行单元测试"
echo "======================================"
pytest tests/unit --cov=src --cov-report=html --cov-report=term -v

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ 单元测试通过${NC}"
else
    echo -e "${RED}❌ 单元测试失败${NC}"
    exit 1
fi

echo ""

# 2. 运行集成测试
echo "======================================"
echo "2. 运行集成测试"
echo "======================================"
pytest tests/integration --cov=src --cov-append -v

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ 集成测试通过${NC}"
else
    echo -e "${RED}❌ 集成测试失败${NC}"
    exit 1
fi

echo ""

# 3. 运行E2E测试
echo "======================================"
echo "3. 运行E2E测试"
echo "======================================"
pytest tests/e2e -v

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ E2E测试通过${NC}"
else
    echo -e "${RED}❌ E2E测试失败${NC}"
    exit 1
fi

echo ""

# 4. 生成覆盖率报告
echo "======================================"
echo "4. 生成覆盖率报告"
echo "======================================"
coverage report

echo ""
echo "HTML覆盖率报告已生成: htmlcov/index.html"

# 5. 检查覆盖率
echo ""
echo "======================================"
echo "5. 检查覆盖率"
echo "======================================"
coverage report --fail-under=85

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ 覆盖率达标 (≥85%)${NC}"
else
    echo -e "${RED}❌ 覆盖率不足 (<85%)${NC}"
    exit 1
fi

echo ""
echo "======================================"
echo "测试总结"
echo "======================================"
echo -e "${GREEN}✅ 所有测试通过！${NC}"
echo ""
echo "下一步:"
echo "  1. 查看覆盖率报告: open htmlcov/index.html"
echo "  2. 运行代码质量检查: python scripts/pre_commit_check.py"
echo "  3. 提交代码: git commit"
