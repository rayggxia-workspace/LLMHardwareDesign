"""Lint Issue151's proposed design contracts and sources, not a hardware model."""
import argparse
import copy
from datetime import datetime, timezone, timedelta
import hashlib
import json
from pathlib import Path
import re
import sys
from urllib.parse import unquote, urlsplit

SCHEMES = {'attention','extra_norm','gated_ffn','gdn','ssm','moe'}
OWNERS = {'M.cmd':'M_CTRL','N.cmd':'N_CTRL','E.cmd':'E_CTRL','G.input':'G_CTRL',
          'R.cmd':'R_CTRL','S.req':'S_CTRL','S.load':'S_CTRL','T.write':'T_CTRL',
          'T.lifecycle':'T_CTRL','EXT.req':'MEM_CTRL','NUM.cmd':'NUM_CTRL',
          'STATE.root':'STATE_VERSION_CTRL','M.rsp_accept':'M_CTRL',
          'M.A_payload':'S_LOADER','M.B_payload':'S_LOADER'}
DOCS = ['docs/SIX_CONNECTION_SYSTEM_DESIGN.md','docs/SIX_CONNECTION_CONTROL_SPEC.md',
        'docs/SIX_CONNECTION_TEMPLATE_SPEC.md',
        'docs/decisions/0006-fixed-product-hierarchical-control-candidate.md',
        'docs/SIX_CONNECTION_SCHEMES_STUDY.md','docs/SIX_CONNECTION_BRIDGE_AUDIT.md',
        'docs/SIX_CONNECTION_COORDINATION_CANDIDATE.md',
        'docs/handoffs/2026-10-31-issue-151-six-connections.md',
        'progress/Melodydt/STATUS.md','work/Melodydt/151/README.md']
AUX = 'work/Melodydt/151/'
LINK = re.compile(r'(?<!!)\[[^\]]*\]\(([^\s)]+)\)')

def validate(c):
    """Validate declared static invariants; no RTL behavior is inferred."""
    errors=[]
    def need(ok, code):
        if not ok:
            errors.append(code)
    need(c.get('status')=='proposed' and c.get('hardware_verified') is False,
         'unsupported_hardware_claim')
    need(c.get('complete_model_programs_compiled') is False,'unproven_complete_products')
    b=c.get('binding',{})
    need(b.get('model_selected_at')=='M11_M12_customization' and
         b.get('runtime_arbitrary_graph_change') is False,'binding_scope')
    need(b.get('full_programs_required_before_base_freeze') is True,'late_fixed_ROM_compile')
    ctrls=c.get('controllers',[])
    need(len(set(ctrls))==len(ctrls),'duplicate_controller')
    need(c.get('native_owners')==OWNERS,'native_owner_conflict_or_missing')
    actors=c.get('existing_actors',{})
    need(all(owner in ctrls or owner in actors for owner in OWNERS.values()),'owner_controller_missing')
    need(actors.get('S_LOADER',{}).get('controlled_by')=='S_CTRL','loader_owner')
    types=c.get('types',{})
    adapters={a['id']:a for a in c.get('adapters',[])}
    need(len(adapters)==len(c.get('adapters',[])),'duplicate_adapter')
    for edge in c.get('legal_edge_examples',[]):
        src,dst=edge.get('src'),edge.get('dst')
        need(src in types and dst in types,'unknown_edge_type')
        need(edge.get('family') in c.get('families',[]),'unknown_edge_family')
        a=edge.get('adapter')
        if a is None:
            need(src==dst,'implicit_numeric_conversion')
        else:
            need(a in adapters and adapters[a]['src']==src and adapters[a]['dst']==dst,
                 'adapter_type_mismatch')
    ts=c.get('templates',[])
    need({t['id'] for t in ts}==SCHEMES and len(ts)==6,'six_template_coverage')
    for t in ts:
        need(t.get('status')=='candidate_not_implemented','unproven_template_claim')
        rows=t.get('stages',[])
        by_id={s['id']:s for s in rows}
        need(bool(rows) and len(by_id)==len(rows),'duplicate_or_empty_stage:'+t['id'])
        for s in rows:
            need(s['controller'] in ctrls,'unknown_stage_controller:'+t['id'])
            need(s['completion'] in {'data_ready','publish_done','release_done','compute_done'},
                 'unknown_completion:'+t['id'])
            need(all(d in by_id for d in s['after']),'dangling_dependency:'+t['id'])
        visiting=set()
        visited=set()
        def visit(x):
            if x in visiting:
                return False
            if x in visited or x not in by_id:
                return True
            visiting.add(x)
            ok=all(visit(d) for d in by_id[x]['after'])
            visiting.remove(x)
            visited.add(x)
            return ok
        acyclic=all(visit(x) for x in by_id)
        need(acyclic,'dependency_cycle:'+t['id'])
        def precedes(a,z):
            if not acyclic or a not in by_id or z not in by_id:
                return False
            pending=list(by_id[z]['after'])
            seen=set()
            while pending:
                n=pending.pop()
                if n==a:
                    return True
                if n in seen or n not in by_id:
                    continue
                seen.add(n)
                pending.extend(by_id[n]['after'])
            return False
        req=set(t.get('required_services',[]))
        need(req<=set(c.get('services',{})),'undefined_service:'+t['id'])
        if t['id'] in {'gdn','ssm'}:
            need({'NUM_COEFF','EXTERNAL_MEMORY','STATE_VERSIONING'}<=req,
                 'missing_full_R_service:'+t['id'])
            need(t.get('state_mode')=='external_versioned_tile_loop','missing_R_tile_boundary')
            need((t.get('iteration_dependency') or {}).get('initial_version_required') is True,
                 'uninitialized_recurrence')
        if t['id']=='gdn':
            need(precedes('head_norm_full','z_gate'),'GDN_norm_gate_order')
        if t['id']=='ssm':
            need(precedes('state_decay_preload','conv_tiles_saved'),'SSM_preload_order')
            need(precedes('z_gate','channel_norm_full'),'SSM_gate_norm_order')
        if t['id']=='gated_ffn':
            need(precedes('gate_pack','gated_mid') and precedes('up_pack','gated_mid'),
                 'FFN_join_dependencies')
            need(precedes('mid_materialized','down_all_k'),'single_M_materialization')
        if t['id']=='moe':
            need({'NUM_WACC','GATHER_SCORE'}<=req,'missing_MoE_service')
            need(precedes('topk_ids','selected_logits_gather') and
                 precedes('selected_logits_gather','route_softmax'),'MoE_ID_score_order')
    cap=c.get('capacities',{})
    need(cap.get('transport_bytes')==16 and cap.get('S_bytes')==16384 and
         cap.get('T_words')==384 and cap.get('R_value_lanes')==8,'native_capacity_changed')
    ex=c.get('examples',{})
    f=ex.get('ffn8_s8',{})
    occupied=set()
    for r in f.get('S_regions',[]):
        cells=set(range(r['base_word'],r['base_word']+r['words']))
        need(r['words']>0 and r['base_word']>=0,'invalid_S_region')
        need(not occupied.intersection(cells),'overlapping_S_regions')
        occupied.update(cells)
    need(bool(occupied) and (max(occupied)+1)*16==f.get('S_reserved_bytes')==400,
         'FFN_reservation_span')
    need(len(occupied)*16<=cap.get('S_bytes',0),'S_capacity_exceeded')
    need(f.get('includes_input_norm') is False,'FFN_example_scope')
    s=ex.get('softmax257',{})
    n=s.get('elements',0)
    words=(n*2+15)//16
    need(n==257 and s.get('score_words')==words and s.get('exp_words')==words,
         'softmax_replay_capacity')
    need(s.get('T_words')==words and s['T_words']<=cap.get('T_words',0),'T_capacity_exceeded')
    need(s.get('T_elements_last_word')==n%8==1,'tail_count')
    long=ex.get('ffn11008',{})
    need(long.get('mid_bytes')==11008*2 and long.get('gate_up_bytes')==11008*4 and
         long.get('requires_external_memory') is True,'large_FFN_memory')
    falcon=ex.get('falcon4096',{})
    need(falcon.get('output_bytes')==8192 and falcon.get('single_T_batch_fits') is False,
         'long_output_publication')
    w=c.get('wacc',{})
    bound=w.get('max_experts',0)*(2**(w.get('input_bits',1)-1))*w.get('probability_max',0)
    need(bound==w.get('acc_abs_bound')==2**48,'wacc_bound')
    need(bound<2**(w.get('accumulator_bits',1)-1),'wacc_overflow')
    need(bound*w.get('gain_numerator',0)<2**w.get('acc_times_gain_lt_power',0),
         'wacc_gain_overflow')
    need(w.get('extra_shift')=='expert_frac-output_frac' and
         w.get('numeric_quality_accepted') is False,'wacc_scale_or_quality')
    need(w.get('shift_min')==0 and w.get('shift_max')==63 and
         w.get('negative_shift')=='reject_until_range_proven','unproven_left_shift')
    return sorted(set(errors))

def negative_cases(base):
    cases=[]
    def add(name, edit, expected):
        c=copy.deepcopy(base)
        edit(c)
        errors=validate(c)
        cases.append({'name':name,'rejected':any(expected in e for e in errors),
                      'expected_error':expected})
    add('second_S_owner',lambda c:c['native_owners'].update({'S.req':'M_CTRL'}),'native_owner')
    add('implicit_EXP_to_signed_probability',lambda c:c['legal_edge_examples'].append(
        {'src':'U16_Q15_EXP','dst':'S16_Q14_NONNEG','family':'load_m','adapter':None}),
        'implicit_numeric_conversion')
    add('wrong_conversion_adapter',lambda c:c['legal_edge_examples'][1].update(
        {'adapter':'NUM_coefficient'}),'adapter_type_mismatch')
    add('cycle',lambda c:c['templates'][0]['stages'][0]['after'].append('output_publish'),
        'dependency_cycle')
    add('dangling_dependency',lambda c:c['templates'][0]['stages'][1]['after'].append('missing'),
        'dangling_dependency')
    add('unknown_controller',lambda c:c['templates'][0]['stages'][0].update(
        {'controller':'FREE_CONTROLLER'}),'unknown_stage_controller')
    add('missing_full_R_versioning',lambda c:c['templates'][3]['required_services'].remove(
        'STATE_VERSIONING'),'missing_full_R_service')
    add('missing_initial_state',lambda c:c['templates'][3]['iteration_dependency'].update(
        {'initial_version_required':False}),'uninitialized_recurrence')
    add('overlapping_weight_regions',lambda c:c['examples']['ffn8_s8']['S_regions'][2].update(
        {'base_word':4}),'overlapping_S_regions')
    add('output_larger_than_T',lambda c:c['examples']['softmax257'].update({'T_words':513}),
        'T_capacity_exceeded')
    add('padding_counted_as_elements',lambda c:c['examples']['softmax257'].update(
        {'T_elements_last_word':8}),'tail_count')
    add('too_narrow_accumulator',lambda c:c['wacc'].update({'accumulator_bits':32}),
        'wacc_overflow')
    add('fixed_ROM_compiled_after_freeze',lambda c:c['binding'].update(
        {'full_programs_required_before_base_freeze':False}),'late_fixed_ROM_compile')
    add('unmeasured_hardware_claim',lambda c:c.update({'hardware_verified':True}),
        'unsupported_hardware_claim')
    add('uncompiled_eight_products_claim',lambda c:c.update(
        {'complete_model_programs_compiled':True}),'unproven_complete_products')
    add('S16_FFN_budget_reused_for_Norm',lambda c:c['examples']['ffn8_s8'].update(
        {'includes_input_norm':True}),'FFN_example_scope')
    add('unchecked_left_shift',lambda c:c['wacc'].update({'shift_min':-31}),
        'unproven_left_shift')
    return cases

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path,default=Path('.'))
    p.add_argument('--source-dir',type=Path)
    p.add_argument('--prior-source-dir',type=Path)
    p.add_argument('--output',type=Path)
    a=p.parse_args()
    root=a.root.resolve()
    c=json.loads((root/AUX/'system-design-contract.json').read_text(encoding='utf-8'))
    errors=validate(c)
    negatives=negative_cases(c)
    errors += ['negative_not_rejected:'+x['name'] for x in negatives if not x['rejected']]
    indexes=[(json.loads((root/AUX/'source-index.json').read_text(encoding='utf-8')),a.prior_source_dir),
             (json.loads((root/AUX/'system-source-index.json').read_text(encoding='utf-8')),a.source_dir)]
    by_url={}
    source_results=[]
    for idx,directory in indexes:
        for row in idx['sources']:
            by_url[unquote(row['url'])]=row
            if row['path'].startswith('ref-project/'):
                errors.append('out_of_scope_source')
            if directory:
                raw=(directory/row['snapshot_name']).read_bytes()
                blob=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
                if blob!=row['git_blob_sha'] or hashlib.sha256(raw).hexdigest()!=row['sha256']:
                    errors.append('source_hash:'+row['id'])
        source_results.append({'files':len(idx['sources']),'byte_check':'EXECUTED' if directory else 'NOT_EXECUTED'})
    links=0
    blob_links=0
    artifacts=[]
    files=DOCS+['docs/ARCHITECTURE.md',AUX+'system-design-contract.json',
                AUX+'system-source-index.json',AUX+'verify_system_design.py']
    for name in files:
        raw=(root/name).read_bytes()
        text=raw.decode('utf-8')
        artifacts.append({'path':name,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()})
        if b'\r' in raw or any(line.rstrip()!=line for line in text.splitlines()) or not raw.endswith(b'\n'):
            errors.append('whitespace:'+name)
        if not name.endswith('.md'):
            continue
        # The isolated package does not contain the entire old repository tree.
        # Check the newly appended command section of this existing common file.
        if name=='docs/ARCHITECTURE.md':
            text=text.split('## Issue151：六连接与固定产品控制研究的静态核验',1)[-1]
        for target in LINK.findall(text):
            links+=1
            u=urlsplit(target.strip('<>'))
            if u.scheme in {'http','https'}:
                if '/blob/' not in u.path:
                    continue
                key=unquote(u.scheme+'://'+u.netloc+u.path)
                row=by_url.get(key)
                if not row:
                    errors.append('unindexed_source:'+key)
                    continue
                blob_links+=1
                if u.fragment.startswith('L'):
                    m=re.fullmatch(r'L(\d+)(?:-L?(\d+))?',u.fragment)
                    if not m or not 1<=int(m.group(1))<=int(m.group(2) or m.group(1))<=row['lines']:
                        errors.append('invalid_source_anchor:'+target)
            elif not u.scheme and u.path and not (root/name).parent.joinpath(unquote(u.path)).resolve().exists():
                errors.append('broken_local_link:'+name+':'+target)
    result={'schema_version':1,'checked_at':datetime.now(timezone(timedelta(hours=8))).isoformat(timespec='seconds'),
            'passed':not errors,'python':sys.version.split()[0],
            'parent_research_commit':c.get('research_parent_commit','49a34e75657025244fd33af56111029868008db8'),
            'checks':{'templates':len(c['templates']),'stages':sum(len(t['stages']) for t in c['templates']),
                      'native_unique_owners':len(OWNERS),'negative_cases':len(negatives),
                      'negative_cases_rejected':sum(x['rejected'] for x in negatives),
                      'markdown_links':links,'indexed_blob_links':blob_links,'source_sets':source_results,
                      'FFN_S_reserved_bytes':400,'Softmax_S_used_bytes':1056,'Softmax_T_bytes':528},
            'negative_cases':negatives,'artifacts':artifacts,'errors':sorted(set(errors)),
            'not_executed':['RTL simulation','SystemC simulation','full product program compilation',
                            'synthesis','placement/routing','deadlock proof','numeric quality acceptance',
                            'manufacturing qualification','live Projects item synchronization']}
    encoded=json.dumps(result,ensure_ascii=False,indent=2)+'\n'
    if a.output:
        with a.output.open('w',encoding='utf-8',newline='\n') as f:
            f.write(encoded)
    print(json.dumps({'passed':result['passed'],'checks':result['checks'],'errors':result['errors']},
                     ensure_ascii=False,indent=2))
    return 0 if result['passed'] else 1

if __name__=='__main__':
    raise SystemExit(main())
