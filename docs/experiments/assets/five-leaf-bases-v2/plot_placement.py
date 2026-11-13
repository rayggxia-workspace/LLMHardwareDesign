from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
from matplotlib.patches import Rectangle
from PIL import Image

PLACEMENT = re.compile(r"\+ (?:PLACED|FIXED)\s+\(\s*(-?\d+)\s+(-?\d+)\s*\)\s+(\w+)")
DIE = re.compile(r"DIEAREA\s+\(\s*(-?\d+)\s+(-?\d+)\s*\)\s+\(\s*(-?\d+)\s+(-?\d+)\s*\)")
M10 = re.compile(r"\+ LAYER metal10\s+\(\s*(-?\d+)\s+(-?\d+)\s*\)\s+\(\s*(-?\d+)\s+(-?\d+)\s*\)")
PG = re.compile(r"\+ USE (?:POWER|GROUND)\b")
COLORS = {
    "M60": "#86b6df", "N32": "#bda8e2", "R256": "#86b6df", "T6": "#bda8e2",
    "G32": "#f2cb74", "G16": "#f2cb74", "E32": "#e389a0", "E16": "#eaa7a9",
    "S_base": "#9dd3b9", "PM bank": "#bddcdd",
}


def checked_path(path, expected):
    with path.open("rb") as stream:
        actual = hashlib.file_digest(stream, "sha256").hexdigest()
    if actual != expected:
        raise ValueError(f"{path}: expected {expected}, got {actual}")
    return path


def records(stream, section):
    """Yield one complete DEF record at a time."""
    pieces = []
    for line in stream:
        if line.startswith(f"END {section}"):
            if pieces:
                raise ValueError(f"Incomplete {section} record")
            break
        pieces.append(line)
        if line.rstrip().endswith(";"):
            yield "".join(pieces)
            pieces.clear()


def read_def(path, dimensions):
    macros, cells, pads = [], [], {}
    with path.open(encoding="utf-8") as stream:
        for line in stream:
            if line.startswith("UNITS DISTANCE MICRONS"):
                units = int(line.split()[3])
            elif line.startswith("DIEAREA"):
                die = tuple(int(value) / units for value in DIE.match(line).groups())
            elif line.startswith("COMPONENTS "):
                for entry in records(stream, "COMPONENTS"):
                    _, name, master, *_ = entry.split(maxsplit=3)
                    if master.startswith(("FILLCELL", "TAPCELL")):
                        continue
                    match = PLACEMENT.search(entry)
                    if not match:
                        continue
                    x, y, orient = match.groups()
                    xy = int(x) / units, int(y) / units
                    if master in dimensions:
                        label, (width, height) = dimensions[master]
                        if orient in {"E", "W", "FE", "FW"}:
                            width, height = height, width
                        macros.append((label, *xy, width, height))
                    else:
                        cells.append(xy)
            elif line.startswith("PINS "):
                for entry in records(stream, "PINS"):
                    if PG.search(entry) or not (shape := M10.search(entry)):
                        continue
                    position = PLACEMENT.search(entry)
                    if not position or position[3] != "N" or len(M10.findall(entry)) != 1:
                        raise ValueError(f"{path}: unsupported M10 port geometry")
                    x0, y0, x1, y1 = map(int, shape.groups())
                    x = (int(position[1]) + (x0 + x1) / 2) / units
                    y = (int(position[2]) + (y0 + y1) / 2) / units
                    pads[entry.split()[1]] = (x, y)
                break
    return die, macros, cells, pads


def size(die):
    x0, y0, x1, y1 = die
    return x1 - x0, y1 - y0


def save_png(fig, path):
    fig.savefig(path, dpi=160, facecolor="white")
    with Image.open(path) as png:
        reduced = png.convert("RGB").quantize(colors=128, method=Image.Quantize.MEDIANCUT)
    reduced.save(path, optimize=True)
    plt.close(fig)


def paint(ax, data, origin=(0, 0), *, pad_size=2.1, label_size=7.2, box_color="#7b8da0"):
    die, macros, cells, pads = data
    dx, dy = origin[0] - die[0], origin[1] - die[1]
    if cells:
        xs, ys = zip(*((x + dx, y + dy) for x, y in cells))
        ax.scatter(xs, ys, s=.55, c="#637582", alpha=.23, linewidths=0, zorder=1)
    for name, x, y, w, h in macros:
        ax.add_patch(Rectangle((x + dx, y + dy), w, h, facecolor=COLORS[name],
                               edgecolor="#455a6d", lw=.8, zorder=2))
        text = f"{name}\n{w:.0f} × {h:.0f}" if label_size >= 7 else name
        ax.text(x + dx + w / 2, y + dy + h / 2, text, ha="center", va="center",
                fontsize=label_size, color="#1c3345", zorder=4)
    if pads:
        xs, ys = zip(*((x + dx, y + dy) for x, y in pads.values()))
        ax.scatter(xs, ys, s=pad_size, c="#ea722e", alpha=.75, linewidths=0, zorder=3)
    w, h = size(die)
    ax.add_patch(Rectangle(origin, w, h, fill=False, edgecolor=box_color,
                           linestyle="--", lw=.9, zorder=4))


def group_title(ax, data, title, pad_size=2.1):
    paint(ax, data, pad_size=pad_size, box_color="#bf7135" if title.startswith("P2545") else "#7b8da0")
    w, h = size(data[0])
    ax.set(aspect="equal", xlim=(-.045*w, 1.045*w), ylim=(-.045*h, 1.045*h),
           title=f"{title}    {w:.0f} × {h:.0f} µm    M10 {len(data[3]):,}")
    ax.tick_params(labelsize=8, colors="#617487")
    ax.spines[:].set_visible(False)


def render_panels(output, name, title, footer, entries, font, columns, figsize, pad_size):
    rows = (len(entries) + columns - 1) // columns
    fig, axes = plt.subplots(rows, columns, figsize=figsize, squeeze=False)
    for ax, (label, data) in zip(axes.flat, entries):
        group_title(ax, data, label, pad_size)
    for ax in list(axes.flat)[len(entries):]:
        ax.axis("off")
    fig.suptitle(title, fontproperties=font, fontsize=21, x=.045, y=.965,
                 ha="left", color="#152839", fontweight="bold")
    fig.text(.045, .026, footer, fontproperties=font, fontsize=10, color="#586d7e")
    fig.subplots_adjust(left=.045, right=.97, bottom=.075, top=.87, wspace=.25, hspace=.36)
    save_png(fig, output / name)


def render_nine(output, groups, locations, font):
    fig, ax = plt.subplots(figsize=(12, 13))
    for site, (x, y) in locations.items():
        key = "MC" if site == "MC" else site[0]
        data = groups[key]
        paint(ax, data, (x, y), pad_size=.6, label_size=6)
        w, h = size(data[0])
        title = site + (" · P2545" if key == "P" else " · MC06" if key == "MC" else "")
        ax.text(x + w / 2, y + h + 42, title, ha="center", va="bottom", fontsize=9)
    ax.set(aspect="equal", xlim=(-140, 6030), ylim=(-140, 6200), xlabel="µm", ylabel="µm")
    ax.spines[:].set_visible(False)
    fig.suptitle("Block V2 九组候选摆位与母控", fontproperties=font, fontsize=21,
                 x=.07, y=.96, ha="left", color="#152839", fontweight="bold")
    fig.text(.07, .025, "组内坐标取自各自 DEF。组间位置为示意摆位，橙点为 M10 信号接点。尚未做联合布线与验收。",
             fontproperties=font, fontsize=10, color="#586d7e")
    fig.subplots_adjust(left=.075, bottom=.085, top=.91, right=.98)
    save_png(fig, output / "nine-placement.png")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("inputs", type=Path, help="directory with <role>.def and pm.lef")
    parser.add_argument("output", type=Path)
    parser.add_argument("--font", type=Path, required=True, help="Chinese-capable font file")
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_bytes())
    args.output.mkdir(parents=True, exist_ok=True)
    font = FontProperties(fname=args.font)
    bank = checked_path(args.inputs / "pm.lef", manifest["pm_bank"]["sha256"])
    w, h = re.search(r"\bSIZE ([\d.]+) BY ([\d.]+)", bank.read_text()).groups()
    bank_dimensions = {"s_sram_256x128_freepdk45": ("PM bank", (float(w), float(h)))}
    dimensions = dict(bank_dimensions)
    leaves = {}
    for name, entry in manifest["leaf_macros"].items():
        path = checked_path(args.inputs / f"{name}.def", entry["sha256"])
        data = read_def(path, bank_dimensions)
        dimensions[entry["label"]] = name, size(data[0])
        leaves[name] = data
    groups = {}
    for name, entry in manifest["groups"].items():
        path = checked_path(args.inputs / f"{name}.def", entry["sha256"])
        groups[name] = read_def(path, dimensions)
        if len(groups[name][3]) != entry["m10_pins"] or len(groups[name][1]) != entry["macro_count"]:
            raise ValueError(f"{name}: pin or macro count mismatch")
    render_panels(args.output, "blocks-m10.png", "Block V2 五类窄口候选与母控",
                  "彩色为独立叶宏和程序 SRAM，灰点为已摆放单元，橙点为 M10 信号接点。虚线为验收夹具外接范围。",
                  [(entry["label"], groups[key]) for key, entry in manifest["groups"].items()],
                  font, 3, (16, 9), 2.1)
    render_panels(args.output, "leaf-macros-m10.png", "Block V2 对应独立叶宏",
                  "使用独立叶宏 DEF。N32 为底层逻辑对应的独立交付，U39 中的 N32 接点修订以 U39 回执为准。",
                  list(leaves.items()), font, 3, (15, 12), 2.1)
    render_nine(args.output, groups, manifest["nine_group_locations_um"], font)
    for name, data in {**groups, **leaves}.items():
        print(name, size(data[0]), len(data[1]), len(data[2]), len(data[3]))


if __name__ == "__main__":
    main()
