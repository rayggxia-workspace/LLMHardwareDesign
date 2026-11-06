#!/usr/bin/env python3
"""Adapt the immutable #195 regression bundle to exercise the new C/F/J RTL."""
import hashlib
import shutil
import sys
import tarfile
from pathlib import Path

root = Path(__file__).resolve().parents[3]
source = Path(sys.argv[1])
bundle = Path(sys.argv[2])
if hashlib.sha256(source.read_bytes()).hexdigest() != "3387aa6f05f5fdd658e0ce326fce70fd694200c1882a4a5941c4fa6ddafea281":
    raise ValueError("unexpected #195 bundle digest")
bundle.mkdir(parents=True, exist_ok=False)
with tarfile.open(source) as archive:
    archive.extractall(bundle, filter="data")

design = bundle / "design"
native = bundle / "staged/native"
pj = bundle / "staged/pj/project/rtl"
for name in ("block_feed_s16k_sram.sv", "local_s_base.sv"):
    shutil.copyfile(root / "project/rtl/s_sram" / name, native / name)
shutil.copyfile(root / "project/rtl/block_v2/block_v2_e_compact.sv", native / "block_v2_e_compact.sv")
for rtl in (root / "project/rtl/block_cfj_v1").glob("*.sv"):
    if rtl.name in ("pj_mem_port.sv", "pj_sram_client.sv"):
        target = pj / "block_pj_v1" / rtl.name
    elif rtl.name.startswith("ucf_"):
        target = native / rtl.name
    else:
        target = design / rtl.name
    shutil.copyfile(rtl, target)
bench = design / "tb_native_local.sv"
text = bench.read_text()
start = text.index("        block_ucf16 #(.KIND(KIND))")
end = text.index("\n\n", start)
bind = text[start:end]
text = text[:start] + (
    "        if (KIND==0) begin: old_u_reference\n" + bind +
    "\n        end else begin: compact_cf\n" + bind.replace("block_ucf16", "block_cfj_cf") +
    "\n        end"
) + text[end:]
bench.write_text(text)
bench = design / "tb_pj_endpoint.sv"
text = bench.read_text()
assert text.count("block_j16 block") == 1
bench.write_text(text.replace("block_j16 block", "block_cfj_j block"))
