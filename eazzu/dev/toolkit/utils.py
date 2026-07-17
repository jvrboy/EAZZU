"""
Utility functions and shared components for DevToolkit.
"""

import os
import sys
import time
import subprocess
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from contextlib import contextmanager
from dataclasses import dataclass
from enum import Enum

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
    from rich.table import Table
    from rich.syntax import Syntax
    from rich.tree import Tree
    from rich.prompt import Prompt, Confirm
    from rich import box
    HAS_RICH = True
except ImportError:
    HAS_RICH = False

# Global console for rich output
console = Console(color_system="auto", force_terminal=True) if HAS_RICH else None


class LogLevel(Enum):
    DEBUG = "debug"
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class ExecutionResult:
    """Standard result container for all operations."""
    success: bool
    message: str = ""
    data: Any = None
    exit_code: int = 0
    stdout: str = ""
    stderr: str = ""
    duration_ms: float = 0.0
    files_affected: List[str] = None
    
    def __post_init__(self):
        if self.files_affected is None:
            self.files_affected = []


def print_banner():
    """Display the DevToolkit banner."""
    banner = """
╔══════════════════════════════════════════════════════════════════════════╗
║                                                                          ║
║   ██████╗ ███████╗██╗   ██╗████████╗ ██████╗  ██████╗ ██╗     ██╗      ║
║   ██╔══██╗██╔════╝██║   ██║╚══██╔══╝██╔═══██╗██╔═══██╗██║     ██║      ║
║   ██║  ██║█████╗  ██║   ██║   ██║   ██║   ██║██║   ██║██║     ██║      ║
║   ██║  ██║██╔══╝  ╚██╗ ██╔╝   ██║   ██║   ██║██║   ██║██║     ██║      ║
║   ██████╔╝███████╗ ╚████╔╝    ██║   ╚██████╔╝╚██████╔╝███████╗██║      ║
║   ╚═════╝ ╚══════╝  ╚═══╝     ╚═╝    ╚═════╝  ╚═════╝ ╚══════╝╚═╝      ║
║                                                                          ║
║      All-in-One Code Interpreter | Runner | Debugger | Extractor         ║
║                      v2.0.0 | Professional Grade                         ║
║                                                                          ║
╚══════════════════════════════════════════════════════════════════════════╝
    """
    if console:
        console.print(Panel(banner, border_style="cyan", expand=False))
    else:
        print(banner)


def log(level: LogLevel, message: str, detail: str = ""):
    """Unified logging with rich formatting."""
    colors = {
        LogLevel.DEBUG: "dim",
        LogLevel.INFO: "blue",
        LogLevel.SUCCESS: "green",
        LogLevel.WARNING: "yellow",
        LogLevel.ERROR: "red bold",
        LogLevel.CRITICAL: "red bold reverse",
    }
    icons = {
        LogLevel.DEBUG: "[DEBUG]",
        LogLevel.INFO: "[INFO]",
        LogLevel.SUCCESS: "[OK]",
        LogLevel.WARNING: "[!]",
        LogLevel.ERROR: "[ERROR]",
        LogLevel.CRITICAL: "[CRITICAL]",
    }
    
    if console:
        style = colors.get(level, "white")
        icon = icons.get(level, "[*]")
        console.print(f"[{style}]{icon}[/{style}] {message}")
        if detail:
            console.print(f"    {detail}", style="dim")
    else:
        print(f"{icons.get(level, '[*]')} {message}")
        if detail:
            print(f"    {detail}")


def print_table(title: str, columns: List[str], rows: List[List[str]], 
                column_styles: Optional[List[str]] = None):
    """Print a formatted table."""
    if not console:
        print(f"\n=== {title} ===")
        for row in rows:
            print("  |  ".join(row))
        return
    
    table = Table(title=title, box=box.ROUNDED, show_header=True, header_style="bold magenta")
    for i, col in enumerate(columns):
        style = column_styles[i] if column_styles and i < len(column_styles) else None
        table.add_column(col, style=style)
    for row in rows:
        table.add_row(*row)
    console.print(table)


def print_code(content: str, language: str = "python", line_numbers: bool = True, 
               title: Optional[str] = None):
    """Display syntax-highlighted code."""
    if console:
        syntax = Syntax(content, language, theme="monokai", line_numbers=line_numbers,
                       word_wrap=True)
        if title:
            console.print(Panel(syntax, title=title, border_style="green"))
        else:
            console.print(syntax)
    else:
        print(f"\n--- {language} code ---")
        print(content)


@contextmanager
def spinner(message: str):
    """Context manager for showing a spinner during long operations."""
    if console:
        with console.status(f"[bold cyan]{message}...", spinner="dots"):
            yield
    else:
        print(f"{message}...", end=" ", flush=True)
        try:
            yield
        finally:
            print("Done")


def run_command(cmd: List[str], cwd: Optional[str] = None, 
                env: Optional[Dict[str, str]] = None,
                timeout: Optional[int] = 60,
                capture_output: bool = True) -> ExecutionResult:
    """Execute a shell command with proper error handling."""
    start = time.time()
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            env={**os.environ, **(env or {})},
            capture_output=capture_output,
            text=True,
            timeout=timeout,
            shell=False
        )
        duration = (time.time() - start) * 1000
        return ExecutionResult(
            success=result.returncode == 0,
            message="Command executed successfully" if result.returncode == 0 else "Command failed",
            exit_code=result.returncode,
            stdout=result.stdout,
            stderr=result.stderr,
            duration_ms=duration
        )
    except subprocess.TimeoutExpired:
        return ExecutionResult(
            success=False,
            message=f"Command timed out after {timeout}s",
            exit_code=-1,
            duration_ms=(time.time() - start) * 1000
        )
    except FileNotFoundError as e:
        return ExecutionResult(
            success=False,
            message=f"Command not found: {cmd[0]}",
            stderr=str(e),
            exit_code=-1,
            duration_ms=(time.time() - start) * 1000
        )
    except Exception as e:
        return ExecutionResult(
            success=False,
            message=f"Execution error: {str(e)}",
            stderr=str(e),
            exit_code=-1,
            duration_ms=(time.time() - start) * 1000
        )


def ensure_dir(path: str) -> Path:
    """Ensure directory exists, create if not."""
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def format_size(size_bytes: int) -> str:
    """Format byte size to human readable."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} PB"


def format_duration(ms: float) -> str:
    """Format milliseconds to human readable."""
    if ms < 1000:
        return f"{ms:.0f}ms"
    elif ms < 60000:
        return f"{ms/1000:.1f}s"
    else:
        return f"{ms/60000:.1f}m"


def get_file_info(filepath: str) -> Dict[str, Any]:
    """Get detailed file information."""
    p = Path(filepath)
    if not p.exists():
        return {}
    stat = p.stat()
    return {
        "name": p.name,
        "path": str(p.absolute()),
        "size": format_size(stat.st_size),
        "size_bytes": stat.st_size,
        "created": time.ctime(stat.st_ctime),
        "modified": time.ctime(stat.st_mtime),
        "extension": p.suffix,
        "is_file": p.is_file(),
        "is_dir": p.is_dir(),
    }


def list_archive_formats() -> List[Dict[str, str]]:
    """List all supported archive formats."""
    formats = [
        {"format": "ZIP", "extensions": ".zip", "description": "ZIP archive", "method": "Native"},
        {"format": "TAR", "extensions": ".tar", "description": "TAR archive", "method": "Native"},
        {"format": "TAR.GZ", "extensions": ".tar.gz, .tgz", "description": "Gzip compressed TAR", "method": "Native"},
        {"format": "TAR.BZ2", "extensions": ".tar.bz2, .tbz2", "description": "Bzip2 compressed TAR", "method": "Native"},
        {"format": "TAR.XZ", "extensions": ".tar.xz, .txz", "description": "XZ compressed TAR", "method": "Native"},
        {"format": "TAR.LZMA", "extensions": ".tar.lzma", "description": "LZMA compressed TAR", "method": "Native"},
        {"format": "GZIP", "extensions": ".gz", "description": "Gzip compressed file", "method": "Native"},
        {"format": "BZIP2", "extensions": ".bz2", "description": "Bzip2 compressed file", "method": "Native"},
        {"format": "XZ", "extensions": ".xz", "description": "XZ compressed file", "method": "Native"},
        {"format": "LZMA", "extensions": ".lzma", "description": "LZMA compressed file", "method": "Native"},
        {"format": "7Z", "extensions": ".7z", "description": "7-Zip archive", "method": "py7zr"},
        {"format": "RAR", "extensions": ".rar", "description": "RAR archive", "method": "rarfile"},
        {"format": "CAB", "extensions": ".cab", "description": "Microsoft Cabinet", "method": "cabarchive"},
        {"format": "ISO", "extensions": ".iso", "description": "ISO 9660 disk image", "method": "pycdlib"},
        {"format": "DMG", "extensions": ".dmg", "description": "Apple Disk Image", "method": "7z fallback"},
        {"format": "DEB", "extensions": ".deb", "description": "Debian package", "method": "ar + tar"},
        {"format": "RPM", "extensions": ".rpm", "description": "RPM package", "method": "rpmfile"},
        {"format": "WHL", "extensions": ".whl", "description": "Python wheel", "method": "ZIP fallback"},
        {"format": "JAR", "extensions": ".jar, .war, .ear", "description": "Java archive", "method": "ZIP fallback"},
        {"format": "APK", "extensions": ".apk", "description": "Android package", "method": "ZIP fallback"},
        {"format": "EPUB", "extensions": ".epub", "description": "E-book archive", "method": "ZIP fallback"},
        {"format": "DOCX", "extensions": ".docx, .xlsx, .pptx", "description": "Office Open XML", "method": "ZIP fallback"},
    ]
    return formats


class Colors:
    """ANSI color codes for terminals without rich."""
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    END = '\033[0m'
    BOLD = '\033[1m'
