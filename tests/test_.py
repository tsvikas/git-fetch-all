import importlib

import git_fetch_all


def test_version() -> None:
    assert importlib.metadata.version("git_fetch_all") == git_fetch_all.__version__
