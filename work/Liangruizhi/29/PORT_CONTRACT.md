# Issue29 two-bank beat port reference RTL

This is an executable protocol model for comparing fixed bank/link/port resources. It does not instantiate a technology SRAM macro, prove timing closure, or measure PPA. Its behavioral arrays and synchronous registered results need separate technology mapping and physical validation.

## Interface

Module `bank_port_fabric` has `PORT_MODE` integer 0/1/2, `RESP_DEPTH` integer 1/2/4, and typed `logic [5:0] LINK_MASK`. Endpoint numbers are M=0, V=1, D=2. Bank numbers are 0/1. Link bit `ep*2+bank` enables that exact endpoint-to-bank pair. A disabled request never handshakes.

| Port | Width | Meaning |
| --- | ---: | --- |
| `clk`, `rst` | 1 each | Rising-edge clock; synchronous active-high reset |
| `req_valid`, `req_ready` | 3 each | Per-endpoint request handshake |
| `req_bank`, `req_write` | 3 each | Bank selection and write/read flag |
| `req_addr` | 30 | Three 10-bit beat addresses, not byte addresses |
| `req_wdata` | 1536 | Three 512-bit write data fields |
| `req_wstrb` | 192 | Three 64-bit byte masks |
| `req_tag` | 96 | Three 32-bit opaque request tags |
| `rsp_valid`, `rsp_ready`, `rsp_write` | 3 each | Response handshake and write acknowledgement flag |
| `rsp_data` | 1536 | Three 512-bit registered read results; write ack payload zero |
| `rsp_tag` | 96 | Original request tag, returned in per-endpoint acceptance order |

All packed vectors put endpoint 0 in the least-significant slice: `req_addr[ep*10 +: 10]`, `req_wdata[ep*512 +: 512]`, `req_wstrb[ep*64 +: 64]`, and `req_tag[ep*32 +: 32]`; responses use the same convention. `req_ready` is high only for a selected valid request. This is a custom ready/valid interface, not an AXI compliance claim.

## Edge and queue semantics

The external checker should sample all handshake signals immediately before a rising edge. An accepted request is `req_valid && req_ready` at that edge. Each endpoint has one finite FIFO of responses, including write acknowledgements. Every accepted request reserves one response entry; there is no additional request queue or uncredited read-result stage. The source must hold valid and all request fields unchanged while waiting for ready.

A full FIFO can accept a new request when its existing response head is consumed at the same edge. This creates an intentional combinational path from `rsp_ready` through credit and arbitration to `req_ready`. There is no combinational request-to-response bypass: an accepted read/write response is registered at the grant edge and can first be consumed at a later rising edge. The FIFO payload register itself holds the read result. FIFO head valid/write/data/tag remain stable while valid and not ready; invalid outputs are zero.

Each bank contains 1024 512-bit rows. An accepted write commits selected bytes on the grant edge; strobe bit `lane` updates bits `lane*8 +: 8`. A zero mask is a no-op write with a normal acknowledgement. An accepted read captures the addressed bank row's pre-edge value. Same-bank same-row dual grants are conservatively prohibited for R/R, R/W and W/W, so no dual-grant same-address read-during-write behavior is delegated to a memory macro. Equal row indices in different banks are independent.

If an endpoint's current response head is valid and is a read, that endpoint cannot be granted a write, even when that read response will be consumed at this edge. The read response owns the endpoint's half-duplex 512-bit data channel throughout that edge. Read request control may overlap a read response. A write acknowledgement carries no data-channel traffic.

Reset immediately gates external request-ready and response-valid low while asserted, and on its rising edge clears FIFO pointers/counts and arbiter pointers. Reset discards pending responses but does not clear SRAM or require payload-register clearing. Consumers must not read a bank row before initialization; a two-state simulator's default value is not valid evidence of initialized memory.

## Arbitration and ports

Each bank scans three endpoints from its own round-robin pointer and chooses up to two eligible requests. A request needs its link enabled, response credit, half-duplex permission, and a free port of the permitted kind. Each endpoint can receive at most one grant per edge.

| `PORT_MODE` | Maximum accepted requests per bank per edge |
| ---: | --- |
| 0, 1RW | One read or write |
| 1, 1R1W | One read and one write, at distinct rows |
| 2, 2RW | Two operations of either kind, at distinct rows |

The pointer advances to the endpoint after the **first** selected winner, even if the bank grants two operations. Advancing after the last winner can starve the second read source under persistent R0/R1/W2 traffic. This greedy scan does not promise equal throughput between operation classes or endpoints. For example, the directed mixed-operation fixture gives mode1 grants 8/4/12 over 12 edges while serving every endpoint. Fairness statements require continuous eligibility and available downstream response credit; blocked links, indefinitely stalled sinks and read-response/write conflicts are not starvation evidence. The local fixture measures maximum consecutive ungranted edges from external handshakes, without inspecting the pointer.

## Explicit storage inventory

The bank arrays contain `2*1024*512 = 1,048,576` bits (128 KiB total). The three response FIFOs contain `3*RESP_DEPTH*(512+32+1) = 1,635*RESP_DEPTH` payload bits; write acknowledgements use the same allocated width. Pointer width is `max(1, clog2(RESP_DEPTH))`; count width is `clog2(RESP_DEPTH+1)`. Arbiter pointers require four additional stored bits.

| Depth | FIFO payload bits | FIFO pointer/count + RR bits | Banks + response payload + control bits |
| ---: | ---: | ---: | ---: |
| 1 | 1,635 | 13 | 1,050,224 |
| 2 | 3,270 | 16 | 1,051,862 |
| 4 | 6,540 | 25 | 1,055,141 |

Combinational arbitration and output muxes are not storage. The source supplies and retains blocked write requests externally. No hidden endpoint staging is included. Interface assertion-history registers sit under `ifndef SYNTHESIS` and are not part of the synthesized inventory. Declared logical bits are not SRAM area or implementation area.

## Checks and reproducibility

`bank_port_fabric.sv` has simulation assertions for parameters, FIFO credit/count/pointer validity, disabled-link exclusion, request/response stall stability, data-channel conflicts, contiguous grant slots, per-mode limits, duplicate endpoint grants and same-row exclusion. They are simulation monitors, not formal proof.

Actual local checks used the existing ModelSim ALTERA STARTER EDITION 10.1d (2012.11), with no installs. `run_local_smoke.py` executes `vlog -sv` and all 3 modes by 3 depths, retaining commands and logs in `local-smoke-results.json`. All nine passed. The smoke covers reset, finite FIFO full stall and same-edge pop/push including depth1, registered read result, stalled and popping read-head/write exclusion, read-control overlap, same-row R/R serialization, independent banks, mixed-operation persistent arbitration, byte strobes/no-op write, SRAM retention across reset, and disabled-link exclusion. This is a directed protocol check, not exhaustive verification. Parent-owned Verilator/harness runs and independent external replay remain separate evidence.

For Verilator typed-parameter overrides, pass a sized literal as one argv item, e.g. `-GLINK_MASK=6'd63`. Passing unsized `63` triggers strict width warnings; the RTL's typed parameter should remain intact.
