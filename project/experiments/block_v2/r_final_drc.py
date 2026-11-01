"""Prepared R-only final geometry gate; not selected by qualification yet.

Retain the ordinary fragmented native report, check all native rules across the
complete die with freshly proved negative controls, and independently run the
unchanged complete GDS deck. No report or rule exclusions are permitted.
"""
import json
from pathlib import Path
import shutil


def drc(root,out,run,selected):
    from io_slots import file_sha as sha,slot
    from native_drc import summarize
    from r_complete_native_check import check
    folder,receipt,flow,results=selected()
    assert flow['top']=='block_v1_r'
    native_proof=check(root,out,results/'6_final.odb',run,sha)
    assert native_proof['passed'] and native_proof['no_marker_or_rule_exclusions']
    assert native_proof['source_odb_sha256']==flow['final_files']['6_final.odb']['sha256']
    nickname='bv1_'+flow['top']
    target=out/'gds-flow/results/nangate45'/nickname/'base';target.mkdir(parents=True)
    for category in ('logs','reports','objects'):(out/'gds-flow'/category/'nangate45'/nickname/'base').mkdir(parents=True)
    with slot(out.parent):shutil.copyfile(results/'6_final.def',target/'6_final.def')
    assert sha(target/'6_final.def')==flow['final_files']['6_final.def']['sha256']
    run(['make','-C','/OpenROAD-flow-scripts/flow','DESIGN_CONFIG='+str(folder/'config.mk'),
         'WORK_HOME='+str(out/'gds-flow'),'NUM_CORES=16','do-gds'],'gds.log')
    gds=target/'6_final.gds';deck=Path('/OpenROAD-flow-scripts/flow/platforms/nangate45/drc/FreePDK45.lydrc')
    deck_sha=sha(deck)
    run(['klayout','-b','-rd','in_gds='+str(gds),'-rd','report_file='+str(out/'full-deck.lyrdb'),'-r',str(deck)],'full-deck.log')
    assert sha(deck)==deck_sha
    summary=summarize(out/'full-deck.lyrdb');native=(out/'native-whole-drc.rpt').read_text()
    selected()
    result=dict(passed=summary['total_items']==0 and not native.strip() and native_proof['passed'],
                top=flow['top'],source=str(folder),source_receipt_sha256=sha(folder/'receipt.json'),
                native_report=native,full_deck=summary,deck_sha256=deck_sha,
                complete_native_proof=dict(path=str(out/'native-complete-proof.json'),sha256=sha(out/'native-complete-proof.json')),
                gds=dict(path=str(gds),sha256=sha(gds),bytes=gds.stat().st_size),qualified_hard_macro=False,
                scope='Actual final all-rule complete-die native check with original fragmented report retained, freshly executed real negative controls, exact physical geometry preservation, and complete unmodified FreePDK45 GDS deck; no exclusions')
    (out/'five-macro-drc.json').write_text(json.dumps(result,indent=2)+'\n')
    assert result['passed']
