"""
算法进化哨兵模块测试

测试目标: src/evolution/algorithm_evolution_sentinel.py
覆盖率目标: 100%
测试策略: 测试重新导出功能和模块接口
"""

import pytest

from src.evolution.algorithm_evolution_sentinel import (
    Algorithm,
    AlgorithmEvolutionSentinel,
    Paper,
)


class TestAlgorithmEvolutionSentinelModule:
    """测试算法进化哨兵模块"""

    def test_algorithm_evolution_sentinel_import(self):
        """测试AlgorithmEvolutionSentinel类导入"""
        assert AlgorithmEvolutionSentinel is not None
        assert hasattr(AlgorithmEvolutionSentinel, "__name__")
        assert "AlgoEvolutionSentinel" in AlgorithmEvolutionSentinel.__name__

    def test_paper_import(self):
        """测试Paper类导入"""
        assert Paper is not None
        assert hasattr(Paper, "__name__")
        assert "Paper" in Paper.__name__

    def test_algorithm_import(self):
        """测试Algorithm类导入"""
        assert Algorithm is not None
        assert hasattr(Algorithm, "__name__")
        assert "Algorithm" in Algorithm.__name__

    def test_module_all_exports(self):
        """测试模块__all__导出"""
        # pylint: disable=import-outside-toplevel
        from src.evolution import algorithm_evolution_sentinel

        expected_exports = ["AlgorithmEvolutionSentinel", "Paper", "Algorithm"]
        assert hasattr(algorithm_evolution_sentinel, "__all__")
        assert algorithm_evolution_sentinel.__all__ == expected_exports

    def test_re_export_functionality(self):
        """测试重新导出功能"""
        # 验证重新导出的类与原始类是同一个
        # pylint: disable=import-outside-toplevel
        from src.brain.algo_evolution.algo_evolution_sentinel import AlgoEvolutionSentinel as OriginalSentinel
        from src.brain.algo_evolution.algo_evolution_sentinel import Algorithm as OriginalAlgorithm
        from src.brain.algo_evolution.algo_evolution_sentinel import Paper as OriginalPaper

        assert AlgorithmEvolutionSentinel is OriginalSentinel
        assert Algorithm is OriginalAlgorithm
        assert Paper is OriginalPaper

    def test_module_docstring(self):
        """测试模块文档字符串"""
        # pylint: disable=import-outside-toplevel
        from src.evolution import algorithm_evolution_sentinel

        assert algorithm_evolution_sentinel.__doc__ is not None
        assert "Algorithm Evolution Sentinel" in algorithm_evolution_sentinel.__doc__
        assert "第十一章 11.2 算法进化哨兵" in algorithm_evolution_sentinel.__doc__

    def test_class_instantiation(self):
        """测试类实例化"""
        # 测试可以创建实例（不执行具体功能，只测试导入正确性）
        try:
            # 只测试类是否可以被引用，不实际实例化以避免依赖问题
            assert callable(AlgorithmEvolutionSentinel)
            assert callable(Paper)
            assert callable(Algorithm)
        except ImportError as e:
            pytest.fail(f"类引用失败: {e}")

    def test_module_structure(self):
        """测试模块结构"""
        # pylint: disable=import-outside-toplevel
        from src.evolution import algorithm_evolution_sentinel

        # 验证模块包含预期的属性
        expected_attributes = ["AlgorithmEvolutionSentinel", "Paper", "Algorithm", "__all__"]

        for attr in expected_attributes:
            assert hasattr(algorithm_evolution_sentinel, attr), f"缺少属性: {attr}"

    def test_import_path_consistency(self):
        """测试导入路径一致性"""
        # 验证从不同路径导入的是同一个对象
        # pylint: disable=import-outside-toplevel
        from src.brain.algo_evolution.algo_evolution_sentinel import AlgoEvolutionSentinel as OriginalSentinel

        assert AlgorithmEvolutionSentinel is OriginalSentinel, "导入路径不一致"

    def test_module_metadata(self):
        """测试模块元数据"""
        # pylint: disable=import-outside-toplevel
        from src.evolution import algorithm_evolution_sentinel

        # 验证模块有正确的文件路径
        assert hasattr(algorithm_evolution_sentinel, "__file__")
        assert "algorithm_evolution_sentinel.py" in algorithm_evolution_sentinel.__file__

        # 验证模块名称
        assert algorithm_evolution_sentinel.__name__ == "src.evolution.algorithm_evolution_sentinel"
