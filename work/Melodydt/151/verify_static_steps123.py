"""Cross-check static research contracts; no RTL or full product compilation."""
import argparse, hashlib, importlib.util, json, re, sys
from pathlib import Path
from datetime import datetime, timezone, timedelta
from urllib.parse import unquote, urlsplit

AUX='work/Melodydt/151/'
DOCS=['docs/STEPS_1_3_WORK_REPORT.md','docs/SAMPLE_MODEL_FAMILY_SPEC.md',
 'docs/SAMPLE_LEGAL_CONNECTION_LEDGER.md','docs/SAMPLE_ONCHIP_SYSTEM_CONTRACT.md',
 'docs/SIX_CONNECTION_SYSTEM_DESIGN.md','docs/SIX_CONNECTION_CONTROL_SPEC.md',
 'docs/SIX_CONNECTION_TEMPLATE_SPEC.md','docs/ALL_LEGAL_CONNECTION_SPEC.md','docs/LEGAL_CONNECTION_PROFILES.md',
 'docs/decisions/0008-static-compiled-common-base-candidate.md','docs/handoffs/2026-10-31-issue-151-six-connections.md',
 'progress/Melodydt/STATUS.md',AUX+'README.md']
DATA=['static-rework-index.json','family-binding-contract.json','compile-lowering-contract.json',
 'static-execution-contract.json','build_family_binding_contract.py','lower_static_connection.py',
 'verification-cases.json','verify_lowering.py','check_control_budget.py','verify_static_steps123.py',
 'probe-results.json','verification-receipt.json','independent-check-results.json']
LINK=re.compile(r'(?<!!)\[[^\]]*\]\(([^\s)]+)\)')

def loadmod(path,name):
    spec=importlib.util.spec_from_file_location(name,str(path));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,default=Path('.'));p.add_argument('--output',type=Path)
    a=p.parse_args();r=a.root.resolve();x=r/AUX;sys.path.insert(0,str(x))
    j=lambda name:json.loads((x/name).read_text(encoding='utf-8'))
    errors=[]
    def need(ok,name):
        if not ok:errors.append(name)
    ix=j('static-rework-index.json');f=j('family-binding-contract.json');l=j('compile-lowering-contract.json');c=j('static-execution-contract.json')
    original=j('family-spec.json');ledger=j('edge-ledger.json');ob=j('sample-connection-obligations.json')
    need(ix['input_commit']==f['input_commit']==c['input_commit']=='e44c4f5f492b2ef0fef12846dd25c1b1ea637664','input_ref')
    need(ix['source_RTL']==f['RTL_source']==l['source_RTL_freeze']==c['RTL_source_commit']=='643c6012a11cbf461146ac40fbf61485223fe946','RTL_ref')
    need(f['scope']['roles_are_mainly_compile_time_contracts'] and not f['scope']['mandatory_universal_runtime_type_system'],'compile_time_roles')
    need(f['scope']['common_M1_M10_active_base'] and f['scope']['permanent_M11_M12_model_binding'] and
         not f['scope']['per_product_controller_resynthesis'] and not f['scope']['bootload_control_program'],'family_same_base')
    family_check=loadmod(x/'build_family_binding_contract.py','family_binding_check').validate(f,r)
    need(family_check['model_bindings']==8 and family_check['layer_types']==10 and family_check['sample_obligations']==96,'family_counts')
    need(f['freeze_acceptance']['complete_programs_compiled']==f['freeze_acceptance']['complete_programs_accepted']==[],'no_uncompiled_acceptance')
    need(f['memory_boundary']['system_has_external_memory'] and l['scope']['system_has_external_memory'] and c['memory_scope']['system_has_external_memory'],'system_has_memory')
    need(not f['memory_boundary']['external_memory_interface_studied_this_round'] and not f['memory_boundary']['external_memory_scheduling_studied_this_round'],'memory_deferred')
    need(len(l['recipe_action_mapping'])==len(ledger['recipes'])==153 and len(l['slot_source_references'])==1081 and
         len(l['sample_obligation_classification'])==len(ob['obligations'])==96,'full_catalog_retained')
    need(all(v==0 for v in l['implementation_counts'].values()),'no_hardware_claim')
    # Compare generated artifact against the source-based planner, not a second hand-maintained table.
    planner=loadmod(x/'lower_static_connection.py','current_static_planner')
    need(planner.make_contract(r)==l,'lowering_regeneration')
    for row in l['inputs']:
        need(digest(r/row['path'])==row['sha256'],'frozen_input:'+row['path'])
    need(c['same_base']['M1_M10_and_active_geometry_identical_between_products'] and
         not c['same_base']['per_product_resynthesis'] and not c['same_base']['bootload'] and
         c['same_base']['runtime_MUX_prebuilt'],'execution_same_base')
    need(c['architecture']['global_foreground_jobs_max']==1 and c['architecture']['S_outstanding_max']==1,'execution_bounds')
    need(c['command_templates']['physical_service_capture_count']==10 and
         c['command_templates']['physical_template_capture_total_bytes']==640 and
         c['command_templates']['mother_full_descriptor_cache_bytes']==0,'physical_capture_cost')
    budgets={}
    for name in ['runtime_storage_estimate','permanent_storage_estimate']:
        b=c[name];need(sum(z['count']*z['bytes_each'] for z in b['items'])==b['subtotal_bytes'],'budget_sum:'+name)
        need(b['subtotal_bytes']+b['margin_bytes']==b['budget_point_bytes'],'budget_margin:'+name)
        budgets[name]={'subtotal':b['subtotal_bytes'],'budget':b['budget_point_bytes'],'margin':b['margin_bytes']}
    need(c['program']['capacity_unproven'] and c['permanent_storage_estimate']['capacity_unproven'],'program_not_proven')
    need(not c['implemented_by_this_delivery'] and not c['runtime_storage_estimate']['total_chip_smaller_claimed'],'no_area_claim')
    # Independent quantities from the exact model cards, not the budget prose.
    need(sum(m['num_layers'] for m in original['models'])==242,'source_layer_count242')
    q=next(m for m in original['models'] if m['model_id']=='qwen35')
    fa=next(m for m in original['models'] if m['model_id']=='falcon')
    need(q['layer_type_counts']['qwen35_gdn']==24 and fa['num_layers']==32 and
         c['state_root_design']['selected_product_max_roots']==32,'recurrent_root_source')
    need(c['state_root_design']['runtime_root_bytes']==1024,'root_payload_not_deleted')
    lower_check=j('independent-check-results.json')
    need(lower_check['result']=='PASS' and lower_check['bounded_probe_cases']==37 and
         lower_check['exact_rational_rounding_cases']==22561,'bounded_probes')
    artifacts=[];links=0;anchors=0
    for name in DOCS+[AUX+n for n in DATA]:
        raw=(r/name).read_bytes();text=raw.decode('utf-8')
        need(b'\r' not in raw and raw.endswith(b'\n') and all(v.rstrip()==v for v in text.splitlines()),'whitespace:'+name)
        if name.endswith('.json'):json.loads(text)
        artifacts.append({'path':name,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()})
        if not name.endswith('.md'):continue
        for target in LINK.findall(text):
            links+=1;u=urlsplit(target.strip('<>'))
            if not u.scheme and u.path:
                dest=(r/name).parent.joinpath(unquote(u.path)).resolve();need(dest.exists(),'link:'+name+':'+target)
                if dest.is_file() and u.fragment.startswith('L'):
                    mm=re.fullmatch(r'L(\d+)(?:-L?(\d+))?',u.fragment)
                    need(bool(mm) and 1<=int(mm.group(1))<=int(mm.group(2) or mm.group(1))<=len(dest.read_text(encoding='utf-8').splitlines()),'anchor:'+target);anchors+=1
    result={'schema_version':1,'checked_at':datetime.now(timezone(timedelta(hours=8))).isoformat(timespec='seconds'),
      'passed':not errors,'input_research_commit':ix['input_commit'],'source_RTL_commit':ix['source_RTL'],
      'python':sys.version,'execution_code_commit':'new checker uncommitted at execution; source SHA in artifacts, final commit in PR receipt',
      'checks':{'model_bindings':8,'layer_types':10,'data_slots':621,'parameter_slots':460,'recipes':153,
        'sample_obligations':96,'shared_action_families':len(l['action_families']),'bounded_probe_cases':37,
        'independent_rational_RNE_cases':22561,'complete_models_compiled':0,'new_system_RTL':0,
        'markdown_links':links,'relative_source_anchors':anchors,'root_slots':32,'physical_template_capture_bytes':640},
      'budgets':budgets,'family_checks':family_check,'artifacts':artifacts,'errors':errors,
      'not_executed':['full native model compilation','RTL/SystemC/inference','algorithm numeric quality',
       'runtime liveness proof','MEM interface/bandwidth implementation','synthesis/P&R','physical qualification','Projects sync']}
    if a.output:a.output.write_bytes((json.dumps(result,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))
    print(json.dumps({'passed':not errors,'checks':result['checks'],'budgets':budgets,'errors':errors},ensure_ascii=False))
    return int(bool(errors))

if __name__=='__main__':raise SystemExit(main())
