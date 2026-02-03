#!/usr/bin/env python3
"""
MIA系统全量对齐检查脚本
检查所有文件的版本号、内容、逻辑、标准、要求是否一致
"""

import re
from pathlib import Path
from typing import Dict, List, Tuple

class AlignmentChecker:
    def __init__(self):
        self.root = Path(".")
        self.issues = []
        self.warnings = []
        self.info = []
        
    def check_version_consistency(self):
        """检查版本号一致性"""
        print("\n" + "="*80)
        print("1. 检查版本号一致性")
        print("="*80)
        
        version_files = {
            "00_核心文档/mia.md": None,
            "00_核心文档/IMPLEMENTATION_CHECKLIST.md": None,
            "00_核心文档/PROJECT_STRUCTURE.md": None,
            "00_核心文档/DOCUMENTATION_SUMMARY.md": None,
            "00_核心文档/DOCUMENTATION_COMPLETION_REPORT.md": None,
        }
        
        # 提取版本号
        for file_path in version_files.keys():
            try:
                content = (self.root / file_path).read_text(encoding='utf-8')
                
                # 查找版本号
                version_patterns = [
                    r'版本[：:]\s*v?(\d+\.\d+(?:\.\d+)?)',
                    r'version[：:]\s*v?(\d+\.\d+(?:\.\d+)?)',
                    r'文档版本号[：:]\s*v?(\d+\.\d+(?:\.\d+)?)',
                    r'\*\*版本\*\*[：:]\s*v?(\d+\.\d+(?:\.\d+)?)',
                ]
                
                for pattern in version_patterns:
                    match = re.search(pattern, content, re.IGNORECASE)
                    if match:
                        version_files[file_path] = match.group(1)
                        break
                        
            except Exception as e:
                self.issues.append(f"❌ 无法读取文件 {file_path}: {e}")
        
        # 检查一致性
        versions = [v for v in version_files.values() if v]
        if len(set(versions)) > 1:
            self.warnings.append(f"⚠️  版本号不一致:")
            for file, version in version_files.items():
                self.warnings.append(f"   - {file}: v{version}")
        else:
            self.info.append(f"✅ 版本号一致: v{versions[0] if versions else 'unknown'}")
            
        # 显示结果
        for file, version in version_files.items():
            if version:
                print(f"  ✓ {file}: v{version}")
            else:
                print(f"  ✗ {file}: 未找到版本号")
    
    def check_chapter_coverage(self):
        """检查章节覆盖一致性"""
        print("\n" + "="*80)
        print("2. 检查章节覆盖一致性")
        print("="*80)
        
        # 白皮书章节
        whitepaper = self.root / "00_核心文档/mia.md"
        whitepaper_content = whitepaper.read_text(encoding='utf-8')
        
        # 提取白皮书章节
        whitepaper_chapters = set()
        chapter_pattern = r'第([一二三四五六七八九十]+)章[：:]'
        for match in re.finditer(chapter_pattern, whitepaper_content):
            whitepaper_chapters.add(match.group(1))
        
        # 转换中文数字
        chinese_to_num = {
            '一': 1, '二': 2, '三': 3, '四': 4, '五': 5,
            '六': 6, '七': 7, '八': 8, '九': 9, '十': 10,
            '十一': 11, '十二': 12, '十三': 13, '十四': 14, '十五': 15,
            '十六': 16, '十七': 17, '十八': 18, '十九': 19
        }
        
        whitepaper_chapter_nums = sorted([chinese_to_num.get(ch, 0) for ch in whitepaper_chapters])
        
        print(f"  白皮书章节: {len(whitepaper_chapter_nums)}章")
        print(f"  章节范围: 第{min(whitepaper_chapter_nums)}-{max(whitepaper_chapter_nums)}章")
        
        # 检查实现检查清单
        checklist = self.root / "00_核心文档/IMPLEMENTATION_CHECKLIST.md"
        checklist_content = checklist.read_text(encoding='utf-8')
        
        checklist_chapters = set()
        for match in re.finditer(r'第([一二三四五六七八九十]+)章', checklist_content):
            checklist_chapters.add(match.group(1))
        
        checklist_chapter_nums = sorted([chinese_to_num.get(ch, 0) for ch in checklist_chapters])
        
        print(f"  检查清单章节: {len(checklist_chapter_nums)}章")
        print(f"  章节范围: 第{min(checklist_chapter_nums)}-{max(checklist_chapter_nums)}章")
        
        # 对比
        if whitepaper_chapter_nums == checklist_chapter_nums:
            self.info.append(f"✅ 章节覆盖一致: {len(whitepaper_chapter_nums)}章")
        else:
            missing_in_checklist = set(whitepaper_chapter_nums) - set(checklist_chapter_nums)
            extra_in_checklist = set(checklist_chapter_nums) - set(whitepaper_chapter_nums)
            
            if missing_in_checklist:
                self.issues.append(f"❌ 检查清单缺失章节: {missing_in_checklist}")
            if extra_in_checklist:
                self.warnings.append(f"⚠️  检查清单多余章节: {extra_in_checklist}")
    
    def check_test_requirements(self):
        """检查测试要求一致性"""
        print("\n" + "="*80)
        print("3. 检查测试要求一致性")
        print("="*80)
        
        # 标准测试要求
        standard_requirements = {
            "单元测试覆盖率": "≥ 85%",
            "集成测试覆盖率": "≥ 75%",
            "Pylint评分": "≥ 8.0/10",
            "圈复杂度": "≤ 10",
            "代码重复率": "< 5%",
        }
        
        files_to_check = [
            "00_核心文档/IMPLEMENTATION_CHECKLIST.md",
            "00_核心文档/DEVELOPMENT_GUIDE.md",
            "00_核心文档/TESTING_STRATEGY.md",
        ]
        
        inconsistencies = []
        
        for file_path in files_to_check:
            try:
                content = (self.root / file_path).read_text(encoding='utf-8')
                
                for req_name, req_value in standard_requirements.items():
                    # 查找要求
                    pattern = rf'{req_name}[：:]\s*([≥>=<≤]+\s*[\d.]+%?(?:/\d+)?)'
                    match = re.search(pattern, content)
                    
                    if match:
                        found_value = match.group(1).strip()
                        # 标准化比较
                        found_value_normalized = found_value.replace('≥', '>=').replace('≤', '<=')
                        req_value_normalized = req_value.replace('≥', '>=').replace('≤', '<=')
                        
                        if found_value_normalized != req_value_normalized:
                            inconsistencies.append(
                                f"  {file_path}: {req_name} = {found_value} (标准: {req_value})"
                            )
            except Exception as e:
                self.warnings.append(f"⚠️  无法检查 {file_path}: {e}")
        
        if inconsistencies:
            self.warnings.append("⚠️  测试要求不一致:")
            self.warnings.extend(inconsistencies)
        else:
            self.info.append("✅ 测试要求一致")
            for req_name, req_value in standard_requirements.items():
                print(f"  ✓ {req_name}: {req_value}")
    
    def check_strategy_count(self):
        """检查策略数量一致性"""
        print("\n" + "="*80)
        print("4. 检查策略数量一致性")
        print("="*80)
        
        # 白皮书中的策略定义（更精确的模式）
        whitepaper = self.root / "00_核心文档/mia.md"
        whitepaper_content = whitepaper.read_text(encoding='utf-8')
        
        # 查找策略定义：S## 后面跟着策略名称
        strategy_pattern = r'S(\d{2})\s+\w+.*?\('
        strategies = set(re.findall(strategy_pattern, whitepaper_content))
        
        print(f"  白皮书中定义的策略: {len(strategies)}个")
        print(f"  策略编号: {sorted(strategies)}")
        
        # 检查项目结构
        project_structure = self.root / "00_核心文档/PROJECT_STRUCTURE.md"
        structure_content = project_structure.read_text(encoding='utf-8')
        
        # 查找策略文件定义
        structure_pattern = r'S(\d{2})_\w+\.py'
        structure_strategies = set(re.findall(structure_pattern, structure_content))
        
        print(f"  项目结构中的策略: {len(structure_strategies)}个")
        print(f"  策略编号: {sorted(structure_strategies)}")
        
        # 对比
        if strategies == structure_strategies:
            self.info.append(f"✅ 策略数量一致: {len(strategies)}个")
        else:
            missing = strategies - structure_strategies
            extra = structure_strategies - strategies
            
            if missing:
                self.issues.append(f"❌ 项目结构缺失策略: {sorted(missing)}")
            if extra:
                self.warnings.append(f"⚠️  项目结构多余策略: {sorted(extra)}")
    
    def check_performance_metrics(self):
        """检查性能指标一致性"""
        print("\n" + "="*80)
        print("5. 检查性能指标一致性")
        print("="*80)
        
        # 标准性能指标
        standard_metrics = {
            "本地推理延迟": "< 20ms (P99)",
            "热备切换延迟": "< 200ms",
            "SPSC延迟": "< 100μs",
        }
        
        files_to_check = [
            "00_核心文档/mia.md",
            "00_核心文档/IMPLEMENTATION_CHECKLIST.md",
            "00_核心文档/DEVELOPMENT_GUIDE.md",
        ]
        
        inconsistencies = []
        
        for file_path in files_to_check:
            try:
                content = (self.root / file_path).read_text(encoding='utf-8')
                
                for metric_name, metric_value in standard_metrics.items():
                    # 简化的模式匹配
                    if metric_name in content:
                        # 查找附近的数值
                        pattern = rf'{metric_name}[：:：\s]*([<>≤≥]+\s*\d+\s*[μm]?s.*?)(?:\n|$|[，。])'
                        match = re.search(pattern, content)
                        
                        if match:
                            found_value = match.group(1).strip()
                            if metric_value not in found_value and found_value not in metric_value:
                                inconsistencies.append(
                                    f"  {file_path}: {metric_name} = {found_value} (标准: {metric_value})"
                                )
            except Exception as e:
                self.warnings.append(f"⚠️  无法检查 {file_path}: {e}")
        
        if inconsistencies:
            self.warnings.append("⚠️  性能指标不一致:")
            self.warnings.extend(inconsistencies)
        else:
            self.info.append("✅ 性能指标一致")
            for metric_name, metric_value in standard_metrics.items():
                print(f"  ✓ {metric_name}: {metric_value}")
    
    def check_file_references(self):
        """检查文件引用一致性"""
        print("\n" + "="*80)
        print("6. 检查文件引用一致性")
        print("="*80)
        
        # 检查README中引用的文件是否存在
        readme = self.root / "00_核心文档/README.md"
        if readme.exists():
            content = readme.read_text(encoding='utf-8')
            
            # 查找.md文件引用
            md_refs = re.findall(r'([A-Z_]+\.md)', content)
            
            missing_files = []
            for ref in set(md_refs):
                file_path = self.root / "00_核心文档" / ref
                if not file_path.exists():
                    missing_files.append(ref)
            
            if missing_files:
                self.issues.append(f"❌ README引用的文件不存在: {missing_files}")
            else:
                self.info.append("✅ README文件引用完整")
                print(f"  ✓ 检查了 {len(set(md_refs))} 个文件引用")
    
    def generate_report(self):
        """生成对齐检查报告"""
        print("\n" + "="*80)
        print("对齐检查报告")
        print("="*80)
        
        # 统计
        total_checks = len(self.info) + len(self.warnings) + len(self.issues)
        
        print(f"\n总检查项: {total_checks}")
        print(f"  ✅ 通过: {len(self.info)}")
        print(f"  ⚠️  警告: {len(self.warnings)}")
        print(f"  ❌ 错误: {len(self.issues)}")
        
        # 详细信息
        if self.info:
            print("\n✅ 通过的检查:")
            for item in self.info:
                print(f"  {item}")
        
        if self.warnings:
            print("\n⚠️  警告:")
            for item in self.warnings:
                print(f"  {item}")
        
        if self.issues:
            print("\n❌ 错误:")
            for item in self.issues:
                print(f"  {item}")
        
        # 总体评分
        if not self.issues:
            if not self.warnings:
                print("\n🎉 完美对齐！所有检查通过。")
                return 100
            else:
                print(f"\n✅ 基本对齐，但有 {len(self.warnings)} 个警告需要注意。")
                return 90
        else:
            print(f"\n⚠️  发现 {len(self.issues)} 个错误，需要修复。")
            return 70
    
    def run(self):
        """运行所有检查"""
        print("MIA系统全量对齐检查")
        print("="*80)
        
        self.check_version_consistency()
        self.check_chapter_coverage()
        self.check_test_requirements()
        self.check_strategy_count()
        self.check_performance_metrics()
        self.check_file_references()
        
        score = self.generate_report()
        
        return score

if __name__ == "__main__":
    checker = AlignmentChecker()
    score = checker.run()
    
    print(f"\n对齐评分: {score}/100")
    
    if score < 100:
        print("\n建议: 运行 'python scripts/fix_alignment.py' 自动修复问题")
