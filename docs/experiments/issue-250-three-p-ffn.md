# Three-P FFN on the shared S and DMA

The complete Qwen2.5-3B FFN dimensions were exercised through three native M2 engines, three original 16 KiB P.S instances, one original 16 KiB U.S and the G32 SiLU service. The independent integer oracle uses deterministic synthetic weights and input at the exact model dimensions. It checks the 86 quantized Mid tiles and their shifts, and checks every one of the 512 Down result words after reading them back from the original SRAM bank models.

U.S holds 8 KiB of S32 X and up to 4 KiB of quantized X. Each P uses a 256 B active input window, 512 B Gate/Up scratch and its assigned share of Mid in the existing S. The three Mid owners hold 29, 29 and 28 tiles. The Down ranges read each tile from its real owner and copy it to all three P input windows. The same-S source and destination use the existing ordered physical port with separate arbitration clients. There is no new SRAM bank and no new physical SRAM port. Each range terminal waits for real output write acknowledgments.

| Evidence | Workload | Passed | Cycles in seed 25001 with an unstalled backend |
| --- | --- | ---: | ---: |
| 102556 | Complete FFN, previous single-return fixture | 36/36 | 2,926,223 |
| 102563 | Complete FFN, shared typed dual-channel DMA, serial weight fill | 36/36 | 1,543,319 |
| 102564 | Complete FFN, same DMA and inputs, four-bank weight lookahead | 36/36 | 858,678 |

The paired DMA runs have 748,544 W64 Gate/Up returns, 374,272 W64 Down returns, 44,544 acknowledged Gate/Up input copies, 5,504 acknowledged scatter words and 24,768 acknowledged Down input copies. All 36 paired cases conserve the same traffic. Four-bank lookahead saves 42.54% to 44.36% of FFN cycles against the serial provider in this experiment. It uses the four existing M weight banks and two added bounded metadata slots. The DMA has four physical request lanes, two per channel. The fixture asserts at most four accepted requests per channel in every three-cycle window, corresponding to an aggregate ceiling of 51.2 GB/s at 300 MHz. The two pressure modes vary request and SRAM service availability. The cycle model uses a finite deterministic DDR peer behind the actual DMA RTL.

Repeating the unstalled measured FFN cost for 36 sequential layers consumes 30,912,408 of the 32,553,329 cycles allowed by the 9.215647 tok/s threshold. The remaining 1,640,921 cycles must cover the other operators, transfers and control unless a later schedule proves overlap. The elapsed FFN phases exclude test readback between phases. These results bound the performance work and isolate a hardware scheduling gain. The program deployment, real model weights, full-token SystemC estimate and system physical acceptance each have separate gates.

The emitter binds the scope table to a 272 B mother image and the 352 B LC kernel used by each P. The 17 static MC instructions expand to 192 CALLs in the complete FFN. The expected terminal counters are 71,884,800 read bytes, including the 24,576 B descriptor arena, and 96,256 write bytes. The earlier paired DMA runs offered scopes from the test controller. The programmed variant brings actual PM fetch, MC/LC frame transport and descriptor reads into the same fixture.

| Evidence | Programmed FFN scope | Passed | Gate/Up + Down cycles, seed 25001 mode 0 init 0 |
| --- | --- | ---: | ---: |
| 102601 | 384-column two-stripe regression | 36/36 | 21,681 + 0 |
| 102604 | Complete FFN, four-W provider | 36/36 | 590,628 + 269,574 = 860,202 |
| 102603 | Complete FFN, four-W plus early EXEC | 36/36 | 586,103 + 263,811 = 849,914 |

For the complete program both providers confirmed 71,884,800 read bytes and 96,256 write bytes in all trials. Their DMA request and return counters both reached 1,123,200. The early provider saves 0.5223% to 1.1960% across 36 matched cases. This is a provider scheduling change on a fixed instruction image. The fixture still orchestrates the K-tile movement and outer Gate/Up and Down phases. The existing MC transport/fetch timeout remains 4,096 cycles. The fixture uses 131,072 cycles for WAIT on a valid outstanding service after job 102599 showed the original watchdog expiring during live FFN work. There is no instruction format change.

The matched channel-placement experiment 102614 shifts the Up weights by 2,048 bytes to change their DDR channel. All 36 cases passed at identical confirmed traffic and numerical outputs. The change ranges from a 0.2306% slowdown to a 0.2278% speedup. Retain the original placement as the baseline.

Run 102622 prepares each noninitial K tile after the previous window has released and its S reads have drained, before all three next-window requests arrive. It uses the same single S window and copies the same words. The paired full run saved 0.1104% to 1.3207% over 102603. In the first unstalled case it moved the wait from before COPY to the A proof after COPY and reduced 849,914 to 848,976 cycles. This scope uses the test fixture to sequence the tiles. Production use still requires LC ownership and cancellation integration.

Independent combined test 102615 used two 384-column scopes, real typed DMA and three P engines. All 48 cases verified that the old COPY response remains owned until the actual acknowledgment, that one local rearm preserves the next admitted scope and that each M completes 22 real transport FENCE receipts. The local COPY and DDR generations remain separate namespaces.

SystemC 102621 uses the 102603 programmed FFN phases and measured native S80 primitive fees. At B1 decode context512, 300 MHz and 51.2 GB/s, its unstalled configuration estimates 50,003,806 cycles or **5.999543 token/s**. Of those, 30,596,904 are the 36 measured FFN phases, 243,247 are modeled FFN boundaries and 19,163,655 are the modeled remaining path. The all-pressure case is 5.338631 token/s. This replay still needs integrated Attention and system electrical and energy evidence. The FFN comparisons above hold the program fixed and measure changes in the provider or tile sequence.

The source hashes, remote receipt hashes, failing runs and successful runs are recorded in `work/YUZE-LU/250/native-services/ffnnative/index.json`. The independent `audit_ffn_native.py` verifies raw receipts, descriptor byte order and CRC, the exact MC and LC images, confirmed bytes, numerical pass counts and matched traffic. Invoke it with one or more `--receipt-cache` paths containing the raw archive mirrors.
