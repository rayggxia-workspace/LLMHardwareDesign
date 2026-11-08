"""Run server-only RTL fault injections through the external PM/service peers."""
import argparse
import json
import os
import pathlib
import sys
import run as common
import fault_check

HERE=pathlib.Path(__file__).resolve().parent


def main():
    p=argparse.ArgumentParser(); p.add_argument('--verilator',default='verilator')
    p.add_argument('--out',required=True,type=pathlib.Path); a=p.parse_args()
    out=a.out.resolve(); out.mkdir(parents=True,exist_ok=True); env=dict(os.environ)
    command=[a.verilator,'--binary','--timing','--top-module','tb_lc_fault','-I'+str(HERE),
        '--Mdir',out/'obj_dir','-j','4','-o','sim',HERE/'lc_min_controller.sv',HERE/'tb_lc_fault.sv']
    log=common.run(command,out,env,out/'compile.log')
    bundles=json.loads((HERE.parent/'control_image_v0_1/bundles.json').read_text(encoding='utf-8'))['bundles']
    data=bytes.fromhex(next(b for b in bundles if b['manifest']['bundle']=='single_M_clear')['images_hex']['local0'])
    h=common.codec.unpack_record('image_header',data[:128]); io=h['instruction_offset']; td=h['task_offset']; ex=h['execution_offset']
    def word(a): return int.from_bytes(data[a:a+16],'little')
    def patch(a,w): return dict(fault_addr=a,fault_xor=word(a)^w)
    def case(name,expected=0,pc=0,commands=0,**kw):
        return dict(name=name,expected=expected,error_pc=pc,commands=commands,**kw)
    cases=[
        case('bad_opcode',1,**patch(io,(word(io)&((1<<120)-1))|(0xfe<<120))),
        case('bad_EXEC_flags',2,fault_addr=io,fault_xor=1<<112),
        case('unavailable_resource',4,fault_addr=io,fault_xor=1<<104),
        case('bad_token',2,fault_addr=io,fault_xor=8<<96),
        case('bad_descriptor_index',5,fault_addr=io,fault_xor=1<<88),
        case('bad_task_entry',5,fault_addr=td,fault_xor=3<<32),
        case('bad_exec_version',5,fault_addr=ex,fault_xor=3),
        case('bad_exec_ABI',5,fault_addr=ex+48,fault_xor=1<<64),
        case('bad_WAIT',7,1,1,fault_addr=io+16,fault_xor=3<<32),
        case('END_with_live_token',7,1,1,**patch(io+16,0x4f<<120)),
        case('PM_task_error',10,fault_addr=td,pm_error=1),
        case('PM_instruction_error',10,fault_addr=io,pm_error=1),
        case('PM_descriptor_error',10,fault_addr=ex,pm_error=1),
        case('bad_opcode_after_EXEC',1,1,1,**patch(io+16,0xfe<<120)),
        case('native_error_precedence',9,0,1,status=9,**patch(io+16,0xfe<<120)),
        case('step_budget',12,1,1,**patch(td+16,(word(td+16)&~0xffffffff)|1)),
        case('poison_PM_response',poison=1,no_response=1),
        case('poison_held_PM',poison=1,hold_pm=1),
        case('poison_held_service',poison=1,hold_svc=1),
        case('poison_M_response',commands=1,poison=1,no_response=2),
        case('poison_fault_drain',commands=1,poison=1,no_response=2,fault_addr=io+16,fault_xor=3<<32),
        case('poison_reset_reload',commands=2,poison=1,no_response=2,recovery=2),
        case('fault_then_reuse',1,0,1,recovery=1,**patch(io,0xfe<<120)),
        case('PM_error_while_M_pending',10,1,1,fault_addr=io+16,pm_error=1),
        case('native_over_PM_error',9,0,1,status=9,fault_addr=io+16,pm_error=1),
    ]+[case('reject_CALL_'+n,reject=i) for i,n in enumerate(['target','image','epoch','sequence'],1)]
    task=common.codec.pack_record('task_message',dict(kind=0,target_block=0,job_id=7,epoch=1,
        task_sequence=1,completion_token=0,task_descriptor=0,program_image_id=h['program_image_id'],topology_id=h['topology_id']))
    reports=[]; traces={}
    for c in cases:
        name=c['name']; image_path,task_path=out/(name+'.mem'),out/(name+'.task')
        image_path.write_text('\n'.join('{:032x}'.format(int.from_bytes(data[i:i+16],'little')) for i in range(0,len(data),16))+'\n',encoding='ascii')
        task_path.write_text('{:0128x}\n'.format(int.from_bytes(task,'little')),encoding='ascii')
        cmd=[out/'obj_dir/sim','+IMAGE='+str(image_path),'+TASK='+str(task_path),'+WORDS='+str(len(data)//16),'+STALL=2']
        for field,arg in [('status','STATUS'),('fault_addr','FAULT_ADDR'),('pm_error','PM_ERROR'),('expected','EXPECTED'),
            ('error_pc','ERROR_PC'),('commands','COMMANDS'),('poison','POISON'),('recovery','RECOVERY'),
            ('no_response','NO_RESPONSE'),('hold_pm','HOLD_PM'),('hold_svc','HOLD_SVC'),('reject','REJECT')]:
            if field in c: cmd.append('+'+arg+'='+str(c[field]))
        cmd.append('+FAULT_XOR={:032x}'.format(c.get('fault_xor',0)))
        actual=common.run(cmd,out,env,out/(name+'.log'))
        if 'PASS ' not in actual: raise ValueError('missing TB PASS '+name)
        trace=common.decode_trace(actual); traces[name]=trace
        checked=fault_check.check(trace,c)
        reports.append(dict(case=c,cycles=len(trace['cycles']),checker=checked,actual_rtl_simulation=True,
            observations=common.observations(trace),log_sha256=common.sha(actual.encode()),
            input_image_sha256=common.sha(data),input_task_sha256=common.sha(task),command=[str(x) for x in cmd]))
        print(name,'PASS',len(trace['cycles']),'cycles',flush=True)
    mutants=fault_check.mutations(traces,{c['name']:c for c in cases})
    report=dict(schema='local-fault-rtl-runs/0.1',evidence='actual_SV_DUT_external_fault_injection',
        dut_sha256=common.sha((HERE/'lc_min_controller.sv').read_bytes()),
        testbench_sha256=common.sha((HERE/'tb_lc_fault.sv').read_bytes()),
        checker_sha256=common.sha((HERE/'fault_check.py').read_bytes()),
        compile_command=[str(x) for x in command],compile_log_sha256=common.sha(log.encode()),
        tools=dict(verilator=common.run([a.verilator,'--version'],out,env).splitlines()[0],python=sys.version),
        results=reports,mutation_checks=mutants,stall_limit_cycles=128,
        provider_reset_scope='controller + finite PM/service peers, full image reload; no real macro provider',
        native_macro_tested=False,full_block_tested=False,mother_rtl_tested=False,physical_tested=False)
    (out/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('PASS',len(reports),'fault RTL runs;',len(mutants),'mutations rejected')


if __name__=='__main__': main()
