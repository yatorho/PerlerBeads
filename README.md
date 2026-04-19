# Perler Beads Pattern Generator

把参考图转换成 Perler Beads / 拼豆图纸。工具会把图片缩放到指定拼豆网格，按用户色盘匹配颜色，并输出带颜色编号的图纸、预览图、矩阵 CSV 和材料清单。

## Features

- 支持 PNG、JPG、WEBP 等 Pillow 可读取的图片格式。
- 支持固定宽高、只固定宽度、只固定高度的拼豆网格。
- 默认输出 dense 图纸：透明背景会按底色填充，每一格都有拼豆。
- 支持自定义 CSV / JSON 色盘。
- 每个拼豆单位上显示颜色编号。
- 支持圆形和方形拼豆单位渲染。
- 输出图纸 PNG、实物预览 PNG、矩阵 CSV、材料清单 CSV / JSON。

## Repository Layout

```text
.
├── perler_pattern.py              # CLI tool
├── kitty.png                      # Example input image
├── palettes/starter_perler.csv    # Starter palette
├── environment.yml                # Conda environment
├── requirements.txt               # pip dependency list
├── .github/workflows/ci.yml       # GitHub Actions smoke test
├── LICENSE                        # MIT License
└── README.md
```

生成文件默认写到 `output/`，并已在 `.gitignore` 中忽略。

## Installation

推荐使用 conda：

```bash
conda env create -f environment.yml
conda activate perler-beads
```

也可以使用 venv / pip：

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Quick Start

```bash
python perler_pattern.py kitty.png --size 50x60 --cell-size 28 --output-dir output
```

输出文件：

- `*_pattern.png`: 带编号的拼豆图纸和色号用量
- `*_preview.png`: 接近实物效果的预览图
- `*_matrix.csv`: 每一格对应的颜色编号
- `*_materials.csv`: 颜色编号、名称、HEX 和用量
- `*_materials.json`: 适合后续程序读取的材料清单

## Common Usage

固定宽度，高度按原图比例自动计算：

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

输出方形单位：

```bash
python perler_pattern.py input.png --size 80x60 --bead-shape square
```

去掉右侧图例，减少输出图片宽度：

```bash
python perler_pattern.py input.png --size 80x60 --no-legend
```

只使用色盘前 12 个颜色：

```bash
python perler_pattern.py input.png --size 80x60 --max-colors 12
```

## Key Options

- `--size 80x60`: 输出拼豆画布是 80 列、60 行。
- `--size 80x`: 只固定宽度，高度按原图比例自动计算。
- `--size x60`: 只固定高度，宽度按原图比例自动计算。
- `--fit contain`: 保留完整原图，不足处按 `--background` 生成底色拼豆。
- `--fit cover`: 填满画布，必要时裁切边缘。
- `--fit stretch`: 拉伸到目标网格。
- `--cell-size 24`: 每个拼豆单位在输出 PNG 中占 24 像素。它控制图片分辨率，不改变拼豆数量。
- `--bead-shape circle`: 用圆形单位渲染图纸和预览图。
- `--bead-shape square`: 用方形单位渲染图纸和预览图。
- `--palette`: 使用自定义色盘。
- `--max-colors`: 只使用色盘前 N 个颜色。
- `--background`: 透明背景和 `contain` 模式留边会先合成到这个底色，再匹配到最近的色盘颜色。
- `--allow-empty-transparent`: 只有加这个参数时，透明像素才会变成空格；默认输出是 dense 网格，每一格都是拼豆。
- `--transparent-alpha`: 配合 `--allow-empty-transparent` 使用，控制多透明才算空格。
- `--no-grid`: 图纸不画网格线。
- `--no-legend`: 图纸不画右侧用量表。
- `--title`: 自定义图纸标题。

## Output Resolution

输出图纸 PNG 的分辨率主要由 `--size` 和 `--cell-size` 决定：

```text
pattern width  ~= grid columns * cell-size + margins + legend width
pattern height ~= grid rows * cell-size + margins
```

例如 `--size 40x46 --cell-size 24` 会比 `--size 40x46 --cell-size 16` 更高清，但拼豆数量不变。`--no-legend` 可以减少右侧图例带来的额外宽度。

## Custom Palette

CSV 格式：

```csv
code,name,hex
1,White,#FFFFFF
2,Black,#111111
3,Red,#C91D32
```

也支持 RGB 列：

```csv
code,name,r,g,b
W,White,255,255,255
K,Black,17,17,17
```

JSON 格式：

```json
[
  {"code": "1", "name": "White", "hex": "#FFFFFF"},
  {"code": "2", "name": "Black", "hex": "#111111"}
]
```

`code` 会直接印在每颗拼豆上，所以建议使用短编号或短字母。

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE).

## Notes

- 默认色盘是一个 starter palette，不是任何厂商官方完整色号表。
- `kitty.png` 是仓库内的示例输入图片，可以用于快速测试命令行流程。
