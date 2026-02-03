#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
质量门禁脚本 - 集成所有铁律防止LLM漂移

🚨 零号铁律（最高优先级）
- 只能修复"已被明确判定为缺失"的内容
- 不得修改任何已通过认证的章节或功能
- 不得重写或重构非缺失模块
- 不得绕过、弱化或替代任何安全/风控/合规要求

🔒 核心铁律
- 所有回复必须使用中文
- 禁止使用占位符、简化功能
- 发现bug及时修复
- 绝对忠于自己的岗位职责
- 必须专业、标准化、抗幻觉

🧪 测试铁律（最高优先级）
- 严禁跳过任何测试
- 测试超时必须溯源修复（源文件问题或测试逻辑问题）
- 不得使用timeout作为跳过理由
- 发现问题立刻修复

🎯 硅谷12人团队标准
- 遵循角色职责边界，严禁越权
- 复杂问题必须分配给对应角色
- 单轮响应单一主责角色原则
- 强制审计所有维度的完成性

流程：
1. 运行增强质量门禁检查所有铁律
2. 如果有违规:
   - 尝试自动修复
   - 如果无法完全修复，生成详细报告供 AI 处理
3. 如果无违规:
   - 输出成功信息

退出码：
- 0: 无违规或已全部修复
- 1: 有违规需要 AI 介入

使用方法：
    python scripts/quality_gate.py [target_dir]
"""

import sys
from pathlib import Path
from datetime import datetime

# 添加当前目录到路径
sys.path.append(str(Path(__file__).parent))

def main():
    """主函数 - 集成增强质量门禁"""
    target = sys.argv[1] if len(sys.argv) > 1 else "src"
    
    print("")
    print("=" * 60)
    print("🚨 增强质量门禁检查 - 防止LLM漂移")
    print("=" * 60)
    print("")
    
    try:
        # Step 1: 运行增强质量门禁
        print("🔍 [ENHANCED] 运行全面铁律合规检查...")
        from enhanced_quality_gate import EnhancedQualityGate
        
        gate = EnhancedQualityGate()
        is_compliant, violations = gate.run_comprehensive_check(target)
        
        if is_compliant:
            print("")
            print("✅ 所有铁律检查通过!")
            print("")
            print("🎉 质量门禁: PASSED")
            return 0
        
        # Step 2: 生成最终报告
        print("")
        print("=" * 60)
        print("🚨 质量门禁失败 - 需要人工干预")
        print("=" * 60)
        
        total_violations = sum(len(v) for v in violations.values())
        print(f"总违规数: {total_violations}")
        print("")
        
        # 按严重程度分类
        critical_violations = len(violations.get("ZERO_LAW", [])) + len(violations.get("TEST_LAW", []))
        high_violations = len(violations.get("CORE_LAW", [])) + len(violations.get("TEAM_LAW", []))
        medium_violations = len(violations.get("CODE_BUGS", []))
        
        print("违规分类:")
        print(f"  🚨 CRITICAL (零号铁律+测试铁律): {critical_violations}")
        print(f"  ⚠️  HIGH (核心铁律+团队标准): {high_violations}")
        print(f"  📋 MEDIUM (代码质量): {medium_violations}")
        print("")
        
        print("=" * 60)
        print("🔧 推荐修复流程:")
        print("1. 立即修复所有CRITICAL级别违规")
        print("2. 按照硅谷12人团队标准分配任务")
        print("3. 运行: python scripts/team_bug_fixer.py")
        print("4. 严格遵循所有铁律，防止LLM漂移")
        print("=" * 60)
        
        # 保存综合报告
        report_path = Path("reports") / f"quality_gate_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        report_path.parent.mkdir(exist_ok=True)
        
        report_content = f"""
增强质量门禁报告
==================

检查时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
目标目录: {target}
总违规数: {total_violations}

违规分类:
- CRITICAL: {critical_violations} (零号铁律+测试铁律)
- HIGH: {high_violations} (核心铁律+团队标准)  
- MEDIUM: {medium_violations} (代码质量)

状态: FAILED - 需要人工干预

推荐行动:
1. 立即修复所有CRITICAL级别违规
2. 按照硅谷12人团队标准分配任务
3. 运行团队协作修复工具
4. 严格遵循所有铁律，防止LLM漂移

详细违规信息请查看对应的JSON报告文件。
"""
        
        report_path.write_text(report_content, encoding='utf-8')
        print(f"📄 报告已保存: {report_path}")
        
        return 1
        
    except Exception as e:
        print(f"❌ 质量门禁执行失败: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
