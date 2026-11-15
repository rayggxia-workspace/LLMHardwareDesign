"""Index every local RTL file and external elaboration dependency for PR185 review.

Coverage is not approval. Unreviewed files remain pending; hashes invalidate older
reviews. Functional macro inventories require elaboration, not source line counts.
"""
from pathlib import Path
from hashlib import sha256
from collections import Counter
import json
import xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'evidence/architecture-revision-185'
def digest(p):return sha256(p.read_bytes()).hexdigest()
def main():
    before={r['file']:r for r in json.loads((OUT/'rtl-comparison.json').read_text())}
    n32=json.loads((OUT/'n32-mod-receipt.json').read_text())
    unit=dict(n32['source_sha256'])
    for receipt_name in ('projection-local-functional-receipt.json','projection-service-assembly-receipt.json','projection-gated-assembly-receipt.json','e32-mac-mod-receipt.json','e32-dot-service-receipt.json','e32-add-cluster-receipt.json','rope-native-service-receipt.json','rope-cluster-receipt.json','rms-apply-cluster-receipt.json','indexed-gather-shared-receipt.json','shared-read-dma-receipt.json','shared-read-plane-receipt.json','shared-memory-dma-receipt.json','shared-memory-plane-receipt.json'):
        receipt=json.loads((OUT/receipt_name).read_text())
        for name,h in receipt['sources'].items():
            try:local=Path(name).relative_to(ROOT).as_posix() if Path(name).is_absolute() else name
            except ValueError:continue
            unit[local]=h
    denied={
      'rtl/blockv2_mod_p0.sv':'Old P wrapper: physical group boundary and hidden compute require replacement.',
      'rtl/blockv2_mod_p_native_lc.sv':'Old P hierarchy includes undeclared arithmetic; not current base.',
      'rtl/blockv2_mod_u_native_lc.sv':'Old U hierarchy includes undeclared arithmetic; not current base.',
      'rtl/p_native_lc_coplacement.sv':'Old group assembly: fixed supply wiring and wrong SRAM profile require replacement.',
      'rtl/p_services/blockv2_mod_p_resident_services.sv':'Embedded arithmetic must bind declared macros.',
      'rtl/services/rms_s32_service_controller.sv':'Retired combined RMS; use N mod factor and E apply with selected data transfer.',
    }
    denied.update({
      'rtl/p_services/gated_s32_scope.sv':'Embeds G32 inside service; use declared G32 via gated_s32_service_controller.',
      'rtl/p_services/s128_attention_core_scope.sv':'Embeds dot/N32/E32; corrected plan must lease declared macro resources.',
      'rtl/p_services/rope_e32_s128_commit.sv':'Embeds E32; use RoPE control with selected existing E32.',
      'rtl/u0/u_resident_add.sv':'Embeds E32 absent from U inventory; corrected Add selects declared E32 owner.',
      'rtl/u0/u_resident_rms_core.sv':'Embeds incompatible N and extra E32; use explicit N-mod and declared E32 stages.',
      'rtl/u0/u_projection_feed.sv':'Old fixed U-to-P supply implementation; no implicit U/P product route permitted.',
      'rtl/projection/blockv2_mod_projection_feed.sv':'Old U/P feed assembly; not selected by corrected graph frontend.',
    })
    from check_pr185_control_admission import validate
    controls=validate(json.loads((ROOT/'hardware/blockv2-mod-macros.json').read_text()))
    assembly=json.loads((OUT/'selected-nine-structure-receipt.json').read_text())
    active=set()
    for name,h in assembly['sources'].items():
        p=Path(name)
        if p.is_file() and digest(p)==h:active.add(str(p))
        else:raise ValueError('stale full assembly source '+name)
    disposition=json.loads((ROOT/'hardware/pr185-historical-source-disposition.json').read_text())['files']
    rows=[]
    for p in sorted((ROOT/'rtl').rglob('*')):
        if p.suffix not in ('.sv','.svh'):continue
        name=p.relative_to(ROOT).as_posix();h=digest(p);old=before.get(name)
        state='pending_full_review';reason='Check ABI, arithmetic instances, real endpoints, ownership and all callers.'
        if name in denied:state='rejected_for_corrected_base';reason=denied[name]
        elif unit.get(name)==h:
            state='unit_evidence_only'
            reason='Recorded functional receipt matches this file; whole-base binding and full graph remain unaccepted.'
        elif name.startswith('rtl/services/') or name.startswith('rtl/resources/'):
            state='replacement_in_progress'
            reason='Control/adapter implementation; register real resources and validate selected parent assembly.'
        if state=='pending_full_review' and str(p) in active:
            state='structure_evidence_only'
            reason='Current complete assembly elaboration/source hashes checked; full assembled execution remains unaccepted.'
        elif state=='pending_full_review':
            state='not_selected_unreviewed'
            reason='Absent from current parent dependency closure; no admission or functional approval. Retained historical/reference RTL.'
        if name in disposition:
            decision=disposition[name]
            if h!=decision['sha256']:raise ValueError('stale historical disposition '+name)
            if str(p) in active:raise ValueError('excluded historical RTL in current assembly '+name)
            if state=='not_selected_unreviewed':
                state='excluded_historical_reference'
                reason=decision['reason']+' Architecture disposition only; historical functional validation not claimed.'
        rows.append(dict(in_current_assembly_closure=str(p) in active,file=name,sha256=h,review_status=state,reason=reason,
          whole_base_accepted=False,initial_audit_sha256=old.get('sha256') if old else None,
          changed_since_initial_audit=old is None or h!=old['sha256'],
          comparison_source=old.get('comparison_source') if old else None,
          comparison_source_is_authoritative=False))
    xml=OUT/'projection-local-controller-114551.xml'
    tree=ET.parse(xml).getroot()
    modules={m.get('name'):m.get('origName') for m in tree.findall('./netlist/module')}
    instances=Counter(modules[c.get('submodname')] for c in tree.findall('./cells//cell'))
    forbidden={'m_native_leaf_s32','m_native_s32','e_s32_ap64','e_s32_native',
               'n_s32_softmax_s128','n_s32_mod','block_v2_n','dot_s32_core',
               'g32','local_s_base','local_s_p','blockv2_mod_projection_feed'}
    assert not forbidden.intersection(instances),instances
    # Do not rewrite an old elaboration receipt with hashes of newer sources.
    projection=json.loads((OUT/'projection-local-structural-receipt.json').read_text())
    freshness=[]
    for dep in projection['dependencies']:
        p=Path(dep['path'])
        freshness.append({'path':str(p),'matches_recorded_source':p.exists() and digest(p)==dep['sha256']})
    (OUT/'projection-old-elaboration-freshness.json').write_text(json.dumps(
        {'old_job':projection['job'],'sources':freshness,
         'scope':'old evidence freshness only; use current functional receipts for revised sources'},indent=2)+'\n')
    result={'schema':'rtl-review-coverage/1','files':rows,
       'counts':dict(Counter(r['review_status'] for r in rows)),
       'local_rtl_files':len(rows),'all_files_reviewed':False,'whole_base_accepted':False,
       'external_dependency_index':'selected-nine-structure-receipt.json',
       'external_current_dependencies':assembly['sources']}
    (OUT/'rtl-review-coverage.json').write_text(json.dumps(result,indent=2)+'\n')
    lines=['# Complete local RTL review index','',
       'Every local .sv/.svh is indexed. Pending is not approved. External dependencies are separately indexed.',
       '', '| File | Status | Required action / evidence scope |','| --- | --- | --- |']
    for r in rows:lines.append('| '+r['file']+' | '+r['review_status']+' | '+r['reason']+' |')
    (OUT/'RTL_REVIEW_INDEX.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps({'files':len(rows),'counts':result['counts'],'projection_instances':dict(instances)}))
if __name__=='__main__':main()
