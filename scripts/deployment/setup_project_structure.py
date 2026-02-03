#!/usr/bin/env python3
"""
MIA系统项目目录结构自动创建脚本
根据白皮书要求创建完整的目录结构

注意: 白皮书中声称19个策略，但实际只定义了15个（缺失S03, S04, S08, S12）
已定义的策略:
- Meta-Momentum (3个): S02, S07, S13
- Meta-MeanReversion (3个): S01, S05, S11
- Meta-Following (3个): S06, S10, S15
- Meta-Arbitrage (5个): S09, S14, S17, S18, S19
- Meta-Event (1个): S16
"""

import os
from pathlib import Path
from typing import List


class ProjectStructureSetup:
    """项目结构设置器"""
    
    def __init__(self, base_path: str = "."):
        self.base_path = Path(base_path)
        self.created_dirs = []
        self.created_files = []
    
    def create_all(self):
        """创建所有目录和文件"""
        print("=" * 60)
        print("MIA系统项目目录结构创建")
        print("=" * 60)
        print()
        
        # 创建目录
        self._create_directories()
        
        # 创建__init__.py文件
        self._create_init_files()
        
        # 创建.gitkeep文件
        self._create_gitkeep_files()
        
        # 输出总结
        self._print_summary()
    
    def _create_directories(self):
        """创建所有目录"""
        print("📁 创建目录结构...")
        print()
        
        directories = [
            # 源代码 - 第一章: 柯罗诺斯生物钟
            "src/scheduler",
            
            # 源代码 - 第二章: AI三脑
            "src/brain",
            "src/brain/analyzers",
            
            # 源代码 - 第三章: 基础设施
            "src/infra",
            
            # 源代码 - 第四章: 斯巴达进化
            "src/evolution",
            
            # 源代码 - 第五章: LLM策略分析（已包含在brain/analyzers）
            
            # 源代码 - 第六章: 执行与风控
            "src/execution",
            "src/strategies/meta_momentum",
            "src/strategies/meta_mean_reversion",
            "src/strategies/meta_following",
            "src/strategies/meta_arbitrage",
            "src/strategies/meta_event",
            
            # 源代码 - 第七章: 安全与审计
            "src/config",
            "src/core",
            "src/monitoring",
            "src/interface",
            
            # 源代码 - 工具
            "src/utils",
            
            # 测试 - 单元测试
            "tests/unit/chapter_1",
            "tests/unit/chapter_2",
            "tests/unit/chapter_3",
            "tests/unit/chapter_4",
            "tests/unit/chapter_5",
            "tests/unit/chapter_6",
            "tests/unit/chapter_7",
            
            # 测试 - 集成测试
            "tests/integration/chapter_1",
            "tests/integration/chapter_2",
            "tests/integration/chapter_3",
            "tests/integration/chapter_4",
            "tests/integration/chapter_5",
            "tests/integration/chapter_6",
            "tests/integration/chapter_7",
            
            # 测试 - E2E测试
            "tests/e2e",
            
            # 测试 - 性能测试
            "tests/performance",
            
            # 数据目录（D盘）
            "data/historical",
            "data/tick",
            "data/bar",
            "data/radar_archive",
            "data/exported_factors",
            "data/z2h_capsules",
            "data/z2h_meta_capsules",
            "data/backups",
            
            # 模型目录
            "models/qwen-30b",
            "models/algo_hunter",
            "models/checkpoints",
            
            # 日志目录（D盘）
            "logs/audit",
            "logs/trading",
            "logs/evolution",
            "logs/system",
            
            # 文档目录
            "docs/_build",
            "docs/api",
            "docs/guides",
            
            # Docker配置
            "docker",
        ]
        
        for directory in directories:
            path = self.base_path / directory
            if not path.exists():
                path.mkdir(parents=True, exist_ok=True)
                self.created_dirs.append(directory)
                print(f"  ✅ {directory}")
            else:
                print(f"  ⏭️  {directory} (已存在)")
        
        print()
    
    def _create_init_files(self):
        """创建__init__.py文件"""
        print("📄 创建__init__.py文件...")
        print()
        
        # 需要__init__.py的目录
        init_dirs = [
            # src目录
            "src",
            "src/scheduler",
            "src/brain",
            "src/brain/analyzers",
            "src/infra",
            "src/evolution",
            "src/execution",
            "src/strategies",
            "src/strategies/meta_momentum",
            "src/strategies/meta_mean_reversion",
            "src/strategies/meta_following",
            "src/strategies/meta_arbitrage",
            "src/strategies/meta_event",
            "src/config",
            "src/core",
            "src/monitoring",
            "src/interface",
            "src/utils",
            
            # tests目录
            "tests",
            "tests/unit",
            "tests/unit/chapter_1",
            "tests/unit/chapter_2",
            "tests/unit/chapter_3",
            "tests/unit/chapter_4",
            "tests/unit/chapter_5",
            "tests/unit/chapter_6",
            "tests/unit/chapter_7",
            "tests/integration",
            "tests/integration/chapter_1",
            "tests/integration/chapter_2",
            "tests/integration/chapter_3",
            "tests/integration/chapter_4",
            "tests/integration/chapter_5",
            "tests/integration/chapter_6",
            "tests/integration/chapter_7",
            "tests/e2e",
            "tests/performance",
        ]
        
        for directory in init_dirs:
            init_file = self.base_path / directory / "__init__.py"
            if not init_file.exists():
                init_file.touch()
                self.created_files.append(str(init_file))
                print(f"  ✅ {directory}/__init__.py")
            else:
                print(f"  ⏭️  {directory}/__init__.py (已存在)")
        
        print()
    
    def _create_gitkeep_files(self):
        """创建.gitkeep文件"""
        print("📌 创建.gitkeep文件...")
        print()
        
        # 需要.gitkeep的目录（空目录）
        gitkeep_dirs = [
            "data/historical",
            "data/tick",
            "data/bar",
            "data/radar_archive",
            "data/exported_factors",
            "data/z2h_capsules",
            "data/z2h_meta_capsules",
            "data/backups",
            "models/qwen-30b",
            "models/algo_hunter",
            "models/checkpoints",
            "logs/audit",
            "logs/trading",
            "logs/evolution",
            "logs/system",
        ]
        
        for directory in gitkeep_dirs:
            gitkeep_file = self.base_path / directory / ".gitkeep"
            if not gitkeep_file.exists():
                gitkeep_file.touch()
                self.created_files.append(str(gitkeep_file))
                print(f"  ✅ {directory}/.gitkeep")
            else:
                print(f"  ⏭️  {directory}/.gitkeep (已存在)")
        
        print()
    
    def _print_summary(self):
        """输出总结"""
        print("=" * 60)
        print("创建总结")
        print("=" * 60)
        print(f"创建目录: {len(self.created_dirs)} 个")
        print(f"创建文件: {len(self.created_files)} 个")
        print()
        
        if self.created_dirs or self.created_files:
            print("✅ 项目目录结构创建完成！")
        else:
            print("ℹ️  所有目录和文件已存在，无需创建。")
        
        print()
        print("下一步:")
        print("  1. 查看项目结构: tree -L 3")
        print("  2. 开始开发: 参考 START_HERE.md")
        print("  3. 阅读白皮书: cat 00_核心文档/mia.md")


def main():
    """主函数"""
    setup = ProjectStructureSetup()
    setup.create_all()


if __name__ == "__main__":
    main()
