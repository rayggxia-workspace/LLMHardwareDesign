# Issue88 research-library electrical repair

This experiment starts from the exact four Issue84 mapped variants and Issue86 store82 memory cut. Read PROTOCOL.md for the fixed three-pass, 80000um2, no-wire research recipe and retained failed pilots.

- repair.py: explicit existing-library tie lowering, fanout/electrical repair, bounded hold repair, final electrical repair.
- run.py: rebuild the unchanged behavioral storage wrapper around the repaired gate logic, execute complete actual integer consumers, and run independent OpenSTA.
- timing.py: distinct register-to-register and all IO/cut setup/hold endpoint coverage at1/10fF.
- structure.py: independently parse original Liberty functions, fold buffer/inverter/tie graphs, compare every original cell pin and port bit, calculate exact area and input loading.
- receive.py: independently reparse original86 Verilog, check original/corrected graph, Liberty/LEF/Yosys area, numeric reference, all observables, typed protocol, provenance and actual mutation negatives.
- collect.py: package immutable source, raw records, failures and receipts; large artifacts remain on authorized server storage.

All real numerical, gate, EDA, and acceptance work runs on the server through Slurm. Source edits and source/archive-byte reception run on the local PC. Main chat handles push/PR; no self-merge. The original Issue84 variants do not include subsequent Issue85/92 epoch/runtime-control logic.

Reproduce using each immutable phaseN/binding.json and recorded command manifests in the delivery index; each input file has SHA-256. See docs/experiments/issue-88-electrical-repair.md for accepted evidence and limitations.
