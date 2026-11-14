"""Read the exact deployed images for a persistent native controller cohort."""

from hashlib import sha256
import json
from pathlib import Path
import re
from struct import unpack_from
from zlib import crc32


def mother_target_mask(image):
    """Read the actual CALL targets from a checked native v3 PM image."""
    count, code_base = unpack_from("<II", image, 20)
    if count == 0 or code_base != 128 or code_base+count*8 > len(image):
        raise ValueError("native mother has an invalid instruction extent")
    mask = 0
    for offset in range(code_base, code_base+count*8, 8):
        if image[offset+7] == 0x10:  # Native v3 CALL opcode.
            target = image[offset+6]
            if target >= 9:
                raise ValueError(f"native mother CALL uses invalid target {target}")
            mask |= 1 << target
    return mask


def read_pm_image(path, *, base, count, crc, role, topology):
    return parse_pm_image(path.read_bytes(), path, base=base, count=count, crc=crc,
                          role=role, topology=topology)


def parse_pm_image(data, path, *, base, count, crc, role, topology):
    raw = data[:count]
    if (len(data) != ((count + 63) & ~63) or any(data[count:]) or crc32(raw) != crc
            or base < 0 or base % 64 or base + len(data) > 1 << 48):
        raise ValueError(f"invalid DDR program image {path.name}")
    is_local = role == "local"
    if (role not in ("mother", "local") or raw[:8] != b"LBCISA01"
            or not (128 if is_local else 144) <= count <= (1024 if is_local else 16384)
            or count % 16):
        raise ValueError(f"invalid native PM role or size for {path.name}")
    version, encoded_role, width, encoded_bytes = unpack_from("<HBBI", raw, 8)
    image_id, encoded_topology, abi = unpack_from("<III", raw, 60)
    capacity, = unpack_from("<I", raw, 84)
    expected = (2, 1, 0x02510001) if is_local else (3, 0, 0x02590003)
    if ((version, encoded_role, capacity) != expected or width != 8 or encoded_bytes != count
            or image_id == 0 or encoded_topology != topology or abi != 0x02500002):
        raise ValueError(f"invalid native PM metadata for {path.name}")
    result = dict(path=path, base=base, bytes=count, ddr_bytes=len(data), crc=crc, image_id=image_id,
                  topology=topology, abi=abi, capacity=capacity, role=role)
    if not is_local:
        result["target_mask"] = mother_target_mask(raw)
    return result, data, raw


def load_program_schedule(directory, *, manifest=None):
    """Return ordered phases and the DDR files needed by actual PM installers."""
    root = Path(directory)
    if manifest is None:
        manifest = json.loads((root / "product.json").read_bytes())
    schema = manifest["schema"]
    if schema not in ("block-native-product/1", "block-native-product/2", "block-native-product/3",
                      "block-native-product/4"):
        raise ValueError("unsupported native product schedule")
    if schema in ("block-native-product/3", "block-native-product/4") and "mother_page_table" not in manifest:
        raise ValueError("native product is missing the required mother page table receipt")
    if schema == "block-native-product/4" and "runtime_asset_table" not in manifest:
        raise ValueError("native product is missing the required runtime asset table receipt")
    topology, targets = manifest["topology"], manifest["control_targets"]
    if len(set(targets.values())) != len(targets):
        raise ValueError("native product aliases local controller targets")
    program_images, addresses = {}, []
    regions = manifest["program_regions"]
    if set(regions) != {f"program-{index}" for index in range(len(regions))}:
        raise ValueError("native program region indices are incomplete")
    for name, region in regions.items():
        filename = f"{name}.ddr.bin"
        if region["file"] != filename:
            raise ValueError("unexpected native PM filename")
        base, count = region["base"], region["image_bytes"]
        image, data, raw = read_pm_image(root / filename, base=base, count=count, crc=region["image_crc32"],
                                        role=region["image_role"], topology=topology)
        if (len(data) != region["bytes"]
                or sha256(data).hexdigest() != region["sha256"]
                or sha256(raw).hexdigest() != region["image_sha256"]):
            raise ValueError(f"invalid DDR program image {name}")
        if (image["image_id"], image["topology"], image["abi"], image["capacity"]) != (
                region["image_id"], region["image_topology"], region["image_abi"], region["image_capacity_id"]):
            raise ValueError(f"invalid native PM metadata for {name}")
        addresses.append((base, base + len(data)))
        program_images[name] = image

    phases = []
    for step, phase in enumerate(manifest["phases"]):
        if phase["directory"] != f"phase-{step}":
            raise ValueError("native phase bundle directory differs from execution order")
        bundle_path = root / phase["directory"]
        bundle_bytes = (bundle_path / "deployment.json").read_bytes()
        if sha256(bundle_bytes).hexdigest() != phase["deployment_sha256"]:
            raise ValueError(f"native phase bundle digest differs at step {step}")
        bundle = json.loads(bundle_bytes)
        if bundle["topology"] != topology or bundle["descriptor_base"] != phase["descriptors"]["base"]:
            raise ValueError(f"native phase bundle binding differs at step {step}")
        descriptors = (bundle_path / "descriptors.bin").read_bytes()
        descriptor_base = phase["descriptors"]["base"]
        descriptor_end = descriptor_base + len(descriptors)
        if (descriptor_base < 0 or descriptor_base % 128 or len(descriptors) == 0
                or len(descriptors) % 128 or descriptor_end > (1 << 48)):
            raise ValueError(f"invalid native descriptor region at step {step}")
        addresses.append((descriptor_base, descriptor_end))
        if (len(descriptors) != phase["descriptors"]["bytes"]
                or len(descriptors) != bundle["payloads"]["descriptors.bin"]["bytes"]
                or sha256(descriptors).hexdigest() != bundle["payloads"]["descriptors.bin"]["sha256"]):
            raise ValueError(f"native descriptor bytes differ at step {step}")

        def image_for(name, role, member):
            image = program_images[name]
            raw = (bundle_path / member).read_bytes()
            if (image["role"] != role or len(raw) != image["bytes"] or crc32(raw) != image["crc"]
                    or sha256(raw).hexdigest() != regions[name]["image_sha256"]
                    or sha256(raw).hexdigest() != bundle["payloads"][member]["sha256"]):
                raise ValueError(f"native PM membership differs at step {step} for {member}")
            return image

        selected = phase["programs"]
        local_map = selected["local_targets"]
        if (local_map.keys() != selected["locals"].keys() or local_map.keys() != bundle["local_images"].keys()
                or any(targets[group] != target for group, target in local_map.items())):
            raise ValueError(f"native local target binding differs at step {step}")
        if sorted(bundle["local_images"].values()) != sorted(
                f"local-{index}.bin" for index in range(len(local_map))):
            raise ValueError(f"native local image names differ at step {step}")
        locals_by_target = {local_map[group]: image_for(name, "local", bundle["local_images"][group])
                            for group, name in selected["locals"].items()}
        page_metadata = bundle.get("mother_pages")
        if page_metadata is None:
            pages = [dict(image_for(selected["mother"], "mother", "mother.bin"),
                          descriptor_base=bundle["descriptor_base"])]
        else:
            pages = []
            next_descriptor = descriptor_base
            for index, (page, member) in enumerate(zip(selected["mother_pages"], page_metadata, strict=True)):
                if (page["descriptor_base"] != member["descriptor_base"]
                        or page["descriptor_base"] != next_descriptor
                        or member["file"] != f"mother-{index}.bin"
                        or page["call_count"] != member["call_count"] or page["call_count"] <= 0):
                    raise ValueError(f"native page descriptor base differs at step {step}")
                pages.append(dict(image_for(page["region"], "mother", member["file"]),
                                  descriptor_base=member["descriptor_base"]))
                next_descriptor += page["call_count"] * 128
            if next_descriptor != descriptor_end:
                raise ValueError(f"native page calls do not cover the descriptors at step {step}")
        local_mask = sum(1 << target for target in locals_by_target)
        if local_mask and any(not page["target_mask"] or page["target_mask"] & ~local_mask for page in pages):
            raise ValueError(f"native mother selects a target without a phase LC image at step {step}")
        runtime = phase.get("runtime")
        if not pages or (runtime is not None and (runtime["step"], runtime["mother_page_count"]) != (step, len(pages))):
            raise ValueError(f"native phase page count differs at step {step}")
        phases.append(dict(step=step, id=phase["id"], pages=pages, locals=locals_by_target,
                           descriptors=dict(base=descriptor_base, bytes=len(descriptors),
                                            crc=crc32(descriptors), path=bundle_path / "descriptors.bin"),
                           runtime=runtime))
    if not phases:
        raise ValueError("native product has no executable phases")
    addresses.sort()
    if any(end > next_base for (_, end), (next_base, _) in zip(addresses, addresses[1:])):
        raise ValueError("native PM and descriptor regions overlap")
    for name, filename, label, encode in (
            ("mother_page_table", "mother-pages.tsv", "runtime mother page table", mother_page_table_bytes),
            ("runtime_asset_table", "runtime-assets.tsv", "runtime asset table", runtime_asset_table_bytes),
            ("mother_target_table", "mother-targets.tsv", "runtime mother target table", mother_target_table_bytes)):
        table = root / filename
        if name in manifest or table.exists():
            expected = encode(root, phases)
            if not table.is_file() or table.read_bytes() != expected:
                raise ValueError(f"{label} differs from linked schedule")
            if name in manifest and manifest[name] != asset_table_receipt(filename, expected):
                raise ValueError(f"{label} receipt differs from linked schedule")
    return phases


def mother_page_table_bytes(directory, schedule):
    """Encode ordered (step, page) records and register each distinct DDR image once."""
    root = Path(directory).resolve()
    records, regions = [], {}
    for step, phase in enumerate(schedule):
        if phase["step"] != step or not phase["pages"]:
            raise ValueError(f"invalid mother page schedule step {step}")
        for index, page in enumerate(phase["pages"]):
            image = Path(page["path"])
            base, count, crc, span = (page[key] for key in ("base", "bytes", "crc", "ddr_bytes"))
            if (page["role"] != "mother" or image.parent.resolve() != root
                    or not re.fullmatch(r"[\w.-]+", image.name, flags=re.ASCII)):
                raise ValueError(f"invalid mother page asset {image}")
            asset = image.name, count, crc, span
            first = base not in regions
            if not first and regions[base] != asset:
                raise ValueError(f"conflicting mother PM images at {base:#x}")
            regions[base] = asset
            install = first and not page.get("packed", False)
            records.append(
                f"{step:08x}\t{index:08x}\t{base:012x}\t{count}\t{crc:08x}\t{span}\t{int(install)}\t{image.name}\n"
            )
    if not records:
        raise ValueError("native mother page table is empty")
    ordered = sorted(regions.items())
    if any(base + asset[-1] > following for (base, asset), (following, _) in zip(ordered, ordered[1:])):
        raise ValueError("native mother page table images overlap")
    data = f"{len(records)}\n" + "".join(records)
    return data.encode("ascii")


def mother_target_table_bytes(_directory, schedule):
    """Bind each phase/page to the target mask decoded from its PM bytes."""
    records = []
    for step, phase in enumerate(schedule):
        if phase["step"] != step or not phase["pages"]:
            raise ValueError(f"invalid mother target schedule step {step}")
        for index, page in enumerate(phase["pages"]):
            mask = page["target_mask"]
            if type(mask) is not int or not 0 < mask < 512:
                raise ValueError(f"invalid active LC mask for phase {step} page {index}")
            records.append(f"{step:08x}\t{index:08x}\t{mask:03x}\n")
    if not records:
        raise ValueError("native mother target table is empty")
    return (f"{len(records)}\n" + "".join(records)).encode("ascii")


def mother_descriptor_table_bytes(_directory, schedule):
    """Give each physical mother page its exact permitted descriptor address range."""
    records = []
    previous_end = 0
    for step, phase in enumerate(schedule):
        if phase["step"] != step or not phase["pages"]:
            raise ValueError(f"invalid descriptor range schedule step {step}")
        arena = phase["descriptors"]
        arena_start, arena_end = arena["base"], arena["base"]+arena["bytes"]
        for index, page in enumerate(phase["pages"]):
            address, count = page["descriptor_base"], page["descriptor_bytes"]
            if (address % 128 or count <= 0 or count % 128 or address < previous_end or
                    not arena_start <= address < address+count <= arena_end < 1 << 48):
                raise ValueError(f"invalid descriptor range for step {step} page {index}")
            records.append(f"{step:08x}\t{index:08x}\t{address:012x}\t{count}\n")
            previous_end = address+count
    if not records:
        raise ValueError("native mother descriptor ranges are empty")
    return (f"{len(records)}\n" + "".join(records)).encode("ascii")


def runtime_asset_table_bytes(directory, schedule):
    """Emit descriptor arenas and local PM installations for a verified schedule.

    Records give step, kind (D=arena, L=local PM), target (zero for D),
    48-bit DDR base, logical bytes, CRC32, DDR span, first registration, path.
    Every L row is an installation, including rows reusing registered bytes.
    """
    root = Path(directory).resolve()
    records, regions = [], {}
    for step, phase in enumerate(schedule):
        if phase["step"] != step:
            raise ValueError(f"invalid runtime asset schedule step {step}")
        assets = [("D", 0, phase["descriptors"])]
        assets.extend(("L", target, image) for target, image in sorted(phase["locals"].items()))
        for kind, target, asset in assets:
            path = Path(asset["path"]).resolve().relative_to(root).as_posix()
            base, count, crc = (asset[key] for key in ("base", "bytes", "crc"))
            if kind == "D":
                if path != f"phase-{step}/descriptors.bin":
                    raise ValueError(f"invalid descriptor arena path {path}")
                span = count
            else:
                if (asset["role"] != "local" or not re.fullmatch(r"program-[0-9]+\.ddr\.bin", path)
                        or type(target) is not int or not 0 <= target < (1 << 32)):
                    raise ValueError(f"invalid local PM asset {path}")
                span = asset["ddr_bytes"]
            identity = kind, path, count, crc, span
            first = base not in regions
            if not first and regions[base] != identity:
                raise ValueError(f"conflicting runtime assets at {base:#x}")
            regions[base] = identity
            records.append(
                f"{step:08x}\t{kind}\t{target:08x}\t{base:012x}\t{count}\t{crc:08x}\t"
                f"{span}\t{int(first)}\t{path}\n"
            )
    if not records:
        raise ValueError("native runtime asset table is empty")
    return (f"{len(records)}\n" + "".join(records)).encode("ascii")


def asset_table_receipt(filename, data):
    return dict(file=filename, bytes=len(data), entries=int(data.split(b"\n", 1)[0]),
                sha256=sha256(data).hexdigest())


def write_mother_page_table(path, schedule):
    output = Path(path)
    output.write_bytes(mother_page_table_bytes(output.parent, schedule))


def write_product_mother_pages(directory):
    root = Path(directory)
    output = root / "mother-pages.tsv"
    write_mother_page_table(output, load_program_schedule(root))
    return output
