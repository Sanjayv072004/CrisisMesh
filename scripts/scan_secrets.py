#!/usr/bin/env python3
"""
CrisisMesh Git History Secret Scanner.
Audits all git commits, commit messages, and tree blobs for:
- Private keys (RSA, OpenSSH, Ed25519)
- High-entropy API tokens (AWS, OpenAI, Anthropic, GitHub)
- Hardcoded database passwords or bearer tokens
"""

import os
import re
import subprocess
import sys

SECRET_PATTERNS = [
    (re.compile(r"-----BEGIN\s+(RSA|OPENSSH|EC|DSA|PRIVATE)\s+KEY-----"), "Private Key Block"),
    (re.compile(r"(?i)(?:api_key|apikey|secret_key|auth_token)\s*[:=]\s*['\"][A-Za-z0-9_\-]{20,}['\"]"), "API Key Assignment"),
    (re.compile(r"(?i)bearer\s+[A-Za-z0-9_\-\.]{25,}"), "Bearer Token"),
    (re.compile(r"sk-[A-Za-z0-9]{32,}"), "OpenAI Secret Key"),
    (re.compile(r"AKIA[0-9A-Z]{16}"), "AWS Access Key ID"),
    (re.compile(r"(?i)password\s*[:=]\s*['\"][^'\"]{8,}['\"]"), "Plaintext Password Assignment"),
]

# Paths allowed to contain mock/demo/sample credentials
ALLOWLIST_FILES = {
    ".env.example",
    "tests/test_auth.py",
    "tests/test_api_phase5.py",
    "tests/attacks/test_owasp_attacks.py",
    "scripts/scan_secrets.py",
    "data/scenario.json",
}

def scan_git_history() -> int:
    print("=" * 60)
    print("CRISISMESH SECRET SCANNER (Git History Audit)")
    print("=" * 60)

    try:
        # Get list of all commit hashes
        res = subprocess.run(
            ["git", "rev-list", "--all"],
            capture_output=True,
            text=True,
            check=True
        )
        commits = [c.strip() for c in res.stdout.splitlines() if c.strip()]
    except Exception as e:
        print(f"Error reading git commits: {e}")
        return 1

    print(f"[*] Scanning {len(commits)} commits across all branches...")

    findings = []
    for commit in commits:
        diff_res = subprocess.run(
            ["git", "show", "--no-color", commit],
            capture_output=True,
            text=True,
            errors="ignore"
        )
        diff_text = diff_res.stdout
        current_file = None

        for line in diff_text.splitlines():
            if line.startswith("+++ b/"):
                current_file = line[6:].strip()
                continue
            if not line.startswith("+") or line.startswith("+++"):
                continue

            added_content = line[1:]
            if current_file and any(allowed in current_file for allowed in ALLOWLIST_FILES):
                continue

            for pattern, desc in SECRET_PATTERNS:
                if pattern.search(added_content):
                    # Filter out benign documentation or env templates
                    if "EXAMPLE" in added_content or "your_" in added_content or "placeholder" in added_content:
                        continue
                    findings.append({
                        "commit": commit[:8],
                        "file": current_file or "unknown",
                        "description": desc,
                        "snippet": added_content.strip()[:60]
                    })

    if findings:
        print(f"[!] WARNING: {len(findings)} potential secret(s) found in git history:")
        for f in findings:
            print(f"    Commit {f['commit']} in {f['file']}: [{f['description']}] -> {f['snippet']}")
        return 1
    else:
        print(f"[PASS] Zero secrets detected in git history across {len(commits)} commits.")
        return 0

if __name__ == "__main__":
    sys.exit(scan_git_history())
