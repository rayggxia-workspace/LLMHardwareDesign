"""Lint declared all-legal connection scope; never simulate hardware or prove coverage."""
import argparse,copy,hashlib,json,re,sys
from datetime import datetime,timezone,timedelta
from pathlib import Path
from urllib.parse import unquote,urlsplit

AUX='work/Melodydt/151/'
MACROS=set('MNEGRST')
DOCS=['docs/ALL_LEGAL_CONNECTION_SPEC.md','docs/LEGAL_CONNECTION_PROFILES.md',
      'docs/SIX_CONNECTION_SYSTEM_DESIGN.md','docs/SIX_CONNECTION_CONTROL_SPEC.md',
      'docs/SIX_CONNECTION_TEMPLATE_SPEC.md']
LINK=re.compile(r'(?<!!)\[[^\]]*\]\(([^\s)]+)\)')

def validate(c):
    errors=[]
    def need(ok,code):
        if not ok:errors.append(code)
    need(set(c.get('macros',[]))==MACROS,'macro_set')
    scope=c.get('scope',{})
    need(scope.get('finite_families') is True and scope.get('all_legal_role_combinations_target') is True,'scope')
    need(scope.get('six_templates_are_whitelist') is False,'six_template_whitelist')
    need(scope.get('pair_index_is_full_coverage_proof') is False and
         scope.get('all_new_system_paths_implemented') is False,'unsupported_coverage_claim')
    need(scope.get('missing_implementation_changes_semantic_legality') is False,'legality_implementation_coupling')
    b=c.get('binding',{})
    need(b.get('only_M11_M12_permanent') is True and b.get('boot_program_load') is False,'binding')
    need(b.get('full_family_programs_compiled') is False,'unproven_family_programs')
    src=c.get('source_roles',{}); dst=c.get('destination_roles',{})
    need(set(src)==MACROS and set(dst)==MACROS and all(src.values()) and all(dst.values()),'role_registry')
    need({'stored_word','write_echo','loader_A','loader_B'}<=set(src.get('S',{})),'S_source_roles')
    need({'activation','gated'}<=set(src.get('G',{})),'G_source_roles')
    need(set(c.get('controlled_parameter_roles',{}))==MACROS and
         set(c.get('control_events',{}))==MACROS,'control_roles')
    ps=c.get('profiles',[])
    need({p['id'] for p in ps}=={'P%02d'%i for i in range(1,16)} and len(ps)==15,'profile_set')
    need(all(p.get('status')=='candidate_not_implemented' for p in ps),'profile_claim')
    pairs=c.get('pairs',[]); keys=[(p['source'],p['destination']) for p in pairs]
    need(len(keys)==49 and len(set(keys))==49 and set(keys)=={(a,b) for a in MACROS for b in MACROS},'pair_index')
    for p in pairs:
        a,b=p['source'],p['destination']; label=p.get('id','?')
        if a not in src or b not in dst: errors.append('unknown_pair:'+label);continue
        need(set(p.get('source_roles',[]))==set(src[a]) and
             set(p.get('destination_roles',[]))==set(dst[b]),'pair_role_index:'+label)
        need(p.get('semantic_status')=='conditional_by_roles_and_profile' and
             p.get('source_destination_role_cartesian_is_all_legal') is False,'role_cartesian_claim:'+label)
        need(p.get('route')==['EXPORT_'+a,'TYPED_STORE','IMPORT_'+b],'route_recipe:'+label)
        need(set(p.get('required_services',[]))<=set(c.get('services',{})),'missing_service:'+label)
        need(p.get('rtl_implemented') is False and p.get('verified') is False and
             p.get('physical_qualified') is False,'pair_completion_claim:'+label)
        need(p.get('self_lifecycle_required')==(a==b),'self_flag:'+label)
    need(set(c.get('self_lifecycle',{}))==MACROS,'self_rules')
    need(c.get('self_lifecycle',{}).get('R')=='RESUME_same_lease_by_native_guard; save_and_commit_or_revoke_before_new_OPEN' and
         c.get('self_lifecycle',{}).get('N')=='RESUME_group_by_native_guard; finish_before_new_BEGIN','resume_vs_new_context')
    need(c.get('pair_required_services_are_exhaustive_role_recipes') is False,'coarse_index_claim')
    need(c.get('self_lifecycle',{}).get('T')=='spool_entire_batch_then_release_then_BEGIN_new_generation','T_self_lifecycle')
    ctl=c.get('control',{})
    need(ctl.get('unique_native_owner') is True and ctl.get('stage_revisitable_context_leases') is True,'control_composability')
    need(ctl.get('bounded_loops_with_initial_state') is True and
         ctl.get('runtime_arbitrary_graph_switch') is False,'feedback_or_runtime_graph')
    sp=c.get('special_profiles',{})
    need(sp.get('S64_to_S16',{}).get('needs')=='NUM_CONVERT' and
         sp['S64_to_S16'].get('implemented') is False,'S64_gap')
    need(sp.get('EXP_to_probability',{}).get('needs')=='N_normalization_not_bitcast' and
         sp.get('ID_to_score',{}).get('needs')=='GATHER_not_reinterpret','semantic_reinterpret')
    need(sp.get('T_self',{}).get('max_spool_bytes')==384*16 and
         sp['T_self'].get('two_slot_fifo_sufficient') is False,'T_spool_capacity')
    need(sp.get('G_output',{}).get('gated_sigmoid_frac')==10 and
         sp.get('R_S32',{}).get('frac')=='product_declared','native_numeric_contract')
    le=sp.get('S_loader_export',{})
    need(le.get('ordinary_S_access_serialized') is True and le.get('whole_descriptor_spool_required') is True and
         le.get('payload_spool_bytes')==le.get('max_A_bytes',0)+le.get('max_B_bytes',0)==1024 and
         le.get('drain_unused_branch') is True and le.get('implemented') is False,'loader_export_spool')
    return sorted(set(errors))

def negatives(base):
    out=[]
    def case(name,fn,key):
        c=copy.deepcopy(base);fn(c);e=validate(c)
        out.append({'name':name,'rejected':any(key in x for x in e),'expected':key})
    case('missing_pair',lambda c:c['pairs'].pop(),'pair_index')
    case('duplicate_pair',lambda c:c['pairs'].__setitem__(0,copy.deepcopy(c['pairs'][1])),'pair_index')
    case('missing_loader_B_role',lambda c:c['source_roles']['S'].pop('loader_B'),'S_source_roles')
    case('all_roles_implicitly_legal',lambda c:c['pairs'][0].update({'source_destination_role_cartesian_is_all_legal':True}),'role_cartesian_claim')
    case('six_templates_whitelist',lambda c:c['scope'].update({'six_templates_are_whitelist':True}),'six_template_whitelist')
    case('missing_implementation_called_illegal',lambda c:c['scope'].update({'missing_implementation_changes_semantic_legality':True}),'legality_implementation_coupling')
    case('bootload_required',lambda c:c['binding'].update({'boot_program_load':True}),'binding')
    case('uncompiled_families_reported_complete',lambda c:c['binding'].update({'full_family_programs_compiled':True}),'unproven_family_programs')
    case('unimplemented_pair_reported_verified',lambda c:c['pairs'][0].update({'verified':True}),'pair_completion_claim')
    case('S64_via_E13',lambda c:c['special_profiles']['S64_to_S16'].update({'needs':'E13'}),'S64_gap')
    case('EXP_bitcast_probability',lambda c:c['special_profiles']['EXP_to_probability'].update({'needs':'bitcast'}),'semantic_reinterpret')
    case('T_spool_two_slots',lambda c:c['special_profiles']['T_self'].update({'two_slot_fifo_sufficient':True}),'T_spool_capacity')
    case('controller_only_super_tasks',lambda c:c['control'].update({'stage_revisitable_context_leases':False}),'control_composability')
    case('feedback_without_initial_state',lambda c:c['control'].update({'bounded_loops_with_initial_state':False}),'feedback_or_runtime_graph')
    case('loader_export_small_spool',lambda c:c['special_profiles']['S_loader_export'].update({'payload_spool_bytes':128}),'loader_export_spool')
    return out

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,default=Path('.'));p.add_argument('--output',type=Path)
    a=p.parse_args();r=a.root.resolve();c=json.loads((r/AUX/'all-legal-connection-contract.json').read_text(encoding='utf-8'))
    errors=validate(c); ns=negatives(c); errors+=['negative_not_rejected:'+x['name'] for x in ns if not x['rejected']]
    links=0; artifacts=[]
    for name in DOCS+[AUX+'all-legal-connection-contract.json',AUX+'verify_all_legal_connections.py']:
        raw=(r/name).read_bytes(); text=raw.decode('utf-8')
        artifacts.append({'path':name,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()})
        if b'\r' in raw or not raw.endswith(b'\n') or any(x.rstrip()!=x for x in text.splitlines()):errors.append('whitespace:'+name)
        if name.endswith('.md'):
            for target in LINK.findall(text):
                links+=1;u=urlsplit(target.strip('<>'))
                if not u.scheme and u.path and not (r/name).parent.joinpath(unquote(u.path)).resolve().exists():errors.append('local_link:'+name+':'+target)
    result={'schema_version':1,'checked_at':datetime.now(timezone(timedelta(hours=8))).isoformat(timespec='seconds'),
      'passed':not errors,'python':sys.version.split()[0],'design_parent':c['design_parent'],
      'checks':{'macro_pair_index':len(c['pairs']),'source_role_index':sum(map(len,c['source_roles'].values())),
                'destination_role_index':sum(map(len,c['destination_roles'].values())),'profile_families':len(c['profiles']),
                'self_lifecycles':len(c['self_lifecycle']),'negative_cases':len(ns),'negative_cases_rejected':sum(x['rejected'] for x in ns),
                'markdown_links':links,'new_system_paths_implemented':0,'full_hardware_coverage_proven':False},
      'negative_cases':ns,'artifacts':artifacts,'errors':errors,
      'not_executed':['complete family catalog/domain enumeration','complete role/profile parameter coverage','family program compilation',
                      'RTL simulation','integer numeric oracle','deadlock proof','synthesis','placement/routing','physical qualification','online Projects sync'],
      'limits':'Static design-index and assertion consistency only; no measured connection pass rate.'}
    if a.output:a.output.write_bytes((json.dumps(result,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))
    print(json.dumps({'passed':not errors,'checks':result['checks'],'errors':errors},ensure_ascii=False,indent=2))
    return 0 if not errors else 1
if __name__=='__main__':raise SystemExit(main())
