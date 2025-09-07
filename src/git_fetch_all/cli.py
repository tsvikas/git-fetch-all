"""CLI for git_fetch_all."""

from pathlib import Path
from typing import Annotated

import typer

from . import __version__
from .git_fetch_all import fetch_remotes_in_subfolders, format_report

app = typer.Typer()


def _version_callback(value: bool) -> None:  # noqa: FBT001
    if value:
        print(f"git-fetch-all {__version__}")
        raise typer.Exit(0)


@app.command()
def git_fetch_all(  # noqa: PLR0913
    base_dir: Annotated[Path, typer.Argument(help="base directory")] = Path(),
    *,
    recurse: Annotated[
        int, typer.Option("-r", "--recurse", help="max recurse in directories")
    ] = 3,
    include_remote: Annotated[
        list[str] | None,
        typer.Option("-i", "--include-remote", help="only include these remotes"),
    ] = None,
    exclude_remote: Annotated[
        list[str] | None,
        typer.Option("-x", "--exclude-remote", help="don't include these remotes"),
    ] = None,
    exclude_dirname: Annotated[
        list[str] | None,
        typer.Option("-d", "--exclude-dirname", help="don't include these dirs"),
    ] = None,
    quiet: Annotated[
        bool,
        typer.Option(
            "-q", "--quiet/--no-quiet", help="don't output successful fetches"
        ),
    ] = False,
    color: Annotated[
        bool,
        typer.Option("-c", "--color/--no-color", help="output exceptions in red color"),
    ] = False,
    version: Annotated[  # noqa: ARG001
        bool | None,
        typer.Option(
            "--version",
            "-V",
            callback=_version_callback,
            is_eager=True,
            help="Print version",
        ),
    ] = None,
) -> bool:
    """Fetch all remotes for all repos in a directory."""
    fetch_results = fetch_remotes_in_subfolders(
        base_dir,
        recurse,
        include_remote,
        exclude_remote,
        exclude_dirname,
    )
    failed_fatches = any(isinstance(res, Exception) for res in fetch_results.values())
    report = format_report(fetch_results, base_dir, quiet=quiet, color=color)
    print(report)
    return failed_fatches
