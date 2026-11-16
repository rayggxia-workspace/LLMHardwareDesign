# Issue 250: native mother-control candidate

This is a new profile; the previously qualified two-resident controller is unchanged. ABI `0x02500002` has nine real resident task slots, sixteen tokens and nine event bindings. CALL/WAIT remain 64-bit instructions. Logical 64-byte task/return packets cross the external interface as four real 128-bit flits; malformed or old-generation returns cannot release an owner. The program runs against the original 16 KiB `control_pm` and four SRAM-bank behavior views.

`run-index.json` preserves all ten attempts, sources, actual Slurm CPU use and package SHA-256. The packages contain immutable source, strict Verilator build logs, result logs, PM images and the original bank source. Failed lint and testbench attempts are retained.

| Admission | Job | Result |
|---|---|---|
| Parallel internal packet controller | 102122 | 20 cases × six seeds × three initial states = 360 passed |
| Physical-width 128-bit packet transport | 102138 | Same 360 program cases passed |
| Independent beat/descriptor credit classes | 102128 | Two classes × 18 runs = 36 passed |
| Isolated framing and malformed packets | 102142 | 18 passed |

The tests include concurrent 3P+U, all nine targets, target 8/token 15, nine ready events, cancel/drain, timeout quarantine/recovery, held tasks/results, duplicate/late/wrong-source/job/generation/topology and old-profile rejection. Actual program counters and PM reads are logged. Finite peer delays are part of these fixtures, so total cycles are not standalone dispatch costs.

The DDR primitive separates descriptor and 64-byte beat classes, each with 32 credits **per channel**, plus target bounds. It keeps RESERVED/OFFERED/ISSUED lifetimes distinct. It does not implement the record-burst queue or a production DDR scheduler; a 1152-byte record must reserve a descriptor once and obtain beat credits incrementally. It cannot reserve eighteen beats atomically and call that equivalent to the calibrated queue.

The five existing LC physical groups expose PM ports; their fixtures supply external program memory. They do not establish nine physical LC program memories. The native range service needs a measured small kernel plus an explicitly costed mutable PM/ROM and scope parameter storage.

Slurm102178 expands the **candidate** capacity ID to `0x02590002` without enlarging its actual16KiB PM. The full-width instruction-beat counter fixes the former nine-bit fetch-count truncation. Exact layout is `total=128+16*ceil(instructions/2)+16*events<=16384`. With no events the maximum is2032 instructions; with nine16B event records it is2014. All24 cases ×18 runs=432 passed, including257 instructions, the exact two full-PM layouts, and2033-instruction physical overflow rejection. The maximum one-pass case actually fetches2032 instructions and takes12199 fixture runtime cycles. This establishes image/fetch bounds; the full36-layer compiled scope program and required outer-scope FSM must still be generated and measured. A three-instruction LC kernel alone does not implement the outer FFN loop.

These are candidate RTL/unit admissions, not MC+LC native-program integration, M numeric coverage, 300 MHz physical qualification, full-model token/s or energy results. See `project/rtl/mother_control_native/contract.json` for exact packet fields and boundaries. Root Issue 250 integration owns shared documentation, PR registration and physical closure.

The latest independent profile uses instruction-image v3/capacity `0x02590003`, with checked `G_ADDI64` and bounded backward `G_LOOP`. It keeps the same 16KiB PM and packet ABI v2. Job102190 passed34 cases×18=612; job102192 passed35×18=630 including the wholegraph control oracle. The compiler discovered the actual942-scope pattern (prefix1, body26 repeated36 times, suffix5) and produced131 static instructions/1184B. All1304 CALL target/reference pairs match the unrolled oracle. Each execution still performs3596 real PM fetches and the external descriptor table is166912B; no per-group CALL or free host descriptor update is assumed.

Job102200 adds physical128-bit packet and PM timing CSVs in18 runs. PM request-to-response is4 cycles; ordinary sequential instruction request spacing is6 cycles and CALL spacing10 including four flits. The942 waits include finite peer delays and total fixture time must not be interpreted as native-model latency or token/s. The non-P services use explicitly unqualified peers, the FFN/projection outer service remains a candidate, and real typed descriptor fetch/native LC integration remains separate. See `wholegraph-loop-102192.json` and `wholegraph-timing-102200.json`.
