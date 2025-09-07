"""Tests for git_fetch_all core functionality."""

from pathlib import Path

from git import GitCommandError, Repo
from pytest_mock import MockerFixture

from git_fetch_all.git_fetch_all import (
    fetch_remotes_in_subfolders,
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


def test_fetch_remotes_in_subfolders_no_git_repos(tmp_path: Path) -> None:
    """Test with directory that has no git repositories."""
    result = fetch_remotes_in_subfolders(tmp_path)
    assert result == {}


def test_fetch_remotes_in_subfolders_with_mock_fetch(
    tmp_path: Path, mocker: MockerFixture
) -> None:
    """Test fetch_remotes_in_subfolders with mocked git fetch."""
    # Create a fake git repo directory structure
    git_repo_dir = tmp_path / "test_repo"
    git_repo_dir.mkdir()
    Repo.init(git_repo_dir)

    # Simulate not up-to-date
    mock_fetch_info = mocker.Mock()
    mock_fetch_info.flags = 0 << 2
    mock_remote = mocker.Mock()
    mock_remote.name = "origin"
    mock_remote.fetch = mocker.Mock(return_value=[mock_fetch_info])
    mocker.patch("git.Repo.remotes", [mock_remote])

    result = fetch_remotes_in_subfolders(tmp_path)
    assert result == {(git_repo_dir, "origin"): True}

    # Simulate up-to-date
    mock_fetch_info = mocker.Mock()
    mock_fetch_info.flags = 1 << 2
    mock_remote = mocker.Mock()
    mock_remote.name = "origin"
    mock_remote.fetch = mocker.Mock(return_value=[mock_fetch_info])
    mocker.patch("git.Repo.remotes", [mock_remote])

    result = fetch_remotes_in_subfolders(tmp_path)
    assert result == {(git_repo_dir, "origin"): False}


def test_fetch_remotes_in_subfolders_recurse_zero(
    tmp_path: Path, mocker: MockerFixture
) -> None:
    """Test with recurse=0 - should not process subdirectories."""
    # Create a fake git repo directory structure
    git_repo_dir = tmp_path / "test_repo"
    git_repo_dir.mkdir()
    Repo.init(git_repo_dir)

    # Simulate not up-to-date
    mock_fetch_info = mocker.Mock()
    mock_fetch_info.flags = 0 << 2
    mock_remote = mocker.Mock()
    mock_remote.name = "origin"
    mock_remote.fetch = mocker.Mock(return_value=[mock_fetch_info])
    mocker.patch("git.Repo.remotes", [mock_remote])

    result = fetch_remotes_in_subfolders(tmp_path, recurse=0)

    # With recurse=0, should only check tmp_path itself, not subdirectories
    # Since tmp_path has no .git, result should be empty
    assert result == {}


def test_fetch_remotes_in_subfolders_exclude_dirnames(
    tmp_path: Path, mocker: MockerFixture
) -> None:
    """Test excluding specific directory names."""
    # Create directories
    normal_dir = tmp_path / "normal_repo"
    normal_dir.mkdir()
    Repo.init(normal_dir)

    excluded_dir = tmp_path / "do-not-fetch"
    excluded_dir.mkdir()
    Repo.init(excluded_dir)

    # Simulate not up-to-date
    mock_fetch_info = mocker.Mock()
    mock_fetch_info.flags = 0 << 2
    mock_remote = mocker.Mock()
    mock_remote.name = "origin"
    mock_remote.fetch = mocker.Mock(return_value=[mock_fetch_info])
    mocker.patch("git.Repo.remotes", [mock_remote])

    # Mock the directory traversal to simulate finding repos
    # The key is that node_modules should be excluded from traversal
    result = fetch_remotes_in_subfolders(tmp_path, exclude_dirnames=["do-not-fetch"])

    # Even if both directories had git repos, node_modules should be excluded
    # Since neither has actual git repos, both should be empty
    # But the important test is that the function doesn't crash and respects
    # exclude_dirnames
    assert result == {(normal_dir, "origin"): True}


def test_fetch_remotes_in_subfolders_with_git_error(
    tmp_path: Path, mocker: MockerFixture
) -> None:
    """Test handling of GitCommandError during fetch."""
    # Create a fake git repo
    git_repo = tmp_path / "test_repo"
    git_repo.mkdir()
    Repo.init(git_repo)

    # Mock Remote.fetch to raise GitCommandError
    mock_fetch_info = mocker.Mock()
    mock_fetch_info.flags = 0 << 2
    mock_remote = mocker.Mock()
    mock_remote.name = "origin"
    error = GitCommandError("git fetch", stderr="network error")
    mock_remote.fetch = mocker.Mock(side_effect=error)
    mocker.patch("git.Repo.remotes", [mock_remote])

    result = fetch_remotes_in_subfolders(tmp_path)

    assert result == {(git_repo, "origin"): error}
