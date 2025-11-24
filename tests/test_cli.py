from pathlib import Path

import pytest
from git import Repo

from git_fetch_all import __version__
from git_fetch_all.cli import app


@pytest.fixture
def temp_git_repo(tmp_path: Path) -> Path:
    """Create a temporary git repository with a remote.

    Returns:
    -------
    Path
        Path to the temporary git repository
    """
    # Create a "remote" repository (bare)
    remote_repo_path = tmp_path / "remote"
    remote_repo_path.mkdir()
    remote_repo = Repo.init(remote_repo_path, bare=True)

    # Create the actual working repository
    work_repo_path = tmp_path / "work"
    work_repo_path.mkdir()
    work_repo = Repo.init(work_repo_path)

    # Create an initial commit
    test_file = work_repo_path / "test.txt"
    test_file.write_text("initial content\n")
    work_repo.index.add(["test.txt"])
    work_repo.index.commit("Initial commit")

    # Add the remote and push (use current branch name)
    current_branch = work_repo.active_branch.name
    work_repo.create_remote("origin", str(remote_repo_path))
    work_repo.git.push("--set-upstream", "origin", current_branch)

    # Clean up references
    remote_repo.close()
    work_repo.close()

    return work_repo_path


@pytest.fixture
def temp_git_repo_with_changes(temp_git_repo: Path) -> Path:
    """Create a temporary git repository with pending remote changes.

    Returns:
    -------
    Path
        Path to the temporary git repository with pending changes
    """
    # Open the repo, commit and push, then reset back
    work_repo = Repo(temp_git_repo)

    # Create and push a new commit
    test_file = temp_git_repo / "test.txt"
    test_file.write_text("updated content\n")
    work_repo.index.add(["test.txt"])
    work_repo.index.commit("Update test file")
    current_branch = work_repo.active_branch.name
    work_repo.git.push("origin", current_branch)

    # Reset back one commit (both local branch and remote tracking branch)
    work_repo.git.reset("--hard", "HEAD~")
    work_repo.git.update_ref(f"refs/remotes/origin/{current_branch}", "HEAD")
    work_repo.close()

    return temp_git_repo


def test_version(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc_info:
        app("--version")
    assert exc_info.value.code == 0
    assert capsys.readouterr().out.strip() == __version__


def test_app_uptodate(capsys: pytest.CaptureFixture[str], temp_git_repo: Path) -> None:
    """Test git-fetch-all on a repo with no remote changes."""
    with pytest.raises(SystemExit) as exc_info:
        app([str(temp_git_repo)])
    assert exc_info.value.code == 0
    assert capsys.readouterr().out.strip() == "- .:origin"


def test_app_with_changes(
    capsys: pytest.CaptureFixture[str], temp_git_repo_with_changes: Path
) -> None:
    """Test git-fetch-all on a repo with pending remote changes."""
    with pytest.raises(SystemExit) as exc_info:
        app([str(temp_git_repo_with_changes)])
    assert exc_info.value.code == 0
    assert capsys.readouterr().out.strip() == "✓ .:origin"
