# F closure implementation continuation

Selected leaf: candidate-S-minimal-localv4. Its original upper routing remains identical to the accepted S, preserving the original F power-grid interface. The accepted leaf receipt, state/control proof and zero-bloat nativeguard abstract were generated successfully.

The first actual F integration (`parent-F-eco-h20-v4`) completed detailed routing and RCX with setup +0.221638709 ns, hold +0.002453537 ns, zero setup/hold/capacitance/slew/fanout violations, zero antenna violations and connected VDD/VSS. Formal and state/control-cone proofs passed. No BPin or macro transform changed.

## Corrected native-checker acceptance

The original accepted F300 native report has 42 markers, SHA 5a4e970df164649a58a6f97e9e7ef099371fcdd282a856cf2e5b0a21081da8cd, despite its complete GDS deck having zero findings. The newly written f-qualify.py had imposed an unsupported empty-native-report condition. This was diagnosed and reported before changing acceptance; parent authorized reproducing the original physical acceptance with every new native marker individually resolved.

The minimal candidate has 44 native markers: 40 exactly match historical records, 2 old G markers disappear, and 4 new S macro-contact markers appear. The new markers were investigated against actual merged GDS. Each belongs to a connected leaf M10 polygon touching only the intended same-net macro pin: rsp_data[115] at three markers and req_addr[3] at one. They represent legitimate same-net material contact, not foreign-net shorts. Evidence is F-native-marker-diff.json and F-new-marker-gds-connectivity.json. Counts alone are never used as an exemption.

Attempts repair1/2/3 and notch/graft explored eliminating checker markers before the historical criterion was verified. These are preserved as unsuccessful alternatives and are not selected for release. The unmodified first integrated candidate remains the selected candidate. No new physical modifications were made to bypass known historical checker artifacts.

## Allocation and final gates

The first full-deck diagnostic on allocation119586 was terminated when that allocation's original batch finished. The F-owned allocation119627 now owns an eight-core sequential dispatcher and an eight-hour deadline. Its queue re-runs the complete, unchanged FreePDK45 deck; no dependency on another baseline worker remains. STOP is written only by successful final release aggregation.

Repeated GDS streamouts differ only in267 BGNLIB/BGNSTR timestamp records. Every other record is byte-identical; the normalized SHA is dc4145f3b943e77bd6f7a56bdd0f1cb5ca7bf7fca0cee7ce2885c183d864f9cd. The raw hashes and exact comparison are preserved in F-gds-timestamp-identity.json. This explicitly binds material-contact evidence to the final streamout without assuming that different file hashes are interchangeable.

Final acceptance remains pending until the unchanged complete deck reports zero findings, independent final STA/PG/antenna checks pass, every native marker matches the reviewed set, and formal/state evidence and leaf hashes match the delivered candidate. Release will contain freshly generated `write_abstract_lef -bloat_factor 0` parent views and hashes of all artifacts. A/B top RC and timing acceptance remain separate.

## Final acceptance completed

Allocation119627 completed successfully. Selected release is `/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/gs/candidate-S-minimal-localv4/parent-F-eco-h20-v4/release/`. This is the first minimal F candidate, not any notch/graft exploration.

Final TT standalone checks: nominal300MHz, original clock uncertainty0.1ns, emitted SDC period3.3333ns (slightly stricter than original3.333333333ns), setup+0.221605405ns, hold+0.002453537ns (2.454ps). Setup/hold/capacitance/slew/fanout violations are all exactly0. Full unchanged foundry deck reports0. VDD/VSS are connected; antenna net/pin violations are0. F all-boundary formal and state/control preservation pass. Signal and power BPin geometry and macro positions remain unchanged. No PVT robustness or A/B top RC claim is made.

The final material audit is v2: every individual actual parent/leaf M10 intersection component independently connects only to its expected macro pin. Coverage difference is empty; unlabeled components fail. The earlier v1 union-level check was strengthened before release. All four new markers pass v2, bound directly to final GDS.

Release includes zero-bloat parent LEF, characterized Liberty, final ODB/DEF/V/SDC/SPEF/GDS, exact new-S config binding, leaf/physical/formal/state receipts, native marker disposition, timestamp-record identity and SHA manifest. Small evidence is synchronized to `audit/evidence/F/`. Final accepted-parent.json SHA256: `60cbc5d7574e07d8fdfbd7646cfbbe25785c3821ead2da9a4967d40b34c0aa5e`.
