# Issue109 evidence and delivery

[Issue109](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/109), owner Liangruizhi. Worktree `D:/Projects/LLMHardwareDesign-shared-gdn`, branch `task/109-shared-gdn`; root conversation alone publishes PR and task status. Base PR108@7a9fece plus PR107@03ab900 (merge d5e7cd1).

Formal RTL is `project/rtl/shared_gdn`; reproducible tools and protocol are `project/experiments/shared_gdn`. Report is `docs/experiments/issue-109-shared-gdn.md`. Full numerical arrays and raw actual mapping remain in the authorized server root `/public/home/yuzelu/RuizhiLiang/issue109-shared-gdn-20261025`.

- `source-extraction-audit.json`: static, byte-based audit of original104 versus extracted109 state/math code after explicitly enumerated address/generation changes. This is not formal equivalence.
- `orchestration-events.json`: preserved SCP retry, old43cmd receiver dependency correction, and first2400s gate timeouts. Original logs remain in server local-audit/full archive.
- `verify_delivery.py`: archive/member/nested-artifact SHA/size reception only.
- `verify_sources.py`: original Git blob/source.zip/member exact bytes reception; PC does no numerical or RTL work.
- `execution.json`: actual argv/source phases and all43terminal Slurm states:39COMPLETED,2failed firstgates,2canceled dependent readers. Pre-seal snapshot stays unchanged in the archive; its running/pending observations were historical.

Final evidence: two13cmd mixed and two44cmd recovery runs,8 actual-file-rehash semantic negatives and3 inventory forgeries. Gate002/gate102 only bounded6000s replay passed8complete commands each with realrescale and exact raw/RTL bytes. Full104917869B/server and selected356685B/229members plus8phase233original Git bytes passed independent reception. All jobs terminal, no restart needed. `inherited-bytes.json` preserves104的41项/106的52项original paths; pr-body and four-key-readback plan are for root publication.

Registry management PR5 pending. Projects configuration/read:project unavailable, board state unverified and sync pending; root handles explicit upload/readback. No selfmerge or done. Old physical results do not transfer to shared109.
