import pytest

from git_fetch_all import __version__
from git_fetch_all.cli import app


def test_version(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc_info:
        app("--version")
    assert exc_info.value.code == 0
    assert capsys.readouterr().out.strip() == __version__


def test_app(capsys: pytest.CaptureFixture[str]) -> None:
    # TODO: this needs to work in a temp dir
    # TODO: this might need to mock the git command
    with pytest.raises(SystemExit) as exc_info:
        app([])
    assert exc_info.value.code == 0
    assert capsys.readouterr().out.strip() == "- .:origin"
