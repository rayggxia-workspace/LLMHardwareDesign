"""Draw actual independent fixture placements from qualified delivery archives.

Usage: python -B plot64.py OUTPUT.png accepted-c_64.tar.gz ...
Gray dots are placed standard cells excluding fillers/taps, not area estimates.
"""
import io
import json
from pathlib import Path
import re
import sys
import tarfile

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
from matplotlib.patches import Rectangle

output = Path(sys.argv[1])
archives = [Path(p) for p in sys.argv[2:]]
assert archives
font_path = Path("C:/Windows/Fonts/msyh.ttc")
font = FontProperties(fname=str(font_path)) if font_path.exists() else None
colors = {"R": "#8db5e3", "G": "#f3cb76", "E": "#e9a4a4", "S": "#9bd2b1", "T": "#c2addd"}
datasets = []
for archive in archives:
    with tarfile.open(archive, "r:gz") as tar:
        inventory = json.load(tar.extractfile("physical/inventory.json"))
        hard = {x["master"] for x in inventory["instances"].values()}
        points = []
        components = False
        units = None
        for line in io.TextIOWrapper(tar.extractfile("native/6_final.def")):
            if line.startswith("UNITS DISTANCE MICRONS"):
                units = int(line.split()[3])
            if line.startswith("COMPONENTS "):
                components = True
            elif line.startswith("END COMPONENTS"):
                break
            elif components:
                match = re.match(r"\s*-\s+(\S+)\s+(\S+).*?\+\s+(?:PLACED|FIXED)\s+\(\s*(\d+)\s+(\d+)\s*\)", line)
                if not match:
                    continue
                _, master, x, y = match.groups()
                if master in hard or master.startswith(("FILLCELL", "TAPCELL")):
                    continue
                points.append((int(x) / units, int(y) / units))
        assert units and points
        datasets.append((inventory, points))

widths = [d[0]["size_um"][0] for d in datasets]
fig, axes = plt.subplots(1, len(datasets), figsize=(17, 5.5), squeeze=False,
                         gridspec_kw={"width_ratios": widths})
for ax, (inventory, points) in zip(axes[0], datasets):
    width, height = inventory["size_um"]
    x, y = zip(*points)
    ax.scatter(x, y, s=0.3, c="#626b74", alpha=0.40, linewidths=0, rasterized=True)
    for name, instance in inventory["instances"].items():
        master = instance["master"]
        alias = {"local_s_base": "S", "block_v2_g": "G", "block_v2_e_compact": "E",
                 "transaction6k": "T", "r_stream_local": "R"}[master]
        left, bottom = instance["xy_um"]
        w, h = instance["size_um"]
        ax.add_patch(Rectangle((left, bottom), w, h, facecolor=colors[alias],
                               edgecolor="#354052", linewidth=1.0, zorder=3))
        label = "R256" if alias == "R" else "16 KiB S" if alias == "S" else alias
        size_label = f"{w:g}×{h:g}" if alias in ("G", "E") else f"{w:g} × {h:g} µm"
        ax.text(left + w / 2, bottom + h / 2, f"{label}\n{size_label}",
                ha="center", va="center", fontsize=8 if alias == "G" else 10 if alias == "E" else 11,
                color="#17202c", zorder=4)
    ax.add_patch(Rectangle((0, 0), width, height, fill=False, linestyle="--",
                           linewidth=1, edgecolor="#75808b"))
    ax.set(xlim=(-20, width + 20), ylim=(-20, height + 20), aspect="equal")
    ax.set_title(f"{inventory['kind'].upper()}_64 — {width:g} × {height:g} µm", fontsize=13)
    ax.set_xlabel("µm")
    ax.set_ylabel("µm")
    ax.spines[["top", "right", "left", "bottom"]].set_visible(False)
    ax.tick_params(length=0, labelsize=8)

groups = " / ".join(d[0]["kind"].upper() for d in datasets)
fig.suptitle(f"{groups}：独立叶宏与实际标准单元摆放", fontproperties=font, fontsize=17)
caption = "宏内尺寸单位：µm。灰点：宏外局控、适配/服务逻辑及物理修复单元（不含填充/tap）；虚线仅示验收夹具范围，不是硬块封装边界。"
if any(d[0]["kind"] == "j" for d in datasets):
    caption += "\nJ 的宏外服务逻辑包含三路汇合算术，需计入硬件资源。"
fig.text(0.5, 0.055, caption, ha="center", fontproperties=font, fontsize=9, color="#46515e")
fig.subplots_adjust(top=0.87, bottom=0.18, left=0.045, right=0.985, wspace=0.13)
output.parent.mkdir(parents=True, exist_ok=True)
fig.savefig(output, dpi=180, facecolor="white")
plt.close(fig)
print(output)
