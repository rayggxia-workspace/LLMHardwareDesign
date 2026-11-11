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
    d = Diagram("1 - Base and C control", "control-architecture", 1200, 818)
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
    d.box("c-detail-frame", 40, 410, 1120, 345, stroke=LINE, fill=PANEL)
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
        ("s", "S", "Private SRAM", 67, 403),
        ("r", "R", "State service", 344, 526),
        ("g", "G", "Activation", 621, 648),
        ("e", "E", "Vector arithmetic", 898, 760),
    ):
        d.box("macro-" + key, x, 668, 221, 55, title, detail, stroke=LINE, fill="white")
        d.edge("c-service-" + key, [(port, 615), (x + 110, 668)],
               source="c-service", target="macro-" + key, direction="both")
    d.edge("c-g-to-e-product", [(842, 696), (898, 696)], source="macro-g", target="macro-e",
           color=OCHRE, dashed=True)
    d.text("c-g-to-e-label", 870, 737, "Product-wired G → E bypass", size=15,
           color=OCHRE, align="center", width=320)
    for key, x, color, dashed, caption in (
        ("exchange", 60, BLUE, False, "Control and data exchange"),
        ("physical", 623, OCHRE, True, "Product-specific physical wiring"),
    ):
        d.edge("key-" + key, [(x, 787), (x + 42, 787)], color=color, dashed=dashed, direction="none")
        d.text("key-" + key + "-label", x + 54, 787, caption, size=16, color=color, width=470)
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
     (("L_END", "Return task terminal status"),)),
)


def isa_table(d):
    d.text("isa-heading", 36, 36, "(a)  Four instruction classes", size=28, bold=True, width=760)
    d.text("mc-column", 243, 73, "Native MC v3 · 8 opcodes", size=20, bold=True, width=410)
    d.text("lc-column", 885, 73, "Common LC · P / U / C / F / J", size=20, bold=True, width=420)
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


QWEN_PROGRAM = (
    "G_CALL A,t0 → G_CALL B,t1 → G_WAIT 0x03",
    "G_CALL C,t2 → G_WAIT 0x04",
    "G_CALL D,t3 → G_WAIT 0x08 → G_END",
)
GPT_PROGRAM = (
    "G_CALL A,t0 → G_WAIT 0x01",
    "G_CALL B,t1 → G_WAIT 0x02",
    "G_CALL C,t2 → G_WAIT 0x04 → G_END",
)


def model_program(d, prefix, x, lines):
    d.box(prefix + "program", x, 651, 655, 156, stroke=LINE, fill=PANEL)
    d.text(prefix + "program-title", x + 20, 676, "MC issue order", size=18, bold=True, width=400)
    for index, text in enumerate(lines):
        d.text(prefix + f"step-{index}", x + 20, 708 + 30 * index, text,
               size=18, mono=True, width=610)


def qwen_graph(d, x):
    d.box("q-x", x, 493, 55, 61, "x", stroke=LINE, fill=PANEL)
    d.box("q-A", x + 120, 447, 151, 61, "A · P0", "Gate projection")
    d.box("q-B", x + 120, 539, 151, 61, "B · P1", "Up projection")
    d.box("q-C", x + 338, 493, 142, 61, "C · P0.G32", "SiLU × Up")
    d.box("q-D", x + 513, 493, 142, 61, "D · P2", "Down projection")
    for source, target, start, end in (
        ("x", "A", (55, 508), (120, 477)), ("x", "B", (55, 538), (120, 568)),
        ("A", "C", (271, 477), (338, 508)), ("B", "C", (271, 568), (338, 538)),
        ("C", "D", (480, 523), (513, 523)),
    ):
        d.edge("q-" + source + "-to-" + target, [(x + start[0], start[1]), (x + end[0], end[1])],
               source="q-" + source, target="q-" + target, color=OCHRE, dashed=True)
    d.text("q-formula", x + 325, 621, "Down(SiLU(Gate(x)) ⊙ Up(x))", size=22,
           align="center", bold=True, width=600)


def gpt_graph(d, x):
    d.box("g-x", x, 493, 55, 61, "x", stroke=LINE, fill=PANEL)
    d.box("g-A", x + 82, 493, 158, 61, "A · P0", "c_fc affine")
    d.box("g-B", x + 269, 493, 155, 61, "B · F0.G16", "GELU (tanh)")
    d.box("g-C", x + 454, 493, 201, 61, "C · P2", "c_proj affine")
    for source, target, left, right in (
        ("x", "A", 55, 82), ("A", "B", 240, 269), ("B", "C", 424, 454),
    ):
        d.edge("g-" + source + "-to-" + target, [(x + left, 523), (x + right, 523)],
               source="g-" + source, target="g-" + target, color=OCHRE, dashed=True)
    d.text("g-formula", x + 325, 621, "c_proj(GELU(c_fc(x)))", size=22,
           align="center", bold=True, width=600)


def instruction_topologies():
    d = Diagram("2 - ISA and model FFN mappings", "instruction-topologies", 1400, 920)
    isa_table(d)
    d.text("mapping-heading", 36, 381, "(b)  Two model FFNs on the same Block inventory",
           size=28, bold=True, width=1260)
    d.text("q-heading", 37, 421, "Qwen2.5-3B-Instruct · gated FFN",
           size=22, bold=True, width=610)
    d.text("g-heading", 709, 421, "GPT-2 · GELU MLP",
           size=22, bold=True, width=610)
    qwen_graph(d, 37)
    gpt_graph(d, 709)
    model_program(d, "q-", 37, QWEN_PROGRAM)
    model_program(d, "g-", 709, GPT_PROGRAM)
    d.text("route-note", 700, 844, "Dashed tensor routes and Block assignments are illustrative",
           size=18, align="center", width=1280, color=OCHRE)
    d.text("local-note", 700, 873, "Common local sequence: L_EXEC → L_WAIT → L_END",
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
