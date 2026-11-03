"""Validate the P0 onchip evaluation profile; the system has external memory, whose integration is deferred.
Not a full-system memory admission, RTL or numeric-quality acceptance.
"""
import argparse,copy,hashlib,importlib.util,itertools,json,re,sys
from datetime import datetime,timezone,timedelta
from pathlib import Path
from urllib.parse import unquote,urlsplit

AUX='work/Melodydt/151/'
MODELS={'qwen25','qwen3','llama','gemma','phi','qwen35','granite','falcon'}
DOCS=['docs/STEPS_1_3_WORK_REPORT.md','docs/SAMPLE_MODEL_FAMILY_SPEC.md',
 'docs/SAMPLE_LEGAL_CONNECTION_LEDGER.md','docs/SAMPLE_ONCHIP_SYSTEM_CONTRACT.md',
 'docs/SIX_CONNECTION_SYSTEM_DESIGN.md','docs/SIX_CONNECTION_CONTROL_SPEC.md','docs/SIX_CONNECTION_TEMPLATE_SPEC.md',
 'docs/ALL_LEGAL_CONNECTION_SPEC.md','docs/LEGAL_CONNECTION_PROFILES.md',
 'docs/decisions/0006-fixed-product-hierarchical-control-candidate.md',
 'docs/decisions/0007-sample-only-onchip-contract-candidate.md',
 'docs/handoffs/2026-10-31-issue-151-six-connections.md','progress/Melodydt/STATUS.md',AUX+'README.md']
LINK=re.compile(r'(?<!!)\[[^\]]*\]\(([^\s)]+)\)')

def load_module(path,name):
    s=importlib.util.spec_from_file_location(name,str(path));m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

def admit_S(c,first,words,*,external=False,spill=False,purpose='COMPUTE'):
    if external or spill:return 'REJECT_EXTERNAL_OR_SPILL'
    if not isinstance(first,int) or not isinstance(words,int) or first<0 or words<=0:return 'REJECT_RANGE'
    if first+words>c['native_limits']['S_words']:return 'GAP_ONCHIP_CAPACITY'
    region=next((x for x in c['S_reservation']['default_regions'] if x['name']==purpose),None)
    if not region or first<region['word_first'] or first+words-1>region['word_last']:return 'REJECT_OWNERSHIP_RANGE'
    return 'CAPACITY_ONLY_NOT_HARDWARE_PASS'

def validate_resource(c):
    errors=[]
    def need(ok,name):
        if not ok:errors.append(name)
    m=c['memory_policy']
    need(m.get('applies_to')=='P0_onchip_evaluation_only' and
         c.get('architecture_memory',{}).get('system_has_external_memory') is True and
         c['architecture_memory'].get('permanent_onchip_only_architecture') is False,'memory_scope')
    need(m['external_memory_enabled'] is False and m['DMA_enabled'] is False and
         m['automatic_spill_enabled'] is False and m['EXT_request_credit']==0 and
         m['EXT_request_valid_must_be_zero'] is True,'external_policy')
    need(c['implemented_by_this_delivery'] is False,'hardware_claim')
    need(c['binding']['boot_program_load'] is False and c['binding']['permanent_M11_M12'] is True,'permanent_binding')
    n=c['native_capacity_bytes'];need(n['S_payload']==16384 and n['T_payload']==6144 and
         n['R_active_max']==8192 and n['R_shadow_max']==8192,'native_capacity')
    cells=set();total=0
    for z in c['S_reservation']['default_regions']:
        occupied=set(range(z['word_first'],z['word_last']+1))
        need(not cells.intersection(occupied),'S_overlap');cells|=occupied
        need(len(occupied)==z['words'] and z['bytes']==16*z['words'],'S_formula');total+=z['bytes']
    need(cells==set(range(1024)) and total==16384,'S_partition')
    need(next(z for z in c['S_reservation']['default_regions'] if z['name']=='COMPUTE')['bytes']==9216,'compute_region')
    capture=c['new_loader_capture_candidate']
    need(capture['payload_bytes']==1024 and capture['implemented'] is False and capture['counted_in_S_reservation'] is False,'loader_capture')
    for name,v in c['wire_formats'].items():
        if isinstance(v,dict) and 'fields' in v:
            need(sum(x[1] for x in v['fields'])==v['bits'],'field_width:'+name)
            need(len({x[0] for x in v['fields']})==len(v['fields']),'field_duplicate:'+name)
    tr=c['control_transport']
    need(tr['control_flit_bits']==64 and tr['task_beats']*64==c['wire_formats']['task']['bits'] and
         tr['event_beats']*64==c['wire_formats']['event']['bits'] and tr['implemented'] is False,'flit_transport')
    cr=c['credit_contract']
    need(cr['native_commands_outstanding_M_N_R']==1 and cr['S_narrow_requests_outstanding']==1 and
         cr['T_leases']==cr['R_contexts']==cr['N_groups']==cr['M_results']==1,'native_context_credit')
    need(cr['completion_slots_per_service']>=cr['execution_jobs_per_service'] and
         cr['global_outstanding_tasks']<=cr['candidate_services']*cr['task_slots_per_service'],'task_credit')
    b=c['new_control_storage_estimate'];need(sum(x['bytes'] for x in b['items'])==b['sum_bytes'],'control_budget_sum')
    need(all(x['count']*x['entry_bytes']==x['bytes'] for x in b['items']) and
         b['sum_bytes']+b['margin_bytes']==b['reserved_bytes']==32768,'control_budget')
    rom=c['control_ROM_estimate'];fit=rom['address_fit']
    need((rom['sample_slots']*rom['program_instructions_per_sample_slot']+rom['shared_microinstructions'])*rom['instruction_bytes']==rom['program_bytes'],'ROM_program')
    need(rom['sample_slots']*rom['parameter_records_per_sample_slot']*rom['parameter_record_bytes']==rom['parameter_bytes'],'ROM_params')
    need(rom['program_bytes']+rom['parameter_bytes']+rom['scale_layout_profile_dictionary_bytes']==rom['subtotal_bytes'] and
         rom['subtotal_bytes']+rom['margin_bytes']==rom['reserved_bytes']==2**21,'ROM_budget')
    need(fit['program_instructions']<=2**fit['PC_bits'] and fit['parameter_records']<=2**fit['parameter_index_bits'],'ROM_address_width')
    need(rom['bootload'] is False and rom['not_model_weights'] is True and rom['not_dynamic_scratch'] is True,'ROM_misuse')
    return errors

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,default=Path('.'))
    p.add_argument('--source-dir',type=Path);p.add_argument('--baseline-dir',type=Path);p.add_argument('--output',type=Path)
    a=p.parse_args();r=a.root.resolve();j=lambda n:json.loads((r/AUX/n).read_text(encoding='utf-8'))
    f=j('family-spec.json');e=j('edge-ledger.json');c=j('onchip-contract.json');dm=j('sample-memory-demand.json');o=j('sample-connection-obligations.json');ix=j('family-source-index.json')
    errors=validate_resource(c);cases=[]
    def need(ok,name):
        if not ok:errors.append(name)
    need({x['model_id'] for x in f['models']}==MODELS and len(f['models'])==8 and len(f['layer_types'])==10,'eight_models_ten_types')
    need(f['scope']['external_memory_assumed'] is False and f['scope']['other_model_variants_supported'] is False and
         f['scope']['shape_substitution_to_fit_existing_S'] is False,'family_scope')
    for model in f['models']:
        need(model['actual_export_batch']==1 and model['actual_export_sequence_tokens']==2 and
             model['actual_export_use_cache'] is False,'export_scope:'+model['model_id'])
        need(len(model['layer_sequence'])==model['num_layers'] and
             sum(model['layer_type_counts'].values())==model['num_layers'],'layer_sequence:'+model['model_id'])
        need(model['source_max_position_embeddings']>=32768,'source_position_not_test256')
    src=set(e['source_schema']);dst=set(e['destination_schema']);params=set(e['controlled_schema'])
    need(len(src)==23 and len(dst)==27 and len(params)==20,'role_dimensions')
    data={(x['src'],x['dst']) for x in e['data_slots']};par={(x['src'],x['dst']) for x in e['controlled_parameter_slots']}
    need(len(e['data_slots'])==621 and data==set(itertools.product(src,dst)),'data_cartesian')
    need(len(e['controlled_parameter_slots'])==460 and par==set(itertools.product(src,params)),'parameter_cartesian')
    allslots=e['data_slots']+e['controlled_parameter_slots'];by_id={x['id']:x for x in allslots}
    need(len(by_id)==1081,'slot_unique_ids')
    for x in allslots:
        need(x['recipe_id'] in e['recipes'],'unknown_recipe:'+x['id'])
        need(all(v in e['semantic_conditions'] for v in x['condition_ids']),'unknown_condition:'+x['id'])
        need(all(v in e['state_guards'] or v in e['mapping_guards'] for v in x.get('extra_guard_ids',[])),'unknown_guard:'+x['id'])
    for name,recipe in e['recipes'].items():
        need(all(v in e['semantic_conditions'] for v in recipe.get('semantic_guards',[])),'recipe_semantic:'+name)
        need(all(v in e['state_guards'] for v in recipe.get('state_guards',[])),'recipe_state:'+name)
        need(all(v in e['mapping_guards'] for v in recipe.get('mapping_guards',[])),'recipe_mapping:'+name)
    evaluator=load_module(r/AUX/'generate_edge_ledger.py','edge_rules')
    for case in e['static_cases']:
        actual=evaluator.evaluate(case['semantic'],case['state'],case['mapping'])
        need(actual==case['expected'],'edge_case:'+case['id']);cases.append({'id':case['id'],'passed':actual==case['expected']})
    need(len(e['summary']['macro_pair_slot_counts'])==49,'macro_pair_coverage')
    for z in o['obligations']:
        need(z['model_id'] in MODELS and z['slot_id'] in by_id and
             z['recipe_id']==by_id[z['slot_id']]['recipe_id'] and z['numeric_quality_accepted'] is False and
             z['RTL_path_implemented'] is False,'sample_obligation:'+z['id'])
    need({x['model_id'] for x in o['obligations']}==MODELS and
         {x['layer_type_id'] for x in o['obligations']}=={x['layer_type_id'] for x in f['layer_types']},'sample_obligation_scope')
    source_checked=0; config_receipt_checked=0
    if a.source_dir:
        for z in ix['sources']:
            raw=(a.source_dir/z['local_file']).read_bytes();blob=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
            need(hashlib.sha256(raw).hexdigest()==z['sha256'] and blob==z['git_blob_sha'] and len(raw)==z['bytes'],'source:'+z['id']);source_checked+=1
        derived=load_module(r/AUX/'derive_sample_memory.py','sample_mem').derive(a.source_dir)
        need(derived==dm,'memory_demand_reproducibility')
        manifest=json.loads((a.source_dir/'render01.manifest.json').read_text(encoding='utf-8'))
        for z in ix['sources']:
            if z['id'].startswith('config_'):
                name=z['id'][7:];record=next(x for x in manifest if x['model']==name)
                need(record['receipt']['artifacts']['config.json']['sha256']==z['sha256'],'config_receipt:'+name)
                config_receipt_checked+=1
        shape={z['model_key']:z for z in dm['models']}
        for m in f['models']:
            z=shape[m['model_id']];att=m['attention_configuration']
            need((m['hidden_size'],m['ffn_intermediate_size'],att['query_heads'],att['kv_heads'],att['head_dim'],m['source_max_position_embeddings'])==
                 (z['H'],z['I'],z['Q_heads'],z['KV_heads'],z['D'],z['configured_max_positions']),'config_crosscheck:'+m['model_id'])
    if a.baseline_dir:
        for z in e['provenance']:
            raw=(a.baseline_dir/z['path']).read_bytes();need(hashlib.sha256(raw).hexdigest()==z['sha256'],'ledger_frozen_input:'+z['path'])
    # These are capacity and policy tests, not executions of any macro.
    admission=[('FFN8',448,25,False,False,'COMPUTE','CAPACITY_ONLY_NOT_HARDWARE_PASS'),
       ('Softmax_raw_EXP',448,97,False,False,'COMPUTE','CAPACITY_ONLY_NOT_HARDWARE_PASS'),
       ('S_high_bits',1024,1,False,False,'COMPUTE','GAP_ONCHIP_CAPACITY'),
       ('reserved_spool_overlap',440,20,False,False,'COMPUTE','REJECT_OWNERSHIP_RANGE'),
       ('no_external',448,1,True,False,'COMPUTE','REJECT_EXTERNAL_OR_SPILL'),
       ('no_spill',448,1,False,True,'COMPUTE','REJECT_EXTERNAL_OR_SPILL'),
       ('T_spool_exact',64,384,False,False,'T_BATCH_SPOOL','CAPACITY_ONLY_NOT_HARDWARE_PASS'),
       ('T_spool_overflow',64,385,False,False,'T_BATCH_SPOOL','REJECT_OWNERSHIP_RANGE')]
    for name,first,words,ext,spill,purpose,expected in admission:
        actual=admit_S(c,first,words,external=ext,spill=spill,purpose=purpose)
        need(actual==expected,'admission:'+name);cases.append({'id':name,'passed':actual==expected})
    for length,expected in [(2304,True),(2305,False),(65535,False),(262144,False)]:
        fits=2*16*((length+7)//8)<=9216 and 16*((length+7)//8)<=6144
        need(fits==expected,'Softmax_materialization:'+str(length));cases.append({'id':'softmax_capacity_'+str(length),'passed':fits==expected})
    mutations=[('EXT_credit',lambda x:x['memory_policy'].update({'EXT_request_credit':1}),'external_policy'),
       ('bootload',lambda x:x['binding'].update({'boot_program_load':True}),'permanent_binding'),
       ('S_overlap',lambda x:x['S_reservation']['default_regions'][2].update({'word_first':447}),'S_overlap'),
       ('small_loader_capture',lambda x:x['new_loader_capture_candidate'].update({'payload_bytes':128}),'loader_capture'),
       ('bad_task_width',lambda x:x['wire_formats']['task'].update({'bits':256}),'field_width'),
       ('ROM_as_weights',lambda x:x['control_ROM_estimate'].update({'not_model_weights':False}),'ROM_misuse')]
    for name,edit,expected in mutations:
        mutated=copy.deepcopy(c);edit(mutated);caught=any(expected in v for v in validate_resource(mutated))
        need(caught,'mutation:'+name);cases.append({'id':name,'passed':caught})
    by_url={z['url']:z for z in ix['sources']}
    for name in ['source-index.json','system-source-index.json']:
        for z in j(name)['sources']:by_url[z['url']]=dict(z,line_count=z['lines'])
    files=DOCS+[AUX+n for n in ['family-spec.json','edge-ledger.json','onchip-contract.json','family-source-index.json',
      'sample-memory-demand.json','sample-connection-obligations.json','derive_sample_memory.py','generate_edge_ledger.py','verify_steps123.py']]
    artifacts=[];links=0
    for name in files:
        raw=(r/name).read_bytes();text=raw.decode('utf-8');artifacts.append({'path':name,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()})
        need(b'\r' not in raw and raw.endswith(b'\n') and all(v.rstrip()==v for v in text.splitlines()),'whitespace:'+name)
        if not name.endswith('.md'):continue
        for target in LINK.findall(text):
            links+=1;u=urlsplit(target.strip('<>'))
            if not u.scheme and u.path:need((r/name).parent.joinpath(unquote(u.path)).resolve().exists(),'local_link:'+name+':'+target)
            if u.scheme in ('http','https') and '/blob/' in u.path:
                z=by_url.get(u.scheme+'://'+u.netloc+unquote(u.path));need(z is not None,'source_link:'+target)
                if z and u.fragment.startswith('L'):
                    mm=re.fullmatch(r'L(\d+)(?:-L?(\d+))?',u.fragment)
                    need(bool(mm) and 1<=int(mm.group(1))<=int(mm.group(2) or mm.group(1))<=z['line_count'],'source_anchor:'+target)
    result={'schema_version':1,'checked_at':datetime.now(timezone(timedelta(hours=8))).isoformat(timespec='seconds'),
      'passed':not errors,'python':sys.version.split()[0],'input_design_commit':f['design_parent'],
      'checks':{'models':8,'layer_types':10,'data_slots':621,'parameter_slots':460,'shared_recipes':len(e['recipes']),
         'sample_obligations':len(o['obligations']),'rule_and_capacity_cases':len(cases),'cases_passed':sum(z['passed'] for z in cases),
         'fresh_source_byte_checks':source_checked,'config_receipt_checks':config_receipt_checked,
         'frozen_ledger_inputs_checked':bool(a.baseline_dir),'markdown_links':links,
         'new_system_RTL_paths_implemented':0,'full_model_onchip_admission_proven':False},
      'cases':cases,'artifacts':artifacts,'errors':errors,
      'execution_code_commit':'uncommitted at execution; script SHA in artifacts, delivery commit in PR receipt',
      'not_executed':['full quantized model-edge admission','all layout/scale parameter instances','RTL/SystemC/inference',
          'full program compilation','numeric quality acceptance','runtime deadlock proof','EDA/physical qualification','live Projects sync']}
    if a.output:a.output.write_bytes((json.dumps(result,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))
    print(json.dumps({'passed':not errors,'checks':result['checks'],'errors':errors},ensure_ascii=False,indent=2));return 0 if not errors else 1
if __name__=='__main__':raise SystemExit(main())
