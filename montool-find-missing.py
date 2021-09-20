#!/usr/bin/env python3

import argparse
import sys
from pathlib import Path


app_version = "210919.1"

app_title = f"montool-find-missing.py (version {app_version})"


def get_option_entries(opt_section, opt_content):
    result = []
    in_section = False
    for line in opt_content:
        s = line.strip()
        if (0 < len(s)) and not s.startswith("#"):
            if in_section:
                # New section?
                if s.startswith("["):
                    in_section = False
                else:
                    result.append(s)
            if s == opt_section:
                in_section = True
    return result


def try_to_find(file_path: Path) -> str:
    fn = file_path.name
    s = f"**/{fn}"
    par = file_path.parent
    found = False
    while not found:
        parent_path = str(par)
        print(f"Searching {parent_path}")
        fnd = list(par.glob(s))
        if 0 < len(fnd):
            found = True
            assert len(fnd) == 1
            return str(fnd[0])
        else:
            par = par.parent
            if str(par) == parent_path:
                return ""
    return ""


def main():
    print(f"\n{app_title}\n")

    ap = argparse.ArgumentParser(
        description="Search for missing image files listed in a "
        + "settings/options file for montage.py."
    )

    ap.add_argument("opt_file", help="Name of settings/options file.")

    ap.add_argument(
        "-s",
        "--search-dir",
        dest="search_dir",
        type=str,
        action="store",
        help="Optional. Directory to start search. Default is to search the "
        + "parent path of the current image file path.",
    )

    args = ap.parse_args()

    opt_path = Path(args.opt_file).resolve()
    if not opt_path.exists():
        sys.stderr.write("ERROR: Cannot find file: {0}\n".format(opt_path))
        sys.exit(1)

    if args.search_dir is not None:
        if not Path(args.search_dir).exists():
            sys.stderr.write(
                "ERROR: Cannot find directory: {0}\n".format(args.search_dir)
            )
            sys.exit(1)

    print(f"Reading {args.opt_file}.")
    #  Not really! :}~

    with open(opt_path, "r") as f:
        file_text = f.readlines()

    opt_img_b = get_option_entries("[background-settings]", file_text)
    opt_img_f = get_option_entries("[images]", file_text)
    opt_img_1 = get_option_entries("[images-1]", file_text)

    print(f"{opt_img_b=}")
    print(f"{opt_img_1=}")

    out_list = []

    out_list.append("[images]")

    for fn in opt_img_f:
        out_list.append("")
        p = Path(fn).resolve()
        if p.exists():
            out_list.append(str(p))
        else:
            out_list.append(f"# {fn}")
            print(f"Not found: {p}")
            ph = try_to_find(p)
            if 0 < len(ph):
                out_list.append(ph)
            else:
                out_list.append("NOT FOUND")

    with open("output-find-missing.txt", "w") as f:
        for item in out_list:
            f.write(f"{item}\n")


if __name__ == "__main__":
    main()
