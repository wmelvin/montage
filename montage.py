#!/usr/bin/env python3

from PIL import Image
from pathlib import Path


def get_scale_factor(pic_size, frame_size):
    w = frame_size[0] / pic_size[0]
    h = frame_size[1] / pic_size[1]
    return max(w, h)    


file_name = 'output.jpg'

canvas_width = 640
canvas_height = 480
canvas_size = (canvas_width, canvas_height)

# 2 x 2 

margin = 20

frame_width = (canvas_width / 2) - (margin * 2)
frame_height = (canvas_height / 2) - (margin * 2)
frame_size = (frame_width, frame_height)

bg_color = (0, 32, 0)  # (red, green, blue)

pics = []
pics.append(Path.cwd() / 'images' / 'IM000481_resize_1024x768.JPG')
pics.append(Path.cwd() / 'images' / 'IM000482_resize_1024x768.JPG')
pics.append(Path.cwd() / 'images' / 'IM000483_resize_1024x768.JPG')
pics.append(Path.cwd() / 'images' / 'IM000484_resize_1024x768.JPG')
pics.append(Path.cwd() / 'images' / 'IM000488_resize_1024x768.JPG')

image = Image.new('RGB', canvas_size, bg_color)

pic = Image.open(pics[0])

# offset_w = 20
# offset_h = 20

scale_factor = get_scale_factor(pic.size, frame_size)

print(scale_factor)


new_width = int(pic.width * scale_factor)
new_height = int(pic.height * scale_factor)

pic = pic.resize((new_width, new_height))

pic_offset = (margin, margin)

image.paste(pic, pic_offset)

print(f"\nSaving {file_name}.")

image.save(file_name)
