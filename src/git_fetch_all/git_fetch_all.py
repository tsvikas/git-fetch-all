"""Find all subdirectories with git repos, and fetches from all remotes.

Work asynchronously.
Run `git-fetch-all -h` for help.
"""

# TODO: support submodules

import asyncio
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from textwrap import indent

import anyio
from colorama import Fore
from git import GitCommandError, InvalidGitRepositoryError, Repo
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
    fetch_tasks = {remote.name: fetch_remote(remote) for remote in remotes}
    results_with_baseexceptions = dict(
        zip(
            fetch_tasks.keys(),
            await asyncio.gather(*fetch_tasks.values(), return_exceptions=True),
            strict=True,
        )
    )
    results: dict[RemoteName, Exception | bool] = {}
    for k, v in results_with_baseexceptions.items():
        if isinstance(v, BaseException) and not isinstance(v, Exception):
            raise v
        results[k] = v
    return results


async def async_fetch_remotes_in_subfolders(
    folder: Path,
    recurse: int = 3,
    include_remotes: list[RemoteName] | None = None,
    exclude_remotes: list[RemoteName] | None = None,
    exclude_dirnames: list[str] | None = None,
    *,
    _recursive_head: bool = True,
    _seen_common_dirs: set[Path] | None = None,
) -> dict[tuple[Path, RemoteName], Exception | bool]:
    """Fetch all remotes for all repos in this folder, async."""
    exclude_dirnames = exclude_dirnames or []
    # Linked git worktrees share one ref store (common-dir) with their main
    # checkout, so fetching the same remote from two of them concurrently races
    # on refs/remotes/* and emits spurious "cannot lock ref" errors. Dedupe by
    # resolved common-dir so each ref store is fetched at most once per run.
    if _seen_common_dirs is None:
        _seen_common_dirs = set()

    try:
        with Repo(folder, search_parent_directories=False) as repo:
            common_dir = Path(await anyio.Path(repo.common_dir).resolve())
            # No await between the membership check and the add, so this
            # check-and-claim is atomic across the concurrent discovery walk.
            if common_dir in _seen_common_dirs:
                return {}
            _seen_common_dirs.add(common_dir)
            result = await fetch_single_repo(repo, include_remotes, exclude_remotes)
            return {(folder, remote): status for remote, status in result.items()}
    except InvalidGitRepositoryError:
        pass

    if recurse == 0:
        return {}

    folders = [
        Path(f)
        async for f in anyio.Path(folder).glob("*")
        if await f.is_dir()
        and not f.name.startswith(".")
        and f.name not in exclude_dirnames
    ]
    tasks = [
        async_fetch_remotes_in_subfolders(
            folder,
            recurse - 1,
            include_remotes,
            exclude_remotes,
            exclude_dirnames=[],
            _recursive_head=False,
            _seen_common_dirs=_seen_common_dirs,
        )
        for folder in folders
    ]
    subfolder_results = await asyncio.gather(*tasks)

    fetched: dict[tuple[Path, RemoteName], Exception | bool] = {}
    for subfolder_result in subfolder_results:
        fetched = fetched | subfolder_result
    return fetched


def fetch_remotes_in_subfolders(
    folder: Path,
    recurse: int = 3,
    include_remotes: list[RemoteName] | None = None,
    exclude_remotes: list[RemoteName] | None = None,
    exclude_dirnames: list[str] | None = None,
) -> dict[tuple[Path, RemoteName], Exception | bool]:
    """Fetch all remotes for all repos in a directory."""
    return asyncio.run(
        async_fetch_remotes_in_subfolders(
            folder,
            recurse,
            include_remotes,
            exclude_remotes,
            exclude_dirnames,
        )
    )


def format_report(
    fetch_results: dict[tuple[Path, RemoteName], Exception | bool],
    basedir: Path,
    *,
    quiet: bool = False,
    color: bool = False,
) -> str:
    """Format fetch report."""
    report: list[str] = []
    for (p, remote), res in fetch_results.items():
        fail = isinstance(res, Exception)
        if quiet and not fail:
            continue
        status = "𐄂" if fail else "✓" if res else "-"
        color_start = Fore.RED if color and fail else ""
        color_end = Fore.RESET if color and fail else ""
        report.append(
            f"{color_start}"
            f"{status} {p.relative_to(basedir).as_posix()}:{remote}"
            f"{color_end}"
        )
        if fail:
            res_str = (
                res.stderr.strip() if isinstance(res, GitCommandError) else str(res)
            )
            report.append(indent(res_str, "    "))
    return "\n".join(report)
