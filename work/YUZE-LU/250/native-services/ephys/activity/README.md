# E32 AP64 post-route activity

Job 102629 replays activity from the accepted 234 × 234 µm E32 AP64 final ODB. The waveform comes from job 102602 with the real-bank functional fixture and original TT Liberty/SPEF. The zero-delay gate simulation preserves the bank model's 10 ns functional clock and normalizes timestamps to 3,333 ps for the activity calculation.

OpenSTA directly resolved 6,763 pins in the original VCD import. The raw ODB doubles the Verilog escape in flattened gate names. The checked replay resolves each waveform alias to one exact ODB terminal and annotates 89,389 gate pins, plus the original 158 top-level bits. The final three activity reports have zero unannotated pins.

| Replay | Total power at TT300 |
| --- | ---: |
| Mixed active case, 92 services | 5.451 mW |
| Same active duty and clock toggles with nonclock transitions zeroed | 4.565 mW |
| Clocked reset-state idle | 5.725 mW |

The first two rows yield **0.13481 nJ incremental nonclock activity per observed mixed service**, with **0.82940 nJ absolute active energy per observed mixed service** over 4,200 cycles. The reset-state idle has different state duty and is kept as a separate control. The earlier 102598 partial-annotation value is diagnostic. This report covers the E leaf and excludes the SRAM, frontend, M11/M12, and external memory. Whole-model J/token remains pending.

[Independent audit summary](run102629/summary.json) and [source and raw artifact hashes](run102629/remote-evidence.txt) identify the exact archived waveform and tables. Recheck the bounded receipts with `python project/experiments/w8a16_physical/audit_e_activity.py --run work/YUZE-LU/250/native-services/ephys/activity/run102629`.
