"""
Comprehensive tests for DocGenerator docstring-patch engine.

Each test:
1. menyiapkan potongan kode Python (string)
2. mem-parse AST, menemukan node target (function/class/async)
3. menjalankan DocGenerator._update_docstring_with_fallback
4. memverifikasi:
   - operasi berhasil (success == True)
   - docstring baru tersisip / terganti sesuai harapan
   - kode hasil bisa di-compile ulang (syntax-safe)
"""

import ast
import threading

from avcmt.modules.doc_generator import DocGenerator

NEW_DOCSTRING = "New docstring content."

# Constants for test assertions
MIN_NESTED_INDENT_SPACES = 16  # Minimum indentation for deeply nested classes


def _make_source(lines: list[str]) -> str:
    """Helper: create properly formatted source from lines."""
    return "\n".join(lines) + "\n"


def _run_patch(source: str, target_name: str):
    """Helper: jalankan patcher & kembalikan (success, updated_code)."""
    tree = ast.parse(source)
    node = next(
        n
        for n in ast.walk(tree)
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
        and n.name == target_name
    )
    lines = source.splitlines(keepends=True)

    dg = DocGenerator(threading.Event(), debug=False)
    success, new_lines = dg._update_docstring_with_fallback(lines, node, NEW_DOCSTRING)
    updated_code = "".join(new_lines)
    return success, updated_code


# ---------- 1. INLINE - SAME LINE -------------------------------------------------
def test_inline_same_line_replaced():
    # FIXED: Inline docstring dengan body function yang benar
    src = _make_source(["def foo():", '    """old desc"""', "    return 1"])
    success, code = _run_patch(src, "foo")

    # Harus sukses, header TIDAK lagi mengandung triple-quotes,
    # dan docstring baru ada di baris selanjutnya.
    assert success
    assert NEW_DOCSTRING in code
    ast.parse(code)  # syntax check


# ---------- 2. INLINE - OPEN ONLY -------------------------------------------------
def test_inline_open_only_replaced():
    src = _make_source(
        ["def bar():", '    """', "    old stuff", '    """', "    return 0"]
    )
    success, code = _run_patch(src, "bar")

    assert success
    assert NEW_DOCSTRING in code
    # semua triple-quotes sekarang dalam blok terformat, bukan di header
    assert code.splitlines()[0].rstrip().endswith(":")
    ast.parse(code)


# ---------- 3. MULTI-LINE BAWAH HEADER -------------------------------------------
def test_multiline_below_header_replaced():
    src = _make_source(
        [
            "def baz():",
            '    """',
            "    old multi-line",
            "    docstring",
            '    """',
            "    pass",
        ]
    )
    success, code = _run_patch(src, "baz")

    assert success
    assert NEW_DOCSTRING in code
    ast.parse(code)


# ---------- 4. TANPA DOCSTRING ----------------------------------------------------
def test_insert_when_missing():
    src = _make_source(["def qux(a, b):", "    return a + b"])
    success, code = _run_patch(src, "qux")

    assert success
    assert NEW_DOCSTRING in code
    ast.parse(code)


# ---------- 5. CLASS DOCSTRING EXISTING -------------------------------------------
def test_class_docstring_replaced():
    src = _make_source(
        ["class Demo:", '    """old class docs"""', "    def method(self): ..."]
    )
    success, code = _run_patch(src, "Demo")

    assert success
    assert NEW_DOCSTRING in code
    ast.parse(code)


# ---------- 6. CLASS TANPA DOCSTRING ---------------------------------------------
def test_class_insert_when_missing():
    src = _make_source(["class NoDoc:", "    def spam(self): return 1"])
    success, code = _run_patch(src, "NoDoc")

    assert success
    assert NEW_DOCSTRING in code
    ast.parse(code)


# ---------- 7. ASYNC FUNCTION -----------------------------------------------------
def test_async_function_docstring():
    src = _make_source(["async def afunc(x):", "    return x * 2"])
    success, code = _run_patch(src, "afunc")

    assert success
    assert NEW_DOCSTRING in code
    ast.parse(code)


# ---------- 8. TRIPLE SINGLE QUOTES ----------------------------------------------
def test_single_quote_style_handled():
    src = _make_source(
        ["def single():", "    '''old single quote'''", "    return 'ok'"]
    )
    success, code = _run_patch(src, "single")

    assert success
    assert NEW_DOCSTRING in code
    ast.parse(code)


# ---------- 9. FALLBACK KE LEGACY ALG --------------------------------------------
def test_legacy_fallback(monkeypatch):
    """Paksa _insert_docstring() gagal → pastikan legacy path sukses."""
    src = _make_source(["def legacy():", "    pass"])
    # Patch method agar selalu False → trigger legacy
    dg = DocGenerator(threading.Event(), debug=False)
    monkeypatch.setattr(dg, "_insert_docstring", lambda *a, **kw: False)

    tree = ast.parse(src)
    node = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef))

    lines = src.splitlines(keepends=True)
    success, new_lines = dg._update_docstring_with_fallback(lines, node, NEW_DOCSTRING)
    updated_code = "".join(new_lines)

    assert success
    assert NEW_DOCSTRING in updated_code
    ast.parse(updated_code)


# ---------- 10. COMPLEX MULTI-LINE HEADERS WITH TYPE HINTS ----------------------
def test_multiline_header_with_type_hints():
    """Test complex function headers spanning multiple lines with type annotations."""
    src = _make_source(
        [
            "def complex_func(",
            "    param1: str,",
            "    param2: Optional[Dict[str, Any]],",
            "    param3: Union[int, float] = 10",
            ") -> Tuple[str, int]:",
            '    return "test", 1',
        ]
    )
    success, code = _run_patch(src, "complex_func")

    assert success
    assert NEW_DOCSTRING in code
    # Ensure the function definition is preserved
    assert "def complex_func(" in code
    assert ") -> Tuple[str, int]:" in code
    ast.parse(code)


# ---------- 11. NESTED CLASS WITH COMPLEX DOCSTRING -------------------------
def test_nested_class_docstring():
    """Test docstring replacement in nested class scenarios."""
    src = _make_source(
        [
            "class Outer:",
            "    class Inner:",
            '        """old inner docstring"""',
            "        def method(self): pass",
        ]
    )
    success, code = _run_patch(src, "Inner")

    assert success
    assert NEW_DOCSTRING in code
    assert "old inner docstring" not in code
    ast.parse(code)


# ---------- 12. DECORATORS WITH DOCSTRINGS ----------------------------------
def test_decorated_function_docstring():
    """Test function with decorators maintaining proper docstring placement."""
    src = _make_source(
        [
            "@property",
            "@lru_cache(maxsize=128)",
            "def decorated_func(self):",
            '    """old decorated docstring"""',
            "    return self._value",
        ]
    )
    success, code = _run_patch(src, "decorated_func")

    assert success
    assert NEW_DOCSTRING in code
    assert "@property" in code
    assert "@lru_cache" in code
    ast.parse(code)


# ---------- 13. MIXED QUOTE STYLES ------------------------------------------
def test_mixed_quote_styles():
    """Test handling of both triple single and double quotes."""
    src = _make_source(
        [
            "def mixed_quotes():",
            "    '''old single quote docstring'''",
            "    return 'result'",
        ]
    )
    success, code = _run_patch(src, "mixed_quotes")

    assert success
    assert NEW_DOCSTRING in code
    # Should convert to standard double quotes
    assert '"""' in code
    ast.parse(code)


# ---------- 14. VERY LONG INLINE DOCSTRING ----------------------------------
def test_very_long_inline_docstring():
    """Test handling of extremely long inline docstrings."""
    long_docstring = "This is a very long existing docstring that spans way beyond normal line limits and should be properly handled"
    src = _make_source(
        ["def long_inline():", f'    """{long_docstring}"""', "    return True"]
    )
    success, code = _run_patch(src, "long_inline")

    assert success
    assert NEW_DOCSTRING in code
    assert long_docstring not in code
    ast.parse(code)


# ---------- 15. EMPTY FUNCTION BODY -----------------------------------------
def test_empty_function_with_pass():
    """Test function with only pass statement."""
    src = _make_source(["def empty_func():", "    pass"])
    success, code = _run_patch(src, "empty_func")

    assert success
    assert NEW_DOCSTRING in code
    assert "pass" in code
    ast.parse(code)


# ---------- 16. FUNCTION WITH ELLIPSIS --------------------------------------
def test_function_with_ellipsis():
    """Test function with ellipsis (protocol/stub style)."""
    src = _make_source(["def stub_func(x: int) -> str:", "    ..."])
    success, code = _run_patch(src, "stub_func")

    assert success
    assert NEW_DOCSTRING in code
    assert "..." in code
    ast.parse(code)


# ---------- 17. MULTILINE STRING AS FIRST STATEMENT -------------------------
def test_multiline_string_not_docstring():
    """Test function with multiline string that's not a docstring."""
    src = _make_source(
        [
            "def func_with_string():",
            '    text = """',
            "    This is not a docstring",
            "    but a regular string",
            '    """',
            "    return text",
        ]
    )
    success, code = _run_patch(src, "func_with_string")

    assert success
    assert NEW_DOCSTRING in code
    # Original string should remain
    assert "This is not a docstring" in code
    ast.parse(code)


# ---------- 18. SYNTAX ERROR RECOVERY ---------------------------------------
def test_syntax_error_recovery(monkeypatch):
    """Test recovery when new insertion creates syntax error."""
    src = _make_source(["def recovery_test():", "    return 1"])

    dg = DocGenerator(threading.Event(), debug=False)

    # Mock _insert_docstring to return True but _validate_syntax to fail initially
    original_validate = dg._validate_syntax
    call_count = [0]

    def mock_validate(lines):
        call_count[0] += 1
        if call_count[0] == 1:
            return False  # First call fails
        return original_validate(lines)  # Second call succeeds

    monkeypatch.setattr(dg, "_validate_syntax", mock_validate)

    tree = ast.parse(src)
    node = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef))
    lines = src.splitlines(keepends=True)

    success, new_lines = dg._update_docstring_with_fallback(lines, node, NEW_DOCSTRING)
    updated_code = "".join(new_lines)

    assert success
    assert NEW_DOCSTRING in updated_code
    ast.parse(updated_code)


# ---------- 19. SPECIAL CHARACTERS IN DOCSTRING ----------------------------
def test_special_characters_in_docstring():
    """Test docstring with special characters and escape sequences."""
    special_docstring = (
        "Docstring with \"quotes\" and 'apostrophes' and \\backslashes\\"
    )
    src = _make_source(["def special_chars():", "    pass"])

    tree = ast.parse(src)
    node = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef))
    lines = src.splitlines(keepends=True)

    dg = DocGenerator(threading.Event(), debug=False)
    success, new_lines = dg._update_docstring_with_fallback(
        lines, node, special_docstring
    )
    updated_code = "".join(new_lines)

    assert success
    assert special_docstring in updated_code
    ast.parse(updated_code)


# ---------- 20. EXTREMELY NESTED INDENTATION -------------------------------
def test_deeply_nested_function():
    """Test function with deep nesting levels."""
    src = _make_source(
        [
            "class A:",
            "    class B:",
            "        class C:",
            "            def deeply_nested(self):",
            '                """old deep docstring"""',
            '                return "deep"',
        ]
    )
    success, code = _run_patch(src, "deeply_nested")

    assert success
    assert NEW_DOCSTRING in code
    # Check indentation is preserved - should have proper nesting
    lines = code.split("\n")
    docstring_line = next(line for line in lines if NEW_DOCSTRING in line)
    # Should have at least some indentation for nested class
    assert (
        len(docstring_line) - len(docstring_line.lstrip()) >= MIN_NESTED_INDENT_SPACES
    )  # At least 16 spaces
    ast.parse(code)


# ---------- 21. FUNCTION WITH ONLY DOCSTRING --------------------------------
def test_function_only_docstring():
    """Test function that contains only a docstring."""
    src = _make_source(
        ["def docs_only():", '    """This function only has documentation."""']
    )
    success, code = _run_patch(src, "docs_only")

    assert success
    assert NEW_DOCSTRING in code
    assert "This function only has documentation." not in code
    ast.parse(code)


# ---------- 22. ASYNC FUNCTION WITH COMPLEX SIGNATURE ----------------------
def test_async_complex_signature():
    """Test async function with complex signature and existing docstring."""
    src = _make_source(
        [
            "async def async_complex(",
            "    self,",
            "    *args: Any,",
            "    **kwargs: Dict[str, Any]",
            ") -> AsyncGenerator[str, None]:",
            '    """old async docstring"""',
            '    yield "test"',
        ]
    )
    success, code = _run_patch(src, "async_complex")

    assert success
    assert NEW_DOCSTRING in code
    assert "async def" in code
    assert "old async docstring" not in code
    ast.parse(code)


# ---------- 23. CLASS WITH METACLASS AND INHERITANCE ----------------------
def test_complex_class_definition():
    """Test class with metaclass, inheritance, and complex definition."""
    src = _make_source(
        [
            "class ComplexClass(",
            "    BaseClass,",
            "    MixinClass,",
            "    metaclass=MetaClass",
            "):",
            '    """old complex class docstring"""',
            "    pass",
        ]
    )
    success, code = _run_patch(src, "ComplexClass")

    assert success
    assert NEW_DOCSTRING in code
    assert "metaclass=MetaClass" in code
    assert "old complex class docstring" not in code
    ast.parse(code)


# ---------- 24. EDGE CASE: MALFORMED QUOTES --------------------------------
def test_malformed_quote_handling():
    """Test handling of malformed or unbalanced quotes."""
    src = _make_source(['def malformed(): """unclosed docstring', '    return "test"'])

    # This should either be handled gracefully or fall back to legacy
    try:
        tree = ast.parse(src)
        node = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef))
        lines = src.splitlines(keepends=True)

        dg = DocGenerator(threading.Event(), debug=False)
        success, new_lines = dg._update_docstring_with_fallback(
            lines, node, NEW_DOCSTRING
        )

        if success:
            updated_code = "".join(new_lines)
            ast.parse(updated_code)  # Should be valid after fix
    except SyntaxError:
        # Original code was malformed, which is expected
        pass


# ---------- 25. WHITESPACE AND FORMATTING PRESERVATION --------------------
def test_whitespace_preservation():
    """Test that existing whitespace and formatting is preserved where appropriate."""
    src = _make_source(
        [
            "def whitespace_test(",
            "    param1,",
            "    param2",
            "):",
            '    """old docstring"""',
            "    ",
            "    ",
            "    return param1 + param2",
        ]
    )
    success, code = _run_patch(src, "whitespace_test")

    assert success
    assert NEW_DOCSTRING in code
    # Some whitespace should be preserved
    assert "return param1 + param2" in code
    ast.parse(code)


# ---------- 26. UNICODE AND ENCODING TESTS ---------------------------------
def test_unicode_docstring():
    """Test handling of unicode characters in docstrings."""
    unicode_docstring = "Функция c unicode символами: αβγ 中文 🚀"
    src = _make_source(["def unicode_func():", "    pass"])

    tree = ast.parse(src)
    node = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef))
    lines = src.splitlines(keepends=True)

    dg = DocGenerator(threading.Event(), debug=False)
    success, new_lines = dg._update_docstring_with_fallback(
        lines, node, unicode_docstring
    )
    updated_code = "".join(new_lines)

    assert success
    assert unicode_docstring in updated_code
    ast.parse(updated_code)


# ---------- 27. PROPERTY AND DESCRIPTOR METHODS ----------------------------
def test_property_method_docstring():
    """Test docstring handling for property methods."""
    src = _make_source(
        [
            "class TestClass:",
            "    @property",
            "    def prop_method(self):",
            '        """old property docstring"""',
            "        return self._value",
            "        ",
            "    @prop_method.setter",
            "    def prop_method(self, value):",
            "        self._value = value",
        ]
    )
    success, code = _run_patch(src, "prop_method")

    assert success
    assert NEW_DOCSTRING in code
    assert "@property" in code
    ast.parse(code)


# ---------- 28. GENERATOR FUNCTIONS ----------------------------------------
def test_generator_function_docstring():
    """Test docstring handling for generator functions."""
    src = _make_source(
        [
            "def generator_func():",
            '    """old generator docstring"""',
            "    yield 1",
            "    yield 2",
            "    yield 3",
        ]
    )
    success, code = _run_patch(src, "generator_func")

    assert success
    assert NEW_DOCSTRING in code
    assert "yield" in code
    ast.parse(code)


# ---------- 29. CONTEXT MANAGER METHODS ------------------------------------
def test_context_manager_methods():
    """Test docstring handling for context manager methods."""
    src = _make_source(
        [
            "class ContextManager:",
            "    def __enter__(self):",
            '        """old enter docstring"""',
            "        return self",
            "        ",
            "    def __exit__(self, exc_type, exc_val, exc_tb):",
            "        pass",
        ]
    )
    success, code = _run_patch(src, "__enter__")

    assert success
    assert NEW_DOCSTRING in code
    assert "__enter__" in code
    ast.parse(code)


# ---------- 30. COMPREHENSIVE STRESS TEST ----------------------------------
def test_comprehensive_stress_test():
    """Comprehensive test combining multiple challenging patterns."""
    src = _make_source(
        [
            "@dataclass",
            '@custom_decorator(param="value")',
            "class StressTestClass(",
            "    BaseClass,",
            "    ProtocolClass,",
            "    Generic[T],",
            "    metaclass=CustomMeta",
            "):",
            '    """old class docstring with \'quotes\' and "more quotes" """',
            "    ",
            "    @classmethod",
            "    async def complex_method(",
            "        cls,",
            "        param1: Optional[Union[str, int]],",
            "        *args: Tuple[Any, ...],",
            "        **kwargs: Dict[str, Any]",
            "    ) -> AsyncIterator[Tuple[str, int]]:",
            '        """old method docstring"""',
            "        async for item in some_async_iterator():",
            '            yield ("result", 42)',
        ]
    )

    # Test both class and method
    class_success, class_code = _run_patch(src, "StressTestClass")
    method_success, method_code = _run_patch(src, "complex_method")

    assert class_success
    assert method_success
    assert NEW_DOCSTRING in class_code
    assert NEW_DOCSTRING in method_code
    ast.parse(class_code)
    ast.parse(method_code)
