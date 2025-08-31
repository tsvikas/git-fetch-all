from pytest_mock import MockerFixture


def test_main_module_execution(mocker: MockerFixture) -> None:
    mock_app = mocker.patch("git_fetch_all.cli.app")
    import git_fetch_all.__main__  # noqa: F401, PLC0415

    mock_app.assert_called_once_with(prog_name="git-fetch-all")
