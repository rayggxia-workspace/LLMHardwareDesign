"""Extract the actual system boundary graph from accepted leaf pin inventories."""
import argparse,collections,hashlib,json,os,re,subprocess
from pathlib import Path

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def main():
    p=argparse.ArgumentParser();p.add_argument('--manifest',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--link-native-output',action='append',choices=['macro_s','macro_1','macro_2','macro_3','macro_4','macro_t','macro_r'])
    p.add_argument('--r256-scene',action='store_true',help='Exact PR168 R256 scene, with separately qualified fixed-parameter control blocks')
    p.add_argument('--split-output-fanout',action='append',choices=['s_port:dout','controller:task_data','controller:task_last'])
    p.add_argument('--audit-existing',type=Path)
    p.add_argument('--audit-spec',type=Path)
    a=p.parse_args()
    assert os.environ.get('SLURM_JOB_ID') and len(os.sched_getaffinity(0))<=16
    if a.audit_existing:
        assert a.audit_spec and not a.link_native_output and not a.split_output_fanout
        from topology_receipt import audit
        return audit(a)
    assert not a.audit_spec
    a.out.mkdir(parents=True,exist_ok=False);root=Path(__file__).resolve().parents[3]
    manifest=json.loads(a.manifest.read_text());inputs={str(a.manifest):sha(a.manifest)};stubs=[];pin_maps={}
    if a.r256_scene:
        from r256_scene import fixed_top,SCHEMA,BASE
        helper=Path(__file__).with_name('r256_scene.py');inputs[str(helper)]=sha(helper)
        assert manifest.get('scene')==SCHEMA
        assert set(manifest['leaves'])==set(BASE.values())|{'control_link8'}
    else:assert 'r_stream_local'not in manifest['leaves']and 'macro_r'not in(a.link_native_output or [])
    internal_s=manifest['leaves']['block_feed_s_macro'].get('S_internal_drive')
    if internal_s:
        assert 'macro_s' not in (a.link_native_output or []),'User selected drive inside S; external S links are not the final repair'
        assert internal_s['owner']=='block_feed_s_macro M1-M10' and internal_s['all_four_gates_fresh']
        proof=internal_s['actual_final_driver_proof']
        assert proof['passed'] and proof['output_count']==788 and proof['all_actual_drivers_BUF_X32']
        assert sha(proof['table'])==proof['table_sha256'];inputs[proof['table']]=proof['table_sha256']
    helper=Path(__file__).with_name('boundary_links.py');inputs[str(helper)]=sha(helper)
    for top,row in manifest['leaves'].items():
        path=Path(row['pins']);assert sha(path)==row['pins_sha256'];inputs[str(path)]=sha(path)
        netlist=Path(row['final_files']['6_final.v']['path']);assert sha(netlist)==row['final_files']['6_final.v']['sha256']
        inputs[str(netlist)]=sha(netlist)
        declarations={m.group(4):m.group(1) for m in re.finditer(r'(?m)^\s*(input|output)\s+(?:\[(\d+):(\d+)\]\s+)?(\S+)\s*;',netlist.read_text())}
        assert declarations,top
        plan=json.loads(path.read_text());ports=collections.defaultdict(dict);pin_maps[top]={p['pin']:p for p in plan['pins']}
        for pin in plan['pins']:
            m=re.fullmatch(r'([A-Za-z_][A-Za-z_0-9]*)(?:\[(\d+)\])?',pin['pin']);assert m,pin['pin']
            name,index=m.groups();direction=declarations[name]
            if 'direction' in pin:assert pin['direction'].lower()==direction
            ports[name][int(index) if index else None]=direction
        stubs.append('(* blackbox *) module '+top+'('+','.join(ports)+');')
        for name,bits in ports.items():
            directions=set(bits.values());assert len(directions)==1 and directions<={'input','output'}
            if None in bits:assert len(bits)==1;width=''
            else:
                assert set(bits)==set(range(max(bits)+1)),(top,name)
                width='['+str(max(bits))+':0] '
            stubs.append(next(iter(directions))+' '+width+name+';')
        stubs.append('endmodule')
    (a.out/'leaves.v').write_text('\n'.join(stubs)+'\n')
    top=root/'project/rtl/control_v1/control_system.sv';inputs[str(top)]=sha(top)
    if a.r256_scene:
        target=a.out/'r256-fixed-top.sv';target.write_text(fixed_top(top.read_bytes()));top=target
    script='read_verilog -lib '+str(a.out/'leaves.v')+'\nread_verilog -sv '+str(top)+'\nhierarchy -check -top control_system\nproc\nopt_clean\ncheck -assert\nwrite_json '+str(a.out/'topology.json')+'\n'
    (a.out/'extract.ys').write_text(script)
    with (a.out/'extract.log').open('w') as f:q=subprocess.run(['yosys','-s',a.out/'extract.ys'],stdout=f,stderr=subprocess.STDOUT)
    assert q.returncode==0
    data=json.loads((a.out/'topology.json').read_text());module=data['modules']['control_system'];nets=collections.defaultdict(list);instances={}
    links=None
    if a.link_native_output or a.split_output_fanout:
        from boundary_links import insert,verilog
        helper=Path(__file__).with_name('boundary_links.py');inputs[str(helper)]=sha(helper)
        (a.out/'original-topology.json').write_text(json.dumps(data,indent=2)+'\n')
        links=insert(module,manifest,pin_maps,a.link_native_output or [],a.split_output_fanout or [])
        (a.out/'topology.json').write_text(json.dumps(data,indent=2)+'\n')
        (a.out/'combined.v').write_text(verilog(module))
    for name,cell in module['cells'].items():
        assert cell['type'] in manifest['leaves'],('Unassigned active logic',name,cell['type'])
        instances[name]=cell['type']
        for port,bits in cell['connections'].items():
            for index,bit in enumerate(bits):
                pin=port+'['+str(index)+']' if port+'['+str(index)+']' in pin_maps[cell['type']] else port
                assert pin in pin_maps[cell['type']],(name,pin)
                assert isinstance(bit,int),('Constant boundary requires a qualified physical owner',name,pin,bit)
                nets[bit].append(dict(instance=name,pin=pin,direction=cell['port_directions'][port]))
    for port,row in module['ports'].items():
        for index,bit in enumerate(row['bits']):
            if isinstance(bit,int):nets[bit].append(dict(instance='TOP',pin=port+('['+str(index)+']' if len(row['bits'])>1 else ''),direction='output' if row['direction']=='input' else 'input'))
    assert len(instances)==(29 if a.r256_scene else 26)+(len(links['links'])if links else 0),('Missing physical instance',instances)
    assert instances.get('reset_distribution')==('control_reset_distribution_r28'if a.r256_scene else'control_reset_distribution')
    connected={}
    for bit,ends in nets.items():
        drivers=[e for e in ends if e['direction']=='output'];sinks=[e for e in ends if e['direction']=='input']
        assert len(drivers)<=1,('Multiple actual drivers',bit,ends)
        if sinks:assert len(drivers)==1,('Undriven boundary',bit,ends)
        if drivers and sinks:connected[str(bit)]=dict(driver=drivers[0],sinks=sinks)
    result=dict(passed=True,instances=instances,connections=connected,connected_nets=len(connected),instance_count=len(instances),
                inputs=inputs,source_sha256=sha(Path(__file__)),no_unassigned_active_logic=True,
                R_instantiated=any(top in ('block_v1_r','block_v2_r','r_stream_local')for top in instances.values()),
                scope='Exact RTL boundary graph with actual qualified-leaf pin inventories. No placement/routing/timing qualification.')
    if links:result['boundary_links']=links
    if a.r256_scene:result['scene']=SCHEMA
    if internal_s:
        result['S_internal_drive']=internal_s
        result['S_external_link_instances']=0
        result['state_ownership_change']='S adds only combinational output stages. No new S registers or payload cycle. External S Link8 isolation registers are absent; all remaining Link8 state remains owned by its named physical instance.'
    from boundary_links import validate
    validate(manifest,result)
    (a.out/'boundary-graph.json').write_text(json.dumps(result,indent=2)+'\n')
    # This is a completed graph-generation receipt, never physical acceptance.
    receipt=dict(passed=True,operation='topology-generation',inputs=inputs,
        source_sha256=sha(Path(__file__)),
        original_graph_sha256=sha(a.out/'boundary-graph.json'),
        no_unassigned_active_logic=True,whole_system_qualified=False,
        native_leaf_qualified=False,
        outputs={name:sha(a.out/name)for name in
                 ['boundary-graph.json','topology.json','combined.v','leaves.v']},
        scope='Actual completed extraction and ownership validation of this graph only; all physical, numerical and system gates remain mandatory.')
    (a.out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
if __name__=='__main__':main()
