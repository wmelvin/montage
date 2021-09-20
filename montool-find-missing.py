#!/usr/bin/env python3

import argparse
import sys

from datetime import datetime
from pathlib import Path
from typing import List


app_version = "210920.1"

app_name = "montool-find-missing"

app_title = f"{app_name}.py (version {app_version})"

run_dt = datetime.now().strftime("%y%m%d_%H%M%S")


class Lawg:
    def __init__(self, file_name: str):
        self.file_name = file_name
        self.entries: List[str] = []

    def add(self, text: str):
        self.entries.append(text)

    def say(self, text: str):
        print(text)
        self.add(text)

    def write_out(self):
        print(f"Writing '{self.file_name}'")
        with open(self.file_name, "w") as f:
            for entry in self.entries:
                f.write(f"{entry}\n")


class ImageListItem:
    def __init__(self, list_name, original_path):
        self.list_name: str = list_name
        self.original_path: str = original_path
        p = Path(original_path).expanduser().resolve()
        self.path_expanded: str = str(p)
        self.orig_parent: str = str(p.parent)
        self.file_name: str = p.name
        self.original_exists: bool = p.exists()
        self.tried_to_find: bool = False
        self.new_path: str = ""

    def __str__(self):
        return f"ImageListItem('{self.list_name}', '{self.original_path}')"

    def as_str(self):
        s = f"  {self.list_name=}\n"
        s += f"  {self.original_path=}\n"
        s += f"  {self.path_expanded=}\n"
        s += f"  {self.orig_parent=}\n"
        s += f"  {self.file_name=}\n"
        s += f"  {self.original_exists=}\n"
        s += f"  {self.tried_to_find=}\n"
        s += f"  {self.new_path=}\n"
        return s

    def do_find(self):
        return not (self.original_exists or self.tried_to_find)


class ImageList:
    def __init__(self, output_dir: str, log: Lawg):
        self.output_dir = output_dir
        self.log = log
        self.items: List[ImageListItem] = []

    def get_same_path(self, list_item: ImageListItem):
        for i in self.items:
            if i.tried_to_find and (0 < len(i.new_path)):
                if i.orig_parent == list_item.orig_parent:
                    return str(Path(i.new_path).parent)
        return ""

    def find_per_same_parent(self, list_item: ImageListItem):
        globpat = f"**/{list_item.file_name}"
        same_parent_path = self.get_same_path(list_item)
        if 0 < len(same_parent_path):
            self.log.say("Found another item with the same parent path.")
            self.log.say(f"Searching {same_parent_path}")
            found = list(Path(same_parent_path).glob(globpat))
            if 0 < len(found):
                if 1 < len(found):
                    self.log.say("Found more than one match. Using first one.")
                    for x in found:
                        self.log.add(f"  '{x}'")
                list_item.new_path = str(found[0])
                self.log.say(f"Found '{list_item.new_path}'")
                return True
        return False

    def find_file(self, list_item: ImageListItem):
        list_item.tried_to_find = True

        self.log.say(f"MISSING: {list_item.file_name}")
        self.log.say(f"Original location: {list_item.orig_parent}")

        #  If another item with the same parent path has already been found,
        #  then look in that item's new location first.
        if self.find_per_same_parent(list_item):
            return

        #  Look for the file by walking up the original parent path.
        globpat = f"**/{list_item.file_name}"

        parents = list(Path(list_item.orig_parent).parents)

        #  Stop before top-level directory under root.
        for p in parents[:-2]:
            self.log.say(f"Searching {p}")
            found = list(p.glob(globpat))
            if 0 < len(found):
                if 1 < len(found):
                    self.log.say("Found more than one match. Using first one.")
                    for x in found:
                        self.log.add(f"  '{x}'")
                list_item.new_path = str(found[0])
                self.log.say(f"Found '{list_item.new_path}'")
                return
        self.log.say("Not found :(")

    def find_files(self):
        for item in self.items:
            if item.do_find():
                self.find_file(item)

    def write_items_txt(self, suffix: str):
        file_name = f"{app_name}_{run_dt}_ITEMS_{suffix}.txt"
        file_name = Path(self.output_dir).joinpath(file_name)

        self.log.say(f"Writing '{file_name}'")

        with open(file_name, "w") as f:
            for i in self.items:
                f.write(f"{i}\n")
                f.write(f"{i.as_str()}\n")

    def get_section(self, tag: str) -> List[str]:
        s = f"\n[{tag}]\n"
        for item in self.items:
            if item.list_name == tag:
                if item.original_exists:
                    s += f"{item.original_path}\n"
                elif 0 < len(item.new_path):
                    s += f"# OLD: {item.original_path}\n"
                    s += f"{item.new_path}\n"
                else:
                    s += f"# NOT FOUND: {item.original_path}\n"
                s += "\n"
        return s

    def write_output_txt(self):
        file_name = f"{app_name}_{run_dt}_OUTPUT.txt"
        file_name = Path(self.output_dir).joinpath(file_name)
        self.log.say(f"Writing '{file_name}'")
        with open(file_name, "w") as f:
            f.write(self.get_section("background-images"))
            f.write(self.get_section("images"))
            f.write(self.get_section("images-1"))


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

    ap.add_argument(
        "-o",
        "--output-dir",
        dest="output_dir",
        type=str,
        default=str(Path.cwd()),
        action="store",
        help="Optional. Directory for output files. Default is current "
        + "directory.",
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


def main():
    print(f"\n{app_title}\n")

    args = get_args()

    opt_path = Path(args.opt_file).expanduser().resolve()

    if not opt_path.exists():
        sys.stderr.write("ERROR: Cannot find file: {0}\n".format(opt_path))
        sys.exit(1)

    if args.search_dir is not None:
        if not Path(args.search_dir).exists():
            sys.stderr.write(
                "ERROR: Cannot find directory: {0}\n".format(args.search_dir)
            )
            sys.exit(1)

    output_dir = str(Path(args.output_dir).expanduser().resolve())

    if not Path(output_dir).exists():
        sys.stderr.write(
            "ERROR: Cannot find output directory: {0}\n".format(output_dir)
        )
        sys.exit(1)

    log_name = f"{app_name}_{run_dt}_LOG.txt"
    log_name = Path(output_dir).joinpath(log_name)
    log = Lawg(log_name)

    log.add(f"Running {app_title}")
    log.say(f"Reading '{args.opt_file}'")

    with open(opt_path, "r") as f:
        file_text = f.readlines()

    image_list = ImageList(output_dir, log)

    image_list.items += [
        ImageListItem("background-images", x)
        for x in get_option_entries("[background-images]", file_text)
    ]

    image_list.items += [
        ImageListItem("images", x)
        for x in get_option_entries("[images]", file_text)
    ]

    image_list.items += [
        ImageListItem("images-1", x)
        for x in get_option_entries("[images-1]", file_text)
    ]

    image_list.write_items_txt("1-before")

    image_list.find_files()

    image_list.write_items_txt("2-after")

    image_list.write_output_txt()

    log.write_out()


if __name__ == "__main__":
    main()
