#!/usr/bin/env python3

import argparse
import random
import sys
import textwrap
from collections import namedtuple
from datetime import datetime
from typing import List
from PIL import Image, ImageFilter, ImageOps
from pathlib import Path

MAX_SHUFFLE_COUNT = 99

SKIP_MARKER = "(skip)"

app_version = "211010.1"

pub_version = "1.0.dev1"

app_title = f"montage.py - version {app_version}"

# global confirm_errors
confirm_errors = True


FeatureImage = namedtuple("FeatureImage", "col, ncols, row, nrows, file_name")


class Placement:
    def __init__(self, left, top, width, height, file_name):
        self.x = left
        self.y = top
        self.width = width
        self.height = height
        self.file_name = file_name


class MontageDefaults:
    def __init__(self):
        self.file_name = "output.jpg"
        self.canvas_width = 640
        self.canvas_height = 480
        self.margin = 10
        self.padding = 10
        self.bg_blur = 3
        self.ncols = [2]
        self.nrows = [2]
        self.border_rgba = (0, 0, 0, 255)
        self.background_rgba = (255, 255, 255, 255)


class MontageOptions:
    def __init__(self):
        self._run_dt = datetime.now()
        self.output_file_name = None
        self.output_dir = None
        self.canvas_width = None
        self.canvas_height = None
        self.init_ncols = None
        self.init_nrows = None
        self.rows = None
        self.cols = None
        self.margin = None
        self.padding = None
        self.feature1 = None
        self.feature2 = None
        self.bg_rgba = None
        self.bg_blur = None
        self.shuffle_mode = None
        self.shuffle_count = None
        self.stamp_mode = None
        self.write_opts = None
        self.border_width = None
        self.border_rgba = None
        self.do_zoom = None

        self.pool_index = -1
        self.pool_wrapped = False
        self.bg_index = -1
        self.im1_index = -1

        self.init_images = []
        #  Initial list of image file names, as loaded from the
        #  [images] section and/or positional args.

        self.init_images1 = []
        #  Initial list of image file names, as loaded from the
        #  [images-1] section.

        self.init_bg_images = []
        #  Initial list of image file names, as loaded from the
        #  [background-images] section.

        self.image_pool = []
        #  List to pull from when filling current_images. Loaded
        #  from init_images and shuffled, depending on option.

        self.current_images = []
        #  List of images selected for the current montage.

        self._placements = []
        #  List of images to be placed in the current montage.

        self._log = []

    def canvas_size(self):
        return (int(self.canvas_width), int(self.canvas_height))

    def get_pool_index(self):
        first_use = self.pool_index == -1
        self.pool_index += 1
        if len(self.image_pool) <= self.pool_index:
            self.pool_index = 0
            self.pool_wrapped = not first_use
        return self.pool_index

    def get_im1_index(self):
        self.im1_index += 1
        if len(self.init_images1) <= self.im1_index:
            self.im1_index = 0
        return self.im1_index

    def get_bg_index(self):
        n = len(self.init_bg_images)
        if n == 0:
            self.bg_index = -1
        elif self.do_shuffle_bg_images():
            self.bg_index = random.randrange(n)
        else:
            self.bg_index += 1
            if self.bg_index == len(self.init_bg_images):
                self.bg_index = 0
        return self.bg_index

    def add_placement(self, x, y, w, h, file_name=""):
        self._placements.append(Placement(x, y, w, h, file_name))

    def get_placements_list(self) -> List[Placement]:
        return self._placements

    def has_background_image(self):
        return 0 < len(self.init_bg_images)

    def get_bg_file_name(self):
        i = self.get_bg_index()
        if 0 <= i:
            return self.init_bg_images[i]
        else:
            return None

    def background_rgb(self):
        return self.bg_rgba[:3]

    def background_mask_rgba(self):
        return (0, 0, 0, self.bg_rgba[3])

    def border_rgb(self):
        return self.border_rgba[:3]

    def border_mask_rgba(self):
        return (0, 0, 0, self.border_rgba[3])

    def shuffled_col_row(self, values: List[int], weighted_flag: str):
        if weighted_flag in self.shuffle_mode:
            a = []
            for i in range(len(values)):
                for x in range((i + 1) * 2):
                    a.append(values[i])
        else:
            a = [] + values
        random.shuffle(a)
        return a[0]

    def set_cols_rows(self) -> int:
        if "c" in self.shuffle_mode:
            self.cols = self.shuffled_col_row(self.init_ncols, "wc")
        else:
            self.cols = self.init_ncols[0]
        if "r" in self.shuffle_mode:
            self.rows = self.shuffled_col_row(self.init_nrows, "wr")
        else:
            self.rows = self.init_nrows[0]

    def get_ncols(self):
        if self.cols is None:
            self.set_cols_rows()
        return self.cols

    def get_nrows(self):
        if self.rows is None:
            self.set_cols_rows()
        return self.rows

    def _feature_cell_count(self):
        n = self.feature1.ncols * self.feature1.nrows
        n += self.feature2.ncols * self.feature2.nrows
        return n

    def _current_image_count(self):
        n = self.get_ncols() * self.get_nrows()
        n -= self._feature_cell_count()
        return n

    def _load_current_images(self):
        self.current_images.clear()
        n_images = self._current_image_count()
        if 0 < len(self.init_images1):
            n_images -= 1
        assert 0 < n_images
        no_wrap = "n" in self.shuffle_mode
        while len(self.current_images) < n_images:
            i = self.get_pool_index()
            if self.pool_wrapped and no_wrap:
                break
            self.current_images.append(self.image_pool[i])
        if 0 < len(self.init_images1):
            self.current_images.append(self.init_images1[self.get_im1_index()])
        if self.do_shuffle_images():
            random.shuffle(self.current_images)

    def do_shuffle_images(self):
        return "i" in self.shuffle_mode

    def do_shuffle_bg_images(self):
        return "b" in self.shuffle_mode

    def get_montage_count(self):
        if len(self.shuffle_mode) == 0:
            return 1
        else:
            return min(self.shuffle_count, MAX_SHUFFLE_COUNT)

    def log_add(self, message):
        self._log.append(message)

    def log_say(self, message):
        print(message)
        self._log.append(message)

    def prepare(self):
        self._placements.clear()
        self._log.clear()
        self.set_cols_rows()
        if len(self.image_pool) == 0:  # First run.
            self.image_pool = [] + self.init_images
            if self.do_shuffle_images():
                random.shuffle(self.image_pool)
        elif self.pool_wrapped and self.do_shuffle_images():
            random.shuffle(self.image_pool)
        self._load_current_images()
        self.pool_wrapped = False

    def _timestamp_str(self):
        if 2 < self.stamp_mode:
            fmt_str = "%Y%m%d_%H%M%S_%f"
        else:
            fmt_str = "%Y%m%d_%H%M%S"
        return self._run_dt.strftime(fmt_str)

    def image_file_name(self, image_num):
        if len(self.output_dir) == 0:
            dir = Path.cwd()
        else:
            dir = Path(self.output_dir).expanduser().resolve()

        assert dir.is_dir
        assert dir.exists()

        p = Path(self.output_file_name)

        if 1 < self.shuffle_count:
            p = Path(
                "{0}-{1:02d}".format(p.with_suffix(""), image_num)
            ).with_suffix(p.suffix)

        if self.stamp_mode in [1, 3]:
            #  Mode 1: date_time stamp at left of file name.
            p = Path(
                "{0}_{1}".format(self._timestamp_str(), p.with_suffix(""))
            ).with_suffix(p.suffix)
        elif self.stamp_mode in [2, 4]:
            #  Mode 2: date_time stamp at right of file name.
            p = Path(
                "{0}_{1}".format(p.with_suffix(""), self._timestamp_str())
            ).with_suffix(p.suffix)

        return str(dir.joinpath(p))

    def _options_as_str(self):
        s = ""
        s += "\n[settings]\n"
        s += f"output_file={qs(self.output_file_name)}\n"
        s += f"output_dir={qs(self.output_dir)}\n"
        s += f"canvas_width={self.canvas_width}\n"
        s += f"canvas_height={self.canvas_height}\n"
        s += "background_rgba={0},{1},{2},{3}\n".format(
            self.bg_rgba[0], self.bg_rgba[1], self.bg_rgba[2], self.bg_rgba[3]
        )
        s += f"background_blur={self.bg_blur}\n"
        s += f"columns={int_list_str(self.init_ncols)}\n"
        s += f"rows={int_list_str(self.init_nrows)}\n"
        s += f"margin={self.margin}\n"
        s += f"padding={self.padding}\n"
        s += f"border_width={self.border_width}\n"
        s += "border_rgba={0},{1},{2},{3}\n".format(
            self.border_rgba[0],
            self.border_rgba[1],
            self.border_rgba[2],
            self.border_rgba[3],
        )
        s += f"do_zoom={self.do_zoom}\n"
        s += f"shuffle_mode={self.shuffle_mode}\n"
        s += f"shuffle_count={self.shuffle_count}\n"
        s += f"stamp_mode={self.stamp_mode}\n"
        s += f"write_opts={self.write_opts}\n"

        s += "\n[feature-1]\n"
        s += f"file={qs(self.feature1.file_name)}\n"
        s += f"column={self.feature1.col}\n"
        s += f"row={self.feature1.row}\n"
        s += f"num_columns={self.feature1.ncols}\n"
        s += f"num_rows={self.feature1.nrows}\n"

        s += "\n[feature-2]\n"
        s += f"file={qs(self.feature2.file_name)}\n"
        s += f"column={self.feature2.col}\n"
        s += f"row={self.feature2.row}\n"
        s += f"num_columns={self.feature2.ncols}\n"
        s += f"num_rows={self.feature2.nrows}\n"

        s += "\n[background-images]\n"
        for i in self.init_bg_images:
            s += f"{qs(i)}\n"

        s += "\n[images]\n"
        for i in self.init_images:
            s += f"{qs(i)}\n"

        s += "\n[images-1]\n"
        for i in self.init_images1:
            s += f"{qs(i)}\n"

        return s

    def write_options(self, image_file_name):
        if self.write_opts:
            p = Path(image_file_name)

            file_name = str(
                Path(
                    "{0}_{1}".format(p.with_suffix(""), "options")
                ).with_suffix(".txt")
            )

            print(f"\nWriting options to '{file_name}'\n")
            with open(file_name, "w") as f:
                f.write(
                    "# Created {0} by {1}\n".format(
                        datetime.now().strftime("%Y-%m-%d %H:%M"), app_title
                    )
                )

                f.write(self._options_as_str())

                f.write("\n\n[LOG: CURRENT-IMAGES]\n")
                for i in self.current_images:
                    f.write(f"{qs(i)}\n")

                if 0 < len(self._log):
                    f.write("\n\n[LOG: STEPS]\n")
                    for i in self._log:
                        f.write(f"{i}\n")

    def check_feature(self, feat_num: int, feat_attr: FeatureImage):
        errors = []
        numeric_attrs = [
            feat_attr.col,
            feat_attr.ncols,
            feat_attr.row,
            feat_attr.nrows,
        ]

        if any(0 < x for x in numeric_attrs):
            if any(x <= 0 for x in numeric_attrs):
                errors.append(
                    f"Feature-{feat_num}: All column and row settings must "
                    + "be set to not-zero values if any are set."
                )
                if len(feat_attr.file_name) == 0:
                    errors.append(
                        f"Feature-{feat_num}: File name must be set."
                    )

        if 0 < len(feat_attr.file_name):
            if not (
                feat_attr.file_name == SKIP_MARKER
                or Path(feat_attr.file_name).exists()
            ):
                errors.append(
                    "Feature-{0}: Image file not found: '{1}'.".format(
                        feat_num, feat_attr.file_name
                    )
                )

        return errors

    def check_options(self):
        errors = []

        if 0 < len(self.output_dir):
            if not Path(self.output_dir).exists():
                errors.append(f"Output folder not found: '{self.output_dir}'.")

            if not Path(self.output_dir).is_dir():
                errors.append(
                    f"Output folder not a directory: '{self.output_dir}'."
                )

        for file_name in self.init_images:
            if not (
                file_name.strip() == SKIP_MARKER or Path(file_name).exists()
            ):
                errors.append(f"Image file not found: '{file_name}'.")

        for file_name in self.init_images1:
            if not Path(file_name).exists():
                errors.append(f"Image file not found: '{file_name}'.")

        for file_name in self.init_bg_images:
            if not Path(file_name).exists():
                errors.append(
                    f"Background image file not found: '{file_name}'."
                )

        errors += self.check_feature(1, self.feature1)

        errors += self.check_feature(2, self.feature2)

        if 0 < len(errors):
            print("\nCANNOT PROCEED")
            for message in errors:
                sys.stderr.write(f"{message}\n")
            error_exit()

    def _load_from_file(self, file_name):
        if file_name is not None:
            p = Path(file_name).expanduser().resolve()
            if not p.exists():
                sys.stderr.write(f"ERROR: File not found: {p}")
                error_exit()

            print(f"Load settings from '{file_name}'.")

            with open(p, "r") as f:
                file_text = f.readlines()

            settings = get_option_entries("[settings]", file_text)

            warn_old_settings(settings)

            self.output_file_name = get_opt_str(None, "output_file", settings)

            self.output_dir = get_opt_str(None, "output_dir", settings)

            self.canvas_width = get_opt_int(None, "canvas_width", settings)

            self.canvas_height = get_opt_int(None, "canvas_height", settings)

            self.init_ncols = as_int_list(
                get_opt_str(None, "columns", settings)
            )

            self.init_nrows = as_int_list(get_opt_str(None, "rows", settings))

            self.margin = get_opt_int(None, "margin", settings)

            self.padding = get_opt_int(None, "padding", settings)

            self.border_width = get_opt_int(None, "border_width", settings)

            self.border_rgba = get_opt_str(None, "border_rgba", settings)

            self.bg_rgba = get_opt_str(None, "background_rgba", settings)

            self.bg_blur = get_opt_int(None, "background_blur", settings)

            self.shuffle_mode = get_opt_str(None, "shuffle_mode", settings)

            self.shuffle_count = get_opt_int(None, "shuffle_count", settings)

            self.stamp_mode = get_opt_int(None, "stamp_mode", settings)

            self.write_opts = get_opt_bool(None, "write_opts", settings)

            self.do_zoom = get_opt_bool(None, "do_zoom", settings)

            self.feature1 = get_opt_feat(
                get_option_entries("[feature-1]", file_text), True
            )

            self.feature2 = get_opt_feat(
                get_option_entries("[feature-2]", file_text), True
            )

            self.init_images += [
                i.strip("'\"")
                for i in get_option_entries("[images]", file_text)
            ]

            self.init_images1 += [
                i.strip("'\"")
                for i in get_option_entries("[images-1]", file_text)
            ]

            self.init_bg_images += [
                i.strip("'\"")
                for i in get_option_entries("[background-images]", file_text)
            ]

    def _set_defaults(self, defaults: MontageDefaults):
        # -- Use defaults for options not already set.

        if self.output_file_name is None:
            self.output_file_name = defaults.file_name

        if self.output_dir is None:
            self.output_dir = ""

        if self.canvas_width is None:
            self.canvas_width = defaults.canvas_width

        if self.canvas_height is None:
            self.canvas_height = defaults.canvas_height

        if self.init_ncols is None:
            self.init_ncols = defaults.ncols

        if self.init_nrows is None:
            self.init_nrows = defaults.nrows

        if self.margin is None:
            self.margin = defaults.margin

        if self.padding is None:
            self.padding = defaults.padding

        if self.border_width is None:
            self.border_width = 0

        if self.border_rgba is None:
            self.border_rgba = defaults.border_rgba
        elif type(self.border_rgba) == str:
            self.border_rgba = get_rgba(defaults.border_rgba, self.border_rgba)

        if self.bg_rgba is None:
            self.bg_rgba = defaults.background_rgba
        elif type(self.bg_rgba) == str:
            self.bg_rgba = get_rgba(defaults.background_rgba, self.bg_rgba)

        if self.bg_blur is None:
            self.bg_blur = defaults.bg_blur

        if self.shuffle_mode is None:
            self.shuffle_mode = ""

        if self.shuffle_count is None:
            self.shuffle_count = 1

        if self.stamp_mode is None:
            self.stamp_mode = 0

        if self.write_opts is None:
            self.write_opts = False

        if self.do_zoom is None:
            self.do_zoom = False

        if self.feature1 is None:
            self.feature1 = get_opt_feat("", False)

        if self.feature2 is None:
            self.feature2 = get_opt_feat("", False)

    def load(self, args, defaults: MontageDefaults, settings_file=None):
        if args is None and settings_file is None:
            sys.stderr.write(
                "ERROR: No args object, and no settings file name.\n"
            )
            error_exit()

        if settings_file is None:
            self._load_from_file(args.settings_file)
        else:
            self._load_from_file(settings_file)

        if args is not None:
            #  Command line arguments will override settings file.
            #  Arguments that were not provided either need to be
            #  None or a default value that indicates it was not
            #  specified.

            if args.output_file is not None:
                self.output_file_name = args.output_file

            if args.output_dir is not None:
                self.output_dir = args.output_dir

            if args.canvas_width is not None:
                self.canvas_width = args.canvas_width

            if args.canvas_height is not None:
                self.canvas_height = args.canvas_height

            if args.cols is not None:
                self.init_ncols = as_int_list(args.cols)

            if args.rows is not None:
                self.init_nrows = as_int_list(args.rows)

            if args.margin is not None:
                self.margin = args.margin

            if args.padding is not None:
                self.padding = args.padding

            if args.border_width is not None:
                self.border_width = args.border_width

            if args.border_rgba_str is not None:
                self.border_rgba = args.border_rgba_str

            if args.bg_rgba_str is not None:
                self.bg_rgba = args.bg_rgba_str

            if args.bg_blur is not None:
                self.bg_blur = args.bg_blur

            if args.shuffle_mode is not None:
                self.shuffle_mode = args.shuffle_mode

            if args.shuffle_count is not None:
                self.shuffle_count = args.shuffle_count

            if args.stamp_mode is not None:
                self.stamp_mode = args.stamp_mode

            if args.write_opts is not None:
                if args.write_opts:
                    self.write_opts = True

            if args.do_zoom is not None:
                if args.do_zoom:
                    self.do_zoom = True

            if args.feature_1 is not None:
                self.feature1 = get_feature_args(args.feature_1)

            if args.feature_2 is not None:
                self.feature2 = get_feature_args(args.feature_2)

            self.init_images = [
                i for i in args.images if 0 < len(i)
            ] + self.init_images

        self.init_images = expand_image_list(self.init_images)

        self.init_images1 = expand_image_list(self.init_images1)

        self.init_bg_images = expand_image_list(self.init_bg_images)

        self._set_defaults(defaults)

        self.shuffle_mode = self.shuffle_mode.lower()


# ----------------------------------------------------------------------


def error_exit():
    print("*" * 70)
    if confirm_errors:
        input("ERRORS: Press [Enter]. ")
    else:
        print("Halted due to errors.")
    sys.exit(1)


def get_list_from_file(file_name):
    p = Path(file_name).expanduser().resolve()
    if not p.exists():
        sys.stderr.write(f"ERROR: File not found: {p}")
        error_exit()

    result = []

    with open(p, "r") as f:
        file_text = f.readlines()

    for line in file_text:
        s = line.strip()
        if (0 < len(s)) and not s.startswith("#"):
            result.append(s)

    return result


def expand_image_list(raw_list):
    new_list = []
    if (raw_list is not None) and (0 < len(raw_list)):
        for item in raw_list:
            if item.startswith("@"):
                new_list += get_list_from_file(item[1:])
            else:
                new_list.append(item)
    return new_list


def warn_old_settings(settings):
    old_settings = {
        "background_rgb": "Replaced by 'background_rgba'",
        "bg_alpha": "Replaced by 'background_rgba'",
        "bg_blur": "Replaced by 'background_blur'",
    }
    for line in settings:
        a = line.split("=", 1)
        if len(a) == 2:
            setting_name = a[0].strip()
            if setting_name in old_settings.keys():
                print(
                    "WARNING: Obsolete setting '{0}': {1}".format(
                        setting_name, old_settings[setting_name]
                    )
                )


def get_arguments():
    ap = argparse.ArgumentParser(
        formatter_class=argparse.RawTextHelpFormatter,
        description="Create an image montage given a list of image files.",
    )

    ap.add_argument(
        "images",
        nargs="*",
        action="store",
        help="Images files to include in the montage image. "
        + "Multiple files can be specified.",
    )

    ap.add_argument(
        "-o",
        "--output-file",
        dest="output_file",
        action="store",
        help="Name of output file.",
    )

    ap.add_argument(
        "-d",
        "--output-dir",
        dest="output_dir",
        action="store",
        help="Name of output directory.",
    )

    ap.add_argument(
        "-x",
        "--canvas-width",
        dest="canvas_width",
        type=int,
        action="store",
        help="Canvas width in pixels.",
    )

    ap.add_argument(
        "-y",
        "--canvas-height",
        dest="canvas_height",
        type=int,
        action="store",
        help="Canvas height in pixels.",
    )

    ap.add_argument(
        "-c",
        "--columns",
        dest="cols",
        type=int,
        action="store",
        help="Number of columns.",
    )

    ap.add_argument(
        "-r",
        "--rows",
        dest="rows",
        type=int,
        action="store",
        help="Number of rows.",
    )

    ap.add_argument(
        "-m",
        "--margin",
        dest="margin",
        type=int,
        action="store",
        help="Margin in pixels.",
    )

    ap.add_argument(
        "-p",
        "--padding",
        dest="padding",
        type=int,
        action="store",
        help="Padding in pixels.",
    )

    ap.add_argument(
        "-b",
        "--background-rgba",
        dest="bg_rgba_str",
        type=str,
        action="store",
        help="Background color as red,green,blue,alpha.",
    )

    ap.add_argument(
        "--border-width",
        dest="border_width",
        type=int,
        action="store",
        help="Border width in pixels.",
    )

    ap.add_argument(
        "--border-rgba",
        dest="border_rgba_str",
        type=str,
        action="store",
        help="Border color as red,green,blue,alpha.",
    )

    ap.add_argument(
        "-g",
        "--background-image",
        dest="bg_file",
        action="store",
        help="Name of image file to use as the background image.",
    )

    ap.add_argument(
        "--background-blur",
        dest="bg_blur",
        type=int,
        action="store",
        help="Blur radius for background image (0 = none).",
    )

    ap.add_argument(
        "--feature-1",
        dest="feature_1",
        type=str,
        action="store",
        help="Attributes for first featured image as "
        + "(col, ncols, row, nrows, file_name).",
    )

    ap.add_argument(
        "--feature-2",
        dest="feature_2",
        type=str,
        action="store",
        help="Attributes for second featured image as "
        + "(col, ncols, row, nrows, file_name).",
    )

    ap.add_argument(
        "--shuffle-mode",
        dest="shuffle_mode",
        type=str,
        action="store",
        help=textwrap.dedent(
            """\
            Flags that control shuffling (random order):
                i = images
                b = background image
                c = columns
                r = rows
                wc = weighted columns
                wr = weighted rows
                (weighted favors larger numbers)
                n = do not start over at beginning of list
                    when all images have been used.
            Example: --shuffle-mode=ibwc
        """
        ),
    )

    ap.add_argument(
        "--shuffle-count",
        dest="shuffle_count",
        type=int,
        action="store",
        help="Number of output files to create when using --shuffle-mode.",
    )

    ap.add_argument(
        "--stamp-mode",
        dest="stamp_mode",
        type=int,
        action="store",
        help=textwrap.dedent(
            """\
            Mode for adding a date_time stamp to the output file name:
                0 = none
                1 = at left of file name
                2 = at right of file name
                3 = at left of file name, include microseconds
                4 = at right of file name, include microseconds
            """
        ),
    )

    ap.add_argument(
        "-s",
        "--settings-file",
        dest="settings_file",
        action="store",
        help="Name of settings file.",
    )

    ap.add_argument(
        "-z",
        "--zoom",
        dest="do_zoom",
        action="store_true",
        help="Zoom images to fill instead of fitting to frame.",
    )

    ap.add_argument(
        "-q",
        dest="do_quit",
        action="store_true",
        help="Quit immediately when there is an error. By default you are "
        + "asked to press Enter to acknowledge the error message.",
    )

    ap.add_argument(
        "--write-opts",
        dest="write_opts",
        action="store_true",
        help="Write the option settings to a file.",
    )

    # TODO: Add details to help messages.

    return ap.parse_args()


def get_option_entries(opt_section, opt_content):
    result = []
    in_section = False
    for line in opt_content:
        s = line.strip()
        if (0 < len(s)) and not s.startswith("#"):
            if in_section:
                #  New section?
                if s.startswith("["):
                    in_section = False
                else:
                    result.append(s)
            if s == opt_section:
                in_section = True
    return result


def get_opt_str(default, opt_name, content):
    for opt in content:
        if opt.strip().startswith(opt_name):
            a = opt.split("=", 1)
            if len(a) == 2:
                if a[0].strip() == opt_name:
                    return a[1].strip("'\" ")
    return default


def get_opt_int(default, opt_name, content):
    s = get_opt_str(None, opt_name, content)
    if (s is None) or (len(s) == 0):
        return default
    else:
        assert s.isdigit()
        # TODO: Handle case of invalid int setting.
        return int(s)


def get_opt_bool(default, opt_name, content):
    s = get_opt_str(None, opt_name, content)
    if (s is None) or (len(s) == 0):
        return default
    s = s[0].lower()
    #  The values 'True', 'Yes', 'Y', and '1' are considered True.
    #  Only the first character is checked, so any value starting
    #  with one of those characters is taken as True.
    return s in ("t", "y", "1")


def get_feature_args(feat_args):
    if feat_args is None:
        return FeatureImage(0, 0, 0, 0, "")

    a = feat_args.strip("()").split(",")

    if len(a) != 5:
        print(
            "WARNING: Ignoring invalid feature attributes. ",
            "Expected five values separated by commas.",
        )
        return FeatureImage(0, 0, 0, 0, "")

    if any(not x.strip().isdigit() for x in a[:-1]):
        print(
            "WARNING: Ignoring invalid feature attributes. ",
            "Expected first four numeric values are numeric.",
        )
        return FeatureImage(0, 0, 0, 0, "")

    fn = a[4].strip("\\'\" ")

    return FeatureImage(int(a[0]), int(a[1]), int(a[2]), int(a[3]), fn)


def get_opt_feat(section_content, default_to_none):
    col = get_opt_int(0, "column", section_content)
    ncols = get_opt_int(0, "num_columns", section_content)
    row = get_opt_int(0, "row", section_content)
    nrows = get_opt_int(0, "num_rows", section_content)
    file_name = get_opt_str("", "file", section_content)
    if (ncols == 0) and default_to_none:
        return None
    else:
        return FeatureImage(col, ncols, row, nrows, file_name)


def as_int_list(text, default=None):
    if (text is None) or (len(text) == 0):
        return default
    else:
        a = [
            int(x) for x in [t.strip() for t in text.split(",")] if 0 < len(x)
        ]
        return a


def int_list_str(int_list):
    return ",".join([str(x) for x in int_list])


def qs(s: str) -> str:
    """Returns the given string in quotes if it contains spaces."""

    if s is None:
        return ""

    assert '"' not in s
    #  TODO: Handle this case instead of just asserting? If so, are quotes
    #  doubled ("") or escaped (\")?

    if " " in s:
        return f'"{s}"'
    else:
        return s


def get_rgba(default, arg_str):
    if arg_str is None:
        return default

    a = arg_str.strip().split(",")

    if any(not x.isdigit() for x in a):
        print(
            "WARNING: Invalid backround color setting. ",
            "Expecting numeric values separated by commas. ",
            "Using default setting.",
        )
        return default

    if any(int(x) < 0 or 255 < int(x) for x in a):
        print(
            "WARNING: Invalid backround color setting. ",
            "Expecting numeric values between 0 and 255. ",
            "Using default setting.",
        )
        return default

    if len(a) == 3:
        default_alpha = 255
        rgba = (int(a[0]), int(a[1]), int(a[2]), default_alpha)
        return rgba
    elif len(a) == 4:
        rgba = (int(a[0]), int(a[1]), int(a[2]), int(a[3]))
        return rgba
    else:
        print(
            "WARNING: Invalid color setting. ",
            "Expecting numeric color values separated by commas",
            "('r,g,b' or 'r,g,b,a'). ",
            "Using default.",
        )
        return default


def place_feature(opts: MontageOptions, feat_attr: FeatureImage, cell_size):
    if feat_attr.nrows and feat_attr.ncols:
        x = opts.margin + ((feat_attr.col - 1) * cell_size[0]) + opts.padding
        y = opts.margin + ((feat_attr.row - 1) * cell_size[1]) + opts.padding
        w = int((cell_size[0] * feat_attr.ncols) - (opts.padding * 2))
        h = int((cell_size[1] * feat_attr.nrows) - (opts.padding * 2))
        opts.add_placement(x, y, w, h, feat_attr.file_name)


def outside_feat(col_index, row_index, feat_attr: FeatureImage):
    if feat_attr.nrows and feat_attr.ncols:
        a = (col_index + 1) in range(
            feat_attr.col, feat_attr.col + feat_attr.ncols
        )
        b = (row_index + 1) in range(
            feat_attr.row, feat_attr.row + feat_attr.nrows
        )
        return not (a and b)
    return True


def outside_feature(col_index, row_index, feat_1, feat_2):
    a = outside_feat(col_index, row_index, feat_1)
    b = outside_feat(col_index, row_index, feat_2)
    return a and b


def get_new_size_zoom(current_size, target_size):
    scale_w = target_size[0] / current_size[0]
    scale_h = target_size[1] / current_size[1]
    scale_by = max(scale_w, scale_h)
    return (int(current_size[0] * scale_by), int(current_size[1] * scale_by))


def get_crop_box(current_size, target_size):
    cur_w, cur_h = current_size
    trg_w, trg_h = target_size

    if trg_w < cur_w:
        x1, xm = divmod(cur_w - trg_w, 2)
        x2 = cur_w - (x1 + xm)
    else:
        x1 = 0
        x2 = trg_w

    if trg_h < cur_h:
        y1, ym = divmod(cur_h - trg_h, 2)
        y2 = cur_h - (y1 + ym)
    else:
        y1 = 0
        y2 = trg_h

    return (x1, y1, x2, y2)


def add_border(image, border_size, border_xy, opts):
    border_image = Image.new("RGB", border_size, opts.border_rgb())

    border_mask = Image.new("RGBA", border_size, opts.border_mask_rgba())

    image.paste(border_image, border_xy, mask=border_mask)


def create_image(opts: MontageOptions, image_num: int):
    ncols = opts.get_ncols()
    nrows = opts.get_nrows()
    cell_w = int((opts.canvas_width - (opts.margin * 2)) / ncols)
    cell_h = int((opts.canvas_height - (opts.margin * 2)) / nrows)
    cell_size = (cell_w, cell_h)

    inner_w = int(cell_w - (opts.padding * 2))
    inner_h = int(cell_h - (opts.padding * 2))

    opts.log_say(
        "Creating new image (canvas size = {0} x {1} pixels).".format(
            opts.canvas_width, opts.canvas_height
        )
    )
    opts.log_add(f"ncols={ncols}")
    opts.log_add(f"nrows={nrows}")
    opts.log_add(f"cell_size={cell_size}")

    image = Image.new("RGB", opts.canvas_size(), opts.background_rgb())

    if opts.has_background_image():
        opts.log_say(f"Adding background image '{opts.get_bg_file_name()}'")

        bg_image = Image.open(opts.get_bg_file_name())

        opts.log_add(f"(original) bg_image.size='{bg_image.size}")

        zoom_size = get_new_size_zoom(bg_image.size, opts.canvas_size())

        opts.log_add(f"zoom_size='{zoom_size}")

        bg_image = bg_image.resize(zoom_size)

        opts.log_add(f"(resized) bg_image.size='{bg_image.size}")

        crop_box = get_crop_box(bg_image.size, opts.canvas_size())

        opts.log_add(f"crop_box='{crop_box}")

        bg_image = bg_image.crop(crop_box)

        if bg_image.size != opts.canvas_size():
            #  These should match. Warn when they do not.
            opts.log_say(
                "WARNING: bg_image.size={0} but canvas_size={1}.".format(
                    bg_image.size, opts.canvas_size()
                )
            )

        bg_image = bg_image.filter(ImageFilter.BoxBlur(opts.bg_blur))

        bg_mask = Image.new("RGBA", bg_image.size, opts.background_mask_rgba())

        image.paste(bg_image, (0, 0), mask=bg_mask)

    place_feature(opts, opts.feature1, cell_size)

    place_feature(opts, opts.feature2, cell_size)

    for row in range(nrows):
        for col in range(ncols):
            if outside_feature(col, row, opts.feature1, opts.feature2):
                x = opts.margin + (col * cell_w) + opts.padding
                y = opts.margin + (row * cell_h) + opts.padding
                opts.add_placement(x, y, inner_w, inner_h)
                #  Placement is padded left, top, width, height.

    i = 0
    for place in opts.get_placements_list():
        if i < len(opts.current_images):

            if len(place.file_name) == 0:
                image_name = opts.current_images[i]
                i += 1
            else:
                image_name = place.file_name

            assert 0 < len(image_name)

            if image_name == SKIP_MARKER:
                opts.log_say("Skip placement.")
                continue

            opts.log_say(f"Placing image '{image_name}'")

            img = Image.open(image_name)

            img = ImageOps.exif_transpose(img)

            scale_w = place.width / img.width
            scale_h = place.height / img.height

            precrop_w = None
            precrop_h = None
            crop_box = None

            if opts.do_zoom:
                scale_by = max(scale_w, scale_h)
                precrop_w = int(img.width * scale_by)
                precrop_h = int(img.height * scale_by)
                new_w = place.width
                new_h = place.height
                new_x = place.x
                new_y = place.y
                if 0 < opts.border_width:
                    border_size = (place.width, place.height)
                    border_xy = (place.x, place.y)
                    new_w = new_w - (opts.border_width * 2)
                    new_h = new_h - (opts.border_width * 2)
                    new_x = new_x + opts.border_width
                    new_y = new_y + opts.border_width

                crop_box = get_crop_box((precrop_w, precrop_h), (new_w, new_h))

            else:
                scale_by = min(scale_w, scale_h)
                new_w = int(img.width * scale_by)
                new_h = int(img.height * scale_by)

                if new_w < place.width:
                    new_x = place.x + int((place.width - new_w) / 2)
                else:
                    new_x = place.x

                if new_h < place.height:
                    new_y = place.y + int((place.height - new_h) / 2)
                else:
                    new_y = place.y

                if 0 < opts.border_width:
                    border_size = (new_w, new_h)
                    border_xy = (new_x, new_y)
                    new_w = new_w - (opts.border_width * 2)
                    new_h = new_h - (opts.border_width * 2)
                    new_x = new_x + opts.border_width
                    new_y = new_y + opts.border_width

            new_size = (new_w, new_h)
            new_xy = (new_x, new_y)

            if 0 < opts.border_width:
                add_border(image, border_size, border_xy, opts)

            if crop_box is None:
                img = img.resize(new_size)
            else:
                img = img.resize((precrop_w, precrop_h))
                img = img.crop(crop_box)

            image.paste(img, new_xy)

    file_name = opts.image_file_name(image_num)

    opts.log_say(f"Saving '{file_name}'")

    image.save(file_name)

    opts.write_options(file_name)


def create_montage(opts: MontageOptions):
    opts.check_options()
    n_images = opts.get_montage_count()
    for i in range(0, n_images):
        opts.prepare()
        create_image(opts, i + 1)


def main():
    print(f"\n{app_title}\n")

    defaults = MontageDefaults()

    args = get_arguments()

    if args.do_quit:
        global confirm_errors
        confirm_errors = False

    opts = MontageOptions()

    opts.load(args, defaults)

    create_montage(opts)

    print(f"\nDone ({app_title}).")


if __name__ == "__main__":
    main()
