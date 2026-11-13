# Issue250 child evidence update

Refs #250; parent owns PR251/integration/online status. This is not final system acceptance.

- M RF-only ready-independent candidate `deba22aa3`: run38/job102256,18 strict real-product aperture runs passed. INPUT11, CONTINUE16, FINAL18 core-relative cycles; actual serialguard next head EXEC II21. M guard uses host S provider RTT2 (stalled3..9), not SRAM-macro qualification. M36/37 preparation candidates each18passed but charge one preparation cycle and II22; no numeric/traffic savings.
- M maps39/40 are source-bound, no300MHz claim. Raw maps stay remote with SHA/bytes and complete index; no large mapping archive tracked. Physical10/11 still in progress under originalLib/300MHz/fullrules, side1390. Early GPL WNS-2.14/-1.91ns respectively, so neither is presently a qualified M leaf. Early reports preserved. Previous physical06 failed real POWER routing and remains indexed; standard hilomap fix is separately tracked in newer source.
- DMA07/job102266:4fixed-lane skid source be353,36strict ownership/credit/fault/reset-startup tests passed. This does not imply nominal bandwidth reached.
- DMA08/job102272:original three-M randomOOO pressure revealed about87.2% nominal service; DMA09 attempted egress-pressure scheduling did not help and was removed from current RTL. Raw failures preserved.
- DMA10/job102286:8sharedskids first RTL runs passed with100% nominal trimmed rate, but extra PERF stdout violated old runner framing. Test-only output fix produced DMA11/job102288 full36PASS, then independent source/SHA/conservation/strictrolling3/throughput audit PASS.
- DMA12/job102289:6sharedskids full36PASS and independent audit PASS.384B payload total, +128B versus old256B; source metadata still has no data storage. This is smallest passing tested return capacity; DMA13/job102291 shared4skids failed original97% pressure gate, not silently accepted.
- The nominal51.2GB/s is two channels, each <=2actual64B issues/cycle and <=4in every sliding3cycles. Data ACK releases credits only after real client ACK. Real scope/M/P integration, MC mapping/physical, full-model timing/energy and mid-flight reset are separate remaining gates. No unit throughput is a whole-model token/s claim.

Compact source/receipt packages and SHA audits live in dma01..13/run36..40. Large physical archives remain authorized remote and are recovered via each remote-index command. C: extraction paths are audit caches; their SHA-bound archives are retained.

Next: complete shared-fabric/P executor joint, add real mid-flight reset/purge isolation test, cut M leaf transport/control critical paths without relaxing original constraints, then repeat actual product vectors/map/P&R/final functional/formal/DRC/electrical/density gates. Any added latency/storage is reported to the native service model.


## 2026-11-11 continuation: actual finite M2 and zero-cycle physical cuts

- f08 original physical13/14 remain running; CTS13 is **not** qualified (WNS-1.22ns,
fmax219.86MHz); reply-only CTS12 WNS-1.54ns. These original reports are retained.
- Original exact placement probe102358/physical15 ties original ODB/SDC/Lib SHAs to
4.626ns scope-validation¡úcontrol_context-gate¡úRF read/prefix path, and3.734ns
mc_rsp_tag¡úfill validation¡úgood cancellation¡úraw/RF¡úa_ready path.
- Good matching CANCEL can accept with unrelated malformed FILL, whose fault remains
solely FILL-owned. No state or cycle added. Canonical f334 source102365/102367:
W18+native18+leaf18 PASS. Actual map726068.280um2/1330pins vs f08 726065.354;
physical16/job102375 at originalTT300MHz/side1390 is running.
- Minimal control address fix41a5: n_control_context=handle even when invalid, instead
of zero-gating through command validation. This changes no sampling or handshake.
102377 actual18 products PASS and independent audit125files PASS; all costs and work
unchanged. Source-bound map102379 is running. RF/scale source is unchanged.
- Independent C worktree task/250-dual-record-experiment: two finite M owners add
121.625B logical metadata, no payload SRAM; W4/RF16/one raw array remain unchanged.
Actual old+overlap18run passes, samectx head and cancelled second prefix preserved.
Leaf aperture no-stall II14; old single-active production guard remains II21.
M2 map735299.278um2/1330pins (+1.272% vs f08), physical17/job102376 running.
M2 source7542825c4 merges both zero-cycle cuts,10238018PASS + independent audit;
source-bound map102384 is running. Controller agent owns real guard2/executor2 joint;
its guard2 real4bankS unit10238118PASS does not alone establish the M2 system rate.
- New raw mapping/physical packages remain remote with SHA/byte indexes. No large
ODB/GDS/map archives added to Git. New RTL test receipts recover into own C caches.
Own physical02 expanded cache805995335B moved normally from D to
C:/Users/wine10/.codex/issue250-cache/m-physical02-original-receipts with all422file
bytes/SHA unchanged; C physical02-move-manifest.json retains exact relocation proof.
No deletion or denied-cleanup retry, no Git/history/other-owner changes.

Parent root continues to own PR251/Issue250 online status, shared docs and final
hardware selection. All new gains are hardware candidates, not DP20% algorithm gains.
Continue physical18/19 after newest exact maps, final original timing/electrical,
full originalGDS DRC/connectivity, actual netlist function/formal/density/delivery,
true guard2/COPY/MC/globalDMA/S integration and native full-model time/energy.
