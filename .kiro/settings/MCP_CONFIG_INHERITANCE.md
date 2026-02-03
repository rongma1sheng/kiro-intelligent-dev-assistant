# MCP配置继承机制

## 概述
新的MCP配置系统采用继承机制，避免重复定义，提高可维护性。

## 配置文件结构
```
.kiro/settings/
├── mcp.json           # 基础配置（所有平台共享）
├── mcp_darwin.json    # macOS特定配置
└── mcp_win32.json     # Windows特定配置
```

## 继承规则
1. **基础配置** (`mcp.json`): 包含所有平台共享的MCP服务器定义
2. **平台配置**: 通过 `_extends` 字段继承基础配置
3. **覆盖机制**: 平台配置中的设置会覆盖基础配置中的相同字段
4. **合并策略**: 嵌套对象会进行深度合并

## 配置示例
### 基础配置 (mcp.json)
```json
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "."],
      "env": {
        "FILESYSTEM_MAX_FILE_SIZE": "10MB"
      }
    }
  }
}
```

### 平台配置 (mcp_darwin.json)
```json
{
  "_extends": "mcp.json",
  "mcpServers": {
    "filesystem": {
      "env": {
        "SHELL": "/bin/zsh"
      }
    }
  }
}
```

## 最终效果
macOS平台的最终配置将是：
```json
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "."],
      "env": {
        "FILESYSTEM_MAX_FILE_SIZE": "10MB",
        "SHELL": "/bin/zsh"
      }
    }
  }
}
```

## 维护指南
1. **通用设置**: 修改 `mcp.json`
2. **平台特定设置**: 修改对应的平台配置文件
3. **新增服务器**: 优先在基础配置中添加，平台差异在平台配置中覆盖
4. **配置验证**: 使用配置验证工具检查继承关系的正确性

## 版本历史
- v2.0: 引入配置继承机制，解决重复定义问题
- v1.0: 原始配置方式（已废弃）
