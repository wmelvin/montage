#!/usr/bin/env python3

import argparse
from PIL import Image
from pathlib import Path


app_version = '20210813.1'

app_title = f'montage.py - version {app_version}'


def get_arguments():
    default_canvas_width = 640
    default_canvas_height = 480
    default_margin = 20
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

    ap.add_argument(
        '-f', '--feature-width',
        dest = 'feature_width',
        type = int,
        action = 'store',
        help = 'Featured image width.')

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
        if len(s) == 0:
            in_section = False
        else:
            if in_section:
                # Handle new section w/o blank lines between.
                if s.startswith('['):
                    in_section = False
                # Support whole-line comments identified by '#' (ignore them).
                elif not s.startswith('#'):
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
    args.feature_width = get_opt_int(args.feature_width, 'feature_width', settings)
    args.bg_color_str = get_opt_str(args.bg_color_str, 'background_rgb', settings)
    args.output_file = get_opt_str(args.output_file, 'output_file', settings)

    image_list += [x.strip("'\"") for x in get_option_entries('[images]', file_text)]


def get_scale_factor(pic_size, frame_size):
    w = frame_size[0] / pic_size[0]
    h = frame_size[1] / pic_size[1]
    return min(w, h)


def get_size_and_placement(pic_size, target_size):
    scale_factor = get_scale_factor(pic_size, target_size)
    size_width = int(pic_size[0] * scale_factor)
    size_height = int(pic_size[1] * scale_factor)
    if size_width < target_size[0]:
        place_x = int((target_size[0] - size_width) / 2)
    else:
        place_x = 0
    if size_height < target_size[1]:
        place_y = int((target_size[1] - size_height) / 2)
    else:
        place_y = 0    
    return ((size_width, size_height), (place_x, place_y))


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


def main():
    print(f"\n{app_title}")

    args = get_arguments()

    pics = [pic for pic in args.images]

    if args.settings_file is not None:
        get_options_from_file(args.settings_file, args, pics)

    (bg_color, frame_bg_color) = get_background_colors((0, 32, 0), args.bg_color_str)

    file_name = args.output_file

    canvas_size = (args.canvas_width, args.canvas_height)

    if args.feature_width is None:
        use_width = args.canvas_width
    else:
        assert(abs(args.feature_width) < (args.canvas_width + (args.margin * 2)))
        use_width = args.canvas_width - abs(args.feature_width)

    frame_width = int((use_width / args.cols) - (args.margin + (args.margin / args.cols)))
    frame_height = int((args.canvas_height / args.rows) - (args.margin + (args.margin / args.rows)))
    frame_size = (frame_width, frame_height)

    image = Image.new('RGB', canvas_size, bg_color)

    pic_index = 0

    if args.feature_width is None:
        feature_offset = 0
    else:
        feature_offset = args.feature_width

        feature_width = int(abs(args.feature_width) - args.margin)
        feature_height = int(args.canvas_height - (args.margin * 2))
        
        feature_size = (feature_width, feature_height)
        frame = Image.new('RGB', feature_size, frame_bg_color)
        if args.feature_width > 0:
            pic = Image.open(pics[pic_index])
            pic_index += 1
            (new_size, placement) = get_size_and_placement(pic.size, feature_size)                
            pic = pic.resize(new_size)            
            frame.paste(pic, placement)

        image.paste(frame, (args.margin, args.margin))

    for y in range(0, args.rows):
        y_offset = int(args.margin + (y * frame_height) + (y * args.margin))
        for x in range(0, args.cols):
            x_offset = int(feature_offset + args.margin + (x * frame_width) + (x * args.margin))

            frame = Image.new('RGB', frame_size, frame_bg_color)

            if pic_index < len(pics):        
                pic = Image.open(pics[pic_index])
                pic_index += 1
                (new_size, placement) = get_size_and_placement(pic.size, frame_size)
                pic = pic.resize(new_size)
                frame.paste(pic, placement)

            image.paste(frame, (x_offset, y_offset))

    print(f"\nSaving '{file_name}'.")

    image.save(file_name)

    print(f"\nDone ({app_title}).")


if __name__ == "__main__":
    main()