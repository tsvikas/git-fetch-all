"""CLI for git_fetch_all."""

from pathlib import Path
from typing import Annotated

from cyclopts import App, Parameter

from .git_fetch_all import fetch_remotes_in_subfolders, format_report

app = App(name="git-fetch-all")
app.register_install_completion_command()


@app.default()
def git_fetch_all(  # noqa: PLR0913
    base_dir: Path = Path(),
    /,
    *,
    recurse: Annotated[int, Parameter(alias="-r")] = 3,
    include_remote: Annotated[list[str] | None, Parameter(alias="-i")] = None,
    exclude_remote: Annotated[list[str] | None, Parameter(alias="-x")] = None,
    exclude_dirname: Annotated[list[str] | None, Parameter(alias="-d")] = None,
    quiet: Annotated[bool, Parameter(alias="-q")] = False,
    color: Annotated[bool, Parameter(alias="-c")] = False,
) -> int:
    """Fetch all remotes for all repos in a directory.

    Parameters
    ----------
    base_dir
        base directory
    recurse
        max recurse in directories
    include_remote
        only include these remotes
    exclude_remote
        don't include these remotes
    exclude_dirname
        don't include these dirs
    quiet
        don't output successful fetches
    color
        output exceptions in red color
    """
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
    return int(failed_fatches)
