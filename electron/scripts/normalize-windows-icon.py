from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image


TARGET_SIZES = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (24, 24), (20, 20), (16, 16)]


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit('Usage: normalize-windows-icon.py <icon-path>')

    icon_path = Path(sys.argv[1]).resolve()
    if not icon_path.is_file():
        raise SystemExit(f'Icon file not found: {icon_path}')

    with Image.open(icon_path) as image:
        rgba_image = image.convert('RGBA')
        max_edge = max(rgba_image.size)
        canvas_size = max(256, max_edge)

        if rgba_image.size != (canvas_size, canvas_size):
            padded = Image.new('RGBA', (canvas_size, canvas_size), (0, 0, 0, 0))
            offset = ((canvas_size - rgba_image.width) // 2, (canvas_size - rgba_image.height) // 2)
            padded.paste(rgba_image, offset)
            rgba_image = padded

        rgba_image.save(icon_path, format='ICO', sizes=TARGET_SIZES)

    return 0


if __name__ == '__main__':
    raise SystemExit(main())
