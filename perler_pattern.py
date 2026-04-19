#!/usr/bin/env python3
"""Generate numbered Perler bead patterns from reference images."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from PIL import Image, ImageDraw, ImageFont, ImageOps


DEFAULT_PALETTE = Path(__file__).resolve().parent / "palettes" / "starter_perler.csv"
TRANSPARENT_CODE = "."
BEAD_SHAPES = ("circle", "square")


@dataclass(frozen=True)
class PaletteColor:
    code: str
    name: str
    rgb: tuple[int, int, int]
    hex: str


def parse_hex_color(value: str) -> tuple[int, int, int]:
    text = value.strip()
    if text.startswith("#"):
        text = text[1:]
    if len(text) == 3:
        text = "".join(ch * 2 for ch in text)
    if len(text) != 6:
        raise ValueError(f"Invalid hex color: {value!r}")
    return tuple(int(text[i : i + 2], 16) for i in (0, 2, 4))


def rgb_to_hex(rgb: tuple[int, int, int]) -> str:
    return "#{:02X}{:02X}{:02X}".format(*rgb)


def load_palette(path: Path, limit: int | None = None) -> list[PaletteColor]:
    if not path.exists():
        raise FileNotFoundError(f"Palette file not found: {path}")

    if path.suffix.lower() == ".json":
        data = json.loads(path.read_text(encoding="utf-8"))
        rows = data.get("colors", data) if isinstance(data, dict) else data
    else:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.DictReader(handle))

    palette: list[PaletteColor] = []
    seen_codes: set[str] = set()
    for index, row in enumerate(rows, start=1):
        code = str(row.get("code") or row.get("id") or index).strip()
        name = str(row.get("name") or row.get("label") or f"Color {code}").strip()
        color_value = row.get("hex") or row.get("color")
        if color_value:
            rgb = parse_hex_color(str(color_value))
        else:
            rgb = (
                int(row["r"]),
                int(row["g"]),
                int(row["b"]),
            )
        if code in seen_codes:
            raise ValueError(f"Duplicate palette code: {code}")
        seen_codes.add(code)
        palette.append(PaletteColor(code=code, name=name, rgb=rgb, hex=rgb_to_hex(rgb)))

    if not palette:
        raise ValueError(f"Palette is empty: {path}")
    if limit is not None:
        if limit <= 0:
            raise ValueError("--max-colors must be greater than zero")
        palette = palette[:limit]
    return palette


def parse_size(text: str) -> tuple[int | None, int | None]:
    if "x" not in text.lower():
        value = int(text)
        return value, None
    left, right = text.lower().split("x", 1)
    width = int(left) if left else None
    height = int(right) if right else None
    if width is None and height is None:
        raise argparse.ArgumentTypeError("Size must include width, height, or both")
    return width, height


def resolve_grid_size(
    requested: tuple[int | None, int | None], image_size: tuple[int, int]
) -> tuple[int, int]:
    req_width, req_height = requested
    image_width, image_height = image_size
    if req_width is None and req_height is None:
        raise ValueError("A grid width or height is required")
    if req_width is None:
        req_width = max(1, round(req_height * image_width / image_height))
    if req_height is None:
        req_height = max(1, round(req_width * image_height / image_width))
    if req_width <= 0 or req_height <= 0:
        raise ValueError("Grid dimensions must be greater than zero")
    return req_width, req_height


def prepare_image(
    image_path: Path,
    grid_size: tuple[int, int],
    fit: str,
    background: tuple[int, int, int],
) -> Image.Image:
    source = Image.open(image_path)
    source = ImageOps.exif_transpose(source).convert("RGBA")
    target_width, target_height = grid_size

    if fit == "stretch":
        fitted = source.resize(grid_size, Image.Resampling.LANCZOS)
    elif fit == "cover":
        fitted = ImageOps.fit(source, grid_size, method=Image.Resampling.LANCZOS, centering=(0.5, 0.5))
    else:
        canvas = Image.new("RGBA", grid_size, (*background, 255))
        contained = ImageOps.contain(source, grid_size, method=Image.Resampling.LANCZOS)
        offset = ((target_width - contained.width) // 2, (target_height - contained.height) // 2)
        canvas.alpha_composite(contained, offset)
        fitted = canvas

    return fitted


def color_distance(a: tuple[int, int, int], b: tuple[int, int, int]) -> int:
    red_mean = (a[0] + b[0]) // 2
    red_delta = a[0] - b[0]
    green_delta = a[1] - b[1]
    blue_delta = a[2] - b[2]
    return (
        (((512 + red_mean) * red_delta * red_delta) >> 8)
        + 4 * green_delta * green_delta
        + (((767 - red_mean) * blue_delta * blue_delta) >> 8)
    )


def nearest_palette_color(
    rgb: tuple[int, int, int], palette: list[PaletteColor]
) -> PaletteColor:
    return min(palette, key=lambda color: color_distance(rgb, color.rgb))


def pixel_to_rgb(pixel: tuple[int, ...], background: tuple[int, int, int]) -> tuple[int, int, int]:
    red, green, blue, alpha = pixel
    if alpha >= 255:
        return red, green, blue
    alpha_ratio = alpha / 255
    return (
        round(red * alpha_ratio + background[0] * (1 - alpha_ratio)),
        round(green * alpha_ratio + background[1] * (1 - alpha_ratio)),
        round(blue * alpha_ratio + background[2] * (1 - alpha_ratio)),
    )


def quantize_to_palette(
    image: Image.Image,
    palette: list[PaletteColor],
    background: tuple[int, int, int],
    transparent_alpha: int,
    allow_empty_transparent: bool,
) -> tuple[list[list[str]], dict[str, PaletteColor], Counter[str]]:
    width, height = image.size
    pixels = image.load()
    matrix: list[list[str]] = []
    counts: Counter[str] = Counter()
    used: dict[str, PaletteColor] = {}

    for y in range(height):
        row: list[str] = []
        for x in range(width):
            pixel = pixels[x, y]
            if allow_empty_transparent and len(pixel) == 4 and pixel[3] < transparent_alpha:
                row.append(TRANSPARENT_CODE)
                continue
            rgb = pixel_to_rgb(pixel, background)
            color = nearest_palette_color(rgb, palette)
            row.append(color.code)
            counts[color.code] += 1
            used[color.code] = color
        matrix.append(row)

    return matrix, used, counts


def contrasting_text_color(rgb: tuple[int, int, int]) -> tuple[int, int, int]:
    luminance = (0.299 * rgb[0]) + (0.587 * rgb[1]) + (0.114 * rgb[2])
    return (0, 0, 0) if luminance > 150 else (255, 255, 255)


def load_font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    candidates = [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/Library/Fonts/Arial Bold.ttf" if bold else "/Library/Fonts/Arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for candidate in candidates:
        try:
            return ImageFont.truetype(candidate, size)
        except OSError:
            pass
    return ImageFont.load_default()


def text_size(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont) -> tuple[int, int]:
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]


def draw_centered_text(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    text: str,
    font: ImageFont.ImageFont,
    fill: tuple[int, int, int],
) -> None:
    width, height = text_size(draw, text, font)
    left, top, right, bottom = box
    x = left + ((right - left - width) / 2)
    y = top + ((bottom - top - height) / 2) - 1
    draw.text((x, y), text, font=font, fill=fill)


def draw_bead(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    color: tuple[int, int, int],
    shape: str,
    outline: tuple[int, int, int],
) -> None:
    left, top, right, bottom = box
    inset = max(1, (right - left) // 10)
    bead_box = (left + inset, top + inset, right - inset, bottom - inset)
    if shape == "square":
        draw.rectangle(bead_box, fill=color, outline=outline)
    else:
        draw.ellipse(bead_box, fill=color, outline=outline)


def render_pattern(
    matrix: list[list[str]],
    used: dict[str, PaletteColor],
    counts: Counter[str],
    output_path: Path,
    cell_size: int,
    show_grid: bool,
    show_legend: bool,
    title: str,
    bead_shape: str,
) -> None:
    rows = len(matrix)
    cols = len(matrix[0])
    margin = max(18, cell_size)
    legend_width = 0
    if show_legend:
        legend_width = max(270, cell_size * 7)

    code_font = load_font(max(8, min(cell_size - 4, int(cell_size * 0.42))), bold=True)
    title_font = load_font(max(16, int(cell_size * 0.55)), bold=True)
    legend_font = load_font(14)
    legend_bold = load_font(14, bold=True)

    scratch = Image.new("RGB", (1, 1), "white")
    scratch_draw = ImageDraw.Draw(scratch)
    title_height = text_size(scratch_draw, title, title_font)[1]
    title_area = title_height + max(14, cell_size // 2)
    grid_top = margin + title_area
    grid_left = margin
    grid_width = cols * cell_size
    grid_height = rows * cell_size
    legend_header_height = 28 if show_legend else 0
    legend_row_height = 24
    legend_height = legend_header_height + (len(counts) * legend_row_height)
    image_width = grid_width + (margin * 2) + legend_width
    image_height = max(grid_height, legend_height) + (margin * 2) + title_area
    output = Image.new("RGB", (image_width, image_height), "white")
    draw = ImageDraw.Draw(output)
    grid_color = (210, 210, 210)

    draw.text((margin, margin // 2), title, fill=(20, 20, 20), font=title_font)

    for y, row in enumerate(matrix):
        for x, code in enumerate(row):
            left = grid_left + x * cell_size
            top = grid_top + y * cell_size
            right = left + cell_size
            bottom = top + cell_size
            if code == TRANSPARENT_CODE:
                draw.rectangle((left, top, right, bottom), fill=(248, 248, 248), outline=grid_color if show_grid else None)
                draw.line((left, top, right, bottom), fill=(225, 225, 225))
                draw.line((right, top, left, bottom), fill=(225, 225, 225))
                continue

            color = used[code]
            draw.rectangle((left, top, right, bottom), fill=(245, 245, 245), outline=grid_color if show_grid else None)
            draw_bead(draw, (left, top, right, bottom), color.rgb, bead_shape, (120, 120, 120))
            draw_centered_text(
                draw,
                (left, top, right, bottom),
                code,
                code_font,
                contrasting_text_color(color.rgb),
            )

    if show_grid:
        for x in range(cols + 1):
            px = grid_left + x * cell_size
            draw.line((px, grid_top, px, grid_top + grid_height), fill=grid_color)
        for y in range(rows + 1):
            py = grid_top + y * cell_size
            draw.line((grid_left, py, grid_left + grid_width, py), fill=grid_color)

    if show_legend:
        legend_left = grid_left + grid_width + margin
        y = grid_top
        draw.text((legend_left, y), "Legend / Materials", fill=(20, 20, 20), font=legend_bold)
        y += 28
        for code, count in sorted(counts.items(), key=lambda item: natural_sort_key(item[0])):
            color = used[code]
            draw.rectangle((legend_left, y, legend_left + 18, y + 18), fill=color.rgb, outline=(80, 80, 80))
            label = f"{code}  {color.name}  {color.hex}  x{count}"
            draw.text((legend_left + 28, y), label, fill=(30, 30, 30), font=legend_font)
            y += 24

    output.save(output_path)


def render_preview(
    matrix: list[list[str]],
    used: dict[str, PaletteColor],
    output_path: Path,
    cell_size: int,
    bead_shape: str,
) -> None:
    rows = len(matrix)
    cols = len(matrix[0])
    image = Image.new("RGBA", (cols * cell_size, rows * cell_size), (255, 255, 255, 0))
    draw = ImageDraw.Draw(image)
    for y, row in enumerate(matrix):
        for x, code in enumerate(row):
            if code == TRANSPARENT_CODE:
                continue
            color = used[code]
            left = x * cell_size
            top = y * cell_size
            draw_bead(
                draw,
                (left, top, left + cell_size, top + cell_size),
                (*color.rgb, 255),
                bead_shape,
                (90, 90, 90, 255),
            )
    image.save(output_path)


def natural_sort_key(value: str) -> tuple[int, int | str]:
    return (0, int(value)) if value.isdigit() else (1, value)


def write_matrix_csv(matrix: list[list[str]], output_path: Path) -> None:
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["row/col", *range(1, len(matrix[0]) + 1)])
        for index, row in enumerate(matrix, start=1):
            writer.writerow([index, *row])


def write_materials_csv(
    used: dict[str, PaletteColor],
    counts: Counter[str],
    output_path: Path,
) -> None:
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["code", "name", "hex", "count"])
        writer.writeheader()
        for code, count in sorted(counts.items(), key=lambda item: natural_sort_key(item[0])):
            color = used[code]
            writer.writerow({"code": code, "name": color.name, "hex": color.hex, "count": count})


def write_materials_json(
    used: dict[str, PaletteColor],
    counts: Counter[str],
    output_path: Path,
    grid_size: tuple[int, int],
    source: Path,
) -> None:
    payload = {
        "source": str(source),
        "grid": {"width": grid_size[0], "height": grid_size[1]},
        "total_beads": sum(counts.values()),
        "colors": [
            {
                "code": code,
                "name": used[code].name,
                "hex": used[code].hex,
                "count": count,
            }
            for code, count in sorted(counts.items(), key=lambda item: natural_sort_key(item[0]))
        ],
    }
    output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate numbered Perler bead pattern sheets from images."
    )
    parser.add_argument("image", type=Path, help="Reference image path")
    parser.add_argument(
        "-o",
        "--output-dir",
        type=Path,
        default=Path("examples/output"),
        help="Output directory",
    )
    parser.add_argument(
        "-s",
        "--size",
        type=parse_size,
        default=(60, None),
        help="Bead grid size as WIDTHxHEIGHT, WIDTHx, xHEIGHT, or WIDTH. Default: 60x auto",
    )
    parser.add_argument(
        "-p",
        "--palette",
        type=Path,
        default=DEFAULT_PALETTE,
        help="CSV or JSON palette. CSV columns: code,name,hex or code,name,r,g,b",
    )
    parser.add_argument("--max-colors", type=int, default=None, help="Use only the first N palette colors")
    parser.add_argument("--cell-size", type=int, default=28, help="Pattern cell size in pixels")
    parser.add_argument(
        "--bead-shape",
        choices=BEAD_SHAPES,
        default="circle",
        help="Rendered bead unit shape",
    )
    parser.add_argument(
        "--fit",
        choices=["contain", "cover", "stretch"],
        default="contain",
        help="How the source image fits into the bead grid",
    )
    parser.add_argument("--background", default="#FFFFFF", help="Background color for transparent/contained areas")
    parser.add_argument(
        "--transparent-alpha",
        type=int,
        default=10,
        help="Alpha threshold used only with --allow-empty-transparent",
    )
    parser.add_argument(
        "--allow-empty-transparent",
        action="store_true",
        help="Let pixels below --transparent-alpha become empty cells instead of background-filled beads",
    )
    parser.add_argument("--no-grid", action="store_true", help="Hide square grid lines on the pattern")
    parser.add_argument("--no-legend", action="store_true", help="Hide legend on the pattern PNG")
    parser.add_argument("--title", default=None, help="Pattern title printed on the sheet")
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    if args.cell_size < 12:
        parser.error("--cell-size must be at least 12 so color codes remain readable")
    if not 0 <= args.transparent_alpha <= 255:
        parser.error("--transparent-alpha must be between 0 and 255")
    if not args.image.exists():
        parser.error(f"Image not found: {args.image}")

    background = parse_hex_color(args.background)
    with Image.open(args.image) as original:
        image_size = original.size
    grid_size = resolve_grid_size(args.size, image_size)
    palette = load_palette(args.palette, args.max_colors)
    prepared = prepare_image(args.image, grid_size, args.fit, background)
    matrix, used, counts = quantize_to_palette(
        prepared,
        palette,
        background,
        args.transparent_alpha,
        args.allow_empty_transparent,
    )

    stem = args.image.stem
    args.output_dir.mkdir(parents=True, exist_ok=True)
    pattern_path = args.output_dir / f"{stem}_pattern.png"
    preview_path = args.output_dir / f"{stem}_preview.png"
    matrix_path = args.output_dir / f"{stem}_matrix.csv"
    materials_csv_path = args.output_dir / f"{stem}_materials.csv"
    materials_json_path = args.output_dir / f"{stem}_materials.json"

    title = args.title or f"{stem} - {grid_size[0]}x{grid_size[1]} beads"
    render_pattern(
        matrix=matrix,
        used=used,
        counts=counts,
        output_path=pattern_path,
        cell_size=args.cell_size,
        show_grid=not args.no_grid,
        show_legend=not args.no_legend,
        title=title,
        bead_shape=args.bead_shape,
    )
    render_preview(matrix, used, preview_path, max(8, min(args.cell_size, 24)), args.bead_shape)
    write_matrix_csv(matrix, matrix_path)
    write_materials_csv(used, counts, materials_csv_path)
    write_materials_json(used, counts, materials_json_path, grid_size, args.image)

    print(f"Pattern:   {pattern_path}")
    print(f"Preview:   {preview_path}")
    print(f"Matrix:    {matrix_path}")
    print(f"Materials: {materials_csv_path}")
    print(f"Materials: {materials_json_path}")
    print(f"Grid:      {grid_size[0]} x {grid_size[1]}")
    print(f"Beads:     {sum(counts.values())}")
    print(f"Colors:    {len(counts)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
