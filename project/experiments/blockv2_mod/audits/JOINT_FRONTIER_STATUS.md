# Joint native frontier integration — work in progress

The implementation lowers existing native commit units into a joint search over
ready ranges, actual service bindings, SRAM placement, dirty retention and
last-reader release. A retained intermediate has no valid DDR backing until an
explicit existing DWS command commits it. Scheduling a consumer can precede
completion of all ranges of its producer.

No throughput or completed integration claim is made by this implementation note.
Full graph search, package validation and exact-package TLM execution are required.

## Actual hardware restriction

The current MPR1 projection service reads its activation source from DDR.
A downstream full-K matrix projection therefore forces backing of its input.
The native path cannot reproduce the prototype's Gate/Up → G → partial-Down
pipeline merely by deleting stores.

The M arithmetic macro already contains context create/restore/step/snapshot-clear
commands in projection_context_s32. Existing stream integration is the gap:
p_scope128_decode rejects partial K for a stream scope; p_scope_range_service
rejects a partial native stream provider; p_native_weight_overlap_candidate
rejects record_restore / record_spill. These must be distinguished from an
absent arithmetic operation. Any continuation support must preserve the actual
per-K128 S32 scaling/rounding, context identity and completion semantics.

No extra accumulator bank, implicit U/P connection, new physical block boundary,
or host arithmetic implementation is introduced by this integration.

## Search semantics and evidence boundary

- Depth counts unfinished source-graph operators. Gate/Up/G/Down lowering stages
  belong to their original FFN operator; they do not consume extra source depth.
- The beam jointly varies ready-range order, implemented service binding and
  retain/commit choice. Actual DDR commands determine the traffic objective.
  Ready consumer locality breaks equal-traffic ties; it is not a throughput model.
- SRAM capacity comes from each selected macro's source profile. Fixed staging
  windows of an MPR command are protected; rewritten descriptors are admitted
  again before packaging, including an eviction emitted on another controller.
- Packing copies do not rename their source SRAM data. A copy to DDR scratch
  cannot silently destroy a still-live dirty SSA value.
- Last-reader release uses the unscheduled readers of each produced page.
  Physical reuse is additionally ordered after the actual prior controller
  completion, not merely after the search has visited a node.
- Prefill live-outs include all 72 KV roots needed by decode. Decode graph outputs
  include logits and 72 present-KV values. These must be committed.
- Full-K MPR, RMS reduction and unsupported relocation services remain atomic.
  Compound services materialize required dirty inputs and use their admitted
  canonical SRAM footprint. This is a conservative executable restriction.
- Candidate depth and beam limits do not prove global optimality. The CLI supports
  a sealed incumbent from the identical graph, hardware and allocation; a lower
  structural-cost incumbent can be retained without changing its instructions.

The earlier range8 experiment retains all DDR stores and is a separate baseline.
Its call reduction must not be reported as the benefit of this joint dirty search.

Packing workspace contents are also explicit state: each committed 512B scratch
page records the immutable SSA source page copied into it. A repeated identical
LOAD/STORE packing pair can be omitted only while that mapping remains valid.
A different source or opaque write invalidates the mapping. All actual accesses
to the same DDR workspace share a scheduling resource and completion dependency,
including accesses issued by different local controllers. This avoids repeatedly
repacking a segmented matrix input for every output range and prevents a scratch
overwrite from racing an earlier projection.
