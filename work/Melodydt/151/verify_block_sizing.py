"""Check conditional macro BOM, sample coverage and scope; not RTL simulation."""
import argparse,hashlib,json,re,sys
from pathlib import Path
from datetime import datetime,timezone
from urllib.parse import urlsplit,unquote

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,default=Path('.'));p.add_argument('--output',type=Path)
    a=p.parse_args();r=a.root.resolve();A=r/'work/Melodydt/151';j=lambda n:json.loads((A/n).read_text(encoding='utf8'))
    idx=j('block-sizing-index.json');inp=j('block-sizing-inputs.json');m=j('block-variant-models.json');b=j('resource-baselines.json');c=j('block-control-sizing.json');f=j('family-spec.json')
    mc=j('block-variant-model-checks.json');cc=j('block-control-checks.json');rc=j('resource-count-checks.json')
    errors=[]
    def need(ok,name):
        if not ok:errors.append(name)
    parent='a37e37cad757af5bfc94ed65db3e2e728023c251';leaf='707878621b2add4ed218b8c43df2e95c9a56e2ba'
    need(idx['research_parent']==inp['research_parent']==m['research_parent']==c['input_full_commit']==b['research_input']==parent,'research_parent')
    need(idx['leaf_source']==inp['leaf_source']==m['leaf_source']==c['leaf_source_commit']==leaf,'leaf_source')
    order=['M','N','E','G','R','S','T'];expected={'A_plain':[1,1,1,0,0,1,1],'A_gate':[1,1,1,1,0,1,1],'F':[1,1,1,1,0,1,1],'D':[1,1,1,1,1,1,1],'H':[1,1,1,1,1,1,1],'X':[1,1,1,1,0,1,1]}
    vm={x['variant_id']:x for x in m['variant_rows']};cm={x['profile']:x for x in c['serial_reference_function_blocks']}
    need(set(vm)==set(cm)==set(idx['resource_variants'])==set(expected),'six_variants')
    for name,vec in expected.items():
        need([vm[name]['counts'][k] for k in order]==vec and cm[name]['counts']==vec and [b['profile_baselines'][name]['seven_leaf_instances'][k] for k in order]==vec,'cross_BOM:'+name)
        need(vm[name]['leaf_instance_sum']==cm[name]['leaf_total']==sum(vec) and vm[name]['local_controller_reference_count']==cm[name]['local_CTRL_domains']==1,'sum_CTRL:'+name)
        need(not vm[name]['mathematical_minimum_proved'] and not vm[name]['complete_RTL_mapping_accepted'],'not_minimum_or_mapping:'+name)
    need([sum(expected[k]) for k in expected]==[5,6,6,7,7,6],'leaf_sums')
    need(len(m['model_rows'])==8 and len(m['layer_type_rows'])==10 and sum(x['layers'] for x in m['model_rows'])==242,'eight_ten242')
    need(m['global_logical_variant_invocations']=={'A_plain':178,'A_gate':8,'F':210,'D':24,'H':32,'X':32},'logical484_split')
    for x in m['model_rows']:
        original=next(y for y in f['models'] if y['model_id']==x['model_id'])
        need(x['source_layer_sequence']==original['layer_sequence'] and x['H']==original['hidden_size'] and x['I']==original['ffn_intermediate_size'],'source_model:'+x['model_id'])
    need([x['seven_leaf_instance_sum'] for x in b['chip_reuse_examples']]==[7,13,32,35],'chip_examples')
    need([x['S_T_double_R_bank_bytes_only'] for x in b['chip_reuse_examples']]==[38912,61440,145408,194560],'bank_examples_not_area')
    need(m['H_split_comparison']['split_leaf_instance_sum']==c['H_split_comparison']['leaf_total']==12,'Hsplit12')
    need(mc['checks_count']==313 and len(cc['checks'])==20 and rc['RTL_verification']=='NOT_EXECUTED','research_receipts')
    need(not idx['whole_LLM_BOM_complete'] and not idx['minimum_or_optimal_counts_proved'] and not idx['full_numeric_resource_program_admission'],'bounded_claims')
    need(not idx['new_RTL'] and not idx['new_simulation'] and not idx['new_PPA'] and not idx['P2_fully_accepted'] and not idx['P3_P7_started'] and not idx['server_upload_or_jobs'],'no_new_impl_server')
    for x in inp['files']:
        raw=(r/x['path']).read_bytes();need(len(raw)==x['bytes'] and hashlib.sha256(raw).hexdigest()==x['sha256'],'input:'+x['path'])
    for x in b['source_provenance']:need(hashlib.sha256((r/x['path']).read_bytes()).hexdigest()==x['sha256'],'resource_input:'+x['path'])
    # Current parent has Gemma softcapping disabled; these fresh source observations
    # supplement inherited model/graph evidence, not a new inference run.
    need(inp['Gemma_softcaps_observed_null'],'Gemma_plain_no_unaccounted_softcap')
    roadmap=j('seven-stage-roadmap.json');need(roadmap['current']['stage']=='P2' and all(x['status']=='not_started' for x in roadmap['stages'] if x['id'] in ['P3','P4','P5','P6','P7']),'route_preserved')
    links=0
    docs=idx['reports']+['docs/decisions/2026-11-01-block-variants-and-serial-counts.md']
    for name in docs:
        raw=(r/name).read_bytes();text=raw.decode('utf8');need(b'\r' not in raw and raw.endswith(b'\n') and all(x.rstrip()==x for x in text.splitlines()),'UTF8_LF:'+name)
        for target in re.findall(r'\[[^\]]+\]\(([^\s)]+)\)',text):
            u=urlsplit(target.strip('<>'));links+=1
            if not u.scheme and u.path:need((r/name).parent.joinpath(unquote(u.path)).exists(),'link:'+name+':'+target)
    out={'schema_version':1,'checked_at_utc':datetime.now(timezone.utc).isoformat(),'passed':not errors,'research_parent':parent,'leaf_source':leaf,'python':sys.version,
         'checks':{'functional_classes':5,'resource_variants':6,'BOM_integer_entries':42,'models':8,'layer_types':10,'source_layers':242,'logical_invocations':484,'model_consistency_checks':313,'control_count_checks':20,'chip_leaf_sums':[7,13,32,35],'document_links':links},
         'errors':errors,'scope':'conditional reference counts and source/accounting only; no minimum, program, numeric, model, liveness, RTL, performance or PPA admission'}
    if a.output:a.output.write_bytes((json.dumps(out,ensure_ascii=False,indent=2)+'\n').encode('utf8'))
    print(json.dumps({'passed':not errors,'checks':out['checks'],'errors':errors},ensure_ascii=False));return int(bool(errors))
if __name__=='__main__':raise SystemExit(main())
