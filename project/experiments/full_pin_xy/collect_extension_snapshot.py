"""Compact immutable snapshot of additional native stream-out/DRC evidence."""
from pathlib import Path
from collections import Counter
import datetime,gzip,json,shutil,sys,tarfile,xml.etree.ElementTree as ET
from run_exports import ROOT,sha

name=sys.argv[1];assert name.replace('-','').isalnum()
out=ROOT/'validation_extensions'/name;out.mkdir(parents=True,exist_ok=False)
summary=[]
for p in sorted((ROOT/'streamout').glob('*/*/execution.json')):
    rec=json.loads(p.read_text());dest=out/'streamout'/p.parent.parent.name/p.parent.name;dest.mkdir(parents=True)
    row={'case':rec['case'],'plan':rec['plan'],'source':str(p),'source_sha256':sha(p),'merge_returncode':rec['merge_returncode'],
       'missing_GDS_cells':rec['missing_GDS_cells'],'DRC_returncode':rec.get('DRC_returncode'),
       'source_clean_execution':rec.get('source_clean_execution'),'scope':'ACT740/full C, others8-pin pilots unless source receipt explicitly says otherwise; original A baseline. No missing GDS waiver; native DRC and this available deck are different gates.'}
    drc=p.parent/'diagnostic.lyrdb';counts=Counter()
    if drc.exists():
        for event,e in ET.iterparse(str(drc),events=['end']):
            if e.tag=='item':counts[e.findtext('category')]+=1;e.clear()
        row.update({'available_deck_violation_count':sum(counts.values()),'categories':dict(counts),'raw_report':str(drc),'raw_report_sha256':sha(drc)})
    row['full_rule_qualification']='FAILED_OR_INCOMPLETE' if rec['merge_returncode'] or counts else 'AVAILABLE_DECK_ONLY; LVS/parent/full qualification unverified'
    summary.append(row)
    for filename in ['execution.json','input.json','merge.json','merge.log','drc.log']:
        q=p.parent/filename
        if not q.exists():continue
        if q.suffix=='.log':
            with (dest/(filename+'.gz')).open('xb') as raw,gzip.GzipFile(filename='',mode='wb',fileobj=raw,mtime=0) as f:f.write(q.read_bytes())
        else:shutil.copyfile(q,dest/q.name)
    if drc.exists() and drc.stat().st_size<15000000:
        with (dest/'diagnostic.lyrdb.gz').open('xb') as raw,gzip.GzipFile(filename='',mode='wb',fileobj=raw,mtime=0) as f:f.write(drc.read_bytes())
electrical=sorted((ROOT/'electrical_observations').glob('*/summary.json'))
if electrical:shutil.copyfile(electrical[-1],out/'electrical_observations.json')
(out/'summary.json').write_text(json.dumps({'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'streamout':summary,
 'scope':'Read completed execution receipts only; unfinished jobs omitted, not passed. Complete unmodified raw outputs remain at indexed remote paths.'},indent=2)+'\n')
with tarfile.open(str(out)+'.tar.gz','x:gz') as tar:tar.add(str(out),arcname=name)
print('EXTENSION_SNAPSHOT',str(out)+'.tar.gz',len(summary),'completed stream-out receipts')
