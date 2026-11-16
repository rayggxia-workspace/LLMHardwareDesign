"""Place routed spare-buffer banks in legal block gaps and stream the result."""

import csv
import hashlib
import itertools
import json
from pathlib import Path

import pya


SOURCE_DBU_PER_UM = 2000
STREAM_DBU_UM = 0.0001
SCALE = 5


def read_tsv(path):
    with open(path, encoding="utf-8", newline="") as table:
        return list(csv.DictReader(table, delimiter="\t"))


def intersect(a, b):
    return a[0] < b[2] and a[2] > b[0] and a[1] < b[3] and a[3] > b[1]


def contains(outer, inner):
    return (
        outer[0] <= inner[0] < inner[2] <= outer[2]
        and outer[1] <= inner[1] < inner[3] <= outer[3]
    )


def gaps_between_blocks(boxes):
    for a, b in itertools.combinations(boxes, 2):
        left, right = sorted((a, b), key=lambda box: box[0])
        low, high = sorted((a, b), key=lambda box: box[1])
        for box in (
            (left[2], max(a[1], b[1]), right[0], min(a[3], b[3])),
            (max(a[0], b[0]), low[3], min(a[2], b[2]), high[1]),
        ):
            if box[0] < box[2] and box[1] < box[3]:
                yield box


def source_box(cell, dbu):
    box = cell.dbbox()
    return (
        int(box.left / dbu // 1), int(box.bottom / dbu // 1),
        -int(-box.right / dbu // 1), -int(-box.top / dbu // 1),
    )


def copy_cell(layout, source, target_name):
    target = layout.create_cell(target_name)
    if target.name != target_name:
        raise ValueError(f"Duplicate output cell name {target_name}")
    target.copy_tree(source)
    return target


def add_instance(parent, child, x, y):
    parent.insert(pya.CellInstArray(child.cell_index(), pya.Trans(x * SCALE, y * SCALE)))


def read_box(box, name):
    if not isinstance(box, list) or len(box) != 4 or any(type(v) is not int for v in box):
        raise ValueError(f"{name} must contain four integer DBU coordinates")
    if box[0] >= box[2] or box[1] >= box[3]:
        raise ValueError(f"{name} has invalid bounds")
    return box


def load_base(layout, path):
    manifest_path = Path(path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest["dbu_per_micron"] != SOURCE_DBU_PER_UM:
        raise ValueError("Expected manifest coordinates in 2000 DBU per micron")
    die = read_box(manifest["bounds_dbu"], "bounds_dbu")
    boxes = [read_box(box, name) for name, box in manifest["boxes_dbu"].items()]
    if len(boxes) < 2 or any(not contains(die, box) for box in boxes):
        raise ValueError("Need at least two block boxes inside the die")
    keepouts = [read_box(box, "keepout") for box in manifest.get("keepouts_dbu", [])]
    stream_path = (manifest_path.parent / manifest["base_stream"]).resolve(strict=True)
    source = pya.Layout()
    source.read(str(stream_path))
    ratio = source.dbu / STREAM_DBU_UM
    if ratio < 1 or abs(ratio - round(ratio)) > 1e-8:
        raise ValueError("Base stream units cannot be represented on the 0.0001 um export grid")
    top_name = manifest.get("top_cell")
    stream_top = source.cell(top_name) if top_name else source.top_cell()
    if stream_top is None or stream_top.is_empty():
        raise ValueError("Missing or empty base stream top cell")
    base = layout.create_cell("SPARE_BASE")
    top = copy_cell(layout, stream_top, layout.unique_cell_name(stream_top.name))
    add_instance(base, top, 0, 0)
    checksum = hashlib.sha256()
    with stream_path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            checksum.update(chunk)
    actual = {
        "source_top": {
            "source_cell": stream_top.name,
            "source_view": str(stream_path),
            "source_sha256": checksum.hexdigest(),
            "stream_bbox_dbu": source_box(top, 1 / SOURCE_DBU_PER_UM),
            "translation_dbu": [0, 0],
        },
    }
    return base, actual, die, boxes, keepouts


def touches_base_geometry(base, layers, halo):
    window = pya.Box(*(value * SCALE for value in halo))
    for layer in layers:
        shapes = base.begin_shapes_rec_touching(layer, window)
        while not shapes.at_end():
            if not shapes.shape().is_text():
                return True
            shapes.next()
    return False


def assemble(layout, placement, views_file):
    """Compose the source block streams, preserving each donor's hierarchy."""
    rows = read_tsv(views_file)
    boxes = placement["boxes_dbu"]
    if len(rows) != len(boxes) or {row["block"] for row in rows} != set(boxes):
        raise ValueError("Source streams do not cover exactly the placed blocks")
    base = layout.create_cell("SPARE_BASE")
    sources = {}
    actual = {}
    for row in rows:
        block, path = row["block"], row["path"]
        if path not in sources:
            source = pya.Layout()
            source.read(path)
            stream_top = source.top_cell()
            if stream_top is None or stream_top.is_empty():
                raise ValueError(f"Missing stream top for {block}")
            source_name = row["source_view"].rsplit(".", 1)[0].replace(".", "_")
            name = f"PR271_{source_name}_VIEW"
            cell = copy_cell(layout, stream_top, name)
            sources[path] = (cell, source_box(cell, 1 / SOURCE_DBU_PER_UM), stream_top.name)
        cell, (x0, y0, x1, y1), original_top = sources[path]
        x, y = placement["placement_dbu"][block]
        x -= int(row["origin_x_dbu"])
        y -= int(row["origin_y_dbu"])
        block_box = (x0 + x, y0 + y, x1 + x, y1 + y)
        if not intersect(block_box, boxes[block]):
            raise ValueError(f"Stream {original_top} is outside its box for {block}")
        add_instance(base, cell, x, y)
        actual[block] = {
            "source_cell": original_top,
            "source_view": row["source_view"],
            "source_sha256": row["source_sha256"],
            "stream_bbox_dbu": block_box,
            "translation_dbu": [x, y],
        }
        print(f"BASE {block}: {original_top} bbox={block_box}", flush=True)
    return base, actual


def site_grid(die, block_boxes, obstacles, bank, pitch_x, pitch_y, clearance):
    channels = list(gaps_between_blocks(block_boxes))
    if pitch_x < bank[2] - bank[0] + clearance or pitch_y < bank[3] - bank[1] + clearance:
        raise ValueError("Pitch is too small for the bank plus clearance")
    # A common 0.2 um translation grid keeps every native shape on the
    # manufacturing grid and preserves the relative M10 port spacing.
    step = SOURCE_DBU_PER_UM // 5
    lattice = lambda start: -(-start // step) * step
    for y in range(lattice(die[1] + clearance), die[3] - bank[3] - clearance + 1, pitch_y):
        for x in range(lattice(die[0] + clearance), die[2] - bank[2] - clearance + 1, pitch_x):
            rect = (x + bank[0], y + bank[1], x + bank[2], y + bank[3])
            if not any(contains(box, rect) for box in channels):
                continue
            halo = (rect[0] - clearance, rect[1] - clearance, rect[2] + clearance, rect[3] + clearance)
            if contains(die, halo) and not any(intersect(halo, box) for box in obstacles):
                yield (x, y), halo


def write_tables(output, positions, ports):
    with (output / "m10-ports.tsv").open("w", encoding="utf-8", newline="") as f, (
        output / "banks.tsv"
    ).open("w", encoding="utf-8", newline="") as placement_file:
        table = csv.writer(f, delimiter="\t", lineterminator="\n")
        table.writerow(["bank", "instance", "pin", "layer", "x_um", "y_um",
                        "x0_um", "y0_um", "x1_um", "y1_um"])
        sites = csv.writer(placement_file, delimiter="\t", lineterminator="\n")
        sites.writerow(["bank", "origin_x_um", "origin_y_um"])
        for index, (x, y) in enumerate(positions):
            name = f"SPARE_{index:05d}"
            sites.writerow([name, x / SOURCE_DBU_PER_UM, y / SOURCE_DBU_PER_UM])
            for p in ports:
                coords = [
                    (int(p[key + "_dbu"]) + shift) / SOURCE_DBU_PER_UM
                    for key, shift in (("x", x), ("y", y), ("x0", x), ("y0", y), ("x1", x), ("y1", y))
                ]
                table.writerow([name, f'{name}/{p["instance"]}', p["pin"], "M10", *coords])


def main():
    bank = pya.Layout()
    bank.read(bank_gds)
    bank_top = bank.cell("spare_bank")
    if bank_top is None or bank_top.is_empty():
        raise ValueError("Missing physical spare bank")
    bank_box = (0, 0, 48 * SOURCE_DBU_PER_UM, 56 * SOURCE_DBU_PER_UM)
    if not contains(bank_box, source_box(bank_top, 1 / SOURCE_DBU_PER_UM)):
        raise ValueError("Bank copper exceeds its declared envelope")
    ports = read_tsv(bank_ports)
    signal_set = {(row["instance"], row["pin"]) for row in ports if row["instance"] != "PG"}
    if len(ports) != 12 or signal_set != {(f"b{i}", pin) for i in range(4) for pin in ("A", "Z")}:
        raise ValueError("Unexpected bank port inventory")
    out = Path(output_dir)
    layout = pya.Layout()
    layout.dbu = STREAM_DBU_UM
    existing_layers = []
    if globals().get("manifest_file"):
        base, actual, die, boxes, keepouts = load_base(layout, manifest_file)
        variant = "base_stream"
        # FreePDK45 active/well/implant/poly/contact, M1-M10 and via1-via9.
        existing_layers = [
            i for i in layout.layer_indexes()
            if 1 <= layout.get_info(i).layer <= 29
        ]
        if not existing_layers:
            raise ValueError("Base stream has no recognized FreePDK45 physical layers")
    else:
        placement = json.loads(Path(placement_file).read_text(encoding="utf-8"))
        archive = json.loads(Path(archive_file).read_text(encoding="utf-8"))
        if archive["dbu_per_micron"] != SOURCE_DBU_PER_UM:
            raise ValueError("Expected source units of 2000 DBU per micron")
        base, actual = assemble(layout, placement, views_tsv)
        boxes = list(placement["boxes_dbu"].values())
        die = archive["bounds_dbu"]
        keepouts = [entry["stream_bbox_dbu"] for entry in actual.values()]
        variant = placement["variant"]
    px, py = (int(value) * SOURCE_DBU_PER_UM for value in pitch_um.split(","))
    all_positions = []
    geometry_blocked = 0
    for site, halo in site_grid(die, boxes, boxes + keepouts, bank_box, px, py, 4000):
        if touches_base_geometry(base, existing_layers, halo):
            geometry_blocked += 1
        else:
            all_positions.append(site)
    size = int(limit)
    if size < 0 or not all_positions:
        raise ValueError("Invalid placement count or no eligible gap sites")
    # Take evenly spaced samples of the full scan for a distributed pilot.
    positions = all_positions
    if 0 < size < len(all_positions):
        positions = [all_positions[(2 * i + 1) * len(all_positions) // (2 * size)] for i in range(size)]
    merged = layout.create_cell(layout.unique_cell_name("BASE_WITH_SPARES"))
    layer = layout.layer(235, 0)
    if variant != "base_stream":
        merged.shapes(layer).insert(pya.Box(*(v * SCALE for v in die)))
    add_instance(merged, base, 0, 0)
    overlay = layout.create_cell(layout.unique_cell_name("SPARE_BUFFER_OVERLAY"))
    bank_copy = copy_cell(layout, bank_top, layout.unique_cell_name("SPARE_BUFFER_BANK"))
    bank_copy.shapes(layer).clear()
    for x, y in positions:
        add_instance(overlay, bank_copy, x, y)
    add_instance(merged, overlay, 0, 0)
    overlay_layout = pya.Layout()
    overlay_layout.dbu = layout.dbu
    copy_cell(overlay_layout, overlay, overlay.name)
    overlay_layout.write(str(out / "spare-overlay.oas"))
    layout.write(str(out / "base-with-spares.oas"))
    write_tables(out, positions, ports)
    summary = {
        "variant": variant,
        "base_instances": actual,
        "stream_cells": {"top": merged.name, "base": base.name, "overlay": overlay.name, "bank": bank_copy.name},
        "candidate_banks": len(all_positions),
        "geometry_blocked_sites": geometry_blocked,
        "placed_banks": len(positions),
        "placed_buffers": 4 * len(positions),
        "m10_signal_ports": 8 * len(positions),
        "m10_pg_shapes": 4 * len(positions),
        "pitch_um": [px / SOURCE_DBU_PER_UM, py / SOURCE_DBU_PER_UM],
        "block_clearance_um": 2,
        "source_dbu_per_micron": SOURCE_DBU_PER_UM,
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in summary.items() if key != "base_instances"}), flush=True)


main()
