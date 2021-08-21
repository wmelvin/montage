#!/usr/bin/env python3

import argparse
import random
from collections import namedtuple
from datetime import datetime
from PIL import Image, ImageFilter, ImageOps
from pathlib import Path

MAX_SHUFFLE_COUNT = 99

app_version = '20210821.1'

app_title = f'montage.py - version {app_version}'


FeatureImage = namedtuple(
    'FeatureImage', 'col, ncols, row, nrows, file_name'
)

Placement = namedtuple('Placement', 'left, top, width, height, file_name')


class AppOptions:
    def __init__(self):
        self.output_file_name = None
        self.canvas_width = None
        self.canvas_height = None
        self.init_ncols = None
        self.init_nrows = None
        self.rows = None
        self.cols = None
        self.margin = None
        self.padding = None
        self.bg_color = None
        self.feature1 = None
        self.feature2 = None
        self.image_list = []
        self.bg_image_list = []
        self.placements = []
        self.bg_alpha = None
        self.bg_blur = None
        self.shuffle_mode = None
        self.shuffle_count = None
        self.stamp_mode = 0
        self.write_opts = False
        self.dt_stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.output_dir = None
        self.border_width = None
        self.border_rgba = None

    def canvas_size(self):
        return (int(self.canvas_width), int(self.canvas_height))

    def add_placement(self, x, y, w, h, file_name=''):
        self.placements.append(Placement(x, y, w, h, file_name))

    def has_background_image(self):
        return 0 < len(self.bg_image_list)

    def get_bg_file_name(self):
        return self.bg_image_list[0]

    def background_mask_rgba(self):
        return (0, 0, 0, self.bg_alpha)

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
            a = [x for x in range(0, value + 1)]
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

    def prepare(self):
        self.placements.clear()
        self.set_cols_rows()
        self.shuffle_bg_images()
        self.shuffle_images()

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

        if self.stamp_mode == 1:
            #  Mode 1: date_time stamp at left of file name.
            p = Path('{0}_{1}'.format(
                self.dt_stamp,
                p.with_suffix(''))
            ).with_suffix(p.suffix)
        elif self.stamp_mode == 2:
            #  Mode 2: date_time stamp at right of file name.
            p = Path('{0}_{1}'.format(
                p.with_suffix(''),
                self.dt_stamp)
            ).with_suffix(p.suffix)

        return str(dir.joinpath(p))

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

                f.write("\n[settings]\n")
                f.write(f"output_file={qs(self.output_file_name)}\n")
                f.write(f"output_dir={qs(self.output_dir)}\n")
                f.write(f"canvas_width={self.canvas_width}\n")
                f.write(f"canvas_height={self.canvas_height}\n")
                f.write(f"columns={self.init_ncols}\n")
                f.write(f"rows={self.init_nrows}\n")
                f.write(f"margin={self.margin}\n")
                f.write(f"padding={self.padding}\n")

                f.write(f"border_width={self.border_width}\n")
                f.write("border_rgba={0},{1},{2},{3}\n".format(
                    self.border_rgba[0],
                    self.border_rgba[1],
                    self.border_rgba[2],
                    self.border_rgba[3]
                ))

                f.write("background_rgb={0},{1},{2}\n".format(
                    self.bg_color[0],
                    self.bg_color[1],
                    self.bg_color[2]
                ))

                f.write(f"bg_alpha={self.bg_alpha}\n")
                f.write(f"bg_blur={self.bg_blur}\n")
                f.write(f"shuffle_mode={self.shuffle_mode}\n")
                f.write(f"shuffle_count={self.shuffle_count}\n")
                f.write(f"stamp_mode={self.stamp_mode}\n")
                f.write(f"write_opts={self.write_opts}\n")

                f.write("\n[feature-1]\n")
                f.write(f"file={qs(self.feature1.file_name)}\n")
                f.write(f"column={self.feature1.col}\n")
                f.write(f"row={self.feature1.row}\n")
                f.write(f"num_columns={self.feature1.ncols}\n")
                f.write(f"num_rows={self.feature1.nrows}\n")

                f.write("\n[feature-2]\n")
                f.write(f"file={qs(self.feature2.file_name)}\n")
                f.write(f"column={self.feature2.col}\n")
                f.write(f"row={self.feature2.row}\n")
                f.write(f"num_columns={self.feature2.ncols}\n")
                f.write(f"num_rows={self.feature2.nrows}\n")

                f.write("\n[background-images]\n")
                for i in self.bg_image_list:
                    f.write(f"{qs(i)}\n")

                f.write("\n[images]\n")
                for i in self.image_list:
                    f.write(f"{qs(i)}\n")


def get_options(args):
    ao = AppOptions()

    if args.settings_file is None:
        file_text = ''
    else:
        p = Path(args.settings_file).expanduser().resolve()

        # TODO: Check exists, or just let an exception happen?
        # if not p.exists():
        #     print(f"ERROR: File not found: {args.settings_file}")
        #     return

        with open(p, 'r') as f:
            file_text = f.readlines()

    #  If file_text is empty, the defaults from args will be used.

    settings = get_option_entries('[settings]', file_text)

    ao.output_file_name = get_opt_str(
        args.output_file, 'output_file', settings
    )

    ao.output_dir = get_opt_str(
        args.output_dir, 'output_dir', settings
    )

    ao.canvas_width = get_opt_int(
        args.canvas_width, 'canvas_width', settings
    )

    ao.canvas_height = get_opt_int(
        args.canvas_height, 'canvas_height', settings
    )

    ao.init_ncols = get_opt_int(args.cols, 'columns', settings)

    ao.init_nrows = get_opt_int(args.rows, 'rows', settings)

    ao.margin = get_opt_int(args.margin, 'margin', settings)

    ao.padding = get_opt_int(args.padding, 'padding', settings)

    ao.border_width = get_opt_int(args.border_width, 'border_width', settings)

    s = get_opt_str(args.border_rgba_str, 'border_rgba', settings)
    ao.border_rgba = get_background_rgba((0, 0, 0, 255), s)

    s = get_opt_str(args.bg_color_str, 'background_rgb', settings)
    ao.bg_color = get_background_rgba((255, 255, 255), s)

    ao.bg_alpha = get_opt_int(args.bg_alpha, 'bg_alpha', settings)

    ao.bg_blur = get_opt_int(args.bg_blur, 'bg_blur', settings)

    ao.shuffle_mode = get_opt_str(
        args.shuffle_mode, 'shuffle_mode', settings
    )

    ao.shuffle_count = get_opt_int(
        args.shuffle_count, 'shuffle_count', settings
    )

    ao.stamp_mode = get_opt_int(args.stamp_mode, 'stamp_mode', settings)

    ao.write_opts = get_opt_bool(args.write_opts, 'write_opts', settings)

    ao.feature1 = get_feature_args(args.feature_1)
    if ao.feature1.ncols == 0:
        ao.feature1 = get_opt_feat(
            get_option_entries('[feature-1]', file_text)
        )

    ao.feature2 = get_feature_args(args.feature_2)
    if ao.feature2.ncols == 0:
        ao.feature2 = get_opt_feat(
            get_option_entries('[feature-2]', file_text)
        )

    ao.image_list = [i for i in args.images]

    ao.image_list += [
        i.strip("'\"") for i in get_option_entries(
            '[images]', file_text
        )
    ]

    ao.bg_image_list += [
        i.strip("'\"") for i in get_option_entries(
            '[background-images]', file_text
        )
    ]

    return ao


def get_arguments():
    default_canvas_width = 640
    default_canvas_height = 480
    default_margin = 10
    default_padding = 20
    default_bg_alpha = 64
    default_bg_blur = 3
    default_file_name = 'output.jpg'

    ap = argparse.ArgumentParser(
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
        default=default_file_name,
        action='store',
        help='Name of output file.'
    )

    ap.add_argument(
        '-d', '--output-dir',
        dest='output_dir',
        default='',
        action='store',
        help='Name of output directory.'
    )

    ap.add_argument(
        '-x', '--canvas-width',
        dest='canvas_width',
        type=int,
        default=default_canvas_width,
        action='store',
        help='Canvas width in pixels.'
    )

    ap.add_argument(
        '-y', '--canvas-height',
        dest='canvas_height',
        type=int,
        default=default_canvas_height,
        action='store',
        help='Canvas height in pixels.'
    )

    ap.add_argument(
        '-c', '--columns',
        dest='cols',
        type=int,
        default=2,
        action='store',
        help='Number of columns.'
    )

    ap.add_argument(
        '-r', '--rows',
        dest='rows',
        type=int,
        default=2,
        action='store',
        help='Number of rows.'
    )

    ap.add_argument(
        '-m', '--margin',
        dest='margin',
        type=int,
        default=default_margin,
        action='store',
        help='Margin in pixels.'
    )

    ap.add_argument(
        '-p', '--padding',
        dest='padding',
        type=int,
        default=default_padding,
        action='store',
        help='Padding in pixels.'
    )

    ap.add_argument(
        '-b', '--background-rgb',
        dest='bg_color_str',
        type=str,
        action='store',
        help='Background color as red,green,blue.'
    )

    ap.add_argument(
        '--border-width',
        dest='border_width',
        type=int,
        default=0,
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
        '--background-alpha',
        dest='bg_alpha',
        type=int,
        default=default_bg_alpha,
        action='store',
        help='Alpha (transparency) value for background image (0..255).'
    )

    ap.add_argument(
        '--background-blur',
        dest='bg_blur',
        type=int,
        default=default_bg_blur,
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
        default='',
        action='store',
        help='Flags that control shuffling (random order): i (images), '
        + 'b (background image), c (columns), r (rows), wc (weighted '
        + 'columns), wr (weighted rows). Example: --shuffle-mode=ibwc'
    )

    ap.add_argument(
        '--shuffle-count',
        dest='shuffle_count',
        type=int,
        default=1,
        action='store',
        help='Number of output files to create when using --shuffle-mode.'
    )

    ap.add_argument(
        '--stamp-mode',
        dest='stamp_mode',
        type=int,
        default=0,
        action='store',
        help='Mode for adding a date_time stamp to the output file name: '
        + '0 = none, 1 = at left of file name, 2 = at right of file name.'
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


def get_opt_feat(section_content):
    col = get_opt_int(0, 'column', section_content)
    ncols = get_opt_int(0, 'num_columns', section_content)
    row = get_opt_int(0, 'row', section_content)
    nrows = get_opt_int(0, 'num_rows', section_content)
    file_name = get_opt_str('', 'file', section_content)
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


def get_background_rgba(default, arg_str):
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
        rgb = (int(a[0]), int(a[1]), int(a[2]))
        return rgb
    elif len(a) == 4:
        rgba = (int(a[0]), int(a[1]), int(a[2]), int(a[3]))
        return rgba
    else:
        print(
            "WARNING: Invalid backround color setting. ",
            "Expecting numeric color values separated by commas",
            "('r,g,b' or 'r,g,b,a'). ",
            "Using default."
        )
        return default


def place_feature(opts: AppOptions, feat_attr, cell_size):
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
        x1 = int((cur_w - trg_w) / 2)
        x2 = cur_w - x1
    else:
        x1 = 0
        x2 = trg_w

    if trg_h < cur_h:
        y1 = int((cur_h - trg_h) / 2)
        y2 = cur_h - y1
    else:
        y1 = 0
        y2 = trg_h

    return (x1, y1, x2, y2)


def create_image(opts: AppOptions, image_num: int):
    cell_w = int(
        (opts.canvas_width - (opts.margin * 2)) / opts.get_ncols()
    )
    cell_h = int(
        (opts.canvas_height - (opts.margin * 2)) / opts.get_nrows()
    )
    cell_size = (cell_w, cell_h)

    inner_w = int(cell_w - (opts.padding * 2))
    inner_h = int(cell_h - (opts.padding * 2))

    image = Image.new('RGB', opts.canvas_size(), opts.bg_color)

    if opts.has_background_image():
        bg_image = Image.open(opts.get_bg_file_name())

        new_size = get_new_size_zoom(bg_image.size, opts.canvas_size())
        bg_image = bg_image.resize(new_size)

        crop_box = get_crop_box(bg_image.size, opts.canvas_size())
        bg_image = bg_image.crop(crop_box)

        if bg_image.size != opts.canvas_size():
            #  These should match. Warn when they do not.
            print(
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
    for placement in opts.placements:
        if i < len(opts.image_list):

            if len(placement.file_name) == 0:
                image_name = opts.image_list[i]
                i += 1
            else:
                image_name = placement.file_name

            img = Image.open(image_name)

            img = ImageOps.exif_transpose(img)

            new_size, new_pos = get_size_and_position(img.size, placement)

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

    print(f"\nCreating image '{file_name}'")

    image.save(file_name)

    opts.write_options(file_name)


def main():
    print(f"\n{app_title}\n")
    opts = get_options(get_arguments())
    n_images = opts.get_image_count()
    for i in range(0, n_images):
        opts.prepare()
        create_image(opts, i + 1)

    print(f"\nDone ({app_title}).")


if __name__ == "__main__":
    main()
