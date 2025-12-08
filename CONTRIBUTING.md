# Contributing to CognitiveOS

Thank you for your interest in contributing! See the full [Contributing Guide](docs/contributing.md) for detailed information.

## Quick Start

```bash
# Fork and clone
git clone https://github.com/YOUR-USERNAME/CognitiveOS.git
cd CognitiveOS

# Setup environment
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt

# Create branch
git checkout -b feat/your-feature

# Run tests
pytest tests/ -v

# Commit with conventional format
git commit -m "feat: Add your feature"
```

## Commit Format

```
type: Short description

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Your Name <your@email.com>
```

Types: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`

## Pull Request Checklist

- [ ] Tests pass (`pytest tests/ -v`)
- [ ] Documentation updated if needed
- [ ] CHANGELOG.md updated
- [ ] Follows code style conventions

## License

MIT License - contributions are licensed under the same terms.
