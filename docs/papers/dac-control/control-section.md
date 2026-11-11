# Hierarchical Control and Instruction Set

## Two-level scheduling

Model dependencies determine which Blocks can execute together and when a consumer can start. Within a Block, the order and timing of memory accesses, sub-macro operations, and writes depend on the local service and its available resources. Driving all of those steps from the mother controller would tie the global program to each Block's internal sequence and expose local backpressure to the global scheduler.

Figure 1 shows how the two levels separate these decisions. The mother controller (MC) dispatches a service scope to a target Block and tracks completion with a token. The local controller (LC) and its service logic fetch the scope parameters, sequence local memory and sub-macro operations, and wait for the matching completion. In the tested P service, completion includes acknowledgment of the destination writes. The LC then releases the scope and returns terminal status. A single call thus covers a range of local operations, and independent Blocks can advance at their own pace before the MC reaches a dependency barrier. A Block's internal schedule can change while the MC program stays valid, provided the service parameters and completion contract are preserved.

![Two-level control and the local P service](control-architecture.svg)

**Figure 1. Two-level scheduling across and within Blocks.** The MC selects targets and synchronizes calls at Block granularity. Each LC and its service logic control the operations within a Block. The expanded P service illustrates weight and operand supply, compute, and acknowledged writeback. The steps show dependencies within a scope and may overlap during execution.

## Instruction set and topology mapping

The ISA gives the two levels separate 64-bit instruction streams. At the global level, `G_CALL` selects a target and completion token, and `G_WAIT` identifies the required tokens through a mask. A call snapshots eight argument registers. In the native P profile, these carry a descriptor reference and deployment identifiers. The versioned descriptor holds service parameters such as the work range and operand locations, so scope-specific values can change independently of the instruction format. At the local level, the P kernel uses `L_EXEC`, `L_WAIT`, and `L_END` to launch a registered service, wait for its matching completion, and release the scope.

Figure 2 shows two dependency patterns that can arise when mapping different models. For a chain of dependent operators, the MC waits for A before dispatching B, then waits for B before dispatching C. For two independent projections feeding C, the MC dispatches A and B before waiting for both tokens. The opcode set and call/return interface serve both patterns. The mapping supplies the target IDs, call order, wait masks, and service parameters for each graph. This permits reuse of compatible Block services across model mappings. Deployment must also bind every data edge to an available path and a compatible service port. The wait mask orders work, while the deployed data paths carry the operands.

![Chain and parallel-join schedules using the same global instructions](instruction-topologies.svg)

**Figure 2. Mapping two logical dependency graphs to the same global ISA.** A chain uses separate waits for tokens 0 and 1. Two independent producers use one wait with mask `0x3` before dispatching their shared consumer. Both examples wait for token 2 at the end. A, B, and C denote illustrative Block targets with compatible services and data paths. The arrows represent logical dependencies. The instruction fragments omit the argument setup for each call.

## Implementation example

In the programmed three-P feed-forward network (FFN), each call and each terminal reply crosses the MC–LC interface as four 128-bit flits. The MC validates the source, token, job, epoch, task sequence, generation, and topology before recording a terminal reply. It uses `G_MOVI` to initialize registers, issues three `G_CALL` instructions per iteration, and advances the descriptor pointer by 128 bytes with `G_ADDI64` after each call. `G_WAIT 0x7` waits for all three tokens before `G_LOOP` advances the bounded loop. The 272-byte MC image contains 17 static instructions and dispatches 192 calls over 64 iterations.

Each P LC runs the same three-instruction kernel from a 352-byte image. The LC obtains each 128-byte descriptor through two 64-byte transfers from the shared DMA. The programmed RTL experiment exercised Qwen2.5-3B FFN dimensions with deterministic synthetic integer weights. Both weight-provider variants passed all 36 cases, including checks of quantized intermediate tiles and outputs read back from the original SRAM bank models. The fixture sequenced K-tile movement and the outer Gate/Up and Down phases. The experiment provides evidence for programmed FFN execution within this fixture. Cross-model mapping is illustrated by the dependency examples in Figure 2.

## Instruction encodings used in the FFN example

The 64-bit MC word places the opcode at bits `[63:56]`, three operand bytes at `[55:48]`, `[47:40]`, and `[39:32]`, and the immediate at `[31:0]`. The table lists the operands used in the FFN image. Omitted operands are zero in this image.

| MC instruction | Opcode | Operands used |
| --- | --- | --- |
| `G_MOVI` | `0x13` | First operand selects the destination register. The immediate supplies its value. |
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

