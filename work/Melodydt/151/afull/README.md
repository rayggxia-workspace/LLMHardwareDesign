Actual first r01 result: source 08e674a272a74810e761fadd2d047285e0b1e0ff, Slurm95793/node1/c64/8CPU COMPLETED0:0/00:04:32, 32 CASEs and 9 actual dump SHA checks PASS. See [report](../../../../docs/W4_AFULL_IMPLEMENTATION.md), [run receipt](evidence/runs/r01/results/run-receipt.json) and [current roadmap](roadmap-update.json). Preparation wording below records source-time intent; actual acceptance is bounded synthetic Sq2 integer Attention, not model quality.

# L4-A-FULL implementation and evidence workspace

Issue151 / PR152, Melodydt. Input research commit cddcdc2d38b588d23ffb082eefabaaf1ad606772; branch task/151-six-connection-study, PR base task/143-seven-block-v2. Local partial API package is work/Melodydt/151/afull-cddcdc2/integrated, not a Git checkout. Original 50 RTL/TB/include files remain unchanged.

This task integrates the previously separate AH2 context and ATSP residual mechanisms into one M/N/E/S/T resource set for H1024, Sq2, KV8, Q16, D128. It produces the full 8192-byte context, executes full-K2048 Wo, adds the original 4096-byte residual and reuses the same T only after its original transaction is actually released. M1/N1/E1/S1/T1 is a conditional serial construction, not a physical qualification or throughput claim.

- Formal RTL/TB: project/rtl/block_connection_w4/block_w4_afull_top.sv and project/tb/block_connection_w4/block_w4_afull_tb.sv.
- Interface and lifetime: docs/rtl-contracts/AFULL_PORTS_AND_LIFETIME.md.
- build_afull_vectors.py and fixture-contract.json: independent mathematical reference, full tile-major 6MiB weight streams, stage values and fixed file fingerprints.
- afull-tb-contract.json: predeclared CASE order, compile/include closure and nine actual input/weight/output dump fingerprints.
- run_afull_job.py: source-bound Slurm-only Verilator runner; checks all source and generated file hashes before/after execution and real handshake dump hashes.
- evidence/: actual receipts, commands, tool versions, source manifests, logs and hash indices when received. Runtime binaries, vectors, weights and build trees stay in the authorized server directory.

Selected integer profile remains S16 Fin10, projection S8 Fin7, epsilon_code1, positions0/1 theta1e6, exact-U16 EXP replay and explicit RNE/clip. Synthetic fixture acceptance is separate from trained-model quality, framework agreement, decode/cache, real A-to-F, generic L5 coordination, MEM platform and physical M11/M12 product binding. The historical 24 real-target GAP decisions are not changed.

All RTL compilation/simulation is restricted to server yuzelu@10.129.166.172, under /public/home/yuzelu/Melodydt/LLMHardwareDesign/issue151/afull-cddcdc2-20261103, with Slurm job name zenanyan-afull and an 8-CPU allocation. New attempts use new input/output directories and preserve failed attempts. Implementation preparation is not a simulation PASS; actual results will be recorded separately after execution.
