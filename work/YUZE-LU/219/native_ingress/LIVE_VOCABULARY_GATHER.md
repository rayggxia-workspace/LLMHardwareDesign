# Block V2 vocabulary-to-Gather boundary

This check connects the vocabulary producer to the next decode Gather for one boundary of the sealed Qwen2.5-3B request. It uses decode step 126 as producer and step 127 as consumer. The input is the captured final hidden state for step 126. The runtime computes the final RMS, reads the real lm_head weights, produces every S32 logit, and reduces the logits in the terminal. The logits archive supplies assertions. The next Gather's input comes from the terminal's token handshake with the native index writer.

The U0 side runs the linked native MC/LC program and four-flit switch for step 127, checks index generation 127, and waits for the index commit at U0 SRAM before fetching the selected row. The row comes from the real DDR embedding image. The reference row supplies assertions. The boundary fixture has distinct P and U control instances and shares the typed DDR fabric. It exercises the U stored-link handshake directly in the fixture. It does not instantiate the physically placed C0 producer. This is a component-boundary replay, not a new PR #260 speed result.

The original step 126 descriptors are sealed by job 111141. The replay checks the original and fixture CRCs and compares the bytes outside the previously relocated source identity (position 184636 to 1), DDR weight base (360976384 to 4655939584), and CRC. It also verifies that the U0 local PM and mother image match their sealed artifacts.

## Remote result

Slurm 111164 completed with exit code 0. Final RMS made 256 DDR reads and produced 512 S write acknowledgements. The projection issued 1,187 tiles and recomputed 151,936 S32 logits. All 37,984 output words matched the sealed reference. The terminal retired token 81917 with S32 logit 1630078.

| Boundary event | Fixture cycle |
| --- | ---: |
| MC sends Gather CALL | 12,849,966 |
| U0 confirms index in SRAM | 12,850,039 |
| U0 confirms final embedding word | 12,852,544 |
| MC accepts final response flit | 12,852,562 |

Gather issued 128 DDR reads and committed 512 16-byte words. The combined fixture accepted, returned and retired 5,472,454 DDR reads. These cycle counts describe the fixture. The full P512/D128 trace requires a physically bound provider, complete live KV and observed retirements for all 128 generated tokens.

- Runtime proof log SHA-256 `38841b35cd6810be560bdfb5aeb779253c3efa82b7b198efadedf65d7a4441f8`
- Full logits SHA-256 `6047f86722cb9a1678ab311fcad05fff54fca36a4cad89dc2b00db5914b75c2a`
- Runtime source bindings SHA-256 `da41b3090203731bf5eea084357ad1618bb02039beb6a969f7f1f6abc53542e2`

## Same-plan placement handoff

Job 111175 enumerated the nine signals (207 bits) in the P0 auxiliary read interface from the placed DEF. All 207 bits have named DEF terminals. There are 79 M10 landings. The 128 bits of `aux_rsp_data` have no M10 landing. The vocabulary terminal is currently unbound on this placement. The C0-to-U0 transport already has candidate endpoint geometry for 153 members, and the U0-to-DMA3 interface adds 650. The layout has no bound producer at C0 for this retirement path.

`bind_retirement_placement.py` checks the identities of the sealed request, base, sidecars, P0 endpoint inventory, and Algo2 endpoint requirements. For each of the 127 feedback edges it compares the producer page and proof, U0 image SHA, dispatch and commit prerequisites, and users of both route demands. The resulting handoff remains in `blocked_on_placed_token_provider`, including when supplied with the boundary replay. Do not release the product route using that replay as placement evidence.

The design candidate is to place the terminal next to the P0 SRAM and export a tagged token through an explicitly registered transport. This avoids making a new 128-bit top-level logits connection a prerequisite for the feedback path. It still requires the release/ack protocol, an actual driver bound to the selected path, and a new geometry receipt. The physical task may compare that candidate with a separately placed terminal and explicit SRAM response access.

- Base SHA-256 `5e29e7ad71e1be84b5b8fd8b5a327d4672bef511af8b567a7c08d6f36ee0620b`
- Sealed handoff digest `8173669ef8387078a99fca1394004346c8b6e6386b187d5e331558d9e1679951`
- P0 pin evidence SHA-256 `abfd5ea748d77c224cbe53dc8f4c4b66a4d3278694136f17295449696ddd5910`

The handoff reproduced on the server. Three negative checks rejected a changed base identity, an Algo2 consumer bound to another image, and a route requirement emitted from another sidecar.

## Reproduction

Use the remote run directory with the frozen prerequisite locations in the two Slurm scripts. Let `G` be the framework directory containing `route_contract.py`, `D` its decode-feedback directory, and `A` the directory from vocabulary-link job 111141.

```bash
sbatch -J yzl-live-vocab-gather --time=0 -c 8 run_live_vocab_gather.sbatch "$PWD" "$G" "$D" "$A/retirement-link.json"
sbatch -J yzl-vocab-aux --time=0 -c 1 inventory_vocab_aux.sbatch "$PWD" "$G" "$D" "$A/retirement-link.json"
PYTHONPATH="$G" python -B bind_retirement_placement.py "$A/retirement-link.json" \
  "$D/mother-ingress-sNMsK9/link-110415/request-link.json" \
  "$D/request-110369/local-sidecars.json" "$D/geometry-110384/geometry-requirements.json" \
  aux-111175.json feedback-placement.json
```

The reproduction retains weights, model captures, and replay outputs on the server.
