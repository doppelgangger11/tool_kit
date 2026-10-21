
"""Generate minimalist, perspective-style checkers assets.

Usage:
    python -m games.checkers.generate_assets
    python -m games.checkers.generate_assets --size 64 --preview
    python -m games.checkers.generate_assets --out some/folder

Creates:
    Piece=Man, Side=White.png
    Piece=Man, Side=Black.png
    Piece=King, Side=White.png
    Piece=King, Side=Black.png

Requires Pillow.
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
        "edge": (77, 73, 65),
        "face": (246, 243, 233),
        "side": (207, 202, 189),
        "side_light": (224, 219, 207),
        "ring": (177, 171, 158),
        "shadow_alpha": 65,
    },
    "Black": {
        "edge": (25, 24, 23),
        "face": (65, 62, 58),
        "side": (43, 41, 39),
        "side_light": (54, 51, 48),
        "ring": (91, 86, 79),
        "shadow_alpha": 85,
    },
}

GOLD = (232, 181, 52)
GOLD_LIGHT = (250, 210, 93)
GOLD_EDGE = (119, 83, 20)


def _ellipse(
    draw,
    cx: float,
    cy: float,
    rx: float,
    ry: float,
    fill=None,
    outline=None,
    width: int = 1,
):
    draw.ellipse(
        (cx - rx, cy - ry, cx + rx, cy + ry),
        fill=fill,
        outline=outline,
        width=width,
    )


def _draw_cylinder(
    image,
    cx,
    top_y,
    rx,
    ry,
    depth,
    colors,
    line_width,
):
    draw = ImageDraw.Draw(image)

    left = cx - rx
    right = cx + rx
    bottom_y = top_y + depth

    # Body: short side wall between two elliptical surfaces.
    draw.rectangle(
        (left, top_y, right, bottom_y),
        fill=colors["side"],
    )

    # Front-facing half of the lower rim.
    draw.pieslice(
        (left, bottom_y - ry, right, bottom_y + ry),
        start=0,
        end=180,
        fill=colors["edge"],
    )

    # Restore the flat side wall so the bottom does not look like a box.
    draw.rectangle(
        (left, top_y, right, bottom_y),
        fill=colors["side"],
    )

    # Top rim, drawn last to create a clean silhouette.
    _ellipse(
        draw,
        cx,
        top_y,
        rx,
        ry,
        fill=colors["edge"],
    )

    _ellipse(
        draw,
        cx,
        top_y,
        rx - line_width,
        ry - line_width,
        fill=colors["face"],
        outline=colors["ring"],
        width=line_width,
    )




def _draw_crown(
    draw,
    cx: float,
    cy: float,
    width: float,
    height: float,
    line_width: int,
):
    """Draw a compact gold crown centered on the top surface."""

    left = cx - width / 2
    right = cx + width / 2
    top = cy - height / 2
    bottom = cy + height / 2

    points = [
        (left, bottom),
        (left - width * 0.04, top + height * 0.08),
        (cx - width * 0.25, cy + height * 0.04),
        (cx, top - height * 0.17),
        (cx + width * 0.25, cy + height * 0.04),
        (right + width * 0.04, top + height * 0.08),
        (right, bottom),
    ]

    draw.polygon(
        points,
        fill=GOLD,
        outline=GOLD_EDGE,
        width=line_width,
    )

    # Slightly lighter upper edge.
    draw.line(
        points[1:6],
        fill=GOLD_LIGHT,
        width=line_width,
    )

    # Crown band.
    draw.line(
        [
            (left + width * 0.02, bottom - height * 0.16),
            (right - width * 0.02, bottom - height * 0.16),
        ],
        fill=GOLD_EDGE,
        width=line_width,
    )

    # Three simple round tips.
    for px, py in (
        (points[1][0], points[1][1]),
        (points[3][0], points[3][1]),
        (points[5][0], points[5][1]),
    ):
        _ellipse(
            draw,
            px,
            py,
            width * 0.045,
            width * 0.045,
            fill=GOLD_LIGHT,
            outline=GOLD_EDGE,
            width=line_width,
        )


def _draw_piece(size: int, side: str, king: bool) -> Image.Image:
    """Draw a one-layer man or two-layer crowned king."""

    colors = THEME[side]
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))

    cx = size / 2
    rx = size * 0.405
    ry = size * 0.30
    depth = size * 0.10
    line_width = max(1, int(size * 0.025))

    # Top surface positions. Kings use two closely stacked layers.
    top_y = size * (0.345 if king else 0.395)

    # Soft shadow underneath the token.
    # shadow = Image.new("RGBA", image.size, (0, 0, 0, 0))
    # sd = ImageDraw.Draw(shadow)

    # _ellipse(
    #     sd,
    #     cx,
    #     top_y + depth + ry * (2 if king else 1) + size * 0.015,
    #     rx * 0.91,
    #     ry * 0.75,
    #     fill=(0, 0, 0, colors["shadow_alpha"]),
    # )

    # image.alpha_composite(
    #     shadow.filter(ImageFilter.GaussianBlur(size * 0.035))
    # )

    draw = ImageDraw.Draw(image)

    if king:
        # Bottom cylinder first; the upper cylinder overlaps it.
        lower_y = top_y + size * 0.175

        _draw_cylinder(
            image,
            cx,
            lower_y,
            rx,
            ry,
            depth,
            colors,
            line_width,
        )

    _draw_cylinder(
        image,
        cx,
        top_y,
        rx,
        ry,
        depth,
        colors,
        line_width,
    )

    if king:
        # The crown sits on the upper face.
        crown_width = size * 0.34
        crown_height = size * 0.205

        _draw_crown(
            draw,
            cx,
            top_y + size * 0.005,
            crown_width,
            crown_height,
            max(1, int(size * 0.018)),
        )

    return image


def render_piece(
    size: int,
    side: str,
    king: bool = False,
) -> Image.Image:
    """Return a transparent RGBA image of exactly size x size."""

    if side not in THEME:
        raise ValueError(
            f"side must be 'White' or 'Black', got {side!r}"
        )

    if size < 16:
        raise ValueError("size must be at least 16")

    big = size * SCALE
    image = _draw_piece(big, side, king)

    return image.resize(
        (size, size),
        Image.Resampling.LANCZOS,
    )


def generate(
    out_dir: Path = ASSETS_DIR,
    size: int = DEFAULT_SIZE,
) -> list[Path]:
    """Generate the four piece assets."""

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    written = []

    for side in ("White", "Black"):
        for piece, king in (
            ("Man", False),
            ("King", True),
        ):
            path = out_dir / FILE_NAME.format(
                piece=piece,
                side=side,
            )

            render_piece(size, side, king).save(path)

            written.append(path)

    return written


def make_preview(
    out_dir: Path = ASSETS_DIR,
    size: int = DEFAULT_SIZE,
) -> Path:
    """Create a preview board showing all four assets."""

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    cell = size
    sheet = Image.new(
        "RGB",
        (cell * 4, cell * 2),
        PREVIEW_LIGHT,
    )
    draw = ImageDraw.Draw(sheet)

    for row in range(2):
        for col in range(4):
            color = (
                PREVIEW_DARK
                if (row + col) % 2
                else PREVIEW_LIGHT
            )

            draw.rectangle(
                (
                    col * cell,
                    row * cell,
                    (col + 1) * cell,
                    (row + 1) * cell,
                ),
                fill=color,
            )

    pieces = [
        ("White", False),
        ("White", True),
        ("Black", False),
        ("Black", True),
    ]

    for index, (side, king) in enumerate(pieces):
        piece = render_piece(size, side, king)

        for row in range(2):
            sheet.paste(
                piece,
                (index * cell, row * cell),
                piece,
            )

    path = out_dir / "preview.png"
    sheet.resize(
        (sheet.width * 3, sheet.height * 3),
        Image.Resampling.NEAREST,
    ).save(path)

    return path


def main():
    parser = argparse.ArgumentParser(
        description="Generate minimalist checkers PNG assets."
    )

    parser.add_argument(
        "--size",
        type=int,
        default=DEFAULT_SIZE,
        help=f"piece image size in pixels (default {DEFAULT_SIZE})",
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
        help="also save preview.png",
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
