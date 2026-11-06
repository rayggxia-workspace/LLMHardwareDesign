"""Route per-peer side channels and place the transport's native pins on their rows."""
import argparse
from collections import defaultdict
import json
from pathlib import Path
import subprocess

from bind_switch import ports
from escape import to_dbu, to_grid
from qwen_candidate import dump, landing, read_lef


COLUMNS = (("P0", "P1", "C0", "U0", "F0"), ("P2", "J0", "J1", "U1"))
SWITCH_WIDTH = 1344


def midpoint(rect):
    a, b, c, d = rect
    return (a+c)//2, (b+d)//2


def compact(points):
    start = points[0]
    previous = start
    segments, vias = [], []
    for point in points[1:]:
        if point[2] != previous[2]:
            if start != previous:
                segments.append((start[2], to_dbu(start[:2]), to_dbu(previous[:2])))
            vias.append(to_dbu(point[:2]))
            start = point
        previous = point
    if start != previous:
        segments.append((start[2], to_dbu(start[:2]), to_dbu(previous[:2])))
    return segments, vias


def escape(executable, items, y0, y1, exit_x):
    points = [to_grid(midpoint(rect)) for _, _, rect in items]
    xs = sorted({exit_x} | {x+dx for x, _ in points for dx in range(-2, 3)})
    if exit_x not in (xs[0], xs[-1]):
        raise ValueError("Channel exit is inside the pin area")
    ys = range(y0//4+4, y1//4-4)
    x_index = {x: i for i, x in enumerate(xs)}
    inputs = [f"{len(xs)} {len(ys)} {len(points)} {x_index[exit_x]}",
              " ".join(map(str, xs)), " ".join(map(str, ys))]
    inputs.extend(f"{x_index[x]} {ys.index(y)}" for x, y in points)
    proc = subprocess.run([str(executable)], input="\n".join(inputs)+"\n",
                          stdout=subprocess.PIPE, universal_newlines=True, check=True)
    paths = []
    for line in proc.stdout.splitlines():
        values = list(map(int, line.split()))
        paths.append(list(zip(values[::3], values[1::3], values[2::3])))
    if len(paths) != len(points) or any(
            path[0] != (*point, 11) or path[-1][0] != exit_x or path[-1][2] != 11
            for point, path in zip(points, paths)):
        raise ValueError("Side channel paths do not match the requested terminals")
    return paths


def plan(inputs, executable, out):
    base = json.loads((inputs/"inputs.json").read_text())
    sizes = base["sizes_um"]
    lefs = {kind: read_lef(inputs/f"{kind}.lef") for kind in "PUCFJ"}
    ends = defaultdict(list)
    for index, (a, b) in enumerate(ports("nine")):
        source, sink = (a, b) if a[0] != "T0" else (b, a)
        ends[source[0]].append((f"word_{index:04d}", source, sink[1], "OUTPUT" if source == a else "INPUT"))

    out.mkdir(parents=True)
    positions, pin_plan, endpoints, routes = {}, {}, {}, {}
    left_edge = 3360
    switch_x = left_edge+256
    right_edge = switch_x+SWITCH_WIDTH+256
    y_limits = []
    for side, peers in enumerate(COLUMNS):
        y0 = 256
        for peer in peers:
            width, height = sizes[peer[0]]
            x = right_edge if side else (left_edge-width)//8*8
            positions[peer] = [x, y0+64]
            y1 = y0 + max((height+7)//8*8+128, 4*(len(ends[peer])+40))
            items = []
            for net, (block, pin), switch_pin, direction in ends[peer]:
                rect = landing(lefs, positions, block, pin, direction)
                if rect is None:
                    raise ValueError(f"No native landing for {block}/{pin}")
                items.append((net, switch_pin, rect))
            exit_x = (right_edge-64 if side else left_edge+64)//4
            print(f"Route {peer} with {len(items)} pins on side {side}", flush=True)
            for (net, switch_pin, rect), path in zip(items, escape(executable, items, y0, y1, exit_x)):
                exit_y = path[-1][1]
                pin_inset = 40+8*(exit_y%2)
                pin_x = switch_x+SWITCH_WIDTH-pin_inset if side else switch_x+pin_inset
                p = to_dbu((pin_x//4, exit_y))
                pin_plan[switch_pin] = [(p[0]-2000*switch_x)/2000, p[1]/2000]
                pin_rect = [p[0]-2000, p[1]-2000, p[0]+2000, p[1]+2000]
                endpoints[net] = [rect, pin_rect]
                segments, vias = compact(path)
                segments.append((11, to_dbu(path[-1][:2]), p))
                routes[net] = dict(segments=segments, via10=[midpoint(rect), p], via11=vias)
            y0 = (y1+71)//8*8
        y_limits.append(y0)
    if len(routes) != sum(map(len, ends.values())) or len(pin_plan) != len(routes):
        raise ValueError("Incomplete upper route or repeated switch terminals")

    switch_height = max(y_limits)+128
    positions["T0"] = [switch_x, 0]
    size = [SWITCH_WIDTH, switch_height]
    die = [max(positions[b][0]+sizes[b[0]][0] for peers in COLUMNS for b in peers)+256, switch_height+256]
    dump(out/"pin-plan.json", dict(size=size, pins=pin_plan))
    dump(out/"layout-plan.json", dict(positions_um=positions, switch_size_um=size, die_um=die))
    dump(out/"inputs.json", dict(macro_endpoint_rects_dbu=endpoints))
    dump(out/"route.json", dict(routes=routes, failed={}, units=2000))
    (out/"coupon.def").write_text("")


def check_bound(plan_path, case):
    planned = json.loads((plan_path/"inputs.json").read_text())["macro_endpoint_rects_dbu"]
    actual = json.loads((case/"inputs.json").read_text())["macro_endpoint_rects_dbu"]
    canonical = lambda endpoints: {name: sorted(map(tuple, rects)) for name, rects in endpoints.items()}
    if canonical(planned) != canonical(actual):
        raise ValueError("Physical M10 pin rectangles differ from the channel plan")
    (case/"route.json").write_bytes((plan_path/"route.json").read_bytes())


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("mode", choices=("plan", "check-bound"))
    cli.add_argument("paths", nargs="+", type=Path)
    args = cli.parse_args()
    if args.mode == "plan":
        plan(*args.paths)
    else:
        check_bound(*args.paths)
