"""AST-based syntax and safety validation checks for AI-generated code."""

import ast
import time
from typing import List

from app.schemas import CheckResult


class SafetyASTVisitor(ast.NodeVisitor):
    """AST visitor detecting dangerous operations, unauthorized imports, and injection vectors."""

    BLOCKED_MODULES = {
        "os",
        "subprocess",
        "socket",
        "sys",
        "shutil",
        "pty",
        "multiprocessing",
        "ctypes",
        "commands",
        "builtins",
        "importlib",
        "posix",
        "nt",
    }

    BLOCKED_FUNCTIONS = {
        "eval",
        "exec",
        "__import__",
        "globals",
        "locals",
        "compile",
        "breakpoint",
    }

    def __init__(self) -> None:
        self.violations: List[str] = []

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            base_pkg = alias.name.split(".")[0]
            if base_pkg in self.BLOCKED_MODULES:
                self.violations.append(
                    f"Line {node.lineno}: Prohibited import of module '{alias.name}'"
                )
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.module:
            base_pkg = node.module.split(".")[0]
            if base_pkg in self.BLOCKED_MODULES:
                self.violations.append(
                    f"Line {node.lineno}: Prohibited import from module '{node.module}'"
                )
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        # Check direct function calls (e.g. eval(), exec(), __import__())
        if isinstance(node.func, ast.Name):
            if node.func.id in self.BLOCKED_FUNCTIONS:
                self.violations.append(
                    f"Line {node.lineno}: Prohibited function call '{node.func.id}()'"
                )
            elif node.func.id == "open":
                self._check_open_call(node)

        # Check attribute calls (e.g. os.system(), subprocess.run(), socket.connect())
        elif isinstance(node.func, ast.Attribute):
            attr_name = node.func.attr
            # If the attribute object is a Name (e.g. os.system)
            if isinstance(node.func.value, ast.Name):
                pkg_name = node.func.value.id
                if pkg_name in self.BLOCKED_MODULES:
                    self.violations.append(
                        f"Line {node.lineno}: Prohibited call to '{pkg_name}.{attr_name}()'"
                    )
            elif attr_name in ("system", "popen", "spawn"):
                self.violations.append(
                    f"Line {node.lineno}: Prohibited call to method '{attr_name}()'"
                )

        self.generic_visit(node)

    def _check_open_call(self, node: ast.Call) -> None:
        """Inspect arguments to open() to prevent absolute path or path traversal access."""
        if not node.args:
            return

        arg0 = node.args[0]
        # Check constant string literal file paths
        if isinstance(arg0, ast.Constant) and isinstance(arg0.value, str):
            path_val = arg0.value
            if (
                path_val.startswith("/")
                or (len(path_val) > 1 and path_val[1] == ":")
                or ".." in path_val
                or path_val.startswith("\\")
            ):
                self.violations.append(
                    f"Line {node.lineno}: Prohibited open() call with absolute or traversal path: '{path_val}'"
                )
        else:
            # Dynamic path passed to open()
            self.violations.append(
                f"Line {node.lineno}: Prohibited open() call with non-literal dynamic path expression"
            )


def check_syntax(code: str) -> CheckResult:
    """Check 1: Parse abstract syntax tree to verify Python syntax validity."""
    start_time = time.perf_counter()
    try:
        ast.parse(code)
        duration_ms = (time.perf_counter() - start_time) * 1000
        return CheckResult(
            check_name="syntax_check",
            passed=True,
            execution_time_ms=round(duration_ms, 2),
        )
    except SyntaxError as syn_err:
        duration_ms = (time.perf_counter() - start_time) * 1000
        violation = f"Line {syn_err.lineno}, Col {syn_err.offset}: {syn_err.msg}"
        return CheckResult(
            check_name="syntax_check",
            passed=False,
            execution_time_ms=round(duration_ms, 2),
            violations=[violation],
            error="Syntax error in source code",
        )


def scan_safety_ast(code: str) -> CheckResult:
    """Check 2: Static analysis of AST to block unsafe modules, builtins, and file access."""
    start_time = time.perf_counter()
    try:
        tree = ast.parse(code)
    except SyntaxError:
        # Syntax check handles syntax errors; safety scan skips unparseable code
        return CheckResult(
            check_name="ast_safety_scan",
            passed=False,
            execution_time_ms=0.0,
            error="Cannot perform safety scan on syntactically invalid code",
        )

    visitor = SafetyASTVisitor()
    visitor.visit(tree)
    duration_ms = (time.perf_counter() - start_time) * 1000

    passed = len(visitor.violations) == 0
    return CheckResult(
        check_name="ast_safety_scan",
        passed=passed,
        execution_time_ms=round(duration_ms, 2),
        violations=visitor.violations,
        error="Safety policy violations detected" if not passed else None,
    )
