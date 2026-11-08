"""Count hard bank footprints and functional cell footprints in actual placement."""
import re

BANK = "s_sram_256x128_freepdk45"


def measure(path):
    rows = iter(path.read_text().splitlines())
    dbu, x0, y0, x1, y1 = map(int, next(rows).split())
    die = (x1 - x0) * (y1 - y0)
    area = {"bank": 0, "active": 0, "physical_only": 0}
    counts = dict.fromkeys(area, 0)
    nx, ny = 16, 10
    occupied = [[0] * nx for _ in range(ny)]
    xs = [x0 + (x1 - x0) * i // nx for i in range(nx + 1)]
    ys = [y0 + (y1 - y0) * i // ny for i in range(ny + 1)]
    for row in rows:
        name, kind, *coords = row.split()
        left, bottom, right, top = map(int, coords)
        assert x0 <= left < right <= x1 and y0 <= bottom < top <= y1, row
        if name == BANK:
            group = "bank"
        elif re.search(r"FILL|TAP|ENDCAP|ANTENNA|DECAP", name, re.I) or "SPACER" in kind:
            group = "physical_only"
        else:
            group = "active"
        area[group] += (right - left) * (top - bottom)
        counts[group] += 1
        if group == "physical_only":
            continue
        for j in range(ny):
            overlap_y = min(top, ys[j+1]) - max(bottom, ys[j])
            if overlap_y <= 0:
                continue
            for i in range(nx):
                overlap_x = min(right, xs[i+1]) - max(left, xs[i])
                if overlap_x > 0:
                    occupied[j][i] += overlap_x * overlap_y
    assert counts["bank"] == 4
    density = [[occupied[j][i] / ((xs[i+1] - xs[i]) * (ys[j+1] - ys[j]))
                for i in range(nx)] for j in range(ny)]
    assert all(0 <= value <= 1 for row in density for value in row)
    return dict(die_um2=die / dbu**2, area_um2={key: value / dbu**2 for key, value in area.items()},
                counts=counts, useful_fraction=(area["bank"] + area["active"]) / die,
                active_standard_cell_fraction=area["active"] / die,
                bins_under_10pct=sum(value < .1 for row in density for value in row),
                bottom_to_top_useful_fraction_16x10=density)
