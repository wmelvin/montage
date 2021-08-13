#!/usr/bin/env python3

import argparse
from PIL import Image
from pathlib import Path


def get_scale_factor(pic_size, frame_size):
    w = frame_size[0] / pic_size[0]
    h = frame_size[1] / pic_size[1]
    return min(w, h)

def main():
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
        default = 'output.jpg',
        action = 'store',
        help = 'Name of output file.')

    args = ap.parse_args()

    #file_name = 'output.jpg'
    file_name = args.output_file

    canvas_width = 640
    canvas_height = 480
    canvas_size = (canvas_width, canvas_height)

    cols = 3
    rows = 3

    margin = 20

    frame_width = int((canvas_width / cols) - (margin + (margin / cols)))
    frame_height = int((canvas_height / rows) - (margin + (margin / rows)))
    frame_size = (frame_width, frame_height)

    bg_color = (0, 32, 0)  # (red, green, blue)

    pics = []

    # Same size.
    pics.append(Path.cwd() / 'images' / 'IM000481_resize_1024x768.JPG')
    pics.append(Path.cwd() / 'images' / 'IM000482_resize_1024x768.JPG')
    pics.append(Path.cwd() / 'images' / 'IM000483_resize_1024x768.JPG')
    pics.append(Path.cwd() / 'images' / 'IM000484_resize_1024x768.JPG')
    pics.append(Path.cwd() / 'images' / 'IM000488_resize_1024x768.JPG')

    # Different sizes.
    pics.append(Path.cwd() / 'images' / 'IM000481_resize_400x439.JPG')
    pics.append(Path.cwd() / 'images' / 'IM000481_resize_700x768.JPG')
    pics.append(Path.cwd() / 'images' / 'IM000484_resize_400x234.JPG')
    pics.append(Path.cwd() / 'images' / 'IM000484_resize_1024x600.JPG')

    image = Image.new('RGB', canvas_size, bg_color)

    frame_bg_color = (0, 64, 0)
    #frame_bg_color = bg_color

    pic_index = 0
    for y in range(0, rows):
        y_offset = int(margin + (y * frame_height) + (y * margin))
        for x in range(0, cols):
            x_offset = int(margin + (x * frame_width) + (x * margin))

            frame = Image.new('RGB', frame_size, frame_bg_color)

            if pic_index < len(pics):        
                pic = Image.open(pics[pic_index])
                pic_index += 1

                scale_factor = get_scale_factor(pic.size, frame_size)
                new_width = int(pic.width * scale_factor)
                new_height = int(pic.height * scale_factor)
                
                pic = pic.resize((new_width, new_height))

                if new_width < frame_width:
                    w = int((frame_width - new_width) / 2)
                else:
                    w = 0

                if new_height < frame_height:
                    h = int((frame_height - new_height) / 2)
                else:
                    h = 0
            
                frame.paste(pic, (w,h))

            image.paste(frame, (x_offset, y_offset))

    print(f"\nSaving {file_name}.")

    image.save(file_name)


if __name__ == "__main__":
    main()