from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch


INK = "#152636"
BLUE = "#174E77"
BLUE_BG = "#EAF2F8"
OCHRE = "#86501F"
OCHRE_BG = "#FBF1E6"
GRAY = "#495D6F"
LINE = "#C4CFD7"


def box(ax, x, y, width, height, title, details, edge=BLUE, face=BLUE_BG):
    ax.add_patch(FancyBboxPatch(
        (x, y), width, height, boxstyle="round,pad=0,rounding_size=9",
        linewidth=0.85, edgecolor=edge, facecolor=face,
    ))
    ax.text(x + width / 2, y + height * 0.64, title, ha="center", va="center",
            fontsize=9, weight="semibold", color=INK)
    ax.text(x + width / 2, y + height * 0.29, details, ha="center", va="center",
            fontsize=7.7, color=edge, linespacing=1.25)


def arrow(ax, start, end, *, color=BLUE, both=False, bend=0):
    ax.add_patch(FancyArrowPatch(
        start, end, arrowstyle="<|-|>" if both else "-|>", mutation_scale=8,
        linewidth=1.0, color=color, shrinkA=0, shrinkB=0,
        connectionstyle=f"arc3,rad={bend}",
    ))


def label(ax, x, y, message, *, color=GRAY, align="left"):
    ax.text(x, y, message, ha=align, va="center", fontsize=7.7, color=color)


def draw():
    plt.rcParams.update({
        "font.family": "DejaVu Sans", "svg.fonttype": "none",
        "svg.hashsalt": "dac-control-figure-1",
    })
    fig = plt.figure(figsize=(7.2, 3.65), facecolor="white")
    ax = fig.add_axes([0, 0, 1, 1], xlim=(0, 1030), ylim=(0, 510))
    ax.set_axis_off()
    ax.plot([514, 514], [31, 478], color=LINE, linewidth=0.8)
    ax.text(26, 474, "(a)  Control architecture", fontsize=10.5, weight="bold", color=INK)
    ax.text(545, 474, "(b)  Program execution", fontsize=10.5, weight="bold", color=INK)

    box(ax, 40, 364, 248, 73, "Mother controller (MC)", "64-bit ISA · program memory")
    box(ax, 40, 210, 248, 76, "Local controller ×3", "64-bit program kernel")
    box(ax, 40, 53, 248, 76, "P service ×3", "Range execution · private S")
    box(ax, 330, 130, 160, 76, "Shared DMA", "Two channels", OCHRE, OCHRE_BG)
    arrow(ax, (164, 364), (164, 286), both=True)
    label(ax, 177, 335, "Call / terminal reply")
    label(ax, 177, 312, "4 × 128-bit flits")
    arrow(ax, (164, 210), (164, 129), both=True)
    label(ax, 177, 179, "Invoke / complete")
    label(ax, 177, 155, "Owner + ticket")
    arrow(ax, (288, 243), (391, 206), color=OCHRE, both=True, bend=-0.09)
    label(ax, 348, 254, "Descriptors", color=OCHRE)
    arrow(ax, (288, 92), (391, 130), color=OCHRE, both=True, bend=0.09)
    label(ax, 347, 83, "Weights", color=OCHRE)

    label(ax, 550, 434, "MC · one iteration", color=BLUE)
    label(ax, 815, 434, "LC · one call", color=BLUE)
    box(ax, 550, 335, 223, 72, "G_CALL ×3", "G_ADDI64 after each call")
    box(ax, 815, 335, 188, 72, "L_EXEC", "Fetch scope, invoke P")
    box(ax, 550, 211, 223, 72, "G_WAIT 0x7", "Wait for all three tokens")
    box(ax, 815, 211, 188, 72, "L_WAIT", "Wait for P completion")
    box(ax, 550, 87, 223, 72, "G_LOOP", "Repeat, then G_END")
    box(ax, 815, 87, 188, 72, "L_END", "Release scope, reply")
    arrow(ax, (661, 335), (661, 283))
    arrow(ax, (661, 211), (661, 159))
    arrow(ax, (909, 335), (909, 283))
    arrow(ax, (909, 211), (909, 159))
    arrow(ax, (773, 371), (815, 371))
    arrow(ax, (815, 123), (773, 237), bend=-0.12)
    label(ax, 550, 52, "272 B MC image · 352 B per LC image")
    return fig


if __name__ == "__main__":
    directory = Path(__file__).resolve().parent
    figure = draw()
    figure.savefig(directory / "control-architecture.svg", metadata={"Date": None})
    figure.savefig(directory / "control-architecture.png", dpi=200)
