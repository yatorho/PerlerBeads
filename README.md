# Perler Beads Pattern Generator

Generate numbered Perler Beads pattern sheets from reference images. The tool resizes an input image to a bead grid, maps pixels to a user-controlled color palette, and writes a pattern sheet, preview image, grid matrix, and material list.

## Features

- Supports PNG, JPG, WEBP, and other image formats readable by Pillow.
- Supports fixed width and height, width-only, or height-only bead grids.
- Produces dense patterns by default: transparent pixels are composited onto a background color so every grid cell becomes a bead.
- Supports custom CSV and JSON palettes.
- Prints the palette code on each bead unit.
- Renders bead units as circles or squares.
- Exports a numbered pattern PNG, preview PNG, matrix CSV, material CSV, and material JSON.

## Repository Layout

```text
.
|-- perler_pattern.py              # CLI tool
|-- examples/kitty.png             # Example input image
|-- palettes/starter_perler.csv    # Starter palette
|-- environment.yml                # Conda environment
|-- requirements.txt               # pip dependency list
|-- .github/workflows/ci.yml       # GitHub Actions smoke test
|-- LICENSE                        # MIT License
`-- README.md
```

Generated files are written to `output/` by default and ignored by `.gitignore`.

## Installation

Using conda:

```bash
conda env create -f environment.yml
conda activate perler-beads
```

Using venv and pip:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Quick Start

```bash
python perler_pattern.py examples/kitty.png --size 50x60 --cell-size 28 --output-dir output
```

Generated outputs:

- `*_pattern.png`: numbered pattern sheet with a material legend
- `*_preview.png`: bead-style preview image
- `*_matrix.csv`: grid cells mapped to palette codes
- `*_materials.csv`: palette code, name, HEX value, and bead count
- `*_materials.json`: machine-readable material list

## Common Usage

Set the width and calculate height from the source image aspect ratio:

```bash
python perler_pattern.py input.jpg \
  --size 80x \
  --palette palettes/starter_perler.csv \
  --fit contain \
  --cell-size 24 \
  --bead-shape circle \
  --background "#FFFFFF" \
  --output-dir output
```

Render square bead units:

```bash
python perler_pattern.py input.png --size 80x60 --bead-shape square
```

Hide the right-side legend to reduce output image width:

```bash
python perler_pattern.py input.png --size 80x60 --no-legend
```

Use only the first 12 colors from the palette:

```bash
python perler_pattern.py input.png --size 80x60 --max-colors 12
```

## Key Options

- `--size 80x60`: create an 80-column by 60-row bead grid.
- `--size 80x`: set width only and calculate height from the source image aspect ratio.
- `--size x60`: set height only and calculate width from the source image aspect ratio.
- `--fit contain`: keep the full source image and fill extra space with `--background`.
- `--fit cover`: fill the target grid and crop edges when needed.
- `--fit stretch`: stretch the source image to the target grid.
- `--cell-size 24`: render each bead unit as 24 pixels in the output PNG. This controls output resolution, not bead count.
- `--bead-shape circle`: render pattern and preview bead units as circles.
- `--bead-shape square`: render pattern and preview bead units as squares.
- `--palette`: use a custom palette file.
- `--max-colors`: use only the first N colors from the palette.
- `--background`: composite transparent pixels and `contain` padding onto this color before palette matching.
- `--allow-empty-transparent`: let transparent pixels become empty cells. By default, patterns are dense and every cell is a bead.
- `--transparent-alpha`: alpha threshold used with `--allow-empty-transparent`.
- `--no-grid`: hide grid lines on the pattern sheet.
- `--no-legend`: hide the material legend on the pattern sheet.
- `--title`: set a custom pattern title.

## Output Resolution

The pattern PNG resolution is mainly controlled by `--size` and `--cell-size`:

```text
pattern width  ~= grid columns * cell-size + margins + legend width
pattern height ~= grid rows * cell-size + margins
```

For example, `--size 40x46 --cell-size 24` produces a higher-resolution image than `--size 40x46 --cell-size 16`, while keeping the same bead count. Use `--no-legend` to reduce the extra width added by the legend.

## Custom Palette

CSV with HEX colors:

```csv
code,name,hex
1,White,#FFFFFF
2,Black,#111111
3,Red,#C91D32
```

CSV with RGB columns:

```csv
code,name,r,g,b
W,White,255,255,255
K,Black,17,17,17
```

JSON:

```json
[
  {"code": "1", "name": "White", "hex": "#FFFFFF"},
  {"code": "2", "name": "Black", "hex": "#111111"}
]
```

The `code` value is printed directly on each bead, so short numbers or letters work best.

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE).

## Notes

- The included starter palette is not an official complete color chart from any manufacturer.
- `examples/kitty.png` is included as an example input image for quick CLI testing.
