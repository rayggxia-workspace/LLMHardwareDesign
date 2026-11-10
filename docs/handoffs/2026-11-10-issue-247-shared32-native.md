# Issue247 shared32 native RTL implementation

Owner/account: Melodydt. Issue247 / PR243 / task/242-r-load-bounds; base source a8e793e4c6f97e9dca5b0cc203797dcd3b0e0e78. User authorized both capabilities and selected shared32KiB. Status in_progress; no simulation submitted yet, no new token/s claim.

Backup task/247-before-shared32-rtl was read back at the exact source base. Formal staging is work/Melodydt/242/r-load-bounds/repo (non-Git snapshot). Parallel source-only Git worktrees live in work/Melodydt/247/shared32-rtl: integration (root), pool (shared_s_rtl), rw (shared_s_schedule), tests (shared_s_budget). Their baseline commit160a3de is a local subset identity, not a remote source commit. No concurrent writes to the same worktree. Prior run24/run25 report/evidence upload remains blocked and is not included in this source delivery.

First implementation: eight real4KiB macros form shared32KiB, a single global64B read service with finite4x512bit FIFO perP and native128bit A delivery. Compact tile-major S8/S16 objects, BEGIN/fill-ACK/SEAL/RELEASE, epoch/range checks, no free broadcast. P receives shared A directly, keeps B loading local and joins both completions. Defaults on existing P interfaces remain disabled; new twoP wrapper explicitly selects capabilities.

P local true1R1W uses two physical copies per lane and a1024bit live-location table. Logical16KiB, physical32KiB perP; same-address read-before-write, finite response credits,64B wide masked write port, protected LOAD leases. Warm reset retains live locations; cold reset invalidates contents and requires refill. TwoP+U+pool physical112KiB/28macros vs prior48KiB/12. Macro-area increment proxy1.4793928004mm2; logic/interconnect and physical timing not qualified.

Validation pending: unit real-macro three-seed tests, held responses, same-address/mask cases, reset/reload,256-cycle64B read+write service; integrated twoP arithmetic and four feature combinations; old default regression; Yosys area. EDA only in Slurm under the authorized personal server directory. Proposed run26 units+area, followed by integrated tests; actual job/commit/path receipts will be appended after submission. Current tests are source only, not passed claims.

Old S32/S96 four-scenario metrics remain conditional and distinct from native S8/S16/S40/S64. Prior4.x is not this RTL's measured token/s. New measured bandwidth/latency and control costs must be included before any model reuse claim.

Management check in the full formal snapshot passed; source-only worktrees intentionally lack template management files. PR open/unmerged; registration management-hub PR5 pending; board unverified/sync pending (missing board config/tool), reviewer/admin pending. No automatic post-chat monitoring configured.

Resume: inspect latest PR head and this handoff; verify frozen unit source SHA; package only enumerated sources using a real uploaded commit; submit Slurm job, immediately report job/node/log/output tracking. Do not overwrite prior pending research records.
