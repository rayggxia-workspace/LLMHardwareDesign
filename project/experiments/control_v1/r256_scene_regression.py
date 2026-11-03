"""Actual Yosys boundary extraction and rejection tests for the R256 scene."""
import copy,json,os,re,subprocess
from pathlib import Path
from r256_scene import BASE,SPECIAL,SCHEMA,fixed_top,validate_base


def run(a,root,sha):
    assert os.environ.get('SLURM_JOB_ID')and len(os.sched_getaffinity(0))<=16
    a.out=a.out.resolve();a.out.mkdir(parents=True,exist_ok=False)
    receipt=dict(passed=False,whole_system_qualified=False,inputs={},commands=[])
    def bind(p):receipt['inputs'][str(p)]=sha(p)
    try:
        for name in ['r256_scene.py','r256_scene_regression.py','boundary_links.py']:bind(Path(__file__).with_name(name))
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
        # Exercise actual link insertion and exact contraction for the new R
        # owner; one real output plus seven padding lanes, no payload register.
        module=dict(ports={},cells={name:dict(type=top,parameters={},port_directions=dict(clk='input',reset='input'),connections=dict(clk=[1],reset=[2]))for name,top in BASE.items()})
        module['cells']['macro_r']['connections']['rsp_data']=[3]
        module['cells']['macro_r']['port_directions']['rsp_data']='output'
        module['cells']['endpoint_7']['connections']['rsp_data']=[3]
        module['cells']['endpoint_7']['port_directions']['rsp_data']='input'
        linked=copy.deepcopy(manifest);linked['leaves']['control_link8']={};linked['leaves']['r_stream_local']['die_um']=[1000,1000]
        proof=insert(module,linked,{'r_stream_local':{'rsp_data':{'xy_um':[0,100]}}},['macro_r'])
        assert len(proof['links'])==proof['new_state_bits']==1 and proof['payload_register_bits']==0
        linked_graph=dict(instances={n:c['type']for n,c in module['cells'].items()},instance_count=30,scene=SCHEMA,boundary_links=proof)
        validate(linked,linked_graph)
        bad=copy.deepcopy(linked_graph);bad['boundary_links']['payload_register_bits']=1;reject('hidden-payload-register',lambda:validate(linked,bad))
        receipt.update(passed=True,actual_boundary_instances=29,actual_physical_types=22,
            exact_all_ports_and_connections=True,link_contraction_passed=True,rejected=rejected,
            scope='Actual RTL boundary elaboration and closed scene/ownership negative controls only; no physical, numerical, final-cell or system qualification.')
    finally:
        receipt['outputs']={p.name:sha(p)for p in a.out.iterdir()if p.is_file()}
        (a.out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
