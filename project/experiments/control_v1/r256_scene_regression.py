"""Actual Yosys boundary extraction and rejection tests for the R256 scene."""
import copy,json,os,re,subprocess
from pathlib import Path
from r256_scene import BASE,SPECIAL,SCHEMA,fixed_top,validate_base,placement_pin_maps,phase_placement


def run(a,root,sha):
    assert os.environ.get('SLURM_JOB_ID')and len(os.sched_getaffinity(0))<=16
    a.out=a.out.resolve();a.out.mkdir(parents=True,exist_ok=False)
    receipt=dict(passed=False,whole_system_qualified=False,inputs={},commands=[])
    def bind(p):receipt['inputs'][str(p)]=sha(p)
    try:
        for name in ['r256_scene.py','r256_scene_regression.py','boundary_links.py','reset_link_banks.py','test_reset_link_banks.py']:bind(Path(__file__).with_name(name))
        original=root/'project/rtl/control_v1/control_system.sv';bind(original)
        fixed=a.out/'fixed.sv';fixed.write_text(fixed_top(original.read_bytes()))
        control=list(sorted((root/'project/rtl/control_v1').glob('*.sv')))
        sources=[p for p in control if p!=original]
        sources+=list(sorted((root/'project/rtl/block_feed_v1').glob('*.sv')))
        sources+=[root/'project/rtl/block_v2'/(name+'.sv')for name in ['block_v2_m','block_v2_n','block_v2_n_group','block_v2_e','block_v2_g']]
        sources+=[root/'project/rtl/block_v1/transaction6k.sv']
        sources+=list(sorted((root/'project/rtl/r_local_state').glob('*.sv')))
        for p in sources:bind(p)
        for label,top in [('original',original),('fixed',fixed)]:
            script=a.out/(label+'.ys')
            script.write_text('read_verilog -sv -lib '+' '.join(map(str,sources))+'\nread_verilog -sv '+str(top)+'\nhierarchy -check -top control_system\nproc\nopt_clean\ncheck -assert\nwrite_json '+str(a.out/(label+'.json'))+'\n')
            with(a.out/(label+'.log')).open('w')as f:q=subprocess.run(['yosys','-s',script],stdout=f,stderr=subprocess.STDOUT)
            receipt['commands'].append(dict(label=label,returncode=q.returncode,log=label+'.log',sha256=sha(a.out/(label+'.log'))));assert q.returncode==0,label
        old=json.loads((a.out/'original.json').read_text())['modules']['control_system']
        new=json.loads((a.out/'fixed.json').read_text())['modules']['control_system']
        assert set(old['cells'])==set(new['cells'])==set(BASE)
        assert old['ports']==new['ports'],'Top interfaces or actual net IDs changed'
        for name,cell in new['cells'].items():
            before=old['cells'][name]
            assert cell['type']==BASE[name]and not cell['parameters']
            assert cell['connections']==before['connections']and cell['port_directions']==before['port_directions'],name
            if name in SPECIAL:
                parent,param,value,variant=SPECIAL[name]
                assert before['type']==parent
                assert set(before['parameters'])=={param}and int(before['parameters'][param],2)==value
            else:assert before['type']==cell['type']and not before['parameters']
        validate_base(BASE,set(BASE.values()))
        rejected=[]
        def reject(label,action):
            try:action()
            except AssertionError:rejected.append(label)
            else:raise AssertionError('Accepted invalid scene: '+label)
        reject('changed-source',lambda:fixed_top(original.read_bytes()+b'\n'))
        for label,change in [
            ('missing-R',lambda d:d.pop('macro_r')),
            ('unassigned-extra-state',lambda d:d.update(hidden_state='control_status_r8')),
            ('wrong-C-endpoints',lambda d:d.update(controller='control_c')),
            ('wrong-arbitration',lambda d:d.update(s_port='control_s_arbiter')),
            ('wrong-reset',lambda d:d.update(reset_distribution='control_reset_distribution')),
            ('missing-eighth-queue',lambda d:d.pop('queue_7')),
            ('unqualified-R1024-type',lambda d:d.update(macro_r='r_stream_1024'))]:
            bad=dict(BASE);change(bad);reject(label,lambda bad=bad:validate_base(bad,set(bad.values())))
        reject('extra-unused-type',lambda:validate_base(BASE,set(BASE.values())|{'hidden_logic'}))
        from boundary_links import validate,insert
        graph=dict(instances=dict(BASE),instance_count=29,scene=SCHEMA)
        manifest=dict(leaves={t:{}for t in set(BASE.values())},scene=SCHEMA)
        validate(manifest,graph)
        bad=copy.deepcopy(graph);bad['scene']='six-native';reject('wrong-scene-marker',lambda:validate(manifest,bad))
        # Closed316-Link8 case: preserve the original exact contraction check
        # and exercise all25 dedicated reset banks, including actual R owner.
        from test_reset_link_banks import COUNTS
        module=dict(ports={},cells={name:dict(type=top,parameters={},port_directions=dict(clk='input',reset='input'),connections=dict(clk=[1],reset=[100]))for name,top in BASE.items()})
        reset=module['cells']['reset_distribution'];reset['port_directions']['reset_out']='output';reset['connections']['reset_out']=list(range(100,153))
        linked=copy.deepcopy(manifest);linked['leaves']['control_link8']={};pins={};next_bit=200
        for source,count in sorted(COUNTS.items()):
            cell=module['cells'][source];port='task_data'if source=='controller'else'dout'if source=='s_port'else'rsp_data'
            bits=list(range(next_bit,next_bit+count*8));next_bit+=count*8
            cell['port_directions'][port]='output';cell['connections'][port]=bits
            sink=module['cells']['endpoint_7'];name='from_'+source;sink['port_directions'][name]='input';sink['connections'][name]=bits[:]
            linked['leaves'][cell['type']]['die_um']=[1000,1000]
            pins[cell['type']]={port+'['+str(i)+']':dict(xy_um=[0,i])for i in range(len(bits))}
        proof=insert(module,linked,pins,['macro_1','macro_2','macro_3','macro_4','macro_t','macro_r'],['controller:task_data','s_port:dout'])
        assert len(proof['links'])==proof['new_state_bits']==316 and proof['payload_register_bits']==0
        linked_graph=dict(instances={n:c['type']for n,c in module['cells'].items()},instance_count=345,scene=SCHEMA,boundary_links=proof,connections={})
        for bank in proof['reset_banks']['banks']:
            linked_graph['connections'][str(bank['bit'])]=dict(driver=dict(instance='reset_distribution',pin='reset_out['+str(bank['output'])+']',direction='output'),sinks=[dict(instance=n,pin='reset',direction='input')for n in bank['link_instances']])
        validate(linked,linked_graph)
        bad=copy.deepcopy(linked_graph);bad['boundary_links']['payload_register_bits']=1;reject('hidden-payload-register',lambda:validate(linked,bad))
        bad=copy.deepcopy(linked_graph);bad['boundary_links']['reset_banks']['extra_state_bits']=1;reject('hidden-reset-pipeline',lambda:validate(linked,bad))
        phase_manifest=dict(scene=SCHEMA,leaves={'r_stream_local':dict(placement_phase_um=[.095,.07])})
        native_pins={'r_stream_local':{'clk':dict(xy_um=[24,80]),'VDD':dict(xy_um=[8,12])}}
        before=copy.deepcopy(native_pins);cost_pins=placement_pin_maps(phase_manifest,native_pins)
        positions=phase_placement(phase_manifest,BASE,{'macro_r':[128,256]})
        assert native_pins==before and positions=={'macro_r':[128.095,256.07]}
        assert phase_placement(phase_manifest,BASE,positions,reused=True)==positions
        for name,pin in native_pins['r_stream_local'].items():
            actual=[pin['xy_um'][i]+positions['macro_r'][i]for i in range(2)]
            expected=[cost_pins['r_stream_local'][name]['xy_um'][i]+[128,256][i]for i in range(2)]
            assert all(abs(x-y)<1e-8 for x,y in zip(actual,expected))
            assert all(abs((actual[i]-[.095,.07][i])/4-round((actual[i]-[.095,.07][i])/4))<1e-7 for i in range(2))
        bad=copy.deepcopy(phase_manifest);bad['leaves']['r_stream_local']['placement_phase_um']=[0,0]
        reject('wrong-native-R-placement-phase',lambda:placement_pin_maps(bad,native_pins))
        reject('double-phase-application',lambda:phase_placement(phase_manifest,BASE,positions))
        reject('unphased-R-reuse',lambda:phase_placement(phase_manifest,BASE,{'macro_r':[128,256]},reused=True))
        receipt.update(passed=True,actual_boundary_instances=29,actual_physical_types=22,
            exact_all_ports_and_connections=True,link_contraction_passed=True,rejected=rejected,
            exact_rigid_R_signal_and_PG_phase=True,
            scope='Actual RTL boundary elaboration and closed scene/ownership negative controls only; no physical, numerical, final-cell or system qualification.')
    finally:
        receipt['outputs']={p.name:sha(p)for p in a.out.iterdir()if p.is_file()}
        (a.out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
