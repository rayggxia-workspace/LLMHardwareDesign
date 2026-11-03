"""Observe current final-cell programs; reuse immutable compiled design assets only.

This is zero-delay event evidence, never upper geometry/PG/RC qualification.
"""
import concurrent.futures,hashlib,json,os,subprocess,time
from pathlib import Path


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb')as f:
        for chunk in iter(lambda:f.read(1048576),b''):h.update(chunk)
    return h.hexdigest()


def instrument(original):
    # Insert only observational statements/includes. Removing these exact
    # insertions must recover the complete original benchmark byte for byte.
    changes=[]
    def after(needle,addition):
        nonlocal original
        assert original.count(needle)==1,needle
        original=original.replace(needle,needle+addition,1);changes.append((needle,addition))
    after('#include <cstdlib>', '\n#include <fstream>\n#include <string>')
    after('static uint64_t checks=0,cycles=0;', r"""
static unsigned event_case=0,event_run=0;
static void event_trace(const char* event,const std::string& fields=""){
 static std::ofstream out(std::getenv("CONTROL_TASK_TRACE"));
 out<<"{\"schema\":\"control-task-events/1\",\"cycle\":"<<cycles<<",\"case\":"<<event_case
    <<",\"run\":"<<event_run<<",\"event\":\""<<event<<"\""<<fields<<"}\n";
 if(!out)std::exit(2);
}
static std::string event_data(const VlWide<4>& data){
 std::string s=",\"data\":[";
 for(unsigned n=0;n<4;++n){if(n)s+=",";s+=std::to_string(data[n]);}return s+"]";
}
""")
    after('Sim(){', '++event_case;event_run=0;event_trace("case_begin");')
    after('unsigned offset(uint64_t a){', '')
    after('if(v.rvalid && v.rready){', r'event_trace("R",",\"id\":"+std::to_string(r)+",\"last\":"+std::to_string(v.rlast)+event_data(v.rdata));')
    after('if(v.bvalid && v.bready)', r'event_trace("B",",\"id\":"+std::to_string(b));if(v.bvalid && v.bready)')
    after('if(v.arvalid && v.arready){', r'event_trace("AR",",\"id\":"+std::to_string(v.arid)+",\"addr\":"+std::to_string(v.araddr)+",\"beats\":"+std::to_string(v.arlen+1));')
    after('if(v.awvalid && v.awready){', r'event_trace("AW",",\"id\":"+std::to_string(v.awid)+",\"addr\":"+std::to_string(v.awaddr)+",\"beats\":"+std::to_string(v.awlen+1));')
    after('if(v.wvalid && v.wready){', r'event_trace("W",",\"last\":"+std::to_string(v.wlast)+",\"strb\":"+std::to_string(v.wstrb)+event_data(v.wdata));')
    after('void run(const std::vector<Desc>&ds,const std::vector<unsigned>&order){', r"""
  ++event_run;event_trace("program_begin",",\"descriptors\":"+std::to_string(ds.size())+",\"order_count\":"+std::to_string(order.size()));
  for(unsigned d=0;d<ds.size();++d){std::string fields=",\"index\":"+std::to_string(d)+",\"words\":[";
   for(unsigned w=0;w<8;++w){if(w)fields+=",";fields+=std::to_string(ds[d][w]);}event_trace("descriptor",fields+"]");}
  for(unsigned n=0;n<order.size();++n)event_trace("planned_order",",\"position\":"+std::to_string(n)+",\"descriptor\":"+std::to_string(order[n]));
""")
    after('cfg(4,1);', 'event_trace("program_started");')
    after('"all real transactions drained");', r'event_trace("program_end",",\"ended\":"+std::to_string(v.ended)+",\"fault\":"+std::to_string(v.fault)+",\"busy\":"+std::to_string(v.busy));')
    after('int main(int argc,char**argv){', '')
    # Empty anchors above also check the expected harness shape.
    result=original
    for needle,addition in reversed(changes):
        assert result.count(needle+addition)==1
        result=result.replace(needle+addition,needle,1)
    return original,result


def audit(path,expected_cycles):
    cases={};active=None;last_cycle=-1;counts={};reads={};writes=[];responses=set();programs=[]
    for line in Path(path).open():
        row=json.loads(line);assert row['schema']=='control-task-events/1'
        cycle=row['cycle'];case=row['case'];run=row['run'];event=row['event']
        assert last_cycle<=cycle<=expected_cycles;last_cycle=cycle;counts[event]=counts.get(event,0)+1
        if event=='case_begin':
            assert active is None and not reads and not writes and not responses and case not in cases
            cases[case]=[]
        elif event=='program_begin':
            assert active is None and not reads and not writes and not responses
            active=dict(case=case,run=run,begin=cycle,descriptors=row['descriptors'],order_count=row['order_count'],descriptor_indices=[],order=[],AR=0,AW=0,R=0,W=0,B=0)
        else:
            assert active is not None and(case,run)==(active['case'],active['run'])
            if event=='descriptor':
                assert len(row['words'])==8 and all(0<=n<2**32 for n in row['words'])
                active['descriptor_indices'].append(row['index'])
            elif event=='planned_order':
                assert row['position']==len(active['order'])and 0<=row['descriptor']<active['descriptors'];active['order'].append(row['descriptor'])
            elif event=='program_started':
                assert 'started'not in active;active['started']=cycle
                assert active['descriptor_indices']==list(range(active['descriptors']))and len(active['order'])==active['order_count']
            elif event=='AR':
                assert row['id']not in reads and 1<=row['beats']<=16 and 0x1200000000<=row['addr']<0x1200040000
                reads[row['id']]=row['beats'];active['AR']+=1
            elif event=='R':
                assert row['id']in reads and row['last']==(reads[row['id']]==1)and len(row['data'])==4
                reads[row['id']]-=1
                if not reads[row['id']]:del reads[row['id']]
                active['R']+=1
            elif event=='AW':
                assert row['id']not in responses and 1<=row['beats']<=16 and 0x1200000000<=row['addr']<0x1200040000
                writes.append([row['id'],row['beats']]);active['AW']+=1
            elif event=='W':
                assert writes and row['last']==(writes[0][1]==1)and len(row['data'])==4 and 0<=row['strb']<65536
                writes[0][1]-=1
                if not writes[0][1]:responses.add(writes.pop(0)[0])
                active['W']+=1
            elif event=='B':
                assert row['id']in responses;responses.remove(row['id']);active['B']+=1
            elif event=='program_end':
                assert 'started'in active and not reads and not writes and not responses and not row['busy']and(row['ended']or row['fault'])
                assert active['AW']==active['B'];active.update(end=cycle,ended=row['ended'],fault=row['fault'])
                programs.append(active);cases[case].append(len(programs)-1);active=None
            else:raise AssertionError(event)
    assert active is None and set(cases)==set(range(1,15))and all(cases.values())
    assert all(not p['fault']and p['ended']for p in programs if p['case']<=8)
    assert all(p['fault']for p in programs if p['case']>8)
    return dict(passed=True,observed_events=counts,actual_cases=cases,programs=programs,last_event_cycle=last_cycle,
                external_protocol_independently_replayed=True,descriptors_are_host_plan_not_internal_dispatch=True,
                per_cycle_waveform=False,zero_delay=True,whole_system_qualified=False)


def run(config_path,out,receipt):
    config=json.loads(Path(config_path).read_text());assert config['schema']=='control162-program-event-trace/1'
    assert os.environ.get('SLURM_JOB_ID')and len(os.sched_getaffinity(0))<=16
    def bind(path,digest=None):
        path=Path(path);value=sha(path);assert digest is None or value==digest;receipt['inputs'][str(path)]=value;return path
    bind(config_path);bind(__file__)
    old_path=bind(config['original_receipt'],config['original_receipt_sha256']);old=json.loads(old_path.read_text());root=old_path.parent
    audit_path=bind(config['original_independent_audit'],config['original_independent_audit_sha256']);old_audit=json.loads(audit_path.read_text())
    assert old['passed']and old['scene']=='r256-seven-native/2'and old['physical_instances']==345 and old['actual_final_leaf_count']==23 and old['real_program_count']==8
    assert old_audit['passed']and old_audit['initial_results']==old['initial_results']
    for path,digest in old['inputs'].items():bind(path,digest)
    for path,digest in old_audit['inputs'].items():bind(path,digest)
    benches=[p for p in old['inputs']if p.endswith('/test_system.cpp')];assert len(benches)==1
    bench=Path(benches[0]).read_text();changed,recovered=instrument(bench);assert recovered==bench and recovered.encode()==Path(benches[0]).read_bytes()
    generated=out/'test_system_events.cpp';generated.write_text(changed);receipt['inputs'][str(generated)]=sha(generated)
    (out/'instrumentation.json').write_text(json.dumps(dict(original_bench=benches[0],original_sha256=sha(benches[0]),generated_sha256=sha(generated),removing_only_observational_insertions_recovers_original=True,checks_and_test_vectors_unchanged=True,scope='External top AXI handshakes, host planned descriptors, and actual program end/fault only. No internal dispatch capture or per-cycle waveforms.'),indent=2)+'\n')
    obj=root/'obj';assets=[obj/n for n in ['verilated.o','verilated_dpi.o','verilated_threads.o','Vcontrol_system__ALL.a']]
    for p in assets:bind(p)
    for p in obj.glob('*.h'):bind(p)
    for n in ['build.log','actual-qualified-top.v','hierarchical-inputs.json']:bind(root/n,old.get('outputs',{}).get(n))
    include=Path('/public/home/yuzelu/opt/eda/verilator-5.042/share/verilator/include')
    for p in include.glob('*.h'):bind(p)
    commands=[]
    def execute(command,log,env=None):
        with(out/log).open('w')as f:q=subprocess.run(list(map(str,command)),stdout=f,stderr=subprocess.STDOUT,env=env)
        commands.append(dict(command=list(map(str,command)),returncode=q.returncode,log=log,sha256=sha(out/log)));assert q.returncode==0,log
    compiler='/usr/bin/g++';bind(compiler)
    receipt['compiler_version']=subprocess.check_output([compiler,'--version']).decode().splitlines()[0]
    execute([compiler,'-std=c++17','-O1','-I'+str(obj),'-I'+str(include),'-I'+str(include/'vltstd'),'-DVERILATOR=1','-DVM_COVERAGE=0','-DVM_SC=0','-DVM_TIMING=0','-DVM_TRACE=0','-DVM_TRACE_FST=0','-DVM_TRACE_VCD=0','-DVM_TRACE_SAIF=0','-c',generated,'-o',out/'test_system_events.o'],'compile.log')
    execute([compiler,out/'test_system_events.o',*assets,'-pthread','-lpthread','-latomic','-o',out/'Vcontrol_system_events'],'link.log')
    receipt['inputs'][str(out/'Vcontrol_system_events')]=sha(out/'Vcontrol_system_events')
    def simulate(pair):
        mode,seed=pair;name='initial-'+str(mode)+'-'+str(seed);env=dict(os.environ);env['CONTROL_TASK_TRACE']=str(out/(name+'.jsonl'))
        execute([out/'Vcontrol_system_events','+verilator+rand+reset+'+str(mode),'+verilator+seed+'+str(seed)],name+'.json',env)
        result=json.loads((out/(name+'.json')).read_text());assert result==old['initial_results'][name+'.json']
        observed=audit(out/(name+'.jsonl'),result['cycles']);observed.update(result=result,trace_sha256=sha(out/(name+'.jsonl')))
        (out/(name+'-audit.json')).write_text(json.dumps(observed,indent=2)+'\n');return name,observed
    with concurrent.futures.ThreadPoolExecutor(max_workers=3)as pool:results=dict(pool.map(simulate,[(1,162),(2,162),(2,163)]))
    (out/'trace-audit.json').write_text(json.dumps(dict(passed=True,results=results,compiled_model_assets_now_sha_bound=True,original_build_source_and_log_bound=True,original_build_time_asset_hashes_were_not_recorded=True,whole_system_qualified=False),indent=2)+'\n')
    receipt.update(passed=True,stage='actual-final-cell-program-event-trace-only',commands=commands,scope='Three actual initialization executions of unchanged original eight numerical programs and six rejection cases. Only observational C++ insertions; same345instance compiled model reused read-only with current asset hashes. All golden checks/cycles/results exact. External event protocol replay only; no per-cycle waveform, internal dispatch or full upper physical qualification.')
