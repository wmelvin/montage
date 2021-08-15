#!/usr/bin/env python3

import argparse
from PIL import Image, ImageFilter
from pathlib import Path


app_version = '20210815.1'

app_title = f'montage.py - version {app_version}'


class AppOptions:
    def __init__(self):
        self.out_file_name = None
        self.canvas_width = None
        self.canvas_height = None
        self.cols = None
        self.rows = None
        self.margin = None
        self.padding = None
        self.bg_color = None
        self.frame_bg_color = None
        self.featured1 = None
        self.featured2 = None
        self.image_list = []
        self.placements = []
        self.bg_file = None
        self.bg_alpha = None
        self.bg_blur = None
    
    def canvas_size(self):
        return (int(self.canvas_width), int(self.canvas_height))

    def add_placement(self, x, y, w, h):
        self.placements.append((x, y, w, h))

    def has_background_image(self):
        return (self.bg_file is not None) and (0 < len(self.bg_file))

    def background_mask_rgba(self):
        return (0, 0, 0, self.bg_alpha)
    

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

    ao.canvas_width = get_opt_int(args.canvas_width, 'canvas_width', settings)
    ao.canvas_height = get_opt_int(args.canvas_height, 'canvas_height', settings)
    ao.cols = get_opt_int(args.cols, 'columns', settings)
    ao.rows = get_opt_int(args.rows, 'rows', settings)
    ao.margin = get_opt_int(args.margin, 'margin', settings)
    ao.padding = get_opt_int(args.padding, 'padding', settings)
    ao.out_file_name = get_opt_str(args.output_file, 'output_file', settings)
    ao.bg_color, ao.frame_bg_color = get_background_colors((0, 32, 0), args.bg_color_str)
    ao.bg_file = get_opt_str(args.bg_file, 'bg_file', settings)
    ao.bg_alpha = get_opt_int(args.bg_alpha, 'bg_alpha', settings)
    ao.bg_blur = get_opt_int(args.bg_blur, 'bg_blur', settings)
    
    ao.featured1 = get_opt_feat(get_option_entries('[featured-1]', file_text))
    ao.featured2 = get_opt_feat(get_option_entries('[featured-2]', file_text))
    
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
        '-o', '--output-file',
        dest = 'output_file',
        default = default_file_name,
        action = 'store',
        help = 'Name of output file.')

    # ap.add_argument(
    #     '-f', '--featured-1',
    #     dest = 'feat_1',
    #     type = str,
    #     action = 'store',
    #     help = 'Attributes for first featured image as (col, ncols, row, nrows).')

    # ap.add_argument(
    #     '-F', '--featured-2',
    #     dest = 'feat_1',
    #     type = str,
    #     action = 'store',
    #     help = 'Attributes for second featured image as (col, ncols, row, nrows).')

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
        '-s', '--settings-file',
        dest = 'settings_file',
        action = 'store',
        help = 'Name of settings file.')

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


def get_opt_feat(section_content):
    col = get_opt_int(0, 'column', section_content)
    ncols = get_opt_int(0, 'num_columns', section_content)
    row = get_opt_int(0, 'row', section_content)
    nrows = get_opt_int(0, 'num_rows', section_content)    
    return (col, ncols, row, nrows)


def get_size_and_placement(img_size, initial_placement):
    scale_w = initial_placement[2] / img_size[0]
    scale_h = initial_placement[3] / img_size[1]
    scale_factor = min(scale_w, scale_h)
    size_width = int(img_size[0] * scale_factor)
    size_height = int(img_size[1] * scale_factor)
    if size_width < initial_placement[2]:
        add_x = int((initial_placement[2] - size_width) / 2)
    else:
        add_x = 0
    if size_height < initial_placement[3]:
        add_y = int((initial_placement[3] - size_height) / 2)
    else:
        add_y = 0
    new_placement = (
        initial_placement[0] + add_x, 
        initial_placement[1] + add_y
    )
    return ((size_width, size_height), new_placement)


def get_background_colors(default, arg_str):
    if arg_str is None:
        return (default, default)

    a = arg_str.strip().split(',')

    if any(not x.isdigit() for x in a):
        print("WARNING: Invalid backround color setting. ",
            "Expecting numeric values separated by commas. ",
            "Using default setting."
        )
        return (default, default)

    if len(a) == 3:
        rgb = (int(a[0]), int(a[1]), int(a[2]))
        return (rgb, rgb)
    elif len(a) == 6:
        rgb1 = (int(a[0]), int(a[1]), int(a[2]))
        rgb2 = (int(a[3]), int(a[4]), int(a[5]))
        return (rgb1, rgb2)
    else:
        print("WARNING: Invalid backround color setting. ", 
            "Expecting three (or six) numbers separated by commas. ", 
            "Using default."
        )
        return (default, default)


def place_featured(opts: AppOptions, feat_attr, frame_size):
    f_col, f_ncols, f_row, f_nrows = feat_attr

    if f_nrows and f_ncols:
        assert(0 < f_nrows)
        assert(0 < f_ncols)
        x = (opts.margin + ((f_col - 1) * frame_size[0]) + opts.padding)
        y = (opts.margin + ((f_row - 1) * frame_size[1]) + opts.padding)
        w = int((frame_size[0] * f_ncols) - (opts.padding * 2))
        h = int((frame_size[1] * f_nrows) - (opts.padding * 2))
        opts.add_placement(x, y, w, h)


def outside_feat(col_index, row_index, feat_attr):
    f_col, f_ncols, f_row, f_nrows = feat_attr
    if f_nrows and f_ncols:
        a = (col_index + 1) in range(f_col, (f_col + f_ncols))
        b = (row_index + 1) in range(f_row, (f_row + f_nrows))
        return not (a and b)
    return True


def outside_featured(col_index, row_index, feat_1, feat_2):
    a = outside_feat(col_index, row_index, feat_1)
    b = outside_feat(col_index, row_index, feat_2)
    return a and b


def main():
    print(f"\n{app_title}")

    opts = get_options(get_arguments())

    frame_w = int((opts.canvas_width - (opts.margin * 2)) / opts.cols)
    frame_h = int((opts.canvas_height - (opts.margin * 2)) / opts.rows)
    frame_size = (frame_w, frame_h)

    inner_w = int(frame_w - (opts.padding * 2))
    inner_h = int(frame_h - (opts.padding * 2))
    # inner_size = (inner_w, inner_h)

    image = Image.new('RGB', opts.canvas_size(), opts.bg_color)

    if opts.has_background_image():
        bg_image = Image.open(opts.bg_file)
        bg_image = bg_image.resize(opts.canvas_size())
        bg_image = bg_image.filter(ImageFilter.BoxBlur(opts.bg_blur))
        bg_mask = Image.new('RGBA', opts.canvas_size(), opts.background_mask_rgba())
        image.paste(bg_image, (0, 0), mask=bg_mask)

    place_featured(opts, opts.featured1, frame_size)

    place_featured(opts, opts.featured2, frame_size)

    for row in range(0, opts.rows):
        for col in range(0, opts.cols):
            if outside_featured(col, row, opts.featured1, opts.featured2):
                x = (opts.margin + (col * frame_w) + opts.padding)
                y = (opts.margin + (row * frame_h) + opts.padding)
                opts.add_placement(x, y, inner_w, inner_h)

    i = 0
    for p in opts.placements:
        if i < len(opts.image_list):
            img = Image.open(opts.image_list[i])
            i += 1
            new_size, new_placement =  get_size_and_placement(img.size, p)
            img = img.resize(new_size)            
            image.paste(img, new_placement)

    print(f"\nSaving '{opts.out_file_name}'.")

    image.save(opts.out_file_name)

    print(f"\nDone ({app_title}).")


if __name__ == "__main__":
    main()
