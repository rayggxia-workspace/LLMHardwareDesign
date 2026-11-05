# Block-local S server verification

See [interface and scope](../../../docs/BLOCK_LOCAL_S.md) and [Issue177](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/177).

`local_s_pool.sv` instantiates nine real private S instances: P/P/P/U/U/C/F/J/J. `test_local_s.cpp` uses independent reference arrays and checks actual request/response handshakes, local fairness, cross-block isolation, retained memory/reset, and the real legacy feeder. Protocol peers are not full compute macros.

Run `run_server.py` only inside Slurm, with the existing server Verilator/Yosys tools and a fresh output directory. The runner requires a `source_binding.json` at the uploaded source root, containing the full Git commit, baseline commit, and exact SHA256 of the eight input files listed in `SOURCES`. Local CRLF working-tree bytes must not replace Git object bytes during transport.

`job.sh <new-authorized-task-root>` uses four CPUs. Hardware execution is not performed on the login node. For the debug partition, override partition/node/time according to its 30 minute limit. All caches, logs and outputs must remain in the newly created authorized task root.

Results: `results.json`, `inventory.json`, complete lint/structural/synthesis/build logs, nine run logs, and the source binding. Keep the full structural netlist/build products on authorized storage; commit lightweight logs and source/hash receipts. No physical qualification is implied by generic synthesis.
