# Conditional whole-graph timing results

Conditional timing at300MHz, two P plus frozen candidate U. Not real LLM generation, native full-graph execution, numerical model quality, or physical qualification.

No native full-model generation token/s is available. These paired numbers are executions of the declared timing model.

| Workload | Weight | Legacy-program token/s | Context8 token/s | Rate change | Seconds before→after |
|---|---|---|---|---|---|
| decode512 | w8 | 0.067582201 | 0.081740530 | +20.949790% | 14.796795481→12.233833155 |
| decode512 | w16 | 0.044917814 | 0.050525304 | +12.483888% | 22.262882160→19.792063195 |
| decode2048 | w8 | 0.048265124 | 0.055078418 | +14.116391% | 20.718894230→18.155931905 |
| prefill2 | w8 | 0.077239045 | 0.077239045 | +0.000000% | 25.893639820→25.893639820 |

Same-interface context1→8, decode512/W8: 0.064566657→0.081740530 conditional token/s (+26.598672%). Native arithmetic and command counts remain equal; A reuse/packing/LOAD work and DDR ordering change.

## P costs

Do not add summed P work or DMA service to whole-model seconds; two P overlap and DMA wait contains its S service.

### decode512 / w8

| Cost or bytes (two P summed) | Before | After | Delta |
|---|---|---|---|
| native_leaf_cycles | 715369472 | 957327648 | +241958176 |
| command_control_cycles | 109179328 | 344328768 | +235149440 |
| LOAD_wall_cycles | 480046080 | 290203392 | -189842688 |
| local_narrow_cycles | 4748249088 | 3174149600 | -1574099488 |
| packing_compute_cycles | 889085952 | 804711424 | -84374528 |
| merge96_compute_cycles | 37179072 | 31850496 | -5328576 |
| final96_RNE_compute_cycles | 2329152 | 552960 | -1776192 |
| DMA_narrow_service_cycles | 1427325504 | 1294172736 | -133152768 |
| raw_A_DDR_logical_bytes | 412303360 | 57229312 | -355074048 |
| raw_B_DDR_logical_bytes | 3387686912 | 3387686912 | +0 |
| output_DDR_logical_bytes | 6211072 | 6211072 | +0 |

### decode512 / w16

| Cost or bytes (two P summed) | Before | After | Delta |
|---|---|---|---|
| native_leaf_cycles | 1583221760 | 1825179936 | +241958176 |
| command_control_cycles | 109179328 | 344328768 | +235149440 |
| LOAD_wall_cycles | 504153088 | 377591296 | -126561792 |
| local_narrow_cycles | 7062521856 | 5488422368 | -1574099488 |
| packing_compute_cycles | 889085952 | 804711424 | -84374528 |
| merge96_compute_cycles | 37179072 | 31850496 | -5328576 |
| final96_RNE_compute_cycles | 2329152 | 552960 | -1776192 |
| DMA_narrow_service_cycles | 2584461888 | 2451309120 | -133152768 |
| raw_A_DDR_logical_bytes | 412303360 | 57229312 | -355074048 |
| raw_B_DDR_logical_bytes | 6473383936 | 6473383936 | +0 |
| output_DDR_logical_bytes | 6211072 | 6211072 | +0 |

### decode2048 / w8

| Cost or bytes (two P summed) | Before | After | Delta |
|---|---|---|---|
| native_leaf_cycles | 1089612800 | 1331570976 | +241958176 |
| command_control_cycles | 268874176 | 504023616 | +235149440 |
| LOAD_wall_cycles | 726887424 | 537044736 | -189842688 |
| local_narrow_cycles | 6669895680 | 5095796192 | -1574099488 |
| packing_compute_cycles | 952786944 | 868412416 | -84374528 |
| merge96_compute_cycles | 132730560 | 127401984 | -5328576 |
| final96_RNE_compute_cycles | 3656256 | 1880064 | -1776192 |
| DMA_narrow_service_cycles | 1771045440 | 1637892672 | -133152768 |
| raw_A_DDR_logical_bytes | 419381248 | 64307200 | -355074048 |
| raw_B_DDR_logical_bytes | 4293656576 | 4293656576 | +0 |
| output_DDR_logical_bytes | 9750016 | 9750016 | +0 |

### prefill2 / w8

| Cost or bytes (two P summed) | Before | After | Delta |
|---|---|---|---|
| native_leaf_cycles | 1186510336 | 1186510336 | +0 |
| command_control_cycles | 116047232 | 116047232 | +0 |
| LOAD_wall_cycles | 798973440 | 798973440 | +0 |
| local_narrow_cycles | 8244596736 | 8244596736 | +0 |
| packing_compute_cycles | 1735907328 | 1735907328 | +0 |
| merge96_compute_cycles | 13145472 | 13145472 | +0 |
| final96_RNE_compute_cycles | 3787392 | 3787392 | +0 |
| DMA_narrow_service_cycles | 2626188672 | 2626188672 | +0 |
| raw_A_DDR_logical_bytes | 819316736 | 819316736 | +0 |
| raw_B_DDR_logical_bytes | 6173753344 | 6173753344 | +0 |
| output_DDR_logical_bytes | 10072064 | 10072064 | +0 |

## Separate historical replay

Separate historical S32/S96, ideal1R1W conditional model. No cross-model speedup is computed.

| Workload | Profile | Historical conditional token/s | Seconds |
|---|---|---|---|
| decode512 | queued_pipe_w8 | 3.496168883 | 0.286027373 |
| decode512 | queued_pipe_w16 | 2.116658600 | 0.472442745 |
| decode2048 | queued_pipe_w8 | 2.552804359 | 0.391726063 |
| prefill2 | queued_pipe_w8 | 3.696697379 | 0.541023458 |

## Boundaries

- Serial same-P staging/packing/LOAD/M/output program; not a controller with fully overlapped DDR and compute.
- Consumer priority and independent-bank concurrency have zero cycle benefit in this no-contention program.
- Per P: existing16KiB S and512B native result RF; extra2712B conditional adapter registers(2560 conversion+128 DMA+24 merge), not implemented.
- Context control adds325bits; no new S capacity or native result slots.
- Raw A full residency is common to both routes when capacity permits; no prefix policy in this new program.
- Per-bank count distribution is local-offset bookkeeping; only total physical work is contractual, no compiled S allocator.
- The unchanged U engine remains the frozen S32 candidate; weights/scales/native whole-graph compiler and quality evidence remain absent.

Actual source commit: `b5ff1f708b1b1809bb78d5849d1f025dc5f3b6d1`; full result SHA256: `afa8c326958295957c912f6f0a7836bb98ea235670cd8192cdbcdd64583f480f`.
