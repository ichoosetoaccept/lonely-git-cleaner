#!/usr/bin/env python3

import sys

from git import Repo


def main():
    repo = Repo(".")
    try:
        branch = repo.active_branch.name
        if branch == "main":
            print("Cannot commit directly to main branch")
            sys.exit(1)
    except TypeError:
        print("Skipping main branch check in detached HEAD state")
        sys.exit(0)


if __name__ == "__main__":
    main()
