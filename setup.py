"""Setup configuration for Internet Performance Optimizer."""

from setuptools import setup, find_packages
from pathlib import Path

# Read README for long description
readme_path = Path(__file__).parent / "README.md"
long_description = readme_path.read_text(encoding="utf-8") if readme_path.exists() else ""

setup(
    name="internet-performance-optimizer",
    version="0.1.0",
    author="IPO Contributors",
    author_email="ipo@example.com",
    description="Measurement-first, reversible network optimization tool",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/internet-performance-optimizer",
    packages=find_packages(exclude=["tests", "tests.*"]),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: End Users/Desktop",
        "Intended Audience :: System Administrators",
        "Topic :: System :: Networking",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Operating System :: Microsoft :: Windows :: Windows 10",
        "Operating System :: Microsoft :: Windows :: Windows 11",
    ],
    python_requires=">=3.9",
    install_requires=[
        "click>=8.0.0",
        "psutil>=5.9.0",
        "ping3>=4.0.0",
        "requests>=2.28.0",
        "pydantic>=2.0.0",
        "rich>=13.0.0",
        "PyQt6>=6.5.0",
        "matplotlib>=3.7.0",
        "numpy>=1.24.0",
        "pandas>=2.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "pytest-asyncio>=0.21.0",
            "black>=23.0.0",
            "flake8>=6.0.0",
            "mypy>=1.0.0",
            "isort>=5.12.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "ipo=ipo.cli.main:cli",
        ],
    },
    include_package_data=True,
    package_data={
        "ipo": ["templates/*.txt", "schemas/*.json"],
    },
    project_urls={
        "Bug Reports": "https://github.com/yourusername/internet-performance-optimizer/issues",
        "Source": "https://github.com/yourusername/internet-performance-optimizer",
        "Documentation": "https://github.com/yourusername/internet-performance-optimizer/docs",
    },
)
