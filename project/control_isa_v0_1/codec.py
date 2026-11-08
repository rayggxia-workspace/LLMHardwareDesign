"""Bit-exact proposed two-level ISA v0.1 codec; no hardware or model execution."""
import argparse
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCHEMA = json.loads((HERE / "isa.json").read_text(encoding="utf-8"))
OPS = {op["name"]: op for op in SCHEMA["opcodes"]}
CODES = {op["opcode"]: op for op in SCHEMA["opcodes"]}

def integer(value):
    if isinstance(value, bool):
        raise ValueError("Boolean is not an integer operand")
    if isinstance(value, str):
        return int(value, 0)
    if type(value) is not int:
        raise ValueError("Expected an integer or 0x-prefixed string")
    return value

def instruction_spec(name, role):
    if role not in SCHEMA["roles"]:
        raise ValueError("Unknown role")
    if name not in OPS:
        raise ValueError("Unknown opcode name: " + str(name))
    spec = OPS[name]
    if spec["role"] not in (role, "both"):
        raise ValueError("Opcode is illegal for role " + role)
    return spec

def encode_instruction(instruction, role):
    if not isinstance(instruction, dict) or "op" not in instruction:
        raise ValueError("Instruction must be an object with op")
    spec = instruction_spec(instruction["op"], role)
    field_names = {f["name"] for f in SCHEMA["fields"]} - {"opcode"}
    if set(instruction) - field_names - {"op"}:
        raise ValueError("Unknown instruction field")
    allowed = {o["field"]: o for o in spec["operands"]}
    result = spec["opcode"] << 120
    for f in SCHEMA["fields"]:
        name = f["name"]
        if name == "opcode":
            continue
        value = integer(instruction.get(name, 0))
        if not 0 <= value < (1 << f["bits"]):
            raise ValueError("Operand width overflow: " + name)
        if name not in allowed and value != 0:
            raise ValueError("Reserved/non-operand field must be zero: " + name)
        if name in allowed:
            bounds = allowed[name]
            if not bounds["min"] <= value <= bounds["max"]:
                raise ValueError("Operand range error: " + name)
        result |= value << f["lsb"]
    return result

def decode_instruction(word, role):
    value = integer(word)
    if not 0 <= value < (1 << 128):
        raise ValueError("Instruction must fit 128 bits")
    code = value >> 120
    if code not in CODES:
        raise ValueError("Reserved opcode")
    spec = instruction_spec(CODES[code]["name"], role)
    raw = {f["name"]: (value >> f["lsb"]) & ((1 << f["bits"]) - 1)
           for f in SCHEMA["fields"] if f["name"] != "opcode"}
    checked = dict(raw, op=spec["name"])
    if encode_instruction(checked, role) != value:
        raise ValueError("Noncanonical encoding")
    return dict(op=spec["name"], **{o["field"]: raw[o["field"]] for o in spec["operands"]})

def check_program(program, role):
    if not isinstance(program, list) or not program:
        raise ValueError("Empty program")
    words = [encode_instruction(i, role) for i in program]
    for pc, ins in enumerate(program):
        name = ins["op"]
        if name in ("G_LOOP", "L_LOOP"):
            if not 0 <= integer(ins.get("x", 0)) < pc:
                raise ValueError("LOOP target must be an earlier instruction")
        if name in ("G_BRANCH", "L_BRANCH"):
            for field in ("x", "y"):
                if not pc < integer(ins.get(field, 0)) < len(program):
                    raise ValueError("v0.1 BRANCH target must be forward and within image")
    end = "G_END" if role == "mother" else "L_END"
    fail = "G_FAIL" if role == "mother" else "L_FAIL"
    if program[-1]["op"] not in (end, fail):
        raise ValueError("Last instruction must be END or FAIL")
    return words

def record_value(field, value):
    number = integer(value)
    if not 0 <= number < (1 << field["bits"]):
        raise ValueError("Record field width: " + field["name"])
    if "constant" in field and number != integer(field["constant"]):
        raise ValueError("Wrong constant/version/reserved field: " + field["name"])
    if not field.get("min", 0) <= number <= field.get("max", (1 << field["bits"]) - 1):
        raise ValueError("Record field range: " + field["name"])
    if field["name"].endswith("_reg") and number not in list(range(8)) + [255]:
        raise ValueError("Register selector must be 0..7 or 255")
    if field["name"] in ("src0", "src1", "src2", "dst") and number not in list(range(16)) + [255]:
        raise ValueError("Object selector must be 0..15 or 255")
    return number

def pack_record(name, values):
    if name not in SCHEMA["records"] or not isinstance(values, dict):
        raise ValueError("Unknown record type or non-object input")
    spec = SCHEMA["records"][name]
    names = {f["name"] for f in spec["fields"]}
    if set(values) - names:
        raise ValueError("Unknown record field")
    data = bytearray(spec["bytes"])
    for field in spec["fields"]:
        default = field.get("constant", field.get("default", 0))
        value = record_value(field, values.get(field["name"], default))
        offset, size = field["offset"], field["bits"] // 8
        data[offset:offset+size] = value.to_bytes(size, "little")
    return bytes(data)

def unpack_record(name, data):
    if name not in SCHEMA["records"]:
        raise ValueError("Unknown record type")
    spec = SCHEMA["records"][name]
    if not isinstance(data, bytes) or len(data) != spec["bytes"]:
        raise ValueError("Wrong record byte count")
    values = {f["name"]: int.from_bytes(data[f["offset"]:f["offset"]+f["bits"]//8], "little")
              for f in spec["fields"]}
    if pack_record(name, values) != data:
        raise ValueError("Nonzero reserved gap or noncanonical record")
    return values

def encode_examples():
    source = json.loads((HERE / "examples.json").read_text(encoding="utf-8"))
    programs = []
    for p in source["programs"]:
        words = check_program(p["instructions"], p["role"])
        programs.append(dict(name=p["name"], role=p["role"],
                             instruction_bytes=16,
                             instructions=[dict(pc=pc, assembly=ins,
                                                word_hex=format(word, "032x"),
                                                bytes_le=word.to_bytes(16, "little").hex())
                                           for pc, (ins, word) in enumerate(zip(p["instructions"], words))],
                             stream_bytes_le=b"".join(w.to_bytes(16, "little") for w in words).hex()))
    return dict(schema=source["schema"], scope=source["scope"], programs=programs,
                hardware_executed=False, native_descriptors_semantically_validated=False)

def output_json(value, path):
    text = json.dumps(value, ensure_ascii=False, indent=2) + "\n"
    if path:
        Path(path).write_bytes(text.encode("utf-8"))
    else:
        print(text, end="")

def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)
    examples = sub.add_parser("examples")
    examples.add_argument("--output")
    enc = sub.add_parser("encode")
    enc.add_argument("--role", choices=list(SCHEMA["roles"]), required=True)
    enc.add_argument("--input", required=True)
    enc.add_argument("--output")
    dec = sub.add_parser("decode")
    dec.add_argument("--role", choices=list(SCHEMA["roles"]), required=True)
    dec.add_argument("--word", required=True)
    pack = sub.add_parser("pack-record")
    pack.add_argument("--record", choices=list(SCHEMA["records"]), required=True)
    pack.add_argument("--input", required=True)
    unpack = sub.add_parser("unpack-record")
    unpack.add_argument("--record", choices=list(SCHEMA["records"]), required=True)
    unpack.add_argument("--bytes-le", required=True)
    args = p.parse_args()
    try:
        if args.command == "examples":
            output_json(encode_examples(), args.output)
        elif args.command == "encode":
            program = json.loads(Path(args.input).read_text(encoding="utf-8"))
            words = check_program(program, args.role)
            output_json(dict(words_hex=[format(w, "032x") for w in words],
                             bytes_le=b"".join(w.to_bytes(16, "little") for w in words).hex()), args.output)
        elif args.command == "decode":
            output_json(decode_instruction(args.word, args.role), None)
        elif args.command == "pack-record":
            values = json.loads(Path(args.input).read_text(encoding="utf-8"))
            print(pack_record(args.record, values).hex())
        else:
            output_json(unpack_record(args.record, bytes.fromhex(args.bytes_le)), None)
    except (ValueError, KeyError, OSError) as exc:
        p.exit(2, "ERROR: " + str(exc) + "\n")

if __name__ == "__main__":
    main()
