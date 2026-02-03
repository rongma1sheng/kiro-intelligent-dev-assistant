# macOS开发环境配置指南

## 系统要求
- macOS 12.0 (Monterey) 或更高版本
- 至少8GB RAM (推荐16GB+)
- 至少50GB可用磁盘空间
- 稳定的网络连接

## 必需工具安装

### 1. Homebrew包管理器
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

### 2. Xcode Command Line Tools
```bash
xcode-select --install
```

### 3. Python环境
```bash
# 使用Homebrew安装Python
brew install python@3.11
brew install python@3.12

# 安装pipenv
pip3 install pipenv
```

### 4. Node.js环境
```bash
# 安装Node.js
brew install node

# 安装yarn
brew install yarn
```

### 5. Git配置
```bash
# 配置Git
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"
git config --global init.defaultBranch main
```

## Kiro配置优化

### 1. MCP服务器配置
- 使用`mcp_darwin.json`配置文件
- 启用macOS特定优化
- 配置Homebrew路径支持

### 2. Hook系统配置
- 启用Mac特定Hook
- 配置性能监控
- 设置兼容性检查

### 3. 环境变量设置
```bash
# 添加到~/.zshrc
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"
export KIRO_PLATFORM="darwin"
export SHELL="/bin/zsh"
```

## 性能优化建议

### 1. 系统设置
- 启用"减少动画"以提升性能
- 配置Spotlight索引排除开发目录
- 设置合适的虚拟内存

### 2. 开发工具优化
- 配置IDE内存设置
- 启用增量编译
- 使用SSD存储开发项目

### 3. 网络优化
- 配置DNS服务器
- 启用网络缓存
- 优化代理设置

## 故障排除

### 常见问题
1. **权限问题**: 使用`sudo`或配置正确的文件权限
2. **路径问题**: 检查PATH环境变量配置
3. **依赖冲突**: 使用虚拟环境隔离项目依赖
4. **性能问题**: 检查系统资源使用情况

### 诊断命令
```bash
# 检查系统信息
system_profiler SPSoftwareDataType

# 检查内存使用
vm_stat

# 检查磁盘使用
df -h

# 检查进程
top -o cpu
```

## 最佳实践

1. **定期更新**: 保持系统和工具最新版本
2. **备份配置**: 定期备份开发环境配置
3. **监控性能**: 使用内置工具监控系统性能
4. **安全设置**: 启用防火墙和系统完整性保护

## 支持和帮助

如遇到问题，请：
1. 查看系统日志: `Console.app`
2. 检查Kiro日志: `.kiro/logs/`
3. 运行诊断工具: `kiro diagnose`
4. 联系技术支持

---
最后更新: 2026-02-03T13:56:08.774513
维护者: DevOps Engineer
