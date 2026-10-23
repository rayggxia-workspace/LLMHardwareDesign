# Issue29 Yosys job89838: bounded read-only diagnosis

Observed remotely at **2026-10-23 01:50:48 UTC / 09:50:48 Asia/Shanghai**. This is an observation timestamp, not a claim about subsequent job state. Only the explicitly named own-job logs, source hash, version/hash receipts and `sacct -j 89838` were queried. No job was submitted, cancelled or changed; no process or other-user directory scan was performed.

## Established facts

- Own job89838, name `lrz-portsyn`, reported RUNNING, elapsed 00:15:23, AllocCPUS=1. MaxRSS was blank; this read does not establish current CPU utilization, memory use, progress rate or whether a resource limit will be hit.
- Both `/public/home/yuzelu/RuizhiLiang/issue29-port-rtl-20261022/formal01/synth-89838.log` and `synth-check/m0-d1.log` were 2,497 bytes with mtime 2026-10-23 09:45:35 +0800. A prior observation at 01:49:10 UTC had the same sizes/mtime. An unchanged log is not proof that the process is hung.
- Yosys version is `0.63`, git `70a11c6bf`, g++11.4.0. Retained binary hash is `a409abe03c090a72e15906082775f506ff6f5fa50106dec087900a7104c08a4c`.
- Remote RTL hash is `decaf90749dbbfca37d95af006b0b4066d5b3b76ebc5d434858af7e6cefa5890`, identical to the frozen formal source used for the independent local code inspection.
- The script first runs `read_verilog -sv -D SYNTHESIS` with module defaults PORT_MODE0 / RESP_DEPTH2. Its log explicitly reports `Successfully finished Verilog frontend`. It then overrides parameters in `hierarchy -check ... -chparam PORT_MODE 0 -chparam RESP_DEPTH 1` and enters a second AST-to-RTLIL derivation. The last retained stage is this parameter-specific derivation. No `proc`, `opt`, `memory_collect`, `check`, `stat` completion or output JSON is evidenced by this log.
- In both frontend passes, register-replacement warnings name only `rr`, `response_count`, `wr_ptr`, `rd_ptr`, `slot_ep`, `slot_valid`, `rr_next`, `credit`. These are small control arrays. No retained warning says `bank_mem` or `response_data` was replaced by registers. The default frontend's success demonstrates some elaboration acceptance, not a completed synthesis check for all nine configurations.

## Diagnosis and confidence

**Confirmed avoidable duplication:** this script fully lowers the default depth2 module, then re-lowers the parameterized depth1 module. This is parameter derivation performing frontend work again, not evidence of work in a technology-mapping pass. `read_verilog -defer` retains the AST and delays compilation until `hierarchy`, avoiding the initial default-parameter lowering. This is documented behavior, not a guarantee that the one remaining derivation will be fast. [Yosys0.63 frontend options](https://yosyshq.readthedocs.io/projects/yosys/en/v0.63/cmd/index_frontends.html#read-verilog-read-modules-from-verilog-file)

**Plausible cost inside each lowering, not yet isolated:** source lines156–169 unroll 2 banks × 2 grant slots × 64 byte lanes, yielding up to256 syntactic byte-write sites before optimization. The selected endpoint is dynamic, including dynamic source data slices and response FIFO indices. Yosys's AST simplifier unrolls loops, transforms array accesses and expands dynamic left-hand selections before RTLIL generation. Large generated expressions/process case structures are therefore a plausible frontend cost. This is an inference from this source and tool behavior, not a measured profile identifying the hot function. [Yosys0.63 AST frontend](https://yosyshq.readthedocs.io/projects/yosys/en/v0.63/yosys_internals/flow/verilog_frontend.html)

**Unproven explanation:** 1,048,576 bank-storage bits being flattened to individual FFs. The observed warnings do not show that happening, and the script has not reached its memory passes in the retained log. Absence of such a warning also does not prove a particular final memory representation. `memory_collect` later combines memory ports; it does not map to a technology macro. The script does not call `memory_map`, `memory_libmap`, technology mapping or STA. Even successful completion would therefore be a generic IR structural check. [Yosys0.63 memory handling](https://yosyshq.readthedocs.io/projects/yosys/en/v0.63/using_yosys/synthesis/memory.html)

## Smallest next falsifiable check — proposed, NOT executed

Keep job89838 and its evidence intact. When the parent elects to run a separate diagnostic, use a new output directory with the same frozen source, same Yosys/container hashes, and only PORT_MODE0 / RESP_DEPTH1 initially. Change only the frontend loading strategy:

```text
read_verilog -sv -D SYNTHESIS -defer source/bank_port_fabric.sv;
hierarchy -check -top bank_port_fabric -chparam PORT_MODE 0 -chparam RESP_DEPTH 1;
stat;
write_rtlil diagnostic/m0-d1-elaborated.il
```

Capture process elapsed time and peak RSS plus the usual source/tool hashes. This should produce one parameter-specific AST lowering instead of two. The first explicit criterion is reaching `stat` and the RTLIL checkpoint. It tests duplicate-default elaboration overhead while leaving the target design unchanged; it does not by itself isolate byte-loop cost. Use RTLIL here because the design still contains processes; defer JSON until after `proc`.

If that checkpoint is produced, a second invocation can load it and run the existing downstream commands, avoiding another frontend pass:

```text
read_rtlil diagnostic/m0-d1-elaborated.il;
proc; opt; memory_collect; check -assert; stat;
write_json diagnostic/m0-d1-generic.json
```

Inspect retained memory geometry/read/write-port counts and process/cell counts before considering a nine-configuration sweep. Do not infer a 1RW/1R1W/2RW technology macro implementation from declared bank capacity or generic memory-cell counts.

If even the single deferred derivation is slow, a later separately versioned source prototype can factor endpoint selection into one explicit request bundle per bank/slot before byte-lane memory updates. It can test whether repeated dynamic endpoint expressions dominate frontend construction. That prototype would need its own hash and protocol equivalence/regression evidence; it must not silently replace the frozen RTL or its measured results. No such refactor or experiment was made in this diagnosis.

## Receipt

`synth-89838-readonly-snapshot.json` preserves the complete safe command argv, timestamp, stdout and return code. Only a key pathname occurs in argv; no key content or token was read or logged. `synth-diagnosis-hashes.json` hashes the snapshot and this note. Main worktree, GitHub and server files remain unchanged by this subtask.
