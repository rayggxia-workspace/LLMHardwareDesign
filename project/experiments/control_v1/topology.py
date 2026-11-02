"""Extract the actual system boundary graph from accepted leaf pin inventories."""
import argparse,collections,hashlib,json,os,re,subprocess
from pathlib import Path

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def main():
    p=argparse.ArgumentParser();p.add_argument('--manifest',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    assert os.environ.get('SLURM_JOB_ID') and len(os.sched_getaffinity(0))<=16
    a.out.mkdir(parents=True,exist_ok=False);root=Path(__file__).resolve().parents[3]
    manifest=json.loads(a.manifest.read_text());inputs={str(a.manifest):sha(a.manifest)};stubs=[];pin_maps={}
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
    script='read_verilog -lib '+str(a.out/'leaves.v')+'\nread_verilog -sv '+str(top)+'\nhierarchy -check -top control_system\nproc\nopt_clean\ncheck -assert\nwrite_json '+str(a.out/'topology.json')+'\n'
    (a.out/'extract.ys').write_text(script)
    with (a.out/'extract.log').open('w') as f:q=subprocess.run(['yosys','-s',a.out/'extract.ys'],stdout=f,stderr=subprocess.STDOUT)
    assert q.returncode==0
    data=json.loads((a.out/'topology.json').read_text());module=data['modules']['control_system'];nets=collections.defaultdict(list);instances={}
    for name,cell in module['cells'].items():
        assert cell['type'] in manifest['leaves'],('Unassigned active logic',name,cell['type'])
        assert cell['type']!='block_v1_r';instances[name]=cell['type']
        for port,bits in cell['connections'].items():
            for index,bit in enumerate(bits):
                pin=port+'['+str(index)+']' if port+'['+str(index)+']' in pin_maps[cell['type']] else port
                assert pin in pin_maps[cell['type']],(name,pin)
                assert isinstance(bit,int),('Constant boundary requires a qualified physical owner',name,pin,bit)
                nets[bit].append(dict(instance=name,pin=pin,direction=cell['port_directions'][port]))
    for port,row in module['ports'].items():
        for index,bit in enumerate(row['bits']):
            if isinstance(bit,int):nets[bit].append(dict(instance='TOP',pin=port+('['+str(index)+']' if len(row['bits'])>1 else ''),direction='output' if row['direction']=='input' else 'input'))
    assert len(instances)==25 and len(manifest['leaves'])==19,('Missing physical instance',instances)
    connected={}
    for bit,ends in nets.items():
        drivers=[e for e in ends if e['direction']=='output'];sinks=[e for e in ends if e['direction']=='input']
        assert len(drivers)<=1,('Multiple actual drivers',bit,ends)
        if sinks:assert len(drivers)==1,('Undriven boundary',bit,ends)
        if drivers and sinks:connected[str(bit)]=dict(driver=drivers[0],sinks=sinks)
    result=dict(passed=True,instances=instances,connections=connected,connected_nets=len(connected),instance_count=len(instances),
                inputs=inputs,source_sha256=sha(Path(__file__)),no_unassigned_active_logic=True,R_instantiated=False,
                scope='Exact RTL boundary graph with actual qualified-leaf pin inventories. No placement/routing/timing qualification.')
    (a.out/'boundary-graph.json').write_text(json.dumps(result,indent=2)+'\n')
if __name__=='__main__':main()
