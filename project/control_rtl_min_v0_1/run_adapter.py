"""Compile strict M adapter peers and LC + unchanged real native M RTL."""
import argparse,json,os,pathlib,sys
import run as common
import cancel_check,adapter_check
HERE=pathlib.Path(__file__).resolve().parent


def main():
    p=argparse.ArgumentParser(); p.add_argument('--verilator',default='verilator'); p.add_argument('--out',required=True,type=pathlib.Path)
    a=p.parse_args(); out=a.out.resolve(); out.mkdir(parents=True,exist_ok=True); env=dict(os.environ)
    bundles=json.loads((HERE.parent/'control_image_v0_1/bundles.json').read_text(encoding='utf-8'))['bundles']
    images={b['manifest']['bundle']:bytes.fromhex(b['images_hex']['local0']) for b in bundles}
    clear=images['single_M_clear']; h=common.codec.unpack_record('image_header',clear[:128]); ex=h['execution_offset']
    descriptor=clear[ex:ex+128]; canonical=int.from_bytes(descriptor,'little')
    descriptor_file=out/'clear.descriptor'; descriptor_file.write_text('{:0256x}\n'.format(canonical),encoding='ascii')
    reports=[]; compile_reports=[]; unit_rows=None
    native_source=HERE.parent/'rtl/block_v2/block_v2_m.sv'
    for top,sources,kind in [('tb_m_clear_adapter',[HERE/'lc_m_clear_adapter.sv',HERE/'tb_m_clear_adapter.sv'],'protocol_peer'),
        ('tb_lc_native',[HERE/'lc_min_controller.sv',HERE/'lc_m_clear_adapter.sv',native_source,HERE/'tb_lc_native.sv'],'real_native_M')]:
        obj=out/('obj_'+top)
        cmd=[a.verilator,'--binary','--timing','--top-module',top,'-I'+str(HERE),'--Mdir',obj,'-j','4','-o','sim']+sources
        compiled=common.run(cmd,out,env,out/(top+'.compile.log'))
        compile_reports.append(dict(top=top,command=[str(x) for x in cmd],log_sha256=common.sha(compiled.encode())))
        if kind=='protocol_peer':
            for mode in range(10):
                name='adapter_peer_'+str(mode); run=[obj/'sim','+MODE='+str(mode),'+DESCRIPTOR='+str(descriptor_file)]
                log=common.run(run,out,env,out/(name+'.log')); need_pass(log,name)
                rows=adapter_check.unit_trace(log); checked=adapter_check.check_unit(rows,mode,canonical)
                if mode==0: unit_rows=rows
                reports.append(dict(name=name,kind=kind,mode=mode,checker=checked,cycles=len(rows),
                    actual_rtl_simulation=True,log_sha256=common.sha(log.encode()),command=[str(x) for x in run]))
                print(name,'PASS',len(rows),'cycles',flush=True)
        else:
            for name,bundle,stall,calls,cancel in [('native_empty','empty_task',0,1,0),
                ('native_clear','single_M_clear',0,1,0),('native_stalled','single_M_clear',2,1,0),
                ('native_reuse','single_M_clear',2,2,0),('native_cancel','single_M_clear',2,1,1)]:
                data=images[bundle]; h=common.codec.unpack_record('image_header',data[:128])
                task=common.codec.pack_record('task_message',dict(kind=0,target_block=0,job_id=7,epoch=1,
                    task_sequence=1,completion_token=0,task_descriptor=0,program_image_id=h['program_image_id'],topology_id=h['topology_id']))
                image_path,task_path=out/(name+'.mem'),out/(name+'.task')
                image_path.write_text('\n'.join('{:032x}'.format(int.from_bytes(data[i:i+16],'little')) for i in range(0,len(data),16))+'\n',encoding='ascii')
                task_path.write_text('{:0128x}\n'.format(int.from_bytes(task,'little')),encoding='ascii')
                run=[obj/'sim','+IMAGE='+str(image_path),'+TASK='+str(task_path),'+WORDS='+str(len(data)//16),
                    '+STALL='+str(stall),'+CALLS='+str(calls),'+CANCEL='+str(cancel),'+STATUS='+str(11 if cancel else 0)]
                log=common.run(run,out,env,out/(name+'.log')); need_pass(log,name); trace=common.decode_trace(log)
                checked=cancel_check.check(trace) if cancel else common.check_cycles.check_trace(trace)
                bridge=adapter_check.check_native(log,trace)
                reports.append(dict(name=name,kind=kind,actual_rtl_simulation=True,checker=checked,native_bridge=bridge,
                    cycles=len(trace['cycles']),observations=common.observations(trace),input_image_sha256=common.sha(data),
                    input_task_sha256=common.sha(task),log_sha256=common.sha(log.encode()),command=[str(x) for x in run]))
                print(name,'PASS',len(trace['cycles']),'cycles',flush=True)
    mutants=adapter_check.mutations(unit_rows,canonical)
    report=dict(schema='local-M-clear-adapter-runs/0.1',evidence='real adapter RTL; native integration separated from injected protocol peers',
        results=reports,compile_reports=compile_reports,mutation_checks=mutants,
        sources_sha256={p.name:common.sha(p.read_bytes()) for p in [HERE/'lc_min_controller.sv',HERE/'lc_m_clear_adapter.sv',native_source,
            HERE/'tb_m_clear_adapter.sv',HERE/'tb_lc_native.sv',HERE/'adapter_check.py']},
        native_source=dict(path='project/rtl/block_v2/block_v2_m.sv',git_blob='d91ffdf904bc77c19d5d0ecfd4cd11560b44a417',changed=False),
        tools=dict(verilator=common.run([a.verilator,'--version'],out,env).splitlines()[0],python=sys.version),
        full_block_tested=False,MAC_numeric_tested=False,full_provider_reset_coordinator_tested=False,mother_rtl_tested=False,physical_tested=False)
    (out/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('PASS',len(reports),'adapter RTL runs;',len(mutants),'mutations rejected')


def need_pass(log,name):
    if 'PASS ' not in log: raise ValueError('missing TB PASS '+name)


if __name__=='__main__': main()
