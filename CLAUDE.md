# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

This project uses `uv` and `just` for development workflow:

### Setup

- `uv run just prepare` - Set up development environment after cloning

### Code Quality

- `uv run just test` - Run pytest tests with coverage
- `uv run just lint` - Run ruff check and mypy type checking
- `uv run just format` - Format code with black and sort imports
- `uv run just check` - Run all quality checks (test, lint, pre-commit)
- `uv run just format-and-check` - Run both. Use this to test before committing

### Individual Tools

- `uv run pytest` - Run tests directly
- `uv run mypy` - Type check with mypy
- `uv run ruff check` - Lint with ruff
- `uv run black .` - Format code with black
- `uv run pre-commit run --all-files` - Run all pre-commit hooks

## Project Architecture

This is a Python CLI tool that asynchronously fetches git remotes from multiple repositories in subdirectories.

### Core Components

- **CLI Entry Point**: `src/git_fetch_all/cli.py` - Typer-based command line interface with options for recursion depth, remote filtering, output formatting
- **Core Logic**: `src/git_fetch_all/git_fetch_all.py` - Async implementation using ThreadPoolExecutor for git operations:
  - `fetch_remote()` - Fetches single remote asynchronously
  - `fetch_single_repo()` - Fetches all remotes for one repository
  - `fetch_remotes_in_subfolders()` - Recursively finds and processes git repos
  - `print_report()` - Formats and displays results with status symbols

### Key Technologies

- **GitPython** for git operations
- **Typer** for CLI interface
- **asyncio** with ThreadPoolExecutor for concurrent git fetches
- **uv** for dependency management and task running

### Testing

- Tests in `tests/` directory using pytest
- Coverage tracking enabled with `--cov=src/git_fetch_all`
- Pre-commit hooks for code quality.
  If the pre-commit fails, remember to `git add` the changed files.

### Code Style

- Strict type checking with mypy
- Ruff for linting with comprehensive rule set
- Black for code formatting
- Google-style docstring conventions
