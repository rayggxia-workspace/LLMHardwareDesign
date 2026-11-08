"""Server RTL: bounded RAW16 reservations, retirement and abort ownership."""
import argparse,json,os,pathlib,sys
import run as common
import object_check
HERE=pathlib.Path(__file__).resolve().parent
image=common.check_cycles.image
codec=common.codec


def main():
    p=argparse.ArgumentParser(); p.add_argument('--verilator',default='verilator'); p.add_argument('--out',required=True,type=pathlib.Path)
    a=p.parse_args(); out=a.out.resolve(); out.mkdir(parents=True,exist_ok=True); env=dict(os.environ)
    cmd=[a.verilator,'--binary','--timing','--top-module','tb_lc_object','-I'+str(HERE),'--Mdir',out/'obj_dir','-j','4','-o','sim',
        HERE/'lc_min_controller.sv',HERE/'tb_lc_object.sv']
    compiled=common.run(cmd,out,env,out/'compile.log')
    bundles=json.loads((HERE.parent/'control_image_v0_1/bundles.json').read_text(encoding='utf-8'))['bundles']
    clear=bytes.fromhex(next(b for b in bundles if b['manifest']['bundle']=='single_M_clear')['images_hex']['local0'])
    h=codec.unpack_record('image_header',clear[:128]); e=codec.unpack_record('execution',clear[h['execution_offset']:h['execution_offset']+128])
    programs={
        'open_drop':[dict(op='L_OPEN',a=0),dict(op='L_DROP',a=0),dict(op='L_END')],
        'open_M':[dict(op='L_OPEN',a=0),dict(op='L_EXEC',a=0,b=0,c=0),dict(op='L_WAIT',x=1),dict(op='L_DROP',a=0),dict(op='L_END')],
        'reopen':[dict(op='L_OPEN',a=0),dict(op='L_DROP',a=0),dict(op='L_OPEN',a=0),dict(op='L_DROP',a=0),dict(op='L_END')],
        'movi_open':[dict(op='L_MOVI',a=0,x=123),dict(op='L_OPEN',a=0),dict(op='L_DROP',a=0),dict(op='L_END')],
    }
    images={}
    for key,program in programs.items():
        resource=33 if key=='open_M' else 32
        task=dict(block_type=0,entry_pc=0,max_steps=32,required_resources=resource,program_image_id=301,
            topology_id=image.TOPOLOGY,native_abi_id=image.ABI,input_object_mask=0,output_object_mask=0)
        obj=dict(object_id=0,kind=0,base_bytes=256,capacity_bytes=16,format=4,object_version=1,length_bytes=16,native_abi_id=image.ABI)
        images[key]=image.assemble_image('local',program,dict(task=[task],object=[obj],execution=[e] if key=='open_M' else []),301,resource)
    def case(name,program='open_drop',expected=0,pc=0xffffffff,commands=0,**kw):
        return dict(name=name,program=program,expected=expected,error_pc=pc,commands=commands,**kw)
    data=images['open_drop']; h=codec.unpack_record('image_header',data[:128]); io=h['instruction_offset']; ob=h['object_offset']
    mex=codec.unpack_record('image_header',images['open_M'][:128])['execution_offset']
    cases=[case('open_drop'),case('open_M_wait_drop','open_M',commands=1),case('reopen','reopen'),
        case('object_reuse',recovery=1),case('MOVI_retirement','movi_open'),
        case('duplicate_OPEN',expected=7,pc=1,fault_addr=io+16,fault_xor=(0x49^0x40)<<120),
        case('END_live_object',expected=7,pc=1,fault_addr=io+16,fault_xor=(0x49^0x4f)<<120),
        case('DROP_inactive',expected=7,pc=0,fault_addr=io,fault_xor=(0x40^0x49)<<120),
        case('OPEN_bad_flags',expected=2,pc=0,fault_addr=io,fault_xor=1<<112),
        case('OPEN_bad_index',expected=5,pc=0,fault_addr=io,fault_xor=1<<104),
        case('object_bad_opcode',expected=1,pc=1,fault_addr=io+16,fault_xor=(0x49^0xfe)<<120),
        case('bad_object_ABI',expected=5,pc=0,fault_addr=ob+32,fault_xor=1),
        case('bad_object_format',expected=5,pc=0,fault_addr=ob+16,fault_xor=7),
        case('bad_object_version',expected=5,pc=0,fault_addr=ob+16,fault_xor=1<<32),
        case('bad_object_dynamic_base',expected=5,pc=0,fault_addr=ob+16,fault_xor=255<<64),
        case('bad_object_gap',expected=5,pc=0,fault_addr=ob+32,fault_xor=1<<32),
        case('bad_object_capacity',expected=5,pc=0,fault_addr=ob,fault_xor=48<<64),
        case('bad_object_length',expected=5,pc=0,fault_addr=ob+16,fault_xor=48<<96),
        case('object_out_of_range',expected=6,pc=0,fault_addr=ob,fault_xor=(256^16384)<<32),
        case('object_unaligned',expected=6,pc=0,fault_addr=ob,fault_xor=1<<32),
        case('zero_object_record',expected=5,pc=0,zero_begin=ob,zero_end=ob+64),
        case('zero_execution_record','open_M',expected=5,pc=1,zero_begin=mex,zero_end=mex+128),
        case('PM_object_error',expected=10,pc=0,fault_addr=ob,pm_error=1),
        case('cancel_object',expected=11,pc=1,cancel=1,cancel_pc=1),
        case('cancel_object_M','open_M',expected=11,pc=2,commands=1,cancel=1,cancel_pc=2),
        case('poison_object_M','open_M',commands=1,cancel=1,cancel_pc=2,poison=1,no_response=2),
        case('MOVI_bad_register','movi_open',expected=2,pc=0,fault_addr=io,fault_xor=8<<104),
    ]
    results=[]; traces={}
    for c in cases:
        name=c['name']; data=images[c['program']]; h=codec.unpack_record('image_header',data[:128])
        task=codec.pack_record('task_message',dict(kind=0,target_block=0,job_id=7,epoch=1,task_sequence=1,completion_token=0,
            task_descriptor=0,program_image_id=h['program_image_id'],topology_id=h['topology_id']))
        ip,tp=out/(name+'.mem'),out/(name+'.task')
        ip.write_text('\n'.join('{:032x}'.format(int.from_bytes(data[i:i+16],'little')) for i in range(0,len(data),16))+'\n',encoding='ascii')
        tp.write_text('{:0128x}\n'.format(int.from_bytes(task,'little')),encoding='ascii')
        run=[out/'obj_dir/sim','+IMAGE='+str(ip),'+TASK='+str(tp),'+WORDS='+str(len(data)//16),'+STALL=2']
        for field,arg in [('expected','EXPECTED'),('error_pc','ERROR_PC'),('commands','COMMANDS'),('fault_addr','FAULT_ADDR'),
            ('pm_error','PM_ERROR'),('zero_begin','ZERO_BEGIN'),('zero_end','ZERO_END'),('cancel','CANCEL'),('cancel_pc','CANCEL_PC'),('poison','POISON'),('no_response','NO_RESPONSE'),('recovery','RECOVERY')]:
            if field in c: run.append('+'+arg+'='+str(c[field]))
        run.append('+FAULT_XOR={:032x}'.format(c.get('fault_xor',0)))
        log=common.run(run,out,env,out/(name+'.log'))
        if 'PASS ' not in log: raise ValueError('missing TB PASS '+name)
        trace=common.decode_trace(log); traces[name]=trace; checked=object_check.check(trace,c,data)
        results.append(dict(case=c,actual_rtl_simulation=True,checker=checked,cycles=len(trace['cycles']),observations=common.observations(trace),
            input_image_sha256=common.sha(data),input_task_sha256=common.sha(task),log_sha256=common.sha(log.encode()),command=[str(x) for x in run]))
        print(name,'PASS',len(trace['cycles']),'cycles',flush=True)
    mutants=object_check.mutations(traces,{c['name']:c for c in cases},images)
    report=dict(schema='local-object-reservation-rtl-runs/0.1',evidence='actual_SV_DUT_PM_and_M_service_peers',
        results=results,mutation_checks=mutants,compile_command=[str(x) for x in cmd],compile_log_sha256=common.sha(compiled.encode()),
        dut_sha256=common.sha((HERE/'lc_min_controller.sv').read_bytes()),
        tools=dict(verilator=common.run([a.verilator,'--version'],out,env).splitlines()[0],python=sys.version),
        images={k:dict(bytes=len(v),sha256=common.sha(v)) for k,v in images.items()},
        object_slots=1,object_bytes=16,local_S_capacity_bound=16384,actual_S_data_tested=False,register_value_readback_tested=False,
        RX_TX_tested=False,full_block_tested=False,mother_rtl_tested=False,physical_tested=False)
    (out/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('PASS',len(results),'object RTL runs;',len(mutants),'mutations rejected')


if __name__=='__main__': main()
