#!/usr/bin/env python3
"""
Find all subdirectories with git repos, and fetches from all remotes.

Work asynchronously.
Run `git-fetch-all -h` for help.
Requires GitPython package
"""

import argparse
import asyncio
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from textwrap import indent

from git import InvalidGitRepositoryError, Repo
from git.remote import Remote


async def fetch_remote(remote: Remote) -> None:
    """Fetch a single remote asynchronously using a thread pool."""
    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor() as pool:
        await loop.run_in_executor(pool, remote.fetch)


async def fetch_single_repo(
    repo: Repo, include: list[str] | None = None, exclude: list[str] | None = None
) -> dict[str, Exception | None]:
    """Fetch all remotes for a single repository asynchronously."""
    remotes = list(repo.remotes)
    if include is not None:
        remotes = [r for r in remotes if r.name in include]
    if exclude is not None:
        remotes = [r for r in remotes if r.name not in exclude]
    fetch_tasks = [fetch_remote(remote) for remote in remotes]
    results = dict(
        zip(
            (remote.name for remote in remotes),
            await asyncio.gather(*fetch_tasks, return_exceptions=True),
        )
    )
    results_ok = {name: exc for name, exc in results.items() if exc is None}
    results_exceptions = {name: exc for name, exc in results.items() if exc is not None}
    return results_ok | results_exceptions


async def fetch_remotes_in_subfolders(
    folder: Path,
    recurse: int = 3,
    include: list[str] | None = None,
    exclude: list[str] | None = None,
    exclude_dirs: list[str] | None = None,
    *,
    _recursive_head: bool = True,
) -> dict[tuple[Path, str], Exception | None]:
    exclude_dirs = exclude_dirs or []

    try:
        repo = Repo(folder, search_parent_directories=False)
    except InvalidGitRepositoryError:
        pass
    else:
        result = await fetch_single_repo(repo, include, exclude)
        return {(folder, remote): status for remote, status in result.items()}

    if recurse == 0:
        return {}

    folders = [
        folder
        for folder in folder.glob("*")
        if folder.is_dir()
        and not folder.name.startswith(".")
        and folder.name not in exclude_dirs
    ]
    tasks = [
        fetch_remotes_in_subfolders(
            folder,
            recurse - 1,
            include,
            exclude,
            exclude_dirs=[],
            _recursive_head=False,
        )
        for folder in folders
    ]
    results = await asyncio.gather(*tasks)

    fetched = {}
    for result in results:
        fetched = fetched | result
    return fetched


def print_report(
    fetch_errors: dict[tuple[Path, str], Exception | None], basedir: Path
) -> None:
    for (p, remote), exc in fetch_errors.items():
        status = "✓" if exc is None else "𐄂"
        print(f"{status} {p.relative_to(basedir).as_posix()}:{remote}")
        if exc is not None:
            print(indent(str(exc), "  "))


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="git-fetch-all", description="fetch all git repos in a directory"
    )
    parser.add_argument("DIRECTORY", help="base directory", default=".", nargs="?")
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
        "-d", "--exclude-dir", action="append", help="don't include these dirs"
    )
    args = parser.parse_args()
    basedir = Path(args.DIRECTORY)
    fetch_errors = asyncio.run(
        fetch_remotes_in_subfolders(
            basedir,
            args.recurse,
            include=args.include_remote,
            exclude=args.exclude_remote,
            exclude_dirs=args.exclude_dir,
        )
    )
    print_report(fetch_errors, basedir)


if __name__ == "__main__":
    main()
