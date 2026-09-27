"""CLI for git_fetch_all."""

import sys
import traceback
from collections.abc import Sequence
from pathlib import Path
from typing import Annotated, NoReturn

from cyclopts import App, Parameter

from .git_fetch_all import fetch_remotes_in_subfolders, format_report

app = App(name="git-fetch-all")
app.register_install_completion_command()


# --- Commands -------------------------------------------------------------------------
# This is the part to replace. `@app.default()` runs when no subcommand is
# given, so switch these to `@app.command()` once there is more than one, and
# keep the exit codes each returns listed in its docstring.
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

    Args:
        base_dir: base directory
        recurse: max recurse in directories
        include_remote: only include these remotes
        exclude_remote: don't include these remotes
        exclude_dirname: don't include these dirs
        quiet: don't output successful fetches
        color: output exceptions in red color

    Returns:
        The process exit code.

    Exit Codes:
        0: Success.
        1: At least one fetch failed.
        2: Invalid usage.
        64-78: Reserved, an internal failure.
        129-159: Reserved, terminated by signal N, as 128 + N.
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


# --- Entry point ----------------------------------------------------------------------
# Maps the commands above onto exit codes, and is what `[project.scripts]` and
# `__main__` both call.

# Cyclopts itself exits 2 on invalid usage. These are sysexits(3) codes.
# `os.EX_*` holds the same values but only exists on Unix, so they are inlined
# to keep the CLI importable on Windows.
EX_NOINPUT = 66
EX_UNAVAILABLE = 69
EX_SOFTWARE = 70
EX_NOPERM = 77


def _fail(exc: Exception, code: int) -> NoReturn:
    """Report `exc` on stderr and exit with `code`."""
    print(f"error: {exc}", file=sys.stderr)
    sys.exit(code)


def main(tokens: Sequence[str] | None = None) -> None:
    """Run the CLI, reporting failures and mapping them onto exit codes.

    Args:
        tokens: The command line to parse. Defaults to `sys.argv[1:]`.
    """
    try:
        # `tokens` is a parameter so that tests can pass a command line here.
        # Under pytest, a bare `app()` warns, since it would parse pytest's own
        # argv, and a test that does so passes while testing nothing.
        app(tokens)
    # Nothing reports the errors below, so without `_fail` the CLI would exit on
    # a bare code and no output. Match on the exception rather than on
    # `type(exc)`, so that subclasses such as ConnectionRefusedError still land
    # on the right code. Specific OSError subclasses must precede any bare
    # `except OSError`, which would otherwise swallow them.
    except FileNotFoundError as exc:
        _fail(exc, EX_NOINPUT)
    except PermissionError as exc:
        _fail(exc, EX_NOPERM)
    except ConnectionError as exc:
        _fail(exc, EX_UNAVAILABLE)
    except Exception:  # noqa: BLE001
        traceback.print_exc()
        sys.exit(EX_SOFTWARE)
