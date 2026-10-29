"""Explain the real strict relation failure without changing that check.

Bounded examples plus a complete failing-original-net inventory. This does not
declare a split harmless or establish a broader Boolean/RTL equivalence.
"""
from pathlib import Path
from collections import defaultdict
import csv,datetime,hashlib,json,os,subprocess,sys
from run_exports import ROOT,IMAGE,sha
from verify_mapped_eco import load
from buffer_graph_contract import DSU,identity_buffer

DRIVER=Path(__file__).resolve().parent


def run(revision):
    source=ROOT/'vector_clone_probe/r03';rp=source/'execution.json';p=json.loads(rp.read_text())
    failure=ROOT/'vector_probe_equivalence/r01/execution.json';failed=json.loads(failure.read_text())
    assert p.get('completed_utc') and failed.get('completed_utc') and not failed['relative_mapped_digital_contract_pass']
    assert 'An original logical net split after buffer elimination' in failed['actual_failure']
    files=[source/'source.tsv.gz',source/'repaired.tsv.gz']
    for f in files:assert sha(f)==p['files'][f.name]['sha256']==failed['source_SHA'][str(f)]
    inputs={str(f):sha(f) for f in files+[rp,failure]}
    out=ROOT/'vector_probe_partition_diagnosis'/revision;out.mkdir(parents=True,exist_ok=False)
    lib='/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib'
    text=subprocess.check_output(['singularity','exec','--cleanenv','--home',str(ROOT/'home'),IMAGE,'cat',lib]).decode()
    assert hashlib.sha256(text.encode()).hexdigest()==failed['actual_Liberty_SHA256']
    a,at,ap=load(files[0]);b,bt,bp=load(files[1]);assert set(a)<=set(b) and ap==bp
    added=set(b)-set(a);newterms=defaultdict(dict)
    for (n,pin),value in bt.items():
        if n in added:newterms[n][pin]=value
    dsu=DSU();models={}
    for n in sorted(added):
        master=b[n][0]
        if master not in models:models[master]=identity_buffer(text,master)
        ip,op,model=models[master];terms=newterms[n];assert set(terms)=={ip,op}
        dsu.union(terms[ip][1],terms[op][1])
    ref={('I',)+k:v for k,v in at.items()};cur={('I',)+k:v for k,v in bt.items() if k[0] in a}
    ref.update({('P',n):v for n,v in ap.items()});cur.update({('P',n):v for n,v in bp.items()})
    groups=defaultdict(list)
    for key,(direction,net) in ref.items():
        if net=='NULL':continue
        got_direction,got_net=cur[key];assert direction==got_direction
        groups[net].append((key,direction,got_net,dsu.find(got_net)))
    bad={net:rows for net,rows in groups.items() if len({r[3] for r in rows})>1}
    assert bad,'Do not report the prior failure without reproducing its actual partition condition'
    cache={}
    def original_identity(master):
        if master not in cache:
            try:identity_buffer(text,master);cache[master]=True
            except AssertionError:cache[master]=False
        return cache[master]
    examples=[]
    for net,rows in sorted(bad.items())[:30]:
        endpoints=[]
        for key,direction,got_net,root in rows[:30]:
            master=a[key[1]][0] if key[0]=='I' else None
            endpoints.append({'endpoint':list(key),'direction':direction,'current_net':got_net,'new_buffer_contracted_component':root,
              'original_master':master,'current_master':b[key[1]][0] if master else None,
              'original_master_is_exact_identity_buffer':original_identity(master) if master else False})
        examples.append({'original_net':net,'current_contracted_components':sorted({r[3] for r in rows}),
          'all_original_endpoints':len(rows),'bounded_endpoint_examples':endpoints,'examples_truncated':len(rows)>30})
    with (out/'all_split_original_nets.csv').open('w',newline='') as f:
        w=csv.writer(f,lineterminator='\n');w.writerow(['original_net','current_components_after_only_new_buffer_contraction','original_endpoints'])
        for net,rows in sorted(bad.items()):w.writerow([net,len({r[3] for r in rows}),len(rows)])
    (out/'bounded_actual_endpoint_examples.json').write_text(json.dumps(examples,indent=2)+'\n')
    rec={'scope':'REAL_STRICT_PARTITION_FAILURE_DIAGNOSIS_ONLY_NO_EQUIVALENCE_PASS_OR_CHECK_RELAXATION',
      'source_SHA':inputs,'strict_relation_pass':False,'original_split_net_count':len(bad),
      'original_nonfiller_instances':len(a),'new_actual_buffer_instances':len(added),
      'bounded_examples':len(examples),'all_split_net_names_in_CSV':True,
      'interpretation':'Original/new buffer endpoint details are evidence for follow-up, not proof that rewiring is harmless. Original strict failure retained. No broader Boolean or RTL equivalence, or P&R execution.',
      'all_closed_sources_unchanged':all(sha(Path(k))==v for k,v in inputs.items()),'full_qualification':False,
      'scheduler_job':os.environ['SLURM_JOB_ID'],'driver_commit':(DRIVER/'driver_commit.txt').read_text().strip(),
      'completed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
      'files':{f.name:{'bytes':f.stat().st_size,'sha256':sha(f)} for f in out.iterdir() if f.is_file()}}
    (out/'execution.json').write_text(json.dumps(rec,indent=2)+'\n')


if __name__=='__main__':run(sys.argv[1])
