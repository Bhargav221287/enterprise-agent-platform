#!/usr/bin/env python3
"""Quality Gate CLI: Verifies AI-generated Python code snippets against safety policies.

Scans sample snippets, ensuring all safe code passes while dangerous or malformed code
is strictly rejected. Exits non-zero if any unsafe snippet is wrongly accepted.
"""

import argparse
import sys
from pathlib import Path

# Add verifier service to sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
VERIFIER_PATH = REPO_ROOT / "verifier"
if str(VERIFIER_PATH) not in sys.path:
    sys.path.insert(0, str(VERIFIER_PATH))

from app.checks import check_syntax, scan_safety_ast  # noqa: E402


def run_verification_gate(samples_dir: Path) -> int:
    """Run verification checks on all snippet files in the directory."""
    print("=" * 70)
    print(" ENTERPRISE AGENT PLATFORM - VERIFICATION QUALITY GATE")
    print(f" Scanning directory: {samples_dir}")
    print("=" * 70)

    if not samples_dir.exists():
        print(f"ERROR: Samples directory not found: {samples_dir}")
        return 1

    sample_files = sorted(list(samples_dir.glob("*.py")))
    if not sample_files:
        print("ERROR: No .py sample files found to verify.")
        return 1

    failures = []
    passed_count = 0

    for file_path in sample_files:
        filename = file_path.name
        code = file_path.read_text(encoding="utf-8")
        is_expected_unsafe = any(kw in filename.lower() for kw in ("unsafe", "broken", "malformed"))

        print(f"\nEvaluating: {filename} (Expectation: {'REJECT' if is_expected_unsafe else 'ACCEPT'})")

        # 1. Syntax Check
        syntax_res = check_syntax(code)
        if not syntax_res.passed:
            if is_expected_unsafe:
                print(f"  [PASSED GATE] Syntax error correctly detected: {syntax_res.violations}")
                passed_count += 1
                continue
            else:
                msg = f"Good snippet '{filename}' failed syntax check: {syntax_res.violations}"
                print(f"  [FAILED GATE] {msg}")
                failures.append(msg)
                continue

        # 2. Safety Scan
        safety_res = scan_safety_ast(code)
        if not safety_res.passed:
            if is_expected_unsafe:
                print(f"  [PASSED GATE] Safety violation correctly caught: {safety_res.violations}")
                passed_count += 1
                continue
            else:
                msg = f"Good snippet '{filename}' was wrongly flagged for safety: {safety_res.violations}"
                print(f"  [FAILED GATE] {msg}")
                failures.append(msg)
                continue

        # If it reached here, code was deemed safe
        if is_expected_unsafe:
            msg = f"CRITICAL SECURITY FAILURE: Unsafe snippet '{filename}' was wrongly ACCEPTED!"
            print(f"  [FAILED GATE] {msg}")
            failures.append(msg)
        else:
            print("  [PASSED GATE] Clean snippet verified and accepted.")
            passed_count += 1

    print("\n" + "=" * 70)
    print(f"SUMMARY: {passed_count}/{len(sample_files)} snippets matched safety policy expectations.")

    if failures:
        print(f"\nGATE REJECTED: {len(failures)} policy failures encountered:")
        for f in failures:
            print(f"  - {f}")
        return 1

    print("ALL VERIFICATION CHECKS PASSED: Code generation quality gate satisfied.")
    print("=" * 70)
    return 0


def main():
    parser = argparse.ArgumentParser(description="AI Code Generation Verification Quality Gate")
    parser.add_argument(
        "--directory",
        type=Path,
        default=REPO_ROOT / "samples" / "ai_generated",
        help="Directory containing snippet samples",
    )
    args = parser.parse_args()
    sys.exit(run_verification_gate(args.directory))


if __name__ == "__main__":
    main()
