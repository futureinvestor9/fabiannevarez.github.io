"""Safety invariants enforced technically + isolated accept-phase1 (Section U/V)."""
import ast
import re
from pathlib import Path

from jobsearch_os import accept_phase1

PKG = Path(__file__).resolve().parents[2] / "jobsearch_os"

FORBIDDEN_IMPORTS = {"smtplib", "selenium", "playwright", "requests"}
FORBIDDEN_CALL_NAMES = {"sendmail", "send_message", "connect_to_profile"}


def _py_files():
    return list(PKG.rglob("*.py"))


def test_no_external_action_code_path():
    violations = []
    for path in _py_files():
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for n in node.names:
                    if n.name.split(".")[0] in FORBIDDEN_IMPORTS:
                        violations.append(f"{path.name}: import {n.name}")
            elif isinstance(node, ast.ImportFrom):
                if (node.module or "").split(".")[0] in FORBIDDEN_IMPORTS:
                    violations.append(f"{path.name}: from {node.module}")
            elif isinstance(node, ast.Call):
                fn = node.func
                name = fn.attr if isinstance(fn, ast.Attribute) else getattr(fn, "id", None)
                if name in FORBIDDEN_CALL_NAMES:
                    violations.append(f"{path.name}: call {name}")
    assert violations == [], f"external-action/automation paths found: {violations}"


def test_no_linkedin_automation_strings():
    pat = re.compile(r"requests\.(post|put|get)\([^)]*linkedin", re.IGNORECASE)
    for path in _py_files():
        assert not pat.search(path.read_text(encoding="utf-8")), f"{path.name} touches linkedin"


def test_no_hardcoded_secrets():
    secret_pat = re.compile(r"(sk-ant-[A-Za-z0-9]{16,}|sk-[A-Za-z0-9]{20,}|ghp_[A-Za-z0-9]{20,})")
    for path in _py_files():
        m = secret_pat.search(path.read_text(encoding="utf-8"))
        assert not m, f"possible secret literal in {path.name}"


def test_accept_phase1_isolated_passes():
    passed, workspace, report = accept_phase1.run(keep_temp=False)
    assert passed, f"accept-phase1 failed: {report}"
    # production dirs untouched: the harness used a temp workspace
    assert "jobsearch_accept_" in workspace
