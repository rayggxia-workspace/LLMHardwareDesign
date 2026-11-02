"""Allocated-node audit of explicit positive/negative/candidate manifests.

Does not modify inference outputs. Reassesses frozen numerical gates; original
FP32 metrics are retained, not silently replaced by this file-integrity audit.
"""
import argparse,concurrent.futures,hashlib,importlib.util,json,struct,subprocess,time
from pathlib import Path

def digest(p):
    h=hashlib.sha256()
    with p.open('rb')as f:
        for b in iter(lambda:f.read(16*1024*1024),b''):h.update(b)
    return dict(bytes=p.stat().st_size,sha256=h.hexdigest())

def module(name,p):
    s=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

def records(p,size):
    raw=p.read_bytes();at=n=0
    while at<len(raw):
        e,count=struct.unpack_from('<iI',raw,at);assert count==size
        at+=8+2*count+(4*count if e==-2147483648 else 0);n+=1
    assert at==len(raw);return n

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('root',type=Path)
    ap.add_argument('manifest',type=Path);ap.add_argument('output',type=Path);a=ap.parse_args();root=a.root;started=time.time()
    manifest=json.loads(a.manifest.read_text());cases=manifest['cases']
    analyze=module('strict_flow',root/manifest['analyzer']).analyze
    assess=module('frozen_gates',root/'src-f2/project/systemc/llm/tools/assess_numerics.py').assess
    cps={root/c['checkpoint']for c in cases};exports={cp:json.loads((cp/'export_receipt.json').read_text())for cp in cps}
    heavy=set()
    for cp,ex in exports.items():
        heavy.add((cp/'weights.bin').resolve())
        if (cp/'weights.scales').exists():heavy.add((cp/'weights.scales').resolve())
        if (cp/'parameters.scales').exists():heavy.add((cp/'parameters.scales').resolve())
        heavy.update(Path(row['path']).resolve()for row in ex['source_files'])
    with concurrent.futures.ThreadPoolExecutor(max_workers=6)as pool:
        heavy_hashes=dict(zip(sorted(heavy),pool.map(digest,sorted(heavy))))
    def sha(p):return heavy_hashes[p.resolve()]if p.resolve()in heavy_hashes else digest(p)
    for cp,ex in exports.items():
        assert sha(cp/'weights.bin')['sha256']==ex['weights_sha256']
        if (cp/'weights.scales').exists():assert sha(cp/'weights.scales')['sha256']==ex['weight_scales_sha256']
        if (cp/'parameters.scales').exists():assert sha(cp/'parameters.scales')['sha256']==ex['parameter_scales_sha256']
        for row in ex['source_files']:assert sha(Path(row['path']))==dict(bytes=row['bytes'],sha256=row['sha256'])
        if ex.get('reference_reused_from'):
            for n in ('reference_hidden.bin','reference_logits.bin'):assert sha(cp/n)==sha(Path(ex['reference_reused_from'])/n)
        for directory,key in (('previous_export','previous_receipt_sha256'),('sequence_case_parent','sequence_case_parent_receipt_sha256'),
                              ('recheck_weight_parent','recheck_weight_receipt_sha256'),('reference_reused_from','reference_receipt_sha256')):
            if directory in ex and key in ex:assert sha(Path(ex[directory])/'export_receipt.json')['sha256']==ex[key]
    def audit(c):
        run=root/c['run'];cp=root/c['checkpoint'];ex=exports[cp];cfg=ex['config']
        receipt=json.loads((run/'systemc_receipt.json').read_text());val=json.loads((run/'validation.json').read_text())
        gates=assess(run/'validation.json');expected=c['expected_accepted']
        if expected is not None:assert gates['accepted']==expected,(c['run'],gates['failures'])
        if (run/'numerical-gates.json').exists():assert gates==json.loads((run/'numerical-gates.json').read_text())
        assert analyze(run)==json.loads((run/'flow-summary.json').read_text()),'flow audit changed'
        steps=len(ex['reference_inputs']);assert len(receipt['inputs'])==len(val['steps'])==steps
        assert len(receipt['generated'])==c['generated_tokens']
        if expected is True:assert receipt['inputs']==ex['reference_inputs']
        assert records(run/'systemc_hidden.bin',cfg['hidden_size'])==steps*(cfg['num_hidden_layers']+1)
        assert records(run/'systemc_logits.bin',cfg['vocab_size'])==steps
        assert (receipt['transactions']['R']>0)==(c['model']in ('falcon','qwen35'))
        log=root/c['log'];assert sum(s.startswith('LAYER ')for s in log.read_text().splitlines())==steps*cfg['num_hidden_layers']
        paths=[p for p in run.iterdir()if p.is_file()]+[cp/n for n in ('metadata.txt','weights.index','weights.bin','prompt.txt','export_receipt.json','reference_hidden.bin','reference_logits.bin')]+[log]
        if (cp/'weights.scales').exists():paths.append(cp/'weights.scales')
        if (cp/'parameters.scales').exists():paths.append(cp/'parameters.scales')
        hashes={str(p):sha(p)for p in paths}
        for path,h in val['hashes'].items():assert hashes[path]['sha256']==h
        for line in (run/'run-inputs.sha256').read_text().splitlines():
            h,path=line.split(maxsplit=1);p=root/path.lstrip('*');assert sha(p)['sha256']==h,str(p)
        equivalence={}
        for base in c.get('byte_equal_to',[]):
            for n in ('systemc_hidden.bin','systemc_logits.bin'):
                p=root/base/n;equivalence[str(p)]=sha(p);assert sha(run/n)==sha(p),'binary equivalence'
        controls={};control_file=run/'flow-controls.jsonl'
        if control_file.exists():
            rows=[json.loads(s)for s in control_file.read_text().splitlines()]
            tokens=[r for r in rows if r['name']=='token.next']
            assert [r['ids'][0]for r in tokens]==receipt['next_ids']and [r['step']for r in tokens]==list(range(steps))
            experts=[r for r in rows if r['name']=='moe.experts'];by_layer={}
            for r in experts:
                assert len(r['ids'])==len(set(r['ids']))==cfg['num_experts_per_tok']
                assert all(0<=i<cfg['num_local_experts']for i in r['ids'])
                by_layer.setdefault(r['layer'],[]).append(r)
            changes=sum(set(p['ids'])!=set(q['ids'])for rr in by_layer.values()for p,q in zip(rr,rr[1:]))
            if c['model']=='granite':assert len(experts)==steps*cfg['num_hidden_layers']and changes>0
            else:assert not experts
            controls=dict(token_decisions=len(tokens),expert_decisions=len(experts),expert_set_changes_between_positions=changes,
                          distinct_expert_ids=sorted({i for r in experts for i in r['ids']}),expert_selection_examples=experts[:3])
        link=json.loads((run/'tensor-link.json').read_text())
        if not c['link']:assert not link['enabled']and link['packets']==0
        else:
            assert link['enabled']and link['width_bytes']==c['width_bytes']and link['queue_packets_each_direction']==c['queue_packets']
            assert 0<link['max_request_slots']<=c['queue_packets']and link['bytes']>0 and link['tensor_transfers']>0
            assert link['packet_latency_ns']==2 and link['beat_ns']==1 and link['mtu_bytes']==256
            assert abs(link['simulated_ns']-link['service_ns'])<.001
            assert 2*link['packets']+link['bytes']/c['width_bytes']<=link['service_ns']<=3*link['packets']+link['bytes']/c['width_bytes']
        return dict(case=c,layers=cfg['num_hidden_layers'],steps=steps,gates=gates,files=hashes,
                    baseline_binary_hashes=equivalence,controls=controls,link=link)
    with concurrent.futures.ThreadPoolExecutor(max_workers=6)as pool:runs=list(pool.map(audit,cases))
    by_name={r['case']['run']:r for r in runs}
    for m,names in manifest['queue_width_comparisons'].items():
        narrow,wide1,wide=[by_name[n]['link']for n in names]
        for key in ('bytes','packets','tensor_transfers'):assert narrow[key]==wide1[key]==wide[key]
        assert wide1['service_ns']==wide['service_ns']<narrow['service_ns']
    selected={m:by_name[n]for m,n in manifest['final_sequence'].items()}
    assert len(selected)==7 and all(r['gates']['accepted']and r['steps']==9 for r in selected.values())
    executable=manifest['final_common_executable']
    for r in selected.values():
        lines=(root/r['case']['run']/'run-inputs.sha256').read_text().splitlines()
        assert any(line.split(maxsplit=1)[1]==executable for line in lines),'final binary differs'
    files={str(root/n):sha(root/n)for n in manifest['extra_files']};diagnostics={}
    for model,p in manifest['weight_diagnostics'].items():
        q=json.loads((root/p).read_text());assert q['family']in ('falcon_h1','gemma3_text','qwen2')
        diagnostics[model]=dict(compared_prefix_positions=q['compared_prefix_positions'],top1=[s['top1_equal']for s in q['steps']],
             worst_hidden_relative_l2=max(h['relative_l2']for s in q['steps']for h in s['hidden']))
        files[str(root/p)]=sha(root/p)
    result=dict(scope=manifest['scope'],manifest_sha256=digest(a.manifest),runs=runs,final_sequence=manifest['final_sequence'],
                weight_diagnostics=diagnostics,files=files,large_input_files={str(p):h for p,h in heavy_hashes.items()},
                slurm=subprocess.check_output(['sacct','-j'+','.join(map(str,manifest['jobs'])),'-n','-X','-o','JobID,State,ExitCode,Elapsed,NodeList'],universal_newlines=True),seconds=time.time()-started)
    with a.output.open('x')as f:json.dump(result,f,indent=2);f.write('\n')
    print('INTERCONNECT_AUDIT_PASS',len(runs),'runs; retained failures',sum(not r['gates']['accepted']for r in runs),'final sequence 7/7',flush=True)

if __name__=='__main__':main()
