#!/usr/bin/env python3

import argparse
# import datetime
# import os
# import re
# import shutil
import sys
from pathlib import Path


app_version = "210919.1"

app_title = f"montool-find-missing.py (version {app_version})"


def main():
    print(f"\n{app_title}\n")

    ap = argparse.ArgumentParser(
        description="Search for missing image files listed in a "
        + "settings/options file for montage.py."
    )

    ap.add_argument(
        "opt_file", help="Name of settings/options file."
    )

    ap.add_argument(
        "-s", "--search-dir",
        dest="search_dir",
        type=str,
        action="store",
        help="Optional. Directory to start search. Default is to search the "
        + "parent path of the current image file path."
    )

    args = ap.parse_args()

    if not Path(args.opt_file).exists():
        sys.stderr.write(
            "ERROR: Cannot find file: {0}\n".format(
                args.opt_file
            )
        )
        sys.exit(1)

    if args.search_dir is not None:
        if not Path(args.search_dir).exists():
            sys.stderr.write(
                "ERROR: Cannot find directory: {0}\n".format(
                    args.search_dir
                )
            )
            sys.exit(1)

    print(f"Reading {args.opt_file}.")
    #  Not really! :}~


if __name__ == "__main__":
    main()
