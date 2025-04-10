"""git-fetch-all: Async fetch for all repos in sub-directories.

use `python -m git_fetch_all` to run the cli
"""

from .cli import app

app(prog_name="git-fetch-all")
