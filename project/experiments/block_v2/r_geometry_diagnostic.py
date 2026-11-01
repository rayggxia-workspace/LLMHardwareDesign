"""Read-only source/bounded-copy DRC computation, never leaf acceptance."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import time
from physical import ROOT, sha


def main():
    p=argparse.ArgumentParser();p.add_argument('--mode',choices=('baseline','gds','locate','reinforce','partial-reinforce','monolithic','partition-controls','fresh-rc'),required=True)
    for n in ('source','candidate','out'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    receipt=json.loads((a.source/'receipt.json').read_text());assert receipt['passed'] is False
    assert sha(a.source/'receipt.json')==sha(ROOT/'work/YUZE-LU/143/r-input-hold/final-126/receipt.json')
    relative=Path('flow/results/nangate45/bv1_block_v1_r/base')
    result=dict(diagnostic_only=True,native_leaf_accepted=False,qualified=False,mode=a.mode,commands=[])
    bindings={}
    def bind(path,expected=None):
        digest=sha(path)
        if expected is not None:assert digest==expected
        bindings[str(path)]=digest;return digest
    def run(cmd,log):
        start=time.time()
        with (a.out/log).open('w') as f:r=subprocess.run(list(map(str,cmd)),cwd=a.out,stdout=f,stderr=subprocess.STDOUT)
        result['commands'].append(dict(command=list(map(str,cmd)),returncode=r.returncode,seconds=time.time()-start,log=log,sha256=sha(a.out/log)))
        assert r.returncode==0,(log,r.returncode)
    try:
        bind(a.source/'receipt.json')
        if a.mode=='baseline':
            odb=a.source/relative/'6_final.odb';bind(odb,receipt['outputs'][str(relative/'6_final.odb')])
            script='set_thread_count 16\nread_db {'+str(odb)+'}\ndrt::check_drc_cmd native-whole-drc.rpt 0 0 0 0 baseline_native_drc\n'
            (a.out/'diagnostic.tcl').write_text(script)
            run(['openroad','-no_init','-exit',a.out/'diagnostic.tcl'],'native-drc.log')
            text=(a.out/'native-whole-drc.rpt').read_text();result.update(native_drc_count=text.count('violation type:'),native_drc_zero=not text.strip())
        elif a.mode in ('reinforce','partial-reinforce'):
            from r_contained_rectangles import implement
            result.update(implement(ROOT,a.out,a.source,a.candidate,run,sha,partial=a.mode=='partial-reinforce'))
            bind(a.candidate/'candidate.odb')
        elif a.mode=='fresh-rc':
            evidence=ROOT/'work/YUZE-LU/143/r-input-hold/buffer-129/index.json'
            index=json.loads(evidence.read_text());odb=a.candidate/'candidate.odb'
            bind(odb,index['large_remote_files']['candidate.odb']['sha256'])
            sdc=a.source/relative/'6_final.sdc';bind(sdc,receipt['outputs'][str(relative/'6_final.sdc')])
            prototype=ROOT/'project/experiments/block_v2/probe_r_final_rc.tcl';bind(prototype)
            script=prototype.read_text()
            assert script.count('$::env(BV1_ODB)')==script.count('$::env(BV1_SDC)')==1
            script=script.replace('$::env(BV1_ODB)','{'+str(odb)+'}').replace('$::env(BV1_SDC)','{'+str(sdc)+'}')
            (a.out/'fresh-rc.tcl').write_text(script)
            run(['openroad','-no_init','-exit',a.out/'fresh-rc.tcl'],'fresh-rc.log')
            rows={v.split('\t')[0]:v.split('\t')[1:] for v in (a.out/'summary.tsv').read_text().splitlines()}
            assert rows['diagnostic_only']==['true'] and rows['native_leaf_accepted']==['false']
            counts={k:int(rows[k][0]) for k in ('setup_checks','hold_checks','capacitance','slew','fanout')}
            result.update(fresh_rc_counts=counts,fresh_rc_all_zero=not any(counts.values()))
        elif a.mode=='partition-controls':
            from r_gc_partition_control import controls
            result.update(controls(ROOT,a.out,a.candidate,run,sha))
            bind(a.candidate/'after.def')
        elif a.mode=='monolithic':
            from r_monolithic_drc import diagnostic
            result.update(diagnostic(ROOT,a.out,a.candidate,run,sha))
            bind(a.candidate/'candidate.odb')
        elif a.mode=='locate':
            from r_spacing_sample import sample
            result.update(sample(ROOT,a.out,a.source,a.candidate,run,sha))
            bind(a.candidate/'candidate.odb')
        else:
            candidate_manifest={}
            for line in (a.candidate/'outputs.sha256').read_text().splitlines():
                h,n=line.split();candidate_manifest[n]=h
            bind(a.candidate/'outputs.sha256');bind(a.candidate/'after.def',candidate_manifest['after.def'])
            bind(a.source/'config.mk',receipt['outputs']['config.mk'])
            for category in ('results','logs','reports','objects'):(a.out/'gds-flow'/category/'nangate45/bv1_block_v1_r/base').mkdir(parents=True)
            target=a.out/'gds-flow'/relative.relative_to('flow');shutil.copyfile(a.candidate/'after.def',target/'6_final.def')
            run(['make','-C','/OpenROAD-flow-scripts/flow','DESIGN_CONFIG='+str(a.source/'config.mk'),'WORK_HOME='+str(a.out/'gds-flow'),'NUM_CORES=16','do-gds'],'gds.log')
            gds=target/'6_final.gds';assert gds.is_file()
            deck=Path('/OpenROAD-flow-scripts/flow/platforms/nangate45/drc/FreePDK45.lydrc');bind(deck)
            run(['klayout','-b','-rd','in_gds='+str(gds),'-rd','report_file='+str(a.out/'full-deck.lyrdb'),'-r',deck],'full-deck.log')
            from native_drc import summarize
            full=summarize(a.out/'full-deck.lyrdb');result.update(full_deck=full,gds=dict(path=str(gds),sha256=sha(gds),bytes=gds.stat().st_size),full_deck_zero=full['total_items']==0)
        for path,digest in bindings.items():assert sha(path)==digest
        result.update(diagnostic_completed=True,source_bytes_unchanged=True,inputs=bindings)
    finally:
        result['outputs']={str(f.relative_to(a.out)):dict(sha256=sha(f),bytes=f.stat().st_size) for f in a.out.rglob('*') if f.is_file()}
        (a.out/'diagnostic.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(mode=a.mode,diagnostic_completed=True,native_leaf_accepted=False,native_drc_count=result.get('native_drc_count'),full_deck_items=result.get('full_deck',{}).get('total_items'))))


if __name__=='__main__':main()
