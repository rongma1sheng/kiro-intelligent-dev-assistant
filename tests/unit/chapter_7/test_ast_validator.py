"""ASTWhitelistValidator单元测试

白皮书依据: 第七章 7.2 AST白名单验证

测试AST白名单验证器的各项功能。
"""

import pytest
from src.compliance.ast_validator import (
    ASTWhitelistValidator,
    ASTValidationError,
    ValidationResult,
)


class TestASTWhitelistValidatorInit:
    """测试ASTWhitelistValidator初始化"""
    
    def test_default_initialization(self):
        """测试默认初始化"""
        validator = ASTWhitelistValidator()
        
        assert validator is not None
        assert len(validator.whitelist_functions) > 0
        assert len(validator.blacklist_functions) > 0
        assert len(validator.blacklist_modules) > 0
        assert validator.max_complexity == 50
    
    def test_custom_whitelist(self):
        """测试自定义白名单"""
        custom_whitelist = {'abs', 'min', 'max'}
        validator = ASTWhitelistValidator(whitelist_functions=custom_whitelist)
        
        assert validator.whitelist_functions == custom_whitelist
    
    def test_custom_blacklist_functions(self):
        """测试自定义黑名单函数"""
        custom_blacklist = {'eval', 'exec'}
        validator = ASTWhitelistValidator(blacklist_functions=custom_blacklist)
        
        assert validator.blacklist_functions == custom_blacklist
    
    def test_custom_blacklist_modules(self):
        """测试自定义黑名单模块"""
        custom_modules = {'os', 'sys'}
        validator = ASTWhitelistValidator(blacklist_modules=custom_modules)
        
        assert validator.blacklist_modules == custom_modules
    
    def test_custom_max_complexity(self):
        """测试自定义最大复杂度"""
        validator = ASTWhitelistValidator(max_complexity=100)
        
        assert validator.max_complexity == 100


class TestASTWhitelistValidatorBlacklistFunctions:
    """测试黑名单函数拒绝"""
    
    def test_reject_eval(self):
        """测试拒绝eval函数"""
        validator = ASTWhitelistValidator()
        code = "result = eval('1 + 1')"
        
        result = validator.validate(code)
        
        assert result.approved is False
        assert any('eval' in v for v in result.violations)
        assert result.execution_time_ms > 0
    
    def test_reject_exec(self):
        """测试拒绝exec函数"""
        validator = ASTWhitelistValidator()
        code = "exec('print(1)')"
        
        result = validator.validate(code)
        
        assert result.approved is False
        assert any('exec' in v for v in result.violations)
    
    def test_reject_compile(self):
        """测试拒绝compile函数"""
        validator = ASTWhitelistValidator()
        code = "code_obj = compile('1 + 1', '<string>', 'eval')"
        
        result = validator.validate(code)
        
        assert result.approved is False
        assert any('compile' in v for v in result.violations)
    
    def test_reject___import__(self):
        """测试拒绝__import__函数"""
        validator = ASTWhitelistValidator()
        code = "os_module = __import__('os')"
        
        result = validator.validate(code)
        
        assert result.approved is False
        assert any('__import__' in v for v in result.violations)
    
    def test_reject_open(self):
        """测试拒绝open函数"""
        validator = ASTWhitelistValidator()
        code = "f = open('/etc/passwd', 'r')"
        
        result = validator.validate(code)
        
        assert result.approved is False
        assert any('open' in v for v in result.violations)
    
    def test_reject_os_system(self):
        """测试拒绝os.system函数"""
        validator = ASTWhitelistValidator()
        code = "import os\nos.system('ls')"
        
        result = validator.validate(code)
        
        # 应该同时检测到模块导入和函数调用
        assert result.approved is False
        assert len(result.violations) >= 1  # 至少有模块导入违规
    
    def test_reject_subprocess_call(self):
        """测试拒绝subprocess.call函数"""
        validator = ASTWhitelistValidator()
        code = "import subprocess\nsubprocess.call(['ls'])"
        
        result = validator.validate(code)
        
        assert result.approved is False
        assert len(result.violations) >= 1
    
    def test_reject_pickle_load(self):
        """测试拒绝pickle.load函数"""
        validator = ASTWhitelistValidator()
        code = "import pickle\ndata = pickle.load(f)"
        
        result = validator.validate(code)
        
        assert result.approved is False
        assert len(result.violations) >= 1
    
    def test_reject_getattr(self):
        """测试拒绝getattr函数"""
        validator = ASTWhitelistValidator()
        code = "attr = getattr(obj, 'method')"
        
        result = validator.validate(code)
        
        assert result.approved is False
        assert any('getattr' in v for v in result.violations)
    
    def test_reject_setattr(self):
        """测试拒绝setattr函数"""
        validator = ASTWhitelistValidator()
        code = "setattr(obj, 'attr', value)"
        
        result = validator.validate(code)
        
        assert result.approved is False
        assert any('setattr' in v for v in result.violations)


class TestASTWhitelistValidatorBlacklistModules:
    """测试黑名单模块拒绝"""
    
    def test_reject_import_os(self):
        """测试拒绝import os"""
        validator = ASTWhitelistValidator()
        code = "import os"
        
        result = validator.validate(code)
        
        assert result.approved is False
        assert any('os' in v for v in result.violations)
    
    def test_reject_import_sys(self):
        """测试拒绝import sys"""
        validator = ASTWhitelistValidator()
        code = "import sys"
        
        result = validator.validate(code)
        
        assert result.approved is False
        assert any('sys' in v for v in result.violations)
    
    def test_reject_import_subprocess(self):
        """测试拒绝import subprocess"""
        validator = ASTWhitelistValidator()
        code = "import subprocess"
        
        result = validator.validate(code)
        
        assert result.approved is False
        assert any('subprocess' in v for v in result.violations)
    
    def test_reject_import_socket(self):
        """测试拒绝import socket"""
        validator = ASTWhitelistValidator()
        code = "import socket"
        
        result = validator.validate(code)
        
        assert result.approved is False
        assert any('socket' in v for v in result.violations)
    
    def test_reject_import_pickle(self):
        """测试拒绝import pickle"""
        validator = ASTWhitelistValidator()
        code = "import pickle"
        
        result = validator.validate(code)
        
        assert result.approved is False
        assert any('pickle' in v for v in result.violations)
    
    def test_reject_from_os_import(self):
        """测试拒绝from os import"""
        validator = ASTWhitelistValidator()
        code = "from os import system"
        
        result = validator.validate(code)
        
        assert result.approved is False
        assert any('os' in v for v in result.violations)
    
    def test_reject_from_subprocess_import(self):
        """测试拒绝from subprocess import"""
        validator = ASTWhitelistValidator()
        code = "from subprocess import call"
        
        result = validator.validate(code)
        
        assert result.approved is False
        assert any('subprocess' in v for v in result.violations)
    
    def test_reject_urllib_request(self):
        """测试拒绝urllib.request"""
        validator = ASTWhitelistValidator()
        code = "import urllib.request"
        
        result = validator.validate(code)
        
        assert result.approved is False
        # urllib.request应该被urllib前缀匹配
        assert len(result.violations) > 0


class TestASTWhitelistValidatorWhitelistFunctions:
    """测试白名单函数允许"""
    
    def test_allow_abs(self):
        """测试允许abs函数"""
        validator = ASTWhitelistValidator()
        code = "result = abs(-5)"
        
        result = validator.validate(code)
        
        assert result.approved is True
        assert len(result.violations) == 0
    
    def test_allow_min_max(self):
        """测试允许min/max函数"""
        validator = ASTWhitelistValidator()
        code = "result = min(1, 2, 3) + max(4, 5, 6)"
        
        result = validator.validate(code)
        
        assert result.approved is True
        assert len(result.violations) == 0
    
    def test_allow_sum(self):
        """测试允许sum函数"""
        validator = ASTWhitelistValidator()
        code = "result = sum([1, 2, 3, 4, 5])"
        
        result = validator.validate(code)
        
        assert result.approved is True
        assert len(result.violations) == 0
    
    def test_allow_pandas_series(self):
        """测试允许pd.Series"""
        validator = ASTWhitelistValidator()
        code = "import pandas as pd\ns = pd.Series([1, 2, 3])"
        
        result = validator.validate(code)
        
        assert result.approved is True
        assert len(result.violations) == 0
    
    def test_allow_numpy_array(self):
        """测试允许np.array"""
        validator = ASTWhitelistValidator()
        code = "import numpy as np\narr = np.array([1, 2, 3])"
        
        result = validator.validate(code)
        
        assert result.approved is True
        assert len(result.violations) == 0
    
    def test_allow_factor_operators(self):
        """测试允许因子算子"""
        validator = ASTWhitelistValidator()
        code = """
result = rank(close)
delayed = delay(close, 5)
change = delta(close, 1)
"""
        
        result = validator.validate(code)
        
        assert result.approved is True
        assert len(result.violations) == 0
    
    def test_allow_complex_expression(self):
        """测试允许复杂表达式"""
        validator = ASTWhitelistValidator()
        code = """
import pandas as pd
import numpy as np

def calculate_factor(close, volume):
    # 计算价格变化
    returns = close / delay(close, 1) - 1
    
    # 计算排名
    rank_returns = rank(returns)
    
    # 计算移动平均
    ma = ts_mean(close, 20)
    
    # 组合因子
    factor = rank_returns * np.log(volume + 1)
    
    return factor
"""
        
        result = validator.validate(code)
        
        assert result.approved is True
        assert len(result.violations) == 0


class TestASTWhitelistValidatorComplexity:
    """测试复杂度检查"""
    
    def test_simple_code_passes(self):
        """测试简单代码通过"""
        validator = ASTWhitelistValidator(max_complexity=10)
        code = "result = abs(-5)"
        
        result = validator.validate(code)
        
        assert result.approved is True
    
    def test_moderate_complexity_passes(self):
        """测试中等复杂度通过"""
        validator = ASTWhitelistValidator(max_complexity=10)
        code = """
if x > 0:
    result = x
elif x < 0:
    result = -x
else:
    result = 0
"""
        
        result = validator.validate(code)
        
        assert result.approved is True
    
    def test_high_complexity_fails(self):
        """测试高复杂度失败"""
        validator = ASTWhitelistValidator(max_complexity=5)
        code = """
if a:
    if b:
        if c:
            if d:
                if e:
                    if f:
                        result = 1
"""
        
        result = validator.validate(code)
        
        assert result.approved is False
        assert any('复杂度' in v for v in result.violations)
    
    def test_loop_increases_complexity(self):
        """测试循环增加复杂度"""
        validator = ASTWhitelistValidator(max_complexity=2)
        code = """
for i in range(10):
    for j in range(10):
        for k in range(10):
            result = i + j + k
"""
        
        result = validator.validate(code)
        
        # 3个嵌套循环，复杂度为3，应该超过max_complexity=2
        assert result.approved is False
        assert any('复杂度' in v for v in result.violations)
    
    def test_exception_handling_increases_complexity(self):
        """测试异常处理增加复杂度"""
        validator = ASTWhitelistValidator(max_complexity=2)
        code = """
try:
    result = risky_operation()
except ValueError:
    result = 0
except TypeError:
    result = 1
except Exception:
    result = -1
"""
        
        result = validator.validate(code)
        
        assert result.approved is False
        assert any('复杂度' in v for v in result.violations)


class TestASTWhitelistValidatorEdgeCases:
    """测试边界条件"""
    
    def test_empty_code(self):
        """测试空代码"""
        validator = ASTWhitelistValidator()
        code = ""
        
        result = validator.validate(code)
        
        assert result.approved is False
        assert '空' in result.reason
    
    def test_whitespace_only_code(self):
        """测试仅空白字符代码"""
        validator = ASTWhitelistValidator()
        code = "   \n\t  \n  "
        
        result = validator.validate(code)
        
        assert result.approved is False
        assert '空' in result.reason
    
    def test_syntax_error(self):
        """测试语法错误"""
        validator = ASTWhitelistValidator()
        code = "if x > 0"  # 缺少冒号
        
        result = validator.validate(code)
        
        assert result.approved is False
        assert '语法错误' in result.reason
    
    def test_invalid_indentation(self):
        """测试缩进错误"""
        validator = ASTWhitelistValidator()
        code = """
def func():
result = 1
"""
        
        result = validator.validate(code)
        
        assert result.approved is False
        assert '语法错误' in result.reason or '解析' in result.reason
    
    def test_content_hash_generated(self):
        """测试内容哈希生成"""
        validator = ASTWhitelistValidator()
        code = "result = abs(-5)"
        
        result = validator.validate(code)
        
        assert result.content_hash != ""
        assert len(result.content_hash) == 64  # SHA256哈希长度
    
    def test_same_code_same_hash(self):
        """测试相同代码生成相同哈希"""
        validator = ASTWhitelistValidator()
        code = "result = abs(-5)"
        
        result1 = validator.validate(code)
        result2 = validator.validate(code)
        
        assert result1.content_hash == result2.content_hash
    
    def test_different_code_different_hash(self):
        """测试不同代码生成不同哈希"""
        validator = ASTWhitelistValidator()
        code1 = "result = abs(-5)"
        code2 = "result = abs(-6)"
        
        result1 = validator.validate(code1)
        result2 = validator.validate(code2)
        
        assert result1.content_hash != result2.content_hash


class TestASTWhitelistValidatorPerformance:
    """测试性能要求"""
    
    def test_validation_latency_under_1ms(self):
        """测试验证延迟 < 1ms (P99)
        
        白皮书依据: 第七章 7.2 性能要求
        """
        validator = ASTWhitelistValidator()
        code = "result = abs(-5)"
        
        # 运行多次取P99
        latencies = []
        for _ in range(100):
            result = validator.validate(code)
            latencies.append(result.execution_time_ms)
        
        latencies.sort()
        p99_latency = latencies[98]  # 第99个值
        
        assert p99_latency < 1.0, f"P99延迟 {p99_latency:.3f}ms 超过1ms"
    
    def test_complex_code_validation_performance(self):
        """测试复杂代码验证性能"""
        validator = ASTWhitelistValidator()
        code = """
import pandas as pd
import numpy as np

def calculate_complex_factor(data):
    close = data['close']
    volume = data['volume']
    
    # 多个因子计算
    returns = close / delay(close, 1) - 1
    rank_returns = rank(returns)
    ma5 = ts_mean(close, 5)
    ma20 = ts_mean(close, 20)
    vol_ma = ts_mean(volume, 20)
    
    # 组合因子
    factor = (rank_returns * np.log(volume / vol_ma + 1) * 
              (ma5 / ma20 - 1))
    
    return factor
"""
        
        result = validator.validate(code)
        
        # 复杂代码也应该在合理时间内完成
        assert result.execution_time_ms < 5.0, \
            f"复杂代码验证耗时 {result.execution_time_ms:.3f}ms 超过5ms"


class TestASTWhitelistValidatorMultipleViolations:
    """测试多个违规项"""
    
    def test_multiple_blacklist_functions(self):
        """测试多个黑名单函数"""
        validator = ASTWhitelistValidator()
        code = """
result1 = eval('1 + 1')
result2 = exec('print(1)')
result3 = compile('x = 1', '<string>', 'exec')
"""
        
        result = validator.validate(code)
        
        assert result.approved is False
        assert len(result.violations) >= 3
    
    def test_multiple_blacklist_modules(self):
        """测试多个黑名单模块"""
        validator = ASTWhitelistValidator()
        code = """
import os
import sys
import subprocess
"""
        
        result = validator.validate(code)
        
        assert result.approved is False
        assert len(result.violations) >= 3
    
    def test_mixed_violations(self):
        """测试混合违规"""
        validator = ASTWhitelistValidator(max_complexity=2)
        code = """
import os

if True:
    if True:
        if True:
            result = eval('1 + 1')
"""
        
        result = validator.validate(code)
        
        assert result.approved is False
        # 应该检测到：模块导入、eval函数、复杂度
        assert len(result.violations) >= 2


class TestASTWhitelistValidatorValidationResult:
    """测试ValidationResult数据类"""
    
    def test_validation_result_structure(self):
        """测试ValidationResult结构"""
        result = ValidationResult(
            approved=True,
            reason="测试",
            violations=[],
            execution_time_ms=1.5,
            content_hash="abc123"
        )
        
        assert result.approved is True
        assert result.reason == "测试"
        assert result.violations == []
        assert result.execution_time_ms == 1.5
        assert result.content_hash == "abc123"
    
    def test_validation_result_default_values(self):
        """测试ValidationResult默认值"""
        result = ValidationResult(approved=False)
        
        assert result.approved is False
        assert result.reason == ""
        assert result.violations == []
        assert result.execution_time_ms == 0.0
        assert result.content_hash == ""
