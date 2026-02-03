#!/usr/bin/env python
"""
依赖关系检查器

功能:
1. 检测循环依赖
2. 分析模块依赖关系
3. 生成依赖图
4. 识别紧耦合模块
"""

import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple
import json
from datetime import datetime


class DependencyChecker:
    """依赖关系检查器"""
    
    def __init__(self, src_dir: str = "src"):
        """初始化检查器
        
        Args:
            src_dir: 源代码目录
        """
        self.project_root = Path.cwd()
        self.src_dir = self.project_root / src_dir
        self.reports_dir = self.project_root / "reports"
        self.reports_dir.mkdir(exist_ok=True)
        
        # 依赖图: module -> [imported_modules]
        self.dependency_graph: Dict[str, List[str]] = {}
        
        # 反向依赖图: module -> [modules_that_import_it]
        self.reverse_graph: Dict[str, List[str]] = {}
        
    def analyze(self) -> Dict[str, any]:
        """分析依赖关系
        
        Returns:
            Dict[str, any]: 分析结果
        """
        print("=" * 60)
        print("🔍 依赖关系分析")
        print("=" * 60)
        
        # 构建依赖图
        self._build_dependency_graph()
        
        print(f"总模块数: {len(self.dependency_graph)}")
        
        # 检测循环依赖
        circular_deps = self._detect_circular_dependencies()
        
        if circular_deps:
            print(f"\n⚠️  发现 {len(circular_deps)} 个循环依赖:")
            print("-" * 60)
            for i, (mod1, mod2) in enumerate(circular_deps[:10], 1):
                print(f"{i}. {mod1} <-> {mod2}")
        else:
            print("\n✅ 未发现循环依赖")
        
        # 分析模块耦合度
        coupling_analysis = self._analyze_coupling()
        
        if coupling_analysis['high_coupling']:
            print(f"\n⚠️  发现 {len(coupling_analysis['high_coupling'])} 个高耦合模块:")
            print("-" * 60)
            for i, (module, count) in enumerate(coupling_analysis['high_coupling'][:10], 1):
                print(f"{i}. {module}: {count} 个依赖")
        else:
            print("\n✅ 未发现高耦合模块")
        
        # 识别核心模块
        core_modules = self._identify_core_modules()
        
        if core_modules:
            print(f"\n📌 核心模块 (被多个模块依赖):")
            print("-" * 60)
            for i, (module, count) in enumerate(core_modules[:10], 1):
                print(f"{i}. {module}: 被 {count} 个模块依赖")
        
        # 生成报告
        report_data = {
            'timestamp': datetime.now().isoformat(),
            'total_modules': len(self.dependency_graph),
            'circular_dependencies': [
                {'module1': m1, 'module2': m2} for m1, m2 in circular_deps
            ],
            'high_coupling_modules': [
                {'module': m, 'dependency_count': c} 
                for m, c in coupling_analysis['high_coupling']
            ],
            'core_modules': [
                {'module': m, 'dependent_count': c}
                for m, c in core_modules
            ]
        }
        
        report_file = self.reports_dir / f"dependency_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)
        
        print(f"\n📄 详细报告已保存: {report_file}")
        
        return report_data
    
    def _build_dependency_graph(self):
        """构建依赖图"""
        if not self.src_dir.exists():
            print(f"❌ 源代码目录不存在: {self.src_dir}")
            return
        
        for py_file in self.src_dir.rglob("*.py"):
            if py_file.name == "__init__.py":
                continue
            
            try:
                content = py_file.read_text(encoding='utf-8', errors='ignore')
                module_name = str(py_file.relative_to(self.src_dir)).replace('/', '.').replace('\\', '.')[:-3]
                
                imports = []
                for line in content.split('\n'):
                    line = line.strip()
                    
                    # 解析 from src.xxx import yyy
                    if line.startswith('from src.'):
                        parts = line.split()
                        if len(parts) >= 2:
                            imported = parts[1].replace('src.', '').split('.')[0]
                            if imported and imported not in imports:
                                imports.append(imported)
                    
                    # 解析 import src.xxx
                    elif line.startswith('import src.'):
                        parts = line.split()
                        if len(parts) >= 2:
                            imported = parts[1].replace('src.', '').split('.')[0]
                            if imported and imported not in imports:
                                imports.append(imported)
                
                self.dependency_graph[module_name] = imports
                
                # 构建反向图
                for imported in imports:
                    if imported not in self.reverse_graph:
                        self.reverse_graph[imported] = []
                    if module_name not in self.reverse_graph[imported]:
                        self.reverse_graph[imported].append(module_name)
                
            except Exception as e:
                print(f"⚠️  解析文件失败: {py_file} - {e}")
    
    def _detect_circular_dependencies(self) -> List[Tuple[str, str]]:
        """检测循环依赖
        
        Returns:
            List[Tuple[str, str]]: 循环依赖对列表
        """
        circular_deps = []
        checked = set()
        
        for module, imports in self.dependency_graph.items():
            for imported in imports:
                # 避免重复检查
                pair = tuple(sorted([module, imported]))
                if pair in checked:
                    continue
                checked.add(pair)
                
                # 检查是否存在反向依赖
                if imported in self.dependency_graph:
                    if module in self.dependency_graph[imported]:
                        circular_deps.append((module, imported))
        
        return circular_deps
    
    def _analyze_coupling(self) -> Dict[str, List[Tuple[str, int]]]:
        """分析模块耦合度
        
        Returns:
            Dict[str, List[Tuple[str, int]]]: 耦合度分析结果
        """
        # 计算每个模块的依赖数量
        coupling_scores = []
        
        for module, imports in self.dependency_graph.items():
            dependency_count = len(imports)
            if dependency_count > 0:
                coupling_scores.append((module, dependency_count))
        
        # 按依赖数量排序
        coupling_scores.sort(key=lambda x: x[1], reverse=True)
        
        # 识别高耦合模块（依赖数量 > 5）
        high_coupling = [(m, c) for m, c in coupling_scores if c > 5]
        
        return {
            'all_modules': coupling_scores,
            'high_coupling': high_coupling
        }
    
    def _identify_core_modules(self) -> List[Tuple[str, int]]:
        """识别核心模块
        
        Returns:
            List[Tuple[str, int]]: 核心模块列表 (模块名, 被依赖次数)
        """
        core_modules = []
        
        for module, dependents in self.reverse_graph.items():
            dependent_count = len(dependents)
            if dependent_count > 0:
                core_modules.append((module, dependent_count))
        
        # 按被依赖次数排序
        core_modules.sort(key=lambda x: x[1], reverse=True)
        
        return core_modules
    
    def visualize_dependencies(self, output_file: str = None):
        """可视化依赖关系（生成DOT格式）
        
        Args:
            output_file: 输出文件路径
        """
        if output_file is None:
            output_file = str(self.reports_dir / f"dependency_graph_{datetime.now().strftime('%Y%m%d_%H%M%S')}.dot")
        
        dot_content = ["digraph Dependencies {"]
        dot_content.append("  rankdir=LR;")
        dot_content.append("  node [shape=box];")
        
        for module, imports in self.dependency_graph.items():
            for imported in imports:
                dot_content.append(f'  "{module}" -> "{imported}";')
        
        dot_content.append("}")
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(dot_content))
        
        print(f"\n📊 依赖图已生成: {output_file}")
        print("可使用 Graphviz 可视化: dot -Tpng dependency_graph.dot -o dependency_graph.png")


def main():
    """主函数"""
    src_dir = sys.argv[1] if len(sys.argv) > 1 else "src"
    
    checker = DependencyChecker(src_dir)
    result = checker.analyze()
    
    # 生成可视化
    if '--visualize' in sys.argv:
        checker.visualize_dependencies()
    
    # 如果发现循环依赖，返回非0退出码
    if result.get('circular_dependencies'):
        sys.exit(1)


if __name__ == "__main__":
    main()
