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


def panel(ax, x, y, width, height, edge, face):
    ax.add_patch(FancyBboxPatch(
        (x, y), width, height, boxstyle="round,pad=0,rounding_size=9",
        linewidth=0.85, edgecolor=edge, facecolor=face,
    ))


def box(ax, x, y, width, height, title, details, edge=BLUE, face=BLUE_BG):
    panel(ax, x, y, width, height, edge, face)
    ax.text(x + width / 2, y + height * 0.64, title, ha="center", va="center",
            fontsize=8.8, weight="semibold", color=INK)
    ax.text(x + width / 2, y + height * 0.29, details, ha="center", va="center",
            fontsize=7.2, color=edge, linespacing=1.25)


def arrow(ax, start, end, *, color=BLUE, both=False):
    ax.add_patch(FancyArrowPatch(
        start, end, arrowstyle="<|-|>" if both else "-|>", mutation_scale=8,
        linewidth=1.0, color=color, shrinkA=0, shrinkB=0,
    ))


def label(ax, x, y, message, *, color=GRAY, align="left"):
    ax.text(x, y, message, ha=align, va="center", fontsize=7.7, color=color)


def canvas():
    fig = plt.figure(figsize=(7.2, 3.65), facecolor="white")
    ax = fig.add_axes([0, 0, 1, 1], xlim=(0, 1000), ylim=(0, 500))
    ax.set_axis_off()
    return fig, ax


def heading(ax, x, y, message):
    ax.text(x, y, message, va="center", fontsize=10.5, weight="bold", color=INK)


def draw_hierarchy():
    fig, ax = canvas()
    heading(ax, 36, 459, "Inter-Block scheduling")
    box(ax, 230, 355, 540, 72, "Mother controller (MC)",
        "Select targets · dispatch scopes · synchronize completion tokens")

    ax.plot([36, 964], [292, 292], color=LINE, linewidth=0.8, linestyle=(0, (4, 3)))
    label(ax, 500, 324, "G_CALL / terminal reply", color=BLUE, align="center")
    heading(ax, 36, 267, "Intra-Block scheduling")
    panel(ax, 36, 34, 590, 201, LINE, "#F9FBFC")
    panel(ax, 659, 34, 305, 201, LINE, "#F9FBFC")
    label(ax, 56, 216, "P Block", color=INK)
    label(ax, 845, 216, "Another Block", color=INK, align="center")

    box(ax, 56, 137, 550, 59, "Local controller (LC)", "Fetch descriptor · invoke service · wait for completion")
    box(ax, 680, 137, 263, 59, "Local controller (LC)", "Run the Block's service")
    arrow(ax, (365, 355), (365, 196), both=True)
    arrow(ax, (731, 355), (731, 196), both=True)

    panel(ax, 46, 42, 570, 68, LINE, "white")
    box(ax, 56, 51, 158, 49, "Operand supply", "Local S + weights", OCHRE, OCHRE_BG)
    box(ax, 253, 51, 155, 49, "Compute", "M sub-macro", OCHRE, OCHRE_BG)
    box(ax, 448, 51, 158, 49, "Writeback", "Write ACKs", OCHRE, OCHRE_BG)
    box(ax, 680, 51, 263, 49, "Local service", "Sub-macros and local state", OCHRE, OCHRE_BG)
    arrow(ax, (330, 137), (330, 110), both=True)
    arrow(ax, (812, 137), (812, 101), both=True)
    arrow(ax, (215, 75), (252, 75), color=OCHRE)
    arrow(ax, (409, 75), (447, 75), color=OCHRE)
    return fig


def graph_node(ax, x, y, name):
    panel(ax, x - 36, y - 22, 72, 44, BLUE, BLUE_BG)
    ax.text(x, y, name, ha="center", va="center", weight="bold", fontsize=9, color=INK)


def schedule(ax, x, lines):
    panel(ax, x, 76, 424, 240, LINE, "#F9FBFC")
    label(ax, x + 23, 293, "MC instruction sequence", color=INK)
    for index, (opcode, operands) in enumerate(lines):
        y = 257 - 30 * index
        color = OCHRE if opcode == "G_WAIT" else BLUE
        ax.text(x + 24, y, opcode, va="center", family="DejaVu Sans Mono", fontsize=8.2, color=color)
        ax.text(x + 159, y, operands, va="center", family="DejaVu Sans Mono", fontsize=8.2, color=INK)


def draw_topologies():
    fig, ax = canvas()
    ax.plot([500, 500], [77, 469], color=LINE, linewidth=0.8)
    heading(ax, 38, 459, "(a)  Dependent chain")
    heading(ax, 538, 459, "(b)  Parallel producers")

    for x, name in ((108, "A"), (250, "B"), (392, "C")):
        graph_node(ax, x, 382, name)
    arrow(ax, (144, 382), (214, 382))
    arrow(ax, (286, 382), (356, 382))

    graph_node(ax, 655, 411, "A")
    graph_node(ax, 655, 353, "B")
    graph_node(ax, 870, 382, "C")
    arrow(ax, (691, 411), (834, 390))
    arrow(ax, (691, 353), (834, 374))

    schedule(ax, 38, [
        ("G_CALL", "A, t0"), ("G_WAIT", "0x1"),
        ("G_CALL", "B, t1"), ("G_WAIT", "0x2"),
        ("G_CALL", "C, t2"), ("G_WAIT", "0x4"),
    ])
    schedule(ax, 538, [
        ("G_CALL", "A, t0"), ("G_CALL", "B, t1"), ("G_WAIT", "0x3"),
        ("G_CALL", "C, t2"), ("G_WAIT", "0x4"),
    ])
    label(ax, 500, 45, "Same opcodes and service interface · Deployment binds each data edge", align="center")
    return fig


if __name__ == "__main__":
    plt.rcParams.update({
        "font.family": "DejaVu Sans", "svg.fonttype": "none",
        "svg.hashsalt": "dac-control-figures",
    })
    directory = Path(__file__).resolve().parent
    for name, draw in (
        ("control-architecture", draw_hierarchy),
        ("instruction-topologies", draw_topologies),
    ):
        figure = draw()
        figure.savefig(directory / (name + ".svg"), metadata={"Date": None})
        figure.savefig(directory / (name + ".png"), dpi=200)
        plt.close(figure)
