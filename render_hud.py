"""Generate the original ASCII project HUD as a short GIF and a PNG."""

import argparse
import math
import os
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

WIDTH, HEIGHT = 1056, 380
SIZE = WIDTH, HEIGHT
CENTER = 785, 191
TAU = math.tau

INK = "#dff7ff"
CYAN = "#67eaff"
ICE = "#9dbdcf"
MUTED = "#5a8aa4"
LINE = "#274c63"
GRID = "#132a3b"
RED = "#ed6e66"
AMBER = "#f5ab66"

SIGNALS = (
    ("01", "AR_DUNGEON", "SPATIAL"),
    ("02", "MATH_ENGINE", "NUMERICAL"),
    ("03", "DOOMSDAY", "REALTIME"),
)
BOOT_STEPS = (0.00, 0.20, 0.45)
FRAMES = 34
STEP_MS = 110


def load_fonts(mono_path, display_path):
    return {
        "label": ImageFont.truetype(mono_path, 16),
        "small": ImageFont.truetype(mono_path, 13),
        "signal": ImageFont.truetype(mono_path, 18),
        "glyph": ImageFont.truetype(mono_path, 16),
        "name": ImageFont.truetype(display_path, 62),
        "handle": ImageFont.truetype(mono_path, 21),
    }


def polar(radius, angle):
    return tuple(
        round(center + radius * direction)
        for center, direction in zip(CENTER, (math.cos(angle), math.sin(angle)))
    )


def arc(draw, radius, start, end, fill, width=1):
    x, y = CENTER
    draw.arc((x - radius, y - radius, x + radius, y + radius), start, end, fill, width)


def stamp(draw, text, point, font, color, *, anchor="lt", tracking=0):
    if not tracking:
        draw.text(point, text, font=font, fill=color, anchor=anchor)
        return
    x, y = point
    for glyph in text:
        draw.text((x, y), glyph, font=font, fill=color, anchor=anchor)
        x += font.getlength(glyph) + tracking


def corner(draw, x, y, dx, dy):
    draw.line([(x, y + dy * 20), (x, y), (x + dx * 20, y)], fill=CYAN, width=2)


def crosshair(draw, x, y, fill, radius=5):
    draw.line((x - radius, y, x + radius, y), fill)
    draw.line((x, y - radius, x, y + radius), fill)


def make_base(fonts):
    image = Image.new("RGB", SIZE)
    pixels = image.load()
    for y in range(HEIGHT):
        for x in range(WIDTH):
            distance = math.hypot((x - CENTER[0]) / 405, (y - CENTER[1]) / 225)
            light = max(0.0, 1 - distance)
            pixels[x, y] = (5 + int(3 * light), 13 + int(13 * light), 23 + int(21 * light))

    draw = ImageDraw.Draw(image)
    for x in range(26, WIDTH - 21, 26):
        draw.line((x, 61, x, 329), fill=GRID if x >= 530 else "#0b1d2c")
    for y in range(62, 330, 19):
        draw.line((26, y, 1030, y), fill="#102536")

    draw.rounded_rectangle((12, 12, 1043, 367), radius=8, outline=LINE, width=1)
    for x, y, dx, dy in [(20, 20, 1, 1), (1035, 20, -1, 1), (20, 359, 1, -1), (1035, 359, -1, -1)]:
        corner(draw, x, y, dx, dy)
    draw.line((40, 55, 1016, 55), LINE)
    draw.line((40, 331, 1016, 331), LINE)
    draw.line((510, 69, 510, 316), LINE)
    draw.line((510, 70, 510, 105), fill=CYAN, width=2)
    draw.line((510, 281, 510, 316), fill=LINE, width=2)

    draw.rectangle((40, 30, 48, 39), fill=RED)
    stamp(draw, "PROJECT CONSOLE", (63, 29), fonts["label"], CYAN, tracking=2)
    stamp(draw, "PORTFOLIO / MARK 01", (1016, 29), fonts["label"], ICE, anchor="rt")
    stamp(draw, "OPERATOR", (40, 78), fonts["label"], CYAN, tracking=3)
    stamp(draw, "Vaishnavi Jha", (37, 102), fonts["name"], INK)
    stamp(draw, "@DeadPull3000", (40, 178), fonts["handle"], ICE)
    stamp(draw, "> load project_index", (40, 214), fonts["label"], CYAN)
    stamp(draw, "ASHOKA UNIVERSITY", (40, 344), fonts["label"], ICE)
    stamp(draw, "COMPUTER SCIENCE + MATHEMATICS", (1016, 344), fonts["label"], ICE, anchor="rt")

    x, y = CENTER
    draw.line((549, y, 1016, y), fill=LINE)
    draw.line((x, 64, x, 317), fill=LINE)
    for cross_x in (551, 1014):
        for cross_y in (73, 312):
            crosshair(draw, cross_x, cross_y, LINE)
    stamp(draw, "ASCII REACTOR", (559, 81), fonts["small"], ICE)
    stamp(draw, "SECTOR 01", (1004, 81), fonts["small"], ICE, anchor="rt")
    draw.line([(560, 291), (639, 291), (666, 264)], fill=LINE, width=1)
    draw.line([(899, 118), (928, 105), (1004, 105)], fill=LINE, width=1)
    for radius in (52, 80, 109, 127):
        arc(draw, radius, 0, 360, LINE)
    for start, end in [(10, 68), (97, 158), (185, 235), (262, 326)]:
        arc(draw, 119, start, end, "#397c97", 2)
    for start, end in [(20, 45), (146, 177), (244, 277), (311, 331)]:
        arc(draw, 101, start, end, "#2a617d", 2)
    for index in range(72):
        angle = index * TAU / 72
        major = index % 6 == 0
        draw.line(
            (polar(127, angle), polar(137 if major else 131, angle)),
            fill="#538ca0" if major else LINE,
        )
    for index, angle in enumerate((-2.82, -0.55, 0.86), start=1):
        marker_x, marker_y = polar(119, angle)
        draw.rectangle((marker_x - 3, marker_y - 3, marker_x + 3, marker_y + 3), fill=AMBER)
        label_x, label_y = polar(156, angle)
        stamp(draw, f"{index:02d}", (label_x, label_y), fonts["small"], AMBER, anchor="mm")
    return image


@lru_cache(maxsize=1)
def ascii_cells():
    """Map real printable ASCII characters onto concentric rings."""
    cells = []
    for row in range(-8, 9):
        for column in range(-12, 13):
            x, y = column * 9, row * 13
            radius = math.hypot(x, y)
            angle = math.atan2(y, x)
            sector = (angle % TAU) / TAU * 12
            if abs(radius - 93) < 5 and int(sector) % 3 != 2:
                glyph = ":+#"[(row + column) % 3]
            elif abs(radius - 71) < 5:
                glyph = "x+:"[(row - column) % 3]
            elif abs(radius - 43) < 4:
                glyph = "+"
            elif radius < 109 and (row * 19 + column * 23) % 11 == 0:
                glyph = "."
            else:
                continue
            cells.append((CENTER[0] + x, CENTER[1] + y, angle, glyph))
    return cells


def render_reactor(image, fonts, angle, settled):
    draw = ImageDraw.Draw(image)
    tail = 1.06
    if not settled:
        sweep = Image.new("RGBA", SIZE)
        sweep_draw = ImageDraw.Draw(sweep)
        for index in range(15):
            lead = angle - tail * index / 15
            trail = angle - tail * (index + 1) / 15
            points = [CENTER, polar(117, lead), polar(117, trail)]
            sweep_draw.polygon(points, fill=(57, 207, 248, 42 - index * 2))
        image.paste(sweep, (0, 0), sweep)
        draw.line((CENTER, polar(118, angle)), fill="#458aa5")
        draw.line((polar(110, angle), polar(128, angle)), fill=CYAN, width=2)
        arc(draw, 119, math.degrees(angle) - 40, math.degrees(angle), CYAN, 2)
    else:
        arc(draw, 119, 193, 231, CYAN, 2)
        arc(draw, 119, 24, 65, CYAN, 2)

    for x, y, cell_angle, glyph in ascii_cells():
        illuminated = (angle - cell_angle) % TAU < tail
        color = CYAN if illuminated else ("#467a92" if glyph != "." else "#30536d")
        if illuminated and glyph != ".":
            glyph = "+#@%"[ord(glyph) % 4]
        stamp(draw, glyph, (x, y), fonts["glyph"], color, anchor="mm")

    x, y = CENTER
    # The original insignia is composed entirely of printable ASCII.
    core = ("     /\\     ", "    /++\\    ", "   /+@@+\\   ", "  /+@@@@+\\  ", " /________\\ ")
    for row, line in enumerate(core):
        stamp(draw, line, (x, y - 25 + row * 12), fonts["glyph"], CYAN if row < 4 else INK, anchor="mm")
    stamp(draw, "<  CORE  >", (x, 306), fonts["label"], CYAN, anchor="mt")


def render_signals(draw, fonts, progress):
    for index, (number, name, category) in enumerate(SIGNALS):
        y = 244 + index * 23
        active = progress >= BOOT_STEPS[index]
        stamp(draw, f"[{number}]", (40, y), fonts["signal"], CYAN if active else MUTED)
        stamp(draw, name, (103, y), fonts["signal"], INK if active else MUTED)
        draw.line((259, y + 7, 319, y + 7), LINE)
        stamp(draw, category, (338, y), fonts["signal"], ICE if active else MUTED)
        draw.rectangle((463, y + 2, 470, y + 9), fill=AMBER if active else LINE)
    stamp(draw, "SIGNAL LOCK" if progress == 1 else "SCANNING", (1007, 292), fonts["small"], CYAN, anchor="rt")
    for index in range(9):
        x = 917 + index * 10
        draw.rectangle((x, 306, x + 6, 310), fill=CYAN if (index + 1) / 9 <= progress else LINE)


def draw_frame(base, fonts, index):
    settled = index == FRAMES - 1
    progress = index / (FRAMES - 1)
    angle = -TAU / 4 + progress * TAU * 1.08
    image = base.copy()
    render_reactor(image, fonts, angle, settled)
    render_signals(ImageDraw.Draw(image), fonts, progress)
    return image


def main():
    fonts_folder = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts"
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mono-font", type=Path, default=fonts_folder / "consola.ttf")
    parser.add_argument("--display-font", type=Path, default=fonts_folder / "bahnschrift.ttf")
    options = parser.parse_args()
    fonts = load_fonts(str(options.mono_font), str(options.display_font))

    assets = Path(__file__).resolve().parent
    assets.mkdir(exist_ok=True)
    base = make_base(fonts)
    frames = [draw_frame(base, fonts, index) for index in range(FRAMES)]
    frames[-1].save(assets / "hud-static.png", optimize=True)
    palette = frames[FRAMES // 2].quantize(colors=192)
    gif_frames = [frame.quantize(palette=palette, dither=Image.Dither.NONE) for frame in frames]
    # Omitting GIF loop metadata makes the sweep play once and hold its last frame.
    gif_frames[0].save(
        assets / "hud-boot.gif",
        save_all=True,
        append_images=gif_frames[1:],
        duration=[STEP_MS] * (FRAMES - 1) + [800],
        disposal=1,
        optimize=True,
    )


if __name__ == "__main__":
    main()
