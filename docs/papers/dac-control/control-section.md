# Hierarchical Control and Instruction Set

The control plane splits task dispatch and local service execution between a mother controller (MC) and a local controller (LC) for each participating compute group. The MC fetches 64-bit instructions from program memory, dispatches calls to selected LCs, and tracks their completion with tokens. Each call carries a target, a token, and a snapshot of eight argument registers. In the three-P feed-forward network (FFN) experiment, these registers supply a descriptor address and the identifiers required by the native scope interface. Each call and each terminal reply crosses the MC–LC interface as four 128-bit flits. The MC checks the source, token, job, epoch, task sequence, generation, and topology before recording a terminal reply.

The two instruction streams operate at different granularities. The MC program initializes registers with `G_MOVI`, issues a `G_CALL` to each of the three P instances, and advances the descriptor pointer by 128 bytes with `G_ADDI64` after each call. `G_WAIT` with mask `0x7` synchronizes the three tokens before `G_LOOP` advances the bounded loop. The complete FFN bundle uses 17 static MC instructions in a 272-byte image. Its 64 loop iterations dispatch 192 calls.

Each P LC fetches a three-instruction kernel from a 352-byte image. `L_EXEC` initiates a service invocation. The LC reads the program metadata and obtains the 128-byte descriptor through two 64-byte transfers from the shared DMA before offering the request to the P service. `L_WAIT` waits for the completion carrying the matching task owner and ticket. The P service waits for actual destination write acknowledgments before reporting successful completion for the tested FFN ranges. `L_END` releases the descriptor scope before the LC returns its terminal status to the MC. This lets the MC express parallel calls and a barrier while the LCs handle the descriptor and service lifetimes.

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

## Validation scope

The programmed RTL experiment used Qwen2.5-3B FFN dimensions and deterministic synthetic integer weights. Both weight-provider variants passed all 36 cases, checking the quantized intermediate tiles and the outputs read back from the original SRAM bank models. The test fixture sequenced K-tile movement and the outer Gate/Up and Down phases. The measurements cover programmed FFN execution within that fixture. Full-model behavior and joint physical closure are separate acceptance targets.

## Figure caption

**Figure 1. Hierarchical control in the programmed three-P FFN fixture.** (a) The MC dispatches and synchronizes the calls. Each LC obtains a scope descriptor through the shared DMA and invokes its associated P service. The service reports completion after destination write acknowledgment. (b) One MC iteration issues three calls with successive descriptor addresses and waits for their terminal replies. Each LC executes the same three-instruction kernel for its own call. The diagram shows execution order without a cycle scale.
