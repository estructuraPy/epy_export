# ruff: noqa: D103, E501

"""Generate the modern ePy family mark for every own application.

The mark is a navy rounded tile, a gold rule, a white application
letter and one small gold glyph that says what the application does.
It is drawn here rather than copied from another product: the family is
ours, and the generator is the source of truth for the PNG and ICO files
the applications and Studio ship.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

SUITE = Path(__file__).resolve().parents[3]
SIZE = 2048
NAVY_TOP = (8, 22, 48)
NAVY_BOTTOM = (18, 48, 100)
GOLD = (226, 178, 63)
WHITE = (247, 249, 255)
MUTED = (174, 188, 218)

APPS = {
    "epy_reports": ("R", "document"),
    "epy_slides": ("S", "slide"),
    "epy_papers": ("P", "paper"),
    "epy_draft": ("D", "pen"),
    "epy_quoting": ("Q", "check"),
    "epy_outreach": ("O", "mail"),
    "epy_project": ("G", "gantt"),
    "epy_studio": ("e", "grid"),
}


def _font(size: int) -> ImageFont.FreeTypeFont:
    for name in ("seguibl.ttf", "segoeuib.ttf", "arialbd.ttf"):
        candidate = Path("C:/Windows/Fonts") / name
        if candidate.is_file():
            return ImageFont.truetype(str(candidate), size)
    return ImageFont.load_default()


def _gradient() -> Image.Image:
    image = Image.new("RGB", (SIZE, SIZE), NAVY_TOP)
    pixels = image.load()
    for y in range(SIZE):
        t = y / (SIZE - 1)
        color = tuple(
            round(NAVY_TOP[i] * (1 - t) + NAVY_BOTTOM[i] * t)
            for i in range(3)
        )
        for x in range(SIZE):
            pixels[x, y] = color
    return image


def _glyph(draw: ImageDraw.ImageDraw, kind: str) -> None:
    left, top, right, bottom = 1320, 1310, 1810, 1800
    if kind == "gantt":
        for index, (x, width) in enumerate(((0, 340), (140, 300), (70, 390))):
            y = top + 70 + index * 150
            draw.rounded_rectangle(
                (left + x, y, left + x + width, y + 54),
                radius=27,
                fill=GOLD,
            )
            draw.ellipse(
                (left + x - 22, y + 7, left + x + 32, y + 61),
                fill=WHITE,
            )
    elif kind == "mail":
        draw.rounded_rectangle(
            (left, top + 80, right, bottom - 90),
            radius=34,
            outline=GOLD,
            width=34,
        )
        draw.line(
            (left + 30, top + 110, (left + right) // 2, top + 410),
            fill=GOLD,
            width=30,
        )
        draw.line(
            ((left + right) // 2, top + 410, right - 30, top + 110),
            fill=GOLD,
            width=30,
        )
    elif kind == "slide":
        draw.rounded_rectangle(
            (left, top + 100, right, bottom - 140),
            radius=34,
            outline=GOLD,
            width=30,
        )
        draw.polygon(
            ((left + 120, top + 210), (left + 120, top + 520), (left + 400, top + 365)),
            fill=GOLD,
        )
    elif kind == "paper":
        draw.polygon(
            ((left + 50, top + 70), (right - 160, top + 70), (right, top + 230),
             (right, bottom - 80), (left + 50, bottom - 80)),
            outline=GOLD,
            width=30,
        )
        draw.line((right - 160, top + 70, right - 160, top + 230), fill=GOLD, width=26)
        draw.line((right - 160, top + 230, right, top + 230), fill=GOLD, width=26)
    elif kind == "document":
        draw.rounded_rectangle(
            (left + 40, top + 50, right - 40, bottom - 80),
            radius=28,
            outline=GOLD,
            width=28,
        )
        for offset in (180, 360, 540):
            draw.line((left + 130, top + offset, right - 130, top + offset), fill=GOLD, width=26)
    elif kind == "pen":
        draw.polygon(
            ((left + 60, bottom - 80), (left + 260, top + 80),
             (left + 500, top + 230), (left + 180, bottom - 80)),
            outline=GOLD,
            width=30,
        )
        draw.line((left + 180, bottom - 80, left + 260, top + 80), fill=GOLD, width=28)
    elif kind == "check":
        draw.ellipse((left + 50, top + 80, right - 50, bottom - 60), outline=GOLD, width=32)
        draw.line(
            (left + 180, top + 380, left + 320, top + 520, left + 510, top + 230),
            fill=GOLD,
            width=42,
            joint="curve",
        )
    elif kind == "grid":
        for row in range(2):
            for col in range(2):
                x = left + 40 + col * 220
                y = top + 140 + row * 220
                draw.rounded_rectangle(
                    (x, y, x + 150, y + 150), radius=24, fill=GOLD
                )
    else:
        draw.ellipse((left + 60, top + 90, right - 60, bottom - 70), outline=GOLD, width=30)


def generate(letter: str, kind: str, target: Path) -> None:
    image = _gradient().convert("RGBA")
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle(
        (76, 76, SIZE - 76, SIZE - 76), radius=410, outline=GOLD, width=22
    )
    draw.rounded_rectangle(
        (104, 104, SIZE - 104, SIZE - 104), radius=382, outline=(255, 255, 255, 24), width=8
    )
    font = _font(1080)
    box = draw.textbbox((0, 0), letter, font=font)
    width = box[2] - box[0]
    draw.text(
        ((SIZE - width) / 2 - box[0], 270 - box[1]),
        letter,
        font=font,
        fill=WHITE,
    )
    _glyph(draw, kind)
    image.resize((1024, 1024), Image.Resampling.LANCZOS).save(target)
    image.resize((1024, 1024), Image.Resampling.LANCZOS).save(
        target.with_suffix(".ico"),
        sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
    )


def _repo(app_id: str) -> Path:
    for base in (SUITE, SUITE / "_deps"):
        candidate = base / app_id
        if candidate.is_dir():
            return candidate
    raise FileNotFoundError(app_id)


def main() -> None:
    for app_id, (letter, kind) in APPS.items():
        repo = _repo(app_id)
        build = repo / "src" / app_id / "_core" / "_packaging" / "assets_build"
        runtime = (
            repo / "src" / app_id / "_config" / "_assets"
            if app_id == "epy_studio"
            else repo / "src" / app_id / "_config" / "_assets" / "branding"
        )
        build.mkdir(parents=True, exist_ok=True)
        runtime.mkdir(parents=True, exist_ok=True)
        generate(letter, kind, build / f"{app_id}.png")
        if app_id == "epy_studio":
            generate(letter, kind, runtime / f"{app_id}.png")
        else:
            generate(letter, kind, runtime / f"{app_id}.png")
        print(app_id, letter, kind)


if __name__ == "__main__":
    main()
