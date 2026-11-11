from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch


INK = "#162A38"
BLUE = "#154D73"
BLUE_BG = "#EAF2F8"
OCHRE = "#89501C"
OCHRE_BG = "#FAF0E5"
GRAY = "#465D6C"
LINE = "#C2D0D8"
PANEL = "#F6F9FA"


def canvas():
    fig = plt.figure(figsize=(7.25, 5.35), facecolor="white")
    ax = fig.add_axes([0, 0, 1, 1], xlim=(0, 1000), ylim=(0, 730))
    ax.set_axis_off()
    return fig, ax


def label(ax, x, y, message, *, size=7.4, color=INK, align="left", weight="normal", mono=False):
    ax.text(x, y, message, ha=align, va="center", fontsize=size, color=color,
            weight=weight, family="DejaVu Sans Mono" if mono else "DejaVu Sans")


def heading(ax, x, y, message):
    label(ax, x, y, message, size=10.2, weight="bold")


def panel(ax, x, y, width, height, edge=LINE, face=PANEL):
    ax.add_patch(FancyBboxPatch(
        (x, y), width, height, boxstyle="round,pad=0,rounding_size=7",
        linewidth=0.8, edgecolor=edge, facecolor=face,
    ))


def box(ax, x, y, width, height, title, details, edge=BLUE, face=BLUE_BG):
    panel(ax, x, y, width, height, edge, face)
    label(ax, x + width / 2, y + height * 0.65, title,
          size=8.6, align="center", weight="bold")
    label(ax, x + width / 2, y + height * 0.29, details,
          size=7, color=edge, align="center")


def line(ax, xs, ys, *, color=BLUE, dashed=False):
    style = (0, (3, 2)) if dashed else "-"
    ax.plot(xs, ys, color=color, linewidth=0.95, linestyle=style)


def arrow(ax, start, end, *, color=BLUE, both=False, dashed=False):
    style = (0, (3, 2)) if dashed else "-"
    ax.add_patch(FancyArrowPatch(
        start, end, arrowstyle="<|-|>" if both else "-|>", mutation_scale=7,
        linewidth=0.95, linestyle=style, color=color, shrinkA=0, shrinkB=0,
    ))


def block_inventory(ax):
    groups = [
        (36, 296, "P", ("P0", "P1", "P2")),
        (347, 190, "U", ("U0", "U1")),
        (552, 92, "C", ("C0",)),
        (659, 92, "F", ("F0",)),
        (766, 198, "J", ("J0", "J1")),
    ]
    line(ax, [184, 865], [550, 550])
    line(ax, [185, 185], [594, 550])
    label(ax, 508, 568, "Per-instance call and completion interfaces", color=BLUE, align="center")
    for x, width, kind, instances in groups:
        center = x + width / 2
        selected = kind == "P"
        panel(ax, x, 426, width, 95, BLUE if selected else LINE, BLUE_BG if selected else PANEL)
        label(ax, center, 503, f"{kind} ×{len(instances)}", size=8.6, align="center", weight="bold")
        arrow(ax, (center, 550), (center, 521), both=True)
        for index, instance in enumerate(instances):
            slot_width = (width - 18) / len(instances)
            slot_x = x + 9 + index * slot_width
            panel(ax, slot_x + 4, 441, slot_width - 8, 35, BLUE if selected else LINE, "white")
            label(ax, slot_x + slot_width / 2, 458, instance, size=8, align="center", weight="semibold")
        line(ax, [center, center], [426, 410], color=OCHRE, dashed=True)


def draw_hierarchy():
    fig, ax = canvas()
    heading(ax, 36, 700, "(a)  NoPool base candidate · five Block types, nine instances")
    box(ax, 36, 594, 298, 72, "Mother controller (MC)", "16 KiB program SRAM · task tokens")
    box(ax, 596, 594, 204, 72, "Shared typed DMA", "Two channels", OCHRE, OCHRE_BG)
    box(ax, 837, 594, 127, 72, "DDR", "Off-chip memory", OCHRE, OCHRE_BG)
    arrow(ax, (800, 630), (837, 630), color=OCHRE, both=True)
    block_inventory(ax)
    panel(ax, 36, 375, 928, 35, OCHRE, OCHRE_BG)
    label(ax, 500, 392, "Product-bound data paths · cross-Block transfers and DMA",
          color=OCHRE, align="center", weight="semibold")
    line(ax, [698, 698, 981, 981, 964], [594, 581, 581, 392, 392], color=OCHRE, dashed=True)

    heading(ax, 36, 337, "(b)  P Block detail · three leaf macros per instance")
    panel(ax, 36, 25, 928, 286)
    box(ax, 53, 227, 166, 60, "MC control port", "4 × 128-bit flits")
    box(ax, 333, 227, 204, 60, "P local controller", "64-bit scope kernel")
    box(ax, 664, 227, 279, 60, "LC program memory", "1 KiB in the native RTL profile")
    arrow(ax, (219, 257), (333, 257), both=True)
    label(ax, 276, 274, "Call / reply", size=6.8, color=BLUE, align="center")
    arrow(ax, (537, 257), (664, 257), both=True)
    label(ax, 600, 274, "Fetch / read", size=6.8, color=BLUE, align="center")

    box(ax, 53, 142, 178, 51, "Descriptor DMA", "Two 64 B reads", OCHRE, OCHRE_BG)
    arrow(ax, (333, 236), (231, 171), color=OCHRE, both=True)
    label(ax, 243, 211, "DMA reads", size=6.7, color=OCHRE, align="center")
    box(ax, 300, 137, 400, 56, "Scope and service logic", "Descriptor · range iterator · A/W feed · ACK tracking")
    arrow(ax, (435, 227), (435, 193), both=True)
    label(ax, 452, 211, "Scope / done", size=6.8, color=BLUE)
    arrow(ax, (325, 137), (166, 94), both=True)
    label(ax, 151, 126, "Command / result", size=6.7, color=BLUE)
    arrow(ax, (500, 137), (500, 94), color=OCHRE, both=True)
    label(ax, 514, 113, "Read / write ACK", size=6.7, color=OCHRE)
    arrow(ax, (676, 137), (829, 94), both=True, dashed=True)
    label(ax, 792, 126, "G service binding", size=6.7, color=BLUE)

    box(ax, 55, 42, 221, 52, "M ×1 · matrix engine", "K16 × N8 · W8/A16", OCHRE, OCHRE_BG)
    box(ax, 383, 42, 234, 52, "S ×1 · private SRAM", "16 KiB · four banks", OCHRE, OCHRE_BG)
    box(ax, 721, 42, 222, 52, "G32 ×1 · activation", "SiLU / gate multiplication", OCHRE, OCHRE_BG)
    arrow(ax, (617, 67), (721, 67), color=OCHRE, both=True, dashed=True)
    label(ax, 669, 84, "via adapter", size=6.2, color=OCHRE, align="center")
    return fig


ISA_ROWS = (
    ("Dispatch", (("G_CALL", "Launch a target with a token"),),
     (("L_EXEC", "Invoke a local service"),)),
    ("Synchronization", (("G_WAIT", "Wait for all selected tokens"),
                         ("G_EVENT", "Consume bound READY and latch scalar")),
     (("L_WAIT", "Wait for local completion"),)),
    ("Argument setup", (("G_MOVI", "Load a 32-bit immediate"),
                        ("G_ADDI64", "Add to a 64-bit register pair")), ()),
    ("Program flow", (("G_JNZ", "Branch forward if nonzero"),
                      ("G_LOOP", "Counted backward branch"),
                      ("G_END", "Finish the MC program")),
     (("L_END", "Release scope and reply"),)),
)


def isa_table(ax):
    heading(ax, 36, 700, "(a)  Four instruction classes in the illustrated 64-bit profiles")
    label(ax, 232, 660, "Native MC v3 · 8 opcodes", size=8.2, weight="bold")
    label(ax, 663, 660, "Native P LC · 3 opcodes", size=8.2, weight="bold")
    top = 643
    for (name, mc, lc), height in zip(ISA_ROWS, (46, 65, 65, 85)):
        bottom = top - height
        panel(ax, 36, bottom, 928, height - 4)
        label(ax, 50, bottom + (height - 4) / 2, name, size=7.7, weight="semibold")
        for x, ops in ((232, mc), (663, lc)):
            for index, (op, description) in enumerate(ops):
                y = top - 20 - index * 20
                label(ax, x, y, op, size=7.2, color=BLUE, mono=True)
                label(ax, x + 112, y, description, size=7)
        top = bottom


def graph_node(ax, x, y, name):
    panel(ax, x - 28, y - 14, 56, 28, BLUE, BLUE_BG)
    label(ax, x, y, name, size=8.2, align="center", weight="bold")


def schedule(ax, x, lines):
    panel(ax, x, 56, 444, 161)
    for index, (opcode, operands) in enumerate(lines):
        y = 202 - 21 * index
        color = OCHRE if opcode == "G_WAIT" else BLUE
        label(ax, x + 27, y, opcode, size=7.7, color=color, mono=True)
        label(ax, x + 168, y, operands, size=7.7, mono=True)


def draw_topologies():
    fig, ax = canvas()
    isa_table(ax)
    heading(ax, 36, 355, "(b)  Same ISA, different execution order")
    label(ax, 36, 331, "Common setup: G_MOVI initializes the descriptor pointer at dA (128 B stride)",
          color=GRAY)
    label(ax, 36, 302, "Dependent chain", size=8.4, weight="bold")
    label(ax, 520, 302, "Parallel producers", size=8.4, weight="bold")

    for x, name in ((115, "A"), (258, "B"), (401, "C")):
        graph_node(ax, x, 262, name)
    arrow(ax, (143, 262), (230, 262))
    arrow(ax, (286, 262), (373, 262))

    graph_node(ax, 669, 276, "A")
    graph_node(ax, 669, 238, "B")
    graph_node(ax, 866, 257, "C")
    arrow(ax, (697, 276), (838, 263))
    arrow(ax, (697, 238), (838, 251))

    schedule(ax, 36, [
        ("G_CALL", "A, t0"), ("G_WAIT", "0x1"),
        ("G_ADDI64", "r0, +128"), ("G_CALL", "B, t1"),
        ("G_WAIT", "0x2"), ("G_ADDI64", "r0, +128"), ("G_CALL", "C, t2"),
    ])
    schedule(ax, 520, [
        ("G_CALL", "A, t0"), ("G_ADDI64", "r0, +128"),
        ("G_CALL", "B, t1"), ("G_WAIT", "0x3"),
        ("G_ADDI64", "r0, +128"), ("G_CALL", "C, t2"),
    ])
    label(ax, 500, 34, "Common MC finish: G_WAIT 0x4 → G_END", color=GRAY, align="center")
    label(ax, 500, 14, "Each native P scope: L_EXEC → L_WAIT → L_END", color=BLUE, align="center")
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
        figure.savefig(directory / (name + ".png"), dpi=240)
        plt.close(figure)
