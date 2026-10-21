"""
Generates the PNG assets for the checkers game.

Usage (from the project root):

    python -m games.checkers.generate_assets
    python -m games.checkers.generate_assets --size 64 --preview
    python -m games.checkers.generate_assets --out some/folder

Creates four transparent PNG files in games/checkers/assets/:

    Piece=Man, Side=White.png      Piece=Man, Side=Black.png
    Piece=King, Side=White.png     Piece=King, Side=Black.png

(the same naming scheme as the chess assets). The size has to match
SQUARE_SIZE in checkers_interface.py (55 by default); if you change one,
generate the files again with the other.

Requires Pillow (already a dependency of the project).
Everything is drawn 4x larger and scaled down, so the edges are smooth.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter


DEFAULT_SIZE = 55
SCALE = 4

ASSETS_DIR = Path(__file__).resolve().parent / "assets"

FILE_NAME = "Piece={piece}, Side={side}.png"

# Board colours from checkers_interface.py, used by --preview only.
PREVIEW_LIGHT = (214, 210, 196)
PREVIEW_DARK = (143, 139, 128)

THEME = {
    "White": {
        "edge": (90, 87, 80),
        "face_dark": (206, 201, 188),
        "face_light": (255, 253, 247),
        "groove": (176, 170, 156),
        "glow": 70,
    },
    "Black": {
        "edge": (22, 20, 19),
        "face_dark": (44, 41, 38),
        "face_light": (104, 99, 92),
        "groove": (24, 22, 21),
        "glow": 45,
    },
}

GOLD = (212, 170, 40)
GOLD_DARK = (122, 92, 14)


# ---------------------------------------------------------
# helpers
# ---------------------------------------------------------

def _lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def _disc(draw, cx, cy, radius, fill=None, outline=None, width=1):
    draw.ellipse(
        (cx - radius, cy - radius, cx + radius, cy + radius),
        fill=fill,
        outline=outline,
        width=width,
    )


# ---------------------------------------------------------
# drawing (everything at SCALE times the final size)
# ---------------------------------------------------------

def _draw_man(big: int, side: str) -> Image.Image:
    colors = THEME[side]

    cx = cy = big / 2
    radius = big * 0.40

    image = Image.new("RGBA", (big, big), (0, 0, 0, 0))

    # soft drop shadow
    shadow = Image.new("RGBA", (big, big), (0, 0, 0, 0))

    _disc(
        ImageDraw.Draw(shadow),
        cx,
        cy + big * 0.035,
        radius,
        fill=(0, 0, 0, 90),
    )

    image.alpha_composite(
        shadow.filter(ImageFilter.GaussianBlur(big * 0.018))
    )

    draw = ImageDraw.Draw(image)

    # outer edge
    _disc(draw, cx, cy, radius, fill=colors["edge"] + (255,))

    # face with a radial gradient, the light comes from the top left
    face_radius = radius * 0.93
    steps = 40

    for i in range(steps):
        t = i / (steps - 1)

        _disc(
            draw,
            cx - face_radius * 0.18 * t,
            cy - face_radius * 0.18 * t,
            face_radius * (1 - t * 0.92),
            fill=_lerp(colors["face_dark"], colors["face_light"], t) + (255,),
        )

    # two grooves, like on real draughts
    for factor in (0.74, 0.50):
        _disc(
            draw,
            cx,
            cy,
            radius * factor,
            outline=colors["groove"] + (255,),
            width=max(2, int(big * 0.016)),
        )

    # small specular highlight
    glow = Image.new("RGBA", (big, big), (0, 0, 0, 0))

    ImageDraw.Draw(glow).ellipse(
        (
            cx - radius * 0.62,
            cy - radius * 0.72,
            cx - radius * 0.12,
            cy - radius * 0.38,
        ),
        fill=(255, 255, 255, colors["glow"]),
    )

    image.alpha_composite(
        glow.filter(ImageFilter.GaussianBlur(big * 0.02))
    )

    return image


def _draw_crown(image: Image.Image) -> None:
    """Draws a golden crown in the middle of the image (in place)."""
    big = image.size[0]
    draw = ImageDraw.Draw(image)

    cx = cy = big / 2

    width = big * 0.34
    height = big * 0.24

    left = cx - width / 2
    right = cx + width / 2
    top = cy - height / 2
    bottom = cy + height / 2

    peak = top - height * 0.12

    points = [
        (left, bottom),
        (left, top),
        (cx - width * 0.25, cy - height * 0.02),
        (cx, peak),
        (cx + width * 0.25, cy - height * 0.02),
        (right, top),
        (right, bottom),
    ]

    gold = GOLD + (255,)
    dark = GOLD_DARK + (255,)
    line = max(2, int(big * 0.014))

    draw.polygon(points, fill=gold, outline=dark, width=line)

    # band at the bottom of the crown
    draw.rectangle(
        (left, bottom - height * 0.22, right, bottom),
        fill=dark,
    )

    # pearls on the three peaks
    for px, py in ((left, top), (cx, peak), (right, top)):
        _disc(draw, px, py, big * 0.027, fill=gold, outline=dark, width=line)


# ---------------------------------------------------------
# public API
# ---------------------------------------------------------

def render_piece(size: int, side: str, king: bool = False) -> Image.Image:
    """
    Returns a size x size transparent RGBA image.

    side: "White" or "Black"
    """
    if side not in THEME:
        raise ValueError(f"side must be 'White' or 'Black', got {side!r}")

    image = _draw_man(size * SCALE, side)

    if king:
        _draw_crown(image)

    return image.resize((size, size), Image.LANCZOS)


def generate(out_dir: Path = ASSETS_DIR, size: int = DEFAULT_SIZE) -> list[Path]:
    """
    Creates the four piece images. Returns the written files.
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    written = []

    for side in ("White", "Black"):
        for piece, king in (("Man", False), ("King", True)):
            path = out_dir / FILE_NAME.format(piece=piece, side=side)

            render_piece(size, side, king).save(path)

            written.append(path)

    return written


def make_preview(out_dir: Path = ASSETS_DIR, size: int = DEFAULT_SIZE) -> Path:
    """
    Saves preview.png: all four pieces on light and dark squares.
    """
    out_dir = Path(out_dir)

    cell = size
    sheet = Image.new("RGB", (cell * 4, cell * 2), PREVIEW_LIGHT)

    draw = ImageDraw.Draw(sheet)

    for row in range(2):
        for col in range(4):
            color = PREVIEW_DARK if (row + col) % 2 == 1 else PREVIEW_LIGHT

            draw.rectangle(
                (col * cell, row * cell, (col + 1) * cell, (row + 1) * cell),
                fill=color,
            )

    pieces = [
        ("White", False), ("White", True), ("Black", False), ("Black", True),
    ]

    for index, (side, king) in enumerate(pieces):
        piece = render_piece(size, side, king)

        for row in range(2):
            x = index * cell
            y = row * cell

            sheet.paste(piece, (x, y), piece)

    path = out_dir / "preview.png"

    sheet.resize((sheet.width * 3, sheet.height * 3), Image.NEAREST).save(path)

    return path


def main():
    parser = argparse.ArgumentParser(
        description="Generate PNG assets for the checkers game."
    )

    parser.add_argument(
        "--size",
        type=int,
        default=DEFAULT_SIZE,
        help=f"piece image size in pixels (default {DEFAULT_SIZE}, "
             "must match SQUARE_SIZE in checkers_interface.py)",
    )

    parser.add_argument(
        "--out",
        type=Path,
        default=ASSETS_DIR,
        help="output folder (default: games/checkers/assets)",
    )

    parser.add_argument(
        "--preview",
        action="store_true",
        help="also save preview.png with all pieces on a board",
    )

    args = parser.parse_args()

    if args.size < 16:
        parser.error("--size must be at least 16")

    for path in generate(args.out, args.size):
        print(f"  + {path}")

    if args.preview:
        print(f"  + {make_preview(args.out, args.size)}")


if __name__ == "__main__":
    main()
