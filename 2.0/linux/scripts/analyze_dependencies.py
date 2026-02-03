"""依赖分析工具

白皮书依据: 第四章 4.8 循环依赖检测
任务依据: Task 16.5 运行依赖分析工具

功能:
1. 检测Python模块之间的循环依赖
2. 生成依赖关系图
3. 验证vLLM集成无循环依赖
4. 输出分析报告
"""

import ast
import os
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple
from collections import defaultdict
import json


class DependencyAnalyzer:
    """依赖分析器
    
    分析Python项目中的模块依赖关系，检测循环依赖。
    """
    
    def __init__(self, project_root: str):
        """初始化依赖分析器
        
        Args:
            project_root: 项目根目录路径
        """
        self.project_root = Path(project_root)
        self.src_root = self.project_root / "src"
        
        # 依赖关系图: module -> [imported_modules]
        self.dependencies: Dict[str, Set[str]] = defaultdict(set)
        
        # 循环依赖列表
        self.circular_dependencies: List[List[str]] = []
        
        # 分析统计
        self.stats = {
            "total_modules": 0,
            "total_imports": 0,
            "circular_count": 0,
            "max_depth": 0
        }
    
    def analyze(self) -> None:
        """分析项目依赖关系"""
        print(f"🔍 开始分析项目依赖关系...")
        print(f"📁 项目根目录: {self.project_root}")
        print(f"📦 源代码目录: {self.src_root}")
        print()
        
        # 扫描所有Python文件
        python_files = list(self.src_root.rglob("*.py"))
        self.stats["total_modules"] = len(python_files)
        
        print(f"📊 找到 {len(python_files)} 个Python模块")
        print()
        
        # 分析每个文件的导入
        for py_file in python_files:
            self._analyze_file(py_file)
        
        # 检测循环依赖
        self._detect_circular_dependencies()
        
        # 计算统计信息
        self._calculate_stats()
    
    def _analyze_file(self, file_path: Path) -> None:
        """分析单个文件的导入关系
        
        Args:
            file_path: Python文件路径
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 解析AST
            tree = ast.parse(content, filename=str(file_path))
            
            # 获取模块名
            module_name = self._get_module_name(file_path)
            
            # 提取导入语句
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imported = alias.name
                        if self._is_project_module(imported):
                            self.dependencies[module_name].add(imported)
                            self.stats["total_imports"] += 1
                
                elif isinstance(node, ast.ImportFrom):
                    if node.module and self._is_project_module(node.module):
                        self.dependencies[module_name].add(node.module)
                        self.stats["total_imports"] += 1
        
        except Exception as e:
            print(f"⚠️  解析文件失败: {file_path.name} - {e}")
    
    def _get_module_name(self, file_path: Path) -> str:
        """获取模块名
        
        Args:
            file_path: 文件路径
            
        Returns:
            模块名 (如 'src.brain.soldier_engine_v2')
        """
        relative_path = file_path.relative_to(self.project_root)
        module_parts = list(relative_path.parts[:-1]) + [relative_path.stem]
        
        # 移除 __init__
        if module_parts[-1] == "__init__":
            module_parts = module_parts[:-1]
        
        return ".".join(module_parts)
    
    def _is_project_module(self, module_name: str) -> bool:
        """判断是否是项目内部模块
        
        Args:
            module_name: 模块名
            
        Returns:
            是否是项目模块
        """
        return module_name.startswith("src.")
    
    def _detect_circular_dependencies(self) -> None:
        """检测循环依赖"""
        print("🔄 检测循环依赖...")
        
        visited = set()
        rec_stack = set()
        
        def dfs(module: str, path: List[str]) -> None:
            """深度优先搜索检测循环
            
            Args:
                module: 当前模块
                path: 当前路径
            """
            visited.add(module)
            rec_stack.add(module)
            path.append(module)
            
            for dep in self.dependencies.get(module, []):
                if dep not in visited:
                    dfs(dep, path.copy())
                elif dep in rec_stack:
                    # 找到循环依赖
                    cycle_start = path.index(dep)
                    cycle = path[cycle_start:] + [dep]
                    
                    # 检查是否已记录（避免重复）
                    if not self._is_duplicate_cycle(cycle):
                        self.circular_dependencies.append(cycle)
            
            rec_stack.remove(module)
        
        # 对每个模块执行DFS
        for module in self.dependencies.keys():
            if module not in visited:
                dfs(module, [])
        
        self.stats["circular_count"] = len(self.circular_dependencies)
    
    def _is_duplicate_cycle(self, cycle: List[str]) -> bool:
        """检查循环是否已存在
        
        Args:
            cycle: 循环路径
            
        Returns:
            是否重复
        """
        cycle_set = set(cycle)
        for existing_cycle in self.circular_dependencies:
            if set(existing_cycle) == cycle_set:
                return True
        return False
    
    def _calculate_stats(self) -> None:
        """计算统计信息"""
        # 计算最大依赖深度
        def get_depth(module: str, visited: Set[str]) -> int:
            if module in visited:
                return 0
            visited.add(module)
            
            max_child_depth = 0
            for dep in self.dependencies.get(module, []):
                depth = get_depth(dep, visited.copy())
                max_child_depth = max(max_child_depth, depth)
            
            return max_child_depth + 1
        
        for module in self.dependencies.keys():
            depth = get_depth(module, set())
            self.stats["max_depth"] = max(self.stats["max_depth"], depth)
    
    def print_report(self) -> None:
        """打印分析报告"""
        print()
        print("=" * 80)
        print("📊 依赖分析报告")
        print("=" * 80)
        print()
        
        # 统计信息
        print("📈 统计信息:")
        print(f"  - 总模块数: {self.stats['total_modules']}")
        print(f"  - 总导入数: {self.stats['total_imports']}")
        print(f"  - 循环依赖数: {self.stats['circular_count']}")
        print(f"  - 最大依赖深度: {self.stats['max_depth']}")
        print()
        
        # 循环依赖详情
        if self.circular_dependencies:
            print("❌ 发现循环依赖:")
            print()
            for i, cycle in enumerate(self.circular_dependencies, 1):
                print(f"  循环 {i}:")
                for j, module in enumerate(cycle):
                    if j < len(cycle) - 1:
                        print(f"    {module}")
                        print(f"      ↓")
                    else:
                        print(f"    {module} (回到起点)")
                print()
        else:
            print("✅ 未发现循环依赖")
            print()
        
        # 关键模块分析
        print("🔑 关键模块 (被导入次数最多):")
        import_counts = defaultdict(int)
        for deps in self.dependencies.values():
            for dep in deps:
                import_counts[dep] += 1
        
        top_modules = sorted(import_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        for module, count in top_modules:
            print(f"  - {module}: {count} 次")
        print()
        
        # vLLM集成检查
        print("🚀 vLLM集成检查:")
        vllm_modules = [
            "src.brain.vllm_inference_engine",
            "src.brain.vllm_memory_coordinator",
            "src.brain.adaptive_batch_scheduler"
        ]
        
        vllm_has_circular = False
        for cycle in self.circular_dependencies:
            for vllm_module in vllm_modules:
                if vllm_module in cycle:
                    print(f"  ❌ {vllm_module} 存在循环依赖")
                    vllm_has_circular = True
                    break
        
        if not vllm_has_circular:
            print("  ✅ vLLM集成无循环依赖")
        print()
        
        # 总结
        print("=" * 80)
        if self.circular_dependencies:
            print("❌ 分析完成 - 发现问题，需要修复循环依赖")
        else:
            print("✅ 分析完成 - 依赖关系健康")
        print("=" * 80)
    
    def generate_graph(self, output_file: str = "dependency_graph.json") -> None:
        """生成依赖关系图
        
        Args:
            output_file: 输出文件路径
        """
        graph_data = {
            "nodes": [],
            "edges": [],
            "stats": self.stats,
            "circular_dependencies": self.circular_dependencies
        }
        
        # 添加节点
        all_modules = set(self.dependencies.keys())
        for deps in self.dependencies.values():
            all_modules.update(deps)
        
        for module in all_modules:
            graph_data["nodes"].append({
                "id": module,
                "label": module.split(".")[-1]
            })
        
        # 添加边
        for source, targets in self.dependencies.items():
            for target in targets:
                graph_data["edges"].append({
                    "source": source,
                    "target": target
                })
        
        # 保存到文件
        output_path = self.project_root / output_file
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(graph_data, f, indent=2, ensure_ascii=False)
        
        print(f"📊 依赖关系图已保存到: {output_path}")


def main():
    """主函数"""
    # 获取项目根目录
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    
    # 创建分析器
    analyzer = DependencyAnalyzer(str(project_root))
    
    # 执行分析
    analyzer.analyze()
    
    # 打印报告
    analyzer.print_report()
    
    # 生成依赖图
    analyzer.generate_graph()
    
    # 返回退出码
    if analyzer.circular_dependencies:
        sys.exit(1)  # 有循环依赖，返回错误码
    else:
        sys.exit(0)  # 无循环依赖，返回成功码


if __name__ == "__main__":
    main()
