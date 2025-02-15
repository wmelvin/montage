from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

from montage.make_montage import expand_image_list, unquote

app_version = "2023.12.1"

app_name = "montool_missing"

app_title = f"montage-missing ({app_name}.py v{app_version})"

run_dt = datetime.now().strftime("%y%m%d_%H%M%S")  # noqa: DTZ005


class Lawg:
    def __init__(
        self,
        file_name: str,
        include_timestamp: bool,  # noqa: FBT001
        do_write_now: bool,  # noqa: FBT001
    ):
        self.file_name = file_name
        self.include_timestamp = include_timestamp
        self.do_write_now = do_write_now
        self.entries: list[str] = []

    def add(self, text: str):
        s = (
            f"[{datetime.now().strftime('%Y-%m-%dT%H:%M:%S')}]: {text}"
            if self.include_timestamp
            else text
        )  # noqa: DTZ005

        if self.do_write_now:
            self.write_now(s)
        else:
            self.entries.append(s)

    def say(self, text: str):
        print(text)
        self.add(text)

    def write_now(self, text: str):
        with open(self.file_name, "a") as f:
            f.write(f"{text}\n")

    def write_out(self):
        if len(self.entries) > 0:
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
        s = f"  list_name = '{self.list_name}'\n"
        s += f"  original_path = '{self.original_path}'\n"
        s += f"  path_expanded = '{self.path_expanded}'\n"
        s += f"  orig_parent = '{self.orig_parent}'\n"
        s += f"  file_name = '{self.file_name}'\n"
        s += f"  original_exists = {self.original_exists}\n"
        s += f"  tried_to_find = {self.tried_to_find}\n"
        s += f"  new_path = '{self.new_path}'\n"
        return s

    def do_find(self):
        return not (self.original_exists or self.tried_to_find)


class ImageList:
    def __init__(self, from_file: str, output_dir: str, log: Lawg):
        self.from_file = from_file
        self.output_dir = output_dir
        self.log = log
        self.items: list[ImageListItem] = []
        self.num_missing = 0
        self.num_found = 0

    def _get_same_path(self, list_item: ImageListItem):
        for i in self.items:
            if (
                i.tried_to_find
                and (len(i.new_path) > 0)
                and i.orig_parent == list_item.orig_parent
            ):
                return str(Path(i.new_path).parent)
        return ""

    def _find_per_same_parent(self, list_item: ImageListItem):
        globpat = f"**/{list_item.file_name}"
        same_parent_path = self._get_same_path(list_item)
        if len(same_parent_path) > 0:
            self.log.say("Found another item with the same parent path.")
            self.log.say(f"Searching {same_parent_path}")
            found = list(Path(same_parent_path).glob(globpat))
            if len(found) > 0:
                if len(found) > 1:
                    self.log.say("Found more than one match. Using first one.")
                    for x in found:
                        self.log.add(f"  '{x}'")
                list_item.new_path = str(found[0])
                self.log.say(f"Found '{list_item.new_path}'")
                self.num_found += 1
                return True
        return False

    def _find_file(self, search_dir: str, list_item: ImageListItem):
        list_item.tried_to_find = True

        self.log.say(f"MISSING: {list_item.file_name}")
        self.log.say(f"Original location: {list_item.orig_parent}")

        self.num_missing += 1

        #  If another item with the same parent path has already been found,
        #  then look in that item's new location first.
        if self._find_per_same_parent(list_item):
            return

        globpat = f"**/{list_item.file_name}"

        if len(search_dir) == 0:
            #  Look for the file by walking up the original parent path.
            parents = list(Path(list_item.orig_parent).parents)

            #  Stop before top-level directory under root.
            for p in parents[:-2]:
                self.log.say(f"Searching {p}")
                found = list(p.glob(globpat))
                if len(found) > 0:
                    if len(found) > 1:
                        self.log.say("Found more than one match. Using first one.")
                        for x in found:
                            self.log.add(f"  '{x}'")
                    list_item.new_path = str(found[0])
                    self.log.say(f"Found '{list_item.new_path}'")
                    self.num_found += 1
                    return
            self.log.say("Not found :(")
        else:
            #  If search_dir was specified then only search under that path.
            p = Path(search_dir)
            self.log.say(f"Searching {p}")
            found = list(p.glob(globpat))
            if len(found) > 0:
                if len(found) > 1:
                    self.log.say("Found more than one match. Using first one.")
                    for x in found:
                        self.log.add(f"  '{x}'")
                list_item.new_path = str(found[0])
                self.log.say(f"Found '{list_item.new_path}'")
                self.num_found += 1
                return
            self.log.say("Not found :(")

    def find_files(self, search_dir: str):
        for item in self.items:
            if item.do_find():
                self._find_file(search_dir, item)

    def write_items_txt(self, suffix: str):
        file_name = f"{app_name}_{run_dt}_ITEMS_{suffix}.txt"
        file_name = Path(self.output_dir).joinpath(file_name)

        self.log.say(f"Writing '{file_name}'")

        with open(file_name, "w") as f:
            for i in self.items:
                f.write(f"{i}\n")
                f.write(f"{i.as_str()}\n")

    def _get_section(self, tag: str) -> list[str]:
        s = f"\n[{tag}]\n"
        has_tag = False
        for item in self.items:
            if item.list_name == tag:
                has_tag = True
                if item.original_exists:
                    s += f"{item.original_path}"
                elif len(item.new_path) > 0:
                    s += f"# OLD: {item.original_path}\n"
                    s += f"{item.new_path}\n"
                else:
                    s += f"# NOT FOUND: {item.original_path}\n"
                s += "\n"
        if has_tag:
            return s
        return ""

    def _get_section_bare(self, tag: str) -> list[str]:
        s = f"\n[{tag}]\n"
        has_tag = False
        for item in self.items:
            if item.list_name == tag:
                has_tag = True
                if item.original_exists:
                    s += f"{item.original_path}\n"
                elif len(item.new_path) > 0:
                    s += f"{item.new_path}\n"
        if has_tag:
            return s
        return ""

    def _get_commented(self, tag: str) -> list[str]:
        s = self._get_section(tag)
        if len(s) == 0:
            return ""
        t = ""
        for x in s.split("\n"):
            t += f"# {x}\n"
        return t

    def write_output_a(self):
        #  Annotated output.  Includes comment lines when original files were
        #  found in a new location or not found at all.  Also includes
        #  commented-out Feature-n sections.  This output should be reviewed
        #  first to see if there are image files that could not be found in
        #  a new location.
        file_name = f"{app_name}_{run_dt}_OUTPUT_A.txt"
        file_name = Path(self.output_dir).joinpath(file_name)
        self.log.say(f"Writing '{file_name}'")
        with open(file_name, "w") as f:
            f.write(f"# From file '{self.from_file}':\n\n")
            f.write(self._get_commented("feature-1"))
            f.write(self._get_commented("feature-2"))
            f.write(self._get_section("background-images"))
            f.write(self._get_section("images"))
            f.write(self._get_section("images-1"))

    def write_output_b(self):
        #  Bare output.  Only includes image list sections where original
        #  files were found in the same or a new location.  This output
        #  is useful for making a copy-and-paste update to the original
        #  settings file.
        file_name = f"{app_name}_{run_dt}_OUTPUT_B.txt"
        file_name = Path(self.output_dir).joinpath(file_name)
        self.log.say(f"Writing '{file_name}'")
        with open(file_name, "w") as f:
            f.write(f"# From file '{self.from_file}':\n\n")
            f.write(self._get_section_bare("background-images"))
            f.write(self._get_section_bare("images"))
            f.write(self._get_section_bare("images-1"))


def get_args(arglist=None):
    ap = argparse.ArgumentParser(
        description="Search for missing image files listed in a "
        "settings/options file for montage.py."
    )

    ap.add_argument("opt_file", help="Name of settings/options file.")

    ap.add_argument(
        "-s",
        "--search-dir",
        dest="search_dir",
        type=str,
        default="",
        action="store",
        help="Optional. Directory to start search. Default is to search the "
        "parent path of the current image file path.",
    )

    ap.add_argument(
        "-o",
        "--output-dir",
        dest="output_dir",
        type=str,
        default=str(Path.cwd()),
        action="store",
        help="Optional. Directory for output files. Default is current directory.",
    )

    return ap.parse_args(arglist)


def get_opt_str(default, opt_name, content):
    for opt in content:
        if opt.strip().startswith(opt_name):
            a = opt.split("=", 1)
            if len(a) == 2 and a[0].strip() == opt_name:  # noqa: PLR2004
                return a[1].strip("'\" ")
    return default


def get_option_entries(opt_section, opt_content):
    result = []
    in_section = False
    for line in opt_content:
        s = line.strip()
        if (len(s) > 0) and not s.startswith("#"):
            if in_section:
                # New section?
                if s.startswith("["):
                    in_section = False
                else:
                    result.append(s)
            if s == opt_section:
                in_section = True
    return result


def main(arglist=None):
    print(f"\n{app_title}\n")

    args = get_args(arglist)

    opt_path = Path(args.opt_file).expanduser().resolve()

    if not opt_path.exists():
        sys.stderr.write(f"ERROR: Cannot find file: {opt_path}\n")
        sys.exit(1)

    if (args.search_dir is not None) and (not Path(args.search_dir).exists()):
        sys.stderr.write(f"ERROR: Cannot find directory: {args.search_dir}\n")
        sys.exit(1)

    output_dir = str(Path(args.output_dir).expanduser().resolve())

    if not Path(output_dir).exists():
        sys.stderr.write(f"ERROR: Cannot find output directory: {output_dir}\n")
        sys.exit(1)

    log_name = f"{app_name}_{run_dt}_LOG.txt"
    log_name = Path(output_dir).joinpath(log_name)
    log = Lawg(log_name, include_timestamp=False, do_write_now=True)

    log.add(f"Running {app_title}")
    log.say(f"Reading '{args.opt_file}'")

    with open(opt_path) as f:
        file_text = f.readlines()

    image_list = ImageList(args.opt_file, output_dir, log)

    # TODO: Handle list of images in a Feature section.

    section_text = get_option_entries("[feature-1]", file_text)
    if len(section_text) > 0:
        feature_img = get_opt_str("", "file", section_text)
        if len(feature_img) > 0 and (feature_img != "(skip)"):
            image_list.items.append(ImageListItem("feature-1", feature_img))

    section_text = get_option_entries("[feature-2]", file_text)
    if len(section_text) > 0:
        feature_img = get_opt_str("", "file", section_text)
        if len(feature_img) > 0 and (feature_img != "(skip)"):
            image_list.items.append(ImageListItem("feature-2", feature_img))

    image_list.items += [
        ImageListItem("background-images", a)
        for a in expand_image_list(
            [
                unquote(b)
                for b in get_option_entries("[background-images]", file_text)
                if (b != "(skip)")
            ]
        )
    ]

    image_list.items += [
        ImageListItem("images", a)
        for a in expand_image_list(
            [
                unquote(b)
                for b in get_option_entries("[images]", file_text)
                if (b != "(skip)")
            ]
        )
    ]

    image_list.items += [
        ImageListItem("images-1", a)
        for a in expand_image_list(
            [
                unquote(b)
                for b in get_option_entries("[images-1]", file_text)
                if (b != "(skip)")
            ]
        )
    ]

    log.add(f"search_dir = '{args.search_dir}'")

    image_list.write_items_txt("1-before")

    image_list.find_files(args.search_dir)

    image_list.write_items_txt("2-after")

    image_list.write_output_a()

    image_list.write_output_b()

    log.say(f"Count of missing image files = {image_list.num_missing}")
    if image_list.num_missing > 0:
        log.say(f"Count of those found = {image_list.num_found}")

    log.write_out()


if __name__ == "__main__":
    main()
