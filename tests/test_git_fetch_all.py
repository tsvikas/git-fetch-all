"""Tests for git_fetch_all core functionality."""

from pathlib import Path

from git import GitCommandError
from pytest_mock import MockerFixture

from git_fetch_all.git_fetch_all import (
    print_report,
)


def test_print_report_with_error(mocker: MockerFixture, tmp_path: Path) -> None:
    """Test printing results with errors."""
    mock_print = mocker.patch("builtins.print")
    mock_indent = mocker.patch(
        "git_fetch_all.git_fetch_all.indent", return_value="    error message"
    )

    error = GitCommandError("git fetch", stderr="fetch failed")
    fetch_results: dict[tuple[Path, str], Exception | bool] = {
        (tmp_path / "repo1", "origin"): error,
    }

    result = print_report(fetch_results, tmp_path)

    assert result is True  # Has errors
    mock_print.assert_any_call("𐄂 repo1:origin")
    mock_print.assert_any_call("    error message")
    mock_indent.assert_called_once_with("stderr: 'fetch failed'", "    ")


def test_print_report_quiet_mode(mocker: MockerFixture, tmp_path: Path) -> None:
    """Test quiet mode only shows errors."""
    mock_print = mocker.patch("builtins.print")

    error = Exception("some error")
    fetch_results: dict[tuple[Path, str], Exception | bool] = {
        (tmp_path / "repo1", "origin"): True,  # Success - should be hidden
        (tmp_path / "repo2", "origin"): error,  # Error - should be shown
    }

    result = print_report(fetch_results, tmp_path, quiet=True)

    assert result is True
    assert mock_print.call_count == 2  # Only error output
    mock_print.assert_any_call("𐄂 repo2:origin")


def test_print_report_with_color(mocker: MockerFixture, tmp_path: Path) -> None:
    """Test colored output for errors."""
    mock_print = mocker.patch("builtins.print")
    error = Exception("test error")
    fetch_results: dict[tuple[Path, str], Exception | bool] = {
        (tmp_path / "repo1", "origin"): True,
        (tmp_path / "repo2", "origin"): error,
    }

    result = print_report(fetch_results, tmp_path, color=True)

    assert result is True
    mock_print.assert_any_call("✓ repo1:origin")
    mock_print.assert_any_call("\033[31m𐄂 repo2:origin\033[0m")


def test_print_report_git_command_error(mocker: MockerFixture, tmp_path: Path) -> None:
    """Test handling GitCommandError specifically."""
    mock_indent = mocker.patch(
        "git_fetch_all.git_fetch_all.indent", return_value="    stripped error"
    )
    error = GitCommandError("git fetch", stderr="  error with whitespace  ")
    fetch_results: dict[tuple[Path, str], Exception | bool] = {
        (tmp_path / "repo1", "origin"): error,
    }

    print_report(fetch_results, tmp_path)

    mock_indent.assert_called_once_with("stderr: '  error with whitespace  '", "    ")
