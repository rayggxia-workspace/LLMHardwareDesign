# Exact mapped gate replay and declared logic timing

Issue86. Read PROTOCOL.md and docs/experiments/issue-86-gate-sta.md before reuse. Entry points run.py prepare/build/sim/sta, receive.py independent complete integer math and scope verification, collect.py immutable evidence delivery. Actual commands and frozen phases are in work/Liangruizhi/86/execution.json; exact data dependencies and archives in results/issue-86/index.json.

Run on the authorized CPU server only, from a frozen source directory containing binding.json. Existing Yosys, Verilator and OpenSTA are used read-only. `python -B project/experiments/gate_sta/receive.py --root <issue86-server-root> --prior <issue84-server-root> --out <new-directory>` checks all eight original gate conditions and the explicitly cut timing evidence. Output directories must not exist. The final accepted run is receive03 from phase8; intermediate failures remain evidence.

PC checks are byte-only: `python -B project/experiments/closure/verify_delivery.py --index <index.json> --archive <selected.zip> --out <new-receipt.json>` and `python -B work/Liangruizhi/82/verify_sources.py --repository <repo> --index <index.json> --selected <selected.zip> --expected-phases 8 --out <new-source-receipt.json>`.

All gates pass selected zero-delay functional replay. Slew/cap violations remain in every timing variant. No target Fmax, SRAM macro, physical closure or Issue85 runtime design qualification is implied.
