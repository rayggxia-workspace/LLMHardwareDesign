# Nine-net candidate extraction consistency — qualified

`qualified-binding.json` joins the actual nine-net local repair qualification, source-preserving DEF normalization, actual wire-encoder readback, complete per-net extraction material comparison, uncached post-extraction PG checks and an independent complete GDS material identity check. Jobs 120170 and 120182 both completed successfully.

Only a redundant explicit zero extension at `net67393` was removed. The input net's complete layer/via material and every other net/body/non-NETS section are preserved. After actual OpenDB wire import and extraction, all 277,589 NETS declarations agree in material (277,587 signal/clock declarations and two PG declarations). Macro pins/positions and obstructions remain unchanged. Both uncached post-extraction PG rails pass. Independently streaming the normalized input DEF produces GDS with exactly identical per-cell/per-layer material and child instance references/transforms to the original nine-net combined GDS.

Preferred next ECO seed, remote:
`audit/C-v28-nine-net-normalization-v1/reextract-encoder/before.odb`

SHA: `666d30659827b7764eb3e89e8f0e4846e366142b9f3ca0bfffae34f32a4ac371`

Qualified same-physical-candidate parasitics, remote:
`audit/C-v28-nine-net-normalization-v1/reextract-encoder/isolated.spef`

SHA: `303a113045f40318159e235f7566cb7c31e76837f1dab465a8dd01aa9e2524ab`

This is extraction/physical consistency qualification, not backend acceptance. The remaining antenna repair, timing/electrical closure, same-final-GDS complete unchanged foundry deck and final functional/model checks are still required. Any later candidate must undergo its own dynamic extraction/material check; neither this SPEF nor the normalization target list can be reused across changed routes.
