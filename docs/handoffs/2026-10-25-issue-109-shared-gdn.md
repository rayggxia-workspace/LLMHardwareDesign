# Issue109 four-profile shared-bank handoff

Repository: https://github.com/rayggxia-workspace/LLMHardwareDesign
Issue: https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/109
Owner: Liangruizhi (182389313;2663955430@qq.com)
Branch/worktree: task/109-shared-gdn / D:/Projects/LLMHardwareDesign-shared-gdn
Base: PR108@7a9fecec1bb82af2c8af03dc89a2f42c0fdfba6c + PR107@03ab900651aa80a382316f6b8673cab4599540c8, merge d5e7cd1.
Scientific source: actual RTL/normal driver4b69d43; final recovery44cmd fe14c02; final receiver phase6; inventory/ports phase7; bounded gate/analysis/archive phase8@33f7a46. Final documentation commit is separate from these frozen source bindings.
Server: /public/home/yuzelu/RuizhiLiang/issue109-shared-gdn-20261025
Temporary PC files: D:/Projects/Codex/shared-gdn-20261025-01
PR: not published by this worker; root publishes and reads back. Issue in_progress, not done.

## Actual evidence

M/V, complete GQA A, Falcon singlehead R and Qwen3.5 twohead GDN now use one actual16KiB128bit1RW,8S8 bank,S32 service,SFU and external bridge. Both13cmd mixed and44cmd recovery runs are independently accepted; actual GDN stages/full32768state/256Y per snapshot, full M/A/Falcon math and metadata are checked. GDN3native continuous steps span other leases plus one actual legacy rescale checkpoint. It is not a complete same-model dataflow graph or all prior104 native32/portable12 repeated.

GDN candidate2048B is exported through the real shared external link with128 reads. Candidate accept initiates irrevocable commit; root ACK before published mirror/DONE. Provisional environment sink and2response FIFO320bit+control are external costs. Input/output representation, context/position/version and numeric_epoch versus D generation remain explicit. The full report states exact arithmetic/width/metadata/port costs.

Logic-only mapping163901.220um2, unique memory131072bit,109574cells; no macro/STA/PVT/CTS/RC or full product qualification. Eight numerical file-rehash negatives and three actual inventory rehash negatives rejected. Original104 extraction static audit is not formal equivalence.

## Final acceptance and root publication

All43own jobs are terminal:39COMPLETED,2first2400s gateFAILED,2dependent readerCANCELLED. Sameactualmap/binary/input once6000s replay completed quiet41:43 andheld50:46. Each finalreceiver accepted8complete commands,2GDN commits/1true range-wave,50560stagepairs/262144statecodes/2048Ycodes. analysis01 verifies exact allraw rows/snapshots/stages/protocol bytes against matchingRTL. No RTL-only Q injection or full44cmd recovery is claimed as gatecoverage.

Server fullarchive: delivery01/full-results.zip,104917869B/673members,SHA9de3fc27bf2fd89fbcb8d3d1a753b26910b4a73214ee8d0f42ad0f1334a19994. Selected356685B/229members,SHA24080128111fac643d7e10186545eb849d103829e76c35e8a065399ad972fd13. Serverbothbytes,PCselected and8phase233originalGit bytes PASS. Formal index/receipts: project/experiments/shared_gdn/results/issue-109. Original10441paths/10652paths have identicalGitblob/tree, see work109/inherited-bytes.json. Source-extraction staticaudit is separately scoped.

Root publishes using work/Liangruizhi/109/pr-body.md after receiving cleanfinalHEAD. Four suggested readbacks: docs/experiments/issue-109-shared-gdn.md and project/experiments/shared_gdn/results/issue-109/{index.json,cost.json,gate-receipt.json}. Read latestIssue/PR before publishing; no jobs remain to restart. UpdateIssue toactualin_review afterupload, read backGitbytes and boardwherepermitted; no selfmerge/done. Final localcheck and publicationdiff receipts remain work109.

Circuitcandidatev2 and itsdecision record fix numerical/transaction ownership, preserve true scratch/externalstate lifetimes and provisional sink costs. They explicitly do not inherit97/PR111physical or freezeM+A/Rmacros, SRAMmacro orM9–M10topology. Minimum next gates are realtransactionconsumer buffer,macro/drive/PG/PVT,newtopphysical and55/63manufacturing interfaces.

## Collaboration limits and next research

Parent/root owns final upload/PR, Issue and board synchronization. RegistryPR5 pending; Projects board configuration and read:project remain unverified/syncpending, administrator/reviewer待指定. No branch push or selfmerge by this worker. Report PR upload, review, merge and acceptance separately.

All actual arrays/oracles/RTL/map/gate run only on the authorized server. PC performs source, AST, project structure and archive byte checks. No new model download, license action, Phi unseal, install or other-machine task. Read original106/104 input dirs only. Unrelated member55/63 physical/adapter tasks and Issue110 width optimization are not modified.

Next substantive gaps: same-profile dataflow consumers and provisional sink implementation; generalized M/V and online/append attention; controller-scale/ports and physical memory/timing. Candidate logical Block boundaries are supported, final physical manufacturing boundaries are not signed off by logic area or gate replay.
