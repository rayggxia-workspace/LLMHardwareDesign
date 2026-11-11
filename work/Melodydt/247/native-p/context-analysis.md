# Actual run10 native M context cycles

This file analyzes standalone M with release included. The final whole-P timing is run11 (K11 672→676; K59 2112→2032), documented in the main report; run10 whole-P output-prefix timing is historical.

Source commit: `c2359bdeeea83270ab632861eebe6ffc8dcc510e`. All numbers are actual RTL cycles, not token/s or physical clock qualification.

Each table cell is legacy / reordered-reload-A / reordered-reuse-A. All three routes have the same per-case tensors, active N, direct integer golden values and B work. The last two also have the same commands. The context routes include one explicit release per context.

| Contexts | Improved / equal / regressed (44 cases) | Equal-test-mix cycles (legacy/reload/reuse) | Cycle reduction vs own legacy |
|---|---|---|---|
| 1 | 0 / 0 / 44 | 6176/6264/6264 | -1.424870% |
| 2 | 20 / 8 / 16 | 12352/12528/12032 | 2.590674% |
| 8 | 28 / 0 / 16 | 49408/50112/46640 | 5.602332% |

These totals weight the 44 tests equally; they do not represent a model. Context counts execute different numbers of output groups and different random-vector streams, so their total cycles are not a fair direct cross-context comparison.

All 132 distinct case/configuration rows exactly satisfy `reload = legacy + 2*contexts` and `reuse = reload - saved_A_handshakes`. Thus the reordered loop itself has no observed standalone cycle gain; its extra release command costs two cycles per context. A reuse saves one cycle per eliminated native A handshake in this serialized driver.

## All 44 cases for eight contexts

| K | S8×S8 | S16×S8 | S8×S16 | S16×S16 |
|---|---|---|---|---|
| 1 | 288/304/297 | 304/320/313 | 312/328/321 | 360/376/369 |
| 7 | 288/304/297 | 304/320/313 | 312/328/321 | 360/376/369 |
| 8 | 288/304/297 | 304/320/313 | 312/328/321 | 360/376/369 |
| 9 | 312/328/314 | 344/360/346 | 360/376/362 | 456/472/458 |
| 31 | 360/376/348 | 424/440/412 | 456/472/444 | 648/664/636 |
| 32 | 360/376/348 | 424/440/412 | 456/472/444 | 648/664/636 |
| 33 | 504/520/485 | 584/600/565 | 624/640/605 | 864/880/845 |
| 65 | 720/736/673 | 864/880/817 | 936/952/889 | 1368/1384/1321 |
| 255 | 1872/1888/1664 | 2384/2400/2176 | 2640/2656/2432 | 4176/4192/3968 |
| 256 | 1872/1888/1664 | 2384/2400/2176 | 2640/2656/2432 | 4176/4192/3968 |
| 257 | 2016/2032/1801 | 2544/2560/2329 | 2808/2824/2593 | 4392/4408/4177 |

Best: S8×S8 K255/256, 1872→1664 cycles (11.111111% fewer cycles; 12.5% higher fixed-work rate). Worst: S8×S8 K1/7/8, 288→297 cycles (3.125% more cycles; 3.030303% lower fixed-work rate). All formats regress for tested K1/7/8/9. Every tested K31 and above improves with eight contexts.

## K257 representatives for eight contexts

| Format | Legacy/reload/reuse | Cycle reduction | Same-work rate gain | A beats | B beats | Commands legacy/context |
|---|---|---|---|---|---|---|
| S8xS8 | 2016/2032/1801 | 10.664683% | 11.937812% | 264→33 | 264 | 192/200 |
| S16xS8 | 2544/2560/2329 | 8.451258% | 9.231430% | 264→33 | 264 | 192/200 |
| S8xS16 | 2808/2824/2593 | 7.656695% | 8.291554% | 264→33 | 528 | 192/200 |
| S16xS16 | 4392/4408/4177 | 4.895264% | 5.147235% | 264→33 | 528 | 192/200 |

The standalone M tests include four raw-result and two final-RNE commands per group, with register operand loads and no S or DDR model.

## Receipt and denominator review

- All 15 M runs passed. Original and candidate legacy results match exactly: 68,787 checks, 45,724 cycles, 96 cases, latencies [53,114,114,306]. The three reset/initialization repetitions reproduce the same 132 distinct context-case rows; they are not 396 distinct numerical cases.
- Policy: total steady cycles stay 516; 64 consumer responses and transaction/reset denominators stay fixed. Lower consumer latency must not be presented as global throughput gain.
- Memory backend: 64 narrow + 32 wide commands and 192 physical bank operations remain fixed; both take 99 cycles. Local integration keeps 64 writes, 6 wide reads, A16/B2 while cycles fall 122→71; concurrent admission changes, not work deletion.
- Full P: all three initializations reproduce 672→644 cycles with B16 and 16 output stores unchanged; A16→2 and wide reads32→18. Adding independent-bank access gives 644 again in this matched arithmetic workload. The separate overlap probe is outside that timing window.
- Full-P timing starts after identical S preload and ends at output write ACK. It excludes readback validation and context release; the standalone-M table includes release. The 4.166667% P cycle reduction (4.347826% fixed-work rate gain) is a finite output-completion measurement, not sustained reuse throughput. Context variants also enable priority, though this timed serial program injects no competing ordinary client.
- Verified 91 SHA entries across 76 unique receipt paths; all 25 top-level commands exit zero and all component receipts bind correctly. Five relevant formal functional files match the measured input manifest.

Machine evidence: `analysis.json` contains all 44 cases for each context count and the checked receipt hashes. Production source was not changed; no local EDA was run.
