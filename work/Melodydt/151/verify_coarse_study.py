"""Cross-check coarse-block research evidence and limits; no simulation."""
import argparse,hashlib,json,re,sys
from pathlib import Path
from datetime import datetime,timezone
from urllib.parse import urlsplit,unquote

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,default=Path('.'));p.add_argument('--output',type=Path)
    a=p.parse_args();r=a.root.resolve();A=r/'work/Melodydt/151';j=lambda n:json.loads((A/n).read_text(encoding='utf8'))
    idx=j('coarse-study-index.json');m=j('coarse-model-map.json');c=j('coarse-control-candidate.json');b=j('coarse-block-bounds.json')
    src=j('coarse-block-source-index.json');family=j('family-spec.json');oldsrc=j('family-source-index.json')
    mc=j('coarse-model-checks.json');bc=j('coarse-block-independent-checks.json');cc=j('coarse-control-checks.json')
    errors=[]
    def need(ok,name):
        if not ok:errors.append(name)
    need(idx['research_parent']==m['research_parent']==c['input_research_ref']==src['research_parent']=='1cc43a93a0c985587745ceba5e0d8d425d43a843','research_parent')
    need(idx['leaf_source']==m['leaf_source']==c['leaf_source_commit']=='707878621b2add4ed218b8c43df2e95c9a56e2ba','leaf_ref')
    need(set(idx['profiles'])==set(c['functional_profiles'])=={x['profile_id'] for x in m['profile_rows']}==set('AFDHX'),'five_profiles')
    need(len(m['model_rows'])==8 and len(m['layer_type_rows'])==10 and sum(x['layers'] for x in m['model_rows'])==242,'eight_ten_242')
    need({x['model_id'] for x in m['model_rows']}=={x['model_id'] for x in family['models']},'source_model_ids')
    need(sum(len(x['coarse_layer_sequence'])*2 for x in m['model_rows'])==484 and len(m['sample_obligation_placement_rows'])==96,'logical484_obligations96')
    for row in m['model_rows']:
        original=next(x for x in family['models'] if x['model_id']==row['model_id'])
        need(row['source_layer_sequence']==original['layer_sequence'] and row['H']==original['hidden_size'] and row['I']==original['ffn_intermediate_size'],'real_sequence:'+row['model_id'])
    need(mc['checks_count']==313 and bc['check_count']==57 and len(cc['checks'])==17,'static_receipts')
    need(b['one_each_island']['explicit_S_T_R_bank_bytes']==38912 and b['one_each_island']['not_one_shared_38KiB_RAM'],'separate_bank_floor')
    need(not idx['new_RTL'] and not idx['new_simulation'] and not idx['new_physical_results'] and not idx['P2_fully_accepted'] and not idx['P3_P7_started'],'no_false_new_implementation')
    need(not c['implemented_by_this_delivery'] and not c['coarse_system_verified'] and not c['physical_qualified'],'candidate_only')
    need(c['scope']['system_has_external_memory'] and c['scope']['same_prefabricated_M1_M10_for_products'] and c['scope']['M11_M12_passive_permanent_binding_only'] and not c['scope']['bootload_control_program'],'fixed_base_scope')
    need(idx['server_simulation_authorized'] and not idx['server_directory_created'] and not idx['server_upload'] and not idx['server_jobs'],'server_plan_not_deployed')
    observed=src['model_source_snapshots'];need(len(observed)==19 and all(x['matched'] and x['expected_git_blob']==x['observed_git_blob'] for x in observed),'fresh19sourceblobs')
    for x in oldsrc['sources']:
        row=next(y for y in observed if y['id']==x['id'])
        need(row['path']==x['repository_path'] and row['observed_git_blob']==x['git_blob_sha'] and row['inherited_SHA256']==x['sha256'],'source_blob:'+x['id'])
    road=j('seven-stage-roadmap.json');need(road['current']['stage']=='P2' and all(x['status']=='not_started' for x in road['stages'] if x['id'] in ['P3','P4','P5','P6','P7']),'prior_route_preserved')
    need(not j('phase2-verification-status.json')['P2_fully_accepted'],'P2_not_upgraded')
    docs=idx['reports']+['docs/decisions/2026-11-01-coarse-seven-macro-islands-candidate.md']
    link_count=0
    for name in docs:
        raw=(r/name).read_bytes();text=raw.decode('utf8')
        need(b'\r' not in raw and raw.endswith(b'\n') and all(x.rstrip()==x for x in text.splitlines()),'UTF8_LF:'+name)
        for target in re.findall(r'\[[^\]]+\]\(([^\s)]+)\)',text):
            u=urlsplit(target.strip('<>'));link_count+=1
            if not u.scheme and u.path:need((r/name).parent.joinpath(unquote(u.path)).exists(),'link:'+name+':'+target)
    for x in c['sources']:need((r/x['path']).exists(),'control_source:'+x['path'])
    out={'schema_version':1,'checked_at_utc':datetime.now(timezone.utc).isoformat(),'passed':not errors,
         'research_parent':idx['research_parent'],'leaf_source':idx['leaf_source'],'python':sys.version,
         'checks':{'models':8,'layer_types':10,'source_layers':242,'logical_profile_calls':484,'obligations':96,'fresh_source_blobs':19,'model_consistency_checks':313,'bound_checks':57,'control_checks':17,'document_links':link_count,'new_RTL':False,'new_simulation':False,'new_physical_results':False},
         'errors':errors,'scope':'research consistency only; no program, resource admission, liveness, model, RTL, PPA or common-base freeze proof'}
    if a.output:a.output.write_bytes((json.dumps(out,ensure_ascii=False,indent=2)+'\n').encode('utf8'))
    print(json.dumps({'passed':not errors,'checks':out['checks'],'errors':errors},ensure_ascii=False));return int(bool(errors))
if __name__=='__main__':raise SystemExit(main())
