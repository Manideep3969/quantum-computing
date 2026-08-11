# Contributing to qc-compiler

Thank you for your interest in contributing! This document covers everything you need to get started.

## Quick Links

- [Report a Bug](https://github.com/Manideep3969/quantum-computing/issues/new?template=bug_report.md)
- [Request a Feature](https://github.com/Manideep3969/quantum-computing/issues/new?template=feature_request.md)
- [Ask a Question](https://github.com/Manideep3969/quantum-computing/issues/new?template=question.md)

## Development Setup

1. **Fork and clone** the repository
2. **Create a virtual environment** and install with dev dependencies:

```bash
python -m venv venv
source venv/bin/activate
pip install -e ".[dev]"
```

3. **Run the test suite** to verify everything works:

```bash
pytest
```

4. **Lint your code** before committing:

```bash
ruff check src/ tests/
black --check src/ tests/
```

## Making Changes

### Branch Naming

Use descriptive branch names with a prefix:

| Type | Example |
|------|---------|
| Bug fix | `fix/issue-12-alap-scheduling` |
| Feature | `feat/cutting-subcircuits` |
| Documentation | `docs/add-api-reference` |
| Refactor | `refactor/extract-cost-model` |
| Test | `test/add-mitigation-coverage` |

### Commit Messages

Write clear, concise commit messages. Use [Conventional Commits](https://www.conventionalcommits.org/) style:

```
feat(scheduling): add coherence-aware priority queue
fix(cutting): preserve all subcircuits after circuit cutting
docs: add CONTRIBUTING.md
test(cost-model): add QFT circuit metrics test
```

### Code Style

- **Line length**: 100 characters (enforced by ruff and black)
- **Target Python**: 3.10+
- **Type hints**: Encouraged but not required
- **Docstrings**: Use Google-style docstrings for public APIs
- **Imports**: Sorted by ruff/isort rules

### Tests

- All new features must include tests
- Bug fixes should include a regression test
- Run the full suite before pushing:

```bash
pytest
```

- For coverage reports:

```bash
pytest --cov=qc_compiler --cov-report=term-missing
```

We enforce a minimum coverage threshold. If your changes drop coverage below the threshold, add the missing tests.

### Notebooks

If you modify validation notebooks, verify they convert to scripts without errors:

```bash
jupyter nbconvert --to script notebooks/*.ipynb
```

CI also runs this check automatically.

## Pull Request Process

1. **Update your branch** with the latest `main` before opening a PR
2. **Ensure all CI checks pass** (lint, tests across Python 3.10-3.13, notebook validation)
3. **Add tests** for any new functionality or bug fixes
4. **Update documentation** (README, docstrings, CHANGELOG) if applicable
5. **Keep PRs focused** — one logical change per PR
6. **Respond to reviews** promptly and push fixes as new commits

### PR Checklist

Before submitting, verify:

- [ ] All tests pass locally
- [ ] `ruff check src/ tests/` passes with no errors
- [ ] `black --check src/ tests/` passes with no errors
- [ ] New code has corresponding tests
- [ ] CHANGELOG.md updated (if applicable)
- [ ] Public APIs have docstrings

## Project Structure

```
src/qc_compiler/
  autotuning.py    # Hardware-aware transpilation
  batching.py      # Circuit batching
  cost_model.py    # Unified cost model
  cutting.py       # Circuit cutting
  fusion.py        # Gate fusion
  mitigation.py    # Adaptive error mitigation
  scheduling.py    # Decoherence budget scheduling
  transpiler.py    # Pipeline orchestrator
  utils.py         # Shared utilities
tests/
  test_autotuning.py
  test_batching.py
  test_cost_model.py
  test_cutting.py
  test_fusion.py
  test_mitigation.py
  test_scheduling.py
  test_transpiler.py
  test_utils.py
  conftest.py       # Shared fixtures
notebooks/          # Validation notebooks
```

## Reporting Issues

### Bug Reports

Include:
- Python version and OS
- qc-compiler version (`pip show qc-compiler`)
- Minimal reproducible example
- Expected vs. actual behavior
- Full error traceback

### Feature Requests

Include:
- Use case and motivation
- Proposed API or behavior
- Any relevant quantum computing background

## Getting Help

- Open an issue with the [question template](https://github.com/Manideep3969/quantum-computing/issues/new?template=question.md)
- Start a [GitHub Discussion](https://github.com/Manideep3969/quantum-computing/discussions)

## License

By contributing, you agree that your contributions will be licensed under the [MIT License](LICENSE).