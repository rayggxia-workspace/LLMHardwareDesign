# Issue104 frozen complete-GDN contract

Liangruizhi / task/104-gdn-state / base99 PR103@8c51f5df74ff5658ee159ee463f13dea6f691237. Only own server issue104-gdn-state-20261025/lrz-i104-*; all real tensors/bigint/RTL/map/gate on server. No new weights/models/Phi/tools/other machines. Root publishes PR, no self-merge/done.

## Scope and arithmetic

Two complete heads0/1, K128/V128. S32 codes[-2147483648,2147418112], power2 I8 unit per head (includes -128); Q/K/V symmetric S16, QK unit-15, beta U16Q15 inclusive32768, decay U32Q31 inclusive2147483648. V units fixed per source. Native32 starts position128/version0/units[-28,-28]/V[-11,-10]; portable12 starts position7938/version2/units[-27,-33]/V[-10,-10]. No reset to native intermediate states. Whole256 is provenance/boundary analysis only, not executed here. Original full256 metadata has34bit aligned/residual; selected12 and native32 have33bit correction. Keep I64 stages, add synthetic34bit coverage, never narrow to observations.

Stages: decay=RNE31(S*d); prediction=RNE15(sum_complete_K(decay*K)); aligned=RNE(V,eS-eV); residual=aligned-prediction; correction=RNE15(residual*beta); proposal=decay+RNE15(K*correction). Only after BOTH complete heads pass S32 range guard compute Y=RNE15(sum_complete_K(proposal*Q)), stored I64 with post-trial state units. No success clipping, no partial-K RNE. Whole-group conservative maxima/product/sum guards preserve68 semantics. Retry only current token: range badmask heads fully RNE1 trial-old, their units+1; numeric width guard affects both. One shared numeric_epoch increment per wave, max8 waves/9 attempts, unchanged published context until one complete group commit. I8/epoch exhaustion rejects, no wrap. All guard/proposal/output stages get independent bigint reference; old68 oracle alone does not implement every conservative format guard.

For fixed S32/K128 format, P=ceil(128*2^31*32767/32768)=274869518336. Aligned bound B=ceil(32767/2^s) for s>=0 or32767*2^(-s). Strongest format test (B+P)*32768<=I64_MAX implies all other declared-stage format bounds; integer s=eS-eV must be>=-32. Numeric format failures use all-head retries. Original rne shift outside[-62,62] throws uncaught ValueError, not a proved recovery path: explicitly reject E_FORMAT if an admitted/current aligned shift exceeds62 (lower end fails numeric format first), preserve published context; do not call that old68 boundary qualification. Left shifts/product/additions checked before execution; I64_MIN rejected wherever absolute/RNE is required.

wide104 performs I64*a small S16/U16 b using abs(a) radix2^31 chunks(31/31/1bit), three exact positive signed32 products with abs(b)<=32768. Each shifted term checked p<=I64_MAX>>shift and acc<=I64_MAX-term, shift0/31/62. Restore sign after exact whole product; one final RNE in controller. No128/96-bit free multiplier/accumulator. Three S32 requests per wide product; input magnitude64+small magnitude16+accumulator64 and all control/mux/guard/shift/add registers mapped. Decay==2^31 identity branch; other decay/prediction/output use one signed32 product. No-retry materialized full-group nominal197376 S32 requests before decay endpoint bypass. Counts are actual, not a clock/PPA prediction.

## Fixed finite storage and data interface

Single16KiB128bit1RW store, one S32 service with independent peer holder; no S8 bank or SFU instantiated in standalone104. Vpair2 retains complete K. Scratch lines0..97 coeff1568B, lines128..255 decay pair2048B(2 S32 codes/row, upper64 zero), lines256..287 reserved512B frame, all other lines canary/unused. Logical decay pair1024B occupies2048B physically; source four-code line is reread for each pair, charged. All prediction/outer/readout phase costs explicit. Complete proposal is external I64, not clipped scratch.

External fixed1MiB window [0x04000000,0x04100000):
- state banks each128KiB at offsets0/0x20000;
- trial128KiB at0x40000;
- proposal I64 256KiB at0x60000;
- Y banks each2048B at0xa0000/0xa0800;
- metadata banks each64B at0xa1000/0xa1040;
- atomic root16B at0xa1080;
- 32 coefficient slots,1568B each at0xb0000 (end0xbc400).
Mutable659600B + coefficient50176B =709776B active; whole1MiB inventory charged. ONLY32 slots/window, not256 inputs; no silent capacity extension. Caller-provided imported checkpoint is read-only initial evidence until RTL begins; no zero INIT replacing nonzero old state. RESTORE reads actual root and four metadata words and leaves state_validated=0; this is metadata-only acceptance. STEP clone checks all32768 old codes, including forbidden0x7fff0001..0x7fffffff, and E_STATE rejects invalid import without any retry or publication. Successful full clone marks state_validated=1. No hardware SHA engine claimed.

Coefficient slot word0: magic32 0x47444331, slot32, expected_position64. Word1: decay0U32,decay1U32,beta0U16/beta1U16,reserved32zero. Words2..33 Q[2,128] S16;34..65 K;66..97 V. Host supplies only original integer coefficients/checkpoint, no predicted/intermediate/new state/output.

Metadata64B, word0 bit[31:0]magic0x47444e31,[47:32]profile1,[79:48]owner32,[84:80]head0=0,[89:85]head1=1,[95:90]flags0,[103:96]eS0,[111:104]eS1,[119:112]eV0,[127:120]eV1. Word1 position64 low/version64 high. Word2 numeric_epoch32 low/context_id64 bits95:32/bank bit96/reserved127:97zero. Word3 coeff_base32,capacity_slots32=32,state_base32,Y_base32. Context_id is caller logical sequence ID, NOT source SHA/authentication. Addresses exact frozen banks, all metadata validated. Root128: magic32 0x47445231,bank bit32,valid bit33,reserved63:34zero,version64 high; root version aliases metadata VERSION, never position. position64/version64 independent, STEP rejects either at max; version may begin2 at position7938. Read root+4 words; metadata/root mismatch rejects. No per-head descriptor publication.

## Command, publication, recovery

Explicit cmd_ready/accept; config pending wins, no swallowed command; accepted owner/context/position/version/slot lock. Single operation RESTORE or STEP. One external transaction outstanding, original5*128bit beats/transaction, request/response32bit transport generation sideband separately. S request/write ACK, S32 exact response/take; peer holder independent from R completion. Generation independent of numeric_epoch/version, no wrap. Terminal generation rejects new command; coordinated hardreset/fabric barrier needed for restart.

STEP full-group trial clone, proposal/guard, shadow state and Y, four metadata writes all ACK before OFFER. Consumer accept begins irreversible root commit immediately; abort not ready thereafter. Root ACK marks committed, response held untilack. Single owner controls external memory; no concurrent external readers/writers are permitted while busy. DONE-held caller may export current Y/state; ack asserts that export and all old checkpoint/output references are released before next command. Inactive bank reuse is legal only after that release; there is no immutable multigeneration snapshot promise. Test hold/reject must preserve current published bank/root. Reject/abort before accept retains old root/state/Y; scratch/private banks may change. Read-chain abort stops new IO and drains accepted S/link/mul/wide requests; no lost same-cycle ACK. Pending writes may apply late; no private reuse until drain. Peer responses belong to peer and can remain held across offer/reject/RESTORE. Hardreset resets common service only after peer/fabric coordination; late private/root write may have applied, so restore ACTUAL root, never host-assumed prior bank. Atomic128bit root plus write-ACK ordering are fabric assumptions, not macro proof.

Consumer interface is acceptance/metadata cut, not Qwen full gated norm/projection. Outputs I64 twohead2048B; consumer read traffic not silently counted as performed. Shared service candidate is not yet integrated with97/102/106. Physical macro/STA/RC/manufacturing/fullmodel quality remain unqualified.

## Acceptance preregistration

Native32 and portable12 complete both heads in quiet and held/peer modes, same core continuation and periodic actual RESTORE. Strict independent bigint/format/global guards/all32768state/256Y/unit/epoch/position/version each record. Synthetic unsigned endpoints, signed ties, S32 asymmetric upper edge,34bit aligned/residual and33bit correction, I64 product/shift/add boundaries, all/one-head retry, retry/unit/epoch/version/position exhaustion, invalid root/metadata, peer held, allphase abort/reject, delayed write and same-cycle ACK, hardreset after applied private/root write. Actual file mutation + recomputed SHA rejected semantically. Lowerer dedicated fixed-boundary and random integer stress, but kernel tests do not replace full-GDN runs.

Map exact final source and inventory, raw gate complete twohead normal and actual rescale checkpoint underquiet/held, same driver RTL and bigint. First gate pilot preregister bounded runtime before remainder, no endless rerun. Full artifacts/input/source byte provenance/failed runs remain server; selected metadata/source and SHA index in repo. Local firstcheck scripts/check_project.py, never treat structure as business acceptance.

## Accepted implementation clarification (after frozen experiment source)

The actual admission `s>=-32` is an algebraic proof that ALL original conservative format/product/add/reduction guards fit I64 in this fixed domain; hardware does not add an uncounted global max-scan. Independent receiver evaluates original conservative guards literally. Lowerer includes magnitude64+acc64+partial64+factor16=208 data bits plus8 control bits before synthesis. The constant `slot*49<<5` address cell is separate from the one dynamic S32 arithmetic multiplier and included in mapped logic. These wording/inventory clarifications do not alter RTL or frozen numeric contract.

Actual command=1'b0 selects RESTORE; command=1'b1 selects STEP. Status:0 success,2 drained abort,3 reject,4 invalid command/context/position/version,6 retry limit,7 unit terminal,8 numeric epoch terminal,9 root/meta invalid,10 coeff invalid,11 illegal stored code,12 format domain. RESTORE metadata acceptance has state_validated=0; next STEP validates complete stored state. Initial imported Y is a zero placeholder, never used by GDN; checkpoint replay instead imports the true previously accepted Y.

## Mixed illegal-domain priority supplement

At the beginning of EVERY attempt, if either head has aligned shift eS-eV>62, return E_FORMAT before evaluating either head's numeric WIDTH/format bound or rescaling. Thus shifts[63,-33] and[-33,63] both reject immediately with zero new retry and zero publication. This order is a new frozen-contract rejection policy, not inherited proof of old68 exception ordering. Input coefficient/state validation still precedes ATTEMPT, as described above. The independent reference now applies the group-wide upper-domain check before per-head conservative fmt. Main RTL already implements this order; no RTL/netlist change.
