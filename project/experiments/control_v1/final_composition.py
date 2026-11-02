"""Run real programs against all selected actual final leaf netlists.

Zero-delay final-cell composition is separate from upper interconnect STA.
"""
import argparse,hashlib,json,os,re,subprocess,time,concurrent.futures,threading
from pathlib import Path

def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for chunk in iter(lambda:f.read(1048576),b''):h.update(chunk)
    return h.hexdigest()

def main():
    p=argparse.ArgumentParser();p.add_argument('--manifest',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--hierarchical',action='store_true');a=p.parse_args()
    assert os.environ.get('SLURM_JOB_ID') and len(os.sched_getaffinity(0))<=16
    root=Path(__file__).resolve().parents[3];a.out.mkdir(parents=True,exist_ok=False)
    r=dict(passed=False,job=os.environ['SLURM_JOB_ID'],inputs={str(a.manifest):sha(a.manifest)},commands=[],qualified_system=False)
    lock=threading.Lock()
    def run(cmd,log):
        with (a.out/log).open('w') as f:q=subprocess.run(list(map(str,cmd)),cwd=a.out,stdout=f,stderr=subprocess.STDOUT)
        with lock:r['commands'].append(dict(command=list(map(str,cmd)),returncode=q.returncode,log=log,sha256=sha(a.out/log)))
        assert q.returncode==0,log
    def bind(path,digest):
        assert sha(path)==digest,path;r['inputs'][str(path)]=digest
    try:
        views=[];tops=[];manifest=json.loads(a.manifest.read_text())
        assert len(manifest['leaves'])==20 and 'control_reset_distribution' in manifest['leaves']
        for label,leaf in manifest['leaves'].items():
            receipt=Path(leaf['receipt']);bind(receipt,leaf['receipt_sha256']);g=json.loads(receipt.read_text());assert g['passed']
            report=Path(leaf['report']);bind(report,leaf['report_sha256']);assert g['outputs'][report.name]==leaf['report_sha256']
            proof=json.loads(report.read_text());assert proof['passed']
            found={}
            def search(v):
                if isinstance(v,dict):
                    if v.get('full_view') and v.get('full_view_sha256'):found[v['full_view']]=v
                    for w in v.values():search(w)
                elif isinstance(v,list):
                    for w in v:search(w)
            # The S proof also binds its M feeder peer. Only the report's
            # explicit primary physical view implements this selected leaf.
            assert 'full_final_netlist' in proof,label
            search(proof['full_final_netlist']);assert len(found)==1,(label,list(found))
            path,view=next(iter(found.items()));assert view['passed'];bind(path,view['full_view_sha256'])
            for name,digest in view['input_sha256'].items():bind(name,digest)
            views.append(path);tops.append(label)
        lib=Path('/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib')
        r['inputs'][str(lib)]=sha(lib)
        (a.out/'cells.ys').write_text('read_liberty -ignore_miss_func -ignore_miss_dir '+str(lib)+'\nwrite_verilog -noattr cells.v\n')
        run(['yosys','-s',a.out/'cells.ys'],'cells.log')
        top=root/'project/rtl/control_v1/control_system.sv';bench=root/'project/experiments/control_v1/test_system.cpp'
        r['inputs'][str(top)]=sha(top);r['inputs'][str(bench)]=sha(bench)
        compiler='/public/home/yuzelu/opt/eda/verilator-5.042/bin/verilator'
        hierarchy=[]
        if a.hierarchical:
            marked=[];proof={}
            for name,path in zip(tops,views):
                original=Path(path).read_text()
                pattern=r'(\bmodule\s+'+re.escape(name)+r'\s*\([^;]*;)' 
                changed,count=re.subn(pattern,r'\1\n/*verilator hier_block*/',original)
                assert count==1,(name,count)
                assert changed.replace('\n/*verilator hier_block*/','',1)==original
                target=a.out/(name+'-hierarchical.v');target.write_text(changed);marked.append(target)
                proof[name]=dict(original=str(path),original_sha256=sha(path),marked=str(target),marked_sha256=sha(target),
                                 only_compiler_partition_comment_added=True)
            (a.out/'hierarchical-inputs.json').write_text(json.dumps(proof,indent=2)+'\n')
            views=marked;hierarchy=['--hierarchical','--hierarchical-threads','16']
        run([compiler,'--cc','--exe','--build','-j','16','-Wno-fatal','--top-module','control_system','--Mdir',a.out/'obj',
             '--output-split','12000','--output-split-cfuncs','150','--output-groups','0','--x-initial','unique','--x-assign','unique',
             *hierarchy,'-CFLAGS','-std=c++17 -O1',top,*views,a.out/'cells.v',bench],'build.log')
        def simulate(pair):
            mode,seed=pair
            name='initial-'+str(mode)+'-'+str(seed)+'.json'
            run([a.out/'obj/Vcontrol_system','+verilator+rand+reset+'+str(mode),'+verilator+seed+'+str(seed)],name)
            result=json.loads((a.out/name).read_text());assert result['passed'] and result['real_compositions']==3 and result['cpu_tensor_moves']==0
            return name,result
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
            results=dict(pool.map(simulate,[(1,162),(2,162),(2,163)]))
        assert len({json.dumps(v,sort_keys=True) for v in results.values()})==1
        r.update(passed=True,actual_final_leaf_count=len(views),leaves=tops,initial_results=results,
                 scope='Three true externally-fed programs using all selected final leaf physical-functional views. No new RTL replacement, no R. Zero-delay function only; combined final geometry/RC/STA/PG/clock/reset still separate.')
    finally:
        r['outputs']={str(f.relative_to(a.out)):sha(f) for f in a.out.glob('*.log')}
        (a.out/'receipt.json').write_text(json.dumps(r,indent=2)+'\n')
if __name__=='__main__':main()
