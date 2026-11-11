# Hierarchical Control and Instruction Set

## Two-level scheduling

Model dependencies determine which Blocks can execute together and when a consumer can start. Within a Block, the order and timing of memory accesses, sub-macro operations, and writes depend on the local service and its available resources. Driving all of those steps from the mother controller would tie the global program to each Block's internal sequence and expose local backpressure to the global scheduler.

The selected NoPool base candidate comprises nine Block instances across five types (three P, two U, one C, one F, and two J). The mother controller (MC) uses its own 16 KiB program SRAM and issues calls to the per-Block local controllers. A separate data plane provides product-bound inter-Block paths and access to off-chip DDR through a shared two-channel DMA. The Block outlines in Figure 1 denote control ownership over independently placed leaf macros and their adapters.

The P group illustrates the two scheduling levels. Each P is specified with one K16 × N8 matrix macro M, one G32 SiLU and gate-multiply macro, and one 16 KiB private SRAM S with four banks. The MC sends a scope call and associates it with a token. The P local controller (LC) fetches its kernel from separate program memory, accepts the scope descriptor, and invokes the range service. The service logic sequences operands and M commands, and tracks writes to S. The native RTL instantiates a 1 KiB LC program store and uses four 128-bit flits per call or terminal reply. For the tested P ranges, destination write acknowledgments precede successful completion and the LC releases the scope before replying. The figure identifies the G32 service binding as part of the per-P candidate. The programmed FFN fixture uses a shared G32 service and supplies outer-phase sequencing.

A single global call covers a range of local operations. Independent Blocks can advance at their own pace before the MC reaches a dependency barrier, and a Block's internal schedule can change while the MC program stays valid if the service parameters and completion contract are preserved.

![Nine-Block base candidate and expanded P control group](control-architecture.svg)

**Figure 1. NoPool base candidate and expanded P control group.** (a) The candidate has nine Block instances and one MC. Calls and completion replies travel on the control plane, while operands travel on product-bound paths. The instance labels are schematic ordinals. (b) The P LC calls the scope service, whose adapters connect to M and private S. Dashed connections show the schematic product data paths and the candidate per-P G32 binding. Nine-instance integration and physical qualification remain separate from the P range RTL results.

## Instruction set and topology mapping

The two levels use separate 64-bit instruction streams. Figure 2 groups the eight native MC v3 opcodes and the three native P LC kernel opcodes by function. Dispatch uses `G_CALL` to select a target and token and `L_EXEC` to invoke a registered local service. Synchronization uses `G_WAIT` for selected terminal tokens, `G_EVENT` to consume a bound READY event and capture its scalar, and `L_WAIT` for the matching local completion. Argument setup uses `G_MOVI` to load a register and `G_ADDI64` to advance a 64-bit register pair. Program flow uses `G_JNZ` for a forward branch, `G_LOOP` for a counted backward branch, `G_END` to finish the MC program, and `L_END` to release the scope and return status. The local column describes the native P scope profile. The existing U/C/F/J LC services have their own profile bindings.

Each call snapshots eight argument registers. In the native P profile these include a descriptor reference and deployment identifiers. The versioned descriptor holds the work range and operand locations, so scope-specific values can change independently of the instruction format. Figure 2 illustrates two schedules for a table of three consecutive 128-byte descriptors. The common setup loads the first address into the `r0:r1` pair with two `G_MOVI` instructions (`r0` holds the low word). Both schedules advance the pointer by 128 bytes between calls. A chain waits for A before dispatching B and for B before dispatching C. With two independent producers, the MC dispatches A and B before waiting on both tokens with mask `0x3`. The opcode set and service interface serve both patterns. Deployment still binds each data edge to an available path and a compatible service port and must ensure input delivery before the consumer uses the data.

![Chain and parallel-join schedules using the same global instructions](instruction-topologies.svg)

**Figure 2. Instruction classes and topology-dependent scheduling.** (a) Four functional classes cover eight native MC v3 opcodes and the three-opcode native P LC kernel. (b) The same call, pointer-update, and wait instructions express a chain and a two-producer join. A, B, and C denote illustrative targets with compatible services. The arrows represent logical dependencies. The fragments show descriptor-pointer setup and omit the remaining ABI arguments and the product-specific data transfers.

## Implementation example

In the programmed three-P feed-forward network (FFN), each call and each terminal reply crosses the MC–LC interface as four 128-bit flits. The MC validates the source, token, job, epoch, task sequence, generation, and topology before recording a terminal reply. It uses `G_MOVI` to initialize registers, issues three `G_CALL` instructions per iteration, and advances the descriptor pointer by 128 bytes with `G_ADDI64` after each call. `G_WAIT 0x7` waits for all three tokens before `G_LOOP` advances the bounded loop. The 272-byte MC image contains 17 static instructions and dispatches 192 calls over 64 iterations.

Each P LC runs the same three-instruction kernel from a 352-byte image. The LC obtains each 128-byte descriptor through two 64-byte transfers from the shared DMA. The programmed RTL experiment exercised Qwen2.5-3B FFN dimensions with deterministic synthetic integer weights. Both weight-provider variants passed all 36 cases, including checks of quantized intermediate tiles and outputs read back from the original SRAM bank models. With the program images and traffic held fixed, the early-execution provider reduced FFN cycles by 0.52–1.20% across the matched cases. This comparison measures a provider scheduling change within the same control interface. The fixture sequenced K-tile movement and the outer Gate/Up and Down phases. Cross-model mapping is illustrated by the dependency examples in Figure 2.

## Native MC v3 and P LC encodings

The 64-bit MC word places the opcode at bits `[63:56]`, three operand bytes at `[55:48]`, `[47:40]`, and `[39:32]`, and the immediate at `[31:0]`. The table lists the eight decoded MC opcodes. The programmed FFN uses `G_MOVI`, `G_CALL`, `G_ADDI64`, `G_WAIT`, `G_LOOP`, and `G_END`.

| MC instruction | Opcode | Operands used |
| --- | --- | --- |
| `G_EVENT` | `0x12` | Selects a destination register and event binding. Consumes READY and captures its scalar. |
| `G_MOVI` | `0x13` | First operand selects the destination register. The immediate supplies its value. |
| `G_JNZ` | `0x15` | Forward conditional branch on a nonzero register. |
| `G_CALL` | `0x10` | First and second operands select target and token. The LC entry in the third operand is zero. |
| `G_ADDI64` | `0x16` | First operand selects the low register of an even-indexed register pair. The immediate is the unsigned increment. |
| `G_WAIT` | `0x11` | The immediate holds the token mask. |
| `G_LOOP` | `0x17` | First operand selects the loop counter. The immediate is the backward target PC. |
| `G_END` | `0x1F` | No operands. |

| LC instruction | Encoded 64-bit word in the kernel | Action in this profile |
| --- | --- | --- |
| `L_EXEC` | `0x4100000000000000` | Invoke resource 0 with token 0 and execution record 0. |
| `L_WAIT` | `0x4400000000000001` | Wait for the invocation with local mask `0x1`. |
| `L_END` | `0x4F00000000000000` | Release the scope and return terminal status. |

