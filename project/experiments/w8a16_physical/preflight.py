"""Check measured area and explicitly priced resources before physical acceptance.

Passing this check only means that the declaration is internally consistent.
Native routed gates remain mandatory; no field grants inherited qualification.
"""
import argparse
import json
from pathlib import Path

from baseline import BASELINE


def resource_ledger():
    old = dict(down=11008, b_double=2304, a_double=512, gate_up=1024, mid=1024, control=512)
    conservative = dict(old, down=2752)
    mid32 = dict(conservative, mid=512)
    weight_replacement = dict(conservative, b_double=4608)
    return dict(schema="issue250-storage-options/1", status="Capacity arithmetic, not a frozen hardware allocation",
        private_usable_bytes=16384,
        old=sum(old.values()), down_s32_conservative=dict(parts=conservative, bytes=sum(conservative.values())),
        down_mid_s32=dict(parts=mid32, bytes=sum(mid32.values())),
        independent_x_bytes=0, x_in_private_s_bytes=4096,
        four_weight_banks=dict(count=4, bytes_each=1152, total_bytes=4608,
            relation="Must explicitly replace the old 2304B double-B or be an additional physical buffer; never count as free"),
        weight_replaces_double_b=dict(parts=weight_replacement, bytes=sum(weight_replacement.values()),
            with_x_bytes=sum(weight_replacement.values())+4096,
            with_x_remaining_bytes=16384-sum(weight_replacement.values())-4096),
        projection_context_register_bytes=16*8*4,
        projection_context_location="Separate register/context resource; do not silently charge twice to private SRAM",
        g_table=dict(entries=257, bits_per_entry=32, logical_bytes=257*4, lanes=2,
            lookups_per_lane=2, simultaneous_lookups=4,
            physical_implementation="Unmeasured. Four adjacent-point read services may duplicate logic or storage; report actual result"),
        shared_pool=dict(usable_bytes=32768, lvt_enabled=False,
            physical_bytes_minimum=32768, same_4kib_bank_count_if_reused=8,
            same_bank_outline_area_um2_if_reused=2*369848.2001,
            area_scope="Conditional sum of accepted bank outlines only; excludes pool logic, pins, PG, gaps and routing"))


def check(candidate, baseline):
    errors = []
    kind = candidate.get("baseline_class")
    if kind not in baseline["macros"]:
        return ["baseline_class must name an existing measured main leaf"]
    base = baseline["macros"][kind]
    area = candidate.get("area", {})
    keys = ["outline_um2", "core_um2", "functional_stdcell_um2", "hardmacro_outline_um2", "physical_only_um2"]
    if any(not isinstance(area.get(k), (int, float)) or area[k] < 0 for k in keys):
        errors.append("all five area terms must be separately measured nonnegative numbers")
    elif area["outline_um2"] <= 0 or area["core_um2"] <= 0 or area["core_um2"] > area["outline_um2"]:
        errors.append("outline/core geometry is invalid")
    else:
        useful = area["functional_stdcell_um2"] + area["hardmacro_outline_um2"]
        if useful + area["physical_only_um2"] > area["outline_um2"] + 1e-6:
            errors.append("instance areas exceed outline: check overlap or hierarchical double counting")
        if area.get("source") != "final_odb" or not area.get("excludes_filler_tap_endcap_antenna"):
            errors.append("use final ODB geometry and the compact baseline exclusion policy")
        if useful/area["outline_um2"] + 1e-10 < base["occupied_outline_ratio"]:
            errors.append("functional occupied/outline ratio falls below corresponding main compact baseline")
        if useful/area["core_um2"] + 1e-10 < base["occupied_core_ratio"]:
            errors.append("functional occupied/core ratio falls below corresponding main compact baseline")
    pins = candidate.get("pins", {})
    ports = pins.get("rtl_ports", [])
    if not ports or any(not isinstance(p.get("width"), int) or p["width"] <= 0 for p in ports):
        errors.append("declare every native signal/clock RTL port and its width")
    elif len({p.get("name") for p in ports}) != len(ports):
        errors.append("duplicate RTL ports")
    elif sum(p["width"] for p in ports) != pins.get("final_odb_signal_bits"):
        errors.append("RTL port bits and final ODB native pin inventory differ")
    for key in ["exact_final_pin_readback", "simultaneous_escape", "native_pg_checked", "halo_and_obstacles_checked"]:
        if pins.get(key) is not True:
            errors.append(f"pins.{key} remains unproved")
    for storage in candidate.get("storage", []):
        logical, physical = storage.get("usable_bytes"), storage.get("physical_bytes")
        if not isinstance(logical, int) or not isinstance(physical, int) or physical < logical:
            errors.append("storage needs separate usable/physical byte counts, with physical >= usable")
        if storage.get("lvt_enabled"):
            errors.append("LVT SRAM duplication is disabled for this candidate plan")
        if not storage.get("implementation") or not storage.get("read_write_conflict_policy"):
            errors.append("storage implementation, ports and read/write conflict policy must be priced")
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", type=Path)
    parser.add_argument("--ledger", type=Path)
    args = parser.parse_args()
    if args.ledger:
        args.ledger.write_text(json.dumps(resource_ledger(), indent=2)+"\n", encoding="utf-8", newline="\n")
    if args.candidate:
        result = check(json.loads(args.candidate.read_text(encoding="utf-8")),
                       json.loads(BASELINE.read_text(encoding="utf-8")))
        print(json.dumps(dict(declaration_preflight_passed=not result, issues=result,
            physical_qualified=False, scope="Arithmetic/interface preflight only; original routed acceptance gates remain required"), indent=2))
        if result:
            raise SystemExit(1)


if __name__ == "__main__":
    main()
