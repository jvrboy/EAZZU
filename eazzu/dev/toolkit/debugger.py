"""
Code Debugger Module - Intelligent debugging and error analysis.
Provides: stack trace parsing, variable inspection, breakpoint management,
step-through debugging, and AI-assisted error diagnosis.
"""

import os
import re
import sys
import traceback
import inspect
import linecache
from pathlib import Path
from typing import Optional, List, Dict, Any, Callable, Tuple
from dataclasses import dataclass, field
from enum import Enum

from .utils import (
    ExecutionResult, log, LogLevel, console, print_code, print_table
)


class BreakpointType(Enum):
    LINE = "line"
    FUNCTION = "function"
    CONDITIONAL = "conditional"
    EXCEPTION = "exception"


@dataclass
class Breakpoint:
    """Represents a debugger breakpoint."""
    id: int
    file: str
    line: Optional[int] = None
    function: Optional[str] = None
    condition: Optional[str] = None
    hit_count: int = 0
    enabled: bool = True
    bp_type: BreakpointType = BreakpointType.LINE
    
    def __str__(self):
        status = "enabled" if self.enabled else "disabled"
        if self.bp_type == BreakpointType.LINE:
            return f"#{self.id} {self.file}:{self.line} ({status})"
        elif self.bp_type == BreakpointType.FUNCTION:
            return f"#{self.id} {self.file}::{self.function} ({status})"
        elif self.bp_type == BreakpointType.CONDITIONAL:
            return f"#{self.id} {self.file}:{self.line} when {self.condition} ({status})"
        return f"#{self.id} ({status})"


@dataclass
class StackFrame:
    """Represents a single frame in the call stack."""
    filename: str
    lineno: int
    function: str
    code_context: Optional[str] = None
    locals: Dict[str, str] = field(default_factory=dict)
    globals: Dict[str, str] = field(default_factory=dict)
    
    def __str__(self):
        ctx = f" -> {self.code_context.strip()}" if self.code_context else ""
        return f"  File {self.filename}, line {self.lineno}, in {self.function}{ctx}"


@dataclass
class ExceptionInfo:
    """Detailed exception information."""
    exception_type: str
    message: str
    traceback_frames: List[StackFrame]
    cause: Optional[str] = None
    suggestions: List[str] = field(default_factory=list)
    
    def format(self) -> str:
        lines = [
            f"Exception Type: {self.exception_type}",
            f"Message: {self.message}",
            "Traceback (most recent call last):",
        ]
        for frame in self.traceback_frames:
            lines.append(str(frame))
        if self.cause:
            lines.append(f"Caused by: {self.cause}")
        if self.suggestions:
            lines.append("\nSuggestions:")
            for s in self.suggestions:
                lines.append(f"  - {s}")
        return "\n".join(lines)


class CodeDebugger:
    """
    Advanced code debugger with intelligent error analysis.
    
    Features:
    - Stack trace parsing and visualization
    - Variable inspection and watch expressions
    - Breakpoint management
    - Step-through debugging (step in/over/out)
    - Post-mortem debugging
    - Exception analysis with suggestions
    """
    
    def __init__(self):
        self.breakpoints: Dict[int, Breakpoint] = {}
        self._bp_counter = 0
        self._watch_expressions: List[str] = []
        self._current_frame = None
        self._call_stack: List[StackFrame] = []
        self._step_mode = None  # 'in', 'over', 'out'
        self._step_depth = 0
    
    def set_breakpoint(self, file: str, line: int, 
                       condition: Optional[str] = None) -> Breakpoint:
        """Set a breakpoint at a specific line."""
        self._bp_counter += 1
        bp_type = BreakpointType.CONDITIONAL if condition else BreakpointType.LINE
        bp = Breakpoint(
            id=self._bp_counter,
            file=os.path.abspath(file),
            line=line,
            condition=condition,
            bp_type=bp_type
        )
        self.breakpoints[self._bp_counter] = bp
        log(LogLevel.SUCCESS, f"Breakpoint set: {bp}")
        return bp
    
    def set_function_breakpoint(self, file: str, function: str) -> Breakpoint:
        """Set a breakpoint on a function."""
        self._bp_counter += 1
        bp = Breakpoint(
            id=self._bp_counter,
            file=os.path.abspath(file),
            function=function,
            bp_type=BreakpointType.FUNCTION
        )
        self.breakpoints[self._bp_counter] = bp
        log(LogLevel.SUCCESS, f"Function breakpoint set: {bp}")
        return bp
    
    def remove_breakpoint(self, bp_id: int) -> bool:
        """Remove a breakpoint by ID."""
        if bp_id in self.breakpoints:
            bp = self.breakpoints.pop(bp_id)
            log(LogLevel.INFO, f"Removed breakpoint: {bp}")
            return True
        log(LogLevel.WARNING, f"Breakpoint #{bp_id} not found")
        return False
    
    def list_breakpoints(self):
        """Display all breakpoints."""
        if not self.breakpoints:
            log(LogLevel.INFO, "No breakpoints set")
            return
        
        rows = []
        for bp in self.breakpoints.values():
            rows.append([
                str(bp.id),
                bp.bp_type.value,
                bp.file,
                str(bp.line or ""),
                bp.function or "",
                bp.condition or "",
                str(bp.hit_count),
                "Yes" if bp.enabled else "No"
            ])
        
        print_table(
            "Breakpoints",
            ["ID", "Type", "File", "Line", "Function", "Condition", "Hits", "Enabled"],
            rows
        )
    
    def add_watch(self, expression: str):
        """Add a watch expression."""
        self._watch_expressions.append(expression)
        log(LogLevel.SUCCESS, f"Watch added: {expression}")
    
    def remove_watch(self, expression: str):
        """Remove a watch expression."""
        if expression in self._watch_expressions:
            self._watch_expressions.remove(expression)
            log(LogLevel.SUCCESS, f"Watch removed: {expression}")
    
    def analyze_exception(self, exc_info=None) -> ExceptionInfo:
        """
        Analyze an exception and provide detailed information with suggestions.
        
        Args:
            exc_info: sys.exc_info() tuple. Uses current exception if None.
        """
        if exc_info is None:
            exc_info = sys.exc_info()
        
        exc_type, exc_value, exc_tb = exc_info
        
        if exc_type is None:
            return ExceptionInfo("None", "No active exception", [])
        
        # Parse traceback frames
        frames = []
        tb = exc_tb
        while tb is not None:
            frame = tb.tb_frame
            filename = frame.f_code.co_filename
            lineno = tb.tb_lineno
            function = frame.f_code.co_name
            
            # Get code context
            code_context = None
            try:
                line = linecache.getline(filename, lineno)
                if line:
                    code_context = line.strip()
            except:
                pass
            
            # Get local variables
            locals_dict = {}
            try:
                for name, value in list(frame.f_locals.items())[:20]:
                    try:
                        locals_dict[name] = repr(value)[:100]
                    except:
                        locals_dict[name] = "<unprintable>"
            except:
                pass
            
            frames.append(StackFrame(
                filename=filename,
                lineno=lineno,
                function=function,
                code_context=code_context,
                locals=locals_dict
            ))
            tb = tb.tb_next
        
        # Get exception message
        try:
            message = str(exc_value)
        except:
            message = "<unable to stringify exception>"
        
        # Get cause if any
        cause = None
        if exc_value.__cause__:
            cause = f"{exc_value.__cause__.__class__.__name__}: {exc_value.__cause__}"
        
        # Generate suggestions
        suggestions = self._generate_suggestions(exc_type.__name__, message, frames)
        
        info = ExceptionInfo(
            exception_type=exc_type.__name__,
            message=message,
            traceback_frames=frames,
            cause=cause,
            suggestions=suggestions
        )
        
        return info
    
    def _generate_suggestions(self, exc_type: str, message: str, 
                              frames: List[StackFrame]) -> List[str]:
        """Generate suggestions based on exception type and context."""
        suggestions = []
        
        # Common exception patterns
        patterns = {
            "NameError": [
                "Check that the variable/function name is spelled correctly",
                "Ensure the variable is defined before use",
                "Check if you need to import the name",
                "Verify the scope - is it defined in the current namespace?",
            ],
            "TypeError": [
                "Check the types of all operands/arguments",
                "Ensure you're not mixing incompatible types (e.g., str + int)",
                "Verify function signatures match your call",
                "Check for None values where objects are expected",
            ],
            "ValueError": [
                "Check that input values are in the expected range/format",
                "Verify string formatting arguments match the format spec",
                "Ensure numeric conversions have valid input",
            ],
            "KeyError": [
                "Check that the key exists in the dictionary",
                "Use dict.get() to safely access potentially missing keys",
                "Verify the key type matches (e.g., '1' vs 1)",
                "Consider using collections.defaultdict",
            ],
            "IndexError": [
                "Check that the index is within bounds",
                "Verify the list/string is not empty before indexing",
                "Consider using negative indices or slice notation",
            ],
            "AttributeError": [
                "Check that the object has the attribute/method",
                "Verify the object type - is it what you expect?",
                "Ensure proper initialization before attribute access",
                "Check for None where an object is expected",
            ],
            "ModuleNotFoundError": [
                "Install the missing module: pip install <module>",
                "Check that the module name is spelled correctly",
                "Verify your Python environment and PATH",
                "Ensure you're using the correct Python interpreter",
            ],
            "ImportError": [
                "Check that the imported name exists in the module",
                "Verify the module is installed correctly",
                "Check for circular imports",
                "Ensure __init__.py files exist for packages",
            ],
            "ZeroDivisionError": [
                "Add a check for zero before division",
                "Use try/except or conditional logic",
                "Consider using float('inf') or numpy division",
            ],
            "FileNotFoundError": [
                "Verify the file path is correct",
                "Check that the file/directory exists",
                "Use absolute paths or check working directory",
                "Ensure proper permissions to access the path",
            ],
            "PermissionError": [
                "Check file/directory permissions",
                "Run with appropriate privileges",
                "Check if the file is locked by another process",
                "Verify ownership of the file/directory",
            ],
            "RecursionError": [
                "Check for infinite recursion in your function",
                "Add a base case to your recursive function",
                "Consider converting to an iterative approach",
                "Increase sys.setrecursionlimit() if truly needed",
            ],
            "MemoryError": [
                "Your program is using too much memory",
                "Consider processing data in chunks",
                "Use generators instead of lists for large data",
                "Check for memory leaks or infinite data structures",
            ],
            "TimeoutError": [
                "The operation took too long to complete",
                "Check for infinite loops or blocking operations",
                "Consider using asynchronous operations",
                "Increase timeout if the operation is genuinely slow",
            ],
        }
        
        if exc_type in patterns:
            suggestions.extend(patterns[exc_type])
        
        # Context-aware suggestions based on code
        if frames:
            last_frame = frames[0]
            code = last_frame.code_context or ""
            
            if "." in code and "None" in message:
                suggestions.append("The object before the dot (.) might be None")
            
            if "[" in code and "]" in code:
                suggestions.append("Check that the indexing operation uses valid keys/indices")
            
            if "(" in code and ")" in code:
                suggestions.append("Verify function arguments match the expected signature")
        
        if not suggestions:
            suggestions.append("Review the traceback to locate the error source")
            suggestions.append("Add logging or print statements to debug")
            suggestions.append("Use a debugger to step through the code")
        
        return suggestions
    
    def debug_function(self, func: Callable, *args, **kwargs) -> ExecutionResult:
        """
        Execute a function with full debugging enabled.
        
        Args:
            func: Function to debug
            *args, **kwargs: Arguments to pass to the function
        """
        log(LogLevel.INFO, f"Debugging function: {func.__name__}")
        
        start_time = __import__('time').time()
        
        try:
            # Set up trace function
            sys.settrace(self._trace_calls)
            result = func(*args, **kwargs)
            sys.settrace(None)
            
            duration = (__import__('time').time() - start_time) * 1000
            
            return ExecutionResult(
                success=True,
                message=f"Function completed successfully",
                data=result,
                duration_ms=duration
            )
        except Exception as e:
            sys.settrace(None)
            duration = (__import__('time').time() - start_time) * 1000
            
            exc_info = self.analyze_exception()
            
            log(LogLevel.ERROR, f"Exception caught: {exc_info.exception_type}")
            log(LogLevel.ERROR, exc_info.message)
            
            if console:
                console.print(exc_info.format())
            
            return ExecutionResult(
                success=False,
                message=f"{exc_info.exception_type}: {exc_info.message}",
                data=exc_info,
                stderr=exc_info.format(),
                exit_code=1,
                duration_ms=duration
            )
    
    def _trace_calls(self, frame, event, arg):
        """Internal trace function for step-through debugging."""
        filename = frame.f_code.co_filename
        lineno = frame.f_lineno
        function = frame.f_code.co_name
        
        # Skip built-in modules
        if '/lib/python' in filename and 'site-packages' not in filename:
            return self._trace_calls
        
        if event == 'call':
            self._call_stack.append(StackFrame(
                filename=filename,
                lineno=lineno,
                function=function
            ))
            
            # Check function breakpoints
            for bp in self.breakpoints.values():
                if bp.enabled and bp.bp_type == BreakpointType.FUNCTION:
                    if bp.function == function:
                        log(LogLevel.INFO, f"Hit function breakpoint: {bp}")
                        self._inspect_frame(frame)
            
        elif event == 'line':
            # Check line breakpoints
            for bp in self.breakpoints.values():
                if bp.enabled and bp.bp_type in (BreakpointType.LINE, BreakpointType.CONDITIONAL):
                    if bp.line == lineno and bp.file == filename:
                        bp.hit_count += 1
                        if bp.condition:
                            try:
                                if not eval(bp.condition, frame.f_globals, frame.f_locals):
                                    continue
                            except:
                                continue
                        log(LogLevel.INFO, f"Hit breakpoint: {bp}")
                        self._inspect_frame(frame)
            
            # Check watch expressions
            for expr in self._watch_expressions:
                try:
                    val = eval(expr, frame.f_globals, frame.f_locals)
                    log(LogLevel.INFO, f"Watch [{expr}] = {val}")
                except:
                    pass
        
        elif event == 'return':
            if self._call_stack:
                self._call_stack.pop()
        
        elif event == 'exception':
            exc_type, exc_value, exc_tb = arg
            log(LogLevel.WARNING, f"Exception in {function}: {exc_type.__name__}: {exc_value}")
        
        return self._trace_calls
    
    def _inspect_frame(self, frame):
        """Inspect current frame - show variables and wait for commands."""
        # Get local variables
        locals_dict = {}
        for name, value in list(frame.f_locals.items()):
            try:
                locals_dict[name] = f"{type(value).__name__} = {repr(value)[:80]}"
            except:
                locals_dict[name] = f"{type(value).__name__} = <unprintable>"
        
        if locals_dict:
            rows = [[k, v] for k, v in list(locals_dict.items())[:15]]
            print_table("Local Variables", ["Name", "Value"], rows)
        
        # Show code context
        code_context = linecache.getline(frame.f_code.co_filename, frame.f_lineno)
        if code_context:
            log(LogLevel.INFO, f"Current line: {code_context.strip()}")
    
    def post_mortem(self, exc_info=None):
        """
        Post-mortem debugging - analyze the last exception.
        
        Args:
            exc_info: Optional exc_info tuple. Uses last exception if None.
        """
        if exc_info is None:
            exc_info = sys.last_value if hasattr(sys, 'last_value') else None
            if exc_info is None:
                exc_info = sys.exc_info()
        
        info = self.analyze_exception(exc_info)
        
        if console:
            from rich.panel import Panel
            console.print(Panel(
                info.format(),
                title=f"[bold red]Exception Analysis: {info.exception_type}[/]",
                border_style="red"
            ))
        else:
            print("\n" + "="*60)
            print(f"POST-MORTEM ANALYSIS: {info.exception_type}")
            print("="*60)
            print(info.format())
        
        return info
    
    def inspect_object(self, obj: Any, depth: int = 0, max_depth: int = 3) -> Dict[str, Any]:
        """
        Deep inspection of any Python object.
        
        Args:
            obj: Object to inspect
            depth: Current recursion depth
            max_depth: Maximum inspection depth
        """
        if depth > max_depth:
            return {"...": "max depth reached"}
        
        info = {
            "type": type(obj).__name__,
            "module": type(obj).__module__,
            "id": id(obj),
            "hash": hash(obj) & 0xFFFFFFFF,
        }
        
        # String representation
        try:
            info["repr"] = repr(obj)[:200]
        except:
            info["repr"] = "<unprintable>"
        
        # Size
        try:
            info["size"] = sys.getsizeof(obj)
        except:
            pass
        
        # Attributes
        try:
            attrs = {}
            for name in dir(obj):
                if not name.startswith('_'):
                    try:
                        val = getattr(obj, name)
                        attrs[name] = f"{type(val).__name__}"
                    except:
                        attrs[name] = "<inaccessible>"
            if attrs:
                info["attributes"] = attrs
        except:
            pass
        
        # For containers, inspect contents
        if isinstance(obj, (list, tuple, set)):
            info["length"] = len(obj)
            info["items"] = [self.inspect_object(item, depth+1, max_depth) 
                           for item in list(obj)[:10]]
        elif isinstance(obj, dict):
            info["length"] = len(obj)
            info["items"] = {k: self.inspect_object(v, depth+1, max_depth) 
                           for k, v in list(obj.items())[:10]}
        
        return info
    
    def format_inspection(self, obj: Any, title: str = "Object Inspection") -> str:
        """Format object inspection as a readable string."""
        info = self.inspect_object(obj)
        
        lines = [f"\n{'='*50}", f"{title}", f"{'='*50}"]
        lines.append(f"Type: {info['type']}")
        lines.append(f"Module: {info['module']}")
        lines.append(f"ID: {info['id']:#x}")
        lines.append(f"Hash: {info['hash']}")
        lines.append(f"Size: {info.get('size', 'N/A')} bytes")
        lines.append(f"Repr: {info['repr']}")
        
        if 'length' in info:
            lines.append(f"Length: {info['length']}")
        
        if 'attributes' in info:
            lines.append(f"\nAttributes ({len(info['attributes'])}):")
            for name, type_name in sorted(info['attributes'].items())[:20]:
                lines.append(f"  {name}: {type_name}")
        
        return "\n".join(lines)
