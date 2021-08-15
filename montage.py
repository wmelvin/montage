#!/usr/bin/env python3

import argparse
from PIL import Image
from pathlib import Path


app_version = '20210814.1'

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

        #TODO: Temporary stub
        # self.feature_width = None
    
    def canvas_size(self):
        return (int(self.canvas_width), int(self.canvas_height))

    def add_placement(self, x, y, w, h):
        self.placements.append((x, y, w, h))
    

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
    ao.bg_color, ao.frame_bg_color = get_background_colors((0, 32, 0), args.bg_color_str)
    ao.padding = get_opt_int(args.padding, 'padding', settings)
    ao.out_file_name = get_opt_str(args.output_file, 'output_file', settings)
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
    #     '-f', '--feature-width',
    #     dest = 'feature_width',
    #     type = int,
    #     action = 'store',
    #     help = 'Featured image width.')

    ### For now, make the featured-image(s) feature only available via the options file.
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
        '-b', '--background-rgb',
        dest = 'bg_color_str',
        type=str, 
        action = 'store',
        help = 'Background color as red,green,blue. '
        + 'Also accepts r1,g1,b1,r2,g2,b2 where 2nd set is '
        + 'the background color for the innder frames.')

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


def get_options_from_file(file_name, args, image_list):
    p = Path(file_name).expanduser().resolve()
    if not p.exists():
        print(f"ERROR: File not found: {file_name}")
        return

    with open(p, 'r') as f:
        file_text = f.readlines()

    settings = get_option_entries('[settings]', file_text)

    args.canvas_width = get_opt_int(args.canvas_width, 'canvas_width', settings)
    args.canvas_height = get_opt_int(args.canvas_height, 'canvas_height', settings)
    args.cols = get_opt_int(args.cols, 'columns', settings)
    args.rows = get_opt_int(args.rows, 'rows', settings)
    args.margin = get_opt_int(args.margin, 'margin', settings)
    #args.feature_width = get_opt_int(args.feature_width, 'feature_width', settings)
    args.bg_color_str = get_opt_str(args.bg_color_str, 'background_rgb', settings)
    args.output_file = get_opt_str(args.output_file, 'output_file', settings)

    image_list += [x.strip("'\"") for x in get_option_entries('[images]', file_text)]


# def get_scale_factor(pic_size, frame_size):
#     w = frame_size[0] / pic_size[0]
#     h = frame_size[1] / pic_size[1]
#     return min(w, h)


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


# def scale_image(img, target_size):
#     scale_w = target_size[0] / img_size[0]
#     scale_h = target_size[1] / img_size[1]
#     scale_factor = min(scale_w, scale_h)




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
        x = (opts.margin + ((f_col - 1) * frame_size[0]))
        y = (opts.margin + ((f_row - 1) * frame_size[1]))
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

    #args = get_arguments()

    #pics = [pic for pic in args.images]

    opts = get_options(get_arguments())

    #print(opts.canvas_size())

    # if args.settings_file is not None:
    #     get_options_from_file(args.settings_file, args, pics)

    # (bg_color, frame_bg_color) = get_background_colors((0, 32, 0), args.bg_color_str)

    # canvas_size = (args.canvas_width, args.canvas_height)

    # if opts.feature_width is None:
    #     use_width = opts.canvas_width
    # else:
    #     assert(abs(opts.feature_width) < (opts.canvas_width + (opts.margin * 2)))
    #     use_width = opts.canvas_width - abs(opts.feature_width)

    # frame_width = int((use_width / opts.cols) - (opts.margin + (opts.margin / opts.cols)))
    # frame_height = int((opts.canvas_height / opts.rows) - (opts.margin + (opts.margin / opts.rows)))
    # frame_size = (frame_width, frame_height)

    frame_w = int((opts.canvas_width - (opts.margin * 2)) / opts.cols)
    frame_h = int((opts.canvas_height - (opts.margin * 2)) / opts.rows)
    frame_size = (frame_w, frame_h)

    inner_w = int(frame_w - (opts.padding * 2))
    inner_h = int(frame_h - (opts.padding * 2))
    inner_size = (inner_w, inner_h)

    image = Image.new('RGB', opts.canvas_size(), opts.bg_color)

    place_featured(opts, opts.featured1, frame_size)

    place_featured(opts, opts.featured2, frame_size)


    for row in range(0, opts.rows):
        for col in range(0, opts.cols):
            if outside_featured(col, row, opts.featured1, opts.featured2):
                x = (opts.margin + (col * frame_w) + opts.padding)
                y = (opts.margin + (row * frame_h) + opts.padding)
                #frame = Image.new('RGB', frame_size, frame_bg(col, row, 0))
                #inner = Image.new('RGB', inner_size, frame_bg(col, row, 1))
                #frame.paste(inner, (padding, padding))
                #image.paste(frame, (x, y))
                opts.add_placement(x, y, inner_w, inner_h)

    i = 0
    for p in opts.placements:
        if i < len(opts.image_list):
            img = Image.open(opts.image_list[i])
            i += 1
            new_size, new_placement =  get_size_and_placement(img.size, p)
            img = img.resize(new_size)            
            image.paste(img, new_placement)



    # pic_index = 0

    # if opts.feature_width is None:
    #     feature_offset = 0
    # else:
    #     feature_offset = abs(opts.feature_width)

    #     feature_width = int(abs(opts.feature_width) - opts.margin)
    #     feature_height = int(opts.canvas_height - (opts.margin * 2))
        
    #     feature_size = (feature_width, feature_height)
    #     frame = Image.new('RGB', feature_size, opts.frame_bg_color)
    #     if opts.feature_width > 0:
    #         pic = Image.open(opts.image_list[pic_index])
    #         pic_index += 1
    #         (new_size, placement) = get_size_and_placement(pic.size, feature_size)                
    #         pic = pic.resize(new_size)            
    #         frame.paste(pic, placement)

    #     image.paste(frame, (opts.margin, opts.margin))

    # for y in range(0, opts.rows):
    #     y_offset = int(opts.margin + (y * frame_height) + (y * opts.margin))
    #     for x in range(0, opts.cols):
    #         x_offset = int(feature_offset + opts.margin + (x * frame_width) + (x * opts.margin))

    #         frame = Image.new('RGB', frame_size, opts.frame_bg_color)

    #         if pic_index < len(opts.image_list):        
    #             pic = Image.open(opts.image_list[pic_index])
    #             pic_index += 1
    #             (new_size, placement) = get_size_and_placement(pic.size, frame_size)
    #             pic = pic.resize(new_size)
    #             frame.paste(pic, placement)

    #         image.paste(frame, (x_offset, y_offset))

    print(f"\nSaving '{opts.out_file_name}'.")

    image.save(opts.out_file_name)

    print(f"\nDone ({app_title}).")


if __name__ == "__main__":
    main()