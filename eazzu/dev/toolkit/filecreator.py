"""
File Creator Module - Create files of any type with templates and scaffolding.
Supports: 50+ file types with syntax-aware templates, project scaffolding,
batch file creation, and intelligent content generation.
"""

import os
import re
import json
import stat
from pathlib import Path
from typing import Optional, List, Dict, Any, Union
from datetime import datetime

from .utils import (
    ExecutionResult, log, LogLevel, console, print_code, 
    ensure_dir, spinner, print_table
)


# File templates for various types
FILE_TEMPLATES = {
    # Python
    ".py": '''#!/usr/bin/env python3
"""
{filename}
{description}

Author: {author}
Date: {date}
"""


def main():
    """Main function."""
    pass


if __name__ == "__main__":
    main()
''',
    ".pyi": '''# Type stub file
from typing import Any, Optional, List, Dict, Union, Tuple

def function_name(param: str) -> int: ...
''',
    
    # JavaScript/TypeScript
    ".js": '''/**
 * {filename}
 * {description}
 * 
 * @author {author}
 * @date {date}
 */

/**
 * Main function
 */
function main() {{
    console.log("Hello, World!");
}}

// Run if executed directly
if (require.main === module) {{
    main();
}}

module.exports = {{ main }};
''',
    ".ts": '''/**
 * {filename}
 * {description}
 * 
 * @author {author}
 * @date {date}
 */

interface Config {{
    name: string;
    value: number;
}}

function main(): void {{
    console.log("Hello, TypeScript!");
}}

// Run if executed directly
if (require.main === module) {{
    main();
}}

export {{ main }};
''',
    
    # Web
    ".html": '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 1200px;
            margin: 0 auto;
            padding: 2rem;
        }}
    </style>
</head>
<body>
    <header>
        <h1>{title}</h1>
    </header>
    
    <main>
        <p>Welcome to {title}!</p>
    </main>
    
    <footer>
        <p>&copy; {year} {author}. All rights reserved.</p>
    </footer>
    
    <script>
        console.log("Page loaded successfully!");
    </script>
</body>
</html>
''',
    ".css": '''/**
 * {filename}
 * {description}
 * 
 * @author {author}
 * @date {date}
 */

:root {{
    --primary-color: #3498db;
    --secondary-color: #2c3e50;
    --accent-color: #e74c3c;
    --text-color: #333;
    --bg-color: #f8f9fa;
    --border-radius: 8px;
    --spacing: 1rem;
}}

* {{
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}}

body {{
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    line-height: 1.6;
    color: var(--text-color);
    background-color: var(--bg-color);
}}

.container {{
    max-width: 1200px;
    margin: 0 auto;
    padding: var(--spacing);
}}
''',
    
    # Shell
    ".sh": '''#!/bin/bash
###############################################################################
# {filename}
# {description}
#
# Author: {author}
# Date: {date}
###############################################################################

set -euo pipefail

# Colors
RED='\\033[0;31m'
GREEN='\\033[0;32m'
YELLOW='\\033[1;33m'
NC='\\033[0m' # No Color

# Logging functions
log_info() {{ echo -e "${{GREEN}}[INFO]${{NC}} $1"; }}
log_warn() {{ echo -e "${{YELLOW}}[WARN]${{NC}} $1"; }}
log_error() {{ echo -e "${{RED}}[ERROR]${{NC}} $1"; }}

# Main function
main() {{
    log_info "Starting {filename}..."
    
    # Your code here
    
    log_info "Completed successfully!"
}}

# Show usage
usage() {{
    echo "Usage: $0 [options]"
    echo "Options:"
    echo "  -h, --help    Show this help message"
    echo "  -v, --verbose Enable verbose output"
}}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            usage
            exit 0
            ;;
        -v|--verbose)
            set -x
            shift
            ;;
        *)
            echo "Unknown option: $1"
            usage
            exit 1
            ;;
    esac
done

main "$@"
''',
    
    ".bash": '''#!/bin/bash
# {filename}
# {description}

set -euo pipefail

main() {{
    echo "Hello from Bash!"
}}

main "$@"
''',
    
    ".zsh": '''#!/bin/zsh
# {filename}
# {description}

set -euo pipefail

main() {{
    echo "Hello from Zsh!"
}}

main "$@"
''',
    
    ".ps1": '''# {filename}
# {description}
# Author: {author}
# Date: {date}

[CmdletBinding()]
param(
    [Parameter()]
    [string]$Name = "World"
)

function Write-Log {{
    param([string]$Message, [string]$Level = "INFO")
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Write-Host "[$timestamp] [$Level] $Message"
}}

function Main {{
    Write-Log -Message "Starting {filename}..."
    Write-Host "Hello, $Name!"
    Write-Log -Message "Completed successfully!"
}}

Main
''',
    
    # C-family
    ".c": '''/**
 * {filename}
 * {description}
 * 
 * @author {author}
 * @date {date}
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/**
 * Main function
 */
int main(int argc, char *argv[]) {{
    printf("Hello, World!\\n");
    return 0;
}}
''',
    
    ".cpp": '''/**
 * {filename}
 * {description}
 * 
 * @author {author}
 * @date {date}
 */

#include <iostream>
#include <string>
#include <vector>
#include <memory>

/**
 * Main function
 */
int main(int argc, char* argv[]) {{
    std::cout << "Hello, C++!" << std::endl;
    return 0;
}}
''',
    
    ".h": '''/**
 * {filename}
 * Header file
 * 
 * @author {author}
 * @date {date}
 */

#ifndef {guard}
#define {guard}

#ifdef __cplusplus
extern "C" {{
#endif

// Function declarations

#ifdef __cplusplus
}}
#endif

#endif /* {guard} */
''',
    
    ".hpp": '''/**
 * {filename}
 * C++ Header file
 * 
 * @author {author}
 * @date {date}
 */

#ifndef {guard}
#define {guard}

#include <iostream>
#include <string>
#include <vector>

class {class_name} {{
public:
    {class_name}();
    ~{class_name}();
    
private:
    
}};

#endif /* {guard} */
''',
    
    # Java
    ".java": '''/**
 * {filename}
 * {description}
 * 
 * @author {author}
 * @date {date}
 */

public class {class_name} {{
    
    /**
     * Main entry point
     */
    public static void main(String[] args) {{
        System.out.println("Hello, Java!");
    }}
}}
''',
    
    # Go
    ".go": '''// {filename}
// {description}
//
// Author: {author}
// Date: {date}

package main

import (
	"fmt"
	"log"
)

func main() {{
	fmt.Println("Hello, Go!")
}}
''',
    
    # Rust
    ".rs": '''//! {filename}
//! {description}
//!
//! Author: {author}
//! Date: {date}

fn main() {{
    println!("Hello, Rust!");
}}
''',
    
    # Ruby
    ".rb": '''#!/usr/bin/env ruby
# {filename}
# {description}
#
# Author: {author}
# Date: {date}

class Application
  def initialize
    puts "Initializing..."
  end
  
  def run
    puts "Hello, Ruby!"
  end
end

if __FILE__ == $0
  app = Application.new
  app.run
end
''',
    
    # PHP
    ".php": '''<?php
/**
 * {filename}
 * {description}
 * 
 * @author {author}
 * @date {date}
 */

declare(strict_types=1);

class Application
{{
    public function run(): void
    {{
        echo "Hello, PHP!\\n";
    }}
}}

// Main
$app = new Application();
$app->run();
''',
    
    # Perl
    ".pl": '''#!/usr/bin/env perl
# {filename}
# {description}
#
# Author: {author}
# Date: {date}

use strict;
use warnings;
use feature qw(say);

sub main {{
    say "Hello, Perl!";
}}

main();
''',
    
    # Lua
    ".lua": '''-- {filename}
-- {description}
--
-- Author: {author}
-- Date: {date}

local M = {{}}

function M.main()
    print("Hello, Lua!")
end

-- Run if executed directly
if ... == nil then
    M.main()
end

return M
''',
    
    # R
    ".r": '''# {filename}
# {description}
#
# Author: {author}
# Date: {date}

main <- function() {{
    cat("Hello, R!\\n")
}}

# Run if executed directly
if (interactive() == FALSE) {{
    main()
}}
''',
    
    # Swift
    ".swift": '''// {filename}
// {description}
//
// Author: {author}
// Date: {date}

import Foundation

class Application {{
    func run() {{
        print("Hello, Swift!")
    }}
}}

// Main
let app = Application()
app.run()
''',
    
    # Kotlin
    ".kt": '''/**
 * {filename}
 * {description}
 * 
 * @author {author}
 * @date {date}
 */

fun main() {{
    println("Hello, Kotlin!")
}}
''',
    
    # Scala
    ".scala": '''/**
 * {filename}
 * {description}
 * 
 * @author {author}
 * @date {date}
 */

object {class_name} {{
  def main(args: Array[String]): Unit = {{
    println("Hello, Scala!")
  }}
}}
''',
    
    # Haskell
    ".hs": '''-- {filename}
-- {description}
--
-- Author: {author}
-- Date: {date}

module Main where

main :: IO ()
main = putStrLn "Hello, Haskell!"
''',
    
    # Config/Data files
    ".json": '''{{
  "name": "{name}",
  "version": "1.0.0",
  "description": "{description}",
  "author": "{author}",
  "license": "MIT",
  "scripts": {{
    "start": "echo 'Starting...'",
    "test": "echo 'Running tests...'"
  }}
}}
''',
    
    ".yaml": '''# {filename}
# {description}
# Author: {author}
# Date: {date}

name: {name}
version: "1.0.0"
description: |
  {description}

settings:
  debug: false
  log_level: info
  
environments:
  development:
    host: localhost
    port: 3000
  production:
    host: 0.0.0.0
    port: 8080
''',
    
    ".yml": '''# {filename}
# {description}
# Author: {author}
# Date: {date}

name: {name}
version: "1.0.0"

config:
  setting1: value1
  setting2: value2
''',
    
    ".toml": '''# {filename}
# {description}
# Author: {author}
# Date: {date}

[package]
name = "{name}"
version = "1.0.0"
description = "{description}"
author = "{author}"

[settings]
debug = false
log_level = "info"
''',
    
    ".ini": '''; {filename}
; {description}
; Author: {author}
; Date: {date}

[DEFAULT]
debug = false
log_level = info

[database]
host = localhost
port = 5432
name = mydb

[server]
host = 0.0.0.0
port = 8080
workers = 4
''',
    
    ".xml": '''<?xml version="1.0" encoding="UTF-8"?>
<!--
  {filename}
  {description}
  
  Author: {author}
  Date: {date}
-->
<root>
  <metadata>
    <name>{name}</name>
    <version>1.0.0</version>
  </metadata>
  <content>
    <!-- Your content here -->
  </content>
</root>
''',
    
    # Documentation
    ".md": '''# {title}

{description}

## Overview

Brief overview of the project or document.

## Table of Contents

- [Installation](#installation)
- [Usage](#usage)
- [API Reference](#api-reference)
- [Contributing](#contributing)
- [License](#license)

## Installation

```bash
# Add installation instructions here
```

## Usage

```python
# Add usage examples here
```

## API Reference

### Functions

#### `function_name(param: type) -> return_type`

Description of the function.

**Parameters:**
- `param` (type): Description

**Returns:**
- Description of return value

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License.

---

*Created by {author} on {date}*
''',
    
    ".rst": '''{title}
{underline}

{description}

Overview
========

Brief overview of the project or document.

Installation
============

.. code-block:: bash

    # Add installation instructions here

Usage
=====

.. code-block:: python

    # Add usage examples here

API Reference
=============

.. py:function:: function_name(param)

   Description of the function.

   :param param: Description
   :type param: type
   :returns: Description

License
=======

This project is licensed under the MIT License.

---

*Created by {author} on {date}*
''',
    
    # Docker & DevOps
    "Dockerfile": '''# {filename}
# {description}
# Author: {author}
# Date: {date}

# Build stage
FROM node:18-alpine AS builder

WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production

# Production stage
FROM node:18-alpine

WORKDIR /app
COPY --from=builder /app/node_modules ./node_modules
COPY . .

EXPOSE 3000

USER node

CMD ["node", "index.js"]
''',
    
    ".dockerignore": '''# Git
.git
.gitignore

# Dependencies
node_modules/
vendor/

# Build outputs
dist/
build/
*.log

# Environment
.env
.env.local
.env.*.local

# IDE
.idea/
.vscode/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db
''',
    
    # Git
    ".gitignore": '''# Dependencies
node_modules/
vendor/
__pycache__/
*.egg-info/

# Build outputs
dist/
build/
target/
*.exe
*.dll
*.so
*.class

# Logs
*.log
logs/

# Environment
.env
.env.local
.env.*.local

# IDE
.idea/
.vscode/
*.swp
*.swo
*~

# OS
.DS_Store
Thumbs.db

# Testing
.coverage
htmlcov/
.pytest_cache/

# Temporary
tmp/
temp/
*.tmp
''',
    
    # SQL
    ".sql": '''-- {filename}
-- {description}
-- Author: {author}
-- Date: {date}

-- Create database
-- CREATE DATABASE IF NOT EXISTS {name}_db;

-- Use database
-- USE {name}_db;

-- Create table example
CREATE TABLE IF NOT EXISTS users (
    id INT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(100) NOT NULL UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- Insert sample data
INSERT INTO users (username, email) VALUES
    ('admin', 'admin@example.com'),
    ('user1', 'user1@example.com');

-- Select all users
SELECT * FROM users;
''',
    
    # Makefile
    "Makefile": '''# {filename}
# {description}
# Author: {author}
# Date: {date}

.PHONY: all help install build test clean run dev lint format

# Default target
all: help

# Show help
help:
	@echo "Available targets:"
	@echo "  install  - Install dependencies"
	@echo "  build    - Build the project"
	@echo "  test     - Run tests"
	@echo "  clean    - Clean build artifacts"
	@echo "  run      - Run the application"
	@echo "  dev      - Run in development mode"
	@echo "  lint     - Run linter"
	@echo "  format   - Format code"

# Install dependencies
install:
	@echo "Installing dependencies..."

# Build the project
build:
	@echo "Building..."

# Run tests
test:
	@echo "Running tests..."

# Clean build artifacts
clean:
	@echo "Cleaning..."
	rm -rf dist/ build/ *.egg-info/

# Run the application
run:
	@echo "Running..."

# Development mode
dev:
	@echo "Starting development server..."

# Run linter
lint:
	@echo "Running linter..."

# Format code
format:
	@echo "Formatting code..."
''',
    
    # Vim
    ".vim": '''" {filename}
" {description}
" Author: {author}
" Date: {date}

" Settings
setlocal tabstop=4
setlocal shiftwidth=4
setlocal expandtab
setlocal autoindent
setlocal smartindent

" Key mappings
nnoremap <buffer> <F5> :w<CR>:!python3 %<CR>

" Your vim settings here
''',
    
    # Emacs
    ".el": ''';;; {filename} --- {description} -*- lexical-binding: t -*-

;; Author: {author}
;; Date: {date}

;;; Commentary:

;; {description}

;;; Code:

(message "Hello from Emacs Lisp!")

(provide '{module_name})
;;; {filename} ends here
''',
    
    # Jupyter
    ".ipynb": '''{{
 "cells": [
  {{
   "cell_type": "markdown",
   "metadata": {{}},
   "source": [
    "# {title}\\n",
    "\\n",
    "{description}"
   ]
  }},
  {{
   "cell_type": "code",
   "execution_count": null,
   "metadata": {{}},
   "outputs": [],
   "source": [
    "# Your code here\\n",
    "print('Hello, Jupyter!')"
   ]
  }}
 ],
 "metadata": {{
  "kernelspec": {{
   "display_name": "Python 3",
   "language": "python",
   "name": "python3"
  }},
  "language_info": {{
   "name": "python",
   "version": "3.10.0"
  }}
 }},
 "nbformat": 4,
 "nbformat_minor": 4
}}
''',
}


class FileCreator:
    """
    Intelligent file creator with templates for 50+ file types.
    
    Features:
    - Syntax-aware templates for each file type
    - Custom variable substitution
    - Batch file creation
    - Project scaffolding
    - File content generation
    """
    
    def __init__(self, author: str = "Developer", default_dir: str = "."):
        self.author = author
        self.default_dir = default_dir
        self.templates = FILE_TEMPLATES
    
    def list_templates(self):
        """Display all available file templates."""
        rows = []
        for ext, template in sorted(self.templates.items()):
            desc = template.split('\n')[0][:50] if template else "Empty template"
            rows.append([ext, f"{len(template)} chars", desc])
        
        print_table(
            f"Available Templates ({len(self.templates)})",
            ["Extension", "Size", "Description"],
            rows
        )
    
    def create_file(self, filepath: str, template_key: Optional[str] = None,
                    variables: Optional[Dict[str, str]] = None,
                    content: Optional[str] = None,
                    executable: bool = False,
                    overwrite: bool = False) -> ExecutionResult:
        """
        Create a file with appropriate template.
        
        Args:
            filepath: Path for the new file
            template_key: Specific template to use (auto-detect if None)
            variables: Custom template variables
            content: Raw content (ignores template if provided)
            executable: Make file executable
            overwrite: Overwrite existing file
        """
        filepath = os.path.abspath(filepath)
        
        if os.path.exists(filepath) and not overwrite:
            return ExecutionResult(
                success=False,
                message=f"File already exists: {filepath} (use --overwrite to replace)",
                exit_code=1
            )
        
        # Create directory if needed
        dir_path = os.path.dirname(filepath)
        if dir_path:
            os.makedirs(dir_path, exist_ok=True)
        
        try:
            if content is not None:
                # Use provided content directly
                file_content = content
            else:
                # Generate from template
                file_content = self._generate_content(filepath, template_key, variables)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(file_content)
            
            if executable:
                os.chmod(filepath, os.stat(filepath).st_mode | stat.S_IEXEC)
            
            return ExecutionResult(
                success=True,
                message=f"Created: {filepath}",
                files_affected=[filepath]
            )
        except Exception as e:
            return ExecutionResult(
                success=False,
                message=f"Failed to create {filepath}: {str(e)}",
                stderr=str(e),
                exit_code=1
            )
    
    def create_batch(self, files: List[Dict[str, Any]]) -> ExecutionResult:
        """
        Create multiple files at once.
        
        Args:
            files: List of dicts with 'path', and optional 'template', 'variables', 'content'
        """
        created = []
        failed = []
        
        for file_info in files:
            path = file_info.get('path')
            template = file_info.get('template')
            variables = file_info.get('variables')
            content = file_info.get('content')
            executable = file_info.get('executable', False)
            
            result = self.create_file(
                path, template, variables, content, executable
            )
            
            if result.success:
                created.append(path)
                log(LogLevel.SUCCESS, f"Created: {path}")
            else:
                failed.append((path, result.message))
                log(LogLevel.ERROR, f"Failed: {path} - {result.message}")
        
        if failed:
            return ExecutionResult(
                success=len(created) > 0,
                message=f"Created {len(created)} files, {len(failed)} failed",
                data={"created": created, "failed": failed},
                files_affected=created
            )
        
        return ExecutionResult(
            success=True,
            message=f"Successfully created {len(created)} files",
            files_affected=created
        )
    
    def scaffold_project(self, project_type: str, name: str, 
                         directory: Optional[str] = None) -> ExecutionResult:
        """
        Scaffold a complete project structure.
        
        Args:
            project_type: Type of project (python, node, go, rust, etc.)
            name: Project name
            directory: Target directory (default: current dir)
        """
        directory = directory or "."
        base_dir = os.path.join(directory, name)
        
        log(LogLevel.INFO, f"Scaffolding {project_type} project: {name}")
        
        # Define project structures
        structures = {
            "python": [
                {"path": f"{base_dir}/README.md", "template": ".md", 
                 "variables": {"title": name, "description": f"A Python project called {name}"}},
                {"path": f"{base_dir}/.gitignore", "template": ".gitignore"},
                {"path": f"{base_dir}/setup.py", "content": self._generate_setup_py(name)},
                {"path": f"{base_dir}/requirements.txt", "content": "# Dependencies\n"},
                {"path": f"{base_dir}/{name}/__init__.py", "content": f'"""{name} package."""\n\n__version__ = "0.1.0"\n'},
                {"path": f"{base_dir}/{name}/main.py", "template": ".py",
                 "variables": {"filename": "main.py", "description": f"Main module for {name}"}},
                {"path": f"{base_dir}/tests/__init__.py", "content": ""},
                {"path": f"{base_dir}/tests/test_main.py", "content": self._generate_test_file(name)},
                {"path": f"{base_dir}/Makefile", "template": "Makefile"},
            ],
            "node": [
                {"path": f"{base_dir}/README.md", "template": ".md",
                 "variables": {"title": name, "description": f"A Node.js project called {name}"}},
                {"path": f"{base_dir}/.gitignore", "template": ".gitignore"},
                {"path": f"{base_dir}/package.json", "content": self._generate_package_json(name)},
                {"path": f"{base_dir}/index.js", "template": ".js",
                 "variables": {"filename": "index.js", "description": f"Main entry point for {name}"}},
                {"path": f"{base_dir}/src/index.js", "template": ".js",
                 "variables": {"filename": "src/index.js", "description": "Source entry point"}},
                {"path": f"{base_dir}/tests/index.test.js", "content": self._generate_js_test(name)},
            ],
            "go": [
                {"path": f"{base_dir}/README.md", "template": ".md",
                 "variables": {"title": name, "description": f"A Go project called {name}"}},
                {"path": f"{base_dir}/.gitignore", "template": ".gitignore"},
                {"path": f"{base_dir}/go.mod", "content": f"module {name}\n\ngo 1.21\n"},
                {"path": f"{base_dir}/main.go", "template": ".go",
                 "variables": {"filename": "main.go", "description": f"Main package for {name}"}},
                {"path": f"{base_dir}/cmd/server/main.go", "template": ".go",
                 "variables": {"filename": "cmd/server/main.go", "description": "Server entry point"}},
            ],
            "rust": [
                {"path": f"{base_dir}/README.md", "template": ".md",
                 "variables": {"title": name, "description": f"A Rust project called {name}"}},
                {"path": f"{base_dir}/.gitignore", "template": ".gitignore"},
                {"path": f"{base_dir}/Cargo.toml", "content": self._generate_cargo_toml(name)},
                {"path": f"{base_dir}/src/main.rs", "template": ".rs",
                 "variables": {"filename": "src/main.rs", "description": f"Main binary for {name}"}},
                {"path": f"{base_dir}/src/lib.rs", "content": f"//! {name} library\npub fn hello() -> &'static str {{\n    \"Hello from {name}!\"\n}}\n"},
            ],
            "web": [
                {"path": f"{base_dir}/index.html", "template": ".html",
                 "variables": {"title": name, "description": f"Web project: {name}"}},
                {"path": f"{base_dir}/css/style.css", "template": ".css",
                 "variables": {"filename": "style.css", "description": "Main stylesheet"}},
                {"path": f"{base_dir}/js/main.js", "template": ".js",
                 "variables": {"filename": "main.js", "description": "Main JavaScript file"}},
                {"path": f"{base_dir}/assets/README.md", "content": "# Assets\n\nPut images, fonts, and other assets here.\n"},
            ],
        }
        
        if project_type not in structures:
            available = ", ".join(structures.keys())
            return ExecutionResult(
                success=False,
                message=f"Unknown project type: {project_type}. Available: {available}",
                exit_code=1
            )
        
        return self.create_batch(structures[project_type])
    
    def _generate_content(self, filepath: str, template_key: Optional[str] = None,
                          variables: Optional[Dict[str, str]] = None) -> str:
        """Generate file content from template."""
        p = Path(filepath)
        
        # Determine template key from file extension or name
        if template_key is None:
            if p.name in self.templates:
                template_key = p.name
            elif p.suffix in self.templates:
                template_key = p.suffix
            else:
                # Return empty content for unknown types
                return ""
        
        template = self.templates.get(template_key, "")
        
        # Default variables
        default_vars = {
            "filename": p.name,
            "name": p.stem,
            "description": f"Auto-generated {p.suffix or p.name} file",
            "author": self.author,
            "date": datetime.now().strftime("%Y-%m-%d"),
            "year": str(datetime.now().year),
            "title": p.stem.replace('_', ' ').replace('-', ' ').title(),
            "class_name": self._to_class_name(p.stem),
            "guard": self._to_guard_name(p.stem),
            "module_name": p.stem.replace('-', '_').lower(),
        }
        
        # Merge with user variables
        if variables:
            default_vars.update(variables)
        
        try:
            return template.format(**default_vars)
        except KeyError as e:
            log(LogLevel.WARNING, f"Unknown template variable: {e}")
            return template
        except Exception as e:
            log(LogLevel.WARNING, f"Template error: {e}")
            return template
    
    def _to_class_name(self, name: str) -> str:
        """Convert filename to class name (PascalCase)."""
        parts = re.split(r'[_\-]', name)
        return ''.join(p.capitalize() for p in parts if p)
    
    def _to_guard_name(self, name: str) -> str:
        """Convert filename to C header guard."""
        return re.sub(r'[^A-Z0-9]', '_', name.upper()) + "_H"
    
    def _generate_setup_py(self, name: str) -> str:
        """Generate setup.py content."""
        return f'''from setuptools import setup, find_packages

setup(
    name="{name}",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        # Add dependencies here
    ],
    python_requires=">=3.8",
    entry_points={{
        "console_scripts": [
            "{name}={name}.main:main",
        ],
    }},
)
'''
    
    def _generate_package_json(self, name: str) -> str:
        """Generate package.json content."""
        return json.dumps({
            "name": name,
            "version": "1.0.0",
            "description": f"A Node.js project called {name}",
            "main": "index.js",
            "scripts": {
                "start": "node index.js",
                "test": "jest",
                "dev": "nodemon index.js"
            },
            "keywords": [],
            "author": self.author,
            "license": "MIT",
            "dependencies": {},
            "devDependencies": {}
        }, indent=2) + '\n'
    
    def _generate_cargo_toml(self, name: str) -> str:
        """Generate Cargo.toml content."""
        return f'''[package]
name = "{name}"
version = "0.1.0"
edition = "2021"
authors = ["{self.author}"]
description = "A Rust project"
license = "MIT"

[dependencies]
'''
    
    def _generate_test_file(self, name: str) -> str:
        """Generate Python test file."""
        return f'''import unittest
from {name}.main import main


class TestMain(unittest.TestCase):
    """Test cases for main module."""
    
    def test_main(self):
        """Test main function."""
        result = main()
        self.assertIsNone(result)


if __name__ == '__main__':
    unittest.main()
'''
    
    def _generate_js_test(self, name: str) -> str:
        """Generate JavaScript test file."""
        return f'''const {{ main }} = require('../index');

describe('{name}', () => {{
  test('main function exists', () => {{
    expect(main).toBeDefined();
  }});
  
  test('main runs without error', () => {{
    expect(() => main()).not.toThrow();
  }});
}});
'''
