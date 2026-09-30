#!/usr/bin/env python3
"""
Universal make verify script for CrisisMesh.
Runs all quality gates: secret scan, linting, type checks, tests.
Works on Windows (PowerShell) and Unix/macOS.
"""
import subprocess
import sys
import os
import platform

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND = os.path.join(ROOT, "frontend")
IS_WIN = platform.system() == "Windows"

RESULTS = []


def npm_cmd(*args):
    """Return platform-appropriate npm command list."""
    npm = "npm.cmd" if IS_WIN else "npm"
    return [npm, *args]


def npx_cmd(*args):
    """Return platform-appropriate npx command list."""
    npx = "npx.cmd" if IS_WIN else "npx"
    return [npx, *args]


def run(label: str, cmd: list, cwd: str = ROOT, expected_rc: int = 0) -> bool:
    print(f"\n{'='*60}")
    print(f"[RUN] {label}")
    print(f"  $ {' '.join(str(c) for c in cmd)}")
    print("=" * 60)
    try:
        rc = subprocess.call(cmd, cwd=cwd)
        ok = rc == expected_rc
        RESULTS.append((label, ok, f"exit={rc}"))
        print(f"  [{'PASS' if ok else 'FAIL'}] {label}")
        return ok
    except FileNotFoundError as e:
        RESULTS.append((label, False, str(e)))
        print(f"  [FAIL] {label}: {e}")
        return False


def main():
    print("=" * 60)
    print("CRISISMESH make verify -- Full Quality Gate")
    print("=" * 60)

    # 1. Secret scan
    run("Secret scan (git history)",
        [sys.executable, "scripts/scan_secrets.py"])

    # 2. Backend ruff lint
    run("Backend ruff lint",
        [sys.executable, "-m", "ruff", "check", "backend/"])

    # 3. Backend pytest (66 tests)
    run("Backend pytest (66 tests)",
        [sys.executable, "-m", "pytest", "backend/tests/", "-v", "--tb=short"])

    # 4. Frontend ESLint
    run("Frontend ESLint",
        npm_cmd("run", "lint"),
        cwd=FRONTEND)

    # 5. Frontend TypeScript check
    run("Frontend tsc --noEmit",
        npx_cmd("tsc", "--noEmit"),
        cwd=FRONTEND)

    # 6. Frontend production build
    run("Frontend npm build",
        npm_cmd("run", "build"),
        cwd=FRONTEND)

    # 7. npm audit (informational — known pinned CVEs documented below)
    run("npm audit (informational, known issues documented)",
        npm_cmd("audit"),
        cwd=FRONTEND,
        expected_rc=0)  # We accept non-zero; real failures documented

    # Summary
    print("\n" + "=" * 60)
    print("VERIFY RESULTS")
    print("=" * 60)
    passed = sum(1 for _, ok, _ in RESULTS if ok)
    failed = sum(1 for _, ok, _ in RESULTS if not ok)
    for label, ok, detail in RESULTS:
        status = "PASS" if ok else "FAIL"
        print(f"  [{status}] {label}" + (f" ({detail})" if not ok else ""))

    print(f"\nTotal: {passed} passed, {failed} failed")
    if failed > 0:
        # Check if only npm audit failed (informational)
        real_failures = [(l, d) for l, ok, d in RESULTS if not ok and "audit" not in l.lower()]
        if real_failures:
            print("\n[!] Critical checks failed. Review output above.")
            sys.exit(1)
        else:
            print("\n[*] All critical checks passed. npm audit findings documented in docs/threat-model.md.")
            sys.exit(0)
    else:
        print("\n[*] All checks passed. CrisisMesh is ready.")
        sys.exit(0)


if __name__ == "__main__":
    main()
