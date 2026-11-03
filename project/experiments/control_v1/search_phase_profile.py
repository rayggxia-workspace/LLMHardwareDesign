"""Bounded software search diagnosis. Never a final route or physical receipt."""
import argparse,hashlib,json,os,subprocess,time
from pathlib import Path


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser();p.add_argument('--config',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    assert os.environ.get('SLURM_JOB_ID')and len(os.sched_getaffinity(0))==16
    config=json.loads(a.config.read_text());assert config['schema']=='bounded-phase7-profile/1'and len(config['trials'])==16
    assert 60<=config['max_seconds']<=1200
    a.out.mkdir(parents=True,exist_ok=False);receipt=dict(passed=False,stage='bounded-search-phase-diagnostic-only',whole_system_qualified=False,route_qualified=False,inputs={},trials=[])
    active={};logs={}
    def bind(p,digest=None):
        p=Path(p);value=sha(p);assert digest is None or digest==value;receipt['inputs'][str(p)]=value;return p
    try:
        bind(a.config);bind(__file__);source=bind(config['source_cpp'],config['source_cpp_sha256']);original=source.read_text();changed=original;insertions=[]
        def after(needle,extra):
            nonlocal changed
            assert changed.count(needle)==1
            changed=changed.replace(needle,needle+extra,1);insertions.append((needle,extra))
        after('#include <algorithm>\n', '#include <chrono>\n')
        after(' bool complete=false;uint64_t previous_conflicts=size;', '\n uint64_t diagnostic_pops=0;')
        after('  for(int n:order){\n', '''   bool diagnostic_active=iteration==7&&number>=1200;uint64_t diagnostic_base=diagnostic_pops;
   if(diagnostic_active){bool skip=iteration&&negotiated_priority&&all_of(trees[n].begin(),trees[n].end(),[&](int v){return usage[v]<=1;});
    if(!skip)cout<<"{\\"diagnostic_event\\":\\"net_start\\",\\"round\\":"<<iteration<<",\\"routed_before\\":"<<number<<",\\"net\\":\\""<<names[n]<<"\\",\\"wire_limited\\":"<<(n<locked_count&&wire_limits[n]>=0?"true":"false")<<",\\"search_weight\\":"<<search_weight<<",\\"monotonic_ms\\":"<<chrono::duration_cast<chrono::milliseconds>(chrono::steady_clock::now().time_since_epoch()).count()<<"}"<<endl;
   }
''')
        after('    while(!q.empty()){\n     auto item=q.top();', '''
     if(diagnostic_active){++diagnostic_pops;if((diagnostic_pops-diagnostic_base)%1000000==0){
      cout<<"{\\"diagnostic_event\\":\\"ordinary_heap_progress\\",\\"round\\":"<<iteration<<",\\"net\\":\\""<<names[n]<<"\\",\\"heap_pops\\":"<<diagnostic_pops-diagnostic_base<<",\\"search_weight\\":"<<search_weight<<"}"<<endl;
      if(diagnostic_pops-diagnostic_base>=2000000)throw runtime_error("diagnostic-only heap-pop bound reached");
     }}
''')
        after('   trees[n]=move(tree);for(int v:trees[n])++usage[v];++number;', '''
   if(diagnostic_active)cout<<"{\\"diagnostic_event\\":\\"net_end\\",\\"round\\":"<<iteration<<",\\"net\\":\\""<<names[n]<<"\\",\\"routed_after\\":"<<number<<",\\"ordinary_heap_pops\\":"<<diagnostic_pops-diagnostic_base<<",\\"monotonic_ms\\":"<<chrono::duration_cast<chrono::milliseconds>(chrono::steady_clock::now().time_since_epoch()).count()<<"}"<<endl;
''')
        recovered=changed
        for needle,extra in reversed(insertions):
            assert recovered.count(needle+extra)==1;recovered=recovered.replace(needle+extra,needle,1)
        assert recovered.encode()==source.read_bytes()
        cpp=a.out/'profile.cpp';cpp.write_text(changed);receipt['generated_source_sha256']=sha(cpp);receipt['instrumentation_removal_exact']=True
        for name in ['resource_search.h']:
            bind(source.with_name(name))
        binary=a.out/'profile';command=['g++','-std=c++17','-O2','-I'+str(source.parent),str(cpp),'-o',str(binary)]
        with(a.out/'compile.log').open('w')as f:subprocess.run(command,stdout=f,stderr=subprocess.STDOUT,check=True)
        receipt['compile_command']=command;receipt['binary_sha256']=sha(binary)
        with(a.out/'oracle.json').open('w')as f:subprocess.run([str(binary),'--self-test'],stdout=f,check=True)
        assert json.loads((a.out/'oracle.json').read_text())['passed']
        mem={k:int(v.split()[0])*1024 for k,v in(line.split(':',1)for line in Path('/proc/meminfo').read_text().splitlines())}
        required=(16*2*1.2+16)*1024**3;assert mem['MemAvailable']>required
        receipt['memory_admission']=dict(required_bytes=required,available_bytes=mem['MemAvailable'],active_trials=16,forecast_gib_per_trial=2)
        for i,row in enumerate(config['trials']):
            inp=bind(row['input'],row['input_sha256']);bind(row['reference_prefix'],row['reference_prefix_sha256']);text=inp.read_text();header,body=text.split('\n',1);fields=header.split();assert fields[4]=='80'and fields[5]=='128';fields[4]='8'
            folder=a.out/('trial-'+str(i));folder.mkdir();target=folder/'input.txt';target.write_text(' '.join(fields)+'\n'+body)
            logs[i]=(folder/'profile.log').open('w');cmd=[str(binary),str(target),str(folder/'not-a-qualified-route.txt'),'--resource-labels=8000000','--critical-first']
            process=subprocess.Popen(cmd,stdout=logs[i],stderr=subprocess.STDOUT);active[i]=dict(process=process,started=time.monotonic(),last_diagnostic=None,last_observed=time.monotonic(),command=cmd)
        while active:
            for i,row in list(active.items()):
                process=row['process'];folder=a.out/('trial-'+str(i));path=folder/'profile.log'
                with path.open('rb')as f:f.seek(max(0,path.stat().st_size-8192));tail=f.read().decode(errors='replace').splitlines()
                events=[]
                for line in tail:
                    try:
                        item=json.loads(line)
                        if 'diagnostic_event'in item:events.append(item)
                    except ValueError:pass
                last=events[-1]if events else None
                if last!=row['last_diagnostic']:row['last_diagnostic']=last;row['last_observed']=time.monotonic()
                reason=None
                if time.monotonic()-row['started']>=config['max_seconds']:reason='Bounded diagnostic wall limit; not routing infeasibility'
                elif last and last['diagnostic_event']=='net_start'and time.monotonic()-row['last_observed']>=45:reason='Same observed net start for45seconds; software phase diagnosis only'
                rc=process.poll()
                if rc is None and reason:process.terminate();rc=process.wait()
                if rc is not None:
                    logs[i].close();del active[i];raw=path.read_bytes();reference=Path(config['trials'][i]['reference_prefix']).read_bytes();assert raw.startswith(reference),'Instrumented first7round prefix differs'
                    receipt['trials'].append(dict(trial=i,returncode=rc,termination_reason=reason,last_diagnostic=last,last_diagnostic_events=events[-5:],exact_original_first7round_prefix=True,prefix_bytes=len(reference),log_sha256=sha(path),command=row['command']))
            if active:time.sleep(.5)
        assert len(receipt['trials'])==16
        receipt.update(passed=True,scope='Bounded instrumented software replay only: all16 actual original trial inputs and complete first7round stdout prefixes must match exactly. At round7 and routed>=1200 record net category and ordinary heap pops; stop only own children at explicit2million-pop/45second-same-net/finite-wall diagnostic bounds. Not a route, infeasibility proof, geometry, timing or system qualification.')
    finally:
        for row in active.values():
            process=row['process']
            if process.poll()is None:process.terminate()
        for row in active.values():row['process'].wait()
        for f in logs.values():
            if not f.closed:f.close()
        (a.out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')


if __name__=='__main__':main()
