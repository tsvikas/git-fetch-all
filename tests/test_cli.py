from typer.testing import CliRunner

from git_fetch_all import __version__
from git_fetch_all.cli import app

runner = CliRunner()


def test_app() -> None:
    result = runner.invoke(app)
    assert result.exit_code == 0
    assert "" in result.stdout


def test_app_version() -> None:
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert __version__ in result.stdout
