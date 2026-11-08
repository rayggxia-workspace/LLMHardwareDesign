"""Candidate M10 landings and simultaneous M11/M12 escapes for rectangular S."""
from collections import defaultdict
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "block_v1"))
from revision300_geometry import DBU, u, box, verify


def generate(ports, width, height, technology, dual_layer, deep_offset=124):
    """A second layer on a side needs short nonpreferred-direction segments.

    Inner and outer bands are separated on the macro scale. Alternating two
    adjacent grid locations *within* each band meets the tighter cut spacing.
    Corner guards keep the perpendicular escapes and their vias separate.
    """
    geometry = technology["geometry_um"]
    pitch = u(geometry["pitch"])
    ox, oy = (u(geometry[f"track_offset_{axis}"]) for axis in "xy")
    dx, dy = u(width), u(height)
    corner_x = u(76 if dual_layer else 24)
    corner_y = u(deep_offset + 8 if dual_layer else 24)
    slots = {}
    for side, horizontal, negative in (
        ("west", True, True), ("east", True, False),
        ("south", False, True), ("north", False, False),
    ):
        along_phase, along_size = (ox, dx) if horizontal else (oy, dy)
        cross_phase, cross_size = (oy, dy) if horizontal else (ox, dx)
        guard = corner_y if horizontal else corner_x
        preferred = "metal11" if horizontal else "metal12"
        second = "metal12" if horizontal else "metal11"
        depths = [(preferred, 12)]
        if dual_layer:
            depths = [(preferred, 12), (second, 68)] if horizontal else [
                (preferred, deep_offset), (second, 12)]
        for layer, depth in depths:
            start = u(depth) if negative else along_size - u(depth)
            anchor = along_phase + pitch * round((start - along_phase) / pitch)
            outward = -1 if negative else 1
            end = -u(32) if negative else along_size + u(32)
            first = (guard - cross_phase + pitch - 1) // pitch
            last = (cross_size - guard - cross_phase) // pitch
            entries = []
            for index in range(first, last + 1):
                track = cross_phase + pitch * index
                band_depth = depth
                if dual_layer and layer == preferred and (index // 16) % 2:
                    band_depth = 40 if horizontal else 72
                target = u(band_depth) if negative else along_size - u(band_depth)
                band_anchor = along_phase + pitch * round((target - along_phase) / pitch)
                stagger = band_anchor + (index % 2) * pitch * outward
                xy, endpoint = ([stagger, track], [end, track]) if horizontal else (
                    [track, stagger], [track, end])
                entries.append((xy, endpoint, layer, side, band_depth))
            slots[f"{side}/{layer}"] = entries
    used = defaultdict(int)
    pins, shapes, connections, groups = [], [], [], []

    def add(layer, rectangle, net):
        shapes.append(dict(layer=layer, box_dbu=list(map(int, rectangle)), net=net))

    group_size = 8 if dual_layer else 16
    for port, entry in sorted(ports.items()):
        count = entry["bits"]
        for begin in range(0, count, group_size):
            bits = min(group_size, count - begin)
            available = [key for key, values in slots.items() if used[key] + bits <= len(values)]
            if not available:
                raise ValueError(f"Escape capacity exhausted at {port}[{begin}]")
            key = min(available, key=lambda key: used[key] / len(slots[key]))
            group = f"{port}-{begin // group_size}"
            groups.append(dict(id=group, port=port, first=begin, bits=bits, escape=key))
            for bit in range(begin, begin + bits):
                xy, end, layer, side, depth = slots[key][used[key]]
                used[key] += 1
                name = port if count == 1 else f"{port}[{bit}]"
                pins.append(dict(pin=name, port=port, index=bit, direction=entry["direction"],
                                 role="clock" if port == "clk" else "signal", layer="metal10",
                                 xy_um=[v / DBU for v in xy], size_um=[2., 2.], region="internal",
                                 group=group, escape_side=side, escape_layer=layer, band_depth_um=depth))
                add("metal10", box(*xy), name)
                add("via10", box(*xy), name)
                if layer == "metal12":
                    add("metal11", box(*xy), name)
                    add("via11", box(*xy), name)
                add(layer, [min(xy[0], end[0]) - u(1), min(xy[1], end[1]) - u(1),
                            max(xy[0], end[0]) + u(1), max(xy[1], end[1]) + u(1)], name)
                connections.append(dict(net=name, source_m10_dbu=xy,
                                        external_endpoint_dbu=end, endpoint_layer=layer))
    fixture = dict(schema="coarse-interface-fixture/1", name="compact-s-all-ports", dbu_per_um=DBU,
                   expected_bits=len(pins), macro_box_dbu=[0, 0, dx, dy],
                   test_boundary_dbu=[-u(40), -u(40), dx+u(40), dy+u(40)],
                   ports=connections, shapes=shapes)
    proof = verify(fixture, technology)
    plan = dict(schema="block-v1-pin-plan/1", policy="rectangular-bands-v1",
                pins=pins, ports=len(pins), internal_ports=len(pins), groups=groups,
                track_demand=dict(used), track_capacity={key: len(value) for key, value in slots.items()},
                wire_pitch_um=4., stagger_um=4., qualified_access=False,
                uses_nonpreferred_escape=dual_layer)
    return plan, fixture, proof
