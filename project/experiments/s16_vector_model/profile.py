"""Validate observed native timing, its logs, and the exact deployed RTL."""
import hashlib,json,re
from pathlib import Path
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def require(c,m):
    if not c:raise ValueError(m)
def read_profile(root):
    root=Path(root);receipt=root/'native/results/result.json';r=json.loads(receipt.read_bytes())
    require(r['passed'] and r['functional_passed'] and r['default_exact_pairs']==3,'native gates')
    require(r['area']['status']=='passed','mapped area gate')
    collection=json.loads((root/'native/collection.json').read_bytes())
    for name,data in collection['files'].items():
        require(sha(root/'native'/name)==data['sha256'],'native received file drift '+name)
    charge={};full={}
    for label,prefix,target,selected in [
        ('compute','NEXP_COMPUTE',charge,lambda q:q['mode32']==0),
        ('bridge-u','NEXP_FULL_U',full,lambda q:q['tag']==0x4e583136)]:
        require(r['tests'][label]['passed'],'native test gate')
        for run in r['tests'][label]['runs']:
            path=root/'native/results'/run['log']
            require(sha(path)==run['log_sha256'],'timing log drift')
            rows=[{k:int(v) for k,v in re.findall(r'(\w+)=(-?\d+)',s)} for s in path.read_text().splitlines() if s.startswith(prefix+' ')]
            rows=[q for q in rows if selected(q)]
            require({q['count'] for q in rows}==set(range(1,9)) and len(rows)==8,'all native tail counts')
            for q in rows:
                count=q['count']
                if label=='compute':
                    value=q['accepted_to_next_accept_cycles']
                    require(value==q['accepted_to_done_cycles']+1,'compute response retirement')
                else:
                    require(q['S_reads']==1 and q['S_writes']==(count+3)//4,'native actual S traffic')
                    require(q['accepted_to_done_cycles']==sum(q[k] for k in ['input_stage_cycles','compute_stage_cycles','output_stage_cycles']),'native stage accounting')
                    value=q['accepted_to_done_cycles']+1
                if count in target:require(target[count]==value,'native seed timing differs')
                target[count]=value
    require(r['tests']['compute']['runs'][0]['checks']['NEXP_COMPUTE_PASS']['values']>=65536,'numeric domain gate')
    for p,digest in r['source_sha256'].items():
        # Candidate checkout files can have platform line endings; deployment
        # manifest binds exact byte versions used in the native calibration.
        if p.startswith('project/rtl/'):
            require(sha(root/'source'/p)==digest,'calibrated production RTL changed '+p)
    return dict(source_commit=r['source_commit'],result_sha256=sha(receipt),
        frame_compute_cycles=[0]+[charge[i] for i in range(1,9)],
        frame_full_U_cycles=[0]+[full[i] for i in range(1,9)],
        numeric_gate=True,scope='packed signed16 NExp compute-wrapper measured; old vector-region E/S/cache/DDR retained',
        full_U_bound='whole native U frame plus retirement, conservatively charged in addition to old E/S accounting; not an exact total-model calibration',
        vector8_scope='unimplemented complete-U 8-value/cycle service target; standalone E II=1 is insufficient')
