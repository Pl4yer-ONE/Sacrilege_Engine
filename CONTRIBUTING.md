# Contributing to Sacrilege Engine

Thank you for your interest in contributing to Sacrilege Engine. This document outlines our standards and processes.

## Code Standards

### Style
- Follow PEP 8 for Python code
- Use type hints for all function signatures
- Docstrings for all public functions and classes
- Maximum line length: 100 characters

### Architecture
- Keep modules focused and single-purpose
- Use dependency injection where appropriate
- All new features require corresponding tests
- Document any changes to data models

## Pull Request Process

1. **Fork** the repository
2. **Create** a feature branch (`git checkout -b feature/amazing-feature`)
3. **Write** your code with tests
4. **Commit** with clear messages following conventional commits
5. **Push** to your fork
6. **Open** a Pull Request with description of changes

### Commit Messages

```
type(scope): description

feat: new feature
fix: bug fix
docs: documentation
refactor: code restructuring
test: adding tests
```

## Development Setup

```bash
git clone https://github.com/Pl4yer-ONE/Sacrilege_Engine.git
cd Sacrilege_Engine
python -m venv venv
source venv/bin/activate
pip install -e ".[dev]"
```

## Code of Conduct

- Be respectful and constructive
- Focus on the code, not the person
- Help others learn and grow

## Questions?

Open an issue with the `question` label.

---

© 2026 Pl4yer-ONE. All rights reserved.
