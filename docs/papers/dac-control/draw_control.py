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
            size=20, bold=True, ink=INK):
        detail_ink = GRAY if stroke == LINE else stroke
        if ink != INK:
            detail_ink = "#DEEAF2"
        rect = FancyBboxPatch((x, y), width, height, boxstyle="round,pad=0,rounding_size=8",
                              edgecolor=stroke, facecolor=fill, linewidth=0.82, zorder=1)
        self.ax.add_patch(rect)
        rect.set_gid(key)
        self.boxes[key] = (x, y, width, height)
        if title:
            self.print_text(key + "-title", x + width / 2, y + height * (0.35 if detail else 0.5),
                            title, size=size, color=ink, align="center", bold=bold)
        if detail:
            self.print_text(key + "-detail", x + width / 2, y + height * 0.71, detail,
                            size=size * 0.79, color=detail_ink, align="center", bold=False)
        value = f"<b>{escape(title)}</b>" if bold else escape(title)
        if detail:
            value += f'<br><span style="font-size:{size * 0.79:g}px;color:{detail_ink}">{escape(detail)}</span>'
        style = (f"rounded=1;arcSize=12;whiteSpace=wrap;html=1;align=center;verticalAlign=middle;"
                 f"strokeColor={stroke};fillColor={fill};fontColor={ink};fontFamily=DejaVu Sans;"
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
    d = Diagram("1 - Base and C control", "control-architecture", 1200, 867)
    d.text("base-heading", 38, 36, "(a)  NoPool base candidate", size=27, bold=True, width=600)
    d.box("mother", 397, 67, 385, 78, "Mother controller", "Program memory and task tokens",
          fill=BLUE, ink="#FFFFFF", size=26)
    d.box("shared-dma", 832, 77, 175, 59, "Shared DMA", stroke=LINE, fill=PANEL)
    d.box("external-ddr", 1040, 77, 120, 59, "DDR", "Off-chip", stroke=LINE, fill=PANEL)
    d.edge("memory-link", [(1007, 106), (1040, 106)], source="shared-dma", target="external-ddr",
           direction="both")
    d.text("calls-label", 93, 158, "Calls and terminal replies", color=BLUE)
    d.edge("mc-control-trunk", [(590, 145), (590, 178)], source="mother", direction="none")
    d.edge("control-trunk", [(96, 178), (1096, 178)], direction="none")
    d.box("product-data-paths", 40, 291, 1120, 45, "Product-bound data paths",
          stroke=OCHRE, fill=OCHRE_BG)
    for index, name in enumerate(("P0", "P1", "P2", "U0", "U1", "C0", "F0", "J0", "J1")):
        x = 42 + 125 * index
        center = x + 54
        selected = name == "C0"
        d.box(name, x, 205, 108, 49, name, stroke=BLUE if selected else LINE,
              fill=BLUE_BG if selected else PANEL)
        d.edge("control-" + name, [(center, 178), (center, 205)], target=name, direction="both")
        d.edge("data-" + name, [(center, 254), (center, 291)], source=name,
               target="product-data-paths", color=OCHRE, dashed=True, direction="none")
    d.edge("dma-data-path", [(920, 136), (920, 153), (1179, 153), (1179, 313), (1160, 313)],
           source="shared-dma", target="product-data-paths", color=OCHRE, dashed=True, direction="none")

    d.text("c-detail-heading", 38, 381, "(b)  Local controller and physical links inside C",
           size=27, bold=True, width=1020)
    d.box("c-detail-frame", 40, 410, 1120, 398, stroke=LINE, fill=PANEL)
    d.box("mc-port", 66, 452, 182, 57, "MC interface", stroke=BLUE, fill=BLUE_BG)
    d.box("c-lc", 373, 435, 417, 91, "C local controller", "Dispatch services · track completion",
          fill=BLUE, ink="#FFFFFF", size=28)
    d.box("c-program", 910, 452, 212, 57, "Program memory", stroke=LINE, fill="white", size=18)
    d.edge("c-call-return", [(248, 481), (373, 481)], source="mc-port", target="c-lc", direction="both")
    d.edge("c-pm-fetch", [(790, 481), (910, 481)], source="c-lc", target="c-program", direction="both")
    d.text("c-call-label", 310, 463, "Call / reply", color=BLUE, size=14, align="center", width=100)
    d.text("c-fetch-label", 850, 463, "Fetch", color=BLUE, size=14, align="center", width=95)
    d.box("c-service", 347, 562, 468, 53, "Local services and adapters",
          stroke=BLUE, fill=BLUE_BG)
    d.edge("c-lc-service", [(581, 526), (581, 562)], source="c-lc", target="c-service", direction="both")

    for key, title, detail, x, port in (
        ("s", "S", "Private SRAM", 66, 403),
        ("r", "R", "State service", 342, 526),
        ("g", "G", "Activation", 618, 648),
        ("e", "E", "Vector arithmetic", 918, 760),
    ):
        d.box("macro-" + key, x, 660, 205, 57, title, detail, stroke=LINE, fill="white")
        d.edge("c-service-" + key, [(port, 615), (x + 102.5, 660)],
               source="c-service", target="macro-" + key, direction="both")
    d.box("c-fixed-sram-paths", 66, 748, 1057, 42, "Fixed SRAM paths · S ↔ R/G/E via adapters",
          fill=BLUE_BG, size=18)
    for key in ("s", "r", "g", "e"):
        macro = "macro-" + key
        x, _, width, _ = d.boxes[macro]
        center = x + width / 2
        d.edge("c-sram-" + key, [(center, 717), (center, 748)], source=macro,
               target="c-fixed-sram-paths", direction="both")
    d.edge("c-g-to-e-product", [(823, 690), (918, 690)], source="macro-g", target="macro-e",
           color=OCHRE, dashed=True)
    d.text("c-g-to-e-label", 870.5, 674, "Bypass", size=15,
           color=OCHRE, align="center", width=85)
    for key, x, color, dashed, caption in (
        ("exchange", 60, BLUE, False, "Control and data exchange"),
        ("physical", 623, OCHRE, True, "Product-specific physical wiring"),
    ):
        d.edge("key-" + key, [(x, 837), (x + 42, 837)], color=color, dashed=dashed, direction="none")
        d.text("key-" + key + "-label", x + 54, 837, caption, size=16, color=color, width=470)
    return d


ISA_CLASSES = (
    ("Dispatch", "Start a task on a Block or invoke a service within a Block"),
    ("Synchronization", "Wait for required completions or consume a readiness event"),
    ("Argument setup", "Initialize parameters and advance descriptor addresses"),
    ("Program flow", "Select branches, repeat bounded loops, and finish execution"),
)


def isa_table(d):
    d.text("isa-heading", 36, 36, "(a)  Four instruction classes", size=28, bold=True, width=760)
    for index, (category, purpose) in enumerate(ISA_CLASSES):
        y = 67 + index * 43
        d.box(f"class-{index}", 36, y, 1328, 39, stroke=LINE, fill=PANEL)
        d.text(f"class-{index}-name", 52, y + 19.5, category, size=20, bold=True, width=220)
        d.text(f"class-{index}-purpose", 275, y + 19.5, purpose, size=20, width=1040)


PROJECTION_PHASE = "G_CALL Aq,t0 → G_CALL Ak,t1 → G_WAIT 0x03"
LLAMA_PROGRAM = (
    PROJECTION_PHASE,
    "G_CALL Cq,t2 → G_CALL Ck,t3 → G_WAIT 0x0C",
    "G_END",
)
QWEN_PROGRAM = (
    PROJECTION_PHASE,
    "G_CALL Bq,t2 → G_CALL Bk,t3 → G_WAIT 0x0C",
    "G_CALL Cq,t4 → G_CALL Ck,t5 → G_WAIT 0x30",
    "G_END",
)


def model_program(d, prefix, x, lines):
    d.box(prefix + "program", x, 505, 655, 148, stroke=LINE, fill=PANEL)
    d.text(prefix + "program-title", x + 20, 528, "MC issue order", size=18, bold=True, width=400)
    for index, text in enumerate(lines):
        d.text(prefix + f"step-{index}", x + 20, 555 + 26 * index, text,
               size=18, mono=True, width=610)


def qk_graph(d, prefix, x, normalize):
    d.box(prefix + "x", x, 394, 50, 52, "x", stroke=LINE, fill=PANEL)
    for branch, y, port_y, p, u in (
        ("q", 351, 407, "P0", "U0"),
        ("k", 427, 433, "P1", "U1"),
    ):
        a, b, c = (prefix + stage + branch for stage in "ABC")
        d.box(a, x + 93, y, 147, 60, f"A{branch} · {p}", f"{branch.upper()} projection")
        d.box(c, x + 492, y, 163, 60, f"C{branch} · {u}.E", f"{branch.upper()} RoPE")
        center = y + 30
        d.edge(prefix + "x-to-A" + branch, [(x + 50, port_y), (x + 93, center)],
               source=prefix + "x", target=a)
        if normalize:
            d.box(b, x + 287, y, 158, 60, f"B{branch} · {u}.N", f"{branch.upper()} RMSNorm",
                  stroke=OCHRE, fill=OCHRE_BG)
            d.edge(prefix + f"A{branch}-to-B{branch}", [(x + 240, center), (x + 287, center)],
                   source=a, target=b)
            d.edge(prefix + f"B{branch}-to-C{branch}", [(x + 445, center), (x + 492, center)],
                   source=b, target=c)
        else:
            d.edge(prefix + f"A{branch}-to-C{branch}", [(x + 240, center), (x + 492, center)],
                   source=a, target=c)


def instruction_topologies():
    d = Diagram("2 - ISA and attention QK preparation", "instruction-topologies", 1400, 710)
    isa_table(d)
    d.text("mapping-heading", 36, 277, "(b)  Preparing Q and K for attention", size=28, bold=True, width=1260)
    d.text("l-heading", 37, 321, "Llama 3.2-3B · Projection → RoPE",
           size=22, bold=True, width=640)
    d.text("q-heading", 709, 321, "Qwen3-4B · Projection → RMSNorm → RoPE",
           size=22, bold=True, width=655)
    qk_graph(d, "l-", 37, normalize=False)
    qk_graph(d, "q-", 709, normalize=True)
    model_program(d, "l-", 37, LLAMA_PROGRAM)
    model_program(d, "q-", 709, QWEN_PROGRAM)
    d.text("route-note", 700, 683, "Tensor dependencies and illustrative Block assignments",
           size=18, align="center", width=1280, color=BLUE)
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
