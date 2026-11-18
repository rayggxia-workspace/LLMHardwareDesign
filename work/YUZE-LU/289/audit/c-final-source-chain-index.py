from pathlib import Path
import json,hashlib
R=Path('/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117')
def h(p):return hashlib.sha256(p.read_bytes()).hexdigest()
items=[
('original-source-set','audit/C-rtl-input-chain.json','all_original_sources_match_recorded_hashes=true; enumerate original source hashes and documented R wrapper normalization'),
('parallel-selector-inputs','cu/proof-input-index-v2.json','Raw file hashes take precedence over normalized-text hashes; bind selector and div3 logs/models/scripts'),
('parallel-selector-obligations','cu/compositional-obligations.json','77 selector outputs; pure lane functions, all original sequential/continuous outputs equal; requires exact-source manual proof below'),
('parallel-manual-proof','audit/LOADER-INDEPENDENT-REVIEW.md','Exact raw original85c419 to parallel999948 two-state lane/first-eligible/fallback/default/order argument; not whole-module SAT'),
('arithmetic-inverse-binding','audit/LOADER-ARITHMETIC-REVIEW.json','all inverse substitutions exact;2048 div3 inputs/0 failures; unsigned64 modular distribution; candidate2aaa inverse to parallel999948'),
('distribution-bitwidth','cu/distributed-parallel-width-proof.json','Explicit unsigned mod2^64 identity for every operand value'),
('onehot-binding','audit/onehot-v2-binding.json','All77 outputs SATsuccess, lane_eligible=>lane_exam structural bridge, other logic/state exact; source2aaa to020538'),
('onehot-actual-solver','audit/onehot-v2-119681.log','Actual direct SAT SUCCESS'),
('cache-transform-binding','audit/C-cached-loader-proof-binding.json','passed=true, five inverse substitutions,020538 toa0f714;512 auxiliary bits, no observable cycle'),
('cache-induction-actual-solver','audit/cache-key-119717.log','Both reset base and arbitrary one-step bad_induction/bad_reset prove zero'),
('cache-induction-model','audit/cache-key-induction.sv','Proof-only252-bit complete address-configuration key and slot lifetime model'),
('cache-induction-script','audit/cache-key-induction.ys','Actual SAT commands for both induction obligations'),
('cache-invariant-manual-bridge','audit/C-CACHED-LOADER-REVIEW.md','Guarded uses and complete allocation/start/reset/ack/cancel ordering establish pv implies cached_addr=addr(pi) every reset-initialized cycle'),
('generic523','audit/C-v16-genericadder-cached-live-state-generic-views/complete-equivalence-receipt.json','passed=true,EQY_status PASS,all523 partitions; actual canonicalRTLIL to observed actual pre-DFF graph, live-state aliases only'),
('ff-lowering','audit/C-v16-synth-replay-isolated/abc/ff-mapping-receipt.json','passed=true,22119 generic FFs,all255955 local truth assignments and other connectivity; actualFFcount21095 after cleanup'),
('actual-ff-abc-binding','audit/C-v16-synth-replay-isolated/actual-stage-binding-receipt.json','passed=true; isolated observation leaves actual1_synth_lec byteexact0d42;ABC input same and output differs only timestamp comment'),
('actual-abc-cec','audit/C-v16-synth-replay-byte-fixed/cec-receipt.json','passed=true/allgroupspassed; actual retained ABC input/output CEC, not FAST surrogate'),
('actual-final','audit/C43-plan0-final-proof/proof/complete-equivalence-receipt.json','passed=true;actualgold0d42 toactualfinal2b74 with data/state/macro and independent CK/reset/enable;zero unmatched,21095 states'),
('actual-odb-export','audit/C43-plan0-final-proof/actual-export-binding.json','export_verified=true and saved_final_verilog_exact=true; actual final ODB independently exports2b74')]
entries=[]
for stage,name,criterion in items:
    p=R/name;entries.append(dict(stage=stage,path=str(p),sha256=h(p),acceptance_semantics=criterion))
value=dict(index_complete=True,whole_module_RTL_SAT_claimed=False,four_state_X_equivalence_claimed=False,physical_acceptance=False,scope='Minimum primary cached-C source-to-final evidence map. Manual compositional bridges are explicitly retained; no historical timeout is promoted to a pass. Shared-A/AB alternatives are excluded.',trusted_boundary='Yosys frontend/parsing and stated reference normalization; macro internals rely on separately accepted leaf qualifications. Original loader rewrites/cache are source-bound two-state compositional reasoning plus finite SAT/induction obligations.',source_hash_chain=['85c4199804a0564c2651a1aa008f61bb7c7f7c905e3c7311345b55e0d6592f02','999948f63f4038831fc50c18f370968531dc9703754f1df70c25732666321775','2aaa6e239aa20b50c7ab3703531263146527e04046f1bdf8fe439d66e6161a0e','020538508ff7db6461afab28f73726867e5900fde2255a4a311789b105040567','a0f71497ee0c873649c41d64122e2a906775caaed90dc615a686be053625d0f9','0d42fdd36b5c0ca3f9fc7682a34465dc6ef60732363be81b7eb465a87d7aa0c4','2b74fbc9009a57b54f177c89a929a08abfadff7f566ed56928b0ce1441606e77'],entries=entries)
out=R/'audit/C-final-source-proof-chain-index.json';out.write_text(json.dumps(value,indent=2)+'\n');print(out,h(out))
