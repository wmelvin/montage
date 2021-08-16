#!/usr/bin/env python3

import argparse
from os import name
import random
from collections import namedtuple
from datetime import date, datetime
from PIL import Image, ImageFilter
from pathlib import Path


app_version = '20210816.1'

app_title = f'montage.py - version {app_version}'


FeatureImage = namedtuple('FeatureImage', 'col, ncols, row, nrows, file_name')

Placement = namedtuple('Placement', 'left, top, width, height, file_name')

class AppOptions:
    def __init__(self):
        self.output_file_name = None
        self.canvas_width = None
        self.canvas_height = None
        self.cols = None
        self.rows = None
        self.margin = None
        self.padding = None
        self.bg_color = None
        self.feature1 = None
        self.feature2 = None
        self.image_list = []
        self.placements = []
        self.bg_file = None
        self.bg_alpha = None
        self.bg_blur = None
        self.shuffle = False
        self.stamp = False
        self.write_opts = False
        self.dt_stamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    def canvas_size(self):
        return (int(self.canvas_width), int(self.canvas_height))

    def add_placement(self, x, y, w, h, file_name=''):
        self.placements.append(Placement(x, y, w, h, file_name))

    def has_background_image(self):
        return (self.bg_file is not None) and (0 < len(self.bg_file))

    def background_mask_rgba(self):
        return (0, 0, 0, self.bg_alpha)

    def shuffle_images(self):
        random.shuffle(self.image_list)

    def image_file_name(self):
        p = Path(self.output_file_name)
        if self.stamp:
            p = Path('{0}_{1}'.format(p.with_suffix(''), self.dt_stamp)).with_suffix(p.suffix)
        return str(p)

    def write_options(self):
        if self.write_opts:
            p = Path(self.image_file_name())
            file_name = str(Path('{0}_{1}'.format(p.with_suffix(''), 'options')).with_suffix('.txt'))
            print(f"\nWriting options to '{file_name}'\n")
            with open(file_name, 'w') as f:
                f.write("\n[settings]\n")
                f.write(f"output_file='{self.output_file_name}'\n")
                f.write(f"canvas_width={self.canvas_width}\n")
                f.write(f"canvas_height={self.canvas_height}\n")
                f.write(f"columns={self.cols}\n")
                f.write(f"rows={self.rows}\n")
                f.write(f"margin={self.margin}\n")
                f.write(f"padding={self.padding}\n")
                f.write(f"background_rgb={self.bg_color[0]},{self.bg_color[1]},{self.bg_color[2]}\n")
                f.write(f"bg_file='{self.bg_file}'\n")
                f.write(f"bg_alpha={self.bg_alpha}\n")
                f.write(f"bg_blur={self.bg_blur}\n")
                f.write(f"shuffle={self.shuffle}\n")
                f.write(f"stamp={self.stamp}\n")

                if self.feature1.ncols:
                    f.write("\n[feature-1]\n")
                    f.write(f"file='{self.feature1.file_name}'\n")
                    f.write(f"column={self.feature1.col}\n")
                    f.write(f"row={self.feature1.row}\n")
                    f.write(f"num_columns={self.feature1.ncols}\n")
                    f.write(f"num_rows={self.feature1.nrows}\n")
                
                if self.feature2.ncols:
                    f.write("\n[feature-2]\n")
                    f.write(f"file='{self.feature2.file_name}'\n")
                    f.write(f"column={self.feature2.col}\n")
                    f.write(f"row={self.feature2.row}\n")
                    f.write(f"num_columns={self.feature2.ncols}\n")
                    f.write(f"num_rows={self.feature2.nrows}\n")

                f.write("\n[images]\n")
                for img in self.image_list:
                    f.write(f"'{img}'\n")


def get_options(args):
    ao = AppOptions()

    if args.settings_file is None:
        file_text = ''
    else:
        p = Path(args.settings_file).expanduser().resolve()

        #TODO: Check exists, or just let an exception happen?
        # if not p.exists():
        #     print(f"ERROR: File not found: {args.settings_file}")
        #     return

        with open(p, 'r') as f:
            file_text = f.readlines()


    #  If file_text is empty, the defaults from args will be used.

    settings = get_option_entries('[settings]', file_text)

    ao.output_file_name = get_opt_str(args.output_file, 'output_file', settings)
    ao.canvas_width = get_opt_int(args.canvas_width, 'canvas_width', settings)
    ao.canvas_height = get_opt_int(args.canvas_height, 'canvas_height', settings)
    ao.cols = get_opt_int(args.cols, 'columns', settings)
    ao.rows = get_opt_int(args.rows, 'rows', settings)
    ao.margin = get_opt_int(args.margin, 'margin', settings)
    ao.padding = get_opt_int(args.padding, 'padding', settings)

    s = get_opt_str(args.bg_color_str, 'background_rgb', settings)
    ao.bg_color = get_background_rgb((255, 255, 255), s)

    ao.bg_file = get_opt_str(args.bg_file, 'bg_file', settings)
    ao.bg_alpha = get_opt_int(args.bg_alpha, 'bg_alpha', settings)
    ao.bg_blur = get_opt_int(args.bg_blur, 'bg_blur', settings)

    ao.shuffle = get_opt_bool(args.shuffle, 'shuffle', settings)
    ao.stamp = get_opt_bool(args.stamp, 'stamp', settings)
    ao.write_opts = get_opt_bool(args.write_opts, 'write_opts', settings)
    
    ao.feature1 = get_feature_args(args.feature_1)
    if ao.feature1.ncols == 0:
        ao.feature1 = get_opt_feat(get_option_entries('[feature-1]', file_text))

    ao.feature2 = get_feature_args(args.feature_2)
    if ao.feature2.ncols == 0:
        ao.feature2 = get_opt_feat(get_option_entries('[feature-2]', file_text))
        
    ao.image_list = [i for i in args.images]

    ao.image_list += [i.strip("'\"") for i in get_option_entries('[images]', file_text)]

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
        description =
        'Create an image montage given a list of image files.')

    ap.add_argument(
        'images',
        nargs = '*',
        action = 'store',
        help = 'Images files to include in the montage image. Multiple files can be specified.')

    ap.add_argument(
        '-o', '--output-file',
        dest = 'output_file',
        default = default_file_name,
        action = 'store',
        help = 'Name of output file.')

    ap.add_argument(
        '-x', '--canvas-width',
        dest = 'canvas_width',
        type = int,
        default = default_canvas_width,
        action = 'store',
        help = 'Canvas width in pixels.')

    ap.add_argument(
        '-y', '--canvas-height',
        dest = 'canvas_height',
        type = int,
        default = default_canvas_height,
        action = 'store',
        help = 'Canvas height in pixels.')

    ap.add_argument(
        '-c', '--columns',
        dest = 'cols',
        type = int,
        default = 2,
        action = 'store',
        help = 'Number of columns.')

    ap.add_argument(
        '-r', '--rows',
        dest = 'rows',
        type = int,
        default = 2,
        action = 'store',
        help = 'Number of rows.')

    ap.add_argument(
        '-m', '--margin',
        dest = 'margin',
        type = int,
        default = default_margin,
        action = 'store',
        help = 'Margin in pixels.')

    ap.add_argument(
        '-p', '--padding',
        dest = 'padding',
        type = int,
        default = default_padding,
        action = 'store',
        help = 'Padding in pixels.')

    ap.add_argument(
        '-b', '--background-rgb',
        dest = 'bg_color_str',
        type=str,
        action = 'store',
        help = 'Background color as red,green,blue. '
        + 'Also accepts r1,g1,b1,r2,g2,b2 where 2nd set is '
        + 'the background color for the innder frames.')

    ap.add_argument(
        '-g', '--background-image',
        dest = 'bg_file',
        action = 'store',
        help = 'Name of image file to use as the background image.')

    ap.add_argument(
        '--background-alpha',
        dest = 'bg_alpha',
        type = int,
        default = default_bg_alpha,
        action = 'store',
        help = 'Alpha (transparency) value for background image (0..255).')

    ap.add_argument(
        '--background-blur',
        dest = 'bg_blur',
        type = int,
        default = default_bg_blur,
        action = 'store',
        help = 'Blur radius for background image (0 = none).')

    ap.add_argument(
        '--feature-1',
        dest = 'feature_1',
        type = str,
        action = 'store',
        help = 'Attributes for first featured image as (col, ncols, row, nrows, file_name).')

    ap.add_argument(
        '--feature-2',
        dest = 'feature_2',
        type = str,
        action = 'store',
        help = 'Attributes for second featured image as (col, ncols, row, nrows, file_name).')

    ap.add_argument(
        '--shuffle',
        dest = 'shuffle',
        action = 'store_true',
        help = 'Shuffle the list of images (random order).')

    ap.add_argument(
        '--stamp',
        dest = 'stamp',
        action = 'store_true',
        help = 'Add a date_time stamp to the output file name.')

    ap.add_argument(
        '-s', '--settings-file',
        dest = 'settings_file',
        action = 'store',
        help = 'Name of settings file.')

    ap.add_argument(
        '--write-opts',
        dest = 'write_opts',
        action = 'store_true',
        help = 'Write the option settings to a file.')

    #TODO: Add details to help messages.

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
                return a[1].strip("'\"")
    return default


def get_opt_int(default, opt_name, content):
    s = get_opt_str(None, opt_name, content)
    if s is None:
        return default
    else:
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
        print("WARNING: Ignoring invalid feature attributes. ",
            "Expected five values separated by commas."
        )
        return FeatureImage(0, 0, 0, 0, '')

    if any(not x.strip().isdigit() for x in a[:-1]):
        print("WARNING: Ignoring invalid feature attributes. ",
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


def get_size_and_position(img_size, initial_placement: Placement):
    scale_w = initial_placement.width / img_size[0]
    scale_h = initial_placement.height / img_size[1]
    scale_factor = min(scale_w, scale_h)
    size_width = int(img_size[0] * scale_factor)
    size_height = int(img_size[1] * scale_factor)
    if size_width < initial_placement.width:
        add_x = int((initial_placement.width - size_width) / 2)
    else:
        add_x = 0
    if size_height < initial_placement.height:
        add_y = int((initial_placement.height - size_height) / 2)
    else:
        add_y = 0
    new_position = (
        initial_placement.left + add_x,
        initial_placement.top + add_y
    )
    return ((size_width, size_height), new_position)


def get_background_rgb(default, arg_str):
    if arg_str is None:
        return default

    a = arg_str.strip().split(',')

    if any(not x.isdigit() for x in a):
        print("WARNING: Invalid backround color setting. ",
            "Expecting numeric values separated by commas. ",
            "Using default setting."
        )
        return default

    if any(int(x) < 0 or 255 < int(x) for x in a):
        print("WARNING: Invalid backround color setting. ",
            "Expecting numeric values between 0 and 255. ",
            "Using default setting."
        )
        return default

    if len(a) == 3:
        rgb = (int(a[0]), int(a[1]), int(a[2]))
        return rgb
    else:
        print("WARNING: Invalid backround color setting. ",
            "Expecting three numbers separated by commas. ",
            "Using default."
        )
        return default


def place_feature(opts: AppOptions, feat_attr, frame_size):
    if feat_attr.nrows and feat_attr.ncols:
        assert(0 < feat_attr.nrows)
        assert(0 < feat_attr.ncols)
        x = (opts.margin + ((feat_attr.col - 1) * frame_size[0]) + opts.padding)
        y = (opts.margin + ((feat_attr.row - 1) * frame_size[1]) + opts.padding)
        w = int((frame_size[0] * feat_attr.ncols) - (opts.padding * 2))
        h = int((frame_size[1] * feat_attr.nrows) - (opts.padding * 2))
        opts.add_placement(x, y, w, h, feat_attr.file_name)


def outside_feat(col_index, row_index, feat_attr):
    if feat_attr.nrows and feat_attr.ncols:
        a = (col_index + 1) in range(feat_attr.col, (feat_attr.col + feat_attr.ncols))
        b = (row_index + 1) in range(feat_attr.row, (feat_attr.row + feat_attr.nrows))
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


def main():
    print(f"\n{app_title}\n")

    opts = get_options(get_arguments())

    frame_w = int((opts.canvas_width - (opts.margin * 2)) / opts.cols)
    frame_h = int((opts.canvas_height - (opts.margin * 2)) / opts.rows)
    frame_size = (frame_w, frame_h)

    inner_w = int(frame_w - (opts.padding * 2))
    inner_h = int(frame_h - (opts.padding * 2))

    image = Image.new('RGB', opts.canvas_size(), opts.bg_color)

    if opts.has_background_image():
        bg_image = Image.open(opts.bg_file)

        new_size = get_new_size_zoom(bg_image.size, opts.canvas_size())
        bg_image = bg_image.resize(new_size)

        crop_box = get_crop_box(bg_image.size, opts.canvas_size())
        bg_image = bg_image.crop(crop_box)

        bg_image = bg_image.filter(ImageFilter.BoxBlur(opts.bg_blur))

        bg_mask = Image.new('RGBA', opts.canvas_size(), opts.background_mask_rgba())

        image.paste(bg_image, (0, 0), mask=bg_mask)

    place_feature(opts, opts.feature1, frame_size)

    place_feature(opts, opts.feature2, frame_size)

    if opts.shuffle:
        opts.shuffle_images()

    for row in range(0, opts.rows):
        for col in range(0, opts.cols):
            if outside_feature(col, row, opts.feature1, opts.feature2):
                x = (opts.margin + (col * frame_w) + opts.padding)
                y = (opts.margin + (row * frame_h) + opts.padding)
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
            new_size, new_position =  get_size_and_position(img.size, placement)
            img = img.resize(new_size)
            image.paste(img, new_position)

    print(f"\nCreating image '{opts.image_file_name()}'")

    image.save(opts.image_file_name())

    opts.write_options()

    print(f"\nDone ({app_title}).")


if __name__ == "__main__":
    main()
