#!/usr/bin/env python3
"""
Find all subdirectories with git repos, and fetches from all remotes.

Work asynchronously.
Run `git-fetch-all -h` for help.
Requires GitPython package
"""
# TODO: support submodules

import argparse
import asyncio
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from textwrap import indent

from git import InvalidGitRepositoryError, Repo
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
    include: list[RemoteName] | None = None,
    exclude: list[RemoteName] | None = None,
) -> dict[RemoteName, Exception | bool]:
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
    return results


async def fetch_remotes_in_subfolders(
    folder: Path,
    recurse: int = 3,
    include: list[RemoteName] | None = None,
    exclude: list[RemoteName] | None = None,
    exclude_dirs: list[str] | None = None,
    *,
    _recursive_head: bool = True,
) -> dict[tuple[Path, RemoteName], Exception | bool]:
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
    fetch_results: dict[tuple[Path, RemoteName], Exception | bool],
    basedir: Path,
    *,
    quiet: bool = False,
) -> None:
    for (p, remote), res in fetch_results.items():
        if quiet and not isinstance(res, Exception):
            continue
        status = "𐄂" if isinstance(res, Exception) else "✓" if res else "-"
        print(f"{status} {p.relative_to(basedir).as_posix()}:{remote}")
        if isinstance(res, Exception):
            print(indent(str(res), "  "))


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
    parser.add_argument(
        "-q", "--quiet", action="store_true", help="don't output successful fetches"
    )
    args = parser.parse_args()
    basedir = Path(args.DIRECTORY)
    fetch_results = asyncio.run(
        fetch_remotes_in_subfolders(
            basedir,
            args.recurse,
            include=args.include_remote,
            exclude=args.exclude_remote,
            exclude_dirs=args.exclude_dir,
        )
    )
    print_report(fetch_results, basedir, quiet=args.quiet)


if __name__ == "__main__":
    main()
