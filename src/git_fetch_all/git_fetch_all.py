#!/usr/bin/env python3
"""
Find all subdirectories with git repos, and fetches from all remotes.

Work asynchronously.
Run `git-fetch-all -h` for help.
Requires GitPython package
"""
# TODO: support submodules

from __future__ import annotations

import argparse
import asyncio
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from textwrap import indent
from typing import TYPE_CHECKING

from git import InvalidGitRepositoryError, Repo

if TYPE_CHECKING:
    from git.remote import Remote

RemoteName = str


async def fetch_remote(remote: Remote) -> bool:
    """Fetch a single remote asynchronously using a thread pool."""
    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor() as pool:
        res = await loop.run_in_executor(pool, remote.fetch)
        all_uptodate = all((info.flags >> 2) % 2 for info in res)
        return not all_uptodate


async def fetch_single_repo(
    repo: Repo,
    include_remotes: list[RemoteName] | None = None,
    exclude_remotes: list[RemoteName] | None = None,
) -> dict[RemoteName, Exception | bool]:
    """Fetch all remotes for a single repository asynchronously."""
    remotes = list(repo.remotes)
    if include_remotes is not None:
        remotes = [r for r in remotes if r.name in include_remotes]
    if exclude_remotes is not None:
        remotes = [r for r in remotes if r.name not in exclude_remotes]
    fetch_tasks = [fetch_remote(remote) for remote in remotes]
    results = dict(
        zip(
            (remote.name for remote in remotes),
            await asyncio.gather(*fetch_tasks, return_exceptions=True),
        )
    )
    for v in results.values():
        if isinstance(v, BaseException) and not isinstance(v, Exception):
            raise v
    return results


async def fetch_remotes_in_subfolders(
    folder: Path,
    recurse: int = 3,
    include_remotes: list[RemoteName] | None = None,
    exclude_remotes: list[RemoteName] | None = None,
    exclude_dirnames: list[str] | None = None,
    *,
    _recursive_head: bool = True,
) -> dict[tuple[Path, RemoteName], Exception | bool]:
    exclude_dirnames = exclude_dirnames or []

    try:
        repo = Repo(folder, search_parent_directories=False)
    except InvalidGitRepositoryError:
        pass
    else:
        result = await fetch_single_repo(repo, include_remotes, exclude_remotes)
        return {(folder, remote): status for remote, status in result.items()}

    if recurse == 0:
        return {}

    folders = [
        folder
        for folder in folder.glob("*")
        if folder.is_dir()
        and not folder.name.startswith(".")
        and folder.name not in exclude_dirnames
    ]
    tasks = [
        fetch_remotes_in_subfolders(
            folder,
            recurse - 1,
            include_remotes,
            exclude_remotes,
            exclude_dirnames=[],
            _recursive_head=False,
        )
        for folder in folders
    ]
    subfolder_results = await asyncio.gather(*tasks)

    fetched: dict[tuple[Path, RemoteName], Exception | bool] = {}
    for subfolder_result in subfolder_results:
        fetched = fetched | subfolder_result
    return fetched


def print_report(
    fetch_results: dict[tuple[Path, RemoteName], Exception | bool],
    basedir: Path,
    *,
    quiet: bool = False,
    color: bool = False,
) -> None:
    for (p, remote), res in fetch_results.items():
        fail = isinstance(res, Exception)
        if quiet and not fail:
            continue
        status = "𐄂" if fail else "✓" if res else "-"
        color_start = "\033[31m" if color and fail else ""
        color_end = "\033[0m" if color and fail else ""
        print(
            f"{color_start}{status} {p.relative_to(basedir).as_posix()}:{remote}{color_end}"
        )
        if fail:
            print(indent(str(res), "  "))


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="git-fetch-all", description="fetch all git repos in a directory"
    )
    parser.add_argument(
        "basedir",
        metavar="BASE_DIR",
        type=Path,
        nargs="?",
        default=".",
        help="base directory",
    )
    parser.add_argument(
        "-r", "--recurse", type=int, default=3, help="max recurse in directories"
    )
    parser.add_argument(
        "-i", "--include-remote", action="append", help="only include these remotes"
    )
    parser.add_argument(
        "-x", "--exclude-remote", action="append", help="don't include these remotes"
    )
    parser.add_argument(
        "-d", "--exclude-dirname", action="append", help="don't include these dirs"
    )
    parser.add_argument(
        "-q", "--quiet", action="store_true", help="don't output successful fetches"
    )
    parser.add_argument(
        "-c", "--color", action="store_true", help="output exceptions in red color"
    )
    args = parser.parse_args()
    fetch_results = asyncio.run(
        fetch_remotes_in_subfolders(
            args.basedir,
            args.recurse,
            args.include_remote,
            args.exclude_remote,
            args.exclude_dirname,
        )
    )
    print_report(fetch_results, args.basedir, quiet=args.quiet, color=args.color)


if __name__ == "__main__":
    main()
