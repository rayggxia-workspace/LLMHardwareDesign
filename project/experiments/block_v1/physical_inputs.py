"""Prepare exact mapped leaf sources and port/constraint inventories, no P&R."""
import concurrent.futures
import hashlib
import json
from pathlib import Path


def prepare(root,out,cpus,run,compatible=False):
    assert cpus>=2
    original=out.parents[2]/'block-v1-20261027-004/tasks/map-c8-full'
    receipt=json.loads((original/'receipt.json').read_text())
    bundle=json.loads((root/'bundle-manifest.json').read_text())
    assert receipt['passed'] is True
    for entry in bundle['files']:
        if entry['path'].startswith('project/rtl/'):assert entry['sha256']==receipt['inputs'][entry['path']]
    assert hashlib.sha256((original/'mapped.json').read_bytes()).hexdigest()==receipt['outputs']['mapped.json']
    budget=json.loads((root/'project/experiments/block_v1/physical-budget.json').read_text())
    mapped_source=original/'mapped.json'
    if compatible:
        from structural_view import unsigned
        data=json.loads(mapped_source.read_text())
        proof=unsigned(data)
        mapped_source=out/'unsigned-metadata.json'
        mapped_source.write_text(json.dumps(data)+'\n')
        del data
        (out/'unsigned-metadata-proof.json').write_text(json.dumps(proof,indent=2)+'\n')
    def export(top):
        script='read_json '+str(mapped_source)+'\nhierarchy -check -top '+top+'\n'
        script+='write_verilog -noattr -noexpr '+('-norename 'if compatible else'')+top+'.v\nwrite_json '+top+'.json\n'
        if compatible:
            script+='design -reset\nread_liberty -lib '+str(TOOLS_LIB(root))+'\nread_verilog '+top+'.v\nhierarchy -check -top '+top+'\nwrite_json '+top+'-reparsed.json\n'
        (out/(top+'.ys')).write_text(script)
        run(['yosys','-s',top+'.ys'],top+'.log')
        modules=json.loads((out/(top+'.json')).read_text())['modules']
        if compatible:
            from structural_view import compare
            observed=json.loads((out/(top+'-reparsed.json')).read_text())
            result=compare({'modules':modules},observed)
            changed=False
            for module in observed['modules'].values():
                if module.get('attributes',{}).get('blackbox'):continue
                for cell in module.get('cells',{}).values():
                    bits=next((v for v in cell['connections'].values()if v),None)
                    if bits:
                        previous=bits[0];bits[0]='1'if previous!='1'else'0'
                        try:
                            try:compare({'modules':modules},observed)
                            except AssertionError:changed=True
                        finally:bits[0]=previous
                        assert changed,'Structural receiver accepted an altered cell-pin bit'
                        break
                if changed:break
            assert changed
            result['single_pin_bit_negative_rejected']=True
            (out/(top+'-structural-proof.json')).write_text(json.dumps(result,indent=2)+'\n')
        ports=modules[top]['ports']
        assert ports['clk']['direction']=='input' and len(ports['clk']['bits'])==1
        # Exact bit names are canonical before any candidate chooses XY.
        bits=[]
        for name,port in ports.items():
            assert port['direction']in ('input','output')
            for index,bit in enumerate(port['bits']):
                bits.append(dict(port=name,index=index+port.get('offset',0),direction=port['direction'],net_bit=bit))
        for bit in bits:bit['role']='clock'if bit['port']=='clk'else'data_or_control'
        ports_path=out/(top+'-ports.json');ports_path.write_text(json.dumps(bits,indent=2)+'\n')
        from constraints import generate as constraints
        sdc=constraints(budget)
        (out/(top+'.sdc')).write_text(sdc)
        return dict(top=top,port_bits=len(bits),inputs=sum(p['direction']=='input'for p in bits),
                    outputs=sum(p['direction']=='output'for p in bits),netlist_sha256=hashlib.sha256((out/(top+'.v')).read_bytes()).hexdigest(),
                    source_mapping_receipt_sha256=hashlib.sha256((original/'receipt.json').read_bytes()).hexdigest(),budget=budget['leaves'][top])
    with concurrent.futures.ThreadPoolExecutor(max_workers=2)as pool:leaves=list(pool.map(export,budget['leaves']))
    (out/'physical-inputs.json').write_text(json.dumps(dict(schema='block-v1-physical-inputs/1',leaves=leaves,
          qualification='Prepared exact mapped sources and SDC only; no floorplan, placement, routing or timing pass'),indent=2)+'\n')


def TOOLS_LIB(root):
    return Path('/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib')
