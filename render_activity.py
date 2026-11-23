"""Render a read-only snapshot of the activity visible on a GitHub profile."""

import argparse
from datetime import date, timedelta
from html.parser import HTMLParser
import json
from pathlib import Path
import re
from urllib.request import Request, urlopen

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "contributions.json"
ASSETS = ROOT
SIZE = (1056, 253)
LEVELS = ("#122838", "#185e78", "#207c9e", "#30bad5", "#77edff")
GLYPHS = (".", "+", "x", "#", "@")


class CalendarParser(HTMLParser):
    """Pair date cells with GitHub's visible contribution tooltips."""

    def __init__(self):
        super().__init__()
        self.dates = {}
        self.tooltips = {}
        self.current = None

    def handle_starttag(self, tag, pairs):
        attrs = dict(pairs)
        if tag == "td" and "ContributionCalendar-day" in attrs.get("class", "").split():
            if "id" in attrs and "data-date" in attrs:
                self.dates[attrs["id"]] = attrs["data-date"]
        if tag == "tool-tip" and attrs.get("for"):
            self.current = attrs["for"]
            self.tooltips[self.current] = []

    def handle_endtag(self, tag):
        if tag == "tool-tip":
            self.current = None

    def handle_data(self, text):
        if self.current is not None:
            self.tooltips[self.current].append(text)


def validate(snapshot):
    start, end = (date.fromisoformat(snapshot[key]) for key in ("start", "end"))
    counts = snapshot["counts"]
    if not 350 <= len(counts) <= 371 or (end - start).days + 1 != len(counts):
        raise ValueError("Expected a contiguous annual GitHub contribution calendar")
    if any(type(value) is not int or value < 0 for value in counts):
        raise ValueError("Invalid GitHub contribution count")
    return start, end, counts


def fetch_public_calendar(handle):
    if not re.fullmatch(r"[A-Za-z0-9-]{1,39}", handle):
        raise ValueError("Invalid GitHub username")
    request = Request(
        f"https://github.com/users/{handle}/contributions",
        headers={"Accept-Language": "en", "User-Agent": "GitHub profile HUD"},
    )
    with urlopen(request, timeout=25) as response:
        document = response.read(2_000_000).decode("utf-8")
    parser = CalendarParser()
    parser.feed(document)
    days = {}
    for cell_id, day in parser.dates.items():
        label = "".join(parser.tooltips.get(cell_id, ())).strip()
        match = re.match(r"^(No|[0-9,]+) contributions? on ", label)
        if not match or day in days:
            raise ValueError("GitHub changed the contribution calendar markup")
        value = match[1]
        days[day] = 0 if value == "No" else int(value.replace(",", ""))
    ordered = sorted(days)
    if not ordered:
        raise ValueError("GitHub returned no contribution calendar")
    snapshot = {"start": ordered[0], "end": ordered[-1], "counts": [days[day] for day in ordered]}
    validate(snapshot)
    if (date.today() - date.fromisoformat(snapshot["end"])).days > 3:
        raise ValueError("GitHub returned an out-of-date contribution calendar")
    return snapshot


def render(snapshot, font_path):
    start, end, counts = validate(snapshot)
    font = ImageFont.truetype(font_path, 16)
    small = ImageFont.truetype(font_path, 13)
    title = ImageFont.truetype(font_path, 26)
    offset = (start.weekday() + 1) % 7
    week_count = (len(counts) + offset + 6) // 7
    weeks = [divmod(index + offset, 7) for index in range(len(counts))]
    origin_x, origin_y, step = 81, 94, 17
    background = Image.new("RGB", SIZE, "#080f1b")
    draw = ImageDraw.Draw(background)
    draw.rounded_rectangle((12, 12, 1043, 240), radius=8, outline="#274c63")
    draw.line((32, 63, 1023, 63), fill="#274c63")
    draw.rectangle((33, 32, 41, 40), fill="#ed6e66")
    draw.text((55, 24), "CONTRIBUTION TELEMETRY", font=title, fill="#dff7ff", anchor="lt")
    draw.text((1022, 29), f"{sum(counts):,} CONTRIBUTIONS", font=font, fill="#67eaff", anchor="rt")
    for index, letter in ((1, "M"), (3, "W"), (5, "F")):
        draw.text((48, origin_y + index * step + 6), letter, font=small, fill="#9dbdcf", anchor="mm")
    last_month = None
    for index, (week, _) in enumerate(weeks):
        day = start + timedelta(days=index)
        if last_month != day.month:
            if week < week_count - 2 and (index != 0 or day.day <= 14):
                draw.text((origin_x + week * step, 74), day.strftime("%b").upper(), font=small, fill="#9dbdcf", anchor="lt")
            last_month = day.month
    draw.text((34, 224), f"{start:%d %b %Y}  -  {end:%d %b %Y} UTC".upper(), font=small, fill="#9dbdcf", anchor="lm")
    draw.text((1022, 224), "LESS  . + x # @  MORE", font=small, fill="#9dbdcf", anchor="rm")

    def frame(scan):
        image = background.copy()
        canvas = ImageDraw.Draw(image)
        if scan is not None:
            x = origin_x + scan * step + 6
            canvas.line((x, 92, x, 207), fill="#264e64")
        for count, (week, day) in zip(counts, weeks):
            x, y = origin_x + week * step, origin_y + day * step
            level = 0 if count == 0 else min(4, 1 + (count >= 3) + (count >= 8) + (count >= 16))
            color = LEVELS[level] if scan is None or week <= scan else LEVELS[0]
            canvas.rounded_rectangle((x, y, x + 12, y + 12), radius=2, fill=color)
            if level and (scan is None or week <= scan):
                glyph_ink = "#080f1b" if level >= 2 else "#a9dbee"
                canvas.text((x + 6, y + 6), GLYPHS[level], font=small, fill=glyph_ink, anchor="mm")
        return image

    static = frame(None)
    static.save(ASSETS / "activity-static.png", optimize=True)
    palette = static.quantize(colors=144)
    steps = list(range(0, week_count, 2))
    images = [frame(step).quantize(palette=palette, dither=Image.Dither.NONE) for step in steps]
    images.append(palette)
    images[0].save(ASSETS / "activity-scan.gif", save_all=True, append_images=images[1:],
                   duration=[110] * len(steps) + [700], disposal=1, optimize=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--font", default="C:/Windows/Fonts/consola.ttf")
    parser.add_argument("--fetch", metavar="GITHUB_USERNAME")
    args = parser.parse_args()
    previous = json.loads(DATA.read_text(encoding="utf-8"))
    snapshot = fetch_public_calendar(args.fetch) if args.fetch else previous
    if args.fetch and snapshot == previous and all(
        (ASSETS / file).is_file() for file in ("activity-static.png", "activity-scan.gif")
    ):
        return
    render(snapshot, args.font)
    if args.fetch:
        DATA.write_text(json.dumps(snapshot, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
