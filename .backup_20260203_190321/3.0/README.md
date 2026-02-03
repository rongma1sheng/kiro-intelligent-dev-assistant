# Kiro Silicon Valley Template - 版本3.0

## 🎯 版本概述

版本3.0是Kiro硅谷模板的最新版本，提供了完整的跨平台支持和优化配置。

## 📁 目录结构

```
3.0/
├── base/                 # 基础配置文件
│   └── mcp.json         # 基础MCP配置
├── win/                 # Windows平台配置
│   ├── settings/        # Windows设置文件
│   ├── hooks/          # Windows Hook配置
│   ├── steering/       # Windows引导文件
│   └── docs/           # Windows文档
├── mac/                 # macOS平台配置
│   ├── settings/        # macOS设置文件
│   ├── hooks/          # macOS Hook配置
│   ├── steering/       # macOS引导文件
│   └── docs/           # macOS文档
└── linux/               # Linux平台配置
    ├── settings/        # Linux设置文件
    ├── hooks/          # Linux Hook配置
    ├── steering/       # Linux引导文件
    └── docs/           # Linux文档
```

## 🚀 平台特性

### Windows (win/)
- PowerShell集成优化
- Windows路径处理
- 注册表集成支持
- Visual Studio优化

### macOS (mac/)
- Homebrew路径优化
- Zsh shell集成
- Spotlight集成
- Keychain支持

### Linux (linux/)
- 多包管理器支持
- Systemd集成
- 容器化支持
- 性能调优

## 📊 版本历史

- **3.0.0** (2026-02-03) - 完整跨平台支持，配置继承机制
- **2.1.0** - Mac配置优化
- **2.0.0** - 基础MCP配置统一
- **1.0.0** - 初始版本

## 🔧 使用方法

1. 根据你的操作系统选择对应的平台目录
2. 将配置文件复制到`.kiro/`目录下
3. 根据需要调整平台特定设置
4. 重启Kiro以应用新配置

## 📝 更新日志

### 版本3.0.0新特性
- ✅ 完整的跨平台配置支持
- ✅ 配置继承机制
- ✅ 平台特定优化
- ✅ 统一的Hook系统
- ✅ 性能调优配置

---

**维护者**: 🏗️ Software Architect  
**创建日期**: 2026-02-03  
**版本**: 3.0.0
