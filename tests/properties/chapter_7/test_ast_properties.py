"""AST白名单验证器属性测试

白皮书依据: 第七章 7.2 AST白名单验证

测试AST验证器的通用属性。
"""

import pytest
from hypothesis import given, strategies as st, settings
from src.compliance.ast_validator import ASTWhitelistValidator


# ============================================================================
# Property 14: AST Blacklist Rejection
# ============================================================================

@pytest.mark.property
@settings(max_examples=100)
@given(
    blacklist_func=st.sampled_from([
        'eval', 'exec', 'compile', '__import__', 'open',
        'os.system', 'subprocess.call', 'pickle.load',
        'getattr', 'setattr',
    ])
)
def test_property_14_ast_blacklist_rejection(blacklist_func):
    """Property 14: AST Blacklist Rejection
    
    白皮书依据: 第七章 7.2 AST白名单验证
    **Validates: Requirements 9.2, 9.3**
    
    For any code containing calls to blacklisted functions, 
    the ASTWhitelistValidator SHALL reject the code.
    """
    validator = ASTWhitelistValidator()
    
    # 生成包含黑名单函数的代码
    code = f"result = {blacklist_func}('test')"
    
    result = validator.validate(code)
    
    # 属性：必须拒绝
    assert result.approved is False, \
        f"黑名单函数 {blacklist_func} 应该被拒绝"
    
    # 属性：违规项中应包含该函数
    assert any(blacklist_func in v for v in result.violations), \
        f"违规项中应包含 {blacklist_func}"


@pytest.mark.property
@settings(max_examples=100)
@given(
    blacklist_module=st.sampled_from([
        'os', 'sys', 'subprocess', 'socket', 'pickle',
        'ctypes', 'multiprocessing', 'threading',
    ])
)
def test_property_14_ast_blacklist_module_rejection(blacklist_module):
    """Property 14: AST Blacklist Module Rejection
    
    白皮书依据: 第七章 7.2 AST白名单验证
    **Validates: Requirements 9.2, 9.3**
    
    For any code importing blacklisted modules,
    the ASTWhitelistValidator SHALL reject the code.
    """
    validator = ASTWhitelistValidator()
    
    # 生成包含黑名单模块的代码
    code = f"import {blacklist_module}"
    
    result = validator.validate(code)
    
    # 属性：必须拒绝
    assert result.approved is False, \
        f"黑名单模块 {blacklist_module} 应该被拒绝"
    
    # 属性：违规项中应包含该模块
    assert any(blacklist_module in v for v in result.violations), \
        f"违规项中应包含 {blacklist_module}"


@pytest.mark.property
@settings(max_examples=100)
@given(
    blacklist_module=st.sampled_from([
        'os', 'sys', 'subprocess', 'socket', 'pickle',
    ]),
    import_name=st.sampled_from(['system', 'call', 'load', 'socket', 'exit'])
)
def test_property_14_ast_blacklist_from_import_rejection(blacklist_module, import_name):
    """Property 14: AST Blacklist From-Import Rejection
    
    白皮书依据: 第七章 7.2 AST白名单验证
    **Validates: Requirements 9.2, 9.3**
    
    For any code using "from blacklisted_module import ...",
    the ASTWhitelistValidator SHALL reject the code.
    """
    validator = ASTWhitelistValidator()
    
    # 生成from-import语句
    code = f"from {blacklist_module} import {import_name}"
    
    result = validator.validate(code)
    
    # 属性：必须拒绝
    assert result.approved is False, \
        f"from {blacklist_module} import 应该被拒绝"
    
    # 属性：违规项中应包含该模块
    assert any(blacklist_module in v for v in result.violations), \
        f"违规项中应包含 {blacklist_module}"


# ============================================================================
# Property 15: AST Whitelist Allowance
# ============================================================================

@pytest.mark.property
@settings(max_examples=100)
@given(
    whitelist_func=st.sampled_from([
        'abs', 'min', 'max', 'sum', 'round', 'len',
        'int', 'float', 'str', 'bool', 'list', 'dict',
        'sorted', 'enumerate', 'zip', 'any', 'all',
    ])
)
def test_property_15_ast_whitelist_allowance_builtin(whitelist_func):
    """Property 15: AST Whitelist Allowance (Built-in Functions)
    
    白皮书依据: 第七章 7.2 AST白名单验证
    **Validates: Requirements 9.4**
    
    For any code containing only whitelisted built-in functions
    and no blacklisted elements, the ASTWhitelistValidator SHALL approve the code.
    """
    validator = ASTWhitelistValidator()
    
    # 生成只包含白名单函数的代码
    code = f"result = {whitelist_func}([1, 2, 3])"
    
    result = validator.validate(code)
    
    # 属性：必须通过
    assert result.approved is True, \
        f"白名单函数 {whitelist_func} 应该被允许"
    
    # 属性：无违规项
    assert len(result.violations) == 0, \
        f"白名单函数不应有违规项"


@pytest.mark.property
@settings(max_examples=100)
@given(
    factor_operator=st.sampled_from([
        'rank', 'delay', 'delta', 'ts_sum', 'ts_mean', 'ts_std',
        'ts_max', 'ts_min', 'ts_rank', 'sign', 'log', 'scale',
    ])
)
def test_property_15_ast_whitelist_allowance_factor_operators(factor_operator):
    """Property 15: AST Whitelist Allowance (Factor Operators)
    
    白皮书依据: 第七章 7.2 AST白名单验证 + 第四章因子算子
    **Validates: Requirements 9.4**
    
    For any code containing only whitelisted factor operators
    and no blacklisted elements, the ASTWhitelistValidator SHALL approve the code.
    """
    validator = ASTWhitelistValidator()
    
    # 生成只包含因子算子的代码
    code = f"result = {factor_operator}(close)"
    
    result = validator.validate(code)
    
    # 属性：必须通过
    assert result.approved is True, \
        f"因子算子 {factor_operator} 应该被允许"
    
    # 属性：无违规项
    assert len(result.violations) == 0, \
        f"因子算子不应有违规项"


@pytest.mark.property
@settings(max_examples=100)
@given(
    num_operations=st.integers(min_value=1, max_value=5)
)
def test_property_15_ast_whitelist_allowance_combined(num_operations):
    """Property 15: AST Whitelist Allowance (Combined Operations)
    
    白皮书依据: 第七章 7.2 AST白名单验证
    **Validates: Requirements 9.4**
    
    For any code combining multiple whitelisted operations
    and no blacklisted elements, the ASTWhitelistValidator SHALL approve the code.
    """
    validator = ASTWhitelistValidator()
    
    # 生成组合多个白名单操作的代码
    operations = ['abs', 'min', 'max', 'sum', 'round']
    code_parts = []
    for i in range(num_operations):
        op = operations[i % len(operations)]
        code_parts.append(f"{op}(x)")
    
    code = f"result = {' + '.join(code_parts)}"
    
    result = validator.validate(code)
    
    # 属性：必须通过
    assert result.approved is True, \
        f"组合白名单操作应该被允许"
    
    # 属性：无违规项
    assert len(result.violations) == 0, \
        f"组合白名单操作不应有违规项"


# ============================================================================
# Property 16: AST Validation Idempotence
# ============================================================================

@pytest.mark.property
@settings(max_examples=100)
@given(
    code_template=st.sampled_from([
        "result = abs(-5)",
        "result = min(1, 2, 3)",
        "result = rank(close)",
        "result = delay(close, 5)",
        "x = 1 + 2",
        "if x > 0:\n    result = x",
    ])
)
def test_property_16_ast_validation_idempotence(code_template):
    """Property 16: AST Validation Idempotence
    
    白皮书依据: 第七章 7.2 AST白名单验证
    **Validates: Requirements 9.7**
    
    For any valid factor expression, running AST validation multiple times
    SHALL produce the same result each time.
    """
    validator = ASTWhitelistValidator()
    
    # 第一次验证
    result1 = validator.validate(code_template)
    
    # 第二次验证
    result2 = validator.validate(code_template)
    
    # 第三次验证
    result3 = validator.validate(code_template)
    
    # 属性：所有结果的approved状态相同
    assert result1.approved == result2.approved == result3.approved, \
        "多次验证的approved状态应该相同"
    
    # 属性：所有结果的违规项数量相同
    assert len(result1.violations) == len(result2.violations) == len(result3.violations), \
        "多次验证的违规项数量应该相同"
    
    # 属性：所有结果的内容哈希相同
    assert result1.content_hash == result2.content_hash == result3.content_hash, \
        "多次验证的内容哈希应该相同"


@pytest.mark.property
@settings(max_examples=100)
@given(
    code_base=st.text(
        alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'), min_codepoint=65, max_codepoint=122),
        min_size=1,
        max_size=20
    )
)
def test_property_16_ast_validation_idempotence_with_random_code(code_base):
    """Property 16: AST Validation Idempotence (Random Code)
    
    白皮书依据: 第七章 7.2 AST白名单验证
    **Validates: Requirements 9.7**
    
    For any code (valid or invalid), running AST validation multiple times
    SHALL produce the same result each time.
    """
    validator = ASTWhitelistValidator()
    
    # 构造简单的代码（可能有语法错误）
    code = f"x = {code_base}"
    
    # 多次验证
    results = [validator.validate(code) for _ in range(3)]
    
    # 属性：所有结果的approved状态相同
    approved_values = [r.approved for r in results]
    assert len(set(approved_values)) == 1, \
        "多次验证的approved状态应该相同"
    
    # 属性：所有结果的违规项数量相同
    violation_counts = [len(r.violations) for r in results]
    assert len(set(violation_counts)) == 1, \
        "多次验证的违规项数量应该相同"
    
    # 属性：所有结果的内容哈希相同
    hashes = [r.content_hash for r in results]
    assert len(set(hashes)) == 1, \
        "多次验证的内容哈希应该相同"


@pytest.mark.property
@settings(max_examples=100)
@given(
    num_validations=st.integers(min_value=2, max_value=10)
)
def test_property_16_ast_validation_idempotence_multiple_runs(num_validations):
    """Property 16: AST Validation Idempotence (Multiple Runs)
    
    白皮书依据: 第七章 7.2 AST白名单验证
    **Validates: Requirements 9.7**
    
    For any code, running AST validation N times SHALL produce
    the same result every time.
    """
    validator = ASTWhitelistValidator()
    
    code = "result = abs(-5) + min(1, 2, 3)"
    
    # 运行N次验证
    results = [validator.validate(code) for _ in range(num_validations)]
    
    # 属性：所有结果的approved状态相同
    approved_values = [r.approved for r in results]
    assert all(a == approved_values[0] for a in approved_values), \
        f"所有{num_validations}次验证的approved状态应该相同"
    
    # 属性：所有结果的违规项数量相同
    violation_counts = [len(r.violations) for r in results]
    assert all(c == violation_counts[0] for c in violation_counts), \
        f"所有{num_validations}次验证的违规项数量应该相同"
    
    # 属性：所有结果的内容哈希相同
    hashes = [r.content_hash for r in results]
    assert all(h == hashes[0] for h in hashes), \
        f"所有{num_validations}次验证的内容哈希应该相同"


# ============================================================================
# Additional Property Tests
# ============================================================================

@pytest.mark.property
@settings(max_examples=100)
@given(
    complexity=st.integers(min_value=1, max_value=50)  # 限制在50以内，避免Python解析器限制
)
def test_property_complexity_threshold_enforcement(complexity):
    """Property: Complexity Threshold Enforcement
    
    白皮书依据: 第七章 7.2 AST白名单验证
    **Validates: Requirements 9.5**
    
    For any code with complexity exceeding max_complexity,
    the ASTWhitelistValidator SHALL reject the code.
    """
    # 设置较低的复杂度阈值
    max_complexity = 5
    validator = ASTWhitelistValidator(max_complexity=max_complexity)
    
    # 生成具有指定复杂度的代码（使用嵌套if语句）
    if_statements = "\n".join([f"{'    ' * i}if x{i}:" for i in range(complexity)])
    code = f"{if_statements}\n{'    ' * complexity}result = 1"
    
    result = validator.validate(code)
    
    # 属性：如果复杂度超过阈值，必须拒绝
    if complexity > max_complexity:
        assert result.approved is False, \
            f"复杂度 {complexity} > {max_complexity} 应该被拒绝"
        # 检查是否因为复杂度或语法错误被拒绝
        assert len(result.violations) > 0, \
            "应该有违规项"
    else:
        # 复杂度在阈值内，应该通过（假设没有其他违规）
        assert result.approved is True or len(result.violations) == 0, \
            f"复杂度 {complexity} <= {max_complexity} 应该通过"


@pytest.mark.property
@settings(max_examples=100)
@given(
    code_length=st.integers(min_value=1, max_value=1000)
)
def test_property_validation_performance_scales(code_length):
    """Property: Validation Performance Scales
    
    白皮书依据: 第七章 7.2 AST白名单验证
    **Validates: Requirements 9.6 (性能要求)**
    
    For any code of reasonable length, validation SHALL complete
    within acceptable time limits.
    """
    validator = ASTWhitelistValidator()
    
    # 生成指定长度的代码
    code = "\n".join([f"x{i} = {i}" for i in range(code_length)])
    
    result = validator.validate(code)
    
    # 属性：验证时间应该合理
    # 对于短代码：< 1ms
    # 对于中等代码：< 10ms
    # 对于长代码：< 100ms
    if code_length <= 10:
        max_time_ms = 1.0
    elif code_length <= 100:
        max_time_ms = 10.0
    else:
        max_time_ms = 100.0
    
    assert result.execution_time_ms < max_time_ms, \
        f"验证耗时 {result.execution_time_ms:.2f}ms 超过预期 {max_time_ms:.2f}ms (code_length={code_length})"


@pytest.mark.property
@settings(max_examples=100)
@given(
    has_blacklist=st.booleans(),
    has_whitelist=st.booleans()
)
def test_property_mixed_content_detection(has_blacklist, has_whitelist):
    """Property: Mixed Content Detection
    
    白皮书依据: 第七章 7.2 AST白名单验证
    **Validates: Requirements 9.2, 9.4**
    
    For any code containing both whitelisted and blacklisted elements,
    the ASTWhitelistValidator SHALL reject the code due to blacklisted elements.
    """
    validator = ASTWhitelistValidator()
    
    code_parts = []
    
    if has_whitelist:
        code_parts.append("result1 = abs(-5)")
    
    if has_blacklist:
        code_parts.append("result2 = eval('1 + 1')")
    
    if not code_parts:
        code_parts.append("pass")
    
    code = "\n".join(code_parts)
    
    result = validator.validate(code)
    
    # 属性：如果包含黑名单元素，必须拒绝
    if has_blacklist:
        assert result.approved is False, \
            "包含黑名单元素的代码应该被拒绝"
        assert len(result.violations) > 0, \
            "应该检测到黑名单违规"
    elif has_whitelist:
        # 只有白名单元素，应该通过
        assert result.approved is True, \
            "只包含白名单元素的代码应该通过"
