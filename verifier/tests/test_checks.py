"""Unit tests for AST syntax and safety checks."""

from app.checks import check_syntax, scan_safety_ast


def test_syntax_valid():
    """Verify valid Python syntax passes check."""
    code = "def add(a: int, b: int) -> int:\n    return a + b\n"
    res = check_syntax(code)
    assert res.passed is True
    assert len(res.violations) == 0


def test_syntax_invalid():
    """Verify syntax error is caught with line number."""
    code = "def broken(a, b\n    return a + b\n"
    res = check_syntax(code)
    assert res.passed is False
    assert len(res.violations) > 0
    assert "Line 1" in res.violations[0]


def test_safety_blocks_os_import():
    """Verify import of 'os' is strictly blocked."""
    code = "import os\nos.system('echo hi')\n"
    res = scan_safety_ast(code)
    assert res.passed is False
    assert any("module 'os'" in v for v in res.violations)
    assert any("os.system()" in v for v in res.violations)


def test_safety_blocks_subprocess():
    """Verify import of 'subprocess' is strictly blocked."""
    code = "import subprocess\nsubprocess.Popen(['ls'])\n"
    res = scan_safety_ast(code)
    assert res.passed is False
    assert any("subprocess" in v for v in res.violations)


def test_safety_blocks_socket():
    """Verify socket networking operations are blocked."""
    code = "import socket\ns = socket.socket()\n"
    res = scan_safety_ast(code)
    assert res.passed is False
    assert any("socket" in v for v in res.violations)


def test_safety_blocks_eval_exec():
    """Verify eval() and exec() are blocked."""
    code = "def dynamic_runner(payload: str):\n    eval(payload)\n    exec(payload)\n"
    res = scan_safety_ast(code)
    assert res.passed is False
    assert any("eval()" in v for v in res.violations)
    assert any("exec()" in v for v in res.violations)


def test_safety_blocks_dunder_import():
    """Verify __import__() dynamic module loading is blocked."""
    code = "mod = __import__('os')\n"
    res = scan_safety_ast(code)
    assert res.passed is False
    assert any("__import__()" in v for v in res.violations)


def test_safety_blocks_open_absolute_path():
    """Verify open() with absolute file paths is blocked."""
    code = "with open('/etc/shadow', 'r') as f:\n    data = f.read()\n"
    res = scan_safety_ast(code)
    assert res.passed is False
    assert any("Prohibited open()" in v for v in res.violations)


def test_safety_blocks_open_traversal():
    """Verify open() with path traversal (..) is blocked."""
    code = "with open('../secrets.env', 'r') as f:\n    data = f.read()\n"
    res = scan_safety_ast(code)
    assert res.passed is False
    assert any("traversal path" in v for v in res.violations)


def test_safety_passes_clean_code():
    """Verify safe data transformation code passes all security checks."""
    code = (
        "def format_ticket(ticket_id: str, priority: str) -> dict:\n"
        "    return {'id': ticket_id.upper(), 'p': priority.capitalize()}\n"
    )
    res = scan_safety_ast(code)
    assert res.passed is True
    assert len(res.violations) == 0
