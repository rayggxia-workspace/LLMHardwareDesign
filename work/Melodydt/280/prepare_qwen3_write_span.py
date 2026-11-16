"""Translate actual Qwen3 DMA descriptors to the eight-beat C639 writer ABI."""
import json
from hashlib import sha256
from pathlib import Path
from struct import pack_into, unpack_from
import sys

source, output = map(Path, sys.argv[1:])
data = source.read_bytes()
cases = {}
kv = []
for offset in range(0, len(data), 128):
    if unpack_from("<IHHI", data, offset) != (9, 128, 1, 8):
        continue
    address, word, words = unpack_from("<QHH", data, offset + 16)
    if words != 32 or address % 64:
        raise ValueError("Qwen3 write span differs")
    if 1 << 33 <= address < 15 << 30:
        kv.append((offset, address, word))
    elif 15 << 30 <= address < (15 << 30) + 56 * 3072 * 4:
        cases.setdefault("ffn", (offset, address, word))
if len(kv) != 16 or "ffn" not in cases:
    raise ValueError("missing qualified K, V or activation writes")
cases.update(k=kv[0], v=kv[1])
receipt = {
    "source": str(source), "source_sha256": sha256(data).hexdigest(),
    "payload": "Deterministic nonzero test words. Uses true Qwen3 source and destination addresses.",
    "cases": {},
}
for name, (offset, address, word) in cases.items():
    descriptor = bytearray(128)
    schema = 0x31535744 if name == "ffn" else 0x3152564B
    pack_into("<IHHII", descriptor, 0, schema, 128, 2 if name == "v" else 1, 0x02500002, 25001)
    pack_into("<H6xQQ", descriptor, 16, word, address, address // 64)
    (output / f"{name}.hex").write_text(descriptor[::-1].hex() + "\n")
    receipt["cases"][name] = dict(offset=offset, address=address, source_word=word, ddr_beats=8)
(output / "descriptors.json").write_text(json.dumps(receipt, indent=2) + "\n")
