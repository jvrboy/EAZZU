"""
DevToolkit CLI - Main command-line interface.
Provides an interactive and scriptable interface to all toolkit modules.
"""

import os
import sys
import argparse
import shlex
from pathlib import Path
from typing import Optional, List

from .utils import (
    print_banner, log, LogLevel, console, print_table, 
    ExecutionResult, list_archive_formats, format_size
)
from .runner import CodeRunner
from .debugger import CodeDebugger
from .filecreator import FileCreator
from .extractor import ArchiveExtractor
from .ai_analyzer import AICodeAnalyzer


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser with all subcommands."""
    parser = argparse.ArgumentParser(
        prog='devtoolkit',
        description='All-in-One Code Interpreter, Runner, Debugger, File Creator & Archive Extractor',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  devtoolkit run python "print('Hello World')"
  devtoolkit run file.py
  devtoolkit debug script.py
  devtoolkit create file.py --template python
  devtoolkit extract archive.zip -o ./output
  devtoolkit analyze script.py
  devtoolkit scaffold python myproject
  devtoolkit interactive
        """
    )
    
    parser.add_argument('--version', action='version', version='%(prog)s 2.0.0')
    parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output')
    parser.add_argument('--no-color', action='store_true', help='Disable colored output')
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # ---- RUN command ----
    run_parser = subparsers.add_parser('run', aliases=['r', 'exec'],
        help='Run code in any supported language')
    run_parser.add_argument('language_or_file', help='Language identifier or file path')
    run_parser.add_argument('code', nargs='?', help='Code to execute (if language specified)')
    run_parser.add_argument('-a', '--args', help='Arguments to pass to the program')
    run_parser.add_argument('--stdin', help='Input to pass via stdin')
    run_parser.add_argument('-t', '--timeout', type=int, default=60, help='Timeout in seconds')
    run_parser.add_argument('--interactive', '-i', action='store_true', help='Interactive REPL mode')
    run_parser.add_argument('--list', action='store_true', help='List supported languages')
    
    # ---- DEBUG command ----
    debug_parser = subparsers.add_parser('debug', aliases=['d'],
        help='Debug code with intelligent analysis')
    debug_parser.add_argument('target', help='File or code to debug')
    debug_parser.add_argument('-l', '--language', help='Language (auto-detect if not specified)')
    debug_parser.add_argument('--post-mortem', action='store_true', help='Post-mortem analysis')
    debug_parser.add_argument('--break', '-b', dest='breakpoints', action='append',
        help='Set breakpoint (file:line or file:function)')
    debug_parser.add_argument('--watch', '-w', action='append', help='Watch expression')
    
    # ---- CREATE command ----
    create_parser = subparsers.add_parser('create', aliases=['c', 'new'],
        help='Create files with intelligent templates')
    create_parser.add_argument('filepath', help='Path for the new file')
    create_parser.add_argument('-t', '--template', help='Template to use')
    create_parser.add_argument('--content', help='Raw file content')
    create_parser.add_argument('--var', action='append', help='Template variable (key=value)')
    create_parser.add_argument('--executable', '-x', action='store_true', help='Make executable')
    create_parser.add_argument('--overwrite', action='store_true', help='Overwrite existing')
    create_parser.add_argument('--list-templates', action='store_true', help='List templates')
    create_parser.add_argument('--batch', help='JSON file with multiple files to create')
    
    # ---- SCAFFOLD command ----
    scaffold_parser = subparsers.add_parser('scaffold', aliases=['s', 'init'],
        help='Scaffold a complete project structure')
    scaffold_parser.add_argument('project_type', 
        choices=['python', 'node', 'go', 'rust', 'web'],
        help='Project type')
    scaffold_parser.add_argument('name', help='Project name')
    scaffold_parser.add_argument('-d', '--directory', help='Target directory')
    
    # ---- EXTRACT command ----
    extract_parser = subparsers.add_parser('extract', aliases=['x', 'unzip', 'untar'],
        help='Extract any archive format')
    extract_parser.add_argument('archive', help='Archive file path')
    extract_parser.add_argument('-o', '--output', help='Output directory')
    extract_parser.add_argument('-p', '--password', help='Password for encrypted archives')
    extract_parser.add_argument('--files', nargs='+', help='Extract only specific files')
    extract_parser.add_argument('--overwrite', action='store_true', help='Overwrite existing')
    extract_parser.add_argument('--list', action='store_true', help='List archive contents')
    extract_parser.add_argument('--formats', action='store_true', help='List supported formats')
    
    # ---- ANALYZE command ----
    analyze_parser = subparsers.add_parser('analyze', aliases=['a', 'lint', 'check'],
        help='Analyze code with AI-powered suggestions')
    analyze_parser.add_argument('target', help='File or directory to analyze')
    analyze_parser.add_argument('-l', '--language', help='Language override')
    analyze_parser.add_argument('--fix', action='store_true', help='Show fix suggestions')
    analyze_parser.add_argument('--refactor', action='store_true', help='Generate refactored code')
    analyze_parser.add_argument('--recursive', '-r', action='store_true', help='Analyze directory recursively')
    analyze_parser.add_argument('--pattern', default='*.py', help='File pattern for directory analysis')
    
    # ---- INTERACTIVE command ----
    interactive_parser = subparsers.add_parser('interactive', aliases=['i', 'shell', 'repl'],
        help='Start interactive shell')
    interactive_parser.add_argument('--prompt', default='devtoolkit> ', help='Custom prompt')
    
    # ---- INFO command ----
    info_parser = subparsers.add_parser('info', help='Show system information')
    
    return parser


def handle_run(args) -> int:
    """Handle the 'run' command."""
    runner = CodeRunner()
    
    if args.list:
        runner.list_languages()
        return 0
    
    if args.interactive:
        runner.run_interactive(args.language_or_file)
        return 0
    
    # Determine if first arg is a file or language
    target = args.language_or_file
    
    if os.path.isfile(target):
        # Run a file
        run_args = shlex.split(args.args) if args.args else None
        result = runner.execute_file(
            target, args=run_args, 
            stdin=args.stdin, timeout=args.timeout
        )
    else:
        # Run code string
        if not args.code:
            log(LogLevel.ERROR, "No code provided. Usage: devtoolkit run <language> <code>")
            return 1
        
        result = runner.execute_code(
            target, args.code,
            args=shlex.split(args.args) if args.args else None,
            stdin=args.stdin, timeout=args.timeout
        )
    
    # Output results
    if result.stdout:
        print(result.stdout, end='')
    if result.stderr:
        print(result.stderr, end='', file=sys.stderr)
    
    if not result.success:
        log(LogLevel.ERROR, result.message)
        if result.stderr:
            log(LogLevel.ERROR, f"Error details:\n{result.stderr}")
    
    return result.exit_code


def handle_debug(args) -> int:
    """Handle the 'debug' command."""
    debugger = CodeDebugger()
    
    if args.post_mortem:
        info = debugger.post_mortem()
        return 0 if info else 1
    
    # Set breakpoints
    if args.breakpoints:
        for bp in args.breakpoints:
            if ':' in bp:
                parts = bp.split(':')
                if parts[1].isdigit():
                    debugger.set_breakpoint(parts[0], int(parts[1]))
                else:
                    debugger.set_function_breakpoint(parts[0], parts[1])
    
    # Set watches
    if args.watch:
        for expr in args.watch:
            debugger.add_watch(expr)
    
    # Analyze the file for issues
    if os.path.isfile(args.target):
        analyzer = AICodeAnalyzer()
        result = analyzer.analyze_file(args.target, args.language)
        analyzer.print_report(result)
        
        if result.issues:
            return 1
    else:
        log(LogLevel.ERROR, f"File not found: {args.target}")
        return 1
    
    return 0


def handle_create(args) -> int:
    """Handle the 'create' command."""
    creator = FileCreator()
    
    if args.list_templates:
        creator.list_templates()
        return 0
    
    # Parse template variables
    variables = {}
    if args.var:
        for var in args.var:
            if '=' in var:
                key, value = var.split('=', 1)
                variables[key] = value
    
    if args.batch:
        import json
        with open(args.batch) as f:
            files = json.load(f)
        result = creator.create_batch(files)
    else:
        result = creator.create_file(
            filepath=args.filepath,
            template_key=args.template,
            variables=variables,
            content=args.content,
            executable=args.executable,
            overwrite=args.overwrite
        )
    
    if result.success:
        log(LogLevel.SUCCESS, result.message)
        if result.files_affected:
            for f in result.files_affected:
                print(f"  Created: {f}")
    else:
        log(LogLevel.ERROR, result.message)
        return 1
    
    return 0


def handle_scaffold(args) -> int:
    """Handle the 'scaffold' command."""
    creator = FileCreator()
    result = creator.scaffold_project(args.project_type, args.name, args.directory)
    
    if result.success:
        log(LogLevel.SUCCESS, result.message)
        if result.files_affected:
            print(f"  Created {len(result.files_affected)} files in {args.name}/")
    else:
        log(LogLevel.ERROR, result.message)
        return 1
    
    return 0


def handle_extract(args) -> int:
    """Handle the 'extract' command."""
    extractor = ArchiveExtractor()
    
    if args.formats:
        formats = list_archive_formats()
        rows = [[f['format'], f['extensions'], f['description'], f['method']] for f in formats]
        print_table("Supported Archive Formats (25+)", 
                   ["Format", "Extensions", "Description", "Method"], rows)
        return 0
    
    if args.list:
        info = extractor.list_contents(args.archive)
        if info:
            print(f"\nArchive: {args.archive}")
            print(f"Format: {info.format}")
            print(f"Files: {info.file_count}")
            print(f"Size: {info.format_size()}")
            if info.is_encrypted:
                print("Status: [ENCRYPTED]")
            if info.comment:
                print(f"Comment: {info.comment}")
            
            rows = [[f.get('name', ''), str(f.get('size', 0)), f.get('date', '')] 
                   for f in info.files[:100]]
            print_table("Contents", ["Name", "Size", "Date"], rows)
        return 0
    
    result = extractor.extract(
        args.archive,
        output_dir=args.output,
        specific_files=args.files,
        password=args.password,
        overwrite=args.overwrite
    )
    
    if result.success:
        log(LogLevel.SUCCESS, result.message)
        print(f"  Files extracted: {result.file_count}")
        print(f"  Total size: {format_size(result.total_size)}")
        print(f"  Output: {result.output_dir}")
        if result.warnings:
            for w in result.warnings:
                log(LogLevel.WARNING, w)
    else:
        log(LogLevel.ERROR, result.message)
        return 1
    
    return 0


def handle_analyze(args) -> int:
    """Handle the 'analyze' command."""
    analyzer = AICodeAnalyzer()
    
    target = os.path.abspath(args.target)
    
    if os.path.isdir(target):
        if not args.recursive:
            log(LogLevel.ERROR, "Use --recursive to analyze directories")
            return 1
        
        results = analyzer.analyze_directory(target, args.pattern)
        total_issues = sum(r.total_issues for r in results)
        
        print(f"\nAnalyzed {len(results)} files, found {total_issues} issues total\n")
        
        for result in results:
            if result.total_issues > 0:
                analyzer.print_report(result)
        
        return 0 if total_issues == 0 else 1
    
    result = analyzer.analyze_file(target, args.language)
    analyzer.print_report(result)
    
    if args.fix:
        fixes = analyzer.suggest_fixes(result)
        if fixes:
            print("\nSuggested Fixes:")
            for fix in fixes[:20]:
                print(f"  Line {fix['line']} [{fix['severity']}]: {fix['suggestion']}")
    
    if args.refactor:
        with open(target, 'r') as f:
            code = f.read()
        refactored = analyzer.generate_refactored_code(code, result.language)
        print("\nRefactored Code:")
        print("-" * 40)
        print(refactored)
    
    return 0 if result.total_issues == 0 else 1


def handle_interactive(args) -> int:
    """Handle the 'interactive' command."""
    print_banner()
    
    runner = CodeRunner()
    debugger = CodeDebugger()
    creator = FileCreator()
    extractor = ArchiveExtractor()
    analyzer = AICodeAnalyzer()
    
    print("\nWelcome to DevToolkit Interactive Shell!")
    print("Type 'help' for commands, 'exit' to quit\n")
    
    while True:
        try:
            cmd = input(f"\n{args.prompt}").strip()
            
            if not cmd:
                continue
            
            if cmd.lower() in ('exit', 'quit', 'q'):
                print("Goodbye!")
                break
            
            if cmd.lower() == 'help':
                print("""
Commands:
  run <lang> <code>     - Run code in a language
  run <file>            - Run a file
  debug <file>          - Debug a file
  create <path>         - Create a file from template
  extract <archive>     - Extract an archive
  analyze <file>        - Analyze code
  list languages        - List supported languages
  list templates        - List file templates
  list formats          - List archive formats
  exec <python code>    - Execute Python code directly
  clear                 - Clear screen
  exit                  - Exit interactive shell
                """)
                continue
            
            if cmd.lower() == 'clear':
                os.system('clear' if os.name != 'nt' else 'cls')
                continue
            
            if cmd.lower() == 'list languages':
                runner.list_languages()
                continue
            
            if cmd.lower() == 'list templates':
                creator.list_templates()
                continue
            
            if cmd.lower() == 'list formats':
                formats = list_archive_formats()
                rows = [[f['format'], f['extensions'], f['description']] for f in formats]
                print_table("Supported Formats", ["Format", "Extensions", "Description"], rows)
                continue
            
            # Parse and execute command
            parts = shlex.split(cmd)
            if not parts:
                continue
            
            if parts[0] == 'exec':
                # Direct Python execution
                code = ' '.join(parts[1:])
                result = runner.execute_code('python', code)
                if result.stdout:
                    print(result.stdout, end='')
                if result.stderr:
                    print(result.stderr, end='', file=sys.stderr)
                continue
            
            if parts[0] == 'run' and len(parts) >= 2:
                if os.path.isfile(parts[1]):
                    result = runner.execute_file(parts[1])
                else:
                    result = runner.execute_code(parts[1], ' '.join(parts[2:]))
                if result.stdout:
                    print(result.stdout, end='')
                if result.stderr:
                    print(result.stderr, end='', file=sys.stderr)
                continue
            
            if parts[0] == 'debug' and len(parts) >= 2:
                result = analyzer.analyze_file(parts[1])
                analyzer.print_report(result)
                continue
            
            if parts[0] == 'create' and len(parts) >= 2:
                result = creator.create_file(parts[1])
                if result.success:
                    log(LogLevel.SUCCESS, result.message)
                continue
            
            if parts[0] == 'extract' and len(parts) >= 2:
                result = extractor.extract(parts[1])
                if result.success:
                    log(LogLevel.SUCCESS, f"Extracted {result.file_count} files")
                continue
            
            if parts[0] == 'analyze' and len(parts) >= 2:
                result = analyzer.analyze_file(parts[1])
                analyzer.print_report(result)
                continue
            
            # Default: try as Python code
            result = runner.execute_code('python', cmd)
            if result.stdout:
                print(result.stdout, end='')
            if result.stderr:
                print(result.stderr, end='', file=sys.stderr)
        
        except KeyboardInterrupt:
            print("\nInterrupted. Type 'exit' to quit.")
        except EOFError:
            print("\nGoodbye!")
            break
        except Exception as e:
            log(LogLevel.ERROR, f"Error: {e}")
    
    return 0


def handle_info(args) -> int:
    """Handle the 'info' command."""
    import platform
    
    print_banner()
    
    info_data = [
        ["Python Version", platform.python_version()],
        ["Platform", platform.platform()],
        ["OS", f"{platform.system()} {platform.release()}"],
        ["Architecture", platform.machine()],
        ["Processor", platform.processor()],
        ["Python Path", sys.executable],
        ["DevToolkit Version", "2.0.0"],
    ]
    
    print_table("System Information", ["Property", "Value"], info_data)
    
    # Show available features
    runner = CodeRunner()
    available_langs = sum(1 for lid in runner.languages if runner.check_language(lid))
    
    features = [
        ["Languages Supported", str(len(runner.languages))],
        ["Languages Available", f"{available_langs}/{len(runner.languages)}"],
        ["Archive Formats", "25+"],
        ["File Templates", "50+"],
        ["Project Scaffolds", "5 types"],
        ["Analysis Rules", "100+"],
    ]
    
    print_table("Features", ["Feature", "Details"], features)
    
    return 0


def main() -> int:
    """Main entry point."""
    parser = create_parser()
    
    # If no arguments, show banner and help
    if len(sys.argv) == 1:
        print_banner()
        parser.print_help()
        return 0
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 0
    
    # Dispatch to handlers
    handlers = {
        'run': handle_run,
        'r': handle_run,
        'exec': handle_run,
        'debug': handle_debug,
        'd': handle_debug,
        'create': handle_create,
        'c': handle_create,
        'new': handle_create,
        'scaffold': handle_scaffold,
        's': handle_scaffold,
        'init': handle_scaffold,
        'extract': handle_extract,
        'x': handle_extract,
        'unzip': handle_extract,
        'untar': handle_extract,
        'analyze': handle_analyze,
        'a': handle_analyze,
        'lint': handle_analyze,
        'check': handle_analyze,
        'interactive': handle_interactive,
        'i': handle_interactive,
        'shell': handle_interactive,
        'repl': handle_interactive,
        'info': handle_info,
    }
    
    handler = handlers.get(args.command)
    if handler:
        try:
            return handler(args)
        except KeyboardInterrupt:
            print("\nOperation cancelled")
            return 130
        except Exception as e:
            log(LogLevel.ERROR, f"Unexpected error: {e}")
            if args.verbose:
                import traceback
                traceback.print_exc()
            return 1
    else:
        print(f"Unknown command: {args.command}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
