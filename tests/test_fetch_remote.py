"""Tests for fetch_remote, running git against local bare remotes."""

import asyncio
from pathlib import Path

import pytest
from git import GitCommandError, Repo

from git_fetch_all.git_fetch_all import fetch_single_repo


def _commit(repo: Repo, message: str) -> None:
    repo.git.commit("--allow-empty", "-m", message)


@pytest.fixture
def repo_with_remotes(tmp_path: Path) -> Repo:
    """Make a repo with three local bare remotes, each one commit ahead of it."""
    work = Repo.init(tmp_path / "work")
    with work.config_writer() as cw:
        cw.set_value("user", "name", "test")
        cw.set_value("user", "email", "test@example.com")
    _commit(work, "init")
    for name in ("origin", "upstream", "fork"):
        Repo.init(tmp_path / f"{name}.git", bare=True)
        work.create_remote(name, str(tmp_path / f"{name}.git"))
        work.git.push(name, "HEAD:refs/heads/main")
    _commit(work, "ahead")
    for name in ("origin", "upstream", "fork"):
        work.git.push(name, "HEAD:refs/heads/main")
        work.git.update_ref(f"refs/remotes/{name}/main", "HEAD~")
    return work


def test_fetch_single_repo_several_remotes(repo_with_remotes: Repo) -> None:
    """Each of a repo's remotes reports its own change.

    Fetching them concurrently collided on FETCH_HEAD and the commit-graph lock.
    """
    result = asyncio.run(fetch_single_repo(repo_with_remotes))
    assert result == {"origin": True, "upstream": True, "fork": True}

    result = asyncio.run(fetch_single_repo(repo_with_remotes))
    assert result == {"origin": False, "upstream": False, "fork": False}


def test_fetch_single_repo_failing_remote(repo_with_remotes: Repo) -> None:
    """A remote that fails is reported as a GitCommandError with git's stderr."""
    repo_with_remotes.git.remote("set-url", "fork", "/nonexistent/fork.git")
    result = asyncio.run(fetch_single_repo(repo_with_remotes))
    assert result["origin"] is True
    error = result["fork"]
    assert isinstance(error, GitCommandError)
    assert "/nonexistent/fork.git" in error.stderr
