#!/usr/bin/env python3
"""
DevToolkit - Entry point for python -m devtoolkit
"""

import sys
from .cli import main

if __name__ == '__main__':
    sys.exit(main())
