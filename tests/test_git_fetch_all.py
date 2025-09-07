"""Tests for git_fetch_all core functionality."""

from pathlib import Path

from git import GitCommandError

from git_fetch_all.git_fetch_all import (
    format_report,
)


def test_format_report_with_error() -> None:
    """Test printing results with errors."""
    base_dir = Path("/fake-path")
    error = GitCommandError("git fetch", stderr="fetch failed")
    fetch_results: dict[tuple[Path, str], Exception | bool] = {
        (base_dir / "repo1", "origin"): error,
    }
    result = format_report(fetch_results, base_dir)
    assert result == "𐄂 repo1:origin\n    stderr: 'fetch failed'"


def test_format_report_quiet_mode() -> None:
    """Test quiet mode only shows errors."""
    base_dir = Path("/fake-path")
    error = Exception("some error")
    fetch_results: dict[tuple[Path, str], Exception | bool] = {
        (base_dir / "repo1", "origin"): True,
        (base_dir / "repo2", "origin"): False,
        (base_dir / "repo3", "origin"): error,
    }
    result = format_report(fetch_results, base_dir, quiet=True)
    assert result == "𐄂 repo3:origin\n    some error"


def test_format_report_with_color() -> None:
    """Test colored output for errors."""
    base_dir = Path("/fake-path")
    error = Exception("test error")
    fetch_results: dict[tuple[Path, str], Exception | bool] = {
        (base_dir / "repo1", "origin"): True,
        (base_dir / "repo2", "origin"): False,
        (base_dir / "repo3", "origin"): error,
    }
    result = format_report(fetch_results, base_dir, color=True)
    color_start = "\033[31m"
    color_end = "\033[0m"
    assert (
        result == "✓ repo1:origin\n- repo2:origin\n"
        f"{color_start}𐄂 repo3:origin{color_end}\n    test error"
    )
