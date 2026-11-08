"""Seal real backend evidence without promoting fixture geometry to product pass."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import xml.etree.ElementTree as ET


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for data in iter(lambda:f.read(8 << 20),b''):h.update(data)
    return h.hexdigest()


def collect(root,output):
    root,output=Path(root),Path(output)
    output.mkdir(parents=True,exist_ok=False)
    copied=[]
    def take(source,name):
        source=Path(source);target=output/name
        target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(source,target)
        digest=sha(source)
        if sha(target)!=digest:raise ValueError('copied evidence mismatch')
        copied.append({'path':name,'source':str(source),'sha256':digest,'bytes':target.stat().st_size})
    take(root/'attempt06/product-audit/readiness.json','product/readiness.json')
    take(root/'attempt06/product-audit/route-requirements.json','product/route-requirements.json')
    for name in ('handoff-check.json','tests.log','tools.sha256','openroad-version.txt','klayout-version.txt'):
        take(root/'attempt11'/name,'checks/'+name)
    results={};artifacts={}
    for kind,count in [('P',34),('U',130),('C',34),('F',34),('J',130)]:
        base=root/'attempt05'/kind;backend=base/'backend';drc=root/'attempt07'/kind
        for name in ('spec.json','routes.json'):
            take(base/name,kind+'/'+name)
        for name in ('bindings.json','upper.def','upper-vias.lef','upper.odb','upper.gds','upper-readback.def',
                     'odb-geometry.tsv','physical-readback.json','ingest.log','physical-readback.log'):
            take(backend/name,kind+'/backend/'+name)
        for name in ('native-full.json','native-full.lyrdb','native-full.log'):
            take(drc/name,kind+'/drc/'+name)
        g=json.loads((backend/'physical-readback.json').read_text())
        r=json.loads((drc/'native-full.json').read_text())
        routes=json.loads((base/'routes.json').read_text())
        items=len(ET.parse(drc/'native-full.lyrdb').findall('.//items/item'))
        if not (g['geometry_passed'] and g['native_geometry_xor_zero'] and g['net_count']==count
                and r['native_drc_passed'] and items==r['full_original_native_deck_items']==0
                and not routes['failed'] and len(routes['routes'])==count):
            raise ValueError(kind+': physical fixture regression did not pass')
        assets=[]
        for name in ('upper.def','upper.odb','upper.gds','combined.gds'):
            p=backend/name;digest=sha(p)
            if digest!=g['sha256'][name]:raise ValueError('backend geometry changed after verification')
            assets.append({'path':str(p),'sha256':digest,'bytes':p.stat().st_size})
        artifacts[kind]=assets
        results[kind]={'routed_nets':count,'native_geometry_xor_zero':True,'native_full_drc_items':items,
                       'upper_research_geometry_passed':True,
                       'physical_qualified':False,'rc':'not_evaluated','timing':'not_evaluated'}
    snapshots=[]
    for p in sorted(root.glob('attempt*/source.tar')):
        snapshots.append({'path':str(p),'sha256':sha(p),'bytes':p.stat().st_size})
    ids='100378,100383,100389,100394,100399,100404,100406,100408,100414,100458,100463'
    states=subprocess.check_output(['sacct','-j',ids,'--format=JobID,JobName%20,State,ExitCode,AllocCPUS,Elapsed',
                                    '-n','-X','-P'],universal_newlines=True)
    (output/'slurm.psv').write_text(states)
    readiness=json.loads((output/'product/readiness.json').read_text())
    summary={'schema_version':'backend-evidence/1','collected_utc':datetime.now(timezone.utc).isoformat(),
             'fixture_regressions':results,'total_routed_signal_nets':sum(r['routed_nets'] for r in results.values()),
             'actual_backend_artifacts':artifacts,'source_snapshots':snapshots,'copied_files':copied,
             'product_schedule_rechecked':readiness['synthesis_schedule_rechecked'],
             'full_nine_group_product_passed':False,'physical_qualified':False,
             'missing_product_inputs':readiness['missing_inputs'],
             'scope':'Five independently accepted native late-interface regressions; not #220 full-product routing, RC or timing closure'}
    (output/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    archive=output.with_suffix('.tar.gz')
    with tarfile.open(archive,'w:gz') as t:
        for p in sorted(output.rglob('*')):
            if p.is_file():t.add(p,arcname=p.relative_to(output).as_posix(),recursive=False)
    archive.with_suffix(archive.suffix+'.sha256').write_text(sha(archive)+'  '+archive.name+'\n')
    print(json.dumps({'evidence_archive':str(archive),'sha256':sha(archive),'bytes':archive.stat().st_size,
                      'fixture_nets':summary['total_routed_signal_nets'],'full_product_passed':False}))


if __name__=='__main__':collect(*sys.argv[1:])
