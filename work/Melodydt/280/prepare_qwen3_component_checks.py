"""Prepare independent RTL fixtures using the replay's real PM bytes and ADD2 extent."""
from hashlib import sha256
import json
from pathlib import Path
from struct import pack_into, unpack_from
import sys

project, assets, output = map(Path, sys.argv[1:])
page = assets / "pos513-l0-mc-0.bin"
pm = page.read_bytes()
if len(pm) != 1664:
    raise ValueError("unexpected Qwen3 mother program size")
for size in (len(pm), 352):
    data = pm[:size] + b"\x00" * ((-size) % 64)
    (output / f"pm-{size}.hex").write_text("".join(
        data[start:start + 64][::-1].hex() + "\n" for start in range(0, len(data), 64)
    ))

source = assets / "pos513-l0-descriptors.bin"
data = source.read_bytes()
add = [(i, unpack_from("<4H", data, i + 16)) for i in range(0, len(data), 128)
       if unpack_from("<IHHI", data, i) == (3, 128, 2, 0x02500002)]
if len(add) != 2 or any(args != (0, 256, 0, 256) for _, args in add):
    raise ValueError("unexpected Qwen3 ADD2 extent")

records = []
for dest in (0, 1):
    descriptor = bytearray(128)
    pack_into("<IHHII", descriptor, 0, 3, 128, 2, 7, 9)
    pack_into("<4H", descriptor, 16, 0, 256, dest, 256)
    records.append(descriptor[::-1].hex())
(output / "add.hex").write_text("\n".join(records) + "\n")

fixture = project / "experiments/block_local_native/test_native_add_scope.sv"
rtl = fixture.read_text()
for before, after, count in (
    ("i<3", "i<256", 2),
    ("10'(4+i)", "10'(256+i)", 1),
    ("check_terminal(0,48);", "check_terminal(0,4096);", 1),
    ("PASS native ADD2 3 exact SRAM words", "PASS native ADD2 256 exact SRAM words", 1),
    ("        string image;", """        string image, wave;
        if (!$value$plusargs("WAVE=%s",wave)) $fatal(1,"missing ADD2 waveform");
        $dumpfile(wave);
        $dumpvars(2,test_native_add_scope);""", 1),
):
    if rtl.count(before) != count:
        raise ValueError(f"unexpected ADD2 fixture anchor: {before}")
    rtl = rtl.replace(before, after)
(output / "test_native_add_scope.sv").write_text(rtl)
(output / "inputs.json").write_text(json.dumps({
    "files": {str(f): sha256(f.read_bytes()).hexdigest() for f in (page, source, fixture)},
    "add2": add, "add2_payload": "Deterministic functional fixture",
    "pm_cases_bytes": [len(pm), 352],
}, indent=2) + "\n")
