# 🍎 macOS 设置指南

## 硅谷LLM反漂移协同系统 - Mac版本

本指南将帮助Mac用户快速设置和运行硅谷LLM反漂移协同系统。

## 🚀 一键安装

### 方法1：使用自动安装脚本（推荐）

```bash
# 克隆仓库
git clone https://github.com/rongma1sheng/kiro-silicon-valley-template.git
cd kiro-silicon-valley-template

# 运行一键安装脚本
./setup_mac.sh
```

### 方法2：手动安装

#### 1. 系统要求

- macOS 10.15+ (Catalina或更高版本)
- Xcode命令行工具
- Homebrew包管理器
- Python 3.11+

#### 2. 安装Xcode命令行工具

```bash
xcode-select --install
```

#### 3. 安装Homebrew

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

#### 4. 安装必要软件包

```bash
# 更新Homebrew
brew update

# 安装Python和其他依赖
brew install python@3.11 git node redis postgresql@15

# 安装Python包管理工具
pip3 install --upgrade pip virtualenv poetry
```

#### 5. 设置项目环境

```bash
# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 安装项目依赖
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

## 🔧 Apple Silicon 优化

如果您使用的是Apple Silicon芯片（M1/M2/M3），系统已自动优化：

- Homebrew安装路径：`/opt/homebrew`
- 原生ARM64支持
- 优化的性能配置

## 📋 验证安装

运行以下命令验证安装：

```bash
# 激活虚拟环境
source venv/bin/activate

# 运行系统检查
python scripts/mac_system_monitor.py

# 运行测试套件
python -m pytest tests/ -v

# 运行质量门禁
python scripts/mac_quality_gate.py
```

## 🛠️ Mac专用工具

系统为Mac用户提供了专门的工具：

### 1. Mac质量门禁脚本
```bash
python scripts/mac_quality_gate.py
```

### 2. Mac系统监控
```bash
python scripts/mac_system_monitor.py
```

### 3. Mac兼容性检查
```bash
python scripts/mac_compatibility.py
```

## ⚙️ 配置文件

Mac专用配置文件位置：

- 测试配置：`config/mac_test_config.json`
- 系统监控：`scripts/mac_system_monitor.py`
- 质量门禁：`scripts/mac_quality_gate.py`

## 🚨 常见问题

### Q: 安装过程中遇到权限问题
A: 使用以下命令修复权限：
```bash
sudo chown -R $(whoami) /opt/homebrew  # Apple Silicon
sudo chown -R $(whoami) /usr/local     # Intel Mac
```

### Q: Python版本冲突
A: 确保使用正确的Python版本：
```bash
# 检查Python版本
python3 --version

# 如果需要，创建别名
echo 'alias python=python3' >> ~/.zshrc
echo 'alias pip=pip3' >> ~/.zshrc
source ~/.zshrc
```

### Q: 虚拟环境激活失败
A: 重新创建虚拟环境：
```bash
rm -rf venv
python3 -m venv venv
source venv/bin/activate
```

### Q: Homebrew安装缓慢
A: 使用国内镜像加速：
```bash
# 设置Homebrew镜像
export HOMEBREW_BOTTLE_DOMAIN=https://mirrors.ustc.edu.cn/homebrew-bottles
```

## 🔍 系统架构

Mac版本完全兼容硅谷LLM反漂移协同系统的所有功能：

- ✅ 零号铁律、核心铁律、测试铁律
- ✅ 12人硅谷团队角色配置
- ✅ LLM行为约束引擎
- ✅ 实时质量监控
- ✅ 角色权限管理
- ✅ 上下文一致性锚定

## 📊 性能优化

Mac版本包含以下性能优化：

1. **Apple Silicon优化**：原生ARM64支持
2. **内存管理**：优化的内存使用策略
3. **并发处理**：利用Mac的多核优势
4. **文件系统**：APFS文件系统优化

## 🎯 下一步

安装完成后，您可以：

1. 阅读 [开发指南](00_核心文档/DEVELOPMENT_GUIDE.md)
2. 查看 [快速参考](00_核心文档/QUICK_REFERENCE.md)
3. 运行 [质量门禁检查](scripts/enhanced_quality_gate.py)
4. 开始使用 [硅谷12人团队配置](.kiro/steering/silicon-valley-team-config-optimized.md)

## 📞 支持

如果遇到问题，请：

1. 查看 [故障排除指南](00_核心文档/TROUBLESHOOTING.md)
2. 检查 [GitHub Issues](https://github.com/rongma1sheng/kiro-silicon-valley-template/issues)
3. 运行诊断工具：`python scripts/debug_360.py`

---

**版本**: 1.0.0  
**更新日期**: 2026-02-01  
**维护者**: 硅谷项目开发经理  
**状态**: 生产就绪 ✅