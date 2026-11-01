# Conditional numerical diagnosis, r14

This is a one-position diagnostic, not a complete-generation acceptance run.
The independent FP64 dense-layer oracle compares original and exported weights,
each with the reference input and the actual SystemC input. Falcon traces show
actual B/C/dt ranges before the R boundary.

`diagnostic-audit.json` binds the source archive, executable and raw output files.
Small stage traces and JSON are preserved byte for byte. Whole-model hidden and
logit binaries stay in the task server directories listed by the audit. The source
was an uncommitted archive based on 8a31f43, not an execution of that commit alone.
See `docs/SYSTEMC_NUMERICAL_REPAIR.md` for interpretation and acceptance gates.
