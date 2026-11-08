"""Static checks for proposed P control contracts. No RTL or execution model."""
import argparse
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "control_isa_v0_1"))
import codec

REGISTRY = json.loads((HERE / "services.json").read_text(encoding="utf-8"))
PROFILE_DATA = json.loads((HERE / "profiles.json").read_text(encoding="utf-8"))
PROFILES = {p["id"]: p for p in PROFILE_DATA["profiles"]}
SERVICES = {(s["resource"], s["service"], s["native_op"]): s
            for s in REGISTRY["services"]}
ABI = REGISTRY["native_abi_id"]


def require(condition, message):
    if not condition:
        raise ValueError(message)


def record(name, values):
    return codec.unpack_record(name, codec.pack_record(name, values))


def object_table(values, profile):
    result = {}
    for value in values:
        obj = record("object", value)
        oid = obj["object_id"]
        require(oid not in result, "duplicate object_id")
        require(obj["kind"] == 0 and obj["native_abi_id"] == ABI,
                "object must use local S and this research ABI")
        require(obj["base_reg"] == 255 and obj["length_reg"] == 255,
                "dynamic objects are not registered in static profile")
        require(obj["base_bytes"] % 16 == 0 and obj["capacity_bytes"] % 16 == 0,
                "object allocation must use complete 16-byte words")
        require(obj["length_bytes"] <= obj["capacity_bytes"],
                "logical object length exceeds capacity")
        require(obj["base_bytes"] + obj["capacity_bytes"] <= profile["s_bytes"],
                "object exceeds actual S capacity")
        for previous in result.values():
            a, b = obj["base_bytes"], previous["base_bytes"]
            require(a + obj["capacity_bytes"] <= b or
                    b + previous["capacity_bytes"] <= a,
                    "static object allocations overlap")
        result[oid] = obj
    return result


def check_request(request):
    allowed = {"profile", "execution", "objects", "instruction", "descriptor_index"}
    require(not (set(request) - allowed), "unknown request field")
    require(request["profile"] in PROFILES, "unregistered profile")
    profile = PROFILES[request["profile"]]
    desc = record("execution", request["execution"])
    key = desc["resource"], desc["service"], desc["native_op"]
    require(desc["native_abi_id"] == ABI, "unregistered native ABI")
    require(key in SERVICES, "unregistered resource/service/native_op")
    require(profile["resource_mask"] & (1 << desc["resource"]),
            "resource absent from profile")
    require(desc["context_id"] == 0, "only physical context0 is registered")
    for field in ["count_reg", "src0_offset_reg", "src1_offset_reg",
                  "src2_offset_reg", "dst_offset_reg", "parameter_index_reg"]:
        require(desc[field] == 255, "dynamic fields deferred: " + field)
    require(desc["parameter_ref"] == 0 and desc["parameter_bytes"] == 0,
            "parameter provider not registered")
    service = SERVICES[key]
    require(desc["completion"] == service["completion"],
            "unsupported completion strength for service")
    if "instruction" in request:
        ins = request["instruction"]
        codec.encode_instruction(ins, "local")
        require(ins.get("op") == "L_EXEC", "expected L_EXEC")
        require(ins.get("a", 0) == desc["resource"], "L_EXEC resource mismatch")
        require("descriptor_index" in request and
                ins.get("c", 0) == request["descriptor_index"],
                "L_EXEC descriptor index mismatch")
    objs = object_table(request.get("objects", []), profile)
    native = [desc["native%d" % i] for i in range(8)]
    used = set()
    required_checks = [service["runtime_guards"]]
    locks = []
    wire = {}

    def route(name):
        require(name in profile["routes"], "unconnected route: " + name)

    def window(field, extent, fmt):
        used.add(field)
        oid = desc[field]
        require(oid in objs, "missing object: " + field)
        obj = objs[oid]
        offset = desc[field + "_offset"]
        formats = fmt if isinstance(fmt, tuple) else (fmt,)
        require(obj["format"] in formats, "object format mismatch: " + field)
        require(offset % 16 == 0, "unaligned word window: " + field)
        require(extent > 0 and offset + extent <= obj["length_bytes"],
                "window exceeds logical object: " + field)
        address = obj["base_bytes"] + offset
        required_checks.append(field + (" reservation/version/owner must permit writes; "
                               "data remains invalid until actual ACK" if field == "dst" else
                               " validity/version/owner and data contents must be checked "
                               "by runtime; initial_valid=0 is not readiness"))
        return address

    resource, family, op = key
    if resource == 0:
        require(native[0] < 64 and not any(native[3:]),
                "M index overflow or unused native words")
        index = native[0]
        data = native[1] | (native[2] << 32)
        wire = dict(cmd_op=op, cmd_index=index, cmd_data=data)
        locks = ["M.command", "M.result_context0"]
        if op in (3, 12):
            require(index & 7 < 4 and data == 0, "invalid M pair read")
        elif op == 4:
            require(index == 0 and data >> 21 == 0, "invalid M scale fields")
        elif op == 5:
            require(index & 7 < 2 and data >> 10 == 0 and
                    (data >> 8) & 3 < 3 and (data >> 6) & 3 == 0,
                    "invalid M rounded read fields")
        elif op == 6:
            require(index == 0 and data == 0, "invalid M clear-all")
        elif op == 10:
            require(index & 31 == 0 and data >> 19 == 0 and not data & 8,
                    "invalid M GEMM reserved bits")
            last_k, columns = (data >> 4) & 15, (data >> 8) & 15
            tiles, rows = (data >> 12) & 7, (data >> 15) & 15
            require(1 <= last_k <= 8 and 1 <= columns <= 8 and
                    1 <= tiles <= 4 and 1 <= rows <= 8,
                    "invalid M GEMM geometry")
            locks.append("M.operand_bank%d" % (index >> 5))
        elif op == 11:
            require(index < 2 and data == 0, "invalid M operand-bank clear")
            locks.append("M.operand_bank%d" % index)
        if family == 0:
            require(desc["count"] == 0 and desc["stride_bytes"] == 0,
                    "M command has no object stream")
        else:
            route("M.rsp_to_S.client0")
            require(desc["count"] == 1 and desc["stride_bytes"] == 16,
                    "readout is one RAW 128-bit response")
            address = window("dst", 16, (2, 4) if op == 5 else 4)
            wire["destination_word_address"] = address // 16
            required_checks.append("capture M response then consume real S client0 write ACK; "
                                   "native response alone cannot complete LOCAL_STORED")
    elif resource == 3:
        route("S.client1_to_G.adapter")
        route("G.adapter_to_S.client1")
        require(native[0] < 2 and not any(native[1:]),
                "invalid G gate flag or unused native words")
        count = desc["count"]
        require(2 <= count <= 2048 and count % 2 == 0 and
                desc["stride_bytes"] == 8, "G needs whole S words, two packets per word")
        addresses = dict(source=window("src0", count * 8, 2),
                         destination=window("dst", count * 8, 2))
        if native[0]:
            addresses["gate"] = window("src1", count * 8, 2)
        ids = [desc[f] for f in used]
        require(len(set(ids)) == len(ids), "in-place/aliased G objects not registered")
        wire = dict(in_fn=op, in_gated=native[0], packets=count,
                    storage_container_bits=32, native_value_bits=16,
                    byte_addresses=addresses)
        locks = ["G.stream", "S.client1"]
        required_checks.append("source S32 containers must be sign-extended S16; "
                               "track Q5.10 input/gate and Q1.14 ungated sigmoid output; "
                               "aggregate packet errors/saturation and actual S write ACKs")
    else:
        route("S.feeder_to_M.A")
        route("S.feeder_to_M.B")
        require(native[0] < 2 and 1 <= native[1] <= 8 and
                1 <= native[2] <= 4 and native[3] < 8 and not any(native[4:]),
                "invalid feeder fields")
        require(desc["count"] == 1 and desc["stride_bytes"] == 0,
                "feeder is one bounded command")
        bank, rows, tiles, flags = native[:4]
        a_extent = tiles * (128 if rows > 4 else 64)
        a_address = window("src0", a_extent, 4)
        b_address = 0
        if not flags & 4:
            b_extent = tiles * (128 if flags & 2 else 64)
            b_address = window("src1", b_extent, 4)
        require(a_address % 64 == 0 and b_address % 64 == 0,
                "feeder needs 64-byte aligned bases")
        wire = dict(load_bank=bank, load_rows=rows, load_tiles=tiles,
                    load_a_wide=flags & 1, load_b_wide=(flags >> 1) & 1,
                    load_reuse_b=(flags >> 2) & 1,
                    load_a_base=a_address // 16, load_b_base=b_address // 16)
        locks = ["S.feeder", "M.operand_bank%d" % bank]
        required_checks.append("consume done_valid&&done_take and done_error after "
                               "all A/B transfers retire; busy=0 is not sufficient")
    for field in ["src0", "src1", "src2", "dst"]:
        if field not in used:
            require(desc[field] == 255 and desc[field + "_offset"] == 0,
                    "unused object reference/offset: " + field)
    return dict(static_fields_valid=True, deployable=False, service=service["name"],
                profile=profile["id"], proposed_wire_mapping=wire, required_locks=locks,
                context_effect=service["context_effect"], runtime_checks_pending=required_checks,
                boundary="No instruction execution, numerical computation, adapter RTL "
                         "or physical connectivity is validated here")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["examples"])
    args = parser.parse_args()
    examples = json.loads((HERE / "examples.json").read_text(encoding="utf-8"))
    output = [dict(name=row["name"], result=check_request(row["request"]))
              for row in examples["cases"]]
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
