# Command-internal pipeline review

Scope: replace avoidable supply/compute/return serialization in the production
macro-native path. Parent controls are not physical block boundaries. No U/P
connection is implied and no additional functional macro is introduced.

| Path | Replacement | Contract that still matters |
|---|---|---|
| Activation DDR to SRAM | two return slots, ordered writes with two ACKs outstanding | data is visible only after real commit |
| Shared service reads | four tagged requests per owner and four-slot control routing | shared DDR channel limits still apply |
| Gather | index lookup then common activation pipeline | payload address genuinely depends on the index |
| K128 normalization | observe magnitude while loading; one conversion pass, two response/pack slots | scale needs all 128 source values |
| Projection A SRAM reads | two reads in flight into the existing A windows | each returned word must match its generation/slot |
| Projection weights | TLM mirrors existing 32-credit/four-record M path | complete records required before corresponding compute |
| Next K128 source | fill existing S32 window while current A16 is consumed | reuse A16 only after its real consumer releases it |
| Attention dot | separate A/B cache lines | E accumulation/response dependencies remain |
| SRAM to DDR | two 64-byte gather slots, two SRAM reads, one DDR write | completion follows the final physical write ACK |

Review found additional correctness defects in error/cancel handling:
a held valid request must survive backpressure until accepted; an unknown return
tag must not release a real outstanding request. Legal-tag error completions and
unknown identities need separate handling. Corresponding regression receipts
must be regenerated after fixes; earlier passing functional tests alone do not
admit the new hardware.

The production entry has no selectable serial replacement. Generators must
reproduce the same pipeline structure. Historical immutable receipts are not
current admission evidence.

Final acceptance uses history 512 and 513, two causally chained decode steps,
token 840 and initially frozen-zero history. Both complete instruction packages
and all exported values require independent integer-reference comparison.
There is currently no matching old-pipeline full history512/two-step result;
history2 timing improvements cannot establish this change's end-to-end speedup.
Capacity/overlap unit evidence and full-request performance are separate facts.
