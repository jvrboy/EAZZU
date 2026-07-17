"""
Setup script for Deriv Scalper Bot
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read README
readme_file = Path(__file__).parent / "README.md"
long_description = ""
if readme_file.exists():
    long_description = readme_file.read_text(encoding='utf-8')

setup(
    name="deriv-scalper-bot",
    version="1.0.0",
    description="24/7 Perpetual Scalping Bot for Deriv Volatility Indices",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="MiniMax Agent",
    author_email="support@example.com",
    url="https://github.com/example/deriv-scalper-bot",
    packages=find_packages(exclude=["tests", "tests.*"]),
    include_package_data=True,
    install_requires=[
        "websockets>=10.0",
        "asyncio-throttle>=1.0.2",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.18.0",
            "black>=22.0.0",
            "flake8>=4.0.0",
        ],
        "analysis": [
            "numpy>=1.21.0",
            "pandas>=1.3.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "deriv-scalper=main:main",
            "deriv-scalper-gui=main:run_gui",
            "deriv-scaler-cli=main:run_cli",
            "deriv-scaler-backtest=main:run_backtest",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Financial and Insurance Industry",
        "Topic :: Office/Business :: Financial :: Investment",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
)
