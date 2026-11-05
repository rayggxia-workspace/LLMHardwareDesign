from pathlib import Path
p=Path('project/experiments/control_v1/native_prefix_snapshot.py')
p.write_bytes(r'''"""Observe failed native-stage paths with exact replay; never route acceptance."""
import collections
import concurrent.futures
import hashlib
import json
import re
import subprocess
import time
from pathlib import Path
from router_conflict_snapshot import inputs, inspect


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def filtered(raw):
    return b''.join(line for line in raw.splitlines(keepends=True) if b'routing_phase_event' not in line)


def worker(case, binary, out, flags, parents):
    folder=Path(out)/('case-'+str(case['case']));folder.mkdir()
    original=Path(case['input']);assert sha(original)==case['input_sha256']
    header,nets,limits=inputs(original);locked=header[6]
    assert header[2]==11149 and locked==1229 and header[4]==80
    reference=Path(case['native_log']);main_reference=Path(case['main_log'])
    assert sha(reference)==case['native_log_sha256'] and sha(main_reference)==case['main_log_sha256']
    native_rounds=[json.loads(l)for l in reference.read_text().splitlines()if l.startswith('{')and '"conflict_nodes"'in l]
    assert len(native_rounds)==80 and native_rounds[-1]['round']==79 and native_rounds[-1]['conflict_nodes']>0
    assert b'native-prefix negotiation did not converge'in main_reference.read_bytes()
    inp=folder/'input.txt';inp.write_bytes(original.read_bytes());output=folder/'output.txt';log=folder/'router.log'
    with log.open('w')as f:
        process=subprocess.run([binary,str(inp),str(output)]+flags,stdout=f,stderr=subprocess.STDOUT)
    assert process.returncode==1 and not output.exists()
    actual_native=Path(str(output)+'.native-prefix.log')
    assert filtered(actual_native.read_bytes())==filtered(reference.read_bytes()),'Native replay changed search decisions/counters'
    assert log.read_bytes()==main_reference.read_bytes(),'Native replay changed original failure/ordinary-stage state'
    subset={n:nets[n]for n in list(nets)[:locked]};assert all(limits[n]>=0 for n in subset)
    dump=Path(str(output)+'.native-failed-paths.txt')
    diagnostic=inspect(dump,subset,*header[:2],limits,parents)
    for key in ['conflict_nodes','excess_occupancy','occupied_cells','summed_tree_vertices','grid_cell_capacity']:
        assert diagnostic[key]==native_rounds[-1][key]
    # Inspect every native point against ALL original11149 landing owners,
    # including ordinary pins which are not routed during this phase.
    nx,ny=header[:2];plane=nx*ny
    pin_owner={y*nx+x:name for name,ends in nets.items()for x,y in ends}
    assert len(pin_owner)==sum(map(len,nets.values()))
    occupants=collections.defaultdict(list)
    with dump.open()as f:
        assert int(f.readline())==locked
        for name in subset:
            actual,count=f.readline().split();assert actual==name;points=set()
            for _ in range(int(count)):
                row=list(map(int,f.readline().split()));assert len(row)==1+3*row[0]
                for i in range(1,len(row),3):
                    x,y,layer=row[i:i+3];v=layer*plane+y*nx+x;points.add(v)
                    if layer==0:assert pin_owner.get(v,name)==name,('Foreign physical landing',name,v)
            for v in points:occupants[v].append(name)
        assert not f.read().strip()
    conflicts=[dict(x=v%nx,y=(v%plane)//nx,layer=v//plane,nets=names)
               for v,names in sorted(occupants.items())if len(names)>1]
    assert len(conflicts)==diagnostic['conflict_nodes']
    assert sum(len(c['nets'])-1 for c in conflicts)==diagnostic['excess_occupancy']
    diagnostic.update(case=case['case'],original_input=str(original),original_input_sha256=sha(original),
                      all11149_landings_preserved=True,all_landing_owners_checked=True,
                      native_log_filtered_byte_exact=True,main_failure_log_byte_exact=True,
                      snapshot_path=str(dump),snapshot_bytes=dump.stat().st_size,snapshot_sha256=sha(dump),
                      conflict_cells=conflicts,whole_system_qualified=False,route_qualified=False)
    (folder/'diagnostic.json').write_text(json.dumps(diagnostic,indent=2)+'\n')
    return diagnostic


def run(config_path,out):
    out=Path(out);out.mkdir();config=json.loads(Path(config_path).read_text())
    receipt=dict(passed=False,stage='native-prefix-failed-path-diagnostic-only',route_qualified=False,
                 whole_system_qualified=False,inputs={str(config_path):sha(config_path)},outputs={},started_at=time.time())
    try:
        assert config['schema']=='control162-native-prefix-snapshot-v1' and len(config['cases'])==16
        assert len({c['case']for c in config['cases']})==16
        for row in config['sources']:
            assert sha(row['path'])==row['sha256'];receipt['inputs'][row['path']]=row['sha256']
        source=Path(config['kernel']);assert str(source)in receipt['inputs']
        original=source.read_text();code=original;transforms=[]
        for name in re.findall(r'^#include "([^"]+)"$',original,re.M):
            old='#include "'+name+'"';path=source.parent/name;assert str(path)in receipt['inputs']
            new='#include "'+str(path)+'"';assert code.count(old)==1;code=code.replace(old,new);transforms.append((old,new))
        marker=' native_log.release();\n if(!complete)throw'
        assert code.count(marker)==1
        observation=r""" if(!complete&&native_stage){
  ofstream snapshot(string(argv[2])+".native-failed-paths.txt");snapshot<<locked_count<<'\n';
  for(int n=0;n<locked_count;++n){snapshot<<names[n]<<' '<<branches[n].size()<<'\n';
   for(auto&branch:branches[n]){snapshot<<branch.size();for(int v:branch){auto c=coord(v);snapshot<<' '<<c[0]<<' '<<c[1]<<' '<<c[2];}snapshot<<'\n';}}
  if(!snapshot)throw runtime_error("cannot write native failed-path diagnostic");
 }
"""
        code=code.replace(marker,observation+marker);restored=code.replace(observation+marker,marker)
        for old,new in reversed(transforms):restored=restored.replace(new,old)
        assert restored==original
        observed=out/'observation-kernel.cpp';observed.write_text(code);binary=out/'diagnostic-router'
        subprocess.run(['g++','-std=c++17','-O2',str(observed),'-o',str(binary)],check=True)
        oracle=json.loads(subprocess.check_output([str(binary),'--self-test']))
        assert oracle['passed']and oracle['independent_pin_access_matching_checks']==200
        flags=['--resource-labels=8000000','--critical-first','--ordinary-zero-pattern',
               '--weighted-bidirectional','--trace-routing-phases','--ordinary-endpoint-escape',
               '--ordinary-zero-maze=16384','--native-prefix-first','--pin-access=after-native']
        assert config['flags']==flags
        graph=Path(config['graph']);assert str(graph)in receipt['inputs'];g=json.loads(graph.read_text())
        assert len(g['instances'])==345 and 'macro_r'in g['instances']
        link_parent={r['instance']:r['source_instance']for r in g['boundary_links']['links']}
        parents={'net_'+bit:sorted({link_parent.get(e['instance'],e['instance'])for e in[c['driver'],*c['sinks']]})for bit,c in g['connections'].items()}
        assert len(parents)==11147
        with concurrent.futures.ProcessPoolExecutor(max_workers=16)as pool:
            futures=[pool.submit(worker,c,str(binary),str(out),flags,parents)for c in config['cases']]
            results=[f.result()for f in futures]
        report=out/'native-prefix-diagnostics.json';report.write_text(json.dumps(dict(cases=results,whole_system_qualified=False),indent=2)+'\n')
        provenance=out/'observation-provenance.json';provenance.write_text(json.dumps(dict(original_source=str(source),original_sha256=sha(source),observation_sha256=sha(observed),normalized_source_byte_exact=True,changes='Absolute include paths and a failed native-prefix path dump after original80 rounds, before original nonconvergence failure. No search state, decisions, original input, CLI, failure or physical gate changes.'),indent=2)+'\n')
        receipt.update(passed=True,binary_sha256=sha(binary),distance_oracle=oracle,
                       scope='Sixteen actual complete80round failed native-prefix replays. All11149 original nets and physical landings retained in search; only1229 routed native trees dumped after original failure decision. Exact original filtered native logs and unfiltered original main/failure logs required. Independent edge/via/flood/wire and all24760 foreign landing checks, exact conflicting cells/nets reported. No global route or geometry/PG/RC/timing qualification.')
        for p in [report,provenance]:receipt['outputs'][p.name]=sha(p)
    finally:
        receipt['finished_at']=time.time();(out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    return receipt
'''.encode())
