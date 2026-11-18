# G/S selected-port X8 ECO

Owner: YUZE-LU. Remote outputs:
`/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/gs/`.
This directory is implementation/verification infrastructure, not an acceptance receipt.

## Frozen sources and scope

- G: `LLMHardwareDesign/issue-201-compact-ge/2ba89c0bd/release/g/6_final.*` (220 um square). Change only 32 `out_data` and `out_valid` final drivers, actually BUF_X4 → BUF_X8.
- S: `LLMHardwareDesign/issue-200-compact-local-s/run08-base0/results/0/flow/results/nangate45/local_s_base/base/6_final.*`. Change `req_ready` final BUF_X4 → BUF_X8.
- G `out_error` and `out_saturated` are not selected. `out_ready` is an input. No P ports.
- Both candidates retain every BPin rectangle and die boundary; final real endpoint drivers are checked after repair. S uses its original 1068 SRAM landing patches and M10 via constraints.
- C-parent integration uses the overlay C variant only with explicit re-binding to `services.engine[1].genblk1.activate.leaf`. The B original segment C used `local_group.services.engine[1].genblk1.activate.leaf`; the 34 selected port geometries match, but that does not make parent versions interchangeable without recorded binding.
- F parent is `main-blockv2-f300-side-01`, original S at `local_group.services.store.leaf`. Preserve its functional connections. Synthetic B fixture connections are not parent functional proof.

## Attempts

- `probe.sh`: read-only inventory. Job 119527 confirmed selected 34 drivers are X4 and BUF_X8 is available.
- G pilot job 119529: failed unsupported `resize_cell`; fixed to source project's proven `replace_cell` API.
- G pilot 119530/v2: old detailed route became disconnected after resized-cell placement. Cancelled with logs retained.
- `eco.tcl` v3, job 119533: remove obsolete signal dbWires while retaining PG special wires; global/detail routing; preserve original M10 route args; extract new RC. G/S × minimal, hold03, hold08. Original SDC unchanged. Hold margin differences are implementation repair targets only.
- `eco-local-v4.tcl` is an unexecuted fallback retaining routes on nets whose endpoint/master/placement signatures remain unchanged. It must receive fresh independent validation if used.

## Verification gates

1. `qualify-v2.py` / `run-qualify-v2.sh`: private ORFS GDS streamout, unmodified full FreePDK45 deck with expected SHA, independent OpenROAD whole-area DRC, regenerated Liberty/LEF. The first `qualify.py` attempt lacked ORFS log directories and failed streamout; preserve `qualification/` and use `qualification-v2/`.
2. `sta-counts-v2.tcl`: independent extracted setup/hold/cap/slew/fanout counts, placement, PG, antenna. Requires `GS_ROLE` and `GS_CANDIDATE` environment variables.
3. `formal.py`: accepted exact leaf netlist vs candidate Kepler combinational/state-boundary correspondence. S cuts every pin of all four unchanged SRAM instances. Exported graph readback is checked. This alone is not reset/initial-state/sequential regression proof.
4. `state-preservation.py`: state instances/types/parameters, clock/reset/enable controls, and explicit initial state attributes unchanged. Combine with state-boundary LEC to support this buffer-only ECO's functional preservation.
5. `f-parent.py`: unchanged F300 parent `.v/.sdc/.odb/.def/.spef` hashes, new S LIB/LEF/GDS, original F timing/electrical/PG checks, antenna, whole-area native DRC and full GDS DRC. Requires successful leaf physical/formal/state-preservation receipts. C update is coordinated with the CU agent.

S v3 candidate-only extracted slack results (ns):

| Mode | Setup | Hold |
|---|---:|---:|
| minimal | 0.151710644 | 0.027303772 |
| hold03 | 0.175611302 | 0.031941757 |
| hold08 | 0.174261272 | 0.058656693 |

All three S candidates have passed state-boundary LEC and preservation checks for 265 state instances. Independent setup/hold/capacitance/slew/fanout violation counts are all zero; VDD/VSS connectivity and antenna checks pass. Small receipts are in `evidence/`. Full GDS DRC and parent gates remain separate receipts; no overall acceptance is claimed here.
