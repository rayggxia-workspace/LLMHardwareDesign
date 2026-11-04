"""Actual bounded mother RTL against two independent finite child peers."""
import argparse,copy,json,os,pathlib,sys
import run as common
import mc_check
HERE=pathlib.Path(__file__).resolve().parent
codec=common.codec; image=common.check_cycles.image


def main():
    p=argparse.ArgumentParser(); p.add_argument('--verilator',default='verilator'); p.add_argument('--out',type=pathlib.Path,required=True)
    a=p.parse_args(); out=a.out.resolve(); out.mkdir(parents=True,exist_ok=True); env=dict(os.environ)
    bundles=json.loads((HERE.parent/'control_image_v0_1/bundles.json').read_text(encoding='utf-8'))['bundles']
    def original(name): return bytes.fromhex(next(b for b in bundles if b['manifest']['bundle']==name)['images_hex']['mother'])
    images={'single':original('empty_task'),'receiver':original('receiver_first_16B')}
    def variant(name,program):
        images[name]=image.assemble_image('mother',program,{},700+len(images),0)
    variant('movi',[dict(op='G_MOVI',a=7,x=0x12345678),dict(op='G_CALL',a=0,b=0,c=0),dict(op='G_WAIT',x=1),dict(op='G_END')])
    variant('two',[dict(op='G_CALL',a=1,b=0,c=0),dict(op='G_CALL',a=0,b=1,c=0),dict(op='G_WAIT',x=3),dict(op='G_END')])
    variant('target1',[dict(op='G_CALL',a=1,b=0,c=0),dict(op='G_WAIT',x=1),dict(op='G_END')])
    def case(name,which='single',calls=1,**kw): return dict(name=name,image=which,calls=calls,**kw)
    def fault(which,pc,new):
        h=codec.unpack_record('image_header',images[which][:128]); addr=h['instruction_offset']+pc*16
        return dict(fault_addr=addr,fault_xor=int.from_bytes(images[which][addr:addr+16],'little')^new)
    def encoded(ins): return codec.encode_instruction(ins,'mother')
    cases=[case('single_fast',stall=0),case('single_stalled',stall=2),case('single_two_jobs',calls=2,runs=2,stall=3),
        case('receiver_first','receiver',2,ready1=1,dependency=1,traffic=1,stall=2),
        case('receiver_two_jobs','receiver',4,ready1=1,dependency=1,traffic=1,runs=2,stall=3),
        case('receiver_scalarHigh','receiver',2,ready1=1,dependency=1,scalar=0xfedcba98),
        case('movi_args','movi'),case('held_CALL_returns_independent','two',2,hold_target=0,hold_cycles=180,delay1=10),
        case('error_before_READY','receiver',1,ready1=1,dependency=1,error_target=1,expected=9),
        case('error_cancels_other','two',2,error_target=0,delay0=10,delay1=200,cancels=1,expected=9),
        case('error_held_CALL','two',2,error_target=1,delay1=50,hold_target=0,hold_cycles=100,cancels=1,expected=9),
        case('recover_error_two_jobs','receiver',3,ready1=1,dependency=1,error_target=1,recover=1,runs=2,expected=9),
        case('missing_child',no_terminal=0,poison=1),case('stale_return',bad_return=1,poison=1),
        case('revoke_held_CALL',calls=0,mode=5,hold_target=0,hold_cycles=2000,poison=1),
        case('disabled_target','target1',0,enabled=1,expected=4),
        case('duplicate_token','two',1,delay1=200,expected=7,cancels=1,
             **fault('two',1,encoded(dict(op='G_CALL',a=0,b=0,c=0)))),
        case('invalid_opcode',delay0=200,expected=1,cancels=1,**fault('single',1,0xfe<<120)),
        case('bounds',expected=6,**fault('single',2,encoded(dict(op='G_MOVI',a=0,x=0)))),
        case('unconsumed_READY','receiver',1,ready1=1,expected=7,**fault('receiver',1,encoded(dict(op='G_WAIT',x=1)))),
        case('PM_error',delay0=200,expected=10,cancels=1,pm_error=1,fault_addr=144),
        case('prefix_overflow','two',2,prefix_max=1),
        case('partial_load',calls=0,mode=1,negative=True),case('bad_header',calls=0,mode=2,negative=True),
        case('bad_START_generation',calls=0,mode=3,negative=True),case('bad_START_args',calls=0,mode=4,negative=True)]
    obj=out/'obj_dir'; cmd=[a.verilator,'--binary','--timing','--top-module','tb_mc_min','-I'+str(HERE),'--Mdir',obj,'-j','4','-o','sim',
                          HERE/'mc_min_controller.sv',HERE/'tb_mc_min.sv']
    compile_log=common.run(cmd,out,env,out/'compile.log'); results=[]; traces={}
    for c in cases:
        data=images[c['image']]
        if c.get('mode')==2: data=bytes([data[0]^1])+data[1:]
        ip=out/(c['name']+'.mem'); ip.write_text('\n'.join('{:032x}'.format(int.from_bytes(data[i:i+16],'little')) for i in range(0,len(data),16))+'\n',encoding='ascii')
        argv=[obj/'sim','+IMAGE='+str(ip),'+WORDS='+str(len(data)//16),'+CALLS='+str(c['calls']),'+STALL='+str(c.get('stall',2))]
        for key,arg in [('mode','MODE'),('runs','RUNS'),('ready1','READY1'),('dependency','DEPENDENCY'),('error_target','ERROR_TARGET'),
            ('no_terminal','NO_TERMINAL'),('hold_target','HOLD_TARGET'),('hold_cycles','HOLD_CYCLES'),('delay0','DELAY0'),('delay1','DELAY1'),
            ('scalar','SCALAR'),('traffic','TRAFFIC'),('bad_return','BAD_RETURN'),('prefix_max','PREFIX_MAX'),('recover','RECOVER'),
            ('cancels','CANCELS'),('expected','EXPECTED'),('poison','POISON'),('enabled','ENABLED'),('fault_addr','FAULT_ADDR'),('pm_error','PM_ERROR')]:
            if key in c: argv.append('+'+arg+'='+str(c[key]))
        argv.append('+FAULT_XOR={:032x}'.format(c.get('fault_xor',0)))
        log=common.run(argv,out,env,out/(c['name']+'.log')); common.check_cycles.need('PASS mother' in log,'mother TB PASS missing')
        rows=mc_check.decode(log); traces[c['name']]=rows
        checked=dict(negative_admission_only=True,cycles=len(rows)) if c.get('negative') else mc_check.check(rows,c)
        results.append(dict(case=c,checker=checked,input_image_sha256=common.sha(data),log_sha256=common.sha(log.encode()),command=[str(x) for x in argv]))
        print(c['name'],'PASS',len(rows),'cycles',flush=True)
    mutants=mc_check.mutations(traces,{c['name']:c for c in cases})
    report=dict(schema='mother-bounded-rtl-runs/0.1',results=results,mutation_checks=mutants,
        compile_command=[str(x) for x in cmd],compile_log_sha256=common.sha(compile_log.encode()),dut_sha256=common.sha((HERE/'mc_min_controller.sv').read_bytes()),
        tools=dict(verilator=common.run([a.verilator,'--version'],out,env).splitlines()[0],python=sys.version),
        actual_mother_RTL=True,actual_local_RTL=False,finite_child_peers=2,whole_message_bits=512,control_tokens=8,
        G_PARAM_tested=False,full_Block_tested=False,physical_tested=False)
    (out/'mother_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('PASS',len(results),'mother RTL runs;',len(mutants),'mutations rejected',flush=True)


if __name__=='__main__': main()
