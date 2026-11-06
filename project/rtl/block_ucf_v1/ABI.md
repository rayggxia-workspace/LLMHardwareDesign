# U16 / C16 / F16 Block transaction interface

U uses N, E and N4; F uses G, E and N4; C uses R256, G, E and N5. All three private S instances expose 1,024 words of 128 bits. A word address is 10 bits; clients do not accept a byte address. The ordinary S path is fixed in RTL. No direct N→E, G→E or R→E metal bypass is assumed by this contract.

| Lane | U16 | F16 | C16 | S client |
| --- | --- | --- | --- | --- |
| 0 | E | E | E | 0 |
| 1 | N | G | G | 1 |
| 2 | absent | absent | R256 | 4 |
| RX | destination write | destination write | destination write | 2 |
| TX | source read | source read | source read | 3 |

Each compute lane accepts one command on `cmd_valid && cmd_ready`. Its slice is indexed from lane 0 at the least significant end. `cmd_sources` is the number of 128-bit operands (0–3); addresses A, B, C are in increasing 10-bit slices of `cmd_addresses`. `cmd_store` requests a successful result be written to `cmd_dst`. Source operands are captured before execution so a destination may alias a source after its lifetime has ended. An arithmetic error suppresses writeback. With writeback enabled, `done_valid` asserts only after the S write response is consumed. The completion and its result remain available until `done_ready`.

| Engine | Used `cmd_meta` fields | Source / result contract |
| --- | --- | --- |
| E | `[3:0]` operation, `[8:4]` shift | Existing E numeric contract; A/B/C are 128-bit values. |
| N | `[3:0]` operation, `[7:4]` count, `[39:8]` parameter | Existing N context and statistics/replay protocol; A data, B auxiliary data. A context stays on one N. |
| G | `[2:0]` function, `[3]` gate enabled | Low 32 bits of A and B contain two S16 lanes. The result is zero extended from 32 to 128 bits. |
| R | `[1:0]` adapter command | Native loads, commands, state reads and retained result slices as below. |

R adapter command `0` takes A and uses `[4:2]` as the native load target and `[14:5]` as the load index. Callers must obey the native load bounds (state half-row 0–63; key/query packet 0–3; x/update/skip and history packet 0–5; tap packet 0–3). Command `1` maps `[4:2]` native op, `[13:5]` rows, `[14]` role, `[15]` clear, and `[17:16]` mode. A successful native response replaces the retained 512-bit result. Command `2` reads state bank `[2]` and half-row `[12:3]` (0–63); command `3` reads slice `[3:2]` of a valid retained result, with slice 0 in bits 127:0. State version publication for a full token belongs to the upper controller.

RX accepts a reserved destination address and 128-bit data on `rx_valid && rx_ready`. It asserts `rx_stored` after actual S storage and holds the response until `rx_stored_ready`. TX accepts a read on `tx_req && tx_ready`, then holds `tx_valid/tx_data` until `tx_take`. A transport using these signals must reserve the destination, associate acknowledgements with the correct object and release the source only after destination storage. Reset clears in-flight protocol state; it does not erase the contents of SRAM. Reserved command bits are not routable services and may have no native cell loads even if the physical interface preserves their pin names.
