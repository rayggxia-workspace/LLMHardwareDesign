# R4: optional four-lane stateless relative EXP

Refs Issue247 / PR243. This delivery continues the best R2 route. The R3 finite
M candidate and its negative results remain separate backups. The parent owns
formal integration, source commit, remote execution and reports. Local work
here changes no production file and runs no EDA.

## Interface and compatibility

Only `block_v2_n` and `pu_u_group` add `NEXP_DIRECT_LANES=2`. Values2 and4
are supported; any other static value triggers an initial fatal configuration
error before commands can be accepted. U forwards the selected lane count only
when both NEXP_BATCH and NEXP_DIRECT are nonzero; otherwise it forwards2.
Standalone N also uses only2 when NEXP_DIRECT is zero.

Default2 is required to preserve the exact R2 command/response/data/error/cycle
behavior. Selecting4 affects only stateless native opcode12. All ordinary
op0..11 and their error, statistics, factor, replay and top behavior remain on
the original two-lane schedule. DIRECT0 retains the original four-command R1
batch timing even when the requested lane parameter is4.

Shared router and batch adapter are exact R2 sources, guarded by SHA in the
generator. There is still one N instance. The outer opcode15/magic/count/source
ABI and128bit private-S interfaces do not change. NEXP packed16 count1..8 and
NX32 count1..4 remain separate. Used S32 high halves are deliberately ignored
by the existing signed-low16 contract; unused complete containers must be0.
Native opcode12 still requires count1..8, param0, aux0 and zero unused S16 lanes.

## Limited RTL change

The original raw/gamma/ex pair, square, sum, normalization products and EMIT
loops are unchanged. A static generate branch adds two EXP result registers
and valid bits only for the effective four-lane configuration. It invokes the
same exponential function on elements position+2 and position+3 and updates
only during op12 CALC. Its input is gated outside op12.

ACCUM copies the extra two valid results into the existing128bit result. Its
step is4 only for op12/four-lane; all other operations keep2. The final response
also directly overwrites the current extra lanes, rather than relying on a
same-edge nonblocking result update. EMIT remains entirely unchanged.

Numerics remain exactly the R2 table/interpolation/RNE rule, including32768
for nonnegative values and zero below the table range. No persistent session
state is changed. The original completion hold, ownership, real S writes and
reset paths are retained. Extra payload/valid registers reset with N.

## Costs and evaluation boundary

The source-level extra state is34bits: two16bit results and two validity bits.
This is not an area measurement. Two additional independent exponential lanes
also need lookup/endpoint selection, interpolation arithmetic, RNE and routing.
They add four simultaneous table endpoint queries. A single constant-source
file does not imply a free multiport ROM. Existing statistics/normalization
hardware is not widened or duplicated. Private S remains16KiB.

The actual R2 NX32 accepted-to-next-accepted fee is count1/2=7 cycles and
count3/4=9. A four-lane design predicts count1..4=7 if wrapper costs remain
unchanged, but this must be measured. S32 n8 still needs two real n4 frames;
its predicted fee is14, not the packed-S16 n8 predicted9. No predicted value
may enter the calibration before successful actual measurements.

Only the NExp supplemental service in the frozen old SystemC system may be
replaced, using real compute_s32 measurements and their command/log/source SHA.
All old vector packet/canonical fees, S/cache/DDR,300MHz,2P/1U,17.1GB/s and
input identities remain. S16-input/S32-output prefill remains complete legacy
fallback. Main decode512 has73,728 n4 frames; saving2 cycles each would be
0.49152ms at300MHz, not a measured token/s result.

## Generation, tests and evidence status

`baseline/` freezes the exact R2 N and U sources. `candidates()` reconstructs
the two candidates from fixed SHA and unique anchors. `generate(repo,out)`
defaults to integrated mode: actual production N/U must equal candidates,
shared/adapter must equal R2, and flat delivery must equal reconstruction.
`--prepare` allows exact R2 production files before parent integration. Both
modes only prepare files in a new directory.

The separate test agent owns count1..8 and all65536 values, NX32 aliases,
full persistent-state continuation, errors, output/S ACK backpressure, reset,
and actual compute/full-U timing. Required comparisons include exact R2 vs
new default2; ordinary op0..11 cycles with four lanes; DIRECT0/R1 exact batch;
and rejection of illegal lane parameters. Measurement records must identify
requested/effective lanes so an accidentally instantiated two-lane path cannot
satisfy the new profile. The model agent independently audits source/log/gate
binding and retains complete default/prefill fallback regressions.

Local validation is AST, exact source reconstruction, unchanged-dependency
SHA and source diff review. RTL compile/simulation, new cycle measurements,
SystemC token/s, synthesis,300MHz STA and physical qualification are pending
server receipts. `delivery.json` lists only formal delivery files; temporary
prepare directories are excluded. No R3 M source is changed by this delivery.
