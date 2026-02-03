# Kiro Specs 目录

这个目录用于存储项目规格说明文档，支持Kiro的文档同步管理功能。

## 目录结构

```
.kiro/specs/
├── README.md                 # 本文件
├── project-template/         # 项目模板规格
│   └── requirements.md       # 需求文档模板
├── feature-specs/           # 功能规格文档
│   └── requirements.md       # 功能需求文档
└── system-specs/            # 系统规格文档
    └── requirements.md       # 系统需求文档
```

## 使用说明

1. **项目规格**: 在 `project-template/` 目录下创建项目相关的规格文档
2. **功能规格**: 在 `feature-specs/` 目录下创建功能相关的规格文档  
3. **系统规格**: 在 `system-specs/` 目录下创建系统架构相关的规格文档

## 文档同步

文档同步管理器会自动监控这些目录中的 `requirements.md` 文件，确保：
- 文档格式规范
- 内容同步更新
- 版本控制管理

## 注意事项

- 所有规格文档建议使用Markdown格式
- 文件名使用小写字母和连字符
- 保持文档结构清晰，便于维护