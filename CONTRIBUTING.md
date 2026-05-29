# Contributing

## Development Setup

Create the virtual environment with system site packages enabled:

```bash
python3.12 -m venv --system-site-packages .venv
.venv/bin/pip install -e ".[dev]"
```

The `--system-site-packages` flag is required on Ubuntu because GTK and
PyGObject bindings are provided by OS packages, not by normal Python wheels.

## Tests

Run linting:

```bash
.venv/bin/ruff check .
```

Run tests:

```bash
.venv/bin/python -m pytest
```

## Commit Style

Use short, conventional commit-style messages:

```text
docs: clarify local whisper setup
fix: handle missing clipboard command
test: cover systemd service install
```

## Pull Requests

- Keep PRs focused on one behavior or documentation area.
- Add or update tests for behavior changes.
- Update docs for user-facing changes.
- Do not add new input-device permissions without a security note explaining
  what access is granted and why it is needed.
