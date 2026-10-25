# Issue91 V/S structural integration

This directory validates candidate address/lifetime contracts and **symbolic line transactions**, not tensors, integer values, hardware cycles or RTL. The bounded profiles use one 16 KiB 128-bit 1RW store. See [the design contract](../../../docs/V_S_INTEGRATION_CONTRACT_V1.md) and [layered acceptance](../../../docs/BLOCK_LIBRARY_ACCEPTANCE.md).

`contract.json` freezes shapes, byte widths, physical windows, logical register obligations and eight layouts (two deliberately invalid). `layout.py` generates four full line traces. `verify.py` does not import the generator: it checks exact source/output addresses, symbolic value provenance, whole-H statistics before any output, gamma lease/credit/release, in-place X/Y safety, finite source and output holders, unaccessed A/frame/gap and independent complete-I/O count formulae. No arithmetic value is calculated; counts do not prove a cycle-level arbiter or numerical correctness.

Run from repo root using the existing Python environment; only standard library needed. These small pure structural checks may run on the PC. Actual tensors, new RTL/synthesis and numerical receivers remain server-only.

```text
python -B scripts/check_project.py
python -B -m unittest discover -s project/experiments/v_integration -p "test_*.py" -v
# First commit code/config: the runner rejects any uncommitted bound source.
python -B project/experiments/v_integration/layout.py --out NEW_STRUCTURAL_DIR
python -B project/experiments/v_integration/verify.py --folder NEW_STRUCTURAL_DIR --out NEW_RECEIPT.json
```

The runner binds code/config plus14 reused actual sources to original Git bytes. Output directories/receipt must be new. Gzip traces have deterministic mtime0 and SHA-256; results are small enough for Git. No real source arrays, weights, credentials or hardware executables are included.

The norm-only traces count X/G input staging, all global-statistic/output reads, Y writes and output drain. The5×128-bit prototype wire count excludes tag bits, descriptor/config traffic, microcode/LUT/frame operations and software packing; it is not a physical packet estimate or timing result. Source X/G is initially external and immutable. If M produces X on chip, the streaming-X case additionally needs a separately charged spill/producer schedule; do not reuse the norm-only delta as measured end-to-end gain.

The `h1536_resident_existing` label means the existing address capacity layout; its abstract load schedule is not a replay of the current85 cycle trace. `frame_active` reserves the frame but does not execute a V program. Backpressure, RMW locks, epoch/cfg/error handling and all numerical arithmetic remain future RTL tests listed in the contract.
