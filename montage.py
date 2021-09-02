#!/usr/bin/env python3

import argparse
import random
import sys
import textwrap
from collections import namedtuple
from datetime import datetime
from PIL import Image, ImageFilter, ImageOps
from pathlib import Path

MAX_SHUFFLE_COUNT = 99

app_version = '210902.1'

pub_version = '1.0.dev1'

app_title = f'montage.py - version {app_version}'


FeatureImage = namedtuple(
    'FeatureImage', 'col, ncols, row, nrows, file_name'
)

Placement = namedtuple('Placement', 'left, top, width, height, file_name')


class MontageDefaults:

    def __init__(self):
        self.file_name = 'output.jpg'
        self.canvas_width = 640
        self.canvas_height = 480
        self.margin = 10
        self.padding = 10
        self.bg_blur = 3
        self.ncols = 2
        self.nrows = 2
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
        self.image_list = []
        self.bg_image_list = []
        self._placements = []
        self._log = []

    def canvas_size(self):
        return (int(self.canvas_width), int(self.canvas_height))

    def add_placement(self, x, y, w, h, file_name=''):
        self._placements.append(Placement(x, y, w, h, file_name))

    def get_placements_list(self):
        return self._placements

    def has_background_image(self):
        return 0 < len(self.bg_image_list)

    def get_bg_file_name(self):
        return self.bg_image_list[0]

    def background_rgb(self):
        return self.bg_rgba[:3]

    def background_mask_rgba(self):
        return (0, 0, 0, self.bg_rgba[3])

    def border_rgb(self):
        return self.border_rgba[:3]

    def border_mask_rgba(self):
        return (0, 0, 0, self.border_rgba[3])

    def get_shuffled(self, value, weighted_flag):
        if weighted_flag in self.shuffle_mode:
            a = []
            for v in range(1, value + 1):
                for x in range(v * 2):
                    a.append(v)
        else:
            a = [x for x in range(1, value + 1)]
        random.shuffle(a)
        return a[0]

    def set_cols_rows(self):
        if 'c' in self.shuffle_mode:
            self.cols = self.get_shuffled(self.init_ncols, 'wc')
        else:
            self.cols = self.init_ncols
        if 'r' in self.shuffle_mode:
            self.rows = self.get_shuffled(self.init_nrows, 'wr')
        else:
            self.rows = self.init_nrows

    def get_ncols(self):
        if self.cols is None:
            self.set_cols_rows()
        return self.cols

    def get_nrows(self):
        if self.rows is None:
            self.set_cols_rows()
        return self.rows

    def do_shuffle_images(self):
        return 'i' in self.shuffle_mode

    def shuffle_images(self):
        if self.do_shuffle_images():
            random.shuffle(self.image_list)

    def do_shuffle_bg_images(self):
        return 'b' in self.shuffle_mode

    def shuffle_bg_images(self):
        if self.do_shuffle_bg_images():
            random.shuffle(self.bg_image_list)

    def get_image_count(self):
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
        self.shuffle_bg_images()
        self.shuffle_images()

    def _timestamp_str(self):
        if 2 < self.stamp_mode:
            fmt_str = '%Y%m%d_%H%M%S_%f'
        else:
            fmt_str = '%Y%m%d_%H%M%S'
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
            p = Path('{0}-{1:02d}'.format(
                p.with_suffix(''),
                image_num)
            ).with_suffix(p.suffix)

        if self.stamp_mode in [1, 3]:
            #  Mode 1: date_time stamp at left of file name.
            p = Path('{0}_{1}'.format(
                self._timestamp_str(),
                p.with_suffix(''))
            ).with_suffix(p.suffix)
        elif self.stamp_mode in [2, 4]:
            #  Mode 2: date_time stamp at right of file name.
            p = Path('{0}_{1}'.format(
                p.with_suffix(''),
                self._timestamp_str())
            ).with_suffix(p.suffix)

        return str(dir.joinpath(p))

    def _options_as_str(self):
        s = ''
        s += "\n[settings]\n"
        s += f"output_file={qs(self.output_file_name)}\n"
        s += f"output_dir={qs(self.output_dir)}\n"
        s += f"canvas_width={self.canvas_width}\n"
        s += f"canvas_height={self.canvas_height}\n"
        s += "background_rgba={0},{1},{2},{3}\n".format(
            self.bg_rgba[0],
            self.bg_rgba[1],
            self.bg_rgba[2],
            self.bg_rgba[3]
        )
        s += f"background_blur={self.bg_blur}\n"
        s += f"columns={self.init_ncols}\n"
        s += f"rows={self.init_nrows}\n"
        s += f"margin={self.margin}\n"
        s += f"padding={self.padding}\n"
        s += f"border_width={self.border_width}\n"
        s += "border_rgba={0},{1},{2},{3}\n".format(
            self.border_rgba[0],
            self.border_rgba[1],
            self.border_rgba[2],
            self.border_rgba[3]
        )
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
        for i in self.bg_image_list:
            s += f"{qs(i)}\n"

        s += "\n[images]\n"
        for i in self.image_list:
            s += f"{qs(i)}\n"

        return s

    def write_options(self, image_file_name):
        if self.write_opts:
            p = Path(image_file_name)

            file_name = str(Path('{0}_{1}'.format(
                p.with_suffix(''), 'options')
            ).with_suffix('.txt'))

            print(f"\nWriting options to '{file_name}'\n")
            with open(file_name, 'w') as f:
                f.write("# Created {0} by {1}\n".format(
                    datetime.now().strftime('%Y-%m-%d %H:%M'),
                    app_title
                ))

                f.write(self._options_as_str())

                if 0 < len(self._log):
                    f.write("\n\n[LOG]\n")
                    for i in self._log:
                        f.write(f"{i}\n")

    def check_options(self):
        errors = []

        if 0 < len(self.output_dir):
            if not Path(self.output_dir).exists():
                errors.append(
                    f"Output folder not found: '{self.output_dir}'."
                )

            if not Path(self.output_dir).is_dir():
                errors.append(
                    f"Output folder not a directory: '{self.output_dir}'."
                )

        for file_name in self.image_list:
            if not Path(file_name).exists():
                errors.append(
                    f"Image file not found: '{file_name}'."
                )

        for file_name in self.bg_image_list:
            if not Path(file_name).exists():
                errors.append(
                    f"Background image file not found: '{file_name}'."
                )

        if 0 < len(errors):
            print("\nCANNOT PROCEED")
            for message in errors:
                sys.stderr.write(f"{message}\n")
            sys.exit(1)

    def _load_from_file(self, file_name):
        if file_name is not None:
            p = Path(file_name).expanduser().resolve()
            if not p.exists():
                sys.stderr.write(f"ERROR: File not found: {file_name}")
                sys.exit(1)

            with open(p, 'r') as f:
                file_text = f.readlines()

            settings = get_option_entries('[settings]', file_text)

            warn_old_settings(settings)

            self.output_file_name = get_opt_str(None, 'output_file', settings)

            self.output_dir = get_opt_str(None, 'output_dir', settings)

            self.canvas_width = get_opt_int(None, 'canvas_width', settings)

            self.canvas_height = get_opt_int(None, 'canvas_height', settings)

            self.init_ncols = get_opt_int(None, 'columns', settings)

            self.init_nrows = get_opt_int(None, 'rows', settings)

            self.margin = get_opt_int(None, 'margin', settings)

            self.padding = get_opt_int(None, 'padding', settings)

            self.border_width = get_opt_int(None, 'border_width', settings)

            self.border_rgba = get_opt_str(None, 'border_rgba', settings)

            self.bg_rgba = get_opt_str(None, 'background_rgba', settings)

            self.bg_blur = get_opt_int(None, 'background_blur', settings)

            self.shuffle_mode = get_opt_str(None, 'shuffle_mode', settings)

            self.shuffle_count = get_opt_int(None, 'shuffle_count', settings)

            self.stamp_mode = get_opt_int(None, 'stamp_mode', settings)

            self.write_opts = get_opt_bool(None, 'write_opts', settings)

            self.feature1 = get_opt_feat(
                get_option_entries('[feature-1]', file_text), True
            )

            self.feature2 = get_opt_feat(
                get_option_entries('[feature-2]', file_text), True
            )

            self.image_list += [
                i.strip("'\"") for i in get_option_entries(
                    '[images]', file_text
                )
            ]

            self.bg_image_list += [
                i.strip("'\"") for i in get_option_entries(
                    '[background-images]', file_text
                )
            ]

    def _set_defaults(self, defaults):
        # -- Use defaults for options not already set.

        if self.output_file_name is None:
            self.output_file_name = defaults.file_name

        if self.output_dir is None:
            self.output_dir = ''

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
            self.border_rgba = get_rgba(
                defaults.border_rgba, self.border_rgba
            )

        if self.bg_rgba is None:
            self.bg_rgba = defaults.background_rgba
        elif type(self.bg_rgba) == str:
            self.bg_rgba = get_rgba(
                defaults.background_rgba, self.bg_rgba
            )

        if self.bg_blur is None:
            self.bg_blur = defaults.bg_blur

        if self.shuffle_mode is None:
            self.shuffle_mode = ''

        if self.shuffle_count is None:
            self.shuffle_count = 1

        if self.stamp_mode is None:
            self.stamp_mode = 0

        if self.write_opts is None:
            self.write_opts = False

        if self.feature1 is None:
            self.feature1 = get_opt_feat('', False)

        if self.feature2 is None:
            self.feature2 = get_opt_feat('', False)

    def load(self, args, defaults: MontageDefaults, settings_file=None):
        if args is None and settings_file is None:
            sys.stderr.write(
                "ERROR: No args object, and no settings file name.\n"
            )
            sys.exit(1)

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
                self.init_ncols = args.cols

            if args.rows is not None:
                self.init_nrows = args.rows

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

            if args.feature_1 is not None:
                self.feature1 = get_feature_args(args.feature_1)

            if args.feature_2 is not None:
                self.feature2 = get_feature_args(args.feature_2)

            self.image_list = [i for i in args.images] + self.image_list

        self._set_defaults(defaults)


def warn_old_settings(settings):
    old_settings = {
        'background_rgb': "Replaced by 'background_rgba'",
        'bg_alpha': "Replaced by 'background_rgba'",
        'bg_blur': "Replaced by 'background_blur'"
    }
    for line in settings:
        a = line.split('=', 1)
        if len(a) == 2:
            setting_name = a[0].strip()
            if setting_name in old_settings.keys():
                print(
                    "WARNING: Obsolete setting '{0}': {1}".format(
                        setting_name,
                        old_settings[setting_name]
                    )
                )


def get_arguments():
    ap = argparse.ArgumentParser(
        formatter_class=argparse.RawTextHelpFormatter,
        description='Create an image montage given a list of image files.'
    )

    ap.add_argument(
        'images',
        nargs='*',
        action='store',
        help='Images files to include in the montage image. '
        + 'Multiple files can be specified.'
    )

    ap.add_argument(
        '-o', '--output-file',
        dest='output_file',
        action='store',
        help='Name of output file.'
    )

    ap.add_argument(
        '-d', '--output-dir',
        dest='output_dir',
        action='store',
        help='Name of output directory.'
    )

    ap.add_argument(
        '-x', '--canvas-width',
        dest='canvas_width',
        type=int,
        action='store',
        help='Canvas width in pixels.'
    )

    ap.add_argument(
        '-y', '--canvas-height',
        dest='canvas_height',
        type=int,
        action='store',
        help='Canvas height in pixels.'
    )

    ap.add_argument(
        '-c', '--columns',
        dest='cols',
        type=int,
        action='store',
        help='Number of columns.'
    )

    ap.add_argument(
        '-r', '--rows',
        dest='rows',
        type=int,
        action='store',
        help='Number of rows.'
    )

    ap.add_argument(
        '-m', '--margin',
        dest='margin',
        type=int,
        action='store',
        help='Margin in pixels.'
    )

    ap.add_argument(
        '-p', '--padding',
        dest='padding',
        type=int,
        action='store',
        help='Padding in pixels.'
    )

    ap.add_argument(
        '-b', '--background-rgba',
        dest='bg_rgba_str',
        type=str,
        action='store',
        help='Background color as red,green,blue,alpha.'
    )

    ap.add_argument(
        '--border-width',
        dest='border_width',
        type=int,
        action='store',
        help='Border width in pixels.'
    )

    ap.add_argument(
        '--border-rgba',
        dest='border_rgba_str',
        type=str,
        action='store',
        help='Border color as red,green,blue,alpha.'
    )

    ap.add_argument(
        '-g', '--background-image',
        dest='bg_file',
        action='store',
        help='Name of image file to use as the background image.'
    )

    ap.add_argument(
        '--background-blur',
        dest='bg_blur',
        type=int,
        action='store',
        help='Blur radius for background image (0 = none).'
    )

    ap.add_argument(
        '--feature-1',
        dest='feature_1',
        type=str,
        action='store',
        help='Attributes for first featured image as '
        + '(col, ncols, row, nrows, file_name).'
    )

    ap.add_argument(
        '--feature-2',
        dest='feature_2',
        type=str,
        action='store',
        help='Attributes for second featured image as '
        + '(col, ncols, row, nrows, file_name).'
    )

    ap.add_argument(
        '--shuffle-mode',
        dest='shuffle_mode',
        type=str,
        action='store',
        help=textwrap.dedent('''\
            Flags that control shuffling (random order):
                i = images
                b = background image
                c = columns
                r = rows
                wc = weighted columns
                wr = weighted rows
                (weighted favors larger numbers)
            Example: --shuffle-mode=ibwc
        ''')
    )

    ap.add_argument(
        '--shuffle-count',
        dest='shuffle_count',
        type=int,
        action='store',
        help='Number of output files to create when using --shuffle-mode.'
    )

    ap.add_argument(
        '--stamp-mode',
        dest='stamp_mode',
        type=int,
        action='store',
        help=textwrap.dedent('''\
            Mode for adding a date_time stamp to the output file name:
                0 = none
                1 = at left of file name
                2 = at right of file name
                3 = at left of file name, include microseconds
                4 = at right of file name, include microseconds
            ''')
    )

    ap.add_argument(
        '-s', '--settings-file',
        dest='settings_file',
        action='store',
        help='Name of settings file.'
    )

    ap.add_argument(
        '--write-opts',
        dest='write_opts',
        action='store_true',
        help='Write the option settings to a file.'
    )

    # TODO: Add details to help messages.

    return ap.parse_args()


def get_option_entries(opt_section, opt_content):
    result = []
    in_section = False
    for line in opt_content:
        s = line.strip()
        if (0 < len(s)) and not s.startswith('#'):
            if in_section:
                # New section?
                if s.startswith('['):
                    in_section = False
                else:
                    result.append(s)
            if s == opt_section:
                in_section = True
    return result


def get_opt_str(default, opt_name, content):
    for opt in content:
        if opt.strip().startswith(opt_name):
            a = opt.split('=', 1)
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
    return s in ('t', 'y', '1')


def get_feature_args(feat_args):
    if feat_args is None:
        return FeatureImage(0, 0, 0, 0, '')

    a = feat_args.strip('()').split(',')

    if len(a) != 5:
        print(
            "WARNING: Ignoring invalid feature attributes. ",
            "Expected five values separated by commas."
        )
        return FeatureImage(0, 0, 0, 0, '')

    if any(not x.strip().isdigit() for x in a[:-1]):
        print(
            "WARNING: Ignoring invalid feature attributes. ",
            "Expected first four numeric values are numeric."
        )
        return FeatureImage(0, 0, 0, 0, '')

    fn = a[4].strip("\\'\" ")

    return FeatureImage(int(a[0]), int(a[1]), int(a[2]), int(a[3]), fn)


def get_opt_feat(section_content, default_to_none):
    col = get_opt_int(0, 'column', section_content)
    ncols = get_opt_int(0, 'num_columns', section_content)
    row = get_opt_int(0, 'row', section_content)
    nrows = get_opt_int(0, 'num_rows', section_content)
    file_name = get_opt_str('', 'file', section_content)
    if (ncols == 0) and default_to_none:
        return None
    else:
        return FeatureImage(col, ncols, row, nrows, file_name)


def qs(s: str) -> str:
    """ Returns the given string in quotes if it contains spaces. """

    if s is None:
        return ''

    assert '"' not in s
    #  TODO: Handle this case instead of just asserting? If so, are quotes
    #  doubled ("") or escaped (\")?

    if ' ' in s:
        return f'"{s}"'
    else:
        return s


def get_size_and_position(img_size, initial_placement: Placement, border=0):
    w = initial_placement.width
    h = initial_placement.height
    img_w = img_size[0]
    img_h = img_size[1]
    scale_w = (w - (border * 2)) / img_w
    scale_h = (h - (border * 2)) / img_h
    scale_factor = min(scale_w, scale_h)
    size_width = int(img_w * scale_factor)
    size_height = int(img_h * scale_factor)

    if size_width < w:
        add_x = int((w - size_width) / 2)
    else:
        add_x = 0

    if size_height < h:
        add_y = int((h - size_height) / 2)
    else:
        add_y = 0

    new_position = (
        initial_placement.left + add_x,
        initial_placement.top + add_y
    )
    return ((size_width, size_height), new_position)


def get_rgba(default, arg_str):
    if arg_str is None:
        return default

    a = arg_str.strip().split(',')

    if any(not x.isdigit() for x in a):
        print(
            "WARNING: Invalid backround color setting. ",
            "Expecting numeric values separated by commas. ",
            "Using default setting."
        )
        return default

    if any(int(x) < 0 or 255 < int(x) for x in a):
        print(
            "WARNING: Invalid backround color setting. ",
            "Expecting numeric values between 0 and 255. ",
            "Using default setting."
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
            "Using default."
        )
        return default


def place_feature(opts: MontageOptions, feat_attr, cell_size):
    if feat_attr.nrows and feat_attr.ncols:
        assert(0 < feat_attr.nrows)
        assert(0 < feat_attr.ncols)
        x = opts.margin + ((feat_attr.col - 1) * cell_size[0]) + opts.padding
        y = opts.margin + ((feat_attr.row - 1) * cell_size[1]) + opts.padding
        w = int((cell_size[0] * feat_attr.ncols) - (opts.padding * 2))
        h = int((cell_size[1] * feat_attr.nrows) - (opts.padding * 2))
        opts.add_placement(x, y, w, h, feat_attr.file_name)


def outside_feat(col_index, row_index, feat_attr):
    if feat_attr.nrows and feat_attr.ncols:
        a = (col_index + 1) in range(
            feat_attr.col,
            feat_attr.col + feat_attr.ncols
        )
        b = (row_index + 1) in range(
            feat_attr.row,
            feat_attr.row + feat_attr.nrows
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


def create_image(opts: MontageOptions, image_num: int):
    cell_w = int(
        (opts.canvas_width - (opts.margin * 2)) / opts.get_ncols()
    )
    cell_h = int(
        (opts.canvas_height - (opts.margin * 2)) / opts.get_nrows()
    )
    cell_size = (cell_w, cell_h)

    inner_w = int(cell_w - (opts.padding * 2))
    inner_h = int(cell_h - (opts.padding * 2))

    opts.log_say(f"Creating new image (canvas size = {opts.canvas_size()})")
    opts.log_add(f"cell_size={cell_size}")

    image = Image.new('RGB', opts.canvas_size(), opts.background_rgb())

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
                    bg_image.size,
                    opts.canvas_size()
                )
            )

        bg_image = bg_image.filter(ImageFilter.BoxBlur(opts.bg_blur))

        bg_mask = Image.new(
            'RGBA', bg_image.size, opts.background_mask_rgba()
        )

        image.paste(bg_image, (0, 0), mask=bg_mask)

    place_feature(opts, opts.feature1, cell_size)

    place_feature(opts, opts.feature2, cell_size)

    for row in range(0, opts.get_nrows()):
        for col in range(0, opts.get_ncols()):
            if outside_feature(col, row, opts.feature1, opts.feature2):
                x = (opts.margin + (col * cell_w) + opts.padding)
                y = (opts.margin + (row * cell_h) + opts.padding)
                opts.add_placement(x, y, inner_w, inner_h)

    i = 0
    for placement in opts.get_placements_list():
        if i < len(opts.image_list):

            if len(placement.file_name) == 0:
                image_name = opts.image_list[i]
                i += 1
            else:
                image_name = placement.file_name

            opts.log_say(f"Placing image '{image_name}'")

            img = Image.open(image_name)

            img = ImageOps.exif_transpose(img)

            new_size, new_pos = get_size_and_position(img.size, placement)

            opts.log_add(f"new_size='{new_size}")
            opts.log_add(f"new_pos='{new_pos}")

            if 0 < opts.border_width:
                border_image = Image.new('RGB', new_size, opts.border_rgb())
                border_mask = Image.new(
                    'RGBA',
                    border_image.size,
                    opts.border_mask_rgba()
                )
                image.paste(border_image, new_pos, mask=border_mask)
                new_size, new_pos = get_size_and_position(
                    img.size, placement, opts.border_width
                )

            img = img.resize(new_size)

            image.paste(img, new_pos)

    file_name = opts.image_file_name(image_num)

    # print(f"\nCreating image '{file_name}'")

    opts.log_say(f"Saving '{file_name}'")

    image.save(file_name)

    opts.write_options(file_name)


def create_montage(opts: MontageOptions):
    opts.check_options()
    n_images = opts.get_image_count()
    for i in range(0, n_images):
        opts.prepare()
        create_image(opts, i + 1)


def main():
    print(f"\n{app_title}\n")

    defaults = MontageDefaults()

    args = get_arguments()

    opts = MontageOptions()

    opts.load(args, defaults)

    create_montage(opts)

    print(f"\nDone ({app_title}).")


if __name__ == "__main__":
    main()
