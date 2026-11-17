# Active continuation — 2026-11-17 CST

Issue289/PR290 remain in progress. No complete parent/block release exists.

- G hold03 and S full-reroute v3 leaf releases are frozen under remote `release-20261117/leaf/{G,S}`, 10 files each verified by package_leaf.py. Parent compatibility is separate.
- S full reroute introduced M9/M10 signals intersecting the old F power network. F h20-v4 has extracted setup/hold/electrical counts all zero, but PG fails. Reapplying original PG via-stack filter removes 18 VDD/8 VSS stacks; two actual VSS M10 stripe shorts remain. No PG/BPin clipping is authorized by our current fixed-interface contract; do not conceal them.
- Better branch: `candidate-S-{minimal,hold03,hold08}-localv4` modifies only nets affected by placement/resize. Minimal preserves all 1196 original upper-layer signal route records. Minimal/hold03 formal and independent STA/electrical/PG/antenna checks pass; full physical qualification-v2 running as extra steps in job119586. Pending standalone119618 was cancelled before start to reuse available slots.
- endpoint_audit agent now owns F completion using localv4. It may use existing119586 exclusive8CPU steps (total<=6 main tasks) and must create new script versions when replacing previous hardcoded S-hold08-v3 input. gs_upgrade agent hit usage limit; root had taken over its work.
- U-v6-ctsdelay-x8-seed0 incorporates the complete 50fF IO contract before CTS and macro insertion latency; completed global routing and is in detailed routing. This is a multi-change physical strategy, not proof that one CTS flag alone fixed hold. Real CTS hold cells are13600 CLKBUF_X1+27 CLKBUF_X3; earlier BUF_X1/2/4 exclusions did not affect those cells. Old-v5 hold candidates remain comparative and unaccepted.
- C-v9 newG candidates and C-v10 preCTS-contract/newG strategy remain unaccepted. C worst data path is a_words[0]→memory_service.actor2.loader.pd[1][117], long carry/mux logic, initial slack−3.008ns; CTS resizing still−2.119ns/443 endpoints. cu_upgrade is investigating cycle-preserving equivalent combinational optimization. Never invent multicycle/false-path or lower frequency to label this passed.
- Asynchronous reset recovery/removal is independently reported; no blanket exceptions added.

Active allocations:119542 node18 (comparisons, new C/U CTS strategies);119595 node14 (C-v9/U-v5 variants);119586 node19 (C comparison and F/S stages). Added external srun steps share allocations; verify allocation life before using them because original batch completion may terminate extra steps. Inspect actual srun command before cancelling any step; never cancel unrelated tasks.

Latest pushed commit before these notes:acad8c580. Further scripts and evidence remain in working tree. Continue tests, update evidence, commit/push PR290, and keep Issue in_progress until all engineering acceptance gates are evidenced. Do not self-merge or claim top-level A/B RC timing closure.
