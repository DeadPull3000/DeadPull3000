"""Render the November 2026 commit counts shown on the public profile."""

from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

COMMITS = (("TECH + DATA", 46), ("PROGRAMMING LAB", 24), ("THE WITCHES' ROAD", 7))
ASSETS = Path(__file__).resolve().parent
FONT = "C:/Windows/Fonts/consola.ttf"


def render(step):
    image = Image.new("RGB", (1056, 211), "#080f1b")
    draw = ImageDraw.Draw(image)
    heading = ImageFont.truetype(FONT, 25)
    mono = ImageFont.truetype(FONT, 16)
    draw.rounded_rectangle((12, 12, 1043, 198), radius=8, outline="#274c63")
    draw.line((32, 63, 1023, 63), fill="#274c63")
    draw.rectangle((33, 31, 41, 39), fill="#ed6e66")
    draw.text((55, 24), "NOVEMBER 2026 / COMMIT REPLAY", font=heading, fill="#dff7ff", anchor="lt")
    draw.text((1022, 29), "SNAPSHOT THROUGH NOV 23", font=mono, fill="#9dbdcf", anchor="rt")
    for index, (label, total) in enumerate(COMMITS):
        y = 83 + index * 38
        count = min(total, round(total * max(0.0, min(1.0, (step - index * 2) / 13))))
        draw.text((34, y), f"[0{index + 1}]  {label}", font=mono, fill="#9dbdcf", anchor="lt")
        draw.text((1022, y), f"{count:02d} COMMITS", font=mono, fill="#67eaff", anchor="rt")
        for position in range(46):
            x = 300 + position * 12
            color = "#67eaff" if position < count else "#19384b"
            draw.text((x, y), "#" if position < count else ":", font=mono, fill=color, anchor="lt")
    return image


if __name__ == "__main__":
    static = render(17)
    static.save(ASSETS / "commits-static.png", optimize=True)
    palette = static.quantize(colors=128)
    frames = [render(step).quantize(palette=palette, dither=Image.Dither.NONE) for step in range(17)]
    frames.append(palette)
    frames[0].save(ASSETS / "commits-replay.gif", save_all=True, append_images=frames[1:],
                   duration=[130] * 17 + [700], disposal=1, optimize=True)
