from __future__ import annotations

import argparse
import random
import sys
import textwrap
from datetime import datetime, timezone
from enum import Enum
from importlib import metadata
from pathlib import Path
from typing import NamedTuple

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

DIST_NAME = "montage"
MAX_SHUFFLE_COUNT = 999
MAX_FEATURED_IMAGES = 4
SKIP_MARKER = "(skip)"
DEFAULT_ERRLOG = "montage-errors.txt"

LEN_NAME_VALUE_SPLIT = 2
LEN_RGB = 3
LEN_RGBA = 4

RGBA_MIN = 0
RGBA_MAX = 255
RGB_MID = 128

#  Mode for adding a date_time stamp to the output file name:
class StampMode(Enum):
    NONE = 0
    LEFT = 1  # left of file name
    RIGHT = 2  # right of file name
    LEFT_USEC = 3  # left of file name, include microseconds
    RIGHT_USEC = 4  # right of file name, include microseconds


class ErrorLog:
    def __init__(self):
        self.log_file_name = str(Path.cwd().joinpath(DEFAULT_ERRLOG))

    def set_filename(self, file_name: str):
        self.log_file_name = file_name

    @property
    def file_name(self):
        return self.log_file_name


errlog = ErrorLog()


class FeatureAttributes(NamedTuple):
    col: int
    ncols: int
    row: int
    nrows: int
    file_names: list[str]


class FeaturedImage:
    def __init__(self, initial_attr: FeatureAttributes):
        self.initial_attr: FeatureAttributes = initial_attr
        self.current_attr: FeatureAttributes = None
        self.feature_index = -1

    def get_next_feature_index(self):
        self.feature_index += 1
        if len(self.current_attr.file_names) <= self.feature_index:
            self.feature_index = 0
        return self.feature_index


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
        self._run_dt = datetime.now(timezone.utc)
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
        self.bg_rgba = None
        self.bg_blur = None
        self.shuffle_mode = None
        self.shuffle_count = None
        self.stamp_mode = None
        self.write_opts = None
        self.border_width = None
        self.border_rgba = None
        self.do_zoom = None
        self.label_font = None
        self.label_size = None
        self.init_img1_pos = None
        self.curr_img1_pos = None
        self.img1_pos_index = -1
        self.img1_start = 1
        self.init_img1_freq = None
        self.img1_freq_index = -1
        self.img1_next = 1
        self.do_img1 = False

        self.pool_index = -1
        self.pool_wrapped = False
        self.bg_index = -1
        self.im1_index = -1
        self.col_index = -1
        self.row_index = -1

        self.featured_images: list[FeaturedImage] = []

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

    def get_next_pool_index(self):
        self.pool_index += 1
        if len(self.image_pool) <= self.pool_index:
            self.pool_index = 0
            self.pool_wrapped = True
        return self.pool_index

    def get_next_im1_index(self):
        self.im1_index += 1
        if len(self.init_images1) <= self.im1_index:
            self.im1_index = 0
        return self.im1_index

    def set_bg_index(self):
        n = len(self.init_bg_images)
        if n == 0:
            self.bg_index = -1
        elif self.do_shuffle_bg_images():
            self.bg_index = random.randrange(n)
        else:
            self.bg_index += 1
            if self.bg_index == len(self.init_bg_images):
                self.bg_index = 0

    def get_feature_filename(self, feature: FeatureAttributes, index: int):
        if index < len(feature.file_names):
            return feature.file_names[index]
        return ""

    def add_placement(self, x, y, w, h, file_name=""):
        self._placements.append(Placement(x, y, w, h, file_name))

    def get_placements_list(self) -> list[Placement]:
        return self._placements

    def has_background_image(self) -> bool:
        return bool(self.init_bg_images)

    def get_bg_file_name(self):
        if self.bg_index >= 0:
            return self.init_bg_images[self.bg_index]
        return None

    def background_rgb(self):
        return self.bg_rgba[:3]

    def background_mask_rgba(self):
        return (0, 0, 0, self.bg_rgba[3])

    def border_rgb(self):
        return self.border_rgba[:3]

    def border_mask_rgba(self):
        return (0, 0, 0, self.border_rgba[3])

    def set_cols(self):
        n = len(self.init_ncols)
        if "c" in self.shuffle_mode:
            if n == 1:
                self.cols = random.randint(1, self.init_ncols[0])
            else:
                self.col_index = random.randrange(n)
                self.cols = self.init_ncols[self.col_index]
        else:
            self.col_index += 1
            if n <= self.col_index:
                self.col_index = 0
            self.cols = self.init_ncols[self.col_index]

        assert self.cols

    def set_rows(self):
        n = len(self.init_nrows)
        if "r" in self.shuffle_mode:
            if n == 1:
                self.rows = random.randint(1, self.init_nrows[0])
            else:
                self.row_index = random.randrange(n)
                self.rows = self.init_nrows[self.row_index]
        else:
            self.row_index += 1
            if len(self.init_nrows) <= self.row_index:
                self.row_index = 0
            self.rows = self.init_nrows[self.row_index]

        assert self.rows

    def _get_img1_freq(self):
        self.img1_freq_index += 1
        if len(self.init_img1_freq) <= self.img1_freq_index:
            self.img1_freq_index = 0
        return self.init_img1_freq[self.img1_freq_index]

    def _set_img1_pos(self, image_num: int):
        self.do_img1 = False
        self.curr_img1_pos = 0

        if not self.init_images1:
            #  Nothing in [images-1] section.
            return

        if image_num < self.img1_start:
            #  Not yet at starting image number.
            return

        self.img1_next -= 1
        if self.img1_next == 0:
            self.img1_next = self._get_img1_freq()
        else:
            #  Current image number is not the next image-1 based on
            #  frequency list.
            return

        self.do_img1 = True

        if len(self.init_img1_pos) == 0:
            #  No position specified. Will be placed according to shuffle.
            return

        self.img1_pos_index += 1
        if len(self.init_img1_pos) <= self.img1_pos_index:
            self.img1_pos_index = 0
        self.curr_img1_pos = self.init_img1_pos[self.img1_pos_index]

    def get_ncols(self):
        if self.cols is None:
            self.set_cols()
        return self.cols

    def get_nrows(self):
        if self.rows is None:
            self.set_rows()
        return self.rows

    def _feature_cell_count(self):
        n = 0
        for feat in self.featured_images:
            n += feat.current_attr.ncols * feat.current_attr.nrows
        return n

    def _current_image_count(self):
        n = self.get_ncols() * self.get_nrows()
        n -= self._feature_cell_count()
        return n

    def _load_current_images(self, image_num: int):
        self.current_images.clear()
        n_images = self._current_image_count()

        self._set_img1_pos(image_num)

        #  If img1_pos is greater than the number of images then
        #  ignore that option.
        if n_images < self.curr_img1_pos:
            self.curr_img1_pos = 0

        if self.do_img1:
            n_images -= 1

        no_wrap = "n" in self.shuffle_mode

        if self.image_pool:
            while len(self.current_images) < n_images:
                ix = self.get_next_pool_index()
                if self.pool_wrapped and no_wrap:
                    break
                self.current_images.append(self.image_pool[ix])

        if self.do_img1 and self.curr_img1_pos < 1:
            #  Image from [images-1] in shuffle (not at fixed position).
            self.current_images.append(
                self.init_images1[self.get_next_im1_index()]
            )

        if self.do_shuffle_images():
            random.shuffle(self.current_images)

        if self.init_images1 and self.curr_img1_pos > 0:
            #  Image from [images-1] inserted at fixed position.
            #  Position is in range 1..n_images (index + 1).
            self.current_images.insert(
                self.curr_img1_pos - 1,
                self.init_images1[self.get_next_im1_index()],
            )

    def do_shuffle_images(self):
        return "i" in self.shuffle_mode

    def do_shuffle_bg_images(self):
        return "b" in self.shuffle_mode

    def get_montages_count(self):
        return min(self.shuffle_count, MAX_SHUFFLE_COUNT)

    def log_add(self, message):
        self._log.append(message)

    def log_say(self, message):
        print(message)
        self._log.append(message)

    def prepare_feature(self, feat: FeatureAttributes) -> FeatureAttributes:
        if feat.ncols == 0 or feat.nrows == 0:
            return feat

        #  Adjust placement to available columns and rows in case feature
        #  is out-of-bounds as specified.
        img_ncols = self.get_ncols()

        at_col = feat.col
        while at_col > 1 and img_ncols < ((at_col - 1) + feat.ncols):
            at_col -= 1

        use_ncols = feat.ncols
        while use_ncols > 0 and img_ncols < use_ncols:
            use_ncols -= 1

        assert at_col
        assert use_ncols

        img_nrows = self.get_nrows()
        at_row = feat.row
        while at_row > 1 and img_nrows < ((at_row - 1) + feat.nrows):
            at_row -= 1
        use_nrows = feat.nrows
        while use_nrows > 0 and img_nrows < use_nrows:
            use_nrows -= 1

        assert at_row
        assert use_nrows

        filenames = [*feat.file_names]
        if "f" in self.shuffle_mode:
            random.shuffle(filenames)

        return FeatureAttributes(
            at_col, use_ncols, at_row, use_nrows, filenames
        )

    def prepare(self, image_num: int):
        self._placements.clear()
        self._log.clear()
        self.set_cols()
        self.set_rows()

        for feat in self.featured_images:
            feat.current_attr = self.prepare_feature(feat.initial_attr)

        if len(self.image_pool) == 0:  # First run.
            self.pool_index = -1
            self.image_pool = [*self.init_images]
            if self.do_shuffle_images():
                random.shuffle(self.image_pool)
        elif self.pool_wrapped and self.do_shuffle_images():
            random.shuffle(self.image_pool)
        self._load_current_images(image_num)
        self.pool_wrapped = False
        self.set_bg_index()

    def _timestamp_str(self):
        if self.stamp_mode in [StampMode.LEFT_USEC, StampMode.RIGHT_USEC]:
            fmt_str = "%Y%m%d_%H%M%S_%f"
        else:
            fmt_str = "%Y%m%d_%H%M%S"
        return self._run_dt.astimezone().strftime(fmt_str)

    def image_file_name(self, image_num):
        out_dir = Path(self.output_dir).expanduser().resolve() if self.output_dir else Path.cwd()

        assert out_dir.is_dir
        assert out_dir.exists()

        p = Path(self.output_file_name)

        if self.shuffle_count > 1:
            #  Note: The zero-padded length in the format for image_num should
            #  match the length of the value in MAX_SHUFFLE_COUNT.
            p = Path(f"{p.with_suffix('')}-{image_num:03d}").with_suffix(p.suffix)

        if self.stamp_mode in [StampMode.LEFT, StampMode.LEFT_USEC]:
            #  Mode 1: date_time stamp at left of file name.
            p = Path(
                f"{self._timestamp_str()}_{p.with_suffix('')}"
            ).with_suffix(p.suffix)
        elif self.stamp_mode in [StampMode.RIGHT, StampMode.RIGHT_USEC]:
            #  Mode 2: date_time stamp at right of file name.
            p = Path(
                f"{p.with_suffix('')}_{self._timestamp_str()}"
            ).with_suffix(p.suffix)

        return str(out_dir.joinpath(p))

    def _options_as_str(self):
        s = ""
        s += "\n[settings]\n"
        s += f"output_file={qs(self.output_file_name)}\n"
        s += f"output_dir={qs(self.output_dir)}\n"
        s += f"canvas_width={self.canvas_width}\n"
        s += f"canvas_height={self.canvas_height}\n"
        s += f"background_rgba={self.bg_rgba[0]},{self.bg_rgba[1]},{self.bg_rgba[2]},{self.bg_rgba[3]}\n"
        s += f"background_blur={self.bg_blur}\n"
        s += f"columns={int_list_str(self.init_ncols)}\n"
        s += f"rows={int_list_str(self.init_nrows)}\n"
        s += f"margin={self.margin}\n"
        s += f"padding={self.padding}\n"
        s += f"border_width={self.border_width}\n"
        s += f"border_rgba={self.border_rgba[0]},{self.border_rgba[1]},{self.border_rgba[2]},{self.border_rgba[3]}\n"
        s += f"do_zoom={self.do_zoom}\n"
        s += f"img1_pos={int_list_str(self.init_img1_pos)}\n"
        s += f"img1_start={self.img1_start}\n"
        s += f"img1_freq={int_list_str(self.init_img1_freq)}\n"
        s += f"label_font={self.label_font}\n"
        s += f"label_size={self.label_size}\n"
        s += f"shuffle_mode={self.shuffle_mode}\n"
        s += f"shuffle_count={self.shuffle_count}\n"
        s += f"stamp_mode={self.stamp_mode}\n"
        s += f"write_opts={self.write_opts}\n"

        if self.featured_images:
            for feat_num, feat in enumerate(self.featured_images, start=1):
                s += f"\n[feature-{feat_num}]\n"
                s += (
                    "file="
                    f"{qs(self.get_feature_filename(feat.current_attr, 0))}\n"
                )
                s += f"column={feat.current_attr.col}\n"
                s += f"row={feat.current_attr.row}\n"
                s += f"num_columns={feat.current_attr.ncols}\n"
                s += f"num_rows={feat.current_attr.nrows}\n"
                for i in feat.current_attr.file_names[1:]:
                    s += f"{qs(i)}\n"
        else:
            #  Add a [Feature-1] template when the current montage has no
            #  featured images.
            s += "\n# [feature-1]\n"
            s += "# file=\n"
            s += "# column=\n"
            s += "# row=\n"
            s += "# num_columns=\n"
            s += "# num_rows=\n"

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
                Path(f"{p.with_suffix('')}_options").with_suffix(".txt")
            )

            print(f"\nWriting options to '{file_name}'\n")
            with open(file_name, "w") as f:
                f.write(
                    f"# Created {datetime.now(timezone.utc).astimezone().strftime('%Y-%m-%d %H:%M')}"
                    f" by {app_title()}\n"
                )

                f.write(self._options_as_str())

                f.write("\n\n[LOG: CURRENT-IMAGES]\n")
                for i in self.current_images:
                    f.write(f"{qs(i)}\n")

                if self._log:
                    f.write("\n\n[LOG: STEPS]\n")
                    for i in self._log:
                        f.write(f"{i}\n")

    def check_feature(self, feat_num: int, feat_attr: FeatureAttributes):
        errors = []
        numeric_attrs = [
            feat_attr.col,
            feat_attr.ncols,
            feat_attr.row,
            feat_attr.nrows,
        ]

        if any(x > 0 for x in numeric_attrs):
            if any(x <= 0 for x in numeric_attrs):
                errors.append(
                    f"Feature-{feat_num}: All column and row settings must "
                    "be set to not-zero values if any are set."
                )
            if len(self.get_feature_filename(feat_attr, 0)) == 0:
                errors.append(f"Feature-{feat_num}: File name must be set.")

        if feat_attr.file_names:
            # for file_name in feat_attr.file_names:
            #     if not (
            #         file_name == SKIP_MARKER
            #         or Path(file_name).expanduser().resolve().exists()
            #     ):
            #         errors.append(
            #             f"Feature-{feat_num}: Image file not found: '{file_name}'."
            #         )
            errors.extend(
                f"Feature-{feat_num}: Image file not found: '{file_name}'."
                for file_name in feat_attr.file_names
                if not (
                    file_name == SKIP_MARKER
                    or Path(file_name).expanduser().resolve().exists()
                )
            )

        return errors

    def check_options(self):
        errors = []

        if self.output_dir:
            if not Path(self.output_dir).exists():
                errors.append(f"Output folder not found: '{self.output_dir}'.")

            if not Path(self.output_dir).is_dir():
                errors.append(
                    f"Output folder not a directory: '{self.output_dir}'."
                )

        # for file_name in self.init_images:
        #     if (file_name.strip() != SKIP_MARKER) and (not Path(file_name).expanduser().resolve().exists()):
        #         errors.append(f"Image file not found: '{file_name}'.")
        errors.extend(
            f"Image file not found: '{file_name}'."
            for file_name in self.init_images
            if (file_name.strip() != SKIP_MARKER) and (not Path(file_name).expanduser().resolve().exists())
        )

        # for file_name in self.init_images1:
        #     if (file_name.strip() != SKIP_MARKER) and (not Path(file_name).expanduser().resolve().exists()):
        #         errors.append(f"Image file not found: '{file_name}'.")
        errors.extend(
            f"Image file not found: '{file_name}'."
            for file_name in self.init_images1
            if (file_name.strip() != SKIP_MARKER) and (not Path(file_name).expanduser().resolve().exists())
        )

        # for file_name in self.init_bg_images:
        #     if not Path(file_name).expanduser().resolve().exists():
        #         errors.append(
        #             f"Background image file not found: '{file_name}'."
        #         )
        errors.extend(
            f"Background image file not found: '{file_name}'."
            for file_name in self.init_bg_images
            if not Path(file_name).expanduser().resolve().exists()
        )

        for feat_num, feat in enumerate(self.featured_images, start=1):
            errors += self.check_feature(feat_num, feat.initial_attr)

        if errors:
            error_exit("CANNOT PROCEED", error_list=errors)

    def _load_from_file(self, file_name):
        if file_name is not None:
            p = Path(file_name).expanduser().resolve()
            if not p.exists():
                error_exit(f"ERROR: File not found: {p}", [])

            print(f"Load settings from '{p.name}' in '{p.parent}'.")

            with open(p) as f:
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

            self.label_font = get_opt_str(None, "label_font", settings)

            self.label_size = get_opt_int(None, "label_size", settings)

            self.shuffle_mode = get_opt_str(None, "shuffle_mode", settings)

            self.shuffle_count = get_opt_int(None, "shuffle_count", settings)

            self.stamp_mode = get_opt_int(None, "stamp_mode", settings)

            self.write_opts = get_opt_bool(None, "write_opts", settings)

            self.do_zoom = get_opt_bool(None, "do_zoom", settings)

            self.img1_start = get_opt_int(1, "img1_start", settings)

            self.init_img1_freq = as_int_list(
                get_opt_str(None, "img1_freq", settings)
            )

            self.init_img1_pos = as_int_list(
                get_opt_str(None, "img1_pos", settings)
            )

            for feat_num in range(1, MAX_FEATURED_IMAGES + 1):
                temp_feat: FeatureAttributes = get_opt_feat(
                    get_option_entries(f"[feature-{feat_num}]", file_text),
                    True,
                )
                if temp_feat:
                    self.featured_images.append(FeaturedImage(temp_feat))

            self.init_images += [
                unquote(i) for i in get_option_entries("[images]", file_text)
            ]

            self.init_images1 += [
                unquote(i) for i in get_option_entries("[images-1]", file_text)
            ]

            self.init_bg_images += [
                unquote(i)
                for i in get_option_entries("[background-images]", file_text)
            ]

    def _set_defaults(self, defaults: MontageDefaults):
        #  Use defaults for options not already set.

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
        elif isinstance(self.border_rgba, str):
            self.border_rgba = get_rgba(defaults.border_rgba, self.border_rgba)

        if self.bg_rgba is None:
            self.bg_rgba = defaults.background_rgba
        elif isinstance(self.bg_rgba, str):
            self.bg_rgba = get_rgba(defaults.background_rgba, self.bg_rgba)

        if self.bg_blur is None:
            self.bg_blur = defaults.bg_blur

        if self.label_font is None:
            self.label_font = ""

        if self.label_size is None:
            self.label_size = 0

        if self.shuffle_mode is None:
            self.shuffle_mode = ""

        if self.shuffle_count is None:
            self.shuffle_count = 1

        if self.stamp_mode is None:
            self.stamp_mode = StampMode.NONE

        if self.write_opts is None:
            self.write_opts = False

        if self.do_zoom is None:
            self.do_zoom = False

        if self.init_img1_freq is None:
            self.init_img1_freq = [1]

        if self.init_img1_pos is None:
            self.init_img1_pos = []

    def load(self, args, defaults: MontageDefaults, settings_file=None):
        if args is None and settings_file is None:
            error_exit("ERROR: No args object and no settings file name.", [])

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

            if args.label_font is not None:
                self.label_font = args.label_font

            if args.label_size is not None:
                self.label_size = args.label_size

            if args.shuffle_mode is not None:
                self.shuffle_mode = args.shuffle_mode

            if args.shuffle_count is not None:
                self.shuffle_count = args.shuffle_count

            if args.stamp_mode is not None:
                self.stamp_mode = args.stamp_mode

            if (args.write_opts is not None) and args.write_opts:
                self.write_opts = True

            if (args.do_zoom is not None) and args.do_zoom:
                self.do_zoom = True

            #  Only support 2 featured images via command-line args.
            #  TODO: Accept more than two?

            if args.feature_1 is not None:
                assert len(self.featured_images) < MAX_FEATURED_IMAGES
                self.featured_images.append(
                    FeaturedImage(get_feature_args(args.feature_1))
                )

            if args.feature_2 is not None:
                assert len(self.featured_images) < MAX_FEATURED_IMAGES
                self.featured_images.append(
                    FeaturedImage(get_feature_args(args.feature_2))
                )

            self.init_images = [i for i in args.images if i] + self.init_images

        self.init_images = expand_image_list(self.init_images)

        self.init_images1 = expand_image_list(self.init_images1)

        self.init_bg_images = expand_image_list(self.init_bg_images)

        self._set_defaults(defaults)

        self.shuffle_mode = self.shuffle_mode.lower()


# ----------------------------------------------------------------------

def app_title():
    try:
        ver = metadata.version(DIST_NAME)
    except metadata.PackageNotFoundError:
        ver = "?"
    return f"make-montage ({Path(__file__).name} v{ver})"


def error_exit(error_message: str, error_list: list[str]):
    errs = []
    errs.append(f"\n[{datetime.now(timezone.utc).astimezone().strftime('%Y-%m-%d %H:%M')}]")
    errs.append(f"HALTED {app_title()}")

    if error_message:
        errs.append(error_message)
        print("")
        sys.stderr.write(f"{error_message}\n")

    if error_list:
        print("")
        for s in error_list:
            errs.append(s)
            sys.stderr.write(f"{s}\n")

    print("*" * 70)
    print("Halted due to errors.")

    if errlog.file_name:
        print(f"\nWriting '{errlog.file_name}'.\n")
        with open(errlog.file_name, "a") as t:
            for e in errs:
                t.write(f"{e}\n")

    sys.exit(1)


def unquote(text: str) -> str:
    s = text.strip()
    if s:
        if s[0] == '"':
            return s.strip('"')
        if s[0] == "'":
            return s.strip("'")
    return s


def get_list_from_file(file_name):
    p = Path(file_name).expanduser().resolve()
    if not p.exists():
        error_exit(f"ERROR: File not found: {p}", [])

    result = []

    with open(p) as f:
        file_text = f.readlines()

    for line in file_text:
        s = unquote(line)
        if s and not s.startswith("#"):
            result.append(s)

    return result


def expand_image_list(raw_list):
    new_list = []
    if raw_list:
        assert isinstance(raw_list, list)
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
        if len(a) == LEN_NAME_VALUE_SPLIT:
            setting_name = a[0].strip()
            if setting_name in old_settings:
                print(
                    f"WARNING: Obsolete setting '{setting_name}': {old_settings[setting_name]}"
                )


def get_arguments(arglist=None):
    ap = argparse.ArgumentParser(
        formatter_class=argparse.RawTextHelpFormatter,
        description="Create an image montage given a list of image files.",
    )

    ap.add_argument(
        "images",
        nargs="*",
        action="store",
        help="Images files to include in the montage image."
        " Multiple files can be specified.",
    )

    ap.add_argument(
        "-s",
        "--settings-file",
        dest="settings_file",
        action="store",
        help="Name of settings (options) file.",
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
        type=str,
        action="store",
        help="Number of columns.",
    )

    ap.add_argument(
        "-r",
        "--rows",
        dest="rows",
        type=str,
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
        help="Attributes for first featured image as"
        " (col, ncols, row, nrows, file_name).",
    )

    ap.add_argument(
        "--feature-2",
        dest="feature_2",
        type=str,
        action="store",
        help="Attributes for second featured image as"
        " (col, ncols, row, nrows, file_name).",
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
                f = feature (where a feature has multiple images)
                n = do not start over at beginning of list
                    when all images have been used.
            Example: --shuffle-mode=ib
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
        "-z",
        "--zoom",
        dest="do_zoom",
        action="store_true",
        help="Zoom images to fill instead of fitting to frame.",
    )

    ap.add_argument(
        "--error-log",
        dest="error_log",
        type=str,
        help="Change the file name used for the error log file. "
        f"By default the error log is named '{DEFAULT_ERRLOG}'.",
    )

    ap.add_argument(
        "--no-log",
        dest="no_log",
        action="store_true",
        help="Do not write a log file when there are errors.",
    )

    ap.add_argument(
        "--write-opts",
        dest="write_opts",
        action="store_true",
        help="Write the option settings to a file.",
    )

    ap.add_argument(
        "--label-font",
        dest="label_font",
        type=str,
        help="Font to use for file name label added to images. A file name"
        " label is useful for making an image catalog.",
    )

    ap.add_argument(
        "--label-size",
        dest="label_size",
        type=int,
        help="Point size for font used to add a file name label to images.",
    )

    # TODO: Add details to help messages.

    return ap.parse_args(arglist)


def get_option_entries(opt_section, opt_content):
    result = []
    in_section = False
    for line in opt_content:
        s = line.strip()
        if s and not s.startswith("#"):
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
            if (len(a) == LEN_NAME_VALUE_SPLIT) and (a[0].strip() == opt_name):
                return unquote(a[1])
    return default


def get_opt_int(default, opt_name, content):
    s = get_opt_str(None, opt_name, content)
    if (s is None) or (len(s) == 0):
        return default

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
        return FeatureAttributes(0, 0, 0, 0, [])

    a = feat_args.strip("()").split(",")

    expect_n_fields = 5
    if len(a) != expect_n_fields:
        print(
            "WARNING: Ignoring invalid feature attributes. "
            "Expected five values separated by commas."
        )
        return FeatureAttributes(0, 0, 0, 0, [])

    if any(not x.strip().isdigit() for x in a[:-1]):
        print(
            "WARNING: Ignoring invalid feature attributes. "
            "Expected first four numeric values are numeric."
        )
        return FeatureAttributes(0, 0, 0, 0, [])

    filename = unquote(a[4])
    filename_list = expand_image_list([filename])

    return FeatureAttributes(
        int(a[0]),
        int(a[1]),
        int(a[2]),
        int(a[3]),
        filename_list,
    )


def get_opt_feat(section_content, default_to_none):
    col = get_opt_int(0, "column", section_content)
    ncols = get_opt_int(0, "num_columns", section_content)
    row = get_opt_int(0, "row", section_content)
    nrows = get_opt_int(0, "num_rows", section_content)
    file_name = get_opt_str("", "file", section_content)

    file_names = [] if len(file_name) == 0 else [file_name]

    #  Get any additional file names in Feature section.
    # for line in section_content:
    #     if "=" not in line:
    #         file_names.append(unquote(line))
    file_names.extend(unquote(line) for line in section_content if "=" not in line)

    file_names = expand_image_list(file_names)

    if (ncols == 0) and default_to_none:
        return None

    return FeatureAttributes(col, ncols, row, nrows, file_names)


def as_int_list(text: str, default=None):
    """
    Takes a string representing a list of one or more integer values,
    separated by commas, and returns a list of integers. If the input
    is None, or an empty string, a default value (or None) is returned.
    """
    if (text is None) or (len(text) == 0):
        return default

    return [int(x) for x in [t.strip() for t in text.split(",")] if x]


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
    return s


def get_rgba(default, arg_str):
    if arg_str is None:
        return default

    a = arg_str.strip().split(",")

    if any(not x.isdigit() for x in a):
        print(
            "WARNING: Invalid backround color setting. "
            "Expecting numeric values separated by commas. "
            "Using default setting."
        )
        return default

    if any(int(x) < RGBA_MIN or int(x) > RGBA_MAX for x in a):
        print(
            "WARNING: Invalid backround color setting. "
            "Expecting numeric values between 0 and 255. "
            "Using default setting."
        )
        return default

    if len(a) == LEN_RGB:
        return (int(a[0]), int(a[1]), int(a[2]), RGBA_MAX)

    if len(a) == LEN_RGBA:
        return (int(a[0]), int(a[1]), int(a[2]), int(a[3]))

    print(
        "WARNING: Invalid color setting. "
        "Expecting numeric color values separated by commas "
        "('r,g,b' or 'r,g,b,a'). "
        "Using default."
    )
    return default


def place_feature(
    opts: MontageOptions, feat_attr: FeatureAttributes, image_index, cell_size
):
    if feat_attr.nrows and feat_attr.ncols:
        x = opts.margin + ((feat_attr.col - 1) * cell_size[0]) + opts.padding
        y = opts.margin + ((feat_attr.row - 1) * cell_size[1]) + opts.padding
        w = int((cell_size[0] * feat_attr.ncols) - (opts.padding * 2))
        h = int((cell_size[1] * feat_attr.nrows) - (opts.padding * 2))
        opts.add_placement(x, y, w, h, feat_attr.file_names[image_index])


def outside_feat(col_index, row_index, feat_attr: FeatureAttributes):
    if feat_attr.nrows and feat_attr.ncols:
        a = (col_index + 1) in range(
            feat_attr.col, feat_attr.col + feat_attr.ncols
        )
        b = (row_index + 1) in range(
            feat_attr.row, feat_attr.row + feat_attr.nrows
        )
        return not (a and b)
    return True


def outside_feature(col_index, row_index, feat_imgs: list[FeaturedImage]):
    # for feat in feat_imgs:
    #     if not outside_feat(col_index, row_index, feat.current_attr):
    #         return False
    # return True
    return all(outside_feat(col_index, row_index, feat.current_attr) for feat in feat_imgs)


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


def add_label(
    image: Image.Image,
    file_name: str,
    at_x: int,
    at_y: int,
    opts: MontageOptions,
):
    assert opts.label_font
    assert opts.label_size

    try:
        if opts.label_font.lower().endswith(".ttf"):
            font = ImageFont.truetype(opts.label_font, opts.label_size)
        else:
            font = ImageFont.load(opts.label_font)
    except OSError:
        print(f"WARNING: Cannot load font '{opts.label_font}'.")
        return

    draw = ImageDraw.Draw(image)

    label_text = Path(file_name).name

    #  New image is RGB so there should be 3 bands.
    bands = image.getbands()
    assert len(bands) == LEN_RGB

    try:
        px = image.getpixel((at_x, at_y))
    except IndexError:
        print(
            "WARNING: Cannot place label. Try increasing 'padding' and/or "
            "'margin' values."
        )
        return

    #  Use average of RGB to select white or black fill.
    avg = int(sum(px) / 3)
    fill_rgba = (0, 0, 0, 255) if avg > RGB_MID else (255, 255, 255, 255)

    draw.text((at_x, at_y), label_text, font=font, fill=fill_rgba)


def create_image(opts: MontageOptions, image_num: int):
    ncols = opts.get_ncols()
    nrows = opts.get_nrows()
    cell_w = int((opts.canvas_width - (opts.margin * 2)) / ncols)
    cell_h = int((opts.canvas_height - (opts.margin * 2)) / nrows)
    cell_size = (cell_w, cell_h)

    inner_w = int(cell_w - (opts.padding * 2))
    inner_h = int(cell_h - (opts.padding * 2))

    opts.log_say(
        f"Creating new image (canvas size = {opts.canvas_width} x {opts.canvas_height} pixels)."
    )
    opts.log_add(f"ncols={ncols}")
    opts.log_add(f"nrows={nrows}")
    opts.log_add(f"cell_size={cell_size}")

    image = Image.new("RGB", opts.canvas_size(), opts.background_rgb())

    if opts.has_background_image():
        bg_filename = opts.get_bg_file_name()

        opts.log_say(f"Adding background image '{bg_filename}'")

        bg_filename = str(Path(bg_filename).expanduser().resolve())

        bg_image = Image.open(bg_filename)

        bg_image = ImageOps.exif_transpose(bg_image)

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
                f"WARNING: bg_image.size={bg_image.size} but canvas_size={opts.canvas_size()}."
            )

        bg_image = bg_image.filter(ImageFilter.BoxBlur(opts.bg_blur))

        bg_mask = Image.new("RGBA", bg_image.size, opts.background_mask_rgba())

        image.paste(bg_image, (0, 0), mask=bg_mask)

    for feat in opts.featured_images:
        place_feature(
            opts, feat.current_attr, feat.get_next_feature_index(), cell_size
        )

    for row in range(nrows):
        for col in range(ncols):
            if outside_feature(col, row, opts.featured_images):
                x = opts.margin + (col * cell_w) + opts.padding
                y = opts.margin + (row * cell_h) + opts.padding
                opts.add_placement(x, y, inner_w, inner_h)
                #  Placement is padded left, top, width, height.

    i = 0
    for place in opts.get_placements_list():
        if len(place.file_name) == 0:
            if i < len(opts.current_images):
                image_name = opts.current_images[i]
                i += 1
            else:
                continue
        else:
            image_name = place.file_name

        assert image_name

        if image_name == SKIP_MARKER:
            opts.log_say("Skip placement.")
            continue

        opts.log_say(f"Placing image '{image_name}'")

        image_name = str(Path(image_name).expanduser().resolve())

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
            if opts.border_width > 0:
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

            new_x = place.x + int((place.width - new_w) / 2) if new_w < place.width else place.x

            new_y = place.y + int((place.height - new_h) / 2) if new_h < place.height else place.y

            if opts.border_width > 0:
                border_size = (new_w, new_h)
                border_xy = (new_x, new_y)
                new_w = new_w - (opts.border_width * 2)
                new_h = new_h - (opts.border_width * 2)
                new_x = new_x + opts.border_width
                new_y = new_y + opts.border_width

        new_size = (new_w, new_h)
        new_xy = (new_x, new_y)

        if opts.border_width > 0:
            add_border(image, border_size, border_xy, opts)

        if opts.label_size > 0 and opts.label_font:
            label_x = place.x
            label_y = new_y + new_h + opts.border_width + 3
            add_label(image, image_name, label_x, label_y, opts)

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


def create_montages(opts: MontageOptions):
    opts.check_options()
    n_images = opts.get_montages_count()
    for i in range(n_images):
        image_num = i + 1
        opts.prepare(image_num)
        create_image(opts, image_num)


def main(arglist=None):
    print(f"\n{app_title()}\n")

    defaults = MontageDefaults()

    args = get_arguments(arglist)

    if args.no_log:
        errlog.set_filename("")
    elif args.error_log:
        #  Override default error log per arg.
        altlog = Path(args.error_log).expanduser().resolve()
        if not altlog.parent.exists():
            error_exit(f"Cannot find directory for log file: '{altlog.parent}'", [])
        if altlog.exists() and not altlog.is_file():
            error_exit(f"Not a file: '{altlog}'", [])
        errlog.set_filename(str(altlog))

    opts = MontageOptions()

    opts.load(args, defaults)

    create_montages(opts)

    print(f"\nDone ({app_title()}).")

    return 0


if __name__ == "__main__":
    sys.exit(main())
