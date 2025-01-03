#!/usr/bin/env python3

import re
import sys

from git import Repo


def main():
    repo = Repo(".")
    try:
        branch = repo.active_branch.name
        patterns = ["^feature/", "^bugfix/", "^hotfix/", "^release/", "^ci/", "^main$"]
        if not any(re.match(p, branch) for p in patterns):
            print(f"Branch name {branch} does not follow convention")
            sys.exit(1)
        print(f"Branch name {branch} follows convention")
    except TypeError:
        print("Skipping branch name check in detached HEAD state")
        sys.exit(0)


if __name__ == "__main__":
    main()
