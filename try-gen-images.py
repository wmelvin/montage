#!/usr/bin/env python3

from pathlib import Path
from PIL import Image, ImageDraw, ImageFont


def make_image(canvas_size, bg_color, suffix=''):
    if (0 < len(suffix)) and (not suffix.startswith('-')):
        suffix = '-' + suffix
    file_name = 'gen-{0}x{1}{2}.jpg'.format(
        canvas_size[0], canvas_size[1], suffix
    )
    file_path = Path.cwd() / 'images_gen' / file_name

    image = Image.new('RGB', canvas_size, bg_color)

    font = ImageFont.truetype('LiberationMono-Regular.ttf', size=24)

    draw = ImageDraw.Draw(image)

    draw.text((10, 10), file_name, font=font, fill=(255, 255, 255, 255))

    print(f"Saving '{file_path}'")

    image.save(file_path)


make_image((400, 400), (200, 100, 100), 'A')
make_image((400, 400), (100, 200, 100), 'B')
make_image((400, 400), (100, 100, 200), 'C')

make_image((480, 640), (128, 128, 50), 'D')
make_image((480, 640), (128, 50, 128), 'E')
make_image((480, 640), (50, 128, 128), 'F')

make_image((640, 240), (80, 0, 0), 'G')
make_image((640, 240), (0, 80, 0), 'H')
make_image((640, 240), (0, 0, 80), 'I')

make_image((640, 480), (128, 0, 0), 'J')
make_image((640, 480), (0, 128, 0), 'K')
make_image((640, 480), (0, 0, 128), 'L')
