"""
AI Code Analyzer Module - Intelligent code analysis and suggestions.
Provides: static analysis, complexity metrics, code quality assessment,
security vulnerability detection, performance optimization suggestions,
bug prediction, and automated fix recommendations.
"""

import os
import re
import ast
import sys
import math
import tokenize
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple, Set
from dataclasses import dataclass, field
from collections import Counter, defaultdict

from .utils import (
    ExecutionResult, log, LogLevel, console, print_code, 
    print_table, spinner
)


@dataclass
class CodeMetrics:
    """Code complexity and quality metrics."""
    lines_of_code: int = 0
    blank_lines: int = 0
    comment_lines: int = 0
    comment_ratio: float = 0.0
    cyclomatic_complexity: int = 0
    cognitive_complexity: int = 0
    max_nesting_depth: int = 0
    function_count: int = 0
    class_count: int = 0
    average_function_length: float = 0.0
    duplicate_lines: int = 0
    halstead_volume: float = 0.0
    maintainability_index: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "Lines of Code": self.lines_of_code,
            "Blank Lines": self.blank_lines,
            "Comment Lines": self.comment_lines,
            "Comment Ratio": f"{self.comment_ratio:.1%}",
            "Cyclomatic Complexity": self.cyclomatic_complexity,
            "Cognitive Complexity": self.cognitive_complexity,
            "Max Nesting Depth": self.max_nesting_depth,
            "Function Count": self.function_count,
            "Class Count": self.class_count,
            "Avg Function Length": f"{self.average_function_length:.1f} lines",
            "Duplicate Lines": self.duplicate_lines,
            "Halstead Volume": f"{self.halstead_volume:.1f}",
            "Maintainability Index": f"{self.maintainability_index:.1f}",
        }


@dataclass
class Issue:
    """A code issue found during analysis."""
    severity: str  # critical, high, medium, low, info
    category: str  # bug, security, performance, style, best-practice
    message: str
    line: int = 0
    column: int = 0
    code_snippet: str = ""
    suggestion: str = ""
    confidence: float = 1.0  # 0.0 to 1.0
    rule_id: str = ""
    
    def __str__(self):
        return f"[{self.severity.upper()}] Line {self.line}: {self.message}"


@dataclass
class AnalysisResult:
    """Complete code analysis result."""
    filepath: str
    language: str
    metrics: CodeMetrics
    issues: List[Issue]
    summary: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def critical_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == 'critical')
    
    @property
    def high_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == 'high')
    
    @property
    def medium_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == 'medium')
    
    @property
    def low_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == 'low')
    
    @property
    def total_issues(self) -> int:
        return len(self.issues)


class AICodeAnalyzer:
    """
    Intelligent code analyzer with AI-powered suggestions.
    
    Features:
    - Static code analysis (complexity, metrics)
    - Bug pattern detection
    - Security vulnerability scanning
    - Performance optimization suggestions
    - Code quality assessment
    - Best practice recommendations
    - Automated fix suggestions
    """
    
    # Severity colors
    SEVERITY_COLORS = {
        'critical': 'red bold reverse',
        'high': 'red bold',
        'medium': 'yellow',
        'low': 'blue',
        'info': 'dim',
    }
    
    def __init__(self):
        self._pattern_db = self._load_pattern_database()
    
    def analyze_file(self, filepath: str, language: Optional[str] = None) -> AnalysisResult:
        """
        Analyze a source code file.
        
        Args:
            filepath: Path to source file
            language: Language override (auto-detect if None)
        """
        filepath = os.path.abspath(filepath)
        
        if not os.path.exists(filepath):
            return AnalysisResult(
                filepath=filepath,
                language=language or "unknown",
                metrics=CodeMetrics(),
                issues=[Issue('critical', 'bug', f"File not found: {filepath}")]
            )
        
        # Detect language
        if language is None:
            language = self._detect_language(filepath)
        
        # Read source
        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            source = f.read()
        
        log(LogLevel.INFO, f"Analyzing: {filepath} ({language})")
        
        # Calculate metrics
        metrics = self._calculate_metrics(source, language)
        
        # Find issues
        issues = []
        issues.extend(self._find_syntax_errors(source, filepath, language))
        issues.extend(self._find_bug_patterns(source, filepath, language))
        issues.extend(self._find_security_issues(source, filepath, language))
        issues.extend(self._find_performance_issues(source, filepath, language))
        issues.extend(self._find_style_issues(source, filepath, language))
        issues.extend(self._find_best_practice_issues(source, filepath, language))
        
        # Generate summary
        summary = self._generate_summary(metrics, issues)
        
        return AnalysisResult(
            filepath=filepath,
            language=language,
            metrics=metrics,
            issues=sorted(issues, key=lambda x: ['critical', 'high', 'medium', 'low', 'info'].index(x.severity)),
            summary=summary
        )
    
    def analyze_code(self, code: str, language: str = "python") -> AnalysisResult:
        """Analyze code string directly."""
        # Write to temp file for analysis
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix=f'.{language}', delete=False) as f:
            f.write(code)
            tmp_path = f.name
        
        try:
            return self.analyze_file(tmp_path, language)
        finally:
            os.unlink(tmp_path)
    
    def analyze_directory(self, directory: str, 
                          pattern: str = "*.py") -> List[AnalysisResult]:
        """Analyze all matching files in a directory."""
        results = []
        for filepath in Path(directory).rglob(pattern):
            result = self.analyze_file(str(filepath))
            results.append(result)
        return results
    
    def print_report(self, result: AnalysisResult):
        """Print a formatted analysis report."""
        if console:
            from rich.panel import Panel
            from rich.columns import Columns
            
            # Header
            header = (
                f"[bold]{result.filepath}[/]\n"
                f"Language: {result.language} | "
                f"Issues: {result.total_issues} "
                f"([red]{result.critical_count} critical[/], "
                f"[red]{result.high_count} high[/], "
                f"[yellow]{result.medium_count} medium[/], "
                f"[blue]{result.low_count} low[/])"
            )
            console.print(Panel(header, title="Code Analysis Report", border_style="cyan"))
            
            # Metrics
            console.print("\n[bold]Metrics:[/]")
            metrics_data = [[k, str(v)] for k, v in result.metrics.to_dict().items()]
            print_table("", ["Metric", "Value"], metrics_data)
            
            # Issues
            if result.issues:
                console.print(f"\n[bold]Issues ({result.total_issues}):[/]")
                for issue in result.issues[:50]:  # Limit to 50 issues
                    color = self.SEVERITY_COLORS.get(issue.severity, 'white')
                    severity_emoji = {
                        'critical': '🔴', 'high': '🟠', 'medium': '🟡', 
                        'low': '🔵', 'info': '⚪'
                    }.get(issue.severity, '•')
                    
                    console.print(f"\n[{color}]{severity_emoji} [{issue.severity.upper()}] {issue.category}[/]")
                    console.print(f"   Line {issue.line}: {issue.message}")
                    if issue.code_snippet:
                        console.print(f"   [dim]Code: {issue.code_snippet[:80]}[/]")
                    if issue.suggestion:
                        console.print(f"   [green]→ {issue.suggestion}[/]")
            else:
                console.print("\n[green]No issues found![/]")
            
            # Summary
            if result.summary:
                console.print(f"\n[bold]Assessment:[/] {result.summary.get('assessment', 'N/A')}")
                console.print(f"[bold]Score:[/] {result.summary.get('score', 'N/A')}/100")
        else:
            # Plain text output
            print(f"\n{'='*60}")
            print(f"ANALYSIS: {result.filepath}")
            print(f"{'='*60}")
            print(f"Language: {result.language}")
            print(f"Issues: {result.total_issues}")
            print(f"\nMetrics:")
            for k, v in result.metrics.to_dict().items():
                print(f"  {k}: {v}")
            
            if result.issues:
                print(f"\nIssues:")
                for issue in result.issues:
                    print(f"\n  [{issue.severity.upper()}] {issue.category}")
                    print(f"  Line {issue.line}: {issue.message}")
                    if issue.suggestion:
                        print(f"  -> {issue.suggestion}")
    
    def suggest_fixes(self, result: AnalysisResult) -> List[Dict[str, str]]:
        """Generate automated fix suggestions for found issues."""
        fixes = []
        
        for issue in result.issues:
            if issue.suggestion and issue.code_snippet:
                fixes.append({
                    'line': str(issue.line),
                    'severity': issue.severity,
                    'original': issue.code_snippet,
                    'suggestion': issue.suggestion,
                    'category': issue.category
                })
        
        return fixes
    
    def generate_refactored_code(self, code: str, language: str = "python") -> str:
        """
        Generate refactored version of code with improvements applied.
        This is a basic implementation - can be enhanced with LLM integration.
        """
        lines = code.split('\n')
        modified = list(lines)
        
        # Apply common Python refactorings
        if language == "python":
            for i, line in enumerate(lines):
                # Replace list comprehensions with generator expressions where appropriate
                if 'sum([' in line and 'for' in line:
                    modified[i] = line.replace('sum([', 'sum(').replace('])', ')')
                
                # Use f-strings instead of % formatting
                if '%s' in line and '"' in line:
                    # Basic f-string conversion attempt
                    pass
                
                # Use dict.get() instead of KeyError handling
                if 'try:' in line and i + 2 < len(lines):
                    next_lines = '\n'.join(lines[i:i+3])
                    if 'KeyError' in next_lines:
                        modified[i] = f"# TODO: Consider using dict.get() instead of try/except for KeyError"
        
        return '\n'.join(modified)
    
    def _detect_language(self, filepath: str) -> str:
        """Detect programming language from file extension."""
        ext = Path(filepath).suffix.lower()
        lang_map = {
            '.py': 'python', '.js': 'javascript', '.ts': 'typescript',
            '.java': 'java', '.c': 'c', '.cpp': 'cpp', '.h': 'c',
            '.hpp': 'cpp', '.go': 'go', '.rs': 'rust', '.rb': 'ruby',
            '.php': 'php', '.sh': 'bash', '.pl': 'perl', '.lua': 'lua',
            '.r': 'r', '.swift': 'swift', '.kt': 'kotlin', '.scala': 'scala',
            '.dart': 'dart', '.hs': 'haskell', '.ex': 'elixir', '.exs': 'elixir',
            '.clj': 'clojure', '.cs': 'csharp', '.fs': 'fsharp',
            '.m': 'objective-c', '.mm': 'objective-cpp', '.scala': 'scala',
        }
        return lang_map.get(ext, 'unknown')
    
    def _calculate_metrics(self, source: str, language: str) -> CodeMetrics:
        """Calculate code complexity metrics."""
        metrics = CodeMetrics()
        lines = source.split('\n')
        
        metrics.lines_of_code = len(lines)
        metrics.blank_lines = sum(1 for l in lines if not l.strip())
        metrics.comment_lines = sum(1 for l in lines if l.strip().startswith('#'))
        
        if metrics.lines_of_code > 0:
            metrics.comment_ratio = metrics.comment_lines / metrics.lines_of_code
        
        # Python-specific AST analysis
        if language == 'python':
            try:
                tree = ast.parse(source)
                metrics = self._analyze_python_ast(tree, source, metrics)
            except SyntaxError as e:
                log(LogLevel.WARNING, f"Syntax error in metrics calculation: {e}")
        
        # Calculate Halstead metrics (simplified)
        operators = len(re.findall(r'[+\-*/%=<>!&|^~]+|\b(and|or|not|in|is)\b', source))
        operands = len(re.findall(r'\b[a-zA-Z_]\w*\b', source))
        if operands > 0:
            metrics.halstead_volume = (operators + operands) * math.log2(max(operands, 1))
        
        # Maintainability Index (simplified Microsoft formula)
        if metrics.lines_of_code > 0:
            mi = 171 - 5.2 * math.log(metrics.halstead_volume + 1) - 0.23 * metrics.cyclomatic_complexity - 16.2 * math.log(metrics.lines_of_code)
            metrics.maintainability_index = max(0, mi)
        
        return metrics
    
    def _analyze_python_ast(self, tree: ast.AST, source: str, metrics: CodeMetrics) -> CodeMetrics:
        """Analyze Python AST for detailed metrics."""
        class_counts = 0
        function_counts = 0
        function_lengths = []
        max_depth = 0
        complexity = 0
        
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                class_counts += 1
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                function_counts += 1
                func_len = node.end_lineno - node.lineno if node.end_lineno else 0
                function_lengths.append(func_len)
                complexity += self._calculate_node_complexity(node)
            
            # Track nesting depth
            depth = 0
            current = node
            while hasattr(current, 'parent'):
                depth += 1
                current = getattr(current, 'parent', None)
            max_depth = max(max_depth, depth)
        
        metrics.class_count = class_counts
        metrics.function_count = function_counts
        if function_lengths:
            metrics.average_function_length = sum(function_lengths) / len(function_lengths)
        metrics.cyclomatic_complexity = complexity
        metrics.max_nesting_depth = max_depth
        
        # Calculate cognitive complexity (simplified)
        metrics.cognitive_complexity = complexity + max_depth * 2
        
        return metrics
    
    def _calculate_node_complexity(self, node: ast.AST) -> int:
        """Calculate cyclomatic complexity for a node."""
        complexity = 1
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.ExceptHandler)):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1
            elif isinstance(child, ast.comprehension):
                complexity += 1
        return complexity
    
    def _find_syntax_errors(self, source: str, filepath: str, language: str) -> List[Issue]:
        """Find syntax errors in code."""
        issues = []
        
        if language == 'python':
            try:
                ast.parse(source)
            except SyntaxError as e:
                issues.append(Issue(
                    severity='critical',
                    category='bug',
                    message=f"Syntax Error: {e.msg}",
                    line=e.lineno or 0,
                    column=e.offset or 0,
                    code_snippet=e.text.strip() if e.text else "",
                    suggestion="Fix the syntax error before running the code",
                    rule_id='SYNTAX001'
                ))
        
        return issues
    
    def _find_bug_patterns(self, source: str, filepath: str, language: str) -> List[Issue]:
        """Find common bug patterns."""
        issues = []
        lines = source.split('\n')
        
        if language == 'python':
            patterns = {
                r'==\s*(True|False|None)': (
                    'medium', 'bug',
                    "Use 'is' for singleton comparison, not '=='",
                    "Replace '== True' with 'is True' or just the variable"
                ),
                r'except\s*:\s*$': (
                    'high', 'bug',
                    "Bare except: catches KeyboardInterrupt and SystemExit",
                    "Use 'except Exception:' instead of bare 'except:'"
                ),
                r'\.has_key\s*\(': (
                    'medium', 'bug',
                    "dict.has_key() is deprecated, use 'in' operator",
                    "Replace 'd.has_key(k)' with 'k in d'"
                ),
                r'\b(input|raw_input)\s*\(': (
                    'low', 'security',
                    "input() can be unsafe. Consider using a safer alternative",
                    "Use a validation library or sanitize input"
                ),
                r'while\s+True\s*:': (
                    'low', 'best-practice',
                    "Infinite loop - ensure there's a break condition",
                    "Add proper exit condition or use a for loop"
                ),
                r'open\([^)]*\)[^\n]*$': (
                    'medium', 'bug',
                    "File handle not closed - potential resource leak",
                    "Use 'with open(...) as f:' context manager"
                ),
                r'\blist\s*\(\s*\)': (
                    'low', 'performance',
                    "Use '[]' instead of 'list()' for empty lists",
                    "Replace 'list()' with '[]'"
                ),
                r'\bdict\s*\(\s*\)': (
                    'low', 'performance',
                    "Use '{}' instead of 'dict()' for empty dicts",
                    "Replace 'dict()' with '{}'"
                ),
                r'==\s*\[\s*\]': (
                    'medium', 'bug',
                    "Comparing to empty list creates a new list each time",
                    "Use 'if not seq:' instead of 'seq == []'"
                ),
                r'==\s*\{\s*\}': (
                    'medium', 'bug',
                    "Comparing to empty dict creates a new dict each time",
                    "Use 'if not d:' instead of 'd == {}'"
                ),
                r'range\s*\(\s*0\s*,\s*len\s*\(': (
                    'low', 'best-practice',
                    "Consider using enumerate() instead of range(len())",
                    "Use 'for i, item in enumerate(seq):'"
                ),
                r'\.format\s*\([^)]*\)': (
                    'info', 'best-practice',
                    "Consider using f-strings for better readability",
                    "Replace '.format()' with f-string"
                ),
                r'os\.system\s*\(': (
                    'high', 'security',
                    "os.system() is insecure - use subprocess module",
                    "Replace os.system() with subprocess.run()"
                ),
                r'subprocess\.call\s*\(.*shell\s*=\s*True': (
                    'high', 'security',
                    "shell=True can be dangerous with untrusted input",
                    "Avoid shell=True or properly sanitize input"
                ),
                r'yaml\.load\s*\([^)]*\)': (
                    'critical', 'security',
                    "yaml.load() without Loader is unsafe - can execute arbitrary code",
                    "Use yaml.safe_load() instead"
                ),
                r'pickle\.loads?\s*\(': (
                    'high', 'security',
                    "pickle can execute arbitrary code during deserialization",
                    "Use JSON or MessagePack for untrusted data"
                ),
                r'eval\s*\(': (
                    'critical', 'security',
                    "eval() executes arbitrary code - extremely dangerous",
                    "Use ast.literal_eval() for safe evaluation"
                ),
                r'exec\s*\(': (
                    'critical', 'security',
                    "exec() executes arbitrary code - extremely dangerous",
                    "Find a safer alternative for your use case"
                ),
                r'__import__\s*\(': (
                    'high', 'security',
                    "Dynamic imports can be used for code injection",
                    "Use importlib.import_module() with validation"
                ),
                r'sql\s*=.*%\s*\w+': (
                    'critical', 'security',
                    "String formatting in SQL - SQL injection vulnerability",
                    "Use parameterized queries with placeholders"
                ),
                r'\.execute\s*\(.*\+': (
                    'critical', 'security',
                    "String concatenation in SQL execute - SQL injection risk",
                    "Use parameterized queries: cursor.execute(query, params)"
                ),
                r'return\s+\[\s*\]\s*$': (
                    'low', 'bug',
                    "Returning mutable default - can cause unexpected behavior",
                    "Return None or use a sentinel value"
                ),
                r'def\s+\w+\s*\([^)]*=\s*\[\s*\]': (
                    'high', 'bug',
                    "Mutable default argument - shared across all calls",
                    "Use 'arg=None' and set to [] inside function"
                ),
                r'def\s+\w+\s*\([^)]*=\s*\{\s*\}': (
                    'high', 'bug',
                    "Mutable default argument (dict) - shared across all calls",
                    "Use 'arg=None' and set to {} inside function"
                ),
                r'\blen\s*\(\s*\w+\s*\)\s*>\s*0\b': (
                    'low', 'best-practice',
                    "Use truthiness check instead of len() > 0",
                    "Replace 'len(x) > 0' with just 'x'"
                ),
                r'\blen\s*\(\s*\w+\s*\)\s*==\s*0\b': (
                    'low', 'best-practice',
                    "Use truthiness check instead of len() == 0",
                    "Replace 'len(x) == 0' with 'not x'"
                ),
            }
            
            for i, line in enumerate(lines, 1):
                for pattern, (severity, category, message, suggestion) in patterns.items():
                    if re.search(pattern, line):
                        issues.append(Issue(
                            severity=severity,
                            category=category,
                            message=message,
                            line=i,
                            code_snippet=line.strip(),
                            suggestion=suggestion,
                            rule_id=f"BUG{len(issues):03d}"
                        ))
        
        return issues
    
    def _find_security_issues(self, source: str, filepath: str, language: str) -> List[Issue]:
        """Find security vulnerabilities."""
        issues = []
        
        # Many security issues are caught in bug patterns
        # Add language-specific security checks here
        
        if language == 'python':
            # Check for hardcoded secrets
            secret_patterns = [
                (r'(?:password|passwd|pwd|secret|token|key|api_key)\s*=\s*["\'][^"\']+["\']', 
                 'high', 'Hardcoded credential detected'),
                (r'AWS_ACCESS_KEY_ID\s*=\s*["\']?AKIA',
                 'critical', 'Hardcoded AWS access key'),
                (r'private_key|rsa_key|ssh_key\s*=',
                 'critical', 'Potential private key in source code'),
            ]
            
            lines = source.split('\n')
            for i, line in enumerate(lines, 1):
                for pattern, severity, message in secret_patterns:
                    if re.search(pattern, line, re.IGNORECASE):
                        issues.append(Issue(
                            severity=severity,
                            category='security',
                            message=message,
                            line=i,
                            code_snippet=line.strip()[:50],
                            suggestion="Use environment variables or a secrets manager",
                            rule_id='SEC001'
                        ))
        
        return issues
    
    def _find_performance_issues(self, source: str, filepath: str, language: str) -> List[Issue]:
        """Find performance issues."""
        issues = []
        
        if language == 'python':
            lines = source.split('\n')
            
            # Check for inefficient patterns
            for i, line in enumerate(lines, 1):
                # List concatenation in loop
                if re.search(r'\w+\s*=\s*\w+\s*\+\s*\[', line):
                    issues.append(Issue(
                        severity='low',
                        category='performance',
                        message="List concatenation in loop is O(n²)",
                        line=i,
                        code_snippet=line.strip(),
                        suggestion="Use list.append() or list.extend() instead",
                        rule_id='PERF001'
                    ))
                
                # String concatenation in loop
                if re.search(r'\w+\s*\+=\s*["\']', line):
                    issues.append(Issue(
                        severity='low',
                        category='performance',
                        message="String concatenation - consider using join()",
                        line=i,
                        code_snippet=line.strip(),
                        suggestion="Use '\n'.join(list) or f-string formatting",
                        rule_id='PERF002'
                    ))
                
                # Inefficient membership test
                if re.search(r'x\s+in\s+list\s*\(', line):
                    issues.append(Issue(
                        severity='medium',
                        category='performance',
                        message="O(n) list membership test - use a set for O(1)",
                        line=i,
                        code_snippet=line.strip(),
                        suggestion="Convert to set: 'x in my_set'",
                        rule_id='PERF003'
                    ))
        
        return issues
    
    def _find_style_issues(self, source: str, filepath: str, language: str) -> List[Issue]:
        """Find style issues."""
        issues = []
        
        if language == 'python':
            lines = source.split('\n')
            
            for i, line in enumerate(lines, 1):
                # Line too long
                if len(line) > 120:
                    issues.append(Issue(
                        severity='low',
                        category='style',
                        message=f"Line too long ({len(line)} > 120 characters)",
                        line=i,
                        code_snippet=line[:80] + "...",
                        suggestion="Break line into multiple lines or use parentheses",
                        rule_id='STYLE001'
                    ))
                
                # Trailing whitespace
                if line.rstrip() != line and line.strip():
                    issues.append(Issue(
                        severity='info',
                        category='style',
                        message="Trailing whitespace",
                        line=i,
                        suggestion="Remove trailing spaces",
                        rule_id='STYLE002'
                    ))
                
                # Mixed tabs and spaces
                if '\t' in line and '    ' in line:
                    issues.append(Issue(
                        severity='low',
                        category='style',
                        message="Mixed tabs and spaces",
                        line=i,
                        suggestion="Use spaces (4) consistently for indentation",
                        rule_id='STYLE003'
                    ))
        
        return issues
    
    def _find_best_practice_issues(self, source: str, filepath: str, language: str) -> List[Issue]:
        """Find best practice violations."""
        issues = []
        
        if language == 'python':
            lines = source.split('\n')
            
            # Check for missing docstrings
            try:
                tree = ast.parse(source)
                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.ClassDef, ast.AsyncFunctionDef)):
                        if not ast.get_docstring(node):
                            issues.append(Issue(
                                severity='info',
                                category='best-practice',
                                message=f"Missing docstring for {node.__class__.__name__.lower()} '{node.name}'",
                                line=node.lineno,
                                suggestion=f"Add a docstring to document {node.name}",
                                rule_id='DOC001'
                            ))
            except:
                pass
            
            # Check for TODO/FIXME comments
            for i, line in enumerate(lines, 1):
                if 'TODO' in line.upper() or 'FIXME' in line.upper() or 'HACK' in line.upper():
                    issues.append(Issue(
                        severity='info',
                        category='best-practice',
                        message=f"Found {re.search(r'TODO|FIXME|HACK', line, re.I).group().upper()} comment",
                        line=i,
                        code_snippet=line.strip(),
                        suggestion="Address the TODO before merging to production",
                        rule_id='TODO001'
                    ))
            
            # Check shebang
            if lines and not lines[0].startswith('#!'):
                if any('def main' in l or 'if __name__' in l for l in lines[:10]):
                    issues.append(Issue(
                        severity='info',
                        category='best-practice',
                        message="Script missing shebang line",
                        line=1,
                        suggestion="Add '#!/usr/bin/env python3' as the first line",
                        rule_id='SHEB001'
                    ))
        
        return issues
    
    def _generate_summary(self, metrics: CodeMetrics, issues: List[Issue]) -> Dict[str, Any]:
        """Generate analysis summary."""
        severity_counts = Counter(i.severity for i in issues)
        category_counts = Counter(i.category for i in issues)
        
        # Calculate quality score (0-100)
        score = 100
        score -= severity_counts['critical'] * 20
        score -= severity_counts['high'] * 10
        score -= severity_counts['medium'] * 5
        score -= severity_counts['low'] * 2
        score -= severity_counts['info'] * 0.5
        
        # Complexity penalty
        if metrics.cyclomatic_complexity > 10:
            score -= (metrics.cyclomatic_complexity - 10) * 2
        if metrics.max_nesting_depth > 4:
            score -= (metrics.max_nesting_depth - 4) * 5
        
        score = max(0, min(100, score))
        
        # Assessment
        if score >= 90:
            assessment = "Excellent - Production ready"
        elif score >= 75:
            assessment = "Good - Minor improvements needed"
        elif score >= 60:
            assessment = "Fair - Several issues to address"
        elif score >= 40:
            assessment = "Poor - Significant refactoring needed"
        else:
            assessment = "Critical - Major rework required"
        
        return {
            'score': round(score, 1),
            'assessment': assessment,
            'severity_distribution': dict(severity_counts),
            'category_distribution': dict(category_counts),
        }
    
    def _load_pattern_database(self) -> Dict[str, Any]:
        """Load the bug pattern database."""
        # This can be expanded with more sophisticated pattern matching
        return {
            'python': {
                'anti_patterns': [
                    'mutable_defaults',
                    'bare_except',
                    'sql_injection',
                    'hardcoded_secrets',
                ]
            }
        }
