"""Lightweight snapshot of this task's receipts; does not alter jobs or outputs."""
from pathlib import Path
import argparse,datetime,gzip,hashlib,json,shutil,tarfile
ROOT=Path('/public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027')
def run(name):
    assert name.replace('-','').isalnum()
    out=ROOT/'snapshots'/name;out.mkdir(parents=True,exist_ok=False)
    for d in (ROOT/'trials').glob('*/*'):
        if not d.is_dir():continue
        dest=out/'trials'/d.parent.name/d.name;dest.mkdir(parents=True)
        for p in d.iterdir():
            if not p.is_file():continue
            # No ODB, DEF, netlist, SPEF, full path JSON or huge fingerprints in Git.
            if p.name in ['execution.json','driver_failure.json','stages.tsv','access.json','independent-access.json','fresh_route.drc','route.drc','timing.setup.txt','timing.hold.txt','timing.setup_tns.txt','timing.hold_tns.txt','timing.checks.txt','timing.constraint_coverage.txt','timing.parasitic_coverage.txt'] or p.suffix=='.error.txt':
                shutil.copyfile(p,dest/p.name)
            elif p.name=='openroad.log' or p.name.endswith('.pdn.rpt') or p.name.startswith('timing.selected_') or p.name in ['before.pins.tsv','after.pins.tsv'] or (p.name in ['access.tsv','independent-access.tsv'] and p.stat().st_size<10000000):
                with (dest/(p.name+'.gz')).open('xb') as raw,gzip.GzipFile(filename='',mode='wb',fileobj=raw,mtime=0) as f:f.write(p.read_bytes())
    logs=out/'logs';logs.mkdir()
    for p in (ROOT/'connectivity').glob('*/*/*.json'):
        dest=out/'connectivity'/p.relative_to(ROOT/'connectivity');dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dest)
    for p in (ROOT/'logs').glob('*.log'):
        with (logs/(p.name+'.gz')).open('xb') as raw,gzip.GzipFile(filename='',mode='wb',fileobj=raw,mtime=0) as f:f.write(p.read_bytes())
    (out/'snapshot.json').write_text(json.dumps({'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_root':str(ROOT),
        'scope':'Current receipts only; active job logs may be partial. Read execution.finished_utc/status; no job state inferred from snapshot presence.'},indent=2)+'\n')
    with tarfile.open(str(out)+'.tar.gz','x:gz') as t:t.add(str(out),arcname=name)
    print(str(out)+'.tar.gz')
if __name__=='__main__':run(argparse.ArgumentParser().parse_known_args()[1][0])
