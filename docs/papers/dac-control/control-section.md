# Hierarchical Control and Instruction Set

## Two-level scheduling

Model dependencies determine which Blocks can execute together and when a consumer can start. Within a Block, the order and timing of memory accesses, sub-macro operations, and writes depend on the local service and its available resources. Driving all of those steps from the mother controller would tie the global program to each Block's internal sequence and expose local backpressure to the global scheduler.

The selected NoPool base candidate comprises nine Block instances across five types (three P, two U, one C, one F, and two J). The mother controller (MC) uses its own 16 KiB program SRAM and issues calls to the per-Block local controllers. A separate data plane provides product-bound inter-Block paths and access to off-chip DDR through a shared two-channel DMA. The Block outlines in Figure 1 denote control ownership over independently placed leaf macros and their adapters.

The P group illustrates the two scheduling levels. Each P is specified with one K16 × N8 matrix macro M, one G32 SiLU and gate-multiply macro, and one 16 KiB private SRAM S with four banks. The MC sends a scope call and associates it with a token. The P local controller (LC) fetches its kernel from separate program memory, accepts the scope descriptor, and invokes the range service. The service logic sequences operands and M commands, and tracks writes to S. The native RTL instantiates a 1 KiB LC program store and uses four 128-bit flits per call or terminal reply. For the tested P ranges, destination write acknowledgments precede successful completion and the LC releases the scope before replying. The figure identifies the G32 service binding as part of the per-P candidate. The programmed FFN fixture uses a shared G32 service and supplies outer-phase sequencing.

A single global call covers a range of local operations. Independent Blocks can advance at their own pace before the MC reaches a dependency barrier, and a Block's internal schedule can change while the MC program stays valid if the service parameters and completion contract are preserved.

![Nine-Block base candidate and expanded P control group](control-architecture.svg)

**Figure 1. NoPool base candidate and expanded P control group.** (a) The instance row shows all nine candidate Blocks. Calls and terminal replies travel on the control plane, while operands travel on product-bound paths. The instance labels are schematic ordinals. (b) Blue lines carry instructions, commands, requests, acknowledgments, and status. Orange lines carry descriptors, operands, and result data. Solid lines indicate interfaces supported by the cited P range RTL. Dashed lines indicate candidate bindings, including the per-P G32 control and data connections. An interface may carry both kinds of information. The paired arrows separate those roles logically. Nine-instance integration and physical qualification remain separate from the P range RTL results.

## Instruction set and topology mapping

The two levels use separate 64-bit instruction streams. Figure 2 groups the eight native MC v3 opcodes and the three LC instructions used by all five Block classes in the bounded native programs. Dispatch uses `G_CALL` to select a target and token and `L_EXEC` to invoke a registered local service. Synchronization uses `G_WAIT` for selected terminal tokens, `G_EVENT` to consume a bound READY event and capture its scalar, and `L_WAIT` for the matching local completion. Argument setup uses `G_MOVI` to load a register and `G_ADDI64` to advance a 64-bit register pair. Program flow uses `G_JNZ` to select one of two forward PCs, `G_LOOP` for a counted backward branch, `G_END` to finish the MC program, and `L_END` to return task status after local obligations are closed.

The execution descriptor determines what `L_EXEC` does. P selects load, matrix, and gate services in its leaf profile, or the bounded range service in the newer native P profile. U selects normalization or vector arithmetic, C selects state, activation, or vector arithmetic, and F selects activation or vector arithmetic. U, C, and F can also invoke receive reservation, send, and receive through native service descriptors. J selects join or lease release. The shared instruction names and opcode values provide a common program structure. Program images, execution descriptors, and transport bindings still follow the target's profile.

Figure 2(b) uses the ordinary FMA service of the E macro in U0. With two input routes, producer tasks A and B supply `a` and `b`. The MC waits on their tokens with mask `0x03` and the U LC invokes E with a two-source descriptor. E substitutes zero for the omitted addend and computes `a × b`. A second product mapping adds the route from producer C into a third private-S source slot. The MC dispatches C before the join and changes the wait mask to `0x07`. The U LC uses a three-source descriptor, so the same E macro computes `a × b + c`. The input values 2, 3, and 5 give 6 and 11 in the existing U native-entry regression.

The shown MC fragments require producer terminal status to cover destination writes to U0. A deployment with source-local completion must schedule and verify the transfers before issuing U0. The paths from the illustrative producer Blocks and the corresponding MC schedule describe a product mapping. The cited regression validates the U service with actual SRAM operands, including the difference in read count and output.

![Instruction classes and two U FMA input mappings](instruction-topologies.svg)

**Figure 2. Common LC instructions, Block-specific services, and topology-dependent computation.** (a) The shared LC instruction subset sequences the registered service for each Block class. (b) A third input route supplies the FMA addend. The MC adds C to the producer sequence and wait mask, and the U LC selects the three-source E descriptor. A, B, and C name producer tasks. Dashed data edges denote illustrative product bindings. The numeric results are from the standalone U native-entry test.

## Implementation example

In the programmed three-P feed-forward network (FFN), each call and each terminal reply crosses the MC–LC interface as four 128-bit flits. The MC validates the source, token, job, epoch, task sequence, generation, and topology before recording a terminal reply. It uses `G_MOVI` to initialize registers, issues three `G_CALL` instructions per iteration, and advances the descriptor pointer by 128 bytes with `G_ADDI64` after each call. `G_WAIT 0x7` waits for all three tokens before `G_LOOP` advances the bounded loop. The 272-byte MC image contains 17 static instructions and dispatches 192 calls over 64 iterations.

Each P LC runs the same three-instruction kernel from a 352-byte image. The LC obtains each 128-byte descriptor through two 64-byte transfers from the shared DMA. The programmed RTL experiment exercised Qwen2.5-3B FFN dimensions with deterministic synthetic integer weights. Both weight-provider variants passed all 36 cases, including checks of quantized intermediate tiles and outputs read back from the original SRAM bank models. With the program images and traffic held fixed, the early-execution provider reduced FFN cycles by 0.52–1.20% across the matched cases. This comparison measures a provider scheduling change within the same control interface. The fixture sequenced K-tile movement and the outer Gate/Up and Down phases.

## Native MC v3 and the common LC subset

The 64-bit MC word places the opcode at bits `[63:56]`, three operand bytes at `[55:48]`, `[47:40]`, and `[39:32]`, and the immediate at `[31:0]`. The table lists the eight decoded MC opcodes. The programmed FFN uses `G_MOVI`, `G_CALL`, `G_ADDI64`, `G_WAIT`, `G_LOOP`, and `G_END`.

| MC instruction | Opcode | Operands used |
| --- | --- | --- |
| `G_EVENT` | `0x12` | Selects a destination register and event binding. Consumes READY and captures its scalar. |
| `G_MOVI` | `0x13` | First operand selects the destination register. The immediate supplies its value. |
| `G_JNZ` | `0x15` | Selects one of two encoded forward PCs according to whether the tested register is nonzero. |
| `G_CALL` | `0x10` | First and second operands select target and token. The LC entry in the third operand is zero. |
| `G_ADDI64` | `0x16` | First operand selects the low register of an even-indexed register pair. The immediate is the unsigned increment. |
| `G_WAIT` | `0x11` | The immediate holds the token mask. |
| `G_LOOP` | `0x17` | First operand selects the loop counter. The immediate is the backward target PC. |
| `G_END` | `0x1F` | No operands. |

| LC instruction | Opcode | Shared action | Example word in the native P kernel |
| --- | --- | --- | --- |
| `L_EXEC` | `0x41` | Invoke the service selected by the execution record. | `0x4100000000000000` selects resource, token, and record 0. |
| `L_WAIT` | `0x44` | Wait for the selected local completion. | `0x4400000000000001` uses mask `0x1`. |
| `L_END` | `0x4F` | Return task terminal status after local obligations are closed. | `0x4F00000000000000` releases the native P scope before replying. |

