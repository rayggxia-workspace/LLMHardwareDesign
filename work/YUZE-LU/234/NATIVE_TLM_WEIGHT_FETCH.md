# Native M weight fetch timing

The optional TLM weight fetch models the four M weight banks, one registered request offer with round-robin selection, and a 32-beat credit that runs from M request acceptance through M fill. It uses 17 beats for ordinary W8 and 18 for HEAD16, with the entire record routed by bit 11 of its base. The two physical lanes per channel have bounded 16-entry FIFOs and the return skid has three entries per channel. The numerical path assembles data by beat index from actual DRAM callbacks.

The control-frame admission and fill acknowledgment delays are approximations. The existing shared TLM DRAM scheduler still owns arbitration across M clients and unrelated traffic. Its issue budget applies at simulated DRAM admission, while RTL applies it before the physical lane queues. The P compute and scope control timings are unchanged by this option.

## Native address and time sample

Source `/public/home/yuzelu/project-circuit/issue260-decode638-live-product-ffn-repeat5-SR6Qffhj/replay-105802`. Use nominal `DDR-0/transactions.tsv` and the `generated/assets.txt` allocation. These are two actual layer-zero FFN pages using a 10,000 ps core and shared P0/P1/P2. The disjoint half-open weight intervals are `[711405568,735358976)` gate, `[735358976,759312384)` up and `[759312384,783265792)` down.

Read-only Slurm 111860 yielded 2,245,632 admitted and returned weight beats, exactly `2 × 3 × 23,953,408 / 64`. First physical admit was at core cycle 852,649 and concurrently used lanes 0, 1 and 2. Last admit was at cycle 2,632,315 and last return at 2,632,320. Observed peak was 63 outstanding physical beats across the three M clients. The physical admit-to-return interval averaged 6.63326 core cycles and peaked at 105. The trace records DMA global tags and physical lane handshakes. It cannot attribute allocation or FILL wait to an individual M bank. These are measurements at the fixture clock, with no same-period TLM comparison yet.

To reproduce the observation on a compute node, run this over the nominal trace. Only records emitted at core-clock admit and return edges enter the latency calculation.

```sh
awk -F '\t' '
$5 >= 711405568 && $5 < 783265792 {
    key = $3 ":" $4
    if ($1 == "admit") {
        if (key in active) exit 1
        active[key] = $2
        if (++admitted == 1) first = $2
        if (++live > peak) peak = live
        last = $2
    } else if ($1 == "return") {
        if (!(key in active)) exit 1
        delay = $2 - active[key]
        total += delay
        if (delay > max) max = delay
        delete active[key]
        live--
        returned++
        finish = $2
    }
}
END {
    if (live || admitted != 2245632 || returned != admitted) exit 1
    print admitted, returned, first, last, finish, peak, total / returned, max
}
' DDR-0/transactions.tsv
```
