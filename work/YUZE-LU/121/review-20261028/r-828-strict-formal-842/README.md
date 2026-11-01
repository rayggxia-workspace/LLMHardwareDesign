# R 828 strict final-netlist equivalence capture

The independent strict LEC passed with explicit UNSAT / IDENTICAL. All 292,950 inputs and 292,936 outputs match, with zero unmatched boundaries. Every strict LEC check passes.

This capture binds the proof to the same final-source receipt as captures 838 and 840 (SHA-256 `759cae257ff6731b8424eac6270a7bf255b6f0dc980ba0ff3a7bb508037b916b`) and verifies the exact function receipt dependency. The three initialization regressions remain separately required and passed; LEC does not establish reset or initial-state behavior by itself.

[index.json](index.json) records 47 actual raw files and 17 actual remote large-file hashes and sizes. All 365 archived source Git blobs, receipt inputs and stable outputs were checked before writing this capture. Only the explicitly recorded queue child log append is permitted after its receipt. [collect842.py](collect842.py) preserves the collector.

This is a partial capture of completed source, function and formal tasks while job 94421 continues running. Full unmodified GDS DRC, final delivery, actual complete geometry inspection and the 829 all-port finite interface experiments remain pending. Overall final acceptance remains false. No old R failure qualification is transferred and no full-system qualification is claimed.

[publication841-readback.json](publication841-readback.json) preserves the previously verified publication receipt for commit fc8c9997; it does not claim that this new capture is already published.
