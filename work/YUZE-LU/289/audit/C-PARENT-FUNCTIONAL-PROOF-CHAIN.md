# C cached parent functional proof chain (progress record)

Issue289; evidence root `/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit`.

## Proven segments

1. Original delivered source set / original synthesized baseline relation: `C-rtl-input-chain.json` records all source hashes and the one documented R wrapper normalization. Original synth→original CTS independently passes data/state and all clock/reset controls. Hardmacro behavior remains a separately qualified leaf prerequisite.
2. Original loader→parallel selector→exact div3→64-bit distribution→onehot-v2: source inverse bindings and finite-selector/arithmetic SAT obligations are recorded in the independent loader reviews. They are two-state compositional proofs, not a whole-module SAT claim.
3. Onehot-v2→cached loader `a0f71497...`: exact five-substitution inverse binding plus reset base and arbitrary one-step cache-key induction. Every replaced addr use is guarded by valid slot/eligible selection. External cycle behavior is unchanged. Independent endpoint review is recorded in `C-CACHED-LOADER-REVIEW.md`.
4. Actual C-v16 parent synthesis exact replay119769: original config and source, with only the ABC invocation retaining its intermediate files. Both emitted netlists are byte-identical to actual parent artifacts: `1_2_yosys.v` SHA256 `0d68e40dfa436e28c45c127f312e9de9c34a0be662a203049ef47c13aa6e5c12`; `1_synth_lec.v` SHA256 `0d42fdd36b5c0ca3f9fc7682a34465dc6ef60732363be81b7eb465a87d7aa0c4`.
5. Actual parent ABC input→output mapping119786: complete ABC CEC PASS (1210.04 CPU seconds), bound by the exact replay above. Input BLIF `58d071ef04d28fa7fb6d096c3fa2ba231edc51e857566777d7bf93b9688b3073`; output BLIF `78592a357ed57938f8e483827161329b1b036791ad32e2040aa13d8f84d01825`. `C-parent-actual-abc-cec-receipt.json` includes exact command and hashes. This is the actual parent, not the FAST module surrogate.
6. FF mapping stage119789: captured before/after dfflibmap graph independently checks 22119 generic FFs, 31522 new MUXes, 255955 local truth assignments, generic synchronous/asynchronous reset, set, enable priority, clock polarity, true Q/QN semantics, retained initialization and all other cell connectivity. The observation replay's ABC mapping119794 also passes CEC. Because observation changes serialization/mapping ordering, its mapped→actual bridge is a separate pending proof, not byte equality.
7. Actual C-v16 synthesized netlist→C-v18 D-only CTS119792: data/state proof UNSAT, 45172 matched inputs and 50482 matched outputs; clock/reset/enable proof UNSAT, 72024 inputs and 26852 outputs. Both require zero unmatched boundaries. All 21095 actual state elements retain Liberty semantics and initialization (old baseline20599+496 retained cache bits). The 22119 count above belongs to the earlier generic lowering stage before later cleanup of unused padding. Macro instance/type/all-pin signatures are checked; macro internals are separately qualified.

## Remaining boundaries

- The canonical RTL→generic pre-DFF stage is being independently strengthened using EQY. Partial passes or timeouts are not whole-design proofs. Standard Yosys frontend/process/memory/optimization remains the explicitly stated trust boundary until this closes.
- Observer FF snapshots→actual parent mapped netlist119803 runs an explicit unique state-Q alias correspondence; D/CK/reset and every top/macro observation are compared, QN is the exact complement of Q, and zero extra states are allowed. It has no success receipt yet.
- C-v18 CTS is not a routed signoff candidate. Actual final postroute data/state/control proof is required after a routed candidate exists.
- Neither source transformation proof, ABC CEC, nor CTS equivalence establishes setup/hold, electrical limits, geometry, routing DRC, or full macro/block acceptance.

Tool provenance: `C-proof-tool-version-119800.log` records Yosys0.68+post, ABC1.01, exact Yosys/ABC/Kepler binaries and generic FF model hashes; `C-parent-proof-provenance.json` records inputs/config/instrumentation hashes. The original full-width EQY/SAT failures and timeouts remain retained and unclaimed. Redundant alternate119808 was stopped only after actual complete CEC119786 passed; redundant packed control119832 was stopped after119792 control passed.
