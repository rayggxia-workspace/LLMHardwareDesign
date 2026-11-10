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
