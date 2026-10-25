# Command-scoped cache and epoch-scoped cancellation

Issue85 uses one M core and one sharedS32 multiplier. A mode is latched at explicit cmd_accept; cfg/pending responses take priority, and callers use cmd_ready rather than compute busy. Runtime mux/control/epoch overhead is measured (+1.52715% logic-only area,+97 generic register bits versus84cached/shared) with unchanged core cycles, so retain a per-command bypass choice.

Soft abort invalidates the generation and retains SRAM. External responses carry32bit epochs; stale generations drain without entering a new consumer. Hard reset remains coordinated withfabric and epoch wrap is forbidden. The two-slot external recovery test queue has at least320bits payload/tag plus control outside core area; real tag wires/framing remain unqualified.

This is a bounded single-clock command/cancel prototype, not a signed-off physical Block boundary or complete accelerator. Keep existing M/V placement alternatives and qualify the full bus/memory circuit before freezing manufacturing boundaries.
