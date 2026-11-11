from html import escape
from pathlib import Path
import xml.etree.ElementTree as ET

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch
from matplotlib.path import Path as PlotPath


INK = "#162A38"
BLUE = "#154D73"
BLUE_BG = "#EAF2F8"
OCHRE = "#89501C"
OCHRE_BG = "#FAF0E5"
GRAY = "#465D6C"
LINE = "#C2D0D8"
PANEL = "#F6F9FA"


class Diagram:
    def __init__(self, page, name, width, height):
        self.page = page
        self.name = name
        self.fig = plt.figure(figsize=(7.25, 7.25 * height / width), facecolor="white")
        self.ax = self.fig.add_axes([0, 0, 1, 1], xlim=(0, width), ylim=(height, 0))
        self.ax.set_axis_off()
        self.scale = 522 / width
        self.model = ET.Element("mxGraphModel", page="1", pageWidth=str(width), pageHeight=str(height),
                                grid="0", arrows="1", connect="1", background="#FFFFFF")
        self.cells = ET.SubElement(self.model, "root")
        ET.SubElement(self.cells, "mxCell", id="0")
        ET.SubElement(self.cells, "mxCell", id="1", parent="0")
        self.boxes = {}

    def vertex(self, key, value, style, bounds):
        node = ET.SubElement(self.cells, "mxCell", id=key, value=value, style=style,
                             vertex="1", parent="1")
        geometry = dict(zip(("x", "y", "width", "height"), map(str, bounds)))
        ET.SubElement(node, "mxGeometry", {**geometry, "as": "geometry"})

    def print_text(self, key, x, y, content, *, size, color, align, bold, mono=False):
        artist = self.ax.text(x, y, content, va="center", ha=align, fontsize=size * self.scale,
                              color=color, weight="bold" if bold else "normal",
                              family="DejaVu Sans Mono" if mono else "DejaVu Sans",
                              zorder=4)
        artist.set_gid(key)

    def text(self, key, x, y, content, *, size=17, color=INK, align="left", bold=False,
             mono=False, width=400):
        self.print_text(key, x, y, content, size=size, color=color, align=align, bold=bold, mono=mono)
        left = x - width / 2 if align == "center" else x
        family = "DejaVu Sans Mono" if mono else "DejaVu Sans"
        style = (f"text;html=1;align={align};verticalAlign=middle;spacing=0;overflow=visible;"
                 f"fontFamily={family};fontSize={size};fontColor={color};fontStyle={int(bold)};")
        self.vertex(key, escape(content), style, (left, y - size, width, 2 * size))

    def box(self, key, x, y, width, height, title="", detail="", *, stroke=BLUE, fill=BLUE_BG,
            size=20, bold=True):
        rect = FancyBboxPatch((x, y), width, height, boxstyle="round,pad=0,rounding_size=8",
                              edgecolor=stroke, facecolor=fill, linewidth=0.82, zorder=1)
        self.ax.add_patch(rect)
        rect.set_gid(key)
        self.boxes[key] = (x, y, width, height)
        if title:
            self.print_text(key + "-title", x + width / 2, y + height * (0.35 if detail else 0.5),
                            title, size=size, color=INK, align="center", bold=bold)
        if detail:
            self.print_text(key + "-detail", x + width / 2, y + height * 0.71, detail,
                            size=size * 0.79, color=stroke, align="center", bold=False)
        value = f"<b>{escape(title)}</b>" if bold else escape(title)
        if detail:
            value += f'<br><span style="font-size:{size * 0.79:g}px;color:{stroke}">{escape(detail)}</span>'
        style = (f"rounded=1;arcSize=12;whiteSpace=wrap;html=1;align=center;verticalAlign=middle;"
                 f"strokeColor={stroke};fillColor={fill};fontColor={INK};fontFamily=DejaVu Sans;"
                 f"fontSize={size};spacing=0;")
        self.vertex(key, value, style, (x, y, width, height))

    def edge(self, key, points, *, source=None, target=None, color=BLUE, dashed=False,
             direction="forward"):
        path = PlotPath(points, [PlotPath.MOVETO] + [PlotPath.LINETO] * (len(points) - 1))
        style = {"forward": "-|>", "both": "<|-|>", "none": "-"}[direction]
        artist = FancyArrowPatch(path=path, arrowstyle=style, mutation_scale=7,
                                 color=color, linewidth=0.96, zorder=3,
                                 linestyle=(0, (3, 2)) if dashed else "-")
        self.ax.add_patch(artist)
        artist.set_gid(key)
        drawing_style = (f"edgeStyle=none;rounded=0;html=1;strokeColor={color};strokeWidth=2;"
                         f"dashed={int(dashed)};startArrow={'block' if direction == 'both' else 'none'};"
                         f"endArrow={'none' if direction == 'none' else 'block'};")
        attributes = {"id": key, "edge": "1", "parent": "1"}
        for prefix, side, vertex, point in (("exit", "source", source, points[0]),
                                            ("entry", "target", target, points[-1])):
            if vertex is not None:
                x, y, width, height = self.boxes[vertex]
                px, py = point
                drawing_style += (f"{prefix}X={(px - x) / width:g};"
                                  f"{prefix}Y={(py - y) / height:g};{prefix}Perimeter=0;")
                attributes[side] = vertex
        cell = ET.SubElement(self.cells, "mxCell", {**attributes, "style": drawing_style})
        geometry = ET.SubElement(cell, "mxGeometry", {"relative": "1", "as": "geometry"})
        if source is None:
            ET.SubElement(geometry, "mxPoint", {"x": str(points[0][0]), "y": str(points[0][1]),
                                               "as": "sourcePoint"})
        if target is None:
            ET.SubElement(geometry, "mxPoint", {"x": str(points[-1][0]), "y": str(points[-1][1]),
                                               "as": "targetPoint"})
        if len(points) > 2:
            waypoints = ET.SubElement(geometry, "Array", {"as": "points"})
            for x, y in points[1:-1]:
                ET.SubElement(waypoints, "mxPoint", x=str(x), y=str(y))

    def save(self, output, workbook):
        self.fig.savefig(output / (self.name + ".svg"), metadata={"Date": None})
        self.fig.savefig(output / (self.name + ".png"), dpi=220)
        plt.close(self.fig)
        page = ET.SubElement(workbook, "diagram", id=self.name, name=self.page)
        page.append(self.model)


def architecture():
    d = Diagram("1 - Base and P control", "control-architecture", 1200, 742)
    d.text("base-heading", 38, 36, "(a)  NoPool base candidate", size=27, bold=True, width=600)
    d.box("mother", 40, 73, 317, 62, "Mother controller", "Program memory and task tokens")
    d.box("shared-dma", 728, 73, 214, 62, "Shared DMA")
    d.box("external-ddr", 1000, 73, 160, 62, "Off-chip DDR")
    d.edge("memory-link", [(942, 104), (1000, 104)], source="shared-dma", target="external-ddr",
           color=OCHRE, direction="both")
    d.text("calls-label", 451, 151, "Calls and terminal replies", color=BLUE)
    d.edge("mc-control-trunk", [(198, 135), (198, 178)], source="mother", direction="none")
    d.edge("control-trunk", [(96, 178), (1096, 178)], direction="none")
    d.box("product-data-paths", 40, 291, 1120, 45, "Product-bound data paths",
          stroke=OCHRE, fill=OCHRE_BG)
    for index, name in enumerate(("P0", "P1", "P2", "U0", "U1", "C0", "F0", "J0", "J1")):
        x = 42 + 125 * index
        center = x + 54
        is_p = name.startswith("P")
        d.box(name, x, 205, 108, 49, name, stroke=BLUE if is_p else LINE,
              fill=BLUE_BG if is_p else PANEL)
        d.edge("control-" + name, [(center, 178), (center, 205)], target=name, direction="both")
        d.edge("data-" + name, [(center, 254), (center, 291)], source=name,
               target="product-data-paths", color=OCHRE, dashed=True, direction="none")
    d.edge("dma-data-path", [(835, 135), (835, 151), (1179, 151), (1179, 313), (1160, 313)],
           source="shared-dma", target="product-data-paths", color=OCHRE, dashed=True, direction="none")

    d.text("p-detail-heading", 38, 385, "(b)  Control inside one P Block", size=27, bold=True, width=800)
    d.box("p-detail-frame", 40, 416, 1120, 291, stroke=LINE, fill=PANEL)
    d.box("mc-port", 61, 442, 175, 54, "MC port")
    d.box("p-lc", 354, 442, 246, 54, "P local controller")
    d.box("p-program", 831, 442, 280, 54, "Program memory")
    d.edge("p-call-return", [(236, 469), (354, 469)], source="mc-port", target="p-lc", direction="both")
    d.text("p-call-return-label", 295, 453, "Call / reply", color=BLUE, size=14, align="center", width=107)
    d.edge("p-pm-fetch", [(600, 469), (831, 469)], source="p-lc", target="p-program", direction="both")
    d.text("p-pm-fetch-label", 714, 453, "Fetch", color=BLUE, size=14, align="center", width=90)
    d.box("p-descriptor-dma", 61, 531, 175, 54, "Scope DMA", stroke=OCHRE, fill=OCHRE_BG)
    d.edge("p-descriptor-fetch", [(236, 558), (298, 558), (298, 486), (354, 486)],
           source="p-descriptor-dma", target="p-lc", color=OCHRE, direction="both")
    d.box("p-service", 354, 531, 444, 54, "Scope and service logic")
    d.edge("p-scope-service", [(477, 496), (477, 531)], source="p-lc", target="p-service", direction="both")
    d.text("p-scope-service-label", 494, 515, "Scope / done", color=BLUE, size=14, width=125)

    d.box("macro-m", 61, 632, 244, 55, "M", "Matrix compute", stroke=OCHRE, fill=OCHRE_BG)
    d.box("macro-s", 454, 632, 244, 55, "S", "Private SRAM", stroke=OCHRE, fill=OCHRE_BG)
    d.box("macro-g", 867, 632, 244, 55, "G", "Activation and gate", stroke=OCHRE, fill=OCHRE_BG)
    d.edge("p-m-service", [(403, 585), (183, 632)], source="p-service", target="macro-m", direction="both")
    d.edge("p-s-service", [(576, 585), (576, 632)], source="p-service", target="macro-s",
           color=OCHRE, direction="both")
    d.edge("p-g-service", [(748, 585), (989, 632)], source="p-service", target="macro-g",
           dashed=True, direction="both")
    d.edge("p-g-private-data", [(698, 659), (867, 659)], source="macro-s", target="macro-g",
           color=OCHRE, dashed=True, direction="both")
    return d


ISA_ROWS = (
    ("Dispatch", (("G_CALL", "Launch target with a token"),),
     (("L_EXEC", "Invoke a local service"),)),
    ("Synchronization", (("G_WAIT", "Wait for selected tokens"),
                         ("G_EVENT", "Consume READY and capture scalar")),
     (("L_WAIT", "Wait for local completion"),)),
    ("Arguments", (("G_MOVI", "Load a 32-bit immediate"),
                   ("G_ADDI64", "Add to a 64-bit register pair")), ()),
    ("Program flow", (("G_JNZ", "Select one of two forward PCs"),
                      ("G_LOOP", "Repeat with a bounded counter"),
                      ("G_END", "Finish the MC program")),
     (("L_END", "Release scope and reply"),)),
)


def isa_table(d):
    d.text("isa-heading", 36, 36, "(a)  Four instruction classes", size=28, bold=True, width=760)
    d.text("mc-column", 243, 73, "Native MC v3 · 8 opcodes", size=20, bold=True, width=410)
    d.text("lc-column", 885, 73, "Native P LC · 3 opcodes", size=20, bold=True, width=390)
    top = 97
    for index, ((category, mc, lc), height) in enumerate(zip(ISA_ROWS, (42, 62, 62, 82))):
        d.box(f"class-{index}", 36, top, 1328, height - 4, stroke=LINE, fill=PANEL)
        d.text(f"class-{index}-name", 52, top + (height - 4) / 2, category,
               size=19, bold=True, width=182)
        for x, ops in ((243, mc), (885, lc)):
            for row, (op, description) in enumerate(ops):
                y = top + 18 + 21 * row
                d.text("isa-" + op, x, y, op, size=18, color=BLUE, mono=True, width=145)
                d.text("isa-" + op + "-action", x + 143, y, description, size=18, width=340)
        top += height


STAGES = (
    ("A", "Norm", "U0"),
    ("B", "Gate proj.", "P0"),
    ("C", "Up proj.", "P1"),
    ("D", "SiLU × Up", "P0"),
    ("E", "Down proj.", "P2"),
    ("F", "Add residual", "J0"),
)
PARALLEL = (
    "G_CALL A,t0  →  G_WAIT 0x01",
    "G_CALL B,t1  →  G_CALL C,t2  →  G_WAIT 0x06",
    "G_CALL D,t3  →  G_WAIT 0x08",
    "G_CALL E,t4  →  G_WAIT 0x10",
    "G_CALL F,t5  →  G_WAIT 0x20  →  G_END",
)
SERIAL = (
    "G_CALL A,t0  →  G_WAIT 0x01",
    "G_CALL B,t1  →  G_WAIT 0x02",
    "G_CALL C,t2  →  G_WAIT 0x04",
    "G_CALL D,t3  →  G_WAIT 0x08",
    "G_CALL E,t4  →  G_WAIT 0x10",
    "G_CALL F,t5  →  G_WAIT 0x20  →  G_END",
)


def graph(d, prefix, x, shared):
    positions = {"X": (0, 478, 60), "A": (83, 478, 75),
                 "B": (184, 422, 102), "C": (184, 534, 102),
                 "D": (315, 478, 91), "E": (433, 478, 95), "F": (554, 478, 101)}
    for stage, name, target in STAGES:
        dx, y, width = positions[stage]
        if shared and stage == "C":
            target = "P0"
        d.box(prefix + stage, x + dx, y, width, 55, stage + " · " + target, name, size=19)
    d.box(prefix + "X", x, 478, 60, 55, "x", "Input", size=18, stroke=OCHRE, fill=OCHRE_BG)
    for src, dst, ys, yd in (
        ("X", "A", 506, 506), ("A", "B", 493, 450), ("A", "C", 518, 562),
        ("B", "D", 450, 493), ("C", "D", 562, 518),
        ("D", "E", 506, 506), ("E", "F", 506, 506),
    ):
        sx, _, sw = positions[src]
        tx, _, _ = positions[dst]
        d.edge(prefix + src + "-to-" + dst, [(x + sx + sw, ys), (x + tx, yd)],
               source=prefix + src, target=prefix + dst)
    d.edge(prefix + "residual", [(x + 30, 533), (x + 30, 619), (x + 606, 619), (x + 606, 533)],
           source=prefix + "X", target=prefix + "F", color=OCHRE, dashed=True)
    d.text(prefix + "residual-label", x + 350, 604, "Residual x", size=15, color=OCHRE,
           align="center", width=135)
    if shared:
        d.edge(prefix + "same-target", [(x + 235, 477), (x + 235, 534)],
               source=prefix + "B", target=prefix + "C", color=GRAY, dashed=True)
        d.text(prefix + "same-target-label", x + 247, 507, "Reuse P0", size=14, color=GRAY, width=80)


def instruction_topologies():
    d = Diagram("2 - ISA and FFN mappings", "instruction-topologies", 1400, 989)
    isa_table(d)
    d.text("mapping-heading", 36, 377, "(b)  Gated FFN with residual · two Block mappings",
           size=28, bold=True, width=1000)
    for prefix, x, title, program, shared in (
        ("dual-", 37, "Separate projection targets", PARALLEL, False),
        ("shared-", 709, "Shared projection target", SERIAL, True),
    ):
        d.text(prefix + "heading", x, 410, title, size=22, bold=True, width=500)
        graph(d, prefix, x, shared)
        d.box(prefix + "program", x, 644, 655, 235, stroke=LINE, fill=PANEL)
        d.text(prefix + "program-title", x + 21, 668, "MC issue order", size=19, bold=True, width=400)
        for index, line in enumerate(program):
            d.text(prefix + f"step-{index}", x + 22, 704 + 29 * index, line,
                   size=18, mono=True, width=610)
    d.text("descriptor-setup", 700, 914,
           "G_MOVI loads the first descriptor address · G_ADDI64 advances it before each later call",
           size=18, align="center", width=1300, color=GRAY)
    d.text("local-flow", 700, 947, "Native P scope: L_EXEC → L_WAIT → L_END",
           size=18, align="center", width=800, color=BLUE)
    return d


if __name__ == "__main__":
    plt.rcParams.update({"svg.fonttype": "none", "svg.hashsalt": "dac-control-figures"})
    output = Path(__file__).resolve().parent
    workbook = ET.Element("mxfile", host="app.diagrams.net", compressed="false")
    for draw in (architecture, instruction_topologies):
        draw().save(output, workbook)
    if hasattr(ET, "indent"):
        ET.indent(workbook, space="  ")
    ET.ElementTree(workbook).write(output / "control-figures.drawio", encoding="utf-8", xml_declaration=True)
