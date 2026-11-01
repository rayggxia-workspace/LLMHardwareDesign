# Real text-model execution, r15

All decoder layers and the full vocabulary run through the SystemC adapter.
`numerical-gates.json` applies the predeclared engineering thresholds and binds
each raw `validation.json` by SHA-256. It retains every numerical failure.
Passing Slurm/CTest and matching generated tokens do not replace these gates.

`remote-audit.json` independently hashes input weights, reference data, source
archive, executable and outputs in an allocated server job. Collected small raw
receipts and stage traces are byte-preserved; large binaries stay on the task
server. The source manifest records the actual uncommitted execution archive and
its parent commit. No hardware performance or general model-quality claim.
