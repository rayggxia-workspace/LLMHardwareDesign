# Issue85 single runtime core

One mfront85 executes either physical format selected and latched at cmd_accept. One shared mul84, one exact sfu84, one store82 16KiB 1RW. No duplicate M or command FIFO. Two existing 64bit multiplier response slots remain. cmd is valid, must be held until cmd_ready; cmd_accept is actual handshake. cfg has priority; pending cfg response is not cmd-ready even if compute busy=0.

soft abort synchronously clears pipeline/control/response slots and preserves SRAM contents. It advances a monotonically increasing32bit epoch. Every external request carries ext_epoch, every response must echo it; mismatched responses drain/count without entering the core. New command also advances epoch. Counter wrap is forbidden: cmd_ready stays low at0xffffffff until coordinated hard reset with fabric. Global reset requires the fabric to discard all old transactions; only soft abort tolerates tagged stale responses. There is one in-flight external core transaction, no unbounded buffer. Caller must use abort pulses and reload gamma after an abort that may have modified data.

No claim of independent clock domains, arbitrary-order matching or external-fabric fairness. Store is still control-reset/read-modify within one clock. Counter/epoch/mux overhead remains in logic mapping.
