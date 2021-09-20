#!/usr/bin/env python3

import argparse
import sys
from pathlib import Path


app_version = "210920.1"

app_title = f"montool-find-missing.py (version {app_version})"


class ImageListItem:
    def __init__(self, list_name, original_path):
        self.list_name = list_name
        self.original_path = original_path
        p = Path(original_path).expanduser().resolve()
        self.path_expanded = str(p)
        self.original_exists = p.exists()
        self.tried_to_find = False
        self.new_path = None

    def __str__(self):
        return f"ImageListItem('{self.list_name}', '{self.original_path}')"

    def as_str(self):
        s = f"  {self.list_name=}\n"
        s += f"  {self.original_path=}\n"
        s += f"  {self.path_expanded=}\n"
        s += f"  {self.original_exists=}\n"
        s += f"  {self.tried_to_find=}\n"
        s += f"  {self.new_path=}\n"
        return s

    def do_find(self):
        return not (self.original_exists or self.tried_to_find)


def get_args():
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

    return ap.parse_args()


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

    args = get_args()

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

    with open(opt_path, "r") as f:
        file_text = f.readlines()

    list_items = []

    list_items += [
        ImageListItem("background-images", x)
        for x in get_option_entries("[background-images]", file_text)
    ]

    list_items += [
        ImageListItem("images", x)
        for x in get_option_entries("[images]", file_text)
    ]

    list_items += [
        ImageListItem("images-1", x)
        for x in get_option_entries("[images-1]", file_text)
    ]

    for i in list_items:
        print(i)
        print(f"{i.as_str()}\n")

    # out_list = []

    # out_list.append("[images]")

    # for fn in opt_img_f:
    #     out_list.append("")
    #     p = Path(fn).resolve()
    #     if p.exists():
    #         out_list.append(str(p))
    #     else:
    #         out_list.append(f"# {fn}")
    #         print(f"Not found: {p}")
    #         ph = try_to_find(p)
    #         if 0 < len(ph):
    #             out_list.append(ph)
    #         else:
    #             out_list.append("NOT FOUND")

    # with open("output-find-missing.txt", "w") as f:
    #     for item in out_list:
    #         f.write(f"{item}\n")


if __name__ == "__main__":
    main()
