"""Compile actual MC + two actual LC cores; bounded program/SRAM/link peers."""
import argparse,copy,json,os,pathlib,sys
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parent.parent/"control_rtl_min_v0_1"))
import run as common
import dma_check
import network_check
HERE=pathlib.Path(__file__).resolve().parent
OLD=HERE.parent/'control_rtl_min_v0_1'
codec=common.codec; image=common.check_cycles.image


def main():
    p=argparse.ArgumentParser(); p.add_argument('--verilator',default='verilator'); p.add_argument('--out',type=pathlib.Path,required=True)
    a=p.parse_args(); out=a.out.resolve(); out.mkdir(parents=True,exist_ok=True); env=dict(os.environ)
    bundles=json.loads((HERE.parent/'control_image_v0_1/bundles.json').read_text(encoding='utf-8'))['bundles']
    def bundle(name): return {k:bytes.fromhex(v) for k,v in next(b for b in bundles if b['manifest']['bundle']==name)['images_hex'].items()}
    images={'receiver':bundle('receiver_first_16B'),'empty':bundle('empty_task')}
    parsed=image.parse_image(images['empty']['local0'],'local'); records=copy.deepcopy({k:v for k,v in parsed['records'].items() if k!='instruction'})
    records['task'][0]['program_image_id']=101
    images['empty']['local1']=image.assemble_image('local',parsed['program'],records,101,0)
    images['empty']['mother']=image.assemble_image('mother',[dict(op='G_CALL',a=1,b=0,c=0),dict(op='G_CALL',a=0,b=1,c=0),dict(op='G_WAIT',x=3),dict(op='G_END')],{},701,0)
    scalar=copy.deepcopy(images['receiver']); parsed=image.parse_image(scalar['local1'],'local'); prog=parsed['program']; rec={k:v for k,v in parsed['records'].items() if k!='instruction'}
    for ins in prog:
        if ins['op']=='L_MOVI': ins['a']=7; ins['x']=0xfedcba98
        elif ins['op']=='L_REPORT': ins['b']=7
    scalar['local1']=image.assemble_image('local',prog,rec,101,parsed['header']['resource_mask']); images['scalar']=scalar
    def local(calls,commands,reports,**kw): return dict(calls=calls,commands=commands,reports=reports,**kw)
    def case(name,which='receiver',calls=2,locals=None,**kw):
        return dict(name=name,image=which,calls=calls,locals=locals or [local(1,2,0),local(1,1,1)],**kw)
    cases=[case('receiver_fast',stall=0),case('receiver_stalled',stall=3),case('receiver_two_jobs',calls=4,runs=2,stall=2,
                locals=[local(2,4,0),local(2,2,2)]),case('scalar_R7'),
        case('return_backpressure',return_delay=40,stall=3),
        case('held_CALL_independent_return','empty',locals=[local(1,0,0),local(1,0,0)],hold_target=0,hold_cycles=180),
        case('error_before_READY',calls=1,mode=1,expected=5,locals=[local(0,0,0),local(1,0,0,expected=5)]),
        case('recover_unequal_sequences',calls=3,mode=3,expected=5,recover=1,runs=2,
             locals=[local(1,2,0),local(2,1,1)]),
        case('missing_TX_ACK',mode=2,poison=1,locals=[local(1,2,0,poison=1),local(1,1,1)]),
        case('error_cannot_close_RX',mode=4,poison=1,cancels=1,locals=[local(1,1,0,expected=5),local(1,1,1,poison=1)])]
    cases[3]['image']='scalar'
    cases += [case('external_error_poison',mode=5,poison=1,locals=[local(1,1,0,poison=1),local(1,1,1,poison=1)]),case('wrong_physical_ID_poison',mode=6,poison=1,locals=[local(1,1,0,poison=1),local(1,1,1,poison=1)])]
    obj=out/'obj_dir'; cmd=[a.verilator,'--binary','--timing','--top-module','tb_control_dma','-I'+str(OLD),'--Mdir',obj,'-j','4','-o','sim']
    cmd+=[OLD/x for x in ['mc_min_controller.sv','lc_min_controller.sv','tb_network_pm.sv']]
    cmd+=[HERE/'lc_raw16_s_adapter.sv',HERE/'tb_dma_local.sv',HERE/'tb_control_dma.sv',HERE/'raw16_dma_bridge.sv',HERE/'finite_external_memory.sv']
    cmd+=[HERE.parent/x for x in ['rtl/block_local_s/block_local_s_arbiter.sv','rtl/block_local_s/block_local_s_macro.sv','rtl/block_feed_v1/block_feed_s16k.sv','rtl/block_feed_v1/block_feed_loader.sv','rtl/hbm_feed/hbm_group_dma.sv','rtl/hbm_feed/hbm_async_fifo.sv']]
    compile_log=common.run(cmd,out,env,out/'compile.log'); traces={}; results=[]
    for c in cases:
        paths={}
        for target,data in images[c['image']].items():
            f=out/(c['name']+'-'+target+'.mem'); f.write_text('\n'.join('{:032x}'.format(int.from_bytes(data[i:i+16],'little')) for i in range(0,len(data),16))+'\n',encoding='ascii'); paths[target]=f
        argv=[obj/'sim','+IMAGE='+str(paths['mother']),'+WORDS='+str(len(images[c['image']]['mother'])//16),'+CALLS='+str(c['calls']),'+STALL='+str(c.get('stall',2))]
        for b in (0,1): argv+=['+LOCAL'+str(b)+'='+str(paths['local'+str(b)]),'+WORDS'+str(b)+'='+str(len(images[c['image']]['local'+str(b)])//16)]
        for key,arg in [('mode','MODE'),('runs','RUNS'),('cancels','CANCELS'),('expected','EXPECTED'),('poison','POISON'),
            ('hold_target','HOLD_TARGET'),('hold_cycles','HOLD_CYCLES'),('return_delay','RETURN_DELAY')]:
            if key in c: argv.append('+'+arg+'='+str(c[key]))
        log=common.run(argv,out,env,out/(c['name']+'.log')); common.check_cycles.need('PASS network' in log,'network TB PASS missing')
        trace=network_check.decode(log); checked=network_check.check(trace,c,images[c['image']]); traces[c['name']]=trace; checked['DMA']=dma_check.fault(log,c['mode']) if c.get('mode',0) in (5,6) else dma_check.check(log)
        if c['name']=='receiver_stalled': native_mutants=dma_check.mutations(log)
        results.append(dict(case=c,checker=checked,cycles=len(trace['mother']),log_sha256=common.sha(log.encode()),
            input_images_sha256={k:common.sha(v) for k,v in images[c['image']].items()},command=[str(x) for x in argv]))
        print(c['name'],'PASS',len(trace['mother']),'cycles',flush=True)
    mutants=network_check.mutations(traces,{c['name']:c for c in cases},images)
    bridge_report=__import__('run_bridge').run(a.verilator,out/'bridge')
    report=dict(bridge=bridge_report,schema='actual-control-private-S-DMA-runs/0.1',results=results,mutation_checks=mutants,actual_mother_RTL=True,actual_local_RTL=2,
        finite_SRAM_bytes_each=16384,native_S_RTL=True,native_S_instances=2,real_DMA=True,real_CDC_FIFOs=2,adapter_mutations=native_mutants,full_Block_tested=False,physical_tested=False,RX_close_tested=False,
        compile_command=[str(x) for x in cmd],compile_log_sha256=common.sha(compile_log.encode()),
        sources_sha256={n:common.sha((OLD/n).read_bytes()) for n in ['mc_min_controller.sv','lc_min_controller.sv']},
        tools=dict(verilator=common.run([a.verilator,'--version'],out,env).splitlines()[0],python=sys.version))
    (out/'real_dma_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('PASS',len(results),'actual mother/two-LC cases;',len(mutants),'mutations rejected',flush=True)


if __name__=='__main__': main()
