"""Compute complete unchanged GDS rules while native final reports run.

Only an exact final DEF match plus a fresh final-ODB whole-chip check can join
this computation to a sealed candidate. A computation is never leaf acceptance.
"""
import concurrent.futures
import json
from pathlib import Path
import shutil

from io_slots import file_sha as sha


def compute(root,folder,out,run):
    from native_drc import summarize
    proof=folder/'route-repair-proof.json'
    p=json.loads(proof.read_text())
    assert p['passed'] and p['identical_non_target_geometry'] and p['native_whole_drc_zero']
    results=folder/'flow/results/nangate45/bv1_block_feed_s_macro/base'
    odb=results/'5_route.odb';definition=folder/'after-route.def'
    assert sha(definition)==p['after_def_sha256']
    bindings={str(f):sha(f) for f in (proof,odb,definition,folder/'config.mk')}
    script='set_thread_count 16\nread_db {'+str(odb)+'}\nwrite_def native-check.def\n'
    script+='drt::check_drc_cmd native-whole-drc.rpt 0 0 0 0 native_whole_drc\n'
    (out/'native-drc.tcl').write_text(script)
    run(['openroad','-no_init','-exit',out/'native-drc.tcl'],'native-drc.log')
    assert sha(out/'native-check.def')==sha(definition)
    assert not (out/'native-whole-drc.rpt').read_text().strip()
    for category in ('results','logs','reports','objects'):
        (out/'gds-flow'/category/'nangate45/bv1_block_feed_s_macro/base').mkdir(parents=True)
    target=out/'gds-flow/results/nangate45/bv1_block_feed_s_macro/base'
    shutil.copyfile(definition,target/'6_final.def')
    run(['make','-C','/OpenROAD-flow-scripts/flow','DESIGN_CONFIG='+str(folder/'config.mk'),
         'WORK_HOME='+str(out/'gds-flow'),'NUM_CORES=16','do-gds'],'gds.log')
    gds=target/'6_final.gds'
    deck=Path('/OpenROAD-flow-scripts/flow/platforms/nangate45/drc/FreePDK45.lydrc')
    run(['klayout','-b','-rd','in_gds='+str(gds),'-rd','report_file='+str(out/'full-deck.lyrdb'),'-r',str(deck)],'full-deck.log')
    full=summarize(out/'full-deck.lyrdb');assert full['total_items']==0
    assert all(sha(f)==h for f,h in bindings.items())
    report=dict(passed=True,source=str(folder),source_geometry=bindings,full_deck=full,
        deck_sha256=sha(deck),gds=dict(path=str(gds),sha256=sha(gds),bytes=gds.stat().st_size),
        native_report='',native_leaf_accepted=False,
        scope='Complete unmodified FreePDK45 computation on repaired actual geometry; sealed final candidate must independently join exact DEF and fresh final native DRC')
    (out/'drc-computation.json').write_text(json.dumps(report,indent=2)+'\n')


def join(root,folder,out,run,computation):
    from qualify import source
    from native_drc import summarize
    folder,r,flow,results=source(folder)
    assert flow['top']=='block_feed_s_macro'
    producer=json.loads((computation/'receipt.json').read_text())
    assert producer['passed'] and producer['operation']=='drc-compute'
    assert len(producer['commands'])==3 and all(c['returncode']==0 for c in producer['commands'])
    producer_root=computation.parents[1]
    manifest=json.loads((producer_root/'source-manifest.json').read_text())
    rows=[(producer_root/p,h) for p,h in producer['inputs'].items()]
    rows += [(producer_root/p,h) for p,h in manifest['files'].items()]
    rows += [(computation/p,h) for p,h in producer['outputs'].items()]
    def check(row):assert sha(row[0])==row[1],str(row[0])
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:list(pool.map(check,rows))
    for c in producer['commands']:assert sha(computation/c['log'])==c['sha256']
    report=json.loads((computation/'drc-computation.json').read_text())
    assert report['passed'] and report['native_leaf_accepted'] is False
    for f,h in report['source_geometry'].items():assert sha(f)==h
    definition=Path(report['source'])/'after-route.def'
    assert sha(results/'6_final.def')==report['source_geometry'][str(definition)]
    deck=Path('/OpenROAD-flow-scripts/flow/platforms/nangate45/drc/FreePDK45.lydrc')
    assert report['deck_sha256']==sha(deck)
    assert report['full_deck']==summarize(computation/'full-deck.lyrdb')
    assert report['full_deck']['total_items']==0
    assert sha(report['gds']['path'])==report['gds']['sha256']
    # Check the real final ODB again, independently of the earlier geometry.
    script='set_thread_count 16\nread_db {'+str(results/'6_final.odb')+'}\nwrite_def before.def\n'
    script+='drt::check_drc_cmd native-whole-drc.rpt 0 0 0 0 native_whole_drc\nwrite_def after.def\n'
    (out/'native-drc.tcl').write_text(script)
    run(['openroad','-no_init','-exit',out/'native-drc.tcl'],'native-drc.log')
    assert sha(out/'before.def')==sha(out/'after.def')==sha(definition)
    assert not (out/'native-whole-drc.rpt').read_text().strip()
    for name in ('full-deck.lyrdb','full-deck.log','drc-computation.json'):
        shutil.copyfile(computation/name,out/name)
    shutil.copyfile(computation/'receipt.json',out/'drc-computation-receipt.json')
    result=dict(passed=True,top=flow['top'],source=str(folder),source_receipt_sha256=sha(folder/'receipt.json'),
        native_report='',full_deck=report['full_deck'],deck_sha256=sha(deck),gds=report['gds'],
        computation=dict(receipt=str(computation/'receipt.json'),receipt_sha256=sha(computation/'receipt.json'),
            exact_final_def_sha256=sha(definition),all_original_outputs_rehashed=True,fresh_final_whole_drc_zero=True),
        qualified_hard_macro=False,scope='Actual final whole-chip native DRC plus complete unmodified GDS deck on byte-identical final DEF; all rules, no exclusions')
    (out/'five-macro-drc.json').write_text(json.dumps(result,indent=2)+'\n')
