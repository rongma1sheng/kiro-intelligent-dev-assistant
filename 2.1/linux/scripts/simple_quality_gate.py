#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
简化质量门禁脚本 - 用于调试
"""

import sys
from pathlib import Path

# 添加当前目录到路径
sys.path.append(str(Path(__file__).parent))

def main():
    """主函数"""
    target = sys.argv[1] if len(sys.argv) > 1 else "src"
    
    print("🔍 运行简化质量门禁检查...")
    
    try:
        from enhanced_quality_gate import EnhancedQualityGate
        
        gate = EnhancedQualityGate()
        is_compliant, violations = gate.run_comprehensive_check(target)
        
        if is_compliant:
            print("✅ 质量门禁: PASSED")
            return 0
        else:
            print("❌ 质量门禁: FAILED")
            total_violations = sum(len(v) for v in violations.values())
            print(f"总违规数: {total_violations}")
            return 1
            
    except Exception as e:
        print(f"❌ 质量门禁执行失败: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())