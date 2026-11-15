# Stage resource scheduling and diverse search

The search construction order requires every needed producer range to have been
chosen before its consumer. Choosing A's mapping does not wait for all A ranges
to execute. Independent C can be chosen before or after B and still overlap.

The internal range-ready set denotes constructible ranges, not the user's
independent operator-level Ready frontier. Source operators retain partial
progress; software planning completion must not be read as hardware retirement.

Actual CALLs remain atomic under the existing single-command LC contract.
Different owners are released after their respective last CALLs, rather than
after the whole candidate. Shared SRAM is protected by the owner's dependency;
a shared DDR workspace remains leased through the complete candidate.

The emitted dependency graph is checked against the searched resource schedule.
Mother encoding issues ready independent targets and uses individual predicted-
first WAITs, instead of joining unrelated live commands into one WAIT barrier.
These are existing target-mask WAIT instructions. Prediction uses structural
work units, not calibrated physical time. No concurrency inside a busy LC CALL
or WAIT-any hardware support is assumed.

The bounded beam reserves opportunities for early estimated completion, low DDR
traffic and low dirty-buffer pressure. Only exactly equivalent stored states are
deduplicated. There is no dominance claim across incompatible mappings or data
placements, and no global optimality claim.

RTL changes are not part of this increment. Direct inter-SRAM transfers, SRAM-
source M execution and cross-command K continuation remain separate capability
gaps. No implicit U/P path, extra accumulator bank or physical block boundary
is introduced.

Validation: 12 independent scheduling/control/construction tests passed in job
115275. Full graph stage/diversity search is job 115276; full instruction-package
execution is still pending. The prior dirty frontier remains a separate baseline.

Full-graph run 115257 exposed Python decimal integer serialization limits in state deduplication. Structural tuple keys replace JSON keys; the regression covers 31,034-bit task masks and 100,000-bit backing masks. No global interpreter limit was disabled.
