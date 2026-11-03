"""Build W0 research traceability from fixed P1/P2 evidence; does not run RTL."""
import argparse
import hashlib
import json
import re
from pathlib import Path


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', type=Path, required=True)
    ap.add_argument('--output-dir', type=Path, required=True)
    args = ap.parse_args()
    root, out = args.root, args.output_dir
    out.mkdir(parents=True, exist_ok=True)
    base = root / 'work/Melodydt/151'
    paths = ['work/Melodydt/151/phase1-verification-plan.json', 'work/Melodydt/151/phase2-verification-status.json', 'work/Melodydt/151/phase2-rtl-evidence/run-receipt.json', 'work/Melodydt/151/phase2-rtl-evidence/simulation-helper.log', 'work/Melodydt/151/phase2-rtl-evidence/simulation-mst.log', 'docs/PHASE2_MST_VERIFICATION.md', 'docs/PHASE2_MST_IMPLEMENTATION.md', 'work/Melodydt/151/island-sync-plan.json']
    p1 = json.loads((root / paths[0]).read_text(encoding='utf-8'))
    p2 = json.loads((root / paths[1]).read_text(encoding='utf-8'))
    receipt = json.loads((root / paths[2]).read_text(encoding='utf-8'))
    logs = '\n'.join((root / x).read_text(encoding='utf-8') for x in paths[3:5])
    case_ids = re.findall(r'CASE_PASS\s+([HM]\d\d_\w+)', logs)
    assert len(case_ids) == len(set(case_ids)) == 19
    assert set(case_ids) == set(receipt['case_ids']) == set(p2['actual_RTL_case_ids'])
    assert receipt['source_ref'] == '707878621b2add4ed218b8c43df2e95c9a56e2ba'
    descriptions = dict(re.findall(r'^\|\s*([HM]\d\d_\w+)\s*\|\s*([^\n]+?)\s*\|\s*$', (root / paths[5]).read_text(encoding='utf-8'), re.M))
    for c in case_ids:
        assert c in descriptions

    def t(name, work, inputs, expected, layer='RTL_FUNCTION'):
        return {'test_name': name, 'future_work_packages': work.split(','), 'planned_inputs': inputs, 'decidable_expected': expected, 'required_evidence_layer': layer, 'execution_status': 'NOT_EXECUTED_FUTURE_REQUIREMENT'}

    specs = {
      'MST-01': [t('P2_GEOMETRY_S8_DOT_ORACLE', 'W1', 'Direct native/kernel harness: rows1/2/8, tiles1/4, lastK1/8, N1/8, signed S8 deterministic vectors; variable geometry is a later admitted kernel profile, not a new W1-min runtime option.', 'Each requested row/column equals independent unbounded sum(A*B) with factor/left; exact op3 pair order. Current W1-min remains row1/tile1/K8/N8.')],
      'MST-02': [t('P2_SCALE_APPEND_MIXED_WIDTH', 'W1', 'Native harness S8/S16 combinations, factors1/-1/32767/-32768, left0/31, two K segments clear then append; successful and overflow cases separated.', 'Exact segment-scaled mathematical sum for in-range rows; error/fault mask on overflow; no wrapped successful value.'), t('P2_CLEAR_SCALE_PERSISTENCE', 'W1', 'SET_SCALE then op6, reload operands and EXEC; compare with coordinated reset and same reload.', 'op6 preserves scale; reset factor1/left0; operand/result valid flags clear as specified.')],
      'MST-03': [t('P2_MIXED_ROW_COMMIT_PRESERVE', 'W1', 'First seed two merged rows with known results. New wide execution uses a high row that overflows scaled S64 and a small nonzero row that fits; test clear and append, including only final column overflowing.', 'Fault mask identifies failed row; whole failed row stays old including first columns; successful row commits all new/append values. No command-wide rollback and no blind append retry.')],
      'MST-04': [t('P2_OP5_RNE_CARRIER_LAYOUT', 'W1,W3', 'Known positive/negative/tie results; right shifts0/1/31/32/63; S8/S16/S32 modes and clipping boundaries.', 'RNE/tie-to-even and signed clamps match independent integer oracle; four sign-extended S32 carrier slots, saturated OR; logical narrow elements not treated as8S16.'), t('P2_OP12_FINITE_DIAGNOSTIC', 'W1', 'Run2 and8 rows; read currently owned partial slots versus stale row owners, nonzero reserved data and invalid pair.', 'Only valid owner/pair returns sign-extended twoS40 partials before global scale; stale/invalid requests error. Diagnostic is not a restorable result context.')],
      'MST-05': [t('P2_S_WIDE_NARROW_ACK_ARBITRATION', 'W1', 'Real S storage with ordinary read/write and private-wide fires; stall each response; include take plus new request edge.', 'Every accepted ordinary request returns one response, write echo=din; wide fire wins real banks and suppresses ordinary ready that edge; held payload stable.'), t('P5_S_OVERLAP_COPY_NO_WAIT_CYCLE', 'W6', 'Same-S overlapping regions, both copy directions and temporary region, finite output stalls.', 'Matches independent memmove oracle; no held native response waiting for another S access; all ACKs drained and resource wait condition closes.', 'RTL_FUNCTION_PLUS_LIVENESS')],
      'MST-06': [t('P2_LOADER_GEOMETRY_HALF_AND_RANGE', 'W1', 'rows1/8 tiles1/4, A/B S8/S16, both banks; bases at aligned end1024 and unaligned/overflow; S16 B half0 thenhalf1.', 'Exact rows*tiles A beats and tiles*(Bwide?2:1) B beats/data; invalid descriptor yields held done_error without compute; legal boundary fits.'), t('P2_LOADER_INDEPENDENT_STALL_REUSE', 'W1,W6', 'Independent finite A/B sink stalls and done_take stall; reuse_b with matching or mismatched owner-side weight version; both banks.', 'No done until all actual A/B obligations retire; no new load on same edge old done is taken; reused B skips reads but owner rejects wrong version before publication. No fictitious native identity error.')],
      'MST-07': [t('P2_NATIVE_VALID_HELD_WHILE_READY_LOW', 'W1', 'Present stable second native command while previous response/state makes cmd_ready0; similarly loader busy/done pending; not merely gating launch before valid.', 'Native valid and all fields remain stable until true handshake; exactly one accepted command; no response loss or duplicate.'), t('P2_RANDOM_BOUNDED_STALLS', 'W1,W2,W6', 'Recorded seeds, declared finite stall bound, independent request/response/A/B/done/T consumer and completion stalls.', 'Per-job accepted/retired counters conserve; payload stable during stalls; drain completes under stated finite/fair assumptions, timeout recorded as failure not proof.', 'RTL_FUNCTION_PLUS_LIVENESS')],
      'MST-08': [t('P2_RESET_STATE_MATRIX', 'W1', 'Reset/abort at queued request, accepted S write, loader pending/A/B, EXEC, M response, T FILL/SEALED/READ/RELEASE and pending DONE.', 'Coordinated reset clears valids/control, RAM not rolled back; abort after accepted run has one retained error completion; hard reset supplies no invented completion; old prefix not retracted.'), t('P2_NO_RESET_DRAIN_CANCEL', 'W1,W6', 'Future explicit drain-stop contract only; cancel before valid, while valid presented, loader accepted, M executing and T pre/postcommit.', 'No illegal valid withdrawal; drain every accepted native obligation; T revoke only legal phases else drain/release; do not call coordinated reset a no-reset cancel. This is outside W1-min until separately implemented.', 'RTL_FUNCTION_PLUS_LIVENESS')],
      'MST-09': [t('P2_T_LENGTH_STARTUP_RELEASE', 'W1,W2,W6', 'Real T words1/2/4/383/384, contiguous writes, read stalls on first/middle/last word.', 'SEALED only after exact write count; commit read startup respected; steady reads correct; final take does not free before RELEASE; data/index/last stable. No full-job atomicity from fragment end.')],
      'MST-10': [t('P2_T_ILLEGAL_AND_REVOKE_MATRIX', 'W1,W6', 'BEGIN0/385/1023; wrong/duplicate write index; early BEGIN/COMMIT/RELEASE; revoke in FILL/SEALED and after commit; simultaneous revoke/write/commit.', 'Only native diagnosed size/index conditions set sticky protocol_error until reset; other premature controls may not handshake without error; revoke priority/native windows respected; no invented commit_error.')],
      'MST-11': [t('P2_BANK_FORMAT_SCALE_REUSE', 'W1,W3', 'Back-to-back declared jobs across bank0/1, S8/S16 formats, scale changes/op6/op11 and selected-bank lock/opposite-bank load.', 'No old valid/result/response finishes new job; active bank locks correct, opposite-bank load only native-allowed; M scale and single merged context lifetime tracked.')],
      'CTRL-01': [t('W1_FIXED_PROGRAM_CAPTURE_WAIT', 'W1', 'Variable tensor frames under one permanent program; incomplete input and stalled S response while local SERVICE/WAIT executes.', 'Native work only after full admitted inputs/required fields captured; SERVICE acceptance differs from completion; helper progresses while parent waits. Old64bit/template/tenbank representation is pending design disposition, not mandatory W1-min hardware.')],
      'CTRL-02': [t('W1_INPUT_LIFETIME_SINGLE_FOREGROUND', 'W1', 'Partial frame then abort/reset, early/busy start, completion hold, two successive different frames.', 'Only complete current frame can start; no stale flags/data or duplicate done; RUN and retained completion occupy the one slot.'), t('W2_CONTROL_LIFETIME_TAG_OR_ELISION_PROOF', 'W2,W6', 'Future chosen transport with stale/invalid/control-word and exhaustion cases; or explicit serial no-tag lifetime proof.', 'If tags/credits are implemented, reject stale/partial packets and stop/drain instead of wrap. If elided, prove ordered single-lifetime/coordinated reset equivalent safety; do not silently mark old epoch gate passed.', 'RTL_FUNCTION_PLUS_FORMAL_OR_REVIEW')]
    }
    by_status = {r['id']: r for r in p2['requirements']}
    future = {'BASE-01':['W0'], 'BASE-02':['W11'], 'EG-01':['W3'], 'EG-02':['W3'], 'EG-03':['W3','W5'], 'N-01':['W4'], 'N-02':['W4'], 'N-03':['W4','W6'], 'TOPO-01':['W6'], 'TOPO-02':['W6'], 'TOPO-03':['W6'], 'TOPO-04':['W6'], 'R-01':['W8'], 'R-02':['W8'], 'R-03':['W8'], 'R-04':['W8','W10'], 'NUM-01':['W7'], 'SYS-01':['W9','W11'], 'MEM-01':['W2','W10'], 'PHY-01':['W11']}
    requirements = []
    gates = []
    for r in p1['requirements']:
        s = by_status[r['id']]
        item = {'id':r['id'], 'original_phase':r['execution_phase'], 'original_check':r['check'], 'observed_P2_status':s['status'], 'actual_case_ids':s['cases'], 'remaining_verbatim':s['remaining'], 'future_work_packages':sorted(set(w for test in specs.get(r['id'], []) for w in test['future_work_packages'])) if r['id'] in specs else future[r['id']], 'whole_requirement_accepted_by_W0':False}
        requirements.append(item)
        if r['execution_phase'] == 'P2':
            tests = specs[r['id']]
            gates.append(dict(item, gate_id='G-'+r['id'], remaining_tests=tests, gate_status='OPEN_NOT_EXECUTED', acceptance_basis='current fixed source and explicit admitted workload; independent reference/RTL evidence and review required'))
    assert len(gates) == 13
    vectors = []
    def vector(name, a, cols):
        result = [sum(a[k]*cols[n][k] for k in range(8)) for n in range(8)]
        pack = lambda vals,bits: sum((v & ((1<<bits)-1)) << (bits*i) for i,v in enumerate(vals))
        words = [pack(a,8),0,0,0]
        b = pack([v for col in cols for v in col],8)
        words += [(b>>(128*i)) & ((1<<128)-1) for i in range(4)]
        vectors.append({'id':name,'A':a,'B_columns':cols,'ingress_words_hex':['%032x'%v for v in words],'expected_S64':result,'expected_output128_hex':['%032x'%pack(result[i:i+2],64) for i in range(0,8,2)],'RTL_execution_status':'NOT_EXECUTED_W1_FUTURE_VECTOR'})
    vector('W1_DOT8_LITERAL_P2', [1,-2,3,-4,5,-6,7,-8], [[n+1]*8 for n in range(8)])
    vector('W1_DOT8_ZERO', [0]*8, [[127]*8 for _ in range(8)])
    vector('W1_DOT8_MAX_POSITIVE', [-128]*8, [[-128]*8 for _ in range(8)])
    vector('W1_DOT8_MIN_NEGATIVE', [-128]*8, [[127]*8 for _ in range(8)])
    vector('W1_DOT8_DISTINCT_COLUMNS', [-128,127,-1,0,1,-64,64,2], [[(n*23+k*17)%256-128 for k in range(8)] for n in range(8)])
    w1 = {
      'status':'PROPOSED_MINIMAL_W1_SLICE_PENDING_REVIEW_NOT_ALL_W1_FREEZE',
      'profile':'W1_FIXED_DOT8_VARIABLE_TENSOR', 'program_loading':False, 'runtime_shape_address_opcode_scale_configuration':False,
      'geometry':{'A_bits':8,'B_bits':8,'rows':1,'tiles':1,'K':8,'N':8,'bank':0,'factor':1,'left_shift':0,'EXEC_op':10,'EXEC_index':0,'EXEC_data_hex':'0x9884'},
      'ingress':{'ordered_beats':8,'beat_bits':128,'transfer_bytes':128,'effective_A_bytes':8,'effective_B_bytes':64,'effective_payload_bytes':72,'padding_written_zero_bytes':56,'runtime_address_or_program_fields':False,'one_accepted_ingress_beat_in_flight':True,'suggested_signals':['in_valid','in_ready','in_data[127:0]'],'beat_index':'implicit0..7; no runtime address/opcode'},
      'address_map':{'beats0_3':'S448..451 A reserved4words','beats4_7':'S452..455 n-major B','results':'S456..459 four S64 pairs'},
      'padding':'Hardware canonicalizes beat0 high64 and beats1..3 to zero and actually writes/ACKs all4 A words; source nonzero padding ignored, never stale RAM.',
      'input_complete':'input_stored level/marker set only after8 ingress handshakes and8 actual ordinary S write ACKs with no pending input transaction; remains bound to this frame until done consumed/reset/abort.',
      'start':'start_ready only when current input_stored and native lifetimes safe; early pulse not queued; held valid may accept once ready. No input overwriting during RUN or pending DONE.',
      'literal_init_must_change':'Remove/replace P2 literal S_INIT write service with INPUT_STORED verification; it must not overwrite ingress data. Permanent program remains fixed; this is a source-design change for future RTL, not bootload.',
      'S_owner':'One ordinary helper owns ingress writes and all RUN result writes/reads; no direct second writer.',
      'M_rule':'CLEAR/SET_SCALE ACK then loader complete then EXEC status inspected; only op3 payloads are results, 4 sequential pairs saved to S with ACK.',
      'T_rule':'BEGIN4 owner0 generation1,4 ordered result words,COMMIT,real consumer takes,index0..3,last only3,then RELEASE before task success.',
      'output_completion':'Preserve P2 data/index/last under backpressure; stable done_valid/done_error until consumed; input_stored not compute done, last not release/job done.',
      'counts':{'ingress_phase_S_writes_ACKs':8,'RUN_S_result_writes_ACKs':4,'RUN_S_reads_ACKs':4,'RUN_S_transactions':8,'frame_plus_RUN_S_transactions':16,'RUN_M_commands_responses':7,'T_output_words':4},
      'reset_abort':{'hard_reset':'invalidate frame/counts/lifetimes/completion coherently, not RAM rollback; no invented done for interrupted accepted run','abort_before_start':'discard incomplete/complete-not-started frame and clear input_stored; no task completion because no start accepted','abort_RUN':'coordinated leaf/helper reset plus one retained error completion, already consumed external prefix not retracted','abort_existing_DONE':'keep existing done result; ready may consume it once; no duplicate','reuse':'after done consumed accept a wholly new8beat frame; never reuse old complete marker'},
      'unknown_or_excluded':['variable geometry/addresses/formats/scales','no-reset drain cancel','N/E/G/R integration','generic packet/handle/epoch ABI','multi-job queue','MEM/NUM','general fragments/forkjoin','global rollback/atomicity','complete F/A/D/H/X','PPA'],
      'oracle':{'formula':'dot[n]=sum_k signedS8(A[k])*signedS8(B[8*n+k]); raw exact integer, no rounding','range':[-130048,131072],'pair_order':'low64=dot[2p],high64=dot[2p+1]','future_vectors':vectors,'proof_boundary':'five Python-generated expected vectors are future test data, not RTL evidence'},
      'required_future_tests':[
        {'name':'W1_INPUT8_STORED_BEFORE_START','expected':'partial frame/ACK stall cannot assert input_stored/start_ready or issue loader/EXEC'},
        {'name':'W1_VARIABLE_DOT8_ORACLE','expected':'all five vectors exact pair order, including nonliteral and extreme data; no S_INIT clobber'},
        {'name':'W1_CANONICAL_PADDING_AND_STALE_RAM','expected':'preseed nonzero S padding then input; all56 padding bytes actually zero after ACK; reset not assumed to clear payload'},
        {'name':'W1_TWO_DIFFERENT_FRAMES_NO_STALE_COMPLETE','expected':'second start blocked until its own8 writes ACK; different output, no prior response/data leakage'},
        {'name':'W1_INPUT_OUTPUT_DONE_BACKPRESSURE','expected':'handshake fields and outputs stable, exact accepted/ACK/output counts; frame+RUN16 versus RUN8 S transactions distinguished'},
        {'name':'W1_RESET_ABORT_FRAME_RUN_DONE','expected':'before/after input S accept, duringRUN and pendingDONE follow stated lifecycle and recover on a fresh complete frame'}
      ]
    }
    output = {
      'schema_version':1,'issue':151,'PR':152,'input_parent_ref':'bd7cb2f','input_parent_full_commit':'bd7cb2f3060c61e5d28a2ece0653dd9336a024af','leaf_source_commit':receipt['source_ref'],
      'upstream_observation_reported_by_root':{'PR144_head':'d1f26884b13f8d0466bbaefe2fc6322a14c66df9','core_paths_equal_to_selected707':14,'core_paths_compared':14,'claim_boundary':'root source observation; no whole branch upgrade or new physical qualification'},
      'status':'W0_MAINLINE1_CONTRACT_EVIDENCE_DELIVERY_PENDING_REVIEW','this_delivery_new_RTL_or_simulation':False,
      'source_index':[{'path':x,'sha256':sha(root/x)} for x in paths],
      'evidence_levels':{'MANAGEMENT':'structure only','SOURCE_STATIC':'source/interface/count/lint only','PYTHON_ORACLE':'bounded mathematical expected values, not DUT protocol evidence','RTL_FUNCTION':'actual fixed-version DUT/TB logs and observed scope','FORMAL_LIVENESS':'separate proof under explicit environment assumptions','MODEL_QUALITY':'full accepted integer/model workload and quality','PHYSICAL':'real netlist/LEC/STA/PG/DRC and route evidence'},
      'actual_P2':{'case_count':19,'cases':[{'id':c,'observed_check':descriptions[c],'evidence_layer':'RTL_FUNCTION','origin':'phase2 historical fixed run; not rerun by W0'} for c in case_ids],'run_exit_codes':[{'label':r['label'],'exit_code':r['exit_code']} for r in receipt['runs']],'P2_fully_accepted':False,'normal_batch':'16S requests/ACKs,7M commands/responses,A/B each1,loaderdone1,T4word+release','abort_accounting':'global Sreq113/Sack112 differs by one intentionally abandoned ACK, not normal-job loss','other_macros':'N/E/G/R compile only; no new functional qualification'},
      'all_P1_requirement_trace':requirements,'P2_remaining_gates':gates,
      'design_dispositions_pending_review':[
        {'ids':['CTRL-01'],'old_representation':'64bit instruction/header,4or8 template words,ten64B banks','preserved_obligation':'complete parameter capture before native execution, finite storage and SERVICE versus completion','W1_min_requires_old_representation':False,'rule':'Do not silently delete the old requirement or mark it passed; review whether it remains optional comparison or is formally restated for fixed-program shell.'},
        {'ids':['CTRL-02'],'old_representation':'epoch/credit/sequence-tag transport','preserved_obligation':'no stale or partial command/result can complete a new lifetime; bounded completion reservation','W1_min_requires_generic_tags':False,'rule':'One strictly serialized frame/run plus coordinated reset may elide generic tags only with explicit lifetime proof; distributed transport exhaustion needs its own later contract/test.'}
      ],
      'W0_exit_checklist':[
        {'id':'W0-X1','item':'fixed source/parent/provenance and P1 historical versus P2 current source are explicit','status':'prepared_pending_review'},
        {'id':'W0-X2','item':'all33 P1 IDs retained, all13 P2 IDs have open remaining gates and future test expectations','status':'prepared_pending_review'},
        {'id':'W0-X3','item':'19 unique historical CASE_PASS agree across receipt/status/raw logs and bounded descriptions','status':'prepared_pending_review'},
        {'id':'W0-X4','item':'static/Python/RTL/liveness/model/physical evidence levels do not substitute','status':'prepared_pending_review'},
        {'id':'W0-X5','item':'old generic CTRL representation disposition explicitly needs review; no silent acceptance-rule deletion','status':'prepared_pending_review'},
        {'id':'W0-X6','item':'minimal W1 fixed-shape/variable-data input integrity and lifecycle contract is implementable and gaps explicit','status':'prepared_pending_review'},
        {'id':'W0-X7','item':'prepared for root integration; actual root validation/delivery is recorded in w0-checks and PR receipts, external independent PR review remains pending unless separately evidenced','status':'prepared_for_root_integration_independent_PR_review_pending'},
        {'id':'W0-X8','item':'W0 acceptance does not accept P2 phase/full profiles or start W1 RTL','status':'explicit_boundary_pending_review'}
      ],
      'W1_minimal_contract':w1,
      'completion_claims':{'W0_artifacts_prepared':True,'W0_independently_accepted':False,'P2_fully_accepted':False,'W1_implemented':False,'full_profiles_implemented':False,'physical_qualified':False},
      'validation':'static builder cross-check only; independent checker and root review required; no RTL/SystemC/server/EDA/ref-project action'
    }
    (out/'w0-evidence-gates.json').write_bytes((json.dumps(output,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))
    print('Prepared33 requirement traces,13 open P2 gates,19 historical cases,{} future P2 tests,5 W1 oracle vectors'.format(sum(len(g['remaining_tests']) for g in gates)))


if __name__ == '__main__':
    main()
