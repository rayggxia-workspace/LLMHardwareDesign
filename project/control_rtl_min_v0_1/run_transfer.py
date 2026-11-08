"""Compile real LC RTL and run RAW16 finite-store/ACK control campaigns."""
import argparse,copy,json,os,pathlib,sys
import run as common
import transfer_check
HERE=pathlib.Path(__file__).resolve().parent
image=common.check_cycles.image; codec=common.codec


def main():
    p=argparse.ArgumentParser(); p.add_argument('--verilator',default='verilator'); p.add_argument('--out',required=True,type=pathlib.Path)
    a=p.parse_args(); out=a.out.resolve(); out.mkdir(parents=True,exist_ok=True); env=dict(os.environ)
    bundles=json.loads((HERE.parent/'control_image_v0_1/bundles.json').read_text(encoding='utf-8'))['bundles']
    b=next(b for b in bundles if b['manifest']['bundle']=='receiver_first_16B')
    images={'producer':bytes.fromhex(b['images_hex']['local0']),'consumer':bytes.fromhex(b['images_hex']['local1'])}
    def variant(name,base,scalar=None,write_reg=0,read_reg=0,address=None):
        parsed=image.parse_image(images[base],'local'); program=copy.deepcopy(parsed['program'])
        records=copy.deepcopy({k:v for k,v in parsed['records'].items() if k!='instruction'})
        new_id=500+len(images); records['task'][0]['program_image_id']=new_id
        for ins in program:
            if ins['op']=='L_MOVI': ins['a']=write_reg; ins['x']=scalar
            elif ins['op']=='L_REPORT': ins['b']=read_reg
        if address is not None: records['object'][0]['base_bytes']=address
        images[name]=image.assemble_image('local',program,records,new_id,parsed['header']['resource_mask'])
    variant('scalar_full','consumer',0xfedcba98)
    variant('scalar_R7','consumer',0x12345678,7,7)
    variant('initial_R0','consumer',0x12345678,7,0)
    variant('consumer_last_word','consumer',1,address=16368)
    # Producer has no MOVI/REPORT; its program is retained verbatim.
    variant('producer_last_word','producer',address=16368)
    def case(name,which,block,commands,reports,read=0,write=16,expected=0,pc=0xffffffff,**kw):
        return dict(name=name,image=which,block=block,commands=commands,reports=reports,read_bytes=read,write_bytes=write,
                    expected=expected,error_pc=pc,**kw)
    ch=codec.unpack_record('image_header',images['consumer'][:128]); ph=codec.unpack_record('image_header',images['producer'][:128])
    tf=ch['transfer_offset']; io=ch['instruction_offset']
    cases=[case('producer','producer',0,2,0,16),case('producer_fast','producer',0,2,0,16,stall=0),
        case('producer_reuse','producer',0,4,0,16,calls=2),case('consumer','consumer',1,1,1),
        case('consumer_fast','consumer',1,1,1,stall=0),case('consumer_reuse','consumer',1,2,2,calls=2),
        case('scalar_full','scalar_full',1,1,1,scalar=0xfedcba98),case('scalar_R7','scalar_R7',1,1,1,scalar=0x12345678),
        case('initial_R0','initial_R0',1,1,1,scalar=0),case('last_SRAM_word','consumer_last_word',1,1,1),
        case('producer_last_word','producer_last_word',0,2,0,16),
        case('wrong_RX_response','consumer',1,1,1,mode=1,poison=1),
        case('missing_TX_ACK','producer',0,2,0,mode=2,poison=1),
        case('RX_write_error','consumer',1,1,0,write=0,expected=9,pc=1,mode=3),
        case('TX_error_after_ACK','producer',0,2,0,16,expected=9,pc=3,mode=5),
        case('CANCEL_held_READY','consumer',1,1,1,expected=11,pc=4,mode=6),
        case('bad_transfer_version','consumer',1,0,0,write=0,expected=5,pc=1,fault_addr=tf,fault_xor=1),
        case('bad_transfer_count','consumer',1,0,0,write=0,expected=5,pc=1,fault_addr=tf,fault_xor=48<<96),
        case('bad_transfer_port','consumer',1,0,0,write=0,expected=5,pc=1,fault_addr=tf,fault_xor=1<<40),
        case('bad_transfer_route','consumer',1,0,0,write=0,expected=5,pc=1,fault_addr=tf+16,fault_xor=3<<32),
        case('bad_transfer_invocation','consumer',1,0,0,write=0,expected=5,pc=1,fault_addr=tf+16,fault_xor=3<<96),
        case('zero_transfer_record','consumer',1,0,0,write=0,expected=5,pc=1,zero_begin=tf,zero_end=tf+64),
        case('TX_without_declared_output','consumer',1,0,0,write=0,expected=4,pc=1,fault_addr=io+16,fault_xor=(0x42^0x43)<<120),
        case('TX_before_RX_valid','producer',0,0,0,write=0,expected=7,pc=1,fault_addr=ph['instruction_offset']+16,fault_xor=(0x42^0x43)<<120),
        case('DROP_before_ACK','producer',0,1,0,expected=7,pc=2,fault_addr=ph['instruction_offset']+32,
             fault_xor=int.from_bytes(images['producer'][ph['instruction_offset']+32:ph['instruction_offset']+48],'little')^(0x49<<120)),
    ]
    compile_reports=[]; executables={}
    for block in [0,1]:
        obj=out/('obj_'+str(block))
        cmd=[a.verilator,'--binary','--timing','--top-module','tb_lc_transfer','-GBLOCK='+str(block),'-I'+str(HERE),
            '--Mdir',obj,'-j','4','-o','sim',HERE/'lc_min_controller.sv',HERE/'tb_lc_transfer.sv']
        log=common.run(cmd,out,env,out/('compile_'+str(block)+'.log')); executables[block]=obj/'sim'
        compile_reports.append(dict(block=block,command=[str(x) for x in cmd],log_sha256=common.sha(log.encode())))
    results=[]; traces={}; event_map={}
    for c in cases:
        name=c['name']; data=images[c['image']]; h=codec.unpack_record('image_header',data[:128]); block=c['block']
        task=codec.pack_record('task_message',dict(kind=0,target_block=block,job_id=7,epoch=1,task_sequence=1,
            completion_token=1-block,task_descriptor=0,program_image_id=h['program_image_id'],topology_id=h['topology_id']))
        ip,tp=out/(name+'.mem'),out/(name+'.task')
        ip.write_text('\n'.join('{:032x}'.format(int.from_bytes(data[i:i+16],'little')) for i in range(0,len(data),16))+'\n',encoding='ascii')
        tp.write_text('{:0128x}\n'.format(int.from_bytes(task,'little')),encoding='ascii')
        run=[executables[block],'+IMAGE='+str(ip),'+TASK='+str(tp),'+WORDS='+str(len(data)//16),'+STALL='+str(c.get('stall',2))]
        for field,arg in [('mode','MODE'),('calls','CALLS'),('commands','COMMANDS'),('reports','REPORTS'),('read_bytes','READ_BYTES'),
            ('write_bytes','WRITE_BYTES'),('expected','EXPECTED'),('error_pc','ERROR_PC'),('scalar','SCALAR'),('poison','POISON'),
            ('fault_addr','FAULT_ADDR'),('zero_begin','ZERO_BEGIN'),('zero_end','ZERO_END')]:
            if field in c: run.append('+'+arg+'='+str(c[field]))
        run.append('+FAULT_XOR={:032x}'.format(c.get('fault_xor',0)))
        log=common.run(run,out,env,out/(name+'.log'))
        if 'PASS ' not in log: raise ValueError('missing RAW16 TB PASS '+name)
        trace=common.decode_trace(log); trace['block']=block; traces[name]=trace; events=transfer_check.data_events(log); event_map[name]=events
        checked=transfer_check.check(trace,c,data,events)
        results.append(dict(case=c,actual_rtl_simulation=True,checker=checked,cycles=len(trace['cycles']),observations=common.observations(trace),
            data_events=sum(len(v) for v in events.values()),input_image_sha256=common.sha(data),input_task_sha256=common.sha(task),
            log_sha256=common.sha(log.encode()),command=[str(x) for x in run]))
        print(name,'PASS',len(trace['cycles']),'cycles',flush=True)
    mutants=transfer_check.mutations(traces,{c['name']:c for c in cases},images,event_map)
    report=dict(schema='local-RAW16-transfer-rtl-runs/0.1',evidence='actual_SV_LC_with_bounded_16KiB_SRAM_and_link_peers',
        results=results,compile_reports=compile_reports,mutation_checks=mutants,dut_sha256=common.sha((HERE/'lc_min_controller.sv').read_bytes()),
        tools=dict(verilator=common.run([a.verilator,'--version'],out,env).splitlines()[0],python=sys.version),
        images={k:dict(bytes=len(v),sha256=common.sha(v)) for k,v in images.items()},
        register_value_readback_tested=True,logical_object_data_valid_tested=True,native_S_tested=False,
        full_Block_tested=False,mother_RTL_tested=False,physical_tested=False,RX_close_tested=False)
    (out/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('PASS',len(results),'RAW16 RTL runs;',len(mutants),'mutations rejected')


if __name__=='__main__': main()
