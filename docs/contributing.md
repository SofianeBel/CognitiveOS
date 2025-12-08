# Contributing

Thank you for your interest in contributing to CognitiveOS!

## Getting Started

### 1. Fork and Clone

```bash
git clone https://github.com/YOUR-USERNAME/CognitiveOS.git
cd CognitiveOS
```

### 2. Set Up Development Environment

```bash
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
```

### 3. Create a Branch

```bash
git checkout -b feat/your-feature-name
```

## Development Workflow

### Running Tests

```bash
# All tests
pytest tests/ -v

# With coverage
pytest tests/ -v --cov=src

# Specific test file
pytest tests/test_memory.py -v

# Skip slow tests
pytest tests/ -v -m "not slow"
```

### Code Style

We follow standard Python conventions:

- **PEP 8** for code style
- **Google-style docstrings** for documentation
- **Type hints** for function signatures

Example:
```python
def search_similar(
    self,
    query: str,
    top_k: int = 10,
    threshold: float = 0.7
) -> List[Tuple[Node, float]]:
    """
    Search for semantically similar nodes.

    Args:
        query: Natural language search query.
        top_k: Maximum results to return.
        threshold: Minimum similarity score.

    Returns:
        List of (node, score) tuples.
    """
```

### Commit Messages

Use conventional commits format:

```
type: Short description

Longer description if needed.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Your Name <your@email.com>
```

Types:
- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation
- `refactor:` Code refactoring
- `test:` Adding tests
- `chore:` Maintenance

### Pull Request Process

1. **Update documentation** if you changed functionality
2. **Add tests** for new features
3. **Update CHANGELOG.md** with your changes
4. **Run tests** to ensure nothing breaks
5. **Create PR** with clear description

## Project Structure

```
CognitiveOS/
├── src/
│   ├── agents/          # LLM agents (extraction, factory)
│   ├── memory/          # Graph, database, embeddings
│   ├── consolidation/   # Memory optimization
│   └── config.py        # Configuration
├── tests/               # Unit tests
├── docs/                # Documentation (MkDocs)
├── data/                # Storage files
├── main.py              # CLI entry point
└── app.py               # Streamlit entry point
```

## Areas for Contribution

### Good First Issues

- Documentation improvements
- Test coverage expansion
- Bug fixes
- Error message improvements

### Feature Ideas

- Additional entity types
- New relation types
- Alternative embedding models
- Export formats (CSV, RDF)
- Performance optimizations

### Documentation

- Tutorial improvements
- API documentation
- Architecture diagrams
- Translation

## Testing Requirements

### Unit Tests

Every new feature should have tests:

```python
# tests/test_feature.py
import pytest
from src.module import Feature

class TestFeature:
    def test_basic_functionality(self):
        feature = Feature()
        result = feature.do_something()
        assert result == expected

    def test_edge_case(self):
        feature = Feature()
        with pytest.raises(ValueError):
            feature.do_something_invalid()
```

### Integration Tests

For features that interact with external services:

```python
@pytest.mark.integration
def test_llm_integration():
    # Requires actual API key
    pass
```

Run with:
```bash
pytest tests/ -v -m integration
```

## Documentation

### Updating Docs

Documentation is in `docs/` using MkDocs:

```bash
# Install MkDocs
pip install mkdocs-material

# Preview locally
mkdocs serve

# Build static site
mkdocs build
```

### Doc Style Guide

- Use clear, concise language
- Include code examples
- Add cross-references (`[Link](other-page.md)`)
- Use admonitions for warnings/notes

```markdown
!!! warning "Important"
    This is a warning message.

!!! note
    This is a note.
```

## Code Review

### What We Look For

- **Correctness** - Does it work as intended?
- **Tests** - Are edge cases covered?
- **Documentation** - Is it clear how to use?
- **Style** - Does it follow conventions?
- **Performance** - Any obvious issues?

### Review Process

1. Automated checks run on PR
2. Maintainer reviews code
3. Feedback addressed
4. Approved and merged

## Versioning

We use [Semantic Versioning](https://semver.org/):

- **MAJOR** - Breaking changes
- **MINOR** - New features (backward compatible)
- **PATCH** - Bug fixes

Current version: **v0.3.0** (pre-1.0, breaking changes may occur)

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

## Questions?

- Open an issue for questions
- Check existing issues first
- Be respectful and constructive

Thank you for contributing to CognitiveOS!
