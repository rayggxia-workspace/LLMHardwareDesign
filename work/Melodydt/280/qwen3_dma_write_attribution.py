"""Verify Qwen3 DDR write attribution against the descriptors actually replayed."""

from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
from struct import unpack_from
import sys


rollup_file, replay, destination = map(Path, sys.argv[1:])
rollup = json.loads(rollup_file.read_bytes())
windows = {
    "prefill": ("prefill-w4-tile128-pr272-combined", (0, 1)),
    "first_token": ("decode-live-w4-tile128-pr272-combined", (512,)),
    "decode": ("decode-live-w4-tile128-pr272-combined", (513,)),
}
result = {"rollup_sha256": sha256(rollup_file.read_bytes()).hexdigest(), "windows": {}}
for name, (stage, positions) in windows.items():
    groups = Counter()
    inputs = {}
    for position in positions:
        for layer in range(28):
            rel = Path(stage) / "assets" / f"pos{position}-l{layer}-descriptors.bin"
            data = (replay / rel).read_bytes()
            if not data or len(data) % 128:
                raise ValueError(f"invalid descriptor alignment: {rel}")
            inputs[str(rel)] = sha256(data).hexdigest()
            layer_groups = Counter()
            for offset in range(0, len(data), 128):
                schema, size, op, abi = unpack_from("<IHHI", data, offset)
                if size != 128:
                    raise ValueError(f"unexpected descriptor size: {rel}@{offset}")
                if (schema, op, abi) == (3, 2, 0x02500002):
                    layer_groups["local_u_residual_calls"] += 1
                if (schema, op, abi) == (9, 1, 8):
                    address, _, words = unpack_from("<QHH", data, offset + 16)
                    if address % 64 or words != 32:
                        raise ValueError(f"unexpected DMA store footprint: {rel}@{offset}")
                    if 1 << 33 <= address < 15 << 30:
                        layer_groups["kv_bursts"] += words // 4
                    elif 15 << 30 <= address < (15 << 30) + 56 * 3072 * 4:
                        layer_groups["ffn_backing_bursts"] += words // 4
                    else:
                        raise ValueError(f"unrecognized DMA write address: {address:#x}")
            if layer_groups != {"local_u_residual_calls": 2, "kv_bursts": 128, "ffn_backing_bursts": 192}:
                raise ValueError(f"unexpected per-layer write attribution: {rel}: {layer_groups}")
            groups.update(layer_groups)
    accepted = rollup["windows"][name]["dma_transport_events"]["write"]
    total = groups["kv_bursts"] + groups["ffn_backing_bursts"]
    if any(accepted[key] != total for key in ("submitted", "accepted", "completed")):
        raise ValueError(f"write descriptors do not reconcile with replay: {name}")
    result["windows"][name] = {**groups, "ddr_write_bursts": total, "descriptor_sha256": inputs}

with destination.open("x", encoding="utf-8") as stream:
    json.dump(result, stream, indent=2)
    stream.write("\n")
