"""Compact read-only extraction of frozen full-design ownership and top bit connections."""
from pathlib import Path
import hashlib,json,gzip,shutil

ROOT=Path.cwd().resolve();OUT=ROOT/'inputs'/'partition-r02';OUT.mkdir(exist_ok=False)
SOURCE=Path('/public/home/yuzelu/PingyangHuang/issue-55/full-block-integration-20261023T103718349596Z/runs')
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(4*1024*1024),b''):h.update(b)
    return h.hexdigest()
def dump(p,j):
    with p.open('xb') as raw,gzip.GzipFile(filename='',mode='wb',fileobj=raw,mtime=0) as f:f.write(json.dumps(j,separators=(',',':')).encode())
for case,hn in [('opentpu','hierarchy-opentpu-04'),('llaccel','hierarchy-llaccel-03')]:
    part=SOURCE/f'partition-{case}-02';review=SOURCE/f'partition-{case}-02-review01'
    rec=json.loads((review/'execution.json').read_text());assert rec['status']=='PASS_INITIAL_PARTITION_STRUCTURAL_ISOMORPHISM'
    src=part/'partitioned.json';assert sha(src)==rec['source_files'][str(src)]
    j=json.loads(src.read_text());mods=j['modules']
    tops=[(n,m) for n,m in mods.items() if m.get('attributes',{}).get('top') in [1,'00000000000000000000000000000001']];assert len(tops)==1
    top,mod=tops[0];names={c['type'] for c in mod['cells'].values()};frontier={}
    for n in names:
        m=mods[n];frontier[n]={'ports':m['ports'],'attributes':m.get('attributes',{}),'cell_count':len(m.get('cells',{})),
                              'parameter_default_values':m.get('parameter_default_values',{})}
    result={'case':case,'source_partition':str(src),'source_partition_sha256':sha(src),'top':top,'top_module':mod,'frontier':frontier,
            'inherited_structural_certificate':str(review/'partition_structural_proof.json'),
            'certificate_sha256':sha(review/'partition_structural_proof.json'),'full_top_functional_proof_scope':'inherited finite replay; not exhaustive equivalence'}
    dump(OUT/f'{case}_partition_graph.json.gz',result)
    for f in ['hierarchy_instances.jsonl.gz','partition_inventory.json','boundary_interfaces.json','input_manifest.json','execution.json']:
        src=SOURCE/hn/f;assert src.is_file();shutil.copyfile(src,OUT/f'{case}_{f}')
    for f in ['leaf_origin_inventory.jsonl.gz','auxiliary_extraction.json','execution.json']:
        src=part/f;assert src.is_file();shutil.copyfile(src,OUT/f'{case}_partition_{f}')
    print(case,'TOP',top,'cells',[(n,c['type']) for n,c in mod['cells'].items()],flush=True)
    print('ports',[(n,len(c['ports'])) for n,c in frontier.items()],flush=True)
print('PARTITION_COLLECTION_COMPLETE',flush=True)
