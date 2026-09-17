"""Build the transparent animated house used by the dashboard 3D link."""

from __future__ import annotations

import math
import sys
from collections import deque
from pathlib import Path

from PIL import Image, ImageOps


def remove_connected_neutral_background(source: Image.Image) -> Image.Image:
    image = source.convert("RGBA")
    pixels = image.load()
    width, height = image.size
    background = bytearray(width * height)
    queue: deque[tuple[int, int]] = deque()

    def is_background(x: int, y: int) -> bool:
        red, green, blue, _ = pixels[x, y]
        return max(red, green, blue) - min(red, green, blue) <= 10

    for x in range(width):
        queue.extend(((x, 0), (x, height - 1)))
    for y in range(height):
        queue.extend(((0, y), (width - 1, y)))

    while queue:
        x, y = queue.popleft()
        index = y * width + x
        if background[index] or not is_background(x, y):
            continue
        background[index] = 1
        if x:
            queue.append((x - 1, y))
        if x + 1 < width:
            queue.append((x + 1, y))
        if y:
            queue.append((x, y - 1))
        if y + 1 < height:
            queue.append((x, y + 1))

    for y in range(height):
        for x in range(width):
            if background[y * width + x]:
                red, green, blue, _ = pixels[x, y]
                pixels[x, y] = (red, green, blue, 0)
    return image


def build(source_path: Path, destination: Path) -> None:
    house = remove_connected_neutral_background(Image.open(source_path))
    bounds = house.getbbox()
    if not bounds:
        raise ValueError("The source image does not contain a visible house")
    house = house.crop(bounds)
    house.thumbnail((156, 156), Image.Resampling.LANCZOS)

    frames: list[Image.Image] = []
    for index in range(24):
        angle = 2 * math.pi * index / 24
        cosine = math.cos(angle)
        frame_source = house if cosine >= 0 else ImageOps.mirror(house)
        width = max(28, round(house.width * (0.28 + 0.72 * abs(cosine))))
        turned = frame_source.resize((width, house.height), Image.Resampling.LANCZOS)
        frame = Image.new("RGBA", (180, 180), (0, 0, 0, 0))
        frame.alpha_composite(
            turned,
            ((frame.width - turned.width) // 2, (frame.height - turned.height) // 2),
        )
        frames.append(frame)

    destination.parent.mkdir(parents=True, exist_ok=True)
    frames[0].save(
        destination,
        save_all=True,
        append_images=frames[1:],
        duration=70,
        loop=0,
        disposal=2,
        transparency=0,
        optimize=True,
    )


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("usage: build_dashboard_house_gif.py SOURCE DESTINATION")
    build(Path(sys.argv[1]), Path(sys.argv[2]))
