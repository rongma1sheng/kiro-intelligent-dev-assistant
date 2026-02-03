# 🏗️ Kiro配置系统版本化目录结构

## 📊 目录结构概览

```
kiro-silicon-valley-template/
├── 1.0/                    # v1.0 基础版本
│   ├── win/                # Windows平台配置
│   ├── mac/                # Mac平台配置 (不支持)
│   └── linux/              # Linux平台配置
├── 2.0/                    # v2.0 增强版本
│   ├── win/                # Windows平台配置
│   ├── mac/                # Mac平台配置 (不支持)
│   └── linux/              # Linux平台配置
├── 2.1/                    # v2.1 Mac适配版本 (当前最新)
│   ├── win/                # Windows平台配置
│   ├── mac/                # Mac平台配置 (完全支持)
│   └── linux/              # Linux平台配置
├── VERSION_INDEX.json      # 版本索引文件
└── VERSIONED_STRUCTURE_README.md  # 本文档
```

## 🎯 版本化设计理念

### 清晰的版本分离
- **按版本分离**: 每个主要版本有独立目录
- **按平台分离**: 每个版本下按平台组织配置
- **向后兼容**: 新版本不影响旧版本使用
- **平台特化**: 每个平台有专门优化的配置

### 版本演进路径
```
v1.0 (基础版) → v2.0 (增强版) → v2.1 (Mac适配版)
     ↓              ↓              ↓
  Win/Linux     Win/Linux     Win/Mac/Linux
```

## 📋 版本对比表

| 功能特性 | v1.0 | v2.0 | v2.1 |
|---------|------|------|------|
| **平台支持** |
| Windows | ✅ | ✅ | ✅ |
| Linux | ✅ | ✅ | ✅ |
| macOS | ❌ | ❌ | ✅ |
| Apple Silicon | ❌ | ❌ | ✅ |
| **核心功能** |
| 硅谷12人团队 | ✅ | ✅ | ✅ |
| Hook系统 | 基础 | 增强 | 完整 |
| 质量门禁 | ✅ | ✅ | ✅ |
| 任务层次化管理 | ❌ | ✅ | ✅ |
| LLM反漂移系统 | ❌ | ✅ | ✅ |
| 跨平台模板 | ❌ | ✅ | ✅ |
| 一键安装脚本 | ❌ | ❌ | ✅ |

## 🚀 快速开始指南

### 选择合适的版本

#### 🪟 Windows用户
```bash
# 推荐使用最新版本
cd 2.1/win/
# 或根据需求选择其他版本
cd 1.0/win/  # 基础功能
cd 2.0/win/  # 增强功能
```

#### 🐧 Linux用户
```bash
# 推荐使用最新版本
cd 2.1/linux/
# 或根据需求选择其他版本
cd 1.0/linux/  # 基础功能
cd 2.0/linux/  # 增强功能
```

#### 🍎 Mac用户
```bash
# Mac用户只能使用v2.1+版本
cd 2.1/mac/
./setup_mac.sh  # 一键安装
```

### 版本升级路径

#### 从v1.0升级到v2.1
```bash
# 1. 备份当前配置
cp -r 1.0/win/ backup/

# 2. 使用新版本配置
cd 2.1/win/

# 3. 运行配置验证
python scripts/kiro_config_validator.py
```

#### 从v2.0升级到v2.1
```bash
# 1. 直接使用新版本（向后兼容）
cd 2.1/win/  # 或 2.1/linux/ 或 2.1/mac/

# 2. 运行配置验证
python scripts/kiro_config_validator.py
```

## 📁 每个平台目录结构

```
{version}/{platform}/
├── .kiro/              # Kiro配置文件
│   ├── hooks/          # Hook配置
│   ├── settings/       # 系统设置
│   ├── steering/       # 指导文档
│   ├── specs/          # 规格说明
│   └── templates/      # 配置模板
├── scripts/            # 工具脚本
├── config/             # 配置文件
├── docs/               # 文档
├── examples/           # 示例配置
├── README.md           # 平台特定说明
└── version.json        # 版本信息
```

## 🔧 平台特定说明

### Windows平台
- **支持版本**: v1.0, v2.0, v2.1
- **Python命令**: `python`
- **Shell**: PowerShell/CMD
- **包管理**: pip

### Linux平台
- **支持版本**: v1.0, v2.0, v2.1
- **Python命令**: `python3`
- **Shell**: bash
- **包管理**: pip3/apt

### macOS平台
- **支持版本**: v2.1+ (仅限)
- **Python命令**: `python3`
- **Shell**: zsh (macOS Catalina+)
- **包管理**: pip3/Homebrew
- **特殊支持**: Apple Silicon + Intel芯片

## 📊 版本选择建议

### 🆕 新项目
**推荐**: v2.1 (最新版本)
- 完整功能支持
- 跨平台兼容
- 持续更新维护

### 🔄 现有项目升级
**评估标准**:
1. **功能需求**: 是否需要新版本功能
2. **平台支持**: 是否需要Mac支持
3. **团队规模**: 是否需要完整的12人团队配置
4. **维护成本**: 升级的工作量评估

### 🍎 Mac团队
**必须**: v2.1+
- Mac平台唯一支持版本
- Apple Silicon优化
- 一键安装脚本

## 🔍 版本信息查询

### 查看版本索引
```bash
cat VERSION_INDEX.json
```

### 查看特定版本信息
```bash
cat 2.1/mac/version.json
```

### 验证配置完整性
```bash
cd 2.1/mac/
python scripts/kiro_config_validator.py
```

## 🛠️ 维护和更新

### 版本发布流程
1. **开发新功能** → 在当前版本基础上开发
2. **创建新版本目录** → 使用版本组织器
3. **适配各平台** → 确保跨平台兼容性
4. **更新版本索引** → 更新VERSION_INDEX.json
5. **创建发布说明** → 详细的变更日志
6. **Git标签管理** → 创建版本标签

### 版本维护策略
- **当前版本**: v2.1 - 积极维护，新功能开发
- **前一版本**: v2.0 - 安全更新，重要Bug修复
- **历史版本**: v1.0 - 仅安全更新

## 📞 支持和帮助

### 获取帮助
- **通用问题**: 查看根目录README.md
- **版本特定问题**: 查看对应版本的README.md
- **平台特定问题**: 查看对应平台的README.md

### 问题报告
- **GitHub Issues**: https://github.com/rongma1sheng/kiro-silicon-valley-template/issues
- **版本标签**: 请在问题中标明使用的版本
- **平台信息**: 请提供操作系统和版本信息

### 功能请求
- **GitHub Discussions**: 讨论新功能需求
- **版本规划**: 参与版本规划讨论
- **平台支持**: 请求新平台支持

---

**文档版本**: v1.0  
**最后更新**: 2026-02-02  
**维护者**: 🏗️ Software Architect  
**状态**: ✅ 生产就绪

## 🎉 总结

这个版本化目录结构为Kiro配置系统提供了：

1. **清晰的版本管理** - 每个版本独立维护
2. **平台特化支持** - 每个平台优化配置
3. **平滑升级路径** - 向后兼容的升级体验
4. **企业级标准** - 符合大型项目管理需求

无论您是Windows、Linux还是Mac用户，都能找到适合的版本和配置，享受Kiro配置系统带来的标准化开发体验！