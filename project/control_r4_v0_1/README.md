# R4 real-provider control research

Issue179 / Draft PR180; owner Melodydt. This bounded RAW16/P transfer profile
extends the existing MC and LC qualification with real private S, native DMA and
cohort reset. It does not implement complete P/U/C/F/J Blocks.

`contract.json` pins six unchanged source dependencies from PR178 and PR182.
`check_contract.py` performs static source/port checks, not simulation.

- `lc_raw16_s_adapter.sv`: one service/context; fixed RX/TX private-S clients;
  receive-store ACK waits for the real write response, transmit reads real S.
- `raw16_dma_bridge.sv`: one word/descriptor, one full 141-bit identity per S,
  separate monotonic 16-bit tag; no wrap before certified cohort reset. LOAD
  waits for actual S write ACK, STORE for external write ACK; bad or missing
  completions retain ownership and isolate.
- `cohort_reset_controller.sv`: eight-member ACK bitmap, minimum reset, quiet
  interval, full three-image PREPARE gate and increasing reset sequence,
  generation and epoch. ACKs are trusted management-side provider certificates.
  The module does not create a production reset tree or prove CDC/MTBF.

The integration fixtures instantiate actual MC + two LC + two private 16KiB S
and, in the DMA/reset campaigns, actual `hbm_group_dma` and two async FIFOs.
The 64-word external native memory is an explicit finite test peer, not AXI,
HBM, a PHY or an M11/M12 data link. Test clock ratio is 5:3, without STA claims.

Run simulations only in the authorized server Slurm/Singularity environment:

```bash
python3 -B project/control_r4_v0_1/run_real_s.py --verilator /eda/verilator-5.042/bin/verilator --out /work/results/real_s
python3 -B project/control_r4_v0_1/run_real_dma.py --verilator /eda/verilator-5.042/bin/verilator --out /work/results/real_dma
python3 -B project/control_r4_v0_1/run_reset.py --verilator /eda/verilator-5.042/bin/verilator --out /work/results/reset
```

Each runner compiles with warnings enabled, runs typed binary images, records
commands, tool versions and input/output hashes, and applies an independent
observer. Bridge/coordinator directed benches use explicitly bounded peers.
Raw logs and executable builds stay in the member's server directory; report
JSON and SHA indices under `work/Melodydt/179/control-r4-*` provide provenance.
The maintained research report and its stable PDF are in `docs/local-blocks/`.

Production provider reset ACK transport, M/G active-compute reset membership,
RX-close, native flit/M11/M12 transport, general scheduling/liveness, synthesis,
STA/physical power/area and model numerical correctness remain outside these
bounded gates. Retained payload is not retained object or program validity.
