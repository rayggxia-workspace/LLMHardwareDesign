# Optional four-lane S32 U

E_S32=1 selects the S32 compact core; its signed seven-bit shift replaces the
five-bit S16 shift only for that static U instance. E_S32=0 preserves the legacy
ABI and default queue depth zero. This is not a dynamic mixed-S16/S32 dispatcher.

Opcodes 0 add, 1 subtract, 2 product, 3 multiply-add, 4 max, 5 min, 6 select
(C nonzero selects A), 7 left shift, 8 arithmetic right shift, 9 pair RoPE,
10 rescale and 11 abs return four packed S32 values. 12..15 are errors; there
is no implicit S16/S8 output packing. For 2/3/9/10, signed shift -64..63 means
left-shift when negative and RNE right-shift when positive. Saturation occurs
once at the output boundary. 7/8 reject negative shift. Add/sub/min/max/select/
abs ignore shift. No real model activation/quantization quality is qualified.

The trace gate accepts only exact-arity pure S32 operations with equally sized
inputs, no partial four-value tail, legal shifts and supported semantics. Multi-
input nodes, mixed widths and broadcasting remain excluded. Keep conditional
model costs for excluded nodes and report coverage; never scale all E work by
a microbenchmark gain. Full U tests use the actual SRAM/arbiter and queue 0/2/4.

Run the supplied job.sh on Slurm (4 cores) in a new locked-input run directory.
The runner requires default compatibility, integer-oracle results, ACK/traffic,
hazards/backpressure/reset and native NExp regression before matched area mapping.
The freeze references e22e60c6868795fb0f2e708c7e21358ce19a8b03.
