"""
Code Runner Module - Execute code in multiple languages.
Supports: Python, JavaScript, TypeScript, Bash, Ruby, Go, Rust, Java, C, C++, C#, PHP, Perl, Lua, R, Swift, Kotlin, Scala, Dart, Elixir, Haskell, and more.
"""

import os
import sys
import time
import tempfile
import subprocess
from pathlib import Path
from typing import Optional, List, Dict, Any, Callable
from dataclasses import dataclass

from .utils import (
    ExecutionResult, log, LogLevel, console, print_code, 
    spinner, run_command, print_table
)


@dataclass
class LanguageConfig:
    """Configuration for a programming language."""
    name: str
    extensions: List[str]
    command: str
    args: List[str]
    env_vars: Dict[str, str] = None
    file_extension: str = ""
    needs_file: bool = True
    interpreter: bool = True
    
    def __post_init__(self):
        if self.env_vars is None:
            self.env_vars = {}


# Language definitions
LANGUAGES = {
    "python": LanguageConfig(
        name="Python",
        extensions=[".py", ".pyw", ".pyi"],
        command="python3",
        args=[],
        file_extension=".py",
        needs_file=True,
    ),
    "python2": LanguageConfig(
        name="Python 2",
        extensions=[".py2"],
        command="python2",
        args=[],
        file_extension=".py",
        needs_file=True,
    ),
    "javascript": LanguageConfig(
        name="JavaScript",
        extensions=[".js", ".mjs", ".cjs"],
        command="node",
        args=[],
        file_extension=".js",
        needs_file=True,
    ),
    "typescript": LanguageConfig(
        name="TypeScript",
        extensions=[".ts", ".tsx", ".mts"],
        command="npx",
        args=["tsx"],
        file_extension=".ts",
        needs_file=True,
    ),
    "bash": LanguageConfig(
        name="Bash",
        extensions=[".sh", ".bash"],
        command="bash",
        args=["-c"],
        needs_file=False,
    ),
    "sh": LanguageConfig(
        name="Shell",
        extensions=[".sh"],
        command="sh",
        args=["-c"],
        needs_file=False,
    ),
    "zsh": LanguageConfig(
        name="Zsh",
        extensions=[".zsh"],
        command="zsh",
        args=["-c"],
        needs_file=False,
    ),
    "ruby": LanguageConfig(
        name="Ruby",
        extensions=[".rb", ".rbw"],
        command="ruby",
        args=[],
        file_extension=".rb",
        needs_file=True,
    ),
    "go": LanguageConfig(
        name="Go",
        extensions=[".go"],
        command="go",
        args=["run"],
        file_extension=".go",
        needs_file=True,
    ),
    "rust": LanguageConfig(
        name="Rust",
        extensions=[".rs"],
        command="rustc",
        args=["--edition", "2021", "-o"],
        file_extension=".rs",
        needs_file=True,
        interpreter=False,
    ),
    "java": LanguageConfig(
        name="Java",
        extensions=[".java"],
        command="java",
        args=[],
        file_extension=".java",
        needs_file=True,
        interpreter=False,
    ),
    "cpp": LanguageConfig(
        name="C++",
        extensions=[".cpp", ".cc", ".cxx", ".c++"],
        command="g++",
        args=["-std=c++20", "-O2", "-o"],
        file_extension=".cpp",
        needs_file=True,
        interpreter=False,
    ),
    "c": LanguageConfig(
        name="C",
        extensions=[".c", ".h"],
        command="gcc",
        args=["-std=c11", "-O2", "-o"],
        file_extension=".c",
        needs_file=True,
        interpreter=False,
    ),
    "csharp": LanguageConfig(
        name="C#",
        extensions=[".cs"],
        command="dotnet",
        args=["run"],
        file_extension=".cs",
        needs_file=True,
        interpreter=False,
    ),
    "php": LanguageConfig(
        name="PHP",
        extensions=[".php"],
        command="php",
        args=[],
        file_extension=".php",
        needs_file=True,
    ),
    "perl": LanguageConfig(
        name="Perl",
        extensions=[".pl", ".pm"],
        command="perl",
        args=[],
        file_extension=".pl",
        needs_file=True,
    ),
    "lua": LanguageConfig(
        name="Lua",
        extensions=[".lua"],
        command="lua",
        args=[],
        file_extension=".lua",
        needs_file=True,
    ),
    "r": LanguageConfig(
        name="R",
        extensions=[".r", ".R"],
        command="Rscript",
        args=[],
        file_extension=".R",
        needs_file=True,
    ),
    "swift": LanguageConfig(
        name="Swift",
        extensions=[".swift"],
        command="swift",
        args=[],
        file_extension=".swift",
        needs_file=True,
    ),
    "kotlin": LanguageConfig(
        name="Kotlin",
        extensions=[".kt", ".kts"],
        command="kotlin",
        args=[],
        file_extension=".kt",
        needs_file=True,
    ),
    "scala": LanguageConfig(
        name="Scala",
        extensions=[".scala", ".sc"],
        command="scala",
        args=[],
        file_extension=".scala",
        needs_file=True,
    ),
    "dart": LanguageConfig(
        name="Dart",
        extensions=[".dart"],
        command="dart",
        args=["run"],
        file_extension=".dart",
        needs_file=True,
    ),
    "elixir": LanguageConfig(
        name="Elixir",
        extensions=[".ex", ".exs"],
        command="elixir",
        args=[],
        file_extension=".exs",
        needs_file=True,
    ),
    "haskell": LanguageConfig(
        name="Haskell",
        extensions=[".hs", ".lhs"],
        command="runhaskell",
        args=[],
        file_extension=".hs",
        needs_file=True,
    ),
    "clojure": LanguageConfig(
        name="Clojure",
        extensions=[".clj", ".cljs", ".cljc"],
        command="clojure",
        args=["-M"],
        file_extension=".clj",
        needs_file=True,
    ),
    "groovy": LanguageConfig(
        name="Groovy",
        extensions=[".groovy", ".gvy"],
        command="groovy",
        args=[],
        file_extension=".groovy",
        needs_file=True,
    ),
    "powershell": LanguageConfig(
        name="PowerShell",
        extensions=[".ps1"],
        command="pwsh",
        args=["-Command"],
        needs_file=False,
    ),
    "sql": LanguageConfig(
        name="SQL",
        extensions=[".sql"],
        command="sqlite3",
        args=[":memory:", "-cmd"],
        file_extension=".sql",
        needs_file=True,
    ),
    "awk": LanguageConfig(
        name="AWK",
        extensions=[".awk"],
        command="awk",
        args=["-f"],
        file_extension=".awk",
        needs_file=True,
    ),
    "sed": LanguageConfig(
        name="Sed",
        extensions=[".sed"],
        command="sed",
        args=["-f"],
        file_extension=".sed",
        needs_file=True,
    ),
    "nim": LanguageConfig(
        name="Nim",
        extensions=[".nim"],
        command="nim",
        args=["r"],
        file_extension=".nim",
        needs_file=True,
    ),
    "crystal": LanguageConfig(
        name="Crystal",
        extensions=[".cr"],
        command="crystal",
        args=["run"],
        file_extension=".cr",
        needs_file=True,
    ),
    "julia": LanguageConfig(
        name="Julia",
        extensions=[".jl"],
        command="julia",
        args=[],
        file_extension=".jl",
        needs_file=True,
    ),
    "erlang": LanguageConfig(
        name="Erlang",
        extensions=[".erl"],
        command="escript",
        args=[],
        file_extension=".erl",
        needs_file=True,
    ),
    "ocaml": LanguageConfig(
        name="OCaml",
        extensions=[".ml"],
        command="ocaml",
        args=[],
        file_extension=".ml",
        needs_file=True,
    ),
    "fortran": LanguageConfig(
        name="Fortran",
        extensions=[".f90", ".f95", ".f03"],
        command="gfortran",
        args=["-o"],
        file_extension=".f90",
        needs_file=True,
        interpreter=False,
    ),
    "pascal": LanguageConfig(
        name="Pascal",
        extensions=[".pas"],
        command="fpc",
        args=["-o"],
        file_extension=".pas",
        needs_file=True,
        interpreter=False,
    ),
    "tcl": LanguageConfig(
        name="Tcl",
        extensions=[".tcl"],
        command="tclsh",
        args=[],
        file_extension=".tcl",
        needs_file=True,
    ),
    "scheme": LanguageConfig(
        name="Scheme",
        extensions=[".scm", ".ss"],
        command="scheme",
        args=[],
        file_extension=".scm",
        needs_file=True,
    ),
    "vhdl": LanguageConfig(
        name="VHDL",
        extensions=[".vhd", ".vhdl"],
        command="ghdl",
        args=["-a", "-e", "-r"],
        file_extension=".vhd",
        needs_file=True,
        interpreter=False,
    ),
    "verilog": LanguageConfig(
        name="Verilog",
        extensions=[".v", ".sv"],
        command="iverilog",
        args=["-o"],
        file_extension=".v",
        needs_file=True,
        interpreter=False,
    ),
}


class CodeRunner:
    """
    Multi-language code execution engine.
    Supports 35+ programming languages with intelligent detection and execution.
    """
    
    def __init__(self):
        self.languages = LANGUAGES
        self._check_cache: Dict[str, bool] = {}
    
    def list_languages(self) -> None:
        """Display all supported languages with availability status."""
        rows = []
        for lang_id, config in sorted(self.languages.items(), key=lambda x: x[0]):
            available = self.check_language(lang_id)
            status = "[green]Available[/]" if available else "[red]Not Found[/]"
            rows.append([
                lang_id,
                config.name,
                ", ".join(config.extensions),
                config.command,
                status
            ])
        
        print_table(
            "Supported Languages (35+)",
            ["ID", "Name", "Extensions", "Command", "Status"],
            rows
        )
    
    def check_language(self, lang_id: str) -> bool:
        """Check if a language runtime is installed."""
        if lang_id in self._check_cache:
            return self._check_cache[lang_id]
        
        if lang_id not in self.languages:
            self._check_cache[lang_id] = False
            return False
        
        config = self.languages[lang_id]
        try:
            result = subprocess.run(
                [config.command, "--version"] if config.command not in ["npx", "dotnet"] else [config.command, "--version"],
                capture_output=True,
                timeout=10,
                text=True
            )
            self._check_cache[lang_id] = result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            self._check_cache[lang_id] = False
        
        return self._check_cache[lang_id]
    
    def detect_language(self, filepath: str) -> Optional[str]:
        """Auto-detect language from file extension."""
        p = Path(filepath)
        ext = p.suffix.lower()
        
        # Handle compound extensions
        name_lower = p.name.lower()
        if name_lower.endswith(".tar.gz") or name_lower.endswith(".tgz"):
            return None  # Not a code file
        
        for lang_id, config in self.languages.items():
            if ext in [e.lower() for e in config.extensions]:
                return lang_id
        return None
    
    def execute_file(self, filepath: str, args: Optional[List[str]] = None,
                     stdin: Optional[str] = None, timeout: int = 60,
                     env: Optional[Dict[str, str]] = None) -> ExecutionResult:
        """Execute a code file with automatic language detection."""
        filepath = os.path.abspath(filepath)
        
        if not os.path.exists(filepath):
            return ExecutionResult(
                success=False,
                message=f"File not found: {filepath}",
                exit_code=1
            )
        
        lang = self.detect_language(filepath)
        if not lang:
            # Try to run as executable or script
            return self._execute_raw(filepath, args, stdin, timeout, env)
        
        return self._execute_language_file(lang, filepath, args, stdin, timeout, env)
    
    def execute_code(self, language: str, code: str, 
                     args: Optional[List[str]] = None,
                     stdin: Optional[str] = None,
                     timeout: int = 60,
                     env: Optional[Dict[str, str]] = None) -> ExecutionResult:
        """
        Execute code string in specified language.
        
        Args:
            language: Language identifier (python, javascript, etc.)
            code: Source code to execute
            args: Additional command-line arguments
            stdin: Input to pass to the program
            timeout: Maximum execution time in seconds
            env: Additional environment variables
        """
        lang = language.lower()
        
        if lang not in self.languages:
            return ExecutionResult(
                success=False,
                message=f"Unsupported language: {language}. Run 'list' to see supported languages.",
                exit_code=1
            )
        
        config = self.languages[lang]
        
        # Handle languages that need files vs inline execution
        if config.needs_file:
            return self._execute_from_string(lang, code, args, stdin, timeout, env)
        else:
            return self._execute_inline(lang, code, args, stdin, timeout, env)
    
    def _execute_from_string(self, lang: str, code: str,
                             args: Optional[List[str]] = None,
                             stdin: Optional[str] = None,
                             timeout: int = 60,
                             env: Optional[Dict[str, str]] = None) -> ExecutionResult:
        """Execute code by writing to a temporary file first."""
        config = self.languages[lang]
        
        with tempfile.NamedTemporaryFile(
            mode='w', 
            suffix=config.file_extension, 
            delete=False,
            dir=tempfile.gettempdir()
        ) as f:
            f.write(code)
            tmp_path = f.name
        
        try:
            if not config.interpreter:
                return self._compile_and_run(lang, tmp_path, args, stdin, timeout, env)
            return self._execute_language_file(lang, tmp_path, args, stdin, timeout, env)
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
    
    def _execute_language_file(self, lang: str, filepath: str,
                               args: Optional[List[str]] = None,
                               stdin: Optional[str] = None,
                               timeout: int = 60,
                               env: Optional[Dict[str, str]] = None) -> ExecutionResult:
        """Execute a code file for a specific language."""
        config = self.languages[lang]
        
        if not config.interpreter:
            return self._compile_and_run(lang, filepath, args, stdin, timeout, env)
        
        cmd = [config.command] + config.args + [filepath]
        if args:
            cmd.extend(args)
        
        return self._run_with_stdin(cmd, stdin, timeout, env)
    
    def _compile_and_run(self, lang: str, source: str,
                         args: Optional[List[str]] = None,
                         stdin: Optional[str] = None,
                         timeout: int = 60,
                         env: Optional[Dict[str, str]] = None) -> ExecutionResult:
        """Compile and run compiled languages."""
        config = self.languages[lang]
        
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, "output")
            
            # Compile
            if lang in ["rust", "cpp", "c"]:
                compile_cmd = [config.command] + config.args + [output_path, source]
            elif lang == "java":
                compile_cmd = ["javac", "-d", tmpdir, source]
            elif lang == "pascal":
                compile_cmd = [config.command] + config.args + [os.path.join(tmpdir, "output"), source]
            elif lang == "fortran":
                compile_cmd = [config.command] + config.args + [output_path, source]
            else:
                compile_cmd = [config.command] + config.args + [source]
            
            log(LogLevel.INFO, f"Compiling {config.name}...")
            compile_result = run_command(compile_cmd, env=env, timeout=timeout)
            
            if not compile_result.success:
                return ExecutionResult(
                    success=False,
                    message=f"Compilation failed:\n{compile_result.stderr}",
                    stderr=compile_result.stderr,
                    exit_code=compile_result.exit_code,
                    duration_ms=compile_result.duration_ms
                )
            
            # Run
            if lang == "java":
                # Get class name from file
                class_name = Path(source).stem
                run_cmd = ["java", "-cp", tmpdir, class_name]
            elif lang == "pascal":
                run_cmd = [os.path.join(tmpdir, "output")]
            else:
                run_cmd = [output_path]
            
            if args:
                run_cmd.extend(args)
            
            log(LogLevel.INFO, f"Running compiled {config.name}...")
            return self._run_with_stdin(run_cmd, stdin, timeout, env)
    
    def _execute_inline(self, lang: str, code: str,
                        args: Optional[List[str]] = None,
                        stdin: Optional[str] = None,
                        timeout: int = 60,
                        env: Optional[Dict[str, str]] = None) -> ExecutionResult:
        """Execute code inline (for shell languages)."""
        config = self.languages[lang]
        cmd = [config.command] + config.args + [code]
        if args:
            cmd.extend(args)
        return self._run_with_stdin(cmd, stdin, timeout, env)
    
    def _execute_raw(self, filepath: str,
                     args: Optional[List[str]] = None,
                     stdin: Optional[str] = None,
                     timeout: int = 60,
                     env: Optional[Dict[str, str]] = None) -> ExecutionResult:
        """Try to execute a file directly or with shebang."""
        filepath = os.path.abspath(filepath)
        
        # Check for shebang
        try:
            with open(filepath, 'r') as f:
                first_line = f.readline().strip()
            if first_line.startswith("#!/"):
                cmd = [filepath]
                if args:
                    cmd.extend(args)
                os.chmod(filepath, os.stat(filepath).st_mode | 0o111)
                return self._run_with_stdin(cmd, stdin, timeout, env)
        except (IOError, OSError):
            pass
        
        # Try to make executable and run
        try:
            os.chmod(filepath, os.stat(filepath).st_mode | 0o111)
            cmd = [filepath]
            if args:
                cmd.extend(args)
            return self._run_with_stdin(cmd, stdin, timeout, env)
        except OSError:
            return ExecutionResult(
                success=False,
                message=f"Cannot execute {filepath}. Unknown file type or no execute permission.",
                exit_code=1
            )
    
    def _run_with_stdin(self, cmd: List[str], stdin: Optional[str] = None,
                        timeout: int = 60, 
                        env: Optional[Dict[str, str]] = None) -> ExecutionResult:
        """Run a command with optional stdin input."""
        start = time.time()
        try:
            result = subprocess.run(
                cmd,
                input=stdin,
                capture_output=True,
                text=True,
                timeout=timeout,
                env={**os.environ, **(env or {})},
                shell=False
            )
            duration = (time.time() - start) * 1000
            
            return ExecutionResult(
                success=result.returncode == 0,
                message="Execution completed",
                exit_code=result.returncode,
                stdout=result.stdout,
                stderr=result.stderr,
                duration_ms=duration
            )
        except subprocess.TimeoutExpired:
            duration = (time.time() - start) * 1000
            return ExecutionResult(
                success=False,
                message=f"Execution timed out after {timeout}s",
                exit_code=-1,
                duration_ms=duration
            )
        except FileNotFoundError as e:
            duration = (time.time() - start) * 1000
            return ExecutionResult(
                success=False,
                message=f"Command not found: {cmd[0]}",
                stderr=str(e),
                exit_code=-1,
                duration_ms=duration
            )
    
    def run_interactive(self, language: str):
        """Start an interactive REPL session for a language."""
        lang = language.lower()
        if lang not in self.languages:
            log(LogLevel.ERROR, f"Unsupported language: {language}")
            return
        
        config = self.languages[lang]
        log(LogLevel.INFO, f"Starting interactive {config.name} session...")
        log(LogLevel.INFO, "Type 'exit' or press Ctrl+D to quit")
        
        try:
            if config.needs_file and config.interpreter:
                # For interpreted languages, start REPL directly
                cmd = [config.command]
                subprocess.run(cmd)
            else:
                # For others, use our own input loop
                while True:
                    try:
                        line = input(f"{config.name}> ")
                        if line.strip().lower() in ('exit', 'quit', 'q'):
                            break
                        result = self.execute_code(lang, line)
                        if result.stdout:
                            print(result.stdout, end='')
                        if result.stderr:
                            print(result.stderr, end='', file=sys.stderr)
                    except EOFError:
                        break
                    except KeyboardInterrupt:
                        print("\nInterrupted. Type 'exit' to quit.")
        except KeyboardInterrupt:
            log(LogLevel.INFO, "\nSession ended")
