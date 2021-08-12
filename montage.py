#!/usr/bin/env python3

from PIL import Image

file_name = 'output.jpg'

canvas_width = 640
canvas_height = 480
canvas_size = (canvas_width, canvas_height)

bg_color = (0, 64, 0)  # (red, green, blue)

image = Image.new('RGB', canvas_size, bg_color)

print(f"\nSaving {file_name}.")

image.save(file_name)
