"""Prepare exact mapped leaf sources and port/constraint inventories, no P&R."""
import concurrent.futures
import hashlib
import json
from pathlib import Path


def prepare(root,out,cpus,run):
    assert cpus>=2
    original=out.parents[2]/'block-v1-20261027-004/tasks/map-c8-full'
    receipt=json.loads((original/'receipt.json').read_text())
    bundle=json.loads((root/'bundle-manifest.json').read_text())
    assert receipt['passed'] is True
    for entry in bundle['files']:
        if entry['path'].startswith('project/rtl/'):assert entry['sha256']==receipt['inputs'][entry['path']]
    assert hashlib.sha256((original/'mapped.json').read_bytes()).hexdigest()==receipt['outputs']['mapped.json']
    budget=json.loads((root/'project/experiments/block_v1/physical-budget.json').read_text())
    def export(top):
        script='read_json '+str(original/'mapped.json')+'\nhierarchy -check -top '+top+'\n'
        script+='write_verilog -noattr -noexpr '+top+'.v\nwrite_json '+top+'.json\n'
        (out/(top+'.ys')).write_text(script)
        run(['yosys','-s',top+'.ys'],top+'.log')
        modules=json.loads((out/(top+'.json')).read_text())['modules']
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
        sdc='create_clock -name core -period %g [get_ports clk]\n'%budget['clock_ns']
        sdc+='set_clock_uncertainty %g [get_clocks core]\n'%budget['uncertainty_ns']
        sdc+='set_clock_transition %g [get_clocks core]\n'%budget['clock_transition_ns']
        sdc+='set data_inputs [remove_from_collection [all_inputs] [get_ports clk]]\n'
        sdc+='set_input_delay -clock core -max %g $data_inputs\n'%budget['input_delay_max_ns']
        sdc+='set_input_delay -clock core -min %g $data_inputs\n'%budget['input_delay_min_ns']
        sdc+='set_output_delay -clock core -max %g [all_outputs]\n'%budget['output_delay_max_ns']
        sdc+='set_output_delay -clock core -min %g [all_outputs]\n'%budget['output_delay_min_ns']
        sdc+='set_driving_cell -lib_cell %s -pin %s $data_inputs\n'%(budget['input_driver']['cell'],budget['input_driver']['pin'])
        sdc+='set_load %g [all_outputs]\n'%budget['output_load_pf']
        (out/(top+'.sdc')).write_text(sdc)
        return dict(top=top,port_bits=len(bits),inputs=sum(p['direction']=='input'for p in bits),
                    outputs=sum(p['direction']=='output'for p in bits),netlist_sha256=hashlib.sha256((out/(top+'.v')).read_bytes()).hexdigest(),
                    source_mapping_receipt_sha256=hashlib.sha256((original/'receipt.json').read_bytes()).hexdigest(),budget=budget['leaves'][top])
    with concurrent.futures.ThreadPoolExecutor(max_workers=2)as pool:leaves=list(pool.map(export,budget['leaves']))
    (out/'physical-inputs.json').write_text(json.dumps(dict(schema='block-v1-physical-inputs/1',leaves=leaves,
          qualification='Prepared exact mapped sources and SDC only; no floorplan, placement, routing or timing pass'),indent=2)+'\n')
