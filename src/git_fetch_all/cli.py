"""CLI for git_fetch_all.

Currently, a placeholder until the real CLI will be added.
"""

from typing import Annotated

import typer
from click.exceptions import UsageError

from . import __version__

app = typer.Typer()


def _version_callback(value: bool) -> None:  # noqa: FBT001
    if value:
        print(f"git-fetch-all {__version__}")
        raise typer.Exit(0)


@app.callback(invoke_without_command=True)
def callback(
    ctx: typer.Context,
    *,
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
) -> None:
    """Awesome Portal Gun."""
    if ctx.invoked_subcommand is None:
        raise UsageError("Missing command.")  # noqa: TRY003


@app.command()
def shoot() -> None:
    """Shoot the portal gun."""
    print("Shooting portal gun")


@app.command()
def load() -> None:
    """Load the portal gun."""
    print("Loading portal gun")
