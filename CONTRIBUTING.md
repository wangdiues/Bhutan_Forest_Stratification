# Contributing to Bhutan Forest Stratification Pipeline

Thank you for considering contributing to this project! This document provides guidelines and instructions for contributing.

## 📋 Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Coding Standards](#coding-standards)
- [Testing](#testing)
- [Pull Request Process](#pull-request-process)
- [Issue Reporting](#issue-reporting)

---

## Code of Conduct

Please read and follow our [Code of Conduct](CODE_OF_CONDUCT.md). Be respectful and inclusive in all interactions.

---

## Getting Started

1. **Fork the repository** on GitHub
2. **Clone your fork** locally
3. **Create a branch** for your changes
4. **Make your changes** following our coding standards
5. **Submit a pull request**

---

## Development Setup

### Prerequisites

- Python 3.10+
- pip or conda
- Git

### Installation

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/bhutan-forest-stratification.git
cd bhutan-forest-stratification

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
.venv\Scripts\Activate.ps1  # Windows

# Install development dependencies
pip install -e ".[dev,test,docs]"

# Install pre-commit hooks
pre-commit install
```

### Verify Setup

```bash
# Run tests
pytest tests/ -v

# Check code style
pre-commit run --all-files
```

---

## Coding Standards

### Python Style

- Follow [PEP 8](https://pep8.org/) style guidelines
- Use [Black](https://black.readthedocs.io/) for code formatting
- Use [isort](https://pycqa.github.io/isort/) for import sorting
- Use [flake8](https://flake8.pycqa.org/) for linting
- Use [mypy](https://mypy.readthedocs.io/) for type checking

### Type Hints

All public functions must have type hints:

```python
from __future__ import annotations

def run_module(
    module_id: str,
    cfg: dict,
    logger: logging.Logger | None = None,
) -> dict:
    """Execute a pipeline module."""
    ...
```

### Docstrings

Use Google-style docstrings:

```python
def validate_csv(path: Path, required_columns: list[str]) -> ValidationResult:
    """
    Validate a CSV file against expected schema.
    
    Args:
        path: Path to CSV file
        required_columns: List of required column names
        
    Returns:
        ValidationResult with status and any errors
        
    Raises:
        FileNotFoundError: If CSV file doesn't exist
        ValidationError: If required columns are missing
    """
    ...
```

### Naming Conventions

| Type | Convention | Example |
|------|------------|---------|
| Variables | snake_case | `plot_id`, `species_matrix` |
| Functions | snake_case | `run_module`, `validate_output` |
| Classes | PascalCase | `ValidationError`, `PipelineConfig` |
| Constants | UPPER_SNAKE_CASE | `MAX_WORKERS`, `DEFAULT_SEED` |
| Private | Leading underscore | `_internal_function`, `_cache` |

---

## Testing

### Running Tests

```bash
# All tests
pytest tests/ -v

# With coverage
pytest tests/ --cov=python --cov-report=html

# Specific test file
pytest tests/test_smoke.py -v

# Specific test
pytest tests/test_config.py::test_config_detect_root -v
```

### Writing Tests

- Place tests in `tests/` directory
- Name test files `test_*.py`
- Use descriptive test names: `test_<function>_<scenario>_<expected>`
- Aim for >80% code coverage

Example:

```python
def test_run_module_success(config):
    """Module should return success status with outputs."""
    result = run_module("00", config)
    
    assert result["status"] == "success"
    assert len(result["outputs"]) > 0
    assert "runtime_sec" in result
```

### Test Fixtures

Use fixtures from `conftest.py`:

```python
def test_something(config, project_root, tmp_path):
    # config: loaded configuration
    # project_root: Path to project root
    # tmp_path: pytest temporary directory
    ...
```

---

## Pull Request Process

### Before Submitting

1. **Update documentation** if adding/changing functionality
2. **Add tests** for new features
3. **Run all tests** and ensure they pass
4. **Run pre-commit** hooks and fix any issues
5. **Update CHANGELOG.md** with your changes

### PR Template

When creating a PR, please include:

- [ ] Tests added/updated
- [ ] Documentation updated
- [ ] CHANGELOG.md updated
- [ ] Pre-commit checks pass

### Review Process

1. Maintainer reviews code within 3-5 business days
2. Address any feedback or requested changes
3. Once approved, PR will be merged
4. CI/CD pipeline will run automatically

---

## Issue Reporting

### Bug Reports

Use the [Bug Report](.github/ISSUE_TEMPLATE/bug_report.md) template and include:

- Clear description of the issue
- Steps to reproduce
- Expected vs actual behavior
- Python version and OS
- Error messages/tracebacks

### Feature Requests

Use the [Feature Request](.github/ISSUE_TEMPLATE/feature_request.md) template and include:

- Clear description of the feature
- Use case and motivation
- Proposed implementation (optional)
- Any relevant examples

---

## Module Development

### Creating a New Module

1. Create `python/modules/XX_module_name.py`
2. Implement `module_run(config: dict) -> dict`
3. Add to registry in `python/run_pipeline.py`
4. Add tests in `tests/test_modules.py`
5. Update documentation

### Module Template

```python
from __future__ import annotations

import time
from pathlib import Path

from python.utils import ensure_dirs


def module_run(config: dict) -> dict:
    """
    Execute the module analysis.
    
    Args:
        config: Pipeline configuration dictionary
        
    Returns:
        Dictionary with status, outputs, warnings, runtime_sec
    """
    t0 = time.time()
    output_dir = ensure_dirs("XX_module_name", config)
    
    try:
        # Your analysis code here
        result = {
            "status": "success",
            "outputs": [str(output_file)],
            "warnings": [],
            "runtime_sec": time.time() - t0,
        }
    except Exception as e:
        result = {
            "status": "failed",
            "outputs": [],
            "warnings": [str(e)],
            "runtime_sec": time.time() - t0,
        }
    
    return result
```

---

## Questions?

- Check existing [documentation](context/)
- Search [closed issues](https://github.com/YOUR_USERNAME/bhutan-forest-stratification/issues?q=is%3Aissue+is%3Aclosed)
- Start a [discussion](https://github.com/YOUR_USERNAME/bhutan-forest-stratification/discussions)

Thank you for contributing! 🎉
