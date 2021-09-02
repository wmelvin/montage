#!/usr/bin/env python3

from pathlib import Path
from PIL import Image


def make_image(canvas_size, bg_color, suffix=''):
    if (0 < len(suffix)) and (not suffix.startswith('-')):
        suffix = '-' + suffix
    file_name = 'gen-{0}x{1}{2}.jpg'.format(
        canvas_size[0], canvas_size[1], suffix
    )
    file_name = str(Path.cwd() / 'images_gen' / file_name)

    image = Image.new('RGB', canvas_size, bg_color)

    print(f"Saving '{file_name}'")

    image.save(file_name)


make_image((400, 400), (200, 100, 100), 'a')
make_image((400, 400), (100, 200, 100), 'b')
make_image((400, 400), (100, 100, 200), 'c')

# make_image((480, 640), (128, 50, 50), 'a')
# make_image((480, 640), (50, 128, 50), 'b')
# make_image((480, 640), (50, 50, 128), 'c')

make_image((480, 640), (128, 128, 50), 'a')
make_image((480, 640), (128, 50, 128), 'b')
make_image((480, 640), (50, 128, 128), 'c')

make_image((640, 240), (80, 0, 0), 'a')
make_image((640, 240), (0, 80, 0), 'b')
make_image((640, 240), (0, 0, 80), 'c')

make_image((640, 480), (128, 0, 0), 'a')
make_image((640, 480), (0, 128, 0), 'b')
make_image((640, 480), (0, 0, 128), 'c')

