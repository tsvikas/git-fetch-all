"""Tests for git_fetch_all core functionality."""

from pathlib import Path
from unittest.mock import Mock

import git.remote
import pytest
from git import GitCommandError, Repo
from pytest_mock import MockerFixture

from git_fetch_all.git_fetch_all import (
    fetch_remotes_in_subfolders,
)


@pytest.fixture
def remote_not_up_to_date(mocker: MockerFixture) -> Mock:
    mock_fetch_info = mocker.Mock(spec=git.remote.FetchInfo)
    mock_fetch_info.flags = 0 << 2
    mock_remote = mocker.Mock(spec=git.remote.Remote)
    mock_remote.name = "origin"
    mock_remote.fetch = mocker.Mock(return_value=[mock_fetch_info])
    assert isinstance(mock_remote, Mock)
    return mock_remote


@pytest.fixture
def remote_up_to_date(mocker: MockerFixture) -> Mock:
    mock_fetch_info = mocker.Mock(spec=git.remote.FetchInfo)
    mock_fetch_info.flags = 1 << 2
    mock_remote = mocker.Mock(spec=git.remote.Remote)
    mock_remote.name = "origin"
    mock_remote.fetch = mocker.Mock(return_value=[mock_fetch_info])
    assert isinstance(mock_remote, Mock)
    return mock_remote


def test_fetch_remotes_in_subfolders_no_git_repos(tmp_path: Path) -> None:
    """Test with directory that has no git repositories."""
    result = fetch_remotes_in_subfolders(tmp_path)
    assert result == {}


def test_fetch_remotes_in_subfolders(
    tmp_path: Path,
    mocker: MockerFixture,
    remote_not_up_to_date: Mock,
) -> None:
    """Test fetch_remotes_in_subfolders with mocked git fetch."""
    git_repo_dir = tmp_path / "test_repo"
    git_repo_dir.mkdir()
    Repo.init(git_repo_dir)

    mocker.patch("git.Repo.remotes", [remote_not_up_to_date])
    result = fetch_remotes_in_subfolders(tmp_path)
    assert result == {(git_repo_dir, "origin"): True}


def test_fetch_remotes_in_subfolders_uptodate(
    tmp_path: Path,
    mocker: MockerFixture,
    remote_up_to_date: Mock,
) -> None:
    """Test with up-to-date repo."""
    git_repo_dir = tmp_path / "test_repo"
    git_repo_dir.mkdir()
    Repo.init(git_repo_dir)

    mocker.patch("git.Repo.remotes", [remote_up_to_date])
    result = fetch_remotes_in_subfolders(tmp_path)
    assert result == {(git_repo_dir, "origin"): False}


def test_fetch_remotes_in_subfolders_recurse_zero(
    tmp_path: Path,
    mocker: MockerFixture,
    remote_not_up_to_date: Mock,
) -> None:
    """Test with recurse=0 - should not process subdirectories."""
    # Create a fake git repo directory structure
    git_repo_dir = tmp_path / "test_repo"
    git_repo_dir.mkdir()
    Repo.init(git_repo_dir)

    mocker.patch("git.Repo.remotes", [remote_not_up_to_date])
    result = fetch_remotes_in_subfolders(tmp_path, recurse=0)
    assert result == {}


def test_fetch_remotes_in_subfolders_exclude_dirnames(
    tmp_path: Path,
    mocker: MockerFixture,
    remote_not_up_to_date: Mock,
) -> None:
    """Test excluding specific directory names."""
    normal_dir = tmp_path / "normal_repo"
    normal_dir.mkdir()
    Repo.init(normal_dir)

    excluded_dir = tmp_path / "do-not-fetch"
    excluded_dir.mkdir()
    Repo.init(excluded_dir)

    mocker.patch("git.Repo.remotes", [remote_not_up_to_date])
    result = fetch_remotes_in_subfolders(tmp_path, exclude_dirnames=["do-not-fetch"])
    assert result == {(normal_dir, "origin"): True}


def test_fetch_remotes_in_subfolders_with_git_error(
    tmp_path: Path,
    mocker: MockerFixture,
    remote_not_up_to_date: Mock,
) -> None:
    """Test handling of GitCommandError during fetch."""
    git_repo = tmp_path / "test_repo"
    git_repo.mkdir()
    Repo.init(git_repo)
    error = GitCommandError("git fetch", stderr="network error")
    remote_not_up_to_date.fetch = mocker.Mock(side_effect=error)
    mocker.patch("git.Repo.remotes", [remote_not_up_to_date])
    result = fetch_remotes_in_subfolders(tmp_path)
    assert result == {(git_repo, "origin"): error}
