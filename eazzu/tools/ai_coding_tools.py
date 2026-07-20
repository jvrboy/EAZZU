"""AI coding assistant tools.

Pure-Python helpers that model common developer workflows: repo chat,
inline completion, refactoring, test generation, PR review, vulnerability
scanning, migrations, profiling, and more. Each tool returns a structured dict.
"""

from __future__ import annotations

import hashlib
import re

def _detect_language(filename: str) -> str:
    ext_map = {".py": "python", ".js": "javascript", ".ts": "typescript", ".go": "go", ".rs": "rust",
               ".java": "java", ".c": "c", ".cpp": "cpp", ".rb": "ruby", ".php": "php", ".swift": "swift", ".kt": "kotlin"}
    for ext, lang in ext_map.items():
        if filename.endswith(ext):
            return lang
    return "unknown"

def _count_functions(code: str) -> int:
    return len(re.findall(r"^\s*(def |function |func |void |public |private )", code, re.MULTILINE))

def _vuln_patterns() -> list[dict]:
    return [
        {"pattern": r"eval\s*\(", "severity": "high", "name": "eval usage"},
        {"pattern": r"exec\s*\(", "severity": "high", "name": "exec usage"},
        {"pattern": r"SELECT.*\+.*\?", "severity": "high", "name": "SQL injection"},
        {"pattern": r"innerHTML\s*=", "severity": "medium", "name": "XSS via innerHTML"},
        {"pattern": r"os\.system\s*\(", "severity": "high", "name": "command injection"},
        {"pattern": r"password\s*=\s*['\"]", "severity": "medium", "name": "hardcoded password"},
    ]

def _scan_for_vulns(code: str) -> list[dict]:
    findings = []
    for vp in _vuln_patterns():
        for m in re.finditer(vp["pattern"], code, re.IGNORECASE):
            findings.append({"name": vp["name"], "severity": vp["severity"], "line": code[:m.start()].count("\n") + 1})
    return findings

def _cyclomatic(code: str) -> int:
    return max(1, len(re.findall(r"\b(if|elif|else|for|while|case|catch|except|and|or)\b", code)) + 1)

def _dead_code_candidates(code: str) -> list[str]:
    defs = re.findall(r"^\s*(?:def|function|func)\s+(\w+)", code, re.MULTILINE)
    called = set(re.findall(r"\b(\w+)\s*\(", code))
    return [d for d in defs if d not in called]

def _supported_languages() -> list[str]:
    return ["python", "javascript", "typescript", "go", "rust", "java", "c", "cpp", "ruby", "php"]

def _env_packages(lang: str) -> list[str]:
    return {"python": ["pytest", "black", "ruff", "mypy"], "javascript": ["eslint", "prettier", "jest"],
            "typescript": ["typescript", "tslint", "jest"], "go": ["golangci-lint", "gofumpt"],
            "rust": ["clippy", "rustfmt"]}.get(lang, [])

def _hash_file(path: str, content: str = "") -> str:
    return hashlib.sha256((path + content).encode()).hexdigest()[:12]

def _make_mock(method: str, status: int) -> dict:
    return {"method": method.upper(), "status": status, "body": {"mocked": True}}

TOOLS: list[dict] = [
    {"name": "code_repo_chat", "description": "Answer questions about a codebase using indexed repository context.",
     "params": {"repo": "str", "question": "str", "context_files": "list[str]"},
     "run": lambda a: {"answer": f"Based on {a.get('repo', 'repo')}: analysis of '{a.get('question', '')}'",
                      "context_files": a.get("context_files", [])[:5], "confidence": 0.88}},

    {"name": "code_inline_complete", "description": "Generate inline code completions at a cursor position.",
     "params": {"file": "str", "prefix": "str", "suffix": "str", "language": "str"},
     "run": lambda a: {"completions": [a.get("prefix", "") + " // generated completion", a.get("prefix", "") + " // alt"],
                      "language": a.get("language", _detect_language(a.get("file", "")))}},

    {"name": "code_refactor", "description": "Suggest refactoring for a code snippet (extract function, simplify, etc.).",
     "params": {"code": "str", "operation": "str", "language": "str"},
     "run": lambda a: {"operation": a.get("operation", "extract_function"),
                      "suggestions": [{"type": a.get("operation", "extract_function"), "line_start": 1,
                                      "line_end": len((a.get("code", "") or "").splitlines())}],
                      "language": a.get("language", "python")}},

    {"name": "code_test_gen", "description": "Generate unit tests for a given function or module.",
     "params": {"code": "str", "framework": "str", "language": "str"},
     "run": lambda a: {"framework": a.get("framework", "pytest"), "language": a.get("language", "python"),
                      "tests": [{"name": "test_basic_case", "type": "unit"}, {"name": "test_edge_case", "type": "unit"},
                                {"name": "test_error_case", "type": "unit"}],
                      "function_count": _count_functions(a.get("code", ""))}},

    {"name": "code_bug_reproducer", "description": "Generate a minimal reproduction case for a reported bug.",
     "params": {"description": "str", "code": "str", "stack_trace": "str"},
     "run": lambda a: {"reproducer": f"# Minimal repro for: {a.get('description', 'bug')}",
                      "steps": ["setup", "execute", "assert_failure"],
                      "stack_trace_lines": len(a.get("stack_trace", "").splitlines())}},

    {"name": "code_commit_msg", "description": "Generate a conventional commit message from a diff.",
     "params": {"diff": "str", "style": "str"},
     "run": lambda a: {"message": "feat: add new feature" if "add" in a.get("diff", "").lower() else "fix: resolve issue",
                      "style": a.get("style", "conventional"), "files_changed": a.get("diff", "").count("diff --git")}},

    {"name": "code_pr_review", "description": "Review a pull request diff and provide feedback.",
     "params": {"diff": "str", "pr_title": "str", "guidelines": "str"},
     "run": lambda a: {"summary": f"Review of '{a.get('pr_title', 'PR')}'",
                      "issues": [{"severity": "warning", "message": "Consider adding tests", "line": 1}],
                      "approved": False, "files_reviewed": a.get("diff", "").count("diff --git")}},

    {"name": "code_vuln_scan", "description": "Scan code for common security vulnerabilities.",
     "params": {"code": "str", "file": "str"},
     "run": lambda a: {"findings": _scan_for_vulns(a.get("code", "")), "file": a.get("file", "unknown"),
                      "scan_count": len(_vuln_patterns())}},

    {"name": "codebase_qa", "description": "Answer a codebase-level QA query with semantic search.",
     "params": {"query": "str", "repo": "str", "top_k": "int"},
     "run": lambda a: {"query": a.get("query", ""),
                      "results": [{"file": f"src/module_{i}.py", "score": round(0.9 - i * 0.1, 2), "snippet": "..."}
                                  for i in range(a.get("top_k", 3))]}},

    {"name": "code_migration", "description": "Plan a code migration between languages or frameworks.",
     "params": {"source_lang": "str", "target_lang": "str", "files": "list[str]"},
     "run": lambda a: {"source": a.get("source_lang", "python"), "target": a.get("target_lang", "typescript"),
                      "files": a.get("files", []), "estimated_effort_hours": len(a.get("files", [])) * 2, "compatibility": 0.75}},

    {"name": "code_dead_code", "description": "Detect potentially dead (uncalled) functions in code.",
     "params": {"code": "str", "file": "str"},
     "run": lambda a: {"dead_functions": _dead_code_candidates(a.get("code", "")), "file": a.get("file", "unknown"),
                      "total_functions": _count_functions(a.get("code", ""))}},

    {"name": "code_doc_gen", "description": "Generate documentation (docstrings/README) from code.",
     "params": {"code": "str", "format": "str", "language": "str"},
     "run": lambda a: {"format": a.get("format", "docstring"), "language": a.get("language", "python"),
                      "doc": "Generated documentation from code analysis.",
                      "functions_documented": _count_functions(a.get("code", ""))}},

    {"name": "code_regex_builder", "description": "Build and test a regex from a natural-language description.",
     "params": {"description": "str", "test_strings": "list[str]"},
     "run": lambda a: {"regex": r"\d{3}-\d{4}", "description": a.get("description", ""),
                      "test_results": [{"input": s, "match": bool(re.match(r"\d{3}-\d{4}", s))}
                                       for s in a.get("test_strings", ["123-4567", "abc"])]}},

    {"name": "code_sql_builder", "description": "Build a SQL query from a natural-language description.",
     "params": {"description": "str", "dialect": "str", "schema": "dict"},
     "run": lambda a: {"sql": "SELECT * FROM users WHERE active = true;", "dialect": a.get("dialect", "postgresql"),
                      "description": a.get("description", ""),
                      "tables": list(a.get("schema", {}).keys()) if a.get("schema") else ["users"]}},

    {"name": "code_api_mock", "description": "Generate mock API responses for endpoints.",
     "params": {"endpoints": "list[dict]", "base_url": "str"},
     "run": lambda a: {"mocks": [{**ep, "response": _make_mock(ep.get("method", "GET"), ep.get("status", 200))}
                                for ep in a.get("endpoints", [])],
                      "base_url": a.get("base_url", "http://localhost:3000")}},

    {"name": "code_agentic_runner", "description": "Run an agentic coding task with a plan-execute-verify loop.",
     "params": {"task": "str", "max_steps": "int", "tools": "list[str]"},
     "run": lambda a: {"task": a.get("task", ""), "plan": ["analyze", "implement", "test", "verify"],
                      "max_steps": a.get("max_steps", 10), "tools": a.get("tools", ["read", "write", "exec"]), "status": "ready"}},

    {"name": "code_sandbox", "description": "Create an isolated sandbox for running untrusted code.",
     "params": {"language": "str", "code": "str", "timeout_ms": "int"},
     "run": lambda a: {"language": a.get("language", "python"), "timeout_ms": a.get("timeout_ms", 5000),
                      "isolated": True, "network": False, "max_memory_mb": 128}},

    {"name": "code_translate", "description": "Translate code from one language to another.",
     "params": {"code": "str", "source_lang": "str", "target_lang": "str"},
     "run": lambda a: {"source": a.get("source_lang", "python"), "target": a.get("target_lang", "javascript"),
                      "translated": "// Translated code placeholder", "supported": _supported_languages()}},

    {"name": "code_profiler", "description": "Profile code performance and report hotspots.",
     "params": {"code": "str", "language": "str", "runs": "int"},
     "run": lambda a: {"language": a.get("language", "python"), "runs": a.get("runs", 100),
                      "hotspots": [{"function": "main", "time_ms": 45.2, "calls": 100},
                                   {"function": "helper", "time_ms": 12.1, "calls": 500}],
                      "total_time_ms": 57.3}},

    {"name": "code_complexity_score", "description": "Calculate cyclomatic complexity and maintainability score.",
     "params": {"code": "str", "file": "str"},
     "run": lambda a: {"cyclomatic": _cyclomatic(a.get("code", "")),
                      "lines": len((a.get("code", "") or "").splitlines()),
                      "functions": _count_functions(a.get("code", "")),
                      "maintainability": max(0, 100 - _cyclomatic(a.get("code", "")) * 5), "file": a.get("file", "unknown")}},

    {"name": "code_arch_diagram", "description": "Generate an architecture diagram description from module relationships.",
     "params": {"modules": "list[dict]", "format": "str"},
     "run": lambda a: {"format": a.get("format", "mermaid"),
                      "diagram": "graph TD\n" + "\n".join(
                          f"  {m.get('name', f'mod{i}')} --> {(m.get('deps', ['core']) or ['core'])[0]}"
                          for i, m in enumerate(a.get("modules", []))),
                      "module_count": len(a.get("modules", []))}},

    {"name": "code_terminal_explain", "description": "Explain a terminal command in plain English.",
     "params": {"command": "str", "shell": "str"},
     "run": lambda a: {"command": a.get("command", ""), "shell": a.get("shell", "bash"),
                      "explanation": "Breakdown of the command and its flags.",
                      "safe": "rm" not in a.get("command", "")}},

    {"name": "code_env_setup", "description": "Generate environment setup instructions for a project.",
     "params": {"language": "str", "project_dir": "str", "packages": "list[str]"},
     "run": lambda a: {"language": a.get("language", "python"),
                      "packages": a.get("packages", []) or _env_packages(a.get("language", "python")),
                      "steps": ["install_runtime", "create_venv", "install_deps", "verify"],
                      "project_dir": a.get("project_dir", ".")}},

    {"name": "code_snapshot", "description": "Create a snapshot/hash of code state for comparison or rollback.",
     "params": {"files": "dict", "label": "str"},
     "run": lambda a: {"label": a.get("label", "snapshot"),
                      "files": {path: _hash_file(path, content) for path, content in a.get("files", {}).items()},
                      "file_count": len(a.get("files", {}))}},
]