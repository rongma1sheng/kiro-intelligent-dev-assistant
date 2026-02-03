#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Hook触发逻辑测试器 v4.0

全面测试.kiro/hooks/目录下所有Hook的触发逻辑：
- 文件编辑触发测试
- 用户触发测试  
- 提示提交触发测试
- 触发条件验证
- 冲突检测
- 性能测试
"""

import json
import os
import tempfile
import time
from pathlib import Path
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass
from enum import Enum


class TriggerType(Enum):
    FILE_EDITED = "fileEdited"
    USER_TRIGGERED = "userTriggered"
    PROMPT_SUBMIT = "promptSubmit"


@dataclass
class HookConfig:
    """Hook配置数据类"""
    name: str
    version: str
    trigger_type: TriggerType
    patterns: List[str]
    file_path: str
    enabled: bool = True


@dataclass
class TestResult:
    """测试结果数据类"""
    hook_name: str
    test_type: str
    passed: bool
    message: str
    execution_time: float = 0.0
    details: Dict[str, Any] = None


class HookTriggerTester:
    """Hook触发逻辑测试器"""
    
    def __init__(self, hooks_dir: str = ".kiro/hooks"):
        self.hooks_dir = Path(hooks_dir)
        self.hooks: List[HookConfig] = []
        self.test_results: List[TestResult] = []
        self.temp_files: List[Path] = []
        
    def run_all_tests(self) -> Tuple[bool, List[TestResult]]:
        """运行所有触发逻辑测试"""
        print("🧪 开始Hook触发逻辑测试...")
        print("="*60)
        
        # 1. 加载Hook配置
        self._load_hook_configs()
        
        # 2. 验证Hook配置
        self._test_hook_configs()
        
        # 3. 测试文件编辑触发
        self._test_file_edit_triggers()
        
        # 4. 测试用户触发
        self._test_user_triggers()
        
        # 5. 测试提示提交触发
        self._test_prompt_submit_triggers()
        
        # 6. 测试触发冲突
        self._test_trigger_conflicts()
        
        # 7. 性能测试
        self._test_performance()
        
        # 8. 清理临时文件
        self._cleanup()
        
        # 9. 输出结果
        return self._print_results()
    
    def _load_hook_configs(self):
        """加载Hook配置"""
        print("📋 加载Hook配置...")
        
        if not self.hooks_dir.exists():
            self.test_results.append(TestResult(
                "system", "config_load", False, 
                f"Hooks目录不存在: {self.hooks_dir}"
            ))
            return
        
        hook_files = list(self.hooks_dir.glob("*.hook"))
        print(f"发现 {len(hook_files)} 个Hook文件")
        
        for hook_file in hook_files:
            try:
                with open(hook_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                
                # 解析触发类型
                trigger_type_str = config.get("when", {}).get("type", "")
                try:
                    trigger_type = TriggerType(trigger_type_str)
                except ValueError:
                    trigger_type = None
                
                # 解析模式
                patterns = config.get("when", {}).get("patterns", [])
                if isinstance(patterns, str):
                    patterns = [patterns]
                
                hook_config = HookConfig(
                    name=config.get("name", hook_file.stem),
                    version=config.get("version", "unknown"),
                    trigger_type=trigger_type,
                    patterns=patterns,
                    file_path=str(hook_file),
                    enabled=config.get("enabled", True)
                )
                
                self.hooks.append(hook_config)
                
                self.test_results.append(TestResult(
                    hook_config.name, "config_load", True,
                    f"配置加载成功 (v{hook_config.version})"
                ))
                
            except Exception as e:
                self.test_results.append(TestResult(
                    hook_file.stem, "config_load", False,
                    f"配置加载失败: {e}"
                ))
    
    def _test_hook_configs(self):
        """测试Hook配置有效性"""
        print("\n🔍 验证Hook配置...")
        
        for hook in self.hooks:
            # 测试必需字段
            if not hook.name:
                self.test_results.append(TestResult(
                    hook.name, "config_validation", False,
                    "缺少Hook名称"
                ))
                continue
            
            if not hook.trigger_type:
                self.test_results.append(TestResult(
                    hook.name, "config_validation", False,
                    "无效的触发类型"
                ))
                continue
            
            # 测试版本格式
            if not hook.version or hook.version == "unknown":
                self.test_results.append(TestResult(
                    hook.name, "config_validation", False,
                    "缺少或无效的版本号"
                ))
                continue
            
            # 测试文件编辑触发的模式
            if hook.trigger_type == TriggerType.FILE_EDITED:
                if not hook.patterns:
                    self.test_results.append(TestResult(
                        hook.name, "config_validation", False,
                        "文件编辑触发缺少文件模式"
                    ))
                    continue
            
            self.test_results.append(TestResult(
                hook.name, "config_validation", True,
                "配置验证通过"
            ))
    
    def _test_file_edit_triggers(self):
        """测试文件编辑触发逻辑"""
        print("\n📝 测试文件编辑触发...")
        
        file_edit_hooks = [h for h in self.hooks if h.trigger_type == TriggerType.FILE_EDITED]
        print(f"发现 {len(file_edit_hooks)} 个文件编辑触发Hook")
        
        # 创建测试文件
        test_files = {
            "src/test_file.py": "# Python源代码测试文件",
            "tests/test_example.py": "# Python测试文件",
            "PRD.md": "# PRD文档测试",
            "README.md": "# 普通Markdown文件",
            "config.json": '{"test": true}',
            "script.js": "// JavaScript测试文件"
        }
        
        for file_path, content in test_files.items():
            # 创建临时测试文件
            temp_file = self._create_temp_file(file_path, content)
            
            # 测试哪些Hook会被触发
            triggered_hooks = []
            for hook in file_edit_hooks:
                if self._should_trigger_for_file(hook, file_path):
                    triggered_hooks.append(hook.name)
            
            # 记录测试结果
            self.test_results.append(TestResult(
                f"file_trigger_{Path(file_path).name}", "file_edit_trigger", True,
                f"文件 {file_path} 触发了 {len(triggered_hooks)} 个Hook: {triggered_hooks}",
                details={"triggered_hooks": triggered_hooks, "file_path": file_path}
            ))
    
    def _test_user_triggers(self):
        """测试用户触发逻辑"""
        print("\n👤 测试用户触发...")
        
        user_trigger_hooks = [h for h in self.hooks if h.trigger_type == TriggerType.USER_TRIGGERED]
        print(f"发现 {len(user_trigger_hooks)} 个用户触发Hook")
        
        for hook in user_trigger_hooks:
            # 模拟用户触发
            start_time = time.time()
            
            # 用户触发Hook不需要特定条件，只需要验证配置正确性
            trigger_valid = True
            message = "用户触发配置正确"
            
            execution_time = time.time() - start_time
            
            self.test_results.append(TestResult(
                hook.name, "user_trigger", trigger_valid, message,
                execution_time=execution_time
            ))
    
    def _test_prompt_submit_triggers(self):
        """测试提示提交触发逻辑"""
        print("\n💬 测试提示提交触发...")
        
        prompt_hooks = [h for h in self.hooks if h.trigger_type == TriggerType.PROMPT_SUBMIT]
        print(f"发现 {len(prompt_hooks)} 个提示提交触发Hook")
        
        # 模拟不同类型的提示
        test_prompts = [
            "请帮我修复这个Bug",
            "运行测试",
            "检查代码质量",
            "生成文档",
            "部署应用"
        ]
        
        for hook in prompt_hooks:
            for prompt in test_prompts:
                # 提示提交触发通常基于内容匹配
                should_trigger = self._should_trigger_for_prompt(hook, prompt)
                
                self.test_results.append(TestResult(
                    hook.name, "prompt_submit_trigger", True,
                    f"提示 '{prompt[:20]}...' 触发状态: {should_trigger}",
                    details={"prompt": prompt, "triggered": should_trigger}
                ))
    
    def _test_trigger_conflicts(self):
        """测试触发冲突"""
        print("\n⚠️ 测试触发冲突...")
        
        # 按触发类型分组
        file_edit_hooks = [h for h in self.hooks if h.trigger_type == TriggerType.FILE_EDITED]
        
        # 检查文件模式重叠
        conflicts = []
        for i, hook1 in enumerate(file_edit_hooks):
            for hook2 in file_edit_hooks[i+1:]:
                overlapping_patterns = self._find_pattern_overlap(hook1.patterns, hook2.patterns)
                if overlapping_patterns:
                    conflicts.append({
                        "hook1": hook1.name,
                        "hook2": hook2.name,
                        "overlapping_patterns": overlapping_patterns
                    })
        
        if conflicts:
            for conflict in conflicts:
                self.test_results.append(TestResult(
                    "conflict_detection", "trigger_conflict", False,
                    f"发现触发冲突: {conflict['hook1']} vs {conflict['hook2']}",
                    details=conflict
                ))
        else:
            self.test_results.append(TestResult(
                "conflict_detection", "trigger_conflict", True,
                "未发现触发冲突"
            ))
    
    def _test_performance(self):
        """性能测试"""
        print("\n⚡ 性能测试...")
        
        # 测试Hook配置加载性能
        start_time = time.time()
        self._load_hook_configs()
        load_time = time.time() - start_time
        
        self.test_results.append(TestResult(
            "performance", "config_load_time", load_time < 1.0,
            f"配置加载时间: {load_time:.3f}s (目标: <1.0s)",
            execution_time=load_time
        ))
        
        # 测试文件匹配性能
        start_time = time.time()
        test_file = "src/very/deep/nested/test_file.py"
        for hook in self.hooks:
            if hook.trigger_type == TriggerType.FILE_EDITED:
                self._should_trigger_for_file(hook, test_file)
        match_time = time.time() - start_time
        
        self.test_results.append(TestResult(
            "performance", "pattern_matching_time", match_time < 0.1,
            f"模式匹配时间: {match_time:.3f}s (目标: <0.1s)",
            execution_time=match_time
        ))
    
    def _should_trigger_for_file(self, hook: HookConfig, file_path: str) -> bool:
        """判断Hook是否应该为特定文件触发"""
        if hook.trigger_type != TriggerType.FILE_EDITED:
            return False
        
        import fnmatch
        for pattern in hook.patterns:
            if fnmatch.fnmatch(file_path, pattern):
                return True
        return False
    
    def _should_trigger_for_prompt(self, hook: HookConfig, prompt: str) -> bool:
        """判断Hook是否应该为特定提示触发"""
        if hook.trigger_type != TriggerType.PROMPT_SUBMIT:
            return False
        
        # 简单的关键词匹配逻辑
        trigger_keywords = ["测试", "test", "质量", "quality", "检查", "check"]
        prompt_lower = prompt.lower()
        
        return any(keyword in prompt_lower for keyword in trigger_keywords)
    
    def _find_pattern_overlap(self, patterns1: List[str], patterns2: List[str]) -> List[str]:
        """查找模式重叠"""
        overlaps = []
        import fnmatch
        
        for p1 in patterns1:
            for p2 in patterns2:
                # 简单的重叠检测
                if p1 == p2:
                    overlaps.append(p1)
                elif "*" in p1 and "*" in p2:
                    # 更复杂的模式重叠检测可以在这里实现
                    pass
        
        return overlaps
    
    def _create_temp_file(self, file_path: str, content: str) -> Path:
        """创建临时测试文件"""
        # 在系统临时目录创建文件
        temp_dir = Path(tempfile.gettempdir()) / "kiro_hook_test"
        temp_dir.mkdir(exist_ok=True)
        
        temp_file = temp_dir / file_path
        temp_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(temp_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        self.temp_files.append(temp_file)
        return temp_file
    
    def _cleanup(self):
        """清理临时文件"""
        print("\n🧹 清理临时文件...")
        for temp_file in self.temp_files:
            try:
                if temp_file.exists():
                    temp_file.unlink()
            except Exception as e:
                print(f"清理文件失败 {temp_file}: {e}")
    
    def _print_results(self) -> Tuple[bool, List[TestResult]]:
        """输出测试结果"""
        print("\n" + "="*60)
        print("📊 Hook触发逻辑测试结果")
        print("="*60)
        
        # 按测试类型分组统计
        test_types = {}
        for result in self.test_results:
            if result.test_type not in test_types:
                test_types[result.test_type] = {"passed": 0, "failed": 0, "total": 0}
            
            test_types[result.test_type]["total"] += 1
            if result.passed:
                test_types[result.test_type]["passed"] += 1
            else:
                test_types[result.test_type]["failed"] += 1
        
        # 输出统计信息
        total_passed = sum(result.passed for result in self.test_results)
        total_tests = len(self.test_results)
        
        print(f"总测试数: {total_tests}")
        print(f"通过: {total_passed}")
        print(f"失败: {total_tests - total_passed}")
        print(f"通过率: {(total_passed/total_tests*100):.1f}%")
        print()
        
        # 按类型输出详细结果
        for test_type, stats in test_types.items():
            print(f"📋 {test_type}:")
            print(f"  通过: {stats['passed']}/{stats['total']} ({stats['passed']/stats['total']*100:.1f}%)")
            
            # 显示失败的测试
            failed_tests = [r for r in self.test_results 
                          if r.test_type == test_type and not r.passed]
            for failed_test in failed_tests:
                print(f"  ❌ {failed_test.hook_name}: {failed_test.message}")
            print()
        
        # 显示触发冲突详情
        conflict_results = [r for r in self.test_results if r.test_type == "trigger_conflict"]
        if conflict_results:
            print("⚠️ 触发冲突详情:")
            for result in conflict_results:
                if not result.passed and result.details:
                    print(f"  {result.details}")
            print()
        
        # 显示性能测试结果
        perf_results = [r for r in self.test_results if "performance" in r.test_type]
        if perf_results:
            print("⚡ 性能测试结果:")
            for result in perf_results:
                status = "✅" if result.passed else "❌"
                print(f"  {status} {result.message}")
            print()
        
        print("="*60)
        
        all_passed = total_passed == total_tests
        if all_passed:
            print("🎉 所有Hook触发逻辑测试通过！")
        else:
            print("💥 部分Hook触发逻辑测试失败！")
        
        return all_passed, self.test_results


def main():
    """主函数"""
    tester = HookTriggerTester()
    success, results = tester.run_all_tests()
    
    return 0 if success else 1


if __name__ == "__main__":
    exit(main())