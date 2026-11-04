"""Server RTL campaign for CANCEL, preserved offers, drain and quarantine."""
import argparse
import json
import os
import pathlib
import sys
import run as common
import cancel_check

HERE=pathlib.Path(__file__).resolve().parent


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--verilator',default='verilator')
    parser.add_argument('--out',required=True,type=pathlib.Path)
    a=parser.parse_args(); out=a.out.resolve(); out.mkdir(parents=True,exist_ok=True)
    env=dict(os.environ)
    command=[a.verilator,'--binary','--timing','--top-module','tb_lc_cancel','-I'+str(HERE),
        '--Mdir',out/'obj_dir','-j','4','-o','sim',HERE/'lc_min_controller.sv',HERE/'tb_lc_cancel.sv']
    log=common.run(command,out,env,out/'compile.log')
    bundles=json.loads((HERE.parent/'control_image_v0_1/bundles.json').read_text(encoding='utf-8'))['bundles']
    images={b['manifest']['bundle']:bytes.fromhex(b['images_hex']['local0']) for b in bundles}
    scenarios=[
        ('before_task_fetch',1,'single_M_clear',0,1),('held_task_request',2,'single_M_clear',0,1),
        ('task_response_pending',3,'single_M_clear',0,1),('instruction_response_pending',4,'single_M_clear',0,1),
        ('descriptor_response_pending',5,'single_M_clear',0,1),('held_service',6,'single_M_clear',0,1),
        ('wait_service',7,'single_M_clear',0,1),('response_same_edge',8,'single_M_clear',0,1),
        ('locked_DONE',9,'single_M_clear',0,1),('poison_missing_response',10,'single_M_clear',0,1),
        ('duplicate_CANCEL',11,'single_M_clear',0,1),('poison_held_PM',12,'single_M_clear',0,1),
        ('wrong_CANCEL_identity',13,'single_M_clear',0,1),('END_decode_priority',14,'empty_task',0,1),
        ('cancel_then_reuse',15,'single_M_clear',0,2),('native_error_same_edge',16,'single_M_clear',9,1),
        ('completed_token_priority',17,'single_M_clear',0,1),('held_instruction_request',18,'single_M_clear',0,1),
        ('held_descriptor_request',19,'single_M_clear',0,1),('instruction_response_same_edge',20,'single_M_clear',0,1),
        ('new_service_priority',21,'single_M_clear',0,1),('poison_wrong_response_identity',22,'single_M_clear',0,1)]
    reports=[]; traces={}
    for name,point,bundle,status,calls in scenarios:
        data=images[bundle]; h=common.codec.unpack_record('image_header',data[:128])
        task=common.codec.pack_record('task_message',dict(kind=0,target_block=0,job_id=7,epoch=1,
            task_sequence=1,completion_token=0,task_descriptor=0,program_image_id=h['program_image_id'],topology_id=h['topology_id']))
        image_path,task_path=out/(name+'.mem'),out/(name+'.task')
        image_path.write_text('\n'.join('{:032x}'.format(int.from_bytes(data[i:i+16],'little')) for i in range(0,len(data),16))+'\n',encoding='ascii')
        task_path.write_text('{:0128x}\n'.format(int.from_bytes(task,'little')),encoding='ascii')
        cmd=[out/'obj_dir/sim','+IMAGE='+str(image_path),'+TASK='+str(task_path),'+WORDS='+str(len(data)//16),
            '+STALL=2','+STATUS='+str(status),'+POINT='+str(point),'+CALLS='+str(calls)]
        actual=common.run(cmd,out,env,out/(name+'.log'))
        if 'PASS ' not in actual: raise ValueError('no testbench PASS: '+name)
        trace=common.decode_trace(actual); trace['name']=name; traces[name]=trace
        checked=cancel_check.check(trace,poison=point in (10,12,22),expected_cancels=0 if point==13 else 2 if point==11 else 1)
        reports.append(dict(name=name,point=point,status=status,calls=calls,cycles=len(trace['cycles']),
            actual_rtl_simulation=True,checker=checked,observations=common.observations(trace),
            input_image_sha256=common.sha(data),input_task_sha256=common.sha(task),
            log_sha256=common.sha(actual.encode('utf-8')),command=[str(c) for c in cmd]))
        print(name,'PASS',len(trace['cycles']),'cycles',flush=True)
    rejected=cancel_check.mutations(traces)
    report=dict(schema='local-cancel-rtl-runs/0.1',evidence='actual_SV_DUT_with_external_protocol_peers',
        dut_sha256=common.sha((HERE/'lc_min_controller.sv').read_bytes()),
        testbench_sha256=common.sha((HERE/'tb_lc_cancel.sv').read_bytes()),
        checker_sha256=common.sha((HERE/'cancel_check.py').read_bytes()),
        compile_command=[str(c) for c in command],compile_log_sha256=common.sha(log.encode('utf-8')),
        tools=dict(verilator=common.run([a.verilator,'--version'],out,env).splitlines()[0],python=sys.version),
        output_directory=str(out),results=reports,mutation_checks=rejected,
        drain_limit_cycles=128,full_provider_reset_tested=False,native_macro_tested=False,full_block_tested=False,mother_rtl_tested=False,
        physical_tested=False)
    (out/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('PASS',len(reports),'cancellation RTL runs;',len(rejected),'observer mutations rejected')


if __name__=='__main__': main()
