"""Metadata-only payload/fanout oracle on an actual extracted topology.

This is not simulation, timing, physical qualification or a replacement for
the three actual final-cell programs. Run with qualified manifest/topology.
"""
import argparse,copy,json,random
from pathlib import Path
from boundary_links import insert,validate,verilog


def main():
    p=argparse.ArgumentParser();p.add_argument('--manifest',type=Path,required=True);p.add_argument('--topology',type=Path,required=True);a=p.parse_args()
    manifest=json.loads(a.manifest.read_text());original=json.loads(a.topology.read_text())['modules']['control_system']
    pins={top:{p['pin']:p for p in json.loads(Path(row['pins']).read_text())['pins']}for top,row in manifest['leaves'].items()}
    module=copy.deepcopy(original);proof=insert(module,manifest,pins,['macro_s'])
    assert proof['new_state_bits']>0 and proof['payload_register_bits']==0
    for row in proof['links']:
        assert module['cells'][row['instance']]['connections']['reset']==original['cells']['macro_s']['connections']['reset']
        assert module['cells'][row['instance']]['connections']['clk']==original['cells']['macro_s']['connections']['clk']
    rng=random.Random(162);bits={b for c in original['cells'].values()for bs in c['connections'].values()for b in bs}
    def equivalent(candidate,values):
        values=values.copy()
        for row in proof['links']:
            cell=candidate['cells'][row['instance']]
            for before,after in zip(cell['connections']['in_data'],cell['connections']['out_data']):values[after]=values[before]
        for name,cell in original['cells'].items():
            for port,bs in cell['connections'].items():
                if cell['port_directions'][port]=='input':
                    if [values[b]for b in bs]!=[values[b]for b in candidate['cells'][name]['connections'][port]]:return False
        for name,port in original['ports'].items():
            if port['direction']=='output'and[values[b]for b in port['bits']]!=[values[b]for b in candidate['ports'][name]['bits']]:return False
        return True
    values={bit:rng.getrandbits(64)for bit in bits};assert equivalent(module,values)
    # A lane permutation is a real bus corruption, and the oracle must reject
    # it. Distinct 64-bit source tokens also exercise every fanout sink.
    corrupted=copy.deepcopy(module);row=next(r for r in proof['links']if len(r['lanes'])==8)
    connections=corrupted['cells'][row['instance']]['connections'];connections['in_data'][0],connections['in_data'][1]=connections['in_data'][1],connections['in_data'][0]
    assert not equivalent(corrupted,values),'Payload oracle failed to detect a lane swap'
    graph=dict(instances={n:c['type']for n,c in module['cells'].items()},instance_count=len(module['cells']),boundary_links=proof)
    validate(manifest,graph)
    corrupted=copy.deepcopy(graph);corrupted['instances']['hidden_state']='unqualified_control';corrupted['instance_count']+=1
    try:validate(manifest,corrupted)
    except AssertionError:pass
    else:raise AssertionError('Unqualified state owner was accepted')
    text=verilog(module);assert text.count('control_link8 ')==proof['new_state_bits']
    print(json.dumps(dict(passed=True,scope='Metadata-only independent payload/fanout and negative corruption checks; no hardware qualification',
        base_instances=26,new_link_instances=proof['new_state_bits'],payload_source_bits=sum(len(r['lanes'])for r in proof['links']),
        random_token_width=64,lane_swap_rejected=True,hidden_state_rejected=True)))


if __name__=='__main__':main()
