# Contributing to Internet Performance Optimizer

Thank you for your interest in contributing to IPO! This document provides guidelines and instructions for contributing.

## Code of Conduct

Be respectful, constructive, and professional. We're all here to build better network tools.

## How to Contribute

### Reporting Bugs

Before creating bug reports, please check existing issues. When creating a bug report, include:

1. **IPO version**: Run `ipo --version`
2. **System info**: Run `ipo info --output sysinfo.json` and attach
3. **Benchmark artifact**: If related to measurement, include your `.json` benchmark file
4. **Steps to reproduce**: Detailed steps to reproduce the issue
5. **Expected behavior**: What you expected to happen
6. **Actual behavior**: What actually happened
7. **Logs**: Attach log file from `%APPDATA%\IPO\logs\ipo.log` (Windows) or `~/.ipo/logs/ipo.log` (Unix)

**Template**:
```markdown
**IPO Version**: 0.1.0
**OS**: Windows 11 22H2
**Python**: 3.11.5

**Description**:
Brief description of the issue

**Steps to Reproduce**:
1. Run `ipo bench --target 1.1.1.1`
2. Wait for completion
3. Error occurs at...

**Expected**: Benchmark should complete successfully
**Actual**: Benchmark fails with error...

**Attached**:
- benchmark.json
- sysinfo.json
- ipo.log
```

### Suggesting Enhancements

Enhancement suggestions are welcome! Include:

1. **Use case**: Describe the problem you're trying to solve
2. **Proposed solution**: Your idea for how to solve it
3. **Alternatives**: Other approaches you've considered
4. **Impact**: Who would benefit from this enhancement

### Code Contributions

#### Development Setup

1. Fork and clone the repository:
```bash
git clone https://github.com/YOUR_USERNAME/internet-performance-optimizer.git
cd internet-performance-optimizer
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install development dependencies:
```bash
pip install -e ".[dev]"
```

4. Install pre-commit hooks:
```bash
pre-commit install
```

#### Development Workflow

1. **Create a branch**:
```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/bug-description
```

2. **Make changes**:
   - Write code following our style guide (below)
   - Add tests for new functionality
   - Update documentation as needed

3. **Run tests**:
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=ipo --cov-report=html

# Run specific test file
pytest tests/test_bench_parsers.py -v
```

4. **Check code quality**:
```bash
# Format code
black .
isort .

# Lint
flake8 .

# Type check (optional but encouraged)
mypy ipo --ignore-missing-imports
```

5. **Commit changes**:
```bash
git add .
git commit -m "feat: add feature description"
# or
git commit -m "fix: fix bug description"
```

**Commit Message Format**:
```
<type>: <short summary>

<optional detailed description>

<optional footer>
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

6. **Push and create pull request**:
```bash
git push origin feature/your-feature-name
```

Then create a PR on GitHub.

#### Pull Request Guidelines

**PR Description Template**:
```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] All tests pass
- [ ] Added new tests for new functionality
- [ ] Manually tested on Windows/Linux

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-reviewed my code
- [ ] Commented complex code sections
- [ ] Updated documentation
- [ ] No new warnings
- [ ] Added tests with good coverage
- [ ] All tests pass locally

## Security Checklist
- [ ] No shell=True with user input
- [ ] File paths validated
- [ ] User input sanitized
- [ ] No secrets in code
- [ ] Changes are reversible
- [ ] Admin operations require consent

## Screenshots (if applicable)

## Related Issues
Fixes #issue_number
```

**PR Review Process**:
1. Automated CI checks must pass
2. At least one maintainer approval required
3. No unresolved review comments
4. All conversations resolved

### Code Style Guide

#### Python Code

**Formatting**: Use Black (line length: 100)

**Imports**: Use isort with Black compatibility

**Order**:
```python
# Standard library
import os
import sys
from typing import List, Dict

# Third-party
import click
from pydantic import BaseModel

# Local
from ipo.core.measurement import run_benchmark
from ipo.core.utils import get_logger
```

**Type Hints**: Always use type hints
```python
def calculate_percentile(data: List[float], percentile: float) -> float:
    """Calculate percentile from sorted data."""
    ...
```

**Docstrings**: Use Google-style docstrings
```python
def run_benchmark(
    target: str,
    ping_count: int = 1000
) -> tuple[BenchmarkResult, Path]:
    """
    Run network performance benchmark.
    
    Args:
        target: Target host for testing
        ping_count: Number of ping samples
    
    Returns:
        Tuple of (BenchmarkResult, output_path)
    
    Raises:
        RuntimeError: If benchmark fails
    
    Examples:
        >>> result, path = run_benchmark("1.1.1.1", count=100)
        >>> print(result.icmp.p50)
        12.3
    """
    ...
```

**Logging**:
```python
logger = get_logger(__name__)

# Use appropriate levels
logger.debug("Detailed execution info")
logger.info("User-facing operations")
logger.warning("Non-fatal issues")
logger.error("Operation failures")
```

**Error Handling**:
```python
# Specific exceptions
try:
    result = measure_throughput()
except RuntimeError as e:
    logger.error(f"Throughput measurement failed: {e}")
    # Provide fallback or user guidance
    
# Don't catch bare Exception unless truly necessary
```

#### Security Guidelines

**MUST**:
- Validate all user inputs
- Use `subprocess.run()` with list arguments (not `shell=True`)
- Sanitize file paths (prevent traversal)
- Log security-sensitive operations
- Require explicit consent for system changes

**MUST NOT**:
- Execute commands with `shell=True` and user input
- Store secrets or credentials
- Disable security features permanently
- Collect PII without consent
- Install kernel drivers

### Testing Guidelines

#### Test Coverage

**Target**: >80% coverage for core modules

**Required Tests**:
- Unit tests for all new functions/classes
- Integration tests for workflows
- Schema validation tests
- Error handling tests

**Test Structure**:
```python
class TestPingMeasurement:
    """Tests for ICMP ping measurement."""
    
    def test_compute_statistics_valid_samples(self):
        """Test statistics computation with valid samples."""
        # Arrange
        config = PingConfig(target="1.1.1.1", count=100)
        measurement = PingMeasurement(config)
        samples = [10.0 + i * 0.5 for i in range(95)]
        
        # Act
        result = measurement._compute_statistics(samples=samples, failures=5)
        
        # Assert
        assert result.samples == 100
        assert result.packet_loss == 5.0
        assert 30.0 < result.p50 < 35.0
```

**Fixtures**:
```python
@pytest.fixture
def sample_benchmark():
    """Fixture providing sample benchmark result."""
    return BenchmarkResult(...)
```

**Mocking**:
```python
@patch('subprocess.run')
def test_ping_parsing(mock_run):
    """Test ping output parsing."""
    mock_run.return_value = Mock(
        returncode=0,
        stdout="Reply from 1.1.1.1: time=12ms"
    )
    # Test implementation
```

### Documentation

#### Required Documentation Updates

When adding features, update:

1. **README.md**: User-facing changes
2. **docs/architecture.md**: Architectural changes
3. **Docstrings**: All new functions/classes
4. **CHANGELOG.md**: All notable changes

#### Documentation Style

- Use clear, concise language
- Include code examples
- Provide context (why, not just what)
- Link to related documentation

### Release Process

**Version Numbering**: Semantic Versioning (MAJOR.MINOR.PATCH)

**Release Checklist**:
1. Update version in `setup.py` and `ipo/__init__.py`
2. Update `CHANGELOG.md`
3. Run full test suite
4. Create release tag: `git tag v0.1.0`
5. Push tag: `git push origin v0.1.0`
6. GitHub Actions builds and publishes

### Community

**Communication Channels**:
- GitHub Issues: Bug reports, feature requests
- GitHub Discussions: Questions, ideas
- Pull Requests: Code contributions

**Getting Help**:
- Check existing issues and documentation
- Ask in GitHub Discussions
- Ping maintainers in PR comments

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

All contributors must agree:
- Code is original or properly attributed
- You have rights to contribute the code
- Contribution is under MIT license

## Recognition

Contributors are recognized in:
- Git commit history
- CHANGELOG.md
- Release notes
- README.md (for significant contributions)

## Questions?

Don't hesitate to ask! Open an issue or discussion if anything is unclear.

Thank you for contributing to IPO! 🚀
